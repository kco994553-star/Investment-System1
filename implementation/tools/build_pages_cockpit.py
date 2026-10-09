"""Export public cockpit metadata for Pages; never accept holdings or demo input."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.web_mvp import build, repository_bundle
from investment_system.product.device_actual_catalog import (
    public_actual_catalog, reject_private_holdings, TARGET_SHA256, MAP_SHA256, THEME_SHA256,
)

TARGET_ASSETS = Path(__file__).resolve().parents[1] / 'src/investment_system/product/target_reference_assets'
TARGET_SOURCE_URL = ('https://raw.githubusercontent.com/kco994553-star/Investment-System1/'
                     'refs/heads/claude/investment-system-top500-validation-alrugm/'
                     'implementation/docs/portfolio_target_owner/TARGET_v0.yaml')


def target_reference_artifacts() -> tuple[bytes, str, str]:
    """Preflight immutable public provenance before the existing builder writes."""
    metadata = {'schema': 'PUBLIC_TARGET_REFERENCE/1',
        'role': 'PUBLIC_READ_ONLY_REFERENCE', 'source_url': TARGET_SOURCE_URL,
        'expected_target_root_sha256': TARGET_SHA256,
        'lineage': {'target_root_sha256': TARGET_SHA256,
            'identity_map_sha256': MAP_SHA256, 'theme_assignments_sha256': THEME_SHA256,
            'source_values_changed': False},
        'catalog': public_actual_catalog()}
    reject_private_holdings(metadata)
    raw = json.dumps(metadata, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    for name in ('target.html', 'target.css'):
        (TARGET_ASSETS / name).read_bytes()
    verifier = (TARGET_ASSETS / 'target.js').read_text(encoding='utf-8')
    marker = '__TARGET_METADATA_SHA256__'
    if verifier.count(marker) != 1:
        raise ValueError('TARGET metadata digest marker must appear exactly once')
    index = (TARGET_ASSETS.parent / 'web_assets/index.html').read_text(encoding='utf-8')
    link_marker = '<!-- PUBLIC_TARGET_REFERENCE_LINK -->'
    if index.count(link_marker) != 1:
        raise ValueError('Pages TARGET link marker must appear exactly once')
    index = index.replace(link_marker,
        '<a href="target.html">TARGET · 공개 참고 / Public reference</a>')
    return raw, verifier.replace(marker, hashlib.sha256(raw).hexdigest()), index


def build_public_cockpit(out: Path) -> Path:
    out = Path(out)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError('Pages output must be an empty regular directory')
    metadata, verifier, index = target_reference_artifacts()
    bundle = repository_bundle()
    # Publication projection only. Immutable Frozen source and existing builder
    # remain unchanged; identity, membership, ranks and provenance are retained.
    universe = bundle['universe']['data']
    universe.pop('cutoff_mcap', None)
    for member in universe['members']:
        member.pop('mcap', None)
    build(out, bundle=bundle)
    # This public source-checking route is intentionally not part of the generic
    # MVP builder or device app. Only its standalone CSP permits the fixed root.
    for name in ('target.html', 'target.css'):
        shutil.copyfile(TARGET_ASSETS / name, out / name)
    (out / 'index.html').write_text(index, encoding='utf-8')
    (out / 'target.js').write_text(verifier, encoding='utf-8')
    (out / 'target-reference.json').write_bytes(metadata)
    return out


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
