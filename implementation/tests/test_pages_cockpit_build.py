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
            self.assertEqual({p.name for p in out.iterdir()}, {'tradingview-widgets.js', 'share-class-groups.js', 'watchlist.js', 'playbook-engine.js', 'macro-screen.json', 'sec-13f-changes.json', 'holdings-capture.js', 'app-config.js', 'data.json', 'device-profiles.js', 'report-benchmarks.js', 'forward-validation.js', 'universe-codes.json', 'locale.js', 'engine-preview.js', 'offline.html', 'portfolio-screen.js', 'company-logos.js', 'sec-filing-windows.json', 'profile-defaults.js', 'worker-quote-fallback.js', 'company-classification.json', 'playbook-config-defaults.js', 'virtual-trading-signals.js', 'sec-qg-factors.json', 'virtual-trading-compare.js', 'sec-disclosures.json', 'universe-domains.json', 'sec-reported.js', 'device-actual.js', 'table-sort.js', 'research.html', 'google-sheet-quotes.js', 'entity-search.js', 'virtual-ledger-sheets.js', 'virtual-trading-runner.js', 'sec-valuation-inputs.json', 'classification-screens.js', 'device-actual.css', 'company-logos.json', 'sec-m3-adapter.js', 'leaderboard-screen.js', 'icon-512.png', 'type-config-defaults.js', 'private-trades.js', 'private-history.js', 'device-backup.js', 'sec-qgv2.js', 'screen-detail.js', 'company-types-pricefree.json', 'dcf-parameters-defaults.js', 'public-screens.js', 'icon-192.png', 'app.js', 'sec-m2-candidates.json', 'pwa.js', 'entities.json', 'thirteenf-quarter.js', 'pc-layout.css', 'price-store.js', 'google-sheet-quotes.css', 'style.css', 'google-sheet-core.js', 'device-market.js', 'technical-chart.js', 'holdings-capture-view.js', 'index.html', 'private-subset-view.js', 'device-valuation.js', 'ops-status.js', 'private-history.css', 'google-sheet-setup.js', 'daily-report.js', 'private-subset.js', 'service-worker.js', 'chart-indicators.js', 'sec-universe-qg.js', 'actual-catalog.json', 'technical-cards.js', 'company-screen.js', 'virtual-trading-v-history.js', 'sec-universe-shares.js', 'manifest.json', 'manager-styles-v0.js', 'sec-disclosures.js', 'virtual-trading.js'})
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
