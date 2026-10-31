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
