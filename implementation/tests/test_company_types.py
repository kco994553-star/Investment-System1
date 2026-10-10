import copy
import importlib
import json
from pathlib import Path
import pytest

CONFIG=Path(__file__).parents[1]/'src/investment_system/qgv/type_config_v1.json'
def raw(): return json.loads(CONFIG.read_text())
def api(): return importlib.import_module('investment_system.qgv.company_types')
def cfg_api(): return importlib.import_module('investment_system.qgv.type_config')
def calc(metrics=None, scores=None, config=None):
    return api().calculate_company_types(metrics=metrics or {}, original_qgv=scores or {'Q':70,'G':80,'V':60}, config=config or cfg_api().load_official_type_config())

@pytest.mark.parametrize('value,expected',[(.05,0),(.10,0),(.15,.5),(.20,1),(.25,1)])
def test_growth_approved_ramp(value,expected):
    out=calc({'revenue_cagr_3y':value})
    assert out['memberships']['growth']['membership']==pytest.approx(expected)
    assert out['config_status']=='OFFICIAL_PROVISIONAL'
    assert out['calibration']=='V2_PENDING'

@pytest.mark.parametrize('value',[None,True,'0.2',float('nan'),float('inf')])
def test_missing_invalid_not_zero(value):
    out=calc({'revenue_cagr_3y':value})
    assert out['memberships']['growth']['membership'] is None
    assert out['memberships']['growth']['state']=='NOT_AVAILABLE'
    assert 'TYPE_UNCONFIRMED' in out['reason_codes']

def test_known_roic_does_not_invent_quality_combination():
    out=calc({'roic':.20})
    q=out['memberships']['quality']
    assert q['membership'] is None
    assert q['components'][0]['membership']==1
    assert 'QUALITY_COMBINATION' in q['reason_codes']

def test_dividend_gate_missing_vs_false():
    assert calc({'dividend_yield':.03})['memberships']['dividend']['membership'] is None
    assert calc({'dividend_paid_5_consecutive_years':False})['memberships']['dividend']['membership']==0
    assert calc({'dividend_yield':.0225,'dividend_paid_5_consecutive_years':True})['memberships']['dividend']['membership']==pytest.approx(.5)

def test_weights_preserve_original_missing_qgv_and_no_rescale():
    out=calc({'revenue_cagr_3y':.20}, {'Q':70,'G':80,'V':None})
    assert out['original_qgv']=={'Q':70,'G':80,'V':None}
    assert out['adjusted_qgv']=={'Q':70,'G':80,'V':None}
    assert out['weights']=={'Q':30.,'G':50.,'V':20.}
    assert out['adjusted_score'] is None
    assert out['missing_pillars']==['V']

def test_all_unavailable_fallback_has_uncertainty():
    out=calc()
    assert out['selected_types']==[] and out['weights']=={'Q':34.,'G':33.,'V':33.}
    assert 'TYPE_UNCONFIRMED' in out['reason_codes']

def test_theme_never_changes_qgv():
    x=raw(); x['types'][-1]['rule']={'kind':'ramp','metric':'theme_test','lower':0,'upper':1}
    c=cfg_api().compile_custom_config(x)
    assert calc({'theme_test':1}, config=c)['weights']=={'Q':34.,'G':33.,'V':33.}

def test_custom_add_delete_rename_criteria_weights_and_no_mutation():
    official=cfg_api().load_official_type_config(); before=official.to_dict()
    x=official.to_dict();x['types']=[{'id':'custom','name':'내 유형','affects_qgv':True,'rule':{'kind':'ramp','metric':'user_metric','lower':1,'upper':2},'weights':{'Q':40,'G':20,'V':40}}]
    x['mixing']['exclusive_pairs']=[];x['value_basis']['cyclical_type']=None
    c=cfg_api().compile_custom_config(x)
    out=calc({'user_metric':2},config=c)
    assert out['role']=='PREVIEW' and out['config_status']=='CUSTOM_PREVIEW'
    assert out['selected_types']==['custom'] and out['weights']=={'Q':40.,'G':20.,'V':40.}
    x['types'][0]['name']='changed'
    assert c.to_dict()['types'][0]['name']=='내 유형' and official.to_dict()==before

