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
            self.assertEqual({p.name for p in out.iterdir()}, {'private-subset.js', 'news-signals.js', 'google-sheet-setup.js', 'playbook-config-defaults.js', 'chart-indicators.js', 'device-actual.css', 'news-signals.json', 'ops-status.js', 'dart-disclosures.js', 'virtual-trading-runner.js', 'price-store.js', 'sec-m3-adapter.js', 'sec-universe-qg.js', 'device-actual.js', 'icon-512.png', 'data.json', 'virtual-trading-compare.js', 'google-sheet-quotes.css', 'forward-validation.js', 'sec-valuation-inputs.json', 'virtual-trading-v-history.js', 'leaderboard-screen.js', 'engine-preview.js', 'dart-disclosures.json', 'thirteenf-quarter.js', 'service-worker.js', 'sec-disclosures.json', 'universe-codes.json', 'sec-13f-changes.json', 'sec-universe-shares.js', 'dcf-parameters-defaults.js', 'actual-catalog.json', 'technical-cards.js', 'index.html', 'sec-qg-factors.json', 'device-market.js', 'virtual-trading-signals.js', 'research.html', 'private-history.js', 'portfolio-screen.js', 'sec-disclosures.js', 'google-sheet-quotes.js', 'entities.json', 'playbook-engine.js', 'manifest.json', 'entity-search.js', 'icon-192.png', 'style.css', 'sec-m2-candidates.json', 'macro-screen.json', 'profile-defaults.js', 'device-backup.js', 'device-valuation.js', 'company-classification.json', 'holdings-capture.js', 'company-screen.js', 'public-screens.js', 'technical-chart.js', 'device-profiles.js', 'google-sheet-core.js', 'private-history.css', 'daily-report.js', 'sec-reported.js', 'pwa.js', 'report-benchmarks.js', 'app-config.js', 'company-types-pricefree.json', 'classification-screens.js', 'private-trades.js', 'sec-filing-windows.json', 'manager-styles-v0.js', 'private-subset-view.js', 'dart-financials.json', 'pc-layout.css', 'worker-quote-fallback.js', 'watchlist.js', 'offline.html', 'sec-qgv2.js', 'app.js', 'share-class-groups.js', 'virtual-ledger-sheets.js', 'virtual-trading.js', 'holdings-capture-view.js', 'screen-detail.js', 'locale.js', 'table-sort.js', 'type-config-defaults.js'})
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
