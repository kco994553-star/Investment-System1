#!/usr/bin/env python3
"""Stage the held common classification bundle for the owner-checked private Worker (owner 2026-11-08 「통합 결과 수령」 2항).

The private Worker route /kis/classification?part=<part> (implementation/worker/src/index.js) serves one file per part from the
data branch of the private repository: classification/<part>.json. This tool copies Codex's held result files there BYTE FOR BYTE
after checking each against the Codex handoff manifest (size and SHA-256) and the schema the Worker and the screen expect. It
computes nothing, re-serializes nothing and fetches nothing.

  python implementation/tools/stage_private_classification.py --source <extracted held bundle dir> \
      --manifest <its handoff-manifest.json> --data-dir <checkout of the private repository's data branch>

With --expanded-source / --expanded-manifest it also stages the expanded held issuer sample's summary (Codex #520, a separate
population) as classification/expanded_summary.json, checked the same way.

The current classification/ is replaced whole or not at all (owner 2026-11-08): the view's dictionary + mapping pair must be one of
VERSION_PAIRS, the dictionary must be that version (and a /2 pair must name one boundary policy), every part must share the view's
classification hash and evaluation date; on any failure the existing connection stays as it was.

Refuses (exit 1, nothing written) when a file is missing, its size or SHA-256 differs from the manifest, it is not one JSON object
of its part's schema, every part does not name the same classification_hash and valuation_date as the view, or --data-dir is
inside this public repository. Output: one line per part with its size and SHA-256 (no file content), and a README table row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

# part → (path inside the Codex handoff, schema_version the file must carry). Order = the screen's read order.
PARTS = {
    'view': ('result/classification-view.json', 'common-classification-view/1'),
    'technical': ('result/technical.json', 'common-classification-technical/1'),
    'macro': ('result/macro.json', 'common-classification-macro/1'),
    'qgv_links': ('result/qgv-classification-links.json', 'common-classification-qgv-links/1'),
    'dictionary': ('result/dictionary.json', 'common-classification-dictionary/1'),
}
# The expanded held issuer sample (Codex #520): a separate population; its summary only (its view / preview exceed the Worker bound).
EXPANDED_PARTS = {'expanded_summary': ('final/summary.json', 'held-expanded-classification-summary/1')}
# The exact dictionary + mapping pairs the screen reads (classification.js VERSION_PAIRS; Codex #520 41f2a25b).
VERSION_PAIRS = {'common-industry-dictionary/1': 'common-classification-map/1',
                 'common-industry-dictionary/2': 'common-classification-map/2'}
POLICY_DICTIONARY = 'common-industry-dictionary/2'
MAX_BYTES = 2 * 1024 * 1024          # the Worker's per-file bound (MAX_CHART_BYTES)
REPO_ROOT = Path(__file__).resolve().parents[2]


class StageError(Exception):
    pass


def _manifest_entries(manifest: dict) -> dict:
    files = manifest.get('files')
    if not isinstance(files, list):
        raise StageError('MANIFEST_FILES_MISSING')
    out = {}
    for f in files:
        if not isinstance(f, dict) or not isinstance(f.get('path'), str):
            raise StageError('MANIFEST_ENTRY_INVALID')
        if f['path'] in out:
            raise StageError('MANIFEST_DUPLICATE_PATH')
        out[f['path']] = f
    return out


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check(source: Path, manifest: dict, parts: dict = PARTS) -> list:
    """→ [(part, source path, bytes, sha256)] after every check; raises StageError at the first fault."""
    entries = _manifest_entries(manifest)
    staged, head = [], None
    for part, (rel, schema) in parts.items():
        entry = entries.get(rel)
        if entry is None:
            raise StageError('MANIFEST_PART_MISSING:' + part)
        path = source / rel
        if path.is_symlink() or not path.is_file():
            raise StageError('FILE_MISSING:' + part)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        size = entry.get('size', entry.get('bytes'))      # the handoff manifests spell it either way
        if len(data) != size or digest != entry.get('sha256'):
            raise StageError('MANIFEST_MISMATCH:' + part)
        if len(data) > MAX_BYTES:
            raise StageError('TOO_LARGE_FOR_WORKER:' + part)
        try:
            value = json.loads(data.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise StageError('NOT_JSON:' + part) from error
        if not isinstance(value, dict) or value.get('schema_version') != schema:
            raise StageError('SCHEMA_MISMATCH:' + part)
        if part == 'view':
            head = (value.get('classification_hash'), value.get('valuation_date'))
            if not all(isinstance(x, str) and x for x in head):
                raise StageError('VIEW_IDENTITY_MISSING')
            version = value.get('dictionary_version')
            if VERSION_PAIRS.get(version) != value.get('mapping_version') or version is None:
                raise StageError('VERSION_PAIR_INVALID')
            policy = value.get('boundary_policy')
            if (version == POLICY_DICTIONARY) != isinstance(policy, dict):
                raise StageError('POLICY_VERSION_MISMATCH')
        elif part == 'dictionary':
            if value.get('version') != version:
                raise StageError('PART_OTHER_VERSION:dictionary')
            if version == POLICY_DICTIONARY:
                p = value.get('policy') or {}
                if (p.get('version'), p.get('source'), p.get('approved_date')) != (policy.get('version'), policy.get('source'), policy.get('approved_date')):
                    raise StageError('POLICY_VERSION_MISMATCH')
        elif part in ('technical', 'macro', 'qgv_links') and (value.get('classification_hash'), value.get('valuation_date')) != head:
            raise StageError('PART_OTHER_RECORDS:' + part)
        staged.append((part, path, len(data), digest))
    return staged


def _manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StageError('MANIFEST_UNREADABLE') from error


def stage(source: Path, manifest_path: Path, data_dir: Path, expanded: tuple | None = None) -> list:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if not data_dir.is_dir():
        raise StageError('DATA_DIR_MISSING')
    staged = check(source, _manifest(manifest_path))          # everything is checked before anything is written
    if expanded is not None:
        staged += check(expanded[0], _manifest(expanded[1]), EXPANDED_PARTS)
    # The current connection is replaced whole or not at all: the new set is written and re-hashed beside it, then swapped in;
    # on any failure the staging copy is removed and the existing classification/ stays as it was.
    target, fresh, old = data_dir / 'classification', data_dir / 'classification.staging', data_dir / 'classification.previous'
    for leftover in (fresh, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        fresh.mkdir()
        if expanded is None and (target / 'expanded_summary.json').is_file():
            raise StageError('EXPANDED_SUMMARY_REQUIRED')     # never keep a summary of another delivery beside a new set
        for part, path, _, digest in staged:
            out = fresh / (part + '.json')
            shutil.copyfile(path, out)
            if hashlib.sha256(out.read_bytes()).hexdigest() != digest:
                raise StageError('COPY_MISMATCH:' + part)
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
    return staged


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--expanded-source', type=Path, help='the expanded held issuer sample handoff (its own population)')
    parser.add_argument('--expanded-manifest', type=Path)
    args = parser.parse_args(argv)
    if (args.expanded_source is None) != (args.expanded_manifest is None):
        parser.error('--expanded-source and --expanded-manifest go together')
    try:
        staged = stage(args.source, args.manifest, args.data_dir,
                       (args.expanded_source, args.expanded_manifest) if args.expanded_source else None)
    except StageError as error:
        print('STAGE_PRIVATE_CLASSIFICATION refused=' + str(error))
        return 1
    for part, _, size, digest in staged:
        print(f'STAGE_PRIVATE_CLASSIFICATION part={part} bytes={size} sha256={digest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
