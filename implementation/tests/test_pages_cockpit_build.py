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
            self.assertEqual({p.name for p in out.iterdir()}, {'thirteenf-quarter.js', 'locale.js', 'virtual-trading-signals.js', 'virtual-trading-compare.js', 'pwa.js', 'sec-qg-factors.json', 'device-market.js', 'ops-status.js', 'index.html', 'company-types-pricefree.json', 'public-screens.js', 'manager-styles-v0.js', 'device-actual.css', 'entity-search.js', 'virtual-trading.js', 'sec-disclosures.js', 'dcf-parameters-defaults.js', 'engine-preview.js', 'virtual-trading-runner.js', 'private-subset-view.js', 'classification-screens.js', 'company-screen.js', 'sec-valuation-inputs.json', 'app-config.js', 'sec-m2-candidates.json', 'type-config-defaults.js', 'profile-defaults.js', 'dart-disclosures.json', 'service-worker.js', 'private-subset.js', 'dart-financials.json', 'worker-quote-fallback.js', 'google-sheet-quotes.css', 'research.html', 'offline.html', 'sec-disclosures.json', 'device-actual.js', 'google-sheet-quotes.js', 'icon-192.png', 'share-class-groups.js', 'chart-indicators.js', 'virtual-trading-v-history.js', 'device-valuation.js', 'sec-qgv2.js', 'virtual-ledger-sheets.js', 'google-sheet-setup.js', 'macro-screen.json', 'portfolio-screen.js', 'forward-validation.js', 'report-benchmarks.js', 'playbook-config-defaults.js', 'holdings-capture-view.js', 'private-history.css', 'device-backup.js', 'pc-layout.css', 'company-classification.json', 'app.js', 'private-trades.js', 'screen-detail.js', 'google-sheet-core.js', 'dart-disclosures.js', 'entities.json', 'universe-codes.json', 'sec-filing-windows.json', 'private-history.js', 'holdings-capture.js', 'sec-m3-adapter.js', 'device-profiles.js', 'technical-chart.js', 'style.css', 'news-signals.json', 'table-sort.js', 'playbook-engine.js', 'technical-cards.js', 'daily-report.js', 'leaderboard-screen.js', 'actual-catalog.json', 'price-store.js', 'sec-13f-changes.json', 'manifest.json', 'sec-universe-shares.js', 'data.json', 'news-signals.js', 'icon-512.png', 'watchlist.js', 'sec-reported.js', 'sec-universe-qg.js'})
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
