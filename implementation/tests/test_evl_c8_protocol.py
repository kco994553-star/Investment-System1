"""Actual C7 current resolution, pre-access order, boundaries and one-shot VERIFY."""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
import pytest
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.calibration_ledger import CalibrationLedger
from investment_system.evl.calibration_protocol import (
    read_partition, record_fixture_threshold_choice, register_calibration)
from tests.evl_c8_fixture import (c8_source, c8_rig, register, fit, choose, verify,
                                 FIT_AT, VERIFY_AT, refresh_partition)


def test_durable_registration_pending_access_checkpoint_precedes_read(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]

    def before(role):
        events = [r["body"]["event"] for r in ledger.events()]
        assert [e["kind"] for e in events] == ["REGISTRATION", "PENDING", "ACCESS_INTENT"]
        assert events[1]["full_family"] == c8_rig["plan"]["family_members"]
        assert ledger.registry.spent(c8_rig["plan"]["datasets"][role])
        assert ledger.registry.enrolled(c8_rig["plan"]["ledger_id"], ledger.registration()["sha256"])
    c8_rig["provider"].before_read = before
    assert fit(c8_rig)["status"] == "PASS"
    assert c8_rig["provider"].reads == ["CAL_FIT"]
    assert ledger.accounting()["charged_attempts"] == 1


def test_frozen_models_predictive_thresholds_and_complete_family(c8_rig):
    register(c8_rig)
    expected = deepcopy(c8_rig["plan"]["model_instances"])
    result = fit(c8_rig)
    assert result["status"] == "PASS"
    assert result["output"]["model_instances"] == expected
    assert len(result["output"]["data"]["cohorts"]) == 4
    assert all(len(rows) == 2 for rows in result["output"]["data"]["cohorts"].values())
    assert result["output"]["confirmation_decision"] is None


def test_verify_one_shot_then_no_fit_choice_or_verify_retry(c8_rig):
    register(c8_rig)
    assert fit(c8_rig)["status"] == choose(c8_rig)["status"] == "PASS"
    assert verify(c8_rig)["status"] == "PASS"
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]
    assert verify(c8_rig, "retry")["status"] == "NOT_RUN"
    assert fit(c8_rig, "refit", at=VERIFY_AT)["status"] == "NOT_RUN"
    assert choose(c8_rig, "next-best", "fixture-b", at=VERIFY_AT)["status"] == "NOT_RUN"
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]
    assert c8_rig["ledger"].accounting()["charged_attempts"] == 6


@pytest.mark.parametrize("failure", [IntegrityFailure("invalid provider"), MissingPrerequisite("missing support")])
def test_verify_failure_keeps_access_used_without_tuning(c8_rig, failure):
    register(c8_rig)
    assert fit(c8_rig)["status"] == choose(c8_rig)["status"] == "PASS"
    c8_rig["provider"].fail = failure
    result = verify(c8_rig)
    assert result["status"] == ("FAIL" if isinstance(failure, IntegrityFailure) else "NOT_RUN")
    c8_rig["provider"].fail = None
    assert verify(c8_rig, "again")["status"] == "NOT_RUN"
    assert choose(c8_rig, "replacement", "fixture-b", at=VERIFY_AT)["status"] == "NOT_RUN"
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]


def test_verify_crash_keeps_pending_charge_and_access_intent(c8_rig):
    class Crash(BaseException):
        pass
    register(c8_rig)
    fit(c8_rig)
    choose(c8_rig)
    c8_rig["provider"].fail = Crash()
    with pytest.raises(Crash):
        verify(c8_rig)
    ledger = c8_rig["ledger"]
    assert ledger.accounting()["pending"] == ["verify"]
    assert ledger.accounting()["charged_attempts"] == 3
    ledger.recover(VERIFY_AT)
    c8_rig["provider"].fail = None
    assert verify(c8_rig, "crash-retry")["status"] == "NOT_RUN"
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]
    assert ledger.accounting()["charged_attempts"] == 4
    assert any(r["body"]["event"].get("status") == "CRASH" for r in ledger.events())


def test_directory_experiment_and_timestamp_reset_cannot_make_verify_unseen(c8_rig, tmp_path):
    register(c8_rig)
    fit(c8_rig)
    choose(c8_rig)
    verify(c8_rig)
    plan = deepcopy(c8_rig["plan"])
    plan["ledger_id"], plan["campaign_id"] = "renamed-ledger", "renamed-campaign"
    plan["registered_at"] = VERIFY_AT.isoformat()
    new = CalibrationLedger(tmp_path / "renamed-c8", c8_rig["ledger"].registry)
    with pytest.raises(IntegrityFailure):
        register_calibration(new, *c8_rig["source"], plan)
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_VERIFY"]


