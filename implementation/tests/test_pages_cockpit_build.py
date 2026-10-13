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
            self.assertEqual({p.name for p in out.iterdir()}, {'pc-layout.css', 'google-sheet-core.js', 'chart-indicators.js', 'app-config.js', 'pwa.js', 'data.json', 'virtual-trading-runner.js', 'service-worker.js', 'sec-m2-candidates.json', 'price-store.js', 'screen-detail.js', 'app.js', 'news-signals.js', 'device-backup.js', 'sec-disclosures.json', 'company-screen.js', 'public-screens.js', 'forward-validation.js', 'private-trades.js', 'playbook-config-defaults.js', 'virtual-trading-signals.js', 'report-benchmarks.js', 'icon-512.png', 'macro-screen.json', 'sec-valuation-inputs.json', 'classification-screens.js', 'index.html', 'private-history.js', 'entities.json', 'news-signals.json', 'actual-catalog.json', 'company-classification.json', 'style.css', 'company-types-pricefree.json', 'daily-report.js', 'sec-disclosures.js', 'playbook-engine.js', 'leaderboard-screen.js', 'type-config-defaults.js', 'virtual-trading.js', 'watchlist.js', 'worker-quote-fallback.js', 'thirteenf-quarter.js', 'manager-styles-v0.js', 'virtual-ledger-sheets.js', 'google-sheet-quotes.js', 'virtual-trading-compare.js', 'locale.js', 'private-subset-view.js', 'virtual-trading-v-history.js', 'sec-filing-windows.json', 'entity-search.js', 'google-sheet-setup.js', 'profile-defaults.js', 'device-profiles.js', 'sec-universe-qg.js', 'share-class-groups.js', 'sec-qg-factors.json', 'research.html', 'offline.html', 'private-subset.js', 'icon-192.png', 'ops-status.js', 'technical-chart.js', 'device-market.js', 'manifest.json', 'device-valuation.js', 'universe-codes.json', 'sec-universe-shares.js', 'private-history.css', 'holdings-capture.js', 'sec-qgv2.js', 'dcf-parameters-defaults.js', 'device-actual.js', 'engine-preview.js', 'device-actual.css', 'holdings-capture-view.js', 'technical-cards.js', 'sec-13f-changes.json', 'sec-m3-adapter.js', 'sec-reported.js', 'table-sort.js', 'portfolio-screen.js', 'google-sheet-quotes.css'})
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
