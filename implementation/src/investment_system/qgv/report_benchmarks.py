"""S17 daily report ⑪ Track Record, ⑫ period returns and ⑬ relative-index dashboard (pure functions).

Python reference for web_assets/report-benchmarks.js (vectors: tests/fixtures/report_benchmarks_v1.json, built by
tools/report_benchmarks_reference.py). The device passes RAM-only inputs: the runner's `indices` (Worker daily closes of
SPY, XLK, VUG, QUAL, XLY, XLP and the KRW=X rate), the engine ledger days (KRW) and the engine hit evaluation. Nothing
here fetches, stores or publishes prices, rates, values or returns.

Rules (REPORT_TEMPLATE_V1 ⑪⑫⑬, VIRTUAL_TRADING_V1_PROPOSAL table ⑬, GSQ-018 D-11/D-12):
- Session calendar = SPY completed sessions. The as-of session is the target ledger's last day, else the last SPY session.
- A period of N sessions ends at the as-of session; its base is the session N sessions earlier (the close of the
  session right before the period start). SINCE_START starts at the ledger start; its base is the last session before it.
- Every series is 100 at the base. A missing close / rate / ledger value is a gap (None) with a reason code. Nothing is
  interpolated or carried forward; a missing base or as-of value makes that series' period return NOT_AVAILABLE.
- Currency basis (one basis for every series on screen):
  KRW (default) — the ledgers in KRW as recorded; each USD index converted with that session's KRW=X close
  (close × rate), i.e. what a KRW investor holding the ETF would have seen.
  USD — every USD index as its local close; each ledger converted to USD with that session's KRW=X close.
  The rate must be on the same session date; a missing rate is a gap (FX_MISSING), never the previous rate.
- Ledger index = time-weighted chain of the engine ledger: link = (value − deposits since the last valued session) /
  last valued value; no capital before the first ledger day → that day's link is 1 (engine convention). With no gap and
  the KRW basis this equals the engine summary.twr. In the USD basis each link is multiplied by rate_prev / rate_now.
- ⑪ uses the engine evaluate_hits (D+5/D+20/D+63 sessions, S&P 500, 30-sample minimum). Below 30 samples the hit rate
  is not shown. Before a window can have a sample the expected first evaluation date is given; dates beyond the known
  session calendar are estimated with weekdays minus the NYSE holidays listed below (marked as estimates).
"""
from __future__ import annotations

import datetime as dt

SCHEMA = 'report-benchmarks/1'
PERIODS = (('1D', 1), ('5D', 5), ('20D', 20), ('60D', 60), ('120D', 120), ('SINCE_START', None))
PERIOD_IDS = tuple(p for p, _ in PERIODS)
DASHBOARD = (('SP500', 'SPY'), ('XLK', 'XLK'), ('VUG', 'VUG'), ('QUAL', 'QUAL'), ('XLY', 'XLY'), ('XLP', 'XLP'))
SPY = 'SPY'
FX_SYMBOL = 'KRW=X'
BASES = ('KRW', 'USD')
# NYSE full-day holidays used only to estimate future session dates (published exchange calendar 2026–2027).
NYSE_HOLIDAYS = frozenset((
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
    '2026-11-26', '2026-12-25',
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06',
    '2027-11-25', '2027-12-24'))
HOLIDAYS_KNOWN_UNTIL = '2027-12-31'


def _num(v):
    return type(v) in (int, float) and v == v and v not in (float('inf'), float('-inf'))


def _na(reason):
    return {'state': 'NOT_AVAILABLE', 'reason': reason}


def period_window(calendar, as_of, period, start_date):
    """Base session and the sessions of one period on the SPY calendar."""
    if as_of is None or as_of not in calendar:
        return _na('SESSIONS_NOT_AVAILABLE')
    a = calendar.index(as_of)
    if period == 'SINCE_START':
        if start_date is None or start_date > as_of:
            return _na('BEFORE_START_DATE')
        before = [d for d in calendar if d < start_date]
        if not before:
            return _na('NO_SESSION_BEFORE_START')
        return {'state': 'OK', 'reason': None, 'base': before[-1], 'sessions': [d for d in calendar if start_date <= d <= as_of]}
    n = dict(PERIODS).get(period)
    if n is None:
        return _na('PERIOD_INVALID')
    if a < n:
        return _na('HISTORY_TOO_SHORT')
    return {'state': 'OK', 'reason': None, 'base': calendar[a - n], 'sessions': calendar[a - n + 1:a + 1]}


