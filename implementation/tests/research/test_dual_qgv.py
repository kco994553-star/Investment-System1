"""Synthetic counterexamples for fixed-core dual boards, no real company fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from investment_system.research.sector_qgv import CATALOG, digest, default_config, preview_qgv

FIX=Path(__file__).resolve().parents[2]/'docs/research/sector_qgv/synthetic-input.json'

def inputs(n=20):
    s=json.loads(FIX.read_text());s['rows']=s['rows'][:n];s['members']=s['members'][:n]
    for i,r in enumerate(s['rows']):
        r['sector_id']='ENERGY' if i<n//2 else 'INFORMATION_TECHNOLOGY'
        for v,src in [('roa_ttm','operating_margin_ttm'),('common_bp','ep_ttm_diluted')]:
            o=deepcopy(r['observations'][src]);o.update(variant_id=v,formula_version=CATALOG[v]['formula_version'],unit=CATALOG[v]['unit'])
            o['fiscal_period']['kind']=CATALOG[v]['period'];r['observations'][v]=o
    ev=deepcopy(s);ev['rows']=ev['rows'][:3];ev['members']=ev['members'][:3];ev['universe_id']='SYN-EVALUATION'
    s['universe_id']='SYN-REFERENCE'
    return ev,s

def run(ev=None,ref=None,cid='U1'):
    from investment_system.research.dual_qgv import candidate_configs,run_board
    if ev is None:ev,ref=inputs()
    return run_board(candidate_configs()[cid],ev,ref,request_id='synthetic')

def test_common_pool_not_sector_percentiles_equal_values_same_scores():
    ev,ref=inputs();a=run(ev,ref)
    assert a['rows'][0]['factors']['roa_ttm']['valid_n']==20
    assert a['rows'][1]['factors']['roa_ttm']['score']==pytest.approx(100/19)
    assert a['rows'][0]['total']==0
    for s in (ev,ref):
        for r in s['rows']:r['sector_id']='UTILITIES'
    b=run(ev,ref)
    assert [(r['axes'],r['total'],r['rank']) for r in a['rows']]==[(r['axes'],r['total'],r['rank']) for r in b['rows']]
    sec=run(cid='S1');assert sec['rows'][0]['axes']['Q'] is None
    assert sec['rows'][0]['factors']['operating_margin_ttm']['valid_n']==10

def test_exact_thirds_gate_and_original_target_only():
    r=run();assert len(r['rows'])==3
    assert all(x['nominal_axis_weights']=={'Q':1,'G':1,'V':1} for x in r['rows'])
    assert all(x['post_gate_axis_weights']=={'Q':1/3,'G':1/3,'V':1/3} for x in r['rows'])
    assert all(x['rank_n']==3 for x in r['rows'])
    ev,ref=inputs();ev['rows'][0]['gate']=None;ref['rows'][0]['gate']=None
    r=run(ev,ref);assert r['rows'][0]['pre_gate_total']==0 and r['rows'][0]['total'] is None
    assert r['rows'][0]['gate_status']=='UNKNOWN'
    ev,ref=inputs()
    for s in (ev,ref):s['rows'][0]['gate']['q_industry_percentile']=0
    r=run(ev,ref);assert r['rows'][0]['gate_status']=='VALUE_EXCLUDED'
    assert r['rows'][0]['post_gate_axis_weights']=={'Q':.5,'G':.5,'V':0}
    assert r['rows'][0]['total']==0

def test_additional_missing_cannot_change_core():
    ev,ref=inputs();a=run(ev,ref)
    for s in (ev,ref):
        for row in s['rows']:row['observations'].pop('accruals_assets_ttm')
    b=run(ev,ref)
    assert [(r['axes'],r['total']) for r in a['rows']]==[(r['axes'],r['total']) for r in b['rows']]
    assert b['rows'][0]['factors']['accruals_assets_ttm']['kind']=='ADDITIONAL'

def test_core_missing_strict_no_issuer_fallback():
    ev,ref=inputs()
    for s in (ev,ref):s['rows'][0]['observations'].pop('common_bp')
    r=run(ev,ref);assert r['rows'][0]['axes']['V'] is None and r['rows'][0]['total'] is None
    assert 'common_bp' in r['rows'][0]['missing_factors']['V']
    assert r['rows'][0]['factors']['common_bp']['raw_value'] is None

@pytest.mark.parametrize('n',[19,20])
def test_minimum_is_factor_stage_not_raw(n):
    ev,ref=inputs(n);r=run(ev,ref);f=r['rows'][0]['factors']['roa_ttm']
    assert f['raw_value']==1 and f['valid_n']==n
    assert (f['score'] is not None)==(n==20)

def test_sector_ranking_separates_accounting_and_preserves_filter():
    from investment_system.research.dual_qgv import project_board
    ev,ref=inputs()
    for s in (ev,ref):
        for row in s['rows']:row['sector_id']='INFORMATION_TECHNOLOGY'
    r=run(ev,ref,'S1');filtered=project_board(r,[r['rows'][1]['company_id']])
    assert filtered['rows']==[r['rows'][1]]
    assert filtered['evaluation_population']==r['evaluation_population']
    assert filtered['reference_population']==r['reference_population']
    assert r['rows'][0]['ranking_scope'].endswith('INFORMATION_TECHNOLOGY|GENERAL')

def test_unknown_and_reit_not_replaced_with_general():
    ev,ref=inputs()
    for s in (ev,ref):s['rows'][0]['accounting_template']='EQUITY_REIT'
    r=run(ev,ref);assert r['rows'][0]['factors']['roa_ttm']['raw_status']=='NOT_APPLICABLE'
    assert r['rows'][0]['total'] is None
    for s in (ev,ref):s['rows'][0]['mapping']=None
    r=run(ev,ref);assert len(r['rows'])==3 and r['rows'][0]['status']=='MAPPING_UNRESOLVED'

@pytest.mark.parametrize('field,value',[('valuation_date','2026-11-01'),('as_of','2099-01-01T00:00:00Z'),('mapping_version','bad')])
def test_context_mismatch(field,value):
    ev,ref=inputs();ref[field]=value
    with pytest.raises(ValueError,match='CONTEXT'):run(ev,ref)

def test_original_target_input_and_missing_row_cannot_be_replaced():
    ev,ref=inputs();ref['rows'][0]['observations']['roa_ttm']['value']=42
    with pytest.raises(ValueError,match='TARGET_INPUT'):run(ev,ref)
    ev,ref=inputs();ref['rows'].pop(0)
    with pytest.raises(ValueError,match='TARGET_INPUT'):run(ev,ref)

def test_duplicate_issuer_never_inflates_n():
    ev,ref=inputs();ref['rows'][-1]['issuer_id']=ref['rows'][-2]['issuer_id']
    ref['rows'][-1]['observations']['roa_ttm']['issuer_id']=ref['rows'][-2]['issuer_id']
    r=run(ev,ref);assert r['rows'][0]['factors']['roa_ttm']['valid_n']==18

def test_future_input_does_not_enter_pool():
    ev,ref=inputs();ref['rows'][-1]['observations']['roa_ttm']['source_available_at']='2099-01-01T00:00:00Z'
    r=run(ev,ref);assert r['rows'][0]['factors']['roa_ttm']['valid_n']==19

def test_signed_zero_missing_not_conflated():
    ev,ref=inputs()
    for s in (ev,ref):
        for i in range(3):s['rows'][i]['observations']['roa_ttm']['value']=i-1
    r=run(ev,ref);assert [x['factors']['roa_ttm']['raw_status'] for x in r['rows']]==['VALID_NEGATIVE','VALID_ZERO','VALID']

def test_fixed_candidate_configs_not_mutated_and_alias_duplicates_rejected():
    from investment_system.research.dual_qgv import candidate_configs,validate_model
    c=candidate_configs()['U1'];d=deepcopy(c);ev,ref=inputs();run(ev,ref);assert c==d
    c['uniform_preset']['axes']['V']['earnings']['factors']={'ep_ttm_diluted':5000,'PER_TTM_DILUTED':5000}
    with pytest.raises(ValueError,match='DUPLICATE'):validate_model(c)

def test_saved_replay_exact_input_filter_and_versions():
    from investment_system.research.dual_qgv import candidate_configs,save_board,replay_board
    ev,ref=inputs();r=run(ev,ref);saved=save_board(candidate_configs()['U1'],r)
    replay=replay_board(saved,ev,ref,'replay');assert replay['rows']==r['rows']
    ref['rows'][-1]['observations']['roa_ttm']['value']=99
    with pytest.raises(ValueError,match='REPLAY'):replay_board(saved,ev,ref,'bad')

def test_stage_coverage_and_unique_issuer_overlap():
    r=run();c=r['coverage']
    assert c['denominator']=={'code_rows':3,'issuers':3,'security_ids_present':3}
    assert c['stages']['total']['issuers']==3
    assert c['target95']=={'code_rows':3,'issuers':3}
    assert c['whole_market_denominator'] is None

def test_legacy_entry_unchanged_by_dual_call():
    ev,ref=inputs();before=preview_qgv(default_config(),ref,'legacy')
    run(ev,ref);assert preview_qgv(default_config(),ref,'legacy')==before

def test_classification_context_version_and_missing_hash_fail_closed():
    ev,ref=inputs()
    for s in (ev,ref):
        s['classification_context']={'dictionary_version':'common-industry-dictionary/2','mapping_version':'common-classification-map/2','knowledge_as_of':s['as_of'],'classification_hash':'a'*64}
        for r in s['rows']:
            r['classification_record_id']='record:'+r['company_id']
            r['mapping'].update(common_classification_hash='a'*64,common_record_id=r['classification_record_id'],common_dictionary_version='common-industry-dictionary/2',common_mapping_version='common-classification-map/2',knowledge_as_of=s['as_of'])
    ref['classification_context']['dictionary_version']='different'
    with pytest.raises(ValueError,match='CLASSIFICATION_CONTEXT'):run(ev,ref)
    ref['classification_context']=deepcopy(ev['classification_context']);del ref['classification_context']['classification_hash']
    with pytest.raises(ValueError,match='CLASSIFICATION_CONTEXT'):run(ev,ref)

def test_bounded_delivery_keeps_ids_scopes_counts_and_rejects_mixed_dates():
    from investment_system.research.dual_qgv import delivery_artifacts
    a=run();b=run(cid='S1');parts=delivery_artifacts({'U1':a,'S1':b},max_bytes=60000)
    assert all(len((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode())<=60000 for v in parts.values())
    idx=parts['index.json'];assert len(idx['rows'])==3
    for x in idx['rows']:
        detail=next(r for r in parts[x['detail_file']]['rows'] if r['company_id']==x['company_id'])
        assert detail['boards']['U1']['axes']==next(r['axes'] for r in a['rows'] if r['company_id']==x['company_id'])
    b['evaluation_population']['valuation_date']='2000-01-01'
    with pytest.raises(ValueError,match='DELIVERY_CONTEXT'):delivery_artifacts({'U1':a,'S1':b})

def test_cli_pins_inputs_saved_replay_and_hash_rejection(tmp_path):
    import importlib.util,hashlib
    spec=importlib.util.spec_from_file_location('dual_cli',Path(__file__).resolve().parents[2]/'tools/sector_qgv.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    from investment_system.research.dual_qgv import candidate_configs
    ev,ref=inputs();job={'mode':'dual-study','data_kind':'SYNTHETIC','request_id':'cli'}
    for k,obj in [('evaluation_snapshot',ev),('reference_snapshot',ref),('dual_config',candidate_configs()['U1'])]:
        p=tmp_path/(k+'.json');p.write_text(json.dumps(obj));job[k]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    out=tmp_path/'out';result=cli.run(job,out,True);assert result['coverage']['stages']['total']['code_rows']==3
    saved=out/'dual-saved.json';job.pop('dual_config');job['dual_saved']={'path':str(saved),'sha256':hashlib.sha256(saved.read_bytes()).hexdigest()}
    replay=tmp_path/'replay';cli.run(job,replay,True)
    assert json.loads((out/'dual-result.json').read_text())['result_hash']==json.loads((replay/'dual-result.json').read_text())['result_hash']
    job['reference_snapshot']['sha256']='0'*64
    with pytest.raises(ValueError):cli.run(job,tmp_path/'bad',True)
