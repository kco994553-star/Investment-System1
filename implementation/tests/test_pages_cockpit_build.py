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
            self.assertEqual({p.name for p in out.iterdir()}, {'holdings-capture-view.js', 'icon-512.png', 'virtual-trading-compare.js', 'locale.js', 'share-class-groups.js', 'virtual-trading-runner.js', 'icon-192.png', 'playbook-config-defaults.js', 'device-actual.js', 'sec-m3-adapter.js', 'manifest.json', 'actual-catalog.json', 'classification-screens.js', 'company-types-pricefree.json', 'macro-screen.json', 'research.html', 'service-worker.js', 'profile-defaults.js', 'app-config.js', 'universe-codes.json', 'device-actual.css', 'company-classification.json', 'entity-search.js', 'table-sort.js', 'leaderboard-screen.js', 'sec-m2-candidates.json', 'data.json', 'private-subset-view.js', 'daily-report.js', 'worker-quote-fallback.js', 'entities.json', 'sec-13f-changes.json', 'thirteenf-quarter.js', 'google-sheet-quotes.js', 'google-sheet-quotes.css', 'google-sheet-setup.js', 'ops-status.js', 'virtual-trading-v-history.js', 'engine-preview.js', 'watchlist.js', 'chart-indicators.js', 'virtual-trading-signals.js', 'portfolio-screen.js', 'style.css', 'index.html', 'type-config-defaults.js', 'playbook-screen.js', 'sec-reported.js', 'public-screens.js', 'forward-validation.js', 'device-profiles.js', 'sec-qgv2.js', 'private-history.css', 'screen-detail.js', 'holdings-capture.js', 'company-screen.js', 'virtual-ledger-sheets.js', 'device-market.js', 'google-sheet-core.js', 'report-benchmarks.js', 'device-valuation.js', 'private-subset.js', 'offline.html', 'playbook-engine.js', 'private-history.js', 'sec-universe-qg.js', 'pc-layout.css', 'technical-chart.js', 'sec-qg-factors.json', 'manager-styles-v0.js', 'sec-valuation-inputs.json', 'pwa.js', 'device-backup.js', 'private-trades.js', 'sec-filing-windows.json', 'sec-universe-shares.js', 'dcf-parameters-defaults.js', 'virtual-trading.js', 'app.js', 'technical-cards.js'})
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
