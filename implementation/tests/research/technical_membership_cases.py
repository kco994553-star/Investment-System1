"""Shared synthetic input mutations with independently specified expectations.

Paths address a deep copy of base; sets replace, removes delete. No production
result is used to choose an expected success, error, count, score or rank.
"""
from copy import deepcopy

from test_technical_filter_membership import inputs


def apply_case(base, case):
    value = deepcopy(base)
    for path, replacement in case.get('sets', []):
        parent = value
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = deepcopy(replacement)
    for path in case.get('removes', []):
        parent = value
        for key in path[:-1]:
            parent = parent[key]
        del parent[path[-1]]
    return value


def make_fixture():
    args, view, technical = inputs()
    base = dict(join=args, bundle=dict(view=view, technical=technical))
    cases = []

    def put(name, sets=(), removes=(), error=None, selected=3, audit=0, validation='VERIFIED'):
        expected = dict(ok=False, code=error) if error else dict(ok=True,
            selected_count=selected, original_group_count=0 if validation == 'VERIFIED_EMPTY' else 3,
            issuer_connections=audit, membership_validation=validation)
        cases.append(dict(id=name, sets=[[p, v] for p, v in sets], removes=list(removes), expected=expected))

    def change(path, value):
        return (['join'] + path, value)

    rows = args['qgv_rows']
    put('normal_distinct_code_display_issuer_security')
    put('member_row_missing', [change(['qgv_rows'], rows[1:])], error='GROUP_MEMBER_MISSING')
    put('duplicate_row', [change(['qgv_rows'], rows + [rows[0]])], error='DUPLICATE_GROUP_ROW')
    put('outside_group_row', [change(['qgv_rows'], rows + [dict(rows[0], code='SYNTHETIC:OUTSIDE')])], error='ROW_OUTSIDE_GROUP')
    put('roster_unknown', [change(['group_manifest', 'membership_status'], 'UNKNOWN')], error='GROUP_MEMBERSHIP_UNCONFIRMED')
    put('roster_absent', [change(['group_manifest'], None)], error='GROUP_MEMBERSHIP_REQUIRED')
    empty, ev, et = inputs(0)
    put('confirmed_empty', [(['join'], empty), (['bundle'], dict(view=ev, technical=et))], selected=0, validation='VERIFIED_EMPTY')
    shared = []
    for i in (0, 1):
        for path in (['join', 'qgv_rows', i, 'issuer_id'], ['join', 'security_links', i, 'issuer_id'],
                     ['join', 'group_manifest', 'members', i, 'issuer_id'], ['bundle', 'view', 'rows', i, 'issuer_id'],
                     ['bundle', 'technical', 'rows', i, 'issuer_id']):
            shared.append((path, 'SYNTHETIC:SHARED_ISSUER'))
    put('two_codes_one_issuer', shared)
    put('row_date_mismatch', [change(['qgv_rows', 0, 'signal_day'], '2017-01-07')], error='SIGNAL_DAY_MISMATCH')
    put('requested_date_mismatch', [change(['group_context', 'signal_day'], '2017-01-07')], error='GROUP_CONTEXT_MISMATCH:signal_day')
    put('requested_hash_mismatch', [change(['group_context', 'classification_hash'], 'b'*64)], error='GROUP_CONTEXT_MISMATCH:classification_hash')
    put('requested_population_mismatch', [change(['group_context', 'population_hash'], 'b'*64)], error='GROUP_CONTEXT_MISMATCH:population_hash')
    put('row_hash_mismatch', [change(['qgv_rows', 0, 'classification_hash'], 'b'*64)], error='ROW_CLASSIFICATION_MISMATCH')
    put('row_record_mismatch', [change(['qgv_rows', 0, 'classification_record_id'], 'SYNTHETIC:WRONG')], error='ROW_CLASSIFICATION_MISMATCH')
    put('issuer_explicit_null', [change(['qgv_rows', 0, 'issuer_id'], None)], error='ISSUER_LINK_MISMATCH')
    connection = [change(['qgv_rows', 0, 'issuer_id'], None), change(['connect_issuers'], True)]
    put('issuer_evidence_connection', connection, audit=1)
    put('issuer_connection_without_evidence', connection + [change(['group_manifest', 'members', 0, 'evidence_refs'], [])],
        error='ISSUER_CONNECTION_EVIDENCE_REQUIRED')
    put('classification_not_applicable_on_day', connection + [
        change(['group_manifest', 'membership_status'], 'UNKNOWN'),
        change(['group_manifest', 'reasons'], ['CLASSIFICATION_APPLICABILITY_UNCONFIRMED']),
        (['bundle', 'view', 'rows', 0, 'applicability', 'evaluation_date'], '2017-01-07')],
        error='GROUP_MEMBERSHIP_UNCONFIRMED')
    put('issuer_connection_conflict', [change(['qgv_rows', 0, 'issuer_id'], 'SYNTHETIC:WRONG'), change(['connect_issuers'], True)],
        error='ISSUER_CLASSIFICATION_MISMATCH')
    put('case_changed_company_code', [change(['qgv_rows', 0, 'code'], rows[0]['code'].lower())], error='ROW_OUTSIDE_GROUP')
    put('company_code_missing', removes=[['join', 'qgv_rows', 0, 'code']], error='COMPANY_CODE_REQUIRED')
    put('original_order_and_ranks', [change(['qgv_rows'], list(reversed(rows)))])
    put('median_filter_keeps_original_ranks', [change(['conditions'], [dict(metric='momentum_3m', condition='ge_median')])], selected=2)
    return dict(schema_version='technical-filter-group-fixtures/1', data_kind='SYNTHETIC',
                base=base, cases=cases,
                consumer_contract='join is the complete group, not the entire outer population; connect_issuers is explicit',
                preservation='Input objects and original score/rank fields must remain unchanged; no rank recalculation.')
