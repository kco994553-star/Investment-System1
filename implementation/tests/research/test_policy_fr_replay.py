import copy
import json
from pathlib import Path
import pytest
from investment_system.research.policy_impact.federal_register import initial,plan,replay,DEFAULTS,url

NOW='2026-11-07T03:00:00Z';ACQ='2026-11-07T02:00:00Z'


def doc(n='2026-12345',title='Synthetic rule',pub='2026-11-01'):
    return {'document_number':n,'title':title,'publication_date':pub,'html_url':'https://www.federalregister.gov/documents/synthetic/'+n,'agencies':[{'name':'Synthetic Agency'}],'type':'Rule','effective_on':'2026-12-01'}


def response(rows,*,start='2026-11-01',end='2026-11-07',page=1,count=None,per=100,total=1):
    return {'data_kind':'SYNTHETIC','status':200,'acquired_at':ACQ,
      'request':{'start':start,'end':end,'page':page,'kind':'INCREMENTAL','url':url(start,end,page,per)},
      'body':{'count':len(rows) if count is None else count,'total_pages':total,'results':rows}}


def run(state,rs,**kw):return replay(state,rs,through='2026-11-07',now=NOW,**kw)


def test_repeat_and_content_revision_preserve_old_evidence():
    s=initial('2026-11-01');r=response([doc()]);a=run(s,[r]);b=run(a['state'],[r])
    assert a['state']['completed_through']=='2026-11-07' and len(b['state']['candidates'])==1
    assert b['changes']['DUPLICATE']==1 and b['changes']['CONTENT_CHANGED']==0
    old=copy.deepcopy(b['state']['documents']['FR:2026-12345']['versions'])
    revised=response([doc(title='Synthetic changed content')]);c=run(b['state'],[revised])
    versions=c['state']['documents']['FR:2026-12345']['versions']
    assert len(versions)==2 and all(versions[k]==v for k,v in old.items())
    assert all(x['status']=='UNREVIEWED' and x['policy_id'] is None and x['lifecycle_status']=='UNKNOWN' for x in c['state']['candidates'].values())


def test_late_correction_is_not_filtered_by_checkpoint_or_title():
    s=run(initial('2026-11-01'),[response([doc()])])['state']
    out=run(s,[response([doc(),doc('2026-12346','Correction of an earlier rule','2026-11-02')])])
    assert len(out['state']['candidates'])==2 and out['changes']['NEW_DOCUMENT']==1
    assert all(x['policy_relation']=='NOT_ESTABLISHED' for x in out['state']['candidates'].values())
    assert any(r['kind']=='TRACKED_DOCUMENT' for r in out['next_plan']['requests'])


def test_pagination_resume_and_checkpoint_only_after_complete_interval():
    c=dict(DEFAULTS,per_page=1);s=initial('2026-11-01')
    a=run(s,[response([doc()],count=2,total=2,per=1)],settings=c)
    assert a['state']['completed_through'] is None and a['state']['result']=='INCOMPLETE'
    assert a['next_plan']['requests'][0]['page']==2
    assert len([r for r in a['next_plan']['requests'] if r.get('start')=='2026-11-01' and r.get('end')=='2026-11-07'])==1
    b=run(a['state'],[response([doc('2026-12346')],count=2,total=2,per=1,page=2)],settings=c)
    assert b['state']['completed_through']=='2026-11-07' and b['state']['result']=='UPDATED'
    both=run(s,[response([doc()],count=2,total=2,per=1),response([doc('2026-12346')],count=2,total=2,per=1,page=2)],settings=c)
    assert both['state']['result']=='UPDATED'


@pytest.mark.parametrize('failure',['429','parse','truncated','page_limit'])
def test_failures_do_not_mean_unchanged_or_update_last_good(failure):
    s=initial('2026-11-01');r=response([doc()])
    if failure=='429':r.update(status=429,retry_after='3600')
    elif failure=='parse':r['body']='<html>not API JSON</html>'
    elif failure=='truncated':r['body']['count']=2
    else:r['body'].update(count=2100,total_pages=21)
    good={'bundle_id':'last-good','policy_as_of':'2026-10-31T00:00:00Z','policies':[{'kept':True}],
          'refresh':{'last_success_at':'2026-10-31T00:00:00Z'}}
    a=run(s,[r],last_good=good)
    assert a['state']['completed_through'] is None and a['state']['result'] in ('FAILED','INCOMPLETE')
    assert a['retained_good']['policy_as_of']==good['policy_as_of'] and a['retained_good']['refresh']['last_success_at']==good['refresh']['last_success_at']
    if failure=='page_limit':assert any(x['kind']=='SPLIT_RETRY' for x in a['next_plan']['requests'])


