#!/usr/bin/env python3
"""Stage Codex #525's company-industry-macro-query/1 output for the owner-checked private Worker (owner 2026-11-09 queue item 5).

The Worker serves /kis/classification?part=industry_macro from classification/industry_macro.json on the private data branch. This
copies the query byte for byte after checking: its SHA-256 equals --sha256 (the pin from the authenticated handoff manifest), it is
one JSON object of schema company-industry-macro-query/1 within 2 MiB, its classification context (date, hash, dictionary, mapping)
equals the staged classification/view.json, and --data-dir is outside this public repository. A later restage of classification/
replaces the directory whole, so a query of another classification never stays beside it. Prints counts and the hash only.

  python implementation/tools/stage_private_industry_macro.py --query <query.json> --sha256 <pin> --data-dir <private data checkout>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 2 * 1024 * 1024
CONTEXT = ('valuation_date', 'classification_hash', 'dictionary_version', 'mapping_version')


class StageError(Exception):
    pass


def stage(query: Path, pin: str, data_dir: Path) -> dict:
    try:
        data_dir.resolve().relative_to(REPO_ROOT.resolve())
        raise StageError('DATA_DIR_INSIDE_PUBLIC_REPOSITORY')
    except ValueError:
        pass
    raw = query.read_bytes()
    if len(raw) > MAX_BYTES:
        raise StageError('FILE_TOO_LARGE')
    if hashlib.sha256(raw).hexdigest() != pin:
        raise StageError('PIN_MISMATCH')
    q = json.loads(raw)
    if not isinstance(q, dict) or q.get('schema_version') != 'company-industry-macro-query/1':
        raise StageError('SCHEMA')
    view_path = data_dir / 'classification' / 'view.json'
    if not view_path.is_file():
        raise StageError('VIEW_NOT_STAGED')
    view = json.loads(view_path.read_bytes())
    for k in CONTEXT:
        if q['classification_context'].get(k) != view.get(k):
            raise StageError('CLASSIFICATION_CONTEXT_MISMATCH:' + k)
    out = data_dir / 'classification' / 'industry_macro.json'
    tmp = out.with_name('industry_macro.json.staging')
    tmp.write_bytes(raw)
    if hashlib.sha256(tmp.read_bytes()).hexdigest() != pin:
        tmp.unlink()
        raise StageError('COPY_MISMATCH')
    tmp.replace(out)
    return q['counts']


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--query', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--data-dir', required=True, type=Path)
    a = parser.parse_args(argv)
    try:
        counts = stage(a.query, a.sha256, a.data_dir)
    except StageError as e:
        print('STAGE_PRIVATE_INDUSTRY_MACRO refused=' + str(e))
        return 1
    print('STAGE_PRIVATE_INDUSTRY_MACRO sha256=' + a.sha256 + ' ' + ' '.join(f'{k}={v}' for k, v in sorted(counts.items())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
