"""Acceptance of already saved all-band files; no QGV engine execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from investment_system.research.dual_qgv import json_bytes
from investment_system.research.dual_qgv_distribution import STORED
from investment_system.research.dual_qgv_distribution_index import bin_index_artifacts, validate_distribution
from test_dual_qgv_distribution import result, seal, projected


def raw(out):return {k:json_bytes(v) for k,v in out.items()}
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(files):return sha(files['distribution-manifest.json'])
def resign(out):
    out['distribution-manifest.json']['files']=[dict(path=k,size=len(json_bytes(v)),sha256=sha(json_bytes(v))) for k,v in sorted(out.items()) if k!='distribution-manifest.json']
    return raw(out)
def records(out):return [g for name,x in out.items() if name.startswith('bins-') for g in x['groups']]


def test_route_all_ten_bins_preserves_original_files_and_ranks():
    source=raw(projected(result(),STORED));before=deepcopy(source)
    out=bin_index_artifacts(source,expected_manifest_sha256=pin(source));g=records(out)[0]
    assert len(g['bins'])==10 and [b['count'] for b in g['bins']]==[2]*10
    assert [(b['first_rank'],b['last_rank']) for b in g['bins']]==[(i,i+1) for i in range(1,21,2)]
    assert all(b['member_files'] for b in g['bins']) and sum(b['count'] for b in g['bins'])==20
    assert out['bin-index.json']['new_score_calculations']==0 and source==before
    assert out['bin-index.json']['boards']['U1']['evaluation_population']['code_rows']==20


@pytest.mark.parametrize('case,error',[('missing','FILE_SET'),('bytes','FILE_HASH'),('duplicate','GROUP_MEMBERS'),('outside','UNKNOWN_GROUP'),('scope','GROUP_ID'),('count','BIN_COUNTS'),('rank','RANK_INTEGRITY'),('null_bin','DECILE_PARTITION')])
def test_partial_or_corrupt_batch_rejected_before_output(case,error):
    out=projected(result(),STORED);part=next(v for k,v in out.items() if k.startswith('distribution-0'));g=out['distribution-index.json']['groups'][0]
    if case=='missing':
        files=raw(out);del files[g['files'][0]]
    elif case=='bytes':
        files=raw(out);files[g['files'][0]]+=b' '
    else:
        if case=='duplicate':part['parts'][0]['rows'][1]=deepcopy(part['parts'][0]['rows'][0])
        elif case=='outside':part['parts'][0]['group_id']='U1|OTHER|debt_assets'
        elif case=='scope':g['ranking_scope']='OTHER'
        elif case=='count':g['bins'][0]['count']=1
        elif case=='rank':part['parts'][0]['rows'][1]['rank']=1
        elif case=='null_bin':part['parts'][0]['rows'][0]['decile']=None
        files=resign(out)
    with pytest.raises(ValueError,match=error):bin_index_artifacts(files,expected_manifest_sha256=pin(files))


def test_uneven_sample_and_ties_copy_stored_boundaries():
    b=result([50]*23,ref_n=23)
    # Existing ordinal rule at N=23: 2,3,3,3,2,2,2,2,2,2.
    ds=[10]*2+[9]*3+[8]*3+[7]*3+[6]*2+[5]*2+[4]*2+[3]*2+[2]*2+[1]*2
    for r,d in zip(b['rows'],ds):r['factors']['debt_assets'].update(decile=d,decile_status='VALID')
    files=raw(projected(seal(b),STORED));g=records(bin_index_artifacts(files,expected_manifest_sha256=pin(files)))[0]
    assert [x['count'] for x in g['bins']]==[2,3,3,3,2,2,2,2,2,2]
    assert len(g['legacy_tie_splits'])==9 and g['bins'][0]['last_rank']==2
    assert g['comparison_group']['unit']=='EVALUATION_CODE_ROW'


def test_sample_small_is_outside_bins_without_removing_denominator():
    files=raw(projected(result([100,50,0]),STORED));g=records(bin_index_artifacts(files,expected_manifest_sha256=pin(files)))[0]
    assert g['evaluation_valid_n']==3 and g['reference_valid_n']==20
    assert g['binned_evaluation_n']==0 and g['unavailable_count']==3
    assert g['partition_status']=='SAMPLE_LT_10' and sum(x['count'] for x in g['bins'])==0


def test_shards_larger_than_top20_have_complete_d10():
    b=result([100-i/10 for i in range(230)],ref_n=230)
    for i,r in enumerate(b['rows']):r['factors']['debt_assets'].update(decile=10-i//23,decile_status='VALID')
    from investment_system.research.dual_qgv_distribution import distribution_artifacts
    files=raw(distribution_artifacts({'U1':seal(b)},scope='held1057',data_kind='SYNTHETIC',display_policy=STORED,max_bytes=50000))
    out=bin_index_artifacts(files,expected_manifest_sha256=pin(files),max_bytes=50000)
    g=records(out)[0];assert g['bins'][0]['count']==23 and g['bins'][0]['last_rank']==23
    assert all(len(json_bytes(x))<=50000 for x in out.values())
    assert len(g['files'])>1


def test_source_pin_and_policy_are_separate_from_internal_consistency():
    files=raw(projected(result(),STORED))
    with pytest.raises(ValueError,match='MANIFEST_PIN'):validate_distribution(files,'0'*64)
    out=projected(result(),STORED);out['distribution-index.json']['display_policy']='reference-score-deciles/1'
    files=resign(out)
    with pytest.raises(ValueError,match='STORED_POLICY'):validate_distribution(files,pin(files))


def test_public_examples_match_exact_members_and_pins():
    root=Path(__file__).resolve().parents[2]/'docs/research/sector_qgv/dual-bin-synthetic'
    cases=json.loads((root/'cases.json').read_bytes())['cases'];assert len(cases)==9
    for c in cases:
        source=root/c['source'];files={p.name:p.read_bytes() for p in source.iterdir()}
        out=bin_index_artifacts(files,expected_manifest_sha256=c['source_manifest_sha256'])
        assert sha((root/c['output']/'bin-manifest.json').read_bytes())==c['manifest_sha256']
        _,rows,_,_=validate_distribution(files,c['source_manifest_sha256'])
        for g in c['expected_groups']:
            for b in g['bins']:
                actual=sorted((r for r in rows[g['group_id']] if r['decile']==b['decile']),key=lambda r:r['rank'])
                assert [r['company_id'] for r in actual]==b['members']
                assert [r['rank'] for r in actual]==b['ranks']
        for name,value in out.items():assert json_bytes(value)==(root/c['output']/name).read_bytes()


def test_cli_partial_failure_does_not_create_or_overwrite_output(tmp_path):
    import os,subprocess,sys
    source=tmp_path/'source';source.mkdir();files=raw(projected(result(),STORED))
    for name,value in files.items():(source/name).write_bytes(value)
    dest=tmp_path/'output'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
    cmd=[sys.executable,'-m','investment_system.research.dual_qgv_distribution_index','--source-dir',str(source),'--source-manifest-sha256',pin(files),'--output-dir',str(dest)]
    shard=next(n for n in files if n.startswith('distribution-0'));(source/shard).unlink()
    failed=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert failed.returncode==1 and 'FILE_SET' in failed.stderr and not dest.exists()
    (source/shard).write_bytes(files[shard]);good=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert good.returncode==0,good.stderr
    before={p.name:p.read_bytes() for p in dest.iterdir()}
    again=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert again.returncode==1 and before=={p.name:p.read_bytes() for p in dest.iterdir()}


@pytest.mark.parametrize('n,counts',[(9,[0]*10),(10,[1]*10),(11,[1,2,1,1,1,1,1,1,1,1]),(17,[1,2,2,2,2,2,2,2,1,1])])
def test_requested_small_sample_examples(n,counts):
    root=Path(__file__).resolve().parents[2]/'docs/research/sector_qgv/dual-bin-synthetic'/f'boundary-{n}'
    g=json.loads((root/'routing/bins-000.json').read_bytes())['groups'][0]
    assert [b['count'] for b in g['bins']]==counts
    assert g['reference_valid_n']==20 and g['evaluation_valid_n']==n
    assert g['binned_evaluation_n']==(n if n>=10 else 0)
    assert g['unavailable_count']==(0 if n>=10 else n)
