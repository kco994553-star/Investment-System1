"""Why does an issuer have no usable share count at as_of? Diagnostic only — nothing here feeds the ranking.

For --cik: (1) every dei:EntityCommonStockSharesOutstanding / TradingSymbol / Security12bTitle fact of the stored cover
XBRL instance (latest 10-K/10-Q filed <= as_of) with raw text, unit, decimals and ALL context dimensions; (2) the
companyfacts share series (dei + us-gaap) with filed dates, split into filed <= as_of and filed > as_of; (3) what
pit_shares / parse_cover / class_symbols return; (4) cover-page sentences of the primary documents (latest 10-K and
10-Q filed <= as_of) that state shares outstanding. Facts filed after as_of are reported as
POST_AS_OF_FILING (investigation only, never applied as the as_of share count).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/share_count_diagnostic.py --cik 0001800227 --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_companyfacts, load_submissions_merged  # noqa: E402
from investment_system.providers.sec_cover_shares import class_symbols, parse_cover, select_filing  # noqa: E402
from investment_system.universe.sources import pit_shares  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"
COVER_FACTS = ("EntityCommonStockSharesOutstanding", "TradingSymbol", "Security12bTitle", "SecurityExchangeName",
               "EntityRegistrantName", "DocumentType", "DocumentPeriodEndDate")
SHARE_CONCEPTS = ("EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding", "CommonStockSharesIssued",
                  "WeightedAverageNumberOfSharesOutstandingBasic", "SharesOutstanding")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_scd_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag.split(":")[-1]


def cover_facts(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    ctx = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        dims, date = [], None
        for e in c.iter():
            n = _local(e.tag)
            if n in ("explicitMember", "typedMember"):
                dims.append(f"{_local(str(e.get('dimension') or ''))}={_local((e.text or '').strip()) or 'typed'}")
            elif n in ("instant", "endDate"):
                date = (e.text or "").strip()
        ctx[str(c.get("id"))] = {"dims": dims, "date": date}
    out = []
    for e in root.iter():
        n = _local(e.tag)
        if n in COVER_FACTS and e.get("contextRef") is not None:
            c = ctx.get(str(e.get("contextRef"))) or {}
            out.append({"concept": n, "raw": (e.text or "").strip(), "unit": e.get("unitRef"), "decimals": e.get("decimals"),
                        "nil": e.get("{http://www.w3.org/2001/XMLSchema-instance}nil"), "date": c.get("date"),
                        "dims": c.get("dims"), "context": e.get("contextRef")})
    return out


def companyfacts_shares(cf: dict, as_of: datetime) -> dict:
    cut = as_of.date().isoformat()
    rows = {"filed_on_or_before_as_of": [], "POST_AS_OF_FILING": []}
    for tax, concepts in (cf.get("facts") or {}).items():
        for name, body in concepts.items():
            if name not in SHARE_CONCEPTS:
                continue
            for unit, facts in (body.get("units") or {}).items():
                for f in facts:
                    r = {"concept": f"{tax}:{name}", "unit": unit, "val": f.get("val"), "end": f.get("end"), "filed": f.get("filed"),
                         "form": f.get("form"), "accn": f.get("accn"), "fy": f.get("fy"), "fp": f.get("fp")}
                    rows["filed_on_or_before_as_of" if str(f.get("filed") or "9999") <= cut else "POST_AS_OF_FILING"].append(r)
    for k in rows:
        rows[k] = sorted(rows[k], key=lambda r: (str(r["end"]), str(r["filed"])))[-40:]
    # post-as_of filings that state a count for a period ending on/before as_of: evidence only (never applied)
    rows["POST_AS_OF_FILINGS_ABOUT_PERIODS_ENDING_ON_OR_BEFORE_AS_OF"] = [
        r for r in rows["POST_AS_OF_FILING"] if str(r["end"] or "9999") <= cut]
    return rows


def cover_sentences(text: str) -> list[str]:
    """Sentences stating a number of shares outstanding (cover page wording), first 12 matches."""
    pat = re.compile(r"[^.]{0,300}\b(shares?|units?)\b[^.]{0,200}\boutstanding\b[^.]{0,200}", re.I)
    return [m.group(0).strip()[:600] for m in pat.finditer(text[:60000])][:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--cik", required=True)
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    frd, frc = _load("fetch_real_data"), _load("fetch_class_rights_evidence")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    cik = str(int(a.cik)).zfill(10)
    sub = load_submissions_merged(store, cik, d)[0] or {}
    f = select_filing(sub, d)
    aid = f"xbrl_instance:{cik}:{f['accn']}" if f else None
    rep = {"kind": "SHARE_COUNT_DIAGNOSTIC", "as_of": a.as_of, "cik": cik, "entity_name": sub.get("name"),
           "tickers_current": sub.get("tickers"), "exchanges_current": sub.get("exchanges"), "sic": sub.get("sic"),
           "sic_description": sub.get("sicDescription"), "entity_type": sub.get("entityType"),
           "cover_filing": f, "cover_instance": aid}
    rec = (sub.get("filings") or {}).get("recent") or {}
    rep["filings_on_or_before_as_of"] = [{"form": fm, "filed": dt} for fm, dt in zip(rec.get("form") or [], rec.get("filingDate") or [])
                                         if str(dt) <= a.as_of][:25]
    if aid and store.has(aid):
        raw = store.get_bytes(aid)
        rep["cover_facts"] = cover_facts(raw)
        cov = parse_cover(raw)
        rep["parse_cover"] = cov
        rep["class_symbols"] = class_symbols(cov)
    cf = load_companyfacts(store, cik)
    rep["pit_shares"] = pit_shares(cf, d) if cf is not None else None
    rep["companyfacts_shares"] = companyfacts_shares(cf, d) if cf is not None else None
    log: list[dict] = []
    docs = []
    for lf in frc.latest_forms(sub, d):
        did = frc.doc_id(cik, lf["accn"])
        if not a.no_fetch:
            frd._fetch_one(store, did, frc.ARCHIVE_URL.format(cik=int(cik), accn=lf["accn"].replace("-", ""), doc=lf["primary_document"]),
                           "SEC_FILING_DOCUMENT", frd.UA, log, False)
            frd._throttle(log, 0.15)
        if store.has(did):
            docs.append({**lf, "artifact_id": did, "cover_sentences": cover_sentences(frc.html_text(store.get_bytes(did)))})
    rep["documents"] = docs
    rep["note"] = ("Diagnostic only. POST_AS_OF_FILING rows are investigation evidence and are never used as the as_of "
                   "share count (user decision 2026-09-26).")
    (GE / f"share_count_diagnostic_{cik}_{a.as_of}.json").write_text(json.dumps(rep, indent=1, default=str) + "\n", encoding="utf-8")
    if not a.no_fetch:
        frd.write_store_index(store)
    print(json.dumps({k: rep.get(k) for k in ("entity_name", "cover_filing", "pit_shares", "class_symbols")}, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
