"""Projection only: no scoring engine call or real-company fixture."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]

def test_independent_evaluation_and_reference_bindings():
    from copy import deepcopy
    from investment_system.research.sector_qgv_reference import _identity
    d=ROOT/'docs/research/sector_qgv/dual-synthetic'
    evaluation=_identity(json.loads((d/'evaluation.json').read_bytes()))
    reference=_identity(json.loads((d/'reference.json').read_bytes()))
    summary=json.loads((d/'summary.json').read_bytes());index=json.loads((d/'index.json').read_bytes())
    validate=api().validate_input_bindings
    assert validate(summary,index,expected_evaluation=evaluation,expected_reference=reference)['status']=='VERIFIED_BOTH_INPUT_BINDINGS'
    # Internally consistent evaluation mutation still cannot match the independently pinned input.
    bad=deepcopy(summary);ix=deepcopy(index)
    for b in bad['boards'].values():
        b['evaluation_population']['input_hash']='0'*64;b['bindings']['evaluation']['input_hash']='0'*64
    ix['evaluation_population']['input_hash']='0'*64
    with pytest.raises(ValueError,match='EVALUATION_INPUT_BINDING'):
        validate(bad,ix,expected_evaluation=evaluation,expected_reference=reference)
    bad=deepcopy(summary)
    for b in bad['boards'].values():
        b['reference_population']['input_hash']='0'*64
        b['reference_population']['candidate_population']['input_hash']='0'*64
        b['bindings']['reference']['input_hash']='0'*64
    with pytest.raises(ValueError,match='REFERENCE_INPUT_BINDING'):
        validate(bad,index,expected_evaluation=evaluation,expected_reference=reference)
    with pytest.raises(ValueError,match='EXPECTED_EVALUATION_REQUIRED'):
        validate(summary,index,expected_evaluation=None,expected_reference=reference)


def test_five_fields_required_even_if_total_missing_and_unmapped_not_zero():
    from copy import deepcopy
    row=json.loads(files()['detail-000.json'])['rows'][0]['boards']['U1']
    row.update(total=None,status='STRICT_INCOMPLETE')
    assert api().validate_detail_weight_fields(row)['presence']=='REQUIRED_PRESENT'
    for field in api().DETAIL_WEIGHT_FIELDS:
        bad=deepcopy(row);del bad[field]
        with pytest.raises(ValueError,match='DETAIL_WEIGHT_FIELD_MISSING'):
            api().validate_detail_weight_fields(bad)
    unknown={k:v for k,v in row.items() if k not in api().DETAIL_WEIGHT_FIELDS}
    unknown.update(status='MAPPING_UNRESOLVED',gate_status='UNKNOWN',axes=dict.fromkeys(('Q','G','V')),pre_gate_total=None)
    assert api().validate_detail_weight_fields(unknown)['presence']=='NOT_APPLICABLE_MAPPING_UNRESOLVED'
    unknown['missing_factors']={}
    with pytest.raises(ValueError,match='UNMAPPED_WEIGHT_FIELDS'):
        api().validate_detail_weight_fields(unknown)
    row['gate_status']='UNKNOWN'
    assert api().validate_detail_weight_fields(row)['post_gate_application']=='UNDETERMINED'


def test_stored_leader_selection_keeps_top_n_distinct_from_top_decile():
    api_ = api()
    group={'evaluation_valid_n':23,'top_n':1,'leaders':[{'rank':1}],
      'decile_status':'VALID','decile_boundaries':[{'decile':10,'count':2,'first_rank':1,'last_rank':2}]}
    before=json.dumps(group,sort_keys=True)
    info=api_.leader_selection(group)
    assert info['top_n']=={'requested_n':1,'returned_n':1,'complete':True}
    assert info['top_10_percent']=={'status':'VALID','k':2,'first_rank':1,'last_rank':2,'returned_in_top_n':1,'complete_in_top_n':False}
    assert json.dumps(group,sort_keys=True)==before
    group.update(evaluation_valid_n=3,decile_status='SAMPLE_LT_10',decile_boundaries=[])
    assert api_.leader_selection(group)['top_10_percent']['k'] is None
    group.update(evaluation_valid_n=23,decile_status='VALID',decile_boundaries=[{'decile':10,'count':3,'first_rank':1,'last_rank':3}])
    with pytest.raises(ValueError,match='TOP_DECILE_BOUNDARY'):
        api_.leader_selection(group)

def api():
    name='investment_system.research.dual_qgv_delivery'
    assert importlib.util.find_spec(name) is not None,'factor leader projection missing'
    return importlib.import_module(name)


def files():
    d=ROOT/'docs/research/sector_qgv/dual-synthetic'
    raw={n:(d/n).read_bytes() for n in ('summary.json','index.json','detail-000.json')}
    manifest={'schema_version':'qgv-dual-delivery-manifest/1','data_kind':'SYNTHETIC','scope':'operating504',
      'files':[{'path':n,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(raw.items())]}
    raw['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();return raw


def test_projection_uses_existing_rank_no_recalculation_or_raw_values():
    raw=files();before=dict(raw);out=api().factor_leaders_artifacts(raw,expected_manifest_sha256=hashlib.sha256(raw['manifest.json']).hexdigest(),top_n=2)
    index=out['factor-leaders.json'];entry=next(g for g in index['groups'] if g['board']=='U1' and g['variant_id']=='roa_ttm')
    group=next(g for g in out[entry['file']]['groups'] if g['group_id']==entry['group_id'])
    rows=json.loads(raw['detail-000.json'])['rows'];expected=sorted((r['boards']['U1'] for r in rows),key=lambda r:r['factors']['roa_ttm']['rank'])[:2]
    assert [(r['company_id'],r['rank'],r['score']) for r in group['leaders']]==[(r['company_id'],r['factors']['roa_ttm']['rank'],r['factors']['roa_ttm']['score']) for r in expected]
    assert group['evaluation_valid_n']==3 and group['reference_valid_n']==20 and group['decile_status']=='SAMPLE_LT_10'
    assert group['decile_boundaries']==[] and raw==before
    assert 'raw_value' not in json.dumps(out)
    assert all(len(api().json_bytes(x))<=1_800_000 for x in out.values())


def test_bad_pin_missing_detail_wrong_rank_and_mixed_context_fail():
    raw=files();pin=hashlib.sha256(raw['manifest.json']).hexdigest()
    with pytest.raises(ValueError,match='MANIFEST_HASH'):api().factor_leaders_artifacts(raw,expected_manifest_sha256='0'*64)
    del raw['detail-000.json']
    with pytest.raises(ValueError,match='FILE_MISSING'):api().factor_leaders_artifacts(raw,expected_manifest_sha256=pin)
    raw=files();raw['detail-000.json']+=b' '
    with pytest.raises(ValueError,match='FILE_HASH'):api().factor_leaders_artifacts(raw,expected_manifest_sha256=pin)


def test_rank_and_decile_boundaries_hand_worked_without_scorer():
    # 10 retained ranks, D10 top1/D1 bottom1; no score or decile recomputation.
    source=files();detail=json.loads(source['detail-000.json']);row=detail['rows'][0]
    from copy import deepcopy
    rows=[]
    for i in range(10):
        r=deepcopy(row);r['company_id']='SYN:'+str(i)
        for name,b in r['boards'].items():
            b['company_id']=r['company_id'];b['issuer_id']='issuer:'+str(i)
            for v,f in b['factors'].items():
                f.update(score=100-i,rank=i+1,rank_n=10,decile=10-i,decile_status='VALID',score_status='VALID')
        rows.append(r)
    idx=json.loads(source['index.json']);template=idx['rows'][0];idx['rows']=[]
    summary=json.loads(source['summary.json'])
    for k,b in summary['boards'].items():b['evaluation_population']['code_rows']=10;b['evaluation_population']['issuers']=10
    idx['evaluation_population']=summary['boards']['U1']['evaluation_population']
    for r in rows:
        head=deepcopy(template);head.update(company_id=r['company_id'],issuer_id=r['boards']['U1']['issuer_id']);idx['rows'].append(head)
    detail['rows']=rows
    source['detail-000.json']=api().json_bytes(detail);source['index.json']=api().json_bytes(idx);source['summary.json']=api().json_bytes(summary)
    source['manifest.json']=api().json_bytes(api().delivery_manifest(source,scope='operating504',data_kind='SYNTHETIC'))
    out=api().factor_leaders_artifacts(source,expected_manifest_sha256=hashlib.sha256(source['manifest.json']).hexdigest(),top_n=2)
    ent=next(g for g in out['factor-leaders.json']['groups'] if g['board']=='U1' and g['variant_id']=='roa_ttm')
    group=next(g for g in out[ent['file']]['groups'] if g['group_id']==ent['group_id'])
    assert group['leaders'][0]['rank']==1 and group['leaders'][1]['rank']==2
    assert group['decile_boundaries'][0]=={'decile':10,'count':1,'first_rank':1,'last_rank':1,'first_score':100,'last_score':100}
    rows[0]['boards']['U1']['factors']['roa_ttm']['rank']=2
    source['detail-000.json']=api().json_bytes({'schema_version':'qgv-dual-detail/1','rows':rows})
    source['manifest.json']=api().json_bytes(api().delivery_manifest(source,scope='operating504',data_kind='SYNTHETIC'))
    with pytest.raises(ValueError,match='RANK_INTEGRITY'):api().factor_leaders_artifacts(source,expected_manifest_sha256=hashlib.sha256(source['manifest.json']).hexdigest())

def test_projection_rejects_population_mix_and_size_overflow():
    raw=files();summary=json.loads(raw['summary.json']);summary['boards']['U2']['evaluation_population']['valuation_date']='2026-11-05'
    raw['summary.json']=api().json_bytes(summary);raw['manifest.json']=api().json_bytes(api().delivery_manifest(raw,scope='operating504',data_kind='SYNTHETIC'))
    with pytest.raises(ValueError,match='POPULATION_MISMATCH'):api().factor_leaders_artifacts(raw,expected_manifest_sha256=hashlib.sha256(raw['manifest.json']).hexdigest())
    raw=files()
    with pytest.raises(ValueError,match='SIZE'):api().factor_leaders_artifacts(raw,expected_manifest_sha256=hashlib.sha256(raw['manifest.json']).hexdigest(),max_bytes=200)


def test_published_manifest_is_same_retained_synthetic_bytes_and_projection_pins():
    d=ROOT/'docs/research/sector_qgv/dual-synthetic'
    raw={n:(d/n).read_bytes() for n in ('summary.json','index.json','detail-000.json')}
    raw['manifest.json']=(d/'delivery-manifest.json').read_bytes()
    out=api().factor_leaders_artifacts(raw,expected_manifest_sha256=hashlib.sha256(raw['manifest.json']).hexdigest())
    target=d.parent/'dual-factor-leaders-synthetic'
    assert {p.name for p in target.iterdir() if p.is_file()}==set(out)
    for name,value in out.items():assert (target/name).read_bytes()==api().json_bytes(value)

def test_projection_cli_uses_pinned_bytes_and_refuses_existing_output(tmp_path):
    import os,subprocess,sys
    raw=files();source=tmp_path/'source';source.mkdir()
    for name,body in raw.items():(source/name).write_bytes(body)
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
    out=tmp_path/'projection'
    command=[sys.executable,'-m','investment_system.research.dual_qgv_delivery','--source-dir',str(source),
       '--manifest-sha256',hashlib.sha256(raw['manifest.json']).hexdigest(),'--output-dir',str(out)]
    first=subprocess.run(command,env=env,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    before=(out/'factor-leaders.json').read_bytes()
    assert json.loads(first.stdout)['score_calculations']==0
    second=subprocess.run(command,env=env,capture_output=True,text=True)
    assert second.returncode!=0 and 'Traceback' not in second.stderr
    assert (out/'factor-leaders.json').read_bytes()==before


def test_shared_binding_cases_and_independent_input_pins():
    from copy import deepcopy
    from investment_system.research.sector_qgv_reference import _identity
    d=ROOT/'docs/research/sector_qgv'
    fixture=json.loads((d/'dual-delivery-binding-cases.json').read_bytes())
    for f in fixture['sources']:assert hashlib.sha256((d/f['path']).read_bytes()).hexdigest()==f['sha256']
    assert fixture['expected_evaluation']==_identity(json.loads((d/'dual-synthetic/evaluation.json').read_bytes()))
    assert fixture['expected_reference']==_identity(json.loads((d/'dual-synthetic/reference.json').read_bytes()))
    base={n:json.loads((d/f'dual-synthetic/{n}.json').read_bytes()) for n in ('summary','index')}
    for case in fixture['cases']:
        docs=deepcopy(base)
        for patch in case['patches']:
            node=docs
            for key in patch[:-2]:node=node[key]
            node[patch[-2]]=patch[-1]
        try:
            actual=api().validate_input_bindings(docs['summary'],docs['index'],
              expected_evaluation=fixture['expected_evaluation'],expected_reference=fixture['expected_reference'])['status']
        except ValueError as exc:actual=str(exc)
        assert actual==case['expected']


def test_selection_contract_cli_preserves_source_bytes_and_no_scorer(tmp_path,monkeypatch):
    import subprocess,sys,os
    d=ROOT/'docs/research/sector_qgv/dual-factor-leaders-synthetic'
    raw={p.name:p.read_bytes() for p in d.iterdir() if p.is_file()};before=dict(raw)
    pin=hashlib.sha256(raw['factor-leaders-manifest.json']).hexdigest()
    import investment_system.research.dual_qgv as scorer
    def forbidden(*args,**kwargs):raise AssertionError('must not run scorer')
    monkeypatch.setattr(scorer,'run_board',forbidden)
    out=api().selection_contract_artifacts(raw,expected_manifest_sha256=pin)
    target=d.parent/'dual-leader-selection-synthetic'
    for name,value in out.items():assert (target/name).read_bytes()==api().json_bytes(value)
    assert raw==before
    assert out['factor-leaders-selection.json']['tie_policy']['secondary']=='COMPANY_ID_ASC'
    raw['factor-leaders-000.json']+=b' '
    with pytest.raises(ValueError,match='FILE_HASH'):api().selection_contract_artifacts(raw,expected_manifest_sha256=pin)
    command=[sys.executable,'-m','investment_system.research.dual_qgv_delivery','--selection-contract',
      '--source-dir',str(d),'--manifest-sha256',pin,'--output-dir',str(tmp_path/'selection')]
    result=subprocess.run(command,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['score_calculations']==0
    for name in out:assert (tmp_path/'selection'/name).read_bytes()==(target/name).read_bytes()
