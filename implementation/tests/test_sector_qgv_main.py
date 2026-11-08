import copy
import json
from pathlib import Path
import pytest
from investment_system.research.sector_qgv import default_config,preset,preview_qgv,config_hash
from investment_system.research.sector_qgv_main import (canonical_config,editor_config,editor_tree,
    run_preview_request,display_projection,variant_id,editor_contract)

FIX=Path(__file__).parents[1]/'docs/research/sector_qgv/synthetic-input.json'

def request():
    return {'schema_version':'sector-qgv-main-request/1','request_id':'synthetic-main',
            'before_config':editor_config(default_config()),'after_config':editor_config(default_config())}

def test_editor_roundtrip_and_engine_results_are_exact():
    c=default_config();p=preset(c,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['G']['growth']['factors']={'revenue_cagr_3y':6000,'revenue_cagr_5y':4000}
    c['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    assert canonical_config(editor_config(c))==c
    s=json.loads(FIX.read_text());req=request();req['after_config']=editor_config(c)
    answer=run_preview_request(s,req);direct=preview_qgv(c,s,req['request_id'])
    assert answer['after']==direct
    assert answer['saved_config']['canonical_config_hash']==config_hash(c)
    for row,original in zip(answer['display']['after']['rows'],direct['result_rows']):
        assert {a:row[a] for a in ('Q','G','V')}==original['axes']
        assert row['total']==original['total'] and row['rank']==original['rank']
    assert answer['before']['input_hash']==answer['after']['input_hash']


def test_default_editor_contract_has_exact_cash_fcf_weights_and_required_gate():
    contract=editor_contract();tree=contract['contexts']['CONSUMER_DISCRETIONARY|GENERAL']
    assert [(r['role'],r['weight_bp']) for r in tree['roles']['V']]==[('earnings',3500),('cash',4000),('other_value',2500)]
    assert contract['canonical_policies']['gate_policy']=='official-q-percentile-required/1'
    assert contract['selection_key']=='variant_id'


def test_old_combined_cash_role_requires_explicit_rebase_not_rounding():
    e=editor_config(default_config());p=editor_tree(preset(default_config(),'CONSUMER_DISCRETIONARY','GENERAL'))
    p['roles']['V']=[{'role':'earnings','weight_bp':3500,'factors':[{'factor_id':'V_EARNINGS_YIELD','weight_bp':10000}]},
        {'role':'cash','weight_bp':6500,'factors':[{'factor_id':'V_CFO_YIELD','weight_bp':6154},{'factor_id':'V06_FCF_TO_MCAP','weight_bp':3846}]}]
    e['overrides']['CONSUMER_DISCRETIONARY|GENERAL']=p
    with pytest.raises(ValueError,match='REBASE'):canonical_config(e)


def test_unknown_gate_retained_and_ui_cannot_disable_it():
    s=json.loads(FIX.read_text());s['rows'][0]['gate']=None
    answer=run_preview_request(s,request())
    assert answer['display']['after']['rows'][0]['gate_status']=='UNKNOWN'
    assert answer['display']['after']['rows'][0]['total'] is None
    c=default_config();c['gate_policy']='NONE'
    with pytest.raises(ValueError,match='VERSION'):canonical_config(c)


def test_ambiguous_forward_id_and_alias_duplicates_are_not_merged():
    with pytest.raises(ValueError,match='AMBIGUOUS'):variant_id('V_FWD_EARNINGS_YIELD')
    assert variant_id('V_EARNINGS_YIELD')=='ep_ttm_diluted'
    assert variant_id('ep_fy_diluted')!='ep_ttm_diluted'
    e=editor_config(default_config());p=editor_tree(preset(default_config(),'INFORMATION_TECHNOLOGY','GENERAL'))
    p['roles']['V'][0]['factors']=[{'factor_id':'V_EARNINGS_YIELD','weight_bp':5000},{'factor_id':'ep_ttm_diluted','weight_bp':5000}]
    e['overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    with pytest.raises(ValueError,match='DUPLICATE'):canonical_config(e)


def test_unmapped_member_and_filter_keep_original_row_and_rank():
    s=json.loads(FIX.read_text());s['rows'][0]['mapping']=None
    a=run_preview_request(s,request());d=a['display']['after']
    assert d['denominator']==20 and len(d['rows'])==20
    assert d['rows'][0]['reason']=='MAPPING_UNRESOLVED' and d['rows'][0]['total'] is None
    assert d['computed']==0  # Other 19 remain below minimum; never discard unknown from denominator.


def test_existing_cli_accepts_editor_request_and_writes_engine_response(tmp_path):
    import hashlib
    import importlib.util
    spec=importlib.util.spec_from_file_location('sector_cli',Path(__file__).parents[1]/'tools/sector_qgv.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    req=request();p=tmp_path/'request.json';p.write_text(json.dumps(req))
    job={'mode':'normalized','data_kind':'SYNTHETIC','request_id':req['request_id'],
         'snapshot':{'path':str(FIX),'sha256':hashlib.sha256(FIX.read_bytes()).hexdigest()},
         'main_request':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}
    out=tmp_path/'result';summary=cli.run(job,out,synthetic=True)
    answer=json.loads((out/'main-response.json').read_text())
    assert answer['after']==json.loads((out/'preview.json').read_text())
    assert answer['saved_config']==json.loads((out/'saved-config.json').read_text())
    assert summary['total']==answer['after']['coverage']['total']
    job['request_id']='wrong'
    with pytest.raises(ValueError,match='REQUEST_JOB_MISMATCH'):cli.run(job,tmp_path/'rejected',synthetic=True)


def test_display_matches_main_preview_view_shape_without_rescoring():
    s=json.loads(FIX.read_text());s['rows'][0]['gate']=None;s['rows'][0]['lynch_tags']=['미분류']
    answer=run_preview_request(s,request());display=answer['display']
    assert len(display['diff']['rows'])==len(s['members'])
    assert display['diff']['rows'][0]['after']['total'] is None
    assert display['diff']['rows'][0]['common_after'] is None
    assert display['diff']['rows'][0]['after']['lynch_tags']==['미분류']
    assert set(display['diff']['rows'][0]['after']['why'])=={'Q','G','V'}
    assert display['diff']['common']==answer['diff']['common_valid']
    for row in display['diff']['rows'][1:]:
        exact=next(r for r in answer['diff']['rows'] if r['company_id']==row['company_id'])
        assert row['common_after']==exact['after_common_rank']
