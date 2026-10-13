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
            self.assertEqual({p.name for p in out.iterdir()}, {'dcf-parameters-defaults.js', 'holdings-capture.js', 'worker-quote-fallback.js', 'google-sheet-core.js', 'locale.js', 'macro-screen.json', 'manifest.json', 'data.json', 'manager-styles-v0.js', 'device-actual.css', 'virtual-trading-v-history.js', 'device-actual.js', 'leaderboard-screen.js', 'playbook-screen.js', 'private-subset-view.js', 'sec-filing-windows.json', 'engine-preview.js', 'pc-layout.css', 'sec-valuation-inputs.json', 'virtual-trading-signals.js', 'virtual-ledger-sheets.js', 'thirteenf-quarter.js', 'sec-13f-changes.json', 'playbook-config-defaults.js', 'technical-chart.js', 'sec-qg-factors.json', 'style.css', 'sec-m2-candidates.json', 'google-sheet-quotes.js', 'app.js', 'company-classification.json', 'screen-detail.js', 'service-worker.js', 'pwa.js', 'private-history.js', 'forward-validation.js', 'device-backup.js', 'portfolio-screen.js', 'sec-universe-qg.js', 'app-config.js', 'private-history.css', 'index.html', 'classification-screens.js', 'entities.json', 'sec-qgv2.js', 'research.html', 'type-config-defaults.js', 'google-sheet-quotes.css', 'offline.html', 'virtual-trading-runner.js', 'sec-m3-adapter.js', 'ops-status.js', 'virtual-trading.js', 'device-valuation.js', 'sec-reported.js', 'daily-report.js', 'entity-search.js', 'google-sheet-setup.js', 'report-benchmarks.js', 'profile-defaults.js', 'private-subset.js', 'table-sort.js', 'public-screens.js', 'holdings-capture-view.js', 'company-types-pricefree.json', 'chart-indicators.js', 'device-market.js', 'device-profiles.js', 'playbook-engine.js', 'virtual-trading-compare.js', 'actual-catalog.json', 'private-trades.js', 'sec-universe-shares.js', 'icon-512.png', 'technical-cards.js', 'watchlist.js', 'icon-192.png', 'universe-codes.json', 'company-screen.js', 'share-class-groups.js'})
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