def test_mixing_top_three_exclusion_and_exact_clamp_order():
    x=raw()
    for i,t in enumerate(x['types']):
        if t['affects_qgv']:t['rule']={'kind':'ramp','metric':t['id'],'lower':0,'upper':1}
    out=calc({'growth':.9,'value':.8,'cyclical':.7,'defensive':.6,'quality':.2}, config=cfg_api().compile_custom_config(x))
    assert out['selected_types']==['growth','value','cyclical']
    assert out['adjusted_qgv']['V'] is None
    assert 'NORMALIZED_EARNINGS_VALUE_REQUIRED' in out['reason_codes']
    x['types']=[{'id':'custom','name':'x','affects_qgv':True,'rule':{'kind':'rank','metric':'rank','max_rank':3},'weights':{'Q':100,'G':0,'V':0}}]
    x['mixing']['exclusive_pairs']=[];x['value_basis']['cyclical_type']=None
    out=calc({'rank':1},config=cfg_api().compile_custom_config(x))
    assert out['weights']==pytest.approx({'Q':100*60/90,'G':100*15/90,'V':100*15/90})

@pytest.mark.parametrize('mutate,code',[
    (lambda x:x['types'][0]['weights'].update(Q=31),'WEIGHT_SUM'),
    (lambda x:x['types'][0]['rule'].update(upper=.10),'RAMP_BOUNDS'),
    (lambda x:x['types'][1].update(id='growth'),'TYPE_ID_DUPLICATE'),
    (lambda x:x['types'][0]['rule'].update(kind='new_model'),'RULE_KIND'),
    (lambda x:x['mixing'].update(maximum_types=True),'MIXING_INVALID'),
    (lambda x:x['types'][0]['weights'].update(Q=float('nan')),'WEIGHT_INVALID'),
    (lambda x:x['types'][-1].update(affects_qgv=True),'THEME_QGV_FORBIDDEN'),
])
def test_schema_reason_codes(mutate,code):
    x=raw();mutate(x)
    assert code in cfg_api().validate_type_config(x)
    with pytest.raises(ValueError):cfg_api().compile_custom_config(x)

def test_official_cannot_be_mutated_and_cyclical_normalized_v_is_explicit():
    c=cfg_api().load_official_type_config()
    with pytest.raises((AttributeError,TypeError)):c.payload='{}'
    x=raw();t=next(t for t in x['types'] if t['id']=='cyclical');t['rule']={'kind':'rank','metric':'rank','max_rank':3}
    out=calc({'rank':1,'cyclical_v_score':55},config=cfg_api().compile_custom_config(x))
    assert out['adjusted_qgv']['V']==55 and out['original_qgv']['V']==60

@pytest.mark.parametrize('rank,expected',[(1,1),(3,1),(4,0),(0,None),(1.5,None),(True,None)])
def test_leader_requires_valid_rank(rank,expected):
    assert calc({'sector_marketcap_rank':rank})['memberships']['leader']['membership']==expected

def test_reserved_theme_cannot_be_promoted_by_changing_role():
    x=raw();t=x['types'][-1]
    t.update(type_role='QGV_TYPE',affects_qgv=True,weights={'Q':60,'G':20,'V':20},rule={'kind':'rank','metric':'theme_rank','max_rank':3})
    assert 'THEME_QGV_FORBIDDEN' in cfg_api().validate_type_config(x)
    with pytest.raises(ValueError,match='THEME_QGV_FORBIDDEN'):cfg_api().compile_custom_config(x)

@pytest.mark.parametrize('section,field,code', [('fallback','id','FALLBACK_INVALID'),('value_basis','cyclical_type','VALUE_BASIS_INVALID')])
def test_missing_required_fields_fail_schema_not_runtime(section,field,code):
    x=raw();del x[section][field]
    assert code in cfg_api().validate_type_config(x)
    with pytest.raises(ValueError,match=code):cfg_api().compile_custom_config(x)

def test_invalid_config_root_and_nonfinite_compile_have_fixed_reason_codes():
    with pytest.raises(ValueError,match='CONFIG_INVALID'):cfg_api().compile_custom_config([])
    x=raw();x['types'][0]['weights']['Q']=float('nan')
    with pytest.raises(ValueError,match='WEIGHT_INVALID'):cfg_api().compile_custom_config(x)
    x=raw();x['types'][0]['weights']['Q']=10**999
    assert 'WEIGHT_INVALID' in cfg_api().validate_type_config(x)
