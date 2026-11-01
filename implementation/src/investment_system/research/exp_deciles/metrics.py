"""Performance metrics for EXP-STOCK-INDICATOR-DECILES-v1 (stdlib only).

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1.

Kept from the source: CAGR on actual days from the start anchor, cumulative return, annualized daily volatility
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
  depend on that capital. Ledger metric headers name it internal_notional_capital_usd with reported_nav INDEX_BASE_100.

Review fixes (11/01 engine review):
- Start anchor (missed M1): a ledger run is measured from the T of its first rebalance with a non-empty selection that
  the run reached, at the internal notional capital, not from its first fill. A year whose picks all went unfilled is
  held as cash (0% before costs) and stays in every metric; only a run that reached no selected rebalance is
  NOT_STARTED (every metric null).
- Terminal mark (R1): a final NAV that used a stale mark is not an end value: final.valuation is STALE with
  TERMINAL_MARK_STALE, its nav is null, and cumulative return, CAGR, trailing returns, the last calendar year, the final
  partial monthly interval and the final point of the month-end MDD are null or left out; the ledger metrics status is
  TERMINAL_MARK_STALE. A final valuation PREVIOUS_CLOSE (an external series whose end-day open is missing and whose
  immediately preceding session close is used, labelled; benchmarks M3) is an accepted, labelled substitute.
- Calendar years (R3, missed M2): annual_returns uses only year boundaries; a year whose start or end boundary used a
  stale mark is null with YEAR_END_MARK_STALE. annual_return_detail gives each year's start, end, value, reason and
  partial flag (PARTIAL_YEAR: the start anchor is not the previous year's last session, or the end is not the year's
  last session); worst_year is taken over full calendar years only (null with NO_FULL_CALENDAR_YEAR, or
  INCOMPLETE_ANNUAL_RETURNS when a full year is null).
- Trailing N years (R5): with cycle boundaries (the runner always passes them) an N-year horizon is N complete annual
  reselection cycles, from the T open N cycles back (the initial capital at the first T, else that T's open NAV before
  trades) to the terminal reselection T open; basis RESELECTION_CYCLES. Null with INSUFFICIENT_HISTORY when fewer than N
  cycles exist and with RUN_NOT_ENDED_AT_RESELECTION_T_OPEN when the run does not end at a reselection T open. The
  calendar-date basis (CALENDAR_YEARS) is kept for calls without boundaries.
- Comparison inputs (R6): Sharpe / Sortino use a verified risk-free series when one is supplied (a RiskFreeSeries on the
  exact interval grid, or MonthlyRiskFreeRates by month, placed on each portfolio's grid), else MISSING_RISK_FREE; the
  information ratio uses the benchmark_monthly the caller passes (the runner: the same group's equal-weight series,
  same scenario and cost).

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
TERMINAL_MARK_STALE = 'TERMINAL_MARK_STALE'
YEAR_END_MARK_STALE = 'YEAR_END_MARK_STALE'
PARTIAL_YEAR = 'PARTIAL_YEAR'
NO_FULL_CALENDAR_YEAR = 'NO_FULL_CALENDAR_YEAR'
INCOMPLETE_ANNUAL_RETURNS = 'INCOMPLETE_ANNUAL_RETURNS'
VALUATION_STALE = 'STALE'
VALUATION_PREVIOUS_CLOSE = 'PREVIOUS_CLOSE'      # a labelled substitute for an end-day open (benchmarks M3)
NOT_STARTED = 'NOT_STARTED'
NO_SELECTED_REBALANCE_REACHED = 'NO_SELECTED_REBALANCE_REACHED'
START_BASIS = 'FIRST_SELECTED_REBALANCE_T'
BASIS_CYCLES = 'RESELECTION_CYCLES'
BASIS_CALENDAR_YEARS = 'CALENDAR_YEARS'
RUN_NOT_ENDED_AT_RESELECTION_T_OPEN = 'RUN_NOT_ENDED_AT_RESELECTION_T_OPEN'
REPORTED_NAV = 'INDEX_BASE_100'
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
class MonthlyRiskFreeRates:
    """Monthly risk-free returns by calendar month ('YYYY-MM' -> decimal fraction for that full month), with a named,
    verified source. series_metrics places them on each portfolio's own interval grid (full months only)."""
    source: str
    verified: bool
    by_month: Mapping[str, float]


