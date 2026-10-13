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
            self.assertEqual({p.name for p in out.iterdir()}, {'macro-screen.json', 'sec-reported.js', 'app-config.js', 'google-sheet-quotes.css', 'data.json', 'holdings-capture.js', 'type-config-defaults.js', 'private-trades.js', 'sec-universe-shares.js', 'engine-preview.js', 'sec-qgv2.js', 'profile-defaults.js', 'pc-layout.css', 'screen-detail.js', 'sec-m2-candidates.json', 'virtual-trading-runner.js', 'sec-disclosures.js', 'news-signals.json', 'thirteenf-quarter.js', 'icon-512.png', 'actual-catalog.json', 'technical-chart.js', 'watchlist.js', 'google-sheet-quotes.js', 'device-valuation.js', 'virtual-trading-v-history.js', 'news-signals.js', 'device-actual.js', 'sec-m3-adapter.js', 'leaderboard-screen.js', 'portfolio-screen.js', 'manager-styles-v0.js', 'sec-filing-windows.json', 'google-sheet-core.js', 'sec-valuation-inputs.json', 'report-benchmarks.js', 'app.js', 'technical-cards.js', 'index.html', 'private-subset.js', 'private-history.js', 'style.css', 'classification-screens.js', 'private-subset-view.js', 'company-types-pricefree.json', 'device-actual.css', 'device-market.js', 'company-screen.js', 'entity-search.js', 'price-store.js', 'manifest.json', 'virtual-trading-signals.js', 'holdings-capture-view.js', 'service-worker.js', 'sec-qg-factors.json', 'playbook-engine.js', 'private-history.css', 'research.html', 'worker-quote-fallback.js', 'daily-report.js', 'chart-indicators.js', 'dcf-parameters-defaults.js', 'share-class-groups.js', 'sec-universe-qg.js', 'universe-codes.json', 'offline.html', 'entities.json', 'forward-validation.js', 'google-sheet-setup.js', 'pwa.js', 'locale.js', 'icon-192.png', 'playbook-screen.js', 'virtual-trading-compare.js', 'public-screens.js', 'playbook-config-defaults.js', 'sec-13f-changes.json', 'virtual-ledger-sheets.js', 'device-backup.js', 'virtual-trading.js', 'table-sort.js', 'device-profiles.js', 'sec-disclosures.json', 'company-classification.json', 'ops-status.js'})
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
