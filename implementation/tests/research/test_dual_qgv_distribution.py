"""Full factor distribution projection: hand-worked stored scores, no scorer."""
from copy import deepcopy
import importlib,json,hashlib
from pathlib import Path
import pytest
from investment_system.research.sector_qgv import digest
from investment_system.research.dual_qgv import json_bytes


def api():return importlib.import_module('investment_system.research.dual_qgv_distribution')


def result(scores=None,scope='COMMON',ref_n=20):
    # Fictional retained result; scores/ranks/old bins are explicit test observations.
    scores=scores or [100,95,90,85,80,75,70,65,60,55,50,45,40,35,30,25,20,15,5,0]
    rows=[]
    for i,score in enumerate(scores):
        rows.append(dict(company_id=f'SYN-{i:03}',issuer_id=f'issuer:{i:03}',security_id=None,ranking_scope=scope,total=None,
          factors={'debt_assets':dict(score=score,rank=i+1,rank_n=len(scores),decile=10-i//2 if len(scores)==20 else None,
            decile_status='VALID' if len(scores)==20 else 'SAMPLE_LT_10',valid_n=ref_n,score_status='VALID',raw_status='VALID',kind='ADDITIONAL')}))
    pop=dict(id='SYN-EVALUATION',version='1',members_hash=digest([r['company_id'] for r in rows]),valuation_date='2026-11-04',as_of='2026-11-04T20:00:00Z',code_rows=len(rows),issuers=len(rows),input_hash='1'*64)
    groups=[dict(ranking_scope=scope,variant_id='debt_assets',valid_n=ref_n,members_hash='2'*64,issuer_members_hash='3'*64)]
    b=dict(schema_version='qgv-dual-board/1',model_id='unified-roa-core/0.1.0' if scope=='COMMON' else 'sector-reduced-core/0.1.0',model_version='0.1.0',evaluation_population=pop,
      reference_population=dict(id='SYN-REFERENCE',version='1',input_hash='4'*64,members_hash='5'*64,factor_members_hash=digest(groups)),
      configuration={'minimum':20},normalization_version='common-midrank-strict20/1',bindings={'evaluation':pop,'reference':{'input_hash':'4'*64}},
      engine_version='SYN-ENGINE',adapter_version='SYN-ADAPTER',rows=rows,groups=groups)
    return seal(b)


def seal(b):
    b['result_hash']=digest({k:v for k,v in b.items() if k not in ('request_id','result_hash')});return b


def projected(b,policy):
    return api().distribution_artifacts({'U1' if b['rows'][0]['ranking_scope']=='COMMON' else 'S1':b},
      scope='operating504',data_kind='SYNTHETIC',display_policy=policy)


def resolve(out,entry):
    return [r for name in entry['files'] for p in out[name]['parts'] if p['group_id']==entry['group_id'] for r in p['rows']]


def test_all_ten_bins_all_rows_and_null_total_no_bonus():
    b=result();before=deepcopy(b);out=projected(b,api().STORED)
    idx=out['distribution-index.json'];g=idx['groups'][0];rows=resolve(out,g)
    assert len(rows)==20 and {r['decile'] for r in rows}==set(range(1,11))
    assert len(g['bins'])==10 and [x['count'] for x in g['bins']]==[2]*10
    assert idx['bands'][0]['label']=='상위 0–10%' and idx['bands'][-1]['label']=='상위 90–100%'
    assert g['raw_direction']=='LOWER' and g['score_direction']=='HIGHER_IS_BETTER'
    assert g['comparison_group']['n']==20 and g['reference_valid_n']==20
    assert all(r['kind']=='ADDITIONAL' for r in rows) and idx['additional_factor_score_contribution']==0 and b==before
    one=api().select_rows(out,g['group_id'],[7]);assert len(one['rows'])==2
    assert one['group']==g and one['rows'][0]['rank']==7


