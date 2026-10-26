"""Synthetic report checks at the private artifact boundary."""
from datetime import date, timedelta
import json
from pathlib import Path
import unittest
from xml.etree import ElementTree

from investment_system.research.qgv_backtest import reporting as r


SPEC = Path(__file__).resolve().parents[2] / 'docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json'


def run(strategy, *, cagr=.1, mdd=-.2, sharpe=1, panel='COMMON', period='TARGET_QGV_V2'):
    return dict(cell=dict(period_id=period, strategy_id=strategy, panel=panel, cost_bps=10),
                status='COMPLETE', blockers=[], monthly=[], benchmark=[], risk_free=[],
                nav=[dict(session='2020-01-01', nav='100', status='COMPLETE'),
                     dict(session='2020-01-02', nav='110', status='COMPLETE'),
                     dict(session='2020-01-03', nav='99', status='COMPLETE')],
                metrics={name: dict(value=value, reason=None) for name, value in
                         [('cagr', cagr), ('max_drawdown', mdd), ('sharpe', sharpe),
                          ('sortino', 1.2), ('annualized_volatility', .15)]},
                decisions=[dict(signal_day='2020-01-01', selected=['A', 'B'])],
                fills=[dict(session='2020-01-02', gross='20', fee='.02', quantity='1')])


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(SPEC.read_text())

    def test_status_matrix_preserves_all_registered_periods_and_missing_runs(self):
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=[run('W0-N15-Q')]))
        self.assertEqual(len(report['strategy_period_status']), 90)
        missing = next(row for row in report['strategy_period_status']
                       if row['strategy_id'] == 'W3-N50-Y' and row['period_id'] == 'TARGET_QGV_V2')
        self.assertEqual(missing['status'], 'NOT_RUN')
        self.assertEqual(report['status'], 'REPORT_PARTIAL')
        self.assertEqual(report['runs'][0]['metrics']['cagr']['value'], .1)
        self.assertEqual(report['runs'][0]['metrics']['sharpe']['reason'], 'MISSING_MONTHLY_RETURNS')
        self.assertAlmostEqual(report['runs'][0]['annual_turnover'][2020]['value'], 20 / 103)

    def test_primary_bootstrap_and_missing_rf_prevent_unverified_decision(self):
        baseline, candidate = run('W0-N15-Q'), run('W1-N15-Q', cagr=.12)
        start = date(2000, 1, 1)
        for i in range(60):
            a, b = start + timedelta(days=30 * i), start + timedelta(days=30 * (i + 1))
            for row, value in [(baseline, 0), (candidate, .01)]:
                row['monthly'].append(dict(start=str(a), end=str(b), value=value, full_month=True))
                row['benchmark'].append(dict(start=str(a), end=str(b), value=0, full_month=True))
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=[baseline, candidate]))
        comparison = next(row for row in report['primary_comparisons'] if row['candidate'] == 'W1')
        self.assertAlmostEqual(comparison['lower_bound']['value'], 1.01 ** (365.25 / 30) - 1)
        self.assertEqual(comparison['decision']['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(comparison['missing_inputs'], ['MISSING_RISK_FREE'])
        missing = next(row for row in report['primary_comparisons'] if row['candidate'] == 'W3')
        self.assertEqual(missing['lower_bound']['reason'], 'MISSING_STRATEGY_RUN')

    def test_registered_effects_and_q_y_deltas_do_not_choose_winners(self):
        runs = [run('W0-N15-Q', cagr=.1), run('D0-N15-Q', cagr=.09),
                run('W2-N15-Q', cagr=.12), run('D2-N15-Q', cagr=.08),
                run('W0-N25-Q', cagr=.13), run('W0-N25-Y', cagr=.11)]
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=runs))
        effect = next(row for row in report['diagnostic_effects'] if row['comparison'] == 'D0-W0')
        self.assertAlmostEqual(effect['cagr_difference']['value'], -.01)
        inner = next(row for row in report['diagnostic_effects'] if row['comparison'] == 'D2-D0')
        self.assertAlmostEqual(inner['cagr_difference']['value'], -.01)
        delta = next(row for row in report['frequency_deltas'] if row['variant'] == 'W0' and row['n'] == 25)
        self.assertAlmostEqual(delta['cagr_difference']['value'], .02)
        self.assertEqual(delta['orientation'], 'QUARTERLY_MINUS_ANNUAL')

    def test_selection_overlap_and_fixed_regime_return_use_correct_nav_anchor(self):
        baseline, candidate = run('W0-N15-Q'), run('W1-N15-Q')
        candidate['decisions'][0]['selected'] = ['B', 'C']
        self.spec['period']['regime_windows'] = [dict(label='FIXED', start='2020-01-02', end='2020-01-03')]
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=[baseline, candidate]))
        overlap = next(row for row in report['selection_overlap'] if row['comparison'] == 'W1-W0')
        self.assertAlmostEqual(overlap['jaccard'], 1 / 3)
        regime = report['runs'][0]['regime_summaries'][0]
        # Prior close100 ->110 ->99: the fixed window loses1%, not10%.
        self.assertAlmostEqual(regime['metrics']['cumulative_return']['value'], -.01)
        self.assertAlmostEqual(regime['metrics']['max_drawdown']['value'], -.1)
        self.assertEqual(regime['observed_start'], '2020-01-01')

    def test_missing_nav_is_explicit_and_svg_breaks_paths_without_leaking_xml(self):
        sample = run('W0-N15-Q')
        sample['cell']['strategy_id'] = 'W0-N15-Q<script>'
        sample['nav'][1]['nav'] = None
        sample['status'] = 'INCOMPLETE_NAV'
        detailed = dict(period_id='TARGET_QGV_V2', runs=[sample])
        report = r.build_report(self.spec, detailed)
        self.assertEqual(report['runs'][0]['metrics']['cagr']['reason'], 'INCOMPLETE_NAV')
        svg = r.render_svg(detailed)
        ElementTree.fromstring(svg)
        self.assertNotIn('<script>', svg)
        self.assertIn('&lt;script&gt;', svg)
        self.assertIn('INCOMPLETE_NAV', svg)
        self.assertIn('NA (INCOMPLETE_NAV)', r.render_markdown(report))

    def test_invalid_monthly_inputs_remain_explicit_and_cell_inherits_period(self):
        baseline, candidate = run('W0-N15-Q'), run('W1-N15-Q')
        baseline['cell'].pop('period_id')
        for row in (baseline, candidate):
            row['monthly'] = [dict(start='invalid-date', end='2020-01-31', value=.01)]
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=[baseline, candidate]))
        comparison = next(row for row in report['primary_comparisons'] if row['candidate'] == 'W1')
        self.assertEqual(comparison['lower_bound']['reason'], 'MONTHLY_ALIGNMENT_OR_INPUT_INVALID')
        self.assertEqual(report['runs'][0]['cell']['period_id'], 'TARGET_QGV_V2')

    def test_svg_includes_paired_benchmark_when_daily_reference_is_provided(self):
        sample = run('W0-N15-Q')
        sample['benchmark_nav'] = [dict(session='2020-01-01', nav=100), dict(session='2020-01-03', nav=102)]
        svg = r.render_svg(dict(runs=[sample]))
        self.assertIn('BENCHMARK', svg)
        self.assertNotIn('SPY', svg)
        ElementTree.fromstring(svg)

    def test_formal_long_period_labels_index_in_report_and_svg(self):
        sample = run('W0-N15-Q')
        sample['benchmark_nav'] = [dict(session='2020-01-01', nav=100), dict(session='2020-01-03', nav=102)]
        detailed = dict(period_id='TARGET_QGV_V2', benchmark_label='SP500_TR_INDEX', runs=[sample])
        report = r.build_report(self.spec, detailed)
        self.assertEqual(report['benchmark_label'], 'SP500_TR_INDEX')
        self.assertEqual(report['primary_comparisons'][0]['benchmark_label'], 'SP500_TR_INDEX')
        self.assertNotIn('SPY', r.render_svg(detailed))
        self.assertIn('SP500_TR_INDEX', r.render_svg(detailed))

    def test_registered_period_fallback_distinguishes_index_from_spy(self):
        for period, label in [('TARGET_QGV_V2', 'SP500_TR_INDEX'),
                              ('SECONDARY_DIAGNOSTIC_NOT_TARGET', 'SPY_TR'),
                              ('DATA_LIMITED_DIAGNOSTIC_NOT_TARGET', 'SPY_TR')]:
            detailed = dict(period_id=period, runs=[run('W0-N15-Q', period=period)])
            report = r.build_report(self.spec, detailed)
            self.assertEqual(report['benchmark_label'], label)
            self.assertEqual(report['primary_comparisons'][0]['benchmark_label'], label)

    def test_turnover_mean_excludes_pre_entry_audit_baseline(self):
        self.spec['period']['data_feasibility_ladder'][0]['start'] = '2020-01-02'
        report = r.build_report(self.spec, dict(period_id='TARGET_QGV_V2', runs=[run('W0-N15-Q')]))
        self.assertAlmostEqual(report['runs'][0]['annual_turnover'][2020]['value'], 20 / 104.5)


if __name__ == '__main__':
    unittest.main()
