"""Explain G input/peer effects with exact rank arithmetic; official scorer is unchanged.

Consumes already normalized same-membership rows, never SEC facts or prices. Input
metrics retain the official six-significant-digit precision. Scores are not rounded;
exact fractions audit the existing binary-float calculator, not a replacement model.
"""
from fractions import Fraction
import math
from investment_system.qgv import v2_scoring as vs
from investment_system.qgv.v2_factors import CALC_VERSION

POPULATION_FIELDS = ('cik', 'state', 'profile', 'industry_group', 'calc_version')


def _fraction(value):
    return None if value is None else {'numerator': value.numerator, 'denominator': value.denominator}


def _points(rows, version):
    points = {}
    for code in sorted(rows):
        r = rows[code]
        if r['state'] in vs.SCORED_STATES and r['cik'] is not None and r.get('calc_version') == version:
            points.setdefault(r['cik'], r)
    return points


def _trace(row, points, version):
    empty = {'score_unrounded': None, 'score_exact': None, 'available_weight': 0,
             'peer_basis': None, 'peer_count': 0, 'factor_details': {}}
    if (row['state'] not in vs.SCORED_STATES or row['profile'] is None
            or row.get('calc_version') != version):
        return empty, None
    profile = row['profile']
    peers = {cik: r['metrics'] for cik, r in points.items() if r['profile'] == profile}
    peer_count = len(peers) + (row['cik'] not in peers)
    out = {**empty, 'peer_basis': 'FINANCIAL_PROFILE' if profile == 'FINANCIAL' else 'UNIVERSE',
           'peer_count': peer_count, 'factor_details': {}}
    factor_values = {}
    for fid in vs.G_WEIGHTS_V2:
        details, percentiles = [], []
        for metric, direction in vs.SUBMETRICS[profile][fid]:
            own = row['metrics'].get(metric)
            values = [direction * m[metric] for cik, m in peers.items()
                      if cik != row['cik'] and m.get(metric) is not None]
            detail = {'metric': metric, 'own': own, 'direction': direction,
                      'comparison_set': profile + ':' + metric,
                      'less': None, 'equal': None, 'n': None, 'percentile_exact': None}
            if own is not None:
                x = direction * own
                less, equal, n = sum(v < x for v in values), 1 + sum(v == x for v in values), len(values) + 1
                detail.update(less=less, equal=equal, n=n)
                if peer_count >= vs.MIN_PEERS and n >= vs.MIN_PEERS:
                    pct = Fraction(100 * (2 * less + equal - 1), 2 * (n - 1))
                    detail['percentile_exact'] = _fraction(pct)
                    percentiles.append(pct)
            details.append(detail)
        value = sum(percentiles, Fraction()) / len(percentiles) if percentiles else None
        factor_values[fid] = value
        out['factor_details'][fid] = {'score_unrounded': None if value is None else float(value),
                                      'score_exact': _fraction(value), 'submetrics': details}
    weight = sum(vs.G_WEIGHTS_V2[k] for k, v in factor_values.items() if v is not None)
    score = None
    if weight * 100 >= vs.AXIS_COVERAGE_MIN * sum(vs.G_WEIGHTS_V2.values()):
        score = sum(vs.G_WEIGHTS_V2[k] * v for k, v in factor_values.items() if v is not None) / weight
    out.update(score_unrounded=None if score is None else float(score), score_exact=_fraction(score), available_weight=weight)
    return out, score


def _peer_crossings(row, old, new):
    out = []
    if row['profile'] not in vs.SUBMETRICS:
        return out
    for fid in vs.G_WEIGHTS_V2:
        for metric, direction in vs.SUBMETRICS[row['profile']][fid]:
            own = row['metrics'].get(metric)
            if own is None:
                continue
            for cik in old.keys() | new.keys():
                if cik == row['cik'] or old.get(cik, new.get(cik))['profile'] != row['profile']:
                    continue
                a = old.get(cik, {}).get('metrics', {}).get(metric)
                b = new.get(cik, {}).get('metrics', {}).get(metric)
                if a == b:
                    continue
                less = int(b is not None and direction*b < direction*own) - int(a is not None and direction*a < direction*own)
                equal = int(b is not None and b == own) - int(a is not None and a == own)
                valid = int(b is not None) - int(a is not None)
                if less or equal or valid:
                    out.append({'issuer_cik': cik, 'factor': fid, 'metric': metric,
                                'before': a, 'after': b, 'own_after': own,
                                'less_delta': less, 'equal_delta': equal, 'valid_count_delta': valid})
    return sorted(out, key=lambda x: (x['metric'], x['issuer_cik']))