def risk_free_on_grid(rates: MonthlyRiskFreeRates, monthly: Sequence[MonthlyReturn]) -> RiskFreeSeries:
    """A RiskFreeSeries on exactly the grid of `monthly`: a full month takes the rate of the month it ends in; a partial
    interval has none (risk metrics use full months only); a full month without a rate is None (MISSING_RISK_FREE)."""
    rows = tuple(MonthlyReturn(item.start, item.end,
                               rates.by_month.get(f'{item.end.year:04d}-{item.end.month:02d}') if item.full_month
                               else None, item.full_month) for item in monthly)
    return RiskFreeSeries(rates.source, rates.verified, rows)


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


def calendar_year_returns(nav_points: Sequence[NavPoint], *, started_at: date, initial_capital: float,
                          sessions: Sequence[date], coverage_end: date | None = None, stale_dates=()) -> dict:
    """Calendar-year returns from year boundaries only (review R3 / M2).

    Year y runs from its start anchor (the initial capital at started_at for the first year, else the NAV on the last
    point of year y-1) to the NAV on its last point. PARTIAL_YEAR when the start anchor is not the previous year's last
    calendar session or the end is not year y's last calendar session (or the calendar does not cover 31 December). A
    boundary NAV that used a stale mark makes the year null (YEAR_END_MARK_STALE); a missing boundary NAV INCOMPLETE_NAV.
    Returns {'annual_returns': {year: value | None}, 'annual_return_detail': {year: {start, end, value, reason,
    partial}}, 'worst_year', 'worst_year_reason'} with worst_year over full years only."""
    points = list(nav_points)
    _validate_points(points)
    stale = frozenset(stale_dates or ())
    days = sorted(set(sessions))
    coverage = (days[-1] if days else None) if coverage_end is None else coverage_end
    last_session = {}
    for day in days:
        last_session[day.year] = day

    def year_end(year):
        return last_session.get(year) if coverage is not None and coverage >= date(year, 12, 31) else None

    annual, detail = {}, {}
    if not points:
        return dict(annual_returns=annual, annual_return_detail=detail, worst_year=None,
                    worst_year_reason=NO_FULL_CALENDAR_YEAR)
    by_year = {}
    for point in points:
        by_year.setdefault(point.date.year, []).append(point)
    previous = None
    for year in sorted(by_year):
        end = by_year[year][-1]
        if previous is None:
            start_date, base, base_stale = started_at, float(initial_capital), False
        else:
            start_date, base, base_stale = previous.date, previous.nav, previous.date in stale
        partial = start_date != year_end(year - 1) or end.date != year_end(year)
        if base_stale or end.date in stale:
            value, reason = None, YEAR_END_MARK_STALE
        elif base is None or end.nav is None:
            value, reason = None, 'INCOMPLETE_NAV'
        elif base == 0:
            value, reason = None, 'ZERO_NAV_BASE'
        else:
            value, reason = end.nav / base - 1, None
        annual[year] = value
        detail[year] = dict(start=start_date, end=end.date, value=value, reason=reason, partial=partial,
                            partial_reason=PARTIAL_YEAR if partial else None)
        previous = end
    full = [year for year in annual if not detail[year]['partial']]
    if not full:
        worst, why = None, NO_FULL_CALENDAR_YEAR
    elif any(annual[year] is None for year in full):
        worst, why = None, INCOMPLETE_ANNUAL_RETURNS
    else:
        worst, why = min(full, key=lambda year: annual[year]), None
    return dict(annual_returns=annual, annual_return_detail=detail, worst_year=worst, worst_year_reason=why)


