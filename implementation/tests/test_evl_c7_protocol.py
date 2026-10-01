"""Real C4/C5/C6 software path, immutable C7 evidence and blocked negative paths."""
from copy import deepcopy
from datetime import timedelta
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.evl_c7_fixture import prepare, T
from investment_system.evl.profile_selection import (register_selection, run_selection,
    resolve_selection, registration, STAGES)
from investment_system.evl.selection_contracts import validate_plan, FIXTURE_SCOPE
from investment_system.evl.landscape import checkpoint
from investment_system.evl.walkforward import digest, _write_json
from investment_system.evl.contracts import TrialRecord, TrialStatus

@pytest.fixture
def prepared(tmp_path):
    return prepare(tmp_path)

def execute(args):
    ledger,cohorts,plan=args
    register_selection(*args)
    result=run_selection(ledger,cohorts,recorded_at=T)
    return result

def overwrite(path,body):
    path.write_text(json.dumps(body,allow_nan=False))

def test_integrated_complete_landscape_all_mandatory_stages(prepared):
    result=execute(prepared); ledger,cohorts,plan=prepared
    assert result['status']=='PASS'
    report=resolve_selection(ledger,cohorts)
    output=report['output']
    assert set(s['stage'] for s in output['stages'])==set(STAGES)
    landscape=output['stages'][0]['output']
    assert len(landscape['roster'])==2
    assert len(landscape['cohorts'])==4
    for c in landscape['cohorts'].values():
        assert len(c['acceptance']['results'])==17
        assert len(c['inventory']['attempt_ids'])==4
    assert len(ledger.trials.records())==1
    assert result['software_freeze_eligible']
    assert not result['real_pit_validated']
    assert report['holdout_state']=='UNCONSUMED'
    assert not report['official']
    assert report['configuration_scope']==FIXTURE_SCOPE

def test_shared_profile_identity_remains_descriptive_zero_difference(prepared):
    assert execute(prepared)['status']=='PASS'
    report=resolve_selection(prepared[0],prepared[1])
    distinct=report['output']['distinctness']
    assert distinct['role']=='DESCRIPTIVE_ONLY'
    assert not distinct['next_best_substitution']
    assert distinct['pairs']
    assert all(p['delta_right_minus_left']=='0' for p in distinct['pairs'])

def test_registration_precedes_controlled_value_access(prepared):
    ledger,cohorts,plan=prepared
    assert not (ledger.directory/'first-selection-access.json').exists()
    register_selection(*prepared)
    assert not (ledger.directory/'first-selection-access.json').exists()
    run_selection(ledger,cohorts,recorded_at=T)
    event=json.loads((ledger.directory/'first-selection-access.json').read_text())
    assert event['registration_hash']==registration(ledger)['sha256']
    assert event['access_at']>=plan['registered_at']

@pytest.mark.parametrize('field,value',[
    ('scope','REAL_PIT_RESEARCH_VALIDATION'),('configuration_scope','REAL_DEFAULT'),
    ('graph_policy','PARETO_ONLY'),('drift_policy','SIGNED'),
    ('numeric_representation','EPSILON'),('partition','holdout'),
    ('tax_mode','INCLUDED'),('authority_refs',{}),('seed',True)])
def test_unapproved_contract_cannot_register(prepared,field,value):
    ledger,cohorts,plan=prepared;plan[field]=value
    with pytest.raises(ValueError): register_selection(ledger,cohorts,plan)
    assert not (ledger.directory/'first-selection-access.json').exists()

@pytest.mark.parametrize('mutation',['limit','tolerance','formula','units','direction','cohort','scale'])
def test_missing_or_invalid_registration_is_blocked(prepared,mutation):
    ledger,cohorts,plan=prepared
    p=plan['profiles']['Balanced']
    if mutation=='limit': p['constraints'][0]['limit']=None
    elif mutation=='tolerance': p['plateau_tolerances'].pop('net_cagr')
    elif mutation=='formula': p['metrics'][0]['formula_id']='invented'
    elif mutation=='units': p['metrics'][0]['units']='PERCENT_ALIAS'
    elif mutation=='direction': p['metrics'][0]['direction']='weighted'
    elif mutation=='cohort': plan['cohort_metadata'].pop(plan['dimensions'][0])
    elif mutation=='scale': next(iter(plan['drift_registry'].values()))['scales']['cash_buffer']=0
    with pytest.raises((ValueError,KeyError,TypeError)): register_selection(*prepared)

def test_no_result_selected_plateau_tolerance(prepared):
    assert execute(prepared)['status']=='PASS'
    plan=prepared[2];plan['profiles']['Aggressive']['plateau_tolerances']['net_mdd']=100
    with pytest.raises(FileExistsError): register_selection(*prepared)

def test_dedicated_registration_cannot_overwrite(prepared):
    register_selection(*prepared)
    with pytest.raises(FileExistsError): register_selection(*prepared)

