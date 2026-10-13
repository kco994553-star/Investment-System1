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
            self.assertEqual({p.name for p in out.iterdir()}, {'forward-validation.js', 'public-screens.js', 'index.html', 'dart-disclosures.json', 'locale.js', 'playbook-engine.js', 'research.html', 'private-trades.js', 'data.json', 'report-benchmarks.js', 'sec-m2-candidates.json', 'entities.json', 'device-actual.css', 'virtual-trading.js', 'virtual-trading-runner.js', 'private-history.css', 'google-sheet-core.js', 'sec-qgv2.js', 'sec-valuation-inputs.json', 'google-sheet-setup.js', 'sec-13f-changes.json', 'type-config-defaults.js', 'device-profiles.js', 'pc-layout.css', 'watchlist.js', 'virtual-trading-v-history.js', 'sec-m3-adapter.js', 'screen-detail.js', 'private-history.js', 'sec-qg-factors.json', 'leaderboard-screen.js', 'device-actual.js', 'dcf-parameters-defaults.js', 'google-sheet-quotes.js', 'technical-cards.js', 'universe-codes.json', 'company-types-pricefree.json', 'company-screen.js', 'holdings-capture.js', 'private-subset.js', 'news-signals.js', 'holdings-capture-view.js', 'macro-screen.json', 'engine-preview.js', 'device-market.js', 'app.js', 'chart-indicators.js', 'dart-financials.json', 'playbook-config-defaults.js', 'virtual-ledger-sheets.js', 'daily-report.js', 'thirteenf-quarter.js', 'share-class-groups.js', 'sec-disclosures.json', 'private-subset-view.js', 'device-backup.js', 'technical-chart.js', 'price-store.js', 'actual-catalog.json', 'entity-search.js', 'device-valuation.js', 'virtual-trading-signals.js', 'pwa.js', 'portfolio-screen.js', 'qgv-v2.js', 'google-sheet-quotes.css', 'sec-reported.js', 'sec-disclosures.js', 'worker-quote-fallback.js', 'profile-defaults.js', 'classification-screens.js', 'offline.html', 'sec-filing-windows.json', 'app-config.js', 'ops-status.js', 'qgv-scores.js', 'sec-universe-shares.js', 'qgv2-inputs.js', 'table-sort.js', 'service-worker.js', 'manifest.json', 'scoring-default.js', 'sec-universe-qg.js', 'company-classification.json', 'virtual-trading-compare.js', 'icon-192.png', 'icon-512.png', 'news-signals.json', 'style.css', 'manager-styles-v0.js', 'dart-disclosures.js'})
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
