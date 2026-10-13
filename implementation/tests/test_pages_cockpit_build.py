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
            self.assertEqual({p.name for p in out.iterdir()}, {'actual-catalog.json', 'type-config-defaults.js', 'worker-quote-fallback.js', 'sec-universe-qg.js', 'forward-validation.js', 'device-actual.css', 'company-logos.json', 'icon-512.png', 'chart-indicators.js', 'ops-status.js', 'playbook-config-defaults.js', 'device-profiles.js', 'virtual-ledger-sheets.js', 'device-backup.js', 'entity-search.js', 'virtual-trading.js', 'virtual-trading-compare.js', 'technical-chart.js', 'app.js', 'google-sheet-quotes.js', 'service-worker.js', 'engine-preview.js', 'icon-192.png', 'private-history.js', 'dcf-parameters-defaults.js', 'data.json', 'private-history.css', 'holdings-capture.js', 'sec-13f-changes.json', 'sec-valuation-inputs.json', 'manifest.json', 'locale.js', 'table-sort.js', 'tradingview-widgets.js', 'company-types-pricefree.json', 'company-screen.js', 'device-market.js', 'sec-qgv2.js', 'private-subset.js', 'sec-reported.js', 'technical-cards.js', 'news-signals.js', 'report-benchmarks.js', 'private-trades.js', 'screen-detail.js', 'price-store.js', 'watchlist.js', 'sec-disclosures.js', 'playbook-engine.js', 'daily-report.js', 'pwa.js', 'universe-domains.json', 'research.html', 'company-logos.js', 'private-subset-view.js', 'google-sheet-setup.js', 'device-valuation.js', 'virtual-trading-signals.js', 'holdings-capture-view.js', 'offline.html', 'app-config.js', 'sec-qg-factors.json', 'sec-universe-shares.js', 'public-screens.js', 'pc-layout.css', 'leaderboard-screen.js', 'universe-codes.json', 'device-actual.js', 'macro-screen.json', 'virtual-trading-runner.js', 'google-sheet-quotes.css', 'company-classification.json', 'classification-screens.js', 'sec-m2-candidates.json', 'style.css', 'sec-m3-adapter.js', 'index.html', 'news-signals.json', 'sec-filing-windows.json', 'google-sheet-core.js', 'manager-styles-v0.js', 'thirteenf-quarter.js', 'entities.json', 'portfolio-screen.js', 'share-class-groups.js', 'profile-defaults.js', 'virtual-trading-v-history.js', 'sec-disclosures.json'})
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
