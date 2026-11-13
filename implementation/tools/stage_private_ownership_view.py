#!/usr/bin/env python3
"""Stage Codex company relationship views (#531 company-ownership-view/1) for the owner's authenticated delivery (owner 2026-11-13).

The private Worker serves /kis/classification?part=ownership_index and ?part=ownership_view|ownership_receipt&entity=<entity id> from
classification/ownership/ on the data branch of the private repository. This tool copies each handoff's view.json there BYTE FOR BYTE
(and an optional refresh-attempt receipt, the producer's five keys) after checking them, and writes Main's index
(company-ownership-delivery/1) naming every staged file's size and SHA-256. It computes, infers and fetches nothing.

  python implementation/tools/stage_private_ownership_view.py \
      --handoff <handoff dir with handoff-manifest.json and view.json> --handoff-manifest-sha256 <its SHA-256 as pinned> [repeat] \
      [--receipt <receipt.json> --receipt-sha256 <its SHA-256>] [repeat] --data-dir <private data checkout> [--synthetic]

Checks, all before anything is written:
- handoff-manifest.json's own SHA-256 equals its pin; it lists view.json with that file's size and SHA-256; every file is at most 2 MiB;
- view.json is company-ownership-view/1, publication PRIVATE (SYNTHETIC with --synthetic), its bytes the producer's canonical form
  (sorted-key compact JSON + newline), its centre a listed entity with company ids, one view per centre and per company id;
  --synthetic stages Codex's fictional views (publication PUBLIC_APPROVED) and marks the index SYNTHETIC;
- a receipt is exactly the producer's five keys, names the SHA-256 of one staged view's bytes and that view's unchanged generated and
  last-success times, and its attempt is later than the view; at most one receipt per view;
- --data-dir is outside this public repository.
classification/ownership/ is replaced whole or not at all; on any failure the existing copy stays. Output: one line with counts and
hashes (no content).
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
VIEW_SCHEMA = 'company-ownership-view/1'
INDEX_SCHEMA = 'company-ownership-delivery/1'
ENTITY = re.compile(r'^[A-Z0-9][A-Z0-9-]{0,31}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
RECEIPT_KEYS = {'attempt', 'retained_dataset_sha256', 'retained_view_sha256', 'unchanged_generated_at', 'unchanged_last_success_at'}
OUTCOMES = {'SUCCESS', 'FAILED', 'PARTIAL', 'PARSE_FAILED'}


class StageError(Exception):
    pass


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read(path: Path, name: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise StageError('FILE_MISSING:' + name)
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise StageError('FILE_TOO_LARGE:' + name)
    return data


def _json(data: bytes, name: str):
    try:
        return json.loads(data)
    except ValueError:
        raise StageError('NOT_JSON:' + name) from None


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


INSTANT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?(Z|[+-]\d{2}:\d{2})$')


def _time(value, name):
    # A time and an explicit zone (the producer's _instant); a date alone or a zoneless time is refused (Codex #437 6848164775).
    if not isinstance(value, str) or not INSTANT.match(value):
        raise StageError('RECEIPT_TIME:' + name)
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise StageError('RECEIPT_TIME:' + name) from None


def check_view(handoff: Path, pin: str, synthetic: bool) -> dict:
    if not isinstance(pin, str) or not HEX64.match(pin):
        raise StageError('PIN_INVALID')
    manifest_bytes = _read(handoff / 'handoff-manifest.json', 'handoff-manifest.json')
    if _sha(manifest_bytes) != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    manifest = _json(manifest_bytes, 'handoff-manifest.json')
    listed = {f.get('path'): f for f in (manifest.get('files') if isinstance(manifest, dict) and isinstance(manifest.get('files'), list) else []) if isinstance(f, dict)}
    view_bytes = _read(handoff / 'view.json', 'view.json')
    entry = listed.get('view.json')
    if not entry or entry.get('bytes') != len(view_bytes) or entry.get('sha256') != _sha(view_bytes):
        raise StageError('VIEW_NOT_LISTED')
    view = _json(view_bytes, 'view.json')
    if not isinstance(view, dict) or view.get('schema_version') != VIEW_SCHEMA:
        raise StageError('VIEW_SCHEMA')
    if view.get('publication') != ('PUBLIC_APPROVED' if synthetic else 'PRIVATE'):  # Codex's synthetic views are PUBLIC_APPROVED fiction
        raise StageError('VIEW_PUBLICATION')
    if canonical(view) != view_bytes:
        raise StageError('VIEW_NOT_CANONICAL')
    centre = (view.get('entity_context') or {}).get('entity_id')
    if not isinstance(centre, str) or not ENTITY.match(centre):
        raise StageError('VIEW_CENTRE')
    entity = next((e for e in view.get('entities') or [] if isinstance(e, dict) and e.get('entity_id') == centre), None)
    if not entity or not isinstance(entity.get('company_ids'), list) or not entity['company_ids'] or not all(isinstance(c, str) and c for c in entity['company_ids']):
        raise StageError('VIEW_COMPANY_IDS')
    if not isinstance(view.get('dataset_hash'), str) or not HEX64.match(view['dataset_hash']):
        raise StageError('VIEW_DATASET_HASH')
    return {'entity_id': centre, 'company_ids': list(entity['company_ids']), 'dataset_hash': view['dataset_hash'], 'bytes': view_bytes, 'view': view,
            'source': {'handoff_path': manifest.get('path') if isinstance(manifest.get('path'), str) else handoff.name, 'handoff_manifest_sha256': pin}}


def check_receipt(path: Path, pin: str, views: list) -> tuple:
    if not isinstance(pin, str) or not HEX64.match(pin):
        raise StageError('PIN_INVALID')
    data = _read(path, path.name)
    if _sha(data) != pin:
        raise StageError('RECEIPT_PIN_MISMATCH')
    r = _json(data, path.name)
    if not isinstance(r, dict) or set(r) != RECEIPT_KEYS or not isinstance(r['attempt'], dict) or set(r['attempt']) != {'attempted_at', 'outcome'}:
        raise StageError('RECEIPT_SCHEMA')
    if r['attempt']['outcome'] not in OUTCOMES or not HEX64.match(str(r['retained_view_sha256'])) or not HEX64.match(str(r['retained_dataset_sha256'])):
        raise StageError('RECEIPT_SCHEMA')
    view = next((v for v in views if _sha(v['bytes']) == r['retained_view_sha256']), None)
    if view is None:
        raise StageError('RECEIPT_VIEW_MISMATCH')
    collection = view['view'].get('collection') or {}
    if r['unchanged_generated_at'] != view['view'].get('generated_at') or r['unchanged_last_success_at'] != collection.get('last_success_at'):
        raise StageError('RECEIPT_VIEW_MISMATCH')
    if r['retained_dataset_sha256'] != view['dataset_hash']:
        raise StageError('RECEIPT_DATASET_MISMATCH')
    if not _time(r['attempt']['attempted_at'], 'attempted_at') > _time(view['view'].get('generated_at'), 'generated_at'):
        raise StageError('RECEIPT_TIME')
    return view['entity_id'], data


def build(handoffs: list, receipts: list, synthetic: bool) -> tuple:
    if not handoffs:
        raise StageError('NO_VIEW')
    views = [check_view(Path(d), pin, synthetic) for d, pin in handoffs]
    centres, codes = set(), set()
    for v in views:
        if v['entity_id'] in centres:
            raise StageError('DUPLICATE_CENTRE:' + v['entity_id'])
        centres.add(v['entity_id'])
        for c in v['company_ids']:
            if c in codes:
                raise StageError('DUPLICATE_COMPANY:' + c)
            codes.add(c)
    staged_receipts = {}
    for path, pin in receipts:
        entity, data = check_receipt(Path(path), pin, views)
        if entity in staged_receipts:
            raise StageError('DUPLICATE_RECEIPT:' + entity)
        staged_receipts[entity] = data
    index = {'schema_version': INDEX_SCHEMA, 'data_kind': 'SYNTHETIC' if synthetic else 'PRIVATE',
             'sources': [v['source'] for v in views], 'new_external_requests': 0,
             'views': [{'entity_id': v['entity_id'], 'company_ids': v['company_ids'], 'dataset_hash': v['dataset_hash'],
                        'view': {'size': len(v['bytes']), 'sha256': _sha(v['bytes'])},
                        'receipt': ({'size': len(staged_receipts[v['entity_id']]), 'sha256': _sha(staged_receipts[v['entity_id']])}
                                    if v['entity_id'] in staged_receipts else None)} for v in views]}
    files = {'ownership-index.json': (json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')}
    for v in views:
        files['views/' + v['entity_id'] + '.json'] = v['bytes']
    for entity, data in staged_receipts.items():
        files['receipts/' + entity + '.json'] = data
    return files, index


def stage(handoffs: list, receipts: list, data_dir: Path, synthetic: bool = False) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    files, index = build(handoffs, receipts, synthetic)
    target = data_dir / 'classification' / 'ownership'
    fresh, old = target.with_name('ownership.staging'), target.with_name('ownership.previous')
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        for name, data in files.items():
            out = fresh / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            if _sha(out.read_bytes()) != _sha(data):
                raise StageError('COPY_MISMATCH:' + name)
        if target.exists():
            target.rename(old)
        fresh.rename(target)
    except BaseException:
        if fresh.exists():
            shutil.rmtree(fresh)
        if old.exists() and not target.exists():
            old.rename(target)
        raise
    if old.exists():
        shutil.rmtree(old)
    return files, index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--handoff', action='append', default=[], type=Path)
    parser.add_argument('--handoff-manifest-sha256', action='append', default=[])
    parser.add_argument('--receipt', action='append', default=[], type=Path)
    parser.add_argument('--receipt-sha256', action='append', default=[])
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--synthetic', action='store_true')
    args = parser.parse_args(argv)
    try:
        if len(args.handoff) != len(args.handoff_manifest_sha256) or len(args.receipt) != len(args.receipt_sha256):
            raise StageError('PIN_COUNT')
        files, index = stage(list(zip(args.handoff, args.handoff_manifest_sha256)), list(zip(args.receipt, args.receipt_sha256)), args.data_dir, args.synthetic)
    except StageError as error:
        print('STAGE_PRIVATE_OWNERSHIP_VIEW refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_OWNERSHIP_VIEW kind=' + index['data_kind'] + ' views=' + str(len(index['views']))
          + ' receipts=' + str(sum(1 for v in index['views'] if v['receipt'])) + ' index sha256=' + _sha(files['ownership-index.json'])
          + ' ' + ' '.join(v['entity_id'] + ':' + v['view']['sha256'] for v in index['views']) + ' files=' + str(len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
