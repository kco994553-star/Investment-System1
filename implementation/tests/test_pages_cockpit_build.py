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
            self.assertEqual({p.name for p in out.iterdir()}, {'profile-defaults.js', 'portfolio-screen.js', 'device-market.js', 'locale.js', 'sec-qg-factors.json', 'manager-styles-v0.js', 'sec-qgv2.js', 'technical-chart.js', 'sec-m2-candidates.json', 'google-sheet-quotes.js', 'screen-detail.js', 'macro-screen.json', 'public-screens.js', 'google-sheet-core.js', 'thirteenf-quarter.js', 'entity-search.js', 'service-worker.js', 'entities.json', 'forward-validation.js', 'icon-512.png', 'style.css', 'engine-preview.js', 'universe-codes.json', 'app-config.js', 'sec-universe-qg.js', 'virtual-trading-signals.js', 'technical-cards.js', 'playbook-config-defaults.js', 'virtual-trading-runner.js', 'index.html', 'report-benchmarks.js', 'share-class-groups.js', 'device-profiles.js', 'icon-192.png', 'private-subset-view.js', 'pwa.js', 'manifest.json', 'data.json', 'company-screen.js', 'watchlist.js', 'pc-layout.css', 'private-trades.js', 'sec-valuation-inputs.json', 'private-history.css', 'offline.html', 'actual-catalog.json', 'price-store.js', 'daily-report.js', 'ops-status.js', 'sec-filing-windows.json', 'dcf-parameters-defaults.js', 'google-sheet-quotes.css', 'device-actual.js', 'app.js', 'virtual-trading.js', 'google-sheet-setup.js', 'table-sort.js', 'sec-13f-changes.json', 'virtual-trading-v-history.js', 'company-types-pricefree.json', 'company-classification.json', 'chart-indicators.js', 'holdings-capture.js', 'worker-quote-fallback.js', 'leaderboard-screen.js', 'playbook-engine.js', 'private-history.js', 'virtual-trading-compare.js', 'device-backup.js', 'holdings-capture-view.js', 'type-config-defaults.js', 'virtual-ledger-sheets.js', 'sec-universe-shares.js', 'sec-m3-adapter.js', 'device-actual.css', 'private-subset.js', 'sec-reported.js', 'device-valuation.js', 'classification-screens.js', 'research.html'})
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
