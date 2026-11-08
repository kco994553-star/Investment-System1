"""Membership omission and evidence substitution must fail before filtering."""
from copy import deepcopy

import pytest

from investment_system.research import technical_filter_join as join
from investment_system.research.sector_qgv import digest
from test_common_classification_technical_macro import fixture, group
from investment_system.research.common_classification.technical_macro import technical_groups


def inputs(count=3):
    view, measures, links = fixture(count)
    view.update(universe_id='SYNTHETIC:UNIVERSE', universe_version='SYNTHETIC:VERSION:1')
    for row in view['rows']:
        row['applicability'] = dict(kind='EVALUATION_ONLY', evaluation_date=view['valuation_date'], valid_from=None, valid_to=None)
    technical = technical_groups(view, measures, links, price_basis='RAW')
    board = group(technical)['board']
    context = dict(signal_day=view['valuation_date'], group_id=board['group_id'],
        classification_hash=view['classification_hash'], population_hash=board['population_hash'],
        universe_id=view['universe_id'], universe_version=view['universe_version'],
        universe_members_hash=digest(sorted(view['members'])), dictionary_version=view['dictionary_version'],
        mapping_version=view['mapping_version'], knowledge_as_of=view['knowledge_as_of'], price_basis='RAW')
    members = [dict(company_id=r['company_id'], issuer_id=r['issuer_id'], classification_record_id=r['record_id'],
                    security_id=l['security_id'], evidence_refs=r['sector']['evidence_refs'])
               for r, l in zip(view['rows'], links)]
    manifest = dict(schema_version='technical-filter-membership/1', data_kind='SYNTHETIC',
                    context=deepcopy(context), membership_status='CONFIRMED', reasons=[], members=members)
    rows = [dict(id=f'SYNTHETIC:DISPLAY:{i}', code=r['company_id'], issuer_id=r['issuer_id'], ticker=l['symbol'],
                 security_id=l['security_id'], signal_day=view['valuation_date'],
                 score={'total':80-i}, rank={'official':20-i,'of':504})
            for i,(r,l) in enumerate(zip(view['rows'],links))]
    return dict(board=board,qgv_rows=rows,security_links=links,conditions=[dict(metric='momentum_3m',condition='gt_zero')],
                data_kind='SYNTHETIC',group_manifest=manifest,group_context=context), view, technical


def test_omitted_member_is_refused_by_common_join_even_if_it_would_not_survive_filter():
    args, _, _ = inputs()
    args['qgv_rows'] = args['qgv_rows'][1:]
    with pytest.raises(ValueError, match='^GROUP_MEMBER_MISSING$'):
        join.join_filtered_rows(**args)


@pytest.mark.parametrize('change,error', [
    ('duplicate_row','DUPLICATE_GROUP_ROW'),('outside','ROW_OUTSIDE_GROUP'),
    ('duplicate_manifest','DUPLICATE_GROUP_MEMBER'),('unknown','GROUP_MEMBERSHIP_UNCONFIRMED'),
    ('date','GROUP_CONTEXT_MISMATCH:signal_day'),('hash','GROUP_CONTEXT_MISMATCH:classification_hash'),
    ('population','GROUP_CONTEXT_MISMATCH:population_hash'),('group','GROUP_CONTEXT_MISMATCH:group_id'),
    ('row_date','SIGNAL_DAY_MISMATCH'),('row_hash','ROW_CLASSIFICATION_MISMATCH'),
    ('row_record','ROW_CLASSIFICATION_MISMATCH'),('issuer_conflict','ISSUER_CLASSIFICATION_MISMATCH'),
    ('case_changed_code','ROW_OUTSIDE_GROUP'),('missing_code','COMPANY_CODE_REQUIRED'),
])
def test_strict_boundaries(change,error):
    a,_,_=inputs()
    if change=='duplicate_row':a['qgv_rows'].append(deepcopy(a['qgv_rows'][0]))
    elif change=='outside':a['qgv_rows'].append(dict(a['qgv_rows'][0],code='SYNTHETIC:OUTSIDE'))
    elif change=='duplicate_manifest':a['group_manifest']['members'].append(deepcopy(a['group_manifest']['members'][0]))
    elif change=='unknown':a['group_manifest'].update(membership_status='UNKNOWN',reasons=['SYNTHETIC:UNKNOWN'])
    elif change in ('date','hash','population','group'):
        k={'date':'signal_day','hash':'classification_hash','population':'population_hash','group':'group_id'}[change]
        a['group_context'][k]='2017-01-07' if change=='date' else ('b'*64 if change in ('hash','population') else 'OTHER')
    elif change=='row_date':a['qgv_rows'][0]['signal_day']='2017-01-07'
    elif change=='row_hash':a['qgv_rows'][0]['classification_hash']='b'*64
    elif change=='row_record':a['qgv_rows'][0]['classification_record_id']='SYNTHETIC:WRONG'
    elif change=='issuer_conflict':a['qgv_rows'][0]['issuer_id']='SYNTHETIC:OTHER'
    elif change=='case_changed_code':a['qgv_rows'][0]['code']=a['qgv_rows'][0]['code'].lower()
    elif change=='missing_code':del a['qgv_rows'][0]['code']
    with pytest.raises(ValueError,match='^'+error+'$'):join.join_group_rows(**a,connect_issuers=True)


