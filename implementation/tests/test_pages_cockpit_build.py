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
            self.assertEqual({p.name for p in out.iterdir()}, {'table-sort.js', 'company-types-pricefree.json', 'private-subset.js', 'holdings-capture-view.js', 'entity-search.js', 'google-sheet-quotes.js', 'worker-quote-fallback.js', 'thirteenf-quarter.js', 'sec-m3-adapter.js', 'news-signals.js', 'daily-report.js', 'public-screens.js', 'offline.html', 'pc-layout.css', 'forward-validation.js', 'google-sheet-core.js', 'private-history.css', 'sec-qgv2.js', 'sec-reported.js', 'sec-m2-candidates.json', 'dcf-parameters-defaults.js', 'company-classification.json', 'device-backup.js', 'device-valuation.js', 'universe-codes.json', 'technical-cards.js', 'dart-disclosures.js', 'leaderboard-screen.js', 'virtual-trading-signals.js', 'device-profiles.js', 'sec-universe-shares.js', 'app.js', 'private-subset-view.js', 'icon-512.png', 'chart-indicators.js', 'google-sheet-setup.js', 'portfolio-screen.js', 'virtual-trading-compare.js', 'google-sheet-quotes.css', 'pwa.js', 'device-actual.css', 'watchlist.js', 'sec-disclosures.json', 'macro-screen.json', 'entities.json', 'service-worker.js', 'locale.js', 'sec-qg-factors.json', 'virtual-trading-runner.js', 'icon-192.png', 'device-actual.js', 'data.json', 'app-config.js', 'research.html', 'virtual-ledger-sheets.js', 'report-benchmarks.js', 'manager-styles-v0.js', 'classification-screens.js', 'share-class-groups.js', 'index.html', 'sec-valuation-inputs.json', 'manifest.json', 'playbook-engine.js', 'ops-status.js', 'virtual-trading.js', 'news-signals.json', 'technical-chart.js', 'screen-detail.js', 'sec-disclosures.js', 'sec-filing-windows.json', 'dart-financials.json', 'sec-universe-qg.js', 'engine-preview.js', 'actual-catalog.json', 'profile-defaults.js', 'playbook-config-defaults.js', 'style.css', 'type-config-defaults.js', 'sec-13f-changes.json', 'holdings-capture.js', 'company-screen.js', 'private-history.js', 'device-market.js', 'virtual-trading-v-history.js', 'private-trades.js', 'price-store.js', 'dart-disclosures.json'})
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
