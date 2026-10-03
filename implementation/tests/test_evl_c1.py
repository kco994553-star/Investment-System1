from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from hashlib import sha256
import json
import pytest
from investment_system.evl import DatasetSplit, ExperimentSpec, MetricSet, ParameterSpace, SearchBudget, TrialLedger, TrialRecord, TrialStatus
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.ledger import canonical_json


def spec(max_trials=8):
    d = datetime(2020, 1, 1)
    return ExperimentSpec('exp', d, d, 'dataset', 'v1', 'datahash', 'codehash', 7,
        ParameterSpace({'w': [0.4, 0.5]}, 1, 1), SearchBudget(max_trials),
        DatasetSplit(*(d + timedelta(days=i) for i in range(6))), MetricSet(('cagr',)))


def trial(i=0, status=TrialStatus.SUCCESS, **kwargs):
    values = dict(trial_id=f't{i}', experiment_id='exp', sequence=i,
                  recorded_at=datetime(2020, 2, 1), status=status,
                  parameters={'w': .4}, metrics={'cagr': .1},
                  reason=None if status == TrialStatus.SUCCESS else 'test reason')
    values.update(kwargs)
    return TrialRecord(**values)


def test_registration_one_time_and_snapshots_mutable_spec(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    s = spec()
    ledger.register(s)
    original = ledger.registration_path.read_bytes()
    s.parameter_space.values['w'].append(.9)
    assert ledger.registration()['parameter_space']['values']['w'] == [.4, .5]
    with pytest.raises(FileExistsError):
        ledger.register(s)
    assert ledger.registration_path.read_bytes() == original


def test_unregistered_and_retroactive_results_blocked(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    with pytest.raises(ValueError, match='preregistration'):
        ledger.append(trial())
    ledger.trials.append(trial())
    with pytest.raises(ValueError, match='after trial'):
        ledger.register(spec())


def test_registration_hash_checked(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec())
    row = json.loads(ledger.registration_path.read_text())
    row['spec']['seed'] = 99
    ledger.registration_path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='digest'):
        ledger.append(trial())


def test_all_outcomes_logged_and_prefix_preserved(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec())
    prefix = b''
    for i, status in enumerate(TrialStatus):
        ledger.append(trial(i, status, parent_trial_id='t0' if status == TrialStatus.INVALIDATED else None))
        content = ledger.trials.path.read_bytes()
        assert content.startswith(prefix)
        prefix = content
    assert [r['trial']['status'] for r in ledger.trials.records()] == [s.value for s in TrialStatus]
    with pytest.raises(ValueError, match='invalidated'):
        ledger.supporting_trial('t0')


def test_budget_counts_failed_rejected_early_stopped(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec(max_trials=3))
    for i, status in enumerate((TrialStatus.FAILED, TrialStatus.REJECTED, TrialStatus.EARLY_STOPPED)):
        ledger.append(trial(i, status))
    ledger.append(trial(3))
    assert len(ledger.trials.records()) == 4
    with pytest.raises(ValueError, match='budget'):
        ledger.supporting_trial('t3')


def test_invalidation_does_not_spend_budget(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec(max_trials=2))
    ledger.append(trial(0))
    ledger.append(trial(1))
    ledger.append(trial(2, TrialStatus.INVALIDATED, parent_trial_id='t0'))
    assert ledger.supporting_trial('t1')['trial_id'] == 't1'
    with pytest.raises(ValueError, match='existing trial'):
        ledger.append(trial(3, TrialStatus.INVALIDATED, parent_trial_id='unknown'))


def test_unlogged_failed_out_of_space_missing_metrics_not_evidence(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec())
    with pytest.raises(ValueError, match='unlogged'):
        ledger.supporting_trial('missing')
    ledger.append(trial(0, TrialStatus.FAILED))
    ledger.append(trial(1, parameters={'w': .9}))
    ledger.append(trial(2, metrics={}))
    for tid, error in [('t0', 'unsuccessful'), ('t1', 'space'), ('t2', 'metrics')]:
        with pytest.raises(ValueError, match=error):
            ledger.supporting_trial(tid)
    ledger.append(trial(3))
    assert ledger.supporting_trial('t3')['parameters'] == {'w': .4}


def test_foreign_predated_results_blocked(tmp_path):
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec())
    with pytest.raises(ValueError, match='mismatch'):
        ledger.append(trial(experiment_id='other'))
    with pytest.raises(ValueError, match='precedes'):
        ledger.append(trial(recorded_at=datetime(2019, 1, 1)))
    ledger.trials.append(trial(experiment_id='other'))
    with pytest.raises(ValueError, match='foreign'):
        ledger.supporting_trial('t0')


def test_corruption_blocks_append_without_rewriting(tmp_path):
    ledger = TrialLedger(tmp_path / 'trials.jsonl')
    ledger.append(trial())
    row = json.loads(ledger.path.read_text())
    row['trial']['metrics']['cagr'] = 10
    corrupted = json.dumps(row) + '\n'
    ledger.path.write_text(corrupted)
    assert not ledger.verify()
    with pytest.raises(ValueError):
        ledger.append(trial(1))
    assert ledger.path.read_text() == corrupted


@pytest.mark.parametrize('raw', ['{', '\n', '{}\n', '{"trial":null}\n'])
def test_malformed_partial_ledger_fails_closed(tmp_path, raw):
    ledger = TrialLedger(tmp_path / 'trials.jsonl')
    ledger.path.write_text(raw)
    assert not ledger.verify()
    with pytest.raises(ValueError):
        ledger.append(trial())
    assert ledger.path.read_text() == raw


def test_duplicate_ids_detected_even_with_recomputed_digest(tmp_path):
    ledger = TrialLedger(tmp_path / 'trials.jsonl')
    ledger.append(trial())
    ledger.append(trial(1))
    rows = ledger.records()
    rows[1]['trial']['trial_id'] = 't0'
    rows[1]['sha256'] = sha256(canonical_json(rows[1]['trial']).encode()).hexdigest()
    ledger.path.write_text(''.join(canonical_json(r) + '\n' for r in rows))
    assert not ledger.verify()


def test_legacy_c0_envelopes_preserved(tmp_path):
    ledger = TrialLedger(tmp_path / 'trials.jsonl')
    ledger.append(trial())
    old = ledger.records()[0]
    del old['previous_sha256']
    legacy = json.dumps(old, sort_keys=True) + '\n'
    ledger.path.write_text(legacy)
    ledger.append(trial(1))
    assert ledger.path.read_text().startswith(legacy)
    assert ledger.verify()


@pytest.mark.parametrize('metric', [float('nan'), float('inf'), True, '0.1'])
def test_invalid_metrics_never_enter_ledger(tmp_path, metric):
    ledger = TrialLedger(tmp_path / 'trials.jsonl')
    with pytest.raises(ValueError):
        ledger.append(trial(metrics={'cagr': metric}))
    assert not ledger.path.exists()


def test_concurrent_writers_cannot_duplicate_sequence(tmp_path):
    path = tmp_path / 'trials.jsonl'
    def write(i):
        try:
            TrialLedger(path).append(trial(trial_id=f't{i}'))
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(write, (1, 2))) == 1
    assert TrialLedger(path).verify()
    assert len(TrialLedger(path).records()) == 1
