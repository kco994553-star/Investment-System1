"""Public preview of the new frontend next to the current screens (DC-51; owner 2026-11-14: a preview anyone can open).

The normal Pages build (build_pages_cockpit.py) calls emit(out) last. It adds the new app as app.html beside the current
index.html, at the artifact root like every other published file, so both workflows that build Pages publish it:
  - app.html is web_app/index.html with the preview banner ("새 화면 미리보기 · 일부 기능 준비 중", links to the current
    screens) and its stylesheet added. Nothing else in the page changes: the same Content-Security-Policy, no inline script.
  - Every other web_app file is copied by its own name. A name the current site already publishes must be byte-identical
    (the shared fonts and their licence text), except the names in RENAMED: web_app's own screen-detail.js differs from the
    current screen of that name, so it is published as app-screen-detail.js and app.html loads it under that name. Any other
    clash fails the build instead of replacing a current file.
  - The old modules the new app reuses (loader.js LOAD_ORDER names with no web_app file, plan A) are not copied again: the
    page loads the current site's files of those names, which must be byte-identical to web_assets (build_web_app.py rule).
  - The data files are the current site's: data.js fetches them by plain name, page-relative, and nothing new is written.
The guard pins every added file by exact name and SHA-256 (pages_artifact_guard.py APPROVED_SHA256); no limit changes.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from build_web_app import NEW, OLD, reused_old_files  # noqa: E402

PREVIEW = TOOLS.parents[0] / 'src/investment_system/product/web_preview'
PAGE = 'app.html'
STYLE = 'preview-banner.css'
RENAMED = {'screen-detail.js': 'app-screen-detail.js'}
# The current screens the banner links to (web_assets/index.html hash sections).
CURRENT_SCREENS = (('홈', 'home'), ('리더보드', 'leaderboard'), ('기술적 분석', 'technical'), ('포트폴리오', 'portfolio'))
BANNER = ('<div class="is2-preview" role="note"><strong>새 화면 미리보기 · 일부 기능 준비 중</strong>'
          '<nav aria-label="기존 화면">기존 화면: '
          + ' '.join(f'<a href="./#{anchor}">{label}</a>' for label, anchor in CURRENT_SCREENS)
          + '</nav></div>')


def _once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f'web_app/index.html must hold exactly once: {old}')
    return text.replace(old, new)


def page_html(index_html: str) -> str:
    """app.html from web_app/index.html: stylesheet, banner and renamed scripts; exact-once replacements or ValueError."""
    text = _once(index_html, '<link rel="stylesheet" href="app.css" />',
                 f'<link rel="stylesheet" href="app.css" />\n    <link rel="stylesheet" href="{STYLE}" />')
    text = _once(text, '<div id="app"></div>', f'{BANNER}\n    <div id="app"></div>')
    for old, new in RENAMED.items():
        text = _once(text, f'<script defer src="{old}"></script>', f'<script defer src="{new}"></script>')
    return text


def emit(out: Path) -> list[str]:
    """Adds the preview to a finished Pages build; returns the names it wrote."""
    out = Path(out)
    keep = reused_old_files()  # also refuses a bad index.html or LOAD_ORDER
    for name in keep:
        if not (out / name).is_file() or (out / name).read_bytes() != (OLD / name).read_bytes():
            raise ValueError(f'the preview reuses a current file that the build did not publish byte-identical: {name}')
    plan: dict[str, bytes] = {}
    for p in sorted(NEW.iterdir()):
        if not p.is_file() or p.name == 'index.html':
            continue
        payload = p.read_bytes()
        name = RENAMED.get(p.name, p.name)
        if (out / name).exists():
            if name == p.name and (out / name).read_bytes() == payload:
                continue  # the same file the current site publishes (fonts, licence text)
            raise ValueError(f'a preview file would replace a current file: {name}')
        plan[name] = payload
    for name in (PAGE, STYLE):
        if (out / name).exists() or name in plan:
            raise ValueError(f'a preview file would replace a current file: {name}')
    plan[PAGE] = page_html((NEW / 'index.html').read_text(encoding='utf-8')).encode('utf-8')
    plan[STYLE] = (PREVIEW / STYLE).read_bytes()
    for name, payload in plan.items():
        (out / name).write_bytes(payload)
    return sorted(plan)
