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
            self.assertEqual({p.name for p in out.iterdir()}, {'data.json', 'playbook-engine.js', 'thirteenf-quarter.js', 'manager-styles-v0.js', 'google-sheet-quotes.js', 'daily-report.js', 'chart-indicators.js', 'virtual-ledger-sheets.js', 'ops-status.js', 'virtual-trading-signals.js', 'entities.json', 'service-worker.js', 'google-sheet-setup.js', 'universe-codes.json', 'playbook-config-defaults.js', 'app-config.js', 'qgv-v2.js', 'macro-screen.json', 'holdings-capture.js', 'device-actual.css', 'engine-preview.js', 'device-valuation.js', 'pwa.js', 'price-store.js', 'virtual-trading-compare.js', 'app.js', 'icon-192.png', 'private-trades.js', 'profile-defaults.js', 'scoring-default.js', 'company-screen.js', 'worker-quote-fallback.js', 'qgv2-inputs.js', 'icon-512.png', 'private-history.css', 'private-history.js', 'sec-qgv2.js', 'technical-chart.js', 'device-actual.js', 'index.html', 'report-benchmarks.js', 'sec-filing-windows.json', 'device-profiles.js', 'qgv-scores.js', 'table-sort.js', 'virtual-trading.js', 'actual-catalog.json', 'screen-detail.js', 'research.html', 'offline.html', 'technical-cards.js', 'sec-m3-adapter.js', 'portfolio-screen.js', 'holdings-capture-view.js', 'virtual-trading-v-history.js', 'locale.js', 'company-types-pricefree.json', 'forward-validation.js', 'private-subset.js', 'public-screens.js', 'sec-reported.js', 'sec-valuation-inputs.json', 'leaderboard-screen.js', 'google-sheet-quotes.css', 'sec-disclosures.js', 'dcf-parameters-defaults.js', 'virtual-trading-runner.js', 'entity-search.js', 'type-config-defaults.js', 'watchlist.js', 'device-market.js', 'sec-universe-shares.js', 'sec-disclosures.json', 'classification-screens.js', 'style.css', 'manifest.json', 'google-sheet-core.js', 'sec-13f-changes.json', 'company-classification.json', 'private-subset-view.js', 'sec-m2-candidates.json', 'sec-qg-factors.json', 'share-class-groups.js', 'device-backup.js', 'sec-universe-qg.js', 'pc-layout.css'})
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
