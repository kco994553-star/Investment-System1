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
            self.assertEqual({p.name for p in out.iterdir()}, {'actual-catalog.json', 'company-names-ko.json', 'app-config.js', 'app.js', 'app-shell.js', 'home-screen.js', 'home-quotes.js', 'universe-company.js', 'universe-company.css', 'stat-radar.js', 'stat-radar.css', 'macro-cycle-ring.js', 'macro-cycle-ring.css', 'v-coverage.js', 'v-coverage.css', 'doodles.js', 'ia-screens.js', 'theme-boot.js', 'theme.css', 'chart-bars.js', 'chart-renderer.js', 'chart-workbench.css', 'chart-workbench.js', 'lightweight-charts-5.2.1.LICENSE.txt', 'lightweight-charts-5.2.1.NOTICE.txt', 'lightweight-charts-5.2.1.standalone.js', 'third-party-notices.txt', 'chart-indicators.js', 'classification-screens.js', 'company-classification.json', 'company-logos.js', 'company-logos.json', 'company-screen.js', 'company-types-pricefree.json', 'daily-report.js', 'dart-disclosures.js', 'dart-disclosures.json', 'dart-financials.json', 'data-refresh.js', 'data.json', 'dcf-parameters-defaults.js', 'device-actual.css', 'device-actual.js', 'device-backup.js', 'device-market.js', 'device-profiles.js', 'device-valuation.js', 'engine-preview.js', 'entities.json', 'entity-search.js', 'forward-validation.js', 'google-sheet-core.js', 'google-sheet-quotes.css', 'google-sheet-quotes.js', 'google-sheet-setup.js', 'holdings-capture-view.js', 'holdings-capture.js', 'icon-192.png', 'icon-512.png', 'index.html', 'leaderboard-screen.js', 'locale.js', 'macro-lights.js', 'macro-screen.json', 'manager-styles-v0.js', 'manifest.json', 'news-signals.js', 'news-signals.json', 'offline.html', 'ops-status.js', 'pattern-config-defaults.js', 'pattern-engine.js', 'pattern-history.js', 'pc-layout.css', 'playbook-config-defaults.js', 'playbook-engine.js', 'playbook-screen.js', 'portfolio-screen.js', 'price-store.js', 'price-time.js', 'private-history.css', 'private-history.js', 'private-subset-view.js', 'private-subset.js', 'private-trades.js', 'profile-defaults.js', 'public-screens.js', 'pwa.js', 'qgv-scores.js', 'qgv-v2.js', 'qgv2-inputs.js', 'report-benchmarks.js', 'research.html', 'scoring-default.js', 'screen-detail.js', 'sec-13f-changes.json', 'sec-disclosures.js', 'sec-disclosures.json', 'sec-filing-windows.json', 'sec-m2-candidates.json', 'sec-m3-adapter.js', 'sec-qg-factors.json', 'sec-qgv2.js', 'sec-reported.js', 'sec-universe-qg.js', 'sec-universe-shares.js', 'sec-valuation-inputs.json', 'service-worker.js', 'share-class-groups.js', 'style.css', 'table-sort.js', 'technical-cards.js', 'technical-chart.js', 'thirteenf-quarter.js', 'tradingview-widgets.js', 'type-config-defaults.js', 'universe-codes.json', 'universe-domains.json', 'virtual-ledger-sheets.js', 'virtual-trading-compare.js', 'virtual-trading-runner.js', 'virtual-trading-signals.js', 'virtual-trading-v-history.js', 'virtual-trading.js', 'watchlist.js', 'worker-quote-fallback.js'})
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
