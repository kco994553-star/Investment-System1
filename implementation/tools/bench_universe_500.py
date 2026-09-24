"""500-company SYNTHETIC benchmark. In-process compute only.

Measures wall-clock / peak Python heap / error behaviour of the real calculation
paths on 500 synthetic companies. Network I/O (SEC, Yahoo, FRED) is NOT measured:
this sandbox has no egress. Output is SYNTHETIC evidence, not a live run.

Usage: python tools/bench_universe_500.py [--n 500] [--out reports/x.json]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from investment_system.contracts.universe import EventKind  # noqa: E402
from investment_system.providers.memory import MemoryFundamentalsProvider  # noqa: E402
from investment_system.qgv.pipeline import AnalysisPipeline  # noqa: E402
from investment_system.universe.engine import UniverseEngine  # noqa: E402
from investment_system.universe.events import IncrementalEngine, make_event  # noqa: E402
from investment_system.universe.recon import daily_reconciliation  # noqa: E402
from investment_system.validation.file_store import FileTrackRecordStore  # noqa: E402
from investment_system.validation.historical import run_as_of  # noqa: E402
from investment_system.validation.records import ScopedTrackStore  # noqa: E402
from tests.synthetic_universe import bars, cid, companyfacts, raw, roster  # noqa: E402

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)


def measure(fn, repeats=3):
    times, peak, out = [], 0, None
    for _ in range(repeats):
        tracemalloc.start()
        t = time.perf_counter()
        out = fn()
        times.append(time.perf_counter() - t)
        peak = max(peak, tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
    return out, {"median_s": round(statistics.median(times), 4), "runs_s": [round(x, 4) for x in times], "peak_heap_mb": round(peak / 2**20, 2)}


def main(n: int, out_path: Path, bad: int = 5) -> dict:
    prov = MemoryFundamentalsProvider()
    for i in range(n):
        prov.put(raw(i, T0 - timedelta(days=30)))
    pipe = AnalysisPipeline(fundamentals=prov)
    calls = []

    def recompute(c, a):
        calls.append(c)
        r = prov.get(c, a)
        return None if r is None else pipe.analyze_raw(r, as_of=a)

    uni = UniverseEngine().snapshot(T0, roster=roster(n))
    res = {}

    def cold():
        e = IncrementalEngine()
        return e, e.full_batch(uni, T0, recompute)

    (eng, fb), res["live_full_batch"] = measure(cold)
    res["live_full_batch"]["qgv_recomputed"] = fb["qgv_recomputed"]
    res["live_full_batch"]["errors"] = len(fb["errors"])

    t1 = T0 + timedelta(days=1)
    prov.put(raw(7, t1, tag="b", bump=1.2))
    one = [make_event(EventKind.FUNDAMENTAL, t1, cid(7))]
    calls.clear()
    rep1, res["incremental_1_fundamental"] = measure(lambda: eng.process(one, t1, uni, recompute), repeats=3)
    res["incremental_1_fundamental"]["qgv_calls_per_run"] = len(calls) // 3
    for i in range(10):
        prov.put(raw(i * 37 % n, t1, tag="c", bump=1.1))
    mixed = (
        [make_event(EventKind.FUNDAMENTAL, t1, cid(i * 37 % n)) for i in range(10)]
        + [make_event(EventKind.PRICE, t1, cid(i)) for i in range(50)]
        + [make_event(EventKind.NEWS, t1, cid(i)) for i in range(20)]
        + [make_event(EventKind.MACRO, t1)]
    )
    calls.clear()
    rep2, res["incremental_mixed_81_events"] = measure(
        lambda: eng.process(mixed, t1, uni, recompute, recompute_technical=lambda c, a: {"c": c}, refresh_macro=lambda a: {}), repeats=3
    )
    res["incremental_mixed_81_events"]["qgv_calls_per_run"] = len(calls) // 3
    res["incremental_mixed_81_events"]["untouched_qgv"] = rep2["untouched_qgv"]

    _, res["leaderboard_rebuild"] = measure(lambda: eng.refresh_leaderboard(uni, t1))
    latest = lambda c, a: prov.get(c, a).stamp if prov.get(c, a) else None
    recon, res["daily_recon_stamp_check"] = measure(lambda: daily_reconciliation(t1, uni, eng.qgv, latest_stamp=latest))
    res["daily_recon_stamp_check"]["recompute_set"] = len(recon["recompute_set"])
    res["daily_recon_stamp_check"]["clean_skipped"] = recon["clean_skipped"]

    # PIT historical cross-section: parse -> PIT price -> peers -> QGV -> Technical ->
    # portfolio -> integration -> track store (file-backed). Some payloads malformed on purpose.
    ids = tuple(m.company_id for m in uni.members)
    listings = {m.company_id: {"yahoo": m.ticker, "cik": m.cik, "exchange": None} for m in uni.members}
    payloads = {c: companyfacts(i) for i, c in enumerate(ids)}
    for i in range(bad):
        payloads[cid(i * 97 % n)] = {"facts": "MALFORMED_ON_PURPOSE"}
    px = {c: bars(i, datetime(2024, 1, 1, tzinfo=UTC), 640) for i, c in enumerate(ids)}  # extends past as_of on purpose
    tmp = Path(tempfile.mkdtemp())

    def pit():
        store = ScopedTrackStore(FileTrackRecordStore(tmp / f"pit_{time.perf_counter_ns()}.json"))
        return run_as_of(T0, payloads, px, store, ids, listings=listings)

    row, res["pit_historical_run_as_of"] = measure(pit, repeats=1)
    leaks = 0
    for c, q in row["quality"].items():
        if q.get("pit_price") is None:
            continue
        expected = [b["price"] for b in px[c] if b["observed_at"] <= T0][-1]
        leaks += q["pit_price"] != expected
    res["pit_historical_run_as_of"].update({
        "pit_price_lookahead_violations": leaks,
        "names_scored": row["names"],
        "name_errors": len(row["name_errors"]),
        "gate": row["gate"],
        "future_bars_seen_not_used": row["lookahead"]["future_bars"],
    })

    report = {
        "kind": "UNIVERSE_500_BENCHMARK",
        "evidence_class": "SYNTHETIC",
        "n_companies": n,
        "measured": "in-process compute (+ local JSON track store for PIT path)",
        "not_measured": "network I/O to SEC/Yahoo/FRED (sandbox egress disabled)",
        "live_wall_clock_verified": False,
        "real_data_verified": False,
        "environment": {"python": platform.python_version(), "machine": platform.machine(), "cpus": os.cpu_count()},
        "generated_at": datetime.now(UTC).isoformat(),
        "results": res,
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default=str(ROOT / "reports" / "bench_universe_500_2026-09-23.json"))
    a = ap.parse_args()
    print(json.dumps(main(a.n, Path(a.out))["results"], indent=2))