def cycle_trailing_returns(as_of: date, boundaries: Sequence, *, years: Sequence[int] = TRAILING_YEARS) -> dict:
    """Trailing N-year returns as N complete annual reselection cycles (review R5).

    boundaries: [(date, nav | None)] of every reselection T-open boundary from the start anchor (the initial capital at
    the first T) through the terminal T open when the run ends at one. The N-year return is NAV(terminal) / NAV(the
    boundary N cycles back) - 1, annualized over N; null with INSUFFICIENT_HISTORY when fewer than N cycles exist and
    with RUN_NOT_ENDED_AT_RESELECTION_T_OPEN when the last boundary is not as_of."""
    rows = list(boundaries)
    ended = bool(rows) and rows[-1][0] == as_of
    result = {}
    for n in years:
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError('Trailing periods are positive year counts')
        item = dict(years=n, basis=BASIS_CYCLES, cycles=n, start=None, end=as_of)
        if not ended:
            reason = RUN_NOT_ENDED_AT_RESELECTION_T_OPEN
        elif len(rows) - 1 < n:
            reason = INSUFFICIENT_HISTORY
        else:
            item['start'], base = rows[-1 - n]
            end_value = rows[-1][1]
            reason = ('INCOMPLETE_NAV' if base is None or end_value is None else 'ZERO_NAV_BASE' if base == 0 else None)
        if reason:
            item.update(total_return=Metric(None, reason), annualized_return=Metric(None, reason))
        else:
            total = end_value / base - 1
            item.update(total_return=Metric(total), annualized_return=Metric((1 + total) ** (1 / n) - 1))
        result[f'{n}y'] = item
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
        item = dict(years=n, basis=BASIS_CALENDAR_YEARS, start=None, end=as_of)
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
                   risk_free: RiskFreeSeries | MonthlyRiskFreeRates | None = None,
                   benchmark_monthly: Sequence[MonthlyReturn] | None = None, stale_dates=(),
                   final_valuation: str | None = None, cycle_boundaries: Sequence | None = None) -> dict:
    """Performance (DAILY), daily coverage, monthly metrics (MONTHLY), month-end NAV with the base-100 index, monthly
    returns, calendar-year returns, rolling windows, trailing returns and the final value for one NAV path (module doc).

    stale_dates: sessions whose NAV used a stale mark; final_valuation: CLOSE / OPEN / PREVIOUS_CLOSE of the last point
    (a stale final point that is not a labelled PREVIOUS_CLOSE is TERMINAL_MARK_STALE, review R1); cycle_boundaries:
    [(date, nav)] reselection T-open boundaries for the cycle-based trailing returns (review R5)."""
    points = list(nav_points)
    stale_dates = frozenset(stale_dates or ())
    calendar = sorted(sessions) if sessions is not None else [point.date for point in points]
    expected = [day for day in calendar if points and points[0].date <= day <= points[-1].date]
    final = points[-1] if points else None
    terminal_stale = (final is not None and final.date in stale_dates
                      and final_valuation != VALUATION_PREVIOUS_CLOSE)
    month_ends = (month_end_nav(points, sessions=calendar, coverage_end=coverage_end, initial_capital=initial_capital,
                                stale_dates=stale_dates) if points else [])
    monthly = monthly_returns(points, month_ends, started_at=started_at, initial_capital=initial_capital)
    if terminal_stale and monthly and monthly[-1].end == final.date and not monthly[-1].full_month:
        last = monthly[-1]
        monthly[-1] = MonthlyReturn(last.start, last.end, None, False)
    if isinstance(risk_free, MonthlyRiskFreeRates):
        risk_free = risk_free_on_grid(risk_free, monthly)
    perf = performance_metrics(points, monthly_returns=monthly, risk_free=risk_free,
                               benchmark_monthly=benchmark_monthly, expected_sessions=expected,
                               initial_capital=initial_capital, started_at=started_at)
    coverage = daily_coverage(points, expected, stale_dates)
    if terminal_stale:
        perf['cumulative_return'] = perf['cagr'] = Metric(None, TERMINAL_MARK_STALE)
    elif perf['cumulative_return'].value is None and final is not None and final.nav is not None and initial_capital:
        # Endpoint returns need only the start anchor and the final NAV, not every session.
        days = (final.date - started_at).days
        perf['cumulative_return'] = Metric(final.nav / initial_capital - 1)
        perf['cagr'] = (Metric((final.nav / initial_capital) ** (365.25 / days) - 1) if days
                        else Metric(None, 'ZERO_DURATION'))
    if coverage['status'] != DAILY_COVERAGE_COMPLETE:
        perf.update({key: Metric(None, DAILY_PRICES_NOT_SUPPLIED) for key in DAILY_METRIC_KEYS})
        perf.update(dict.fromkeys(DAILY_DETAIL_KEYS))
    perf.update(calendar_year_returns(points, started_at=started_at, initial_capital=initial_capital,
                                      sessions=calendar, coverage_end=coverage_end, stale_dates=stale_dates))
    performance = {'basis': BASIS_DAILY, **{key: value for key, value in perf.items()
                                            if key not in MONTHLY_METRIC_KEYS}}
    if cycle_boundaries is not None and final is not None:
        trailing = cycle_trailing_returns(final.date, cycle_boundaries)
    else:
        trailing = trailing_returns(points, started_at=started_at, initial_capital=initial_capital)
    if terminal_stale:
        for item in trailing.values():
            item.update(total_return=Metric(None, TERMINAL_MARK_STALE),
                        annualized_return=Metric(None, TERMINAL_MARK_STALE))
    return dict(performance=performance, daily_coverage=coverage,
                monthly=monthly_metrics(month_ends, monthly, started_at=started_at, initial_capital=initial_capital,
                                        final=None if terminal_stale else final, risk_free=risk_free,
                                        benchmark_monthly=benchmark_monthly),
                month_end_nav=month_ends, monthly_returns=monthly,
                rolling_windows=rolling_window_returns(month_ends), trailing_returns=trailing,
                terminal_mark_stale=terminal_stale,
                final=final_value(final, initial_capital, VALUATION_STALE if terminal_stale else final_valuation,
                                  stale=terminal_stale),
                nav_index_label=NAV_INDEX_LABEL)


