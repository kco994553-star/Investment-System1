"""C8 control/economic evidence frameworks and scoped software artifacts only.

No skill/NO_EVIDENCE_OF_SKILL, profile hard decision, Champion/Challenger,
statistical family decision, real FreezeManifest or promotion is emitted.
"""
from copy import deepcopy
from .calibration_contracts import (BLOCKED, CONTROLS, ECONOMIC_ORDER, METHOD, SCOPE,
                                   FIXTURE_SCOPE, IntegrityFailure, MissingPrerequisite,
                                   canonical_metric, finite_number)
from .calibration_protocol import resolve_entry
from .selection import number
from .walkforward import digest


def _metric(report, registration):
    canonical_metric(registration)
    value = report
    for key in registration["path"]:
        if not isinstance(value, dict) or key not in value:
            raise MissingPrerequisite("registered metric path evidence missing")
        value = value[key]
    if value is None:
        return None
    return finite_number(value)


def _source(ledger, receipt_id):
    receipt = ledger.receipt(receipt_id)
    if receipt["operation"] not in ("CAL_FIT", "CAL_VERIFY"):
        raise IntegrityFailure("control/economic evidence needs registered calibration receipt")
    return receipt


def record_control_evidence(ledger, selection_ledger, cohorts, *, source_attempt_id, attempt_id, at):
    def produce(pending):
        plan, current = resolve_entry(ledger, selection_ledger, cohorts)
        source = _source(ledger, source_attempt_id)
        pairs = []
        for cohort in plan["cohort_metadata"]:
            for candidate in plan["family_members"]:
                row = source["output"]["data"]["cohorts"][cohort][candidate]
                for control in plan["controls"]:
                    left = _metric(row["metric_report"], control["metric"])
                    right = _metric(row["controls"][control["control_id"]], control["metric"])
                    pairs.append({"candidate_id": candidate, "cohort": cohort,
                                  "control": deepcopy(control), "candidate_value": left,
                                  "control_value": right,
                                  "descriptive_candidate_minus_control": None if left is None or right is None
                                  else str(number(left) - number(right)),
                                  "skill_decision": None,
                                  "decision_status": "NOT_RUN_A6_AND_REAL_CONFIGURATION_NOT_APPROVED"})
        return {"source_receipt_hash": digest(source), "source_role": source["operation"],
                "pairs": pairs, "all_registered_controls": list(CONTROLS),
                "c7_report_hash": current["c7_report_hash"], "skill_decision": None,
                "statistical_decision": None, "economic_superiority_decision": None}
    return ledger.execute(attempt_id, "CONTROL_EVIDENCE", at, produce)


def record_economic_evidence(ledger, selection_ledger, cohorts, *, source_attempt_id, attempt_id, at):
    def produce(pending):
        plan, current = resolve_entry(ledger, selection_ledger, cohorts)
        source = _source(ledger, source_attempt_id)
        rows = []
        for cohort in plan["cohort_metadata"]:
            for candidate in plan["family_members"]:
                metrics = source["output"]["data"]["cohorts"][cohort][candidate]["metric_report"]
                values = []
                for gate in plan["economic_gates"]:
                    value = None if gate["metric"] is None else _metric(metrics, gate["metric"])
                    missing = (["METRIC_IDENTITY"] if gate["metric"] is None else []) + (
                        ["REAL_NUMERIC_CONFIGURATION"] if gate["limit"] is None else [])
                    if value is None:
                        missing.append("METRIC_SUPPORT")
                    values.append({"stage": gate["stage"], "registered_identity": deepcopy(gate),
                                   "raw_value": value, "missing": missing,
                                   "economic_decision": "NOT_RUN",
                                   "reason": "ACTUAL_RESEARCH_CONFIGURATION_NOT_APPROVED"})
                rows.append({"candidate_id": candidate, "cohort": cohort, "gates": values,
                             "raw_C3_views": deepcopy(metrics["views"])})
        return {"source_receipt_hash": digest(source), "source_role": source["operation"],
                "order": list(ECONOMIC_ORDER), "candidates": rows, "compensation_allowed": False,
                "economic_decision": "NOT_RUN", "actual_numeric_authority": None,
                "c7_report_hash": current["c7_report_hash"]}
    return ledger.execute(attempt_id, "ECONOMIC_EVIDENCE", at, produce)


