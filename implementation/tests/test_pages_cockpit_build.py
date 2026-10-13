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
            self.assertEqual({p.name for p in out.iterdir()}, {'pwa.js', 'sec-valuation-inputs.json', 'engine-preview.js', 'private-trades.js', 'app.js', 'company-screen.js', 'sec-universe-qg.js', 'virtual-ledger-sheets.js', 'google-sheet-quotes.js', 'dcf-parameters-defaults.js', 'virtual-trading.js', 'locale.js', 'google-sheet-core.js', 'universe-codes.json', 'holdings-capture.js', 'public-screens.js', 'data.json', 'share-class-groups.js', 'profile-defaults.js', 'entity-search.js', 'private-history.css', 'device-actual.js', 'sec-13f-changes.json', 'manifest.json', 'sec-filing-windows.json', 'screen-detail.js', 'type-config-defaults.js', 'sec-m2-candidates.json', 'holdings-capture-view.js', 'icon-512.png', 'sec-disclosures.js', 'device-backup.js', 'app-config.js', 'pc-layout.css', 'offline.html', 'company-types-pricefree.json', 'actual-catalog.json', 'virtual-trading-v-history.js', 'dart-disclosures.js', 'sec-m3-adapter.js', 'ops-status.js', 'device-actual.css', 'google-sheet-quotes.css', 'table-sort.js', 'leaderboard-screen.js', 'index.html', 'technical-chart.js', 'sec-universe-shares.js', 'private-subset.js', 'style.css', 'technical-cards.js', 'chart-indicators.js', 'forward-validation.js', 'research.html', 'icon-192.png', 'device-profiles.js', 'google-sheet-setup.js', 'virtual-trading-compare.js', 'virtual-trading-runner.js', 'daily-report.js', 'entities.json', 'device-market.js', 'watchlist.js', 'portfolio-screen.js', 'virtual-trading-signals.js', 'sec-reported.js', 'macro-screen.json', 'service-worker.js', 'classification-screens.js', 'thirteenf-quarter.js', 'company-classification.json', 'manager-styles-v0.js', 'private-subset-view.js', 'sec-qg-factors.json', 'private-history.js', 'device-valuation.js', 'macro-lights.js', 'worker-quote-fallback.js', 'news-signals.js', 'sec-qgv2.js', 'report-benchmarks.js'})
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
