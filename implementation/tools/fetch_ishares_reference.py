"""Independent dated PIT large-cap reference for the Top-500 Sufficiency Gate (user decision 2026-09-25).

Fetches the iShares Russell 1000 ETF (IWB) holdings file for --as-of (asOfDate=YYYYMMDD), keeps the
raw bytes as ishares_holdings:IWB:<YYYYMMDD>, and accepts it only if the file's own "Fund Holdings as of"
date equals as_of (fail-closed otherwise). Writes:
  reports/gate_evidence/russell1000_iwb_<as_of>.json   reference (reference_role SUPERSET_REFERENCE)
  reports/gate_evidence/russell1000_extra_listings_<as_of>.json   members not yet in the pool, with CIKs
CIK resolution for members not in the pool: current SEC company_tickers (sec_tickers artifact), then, for
names delisted since, a UNIQUE normalised-name match in SEC cik-lookup-data.txt (artifact sec_cik_lookup).
Candidates found by name are only candidates: the gate chain's PIT eligibility (submissions filed <= as_of)
still has to accept them. Unresolved members are reported, never guessed.

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" python tools/fetch_ishares_reference.py --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.universe.resolve import current_ticker_map  # noqa: E402

IWB_URL = ("https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/1467271812596.ajax"
           "?fileType=csv&fileName=IWB_holdings&dataType=fund&asOfDate={ymd}")
CIK_LOOKUP_URL = "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
GE = ROOT / "reports" / "gate_evidence"
SUFFIXES = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "LLC", "LP", "HOLDINGS", "HOLDING",
            "GROUP", "THE", "SA", "NV", "AG", "CLASS", "A", "B", "C", "REIT", "TRUST", "INCORPORATED"}


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fir_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nodot(t) -> str:
    """iShares drops the class separator (BRKB); SEC/Yahoo use BRK-B / BRK.B."""
    return re.sub(r"[^A-Z0-9]", "", str(t or "").upper())


def norm_name(n: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]", " ", str(n or "").upper()).split()
    return " ".join(w for w in words if w not in SUFFIXES)


def parse_holdings(body: bytes) -> tuple[str | None, list[dict]]:
    """(holdings-as-of date ISO, equity rows). iShares CSV: preamble lines, then a header row starting 'Ticker'."""
    text = body.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    as_of = None
    for ln in lines[:15]:
        if ln.lower().startswith("fund holdings as of"):
            raw = ln.split(",", 1)[1].strip().strip('"').strip()
            for fmt in ("%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
                try:
                    as_of = datetime.strptime(raw, fmt).date().isoformat()
                    break
                except ValueError:
                    continue
    start = next((i for i, ln in enumerate(lines) if ln.startswith("Ticker,")), None)
    if start is None:
        return as_of, []
    rows = []
    for r in csv.DictReader(io.StringIO("\n".join(lines[start:]))):
        if (r.get("Asset Class") or "").strip() != "Equity":
            continue
        t = (r.get("Ticker") or "").strip()
        if t and t != "-":
            rows.append({"ticker": t, "name": (r.get("Name") or "").strip(), "location": (r.get("Location") or "").strip(),
                         "exchange": (r.get("Exchange") or "").strip()})
    return as_of, rows


def parse_cik_lookup(body: bytes) -> dict[str, set[str]]:
    """normalised name -> CIK10 set, from lines 'NAME:0000000000:'."""
    out: dict[str, set[str]] = {}
    for ln in body.decode("latin-1", errors="replace").splitlines():
        parts = ln.rsplit(":", 2)
        if len(parts) < 3 or not parts[1].strip().isdigit():
            continue
        out.setdefault(norm_name(parts[0]), set()).add(parts[1].strip().zfill(10))
    return out


def build(store: RawDatasetStore, as_of: str, holdings: list[dict], pool_symbols: set[str], source_vintage: str) -> tuple[dict, dict, dict]:
    tmap = current_ticker_map(json.loads(store.get_bytes("sec_tickers"))) if store.has("sec_tickers") else {}
    by_nodot = {nodot(t): (t, c) for t, c in tmap.items()}
    pool_nodot = {nodot(s) for s in pool_symbols}
    lookup = parse_cik_lookup(store.get_bytes("sec_cik_lookup")) if store.has("sec_cik_lookup") else {}
    extra, resolution = {}, {"IN_POOL": 0, "SEC_TICKERS_CURRENT": 0, "SEC_CIK_LOOKUP_UNIQUE_NAME": 0, "UNRESOLVED": []}
    for h in holdings:
        k = nodot(h["ticker"])
        if k in pool_nodot:
            resolution["IN_POOL"] += 1
            continue
        hit = by_nodot.get(k)
        if hit:
            extra[f"r1000:{k.lower()}"] = {"yahoo": hit[0].replace(".", "-"), "cik": hit[1], "cik_method": "SEC_TICKERS_CURRENT",
                                          "reference_name": h["name"]}
            resolution["SEC_TICKERS_CURRENT"] += 1
            continue
        ciks = lookup.get(norm_name(h["name"])) or set()
        if len(ciks) == 1:
            extra[f"r1000:{k.lower()}"] = {"yahoo": h["ticker"].upper(), "cik": next(iter(ciks)),
                                          "cik_method": "SEC_CIK_LOOKUP_UNIQUE_NAME", "reference_name": h["name"]}
            resolution["SEC_CIK_LOOKUP_UNIQUE_NAME"] += 1
        else:
            resolution["UNRESOLVED"].append({"ticker": h["ticker"], "name": h["name"], "name_matches": len(ciks)})
    ref = {"name": "RUSSELL1000_IWB_HOLDINGS", "kind": "DATED_FUND_HOLDINGS",
           "source": "iShares Russell 1000 ETF (IWB) holdings file, asOfDate=" + as_of.replace("-", ""),
           "source_url": IWB_URL.format(ymd=as_of.replace("-", "")), "source_vintage": source_vintage,
           "as_of": as_of + "T00:00:00+00:00", "membership_basis": "DATED_FUND_HOLDINGS",
           "reference_role": "SUPERSET_REFERENCE", "survivorship_risk": False,
           "members": [h["ticker"] for h in holdings], "member_names": {h["ticker"]: h["name"] for h in holdings},
           "member_locations": {h["ticker"]: h["location"] for h in holdings},
           "note": ("Russell 1000 = the ~1000 largest US companies by market cap (FTSE Russell, reconstituted annually, "
                    "IPO additions quarterly); used as a SUPERSET of the US top 500: every member must be in the pool "
                    "and rankable (or excluded by the documented eligibility rule); members may rank below 500.")}
    return ref, extra, resolution


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=GE / "missing_large_cap_priority_plan_2024-12-31.json")
    a = ap.parse_args()
    frd = _load("fetch_real_data")
    chain = _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    log: list[dict] = []
    ymd = a.as_of.replace("-", "")
    aid = f"ishares_holdings:IWB:{ymd}"
    frd._fetch_one(store, aid, IWB_URL.format(ymd=ymd), "ISHARES_FUND_HOLDINGS", frd.YAHOO_UA, log, False)
    frd._fetch_one(store, "sec_cik_lookup", CIK_LOOKUP_URL, "SEC_CIK_LOOKUP", frd.UA, log, False)
    report = {"kind": "ISHARES_REFERENCE_RUN", "as_of": a.as_of, "log": log}
    if not store.has(aid):
        report["status"] = "HOLDINGS_NOT_FETCHED"
    else:
        file_as_of, holdings = parse_holdings(store.get_bytes(aid))
        report.update({"file_as_of": file_as_of, "n_equity_rows": len(holdings)})
        if file_as_of != a.as_of or len(holdings) < 900:
            report["status"] = "REJECTED_DATE_MISMATCH_OR_TOO_FEW_ROWS"  # never use a holdings file for another date
        else:
            rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
            rows, _ = chain.extend_listings(store, rd(a.listings) or {}, rd(a.plan))
            vintage = str(store.get_manifest(aid).get("fetched_at", ""))[:10]
            ref, extra, res = build(store, a.as_of, holdings, {m.get("yahoo") for m in rows.values()}, vintage)
            (GE / f"russell1000_iwb_{a.as_of}.json").write_text(json.dumps(ref, indent=2) + "\n", encoding="utf-8")
            (GE / f"russell1000_extra_listings_{a.as_of}.json").write_text(json.dumps(extra, indent=2) + "\n", encoding="utf-8")
            report.update({"status": "OK", "resolution": {**res, "n_unresolved": len(res["UNRESOLVED"])}, "n_extra": len(extra)})
    (store.root / f"ishares_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    print(json.dumps({k: v for k, v in report.items() if k != "log"}, indent=2)[:4000])


if __name__ == "__main__":
    main()