def software_artifact(ledger, selection_ledger, cohorts, receipt_ids):
    """Current-resolving exporter; not a performance/calibration attempt."""
    plan, current = resolve_entry(ledger, selection_ledger, cohorts)
    operations = ("CAL_FIT", "THRESHOLD_CHOICE", "CAL_VERIFY", "CONTROL_EVIDENCE", "ECONOMIC_EVIDENCE")
    if set(receipt_ids) != set(operations):
        raise MissingPrerequisite("complete approved foundation protocol receipts required")
    receipts = {op: ledger.receipt(receipt_ids[op]) for op in operations}
    if any(receipts[op]["operation"] != op for op in operations):
        raise IntegrityFailure("receipt method/identity cannot be substituted")
    fit, choice, verify = (receipts[k] for k in operations[:3])
    if (choice["output"]["fit_receipt_hash"] != digest(fit)
            or choice["output"]["threshold_registration_hash"] != digest(plan["threshold_registration"])
            or verify["output"]["model_instances"] != current["model_instances"]
            or verify["output"]["data_hash"] != plan["datasets"]["CAL_VERIFY"]["content_hash"]):
        raise IntegrityFailure("exact FIT/choice/VERIFY/config lineage incomplete")
    for op in ("CONTROL_EVIDENCE", "ECONOMIC_EVIDENCE"):
        if receipts[op]["output"]["source_receipt_hash"] != digest(verify):
            raise IntegrityFailure("acceptance control/economic ancestry must retain VERIFY role")
    if any(r["output"]["c7_report_hash"] != current["c7_report_hash"] for r in receipts.values()):
        raise IntegrityFailure("stale/mixed current upstream resolution")
    events = ledger.events()
    if ledger.accounting()["pending"]:
        raise MissingPrerequisite("pending attempts cannot be omitted from acceptance")
    if any(r["body"]["event"]["kind"] == "TERMINAL" and r["body"]["event"]["status"] == "FAIL" for r in events):
        raise IntegrityFailure("integrity/computation FAIL cannot be offset")
    if any(r["body"]["event"]["kind"] == "BLOCKED_NOT_RUN"
           or (r["body"]["event"]["kind"] == "TERMINAL" and r["body"]["event"]["status"] in ("NOT_RUN", "CRASH"))
           for r in events):
        raise MissingPrerequisite("blocked/crashed evidence is retained, not successful-subset acceptance")
    payload = {"foundation_status": "APPROVED_FOUNDATION_PROTOCOL_PASS",
               "receipt_ids": deepcopy(receipt_ids),
               "receipt_hashes": {op: digest(r) for op, r in receipts.items()},
               "ledger_checkpoint": events[-1]["sha256"], "accounting": ledger.accounting(),
               "representative_ties": deepcopy(current["representative_ties"]),
               "C7_distinctness": deepcopy(current["descriptive_distinctness"]),
               "C6_calculation_evidence": deepcopy(current["c6_evidence_refs"]),
               "unapproved_policy_status": {key: "PROPOSED_NOT_APPROVED_NOT_ACTIVE" for key in BLOCKED},
               "statistical_decision": None, "distinctness_decision": None, "roles": None,
               "real_economic_decision": "NOT_RUN", "C8_SOFTWARE_FROZEN": False,
               "frozen_phase_count": "8/11 = 72.7% SOFTWARE_PHASE_COUNT_ONLY"}
    return {"schema": METHOD, "artifact_kind": "SOFTWARE_ACCEPTANCE", "evidence_scope": SCOPE,
            "configuration_scope": FIXTURE_SCOPE, "temporal_origin": "SIMULATED", "synthetic": True,
            "source_checkpoint": current["snapshot_hash"], "code_hash": plan["code_hash"],
            "config_hash": digest(plan), "validation_result": "APPROVED_FOUNDATION_PROTOCOL_PASS",
            "lineage": {"registration_hash": ledger.registration()["sha256"],
                        "C7_report_hash": current["c7_report_hash"], "dataset_vintage": plan["dataset_vintage"],
                        "calibration_manifests": {k: d["manifest_hash"] for k, d in plan["datasets"].items()}},
            "approval_event_ref": {"policy": plan["policy"], "approval_blob": plan["approval_blob"],
                                  "purpose": "PARTIAL_SOFTWARE_PROTOCOL_ONLY"},
            "tax_mode": "EXCLUDED", "payload_hash": digest(payload),
            "fixture_manifest_payload": payload,
            "official": False, "research_state": None, "promotion_authority": None,
            "real_holdout_eligible": False, "holdout_state": "UNCONSUMED",
            "real_pit_research_validated": False, "software_freeze_eligible": False}


def resolve_software_artifact(artifact, ledger, selection_ledger, cohorts):
    if (not isinstance(artifact, dict) or artifact.get("artifact_kind") != "SOFTWARE_ACCEPTANCE"
            or artifact.get("evidence_scope") != SCOPE
            or artifact.get("research_state") is not None or artifact.get("official") is not False
            or artifact.get("real_holdout_eligible") is not False):
        raise IntegrityFailure("unknown/mixed/real Manifest cannot be admitted")
    expected = software_artifact(ledger, selection_ledger, cohorts,
                                 artifact["fixture_manifest_payload"]["receipt_ids"])
    if artifact != expected:
        raise IntegrityFailure("artifact hash/scope/current lineage/authority mismatch")
    return deepcopy(expected)


def research_admission(artifact):
    """Real authority stays closed irrespective of producer PASS/synthetic flag."""
    raise MissingPrerequisite("NOT_RUN_UNAPPROVED_A6_A8_A10_AND_ACTUAL_RESEARCH_CONFIGURATION")
