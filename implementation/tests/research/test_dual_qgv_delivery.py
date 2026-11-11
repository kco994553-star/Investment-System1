"""Projection only: no scoring engine call or real-company fixture."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[2]

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
