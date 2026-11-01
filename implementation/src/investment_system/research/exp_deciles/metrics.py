"""Performance metrics for EXP-STOCK-INDICATOR-DECILES-v1 (stdlib only).

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1.

Kept from the source: CAGR on actual days from the first fill, cumulative return, annualized daily volatility
(sample stdev x sqrt 252), MDD with peak / trough / recovery, calendar-year returns, monthly Sharpe / Sortino / IR,
annual two-way turnover, fixed-trade cost attribution. Missing values are None with an UPPER_SNAKE reason, never 0.

Changed: Sharpe and Sortino need a RiskFreeSeries marked verified with a named source (else null with
MISSING_RISK_FREE or RISK_FREE_UNVERIFIED). Added month-end NAV, rolling 12/36/60/120-month windows on month-end NAV
(each window's return list plus worst / best / median), trailing 1/3/5/10-year returns that are null with
INSUFFICIENT_HISTORY when the period is too short, adapters that read run_ledger results, and a before-cost /
after-cost side-by-side report computed from two ledger runs (cost 0 and cost > 0). The #417 bootstrap and primary
decision rules are not ported (they belong to that study).

Daily vs monthly (owner 11/01 decision 7: the price scope is the entry price, holding-period valuation prices, the
next-reselection execution price and corporate actions; daily prices may not be supplied for every period):
- series_metrics / ledger_metrics report `daily_coverage`: DAILY_COVERAGE_COMPLETE only when the NAV has a value on
  every session of the holding period and no session's valuation used a stale mark (for a ledger: no STALE_MARK flag,
  i.e. every held tradable name had that session's price; LOSS / CARRY positions need none). Otherwise
  DAILY_PRICES_NOT_SUPPLIED, and the daily-based metrics (annualized daily volatility, daily MDD with its peak / trough
  / recovery) are null with that reason instead of being presented as computed.
- `performance` (basis DAILY) keeps those daily metrics and the endpoint returns (cumulative return and CAGR need only
  the start anchor and the final NAV); `monthly` (basis MONTHLY) holds the month-end NAV metrics, reported separately:
  worst month, monthly volatility (sample stdev of full-month returns x sqrt 12), month-end MDD, Sharpe / Sortino / IR.
  A month-end NAV that used a stale mark is not a month-end value (MONTH_END_MARK_STALE).
- NAV index starting at 100 (the reported NAV, owner 11/01 supplementary instruction: "USD NAV=100만" meant this index):
  every month-end row and the final value carry nav_index = NAV / initial capital x 100 next to the USD NAV of the internal
  notional account (settings.INTERNAL_NOTIONAL_CAPITAL_USD, an engine setting, not an owner-set capital). Returns do not
  depend on that capital.

Returns and weights are decimal fractions. Callers supply the verified session calendar; this module never invents
sessions, fills missing NAV or obtains data.
"""
from __future__ import annotations

import calendar as civil_calendar
from dataclasses import dataclass
from datetime import date
import math
from statistics import fmean, median, stdev
from typing import Mapping, Sequence

ROLLING_WINDOW_MONTHS = (12, 36, 60, 120)
TRAILING_YEARS = (1, 3, 5, 10)
INSUFFICIENT_HISTORY = 'INSUFFICIENT_HISTORY'
DAILY_COVERAGE_COMPLETE = 'DAILY_COVERAGE_COMPLETE'
DAILY_PRICES_NOT_SUPPLIED = 'DAILY_PRICES_NOT_SUPPLIED'
MONTH_END_MARK_STALE = 'MONTH_END_MARK_STALE'
BASIS_DAILY = 'DAILY'
BASIS_MONTHLY = 'MONTHLY'
NAV_INDEX_BASE = 100.0
NAV_INDEX_LABEL = ('REPORTED_NAV_INDEX_BASE_100: nav_index = NAV / initial capital x 100 is the reported NAV; '
                   'the USD NAV is the internal notional account (engine setting, not an owner-set capital)')
DAILY_METRIC_KEYS = ('annualized_volatility', 'max_drawdown')
DAILY_DETAIL_KEYS = ('max_drawdown_peak_date', 'max_drawdown_trough_date', 'max_drawdown_recovered',
                     'max_drawdown_recovery_date', 'max_drawdown_recovery_sessions', 'max_drawdown_elapsed_sessions')
MONTHLY_METRIC_KEYS = ('full_months', 'worst_month', 'sharpe', 'sortino', 'information_ratio')


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


