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
            self.assertEqual({p.name for p in out.iterdir()}, {'google-sheet-quotes.js', 'sec-reported.js', 'virtual-trading-compare.js', 'virtual-trading.js', 'sec-m2-candidates.json', 'dcf-parameters-defaults.js', 'engine-preview.js', 'private-subset-view.js', 'dart-disclosures.json', 'playbook-engine.js', 'entity-search.js', 'sec-13f-changes.json', 'style.css', 'price-store.js', 'sec-valuation-inputs.json', 'company-classification.json', 'app-config.js', 'private-history.js', 'sec-m3-adapter.js', 'report-benchmarks.js', 'technical-cards.js', 'company-screen.js', 'data.json', 'public-screens.js', 'holdings-capture.js', 'device-actual.js', 'google-sheet-setup.js', 'icon-192.png', 'sec-disclosures.js', 'playbook-config-defaults.js', 'manager-styles-v0.js', 'device-backup.js', 'research.html', 'device-valuation.js', 'pwa.js', 'chart-indicators.js', 'company-types-pricefree.json', 'sec-qgv2.js', 'portfolio-screen.js', 'google-sheet-core.js', 'entities.json', 'private-trades.js', 'device-actual.css', 'sec-universe-shares.js', 'thirteenf-quarter.js', 'actual-catalog.json', 'device-profiles.js', 'device-market.js', 'holdings-capture-view.js', 'icon-512.png', 'table-sort.js', 'virtual-trading-v-history.js', 'index.html', 'manifest.json', 'google-sheet-quotes.css', 'dart-financials.json', 'technical-chart.js', 'dart-disclosures.js', 'service-worker.js', 'leaderboard-screen.js', 'sec-filing-windows.json', 'offline.html', 'locale.js', 'type-config-defaults.js', 'virtual-trading-signals.js', 'daily-report.js', 'news-signals.json', 'virtual-trading-runner.js', 'macro-screen.json', 'sec-qg-factors.json', 'forward-validation.js', 'share-class-groups.js', 'pc-layout.css', 'screen-detail.js', 'watchlist.js', 'profile-defaults.js', 'sec-universe-qg.js', 'app.js', 'news-signals.js', 'virtual-ledger-sheets.js', 'sec-disclosures.json', 'worker-quote-fallback.js', 'universe-codes.json', 'classification-screens.js', 'ops-status.js', 'private-subset.js', 'private-history.css'})
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
