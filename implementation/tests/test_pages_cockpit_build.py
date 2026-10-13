"""Privacy and provenance boundaries of the Pages-only export."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from investment_system.product.web_mvp import repository_bundle

TOOL = Path(__file__).resolve().parents[1] / 'tools/build_pages_cockpit.py'


def load_tool():
    spec = importlib.util.spec_from_file_location('pages_build', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PagesBuildTest(unittest.TestCase):
    def test_publication_withholds_price_derived_membership_and_order(self):
        original = repository_bundle()
        before = deepcopy(original)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            public = json.loads((out / 'data.json').read_text())
            self.assertEqual(public['companies'], [])
            self.assertIsNone(public['universe']['data'])
            self.assertEqual(public['universe']['state'], 'NOT_AVAILABLE')
            self.assertEqual(public, before)
        self.assertEqual(original, before)

    def test_only_web_assets_and_public_identity_catalog_are_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            self.assertEqual({p.name for p in out.iterdir()}, {'icon-192.png', 'sec-qg-factors.json', 'leaderboard-screen.js', 'virtual-trading-compare.js', 'device-valuation.js', 'sec-valuation-inputs.json', 'playbook-engine.js', 'sec-filing-windows.json', 'virtual-trading-runner.js', 'thirteenf-quarter.js', 'macro-screen.json', 'sec-reported.js', 'qgv-v2.js', 'technical-cards.js', 'public-screens.js', 'dart-disclosures.js', 'engine-preview.js', 'company-screen.js', 'entities.json', 'offline.html', 'private-subset.js', 'manager-styles-v0.js', 'profile-defaults.js', 'app-config.js', 'sec-m2-candidates.json', 'device-backup.js', 'virtual-trading-signals.js', 'qgv2-inputs.js', 'sec-qgv2.js', 'share-class-groups.js', 'universe-codes.json', 'virtual-trading.js', 'chart-indicators.js', 'table-sort.js', 'forward-validation.js', 'private-history.css', 'private-history.js', 'device-market.js', 'portfolio-screen.js', 'icon-512.png', 'index.html', 'holdings-capture-view.js', 'dcf-parameters-defaults.js', 'actual-catalog.json', 'virtual-trading-v-history.js', 'report-benchmarks.js', 'news-signals.js', 'entity-search.js', 'app.js', 'daily-report.js', 'google-sheet-quotes.js', 'dart-disclosures.json', 'virtual-ledger-sheets.js', 'company-types-pricefree.json', 'google-sheet-quotes.css', 'classification-screens.js', 'news-signals.json', 'device-profiles.js', 'manifest.json', 'sec-universe-shares.js', 'research.html', 'playbook-config-defaults.js', 'data.json', 'private-subset-view.js', 'sec-disclosures.js', 'technical-chart.js', 'private-trades.js', 'worker-quote-fallback.js', 'device-actual.css', 'qgv-scores.js', 'ops-status.js', 'style.css', 'google-sheet-setup.js', 'service-worker.js', 'sec-disclosures.json', 'google-sheet-core.js', 'price-store.js', 'sec-13f-changes.json', 'locale.js', 'pwa.js', 'sec-m3-adapter.js', 'screen-detail.js', 'device-actual.js', 'sec-universe-qg.js', 'company-classification.json', 'holdings-capture.js', 'scoring-default.js', 'type-config-defaults.js', 'pc-layout.css', 'dart-financials.json', 'watchlist.js'})
            catalog = json.loads((out / 'actual-catalog.json').read_text())
            self.assertEqual(len(catalog['instruments']), 19)
            self.assertTrue(all('quantity' not in r and 'average_cost' not in r
                                for r in catalog['instruments']))
            bundle = json.loads((out / 'data.json').read_text())
            for name in ['portfolio', 'qgv', 'technical', 'macro']:
                self.assertEqual(bundle[name]['state'], 'NOT_AVAILABLE')
                self.assertIsNone(bundle[name]['data'])

    def test_relative_assets_and_repository_scoped_pwa(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            html = (out / 'index.html').read_text()
            self.assertNotIn('src="/', html)
            self.assertNotIn('href="/', html)
            self.assertIn('rel="manifest" href="manifest.json"', html)
            js = '\n'.join(p.read_text() for p in out.glob('*.js'))
            self.assertIn("scope:'./'", js)
            self.assertNotIn("scope:'/'", js)

    def test_nonempty_output_fails_without_removing_existing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'; out.mkdir()
            marker = out / 'existing.txt'; marker.write_text('user-owned marker')
            with self.assertRaisesRegex(ValueError, '^Pages output must be an empty regular directory$'):
                load_tool().build_public_cockpit(out)
            self.assertEqual(marker.read_text(), 'user-owned marker')
            self.assertEqual(len(list(out.iterdir())), 1)

    def test_symlink_output_fails_without_writing_target(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'target'; target.mkdir()
            out = Path(folder) / 'site'; out.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, '^Pages output must be an empty regular directory$'):
                load_tool().build_public_cockpit(out)
            self.assertEqual(list(target.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
