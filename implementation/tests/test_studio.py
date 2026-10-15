"""Behavioral checks for the local, explicitly synthetic studio adapter."""
import math
import unittest

from investment_system.product.studio import studio_snapshot, simulate
from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS


class StudioTest(unittest.TestCase):
    def test_demo_preserves_target_and_uses_v2(self):
        data = studio_snapshot()
        self.assertEqual(data['state'], 'DEMO')
        self.assertEqual({r['company_id']: r['target_weight'] for r in data['companies']}, OFFICIAL_V11_TARGETS)
        self.assertTrue(all(r['qgv']['version'] == 'qgv-v2' for r in data['companies']))
        self.assertTrue(all(r['technical']['synthetic'] for r in data['companies']))
        self.assertTrue(data['macro']['synthetic'])
        self.assertEqual(next(r for r in data['companies'] if r['company_id'] == 'tokyo_electron')['exchange'], None)

    def test_presets_change_scores_without_changing_target(self):
        a, b = studio_snapshot(), studio_snapshot('value')
        self.assertNotEqual([r['qgv']['total'] for r in a['companies']], [r['qgv']['total'] for r in b['companies']])
        self.assertEqual([r['target_weight'] for r in a['companies']], [r['target_weight'] for r in b['companies']])

    def test_missing_axis_stays_missing(self):
        rows = studio_snapshot()['companies']
        self.assertIsNone(next(r for r in rows if r['company_id'] == 'intc')['qgv']['axes']['V']['score'])

    def test_price_chart_change_and_technical_share_the_same_input(self):
        for row in studio_snapshot()['companies']:
            history = row['price_history']
            self.assertEqual(history[-1], row['price'])
            self.assertEqual(row['daily_change'], round((history[-1] / history[-2] - 1) * 100, 2))

    def test_contributions_are_not_profit_and_both_series_receive_them(self):
        a = simulate({'capital': 10000000, 'monthly': 1000000, 'months': 12, 'cash': 0, 'scenario': 'base'})
        self.assertEqual(a['contributed'], 22000000)
        self.assertAlmostEqual(a['profit'], a['ending_value'] - a['contributed'])
        self.assertEqual(len(a['series']), 13)
        self.assertEqual(a['series'][0]['strategy'], 10000000)
        b = simulate({'capital': 10000000, 'monthly': 0, 'months': 12, 'cash': 0, 'scenario': 'base'})
        self.assertGreater(a['series'][-1]['benchmark'], b['series'][-1]['benchmark'] + 11000000)
        self.assertAlmostEqual(a['total_return'], b['total_return'])
        self.assertAlmostEqual(a['max_drawdown'], b['max_drawdown'])
        self.assertTrue(a['synthetic'])
        self.assertEqual(a['purpose'], 'PRODUCT_SIMULATION')

    def test_all_cash_has_no_market_return(self):
        r = simulate({'capital': 10000000, 'monthly': 100000, 'months': 12, 'cash': 100, 'scenario': 'recession'})
        self.assertEqual(r['ending_value'], 11200000)
        self.assertEqual(r['total_return'], 0)
        self.assertEqual(r['profit'], 0)

    def test_invalid_inputs_are_rejected(self):
        for patch in ({'capital': -1}, {'capital': math.nan}, {'capital': math.inf}, {'capital': True}, {'capital': 'abc'}, {'months': 1.5}, {'months': 121}, {'cash': 101}, {'monthly': -1}, {'scenario': 'unknown'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                simulate(patch)
        with self.assertRaises(ValueError):
            studio_snapshot('custom')
