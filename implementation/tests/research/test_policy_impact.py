import copy
import json
from pathlib import Path
import pytest
from investment_system.research.policy_impact import build,validate,Invalid
from investment_system.research.policy_impact.build import append_only,collection_outcome,retain_good,from_news_reference

ROOT=Path(__file__).parents[2];FIX=ROOT/'docs/research/policy_impact/synthetic-job.json'
@pytest.fixture
def j():return json.loads(FIX.read_text())
def view(j,**kw):return build(j['bundle'],j['company_ids'],kw.pop('as_of',j['as_of']),public=True,**kw)

def test_p01_repeat_source_not_policy_revision(j):
    a=view(j);assert a==view(j)
    assert len(a['bundle']['policies'])==3

def revise(j):
    b=j['bundle'];p=copy.deepcopy(b['policies'][0]);p.update(revision_id='2',supersedes_revision_id='1',change_recorded_at='2026-11-07T01:00:00Z',recorded_at='2026-11-07T01:00:00Z',reviewed_at='2026-11-07T01:00:00Z')
    p['identity_basis']['relation_evidence_refs']=copy.deepcopy(p['evidence_refs']);b['policies'].append(p)
    r=copy.deepcopy(b['review_records'][0]);r.update(revision_id='2',reviewed_at=p['reviewed_at']);b['review_records'].append(r)
    return p

def test_p02_append_history_and_p11_old_hypothesis(j):
    old=copy.deepcopy(j['bundle']);revise(j)
    append_only(old,j['bundle'])
    a=view(j,as_of='2026-11-07T02:00:00Z')
    assert a['current_policy_revisions']['p0']=='2' and len(a['bundle']['policies'])==4
    assert a['bundle']['hypotheses'][0]['review_status']=='REVIEW_REQUIRED'
    assert j['bundle']['hypotheses'][0]['policy_revision_id']=='1'
    j['bundle']['policies'][0]['title']='rewrite'
    with pytest.raises(Invalid,match='HISTORY_MUTATION'):append_only(old,j['bundle'])

def test_p03_partial_unit_not_global_and_p04_date_not_status(j):
    p=revise(j);p['policy_id']='unit-exception';p['supersedes_revision_id']=None;p['parent_policy_id']='p0';p['lifecycle_status']='SUSPENDED'
    j['bundle']['review_records'][-1]['id']='unit-exception'
    a=view(j,as_of='2026-11-09T00:00:00Z')['bundle']
    assert next(p for p in a['policies'] if p['policy_id']=='p0')['lifecycle_status']=='ADOPTED'
    assert a['freshness']['review_due'] is True

def test_p05_date_and_gdelt_discovery_preserved(j):
    s=j['bundle']['sources'][0];s['first_seen_at']='2026-11-07T00:00:00Z'
    n=from_news_reference({'link':s['url'],'title':'article','source_seen_at':s['first_seen_at']},s)
    assert n['published']['value'] is None
    a=view(j)['bundle']['policies'][0]['published'];assert a['precision']=='DATE' and a['timezone'] is None

@pytest.mark.parametrize('group,field',[('sources','revision_acquired_at'),('policies','reviewed_at'),('exposures','recorded_at'),('hypotheses','recorded_at')])
def test_p06_all_dependency_times_block_future(j,group,field):
    j['bundle'][group][0][field]='2026-11-08T00:00:00Z'
    a=view(j);assert not any(h['policy_id']=='p0' for h in a['bundle']['hypotheses'])
    assert a['historical_pit_eligible'] is False

def test_p07_region_not_applicability_p08_null(j):
    e=view(j)['bundle']['exposures'][0]
    assert e['evidence_status']=='DOCUMENTED' and e['policy_applicability']=='UNCONFIRMED'
    assert e['ratio'] is None and e['reason_codes']