@dataclass(frozen=True)
class RiskFreeSeries:
    """Monthly risk-free returns on the same interval grid as the strategy, with a named, verified source."""
    source: str
    verified: bool
    monthly: tuple[MonthlyReturn, ...]


@dataclass(frozen=True)
class MonthEndNav:
    month: str  # YYYY-MM
    date: date | None  # Last calendar session of the month, when the calendar covers the month end.
    nav: float | None
    complete: bool
    reason: str | None = None
    nav_index: float | None = None  # Reported NAV: NAV / initial capital x 100 (NAV_INDEX_LABEL).


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_points(points: Sequence[NavPoint]) -> None:
    if any(not isinstance(p.date, date) for p in points):
        raise ValueError('NAV dates must be dates')
    if any(a.date >= b.date for a, b in zip(points, points[1:])):
        raise ValueError('NAV dates must be strictly increasing')
    if any(p.nav is not None and (not _finite(p.nav) or p.nav < 0) for p in points):
        raise ValueError('NAV must be finite and nonnegative, or explicitly missing')


def _nav_complete(points: Sequence[NavPoint], expected_sessions=None) -> bool:
    _validate_points(points)
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


def monthly_risk_metrics(monthly_returns: Sequence[MonthlyReturn], *, risk_free: RiskFreeSeries | None = None,
                         benchmark_monthly: Sequence[MonthlyReturn] | None = None) -> dict:
    """Monthly sample Sharpe/IR and all-month-denominator downside Sortino over full months only.

    RF and benchmark must match the ENTIRE supplied interval grid, including partial intervals; full-month
    filtering happens after that paired check.
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
        grid = lambda rows: [(row.start, row.end, row.full_month) for row in rows]  # noqa: E731
        if grid(monthly) != grid(other):
            return None, f'{label}_ALIGNMENT_MISMATCH'
        _monthly_validate(other)
        if any(other[i].value is None for i in full):
            return None, f'MISSING_{label}'
        return [monthly[i].value - other[i].value for i in full], None

    if risk_free is None:
        excess, reason = None, 'MISSING_RISK_FREE'
    elif (not isinstance(risk_free, RiskFreeSeries) or risk_free.verified is not True
          or not isinstance(risk_free.source, str) or not risk_free.source.strip()):
        excess, reason = None, 'RISK_FREE_UNVERIFIED'
    else:
        excess, reason = differences(risk_free.monthly, 'RISK_FREE')
    result['sharpe'] = Metric(None, reason) if reason else _ratio(excess)
    result['sortino'] = Metric(None, reason) if reason else _ratio(excess, downside=True)
    active, reason = differences(benchmark_monthly, 'BENCHMARK')
    result['information_ratio'] = Metric(None, reason) if reason else _ratio(active)
    return result


def performance_metrics(nav_points: Sequence[NavPoint], *, monthly_returns: Sequence[MonthlyReturn] | None = None,
                        risk_free: RiskFreeSeries | None = None,
                        benchmark_monthly: Sequence[MonthlyReturn] | None = None,
                        expected_sessions: Sequence[date] | None = None,
                        initial_capital: float | None = None, started_at: date | None = None) -> dict:
    """Daily NAV metrics, with optional explicit monthly observations.

    initial_capital anchors the pre-trade capital at started_at (the actual first fill date), so the first
    session's entry costs and open-to-close move count. Recovery is sessions from the MDD's preceding peak to its
    first recovery; an unrecovered MDD has no recovery duration. A missing session is detectable only when
    expected_sessions is supplied.
    """
    points = list(nav_points)
    if initial_capital is not None and (not _finite(initial_capital) or initial_capital <= 0):
        raise ValueError('Initial capital must be finite and positive')
    if started_at is not None and (not isinstance(started_at, date)
                                   or (points and started_at > points[0].date)):
        raise ValueError('Start date must be no later than the first NAV date')
    complete = _nav_complete(points, expected_sessions)
    result = monthly_risk_metrics(monthly_returns or [], risk_free=risk_free, benchmark_monthly=benchmark_monthly)
    if not complete:
        result.update({key: Metric(None, 'INCOMPLETE_NAV') for key in
                       ('cagr', 'cumulative_return', 'annualized_volatility', 'max_drawdown')})
        result.update(annual_returns={}, worst_year=None, max_drawdown_peak_date=None,
                      max_drawdown_trough_date=None, max_drawdown_recovered=None, max_drawdown_recovery_date=None,
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
                       if points[i].nav >= worst_peak_value), None) if worst < 0 else None
    result.update(max_drawdown=Metric(worst), max_drawdown_peak_date=worst_peak_date if worst < 0 else None,
                  max_drawdown_trough_date=points[trough_i].date if worst < 0 else None,
                  max_drawdown_recovered=(recovery_i is not None) if worst < 0 else None,
                  max_drawdown_recovery_date=points[recovery_i].date if recovery_i is not None else None,
                  max_drawdown_recovery_sessions=(recovery_i - worst_peak if recovery_i is not None else None),
                  max_drawdown_elapsed_sessions=((recovery_i if recovery_i is not None else len(points) - 1)
                                                 - worst_peak) if worst < 0 else None)
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


def annual_turnover(trades: Sequence[Mapping], nav_points: Sequence[NavPoint]) -> dict[int, Metric]:
    """Two-way executed buy+sell notional / that year's mean daily NAV."""
    points = list(nav_points)
    _validate_points(points)
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
    """Subtract booked costs from a fixed-trade gross path (same fills, fees added back as cash).

    A separately simulated zero-cost run is a different cost experiment; it is reported by cost_comparison.
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


# -- month-end NAV, rolling windows, trailing returns -----------------------------------------------------------
def nav_index(nav, initial_capital):
    """The reported NAV index (base 100) of a NAV (None when either is missing)."""
    if nav is None or initial_capital is None or not _finite(initial_capital) or initial_capital <= 0:
        return None
    return float(nav) / float(initial_capital) * NAV_INDEX_BASE


def month_end_nav(nav_points: Sequence[NavPoint], *, sessions: Sequence[date],
                  coverage_end: date | None = None, initial_capital: float | None = None,
                  stale_dates=()) -> list[MonthEndNav]:
    """NAV at the last calendar session of each month from the first to the last NAV month.

    A month end counts only when the verified calendar covers the civil month end (coverage_end, default the last
    supplied session) and the NAV series has a value on that month's last session that did not use a stale mark
    (stale_dates: MONTH_END_MARK_STALE). Never guesses by weekdays. With initial_capital every complete row also carries
    the base-100 nav_index.
    """
    stale_dates = frozenset(stale_dates or ())
    points = list(nav_points)
    _validate_points(points)
    if not points:
        return []
    days = sorted(set(sessions))
    if any(not isinstance(day, date) for day in days):
        raise ValueError('Sessions must be dates')
    if not days:
        raise ValueError('Month-end NAV needs the verified session calendar')
    coverage = days[-1] if coverage_end is None else coverage_end
    last_session = {}
    for day in days:
        last_session[(day.year, day.month)] = day
    values = {point.date: point.nav for point in points}
    first, last = points[0].date, points[-1].date
    year, month = first.year, first.month
    result = []
    while (year, month) <= (last.year, last.month):
        label = f'{year:04d}-{month:02d}'
        civil_end = date(year, month, civil_calendar.monthrange(year, month)[1])
        session = last_session.get((year, month))
        if coverage < civil_end or session is None:
            result.append(MonthEndNav(label, None, None, False, 'PARTIAL_MONTH'))
        elif session > last:
            result.append(MonthEndNav(label, session, None, False, 'PARTIAL_MONTH'))
        elif session not in values:
            result.append(MonthEndNav(label, session, None, False, 'MISSING_MONTH_END_NAV'))
        elif values[session] is None:
            result.append(MonthEndNav(label, session, None, False, 'INCOMPLETE_NAV'))
        elif session in stale_dates:
            result.append(MonthEndNav(label, session, None, False, MONTH_END_MARK_STALE))
        else:
            result.append(MonthEndNav(label, session, values[session], True, None,
                                      nav_index(values[session], initial_capital)))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def _core_months(month_ends: Sequence[MonthEndNav]) -> list[MonthEndNav]:
    """Drop leading/trailing partial months; interior gaps stay and make the windows that span them null."""
    rows = list(month_ends)
    while rows and rows[0].reason == 'PARTIAL_MONTH':
        rows.pop(0)
    while rows and rows[-1].reason == 'PARTIAL_MONTH':
        rows.pop()
    return rows


def monthly_returns(nav_points: Sequence[NavPoint], month_ends: Sequence[MonthEndNav], *,
                    started_at: date | None = None, initial_capital: float | None = None) -> list[MonthlyReturn]:
    """Interval returns between month ends, from the start anchor to the last NAV point.

    The first interval (start anchor to the first month end) and the last (last month end to a non-month-end final
    point) are partial (full_month=False). A month end without NAV gives None for both full months touching it, so
    the monthly risk metrics report INCOMPLETE_MONTHLY_RETURNS instead of skipping the gap.
    """
    points = list(nav_points)
    _validate_points(points)
    if not points:
        return []
    start = points[0].date if started_at is None else started_at
    start_value = points[0].nav if initial_capital is None else float(initial_capital)
    boundaries = [(start, start_value, False)]
    for row in _core_months(month_ends):
        if row.date is not None and start < row.date <= points[-1].date:
            boundaries.append((row.date, row.nav, True))
    if boundaries[-1][0] != points[-1].date:
        boundaries.append((points[-1].date, points[-1].nav, False))
    result = []
    for (a, av, a_end), (b, bv, b_end) in zip(boundaries, boundaries[1:]):
        value = bv / av - 1 if av and bv is not None else None
        result.append(MonthlyReturn(a, b, value, full_month=a_end and b_end))
    return result


def rolling_window_returns(month_ends: Sequence[MonthEndNav],
                           windows: Sequence[int] = ROLLING_WINDOW_MONTHS) -> dict[int, dict]:
    """Every w-month window of month-end NAV: cumulative and annualized return, plus worst / best / median."""
    rows = _core_months(month_ends)
    result = {}
    for window in windows:
        if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
            raise ValueError('Rolling windows are positive month counts')
        items = []
        for i in range(len(rows) - window):
            a, b = rows[i], rows[i + window]
            if not (a.complete and b.complete):
                value, annualized = Metric(None, 'INCOMPLETE_MONTH_END_NAV'), Metric(None, 'INCOMPLETE_MONTH_END_NAV')
            elif a.nav == 0:
                value, annualized = Metric(None, 'ZERO_NAV_BASE'), Metric(None, 'ZERO_NAV_BASE')
            else:
                total = b.nav / a.nav - 1
                value, annualized = Metric(total), Metric((1 + total) ** (12 / window) - 1)
            items.append(dict(start_month=a.month, end_month=b.month, start=a.date, end=b.date,
                              total_return=value, annualized_return=annualized))
        values = [item['total_return'].value for item in items if item['total_return'].value is not None]
        if not items:
            summary = {key: Metric(None, INSUFFICIENT_HISTORY) for key in ('worst', 'best', 'median')}
        elif not values:
            summary = {key: Metric(None, 'INCOMPLETE_MONTH_END_NAV') for key in ('worst', 'best', 'median')}
        else:
            summary = dict(worst=Metric(min(values)), best=Metric(max(values)), median=Metric(median(values)))
        result[window] = dict(months=window, windows=items, count=len(items),
                              incomplete_windows=len(items) - len(values), **summary)
    return result


def _years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 February -> 28 February.
        return day.replace(year=day.year - years, day=28)


def trailing_returns(nav_points: Sequence[NavPoint], *, years: Sequence[int] = TRAILING_YEARS,
                     started_at: date | None = None, initial_capital: float | None = None) -> dict[str, dict]:
    """Trailing N-year returns as of the last NAV date; null with INSUFFICIENT_HISTORY when too short.

    The base is the NAV on the last date on or before (as_of - N years); before the first NAV point it is the
    initial capital at started_at. A base date earlier than started_at (default: the first NAV date) is too short.
    """
    points = list(nav_points)
    _validate_points(points)
    result = {}
    if not points:
        for n in years:
            result[f'{n}y'] = dict(years=n, start=None, end=None, total_return=Metric(None, INSUFFICIENT_HISTORY),
                                   annualized_return=Metric(None, INSUFFICIENT_HISTORY))
        return result
    as_of, end_value = points[-1].date, points[-1].nav
    inception = points[0].date if started_at is None else started_at
    for n in years:
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError('Trailing periods are positive year counts')
        base_date = _years_before(as_of, n)
        item = dict(years=n, start=None, end=as_of)
        if base_date < inception:
            reason = INSUFFICIENT_HISTORY
        else:
            earlier = [point for point in points if point.date <= base_date]
            if earlier:
                item['start'], base = earlier[-1].date, earlier[-1].nav
            elif initial_capital is not None:
                item['start'], base = inception, float(initial_capital)
            else:
                base = None
            reason = (INSUFFICIENT_HISTORY if item['start'] is None
                      else 'INCOMPLETE_NAV' if base is None or end_value is None
                      else 'ZERO_NAV_BASE' if base == 0 else None)
        if reason:
            item.update(total_return=Metric(None, reason), annualized_return=Metric(None, reason))
        else:
            total = end_value / base - 1
            item.update(total_return=Metric(total), annualized_return=Metric((1 + total) ** (1 / n) - 1))
        result[f'{n}y'] = item
    return result


def daily_coverage(nav_points: Sequence[NavPoint], expected_sessions: Sequence[date], stale_dates=()) -> dict:
    """DAILY_COVERAGE_COMPLETE when every expected session has a NAV that used no stale mark, else
    DAILY_PRICES_NOT_SUPPLIED with the session counts and the first uncovered session."""
    values = {point.date: point.nav for point in nav_points}
    stale = frozenset(stale_dates or ())
    uncovered = [day for day in expected_sessions if values.get(day) is None or day in stale]
    return dict(status=DAILY_PRICES_NOT_SUPPLIED if uncovered or not expected_sessions else DAILY_COVERAGE_COMPLETE,
                sessions=len(expected_sessions), uncovered_sessions=len(uncovered),
                first_uncovered=uncovered[0] if uncovered else None)


def monthly_metrics(month_ends: Sequence[MonthEndNav], monthly: Sequence[MonthlyReturn], *, started_at: date,
                    initial_capital: float, final: NavPoint | None, risk_free: RiskFreeSeries | None = None,
                    benchmark_monthly: Sequence[MonthlyReturn] | None = None) -> dict:
    """Month-end NAV metrics (basis MONTHLY): worst month, Sharpe / Sortino / IR, monthly volatility and month-end MDD."""
    risk = monthly_risk_metrics(monthly, risk_free=risk_free, benchmark_monthly=benchmark_monthly)
    out = {'basis': BASIS_MONTHLY, **{key: risk[key] for key in MONTHLY_METRIC_KEYS}}
    full = [item.value for item in monthly if item.full_month]
    if any(value is None for value in full):
        out['annualized_volatility'] = Metric(None, 'INCOMPLETE_MONTHLY_RETURNS')
    elif len(full) < 2:
        out['annualized_volatility'] = Metric(None, 'INSUFFICIENT_MONTHS')
    else:
        out['annualized_volatility'] = Metric(stdev(full) * math.sqrt(12))
    rows = [row for row in _core_months(month_ends) if row.date is not None and started_at < row.date
            and (final is None or row.date <= final.date)]
    path = [float(initial_capital)] + [row.nav for row in rows]
    if final is not None and (not rows or rows[-1].date != final.date):
        path.append(final.nav)
    if any(value is None for value in path):
        out['max_drawdown'] = Metric(None, 'INCOMPLETE_MONTH_END_NAV')
    elif len(path) < 2:
        out['max_drawdown'] = Metric(None, 'INSUFFICIENT_MONTHS')
    else:
        peak, worst = path[0], 0.0
        for value in path:
            peak = max(peak, value)
            worst = min(worst, value / peak - 1 if peak else 0.0)
        out['max_drawdown'] = Metric(worst)
    return out


def series_metrics(nav_points: Sequence[NavPoint], *, started_at: date, initial_capital: float,
                   sessions: Sequence[date] | None = None, coverage_end: date | None = None,
                   risk_free: RiskFreeSeries | None = None,
                   benchmark_monthly: Sequence[MonthlyReturn] | None = None, stale_dates=(),
                   final_valuation: str | None = None) -> dict:
    """Performance (DAILY), daily coverage, monthly metrics (MONTHLY), month-end NAV with the base-100 index, monthly
    returns, rolling windows, trailing returns and the final value for one NAV path (module doc).

    stale_dates: sessions whose NAV used a stale mark; final_valuation: CLOSE / OPEN / PREVIOUS_CLOSE of the last point."""
    points = list(nav_points)
    calendar = sorted(sessions) if sessions is not None else [point.date for point in points]
    expected = [day for day in calendar if points and points[0].date <= day <= points[-1].date]
    month_ends = (month_end_nav(points, sessions=calendar, coverage_end=coverage_end, initial_capital=initial_capital,
                                stale_dates=stale_dates) if points else [])
    monthly = monthly_returns(points, month_ends, started_at=started_at, initial_capital=initial_capital)
    perf = performance_metrics(points, monthly_returns=monthly, risk_free=risk_free,
                               benchmark_monthly=benchmark_monthly, expected_sessions=expected,
                               initial_capital=initial_capital, started_at=started_at)
    coverage = daily_coverage(points, expected, stale_dates)
    final = points[-1] if points else None
    if perf['cumulative_return'].value is None and final is not None and final.nav is not None and initial_capital:
        # Endpoint returns need only the start anchor and the final NAV, not every session.
        days = (final.date - started_at).days
        perf['cumulative_return'] = Metric(final.nav / initial_capital - 1)
        perf['cagr'] = (Metric((final.nav / initial_capital) ** (365.25 / days) - 1) if days
                        else Metric(None, 'ZERO_DURATION'))
    if coverage['status'] != DAILY_COVERAGE_COMPLETE:
        perf.update({key: Metric(None, DAILY_PRICES_NOT_SUPPLIED) for key in DAILY_METRIC_KEYS})
        perf.update(dict.fromkeys(DAILY_DETAIL_KEYS))
    performance = {'basis': BASIS_DAILY, **{key: value for key, value in perf.items()
                                            if key not in MONTHLY_METRIC_KEYS}}
    return dict(performance=performance, daily_coverage=coverage,
                monthly=monthly_metrics(month_ends, monthly, started_at=started_at, initial_capital=initial_capital,
                                        final=final, risk_free=risk_free, benchmark_monthly=benchmark_monthly),
                month_end_nav=month_ends, monthly_returns=monthly,
                rolling_windows=rolling_window_returns(month_ends),
                trailing_returns=trailing_returns(points, started_at=started_at, initial_capital=initial_capital),
                final=final_value(final, initial_capital, final_valuation), nav_index_label=NAV_INDEX_LABEL)


def final_value(point: NavPoint | None, initial_capital, valuation=None) -> dict:
    """{'date', 'valuation', 'nav_usd', 'nav_index'} of the last NAV point (nav_index: base-100 display only)."""
    return dict(date=None if point is None else point.date, valuation=valuation,
                nav_usd=None if point is None else point.nav,
                nav_index=None if point is None else nav_index(point.nav, initial_capital))


# -- ledger adapters --------------------------------------------------------------------------------------------
def ledger_nav_points(result: Mapping) -> tuple[list[NavPoint], date | None, float]:
    """NAV points from the first fill date on, that date, and the initial capital (floats for statistics)."""
    started = result['first_fill_date']
    points = [NavPoint(row['date'], None if row['nav'] is None else float(row['nav']))
              for row in result['daily'] if started is not None and row['date'] >= started]
    return points, started, float(result['initial_capital'])


def ledger_trades(result: Mapping) -> list[dict]:
    return [dict(date=fill.session, security_id=fill.security_id, side='BUY' if fill.quantity > 0 else 'SELL',
                 notional=float(fill.gross), cost=float(fill.fee)) for fill in result['fills']]


def ledger_stale_dates(result: Mapping) -> set:
    """Sessions whose ledger valuation used a stale mark for a held tradable name (STALE_MARK flag)."""
    return {row['date'] for row in result['daily'] if any(flag.startswith('STALE_MARK:') for flag in row['flags'])}


def ledger_metrics(result: Mapping, *, sessions: Sequence[date] | None = None, coverage_end: date | None = None,
                   risk_free: RiskFreeSeries | None = None,
                   benchmark_monthly: Sequence[MonthlyReturn] | None = None) -> dict:
    """All metrics for one run_ledger result, measured from the actual first fill (CAGR from first fill); daily
    coverage from the run's STALE_MARK flags (module doc)."""
    points, started, initial = ledger_nav_points(result)
    header = dict(scenario=result['scenario'], cost_bps=float(result['cost_bps']), initial_capital=initial,
                  currency=result['currency'], started_at=started, end=result['end'],
                  end_valuation=result.get('end_valuation'))
    last = result['daily'][-1] if result['daily'] else None
    final = None if last is None else NavPoint(last['date'], None if last['nav'] is None else float(last['nav']))
    if started is None:
        null = Metric(None, 'NO_FILL')
        return dict(header, status='NO_FILL',
                    performance={'basis': BASIS_DAILY, **{key: null for key in
                                                          ('cagr', 'cumulative_return', 'annualized_volatility',
                                                           'max_drawdown')}},
                    daily_coverage=dict(status='NO_FILL', sessions=0, uncovered_sessions=0, first_uncovered=None),
                    monthly={'basis': BASIS_MONTHLY, **{key: null for key in ('worst_month', 'sharpe', 'sortino',
                                                                             'annualized_volatility',
                                                                             'max_drawdown')}},
                    month_end_nav=[], monthly_returns=[], rolling_windows=rolling_window_returns([]),
                    trailing_returns=trailing_returns([]), turnover={}, cost_attribution=None,
                    final=final_value(final, initial, None if last is None else last.get('valuation')),
                    nav_index_label=NAV_INDEX_LABEL)
    if sessions is None:
        sessions = [row['date'] for row in result['daily']]
    metrics = series_metrics(points, started_at=started, initial_capital=initial, sessions=sessions,
                             coverage_end=coverage_end, risk_free=risk_free, benchmark_monthly=benchmark_monthly,
                             stale_dates={day for day in ledger_stale_dates(result) if day >= started},
                             final_valuation=last.get('valuation'))
    trades = [trade for trade in ledger_trades(result) if trade['date'] >= started]
    cumulative, gross_path = 0.0, []
    fees_by_day = {}
    for trade in trades:
        fees_by_day[trade['date']] = fees_by_day.get(trade['date'], 0.0) + trade['cost']
    for point in points:
        cumulative += fees_by_day.get(point.date, 0.0)
        gross_path.append(NavPoint(point.date, None if point.nav is None else point.nav + cumulative))
    by_year = {}
    for trade in trades:
        by_year[trade['date'].year] = by_year.get(trade['date'].year, 0.0) + trade['cost']
    total_cost = sum(trade['cost'] for trade in trades)
    cost = dict(fixed_trade_cost_attribution(trades, gross_path), cost_by_year=by_year,
                total_cost_to_initial_capital=total_cost / initial,
                gross_traded=sum(trade['notional'] for trade in trades))
    return dict(header, status='COMPLETE' if result['status'] == 'COMPLETE' else 'INCOMPLETE_NAV', **metrics,
                turnover=annual_turnover(trades, points), cost_attribution=cost)


