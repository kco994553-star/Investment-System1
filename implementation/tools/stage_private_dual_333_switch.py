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
      (either scope, a new input version; Codex qgv-dual-input-anchors/1)
                    --input-anchors <input-anchors.json> --input-anchors-sha256 <pin> --clocks <delivery-clocks.json> --clocks-sha256 <pin>
                    --preserved-handoff <dir of the earlier pinned input handoff> --preserved-root-sha256 <its handoff-manifest pin>

With the two input anchors (owner 2026-11-13; Codex #534 fe29867c, Q_INPUT_DELIVERY.md) the delivery's inputs are a new, retrospectively
reviewed input version, so the classification bundle's own input hash no longer names them (the population and day still must). Their
trust chain is checked here against the EARLIER handoff Main already pinned (never against the result being switched): its
handoff-manifest has --preserved-root-sha256, lists the bundle manifest the anchors name (size and SHA-256), which lists both source
snapshots the anchors name; the anchors' execution is that bundle's. Each full identity must then be every board's evaluation /
bindings / candidate population and the index's evaluation (the producer's validate_input_bindings). The clock record must carry
calculated_at null only with its reason, the same execution, and is never filled here.

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
ANCHORS_FILE, CLOCKS_FILE = 'input-anchors.json', 'delivery-clocks.json'
IDENTITY_KEYS = ('id', 'version', 'members_hash', 'input_hash', 'valuation_date', 'as_of', 'code_rows', 'issuers', 'snapshot_id')


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


def _pinned(path: Path, pin: str, code: str) -> bytes:
    if not isinstance(pin, str) or len(pin) != 64 or not path.is_file() or path.is_symlink():
        raise SwitchError(code + '_MISSING')
    data = path.read_bytes()
    if len(data) > qgv_tool.MAX_BYTES or _sha(data) != pin:
        raise SwitchError(code + '_PIN_MISMATCH')
    return data


def _listed(manifest: dict, desc: dict, code: str):
    hits = [f for f in manifest.get('files') or [] if isinstance(f, dict) and f.get('path') == desc.get('path')]
    if len(hits) != 1 or hits[0].get('size') != desc.get('size') or hits[0].get('sha256') != desc.get('sha256'):
        raise SwitchError(code)


def check_anchors(a, scope: str) -> tuple:
    raw = _pinned(a.input_anchors, a.input_anchors_sha256, 'INPUT_ANCHORS')
    x = json.loads(raw.decode('utf-8'))
    if (not isinstance(x, dict) or x.get('schema_version') != 'qgv-dual-input-anchors/1' or x.get('scope') != scope
            or x.get('runtime_lineage_used_as_proof') is not False or x.get('new_score_calculations') != 0 or x.get('whole_market_denominator', 0) is not None):
        raise SwitchError('INPUT_ANCHORS_SCHEMA')
    root = a.preserved_handoff / 'handoff-manifest.json'
    if not root.is_file() or _sha(root.read_bytes()) != a.preserved_root_sha256:
        raise SwitchError('PRESERVATION_ROOT_HASH')
    pres = x.get('preservation') or {}
    if pres.get('handoff_manifest_sha256') != a.preserved_root_sha256:
        raise SwitchError('PRESERVATION_ROOT_HASH')
    handoff = json.loads(root.read_bytes())
    if handoff.get('schema_version') != 'qgv-q-input-handoff/1' or any(handoff.get(k) != pres.get(k) for k in ('repo', 'ref', 'path')):
        raise SwitchError('PRESERVATION_LOCATION')
    _listed(handoff, pres.get('bundle_manifest') or {}, 'PRESERVATION_BUNDLE')
    bundle_raw = (a.preserved_handoff / 'bundle-manifest.json').read_bytes() if (a.preserved_handoff / 'bundle-manifest.json').is_file() else b''
    if _sha(bundle_raw) != (pres.get('bundle_manifest') or {}).get('sha256'):
        raise SwitchError('PRESERVATION_BUNDLE')
    bundle = json.loads(bundle_raw)
    for side in ('evaluation', 'reference'):
        _listed(bundle, (x.get('source_files') or {}).get(side) or {}, 'PRESERVATION_SOURCE:' + side)
    if x.get('execution_sha') != bundle.get('execution_sha'):
        raise SwitchError('PRESERVATION_EXECUTION')
    for side in ('expected_evaluation', 'expected_reference'):
        if not isinstance(x.get(side), dict) or any(k not in x[side] for k in IDENTITY_KEYS):
            raise SwitchError('INPUT_ANCHORS_SCHEMA')
    craw = _pinned(a.clocks, a.clocks_sha256, 'CLOCKS')
    c = json.loads(craw.decode('utf-8'))
    if (not isinstance(c, dict) or c.get('schema_version') != 'qgv-dual-delivery-clocks/1' or c.get('execution_sha') != x['execution_sha']
            or (c.get('calculated_at') is None and not c.get('calculated_at_reason')) or not c.get('inspected_execution_records')
            or not c.get('delivery_generated_at') or c.get('new_score_calculations') != 0):
        raise SwitchError('CLOCKS_SCHEMA')
    return raw, x, craw


