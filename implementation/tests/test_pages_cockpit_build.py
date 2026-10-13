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
            self.assertEqual({p.name for p in out.iterdir()}, {'sec-universe-shares.js', 'company-classification.json', 'price-store.js', 'sec-13f-changes.json', 'public-screens.js', 'sec-filing-windows.json', 'virtual-trading-compare.js', 'google-sheet-quotes.css', 'forward-validation.js', 'google-sheet-core.js', 'service-worker.js', 'private-trades.js', 'virtual-trading.js', 'sec-universe-qg.js', 'device-backup.js', 'actual-catalog.json', 'sec-qgv2.js', 'report-benchmarks.js', 'sec-m3-adapter.js', 'ops-status.js', 'table-sort.js', 'entity-search.js', 'screen-detail.js', 'virtual-ledger-sheets.js', 'device-profiles.js', 'classification-screens.js', 'company-types-pricefree.json', 'device-actual.js', 'private-subset-view.js', 'profile-defaults.js', 'thirteenf-quarter.js', 'style.css', 'leaderboard-screen.js', 'virtual-trading-runner.js', 'pwa.js', 'device-market.js', 'chart-indicators.js', 'private-history.js', 'sec-valuation-inputs.json', 'dcf-parameters-defaults.js', 'device-valuation.js', 'sec-m2-candidates.json', 'private-history.css', 'google-sheet-setup.js', 'sec-reported.js', 'device-actual.css', 'holdings-capture.js', 'index.html', 'macro-screen.json', 'holdings-capture-view.js', 'data.json', 'icon-192.png', 'manifest.json', 'type-config-defaults.js', 'technical-cards.js', 'research.html', 'app.js', 'google-sheet-quotes.js', 'sec-qg-factors.json', 'manager-styles-v0.js', 'private-subset.js', 'app-config.js', 'virtual-trading-signals.js', 'technical-chart.js', 'locale.js', 'virtual-trading-v-history.js', 'engine-preview.js', 'share-class-groups.js', 'company-screen.js', 'daily-report.js', 'portfolio-screen.js', 'worker-quote-fallback.js', 'pc-layout.css', 'watchlist.js', 'offline.html', 'entities.json', 'universe-codes.json', 'icon-512.png'})
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