def _selections(result):
    return [(row['signal_date'], row['execution_date'], tuple(row['selected'])) for row in result['rebalances']]


def cost_comparison(before_cost: Mapping, after_cost: Mapping, **kwargs) -> dict:
    """Before-cost (cost 0) and after-cost (cost > 0) runs side by side, from the same selections and inputs.

    These are two ledger replays: fills differ because fees change cash, which is the experiment's
    before/after-cost report. kwargs go to ledger_metrics (sessions, coverage_end, risk_free, benchmark_monthly).
    """
    if float(before_cost['cost_bps']) != 0:
        raise ValueError('BEFORE_COST_RUN_MUST_HAVE_ZERO_COST')
    if float(after_cost['cost_bps']) <= 0:
        raise ValueError('AFTER_COST_RUN_MUST_HAVE_POSITIVE_COST')
    for key in ('scenario', 'initial_capital', 'currency', 'start', 'end'):
        if before_cost[key] != after_cost[key]:
            raise ValueError(f'COST_RUNS_DIFFER_IN_{key.upper()}')
    if _selections(before_cost) != _selections(after_cost):
        raise ValueError('COST_RUNS_DIFFER_IN_SELECTIONS')
    before, after = ledger_metrics(before_cost, **kwargs), ledger_metrics(after_cost, **kwargs)
    difference = {}
    for key in ('cagr', 'cumulative_return', 'annualized_volatility', 'max_drawdown'):
        a, b = after['performance'][key], before['performance'][key]
        difference[key] = (Metric(a.value - b.value) if a.value is not None and b.value is not None
                           else Metric(None, a.reason or b.reason))
    final = [row for row in (before_cost['daily'][-1], after_cost['daily'][-1])]
    difference['final_nav'] = (Metric(float(final[1]['nav']) - float(final[0]['nav']))
                               if final[0]['nav'] is not None and final[1]['nav'] is not None
                               else Metric(None, 'INCOMPLETE_NAV'))
    return dict(scenario=before_cost['scenario'], before_cost_bps=0.0, after_cost_bps=float(after_cost['cost_bps']),
                before_cost=before, after_cost=after, after_minus_before=difference,
                after_cost_total_fees=float(after_cost['total_costs']))
