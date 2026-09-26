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
REGISTRATION_FORMS = ("10-12B", "10-12B/A", "10-12G", "10-12G/A", "8-K", "8-K/A", "424B3", "424B4", "S-1", "S-1/A")
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
    return [m.group(0).strip()[:600] for m in pat.finditer(text)][:20]


def distribution_sentences(text: str) -> list[str]:
    """Sentences stating a number of shares distributed/issued in a spin-off completion notice (wording that names
    a count without the word 'outstanding' nearby, e.g. GRAIL/AMTM Item 3.03/5.01 8-Ks), first 20 matches."""
    pat = re.compile(r"[^.]{0,250}\b\d[\d,]{5,}\b[^.]{0,50}\bshares\b[^.]{0,200}", re.I)
    return [m.group(0).strip()[:600] for m in pat.finditer(text)][:20]


EXHIBIT_NAME = re.compile(r"(?:^|[^a-z])d?ex-?99", re.I)
INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/index.json"
MAX_EXHIBIT_BYTES = 6_000_000


def exhibit_names(index_json: bytes) -> list[str]:
    """EX-99.x document names (htm/txt) listed in an EDGAR filing folder index.json."""
    try:
        items = (json.loads(index_json).get("directory") or {}).get("item") or []
    except ValueError:
        return []
    out = []
    for it in items:
        n = str(it.get("name") or "")
        try:
            size = int(it.get("size") or 0)
        except ValueError:
            size = 0
        if n.lower().endswith((".htm", ".html", ".txt")) and EXHIBIT_NAME.search(n) and size <= MAX_EXHIBIT_BYTES:
            out.append(n)
    return out[:4]


def exhibit_docs(store, frd, frc, cik: str, accn: str, no_fetch: bool, log: list) -> list[dict]:
    nodash = accn.replace("-", "")
    iid = f"sec_filing_index:{cik}:{accn}"
    if not no_fetch:
        frd._fetch_one(store, iid, INDEX_URL.format(cik=int(cik), nodash=nodash), "SEC_FILING_INDEX", frd.UA, log, False)
        frd._throttle(log, 0.15)
    if not store.has(iid):
        return []
    out = []
    for name in exhibit_names(store.get_bytes(iid)):
        eid = f"sec_filing_exhibit:{cik}:{accn}:{name}"
        if not no_fetch:
            frd._fetch_one(store, eid, frc.ARCHIVE_URL.format(cik=int(cik), accn=nodash, doc=name), "SEC_FILING_DOCUMENT",
                           frd.UA, log, False)
            frd._throttle(log, 0.15)
        if store.has(eid):
            txt = frc.html_text(store.get_bytes(eid))
            out.append({"artifact_id": eid, "exhibit": name, "text_len": len(txt), "cover_sentences": cover_sentences(txt),
                        "distribution_sentences": distribution_sentences(txt), "symbol_sentences": []})
    return out


def symbol_sentences(text: str, symbols: list[str]) -> list[str]:
    """Sentences naming a trading symbol (which class is listed where), first 12."""
    out = []
    for sym in symbols:
        for m in re.finditer(r"[^.;]{0,300}\b" + re.escape(sym) + r"\b[^.;]{0,300}", text):
            out.append(m.group(0).strip()[:600])
            if len(out) >= 12:
                return out
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--cik", action="append", default=[], help="CIK to diagnose (repeatable)")
    ap.add_argument("--cover-unresolved", action="store_true",
                    help="also diagnose every eligible issuer the gate chain's cover route leaves unresolved")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()
    frd, frc = _load("fetch_real_data"), _load("fetch_class_rights_evidence")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    ciks = [str(int(c)).zfill(10) for c in a.cik]
    if a.cover_unresolved:
        chain = _load("run_top500_gate_chain")
        rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
        base = rd(ROOT / "reports" / "us_ingested_facts_listings.json") or {}
        base.update(rd(GE / f"russell1000_extra_listings_{a.as_of}.json") or {})
        rows, _ = chain.extend_listings(store, base, rd(GE / f"missing_large_cap_priority_plan_{a.as_of}.json"),
                                        chain.verify_cik_candidates(store, rd(GE / f"delisted_cik_candidates_{a.as_of}.json") or rd(GE / "delisted_cik_candidates_2024-12-31.json")))
        listings, _ = chain.company_level_listings(store, rows)
        listings, _ = chain.eligibility_filter(store, listings, d)
        _, unresolved = chain.cover_mcap_overrides(store, listings, d)
        ciks += [str(listings[cid]["cik"]).zfill(10) for cid in unresolved if str(listings[cid].get("cik") or "").isdigit()]
    for cik in sorted(set(ciks)):
        diagnose(store, frd, frc, cik, d, a.as_of, a.no_fetch)
    if not a.no_fetch:
        frd.write_store_index(store)


