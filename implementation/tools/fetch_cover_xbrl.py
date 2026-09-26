"""Network-enabled companion to fetch_real_data.py: cover-page XBRL instances for share classes.

For every issuer that needs it (shares unresolved from companyfacts, or more than one
listed line under one CIK), fetch the XBRL instance of the latest 10-K/10-Q filed on or
before --as-of, as artifact xbrl_instance:<CIK10>:<accession>. Then fetch Yahoo charts
(+ split events) for any class TradingSymbol not yet in the store, so class prices exist.
Reuses fetch_real_data's retry/backoff, egress breaker, throttle and resume (present ids skipped).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" \
  python tools/fetch_cover_xbrl.py --store data/raw --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_companyfacts, load_submissions, load_submissions_merged, submission_page_id  # noqa: E402
from investment_system.providers.sec_cover_shares import class_symbols, instance_name, pages_needed, parse_cover, select_filing  # noqa: E402
from investment_system.universe.sources import pit_shares  # noqa: E402

ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{doc}"
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fcx_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _chain():
    """The gate chain module (loaded directly: its share checks and ticker normalisation are shared, not duplicated)."""
    spec = importlib.util.spec_from_file_location("_fcx_chain", ROOT / "tools" / "run_top500_gate_chain.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def instance_id(cik10: str, accn: str) -> str:
    return f"xbrl_instance:{cik10}:{accn}"


def needs_cover(store: RawDatasetStore, row_listings: dict, as_of: datetime) -> list[str]:
    """CIK10s whose shares are unresolved in companyfacts or that have >1 listed line."""
    lines: dict[str, int] = {}
    for m in row_listings.values():
        if m.get("cik"):
            c = str(int(str(m["cik"]))).zfill(10)
            lines[c] = lines.get(c, 0) + 1
    chain = _chain()
    out = []
    for c, n in sorted(lines.items()):
        cf = load_companyfacts(store, c)
        sh = pit_shares(cf, as_of) if cf is not None else None
        # a zero/negative companyfacts count (e.g. a converted class reported alone) is unresolved too;
        # so is a count not filed with the latest periodic report (per-class facts dropped) or one failing the scale check
        if (n > 1 or sh is None or sh["status"] != "OK" or not (sh["shares"] or 0) > 0
                or chain.share_fact_stale(store, c, sh, as_of) or chain.share_scale_check(cf, as_of, sh["shares"])["flagged"]):
            out.append(c)
    return out


def fetch_submission_pages(store: RawDatasetStore, ciks: list[str], as_of: datetime, log: list[dict], sleep: float = 0.15) -> int:
    """Older submissions pages for issuers whose 'recent' list starts after as_of (large filers)."""
    frd = _load("fetch_real_data")
    n = 0
    for c in ciks:
        for name in pages_needed(load_submissions(store, c) or {}, as_of):
            frd._fetch_one(store, submission_page_id(name), SUBMISSIONS_PAGE_URL.format(name=name), "SEC_SUBMISSIONS_PAGE", frd.UA, log, False)
            frd._throttle(log, sleep)
            n += 1
    return n


def run(store_dir: Path, as_of: datetime, ciks: list[str], chart_range: str = "5y", sleep: float = 0.15,
        page_ciks: list[str] | None = None) -> dict:
    frd = _load("fetch_real_data")
    store = RawDatasetStore(store_dir)
    frd._BLOCKED_HOSTS.clear()
    log: list[dict] = []
    picked = {}
    n_pages = fetch_submission_pages(store, sorted(set((page_ciks or []) + list(ciks))), as_of, log, sleep)
    for c in ciks:
        sub, _ = load_submissions_merged(store, c)
        f = select_filing(sub or {}, as_of)
        if f is None:
            log.append({"artifact_id": f"xbrl_instance:{c}", "status": "NO_PERIODIC_FILING_BEFORE_AS_OF"})
            continue
        accn = f["accn"].replace("-", "")
        aid = instance_id(c, f["accn"])
        url = ARCHIVE_URL.format(cik=int(c), accn=accn, doc=instance_name(f["primary_document"]))
        frd._fetch_one(store, aid, url, "SEC_XBRL_INSTANCE", frd.UA, log, False)
        frd._throttle(log, sleep)
        picked[c] = {**f, "artifact_id": aid}
    symbols = set()
    chain = _chain()
    for c, f in picked.items():
        if store.has(f["artifact_id"]):
            try:
                # 'BFB' on the cover is the issuer's SEC ticker 'BF-B': fetch the chart under the ticker (same CIK only)
                symbols.update(chain.same_cik_ticker(store, c, s) or s for s in class_symbols(parse_cover(store.get_bytes(f["artifact_id"]))).values())
            except Exception as e:  # noqa: BLE001 - malformed instance stays a logged gap
                log.append({"artifact_id": f["artifact_id"], "status": f"PARSE_ERROR_{type(e).__name__}"})
    for sym in sorted(s.replace(".", "-") for s in symbols):
        for aid, url, kind in ((f"yahoo_chart:{sym}:{chart_range}", frd.YAHOO_CHART_URL, "YAHOO_CHART"),
                               (f"yahoo_events:{sym}:{chart_range}", frd.YAHOO_EVENTS_URL, "YAHOO_SPLIT_EVENTS")):
            frd._fetch_one(store, aid, url.format(symbol=sym, range=chart_range), kind, frd.YAHOO_UA, log, False)
            frd._throttle(log, sleep)
    ok = sum(1 for r in log if r["status"] in ("OK", "SKIPPED_ALREADY_PRESENT"))
    report = {"kind": "COVER_XBRL_INGEST_RUN", "as_of": as_of.isoformat(), "n_issuers": len(ciks), "n_submission_pages": n_pages,
              "n_filings": len(picked), "n_class_symbols": len(symbols), "n_requested": len(log), "n_ok": ok,
              "n_failed": len(log) - ok, "filings": picked, "log": log,
              "egress_blocked_hosts": sorted(frd._BLOCKED_HOSTS), "real_data_verified": False}
    (store_dir / f"cover_xbrl_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=ROOT / "reports" / "gate_evidence" / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--cik-candidates", type=Path, default=ROOT / "reports" / "gate_evidence" / "delisted_cik_candidates_2024-12-31.json")
    ap.add_argument("--chart-range", default="5y")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--extra-listings", type=Path, action="append", default=[])
    a = ap.parse_args()
    chain = _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    cand = chain.verify_cik_candidates(store, rd(a.cik_candidates))
    base = rd(a.listings) or {}
    for x in a.extra_listings:
        base.update(rd(x) or {})
    rows, _ = chain.extend_listings(store, base, rd(a.plan), cand)
    all_ciks = sorted({str(int(str(m["cik"]))).zfill(10) for m in rows.values() if str(m.get("cik") or "").isdigit()})
    rep = run(Path(a.store), d, needs_cover(store, rows, d), a.chart_range, a.sleep, page_ciks=all_ciks)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("log", "filings")}, indent=2))


if __name__ == "__main__":
    main()
