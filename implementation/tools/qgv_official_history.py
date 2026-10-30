#!/usr/bin/env python3
"""Private dated score history of the central QGV publication (owner decision D9, 2026-10-24; plan
CENTRAL_V_DC02_PLAN_20261024.md section 4; GSQ-024 "dated score history only in the private store, public = latest 1").

A NEW publication of this run (tools/qgv_official_check.py `inspect`: valid, named by an OK status of this attempt, verified in
it) is copied byte for byte to the private raw repository's release `qgv-official-<times.price_basis_date>`, as the asset
`<publication_id>.json` plus `<publication_id>.json.sha256` (the forward ledger's release pattern; one asset pair per
publication, so a second publication on the same IEX day is kept beside the first and nothing is ever replaced). The bytes are
the public file's: scores, ranks, reasons, coverage and basis times only, never a price (the strict reader runs first).

Token: env RAW_REPO_TOKEN (the write token the shard and ledger steps already hold); it is never printed. This step never
reads a price, never holds the publication's read token or HMAC key, and never writes the artifact directory.

    python implementation/tools/qgv_official_history.py --artifact-dir DIR

Stdout: ONE line of fixed codes (the tag, byte count and sha256 of the public bytes when uploaded):
    QGV_OFFICIAL_HISTORY skipped=NO_PUBLICATION|PUBLICATION_INVALID|STATUS_ABSENT|STATUS_INVALID|STATUS_MISMATCH|NOT_NEW|UNEXPECTED
    QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED
    QGV_OFFICIAL_HISTORY RAW_UPLOADED tag=qgv-official-YYYY-MM-DD bytes=<n> sha256=<hex>[ already_present]
    QGV_OFFICIAL_HISTORY RAW_UPLOAD_FAILED code=<CODE>
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


def upload(body: bytes, official: dict, *, call=None) -> str:
    """Release asset pair for one publication. Fixed codes only; the token is never printed."""
    call = call or raw_store_release.http
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
            url = f'{raw_store_release.UPLOADS}/repos/{RAW_REPO}/releases/{release_id}/assets?name={urllib.parse.quote(asset)}'
            status, _, _ = call('POST', url, data=data, headers={'Content-Type': kind})
            if status != 201:
                return f'RAW_UPLOAD_FAILED code=HTTP_{int(status)}'
        return f'RAW_UPLOADED tag={tag} bytes={len(body)} sha256={digest}' + (' already_present' if name in existing else '')
    except raw_store_release.ReleaseError as error:
        code = str(error).split()[0] if str(error) else 'RELEASE_ERROR'
        return 'RAW_UPLOAD_FAILED code=' + (code if code.isupper() else 'RELEASE_ERROR')
    except Exception:  # noqa: BLE001 - fixed code only (a message could carry a URL)
        return 'RAW_UPLOAD_FAILED code=UNEXPECTED'


def run(directory, *, environ=None, call=None) -> str:
    environ = os.environ if environ is None else environ
    result = check.inspect(directory)
    reason = skip_reason(result)
    if reason is not None:
        return 'QGV_OFFICIAL_HISTORY skipped=' + reason
    if not environ.get(RAW_TOKEN_ENV):
        return 'QGV_OFFICIAL_HISTORY RAW_UPLOAD_NOT_CONFIGURED'
    return 'QGV_OFFICIAL_HISTORY ' + upload(result['body'], result['official'], call=call)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--artifact-dir', required=True)
    a = ap.parse_args(argv)
    directory = Path(a.artifact_dir)
    if directory.is_symlink() or not directory.is_dir():
        print('QGV_OFFICIAL_HISTORY usage=ARTIFACT_DIR_INVALID')
        return 2
    try:
        print(run(directory))
    except Exception:  # noqa: BLE001 - fixed code only; the history never withholds the artifact
        print('QGV_OFFICIAL_HISTORY skipped=UNEXPECTED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
