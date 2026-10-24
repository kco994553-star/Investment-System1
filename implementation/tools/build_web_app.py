"""Development build of the new frontend (docs/frontend_v2/FRONTEND_V2_PLAN.md): same public data files, new screens.

Runs the normal Pages build into an empty directory, removes the current frontend's files (every file that comes from
product/web_assets, plus the generated research.html / network.html pages), and copies product/web_app in. The public data
files the pipelines write (sec-qgv2.json and the rest) are left exactly as the normal build made them. Not used by any deploy
until the one-time switch.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PRODUCT = TOOLS.parents[0] / 'src/investment_system/product'
OLD, NEW = PRODUCT / 'web_assets', PRODUCT / 'web_app'
GENERATED_OLD_PAGES = ('research.html', 'network.html')
FRONTEND_SUFFIXES = ('.html', '.css', '.js', '.woff2', '.txt', '.png', '.svg')


def build_web_app(out: Path) -> Path:
    sys.path.insert(0, str(TOOLS))
    from build_pages_cockpit import build_public_cockpit
    out = Path(out)
    build_public_cockpit(out)
    # Frontend files only: page, styles, scripts, fonts and their licence texts, icons, manifest. JSON is public data and stays.
    old = {p.name for p in OLD.iterdir() if p.is_file() and p.suffix in FRONTEND_SUFFIXES} | set(GENERATED_OLD_PAGES) | {'manifest.json'}
    for p in out.iterdir():
        if p.is_file() and p.name in old:
            p.unlink()
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
