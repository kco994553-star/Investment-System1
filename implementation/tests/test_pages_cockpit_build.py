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
            self.assertEqual({p.name for p in out.iterdir()}, {'device-actual.css', 'holdings-capture.js', 'dcf-parameters-defaults.js', 'watchlist.js', 'playbook-config-defaults.js', 'research.html', 'style.css', 'technical-cards.js', 'data.json', 'sec-reported.js', 'dart-financials.json', 'dart-disclosures.json', 'private-subset.js', 'news-signals.json', 'universe-codes.json', 'sec-disclosures.json', 'virtual-trading.js', 'manager-styles-v0.js', 'forward-validation.js', 'google-sheet-quotes.js', 'holdings-capture-view.js', 'sec-qgv2.js', 'private-subset-view.js', 'price-store.js', 'virtual-ledger-sheets.js', 'company-classification.json', 'virtual-trading-signals.js', 'sec-valuation-inputs.json', 'engine-preview.js', 'report-benchmarks.js', 'news-signals.js', 'app-config.js', 'device-profiles.js', 'classification-screens.js', 'icon-512.png', 'worker-quote-fallback.js', 'type-config-defaults.js', 'qgv-v2.js', 'device-actual.js', 'sec-universe-shares.js', 'technical-chart.js', 'daily-report.js', 'actual-catalog.json', 'private-trades.js', 'share-class-groups.js', 'private-history.js', 'sec-qg-factors.json', 'sec-13f-changes.json', 'sec-m2-candidates.json', 'device-backup.js', 'locale.js', 'virtual-trading-runner.js', 'qgv-scores.js', 'service-worker.js', 'pc-layout.css', 'public-screens.js', 'device-market.js', 'pwa.js', 'google-sheet-core.js', 'ops-status.js', 'offline.html', 'index.html', 'sec-m3-adapter.js', 'entities.json', 'profile-defaults.js', 'company-screen.js', 'device-valuation.js', 'chart-indicators.js', 'sec-disclosures.js', 'macro-screen.json', 'manifest.json', 'qgv2-inputs.js', 'google-sheet-quotes.css', 'virtual-trading-v-history.js', 'private-history.css', 'thirteenf-quarter.js', 'portfolio-screen.js', 'table-sort.js', 'sec-filing-windows.json', 'app.js', 'scoring-default.js', 'dart-disclosures.js', 'icon-192.png', 'virtual-trading-compare.js', 'leaderboard-screen.js', 'company-types-pricefree.json', 'playbook-engine.js', 'sec-universe-qg.js', 'entity-search.js', 'google-sheet-setup.js', 'screen-detail.js'})
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
