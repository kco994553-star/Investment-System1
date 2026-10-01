"""Raw artifact persistence manifest + retention audit. Reuses RawDatasetStore manifests.

Nothing is moved, copied, uploaded or deleted. Per-artifact facts are derived from the existing
committed data/raw/manifests/*.json (not duplicated into git); the dataset manifest binds them
with a manifest-set digest and records every known storage location and its expiry.

acquired_at is the ingestion fetch time. It is NOT PIT availability: available_at stays
null here because the existing replay parsers derive it from the content (ingestion/manifest.py).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from .contract import parse_ts
from .freshness import require_aware
from .serialization import canonical_sha256, sha256_hex

CONTRACT = 'RAW_DATASET_PERSISTENCE'
VERSION = 1
AVAILABLE_AT_BASIS = 'PARSED_FROM_CONTENT_AT_REPLAY (manifest fetched_at is ingestion time, not PIT availability)'
LOCATION_KINDS = ('REPOSITORY', 'GITHUB_ACTIONS_ARTIFACT', 'GITHUB_ACTIONS_CACHE', 'GITHUB_RELEASE',
                  'OBJECT_STORAGE', 'LOCAL', 'OTHER')


def artifact_records(store_root) -> list[dict]:
    out = []
    for f in sorted((Path(store_root) / 'manifests').glob('*.json')):
        m = json.loads(f.read_text(encoding='utf-8'))
        out.append({'artifact_id': m['artifact_id'], 'source_kind': m['source_kind'], 'source_url': m['source_url'],
                    'acquired_at': m['fetched_at'], 'available_at': None, 'available_at_basis': AVAILABLE_AT_BASIS,
                    'sha256': m['sha256'], 'size': m['bytes'], 'content_type': m['content_type'],
                    'provenance': {'fetcher': m['fetcher'], 'http_status': m.get('http_status')}})
    return out


def manifest_set_sha256(records: list[dict]) -> str:
    """Order-independent binding of (artifact_id, sha256, size) for the whole dataset."""
    return canonical_sha256(sorted([r['artifact_id'], r['sha256'], r['size']] for r in records))


def verify_blobs(store_root, records: list[dict]) -> dict:
    """Recompute sha256/size for blobs that are present. Absent blobs are reported, not failed."""
    blobs = Path(store_root) / 'blobs'
    present = ok = 0
    mismatched = []
    for r in records:
        p = blobs / r['artifact_id'].replace(':', '__')
        if not p.is_file():
            continue
        present += 1
        body = p.read_bytes()
        if len(body) == r['size'] and sha256_hex(body) == r['sha256']:
            ok += 1
        else:
            mismatched.append(r['artifact_id'])
    status = 'BLOBS_NOT_PRESENT' if present == 0 else ('PASS' if not mismatched and present == len(records) else
                                                      'PARTIAL' if not mismatched else 'FAIL')
    return {'status': status, 'present': present, 'verified': ok, 'mismatched': mismatched, 'expected': len(records)}


def retention_audit(locations: list[dict], now: datetime) -> dict:
    """Deterministic: no threshold is invented. Reports remaining time per location and whether
    any verified, non-expiring complete copy exists."""
    require_aware(now)
    rows = []
    for loc in locations:
        if loc.get('kind') not in LOCATION_KINDS:
            raise ValueError(f'unknown storage location kind {loc.get("kind")!r}')
        exp = parse_ts(loc.get('expires_at'), 'expires_at', required=False)
        status = 'NO_EXPIRY' if exp is None else ('EXPIRED' if now >= exp else 'ACTIVE_UNTIL_EXPIRY')
        rows.append({'kind': loc['kind'], 'ref': loc.get('ref'), 'complete_blobs': bool(loc.get('complete_blobs')),
                     'verified': bool(loc.get('verified')), 'expires_at': loc.get('expires_at'), 'status': status,
                     'seconds_remaining': None if exp is None else max(0, int((exp - now).total_seconds()))})
    complete = [r for r in rows if r['complete_blobs'] and r['verified'] and r['status'] != 'EXPIRED']
    if any(r['status'] == 'NO_EXPIRY' for r in complete):
        overall = 'DURABLE_COPY_PRESENT'
    elif complete:
        overall = 'AT_RISK_ONLY_EXPIRING_COPIES'
    else:
        overall = 'NO_VERIFIED_COMPLETE_COPY'
    # With only expiring copies, the dataset is lost when the last complete copy expires.
    last = None if overall == 'DURABLE_COPY_PRESENT' else max(
        (r['expires_at'] for r in complete if r['expires_at']), default=None, key=lambda x: parse_ts(x, 'expires_at'))
    return {'evaluated_at': now.isoformat(), 'overall': overall, 'locations': rows,
            'loss_deadline_if_no_action': last}


def dataset_manifest(store_root, dataset_id: str, locations: list[dict], now: datetime,
                     integrity_binding: dict | None = None) -> dict:
    records = artifact_records(store_root)
    by_kind = Counter(r['source_kind'] for r in records)
    size_kind = Counter()
    for r in records:
        size_kind[r['source_kind']] += r['size']
    return {
        'contract': CONTRACT, 'version': VERSION, 'dataset_id': dataset_id,
        'n_artifacts': len(records), 'total_bytes': sum(r['size'] for r in records),
        'manifest_set_sha256': manifest_set_sha256(records),
        'artifact_record_source': 'implementation/data/raw/manifests/*.json via producers.raw_persistence.artifact_records',
        'record_fields': sorted(records[0]) if records else [],
        'available_at_basis': AVAILABLE_AT_BASIS,
        'by_source_kind': {k: {'n': by_kind[k], 'bytes': size_kind[k]} for k in sorted(by_kind)},
        'acquired_at_range': [min(r['acquired_at'] for r in records), max(r['acquired_at'] for r in records)] if records else None,
        'integrity_binding': integrity_binding,
        'local_blob_verification': verify_blobs(store_root, records),
        'storage_locations': locations,
        'retention': retention_audit(locations, now),
    }
