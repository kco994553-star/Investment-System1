#!/usr/bin/env python3
"""One counts-only coverage line for the FINAL Pages artifact's published `sec-qgv2.json`.

Owner instruction 2026-10-15: coverage is reported from the file actually published (Q and G score counts of
that file), labelled so it is never confused with an offline recalculation estimate. The line carries counts,
dates and a version only: no tickers, CIKs, values, scores or prices.

    PUBLISHED_COVERAGE basis=PUBLISHED_FILE file=sec-qgv2.json universe=504 q=<n> g=<n> qg_both=<n>
        live=<n> stale=<n> not_available=<n> shards_seen=<k>/<shard_count> acquired_oldest=<date|NONE>
        acquired_newest=<date|NONE> stale_7d_rows=<n> never_acquired_rows=<n>
        shard_rows=0:<n>,1:<n>,... shard_acquired=0:<oldest>/<newest>,1:... as_of=<iso> calc_version=<value|NONE>

`shards_seen` counts the shards (sha256(cik) mod shard_count, the daily partition rule) with at least one
collected row in the file. Per shard, `shard_rows` counts the rows with a successful SEC acquisition and
`shard_acquired` gives the oldest/newest acquisition date of those rows (`NONE` when the shard has none).
`stale_7d_rows` counts rows whose acquisition is more than 7 days before the file's `as_of` (7-day freshness
rule, owner 2026-10-15 evening); `never_acquired_rows` counts rows with no acquisition at all. The tool always
exits 0 so it can never withhold the artifact upload.
"""
import argparse
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.universe import sec_qgv2 as qgv2
from investment_system.universe.sec_universe_shares import _clock

PREFIX = 'PUBLISHED_COVERAGE basis=PUBLISHED_FILE file=' + qgv2.FILENAME
FRESH_WINDOW = timedelta(days=7)
_VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:+/-]{0,63}')  # e.g. qgv2-calc/2026-10-15.1 (the v2_factors CALC_VERSION form)


def _day(value):
    try:
        return date.fromisoformat(value[:10]).isoformat() if type(value) is str else None
    except ValueError:
        return None


def _calc_version(payload):
    value = payload.get('calc_version')
    return value if type(value) is str and _VERSION.fullmatch(value) else 'NONE'


def coverage_line(payload):
    """Counts-only line for a validated `sec-qgv2.json` payload."""
    rows = list(payload['records'].values())
    q = {i for i, r in enumerate(rows) if r['axes']['Q']['score'] is not None}
    g = {i for i, r in enumerate(rows) if r['axes']['G']['score'] is not None}
    state = lambda value: sum(1 for r in rows if r['state'] == value)
    count = payload['shard_count']
    collected = [r for r in rows if r['cik'] is not None and r['acquired_at'] is not None]
    shards = {int(sha256(r['cik'].encode()).hexdigest(), 16) % count for r in collected}
    days = sorted(d for d in (_day(r['acquired_at']) for r in collected) if d is not None)
    cut = _clock(payload['as_of'])
    stale_7d = sum(1 for r in collected if cut - _clock(r['acquired_at']) > FRESH_WINDOW)
    never = sum(1 for r in rows if r['acquired_at'] is None)
    by_shard = {index: [] for index in range(count)}
    for r in collected:
        by_shard[int(sha256(r['cik'].encode()).hexdigest(), 16) % count].append(_day(r['acquired_at']))
    shard_rows = ','.join(f'{i}:{len(by_shard[i])}' for i in range(count))
    shard_acquired = ','.join(f'{i}:{min(d)}/{max(d)}' if d else f'{i}:NONE' for i, d in by_shard.items())
    as_of =payload['as_of'] if type(payload['as_of']) is str and re.fullmatch(r'[0-9T:Z.+-]{10,40}', payload['as_of']) else 'NONE'
    return (f"{PREFIX} universe={len(rows)} q={len(q)} g={len(g)} qg_both={len(q & g)} "
            f"live={state('LIVE')} stale={state('STALE')} not_available={state('NOT_AVAILABLE')} "
            f"shards_seen={len(shards)}/{count} acquired_oldest={days[0] if days else 'NONE'} "
            f"acquired_newest={days[-1] if days else 'NONE'} stale_7d_rows={stale_7d} never_acquired_rows={never} "
            f"shard_rows={shard_rows} shard_acquired={shard_acquired} as_of={as_of} calc_version={_calc_version(payload)}")


def report(artifact_dir):
    path = Path(artifact_dir) / qgv2.FILENAME
    if path.is_symlink() or not path.is_file():
        return PREFIX + ' status=MISSING'
    try:
        payload = qgv2.require_qgv2(qgv2.parse_json(path.read_bytes()))
    except Exception:
        return PREFIX + ' status=INVALID'
    try:
        return coverage_line(payload)
    except Exception:
        return PREFIX + ' status=INVALID'


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print('PUBLISHED_COVERAGE CONFIG_INVALID')
        raise SystemExit(0)


def main(argv=None):
    parser = SafeParser(description=__doc__)
    parser.add_argument('--artifact-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    print(report(args.artifact_dir))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
