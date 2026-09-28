"""Golden and counterfactual fixture runner.

Golden fixture (fixtures/golden/*.json):
    {"id", "title", "status", "input": <GameState dict>, "expect": <expectation>}

Counterfactual set (fixtures/counterfactual/*.json):
    {"base": "<golden id>", "variants": [
        {"id", "title", "patch": <partial GameState dict>,
         "expect": <expectation>} | {"id", "title", "patch", "unchanged_from_base": true}
    ]}

Expectation keys are all optional; only the keys present are checked:
    permission       "P0".."P5"
    opportunities    ["PUNISH", ...] (exact, ordered)
    recommended      action name, or null for "no recommendation"
    actions          {ACTION: {"validity", "reasons" (exact), "reasons_include",
                               "unlock_conditions" (exact), "unlock_include"}}
    trace            [[stage, code], ...] (exact, ordered)
    same_as_golden   golden id whose full decision must be identical
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.decision.engine import analyze
from backend.decision.models import Decision
from backend.state.models import GameState

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "fixtures"


@dataclass
class FixtureResult:
    fixture_id: str
    kind: str
    title: str
    mismatches: list[str] = field(default_factory=list)
    changed_from_base: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.mismatches


def deep_merge(base: dict, patch: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    """JSON-comparable view of a Decision (enum members become their values)."""
    return json.loads(json.dumps(asdict(decision), default=str))


def summarize(decision: Decision) -> dict[str, Any]:
    recommended = [evaluation.action.value for evaluation in decision.actions if evaluation.recommended]
    return {
        "permission": decision.permission.name,
        "opportunities": list(decision.opportunities),
        "recommended": recommended[0] if len(recommended) == 1 else recommended or None,
        "actions": {
            evaluation.action.value: {
                "validity": evaluation.validity.value,
                "reasons": [reason.value for reason in evaluation.reasons],
                "unlock_conditions": list(evaluation.unlock_conditions),
            }
            for evaluation in decision.actions
        },
        "trace": [[entry.stage, entry.code] for entry in decision.trace],
    }


def run_state(state_input: dict) -> Decision:
    return analyze(GameState.model_validate(state_input))


def check_expectation(
    decision: Decision,
    expect: dict,
    goldens: dict[str, dict] | None = None,
) -> list[str]:
    actual = summarize(decision)
    mismatches: list[str] = []

    for key in ("permission", "opportunities", "recommended", "trace"):
        if key in expect and expect[key] != actual[key]:
            mismatches.append(f"{key}: expected {expect[key]!r}, got {actual[key]!r}")

    for action, action_expect in expect.get("actions", {}).items():
        got = actual["actions"].get(action)
        if got is None:
            mismatches.append(f"actions.{action}: not evaluated")
            continue
        if "validity" in action_expect and action_expect["validity"] != got["validity"]:
            mismatches.append(
                f"actions.{action}.validity: expected {action_expect['validity']}, got {got['validity']}"
            )
        for key in ("reasons", "unlock_conditions"):
            if key in action_expect and action_expect[key] != got[key]:
                mismatches.append(f"actions.{action}.{key}: expected {action_expect[key]!r}, got {got[key]!r}")
        for key, target in (("reasons_include", "reasons"), ("unlock_include", "unlock_conditions")):
            missing = [item for item in action_expect.get(key, []) if item not in got[target]]
            if missing:
                mismatches.append(f"actions.{action}.{target}: missing {missing!r}, got {got[target]!r}")

    if "same_as_golden" in expect:
        golden_id = expect["same_as_golden"]
        golden = (goldens or {}).get(golden_id)
        if golden is None:
            mismatches.append(f"same_as_golden: unknown golden {golden_id}")
        elif decision_to_dict(decision) != decision_to_dict(run_state(golden["input"])):
            mismatches.append(f"same_as_golden: decision differs from {golden_id}")

    return mismatches


def diff_summaries(base: dict, other: dict, prefix: str = "") -> list[str]:
    changes: list[str] = []
    for key in sorted(set(base) | set(other)):
        path = f"{prefix}{key}"
        left, right = base.get(key), other.get(key)
        if isinstance(left, dict) and isinstance(right, dict):
            changes.extend(diff_summaries(left, right, f"{path}."))
        elif left != right:
            changes.append(f"{path}: {left!r} -> {right!r}")
    return changes


def load_json_dir(directory: Path) -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]


def load_goldens(root: Path = FIXTURE_ROOT) -> dict[str, dict]:
    goldens: dict[str, dict] = {}
    for fixture in load_json_dir(root / "golden"):
        if fixture["id"] in goldens:
            raise ValueError(f"duplicate golden fixture id {fixture['id']}")
        goldens[fixture["id"]] = fixture
    return goldens


def run_golden(fixture: dict, goldens: dict[str, dict]) -> FixtureResult:
    result = FixtureResult(fixture["id"], "GOLDEN", fixture.get("title", ""))
    try:
        result.mismatches = check_expectation(run_state(fixture["input"]), fixture["expect"], goldens)
    except Exception as error:  # a malformed fixture must fail, not crash the run
        result.mismatches = [f"error: {type(error).__name__}: {error}"]
    return result


def run_counterfactual(variant: dict, base: dict, goldens: dict[str, dict]) -> FixtureResult:
    result = FixtureResult(variant["id"], "COUNTERFACTUAL", variant.get("title", ""))
    try:
        base_decision = run_state(base["input"])
        decision = run_state(deep_merge(base["input"], variant["patch"]))
        result.changed_from_base = diff_summaries(summarize(base_decision), summarize(decision))
        if variant.get("unchanged_from_base"):
            if decision_to_dict(decision) != decision_to_dict(base_decision):
                result.mismatches.append(
                    "unchanged_from_base: decision changed: " + "; ".join(result.changed_from_base)
                )
        else:
            result.mismatches = check_expectation(decision, variant["expect"], goldens)
            if not result.changed_from_base:
                result.mismatches.append("counterfactual produced no change from base; use unchanged_from_base")
    except Exception as error:
        result.mismatches = [f"error: {type(error).__name__}: {error}"]
    return result


def run_all(root: Path = FIXTURE_ROOT) -> list[FixtureResult]:
    goldens = load_goldens(root)
    results = [run_golden(fixture, goldens) for fixture in goldens.values()]
    seen: set[str] = set(goldens)
    for counterfactual_set in load_json_dir(root / "counterfactual"):
        base = goldens.get(counterfactual_set["base"])
        for variant in counterfactual_set["variants"]:
            if variant["id"] in seen:
                raise ValueError(f"duplicate fixture id {variant['id']}")
            seen.add(variant["id"])
            if base is None:
                results.append(
                    FixtureResult(variant["id"], "COUNTERFACTUAL", variant.get("title", ""),
                                  [f"unknown base golden {counterfactual_set['base']}"])
                )
                continue
            results.append(run_counterfactual(variant, base, goldens))
    return results
