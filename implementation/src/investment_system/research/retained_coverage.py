"""Coverage of already computed rows. Never infer factor availability from totals."""
from collections import Counter

from .classification_counts import count, require, score_present


def coverage_scope(preview_rows, class_rows):
    rows = list(preview_rows)
    classes = {r['company_id']: r for r in class_rows}
    stages = {k: [] for k in ('sector', 'accounting', 'required_components_present',
                             'all_default_raw', 'all_default_factor_scores', 'Q', 'G', 'V',
                             'joint', 'pre_gate_total', 'total', 'all_axes_and_total')}
    unresolved = 0
    factor_counts = {}
    for row in rows:
        key = row['company_id']
        selected = row.get('selected_variants', [])
        require(len(set(selected)) == len(selected), 'DUPLICATE_SELECTED_VARIANT')
        if not selected:
            unresolved += 1
        f = [row['factors'][v] for v in selected]
        for item in row['factors'].values():
            require(type(item['raw_components_available']) is bool and
                    type(item['verified_external_available']) is bool, 'INPUT_AVAILABILITY_TYPE')
        flags = {k: classes[key][k]['status'] == 'CONFIRMED' for k in ('sector', 'accounting')}
        flags.update(required_components_present=bool(f) and all(x['raw_components_available'] or x['verified_external_available'] for x in f),
                     all_default_raw=bool(f) and all(x['raw_value'] is not None for x in f),
                     all_default_factor_scores=bool(f) and all(score_present(x['score']) for x in f),
                     **{a: score_present(row['axes'][a]) for a in 'QGV'},
                     pre_gate_total=score_present(row['pre_gate_total']), total=score_present(row['total']))
        flags['joint'] = all(flags[a] for a in 'QGV')
        flags['all_axes_and_total'] = flags['joint'] and flags['total']
        for stage, valid in flags.items():
            if valid:
                stages[stage].append(row)
        for variant, x in row['factors'].items():
            item = factor_counts.setdefault(variant, {'denominator': len(rows), 'selected': 0,
                'components_present': 0, 'raw_valid': 0, 'score_valid': 0, 'raw_failures': Counter(), 'score_failures': Counter()})
            item['selected'] += variant in selected
            item['components_present'] += x['raw_components_available'] or x['verified_external_available']
            item['raw_valid'] += x['raw_value'] is not None
            item['score_valid'] += score_present(x['score'])
            if x['raw_value'] is None:
                item['raw_failures'][x['raw_status']] += 1
            if x['score'] is None:
                item['score_failures'][x['score_status']] += 1
    output = {}
    for unit in ('code_rows', 'issuers'):
        size = len(rows) if unit == 'code_rows' else len({r['issuer_id'] for r in rows})
        values = {k: len(v) if unit == 'code_rows' else len({r['issuer_id'] for r in v}) for k, v in stages.items()}
        output[unit] = {k: count(n, size) for k, n in values.items()}
        target = (size * 95 + 99) // 100
        output[unit]['target'] = {'goal_percent': 95, 'stage': 'all_axes_and_total',
            'minimum_valid': target, 'valid': values['all_axes_and_total'], 'denominator': size,
            'additional_required': max(0, target - values['all_axes_and_total']),
            'state': 'EMPTY_POPULATION' if size == 0 else 'MET' if values['all_axes_and_total'] >= target else 'BELOW_TARGET',
            'aggregation': 'EXISTS_ONE_ORIGINAL_ROW_WITH_COMPLETE_STAGE_NOT_CROSS_ROW_AXIS_COMBINATION'}
    output.update(default_selection_unresolved=unresolved, factors=factor_counts,
                  gate_decisions=dict(Counter(r['gate_status'] for r in rows)),
                  total_failure_reasons=dict(Counter(r['status'] for r in rows if r['total'] is None)),
                  required_components_meaning='DECLARED_COMPONENT_PRESENCE_NOT_VALIDITY_OR_GATE_PASS')
    return output
