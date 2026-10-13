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
            self.assertEqual({p.name for p in out.iterdir()}, {'entity-search.js', 'virtual-trading-signals.js', 'private-history.js', 'data.json', 'pwa.js', 'locale.js', 'sec-universe-shares.js', 'table-sort.js', 'sec-filing-windows.json', 'app.js', 'sec-13f-changes.json', 'virtual-trading-compare.js', 'technical-chart.js', 'worker-quote-fallback.js', 'technical-cards.js', 'playbook-config-defaults.js', 'manager-styles-v0.js', 'device-actual.css', 'virtual-trading.js', 'sec-m2-candidates.json', 'google-sheet-quotes.js', 'pc-layout.css', 'virtual-trading-v-history.js', 'classification-screens.js', 'private-trades.js', 'chart-indicators.js', 'offline.html', 'research.html', 'sec-reported.js', 'report-benchmarks.js', 'holdings-capture-view.js', 'virtual-ledger-sheets.js', 'device-backup.js', 'share-class-groups.js', 'ops-status.js', 'company-types-pricefree.json', 'type-config-defaults.js', 'company-classification.json', 'portfolio-screen.js', 'virtual-trading-runner.js', 'daily-report.js', 'icon-192.png', 'service-worker.js', 'profile-defaults.js', 'sec-universe-qg.js', 'google-sheet-setup.js', 'icon-512.png', 'app-config.js', 'forward-validation.js', 'leaderboard-screen.js', 'playbook-engine.js', 'actual-catalog.json', 'holdings-capture.js', 'thirteenf-quarter.js', 'device-valuation.js', 'device-actual.js', 'screen-detail.js', 'universe-codes.json', 'device-profiles.js', 'company-screen.js', 'macro-screen.json', 'private-subset-view.js', 'sec-m3-adapter.js', 'dcf-parameters-defaults.js', 'device-market.js', 'watchlist.js', 'google-sheet-core.js', 'sec-valuation-inputs.json', 'sec-qgv2.js', 'google-sheet-quotes.css', 'entities.json', 'playbook-screen.js', 'private-subset.js', 'index.html', 'engine-preview.js', 'style.css', 'public-screens.js', 'sec-qg-factors.json', 'manifest.json', 'private-history.css'})
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
