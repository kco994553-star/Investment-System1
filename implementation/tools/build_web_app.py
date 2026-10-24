"""Development build of the new frontend (docs/frontend_v2/FRONTEND_V2_PLAN.md): same public data files, new screens.

Runs the normal Pages build into an empty directory, removes the current frontend's files (every file that comes from
product/web_assets, plus the generated research.html / network.html pages), and copies product/web_app in. The public data
files the pipelines write (sec-qgv2.json and the rest) are left exactly as the normal build made them. Not used by any deploy
until the one-time switch.

Reuse (P1 plan A, Main decision 2026-10-24): an old web_assets script that the page loads and that has no file of the same
name in web_app is kept, byte-identical, so the old engines and readers run unchanged and keep their guard pins. A name present
in web_app always wins (screen-detail.js). Old files nothing references are still removed.

What the page loads (P2-1a, owner 2026-10-24 first paint): index.html loads only web_app files (the first screen: an old module
there fails the build); web_app/loader.js loads the rest after the first paint from its LOAD_ORDER literal, the one load list,
which this build reads. A listed name found in neither folder, a name loaded twice, an inline script, a name that is not a plain
local file name or a LOAD_ORDER that is not a literal of plain quoted names fails the build.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PRODUCT = TOOLS.parents[0] / 'src/investment_system/product'
OLD, NEW = PRODUCT / 'web_assets', PRODUCT / 'web_app'
GENERATED_OLD_PAGES = ('research.html', 'network.html')
FRONTEND_SUFFIXES = ('.html', '.css', '.js', '.woff2', '.txt', '.png', '.svg')
LOADER = 'loader.js'
_LOAD_ORDER = re.compile(r'const LOAD_ORDER=Object\.freeze\(\[(.*?)\]\);', re.S)
_QUOTED = re.compile(r"'([^'\\]*)'")


class _Refs(HTMLParser):
    """Script sources and link targets of a page, in document order."""

    def __init__(self):
        super().__init__()
        self.scripts, self.links = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'script':
            if not a.get('src'):
                raise ValueError('index.html has an inline script (CSP allows files only)')
            self.scripts.append(a['src'])
        elif tag == 'link' and a.get('href') and not a['href'].startswith('data:'):
            self.links.append(a['href'])


def _local_name(ref: str) -> str:
    if not ref or ref != Path(ref).name or ref.startswith('.') or any(c in ref for c in ':?#\\'):
        raise ValueError(f'index.html refers to something that is not a local file name: {ref}')
    return ref


def load_order(new: Path = NEW) -> list[str]:
    """loader.js LOAD_ORDER: the scripts the page loads after its first paint, in order (exactly one literal of quoted names)."""
    found = _LOAD_ORDER.findall((new / LOADER).read_text(encoding='utf-8'))
    if len(found) != 1:
        raise ValueError('loader.js must hold exactly one LOAD_ORDER literal')
    items = [item.strip() for item in found[0].split(',')]
    if items and items[-1] == '':
        items.pop()  # trailing comma
    names = []
    for item in items:
        m = _QUOTED.fullmatch(item)
        if not m:
            raise ValueError(f'loader.js LOAD_ORDER has an entry that is not a plain quoted name: {item[:40]!r}')
        names.append(m.group(1))
    return names


def _index_refs(new: Path) -> _Refs:
    refs = _Refs()
    refs.feed((new / 'index.html').read_text(encoding='utf-8'))
    refs.close()
    return refs


def page_scripts(new: Path = NEW) -> tuple[list[str], list[str]]:
    """(index.html scripts, loader.js LOAD_ORDER) as local file names; the second is empty when index.html loads no loader."""
    first = list(map(_local_name, _index_refs(new).scripts))
    if LOADER not in first and (new / LOADER).is_file():
        raise ValueError(f'index.html does not load {LOADER}, so its LOAD_ORDER would never load')
    later = [_local_name(n) for n in load_order(new)] if LOADER in first else []
    return first, later


def reused_old_files(new: Path = NEW, old: Path = OLD) -> list[str]:
    """Old scripts the page loads (plan A), in load order. web_app wins on a shared name; neither -> error."""
    first, later = page_scripts(new)
    keep, seen = [], set()
    for src in first:
        if src in seen:
            raise ValueError(f'index.html loads a script twice: {src}')
        seen.add(src)
        if not (new / src).is_file():
            raise ValueError(f'index.html loads a script that is not in web_app: {src} (old modules load after the first paint, from {LOADER} LOAD_ORDER)')
    for src in later:
        if not src.endswith('.js'):
            raise ValueError(f'{LOADER} LOAD_ORDER lists something that is not a script: {src}')
        if src in seen:
            raise ValueError(f'the page loads a script twice: {src}')
        seen.add(src)
        if (new / src).is_file():
            continue
        if not (old / src).is_file():
            raise ValueError(f'{LOADER} LOAD_ORDER lists a script found in neither web_app nor web_assets: {src}')
        keep.append(src)
    for href in map(_local_name, _index_refs(new).links):
        if not (new / href).is_file():
            raise ValueError(f'index.html links a file that is not in web_app: {href}')
    return keep


def build_web_app(out: Path) -> Path:
    sys.path.insert(0, str(TOOLS))
    from build_pages_cockpit import build_public_cockpit
    out = Path(out)
    keep = reused_old_files()  # before building, so a bad index.html or LOAD_ORDER fails without a half-made output
    build_public_cockpit(out)
    # Frontend files only: page, styles, scripts, fonts and their licence texts, icons, manifest. JSON is public data and stays.
    old = {p.name for p in OLD.iterdir() if p.is_file() and p.suffix in FRONTEND_SUFFIXES} | set(GENERATED_OLD_PAGES) | {'manifest.json'}
    for p in out.iterdir():
        if p.is_file() and p.name in old and p.name not in keep:
            p.unlink()
    for name in keep:
        if (out / name).read_bytes() != (OLD / name).read_bytes():
            raise ValueError(f'reused old script is not byte-identical in the build: {name}')
    for p in sorted(NEW.iterdir()):
        if p.is_file():
            if (out / p.name).exists():
                raise ValueError(f'new frontend file collides with a public data file: {p.name}')
            shutil.copyfile(p, out / p.name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', required=True, help='empty directory')
    args = parser.parse_args()
    try:
        build_web_app(Path(args.out))
    except (OSError, ValueError) as error:
        print(f'web app build failed: {error}', file=sys.stderr)
        return 1
    print('web app built')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
