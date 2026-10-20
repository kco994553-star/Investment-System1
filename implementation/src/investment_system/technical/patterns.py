"""Pattern engine reference (TECHNICAL_PATTERN_CHART_V1_DESIGN §8-§9): rules, engine bars and swing pivots.

Python reference for web_assets/pattern-engine.js (vectors: tests/fixtures/pattern_engine_reference_v1.json).
Pure functions. No network, storage, QGV, rendering or clock reads. Every parameter is a research default
(`pattern-rules/1`, RESEARCH_DEFAULT) and never a validated investment rule. Outputs never carry a probability,
win rate, percentage or score.

Time rule (§8.2): every transition carries `known_at`, the session date of the complete bar at which the fact
becomes knowable. A pivot anchored at bar i needs k later bars, so known_index = i + k.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from . import chart_bars as CB

RULES_PATH = Path(__file__).with_name('pattern_rules_v1.json')
ROLE = 'RESEARCH_DEFAULT'
STRUCTURE_LABELS = {'HH_HL': '고점·저점 상승', 'LH_LL': '고점·저점 하락', 'MIXED': '혼재'}


class PatternRulesError(ValueError):
    pass


# ---------------------------------------------------------------- rules and parameter hash (§8.7)

def _canonical_value(value):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PatternRulesError('PATTERN_RULES_INVALID')
        return int(value) if value.is_integer() else value
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return {k: _canonical_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonical_value(v) for v in value]
    raise PatternRulesError('PATTERN_RULES_INVALID')


def canonical_json(value):
    """Sorted keys, no spaces, ASCII, integral floats written as integers (identical to the JS canonical form)."""
    return json.dumps(_canonical_value(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def params_sha256(params):
    return hashlib.sha256(canonical_json(params).encode('ascii')).hexdigest()


def load_rules(path=RULES_PATH):
    rules = json.loads(Path(path).read_text(encoding='utf-8'))
    check_rules(rules)
    return rules


def check_rules(rules):
    if not isinstance(rules, dict) or rules.get('schema') != 'pattern-rules/1' or rules.get('status') != ROLE \
            or not isinstance(rules.get('params'), dict) or rules.get('params_sha256') != params_sha256(rules['params']):
        raise PatternRulesError('PATTERN_RULES_INVALID')
    return rules


def run_mode(rules):
    """OFFICIAL only for the shipped rules; anything else is a user-settings run that never enters the history."""
    return 'OFFICIAL' if canonical_json(rules) == canonical_json(load_rules()) else 'USER_SETTINGS'


def param(rules, name, timeframe=None):
    value = rules['params'][name]
    if isinstance(value, dict) and timeframe in value:
        return value[timeframe]
    return value


# ---------------------------------------------------------------- ATR14 (mirror of ResearchIndicators ATR_14)

def _js_mean(values):
    scale = max(abs(x) for x in values)
    if scale == 0:
        return 0
    total = 0
    for x in values:
        total = total + x / scale
    return total / len(values) * scale


def _checked(value):
    return value if isinstance(value, (int, float)) and math.isfinite(value) else None


def atr14(bars):
    """ATR14 on RAW OHLC, the exact operation order of web_assets/chart-indicators.js (ResearchIndicators ATR_14).

    The browser calls ResearchIndicators itself; this port only exists so the Python reference produces the same
    numbers. `bars` are engine bars: a missing bar has open/high/low/close None.
    """
    if len(bars) > 1500:  # ResearchIndicators input cap
        return [None] * len(bars)
    values, seed, prev = [], [], None
    for i, b in enumerate(bars):
        v = None
        close = b['close']
        if close is None or not (b['high'] is not None and b['high'] > 0) or not (b['low'] is not None and b['low'] > 0) or b['high'] < b['low']:
            seed, prev = [], None
        elif i == 0 or bars[i - 1]['close'] is None:
            seed, prev = [], None
        else:
            pc = bars[i - 1]['close']
            tr = _checked(max(b['high'] - b['low'], abs(b['high'] - pc), abs(b['low'] - pc)))
            if tr is None:
                seed, prev = [], None
            elif prev is None:
                seed.append(tr)
                if len(seed) == 14:
                    v = _checked(_js_mean(seed))
                    seed, prev = [], v
            else:
                v = _checked(prev + (tr - prev) / 14)
                prev = v
        values.append(v)
    return values


# ---------------------------------------------------------------- engine bars and segments

def engine_bars(series):
    """COMPLETE-prefix bars for detection. Trailing provisional bars are display only (§7.1) and never enter.

    A non-complete or OHLC-missing bar inside the prefix stays as a missing bar (never interpolated). Its
    known_at is the next knowable session so no fact is dated before it could be known.
    """
    timeframe = series['timeframe']
    src = series['bars']
    last = max((i for i, b in enumerate(src) if b['state'] == 'COMPLETE'), default=-1)
    out = []
    for i, b in enumerate(src[:last + 1]):
        ok = b['state'] == 'COMPLETE' and b['ohlc'] == 'PRESENT'
        if timeframe == 'D':
            day, first, final = b['session_date'], b['session_date'], b['session_date']
            known = b['session_date'] if b['state'] == 'COMPLETE' else None
        else:
            day, first, final, known = b['week_start'], b['first_session'], b['last_session'], b['known_at']
        out.append({
            'i': i, 'date': day, 'first_session': first, 'last_session': final, 'known_at': known,
            'timestamp': b['timestamp'], 'ok': ok,
            'open': b['open'] if ok else None, 'high': b['high'] if ok else None,
            'low': b['low'] if ok else None, 'close': b['close'] if ok else None,
            'volume': b['volume'] if ok and b['volume_state'] == 'REPORTED' else None,
        })
    following = None
    for bar in reversed(out):
        if bar['known_at'] is None:
            bar['known_at'] = following
        following = bar['known_at']
    return out


def segments(bars, actions):
    """Split effective dates bound every pattern window (§7.3); returns [start, end] index pairs."""
    actions = CB._actions(actions)
    cuts = []
    for d in actions['splits'] if actions['status'] == 'AVAILABLE' else []:
        at = next((b['i'] for b in bars if b['last_session'] >= d), None)
        if at is not None and at > 0 and at not in cuts:
            cuts.append(at)
    cuts.sort()
    starts = [0] + cuts
    ends = [c - 1 for c in cuts] + [len(bars) - 1]
    return [[s, e] for s, e in zip(starts, ends) if s <= e]


def prepare(series, rules, actions=None):
    check_rules(rules)
    bars = engine_bars(series)
    actions = CB._actions(actions)
    segs = segments(bars, actions) if bars else []
    atr = [None] * len(bars)
    for s, e in segs:
        atr[s:e + 1] = atr14(bars[s:e + 1])
    return {
        'symbol': series['symbol'], 'timeframe': series['timeframe'], 'rule_version': rules['rule_version'],
        'params_sha256': rules['params_sha256'], 'run_mode': run_mode(rules), 'rules': rules, 'bars': bars, 'atr': atr,
        'segments': segs, 'actions': actions,
    }


def judgement(ctx, start_index, end_index):
    bars = ctx['bars']
    return CB.continuity(ctx['actions'], bars[start_index]['first_session'], bars[end_index]['last_session'])


def object_id(ctx, kind, *anchors):
    return '|'.join([kind, ctx['symbol'], ctx['timeframe'], ctx['rule_version'], *anchors])


# ---------------------------------------------------------------- swing pivots (§9.1)

def _candidate(bars, i, k, key, sign):
    here = bars[i][key]
    before = all(sign * (here - bars[j][key]) > 0 for j in range(i - k, i))
    after = all(sign * (here - bars[j][key]) >= 0 for j in range(i + 1, i + k + 1))
    return before and after


def pivots(ctx):
    """Swing pivots with the append-only amplitude filter.

    Candidate high at i: high[i] is greater than each of the k earlier highs and at least each of the k later
    highs (ties go to the earlier bar). Lows mirror it. Known at bar i + k. A window with a missing bar is not
    judged. Against the last confirmed pivot: opposite kind needs amplitude >= SWING_MIN_ATR x ATR(i + k); the same
    kind confirms only when more extreme and then appends SUPERSEDED to the earlier one; otherwise dropped.
    When one bar is both a high and a low candidate, the kind opposite to the last confirmed pivot is evaluated
    first (HIGH first when none exists) - a deterministic tie order, not a market rule.
    """
    tf, rules = ctx['timeframe'], ctx['rules']
    k, swing = param(rules, 'PIVOT_K', tf), param(rules, 'SWING_MIN_ATR')
    bars, atr = ctx['bars'], ctx['atr']
    transitions, skipped = [], {'MISSING_BARS_IN_WINDOW': 0, 'ATR_UNAVAILABLE': 0}
    confirmed_all = []
    for s, e in ctx['segments']:
        confirmed = []
        for t in range(s, e + 1):
            i = t - k
            if i - k < s:
                continue
            window = bars[i - k:t + 1]
            if not all(b['ok'] for b in window):
                skipped['MISSING_BARS_IN_WINDOW'] += 1
                continue
            kinds = [kind for kind, key, sign in (('HIGH', 'high', 1), ('LOW', 'low', -1)) if _candidate(bars, i, k, key, sign)]
            if not kinds:
                continue
            if atr[t] is None:
                skipped['ATR_UNAVAILABLE'] += 1
                continue
            if len(kinds) == 2 and confirmed and confirmed[-1]['pivot'] == 'HIGH':
                kinds = ['LOW', 'HIGH']
            for kind in kinds:
                price = bars[i]['high' if kind == 'HIGH' else 'low']
                last = confirmed[-1] if confirmed else None
                event = None
                if last is None:
                    event = 'PIVOT_CONFIRMED'
                elif last['pivot'] != kind:
                    amplitude = price - last['price'] if kind == 'HIGH' else last['price'] - price
                    if amplitude >= swing * atr[t]:
                        event = 'PIVOT_CONFIRMED'
                elif (price > last['price']) if kind == 'HIGH' else (price < last['price']):
                    event = 'PIVOT_CONFIRMED'
                    confirmed.pop()
                    transitions.append({**_pivot_transition(ctx, last['anchor_index'], kind, last['price'], last['atr'], t, k),
                                        'event': 'SUPERSEDED', 'superseded_by': object_id(ctx, 'PIVOT', kind, bars[i]['date'])})
                if event:
                    record = _pivot_transition(ctx, i, kind, price, atr[t], t, k)
                    transitions.append(record)
                    confirmed.append({'pivot': kind, 'anchor_index': i, 'price': price, 'atr': atr[t], 'object_id': record['object_id'],
                                      'anchor_at': bars[i]['date'], 'known_index': t, 'known_at': bars[t]['known_at']})
        confirmed_all.extend(confirmed)
    return {'transitions': transitions, 'confirmed': confirmed_all, 'skipped': skipped}


def _pivot_transition(ctx, i, kind, price, atr_value, t, k):
    bars = ctx['bars']
    return {
        'object_id': object_id(ctx, 'PIVOT', kind, bars[i]['date']), 'object_kind': 'PIVOT', 'event': 'PIVOT_CONFIRMED',
        'timeframe': ctx['timeframe'], 'rule_version': ctx['rule_version'], 'params_sha256': ctx['params_sha256'],
        'anchor_index': i, 'anchor_at': bars[i]['date'], 'known_index': t, 'known_at': bars[t]['known_at'],
        'detail': {'pivot': kind, 'price': price, 'atr': atr_value},
        'judgement': judgement(ctx, i - k, t),
    }


def structure(confirmed):
    """Description from the last two pivot highs and lows. Not a regime judgement (§9.1)."""
    highs = [p['price'] for p in confirmed if p['pivot'] == 'HIGH'][-2:]
    lows = [p['price'] for p in confirmed if p['pivot'] == 'LOW'][-2:]
    if len(highs) < 2 or len(lows) < 2:
        return {'state': 'NOT_AVAILABLE', 'reason_code': 'INSUFFICIENT_PIVOTS', 'label_ko': None}
    if highs[1] > highs[0] and lows[1] > lows[0]:
        state = 'HH_HL'
    elif highs[1] < highs[0] and lows[1] < lows[0]:
        state = 'LH_LL'
    else:
        state = 'MIXED'
    return {'state': state, 'reason_code': None, 'label_ko': STRUCTURE_LABELS[state]}


def run_pivots(series, rules, actions=None):
    ctx = prepare(series, rules, actions)
    result = pivots(ctx)
    return {'role': ROLE, 'label_ko': rules['label_ko'], 'rule_version': ctx['rule_version'],
            'params_sha256': ctx['params_sha256'], 'run_mode': ctx['run_mode'], 'timeframe': ctx['timeframe'], 'segments': ctx['segments'],
            'transitions': result['transitions'], 'skipped': result['skipped'],
            'structure': structure(result['confirmed'])}
