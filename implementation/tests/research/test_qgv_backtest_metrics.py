"""Hand-oracle tests for research metrics; all inputs are synthetic."""
from datetime import date, timedelta
import math
import unittest

from investment_system.research.qgv_backtest import metrics as m


class MetricsTests(unittest.TestCase):
    def test_actual_days_cagr_daily_sample_volatility_and_recovery(self):
        nav = [m.NavPoint(date(2020, 1, 1) + timedelta(days=i), value)
               for i, value in enumerate([100, 120, 90, 120, 110])]
        result = m.performance_metrics(nav)
        self.assertAlmostEqual(result['cumulative_return'].value, .10)
        self.assertAlmostEqual(result['cagr'].value, 1.1 ** (365.25 / 4) - 1)
        # Four returns: 1/5,-1/4,1/3,-1/12; mean=1/20, sample variance=379/5400.
        self.assertAlmostEqual(result['annualized_volatility'].value,
                               math.sqrt(379 / 5400 * 252))
        self.assertAlmostEqual(result['max_drawdown'].value, -.25)
        self.assertEqual(result['max_drawdown_recovery_sessions'], 2)
        self.assertEqual(result['max_drawdown_recovered'], True)

    def test_unrecovered_drawdown_reports_elapsed_sessions_without_fake_recovery(self):
        result = m.performance_metrics([m.NavPoint(date(2020, 1, 1) + timedelta(days=i), v)
                                        for i, v in enumerate([100, 120, 90, 95])])
        self.assertIsNone(result['max_drawdown_recovery_sessions'])
        self.assertFalse(result['max_drawdown_recovered'])
        self.assertEqual(result['max_drawdown_elapsed_sessions'], 2)

    def test_missing_daily_nav_and_missing_expected_session_never_fill_zero(self):
        points = [m.NavPoint(date(2020, 1, 1), 100), m.NavPoint(date(2020, 1, 3), None)]
        for nav, expected in [(points, None),
                              (points[:1] + [m.NavPoint(date(2020, 1, 3), 110)],
                               [date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 3)])]:
            result = m.performance_metrics(nav, expected_sessions=expected)
            self.assertIsNone(result['cagr'].value)
            self.assertEqual(result['cagr'].reason, 'INCOMPLETE_NAV')

    def test_nonfinite_negative_duplicate_and_unsorted_nav_rejected(self):
        for points in [
            [(date(2020, 1, 1), 100), (date(2020, 1, 2), float('nan'))],
            [(date(2020, 1, 1), 100), (date(2020, 1, 2), -1)],
            [(date(2020, 1, 1), 100), (date(2020, 1, 1), 110)],
            [(date(2020, 1, 2), 100), (date(2020, 1, 1), 110)],
        ]:
            with self.assertRaises(ValueError):
                m.performance_metrics([m.NavPoint(*point) for point in points])

    def test_year_returns_include_prior_year_close_and_partial_initial_year(self):
        result = m.performance_metrics([
            m.NavPoint(date(2019, 6, 1), 100), m.NavPoint(date(2019, 12, 31), 110),
            m.NavPoint(date(2020, 12, 31), 88), m.NavPoint(date(2021, 12, 31), 132)])
        self.assertAlmostEqual(result['annual_returns'][2019], .1)
        self.assertAlmostEqual(result['annual_returns'][2020], -.2)
        self.assertAlmostEqual(result['annual_returns'][2021], .5)
        self.assertEqual(result['worst_year'], 2020)

    def test_full_month_sharpe_sortino_and_information_ratio_hand_oracles(self):
        dates = [(date(2020, 1, 31), date(2020, 2, 29)),
                 (date(2020, 2, 29), date(2020, 3, 31)),
                 (date(2020, 3, 31), date(2020, 4, 30))]
        monthly = [m.MonthlyReturn(a, b, r) for (a, b), r in zip(dates, [.03, -.01, .02])]
        rf = [m.MonthlyReturn(a, b, .01) for a, b in dates]
        benchmark = [m.MonthlyReturn(a, b, r) for (a, b), r in zip(dates, [.01, .01, .01])]
        result = m.monthly_risk_metrics(monthly, risk_free_monthly=rf,
                                        benchmark_monthly=benchmark)
        # Excess = .02,-.02,.01. Mean=.01/3; sample variance=.0004333333333.
        self.assertAlmostEqual(result['sharpe'].value, math.sqrt(12) / math.sqrt(39))
        # Downside denominator averages all THREE observations, not just one loss.
        self.assertAlmostEqual(result['sortino'].value, 1.0)
        self.assertAlmostEqual(result['information_ratio'].value, math.sqrt(12) / math.sqrt(39))
        self.assertAlmostEqual(result['worst_month'].value, -.01)

    def test_partial_month_excluded_and_missing_rf_or_zero_denominator_is_explicit_na(self):
        a, b, c = date(2020, 1, 15), date(2020, 1, 31), date(2020, 2, 29)
        monthly = [m.MonthlyReturn(a, b, -.9, full_month=False), m.MonthlyReturn(b, c, .01)]
        result = m.monthly_risk_metrics(monthly)
        self.assertAlmostEqual(result['worst_month'].value, .01)
        self.assertEqual(result['sharpe'].reason, 'MISSING_RISK_FREE')
        self.assertEqual(result['sortino'].reason, 'MISSING_RISK_FREE')
        result = m.monthly_risk_metrics([m.MonthlyReturn(a, b, .01), m.MonthlyReturn(b, c, .01)],
                                        risk_free_monthly=[m.MonthlyReturn(a, b, 0), m.MonthlyReturn(b, c, 0)])
        self.assertEqual(result['sharpe'].reason, 'ZERO_DENOMINATOR')
        self.assertEqual(result['sortino'].reason, 'ZERO_DENOMINATOR')

    def test_monthly_alignment_and_missing_returns_not_silently_dropped(self):
        a, b, c = date(2020, 1, 31), date(2020, 2, 29), date(2020, 3, 31)
        monthly = [m.MonthlyReturn(a, b, .02), m.MonthlyReturn(b, c, None)]
        self.assertEqual(m.monthly_risk_metrics(monthly)['worst_month'].reason,
                         'INCOMPLETE_MONTHLY_RETURNS')
        monthly = [m.MonthlyReturn(a, b, .02), m.MonthlyReturn(b, c, -.01)]
        rf = [m.MonthlyReturn(b, c, .001), m.MonthlyReturn(a, b, .001)]
        self.assertEqual(m.monthly_risk_metrics(monthly, risk_free_monthly=rf)['sharpe'].reason,
                         'RISK_FREE_ALIGNMENT_MISMATCH')

    def test_bootstrap_paired_indices_keep_identical_nonconstant_paths_equal(self):
        series = [m.MonthlyReturn(date(2000, 1, 1) + timedelta(days=i * 30),
                                  date(2000, 1, 1) + timedelta(days=(i + 1) * 30),
                                  [.2, -.1, .03, -.04, .01][i % 5]) for i in range(60)]
        result = m.paired_monthly_bootstrap({'W0': series, 'W1': series, 'SPY': series}, replications=200)
        for name in ['W1', 'SPY']:
            self.assertEqual(result['comparisons'][name]['lower_bound'].value, 0)
            self.assertEqual(result['comparisons'][name]['observed_difference'].value, 0)
        self.assertEqual(result, m.paired_monthly_bootstrap({'W0': series, 'W1': series, 'SPY': series},
                                                         replications=200))

    def test_bootstrap_partial_window_return_and_duration_travel_together(self):
        base = date(2000, 1, 1)
        baseline = [m.MonthlyReturn(base, base + timedelta(days=15), 0, full_month=False)]
        candidate = [m.MonthlyReturn(base, base + timedelta(days=15), .1, full_month=False)]
        for i in range(60):
            a = base + timedelta(days=15 + i * 30)
            baseline.append(m.MonthlyReturn(a, a + timedelta(days=30), 0))
            candidate.append(m.MonthlyReturn(a, a + timedelta(days=30), 0))
        result = m.paired_monthly_bootstrap({'W0': baseline, 'W1': candidate},
                                          block_months=61, replications=20)
        want = 1.1 ** (365.25 / 1815) - 1
        self.assertAlmostEqual(result['comparisons']['W1']['observed_difference'].value, want)
        self.assertAlmostEqual(result['comparisons']['W1']['lower_bound'].value, want)
        self.assertEqual(result['full_months'], 60)

    def test_bootstrap_short_sample_and_alignment_fail_closed(self):
        a, b = date(2020, 1, 1), date(2020, 2, 1)
        result = m.paired_monthly_bootstrap({'W0': [m.MonthlyReturn(a, b, .01)],
                                            'W1': [m.MonthlyReturn(a, b, .02)]})
        self.assertEqual(result['comparisons']['W1']['lower_bound'].reason, 'INSUFFICIENT_MONTHS')
        with self.assertRaises(ValueError):
            m.paired_monthly_bootstrap({'W0': [m.MonthlyReturn(a, b, .01)],
                                       'W1': [m.MonthlyReturn(a, date(2020, 2, 2), .02)]})

    def test_primary_decision_enforces_scope_and_observed_risk_constraints(self):
        kwargs = dict(panel='COMMON', n=15, rebalance='QUARTERLY', cost_bps=10)
        result = m.primary_decision(.012, .002, .03, .1, **kwargs)
        self.assertTrue(result['superiority_candidate'])
        self.assertTrue(result['noninferiority_candidate'])
        self.assertFalse(m.primary_decision(.012, .002, .031, .1, **kwargs)['noninferiority_candidate'])
        self.assertFalse(m.primary_decision(.0, -.01, 0, 0, **kwargs)['noninferiority_candidate'])
        kwargs['panel'] = 'PRACTICAL'
        self.assertEqual(m.primary_decision(.1, .1, 0, 0, **kwargs)['status'], 'NOT_PRIMARY_COMPARISON')
        kwargs['panel'] = 'COMMON'
        self.assertEqual(m.primary_decision(.1, .1, 0, None, **kwargs)['status'], 'INSUFFICIENT_EVIDENCE')

    def test_exposures_rank_changes_turnover_and_fixed_trade_attribution(self):
        exposure = m.exposure_metrics({'A': .4, 'B': .3}, {'A': 'TECH', 'B': 'TECH'})
        self.assertAlmostEqual(exposure['cash_weight'], .3)
        self.assertAlmostEqual(exposure['security_hhi'], .25)
        self.assertAlmostEqual(exposure['sector_weights']['TECH'], .7)
        change = m.selection_changes(['A', 'B', 'C'], ['C', 'A', 'D'])
        self.assertEqual(change['jaccard'], .5)
        self.assertEqual(change['rank_changes'], {'A': -1, 'C': 2})
        trades = [dict(date=date(2020, 1, 1), side='BUY', notional=50, cost=1),
                  dict(date=date(2020, 1, 2), side='SELL', notional=30, cost=.5)]
        nav = [m.NavPoint(date(2020, 1, 1), 100), m.NavPoint(date(2020, 1, 2), 100)]
        self.assertEqual(m.annual_turnover(trades, nav)[2020].value, .8)
        gross = [m.NavPoint(date(2020, 1, 1), 100), m.NavPoint(date(2020, 1, 2), 105)]
        costs = m.fixed_trade_cost_attribution(trades, gross)
        self.assertEqual(costs['total_cost'], 1.5)
        self.assertEqual(costs['gross_final_nav'], 105)
        self.assertEqual(costs['cost_subtracted_final_nav'], 103.5)
        self.assertEqual(costs['method'], 'FIXED_TRADE_COST_ATTRIBUTION')

    def test_contributions_include_cash_costs_and_reconcile_with_net_profit(self):
        contribution = m.return_contributions({'A': 10, 'B': -4}, 100,
                                              cash_income=2, costs=1)
        self.assertEqual(contribution['security_contributions'], {'A': .1, 'B': -.04})
        self.assertEqual(contribution['cash_contribution'], .02)
        self.assertEqual(contribution['cost_contribution'], -.01)
        self.assertEqual(contribution['total_return'], .07)
        with self.assertRaises(ValueError):
            m.return_contributions({'A': 10}, 0)

    def test_ruin_nav_retains_complete_loss_and_zero_base_is_not_a_zero_daily_return(self):
        points = [m.NavPoint(date(2020, 1, 1), 100),
                  m.NavPoint(date(2020, 1, 2), 0),
                  m.NavPoint(date(2020, 1, 3), 0)]
        result = m.performance_metrics(points)
        self.assertEqual(result['cagr'].value, -1)
        self.assertEqual(result['max_drawdown'].value, -1)
        self.assertEqual(result['annualized_volatility'].reason, 'ZERO_NAV_BASE')

    def test_explicit_entry_capital_keeps_initial_cost_in_daily_returns_and_drawdown(self):
        result = m.performance_metrics([
            m.NavPoint(date(2020, 1, 1), 99), m.NavPoint(date(2020, 1, 2), 100)],
            initial_capital=100, started_at=date(2020, 1, 1))
        self.assertEqual(result['cumulative_return'].value, 0)
        self.assertEqual(result['cagr'].value, 0)
        self.assertAlmostEqual(result['max_drawdown'].value, -.01)
        # The entry-day loss is a real return, followed by 1/99 recovery.
        self.assertAlmostEqual(result['annualized_volatility'].value,
                               (.01 + 1 / 99) / math.sqrt(2) * math.sqrt(252))
        self.assertEqual(result['max_drawdown_recovery_sessions'], 1)
        self.assertEqual(result['annual_returns'][2020], 0)

    def test_bootstrap_default_replications_recompute_positive_cagr_difference(self):
        base = date(2000, 1, 1)
        baseline = [m.MonthlyReturn(base + timedelta(days=i * 30),
                                   base + timedelta(days=(i + 1) * 30), 0) for i in range(60)]
        candidate = [m.MonthlyReturn(point.start, point.end, .01) for point in baseline]
        result = m.paired_monthly_bootstrap({'W0': baseline, 'W1': candidate})
        self.assertEqual(result['replications'], 10000)
        self.assertAlmostEqual(result['comparisons']['W1']['observed_difference'].value,
                               1.01 ** (365.25 / 30) - 1)
        self.assertAlmostEqual(result['comparisons']['W1']['lower_bound'].value,
                               1.01 ** (365.25 / 30) - 1)


if __name__ == '__main__':
    unittest.main()
