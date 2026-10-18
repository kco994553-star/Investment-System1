"""QGV v2 PERSONAL_PREVIEW two-level weights (qgv_v2.score_universe(weights=...)): E1 official equality, E2 recompute
consistency on score_rows axes, E3 isolation of one inner-weight change, invalid trees, stable ids. Owner directive 2026-10-18 §4.2."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

from investment_system.qgv import qgv_v2 as m
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
from investment_system.qgv.type_config import load_official_type_config

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / 'tests/fixtures/qgv_v2_vectors_v1.json'
CUSTOM = ROOT / 'tests/fixtures/qgv_v2_custom_vectors_v1.json'


def ranked(results):
    """Device rank order: total desc, ties by code (ticker) asc; NA has no rank."""
    rows = [(r['total'], code) for code, r in results.items() if r['total'] is not None]
    return [code for _, code in sorted(rows, key=lambda x: (-x[0], x[1]))]


class QgvV2CustomWeightsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_official_type_config().to_dict()
        cls.params = load_default_dcf_parameters()
        cls.official = json.loads(OFFICIAL.read_text(encoding='utf-8'))
        cls.custom = json.loads(CUSTOM.read_text(encoding='utf-8'))

    def score(self, companies, market, **kw):
        return m.score_universe(copy.deepcopy(companies), copy.deepcopy(market), type_config=self.cfg, parameters=self.params, **kw)

    def companies(self, case):
        c = case['input']['companies']
        return self.custom['scored_universe'] if c == 'scored_universe' else c

    def test_fixture_is_fresh(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'tools/qgv_v2_custom_reference.py'), '--check'], capture_output=True, text=True, check=False)
        self.assertEqual(proc.stdout.strip(), 'FIXTURE_OK')

    def test_e1_official_tree_equals_the_preset_path_for_every_vector_case(self):
        for case in self.official['cases']:
            i = case['input']
            preset = i['preset']
            a = self.score(i['companies'], i['synthetic_market'], preset=preset, gate=i['gate'])
            b = self.score(i['companies'], i['synthetic_market'], gate=i['gate'], weights=m.official_weights(preset))
            self.assertEqual(json.loads(json.dumps(a)), case['expected'], case['id'])  # the official path is unchanged
            self.assertEqual(set(a), set(b))
            for code in a:
                pa, pb = a[code].pop('profile'), b[code].pop('profile')
                self.assertEqual(pa['id'], m.VERSION + '/' + preset + '/gate-' + ('on' if pa['gate'] else 'off'))
                self.assertNotIn('namespace', pa)
                self.assertEqual(pb['namespace'], 'PERSONAL_PREVIEW')
                self.assertTrue(pb['id'].startswith('qgv-v2/custom/'))
                self.assertNotEqual(pb['id'], pa['id'])
                self.assertEqual(pb['recomputed_axes'], [])
            self.assertEqual(a, b, case['id'])

    def test_e2_forced_recompute_at_official_weights_matches_published_axes(self):
        u = self.custom['scored_universe']
        market = next(c for c in self.custom['cases'] if c['id'] == 'scored-official-forced-recompute')['input']['synthetic_market']
        pub = self.score(u, market)
        rec = self.score(u, market, weights=m.official_weights('balanced'), recompute_published=True)
        self.assertEqual(rec[next(iter(rec))]['profile']['recomputed_axes'], ['Q', 'G'])
        worst = 0.0
        for code in pub:
            a, b = pub[code], rec[code]
            for axis in ('Q', 'G', 'V'):
                sa, sb = a['axes'][axis]['score'], b['axes'][axis]['score']
                self.assertEqual(sa is None, sb is None, (code, axis))
                if sa is not None:
                    worst = max(worst, abs(sa - sb))
            self.assertEqual(a['total'] is None, b['total'] is None, code)
            if a['total'] is not None:
                worst = max(worst, abs(a['total'] - b['total']))
            self.assertEqual(a['flags'], b['flags'], code)
            self.assertEqual(a['value_trap_gate'], b['value_trap_gate'], code)
            self.assertEqual(a['q_industry_percentile'] is None, b['q_industry_percentile'] is None, code)
        self.assertLessEqual(worst, 1e-9)
        self.assertEqual(ranked(pub), ranked(rec))
        self.assertGreater(len(ranked(pub)), 50)
        self.assertTrue(any(r['value_trap_gate'] for r in pub.values()))

    def test_e3_one_inner_weight_changes_only_affected_rows_and_never_the_official_result(self):
        u = self.custom['scored_universe']
        market = next(c for c in self.custom['cases'] if c['id'] == 'scored-q-profitability-40')['input']['synthetic_market']
        before = self.score(u, market)
        tree = m.official_weights('balanced')
        tree['inner']['Q']['q_profitability'] = 40
        mine = self.score(u, market, weights=tree)
        after = self.score(u, market)
        self.assertEqual(before, after)
        base = self.score(u, market, weights=m.official_weights('balanced'), recompute_published=True)
        changed = 0
        for code, r in mine.items():
            q_old, q_new = base[code]['axes']['Q'], r['axes']['Q']
            has = r['factors']['q_profitability']['score'] is not None
            self.assertEqual(r['axes']['G'], before[code]['axes']['G'])  # untouched axes are the very same values
            self.assertEqual(r['axes']['V'], before[code]['axes']['V'])
            self.assertTrue(r['axes']['Q']['recomputed'])
            if not has and (q_old['score'] is None) == (q_new['score'] is None):
                if q_new['score'] is not None:
                    self.assertLessEqual(abs(q_new['score'] - q_old['score']), 1e-9, code)
            elif has and q_new['score'] is not None and q_old['score'] is not None:
                changed += abs(q_new['score'] - q_old['score']) > 1e-9
            # The gate is re-evaluated from the recomputed Q percentile; V is dropped exactly when that percentile is <= 30.
            qp = r['q_industry_percentile']
            self.assertEqual(r['value_trap_gate'], qp is not None and qp <= m.GATE_PERCENTILE)
        self.assertGreater(changed, 20)
        self.assertEqual(r['profile']['recomputed_axes'], ['Q'])

    def test_zero_weight_is_excluded_not_missing_and_coverage_uses_custom_weights(self):
        w = {'q_profitability': 25, 'q_moat_proxy': 0, 'q_earnings_quality': 20, 'q_financial_safety': 20, 'q_capital_allocation': 15}
        scores = {'q_profitability': 80, 'q_moat_proxy': None, 'q_earnings_quality': 40, 'q_financial_safety': None, 'q_capital_allocation': None}
        out = m.axis_score(scores, 'Q', w)
        self.assertEqual(out['excluded'], ['q_moat_proxy'])
        self.assertEqual(out['missing'], ['q_financial_safety', 'q_capital_allocation'])
        self.assertEqual(out['factors_total'], 4)
        self.assertAlmostEqual(out['weight_available'], 45 / 80)  # 50% rule over the custom weights
        self.assertAlmostEqual(out['weight_available_official'], 0.45)  # fill rate against the official weights
        self.assertAlmostEqual(out['score'], (25 * 80 + 20 * 40) / 45)
        self.assertEqual(m.axis_score(scores, 'Q')['state'], 'NOT_AVAILABLE')  # official: 45% < 50%
        self.assertEqual(m.axis_score(scores, 'Q'), m.axis_score(copy.deepcopy(scores), 'Q', None))

    def test_custom_cases_and_units_reproduce(self):
        for u in self.custom['units']['axis']:
            self.assertEqual(json.loads(json.dumps(m.axis_score(u['scores'], u['axis'], u['weights']))), u['expected'])
        for u in self.custom['units']['weights_id']:
            self.assertEqual(m.weights_id(m.validate_weights(u['weights']), u['type_weights']), u['expected'])
        for case in self.custom['cases']:
            i = case['input']
            out = self.score(self.companies(case), i['synthetic_market'], gate=i['gate'], weights=i['weights'],
                             type_weights=i['type_weights'], recompute_published=i['recompute_published'])
            self.assertEqual(json.loads(json.dumps(out)), case['expected'], case['id'])

    def test_type_weights_toggle_and_axis_zero(self):
        case = next(c for c in self.custom['cases'] if c['id'] == 'recomputed-axis-no-v-types-off')
        for r in case['expected'].values():
            self.assertEqual(r['weights'], {'Q': 60.0, 'G': 40.0, 'V': 0.0})
            self.assertFalse(r['profile']['type_weights'])
            if r['total'] is not None and r['axes']['Q']['score'] is not None and r['axes']['G']['score'] is not None:
                self.assertAlmostEqual(r['total'], 0.6 * r['axes']['Q']['score'] + 0.4 * r['axes']['G']['score'])
        on = self.score(self.official['cases'][0]['input']['companies'], {}, weights=case['input']['weights'], type_weights=True)
        off = self.score(self.official['cases'][0]['input']['companies'], {}, weights=case['input']['weights'], type_weights=False)
        self.assertNotEqual(on['NASDAQ:SYNB1']['weights'], off['NASDAQ:SYNB1']['weights'])  # growth-typed row: type weights applied on top
        self.assertNotEqual(on['NASDAQ:SYNB1']['profile']['id'], off['NASDAQ:SYNB1']['profile']['id'])

    def test_invalid_trees_are_rejected(self):
        bad = [u['weights'] for u in self.custom['units']['invalid']]
        for value in (math.nan, math.inf, -math.inf):
            t = m.official_weights()
            t['inner']['G']['g_consistency'] = value
            bad.append(t)
        bad += ['balanced', {}, []]  # None = no personal weights (the official path)
        for t in bad:
            with self.assertRaises(ValueError, msg=repr(t)) as ctx:
                self.score({}, {}, weights=t)
            self.assertEqual(str(ctx.exception), 'WEIGHTS_INVALID')
        with self.assertRaises(ValueError):
            m.official_weights('tuned')
        self.assertEqual(m.validate_weights(m.official_weights('value')), m.official_weights('value'))
        t = m.official_weights()
        t['inner']['V']['v_fcf_yield'] = -0.0
        self.assertEqual(m.weights_id(m.validate_weights(t)), m.weights_id(m.validate_weights(dict(t, inner=dict(t['inner'], V=dict(t['inner']['V'], v_fcf_yield=0))))))


if __name__ == '__main__':
    unittest.main()
