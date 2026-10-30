#!/usr/bin/env python3
"""Price-free check of the central QGV publication files in a Pages artifact directory (GSQ-024; design
CENTRAL_V_PUBLICATION_DESIGN_20261018.md §3-2 "verify job", §6). No network, no Secret, no price.

- qgv-official.json, when present: the strict reader `qgv_official.parse` (exact key sets, forbidden keys anywhere, V axis =
  weighted factors, total = axes and weights, ranks = total order, coverage = row counts, size <= 2 MiB);
- qgv-official-status.json, when present: `qgv_official.require_status`;
- both: the status names the publication the artifact carries (publication_id, price basis day, verified_at) and is not
  NO_OFFICIAL_YET; a status without a publication carries no publication id.
Absent files are normal: before the first publication, or when the V step did not run (the publisher then leaves the last good
copy or nothing).

`inspect` is shared with tools/qgv_official_history.py: a publication is NEW (made by the attempt the status records) when the
status is OK, names it, and its verified_at is not earlier than the attempt's start (a kept live copy was verified by an earlier
run, which finished before this run started: the daily workflow runs one at a time).

    python implementation/tools/qgv_official_check.py --artifact-dir DIR

Stdout: ONE line of fixed codes, dates and counts (public values only):
    QGV_OFFICIAL_CHECK publication=VALID|ABSENT|INVALID status=VALID|ABSENT|INVALID consistent=YES|NO|- new=YES|NO
        attempt=<state|-> reason=<code|-> basis=<day|-> rows=<n> ranked=<n>
Exit 0 when every present file is valid and the two agree; 1 otherwise; 2 = usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.qgv import qgv_official as qo  # noqa: E402


def _read(directory: Path, name: str):
    """bytes | None (absent) ; ValueError for a symlink, a non-file or an oversized file."""
    path = directory / name
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file() or path.stat().st_size > qo.MAX_BYTES:
        raise ValueError('UNREADABLE')
    return path.read_bytes()


def _clock(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))


def inspect(directory) -> dict:
    """Fixed codes about the two files (never raises for file contents)."""
    directory = Path(directory)
    result = {'publication': 'ABSENT', 'status': 'ABSENT', 'consistent': None, 'new': False, 'attempt': None, 'reason': None,
              'basis': None, 'rows': 0, 'ranked': 0, 'body': None, 'official': None}
    try:
        body = _read(directory, qo.FILENAME)
        if body is not None:
            result['official'], result['body'], result['publication'] = qo.parse(body), body, 'VALID'
    except ValueError:
        result['publication'] = 'INVALID'
    status = None
    try:
        raw = _read(directory, qo.STATUS_FILENAME)
        if raw is not None:
            status = json.loads(raw.decode('utf-8'))
            qo.require_status(status)
            result['status'], result['attempt'], result['reason'] = 'VALID', status['attempt_state'], status['reason_code']
    except (ValueError, UnicodeDecodeError, RecursionError):
        result['status'], status = 'INVALID', None
    official = result['official']
    if official is not None:
        result.update(basis=official['times']['price_basis_date'], rows=len(official['rows']), ranked=official['coverage']['ranked'])
    if result['status'] == 'VALID' and result['publication'] != 'INVALID':
        if official is None:
            result['consistent'] = status['official_publication_id'] is None
        else:
            t = official['times']
            result['consistent'] = (status['attempt_state'] != 'NO_OFFICIAL_YET'
                                    and status['official_publication_id'] == official['publication_id']
                                    and status['official_price_basis_date'] == t['price_basis_date']
                                    and status['official_verified_at'] == t['verified_at'])
            result['new'] = bool(result['consistent'] and status['attempt_state'] == 'OK' and t['verified_at'] is not None
                                 and _clock(t['verified_at']) >= _clock(status['last_attempt_at']))
    return result


def line(result) -> str:
    yes_no = {True: 'YES', False: 'NO', None: '-'}
    return (f"QGV_OFFICIAL_CHECK publication={result['publication']} status={result['status']} "
            f"consistent={yes_no[result['consistent']]} new={yes_no[result['new']]} attempt={result['attempt'] or '-'} "
            f"reason={result['reason'] or '-'} basis={result['basis'] or '-'} rows={result['rows']} ranked={result['ranked']}")


def ok(result) -> bool:
    return 'INVALID' not in (result['publication'], result['status']) and result['consistent'] is not False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--artifact-dir', required=True)
    a = ap.parse_args(argv)
    directory = Path(a.artifact_dir)
    if directory.is_symlink() or not directory.is_dir():
        print('QGV_OFFICIAL_CHECK usage=ARTIFACT_DIR_INVALID')
        return 2
    try:
        result = inspect(directory)
    except Exception:  # noqa: BLE001 - fixed code only
        print('QGV_OFFICIAL_CHECK unexpected=READ_FAILED')
        return 1
    print(line(result))
    return 0 if ok(result) else 1


if __name__ == '__main__':
    raise SystemExit(main())
