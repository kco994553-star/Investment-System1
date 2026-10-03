"""Durable complete accounting, interruption, concurrency and prefix protection."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import pytest
from investment_system.evl.calibration_ledger import CalibrationLedger
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from tests.evl_c8_fixture import c8_source, c8_rig, register, FIT_AT


def test_registration_immutable_even_before_first_read(c8_rig):
    register(c8_rig)
    with pytest.raises((ValueError, FileExistsError)):
        register(c8_rig)
    assert c8_rig["provider"].reads == []
    assert len([r for r in c8_rig["ledger"].events() if r["body"]["event"]["kind"] == "REGISTRATION"]) == 1


def test_all_fail_notrun_and_pending_are_charged_and_preserved(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]

    def fail(pending):
        raise IntegrityFailure("explicit-integrity-failure")

    def missing(pending):
        raise MissingPrerequisite("explicit-missing-support")

    assert ledger.execute("fail", "CONTROL_EVIDENCE", FIT_AT, fail)["status"] == "FAIL"
    assert ledger.execute("missing", "CONTROL_EVIDENCE", FIT_AT, missing)["status"] == "NOT_RUN"
    ledger.begin("pending", "CONTROL_EVIDENCE", FIT_AT)
    assert ledger.accounting()["charged_attempts"] == 3
    assert ledger.accounting()["pending"] == ["pending"]
    ledger.recover(FIT_AT)
    states = [r["body"]["event"].get("status") for r in ledger.events()]
    assert "FAIL" in states and "NOT_RUN" in states and "CRASH" in states
    assert ledger.accounting()["charged_attempts"] == 3
    with pytest.raises(MissingPrerequisite):
        ledger.receipt("pending")


def test_budget_exhaustion_is_logged_without_releasing_failed_charges(c8_rig):
    c8_rig["plan"]["budget"]["max_attempts"] = 1
    register(c8_rig)
    ledger = c8_rig["ledger"]
    assert ledger.execute("first", "CONTROL_EVIDENCE", FIT_AT, lambda p: {})["status"] == "PASS"
    ledger.invalidate("inv", "first", "revoked", FIT_AT)
    assert ledger.accounting()["charged_attempts"] == 1
    calls = []
    result = ledger.execute("over-budget", "CONTROL_EVIDENCE", FIT_AT, lambda p: calls.append(1))
    assert result["status"] == "NOT_RUN"
    assert result["reason"] == "REGISTERED_BUDGET_EXHAUSTED"
    assert calls == []
    assert ledger.accounting()["all_attempt_ids"] == ["first", "over-budget"]
    assert ledger.accounting()["charged_attempts"] == 1
    with pytest.raises(IntegrityFailure):
        ledger.receipt("first")


def test_invalidating_registration_preserves_history_and_blocks_future(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.execute("ok", "CONTROL_EVIDENCE", FIT_AT, lambda p: {})
    prefix = ledger.chain.path.read_bytes()
    ledger.invalidate("all", None, "approval/data invalidated", FIT_AT)
    assert ledger.chain.path.read_bytes().startswith(prefix)
    calls = []
    assert ledger.execute("blocked", "CONTROL_EVIDENCE", FIT_AT, lambda p: calls.append(1))["status"] == "NOT_RUN"
    assert calls == []
    with pytest.raises(IntegrityFailure):
        ledger.receipt("ok")


def test_crash_does_not_allow_same_attempt_rerun(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.begin("interrupted", "CAL_FIT", FIT_AT)
    with pytest.raises(IntegrityFailure):
        ledger.begin("interrupted", "CAL_FIT", FIT_AT)
    events = [r["body"]["event"] for r in ledger.events()]
    assert any(e["kind"] == "TERMINAL" and e["status"] == "CRASH" for e in events)
    assert sum(e["kind"] == "PENDING" for e in events) == 1


def test_two_writers_same_attempt_produce_once(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    calls = []

    def invoke(_):
        try:
            return ledger.execute("shared", "CONTROL_EVIDENCE", FIT_AT, lambda p: calls.append(1))["status"]
        except IntegrityFailure:
            return "REJECTED"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, range(2)))
    assert sorted(results) == ["PASS", "REJECTED"]
    assert calls == [1]
    assert ledger.accounting()["charged_attempts"] == 1


@pytest.mark.parametrize("mutation", ["truncate", "rewrite", "partial_tail", "registration"])
def test_checkpoint_detects_deleted_or_rewritten_history(c8_rig, mutation):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.execute("ok", "CONTROL_EVIDENCE", FIT_AT, lambda p: {"value": 1})
    if mutation == "truncate":
        lines = ledger.chain.path.read_text().splitlines()
        ledger.chain.path.write_text("\n".join(lines[:-1]) + "\n")
    elif mutation == "rewrite":
        raw = ledger.chain.path.read_text().replace('"value":1', '"value":2')
        # Event output is in immutable report bytes; change the event reason instead.
        raw = raw.replace('"status":"PASS"', '"status":"FAIL"')
        ledger.chain.path.write_text(raw)
    elif mutation == "partial_tail":
        ledger.chain.path.write_text(ledger.chain.path.read_text().rstrip("\n"))
    else:
        raw = json.loads(ledger.registration_path.read_text())
        raw["body"]["plan"]["budget"]["max_attempts"] += 1
        ledger.registration_path.write_text(json.dumps(raw))
    with pytest.raises(IntegrityFailure):
        ledger.events()


def test_terminal_report_hash_is_current_not_producer_pass(c8_rig):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.execute("ok", "CONTROL_EVIDENCE", FIT_AT, lambda p: {"value": 1})
    report = json.loads(ledger.report_path("ok").read_text())
    report["output"]["value"] = 999
    ledger.report_path("ok").write_text(json.dumps(report))
    with pytest.raises(IntegrityFailure):
        ledger.receipt("ok")


@pytest.mark.parametrize("operation", ["STATISTICAL_GATE", "PROFILE_DISTINCTNESS", "ROLE_ASSIGNMENT", "HOLDOUT"])
def test_unapproved_operations_have_no_ledger_execution_path(c8_rig, operation):
    register(c8_rig)
    with pytest.raises(IntegrityFailure):
        c8_rig["ledger"].begin("forbidden", operation, FIT_AT)
    assert c8_rig["ledger"].accounting()["charged_attempts"] == 0


def test_time_reset_is_not_preregistration(c8_rig):
    register(c8_rig)
    with pytest.raises(IntegrityFailure):
        c8_rig["ledger"].begin("backdated", "CAL_FIT",
                              c8_rig["plan"]["registered_at"].replace("2026", "2020"))
    assert c8_rig["provider"].reads == []


def test_path_like_attempt_id_cannot_escape_ledger_directory(c8_rig, tmp_path):
    register(c8_rig)
    ledger = c8_rig["ledger"]
    ledger.execute("../escape", "CONTROL_EVIDENCE", FIT_AT, lambda p: {})
    assert ledger.report_path("../escape").parent == ledger.directory
    assert not (tmp_path / "escape.json").exists()


def test_invalidation_requires_real_existing_parent(c8_rig):
    register(c8_rig)
    with pytest.raises(IntegrityFailure):
        c8_rig["ledger"].invalidate("bad", "unlogged", "invalid", FIT_AT)
