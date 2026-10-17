#!/usr/bin/env python3
"""Pre-deploy freshness guard: never publish public data that retreats from the live GitHub Pages copy.

Owner queue 2026-10-17 §5, with the owner's amendments of 2026-10-17. Two workflows deploy Pages in the concurrency
group `checked-cockpit-pages`: the daily `sec-daily-public-inputs.yml` (collect merges a new SEC shard into the live copy
it read) and the manual `cockpit-pages.yml` (its build re-publishes the live copy read at build time). The group
serialises the deploys but not their order, so an artifact built from the live copy at T0 could be deployed after a
newer deploy at T1 and roll the public data back. This check runs inside each deploy job (which holds the group),
immediately before actions/deploy-pages, on exactly the artifact that job deploys.

Row rule (each file against the live copy of the same file, each section separately, row by row on the same key):

- sec-universe-shares.json `records` and sec-universe-qg.json `records`: keyed by Universe code;
- sec-qgv2.json `records` (Universe code) and `target` (TARGET company id): two separate sections;
- sec-public-inputs.json `companies`: a list keyed by `company_id` (records below).

A live row with a collection record (`acquired_at` set) must be in the artifact with an `acquired_at` equal to or later
than the live one. Row missing -> MISSING, artifact `acquired_at` null or unreadable -> LOST_RECORD, earlier -> OLDER:
each refuses the deploy. Equal or later passes whatever the row's values are: a row that is NOT_AVAILABLE with reason
codes, or was computed under another `calc_version`, after a collection at least as new is a normal transition under
the current calculation rules, not a retreat. Live rows without a collection record are not compared (an artifact row
that has one where the live row has none is counted as new_record). Markers are acquisition times only, never a file's
`as_of`: the preserve-only path of the manual build re-stamps the Universe files' `as_of` to its own build time.

sec-public-inputs.json (owner decision 2026-10-17, schema /4; a /3 live copy is compared the same way, its NOT_AVAILABLE
rows have no record). The artifact file is read through its strict validator (`require_public_inputs`); an artifact that
fails it has no rows (PAGES_FRESHNESS_ARTIFACT_INVALID line, every live record MISSING). A row's record is:
- OBSERVED at `acquired_at`: a LIVE row or a /4 NOT_AVAILABLE row (policy NA of a successful collection, which the
  validator only accepts with sources, a normalize-stage policy code and an acquired_at no later than the run);
- WITHDRAWN at `detected_at`, naming `withdrawn_acquired_at`: an identity conflict that stops an observation;
- none: a /3 NOT_AVAILABLE row or a /4 COLLECTION_FAILED row (`checked_at` is a failure time, never a marker).
Rules for a live row with a record (on top of MISSING / LOST_RECORD / OLDER by marker):
- an artifact WITHDRAWN row must name exactly the live observation: `withdrawn_acquired_at` equal to the live row's
  `acquired_at` (live OBSERVED) or to the live withdrawal's `withdrawn_acquired_at` (live WITHDRAWN), else
  WITHDRAWAL_MISMATCH (OLDER when it names an earlier observation), and be detected no earlier than the live marker.
  Against a live OBSERVED row it passes as WITHDRAWN. Setting a status alone therefore never passes: the withdrawal must
  carry the live acquired_at, an identity reason code and a valid detection time, all checked here or by the validator;
- a row kept from the previous copy (`preserved_previous` set) must be the live row itself: same record and the same
  observation content (everything but `preserved_previous`), else PRESERVED_MISMATCH: a kept row is never newer than the
  live one (no timestamp refresh without a collection) and never another observation;
- a row whose record equals the live one must have the same observation content, else CHANGED (values replaced
  without a newer collection);
- a newer OBSERVED row passes over a live WITHDRAWN row only when collected at or after the detection (NEWER), so an
  artifact built before the withdrawal can never bring the stopped value back (OLDER).

Producers (owner decision 2026-10-17, option a): a company/code whose collection or identification failed keeps its
verified previous row unchanged (same acquired_at, sources and calc_version) when the same issuer is confirmed, so such a
failure arrives here as EQUAL, never as LOST_RECORD: tools/public_sec_inputs.py (transient fetch failures) and the
Universe merges (`previous_decision`: unresolved symbol, identity unconfirmed, builder failure). Identity conflicts and
TARGET normalize results are never preserved. In sec-public-inputs.json /4 a TARGET normalize result is a NOT_AVAILABLE
row with this run's acquired_at (NEWER, passes) and an identity conflict is a WITHDRAWN row (passes as WITHDRAWN when
it names the live observation); a collection failure without a kept row (HTTP 404, unknown failure, live copy not read)
is a COLLECTION_FAILED row without a record: LOST_RECORD, refused (fail closed).

forward-validation-ledger.json: every record of every append-only list in `versions` (v1, v1+dcf, v2 and any list a
later schema adds) must be in the artifact at the same position with identical canonical JSON; the artifact may only
add records after them. A live record that is missing, changed or moved refuses the deploy, also when the last session
date is unchanged. `as_of` and the last session date are still compared as markers (older or missing -> refused).

Live copy: 404 -> NO_LIVE (first publication, nothing to roll back: pass). Served (200) but oversized, not JSON or
rejected by the file's strict validator (the same one its daily previous-copy reader applies) ->
PAGES_FRESHNESS_LIVE_INVALID and the deploy is refused: nothing can be compared, and this guard never passes blind.
Restoring a healthy live copy after LIVE_INVALID is a separate, evidence-based procedure decided by the owner; this
guard never repairs, replaces or bypasses the live copy and never lets a deploy through to do so. Any other live read
failure (network, HTTP status, redirect) -> PAGES_FRESHNESS_LIVE_UNREACHABLE, refused (fail closed).

The artifact side is read as plain JSON; its strict validation is pages_artifact_guard.py's job in the jobs that build
and verify it. An artifact file that is absent or unreadable has no rows, so every collected live row is MISSING.

The live copy is read with each daily tool's own previous-copy reader (same URL, no redirects, 404 = absent) plus a
per-run query string so a CDN copy cached before the previous deploy is not mistaken for the live one. Output is fixed:
one line per section and ledger list (counts and latest acquisition times), at most MAX_DETAIL lines per section naming
regressed row keys (public Universe codes / TARGET company ids) or ledger record dates, and one total line. No values,
URLs or secrets are printed.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_validation_ledger as ledger_tool
import preserve_public_sec_inputs as target_tool
import sec_universe_shares as universe_tool
from sec_universe_shares import _fetch_body  # the daily tools' live Pages reader (404 -> None, other failure -> OSError)

fl = ledger_tool.fl
MAX_DETAIL = 20
ROW_KINDS = ('newer', 'equal', 'older', 'missing', 'lost_record')
ROW_REGRESSIONS = ('OLDER', 'MISSING', 'LOST_RECORD', 'WITHDRAWAL_MISMATCH', 'PRESERVED_MISMATCH', 'CHANGED')
# sec-public-inputs.json only (schema /4): counted after new_record on its line.
INPUTS_KINDS = ('withdrawn', 'withdrawal_mismatch', 'preserved_mismatch', 'changed')
MARKER_REFUSING = ('OLDER', 'MISSING')
_PRINTABLE_KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9:._-]{0,39}')
_PRINTABLE_VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/+-]{0,63}')


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('PAGES_FRESHNESS ARGUMENTS_INVALID')
        raise SystemExit(2)


def _instant(value):
    """ISO date-time with an offset -> aware UTC datetime; anything else -> None."""
    if type(value) is not str:
        return None
    try:
        moment = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.utcoffset() is not None else None


def _day(value):
    try:
        return date.fromisoformat(value) if type(value) is str and len(value) == 10 else None
    except ValueError:
        return None


# ---- live copy: the strict validator each file's daily previous-copy reader applies ----
def _valid_shares(body):
    return universe_tool.require_universe_shares(universe_tool.upgrade_legacy(universe_tool.parse_json(body)))


def _valid_qg(body):
    return universe_tool.qg.require_universe_qg(universe_tool.qg.parse_json(body))


def _valid_qgv2(body):
    return universe_tool.qgv2.require_qgv2(universe_tool.qgv2.parse_json(body))


def _valid_inputs(body):
    def invalid_constant(_):
        raise ValueError
    if len(body) > target_tool.MAX_BYTES:
        raise ValueError
    payload = json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=target_tool.unique,
                         parse_constant=invalid_constant)
    return target_tool.require_public_inputs(payload)


def _valid_ledger(body):
    return fl.require_ledger(fl.parse_json(body))


# (published file, live URL as its daily previous-copy reader uses it, byte limit, live validator, row sections)
ROW_FILES = (
    (universe_tool.FILENAME, universe_tool.SOURCE, universe_tool.MAX_BYTES, _valid_shares, ('records',)),
    (universe_tool.qg.FILENAME, universe_tool.QG_SOURCE, universe_tool.qg.MAX_BYTES, _valid_qg, ('records',)),
    (universe_tool.qgv2.FILENAME, universe_tool.QGV2_SOURCE, universe_tool.qgv2.MAX_BYTES, _valid_qgv2,
     ('records', 'target')),
    (target_tool.FILENAME, target_tool.SOURCE, target_tool.MAX_BYTES, _valid_inputs, ('companies',)),
)
LEDGER_FILE = (fl.FILENAME, ledger_tool.SOURCE, fl.MAX_BYTES, _valid_ledger)


class LiveUnreachable(Exception):
    def __init__(self, name):
        super().__init__(name)
        self.name = name


def _payload(body, limit):
    """Artifact bytes -> JSON object, or None when oversized, not UTF-8, not JSON or not an object."""
    if body is None or len(body) > limit:
        return None
    def invalid_constant(_):
        raise ValueError
    try:
        value = json.loads(body.decode('utf-8', errors='strict'), parse_constant=invalid_constant)
    except (ValueError, RecursionError):
        return None
    return value if type(value) is dict else None


def _artifact(folder, name, limit):
    path = folder / name
    if path.is_symlink() or not path.is_file():
        return None
    return _payload(path.read_bytes(), limit)


def _live(name, source, limit, validate, nonce, open_response):
    """-> ('VALID', payload) | ('NO_LIVE', None) | ('LIVE_INVALID', None). Raises LiveUnreachable."""
    try:
        body = _fetch_body(f'{source}?deploy-check={nonce}', limit, open_response)
    except OSError:
        raise LiveUnreachable(name) from None
    if body is None:
        return 'NO_LIVE', None
    if len(body) > limit:
        return 'LIVE_INVALID', None
    try:
        payload = validate(body)
    except Exception:
        return 'LIVE_INVALID', None
    return ('VALID', payload) if type(payload) is dict else ('LIVE_INVALID', None)


def _rows(payload, section):
    """{key: row} of one section: a dict keyed by code/company id, or a list of rows keyed by `company_id`."""
    rows = payload.get(section) if type(payload) is dict else None
    if type(rows) is dict:
        return {key: row for key, row in rows.items() if type(row) is dict}
    out = {}
    if type(rows) is list:
        for row in rows:
            if type(row) is dict and type(row.get('company_id')) is str:
                out.setdefault(row['company_id'], row)
    return out


def _latest(rows):
    stamps = [s for s in (_instant(row.get('acquired_at')) for row in rows.values()) if s is not None]
    return max(stamps) if stamps else None


def _acquired_record(row):
    stamp = _instant(row.get('acquired_at'))
    return None if stamp is None else ('OBSERVED', stamp, None)


def _inputs_record(row):
    """sec-public-inputs.json: ('OBSERVED', acquired_at, None) | ('WITHDRAWN', detected_at, withdrawn_acquired_at) | None."""
    if row.get('status') == 'WITHDRAWN':
        detected = _instant(row.get('detected_at'))
        return None if detected is None else ('WITHDRAWN', detected, _instant(row.get('withdrawn_acquired_at')))
    return _acquired_record(row)


def _observation(row):
    """A row without its run marker, as canonical text (a kept row equals the live row it was kept from)."""
    return json.dumps({k: v for k, v in row.items() if k != 'preserved_previous'}, sort_keys=True, ensure_ascii=True)


def _row_kind(theirs_row, theirs, row, ours, inputs):
    if row is None:
        return 'MISSING'
    if ours is None:
        return 'LOST_RECORD'
    if ours[1] < theirs[1]:
        return 'OLDER'
    if not inputs:
        return 'EQUAL' if ours[1] == theirs[1] else 'NEWER'
    if ours[0] == 'WITHDRAWN':
        named = theirs[1] if theirs[0] == 'OBSERVED' else theirs[2]
        if ours[2] != named:
            return 'OLDER' if ours[2] is not None and named is not None and ours[2] < named else 'WITHDRAWAL_MISMATCH'
    kept = type(row.get('preserved_previous')) is dict
    if ours == theirs and _observation(row) == _observation(theirs_row):
        return 'EQUAL'
    if kept:
        return 'PRESERVED_MISMATCH'
    if ours == theirs:
        return 'CHANGED'
    return 'WITHDRAWN' if ours[0] == 'WITHDRAWN' and theirs[0] == 'OBSERVED' else 'NEWER'


def compare_rows(name, section, live, local):
    """One section, row by row. `live` is the validated live payload or None (404)."""
    inputs = name == target_tool.FILENAME
    record = _inputs_record if inputs else _acquired_record
    mine = _rows(local, section)
    counts = dict.fromkeys(('compared',) + ROW_KINDS + ('new_record',) + (INPUTS_KINDS if inputs else ()), 0)
    regressions = []
    theirs_rows = _rows(live, section) if live is not None else {}
    for key in sorted(set(theirs_rows) | set(mine)):
        theirs = record(theirs_rows[key]) if key in theirs_rows else None
        row = mine.get(key)
        ours = record(row) if row is not None else None
        if theirs is None:
            counts['new_record'] += int(ours is not None)
            continue
        counts['compared'] += 1
        kind = _row_kind(theirs_rows[key], theirs, row, ours, inputs)
        counts[kind.lower()] += 1
        if kind in ROW_REGRESSIONS:
            regressions.append((key, kind, ours[1] if ours else None, theirs[1]))
    verdict = 'NO_LIVE' if live is None else 'REFUSED' if regressions else 'PASS'
    return {'file': name, 'section': section, 'verdict': verdict, 'counts': counts, 'regressions': regressions,
            'artifact_latest': _latest(mine), 'live_latest': _latest(theirs_rows)}


def _canonical(value):
    try:
        return fl.canonical(value)
    except (ValueError, TypeError, RecursionError):
        return None


def compare_ledger_list(version, old, new):
    """Every live record at the same position with identical canonical JSON; the artifact may only append after them."""
    new_text = [_canonical(r) for r in new]
    anywhere = {text for text in new_text if text is not None}
    dates = {r.get('date') for r in new if type(r) is dict and type(r.get('date')) is str}
    regressions = []
    counts = dict.fromkeys(('live_records', 'artifact_records', 'preserved', 'moved', 'changed', 'missing', 'appended'), 0)
    counts['live_records'], counts['artifact_records'] = len(old), len(new)
    for index, record in enumerate(old):
        text = _canonical(record)
        if index < len(new) and new_text[index] is not None and new_text[index] == text:
            counts['preserved'] += 1
            continue
        # MOVED: identical record at another position; CHANGED: a record of that date with other content; else MISSING.
        kind = 'MOVED' if text in anywhere else 'CHANGED' if record['date'] in dates else 'MISSING'
        counts[kind.lower()] += 1
        regressions.append((index, kind, record['date']))
    if not regressions:
        counts['appended'] = len(new) - len(old)
    return {'version': version, 'verdict': 'REFUSED' if regressions else 'PASS', 'counts': counts,
            'regressions': regressions}


def _ledger_session(payload):
    try:
        return _day(ledger_tool.last_session(payload))
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


def _marker(mine, theirs):
    if theirs is None:
        return 'NO_LIVE'
    if mine is None:
        return 'MISSING'
    return 'OLDER' if mine < theirs else 'EQUAL' if mine == theirs else 'NEWER'


def compare_ledger(live, local):
    """-> (marker results, list results). `live` is the validated live ledger or None (404)."""
    markers = []
    for marker_name, extract in (('as_of', lambda p: _instant(p.get('as_of'))), ('session', _ledger_session)):
        mine = extract(local) if local is not None else None
        theirs = extract(live) if live is not None else None
        markers.append((marker_name, _marker(mine, theirs), mine, theirs))
    live_versions = live['versions'] if live is not None else {}
    local_versions = local.get('versions') if type(local) is dict else None
    local_versions = local_versions if type(local_versions) is dict else {}
    lists = []
    for version in list(fl.VERSIONS) + sorted(set(live_versions) - set(fl.VERSIONS)):
        new = local_versions.get(version)
        result = compare_ledger_list(version, live_versions.get(version, []), new if type(new) is list else [])
        if live is None:
            result['verdict'] = 'NO_LIVE'
        lists.append(result)
    return markers, lists


def _run_nonce(environ):
    run_id, attempt = environ.get('GITHUB_RUN_ID', ''), environ.get('GITHUB_RUN_ATTEMPT', '')
    if run_id.isdigit() and attempt.isdigit():
        return run_id + '-' + attempt
    return str(time.time_ns())


def compare(artifact_dir, *, open_response=None, environ=None):
    """-> {'rows': [...], 'ledger_markers': [...], 'ledger_lists': [...], 'live_invalid': [file, ...]}.

    Raises LiveUnreachable on a failed live read (nothing is compared then)."""
    environ = os.environ if environ is None else environ
    artifact_dir = Path(artifact_dir)
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        raise ValueError('PAGES_FRESHNESS ARTIFACT_INVALID')
    nonce = _run_nonce(environ)
    reads = [(entry, _live(*entry[:4], nonce, open_response)) for entry in ROW_FILES + (LEDGER_FILE,)]
    out = {'rows': [], 'ledger_markers': [], 'ledger_lists': [], 'live_invalid': [], 'artifact_invalid': []}
    for (name, _, limit, *rest), (state, live) in reads:
        if state == 'LIVE_INVALID':
            out['live_invalid'].append(name)
            continue
        local = _artifact(artifact_dir, name, limit)
        if name == target_tool.FILENAME and local is not None:
            # The /4 records (WITHDRAWN, kept rows, NA with acquired_at) are only trusted in a file its validator accepts.
            try:
                target_tool.require_public_inputs(local)
            except Exception:
                out['artifact_invalid'].append(name)
                local = None
        if name == fl.FILENAME:
            out['ledger_markers'], out['ledger_lists'] = compare_ledger(live, local)
            continue
        out['rows'] += [compare_rows(name, section, live, local) for section in rest[1]]
    return out


def _text(value):
    if value is None:
        return 'NONE'
    return value.isoformat() if isinstance(value, date) and not isinstance(value, datetime) else \
        value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _key(value):
    return value if type(value) is str and _PRINTABLE_KEY.fullmatch(value) else 'UNPRINTABLE'


def _version(value):
    return value if type(value) is str and _PRINTABLE_VERSION.fullmatch(value) else 'UNPRINTABLE'


def _details(name, section, lines):
    for line in lines[:MAX_DETAIL]:
        print(f'PAGES_FRESHNESS_REGRESSION file={name} section={section} {line}')
    if len(lines) > MAX_DETAIL:
        print(f'PAGES_FRESHNESS_REGRESSION_MORE file={name} section={section} shown={MAX_DETAIL} total={len(lines)}')


def run(artifact_dir, *, open_response=None, environ=None):
    try:
        result = compare(artifact_dir, open_response=open_response, environ=environ)
    except LiveUnreachable as error:
        print(f'PAGES_FRESHNESS_LIVE_UNREACHABLE file={error.name} deploy=REFUSED')
        return 1
    except Exception:
        print('PAGES_FRESHNESS_CHECK_FAILED deploy=REFUSED')
        return 1
    verdicts = []
    for name in result['live_invalid']:
        print(f'PAGES_FRESHNESS_LIVE_INVALID file={name} deploy=REFUSED')
    for name in result.get('artifact_invalid', []):
        print(f'PAGES_FRESHNESS_ARTIFACT_INVALID file={name} rows=NONE')
    for r in result['rows']:
        counts = ' '.join(f'{k}={v}' for k, v in r['counts'].items())
        print(f"PAGES_FRESHNESS file={r['file']} section={r['section']} verdict={r['verdict']} {counts} "
              f"artifact_latest={_text(r['artifact_latest'])} live_latest={_text(r['live_latest'])}")
        _details(r['file'], r['section'], [f'code={_key(key)} kind={kind} artifact={_text(ours)} live={_text(theirs)}'
                                           for key, kind, ours, theirs in r['regressions']])
        verdicts.append(r['verdict'])
    for marker_name, verdict, mine, theirs in result['ledger_markers']:
        print(f'PAGES_FRESHNESS file={fl.FILENAME} marker={marker_name} verdict={verdict} '
              f'artifact={_text(mine)} live={_text(theirs)}')
        verdicts.append('REFUSED' if verdict in MARKER_REFUSING else 'NO_LIVE' if verdict == 'NO_LIVE' else 'PASS')
    for r in result['ledger_lists']:
        section = 'versions.' + _version(r['version'])
        counts = ' '.join(f'{k}={v}' for k, v in r['counts'].items())
        print(f"PAGES_FRESHNESS file={fl.FILENAME} section={section} verdict={r['verdict']} {counts}")
        _details(fl.FILENAME, section, [f'index={index} kind={kind} date={_text(_day(day))}'
                                        for index, kind, day in r['regressions']])
        verdicts.append(r['verdict'])
    rows_compared = sum(r['counts']['compared'] for r in result['rows'])
    rows_regressed = sum(len(r['regressions']) for r in result['rows'])
    records_compared = sum(r['counts']['live_records'] for r in result['ledger_lists'])
    records_regressed = sum(len(r['regressions']) for r in result['ledger_lists'])
    refused, live_invalid = verdicts.count('REFUSED'), len(result['live_invalid'])
    totals = (f"checks={len(verdicts)} refused={refused} no_live={verdicts.count('NO_LIVE')} live_invalid={live_invalid} "
              f"rows_compared={rows_compared} rows_regressed={rows_regressed} "
              f"records_compared={records_compared} records_regressed={records_regressed}")
    if refused or live_invalid:
        print('PAGES_FRESHNESS_REFUSED ' + totals)
        return 1
    print('PAGES_FRESHNESS_PASS ' + totals)
    return 0


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--artifact-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    return run(args.artifact_dir)


if __name__ == '__main__':
    raise SystemExit(main())
