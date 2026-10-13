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
            self.assertEqual({p.name for p in out.iterdir()}, {'private-history.js', 'device-actual.css', 'news-signals.json', 'report-benchmarks.js', 'virtual-trading-v-history.js', 'public-screens.js', 'icon-192.png', 'share-class-groups.js', 'icon-512.png', 'sec-disclosures.json', 'technical-chart.js', 'private-history.css', 'holdings-capture-view.js', 'company-types-pricefree.json', 'playbook-engine.js', 'virtual-trading-compare.js', 'sec-qgv2.js', 'device-valuation.js', 'manifest.json', 'entity-search.js', 'entities.json', 'watchlist.js', 'leaderboard-screen.js', 'device-backup.js', 'actual-catalog.json', 'macro-screen.json', 'private-trades.js', 'sec-universe-qg.js', 'virtual-trading-signals.js', 'virtual-ledger-sheets.js', 'table-sort.js', 'thirteenf-quarter.js', 'pwa.js', 'price-store.js', 'profile-defaults.js', 'portfolio-screen.js', 'google-sheet-quotes.js', 'index.html', 'research.html', 'qgv-scores.js', 'scoring-default.js', 'chart-indicators.js', 'dart-disclosures.js', 'data.json', 'dcf-parameters-defaults.js', 'news-signals.js', 'device-actual.js', 'locale.js', 'google-sheet-core.js', 'type-config-defaults.js', 'company-classification.json', 'google-sheet-quotes.css', 'private-subset-view.js', 'sec-universe-shares.js', 'holdings-capture.js', 'technical-cards.js', 'sec-valuation-inputs.json', 'engine-preview.js', 'sec-reported.js', 'offline.html', 'qgv-v2.js', 'screen-detail.js', 'sec-qg-factors.json', 'device-market.js', 'virtual-trading.js', 'sec-filing-windows.json', 'dart-financials.json', 'company-screen.js', 'style.css', 'service-worker.js', 'sec-13f-changes.json', 'daily-report.js', 'private-subset.js', 'sec-m3-adapter.js', 'ops-status.js', 'forward-validation.js', 'sec-disclosures.js', 'sec-m2-candidates.json', 'classification-screens.js', 'virtual-trading-runner.js', 'app-config.js', 'dart-disclosures.json', 'google-sheet-setup.js', 'pc-layout.css', 'manager-styles-v0.js', 'worker-quote-fallback.js', 'playbook-config-defaults.js', 'universe-codes.json', 'app.js', 'qgv2-inputs.js', 'device-profiles.js'})
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
