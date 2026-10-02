"""QGV invalidation binding. No grant is issued. Scores are not recomputed."""

from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from investment_system.producers.serialization import canonical_sha256
from investment_system.publication.authorization import ACTIVE_AUTHORIZATIONS, summarize_grants
from investment_system.publication.invalidation import (
    CONTRACT,
    InvalidationContractError,
    _resolve_indexed,
    admit,
    event_id,
    resolve_target,
    validate_event,
)
from investment_system.publication.qgv_binding import (
    PRODUCER_ID,
    BindingContractError,
    build_binding,
    provenance_from_persisted,
    provenance_sha256,
    resolve_binding,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "investment_system" / "publication"
T0 = datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)
T2 = T0 + timedelta(days=2)
HEX = {
    "weights": "11" * 32,
    "members": "22" * 32,
    "inputs": "33" * 32,
    "other": "44" * 32,
}
COMMIT = "ce587040e7beb31b66a423eab6ca89767f2a2cf8"
AUTHORITY = "approval-event:not-a-validation-status"


def _semantic(total: int = 10) -> dict:
    return {
        "company_id": "c1",
        "as_of": "2024-12-31T00:00:00+00:00",
        "universe": {"universe_id": "uni_test"},
        "methodology": _methodology(),
        "qgv": {"total_score": total, "V_score": 0.2},
        "cross_section": {"rank": 4},
    }


def _methodology() -> dict:
    return {
        "qgv_system_version": "QGV_SYSTEM_V1",
        "qgv_standard_version": "QGV_STANDARD_V1",
        "qgv_analysis_contract": "QGV_ANALYSIS_V1",
        "implementation_line": "FROZEN_TRACK_A_LINE",
        "weights_sha256": HEX["weights"],
        "cross_section_rule_id": "vertical_slice_rule",
        "cross_section_rule_status": "PROVISIONAL_RESEARCH",
    }


def _company(total: int = 10, **operational) -> dict:
    semantic = _semantic(total)
    record = {
        "record_kind": "QGV_COMPANY_RESULT",
        "record_version": 1,
        "semantic": semantic,
        "semantic_sha256": canonical_sha256(semantic),
        "operational": {"generated_at": "2026-10-01T00:00:00+00:00", "qgv_snapshot_id": "uuid-1", **operational},
    }
    return record


def _manifest(company: dict, *, commit: str = COMMIT, scope: str | None = None, generated_at: str = "2026-10-01T00:00:00+00:00") -> dict:
    semantic = {
        "as_of": company["semantic"]["as_of"],
        "universe": {"universe_id": "uni_test", "members_sha256": HEX["members"]},
        "methodology": _methodology(),
        "data_lineage": {"inputs_sha256": HEX["inputs"]},
        "records": [{"company_id": company["semantic"]["company_id"], "semantic_sha256": company["semantic_sha256"]}],
    }
    if scope is not None:
        semantic["scope"] = scope
    return {
        "manifest_kind": "QGV_PRODUCER_BATCH_MANIFEST",
        "manifest_version": 1,
        "semantic": semantic,
        "semantic_sha256": canonical_sha256(semantic),
        "operational": {"generated_at": generated_at, "code_commit": commit, "run_id": "run-1"},
    }


def _event(target: str, state: str = "CLEAR", reason: str = "EXPLICIT_CLEAR", *, supersedes: str | None = None,
           effective_at: str = "2026-10-02T11:00:00+00:00", available_at: str = "2026-10-02T11:00:00+00:00",
           authority: str = AUTHORITY) -> dict:
    return {
        "contract": CONTRACT,
        "schema_version": 1,
        "target_sha256": target,
        "state": state,
        "reason_code": reason,
        "effective_at": effective_at,
        "available_at": available_at,
        "supersedes": supersedes,
        "authority_ref": authority,
    }


def _clear_for(company: dict, manifest: dict) -> dict:
    return _event(provenance_sha256(provenance_from_persisted(company, manifest)))


