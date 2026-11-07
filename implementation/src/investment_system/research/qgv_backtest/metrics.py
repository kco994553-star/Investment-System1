"""Stdlib-only statistics for the isolated QGV research path.

Returns and weights are decimal fractions (one percentage point = .01).
Callers provide the verified session calendar and monthly boundaries; this
module never invents trading sessions, fills missing NAV, or obtains data.
Partial monthly intervals contribute to CAGR/bootstrap, while risk ratios use
only explicitly complete months. Bootstrap inference is approximate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
import random
from statistics import fmean, stdev
from typing import Mapping, Sequence


@dataclass(frozen=True)
class Metric:
    value: float | None
    reason: str | None = None


@dataclass(frozen=True)
class NavPoint:
    date: date
    nav: float | None


@dataclass(frozen=True)
class MonthlyReturn:
    start: date
    end: date
    value: float | None
    full_month: bool = True


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _nav_complete(points: Sequence[NavPoint], expected_sessions=None) -> bool:
    if any(not isinstance(p.date, date) for p in points):
        raise ValueError('NAV dates must be dates')
    if any(a.date >= b.date for a, b in zip(points, points[1:])):
        raise ValueError('NAV dates must be strictly increasing')
    if any(p.nav is not None and (not _finite(p.nav) or p.nav < 0) for p in points):
        raise ValueError('NAV must be finite and nonnegative, or explicitly missing')
    return (bool(points) and all(p.nav is not None for p in points)
            and (expected_sessions is None or [p.date for p in points] == list(expected_sessions)))


def _monthly_validate(monthly: Sequence[MonthlyReturn]) -> None:
    for item in monthly:
        if not isinstance(item.start, date) or not isinstance(item.end, date) or item.end <= item.start:
            raise ValueError('Monthly intervals need increasing start/end dates')
        if item.value is not None and (not _finite(item.value) or item.value < -1):
            raise ValueError('Monthly returns must be finite and at least -1, or explicitly missing')
    if any(a.end != b.start for a, b in zip(monthly, monthly[1:])):
        raise ValueError('Monthly intervals must be contiguous and ordered')


def _ratio(values: Sequence[float], *, downside: bool = False) -> Metric:
    if len(values) < 2:
        return Metric(None, 'INSUFFICIENT_MONTHS')
    denominator = (math.sqrt(fmean(min(value, 0) ** 2 for value in values))
                   if downside else stdev(values))
    if denominator == 0:
        return Metric(None, 'ZERO_DENOMINATOR')
    return Metric(fmean(values) / denominator * math.sqrt(12))


def monthly_risk_metrics(
    monthly_returns: Sequence[MonthlyReturn], *,
    risk_free_monthly: Sequence[MonthlyReturn] | None = None,
    benchmark_monthly: Sequence[MonthlyReturn] | None = None,
) -> dict:
    """Monthly sample Sharpe/IR and all-month-denominator downside Sortino.

    RF and benchmark must match the ENTIRE supplied interval grid, including
    partial intervals; full-month filtering happens after that paired check.
    """
    monthly = list(monthly_returns)
    _monthly_validate(monthly)
    full = [i for i, item in enumerate(monthly) if item.full_month]
    result = {'full_months': len(full)}
    if any(monthly[i].value is None for i in full):
        reason = 'INCOMPLETE_MONTHLY_RETURNS'
        result.update({key: Metric(None, reason) for key in
                       ('worst_month', 'sharpe', 'sortino', 'information_ratio')})
        return result
    result['worst_month'] = (Metric(min(monthly[i].value for i in full)) if full
                             else Metric(None, 'INSUFFICIENT_MONTHS'))

    def differences(other, label):
        if other is None:
            return None, f'MISSING_{label}'
        other = list(other)
        grid = lambda rows: [(row.start, row.end, row.full_month) for row in rows]
        if grid(monthly) != grid(other):
            return None, f'{label}_ALIGNMENT_MISMATCH'
        _monthly_validate(other)
        if any(other[i].value is None for i in full):
            return None, f'MISSING_{label}'
        return [monthly[i].value - other[i].value for i in full], None

    excess, reason = differences(risk_free_monthly, 'RISK_FREE')
    result['sharpe'] = Metric(None, reason) if reason else _ratio(excess)
    result['sortino'] = Metric(None, reason) if reason else _ratio(excess, downside=True)
    active, reason = differences(benchmark_monthly, 'BENCHMARK')
    result['information_ratio'] = Metric(None, reason) if reason else _ratio(active)
    return result


def performance_metrics(
    nav_points: Sequence[NavPoint], *, monthly_returns: Sequence[MonthlyReturn] | None = None,
    risk_free_monthly: Sequence[MonthlyReturn] | None = None,
    benchmark_monthly: Sequence[MonthlyReturn] | None = None,
    expected_sessions: Sequence[date] | None = None,
    initial_capital: float | None = None, started_at: date | None = None,
) -> dict:
    """Daily NAV metrics, with optional explicit monthly observations.

    Recovery is sessions from the MDD's preceding peak to its first recovery.
    An unrecovered MDD has no recovery duration; elapsed sessions are separate.
    A missing session is detectable only when expected_sessions is supplied.
    For close-only observations, initial_capital anchors first-session entry
    costs and adds its first close return to daily volatility. started_at is
    the actual entry date (defaults to the first NAV date), not an extra session.
    """
    points = list(nav_points)
    if initial_capital is not None and (not _finite(initial_capital) or initial_capital <= 0):
        raise ValueError('Initial capital must be finite and positive')
    if started_at is not None and (not isinstance(started_at, date)
                                   or (points and started_at > points[0].date)):
        raise ValueError('Start date must be no later than the first NAV date')
    complete = _nav_complete(points, expected_sessions)
    result = monthly_risk_metrics(monthly_returns or [], risk_free_monthly=risk_free_monthly,
                                  benchmark_monthly=benchmark_monthly)
    if not complete:
        result.update({key: Metric(None, 'INCOMPLETE_NAV') for key in
                       ('cagr', 'cumulative_return', 'annualized_volatility', 'max_drawdown')})
        result.update(annual_returns={}, worst_year=None, max_drawdown_recovered=None,
                      max_drawdown_recovery_sessions=None, max_drawdown_elapsed_sessions=None)
        return result
    initial = points[0].nav if initial_capital is None else initial_capital
    if initial <= 0:
        raise ValueError('Initial NAV must be positive')
    final = points[-1].nav
    start = points[0].date if started_at is None else started_at
    days = (points[-1].date - start).days
    result['cumulative_return'] = Metric(final / initial - 1)
    result['cagr'] = Metric((final / initial) ** (365.25 / days) - 1) if days else Metric(None, 'ZERO_DURATION')
    daily_nav = ([initial] if initial_capital is not None else []) + [point.nav for point in points]
    if any(value == 0 for value in daily_nav[:-1]):
        result['annualized_volatility'] = Metric(None, 'ZERO_NAV_BASE')
    elif len(daily_nav) < 3:
        result['annualized_volatility'] = Metric(None, 'INSUFFICIENT_DAILY_RETURNS')
    else:
        daily = [b / a - 1 for a, b in zip(daily_nav, daily_nav[1:])]
        result['annualized_volatility'] = Metric(stdev(daily) * math.sqrt(252))

    peak, peak_i, peak_date = initial, 0, start
    worst, worst_peak, trough_i, worst_peak_value, worst_peak_date = 0.0, 0, 0, initial, start
    for i, point in enumerate(points):
        if point.nav >= peak:
            peak, peak_i, peak_date = point.nav, i, point.date
        drawdown = point.nav / peak - 1
        if drawdown < worst:
            worst, worst_peak, trough_i = drawdown, peak_i, i
            worst_peak_value, worst_peak_date = peak, peak_date
    recovery_i = next((i for i in range(trough_i, len(points))
                       if points[i].nav >= worst_peak_value), None)
    result.update(max_drawdown=Metric(worst), max_drawdown_peak_date=worst_peak_date,
                  max_drawdown_trough_date=points[trough_i].date,
                  max_drawdown_recovered=recovery_i is not None,
                  max_drawdown_recovery_date=points[recovery_i].date if recovery_i is not None else None,
                  max_drawdown_recovery_sessions=(recovery_i - worst_peak if recovery_i is not None else None),
                  max_drawdown_elapsed_sessions=(recovery_i if recovery_i is not None else len(points) - 1) - worst_peak)
    annual, base, year = {}, initial, points[0].date.year
    for i, point in enumerate(points):
        if i + 1 == len(points) or points[i + 1].date.year != point.date.year:
            annual[year] = point.nav / base - 1 if base else None
            base = point.nav
            if i + 1 < len(points):
                year = points[i + 1].date.year
    result['annual_returns'] = annual
    valid_years = [year for year, value in annual.items() if value is not None]
    result['worst_year'] = min(valid_years, key=lambda year: annual[year]) if valid_years else None
    return result


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def paired_monthly_bootstrap(
    series: Mapping[str, Sequence[MonthlyReturn]], *, baseline: str = 'W0',
    replications: int = 10000, seed: int = 20261026, block_months: int = 12,
    family_size: int = 3,
) -> dict:
    """Paired circular monthly moving-block CAGR difference percentile bound.

    Each sampled return travels with its actual interval day count. All series
    share each replication's indices. Complete months determine the 60-month
    evidence gate; supplied partial intervals are retained in CAGR resampling.
    Bonferroni's lower tail defaults to .05/3 for the original three contrasts.
    The separate decile/factor registration explicitly supplies family_size=20.
    ``replications``/``block_months`` are exposed for synthetic verification;
    formal research uses their registered defaults and records them in output.
    """
    if baseline not in series:
        raise ValueError('Baseline series is required')
    if isinstance(replications, bool) or not isinstance(replications, int) or replications < 1:
        raise ValueError('replications must be a positive integer')
    if isinstance(block_months, bool) or not isinstance(block_months, int) or block_months < 1:
        raise ValueError('block_months must be a positive integer')
    if type(family_size) is not int or family_size < 1:
        raise ValueError('family_size must be a positive integer')
    rows = {name: list(values) for name, values in series.items()}
    reference = rows[baseline]
    grid = [(row.start, row.end, row.full_month) for row in reference]
    for values in rows.values():
        _monthly_validate(values)
        if [(row.start, row.end, row.full_month) for row in values] != grid:
            raise ValueError('All bootstrap series must share identical interval boundaries')
    full_months = sum(item.full_month for item in reference)
    reason = ('INCOMPLETE_MONTHLY_RETURNS' if any(item.value is None for values in rows.values() for item in values)
              else 'INSUFFICIENT_MONTHS' if full_months < 60 else None)
    days = [(item.end - item.start).days for item in reference]
    logs = {name: [math.log1p(item.value) if item.value is not None and item.value > -1 else -math.inf
                   for item in values] for name, values in rows.items()}

    def cagrs(indices):
        duration = sum(days[i] for i in indices)
        return {name: math.expm1(sum(values[i] for i in indices) * 365.25 / duration)
                for name, values in logs.items()}

    observed = cagrs(range(len(reference))) if reference and reason != 'INCOMPLETE_MONTHLY_RETURNS' else None
    comparisons = {name: {'observed_difference': Metric(observed[name] - observed[baseline]) if observed else Metric(None, reason or 'INSUFFICIENT_MONTHS'),
                          'lower_bound': Metric(None, reason)}
                   for name in rows if name != baseline}
    result = dict(method='PAIRED_CIRCULAR_MOVING_BLOCK', approximate_inference=True,
                  full_months=full_months, observations=len(reference), block_months=block_months,
                  replications=replications, seed=seed, lower_tail_alpha=.05 / family_size,
                  comparisons=comparisons, status=reason or 'OK')
    if reason:
        return result
    rng, count = random.Random(seed), len(reference)
    samples = {name: [] for name in comparisons}
    for _ in range(replications):
        indices = []
        while len(indices) < count:
            start = rng.randrange(count)
            indices.extend((start + offset) % count for offset in range(min(block_months, count - len(indices))))
        values = cagrs(indices)
        for name in samples:
            samples[name].append(values[name] - values[baseline])
    for name in comparisons:
        comparisons[name]['lower_bound'] = Metric(_quantile(samples[name], .05 / family_size))
    return result


def primary_decision(
    observed_difference: float | None, lower_bound: float | None,
    mdd_worsening: float | None, sharpe_deterioration: float | None, *,
    panel: str, n: int, rebalance: str, cost_bps: float,
) -> dict:
    """Candidate labels only for primary COMMON/N15/quarterly/10-bps tests.

    MDD worsening is candidate loss magnitude minus baseline loss magnitude;
    Sharpe deterioration is baseline minus candidate. These are observed risk
    constraints, not a joint statistical guarantee or an adoption instruction.
    """
    result = dict(status='OK', superiority_candidate=False, noninferiority_candidate=False)
    if (panel, n, rebalance, cost_bps) != ('COMMON', 15, 'QUARTERLY', 10):
        result['status'] = 'NOT_PRIMARY_COMPARISON'
        return result
    if any(value is None or not _finite(value) for value in
           (observed_difference, lower_bound, mdd_worsening, sharpe_deterioration)):
        result['status'] = 'INSUFFICIENT_EVIDENCE'
        return result
    result['superiority_candidate'] = observed_difference >= .01 and lower_bound > 0
    result['noninferiority_candidate'] = lower_bound > -.01 and mdd_worsening <= .03 and sharpe_deterioration <= .1
    return result


def exposure_metrics(weights: Mapping[str, float], sectors: Mapping[str, str]) -> dict:
    """Long-only NAV weights; unallocated weight is cash, never redistributed."""
    if any(not _finite(value) or value < 0 for value in weights.values()) or sum(weights.values()) > 1 + 1e-10:
        raise ValueError('Long-only NAV weights must be finite, nonnegative and sum to at most one')
    sector_weights = {}
    for security, value in weights.items():
        sector = sectors.get(security, 'UNKNOWN')
        sector_weights[sector] = sector_weights.get(sector, 0) + value
    return dict(cash_weight=max(0.0, 1 - sum(weights.values())), security_weights=dict(weights),
                sector_weights=sector_weights, security_hhi=sum(value ** 2 for value in weights.values()),
                sector_hhi=sum(value ** 2 for value in sector_weights.values()),
                largest_security_weight=max(weights.values(), default=0),
                largest_sector_weight=max(sector_weights.values(), default=0))


def selection_changes(previous: Sequence[str], current: Sequence[str]) -> dict:
    """Jaccard and old-rank minus new-rank for retained names (positive=up)."""
    if len(set(previous)) != len(previous) or len(set(current)) != len(current):
        raise ValueError('Selection identifiers must be unique')
    old, new = set(previous), set(current)
    before, after = {name: i for i, name in enumerate(previous)}, {name: i for i, name in enumerate(current)}
    return dict(jaccard=len(old & new) / len(old | new) if old | new else 1.0,
                added=sorted(new - old), removed=sorted(old - new),
                rank_changes={name: before[name] - after[name] for name in sorted(old & new)})


def annual_turnover(trades: Sequence[Mapping], nav_points: Sequence[NavPoint]) -> dict[int, Metric]:
    """Two-way executed buy+sell notional / that year's mean daily NAV."""
    points = list(nav_points)
    _nav_complete(points)
    years = sorted({point.date.year for point in points} | {trade['date'].year for trade in trades})
    result = {}
    for year in years:
        values = [point.nav for point in points if point.date.year == year]
        selected = [trade for trade in trades if trade['date'].year == year]
        if any(trade['side'] not in ('BUY', 'SELL') or not _finite(trade['notional']) or trade['notional'] < 0
               for trade in selected):
            raise ValueError('Turnover requires nonnegative executed BUY/SELL notionals')
        if not values or any(value is None for value in values):
            result[year] = Metric(None, 'INCOMPLETE_NAV')
        elif fmean(values) == 0:
            result[year] = Metric(None, 'ZERO_DENOMINATOR')
        else:
            result[year] = Metric(sum(trade['notional'] for trade in selected) / fmean(values))
    return result


