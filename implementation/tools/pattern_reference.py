#!/usr/bin/env python3
"""Synthetic reference vectors for ChartBars (chart-bars.js) and PatternEngine (pattern-engine.js).

Usage: pattern_reference.py --write
  regenerates tests/fixtures/chart_bars_reference_v1.json, tests/fixtures/pattern_engine_reference_v1.json and the
  device copy web_assets/pattern-config-defaults.js (from technical/pattern_rules_v1.json).
Every bar below is invented (symbol SYNTH1, made-up dates and prices); never a real price, holding or account value.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.technical import chart_bars as CB  # noqa: E402
from investment_system.technical import patterns as P  # noqa: E402

FIXTURES = ROOT / 'tests/fixtures'
CHART_FIXTURE = FIXTURES / 'chart_bars_reference_v1.json'
ENGINE_FIXTURE = FIXTURES / 'pattern_engine_reference_v1.json'
CONFIG_JS = ROOT / 'src/investment_system/product/web_assets/pattern-config-defaults.js'
SYMBOL = 'SYNTH1'
YAHOO = 'Yahoo Finance(비공식)'


# ---------------------------------------------------------------- synthetic builders

def weekdays(start, count, skip=()):
    d, out = date.fromisoformat(start), []
    while len(out) < count:
        if d.weekday() < 5 and d.isoformat() not in skip:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def raw_bar(day, o, h, l, c, v=1000, status='COMPLETE', hour=14, minute=30, adjusted=None, session_date=None):
    ts = int(datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=timezone.utc).timestamp())
    bar = {'timestamp': ts, 'open': o, 'high': h, 'low': l, 'close': c,
           'adjusted_close': adjusted if adjusted is not None else c, 'volume': v, 'session_status': status, 'day': day}
    if session_date:
        bar['session_date'] = session_date
    return bar


def history(raw, *, symbol=SYMBOL, tz='America/New_York', provider=YAHOO, read_at='2030-12-31T23:00:00Z'):
    bars = [{k: v for k, v in b.items() if k != 'day'} for b in raw]
    return {'schema': 'private-history/1', 'provider': provider, 'symbol': symbol, 'range': '5y', 'currency': 'USD',
            'exchange': 'NMS', 'timezone': tz, 'interval': '1d', 'basis': 'RAW_CLOSE', 'delay_status': 'UNKNOWN',
            'read_at': read_at, **({'timestamp_kind': 'PROVIDER_SESSION_LABEL'} if provider != YAHOO else {}), 'bars': bars}


def from_hlc(days, highs, lows, closes, volume=1000):
    """Bars from explicit highs/lows/closes; open = previous close clamped into the bar's range."""
    out, prev = [], None
    for d, h, l, c in zip(days, highs, lows, closes):
        o = c if prev is None else min(max(prev, l), h)
        out.append(raw_bar(d, o, h, l, c, volume))
        prev = c
    return out


def from_closes(days, closes, spread=1.0, volume=1000):
    out, prev = [], None
    for d, c in zip(days, closes):
        o = c if prev is None else prev
        out.append(raw_bar(d, round(o, 2), round(max(o, c) + spread, 2), round(min(o, c) - spread, 2), round(c, 2), volume))
        prev = c
    return out


def random_walk(seed, count, start='2030-01-07', base=100.0):
    rng = random.Random(seed)
    days, price, closes = weekdays(start, count), base, []
    drift = 0.0
    for n in range(count):
        if n % 40 == 0:
            drift = rng.choice((-0.004, 0.0, 0.004))
        price = max(5.0, price * (1 + drift + rng.gauss(0, 0.015)))
        closes.append(price)
    raw, prev = [], None
    for d, c in zip(days, closes):
        o = c if prev is None else prev * (1 + rng.gauss(0, 0.004))
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.006)))
        l = min(o, c) * (1 - abs(rng.gauss(0, 0.006)))
        raw.append(raw_bar(d, round(o, 2), round(h, 2), round(l, 2), round(c, 2), rng.randrange(0, 5000)))
        prev = c
    return raw


