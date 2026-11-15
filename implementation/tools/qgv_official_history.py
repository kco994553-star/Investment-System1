#!/usr/bin/env python3
"""Private dated score history of the central QGV publication (owner decision D9, 2026-10-24; plan
CENTRAL_V_DC02_PLAN_20261024.md section 4; GSQ-024 "dated score history only in the private store, public = latest 1").

A NEW publication of this run (tools/qgv_official_check.py `inspect`: valid, named by an OK status of this attempt, verified in
it) is copied byte for byte to the private raw repository's release `qgv-official-<times.price_basis_date>`, as the asset
`<publication_id>.json` plus `<publication_id>.json.sha256` (the forward ledger's release pattern; one asset pair per
publication, so a second publication on the same IEX day is kept beside the first and nothing is ever replaced). The bytes are
the public file's: scores, ranks, reasons, coverage and basis times only, never a price (the strict reader runs first).

Inputs (owner decision 2026-11-15): with the publication, the artifact's `sec-qgv2.json` it was built from is copied to the same
release as `inputs-<inputs_sha256>.json` plus `inputs-<inputs_sha256>.json.sha256` (same sha256-file format), only when the
bytes' sha256 equals the publication's own `inputs[0].sha256` (the strict reader checks it names `sec-qgv2.json`). Price-free
public data (the Pages file of the same run). An existing asset is never replaced. When the inputs are not kept (file missing or
unreadable, another hash, upload failed, or the publication copy failed first) the publication copy is unchanged, the exit stays
0 and a GitHub Actions warning line precedes the fixed line: `::warning::QGV_OFFICIAL_HISTORY inputs <CODE>`.

Token: env RAW_REPO_TOKEN (the write token the shard and ledger steps already hold); it is never printed. This step never
reads a price, never holds the publication's read token or HMAC key, and never writes the artifact directory.

    python implementation/tools/qgv_official_history.py --artifact-dir DIR

Stdout: ONE line of fixed codes (the tag, byte count and sha256 of the public bytes when uploaded), preceded by the one
`::warning::QGV_OFFICIAL_HISTORY inputs <INPUTS>` line when the inputs were not kept:
    QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION|PUBLICATION_INVALID|STATUS_ABSENT|STATUS_INVALID|STATUS_MISMATCH|NOT_NEW|UNEXPECTED
    QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED
    QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-YYYY-MM-DD bytes=<n> sha256=<hex>[ already_present] inputs=<INPUTS>
    QGV_OFFICIAL_HISTORY RAW_UPLOAD_FAILED code=<CODE> inputs=NOT_ATTEMPTED
    INPUTS kept: UPLOADED|ALREADY_PRESENT; not kept (warning):
           MISSING|UNREADABLE|HASH_MISMATCH|UPLOAD_FAILED_HTTP_<n>|UPLOAD_FAILED|NOT_ATTEMPTED
Exit 0 for every outcome (the history never withholds the artifact); 2 = usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qgv_official_check as check  # noqa: E402
import raw_store_release  # noqa: E402

RAW_REPO = 'kco994553-star/investment-system1-raw'
RAW_TOKEN_ENV = 'RAW_REPO_TOKEN'
TAG_PREFIX = 'qgv-official-'
INPUTS_PREFIX = 'inputs-'
INPUTS_KEPT = ('UPLOADED', 'ALREADY_PRESENT')


def skip_reason(result) -> str | None:
    """None when the artifact carries a NEW publication of this run, else the fixed skip code."""
    if result['publication'] == 'ABSENT':
        return 'NO_PUBLICATION'
    if result['publication'] == 'INVALID':
        return 'PUBLICATION_INVALID'
    if result['status'] == 'ABSENT':
        return 'STATUS_ABSENT'
    if result['status'] == 'INVALID':
        return 'STATUS_INVALID'
    if not result['consistent']:
        return 'STATUS_MISMATCH'
    return None if result['new'] else 'NOT_NEW'


def read_inputs(directory, official: dict):
    """(bytes, None) when the artifact's sec-qgv2.json is the publication's recorded input, else (None, fixed code)."""
    try:
        expected = official['inputs'][0]['sha256']      # strict reader: one entry, file sec-qgv2.json, 64 lowercase hex
        data = check._read(Path(directory), official['inputs'][0]['file'])   # no symlink, a regular file, <= 2 MiB
    except Exception:  # noqa: BLE001 - fixed code only; the publication copy goes on
        return None, 'UNREADABLE'
    if data is None:
        return None, 'MISSING'
    if hashlib.sha256(data).hexdigest() != expected:
        return None, 'HASH_MISMATCH'
    return data, None


def _post(call, release_id: int, asset: str, data: bytes, kind: str) -> int:
    url = f'{raw_store_release.UPLOADS}/repos/{RAW_REPO}/releases/{release_id}/assets?name={urllib.parse.quote(asset)}'
    status, _, _ = call('POST', url, data=data, headers={'Content-Type': kind})
    return status


def upload_inputs(data, code, official: dict, release_id: int, existing: set, call) -> str:
    """The inputs asset pair beside the publication (fixed code; an existing asset is never replaced)."""
    if data is None:
        return code
    digest = official['inputs'][0]['sha256']
    name = INPUTS_PREFIX + digest + '.json'
    pair = ((name, data, 'application/json'), (name + '.sha256', f'{digest}  {name}\n'.encode(), 'text/plain'))
    if all(asset in existing for asset, _, _ in pair):
        return 'ALREADY_PRESENT'
    try:
        for asset, body, kind in pair:
            if asset in existing:
                continue
            status = _post(call, release_id, asset, body, kind)
            if status != 201:
                return f'UPLOAD_FAILED_HTTP_{int(status)}'
    except Exception:  # noqa: BLE001 - fixed code only (a message could carry a URL)
        return 'UPLOAD_FAILED'
    return 'UPLOADED'


def upload(body: bytes, official: dict, *, call=None, directory=None) -> str:
    """Release asset pair for one publication, then its inputs pair. Fixed codes only; the token is never printed."""
    call = call or raw_store_release.http
    inputs = read_inputs(directory, official) if directory is not None else (None, 'MISSING')
    tag = TAG_PREFIX + official['times']['price_basis_date']
    name = official['publication_id'] + '.json'
    digest = hashlib.sha256(body).hexdigest()
    try:
        release = raw_store_release.release_for_tag(RAW_REPO, tag, create=True, call=call)
        release_id = release.get('id') if isinstance(release, dict) else None
        if type(release_id) is not int or release_id <= 0:
            return 'RAW_UPLOAD_FAILED code=RELEASE_INVALID'
        existing = {a.get('name') for a in release.get('assets', []) if isinstance(a, dict)}
        for asset, data, kind in ((name, body, 'application/json'),
                                  (name + '.sha256', f'{digest}  {name}\n'.encode(), 'text/plain')):
            if asset in existing:
                continue
            status = _post(call, release_id, asset, data, kind)
            if status != 201:
                return f'RAW_UPLOAD_FAILED code=HTTP_{int(status)} inputs=NOT_ATTEMPTED'
        line = f'RAW_UPLOADED tag={tag} bytes={len(body)} sha256={digest}' + (' already_present' if name in existing else '')
        return line + ' inputs=' + upload_inputs(*inputs, official, release_id, existing, call)
    except raw_store_release.ReleaseError as error:
        code = str(error).split()[0] if str(error) else 'RELEASE_ERROR'
        return 'RAW_UPLOAD_FAILED code=' + (code if code.isupper() else 'RELEASE_ERROR') + ' inputs=NOT_ATTEMPTED'
    except Exception:  # noqa: BLE001 - fixed code only (a message could carry a URL)
        return 'RAW_UPLOAD_FAILED code=UNEXPECTED inputs=NOT_ATTEMPTED'


def warning(line: str) -> str | None:
    """The GitHub Actions warning annotation for inputs that were not kept (None when kept or not applicable)."""
    code = line.rsplit(' inputs=', 1)[1] if ' inputs=' in line else None
    if code is None or code in INPUTS_KEPT:
        return None
    return '::warning::QGV_OFFICIAL_HISTORY inputs ' + code


def run(directory, *, environ=None, call=None) -> str:
    environ = os.environ if environ is None else environ
    result = check.inspect(directory)
    reason = skip_reason(result)
    if reason is not None:
        return 'QGV_OFFICIAL_HISTORY skipped=' + reason
    if not environ.get(RAW_TOKEN_ENV):
        return 'QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED'
    return 'QGV_OFFICIAL_HISTORY ' + upload(result['body'], result['official'], call=call, directory=directory)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--artifact-dir', required=True)
    a = ap.parse_args(argv)
    directory = Path(a.artifact_dir)
    if directory.is_symlink() or not directory.is_dir():
        print('QGV_OFFICIAL_HISTORY usage=ARTIFACT_DIR_INVALID')
        return 2
    try:
        line = run(directory)
    except Exception:  # noqa: BLE001 - fixed code only; the history never withholds the artifact
        line = 'QGV_OFFICIAL_HISTORY skipped=UNEXPECTED'
    note = warning(line)
    if note is not None:
        print(note)                 # a run-summary warning (fixed code); the step still exits 0
    print(line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
