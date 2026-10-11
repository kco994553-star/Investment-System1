"""Python reference for the device-only forward validation computations (cross-check vectors only).

The device (``forward-validation.js``) computes these in RAM from price history it
loads on an explicit click; nothing here is ever run on prices in Actions, and
no result is stored, published or sent. Shared synthetic vectors keep the two
implementations identical (same order of operations, same IEEE doubles).

Forward return rules (v1, UNCALIBRATED):
- per instrument, a bar is usable unless its session_status is IN_PROGRESS;
- base = first usable bar on or after the start date, end = last usable bar;
- return = end.adjusted_close / base.adjusted_close - 1 in the instrument's own
  currency (FX is not applied: no FX source exists);
- a missing series, base, end or adjusted_close gives NOT_AVAILABLE, never 0;
- the portfolio return needs every TARGET instrument: sum(units * return) /
  sum(units), summed in sorted company-id order; otherwise NOT_AVAILABLE;
- the S&P 500 benchmark is NOT_AVAILABLE (not served by the private Worker).
"""
from __future__ import annotations

import math

BENCHMARK = {'state': 'NOT_AVAILABLE', 'reason': 'SP500_NOT_IN_PRIVATE_HISTORY_WORKER'}
BASIS = 'ADJUSTED_CLOSE_LOCAL_CURRENCY_NO_FX'


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def instrument_return(series, start_date):
    if series is None:
        return {'state': 'NOT_AVAILABLE', 'reason': 'HISTORY_NOT_LOADED'}
    if isinstance(series, str):
        return {'state': 'NOT_AVAILABLE', 'reason': series}
    usable = [bar for bar in series if bar['session_status'] != 'IN_PROGRESS']
    after = [bar for bar in usable if bar['session_date'] >= start_date]
    if not after:
        return {'state': 'NOT_AVAILABLE', 'reason': 'NO_SESSION_ON_OR_AFTER_START'}
    base, end = after[0], usable[-1]
    if base is end:
        return {'state': 'NOT_AVAILABLE', 'reason': 'NO_SESSION_AFTER_BASE'}
    if not _positive(base['adjusted_close']):
        return {'state': 'NOT_AVAILABLE', 'reason': 'BASE_ADJUSTED_CLOSE_MISSING'}
    if not _positive(end['adjusted_close']):
        return {'state': 'NOT_AVAILABLE', 'reason': 'END_ADJUSTED_CLOSE_MISSING'}
    return {'state': 'AVAILABLE', 'reason': None, 'base_date': base['session_date'], 'end_date': end['session_date'],
            'return': end['adjusted_close'] / base['adjusted_close'] - 1}


def forward_return(*, start_date, weights_units, series):
    instruments = {cid: instrument_return(series.get(cid), start_date) for cid in sorted(weights_units)}
    missing = [cid for cid, r in instruments.items() if r['state'] != 'AVAILABLE']
    out = {'basis': BASIS, 'start_date': start_date, 'instruments': instruments, 'benchmark': dict(BENCHMARK),
           'missing_count': len(missing)}
    if missing:
        return {**out, 'state': 'NOT_AVAILABLE', 'reason': 'INSTRUMENTS_MISSING', 'portfolio_return': None,
                'end_date_min': None, 'end_date_max': None}
    total, acc = 0, 0.0
    for cid in sorted(weights_units):
        acc += weights_units[cid] * instruments[cid]['return']
        total += weights_units[cid]
    ends = [r['end_date'] for r in instruments.values()]
    return {**out, 'state': 'AVAILABLE', 'reason': None, 'portfolio_return': acc / total,
            'end_date_min': min(ends), 'end_date_max': max(ends)}


def qg_summary(record):
    """Per-day Q·G summary: available counts and TARGET-weighted means over companies with a score."""
    if record['state'] != 'RECORDED':
        return {'date': record['date'], 'state': 'NOT_AVAILABLE', 'reason_codes': list(record['reason_codes'])}
    weights, companies = record['target']['weights_units'], record['companies']
    out = {'date': record['date'], 'state': 'RECORDED', 'reason_codes': [], 'companies': len(companies)}
    for axis in ('Q', 'G'):
        units, acc, count = 0, 0.0, 0
        for cid in sorted(companies):
            score = companies[cid][axis]['score']
            if score is None:
                continue
            units += weights[cid]
            acc += weights[cid] * score
            count += 1
        out[axis] = {'available': count, 'covered_units': units, 'weighted_mean': None if units == 0 else acc / units}
    return out
