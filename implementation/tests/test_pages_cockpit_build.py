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
            self.assertEqual({p.name for p in out.iterdir()}, {'actual-catalog.json', 'app.js', 'style.css', 'sec-qgv2.js', 'icon-512.png', 'table-sort.js', 'sec-m2-candidates.json', 'sec-13f-changes.json', 'sec-disclosures.js', 'google-sheet-quotes.js', 'entities.json', 'screen-detail.js', 'leaderboard-screen.js', 'technical-cards.js', 'virtual-trading-signals.js', 'daily-report.js', 'virtual-trading-runner.js', 'research.html', 'technical-chart.js', 'portfolio-screen.js', 'private-trades.js', 'icon-192.png', 'offline.html', 'private-history.js', 'virtual-ledger-sheets.js', 'private-subset-view.js', 'virtual-trading-compare.js', 'company-classification.json', 'sec-universe-shares.js', 'classification-screens.js', 'virtual-trading.js', 'company-screen.js', 'sec-m3-adapter.js', 'universe-codes.json', 'entity-search.js', 'sec-universe-qg.js', 'thirteenf-quarter.js', 'data.json', 'manager-styles-v0.js', 'private-history.css', 'holdings-capture.js', 'macro-screen.json', 'share-class-groups.js', 'ops-status.js', 'watchlist.js', 'google-sheet-quotes.css', 'device-backup.js', 'device-market.js', 'sec-qg-factors.json', 'type-config-defaults.js', 'playbook-config-defaults.js', 'google-sheet-setup.js', 'worker-quote-fallback.js', 'device-actual.css', 'holdings-capture-view.js', 'device-profiles.js', 'virtual-trading-v-history.js', 'report-benchmarks.js', 'company-types-pricefree.json', 'sec-valuation-inputs.json', 'pwa.js', 'dart-disclosures.js', 'google-sheet-core.js', 'playbook-engine.js', 'news-signals.js', 'pc-layout.css', 'manifest.json', 'chart-indicators.js', 'sec-reported.js', 'profile-defaults.js', 'forward-validation.js', 'locale.js', 'index.html', 'app-config.js', 'private-subset.js', 'public-screens.js', 'sec-filing-windows.json', 'device-valuation.js', 'dcf-parameters-defaults.js', 'device-actual.js', 'macro-lights.js', 'service-worker.js', 'engine-preview.js'})
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
