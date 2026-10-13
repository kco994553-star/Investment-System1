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
            self.assertEqual({p.name for p in out.iterdir()}, {'dart-financials.json', 'virtual-trading-runner.js', 'google-sheet-quotes.css', 'holdings-capture.js', 'forward-validation.js', 'sec-disclosures.json', 'sec-qgv2.js', 'leaderboard-screen.js', 'sec-universe-shares.js', 'playbook-engine.js', 'table-sort.js', 'virtual-trading-signals.js', 'device-market.js', 'device-valuation.js', 'research.html', 'sec-universe-qg.js', 'sec-m3-adapter.js', 'playbook-config-defaults.js', 'classification-screens.js', 'universe-codes.json', 'offline.html', 'worker-quote-fallback.js', 'holdings-capture-view.js', 'virtual-trading-compare.js', 'index.html', 'company-types-pricefree.json', 'style.css', 'service-worker.js', 'profile-defaults.js', 'sec-13f-changes.json', 'icon-192.png', 'device-backup.js', 'entity-search.js', 'technical-cards.js', 'thirteenf-quarter.js', 'locale.js', 'app.js', 'actual-catalog.json', 'private-trades.js', 'share-class-groups.js', 'icon-512.png', 'sec-m2-candidates.json', 'device-actual.css', 'portfolio-screen.js', 'sec-qg-factors.json', 'device-profiles.js', 'dcf-parameters-defaults.js', 'virtual-trading.js', 'screen-detail.js', 'virtual-ledger-sheets.js', 'company-screen.js', 'engine-preview.js', 'public-screens.js', 'daily-report.js', 'google-sheet-core.js', 'dart-disclosures.json', 'sec-disclosures.js', 'pc-layout.css', 'manifest.json', 'report-benchmarks.js', 'private-history.js', 'type-config-defaults.js', 'ops-status.js', 'private-subset-view.js', 'watchlist.js', 'private-history.css', 'data.json', 'technical-chart.js', 'price-store.js', 'chart-indicators.js', 'private-subset.js', 'app-config.js', 'dart-disclosures.js', 'sec-filing-windows.json', 'virtual-trading-v-history.js', 'manager-styles-v0.js', 'macro-screen.json', 'entities.json', 'google-sheet-quotes.js', 'device-actual.js', 'pwa.js', 'sec-valuation-inputs.json', 'sec-reported.js', 'company-classification.json', 'google-sheet-setup.js'})
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
