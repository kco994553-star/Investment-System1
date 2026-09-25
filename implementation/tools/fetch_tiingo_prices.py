"""Tiingo end-of-day fallback prices (user decision 2026-09-25) for eligible issuers / priced share classes
whose Yahoo chart has no bar on/before as_of (delisted after as_of, renamed, or truncated Yahoo payloads).

Tiingo 'close' is the raw (unadjusted) traded close, i.e. exactly the as-of price the market-cap formula
needs; the converted chart is stored under the replay id yahoo_chart:<SYM>:<range> with source_kind
TIINGO_DAILY_RAW, and audit_mcap_store.load_splits returns no post-as_of split factor for that kind (the
price is not split-adjusted back in time). The raw JSON is kept as tiingo_eod:<SYM>.

Before anything is written, a calibration compares Tiingo raw closes with Yahoo closes on the last session
on/before as_of for control symbols without post-as_of splits; every available control must agree within
0.5 % (fail-closed otherwise). The API token is read from TIINGO_API_KEY and sent only as an
'Authorization: Token ...' header: it never appears in URLs, manifests, logs or commits.

Usage:
  TIINGO_API_KEY=... python tools/fetch_tiingo_prices.py --store data/raw --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_price_bars  # noqa: E402

TIINGO_URL = "https://api.tiingo.com/tiingo/daily/{sym}/prices?startDate={start}&format=json"
CONTROLS = ("AAPL", "MSFT", "JPM", "XOM", "PG", "KO")
CALIBRATION_TOLERANCE = 0.005
SOURCE_KIND = "TIINGO_DAILY_RAW"
FETCHER = "tools/fetch_tiingo_prices.py v1"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_ftp_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tiingo_symbol(sym: str) -> str:
    return sym.strip().lower().replace(".", "-")


def parse_eod(body: bytes) -> list[tuple[datetime, float]]:
    """[(bar time 21:00 UTC of the session date, raw close)] from Tiingo JSON; [] for errors/non-lists."""
    try:
        rows = json.loads(body)
    except ValueError:
        return []
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        try:
            d = datetime.fromisoformat(str(r["date"])[:10]).replace(hour=21, tzinfo=timezone.utc)
            c = float(r["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if c > 0:
            out.append((d, c))
    return sorted(out)


def to_chart(bars: list[tuple[datetime, float]], symbol: str) -> bytes:
    return json.dumps({"chart": {"result": [{
        "meta": {"symbol": symbol, "currency": "USD", "source": "tiingo", "price_basis": "raw_close"},
        "timestamp": [int(d.timestamp()) for d, _ in bars],
        "indicators": {"quote": [{"close": [c for _, c in bars]}]}}], "error": None}}, separators=(",", ":")).encode()


def run(store_dir: Path, as_of: datetime, symbols: list[str], token: str | None, chart_range: str = "5y", sleep: float = 1.5) -> dict:
    frd = _load("fetch_real_data")
    store = RawDatasetStore(store_dir)
    frd._BLOCKED_HOSTS.clear()
    log: list[dict] = []
    report = {"kind": "TIINGO_FALLBACK_RUN", "as_of": as_of.isoformat(), "n_targets": len(symbols), "targets": symbols}
    if not token:
        report.update({"status": "NO_TIINGO_API_KEY", "written": []})
        return _finish(store, frd, report, log)
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    start = (as_of - timedelta(days=5 * 365)).date().isoformat()

    def fetch(sym: str) -> list[tuple[datetime, float]]:
        aid = f"tiingo_eod:{sym.upper()}"
        url = TIINGO_URL.format(sym=tiingo_symbol(sym), start=start)
        frd._fetch_one(store, aid, url, "TIINGO_EOD_JSON", frd.YAHOO_UA, log, False, headers=headers)
        frd._throttle(log, sleep)
        if store.has(aid) and not parse_eod(store.get_bytes(aid)) and not store.list_history(aid):
            # an empty '[]' reply (seen for EQR) is retried exactly once; the empty bytes stay in history/
            frd._fetch_one(store, aid, url, "TIINGO_EOD_JSON", frd.YAHOO_UA, log, True, headers=headers)
            frd._throttle(log, sleep)
        return parse_eod(store.get_bytes(aid)) if store.has(aid) else []

    calib = []
    for c in CONTROLS:
        tb = [b for b in fetch(c) if b[0] <= as_of]
        yb = [b for b in load_price_bars(store, c, chart_range) if b["observed_at"] <= as_of]
        if not tb or not yb:
            calib.append({"symbol": c, "status": "UNAVAILABLE"})
            continue
        y, t = yb[-1], tb[-1]
        diff = abs(t[1] - y["close"]) / y["close"]
        calib.append({"symbol": c, "tiingo_date": t[0].date().isoformat(), "tiingo_close": t[1],
                      "yahoo_date": y["observed_at"].date().isoformat(), "yahoo_close": y["close"], "rel_diff": diff,
                      "status": "OK" if diff <= CALIBRATION_TOLERANCE else "MISMATCH"})
    calibrated = sum(r["status"] == "OK" for r in calib) >= 3 and not any(r["status"] == "MISMATCH" for r in calib)
    results, written = {}, []
    for sym in symbols:
        bars = fetch(sym)
        if not bars:
            results[sym] = "NO_TIINGO_DATA"
        elif not any(d <= as_of for d, _ in bars):
            results[sym] = "NO_TIINGO_BAR_ON_OR_BEFORE_AS_OF"
        elif not calibrated:
            results[sym] = "NOT_WRITTEN_CALIBRATION_FAILED"
        elif any(b["observed_at"] <= as_of for b in load_price_bars(store, sym, chart_range)):
            results[sym] = "YAHOO_AS_OF_BAR_PRESENT"
        else:
            store.put(f"yahoo_chart:{sym.upper()}:{chart_range}", to_chart(bars, sym.upper()),
                      TIINGO_URL.format(sym=tiingo_symbol(sym), start=start), SOURCE_KIND, "application/json", FETCHER, 200,
                      notes="Tiingo raw daily close (not split-adjusted); fallback because Yahoo had no as-of bar")
            written.append(sym)
            results[sym] = "WRITTEN_TIINGO_FALLBACK"
    report.update({"status": "OK", "calibration": calib, "calibrated": calibrated, "tolerance": CALIBRATION_TOLERANCE,
                   "results": results, "written": written})
    return _finish(store, frd, report, log)


def _finish(store, frd, report: dict, log: list[dict]) -> dict:
    report["log"] = log
    report["egress_blocked_hosts"] = sorted(frd._BLOCKED_HOSTS)
    report["real_data_verified"] = False
    (store.root / f"tiingo_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=ROOT / "reports" / "gate_evidence" / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--cik-candidates", type=Path, default=ROOT / "reports" / "gate_evidence" / "delisted_cik_candidates_2024-12-31.json")
    ap.add_argument("--extra-listings", type=Path, action="append", default=[])
    a = ap.parse_args()
    chain = _load("run_top500_gate_chain")
    fsp = _load("fetch_stooq_prices")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    base = rd(a.listings) or {}
    for x in a.extra_listings:
        base.update(rd(x) or {})
    rows, _ = chain.extend_listings(store, base, rd(a.plan), chain.verify_cik_candidates(store, rd(a.cik_candidates)))
    rep = run(Path(a.store), d, fsp.target_symbols(store, rows, d, chain), os.environ.get("TIINGO_API_KEY"))
    print(json.dumps({k: v for k, v in rep.items() if k != "log"}, indent=2)[:6000])


if __name__ == "__main__":
    main()
