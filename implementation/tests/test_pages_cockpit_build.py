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
            self.assertEqual({p.name for p in out.iterdir()}, {'device-backup.js', 'data.json', 'device-valuation.js', 'leaderboard-screen.js', 'screen-detail.js', 'style.css', 'sec-universe-shares.js', 'private-subset.js', 'app.js', 'device-actual.js', 'service-worker.js', 'company-screen.js', 'worker-quote-fallback.js', 'macro-screen.json', 'engine-preview.js', 'private-history.js', 'technical-chart.js', 'index.html', 'icon-512.png', 'virtual-trading-compare.js', 'app-config.js', 'google-sheet-core.js', 'virtual-trading-signals.js', 'sec-valuation-inputs.json', 'classification-screens.js', 'dcf-parameters-defaults.js', 'ops-status.js', 'public-screens.js', 'device-actual.css', 'sec-qg-factors.json', 'sec-m2-candidates.json', 'sec-reported.js', 'icon-192.png', 'offline.html', 'sec-disclosures.js', 'device-profiles.js', 'manifest.json', 'technical-cards.js', 'manager-styles-v0.js', 'virtual-trading-v-history.js', 'private-subset-view.js', 'type-config-defaults.js', 'holdings-capture.js', 'google-sheet-setup.js', 'virtual-trading-runner.js', 'chart-indicators.js', 'pc-layout.css', 'price-store.js', 'virtual-ledger-sheets.js', 'google-sheet-quotes.js', 'universe-codes.json', 'sec-13f-changes.json', 'research.html', 'pwa.js', 'sec-qgv2.js', 'playbook-config-defaults.js', 'forward-validation.js', 'report-benchmarks.js', 'sec-m3-adapter.js', 'holdings-capture-view.js', 'table-sort.js', 'profile-defaults.js', 'sec-filing-windows.json', 'google-sheet-quotes.css', 'virtual-trading.js', 'company-classification.json', 'thirteenf-quarter.js', 'playbook-engine.js', 'share-class-groups.js', 'actual-catalog.json', 'daily-report.js', 'locale.js', 'entities.json', 'watchlist.js', 'company-types-pricefree.json', 'private-trades.js', 'sec-disclosures.json', 'sec-universe-qg.js', 'entity-search.js', 'private-history.css', 'portfolio-screen.js', 'device-market.js'})
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
