"""Public V price-inference review tool (tools/qgv_inference_review.py): synthetic only, engine-faithful attacker."""
import math
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qgv_inference_review as t  # noqa: E402

N = 120


class InferenceReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.companies, cls.quotes, cls.sec = t.synthetic_universe(t.SEED, N)
        cls.rv = t.Review(cls.companies, cls.quotes, cls.sec)
        cls.iv = cls.rv.knowledge(cls.rv.ids)
        cls.ov = cls.rv.value_intervals(cls.iv)
        cls.pol = {p['name']: p for p in t.POLICIES}

    def test_synthetic_only(self):
        self.assertTrue(all(re.fullmatch(r'NYSE:SYN\d{3}', c) for c in self.companies))
        src = (ROOT / 'tools/qgv_inference_review.py').read_text(encoding='utf-8')
        self.assertNotRegex(src, r'\bimport (urllib|requests|socket|http)\b|from (urllib|requests|socket|http)')

    def test_model_reproduces_engine_at_the_true_price(self):
        for i in self.rv.targets:
            P = self.quotes[i]['price']
            seg = [s for s in self.rv.model(i, self.ov) if s[0] <= P <= s[1]][0]
            r = self.rv.results[i]
            self.assertEqual(seg[2], tuple(r['factors'][f]['reason'] if r['factors'][f]['score'] is None else None for f in t.V_IDS), i)
            for f in t.V_IDS:
                sc, rg = r['factors'][f]['score'], seg[3][f]
                self.assertEqual(sc is None, rg is None, (i, f))
                if sc is not None:
                    self.assertAlmostEqual(rg[0], sc, places=9)
                    self.assertAlmostEqual(rg[1], sc, places=9)

    def test_truth_always_inside_the_inferred_interval(self):
        for pol in t.POLICIES:
            for i in self.rv.targets:
                self.assertTrue(self.rv.interval(i, self.iv, pol, ovals=self.ov)['contains_truth'], (pol['name'], i))
        for name in ('A_design_full', 'K_axis_quintile_only'):
            for frac in (0.0, 0.5):
                _, misses = t.propagate(self.rv, self.pol[name], frac, 2)
                self.assertEqual(misses, 0, (name, frac))

    def test_full_precision_design_pins_the_price_and_quintile_axis_does_not(self):
        v = [i for i in self.rv.targets if self.rv.results[i]['axes']['V']['score'] is not None]
        per, misses = t._strong(self.rv, v, [self.pol['A_design_full'], self.pol['K_axis_quintile_only']])
        self.assertEqual(misses, 0)
        a, k = t.summarize(per['A_design_full']), t.summarize(per['K_axis_quintile_only'])
        self.assertLess(a['median'], 0.05)
        self.assertGreater(k['median'], 10 * a['median'])

    def test_grouped_reason_code_hides_nothing(self):
        rows = t.scenario_reasons(self.rv)
        for r in rows:
            for a in ('strong', 'zero'):
                self.assertEqual((r[a + '_raw']['lo'], r[a + '_raw']['hi']), (r[a + '_grouped']['lo'], r[a + '_grouped']['hi']))
                self.assertEqual((r[a + '_raw']['lo'], r[a + '_raw']['hi']), (r[a + '_state_only']['lo'], r[a + '_state_only']['hi']))

    def test_hidden_factor_and_hidden_axis_are_backed_out_exactly(self):
        b = t.scenario_backout(self.rv)
        self.assertGreater(b['hidden_factor_cases'], 0)
        self.assertGreater(b['axis_from_total_cases'], 0)
        self.assertLess(b['hidden_factor_max_abs_error'], 1e-9)
        self.assertLess(b['axis_from_total_max_abs_error'], 1e-9)

    def test_transforms(self):
        self.assertEqual(t.tf_apply(t.QUINT, 100.0), 4)
        self.assertEqual(t.tf_apply(t.QUINT, 19.999), 0)
        self.assertTrue(t.tf_match(t.QUINT, 1, 10.0, 25.0))
        self.assertFalse(t.tf_match(t.QUINT, 2, 10.0, 25.0))
        self.assertTrue(t.tf_match(t.R0, 13.0, 12.6, 12.6))
        self.assertTrue(t.tf_match(None, 5, None, None))
        self.assertFalse(t.tf_match(t.FULL, None, 1.0, 1.0))

    def test_a_dividend_type_factor_would_return_the_close_exactly(self):
        self.assertAlmostEqual(t.dividend_factor_leak(0.5, 1 - 0.5 / 41.0), 41.0, places=9)


if __name__ == '__main__':
    unittest.main()
