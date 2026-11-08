#!/usr/bin/env python3
"""Stage the held common classification bundle for the owner-checked private Worker (owner 2026-11-08 「통합 결과 수령」 2항).

The private Worker route /kis/classification?part=<part> (implementation/worker/src/index.js) serves one file per part from the
data branch of the private repository: classification/<part>.json. This tool copies Codex's held result files there BYTE FOR BYTE
after checking each against the Codex handoff manifest (size and SHA-256) and the schema the Worker and the screen expect. It
computes nothing, re-serializes nothing and fetches nothing.

  python implementation/tools/stage_private_classification.py --source <extracted held bundle dir> \
      --manifest <its handoff-manifest.json> --data-dir <checkout of the private repository's data branch>

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


def check(source: Path, manifest: dict) -> list:
    """→ [(part, source path, bytes, sha256)] after every check; raises StageError at the first fault."""
    entries = _manifest_entries(manifest)
    staged, head = [], None
    for part, (rel, schema) in PARTS.items():
        entry = entries.get(rel)
        if entry is None:
            raise StageError('MANIFEST_PART_MISSING:' + part)
        path = source / rel
        if path.is_symlink() or not path.is_file():
            raise StageError('FILE_MISSING:' + part)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != entry.get('size') or digest != entry.get('sha256'):
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
        elif part != 'dictionary' and (value.get('classification_hash'), value.get('valuation_date')) != head:
            raise StageError('PART_OTHER_RECORDS:' + part)
        staged.append((part, path, len(data), digest))
    return staged


def stage(source: Path, manifest_path: Path, data_dir: Path) -> list:
    if _inside(data_dir, REPO_ROOT):
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    if not data_dir.is_dir():
        raise StageError('DATA_DIR_MISSING')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StageError('MANIFEST_UNREADABLE') from error
    staged = check(source, manifest)          # everything is checked before anything is written
    target = data_dir / 'classification'
    target.mkdir(exist_ok=True)
    for part, path, _, digest in staged:
        out = target / (part + '.json')
        shutil.copyfile(path, out)
        if hashlib.sha256(out.read_bytes()).hexdigest() != digest:
            raise StageError('COPY_MISMATCH:' + part)
    return staged


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--data-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        staged = stage(args.source, args.manifest, args.data_dir)
    except StageError as error:
        print('STAGE_PRIVATE_CLASSIFICATION refused=' + str(error))
        return 1
    for part, _, size, digest in staged:
        print(f'STAGE_PRIVATE_CLASSIFICATION part={part} bytes={size} sha256={digest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
