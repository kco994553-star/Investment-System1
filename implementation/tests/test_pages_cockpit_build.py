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
            self.assertEqual({p.name for p in out.iterdir()}, {'manifest.json', 'company-types-pricefree.json', 'locale.js', 'dart-disclosures.json', 'sec-m2-candidates.json', 'holdings-capture.js', 'google-sheet-quotes.css', 'pc-layout.css', 'dcf-parameters-defaults.js', 'device-market.js', 'portfolio-screen.js', 'device-profiles.js', 'worker-quote-fallback.js', 'profile-defaults.js', 'playbook-engine.js', 'sec-universe-shares.js', 'forward-validation.js', 'sec-qg-factors.json', 'macro-screen.json', 'virtual-trading-compare.js', 'company-classification.json', 'device-actual.js', 'tradingview-widgets.js', 'sec-disclosures.js', 'company-screen.js', 'device-backup.js', 'universe-codes.json', 'research.html', 'holdings-capture-view.js', 'service-worker.js', 'virtual-trading-runner.js', 'company-logos.js', 'icon-512.png', 'universe-domains.json', 'sec-valuation-inputs.json', 'actual-catalog.json', 'entities.json', 'private-subset-view.js', 'index.html', 'ops-status.js', 'report-benchmarks.js', 'price-store.js', 'google-sheet-quotes.js', 'sec-13f-changes.json', 'google-sheet-core.js', 'dart-financials.json', 'thirteenf-quarter.js', 'public-screens.js', 'sec-m3-adapter.js', 'private-subset.js', 'technical-chart.js', 'watchlist.js', 'dart-disclosures.js', 'virtual-trading.js', 'type-config-defaults.js', 'sec-qgv2.js', 'private-trades.js', 'offline.html', 'share-class-groups.js', 'virtual-trading-signals.js', 'sec-reported.js', 'style.css', 'google-sheet-setup.js', 'private-history.css', 'screen-detail.js', 'company-logos.json', 'virtual-ledger-sheets.js', 'device-actual.css', 'app-config.js', 'chart-indicators.js', 'private-history.js', 'classification-screens.js', 'table-sort.js', 'entity-search.js', 'data.json', 'device-valuation.js', 'daily-report.js', 'news-signals.json', 'sec-disclosures.json', 'technical-cards.js', 'app.js', 'leaderboard-screen.js', 'sec-universe-qg.js', 'virtual-trading-v-history.js', 'playbook-config-defaults.js', 'engine-preview.js', 'manager-styles-v0.js', 'icon-192.png', 'news-signals.js', 'sec-filing-windows.json', 'pwa.js'})
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
