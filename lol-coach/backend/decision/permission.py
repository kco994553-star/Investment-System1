from enum import IntEnum

from backend.state.models import GameState, JungleState
from backend.decision.opportunity import Opportunity


class PermissionLevel(IntEnum):
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5


def calculate_permission(
    state: GameState,
    opportunities: list[Opportunity],
) -> PermissionLevel:
    permission = PermissionLevel.P2

    if Opportunity.PUNISH in opportunities:
        permission = PermissionLevel.P4

    if state.jungle.enemy == JungleState.UNKNOWN:
        permission = min(permission, PermissionLevel.P3)
    elif state.jungle.enemy == JungleState.CONFIRMED_NEAR:
        permission = min(permission, PermissionLevel.P2)

    return permission
