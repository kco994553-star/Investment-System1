"""Actual Actions evidence for approved C8 FOUNDATION, never C8 software Freeze."""
from pathlib import Path
import json
import subprocess

from tools.track_c_c6_acceptance import blobs, git, boundary_audit
from tests.evl_c8_fixture import full_acceptance
from investment_system.evl.calibration_contracts import authority, APPROVAL_BLOB, BLOCKED
from investment_system.evl.walkforward import digest

BASE = "86e345e54678de05ebcdf2e1db53c9dbe72ca52a"
NEW_SOURCE_TESTS = ["implementation/src/investment_system/evl/calibration_contracts.py","implementation/src/investment_system/evl/calibration_ledger.py","implementation/src/investment_system/evl/calibration_protocol.py","implementation/src/investment_system/evl/calibration_evidence.py","implementation/tests/evl_c8_fixture.py","implementation/tests/test_evl_c8_contracts.py","implementation/tests/test_evl_c8_ledger.py","implementation/tests/test_evl_c8_protocol.py","implementation/tests/test_evl_c8_evidence.py"]
RUNNER = "implementation/tools/track_c_c8_partial_acceptance.py"
OVERLAYS = (
    "implementation/reports/track_c_decision_register_2026-10-01.md",
    "Investment-System1 · CURRENT_HANDOFF.md",
    "Investment-System1 · Master Status Index 2026-09-22.md",
    "Investment System · Project Index.md",
    "Investment-System1 · Contract Conflict Register 2026-09-23.md",
    "Investment-System1 · Artifact Evidence Register 2026-09-23.md",
)
INFRA = (".github/workflows/track-c-evl-validation.yml",
         "implementation/tools/track_c_c6_acceptance.py",
         "implementation/tools/track_c_c7_acceptance.py")


def preservation():
    baseline, current = blobs(BASE), blobs("HEAD")
    frozen = [p for p in baseline if p.startswith(("implementation/src/", "implementation/tests/"))]
    changed = [p for p in frozen if current.get(p) != baseline[p]]
    if changed:
        raise ValueError("C0-C7/all upstream source/test blobs changed: " + repr(changed))
    allowed = set(OVERLAYS) | set(INFRA)
    unexpected = [p for p in baseline if current.get(p) != baseline[p] and p not in allowed]
    if unexpected:
        raise ValueError("historical/proposal/evidence/non-Track-C files changed: " + repr(unexpected))
    for p in OVERLAYS:
        before = subprocess.check_output(["git", "show", BASE + ":" + p])
        if not Path("..", p).read_bytes().startswith(before):
            raise ValueError("history-preserving append required: " + p)
    added = [p for p in current if p not in baseline]
    unauthorized = [p for p in added if p not in NEW_SOURCE_TESTS and p != RUNNER
                    and not p.startswith("implementation/reports/track_c_")]
    if unauthorized:
        raise ValueError("new unauthorized files: " + repr(unauthorized))
    for p in NEW_SOURCE_TESTS:
        if p not in current:
            raise ValueError("approved foundation file missing: " + p)
    # Package A proposal/dossier, B/C, EVL spec, G1/D2 and all prior Freeze blobs
    # are checked with every other pre-existing file, without policy rewrites.
    record = authority()
    if record["canonical_head"] != git("rev-parse", "origin/claude/investment-system-top500-validation-alrugm"):
        raise ValueError("canonical advanced; new integration audit required")
    return {"status": "PASS", "baseline": BASE, "frozen_existing_source_test_count": len(frozen),
            "frozen_source_tests_changed": changed, "historical_unexpected_changes": unexpected,
            "history_overlays": "APPEND_ONLY_PREFIX_VERIFIED", "unauthorized_new_files": unauthorized,
            "original_Package_A_and_dossier": "UNCHANGED",
            "Packages_B_C": "UNCHANGED_PROPOSED_NOT_APPROVED_NOT_ACTIVE",
            "Track_A_B_D_E_Web_Producer_QGV_Entity": "PRESERVED_BY_BLOB_IDENTITY",
            "canonical_boundary": boundary_audit()}


if __name__ == "__main__":
    out = Path("reports/track_c_c8_partial_generated")
    out.mkdir(parents=True, exist_ok=False)
    audit = preservation()
    result = full_acceptance(out / "integrated")
    artifact = result["artifact"]
    if (result["status"] != "APPROVED_FOUNDATION_PROTOCOL_PASS"
            or result["C8_SOFTWARE_FROZEN"] is not False
            or artifact["software_freeze_eligible"] is not False
            or artifact["real_pit_research_validated"] is not False
            or artifact["research_state"] is not None or artifact["promotion_authority"] is not None
            or artifact["official"] is not False or artifact["real_holdout_eligible"] is not False):
        raise SystemExit("scoped partial acceptance must not grant full Freeze/real authority")
    evidence = {"tested_head": git("rev-parse", "HEAD"), "approval_blob": APPROVAL_BLOB,
                "approval_recorded_at_kst": authority()["approval_recorded_at_kst"],
                "scope": "SYNTHETIC_SOFTWARE_VALIDATION",
                "configuration_scope": "SYNTHETIC_SOFTWARE_VALIDATION_ONLY",
                "status": "APPROVED_FOUNDATION_PROTOCOL_PASS", "implementation": result,
                "preservation": audit, "unapproved_policy": {key: "PROPOSED_NOT_APPROVED_NOT_ACTIVE" for key in BLOCKED},
                "C8": "PARTIAL_FOUNDATION_VERIFIED_NOT_SOFTWARE_FROZEN",
                "C0_C7": "SOFTWARE_FROZEN_PRESERVED", "frozen_phase_count": "8/11 = 72.7%",
                "real_calibration": "NOT_RUN_NOT_AUTHORIZED",
                "real_pit_research_validation": "NOT_RUN_MISSING_REAL_CONFIGURATION_AND_POLICIES",
                "PIT_lineage_Holdout": "PASS_CURRENT_ANCESTOR_RESOLUTION_AND_SYNTHETIC_BOUNDARY_TESTS",
                "holdout_state": "UNCONSUMED_NO_REAL_READER",
                "official": False, "Investor_QGV": "FUTURE_TRACK_C_INPUT",
                "new_result_impact_policy": "NONE_INFERRED"}
    (out / "artifact.json").write_text(json.dumps(artifact, indent=2) + "\n")
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("TRACK_C_C8_PARTIAL_EVIDENCE=" + json.dumps(evidence, sort_keys=True, separators=(",", ":")))
