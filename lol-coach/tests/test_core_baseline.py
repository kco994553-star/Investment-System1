"""Characterization tests for the imported v0.1 core decision skeleton.

These pin the behaviour of the code exactly as received (R0 import). They do not
assert that the behaviour is correct coaching; see CURRENT_HANDOFF Open Issues.
"""

from backend.decision.actions import ACTION_DEFINITIONS, ActionType
from backend.decision.engine import analyze
from backend.decision.models import Validity
from backend.decision.permission import PermissionLevel
from backend.decision.reason_codes import ReasonCode
from backend.state.models import (
    GameState,
    JungleContext,
    JungleState,
    MatchupState,
    OpponentAction,
    OpponentContext,
    PowerState,
    RiskContext,
    WaveContext,
)


def make_state(
    matchup=MatchupState.UNKNOWN,
    jungle=JungleState.UNKNOWN,
    opponent=OpponentAction.NEUTRAL,
) -> GameState:
    return GameState(
        power=PowerState(matchup=matchup),
        wave=WaveContext(),
        jungle=JungleContext(enemy=jungle),
        opponent=OpponentContext(action=opponent),
        risk=RiskContext(),
    )


def by_action(decision):
    return {evaluation.action: evaluation for evaluation in decision.actions}


def recommended(decision):
    return [evaluation.action for evaluation in decision.actions if evaluation.recommended]


def punish_state(jungle):
    return make_state(MatchupState.FAVORABLE, jungle, OpponentAction.CS_APPROACH)


def test_default_state_recommends_wait_at_p2():
    decision = analyze(make_state())

    assert decision.permission == PermissionLevel.P2
    assert decision.opportunities == []
    assert recommended(decision) == [ActionType.WAIT]


def test_punish_detected_only_for_favorable_matchup_and_cs_approach():
    assert analyze(punish_state(JungleState.CONFIRMED_FAR)).opportunities == ["PUNISH"]
    assert analyze(make_state(MatchupState.EVEN, opponent=OpponentAction.CS_APPROACH)).opportunities == []
    assert analyze(make_state(MatchupState.FAVORABLE, opponent=OpponentAction.RETREAT)).opportunities == []


def test_punish_permission_capped_by_jungle_state():
    assert analyze(punish_state(JungleState.CONFIRMED_FAR)).permission == PermissionLevel.P4
    assert analyze(punish_state(JungleState.UNKNOWN)).permission == PermissionLevel.P3
    assert analyze(punish_state(JungleState.CONFIRMED_NEAR)).permission == PermissionLevel.P2


def test_punish_with_permission_p3_or_higher_recommends_short_trade():
    for jungle in (JungleState.CONFIRMED_FAR, JungleState.UNKNOWN):
        decision = analyze(punish_state(jungle))
        assert recommended(decision) == [ActionType.SHORT_TRADE]
        assert by_action(decision)[ActionType.SHORT_TRADE].validity == Validity.VALID


def test_punish_with_enemy_jungle_near_downgrades_to_threat():
    decision = analyze(punish_state(JungleState.CONFIRMED_NEAR))

    assert recommended(decision) == [ActionType.THREAT]
    assert by_action(decision)[ActionType.SHORT_TRADE].validity == Validity.CONDITIONAL


def test_unknown_jungle_makes_high_commit_low_reversibility_conditional():
    actions = by_action(analyze(punish_state(JungleState.UNKNOWN)))

    for action in (ActionType.EXTENDED_TRADE, ActionType.ALL_IN):
        assert actions[action].validity == Validity.CONDITIONAL
        assert ReasonCode.ENEMY_JUNGLE_UNKNOWN in actions[action].reasons
        assert "ENEMY_JUNGLE_CONFIRMED_FAR" in actions[action].unlock_conditions


def test_chase_invalid_when_enemy_jungle_unknown():
    actions = by_action(analyze(punish_state(JungleState.UNKNOWN)))

    assert actions[ActionType.CHASE].validity == Validity.INVALID
    assert actions[ActionType.CHASE].reasons.count(ReasonCode.ENEMY_JUNGLE_UNKNOWN) == 1


def test_permission_caps_commitment():
    actions = by_action(analyze(punish_state(JungleState.CONFIRMED_FAR)))

    # P4 allows up to HIGH commitment; FULL (ALL_IN) is conditional.
    assert actions[ActionType.EXTENDED_TRADE].validity == Validity.VALID
    assert actions[ActionType.CHASE].validity == Validity.VALID
    assert actions[ActionType.ALL_IN].validity == Validity.CONDITIONAL


def test_exactly_one_recommendation_per_decision():
    for jungle in JungleState:
        for matchup in MatchupState:
            for opponent in OpponentAction:
                decision = analyze(make_state(matchup, jungle, opponent))
                assert len(recommended(decision)) == 1


def test_evaluations_cover_only_defined_actions():
    decision = analyze(make_state())

    assert [evaluation.action for evaluation in decision.actions] == list(ACTION_DEFINITIONS)


def test_trace_records_opportunities_then_permission():
    decision = analyze(punish_state(JungleState.UNKNOWN))

    assert [(entry.stage, entry.code) for entry in decision.trace] == [
        ("OPPORTUNITY", "PUNISH"),
        ("PERMISSION", "P3"),
    ]
