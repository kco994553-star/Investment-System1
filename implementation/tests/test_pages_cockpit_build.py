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
            self.assertEqual({p.name for p in out.iterdir()}, {'icon-192.png', 'news-signals.json', 'data.json', 'classification-screens.js', 'private-subset.js', 'profile-defaults.js', 'device-profiles.js', 'news-signals.js', 'sec-universe-shares.js', 'research.html', 'portfolio-screen.js', 'device-backup.js', 'thirteenf-quarter.js', 'icon-512.png', 'service-worker.js', 'sec-m2-candidates.json', 'sec-qgv2.js', 'locale.js', 'leaderboard-screen.js', 'watchlist.js', 'app-config.js', 'device-actual.css', 'type-config-defaults.js', 'ops-status.js', 'sec-m3-adapter.js', 'google-sheet-quotes.js', 'macro-screen.json', 'private-history.css', 'sec-universe-qg.js', 'holdings-capture-view.js', 'virtual-trading-runner.js', 'pc-layout.css', 'virtual-trading-compare.js', 'google-sheet-setup.js', 'sec-filing-windows.json', 'forward-validation.js', 'sec-valuation-inputs.json', 'company-types-pricefree.json', 'device-actual.js', 'virtual-trading.js', 'sec-reported.js', 'public-screens.js', 'engine-preview.js', 'pwa.js', 'sec-13f-changes.json', 'share-class-groups.js', 'index.html', 'company-classification.json', 'worker-quote-fallback.js', 'manager-styles-v0.js', 'technical-chart.js', 'actual-catalog.json', 'playbook-engine.js', 'sec-disclosures.js', 'device-valuation.js', 'universe-codes.json', 'screen-detail.js', 'daily-report.js', 'sec-disclosures.json', 'technical-cards.js', 'price-store.js', 'style.css', 'chart-indicators.js', 'virtual-ledger-sheets.js', 'table-sort.js', 'offline.html', 'holdings-capture.js', 'private-trades.js', 'company-screen.js', 'google-sheet-core.js', 'sec-qg-factors.json', 'entities.json', 'app.js', 'private-history.js', 'virtual-trading-v-history.js', 'virtual-trading-signals.js', 'dcf-parameters-defaults.js', 'entity-search.js', 'google-sheet-quotes.css', 'report-benchmarks.js', 'device-market.js', 'playbook-config-defaults.js', 'private-subset-view.js', 'manifest.json'})
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
