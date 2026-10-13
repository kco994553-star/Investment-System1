#!/usr/bin/env python3
"""Daily append-only forward validation ledger -> public price-free `forward-validation-ledger.json`.

User decision 2026-10-11: start 2026-10-19, TARGET v0, QGV standard v1, all v1
UNCALIBRATED; V goes to a separate version; Holdout stays unused. The previous
ledger is read from the live Pages copy and carried byte-identically:

- network error or an invalid previous ledger -> write nothing, exit 1 (history is never lost);
- 404 before the start date -> a new NOT_STARTED ledger; 404 on/after the start -> exit 1
  unless --bootstrap-after-start is given explicitly (first publication only);
- a record is added only on a completed NYSE session day, on that day, from this run's
  `sec-qg-factors.json` and `actual-catalog.json` in --out; a record that already exists is kept.

With RAW_REPO_TOKEN set, the day's ledger is copied to the private repository's
release `forward-ledger-YYYY-MM-DD`; otherwise RAW_UPLOAD_NOT_CONFIGURED. Only
fixed codes and counts are printed: no values, URLs or secrets.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from investment_system.validation import forward_ledger as fl
import raw_store_release

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + fl.FILENAME
RAW_REPO = 'kco994553-star/investment-system1-raw'
RAW_TOKEN_ENV = 'RAW_REPO_TOKEN'
INPUT_LIMIT = 4 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('FORWARD_LEDGER ARGUMENTS_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def fetch_previous(*, open_response=None):
    """Live Pages copy -> (validated payload, original bytes); None on 404. Network errors raise OSError."""
    request = urllib.request.Request(SOURCE, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != SOURCE:
                raise OSError('PREVIOUS_FETCH_FAILED')
            body = response.read(fl.MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError, ValueError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    return fl.require_ledger(fl.parse_json(body)), body


def _read_input(directory, name):
    path = Path(directory) / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > INPUT_LIMIT:
        return None
    return path.read_bytes()


def write(directory, body):
    directory = Path(directory)
    destination = directory / fl.FILENAME
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink():
        raise ValueError('FORWARD_LEDGER_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.forward-ledger-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def upload_ledger(body, *, tag, call=None):
    """Private dated release asset (ledger JSON + sha256). Fixed status codes only; the token is never printed."""
    call = call or raw_store_release.http
    digest = hashlib.sha256(body).hexdigest()
    try:
        release = raw_store_release.release_for_tag(RAW_REPO, tag, create=True, call=call)
        release_id = release.get('id') if isinstance(release, dict) else None
        if type(release_id) is not int or release_id <= 0:
            return 'RAW_UPLOAD_FAILED code=RELEASE_INVALID'
        existing = {a.get('name'): a for a in release.get('assets', []) if isinstance(a, dict)}
        for name, data, kind in ((fl.FILENAME, body, 'application/json'),
                                 (fl.FILENAME + '.sha256', f'{digest}  {fl.FILENAME}\n'.encode(), 'text/plain')):
            if name in existing:
                continue
            url = f'{raw_store_release.UPLOADS}/repos/{RAW_REPO}/releases/{release_id}/assets?name={urllib.parse.quote(name)}'
            status, _, _ = call('POST', url, data=data, headers={'Content-Type': kind})
            if status != 201:
                return f'RAW_UPLOAD_FAILED code=HTTP_{int(status)}'
        return f'RAW_UPLOADED tag={tag} bytes={len(body)} sha256={digest}' + (' already_present' if fl.FILENAME in existing else '')
    except raw_store_release.ReleaseError as error:
        code = str(error).split()[0] if str(error) else 'RELEASE_ERROR'
        return 'RAW_UPLOAD_FAILED code=' + (code if code.isupper() else 'RELEASE_ERROR')
    except Exception:
        return 'RAW_UPLOAD_FAILED'


def run(out, *, preserve_only=False, bootstrap=False, environ=None, now=_utc_now, open_previous=None, upload_call=None):
    environ = os.environ if environ is None else environ
    try:
        fetched = fetch_previous(open_response=open_previous)
    except ValueError:
        print('FORWARD_LEDGER PREVIOUS_INVALID nothing_written')
        return 1
    except Exception:
        print('FORWARD_LEDGER PREVIOUS_FETCH_FAILED nothing_written')
        return 1
    previous, previous_body = fetched if fetched is not None else (None, None)
    if preserve_only:
        if previous is None:
            print('FORWARD_LEDGER PREVIOUS_NOT_AVAILABLE')
            return 0
        try:
            write(out, previous_body)
        except Exception:
            print('FORWARD_LEDGER OUTPUT_FAILED')
            return 1
        print(f"FORWARD_LEDGER PREVIOUS_RESTORED records={len(previous['versions'][fl.VERSION])}")
        return 0
    moment = now()
    today = fl.eastern(moment).date()
    if previous is None and today >= fl.START_DATE and not bootstrap:
        print('FORWARD_LEDGER PREVIOUS_MISSING_AFTER_START nothing_written')
        return 1
    try:
        session = fl.completed_session(moment)
    except fl.CalendarNotConfigured:
        print('FORWARD_LEDGER CALENDAR_NOT_CONFIGURED')
        session = None
    appended, record_state, v2_record_state = False, None, None
    try:
        ledger = fl.finalize(previous, moment) if previous is not None else fl.new_ledger(moment)
        if session is not None and session >= fl.START_DATE:
            catalog_body = _read_input(out, 'actual-catalog.json')
            for version in (fl.VERSION, fl.V2_VERSION):
                rows = ledger['versions'][version]
                if rows and rows[-1]['date'] >= session.isoformat():
                    if version == fl.VERSION:
                        record_state = 'EXISTS' if rows[-1]['date'] == session.isoformat() else None
                    else:
                        v2_record_state = 'EXISTS' if rows[-1]['date'] == session.isoformat() else None
                    continue
                if version == fl.VERSION:
                    record = fl.build_record(now=moment, session=session, qg_body=_read_input(out, 'sec-qg-factors.json'),
                                             catalog_body=catalog_body)
                else:
                    record = fl.build_v2_record(now=moment, session=session, qgv2_body=_read_input(out, 'sec-qgv2.json'), dart_body=_read_input(out, 'dart-financials.json'),
                                                catalog_body=catalog_body)
                ledger = fl.append(ledger, record, moment)
                appended = True
                if version == fl.VERSION:
                    record_state = record['state']
                else:
                    v2_record_state = record['state']
        ledger = fl.finalize(ledger, moment)
        fl.require_ledger(ledger)
        fl.require_append_only(previous, ledger)
        body = fl.encode(ledger)
        write(out, body)
    except Exception:
        print('FORWARD_LEDGER OUTPUT_FAILED nothing_written')
        return 1
    rows = ledger['versions'][fl.VERSION]
    print(f"FORWARD_LEDGER status={ledger['status']} records={len(rows)} appended={int(appended)} "
          f"record={record_state or 'NONE'} session={'NONE' if session is None else session.isoformat()} "
          f"v2_records={len(ledger['versions'][fl.V2_VERSION])} v2_record={v2_record_state or 'NONE'}")
    token = environ.get(RAW_TOKEN_ENV) or None
    if token is None:
        print('RAW_UPLOAD_NOT_CONFIGURED')
    elif session is not None and rows and rows[-1]['date'] == session.isoformat():
        print(upload_ledger(body, tag='forward-ledger-' + session.isoformat(), call=upload_call))
    else:
        print('RAW_UPLOAD_SKIPPED no_session_record')
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--preserve-only', action='store_true')
    parser.add_argument('--bootstrap-after-start', action='store_true')
    args = parser.parse_args(argv)
    return run(args.out, preserve_only=args.preserve_only, bootstrap=args.bootstrap_after_start)


if __name__ == '__main__':
    raise SystemExit(main())