def test_registered_fit_may_be_reexamined_before_verify_with_every_attempt_charged(c8_rig):
    register(c8_rig)
    assert fit(c8_rig)["status"] == fit(c8_rig, "registered-second-fit")["status"] == "PASS"
    assert c8_rig["ledger"].accounting()["charged_attempts"] == 2
    assert c8_rig["provider"].reads == ["CAL_FIT", "CAL_FIT"]


@pytest.mark.parametrize("mutation", ["future_feature", "future_dataset", "long_label", "publication_equality"])
def test_no_lookahead_and_primary_stress_boundaries_before_content_access(c8_rig, mutation):
    sample = c8_rig["plan"]["datasets"]["CAL_FIT"]["samples"][0]
    if mutation == "future_feature":
        sample["observations"][0]["available_at"] = "2030-01-06T00:00:00+00:00"
    elif mutation == "future_dataset":
        c8_rig["plan"]["datasets"]["CAL_FIT"]["available_at"] = "2032-01-01T00:00:00+00:00"
    elif mutation == "long_label":
        sample["label_end"] = sample["label_available_at"] = "2031-01-01T00:00:00+00:00"
    else:
        sample["label_available_at"] = "2030-02-01T00:00:00+00:00"
    refresh_partition(c8_rig, "CAL_FIT")
    register(c8_rig)
    result = fit(c8_rig)
    assert result["status"] == ("NOT_RUN" if mutation == "publication_equality" else "FAIL")
    assert c8_rig["provider"].reads == []


def test_actual_upstream_invalidation_is_resolved_before_new_calibration_read(c8_rig):
    register(c8_rig)
    ledger = c8_rig["source"][0]
    path = ledger.directory / "selection-acceptance.json"
    body = json.loads(path.read_text())
    body["official"] = True
    path.write_text(json.dumps(body))
    result = fit(c8_rig)
    assert result["status"] == "FAIL"
    assert c8_rig["provider"].reads == []
    assert c8_rig["ledger"].accounting()["charged_attempts"] == 1


@pytest.mark.parametrize("mutation", ["cohort", "subset", "model", "tax", "report_version", "fake_real", "no_controls"])
def test_actual_payload_is_resolved_not_producer_pass(c8_rig, mutation):
    body = c8_rig["provider"].bodies["CAL_FIT"]
    cohort = next(iter(body["cohorts"]))
    candidate = next(iter(body["cohorts"][cohort]))
    if mutation == "cohort":
        body["cohorts"].pop(cohort)
    elif mutation == "subset":
        body["cohorts"][cohort].pop(candidate)
    elif mutation == "model":
        body["cohorts"][cohort][candidate]["frozen_instance"]["model_hash"] = "mutated"
    elif mutation == "tax":
        body["tax_mode"] = "INCLUDED"
    elif mutation == "report_version":
        body["cohorts"][cohort][candidate]["metric_report"]["metric_version"] = "new-method"
    elif mutation == "fake_real":
        body["scope"] = "REAL_PIT_RESEARCH_VALIDATION"
    else:
        body["cohorts"][cohort][candidate]["controls"] = {}
    # Bind these bytes to preregistration to exercise semantic validation, not just hashes.
    c8_rig["plan"]["datasets"]["CAL_FIT"]["content_hash"] = sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    c8_rig["provider"].metadata["CAL_FIT"] = deepcopy(c8_rig["plan"]["datasets"]["CAL_FIT"])
    register(c8_rig)
    result = fit(c8_rig)
    assert result["status"] == ("NOT_RUN" if mutation in ("cohort", "no_controls") else "FAIL")
    assert c8_rig["provider"].reads == ["CAL_FIT"]
    assert result["research_state"] is None


def test_missing_threshold_registry_blocks_choice_and_verify_without_defaults(c8_rig):
    c8_rig["plan"]["threshold_registration"] = None
    register(c8_rig)
    fit(c8_rig)
    event = {"event_id": "missing", "actor_id": "fixture", "kind": "EXPLICIT_SOFTWARE_FIXTURE_CHOICE",
             "at": FIT_AT.isoformat(), "registration_hash": c8_rig["ledger"].registration()["sha256"],
             "approval_blob": c8_rig["plan"]["approval_blob"]}
    result = record_fixture_threshold_choice(c8_rig["ledger"], *c8_rig["source"],
        fit_attempt_id="fit", vector_id="none", rounded_vector={}, approval_event=event,
        attempt_id="choice", at=FIT_AT)
    assert result["status"] == "NOT_RUN"
    assert verify(c8_rig)["status"] == "NOT_RUN"
    assert c8_rig["provider"].reads == ["CAL_FIT"]