def test_attempt_time_before_registration(prepared):
    register_selection(*prepared)
    with pytest.raises(ValueError):
        run_selection(prepared[0],prepared[1],recorded_at=T-timedelta(seconds=1))
    assert not prepared[0].trials.records()

def test_no_stable_plateau_not_run_no_peak_substitution(prepared):
    for p in prepared[2]['profiles'].values():
        p['plateau_tolerances']={'net_cagr':0,'net_mdd':0}
    result=execute(prepared)
    assert result['status']=='NOT_RUN'
    assert not result['software_freeze_eligible']
    assert 'NO_STABLE_PLATEAU' in json.loads((prepared[0].directory/'selection-report.json').read_text())['reason']
    assert prepared[0].trials.records()[0]['trial']['status']=='REJECTED'

def test_all_candidates_constraint_excluded_no_subset_replacement(prepared):
    for p in prepared[2]['profiles'].values(): p['constraints'][0]['limit']=-1
    result=execute(prepared)
    assert result['status']=='NOT_RUN'
    report=json.loads((prepared[0].directory/'selection-report.json').read_text())
    assert len(report['completed_stages'][0]['output']['roster'])==2
    assert report['completed_stages'][1]['output']['eligible']==[]

def test_changed_source_checkpoint_fails_not_run(prepared):
    register_selection(*prepared)
    source=next(iter(prepared[1].values()))[2]
    path=source.directory/'search.json';data=json.loads(path.read_text());data['sha256']='bad'
    overwrite(path,data)
    result=run_selection(prepared[0],prepared[1],recorded_at=T)
    assert result['status']=='FAIL'
    assert prepared[0].trials.records()[0]['trial']['status']=='FAILED'

@pytest.mark.parametrize('ancestor',['C5','C6','C4'])
def test_ancestor_invalidation_revokes_saved_pass(prepared,ancestor):
    assert execute(prepared)['status']=='PASS'
    a=next(iter(prepared[1].values()))
    ledger=a[2] if ancestor=='C5' else a[0] if ancestor=='C6' else next(iter(a[3].values()))['c4_ledger']
    trial=ledger.trials.records()[0]['trial']
    ledger.append(TrialRecord('invalidate-parent',ledger.registration()['experiment_id'],
        len(ledger.trials.records()),T,TrialStatus.INVALIDATED,{}, {},'UPSTREAM_INVALIDATED',
        trial['trial_id']))
    with pytest.raises(ValueError): resolve_selection(prepared[0],prepared[1])

def test_own_invalidation_revokes_saved_pass(prepared):
    result=execute(prepared);ledger=prepared[0]
    ledger.append(TrialRecord('invalidate-c7',ledger.registration()['experiment_id'],1,T,
        TrialStatus.INVALIDATED,{}, {},'REVOKED',result['trial_id']))
    with pytest.raises(ValueError): resolve_selection(ledger,prepared[1])

@pytest.mark.parametrize('file',['selection.json','selection-report.json','first-selection-access.json',
                                'selection-acceptance.json'])
def test_terminal_evidence_tamper_is_not_support(prepared,file):
    assert execute(prepared)['status']=='PASS'
    path=prepared[0].directory/file;data=json.loads(path.read_text())
    if file=='selection.json': data['body']['plan']['source_checkpoint']='changed'
    elif file=='selection-report.json': data['output']['stages'][1]['output']['eligible']=[]
    elif file=='first-selection-access.json':data['registration_hash']='changed'
    else:data['report_hash']='changed'
    overwrite(path,data)
    with pytest.raises(ValueError): resolve_selection(prepared[0],prepared[1])

def test_crash_pending_attempt_charged_and_no_resampling(prepared):
    register_selection(*prepared)
    ledger=prepared[0]
    _write_json(ledger.directory/'pending.json',{'trial_id':'selection-complete-landscape','parameters':{}})
    with pytest.raises(ValueError): run_selection(ledger,prepared[1],recorded_at=T)
    rows=ledger.trials.records()
    assert len(rows)==1 and rows[0]['trial']['status']=='FAILED'
    assert len(rows)==ledger.registration()['search_budget']['max_trials']
    assert not (ledger.directory/'first-selection-access.json').exists()

def test_budget_once_and_duplicate_cannot_access_again(prepared):
    assert execute(prepared)['status']=='PASS'
    before=checkpoint(prepared[1])
    with pytest.raises(ValueError): run_selection(prepared[0],prepared[1],recorded_at=T)
    assert len(prepared[0].trials.records())==1
    assert checkpoint(prepared[1])==before

def test_serialized_concurrent_attempts_charge_exactly_one(prepared):
    register_selection(*prepared)
    def attempt():
        try:return run_selection(prepared[0],prepared[1],recorded_at=T)['status']
        except ValueError:return 'BLOCKED'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:attempt(),range(2)))
    assert sorted(results)==['BLOCKED','PASS']
    assert len(prepared[0].trials.records())==1

def test_upstream_files_preserved_across_success(prepared):
    before=checkpoint(prepared[1]);assert execute(prepared)['status']=='PASS'
    assert checkpoint(prepared[1])==before
