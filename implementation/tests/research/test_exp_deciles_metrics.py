"""Hand-oracle metric tests for EXP-STOCK-INDICATOR-DECILES-v1. All inputs are synthetic."""
from datetime import date, timedelta
from decimal import Decimal
import math

import pytest

from investment_system.research.exp_deciles import metrics as m
from investment_system.research.exp_deciles.ledger import Rebalance, run_ledger

D = Decimal


def points(start, values, step=1):
    return [m.NavPoint(start + timedelta(days=i * step), v) for i, v in enumerate(values)]


def weekdays(first, last, drop=()):
    days, day = [], first
    while day <= last:
        if day.weekday() < 5 and day not in drop:
            days.append(day)
        day += timedelta(days=1)
    return days


def month_ends(values, start_year=2030):
    rows = []
    for i, value in enumerate(values):
        year, month = start_year + i // 12, i % 12 + 1
        rows.append(m.MonthEndNav(f'{year:04d}-{month:02d}', date(year, month, 28), value, value is not None,
                                  None if value is not None else 'INCOMPLETE_NAV'))
    return rows


# -- ported core metrics ----------------------------------------------------------------------------------------
def test_cagr_cumulative_daily_volatility_and_drawdown_recovery_hand_oracle():
    result = m.performance_metrics(points(date(2030, 1, 1), [100, 120, 90, 120, 110]))
    assert result['cumulative_return'].value == pytest.approx(.10)
    assert result['cagr'].value == pytest.approx(1.1 ** (365.25 / 4) - 1)
    # Returns 1/5,-1/4,1/3,-1/12: sample variance 379/5400.
    assert result['annualized_volatility'].value == pytest.approx(math.sqrt(379 / 5400 * 252))
    assert result['max_drawdown'].value == pytest.approx(-.25)
    assert result['max_drawdown_peak_date'] == date(2030, 1, 2)
    assert result['max_drawdown_trough_date'] == date(2030, 1, 3)
    assert result['max_drawdown_recovery_date'] == date(2030, 1, 4)
    assert result['max_drawdown_recovery_sessions'] == 2 and result['max_drawdown_recovered'] is True


def test_cagr_from_first_fill_uses_initial_capital_anchor_and_actual_days():
    nav = points(date(2030, 2, 20), [99.9, 105, 109.89])
    result = m.performance_metrics(nav, initial_capital=100, started_at=date(2030, 2, 20))
    assert result['cumulative_return'].value == pytest.approx(.0989)
    assert result['cagr'].value == pytest.approx(1.0989 ** (365.25 / 2) - 1)
    with pytest.raises(ValueError):
        m.performance_metrics(nav, started_at=date(2030, 2, 21))


def test_unrecovered_drawdown_and_missing_nav_are_explicit():
    result = m.performance_metrics(points(date(2030, 1, 1), [100, 120, 90, 95]))
    assert result['max_drawdown_recovered'] is False and result['max_drawdown_recovery_sessions'] is None
    assert result['max_drawdown_elapsed_sessions'] == 2
    missing = m.performance_metrics([m.NavPoint(date(2030, 1, 1), 100), m.NavPoint(date(2030, 1, 2), None)])
    assert missing['cagr'] == m.Metric(None, 'INCOMPLETE_NAV')
    gap = m.performance_metrics(points(date(2030, 1, 1), [100, 110], step=2),
                                expected_sessions=[date(2030, 1, 1), date(2030, 1, 2), date(2030, 1, 3)])
    assert gap['cagr'].reason == 'INCOMPLETE_NAV'


def test_calendar_year_returns_chain_from_prior_year_end():
    result = m.performance_metrics([m.NavPoint(date(2030, 6, 1), 100), m.NavPoint(date(2030, 12, 31), 110),
                                    m.NavPoint(date(2031, 12, 31), 88), m.NavPoint(date(2032, 12, 31), 132)])
    assert result['annual_returns'][2030] == pytest.approx(.1)
    assert result['annual_returns'][2031] == pytest.approx(-.2)
    assert result['annual_returns'][2032] == pytest.approx(.5)
    assert result['worst_year'] == 2031


