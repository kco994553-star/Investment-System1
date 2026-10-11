"""Build tests/fixtures/virtual_trading_reference_v1.json: synthetic ledgers + Python reference results.

All inputs are synthetic (fixed LCG, no market data). Usage: python tools/virtual_trading_reference.py [--check]
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402

OUT = ROOT / 'tests/fixtures/virtual_trading_reference_v1.json'
# Synthetic V factor composition key (factor ids present that day); the V slope compares only equal keys.
COMPOSITION = 'f_one+f_two'


class Lcg:
    def __init__(self, seed):
        self.s = seed

    def next(self):
        self.s = (self.s * 1103515245 + 12345) % 2147483648
        return self.s / 2147483648


def sessions(n, start='2025-06-02'):
    d, out = dt.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def walk(days, seed, start, vol, drift=0.0):
    r, p, out = Lcg(seed), start, {}
    for d in days:
        p = p * (1 + drift + (r.next() - 0.5) * 2 * vol)
        out[d] = round(p, 2)
    return out


def base_ledger(kind='SET_A', n=300):
    days = sessions(n)
    sp = walk(days, 7, 5000, 0.01, 0.0003)
    comps = {
        'aaa': {'currency': 'USD', 'closes': walk(days, 11, 100, 0.02, 0.0004), 'sector_benchmark': 'SMH'},
        'bbb': {'currency': 'KRW', 'closes': walk(days, 23, 50000, 0.015), 'sector_benchmark': None},
        'ccc': {'currency': 'JPY', 'closes': walk(days, 37, 3000, 0.018, 0.0002), 'sector_benchmark': 'XLK'},
    }
    fx = {'USD': walk(days, 41, 1350, 0.003), 'JPY': walk(days, 43, 9.1, 0.003)}
    snaps, vs, vc = {}, {}, {}
    r = Lcg(99)
    for i, d in enumerate(days):
        snaps[d] = {c: {'q': round(60 + 5 * r.next(), 2), 'g': round(55 + 5 * r.next(), 2), 'coverage': 'READY'} for c in sorted(comps)}
        vs[d] = {c: round(50 + 4 * r.next(), 2) for c in sorted(comps)}
        vc[d] = {c: COMPOSITION for c in sorted(comps)}
    return {'id': kind.lower() + '-1', 'kind': kind, 'sessions': days,
            'target_weights': {'aaa': 40, 'bbb': 30, 'ccc': 20},
            'companies': comps, 'benchmarks': {'SP500': sp, 'SMH': walk(days, 5, 200, 0.02)},
            'fx': fx, 'initial': {'cash': 0, 'positions': {}}, 'snapshots': snaps, 'v_scores': vs, 'v_composition': vc, 'flags': [], 'events': {}}


def cfg(start):
    c = vt.load_config()
    c = copy.deepcopy(c)
    c['start_date'] = start
    return c


def scenarios():
    out = []
    L = base_ledger(n=30)
    out.append({'name': 'not_started', 'config': cfg(None), 'ledger': L})

    L = base_ledger(n=30)
    out.append({'name': 'before_start_date', 'config': vt.load_config(), 'ledger': L})

    L = base_ledger()
    out.append({'name': 'set_a_deposit_buys', 'config': cfg(L['sessions'][280]), 'ledger': L})

    # Shadow ledger: starts from a held snapshot; overweight sells, QG decline, user hold, abnormal drop, V up, holiday, missing FX.
    L = base_ledger('SHADOW')
    d = L['sessions']
    start = 280
    L['initial'] = {'cash': 0, 'positions': {'aaa': {'quantity': 900, 'cost': 120000000}, 'bbb': {'quantity': 300, 'cost': 14000000},
                                              'ddd': {'quantity': 40, 'cost': 5000000}}}
    L['companies']['ddd'] = {'currency': 'USD', 'closes': walk(d, 53, 90, 0.02), 'sector_benchmark': None}
    for day in d:
        L['snapshots'][day]['ddd'] = {'q': 58.0, 'g': 52.0, 'coverage': 'READY'}
    L['snapshots'][d[284]]['bbb']['q'] -= 12            # QG decline on bbb
    L['flags'] = [{'date': d[286], 'company': 'ccc', 'kind': 'HOLD'}, {'date': d[290], 'company': 'ccc', 'kind': 'CLEAR'},
                  {'date': d[292], 'company': 'ddd', 'kind': 'EXCLUDE'}]
    for i in range(288, 300):                            # abnormal drop on aaa from session 288
        L['companies']['aaa']['closes'][d[i]] = round(L['companies']['aaa']['closes'][d[i]] * 0.62, 2)
    L['flags'].append({'date': d[294], 'company': 'aaa', 'kind': 'CONFIRMED_TEMPORARY'})
    for i in range(281, 300):                            # V up on ccc vs 20 sessions earlier
        L['v_scores'][d[i]]['ccc'] = L['v_scores'][d[i - 20]]['ccc'] + 12
    del L['companies']['ccc']['closes'][d[283]]          # market holiday for ccc
    del L['fx']['JPY'][d[285]]
    L['events'] = {d[287]: {'bbb': ['EARNINGS_WINDOW']}}
    L['snapshots'][d[289]]['bbb']['coverage'] = 'PARTIAL'
    L['snapshots'][d[291]]['bbb']['coverage'] = 'BLOCKED'
    out.append({'name': 'shadow_rules', 'config': {**cfg(d[start]), 'sector_basis': 'SP500_SUBSTITUTE_D22_PENDING'}, 'ledger': L})

    L = base_ledger('SHADOW', n=30)
    L['target_weights'] = None
    out.append({'name': 'shadow_without_target', 'config': cfg(L['sessions'][20]), 'ledger': L})

    L = base_ledger('SET_B', n=120)                       # under one year of history: recheck basis NA, V not used
    for i in range(21, 120):
        L['v_scores'][L['sessions'][i]]['aaa'] = L['v_scores'][L['sessions'][i - 20]]['aaa'] + 15
    out.append({'name': 'short_history_no_v_signal', 'config': cfg(L['sessions'][100]), 'ledger': L})

    L = base_ledger()
    L['benchmarks']['XLK'] = walk(L['sessions'], 61, 250, 0.012)
    c = cfg(L['sessions'][285])
    c['sector_basis'] = 'SECTOR_ETF_CONFIRMED'
    c['cost_bps'] = 10
    c['buy_limit'] = 300000
    out.append({'name': 'confirmed_sector_cost_small_limit', 'config': c, 'ledger': L})

    # V slope only between days with the same V factor composition (decision 2026-10-11): ccc V rises by 12 but the
    # composition changes on d[290] (and is unknown on d[295..]) → no V_IMPROVED there, V_COMPOSITION_CHANGED instead.
    L = base_ledger('SET_B')
    d = L['sessions']
    for i in range(281, 300):
        L['v_scores'][d[i]]['ccc'] = L['v_scores'][d[i - 20]]['ccc'] + 12
    for i in range(290, 300):
        L['v_composition'][d[i]]['ccc'] = 'f_one'
    for i in range(295, 300):
        del L['v_composition'][d[i]]['ccc']
    del L['v_composition'][d[298]]
    out.append({'name': 'v_composition_changed', 'config': cfg(d[280]), 'ledger': L})

    # Continue from a recorded state (decision 2026-10-11): cash, positions (quantity, KRW cost) and the orders decided on
    # the last recorded session; only sessions after it run, the recorded ones are not replayed.
    L = base_ledger('SET_A')
    d = L['sessions']
    L['resume'] = {'after': d[290], 'cash': 1234567.5, 'total_value': 9876543.25,
                   'positions': {'aaa': {'quantity': 12.5, 'cost': 1700000}, 'bbb': {'quantity': 40.25, 'cost': 2100000.75}},
                   'pending': [{'company': 'bbb', 'side': 'SELL', 'amount': 150000, 'reason_codes': ['OVERWEIGHT_GAP']},
                               {'company': 'ccc', 'side': 'BUY', 'amount': 420000, 'reason_codes': ['UNDERWEIGHT_GAP', 'LIMIT_EXHAUSTED']}]}
    L['flags'] = [{'date': d[289], 'company': 'ccc', 'kind': 'HOLD'}]
    out.append({'name': 'resume_from_recorded_state', 'config': cfg(d[280]), 'ledger': L})

    L = base_ledger('SET_A', n=30)
    L['resume'] = {'after': L['sessions'][-1], 'cash': 0, 'total_value': None, 'positions': {}, 'pending': []}
    out.append({'name': 'resume_no_session_after', 'config': cfg(L['sessions'][20]), 'ledger': L})

    L = base_ledger('SET_A', n=30)
    L['resume'] = {'after': L['sessions'][25], 'cash': -1, 'total_value': None, 'positions': {}, 'pending': []}
    out.append({'name': 'resume_invalid', 'config': cfg(L['sessions'][20]), 'ledger': L})

    L = base_ledger(n=5)
    out.append({'name': 'invalid_input', 'config': cfg(L['sessions'][0]), 'ledger': {**L, 'sessions': [L['sessions'][1], L['sessions'][0]]}})
    return out


def build():
    vectors = []
    for s in scenarios():
        result = vt.run_ledger(s['config'], s['ledger'])
        hits = vt.evaluate_hits(s['config'], s['ledger'], result['trades']) if result['state'] == 'OK' else None
        vectors.append({**s, 'expected': result, 'expected_hits': hits})
    return {'schema': 'virtual-trading-reference/1', 'note': 'Synthetic inputs only. Not market data.', 'vectors': vectors}


def main(argv):
    data = json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if '--check' in argv:
        if OUT.read_text(encoding='utf-8') != data + '\n':
            print('VIRTUAL_TRADING_REFERENCE_STALE')
            return 1
        print('VIRTUAL_TRADING_REFERENCE_OK')
        return 0
    OUT.write_text(data + '\n', encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)} ({len(data)} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
