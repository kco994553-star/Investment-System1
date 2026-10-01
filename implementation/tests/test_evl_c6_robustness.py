from dataclasses import replace
from datetime import timedelta
import copy
import json
import math
import pytest
from tests.evl_c6_fixture import setup_family, run_family, full_acceptance, T
from investment_system.evl import TrialRecord, TrialStatus
from investment_system.evl.robustness import (MANDATORY, acceptance, register_robustness,
    run_robustness, resolve_robustness, package_hash, source_inventory)
from investment_system.evl.walkforward import digest
from investment_system.evl.statistical_kernels import circular_block_indices


def report(args,result,kind):
    return json.loads((args[0].directory/result['results'][kind]['report_file']).read_text())


def registered(args):
    register_robustness(*args)
    return args


def execute(args):
    return run_robustness(*args[:5],evaluator_id=args[5]['evaluator_id'],recorded_at=T)


def test_all_seventeen_methods_execute_with_full_lineage_and_immutable_inputs(tmp_path):
    args=setup_family(tmp_path)
    before=package_hash(*args[2:5])
    result=run_family(args)
    assert result['status']=='PASS',result['results']
    assert result['software_freeze_eligible'] and not result['real_pit_research_validated']
    assert result['decision']=='NOT_ASSESSED_PENDING_C8'
    assert set(result['results'])==set(MANDATORY)
    assert len(args[0].trials.records())==17 and args[0].trials.verify()
    assert package_hash(*args[2:5])==before
    assert resolve_robustness(*args[:5])==result
    for kind in MANDATORY:
        r=report(args,result,kind)
        assert r['status']=='PASS' and r['role']=='MANDATORY'
        assert r['scope']=='SYNTHETIC_SOFTWARE_VALIDATION'
        assert not r['official'] and r['holdout_state']=='UNCONSUMED'
        assert r['tax_mode']=='EXCLUDED'


def test_four_cohorts_are_preserved_separately_reproducible(tmp_path):
    first=full_acceptance(tmp_path/'a');second=full_acceptance(tmp_path/'b')
    assert first==second and first['status']=='PASS'
    assert set(first['cohorts'])=={m+'-'+v for m in ('ROLLING','EXPANDING')
            for v in ('PRIMARY','REBALANCE_GAP_STRESS')}
    assert first['real_pit_research_validation'].startswith('NOT_RUN')


def test_dsr_resolves_all_screening_attempts_and_distinct_identities(tmp_path):
    args=setup_family(tmp_path);result=run_family(args)
    a=report(args,result,'DSR_DISTINCT')['output']
    b=report(args,result,'DSR_ATTEMPTS')['output']
    assert a['trial_count']==2 and b['trial_count']==4
    assert a['count_provenance']!=b['count_provenance']
    assert b['all_attempt_ids']==['search-0','search-1','search-2','search-3']
    assert b['all_status_counts']['SUCCESS']==4
    assert not b['independent_trial_count_estimated']


def test_joint_dependence_and_both_shared_benchmark_family_tests(tmp_path):
    args=setup_family(tmp_path);result=run_family(args)
    bootstrap=report(args,result,'BOOTSTRAP')['output']
    assert bootstrap['sample_indices']==[list(i) for i in circular_block_indices(
        n=8,block_length=2,replicates=32,seed=7)]
    assert len(bootstrap['candidate_ids'])==2 and set(bootstrap['benchmark_ids'])=={'EQUAL','MCAP'}
    pbo=report(args,result,'CSCV_PBO')['output']
    assert pbo['partition_count']==math.comb(4,2)
    for kind,baseline in (('REALITY_EQUAL','EQUAL'),('REALITY_MCAP','MCAP')):
        r=report(args,result,kind)['output']
        assert r['benchmark_id']==baseline and len(r['candidate_ids'])==2
        assert r['decision']=='NOT_ASSESSED_PENDING_C8'


def test_perturbation_controls_drift_and_execution_change_actual_paths(tmp_path):
    args=setup_family(tmp_path);result=run_family(args)
    for kind in ('PARAMETER','REGIME','UNIVERSE','RANDOM_RANKING','RANDOM_WEIGHTS'):
        r=report(args,result,kind)['output']
        assert any(any(abs(v)>1e-12 for v in delta) for delta in r['period_excess_deltas'].values())
    r=report(args,result,'EXECUTION_DELAY')['output']
    for k in r['baseline']['reports']:
        assert r['baseline']['reports'][k]['path_hash']!=r['one_opportunity_delay']['reports'][k]['path_hash']
    r=report(args,result,'COST_STRESS')['output']
    for k in r['1']['reports']:
        assert len({r[str(i)]['reports'][k]['path_hash'] for i in (1,2,3)})==1
        a,b=r['1']['net'][k],r['3']['net'][k]
        assert all(x>y for x,y in zip(a,b))
    drift=report(args,result,'DRIFT')['output']
    assert any(any(abs(v)>0 for d in h['scaled_deltas'] for v in d.values()) for h in drift.values())