def test_sharpe_and_sortino_only_with_a_verified_risk_free_series():
    grid = [(date(2030, 1, 31), date(2030, 2, 28)), (date(2030, 2, 28), date(2030, 3, 29)),
            (date(2030, 3, 29), date(2030, 4, 30))]
    monthly = [m.MonthlyReturn(a, b, r) for (a, b), r in zip(grid, [.03, -.01, .02])]
    rf_rows = tuple(m.MonthlyReturn(a, b, .01) for a, b in grid)
    missing = m.monthly_risk_metrics(monthly)
    assert missing['sharpe'] == m.Metric(None, 'MISSING_RISK_FREE')
    assert missing['sortino'] == m.Metric(None, 'MISSING_RISK_FREE')
    for unverified in (m.RiskFreeSeries('synthetic rf', False, rf_rows), m.RiskFreeSeries(' ', True, rf_rows),
                       rf_rows):
        result = m.monthly_risk_metrics(monthly, risk_free=unverified)
        assert result['sharpe'] == m.Metric(None, 'RISK_FREE_UNVERIFIED')
        assert result['sortino'] == m.Metric(None, 'RISK_FREE_UNVERIFIED')
    verified = m.monthly_risk_metrics(monthly, risk_free=m.RiskFreeSeries('synthetic rf', True, rf_rows))
    # Excess .02,-.02,.01: mean .01/3, sample variance .00043333.
    assert verified['sharpe'].value == pytest.approx(math.sqrt(12) / math.sqrt(39))
    assert verified['sortino'].value == pytest.approx(1.0)
    shifted = m.RiskFreeSeries('synthetic rf', True, rf_rows[1:] + rf_rows[:1])
    assert m.monthly_risk_metrics(monthly, risk_free=shifted)['sharpe'].reason == 'RISK_FREE_ALIGNMENT_MISMATCH'


# -- month-end NAV, monthly returns, rolling windows, trailing returns ----------------------------------------
def test_month_end_nav_uses_the_calendar_last_session_and_flags_partial_months():
    holiday = date(2030, 1, 31)
    sessions = weekdays(date(2030, 1, 1), date(2030, 3, 29), drop=(holiday,))
    nav = [m.NavPoint(day, 100 + i) for i, day in enumerate(s for s in sessions if s <= date(2030, 3, 15))]
    rows = m.month_end_nav(nav, sessions=sessions, coverage_end=date(2030, 3, 31))
    assert [(r.month, r.date, r.complete, r.reason) for r in rows] == [
        ('2030-01', date(2030, 1, 30), True, None),
        ('2030-02', date(2030, 2, 28), True, None),
        ('2030-03', date(2030, 3, 29), False, 'PARTIAL_MONTH')]
    assert rows[0].nav == next(p.nav for p in nav if p.date == date(2030, 1, 30))
    short = m.month_end_nav(nav, sessions=sessions, coverage_end=date(2030, 2, 27))
    assert (short[1].complete, short[1].reason, short[1].date) == (False, 'PARTIAL_MONTH', None)
    gap = [p if p.date != date(2030, 2, 28) else m.NavPoint(p.date, None) for p in nav]
    assert m.month_end_nav(gap, sessions=sessions)[1].reason == 'INCOMPLETE_NAV'
    # Without coverage past 31 March the calendar cannot confirm March's last session.
    assert m.month_end_nav(nav, sessions=sessions)[2].date is None


def test_monthly_returns_mark_first_and_last_intervals_partial():
    sessions = weekdays(date(2030, 2, 18), date(2030, 4, 30))
    nav = [m.NavPoint(day, 100.0) for day in sessions if day <= date(2030, 4, 10)]
    nav[-1] = m.NavPoint(nav[-1].date, 110.0)
    rows = m.month_end_nav(nav, sessions=sessions)
    monthly = m.monthly_returns(nav, rows, started_at=sessions[0], initial_capital=100)
    assert [(r.start, r.end, r.full_month) for r in monthly] == [
        (date(2030, 2, 18), date(2030, 2, 28), False),
        (date(2030, 2, 28), date(2030, 3, 29), True),
        (date(2030, 3, 29), date(2030, 4, 10), False)]
    assert monthly[-1].value == pytest.approx(.1)