def test_empty_confirmed_differs_from_unknown_and_missing_manifest():
    a,_,_=inputs(0)
    assert join.join_group_rows(**a)['membership_validation']=='VERIFIED_EMPTY'
    a['group_manifest']['membership_status']='UNKNOWN'
    with pytest.raises(ValueError,match='GROUP_MEMBERSHIP_UNCONFIRMED'):join.join_group_rows(**a)
    a['group_manifest']=None
    with pytest.raises(ValueError,match='GROUP_MEMBERSHIP_REQUIRED'):join.join_group_rows(**a)


def test_issuer_connection_is_explicit_and_traceable_without_mutating_original():
    a,_,_=inputs();a['qgv_rows'][0]['issuer_id']=None;before=deepcopy(a)
    with pytest.raises(ValueError,match='ISSUER_LINK_MISMATCH'):join.join_group_rows(**a)
    out=join.join_group_rows(**a,connect_issuers=True)
    assert a==before and out['membership_validation']=='VERIFIED'
    assert out['rows'][0]['issuer_id']=='SYNTHETIC:ISSUER:0'
    assert out['issuer_connections'][0]['previous_issuer_id'] is None
    assert out['issuer_connections'][0]['classification_record_id']=='SYNTHETIC:RECORD:0'
    assert out['issuer_connections'][0]['classification_hash']=='a'*64
    assert out['issuer_connections'][0]['signal_day']=='2017-01-06'
    a['group_manifest']['members'][0]['evidence_refs']=[]
    with pytest.raises(ValueError,match='ISSUER_CONNECTION_EVIDENCE_REQUIRED'):
        join.join_group_rows(**a,connect_issuers=True)


def test_one_issuer_multiple_codes_keep_original_scores_ranks_and_order():
    a,_,_=inputs()
    for i in (0,1):
        a['qgv_rows'][i]['issuer_id']='SYNTHETIC:SHARED'
        a['security_links'][i]['issuer_id']='SYNTHETIC:SHARED'
        a['group_manifest']['members'][i]['issuer_id']='SYNTHETIC:SHARED'
    a['qgv_rows'].reverse();before=deepcopy(a)
    out=join.join_group_rows(**a)
    assert out['rows']==before['qgv_rows'] and a==before
    assert [r['rank']['official'] for r in out['rows']]==[18,19,20]


def test_legacy_call_remains_identity_only_and_does_not_claim_completeness():
    a,_,_=inputs();a.pop('group_manifest');a.pop('group_context')
    a['qgv_rows']=a['qgv_rows'][1:]
    assert len(join.join_filtered_rows(**a))==2
    with pytest.raises(ValueError,match='GROUP_MEMBERSHIP_REQUIRED'):join.join_group_rows(**a)


