from dataclasses import replace
from datetime import timedelta
import json
import pytest
from tests.test_evl_c2 import contract, c0_split, dt, sample
from tests.test_evl_c4_bindings import inputs, indicators, portfolio, D
from investment_system.evl import ExperimentSpec, ParameterSpace, SearchBudget, MetricSet
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.bindings import evaluate_bound
from investment_system.evl.metrics import ReturnPeriod
from investment_system.evl.pit import PITObservation
from investment_system.evl.splits import register_split, annual_splits
from investment_system.evl.walkforward import LearningRow, Pipeline, RunnerContract, dataset_digest, register_runner, run_fold, run_annual


def rows():
    return tuple(LearningRow(sample(name, day, day+timedelta(days=1)), {'known':1}, {'a':ret,'b':-.001})
        for name,day,ret in (('train',dt(2014,6),.002),('validation',dt(2015,6),.003),
                            ('oos1',dt(2016,6),.004),('oos2',dt(2016,6,2),-.002)))


def pipeline(events):
    def fit(train,parameters,seed):
        events.append(('fit',tuple(r.sample.sample_id for r in train),seed))
        return {'parameters':parameters,'train_ids':[r.sample.sample_id for r in train]}
    def calibrate(model,validation,seed):
        events.append(('calibrate',tuple(r.sample.sample_id for r in validation),seed))
        return {'fixture_threshold':0}
    def predict(model,thresholds,features):
        output={}
        for row in features:
            assert set(row)=={'sample_id','decision_time','features'}
            shift=row['decision_time']-D
            def move(p):
                return replace(p,measured_at=p.measured_at+shift,stamp=replace(p.stamp,
                    published_at=p.stamp.published_at+shift,available_at=p.stamp.available_at+shift,
                    observed_at=p.stamp.observed_at+shift))
            result=evaluate_bound(row['decision_time'],replace(portfolio(),snapshot_at=row['decision_time']),
                {k:tuple(move(p) for p in v) for k,v in inputs().items()},
                {k:move(p) for k,p in indicators().items()},model['parameters'],synthetic=True)
            output[row['sample_id']]=result['integration'].target_weights
        events.append(('predict',tuple(output)))
        return output
    def evaluate(predictions,outcomes):
        events.append(('evaluate',tuple(r.sample.sample_id for r in outcomes)))
        periods=[]
        for row in outcomes:
            s=row.sample
            gross=sum(w*row.outcome[k] for k,w in predictions[s.sample_id].items())
            periods.append(ReturnPeriod(s.decision_time,s.label_end,gross,0.,0.,0.,.001,0.,'USD',
                PITObservation('rf',s.decision_time,'fixture','v1'),
                PITObservation('outcome',s.label_end,'fixture','v1'),
                PITObservation('inflation',s.label_end,'fixture','v1')))
        return tuple(periods)
    return Pipeline('integrated-fixture-v1',fit,calibrate,predict,evaluate)


def job(path,*,data=None,split=None,budget=2,events=None):
    data=rows() if data is None else data
    split=contract() if split is None else split
    ledger=ExperimentLedger(path)
    ledger.register(ExperimentSpec('exp',dt(2020),dt(2016),'synthetic','v1',dataset_digest(data),
        'fixture-code-v1',7,ParameterSpace({'cash_buffer':[0.,.2]},1,1),SearchBudget(budget),
        c0_split(split),MetricSet(('net_cagr',))))
    register_split(ledger,split)
    runner=RunnerContract('integrated-fixture-v1',252,.05,dt(2017),dt(2020))
    register_runner(ledger,split,runner,data)
    return dict(ledger=ledger,split=split,runner=runner,rows=data,
        pipeline=pipeline([] if events is None else events),parameters={'cash_buffer':.2},
        trial_prefix='trial',recorded_at=dt(2020))


def reports(j,result):
    return [json.loads((j['ledger'].directory/r['report_file']).read_text()) for r in result['variants']]


def test_integrated_partition_isolation_frozen_model_and_paired_reports(tmp_path):
    events=[]
    j=job(tmp_path,events=events)
    result=run_fold(**j)
    assert result['status']=='COMPLETED' and result['official'] is False
    assert events==[('fit',('train',),7),('calibrate',('validation',),7),
        ('predict',('oos1','oos2')),('evaluate',('oos1','oos2'))]*2
    records=j['ledger'].trials.records()
    assert len(records)==2 and j['ledger'].trials.verify()
    for stored,terminal in zip(reports(j,result),records):
        assert stored['model']['parameters']=={'cash_buffer':.2}
        assert stored['tax_mode']=='EXCLUDED'
        assert 'report_sha256=' in terminal['trial']['reason']
    assert {r['variant'] for r in reports(j,result)}=={'PRIMARY','REBALANCE_GAP_STRESS'}


