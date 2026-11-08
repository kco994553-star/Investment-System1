#!/usr/bin/env python3
"""Deploy-time carry of the verified live `macro-evidence.json` into a withheld artifact (owner 2026-11-07 4th).

Why: when only the collect-time read of the live copy fails (UNAVAILABLE after the retries), the daily step withholds the
file (macro_evidence.withhold, record WITHHELD). At deploy the freshness guard then sees MISSING -> WITHHELD, and on a
static Pages site the live good copy leaves the site (effect=LIVE_GOOD_COPY_REMOVED). That is not preservation.

What: run on the deploy artifact directory, after it is unpacked and BEFORE pages_freshness_guard.py. Nothing in the
guard changes: the carried bytes are the live bytes, so the guard sees EQUAL, and the record describes them.

- artifact holds a macro file built from collected data (generated_at set) -> NOT_NEEDED, nothing read, nothing changed;
- artifact holds no macro file and its own attempt record says WITHHELD -> the live copy is read once (same cache-busting
  query as the guard, the daily tool's reader macro_evidence._live_bytes, no redirects, the daily retries):
  - read failed after the retries (data or its live record) -> LIVE_UNREADABLE: nothing carried, exit 1 (the deploy
    stops; the guard would refuse it as LIVE_UNREACHABLE anyway). A failed read is never taken for absence;
  - HTTP 200 but the live body itself is rejected (not JSON, oversized, require_macro_evidence) -> LIVE_INVALID: nothing
    carried, the existing WITHHELD path (guard LIVE_INVALID);
  - the live body is a verified good copy but its live attempt record is damaged, says WITHHELD, describes another file,
    or this attempt's record cannot describe it (Codex #437 6716049571: record_mismatch / record_withheld) ->
    LIVE_RECORD_MISMATCH: nothing carried, the record is never rewritten to fit, exit 1 (deploy=REFUSED, site=KEPT): the
    deploy stops so the live site, good body included, stays as it is;
  - 404, or only the build placeholder -> LIVE_ABSENT: nothing to carry, the file stays unpublished (NOT_PUBLISHED);
  - a verified good copy -> CARRIED: those bytes are written byte for byte (never re-serialized: generated_at and every
    observation, release and check time unchanged) and the attempt record becomes CARRIED_LIVE
    (evidence_lines.carried_status): the attempt's own failure (time, stage, exception class, previous read) unchanged,
    plus the carried file's generated_at and SHA-256 and the deploy read time. Read back and checked; on any write
    failure the artifact is put back as it was (CARRY_FAILED, exit 1);
- anything else (the build placeholder, a damaged file, no or another attempt record) -> NOT_ELIGIBLE: untouched, the
  guard decides as before.

Output: one fixed line `MACRO_EVIDENCE_CARRY outcome=<code> ...` with codes, times, a hash and exception class names only
(no URL, value or message). The next daily run reads the carried copy as LOADED (it is the live bytes) and continues it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_evidence as tool

el = tool.el
OUTCOMES = ('CARRIED', 'LIVE_UNREADABLE', 'LIVE_INVALID', 'LIVE_ABSENT', 'NOT_NEEDED', 'NOT_ELIGIBLE', 'CARRY_FAILED')


def _utc_now():
    return datetime.now(timezone.utc)


def _nonce(environ):
    run_id, attempt = environ.get('GITHUB_RUN_ID', ''), environ.get('GITHUB_RUN_ATTEMPT', '')
    return run_id + '-' + attempt if run_id.isdigit() and attempt.isdigit() else str(time.time_ns())


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _say(outcome, **fields):
    print('MACRO_EVIDENCE_CARRY outcome=%s%s' % (outcome, ''.join(' %s=%s' % (k, v if v is not None else '-')
                                                               for k, v in fields.items())))


def _file(directory, name, validate):
    """-> ('VALID', bytes, payload) | ('ABSENT', None, None) | ('INVALID', None, None)."""
    path = directory / name
    if not path.exists() and not path.is_symlink():
        return 'ABSENT', None, None
    if path.is_symlink() or not path.is_file():
        return 'INVALID', None, None
    body = path.read_bytes()
    try:
        if len(body) > el.MAX_BYTES:
            raise ValueError('MACRO_EVIDENCE_TOO_LARGE')
        return 'VALID', body, validate(tool.parse_json(body))
    except Exception:
        return 'INVALID', None, None


class Unreadable(Exception):
    def __init__(self, name, error_class):
        super().__init__(name)
        self.name, self.error_class = name, error_class


def _read(source, name, open_response):
    """Live bytes or None on 404, with the daily reader's retries. Raises Unreadable after the last failed try."""
    for attempt in range(len(tool.RETRY_DELAYS) + 1):
        try:
            return tool._live_bytes(source, open_response)
        except ValueError:
            raise                                  # served but oversized: damaged, not a failed read
        except Exception as error:
            if attempt == len(tool.RETRY_DELAYS):
                raise Unreadable(name, type(error).__name__) from None
            tool._sleep(tool.RETRY_DELAYS[attempt])