def test_manifest_builder_uses_classification_members_not_available_measurements():
    from investment_system.research.common_classification.group_join import build_group_manifest
    a,view,technical=inputs()
    made=build_group_manifest(view,technical,a['board']['group_id'])
    assert made==a['group_manifest']
    shortened=deepcopy(technical);shortened['rows']=shortened['rows'][1:]
    with pytest.raises(ValueError,match='GROUP_PROJECTION_MEMBERS_MISMATCH'):
        build_group_manifest(view,shortened,a['board']['group_id'])


def test_missing_measurements_do_not_remove_expected_members():
    from investment_system.research.common_classification.group_join import build_group_manifest
    a,view,_=inputs()
    technical=technical_groups(view, [], a['security_links'], price_basis='RAW')
    a['board']=group(technical)['board']
    a['group_manifest']=build_group_manifest(view,technical,a['board']['group_id'])
    out=join.join_group_rows(**a)
    assert out['original_group_count']==3 and out['selected_count']==0
    assert len(a['group_manifest']['members'])==3
    a['qgv_rows']=a['qgv_rows'][1:]
    with pytest.raises(ValueError,match='GROUP_MEMBER_MISSING'):join.join_group_rows(**a)


@pytest.mark.parametrize('change,error', [('hash','GROUP_PROJECTION_CONTEXT_MISMATCH:classification_hash'),
    ('date','GROUP_PROJECTION_CONTEXT_MISMATCH:valuation_date'), ('sector','GROUP_PROJECTION_RECORD_MISMATCH')])
def test_builder_refuses_projection_context_and_record_substitution(change,error):
    from investment_system.research.common_classification.group_join import build_group_manifest
    a,view,t=inputs()
    if change=='hash':t['classification_hash']='b'*64
    elif change=='date':t['valuation_date']='2017-01-07'
    else:t['rows'][0]['sector_id']='ENERGY'
    with pytest.raises(ValueError,match='^'+error+'$'):build_group_manifest(view,t,a['board']['group_id'])


def test_builder_does_not_enrich_from_inapplicable_classification_record():
    from investment_system.research.common_classification.group_join import build_group_manifest
    a,view,t=inputs();view['rows'][0]['applicability']['evaluation_date']='2017-01-07'
    a['group_manifest']=build_group_manifest(view,t,a['board']['group_id'])
    assert 'CLASSIFICATION_APPLICABILITY_UNCONFIRMED' in a['group_manifest']['reasons']
    a['qgv_rows'][0]['issuer_id']=None
    with pytest.raises(ValueError,match='GROUP_MEMBERSHIP_UNCONFIRMED'):
        join.join_group_rows(**a,connect_issuers=True)


def test_empty_sector_retains_nonempty_original_universe_and_unknown_is_not_empty():
    from investment_system.research.common_classification.group_join import build_group_manifest
    a,view,t=inputs()
    a['board']=next(g['board'] for g in t['groups'] if g['sector_id']=='ENERGY')
    a['qgv_rows']=[]
    a['group_manifest']=build_group_manifest(view,t,a['board']['group_id'])
    a['group_context']=deepcopy(a['group_manifest']['context'])
    assert a['group_context']['universe_members_hash']==digest(sorted(view['members']))
    assert join.join_group_rows(**a)['membership_validation']=='VERIFIED_EMPTY'
    view['rows'][0]['sector'].update(id=None,status='UNKNOWN',reasons=['SYNTHETIC:UNCLASSIFIED'])
    unknown=technical_groups(view,[],a['security_links'],price_basis='RAW')
    manifest=build_group_manifest(view,unknown,a['board']['group_id'])
    assert manifest['membership_status']=='UNKNOWN'
    assert 'CLASSIFICATION_POPULATION_INCOMPLETE' in manifest['reasons']


def test_truncated_manifest_cannot_hide_a_member_present_on_the_board():
    a,_,_=inputs();a['group_manifest']['members']=a['group_manifest']['members'][1:]
    a['qgv_rows']=a['qgv_rows'][1:]
    with pytest.raises(ValueError,match='BOARD_MEMBERSHIP_MISMATCH'):join.join_group_rows(**a)