@pytest.mark.parametrize('kind',MANDATORY)
def test_every_mandatory_fail_and_not_run_blocks_acceptance(kind):
    valid={k:{'status':'PASS','role':'MANDATORY','report_hash':'fixture','trial_id':k} for k in MANDATORY}
    for state in ('FAIL','NOT_RUN'):
        rows=copy.deepcopy(valid);rows[kind]['status']=state
        result=acceptance(rows,'SYNTHETIC_SOFTWARE_VALIDATION')
        assert result['status']=='NOT_ACCEPTED' and not result['software_freeze_eligible']
    del valid[kind]
    assert not acceptance(valid,'SYNTHETIC_SOFTWARE_VALIDATION')['software_freeze_eligible']


@pytest.mark.parametrize('kind',['baseline','scenario','short_series','source_failed'])
def test_missing_evidence_not_run_does_not_turn_into_diagnostic_pass(tmp_path,kind):
    args=list(setup_family(tmp_path))
    b=next(iter(args[3].values()))
    if kind=='baseline': b['baseline']=None
    if kind=='scenario': b['scenarios']['REGIME']['input']=None
    if kind=='short_series':
        b['scenarios']['REGIME']['input']=replace(b['scenarios']['REGIME']['input'],rows=())
    if kind=='source_failed':
        source=args[2];params=next(iter(source_inventory(source)['roster'].values()))
        source.append(TrialRecord('source-failed',source.registration()['experiment_id'],4,T,
            TrialStatus.FAILED,params,reason='explicit failure'))
    # Missing inputs are preregistered as missing; no fabricated fill.
    spec=args[0].registration()
    path=args[0].registration_path
    from hashlib import sha256
    spec['data_hash']=package_hash(*args[2:5])
    path.write_text(json.dumps({'spec':spec,'sha256':digest(spec)}))
    # Update the C2 binding to the new pre-result experiment hash.
    split=json.loads((args[0].directory/'split.json').read_text())
    split['split']['experiment_sha256']=digest(spec);split['sha256']=digest(split['split'])
    (args[0].directory/'split.json').write_text(json.dumps(split))
    result=run_family(args)
    assert result['status']=='NOT_ACCEPTED' and not result['software_freeze_eligible']
    if kind in ('baseline','source_failed'):
        assert all(r['status']=='NOT_RUN' for r in result['results'].values())
    else:
        assert result['results']['REGIME']['status']=='NOT_RUN'


@pytest.mark.parametrize('kind',['family_shrink','future_feature','future_rf','future_outcome',
    'holdout','changed_data','changed_definition','invalidated_c5','invalidated_c4','c4_tamper'])
def test_frozen_input_changes_and_invalidations_fail_all_acceptance(tmp_path,kind):
    args=registered(setup_family(tmp_path))
    b=next(iter(args[3].values()));data=b['baseline']
    if kind=='family_shrink': args[3].pop(next(iter(args[3])))
    if kind in ('future_feature','holdout'):
        row=data.rows[0];s=row.sample
        if kind=='future_feature':
            s=replace(s,observations=(replace(s.observations[0],available_at=s.label_end),))
        else: s=replace(s,decision_time=T)
        b['baseline']=replace(data,rows=(replace(row,sample=s),*data.rows[1:]))
    if kind in ('future_rf','future_outcome'):
        row=data.rows[0];field='risk_free_stamp' if kind=='future_rf' else 'outcome_stamp'
        changed=replace(getattr(row.period,field),available_at=T+timedelta(days=1))
        b['baseline']=replace(data,rows=(replace(row,period=replace(row.period,**{field:changed})),*data.rows[1:]))
    if kind=='changed_data': b['baseline']=replace(data,initial_cash=1001.)
    if kind=='changed_definition': b['scenarios']['REGIME']['definition']['regime']='changed'
    if kind.startswith('invalidated'):
        source=args[2] if kind=='invalidated_c5' else b['c4_ledger']
        tid=source.trials.records()[0]['trial']['trial_id']
        source.append(TrialRecord('invalid',source.registration()['experiment_id'],
            len(source.trials.records()),T,TrialStatus.INVALIDATED,{},reason='upstream invalid',parent_trial_id=tid))
    if kind=='c4_tamper':
        from hashlib import sha256
        path=b['c4_ledger'].directory/('report-'+sha256(b['c4_trial_id'].encode()).hexdigest()+'.json')
        r=json.loads(path.read_text());r['predictions']={};path.write_text(json.dumps(r))
    result=execute(args)
    assert result['status']=='NOT_ACCEPTED'
    assert all(r['status']=='FAIL' for r in result['results'].values())
    assert len(args[0].trials.records())==17


