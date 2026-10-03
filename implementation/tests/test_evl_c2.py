from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import pytest
from investment_system.evl import DatasetSplit, ExperimentSpec, MetricSet, ParameterSpace, SearchBudget, TrialRecord, TrialStatus
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.pit import PITObservation, PITViolation
from investment_system.evl.splits import SplitContract, SplitPlan, Window, LabeledSample, annual_splits, register_split, split_samples


def dt(year, month=1, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def contract():
    return SplitContract(annual_splits(dt(2010), dt(2017))[0], dt(2020), dt(2017), timedelta(days=90),
        (dt(2014, 12), dt(2015), dt(2015, 12), dt(2016)), 'monthly-boundaries-v1')


def sample(name, decision, end=None, available=None):
    end = end or decision + timedelta(days=20)
    return LabeledSample(name, decision, end, available or end, 'labels', 'v1',
                         (PITObservation(name, decision, 'features', 'v1'),))


def samples():
    return (sample('train', dt(2014, 6)), sample('validation', dt(2015, 6)),
            sample('oos', dt(2016, 6)), sample('edge', dt(2014, 12)))


def test_annual_calendar_windows_compare_modes_and_insufficient_history():
    plans = annual_splits(dt(2010), dt(2019))
    assert len(plans) == 6
    assert plans[0].train == Window(dt(2010), dt(2015))
    assert plans[2].train == Window(dt(2011), dt(2016))
    assert plans[3].train == Window(dt(2010), dt(2016))
    assert plans[2].oos == plans[3].oos == Window(dt(2017), dt(2018))
    assert annual_splits(dt(2010), dt(2016)) == ()


def test_leap_day_anniversaries_do_not_drift():
    plans = annual_splits(dt(2012, 2, 29), dt(2021, 3))
    assert plans[0].train.end == dt(2017, 2, 28)
    assert plans[2].validation.end == dt(2019, 2, 28)
    assert plans[2].oos.end == dt(2020, 2, 29)


def test_primary_and_stress_both_reported_without_selection():
    c = contract()
    a, b = (split_samples(c, samples(), stress=stress) for stress in (False, True))
    assert a.status == b.status == 'READY'
    assert a.retained['train'] == ('train', 'edge')
    assert b.retained['train'] == ('train',)
    assert b.excluded['edge'] == 'TRAIN_LABEL_INTERVAL_CUTOFF'
    assert a.contract_hash == b.contract_hash
    assert a.retained['oos'] == b.retained['oos']


@pytest.mark.parametrize('boundary', [dt(2015), dt(2014, 12)])
def test_equality_excluded_microsecond_before_retained(boundary):
    stress = boundary == dt(2014, 12)
    s = sample('s', boundary-timedelta(days=20), boundary-timedelta(microseconds=1))
    assert 's' in split_samples(contract(), (s,), stress=stress).retained['train']
    s = replace(s, label_end=boundary, label_available_at=boundary)
    assert 's' in split_samples(contract(), (s,), stress=stress).excluded


def test_label_publication_lag_and_empty_partition():
    s = sample('delayed', dt(2014, 12), dt(2014, 12, 21), dt(2015))
    result = split_samples(contract(), (s,), stress=False)
    assert result.excluded['delayed'] == 'TRAIN_LABEL_PUBLICATION_CUTOFF'
    assert result.status == 'NOT_RUN_INSUFFICIENT_DATA'


@pytest.mark.parametrize('change', [
    {'source_id': ''}, {'vintage': ''}, {'observations': ()},
    {'label_available_at': None}, {'decision_time': datetime(2014, 6, 1)},
    {'label_end': dt(2015)},
    {'observations': (PITObservation('x', dt(2014, 6, 2), 'sec', 'v1'),)},
])
def test_unknown_future_invalid_metadata_fail_closed(change):
    with pytest.raises(PITViolation):
        split_samples(contract(), (replace(sample('s', dt(2014, 6)), **change),), stress=False)


def test_holdout_sample_and_outcomes_blocked():
    c = contract()
    with pytest.raises(PITViolation, match='Holdout'):
        split_samples(c, (sample('holdout', dt(2017)),), stress=False)
    result = split_samples(c, (sample('cross', dt(2016, 12, 20)),), stress=False)
    assert result.excluded['cross'] == 'OOS_LABEL_INTERVAL_CUTOFF'
    with pytest.raises(PITViolation, match='Holdout'):
        replace(c, holdout_start=dt(2016))


def test_duplicate_and_unregistered_schedule_rejected():
    c = contract()
    with pytest.raises(ValueError, match='duplicate'):
        split_samples(c, (samples()[0], samples()[0]), stress=False)
    with pytest.raises(ValueError, match='preceding'):
        replace(c, rebalance_schedule=(dt(2015), dt(2016)))


def test_timezone_equivalence_and_order_invariance():
    original = samples()
    shifted = tuple(replace(s, decision_time=s.decision_time.astimezone(timezone(timedelta(hours=9)))) for s in original)
    assert split_samples(contract(), original, stress=False) == split_samples(contract(), tuple(reversed(shifted)), stress=False)


def c0_split(c):
    us = timedelta(microseconds=1)
    return DatasetSplit(c.plan.train.start, c.plan.train.end-us,
                        c.plan.validation.start, c.plan.validation.end-us,
                        c.plan.oos.start, c.plan.oos.end-us)


def test_c0_adapter_preserves_inclusive_membership():
    c = contract()
    old = c0_split(c)
    adapted = SplitPlan.from_c0(old)
    assert adapted.train.contains(old.train_end)
    assert not adapted.train.contains(c.plan.train.end)
    with pytest.raises(ValueError, match='arbitrary'):
        SplitPlan.from_c0(replace(old, embargo_seconds=1))


def test_registration_binds_views_windows_and_cannot_follow_trials(tmp_path):
    c = contract()
    spec = ExperimentSpec('exp', dt(2020), dt(2016), 'dataset', 'v1', 'hash', 'code', 7,
        ParameterSpace({'x':[1]}, 1, 1), SearchBudget(1), c0_split(c), MetricSet(('cagr',)))
    ledger = ExperimentLedger(tmp_path)
    ledger.register(spec)
    register_split(ledger, c)
    assert json.loads((tmp_path/'split.json').read_text())['split']['variants'] == ['PRIMARY','REBALANCE_GAP_STRESS']
    with pytest.raises(FileExistsError):
        register_split(ledger, c)
    ledger.append(TrialRecord('t', 'exp', 0, dt(2020), TrialStatus.FAILED, {}, reason='failed'))
    with pytest.raises(ValueError, match='after results'):
        register_split(ledger, c)
