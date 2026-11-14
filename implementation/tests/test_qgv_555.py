from copy import deepcopy
import pytest
from investment_system.research.qgv_555 import configuration, run, validate_configuration, catalog, fixture


def test_five_roles_and_fixed_budgets():
    c=configuration('U1-555'); assert c['axis_weights']==dict(Q=34,G=33,V=33)
    for a in 'QGV':
        rs=[r for r in c['roles'].values() if r['axis']==a]
        assert len(rs)==5 and sum(r['weight'] for r in rs)==100
    e,ref=fixture();out=run(c,e,ref)
    assert all(r['fifteen_roles_complete'] for r in out['rows'])
    w=out['rows'][0]['lineage'];assert sum(x['nominal'] for x in w)==pytest.approx(1)
    assert sum(x['effective'] for x in w)==pytest.approx(1)


def test_half_weight_not_strict_and_missing_not_zero():
    c=configuration('U1-555');e,ref=fixture()
    for row in e['rows']:
        row['metrics'].pop('roic');row['metrics'].pop('gross_profit_to_assets')
    out=run(c,e,ref)
    assert out['rows'][0]['roles']['q_profitability']['score'] is None
    assert out['rows'][0]['axes']['Q']['score'] is not None
    assert not out['rows'][0]['fifteen_roles_complete']


def test_unknown_gate_is_not_pass():
    c=configuration('U1-555');e,ref=fixture();e['rows'][0]['gate']=None
    r=run(c,e,ref)['rows'][0]
    assert r['gate_status']=='UNKNOWN' and r['total'] is None


def test_value_excluded_not_company_excluded():
    c=configuration('U1-555');e,ref=fixture();e['rows'][0]['gate']['percentile']=10
    r=run(c,e,ref)['rows'][0]
    assert r['gate_status']=='VALUE_EXCLUDED' and r['total'] is not None
    assert all(x['effective']==0 for x in r['lineage'] if x['axis']=='V')


def test_alias_duplicate_and_custom_three_roles():
    c=configuration('U1-555');c['roles']['v_earnings_yield']['metrics']={'ebit_yield':50,'EV_EBIT_TTM':50}
    with pytest.raises(ValueError,match='DUPLICATE'):validate_configuration(c)
    c=configuration('U1-555');c['roles']['q_moat_proxy']['weight']=0;c['roles']['q_capital_allocation']['weight']=0
    e,ref=fixture();r=run(c,e,ref)['rows'][0]
    assert r['active_roles']['Q']==3
    assert r['fifteen_roles_complete'] is False


def test_financial_never_inherits_general():
    c=configuration('S1-555');e,ref=fixture();e['rows'][0]['accounting_template']='BANK'
    r=run(c,e,ref)['rows'][0];assert r['status']=='ACCOUNTING_RECIPE_PREPARING'
    assert all(a['score'] is None for a in r['axes'].values())


def test_evaluation_reference_separate_hashes_and_date():
    c=configuration('U1-555');e,ref=fixture();r=run(c,e,ref)
    assert r['evaluation']['input_hash']!=r['reference']['input_hash']
    ref['evaluation_day']='2026-11-02'
    with pytest.raises(ValueError,match='CONTEXT'):run(c,e,ref)


def test_tags_order_do_not_change_values_and_no_automatic_duplicate_cap():
    c=configuration('U1-555');e,ref=fixture();a=run(c,e,ref)
    e['rows'].reverse();ref['rows'].reverse()
    for row in e['rows']:row['tags']=['lynch','policy','theme']
    b=run(c,e,ref)
    assert [(r['company_id'],r['total']) for r in a['rows']]==[(r['company_id'],r['total']) for r in b['rows']]
    assert a['duplicate_control']['applied']=='DISCLOSE_ONLY'
    assert a['rows'][0]['input_family_contributions']['incremental_return']['nominal']>0


def test_independent_anchor_required_when_validating_delivery():
    from investment_system.research.qgv_555 import validate_binding
    c=configuration('U1-555');e,ref=fixture();r=run(c,e,ref)
    validate_binding(r,expected_evaluation=r['evaluation'],expected_reference=r['reference'])
    bad=deepcopy(r['evaluation']);bad['input_hash']='0'*64
    with pytest.raises(ValueError,match='EVALUATION'):validate_binding(r,expected_evaluation=bad,expected_reference=r['reference'])


def test_catalog_explicit_periods_and_no_absolute_eps_value_factor():
    cats=catalog()
    assert cats['eps_cagr_3y']['period']=='FY_3Y'
    assert cats['roic']['formula_source'].endswith('v2_factors._Company.roic')
    assert not any(v.get('axis')=='V' and k in ('EPS','BPS','DPS') for k,v in cats.items())


def test_replay_uses_exact_saved_inputs():
    from investment_system.research.qgv_555 import replay
    c=configuration('U1-555');e,ref=fixture();r=run(c,e,ref)
    assert replay(r,e,ref)['rows']==r['rows']
    e['rows'][0]['metrics']['roic']+=1
    with pytest.raises(ValueError,match='INPUT'):replay(r,e,ref)


def test_fractional_weights_and_sector_axis_override():
    c=configuration('S1-555');c['sector_axis_overrides']={'INFORMATION_TECHNOLOGY':dict(Q=40.5,G=20,V=39.5)}
    c['roles']['q_profitability']['weight']=25.5
    e,ref=fixture();r=run(c,e,ref)['rows'][0]
    assert r['nominal_axis_weights']['Q']==40.5
    assert sum(x['nominal'] for x in r['lineage'])==pytest.approx(1)


def test_dictionary_not_confused_with_legacy_adapter_mapping():
    c=configuration('U1-555');e,ref=fixture();ref['classification_context']['dictionary_version']='book-sector-map/1'
    with pytest.raises(ValueError,match='CLASSIFICATION_CONTEXT'):run(c,e,ref)


def test_verified_period_aliases_and_scoped_user_override():
    c=configuration('U1-555');c['roles']['v_earnings_yield']['metrics']={'PER_TTM_DILUTED':1,'sector::ep_ttm_diluted':1}
    with pytest.raises(ValueError,match='DUPLICATE'):validate_configuration(c)
    c['roles']['v_earnings_yield']['metrics']={'PER_TTM_DILUTED':1,'PER_FY_DILUTED':1}
    validate_configuration(c)
    c=configuration('S1-555');r=deepcopy(c['roles']['q_moat_proxy']);r['weight']=0
    c['scoped_role_overrides']={'INFORMATION_TECHNOLOGY|GENERAL':{'q_moat_proxy':r}}
    e,ref=fixture();out=run(c,e,ref)
    assert out['rows'][0]['active_roles']['Q']==4
    assert c['roles']['q_moat_proxy']['weight']==20
