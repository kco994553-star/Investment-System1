from investment_system.dynamic_workflow import (
    Governance,
    Impact,
    RouteRequest,
    Uncertainty,
    WorkflowProfile,
    route,
)


def _route(impact=Impact.LOW, uncertainty=Uncertainty.LOW, governance=Governance()):
    return route(RouteRequest("r1", impact, uncertainty, governance))


def test_low_risk_defaults_fast():
    result = _route()
    assert result.profile is WorkflowProfile.FAST
    assert result.trace()["automatic_downgrade_allowed"] is False


def test_high_impact_routes_deep():
    assert _route(impact=Impact.HIGH).profile is WorkflowProfile.DEEP


def test_high_uncertainty_routes_deep():
    assert _route(uncertainty=Uncertainty.HIGH).profile is WorkflowProfile.DEEP


def test_high_impact_and_uncertainty_routes_critical():
    result = _route(Impact.HIGH, Uncertainty.HIGH)
    assert result.profile is WorkflowProfile.CRITICAL


def test_each_governance_guard_forces_critical():
    guards = (
        Governance(d3_required=True),
        Governance(frozen_affected=True),
        Governance(official_affected=True),
        Governance(pit_policy_affected=True),
        Governance(holdout_affected=True),
    )
    for guard in guards:
        assert _route(governance=guard).profile is WorkflowProfile.CRITICAL


def test_governance_overrides_low_risk_inputs():
    result = _route(governance=Governance(pit_policy_affected=True))
    assert result.profile is WorkflowProfile.CRITICAL
    assert "PIT_POLICY_AFFECTED" in result.reasons


def test_trace_is_deterministic_and_explanatory():
    request = RouteRequest("same", Impact.HIGH, Uncertainty.MEDIUM)
    first = route(request).trace()
    second = route(request).trace()
    assert first == second
    assert first["profile"] == "DEEP"
    assert first["reasons"] == ["HIGH_IMPACT"]
    assert first["escalation_allowed"] is True