def zigzag(count, start='2030-01-07', base=100.0, legs=(8, -6, 10, -9, 7, -4, 12, -10), steps=5):
    days, closes, price, n = weekdays(start, count), [], base, 0
    while len(closes) < count:
        leg = legs[n % len(legs)]
        for _ in range(steps):
            price += leg / steps
            closes.append(price)
        n += 1
    return from_closes(days, closes[:count], spread=0.5)


def flat_hlc(count, overrides):
    """Calm base bars (high 101, low 99, close 100) with explicit (high, low, close) overrides by index."""
    highs, lows, closes = [101.0] * count, [99.0] * count, [100.0] * count
    for n, (h, l, c) in overrides.items():
        highs[n], lows[n], closes[n] = h, l, c
    return highs, lows, closes


ALL_SPLIT_FREE = {'status': 'AVAILABLE', 'covered_from': '2000-01-01', 'covered_to': '2099-12-31', 'events': []}


def rules_with(**overrides):
    rules = copy.deepcopy(P.load_rules())
    rules['params'].update(overrides)
    rules['params_sha256'] = P.params_sha256(rules['params'])
    return rules


# ---------------------------------------------------------------- chart-bars cases

def chart_cases():
    days = weekdays('2030-01-07', 12)
    basic = [raw_bar(d, 10 + i, 11 + i, 9 + i, 10.5 + i, 1000 + i) for i, d in enumerate(days)]
    basic[2]['volume'] = 0                      # real zero volume
    basic[3]['volume'] = None                   # missing volume
    basic[4].update(open=None, high=None, low=None, close=None)   # missing OHLC
    basic[5].update(open=30.0)                  # open above high -> inconsistent, kept raw, marked missing
    basic[6]['session_status'] = 'UNKNOWN'      # non-complete inside history
    basic[11]['session_status'] = 'IN_PROGRESS'  # provisional tail
    seoul = [raw_bar(d, 100, 101, 99, 100.5, 10, hour=15, minute=30) for d in weekdays('2030-01-07', 3)]  # 00:30 KST next day
    tiingo = [raw_bar(d, 20, 21, 19, 20.5, 5, hour=0, minute=0, session_date=d) for d in weekdays('2030-01-07', 4)]
    tiingo[-1]['session_status'] = 'UNKNOWN'
    dup = [raw_bar('2030-01-07', 10, 11, 9, 10, 1), raw_bar('2030-01-07', 10, 11, 9, 10, 1, hour=20), raw_bar('2030-01-08', 10, 11, 9, 10, 1)]
    cases = [
        {'id': 'normalize_codes', 'operation': 'normalize', 'input': {'history': history(basic)}},
        {'id': 'normalize_seoul_session_date', 'operation': 'normalize', 'input': {'history': {**history(seoul), 'timezone': 'Asia/Seoul', 'currency': 'KRW'}}},
        {'id': 'normalize_fallback_session_label', 'operation': 'normalize', 'input': {'history': history(tiingo, provider='Tiingo EOD')}},
        {'id': 'normalize_duplicate_session_date', 'operation': 'normalize', 'input': {'history': history(dup)}},
    ]
    # Weekly W1 (§7.4): weeks of 2030-01-07 .. ; Friday 2030-01-18 is a holiday; week 4 has missing OHLC, week 5 missing
    # volume, week 6 a real zero volume; the last week has no Friday yet.
    wdays = weekdays('2030-01-07', 28, skip=('2030-01-18',))
    wk = [raw_bar(d, 50, 52, 48, 51, 100) for d in wdays]
    wk[wdays.index('2030-01-30')].update(open=None, high=None, low=None, close=None)
    wk[wdays.index('2030-02-05')]['volume'] = None
    wk[wdays.index('2030-02-12')]['volume'] = 0
    wk_tail = [raw_bar(d, 50, 52, 48, 51, 100) for d in weekdays('2030-01-07', 9)]   # ends Thursday 2030-01-17
    wk_prov_friday = [raw_bar(d, 50, 52, 48, 51, 100) for d in weekdays('2030-01-07', 10)]
    wk_prov_friday[-1]['session_status'] = 'IN_PROGRESS'
    wk_mid = [raw_bar(d, 50, 52, 48, 51, 100) for d in weekdays('2030-01-07', 15)]
    wk_mid[7]['session_status'] = 'UNKNOWN'
    for cid, raw in (('weekly_w1_holiday_missing', wk), ('weekly_tail_not_closed', wk_tail),
                     ('weekly_friday_in_progress', wk_prov_friday), ('weekly_provisional_inside', wk_mid)):
        cases.append({'id': cid, 'operation': 'weekly', 'input': {'history': history(raw), 'actions': None}})
    split_days = weekdays('2030-01-07', 15)
    cases.append({'id': 'weekly_split_straddles_week', 'operation': 'weekly',
                  'input': {'history': history([raw_bar(d, 50, 52, 48, 51, 100) for d in split_days]),
                            'actions': {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2030-12-31',
                                        'events': [{'kind': 'SPLIT', 'effective_date': '2030-01-16'}, {'kind': 'DIVIDEND', 'effective_date': '2030-01-23'}]}}})
    avail = {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2030-06-30',
             'events': [{'kind': 'SPLIT', 'effective_date': '2030-03-02'}, {'kind': 'DIVIDEND', 'effective_date': '2030-02-01'}]}
    for cid, actions, start, end in (
            ('continuity_not_provided', None, '2030-01-07', '2030-02-07'),
            ('continuity_not_provided_explicit', {'status': 'NOT_PROVIDED'}, '2030-01-07', '2030-02-07'),
            ('continuity_lookup_failed', {'status': 'LOOKUP_FAILED'}, '2030-01-07', '2030-02-07'),
            ('continuity_invalid_kind', {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2030-06-30', 'events': [{'kind': 'SPINOFF', 'effective_date': '2030-02-01'}]}, '2030-01-07', '2030-02-07'),
            ('continuity_no_events', {**avail, 'events': []}, '2030-01-07', '2030-05-07'),
            ('continuity_dividend_only_window', avail, '2030-01-07', '2030-03-01'),
            ('continuity_split_in_window', avail, '2030-02-07', '2030-03-02'),
            ('continuity_starts_on_split', avail, '2030-03-02', '2030-04-02'),
            ('continuity_coverage_gap', avail, '2029-12-20', '2030-02-07')):
        cases.append({'id': cid, 'operation': 'continuity', 'input': {'actions': actions, 'start': start, 'end': end}})
    old_days = weekdays('2030-01-07', 6)
    old = [raw_bar(d, 10, 11, 9, 10, 100) for d in old_days]
    old[-1]['session_status'] = 'IN_PROGRESS'
    new = [raw_bar(d, 10, 11, 9, 10, 100) for d in weekdays('2030-01-10', 5)]
    new[0]['close'] = 10.5                  # revised complete bar (2030-01-10)
    new[0]['high'] = 11
    new[2]['volume'] = 101                 # 2030-01-14 was provisional before: replaced, not a revision
    cases.append({'id': 'merge_revision', 'operation': 'merge',
                  'input': {'previous': history(old), 'incoming': history(new, provider='Tiingo EOD', read_at='2031-01-01T23:00:00Z')}})
    cases.append({'id': 'session_set_mismatch', 'operation': 'session_set_mismatch',
                  'input': {'history': history([raw_bar(d, 10, 11, 9, 10, 1) for d in weekdays('2030-01-07', 10)]),
                            'store_dates': weekdays('2030-01-09', 12, skip=('2030-01-14',))}})
    for case in cases:
        case['synthetic'] = True
    return cases


def run_chart_case(case):
    i, op = case['input'], case['operation']
    if op == 'normalize':
        return CB.normalize(i['history'])
    if op == 'weekly':
        return CB.weekly(CB.normalize(i['history']), i['actions'])
    if op == 'continuity':
        return CB.continuity(i['actions'], i['start'], i['end'])
    if op == 'merge':
        return CB.merge(CB.normalize(i['previous']), CB.normalize(i['incoming']))
    if op == 'session_set_mismatch':
        return CB.session_set_mismatch(CB.normalize(i['history']), i['store_dates'])
    raise ValueError(op)


# ---------------------------------------------------------------- pattern-engine cases (pivots)

def engine_cases():
    cases = []
    zz = zigzag(120)
    cases.append({'id': 'pivots_zigzag_daily', 'operation': 'pivots', 'input': {'history': history(zz), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    cases.append({'id': 'pivots_zigzag_not_provided', 'operation': 'pivots', 'input': {'history': history(zz), 'timeframe': 'D', 'actions': None}})
    cases.append({'id': 'pivots_zigzag_weekly', 'operation': 'pivots', 'input': {'history': history(zigzag(400, legs=(24, -18, 30, -27, 21, -12, 36, -30), steps=15)), 'timeframe': 'W', 'actions': ALL_SPLIT_FREE}})
    days = weekdays('2030-01-07', 40)
    tie = flat_hlc(40, {20: (110, 99, 100), 22: (110, 99, 100), 26: (101, 90, 100), 31: (108, 99, 100)})
    highs, lows, closes = tie                       # equal highs at 20 and 22: the earlier bar wins (tie rule)
    cases.append({'id': 'pivots_tie_and_alternation', 'operation': 'pivots', 'input': {'history': history(from_hlc(days, *tie)), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    plateau = {18: (105, 103, 104), 19: (108, 106, 107), 20: (110, 107, 109)}
    plateau.update({n: (109.5, 108.5, 109) for n in range(21, 40)})
    plateau.update({26: (109.5, 108.3, 109), 31: (112, 108.5, 109), 35: (109.5, 100, 109)})
    cases.append({'id': 'pivots_superseded', 'operation': 'pivots', 'input': {'history': history(from_hlc(days, *flat_hlc(40, plateau))), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    miss = history(from_hlc(days, highs, lows, closes))
    miss['bars'][24].update(open=None, high=None, low=None, close=None)
    cases.append({'id': 'pivots_missing_bar_in_window', 'operation': 'pivots', 'input': {'history': miss, 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    split = {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2030-12-31', 'events': [{'kind': 'SPLIT', 'effective_date': '2030-03-04'}]}
    cases.append({'id': 'pivots_split_segments', 'operation': 'pivots', 'input': {'history': history(zz), 'timeframe': 'D', 'actions': split}})
    cases.append({'id': 'pivots_user_settings', 'operation': 'pivots', 'input': {'history': history(zz), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE, 'params': {'SWING_MIN_ATR': 2}}})
    rw = random_walk(7, 260)
    rw[-1]['session_status'] = 'IN_PROGRESS'
    cases.append({'id': 'pivots_random_walk_provisional_tail', 'operation': 'pivots', 'input': {'history': history(rw), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    for case in cases:
        case['synthetic'] = True
    return cases


def series_for(i):
    daily = CB.normalize(i['history'])
    return daily if i['timeframe'] == 'D' else CB.weekly(daily, i['actions'])


def run_engine_case(case):
    i = case['input']
    rules = rules_with(**i['params']) if i.get('params') else P.load_rules()
    if case['operation'] == 'pivots':
        return P.run_pivots(series_for(i), rules, i['actions'])
    raise ValueError(case['operation'])


# ---------------------------------------------------------------- fixtures and device config copy

def _build(cases, runner, title):
    return {'schema': 'reference-vectors/1', 'title': title, 'synthetic': True,
            'cases': [{**c, 'expected_json': json.dumps(runner(c), ensure_ascii=False, sort_keys=True)} for c in cases]}


def build_chart():
    return _build(chart_cases(), run_chart_case, 'ChartBars synthetic reference vectors')


def build_engine():
    return _build(engine_cases(), run_engine_case, 'PatternEngine synthetic reference vectors')


def config_js():
    rules = P.load_rules()
    body = json.dumps(rules, ensure_ascii=False, separators=(',', ':'))
    return ('/* pattern-rules/1 research defaults (RESEARCH_DEFAULT, not a validated investment rule). Generated from '
            'technical/pattern_rules_v1.json by tools/pattern_reference.py --write; do not edit by hand. */\n'
            "(function(r){const d=" + body + ";const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};"
            "freeze(d);if(typeof module==='object'&&module.exports)module.exports=d;else r.PatternConfigDefaults=d;})(globalThis);\n")


def main(argv):
    if argv[1:] != ['--write']:
        print(__doc__)
        return 2
    for path, value in ((CHART_FIXTURE, build_chart()), (ENGINE_FIXTURE, build_engine())):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    CONFIG_JS.write_text(config_js(), encoding='utf-8')
    print('PATTERN_REFERENCE_WRITTEN')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
