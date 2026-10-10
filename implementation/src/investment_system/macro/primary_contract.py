"""Private primary-agency evidence sidecars, independent of Macro scoring."""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Literal

AXES = ("Growth", "Inflation", "Liquidity", "Monetary Policy", "Credit", "Labor", "Fiscal", "FX")
DIMENSIONS = ("Level", "Direction", "Momentum", "Surprise", "Stress", "Confidence")
BLS_SERIES = MappingProxyType({
    "CUSR0000SA0": ("Inflation", "index 1982-84=100", "SA"),
    "CUUR0000SA0": ("Inflation", "index 1982-84=100", "NSA"),
    "CES0000000001": ("Labor", "thousands", "SA"),
    "LNS14000000": ("Labor", "percent", "SA"),
})
ENDPOINTS = MappingProxyType({
    "BLS": "https://api.bls.gov/publicAPI/v1/timeseries/data/",
    "BEA": "https://apps.bea.gov/api/data",
    "TREASURY": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml",
})
TREASURY_ID = "TREASURY:daily_treasury_yield_curve:BC_10YEAR"
LEVEL_SOURCES = MappingProxyType({
    "Growth": ("BEA:NIPA:T10106:1:Q",),
    "Inflation": ("BLS:CUSR0000SA0", "BLS:CUUR0000SA0"),
    "Labor": ("BLS:CES0000000001", "BLS:LNS14000000"),
    "Monetary Policy": (TREASURY_ID,),
})
SOURCE_IDS = tuple("BLS:"+s for s in BLS_SERIES) + ("BEA:NIPA:T10106:1:Q", "BEA:NIPA:T10101:1:Q", TREASURY_ID)


@dataclass(frozen=True)
class SourceReceipt:
    provider: Literal["BLS", "BEA", "TREASURY"]
    source_url: str
    response_sha256: str
    acquired_at: datetime
    synthetic: bool
    rights_status: Literal["CLEARED_SCOPE", "UNCONFIRMED"]


@dataclass(frozen=True)
class ReleaseMetadata:
    release_at: datetime | None = None
    release_evidence_ref: str | None = field(default=None, repr=False)
    evidence_kind: Literal["PUBLISHED_ARTIFACT", "SCHEDULE", "UNVERIFIED"] = "UNVERIFIED"
    estimate_kind: Literal["INITIAL", "ADVANCE", "SECOND", "THIRD", "REVISED", "UNKNOWN"] = "UNKNOWN"
    revision_parent: str | None = None


@dataclass(frozen=True)
class MacroObservation:
    observation_id: str
    source_id: str
    axis: str
    observation_period: str
    frequency: str
    unit: str
    seasonal_adjustment: str
    value: Decimal = field(repr=False)
    unit_multiplier: int | None
    metric_name: str | None
    source_series_code: str | None
    source_notes: tuple[str, ...] = field(repr=False)
    source_response_sha256: str
    available_at: datetime
    vintage_at: datetime
    ingested_at: datetime
    release: ReleaseMetadata
    availability_basis: Literal["OBSERVED_CAPTURE_UPPER_BOUND"]
    vintage_kind: Literal["OBSERVED_CAPTURE"]
    synthetic: bool
    quality_flags: tuple[str, ...]


@dataclass(frozen=True)
class ParseResult:
    state: Literal["INPUT_RESEARCH", "NOT_AVAILABLE"]
    observations: tuple[MacroObservation, ...] = field(repr=False)
    reason_codes: tuple[str, ...]
    missing_source_ids: tuple[str, ...]
    synthetic: bool


@dataclass(frozen=True)
class RequestPlan:
    provider: str
    method: str
    endpoint: str
    public_parameters: tuple[tuple[str, str], ...]
    body: bytes | None = field(repr=False)
    credential_slot: Literal["BEA_USERID"] | None
    state: Literal["PLANNED", "NOT_AVAILABLE"]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class MacroCell:
    axis: str
    dimension: str
    state: Literal["RAW_EVIDENCE", "NOT_AVAILABLE"]
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    value: None = None


@dataclass(frozen=True)
class MacroEvidenceGrid:
    contract: Literal["MACRO_PRIMARY_INPUT/1"]
    as_of: datetime
    state: Literal["INPUT_RESEARCH", "NOT_AVAILABLE"]
    cells: tuple[MacroCell, ...]
    observations: tuple[MacroObservation, ...] = field(repr=False)
    pit_status: Literal["OBSERVED_BOUND_ONLY", "NOT_VERIFIED"]
    model_status: Literal["NOT_APPLIED"]
    missing_source_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


def aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def observation_id(source_id: str, period: str, value: Decimal, unit: str,
                   seasonal_adjustment: str, response_sha256: str, acquired_at: datetime) -> str:
    import hashlib
    import json
    fields = dict(source_id=source_id, observation_period=period, value=str(value), unit=unit,
                  seasonal_adjustment=seasonal_adjustment, source_response_sha256=response_sha256,
                  acquired_at=acquired_at.isoformat())
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
