"""U8 plan: the IEX HIST TOPS files the V4 (v_vs_own_history) month-end backfill needs (owner decision GSQ-024, 2026-10-23).

Months = the YYYY-MM of every ebit_per_share_history[*].fiscal_year_end in the published sec-qgv2.json (latest 5 per company);
date = the last date of that month with a TOPS 1.6 file in the IEX hist index (= last trading day); symbols = the IEX symbols of
the Universe codes whose history has that month (SYMBOL_ALIASES applied by date). The plan holds public metadata only (links,
sizes, md5, tickers). Stdout: counts only.

    python implementation/tools/iex_hist/monthend_plan.py [--qgv2 PATH|URL] [--hist PATH|URL] [--gcs-md5] [--out plan.json]
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from investment_system.universe.universe_codes import public_payload  # noqa: E402

SCHEMA = 'iex-monthend-plan/1'
QGV2 = 'https://kco994553-star.github.io/Investment-System1/sec-qgv2.json'
HIST = 'https://iextrading.com/api/1.0/hist'
FEED = ('TOPS', '1.6')
HISTORY_KEY = 'ebit_per_share_history'  # the only history V4 pairs with month-end closes (qgv-v2.js monthClose)
LATEST_YEARS = 5

# Universe code -> [(from_date YYYY-MM-DD, IEX symbol)], applied to month-end dates >= from_date (latest matching entry wins);
# before the first entry the symbol is the code's own ticker ('NYSE:BRK.B' -> 'BRK.B'). Main extends this table; every entry
# names its evidence and whether it is confirmed. A code IEX does not trade (e.g. NASDAQ:WBD, no IEX trades on 2026-10-22) is
# not aliased: it stays NO_TRADE and is never filled.
SYMBOL_ALIASES: dict[str, tuple[tuple[str, str, str], ...]] = {
    # Skydance Corp (formerly Paramount Skydance, CIK 0002041610): Form 25 (Nasdaq) 2026-10-05; on IEX the line trades as SKYD
    # (IEX probe run 39944426209: PSKY status T with regular trades on 2026-10-02 and 10-05, no status/trade from 10-06;
    # SKYD no status/trade through 10-05, status T with regular trades from 10-06; 10-21/22 the same).
    'NASDAQ:PSKY': (('2026-10-06', 'SKYD', 'CONFIRMED: IEX TOPS last PSKY day 2026-10-05, first SKYD day 2026-10-06'),),
}
# Months before a cut date are NOT requested: V4 stays NA with the reason (owner decision 2026-10-23: Paramount Skydance's
# pre-merger history is the predecessor's (Paramount Global) share basis, unconfirmed against the merged line).
V4_NA_BEFORE: dict[str, tuple[str, str]] = {
    'NASDAQ:PSKY': ('2025-08-07', 'MERGER_PRE_BASIS_UNCONFIRMED'),
}


def load_json(source: str):
    if source.startswith('https://'):
        with urllib.request.urlopen(source, timeout=120) as r:
            return json.load(r)
    return json.loads(Path(source).read_text(encoding='utf-8'))


def iex_symbol(code: str, day: str, aliases=SYMBOL_ALIASES) -> str:
    """IEX symbol of a Universe code on day YYYYMMDD or YYYY-MM-DD."""
    iso = day if '-' in day else f'{day[:4]}-{day[4:6]}-{day[6:]}'
    symbol = code.split(':', 1)[1]
    for since, alias, _ in sorted(aliases.get(code, ())):
        if iso >= since:
            symbol = alias
    return symbol


def history_months(qgv2: dict, codes, *, latest=LATEST_YEARS, na_before=V4_NA_BEFORE) -> dict[str, list[str]]:
    """{YYYY-MM: [codes]} of the latest `latest` history entries of each code (codes outside the published records skipped)."""
    records = qgv2.get('records') if isinstance(qgv2, dict) else None
    if not isinstance(records, dict):
        raise ValueError('QGV2_RECORDS_INVALID')
    months: dict[str, set] = {}
    for code in codes:
        record = records.get(code)
        v = record.get('v_inputs_v2') if isinstance(record, dict) else None
        history = v.get(HISTORY_KEY) if isinstance(v, dict) else None
        ends = sorted({h['fiscal_year_end'] for h in history or () if isinstance(h, dict) and isinstance(h.get('fiscal_year_end'), str)
                       and len(h['fiscal_year_end']) == 10})
        cut = na_before.get(code, (None,))[0]
        for end in ends[-latest:]:
            if cut and end < cut:
                continue  # V4 NA (reason in V4_NA_BEFORE), never requested or filled
            months.setdefault(end[:7], set()).add(code)
    return {m: sorted(c) for m, c in sorted(months.items())}


def tops_files(index: dict) -> dict[str, dict]:
    """{YYYYMMDD: TOPS 1.6 entry} of the hist index ({date: [feed entries]})."""
    out = {}
    for day, feeds in index.items():
        for f in feeds if isinstance(feeds, list) else ():
            if isinstance(f, dict) and (f.get('feed'), f.get('version')) == FEED and str(f.get('link', '')).startswith('https://'):
                out[day] = f
    return out


def build(qgv2: dict, index: dict, codes, *, aliases=SYMBOL_ALIASES, latest=LATEST_YEARS, na_before=V4_NA_BEFORE) -> dict:
    files = tops_files(index)
    months, missing = [], []
    for month, month_codes in history_months(qgv2, codes, latest=latest, na_before=na_before).items():
        days = sorted(d for d in files if d[:6] == month.replace('-', ''))
        if not days:
            missing.append(month)
            continue
        day = days[-1]
        entry = files[day]
        symbols = {c: iex_symbol(c, day, aliases) for c in month_codes}
        months.append({'month': month, 'date': day, 'link': entry['link'], 'size': int(entry['size']),
                       'md5': entry.get('md5'), 'codes': symbols, 'symbols': sorted(set(symbols.values()))})
    return {'schema': SCHEMA, 'feed': '/'.join(FEED), 'history_key': HISTORY_KEY, 'latest_years': latest,
            'qgv2_as_of': qgv2.get('as_of'), 'qgv2_calc_version': qgv2.get('calc_version'),
            'aliases': {c: [list(a) for a in v] for c, v in sorted(aliases.items())},
            'v4_na_before': {c: list(v) for c, v in sorted(na_before.items())},
            'months': months, 'months_without_file': missing}


def gcs_metadata_url(link: str) -> str:
    """The GCS JSON-API object metadata URL (md5Hash, size) of a hist download link."""
    parts = urllib.parse.urlsplit(link)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != 'alt']
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path.replace('/download/storage/', '/storage/', 1),
                                    urllib.parse.urlencode(query), ''))


def add_gcs_md5(plan: dict, fetch=load_json) -> None:
    for m in plan['months']:
        if m.get('md5'):
            continue
        meta = fetch(gcs_metadata_url(m['link']))
        if int(meta.get('size', -1)) != m['size']:
            raise ValueError('GCS_SIZE_MISMATCH ' + m['month'])
        m['md5'] = base64.b64decode(meta['md5Hash']).hex()


def shard_months(plan: dict, shards: int) -> list[list[str]]:
    """Deterministic size balancing (largest first onto the lightest shard; ties -> lower index)."""
    load = [0] * shards
    out: list[list[str]] = [[] for _ in range(shards)]
    for m in sorted(plan['months'], key=lambda x: (-x['size'], x['month'])):
        i = min(range(shards), key=lambda j: (load[j], j))
        load[i] += m['size']
        out[i].append(m['month'])
    return [sorted(x) for x in out]


def summary(plan: dict, shards: int | None = None) -> dict:
    counts = [len(m['symbols']) for m in plan['months']]
    out = {'schema': plan['schema'], 'qgv2_as_of': plan['qgv2_as_of'], 'months': len(plan['months']),
           'files': len({m['date'] for m in plan['months']}), 'total_gb': round(sum(m['size'] for m in plan['months']) / 1e9, 1),
           'first_month': plan['months'][0]['month'] if plan['months'] else None,
           'last_month': plan['months'][-1]['month'] if plan['months'] else None,
           'symbols_per_month_min': min(counts, default=0), 'symbols_per_month_max': max(counts, default=0),
           'symbol_requests': sum(counts), 'codes': len({c for m in plan['months'] for c in m['codes']}),
           'md5_known': sum(1 for m in plan['months'] if m.get('md5')), 'months_without_file': plan['months_without_file']}
    if shards:
        by = {m['month']: m['size'] for m in plan['months']}
        out['shard_gb'] = [round(sum(by[x] for x in s) / 1e9, 1) for s in shard_months(plan, shards)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--qgv2', default=QGV2)
    ap.add_argument('--hist', default=HIST)
    ap.add_argument('--gcs-md5', action='store_true', help='add md5 from the GCS object metadata of each file')
    ap.add_argument('--shards', type=int, default=6)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    plan = build(load_json(a.qgv2), load_json(a.hist), public_payload()['codes'])
    if a.gcs_md5:
        add_gcs_md5(plan)
    if a.out:
        Path(a.out).write_text(json.dumps(plan, separators=(',', ':'), sort_keys=True), encoding='utf-8')
    print(json.dumps(summary(plan, a.shards), sort_keys=True))
    return 0 if plan['months'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
