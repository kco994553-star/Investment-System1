"""C2 chronological splits under approved EVL-SPLIT-01 v1.1.

Primary purges labels unavailable at the next evaluation boundary. The paired
stress view adds one actual registered rebalance interval; neither chooses a
winner. This module does not load returns or consume Final Holdout.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import os

from .contracts import DatasetSplit
from .experiments import ExperimentLedger
from .ledger import canonical_json
from .pit import PITGuard, PITObservation, PITViolation

POLICY_ID = 'EVL-SPLIT-01_v1.1'


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise PITViolation('C2 requires timezone-aware timestamps')


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def __post_init__(self):
        aware(self.start)
        aware(self.end)
        if self.start >= self.end:
            raise ValueError('empty or reversed window')

    def contains(self, instant: datetime) -> bool:
        return self.start <= instant < self.end


@dataclass(frozen=True)
class SplitPlan:
    train: Window
    validation: Window
    oos: Window
    mode: str

    def __post_init__(self):
        if self.mode not in ('ROLLING', 'EXPANDING', 'C0_ADAPTED'):
            raise ValueError('unknown split mode')
        if self.train.end > self.validation.start or self.validation.end > self.oos.start:
            raise ValueError('overlapping partitions')

    @classmethod
    def from_c0(cls, split: DatasetSplit):
        if split.purge_seconds or split.embargo_seconds:
            raise ValueError('C0 arbitrary gap metadata cannot replace approved policy')
        # Python datetime precision is one microsecond; retain inclusive membership.
        windows = [Window(getattr(split, name + '_start'),
                          getattr(split, name + '_end') + timedelta(microseconds=1))
                   for name in ('train', 'validation', 'oos')]
        return cls(*windows, 'C0_ADAPTED')


def _anniversary(start: datetime, years: int) -> datetime:
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        # Calendar anniversary of Feb 29 in a non-leap year; never 365-day years.
        if (start.month, start.day) != (2, 29):
            raise
        return start.replace(year=start.year + years, day=28)


def annual_splits(start: datetime, available_end: datetime) -> tuple[SplitPlan, ...]:
    aware(start)
    aware(available_end)
    out, year = [], 0
    while _anniversary(start, year + 7) <= available_end:
        validation = Window(_anniversary(start, year + 5), _anniversary(start, year + 6))
        oos = Window(validation.end, _anniversary(start, year + 7))
        for mode in ('ROLLING', 'EXPANDING'):
            train = Window(_anniversary(start, year) if mode == 'ROLLING' else start,
                           validation.start)
            out.append(SplitPlan(train, validation, oos, mode))
        year += 1
    return tuple(out)


@dataclass(frozen=True)
class SplitContract:
    plan: SplitPlan
    registered_at: datetime
    holdout_start: datetime
    max_label_horizon: timedelta
    rebalance_schedule: tuple[datetime, ...]
    schedule_id: str

    def __post_init__(self):
        aware(self.registered_at)
        aware(self.holdout_start)
        if self.max_label_horizon <= timedelta(0) or not self.schedule_id:
            raise ValueError('missing horizon/schedule identity')
        if self.plan.oos.end > self.holdout_start:
            raise PITViolation('Final Holdout cannot enter research split')
        schedule = self.rebalance_schedule
        for instant in schedule:
            aware(instant)
        if tuple(sorted(set(schedule))) != schedule:
            raise ValueError('schedule must be unique and chronological')
        for boundary in (self.plan.validation.start, self.plan.oos.start):
            if boundary not in schedule or schedule.index(boundary) == 0:
                raise ValueError('boundary needs its actual preceding rebalance timestamp')

    def cutoff(self, boundary: datetime, stress: bool) -> datetime:
        if not stress:
            return boundary
        return self.rebalance_schedule[self.rebalance_schedule.index(boundary) - 1]

    def payload(self) -> dict:
        return {
            'policy_id': POLICY_ID, 'registered_at': self.registered_at.isoformat(),
            'holdout_start': self.holdout_start.isoformat(),
            'max_label_horizon_microseconds': self.max_label_horizon // timedelta(microseconds=1),
            'schedule_id': self.schedule_id,
            'rebalance_schedule': [x.isoformat() for x in self.rebalance_schedule],
            'mode': self.plan.mode,
            'windows': {name: {'start': getattr(self.plan, name).start.isoformat(),
                               'end': getattr(self.plan, name).end.isoformat()}
                        for name in ('train', 'validation', 'oos')},
            'variants': ['PRIMARY', 'REBALANCE_GAP_STRESS'],
        }


@dataclass(frozen=True)
class LabeledSample:
    sample_id: str
    decision_time: datetime
    label_end: datetime
    label_available_at: datetime
    source_id: str
    vintage: str
    observations: tuple[PITObservation, ...]

    def validate(self, horizon: timedelta) -> None:
        for instant in (self.decision_time, self.label_end, self.label_available_at):
            aware(instant)
        if not self.sample_id or not self.source_id or not self.vintage or not self.observations:
            raise PITViolation('missing sample/label/feature provenance')
        if not self.decision_time < self.label_end <= self.decision_time + horizon:
            raise PITViolation('label interval exceeds preregistered horizon')
        if self.label_available_at < self.label_end:
            raise PITViolation('label published before its outcome interval ends')
        for observation in self.observations:
            aware(observation.available_at)
            if not observation.observation_id:
                raise PITViolation('missing observation identity')
        PITGuard.enforce(self.decision_time, self.observations)


@dataclass(frozen=True)
class PartitionResult:
    variant: str
    retained: dict[str, tuple[str, ...]]
    excluded: dict[str, str]
    cutoffs: dict[str, str]
    contract_hash: str

    @property
    def status(self) -> str:
        return 'READY' if all(self.retained.values()) else 'NOT_RUN_INSUFFICIENT_DATA'


def split_samples(contract: SplitContract, samples: tuple[LabeledSample, ...],
                  *, stress: bool) -> PartitionResult:
    ids = [s.sample_id for s in samples]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate sample IDs')
    retained = {name: [] for name in ('train', 'validation', 'oos')}
    excluded = {}
    cutoffs = {
        'train': contract.cutoff(contract.plan.validation.start, stress),
        'validation': contract.cutoff(contract.plan.oos.start, stress),
        # OOS labels must finish within OOS; research may not use holdout outcomes.
        'oos': contract.plan.oos.end,
    }
    for sample in samples:
        sample.validate(contract.max_label_horizon)
    for sample in sorted(samples, key=lambda x: (x.decision_time, x.sample_id)):
        if sample.decision_time >= contract.holdout_start:
            raise PITViolation('Final Holdout sample supplied to research')
        partition = next((name for name in retained
                          if getattr(contract.plan, name).contains(sample.decision_time)), None)
        if partition is None:
            excluded[sample.sample_id] = 'OUTSIDE_NOMINAL_WINDOWS'
        elif sample.label_end >= cutoffs[partition]:
            excluded[sample.sample_id] = partition.upper() + '_LABEL_INTERVAL_CUTOFF'
        elif sample.label_available_at >= cutoffs[partition]:
            excluded[sample.sample_id] = partition.upper() + '_LABEL_PUBLICATION_CUTOFF'
        else:
            retained[partition].append(sample.sample_id)
    return PartitionResult(
        'REBALANCE_GAP_STRESS' if stress else 'PRIMARY',
        {key: tuple(value) for key, value in retained.items()}, excluded,
        {key: value.isoformat() for key, value in cutoffs.items()},
        sha256(canonical_json(contract.payload()).encode()).hexdigest(),
    )


def register_split(ledger: ExperimentLedger, contract: SplitContract) -> str:
    """Bind both views to C1 before any trials; one immutable file per contract."""
    import fcntl
    spec = ledger.registration()
    if contract.registered_at < datetime.fromisoformat(spec['registered_at']):
        raise ValueError('split registration precedes experiment registration')
    c0 = spec['dataset_split']
    expected = SplitPlan.from_c0(DatasetSplit(**{
        key: datetime.fromisoformat(value) if key.endswith(('_start', '_end')) else value
        for key, value in c0.items()
    }))
    if any(getattr(expected, name) != getattr(contract.plan, name)
           for name in ('train', 'validation', 'oos')):
        raise ValueError('split windows differ from preregistered experiment')
    payload = {**contract.payload(), 'experiment_id': spec['experiment_id'],
               'experiment_sha256': sha256(canonical_json(spec).encode()).hexdigest()}
    digest = sha256(canonical_json(payload).encode()).hexdigest()
    with (ledger.directory / 'experiment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ledger.trials.records():
            raise ValueError('split cannot be registered after results')
        with (ledger.directory / 'split.json').open('x', encoding='utf-8') as stream:
            stream.write(canonical_json({'sha256': digest, 'split': payload}) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    return digest
