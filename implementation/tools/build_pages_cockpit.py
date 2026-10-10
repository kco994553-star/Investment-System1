"""Export public cockpit metadata for Pages; never accept holdings or demo input."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.web_mvp import build, repository_bundle


def build_public_cockpit(out: Path, *, sec_m2_candidate=None) -> Path:
    out = Path(out)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError('Pages output must be an empty regular directory')
    bundle = repository_bundle()
    result = build(out, bundle=bundle, sec_m2_candidate=sec_m2_candidate)
    assets = Path(__file__).resolve().parents[1] / 'src/investment_system/product/web_assets'
    for name in ('manifest.json', 'icon-192.png', 'icon-512.png'):
        shutil.copyfile(assets / name, out / name)
    from public_screens_pipeline import emit
    emit(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--sec-m2-candidate', help='Explicit private M2 JSON, projected into price-free research candidates')
    args = parser.parse_args()
    try:
        from investment_system.product.sec_m2_candidates import load_candidates
        candidate = load_candidates(args.sec_m2_candidate) if args.sec_m2_candidate else None
        build_public_cockpit(Path(args.out), sec_m2_candidate=candidate)
    except (OSError, ValueError):
        print('Pages public build failed', file=sys.stderr)
        return 1
    print('Pages public cockpit built')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