def test_rolling_windows_list_every_window_with_worst_best_median():
    rows = month_ends([100, 110, 90, 100, 100, 100, 100, 100, 100, 100, 100, 100, 120, 99])
    result = m.rolling_window_returns(rows)
    twelve = result[12]
    assert twelve['count'] == 2
    assert [w['total_return'].value for w in twelve['windows']] == pytest.approx([.2, 99 / 110 - 1])
    assert twelve['windows'][0]['start_month'] == '2030-01' and twelve['windows'][0]['end_month'] == '2031-01'
    assert twelve['worst'].value == pytest.approx(-.1) and twelve['best'].value == pytest.approx(.2)
    assert twelve['median'].value == pytest.approx(.05)
    assert twelve['windows'][0]['annualized_return'].value == pytest.approx(.2)
    for window in (36, 60, 120):
        assert result[window]['count'] == 0 and result[window]['windows'] == []
        for key in ('worst', 'best', 'median'):
            assert result[window][key] == m.Metric(None, 'INSUFFICIENT_HISTORY')


def test_rolling_windows_36_month_annualizes_and_interior_gap_nulls_its_windows():
    values = [100.0 * 1.01 ** i for i in range(38)]
    result = m.rolling_window_returns(month_ends(values), windows=(36,))
    assert result[36]['count'] == 2
    assert result[36]['windows'][0]['total_return'].value == pytest.approx(1.01 ** 36 - 1)
    assert result[36]['windows'][0]['annualized_return'].value == pytest.approx(1.01 ** 12 - 1)
    values[1] = None
    gapped = m.rolling_window_returns(month_ends(values), windows=(36,))[36]
    assert gapped['windows'][1]['total_return'] == m.Metric(None, 'INCOMPLETE_MONTH_END_NAV')
    assert gapped['incomplete_windows'] == 1
    assert gapped['worst'].value == pytest.approx(1.01 ** 36 - 1)


def test_trailing_returns_are_null_with_insufficient_history_when_too_short():
    nav = [m.NavPoint(date(2030, 2, 20), 100), m.NavPoint(date(2031, 3, 3), 110),
           m.NavPoint(date(2032, 3, 3), 121)]
    result = m.trailing_returns(nav, started_at=date(2030, 2, 20), initial_capital=100)
    assert result['1y']['total_return'].value == pytest.approx(.1)
    assert result['1y']['annualized_return'].value == pytest.approx(.1)
    assert result['1y']['start'] == date(2031, 3, 3) and result['1y']['end'] == date(2032, 3, 3)
    for key in ('3y', '5y', '10y'):
        assert result[key]['total_return'] == m.Metric(None, 'INSUFFICIENT_HISTORY')
        assert result[key]['annualized_return'] == m.Metric(None, 'INSUFFICIENT_HISTORY')
    two = m.trailing_returns(nav, years=(2,), started_at=date(2030, 2, 20), initial_capital=100)['2y']
    assert two['total_return'].value == pytest.approx(.21) and two['annualized_return'].value == pytest.approx(.1)
    leap = m.trailing_returns([m.NavPoint(date(2031, 2, 28), 100), m.NavPoint(date(2032, 2, 29), 105)], years=(1,))
    assert leap['1y']['start'] == date(2031, 2, 28)
    assert m.trailing_returns([m.NavPoint(date(2031, 3, 1), 100), m.NavPoint(date(2032, 2, 29), 105)],
                              years=(1,))['1y']['total_return'].reason == 'INSUFFICIENT_HISTORY'


# -- ledger adapters and before/after cost ----------------------------------------------------------------------
LONG_DAYS = tuple(date(2030, 2, 18) + timedelta(days=i) for i in range(800))


def _long_prices():
    rows = []
    for i, day in enumerate(LONG_DAYS):
        a = D(10) + D(i) / D(100)
        b = D(20) - D(i % 50) / D(10)
        rows.append(dict(date=day, security_id='A', open=a, close=a, price_basis='RAW'))
        rows.append(dict(date=day, security_id='B', open=b, close=b, price_basis='RAW'))
    return rows


def _long_run(cost, selected=('A', 'B')):
    rebalances = [Rebalance(LONG_DAYS[0], LONG_DAYS[1], list(selected)),
                  Rebalance(LONG_DAYS[365], LONG_DAYS[366], ['A'])]
    return run_ledger(LONG_DAYS, rebalances, _long_prices(), scenario='LOSS', cost_bps=cost,
                      initial_capital=1000000)


