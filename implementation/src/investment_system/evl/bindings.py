"""Research-only bindings to existing calculations; unbound semantics fail closed.

This adapter never rewrites official factor weights or modifies legacy engines.
Deadband changes order intents only; it is not a return-optimizable parameter in
an engine that evaluates target weights without an execution model.
"""
from dataclasses import replace
from math import isfinite

from ..contracts.models import PortfolioSnapshot
from ..integration.engine import IntegrationEngine
from ..integration.policy import ProvisionalPolicy
from ..macro.engine import MacroEngine
from ..technical.engine import TechnicalEngine

BINDINGS = {
    'cash_buffer': 'TARGET_WEIGHTS_AND_CASH',
    'technical_lookback': 'TECHNICAL_INPUT_WINDOW',
    'execution_deadband_pp': 'ORDER_INTENTS_ONLY',
}
UNRESOLVED = ('risk_multiplier', 'signal_threshold', 'macro_warning_sensitivity')


def validate_parameters(parameters: dict, *, performance_search: bool = False) -> None:
    unknown = set(parameters) - set(BINDINGS)
    if unknown:
        raise ValueError(f'unbound or frozen parameters: {sorted(unknown)}')
    for key, value in parameters.items():
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
            raise ValueError('parameters must be finite numbers')
        if key == 'cash_buffer' and not 0 <= value <= 1:
            raise ValueError('cash_buffer must be in [0,1]')
        if key == 'technical_lookback' and (not isinstance(value, int) or value <= 0):
            raise ValueError('technical_lookback must be a positive integer')
        if key == 'execution_deadband_pp' and value < 0:
            raise ValueError('deadband must be nonnegative')
    if performance_search and 'execution_deadband_pp' in parameters:
        raise ValueError('order-only deadband cannot be optimized against target-weight returns')


def evaluate_bound(as_of, portfolio: PortfolioSnapshot, returns_by_company: dict,
                   indicators: dict, parameters: dict, *, synthetic: bool = False) -> dict:
    validate_parameters(parameters)
    ids = [h.company_id for h in portfolio.holdings]
    if not ids or len(set(ids)) != len(ids) or set(ids) != set(returns_by_company):
        raise ValueError('exact nonempty portfolio/Technical membership required')
    if portfolio.snapshot_at > as_of or (portfolio.synthetic and not synthetic):
        raise ValueError('future/synthetic portfolio cannot support real decision')
    if any(not isfinite(h.target_weight) or h.target_weight < 0 for h in portfolio.holdings):
        raise ValueError('invalid target weights')
    risky = sum(h.target_weight for h in portfolio.holdings)
    if not isfinite(portfolio.cash_weight) or not 0 <= portfolio.cash_weight <= 1 or abs(risky+portfolio.cash_weight-1) > 1e-9:
        raise ValueError('portfolio capital must sum to one')
    cash = parameters.get('cash_buffer', portfolio.cash_weight)
    if risky == 0 and cash < 1:
        raise ValueError('no registered risky allocation to redistribute')
    holdings = tuple(replace(h, target_weight=0 if risky == 0 else h.target_weight/risky*(1-cash))
                     for h in portfolio.holdings)
    bound_portfolio = replace(portfolio, holdings=holdings, cash_weight=cash, weight_sum=1.)
    technical = {}
    for company_id, source_rows in returns_by_company.items():
        lookback = parameters.get('technical_lookback', len(source_rows))
        if len(source_rows) < lookback:
            raise ValueError('insufficient history for registered lookback')
        # Validate chronology before slicing; do not let ordering choose the window.
        times = tuple(row.measured_at for row in source_rows)
        if len(set(times)) != len(times) or times != tuple(sorted(times)):
            raise ValueError('source history must be chronological')
        technical[company_id] = TechnicalEngine().evaluate_stamped(
            company_id, as_of, tuple(source_rows[-lookback:]), synthetic=synthetic)
    macro = MacroEngine().evaluate_stamped(as_of, indicators, synthetic=synthetic)
    policy = ProvisionalPolicy(deadband_pp=parameters.get('execution_deadband_pp', .50))
    result = IntegrationEngine(policy).run(as_of, bound_portfolio, technical, macro)
    return {'integration': result, 'technical': technical, 'macro': macro,
            'cash_weight': 1-sum(result.target_weights.values()),
            'bound_parameters': dict(parameters), 'official': False}