@pytest.mark.parametrize('mutation,code',[
 (lambda b:b['exposures'][0].update(company_id='ticker-only'),'COMPANY_REF'),
 (lambda b:b['policies'][0]['evidence_refs'][0].update(source_revision_id='missing'),'SOURCE_REF'),
 (lambda b:b['policies'][0].update(parent_policy_id='p0'),'DEPENDENCY_CYCLE'),
 (lambda b:b['hypotheses'][0]['exposure_refs'][0].update(exposure_revision_id='missing'),'EXPOSURE_REF'),
 (lambda b:b['policies'][0]['identity_basis'].update(method='TITLE_SIMILARITY'),'UNSTABLE_POLICY_ID'),
 (lambda b:b['exposures'][0].update(ratio=None,reason_codes=[]),'NULL_REASON'),
 (lambda b:b['sources'][0].update(url='javascript:alert(1)'),'UNSAFE_URL'),
 (lambda b:b['sources'][0].update(data_kind='REAL_REVIEWED'),'MIXED_KIND'),
 (lambda b:b.update(personal_holdings=[]),'FIELDS'),
 (lambda b:b['hypotheses'][0]['watch_items'][0].update(private_kis=1),'FIELDS'),
 (lambda b:b['exposures'][0].update(probability=.5),'FIELDS'),
 (lambda b:b.update(score_effect='QGV'),'FORBIDDEN_EFFECT'),
])
def test_p09_p10_p18_p19_p22_invalid_inputs(j,mutation,code):
    mutation(j['bundle'])
    with pytest.raises(Invalid,match=code):view(j)

@pytest.mark.parametrize('status,parsed,complete,truncated,expected',[(429,True,True,False,'FAILED'),(200,False,True,False,'FAILED'),(200,True,False,True,'INCOMPLETE'),(200,True,True,False,'NO_NEW_ITEMS')])
def test_p12_p13_outcome(status,parsed,complete,truncated,expected):
    a=collection_outcome(http_status=status,parsed=parsed,complete=complete,truncated=truncated,incomplete_ranges=['2026-11-07'])
    assert a['result']==expected and a['checkpoint_advance']==(expected=='NO_NEW_ITEMS')

def test_p14_preserve_good_timestamps(j):
    b=j['bundle'];r=retain_good(b,{'result':'FAILED','at':'2026-11-08T00:00:00Z'})
    assert r['policies']==b['policies'] and r['policy_as_of']==b['policy_as_of']
    assert r['refresh']['last_success_at']==b['refresh']['last_success_at']
    assert b['refresh']['mode']=='MANUAL_REVIEW'

def test_p15_unverified_and_unreviewed_not_public(j):
    j['bundle']['sources'][0]['verification_status']='SOURCE_UNVERIFIED'
    a=view(j)['bundle'];assert not any(p['policy_id']=='p0' for p in a['policies'])
    j['bundle']['policies'][1]['review_status']='UNREVIEWED'
    j['bundle']['review_records']=[r for r in j['bundle']['review_records'] if not (r['group']=='policies' and r['id']=='p1')]
    assert not any(p['policy_id']=='p1' for p in view(j)['bundle']['policies'])

@pytest.mark.parametrize('stage',['PRELIMINARY_TERMS','FINAL_AWARD','DISBURSEMENT_CONFIRMED'])
def test_p16_subsidy_not_lifecycle(j,stage):
    j['bundle']['policies'][2]['subsidy_stage']=stage
    p=next(p for p in view(j)['bundle']['policies'] if p['policy_id']=='p2')
    assert p['subsidy_stage']==stage and p['lifecycle_status']=='ADOPTED'

def test_p17_no_operating_modules_changed_or_imported():
    import ast
    path=ROOT/'src/investment_system/research/policy_impact'
    for p in path.glob('*.py'):
        tree=ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom):assert not any(s in (n.module or '').split('.') for s in ['qgv','providers','macro_current'])
    # No score/gate parameter or result is accepted; fields are fixed NONE.