def test_ledger_metrics_measure_from_the_first_selected_t_with_turnover_and_cost_attribution():
    result = _long_run(10)
    metrics = m.ledger_metrics(result)
    assert metrics['started_at'] == LONG_DAYS[1] and metrics['status'] == 'COMPLETE'
    final = float(result['daily'][-1]['nav'])
    assert metrics['performance']['cumulative_return'].value == pytest.approx(final / 1000000 - 1)
    days = (LONG_DAYS[-1] - LONG_DAYS[1]).days
    assert metrics['performance']['cagr'].value == pytest.approx((final / 1000000) ** (365.25 / days) - 1)
    fees = float(result['total_costs'])
    cost = metrics['cost_attribution']
    assert cost['status'] == 'OK' and cost['total_cost'] == pytest.approx(fees)
    assert cost['gross_final_nav'] == pytest.approx(final + fees)
    assert cost['total_cost_to_initial_capital'] == pytest.approx(fees / 1000000)
    assert sum(cost['cost_by_year'].values()) == pytest.approx(fees)
    first_year = LONG_DAYS[1].year
    gross_first = sum(float(f.gross) for f in result['fills'] if f.session.year == first_year)
    navs = [float(r['nav']) for r in result['daily'] if r['date'] >= LONG_DAYS[1] and r['date'].year == first_year]
    assert metrics['turnover'][first_year].value == pytest.approx(gross_first / (sum(navs) / len(navs)))
    assert metrics['month_end_nav'][0].month == '2030-02' and metrics['month_end_nav'][0].complete
    assert metrics['rolling_windows'][12]['count'] >= 1
    assert metrics['rolling_windows'][36]['worst'] == m.Metric(None, 'INSUFFICIENT_HISTORY')
    # Review R5: trailing horizons are reselection cycles; this run ends at a close, not at a reselection T open.
    for key in ('1y', '3y'):
        assert metrics['trailing_returns'][key]['total_return'] == m.Metric(None, 'RUN_NOT_ENDED_AT_RESELECTION_T_OPEN')
        assert metrics['trailing_returns'][key]['basis'] == 'RESELECTION_CYCLES'
    assert metrics['monthly']['sharpe'] == m.Metric(None, 'MISSING_RISK_FREE') and 'sharpe' not in metrics['performance']
    assert metrics['daily_coverage']['status'] == 'DAILY_COVERAGE_COMPLETE'
    assert metrics['performance']['basis'] == 'DAILY' and metrics['monthly']['basis'] == 'MONTHLY'


def test_cost_comparison_reports_before_and_after_cost_side_by_side():
    before, after = _long_run(0), _long_run(10)
    report = m.cost_comparison(before, after)
    assert report['before_cost_bps'] == 0 and report['after_cost_bps'] == 10
    assert report['before_cost']['cost_attribution']['total_cost'] == 0
    assert report['after_cost_total_fees'] == pytest.approx(float(after['total_costs'])) and report[
        'after_cost_total_fees'] > 0
    b = report['before_cost']['performance']['cumulative_return'].value
    a = report['after_cost']['performance']['cumulative_return'].value
    assert a < b and report['after_minus_before']['cumulative_return'].value == pytest.approx(a - b)
    assert report['after_minus_before']['final_nav'].value < 0
    assert report['after_minus_before']['cagr'].value < 0
    with pytest.raises(ValueError, match='BEFORE_COST_RUN_MUST_HAVE_ZERO_COST'):
        m.cost_comparison(after, before)
    with pytest.raises(ValueError, match='COST_RUNS_DIFFER_IN_SELECTIONS'):
        m.cost_comparison(before, _long_run(10, selected=('A',)))


