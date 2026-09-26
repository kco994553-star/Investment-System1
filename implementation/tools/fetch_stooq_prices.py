"""Stooq fallback prices for eligible issuers/classes with no as-of Yahoo bar (user decision 2026-09-25).

Network-enabled, reuses fetch_real_data's retry/backoff/throttle/resume. For each target symbol the raw
Stooq CSV is stored as stooq_csv:<SYM> (provenance). Before any Stooq price is used, a calibration
compares Stooq and Yahoo closes on the last trading day on/before as_of for control symbols; Stooq
prices are written only if every control agrees within CALIBRATION_TOLERANCE (same split-adjusted,
not dividend-adjusted convention as Yahoo 'close', which mcap_price relies on). Then, and only for
symbols whose Yahoo chart has no bar on/before as_of, the converted series is stored under the
existing replay id yahoo_chart:<SYM>:<range> with source_kind STOOQ_DAILY (the replaced Yahoo bytes
stay in history/). Same contract as tools/import_bulk_real_data.py (source is never relabelled Yahoo).

Usage:
  python tools/fetch_stooq_prices.py --store data/raw --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.ingestion.replay import load_price_bars, load_submissions_merged  # noqa: E402
from investment_system.providers.sec_cover_shares import class_symbols, parse_cover, select_filing  # noqa: E402

STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}.us&i=d"
CONTROLS = ("AAPL", "MSFT", "JPM", "XOM", "PG", "KO")
CALIBRATION_TOLERANCE = 0.005  # 0.5 %
FETCHER = "tools/fetch_stooq_prices.py v1"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_fsp_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stooq_symbol(sym: str) -> str:
    return sym.strip().lower().replace(".", "-")


def csv_close_on_or_before(body: bytes, as_of: datetime) -> tuple[str, float] | None:
    """(date, close) of the last Stooq row on/before as_of's calendar day minus one (the close of the
    last session that ended before as_of 00:00 UTC), mirroring the replay as_of filter."""
    best = None
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig", errors="replace"))):
        d, c = (row.get("Date") or "").strip(), (row.get("Close") or "").strip()
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=21, tzinfo=timezone.utc)
            px = float(c)
        except ValueError:
            continue
        if dt <= as_of and px > 0 and (best is None or d > best[0]):
            best = (d, px)
    return best


def is_stooq_csv(body: bytes) -> bool:
    head = body[:200].decode("utf-8-sig", errors="replace")
    return head.startswith("Date,") and "Close" in head.splitlines()[0]


def target_symbols(store: RawDatasetStore, rows: dict, as_of: datetime, chain) -> list[str]:
    """Primary lines of eligible issuers + priced cover classes whose Yahoo chart has no as-of bar."""
    listings, _ = chain.company_level_listings(store, rows)
    listings, _ = chain.eligibility_filter(store, listings, as_of)
    syms = {str(m.get("yahoo") or "") for m in listings.values()}
    for m in listings.values():
        c = str(m.get("cik") or "")
        if not c.isdigit():
            continue
        f = select_filing(load_submissions_merged(store, c.zfill(10), as_of)[0] or {}, as_of)
        aid = f"xbrl_instance:{c.zfill(10)}:{f['accn']}" if f else None
        if aid and store.has(aid):
            try:
                syms.update(s.replace(".", "-") for s in class_symbols(parse_cover(store.get_bytes(aid))).values())
            except Exception:  # noqa: BLE001
                pass
    return sorted(s for s in syms if s and not any(b["observed_at"] <= as_of for b in load_price_bars(store, s, "5y")))


def run(store_dir: Path, as_of: datetime, symbols: list[str], chart_range: str = "5y", sleep: float = 0.5) -> dict:
    frd = _load("fetch_real_data")
    ibr = _load("import_bulk_real_data")
    store = RawDatasetStore(store_dir)
    frd._BLOCKED_HOSTS.clear()
    log: list[dict] = []

    def fetch(sym: str) -> bytes | None:
        aid = f"stooq_csv:{sym.upper()}"
        frd._fetch_one(store, aid, STOOQ_URL.format(sym=stooq_symbol(sym)), "STOOQ_DAILY_CSV", frd.YAHOO_UA, log, False)
        frd._throttle(log, sleep)
        return store.get_bytes(aid) if store.has(aid) else None

    calib = []
    for c in CONTROLS:
        body = fetch(c)
        yb = [b for b in load_price_bars(store, c, chart_range) if b["observed_at"] <= as_of]
        s = csv_close_on_or_before(body, as_of) if body and is_stooq_csv(body) else None
        if not yb or s is None:
            calib.append({"symbol": c, "status": "UNAVAILABLE"})
            continue
        y = yb[-1]
        diff = abs(s[1] - y["close"]) / y["close"]
        calib.append({"symbol": c, "stooq_date": s[0], "stooq_close": s[1], "yahoo_date": y["observed_at"].date().isoformat(),
                      "yahoo_close": y["close"], "rel_diff": diff, "status": "OK" if diff <= CALIBRATION_TOLERANCE else "MISMATCH"})
    sample = next((store.get_bytes(f"stooq_csv:{c}") for c in CONTROLS
                   if store.has(f"stooq_csv:{c}") and not is_stooq_csv(store.get_bytes(f"stooq_csv:{c}"))), None)
    ok = [r for r in calib if r["status"] == "OK"]
    calibrated = len(ok) >= 3 and all(r["status"] in ("OK", "UNAVAILABLE") for r in calib)
    written, results = [], {}
    for sym in symbols:
        body = fetch(sym)
        if not body or not is_stooq_csv(body):
            results[sym] = "NO_STOOQ_DATA"
            continue
        if csv_close_on_or_before(body, as_of) is None:
            results[sym] = "NO_STOOQ_BAR_ON_OR_BEFORE_AS_OF"
            continue
        if not calibrated:
            results[sym] = "NOT_WRITTEN_CALIBRATION_FAILED"
            continue
        aid = f"yahoo_chart:{sym.upper()}:{chart_range}"
        if any(b["observed_at"] <= as_of for b in load_price_bars(store, sym, chart_range)):
            results[sym] = "YAHOO_AS_OF_BAR_PRESENT"
            continue
        chart = ibr._stooq_to_chart(body, sym.upper())
        store.put(aid, chart, STOOQ_URL.format(sym=stooq_symbol(sym)), "STOOQ_DAILY", "application/json", FETCHER, 200,
                  notes="Stooq daily close converted to the replay chart envelope; fallback because Yahoo had no as-of bar")
        written.append(sym)
        results[sym] = "WRITTEN_STOOQ_FALLBACK"
    report = {"kind": "STOOQ_FALLBACK_RUN", "as_of": as_of.isoformat(), "calibration": calib, "calibrated": calibrated,
              "non_csv_response_head": sample[:600].decode("utf-8", errors="replace") if sample else None,
              "tolerance": CALIBRATION_TOLERANCE, "n_targets": len(symbols), "results": results, "written": written,
              "log": log, "egress_blocked_hosts": sorted(frd._BLOCKED_HOSTS), "real_data_verified": False}
    (store_dir / f"stooq_run_{int(datetime.now(timezone.utc).timestamp())}.json").write_text(json.dumps(report, indent=2))
    frd.write_store_index(store)
    return report


def resolve_cik_candidates(ge: Path, as_of: str) -> Path:
    """Point-in-time CIK corrections are per as_of (e.g. BLK holding-company reorganisation 2024-10-01): use the
    dated file when it exists, else the 2024-12-31 file (never guessed)."""
    return next(p for p in (ge / f"delisted_cik_candidates_{as_of}.json", ge / "delisted_cik_candidates_2024-12-31.json")
                if p.exists() or p.name.endswith("2024-12-31.json"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--as-of", default="2024-12-31")
    ap.add_argument("--listings", type=Path, default=ROOT / "reports" / "us_ingested_facts_listings.json")
    ap.add_argument("--plan", type=Path, default=ROOT / "reports" / "gate_evidence" / "missing_large_cap_priority_plan_2024-12-31.json")
    ap.add_argument("--cik-candidates", type=Path, help="default delisted_cik_candidates_<as_of>.json, else the 2024-12-31 file")
    ap.add_argument("--extra-listings", type=Path, action="append", default=[])
    a = ap.parse_args()
    if a.cik_candidates is None:
        a.cik_candidates = resolve_cik_candidates(ROOT / "reports" / "gate_evidence", a.as_of)
    chain = _load("run_top500_gate_chain")
    store = RawDatasetStore(a.store)
    d = datetime.fromisoformat(a.as_of + "T00:00:00+00:00")
    rd = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else None  # noqa: E731
    base = rd(a.listings) or {}
    for x in a.extra_listings:
        base.update(rd(x) or {})
    rows, _ = chain.extend_listings(store, base, rd(a.plan), chain.verify_cik_candidates(store, rd(a.cik_candidates)))
    rep = run(Path(a.store), d, target_symbols(store, rows, d, chain))
    print(json.dumps({k: v for k, v in rep.items() if k != "log"}, indent=2))


if __name__ == "__main__":
    main()
