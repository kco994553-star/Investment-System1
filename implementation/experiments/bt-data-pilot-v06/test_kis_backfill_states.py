"""Synthetic state transitions only; never actual price evidence."""
import pre2016_prices as p

def test_empty_rejection_and_auth_are_not_success():
    classify=getattr(p,'response_state',None)
    assert classify is not None,'state classifier must distinguish HTTP 200 rejection from data'
    assert classify(200,{'rt_cd':'0','output2':[]})=='EMPTY_RESPONSE'
    assert classify(200,{'rt_cd':'1','msg_cd':'OPSQ1002'})=='RETRYABLE_ERROR'
    assert classify(500,{'rt_cd':'1','msg_cd':'EGW00316'})=='RETRYABLE_ERROR'
    assert classify(429,{})=='BLOCKED'
    assert classify(401,{})=='BLOCKED'
    assert classify(200,{'rt_cd':'0','output2':[{}]})=='FETCHED'

def test_year_windows_skip_only_covered_sessions_and_leave_others_pending():
    planner=getattr(p,'year_tasks',None)
    assert planner is not None,'year queue is required instead of global provider rejection stop'
    expected={'ABT':{'2010-04-01','2010-04-05','2011-01-31'},'ACU':{'2010-04-01'}}
    acquired={'ABT':{'2010-04-01'},'ACU':set()}
    tasks=planner(expected,acquired)
    assert len(tasks)==3
    assert {(t['company'],t['year'],t['cursor'])for t in tasks}=={('ABT',2011,'20110131'),('ABT',2010,'20100405'),('ACU',2010,'20100401')}
    assert all(t['state']=='PENDING'for t in tasks)

def test_rejected_company_does_not_complete_or_block_other_company(tmp_path,monkeypatch):
    import json,hashlib,zipfile
    from unittest.mock import patch
    from pilot import encoded
    import github_kis_probe as k
    # A real archive/store and real queue; only external HTTP, delay and release upload are replaced.
    def archive(name):
        z=tmp_path/(name+'.zip')
        with zipfile.ZipFile(z,'w')as f:f.writestr('requests/','')
        (tmp_path/(name+'.zip.sha256')).write_text(hashlib.sha256(z.read_bytes()).hexdigest())
        return z
    cal=b',open,close\n2010-01-04,2010-01-04,2010-01-04\n'
    plan={'calendar':{'url':'https://example.invalid/calendar','sha256':hashlib.sha256(cal).hexdigest()},
          'routes':[{'company':c,'alias':c,'exchange':'NYS','start':'1900-01-01','end':'2010-12-31','identity_status':'SYNTHETIC'}for c in ['A','B']],
          'history_probe_dates':[]}
    path=tmp_path/'plan.json';path.write_bytes(encoded(plan))
    def acquire(store,aid,url,kind):store.put(aid,cal,url,kind,'text/csv','test',200)
    def transport(url,headers,payload=None):
        if payload:return 200,b'{"access_token":"synthetic-token"}','',.1
        if 'SYMB=A&'in url:return 200,b'{"rt_cd":"1","msg_cd":"OPSQ1002","msg1":"SESSION FULL"}','',.1
        return 200,b'{"rt_cd":"0","output2":[{"xymd":"20100104","open":"10","high":"10","low":"10","clos":"10","tvol":"1"}]}','',.1
    monkeypatch.setenv('GITHUB_ACTIONS','true');monkeypatch.setenv('GITHUB_RUN_ID','synthetic');monkeypatch.setenv('KIS_APP_KEY','synthetic-key');monkeypatch.setenv('KIS_APP_SECRET','synthetic-secret')
    monkeypatch.delenv('KIS_APPKEY',raising=False);monkeypatch.delenv('KIS_APPSECRET',raising=False)
    with patch('pilot.acquire',acquire),patch.object(p.release,'http',return_value=(200,{},b'{"private":true}')),patch.object(p,'checkpoint'),patch.object(k,'transport',transport),patch('time.sleep'):
        result=p.stable_run(tmp_path/'output',archive('old'),archive('resume'),path)
    state=json.loads((tmp_path/'output/stable-state.json').read_text())
    assert result['market_requests']==3
    assert state['token_issuances']==1 and state['token_refreshes']==0
    assert [(t['company'],t['state'])for t in state['tasks']]==[('A','RETRYABLE_ERROR'),('B','VALIDATED')]
    assert state['coverage'][0]['missing_sessions']==1
    assert state['coverage'][1]['missing_sessions']==0
