"""New bounded carrier/consumer lineage characterization; no production patch.

No replacement method is executed. The operational-only code pin case shows why
an unchanged result hash/coarse version cannot authenticate factor method identity.
The horizon case changes declared metadata only, not scoring arithmetic.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.repository.resolve()
    paths = [
        "implementation/src/investment_system/contracts/models.py",
        "implementation/src/investment_system/qgv/analysis.py",
        "implementation/src/investment_system/qgv/leaderboard.py",
        "implementation/src/investment_system/qgv/factors.py",
        "implementation/src/investment_system/qgv_producer/record.py",
        "implementation/src/investment_system/leaderboard_producer/qgv_input.py",
    ]
    before = {p: digest(root / p) for p in paths}
    sys.path.insert(0, str(root / "implementation/src"))
    from investment_system.contracts.enums import QualityState
    from investment_system.contracts.models import FactorObservation, QGVSnapshot, LeaderboardRow
    from investment_system.qgv.analysis import AnalysisEngine
    from investment_system.qgv.factors import Q_WEIGHTS, G_WEIGHTS, V_FACTORS
    from investment_system.qgv.leaderboard import LeaderboardEngine
    from investment_system.qgv_producer.record import make_record, snapshot_semantic, sub_factor_table, validate_record
    from investment_system.leaderboard_producer.qgv_input import methodology_weights_sha256, validate_qgv_record

    when = datetime(2024, 12, 31, tzinfo=timezone.utc)
    # The literal complete-input score fixture is inherited from prior golden
    # characterization, not a proposed score, threshold, normalizer or policy.
    observations = {
        fid: FactorObservation(fid, 70.0, 70.0, QualityState.SYNTHETIC, "SYNTHETIC_TRACE", "SYNTHETIC fixture")
        for fid in set(Q_WEIGHTS) | set(G_WEIGHTS) | set(V_FACTORS)
    }
    snap = AnalysisEngine().analyze("trace_company", when, observations, synthetic=True)
    snap = dataclasses.replace(snap, qgv_snapshot_id="SYNTHETIC_LINEAGE_TRACE")
    semantic = {
        "company_id": snap.company_id, "ticker": "TRACE", "as_of": when.isoformat(),
        "status": "PASS", "status_reasons": [],
        "universe": {"universe_id": "SYNTHETIC_TRACE"},
        "methodology": {
            "qgv_system_version": snap.qgv_system_version,
            "qgv_standard_version": snap.qgv_standard_version,
            "qgv_analysis_contract": snap.qgv_analysis_contract,
            "implementation_line": snap.implementation_line,
            "weights_sha256": methodology_weights_sha256(),
        },
        "research_state": {
            "status": "PROVISIONAL_RESEARCH", "v_policy_status": "PROVISIONAL_INITIAL_PRIOR",
            "official_selection": False, "official_pass": False, "full_pit_pass": False,
            "calibrated": False, "track_c_validated": False,
        },
        "synthetic": True,
        "pit": {
            "fundamentals_available_at": when.isoformat(), "fundamentals_synthetic": True,
            "known_limitations": ["SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED"],
        },
        "lineage": {"inputs": [{"artifact_id": "raw:companyfacts:trace_company", "sha256": "a" * 64,
                                 "source_kind": "SYNTHETIC"}]},
        "qgv": snapshot_semantic(snap), "sub_factors": sub_factor_table(observations),
        "cross_section": {"eligible": True, "rank": 1},
    }
    records = [make_record(semantic, {"qgv_snapshot_id": snap.qgv_snapshot_id, "code_commit": pin,
                                    "generated_at": when.isoformat(), "run_id": "SYNTHETIC"})
               for pin in ("a" * 40, "b" * 40)]
    checks = []

    def check(label: str, predicate: bool) -> None:
        assert predicate, label
        checks.append(label)

    for rec in records:
        validate_record(rec, require_real=False)
        validate_qgv_record(rec, require_real=False)
    check("both operational code pin variants validate only in synthetic characterization mode", True)
    check("different operational code pins leave the exact semantic result hash equal", records[0]["semantic_sha256"] == records[1]["semantic_sha256"])
    check("operational code pins are retained and distinguishable outside the result hash", records[0]["operational"]["code_commit"] != records[1]["operational"]["code_commit"])
    factor_fields = {f.name for f in dataclasses.fields(FactorObservation)}
    snapshot_fields = {f.name for f in dataclasses.fields(QGVSnapshot)}
    row_fields = {f.name for f in dataclasses.fields(LeaderboardRow)}
    check("factor carrier has no explicit method identity/version", not {"method_id", "method_version"} & factor_fields)
    check("snapshot has no independent completeness/scoring validity/ranking assessment", not {"completeness", "scoring_validity", "ranking_eligible"} & snapshot_fields)
    check("persisted subfactor table cannot add a method identity absent in observation", all(not {"method_id", "method_version"} & set(v) for v in semantic["sub_factors"].values()))
    horizon_snaps = [dataclasses.replace(snap, g_horizon={"requested": h, "mutates_g_score": False}) for h in ("1Q", "5Y")]
    horizon_records = [make_record({**semantic, "qgv": snapshot_semantic(s)}, records[0]["operational"]) for s in horizon_snaps]
    for rec in horizon_records:
        validate_qgv_record(rec, require_real=False)
    check("changed declared horizon metadata is detectable by semantic hash", horizon_records[0]["semantic_sha256"] != horizon_records[1]["semantic_sha256"])
    coarse_keys = ("qgv_system_version", "qgv_standard_version", "qgv_analysis_contract", "implementation_line")
    check("coarse method labels do not distinguish declared horizon variants", all(getattr(horizon_snaps[0], k) == getattr(horizon_snaps[1], k) for k in coarse_keys))
    rows = [LeaderboardEngine().build("SYNTHETIC_TRACE", when, [s], tickers={s.company_id: "TRACE"}).to_dict()["rows"][0] for s in horizon_snaps]
    check("legacy row projection equals despite distinct declared horizon metadata", rows[0] == rows[1])
    check("legacy row has no method/horizon/result admission assessment fields", not {"method_id", "method_version", "g_horizon", "scoring_validity", "ranking_eligible"} & row_fields)
    after = {p: digest(root / p) for p in paths}
    check("selected source bytes preserved", before == after)
    result = {
        "status": "PINNED_CARRIER_CHARACTERIZATION_PASS_NOT_VNEXT_RUNTIME_ACCEPTANCE",
        "production_enabled": False, "scheduler_hops": 0,
        "source_sha256": before, "script_sha256": digest(Path(__file__)),
        "checks": checks, "assertions_passed": len(checks), "failed": 0,
        "actual": {
            "operational_variant_semantic_sha256": [r["semantic_sha256"] for r in records],
            "operational_variant_code_commit": [r["operational"]["code_commit"] for r in records],
            "horizon_variant_semantic_sha256": [r["semantic_sha256"] for r in horizon_records],
            "horizon_rows": rows, "factor_fields": sorted(factor_fields), "snapshot_fields": sorted(snapshot_fields),
        },
        "limits": "Manufactured synthetic inputs/operational pins and declared horizon metadata. No alternate economic method, new formula, archived data, full PIT, real company result, production guard, rank policy or publication grant is evaluated. Content hash detects reported metadata drift but is not exact factor-method identity. Existing P01 binding also retains manifest code_commit in its own provenance hash; it is not exercised or weakened here.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "assertions_passed": len(checks), "failed": 0}))


if __name__ == "__main__":
    main()