def test_explicit_choice_preserves_alternatives_without_merit_ranking(c8_rig):
    register(c8_rig)
    fit(c8_rig)
    result = choose(c8_rig, vector_id="fixture-b")
    assert result["status"] == "PASS"
    assert result["output"]["vector_id"] == "fixture-b"
    assert result["output"]["eligibility_decision"] is None
    assert set(c8_rig["ledger"].registration()["body"]["plan"]["threshold_registration"]["vectors"]) == {"fixture-a", "fixture-b"}
    assert choose(c8_rig, "second-choice")["status"] == "NOT_RUN"


def test_rounding_support_cannot_be_changed_after_fit(c8_rig):
    register(c8_rig)
    fit(c8_rig)
    ledger = c8_rig["ledger"]
    event = {"event_id": "changed-rounding", "actor_id": "fixture", "kind": "EXPLICIT_SOFTWARE_FIXTURE_CHOICE",
             "at": FIT_AT.isoformat(), "registration_hash": ledger.registration()["sha256"],
             "approval_blob": c8_rig["plan"]["approval_blob"]}
    result = record_fixture_threshold_choice(ledger, *c8_rig["source"], fit_attempt_id="fit",
        vector_id="fixture-a", rounded_vector={"fixture_only_threshold": .1},
        approval_event=event, attempt_id="bad-rounding", at=FIT_AT)
    assert result["status"] == "FAIL"


def test_holdout_boundary_is_bound_to_current_registered_upstream_metadata(c8_rig):
    c8_rig["plan"]["holdout_boundary"] = "2032-01-01T00:00:00+00:00"
    with pytest.raises(IntegrityFailure):
        register(c8_rig)
    assert c8_rig["provider"].reads == []


def test_no_holdout_read_function_even_with_provider_argument(c8_rig):
    register(c8_rig)
    with pytest.raises(IntegrityFailure):
        read_partition(c8_rig["ledger"], *c8_rig["source"], c8_rig["provider"],
                       role="HOLDOUT", attempt_id="forbidden", at=FIT_AT)
    assert c8_rig["provider"].reads == []


def test_upstream_change_during_read_cannot_leave_saved_pass(c8_rig):
    register(c8_rig)
    source_ledger = c8_rig["source"][0]
    path = source_ledger.directory / "selection-acceptance.json"

    def change_source(role):
        body = json.loads(path.read_text())
        body["official"] = True
        path.write_text(json.dumps(body))
    c8_rig["provider"].before_read = change_source
    assert fit(c8_rig)["status"] == "FAIL"
    assert c8_rig["provider"].reads == ["CAL_FIT"]


def test_real_upstream_declaration_blocks_before_any_ancestor_validation(monkeypatch):
    from investment_system.evl import calibration_protocol as protocol
    calls = []
    monkeypatch.setattr(protocol, "selection_registration",
                        lambda ledger: {"body": {"plan": {
                            "scope": "REAL_PIT_RESEARCH_VALIDATION",
                            "configuration_scope": "REAL_CONFIGURATION"}}})
    monkeypatch.setattr(protocol, "resolve_selection", lambda *args: calls.append("real-validation"))
    with pytest.raises(MissingPrerequisite):
        protocol.describe_upstream(object(), {})
    with pytest.raises(MissingPrerequisite):
        protocol.upstream_snapshot(object(), {})
    assert calls == []


def test_cached_qualified_source_cannot_mask_changed_source_bytes(c8_rig):
    from investment_system.evl.calibration_protocol import describe_upstream
    first = describe_upstream(*c8_rig["source"])
    assert describe_upstream(*c8_rig["source"]) == first
    path = c8_rig["source"][0].directory / "selection-acceptance.json"
    body = json.loads(path.read_text())
    body["official"] = True
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        describe_upstream(*c8_rig["source"])


def test_current_hash_proof_includes_mutable_input_objects(c8_rig):
    register(c8_rig)
    cohort = next(iter(c8_rig["source"][1].values()))
    drift = cohort[4]
    identity = next(iter(drift))
    drift[identity][0]["parameters"]["cash_buffer"] += .001
    assert fit(c8_rig)["status"] == "FAIL"
    assert c8_rig["provider"].reads == []
