#!/usr/bin/env python3
"""Stage Codex's 3/3/3 EPS input connection follow-up (#534 bfadb012, qgv-333-eps-handoff/1) for the authenticated screen
(owner 2026-11-13 「3/3/3 화면 연결 우선, 전달·재현 병렬 작업 추가」 §1, §3).

The private Worker serves /kis/classification?part=dual_eps_index|dual_eps_diagnostic|dual_eps_comparison|dual_eps_continuation
from classification/dual-333/eps/ on the data branch of the private repository. This tool copies the producer's
diagnostic-summary.json, run-comparison.json and continuation-inputs.json there BYTE FOR BYTE after checking them against the
handoff manifest, and writes Main's index (qgv-333-eps-delivery/1) naming each staged file's size and SHA-256 and the producer /
execution SHA. It computes, infers, aggregates and fetches nothing: every count shown comes from the producer's own files.

  python implementation/tools/stage_private_qgv333_eps.py --handoff <dir with handoff-manifest.json and the three files> \
      --handoff-manifest-sha256 <its SHA-256 as pinned> --data-dir <private data checkout>

Checks, all before anything is written:
- handoff-manifest.json's own SHA-256 equals its pin; it is qgv-333-eps-handoff/1 and PRIVATE_RESEARCH with a producer and an
  execution SHA; it lists each of the three files with that file's size and SHA-256; every file is at most 2 MiB;
- diagnostic-summary.json has exactly the scopes operating / held, run-comparison.json exactly operating504 / held1057 with the
  three 3/3/3 candidates each, continuation-inputs.json is qgv-333-eps-continuation/1; the evaluation day and input cutoff agree;
- --data-dir is outside this public repository.
This is not a result delivery: the new input version's bounded delivery (summary / index / details), distribution and bins are
not part of this handoff and are never assembled here. classification/dual-333/eps/ is replaced whole or not at all; on any failure
the existing copy stays. Output: one line with sizes and hashes (no content).
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
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SHA40 = re.compile(r'^[0-9a-f]{40}$')
INDEX_SCHEMA = 'qgv-333-eps-delivery/1'
FILES = {'diagnostic-summary.json': 'diagnostic', 'run-comparison.json': 'comparison', 'continuation-inputs.json': 'continuation'}
MODELS = ('U2-333', 'U1-333', 'S1-333')
SCOPES = {'operating504': 'operating', 'held1057': 'held'}


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


def _read(path: Path, name: str) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise StageError('FILE_MISSING:' + name)
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise StageError('FILE_TOO_LARGE:' + name)
    return data


def check(handoff: Path, pin: str) -> tuple:
    if not isinstance(pin, str) or not HEX64.fullmatch(pin):
        raise StageError('PIN_INVALID')
    raw = _read(handoff / 'handoff-manifest.json', 'handoff-manifest.json')
    if hashlib.sha256(raw).hexdigest() != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    m = _json(raw, 'handoff-manifest.json')
    if (not isinstance(m, dict) or m.get('schema_version') != 'qgv-333-eps-handoff/1' or m.get('visibility') != 'PRIVATE_RESEARCH'
            or not SHA40.fullmatch(str(m.get('producer_sha'))) or not SHA40.fullmatch(str(m.get('execution_sha')))
            or not isinstance(m.get('files'), list) or not isinstance(m.get('path'), str)):
        raise StageError('MANIFEST_SCHEMA')
    listed = {f.get('path'): f for f in m['files'] if isinstance(f, dict)}
    files = {}
    for name in FILES:
        f = listed.get(name)
        if not f:
            raise StageError('FILE_NOT_LISTED:' + name)
        data = _read(handoff / name, name)
        if len(data) != f.get('size') or hashlib.sha256(data).hexdigest() != f.get('sha256'):
            raise StageError('FILE_MISMATCH:' + name)
        files[name] = data
    diag = _json(files['diagnostic-summary.json'], 'diagnostic-summary.json')
    comp = _json(files['run-comparison.json'], 'run-comparison.json')
    cont = _json(files['continuation-inputs.json'], 'continuation-inputs.json')
    if not isinstance(diag, dict) or sorted(diag) != ['held', 'operating']:
        raise StageError('DIAGNOSTIC_SCHEMA')
    if not isinstance(comp, dict) or sorted(comp) != sorted(SCOPES) or any(not isinstance(comp[s], dict) or sorted(comp[s]) != sorted(MODELS) for s in comp):
        raise StageError('COMPARISON_SCHEMA')
    if not isinstance(cont, dict) or cont.get('schema_version') != 'qgv-333-eps-continuation/1':
        raise StageError('CONTINUATION_SCHEMA')
    days = {diag[k].get('valuation_date') for k in diag} | {cont.get('valuation_date')}
    cutoffs = {diag[k].get('as_of') for k in diag} | {cont.get('retained_as_of')}
    if len(days) != 1 or len(cutoffs) != 1:
        raise StageError('DATE_MISMATCH')
    index = {'schema_version': INDEX_SCHEMA, 'data_kind': 'PRIVATE',
             'source': {'handoff_path': m['path'], 'handoff_manifest_sha256': pin, 'producer_sha': m['producer_sha'], 'execution_sha': m['execution_sha']},
             'valuation_date': days.pop(), 'input_as_of': cutoffs.pop(),
             'files': {FILES[n]: {'size': len(d), 'sha256': hashlib.sha256(d).hexdigest()} for n, d in files.items()},
             'result_delivery': None, 'new_external_requests': 0}
    return files, index


def stage(handoff: Path, pin: str, data_dir: Path) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if not (data_dir / 'classification').is_dir():
        raise StageError('CLASSIFICATION_NOT_STAGED')
    files, index = check(handoff, pin)
    out = {**files, 'eps-index.json': (json.dumps(index, indent=2, sort_keys=True) + '\n').encode()}
    target = data_dir / 'classification' / 'dual-333' / 'eps'
    fresh, old = target.with_name('eps.staging'), target.with_name('eps.previous')
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
        print('STAGE_PRIVATE_QGV333_EPS refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_QGV333_EPS index sha256=' + hashlib.sha256(out['eps-index.json']).hexdigest() + ' execution=' + index['source']['execution_sha']
          + ' ' + ' '.join(k + '=' + v['sha256'] + ':' + str(v['size']) for k, v in sorted(index['files'].items())) + ' result_delivery=none')
    return 0


if __name__ == '__main__':
    sys.exit(main())
