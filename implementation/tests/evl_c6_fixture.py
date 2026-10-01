"""Explicit deterministic generic C6 SOFTWARE fixture; no real investor profile.

Upstream inputs are constructed before inference registration. C4 uses existing
bound QGV/Technical/Macro fixture evaluators; C5 logs both screening rungs.
Execution uses explicit quantities/quotes/costs, never a shifted return series.
"""
from dataclasses import replace
from datetime import timedelta
import random
from statistics import mean, variance

from tests.test_evl_c2 import dt, contract, c0_split, sample
from tests.test_evl_c4 import pipeline, rows as old_rows
from tests.test_evl_c6_execution import point
from investment_system.evl import ExperimentSpec, ParameterSpace, SearchBudget, MetricSet
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.splits import register_split, annual_splits
from investment_system.evl.walkforward import (LearningRow, RunnerContract, dataset_digest,
    register_runner, run_fold, digest)
from investment_system.evl.search import register_search, run_search
from investment_system.evl.execution import (ExecutionRow, ExecutionInput, Order,
    Opportunity, evaluate_execution)
from investment_system.evl.pit import PITObservation
from investment_system.evl.metrics import ReturnPeriod
from investment_system.evl.statistical_kernels import METHOD_VERSION, period_sharpe
from investment_system.evl.robustness import (source_inventory, c4_report, package_hash,
    register_robustness, run_robustness, resolve_robustness, SCENARIOS)

T=dt(2020)
CODE='C6_GENERIC_SYNTHETIC_EVALUATOR_v1'
EVALUATOR='integrated-fixture-v1'
DOMAIN={'cash_buffer':[0.,.2],'technical_lookback':[1]}
MOVES=(1.,-2.,3.,-1.,2.,-3.,4.,.5)


def learning_rows():
    train = tuple(replace(old_rows()[0],sample=sample('train'+str(i),dt(2014,6)+timedelta(days=i),
          dt(2014,6)+timedelta(days=i+1))) for i in range(4))
    validation = (old_rows()[1],)
    oos = tuple(LearningRow(sample('oos'+str(i),dt(2016,6)+timedelta(days=i),
          dt(2016,6)+timedelta(days=i+1)),{'known':1},{'a':v/100,'b':-v/200})
          for i,v in enumerate(MOVES))
    return train+validation+oos


def experiment(path,c,identity,data_hash,parameters,metrics,budget):
    ledger=ExperimentLedger(path)
    ledger.register(ExperimentSpec(identity,T,dt(2016),'GENERIC_SYNTHETIC','v1',
        data_hash,CODE,7,ParameterSpace(parameters,2,2),SearchBudget(budget),
        c0_split(c),MetricSet(tuple(metrics))))
    register_split(ledger,c)
    return ledger


def execution_input(samples, references, *, quantity, variation=1., fees=.1, label):
    # Explicit synthetic quantities and prices. No investor weights or actual alpha.
    slots=[];prices={};costs={};rows=[];marks=[]
    price=20.
    for i,(s,move) in enumerate(zip(samples,MOVES)):
        p=ReturnPeriod(s.decision_time,s.label_end,0.,0.,.0001,0.,0.,0.,'USD',
            PITObservation('rf'+str(i),s.decision_time,'GENERIC_SYNTHETIC','v1'),
            PITObservation('out'+str(i),s.label_end,'GENERIC_SYNTHETIC','v1'),
            PITObservation('cpi'+str(i),s.label_end,'GENERIC_SYNTHETIC','v1'))
        oid=label+'-order-'+str(i)
        order=Order(oid,'a',quantity,s.decision_time,references[i])
        rows.append(ExecutionRow(s,(order,),p))
        for j in (1,2):
            slot=Opportunity(label+'-slot-'+str(i)+'-'+str(j),'a',
                s.decision_time+timedelta(minutes=5*j),True,'synthetic-calendar-v1')
            slots.append(slot)
            # Each delay consumes an actual different post-decision price.
            prices[oid,slot.opportunity_id]=point(price+(j-1)*.1,slot.time,label+'-price-'+str(i)+'-'+str(j))
            costs[oid,slot.opportunity_id]=point(fees,slot.time,label+'-cost-'+str(i)+'-'+str(j))
        price += move*variation
        marks.append({'a':point(price,s.label_end,label+'-mark-'+str(i))})
    return ExecutionInput(tuple(rows),tuple(slots),prices,costs,1000.,{}, {},
        tuple(marks),'USD','EXPLICIT_SYNTHETIC_QUOTES_v1',
        'EXPLICIT_SYNTHETIC_MONETARY_COSTS_v1',True,True)