def test_an_all_unfilled_year_is_cash_from_its_t_and_only_a_run_without_a_selected_t_is_not_started():
    """Review M1: a run whose picks all went unfilled was NO_FILL with every metric null (and a later year's metrics
    started at that year's first fill); the rules hold that year as cash."""
    days = LONG_DAYS[:10]
    rows = [dict(date=day, security_id='A', open=None, close=10, price_basis='RAW') for day in days]
    result = run_ledger(days, [Rebalance(days[0], days[1], ['A'])], rows, scenario='LOSS', cost_bps=0,
                        initial_capital=1000)
    metrics = m.ledger_metrics(result)
    assert metrics['status'] == 'COMPLETE' and metrics['started_at'] == days[1]
    assert metrics['start_basis'] == 'FIRST_SELECTED_REBALANCE_T'
    assert metrics['performance']['cumulative_return'] == m.Metric(0.0)
    empty = m.ledger_metrics(run_ledger(days, [Rebalance(days[0], days[1], [])], rows, scenario='LOSS', cost_bps=0,
                                        initial_capital=1000))
    assert (empty['status'], empty['reason']) == ('NOT_STARTED', 'NO_SELECTED_REBALANCE_REACHED')
    assert empty['performance']['cagr'] == m.Metric(None, 'NOT_STARTED')
    assert empty['trailing_returns']['1y']['total_return'] == m.Metric(None, 'NOT_STARTED')
    # Two cycles: year 1 all unfilled (cash), year 2 filled. The anchor stays at year 1's T.
    long_rows = [r for r in _long_prices() if not (r['security_id'] == 'B' and r['date'] == LONG_DAYS[1])]
    two = run_ledger(LONG_DAYS[:500], [Rebalance(LONG_DAYS[0], LONG_DAYS[1], ['B']),
                                       Rebalance(LONG_DAYS[365], LONG_DAYS[366], ['A'])],
                     long_rows, scenario='LOSS', cost_bps=0, initial_capital=1000)
    measured = m.ledger_metrics(two)
    assert two['first_fill_date'] == LONG_DAYS[366] and measured['started_at'] == LONG_DAYS[1]
    assert measured['performance']['annual_returns'][2030] == 0.0
    days_held = (LONG_DAYS[499] - LONG_DAYS[1]).days
    final = float(two['daily'][-1]['nav']) / 1000
    assert measured['performance']['cagr'].value == pytest.approx(final ** (365.25 / days_held) - 1)



# -- owner 11/01 decision 7: daily metrics only with daily prices; monthly metrics reported separately -------------
def _monthly_only_prices():
    """A, B priced at S, T, every month end and the last day only (no other session)."""
    keep, rows = set(), []
    for i, day in enumerate(LONG_DAYS[:400]):
        nxt = LONG_DAYS[i + 1] if i + 1 < 400 else None
        if i in (0, 1, 399) or nxt is None or nxt.month != day.month:
            keep.add(day)
    for row in _long_prices():
        if row['date'] in keep:
            rows.append(row)
    return rows


def test_daily_metrics_are_null_without_daily_prices_and_monthly_metrics_are_labelled():
    days = LONG_DAYS[:400]
    rebalances = [Rebalance(days[0], days[1], ['A', 'B'])]
    full = m.ledger_metrics(run_ledger(days, rebalances, [r for r in _long_prices() if r['date'] in set(days)],
                                       scenario='LOSS', cost_bps=0, initial_capital=1000000))
    assert full['daily_coverage'] == {'status': 'DAILY_COVERAGE_COMPLETE', 'sessions': 399, 'uncovered_sessions': 0,
                                      'first_uncovered': None}
    assert full['performance']['annualized_volatility'].value is not None
    sparse_run = run_ledger(days, rebalances, _monthly_only_prices(), scenario='LOSS', cost_bps=0,
                            initial_capital=1000000)
    sparse = m.ledger_metrics(sparse_run)
    assert sparse['daily_coverage']['status'] == 'DAILY_PRICES_NOT_SUPPLIED'
    assert sparse['daily_coverage']['first_uncovered'] == days[2]
    for key in ('annualized_volatility', 'max_drawdown'):
        assert sparse['performance'][key] == m.Metric(None, 'DAILY_PRICES_NOT_SUPPLIED')
    assert sparse['performance']['max_drawdown_recovery_date'] is None
    assert sparse['performance']['max_drawdown_peak_date'] is None
    # Endpoint and month-end values do not need daily prices: they equal the fully priced run's.
    assert sparse['performance']['cumulative_return'].value == pytest.approx(full['performance']['cumulative_return'].value)
    assert [r.nav for r in sparse['month_end_nav']] == [r.nav for r in full['month_end_nav']]
    assert sparse['monthly']['basis'] == 'MONTHLY' and sparse['monthly']['max_drawdown'].value is not None
    assert sparse['monthly']['annualized_volatility'].value == pytest.approx(
        full['monthly']['annualized_volatility'].value)
    assert sparse['monthly']['worst_month'].value == pytest.approx(full['monthly']['worst_month'].value)


def test_a_stale_month_end_mark_is_not_a_month_end_value():
    days = LONG_DAYS[:60]
    rows = [r for r in _long_prices() if r['date'] in set(days) and not (r['security_id'] == 'B'
                                                                         and r['date'] == date(2030, 3, 31))]
    metrics = m.ledger_metrics(run_ledger(days, [Rebalance(days[0], days[1], ['A', 'B'])], rows, scenario='LOSS',
                                          cost_bps=0, initial_capital=1000000))
    march = next(r for r in metrics['month_end_nav'] if r.month == '2030-03')
    assert (march.nav, march.complete, march.reason) == (None, False, 'MONTH_END_MARK_STALE')
    assert metrics['daily_coverage']['uncovered_sessions'] == 1


