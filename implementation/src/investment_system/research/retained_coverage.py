"""Coverage of already computed rows. Never infer factor availability from totals."""
from collections import Counter

from .classification_counts import count, require, score_present


def coverage_scope(preview_rows, class_rows, *, input_gaps=None, v_readiness=None):
    rows = list(preview_rows)
    classes = {r['company_id']: r for r in class_rows}
    stages = {k: [] for k in ('sector', 'accounting', 'required_components_present',
                             'all_default_raw', 'all_default_factor_scores', 'Q', 'G', 'V',
                             'joint', 'pre_gate_total', 'total', 'all_axes_and_total', 'any_raw', 'any_factor_scores')}
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
        flags['any_raw'] = any(x['raw_value'] is not None for x in row['factors'].values())
        flags['any_factor_scores'] = any(score_present(x['score']) for x in row['factors'].values())
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
                  causes=cause_counts(rows, classes, input_gaps or {}, v_readiness or {}),
                  gate_decisions=dict(Counter(r['gate_status'] for r in rows)),
                  total_failure_reasons=dict(Counter(r['status'] for r in rows if r['total'] is None)),
                  required_components_meaning='DECLARED_COMPONENT_PRESENCE_NOT_VALIDITY_OR_GATE_PASS')
    return output


def cause_counts(rows, classes, gaps, readiness):
    """Overlapping observed reasons, not an invented single root cause.

    Missing raw input is not proof of a period mismatch or formula validity.
    An absent basis audit remains unassessed rather than an observed zero.
    """
    fields = ('classification', 'accounting', 'period', 'share_basis', 'price',
              'formula_applicability', 'gate', 'peer_sample', 'security_identity', 'ev_components')
    observations = {k: [] for k in fields}
    for row in rows:
        key = row['company_id'];selected = row.get('selected_variants', [])
        factors = [row['factors'][v] for v in selected]
        raw = {f['raw_status'] for f in factors}
        missing = not factors or 'MISSING_INPUT' in raw
        vrows = readiness.get(key)
        gap = gaps.get(key, {})
        def basis(field, codes):
            if vrows:
                return any(any(x in codes for x in r['nonprice_missing']) for r in vrows)
            status = gap.get(field, {}).get('status')
            return True if status in ('NOT_CONNECTED', 'UNCONFIRMED') else False if status == 'NOT_REQUIRED_BY_SELECTED_VARIANTS' else None
        state = {
            'classification': classes[key]['sector']['status'] != 'CONFIRMED',
            'accounting': classes[key]['accounting']['status'] != 'CONFIRMED',
            'period': True if 'PERIOD_MISMATCH' in raw or vrows and any('TTM_PERIOD_ALIGNMENT' in r['nonprice_missing'] for r in vrows) else None if missing else False,
            'formula_applicability': True if raw & {'NOT_APPLICABLE','DOMAIN_INVALID'} else None if missing else False,
            'gate': row['gate_status'] != 'PASS',
            'peer_sample': True if any(f['score_status']=='PEER_SAMPLE_SMALL' for f in factors) or vrows and any(r['peer_sample_status']=='STRUCTURAL_PEER_SHORTFALL' for r in vrows) else None if missing else False,
            'share_basis': basis('share_basis', {'DATED_SPLIT_ADR_SHARE_BASIS_EVIDENCE','ALL_CLASS_ACTUAL_SHARES_ON_EVALUATION','ALL_CLASS_QUOTE_AND_CURRENCY_BASIS'}),
            'security_identity': basis('evaluation_security', {'SECURITY_ID_AND_DATED_IDENTITY'}),
            'price': any(r['price_inputs_pending'] for r in vrows) if vrows else basis('price', set()),
            'ev_components': basis('ev_components', {'EV_COMPONENT_PERIOD_AND_DEFINITION_RECONCILIATION','EV_NONCONTROLLING_INTEREST','EV_PREFERRED','EV_TOTAL_DEBT'})}
        for name in fields:observations[name].append((row['issuer_id'],state[name]))
    output = {}
    for unit in ('code_rows','issuers'):
        result = {}
        for name, values in observations.items():
            if unit=='issuers':
                groups={}
                for issuer,value in values:groups.setdefault(issuer,[]).append(value)
                flags=[True if True in x else None if None in x else False for x in groups.values()]
            else:flags=[v for _,v in values]
            affected=sum(v is True for v in flags);unknown=sum(v is None for v in flags)
            result[name]={'count':None if unknown else affected,'known_affected':affected,'known_not_affected':len(flags)-affected-unknown,
                'unassessed':unknown,'denominator':len(flags),'status':'NOT_MEASURED' if unknown==len(flags) and unknown else 'PARTIAL_EVIDENCE' if unknown else 'MEASURED',
                'reason':'SPECIFIC_CAUSE_NOT_PROVEN_BY_RETAINED_FIELDS' if unknown else None}
        output[unit]=result
    output['overlapping']=True
    output['gate_meaning']='UNKNOWN_OR_VALUE_EXCLUDED; SEE_SEPARATE_GATE_DECISIONS'
    output['estimated_new_totals_after_repair']=None
    return output