def final_value(point: NavPoint | None, initial_capital, valuation=None, *, stale=False) -> dict:
    """{'date', 'valuation', 'nav_usd', 'nav_index', 'reason'} of the last NAV point (nav_index: the reported base-100
    NAV). A stale terminal mark is no end value: valuation STALE, nav null, reason TERMINAL_MARK_STALE (review R1)."""
    if stale:
        return dict(date=point.date, valuation=VALUATION_STALE, nav_usd=None, nav_index=None,
                    reason=TERMINAL_MARK_STALE)
    return dict(date=None if point is None else point.date, valuation=valuation,
                nav_usd=None if point is None else point.nav,
                nav_index=None if point is None else nav_index(point.nav, initial_capital), reason=None)


# -- ledger adapters --------------------------------------------------------------------------------------------
_REACHED = ('EXECUTED', 'NO_ORDERS')     # rebalance execution statuses whose T the run reached


def ledger_start(result: Mapping) -> date | None:
    """The start anchor of a run_ledger result (review M1): the T of its first rebalance with a non-empty selection
    that the run reached (executed, or reached without orders), else None. Unfilled picks are cash from that T."""
    for row in result['rebalances']:
        if row['selected'] and row.get('execution_status') in _REACHED:
            return row['execution_date']
    return None


def ledger_nav_points(result: Mapping) -> tuple[list[NavPoint], date | None, float]:
    """NAV points from the start anchor on (ledger_start), that date, and the initial capital (floats for statistics)."""
    started = ledger_start(result)
    points = [NavPoint(row['date'], None if row['nav'] is None else float(row['nav']))
              for row in result['daily'] if started is not None and row['date'] >= started]
    return points, started, float(result['initial_capital'])


def ledger_cycle_boundaries(result: Mapping, started: date) -> list:
    """[(date, nav | None)] reselection T-open boundaries of a run (review R5): the initial capital at the start anchor,
    each later reached rebalance's open NAV before trades, and the terminal open when the run ended at an OPEN
    valuation (the runner uses OPEN only for the next reselection T)."""
    rows = [(started, float(result['initial_capital']))]
    for row in result['rebalances']:
        if row['execution_date'] > started and row.get('execution_status') in _REACHED:
            value = row.get('open_nav_before_trades')
            rows.append((row['execution_date'], None if value is None else float(value)))
    last = result['daily'][-1] if result['daily'] else None
    if last is not None and result.get('end_valuation') == 'OPEN' and last['date'] > rows[-1][0]:
        rows.append((last['date'], None if last['nav'] is None else float(last['nav'])))
    return rows


def ledger_trades(result: Mapping) -> list[dict]:
    return [dict(date=fill.session, security_id=fill.security_id, side='BUY' if fill.quantity > 0 else 'SELL',
                 notional=float(fill.gross), cost=float(fill.fee)) for fill in result['fills']]


def ledger_stale_dates(result: Mapping) -> set:
    """Sessions whose ledger valuation used a stale mark for a held tradable name (STALE_MARK flag)."""
    return {row['date'] for row in result['daily'] if any(flag.startswith('STALE_MARK:') for flag in row['flags'])}


