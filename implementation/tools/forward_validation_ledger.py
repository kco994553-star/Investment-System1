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

W-F2 (user decision 2026-10-15): with FORWARD_LEDGER_PREVIOUS_SOURCE=RAW_FIRST and RAW_REPO_TOKEN set (the daily
workflow only), the newest dated private copy is read first. It is taken instead of the Pages copy only when it passes
the same validator, its sha256 asset matches, its last session is on or after the Pages copy's last session and it
carries every Pages record byte-identically; otherwise the Pages copy is used. A day whose deploy was withheld is
therefore carried into the next public ledger instead of being lost. Pages errors keep failing closed as before.
"""
import argparse
from datetime import datetime, timedelta, timezone
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
PREVIOUS_SOURCE_ENV = 'FORWARD_LEDGER_PREVIOUS_SOURCE'
RAW_FIRST = 'RAW_FIRST'
RAW_TAG_PREFIX = 'forward-ledger-'
# Session days probed for a dated private copy, newest first (about two calendar weeks). Older copies fall back to Pages.
RAW_LOOKBACK_SESSIONS = 10
RAW_READ_TIMEOUT = 30


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


class _ShortTimeoutOpener:
    """Opener for the private release reads: no redirect following (the token is never forwarded), short timeout."""

    def __init__(self):
        self._opener = urllib.request.build_opener(raw_store_release._NoRedirect)

    def open(self, request, timeout=None):
        return self._opener.open(request, timeout=RAW_READ_TIMEOUT)


def _raw_read_call(method, url, **kwargs):
    return raw_store_release.http(method, url, opener=_ShortTimeoutOpener(), **kwargs)


def _raw_tags(moment):
    """Dated private release tags to probe, newest first: NYSE session days from today back, never before the start."""
    day, tags = fl.eastern(moment).date(), []
    while day >= fl.START_DATE and len(tags) < RAW_LOOKBACK_SESSIONS:
        if fl.is_session_day(day):
            tags.append(RAW_TAG_PREFIX + day.isoformat())
        day -= timedelta(days=1)
    return tags


def _raw_asset(release, name, call):
    asset = next((a for a in release.get('assets', []) if isinstance(a, dict) and a.get('name') == name), None)
    asset_id = asset.get('id') if asset is not None else None
    if type(asset_id) is not int or asset_id <= 0:
        raise ValueError('RAW_ASSET_MISSING')
    status, headers, body = call('GET', f'{raw_store_release.API}/repos/{RAW_REPO}/releases/assets/{asset_id}',
                                 headers={'Accept': 'application/octet-stream'})
    if status in (301, 302, 303, 307, 308):
        location = (headers or {}).get('Location') or (headers or {}).get('location')
        if not location or urllib.parse.urlparse(location).scheme != 'https':
            raise ValueError('RAW_ASSET_REDIRECT_INVALID')
        # The signed download location gets no Authorization header.
        status, _, body = call('GET', location, headers={'Accept': 'application/octet-stream'}, auth=False)
    if status != 200 or not isinstance(body, (bytes, bytearray)) or len(body) > fl.MAX_BYTES:
        raise ValueError('RAW_ASSET_UNREADABLE')
    return bytes(body)


def fetch_previous_raw(moment, *, call=None):
    """Newest valid dated private copy -> ((payload, bytes), code) or (None, code). Fixed codes only.

    A missing tag (404) moves to the previous session day; an invalid copy (validator, sha256 asset) too. Any other
    lookup failure stops the search: the caller then falls back to the Pages copy."""
    call = call or _raw_read_call
    try:
        tags = _raw_tags(moment)
    except fl.CalendarNotConfigured:
        return None, 'CALENDAR_NOT_CONFIGURED'
    code = 'NONE'
    for tag in tags:
        try:
            status, _, body = call('GET', f'{raw_store_release.API}/repos/{RAW_REPO}/releases/tags/{urllib.parse.quote(tag)}')
        except Exception:
            return None, 'FETCH_FAILED'
        if status == 404:
            continue
        if status != 200:
            return None, 'HTTP_' + str(status) if type(status) is int else 'FETCH_FAILED'
        try:
            release = json.loads(body)
            ledger_body = _raw_asset(release, fl.FILENAME, call)
            digest = _raw_asset(release, fl.FILENAME + '.sha256', call)
            if digest != f'{hashlib.sha256(ledger_body).hexdigest()}  {fl.FILENAME}\n'.encode('ascii'):
                raise ValueError('RAW_SHA256_MISMATCH')
            payload = fl.require_ledger(fl.parse_json(ledger_body))
        except Exception:
            code = 'INVALID'
            continue
        return (payload, ledger_body), 'FOUND'
    return None, code


def last_session(ledger):
    """Latest record date over the recorded versions (v1 and v2), or None when there is no record."""
    dates = [ledger['versions'][v][-1]['date'] for v in (fl.VERSION, fl.V2_VERSION) if ledger['versions'].get(v)]
    return max(dates) if dates else None


def choose_previous(pages, raw):
    """W-F2 precedence -> (chosen (payload, bytes) or None, source, code).

    The private copy wins only when its last session is on/after the Pages copy's last session and every Pages record
    is carried byte-identically at its front (it never rewrites or drops a published row). Otherwise Pages."""
    if raw is None:
        return pages, 'PAGES' if pages is not None else 'NONE', None
    if pages is None:
        return raw, 'RAW', 'FOUND'
    if (last_session(raw[0]) or '') < (last_session(pages[0]) or ''):
        return pages, 'PAGES', 'OLDER'
    try:
        fl.require_append_only(pages[0], raw[0])
    except ValueError:
        return pages, 'PAGES', 'DIVERGED'
    return raw, 'RAW', 'FOUND'


def _recovered(chosen, pages):
    if chosen is None:
        return 0
    old = len(pages[0]['versions'].get(fl.VERSION, [])) if pages is not None else 0
    return len(chosen[0]['versions'][fl.VERSION]) - old


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


def run(out, *, preserve_only=False, bootstrap=False, environ=None, now=_utc_now, open_previous=None, upload_call=None,
        raw_call=None):
    environ = os.environ if environ is None else environ
    try:
        fetched = fetch_previous(open_response=open_previous)
    except ValueError:
        print('FORWARD_LEDGER PREVIOUS_INVALID nothing_written')
        return 1
    except Exception:
        print('FORWARD_LEDGER PREVIOUS_FETCH_FAILED nothing_written')
        return 1
    if environ.get(PREVIOUS_SOURCE_ENV) == RAW_FIRST:
        if environ.get(RAW_TOKEN_ENV):
            raw, raw_code = fetch_previous_raw(now(), call=raw_call)
        else:
            raw, raw_code = None, 'NOT_CONFIGURED'
        chosen, source, choice_code = choose_previous(fetched, raw)
        print(f'FORWARD_LEDGER_PREVIOUS source={source} raw={choice_code or raw_code} '
              f'recovered_records={max(0, _recovered(chosen, fetched)) if source == "RAW" else 0}')
        fetched = chosen
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
