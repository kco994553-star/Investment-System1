import copy
import importlib
import json
from pathlib import Path
import pytest

def api():return importlib.import_module('investment_system.qgv.theme_exposure')
def config():return json.loads((Path(__file__).parents[1]/'src/investment_system/qgv/theme_config_v1.json').read_text())
def calc(**kwargs):return api().summarize_theme_exposure(config=config(),**kwargs)

def test_fourteen_pending_baskets_never_activate_memberships_or_qgv():
    out=calc(etf_evidence={})
    assert len(out['themes'])==14 and out['role']=='EXPOSURE_ONLY'
    assert out['state']=='NOT_AVAILABLE' and out['display']==[]
    assert all(t['membership'] is None for t in out['themes'].values())
    assert not {'weights','Q','G','V','adjusted_qgv'} & set(out)

def test_supplied_nport_evidence_is_counts_weights_not_unapproved_normalization():
    out=calc(etf_evidence={'SOXX':{'held':True,'portfolio_weight':.02,'source':'SEC_NPORT'},'SMH':{'held':True,'portfolio_weight':.05,'source':'SEC_NPORT'}})
    t=out['themes']['semiconductors']
    assert t['held_etf_count']==2 and t['reported_weights']=={'SOXX':.02,'SMH':.05}
    assert t['membership'] is None

def test_literal_item1_frequency_does_not_infer_membership():
    text='Artificial intelligence supports artificial intelligence. Not semifinal or said. Cloud computing.'
    out=calc(etf_evidence={},item1_text=text)
    assert out['themes']['ai']['keyword_counts']['artificial intelligence']==2
    assert out['themes']['cloud_software']['keyword_counts']['cloud computing']==1
    assert out['themes']['ai']['membership'] is None
    assert text not in str(out)

@pytest.mark.parametrize('market',['KR','JP'])
def test_kr_jp_remain_industry_only_unavailable(market):
    out=calc(etf_evidence={},market=market,item1_text='artificial intelligence',industry_default='technology')
    assert out['industry_default']=='technology'
    assert out['themes']['ai']['keyword_counts'] is None
    assert 'DART_EDINET_NOT_CONNECTED' in out['reason_codes']

def test_device_override_top_two_and_none_are_preview():
    out=calc(etf_evidence={},overrides={'ai':.5,'semiconductors':1,'robotics_automation':.8})
    assert [r['id'] for r in out['display']]==['semiconductors','robotics_automation']
    assert out['override_role']=='DEVICE_PREVIEW'
    assert calc(etf_evidence={},overrides={})['display']==[]
    assert calc(etf_evidence={},overrides={'ai':0})['display']==[]

@pytest.mark.parametrize('overrides',[{'no_theme':1},{'ai':1.1},{'ai':True},{'ai':float('nan')}])
def test_invalid_overrides_have_fixed_errors(overrides):
    with pytest.raises(ValueError,match='OVERRIDE_INVALID'):calc(etf_evidence={},overrides=overrides)

@pytest.mark.parametrize('evidence',[{'SOXX':{'held':True,'portfolio_weight':2,'source':'SEC_NPORT'}},{'SOXX':{'held':True,'portfolio_weight':.1,'source':'OTHER'}},{'SOXX':{'held':False,'portfolio_weight':.1,'source':'SEC_NPORT'}}])
def test_invalid_supplied_evidence_is_not_used(evidence):
    out=calc(etf_evidence=evidence)
    assert out['themes']['semiconductors']['held_etf_count'] is None
    assert 'ETF_EVIDENCE_INVALID' in out['themes']['semiconductors']['reason_codes']

def test_mutation_free_and_configuration_names_not_hardcoded():
    x=config();before=copy.deepcopy(x);x['themes'][0]['name']='Custom label'
    out=api().summarize_theme_exposure(config=x,etf_evidence={})
    assert out['themes']['ai']['name']=='Custom label' and before['themes'][0]['name']=='AI'
    assert x['membership_rule'] is None

def test_duplicate_theme_and_unknown_normalization_fail_closed():
    x=config();x['themes'][1]['id']='ai'
    with pytest.raises(ValueError,match='THEME_CONFIG_INVALID'):api().summarize_theme_exposure(config=x,etf_evidence={})
    x=config();x['membership_rule']='UNAPPROVED_FORMULA'
    with pytest.raises(ValueError,match='MEMBERSHIP_RULE_UNAPPROVED'):api().summarize_theme_exposure(config=x,etf_evidence={})

def test_partial_coverage_is_distinct_from_confirmed_nonholdings():
    row={'held':False,'portfolio_weight':0,'source':'SEC_NPORT'}
    t=calc(etf_evidence={'SOXX':row})['themes']['semiconductors']
    assert t['eligible_etf_count']==1 and t['missing_etfs']==['SMH']
    t=calc(etf_evidence={'SOXX':row,'SMH':row})['themes']['semiconductors']
    assert t['eligible_etf_count']==2 and t['missing_etfs']==[]
    t=calc(etf_evidence={'SOXX':{'held':True,'portfolio_weight':2,'source':'SEC_NPORT'}})['themes']['semiconductors']
    assert t['invalid_etfs']==['SOXX'] and t['missing_etfs']==['SMH']

def test_noninteger_display_limit_has_schema_error():
    x=config();x['maximum_display']=2.0
    with pytest.raises(ValueError,match='THEME_CONFIG_INVALID'):api().summarize_theme_exposure(config=x,etf_evidence={})