def test_module_does_not_import_engines_or_issue_grants():
    banned = ("qgv_producer", "qgv.factors", "leaderboard", "macro", "technical", "evl", "track_c")
    for name in ("invalidation.py", "qgv_binding.py"):
        tree = ast.parse((SRC / name).read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not any(any(token in item for token in banned) for item in imported)
    assert ACTIVE_AUTHORIZATIONS == ()
    assert summarize_grants() == {"research_display": "NONE", "frozen": "NONE", "live": "NONE"}


def test_reconstruction_is_deterministic_and_ignores_operational_noise():
    company = _company()
    first = build_binding(company, _manifest(company), _clear_for(company, _manifest(company)))
    second = build_binding(company, _manifest(company, generated_at="2030-01-01T00:00:00+00:00"), _clear_for(company, _manifest(company)))
    noisy = _company(qgv_snapshot_id="uuid-2")
    third = build_binding(noisy, _manifest(noisy, generated_at="1999-01-01T00:00:00Z"), _clear_for(noisy, _manifest(noisy)))
    assert first["subject_sha256"] == second["subject_sha256"] == third["subject_sha256"]
    assert first["provenance_sha256"] == provenance_sha256(first["provenance"])
    assert first["subject_sha256"] == canonical_sha256(first["binding"])
    assert "total_score" not in first["provenance"]
    assert "generated_at" not in first["provenance"]
    assert "qgv_snapshot_id" not in first["provenance"]
    assert "scope" not in first["provenance"]
    assert first["publication"] == "NOT_AVAILABLE"
    assert first["research_display_grant"] == "NONE"
    full = build_binding(company, _manifest(company, scope="FULL"), _clear_for(company, _manifest(company, scope="FULL")))
    sample = build_binding(company, _manifest(company, scope="SAMPLE"), _clear_for(company, _manifest(company, scope="SAMPLE")))
    assert full["subject_sha256"] == sample["subject_sha256"]


def test_code_commit_or_lineage_change_is_a_different_subject_without_rescoring():
    company = _company()
    original = _company()
    changed_commit = build_binding(company, _manifest(company, commit=COMMIT[:-1] + "0"), _clear_for(company, _manifest(company, commit=COMMIT[:-1] + "0")))
    base = build_binding(original, _manifest(original), _clear_for(original, _manifest(original)))
    assert changed_commit["subject_sha256"] != base["subject_sha256"]
    assert changed_commit["provenance"]["persisted_output_sha256"] == base["provenance"]["persisted_output_sha256"]
    rescored = _company(total=11)
    assert rescored["semantic"]["qgv"]["total_score"] == 11
    rebound = build_binding(rescored, _manifest(rescored), _clear_for(rescored, _manifest(rescored)))
    assert rebound["provenance"]["persisted_output_sha256"] != base["provenance"]["persisted_output_sha256"]
    assert original["semantic"]["qgv"]["total_score"] == 10


def test_hash_mismatch_is_not_repaired():
    company = _company()
    company["semantic"]["qgv"]["total_score"] = 99
    with pytest.raises(BindingContractError, match="semantic_sha256"):
        provenance_from_persisted(company, _manifest(_company()))


def test_missing_clear_event_is_unbound_and_not_inferred():
    company = _company()
    manifest = _manifest(company)
    target = provenance_sha256(provenance_from_persisted(company, manifest))
    assert resolve_target((), target, T1)["resolution"] == "UNSTATED"
    with pytest.raises(InvalidationContractError):
        build_binding(company, manifest, None)


def test_explicit_clear_is_current_but_not_a_grant():
    company = _company()
    manifest = _manifest(company)
    event = _clear_for(company, manifest)
    built = build_binding(company, manifest, event)
    resolution = resolve_binding(built["binding"], (event,), T1)
    assert resolution["current_valid"] is True
    assert resolution["not_bindable"] is False
    assert resolution["provenance_resolution"] == "CLEAR"
    assert resolution["publication"] == "NOT_AVAILABLE"
    assert resolution["research_display_grant"] == "NONE"
    assert resolution["frozen_grant"] == "NONE"
    assert resolution["live_grant"] == "NONE"
    assert ACTIVE_AUTHORIZATIONS == ()


def test_component_absence_does_not_block_or_imply_clear():
    company = _company()
    manifest = _manifest(company)
    event = _clear_for(company, manifest)
    built = build_binding(company, manifest, event)
    resolution = resolve_binding(built["binding"], (event,), T1)
    assert resolution["component_veto"] == ()
    assert resolution["current_valid"] is True
    for field in ("persisted_output_sha256", "inputs_sha256", "members_sha256", "weights_sha256"):
        assert resolve_target((), built["provenance"][field], T1)["resolution"] == "UNSTATED"


def test_component_event_can_veto_and_component_clear_does_not_grant():
    company = _company()
    manifest = _manifest(company)
    event = _clear_for(company, manifest)
    built = build_binding(company, manifest, event)
    veto = _event(HEX["inputs"], "INVALIDATED", "LINEAGE_NO_LONGER_CURRENT")
    blocked = resolve_binding(built["binding"], (event, veto), T1)
    assert blocked["current_valid"] is False
    assert blocked["not_bindable"] is True
    assert blocked["provenance_resolution"] == "CLEAR"
    assert blocked["publication"] == "NOT_AVAILABLE"
    assert blocked["component_veto"][0]["field"] == "inputs_sha256"
    component_clear = _event(HEX["inputs"], "CLEAR", "EXPLICIT_CLEAR", authority="component-clear")
    still = resolve_binding(built["binding"], (event, component_clear), T1)
    assert still["current_valid"] is True
    assert still["research_display_grant"] == "NONE"
    assert still["component_veto"] == ()


def test_pit_hides_later_available_events_and_does_not_rewrite_the_past():
    company = _company()
    manifest = _manifest(company)
    clear = _clear_for(company, manifest)
    built = build_binding(company, manifest, clear)
    later = _event(
        built["provenance_sha256"], "INVALIDATED", "INTEGRITY_FAILURE",
        supersedes=built["event_id"],
        effective_at="2026-10-03T00:00:00+00:00",
        available_at="2026-10-04T00:00:00+00:00",
    )
    log = admit((clear,), later)
    early = resolve_binding(built["binding"], log, T1)
    assert early["current_valid"] is True
    assert early["provenance_resolution"] == "CLEAR"
    late_clock = datetime(2026, 10, 4, 1, tzinfo=timezone.utc)
    after = resolve_binding(built["binding"], log, late_clock)
    assert after["provenance_resolution"] == "INVALIDATED"
    assert after["current_valid"] is False
    assert after["research_display_grant"] == "NONE"
    assert resolve_binding(built["binding"], log, T1)["current_valid"] is True


def test_successor_without_visible_predecessor_is_invalid_chain():
    company = _company()
    manifest = _manifest(company)
    clear = _clear_for(company, manifest)
    built = build_binding(company, manifest, clear)
    hidden_parent = dict(clear, available_at="2026-10-05T00:00:00+00:00")
    child = _event(
        built["provenance_sha256"], "SUSPENDED", "HOLD_PENDING_REVIEW",
        supersedes=event_id(hidden_parent),
        effective_at="2026-10-01T00:00:00+00:00",
        available_at="2026-10-02T00:00:00+00:00",
    )
    seen = resolve_target((hidden_parent, child), built["provenance_sha256"], T1)
    assert seen["resolution"] == "INVALID_CHAIN"
    assert seen["defect"] == "missing_predecessor"
    assert seen["event_id"] is None


def test_chain_defects_are_not_resolved_by_timestamp():
    target = HEX["other"]
    early = _event(target, effective_at="2026-10-01T00:00:00+00:00", available_at="2026-10-01T00:00:00+00:00", authority="a")
    late = _event(target, effective_at="2026-12-01T00:00:00+00:00", available_at="2026-12-01T00:00:00+00:00", authority="b")
    heads = resolve_target((early, late), target, datetime(2026, 12, 2, tzinfo=timezone.utc))
    assert heads["resolution"] == "INVALID_CHAIN"
    assert heads["defect"] == "multiple_heads"
    assert heads["event_id"] is None
    parent = _event(target, authority="parent")
    left = _event(target, "SUSPENDED", "HOLD_PENDING_REVIEW", supersedes=event_id(parent), authority="left",
                  effective_at="2026-10-03T00:00:00+00:00", available_at="2026-10-03T00:00:00+00:00")
    right = _event(target, "INVALIDATED", "INTEGRITY_FAILURE", supersedes=event_id(parent), authority="right",
                   effective_at="2026-11-01T00:00:00+00:00", available_at="2026-11-01T00:00:00+00:00")
    branched = resolve_target((parent, left, right), target, datetime(2026, 12, 2, tzinfo=timezone.utc))
    assert branched["resolution"] == "INVALID_CHAIN"
    assert branched["defect"] == "branching"
    left_id = "aa" * 32
    right_id = "bb" * 32
    cycled = _resolve_indexed({
        left_id: {"target_sha256": target, "supersedes": right_id, "state": "CLEAR", "effective_at": "2026-10-02T00:00:00+00:00"},
        right_id: {"target_sha256": target, "supersedes": left_id, "state": "CLEAR", "effective_at": "2026-10-03T00:00:00+00:00"},
    }, target)
    assert cycled["resolution"] == "INVALID_CHAIN"
    assert cycled["defect"] == "cycle"
    other = _event(HEX["inputs"], authority="other-target")
    cross = _event(target, "SUSPENDED", "HOLD_PENDING_REVIEW", supersedes=event_id(other), authority="cross")
    crossed = resolve_target((other, cross), target, T2)
    assert crossed["resolution"] == "INVALID_CHAIN"
    assert crossed["defect"] == "cross_target"
    terminal = _event(target, "INVALIDATED", "EVIDENCE_SUPERSEDED", authority="terminal")
    follower = _event(target, supersedes=event_id(terminal), authority="follower",
                      effective_at="2026-10-03T00:00:00+00:00", available_at="2026-10-03T00:00:00+00:00")
    followed = resolve_target((terminal, follower), target, T2)
    assert followed["resolution"] == "INVALID_CHAIN"
    assert followed["defect"] == "invalidated_successor"
    same_time_b = _event(target, supersedes=event_id(parent), authority="same-b",
                         effective_at=parent["effective_at"], available_at="2026-10-03T00:00:00+00:00")
    ambiguous = resolve_target((parent, same_time_b), target, T2)
    assert ambiguous["resolution"] == "AMBIGUOUS"
    assert ambiguous["defect"] == "equal_effective_at"


def test_admit_rejects_structural_appends_without_sorting():
    target = HEX["other"]
    parent = _event(target, authority="parent")
    log = admit((), parent)
    assert admit(log, _event(target, "SUSPENDED", "HOLD_PENDING_REVIEW", supersedes=event_id(parent), authority="child",
                             effective_at="2026-10-01T00:00:00+00:00", available_at="2026-10-03T00:00:00+00:00"))[0] == parent
    with pytest.raises(InvalidationContractError, match="duplicate"):
        admit(log, parent)
    with pytest.raises(InvalidationContractError, match="missing predecessor"):
        admit(log, _event(target, supersedes="ab" * 32, authority="missing"))
    log = admit((), parent)
    with pytest.raises(InvalidationContractError, match="cross-target"):
        admit(log, _event(HEX["inputs"], supersedes=event_id(parent), authority="cross"))
    terminal = _event(target, "INVALIDATED", "INTEGRITY_FAILURE", authority="terminal")
    with pytest.raises(InvalidationContractError, match="terminal"):
        admit((terminal,), _event(target, supersedes=event_id(terminal), authority="after"))
    with pytest.raises(InvalidationContractError, match="reason_code"):
        validate_event(_event(target, "CLEAR", "INTEGRITY_FAILURE"))
    naive = _event(target)
    naive["effective_at"] = "2026-10-02T11:00:00"
    with pytest.raises(InvalidationContractError, match="timezone-aware"):
        validate_event(naive)


def test_suspended_is_not_current_and_does_not_restore_an_invalidated_target():
    company = _company()
    manifest = _manifest(company)
    suspended = _event(provenance_sha256(provenance_from_persisted(company, manifest)), "SUSPENDED", "HOLD_PENDING_REVIEW")
    built = build_binding(company, manifest, suspended)
    resolution = resolve_binding(built["binding"], (suspended,), T1)
    assert resolution["provenance_resolution"] == "SUSPENDED"
    assert resolution["current_valid"] is False
    assert resolution["publication"] == "NOT_AVAILABLE"


def test_as_of_text_is_not_normalized():
    company = _company()
    company["semantic"]["as_of"] = "2024-12-31T00:00:00Z"
    company["semantic_sha256"] = canonical_sha256(company["semantic"])
    manifest = _manifest(company)
    provenance = provenance_from_persisted(company, manifest)
    assert provenance["as_of"] == "2024-12-31T00:00:00Z"


def test_producer_id_is_the_persisted_literal():
    company = _company()
    manifest = _manifest(company)
    manifest["producer_id"] = "macro.real.v1"
    with pytest.raises(BindingContractError, match="producer_id"):
        provenance_from_persisted(company, manifest)
    assert provenance_from_persisted(company, _manifest(company))["producer_id"] == PRODUCER_ID


def test_copy_does_not_mutate_persisted_documents():
    company = _company()
    manifest = _manifest(company)
    before_company = copy.deepcopy(company)
    before_manifest = copy.deepcopy(manifest)
    build_binding(company, manifest, _clear_for(company, manifest))
    assert company == before_company
    assert manifest == before_manifest
