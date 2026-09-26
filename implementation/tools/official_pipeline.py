"""Official US Market-Cap Top 500 PIT -> real single_as_of -> >=3-date walk-forward -> 500-company real benchmark.

Runs ONLY for as_of dates whose gate chain evidence (reports/gate_evidence/gate_chain_<as_of>_real_gha.json) has
official_top500_declared = true AND gate_snapshot_consistency.passed = true. Each date is verified independently by its own
gate run; nothing here re-ranks. The Official snapshot is rebuilt with universe.sources.official_mcap500_snapshot from the
gate-audited candidates stored in that evidence and must reproduce the gate's top 500 exactly (members and order).

Existing engines are used unchanged: validation.vertical_slice.run_vertical_slice_from_store (single_as_of) and
run_walk_forward_from_store. The benchmark measures wall-clock / peak heap / error counts of those real paths on the
Official 500 real companies from the raw store (the same measurements as tools/bench_universe_500.py, which is SYNTHETIC),
plus the network fetch statistics recorded by the ingestion runs.

Usage:
  python tools/official_pipeline.py --store data/raw --dates 2024-06-30,2024-09-30,2024-12-31 --final-horizon 2025-03-31
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.universe.sources import official_mcap500_snapshot  # noqa: E402
from investment_system.validation.vertical_slice import run_vertical_slice_from_store, run_walk_forward_from_store  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s if "T" in s else s + "T00:00:00+00:00")


def load_official(as_of: str) -> tuple[object | None, dict]:
    """(Official UniverseSnapshot or None, status) for one as_of, from its own gate evidence."""
    p = GE / f"gate_chain_{as_of}_real_gha.json"
    if not p.exists():
        return None, {"as_of": as_of, "status": "NO_GATE_EVIDENCE"}
    ev = json.loads(p.read_text(encoding="utf-8"))
    cons = ev.get("gate_snapshot_consistency") or {}
    if not ev.get("official_top500_declared") or not cons.get("passed") or not ev.get("official_snapshot_candidates"):
        return None, {"as_of": as_of, "status": "NOT_OFFICIAL", "official_blockers": ev.get("official_blockers"),
                      "consistency_passed": cons.get("passed")}
    cands = []
    for c in ev["official_snapshot_candidates"]:
        c = dict(c)
        for k in ("shares_available_at", "price_observed_at"):
            c[k] = _dt(c[k]) if c.get(k) else None
        cands.append(c)
    snap, rep = official_mcap500_snapshot(cands, _dt(as_of), source="GATE_AUDITED_CANDIDATES")
    gate_ids = [r["company_id"] for r in ev["top500"]]
    if list(snap.ids()) != gate_ids:
        return None, {"as_of": as_of, "status": "REBUILT_SNAPSHOT_DIFFERS_FROM_GATE"}
    return snap, {"as_of": as_of, "status": "OFFICIAL", "universe_id": snap.universe_id, "n_members": len(snap.members),
                  "cutoff_mcap": rep.get("cutoff_mcap"), "gate_evidence": p.name}


def _measure(fn):
    tracemalloc.start()
    t = time.perf_counter()
    out = fn()
    dt = time.perf_counter() - t
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return out, {"wall_s": round(dt, 3), "peak_heap_mb": round(peak / 2**20, 2)}


def network_stats(store_dir: Path) -> dict:
    """Request counts / statuses recorded by the ingestion runs (fetch_real_data and companions)."""
    counts: dict[str, int] = {}
    n_runs = 0
    for f in glob.glob(str(store_dir / "*_run_*.json")):
        try:
            rep = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        n_runs += 1
        for r in rep.get("log") or []:
            counts[str(r.get("status"))] = counts.get(str(r.get("status")), 0) + 1
    return {"n_ingestion_run_reports": n_runs, "request_status_counts": counts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--dates", required=True, help="comma-separated as_of dates, each with its own passing gate run")
    ap.add_argument("--final-horizon", required=True, help="outcome date for the last as_of")
    a = ap.parse_args()
    dates = sorted(d.strip() for d in a.dates.split(",") if d.strip())
    store = RawDatasetStore(a.store)
    snaps, status = {}, []
    for d in dates:
        s, st = load_official(d)
        status.append(st)
        if s is not None:
            snaps[d] = s
    out = {"kind": "OFFICIAL_PIPELINE_RUN", "dates": dates, "final_horizon": a.final_horizon, "per_date": status,
           "real_data_verified": False}
    if len(snaps) != len(dates) or len(dates) < 3:
        out["status"] = "BLOCKED_NOT_ALL_DATES_OFFICIAL" if len(dates) >= 3 else "BLOCKED_FEWER_THAN_3_DATES"
    else:
        horizons = dates[1:] + [a.final_horizon]
        singles, timings, errors = [], [], 0
        for d, h in zip(dates, horizons):
            res, m = _measure(lambda d=d, h=h: run_vertical_slice_from_store(store, _dt(d), _dt(h), snaps[d]))
            errors += len(res.get("name_errors") or {})
            timings.append(m)
            singles.append({k: res[k] for k in ("as_of", "horizon_as_of", "universe_id", "universe_kind", "official_universe",
                                                "universe_policy", "membership_basis", "survivorship_risk", "n_selected",
                                                "equal_weight_realized", "rule_id", "rule_status")}
                           | {"n_universe": len(res["universe"]), "n_investable": len(res["investable"]),
                              "n_missing": len(res["missing_ok"]), "n_name_errors": len(res.get("name_errors") or {}),
                              "n_linked": sum(1 for v in res["outcomes"].values() if v.get("status") == "LINKED")})
        wf, wm = _measure(lambda: run_walk_forward_from_store(store, [_dt(d) for d in dates], lambda t: snaps[t.date().isoformat()]))
        out.update({"status": "RUN", "single_as_of": singles, "walk_forward": wf, "walk_forward_timing": wm,
                    "benchmark_500": {"kind": "REAL_500_COMPANY_BENCHMARK", "per_date_single_as_of": timings,
                                      "median_wall_s": statistics.median(t["wall_s"] for t in timings),
                                      "max_peak_heap_mb": max(t["peak_heap_mb"] for t in timings),
                                      "name_errors_total": errors, "network": network_stats(Path(a.store)),
                                      "note": "Real raw store (network-ingested by the c21 workflow); compare with "
                                              "tools/bench_universe_500.py (SYNTHETIC)."}})
    path = GE / f"official_pipeline_{dates[0]}_{dates[-1]}.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "per_date": status}, indent=1, default=str))


if __name__ == "__main__":
    main()
