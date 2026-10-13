"""QGV v2 PROVISIONAL device scoring reference (qgv/qgv_v2.py): doc weights, missing rules, gate, presets, RAM boundary."""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from investment_system.qgv import qgv_v2 as m
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
from investment_system.qgv.type_config import load_official_type_config

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/qgv_v2_vectors_v1.json'
DOC = ROOT / 'docs/qgv_scoring_standard/QGV_V2_CANDIDATE.md'
sys.path.insert(0, str(ROOT / 'tools'))
import qgv_v2_reference as ref  # noqa: E402


class QgvV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_official_type_config().to_dict()
        cls.params = load_default_dcf_parameters()
        cls.vectors = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def score(self, companies, market, **kw):
        return m.score_universe(copy.deepcopy(companies), copy.deepcopy(market), type_config=self.cfg, parameters=self.params, **kw)

    def test_fixture_is_fresh(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'tools/qgv_v2_reference.py'), '--check'], capture_output=True, text=True, check=False)
        self.assertEqual(proc.stdout.strip(), 'FIXTURE_OK')

    def test_default_weights_match_the_candidate_document_exactly(self):
        text = DOC.read_text(encoding='utf-8')
        names = {'Q': ['수익성', '해자 대리', '이익의 질', '재무 안전', '자본 배분(경영진 대리)'],
                 'G': ['매출 성장', '주당 이익·FCF 성장', '성장 효율', '성장 일관성', '최근 가속'],
                 'V': ['이익 수익률', 'FCF 수익률', '업종 대비', '자기 과거 대비', '기대 점검']}
        for axis, labels in names.items():
            for label, weight in zip(labels, m.WEIGHTS[axis].values()):
                self.assertRegex(text, r'\| ' + re.escape(label) + r' \| ' + str(weight) + r' \|')
            self.assertEqual(sum(m.WEIGHTS[axis].values()), 100)
        for preset, row in (('balanced', '균형 | 34/33/33'), ('quality', '우량 중심 | 50/25/25'), ('growth', '성장 친화 | 30/50/20'), ('value', '가치(관문 켬) | 25/20/55')):
            self.assertIn('| ' + row + ' |', text)
            w = m.PRESETS[preset]['weights']
            self.assertEqual('%d/%d/%d' % (w['Q'], w['G'], w['V']), row.split('| ')[1])
        self.assertIn('Q가 업종 내 하위 30%이면 V를 총점에 반영하지 않고', text)
        self.assertEqual((m.DEFAULT_PRESET, m.GATE_DEFAULT, m.GATE_PERCENTILE, m.MIN_AXIS_WEIGHT), ('balanced', True, 30, 0.5))

    def test_percentile_mid_rank(self):
        self.assertEqual(m.percentile(1.0, [1.0, 3.0, 5.0]), 0.0)
        self.assertEqual(m.percentile(5.0, [1.0, 3.0, 5.0]), 100.0)
        self.assertEqual(m.percentile(2.0, [2.0, 2.0, 2.0, 1.0]), 100.0 * (1 + 1.0) / 3)
        self.assertIsNone(m.percentile(7.0, [7.0]))

    def test_axis_renormalizes_and_half_weight_rule(self):
        a = m.axis_score({'q_profitability': 80, 'q_capital_allocation': 0, 'q_earnings_quality': 40}, 'Q')
        self.assertEqual(a['state'], 'PARTIAL')
        self.assertAlmostEqual(a['score'], (25 * 80 + 20 * 40 + 15 * 0) / 60)
        self.assertEqual((a['factors_available'], a['factors_total']), (3, 5))
        b = m.axis_score({'q_profitability': 80, 'q_capital_allocation': 0}, 'Q')
        self.assertIsNone(b['score'])
        self.assertEqual(b['reason'], 'AXIS_WEIGHT_INSUFFICIENT')
        self.assertEqual(m.axis_score({'q_profitability': 0, 'q_moat_proxy': 0, 'q_earnings_quality': 0}, 'Q')['score'], 0.0)

    def test_missing_v_is_never_zero_and_no_price_echo(self):
        u = ref.universe()
        mk = ref.market(u)
        res = self.score(u, {})
        for code, r in res.items():
            self.assertIsNone(r['axes']['V']['score'])
            self.assertIn('V_NOT_AVAILABLE', r['flags'])
            for k in m.WEIGHTS['V']:
                self.assertEqual((r['factors'][k]['score'], r['factors'][k]['state']), (None, 'NOT_AVAILABLE'))
                self.assertTrue(r['factors'][k]['reason'])
            if u[code]['profile'] == 'GENERAL' and u[code]['v_inputs'] is not None:
                self.assertEqual(r['factors']['v_earnings_yield']['reason'], 'NO_DEVICE_PRICE')
        text = json.dumps(self.score(u, mk))
        self.assertNotRegex(text, r'"(price|market_cap|marketcap|ev|closes)"')

    def test_financial_profile_v_is_not_available_with_reason(self):
        res = self.score(ref.universe(), ref.market(ref.universe()))
        fin = res['NYSE:SYNF1']
        self.assertEqual({fin['factors'][k]['reason'] for k in m.WEIGHTS['V']}, {'FINANCIAL_PROFILE_V_NOT_DEFINED'})
        self.assertIn('V_NOT_AVAILABLE', fin['flags'])
        self.assertIsNotNone(fin['total'])
        self.assertEqual(fin['reference_range']['reason'], 'FINANCIAL_PROFILE_V_NOT_DEFINED')

    def test_value_trap_gate(self):
        u, mk = ref.universe(), ref.market(ref.universe())
        on, off = self.score(u, mk), self.score(u, mk, gate=False)
        trapped = [c for c, r in on.items() if 'VALUE_TRAP_CAUTION' in r['flags']]
        self.assertTrue(trapped)
        for c in trapped:
            r = on[c]
            self.assertLess(r['q_industry_percentile'], 30)
            self.assertEqual(r['v_excluded'], 'VALUE_TRAP_GATE')
            w, a = r['weights'], r['axes']
            if a['V']['score'] is not None:
                self.assertAlmostEqual(r['total'], (w['Q'] * a['Q']['score'] + w['G'] * a['G']['score']) / (w['Q'] + w['G']))
                self.assertNotAlmostEqual(off[c]['total'], r['total'])
            self.assertEqual(r['profile']['id'], 'qgv-v2/balanced/gate-on')
        self.assertFalse(any('VALUE_TRAP_CAUTION' in r['flags'] for r in off.values()))

    def test_industry_basis_and_small_cross_section(self):
        u = ref.universe()
        res = self.score(u, ref.market(u))
        self.assertEqual(res['NYSE:SYNA1']['factors']['v_vs_industry']['basis'], 'INDUSTRY')
        self.assertEqual(res['NASDAQ:SYNB1']['factors']['v_vs_industry']['basis'], 'UNIVERSE_FALLBACK')
        small = dict(list(ref.market(u).items())[:5])
        res = self.score(u, small)
        priced = [c for c in small if res[c]['factors']['v_earnings_yield']['reason'] == 'CROSS_SECTION_TOO_SMALL']
        self.assertEqual(len(priced), 5)

    def test_type_weights_on_top_of_presets(self):
        fb = {'Q': 34.0, 'G': 33.0, 'V': 33.0}
        tw, reason, sel = m.type_axis_weights({'growth': 1.0}, self.cfg)
        self.assertEqual((reason, sel), (None, ['growth']))
        self.assertEqual({p: round(v, 9) for p, v in tw.items()}, {'Q': 30.0, 'G': 50.0, 'V': 20.0})
        bal = m.composite_weights(m.PRESETS['balanced']['weights'], tw, fb)
        self.assertEqual({p: round(v, 9) for p, v in bal.items()}, {'Q': 30.0, 'G': 50.0, 'V': 20.0})
        self.assertEqual(m.type_axis_weights(None, self.cfg)[1], 'TYPE_UNCONFIRMED')
        self.assertAlmostEqual(sum(m.composite_weights(m.PRESETS['value']['weights'], tw, fb).values()), 100.0)
        with self.assertRaisesRegex(ValueError, 'PRESET_INVALID'):
            m.score_universe({}, {}, type_config=self.cfg, parameters=self.params, preset='tuned')

    def test_reference_range_is_price_free_and_ordered(self):
        res = self.score(ref.universe(), {})
        r = res['NYSE:SYNA1']['reference_range']
        self.assertEqual(r['state'], 'PROVISIONAL')
        self.assertLess(r['low'], r['high'])
        self.assertEqual(res['NYSE:SYNX1']['reference_range']['reason'], 'NON_POSITIVE_CASHFLOW')


if __name__ == '__main__':
    unittest.main()
