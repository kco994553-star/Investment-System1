from backend.state.models import GameState, JungleState
from backend.decision.actions import (
    ACTION_DEFINITIONS,
    ActionType,
    Commitment,
    Reversibility,
)
from backend.decision.models import ActionEvaluation, Validity
from backend.decision.permission import PermissionLevel
from backend.decision.reason_codes import ReasonCode


VALIDITY_RANK = {
    Validity.VALID: 0,
    Validity.CONDITIONAL: 1,
    Validity.INVALID: 2,
}


def worsen_validity(evaluation: ActionEvaluation, target: Validity) -> None:
    if VALIDITY_RANK[target] > VALIDITY_RANK[evaluation.validity]:
        evaluation.validity = target


def apply_permission_constraint(
    evaluation: ActionEvaluation,
    commitment: Commitment,
    permission: PermissionLevel,
) -> None:
    max_commitment = {
        PermissionLevel.P0: Commitment.NONE,
        PermissionLevel.P1: Commitment.NONE,
        PermissionLevel.P2: Commitment.LOW,
        PermissionLevel.P3: Commitment.SHORT,
        PermissionLevel.P4: Commitment.HIGH,
        PermissionLevel.P5: Commitment.FULL,
    }[permission]

    if commitment > max_commitment:
        worsen_validity(evaluation, Validity.CONDITIONAL)


def apply_jungle_uncertainty(
    state: GameState,
    evaluation: ActionEvaluation,
    commitment: Commitment,
    reversibility: Reversibility,
) -> None:
    if state.jungle.enemy != JungleState.UNKNOWN:
        return

    if commitment >= Commitment.HIGH and reversibility <= Reversibility.LOW:
        worsen_validity(evaluation, Validity.CONDITIONAL)
        if ReasonCode.ENEMY_JUNGLE_UNKNOWN not in evaluation.reasons:
            evaluation.reasons.append(ReasonCode.ENEMY_JUNGLE_UNKNOWN)
        if "ENEMY_JUNGLE_CONFIRMED_FAR" not in evaluation.unlock_conditions:
            evaluation.unlock_conditions.append("ENEMY_JUNGLE_CONFIRMED_FAR")


def apply_chase_constraint(
    state: GameState,
    evaluation: ActionEvaluation,
) -> None:
    if evaluation.action == ActionType.CHASE and state.jungle.enemy == JungleState.UNKNOWN:
        worsen_validity(evaluation, Validity.INVALID)
        if ReasonCode.ENEMY_JUNGLE_UNKNOWN not in evaluation.reasons:
            evaluation.reasons.append(ReasonCode.ENEMY_JUNGLE_UNKNOWN)


def evaluate_actions(
    state: GameState,
    permission: PermissionLevel,
) -> list[ActionEvaluation]:
    evaluations: list[ActionEvaluation] = []

    for action, definition in ACTION_DEFINITIONS.items():
        evaluation = ActionEvaluation(action=action)

        apply_permission_constraint(evaluation, definition.commitment, permission)
        apply_jungle_uncertainty(
            state,
            evaluation,
            definition.commitment,
            definition.reversibility,
        )
        apply_chase_constraint(state, evaluation)
        evaluations.append(evaluation)

    return evaluations
