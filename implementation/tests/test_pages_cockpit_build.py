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
            self.assertEqual({p.name for p in out.iterdir()}, {'dart-disclosures.json', 'sec-qgv2.js', 'google-sheet-quotes.css', 'app-config.js', 'company-classification.json', 'universe-codes.json', 'virtual-ledger-sheets.js', 'locale.js', 'device-backup.js', 'worker-quote-fallback.js', 'chart-indicators.js', 'private-subset-view.js', 'type-config-defaults.js', 'private-trades.js', 'private-history.css', 'sec-universe-qg.js', 'device-actual.css', 'virtual-trading.js', 'offline.html', 'manifest.json', 'manager-styles-v0.js', 'device-market.js', 'sec-universe-shares.js', 'dcf-parameters-defaults.js', 'sec-reported.js', 'style.css', 'service-worker.js', 'entity-search.js', 'sec-disclosures.json', 'news-signals.js', 'dart-disclosures.js', 'price-store.js', 'thirteenf-quarter.js', 'macro-screen.json', 'classification-screens.js', 'virtual-trading-signals.js', 'icon-192.png', 'report-benchmarks.js', 'sec-13f-changes.json', 'holdings-capture.js', 'google-sheet-core.js', 'sec-valuation-inputs.json', 'actual-catalog.json', 'index.html', 'virtual-trading-v-history.js', 'company-screen.js', 'google-sheet-quotes.js', 'forward-validation.js', 'private-history.js', 'private-subset.js', 'leaderboard-screen.js', 'google-sheet-setup.js', 'pwa.js', 'holdings-capture-view.js', 'sec-m3-adapter.js', 'profile-defaults.js', 'entities.json', 'technical-chart.js', 'table-sort.js', 'app.js', 'daily-report.js', 'portfolio-screen.js', 'virtual-trading-runner.js', 'technical-cards.js', 'macro-lights.js', 'research.html', 'dart-financials.json', 'device-profiles.js', 'sec-m2-candidates.json', 'company-types-pricefree.json', 'virtual-trading-compare.js', 'icon-512.png', 'share-class-groups.js', 'sec-qg-factors.json', 'sec-disclosures.js', 'device-valuation.js', 'device-actual.js', 'watchlist.js', 'sec-filing-windows.json', 'engine-preview.js', 'public-screens.js', 'news-signals.json', 'playbook-config-defaults.js', 'data.json', 'playbook-engine.js', 'ops-status.js', 'screen-detail.js', 'pc-layout.css'})
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
