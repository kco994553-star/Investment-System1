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
            self.assertEqual({p.name for p in out.iterdir()}, {'share-class-groups.js', 'macro-lights.js', 'entity-search.js', 'device-actual.js', 'private-history.css', 'company-screen.js', 'google-sheet-quotes.css', 'manager-styles-v0.js', 'sec-filing-windows.json', 'app-config.js', 'google-sheet-core.js', 'google-sheet-quotes.js', 'locale.js', 'device-valuation.js', 'device-backup.js', 'virtual-trading.js', 'virtual-trading-v-history.js', 'engine-preview.js', 'manifest.json', 'google-sheet-setup.js', 'device-actual.css', 'sec-universe-qg.js', 'holdings-capture.js', 'virtual-trading-runner.js', 'news-signals.json', 'dart-disclosures.json', 'sec-qg-factors.json', 'chart-indicators.js', 'screen-detail.js', 'sec-m3-adapter.js', 'private-history.js', 'profile-defaults.js', 'price-store.js', 'company-classification.json', 'virtual-trading-compare.js', 'app.js', 'leaderboard-screen.js', 'public-screens.js', 'index.html', 'report-benchmarks.js', 'playbook-config-defaults.js', 'private-subset.js', 'playbook-engine.js', 'universe-codes.json', 'dcf-parameters-defaults.js', 'type-config-defaults.js', 'icon-192.png', 'sec-qgv2.js', 'dart-financials.json', 'company-types-pricefree.json', 'macro-screen.json', 'ops-status.js', 'private-trades.js', 'thirteenf-quarter.js', 'sec-universe-shares.js', 'sec-reported.js', 'offline.html', 'holdings-capture-view.js', 'daily-report.js', 'news-signals.js', 'sec-valuation-inputs.json', 'private-subset-view.js', 'watchlist.js', 'table-sort.js', 'technical-cards.js', 'service-worker.js', 'forward-validation.js', 'sec-disclosures.json', 'virtual-trading-signals.js', 'actual-catalog.json', 'device-profiles.js', 'style.css', 'research.html', 'sec-13f-changes.json', 'entities.json', 'data.json', 'device-market.js', 'worker-quote-fallback.js', 'pwa.js', 'dart-disclosures.js', 'classification-screens.js', 'pc-layout.css', 'sec-m2-candidates.json', 'icon-512.png', 'technical-chart.js', 'virtual-ledger-sheets.js', 'portfolio-screen.js', 'sec-disclosures.js'})
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
