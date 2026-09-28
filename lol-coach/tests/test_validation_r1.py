"""R1: fixture runner, GF-001/GF-002, counterfactual and metamorphic validation.

Also self-tests the runner (it must detect wrong expectations) and guards that the
core is byte-identical to the R0 import.
"""

import functools
import hashlib
import json
from pathlib import Path

import pytest

from backend.decision.permission import PermissionLevel
from backend.state.models import JungleState
from validation import fixture_runner, metamorphic

ROOT = Path(__file__).resolve().parent.parent


@functools.cache
def metamorphic_results():
    return {result.relation_id: result for result in metamorphic.run_all()}


def results_by_id():
    return {result.fixture_id: result for result in fixture_runner.run_all()}


def test_core_unchanged_since_r0():
    manifest = json.loads((ROOT / "tests" / "core_manifest_r0.json").read_text())["files"]
    actual = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "backend").rglob("*.py"))
    }
    assert actual == manifest


def test_golden_fixtures_present():
    assert set(fixture_runner.load_goldens()) == {"GF-001", "GF-002"}


@pytest.mark.parametrize("fixture_id", ["GF-001", "GF-002"])
def test_golden_fixture_passes(fixture_id):
    result = results_by_id()[fixture_id]
    assert result.passed, result.mismatches


def test_all_counterfactuals_pass():
    results = [result for result in fixture_runner.run_all() if result.kind == "COUNTERFACTUAL"]
    assert len(results) == 10
    failing = {result.fixture_id: result.mismatches for result in results if not result.passed}
    assert failing == {}


def test_counterfactual_symmetry_between_goldens():
    results = results_by_id()
    # GF-001 with jungle NEAR == GF-002, and GF-002 with jungle UNKNOWN == GF-001.
    assert results["CF-001-B"].passed and results["CF-001-B"].changed_from_base
    assert results["CF-002-A"].passed and results["CF-002-A"].changed_from_base


@pytest.mark.parametrize("relation_id", [relation[0] for relation in metamorphic.RELATIONS])
def test_metamorphic_relation(relation_id):
    result = metamorphic_results()[relation_id]
    assert result.checked > 0
    assert result.passed, result.violations[:3]


def test_state_space_is_exhaustive():
    assert sum(1 for _ in metamorphic.all_states()) == 4 * 3 * 3 * 3 * 4 * 3


# --- runner self-tests: a validator that cannot fail proves nothing ---------------


def golden(fixture_id="GF-001"):
    return fixture_runner.load_goldens()[fixture_id]


def test_runner_detects_wrong_expectation():
    fixture = golden()
    fixture["expect"] = {
        "permission": "P5",
        "recommended": "ALL_IN",
        "actions": {"CHASE": {"validity": "VALID", "reasons_include": ["LOW_REVERSIBILITY"]}},
    }
    mismatches = fixture_runner.run_golden(fixture, fixture_runner.load_goldens()).mismatches
    assert any(m.startswith("permission") for m in mismatches)
    assert any(m.startswith("recommended") for m in mismatches)
    assert any(m.startswith("actions.CHASE.validity") for m in mismatches)
    assert any(m.startswith("actions.CHASE.reasons") for m in mismatches)


def test_runner_detects_unknown_action_and_golden():
    fixture = golden()
    fixture["expect"] = {"actions": {"FREEZE": {"validity": "VALID"}}, "same_as_golden": "GF-999"}
    mismatches = fixture_runner.run_golden(fixture, fixture_runner.load_goldens()).mismatches
    assert "actions.FREEZE: not evaluated" in mismatches
    assert "same_as_golden: unknown golden GF-999" in mismatches


def test_runner_reports_malformed_input_as_failure():
    fixture = golden()
    fixture["input"] = {"power": {"matchup": "NOT_A_STATE"}}
    result = fixture_runner.run_golden(fixture, {})
    assert not result.passed
    assert result.mismatches[0].startswith("error:")


def test_unchanged_from_base_detects_change():
    variant = {"id": "X", "patch": {"jungle": {"enemy": "CONFIRMED_FAR"}}, "unchanged_from_base": True}
    result = fixture_runner.run_counterfactual(variant, golden(), {})
    assert not result.passed
    assert "permission: 'P3' -> 'P4'" in result.changed_from_base


def test_counterfactual_without_effect_is_flagged():
    variant = {"id": "X", "patch": {"wave": {"state": "FAVORABLE"}}, "expect": {"permission": "P3"}}
    result = fixture_runner.run_counterfactual(variant, golden(), {})
    assert not result.passed
    assert "no change from base" in result.mismatches[0]


def test_metamorphic_detects_broken_monotonicity(monkeypatch):
    real_analyze = metamorphic.analyze

    def broken(state):
        decision = real_analyze(state)
        if state.jungle.enemy == JungleState.CONFIRMED_NEAR:
            decision.permission = PermissionLevel.P5
        return decision

    monkeypatch.setattr(metamorphic, "analyze", broken)
    result = metamorphic.RelationResult("MR-02", "DESIGN", "")
    metamorphic.mr_jungle_permission_monotone(result)
    assert not result.passed
    assert result.violations
