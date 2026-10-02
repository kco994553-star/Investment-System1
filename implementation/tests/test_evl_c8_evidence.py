"""Independent arithmetic, current scope authority and absence of real states."""
from copy import deepcopy
from datetime import timedelta
import math
from fractions import Fraction
import pytest
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.calibration_evidence import (software_artifact, resolve_software_artifact,
    record_control_evidence, record_economic_evidence, research_admission)
from investment_system.evl.robustness import acceptance, MANDATORY
from tests.evl_c8_fixture import (c8_source, c8_rig, complete, register, fit, choose, verify,
                                 FIT_AT, VERIFY_AT)
from investment_system.evl.walkforward import digest


def test_complete_scoped_foundation_never_c8_freeze_or_research(c8_rig):
    artifact = complete(c8_rig)
    assert artifact["validation_result"] == "APPROVED_FOUNDATION_PROTOCOL_PASS"
    assert artifact["artifact_kind"] == "SOFTWARE_ACCEPTANCE"
    assert artifact["research_state"] is artifact["promotion_authority"] is None
    assert artifact["real_holdout_eligible"] is artifact["official"] is False
    assert artifact["software_freeze_eligible"] is artifact["real_pit_research_validated"] is False
    payload = artifact["fixture_manifest_payload"]
    assert payload["C8_SOFTWARE_FROZEN"] is False
    assert payload["frozen_phase_count"] == "8/11 = 72.7% SOFTWARE_PHASE_COUNT_ONLY"
    assert payload["roles"] is payload["statistical_decision"] is payload["distinctness_decision"] is None
    assert set(payload["unapproved_policy_status"]) == {"A6", "A8", "A10", "REAL_RESEARCH_CONFIGURATION"}
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]


def test_control_full_family_and_hand_calculated_difference_without_skill(c8_rig):
    artifact = complete(c8_rig)
    result = c8_rig["ledger"].receipt("controls")["output"]
    assert len(result["pairs"]) == 32  # 2 complete candidates x 4 cohorts x 4 controls.
    assert all(p["skill_decision"] is None for p in result["pairs"])
    candidate = c8_rig["plan"]["family_members"][0]
    pair = next(p for p in result["pairs"] if p["candidate_id"] == candidate)
    # Independent wealth/annualization oracle, not calling C3/C8 calculation.
    candidate_cagr = ((1 + .004 - .0001) * (1 - .001 - .0001)) ** (73 / 2) - 1
    control_cagr = ((1 + .001 - .0001) * (1 - .002 - .0001)) ** (73 / 2) - 1
    assert math.isclose(float(Fraction(pair["descriptive_candidate_minus_control"])),
                        candidate_cagr - control_cagr, rel_tol=1e-12, abs_tol=1e-12)
    assert result["skill_decision"] is result["statistical_decision"] is None
    assert result["economic_superiority_decision"] is None


def test_economic_exact_order_views_and_missing_real_numeric_not_zero(c8_rig):
    complete(c8_rig)
    result = c8_rig["ledger"].receipt("economic")["output"]
    assert result["order"] == ["nominal", "real", "risk_free_excess", "premium", "opportunity_cost", "risk_adjusted"]
    assert len(result["candidates"]) == 8
    first = result["candidates"][0]
    gates = first["gates"]
    assert len(gates) == 6 and all(g["economic_decision"] == "NOT_RUN" for g in gates)
    assert all(g["registered_identity"]["limit"] is None for g in gates)
    assert gates[3]["raw_value"] is None
    assert "METRIC_IDENTITY" in gates[3]["missing"]
    wealth = (1 + .004 - .0001) * (1 - .001 - .0001)
    assert math.isclose(gates[0]["raw_value"], wealth ** (73 / 2) - 1, abs_tol=1e-12)
    assert math.isclose(gates[1]["raw_value"], (wealth / (1.0003 ** 2)) ** (73 / 2) - 1, abs_tol=1e-12)
    assert math.isclose(gates[2]["raw_value"], (wealth / (1.0002 ** 2)) ** (73 / 2) - 1, abs_tol=1e-12)
    assert result["actual_numeric_authority"] is None and not result["compensation_allowed"]


def test_shared_singleton_and_zero_pairs_are_preserved_without_roles_or_hard_distinctness(c8_rig):
    artifact = complete(c8_rig)
    payload = artifact["fixture_manifest_payload"]
    assert all(len(v) == 1 for v in payload["representative_ties"].values())
    assert payload["C7_distinctness"]["role"] == "DESCRIPTIVE_ONLY"
    assert all(p["delta_right_minus_left"] == "0" for p in payload["C7_distinctness"]["pairs"])
    assert payload["roles"] is payload["distinctness_decision"] is None
    assert not payload["C7_distinctness"]["next_best_substitution"]


