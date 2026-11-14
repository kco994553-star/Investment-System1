"""Public preview of the new frontend (DC-51; owner 2026-11-14 public preview approval): tools/web_app_preview.py."""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
WEB_APP = Path(__file__).resolve().parents[1] / 'src/investment_system/product/web_app'


def load(name: str):
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.styles, self.inline, self.metas, self.links = [], [], 0, [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script':
            if a.get('src'):
                self.scripts.append(a['src'])
            else:
                self.inline += 1
        elif tag == 'link' and a.get('rel') == 'stylesheet':
            self.styles.append(a['href'])
        elif tag == 'meta':
            self.metas.append(a)
        elif tag == 'a':
            self.links.append(a.get('href'))


def parse(text: str) -> _Page:
    page = _Page()
    page.feed(text)
    page.close()
    return page


class WebAppPreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.builder, cls.preview, cls.guard = load('build_pages_cockpit'), load('web_app_preview'), load('pages_artifact_guard')
        cls.with_preview, cls.without = Path(cls.tmp.name) / 'with', Path(cls.tmp.name) / 'without'
        cls.builder.build_public_cockpit(cls.with_preview)
        cls.builder.build_public_cockpit(cls.without, preview=False)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def added(self) -> set[str]:
        return {p.name for p in self.with_preview.iterdir()} - {p.name for p in self.without.iterdir()}

    def test_preview_only_adds_files_and_leaves_every_current_file_byte_identical(self):
        for p in self.without.iterdir():
            if p.suffix == '.json':  # public data carry their own build time; the preview writes none of them
                self.assertTrue((self.with_preview / p.name).is_file(), p.name)
            else:
                self.assertEqual((self.with_preview / p.name).read_bytes(), p.read_bytes(), p.name)
        own = {p.name for p in WEB_APP.iterdir() if p.is_file()} - {'index.html'}
        shared = {n for n in own if (self.without / n).is_file()}
        self.assertEqual(shared, {'jua-regular-ksx1001.woff2', 'jua-OFL.txt', 'screen-detail.js'})
        expected = (own - shared) | {'app.html', 'preview-banner.css', 'app-screen-detail.js'}
        self.assertEqual(self.added(), expected)

    def test_guard_passes_and_pins_every_added_file(self):
        receipt = self.guard.scan_artifact(self.with_preview)
        self.assertEqual(receipt['pages_artifact_guard'], 'PASS', receipt)
        # A real deploy also carries the allowed public data files the offline build lacks (live-only, e.g. sec-qgv2.json):
        # the preview must fit with all of them, so a web_app that grows past the entry limit fails here, not at deploy.
        live_only = {n for n in self.guard.ALLOWED_NAMES if n.endswith('.json')} - {p.name for p in self.with_preview.iterdir()}
        self.assertLessEqual(receipt['files_scanned'] + len(live_only), self.guard.MAX_ENTRIES)
        self.assertEqual(self.guard.MAX_ENTRIES, 192)
        self.assertEqual(self.guard.MAX_FILE_BYTES, 2 * 1024 * 1024)
        for name in self.added():
            digest = hashlib.sha256((self.with_preview / name).read_bytes()).hexdigest()
            self.assertEqual(self.guard.APPROVED_SHA256.get(name), digest, name)

    def test_page_keeps_csp_and_has_banner_links_and_no_inline_script(self):
        source = (WEB_APP / 'index.html').read_text(encoding='utf-8')
        page_text = (self.with_preview / 'app.html').read_text(encoding='utf-8')
        page, original = parse(page_text), parse(source)
        csp = lambda p: [m['content'] for m in p.metas if m.get('http-equiv') == 'Content-Security-Policy']
        self.assertEqual(csp(page), csp(original))
        self.assertEqual(len(csp(page)), 1)
        self.assertEqual(page.inline, 0)
        self.assertEqual(page_text.count('새 화면 미리보기 · 일부 기능 준비 중'), 1)
        self.assertEqual(page.links, ['./#home', './#leaderboard', './#technical', './#portfolio'])
        self.assertEqual(page.styles, ['app.css', 'preview-banner.css'])
        self.assertNotIn('screen-detail.js', page.scripts)
        self.assertEqual(page.scripts, [self.preview.RENAMED.get(s, s) for s in original.scripts])
        # Nothing else in the page changes: removing the three additions gives the source back.
        restored = page_text.replace(self.preview.BANNER + '\n    ', '').replace(
            '\n    <link rel="stylesheet" href="preview-banner.css" />', '').replace('app-screen-detail.js', 'screen-detail.js')
        self.assertEqual(restored, source)

    def test_every_script_the_page_loads_is_published(self):
        page = parse((self.with_preview / 'app.html').read_text(encoding='utf-8'))
        web_app = load('build_web_app')
        for name in page.scripts + page.styles + web_app.load_order():
            self.assertTrue((self.with_preview / name).is_file(), name)
        for name in web_app.reused_old_files():
            self.assertEqual((self.with_preview / name).read_bytes(), (web_app.OLD / name).read_bytes(), name)

    def test_clash_with_a_current_file_fails_instead_of_replacing_it(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            shutil.copytree(self.without, out)
            (out / 'action.js').write_text('// a current file of the same name\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'would replace a current file: action.js'):
                self.preview.emit(out)
            self.assertEqual((out / 'action.js').read_text(encoding='utf-8'), '// a current file of the same name\n')
            self.assertFalse((out / 'app.html').exists())  # nothing written before the check
        for name in ('app.html', 'preview-banner.css', 'app-screen-detail.js'):
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder) / 'site'
                shutil.copytree(self.without, out)
                (out / name).write_text('x', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'would replace a current file'):
                    self.preview.emit(out)

    def test_reused_current_file_must_be_byte_identical(self):
        reused = load('build_web_app').reused_old_files()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            shutil.copytree(self.without, out)
            (out / reused[0]).write_text('// changed\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'byte-identical'):
                self.preview.emit(out)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'site'
            shutil.copytree(self.without, out)
            (out / reused[-1]).unlink()
            with self.assertRaisesRegex(ValueError, 'byte-identical'):
                self.preview.emit(out)

    def test_page_html_needs_each_anchor_exactly_once(self):
        source = (WEB_APP / 'index.html').read_text(encoding='utf-8')
        for anchor in ('<div id="app"></div>', '<link rel="stylesheet" href="app.css" />',
                       '<script defer src="screen-detail.js"></script>'):
            with self.assertRaisesRegex(ValueError, 'exactly once'):
                self.preview.page_html(source.replace(anchor, ''))
            with self.assertRaisesRegex(ValueError, 'exactly once'):
                self.preview.page_html(source.replace(anchor, anchor + anchor))

    def test_banner_style_is_plain_css_without_remote_resources(self):
        css = (self.with_preview / 'preview-banner.css').read_text(encoding='utf-8')
        self.assertIsNone(re.search(r'url\(|@import|https?:', css))

    def test_development_build_is_unchanged_by_the_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'dev'
            load('build_web_app').build_web_app(out)
            names = {p.name for p in out.iterdir()}
            self.assertIn('index.html', names)
            self.assertFalse({'app.html', 'preview-banner.css', 'app-screen-detail.js'} & names)
            self.assertEqual((out / 'index.html').read_bytes(), (WEB_APP / 'index.html').read_bytes())


if __name__ == '__main__':
    unittest.main()