def setup_family(path, *, mode='ROLLING', variant='PRIMARY', budget=17):
    c=replace(contract(),plan=annual_splits(dt(2010),dt(2017))[0 if mode=='ROLLING' else 1])
    data=learning_rows()
    source=experiment(path/'source',c,'c5-'+mode+'-'+variant,dataset_digest(data[:4]),
        DOMAIN,('score',),20)
    plan={'baseline':{'cash_buffer':0.,'technical_lookback':1},
        'coarse':DOMAIN,'directions':{'score':'max'},
        'levels':[{'size':2,'cutoffs':{'score':-1.}},{'size':4,'cutoffs':{'score':-1.}}],
        'evaluator_id':EVALUATOR,'variant':variant,'registered_at':T.isoformat()}
    register_search(source,c,data[:4],plan)
    engine=pipeline([])
    def evaluate(parameters,train,seed):
        predictions=engine.predict({'parameters':parameters},{},tuple(r.predictor_input() for r in train))
        periods=engine.evaluate(predictions,train)
        return {'score':mean(p.gross_return for p in periods)}
    run_search(source,c,data[:4],evaluator_id=EVALUATOR,evaluate=evaluate,recorded_at=T)
    inventory=source_inventory(source)
    samples=tuple(r.sample for r in data[5:])
    bundles={};drift={}
    for number,(identity,parameters) in enumerate(sorted(inventory['roster'].items())):
        wf=experiment(path/('wf-'+identity),c,'wf-'+identity,dataset_digest(data),DOMAIN,('net_cagr',),2)
        runner=RunnerContract(EVALUATOR,252,.25,T,T)
        register_runner(wf,c,runner,data)
        run_fold(wf,c,runner,data,pipeline([]),parameters,trial_prefix='candidate',recorded_at=T)
        tid='candidate-'+variant
        predictions=c4_report(wf,tid)['predictions']
        refs=tuple(digest(predictions[s.sample_id]) for s in samples)
        quantity=2.*(1-parameters['cash_buffer'])
        baseline=execution_input(samples,refs,quantity=quantity,label='baseline-'+identity)
        scenarios={}
        rng=random.Random(7+number)
        security_ids=['a','b','c'];permutation=security_ids.copy();rng.shuffle(permutation)
        random_values=[rng.random() for _ in security_ids]
        random_weights={k:v/sum(random_values) for k,v in zip(security_ids,random_values)}
        for kind in SCENARIOS:
            definition={'kind':kind,'scenario_id':kind+'-'+identity,'candidate_id':identity,
                'snapshot_refs':['GENERIC_SYNTHETIC-snapshot-v1'],
                'evaluator_id':'GENERIC_SYNTHETIC_SCENARIO_PRODUCER_v1',
                'registered_at':T.isoformat(),'method':'EXPLICIT_GENERIC_SOFTWARE_SCENARIO'}
            q,variation,fee=quantity,1.,.1
            if kind=='PARAMETER':
                definition['parameters']={'cash_buffer':.1,'technical_lookback':1}
                q=1.8
            elif kind=='REGIME':
                definition['regime']='EXPLICIT_SYNTHETIC_VOLATILITY_1_5'
                variation=1.5
            elif kind=='UNIVERSE':
                definition['universe_ref']='GENERIC_SYNTHETIC-preregistered-subuniverse'
                q*=.75
            elif kind=='RANDOM_RANKING':
                definition.update(seed=7+number,security_ids=security_ids,permutation=permutation)
                q=1.+permutation.index('a')/4
            elif kind=='RANDOM_WEIGHTS':
                definition.update(seed=7+number,weights=random_weights)
                q=1.+random_weights['a']
            elif kind=='EQUAL_CONTROL':
                definition['weights']={'a':1/3,'b':1/3,'c':1/3}
                q,fee=1.,.1
            elif kind=='MCAP_CONTROL':
                definition['capitalization_ref']='GENERIC_SYNTHETIC-PIT-mcap-2-1-1'
                definition['weights']={'a':.5,'b':.25,'c':.25}
                q,fee=1.5,.1
            refs=tuple(digest(definition) for _ in samples)
            scenarios[kind]={'definition':definition,
                'input':execution_input(samples,refs,quantity=q,variation=variation,fees=fee,
                    label=kind+'-'+identity)}
        bundles[identity]={'c4_ledger':wf,'c4_trial_id':tid,'baseline':baseline,'scenarios':scenarios}
        drift[identity]=[{'time':dt(2014+i,6).isoformat(),'available_at':dt(2014+i,6).isoformat(),
            'parameters':{'cash_buffer':v,'technical_lookback':1},
            'source_ref':'GENERIC_SYNTHETIC-parameter-history-'+str(i),'vintage':'v1'}
            for i,v in enumerate((0.,parameters['cash_buffer']))]
    scores=[]
    for bundle in bundles.values():
        r=evaluate_execution(bundle['baseline'],split=c,partition='oos',delay=0,multiplier=1,
            evaluation_time=T,periods_per_year=252,tail_fraction=.25)
        values=tuple(f['gross_pnl']/f['opening_equity']-f['execution_cost']/f['opening_equity']-.0001
                     for f in r['path'])
        scores.append(period_sharpe(values))
    drift_plan={'registered_at':T.isoformat(),'evaluation_time':T.isoformat(),
        'scope':'SYNTHETIC_SOFTWARE_VALIDATION','partition':'oos','variant':variant,
        'evaluator_id':'C6_REGISTERED_RUNNER_v1','scenario_evaluator_id':'GENERIC_SYNTHETIC_SCENARIO_PRODUCER_v1',
        'seed':7,'method_version':METHOD_VERSION,'periods_per_year':252,'tail_fraction':.25,
        'reference_sharpe':0.,'sharpe_variance':variance(scores),'block_count':4,
        'block_length':2,'replicates':32,'quantiles':[0.,.5,1.],
        'quantile_convention':'EMPIRICAL_INVERSE_CDF',
        'perturbation_domains':{'cash_buffer':[0.,.1,.2],'technical_lookback':[1]},
        'holdout_start':c.holdout_start.isoformat(),
        'drift_convention':'REGISTERED_COORDINATE_DELTA_OVER_SCALE',
        'drift_scales':{'cash_buffer':.2,'technical_lookback':1}}
    diagnostic=experiment(path/'diagnostics',c,'c6-'+mode+'-'+variant,
        package_hash(source,bundles,drift),{},('diagnostic_complete',),budget)
    return diagnostic,c,source,bundles,drift,drift_plan


def run_family(args):
    ledger,c,source,bundles,drift,plan=args
    register_robustness(*args)
    return run_robustness(ledger,c,source,bundles,drift,
        evaluator_id=plan['evaluator_id'],recorded_at=T)


def full_acceptance(path):
    results={}
    for mode in ('ROLLING','EXPANDING'):
        for variant in ('PRIMARY','REBALANCE_GAP_STRESS'):
            key=mode+'-'+variant
            args=setup_family(path/key,mode=mode,variant=variant)
            result=run_family(args)
            if result['status']=='PASS':
                assert resolve_robustness(*args[:5])==result
            results[key]=result
    return {'scope':'SYNTHETIC_SOFTWARE_VALIDATION',
        'status':'PASS' if all(r['status']=='PASS' for r in results.values()) else 'NOT_ACCEPTED',
        'cohorts':results,'holdout_state':'UNCONSUMED','official':False,
        'real_pit_research_validation':'NOT_RUN_MISSING_COMPLETE_REAL_FAMILY',
        'decision':'NOT_ASSESSED_PENDING_C8','tax_mode':'EXCLUDED'}