@pytest.mark.parametrize("field,value", [
    ("evidence_scope", "REAL_PIT_RESEARCH_VALIDATION"), ("synthetic", False),
    ("artifact_kind", "RESEARCH_FREEZE_MANIFEST"), ("research_state", "VALIDATED"),
    ("research_state", "OFFICIAL"), ("real_holdout_eligible", True),
    ("promotion_authority", "forged"), ("real_pit_research_validated", True),
    ("software_freeze_eligible", True), ("tax_mode", "INCLUDED"), ("code_hash", "fake")])
def test_flags_strings_and_manifest_payload_cannot_grant_authority(c8_rig, field, value):
    artifact = complete(c8_rig)
    artifact[field] = value
    with pytest.raises(IntegrityFailure):
        resolve_software_artifact(artifact, c8_rig["ledger"], *c8_rig["source"])
    with pytest.raises(MissingPrerequisite):
        research_admission(artifact)


def test_bare_c6_real_validation_flag_is_a_negative_witness_not_authority():
    fabricated = {kind: {"status": "PASS", "role": "MANDATORY",
                         "report_hash": "fabricated", "trial_id": "fabricated"}
                  for kind in MANDATORY}
    result = acceptance(fabricated, "REAL_PIT_RESEARCH_VALIDATION")
    assert result["real_pit_research_validated"] is True
    with pytest.raises(MissingPrerequisite):
        research_admission(result)


def test_current_receipt_invalidation_revokes_scoped_export(c8_rig):
    artifact = complete(c8_rig)
    c8_rig["ledger"].invalidate("source-invalidation", "verify", "current evidence revoked", VERIFY_AT)
    with pytest.raises(IntegrityFailure):
        resolve_software_artifact(artifact, c8_rig["ledger"], *c8_rig["source"])
    assert not artifact["real_holdout_eligible"]


def test_pending_unused_attempt_cannot_be_hidden_from_acceptance(c8_rig):
    artifact = complete(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.begin("pending-extra", "CONTROL_EVIDENCE", VERIFY_AT)
    with pytest.raises(MissingPrerequisite):
        software_artifact(ledger, *c8_rig["source"], artifact["fixture_manifest_payload"]["receipt_ids"])
    assert ledger.accounting()["charged_attempts"] == 6


def test_computational_integrity_failure_is_not_offset_by_positive_returns(c8_rig):
    artifact = complete(c8_rig)
    ledger = c8_rig["ledger"]

    def broken(p):
        raise IntegrityFailure("required integrity failure")
    ledger.execute("bad", "ECONOMIC_EVIDENCE", VERIFY_AT, broken)
    with pytest.raises(IntegrityFailure):
        software_artifact(ledger, *c8_rig["source"], artifact["fixture_manifest_payload"]["receipt_ids"])


def test_missing_failed_unused_attempts_are_accounted_not_successful_subset(c8_rig):
    artifact = complete(c8_rig)
    ledger = c8_rig["ledger"]

    def missing(p):
        raise MissingPrerequisite("required support missing")
    ledger.execute("missing", "CONTROL_EVIDENCE", VERIFY_AT, missing)
    with pytest.raises(MissingPrerequisite):
        software_artifact(ledger, *c8_rig["source"], artifact["fixture_manifest_payload"]["receipt_ids"])
    assert "missing" in ledger.accounting()["all_attempt_ids"]


def test_no_manifest_export_from_just_producer_pass_or_legacy_flags(c8_rig):
    register(c8_rig)
    forged = {"artifact_kind": "SOFTWARE_ACCEPTANCE", "evidence_scope": "SYNTHETIC_SOFTWARE_VALIDATION",
              "research_state": None, "official": False, "real_holdout_eligible": False,
              "fixture_manifest_payload": {"receipt_ids": {}}}
    with pytest.raises(MissingPrerequisite):
        resolve_software_artifact(forged, c8_rig["ledger"], *c8_rig["source"])
    assert c8_rig["provider"].reads == []


def test_c6_diagnostic_pass_is_only_preserved_reference(c8_rig):
    artifact = complete(c8_rig)
    refs = artifact["fixture_manifest_payload"]["C6_calculation_evidence"]
    assert len(refs) == 4
    assert all(len(ref["results"]) == 17 for ref in refs.values())
    assert all(ref["decision"] == "NOT_ASSESSED_PENDING_C8" for ref in refs.values())
    assert artifact["fixture_manifest_payload"]["statistical_decision"] is None
