"""Virtual trading set comparison (decision 2026-10-11): rule-based metrics per set, pure functions.

Python reference for web_assets/virtual-trading-compare.js (vectors: tests/fixtures/virtual_trading_compare_v1.json,
built by tools/virtual_trading_compare_reference.py). The return series are exactly those of S17 ⑫⑬
(qgv/report_benchmarks.py): SPY session calendar, one currency basis (KRW by default: US index × same-session KRW=X),
the engine time-weighted ledger chain, every missing close / rate / value a gap (never interpolated or carried).
Standard definitions only; a metric with fewer samples than its minimum is NOT_AVAILABLE (never 0):

- period return and excess vs S&P 500: report_benchmarks ⑫ SINCE_START (from the set's own first ledger day);
- daily return r = P_i / P_{i−1} − 1 on consecutive sessions of the ⑬ index levels when both exist (the base → first
  session link is left out: no capital before the first ledger day); S&P 500 the same on its ⑬ levels;
- upside / downside capture = mean(r) / mean(b) × 100 over the S&P 500's up (b > 0) / down (b < 0) days (≥ 20 days each);
- max drawdown on the ⑬ ledger index levels (≥ 20 daily returns), ≤ 0;
- volatility = sample standard deviation of the daily returns × √252 (≥ 20 daily returns);
- concentration = top-3 holding weight (% of total value) on the last session (NA unless every holding is priced);
- type exposure = Σ weight × public membership (0–1) per type (growth, quality, cyclical, defensive); holdings without
  a public membership (ETFs included) are unclassified;
- virtual trading: buy / sell counts and the engine's D+20 hit rate (D-12 minimum 30 samples).
Float operations follow the JS order so both sides produce identical doubles.
"""
from __future__ import annotations

import math

from . import report_benchmarks as rb

SCHEMA = 'virtual-trading-compare/1'
TYPES = ('growth', 'quality', 'cyclical', 'defensive')
MIN = {'capture_days': 20, 'max_drawdown': 20, 'volatility': 20}


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def _na(reason, *, samples=None):
    row = {'state': 'NOT_AVAILABLE', 'value': None, 'reason': reason}
    return {**row, 'samples': samples} if samples is not None else row


def _ok(value, **extra):
    return {'state': 'OK', 'value': value, 'reason': None, **extra}


def compare_days(days):
    """Engine days → price-free compare days: date, total value (None = NA), deposit, held weights, fully priced flag."""
    out = []
    for d in days or []:
        weights, priced = {}, True
        for cid in sorted(d.get('judgements') or {}):
            j = d['judgements'][cid]
            if not j.get('held'):
                continue
            weights[cid] = j['actual_weight']
            codes = j.get('reason_codes') or []
            if 'DATA_PRICE_MISSING' in codes or 'DATA_FX_MISSING' in codes:
                priced = False
        out.append({'date': d['date'], 'total_value': d['total_value'] if _num(d.get('total_value')) else None,
                    'deposit': d['deposit'], 'weights': weights, 'priced': priced})
    return out


def point_returns(points):
    out = []
    for a, b in zip(points, points[1:]):
        out.append(b / a - 1 if _num(a) and _num(b) and a > 0 else None)
    return out


def _mean(xs):
    s = 0
    for x in xs:
        s += x
    return s / len(xs)


