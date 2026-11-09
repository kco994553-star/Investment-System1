#!/usr/bin/env python3
"""Stage the held issuer delivery (Codex #524 held-issuer-sharded/1) for the owner-checked private Worker (owner 2026-11-09).

The private Worker serves /kis/classification?part=expanded_manifest|expanded_index|expanded_coverage and
?part=expanded_detail&shard=<2 hex> from the data branch of the private repository, under classification/expanded/
(implementation/worker/src/index.js). This tool copies Codex's delivery there BYTE FOR BYTE after checking it. It computes nothing,
re-serializes nothing and fetches nothing.

  python implementation/tools/stage_private_held_issuers.py --delivery <extracted private-delivery dir> \
      --manifest-sha256 <the manifest SHA-256 named in the authenticated handoff> --data-dir <private data branch checkout>

Checks, all before anything is written:
- manifest.json's own SHA-256 equals --manifest-sha256 (the pin from the handoff; the files' own hashes alone prove nothing);
- Codex's verify_shards (research/held_issuer_shards.py, used as is) accepts the whole file set: hashes, sizes, identities, shard
  membership, index ↔ detail, denominator;
- every file is at most 2 MiB (the Worker's bound, unchanged) and the set holds nothing else;
- the summary already staged at classification/expanded_summary.json is the one the delivery names (SHA-256 of its bytes) and its
  held_financial_subsample scope has the delivery's valuation date, population, scoring population, versions, classification and
  result identity;
- --data-dir is outside this public repository.
Optionally (owner 2026-11-09, Codex #527): --input-repair <input-repair-comparison.json> --input-repair-sha256 <pin> stages the
input connection repair comparison next to the delivery (classification/expanded/input-repair-comparison.json, the Worker's part
input_repair), byte for byte, after: its own SHA-256 = the pin; schema sector-qgv-input-repair-comparison/1 and treatment
INPUT_CONNECTION_REPAIR; at most 2 MiB; it compares to this delivery's result — one coverage scope with the same evaluation date, the
same input hash (after_input_hash = that scope's result identity) and the same denominator.
classification/expanded/ is replaced whole or not at all; on any failure the existing copy stays. A later restage of
classification/ (stage_private_classification.py) replaces the directory whole, so a delivery of another summary never stays beside it.
Output: one line per file group with counts, sizes and hashes (no content).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'implementation' / 'src'))
from investment_system.research.held_issuer_shards import verify_shards  # noqa: E402  (Codex's checker, used as is)

MAX_BYTES = 2 * 1024 * 1024
REPAIR_NAME = 'input-repair-comparison.json'
CONTEXT_KEYS = ('valuation_date', 'population', 'scoring_population', 'versions', 'classification', 'result_identity')


class StageError(Exception):
    pass


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read_set(delivery: Path) -> dict:
    files = {}
    for p in sorted(delivery.rglob('*')):
        if p.is_symlink():
            raise StageError('SYMLINK_REFUSED')
        if p.is_file():
            rel = p.relative_to(delivery).as_posix()
            data = p.read_bytes()
            if len(data) > MAX_BYTES:
                raise StageError('FILE_TOO_LARGE:' + rel)
            files[rel] = data
    if 'manifest.json' not in files:
        raise StageError('MANIFEST_MISSING')
    return files


def check(delivery: Path, pin: str, data_dir: Path) -> tuple:
    if len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
        raise StageError('PIN_INVALID')
    files = _read_set(delivery)
    if hashlib.sha256(files['manifest.json']).hexdigest() != pin:
        raise StageError('MANIFEST_PIN_MISMATCH')
    try:
        manifest = verify_shards(files)
    except Exception as error:          # Codex's checker raises its own refusal; its code is the message
        raise StageError('DELIVERY_REFUSED:' + (str(error) or type(error).__name__)) from None
    summary_path = data_dir / 'classification' / 'expanded_summary.json'
    if not summary_path.is_file():
        raise StageError('SUMMARY_NOT_STAGED')
    summary_bytes = summary_path.read_bytes()
    identity = manifest['identity']
    if hashlib.sha256(summary_bytes).hexdigest() != identity['summary']['sha256']:
        raise StageError('SUMMARY_MISMATCH:sha256')
    try:
        held = json.loads(summary_bytes)['calculation_counts']['scopes']['held_financial_subsample']
    except (KeyError, TypeError, ValueError):
        raise StageError('SUMMARY_COUNTS_MISSING') from None
    for key in CONTEXT_KEYS:
        if held.get(key) != identity['context'].get(key):
            raise StageError('SUMMARY_MISMATCH:' + key)
    return files, manifest


def check_repair(path: Path, pin: str, files: dict) -> bytes:
    if len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
        raise StageError('REPAIR_PIN_INVALID')
    if path.is_symlink() or not path.is_file():
        raise StageError('REPAIR_MISSING')
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise StageError('REPAIR_TOO_LARGE')
    if hashlib.sha256(data).hexdigest() != pin:
        raise StageError('REPAIR_PIN_MISMATCH')
    try:
        doc = json.loads(data)
    except ValueError:
        raise StageError('REPAIR_NOT_JSON') from None
    if not isinstance(doc, dict) or doc.get('schema_version') != 'sector-qgv-input-repair-comparison/1' or doc.get('treatment') != 'INPUT_CONNECTION_REPAIR':
        raise StageError('REPAIR_SCHEMA')
    scopes = json.loads(files['coverage.json']).get('scopes', {})
    hit = [k for k, s in scopes.items() if isinstance(s, dict) and isinstance(s.get('context'), dict)
           and s['context'].get('result_identity', {}).get('input_hash') == doc.get('after_input_hash')
           and s['context'].get('population', {}).get('denominator') == doc.get('denominator')
           and s['context'].get('valuation_date') == doc.get('valuation_date')]
    if not hit:
        raise StageError('REPAIR_RESULT_MISMATCH')
    return data


def stage(delivery: Path, pin: str, data_dir: Path, repair: Path | None = None, repair_pin: str | None = None) -> tuple:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if not (data_dir / 'classification').is_dir():
        raise StageError('CLASSIFICATION_NOT_STAGED')
    if (repair is None) != (repair_pin is None):
        raise StageError('REPAIR_PIN_REQUIRED')
    files, manifest = check(delivery, pin, data_dir)
    if repair is not None:
        files = {**files, REPAIR_NAME: check_repair(repair, repair_pin, files)}
    target = data_dir / 'classification' / 'expanded'
    fresh, old = target.with_name('expanded.staging'), target.with_name('expanded.previous')
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        for rel, data in files.items():
            out = fresh / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            if hashlib.sha256(out.read_bytes()).digest() != hashlib.sha256(data).digest():
                raise StageError('COPY_MISMATCH:' + rel)
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
    return files, manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--delivery', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--input-repair', type=Path)
    parser.add_argument('--input-repair-sha256')
    args = parser.parse_args(argv)
    try:
        files, manifest = stage(args.delivery, args.manifest_sha256, args.data_dir, args.input_repair, args.input_repair_sha256)
    except StageError as error:
        print('STAGE_PRIVATE_HELD_ISSUERS refused=' + str(error))
        return 1
    details = [k for k in files if k.startswith('expanded-detail/')]
    print('STAGE_PRIVATE_HELD_ISSUERS manifest sha256=' + hashlib.sha256(files['manifest.json']).hexdigest()
          + ' issuers=' + str(manifest['issuer_count']) + ' shards=' + str(len(details))
          + ' files=' + str(len(files)) + ' bytes=' + str(sum(len(v) for v in files.values()))
          + ' max_file_bytes=' + str(max(len(v) for v in files.values())) + ' kind=' + manifest['data_kind']
          + (' input_repair sha256=' + hashlib.sha256(files[REPAIR_NAME]).hexdigest() if REPAIR_NAME in files else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
