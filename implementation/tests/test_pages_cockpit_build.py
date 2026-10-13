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
            self.assertEqual({p.name for p in out.iterdir()}, {'technical-cards.js', 'classification-screens.js', 'google-sheet-quotes.css', 'icon-512.png', 'leaderboard-screen.js', 'sec-disclosures.js', 'style.css', 'actual-catalog.json', 'virtual-trading-compare.js', 'icon-192.png', 'google-sheet-setup.js', 'chart-indicators.js', 'screen-detail.js', 'index.html', 'app-config.js', 'pwa.js', 'data.json', 'device-backup.js', 'sec-disclosures.json', 'share-class-groups.js', 'ops-status.js', 'device-valuation.js', 'virtual-trading-v-history.js', 'sec-13f-changes.json', 'private-trades.js', 'device-market.js', 'entities.json', 'entity-search.js', 'engine-preview.js', 'sec-universe-qg.js', 'company-classification.json', 'sec-m3-adapter.js', 'google-sheet-core.js', 'table-sort.js', 'google-sheet-quotes.js', 'public-screens.js', 'sec-reported.js', 'holdings-capture-view.js', 'private-subset.js', 'offline.html', 'virtual-trading-signals.js', 'sec-valuation-inputs.json', 'sec-filing-windows.json', 'holdings-capture.js', 'type-config-defaults.js', 'virtual-ledger-sheets.js', 'private-history.css', 'service-worker.js', 'macro-screen.json', 'manifest.json', 'sec-m2-candidates.json', 'dcf-parameters-defaults.js', 'technical-chart.js', 'device-profiles.js', 'pc-layout.css', 'forward-validation.js', 'private-subset-view.js', 'virtual-trading.js', 'device-actual.css', 'research.html', 'profile-defaults.js', 'locale.js', 'company-types-pricefree.json', 'worker-quote-fallback.js', 'report-benchmarks.js', 'device-actual.js', 'sec-qgv2.js', 'manager-styles-v0.js', 'virtual-trading-runner.js', 'portfolio-screen.js', 'daily-report.js', 'private-history.js', 'app.js', 'sec-universe-shares.js', 'sec-qg-factors.json', 'thirteenf-quarter.js', 'universe-codes.json', 'watchlist.js', 'company-screen.js'})
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
