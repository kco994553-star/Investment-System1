from backend.decision.actions import ActionType
from backend.decision.models import ActionEvaluation, Validity
from backend.decision.opportunity import Opportunity
from backend.decision.permission import PermissionLevel


def find_action(
    evaluations: list[ActionEvaluation],
    action: ActionType,
) -> ActionEvaluation | None:
    return next(
        (evaluation for evaluation in evaluations if evaluation.action == action),
        None,
    )


def select_recommendation(
    opportunities: list[Opportunity],
    permission: PermissionLevel,
    evaluations: list[ActionEvaluation],
) -> None:
    preferred = ActionType.WAIT

    if Opportunity.PUNISH in opportunities:
        preferred = (
            ActionType.SHORT_TRADE
            if permission >= PermissionLevel.P3
            else ActionType.THREAT
        )

    candidate = find_action(evaluations, preferred)

    if candidate is not None and candidate.validity == Validity.VALID:
        candidate.recommended = True
        return

    fallback = find_action(evaluations, ActionType.WAIT)

    if fallback is not None and fallback.validity == Validity.VALID:
        fallback.recommended = True