@pytest.mark.parametrize('kind',['report','acceptance','source_report','c4_runner','invalidation'])
def test_saved_pass_is_revoked_by_current_lineage_or_artifact_tamper(tmp_path,kind):
    args=setup_family(tmp_path);result=run_family(args)
    if kind=='report':
        path=args[0].directory/result['results']['PSR']['report_file']
        row=json.loads(path.read_text());row['output']={};path.write_text(json.dumps(row))
    if kind=='acceptance':
        path=args[0].directory/'robustness-acceptance.json'
        row=json.loads(path.read_text());row['official']=True;path.write_text(json.dumps(row))
    if kind=='source_report':
        path=args[2].directory/'search-0.json'
        row=json.loads(path.read_text());row['metrics']={'score':99.};path.write_text(json.dumps(row))
    if kind=='c4_runner':
        path=next(iter(args[3].values()))['c4_ledger'].directory/'runner.json'
        path.write_text('{}')
    if kind=='invalidation':
        args[0].append(TrialRecord('revoke',args[0].registration()['experiment_id'],17,T,
            TrialStatus.INVALIDATED,{},reason='dataset invalidated',
            parent_trial_id=result['results']['PSR']['trial_id']))
    with pytest.raises((ValueError,KeyError)):
        resolve_robustness(*args[:5])


def test_budget_and_crash_keep_terminal_charge_no_retry(tmp_path):
    args=setup_family(tmp_path/'budget',budget=2);result=run_family(args)
    assert result['status']=='NOT_ACCEPTED' and len(args[0].trials.records())==2
    assert result['results']['DSR_ATTEMPTS']['status']=='NOT_RUN'
    args=registered(setup_family(tmp_path/'crash'))
    (args[0].directory/'pending.json').write_text(json.dumps({'trial_id':'interrupted','parameters':{}}))
    with pytest.raises(ValueError,match='consumed'): execute(args)
    assert args[0].trials.records()[0]['trial']['status']=='FAILED'


@pytest.mark.parametrize('kind',['holdout_partition','wrong_method','wrong_seed','wrong_holdout_boundary',
    'late_registration','bad_scope','odd_blocks','unregistered_parameters'])
def test_unapproved_contracts_rejected_before_diagnostics(tmp_path,kind):
    args=setup_family(tmp_path);plan=args[5]
    if kind=='holdout_partition': plan['partition']='holdout'
    if kind=='wrong_method': plan['method_version']='guessed'
    if kind=='wrong_seed': plan['seed']=8
    if kind=='wrong_holdout_boundary': plan['holdout_start']=T.isoformat()
    if kind=='late_registration': plan['registered_at']=(T-timedelta(days=1)).isoformat()
    if kind=='bad_scope': plan['scope']='REAL_SKILL'
    if kind=='odd_blocks': plan['block_count']=3
    if kind=='unregistered_parameters':
        p=args[0].registration_path;r=json.loads(p.read_text());r['spec']['parameter_space']['values']={'risk_multiplier':[1.]}
        r['sha256']=digest(r['spec']);p.write_text(json.dumps(r))
    with pytest.raises(ValueError): register_robustness(*args)
    assert not args[0].trials.records()


def test_synthetic_input_cannot_support_real_pit_claim(tmp_path):
    args=setup_family(tmp_path);args[5]['scope']='REAL_PIT_RESEARCH_VALIDATION'
    result=run_family(args)
    assert result['status']=='NOT_ACCEPTED' and not result['real_pit_research_validated']
    assert all(r['status']=='FAIL' for r in result['results'].values())


def test_diagnostic_not_run_for_zero_variance_and_failed_scenario_integrity(tmp_path):
    args=setup_family(tmp_path/'variance');args[5]['block_length']=99
    result=run_family(args)
    assert result['results']['BOOTSTRAP']['status']=='NOT_RUN'
    assert result['status']=='NOT_ACCEPTED'
    args=setup_family(tmp_path/'scenario')
    for b in args[3].values():
        d=b['scenarios']['PARAMETER']['definition']
        d['parameters']={'risk_multiplier':1.}
        inp=b['scenarios']['PARAMETER']['input']
        b['scenarios']['PARAMETER']['input']=replace(inp,rows=tuple(
            replace(r,orders=tuple(replace(o,source_ref=digest(d)) for o in r.orders)) for r in inp.rows))
    spec=args[0].registration()
    spec['data_hash']=package_hash(*args[2:5])
    args[0].registration_path.write_text(json.dumps({'spec':spec,'sha256':digest(spec)}))
    split=json.loads((args[0].directory/'split.json').read_text())
    split['split']['experiment_sha256']=digest(spec);split['sha256']=digest(split['split'])
    (args[0].directory/'split.json').write_text(json.dumps(split))
    result=run_family(args)
    assert result['results']['PARAMETER']['status']=='FAIL'
    assert result['status']=='NOT_ACCEPTED'
