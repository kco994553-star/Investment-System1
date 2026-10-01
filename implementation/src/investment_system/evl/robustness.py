"""C6 registered family diagnostics under TC-D3P-004 A / TC-D3P-005 S.

Consumes frozen C4 predictions and explicit upstream execution/scenario inputs.
No fit/predict/selection hook, real-data substitution, Holdout reader or thresholds.
Callbacks upstream remain trusted versioned producers, as in C4/C5.
"""
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime
from hashlib import sha256
from itertools import product
import fcntl
import json
import math
from statistics import variance

from ..contracts.models import _to_json
from .contracts import TrialRecord, TrialStatus
from .execution import input_payload, input_hash, validate_input, evaluate_execution
from .statistical_kernels import (METHOD_VERSION, MissingStatisticalEvidence,
    excess_family_from_periods, period_sharpe, probabilistic_sharpe,
    deflated_sharpe_family, cscv_pbo, joint_circular_bootstrap, family_reality_check)
from .splits import aware
from .walkforward import digest, _write_json, _verify_split, _recover_pending
from .bindings import validate_parameters

POLICY = 'TC-D3P-004_A+TC-D3P-005_S_v1'
MANDATORY = ('PSR', 'DSR_DISTINCT', 'DSR_ATTEMPTS', 'CSCV_PBO', 'BOOTSTRAP',
    'REALITY_EQUAL', 'REALITY_MCAP', 'PARAMETER', 'REGIME', 'UNIVERSE',
    'RANDOM_RANKING', 'RANDOM_WEIGHTS', 'EQUAL_CONTROL', 'MCAP_CONTROL',
    'DRIFT', 'EXECUTION_DELAY', 'COST_STRESS')
SCENARIOS = ('PARAMETER', 'REGIME', 'UNIVERSE', 'RANDOM_RANKING',
             'RANDOM_WEIGHTS', 'EQUAL_CONTROL', 'MCAP_CONTROL')
SCOPES = ('SYNTHETIC_SOFTWARE_VALIDATION', 'REAL_PIT_RESEARCH_VALIDATION')


def candidate_identity(parameters, evaluator_id):
    return digest({'parameters': parameters, 'evaluator_id': evaluator_id})


def source_inventory(source):
    """All C5 attempts, including screening/rejected/failed; never survivors only."""
    spec = source.registration()
    stored = json.loads((source.directory/'search.json').read_text())
    body = stored['body']
    if stored['sha256'] != digest(body) or body['experiment_hash'] != digest(spec):
        raise ValueError('C5 search authority/hash mismatch')
    rows = source.trials.records()
    evaluator = body['plan']['evaluator_id']
    domain = spec['parameter_space']['values']
    keys = tuple(sorted(domain))
    roster = {candidate_identity(dict(zip(keys,values)),evaluator):dict(zip(keys,values))
              for values in product(*(domain[k] for k in keys))}
    for row in rows:
        trial = row['trial']
        if trial['status'] != 'INVALIDATED':
            key = candidate_identity(trial['parameters'], evaluator)
            roster[key] = deepcopy(trial['parameters'])
    return {'spec': spec, 'search': body, 'rows': rows, 'roster': roster,
            'evaluator_id': evaluator,
            'attempt_ids': [r['trial']['trial_id'] for r in rows
                            if r['trial']['status'] != 'INVALIDATED'],
            'status_counts': {s: sum(r['trial']['status'] == s for r in rows)
                              for s in ('SUCCESS','REJECTED','EARLY_STOPPED','FAILED','INVALIDATED')}}


def c4_report(ledger, trial_id):
    trial = ledger.supporting_trial(trial_id)
    name = 'report-'+sha256(trial_id.encode()).hexdigest()+'.json'
    report = json.loads((ledger.directory/name).read_text())
    runner = json.loads((ledger.directory/'runner.json').read_text())
    spec = ledger.registration()
    if (runner['sha256'] != digest(runner['body'])
            or runner['body']['experiment_hash'] != digest(spec)
            or report['status'] != 'SUCCESS'
            or trial['reason'] != 'report_sha256='+digest(report)
            or report['experiment_id'] != spec['experiment_id']
            or report['code_hash'] != spec['code_hash']
            or report['data_hash'] != spec['data_hash']
            or report['parameters'] != trial['parameters']
            or report['pipeline_id'] != runner['body']['runner']['pipeline_id']
            or report['model_hash'] != digest(report['model'])
            or report['threshold_hash'] != digest(report['thresholds'])
            or report['prediction_hash'] != digest(report['predictions'])):
        raise ValueError('C4 frozen prediction lineage/hash mismatch')
    return report