def test_reference_percentile_candidate_keeps_equal_scores_in_one_band():
    b=result([50]*20);out=projected(b,api().REFERENCE)
    g=out['distribution-index.json']['groups'][0];rows=resolve(out,g)
    assert {r['decile'] for r in rows}=={6} and len({r['stored_decile'] for r in rows})==10
    assert [x['count'] for x in g['bins']]==[0,0,0,0,20,0,0,0,0,0]
    assert g['legacy_tie_splits'] and g['comparison_group']['role']=='FACTOR_REFERENCE'
    assert {r['rank'] for r in rows}==set(range(1,21))


def test_small_evaluation_is_not_small_reference_and_missing_remains_null():
    b=result([100,50,0]);legacy=projected(b,api().STORED);candidate=projected(b,api().REFERENCE)
    assert all(r['decile'] is None for r in resolve(legacy,legacy['distribution-index.json']['groups'][0]))
    assert [r['decile'] for r in resolve(candidate,candidate['distribution-index.json']['groups'][0])]==[10,6,1]
    f=b['rows'][1]['factors']['debt_assets'];f.update(score=None,rank=None,rank_n=0,decile=None,decile_status='NO_VALID_SCORE',score_status='MISSING_INPUT',raw_status='MISSING_INPUT')
    for i in (0,2):b['rows'][i]['factors']['debt_assets'].update(rank=1 if i==0 else 2,rank_n=2)
    seal(b);out=projected(b,api().REFERENCE);g=out['distribution-index.json']['groups'][0]
    assert g['unavailable_count']==1 and g['evaluation_rows_in_scope']==3
    row=next(r for r in resolve(out,g) if r['company_id']=='SYN-001')
    assert row['score'] is None and row['decile'] is None and row['score_status']=='MISSING_INPUT'


def test_bad_hash_reference_n_and_unknown_policy_rejected():
    b=result();b['rows'][0]['factors']['debt_assets']['score']=12
    with pytest.raises(ValueError,match='RESULT_HASH'):projected(b,api().STORED)
    b=result();b['rows'][0]['factors']['debt_assets']['valid_n']=21;seal(b)
    with pytest.raises(ValueError,match='REFERENCE_GROUP_N'):projected(b,api().STORED)
    with pytest.raises(ValueError,match='DISPLAY_POLICY'):projected(result(),'unknown')


def test_sector_groups_never_merged_and_filter_keeps_full_context():
    a=result(scope='SECTOR|INFORMATION_TECHNOLOGY|GENERAL');b=result(scope='SECTOR|INDUSTRIALS|GENERAL')
    for row in b['rows']:row['company_id']='OTHER-'+row['company_id'];row['issuer_id']='other:'+row['issuer_id']
    a['rows']+=b['rows'];a['groups']+=b['groups']
    a['evaluation_population'].update(code_rows=40,issuers=40,members_hash=digest([r['company_id'] for r in a['rows']]))
    a['reference_population']['factor_members_hash']=digest(a['groups']);seal(a)
    out=projected(a,api().REFERENCE);groups=out['distribution-index.json']['groups']
    assert len(groups)==2 and all(g['comparison_group']['n']==20 for g in groups)
    assert all(g['evaluation_valid_n']==20 for g in groups)
    for g in groups:
        all_rows=resolve(out,g);selected=api().select_rows(out,g['group_id'],[10,1])
        assert selected['rows']==[r for r in all_rows if r['decile'] in [10,1]]
        assert selected['group']['evaluation_valid_n']==20
        assert selected['board']['evaluation_population']['code_rows']==40


