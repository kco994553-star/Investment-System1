from copy import deepcopy
import pytest
from investment_system.research.qgv_555 import configuration,fixture,run,validate_configuration


def test_new_version_preserves_original_configuration_and_marks_target():
    a=configuration('U1-555');b=configuration('U1-555',version='0.2.0')
    assert a['model_id']=='unified-555/0.1.0' and 'growth_efficiency_policy' not in a
    assert b['model_id']=='unified-555/0.2.0'
    e,r=fixture();out=run(b,e,r)
    assert out['coverage']['all15_reference_only'] and out['coverage']['eligible_total']==21
    bad=deepcopy(a);bad.update(growth_efficiency_policy=b['growth_efficiency_policy'])
    with pytest.raises(ValueError):validate_configuration(bad)
    b['roles']['q_capital_allocation']['weight']=0
    out=run(b,e,r)
    assert out['coverage']['all15']==0 and out['coverage']['eligible_total']==21


def test_growth_fallback_only_when_primary_raw_unavailable_and_records_variant():
    e,r=fixture();c=configuration('U1-555',version='0.2.0')
    e['rows'][0]['metrics'].pop('incremental_roic_3y')
    out=run(c,e,r);fallback=out['rows'][0]['roles']['g_growth_efficiency']['metrics'][0]
    assert fallback['metric']=='sector::roa_improvement_3y'
    assert fallback['selection_reason']=='PRIMARY_RAW_UNAVAILABLE_ROA_FALLBACK'
    assert fallback['substitute_for']=='incremental_roic_3y' and 'SUBSTITUTE_METRIC' in fallback['display_flags']
    assert out['rows'][1]['roles']['g_growth_efficiency']['metrics'][0]['metric']=='incremental_roic_3y'
    for x in r['rows'][1:]:x['metrics'].pop('incremental_roic_3y')
    e['rows'][0]['metrics']['incremental_roic_3y']=1
    out=run(c,e,r);v=out['rows'][0]['roles']['g_growth_efficiency']['metrics'][0]
    assert v['metric']=='incremental_roic_3y' and v['reason']=='PEER_SAMPLE_SMALL'


def test_explicit_alternative_is_not_double_counted_by_fallback():
    e,r=fixture();c=configuration('U1-555',version='0.2.0')
    c['roles']['g_growth_efficiency']['metrics']['sector::roa_improvement_3y']=1
    e['rows'][0]['metrics'].pop('incremental_roic_3y')
    out=run(c,e,r);metrics=out['rows'][0]['roles']['g_growth_efficiency']['metrics']
    assert len({m['metric'] for m in metrics})==2
    assert metrics[0]['score'] is None and metrics[1]['score'] is not None


def test_accounting_recipes_distinguish_interim_reit_from_unfinished_ffo():
    from investment_system.research.qgv_555 import accounting_recipes
    old={x['accounting_template']:x for x in accounting_recipes()}
    new={x['accounting_template']:x for x in accounting_recipes(version='0.2.0')}
    assert old['EQUITY_REIT']['state']=='PREPARING'
    assert new['EQUITY_REIT']['state']=='TEMPORARY_GENERAL'
    assert new['EQUITY_REIT']['permanent_ffo_affo_recipe']=='PREPARING'


def test_reit_general_is_explicit_and_financial_stays_reference_only():
    e,r=fixture();c=configuration('S1-555',version='0.2.0')
    for s in (e,r):
        for row in s['rows']:
            row.update(accounting_template='EQUITY_REIT',calculation_accounting_template='GENERAL',
                calculation_sector_id=row['sector_id'],calculation_industry_group=row['industry_group'],
                owner_source_context={'source_hash':'synthetic'},
                temporary_classification={'status':'TEMPORARY_REIT_GENERAL',
                    'label':'REIT 임시(일반기업 식)','source_refs':['SYNTHETIC']})
    out=run(c,e,r)
    assert out['rows'][0]['original_accounting_template']=='EQUITY_REIT'
    assert out['rows'][0]['accounting_template']=='GENERAL'
    assert out['rows'][0]['axes']['Q']['score'] is not None
    assert 'REIT_PROVISIONAL' in out['rows'][0]['display_flags']
    e['rows'][0]['calculation_accounting_template']=None
    e['rows'][0]['financial_reference']={'source_model':'official23.1','Q':99}
    out=run(c,e,r)
    assert out['rows'][0]['axes']['Q']['score'] is None
    assert out['rows'][0]['financial_reference']['Q']==99
    assert 'TEMPORARY_OFFICIAL_PROXY' in out['rows'][0]['display_flags']


def test_temporary_sector_missing_blocks_s1_but_not_u1():
    e,r=fixture()
    for s in (e,r):
        for row in s['rows']:row['sector_id']=None
    assert run(configuration('U1-555',version='0.2.0'),e,r)['coverage']['axes']['Q']==21
    out=run(configuration('S1-555',version='0.2.0'),e,r)
    assert out['coverage']['axes']['Q']==0
    assert out['rows'][0]['status']=='SECTOR_CLASSIFICATION_UNCONFIRMED'
    assert out['coverage']['growth_efficiency_scored']['incremental_roic_3y']==0
    from investment_system.research.qgv_555_additional import attach
    attached=attach(out,e,r)
    assert attached['rows'][0]['factors']['sector::roa_ttm']['reason']=='SECTOR_CLASSIFICATION_UNCONFIRMED'


def test_central_v_share_basis_does_not_accept_actual_outstanding_label():
    e,r=fixture();c=configuration('U1-555',version='0.2.0')
    for m in ('ebit_yield','fcf_yield','own_history','gap'):
        e['rows'][0]['metric_evidence']['central::'+m]['share_basis']='ACTUAL_OUTSTANDING'
    out=run(c,e,r)
    assert out['rows'][0]['axes']['V']['score'] is None
    assert out['rows'][0]['roles']['v_earnings_yield']['metrics'][0]['reason']=='VALUATION_SHARE_BASIS_UNVERIFIED'
