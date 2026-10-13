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
            self.assertEqual({p.name for p in out.iterdir()}, {'virtual-trading-signals.js', 'sec-universe-shares.js', 'device-profiles.js', 'macro-screen.json', 'thirteenf-quarter.js', 'style.css', 'device-actual.js', 'manifest.json', 'sec-13f-changes.json', 'share-class-groups.js', 'service-worker.js', 'pc-layout.css', 'google-sheet-quotes.js', 'playbook-config-defaults.js', 'playbook-engine.js', 'forward-validation.js', 'portfolio-screen.js', 'private-subset-view.js', 'virtual-ledger-sheets.js', 'device-valuation.js', 'watchlist.js', 'pwa.js', 'sec-filing-windows.json', 'table-sort.js', 'actual-catalog.json', 'classification-screens.js', 'report-benchmarks.js', 'app-config.js', 'chart-indicators.js', 'virtual-trading-compare.js', 'holdings-capture.js', 'research.html', 'google-sheet-core.js', 'company-classification.json', 'type-config-defaults.js', 'entity-search.js', 'sec-m2-candidates.json', 'sec-qgv2.js', 'device-backup.js', 'holdings-capture-view.js', 'index.html', 'data.json', 'manager-styles-v0.js', 'google-sheet-quotes.css', 'engine-preview.js', 'price-store.js', 'profile-defaults.js', 'private-history.js', 'private-trades.js', 'sec-m3-adapter.js', 'locale.js', 'sec-reported.js', 'daily-report.js', 'company-screen.js', 'virtual-trading-runner.js', 'entities.json', 'private-history.css', 'sec-universe-qg.js', 'company-types-pricefree.json', 'technical-cards.js', 'worker-quote-fallback.js', 'leaderboard-screen.js', 'sec-qg-factors.json', 'private-subset.js', 'technical-chart.js', 'public-screens.js', 'app.js', 'device-market.js', 'sec-valuation-inputs.json', 'screen-detail.js', 'offline.html', 'google-sheet-setup.js', 'virtual-trading-v-history.js', 'icon-192.png', 'device-actual.css', 'universe-codes.json', 'virtual-trading.js', 'ops-status.js', 'dcf-parameters-defaults.js', 'icon-512.png'})
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
