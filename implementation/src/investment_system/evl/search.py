"""C5 deterministic constrained grid search on registered development rows only.

TC-D3P-002: cash_buffer and technical_lookback only. All screening levels are
preregistered; no OOS/holdout inputs and no peak/champion selection. Evaluators
are trusted, versioned callbacks, just like C4 pipelines.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from itertools import product
import fcntl
import json
import math

from .bindings import validate_parameters
from .contracts import TrialRecord, TrialStatus
from .splits import aware, split_samples
from .walkforward import dataset_digest, digest, _write_json, _recover_pending, _verify_split

STAGES = ('Baseline','QGV','Technical','Macro','Integration','Portfolio/Risk','Interaction')
KEYS = {'Technical': ('technical_lookback',), 'Portfolio/Risk': ('cash_buffer',)}


def register_search(ledger, split, rows, plan):
    """Plan contains baseline, coarse grid, metric directions, screening levels,
    evaluator ID, registration time, and primary/stress variant. Fine grid is the
    ExperimentSpec domain. A level is a registered development-prefix sample size
    plus metric cutoffs; the final level must use all retained training rows.
    """
    spec = ledger.registration()
    _verify_split(ledger, split, spec)
    plan = json.loads(json.dumps(plan, allow_nan=False))
    domain = spec['parameter_space']['values']
    if spec['search_budget']['method'] != 'CONSTRAINED_GRID':
        raise ValueError('unsupported search method')
    if not domain or set(domain)-{'cash_buffer','technical_lookback'}:
        raise ValueError('TC-D3P-002 scope violation')
    if set(plan['baseline']) != set(domain) or set(plan['coarse']) != set(domain):
        raise ValueError('grid/baseline keys mismatch')
    for key, values in domain.items():
        for value in values:
            validate_parameters({key:value}, performance_search=True)
        coarse = plan['coarse'][key]
        if (not coarse or coarse != sorted(set(coarse)) or
            not set(coarse) <= set(values) or plan['baseline'][key] not in coarse):
            raise ValueError('invalid coarse grid/baseline')
    if not plan['evaluator_id'] or plan['variant'] not in ('PRIMARY','REBALANCE_GAP_STRESS'):
        raise ValueError('missing evaluator/variant')
    registered = datetime.fromisoformat(plan['registered_at'])
    aware(registered)
    if registered < max(split.registered_at, datetime.fromisoformat(spec['registered_at'])):
        raise ValueError('search predates registration')
    if set(plan['directions']) != set(spec['metric_set']['metric_ids']) or any(
            v not in ('max','min') for v in plan['directions'].values()):
        raise ValueError('metric direction mismatch')
    if spec['data_hash'] != dataset_digest(rows):
        raise ValueError('dataset hash mismatch')
    partition = split_samples(split, tuple(r.sample for r in rows), stress=plan['variant']!='PRIMARY')
    train_ids = set(partition.retained['train'])
    if not train_ids or train_ids != {r.sample.sample_id for r in rows}:
        raise ValueError('search accepts only retained Train rows; no Validation/OOS/Holdout')
    sizes = [level['size'] for level in plan['levels']]
    if (not sizes or any(type(n) is not int or n <= 0 for n in sizes)
            or sizes != sorted(set(sizes)) or sizes[-1] != len(rows)):
        raise ValueError('levels must increase to complete Train set')
    for level in plan['levels']:
        if set(level['cutoffs']) != set(plan['directions']) or any(
            isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
            for v in level['cutoffs'].values()):
            raise ValueError('invalid screening cutoffs')
    body = {'plan':plan,'experiment_hash':digest(spec),'split_hash':digest(split.payload())}
    with (ledger.directory/'experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if ledger.trials.records() or (ledger.directory/'runner.json').exists():
            raise ValueError('search needs a dedicated unconsumed ledger')
        _write_json(ledger.directory/'search.json', {'sha256':digest(body),'body':body})
    return digest(body)


def run_search(ledger, split, rows, *, evaluator_id, evaluate, recorded_at):
    aware(recorded_at)
    spec = ledger.registration()
    _verify_split(ledger,split,spec)
    envelope = json.loads((ledger.directory/'search.json').read_text())
    body = envelope['body']
    if (digest(body) != envelope['sha256'] or body['experiment_hash'] != digest(spec)
            or body['split_hash'] != digest(split.payload()) or dataset_digest(rows) != spec['data_hash']):
        raise ValueError('search registration/data mismatch')
    plan = body['plan']
    if evaluator_id != plan['evaluator_id'] or recorded_at < datetime.fromisoformat(plan['registered_at']):
        raise ValueError('evaluator/time mismatch')
    with (ledger.directory/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        _recover_pending(ledger,recorded_at)
        # One deterministic run per registration; do not silently resample failures.
        if ledger.trials.records():
            raise ValueError('search already consumed; interrupted attempts remain counted')
        return _run(ledger,spec,plan,rows,evaluate,recorded_at)


def _run(ledger,spec,plan,rows,evaluate,recorded_at):
    rows = tuple(sorted(rows,key=lambda r:(r.sample.decision_time,r.sample.sample_id)))
    domain = spec['parameter_space']['values']
    baseline = plan['baseline']
    seen, survivors, stages = {}, [], []
    budget = spec['search_budget']['max_trials']
    exhausted = False

    def attempt(parameters, stage, resolution):
        nonlocal exhausted
        if digest(parameters) in seen:
            return seen[digest(parameters)]
        seen[digest(parameters)] = False
        complexity = sum(parameters[k] != baseline[k] for k in parameters)
        precision = max(0,-Decimal(str(parameters.get('cash_buffer',0))).normalize().as_tuple().exponent)
        rejection = ('COMPLEXITY_BUDGET' if complexity > spec['parameter_space']['complexity_budget']
                     else 'WEIGHT_PRECISION' if precision > spec['parameter_space']['precision_limit'] else None)
        for rung,level in enumerate(plan['levels']):
            seq = len(ledger.trials.records())
            if seq >= budget:
                exhausted = True
                return False
            trial_id = f'search-{seq}'
            pending = ledger.directory/'pending.json'
            _write_json(pending,{'trial_id':trial_id,'parameters':parameters})
            status,reason,metrics = TrialStatus.SUCCESS,None,{}
            try:
                if rejection:
                    status,reason = TrialStatus.REJECTED,rejection
                else:
                    metrics = evaluate(deepcopy(parameters),deepcopy(rows[:level['size']]),spec['seed'])
                    if set(metrics) != set(plan['directions']) or any(
                        isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
                        for v in metrics.values()):
                        raise ValueError('invalid evaluator metrics')
                    if any((metrics[k] < v if plan['directions'][k]=='max' else metrics[k] > v)
                           for k,v in level['cutoffs'].items()):
                        status,reason = TrialStatus.EARLY_STOPPED,'REGISTERED_SCREEN'
            except Exception as exc:
                status,reason,metrics = TrialStatus.FAILED,type(exc).__name__+': '+str(exc),{}
            evidence = {'stage':stage,'resolution':resolution,'rung':rung,'sample_size':level['size'],
                'status':status.value,'reason':reason,'metrics':metrics,'parameters':parameters,
                'complete_candidate':status==TrialStatus.SUCCESS and rung==len(plan['levels'])-1,
                'data_hash':spec['data_hash'],'code_hash':spec['code_hash'],'seed':spec['seed'],
                'tax_mode':'EXCLUDED','official':False}
            _write_json(ledger.directory/(trial_id+'.json'),evidence)
            ledger.append(TrialRecord(trial_id,spec['experiment_id'],seq,recorded_at,status,
                deepcopy(parameters),deepcopy(metrics),(reason+'; ' if reason else '')+'report_sha256='+digest(evidence)))
            pending.unlink()
            if status != TrialStatus.SUCCESS:
                return False
        seen[digest(parameters)] = True
        survivors.append({'parameters':deepcopy(parameters),'trial_id':trial_id,
                          'stage':stage,'resolution':resolution,'metrics':deepcopy(metrics)})
        return True

    for stage in STAGES:
        keys = tuple(sorted(domain)) if stage=='Interaction' else KEYS.get(stage,())
        if stage!='Baseline' and not set(keys)&set(domain):
            stages.append({'stage':stage,'status':'NO_ELIGIBLE_BOUND_PARAMETER'})
            continue
        keys = tuple(k for k in keys if k in domain)
        if exhausted:
            stages.append({'stage':stage,'status':'NOT_RUN_BUDGET'})
            continue
        accepted = []
        coarse = [dict(baseline)] if stage=='Baseline' else (
            {**baseline,**dict(zip(keys,point))} for point in product(*(plan['coarse'][k] for k in keys)))
        for parameters in coarse:
            if attempt(parameters,stage,'COARSE'):
                accepted.append(parameters)
            if exhausted: break
        # Refine each surviving coarse neighbourhood, never just the best point.
        for center in accepted if stage!='Baseline' else ():
            domains = []
            for key in keys:
                coarse_values = plan['coarse'][key]
                i = coarse_values.index(center[key])
                low = coarse_values[max(0,i-1)]
                high = coarse_values[min(len(coarse_values)-1,i+1)]
                domains.append(sorted(v for v in domain[key] if low <= v <= high))
            for point in product(*domains):
                attempt({**baseline,**dict(zip(keys,point))},stage,'REFINE')
                if exhausted: break
            if exhausted: break
        stages.append({'stage':stage,'status':'BUDGET_EXHAUSTED' if exhausted else 'COMPLETED'})
    return {'status':'BUDGET_EXHAUSTED' if exhausted else 'COMPLETED', 'stages':stages,
            'survivors':survivors,'attempts':len(ledger.trials.records()),'official':False,
            'selection':'NONE_C7_REQUIRED','tax_mode':'EXCLUDED'}
