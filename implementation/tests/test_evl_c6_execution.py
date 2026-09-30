from dataclasses import replace
from datetime import timedelta
import json
import pytest
from tests.test_evl_c2 import dt, contract, c0_split, sample
from investment_system.contracts.lineage import StampedValue
from investment_system.contracts.models import DataStamp
from investment_system.evl import ExperimentSpec, ParameterSpace, SearchBudget, MetricSet, TrialRecord, TrialStatus
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.pit import PITObservation
from investment_system.evl.metrics import ReturnPeriod
from investment_system.evl.splits import register_split
from investment_system.evl.execution import (Opportunity, Order, ExecutionRow, ExecutionInput,
    input_hash, register_execution, run_execution, evaluate_execution, execution_report)


D=dt(2014,6)
E=D+timedelta(days=1)
T=dt(2020)


def point(value, time, name):
    return StampedValue(value,time,DataStamp(name,'fixture','EXECUTION',name,
        time,time,T,synthetic=True),'v1')


def data():
    p=ReturnPeriod(D,E,0.,0.,0.,0.,0.,0.,'USD',
        PITObservation('rf',D,'fixture','v1'),
        PITObservation('out',E,'fixture','v1'),
        PITObservation('cpi',E,'fixture','v1'))
    slots=tuple(Opportunity('s'+str(i),'a',D+timedelta(minutes=i*5),True,'calendar-v1') for i in (1,2,3))
    order=Order('buy','a',2.,D,'frozen-explicit-order')
    return ExecutionInput((ExecutionRow(sample('train',D,E), (order,),p),),slots,
        {('buy','s1'):point(10.,slots[0].time,'p1'),('buy','s2'):point(11.,slots[1].time,'p2')},
        {('buy','s1'):point(.1,slots[0].time,'c1'),('buy','s2'):point(.1,slots[1].time,'c2')},
        100.,{}, {}, ({'a':point(12.,E,'mark')},),'USD','explicit-fixture-price',
        'explicit-cost-model',True,True)


def evaluate(value=None,delay=0,multiplier=1):
    return evaluate_execution(data() if value is None else value,split=contract(),
        partition='train',delay=delay,multiplier=multiplier,evaluation_time=T,
        periods_per_year=1,tail_fraction=1.)


def setup(path,value=None,budget=6):
    value=data() if value is None else value
    c=contract()
    ledger=ExperimentLedger(path)
    ledger.register(ExperimentSpec('execution',T,D,'fixture','v1',input_hash(value),'fixture-code',7,
        ParameterSpace({},0,0),SearchBudget(budget),c0_split(c),MetricSet(('net_total_return',))))
    register_split(ledger,c)
    plan={'registered_at':T.isoformat(),'evaluation_time':T.isoformat(),'partition':'train',
          'parameters':{},'evaluator_id':'TC-D3P-003_v1','periods_per_year':1,'tail_fraction':1.}
    return ledger,c,value,plan


def run(args):
    ledger,c,value,plan=args
    register_execution(ledger,c,value,plan)
    return run_execution(ledger,c,value,evaluator_id=plan['evaluator_id'],recorded_at=T)


def test_baseline_delay_use_actual_slots_with_cash_positions_and_no_shifted_return():
    a,b=evaluate(),evaluate(delay=1)
    assert a['path'][0]['fills'][0]['opportunity_id']=='s1'
    assert b['path'][0]['fills'][0]['opportunity_id']=='s2'
    assert a['path'][0]['cash_1x']==pytest.approx(79.9)
    assert a['path'][0]['positions']=={'a':2.}
    assert a['path'][0]['gross_pnl']==pytest.approx(4.)
    assert b['path'][0]['gross_pnl']==pytest.approx(2.)
    assert a['metrics_report']['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return']==pytest.approx(.039)
    assert b['metrics_report']['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return']==pytest.approx(.019)
    assert not a['official'] and a['claim']=='SOFTWARE_FIXTURE'


def test_cost_stress_isolates_cost_preserves_gross_fills_and_path():
    reports=[evaluate(multiplier=m) for m in (1,2,3)]
    assert len({r['path_hash'] for r in reports})==1
    assert all(r['path']==reports[0]['path'] for r in reports)
    assert [r['metrics_report']['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return']
        for r in reports]==pytest.approx([.039,.038,.037])
    assert all(r['metrics_report']['views']['GROSS_PRE_TAX']==reports[0]['metrics_report']['views']['GROSS_PRE_TAX'] for r in reports)


def test_no_price_skip_missing_quote_rejects_and_all_six_attempts_retained(tmp_path):
    value=data()
    prices=dict(value.prices); del prices['buy','s2']
    value=replace(value,prices=prices)
    args=setup(tmp_path,value)
    result=run(args)
    records=args[0].trials.records()
    assert len(records)==6 and args[0].trials.verify()
    assert [r['trial']['status'] for r in records]==['SUCCESS']*3+['REJECTED']*3
    assert result['status']=='NOT_ACCEPTED'
    for r in result['results'][3:]:
        report=json.loads((tmp_path/r['report_file']).read_text())
        assert 'missing execution provenance' in report['reason']
        assert 'metrics_report' not in report


