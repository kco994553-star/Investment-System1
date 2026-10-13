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
            self.assertEqual({p.name for p in out.iterdir()}, {'portfolio-screen.js', 'sec-universe-qg.js', 'sec-disclosures.js', 'sec-disclosures.json', 'sec-13f-changes.json', 'private-subset-view.js', 'public-screens.js', 'holdings-capture.js', 'private-trades.js', 'private-history.css', 'manifest.json', 'macro-screen.json', 'sec-m2-candidates.json', 'news-signals.json', 'classification-screens.js', 'google-sheet-quotes.css', 'playbook-engine.js', 'google-sheet-quotes.js', 'chart-indicators.js', 'data.json', 'report-benchmarks.js', 'index.html', 'virtual-trading-runner.js', 'sec-reported.js', 'locale.js', 'sec-universe-shares.js', 'virtual-ledger-sheets.js', 'profile-defaults.js', 'dart-disclosures.json', 'style.css', 'manager-styles-v0.js', 'device-backup.js', 'daily-report.js', 'pc-layout.css', 'technical-chart.js', 'type-config-defaults.js', 'sec-m3-adapter.js', 'dart-disclosures.js', 'virtual-trading.js', 'company-screen.js', 'table-sort.js', 'playbook-screen.js', 'leaderboard-screen.js', 'thirteenf-quarter.js', 'entity-search.js', 'share-class-groups.js', 'pwa.js', 'ops-status.js', 'sec-filing-windows.json', 'sec-qg-factors.json', 'google-sheet-setup.js', 'offline.html', 'dart-financials.json', 'private-subset.js', 'forward-validation.js', 'playbook-config-defaults.js', 'virtual-trading-signals.js', 'device-actual.js', 'app-config.js', 'device-market.js', 'news-signals.js', 'google-sheet-core.js', 'device-profiles.js', 'company-classification.json', 'icon-512.png', 'watchlist.js', 'research.html', 'screen-detail.js', 'device-actual.css', 'actual-catalog.json', 'holdings-capture-view.js', 'entities.json', 'icon-192.png', 'dcf-parameters-defaults.js', 'virtual-trading-compare.js', 'price-store.js', 'app.js', 'worker-quote-fallback.js', 'service-worker.js', 'technical-cards.js', 'universe-codes.json', 'device-valuation.js', 'engine-preview.js', 'sec-valuation-inputs.json', 'company-types-pricefree.json', 'sec-qgv2.js', 'virtual-trading-v-history.js', 'private-history.js'})
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