def fixed_trade_cost_attribution(trades: Sequence[Mapping], gross_nav: Sequence[NavPoint]) -> dict:
    """Subtract booked costs from a fixed-trade gross path; no sizing replay.

    The supplied gross path must use the SAME fills/quantities as the attributed
    trades. A separately simulated zero-bps path is a different cost experiment
    and must not be passed here as a surrogate fixed-trade gross path.
    """
    points = list(gross_nav)
    if not _nav_complete(points):
        return dict(method='FIXED_TRADE_COST_ATTRIBUTION', status='INCOMPLETE_NAV', total_cost=None,
                    gross_final_nav=None, cost_subtracted_final_nav=None)
    if any(not _finite(trade['cost']) or trade['cost'] < 0 for trade in trades):
        raise ValueError('Booked costs must be finite and nonnegative')
    if any(not points[0].date <= trade['date'] <= points[-1].date for trade in trades):
        raise ValueError('Attributed costs must fall within the gross NAV path')
    cost = sum(trade['cost'] for trade in trades)
    return dict(method='FIXED_TRADE_COST_ATTRIBUTION', status='OK', total_cost=cost,
                gross_final_nav=points[-1].nav, cost_subtracted_final_nav=points[-1].nav - cost)


def return_contributions(
    profit_loss_by_security: Mapping[str, float], initial_nav: float, *,
    cash_income: float = 0, costs: float = 0,
) -> dict:
    """Additive holding-period P&L contributions / starting NAV.

    Security P&L includes marked gains/losses and dividends exactly once. Cash
    income and booked costs are separate; the caller reconciles their sum with
    the ledger's NAV change. These are contributions, not standalone returns.
    """
    if not _finite(initial_nav) or initial_nav <= 0:
        raise ValueError('Initial NAV must be finite and positive')
    if (any(not _finite(value) for value in profit_loss_by_security.values())
            or not _finite(cash_income) or not _finite(costs) or costs < 0):
        raise ValueError('Contributions need finite P&L/income and nonnegative costs')
    return dict(security_contributions={name: value / initial_nav for name, value in profit_loss_by_security.items()},
                cash_contribution=cash_income / initial_nav, cost_contribution=-costs / initial_nav,
                total_return=(sum(profit_loss_by_security.values()) + cash_income - costs) / initial_nav)