def test_base_100_nav_index_next_to_usd_nav_is_a_display_normalisation():
    result = _long_run(10)
    metrics = m.ledger_metrics(result)
    for row in metrics['month_end_nav']:
        if row.complete:
            assert row.nav_index == pytest.approx(row.nav / 1000000 * 100)
    final = metrics['final']
    assert final['date'] == LONG_DAYS[-1] and final['valuation'] == 'CLOSE'
    assert final['nav_usd'] == pytest.approx(float(result['daily'][-1]['nav']))
    assert final['nav_index'] == pytest.approx(final['nav_usd'] / 10000)
    assert metrics['nav_index_label'].startswith('REPORTED_NAV_INDEX_BASE_100')
    assert m.nav_index(1100000, 1000000) == pytest.approx(110.0) and m.nav_index(None, 1000000) is None


# -- review R1 / R3 / M2 / R5 / R6 -------------------------------------------------------------------------------
def _terminal_open_run(skip_terminal_open=False, end_index=366):
    """Two names from LONG_DAYS[1]; run held to LONG_DAYS[end_index] valued at its OPEN (the next reselection T)."""
    days = LONG_DAYS[:end_index + 1]
    rows = [r for r in _long_prices() if r['date'] in set(days)
            and not (skip_terminal_open and r['date'] == days[-1])]
    return run_ledger(days, [Rebalance(days[0], days[1], ['A', 'B'])], rows, scenario='LOSS', cost_bps=0,
                      initial_capital=1000000, end=days[-1], end_valuation='OPEN')


def test_a_stale_terminal_mark_is_not_an_end_value():
    """Review R1: with the next-T open missing, the final NAV was a stale mark labelled OPEN and cumulative return /
    CAGR were reported from it."""
    fresh = m.ledger_metrics(_terminal_open_run())
    assert fresh['status'] == 'COMPLETE' and fresh['final']['valuation'] == 'OPEN'
    assert fresh['performance']['cagr'].value is not None
    stale = m.ledger_metrics(_terminal_open_run(skip_terminal_open=True))
    assert stale['status'] == 'TERMINAL_MARK_STALE' and stale['terminal_mark_stale'] is True
    assert stale['final'] == {'date': LONG_DAYS[366], 'valuation': 'STALE', 'nav_usd': None, 'nav_index': None,
                              'reason': 'TERMINAL_MARK_STALE'}
    for key in ('cumulative_return', 'cagr'):
        assert stale['performance'][key] == m.Metric(None, 'TERMINAL_MARK_STALE')
    assert all(item['total_return'] == m.Metric(None, 'TERMINAL_MARK_STALE')
               for item in stale['trailing_returns'].values())
    assert stale['performance']['annual_returns'][LONG_DAYS[366].year] is None
    assert stale['monthly_returns'][-1].value is None
    # The month-end MDD leaves the stale endpoint out instead of using it.
    assert stale['monthly']['max_drawdown'].value is not None


def test_calendar_years_use_fresh_boundaries_and_worst_year_skips_partial_years():
    """Review R3 / M2: a stale 31 December went into the calendar-year returns, and partial first / last years were
    compared with full ones in worst_year."""
    days = LONG_DAYS[:700]
    rows = [r for r in _long_prices() if r['date'] in set(days)]
    rebalances = [Rebalance(days[0], days[1], ['A', 'B'])]
    full = m.ledger_metrics(run_ledger(days, rebalances, rows, scenario='LOSS', cost_bps=0, initial_capital=1000000))
    detail = full['performance']['annual_return_detail']
    assert [(y, detail[y]['partial']) for y in sorted(detail)] == [(2030, True), (2031, False), (2032, True)]
    assert full['performance']['worst_year'] == 2031 and full['performance']['worst_year_reason'] is None
    assert detail[2031]['start'] == date(2030, 12, 31) and detail[2031]['end'] == date(2031, 12, 31)
    gap = [r for r in rows if not (r['security_id'] == 'B' and r['date'] == date(2030, 12, 31))]
    stale = m.ledger_metrics(run_ledger(days, rebalances, gap, scenario='LOSS', cost_bps=0, initial_capital=1000000))
    annual = stale['performance']['annual_returns']
    assert annual[2030] is None and annual[2031] is None and annual[2032] is not None
    assert stale['performance']['annual_return_detail'][2030]['reason'] == 'YEAR_END_MARK_STALE'
    assert stale['performance']['worst_year'] is None
    assert stale['performance']['worst_year_reason'] == 'INCOMPLETE_ANNUAL_RETURNS'
    short = m.ledger_metrics(_terminal_open_run())
    assert short['performance']['worst_year'] is None
    assert short['performance']['worst_year_reason'] == 'NO_FULL_CALENDAR_YEAR'