def audit_g_impact(before, after, *, calc_version, target=None):
    """Trace source changes and peer effects for a fixed operational code set.

    Counterfactual order: change this row's own inputs against old peers, then
    change the peers. Components are explanatory path attribution, not causality
    or improvement claims. TARGET propagation is reported separately.
    """
    if calc_version != CALC_VERSION:
        raise ValueError('CALC_VERSION_NOT_SUPPORTED')
    if set(before) != set(after) or any(any(before[k].get(f) != after[k].get(f)
            for f in POPULATION_FIELDS) for k in before):
        raise ValueError('COMPARISON_POPULATION_CHANGED')
    old_points, new_points = _points(before, calc_version), _points(after, calc_version)
    old, _ = vs.score_rows(before, target, calc_version=calc_version)
    new, _ = vs.score_rows(after, target, calc_version=calc_version)
    output = {}
    for role, rows in (('universe', before), ('target', target or {})):
        for code, row in rows.items():
            newer = after[code] if role == 'universe' else row
            a, fa = _trace(row, old_points, calc_version)
            b, fb = _trace(newer, new_points, calc_version)
            mid, fm = _trace(newer, old_points, calc_version)
            for trace, official in ((a, old[(role, code)]), (b, new[(role, code)])):
                value = official['axes']['G']['score']
                if (trace['score_unrounded'] is None) != (value is None) or value is not None and not math.isclose(trace['score_unrounded'], value, abs_tol=1e-12, rel_tol=0):
                    raise ValueError('OFFICIAL_SCORE_TRACE_MISMATCH')
                trace['score_unrounded'] = value  # preserve the actual official float too
                for fid, detail in trace['factor_details'].items():
                    detail['score_unrounded'] = official['factors'][fid]
            changed_input = row['metrics'] != newer['metrics']
            changed_score = a['score_unrounded'] != b['score_unrounded']
            entry = {'input_changed': changed_input, 'score_changed': changed_score,
                     'effect_kind': ('DIRECT_INPUT_AND_PEER' if changed_input else 'PEER_ONLY') if changed_score
                                    else 'INPUT_CHANGED_ORDER_PRESERVED' if changed_input else 'UNCHANGED',
                     'changed_metrics': {m: {'before': row['metrics'].get(m), 'after': newer['metrics'].get(m)}
                                         for m in sorted(set(row['metrics']) | set(newer['metrics']))
                                         if row['metrics'].get(m) != newer['metrics'].get(m)},
                     'before': a, 'after': b,
                     'peer_crossings': _peer_crossings(newer, old_points, new_points),
                     'own_change_with_old_peers': mid,
                     'delta_exact': _fraction(None if fa is None or fb is None else fb-fa),
                     'own_input_delta_exact': _fraction(None if fa is None or fm is None else fm-fa),
                     'peer_delta_exact': _fraction(None if fm is None or fb is None else fb-fm)}
            output[(role, code)] = entry
    all_rows = {k: output[('universe', k)] for k in before}
    sets = {}
    for profile, specs in vs.SUBMETRICS.items():
        for fid in vs.G_WEIGHTS_V2:
            for metric, _ in specs[fid]:
                sets[profile + ':' + metric] = {
                    'before': sorted(c for c,r in old_points.items() if r['profile']==profile and r['metrics'].get(metric) is not None),
                    'after': sorted(c for c,r in new_points.items() if r['profile']==profile and r['metrics'].get(metric) is not None)}
    checks = {
        'membership_metadata_unchanged': True,
        'all_Q_unchanged': all(old[('universe', k)]['axes']['Q'] == new[('universe', k)]['axes']['Q'] for k in before),
        'financial_G_unchanged': all(not all_rows[k]['score_changed'] for k in before if before[k]['profile']=='FINANCIAL'),
        'factor_valid_sets_unchanged': all((old[('universe', k)]['factors'][f] is None) == (new[('universe', k)]['factors'][f] is None)
                                          for k in before for f in vs.FACTOR_IDS),
        'comparison_set_members_unchanged': all(v['before']==v['after'] for v in sets.values()),
    }
    return {'schema_version': 'qg-input-impact/1', 'calc_version': calc_version,
            'input_precision': 'OFFICIAL_NORMALIZED_METRICS_6_SIGNIFICANT_DIGITS',
            'score_precision': 'OFFICIAL_UNROUNDED_FLOAT_AND_EXACT_RANK_FRACTION',
            'weights': dict(vs.G_WEIGHTS_V2), 'comparison_sets': sets, 'unaffected_checks': checks,
            'counts': {'codes': len(before), 'input_changed': sum(r['input_changed'] for r in all_rows.values()),
                       'score_changed': sum(r['score_changed'] for r in all_rows.values()),
                       'direct_changed': sum(r['score_changed'] and r['input_changed'] for r in all_rows.values()),
                       'indirect_changed': sum(r['score_changed'] and not r['input_changed'] for r in all_rows.values()),
                       'input_changed_score_unchanged': sum(r['input_changed'] and not r['score_changed'] for r in all_rows.values())},
            'rows': all_rows,
            'target_rows': {k: output[('target', k)] for k in target or {}},
            'interpretation': 'SCORE_MOVEMENT_NOT_IMPROVEMENT'}