@pytest.mark.parametrize('kind',['future','vintage','estimated','synthetic','naive','publication','negative_cost'])
def test_execution_provenance_fail_closed(kind):
    value=data()
    prices=dict(value.prices); costs=dict(value.costs)
    p=prices['buy','s1']
    if kind=='future': p=replace(p,stamp=replace(p.stamp,available_at=T+timedelta(days=1)))
    if kind=='vintage': p=replace(p,vintage='')
    if kind=='estimated': p=replace(p,stamp=replace(p.stamp,estimated=True))
    if kind=='synthetic': value=replace(value,synthetic=False)
    if kind=='naive': p=replace(p,measured_at=p.measured_at.replace(tzinfo=None))
    if kind=='publication': p=replace(p,stamp=replace(p.stamp,available_at=D,published_at=D))
    if kind=='negative_cost': costs['buy','s1']=replace(costs['buy','s1'],value=-.1)
    prices['buy','s1']=p
    with pytest.raises(ValueError):
        evaluate(replace(value,prices=prices,costs=costs))


@pytest.mark.parametrize('kind',['holdout','crossing','future_feature','mixed_partition'])
def test_research_input_isolation(kind,tmp_path):
    value=data(); row=value.rows[0]
    if kind=='holdout': row=replace(row,sample=sample('holdout',dt(2017)))
    if kind=='crossing': row=replace(row,sample=sample('train',dt(2016,12,20)))
    if kind=='future_feature':
        row=replace(row,sample=replace(row.sample,observations=(PITObservation('future',E,'fixture','v1'),)))
    if kind=='mixed_partition': row=replace(row,sample=sample('validation',dt(2015,6)))
    args=setup(tmp_path,replace(value,rows=(row,)))
    with pytest.raises(ValueError):
        register_execution(*args)
    assert not args[0].trials.records()


def test_all_six_scenarios_hash_bound_no_promotion_reproducible(tmp_path):
    args=setup(tmp_path/'a')
    before=input_hash(args[2])
    a=run(args); b=run(setup(tmp_path/'b'))
    assert a==b and a['status']=='COMPLETED' and not a['robustness_pass']
    assert input_hash(args[2])==before
    assert all(args[0].supporting_trial(r['trial_id']) for r in a['results'])
    for r in a['results']:
        report=json.loads((args[0].directory/r['report_file']).read_text())
        assert report['input_hash']==before and report['tax_mode']=='EXCLUDED'
    with pytest.raises(ValueError,match='consumed'):
        run_execution(args[0],args[1],args[2],evaluator_id='TC-D3P-003_v1',recorded_at=T)


@pytest.mark.parametrize('kind',['data','plan','evaluator'])
def test_changed_input_registration_or_evaluator_blocked(tmp_path,kind):
    args=setup(tmp_path)
    ledger,c,value,plan=args
    register_execution(*args)
    if kind=='data': value=replace(value,initial_cash=101.)
    if kind=='plan':
        p=tmp_path/'execution.json'
        stored=json.loads(p.read_text());stored['body']['plan']['partition']='oos'
        p.write_text(json.dumps(stored))
    with pytest.raises(ValueError):
        run_execution(ledger,c,value,evaluator_id='wrong' if kind=='evaluator' else plan['evaluator_id'],recorded_at=T)
    assert not ledger.trials.records()


@pytest.mark.parametrize('kind',['cash','positions','cost_double_count','no_delay_slot','same_time','insolvency'])
def test_undefined_execution_models_rejected(kind):
    value=data()
    if kind=='cash': value=replace(value,initial_cash=1.)
    if kind=='positions': value=replace(value,rows=(replace(value.rows[0],orders=(replace(value.rows[0].orders[0],quantity=-2.),)),))
    if kind=='cost_double_count': value=replace(value,costs_exclude_price_embedded_components=False)
    if kind=='no_delay_slot': value=replace(value,opportunities=value.opportunities[:1])
    if kind=='same_time':
        row=value.rows[0]
        value=replace(value,rows=(replace(row,orders=(*row.orders,replace(row.orders[0],order_id='other'))),))
    if kind=='insolvency':
        costs={k:replace(v,value=50.) for k,v in value.costs.items()}
        value=replace(value,costs=costs)
    with pytest.raises(ValueError):
        evaluate(value,delay=1 if kind=='no_delay_slot' else 0,multiplier=3 if kind=='insolvency' else 1)


