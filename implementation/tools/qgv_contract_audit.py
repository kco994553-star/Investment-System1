"""Read-only QGV contract audit. No production import, dispatch or weight wiring.

The checked-in golden file is an observation of the pinned legacy program, not
an endorsement of its financial semantics. This tool deliberately has no record
or overwrite-golden option. New policies require new separately reviewed fixtures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from investment_system.contracts.enums import ProfileKind, QualityState
from investment_system.contracts.models import FactorObservation
from investment_system.qgv.analysis import AnalysisEngine

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/qgv_common_contract_vnext"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def evaluate_case(case):
    """Execute only the existing engine on explicit synthetic observations."""
    obs = {row["factor_id"]: FactorObservation(
        row["factor_id"], row["raw_value"], row["score_0_100"],
        QualityState(row["quality"]), row["stamp_id"], row["notes"])
        for row in case["observations"]}
    snapshot = AnalysisEngine().analyze(
        "nvda", datetime.fromisoformat(case["as_of"]), obs,
        profile_kind=ProfileKind(case["profile_kind"]), synthetic=True,
        confidence=case["confidence"], data_stamp_refs=("golden-synthetic",))
    value = snapshot.to_dict()
    # The only excluded field is a freshly generated operational UUID. All
    # timestamps, method versions, statuses, notes and provenance refs remain.
    del value["qgv_snapshot_id"]
    value["score_hex"] = {key: None if value[key] is None else float(value[key]).hex()
                          for key in ("Q_score", "G_score", "V_score", "total_score",
                                      "attractiveness_10", "type_adjusted_score_100")}
    return value


def verify_golden():
    fixture = json.loads((DOCS / "golden_cases.json").read_text())
    failures = [c["case_id"] for c in fixture["cases"] if evaluate_case(c) != c["expected"]]
    return {"status": "FAIL" if failures else "PASS", "case_count": len(fixture["cases"]),
            "failures": failures, "baseline_commit": fixture["baseline_commit"],
            "fixture_sha256": hashlib.sha256((DOCS / "golden_cases.json").read_bytes()).hexdigest(),
            "scope": "SYNTHETIC_LEGACY_EQUIVALENCE_ONLY"}


def validate_spec_record(record):
    """Validate the INACTIVE documentation sample, never admit a runtime score.

    These structural/PIT coherence checks do not implement a missing policy,
    confidence calculation, coverage cutoff or new aggregation function.
    """
    digest(record)  # finite, serializable JSON only; no NaN/Infinity coercion
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((DOCS / "contract_record.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(record)
    def aware(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone-aware time required; never infer midnight or timezone")
        return parsed
    for field in ("as_of", "decision_time", "calculated_at"):
        aware(record[field])
    for metric in record["inputs"]:
        for field in ("period_start", "period_end"):
            if metric[field] is not None:
                if len(metric[field]) == 10:
                    date.fromisoformat(metric[field])  # preserve date precision
                else:
                    aware(metric[field])
        if metric["available_at"] is not None:
            aware(metric["available_at"])
        value = metric["raw_value"]
        if metric["value_state"] == "PRESENT" and value is None:
            raise ValueError("PRESENT requires an observed value")
        if metric["value_state"] == "ABSENT" and value is not None:
            raise ValueError("ABSENT cannot carry an observed value")
    if record["pit"]["status"] == "ELIGIBLE":
        if not record["inputs"] or not record["pit"]["policy_ref"]:
            raise ValueError("PIT eligibility requires input evidence and policy reference")
        decision = aware(record["decision_time"])
        for metric in record["inputs"]:
            if not metric["available_at"] or not metric["source_ref"] or not metric["vintage_ref"]:
                raise ValueError("PIT eligibility requires availability/source/vintage")
            available = aware(metric["available_at"])
            if available > decision:
                raise ValueError("future input is ineligible")
    # Authentication of actual source bytes / full revision closure remains a
    # future migration gate. A well-shaped hash is not proof of a real source.
    return {"status": "SPEC_VALID", "runtime_enabled": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", required=True)
    args = parser.parse_args()
    result = verify_golden()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
