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
    def test_publication_excludes_amounts_and_preserves_original_source(self):
        original = repository_bundle()
        before = deepcopy(original)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            public = json.loads((out / 'data.json').read_text())
            self.assertNotIn('cutoff_mcap', public['universe']['data'])
            self.assertEqual(len(public['universe']['data']['members']), 500)
            self.assertTrue(all('mcap' not in row for row in public['universe']['data']['members']))
            self.assertEqual(public['companies'], original['companies'])
            self.assertEqual(public['universe']['state'], original['universe']['state'])
            self.assertEqual(public['universe']['as_of'], original['universe']['as_of'])
            self.assertEqual(public['universe']['source'], original['universe']['source'])
            self.assertEqual([r['company_id'] for r in public['universe']['data']['members']],
                             [r['company_id'] for r in original['universe']['data']['members']])
        self.assertEqual(original, before)
        self.assertEqual(repository_bundle(), before)

    def test_only_web_assets_and_public_identity_catalog_are_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            self.assertEqual({p.name for p in out.iterdir()}, {
                'index.html', 'style.css', 'app.js', 'locale.js', 'entity-search.js',
                'device-actual.js', 'device-actual.css', 'device-market.js', 'data.json', 'entities.json',
                'actual-catalog.json', 'research.html', 'app-config.js', 'google-sheet-core.js',
                'google-sheet-quotes.js', 'google-sheet-quotes.css'})
            catalog = json.loads((out / 'actual-catalog.json').read_text())
            self.assertEqual(len(catalog['instruments']), 19)
            self.assertTrue(all('quantity' not in r and 'average_cost' not in r
                                for r in catalog['instruments']))
            bundle = json.loads((out / 'data.json').read_text())
            for name in ['portfolio', 'qgv', 'technical', 'macro']:
                self.assertEqual(bundle[name]['state'], 'NOT_AVAILABLE')
                self.assertIsNone(bundle[name]['data'])

    def test_relative_assets_and_no_new_pwa_cache_or_root_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            load_tool().build_public_cockpit(out)
            html = (out / 'index.html').read_text()
            self.assertNotIn('src="/', html)
            self.assertNotIn('href="/', html)
            self.assertNotIn('rel="manifest"', html)
            js = '\n'.join(p.read_text() for p in out.glob('*.js'))
            self.assertNotIn('serviceWorker.register', js)

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
