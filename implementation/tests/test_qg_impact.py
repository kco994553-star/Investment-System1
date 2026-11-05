from copy import deepcopy
import pytest
from investment_system.research.qg_impact import audit_g_impact
from investment_system.qgv.v2_factors import CALC_VERSION


def rows(profile='GENERAL', prefix='G'):
    return {f'{prefix}{i}': {'cik': prefix+str(i), 'state':'LIVE', 'profile':profile,
             'industry_group':'one' if i<5 else 'two', 'calc_version':CALC_VERSION,
             'metrics':{'revenue_cagr_3y':.05,'eps_cagr_3y':.02,'fcf_per_share_cagr_3y':.04,
                        'book_value_per_share_cagr_3y':.04,'incremental_roic_3y':.01,'incremental_roe_3y':.01,
                        'revenue_positive_growth_share':1,'revenue_growth_volatility':.1,'revenue_acceleration':i}}
            for i in range(10)}


def test_one_source_change_propagates_across_general_sectors_not_financials():
    before={**rows(),**rows('FINANCIAL','F')}; after=deepcopy(before)
    after['G0']['metrics']['revenue_acceleration']=9.5
    r=audit_g_impact(before,after,calc_version=CALC_VERSION)
    assert r['counts']=={'codes':20,'input_changed':1,'score_changed':10,'direct_changed':1,'indirect_changed':9,'input_changed_score_unchanged':0}
    assert r['rows']['G0']['before']['score_unrounded']==42.5
    assert r['rows']['G0']['after']['score_unrounded']==57.5
    assert r['rows']['G1']['delta_exact']=={'numerator':-5,'denominator':3}
    assert r['rows']['G1']['after']['peer_basis']=='UNIVERSE'
    assert r['rows']['G1']['after']['factor_details']['g_recent_acceleration']['submetrics'][0]['n']==10
    assert all(r['rows'][f'F{i}']['score_changed'] is False for i in range(10))
    assert r['unaffected_checks']['all_Q_unchanged']
    assert r['unaffected_checks']['financial_G_unchanged']


def test_input_change_without_crossing_a_peer_does_not_change_score():
    before=rows();after=deepcopy(before);after['G5']['metrics']['revenue_acceleration']=5.1
    r=audit_g_impact(before,after,calc_version=CALC_VERSION)
    assert r['counts']['score_changed']==0 and r['counts']['input_changed_score_unchanged']==1
    assert r['rows']['G5']['before']['score_unrounded']==r['rows']['G5']['after']['score_unrounded']


def test_duplicate_issuer_is_not_an_additional_rank_point_and_ties_are_midranked():
    before=rows();before['ALIAS']=deepcopy(before['G1']);after=deepcopy(before)
    after['G0']['metrics']['revenue_acceleration']=1
    r=audit_g_impact(before,after,calc_version=CALC_VERSION)
    item=r['rows']['G0']['after']['factor_details']['g_recent_acceleration']['submetrics'][0]
    assert item['n']==10 and item['less']==0 and item['equal']==2
    assert item['percentile_exact']=={'numerator':50,'denominator':9}
    assert r['rows']['ALIAS']['after']['score_unrounded']==r['rows']['G1']['after']['score_unrounded']


def test_peer_population_change_is_not_mislabeled_as_input_only_recovery():
    before=rows();after=deepcopy(before);after['G0']['profile']='FINANCIAL'
    with pytest.raises(ValueError,match='POPULATION'):
        audit_g_impact(before,after,calc_version=CALC_VERSION)


def test_missing_factors_keep_official_weight_gate_and_no_score_is_filled():
    before=rows();after=deepcopy(before)
    for data in (before,after):data['G0']['metrics']={'revenue_acceleration':0}
    r=audit_g_impact(before,after,calc_version=CALC_VERSION)
    assert r['rows']['G0']['before']['score_unrounded'] is None
    assert r['rows']['G0']['before']['available_weight']==15


def test_audit_does_not_apply_current_rules_to_another_calc_version():
    with pytest.raises(ValueError,match='VERSION'):
        audit_g_impact(rows(),rows(),calc_version='qgv2-calc/old.1')


def test_indirect_effect_names_the_peer_that_crossed_the_unchanged_input():
    before=rows();after=deepcopy(before);after['G0']['metrics']['revenue_acceleration']=9.5
    r=audit_g_impact(before,after,calc_version=CALC_VERSION)
    crossings=r['rows']['G1']['peer_crossings']
    assert len(crossings)==1 and crossings[0]['issuer_cik']=='G0'
    assert crossings[0]['less_delta']==-1 and crossings[0]['equal_delta']==0
    assert r['rows']['G0']['peer_crossings']==[]
