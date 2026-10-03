"""C0 contracts for EVL_SPEC_v0.1.

These contracts are additive. They do not redefine upstream QGV, Technical,
Macro, Portfolio/Risk, Universe, provenance, or Track A data contracts.
Official EVL outputs are always Pre-Tax.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

EVL_CONTRACT_ID = "EVL_SPEC_v0.1"
TAX_MODE = "EXCLUDED"

class TrialStatus(str, Enum):
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    EARLY_STOPPED = "EARLY_STOPPED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"

class HoldoutState(str, Enum):
    UNCONSUMED = "UNCONSUMED"
    CONSUMED = "CONSUMED"

@dataclass(frozen=True)
class DatasetSplit:
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    oos_start: datetime
    oos_end: datetime
    purge_seconds: int = 0
    embargo_seconds: int = 0

    def __post_init__(self) -> None:
        if not (self.train_start <= self.train_end < self.validation_start <=
                self.validation_end < self.oos_start <= self.oos_end):
            raise ValueError("dataset split must be ordered and non-overlapping")
        if self.purge_seconds < 0 or self.embargo_seconds < 0:
            raise ValueError("purge/embargo cannot be negative")

@dataclass(frozen=True)
class ParameterSpace:
    values: Mapping[str, Sequence[Any]]
    complexity_budget: int
    precision_limit: int

    def __post_init__(self) -> None:
        if self.complexity_budget < 0 or self.precision_limit < 0:
            raise ValueError("budgets cannot be negative")
        if any(not tuple(v) for v in self.values.values()):
            raise ValueError("parameter domains cannot be empty")

@dataclass(frozen=True)
class SearchBudget:
    max_trials: int
    method: str = "CONSTRAINED_GRID"

    def __post_init__(self) -> None:
        if self.max_trials <= 0:
            raise ValueError("max_trials must be positive")

@dataclass(frozen=True)
class MetricSet:
    metric_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.metric_ids or len(set(self.metric_ids)) != len(self.metric_ids):
            raise ValueError("metric_ids must be non-empty and unique")

@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    registered_at: datetime
    decision_time: datetime
    dataset_id: str
    dataset_vintage: str
    data_hash: str
    code_hash: str
    seed: int
    parameter_space: ParameterSpace
    search_budget: SearchBudget
    dataset_split: DatasetSplit
    metric_set: MetricSet
    tax_mode: str = TAX_MODE
    contract_id: str = EVL_CONTRACT_ID

    def __post_init__(self) -> None:
        if self.tax_mode != TAX_MODE:
            raise ValueError("Official EVL is Pre-Tax only; TAX_MODE must be EXCLUDED")
        for value in (self.experiment_id, self.dataset_id, self.dataset_vintage,
                      self.data_hash, self.code_hash):
            if not value:
                raise ValueError("required experiment identity/hash field is empty")

@dataclass(frozen=True)
class TrialRecord:
    trial_id: str
    experiment_id: str
    sequence: int
    recorded_at: datetime
    status: TrialStatus
    parameters: Mapping[str, Any]
    metrics: Mapping[str, float] = field(default_factory=dict)
    reason: str | None = None
    parent_trial_id: str | None = None

    def __post_init__(self) -> None:
        if not self.trial_id or not self.experiment_id or self.sequence < 0:
            raise ValueError("invalid trial identity/sequence")
        if self.status != TrialStatus.SUCCESS and not self.reason:
            raise ValueError("non-success trials require a reason")

@dataclass(frozen=True)
class FreezeManifest:
    artifact_id: str
    profile: str
    experiment_id: str
    candidate_id: str
    spec_id: str
    code_hash: str
    data_hash: str
    dataset_vintage: str
    parameters: Mapping[str, Any]
    thresholds: Mapping[str, Any]
    holdout_state: HoldoutState
    promotion_state: str
    lineage_ids: tuple[str, ...]
    tax_mode: str = TAX_MODE

    def __post_init__(self) -> None:
        if self.spec_id != EVL_CONTRACT_ID:
            raise ValueError("freeze manifest must bind EVL_SPEC_v0.1")
        if self.tax_mode != TAX_MODE:
            raise ValueError("Official freeze manifest must remain Pre-Tax")
        if not self.lineage_ids:
            raise ValueError("freeze manifest requires lineage")
