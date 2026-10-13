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
            self.assertEqual({p.name for p in out.iterdir()}, {'entity-search.js', 'engine-preview.js', 'watchlist.js', 'google-sheet-quotes.js', 'worker-quote-fallback.js', 'sec-disclosures.json', 'company-types-pricefree.json', 'google-sheet-quotes.css', 'leaderboard-screen.js', 'report-benchmarks.js', 'device-actual.js', 'private-subset-view.js', 'virtual-trading-v-history.js', 'company-classification.json', 'private-history.css', 'private-trades.js', 'private-subset.js', 'sec-qgv2.js', 'manager-styles-v0.js', 'index.html', 'playbook-engine.js', 'holdings-capture.js', 'device-valuation.js', 'sec-m2-candidates.json', 'app-config.js', 'forward-validation.js', 'public-screens.js', 'portfolio-screen.js', 'virtual-trading-compare.js', 'daily-report.js', 'share-class-groups.js', 'technical-cards.js', 'classification-screens.js', 'sec-valuation-inputs.json', 'thirteenf-quarter.js', 'sec-universe-qg.js', 'device-profiles.js', 'virtual-trading.js', 'news-signals.json', 'sec-m3-adapter.js', 'sec-filing-windows.json', 'macro-screen.json', 'news-signals.js', 'playbook-config-defaults.js', 'google-sheet-setup.js', 'virtual-trading-signals.js', 'pc-layout.css', 'icon-192.png', 'screen-detail.js', 'price-store.js', 'private-history.js', 'profile-defaults.js', 'locale.js', 'device-backup.js', 'virtual-trading-runner.js', 'sec-disclosures.js', 'company-screen.js', 'holdings-capture-view.js', 'entities.json', 'icon-512.png', 'research.html', 'ops-status.js', 'chart-indicators.js', 'type-config-defaults.js', 'device-actual.css', 'data.json', 'actual-catalog.json', 'sec-13f-changes.json', 'device-market.js', 'sec-universe-shares.js', 'sec-qg-factors.json', 'table-sort.js', 'dcf-parameters-defaults.js', 'universe-codes.json', 'sec-reported.js', 'offline.html', 'manifest.json', 'google-sheet-core.js', 'service-worker.js', 'style.css', 'pwa.js', 'technical-chart.js', 'app.js', 'virtual-ledger-sheets.js'})
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