def test_trailing_horizons_are_complete_reselection_cycles():
    """Review R5: T 2018-02-20 to T 2019-02-19 (one full cycle) gave INSUFFICIENT_HISTORY for 1y because the dates
    moved; an N-year horizon is now N complete cycles from the T open N cycles back to the terminal T open."""
    result = _terminal_open_run(end_index=365)                 # 364 calendar days: one cycle, shorter than a year
    metrics = m.ledger_metrics(result)
    one = metrics['trailing_returns']['1y']
    assert (one['basis'], one['start'], one['end']) == ('RESELECTION_CYCLES', LONG_DAYS[1], LONG_DAYS[365])
    assert one['total_return'].value == pytest.approx(float(result['daily'][-1]['nav']) / 1000000 - 1)
    assert metrics['trailing_returns']['3y']['total_return'] == m.Metric(None, 'INSUFFICIENT_HISTORY')
    # Two cycles: the 1y base is the second T's open NAV before trades.
    days = LONG_DAYS[:731]
    two = run_ledger(days, [Rebalance(days[0], days[1], ['A', 'B']), Rebalance(days[365], days[366], ['A'])],
                     [r for r in _long_prices() if r['date'] in set(days)], scenario='LOSS', cost_bps=0,
                     initial_capital=1000000, end=days[730], end_valuation='OPEN')
    trailing = m.ledger_metrics(two)['trailing_returns']
    base = float(two['rebalances'][1]['open_nav_before_trades'])
    assert trailing['1y']['start'] == days[366]
    assert trailing['1y']['total_return'].value == pytest.approx(float(two['daily'][-1]['nav']) / base - 1)
    assert trailing['3y']['total_return'] == m.Metric(None, 'INSUFFICIENT_HISTORY')


def test_information_ratio_and_sharpe_use_the_supplied_benchmark_and_verified_risk_free():
    """Review R6: IR was always MISSING_BENCHMARK and Sharpe / Sortino could never be computed."""
    before, after = _long_run(0), _long_run(10)
    bench = m.cost_comparison(_long_run(0, selected=('A',)), _long_run(10, selected=('A',)))
    report = m.cost_comparison(before, after, benchmark_before=bench['before_cost']['monthly_returns'],
                               benchmark_after=bench['after_cost']['monthly_returns'])
    assert report['before_cost']['monthly']['information_ratio'].value is not None
    assert report['after_cost']['monthly']['information_ratio'].value is not None
    assert report['after_cost']['monthly']['sharpe'] == m.Metric(None, 'MISSING_RISK_FREE')
    months = {f'{y:04d}-{mo:02d}': 0.001 for y in (2030, 2031, 2032) for mo in range(1, 13)}
    verified = m.ledger_metrics(after, risk_free=m.MonthlyRiskFreeRates('synthetic verified source', True, months))
    assert verified['monthly']['sharpe'].value is not None and verified['monthly']['sortino'].value is not None
    unverified = m.ledger_metrics(after, risk_free=m.MonthlyRiskFreeRates('synthetic', False, months))
    assert unverified['monthly']['sharpe'] == m.Metric(None, 'RISK_FREE_UNVERIFIED')
    gap = m.ledger_metrics(after, risk_free=m.MonthlyRiskFreeRates('synthetic', True, {'2030-03': 0.001}))
    assert gap['monthly']['sharpe'] == m.Metric(None, 'MISSING_RISK_FREE')


def test_ledger_metric_headers_name_the_internal_notional_and_the_reported_nav():
    """Review R8: the metrics header exported the internal notional as 'initial_capital'."""
    metrics = m.ledger_metrics(_long_run(0))
    assert 'initial_capital' not in metrics
    assert (metrics['internal_notional_capital_usd'], metrics['reported_nav']) == (1000000.0, 'INDEX_BASE_100')
