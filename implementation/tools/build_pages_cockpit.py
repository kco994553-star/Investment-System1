"""Export public cockpit metadata for Pages; never accept holdings or demo input."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.web_mvp import build, repository_bundle


def build_public_cockpit(out: Path) -> Path:
    out = Path(out)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError('Pages output must be an empty regular directory')
    bundle = repository_bundle()
    # Publication projection only. Immutable Frozen source and existing builder
    # remain unchanged; identity, membership, ranks and provenance are retained.
    universe = bundle['universe']['data']
    universe.pop('cutoff_mcap', None)
    for member in universe['members']:
        member.pop('mcap', None)
    return build(out, bundle=bundle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        build_public_cockpit(Path(args.out))
    except (OSError, ValueError):
        print('Pages public build failed', file=sys.stderr)
        return 1
    print('Pages public cockpit built')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
