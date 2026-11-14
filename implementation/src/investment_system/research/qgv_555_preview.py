"""Pure, network-free UI adapter. Calls the existing 555 engine, never a UI formula."""
from copy import deepcopy
from .qgv_555 import run, identity, validate_binding, _bindings, catalog, SPECS
from .sector_qgv import digest


def selectable_metrics(role, template):
    if role not in SPECS:
        raise ValueError('ROLE_ID')
    # Empty catalog.roles means no default assignment, not unsuitable for users.
    return [key for key, item in catalog().items()
            if item['axis'] == role[0].upper() and template in item['accounting_scope']]


def _weights(row):
    nominal = row['lineage']
    available = {role: {m['metric'] for m in data['metrics'] if m['score'] is not None}
                 for role, data in row['roles'].items()}
    axis_weights = row['nominal_axis_weights'] or {}
    valid_axes = {a for a in axis_weights if row['axes'][a]['score'] is not None}
    axis_total = sum(axis_weights[a] for a in valid_axes)
    projected = []
    for item in nominal:
        axis, role, metric = item['axis'], item['role'], item['metric']
        active_roles = {r for r, v in row['roles'].items()
                        if r.startswith(axis.lower()) and v['score'] is not None}
        role_budget = sum(x['nominal'] for x in nominal if x['role'] == role)
        valid_role_budget = sum(x['nominal'] for x in nominal if x['role'] in active_roles)
        valid_metric_budget = sum(x['nominal'] for x in nominal
                                  if x['role'] == role and x['metric'] in available[role])
        pre = 0.0
        if axis in valid_axes and metric in available[role] and axis_total and valid_role_budget and valid_metric_budget:
            pre = axis_weights[axis] / axis_total * role_budget / valid_role_budget * item['nominal'] / valid_metric_budget
        projected.append(dict(item, missing_redistributed_before_gate=pre,
                              after_gate=item['effective']))
    return projected


def preview(request, evaluation, reference, *, expected_evaluation, expected_reference,
            saved_before=None):
    if request.get('schema_version') != 'qgv-555-preview-request/1' or not request.get('request_id'):
        raise ValueError('PREVIEW_REQUEST')
    if identity(evaluation) != expected_evaluation or identity(reference) != expected_reference:
        raise ValueError('INDEPENDENT_INPUT_ANCHOR')
    before_config, after_config = request['before'], request['after']
    if before_config['model_id'] != after_config['model_id']:
        raise ValueError('SEPARATE_MODEL_COMPARISON_REQUIRED')
    if saved_before is None:
        before = run(before_config, evaluation, reference)
    else:
        validate_binding(saved_before, expected_evaluation=expected_evaluation, expected_reference=expected_reference)
        if saved_before['configuration'] != before_config or saved_before['bindings'] != _bindings(before_config, evaluation, reference):
            raise ValueError('SAVED_ENGINE_OR_CONFIGURATION_MISMATCH')
        before = saved_before
    after = before if before_config == after_config else run(after_config, evaluation, reference)
    rows = []
    for a, b in zip(before['rows'], after['rows']):
        if a['company_id'] != b['company_id']:
            raise ValueError('EVALUATION_ROW_MISMATCH')
        delta = {}
        for axis in 'QGV':
            x, y = a['axes'][axis]['score'], b['axes'][axis]['score']
            delta[axis] = dict(before=x, after=y,
                difference=y-x if x is not None and y is not None else None,
                transition='COMMON' if x is not None and y is not None else
                    'NEWLY_COMPUTABLE' if y is not None else 'LOST' if x is not None else 'UNAVAILABLE_BOTH')
        rows.append(dict(company_id=a['company_id'], issuer_id=a['issuer_id'], axes=delta,
            before=dict(total=a['total'], partial_total=a['partial_total'], rank=a['rank'],
                        active_roles=a['active_roles'], weights=_weights(a), families=a['input_family_contributions']),
            after=dict(total=b['total'], partial_total=b['partial_total'], rank=b['rank'],
                       active_roles=b['active_roles'], weights=_weights(b), families=b['input_family_contributions'])))
    out = dict(schema_version='qgv-555-preview/1', request_id=request['request_id'],
        request_hash=digest(request), evaluation=deepcopy(expected_evaluation), reference=deepcopy(expected_reference),
        effect_scope='SETTINGS_ONLY_FIXED_INPUT_AND_POPULATIONS', population_effect='NOT_EVALUATED',
        before_result_hash=before['result_hash'], after_result_hash=after['result_hash'],
        before_calculated_at=before['calculated_at'], after_calculated_at=after['calculated_at'],
        before_coverage=before['coverage'], after_coverage=after['coverage'], rows=rows,
        after_result=after, official=False, visibility='AUTHENTICATED_RESEARCH',
        server_resolves_inputs=True, public_publication_authorized=False)
    out['result_hash'] = digest(out)
    return out


def top500_view(result):
    """Allowlisted private display projection. Does not grant publication rights."""
    if result.get('schema_version') != 'top500-selection/1' or result.get('result_hash') != digest({k:v for k,v in result.items() if k != 'result_hash'}):
        raise ValueError('TOP500_RESULT_HASH')
    ranks = {r['issuer_id']:i+1 for i,r in enumerate(result['ranked'])}
    out = {k:deepcopy(result[k]) for k in ('population_id','population_version','evaluation_day',
        'input_cutoff','apply_at','status','denominator','target_count','selected_count','boundary_uncertain','reasons')}
    out.update(schema_version='top500-view/1', source_result_hash=result['result_hash'],
        visibility='AUTHENTICATED_RESEARCH', public_publication_authorized=False,
        retained_confirmed_available=result.get('retained_confirmed') is not None,
        members=[dict(issuer_id=r['issuer_id'],representative_security_id=r['representative_security_id'],
                      selection_rank=ranks[r['issuer_id']],economic_class_count=len(r['economic_classes'])) for r in result['members']],
        official=False, replace_official=False)
    out['view_hash'] = digest(out)
    return out


def preview_page(result, *, offset=0, limit=20):
    """Bound transport after the complete calculation; never alters its population."""
    from .dual_qgv import json_bytes
    from .dual_qgv_delivery import MAX_BYTES
    if type(offset) is not int or type(limit) is not int or offset<0 or not 1<=limit<=50:
        raise ValueError('PREVIEW_PAGE_RANGE')
    if result.get('result_hash') != digest({k:v for k,v in result.items() if k!='result_hash'}):
        raise ValueError('PREVIEW_RESULT_HASH')
    out={k:deepcopy(result[k]) for k in ('schema_version','request_id','request_hash','evaluation','reference',
        'effect_scope','population_effect','before_result_hash','after_result_hash','before_calculated_at',
        'after_calculated_at','before_coverage','after_coverage','visibility','official')}
    out.update(schema_version='qgv-555-preview-page/1',source_preview_hash=result['result_hash'],
               offset=offset,rows=deepcopy(result['rows'][offset:offset+limit]),row_count=len(result['rows']),
               next_offset=offset+limit if offset+limit<len(result['rows']) else None)
    if len(json_bytes(out))>MAX_BYTES:raise ValueError('PREVIEW_PAGE_SIZE_REDUCE_LIMIT')
    return out
