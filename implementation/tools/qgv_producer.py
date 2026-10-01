"""QGV Real Producer v1 runner: Frozen Official Universe → existing QGV engine → per-company snapshots → export.

Subcommands (one as_of per process; a 500-name replay peaks at several GB):
  fingerprint  plain engine run (no capture) → ranked/selection fingerprint JSON (the "before" numbers)
  produce      captured engine run → records + manifest → exporter → run report with invariance checks
  compare      two exports of the same as_of must have identical semantic hashes (determinism)

Replay is offline: socket connects are refused for the whole process. A companyfacts payload absent from the store
therefore stays MISSING instead of being fetched live, and the number of refused attempts is reported.
Nothing here changes Universe membership, QGV methodology, ranking or Track A evidence.

  python tools/qgv_producer.py fingerprint --store /tmp/raw --as-of 2024-12-31 --horizon 2025-03-31 --out /tmp/fp.json
  python tools/qgv_producer.py produce --store /tmp/raw --as-of 2024-12-31 --horizon 2025-03-31 \
      --out reports/qgv_producer/full --plain-fingerprint /tmp/fp.json [--sample aapl,msft]
  python tools/qgv_producer.py compare --a reports/qgv_producer/full --b /tmp/repeat --as-of 2024-12-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import resource
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.qgv_producer.batch import ranked_fingerprint, run_qgv_batch  # noqa: E402
from investment_system.qgv_producer.exporter import export_batch, load_export  # noqa: E402
from investment_system.qgv_producer.infra_boundary import export_decision  # noqa: E402
from investment_system.qgv_producer.record import canonical_sha256, sha256_hex  # noqa: E402
from investment_system.validation.vertical_slice import run_vertical_slice_from_store  # noqa: E402

GE = ROOT / "reports" / "gate_evidence"
FROZEN_PIPELINE = GE / "official_pipeline_2024-06-30_2024-12-31.json"
FREEZE_MANIFEST = GE / "track_a_freeze_readiness_2026-09-27.json"
NETWORK_ATTEMPTS: list[str] = []


def block_network() -> None:
    def refuse(self, address, *a, **k):
        NETWORK_ATTEMPTS.append(str(address))
        raise OSError("qgv_producer: offline replay, network refused")
    socket.socket.connect = refuse  # type: ignore[assignment]
    socket.create_connection = lambda address, *a, **k: refuse(None, address)  # type: ignore[assignment]


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s if "T" in s else s + "T00:00:00+00:00")


def _file_ref(p: Path) -> dict:
    b = p.read_bytes()
    return {"file": p.relative_to(ROOT).as_posix(), "sha256": sha256_hex(b), "bytes": len(b)}


def load_universe(as_of: str):
    """The exact Frozen path: tools/official_pipeline.load_official (gate evidence, exact member/order check)."""
    spec = importlib.util.spec_from_file_location("official_pipeline", ROOT / "tools" / "official_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    snap, status = mod.load_official(as_of)
    if snap is None:
        raise SystemExit(f"Universe for {as_of} is not Official: {status}")
    frozen = {d["as_of"]: d for d in json.loads(FREEZE_MANIFEST.read_text())["per_date"]}
    if as_of not in frozen or frozen[as_of]["universe_id"] != snap.universe_id:
        raise SystemExit(f"Universe {snap.universe_id} for {as_of} is not the Track A Frozen universe")
    evidence = {"official_snapshot": _file_ref(GE / f"official_snapshot_{as_of}.json"),
                "gate_evidence": _file_ref(GE / f"gate_chain_{as_of}_real_gha.json"),
                "freeze_manifest": _file_ref(FREEZE_MANIFEST)}
    return snap, evidence


def load_index(path: str | None) -> dict | None:
    if not path:
        return None
    return {a["artifact_id"]: a for a in json.loads(Path(path).read_text())["artifacts"]}


def frozen_reference(as_of: str) -> dict:
    d = json.loads(FROZEN_PIPELINE.read_text())
    single = next((s for s in d["single_as_of"] if s["as_of"][:10] == as_of), None)
    step = next((s for s in (d.get("walk_forward") or {}).get("steps", []) if s["as_of"][:10] == as_of), None)
    return {"file": FROZEN_PIPELINE.relative_to(ROOT).as_posix(), "single": single,
            "walk_forward_selected": None if step is None else step["selected"]}


def engine_summary(res: dict) -> dict:
    return {"as_of": res["as_of"], "horizon_as_of": res["horizon_as_of"], "universe_id": res["universe_id"],
            "n_universe": len(res["universe"]), "n_selected": res["n_selected"], "n_investable": len(res["investable"]),
            "n_missing": len(res["missing_ok"]), "n_name_errors": len(res.get("name_errors") or {}),
            "n_linked": sum(1 for v in res["outcomes"].values() if v.get("status") == "LINKED"),
            "equal_weight_realized": res["equal_weight_realized"],
            "ranked_sha256": ranked_fingerprint(res["ranked"]), "selected_sha256": canonical_sha256(res["selected"])}


def compare_frozen(summary: dict, res: dict, ref: dict) -> dict:
    s = ref["single"]
    if s is None:
        return {"status": "NOT_RUN", "reason": "no Frozen single_as_of for this date"}
    checks = {k: {"frozen": s[k], "producer": summary[k], "equal": s[k] == summary[k]}
              for k in ("universe_id", "n_selected", "n_investable", "n_missing", "n_name_errors", "n_linked",
                        "equal_weight_realized")}
    checks["equal_weight_realized"]["abs_diff"] = abs(s["equal_weight_realized"] - summary["equal_weight_realized"])
    if ref["walk_forward_selected"] is not None:
        checks["selected_list"] = {"equal": ref["walk_forward_selected"] == res["selected"],
                                   "frozen_sha256": canonical_sha256(ref["walk_forward_selected"]),
                                   "producer_sha256": canonical_sha256(res["selected"])}
    return {"status": "PASS" if all(c["equal"] for c in checks.values()) else "FAIL", "reference": ref["file"],
            "note": "post-as_of outcome aggregates are used only to prove the replay equals the Frozen run; "
                    "they are not part of any QGV snapshot", "checks": checks}


def cmd_fingerprint(a) -> None:
    block_network()
    snap, _ = load_universe(a.as_of)
    t = time.perf_counter()
    res = run_vertical_slice_from_store(RawDatasetStore(a.store), _dt(a.as_of), _dt(a.horizon), snap, chart_range="5y")
    out = {"kind": "QGV_PLAIN_ENGINE_FINGERPRINT", **engine_summary(res), "wall_s": round(time.perf_counter() - t, 3),
           "network_attempts": len(NETWORK_ATTEMPTS)}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def cmd_produce(a) -> None:
    block_network()
    snap, evidence = load_universe(a.as_of)
    raw_source = json.loads(a.raw_source) if a.raw_source else {}
    generated_at = a.generated_at or datetime.now(timezone.utc).isoformat()
    sample = [x.strip() for x in a.sample.split(",") if x.strip()] if a.sample else None
    t = time.perf_counter()
    b = run_qgv_batch(RawDatasetStore(a.store), _dt(a.as_of), _dt(a.horizon), snap, generated_at=generated_at,
                      code_commit=a.code_commit, store_index=load_index(a.store_index), sample=sample,
                      universe_evidence=evidence, raw_source=raw_source, run_id=a.run_id)
    wall = round(time.perf_counter() - t, 3)
    manifest = export_batch(b.records, b.manifest, ROOT / a.out)
    records, _ = load_export(ROOT / a.out, b.as_of)  # read back + full re-validation
    summary = engine_summary(b.engine_result)
    plain = json.loads(Path(a.plain_fingerprint).read_text()) if a.plain_fingerprint else None
    invariance = {
        "plain_vs_captured": None if plain is None else {
            k: {"plain": plain[k], "captured": summary[k], "equal": plain[k] == summary[k]}
            for k in ("ranked_sha256", "selected_sha256", "n_selected", "n_investable", "n_missing", "equal_weight_realized")},
        "frozen_track_a": compare_frozen(summary, b.engine_result, frozen_reference(a.as_of)),
        "records_vs_engine": all(
            r["semantic"]["qgv"] is None or (r["semantic"]["qgv"]["Q_score"], r["semantic"]["qgv"]["G_score"],
                                             r["semantic"]["qgv"]["V_score"]) ==
            next((x["Q"], x["G"], x["V"]) for x in b.engine_result["ranked"] if x["company_id"] == r["semantic"]["company_id"])
            for r in records),
    }
    if plain is not None:
        invariance["plain_vs_captured_status"] = "PASS" if all(v["equal"] for v in invariance["plain_vs_captured"].values()) else "FAIL"
    report = {
        "kind": "QGV_PRODUCER_RUN_REPORT", "as_of": a.as_of, "horizon_for_reference_check": a.horizon,
        "scope": manifest["semantic"]["scope"], "out_dir": a.out,
        "manifest_semantic_sha256": manifest["semantic_sha256"], "counts": manifest["semantic"]["counts"],
        "expected_count": manifest["semantic"]["expected_count"], "complete": manifest["semantic"]["complete"],
        "status_reasons": {r["semantic"]["company_id"]: r["semantic"]["status_reasons"]
                           for r in records if r["semantic"]["status"] != "PASS"},
        "engine": summary, "invariance": invariance, "export_decision": export_decision(manifest),
        "wall_s": wall, "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "network_attempts": len(NETWORK_ATTEMPTS), "code_commit": a.code_commit, "run_id": a.run_id,
        "generated_at": generated_at, "raw_source": raw_source}
    rp = ROOT / a.out / f"qgv_producer_run_{a.as_of}.json"
    rp.write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(json.dumps({k: report[k] for k in ("as_of", "scope", "counts", "complete", "network_attempts")}
                     | {"frozen": invariance["frozen_track_a"]["status"], "plain": invariance.get("plain_vs_captured_status")}))
    bad = invariance["frozen_track_a"]["status"] == "FAIL" or invariance.get("plain_vs_captured_status") == "FAIL" \
        or not invariance["records_vs_engine"]
    if bad and not a.allow_mismatch:
        raise SystemExit(f"invariance FAIL: see {rp}")


def cmd_compare(a) -> None:
    ra, ma = load_export(Path(a.a), a.as_of)
    rb, mb = load_export(Path(a.b), a.as_of)
    out = {"kind": "QGV_PRODUCER_DETERMINISM", "as_of": a.as_of,
           "manifest_semantic_equal": ma["semantic_sha256"] == mb["semantic_sha256"],
           "record_hashes_equal": [r["semantic_sha256"] for r in ra] == [r["semantic_sha256"] for r in rb],
           "operational_ids_differ": all(x["operational"]["qgv_snapshot_id"] != y["operational"]["qgv_snapshot_id"]
                                         for x, y in zip(ra, rb) if x["operational"]["qgv_snapshot_id"]),
           "n_records": len(ra), "manifest_semantic_sha256": ma["semantic_sha256"]}
    out["status"] = "PASS" if out["manifest_semantic_equal"] and out["record_hashes_equal"] else "FAIL"
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    if out["status"] != "PASS":
        raise SystemExit("determinism FAIL")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fingerprint")
    p = sub.add_parser("produce")
    for x in (f, p):
        x.add_argument("--store", required=True)
        x.add_argument("--as-of", required=True)
        x.add_argument("--horizon", required=True, help="the Frozen run's horizon for this as_of (reference check only)")
    f.add_argument("--out", required=True)
    p.add_argument("--out", required=True, help="export dir relative to implementation/")
    p.add_argument("--store-index", default=str(ROOT / "data" / "raw" / "STORE_INDEX.json"))
    p.add_argument("--sample", default=None)
    p.add_argument("--plain-fingerprint", default=None)
    p.add_argument("--raw-source", default=None, help="JSON describing where the raw store came from")
    p.add_argument("--code-commit", default="UNKNOWN")
    p.add_argument("--run-id", default=None)
    p.add_argument("--generated-at", default=None)
    p.add_argument("--allow-mismatch", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("--a", required=True)
    c.add_argument("--b", required=True)
    c.add_argument("--as-of", required=True)
    c.add_argument("--report", default=None)
    a = ap.parse_args()
    {"fingerprint": cmd_fingerprint, "produce": cmd_produce, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
