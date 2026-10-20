"""Pattern engine reference (TECHNICAL_PATTERN_CHART_V1_DESIGN §8-§9): rules, engine bars, swing pivots,
support/resistance zones, box breakout/breakdown, double bottom/top and their common state machine.

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
    # Already split-adjusted provider prices are one continuous basis: a split does not cut the series (never re-adjusted).
    for d in actions['splits'] if actions['status'] == 'AVAILABLE' and actions.get('price_basis') != 'SPLIT_ADJUSTED' else []:
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


# ---------------------------------------------------------------- signals, zones and the common state machine (P1-3..P1-5)
#
# Per bar t of a segment the run applies, in this fixed order:
#   A. updates of live objects with bar t (signals: expiry, missing bar, confirmation, invalidation, failure,
#      observation end; zones: expiry, break). At the first bar of a later segment every live object becomes
#      NOT_JUDGEABLE (CORPORATE_ACTION_IN_WINDOW) instead.
#   B. pivot transitions known at t (§9.1),
#   C. support/resistance re-clustering when a pivot changed at t (§9.3),
#   D. new signal objects formed at t (box §9.4 when no box is live, double bottom/top §9.5 for a new pivot).
# A formed signal is first checked on the next bar. Thresholds use the ATR of the formation bar and never move.

PREVIEW_NOTE_KO = '잠정 봉 기준 조건 충족 · 확정 아님'


def _hit(rule, close):
    side, level = rule
    return close > level if side == 'ABOVE' else close < level


def _failed(rule, close):
    if rule[0] == 'IN_RANGE':
        return rule[1] <= close <= rule[2]
    return _hit(rule, close)


def _avg(values):
    total = 0
    for v in values:
        total = total + v
    return total / len(values)


def _volume_note(ctx, seg_start, t):
    """Reference display only (§9.6): never blocks a confirmation, never a score."""
    n, mult, bars = param(ctx['rules'], 'VOL_AVG_N', ctx['timeframe']), param(ctx['rules'], 'VOL_MULT'), ctx['bars']
    if bars[t]['volume'] is None:
        return {'state': 'NOT_AVAILABLE', 'reason_code': 'VOLUME_MISSING'}
    if t - n < seg_start:
        return {'state': 'NOT_AVAILABLE', 'reason_code': 'INSUFFICIENT_BARS'}
    # Adjusted prices with an unconfirmed volume basis: a split inside the average window mixes share-count bases.
    acts = ctx['actions']
    if CB.price_adjusted(acts) and not CB.volume_adjusted(acts) \
            and any(bars[t - n]['first_session'] < d <= bars[t]['last_session'] for d in acts['splits']):
        return {'state': 'NOT_AVAILABLE', 'reason_code': 'VOLUME_BASIS_UNCONFIRMED'}
    previous = [bars[j]['volume'] for j in range(t - n, t)]
    if any(v is None for v in previous):
        return {'state': 'NOT_AVAILABLE', 'reason_code': 'VOLUME_MISSING'}
    return {'state': 'WITH_VOLUME' if bars[t]['volume'] >= mult * _avg(previous) else 'WITHOUT_VOLUME', 'reason_code': None}


class _Run:
    def __init__(self, ctx):
        self.ctx, self.out, self.seen = ctx, [], set()
        self.fail_window = param(ctx['rules'], 'FAIL_WINDOW', ctx['timeframe'])

    def emit(self, obj, event, t, state, detail):
        bars = self.ctx['bars']
        self.out.append({
            'object_id': obj['object_id'], 'object_kind': obj['object_kind'], 'pattern': obj['pattern'], 'event': event, 'state': state,
            'timeframe': self.ctx['timeframe'], 'rule_version': self.ctx['rule_version'], 'params_sha256': self.ctx['params_sha256'],
            'anchor_index': obj['start'], 'anchor_at': bars[obj['start']]['date'], 'known_index': t, 'known_at': bars[t]['known_at'],
            'detail': detail, 'judgement': judgement(self.ctx, obj['start'], t),
        })

    # -- signals
    def signal(self, pattern, oid, start, t, confirm, invalidation, fail, expire_after, atr_value, detail):
        obj = {'object_id': oid, 'object_kind': 'SIGNAL', 'pattern': pattern, 'start': start, 'state': 'FORMED', 'confirm': confirm,
               'invalidation': invalidation, 'fail': fail, 'expire_after': expire_after, 'confirmed_index': None}
        self.seen.add(oid)
        self.emit(obj, 'FORMED', t, 'FORMED', {**detail, 'confirm_level': confirm[1], 'invalidation_level': invalidation[1],
                                              'atr': atr_value, 'atr_at': self.ctx['bars'][t]['date'], 'expire_after_index': expire_after})
        return obj

    def step_signal(self, obj, t, seg_start):
        bar = self.ctx['bars'][t]
        if obj['state'] == 'FORMED':
            if t > obj['expire_after']:
                return self.end(obj, 'EXPIRED', t, 'EXPIRED', {})
            if not bar['ok']:
                return self.end(obj, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {'reason_codes': ['MISSING_BARS_IN_WINDOW']})
            if _hit(obj['confirm'], bar['close']):
                obj['state'], obj['confirmed_index'] = 'CONFIRMED', t
                gap = _hit(obj['confirm'], bar['open'])
                return self.emit(obj, 'CONFIRMED', t, 'CONFIRMED', {'gap': gap, 'volume': _volume_note(self.ctx, seg_start, t)})
            if _hit(obj['invalidation'], bar['close']):
                return self.end(obj, 'INVALIDATED', t, 'INVALIDATED', {})
        elif obj['state'] == 'CONFIRMED':
            if not bar['ok']:
                return self.end(obj, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {'reason_codes': ['MISSING_BARS_IN_WINDOW']})
            if _failed(obj['fail'], bar['close']):
                return self.end(obj, 'FAILED', t, 'FAILED', {})
            if t - obj['confirmed_index'] >= self.fail_window:
                obj['ended'] = True
                return self.emit(obj, 'OBSERVATION_ENDED', t, 'CONFIRMED', {})

    def end(self, obj, event, t, state, detail):
        obj['state'] = state
        self.emit(obj, event, t, state, detail)

    @staticmethod
    def live(obj):
        if obj['object_kind'] == 'ZONE':
            return obj['state'] == 'ACTIVE'
        return obj['state'] == 'FORMED' or (obj['state'] == 'CONFIRMED' and not obj.get('ended'))


def _clusters(items, tol):
    """Single linkage on sorted prices; a cluster wider than 2 x tol is split at its largest gap (first one on ties)."""
    groups, current = [], []
    for item in items:
        if current and item['price'] - current[-1]['price'] > tol:
            groups.append(current)
            current = []
        current.append(item)
    if current:
        groups.append(current)
    out = []
    while groups:
        g = groups.pop(0)
        if len(g) > 1 and g[-1]['price'] - g[0]['price'] > 2 * tol:
            gaps = [g[n + 1]['price'] - g[n]['price'] for n in range(len(g) - 1)]
            cut = gaps.index(max(gaps)) + 1
            groups[0:0] = [g[:cut], g[cut:]]
        else:
            out.append(g)
    return out


def run(series, rules, actions=None):
    """Full pattern run: pivots, support/resistance zones, box breakout/breakdown, double bottom/top (§9.1-§9.5)."""
    ctx = prepare(series, rules, actions)
    piv = pivots(ctx)
    by_bar = {}
    for tr in piv['transitions']:
        by_bar.setdefault(tr['known_index'], []).append(tr)
    r = _Run(ctx)
    tf, bars, atr = ctx['timeframe'], ctx['bars'], ctx['atr']
    p = lambda name: param(rules, name, tf)  # noqa: E731
    buffer_atr, tol_atr = p('BREAK_BUFFER_ATR'), p('ZONE_TOL_ATR')
    skipped = dict(piv['skipped'])
    prior_live = []
    for n, (s, e) in enumerate(ctx['segments']):
        signals, zones, confirmed, live_box = [], [], [], None
        if n > 0:
            for obj in prior_live:
                r.end(obj, 'NOT_JUDGEABLE', s, 'NOT_JUDGEABLE', {'reason_codes': ['CORPORATE_ACTION_IN_WINDOW']})
        for t in range(s, e + 1):
            bar = bars[t]
            # A. live objects
            for obj in signals:
                if r.live(obj):
                    r.step_signal(obj, t, s)
            for z in zones:
                if z['state'] != 'ACTIVE' or z['formed_index'] >= t:
                    continue
                if t - z['last_touch'] + 1 > p('ZONE_LOOKBACK'):
                    r.end(z, 'EXPIRED', t, 'EXPIRED', {})
                elif bar['ok'] and z['side'] != 'ABOVE' and bar['close'] > z['high'] + buffer_atr * z['atr']:
                    r.end(z, 'BROKEN', t, 'BROKEN', {'direction': 'UP'})
                elif bar['ok'] and z['side'] != 'BELOW' and bar['close'] < z['low'] - buffer_atr * z['atr']:
                    r.end(z, 'BROKEN', t, 'BROKEN', {'direction': 'DOWN'})
            if live_box is not None and not any(r.live(o) for o in live_box):
                live_box = None
            # B. pivots known at t
            events = by_bar.get(t, [])
            new_pivots = []
            for tr in events:
                r.out.append(tr)
                if tr['event'] == 'SUPERSEDED':
                    confirmed = [c for c in confirmed if c['object_id'] != tr['object_id']]
                else:
                    item = {'object_id': tr['object_id'], 'pivot': tr['detail']['pivot'], 'anchor_index': tr['anchor_index'],
                            'price': tr['detail']['price'], 'anchor_at': tr['anchor_at']}
                    confirmed.append(item)
                    new_pivots.append(item)
            # C. zones
            if events and atr[t] is not None:
                _recluster(r, ctx, zones, confirmed, t, s, p, tol_atr)
            # D. formation
            if atr[t] is None:
                continue
            if live_box is None:
                live_box = _form_box(r, ctx, confirmed, t, s, p, buffer_atr, tol_atr)
                if live_box:
                    signals.extend(live_box)
            for item in new_pivots:
                obj = _form_double(r, ctx, confirmed, item, t, s, p, buffer_atr)
                if obj:
                    signals.append(obj)
        prior_live = [o for o in signals + zones if r.live(o)]
    objects = {}
    for tr in r.out:
        objects[tr['object_id']] = {'object_id': tr['object_id'], 'object_kind': tr['object_kind'], 'pattern': tr.get('pattern'),
                                    'state': tr['state'] if tr['object_kind'] != 'PIVOT' else ('CONFIRMED' if tr['event'] == 'PIVOT_CONFIRMED' else 'SUPERSEDED'),
                                    'last_event': tr['event'], 'last_known_at': tr['known_at'],
                                    'judgement': tr['judgement']}
    return {'role': ROLE, 'label_ko': rules['label_ko'], 'rule_version': ctx['rule_version'], 'params_sha256': ctx['params_sha256'],
            'run_mode': ctx['run_mode'], 'symbol': ctx['symbol'], 'timeframe': tf, 'segments': ctx['segments'],
            'transitions': r.out, 'skipped': skipped, 'structure': structure(piv['confirmed']),
            'objects': [objects[k] for k in sorted(objects)]}


def _recluster(r, ctx, zones, confirmed, t, s, p, tol_atr):
    tol = tol_atr * ctx['atr'][t]
    lookback = p('ZONE_LOOKBACK')
    members = sorted((c for c in confirmed if c['anchor_index'] >= max(s, t - lookback + 1)), key=lambda c: (c['price'], c['anchor_index']))
    fresh = []
    for g in _clusters(members, tol):
        if len(g) < p('ZONE_MIN_TOUCHES'):
            continue
        anchors = sorted(c['anchor_index'] for c in g)
        oid = object_id(ctx, 'ZONE', ','.join(ctx['bars'][a]['date'] for a in anchors))
        kinds = {c['pivot'] for c in g}
        fresh.append((oid, g, anchors, 'MIXED' if len(kinds) > 1 else ('RESISTANCE' if kinds == {'HIGH'} else 'SUPPORT')))
    ids = {f[0] for f in fresh}
    for z in zones:
        if z['state'] == 'ACTIVE' and z['object_id'] not in ids:
            r.end(z, 'SUPERSEDED', t, 'SUPERSEDED', {})
    for oid, g, anchors, role in fresh:
        if oid in r.seen:
            continue
        r.seen.add(oid)
        z = {'object_id': oid, 'object_kind': 'ZONE', 'pattern': 'SUPPORT_RESISTANCE_ZONE', 'start': anchors[0], 'state': 'ACTIVE',
             'low': g[0]['price'], 'high': g[-1]['price'], 'atr': ctx['atr'][t], 'formed_index': t, 'last_touch': anchors[-1]}
        close = ctx['bars'][t]['close']
        z['side'] = 'ABOVE' if close > z['high'] else 'BELOW' if close < z['low'] else 'INSIDE'
        zones.append(z)
        r.emit(z, 'ACTIVE', t, 'ACTIVE', {'low': z['low'], 'high': z['high'], 'touches': len(g), 'role': role, 'close_side': z['side'],
                                         'role_mixed': role == 'MIXED', 'atr': z['atr'], 'atr_at': ctx['bars'][t]['date'],
                                         'anchors': [ctx['bars'][a]['date'] for a in anchors]})


def _na_candidate(r, ctx, pattern, oid, start, t):
    if oid in r.seen:
        return
    r.seen.add(oid)
    obj = {'object_id': oid, 'object_kind': 'SIGNAL', 'pattern': pattern, 'start': start}
    r.emit(obj, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {'reason_codes': ['MISSING_BARS_IN_WINDOW']})


def _form_box(r, ctx, confirmed, t, s, p, buffer_atr, tol_atr):
    bars, atr = ctx['bars'], ctx['atr'][t]
    tol, lo_len, hi_len = tol_atr * atr, p('BOX_MIN_BARS'), p('BOX_MAX_BARS')
    height_min, height_max = p('BOX_HEIGHT_ATR')['min'], p('BOX_HEIGHT_ATR')['max']
    pool = [c for c in confirmed if c['anchor_index'] >= max(s, t - hi_len + 1)]
    for start in sorted({c['anchor_index'] for c in pool}):
        if not lo_len <= t - start + 1 <= hi_len:
            continue
        inside = [c for c in pool if c['anchor_index'] >= start]
        highs = [c for c in inside if c['pivot'] == 'HIGH']
        lows = [c for c in inside if c['pivot'] == 'LOW']
        if not highs or not lows:
            continue
        upper_price, lower_price = max(c['price'] for c in highs), min(c['price'] for c in lows)
        upper = [c for c in highs if c['price'] >= upper_price - tol]
        lower = [c for c in lows if c['price'] <= lower_price + tol]
        if len(upper) < 2 or len(lower) < 2 or not any(c['anchor_index'] == start for c in upper + lower):
            continue
        window = bars[start:t + 1]
        if any(b['ok'] and not lower_price <= b['close'] <= upper_price for b in window):
            continue
        if not height_min * atr <= upper_price - lower_price <= height_max * atr:
            continue
        anchors = ','.join(bars[a]['date'] for a in sorted(c['anchor_index'] for c in upper + lower))
        if not all(b['ok'] for b in window):
            _na_candidate(r, ctx, 'BOX', object_id(ctx, 'BOX', anchors), start, t)
            continue
        box_id = object_id(ctx, 'BOX', anchors)
        if box_id in r.seen:
            continue
        r.seen.add(box_id)
        buf = buffer_atr * atr
        detail = {'box_id': box_id, 'upper': upper_price, 'lower': lower_price, 'upper_touches': len(upper), 'lower_touches': len(lower),
                  'anchors': anchors.split(',')}
        expire = start + hi_len - 1
        up = r.signal('BOX_BREAKOUT_UP', object_id(ctx, 'BOX_BREAKOUT_UP', anchors), start, t, ('ABOVE', upper_price + buf),
                      ('BELOW', lower_price - buf), ('IN_RANGE', lower_price, upper_price), expire, atr, detail)
        down = r.signal('BOX_BREAKDOWN', object_id(ctx, 'BOX_BREAKDOWN', anchors), start, t, ('BELOW', lower_price - buf),
                        ('ABOVE', upper_price + buf), ('IN_RANGE', lower_price, upper_price), expire, atr, detail)
        return [up, down]
    return None


def _form_double(r, ctx, confirmed, p2, t, s, p, buffer_atr):
    bars, atr = ctx['bars'], ctx['atr'][t]
    bottom = p2['pivot'] == 'LOW'
    pattern = 'DOUBLE_BOTTOM' if bottom else 'DOUBLE_TOP'
    sep_min, sep_max, buf = p('DB_SEP_MIN'), p('DB_SEP_MAX'), buffer_atr * atr
    a2 = p2['anchor_index']
    for p1 in sorted((c for c in confirmed if c['pivot'] == p2['pivot'] and c['anchor_index'] < a2), key=lambda c: -c['anchor_index']):
        a1 = p1['anchor_index']
        sep = a2 - a1
        if sep < sep_min:
            continue
        if sep > sep_max:
            break
        if abs(p2['price'] - p1['price']) > p('DB_TOL_ATR') * atr:
            continue
        between = [c['price'] for c in confirmed if c['pivot'] != p2['pivot'] and a1 < c['anchor_index'] < a2]
        if not between:
            continue
        if bottom:
            neck, edge = max(between), min(p1['price'], p2['price'])
            depth = neck - max(p1['price'], p2['price'])
        else:
            neck, edge = min(between), max(p1['price'], p2['price'])
            depth = min(p1['price'], p2['price']) - neck
        if depth < p('DB_DEPTH_ATR') * atr:
            continue
        if any(b['ok'] and (b['close'] < edge if bottom else b['close'] > edge) for b in bars[a1:a2 + 1]):
            continue
        level = neck + buf if bottom else neck - buf
        if any(b['ok'] and (b['close'] > level if bottom else b['close'] < level) for b in bars[a2 + 1:t + 1]):
            continue
        oid = object_id(ctx, pattern, bars[a1]['date'], bars[a2]['date'])
        if not all(b['ok'] for b in bars[a1:t + 1]):
            _na_candidate(r, ctx, pattern, oid, a1, t)
            return None
        if oid in r.seen:
            return None
        detail = {'p1': p1['price'], 'p2': p2['price'], 'neckline': neck, 'p1_at': bars[a1]['date'], 'p2_at': bars[a2]['date'], 'separation_bars': sep}
        if bottom:
            return r.signal(pattern, oid, a1, t, ('ABOVE', level), ('BELOW', edge - buf), ('BELOW', neck), t + sep, atr, detail)
        return r.signal(pattern, oid, a1, t, ('BELOW', level), ('ABOVE', edge + buf), ('ABOVE', neck), t + sep, atr, detail)
    return None


def preview(series, result):
    """Provisional-bar preview (§9.7): display only, never in the history, may vanish on the next refresh."""
    last = series['bars'][-1] if series['bars'] else None
    if not last or last['state'] != 'PROVISIONAL' or last['ohlc'] != 'PRESENT':
        return []
    formed = {}
    for tr in result['transitions']:
        if tr['object_kind'] == 'SIGNAL' and tr['event'] == 'FORMED':
            formed[tr['object_id']] = tr['detail']
    out = []
    for obj in result['objects']:
        if obj['object_kind'] == 'SIGNAL' and obj['state'] == 'FORMED' and obj['object_id'] in formed:
            d = formed[obj['object_id']]
            above = obj['pattern'] in ('BOX_BREAKOUT_UP', 'DOUBLE_BOTTOM')
            if (last['close'] > d['confirm_level']) if above else (last['close'] < d['confirm_level']):
                out.append({'object_id': obj['object_id'], 'note_ko': PREVIEW_NOTE_KO, 'provisional_at': last.get('session_date') or last.get('week_start')})
    return out
