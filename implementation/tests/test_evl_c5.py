from dataclasses import replace
from datetime import timedelta
import json
import pytest
from tests.test_evl_c2 import contract,c0_split,dt
from tests.test_evl_c4 import rows
from investment_system.evl import ExperimentSpec,ParameterSpace,SearchBudget,MetricSet
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.splits import register_split
from investment_system.evl.walkforward import dataset_digest
from investment_system.evl.search import register_search,run_search,STAGES


def setup(path, *, complexity=2, precision=2, budget=100, data=None, baseline=None):
    if data is None:
        r=rows()[0]
        data=tuple(replace(r,sample=replace(r.sample,sample_id='train'+str(i),
            decision_time=r.sample.decision_time+timedelta(days=i),
            label_end=r.sample.label_end+timedelta(days=i),
            label_available_at=r.sample.label_available_at+timedelta(days=i))) for i in range(4))
    ledger=ExperimentLedger(path)
    c=contract()
    ledger.register(ExperimentSpec('search',dt(2020),dt(2016),'synthetic','v1',dataset_digest(data),
        'fixture-code',7,ParameterSpace({'cash_buffer':[0.,.1,.2],'technical_lookback':[1,2,3]},complexity,precision),
        SearchBudget(budget),c0_split(c),MetricSet(('score',))))
    register_split(ledger,c)
    plan={'baseline':baseline or {'cash_buffer':0.,'technical_lookback':1},
        'coarse':{'cash_buffer':[0.,.2],'technical_lookback':[1,3]},
        'directions':{'score':'max'},'levels':[{'size':2,'cutoffs':{'score':0.}},
        {'size':4,'cutoffs':{'score':0.}}],'evaluator_id':'fixture','variant':'PRIMARY','registered_at':dt(2020).isoformat()}
    return ledger,c,data,plan


def run(setup_value,evaluate=lambda p,r,s:{'score':1.}):
    ledger,c,data,plan=setup_value
    register_search(ledger,c,data,plan)
    return run_search(ledger,c,data,evaluator_id='fixture',evaluate=evaluate,recorded_at=dt(2020))


def test_grid_order_refinement_all_survivors_and_no_peak_selection(tmp_path):
    args=setup(tmp_path)
    calls=[]
    def evaluate(p,rows,seed):
        calls.append((p,len(rows),seed))
        assert all(r.sample.sample_id.startswith('train') for r in rows)
        return {'score':1.+p['cash_buffer']}
    result=run(args,evaluate)
    assert result['status']=='COMPLETED'
    assert tuple(r['stage'] for r in result['stages'])==STAGES
    assert [r['stage'] for r in result['stages'] if r['status']=='NO_ELIGIBLE_BOUND_PARAMETER']==['QGV','Macro','Integration']
    assert len(result['survivors'])==9 and len(calls)==18
    assert {n for _,n,_ in calls}=={2,4} and all(s==7 for _,_,s in calls)
    assert result['selection']=='NONE_C7_REQUIRED' and not result['official']
    assert args[0].trials.verify()
    assert all(args[0].supporting_trial(r['trial_id']) for r in result['survivors'])


@pytest.mark.parametrize('kind',['complexity','precision','screen','exception','nan'])
def test_reject_stop_failure_accounting(tmp_path,kind):
    args=setup(tmp_path,complexity=0 if kind=='complexity' else 2,precision=0 if kind=='precision' else 2)
    def evaluate(p,rows,seed):
        if kind=='exception': raise RuntimeError('fixture failure')
        return {'score':float('nan') if kind=='nan' else -1. if kind=='screen' else 1.}
    result=run(args,evaluate)
    expected={'complexity':'REJECTED','precision':'REJECTED','screen':'EARLY_STOPPED','exception':'FAILED','nan':'FAILED'}[kind]
    trials=args[0].trials.records()
    assert expected in {r['trial']['status'] for r in trials}
    assert len(trials)==result['attempts'] and args[0].trials.verify()


def test_budget_never_calls_evaluator_after_limit_and_no_resume_resampling(tmp_path):
    args=setup(tmp_path,budget=1)
    calls=[]
    result=run(args,lambda *x: calls.append(x) or {'score':1.})
    assert result['status']=='BUDGET_EXHAUSTED' and len(calls)==1
    assert not result['survivors']
    with pytest.raises(ValueError,match='consumed'):
        run_search(args[0],args[1],args[2],evaluator_id='fixture',evaluate=lambda *x:None,recorded_at=dt(2020))


def test_validation_oos_and_missing_train_rejected_before_search(tmp_path):
    args=setup(tmp_path,data=rows())
    with pytest.raises(ValueError,match='only retained Train'):
        register_search(*args)
    assert not args[0].trials.records()


@pytest.mark.parametrize('change',['unbound','future_feature','changed_data','changed_plan','wrong_evaluator'])
def test_unqualified_inputs_fail_closed(tmp_path,change):
    args=setup(tmp_path)
    ledger,c,data,plan=args
    if change=='unbound':
        plan['baseline']['risk_multiplier']=1.
        with pytest.raises(ValueError): register_search(ledger,c,data,plan)
        return
    if change=='future_feature':
        from investment_system.evl.pit import PITObservation
        data=(replace(data[0],sample=replace(data[0].sample,observations=(PITObservation('bad',dt(2025),'f','v'),))),*data[1:])
        args=setup(tmp_path/'future',data=data)
        with pytest.raises(ValueError): register_search(*args)
        return
    register_search(ledger,c,data,plan)
    if change=='changed_data': data=(replace(data[0],outcome={'new':1}),*data[1:])
    if change=='changed_plan':
        p=tmp_path/'search.json'
        payload=json.loads(p.read_text());payload['body']['plan']['levels'][0]['size']=1
        p.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        run_search(ledger,c,data,evaluator_id='wrong' if change=='wrong_evaluator' else 'fixture',evaluate=lambda *x:None,recorded_at=dt(2020))
    assert not ledger.trials.records()
