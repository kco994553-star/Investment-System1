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
            self.assertEqual({p.name for p in out.iterdir()}, {'universe-codes.json', 'virtual-trading-v-history.js', 'style.css', 'leaderboard-screen.js', 'classification-screens.js', 'table-sort.js', 'app.js', 'pc-layout.css', 'worker-quote-fallback.js', 'sec-filing-windows.json', 'profile-defaults.js', 'data.json', 'virtual-trading-runner.js', 'playbook-engine.js', 'sec-m2-candidates.json', 'private-trades.js', 'actual-catalog.json', 'sec-reported.js', 'virtual-trading-compare.js', 'playbook-config-defaults.js', 'private-subset.js', 'offline.html', 'virtual-trading-signals.js', 'thirteenf-quarter.js', 'sec-universe-qg.js', 'engine-preview.js', 'type-config-defaults.js', 'device-market.js', 'icon-192.png', 'ops-status.js', 'dcf-parameters-defaults.js', 'device-actual.js', 'sec-m3-adapter.js', 'google-sheet-core.js', 'icon-512.png', 'technical-chart.js', 'device-valuation.js', 'report-benchmarks.js', 'app-config.js', 'holdings-capture-view.js', 'company-classification.json', 'company-types-pricefree.json', 'google-sheet-quotes.css', 'virtual-trading.js', 'entities.json', 'manager-styles-v0.js', 'sec-universe-shares.js', 'manifest.json', 'device-actual.css', 'service-worker.js', 'public-screens.js', 'sec-qgv2.js', 'company-screen.js', 'forward-validation.js', 'private-history.css', 'screen-detail.js', 'share-class-groups.js', 'virtual-ledger-sheets.js', 'index.html', 'pwa.js', 'sec-valuation-inputs.json', 'macro-screen.json', 'holdings-capture.js', 'locale.js', 'device-backup.js', 'watchlist.js', 'daily-report.js', 'device-profiles.js', 'sec-qg-factors.json', 'portfolio-screen.js', 'private-history.js', 'google-sheet-setup.js', 'entity-search.js', 'google-sheet-quotes.js', 'chart-indicators.js', 'technical-cards.js', 'research.html', 'price-store.js', 'private-subset-view.js', 'sec-13f-changes.json'})
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
