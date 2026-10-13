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
            self.assertEqual({p.name for p in out.iterdir()}, {'manifest.json', 'holdings-capture-view.js', 'dart-financials.json', 'public-screens.js', 'entity-search.js', 'leaderboard-screen.js', 'virtual-trading.js', 'playbook-engine.js', 'technical-cards.js', 'sec-valuation-inputs.json', 'virtual-ledger-sheets.js', 'sec-universe-shares.js', 'holdings-capture.js', 'device-backup.js', 'sec-reported.js', 'actual-catalog.json', 'dart-disclosures.json', 'table-sort.js', 'google-sheet-core.js', 'share-class-groups.js', 'private-history.js', 'thirteenf-quarter.js', 'research.html', 'sec-qgv2.js', 'news-signals.json', 'classification-screens.js', 'universe-codes.json', 'portfolio-screen.js', 'sec-filing-windows.json', 'offline.html', 'pc-layout.css', 'style.css', 'dcf-parameters-defaults.js', 'sec-disclosures.js', 'private-trades.js', 'app.js', 'device-actual.js', 'sec-qg-factors.json', 'google-sheet-setup.js', 'playbook-config-defaults.js', 'forward-validation.js', 'type-config-defaults.js', 'ops-status.js', 'google-sheet-quotes.css', 'company-screen.js', 'device-profiles.js', 'sec-universe-qg.js', 'device-valuation.js', 'price-store.js', 'pwa.js', 'profile-defaults.js', 'service-worker.js', 'device-actual.css', 'google-sheet-quotes.js', 'worker-quote-fallback.js', 'sec-disclosures.json', 'data.json', 'locale.js', 'daily-report.js', 'entities.json', 'screen-detail.js', 'device-market.js', 'engine-preview.js', 'icon-512.png', 'virtual-trading-compare.js', 'company-types-pricefree.json', 'app-config.js', 'virtual-trading-v-history.js', 'icon-192.png', 'private-subset.js', 'sec-13f-changes.json', 'manager-styles-v0.js', 'chart-indicators.js', 'dart-disclosures.js', 'macro-screen.json', 'private-history.css', 'sec-m3-adapter.js', 'news-signals.js', 'sec-m2-candidates.json', 'virtual-trading-runner.js', 'company-classification.json', 'virtual-trading-signals.js', 'private-subset-view.js', 'report-benchmarks.js', 'playbook-screen.js', 'index.html', 'technical-chart.js', 'watchlist.js'})
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
