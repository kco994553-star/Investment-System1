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
            self.assertEqual({p.name for p in out.iterdir()}, {'locale.js', 'sec-disclosures.json', 'sec-m3-adapter.js', 'company-screen.js', 'service-worker.js', 'scoring-default.js', 'sec-reported.js', 'virtual-trading-signals.js', 'daily-report.js', 'sec-m2-candidates.json', 'profile-defaults.js', 'classification-screens.js', 'style.css', 'public-screens.js', 'holdings-capture-view.js', 'news-signals.json', 'device-backup.js', 'actual-catalog.json', 'entity-search.js', 'engine-preview.js', 'app-config.js', 'macro-screen.json', 'sec-qg-factors.json', 'virtual-ledger-sheets.js', 'private-history.css', 'holdings-capture.js', 'sec-filing-windows.json', 'manager-styles-v0.js', 'offline.html', 'universe-codes.json', 'index.html', 'sec-qgv2.js', 'screen-detail.js', 'pwa.js', 'google-sheet-setup.js', 'data.json', 'technical-chart.js', 'private-subset.js', 'sec-disclosures.js', 'virtual-trading.js', 'google-sheet-quotes.css', 'private-trades.js', 'company-types-pricefree.json', 'device-market.js', 'app.js', 'worker-quote-fallback.js', 'qgv2-inputs.js', 'share-class-groups.js', 'pc-layout.css', 'leaderboard-screen.js', 'manifest.json', 'dcf-parameters-defaults.js', 'technical-cards.js', 'news-signals.js', 'chart-indicators.js', 'device-profiles.js', 'price-store.js', 'private-history.js', 'playbook-engine.js', 'device-actual.js', 'company-classification.json', 'icon-192.png', 'device-valuation.js', 'portfolio-screen.js', 'google-sheet-core.js', 'private-subset-view.js', 'virtual-trading-compare.js', 'table-sort.js', 'virtual-trading-v-history.js', 'watchlist.js', 'ops-status.js', 'type-config-defaults.js', 'sec-universe-shares.js', 'qgv-scores.js', 'research.html', 'virtual-trading-runner.js', 'thirteenf-quarter.js', 'device-actual.css', 'entities.json', 'sec-universe-qg.js', 'report-benchmarks.js', 'sec-13f-changes.json', 'icon-512.png', 'sec-valuation-inputs.json', 'google-sheet-quotes.js', 'playbook-config-defaults.js', 'forward-validation.js', 'qgv-v2.js'})
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
