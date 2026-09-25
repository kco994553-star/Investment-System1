"""Cover-page share classes from an SEC XBRL instance. NEW IMPLEMENTATION, no network.

SEC companyfacts drops dimensional facts, so multi-class issuers (META class A/B,
BRK A/B, ...) often have no usable dei:EntityCommonStockSharesOutstanding there.
The filing's XBRL instance keeps the class dimension, and the same cover page tags
each registered class's dei:TradingSymbol, which is what maps a class to a price.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

CLASS_AXIS = "StatementClassOfStockAxis"
PERIODIC_FORMS = ("10-K", "10-Q", "10-K/A", "10-Q/A")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def select_filing(submissions: dict, as_of: datetime) -> dict | None:
    """Latest 10-K/10-Q (or amendment) filed on or before as_of, from submissions 'recent'."""
    rec = (submissions.get("filings") or {}).get("recent") or {}
    best = None
    for i, form in enumerate(rec.get("form") or []):
        if form not in PERIODIC_FORMS:
            continue
        try:
            filed = str(rec["filingDate"][i])
            accn = str(rec["accessionNumber"][i])
            doc = str((rec.get("primaryDocument") or [""] * (i + 1))[i] or "")
        except (KeyError, IndexError):
            continue
        if filed > as_of.date().isoformat() or not doc:
            continue
        if best is None or filed > best["filed"]:
            best = {"form": form, "filed": filed, "accn": accn, "primary_document": doc}
    return best


def instance_name(primary_document: str) -> str:
    """Inline-XBRL filings publish the extracted instance as <primary>_htm.xml."""
    return re.sub(r"\.htm$", "_htm.xml", primary_document)


def parse_cover(xml_bytes: bytes) -> dict:
    """{'classes': [{member, shares, date}], 'symbols': {member|None: [sym]}, 'titles': {member|None: [text]}}.
    member is the StatementClassOfStockAxis member local name, or None for an undimensioned fact."""
    root = ET.fromstring(xml_bytes)
    ctx: dict[str, dict] = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        members, other_dims, date = [], False, None
        for e in c.iter():
            n = _local(e.tag)
            if n in ("explicitMember", "typedMember"):
                if _local(str(e.get("dimension") or "")) == CLASS_AXIS:
                    members.append(_local((e.text or "").strip()))
                else:
                    other_dims = True
            elif n in ("instant", "endDate"):
                date = (e.text or "").strip()
        ctx[str(c.get("id"))] = {"member": members[0] if len(members) == 1 else None,
                                 "dimensioned": bool(members) or other_dims, "date": date}
    classes, symbols, titles = [], {}, {}
    for e in root.iter():
        n = _local(e.tag)
        if n not in ("EntityCommonStockSharesOutstanding", "TradingSymbol", "Security12bTitle"):
            continue
        c = ctx.get(str(e.get("contextRef")))
        if c is None or (c["dimensioned"] and c["member"] is None):
            continue  # other axes (e.g. legal entity) are not share classes of this issuer
        text = (e.text or "").strip()
        if n == "EntityCommonStockSharesOutstanding":
            try:
                classes.append({"member": c["member"], "shares": float(text), "date": c["date"]})
            except ValueError:
                continue
        elif n == "TradingSymbol" and text:
            symbols.setdefault(c["member"], []).append(text.upper())
        elif n == "Security12bTitle" and text:
            titles.setdefault(c["member"], []).append(text)
    if classes:
        last = max(str(r["date"] or "") for r in classes)
        classes = [r for r in classes if str(r["date"] or "") == last]
    return {"classes": classes, "symbols": symbols, "titles": titles}


def class_symbols(cover: dict) -> dict:
    """member -> trading symbol. Dimensioned symbols map directly. A single undimensioned symbol
    with several classes is assigned only when the undimensioned Security12bTitle names exactly one
    'Class X' that matches exactly one CommonClassXMember; otherwise left unmapped (fail-closed)."""
    members = [r["member"] for r in cover["classes"]]
    # only classes with reported shares outstanding (preferred series may also tag a TradingSymbol)
    out = {m: syms[0] for m, syms in cover["symbols"].items() if m is not None and syms and m in members}
    undim = sorted(set(cover["symbols"].get(None) or []))
    if len(members) == 1 and members[0] is None and undim:
        out[None] = undim[0]
    elif len(undim) == 1 and len(members) > 1 and not out:
        letters = {m.group(1) for t in cover["titles"].get(None) or [] for m in re.finditer(r"Class\s+([A-Z])\b", t)}
        if len(letters) == 1:
            want = f"CommonClass{letters.pop()}Member"
            hits = [m for m in members if m == want]
            if len(hits) == 1:
                out[hits[0]] = undim[0]
    return out
