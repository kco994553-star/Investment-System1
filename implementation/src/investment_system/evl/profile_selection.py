"""C7 pre-access, dedicated immutable attempt and descriptive profile evidence.

All result access is through this registered boundary. Like frozen C4/C6 producer
interfaces, external callers remain trusted: this API cannot erase prior human
knowledge or police direct filesystem access outside the producer contract.
"""
from copy import deepcopy
from datetime import datetime
import fcntl
import json
from .contracts import TrialRecord, TrialStatus
from .selection_contracts import validate_plan, POLICY, PROFILES
from .landscape import checkpoint, resolve_landscape, metric_value
from .selection import number, frontier, plateau, complexity, low_drift, medoids
from .statistical_kernels import MissingStatisticalEvidence
from .splits import aware
from .walkforward import digest, _write_json, _recover_pending

STAGES=('LANDSCAPE','ELIGIBILITY','PARETO','PLATEAU','COMPLEXITY','DRIFT','CENTER',
        'PROFILE_CANDIDATE','DISTINCTNESS')
def register_selection(ledger, cohorts, plan):
    """Persist declarations before controlled first target selection OOS access."""
    p=validate_plan(plan); spec=ledger.registration()
    if (spec['parameter_space']['values'] or spec['metric_set']['metric_ids']!=['selection_complete']
            or p['seed']!=spec['seed']
            or datetime.fromisoformat(p['registered_at'])<datetime.fromisoformat(spec['registered_at'])):
        raise ValueError('dedicated C7 experiment/registration required')
    committed=checkpoint(cohorts)
    if spec['data_hash']!=digest(committed):
        raise ValueError('complete source commitment must bind C7 experiment')
    body={'plan':p,'experiment_hash':digest(spec),'checkpoint':committed,
          'policy':POLICY,'stages':list(STAGES)}
    with (ledger.directory/'experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if ledger.trials.records() or (ledger.directory/'first-selection-access.json').exists():
            raise ValueError('registration cannot follow target access/results')
        _write_json(ledger.directory/'selection.json',{'sha256':digest(body),'body':body})
    return digest(body)

def registration(ledger):
    stored=json.loads((ledger.directory/'selection.json').read_text())
    body=stored['body']; validate_plan(body['plan'])
    if (stored['sha256']!=digest(body) or body['experiment_hash']!=digest(ledger.registration())
            or body['policy']!=POLICY or body['stages']!=list(STAGES)):
        raise ValueError('selection authority/hash/contract mismatch')
    return stored

def compute_selection(landscape, plan, stages=None):
    """Pure stages; complete Landscape remains immutable in every report."""
    parameters=landscape['roster']; dimensions=plan['dimensions']
    if stages is None: stages=[]
    stages.append({'stage':'LANDSCAPE','output':landscape})
    profiles={}; values_by_profile={}
    def stage(name,output):
        parent=digest(stages[-1])
        stages.append({'stage':name,'parent_hash':parent,'output':output})
    for name in PROFILES:
        definition=plan['profiles'][name]; metrics=definition['metrics']
        labels=[[d,m['metric_id']] for d in dimensions for m in metrics]
        values={i:[metric_value(landscape['cohorts'][d]['metrics'][i],m)
                   for d in dimensions for m in metrics] for i in parameters}
        eligible=[]; excluded={}
        for i,row in values.items():
            failures=[]
            for d in dimensions:
                for c in definition['constraints']:
                    m=next(m for m in metrics if m['metric_id']==c['metric_id'])
                    v=number(metric_value(landscape['cohorts'][d]['metrics'][i],m))
                    limit=number(c['limit'])
                    if not (v<=limit if c['operator']=='<=' else v>=limit):
                        failures.append({'dimension':d,'constraint':c,'value':str(v)})
            if failures: excluded[i]=failures
            else: eligible.append(i)
        stage('ELIGIBILITY',{'profile':name,'eligible':eligible,'excluded':excluded,
                            'raw_values':values,'objective_dimensions':labels})
        dirs=[m['direction'] for d in dimensions for m in metrics]
        pareto=frontier({i:values[i] for i in eligible},dirs)
        stage('PARETO',{'profile':name,'survivors':pareto,'directions':dirs,
                       'dimensions':labels})
        tol=[definition['plateau_tolerances'][m['metric_id']] for d in dimensions for m in metrics]
        graph=plateau({i:parameters[i] for i in eligible},landscape['domain'],values,tol,pareto)
        stage('PLATEAU',{'profile':name,**graph,'tolerances':tol,'dimensions':labels})
        if not graph['survivors']:
            raise MissingStatisticalEvidence('NOT_RUN_NO_STABLE_PLATEAU: '+name)
        counts=complexity({i:parameters[i] for i in graph['survivors']},landscape['baseline'])
        stage('COMPLEXITY',{'profile':name,**counts,'baseline':landscape['baseline']})
        drift=low_drift({i:landscape['drift_vectors'][i] for i in counts['survivors']})
        stage('DRIFT',{'profile':name,**drift,'dimensions':landscape['drift_dimensions']})
        center=medoids(drift['survivors'],graph,parameters,landscape['domain'])
        stage('CENTER',{'profile':name,'components':center})
        reps=sorted(i for c in center for i in c['representatives'])
        profiles[name]={'profile':name,'representative_tie_set':reps,'components':center,
            'candidates':[{'candidate_id':i,'parameters':parameters[i],
                'scope':plan['scope'],'tax_mode':'EXCLUDED','official':False,
                'research_decision':'NOT_ASSESSED_PENDING_C8',
                'selection_lineage_hash':digest(stages[-1])} for i in reps]}
        values_by_profile[name]=(metrics,values)
    stage('PROFILE_CANDIDATE',profiles)
    # Every exact representative pair and registered union metric/cohort; descriptive only.
    pairs=[]
    for index,left in enumerate(PROFILES):
        for right in PROFILES[index+1:]:
            union={}
            for metric in plan['profiles'][left]['metrics']+plan['profiles'][right]['metrics']:
                union[digest(metric['path'])]=metric
            for a in profiles[left]['representative_tie_set']:
                for b in profiles[right]['representative_tie_set']:
                    for d in dimensions:
                        for metric in union.values():
                            report=landscape['cohorts'][d]['metrics']
                            av=metric_value(report[a],metric); bv=metric_value(report[b],metric)
                            pairs.append({'left_profile':left,'right_profile':right,
                                'left_id':a,'right_id':b,'dimension':d,'metric':metric,
                                'left':av,'right':bv,'delta_right_minus_left':str(number(bv)-number(av))})
    distinctness={'role':'DESCRIPTIVE_ONLY','pairs':pairs,
                  'statistical_economic_decision':'NOT_ASSESSED_PENDING_C8',
                  'next_best_substitution':False}
    stage('DISTINCTNESS',distinctness)
    return {'profiles':profiles,'distinctness':distinctness,'stages':stages}

def run_selection(ledger, cohorts, *, recorded_at):
    aware(recorded_at); stored=registration(ledger); body=stored['body']; plan=body['plan']
    if recorded_at<datetime.fromisoformat(plan['registered_at']):
        raise ValueError('attempt precedes preregistration')
    spec=ledger.registration()
    with (ledger.directory/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        _recover_pending(ledger,recorded_at)
        rows=ledger.trials.records()
        if rows: raise ValueError('selection already attempted; no hidden rerun')
        if len(rows)>=spec['search_budget']['max_trials']:
            return {'status':'NOT_RUN','reason':'REGISTERED_BUDGET_EXHAUSTED'}
        trial_id='selection-complete-landscape'
        _write_json(ledger.directory/'pending.json',{'trial_id':trial_id,'parameters':{}})
        # Durable checkpoint before any controlled target-value access.
        _write_json(ledger.directory/'first-selection-access.json',
            {'registration_hash':stored['sha256'],'trial_id':trial_id,
             'access_at':recorded_at.isoformat(),'checkpoint_hash':digest(body['checkpoint'])})
        status,reason,output='PASS',None,None
        stages=[]
        try:
            landscape=resolve_landscape(cohorts,plan,body['checkpoint'])
            output=compute_selection(landscape,plan,stages); digest(output)
        except MissingStatisticalEvidence as exc:
            status,reason='NOT_RUN',str(exc)
        except Exception as exc:
            status,reason='FAIL',type(exc).__name__+': '+str(exc)
        report={'status':status,'reason':reason,'output':output,
            'completed_stages':stages,'failed_after':stages[-1]['stage'] if stages else 'PRE_LANDSCAPE',
            'registration_hash':stored['sha256'],'checkpoint_hash':digest(body['checkpoint']),
            'code_hash':spec['code_hash'],'source_checkpoint':plan['source_checkpoint'],
            'scope':plan['scope'],'configuration_scope':plan['configuration_scope'],
            'holdout_state':'UNCONSUMED','official':False,'tax_mode':'EXCLUDED',
            'research_decision':'NOT_ASSESSED_PENDING_C8'}
        _write_json(ledger.directory/'selection-report.json',report)
        ledger.append(TrialRecord(trial_id,spec['experiment_id'],len(rows),recorded_at,
            TrialStatus.SUCCESS if status=='PASS' else TrialStatus.REJECTED if status=='NOT_RUN' else TrialStatus.FAILED,
            {},{'selection_complete':1.} if status=='PASS' else {},
            (reason+'; ' if reason else '')+'report_sha256='+digest(report)))
        (ledger.directory/'pending.json').unlink()
        result={'status':status,'scope':plan['scope'],'report_hash':digest(report),
            'trial_id':trial_id,'registration_hash':stored['sha256'],
            'software_freeze_eligible':status=='PASS' and plan['scope']=='SYNTHETIC_SOFTWARE_VALIDATION',
            'real_pit_validated':False,'holdout_state':'UNCONSUMED','official':False}
        _write_json(ledger.directory/'selection-acceptance.json',result)
        return result

def resolve_selection(ledger, cohorts):
    """Recompute all stages from currently qualified ancestors; saved PASS is insufficient."""
    stored=registration(ledger); body=stored['body']
    result=json.loads((ledger.directory/'selection-acceptance.json').read_text())
    trial=ledger.supporting_trial(result['trial_id'])
    report=json.loads((ledger.directory/'selection-report.json').read_text())
    event=json.loads((ledger.directory/'first-selection-access.json').read_text())
    if (result['status']!='PASS' or report['status']!='PASS'
            or result['registration_hash']!=stored['sha256']
            or event['registration_hash']!=stored['sha256']
            or event['checkpoint_hash']!=digest(body['checkpoint'])
            or event['trial_id']!=trial['trial_id']
            or datetime.fromisoformat(event['access_at'])<datetime.fromisoformat(body['plan']['registered_at'])
            or result['report_hash']!=digest(report)
            or trial['reason']!='report_sha256='+digest(report)
            or report['registration_hash']!=stored['sha256']
            or report['checkpoint_hash']!=digest(body['checkpoint'])
            or report['code_hash']!=ledger.registration()['code_hash']):
        raise ValueError('selection terminal/access/ledger lineage mismatch')
    landscape=resolve_landscape(cohorts,body['plan'],body['checkpoint'])
    expected=compute_selection(landscape,body['plan'])
    if report['output']!=expected or report['completed_stages']!=expected['stages']:
        raise ValueError('selection intermediate/output stage tamper')
    return deepcopy(report)