def read_live(open_response=None, environ=None):
    """The live copy for a carry, read once (with retries) -> (read, body, payload, error class, file).

    read: GOOD (verified good copy, its live record absent or describing it) | ABSENT_404 | PLACEHOLDER | INVALID (the live
    body itself is damaged) | RECORD_MISMATCH (the live body is a verified good copy but the live attempt record served
    beside it is damaged, WITHHELD or describes another file: the pair is inconsistent, so it is neither carried nor
    allowed to be replaced; owner / Codex #437 6716049571) | UNREADABLE."""
    environ = os.environ if environ is None else environ
    nonce = _nonce(environ)
    try:
        body = _read(f'{tool.SOURCE}?deploy-carry={nonce}', el.FILENAME, open_response)
    except Unreadable as error:
        return 'UNREADABLE', None, None, error.error_class, el.FILENAME
    except ValueError as error:
        return 'INVALID', None, None, type(error).__name__, el.FILENAME
    if body is None:
        return 'ABSENT_404', None, None, None, el.FILENAME
    try:
        payload = el.require_macro_evidence(tool.parse_json(body))
    except Exception as error:
        return 'INVALID', None, None, type(error).__name__, el.FILENAME
    if not tool.good_copy(payload):
        return 'PLACEHOLDER', None, None, None, el.FILENAME
    # The live attempt record, when served, must describe this very file (a Pages deploy replaces both at once).
    try:
        record_body = _read(f'{tool.STATUS_SOURCE}?deploy-carry={nonce}', el.STATUS_FILENAME, open_response)
    except Unreadable as error:
        return 'UNREADABLE', None, None, error.error_class, el.STATUS_FILENAME
    except ValueError as error:
        return 'RECORD_MISMATCH', None, None, type(error).__name__, el.STATUS_FILENAME
    if record_body is not None:
        try:
            record = el.require_status(tool.parse_json(record_body))
        except Exception as error:
            return 'RECORD_MISMATCH', None, None, type(error).__name__, el.STATUS_FILENAME
        if record['published'] == 'WITHHELD':
            return 'RECORD_MISMATCH', None, None, 'STATUS_WITHHELD', el.STATUS_FILENAME
        if record['data_generated_at'] != payload['generated_at'] or record['data_sha256'] != _sha(body):
            return 'RECORD_MISMATCH', None, None, 'STATUS_MISMATCH', el.STATUS_FILENAME
    return 'GOOD', body, payload, None, el.FILENAME


