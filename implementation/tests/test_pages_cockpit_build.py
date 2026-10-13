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
            self.assertEqual({p.name for p in out.iterdir()}, {'google-sheet-core.js', 'universe-codes.json', 'share-class-groups.js', 'sec-disclosures.json', 'news-signals.json', 'dcf-parameters-defaults.js', 'holdings-capture.js', 'private-trades.js', 'virtual-ledger-sheets.js', 'company-screen.js', 'app.js', 'chart-indicators.js', 'device-actual.js', 'locale.js', 'research.html', 'technical-chart.js', 'index.html', 'playbook-engine.js', 'icon-512.png', 'sec-m3-adapter.js', 'technical-cards.js', 'virtual-trading-signals.js', 'classification-screens.js', 'private-subset-view.js', 'dart-disclosures.json', 'manager-styles-v0.js', 'private-history.css', 'portfolio-screen.js', 'watchlist.js', 'screen-detail.js', 'public-screens.js', 'virtual-trading-compare.js', 'icon-192.png', 'google-sheet-setup.js', 'device-profiles.js', 'ops-status.js', 'service-worker.js', 'entities.json', 'sec-13f-changes.json', 'company-types-pricefree.json', 'thirteenf-quarter.js', 'dart-financials.json', 'device-market.js', 'google-sheet-quotes.js', 'device-actual.css', 'macro-screen.json', 'pc-layout.css', 'virtual-trading-runner.js', 'macro-lights.js', 'forward-validation.js', 'engine-preview.js', 'sec-filing-windows.json', 'data.json', 'offline.html', 'pwa.js', 'sec-disclosures.js', 'sec-qgv2.js', 'table-sort.js', 'google-sheet-quotes.css', 'device-backup.js', 'profile-defaults.js', 'actual-catalog.json', 'leaderboard-screen.js', 'device-valuation.js', 'virtual-trading.js', 'entity-search.js', 'sec-m2-candidates.json', 'sec-valuation-inputs.json', 'worker-quote-fallback.js', 'daily-report.js', 'report-benchmarks.js', 'sec-universe-qg.js', 'type-config-defaults.js', 'sec-reported.js', 'sec-universe-shares.js', 'dart-disclosures.js', 'virtual-trading-v-history.js', 'news-signals.js', 'manifest.json', 'playbook-config-defaults.js', 'sec-qg-factors.json', 'company-classification.json', 'private-subset.js', 'style.css', 'app-config.js', 'price-store.js', 'private-history.js', 'holdings-capture-view.js'})
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