def metrics(days=(), indices=None, sources=None, basis='KRW', types=None, hits=None, summary=None):
    d = compare_days(days)
    last = d[-1] if d else None
    out = {}
    out['value'] = _ok(last['total_value'], date=last['date']) if last and _num(last['total_value']) else \
        _na('VALUATION_NOT_AVAILABLE' if last else 'LEDGER_NOT_AVAILABLE')
    report = rb.build(indices=indices or {}, sources=sources or {}, period='SINCE_START', basis=basis,
                      ledgers=[{'key': 'SET', 'state': 'OK' if d else 'NOT_AVAILABLE', 'reason_codes': [] if d else ['LEDGER_NOT_AVAILABLE'],
                                'days': [{'date': x['date'], 'total_value': x['total_value'], 'deposit': x['deposit']} for x in d]}])
    row = next((p for p in report['periods'] if p['period'] == 'SINCE_START'), None)
    if not d:
        out['period_return'], out['excess_return'] = _na('LEDGER_NOT_AVAILABLE'), _na('LEDGER_NOT_AVAILABLE')
    elif row is None or row['state'] != 'OK':
        reason = row['reason'] if row else report['reason']
        out['period_return'], out['excess_return'] = _na(reason), _na(reason)
    else:
        t, s = row['target'], row['sp500']
        out['period_return'] = _ok(t['return'], start=row['start'], end=row['end']) if t['state'] == 'OK' else _na(t['reason'])
        out['excess_return'] = _na(t['reason'] if t['state'] != 'OK' else s['reason']) if row['excess'] is None else \
            _ok(row['excess'], portfolio=t['return'], benchmark=s['return'])
    dash = report['dashboard']
    series = dash['series'] if dash and dash['state'] == 'OK' else []
    ledger = next((x for x in series if x['kind'] == 'LEDGER'), None)
    spy = next((x for x in series if x['key'] == 'SP500'), None)
    r = point_returns(ledger['points']) if ledger else []
    b = point_returns(spy['points']) if spy else []
    rets = [x for x in r if _num(x)]
    aligned = [{'r': r[i], 'b': b[i]} for i in range(len(r)) if _num(r[i]) and i < len(b) and _num(b[i])]

    def capture(rows):
        if len(rows) < MIN['capture_days']:
            return _na('INSUFFICIENT_SAMPLE', samples=len(rows))
        return _ok(_mean([x['r'] for x in rows]) / _mean([x['b'] for x in rows]) * 100, samples=len(rows))

    out['upside_capture'] = capture([x for x in aligned if x['b'] > 0])
    out['downside_capture'] = capture([x for x in aligned if x['b'] < 0])
    if len(rets) < MIN['max_drawdown']:
        out['max_drawdown'] = _na('INSUFFICIENT_SAMPLE', samples=len(rets))
    else:
        peak, mdd = None, 0
        for p in ledger['points']:
            if not _num(p):
                continue
            if peak is None or p > peak:
                peak = p
            dd = p / peak - 1
            if dd < mdd:
                mdd = dd
        out['max_drawdown'] = _ok(mdd, samples=len(rets))
    if len(rets) < MIN['volatility']:
        out['volatility'] = _na('INSUFFICIENT_SAMPLE', samples=len(rets))
    else:
        m = _mean(rets)
        v = 0
        for x in rets:
            v += (x - m) * (x - m)
        out['volatility'] = _ok(math.sqrt(v / (len(rets) - 1)) * math.sqrt(252), samples=len(rets))
    weighted = bool(last and _num(last['total_value']) and last['priced'])
    if not weighted:
        out['concentration'] = _na('WEIGHTS_NOT_AVAILABLE' if last else 'LEDGER_NOT_AVAILABLE')
    else:
        ws = sorted(last['weights'].values(), reverse=True)
        top = 0
        for x in ws[:3]:
            top += x
        out['concentration'] = _ok(top, holdings=len(ws))
    if not weighted:
        out['type_exposure'] = _na('WEIGHTS_NOT_AVAILABLE' if last else 'LEDGER_NOT_AVAILABLE')
    elif not isinstance(types, dict):
        out['type_exposure'] = _na('TYPES_NOT_AVAILABLE')
    else:
        e = {t: 0 for t in TYPES}
        unclassified = 0
        for cid in sorted(last['weights']):
            w = last['weights'][cid]
            m = types.get(cid) if isinstance(types.get(cid), dict) else None
            known = [t for t in TYPES if m is not None and _num(m.get(t))]
            if not known:
                unclassified += w
                continue
            for t in known:
                e[t] += w * m[t]
        out['type_exposure'] = _ok(e, unclassified=unclassified)
    h20 = next((h for h in hits if h['window'] == 20), None) if isinstance(hits, list) else None
    if isinstance(summary, dict):
        hit = _ok(h20['hit_rate'], samples=h20['samples']) if h20 is not None and h20['hit_rate'] is not None else _na('INSUFFICIENT_SAMPLE')
        out['virtual_trades'] = _ok({'buy': summary['buy_count'], 'sell': summary['sell_count']}, hit20=hit)
    else:
        out['virtual_trades'] = _na('LEDGER_NOT_AVAILABLE')
    return out
