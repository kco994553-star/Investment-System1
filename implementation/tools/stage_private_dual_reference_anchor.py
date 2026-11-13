#!/usr/bin/env python3
"""Stage operating504's independent reference anchor (Codex qgv-dual-reference-anchor/1) beside its staged dual delivery (owner 2026-11-12).

The private Worker serves /kis/classification?part=dual_reference_anchor&scope=operating504 from
classification/dual/operating504/reference-anchor.json on the data branch of the private repository. The reader then compares every
board's reference binding and reference candidate population with the anchor's expected identity (web_app/dual-qgv.js
referenceAnchorCheck); without the file the reference side stays "독립 기준과 대조 안 됨". This tool copies Codex's anchor BYTE FOR
BYTE after checking it. It computes and fetches nothing.

  python implementation/tools/stage_private_dual_reference_anchor.py --anchor <operating-reference-anchor.json> \
      --anchor-sha256 <its SHA-256 as the pinned handoff manifest names it> --data-dir <private data checkout>

Checks, all before anything is written:
- the file's own SHA-256 equals --anchor-sha256; schema qgv-dual-reference-anchor/1, scope operating504, no new score, it claims to
  match all dual boards, and its expected reference has the candidate row count it states;
- every board staged at classification/dual/operating504/summary.json has bindings.reference and reference_population.candidate_population
  exactly equal to the expected reference (and the same reference input hash);
- the #528 view staged at classification/expanded/reference-view.json has the SHA-256 the anchor names and the same reference input
  hash (its selected members are another set and are not compared as the same);
- --data-dir is outside this public repository.
The anchor is written as one file (atomic replace); on any failure the existing copy stays. Restaging the delivery
(stage_private_dual_qgv.py) replaces classification/dual/operating504/ whole and drops it; it is staged again after its delivery.
Output: one line with hashes and counts (no content).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
TARGET = 'reference-anchor.json'


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


def check(anchor: Path, pin: str, data_dir: Path) -> tuple:
    if not isinstance(pin, str) or not re.fullmatch(r'[0-9a-f]{64}', pin):
        raise StageError('PIN_INVALID')
    if not anchor.is_file() or anchor.is_symlink():
        raise StageError('ANCHOR_MISSING')
    data = anchor.read_bytes()
    if len(data) > MAX_BYTES:
        raise StageError('FILE_TOO_LARGE')
    if hashlib.sha256(data).hexdigest() != pin:
        raise StageError('ANCHOR_PIN_MISMATCH')
    x = _json(data, anchor.name)
    if (not isinstance(x, dict) or x.get('schema_version') != 'qgv-dual-reference-anchor/1' or x.get('scope') != 'operating504'
            or x.get('new_score_calculations') != 0 or x.get('matches_all_dual_boards') is not True
            or not isinstance(x.get('expected_reference'), dict) or x['expected_reference'].get('code_rows') != x.get('candidate_rows')):
        raise StageError('ANCHOR_SCHEMA')
    delivery = data_dir / 'classification' / 'dual' / 'operating504'
    if not (delivery / 'manifest.json').is_file() or not (delivery / 'summary.json').is_file():
        raise StageError('DELIVERY_NOT_STAGED')
    boards = _json((delivery / 'summary.json').read_bytes(), 'summary.json').get('boards') or {}
    if not boards:
        raise StageError('DELIVERY_NOT_STAGED')
    expected = x['expected_reference']
    for key, b in boards.items():
        ref = (b.get('reference_population') or {})
        if (b.get('bindings') or {}).get('reference') != expected or ref.get('candidate_population') != expected or ref.get('input_hash') != expected.get('input_hash'):
            raise StageError('ANCHOR_MISMATCH:' + key)
    view = data_dir / 'classification' / 'expanded' / 'reference-view.json'
    if not view.is_file():
        raise StageError('REFERENCE_VIEW_NOT_STAGED')
    view_bytes = view.read_bytes()
    if hashlib.sha256(view_bytes).hexdigest() != x.get('source_reference_view_sha256'):
        raise StageError('REFERENCE_VIEW_MISMATCH')
    if (_json(view_bytes, 'reference-view.json').get('reference_population') or {}).get('input_hash') != expected.get('input_hash'):
        raise StageError('REFERENCE_VIEW_MISMATCH')
    return data, x, boards


def stage(anchor: Path, pin: str, data_dir: Path) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    data, x, boards = check(anchor, pin, data_dir)
    target = data_dir / 'classification' / 'dual' / 'operating504' / TARGET
    fresh = target.with_name(TARGET + '.staging')
    try:
        fresh.write_bytes(data)
        if hashlib.sha256(fresh.read_bytes()).digest() != hashlib.sha256(data).digest():
            raise StageError('COPY_MISMATCH')
        fresh.replace(target)
    finally:
        if fresh.exists():
            fresh.unlink()
    return data, x, boards


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--anchor', required=True, type=Path)
    parser.add_argument('--anchor-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        data, x, boards = stage(args.anchor, args.anchor_sha256, args.data_dir)
    except StageError as error:
        print('STAGE_PRIVATE_DUAL_REFERENCE_ANCHOR refused=' + str(error))
        return 1
    print('STAGE_PRIVATE_DUAL_REFERENCE_ANCHOR scope=operating504 anchor sha256=' + hashlib.sha256(data).hexdigest()
          + ' reference input_hash=' + x['expected_reference']['input_hash'] + ' candidate_rows=' + str(x['candidate_rows'])
          + ' boards=' + ','.join(boards) + ' view sha256=' + x['source_reference_view_sha256'] + ' bytes=' + str(len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
