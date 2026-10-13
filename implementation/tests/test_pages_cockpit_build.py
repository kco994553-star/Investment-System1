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
            self.assertEqual({p.name for p in out.iterdir()}, {'locale.js', 'public-screens.js', 'macro-screen.json', 'actual-catalog.json', 'sec-reported.js', 'technical-chart.js', 'device-backup.js', 'offline.html', 'watchlist.js', 'dart-disclosures.json', 'universe-domains.json', 'manifest.json', 'leaderboard-screen.js', 'engine-preview.js', 'virtual-trading-runner.js', 'private-history.css', 'type-config-defaults.js', 'google-sheet-setup.js', 'company-screen.js', 'research.html', 'app.js', 'dart-financials.json', 'private-subset-view.js', 'dcf-parameters-defaults.js', 'google-sheet-core.js', 'pc-layout.css', 'virtual-trading-signals.js', 'private-subset.js', 'sec-qgv2.js', 'portfolio-screen.js', 'sec-m3-adapter.js', 'entity-search.js', 'company-classification.json', 'icon-192.png', 'style.css', 'sec-universe-shares.js', 'virtual-trading.js', 'virtual-ledger-sheets.js', 'company-logos.json', 'service-worker.js', 'holdings-capture.js', 'data.json', 'dart-disclosures.js', 'index.html', 'price-store.js', 'google-sheet-quotes.js', 'sec-universe-qg.js', 'app-config.js', 'technical-cards.js', 'virtual-trading-compare.js', 'sec-disclosures.js', 'private-trades.js', 'thirteenf-quarter.js', 'forward-validation.js', 'device-profiles.js', 'universe-codes.json', 'sec-13f-changes.json', 'holdings-capture-view.js', 'chart-indicators.js', 'pwa.js', 'virtual-trading-v-history.js', 'playbook-config-defaults.js', 'icon-512.png', 'sec-m2-candidates.json', 'screen-detail.js', 'profile-defaults.js', 'playbook-engine.js', 'device-actual.css', 'sec-valuation-inputs.json', 'company-logos.js', 'ops-status.js', 'device-market.js', 'table-sort.js', 'news-signals.js', 'sec-qg-factors.json', 'company-types-pricefree.json', 'device-actual.js', 'classification-screens.js', 'report-benchmarks.js', 'worker-quote-fallback.js', 'sec-disclosures.json', 'tradingview-widgets.js', 'news-signals.json', 'device-valuation.js', 'share-class-groups.js', 'manager-styles-v0.js', 'sec-filing-windows.json', 'private-history.js', 'entities.json', 'google-sheet-quotes.css', 'daily-report.js'})
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
