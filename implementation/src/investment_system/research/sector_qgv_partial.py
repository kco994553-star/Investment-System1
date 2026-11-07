"""Axis-only comparison of existing engine previews; never rescoring in a reader."""
from __future__ import annotations
from collections import Counter
from .sector_qgv import config_hash, preset, canonical, _input_identity

CONTRACT = 'sector-qgv-axis-comparison/1'


def assert_retained_preview(preview, snapshot, config):
    if preview.get('schema_version') != 'sector-qgv-preview/1':
        raise ValueError('REFERENCE_PREVIEW_SCHEMA_MISMATCH')
    if preview['input_hash'] != _input_identity(snapshot) or preview['config_hash'] != config_hash(config):
        raise ValueError('REFERENCE_PREVIEW_IDENTITY_MISMATCH')
    if len(preview['result_rows']) != len(snapshot['members']) or {r['company_id'] for r in preview['result_rows']} != set(snapshot['members']):
        raise ValueError('REFERENCE_PREVIEW_MEMBERS_MISMATCH')


def _allocations(config, row, axis):
    if not row.get('sector_id') or not row.get('accounting_template'):
        return {}
    p = preset(config, row['sector_id'], row['accounting_template'])
    return {canonical(v): {'role': role, 'role_weight_bp': r['weight'],
                          'inner_weight_bp': w, 'axis_weight': r['weight'] * w / 1e8,
                          'nominal_total_weight': p['axis_weights'][axis] * r['weight'] * w / 1e12}
            for role, r in p['axes'][axis].items() for v, w in r['factors'].items() if r['weight'] and w}


def _reasons(row, axis):
    if row['axes'][axis] is not None:
        return []
    missing = row.get('missing_factors', {}).get(axis, [])
    return sorted(set(row['factors'][v]['score_status'] for v in missing)) or [row['status']]


def compare_axes(before, after, before_config, after_config, comparison_id, *, input_treatment=False):
    """Preserve full denominator and factor N; Q/G common sets are independent.

    An input treatment must keep the configuration fixed. It may change mapping
    and input versions but is never labelled a same-input settings treatment.
    """
    context = ('universe_id', 'universe_version', 'engine_version', 'model_version',
               'normalization_version', 'mapping_version', 'valuation_date', 'as_of')
    if not input_treatment:
        context += ('snapshot_id', 'input_hash', 'input_version')
    elif config_hash(before_config) != config_hash(after_config):
        raise ValueError('INPUT_TREATMENT_CONFIG_CHANGED')
    for k in context:
        if before[k] != after[k]:
            raise ValueError('AXIS_COMPARISON_CONTEXT_MISMATCH:' + k)
    for view, config in ((before, before_config), (after, after_config)):
        if view['config_hash'] != config_hash(config):
            raise ValueError('AXIS_COMPARISON_CONFIG_MISMATCH')
    a = {r['company_id']: r for r in before['result_rows']}
    b = {r['company_id']: r for r in after['result_rows']}
    if set(a) != set(b) or len(a) != len(before['result_rows']) or len(b) != len(after['result_rows']):
        raise ValueError('AXIS_COMPARISON_MEMBERS_MISMATCH')
    out = []; summary = {axis: Counter({k: 0 for k in ('before_valid','after_valid','COMMON_VALID','GAINED','LOST','BOTH_UNAVAILABLE','changed_common')}) for axis in ('Q', 'G')}
    for key in sorted(a):
        old, new = a[key], b[key]; axes = {}
        for axis in ('Q', 'G'):
            ov, nv = old['axes'][axis], new['axes'][axis]
            common = ov is not None and nv is not None
            transition = 'COMMON_VALID' if common else 'GAINED' if nv is not None else 'LOST' if ov is not None else 'BOTH_UNAVAILABLE'
            delta = nv - ov if common else None
            summary[axis][transition] += 1
            summary[axis]['before_valid'] += ov is not None
            summary[axis]['after_valid'] += nv is not None
            summary[axis]['changed_common'] += bool(common and delta != 0)
            ba = _allocations(before_config, old, axis); aa = _allocations(after_config, new, axis)
            factors = []
            for v in sorted(set(ba) | set(aa)):
                x, y = old['factors'][v], new['factors'][v]
                factors.append({'variant_id': v, 'before_allocation': ba.get(v), 'after_allocation': aa.get(v),
                    'before_score': x['score'], 'after_score': y['score'],
                    'before_valid_n': x['valid_n'], 'after_valid_n': y['valid_n'],
                    'before_status': x['score_status'], 'after_status': y['score_status'],
                    'allocation_changed': ba.get(v) != aa.get(v),
                    'score_changed': x['score'] != y['score']})
            why = 'CLASSIFICATION_OR_PEER_INPUT_CHANGED' if input_treatment and (old['sector_id'], old['accounting_template']) != (new['sector_id'], new['accounting_template']) else 'PEER_RESCORING' if input_treatment and any(f['score_changed'] for f in factors) else 'FACTOR_ALLOCATION_CHANGED' if any(f['allocation_changed'] for f in factors) else 'UNCHANGED'
            axes[axis] = {'before': ov, 'after': nv, 'delta': delta, 'common_valid': common,
                          'transition': transition, 'change_reason': why,
                          'before_reasons': _reasons(old, axis), 'after_reasons': _reasons(new, axis), 'factors': factors}
        out.append({'company_id': key, 'before_context': [old['sector_id'], old['accounting_template']],
                    'after_context': [new['sector_id'], new['accounting_template']], 'axes': axes,
                    'V': {'before': old['axes']['V'], 'after': new['axes']['V']},
                    'total': {'before': old['total'], 'after': new['total']}})
    return {'schema_version': CONTRACT, 'comparison_id': comparison_id,
            'treatment': 'INPUT_CLASSIFICATION' if input_treatment else 'SAME_INPUT_CONFIGURATION',
            'valuation_date': before['valuation_date'], 'as_of': before['as_of'],
            'universe_id': before['universe_id'], 'universe_version': before['universe_version'],
            'denominator': len(a), 'axes': {k: dict(v) for k, v in summary.items()}, 'rows': out,
            'before_identity': {k: before[k] for k in ('config_hash','input_hash','cache_key','snapshot_id','input_version','engine_version','model_version','normalization_version','mapping_version')},
            'after_identity': {k: after[k] for k in ('config_hash','input_hash','cache_key','snapshot_id','input_version','engine_version','model_version','normalization_version','mapping_version')},
            'performance': None, 'performance_reason': 'NOT_MEASURED_PARTIAL_QG_DIAGNOSTIC',
            'rank': None, 'rank_reason': 'AXIS_COMPARISON_DOES_NOT_CREATE_TOTAL_OR_MARKET_RANK'}
