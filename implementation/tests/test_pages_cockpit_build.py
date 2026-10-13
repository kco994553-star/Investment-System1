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
            self.assertEqual({p.name for p in out.iterdir()}, {'macro-screen.json', 'engine-preview.js', 'sec-universe-qg.js', 'locale.js', 'classification-screens.js', 'virtual-trading-runner.js', 'device-actual.css', 'index.html', 'device-backup.js', 'dcf-parameters-defaults.js', 'research.html', 'virtual-ledger-sheets.js', 'watchlist.js', 'sec-13f-changes.json', 'manifest.json', 'google-sheet-setup.js', 'table-sort.js', 'icon-512.png', 'app-config.js', 'device-actual.js', 'public-screens.js', 'google-sheet-core.js', 'sec-qgv2.js', 'tradingview-widgets.js', 'company-types-pricefree.json', 'sec-m3-adapter.js', 'company-logos.json', 'private-history.js', 'sec-qg-factors.json', 'virtual-trading-signals.js', 'virtual-trading-compare.js', 'sec-filing-windows.json', 'google-sheet-quotes.js', 'data.json', 'virtual-trading-v-history.js', 'company-screen.js', 'entity-search.js', 'thirteenf-quarter.js', 'ops-status.js', 'universe-codes.json', 'technical-chart.js', 'worker-quote-fallback.js', 'company-classification.json', 'device-valuation.js', 'device-market.js', 'type-config-defaults.js', 'daily-report.js', 'technical-cards.js', 'report-benchmarks.js', 'sec-m2-candidates.json', 'virtual-trading.js', 'sec-reported.js', 'style.css', 'sec-universe-shares.js', 'app.js', 'holdings-capture.js', 'private-subset-view.js', 'pc-layout.css', 'offline.html', 'portfolio-screen.js', 'private-history.css', 'company-logos.js', 'google-sheet-quotes.css', 'share-class-groups.js', 'device-profiles.js', 'private-trades.js', 'sec-valuation-inputs.json', 'actual-catalog.json', 'pwa.js', 'universe-domains.json', 'manager-styles-v0.js', 'icon-192.png', 'forward-validation.js', 'private-subset.js', 'service-worker.js', 'screen-detail.js', 'profile-defaults.js', 'entities.json', 'chart-indicators.js', 'leaderboard-screen.js', 'holdings-capture-view.js'})
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
