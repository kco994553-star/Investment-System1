"""C4 registered annual walk-forward orchestration, including paired gap stress.

Trusted versioned pipeline hooks receive only their own partitions. This is an
API isolation boundary, not a sandbox for malicious callbacks/closures. C5 owns
search; every search attempt inside a fitting hook must use its own C1 ledger.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import fcntl
import json
import math
import os
from typing import Callable

from ..contracts.models import _to_json
from .contracts import TrialRecord, TrialStatus
from .experiments import ExperimentLedger
from .ledger import canonical_json
from .metrics import evaluate_metrics
from .splits import LabeledSample, SplitContract, annual_splits, aware, split_samples


def digest(value) -> str:
    return sha256(canonical_json(_to_json(value)).encode()).hexdigest()


@dataclass(frozen=True)
class LearningRow:
    sample: LabeledSample
    features: dict
    outcome: dict

    def predictor_input(self) -> dict:
        return {'sample_id': self.sample.sample_id, 'decision_time': self.sample.decision_time,
                'features': deepcopy(self.features)}


def dataset_digest(rows: tuple[LearningRow, ...]) -> str:
    return digest([asdict(row) for row in sorted(rows, key=lambda r: r.sample.sample_id)])


@dataclass(frozen=True)
class Pipeline:
    pipeline_id: str
    fit: Callable
    calibrate: Callable
    predict: Callable
    evaluate: Callable


@dataclass(frozen=True)
class RunnerContract:
    pipeline_id: str
    periods_per_year: float
    tail_fraction: float
    evaluation_time: datetime
    registered_at: datetime

    def payload(self) -> dict:
        return _to_json(asdict(self))


def register_runner(ledger: ExperimentLedger, split: SplitContract,
                    runner: RunnerContract, rows: tuple[LearningRow, ...]) -> str:
    aware(runner.registered_at)
    aware(runner.evaluation_time)
    if (not runner.pipeline_id or isinstance(runner.periods_per_year, bool)
            or not math.isfinite(runner.periods_per_year) or runner.periods_per_year <= 0
            or isinstance(runner.tail_fraction, bool) or not 0 < runner.tail_fraction <= 1):
        raise ValueError('invalid runner contract')
    spec = ledger.registration()
    if runner.registered_at < max(datetime.fromisoformat(spec['registered_at']), split.registered_at):
        raise ValueError('runner registration must follow experiment/split registration')
    if spec['data_hash'] != dataset_digest(rows):
        raise ValueError('dataset differs from registered hash')
    _verify_split(ledger, split, spec)
    # Verify both complete partitions and all metadata before accepting a runner.
    for stress in (False, True):
        split_samples(split, tuple(r.sample for r in rows), stress=stress)
    body = {'runner': runner.payload(), 'experiment_hash': digest(spec),
            'split_hash': digest(split.payload()), 'dataset_hash': spec['data_hash']}
    with (ledger.directory/'experiment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ledger.trials.records():
            raise ValueError('runner registration cannot follow results')
        with (ledger.directory/'runner.json').open('x') as stream:
            stream.write(canonical_json({'sha256': digest(body), 'body': body})+'\n')
            stream.flush()
            os.fsync(stream.fileno())
    return digest(body)


def _verify_split(ledger, split, spec):
    try:
        stored = json.loads((ledger.directory/'split.json').read_text())
        expected = {**split.payload(), 'experiment_id': spec['experiment_id'],
                    'experiment_sha256': digest(spec)}
        if stored['sha256'] != digest(stored['split']) or stored['split'] != expected:
            raise ValueError('split registration mismatch')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('missing/malformed split preregistration') from exc


def _verify_registration(ledger, split, runner, rows):
    spec = ledger.registration()
    _verify_split(ledger, split, spec)
    try:
        stored = json.loads((ledger.directory/'runner.json').read_text())
        expected = {'runner': runner.payload(), 'experiment_hash': digest(spec),
                    'split_hash': digest(split.payload()), 'dataset_hash': dataset_digest(rows)}
        if stored['sha256'] != digest(stored['body']) or stored['body'] != expected:
            raise ValueError('runner registration mismatch')
        if expected['dataset_hash'] != spec['data_hash']:
            raise ValueError('dataset registration mismatch')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('missing/malformed runner preregistration') from exc
    return spec


def _metrics(report: dict, metric_ids: list[str]) -> dict:
    net = report['views']['NET_OF_TRADING_COST_PRE_TAX']
    supported = {'net_'+key: value for key, value in net.items()
                 if key in ('cagr', 'mdd', 'sharpe', 'sortino', 'calmar', 'total_return')}
    if not set(metric_ids) <= supported.keys():
        raise ValueError('unsupported registered metric')
    if any(supported[key] is None for key in metric_ids):
        raise ValueError('registered metric undefined for this history')
    return {key: supported[key] for key in metric_ids}


def run_fold(ledger: ExperimentLedger, split: SplitContract, runner: RunnerContract,
             rows: tuple[LearningRow, ...], pipeline: Pipeline, parameters: dict,
             *, trial_prefix: str, recorded_at: datetime) -> dict:
    """Train -> threshold-only calibration -> frozen OOS prediction -> scoring.

    Both predeclared variants are reported, with no winner selection. Reports are retained before the terminal ledger append. An interrupted attempt
    blocks reuse until its pending journal is recovered as FAILED.
    """
    aware(recorded_at)
    with (ledger.directory/'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _run_fold(ledger, split, runner, rows, pipeline, parameters,
                         trial_prefix=trial_prefix, recorded_at=recorded_at)


def _run_fold(ledger, split, runner, rows, pipeline, parameters, *, trial_prefix, recorded_at):
    spec = _verify_registration(ledger, split, runner, rows)
    if pipeline.pipeline_id != runner.pipeline_id or recorded_at < runner.registered_at:
        raise ValueError('pipeline/registration time mismatch')
    domain = spec['parameter_space']['values']
    if set(parameters) != set(domain) or any(parameters[k] not in domain[k] for k in parameters):
        raise ValueError('parameters outside registered space')
    _recover_pending(ledger, recorded_at)
    existing = ledger.trials.records()
    attempts = sum(row['trial']['status'] != 'INVALIDATED' for row in existing)
    if attempts+2 > spec['search_budget']['max_trials']:
        return {'status': 'NOT_RUN_BUDGET', 'variants': [], 'official': False}
    ids = [trial_prefix+'-PRIMARY', trial_prefix+'-REBALANCE_GAP_STRESS']
    if not trial_prefix or any(row['trial']['trial_id'] in ids for row in existing):
        raise ValueError('trial identity already consumed')
    out = []
    by_id = {row.sample.sample_id: row for row in rows}
    for stress, trial_id in zip((False, True), ids):
        partition = split_samples(split, tuple(r.sample for r in rows), stress=stress)
        status, reason, metrics = TrialStatus.SUCCESS, None, {}
        record = {'variant': partition.variant, 'partition': asdict(partition),
                  'pipeline_id': pipeline.pipeline_id, 'data_hash': spec['data_hash'],
                  'code_hash': spec['code_hash'], 'seed': spec['seed'], 'tax_mode': 'EXCLUDED',
                  'experiment_id': spec['experiment_id'], 'trial_id': trial_id,
                  'parameters': deepcopy(parameters), 'runner': runner.payload()}
        pending = {'trial_id': trial_id, 'parameters': deepcopy(parameters)}
        pending_path = ledger.directory/'pending.json'
        _write_json(pending_path, pending)
        try:
            if partition.status != 'READY':
                status, reason = TrialStatus.REJECTED, 'NOT_RUN_INSUFFICIENT_DATA'
            else:
                train, validation, oos = (
                    tuple(deepcopy(by_id[i]) for i in partition.retained[name])
                    for name in ('train', 'validation', 'oos'))
                model = pipeline.fit(train, deepcopy(parameters), spec['seed'])
                model_hash = digest(model)
                thresholds = pipeline.calibrate(model, validation, spec['seed'])
                if digest(model) != model_hash:
                    raise ValueError('calibration mutated frozen model/parameters')
                threshold_hash = digest(thresholds)
                predictor_rows = tuple(row.predictor_input() for row in oos)
                predictions = pipeline.predict(model, thresholds, predictor_rows)
                if digest(model) != model_hash or digest(thresholds) != threshold_hash:
                    raise ValueError('OOS prediction mutated model/thresholds')
                if set(predictions) != set(partition.retained['oos']):
                    raise ValueError('prediction coverage mismatch')
                periods = tuple(pipeline.evaluate(deepcopy(predictions), oos))
                if len(periods) != len(oos) or any(
                    p.start != r.sample.decision_time or p.end != r.sample.label_end
                    for p, r in zip(periods, oos)):
                    raise ValueError('outcome periods do not match registered OOS rows')
                report = evaluate_metrics(periods, evaluation_time=runner.evaluation_time,
                    periods_per_year=runner.periods_per_year, tail_fraction=runner.tail_fraction)
                metrics = _metrics(report, spec['metric_set']['metric_ids'])
                record.update(model_hash=model_hash, threshold_hash=threshold_hash,
                              prediction_hash=digest(predictions), metrics_report=report,
                              model=deepcopy(model), thresholds=deepcopy(thresholds),
                              predictions=deepcopy(predictions))
                canonical_json(_to_json(record))
        except Exception as exc:
            status, reason = TrialStatus.FAILED, type(exc).__name__+': '+str(exc)
            metrics = {}
            for key in ('model', 'thresholds', 'predictions', 'metrics_report',
                        'model_hash', 'threshold_hash', 'prediction_hash'):
                record.pop(key, None)
        record.update(status=status.value, reason=reason)
        # Files use a content digest of the trial ID, never caller path components.
        report_path = ledger.directory/('report-'+sha256(trial_id.encode()).hexdigest()+'.json')
        encoded = canonical_json(_to_json(record))
        _write_json(report_path, _to_json(record))
        seq = len(ledger.trials.records())
        ledger.append(TrialRecord(trial_id, spec['experiment_id'], seq, recorded_at,
                                  status, deepcopy(parameters), metrics,
                                  (reason+'; ' if reason else '')+'report_sha256='+digest(record)))
        pending_path.unlink()
        out.append({'trial_id': trial_id, 'status': status.value, 'reason': reason,
                    'report_sha256': sha256(encoded.encode()).hexdigest(),
                    'report_file': report_path.name, 'metrics': metrics})
    return {'status': 'COMPLETED' if all(r['status']=='SUCCESS' for r in out) else 'NOT_ACCEPTED',
            'variants': out, 'official': False}


def _write_json(path, payload):
    # Exclusive final link exposes only complete bytes; an interrupted temporary
    # write leaves the pending journal for recovery, never a usable success.
    temporary = path.with_suffix(path.suffix+'.tmp')
    with temporary.open('x') as stream:
        stream.write(canonical_json(payload)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()


def _recover_pending(ledger, recorded_at):
    path = ledger.directory/'pending.json'
    if not path.exists():
        if path.with_suffix('.json.tmp').exists():
            raise ValueError('interrupted journal write requires inspection')
        return
    pending = json.loads(path.read_text())
    records = ledger.trials.records()
    if not any(r['trial']['trial_id'] == pending['trial_id'] for r in records):
        ledger.append(TrialRecord(pending['trial_id'], ledger.registration()['experiment_id'],
            len(records), recorded_at, TrialStatus.FAILED, pending['parameters'], {},
            'INTERRUPTED_ATTEMPT: pending journal recovered; reports cannot support promotion'))
    path.unlink()


def run_annual(jobs: tuple[dict, ...], *, start: datetime, end: datetime) -> list[dict]:
    """Require annual 5/1/1 rolling AND expanding coverage; refit each variant."""
    expected = annual_splits(start, end)
    if not expected:
        raise ValueError('insufficient 5Y/1Y/1Y coverage')
    if tuple(job['split'].plan for job in jobs) != expected:
        raise ValueError('annual rolling/expanding plans missing or reordered')
    if len({str(job['ledger'].directory.resolve()) for job in jobs}) != len(jobs):
        raise ValueError('folds require distinct experiment ledgers')
    # Preflight the entire cohort before consuming the first trial.
    for job in jobs:
        _verify_registration(job['ledger'], job['split'], job['runner'], job['rows'])
    return [run_fold(**job) for job in jobs]
