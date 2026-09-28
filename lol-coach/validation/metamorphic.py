"""Metamorphic relations checked over the full enumerable GameState space.

Every GameState field is an enum, so the space is finite (4*3*3*3*4*3 = 1296 states)
and each relation is checked exhaustively rather than by sampling.

Relation classes:
  DESIGN   - property implied by the v0.1 decision structure (safety/permission logic).
  CURRENT  - pins as-received behaviour that is tied to an Open Issue and is expected
             to be revised deliberately when that issue is closed in R2.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, Iterator

from backend.decision.actions import ActionType
from backend.decision.engine import analyze
from backend.decision.evaluator import VALIDITY_RANK
from backend.decision.opportunity import Opportunity
from backend.decision.models import Decision, Validity
from backend.state.models import (
    AccessState,
    GameState,
    JungleContext,
    JungleState,
    MatchupState,
    OpponentAction,
    OpponentContext,
    PowerState,
    ReturnPath,
    RiskContext,
    WaveContext,
    WaveState,
)
from validation.fixture_runner import decision_to_dict

MAX_EXAMPLES = 3


@dataclass
class RelationResult:
    relation_id: str
    kind: str
    title: str
    checked: int = 0
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.checked > 0 and not self.violations


def make_state(matchup, access, wave, jungle, opponent, return_path) -> GameState:
    return GameState(
        power=PowerState(matchup=matchup, access=access),
        wave=WaveContext(state=wave),
        jungle=JungleContext(enemy=jungle),
        opponent=OpponentContext(action=opponent),
        risk=RiskContext(return_path=return_path),
    )


AXES = (MatchupState, AccessState, WaveState, JungleState, OpponentAction, ReturnPath)


def all_states() -> Iterator[GameState]:
    for combo in itertools.product(*AXES):
        yield make_state(*combo)


def with_field(state: GameState, section: str, name: str, value) -> GameState:
    section_model = getattr(state, section).model_copy(update={name: value})
    return state.model_copy(update={section: section_model})


def describe(state: GameState) -> str:
    return (
        f"matchup={state.power.matchup.value} access={state.power.access.value} "
        f"wave={state.wave.state.value} jungle={state.jungle.enemy.value} "
        f"opponent={state.opponent.action.value} return={state.risk.return_path.value}"
    )


def recommended_actions(decision: Decision) -> list[ActionType]:
    return [evaluation.action for evaluation in decision.actions if evaluation.recommended]


def validity_map(decision: Decision) -> dict[ActionType, Validity]:
    return {evaluation.action: evaluation.validity for evaluation in decision.actions}


def record(result: RelationResult, ok: bool, message: Callable[[], str]) -> None:
    result.checked += 1
    if not ok:
        result.violations.append(message())


def mr_determinism(result: RelationResult) -> None:
    for state in all_states():
        before = state.model_dump()
        first, second = analyze(state), analyze(state)
        record(result, decision_to_dict(first) == decision_to_dict(second),
               lambda: f"non-deterministic output for {describe(state)}")
        record(result, state.model_dump() == before, lambda: f"input mutated for {describe(state)}")


def mr_jungle_permission_monotone(result: RelationResult) -> None:
    order = (JungleState.CONFIRMED_NEAR, JungleState.UNKNOWN, JungleState.CONFIRMED_FAR)
    for state in all_states():
        if state.jungle.enemy != JungleState.UNKNOWN:
            continue
        permissions = [analyze(with_field(state, "jungle", "enemy", jungle)).permission for jungle in order]
        record(result, permissions == sorted(permissions),
               lambda: f"NEAR/UNKNOWN/FAR permissions {[p.name for p in permissions]} for {describe(state)}")


def mr_jungle_far_never_worse(result: RelationResult) -> None:
    for state in all_states():
        if state.jungle.enemy != JungleState.UNKNOWN:
            continue
        unknown = validity_map(analyze(state))
        far = validity_map(analyze(with_field(state, "jungle", "enemy", JungleState.CONFIRMED_FAR)))
        for action, validity in unknown.items():
            record(result, VALIDITY_RANK[far[action]] <= VALIDITY_RANK[validity],
                   lambda: f"{action.value} {validity.value}->{far[action].value} when jungle confirmed far, {describe(state)}")


def mr_opportunity_removal(result: RelationResult) -> None:
    for state in all_states():
        decision = analyze(state)
        if Opportunity.PUNISH.value not in decision.opportunities:
            continue
        for opponent in OpponentAction:
            if opponent == state.opponent.action:
                continue
            removed = analyze(with_field(state, "opponent", "action", opponent))
            if Opportunity.PUNISH.value in removed.opportunities:
                continue
            record(result, removed.permission <= decision.permission,
                   lambda: f"permission rose {decision.permission.name}->{removed.permission.name} "
                           f"after removing PUNISH (opponent={opponent.value}), {describe(state)}")


def mr_recommendation_sound(result: RelationResult) -> None:
    for state in all_states():
        decision = analyze(state)
        recommended = recommended_actions(decision)
        record(result, len(recommended) == 1, lambda: f"{len(recommended)} recommendations for {describe(state)}")
        validity = validity_map(decision)
        record(result, all(validity[action] == Validity.VALID for action in recommended),
               lambda: f"non-VALID recommendation {recommended} for {describe(state)}")


def mr_wait_always_valid(result: RelationResult) -> None:
    for state in all_states():
        validity = validity_map(analyze(state)).get(ActionType.WAIT)
        record(result, validity == Validity.VALID, lambda: f"WAIT is {validity} for {describe(state)}")


def mr_trace_consistent(result: RelationResult) -> None:
    for state in all_states():
        decision = analyze(state)
        expected = [("OPPORTUNITY", code) for code in decision.opportunities]
        expected.append(("PERMISSION", decision.permission.name))
        actual = [(entry.stage, entry.code) for entry in decision.trace]
        record(result, actual == expected, lambda: f"trace {actual} != {expected} for {describe(state)}")


def mr_unused_fields_invariant(result: RelationResult) -> None:
    unused = (("wave", "state", WaveState), ("power", "access", AccessState), ("risk", "return_path", ReturnPath))
    for state in all_states():
        baseline = decision_to_dict(analyze(state))
        for section, name, enum in unused:
            for value in enum:
                if value == getattr(getattr(state, section), name):
                    continue
                variant = with_field(state, section, name, value)
                record(result, decision_to_dict(analyze(variant)) == baseline,
                       lambda: f"{section}.{name}={value.value} changed decision for {describe(state)}")


RELATIONS: list[tuple[str, str, str, Callable[[RelationResult], None]]] = [
    ("MR-01", "DESIGN", "Determinism and input immutability", mr_determinism),
    ("MR-02", "DESIGN", "Permission monotone in enemy-jungle safety (NEAR <= UNKNOWN <= FAR)", mr_jungle_permission_monotone),
    ("MR-03", "DESIGN", "Confirming enemy jungle FAR never worsens any action's validity vs UNKNOWN", mr_jungle_far_never_worse),
    ("MR-04", "DESIGN", "Removing the PUNISH opportunity never raises permission", mr_opportunity_removal),
    ("MR-05", "DESIGN", "Exactly one recommendation and it is VALID", mr_recommendation_sound),
    ("MR-06", "CURRENT", "WAIT is VALID in every state (guards OI-5)", mr_wait_always_valid),
    ("MR-07", "CURRENT", "Trace = opportunities then permission only (tied to OI-3)", mr_trace_consistent),
    ("MR-08", "CURRENT", "wave / access / return_path do not affect the decision (tied to OI-4)", mr_unused_fields_invariant),
]


def run_all() -> list[RelationResult]:
    results = []
    for relation_id, kind, title, check in RELATIONS:
        result = RelationResult(relation_id, kind, title)
        check(result)
        results.append(result)
    return results
