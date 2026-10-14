"""Price-free QGV v2 input coverage report, without V, prices, returns or private data."""
from __future__ import annotations

from collections import Counter


def _distribution(values):
    ordered = sorted(values)
    if not ordered:
        return {'count': 0, 'minimum': None, 'median': None, 'maximum': None, 'mean': None,
                'bands': {f'{n}-{100 if n == 80 else n + 19}': 0 for n in range(0, 100, 20)}}
    n = len(ordered)
    bands = Counter(min(4, int(x // 20)) for x in ordered)
    return {'count': n, 'minimum': ordered[0], 'median': (ordered[(n - 1) // 2] + ordered[n // 2]) / 2,
            'maximum': ordered[-1], 'mean': sum(ordered) / n,
            'bands': {f'{k * 20}-{100 if k == 4 else k * 20 + 19}': bands[k] for k in range(5)}}


def report(payload):
    from ..universe.sec_qgv2 import require_qgv2
    require_qgv2(payload)
    records = payload['records']
    result = {'as_of': payload['as_of'], 'registered_codes': len(records),
              'source_state': payload['state'], 'issuer_cross_section': payload['cross_section_size'],
              'axes': {}, 'industry_top10': {}, 'inspection_candidates': [],
              'V': {'state': 'NOT_AVAILABLE', 'reason': 'DEVICE_PRICES_REQUIRED'},
              'total': {'state': 'NOT_AVAILABLE', 'reason': 'DEVICE_ONLY_COMPOSITE'},
              'limitations': ['PRICE_FREE_QG_ONLY', 'AVAILABLE_ROWS_ONLY', 'NO_BACKFILL', 'HOLDOUT_UNUSED']}
    for axis in ('Q', 'G'):
        factors = [f for f in next(iter(records.values()))['factors'] if f.startswith(axis.lower() + '_')]
        scores = [r['axes'][axis]['score'] for r in records.values() if r['axes'][axis]['score'] is not None]
        result['axes'][axis] = {'distribution': _distribution(scores), 'missing_codes': len(records) - len(scores),
                               'missing_rate': (len(records) - len(scores)) / len(records),
                               'factor_missing': {f: sum(r['factors'][f] is None for r in records.values()) for f in factors}}
    groups = sorted({r['industry_group'] for r in records.values() if r['industry_group'] is not None})
    for group in groups:
        result['industry_top10'][group] = {}
        for axis in ('Q', 'G'):
            selected = [(code, r) for code, r in records.items() if r['industry_group'] == group and r['axes'][axis]['score'] is not None]
            selected.sort(key=lambda item: (-item[1]['axes'][axis]['score'], item[0]))
            result['industry_top10'][group][axis] = [{'code': code, 'score': r['axes'][axis]['score'],
                                                    'factors_available': r['axes'][axis]['factors_available'],
                                                    'peer_basis': r['axes'][axis]['peer_basis']} for code, r in selected[:10]]
    candidates = []
    for code, r in records.items():
        if r['state'] == 'NOT_AVAILABLE':
            continue
        q, g = r['axes']['Q']['score'], r['axes']['G']['score']
        reasons = []
        if q is None or g is None:
            reasons.append('AXIS_MISSING')
        if any(a['submetric_fallbacks'] for a in r['axes'].values()):
            reasons.append('SUBMETRIC_UNIVERSE_FALLBACK')
        if any(a['available_weight'] < 100 for a in r['axes'].values()):
            reasons.append('PARTIAL_FACTOR_COVERAGE')
        if r['profile'] == 'FINANCIAL':
            reasons.append('FINANCIAL_V_UNDEFINED')
        # Merely inspection priority: this introduces no new scoring or decision threshold.
        gap = abs(q - g) if q is not None and g is not None else None
        candidates.append({'code': code, 'Q': q, 'G': g, 'axis_gap': gap, 'checks': reasons})
    candidates.sort(key=lambda r: (-(r['axis_gap'] if r['axis_gap'] is not None else -1), -len(r['checks']), r['code']))
    result['inspection_candidates'] = candidates[:10]
    return result