def test_bounded_shards_preserve_every_company_and_all_bins():
    b=result([100-i/2 for i in range(200)],ref_n=200)
    for i,r in enumerate(b['rows']):r['factors']['debt_assets'].update(decile=10-i//20,decile_status='VALID')
    seal(b)
    out=api().distribution_artifacts({'U1':b},scope='held1057',data_kind='SYNTHETIC',display_policy=api().STORED,max_bytes=30000)
    g=out['distribution-index.json']['groups'][0]
    assert len(g['files'])>1 and len(resolve(out,g))==200
    assert {r['company_id'] for r in resolve(out,g)}=={r['company_id'] for r in b['rows']}
    assert all(len(json_bytes(value))<=30000 for value in out.values())
    for f in out['distribution-manifest.json']['files']:
        assert hashlib.sha256(json_bytes(out[f['path']])).hexdigest()==f['sha256']
    del out[g['files'][-1]]['parts'][-1]['rows'][-1]
    with pytest.raises(ValueError,match='GROUP_ROWS'):api().select_rows(out,g['group_id'],[1])


def test_score_thresholds_are_direction_adjusted_and_null_not_zero():
    b=result();out=projected(b,api().REFERENCE);g=out['distribution-index.json']['groups'][0];rows=resolve(out,g)
    by_score={r['score']:r['decile'] for r in rows}
    assert {s:by_score[s] for s in (100,90,80,50,0)}=={100:10,90:10,80:9,50:6,0:1}
    b['rows'][0]['factors']['debt_assets']['score']=float('nan')
    with pytest.raises(ValueError):seal(b)
    for r in b['rows']:
        r['factors']['debt_assets'].update(score=None,rank=None,rank_n=0,decile=None,decile_status='NO_VALID_SCORE',valid_n=19,score_status='PEER_SAMPLE_SMALL')
    b['groups'][0]['valid_n']=19;b['reference_population']['factor_members_hash']=digest(b['groups']);seal(b)
    out=projected(b,api().REFERENCE);g=out['distribution-index.json']['groups'][0]
    assert g['unavailable_count']==20 and g['unavailable_reasons']=={'PEER_SAMPLE_SMALL':20}
    assert len(g['bins'])==10 and all(x['count']==0 for x in g['bins'])


def test_cli_pins_source_and_no_output_overwrite(tmp_path):
    import os,subprocess,sys
    b=result();source=tmp_path/'saved.json';source.write_bytes(json_bytes(b))
    job=dict(schema_version='qgv-dual-factor-distribution-job/1',scope='operating504',data_kind='SYNTHETIC',display_policy=api().STORED,
      board_results={'U1':dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),result_hash=b['result_hash'])})
    p=tmp_path/'job.json';p.write_bytes(json_bytes(job));dest=tmp_path/'out'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
    cmd=[sys.executable,'-m','investment_system.research.dual_qgv_distribution','--job',str(p),'--output-dir',str(dest)]
    run=subprocess.run(cmd,env=env,capture_output=True,text=True);assert run.returncode==0,run.stderr
    assert json.loads(run.stdout)['new_score_calculations']==0
    again=subprocess.run(cmd,env=env,capture_output=True,text=True);assert again.returncode!=0
    source.write_bytes(source.read_bytes()+b' ')
    bad=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert bad.returncode!=0 and 'SOURCE_FILE_HASH' in bad.stderr and 'Traceback' not in bad.stderr


def test_shared_fixtures_have_manual_expected_counts_and_exact_pins():
    root=Path(__file__).resolve().parents[2]/'docs/research/sector_qgv/dual-distribution-synthetic'
    cases=json.loads((root/'cases.json').read_bytes())['cases']
    assert len(cases)==10
    for case in cases:
        raw=(root/case['source']).read_bytes();assert hashlib.sha256(raw).hexdigest()==case['source_sha256']
        manifest=(root/case['output']/'distribution-manifest.json').read_bytes()
        assert hashlib.sha256(manifest).hexdigest()==case['manifest_sha256']
        out=api().distribution_artifacts(json.loads(raw),scope='operating504',data_kind='SYNTHETIC',display_policy=case['display_policy'])
        assert [g['bins'] for g in out['distribution-index.json']['groups']]==case['expected_bins']
        assert [g['unavailable_count'] for g in out['distribution-index.json']['groups']]==case['expected_unavailable']
        for name,value in out.items():assert json_bytes(value)==(root/case['output']/name).read_bytes()
