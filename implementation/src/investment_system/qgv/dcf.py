"""Configured FCFE-per-share DCF/reverse DCF; pure RAM-only research.

No price echo, persistence, fetch, V-score mapper or model adoption. Financial
parameters remain unavailable until the caller supplies confirmed settings.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class DcfResult:
    state: str
    reason_codes: tuple[str, ...] = ()
    value_per_share: float | None = field(default=None, repr=False)
    discounted_cashflows: tuple[float, ...] | None = field(default=None, repr=False)
    implied_growth: float | None = field(default=None, repr=False)
    role: str = field(default='RAM_ONLY_RESEARCH', init=False)
    model_status: str = field(default='NOT_APPLIED', init=False)


def _na(reason):
    return DcfResult('NOT_AVAILABLE', (reason,))


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


_NO_PRICE = object()


def _parameters(parameters, cashflow_currency, price_currency=_NO_PRICE):
    if not isinstance(parameters, Mapping):
        return 'PARAMETER_INVALID'
    if parameters.get('confirmed') is not True:
        return 'PARAMETER_APPROVAL_PENDING'
    years = parameters.get('explicit_years')
    r, terminal = parameters.get('discount_rate'), parameters.get('terminal_growth')
    # Engineering loop bound, not an adopted valuation horizon/default.
    if type(years) is not int or not 1 <= years <= 100 or not _finite(r) or not _finite(terminal) or r <= -1 or terminal <= -1:
        return 'PARAMETER_INVALID'
    if r <= terminal:
        return 'GORDON_RATE_ORDER'
    if parameters.get('cashflow_basis') != 'FCFE_PER_SHARE' or parameters.get('discount_rate_basis') != 'COST_OF_EQUITY':
        return 'CASHFLOW_BASIS_UNCONFIRMED'
    if parameters.get('per_share_basis_confirmed') is not True:
        return 'SHARE_BASIS_UNCONFIRMED'
    currency = parameters.get('currency')
    if currency not in ('USD', 'KRW', 'JPY') or cashflow_currency != currency or price_currency is not _NO_PRICE and price_currency != currency:
        return 'CURRENCY_BASIS_UNCONFIRMED'
    return None


def _compute(cashflow, growth, parameters):
    years, r, terminal = parameters['explicit_years'], parameters['discount_rate'], parameters['terminal_growth']
    flows = tuple(cashflow * (1 + growth)**t / (1 + r)**t for t in range(1, years + 1))
    terminal_pv = cashflow * (1 + growth)**years * (1 + terminal) / (r - terminal) / (1 + r)**years
    value = math.fsum((*flows, terminal_pv))
    if not all(math.isfinite(x) for x in (*flows, terminal_pv, value)):
        raise ArithmeticError
    return value, flows


def two_stage_dcf(*, cashflow_per_share, growth_rate, parameters, cashflow_currency):
    reason = _parameters(parameters, cashflow_currency)
    if reason:
        return _na(reason)
    if not _finite(cashflow_per_share) or not _finite(growth_rate) or growth_rate <= -1:
        return _na('INPUT_INVALID')
    try:
        value, flows = _compute(cashflow_per_share, growth_rate, parameters)
    except (ArithmeticError, ValueError):
        return _na('NUMERIC_OVERFLOW')
    return DcfResult('PROVISIONAL', value_per_share=value, discounted_cashflows=flows)


def reverse_dcf(*, cashflow_per_share, price, parameters, cashflow_currency, price_currency):
    reason = _parameters(parameters, cashflow_currency, price_currency)
    if reason:
        return _na(reason)
    if not _finite(cashflow_per_share) or not _finite(price) or price <= 0:
        return _na('INPUT_INVALID')
    if cashflow_per_share <= 0:
        return _na('NON_POSITIVE_CASHFLOW')
    solver = parameters.get('solver')
    if not isinstance(solver, Mapping):
        return _na('SOLVER_INVALID')
    lower, upper = solver.get('growth_lower'), solver.get('growth_upper')
    tol, limit = solver.get('relative_price_tolerance'), solver.get('maximum_iterations')
    if not _finite(lower) or not _finite(upper) or not -1 < lower < upper or not _finite(tol) or not 0 < tol < 1 or type(limit) is not int or not 1 <= limit <= 10000:
        return _na('SOLVER_INVALID')
    try:
        low_value = _compute(cashflow_per_share, lower, parameters)[0]
        high_value = _compute(cashflow_per_share, upper, parameters)[0]
        for endpoint, value in ((lower, low_value), (upper, high_value)):
            if abs(value / price - 1) <= tol:
                return DcfResult('PROVISIONAL', implied_growth=endpoint)
        if not low_value < price < high_value:
            return _na('ROOT_NOT_BRACKETED')
        for _ in range(limit):
            midpoint = lower / 2 + upper / 2
            value = _compute(cashflow_per_share, midpoint, parameters)[0]
            if abs(value / price - 1) <= tol:
                return DcfResult('PROVISIONAL', implied_growth=midpoint)
            if value < price:
                lower = midpoint
            else:
                upper = midpoint
    except (ArithmeticError, ValueError):
        return _na('NUMERIC_OVERFLOW')
    return _na('ROOT_NOT_CONVERGED')
