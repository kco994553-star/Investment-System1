"""Build tests/fixtures/report_benchmarks_v1.json: SYNTHETIC vectors for S17 ⑪⑫⑬ (qgv/report_benchmarks.py).

Every close, FX rate, ledger value and trade below is generated (fixed LCG / fixed numbers), not market data.
- build vectors: SPY / XLK / QUAL / XLY / XLP closes, KRW=X rates (one day missing), VUG rejected by the Worker,
  an engine-shaped ledger (one unvalued day) → KRW and USD bases, every period, gaps, missing base / last values,
  a period longer than the ledger, no SPY, and the state before the start date.
- track vectors: engine evaluate_hits on synthetic ledger inputs → before the start date, window not elapsed, no trades,
  ≥ 30 samples, and a missing end close.
Usage: python tools/report_benchmarks_reference.py [--check]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import report_benchmarks as rb  # noqa: E402
from investment_system.qgv import virtual_trading as vt  # noqa: E402
import virtual_trading_inputs_reference as base  # noqa: E402

OUT = ROOT / 'tests/fixtures/report_benchmarks_v1.json'
NOTE = 'SYNTHETIC test vectors: every close, FX rate, ledger value and trade below is generated, not market data.'
DAYS = base.weekdays('2026-04-01', '2026-11-30')
START = '2026-10-19'


def walk(seed, start, amplitude, days=DAYS):
    r, p, out = base.Lcg(seed), start, {}
    for d in days:
        p = round(p * (1 + (r.next() - 0.5) * amplitude), 4)
        out[d] = p
    return out


def drop(series, *dates):
    return {d: v for d, v in series.items() if d not in dates}


def indices():
    return {'SPY': walk(11, 500.0, 0.03), 'XLK': drop(walk(12, 200.0, 0.04), '2026-11-02'), 'QUAL': walk(13, 150.0, 0.02),
            'XLY': walk(14, 180.0, 0.035), 'XLP': drop(walk(15, 80.0, 0.015), '2026-11-23'),
            'KRW=X': drop(walk(16, 1380.0, 0.01), '2026-11-11')}


SOURCES = {'SPY': {'state': 'OK', 'code': None}, 'VUG': {'state': 'NOT_AVAILABLE', 'code': 'REQUEST_INVALID'}}


def ledger_days(seed, gap=None, last_none=False):
    r, total, out = base.Lcg(seed), 1_000_000.0, []
    days = [d for d in DAYS if d >= START]
    for i, d in enumerate(days):
        if i:
            total = round(total * (1 + (r.next() - 0.5) * 0.03) + 1_000_000, 2)
        value = None if d == gap or (last_none and i == len(days) - 1) else total
        out.append({'date': d, 'total_value': value, 'deposit': 1_000_000})
    return out


def set_a(**kw):
    return {'key': 'SET_A', 'state': 'OK', 'reason_codes': [], 'days': ledger_days(21, gap='2026-11-04', **kw)}


SET_B_NA = {'key': 'SET_B', 'state': 'NOT_AVAILABLE', 'reason_codes': ['SET_B_NOT_DEFINED'], 'days': []}


def build_scenarios():
    ix = indices()
    early = {k: {d: v for d, v in s.items() if d < START} for k, s in ix.items()}
    out = [
        {'name': 'krw_20d', 'inputs': {'indices': ix, 'sources': SOURCES, 'ledgers': [set_a(), SET_B_NA], 'start_date': START, 'period': '20D', 'basis': 'KRW'}},
        {'name': 'usd_since_start', 'inputs': {'indices': ix, 'sources': SOURCES, 'ledgers': [set_a(), SET_B_NA], 'start_date': START, 'period': 'SINCE_START', 'basis': 'USD'}},
        {'name': 'krw_120d_before_ledger', 'inputs': {'indices': ix, 'sources': SOURCES, 'ledgers': [set_a()], 'start_date': START, 'period': '120D', 'basis': 'KRW'}},
        {'name': 'last_values_missing', 'inputs': {'indices': {**ix, 'XLK': drop(ix['XLK'], '2026-11-30')}, 'sources': SOURCES,
                                                  'ledgers': [set_a(last_none=True)], 'start_date': START, 'period': '5D', 'basis': 'KRW'}},
        {'name': 'base_close_missing', 'inputs': {'indices': {**ix, 'XLP': drop(ix['XLP'], '2026-11-20')}, 'sources': SOURCES,
                                                 'ledgers': [set_a()], 'start_date': START, 'period': '5D', 'basis': 'USD'}},
        {'name': 'shadow_with_set_a', 'inputs': {'indices': ix, 'sources': SOURCES,
                                                'ledgers': [{'key': 'SHADOW', 'state': 'OK', 'reason_codes': [], 'days': ledger_days(31)}, set_a()],
                                                'start_date': START, 'period': '1D', 'basis': 'KRW'}},
        {'name': 'no_spy', 'inputs': {'indices': {k: v for k, v in ix.items() if k != 'SPY'}, 'sources': {'SPY': {'state': 'NOT_AVAILABLE', 'code': 'RATE_LIMITED'}},
                                      'ledgers': [SET_B_NA], 'start_date': START, 'period': '20D', 'basis': 'KRW'}},
        {'name': 'not_started_no_request', 'inputs': {'indices': {}, 'sources': {},
                                                     'ledgers': [{'key': 'SET_A', 'state': 'NOT_STARTED', 'reason_codes': ['BEFORE_START_DATE'], 'days': []}],
                                                     'start_date': START, 'period': '20D', 'basis': 'KRW'}},
        {'name': 'no_fx', 'inputs': {'indices': {k: v for k, v in ix.items() if k != 'KRW=X'}, 'sources': SOURCES,
                                     'ledgers': [set_a()], 'start_date': START, 'period': '20D', 'basis': 'KRW'}},
        {'name': 'before_start_rehearsal_indices', 'inputs': {'indices': early, 'sources': SOURCES,
                                                             'ledgers': [{'key': 'SET_A', 'state': 'NOT_STARTED', 'reason_codes': ['BEFORE_START_DATE'], 'days': []}],
                                                             'start_date': START, 'period': 'SINCE_START', 'basis': 'KRW'}},
        {'name': 'before_start_60d', 'inputs': {'indices': early, 'sources': SOURCES,
                                               'ledgers': [{'key': 'SET_A', 'state': 'NOT_STARTED', 'reason_codes': ['BEFORE_START_DATE'], 'days': []}],
                                               'start_date': START, 'period': '60D', 'basis': 'USD'}},
    ]
    return out


def track_input(n, seed=41, hole=None):
    sessions = [d for d in DAYS if d >= START][:n] if n <= 31 else base.weekdays('2026-10-19', '2027-03-31')[:n]
    r = base.Lcg(seed)
    closes = {}
    for c in ('nvda', 'msft'):
        p, s = 100.0, {}
        for d in sessions:
            p = round(p * (1 + (r.next() - 0.5) * 0.04), 4)
            s[d] = p
        closes[c] = s
    if hole:
        closes['msft'].pop(hole)
    p, spy = 500.0, {}
    for d in sessions:
        p = round(p * (1 + (r.next() - 0.5) * 0.02), 4)
        spy[d] = p
    return {'sessions': sessions, 'companies': {c: {'currency': 'USD', 'closes': s} for c, s in closes.items()}, 'benchmarks': {'SP500': spy}}


def trades_on(sessions, idx, companies=('nvda', 'msft')):
    out = []
    for k, i in enumerate(idx):
        out.append({'date': sessions[i], 'company': companies[k % len(companies)], 'side': 'BUY' if k % 3 else 'SELL'})
    return out


def track_scenarios():
    cfg = vt.load_config()
    out = [{'name': 'before_start', 'inputs': {'hits': None, 'trades': [], 'ledger_input': None, 'ledger_reasons': ['BEFORE_START_DATE'], 'start_date': START}}]
    short = track_input(10)
    out.append({'name': 'window_not_elapsed', 'inputs': {'ledger_input': short, 'trades': trades_on(short['sessions'], [1, 2])}})
    out.append({'name': 'no_trades', 'inputs': {'ledger_input': short, 'trades': []}})
    longer = track_input(90)
    out.append({'name': 'enough_samples', 'inputs': {'ledger_input': longer, 'trades': trades_on(longer['sessions'], list(range(1, 81, 2)))}})
    holed = track_input(12, hole=None)
    holed['companies']['msft']['closes'].pop(holed['sessions'][7])
    out.append({'name': 'end_close_missing', 'inputs': {'ledger_input': holed, 'trades': [{'date': holed['sessions'][2], 'company': 'msft', 'side': 'BUY'}]}})
    for sc in out[1:]:
        i = sc['inputs']
        i.update(hits=vt.evaluate_hits(cfg, copy.deepcopy(i['ledger_input']), i['trades']), ledger_reasons=[], start_date=i['ledger_input']['sessions'][0])
    for sc in out:
        sc['inputs'].update(windows=list(cfg['hit_windows']), min_samples=cfg['hit_min_samples'])
    return out


def build():
    bv = [{'name': s['name'], 'inputs': s['inputs'], 'expected': rb.build(**copy.deepcopy(s['inputs']))} for s in build_scenarios()]
    tv = [{'name': s['name'], 'inputs': s['inputs'], 'expected': rb.track_record(**copy.deepcopy(s['inputs']))} for s in track_scenarios()]
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'build_vectors': bv, 'track_vectors': tv}


def text():
    return json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def main(argv):
    if '--check' in argv:
        print('REPORT_BENCHMARKS_REFERENCE_OK' if OUT.read_text(encoding='utf-8') == text() else 'REPORT_BENCHMARKS_REFERENCE_STALE')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
