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
            self.assertEqual({p.name for p in out.iterdir()}, {'app.js', 'private-history.css', 'watchlist.js', 'google-sheet-quotes.css', 'icon-512.png', 'holdings-capture-view.js', 'sec-filing-windows.json', 'sec-valuation-inputs.json', 'virtual-trading-signals.js', 'company-types-pricefree.json', 'worker-quote-fallback.js', 'google-sheet-setup.js', 'sec-universe-qg.js', 'playbook-config-defaults.js', 'offline.html', 'engine-preview.js', 'google-sheet-quotes.js', 'device-valuation.js', 'style.css', 'dart-financials.json', 'device-market.js', 'pc-layout.css', 'data.json', 'thirteenf-quarter.js', 'locale.js', 'sec-disclosures.json', 'sec-qgv2.js', 'classification-screens.js', 'playbook-engine.js', 'icon-192.png', 'technical-cards.js', 'forward-validation.js', 'universe-codes.json', 'company-classification.json', 'news-signals.json', 'entities.json', 'pwa.js', 'table-sort.js', 'virtual-trading-compare.js', 'sec-m2-candidates.json', 'research.html', 'sec-qg-factors.json', 'virtual-trading-v-history.js', 'dart-disclosures.js', 'private-trades.js', 'profile-defaults.js', 'leaderboard-screen.js', 'sec-reported.js', 'sec-m3-adapter.js', 'company-screen.js', 'device-actual.js', 'index.html', 'service-worker.js', 'sec-disclosures.js', 'virtual-ledger-sheets.js', 'google-sheet-core.js', 'report-benchmarks.js', 'share-class-groups.js', 'virtual-trading-runner.js', 'portfolio-screen.js', 'sec-universe-shares.js', 'news-signals.js', 'daily-report.js', 'virtual-trading.js', 'chart-indicators.js', 'sec-13f-changes.json', 'price-store.js', 'playbook-screen.js', 'public-screens.js', 'device-profiles.js', 'holdings-capture.js', 'dcf-parameters-defaults.js', 'manager-styles-v0.js', 'private-subset.js', 'device-actual.css', 'actual-catalog.json', 'private-history.js', 'manifest.json', 'screen-detail.js', 'ops-status.js', 'device-backup.js', 'app-config.js', 'technical-chart.js', 'entity-search.js', 'macro-screen.json', 'type-config-defaults.js', 'dart-disclosures.json', 'private-subset-view.js'})
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
