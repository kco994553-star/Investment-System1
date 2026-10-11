"""Virtual trading set comparison (decision 2026-10-11): rule-based metrics per set, pure functions.

Python reference for web_assets/virtual-trading-compare.js (vectors: tests/fixtures/virtual_trading_compare_v1.json).
Standard definitions only; a metric with fewer samples than its minimum is NOT_AVAILABLE (never 0):

- daily return r_t = (V_t − deposit_t) / V_{t−1} − 1 on consecutive sessions whose values are both available
  (deposit-neutral, the engine TWR form); S&P 500 b_t = SPY_t / SPY_{t−1} − 1 on the same session pair;
- period return Π(1 + r_t) − 1 (≥ 1 return); excess vs S&P 500 Π(1 + r_t) − Π(1 + b_t) on aligned pairs (≥ 1);
- upside / downside capture = mean(r_t) / mean(b_t) × 100 over the S&P 500's up (b_t > 0) / down (b_t < 0) days
  (≥ 10 days each);
- max drawdown on the deposit-neutral daily value index W_t = Π(1 + r) (≥ 20 returns), ≤ 0;
- volatility = sample standard deviation of r_t × √252 (≥ 20 returns);
- concentration = top-3 holding weight (% of total value) on the last session (NA unless every holding is priced);
- type exposure = Σ weight × public membership (0–1) per type (growth, quality, cyclical, defensive); holdings without
  a public membership (ETFs included) are unclassified;
- virtual trading: buy / sell counts and the engine's D+20 hit rate (D-12 minimum 30 samples).
Float operations follow the JS order so both sides produce identical doubles.
"""
from __future__ import annotations

import math

SCHEMA = 'virtual-trading-compare/1'
SP500 = 'SP500'
TYPES = ('growth', 'quality', 'cyclical', 'defensive')
MIN = {'period_return': 1, 'excess_return': 1, 'capture_days': 10, 'max_drawdown': 20, 'volatility': 20}


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def _na(reason):
    return {'state': 'NOT_AVAILABLE', 'value': None, 'reason': reason}


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


def daily_returns(days):
    out = []
    for a, b in zip(days, days[1:]):
        if _num(a['total_value']) and a['total_value'] > 0 and _num(b['total_value']):
            out.append({'date': b['date'], 'prev': a['date'], 'r': (b['total_value'] - b['deposit']) / a['total_value'] - 1})
    return out


def _product(xs):
    g = 1
    for x in xs:
        g = g * (1 + x)
    return g - 1


def _mean(xs):
    s = 0
    for x in xs:
        s += x
    return s / len(xs)


def metrics(days=(), sp500=None, types=None, hits=None, summary=None):
    d = compare_days(days)
    rets = daily_returns(d)
    last = d[-1] if d else None
    out = {}
    out['value'] = _ok(last['total_value'], date=last['date']) if last and _num(last['total_value']) else \
        _na('VALUATION_NOT_AVAILABLE' if last else 'LEDGER_NOT_AVAILABLE')
    out['period_return'] = _ok(_product([x['r'] for x in rets]), samples=len(rets)) if len(rets) >= MIN['period_return'] else _na('INSUFFICIENT_SAMPLE')
    bench = sp500 if isinstance(sp500, dict) else None
    aligned = []
    if bench is not None:
        for x in rets:
            p, c = bench.get(x['prev']), bench.get(x['date'])
            if _num(p) and _num(c) and p > 0:
                aligned.append({'r': x['r'], 'b': c / p - 1})
    if bench is None:
        out['excess_return'] = _na('BENCHMARK_NOT_AVAILABLE')
    elif len(aligned) < MIN['excess_return']:
        out['excess_return'] = _na('INSUFFICIENT_SAMPLE')
    else:
        p, b = _product([x['r'] for x in aligned]), _product([x['b'] for x in aligned])
        out['excess_return'] = _ok(p - b, portfolio=p, benchmark=b, samples=len(aligned))

    def capture(rows):
        if bench is None:
            return _na('BENCHMARK_NOT_AVAILABLE')
        if len(rows) < MIN['capture_days']:
            return _na('INSUFFICIENT_SAMPLE')
        return _ok(_mean([x['r'] for x in rows]) / _mean([x['b'] for x in rows]) * 100, samples=len(rows))

    out['upside_capture'] = capture([x for x in aligned if x['b'] > 0])
    out['downside_capture'] = capture([x for x in aligned if x['b'] < 0])
    if len(rets) < MIN['max_drawdown']:
        out['max_drawdown'] = _na('INSUFFICIENT_SAMPLE')
    else:
        w, peak, mdd = 1, 1, 0
        for x in rets:
            w = w * (1 + x['r'])
            if w > peak:
                peak = w
            dd = w / peak - 1
            if dd < mdd:
                mdd = dd
        out['max_drawdown'] = _ok(mdd, samples=len(rets))
    if len(rets) < MIN['volatility']:
        out['volatility'] = _na('INSUFFICIENT_SAMPLE')
    else:
        m = _mean([x['r'] for x in rets])
        v = 0
        for x in rets:
            v += (x['r'] - m) * (x['r'] - m)
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
        hit = (_na('INSUFFICIENT_SAMPLE') if h20 is None or h20['hit_rate'] is None else _ok(h20['hit_rate'], samples=h20['samples']))
        out['virtual_trades'] = _ok({'buy': summary['buy_count'], 'sell': summary['sell_count']}, hit20=hit)
    else:
        out['virtual_trades'] = _na('LEDGER_NOT_AVAILABLE')
    return out
