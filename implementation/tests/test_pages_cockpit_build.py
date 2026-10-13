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
            self.assertEqual({p.name for p in out.iterdir()}, {'universe-codes.json', 'service-worker.js', 'sec-13f-changes.json', 'locale.js', 'private-subset.js', 'manifest.json', 'playbook-engine.js', 'manager-styles-v0.js', 'company-types-pricefree.json', 'sec-disclosures.json', 'index.html', 'profile-defaults.js', 'dart-disclosures.json', 'pwa.js', 'daily-report.js', 'private-history.js', 'classification-screens.js', 'sec-universe-shares.js', 'entities.json', 'research.html', 'macro-screen.json', 'device-market.js', 'table-sort.js', 'report-benchmarks.js', 'watchlist.js', 'dcf-parameters-defaults.js', 'sec-m3-adapter.js', 'icon-512.png', 'sec-m2-candidates.json', 'forward-validation.js', 'google-sheet-quotes.js', 'icon-192.png', 'virtual-trading.js', 'app-config.js', 'virtual-trading-v-history.js', 'sec-qg-factors.json', 'engine-preview.js', 'app.js', 'sec-valuation-inputs.json', 'entity-search.js', 'pc-layout.css', 'sec-universe-qg.js', 'private-subset-view.js', 'technical-cards.js', 'news-signals.js', 'worker-quote-fallback.js', 'holdings-capture.js', 'playbook-config-defaults.js', 'actual-catalog.json', 'technical-chart.js', 'price-store.js', 'virtual-trading-signals.js', 'device-backup.js', 'sec-filing-windows.json', 'sec-qgv2.js', 'leaderboard-screen.js', 'data.json', 'google-sheet-setup.js', 'share-class-groups.js', 'google-sheet-core.js', 'thirteenf-quarter.js', 'dart-disclosures.js', 'virtual-ledger-sheets.js', 'device-profiles.js', 'google-sheet-quotes.css', 'ops-status.js', 'device-actual.js', 'sec-disclosures.js', 'virtual-trading-runner.js', 'dart-financials.json', 'sec-reported.js', 'device-valuation.js', 'type-config-defaults.js', 'holdings-capture-view.js', 'chart-indicators.js', 'style.css', 'virtual-trading-compare.js', 'company-classification.json', 'portfolio-screen.js', 'private-history.css', 'offline.html', 'company-screen.js', 'public-screens.js', 'device-actual.css', 'news-signals.json', 'screen-detail.js', 'private-trades.js'})
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