def _bindings(scope_dir: Path, x: dict):
    E, R = x['expected_evaluation'], x['expected_reference']
    if _load(scope_dir / 'index.json').get('evaluation_population') != E:
        raise SwitchError('EVALUATION_INPUT_BINDING')
    for b in (_load(scope_dir / 'summary.json').get('boards') or {}).values():
        if b.get('evaluation_population') != E or (b.get('bindings') or {}).get('evaluation') != E:
            raise SwitchError('EVALUATION_INPUT_BINDING')
        ref = b.get('reference_population') or {}
        if ((b.get('bindings') or {}).get('reference') != R or ref.get('candidate_population') != R
                or any(ref.get(k) != R[k] for k in ('input_hash', 'valuation_date', 'as_of'))):
            raise SwitchError('REFERENCE_INPUT_BINDING')


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
    if (scope_dir / ANCHORS_FILE).is_file():
        x = _load(scope_dir / ANCHORS_FILE)
        if x['expected_evaluation'].get('input_hash') != first['evaluation_population'].get('input_hash') or x['expected_reference'].get('input_hash') != rf.pop():
            raise SwitchError('ANCHORS_OTHER_INPUT')
    elif scope == 'operating504':
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
    anchored = a.input_anchors is not None
    if anchored:
        if a.anchor is not None or a.input_lineage is not None or None in (a.input_anchors_sha256, a.clocks, a.clocks_sha256, a.preserved_handoff, a.preserved_root_sha256):
            raise SwitchError('INPUT_ANCHORS_ARGUMENTS')
        anchors = check_anchors(a, a.scope)
    elif a.scope == 'operating504' and (a.anchor is None or a.input_lineage is not None):
        raise SwitchError('ANCHOR_REQUIRED')
    elif a.scope == 'held1057' and (a.input_lineage is None or a.anchor is not None):
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
            qgv_tool.stage(a.delivery, a.scope, a.manifest_sha256, shadow, a.input_lineage, a.input_lineage_sha256, False, SET, anchored)
            if anchored:
                d = shadow / 'classification' / SET_DIR / a.scope
                _bindings(d, anchors[1])
                (d / ANCHORS_FILE).write_bytes(anchors[0])
                (d / CLOCKS_FILE).write_bytes(anchors[2])
            elif a.scope == 'operating504':
                anchor_tool.stage(a.anchor, a.anchor_sha256, shadow, SET)
            dist_tool.stage(a.distribution, a.scope, a.distribution_sha256, shadow, SET)
            bins_tool.stage(a.bins, a.scope, a.bins_sha256, shadow, SET)
        except (qgv_tool.StageError, anchor_tool.StageError, dist_tool.StageError, bins_tool.StageError) as e:
            raise SwitchError(type(e).__module__.replace('stage_private_dual_', '').upper() + ':' + str(e)) from None
        fresh = shadow / 'classification' / SET_DIR / a.scope
        version = _same_version(fresh, a.scope)
        record = {'schema_version': RECORD_SCHEMA, 'scope': a.scope, 'data_kind': _load(fresh / 'manifest.json').get('data_kind'),
                  'pins': {'delivery_manifest': a.manifest_sha256, 'distribution_manifest': a.distribution_sha256, 'bins_manifest': a.bins_sha256,
                           **({'input_anchors': a.input_anchors_sha256, 'clocks': a.clocks_sha256, 'preserved_root': a.preserved_root_sha256} if anchored else
                              {('reference_anchor' if a.scope == 'operating504' else 'input_projection_proof'): a.anchor_sha256 if a.scope == 'operating504' else a.input_lineage_sha256})},
                  'input_basis': 'INPUT_ANCHORS' if anchored else ('REFERENCE_ANCHOR' if a.scope == 'operating504' else 'PROJECTION_PROOF'),
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
    p.add_argument('--input-anchors', type=Path)
    p.add_argument('--input-anchors-sha256')
    p.add_argument('--clocks', type=Path)
    p.add_argument('--clocks-sha256')
    p.add_argument('--preserved-handoff', type=Path)
    p.add_argument('--preserved-root-sha256')
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
