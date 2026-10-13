#!/usr/bin/env python3
"""Replay the macro lights v1 (PLAYBOOK_V1 13-5) over history from LOCAL CSV files; results go to stdout only.

Run it on your own machine or device. It never fetches, never writes a file and never logs to CI: the market (SPY) and
credit (HYG/IEF) lights are price-derived, so their replay output must stay private (do not commit or paste it into the
public repository, Pages or Actions logs). The public lights (employment, inflation, curve) can be replayed alone by
omitting --spy/--hyg/--ief.

Inputs (CSV with a header; first column = date YYYY-MM-DD; value column = --column if given, else the first of
close/Close/price/value, else the second column; '.', '', 'NA' are missing, never 0). A series option may be repeated:
later files only fill dates the earlier files do not have.
  --unrate  monthly unemployment rate % (BLS LNS14000000 / FRED UNRATE)       date = first day of the month
  --cpi     monthly CPI-U NSA index (BLS CUUR0000SA0 / FRED CPIAUCNS)         date = first day of the month
  --gdp     quarterly real GDP % change SAAR (BEA A191RL)                     date = first day of the quarter
  --curve   daily 10 Y − 3 M spread %  (Treasury par yield curve, e.g. FRED T10Y3M), or two columns via --curve-columns
  --spy / --hyg / --ief   daily closes

Point in time (approximation, revised data): a month is used from the 15th of the next month (BLS release lag), a quarter
from 30 days after its end (BEA advance estimate). Daily series are used up to the evaluation day; the market/credit lights
see at most the last 5 years like the device's Worker range. Evaluation every Friday.

Usage: macro_lights_replay.py --unrate U.csv --cpi C.csv --gdp G.csv --curve T.csv [--spy S.csv --hyg H.csv --ief I.csv]
                              [--period 2000:2000-01-01:2002-12-31 ...] [--weekly]
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.macro import macro_lights_v1 as ml  # noqa: E402

DEFAULT_PERIODS = ('2000:2000-01-01:2002-12-31', '2008:2007-07-01:2009-06-30', '2020:2020-01-01:2020-12-31',
                   '2022:2022-01-01:2022-12-31', 'calm-2004:2004-01-01:2006-12-31', 'calm-2013:2013-01-01:2019-12-31',
                   'recent:2023-01-01:2026-12-31')
LABELS = {'NORMAL': '정상', 'WARNING': '경고', 'CRISIS': '위기'}


def read_series(paths, column=None, columns=None):
    out = {}
    for path in paths or ():
        with open(path, newline='', encoding='utf-8-sig') as handle:
            rows = list(csv.reader(handle))
        header = [h.strip() for h in rows[0]]
        def index(name):
            return header.index(name)
        if columns:
            idx = [index(c) for c in columns]
        elif column:
            idx = [index(column)]
        else:
            pick = next((h for h in ('close', 'Close', 'price', 'value') if h in header), header[1])
            idx = [index(pick)]
        for row in rows[1:]:
            if not row or not row[0].strip():
                continue
            day = row[0].strip()[:10]
            try:
                date.fromisoformat(day)
            except ValueError:
                continue
            values = []
            for i in idx:
                raw = row[i].strip() if i < len(row) else ''
                try:
                    values.append(float(raw) if raw not in ('', '.', 'NA', 'null', 'None') else None)
                except ValueError:
                    values.append(None)
            if day not in out:
                out[day] = values if len(values) > 1 else values[0]
    return dict(sorted(out.items()))


def monthly_available(series, day, lag_days=14):
    """Months whose value would have been published by `day` (released ~mid next month)."""
    out = []
    for key, value in series.items():
        y, m = int(key[:4]), int(key[5:7])
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        if nxt + timedelta(days=lag_days) <= day:
            out.append([key[:7], value])
    return out


def growth_available(series, day):
    latest = None
    for key, value in series.items():
        y, m = int(key[:4]), int(key[5:7])
        end = date(y + (m + 3 > 12), (m + 2) % 12 + 1, 1)  # first day after the quarter
        if end + timedelta(days=30) <= day and value is not None:
            latest = (key, value)
    return None if latest is None else latest[1] / 100


def daily_window(series, day, years=None):
    """Daily rows up to `day`. Rows without a value are dropped: FRED-style files list market holidays as '.', while the
    Treasury XML and the Worker only list published sessions."""
    start = (day - timedelta(days=int(365.25 * years) + 1)).isoformat() if years else '0000'
    end = day.isoformat()
    return [[k, v] for k, v in series.items() if start <= k <= end and v is not None]


def evaluate(day, data):
    unrate, cpi = monthly_available(data['unrate'], day), monthly_available(data['cpi'], day)
    lights = {
        'employment': ml.employment_light(unrate[-30:]) if unrate else ml.unavailable('employment', 'NO_DATA'),
        'inflation': ml.inflation_light(cpi[-30:]) if cpi else ml.unavailable('inflation', 'NO_DATA'),
    }
    curve = [[k, 0.0, v] for k, v in daily_window(data['curve'], day, 1)] if data['curve'] else []
    lights['curve'] = ml.curve_light(curve) if curve else ml.unavailable('curve', 'NO_DATA')
    spy = daily_window(data['spy'], day, 5)
    lights['market'] = ml.market_light(spy) if spy else ml.unavailable('market', 'NO_DATA')
    hyg, ief = daily_window(data['hyg'], day, 1), daily_window(data['ief'], day, 1)
    lights['credit'] = ml.credit_light(hyg, ief) if hyg and ief else ml.unavailable('credit', 'NO_DATA')
    cpi_yoy = lights['inflation']['yoy'] if lights['inflation']['lit'] is not None else None
    growth = growth_available(data['gdp'], day)
    return lights, ml.macro_state(lights, cpi_yoy, growth), cpi_yoy, growth


def fridays(start, end):
    d = start + timedelta(days=(4 - start.weekday()) % 7)
    while d <= end:
        yield d
        d += timedelta(days=7)


def replay(name, start, end, data, out=print):
    counts, first, lit_first, low = {'NORMAL': 0, 'WARNING': 0, 'CRISIS': 0}, {}, {}, 0
    episodes, previous = [], None
    for day in fridays(start, end):
        lights, state, cpi, growth = evaluate(day, data)
        s = state['state']
        counts[s] += 1
        first.setdefault(s, (day.isoformat(), state['reasons'], state['lit_count'], state['available_count']))
        low += state['low_confidence']
        for k, row in lights.items():
            if row['lit']:
                lit_first.setdefault(k, day.isoformat())
        if s != previous:
            episodes.append((day.isoformat(), s, ','.join(k for k, r in lights.items() if r['lit']) or '-',
                             '%d/%d' % (state['lit_count'], state['available_count']), ','.join(state['reasons'])))
            previous = s
    weeks = sum(counts.values())
    out('== %s (%s → %s, %d weeks) ==' % (name, start, end, weeks))
    out('  weeks: ' + ', '.join('%s %d' % (LABELS[k], v) for k, v in counts.items()) + ' · low confidence %d' % low)
    for s in ('WARNING', 'CRISIS'):
        if s in first:
            d, reasons, n, a = first[s]
            out('  first %s: %s (%s, lit %d/%d)' % (LABELS[s], d, ','.join(reasons), n, a))
        else:
            out('  first %s: none' % LABELS[s])
    out('  first lit per light: ' + ', '.join('%s %s' % (k, lit_first.get(k, '-')) for k in ml.LIGHTS))
    out('  state changes: ' + ' | '.join('%s %s [%s %s %s]' % e for e in episodes))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('unrate', 'cpi', 'gdp', 'curve', 'spy', 'hyg', 'ief'):
        p.add_argument('--' + name, action='append', default=[])
    p.add_argument('--curve-columns', nargs=2, metavar=('THREE_MONTH', 'TEN_YEAR'))
    p.add_argument('--period', action='append', default=[])
    args = p.parse_args(argv)
    data = {k: read_series(getattr(args, k)) for k in ('unrate', 'cpi', 'gdp', 'spy', 'hyg', 'ief')}
    if args.curve_columns:
        raw = read_series(args.curve, columns=args.curve_columns)
        data['curve'] = {k: (None if None in v else v[1] - v[0]) for k, v in raw.items()}
    else:
        data['curve'] = read_series(args.curve)
    print('macro lights %s · %s · replay on revised data with release lags (approximation)' % (ml.CONFIG['version'], ml.CONFIG['status']))
    for name, series in data.items():
        keys = [k for k, v in series.items() if v is not None]
        print('  input %-7s %s' % (name, ('%s → %s (%d)' % (keys[0], keys[-1], len(keys))) if keys else 'NOT PROVIDED'))
    for spec in args.period or DEFAULT_PERIODS:
        name, start, end = spec.split(':')
        replay(name, date.fromisoformat(start), date.fromisoformat(end), data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
