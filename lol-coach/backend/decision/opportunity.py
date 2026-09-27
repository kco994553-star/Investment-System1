from enum import StrEnum

from backend.state.models import GameState, MatchupState, OpponentAction


class Opportunity(StrEnum):
    PUNISH = "PUNISH"


def detect_opportunities(state: GameState) -> list[Opportunity]:
    opportunities: list[Opportunity] = []

    if (
        state.power.matchup == MatchupState.FAVORABLE
        and state.opponent.action == OpponentAction.CS_APPROACH
    ):
        opportunities.append(Opportunity.PUNISH)

    return opportunities
