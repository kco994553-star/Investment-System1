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
            self.assertEqual({p.name for p in out.iterdir()}, {'app-config.js', 'sec-disclosures.json', 'private-trades.js', 'forward-validation.js', 'worker-quote-fallback.js', 'device-actual.css', 'portfolio-screen.js', 'technical-cards.js', 'pc-layout.css', 'leaderboard-screen.js', 'classification-screens.js', 'company-screen.js', 'sec-filing-windows.json', 'holdings-capture.js', 'app.js', 'actual-catalog.json', 'thirteenf-quarter.js', 'device-valuation.js', 'ops-status.js', 'device-actual.js', 'chart-indicators.js', 'sec-m3-adapter.js', 'playbook-config-defaults.js', 'universe-codes.json', 'private-history.css', 'dart-disclosures.js', 'macro-screen.json', 'sec-qgv2.js', 'price-store.js', 'virtual-trading-runner.js', 'google-sheet-core.js', 'private-history.js', 'device-backup.js', 'sec-disclosures.js', 'macro-lights.js', 'virtual-trading-compare.js', 'manager-styles-v0.js', 'service-worker.js', 'virtual-trading-signals.js', 'entity-search.js', 'public-screens.js', 'virtual-trading.js', 'report-benchmarks.js', 'sec-universe-qg.js', 'icon-192.png', 'dart-disclosures.json', 'company-classification.json', 'company-types-pricefree.json', 'news-signals.js', 'style.css', 'device-market.js', 'sec-reported.js', 'profile-defaults.js', 'sec-13f-changes.json', 'sec-qg-factors.json', 'entities.json', 'icon-512.png', 'virtual-trading-v-history.js', 'news-signals.json', 'index.html', 'dart-financials.json', 'google-sheet-quotes.css', 'screen-detail.js', 'playbook-engine.js', 'type-config-defaults.js', 'offline.html', 'google-sheet-quotes.js', 'sec-universe-shares.js', 'locale.js', 'engine-preview.js', 'pwa.js', 'holdings-capture-view.js', 'daily-report.js', 'manifest.json', 'technical-chart.js', 'sec-valuation-inputs.json', 'private-subset.js', 'sec-m2-candidates.json', 'private-subset-view.js', 'device-profiles.js', 'dcf-parameters-defaults.js', 'watchlist.js', 'table-sort.js', 'research.html', 'share-class-groups.js', 'data.json', 'virtual-ledger-sheets.js', 'google-sheet-setup.js'})
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