def ledger_metrics(result: Mapping, *, sessions: Sequence[date] | None = None, coverage_end: date | None = None,
                   risk_free: RiskFreeSeries | MonthlyRiskFreeRates | None = None,
                   benchmark_monthly: Sequence[MonthlyReturn] | None = None) -> dict:
    """All metrics for one run_ledger result, measured from its start anchor (the first selected rebalance's T, review
    M1; CAGR from there); daily coverage from the run's STALE_MARK flags; trailing returns on reselection cycles
    (module doc). status: NOT_STARTED, INCOMPLETE_NAV, TERMINAL_MARK_STALE or COMPLETE."""
    points, started, initial = ledger_nav_points(result)
    header = dict(scenario=result['scenario'], cost_bps=float(result['cost_bps']),
                  internal_notional_capital_usd=initial, reported_nav=REPORTED_NAV, currency=result['currency'],
                  started_at=started, start_basis=START_BASIS, end=result['end'],
                  end_valuation=result.get('end_valuation'))
    last = result['daily'][-1] if result['daily'] else None
    final = None if last is None else NavPoint(last['date'], None if last['nav'] is None else float(last['nav']))
    if started is None:
        null = Metric(None, NOT_STARTED)
        return dict(header, status=NOT_STARTED, reason=NO_SELECTED_REBALANCE_REACHED,
                    performance={'basis': BASIS_DAILY, **{key: null for key in
                                                          ('cagr', 'cumulative_return', 'annualized_volatility',
                                                           'max_drawdown')},
                                 'annual_returns': {}, 'annual_return_detail': {}, 'worst_year': None,
                                 'worst_year_reason': NOT_STARTED},
                    daily_coverage=dict(status=NOT_STARTED, sessions=0, uncovered_sessions=0, first_uncovered=None),
                    monthly={'basis': BASIS_MONTHLY, **{key: null for key in ('worst_month', 'sharpe', 'sortino',
                                                                             'information_ratio',
                                                                             'annualized_volatility',
                                                                             'max_drawdown')}},
                    month_end_nav=[], monthly_returns=[], rolling_windows=rolling_window_returns([]),
                    trailing_returns={f'{n}y': dict(years=n, basis=BASIS_CYCLES, cycles=n, start=None, end=None,
                                                    total_return=null, annualized_return=null)
                                      for n in TRAILING_YEARS},
                    terminal_mark_stale=False, turnover={},
                    cost_attribution=None,
                    final=final_value(final, initial, None if last is None else last.get('valuation')),
                    nav_index_label=NAV_INDEX_LABEL)
    if sessions is None:
        sessions = [row['date'] for row in result['daily']]
    metrics = series_metrics(points, started_at=started, initial_capital=initial, sessions=sessions,
                             coverage_end=coverage_end, risk_free=risk_free, benchmark_monthly=benchmark_monthly,
                             stale_dates={day for day in ledger_stale_dates(result) if day >= started},
                             final_valuation=last.get('valuation'),
                             cycle_boundaries=ledger_cycle_boundaries(result, started))
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
    status = ('INCOMPLETE_NAV' if result['status'] != 'COMPLETE'
              else TERMINAL_MARK_STALE if metrics['terminal_mark_stale'] else 'COMPLETE')
    return dict(header, status=status, **metrics, turnover=annual_turnover(trades, points), cost_attribution=cost)


def _selections(result):
    return [(row['signal_date'], row['execution_date'], tuple(row['selected'])) for row in result['rebalances']]


def cost_comparison(before_cost: Mapping, after_cost: Mapping, *, benchmark_before=None, benchmark_after=None,
                    **kwargs) -> dict:
    """Before-cost (cost 0) and after-cost (cost > 0) runs side by side, from the same selections and inputs.

    These are two ledger replays: fills differ because fees change cash, which is the experiment's
    before/after-cost report. kwargs go to ledger_metrics (sessions, coverage_end, risk_free); benchmark_before /
    benchmark_after are the information-ratio benchmarks (monthly returns) of the same cost level (review R6).
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
    before = ledger_metrics(before_cost, benchmark_monthly=benchmark_before, **kwargs)
    after = ledger_metrics(after_cost, benchmark_monthly=benchmark_after, **kwargs)
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
