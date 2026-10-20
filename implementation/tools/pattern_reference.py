#!/usr/bin/env python3
"""Synthetic reference vectors for ChartBars (chart-bars.js) and PatternEngine (pattern-engine.js).

Usage: pattern_reference.py --write
  regenerates tests/fixtures/chart_bars_reference_v1.json, tests/fixtures/pattern_engine_reference_v1.json,
  tests/fixtures/pattern_signals_reference_v1.json and the
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


# ---------------------------------------------------------------- pattern scenario builders (TA_PREP §6)

def path(start, legs, warmup=20):
    """Closes: `warmup` flat bars at `start`, then legs of (bars, total change) in equal steps."""
    closes, price = [float(start)] * warmup, float(start)
    for count, delta in legs:
        for _ in range(count):
            price = round(price + delta / count, 6)
            closes.append(price)
    return closes


# Box base: peaks at 24 and 34 (high 110.5), troughs at 29 and 39 (low 99.5); the box is FORMED at bar 42.
BOX_BASE = [(5, 5), (5, -10), (5, 10), (5, -10)]
# Double bottom base: troughs at 24 and 34 (low 99.5), neckline peak at 29 (high 110.5); FORMED at bar 37.
DB_BASE = [(5, -5), (5, 10), (5, -10)]


def scenario(legs, base=BOX_BASE, start=105, spread=0.5, edit=None, warmup=20):
    closes = path(start, base + legs, warmup)
    raw = from_closes(weekdays('2030-01-07', len(closes)), closes, spread=spread)
    for index, change in (edit or {}).items():
        raw[index].update(change)
    return raw


def mirror(raw, axis=200):
    """Upside-down copy: double top / breakdown cases are the mirrored bottom / breakout cases."""
    out = []
    for b in raw:
        m = dict(b)
        for k in ('open', 'close', 'adjusted_close'):
            m[k] = None if b[k] is None else round(axis - b[k], 6)
        m['high'] = None if b['low'] is None else round(axis - b['low'], 6)
        m['low'] = None if b['high'] is None else round(axis - b['high'], 6)
        out.append(m)
    return out


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
            ('continuity_coverage_gap', avail, '2029-12-20', '2030-02-07'),
            # A confirmation covers only its own range: a window partly outside it stays unconfirmed, even with no events.
            ('continuity_coverage_gap_end', {**avail, 'events': []}, '2030-05-07', '2030-07-07'),
            ('continuity_coverage_gap_end_adjusted_split', {**avail, 'price_basis': 'SPLIT_ADJUSTED'}, '2030-02-07', '2030-07-01'),
            ('continuity_coverage_exact_bounds', {**avail, 'events': []}, '2030-01-01', '2030-06-30'),
            # Worker P1-W: split basis declared by the provider path. Prices are never re-adjusted.
            ('continuity_not_reported', {'status': 'NOT_REPORTED'}, '2030-01-07', '2030-02-07'),
            ('continuity_split_in_window_adjusted', {**avail, 'price_basis': 'SPLIT_ADJUSTED'}, '2030-02-07', '2030-04-02'),
            ('continuity_split_on_window_end_adjusted', {**avail, 'price_basis': 'SPLIT_ADJUSTED'}, '2030-02-07', '2030-03-02'),
            ('continuity_split_on_window_start_adjusted', {**avail, 'price_basis': 'SPLIT_ADJUSTED'}, '2030-03-02', '2030-04-02'),
            ('continuity_split_in_window_unadjusted', {**avail, 'price_basis': 'UNADJUSTED', 'volume_basis': 'UNADJUSTED'}, '2030-02-07', '2030-03-02'),
            ('continuity_no_split_unadjusted', {**avail, 'price_basis': 'UNADJUSTED'}, '2030-03-02', '2030-04-02'),
            ('continuity_invalid_basis', {**avail, 'price_basis': 'ADJUSTED_SOMEHOW'}, '2030-01-07', '2030-02-07')):
        cases.append({'id': cid, 'operation': 'continuity', 'input': {'actions': actions, 'start': start, 'end': end}})
    # Weekly bars across a split when the provider's prices are already split-adjusted: OHLC kept as delivered,
    # volume only when its share-count basis is adjusted too.
    split_raw = [raw_bar(d, 50, 52, 48, 51, 100) for d in split_days]
    adjusted = {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2030-12-31',
                'events': [{'kind': 'SPLIT', 'effective_date': '2030-01-16'}], 'price_basis': 'SPLIT_ADJUSTED', 'volume_basis': 'UNKNOWN'}
    cases.append({'id': 'weekly_split_adjusted_price_volume_unknown', 'operation': 'weekly', 'input': {'history': history(split_raw), 'actions': adjusted}})
    cases.append({'id': 'weekly_split_adjusted_price_and_volume', 'operation': 'weekly',
                  'input': {'history': history(split_raw), 'actions': {**adjusted, 'volume_basis': 'SPLIT_ADJUSTED'}}})
    cases.append({'id': 'weekly_split_unadjusted', 'operation': 'weekly',
                  'input': {'history': history(split_raw), 'actions': {**adjusted, 'price_basis': 'UNADJUSTED', 'volume_basis': 'UNADJUSTED'}}})
    # Worker split block -> corporate actions. A response without the block is NOT_PROVIDED, never "no split".
    basis = {'price': 'SPLIT_ADJUSTED', 'volume': 'UNKNOWN', 'source': 'PROVIDER_CONVENTION'}
    block_days = weekdays('2030-01-07', 6)
    plain = history([raw_bar(d, 10, 11, 9, 10, 100) for d in block_days])
    for cid, block in (
            ('from_history_old_response', {}),
            ('from_history_not_reported', {'split_coverage': {'status': 'NOT_REPORTED', 'from': None, 'to': None}, 'splits': None, 'split_basis': basis}),
            ('from_history_not_available', {'split_coverage': {'status': 'NOT_AVAILABLE', 'from': None, 'to': None}, 'splits': None,
                                            'split_basis': {'price': 'UNADJUSTED', 'volume': 'UNADJUSTED', 'source': 'PROVIDER_DOCUMENTATION'}}),
            ('from_history_invalid', {'split_coverage': {'status': 'INVALID', 'from': None, 'to': None}, 'splits': None, 'split_basis': basis}),
            ('from_history_confirmed_none', {'split_coverage': {'status': 'CONFIRMED', 'from': block_days[0], 'to': block_days[-1]}, 'splits': [], 'split_basis': basis}),
            ('from_history_confirmed_split', {'split_coverage': {'status': 'CONFIRMED', 'from': block_days[0], 'to': block_days[-1]},
                                              'splits': [{'date': block_days[3], 'numerator': 4, 'denominator': 1}], 'split_basis': basis}),
            ('from_history_confirmed_bad_date', {'split_coverage': {'status': 'CONFIRMED', 'from': block_days[0], 'to': block_days[-1]},
                                                 'splits': [{'date': '2030-02-30', 'numerator': 4, 'denominator': 1}], 'split_basis': basis})):
        cases.append({'id': cid, 'operation': 'actions_from_history', 'input': {'history': {**plain, **block}}})
    # Worker block -> continuity for an analysis window: confirmation applies only where the window lies inside split_coverage.
    def confirmed(frm, to, splits=()):
        return {'split_coverage': {'status': 'CONFIRMED', 'from': frm, 'to': to},
                'splits': [{'date': d, 'numerator': 2, 'denominator': 1} for d in splits], 'split_basis': basis}
    for cid, block, start, end in (
            ('history_window_inside_coverage', confirmed(block_days[0], block_days[-1]), block_days[0], block_days[-1]),
            ('history_window_starts_before_coverage', confirmed(block_days[2], block_days[-1]), block_days[0], block_days[-1]),
            ('history_window_ends_after_coverage', confirmed(block_days[0], block_days[3]), block_days[0], block_days[-1]),
            ('history_window_outside_coverage_adjusted_split', confirmed(block_days[0], block_days[3], [block_days[2]]), block_days[0], block_days[-1]),
            ('history_window_not_reported', {'split_coverage': {'status': 'NOT_REPORTED', 'from': None, 'to': None}, 'splits': None, 'split_basis': basis},
             block_days[0], block_days[-1])):
        cases.append({'id': cid, 'operation': 'history_window_continuity', 'input': {'history': {**plain, **block}, 'start': start, 'end': end}})
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
    if op == 'actions_from_history':
        return CB.corporate_actions(CB.actions_from_history(i['history']))
    if op == 'history_window_continuity':
        return CB.continuity(CB.actions_from_history(i['history']), i['start'], i['end'])
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
    cases.append({'id': 'pivots_split_adjusted_one_segment', 'operation': 'pivots',
                  'input': {'history': history(zz), 'timeframe': 'D', 'actions': {**split, 'price_basis': 'SPLIT_ADJUSTED', 'volume_basis': 'UNKNOWN'}}})
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


# ---------------------------------------------------------------- pattern run cases (TA_PREP §6) and history cases (P1-6)

SIGNAL_FIXTURE = FIXTURES / 'pattern_signals_reference_v1.json'
MISSING = {'open': None, 'high': None, 'low': None, 'close': None}
B1_TAIL = [(3, 6), (1, 3), (1, 4), (10, 0)]       # 40-42 up to 106, 43: 109, 44: 113 (> U + 0.25 ATR), then flat
D1_TAIL = [(3, 6), (1, 3), (1, 4), (6, 0)]        # 35-37 up to 106, 38: 109, 39: 113 (> H + 0.25 ATR)


def box_level(raw, index=42):
    """U + 0.25 x ATR at the formation bar: the exact B2 boundary value."""
    ctx = P.prepare(CB.normalize(history(raw)), P.load_rules(), ALL_SPLIT_FREE)
    return 110.5 + P.param(ctx['rules'], 'BREAK_BUFFER_ATR') * ctx['atr'][index]


def split_at(raw, index):
    return {'status': 'AVAILABLE', 'covered_from': '2030-01-01', 'covered_to': '2031-12-31',
            'events': [{'kind': 'SPLIT', 'effective_date': raw[index]['day']}]}


def scenarios():
    """(id, raw daily bars, timeframe, corporate actions). Every bar is invented."""
    b1 = scenario(B1_TAIL)
    level = box_level(b1)
    b3 = scenario(B1_TAIL, edit={44: {'session_status': 'IN_PROGRESS'}})[:45]
    b9_edit = {i: {'open': 105, 'close': 105, 'high': 118, 'low': 92} for i in (43, 44, 45)}
    b9_edit[46] = {'open': 105, 'close': level + 0.01, 'high': level + 0.5, 'low': 104}
    b12a = scenario([(5, 3)], base=[(20, 6), (20, -12), (20, 12), (20, -12)], start=104, edit={63: MISSING})
    b13 = scenario([(3, 6), (10, 0)])
    out = [
        ('B1_box_breakout_confirmed', b1, 'D', ALL_SPLIT_FREE),
        ('B2_close_equal_to_level_is_not_confirmed', scenario([(3, 6), (1, 3), (1, 4), (2, -6), (10, 0)], edit={44: {'close': level, 'high': level + 0.5}}), 'D', ALL_SPLIT_FREE),
        ('B3_provisional_bar_only', b3, 'D', ALL_SPLIT_FREE),
        ('B4_failed_within_fail_window', scenario([(3, 6), (1, 3), (1, 4), (2, -5), (6, 0)]), 'D', ALL_SPLIT_FREE),
        ('B5_return_after_fail_window', scenario([(3, 6), (1, 3), (1, 4), (5, 0), (1, -5), (4, 0)]), 'D', ALL_SPLIT_FREE),
        ('B6_breakdown_first_invalidates_breakout', scenario([(3, 3), (2, -8), (6, 0)]), 'D', ALL_SPLIT_FREE),
        ('B7_expired_at_box_max_bars', scenario([(5, 10), (5, -10)] * 11 + [(3, 3)]), 'D', ALL_SPLIT_FREE),
        ('B8_1_length_below_min', scenario([], base=[(3, 5), (3, -10), (3, 10), (3, -10), (4, 3)]), 'D', ALL_SPLIT_FREE),
        ('B8_1b_length_at_min_forms', scenario([], base=[(3, 5), (3, -10), (3, 10), (3, -10), (5, 3)]), 'D', ALL_SPLIT_FREE),
        ('B8_2_one_upper_touch', scenario([(3, 3)], base=[(5, 5), (5, -10), (5, 7), (5, -7)]), 'D', ALL_SPLIT_FREE),
        ('B8_3_one_lower_touch', scenario([(3, 3)], base=[(5, 5), (5, -10), (5, 10), (5, -7)]), 'D', ALL_SPLIT_FREE),
        ('B8_4_close_outside_box', scenario([(2, 8), (1, 6), (3, 0)]), 'D', ALL_SPLIT_FREE),
        ('B8_5_too_shallow', scenario([(3, 1)], base=[(5, 1), (5, -2), (5, 2), (5, -2)], spread=1.0), 'D', ALL_SPLIT_FREE),
        ('B8_5b_too_deep', scenario([(3, 3)], base=[(15, 15), (15, -30), (15, 30), (15, -30)], spread=0.05), 'D', ALL_SPLIT_FREE),
        ('B9_levels_fixed_when_atr_changes', scenario(B1_TAIL, edit=b9_edit), 'D', ALL_SPLIT_FREE),
        ('B10_gap_breakout', scenario(B1_TAIL, edit={44: {'open': 112, 'low': 111.5}}), 'D', ALL_SPLIT_FREE),
        ('B11_confirm_bar_volume_missing', scenario(B1_TAIL, edit={44: {'volume': None}}), 'D', ALL_SPLIT_FREE),
        ('B12_missing_bar_in_box_window', b12a, 'D', ALL_SPLIT_FREE),
        ('B12b_missing_bar_while_formed', scenario([(3, 6), (10, 0)], edit={43: MISSING}), 'D', ALL_SPLIT_FREE),
        ('B13_split_crosses_live_window', b13, 'D', split_at(b13, 45)),
        ('B13b_split_lookup_failed', b1, 'D', {'status': 'LOOKUP_FAILED'}),
        ('B13c_no_split_events', b1, 'D', None),
        ('B13d_split_adjusted_prices_stay_judgeable', b13, 'D', {**split_at(b13, 45), 'price_basis': 'SPLIT_ADJUSTED', 'volume_basis': 'UNKNOWN'}),
        ('B13e_split_unadjusted_prices', b13, 'D', {**split_at(b13, 45), 'price_basis': 'UNADJUSTED', 'volume_basis': 'UNADJUSTED'}),
        ('B13f_split_not_reported', b1, 'D', {'status': 'NOT_REPORTED'}),
        ('B13g_split_adjusted_volume_basis_unconfirmed', b1, 'D', {**split_at(b1, 40), 'price_basis': 'SPLIT_ADJUSTED', 'volume_basis': 'UNKNOWN'}),
        ('B13h_split_adjusted_price_and_volume', b1, 'D', {**split_at(b1, 40), 'price_basis': 'SPLIT_ADJUSTED', 'volume_basis': 'SPLIT_ADJUSTED'}),
        ('B1_mirror_breakdown', mirror(b1), 'D', ALL_SPLIT_FREE),
        ('B4_mirror_breakdown_failed', mirror(scenario([(3, 6), (1, 3), (1, 4), (2, -5), (6, 0)])), 'D', ALL_SPLIT_FREE),
        ('D1_double_bottom_confirmed', scenario(D1_TAIL, base=DB_BASE), 'D', ALL_SPLIT_FREE),
        ('D2_double_bottom_failed', scenario([(3, 6), (1, 3), (1, 4), (1, -3), (1, -3), (6, 0)], base=DB_BASE), 'D', ALL_SPLIT_FREE),
        ('D3_double_bottom_invalidated', scenario([(3, 6), (1, -3), (1, -6), (5, 0)], base=DB_BASE), 'D', ALL_SPLIT_FREE),
        ('D4_double_bottom_expired', scenario([(3, 6), (14, 0)], base=DB_BASE), 'D', ALL_SPLIT_FREE),
        ('D5_neckline_passed_before_known', scenario([(1, 4), (1, 8), (1, 2), (5, 0)], base=DB_BASE), 'D', ALL_SPLIT_FREE),
        ('D6_nearest_p1_only', scenario([(3, 6), (6, 0)], base=DB_BASE + [(5, 10), (5, -10)]), 'D', ALL_SPLIT_FREE),
        ('D7_separation_min_minus_one', scenario([(3, 6), (6, 0)], base=[(5, -5), (4, 10), (5, -10)]), 'D', ALL_SPLIT_FREE),
        ('D7b_separation_max_plus_one', scenario([(3, 6), (6, 0)], base=[(5, -5), (60, 60), (61, -60)]), 'D', ALL_SPLIT_FREE),
        ('D7c_separation_max_forms', scenario([(3, 6), (6, 0)], base=[(5, -5), (60, 60), (60, -60)]), 'D', ALL_SPLIT_FREE),
        ('D1_mirror_double_top', mirror(scenario(D1_TAIL, base=DB_BASE)), 'D', ALL_SPLIT_FREE),
        ('P6_weekly_patterns', scenario([(15, 6), (5, 3), (5, 4), (30, 0)], base=[(25, 5), (25, -10), (25, 10), (25, -10)], warmup=100), 'W', ALL_SPLIT_FREE),
        ('random_walk_3', random_walk(3, 200), 'D', ALL_SPLIT_FREE),
    ]
    return out


def run_raw(raw, timeframe, actions, rules=None):
    daily = CB.normalize(history(raw))
    return P.run(daily if timeframe == 'D' else CB.weekly(daily, actions), rules or P.load_rules(), actions)


def signal_cases():
    cases = [{'id': cid, 'operation': 'run', 'input': {'history': history(raw), 'timeframe': tf, 'actions': actions}}
             for cid, raw, tf, actions in scenarios()]
    b1 = dict((c[0], c[1]) for c in scenarios())['B1_box_breakout_confirmed']
    b3 = dict((c[0], c[1]) for c in scenarios())['B3_provisional_bar_only']
    cases.append({'id': 'B3_preview_note', 'operation': 'preview', 'input': {'history': history(b3), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE}})
    revised = [dict(b) for b in b1]
    revised[44].update(close=110.8, high=111.3)          # the provider later revises the breakout bar below the level
    cases.append({'id': 'P4_P5_history', 'operation': 'history', 'input': {
        'history': history(b1), 'timeframe': 'D', 'actions': ALL_SPLIT_FREE,
        'revised_incoming': history(revised[40:], read_at='2031-01-02T23:00:00Z'),
        'not_judgeable_history': history(b1)}})
    for case in cases:
        case['synthetic'] = True
    return cases


def run_signal_case(case):
    i, op = case['input'], case['operation']
    if op == 'run':
        return run_raw_history(i['history'], i['timeframe'], i['actions'])
    if op == 'preview':
        s = CB.normalize(i['history'])
        return P.preview(s, P.run(s, P.load_rules(), i['actions']))
    if op == 'history':
        return history_steps(i)
    raise ValueError(op)


def run_raw_history(h, timeframe, actions, rules=None):
    daily = CB.normalize(h)
    return P.run(daily if timeframe == 'D' else CB.weekly(daily, actions), rules or P.load_rules(), actions)


def history_steps(i):
    """P4 repeat / prefix order, user-settings and version refusal, NOT_JUDGEABLE withholding, P5 DATA_REVISION."""
    from investment_system.technical import pattern_history as H
    rules = P.load_rules()
    daily = CB.normalize(i['history'])
    full = P.run(daily, rules, i['actions'])
    log = []
    hist = H.PatternHistory(full['symbol'], full['timeframe'], full['rule_version'], full['params_sha256'])
    for n in (30, 43, 44, 45, len(daily['bars'])):
        part = {**i['history'], 'bars': i['history']['bars'][:n]}
        log.append(['prefix', n, hist.append(P.run(CB.normalize(part), rules, i['actions']), 'T%03d' % n)])
    log.append(['repeat', hist.append(full, 'T999')])
    for label, run_ in (('user_settings', P.run(daily, rules_with(SWING_MIN_ATR=2), i['actions'])),):
        try:
            hist.append(run_, 'TX')
            log.append([label, 'ACCEPTED'])
        except H.PatternHistoryError as error:
            log.append([label, str(error)])
    other = dict(full)
    other['rule_version'] = 'pattern-rules/2'
    try:
        hist.append(other, 'TX')
        log.append(['version_mixed', 'ACCEPTED'])
    except H.PatternHistoryError as error:
        log.append(['version_mixed', str(error)])
    once = H.PatternHistory(full['symbol'], full['timeframe'], full['rule_version'], full['params_sha256'])
    log.append(['full_once', once.append(full, 'T999')])
    same = [{k: v for k, v in r.items() if k not in ('seq', 'computed_at')} for r in once.records()] == \
           [{k: v for k, v in r.items() if k not in ('seq', 'computed_at')} for r in hist.records()]
    log.append(['prefix_order_equals_full_once', same])
    na = H.PatternHistory(full['symbol'], full['timeframe'], full['rule_version'], full['params_sha256'])
    log.append(['no_split_events', na.append(P.run(CB.normalize(i['not_judgeable_history']), rules, None), 'T999'), len(na.records())])
    partial = H.PatternHistory(full['symbol'], full['timeframe'], full['rule_version'], full['params_sha256'])
    partial.append({**full, 'transitions': [t for t in full['transitions'] if t.get('pattern') != 'BOX_BREAKOUT_UP']}, 'T999')
    log.append(['late_object', partial.append(full, 'T1000')])
    incoming = CB.normalize(i['revised_incoming'])
    held = CB.merge(daily, incoming)
    view = CB.merge(daily, incoming, prefer='INCOMING')
    official, revised = P.run(held['series'], rules, i['actions']), P.run(view['series'], rules, i['actions'])
    log.append(['revised_dates', held['revised']])
    log.append(['revision', hist.record_revision(official, revised, held['revised'], incoming['bars'][-1]['session_date'], 'T1000')])
    log.append(['after_revision_append', hist.append(official, 'T1001')])
    return {'log': log, 'records': hist.records()}


# ---------------------------------------------------------------- fixtures and device config copy

def _build(cases, runner, title):
    return {'schema': 'reference-vectors/1', 'title': title, 'synthetic': True,
            'cases': [{**c, 'expected_json': json.dumps(runner(c), ensure_ascii=False, sort_keys=True)} for c in cases]}


def build_chart():
    return _build(chart_cases(), run_chart_case, 'ChartBars synthetic reference vectors')


def build_engine():
    return _build(engine_cases(), run_engine_case, 'PatternEngine synthetic reference vectors')


def build_signals():
    return _build(signal_cases(), run_signal_case, 'PatternEngine/PatternHistory synthetic signal vectors (TA_PREP §6)')


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
    for target, value in ((CHART_FIXTURE, build_chart()), (ENGINE_FIXTURE, build_engine()), (SIGNAL_FIXTURE, build_signals())):
        compact = target == SIGNAL_FIXTURE   # large synthetic inputs: one case per line keeps the file reviewable and small
        text = ('{"schema":%s,"title":%s,"synthetic":true,"cases":[\n' % (json.dumps(value['schema']), json.dumps(value['title'], ensure_ascii=False))
                + ',\n'.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) for c in value['cases']) + '\n]}'
                if compact else json.dumps(value, ensure_ascii=False, indent=1))
        target.write_text(text + '\n', encoding='utf-8')
    CONFIG_JS.write_text(config_js(), encoding='utf-8')
    print('PATTERN_REFERENCE_WRITTEN')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
