"""Cover-page share classes from an SEC XBRL instance. NEW IMPLEMENTATION, no network.

SEC companyfacts drops dimensional facts, so multi-class issuers (META class A/B,
BRK A/B, ...) often have no usable dei:EntityCommonStockSharesOutstanding there.
The filing's XBRL instance keeps the class dimension, and the same cover page tags
each registered class's dei:TradingSymbol, which is what maps a class to a price.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

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


DOMESTIC_PERIODIC = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
FOREIGN_PERIODIC = {"20-F", "20-F/A", "40-F", "40-F/A"}


def pit_filer_status(submissions: dict, as_of: datetime, pages_complete: bool = True) -> str:
    """Filer type AT as_of, from the latest periodic report filed on or before as_of (not today's forms).
    DOMESTIC (10-K/10-Q) | FOREIGN (20-F/40-F) | NOT_REGISTERED_AT_AS_OF (no filing at all by as_of)
    | UNKNOWN (older filing pages missing, or only non-periodic filings by as_of)."""
    rec = (submissions.get("filings") or {}).get("recent") or {}
    cut = as_of.date().isoformat()
    forms, dates = rec.get("form") or [], rec.get("filingDate") or []
    rows = [(str(d), f) for f, d in zip(forms, dates) if d and str(d) <= cut]
    if not rows:
        return "NOT_REGISTERED_AT_AS_OF" if pages_complete else "UNKNOWN"
    periodic = sorted(r for r in rows if r[1] in DOMESTIC_PERIODIC | FOREIGN_PERIODIC)
    if not periodic:
        return "UNKNOWN"
    return "DOMESTIC" if periodic[-1][1] in DOMESTIC_PERIODIC else "FOREIGN"


PAGE_LOOKBACK_DAYS = 400  # a 10-K/10-Q or 20-F/40-F is always filed within ~13 months


def page_window(as_of: datetime) -> tuple[str, str]:
    return (as_of - timedelta(days=PAGE_LOOKBACK_DAYS)).date().isoformat(), as_of.date().isoformat()


def pages_needed(submissions: dict, as_of: datetime) -> list[str]:
    """Older submissions pages to fetch when 'recent' holds no PERIODIC report filed on or before as_of
    (large filers: 'recent' can end in a run of prospectus filings). Only pages overlapping the
    lookback window before as_of are needed."""
    filings = submissions.get("filings") or {}
    rec = filings.get("recent") or {}
    lo, hi = page_window(as_of)
    if any(d and str(d) <= hi and f in DOMESTIC_PERIODIC | FOREIGN_PERIODIC
           for f, d in zip(rec.get("form") or [], rec.get("filingDate") or [])):
        return []
    return [str(f["name"]) for f in filings.get("files") or []
            if f.get("name") and str(f.get("filingFrom") or "") <= hi and str(f.get("filingTo") or "9999") >= lo]


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
    """member -> trading symbol. Dimensioned symbols map directly. One class + one symbol maps directly.
    A single undimensioned symbol with several classes is assigned only when the undimensioned
    Security12bTitle names exactly one 'Class X' matching exactly one CommonClassXMember, or names
    plain "Common Stock" (no class letter) with exactly one CommonStockMember; otherwise unmapped."""
    members = [r["member"] for r in cover["classes"]]
    # only classes with reported shares outstanding (preferred series may also tag a TradingSymbol)
    out = {m: syms[0] for m, syms in cover["symbols"].items() if m is not None and syms and m in members}
    undim = sorted(set(cover["symbols"].get(None) or []))
    if len(members) == 1 and undim and not out:
        out[members[0]] = undim[0]  # one class, one symbol: unambiguous whether or not the class is dimensioned
    elif len(undim) == 1 and len(members) > 1 and not out:
        titles = cover["titles"].get(None) or []
        letters = {m.group(1) for t in cover["titles"].get(None) or [] for m in re.finditer(r"Class\s+([A-Z])\b", t)}
        if len(letters) == 1:
            want = f"CommonClass{letters.pop()}Member"
            hits = [m for m in members if m == want]
            if len(hits) == 1:
                out[hits[0]] = undim[0]
        elif not letters and any("Common Stock" in t for t in titles) and members.count("CommonStockMember") == 1:
            out["CommonStockMember"] = undim[0]  # registered "Common Stock" vs e.g. unlisted Class B (Ford)
    return out
