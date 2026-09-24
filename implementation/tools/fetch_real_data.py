"""Network-enabled runner: fetches SEC/Yahoo data into ingestion/RawDatasetStore.

NOT RUN in the 2026-09-23 Claude sessions: this sandbox's bash_tool has no
outbound HTTP (egress allowlist blocks every external host — confirmed with
curl against sec.gov, github raw, Yahoo, FRED, all returning "Host not in
allowlist"; raw TCP connect to port 443 succeeds, so it is a deliberate proxy
policy, not a DNS/firewall defect). Run this on a machine/session with real
egress. It is deliberately separate from everything under validation/qgv/
technical/macro, which import no networking library and can replay whatever
this writes with zero network access (see ingestion/replay.py).

Writes, for each requested company:
  companyfacts:<CIK10>, submissions:<CIK10>, yahoo_chart:<SYMBOL>:<range>
plus sec_tickers (company_tickers.json). Respects SEC's fair-access guidance
(descriptive User-Agent, throttled requests) and does not invent data for
names that 404 or time out — those stay absent (MISSING downstream).

Usage:
  INVESTMENT_SYSTEM_SEC_UA="Name contact@example.com" \
  python tools/fetch_real_data.py --store data/raw --ciks 0000320193,0001045810 \
      --symbols AAPL,NVDA [--chart-range 5y] [--skip-tickers] [--sleep 0.15]

  # C-21 priority plan (CIK-ready names first, then ticker->CIK via sec_tickers):
  python tools/fetch_real_data.py --store data/raw \
      --plan reports/gate_evidence/missing_large_cap_priority_plan_2024-12-31.json

2026-09-25 (Claude Code r4) additive changes, existing behaviour unchanged:
  * transient failures (HTTP 429/5xx, timeouts, resets) are retried with
    exponential backoff (2s, 4s, 8s, 16s; Retry-After honoured). HTTP 4xx other
    than 429 is not retried.
  * an egress-proxy policy denial ("Tunnel connection failed: 403") is never
    retried; the host is marked blocked and remaining artifacts for that host
    are logged EGRESS_BLOCKED without sending further requests.
  * --plan reads a missing-large-cap priority plan; names without a CIK are
    resolved from the store's sec_tickers artifact (universe.resolve's
    current_ticker_map). Unresolved names are reported, never invented.
  * every run rewrites <store>/STORE_INDEX.json (id, sha256, bytes, url,
    fetched_at per artifact) so a handoff can ship the index without blobs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.universe.resolve import current_ticker_map  # noqa: E402

FETCHER = "tools/fetch_real_data.py v1"
UA = os.environ.get("INVESTMENT_SYSTEM_SEC_UA", "Investment-System1 research contact@example.invalid")
YAHOO_UA = os.environ.get("INVESTMENT_SYSTEM_YAHOO_UA", "Mozilla/5.0 InvestmentSystem1Research/0.2")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range}"


def _get(url: str, ua: str) -> tuple[bytes, int, str]:
    req = Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urlopen(req, timeout=20) as resp:
        return resp.read(), resp.status, resp.headers.get("Content-Type", "application/octet-stream")


RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BACKOFF_BASE = 2.0
_BLOCKED_HOSTS: set[str] = set()


def _is_egress_denial(e: BaseException) -> bool:
    reason = getattr(e, "reason", e)
    return "Tunnel connection failed: 403" in str(reason) or "Host not in allowlist" in str(reason)


def _get_with_retry(url: str, ua: str) -> tuple[bytes, int, str]:
    delay = BACKOFF_BASE
    for attempt in range(MAX_RETRIES + 1):
        try:
            return _get(url, ua)
        except HTTPError as e:
            if e.code not in RETRY_STATUS or attempt == MAX_RETRIES:
                raise
            ra = e.headers.get("Retry-After") if e.headers else None
            wait = float(ra) if ra and str(ra).isdigit() else delay
        except (URLError, TimeoutError, OSError) as e:
            if _is_egress_denial(e) or attempt == MAX_RETRIES:
                raise
            wait = delay
        time.sleep(wait)
        delay *= 2
    raise AssertionError("unreachable")


def _fetch_one(store: RawDatasetStore, artifact_id: str, url: str, source_kind: str, ua: str, log: list[dict], refresh: bool = False) -> bool:
    if store.has(artifact_id) and not refresh:
        log.append({"artifact_id": artifact_id, "status": "SKIPPED_ALREADY_PRESENT"})
        return True
    host = urlparse(url).hostname or ""
    if host in _BLOCKED_HOSTS:
        log.append({"artifact_id": artifact_id, "status": "EGRESS_BLOCKED", "url": url})
        return False
    try:
        body, status, ctype = _get_with_retry(url, ua)
    except HTTPError as e:
        log.append({"artifact_id": artifact_id, "status": f"HTTP_{e.code}", "url": url})
        return False
    except (URLError, TimeoutError, OSError) as e:
        if _is_egress_denial(e):
            _BLOCKED_HOSTS.add(host)
            log.append({"artifact_id": artifact_id, "status": "EGRESS_BLOCKED", "url": url, "error": str(getattr(e, "reason", e))})
            return False
        log.append({"artifact_id": artifact_id, "status": f"ERROR_{type(e).__name__}", "url": url})
        return False
    store.put(artifact_id, body, url, source_kind, ctype, FETCHER, http_status=status)
    log.append({"artifact_id": artifact_id, "status": "OK", "bytes": len(body)})
    return True


def yahoo_symbol(ticker: str) -> str:
    """Share-class tickers: S&P/SEC 'BRK.B' is Yahoo 'BRK-B'."""
    return ticker.strip().upper().replace(".", "-")


def plan_targets(store: RawDatasetStore, plan: dict) -> tuple[list[str], list[str], list[dict]]:
    """(ciks, yahoo symbols, resolution log) for a missing-large-cap priority plan.
    Names without a CIK are resolved from the stored sec_tickers artifact only."""
    tmap: dict[str, str] = {}
    if store.has("sec_tickers"):
        tmap = current_ticker_map(json.loads(store.get_bytes("sec_tickers")))
    ciks, symbols, resolution = [], [], []
    for row in plan.get("priority_fetch_plan", []):
        t = str(row.get("ticker") or "").strip().upper()
        cik = row.get("cik")
        method = "PLAN_CIK" if cik else None
        if not cik:
            cik = tmap.get(t) or tmap.get(t.replace(".", "-"))
            method = "SEC_TICKERS_CURRENT" if cik else "UNRESOLVED"
        resolution.append({"ticker": t, "cik": cik, "method": method})
        if cik:
            ciks.append(str(cik))
        if t:
            symbols.append(yahoo_symbol(t))
    return ciks, symbols, resolution


def write_store_index(store: RawDatasetStore) -> dict:
    rows = []
    for aid in store.list_ids():
        m = store.get_manifest(aid)
        rows.append({k: m.get(k) for k in ("artifact_id", "source_kind", "source_url", "sha256", "bytes", "fetched_at", "http_status")})
    index = {"kind": "RAW_DATASET_STORE_INDEX", "store_dir": str(store.root), "n_artifacts": len(rows),
             "n_blobs_on_disk": sum(1 for r in rows if store.has(str(r.get("artifact_id") or ""))), "artifacts": rows,
             "note": "Reproducible manifest: re-fetch any artifact from source_url and compare sha256."}
    (store.root / "STORE_INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def run(store_dir: Path, ciks: list[str], symbols: list[str], chart_range: str, sleep: float, skip_tickers: bool, refresh: bool = False,
        plan: dict | None = None) -> dict:
    store = RawDatasetStore(store_dir)
    _BLOCKED_HOSTS.clear()
    log: list[dict] = []
    resolution: list[dict] | None = None
    if not skip_tickers:
        _fetch_one(store, "sec_tickers", SEC_TICKERS_URL, "SEC_TICKERS", UA, log, refresh)
        time.sleep(sleep)
    if plan is not None:
        pc, ps, resolution = plan_targets(store, plan)
        ciks = list(dict.fromkeys(list(ciks) + pc))
        symbols = list(dict.fromkeys(list(symbols) + ps))
    for cik in ciks:
        c10 = str(int(cik)).zfill(10)
        _fetch_one(store, f"companyfacts:{c10}", SEC_FACTS_URL.format(cik=c10), "SEC_COMPANYFACTS", UA, log, refresh)
        time.sleep(sleep)
        _fetch_one(store, f"submissions:{c10}", SEC_SUBS_URL.format(cik=c10), "SEC_SUBMISSIONS", UA, log, refresh)
        time.sleep(sleep)
    for sym in symbols:
        aid = f"yahoo_chart:{sym.upper()}:{chart_range}"
        _fetch_one(store, aid, YAHOO_CHART_URL.format(symbol=sym.upper(), range=chart_range), "YAHOO_CHART", YAHOO_UA, log, refresh)
        time.sleep(sleep)
    ok = sum(1 for r in log if r["status"] in ("OK", "SKIPPED_ALREADY_PRESENT"))
    report = {
        "kind": "REAL_DATA_INGEST_RUN",
        "store_dir": str(store_dir),
        "n_requested": len(log),
        "n_ok": ok,
        "n_failed": len(log) - ok,
        "log": log,
        "egress_blocked_hosts": sorted(_BLOCKED_HOSTS),
        "plan_resolution": resolution,
        "real_data_verified": False,  # fetching is not verifying; that happens downstream
        "note": "raw bytes only; ingestion time != PIT availability (see ingestion/manifest.py)",
    }
    (store_dir / f"ingest_run_{int(time.time())}.json").write_text(json.dumps(report, indent=2))
    write_store_index(store)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--ciks", default="")
    ap.add_argument("--symbols", default="")
    ap.add_argument("--chart-range", default="5y")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--skip-tickers", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-fetch existing ids; previous bytes+manifest are archived under store/history")
    ap.add_argument("--plan", type=Path, help="missing-large-cap priority plan JSON (reports/gate_evidence/missing_large_cap_priority_plan_*.json)")
    a = ap.parse_args()
    ciks = [c.strip() for c in a.ciks.split(",") if c.strip()]
    symbols = [s.strip() for s in a.symbols.split(",") if s.strip()]
    plan = json.loads(a.plan.read_text(encoding="utf-8")) if a.plan else None
    print(json.dumps(run(Path(a.store), ciks, symbols, a.chart_range, a.sleep, a.skip_tickers, a.refresh, plan), indent=2))
