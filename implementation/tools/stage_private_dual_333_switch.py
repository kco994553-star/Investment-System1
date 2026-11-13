#!/usr/bin/env python3
"""Switch one scope's 3/3/3 research results to a new result version in one step, or not at all (owner 2026-11-13 「새 Q 결과
전환·인수 상태 정리」 §1).

The per-part staging tools (stage_private_dual_qgv / _reference_anchor / _distribution / _bins) each replace their own piece, and the
delivery tool replaces classification/dual-333/<scope>/ whole: staged one after another, a failure part-way would leave a new summary
beside no deciles, or a staged reference anchor of the previous version. This tool runs the same four checks, unchanged, against a
shadow copy of the data directory, then checks that every piece names the SAME result version, and only then swaps the scope
directory with one rename. On any refusal the existing, working bundle stays exactly as it was and the shadow copy is removed.

  python implementation/tools/stage_private_dual_333_switch.py --scope operating504|held1057 --data-dir <private data checkout> \
      --delivery <delivery/<scope> dir> --manifest-sha256 <pin> \
      --distribution <dir> --distribution-sha256 <pin> --bins <dir> --bins-sha256 <pin> \
      (operating504) --anchor <reference-anchor.json> --anchor-sha256 <pin>
      (held1057)    --input-lineage <input-lineage.json> --input-lineage-sha256 <pin>

Required together (nothing is switched without all of them): the delivery (summary, index, details); the distribution and its
all-bin routing (the full 10-decile view); the evaluation and reference input basis: operating504's evaluation input is the staged
classification coverage's own (checked by the delivery tool) and its reference is the producer's reference anchor; held1057's
reference input is the coverage's (delivery tool) and its evaluation is the producer's projection proof. Same-version checks, after
the four tools pass: the boards of the summary, the distribution manifest's source results and the distribution index are exactly
the same set with the same result hashes; every board names one evaluation and one reference input; the bins route the very
distribution manifest staged here; the anchor / proof names those inputs. The swap writes a switch record (qgv-dual-333-switch/1:
the pins, the new and the replaced result hashes) beside the bundle. It computes no score, fills nothing and fetches nothing.
Output: one line with the result version (hashes and counts only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_private_dual_bins as bins_tool  # noqa: E402
import stage_private_dual_distribution as dist_tool  # noqa: E402
import stage_private_dual_qgv as qgv_tool  # noqa: E402
import stage_private_dual_reference_anchor as anchor_tool  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SET = '333'
SET_DIR = 'dual-333'
RECORD = 'switch.json'
RECORD_SCHEMA = 'qgv-dual-333-switch/1'
SHADOW_INPUTS = (('expanded', 'coverage.json'), ('expanded', 'reference-view.json'))


class SwitchError(Exception):
    pass


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _load(p: Path):
    return json.loads(p.read_bytes().decode('utf-8'))


def _same_version(scope_dir: Path, scope: str) -> dict:
    summary = _load(scope_dir / 'summary.json')
    boards = summary.get('boards') or {}
    dm = _load(scope_dir / 'distribution' / 'distribution-manifest.json')
    di = _load(scope_dir / 'distribution' / 'distribution-index.json')
    bm = _load(scope_dir / 'bins' / 'bin-manifest.json')
    want = {k: b.get('result_hash') for k, b in boards.items()}
    if set(dm.get('source_results') or {}) != set(want) or any(dm['source_results'][k].get('result_hash') != h for k, h in want.items()):
        raise SwitchError('DISTRIBUTION_OTHER_RESULT')
    if set(di.get('boards') or {}) != set(want) or any(di['boards'][k].get('result_hash') != h for k, h in want.items()):
        raise SwitchError('DISTRIBUTION_OTHER_RESULT')
    if bm.get('source_manifest_sha256') != _sha((scope_dir / 'distribution' / 'distribution-manifest.json').read_bytes()):
        raise SwitchError('BINS_OTHER_DISTRIBUTION')
    ev = {json.dumps(b.get('evaluation_population'), sort_keys=True) for b in boards.values()}
    rf = {(b.get('reference_population') or {}).get('input_hash') for b in boards.values()}
    if len(ev) != 1 or len(rf) != 1 or None in rf:
        raise SwitchError('INPUT_VERSION_MIXED')
    first = next(iter(boards.values()))
    if scope == 'operating504':
        anchor = _load(scope_dir / anchor_tool.TARGET)
        if (anchor.get('expected_reference') or {}).get('input_hash') != rf.pop():
            raise SwitchError('ANCHOR_OTHER_INPUT')
    else:
        proof = _load(scope_dir / qgv_tool.LINEAGE_FILE)
        if proof.get('evaluation') != first.get('evaluation_population'):
            raise SwitchError('PROOF_OTHER_INPUT')
    return {'results': want, 'evaluation_input_hash': first['evaluation_population'].get('input_hash'),
            'reference_input_hash': first['reference_population'].get('input_hash'),
            'valuation_date': first['evaluation_population'].get('valuation_date'), 'code_rows': first['evaluation_population'].get('code_rows')}


def switch(a) -> dict:
    data_dir: Path = a.data_dir
    if _inside(data_dir, REPO_ROOT):
        raise SwitchError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if a.scope == 'operating504' and (a.anchor is None or a.input_lineage is not None):
        raise SwitchError('ANCHOR_REQUIRED')
    if a.scope == 'held1057' and (a.input_lineage is None or a.anchor is not None):
        raise SwitchError('INPUT_PROOF_REQUIRED')
    target = data_dir / 'classification' / SET_DIR / a.scope
    shadow = data_dir / ('.switch-' + a.scope)
    if shadow.exists():
        shutil.rmtree(shadow)
    previous = None
    if (target / 'summary.json').is_file():
        previous = {k: b.get('result_hash') for k, b in (_load(target / 'summary.json').get('boards') or {}).items()}
    try:
        for parts in SHADOW_INPUTS:
            src = data_dir / 'classification' / Path(*parts)
            if src.is_file():
                (shadow / 'classification' / parts[0]).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, shadow / 'classification' / Path(*parts))
        (shadow / 'classification' / SET_DIR).mkdir(parents=True)
        try:
            qgv_tool.stage(a.delivery, a.scope, a.manifest_sha256, shadow, a.input_lineage, a.input_lineage_sha256, False, SET)
            if a.scope == 'operating504':
                anchor_tool.stage(a.anchor, a.anchor_sha256, shadow, SET)
            dist_tool.stage(a.distribution, a.scope, a.distribution_sha256, shadow, SET)
            bins_tool.stage(a.bins, a.scope, a.bins_sha256, shadow, SET)
        except (qgv_tool.StageError, anchor_tool.StageError, dist_tool.StageError, bins_tool.StageError) as e:
            raise SwitchError(type(e).__module__.replace('stage_private_dual_', '').upper() + ':' + str(e)) from None
        fresh = shadow / 'classification' / SET_DIR / a.scope
        version = _same_version(fresh, a.scope)
        record = {'schema_version': RECORD_SCHEMA, 'scope': a.scope, 'data_kind': _load(fresh / 'manifest.json').get('data_kind'),
                  'pins': {'delivery_manifest': a.manifest_sha256, 'distribution_manifest': a.distribution_sha256, 'bins_manifest': a.bins_sha256,
                           ('reference_anchor' if a.scope == 'operating504' else 'input_projection_proof'): a.anchor_sha256 if a.scope == 'operating504' else a.input_lineage_sha256},
                  **version, 'replaced_results': previous, 'new_score_calculations': 0}
        (fresh / RECORD).write_bytes((json.dumps(record, indent=2, sort_keys=True) + '\n').encode())
        # one rename makes the new version visible; the previous bundle is kept until the rename has happened
        old = target.with_name(a.scope + '.replaced')
        if old.exists():
            shutil.rmtree(old)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.rename(old)
        try:
            fresh.rename(target)
        except BaseException:
            if old.exists() and not target.exists():
                old.rename(target)
            raise
        if old.exists():
            shutil.rmtree(old)
        return record
    finally:
        if shadow.exists():
            shutil.rmtree(shadow)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--scope', required=True, choices=sorted(qgv_tool.SCOPES))
    p.add_argument('--data-dir', required=True, type=Path)
    p.add_argument('--delivery', required=True, type=Path)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--distribution', required=True, type=Path)
    p.add_argument('--distribution-sha256', required=True)
    p.add_argument('--bins', required=True, type=Path)
    p.add_argument('--bins-sha256', required=True)
    p.add_argument('--anchor', type=Path)
    p.add_argument('--anchor-sha256')
    p.add_argument('--input-lineage', type=Path)
    p.add_argument('--input-lineage-sha256')
    a = p.parse_args(argv)
    try:
        r = switch(a)
    except SwitchError as e:
        print('STAGE_PRIVATE_DUAL_333_SWITCH refused=' + str(e) + ' kept=existing')
        return 1
    print('STAGE_PRIVATE_DUAL_333_SWITCH scope=' + r['scope'] + ' switched results=' + ','.join(k + ':' + h[:12] for k, h in sorted(r['results'].items()))
          + ' evaluation_input=' + str(r['evaluation_input_hash'])[:12] + ' reference_input=' + str(r['reference_input_hash'])[:12]
          + ' code_rows=' + str(r['code_rows']) + ' replaced=' + (','.join(k + ':' + str(h)[:12] for k, h in sorted(r['replaced_results'].items())) if r['replaced_results'] else 'none'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
