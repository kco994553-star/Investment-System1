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
            self.assertEqual({p.name for p in out.iterdir()}, {'technical-cards.js', 'virtual-trading-runner.js', 'sec-disclosures.js', 'screen-detail.js', 'research.html', 'watchlist.js', 'google-sheet-quotes.css', 'sec-qg-factors.json', 'service-worker.js', 'device-actual.css', 'private-subset-view.js', 'company-classification.json', 'report-benchmarks.js', 'google-sheet-quotes.js', 'google-sheet-setup.js', 'sec-valuation-inputs.json', 'app-config.js', 'manager-styles-v0.js', 'sec-reported.js', 'engine-preview.js', 'technical-chart.js', 'classification-screens.js', 'entities.json', 'sec-universe-qg.js', 'sec-m2-candidates.json', 'thirteenf-quarter.js', 'private-trades.js', 'private-history.css', 'icon-192.png', 'private-history.js', 'chart-indicators.js', 'virtual-trading-signals.js', 'public-screens.js', 'device-valuation.js', 'holdings-capture-view.js', 'universe-codes.json', 'private-subset.js', 'share-class-groups.js', 'sec-13f-changes.json', 'virtual-trading.js', 'portfolio-screen.js', 'app.js', 'offline.html', 'virtual-trading-v-history.js', 'sec-qgv2.js', 'device-profiles.js', 'worker-quote-fallback.js', 'ops-status.js', 'sec-universe-shares.js', 'holdings-capture.js', 'company-screen.js', 'data.json', 'sec-filing-windows.json', 'sec-m3-adapter.js', 'leaderboard-screen.js', 'playbook-config-defaults.js', 'type-config-defaults.js', 'device-actual.js', 'locale.js', 'virtual-ledger-sheets.js', 'entity-search.js', 'icon-512.png', 'manifest.json', 'dcf-parameters-defaults.js', 'actual-catalog.json', 'forward-validation.js', 'playbook-screen.js', 'style.css', 'device-backup.js', 'table-sort.js', 'daily-report.js', 'macro-screen.json', 'google-sheet-core.js', 'sec-disclosures.json', 'device-market.js', 'virtual-trading-compare.js', 'playbook-engine.js', 'index.html', 'company-types-pricefree.json', 'profile-defaults.js', 'pwa.js', 'price-store.js', 'pc-layout.css'})
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
