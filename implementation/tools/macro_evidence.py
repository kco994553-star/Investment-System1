#!/usr/bin/env python3
"""Public `macro-evidence.json` (MEV-1 P1 13 macro evidence lines; exploration only, MEV-10).

- build (build_pages_cockpit.py): `emit_empty` writes a NOT_AVAILABLE copy without source data;
- daily run: `public_screens_pipeline.py --live --macro-v0 --macro-evidence` calls `run_from_capture` inside its
  private capture directory, so BLS LNS14000000, BEA A191RL and the Treasury curve are reused from the macro v0 /
  lights v1 collection (never fetched twice). The previous Pages copy is carried forward (append-only vintages):
  404 -> baseline; an invalid copy -> discarded (baseline, PREVIOUS_DISCARDED); a network failure -> a new baseline
  marked continuity=RESET_PREVIOUS_UNAVAILABLE (the earlier history is not on this runner);
- --preserve-only (UI-only deploys, cockpit-pages.yml) -> the validated live copy re-published byte for byte, and the
  live attempt record macro-evidence-status.json with it when it is valid.

Failed attempts (owner 2026-11-07, run 42326419126: BUILD_FAILED while the build-time placeholder stayed in the artifact
and replaced 11 collected series with 0): the new file is built and validated in memory and only then written (atomic
replace). Any failure keeps the last good live copy unchanged, its own bytes and generated_at (never re-stamped), or,
when there is none, leaves the placeholder and says so. Either way macro-evidence-status.json records this attempt
(FAILED, stage, exception class) apart from the data, so the screen can say "this attempt failed, data delayed".
A live copy that is only the placeholder (generated_at null) is not a good copy: the next build starts a new baseline
marked continuity=RESET_PREVIOUS_UNAVAILABLE, because an earlier history existed and is not available.

A failure here never fails the SEC step that hosts it: only fixed codes and counts are printed (no URL, key, value or
provider message).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.macro import evidence_lines as el

SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + el.FILENAME
STATUS_SOURCE = 'https://kco994553-star.github.io/Investment-System1/' + el.STATUS_FILENAME


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('MACRO_EVIDENCE ARGUMENTS_INVALID')
        raise SystemExit(2)


def _utc_now():
    return datetime.now(timezone.utc)


def parse_json(body: bytes) -> dict:
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('MACRO_EVIDENCE_DUPLICATE_KEY')
            out[key] = value
        return out

    def constant(_value):
        raise ValueError('MACRO_EVIDENCE_NONFINITE')
    return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_constant=constant)


def _live_bytes(source, open_response=None):
    """Live bytes or None on 404. Network errors raise OSError, an oversized body ValueError."""
    request = urllib.request.Request(source, headers={'Accept': 'application/json', 'Cache-Control': 'no-cache'})
    fetch = open_response or urllib.request.build_opener(NoRedirect()).open
    try:
        with fetch(request, timeout=20) as response:
            if response.status != 200 or response.geturl() != source:
                raise OSError('PREVIOUS_FETCH_FAILED')
            body = response.read(el.MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    except (urllib.error.URLError, OSError):
        raise OSError('PREVIOUS_FETCH_FAILED') from None
    if len(body) > el.MAX_BYTES:
        raise ValueError('MACRO_EVIDENCE_PREVIOUS_TOO_LARGE')
    return body


def previous_copy(open_response=None):
    """(validated payload, live bytes); (None, None) on 404. Network errors raise OSError, invalid copies ValueError."""
    body = _live_bytes(SOURCE, open_response)
    if body is None:
        return None, None
    return el.require_macro_evidence(parse_json(body)), body


def previous_status(open_response=None):
    """The live attempt record bytes when valid; None when absent or invalid. Network errors raise OSError."""
    body = _live_bytes(STATUS_SOURCE, open_response)
    if body is None:
        return None
    try:
        el.require_status(parse_json(body))
    except ValueError:
        return None
    return body


def load_previous(open_response=None):
    """(payload or None, LOADED | NO_LIVE | UNAVAILABLE)."""
    try:
        payload, _ = previous_copy(open_response)
    except ValueError:
        print('MACRO_EVIDENCE PREVIOUS_DISCARDED')
        return None, 'NO_LIVE'
    except Exception:
        return None, 'UNAVAILABLE'
    return payload, 'LOADED' if payload is not None else 'NO_LIVE'


def good_copy(payload) -> bool:
    """A live copy is a good copy only when it was built from collected data (the placeholder has generated_at null)."""
    return payload is not None and payload.get('generated_at') is not None


def read_previous(open_response=None):
    """(good payload or None, good live bytes or None, previous read for the status record)."""
    try:
        payload, body = previous_copy(open_response)
    except ValueError:
        print('MACRO_EVIDENCE PREVIOUS_DISCARDED')
        return None, None, 'INVALID'
    except Exception:
        return None, None, 'UNAVAILABLE'
    if payload is None:
        return None, None, 'NO_LIVE'
    if not good_copy(payload):
        return None, None, 'EMPTY_LIVE'
    return payload, body, 'LOADED'


# the evidence_lines `previous` value for each status read: a placeholder live copy means an earlier history is lost.
BUILD_PREVIOUS = {'LOADED': 'LOADED', 'NO_LIVE': 'NO_LIVE', 'INVALID': 'NO_LIVE', 'UNAVAILABLE': 'UNAVAILABLE',
                  'EMPTY_LIVE': 'UNAVAILABLE'}


def write_bytes(directory, body: bytes, name: str = el.FILENAME) -> bytes:
    directory = Path(directory)
    destination = directory / name
    if directory.is_symlink() or not directory.is_dir() or destination.is_symlink() or len(body) > el.MAX_BYTES:
        raise ValueError('MACRO_EVIDENCE_OUTPUT_INVALID')
    with tempfile.NamedTemporaryFile(dir=directory, prefix='.' + name + '-', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(body)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return body


def emit_empty(directory, *, now=_utc_now):
    """Offline/PR builds: a NOT_AVAILABLE copy without source data, replaced by the daily or preserve step."""
    return write_bytes(directory, el.encode(el.empty_payload(now())))


def _summary(payload) -> None:
    for sid, row in payload['series'].items():
        print('MACRO_EVIDENCE series=%s state=%s reason=%s obs=%d revised_periods=%d' % (
            sid, row['state'], row['reason'] or '-', len(row['obs']), len(row['history'])))
    print('MACRO_EVIDENCE state=%s previous=%s continuity=%s releases=%d events=%d replay_events=%d' % (
        payload['state'], payload['previous'], payload['continuity'], len(payload['releases']), len(payload['events']),
        len(payload['replay_events'])))


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _status(directory, **fields) -> dict:
    record = el.status_record(**fields)
    write_bytes(directory, el.encode_status(record), el.STATUS_FILENAME)
    print('MACRO_EVIDENCE_STATUS result=%s stage=%s error=%s published=%s data_generated_at=%s previous=%s' % (
        record['attempt_result'], record['failure_stage'] or '-', record['failure_class'] or '-', record['published'],
        record['data_generated_at'] or '-', record['previous']))
    return record


def _need(condition) -> None:
    if not condition:
        raise ValueError('MACRO_EVIDENCE_INCONSISTENT')


def require_successor(payload, *, attempt_at, previous, read) -> dict:
    """What a built file must show, beyond require_macro_evidence, before it replaces anything (owner 2026-11-07 item 3):
    built at this attempt, from the previous read it was given, its overall state the one its indicators give, and, after a
    good copy, a continuation of it (same collection start, later build, release and event records only appended, no
    carried observations dropped). A count of LIVE series is never a criterion (a partial collection is normal)."""
    _need(payload.get('generated_at') == el.iso(attempt_at))
    _need(payload['previous'] == BUILD_PREVIOUS[read])
    started = payload['collection_started_at']
    _need(started is not None and el.parse_iso(started) <= el.parse_iso(payload['generated_at']))
    states = [i['state'] for i in payload['indicators']]
    _need(payload['state'] == ('LIVE' if all(x == 'LIVE' for x in states) else
                               'NOT_AVAILABLE' if all(x == 'NOT_AVAILABLE' for x in states) else 'PARTIAL'))
    if previous is None:
        _need(payload['continuity'] == ('RESET_PREVIOUS_UNAVAILABLE' if BUILD_PREVIOUS[read] == 'UNAVAILABLE' else 'BASELINE'))
        return payload
    _need(payload['continuity'] == 'CONTINUOUS')
    _need(el.parse_iso(payload['generated_at']) > el.parse_iso(previous['generated_at']))
    _need(started == previous['collection_started_at'])
    _need(payload['releases'][:len(previous['releases'])] == previous['releases'])
    _need(payload['events'][:len(previous['events'])] == previous['events'])
    for sid, row in previous['series'].items():
        _need(not row['obs'] or el._held(sid) or bool(payload['series'][sid]['obs']))
    return payload


def withhold(directory) -> str:
    """After an attempt that left no good copy (owner 2026-11-07 item 2): the file in `directory` is published only when it
    is a validated good copy; the build-time placeholder (or anything else) is removed so it is never published as a
    result. An attempt record beside it that does not say NO_GOOD_COPY is removed too. -> 'KEPT' | 'WITHHELD'."""
    directory = Path(directory)
    path, status = directory / el.FILENAME, directory / el.STATUS_FILENAME
    try:
        body = path.read_bytes() if path.is_file() and not path.is_symlink() else None
        if body is not None and good_copy(el.require_macro_evidence(parse_json(body))):
            print('MACRO_EVIDENCE KEPT file=%s' % el.FILENAME)
            return 'KEPT'
    except Exception:
        pass
    if path.exists() or path.is_symlink():
        path.unlink()
    try:
        ok = status.is_file() and not status.is_symlink() and el.require_status(parse_json(status.read_bytes()))['published'] == 'NO_GOOD_COPY'
    except Exception:
        ok = False
    if not ok and (status.exists() or status.is_symlink()):
        status.unlink()
    print('MACRO_EVIDENCE WITHHELD file=%s reason=NO_GOOD_COPY status=%s' % (el.FILENAME, 'NO_GOOD_COPY' if ok else 'NONE'))
    return 'WITHHELD'


def run_from_capture(directory, root, manifest, *, environ, now=_utc_now, open_previous=None, transport=None,
                     previous=None) -> int:
    """Collect, merge with the last good Pages copy and write `macro-evidence.json` into `directory` only after the new
    file is validated; on any failure keep the last good copy unchanged (or the placeholder when there is none). Always
    writes macro-evidence-status.json for this attempt. Returns 0 when a file is in place (new or kept), 1 otherwise.

    `previous` (tests): (payload or None, read) with read in el.PREVIOUS_READ, or the legacy (payload, LOADED/NO_LIVE/
    UNAVAILABLE) pair; a payload is kept on failure as its own canonical encoding."""
    attempt_at = now()
    stage = 'PREVIOUS'
    good, good_body, read = None, None, 'UNAVAILABLE'
    try:
        if previous is not None:
            good, read = previous
            good = good if good_copy(good) else None
            read = 'LOADED' if good is not None else (read if read in el.PREVIOUS_READ and read != 'LOADED' else 'EMPTY_LIVE')
            good_body = el.encode(good) if good is not None else None
        else:
            good, good_body, read = read_previous(open_previous)
        stage = 'COLLECT'
        from investment_system.providers.macro_evidence_collection import collect_macro_evidence
        diagnostics = []
        kwargs = {'transport': transport} if transport is not None else {}
        captures = collect_macro_evidence(root, manifest, environ=environ, diagnostics=diagnostics, **kwargs)
        for d in diagnostics:
            print('MACRO_EVIDENCE_FETCH stage=%s code=%s http=%s size=%s' % tuple(
                (d.get(k) if d.get(k) is not None else '-') for k in ('stage', 'code', 'http', 'size')))
        stage = 'BUILD'
        payload = el.build(captures, previous=good, previous_state=BUILD_PREVIOUS[read], now=attempt_at)
        stage = 'VALIDATE'
        body = el.encode(payload)
        checked = el.require_macro_evidence(parse_json(body))
        if checked.get('generated_at') is None:
            raise ValueError('MACRO_EVIDENCE_NOT_GENERATED')
        require_successor(checked, attempt_at=attempt_at, previous=good, read=read)
        stage = 'WRITE'
        write_bytes(directory, body)
    except Exception as error:
        error_class = type(error).__name__
        if good_body is not None:
            try:
                write_bytes(directory, good_body)
            except Exception:
                print('MACRO_EVIDENCE BUILD_FAILED stage=%s error=%s kept=NONE write_failed' % (stage, error_class))
                try:
                    _status(directory, attempt_at=attempt_at, result='FAILED', stage='WRITE', error_class=error_class,
                            published='NO_GOOD_COPY', data_generated_at=None, data_sha256=None, previous=read)
                except Exception:
                    print('MACRO_EVIDENCE STATUS_WRITE_FAILED')
                return 1
            print('MACRO_EVIDENCE BUILD_FAILED stage=%s error=%s kept=PREVIOUS generated_at=%s' % (
                stage, error_class, good['generated_at']))
            try:
                _status(directory, attempt_at=attempt_at, result='FAILED', stage=stage, error_class=error_class,
                        published='PREVIOUS_KEPT', data_generated_at=good['generated_at'], data_sha256=_sha(good_body), previous=read)
            except Exception:
                print('MACRO_EVIDENCE STATUS_WRITE_FAILED')
            return 0
        print('MACRO_EVIDENCE BUILD_FAILED stage=%s error=%s kept=NONE no_good_copy' % (stage, error_class))
        try:
            _status(directory, attempt_at=attempt_at, result='FAILED', stage=stage, error_class=error_class,
                    published='NO_GOOD_COPY', data_generated_at=None, data_sha256=None, previous=read)
        except Exception:
            print('MACRO_EVIDENCE STATUS_WRITE_FAILED')
        return 1
    # The new file is in place: a failure from here on (summary lines, status record) must not reach the caller's catch-all,
    # which would print BUILD_FAILED for a file that was built.
    try:
        _summary(payload)
        _status(directory, attempt_at=attempt_at, result='BUILT', stage=None, error_class=None, published='NEW',
                data_generated_at=payload['generated_at'], data_sha256=_sha(body), previous=read)
    except Exception:
        print('MACRO_EVIDENCE STATUS_WRITE_FAILED')
    return 0


def preserve(out, *, open_previous=None) -> int:
    """UI-only deploy (cockpit-pages): carry the live good copy byte for byte, with its attempt record when the record
    describes it. No good copy live (404 or the placeholder): the build placeholder is withheld, not published as a result
    (owner 2026-11-07), and a live NO_GOOD_COPY record goes with it. Live unreadable or invalid: the build placeholder stays
    and the deploy check decides (refused when a good copy is live: EMPTIED)."""
    good, body, read = read_previous(open_previous)
    try:
        status = previous_status(open_previous)
        record = el.require_status(parse_json(status)) if status is not None else None
    except Exception:
        status, record = None, None
    if good is None:
        if read in ('UNAVAILABLE', 'INVALID'):
            print('MACRO_EVIDENCE PREVIOUS_FETCH_FAILED kept=BUILD_PLACEHOLDER' if read == 'UNAVAILABLE' else 'MACRO_EVIDENCE PREVIOUS_DISCARDED')
            return 0
        print('MACRO_EVIDENCE PREVIOUS_NOT_AVAILABLE previous=%s' % read)
        try:
            if record is not None and record['published'] == 'NO_GOOD_COPY':
                write_bytes(out, status, el.STATUS_FILENAME)
                print('MACRO_EVIDENCE STATUS_RESTORED')
            withhold(out)
        except Exception:
            print('MACRO_EVIDENCE OUTPUT_FAILED')
            return 1
        return 0
    try:
        write_bytes(out, body)
    except Exception:
        print('MACRO_EVIDENCE OUTPUT_FAILED')
        return 1
    print('MACRO_EVIDENCE PREVIOUS_RESTORED state=%s events=%d' % (good['state'], len(good['events'])))
    # the live attempt record goes with it unchanged when it describes this very file (a UI-only deploy is not a new attempt)
    if record is not None and record['published'] != 'NO_GOOD_COPY' and record['data_generated_at'] == good['generated_at'] \
            and record['data_sha256'] == _sha(body):
        try:
            write_bytes(out, status, el.STATUS_FILENAME)
            print('MACRO_EVIDENCE STATUS_RESTORED')
        except Exception:
            print('MACRO_EVIDENCE STATUS_OUTPUT_FAILED')
            return 1
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--preserve-only', action='store_true')
    args = parser.parse_args(argv)
    if not args.preserve_only:
        print('MACRO_EVIDENCE PRESERVE_ONLY_REQUIRED (daily collection runs inside public_screens_pipeline.py --macro-evidence)')
        return 2
    return preserve(args.out)


if __name__ == '__main__':
    raise SystemExit(main())