def _snapshot(source, bundles, drift):
    inventory = source_inventory(source)
    payload = {}
    for identity, bundle in sorted(bundles.items()):
        c4 = bundle['c4_ledger']
        trials = c4.trials.records()
        ref = bundle['c4_trial_id']
        # Preserve a missing report as missing evidence, never a manufactured row.
        name = 'report-'+sha256(ref.encode()).hexdigest()+'.json'
        payload[identity] = {
            'c4_spec': c4.registration(), 'c4_trials': trials, 'c4_trial_id': ref,
            'c4_report': json.loads((c4.directory/name).read_text()) if (c4.directory/name).exists() else None,
            'baseline': input_payload(bundle['baseline']) if bundle.get('baseline') is not None else None,
            'scenarios': {k: {
                'definition': deepcopy(v['definition']),
                'input': input_payload(v['input']) if v.get('input') is not None else None}
                for k,v in sorted(bundle['scenarios'].items())}}
    return {'source': inventory, 'bundles': payload, 'drift': deepcopy(drift)}


def package_hash(source, bundles, drift):
    return digest(_snapshot(source, bundles, drift))


def register_robustness(ledger, split, source, bundles, drift, plan):
    spec = ledger.registration()
    _verify_split(ledger, split, spec)
    plan = json.loads(json.dumps(plan, allow_nan=False))
    registered = datetime.fromisoformat(plan['registered_at'])
    evaluated = datetime.fromisoformat(plan['evaluation_time'])
    aware(registered); aware(evaluated)
    if (registered < max(split.registered_at, datetime.fromisoformat(spec['registered_at']))
            or evaluated < registered or plan['scope'] not in SCOPES
            or plan['partition'] != 'oos'
            or plan['variant'] not in ('PRIMARY','REBALANCE_GAP_STRESS')
            or not plan['evaluator_id'] or type(plan['seed']) is not int
            or plan['seed'] != spec['seed']
            or plan['method_version'] != METHOD_VERSION
            or plan['quantile_convention'] != 'EMPIRICAL_INVERSE_CDF'
            or plan['holdout_start'] != split.holdout_start.isoformat()):
        raise ValueError('unregistered C6 method/scope/partition/time')
    for key in ('periods_per_year','tail_fraction','reference_sharpe','sharpe_variance'):
        v = plan[key]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
            raise ValueError('missing finite registered convention')
    if (plan['periods_per_year'] <= 0 or not 0 < plan['tail_fraction'] <= 1
            or plan['sharpe_variance'] < 0):
        raise ValueError('invalid convention')
    for key in ('block_count','block_length','replicates'):
        if type(plan[key]) is not int or plan[key] <= 0:
            raise ValueError('explicit positive method dimensions required')
    if plan['block_count'] % 2 or not plan['quantiles']:
        raise ValueError('explicit even CSCV blocks / quantiles required')
    if spec['parameter_space']['values'] or spec['metric_set']['metric_ids'] != ['diagnostic_complete']:
        raise ValueError('dedicated C6 diagnostic ledger required')
    snapshot = _snapshot(source, bundles, drift)
    domain = snapshot['source']['spec']['parameter_space']['values']
    if (set(plan['perturbation_domains']) != set(domain) or any(
            not values or not set(values) <= set(domain[k])
            for k,values in plan['perturbation_domains'].items())):
        raise ValueError('perturbation must remain in registered C5 parameter domains')
    if spec['data_hash'] != digest(snapshot):
        raise ValueError('registered family input hash mismatch')
    if set(bundles)-set(snapshot['source']['roster']):
        raise ValueError('foreign candidate / post-selection roster')
    body = {'plan': plan, 'policy': POLICY, 'mandatory': MANDATORY,
            'experiment_hash': digest(spec), 'split_hash': digest(split.payload()),
            'package': snapshot, 'source_hash': digest(snapshot['source'])}
    with (ledger.directory/'experiment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if ledger.trials.records():
            raise ValueError('registration cannot follow diagnostic results')
        _write_json(ledger.directory/'robustness.json', {'sha256':digest(body),'body':body})
    return digest(body)


def _source_ready(source, body):
    current = source_inventory(source)
    if digest(current) != body['source_hash']:
        raise ValueError('changed/invalidated full C5 family')
    rows = current['rows']
    if current['status_counts']['INVALIDATED']:
        raise ValueError('upstream family invalidation')
    if (not current['roster'] or len(current['roster']) < 2
            or len(current['attempt_ids']) > current['spec']['search_budget']['max_trials']
            or any(r['trial']['status'] != 'SUCCESS' for r in rows)):
        raise MissingStatisticalEvidence('incomplete/failed/invalidated full family')
    # Require an actual final complete C5 report for every identity.
    complete = set()
    for row in rows:
        trial = row['trial']
        source.supporting_trial(trial['trial_id'])
        report = json.loads((source.directory/(trial['trial_id']+'.json')).read_text())
        if trial['reason'] != 'report_sha256='+digest(report):
            raise ValueError('C5 report/ledger hash mismatch')
        if report['complete_candidate']:
            complete.add(candidate_identity(trial['parameters'],current['evaluator_id']))
    if complete != set(current['roster']):
        raise MissingStatisticalEvidence('full-resource C5 coverage missing')
    if body['plan']['registered_at'] < max(r['trial']['recorded_at'] for r in rows):
        raise ValueError('inference registration precedes source terminal checkpoint')
    return current


def _qualified(ledger, split, source, bundles, body):
    plan = body['plan']
    inventory = _source_ready(source, body)
    _verify_split(source,split,inventory['spec'])
    if (inventory['spec']['code_hash'] != ledger.registration()['code_hash']
            or inventory['spec']['dataset_vintage'] != ledger.registration()['dataset_vintage']):
        raise ValueError('C5/C6 code/vintage identity mismatch')
    if inventory['search']['plan']['variant'] != plan['variant']:
        raise ValueError('C5/C6 variant mismatch')
    roster = tuple(sorted(inventory['roster']))
    if set(bundles) != set(roster):
        raise MissingStatisticalEvidence('complete immutable candidate family required')
    samples = None
    for identity in roster:
        b = bundles[identity]
        if b.get('baseline') is None:
            raise MissingStatisticalEvidence('baseline execution input missing')
        _verify_split(b['c4_ledger'],split,b['c4_ledger'].registration())
        report = c4_report(b['c4_ledger'], b['c4_trial_id'])
        if (report['parameters'] != inventory['roster'][identity]
                or report['variant'] != plan['variant']
                or report['runner']['pipeline_id'] != inventory['evaluator_id']
                or report['code_hash'] != ledger.registration()['code_hash']
                or report['partition']['contract_hash'] != digest(split.payload())):
            raise ValueError('C4/C5 candidate/evaluator/code/variant mismatch')
        if b['c4_ledger'].registration()['dataset_vintage'] != ledger.registration()['dataset_vintage']:
            raise ValueError('cross-vintage evidence')
        data = b['baseline']
        validate_input(split,data,plan['partition'])
        ids = tuple(r.sample.sample_id for r in data.rows)
        if ids != tuple(report['partition']['retained']['oos']):
            raise ValueError('C4 predictions / execution sample coverage mismatch')
        if samples is None:
            samples = tuple(r.sample for r in data.rows)
        elif digest([asdict(r.sample) for r in data.rows]) != digest([asdict(s) for s in samples]):
            raise ValueError('cross-candidate timeline/provenance mismatch')
        if plan['scope'] == SCOPES[0] and data.synthetic is not True:
            raise ValueError('software scope requires explicitly synthetic inputs')
        if plan['scope'] == SCOPES[1] and data.synthetic is not False:
            raise ValueError('synthetic cannot support real PIT research')
        for row in data.rows:
            ref = digest(report['predictions'][row.sample.sample_id])
            if not row.orders or any(o.source_ref != ref for o in row.orders):
                raise ValueError('explicit orders must bind frozen C4 prediction')
    return inventory,roster,samples


def _execute(data, split, plan, delay=0, multiplier=1):
    report = evaluate_execution(data,split=split,partition=plan['partition'],
        delay=delay,multiplier=multiplier,
        evaluation_time=datetime.fromisoformat(plan['evaluation_time']),
        periods_per_year=plan['periods_per_year'],tail_fraction=plan['tail_fraction'])
    periods = tuple(replace(row.period,
        gross_return=frame['gross_pnl']/frame['opening_equity'],
        trading_cost=multiplier*frame['execution_cost']/frame['opening_equity'],
        turnover=frame['turnover']) for row,frame in zip(data.rows,report['path']))
    return periods,report


def _family(split, plan, bundles, roster, samples, scenario=None, delay=0, multiplier=1):
    periods, reports = {},{}
    for identity in roster:
        if scenario is None:
            data = bundles[identity]['baseline']
        else:
            b = bundles[identity]
            if scenario not in b['scenarios'] or b['scenarios'][scenario].get('input') is None:
                raise MissingStatisticalEvidence(scenario+' upstream execution evidence missing')
            v = b['scenarios'][scenario]
            _scenario_definition(v['definition'], scenario, plan, b, identity)
            data = v['input']
            if data.synthetic != b['baseline'].synthetic:
                raise ValueError('scenario evidence scope mismatch')
        periods[identity],reports[identity] = _execute(data,split,plan,delay,multiplier)
    adapter = excess_family_from_periods(roster,periods,samples,split=split,
        partition=plan['partition'],stress=plan['variant']!='PRIMARY',
        evaluation_time=datetime.fromisoformat(plan['evaluation_time']))
    return {'adapter':adapter, 'periods':{k:[asdict(p) for p in v] for k,v in periods.items()}, 'reports':reports,
            'net':{k:tuple(p.gross_return-p.trading_cost for p in v) for k,v in periods.items()}}


def _scenario_definition(d, kind, plan, bundle, identity):
    if (d['kind'] != kind or not d['scenario_id'] or not d['snapshot_refs']
            or not d['evaluator_id'] or not d['method'] or d['candidate_id'] != identity
            or d['registered_at'] > plan['registered_at']):
        raise ValueError('scenario must be explicitly defined before inference')
    aware(datetime.fromisoformat(d['registered_at']))
    if d['evaluator_id'] != plan['scenario_evaluator_id']:
        raise ValueError('scenario evaluator identity mismatch')
    # Inputs are frozen upstream producer outputs, not altered Track A artifacts.
    if kind == 'PARAMETER':
        parameters = d['parameters']
        validate_parameters(parameters,performance_search=True)
        if not parameters or set(parameters)-{'cash_buffer','technical_lookback'}:
            raise ValueError('unapproved parameter perturbation')
        for k,v in parameters.items():
            if v not in plan['perturbation_domains'][k]:
                raise ValueError('parameter perturbation outside registered domain')
    if kind == 'RANDOM_RANKING':
        if type(d['seed']) is not int or sorted(d['permutation']) != sorted(d['security_ids']):
            raise ValueError('invalid registered random ranking permutation')
        if len(set(d['security_ids'])) != len(d['security_ids']):
            raise ValueError('duplicate random ranking security')
    if kind == 'RANDOM_WEIGHTS':
        weights = d['weights']
        if (type(d['seed']) is not int or not weights or any(
                isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0
                for v in weights.values()) or not math.isclose(sum(weights.values()),1.)):
            raise ValueError('invalid explicit generic random weights')
    if not bundle['scenarios'][kind].get('input'):
        raise MissingStatisticalEvidence('scenario input unavailable')
    data = bundle['scenarios'][kind]['input']
    if len(data.rows) != len(bundle['baseline'].rows):
        raise MissingStatisticalEvidence('scenario full timeline coverage missing')
    for row in data.rows:
        if any(o.source_ref != digest(d) for o in row.orders):
            raise ValueError('scenario orders must bind registered producer definition')


def _drift(drift, roster, plan):
    if set(drift) != set(roster):
        raise MissingStatisticalEvidence('complete candidate parameter drift histories missing')
    result = {}
    for identity, history in drift.items():
        if not history:
            raise MissingStatisticalEvidence('missing parameter drift observations')
        times = [datetime.fromisoformat(h['time']) for h in history]
        for t in times:
            aware(t)
        if times != sorted(set(times)) or len(times) < 2:
            raise ValueError('registered drift requires unique chronological raw histories')
        if any(t >= datetime.fromisoformat(plan['holdout_start']) for t in times):
            raise ValueError('Holdout cannot enter parameter drift')
        if plan['drift_convention'] != 'REGISTERED_COORDINATE_DELTA_OVER_SCALE':
            raise ValueError('unsupported drift convention')
        scales = plan['drift_scales']
        if not scales or any(isinstance(v,bool) or not isinstance(v,(float,int))
                             or not math.isfinite(v) or v <= 0 for v in scales.values()):
            raise ValueError('positive explicit coordinate scales required')
        for h in history:
            available = datetime.fromisoformat(h['available_at'])
            aware(available)
            if available > datetime.fromisoformat(h['time']):
                raise ValueError('future parameter drift history')
            if set(h['parameters']) != set(scales) or not h['source_ref'] or not h['vintage']:
                raise ValueError('drift coordinates/provenance missing')
            validate_parameters(h['parameters'],performance_search=True)
            for v in h['parameters'].values():
                if not math.isfinite(v):
                    raise ValueError('nonfinite drift')
        result[identity] = {'raw':history,'times':[t.isoformat() for t in times],
            'scaled_deltas':[{k:(b['parameters'][k]-a['parameters'][k])/scales[k] for k in scales}
                             for a,b in zip(history,history[1:])],
            'coordinate_scales':scales,'convention':plan['drift_convention']}
    return result


def acceptance(results, scope):
    """Protocol success only. FAIL/NOT_RUN never offset or become skill."""
    complete = set(results) == set(MANDATORY) and all(
        r.get('status') == 'PASS' and r.get('role') == 'MANDATORY'
        and r.get('report_hash') and r.get('trial_id') for r in results.values())
    return {'scope':scope, 'status':'PASS' if complete else 'NOT_ACCEPTED',
        'software_freeze_eligible':complete and scope==SCOPES[0],
        'real_pit_research_validated':complete and scope==SCOPES[1],
        'decision':'NOT_ASSESSED_PENDING_C8','official':False,'holdout_state':'UNCONSUMED',
        'tax_mode':'EXCLUDED'}


def run_robustness(ledger, split, source, bundles, drift, *, evaluator_id, recorded_at):
    aware(recorded_at)
    spec = ledger.registration()
    _verify_split(ledger,split,spec)
    stored = json.loads((ledger.directory/'robustness.json').read_text())
    body, plan = stored['body'],stored['body']['plan']
    if (stored['sha256'] != digest(body) or body['experiment_hash'] != digest(spec)
            or body['split_hash'] != digest(split.payload()) or body['policy'] != POLICY
            or tuple(body['mandatory']) != MANDATORY or evaluator_id != plan['evaluator_id']
            or recorded_at < datetime.fromisoformat(plan['evaluation_time'])):
        raise ValueError('C6 preregistration/evaluator/time mismatch')
    with (ledger.directory/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        _recover_pending(ledger,recorded_at)
        if ledger.trials.records():
            raise ValueError('C6 inference already consumed; no post-result resampling')
        failure = None
        try:
            if digest(_snapshot(source,bundles,drift)) != digest(body['package']):
                raise ValueError('changed frozen input / upstream invalidation')
            inventory,roster,samples = _qualified(ledger,split,source,bundles,body)
        except MissingStatisticalEvidence as exc:
            failure = ('NOT_RUN',str(exc))
        except (ValueError,KeyError,TypeError,OSError) as exc:
            failure = ('FAIL',type(exc).__name__+': '+str(exc))
        results = {}
        for diagnostic in MANDATORY:
            if len(ledger.trials.records()) >= spec['search_budget']['max_trials']:
                results[diagnostic] = {'status':'NOT_RUN','role':'MANDATORY','reason':'REGISTERED_BUDGET_EXHAUSTED',
                    'missing_evidence':['diagnostic budget'],'affected_scope':plan['scope']}
                continue
            trial_id = 'robustness-'+diagnostic
            _write_json(ledger.directory/'pending.json',{'trial_id':trial_id,'parameters':{}})
            state,reason,output = 'PASS',None,None
            try:
                if failure:
                    state,reason = failure
                else:
                    output = _diagnostic(diagnostic,split,plan,inventory,roster,samples,bundles,drift,body)
                    # Reject non-finite/non-serializable method output before claiming PASS.
                    digest(output)
            except MissingStatisticalEvidence as exc:
                state,reason = 'NOT_RUN',str(exc)
            except (ValueError,KeyError,TypeError,OSError,OverflowError) as exc:
                state,reason = 'FAIL',type(exc).__name__+': '+str(exc)
            except Exception as exc:
                state,reason = 'FAIL',type(exc).__name__+': '+str(exc)
            report = {'diagnostic':diagnostic,'role':'MANDATORY','status':state,'reason':reason,
                'scope':plan['scope'],'output':output if state=='PASS' else None,
                'registration_hash':stored['sha256'],'package_hash':spec['data_hash'],
                'source_hash':body['source_hash'],'method_version':METHOD_VERSION,'policy':POLICY,
                'partition':plan['partition'],'variant':plan['variant'],'mode':split.plan.mode,
                'missing_evidence':[] if state=='PASS' else [reason],
                'affected_scope':plan['scope'],'decision':'NOT_ASSESSED_PENDING_C8',
                'official':False,'holdout_state':'UNCONSUMED','tax_mode':'EXCLUDED'}
            report = _to_json(report)
            name = 'robustness-report-'+sha256(trial_id.encode()).hexdigest()+'.json'
            _write_json(ledger.directory/name,report)
            ledger.append(TrialRecord(trial_id,spec['experiment_id'],len(ledger.trials.records()),
                recorded_at,TrialStatus.SUCCESS if state=='PASS' else
                TrialStatus.REJECTED if state=='NOT_RUN' else TrialStatus.FAILED,
                {},{'diagnostic_complete':1.} if state=='PASS' else {},
                (reason+'; ' if reason else '')+'report_sha256='+digest(report)))
            (ledger.directory/'pending.json').unlink()
            results[diagnostic] = {'status':state,'role':'MANDATORY','reason':reason,
                'trial_id':trial_id,'report_hash':digest(report),'report_file':name}
        result = {**acceptance(results,plan['scope']), 'results':results,
                  'registration_hash':stored['sha256'],'source_hash':body['source_hash']}
        _write_json(ledger.directory/'robustness-acceptance.json',result)
        return result


def _diagnostic(kind,split,plan,inventory,roster,samples,bundles,drift,body):
    if kind == 'DRIFT':
        return _drift(drift,roster,plan)
    base = _family(split,plan,bundles,roster,samples)
    series = base['adapter']['series']
    if kind == 'PSR':
        return {k:probabilistic_sharpe(v,reference_sharpe=plan['reference_sharpe']) for k,v in series.items()}
    if kind.startswith('DSR_'):
        output = deflated_sharpe_family(roster,series,
            all_charged_attempts=len(inventory['attempt_ids']),
            candidate_count_provenance=digest(inventory['roster']),
            attempt_count_provenance=digest(inventory['rows']),
            registered_sharpe_variance=plan['sharpe_variance'])
        view = 'DISTINCT_FULL_CANDIDATES' if kind=='DSR_DISTINCT' else 'ALL_CHARGED_ATTEMPTS'
        return {**output['views'][view], 'all_attempt_ids':inventory['attempt_ids'],
                'all_status_counts':inventory['status_counts'],
                'sharpe_variance':output['sharpe_variance'],
                'variance_provenance':output['variance_provenance'],
                'independent_trial_count_estimated':False}
    if kind == 'CSCV_PBO':
        return cscv_pbo(roster,series,block_count=plan['block_count'])
    kwargs = {'block_length':plan['block_length'],'replicates':plan['replicates'],'seed':plan['seed']}
    if kind in ('BOOTSTRAP','REALITY_EQUAL','REALITY_MCAP'):
        equal = _family(split,plan,bundles,roster,samples,'EQUAL_CONTROL')
        mcap = _family(split,plan,bundles,roster,samples,'MCAP_CONTROL')
        # A benchmark is one shared registered path, not candidate-dependent.
        benchmarks = {}
        for name,value in (('EQUAL',equal),('MCAP',mcap)):
            paths = value['net']
            if len({digest(v) for v in paths.values()}) != 1:
                raise ValueError('benchmark identity must be shared across full candidate family')
            benchmarks[name] = paths[roster[0]]
        if kind == 'BOOTSTRAP':
            # Bootstrap primary statistic uses risk-free excess for both candidates and baselines.
            rf = tuple(p['risk_free_return'] for p in base['periods'][roster[0]])
            return joint_circular_bootstrap(roster,series,
                {k:tuple(a-b for a,b in zip(v,rf)) for k,v in benchmarks.items()},
                quantiles=tuple(plan['quantiles']),quantile_convention=plan['quantile_convention'],**kwargs)
        name = 'EQUAL' if kind=='REALITY_EQUAL' else 'MCAP'
        return {**family_reality_check(roster,base['net'],benchmarks[name],**kwargs),
                'benchmark_id':name,'benchmark_hash':digest(benchmarks[name])}
    if kind in SCENARIOS:
        changed = _family(split,plan,bundles,roster,samples,kind)
        return {'definitions':{k:bundles[k]['scenarios'][kind]['definition'] for k in roster},
            'baseline':base,'scenario':changed,
            'period_excess_deltas':{k:tuple(b-a for a,b in zip(series[k],changed['adapter']['series'][k]))
                                   for k in roster}}
    if kind == 'EXECUTION_DELAY':
        return {'baseline':base,'one_opportunity_delay':_family(split,plan,bundles,roster,samples,delay=1)}
    if kind == 'COST_STRESS':
        views = {str(m):_family(split,plan,bundles,roster,samples,multiplier=m) for m in (1,2,3)}
        for identity in roster:
            if len({v['reports'][identity]['path_hash'] for v in views.values()}) != 1:
                raise ValueError('isolated costs must preserve identical gross fill path')
        return views
    raise ValueError('unregistered diagnostic')


def resolve_robustness(ledger, split, source, bundles, drift):
    """Re-resolve current lineage; saved PASS cannot survive invalidation/tamper."""
    stored = json.loads((ledger.directory/'robustness.json').read_text())
    body = stored['body']
    if stored['sha256'] != digest(body) or digest(_snapshot(source,bundles,drift)) != digest(body['package']):
        raise ValueError('changed/invalidated registered robustness evidence')
    _verify_split(ledger,split,ledger.registration())
    _qualified(ledger,split,source,bundles,body)
    result = json.loads((ledger.directory/'robustness-acceptance.json').read_text())
    if result['registration_hash'] != stored['sha256']:
        raise ValueError('acceptance registration hash mismatch')
    checked = {}
    for kind in MANDATORY:
        entry = result['results'][kind]
        trial = ledger.supporting_trial(entry['trial_id'])
        report = json.loads((ledger.directory/entry['report_file']).read_text())
        if (report['diagnostic'] != kind or report['status'] != 'PASS'
                or entry['report_hash'] != digest(report)
                or trial['reason'] != 'report_sha256='+digest(report)
                or report['registration_hash'] != stored['sha256']
                or report['package_hash'] != ledger.registration()['data_hash']):
            raise ValueError('robustness terminal report hash/lineage mismatch')
        checked[kind] = entry
    expected = {**acceptance(checked,body['plan']['scope']),'results':checked,
                'registration_hash':stored['sha256'],'source_hash':body['source_hash']}
    if result != expected:
        raise ValueError('acceptance tamper/incomplete mandatory diagnostics')
    return deepcopy(expected)
