from backend.state.models import GameState
from backend.decision.models import Decision
from backend.decision.opportunity import detect_opportunities
from backend.decision.permission import calculate_permission
from backend.decision.evaluator import evaluate_actions
from backend.decision.selector import select_recommendation
from backend.decision.trace import build_trace


def analyze(state: GameState) -> Decision:
    opportunities = detect_opportunities(state)
    permission = calculate_permission(state, opportunities)
    evaluations = evaluate_actions(state, permission)

    select_recommendation(
        opportunities,
        permission,
        evaluations,
    )

    trace = build_trace(
        state,
        opportunities,
        permission,
        evaluations,
    )

    return Decision(
        permission=permission,
        opportunities=[opportunity.value for opportunity in opportunities],
        actions=evaluations,
        trace=trace,
    )
