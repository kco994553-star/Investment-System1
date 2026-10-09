"""Validated producer snapshots -> Web schema-1 bundle -> atomic write.

The assembler validates, serializes and combines. It performs no calculation and never
reshapes upstream data. Contract violations raise; contract-valid outputs the Web cannot
represent (e.g. NOT_USABLE freshness) are published as NOT_AVAILABLE with a reason code.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Mapping

from ..product.web_mvp import validate_bundle
from .contract import SECTION_NAMES, validate_snapshot
from .errors import IdentityError
from .freshness import NOT_USABLE, classify, require_aware
from .registry import DEFAULT_REASON, INFRA_VERSION
from .serialization import canonical_bytes, canonical_sha256, sha256_hex

BUNDLE_CONTRACT = 'PRODUCER_BUNDLE'
BUNDLE_CONTRACT_VERSION = 1


def _meta(snap: dict, freshness: str) -> dict:
    return {'producer_id': snap['producer_id'], 'producer_version': snap['producer_version'],
            'data_state': snap['data_state'], 'freshness': freshness,
            'requested_as_of': snap['requested_as_of'], 'as_of': snap['as_of'],
            'generated_at': snap['generated_at'], 'expires_at': snap['expires_at'],
            'usable_until': snap.get('usable_until'), 'methodology': snap['methodology'],
            'synthetic': snap['synthetic'], 'validation': snap['validation'],
            'source_inputs': snap['provenance']['inputs'], 'data_sha256': snap['data_sha256'],
            'snapshot_sha256': canonical_sha256(snap), 'reason_code': snap.get('reason_code')}


def _envelope(snap: dict, freshness: str) -> dict:
    meta = _meta(snap, freshness)
    if snap['data_state'] == 'NOT_AVAILABLE':
        return {'state': 'NOT_AVAILABLE', 'as_of': None, 'source': None, 'reason': snap['reason'],
                'data': None, 'producer': meta}
    if freshness == NOT_USABLE:
        meta['reason_code'] = 'EXPIRED_NOT_USABLE'
        return {'state': 'NOT_AVAILABLE', 'as_of': None, 'source': None, 'reason': DEFAULT_REASON,
                'data': None, 'producer': meta}
    env = {'state': snap['data_state'], 'as_of': snap['as_of'], 'source': snap['provenance']['source'],
           'data': snap['data'], 'producer': meta}
    if snap['expires_at'] is not None:
        env['expires_at'] = snap['expires_at']
    return env


def assemble_bundle(companies: list[dict], snapshots: Mapping[str, dict], now: datetime) -> dict:
    """Deterministic: identical companies/snapshots/now produce byte-identical bundles."""
    require_aware(now)
    unknown = set(snapshots) - set(SECTION_NAMES)
    if unknown:
        raise IdentityError(f'unknown sections {sorted(unknown)}')
    missing = [s for s in SECTION_NAMES if s not in snapshots]
    if missing:
        raise IdentityError(f'every section needs an explicit snapshot (use NOT_AVAILABLE): {missing}')
    bundle = {'schema_version': 1, 'companies': [dict(c) for c in companies]}
    sections = {}
    for name in SECTION_NAMES:
        snap = validate_snapshot(snapshots[name])
        if snap['section'] != name:
            raise IdentityError(f'snapshot for {name} declares section {snap["section"]}')
        freshness = classify(snap, now)
        bundle[name] = _envelope(snap, freshness)
        sections[name] = {'state': bundle[name]['state'], 'freshness': freshness,
                          'producer_id': snap['producer_id'],
                          'reason_code': bundle[name]['producer']['reason_code'],
                          'snapshot_sha256': bundle[name]['producer']['snapshot_sha256']}
    bundle['producer_manifest'] = {'contract': BUNDLE_CONTRACT, 'version': BUNDLE_CONTRACT_VERSION,
                                   'assembler': INFRA_VERSION, 'assembled_at': now.isoformat(),
                                   'companies_sha256': canonical_sha256(bundle['companies']),
                                   'sections': sections}
    validate_bundle(bundle)  # existing Web schema-1 validator, unchanged semantics
    return bundle


def bundle_sha256(bundle: dict) -> str:
    return sha256_hex(canonical_bytes(bundle))


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)  # mkstemp creates 0600; published files are world-readable like other reports
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_bundle_atomic(bundle: dict, path) -> str:
    """Validate, then write canonical bytes + <name>.sha256. On any failure nothing is replaced."""
    validate_bundle(bundle)
    data = canonical_bytes(bundle)
    digest = sha256_hex(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, data)
    _atomic_write(path.with_name(path.name + '.sha256'), f'{digest}  {path.name}\n'.encode())
    return digest
