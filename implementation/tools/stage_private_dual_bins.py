#!/usr/bin/env python3
"""Stage one scope's all-bin routing (Codex qgv-dual-factor-bins/1) beside its staged full factor distribution (owner 2026-11-12).

The private Worker serves /kis/classification?part=dual_bins_manifest|dual_bins_index&scope=<scope> and
?part=dual_bins_detail&scope=<scope>&shard=<3 digits> from classification/dual/<scope>/bins/ on the data branch of the private
repository. This tool copies Codex's routing there BYTE FOR BYTE after checking it against the distribution already staged at
classification/dual/<scope>/distribution/ (stage_private_dual_distribution.py). It computes, ranks, bins and fetches nothing.

  python implementation/tools/stage_private_dual_bins.py --bins <dir with bin-*.json / bins-*.json> --scope operating504|held1057 \
      --manifest-sha256 <bin-manifest.json's SHA-256 as the pinned handoff names it> --data-dir <private data checkout>

Checks, all before anything is written:
- bin-manifest.json's own SHA-256 equals --manifest-sha256; schema qgv-dual-factor-bins-manifest/1; its scope is --scope and its data
  kind the staged distribution's; its source_manifest_sha256 is the SHA-256 of the staged distribution-manifest.json;
- the directory holds exactly the manifest's files plus the manifest; each has the manifest's size and SHA-256 and is at most 2 MiB;
- the index (qgv-dual-factor-bins/1) names the same scope, data kind, stored policy and source manifest / index descriptors, repeats
  the staged distribution's boards, adds no score, does not change the population and claims no whole market; it routes every staged
  distribution group exactly once to a listed bins file, and every listed bins file holds a routed group;
- every bins file (qgv-dual-factor-bins-part/1) holds exactly the groups routed there, with ten bins whose member files are
  descriptors of the staged distribution files; no raw value;
- --data-dir is outside this public repository.
classification/dual/<scope>/bins/ is replaced whole or not at all; on any failure the existing copy stays. Restaging the
distribution leaves this routing pointing at the old manifest; the reader then refuses it until the routing is staged again.
Output: one line with counts, sizes and hashes (no content).
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
MANIFEST = 'bin-manifest.json'
INDEX = 'bin-index.json'
PART = re.compile(r'^bins-\d{3}\.json$')
STORED = 'stored-evaluation-deciles/1'


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


def check(source: Path, scope: str, pin: str, data_dir: Path) -> tuple:
    if scope not in SCOPES:
        raise StageError('SCOPE_UNKNOWN')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise StageError('PIN_INVALID')
    if not source.is_dir():
        raise StageError('BINS_MISSING')
    files = {}
    for p in sorted(source.iterdir()):
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
    dist_dir = data_dir / 'classification' / 'dual' / scope / 'distribution'
    if not (dist_dir / 'distribution-manifest.json').is_file() or not (dist_dir / 'distribution-index.json').is_file():
        raise StageError('DISTRIBUTION_NOT_STAGED')
    dist_manifest_bytes = (dist_dir / 'distribution-manifest.json').read_bytes()
    dist_manifest = _json(dist_manifest_bytes, 'distribution-manifest.json')
    dist_index = _json((dist_dir / 'distribution-index.json').read_bytes(), 'distribution-index.json')
    dist_files = {f['path']: f for f in dist_manifest.get('files', [])}
    m = _json(files[MANIFEST], MANIFEST)
    if (not isinstance(m, dict) or set(m) != {'schema_version', 'scope', 'data_kind', 'source_manifest_sha256', 'files'}
            or m['schema_version'] != 'qgv-dual-factor-bins-manifest/1' or m['scope'] != scope or m['data_kind'] != dist_manifest.get('data_kind')
            or not isinstance(m['files'], list)):
        raise StageError('MANIFEST_SCHEMA')
    if m['source_manifest_sha256'] != hashlib.sha256(dist_manifest_bytes).hexdigest():
        raise StageError('SOURCE_DISTRIBUTION_MISMATCH')
    listed = {}
    for f in m['files']:
        if (not isinstance(f, dict) or set(f) != {'path', 'size', 'sha256'} or not (f['path'] == INDEX or PART.match(str(f['path'])))
                or f['path'] in listed):
            raise StageError('MANIFEST_FILES')
        listed[f['path']] = f
    if INDEX not in listed or set(files) != set(listed) | {MANIFEST}:
        raise StageError('FILE_SET_MISMATCH')
    for name, f in listed.items():
        if len(files[name]) != f['size'] or hashlib.sha256(files[name]).hexdigest() != f['sha256']:
            raise StageError('FILE_MISMATCH:' + name)
    index = _json(files[INDEX], INDEX)
    if (not isinstance(index, dict) or index.get('schema_version') != 'qgv-dual-factor-bins/1' or index.get('scope') != scope
            or index.get('data_kind') != m['data_kind'] or index.get('display_policy') != STORED):
        raise StageError('INDEX_SCHEMA')
    if ((index.get('source_distribution_manifest') or {}).get('sha256') != m['source_manifest_sha256']
            or index.get('source_index') != dist_files.get('distribution-index.json') or index.get('boards') != dist_index.get('boards')):
        raise StageError('SOURCE_DISTRIBUTION_MISMATCH')
    if (index.get('new_score_calculations') != 0 or index.get('additional_factor_score_contribution') != 0 or index.get('filter_changes_population') is not False
            or index.get('whole_market_denominator', 0) is not None or index.get('whole_market_coverage', 0) is not None):
        raise StageError('NOT_PROJECTION')
    groups = {g['group_id'] for g in dist_index.get('groups', [])}
    routes = index.get('groups')
    if (not isinstance(routes, list) or sorted(r.get('group_id') for r in routes if isinstance(r, dict)) != sorted(groups)
            or any(r.get('path') not in listed or not PART.match(str(r.get('path'))) for r in routes)):
        raise StageError('ROUTES_INVALID')
    where = {r['group_id']: r['path'] for r in routes}
    if set(where.values()) != {n for n in listed if PART.match(n)}:
        raise StageError('PART_UNREFERENCED')
    for name in listed:
        if PART.match(name):
            part = _json(files[name], name)
            if not isinstance(part, dict) or part.get('schema_version') != 'qgv-dual-factor-bins-part/1' or not isinstance(part.get('groups'), list):
                raise StageError('PART_SCHEMA:' + name)
            if sorted(g.get('group_id') for g in part['groups'] if isinstance(g, dict)) != sorted(k for k, v in where.items() if v == name):
                raise StageError('PART_GROUP_MISMATCH:' + name)
            for g in part['groups']:
                for b in g.get('bins') or []:
                    if any(not isinstance(f, dict) or dist_files.get(f.get('path')) != f for f in b.get('member_files') or []):
                        raise StageError('MEMBER_FILE_MISMATCH:' + name)
            if _has_raw(part):
                raise StageError('RAW_VALUE_PRESENT:' + name)
    return files, m, index


def stage(source: Path, scope: str, pin: str, data_dir: Path) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    files, manifest, index = check(source, scope, pin, data_dir)
    target = data_dir / 'classification' / 'dual' / scope / 'bins'
    fresh, old = target.with_name('bins.staging'), target.with_name('bins.previous')
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
    parser.add_argument('--bins', required=True, type=Path)
    parser.add_argument('--scope', required=True, choices=SCOPES)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        files, manifest, index = stage(args.bins, args.scope, args.manifest_sha256, args.data_dir)
    except StageError as error:
        print('STAGE_PRIVATE_DUAL_BINS refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_DUAL_BINS scope=' + args.scope + ' manifest sha256=' + hashlib.sha256(files[MANIFEST]).hexdigest()
          + ' source_distribution_manifest sha256=' + manifest['source_manifest_sha256'] + ' groups=' + str(len(index['groups']))
          + ' parts=' + str(sum(1 for k in files if PART.match(k))) + ' files=' + str(len(files))
          + ' bytes=' + str(sum(len(v) for v in files.values())) + ' max_file_bytes=' + str(max(len(v) for v in files.values()))
          + ' kind=' + manifest['data_kind'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
