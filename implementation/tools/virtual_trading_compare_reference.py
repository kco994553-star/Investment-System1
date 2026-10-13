"""Build tests/fixtures/virtual_trading_compare_v1.json: SYNTHETIC vectors for the set comparison metrics.

Engine days come from the synthetic ledgers of tools/virtual_trading_reference.py (fixed LCG, no market data), reduced to
the price-free shape the comparison reads (date, total value, deposit, held weights, reason codes). The S&P 500 and
KRW=X series are the same synthetic ledger's benchmark and FX series. Expected values: qgv/virtual_trading_compare.py.
Usage: python tools/virtual_trading_compare_reference.py [--check]
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_compare as vc  # noqa: E402
import virtual_trading_reference as ref  # noqa: E402

OUT = ROOT / 'tests/fixtures/virtual_trading_compare_v1.json'
NOTE = 'SYNTHETIC test vectors: every value, close and rate below is generated (LCG), not market data; no holdings.'
TYPES = {'aaa': {'growth': 0.8, 'quality': 0.4, 'cyclical': None, 'defensive': 0.0}, 'bbb': {'growth': None, 'quality': None, 'cyclical': None, 'defensive': None},
         'ddd': {'growth': 0.1, 'quality': 0.9, 'cyclical': 0.5, 'defensive': 0.2}}


def reduce_days(days):
    """Price-free days: only what the comparison reads."""
    return [{'date': d['date'], 'total_value': d['total_value'], 'deposit': d['deposit'],
             'judgements': {cid: {'held': j['held'], 'actual_weight': j['actual_weight'], 'reason_codes': j['reason_codes']}
                            for cid, j in sorted(d['judgements'].items())}} for d in days]


def run(ledger, start, cfg_patch=None):
    cfg = ref.cfg(ledger['sessions'][start])
    cfg.update(cfg_patch or {})
    result = vt.run_ledger(cfg, ledger)
    hits = vt.evaluate_hits(cfg, ledger, result['trades']) if result['state'] == 'OK' else None
    summary = {'buy_count': result['summary']['buy_count'], 'sell_count': result['summary']['sell_count']} if result['summary'] else None
    return reduce_days(result['days']), hits, summary


def scenarios():
    out = []
    L = ref.base_ledger()
    indices = {'SPY': L['benchmarks']['SP500'], 'KRW=X': L['fx']['USD']}
    days, hits, summary = run(L, 180)
    out.append({'name': 'long_set_krw', 'days': days, 'indices': indices, 'basis': 'KRW', 'types': TYPES, 'hits': hits, 'summary': summary})
    out.append({'name': 'long_set_usd', 'days': days, 'indices': indices, 'basis': 'USD', 'types': None, 'hits': hits, 'summary': summary})
    short, h2, s2 = run(L, 285)
    out.append({'name': 'short_set_below_minimums', 'days': short, 'indices': indices, 'basis': 'KRW', 'types': TYPES, 'hits': h2, 'summary': s2})
    gap = copy.deepcopy(indices)
    for d in L['sessions'][230:233]:
        del gap['SPY'][d]
    del gap['KRW=X'][L['sessions'][240]]
    out.append({'name': 'gaps_in_spy_and_fx', 'days': days, 'indices': gap, 'basis': 'KRW', 'types': TYPES, 'hits': hits, 'summary': summary})
    out.append({'name': 'no_fx_series', 'days': days, 'indices': {'SPY': indices['SPY']}, 'basis': 'KRW', 'types': TYPES, 'hits': hits, 'summary': summary})
    S = ref.scenarios()
    shadow = next(s for s in S if s['name'] == 'shadow_rules')
    sh = vt.run_ledger(shadow['config'], shadow['ledger'])
    out.append({'name': 'shadow_with_valuation_gap', 'days': reduce_days(sh['days']), 'indices': {'SPY': shadow['ledger']['benchmarks']['SP500'], 'KRW=X': shadow['ledger']['fx']['USD']},
                'basis': 'KRW', 'types': TYPES, 'hits': vt.evaluate_hits(shadow['config'], shadow['ledger'], sh['trades']),
                'summary': {'buy_count': sh['summary']['buy_count'], 'sell_count': sh['summary']['sell_count']}})
    out.append({'name': 'not_started', 'days': [], 'indices': indices, 'basis': 'KRW', 'types': TYPES, 'hits': None, 'summary': None})
    return out


def build():
    vectors = []
    for s in scenarios():
        expected = vc.metrics(days=s['days'], indices=s['indices'], basis=s['basis'], types=s['types'], hits=s['hits'], summary=s['summary'])
        vectors.append({**s, 'expected': expected})
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'min': vc.MIN, 'vectors': vectors}


def text():
    return json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def main(argv):
    if '--check' in argv:
        print('VIRTUAL_TRADING_COMPARE_REFERENCE_OK' if OUT.read_text(encoding='utf-8') == text() else 'VIRTUAL_TRADING_COMPARE_REFERENCE_STALE')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
