"""Synthetic scoring regressions with independent arithmetic and pool denominators."""
import copy
import unittest

from investment_system.qgv import qgv_v2, v2_factors, v2_scoring
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
from investment_system.qgv.type_config import load_official_type_config
from investment_system.research.qgv_backtest import scoring_adapter as score


def companies():
    result = {}
    for i in range(11):
        result[f'SYN{i:02}'] = {'cik': str(i + 1).zfill(10), 'security_id': f'SYN{i:02}',
            'industry_group': 'synthetic', 'profile': 'GENERAL',
            'factors': {k: i * 10 for k in qgv_v2.QG_FACTORS},
            'v_inputs': {'currency': 'USD', 'ebit': 10 + i, 'fcf': 8 + i, 'total_debt': 0,
                         'cash': 0, 'diluted_shares': 10, 'revenue_cagr_3y': 0.05},
            'memberships': {'growth': 1.0}}
    return result


def metric_rows():
    rows, quotes = {}, {}
    for i in range(11):
        key = f'SYN{i:02}'
        metrics = {metric: direction * i for spec in v2_scoring.SUBMETRICS['GENERAL'].values()
                   for metric, direction in spec}
        metrics['revenue_cagr_3y'] = i / 100
        rows[key] = {'cik': str(i + 1).zfill(10), 'security_id': key, 'state': 'LIVE',
            'profile': 'GENERAL', 'sic': '3571', 'industry_group': 'synthetic',
            'fiscal_year_end': '2015-12-31', 'currency': 'USD', 'metrics': metrics,
            'calc_version': v2_factors.CALC_VERSION,
            'provenance': {'signal_day': '2016-02-12', 'shares_basis': {'accn': f'SYN{i}', 'period_end': '2015-12-31'}},
            'v_inputs_v2': {'currency': 'USD', 'ebit': {'fy_value': 10 + i, 'fy_end': '2015-12-31'},
                            'fcf': {'fy_value': 8 + i, 'fy_end': '2015-12-31'},
                            'total_debt': {'value': 0, 'period_end': '2015-12-31'},
                            'cash_and_equivalents': {'value': 0, 'period_end': '2015-12-31'},
                            'diluted_shares': {'value': 10, 'period_end': '2015-12-31'}, 'revenue_cagr_3y': 0.05}}
        quotes[key] = {'price': 10, 'currency': 'USD', 'basis_alignment': {
            'status': 'VERIFIED', 'source': 'SYNTHETIC', 'signal_day': '2016-02-12',
            'verified_through': '2016-02-12', 'shares_period_end': '2015-12-31',
            'shares_filing_accn': f'SYN{i}', 'price_to_shares_factor': 1, 'split_events': []}}
    return rows, quotes


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.cfg = load_official_type_config().to_dict()
        self.params = load_default_dcf_parameters()

    def run_scores(self, rows=None, **kwargs):
        rows = companies() if rows is None else rows
        return score.score_variants(rows, {k: {'price': 10, 'currency': 'USD'} for k in rows},
                                    type_config=self.cfg, parameters=self.params, **kwargs)

    def test_growth_type_equal_axis_and_official_false_flag_trap(self):
        res = self.run_scores(include_diagnostics=True)
        for variant in ['W1', 'W3']:
            row = res['scores'][variant]['SYN08']
            for weight in row['weights'].values():
                self.assertAlmostEqual(weight, 100 / 3)
            self.assertAlmostEqual(row['total'], sum(a['score'] for a in row['axes'].values()) / 3)
        self.assertEqual(res['scores']['W0']['SYN08']['weights'], {'Q': 30.0, 'G': 50.0, 'V': 20.0})
        self.assertEqual(res['scores']['D0']['SYN08']['weights'], {'Q': 34.0, 'G': 33.0, 'V': 33.0})

    def test_g_first_two_official_50_equal40_and_common_before_gate(self):
        rows = companies()
        for f in list(qgv_v2.WEIGHTS['G'])[2:]:
            rows['SYN05']['factors'][f] = None
        res = self.run_scores(rows)
        self.assertEqual(res['scores']['W0']['SYN05']['axes']['G']['score'], 50)
        self.assertIsNone(res['scores']['W2']['SYN05']['axes']['G']['score'])
        self.assertNotIn('SYN05', res['common_ids'])
        self.assertIn('SYN05', res['panels']['PRACTICAL']['W0'])
        self.assertIn('SYN00', res['common_ids'])  # V exists before the gate, although excluded from total
        self.assertTrue(res['scores']['W0']['SYN00']['value_trap_gate'])

    def test_common_selection_keeps_full_pool_percentiles(self):
        rows = companies()
        rows['SYN00']['v_inputs'] = None
        res = self.run_scores(rows)
        self.assertNotIn('SYN00', res['common_ids'])
        # SYN03 has three lower Q values in eleven-company pool => 30, not 2/9*100 after filtering.
        self.assertEqual(res['scores']['W1']['SYN03']['q_industry_percentile'], 30)
        self.assertTrue(res['scores']['W1']['SYN03']['value_trap_gate'])
        self.assertEqual(res['summary']['percentile_population_size'], 11)

    def test_inner_q_change_recalculates_gate(self):
        rows = companies()
        # Official Q: .25*0+.20*0+.20*0+.20*100+.15*100=35;
        # Equal Q = 40. Place peers to make this cross the 30th percentile boundary.
        rows['SYN00']['factors'].update(dict(zip(qgv_v2.WEIGHTS['Q'], [0, 0, 0, 100, 100])))
        for i in range(1, 11):
            for factor in qgv_v2.WEIGHTS['Q']:
                rows[f'SYN{i:02}']['factors'][factor] = 29 + i * 2
        res = self.run_scores(rows)
        self.assertEqual(res['scores']['W0']['SYN00']['axes']['Q']['score'], 35)
        self.assertEqual(res['scores']['W2']['SYN00']['axes']['Q']['score'], 40)
        self.assertTrue(res['scores']['W0']['SYN00']['value_trap_gate'])
        self.assertFalse(res['scores']['W2']['SYN00']['value_trap_gate'])

    def test_cyclical_normalization_retained_when_types_off(self):
        rows = companies()
        rows['SYN08']['cyclical_basis'] = True
        rows['SYN08']['v_inputs'].update(revenue=100, operating_margin_history=[
            {'period_end': f'{2010+i}-12-31', 'value': 0.1} for i in range(5)])
        res = self.run_scores(rows)
        for variant in ['W0', 'W1', 'W2', 'W3']:
            row = res['scores'][variant]['SYN08']
            self.assertEqual(row['detail']['earnings_basis'], 'NORMALIZED')
            self.assertEqual(row['detail']['ebit_yield'], 0.1)

    def test_select_ties_issuer_dedup_and_permanent_id(self):
        identities = {'B': {'cik': '2', 'security_id': 'B'}, 'A': {'cik': '1', 'security_id': 'A'},
                      'A2': {'cik': '1', 'security_id': 'A2'}, 'NA': {'cik': '3', 'security_id': 'NA'}}
        result = score.select_top({'B': {'total': 75}, 'A2': {'total': 75}, 'A': {'total': 75},
                                   'NA': {'total': None}}, identities, 5)
        self.assertEqual([r['security_id'] for r in result], ['A', 'B'])
        self.assertEqual(score.select_top({'A': {'total': 75}}, identities, 2, eligible_ids=[]), ())

    def test_w0_exact_operational_path_and_no_input_mutation(self):
        rows = companies()
        original = copy.deepcopy(rows)
        res = self.run_scores(rows)
        official = qgv_v2.score_universe(rows, {k: {'price': 10, 'currency': 'USD'} for k in rows},
                                        type_config=self.cfg, parameters=self.params, preset='balanced', gate=True)
        self.assertEqual(res['scores']['W0'], official)
        self.assertEqual(rows, original)

    def test_metric_pipeline_independent_percentiles_and_unknown_basis_na(self):
        rows, quotes = metric_rows()
        original = copy.deepcopy(rows)
        res = score.score_variants(rows, quotes)
        self.assertEqual(res['scores']['W0']['SYN04']['axes']['Q']['score'], 40)
        self.assertEqual(res['scores']['W0']['SYN04']['axes']['G']['score'], 40)
        self.assertIsNotNone(res['scores']['W0']['SYN04']['axes']['V']['score'])
        self.assertEqual(rows, original)
        quotes['SYN04']['basis_alignment']['shares_period_end'] = '2014-12-31'
        res = score.score_variants(rows, quotes)
        self.assertIsNone(res['scores']['W0']['SYN04']['axes']['V']['score'])
        self.assertNotIn('SYN04', res['common_ids'])
        quotes['SYN04']['basis_alignment']['shares_period_end'] = '2015-12-31'
        quotes['SYN04']['basis_alignment']['shares_filing_accn'] = 'OTHER_FILING'
        res = score.score_variants(rows, quotes)
        self.assertIsNone(res['scores']['W0']['SYN04']['axes']['V']['score'])

    def test_metric_percentile_pool_is_not_rebuilt_for_common(self):
        rows, quotes = metric_rows()
        del quotes['SYN00']
        res = score.score_variants(rows, quotes)
        self.assertEqual(res['scores']['W1']['SYN03']['axes']['Q']['score'], 30)
        self.assertEqual(res['scores']['W1']['SYN03']['q_industry_percentile'], 30)
        self.assertNotIn('SYN00', res['common_ids'])
        self.assertEqual(res['summary']['percentile_population_size'], 11)


if __name__ == '__main__':
    unittest.main()
