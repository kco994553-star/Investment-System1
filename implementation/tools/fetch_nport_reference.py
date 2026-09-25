"""Independent dated PIT large-cap reference from SEC N-PORT (Sufficiency path, user decision 2026-09-25).

The iShares Russell 1000 ETF (IWB) reports its full holdings to the SEC on Form NPORT-P; 2024-12-31 is a
fiscal quarter end for the fund, so that report is public. This tool (SEC only, same UA/throttle/resume as
fetch_real_data.py):
  1. reads the registrant's submissions (iShares Trust, name verified) and lists NPORT-P filings whose
     reportDate == as_of,
  2. fetches each filing's small index-headers page until the one whose series name is exactly
     --series-name is found (artifact edgar_index_headers:<accession>),
  3. fetches that filing's primary N-PORT XML (artifact nport:<accession>) and parses equity holdings,
  4. resolves each holding to an SEC CIK by a UNIQUE normalised-name match (current company_tickers titles,
     then cik-lookup-data.txt); ambiguous or unmatched names are reported, never guessed.
Writes reports/gate_evidence/russell1000_nport_<as_of>.json (reference_role SUPERSET_REFERENCE, members =
CIK10 strings) and russell1000_extra_listings_<as_of>.json (members not yet in the pool).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/fetch_nport_reference.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_submissions_merged  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"
REGISTRANT_CIK = "0001100663"  # iShares Trust (verified against the submissions name at run time)
REGISTRANT_NAME_TOKEN = "ISHARES TRUST"
SERIES_NAME = "iShares Russell 1000 ETF"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
INDEX_HEADERS_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{accn}-index-headers.html"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{doc}"
CIK_LOOKUP_URL = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fnr_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def nport_filings_for(submissions: dict, as_of: str) -> list[dict]:
    rec = (submissions.get("filings") or {}).get("recent") or {}
    out = []
    for i, form in enumerate(rec.get("form") or []):
        if form != "NPORT-P":
            continue
        try:
            if str(rec["reportDate"][i]) != as_of:
                continue
            out.append({"accn": str(rec["accessionNumber"][i]), "filed": str(rec["filingDate"][i]),
                        "doc": str((rec.get("primaryDocument") or [""] * (i + 1))[i] or "primary_doc.xml")})
        except (KeyError, IndexError):
            continue
    return out


def series_names(index_headers: bytes) -> list[str]:
    """Series names in an EDGAR index-headers page (SGML header shown as text, tags possibly HTML-escaped)."""
    text = index_headers.decode("utf-8", errors="replace").replace("&lt;", "<").replace("&gt;", ">")
    return [m.strip() for m in re.findall(r"<SERIES-NAME>([^\n<]+)", text) if m.strip()]


def parse_nport(xml_bytes: bytes) -> dict:
    """{'report_date', 'series_name', 'holdings': [{name, cusip, isin, asset_cat, country, value}]}."""
    root = ET.fromstring(xml_bytes)
    out = {"report_date": None, "series_name": None, "holdings": []}
    for e in root.iter():
        n = _local(e.tag)
        if n == "repPdDate" and out["report_date"] is None:
            out["report_date"] = (e.text or "").strip()
        elif n == "seriesName" and out["series_name"] is None:
            out["series_name"] = (e.text or "").strip()
        elif n == "invstOrSec":
            h = {"name": None, "cusip": None, "isin": None, "asset_cat": None, "country": None, "value": None}
            for c in e.iter():
                cn = _local(c.tag)
                if cn == "name" and h["name"] is None:
                    h["name"] = (c.text or "").strip()
                elif cn == "cusip":
                    h["cusip"] = (c.text or "").strip()
                elif cn == "isin":
                    h["isin"] = c.get("value") or (c.text or "").strip()
                elif cn == "assetCat":
                    h["asset_cat"] = (c.text or "").strip()
                elif cn == "invCountry":
                    h["country"] = (c.text or "").strip()
                elif cn == "valUSD":
                    try:
                        h["value"] = float(c.text)
                    except (TypeError, ValueError):
                        pass
            out["holdings"].append(h)
    return out


SUFFIXES = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "LLC", "LP", "HOLDINGS", "HOLDING",
            "GROUP", "THE", "SA", "NV", "AG", "CLASS", "A", "B", "C", "INCORPORATED", "COM", "NEW", "DEL", "REIT"}


def norm_name(n: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]", " ", str(n or "").upper().replace("&", " AND ")).split()
    return " ".join(w for w in words if w not in SUFFIXES)


def name_index(store: RawDatasetStore) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    """(current title -> CIKs, historical name -> CIKs, CIK -> current ticker)."""
    cur, tick = {}, {}
    if store.has("sec_tickers"):
        for row in json.loads(store.get_bytes("sec_tickers")).values():
            c = str(row.get("cik_str")).zfill(10)
            cur.setdefault(norm_name(row.get("title")), set()).add(c)
            tick.setdefault(c, str(row.get("ticker") or "").upper().replace(".", "-"))
    hist = {}
    if store.has("sec_cik_lookup"):
        for ln in store.get_bytes("sec_cik_lookup").decode("latin-1", errors="replace").splitlines():
            parts = ln.rsplit(":", 2)
            if len(parts) >= 3 and parts[1].strip().isdigit():
                hist.setdefault(norm_name(parts[0]), set()).add(parts[1].strip().zfill(10))
    return cur, hist, tick


def resolve(holdings: list[dict], cur: dict, hist: dict) -> tuple[dict[str, dict], list[dict]]:
    """CIK10 -> {names, cusips}; unresolved holdings. Share classes of one issuer collapse to one CIK."""
    members, unresolved = {}, []
    for h in holdings:
        k = norm_name(h["name"])
        c = cur.get(k) or set()
        method = "SEC_TICKERS_TITLE"
        if len(c) != 1:
            c, method = hist.get(k) or set(), "SEC_CIK_LOOKUP"
        if len(c) != 1:
            unresolved.append({**h, "name_matches": len(c)})
            continue
        cik = next(iter(c))
        m = members.setdefault(cik, {"names": [], "cusips": [], "method": method})
        m["names"].append(h["name"])
        m["cusips"].append(h["cusip"])
    return members, unresolved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--series-name", default=SERIES_NAME)
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=GE / "missing_large_cap_priority_plan_2024-12-31.json")
    a = ap.parse_args()
    frd = _load("fetch_real_data")
    chain = _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    log: list[dict] = []
    get = lambda aid, url, kind: (frd._fetch_one(store, aid, url, kind, frd.UA, log, False), frd._throttle(log, 0.15))  # noqa: E731
    get(f"submissions:{REGISTRANT_CIK}", SUBMISSIONS_URL.format(cik=REGISTRANT_CIK), "SEC_SUBMISSIONS")
    get("sec_cik_lookup", CIK_LOOKUP_URL, "SEC_CIK_LOOKUP")
    report = {"kind": "NPORT_REFERENCE_RUN", "as_of": a.as_of, "series_name": a.series_name}
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    sub = load_submissions_merged(store, REGISTRANT_CIK)[0] or {}
    if REGISTRANT_NAME_TOKEN not in str(sub.get("name") or "").upper():
        report["status"] = "REGISTRANT_NOT_VERIFIED"
    else:
        # N-PORT reports for a period are filed ~60 days later; older submissions pages may hold them
        page_mod = _load("fetch_cover_xbrl")
        for f in (sub.get("filings") or {}).get("files") or []:
            if str(f.get("filingTo") or "9999") >= a.as_of:
                get(f"submissions_page:{f['name']}", page_mod.SUBMISSIONS_PAGE_URL.format(name=f["name"]), "SEC_SUBMISSIONS_PAGE")
        sub = load_submissions_merged(store, REGISTRANT_CIK)[0] or {}
        cands = nport_filings_for(sub, a.as_of)
        report["n_candidate_filings"] = len(cands)
        chosen = None
        for f in cands:
            nodash = f["accn"].replace("-", "")
            hid = f"edgar_index_headers:{f['accn']}"
            get(hid, INDEX_HEADERS_URL.format(cik=int(REGISTRANT_CIK), nodash=nodash, accn=f["accn"]), "SEC_INDEX_HEADERS")
            if store.has(hid) and any(s.lower() == a.series_name.lower() for s in series_names(store.get_bytes(hid))):
                chosen = f
                break
        if chosen is None:
            report["status"] = "SERIES_FILING_NOT_FOUND"
        else:
            nid = f"nport:{chosen['accn']}"
            get(nid, DOC_URL.format(cik=int(REGISTRANT_CIK), nodash=chosen["accn"].replace("-", ""), doc=chosen["doc"]), "SEC_NPORT")
            doc = parse_nport(store.get_bytes(nid)) if store.has(nid) else {"holdings": []}
            eq = [h for h in doc["holdings"] if h["asset_cat"] == "EC"]
            report.update({"filing": chosen, "nport_report_date": doc.get("report_date"), "nport_series": doc.get("series_name"),
                           "n_holdings": len(doc["holdings"]), "n_equity_common": len(eq)})
            if doc.get("report_date") != a.as_of or len(eq) < 900:
                report["status"] = "REJECTED_REPORT_DATE_OR_TOO_FEW_HOLDINGS"
            else:
                cur, hist, tick = name_index(store)
                members, unresolved = resolve(eq, cur, hist)
                rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
                rows, _ = chain.extend_listings(store, rd(a.listings) or {}, rd(a.plan))
                pool_ciks = {str(m.get("cik") or "").zfill(10) for m in rows.values()}
                extra = {f"r1000:{c}": {"yahoo": tick[c], "cik": c, "cik_method": v["method"], "reference_name": v["names"][0]}
                         for c, v in members.items() if c not in pool_ciks and tick.get(c)}
                no_ticker = sorted(c for c in members if c not in pool_ciks and not tick.get(c))
                ref = {"name": "RUSSELL1000_IWB_NPORT", "kind": "SEC_NPORT_FUND_HOLDINGS",
                       "source": f"SEC Form NPORT-P {chosen['accn']} ({a.series_name}), report date {a.as_of}",
                       "source_url": DOC_URL.format(cik=int(REGISTRANT_CIK), nodash=chosen["accn"].replace("-", ""), doc=chosen["doc"]),
                       "source_vintage": chosen["filed"], "as_of": a.as_of + "T00:00:00+00:00",
                       "membership_basis": "DATED_FUND_HOLDINGS", "reference_role": "SUPERSET_REFERENCE", "survivorship_risk": False,
                       "member_id_type": "CIK10", "members": sorted(members), "member_names": {c: v["names"] for c, v in members.items()},
                       "unresolved_holdings": unresolved, "members_not_in_pool_without_current_ticker": no_ticker,
                       "note": ("Russell 1000 fund holdings as reported to the SEC for the as_of date (filed after as_of: a dated "
                                "historical record, used for validation, not as information available at as_of).")}
                (GE / f"russell1000_nport_{a.as_of}.json").write_text(json.dumps(ref, indent=2) + "\n", encoding="utf-8")
                (GE / f"russell1000_extra_listings_{a.as_of}.json").write_text(json.dumps(extra, indent=2) + "\n", encoding="utf-8")
                report.update({"status": "OK", "n_members_cik": len(members), "n_unresolved": len(unresolved),
                               "n_extra": len(extra), "n_not_in_pool_without_current_ticker": len(no_ticker)})
    report["log"] = log
    (store.root / f"nport_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    print(json.dumps({k: v for k, v in report.items() if k != "log"}, indent=2)[:4000])


if __name__ == "__main__":
    main()
