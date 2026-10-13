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
            self.assertEqual({p.name for p in out.iterdir()}, {'icon-192.png', 'private-history.css', 'profile-defaults.js', 'macro-screen.json', 'sec-qgv2.js', 'company-types-pricefree.json', 'sec-disclosures.js', 'dart-disclosures.json', 'pc-layout.css', 'device-profiles.js', 'sec-filing-windows.json', 'holdings-capture-view.js', 'sec-reported.js', 'news-signals.json', 'classification-screens.js', 'ops-status.js', 'dart-disclosures.js', 'index.html', 'company-classification.json', 'entities.json', 'screen-detail.js', 'type-config-defaults.js', 'manager-styles-v0.js', 'entity-search.js', 'device-valuation.js', 'dart-financials.json', 'sec-valuation-inputs.json', 'worker-quote-fallback.js', 'sec-universe-qg.js', 'technical-chart.js', 'sec-m2-candidates.json', 'engine-preview.js', 'style.css', 'table-sort.js', 'technical-cards.js', 'pwa.js', 'thirteenf-quarter.js', 'news-signals.js', 'google-sheet-core.js', 'locale.js', 'private-trades.js', 'offline.html', 'device-actual.css', 'virtual-trading-compare.js', 'device-actual.js', 'google-sheet-setup.js', 'public-screens.js', 'holdings-capture.js', 'virtual-trading-signals.js', 'leaderboard-screen.js', 'watchlist.js', 'virtual-trading-v-history.js', 'manifest.json', 'forward-validation.js', 'daily-report.js', 'share-class-groups.js', 'app-config.js', 'virtual-trading.js', 'virtual-ledger-sheets.js', 'private-subset-view.js', 'data.json', 'portfolio-screen.js', 'chart-indicators.js', 'actual-catalog.json', 'google-sheet-quotes.css', 'device-market.js', 'dcf-parameters-defaults.js', 'price-store.js', 'sec-universe-shares.js', 'playbook-config-defaults.js', 'google-sheet-quotes.js', 'sec-qg-factors.json', 'service-worker.js', 'sec-disclosures.json', 'report-benchmarks.js', 'research.html', 'device-backup.js', 'sec-m3-adapter.js', 'app.js', 'private-history.js', 'playbook-engine.js', 'icon-512.png', 'company-screen.js', 'sec-13f-changes.json', 'private-subset.js', 'universe-codes.json', 'virtual-trading-runner.js'})
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