def test_cli_invalid_preserves_last_good(j,tmp_path):
    import subprocess,sys
    job=tmp_path/'job.json';out=tmp_path/'view.json';out.write_text('last-good')
    j['bundle']['gate_effect']='BAD';job.write_text(json.dumps(j))
    r=subprocess.run([sys.executable,str(ROOT/'tools/policy_impact.py'),'--job',str(job),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==2 and out.read_text()=='last-good' and 'FORBIDDEN_EFFECT' in r.stdout


def test_revision_relation_evidence_time_and_public_closure(j):
    p=revise(j);s=copy.deepcopy(j['bundle']['sources'][0]);s.update(source_id='relation',revision_acquired_at='2026-11-09T00:00:00Z')
    j['bundle']['sources'].append(s);p['identity_basis']['relation_evidence_refs'][0]['source_id']='relation'
    assert view(j,as_of='2026-11-08T00:00:00Z')['current_policy_revisions']['p0']=='1'
    s['verification_status']='SOURCE_UNVERIFIED'
    assert view(j,as_of='2026-11-10T00:00:00Z')['current_policy_revisions']['p0']=='1'


def test_nested_private_payload_is_rejected(j):
    j['bundle']['hypotheses'][0]['conditions']=[{'private_kis':123}]
    with pytest.raises(Invalid,match='TEXT_ARRAY'):view(j)


def test_p17_actual_shared_qgv_invariance(j):
    from investment_system.qgv.qgv_v2 import score_universe
    from investment_system.qgv.type_config import load_official_type_config
    from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
    c=json.loads((ROOT/'tests/fixtures/qgv_v2_vectors_v1.json').read_text())['cases'][0]['input']
    def run():return score_universe(copy.deepcopy(c['companies']),copy.deepcopy(c['synthetic_market']),type_config=load_official_type_config().to_dict(),parameters=load_default_dcf_parameters())
    original=run();view(j);revise(j);view(j,as_of='2026-11-08T00:00:00Z')
    assert run()==original

@pytest.mark.parametrize('mutate',[
 lambda b:b.update(bundle_id={'personal_holdings':[123]}),
 lambda b:b['refresh'].update(retained_bundle_id={'private_price':123}),
 lambda b:b['review_records'][0].update(author={'private_kis':123}),
])
def test_public_nested_metadata_injection_rejected(j,mutate):
    mutate(j['bundle'])
    with pytest.raises(Invalid):view(j)

def test_policy_id_cannot_join_issuers_or_fork_chain(j):
    p=copy.deepcopy(j['bundle']['policies'][1]);p.update(policy_id='p0',revision_id='2');j['bundle']['policies'].append(p)
    with pytest.raises(Invalid,match='POLICY_IDENTITY_MUTATION'):view(j)


def test_future_top_level_freshness_is_not_historical_state(j):
    j['bundle']['freshness'].update(last_reviewed_at='2026-11-09T00:00:00Z',last_source_check_at='2026-11-09T00:00:00Z')
    j['bundle']['refresh']['last_manual_review_at']='2026-11-09T00:00:00Z'
    a=view(j)['bundle']
    assert a['freshness']['last_reviewed_at']==j['as_of']
    assert a['freshness']['last_source_check_at'] is None and a['refresh']['last_manual_review_at'] is None


def test_datetime_timezone_cannot_carry_private_payload(j):
    j['bundle']['policies'][0]['published']={'value':'2026-11-01T00:00:00Z','precision':'DATETIME','timezone':{'private_price':123}}
    with pytest.raises(Invalid,match='TIMEZONE_TYPE'):view(j)


def test_failure_query_does_not_restamp_policy_confirmation(j):
    b=retain_good(j['bundle'],{'result':'FAILED','at':'2026-11-09T00:00:00Z'})
    a=build(b,j['company_ids'],'2026-11-09T00:00:00Z',public=True)
    assert a['bundle']['policy_as_of']==j['bundle']['policy_as_of']
    assert a['as_of']=='2026-11-09T00:00:00Z'


def test_append_review_record_promotes_without_rewriting_revision(j):
    b=j['bundle'];b['exposures'][0].update(review_status='UNREVIEWED',reviewed_at=None)
    before=copy.deepcopy(b);old=b['review_records'].pop(1)
    assert not any(e['exposure_id']=='e0' for e in view(j)['bundle']['exposures'])
    b['review_records'].append(old)
    assert next(e for e in view(j)['bundle']['exposures'] if e['exposure_id']=='e0')['review_status']=='REVIEWED'
    assert b['exposures'][0]['review_status']=='UNREVIEWED'


def test_p17_macro_gate_same_inputs_are_unchanged(j):
    from investment_system.qgv.playbook import load_config,_special
    cfg=load_config();tc={'members':[],'thresholds':{'basis':'v2'},'leader':False}
    facts={'value_trap_gate':False,'theme_weight_pct':0,'sector':'Technology'}
    before={on:_special(cfg,tc,facts,'CRISIS',False,macro_gate=on) for on in (False,True)}
    view(j);revise(j);view(j,as_of='2026-11-08T00:00:00Z')
    assert before=={on:_special(cfg,tc,facts,'CRISIS',False,macro_gate=on) for on in (False,True)}


def test_late_recorded_earlier_review_does_not_backfill(j):
    for r in j['bundle']['review_records']:
        if r['group']=='hypotheses' and r['id']=='h0':r['recorded_at']='2026-11-09T00:00:00Z'
    assert not any(h['hypothesis_id']=='h0' for h in view(j)['bundle']['hypotheses'])