def test_budget_and_interrupted_attempt_not_silently_resampled(tmp_path):
    args=setup(tmp_path/'budget',budget=2)
    r=run(args)
    assert r['status']=='NOT_RUN_BUDGET' and len(args[0].trials.records())==2
    args=setup(tmp_path/'crash')
    register_execution(*args)
    (args[0].directory/'pending.json').write_text(json.dumps({'trial_id':'crash','parameters':{}}))
    with pytest.raises(ValueError,match='consumed'):
        run_execution(args[0],args[1],args[2],evaluator_id='TC-D3P-003_v1',recorded_at=T)
    assert args[0].trials.records()[0]['trial']['status']=='FAILED'


def test_invalidation_revokes_execution_support(tmp_path):
    args=setup(tmp_path)
    result=run(args)
    trial_id=result['results'][0]['trial_id']
    args[0].append(TrialRecord('invalidate','execution',6,T,TrialStatus.INVALIDATED,{},reason='upstream invalid',parent_trial_id=trial_id))
    with pytest.raises(ValueError,match='invalidated'):
        args[0].supporting_trial(trial_id)


def test_eligible_slots_are_preregistered_and_exclude_at_decision():
    value=data()
    slots=(Opportunity('at-decision','a',D,True,'calendar'),*value.opportunities)
    assert evaluate(replace(value,opportunities=slots))['path'][0]['fills'][0]['opportunity_id']=='s1'
    slots=tuple(replace(o,eligible=False) if o.opportunity_id=='s1' else o for o in slots)
    assert evaluate(replace(value,opportunities=slots))['path'][0]['fills'][0]['opportunity_id']=='s2'


def test_multi_period_positions_and_cash_carried_until_next_fill():
    value=data(); row=value.rows[0]
    E2=E+timedelta(days=1)
    second=ExecutionRow(sample('train2',E,E2),(),replace(row.period,start=E,end=E2,
        risk_free_stamp=PITObservation('rf2',E,'fixture','v1'),
        outcome_stamp=PITObservation('out2',E2,'fixture','v1'),
        inflation_stamp=PITObservation('cpi2',E2,'fixture','v1')))
    value=replace(value,rows=(row,second),closing_marks=(*value.closing_marks,{'a':point(13.,E2,'mark2')}))
    report=evaluate(value)
    assert report['path'][1]['opening_equity']==pytest.approx(103.9)
    assert report['path'][1]['positions']=={'a':2.}
    assert report['path'][1]['cash_1x']==pytest.approx(79.9)
    assert report['path'][1]['gross_pnl']==pytest.approx(2.)


def test_persisted_input_lineage_and_report_tamper_rejected(tmp_path):
    args=setup(tmp_path)
    result=run(args)
    trial_id=result['results'][0]['trial_id']
    report=execution_report(args[0],trial_id)
    assert report['path'][0]['fills'][0]['opportunity_id']=='s1'
    registered=json.loads((tmp_path/'execution.json').read_text())['body']
    assert registered['input_evidence']['prices'][0][2]['stamp']['source_reference']
    assert registered['input_evidence']['rows'][0]['sample']['observations'][0]['source_id']=='features'
    path=tmp_path/result['results'][0]['report_file']
    changed=json.loads(path.read_text());changed['path'][0]['fills'][0]['price']=999.
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='hash'):
        execution_report(args[0],trial_id)


def test_execution_at_evaluation_never_passes_outcomes_to_decision_features():
    value=data()
    report=evaluate(value)
    assert value.prices['buy','s1'].stamp.available_at > value.rows[0].sample.decision_time
    assert report['path'][0]['fills'][0]['price']==10.
    assert all(obs.available_at <= value.rows[0].sample.decision_time
               for obs in value.rows[0].sample.observations)
    # No fitting/predicting callback exists in this post-decision evaluator.


def test_unsupported_delay_and_cost_multipliers_are_rejected():
    with pytest.raises(ValueError): evaluate(delay=2)
    with pytest.raises(ValueError): evaluate(multiplier=4)
    with pytest.raises(ValueError): evaluate(multiplier=True)
    with pytest.raises(ValueError): evaluate(delay=True)


@pytest.mark.parametrize('kind',['foreign_quote','holdout_quote','holdout_mark'])
def test_unused_holdout_or_foreign_execution_evidence_cannot_enter_registration(tmp_path,kind):
    value=data()
    if kind=='foreign_quote':
        value=replace(value,prices={**value.prices,('foreign','s1'):point(10.,D,'foreign')})
    if kind=='holdout_quote':
        slot=Opportunity('holdout-slot','a',dt(2017),True,'calendar')
        value=replace(value,opportunities=(*value.opportunities,slot),
            prices={**value.prices,('buy','holdout-slot'):point(10.,dt(2017),'holdout')})
    if kind=='holdout_mark':
        value=replace(value,closing_marks=({'a':point(12.,E,'mark'),'unused':point(1.,dt(2017),'holdout')},))
    args=setup(tmp_path,value)
    with pytest.raises(ValueError):
        register_execution(*args)
    assert not args[0].trials.records()
