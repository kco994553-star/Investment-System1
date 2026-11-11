#!/usr/bin/env python3
"""Stage one scope's factor leaders companion (Codex qgv-dual-factor-leaders/1) beside its staged dual delivery (owner 2026-11-11).

The private Worker serves /kis/classification?part=dual_leaders_manifest|dual_leaders_index&scope=<scope> and
?part=dual_leaders_detail&scope=<scope>&shard=<3 digits> from classification/dual/<scope>/leaders/ on the data branch of the private
repository (implementation/worker/src/index.js). This tool copies Codex's companion there BYTE FOR BYTE after checking it. It is a
separate tool from stage_private_dual_qgv.py on purpose: the delivery's own strict file set is not widened (Codex DUAL_QGV.md,
"Do not put it through the existing strict delivery reader or silently widen its allowlist"). It computes, ranks and fetches nothing.

  python implementation/tools/stage_private_dual_leaders.py --leaders <dir with factor-leaders*.json> --scope operating504|held1057 \
      --manifest-sha256 <factor-leaders-manifest.json's SHA-256 as the pinned handoff manifest names it> --data-dir <private data checkout> \
      [--selection <dir with factor-leaders-selection*.json> --selection-manifest-sha256 <its manifest's SHA-256 as the handoff names it>]

Checks, all before anything is written:
- factor-leaders-manifest.json's own SHA-256 equals --manifest-sha256; schema qgv-dual-factor-leaders-manifest/1; its scope is --scope
  and its data kind the staged delivery's; its source_delivery_manifest_sha256 is the SHA-256 of the delivery manifest already staged
  at classification/dual/<scope>/manifest.json (the companion belongs to exactly that delivery);
- the directory holds exactly the manifest's files plus the manifest; each has the manifest's size and SHA-256 and is at most 2 MiB;
- the index (qgv-dual-factor-leaders/1) names the same scope, data kind and source, is a projection (projection_only, no rank
  recalculated, no whole-market denominator or coverage), and repeats each staged board's identity (model, configuration and result
  hashes, populations, bindings); every shard (qgv-dual-factor-leaders-detail/1) is listed and carries no raw value;
- --data-dir is outside this public repository;
- with --selection (Codex qgv-dual-factor-leaders-selection/1, #437 6795150039): its manifest has the pinned SHA-256, names this scope
  and data kind and pins THIS leaders manifest (source_leaders_manifest_sha256); the directory holds exactly the manifest and
  factor-leaders-selection.json with the listed size and SHA-256; the body names the same scope, leaders and delivery manifests, is a
  projection (no rank recalculated, no new score, no whole market) and lists exactly the leaders index's groups. It is staged in the
  same leaders/ directory.
classification/dual/<scope>/leaders/ is replaced whole or not at all; on any failure the existing copy stays. Restaging the delivery
(stage_private_dual_qgv.py) replaces classification/dual/<scope>/ whole and so drops this companion with it: a companion pins one
delivery manifest, so it is staged again after its delivery. Output: one line with counts, sizes and hashes (no content).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
SCOPES = ('operating504', 'held1057')
MANIFEST = 'factor-leaders-manifest.json'
INDEX = 'factor-leaders.json'
SHARD = re.compile(r'^factor-leaders-\d{3}\.json$')
BOARD_KEYS = ('model_id', 'model_version', 'configuration_hash', 'result_hash', 'evaluation_population', 'reference_population', 'bindings')


class StageError(Exception):
    pass


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _json(data: bytes, name: str):
    try:
        return json.loads(data)
    except ValueError:
        raise StageError('NOT_JSON:' + name) from None


def _has_raw(o) -> bool:
    if isinstance(o, dict):
        return 'raw_value' in o or any(_has_raw(v) for v in o.values())
    if isinstance(o, list):
        return any(_has_raw(v) for v in o)
    return False


def check(leaders: Path, scope: str, pin: str, data_dir: Path) -> tuple:
    if scope not in SCOPES:
        raise StageError('SCOPE_UNKNOWN')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise StageError('PIN_INVALID')
    if not leaders.is_dir():
        raise StageError('LEADERS_MISSING')
    files = {}
    for p in sorted(leaders.iterdir()):
        if p.is_symlink() or not p.is_file():
            raise StageError('ENTRY_REFUSED:' + p.name)
        data = p.read_bytes()
        if len(data) > MAX_BYTES:
            raise StageError('FILE_TOO_LARGE:' + p.name)
        files[p.name] = data
    if MANIFEST not in files:
        raise StageError('MANIFEST_MISSING')
    if hashlib.sha256(files[MANIFEST]).hexdigest() != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    delivery_dir = data_dir / 'classification' / 'dual' / scope
    if not (delivery_dir / 'manifest.json').is_file() or not (delivery_dir / 'summary.json').is_file():
        raise StageError('DELIVERY_NOT_STAGED')
    delivery_manifest = (delivery_dir / 'manifest.json').read_bytes()
    staged = _json(delivery_manifest, 'manifest.json')
    m = _json(files[MANIFEST], MANIFEST)
    if (not isinstance(m, dict) or set(m) != {'schema_version', 'scope', 'data_kind', 'source_delivery_manifest_sha256', 'files'}
            or m['schema_version'] != 'qgv-dual-factor-leaders-manifest/1' or m['scope'] != scope or m['data_kind'] != staged.get('data_kind')
            or not isinstance(m['files'], list)):
        raise StageError('MANIFEST_SCHEMA')
    if m['source_delivery_manifest_sha256'] != hashlib.sha256(delivery_manifest).hexdigest():
        raise StageError('SOURCE_DELIVERY_MISMATCH')
    listed = {}
    for f in m['files']:
        if (not isinstance(f, dict) or set(f) != {'path', 'size', 'sha256'} or not (f['path'] == INDEX or SHARD.match(str(f['path'])))
                or f['path'] in listed):
            raise StageError('MANIFEST_FILES')
        listed[f['path']] = f
    if INDEX not in listed or set(files) != set(listed) | {MANIFEST}:
        raise StageError('FILE_SET_MISMATCH')
    for name, f in listed.items():
        if len(files[name]) != f['size'] or hashlib.sha256(files[name]).hexdigest() != f['sha256']:
            raise StageError('FILE_MISMATCH:' + name)
    index = _json(files[INDEX], INDEX)
    if (not isinstance(index, dict) or index.get('schema_version') != 'qgv-dual-factor-leaders/1' or index.get('scope') != scope
            or index.get('data_kind') != m['data_kind'] or index.get('source_delivery_manifest_sha256') != m['source_delivery_manifest_sha256']):
        raise StageError('INDEX_SCHEMA')
    if (index.get('projection_only') is not True or index.get('rank_recalculated') is not False
            or index.get('whole_market_denominator', 0) is not None or index.get('whole_market_coverage', 0) is not None):
        raise StageError('NOT_PROJECTION')
    boards = (_json((delivery_dir / 'summary.json').read_bytes(), 'summary.json').get('boards') or {})
    if not isinstance(index.get('boards'), dict) or set(index['boards']) != set(boards):
        raise StageError('BOARD_MISMATCH')
    for key, b in index['boards'].items():
        if not isinstance(b, dict) or any(b.get(k) != boards[key].get(k) for k in BOARD_KEYS):
            raise StageError('BOARD_MISMATCH:' + key)
    groups = index.get('groups')
    if not isinstance(groups, list) or any(not isinstance(g, dict) or g.get('file') not in listed or not SHARD.match(str(g.get('file'))) for g in groups):
        raise StageError('GROUPS_INVALID')
    if {g['file'] for g in groups} != {n for n in listed if SHARD.match(n)}:
        raise StageError('SHARD_UNREFERENCED')
    for name in listed:
        if SHARD.match(name):
            shard = _json(files[name], name)
            if not isinstance(shard, dict) or shard.get('schema_version') != 'qgv-dual-factor-leaders-detail/1' or not isinstance(shard.get('groups'), list):
                raise StageError('SHARD_SCHEMA:' + name)
            if _has_raw(shard):
                raise StageError('RAW_VALUE_PRESENT:' + name)
    return files, m, index


SEL_MANIFEST = 'factor-leaders-selection-manifest.json'
SEL_FILE = 'factor-leaders-selection.json'


def check_selection(selection: Path, pin: str, scope: str, files: dict, manifest: dict, index: dict) -> dict:
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise StageError('SELECTION_PIN_INVALID')
    if not selection.is_dir():
        raise StageError('SELECTION_MISSING')
    got = {}
    for p in sorted(selection.iterdir()):
        if p.is_symlink() or not p.is_file():
            raise StageError('ENTRY_REFUSED:' + p.name)
        data = p.read_bytes()
        if len(data) > MAX_BYTES:
            raise StageError('FILE_TOO_LARGE:' + p.name)
        got[p.name] = data
    if set(got) != {SEL_MANIFEST, SEL_FILE}:
        raise StageError('SELECTION_FILE_SET_MISMATCH')
    if hashlib.sha256(got[SEL_MANIFEST]).hexdigest() != pin:
        raise StageError('SELECTION_PIN_MISMATCH')
    m = _json(got[SEL_MANIFEST], SEL_MANIFEST)
    leaders_sha = hashlib.sha256(files[MANIFEST]).hexdigest()
    if (not isinstance(m, dict) or set(m) != {'schema_version', 'scope', 'data_kind', 'source_leaders_manifest_sha256', 'files'}
            or m['schema_version'] != 'qgv-dual-factor-leaders-selection-manifest/1' or m['scope'] != scope or m['data_kind'] != manifest['data_kind']):
        raise StageError('SELECTION_MANIFEST_SCHEMA')
    if m['source_leaders_manifest_sha256'] != leaders_sha:
        raise StageError('SELECTION_SOURCE_MISMATCH')
    if (not isinstance(m['files'], list) or len(m['files']) != 1 or not isinstance(m['files'][0], dict) or m['files'][0].get('path') != SEL_FILE
            or m['files'][0].get('size') != len(got[SEL_FILE]) or m['files'][0].get('sha256') != hashlib.sha256(got[SEL_FILE]).hexdigest()):
        raise StageError('SELECTION_FILE_MISMATCH')
    x = _json(got[SEL_FILE], SEL_FILE)
    if (not isinstance(x, dict) or x.get('schema_version') != 'qgv-dual-factor-leaders-selection/1' or x.get('scope') != scope
            or x.get('data_kind') != manifest['data_kind'] or x.get('source_leaders_manifest_sha256') != leaders_sha
            or x.get('source_delivery_manifest_sha256') != manifest['source_delivery_manifest_sha256']):
        raise StageError('SELECTION_SCHEMA')
    if (x.get('rank_recalculated') is not False or x.get('new_score_calculations') != 0 or x.get('additional_factor_score_contribution') != 0
            or x.get('whole_market_denominator', 0) is not None or x.get('whole_market_coverage', 0) is not None):
        raise StageError('SELECTION_NOT_PROJECTION')
    if not isinstance(x.get('groups'), list) or sorted(g.get('group_id') for g in x['groups'] if isinstance(g, dict)) != sorted(g['group_id'] for g in index['groups']):
        raise StageError('SELECTION_GROUPS_MISMATCH')
    if _has_raw(x):
        raise StageError('RAW_VALUE_PRESENT:' + SEL_FILE)
    return got


def stage(leaders: Path, scope: str, pin: str, data_dir: Path, selection: Path = None, selection_pin: str = None) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if (selection is None) != (selection_pin is None):
        raise StageError('SELECTION_PIN_REQUIRED')
    files, manifest, index = check(leaders, scope, pin, data_dir)
    if selection is not None:
        files = {**files, **check_selection(selection, selection_pin, scope, files, manifest, index)}
    target = data_dir / 'classification' / 'dual' / scope / 'leaders'
    fresh, old = target.with_name('leaders.staging'), target.with_name('leaders.previous')
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        fresh.mkdir(parents=True)
        for name, data in files.items():
            out = fresh / name
            out.write_bytes(data)
            if hashlib.sha256(out.read_bytes()).digest() != hashlib.sha256(data).digest():
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
    return files, manifest, index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--leaders', required=True, type=Path)
    parser.add_argument('--scope', required=True, choices=SCOPES)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--selection-manifest-sha256')
    args = parser.parse_args(argv)
    try:
        files, manifest, index = stage(args.leaders, args.scope, args.manifest_sha256, args.data_dir, args.selection, args.selection_manifest_sha256)
    except StageError as error:
        print('STAGE_PRIVATE_DUAL_LEADERS refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_DUAL_LEADERS scope=' + args.scope + ' manifest sha256=' + hashlib.sha256(files[MANIFEST]).hexdigest()
          + ' source_delivery_manifest sha256=' + manifest['source_delivery_manifest_sha256'] + ' models=' + ','.join(index['boards'])
          + ' groups=' + str(len(index['groups'])) + ' shards=' + str(sum(1 for k in files if SHARD.match(k))) + ' files=' + str(len(files))
          + (' selection manifest sha256=' + hashlib.sha256(files[SEL_MANIFEST]).hexdigest() if SEL_MANIFEST in files else ' selection=NONE')
          + ' bytes=' + str(sum(len(v) for v in files.values())) + ' max_file_bytes=' + str(max(len(v) for v in files.values()))
          + ' kind=' + manifest['data_kind'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
