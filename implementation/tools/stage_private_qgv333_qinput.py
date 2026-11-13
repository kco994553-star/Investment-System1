#!/usr/bin/env python3
"""Stage Codex's 3/3/3 Q input recovery (#534 4352c8ec, execution 93a699ed, qgv-q-input-handoff/1) for the authenticated screen
(owner 2026-11-13 「3/3/3 화면 연결 우선, 전달·재현 병렬 작업 추가」 §1 Q 결손·공식 관문 결손 별도 줄, §3 시각 구분).

The private Worker serves /kis/classification?part=dual_q_index|dual_q_diag|dual_q_compare from classification/dual-333/qinput/
on the data branch of the private repository. This tool copies the producer's diagnostic-summary.json and comparison.json there
BYTE FOR BYTE after checking them against the handoff manifest, and writes Main's index (qgv-333-q-input-delivery/1). The index
holds only fields the producer wrote: the review clocks of the four new snapshots' review_context (sector-qgv-review-context/1,
read from the archive members pinned by bundle-manifest.json, the reviews themselves left out but counted), the producer's
verification time and verdict, whether source snapshots were reused, and the chain to the staged EPS step. Calculation time is
not a field of this handoff and stays null. It computes no score, fills nothing and fetches nothing.

  python implementation/tools/stage_private_qgv333_qinput.py --handoff <dir with handoff-manifest.json and its files> \
      --handoff-manifest-sha256 <its SHA-256 as pinned> --data-dir <private data checkout>

Checks, all before anything is written:
- handoff-manifest.json's own SHA-256 equals its pin; it is qgv-q-input-handoff/1 and PRIVATE_RESEARCH with a producer and an
  execution SHA; each file used is listed with its size and SHA-256; the two staged files are at most 2 MiB;
- the archive's four transformed snapshots match bundle-manifest.json; their review contexts agree (evaluation day, original and
  new input cutoff, review time, RETROSPECTIVE_REVIEW, historical_system_pit_complete false);
- diagnostic-summary.json has exactly operating504 / held1057; the primary Q causes, the gate decomposition and the official
  input linkage each add up to that scope's issuers; the whole-market denominator is null;
- comparison.json has the two scopes with U2-333 / U1-333 / S1-333; every after side is the new input cutoff and evaluation day;
  each board's before result is the staged EPS step's after result (classification/dual-333/eps/run-comparison.json), so the
  three input versions chain and are never mixed; unified Q available equals each unified board's Q output;
- --data-dir is outside this public repository.
This is not a result delivery: the per-candidate runs in the archive have no scope delivery manifest, distribution, bins or
anchor for the new input, and are never assembled here. classification/dual-333/qinput/ is replaced whole or not at all.
Output: one line with sizes and hashes (no content).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SHA40 = re.compile(r'^[0-9a-f]{40}$')
INDEX_SCHEMA = 'qgv-333-q-input-delivery/1'
STAGED = {'diagnostic-summary.json': 'diagnostic', 'comparison.json': 'comparison'}
SIDE = ('preparation-summary.json', 'verification.json', 'bundle-manifest.json', 'private-run-bundle.tar.gz')
MODELS = ('U2-333', 'U1-333', 'S1-333')
SCOPES = ('operating504', 'held1057')
SNAPSHOTS = ('operating', 'held', 'operating_reference', 'catalog_reference')
CONTEXT_KEYS = ('valuation_date', 'original_input_cutoff', 'input_cutoff', 'reviewed_at', 'result_kind', 'historical_system_pit_complete')


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
        return json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise StageError('NOT_JSON:' + name) from None


def _read(path: Path, name: str, limit=MAX_BYTES) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise StageError('FILE_MISSING:' + name)
    data = path.read_bytes()
    if limit is not None and len(data) > limit:
        raise StageError('FILE_TOO_LARGE:' + name)
    return data


def _nonneg(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _sums(d: dict, key: str, total: int, at: str):
    v = d.get(key)
    if not isinstance(v, dict) or not v or any(not _nonneg(x) for x in v.values()) or sum(v.values()) != total:
        raise StageError('DIAGNOSTIC_SUM:' + at + '.' + key)


def _contexts(archive: bytes, members: dict) -> dict:
    out = {}
    import io
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
        names = {m.name.lstrip('./'): m for m in tar.getmembers() if m.isfile()}
        for snap in SNAPSHOTS:
            name = 'transformed/' + snap + '/snapshot.json'
            pin, m = members.get(name), names.get(name)
            if not pin or m is None:
                raise StageError('SNAPSHOT_NOT_LISTED:' + name)
            data = tar.extractfile(m).read()
            if len(data) != pin.get('size') or hashlib.sha256(data).hexdigest() != pin.get('sha256'):
                raise StageError('SNAPSHOT_MISMATCH:' + name)
            rc = _json(data, name).get('review_context')
            if not isinstance(rc, dict) or rc.get('schema_version') != 'sector-qgv-review-context/1' or not isinstance(rc.get('reviews'), list):
                raise StageError('REVIEW_CONTEXT:' + name)
            out[snap] = rc
    return out


def check(handoff: Path, pin: str, eps_comparison: bytes) -> tuple:
    if not isinstance(pin, str) or not HEX64.fullmatch(pin):
        raise StageError('PIN_INVALID')
    raw = _read(handoff / 'handoff-manifest.json', 'handoff-manifest.json')
    if hashlib.sha256(raw).hexdigest() != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    m = _json(raw, 'handoff-manifest.json')
    if (not isinstance(m, dict) or m.get('schema_version') != 'qgv-q-input-handoff/1' or m.get('visibility') != 'PRIVATE_RESEARCH'
            or not SHA40.fullmatch(str(m.get('producer_sha'))) or not SHA40.fullmatch(str(m.get('execution_sha')))
            or not isinstance(m.get('files'), list) or not isinstance(m.get('path'), str)):
        raise StageError('MANIFEST_SCHEMA')
    listed = {f.get('path'): f for f in m['files'] if isinstance(f, dict)}
    files = {}
    for name in (*STAGED, *SIDE):
        f = listed.get(name)
        if not f:
            raise StageError('FILE_NOT_LISTED:' + name)
        data = _read(handoff / name, name, MAX_BYTES if name in STAGED else None)
        if len(data) != f.get('size') or hashlib.sha256(data).hexdigest() != f.get('sha256'):
            raise StageError('FILE_MISMATCH:' + name)
        files[name] = data
    bundle = _json(files['bundle-manifest.json'], 'bundle-manifest.json')
    if (not isinstance(bundle, dict) or bundle.get('schema_version') != 'qgv-q-input-private-bundle/1' or bundle.get('execution_sha') != m['execution_sha']
            or not isinstance(bundle.get('files'), list)):
        raise StageError('BUNDLE_SCHEMA')
    ctx = _contexts(files['private-run-bundle.tar.gz'], {f.get('path'): f for f in bundle['files'] if isinstance(f, dict)})
    clocks = {k: ctx[SNAPSHOTS[0]].get(k) for k in CONTEXT_KEYS}
    if any({k: c.get(k) for k in CONTEXT_KEYS} != clocks for c in ctx.values()):
        raise StageError('REVIEW_CONTEXT_DISAGREE')
    if clocks['result_kind'] != 'RETROSPECTIVE_REVIEW' or clocks['historical_system_pit_complete'] is not False or not all(isinstance(clocks[k], str) for k in CONTEXT_KEYS[:4]):
        raise StageError('REVIEW_CONTEXT_KIND')
    diag = _json(files['diagnostic-summary.json'], 'diagnostic-summary.json')
    comp = _json(files['comparison.json'], 'comparison.json')
    prep = _json(files['preparation-summary.json'], 'preparation-summary.json')
    ver = _json(files['verification.json'], 'verification.json')
    prev = _json(eps_comparison, 'eps run-comparison.json')
    if not isinstance(diag, dict) or sorted(diag) != sorted(SCOPES):
        raise StageError('DIAGNOSTIC_SCHEMA')
    if not isinstance(comp, dict) or sorted(comp) != sorted(SCOPES) or any(not isinstance(comp[s], dict) or sorted(comp[s]) != sorted(MODELS) for s in SCOPES):
        raise StageError('COMPARISON_SCHEMA')
    if not isinstance(prep, dict) or prep.get('as_of') != clocks['input_cutoff'] or not isinstance(prep.get('source_snapshots_reused'), bool):
        raise StageError('PREPARATION_SCHEMA')
    if not isinstance(ver, dict) or not isinstance(ver.get('passed'), bool) or not isinstance(ver.get('checked_at'), str):
        raise StageError('VERIFICATION_SCHEMA')
    for s in SCOPES:
        d = diag[s]
        den = d.get('denominator_issuers') if isinstance(d, dict) else None
        if not _nonneg(den) or not _nonneg(d.get('code_rows')) or d.get('whole_market_denominator', 0) is not None:
            raise StageError('DIAGNOSTIC_SCHEMA:' + s)
        for key in ('primary_q_causes', 'gate_diagnostic', 'official_input_linkage'):
            _sums(d, key, den, s)
        for k in MODELS:
            b = comp[s][k]
            if not isinstance(b, dict) or not all(isinstance(b.get(x), dict) for x in ('stages', 'before_bindings', 'after_bindings')):
                raise StageError('COMPARISON_SCHEMA:' + s + '.' + k)
            ev = b['after_bindings'].get('evaluation') or {}
            if ev.get('valuation_date') != clocks['valuation_date'] or ev.get('as_of') != clocks['input_cutoff']:
                raise StageError('DATE_MISMATCH:' + s + '.' + k)
            p = (prev.get(s) or {}).get(k) if isinstance(prev, dict) else None
            if not isinstance(p, dict) or b.get('before_result_hash') != p.get('after_result_hash'):
                raise StageError('CHAIN_MISMATCH:' + s + '.' + k)
        for k in ('U2-333', 'U1-333'):
            if comp[s][k]['stages'].get('Q', {}).get('after') != d['primary_q_causes'].get('Q_AVAILABLE'):
                raise StageError('Q_COUNT_DISAGREE:' + s + '.' + k)
    index = {'schema_version': INDEX_SCHEMA, 'data_kind': 'PRIVATE',
             'source': {'handoff_path': m['path'], 'handoff_manifest_sha256': pin, 'producer_sha': m['producer_sha'], 'execution_sha': m['execution_sha']},
             'clocks': {**{k: clocks[k] for k in CONTEXT_KEYS[:4]}, 'producer_verified_at': ver['checked_at'], 'calculated_at': None},
             'result_kind': clocks['result_kind'], 'historical_system_pit_complete': False,
             'review_records': {s: len(ctx[s]['reviews']) for s in SNAPSHOTS},
             'source_snapshots_reused': prep['source_snapshots_reused'], 'producer_verification_passed': ver['passed'],
             'continues': {'step': 'qgv-333-eps-delivery/1', 'eps_comparison_sha256': hashlib.sha256(eps_comparison).hexdigest(), 'boards': len(SCOPES) * len(MODELS)},
             'files': {STAGED[n]: {'size': len(files[n]), 'sha256': hashlib.sha256(files[n]).hexdigest()} for n in STAGED},
             'result_delivery': None}
    return {n: files[n] for n in STAGED}, index


def stage(handoff: Path, pin: str, data_dir: Path) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    eps = data_dir / 'classification' / 'dual-333' / 'eps'
    if not (eps / 'eps-index.json').is_file():
        raise StageError('EPS_STEP_NOT_STAGED')
    files, index = check(handoff, pin, _read(eps / 'run-comparison.json', 'eps run-comparison.json'))
    out = {**files, 'q-index.json': (json.dumps(index, indent=2, sort_keys=True) + '\n').encode()}
    target = data_dir / 'classification' / 'dual-333' / 'qinput'
    fresh, old = target.with_name('qinput.staging'), target.with_name('qinput.previous')
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        fresh.mkdir(parents=True)
        for name, data in out.items():
            (fresh / name).write_bytes(data)
            if (fresh / name).read_bytes() != data:
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
    return out, index


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--handoff', required=True, type=Path)
    parser.add_argument('--handoff-manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        out, index = stage(args.handoff, args.handoff_manifest_sha256, args.data_dir)
    except StageError as error:
        print('STAGE_PRIVATE_QGV333_QINPUT refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_QGV333_QINPUT index sha256=' + hashlib.sha256(out['q-index.json']).hexdigest() + ' execution=' + index['source']['execution_sha']
          + ' ' + ' '.join(k + '=' + v['sha256'] + ':' + str(v['size']) for k, v in sorted(index['files'].items())) + ' result_delivery=none')
    return 0


if __name__ == '__main__':
    sys.exit(main())
