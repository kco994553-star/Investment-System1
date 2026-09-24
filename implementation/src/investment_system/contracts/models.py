from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Any, Optional

from .enums import (
    CalibrationLifecycle,
    CoverageState,
    ExecutionZone,
    Freshness,
    GateDecision,
    MacroState,
    ProfileKind,
    QualityState,
    TechnicalRegime,
)


def _to_json(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if hasattr(obj, "value"):
        return obj.value
    if isinstance(obj, dict):
        return {k: _to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json(v) for v in obj]
    return obj


@dataclass(frozen=True)
class DataStamp:
    data_stamp_id: str
    source_provider: str
    source_type: str
    source_reference: str
    published_at: datetime
    available_at: datetime
    observed_at: datetime
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    market_time_status: str = "CLOSE"
    freshness_status: Freshness = Freshness.GREEN
    estimated: bool = False
    estimation_method: Optional[str] = None
    quality_flags: tuple[str, ...] = ()
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class Identifier:
    company_id: str
    legal_name: str
    display_name: str
    ticker: str
    exchange: Optional[str] = None
    currency: str = "USD"
    country: str = "US"
    sector: Optional[str] = None
    industry: Optional[str] = None
    identifier_history: tuple[str, ...] = ()
    ambiguity_flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class FactorObservation:
    factor_id: str
    raw_value: Optional[float]
    score_0_100: Optional[float]
    quality: QualityState
    stamp_id: Optional[str]
    notes: str = ""


@dataclass(frozen=True)
class VCandidate:
    candidate_id: str
    lifecycle: CalibrationLifecycle
    weights: dict[str, float]
    v_score: Optional[float]
    blocked_reason: Optional[str] = None


@dataclass(frozen=True)
class QGVSnapshot:
    qgv_snapshot_id: str
    company_id: str
    analyzed_at: datetime
    as_of: datetime
    qgv_system_version: str
    qgv_standard_version: str
    qgv_analysis_contract: str
    implementation_line: str
    implementation_kind: str
    profile_kind: ProfileKind
    Q_score: Optional[float]
    G_score: Optional[float]
    V_score: Optional[float]
    V_policy_status: CalibrationLifecycle
    total_score: Optional[float]
    attractiveness_10: Optional[float]
    type_adjusted_score_100: Optional[float]
    confidence: str
    key_drivers: tuple[str, ...]
    peer_weights: dict[str, float]
    factor_breakdown: dict[str, Any]
    v_candidates: tuple[VCandidate, ...]
    data_stamp_refs: tuple[str, ...]
    coverage_state: CoverageState
    quality_states: tuple[QualityState, ...]
    revision_parent_id: Optional[str] = None
    synthetic: bool = False
    g_horizon: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class TechnicalSnapshot:
    technical_snapshot_id: str
    company_id: str
    as_of: datetime
    technical_version: str
    implementation_kind: str
    regime: TechnicalRegime
    execution_zone: ExecutionZone
    scenarios: tuple[dict[str, Any], ...]
    invalidation: Optional[str]
    drawdown_recheck: bool
    qgv_snapshot_id_ref: Optional[str]
    mutated_qgv: bool = False
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class MacroSnapshot:
    macro_snapshot_id: str
    as_of: datetime
    macro_version: str
    implementation_kind: str
    state: MacroState
    regime: str
    environment: dict[str, Any]
    mutated_qgv: bool = False
    synthetic: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class Holding:
    company_id: str
    ticker: str
    target_weight: float
    shares: Optional[float] = None
    average_cost: Optional[float] = None
    price: Optional[float] = None
    actual_weight: Optional[float] = None
    weight_gap: Optional[float] = None
    qgv_snapshot_id: Optional[str] = None
    ambiguity_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PortfolioSnapshot:
    portfolio_snapshot_id: str
    portfolio_version: str
    snapshot_at: datetime
    base_currency: str
    holdings: tuple[Holding, ...]
    cash_weight: float
    weight_sum: float
    policy_version: str
    implementation_kind: str
    synthetic: bool = False
    role: str = "GENERIC_INPUT"

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class LeaderboardRow:
    rank: int
    company_id: str
    ticker: str
    qgv_snapshot_id: str
    Q_score: Optional[float]
    G_score: Optional[float]
    V_score: Optional[float]
    total_score: Optional[float]
    freshness: str


@dataclass(frozen=True)
class LeaderboardSnapshot:
    leaderboard_snapshot_id: str
    universe_id: str
    generated_at: datetime
    rows: tuple[LeaderboardRow, ...]
    implementation_kind: str
    recomputed_qgv: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass(frozen=True)
class TrackRecord:
    track_record_id: str
    record_type: str
    subject_id: str
    decision_at: datetime
    source_snapshot_refs: tuple[str, ...]
    payload: dict[str, Any]
    outcome_window: Optional[str] = None
    outcome_metrics: Optional[dict[str, Any]] = None
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))


@dataclass
class IntegrationResult:
    as_of: datetime
    gate: GateDecision
    gate_reasons: list[str] = field(default_factory=list)
    target_weights: dict[str, float] = field(default_factory=dict)
    order_intents: list[dict[str, Any]] = field(default_factory=list)
    policy_status: str = "PROVISIONAL"
    qgv_refs: list[str] = field(default_factory=list)
    technical_ref: Optional[str] = None
    macro_ref: Optional[str] = None
    implementation_kind: str = "NEW IMPLEMENTATION"
    profile_id: Optional[str] = None
    parameter_set_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return _to_json(asdict(self))
