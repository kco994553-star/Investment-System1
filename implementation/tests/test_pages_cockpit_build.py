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
            self.assertEqual({p.name for p in out.iterdir()}, {'technical-chart.js', 'sec-m2-candidates.json', 'google-sheet-setup.js', 'sec-m3-adapter.js', 'virtual-ledger-sheets.js', 'share-class-groups.js', 'device-actual.css', 'screen-detail.js', 'google-sheet-quotes.js', 'manifest.json', 'dcf-parameters-defaults.js', 'holdings-capture-view.js', 'private-history.js', 'company-screen.js', 'sec-filing-windows.json', 'sec-qg-factors.json', 'type-config-defaults.js', 'sec-valuation-inputs.json', 'watchlist.js', 'style.css', 'index.html', 'report-benchmarks.js', 'device-actual.js', 'news-signals.json', 'technical-cards.js', 'icon-192.png', 'holdings-capture.js', 'news-signals.js', 'company-types-pricefree.json', 'sec-universe-shares.js', 'ops-status.js', 'google-sheet-quotes.css', 'private-subset.js', 'device-profiles.js', 'chart-indicators.js', 'sec-disclosures.js', 'service-worker.js', 'sec-disclosures.json', 'forward-validation.js', 'private-subset-view.js', 'leaderboard-screen.js', 'company-classification.json', 'thirteenf-quarter.js', 'sec-qgv2.js', 'sec-universe-qg.js', 'playbook-engine.js', 'locale.js', 'manager-styles-v0.js', 'virtual-trading-v-history.js', 'google-sheet-core.js', 'private-trades.js', 'virtual-trading-signals.js', 'virtual-trading-runner.js', 'pc-layout.css', 'device-valuation.js', 'app.js', 'virtual-trading.js', 'device-market.js', 'pwa.js', 'public-screens.js', 'icon-512.png', 'sec-13f-changes.json', 'table-sort.js', 'playbook-config-defaults.js', 'macro-screen.json', 'entities.json', 'sec-reported.js', 'private-history.css', 'actual-catalog.json', 'price-store.js', 'universe-codes.json', 'data.json', 'virtual-trading-compare.js', 'offline.html', 'profile-defaults.js', 'device-backup.js', 'app-config.js', 'entity-search.js', 'engine-preview.js', 'daily-report.js', 'worker-quote-fallback.js', 'portfolio-screen.js', 'classification-screens.js', 'research.html'})
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
