#!/usr/bin/env python3
"""Stage one scope's full factor distribution (Codex qgv-dual-factor-distribution/1) beside its staged dual delivery (owner 2026-11-12).

The private Worker serves /kis/classification?part=dual_dist_manifest|dual_dist_index&scope=<scope> and
?part=dual_dist_detail&scope=<scope>&shard=<3 digits> from classification/dual/<scope>/distribution/ on the data branch of the
private repository (implementation/worker/src/index.js). This tool copies Codex's distribution there BYTE FOR BYTE after checking it.
It is separate from stage_private_dual_qgv.py and stage_private_dual_leaders.py on purpose: neither strict file set is widened
(Codex FACTOR_DISTRIBUTION.md, "a separate optional route; the old delivery/leader manifest allowlists are not broadened"). It
computes, ranks, bins and fetches nothing.

  python implementation/tools/stage_private_dual_distribution.py --distribution <dir with distribution-*.json> \
      --scope operating504|held1057 --manifest-sha256 <distribution-manifest.json's SHA-256 as the pinned handoff names it> \
      --data-dir <private data checkout>

Checks, all before anything is written:
- distribution-manifest.json's own SHA-256 equals --manifest-sha256; schema qgv-dual-factor-distribution-manifest/1; its scope is
  --scope and its data kind the staged delivery's; its display policy is stored-evaluation-deciles/1 (the reference-score
  candidate is research only, synthetic only, until the owner confirms it);
- the directory holds exactly the manifest's files plus the manifest; each has the manifest's size and SHA-256 and is at most 2 MiB;
- the index (qgv-dual-factor-distribution/1) names the same scope, data kind and policy, is a projection (no rank recalculated, filters
  do not change the population, no new score, additional factors add 0, no whole-market denominator or coverage), and repeats each
  staged board's identity (model, configuration and result hashes, populations, bindings) with the manifest's source results; its
  companies are the staged delivery's evaluation code rows; every part (qgv-dual-factor-distribution-part/1) is listed by a group,
  names only groups that list it, and carries no raw value;
- --data-dir is outside this public repository.
classification/dual/<scope>/distribution/ is replaced whole or not at all; on any failure the existing copy stays. Restaging the
delivery (stage_private_dual_qgv.py) replaces classification/dual/<scope>/ whole and drops this companion with it; it is staged again
after its delivery. Output: one line with counts, sizes and hashes (no content).

The 3/3/3 candidates (owner 2026-11-13; Codex #534) are staged with --set 333 under classification/dual-333/<scope>/ (the Worker's
&set=333), never over the reduced U1 / U2 / S1 delivery under classification/dual/<scope>/; the same checks, the same 2 MiB limit.
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
SETS = {'reduced': 'dual', '333': 'dual-333'}
MANIFEST = 'distribution-manifest.json'
INDEX = 'distribution-index.json'
PART = re.compile(r'^distribution-\d{3}\.json$')
STORED = 'stored-evaluation-deciles/1'
BOARD_KEYS = ('model_id', 'model_version', 'configuration_hash', 'result_hash', 'evaluation_population', 'reference_population', 'bindings',
              'normalization_version', 'engine_version', 'adapter_version')


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


def check(source: Path, scope: str, pin: str, data_dir: Path, set_: str = 'reduced') -> tuple:
    if set_ not in SETS:
        raise StageError('SET_UNKNOWN')
    if scope not in SCOPES:
        raise StageError('SCOPE_UNKNOWN')
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise StageError('PIN_INVALID')
    if not source.is_dir():
        raise StageError('DISTRIBUTION_MISSING')
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
    delivery_dir = data_dir / 'classification' / SETS[set_] / scope
    for name in ('manifest.json', 'summary.json', 'index.json'):
        if not (delivery_dir / name).is_file():
            raise StageError('DELIVERY_NOT_STAGED')
    staged = _json((delivery_dir / 'manifest.json').read_bytes(), 'manifest.json')
    m = _json(files[MANIFEST], MANIFEST)
    if (not isinstance(m, dict) or set(m) != {'schema_version', 'scope', 'data_kind', 'display_policy', 'source_results', 'files'}
            or m['schema_version'] != 'qgv-dual-factor-distribution-manifest/1' or m['scope'] != scope or m['data_kind'] != staged.get('data_kind')
            or not isinstance(m['files'], list) or not isinstance(m['source_results'], dict)):
        raise StageError('MANIFEST_SCHEMA')
    if m['display_policy'] != STORED:
        raise StageError('POLICY_NOT_CONFIRMED')
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
    if (not isinstance(index, dict) or index.get('schema_version') != 'qgv-dual-factor-distribution/1' or index.get('scope') != scope
            or index.get('data_kind') != m['data_kind'] or index.get('display_policy') != STORED or index.get('policy_state') != 'EXISTING_RULE'):
        raise StageError('INDEX_SCHEMA')
    if (index.get('rank_recalculated') is not False or index.get('filter_changes_population') is not False or index.get('complete_evaluation_rows') is not True
            or index.get('new_score_calculations') != 0 or index.get('additional_factor_score_contribution') != 0
            or index.get('whole_market_denominator', 0) is not None or index.get('whole_market_coverage', 0) is not None):
        raise StageError('NOT_PROJECTION')
    boards = (_json((delivery_dir / 'summary.json').read_bytes(), 'summary.json').get('boards') or {})
    if not isinstance(index.get('boards'), dict) or not index['boards'] or not set(index['boards']) <= set(boards) or set(m['source_results']) != set(index['boards']):
        raise StageError('BOARD_MISMATCH')
    for key, b in index['boards'].items():
        if not isinstance(b, dict) or any(b.get(k) != boards[key].get(k) for k in BOARD_KEYS):
            raise StageError('BOARD_MISMATCH:' + key)
        if m['source_results'][key] != {'result_hash': b.get('result_hash'), 'sha256': b.get('source_result_sha256')}:
            raise StageError('SOURCE_RESULT_MISMATCH:' + key)
    rows = (_json((delivery_dir / 'index.json').read_bytes(), 'index.json').get('rows') or [])
    want = sorted((r.get('company_id'), r.get('issuer_id'), r.get('security_id')) for r in rows if isinstance(r, dict))
    got = sorted((c.get('company_id'), c.get('issuer_id'), c.get('security_id')) for c in (index.get('companies') or []) if isinstance(c, dict))
    if not want or got != want or len(index.get('companies') or []) != len(rows):
        raise StageError('COMPANIES_MISMATCH')
    groups = index.get('groups')
    if (not isinstance(groups, list) or not groups or any(not isinstance(g, dict) or not isinstance(g.get('files'), list) or not g['files']
            or any(f not in listed or not PART.match(str(f)) for f in g['files']) for g in groups)
            or len({g.get('group_id') for g in groups}) != len(groups)):
        raise StageError('GROUPS_INVALID')
    files_of = {g['group_id']: set(g['files']) for g in groups}
    if set().union(*files_of.values()) != {n for n in listed if PART.match(n)}:
        raise StageError('PART_UNREFERENCED')
    for name in listed:
        if PART.match(name):
            part = _json(files[name], name)
            if not isinstance(part, dict) or part.get('schema_version') != 'qgv-dual-factor-distribution-part/1' or not isinstance(part.get('parts'), list):
                raise StageError('PART_SCHEMA:' + name)
            if any(not isinstance(q, dict) or name not in files_of.get(q.get('group_id'), ()) for q in part['parts']):
                raise StageError('PART_GROUP_MISMATCH:' + name)
            if _has_raw(part):
                raise StageError('RAW_VALUE_PRESENT:' + name)
    return files, m, index


def stage(source: Path, scope: str, pin: str, data_dir: Path, set_: str = 'reduced') -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    files, manifest, index = check(source, scope, pin, data_dir, set_)
    target = data_dir / 'classification' / SETS[set_] / scope / 'distribution'
    fresh, old = target.with_name('distribution.staging'), target.with_name('distribution.previous')
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
    parser.add_argument('--distribution', required=True, type=Path)
    parser.add_argument('--scope', required=True, choices=SCOPES)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--set', dest='set_', default='reduced', choices=sorted(SETS))
    args = parser.parse_args(argv)
    try:
        files, manifest, index = stage(args.distribution, args.scope, args.manifest_sha256, args.data_dir, args.set_)
    except StageError as error:
        print('STAGE_PRIVATE_DUAL_DISTRIBUTION refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_DUAL_DISTRIBUTION scope=' + args.scope + ' manifest sha256=' + hashlib.sha256(files[MANIFEST]).hexdigest()
          + ' policy=' + manifest['display_policy'] + ' models=' + ','.join(index['boards']) + ' groups=' + str(len(index['groups']))
          + ' companies=' + str(len(index['companies'])) + ' parts=' + str(sum(1 for k in files if PART.match(k))) + ' files=' + str(len(files))
          + ' bytes=' + str(sum(len(v) for v in files.values())) + ' max_file_bytes=' + str(max(len(v) for v in files.values()))
          + ' kind=' + manifest['data_kind'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
