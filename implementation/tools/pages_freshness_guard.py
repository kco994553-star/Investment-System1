#!/usr/bin/env python3
"""Pre-deploy freshness guard: never publish public data older than the live GitHub Pages copy.

Owner queue 2026-10-17 §5. Two workflows deploy Pages in the concurrency group `checked-cockpit-pages`: the daily
`sec-daily-public-inputs.yml` (collect merges a new SEC shard into the live copy it read) and the manual
`cockpit-pages.yml` (its build re-publishes the live copy read at build time). The group serialises the deploys but not
their order, so an artifact built from the live copy at T0 could be deployed after a newer deploy at T1 and roll the
public data back. This check runs inside each deploy job (which holds the group), immediately before
actions/deploy-pages, on exactly the artifact that job deploys.

Markers are data-acquisition times, never the files' `as_of`: the preserve-only path of the manual build re-stamps
`as_of` of the Universe files to its own build time, so `as_of` there says when the artifact was built, not how new its
data is. Compared per file (artifact vs live, same file only):

- sec-universe-shares.json, sec-universe-qg.json: latest `acquired_at` over `records`;
- sec-qgv2.json: latest `acquired_at` over `records` and `target`;
- sec-public-inputs.json: latest `acquired_at` over `companies`;
- forward-validation-ledger.json: `as_of` (written only by the daily ledger step; the manual build copies the bytes)
  and the last recorded session date.

Verdict per marker: artifact newer or equal -> pass; artifact older -> REFUSED; live has a marker and the artifact has
none (file missing or no stamped row) -> REFUSED; live 404 or live without a marker -> pass. A live file that is
served (200) but is oversized or not JSON cannot be rolled back by anything and is reported LIVE_INVALID (not compared).
Any other live read failure (network, HTTP status, redirect) fails closed: LIVE_UNREACHABLE, exit 1, nothing deployed.

The live copy is read with each daily tool's own previous-copy reader (same URL, no redirects, 404 = absent) plus a
per-run query string so a CDN copy cached before the previous deploy is not mistaken for the live one. Only fixed codes,
file names, counts and dates are printed; no values, URLs or secrets.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_validation_ledger as ledger_tool
import preserve_public_sec_inputs as target_tool
import sec_universe_shares as universe_tool
from sec_universe_shares import _fetch_body  # the daily tools' live Pages reader (404 -> None, other failure -> OSError)


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


def _latest_acquired(*sections):
    def marker(payload):
        stamps = []
        for section in sections:
            rows = payload.get(section)
            rows = rows.values() if type(rows) is dict else rows if type(rows) is list else ()
            stamps += [_instant(row.get('acquired_at')) for row in rows if type(row) is dict]
        stamps = [s for s in stamps if s is not None]
        return max(stamps) if stamps else None
    return marker


def _ledger_as_of(payload):
    return _instant(payload.get('as_of'))


def _ledger_session(payload):
    try:
        return _day(ledger_tool.last_session(payload))
    except (KeyError, IndexError, TypeError, AttributeError):
        return None


# (published file, live URL as its daily previous-copy reader uses it, byte limit, marker name, extractor)
MARKERS = (
    (universe_tool.FILENAME, universe_tool.SOURCE, universe_tool.MAX_BYTES, 'acquired_at', _latest_acquired('records')),
    (universe_tool.qg.FILENAME, universe_tool.QG_SOURCE, universe_tool.qg.MAX_BYTES, 'acquired_at',
     _latest_acquired('records')),
    (universe_tool.qgv2.FILENAME, universe_tool.QGV2_SOURCE, universe_tool.qgv2.MAX_BYTES, 'acquired_at',
     _latest_acquired('records', 'target')),
    (target_tool.FILENAME, target_tool.SOURCE, target_tool.MAX_BYTES, 'acquired_at', _latest_acquired('companies')),
    (ledger_tool.fl.FILENAME, ledger_tool.SOURCE, ledger_tool.fl.MAX_BYTES, 'as_of', _ledger_as_of),
    (ledger_tool.fl.FILENAME, ledger_tool.SOURCE, ledger_tool.fl.MAX_BYTES, 'session', _ledger_session),
)


class LiveUnreachable(Exception):
    def __init__(self, name):
        super().__init__(name)
        self.name = name


def _payload(body, limit):
    """Bytes -> JSON object, or None when oversized, not UTF-8, not JSON or not an object."""
    if body is None or len(body) > limit:
        return None
    def invalid_constant(_):
        raise ValueError
    try:
        value = json.loads(body.decode('utf-8', errors='strict'), parse_constant=invalid_constant)
    except (ValueError, RecursionError):
        return None
    return value if type(value) is dict else None


def _run_nonce(environ):
    run_id, attempt = environ.get('GITHUB_RUN_ID', ''), environ.get('GITHUB_RUN_ATTEMPT', '')
    if run_id.isdigit() and attempt.isdigit():
        return run_id + '-' + attempt
    return str(time.time_ns())


def _text(value):
    if value is None:
        return 'NONE'
    return value.isoformat() if isinstance(value, date) and not isinstance(value, datetime) else \
        value.strftime('%Y-%m-%dT%H:%M:%SZ')


def compare(artifact_dir, *, open_response=None, environ=None):
    """-> list of (file, marker, verdict, artifact marker, live marker). Raises LiveUnreachable on a failed live read.

    Verdicts: NEWER, EQUAL, NO_LIVE, LIVE_INVALID (pass) and OLDER, MISSING (refuse)."""
    environ = os.environ if environ is None else environ
    artifact_dir = Path(artifact_dir)
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        raise ValueError('PAGES_FRESHNESS ARTIFACT_INVALID')
    nonce = _run_nonce(environ)
    live_cache, results = {}, []
    for name, source, limit, marker_name, marker in MARKERS:
        if name not in live_cache:
            try:
                live_cache[name] = _fetch_body(f'{source}?deploy-check={nonce}', limit, open_response)
            except OSError:
                raise LiveUnreachable(name) from None
        body = live_cache[name]
        live = _payload(body, limit)
        path = artifact_dir / name
        local = _payload(path.read_bytes(), limit) if path.is_file() and not path.is_symlink() else None
        mine = marker(local) if local is not None else None
        if body is not None and live is None:
            results.append((name, marker_name, 'LIVE_INVALID', mine, None))
            continue
        theirs = marker(live) if live is not None else None
        if theirs is None:
            verdict = 'NO_LIVE'
        elif mine is None:
            verdict = 'MISSING'
        else:
            verdict = 'OLDER' if mine < theirs else 'EQUAL' if mine == theirs else 'NEWER'
        results.append((name, marker_name, verdict, mine, theirs))
    return results


REFUSING = ('OLDER', 'MISSING')


def run(artifact_dir, *, open_response=None, environ=None):
    try:
        results = compare(artifact_dir, open_response=open_response, environ=environ)
    except LiveUnreachable as error:
        print(f'PAGES_FRESHNESS_LIVE_UNREACHABLE file={error.name} deploy=REFUSED')
        return 1
    except Exception:
        print('PAGES_FRESHNESS_CHECK_FAILED deploy=REFUSED')
        return 1
    for name, marker_name, verdict, mine, theirs in results:
        print(f'PAGES_FRESHNESS file={name} marker={marker_name} verdict={verdict} '
              f'artifact={_text(mine)} live={_text(theirs)}')
    count = lambda *verdicts: sum(1 for r in results if r[2] in verdicts)
    totals = (f"markers={len(results)} newer={count('NEWER')} equal={count('EQUAL')} no_live={count('NO_LIVE')} "
              f"live_invalid={count('LIVE_INVALID')} older={count('OLDER')} missing={count('MISSING')}")
    if count(*REFUSING):
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
