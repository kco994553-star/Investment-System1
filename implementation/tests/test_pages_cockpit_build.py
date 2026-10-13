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
            self.assertEqual({p.name for p in out.iterdir()}, {'technical-chart.js', 'sec-valuation-inputs.json', 'ops-status.js', 'sec-universe-qg.js', 'manifest.json', 'portfolio-screen.js', 'device-profiles.js', 'public-screens.js', 'price-store.js', 'research.html', 'watchlist.js', 'type-config-defaults.js', 'holdings-capture.js', 'google-sheet-core.js', 'icon-192.png', 'company-screen.js', 'private-history.js', 'index.html', 'sec-reported.js', 'device-backup.js', 'sec-filing-windows.json', 'private-subset.js', 'playbook-engine.js', 'google-sheet-quotes.css', 'device-actual.js', 'playbook-config-defaults.js', 'sec-disclosures.json', 'google-sheet-quotes.js', 'locale.js', 'device-actual.css', 'manager-styles-v0.js', 'profile-defaults.js', 'private-trades.js', 'sec-universe-shares.js', 'style.css', 'company-classification.json', 'icon-512.png', 'virtual-ledger-sheets.js', 'sec-disclosures.js', 'virtual-trading-compare.js', 'worker-quote-fallback.js', 'virtual-trading-signals.js', 'sec-qgv2.js', 'google-sheet-setup.js', 'virtual-trading-runner.js', 'dcf-parameters-defaults.js', 'app.js', 'virtual-trading-v-history.js', 'engine-preview.js', 'share-class-groups.js', 'actual-catalog.json', 'screen-detail.js', 'table-sort.js', 'device-valuation.js', 'pc-layout.css', 'holdings-capture-view.js', 'sec-13f-changes.json', 'classification-screens.js', 'app-config.js', 'daily-report.js', 'macro-screen.json', 'virtual-trading.js', 'offline.html', 'universe-codes.json', 'leaderboard-screen.js', 'thirteenf-quarter.js', 'data.json', 'chart-indicators.js', 'entities.json', 'technical-cards.js', 'private-subset-view.js', 'service-worker.js', 'forward-validation.js', 'sec-m3-adapter.js', 'sec-m2-candidates.json', 'entity-search.js', 'pwa.js', 'sec-qg-factors.json', 'report-benchmarks.js', 'device-market.js', 'company-types-pricefree.json', 'private-history.css'})
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
