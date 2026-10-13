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
            self.assertEqual({p.name for p in out.iterdir()}, {'dart-disclosures.js', 'virtual-trading-signals.js', 'virtual-trading.js', 'technical-chart.js', 'google-sheet-quotes.js', 'private-history.js', 'sec-universe-qg.js', 'sec-m3-adapter.js', 'portfolio-screen.js', 'virtual-trading-compare.js', 'report-benchmarks.js', 'daily-report.js', 'sec-qgv2.js', 'sec-13f-changes.json', 'icon-512.png', 'google-sheet-quotes.css', 'private-subset-view.js', 'dcf-parameters-defaults.js', 'forward-validation.js', 'app-config.js', 'research.html', 'virtual-trading-v-history.js', 'entities.json', 'offline.html', 'device-market.js', 'type-config-defaults.js', 'public-screens.js', 'company-types-pricefree.json', 'sec-disclosures.js', 'manager-styles-v0.js', 'google-sheet-setup.js', 'manifest.json', 'sec-m2-candidates.json', 'sec-qg-factors.json', 'table-sort.js', 'leaderboard-screen.js', 'private-trades.js', 'app.js', 'device-profiles.js', 'virtual-ledger-sheets.js', 'virtual-trading-runner.js', 'thirteenf-quarter.js', 'chart-indicators.js', 'holdings-capture.js', 'index.html', 'macro-lights.js', 'pwa.js', 'private-subset.js', 'playbook-config-defaults.js', 'service-worker.js', 'engine-preview.js', 'screen-detail.js', 'playbook-engine.js', 'private-history.css', 'sec-filing-windows.json', 'macro-screen.json', 'actual-catalog.json', 'news-signals.js', 'data.json', 'sec-universe-shares.js', 'locale.js', 'ops-status.js', 'technical-cards.js', 'device-actual.js', 'icon-192.png', 'profile-defaults.js', 'device-actual.css', 'universe-codes.json', 'classification-screens.js', 'sec-reported.js', 'company-classification.json', 'device-backup.js', 'company-screen.js', 'holdings-capture-view.js', 'worker-quote-fallback.js', 'google-sheet-core.js', 'entity-search.js', 'sec-valuation-inputs.json', 'pc-layout.css', 'watchlist.js', 'device-valuation.js', 'style.css', 'share-class-groups.js'})
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