def _series(points, codes, ret, last_code):
    gaps = sum(1 for p in points if p is None)
    if ret is None:
        return {'state': 'NOT_AVAILABLE', 'reason': last_code, 'return': None, 'points': points, 'gap_codes': codes, 'gaps': gaps}
    return {'state': 'OK', 'reason': None, 'return': ret, 'points': points, 'gap_codes': codes, 'gaps': gaps}


def price_index(closes, fx, window, basis):
    """USD index closes → 100 at the base; KRW basis multiplies each close by the same-session KRW=X rate."""
    def level(d):
        c = closes.get(d)
        if not _num(c):
            return None, 'CLOSE_MISSING'
        if basis == 'KRW':
            r = fx.get(d)
            if not _num(r):
                return None, 'FX_MISSING'
            return c * r, None
        return c, None

    base, code = level(window['base'])
    if base is None:
        return {'state': 'NOT_AVAILABLE', 'reason': 'BASE_' + code, 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    points, codes = [], []
    for d in window['sessions']:
        v, c = level(d)
        points.append(None if v is None else v / base * 100)
        codes.append(c)
    last, last_code = level(window['sessions'][-1])
    return _series(points, codes, None if last is None else last / base - 1, None if last_code is None else 'LAST_' + last_code)


def ledger_index(days, calendar, window, basis, fx):
    """Engine ledger days {date, total_value (KRW or None), deposit} → time-weighted index, 100 at the base."""
    by = {d['date']: d for d in days}
    first = days[0]['date']
    before = [d for d in calendar if d < first]
    b = window['base']
    prev, prev_rate = None, None
    if b < first:
        if not before or b != before[-1]:
            return {'state': 'NOT_AVAILABLE', 'reason': 'PERIOD_BEFORE_LEDGER_START', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    else:
        day = by.get(b)
        if day is None or not _num(day.get('total_value')):
            return {'state': 'NOT_AVAILABLE', 'reason': 'BASE_VALUE_MISSING', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
        prev = day['total_value']
        if basis == 'USD':
            prev_rate = fx.get(b)
            if not _num(prev_rate):
                return {'state': 'NOT_AVAILABLE', 'reason': 'BASE_FX_MISSING', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    index, deposits, points, codes, code = 1.0, 0, [], [], None
    for d in window['sessions']:
        day = by.get(d)
        if day is None:
            points.append(None)
            codes.append('VALUE_MISSING')
            code = 'VALUE_MISSING'
            continue
        deposits += day['deposit'] if _num(day.get('deposit')) else 0
        total = day.get('total_value')
        if not _num(total):
            points.append(None)
            codes.append('VALUE_MISSING')
            code = 'VALUE_MISSING'
            continue
        rate = None
        if basis == 'USD':
            rate = fx.get(d)
            if not _num(rate):
                points.append(None)
                codes.append('FX_MISSING')
                code = 'FX_MISSING'
                continue
        if prev is not None and prev > 0:
            link = (total - deposits) / prev
            if basis == 'USD':
                link = link * prev_rate / rate
            index = index * link
        prev, prev_rate, deposits, code = total, rate, 0, None
        points.append(index * 100)
        codes.append(None)
    return _series(points, codes, None if points[-1] is None else index - 1, None if code is None else 'LAST_' + code)


def _ledger_series(entry, calendar, window, basis, fx):
    if entry.get('state') != 'OK' or not entry.get('days'):
        codes = entry.get('reason_codes') or []
        return {'state': 'NOT_AVAILABLE', 'reason': codes[0] if codes else 'LEDGER_NOT_AVAILABLE', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    if basis == 'USD' and not fx:
        return {'state': 'NOT_AVAILABLE', 'reason': 'FX_NOT_AVAILABLE', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    return ledger_index(entry['days'], calendar, window, basis, fx)


def _index_series(symbol, indices, sources, calendar, window, basis, fx):
    closes = indices.get(symbol)
    if not isinstance(closes, dict) or not closes:
        code = (sources.get(symbol) or {}).get('code')
        return {'state': 'NOT_AVAILABLE', 'reason': code or 'NOT_REQUESTED', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    if basis == 'KRW' and not fx:
        return {'state': 'NOT_AVAILABLE', 'reason': 'FX_NOT_AVAILABLE', 'return': None, 'points': [], 'gap_codes': [], 'gaps': 0}
    return price_index(closes, fx, window, basis)


def _verdict(excess):
    if excess is None:
        return None
    return 'ABOVE' if excess > 0 else 'BELOW' if excess < 0 else 'EQUAL'


def build(*, indices, sources=None, ledgers=(), start_date=None, period='20D', basis='KRW'):
    """⑫ period table and ⑬ dashboard. ledgers[0] is the report target; each entry {key, state, reason_codes, days}."""
    indices = indices if isinstance(indices, dict) else {}
    sources = sources if isinstance(sources, dict) else {}
    basis = basis if basis in BASES else 'KRW'
    period = period if period in PERIOD_IDS else '20D'
    spy = indices.get(SPY)
    calendar = sorted(spy) if isinstance(spy, dict) else []
    fx = indices.get(FX_SYMBOL) if isinstance(indices.get(FX_SYMBOL), dict) else {}
    target = ledgers[0] if ledgers else None
    target_days = target.get('days') if target and target.get('state') == 'OK' else None
    as_of = target_days[-1]['date'] if target_days else (calendar[-1] if calendar else None)
    if target_days and target_days[0].get('date'):
        start_date = target_days[0]['date']
    out = {'schema': SCHEMA, 'basis': basis, 'period': period, 'as_of': as_of, 'start_date': start_date,
           'state': 'OK', 'reason': None, 'periods': [], 'dashboard': None}
    if not calendar:
        code = (sources.get(SPY) or {}).get('code')
        out.update(state='NOT_AVAILABLE', reason=code or 'SESSIONS_NOT_AVAILABLE')
    rows = []
    for pid in PERIOD_IDS:
        w = period_window(calendar, as_of, pid, start_date) if calendar else _na(out['reason'])
        if w['state'] != 'OK':
            rows.append({'period': pid, 'state': 'NOT_AVAILABLE', 'reason': w['reason'], 'base': None, 'start': None, 'end': None,
                         'target': None, 'sp500': None, 'excess': None, 'verdict': None})
            continue
        t = _ledger_series(target, calendar, w, basis, fx) if target else _na('LEDGER_NOT_AVAILABLE')
        s = _index_series(SPY, indices, sources, calendar, w, basis, fx)
        tr, sr = t.get('return'), s.get('return')
        excess = None if tr is None or sr is None else tr - sr
        rows.append({'period': pid, 'state': 'OK', 'reason': None, 'base': w['base'], 'start': w['sessions'][0], 'end': w['sessions'][-1],
                     'target': {'state': t['state'], 'reason': t['reason'], 'return': tr},
                     'sp500': {'state': s['state'], 'reason': s['reason'], 'return': sr},
                     'excess': excess, 'verdict': _verdict(excess)})
    out['periods'] = rows
    w = period_window(calendar, as_of, period, start_date) if calendar else _na(out['reason'])
    dash = {'period': period, 'state': w['state'], 'reason': w['reason'], 'base': w.get('base'), 'sessions': w.get('sessions', []), 'series': []}
    if w['state'] == 'OK':
        for entry in ledgers:
            dash['series'].append({'key': entry['key'], 'kind': 'LEDGER', **_ledger_series(entry, calendar, w, basis, fx)})
        for key, sym in DASHBOARD:
            dash['series'].append({'key': key, 'kind': 'INDEX', **_index_series(sym, indices, sources, calendar, w, basis, fx)})
    out['dashboard'] = dash
    return out


# ---------- ⑪ Track Record ----------

def _next_weekday(d):
    x = dt.date.fromisoformat(d)
    while True:
        x += dt.timedelta(days=1)
        s = x.isoformat()
        if x.weekday() < 5 and s not in NYSE_HOLIDAYS:
            return s


def nth_session_after(known, date, k):
    """k-th session strictly after `date`: from the known calendar when it reaches, else estimated → (date, estimated)."""
    after = [s for s in known if s > date]
    if len(after) >= k:
        return after[k - 1], False
    cursor = after[-1] if after else date
    for _ in range(k - len(after)):
        cursor = _next_weekday(cursor)
    return cursor, True


def _day_before(d):
    return (dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat()


def trade_outcomes(ledger_input, trades, window):
    """Per-trade D+window result exactly as the engine evaluate_hits counts it (evaluated trades only)."""
    sessions = ledger_input['sessions']
    pos = {d: i for i, d in enumerate(sessions)}
    bench = ledger_input.get('benchmarks', {}).get('SP500')
    out = []
    for t in trades:
        i = pos.get(t['date'])
        if i is None or i + window >= len(sessions) or bench is None:
            continue
        end = sessions[i + window]
        closes = ledger_input['companies'][t['company']]['closes']
        if t['date'] not in closes or end not in closes or t['date'] not in bench or end not in bench:
            continue
        rs = closes[end] / closes[t['date']] - 1
        rb = bench[end] / bench[t['date']] - 1
        hit = (t['side'] == 'BUY' and rs > rb) or (t['side'] == 'SELL' and rs < rb)
        out.append({'date': t['date'], 'end': end, 'company': t['company'], 'side': t['side'], 'window': window,
                    'stock_return': rs, 'benchmark_return': rb, 'hit': hit})
    return out


def track_record(*, hits, trades=(), ledger_input=None, ledger_reasons=(), start_date=None, windows=(5, 20, 63), min_samples=30,
                 recent_window=5, recent_limit=5):
    """⑪ rows per hit window: samples, hit rate only from min_samples, reason and expected first evaluation date."""
    sessions = list(ledger_input['sessions']) if ledger_input else []
    rows = []
    for w in windows:
        h = next((x for x in hits or [] if x['window'] == w), None)
        if h is None:
            first, est = (None, False)
            if start_date:
                s1, e1 = nth_session_after(sessions, _day_before(start_date), 1)
                first, e2 = nth_session_after(sessions, s1, 1 + w)
                est = e1 or e2
            reasons = list(ledger_reasons or [])
            rows.append({'window': w, 'state': 'NOT_AVAILABLE', 'reason': reasons[0] if reasons else 'LEDGER_NOT_AVAILABLE',
                         'samples': None, 'hits': None, 'pending': None, 'missing': None, 'hit_rate': None,
                         'expected_first': first, 'expected_estimated': est})
            continue
        row = {'window': w, 'samples': h['samples'], 'hits': h['hits'] if h['samples'] >= min_samples else None,
               'pending': h['pending'], 'missing': h['missing'], 'hit_rate': h['hit_rate'] if h['samples'] >= min_samples else None,
               'expected_first': None, 'expected_estimated': False}
        if h['samples'] >= min_samples:
            row.update(state='OK', reason=None)
        elif h['samples'] > 0:
            row.update(state='INSUFFICIENT_SAMPLE', reason='SAMPLE_BELOW_MINIMUM')
        else:
            if not trades:
                reason = 'NO_TRADES'
                anchor = sessions[-1] if sessions else None
                k = 1 + w
            elif h['pending'] > 0:
                reason = 'WINDOW_NOT_ELAPSED'
                anchor = min(t['date'] for t in trades)
                k = w
            else:
                reason = 'PRICE_OR_BENCHMARK_MISSING'
                anchor = None
                k = 0
            row.update(state='NOT_AVAILABLE', reason=reason)
            if anchor is not None:
                row['expected_first'], row['expected_estimated'] = nth_session_after(sessions, anchor, k)
        rows.append(row)
    recent = []
    if ledger_input and trades:
        recent = sorted(trade_outcomes(ledger_input, trades, recent_window), key=lambda r: (r['date'], r['company'], r['side']), reverse=True)[:recent_limit]
    return {'schema': SCHEMA, 'benchmark': 'SP500', 'min_samples': min_samples, 'windows': rows, 'recent': recent,
            'recent_window': recent_window, 'holidays_known_until': HOLIDAYS_KNOWN_UNTIL}
