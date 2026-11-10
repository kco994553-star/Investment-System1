"""Separate target/reference contracts; synthetic hand expectations only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from investment_system.research.sector_qgv import default_config, preview_qgv

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/'docs/research/sector_qgv/synthetic-input.json'
QG=('operating_margin_ttm','accruals_assets_ttm','debt_assets','revenue_cagr_3y','roa_improvement_3y')

def inputs(n=3):
    ref=json.loads(FIX.read_text());ev=copy.deepcopy(ref)
    ev['rows']=ev['rows'][:n];ev['members']=ev['members'][:n]
    ev['universe_id']='SYN-EVAL';ref['universe_id']='SYN-REFERENCE-SOURCE'
    for s in (ev,ref):
        s['classification_context']={'dictionary_version':'synthetic/1','mapping_version':'synthetic/1','knowledge_as_of':s['as_of']}
    c=default_config()
    p=dict(schema_version='sector-qgv-reference-plan/1',study_id='SYN-REF-01',version='1',
       policy='research-reference-additive/1',reference_id='SYN-REF',reference_version='1',minimum=20,
       eligible_groups=[dict(sector_id='INFORMATION_TECHNOLOGY',accounting_template='GENERAL',variant_id=v) for v in QG])
    return c,ev,preview_qgv(c,ev,'base'),ref,preview_qgv(c,ref,'source'),p

def run(args):
    from investment_system.research.sector_qgv_reference import run_reference_study
    return run_reference_study(*args,request_id='study')

def test_targets_preserved_only_declared_reference_factors_admitted():
    args=inputs();old=copy.deepcopy(args);r=run(args)
    assert args==old
    assert len(r['result_rows'])==3 and {x['company_id'] for x in r['result_rows']}==set(args[1]['members'])
    assert r['reference_population']['additional_issuers']==17
    assert r['comparison']['axes']['Q']['gained_rows']==3
    assert r['comparison']['axes']['G']['gained_rows']==3
    assert r['comparison']['new_any_axis_issuers']==3  # not Q3 + G3
    assert all(x['factors']['operating_margin_ttm']['valid_n']==20 for x in r['result_rows'])
    assert all(x['factors']['ep_ttm_diluted']['valid_n']==3 for x in r['result_rows'])
    assert all(x['total'] is None and x['rank'] is None for x in r['result_rows'])
    # Existing endpoint-scaled midrank: unique minimum 0, second is 100/19.
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['score']==0
    assert r['result_rows'][1]['factors']['operating_margin_ttm']['score']==pytest.approx(100/19)

def test_overlap_cannot_replace_evaluation_input_or_supply_missing_target():
    a=list(inputs());a[3]['rows'][0]['observations']['operating_margin_ttm']['value']=999
    a[4]=preview_qgv(a[0],a[3],'source2');r=run(a)
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['raw_value']==1
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['score']==0
    assert r['admission']['reason_counts']['EVALUATION_ISSUER_RETAINED']==3

def test_minimum_19_remains_blocked_without_erasing_raw():
    a=list(inputs());a[3]['rows'].pop();a[3]['members'].pop();a[4]=preview_qgv(a[0],a[3],'s')
    r=run(a);f=r['result_rows'][0]['factors']['operating_margin_ttm']
    assert f['valid_n']==19 and f['raw_value']==1 and f['score'] is None
    assert f['score_status']=='PEER_SAMPLE_SMALL'

@pytest.mark.parametrize('field,value',[('valuation_date','2026-11-01'),('as_of','2026-11-03T00:00:00Z'),('mapping_version','bad')])
def test_context_mismatch_rejected(field,value):
    a=list(inputs());a[3][field]=value
    with pytest.raises(ValueError,match='CONTEXT|IDENTITY'):run(a)

@pytest.mark.parametrize('mutation,reason',[
    ('future','NOT_YET_AVAILABLE'),('period','PERIOD_MISMATCH'),('evidence','EVIDENCE_MISSING'),
    ('mapping','MAPPING_UNRESOLVED')])
def test_reference_invalid_factor_does_not_enter_n(mutation,reason):
    a=list(inputs());row=a[3]['rows'][-1];o=row['observations']['operating_margin_ttm']
    if mutation=='future':o['source_available_at']='2099-01-01T00:00:00Z'
    elif mutation=='period':o['fiscal_period']['kind']='FY'
    elif mutation=='evidence':o['provenance']=[]
    else:row['mapping']['evidence_refs']=[]
    a[4]=preview_qgv(a[0],a[3],'s');r=run(a)
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['valid_n']==19
    assert any(reason in x['reasons'].values() or x['reason']==reason for x in r['admission']['rows'])

def test_duplicate_reference_issuer_requires_one_evidenced_representative():
    a=list(inputs());extra=copy.deepcopy(a[3]['rows'][-1]);extra['company_id']='other-code'
    a[3]['rows'].append(extra);a[3]['members'].append('other-code');a[4]=preview_qgv(a[0],a[3],'s')
    r=run(a);assert r['result_rows'][0]['factors']['operating_margin_ttm']['valid_n']==19
    assert r['admission']['reason_counts']['ISSUER_REPRESENTATIVE_UNRESOLVED']==2
    a[3]['rows'][-1].update(scoring_representative=True,representative_evidence=['synthetic:class'])
    a[4]=preview_qgv(a[0],a[3],'s2');r=run(a)
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['valid_n']==20

def test_target_class_rows_not_dropped_and_filter_cannot_rescore():
    from investment_system.research.sector_qgv_reference import project_reference_rows
    a=list(inputs());extra=copy.deepcopy(a[1]['rows'][0]);extra['company_id']='second-code'
    a[1]['rows'][0].update(scoring_representative=True,representative_evidence=['synthetic:class'])
    a[1]['rows'].append(extra);a[1]['members'].append(extra['company_id']);a[2]=preview_qgv(a[0],a[1],'b')
    r=run(a);assert len(r['result_rows'])==4
    original=copy.deepcopy(r);one=project_reference_rows(r,[r['result_rows'][0]['company_id']])
    assert one['reference_population']==r['reference_population'] and r==original
    assert one['result_rows'][0]==r['result_rows'][0]
    assert one['evaluation_population']['code_rows']==4

def test_save_replay_hash_separates_populations_no_latest_substitution():
    from investment_system.research.sector_qgv_reference import save_reference_settings,replay_reference_study
    a=list(inputs());r=run(a);saved=save_reference_settings(a[0],a[5],r)
    rr=replay_reference_study(saved,*a[1:5],request_id='replay')
    assert rr['result_rows']==r['result_rows'] and rr['cache_key']==r['cache_key']
    b=copy.deepcopy(a);b[3]['rows'].pop();b[3]['members'].pop();b[4]=preview_qgv(b[0],b[3],'s')
    with pytest.raises(ValueError,match='REPLAY'):replay_reference_study(saved,*b[1:5],request_id='bad')
    fresh=run(b);assert fresh['cache_key']!=r['cache_key']
    assert fresh['evaluation_population']==r['evaluation_population']

def test_cli_pins_all_files_and_writes_replay_contract(tmp_path):
    a=inputs();job={'mode':'reference-study','data_kind':'SYNTHETIC','request_id':'study','config':a[0]}
    for name,data in zip(('evaluation_snapshot','evaluation_preview','reference_snapshot','reference_preview','reference_plan'),a[1:]):
        p=tmp_path/(name+'.json');p.write_text(json.dumps(data))
        job[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    spec=importlib.util.spec_from_file_location('ref_cli',ROOT/'tools/sector_qgv.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    result=cli.run(job,tmp_path/'out',True)
    assert result['evaluation_denominator']==3
    assert (tmp_path/'out/reference-settings.json').exists()
    job['reference_snapshot']['sha256']='0'*64
    with pytest.raises(ValueError):cli.run(job,tmp_path/'bad',True)
    assert not (tmp_path/'bad').exists()


def test_total_rank_only_counts_targets_when_reference_only_rows_also_have_totals():
    from investment_system.research.sector_qgv import preset
    a=list(inputs());p=preset(a[0],'INFORMATION_TECHNOLOGY','GENERAL')
    p['axis_weights']={'Q':10000,'G':0,'V':0}
    a[0]['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    a[2]=preview_qgv(a[0],a[1],'b');a[4]=preview_qgv(a[0],a[3],'s')
    r=run(a)
    assert sorted(x['rank'] for x in r['result_rows'])==[1,2,3]
    assert r['comparison']['axes']['total']['after_rows']==3
    assert r['reference_population']['issuers']==20


def test_reference_source_reordering_is_deterministic():
    a=list(inputs());r=run(a)
    a[3]['rows'].reverse();a[3]['members'].reverse();a[4]=preview_qgv(a[0],a[3],'source')
    other=run(a)
    assert r==other


def test_classification_hash_mismatch_cannot_admit_a_reference():
    a=list(inputs())
    for s in (a[1],a[3]):
        s['classification_context']['classification_hash']='synthetic-hash'
        for r in s['rows']:
            r['classification_record_id']='record:'+r['company_id']
            r['mapping'].update(common_classification_hash='synthetic-hash',common_record_id=r['classification_record_id'],knowledge_as_of=s['classification_context']['knowledge_as_of'],
                common_dictionary_version='synthetic/1',common_mapping_version='synthetic/1')
    a[3]['rows'][-1]['mapping']['common_classification_hash']='wrong'
    a[2]=preview_qgv(a[0],a[1],'base');a[4]=preview_qgv(a[0],a[3],'source')
    r=run(a)
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['valid_n']==19
    assert r['admission']['reason_counts']['MAPPING_UNRESOLVED']==1


def common_inputs():
    a=list(inputs())
    for s in (a[1],a[3]):
        s['classification_context']['classification_hash']='a'*64
        for r in s['rows']:
            r['classification_record_id']='record:'+r['company_id']
            r['mapping'].update(common_classification_hash='a'*64,common_record_id=r['classification_record_id'],
                common_dictionary_version='synthetic/1',common_mapping_version='synthetic/1',
                knowledge_as_of=s['classification_context']['knowledge_as_of'])
    a[2]=preview_qgv(a[0],a[1],'base');a[4]=preview_qgv(a[0],a[3],'source')
    return a


def test_review_missing_source_classification_hash_fails_closed():
    a=common_inputs();a[3]['classification_context'].pop('classification_hash')
    with pytest.raises(ValueError,match='CLASSIFICATION_CONTEXT'):run(a)


def test_review_other_classification_knowledge_time_not_admitted():
    a=common_inputs();a[3]['rows'][-1]['mapping']['knowledge_as_of']='2099-01-01T00:00:00Z'
    a[4]=preview_qgv(a[0],a[3],'source');r=run(a)
    assert r['result_rows'][0]['factors']['operating_margin_ttm']['valid_n']==19
    assert r['admission']['reason_counts']['MAPPING_UNRESOLVED']==1


def test_review_excluded_reference_record_id_is_part_of_replay_identity():
    from investment_system.research.sector_qgv_reference import save_reference_settings,replay_reference_study
    a=common_inputs()
    for o in a[3]['rows'][-1]['observations'].values():o['provenance']=[]
    a[4]=preview_qgv(a[0],a[3],'source');r=run(a);saved=save_reference_settings(a[0],a[5],r)
    a[3]['rows'][-1]['classification_record_id']='changed-record'
    with pytest.raises(ValueError,match='REPLAY_INPUT'):replay_reference_study(saved,*a[1:5],request_id='changed')


def test_small_main_view_keeps_dual_identity_and_original_counts():
    from investment_system.research.sector_qgv_reference import reference_view
    r=run(inputs());v=reference_view(r)
    assert v['evaluation_population']==r['evaluation_population']
    assert v['reference_population']==r['reference_population']
    assert v['comparison']==r['comparison']
    assert 'admission' not in v and 'reference_snapshot' not in v
    assert len(json.dumps(v).encode())<2_000_000
