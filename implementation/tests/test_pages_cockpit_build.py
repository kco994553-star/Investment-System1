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
            self.assertEqual({p.name for p in out.iterdir()}, {'style.css', 'report-benchmarks.js', 'profile-defaults.js', 'research.html', 'sec-13f-changes.json', 'watchlist.js', 'worker-quote-fallback.js', 'actual-catalog.json', 'virtual-trading-runner.js', 'private-subset.js', 'entity-search.js', 'private-history.js', 'device-market.js', 'screen-detail.js', 'company-logos.json', 'google-sheet-quotes.js', 'tradingview-widgets.js', 'virtual-trading-signals.js', 'device-valuation.js', 'portfolio-screen.js', 'manifest.json', 'pwa.js', 'sec-reported.js', 'virtual-trading-compare.js', 'device-actual.js', 'index.html', 'forward-validation.js', 'device-actual.css', 'dcf-parameters-defaults.js', 'chart-indicators.js', 'public-screens.js', 'data.json', 'google-sheet-core.js', 'icon-192.png', 'engine-preview.js', 'technical-chart.js', 'company-screen.js', 'company-logos.js', 'thirteenf-quarter.js', 'table-sort.js', 'leaderboard-screen.js', 'app-config.js', 'share-class-groups.js', 'device-profiles.js', 'virtual-trading.js', 'universe-domains.json', 'ops-status.js', 'private-subset-view.js', 'locale.js', 'virtual-trading-v-history.js', 'sec-m2-candidates.json', 'entities.json', 'company-types-pricefree.json', 'sec-qg-factors.json', 'sec-m3-adapter.js', 'manager-styles-v0.js', 'classification-screens.js', 'sec-universe-qg.js', 'virtual-ledger-sheets.js', 'device-backup.js', 'holdings-capture.js', 'offline.html', 'app.js', 'service-worker.js', 'macro-screen.json', 'private-history.css', 'technical-cards.js', 'type-config-defaults.js', 'sec-universe-shares.js', 'company-classification.json', 'icon-512.png', 'sec-filing-windows.json', 'sec-valuation-inputs.json', 'daily-report.js', 'google-sheet-setup.js', 'holdings-capture-view.js', 'google-sheet-quotes.css', 'pc-layout.css', 'universe-codes.json', 'private-trades.js'})
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
