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
            self.assertEqual({p.name for p in out.iterdir()}, {'technical-chart.js', 'sec-13f-changes.json', 'dart-disclosures.json', 'price-store.js', 'sec-universe-shares.js', 'profile-defaults.js', 'sec-disclosures.js', 'offline.html', 'portfolio-screen.js', 'sec-m3-adapter.js', 'report-benchmarks.js', 'manifest.json', 'device-profiles.js', 'private-history.css', 'sec-filing-windows.json', 'sec-universe-qg.js', 'virtual-trading.js', 'public-screens.js', 'research.html', 'company-types-pricefree.json', 'google-sheet-setup.js', 'news-signals.json', 'virtual-trading-runner.js', 'service-worker.js', 'pwa.js', 'device-actual.css', 'leaderboard-screen.js', 'news-signals.js', 'virtual-trading-v-history.js', 'google-sheet-quotes.js', 'google-sheet-core.js', 'locale.js', 'share-class-groups.js', 'icon-192.png', 'private-subset.js', 'style.css', 'actual-catalog.json', 'virtual-ledger-sheets.js', 'sec-valuation-inputs.json', 'watchlist.js', 'device-backup.js', 'icon-512.png', 'thirteenf-quarter.js', 'virtual-trading-signals.js', 'classification-screens.js', 'app.js', 'holdings-capture-view.js', 'engine-preview.js', 'device-market.js', 'data.json', 'company-classification.json', 'index.html', 'dcf-parameters-defaults.js', 'type-config-defaults.js', 'playbook-engine.js', 'macro-screen.json', 'private-history.js', 'entity-search.js', 'dart-financials.json', 'virtual-trading-compare.js', 'playbook-config-defaults.js', 'daily-report.js', 'manager-styles-v0.js', 'sec-qgv2.js', 'sec-reported.js', 'pc-layout.css', 'entities.json', 'private-trades.js', 'ops-status.js', 'sec-qg-factors.json', 'holdings-capture.js', 'private-subset-view.js', 'worker-quote-fallback.js', 'company-screen.js', 'table-sort.js', 'technical-cards.js', 'screen-detail.js', 'universe-codes.json', 'playbook-screen.js', 'sec-m2-candidates.json', 'app-config.js', 'chart-indicators.js', 'google-sheet-quotes.css', 'forward-validation.js', 'device-actual.js', 'sec-disclosures.json', 'dart-disclosures.js', 'device-valuation.js'})
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