def test_429_cooldown_honored_without_request_and_parse_error_keeps_checkpoint():
    r=response([]);r.update(status=429,retry_after='7200');a=run(initial('2026-11-01'),[r])
    assert a['next_plan']['requests']==[]
    b=run(a['state'],[response([doc()])]);assert b['state']==a['state'] and b['actual_http_requests']==0


def test_completed_first_interval_survives_next_interval_failure():
    first=response([doc()],end='2026-11-03');bad=response([],start='2026-11-04');bad['status']=503
    out=run(initial('2026-11-01'),[first,bad])
    assert out['state']['completed_through']=='2026-11-03' and out['state']['result']=='FAILED'
    assert out['next_plan']['requests'][0]['start']=='2026-11-04'


def test_budget_partial_and_actual_cli_no_http(tmp_path):
    import subprocess,sys
    c=dict(DEFAULTS,max_requests=1,per_page=1)
    a=run(initial('2026-11-01'),[response([doc()],count=2,total=2,per=1),response([doc('2026-12346')],count=2,total=2,per=1,page=2)],settings=c)
    assert a['state']['result']=='INCOMPLETE' and a['state']['completed_through'] is None
    job={'mode':'fr-replay','state':initial('2026-11-01'),'responses':[response([doc()])],'through':'2026-11-07','now':NOW}
    path=tmp_path/'job.json';path.write_text(json.dumps(job));out=tmp_path/'out.json'
    cli=Path(__file__).parents[2]/'tools/policy_impact.py'
    r=subprocess.run([sys.executable,str(cli),'--job',str(path),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==0 and json.loads(out.read_text())['actual_http_requests']==0


def test_reappearing_old_content_is_a_reviewable_change_not_fake_revision():
    a=run(initial('2026-11-01'),[response([doc(title='A')])])
    original=copy.deepcopy(a['state']['documents']['FR:2026-12345']['versions'])
    b=response([doc(title='B')]);b['acquired_at']='2026-11-07T02:10:00Z'
    changed=run(a['state'],[b]);back=response([doc(title='A')]);back['acquired_at']='2026-11-07T02:20:00Z'
    out=run(changed['state'],[back]);ledger=out['state']['documents']['FR:2026-12345']
    assert out['changes']['CONTENT_CHANGED']==1 and out['state']['result']=='UPDATED'
    assert len(ledger['versions'])==2 and len(ledger['changes'])==3 and len(out['state']['candidates'])==2
    assert all(ledger['versions'][k]==v for k,v in original.items())


def test_duplicate_final_page_restarts_within_page_bounds():
    settings=dict(DEFAULTS,per_page=1)
    a=run(initial('2026-11-01'),[response([doc()],count=2,total=2,per=1)],settings=settings)
    out=run(a['state'],[response([doc()],count=2,total=2,per=1,page=2)],settings=settings)
    assert out['state']['completed_through'] is None and out['state']['result']=='INCOMPLETE'
    assert out['next_plan']['requests'][0]['page']==1


def test_future_interval_cannot_be_completed_by_earlier_response():
    r=response([]);r['acquired_at']='2026-11-01T00:00:00Z'
    out=run(initial('2026-11-01'),[r])
    assert out['state']['completed_through'] is None and out['attempts'][0]['reason']=='FR_RESPONSE_PREDATES_INTERVAL'


def test_split_retry_replaces_pending_range_and_one_day_block_persists():
    settings=dict(DEFAULTS,per_page=1)
    a=run(initial('2026-11-01'),[response([doc()],count=2,total=2,per=1)],settings=settings)
    too_many=response([]);too_many['body'].update(count=2100,total_pages=21)
    out=run(a['state'],[too_many],settings=settings)
    assert len(out['state']['split_ranges'])==2 and not out['state']['ranges']
    assert all(r.get('kind')!='RESUME' for r in out['next_plan']['requests'])
    too_many=response([],start='2026-11-07');too_many['body'].update(count=2100,total_pages=21)
    blocked=run(initial('2026-11-07'),[too_many]);again=run(blocked['state'],[])
    assert again['state']['result']=='INCOMPLETE' and again['next_plan']['requests']==[]
    assert again['next_plan']['blocked_ranges'][0]['reason']=='ONE_DAY_SCOPE_REFINEMENT_REQUIRED'


def test_large_retry_after_retains_failed_state_without_overflow():
    r=response([]);r.update(status=429,retry_after='9'*60)
    out=run(initial('2026-11-01'),[r])
    assert out['state']['result']=='FAILED' and out['next_plan']['requests']==[]
    assert out['state']['retry_at'].startswith('9999-')


def test_split_child_resumes_page_two_and_changed_counts_restart_page_one():
    settings=dict(DEFAULTS,per_page=1)
    state=initial('2026-11-01');state['split_ranges']=[{'start':'2026-11-01','end':'2026-11-03'}]
    first=response([doc()],end='2026-11-03',count=2,total=2,per=1)
    a=run(state,[first],settings=settings)
    matching=[r for r in a['next_plan']['requests'] if r.get('start')=='2026-11-01' and r.get('end')=='2026-11-03']
    assert len(matching)==1 and matching[0]['page']==2
    changed=response([doc('2026-12346')],end='2026-11-03',count=3,total=3,page=2,per=1)
    b=run(a['state'],[changed],settings=settings)
    assert b['attempts'][0]['reason']=='FR_CHANGED_PAGINATION_RESTART'
    assert b['next_plan']['requests'][0]['page']==1 and b['state']['completed_through'] is None


def test_cli_private_kind_comes_from_replay_state_not_legacy_bundle(tmp_path):
    import subprocess,sys
    checkout=tmp_path/'checkout';checkout.mkdir();(checkout/'.git').write_text('synthetic worktree marker')
    job={'mode':'fr-replay','state':initial('2026-11-01',data_kind='RETAINED_API'),
         'bundle':{'data_kind':'SYNTHETIC'},'responses':[],'through':'2026-11-07','now':NOW}
    path=tmp_path/'job.json';path.write_text(json.dumps(job));out=checkout/'private.json'
    cli=Path(__file__).parents[2]/'tools/policy_impact.py'
    result=__import__('subprocess').run([sys.executable,str(cli),'--job',str(path),'--output',str(out)],capture_output=True,text=True)
    assert result.returncode==2 and json.loads(result.stdout)['code']=='PRIVATE_OUTPUT_REQUIRED' and not out.exists()


def test_raw_only_child_agency_remains_source_label_not_verified_agency():
    from investment_system.research.policy_impact.federal_register import normalize
    row=doc();row['agencies'].append({'raw_name':'SYNTHETIC Office label'})
    n=normalize(row)
    assert n['agencies']==['Synthetic Agency']
    assert n['raw_agency_names']==['SYNTHETIC Office label']
    assert n['agency_name_status']=='PARTIAL_CANONICAL_NAMES'
    result=replay(initial('2026-11-01'),[response([row],end='2026-11-01')],through='2026-11-01',now=NOW)
    assert result['changes']['NEW_DOCUMENT']==1
    candidate=next(iter(result['state']['candidates'].values()))
    assert candidate['status']=='UNREVIEWED' and candidate['policy_id'] is None
    assert candidate['company_applicability']=='UNKNOWN' and not candidate['automatic_publication']


def test_all_raw_agency_labels_keep_canonical_authority_unknown():
    from investment_system.research.policy_impact.federal_register import normalize
    row=doc();row['agencies']=[{'raw_name':'SYNTHETIC only raw label'}]
    n=normalize(row)
    assert n['agencies']==[] and n['agency_name_status']=='RAW_LABEL_ONLY'
    # Normal responses retain their previous normalized bytes/content hash.
    unchanged=normalize(doc())
    assert 'raw_agency_names' not in unchanged and 'agency_name_status' not in unchanged


@pytest.mark.parametrize('agency',[{}, {'raw_name':7}, {'name':7,'raw_name':'SYNTHETIC'}])
def test_malformed_agency_is_still_rejected(agency):
    from investment_system.research.policy_impact.federal_register import normalize
    row=doc();row['agencies']=[agency]
    with pytest.raises(ValueError,match='FR_AGENCY_MISSING'):normalize(row)