def diagnose(store, frd, frc, cik: str, d: datetime, as_of: str, no_fetch: bool) -> None:
    sub = load_submissions_merged(store, cik, d)[0] or {}
    f = select_filing(sub, d)
    aid = f"xbrl_instance:{cik}:{f['accn']}" if f else None
    rep = {"kind": "SHARE_COUNT_DIAGNOSTIC", "as_of": as_of, "cik": cik, "entity_name": sub.get("name"),
           "tickers_current": sub.get("tickers"), "exchanges_current": sub.get("exchanges"), "sic": sub.get("sic"),
           "sic_description": sub.get("sicDescription"), "entity_type": sub.get("entityType"),
           "cover_filing": f, "cover_instance": aid}
    rec = (sub.get("filings") or {}).get("recent") or {}
    rep["filings_on_or_before_as_of"] = [{"form": fm, "filed": dt} for fm, dt in zip(rec.get("form") or [], rec.get("filingDate") or [])
                                         if str(dt) <= as_of][:25]
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
        if not no_fetch:
            frd._fetch_one(store, did, frc.ARCHIVE_URL.format(cik=int(cik), accn=lf["accn"].replace("-", ""), doc=lf["primary_document"]),
                           "SEC_FILING_DOCUMENT", frd.UA, log, False)
            frd._throttle(log, 0.15)
        if store.has(did):
            txt = frc.html_text(store.get_bytes(did))
            syms = sorted({v for vs in (rep.get("parse_cover") or {}).get("symbols", {}).values() for v in vs})
            docs.append({**lf, "artifact_id": did, "cover_sentences": cover_sentences(txt),
                         "symbol_sentences": symbol_sentences(txt, syms)})
    if not frc.latest_forms(sub, d):
        # newly registered (spin-off / IPO) without a periodic report yet: registration and distribution documents filed
        # on or before as_of (Form 10-12B, 8-K, 424B) are the only PIT sources of a share count (never a later 10-Q)
        rec = (sub.get("filings") or {}).get("recent") or {}
        regs = [{"form": f, "filed": str(dt), "accn": str(ac), "primary_document": str(pd or "")}
                for f, dt, ac, pd in zip(rec.get("form") or [], rec.get("filingDate") or [], rec.get("accessionNumber") or [],
                                         rec.get("primaryDocument") or [])
                if f in REGISTRATION_FORMS and str(dt) <= as_of and pd]
        for lf in sorted(regs, key=lambda r: r["filed"], reverse=True)[:6]:
            did = frc.doc_id(cik, lf["accn"])
            if not no_fetch:
                frd._fetch_one(store, did, frc.ARCHIVE_URL.format(cik=int(cik), accn=lf["accn"].replace("-", ""), doc=lf["primary_document"]),
                               "SEC_FILING_DOCUMENT", frd.UA, log, False)
                frd._throttle(log, 0.15)
            if store.has(did):
                txt = frc.html_text(store.get_bytes(did))
                docs.append({**lf, "artifact_id": did, "cover_sentences": cover_sentences(txt), "symbol_sentences": [],
                             "distribution_sentences": distribution_sentences(txt), "text_len": len(txt)})
            # the Information Statement of a Form 10 / the distribution press release is an EXHIBIT (EX-99.x), not
            # the primary document: list the filing folder and read its EX-99 documents (same filing, same date)
            for ex in exhibit_docs(store, frd, frc, cik, lf["accn"], no_fetch, log):
                docs.append({**lf, **ex})
    rep["documents"] = docs
    rep["note"] = ("Diagnostic only. POST_AS_OF_FILING rows are investigation evidence and are never used as the as_of "
                   "share count (user decision 2026-09-26).")
    (GE / f"share_count_diagnostic_{cik}_{as_of}.json").write_text(json.dumps(rep, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: rep.get(k) for k in ("entity_name", "cover_filing", "pit_shares", "class_symbols")}, indent=1, default=str)[:1500])


if __name__ == "__main__":
    main()