def test_oos_labels_cannot_change_fitted_model_or_predictions(tmp_path):
    a=job(tmp_path/'a')
    changed=tuple(replace(r,outcome={'a':.08,'b':.02}) if r.sample.sample_id.startswith('oos') else r for r in rows())
    b=job(tmp_path/'b',data=changed)
    ra,rb=reports(a,run_fold(**a)),reports(b,run_fold(**b))
    assert ra[0]['model_hash']==rb[0]['model_hash']
    assert ra[0]['prediction_hash']==rb[0]['prediction_hash']
    assert ra[0]['metrics_report']!=rb[0]['metrics_report']


@pytest.mark.parametrize('corruption',['data','split','runner','pipeline','parameter'])
def test_preregistration_corruption_rejected_before_fit(tmp_path,corruption):
    events=[]
    j=job(tmp_path,events=events)
    if corruption=='data': j['rows']=tuple(replace(r,features={'known':2}) for r in rows())
    if corruption in ('split','runner'): (tmp_path/(corruption+'.json')).write_text('{}')
    if corruption=='pipeline': j['pipeline']=replace(j['pipeline'],pipeline_id='different')
    if corruption=='parameter': j['parameters']={'cash_buffer':.9}
    with pytest.raises(ValueError): run_fold(**j)
    assert not events and not j['ledger'].trials.records()


@pytest.mark.parametrize('failure',['calibration_mutation','prediction_mutation','coverage','outcome_period','nonfinite'])
def test_failed_execution_recorded_for_both_variants(tmp_path,failure):
    j=job(tmp_path)
    p=j['pipeline']
    if failure=='calibration_mutation':
        def mutate(model,validation,seed):
            model['parameters']['cash_buffer']=.9
            return {}
        p=replace(p,calibrate=mutate)
    if failure=='prediction_mutation':
        def mutate(model,thresholds,features):
            thresholds['new']=1
            return {}
        p=replace(p,predict=mutate)
    if failure=='coverage': p=replace(p,predict=lambda *args:{})
    if failure in ('outcome_period','nonfinite'):
        def bad(predictions,outcomes):
            periods=pipeline([]).evaluate(predictions,outcomes)
            field={'start':dt(2015)} if failure=='outcome_period' else {'gross_return':float('nan')}
            return (replace(periods[0],**field),*periods[1:])
        p=replace(p,evaluate=bad)
    result=run_fold(**{**j,'pipeline':p})
    assert result['status']=='NOT_ACCEPTED'
    assert [r['trial']['status'] for r in j['ledger'].trials.records()]==['FAILED']*2


def test_budget_stops_before_fit_and_duplicate_identity_cannot_rerun(tmp_path):
    events=[]
    j=job(tmp_path,budget=4,events=events)
    run_fold(**j)
    with pytest.raises(ValueError,match='identity'): run_fold(**j)
    run_fold(**{**j,'trial_prefix':'second'})
    count=len(events)
    assert run_fold(**{**j,'trial_prefix':'third'})['status']=='NOT_RUN_BUDGET'
    assert len(events)==count


def test_empty_partition_records_rejection_without_engine(tmp_path):
    events=[]
    j=job(tmp_path,data=rows()[1:],events=events)
    assert run_fold(**j)['status']=='NOT_ACCEPTED' and not events
    assert [r['trial']['status'] for r in j['ledger'].trials.records()]==['REJECTED']*2


def test_annual_compares_modes_and_refits_each_variant(tmp_path):
    events=[]
    jobs=tuple(job(tmp_path/str(i),split=replace(contract(),plan=p),events=events)
               for i,p in enumerate(annual_splits(dt(2010),dt(2017))))
    with pytest.raises(ValueError,match='missing'): run_annual(jobs[:1],start=dt(2010),end=dt(2017))
    assert not events
    assert all(r['status']=='COMPLETED' for r in run_annual(jobs,start=dt(2010),end=dt(2017)))
    assert sum(e[0]=='fit' for e in events)==4


def test_interrupted_attempt_recovers_as_failed_consuming_budget(tmp_path):
    j=job(tmp_path)
    (tmp_path/'pending.json').write_text(json.dumps({'trial_id':'interrupted','parameters':{'cash_buffer':.2}}))
    assert run_fold(**j)['status']=='NOT_RUN_BUDGET'
    assert j['ledger'].trials.records()[0]['trial']['status']=='FAILED'
    assert not (tmp_path/'pending.json').exists()
