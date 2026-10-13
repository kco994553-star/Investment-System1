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
            self.assertEqual({p.name for p in out.iterdir()}, {'engine-preview.js', 'private-history.css', 'manifest.json', 'virtual-trading.js', 'app-config.js', 'device-valuation.js', 'google-sheet-core.js', 'data.json', 'device-market.js', 'company-classification.json', 'google-sheet-quotes.css', 'app.js', 'forward-validation.js', 'icon-192.png', 'thirteenf-quarter.js', 'pwa.js', 'company-screen.js', 'virtual-trading-compare.js', 'device-actual.js', 'private-trades.js', 'playbook-config-defaults.js', 'sec-m3-adapter.js', 'sec-13f-changes.json', 'company-logos.json', 'manager-styles-v0.js', 'daily-report.js', 'universe-domains.json', 'icon-512.png', 'entities.json', 'virtual-ledger-sheets.js', 'worker-quote-fallback.js', 'entity-search.js', 'company-types-pricefree.json', 'style.css', 'service-worker.js', 'private-subset.js', 'type-config-defaults.js', 'holdings-capture-view.js', 'sec-m2-candidates.json', 'table-sort.js', 'google-sheet-setup.js', 'chart-indicators.js', 'research.html', 'device-profiles.js', 'google-sheet-quotes.js', 'sec-valuation-inputs.json', 'technical-chart.js', 'playbook-engine.js', 'macro-screen.json', 'sec-reported.js', 'holdings-capture.js', 'classification-screens.js', 'sec-filing-windows.json', 'sec-universe-qg.js', 'index.html', 'virtual-trading-signals.js', 'pc-layout.css', 'sec-qg-factors.json', 'private-subset-view.js', 'portfolio-screen.js', 'actual-catalog.json', 'sec-universe-shares.js', 'universe-codes.json', 'company-logos.js', 'virtual-trading-v-history.js', 'share-class-groups.js', 'leaderboard-screen.js', 'private-history.js', 'watchlist.js', 'screen-detail.js', 'ops-status.js', 'virtual-trading-runner.js', 'locale.js', 'device-actual.css', 'technical-cards.js', 'dcf-parameters-defaults.js', 'public-screens.js', 'tradingview-widgets.js', 'offline.html', 'profile-defaults.js', 'sec-qgv2.js', 'report-benchmarks.js', 'device-backup.js'})
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
