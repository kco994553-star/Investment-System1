#!/usr/bin/env python3
"""Stage one scope of Codex #529's dual research delivery (qgv-dual-delivery/1) for the owner-checked private Worker (owner 2026-11-11).

The private Worker serves /kis/classification?part=dual_manifest|dual_summary|dual_index&scope=<scope> and
?part=dual_detail&scope=<scope>&shard=<3 digits> from the data branch of the private repository, under classification/dual/<scope>/
(implementation/worker/src/index.js). This tool copies Codex's delivery there BYTE FOR BYTE after checking it. It computes no score,
re-serializes nothing and fetches nothing.

  python implementation/tools/stage_private_dual_qgv.py --delivery <delivery/<scope> dir> --scope operating504|held1057 \
      --manifest-sha256 <that manifest's SHA-256 as the pinned handoff manifest names it> --data-dir <private data branch checkout> \
      [--input-lineage <input-lineage.json> --input-lineage-sha256 <its SHA-256 as the pinned handoff manifest names it>]   (held1057: required,
      or --unverified to stage it explicitly unverified)

Checks, all before anything is written:
- manifest.json's own SHA-256 equals --manifest-sha256 (the pin; the files' own hashes alone prove nothing), its schema is
  qgv-dual-delivery-manifest/1 and its scope is --scope;
- the directory holds exactly the manifest's files plus manifest.json; each file has the manifest's size and SHA-256 and is at most
  2 MiB (the Worker's bound, unchanged);
- summary (qgv-dual-delivery/1, PRIVATE_RESEARCH, boards U1 / U2 / S1 with their model ids, NOT_ADOPTED, NOT_MEASURED), index
  (qgv-dual-index/1) and every detail (qgv-dual-detail/1) carry their schema; no detail factor carries a raw value;
- the evaluation population is the result already staged in classification/expanded/coverage.json: the coverage scope (operating
  for operating504, held_financial_subsample for held1057) with the same population id / version / members hash / denominator and
  evaluation day, and the same input hash (operating504: the evaluation input; held1057: the reference source input);
- --data-dir is outside this public repository;
- held1057 only, with --input-lineage: the producer's projection proof (qgv-dual-input-projection-proof/1, Codex 2026-11-11) has
  the pinned SHA-256 and names exactly this delivery: its evaluation is every board's evaluation population, its reference source is
  every board's reference binding (same input hash as the reference population), it selects evaluation.issuers issuers, changes no
  row value or classification and only the projection fields, and claims no whole-market denominator and no new score. It is then
  staged beside the delivery as input-lineage.json and the evaluation input is reported ATTESTED (by the producer's proof; nothing
  here recomputes the projection). Without it, held1057 stays REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED.
classification/dual/<scope>/ is replaced whole or not at all; on any failure the existing copy stays. A later restage of
classification/ (stage_private_classification.py) replaces the directory whole, so this delivery is staged again after it.
Output: one line with counts, sizes and hashes (no content).

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
SCOPES = {'operating504': ('operating', 'evaluation'), 'held1057': ('held_financial_subsample', 'reference')}
MODELS = {'U1': 'unified-roa-core/0.1.0', 'U2': 'unified-sales-core/0.1.0', 'S1': 'sector-reduced-core/0.1.0'}
# The 3/3/3 boards (Codex #534 qgv-333-contract/1): staged only with --set 333, and a set holds only its own boards (never mixed).
MODELS_333 = {'U2-333': 'unified-333-eps/0.1.0', 'U1-333': 'unified-333-persistence/0.1.0', 'S1-333': 'sector-333/0.1.0'}
SETS = {'reduced': ('dual', MODELS), '333': ('dual-333', MODELS_333)}
# operating504's evaluation input is the staged result's own input; held1057 is tied by its reference source input only, so its
# evaluation input is reported UNVERIFIED (owner 2026-11-11 §2) until the producer gives the evaluation input's derivation.
INPUT_CHECK = {'evaluation': 'EVALUATION_INPUT_MATCHED', 'reference': 'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED'}
ATTESTED = 'EVALUATION_INPUT_PROJECTION_ATTESTED'
LINEAGE_SCHEMA = 'qgv-dual-input-projection-proof/1'
LINEAGE_FILE = 'input-lineage.json'
PROJECTION_FIELDS = ['members', 'rows', 'snapshot_id', 'universe_id', 'universe_version']
HEX = re.compile(r'^[0-9a-f]{64}$')
FILE = re.compile(r'^(summary|index)\.json$|^detail-\d{3}\.json$')


class StageError(Exception):
    pass


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _pin(value: str, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise StageError(code)
    return value


def _json(data: bytes, name: str):
    try:
        return json.loads(data)
    except ValueError:
        raise StageError('NOT_JSON:' + name) from None


def check(delivery: Path, scope: str, pin: str, data_dir: Path, set_: str = 'reduced', input_anchored: bool = False) -> tuple:
    if scope not in SCOPES:
        raise StageError('SCOPE_UNKNOWN')
    if set_ not in SETS:
        raise StageError('SET_UNKNOWN')
    models = SETS[set_][1]
    _pin(pin, 'PIN_INVALID')
    if not delivery.is_dir():
        raise StageError('DELIVERY_MISSING')
    files = {}
    for p in sorted(delivery.iterdir()):
        if p.is_symlink() or not p.is_file():
            raise StageError('ENTRY_REFUSED:' + p.name)
        data = p.read_bytes()
        if len(data) > MAX_BYTES:
            raise StageError('FILE_TOO_LARGE:' + p.name)
        files[p.name] = data
    if 'manifest.json' not in files:
        raise StageError('MANIFEST_MISSING')
    if hashlib.sha256(files['manifest.json']).hexdigest() != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    manifest = _json(files['manifest.json'], 'manifest.json')
    if (not isinstance(manifest, dict) or manifest.get('schema_version') != 'qgv-dual-delivery-manifest/1' or manifest.get('scope') != scope
            or manifest.get('data_kind') not in ('PRIVATE', 'SYNTHETIC') or not isinstance(manifest.get('files'), list)):
        raise StageError('MANIFEST_SCHEMA')
    listed = {}
    for f in manifest['files']:
        if not isinstance(f, dict) or set(f) != {'path', 'size', 'sha256'} or not FILE.match(str(f['path'])) or f['path'] in listed:
            raise StageError('MANIFEST_FILES')
        listed[f['path']] = f
    if set(files) != set(listed) | {'manifest.json'}:
        raise StageError('FILE_SET_MISMATCH')
    for name, f in listed.items():
        if len(files[name]) != f['size'] or hashlib.sha256(files[name]).hexdigest() != f['sha256']:
            raise StageError('FILE_MISMATCH:' + name)
    summary = _json(files['summary.json'], 'summary.json')
    boards = summary.get('boards') if isinstance(summary, dict) else None
    if (summary.get('schema_version') != 'qgv-dual-delivery/1' or summary.get('visibility') != 'PRIVATE_RESEARCH' or not isinstance(boards, dict)
            or not boards or any(k not in models or not isinstance(b, dict) or b.get('model_id') != models[k] or b.get('operating_adoption') != 'NOT_ADOPTED'
                                 or b.get('performance_state') != 'NOT_MEASURED' for k, b in boards.items())):
        raise StageError('SUMMARY_SCHEMA')
    evaluations = [b.get('evaluation_population') for b in boards.values()]
    if any(e != evaluations[0] for e in evaluations) or not isinstance(evaluations[0], dict):
        raise StageError('EVALUATION_MISMATCH')
    if _json(files['index.json'], 'index.json').get('schema_version') != 'qgv-dual-index/1':
        raise StageError('INDEX_SCHEMA')
    for name in listed:
        if name.startswith('detail-'):
            detail = _json(files[name], name)
            if detail.get('schema_version') != 'qgv-dual-detail/1' or not isinstance(detail.get('rows'), list):
                raise StageError('DETAIL_SCHEMA:' + name)
            for row in detail['rows']:
                for b in (row.get('boards') or {}).values():
                    if any(isinstance(f, dict) and 'raw_value' in f for f in (b.get('factors') or {}).values()):
                        raise StageError('RAW_VALUE_PRESENT:' + name)
    coverage_path = data_dir / 'classification' / 'expanded' / 'coverage.json'
    if not coverage_path.is_file():
        raise StageError('COVERAGE_NOT_STAGED')
    anchor_scope, input_side = SCOPES[scope]
    context = (_json(coverage_path.read_bytes(), 'coverage.json').get('scopes', {}).get(anchor_scope) or {}).get('context') or {}
    population, identity, ev = context.get('population') or {}, context.get('result_identity') or {}, evaluations[0]
    if (population.get('id') != ev.get('id') or population.get('version') != ev.get('version') or population.get('members_hash') != ev.get('members_hash')
            or population.get('denominator') != ev.get('code_rows')):
        raise StageError('POPULATION_MISMATCH')
    if context.get('valuation_date') != ev.get('valuation_date'):
        raise StageError('DATE_MISMATCH')
    # A 3/3/3 delivery with the producer's two independent input anchors (qgv-dual-input-anchors/1, checked by the switch tool)
    # carries its own input version: the population and day above stay the bundle's, the input hash is the anchors' to bind.
    for key, b in ({} if input_anchored else boards).items():
        side = b.get('evaluation_population') if input_side == 'evaluation' else b.get('reference_population')
        if not isinstance(side, dict) or side.get('input_hash') != identity.get('input_hash'):
            raise StageError('INPUT_MISMATCH:' + key)
    return files, manifest, summary


def check_lineage(path: Path, pin: str, scope: str, summary: dict) -> bytes:
    if SCOPES[scope][1] != 'reference':
        raise StageError('LINEAGE_NOT_APPLICABLE')
    _pin(pin, 'LINEAGE_PIN_INVALID')
    if path.is_symlink() or not path.is_file():
        raise StageError('LINEAGE_MISSING')
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise StageError('FILE_TOO_LARGE:' + LINEAGE_FILE)
    if hashlib.sha256(data).hexdigest() != pin:
        raise StageError('LINEAGE_PIN_MISMATCH')
    x = _json(data, LINEAGE_FILE)
    if not isinstance(x, dict) or x.get('schema_version') != LINEAGE_SCHEMA:
        raise StageError('LINEAGE_SCHEMA')
    for b in summary['boards'].values():
        reference = (b.get('bindings') or {}).get('reference')
        if x.get('evaluation') != b.get('evaluation_population') or x.get('reference_source') != reference:
            raise StageError('LINEAGE_MISMATCH')
        if not isinstance(reference, dict) or reference.get('input_hash') != (b.get('reference_population') or {}).get('input_hash'):
            raise StageError('LINEAGE_MISMATCH')
    ev = next(iter(summary['boards'].values()))['evaluation_population']
    count = x.get('selected_issuer_count')
    if (type(count) is not int or count != ev.get('issuers') or not HEX.match(str(x.get('selected_issuer_members_hash')))
            or not isinstance(x.get('selection_rule'), str) or not x['selection_rule']
            or x.get('rows_equal_source_projection') is not True or x.get('row_values_or_classification_changed') is not False
            or not isinstance(x.get('changed_top_level_fields'), list) or sorted(map(str, x['changed_top_level_fields'])) != PROJECTION_FIELDS
            or len(x['changed_top_level_fields']) != len(PROJECTION_FIELDS)
            or x.get('whole_market_denominator', 0) is not None or x.get('reference_source_is_not_eligible_whole_market') is not True
            or type(x.get('new_score_calculations')) is not int or x['new_score_calculations'] != 0):
        raise StageError('LINEAGE_INVALID')
    return data


def stage(delivery: Path, scope: str, pin: str, data_dir: Path, lineage: Path = None, lineage_pin: str = None, unverified: bool = False,
          set_: str = 'reduced', input_anchored: bool = False) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if not (data_dir / 'classification').is_dir():
        raise StageError('CLASSIFICATION_NOT_STAGED')
    if (lineage is None) != (lineage_pin is None):
        raise StageError('LINEAGE_PIN_REQUIRED')
    if input_anchored and (set_ != '333' or lineage is not None):
        raise StageError('INPUT_ANCHORS_NOT_APPLICABLE')
    files, manifest, summary = check(delivery, scope, pin, data_dir, set_, input_anchored)
    # held1057's evaluation input: the strict path needs the producer's projection proof; staging without it is an explicit choice
    # (--unverified) and the delivery stays REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED on every screen (owner 2026-11-12 §2).
    if SCOPES[scope][1] == 'reference' and lineage is None and not unverified and not input_anchored:
        raise StageError('LINEAGE_REQUIRED')
    if lineage is not None:
        files = {**files, LINEAGE_FILE: check_lineage(lineage, lineage_pin, scope, summary)}
    target = data_dir / 'classification' / SETS[set_][0] / scope
    fresh, old = target.with_name(scope + '.staging'), target.with_name(scope + '.previous')
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
    return files, manifest, summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--delivery', required=True, type=Path)
    parser.add_argument('--scope', required=True, choices=sorted(SCOPES))
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--input-lineage', type=Path)
    parser.add_argument('--input-lineage-sha256')
    parser.add_argument('--set', dest='set_', default='reduced', choices=sorted(SETS))
    parser.add_argument('--unverified', action='store_true', help='held1057 only: stage without a projection proof; its evaluation input stays UNVERIFIED')
    args = parser.parse_args(argv)
    try:
        files, manifest, summary = stage(args.delivery, args.scope, args.manifest_sha256, args.data_dir, args.input_lineage, args.input_lineage_sha256, args.unverified, args.set_)
    except StageError as error:
        print('STAGE_PRIVATE_DUAL_QGV refused=' + str(error))
        return 1
    ev = next(iter(summary['boards'].values()))['evaluation_population']
    print('STAGE_PRIVATE_DUAL_QGV scope=' + args.scope + ' manifest sha256=' + hashlib.sha256(files['manifest.json']).hexdigest()
          + ' models=' + ','.join(summary['boards']) + ' code_rows=' + str(ev['code_rows']) + ' issuers=' + str(ev['issuers'])
          + ' details=' + str(sum(1 for k in files if k.startswith('detail-'))) + ' files=' + str(len(files))
          + (' lineage sha256=' + hashlib.sha256(files[LINEAGE_FILE]).hexdigest() if LINEAGE_FILE in files else '')
          + ' bytes=' + str(sum(len(v) for v in files.values())) + ' max_file_bytes=' + str(max(len(v) for v in files.values()))
          + ' kind=' + manifest['data_kind'] + ' input_check=' + (ATTESTED if LINEAGE_FILE in files else INPUT_CHECK[SCOPES[args.scope][1]])
          + ('' if args.set_ == 'reduced' else ' set=' + args.set_))
    return 0


if __name__ == '__main__':
    sys.exit(main())
