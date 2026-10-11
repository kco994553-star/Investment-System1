#!/usr/bin/env python3
"""Synthetic Python reference vectors for the device forward validation computations (JS parity).

Writes tests/fixtures/forward_validation_reference_v1.json. Every value is invented test data:
never a real price, return or published record. Usage: python tools/forward_validation_reference.py [--check]
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.validation import forward_device_reference as ref  # noqa: E402
from investment_system.validation.forward_ledger import IDS, UNITS  # noqa: E402

OUT = ROOT / 'tests/fixtures/forward_validation_reference_v1.json'
START = '2026-10-19'


def bars(*rows):
    return [{'session_date': d, 'adjusted_close': c, 'session_status': s} for d, c, s in rows]


def full_series(offset=0.0):
    series = {}
    for index, cid in enumerate(IDS):
        base = 40.0 + index * 7.125 + offset
        series[cid] = bars(('2026-10-16', base - 1.5, 'COMPLETE'), ('2026-10-19', base, 'COMPLETE'),
                           ('2026-10-20', base * 1.0125, 'COMPLETE'), ('2026-10-21', base * (1 + (index - 9) / 400), 'COMPLETE'),
                           ('2026-10-22', base * 1.5, 'IN_PROGRESS'))
    return series


def cases():
    weights = dict(UNITS)
    out = []
    full = full_series()
    out.append(('all_available', 'forward_return', {'start_date': START, 'weights_units': weights, 'series': full}))
    partial = {cid: v for cid, v in full.items() if cid != 'hanmi'}
    out.append(('one_not_loaded_is_not_zero', 'forward_return', {'start_date': START, 'weights_units': weights, 'series': partial}))
    coded = dict(full)
    coded['tokyo_electron'] = 'RATE_LIMITED'
    out.append(('worker_code_kept', 'forward_return', {'start_date': START, 'weights_units': weights, 'series': coded}))
    edge = {
        'before_start_only': bars(('2026-10-15', 10.0, 'COMPLETE'), ('2026-10-16', 11.0, 'COMPLETE')),
        'base_only': bars(('2026-10-16', 10.0, 'COMPLETE'), ('2026-10-19', 11.0, 'COMPLETE'), ('2026-10-20', 12.0, 'IN_PROGRESS')),
        'base_null': bars(('2026-10-19', None, 'COMPLETE'), ('2026-10-20', 12.0, 'COMPLETE')),
        'end_null': bars(('2026-10-19', 10.0, 'UNKNOWN'), ('2026-10-21', None, 'COMPLETE')),
        'holiday_gap': bars(('2026-10-20', 20.0, 'UNKNOWN'), ('2026-10-23', 21.5, 'UNKNOWN')),
    }
    out.append(('instrument_edges', 'forward_return', {'start_date': START,
                'weights_units': {k: 100 for k in edge}, 'series': edge}))
    record = {'date': '2026-10-19', 'state': 'RECORDED', 'reason_codes': [], 'target': {'weights_units': weights},
              'companies': {cid: {'state': 'LIVE' if i % 3 else 'NOT_AVAILABLE',
                                  'Q': {'score': None if i % 3 == 0 else 30.0 + i * 2.5625, 'coverage': 'BLOCKED' if i % 3 == 0 else 'PARTIAL', 'missing_factor_count': 6},
                                  'G': {'score': None if i % 3 == 0 or i == 4 else 55.5 - i * 1.75, 'coverage': 'BLOCKED' if i % 3 == 0 or i == 4 else 'PARTIAL', 'missing_factor_count': 5}}
                            for i, cid in enumerate(IDS)}}
    out.append(('qg_summary_recorded', 'qg_summary', record))
    out.append(('qg_summary_not_available', 'qg_summary', {'date': '2026-10-20', 'state': 'NOT_AVAILABLE',
                'reason_codes': ['SEC_QG_FACTORS_MISSING'], 'target': None, 'companies': None}))
    empty = {**record, 'companies': {cid: {**row, 'Q': {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 7}}
                                     for cid, row in record['companies'].items()}}
    out.append(('qg_summary_no_q_scores', 'qg_summary', empty))
    return out


def replay(case):
    if case.get('synthetic') is not True:
        raise ValueError('SYNTHETIC_ONLY')
    if case['operation'] == 'forward_return':
        return ref.forward_return(**case['input'])
    if case['operation'] == 'qg_summary':
        return ref.qg_summary(case['input'])
    raise ValueError('UNKNOWN_OPERATION')


def build():
    result = []
    for cid, op, data in cases():
        case = {'id': cid, 'synthetic': True, 'operation': op, 'input': data}
        case['expected'] = replay(case)
        result.append(case)
    return {'synthetic': True, 'role': 'REFERENCE_TEST_ONLY', 'cases': result}


def text():
    return json.dumps(build(), sort_keys=True, ensure_ascii=True, allow_nan=False, indent=1) + '\n'


def main(argv):
    if '--check' in argv:
        ok = OUT.exists() and OUT.read_text() == text()
        print('FORWARD_REFERENCE_OK' if ok else 'FORWARD_REFERENCE_STALE')
        return 0 if ok else 1
    OUT.write_text(text())
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