def carry(artifact_dir, *, open_response=None, environ=None, now=_utc_now):
    """-> (outcome, exit code). See the module doc."""
    directory = Path(artifact_dir)
    if directory.is_symlink() or not directory.is_dir():
        _say('NOT_ELIGIBLE', artifact='DIRECTORY_INVALID')
        return 'NOT_ELIGIBLE', 1
    data_state, _, data = _file(directory, el.FILENAME, el.require_macro_evidence)
    status_state, status_body, record = _file(directory, el.STATUS_FILENAME, el.require_status)
    if data_state == 'VALID' and tool.good_copy(data):
        _say('NOT_NEEDED', artifact_generated_at=data['generated_at'],
             artifact_published=record['published'] if status_state == 'VALID' else 'NONE')
        return 'NOT_NEEDED', 0
    if data_state != 'ABSENT' or status_state != 'VALID' or record['published'] != 'WITHHELD':
        reason = ('PLACEHOLDER' if data_state == 'VALID' else 'DATA_INVALID' if data_state == 'INVALID' else
                  'STATUS_ABSENT' if status_state == 'ABSENT' else 'STATUS_INVALID' if status_state == 'INVALID' else
                  'STATUS_NOT_WITHHELD')
        _say('NOT_ELIGIBLE', artifact=reason, carried='NONE')
        return 'NOT_ELIGIBLE', 0
    attempt = dict(attempt_stage=record['failure_stage'], attempt_error=record['failure_class'],
                   attempt_previous=record['previous'])
    read, body, payload, error_class, name = read_live(open_response, environ)
    if read == 'UNREADABLE':
        _say('LIVE_UNREADABLE', file=name, error=error_class, carried='NONE', deploy='REFUSED', **attempt)
        return 'LIVE_UNREADABLE', 1
    if read == 'RECORD_MISMATCH':
        # A verified good live body with an inconsistent live record: never adopted (the record is not rewritten to fit)
        # and never left to the WITHHELD path, which would remove the good body from the site. Stop the deploy so the
        # live site stays as it is.
        _say('LIVE_RECORD_MISMATCH', file=name, error=error_class, carried='NONE', deploy='REFUSED', site='KEPT', **attempt)
        return 'LIVE_RECORD_MISMATCH', 1
    if read == 'INVALID':
        _say('LIVE_INVALID', file=name, error=error_class, carried='NONE', effect='WITHHELD', **attempt)
        return 'LIVE_INVALID', 0
    if read in ('ABSENT_404', 'PLACEHOLDER'):
        _say('LIVE_ABSENT', read='NO_LIVE' if read == 'ABSENT_404' else 'EMPTY_LIVE', carried='NONE',
             effect='NOT_PUBLISHED', **attempt)
        return 'LIVE_ABSENT', 0
    digest = _sha(body)
    try:
        carried = el.encode_status(el.carried_status(record, carried_at=now(), generated_at=payload['generated_at'],
                                                     sha256=digest))
    except Exception as error:
        # a verified good live copy this attempt's record cannot describe (times out of order): never described as
        # carried, and never removed from the site either -> the deploy stops, the live site stays
        _say('LIVE_RECORD_MISMATCH', file=el.STATUS_FILENAME, error=type(error).__name__, carried='NONE', deploy='REFUSED',
             site='KEPT', **attempt)
        return 'LIVE_RECORD_MISMATCH', 1
    try:
        tool.write_bytes(directory, body)
        tool.write_bytes(directory, carried, el.STATUS_FILENAME)
        if (directory / el.FILENAME).read_bytes() != body or (directory / el.STATUS_FILENAME).read_bytes() != carried:
            raise OSError('MACRO_EVIDENCE_CARRY_READBACK')
    except Exception as error:
        restored = 'NO'
        try:
            (directory / el.FILENAME).unlink(missing_ok=True)
            tool.write_bytes(directory, status_body, el.STATUS_FILENAME)
            restored = 'YES'
        except Exception:
            pass
        _say('CARRY_FAILED', error=type(error).__name__, restored=restored, deploy='REFUSED', **attempt)
        return 'CARRY_FAILED', 1
    _say('CARRIED', generated_at=payload['generated_at'], sha256=digest, status='CARRIED_LIVE', **attempt)
    return 'CARRIED', 0


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('MACRO_EVIDENCE_CARRY ARGUMENTS_INVALID')
        raise SystemExit(2)


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--artifact-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return carry(args.artifact_dir)[1]
    except Exception:
        print('MACRO_EVIDENCE_CARRY outcome=CARRY_FAILED error=UNEXPECTED deploy=REFUSED')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
