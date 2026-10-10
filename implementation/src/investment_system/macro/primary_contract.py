"""Immutable offline primary-source evidence contract; no macro model rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from types import MappingProxyType
from typing import Literal

AXES = ("Growth", "Inflation", "Liquidity", "Monetary Policy", "Credit", "Labor", "Fiscal", "FX")
DIMENSIONS = ("Level", "Direction", "Momentum", "Surprise", "Stress", "Confidence")
ENDPOINTS = MappingProxyType({
    "BLS": "https://api.bls.gov/publicAPI/v1/timeseries/data/",
    "BEA": "https://apps.bea.gov/api/data",
    "TREASURY": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml",
})
BLS_SERIES_IDS = ("CUSR0000SA0", "CUUR0000SA0", "CES0000000001", "LNS14000000")
BEA_TABLES = ("T10106", "T10101")
TREASURY_SOURCE = "TREASURY:daily_treasury_yield_curve:BC_10YEAR"


@dataclass(frozen=True)
class SourceDefinition:
    provider: str
    axis: str
    frequency: str
    unit: str | None
    seasonal_adjustment: str
    quality_flags: tuple[str, ...]


SOURCE_REGISTRY = MappingProxyType({
    "BLS:CUSR0000SA0": SourceDefinition("BLS", "Inflation", "M", "index 1982-84=100", "SA", ("CURRENT_REVISED_HISTORY", "CPI_SA_FIVE_YEAR_RECALCULATION")),
    "BLS:CUUR0000SA0": SourceDefinition("BLS", "Inflation", "M", "index 1982-84=100", "NSA", ("CURRENT_REVISED_HISTORY",)),
    "BLS:CES0000000001": SourceDefinition("BLS", "Labor", "M", "thousands", "SA", ("CURRENT_REVISED_HISTORY", "CES_REVISION_AND_BENCHMARK")),
    "BLS:LNS14000000": SourceDefinition("BLS", "Labor", "M", "percent", "SA", ("CURRENT_REVISED_HISTORY", "CPS_REVISION")),
    "BEA:NIPA:T10106:1:Q": SourceDefinition("BEA", "Growth", "Q", None, "SAAR", ("CURRENT_REVISED_HISTORY", "GDP_ESTIMATES_AND_ANNUAL_REVISIONS")),
    "BEA:NIPA:T10101:1:Q": SourceDefinition("BEA", "Growth", "Q", None, "SAAR", ("CURRENT_REVISED_HISTORY", "GDP_ESTIMATES_AND_ANNUAL_REVISIONS", "PUBLISHED_ANNUALIZED_CHANGE")),
    TREASURY_SOURCE: SourceDefinition("TREASURY", "Monetary Policy", "D", "percent", "NOT_APPLICABLE", ("CURRENT_REVISED_HISTORY", "TREASURY_CORRECTION_AND_BACKFILL", "YIELD_CONTEXT_NOT_POLICY_TARGET")),
})
SOURCE_IDS = tuple(SOURCE_REGISTRY)
LEVEL_REQUIRED = MappingProxyType({
    "Growth": ("BEA:NIPA:T10106:1:Q",),
    "Inflation": ("BLS:CUSR0000SA0", "BLS:CUUR0000SA0"),
    "Labor": ("BLS:CES0000000001", "BLS:LNS14000000"),
    "Monetary Policy": (TREASURY_SOURCE,),
})

# Diagnostic vocabulary, in validation precedence; no raw provider messages.
REASON_CODES = (
    "INVALID_REQUEST", "INVALID_RECEIPT", "INVALID_TIMESTAMP", "INVALID_TIME_ORDER",
    "RIGHTS_UNCONFIRMED", "PROVIDER_ERROR", "UNSAFE_XML", "SCHEMA_MISMATCH", "INVALID_VALUE",
    "CONFLICTING_DUPLICATE", "CONFLICTING_VINTAGE", "OBSERVATION_ID_COLLISION",
    "MIXED_SYNTHETIC_INPUT", "RELEASE_EVIDENCE_UNCONFIRMED", "AVAILABLE_AFTER_AS_OF",
    "HISTORICAL_VINTAGE_NOT_PROVEN", "MISSING_SOURCE", "ANNUAL_AVERAGE_EXCLUDED",
    "NO_APPROVED_STATE_RULE", "EXPECTATIONS_NOT_CONFIGURED", "NO_APPROVED_CONFIDENCE_RULE",
    "DEFERRED_GSQ011", "KEY_NOT_CONFIGURED",
)


@dataclass(frozen=True)
class SourceReceipt:
    provider: Literal["BLS", "BEA", "TREASURY"]
    source_url: str = field(repr=False)
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
    revision_parent: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class MacroObservation:
    observation_id: str
    source_id: str
    axis: str
    observation_period: str
    frequency: str
    unit: str = field(repr=False)
    seasonal_adjustment: str
    value: Decimal = field(repr=False)
    unit_multiplier: int | None
    metric_name: str | None = field(repr=False)
    source_series_code: str | None = field(repr=False)
    source_notes: tuple[str, ...] = field(repr=False)
    source_response_sha256: str
    available_at: datetime
    vintage_at: datetime
    ingested_at: datetime
    release: ReleaseMetadata = field(repr=False)
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


def nonempty(value: object) -> bool:
    return type(value) is str and bool(value.strip())


def aware(value: object) -> bool:
    if not isinstance(value, datetime):
        return False
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            return False
        value.astimezone(timezone.utc)
        return True
    except (ValueError, TypeError, OverflowError):
        return False


def valid_hash(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def utc(value: datetime) -> datetime:
    """Compare actual instants, including ambiguous local DST fold times."""
    return value.astimezone(timezone.utc)


def ordered_reasons(reasons) -> tuple[str, ...]:
    return tuple(reason for reason in REASON_CODES if reason in reasons)


def observation_id(source_id: str, period: str, value: Decimal, unit: str,
                   seasonal: str, response_hash: str, acquired_at: datetime) -> str:
    """Bind source, exact Decimal representation and capture, never input position."""
    canonical = {"source_id": source_id, "observation_period": period, "value": str(value),
                 "unit": unit, "seasonal_adjustment": seasonal, "source_response_sha256": response_hash,
                 "acquired_at": acquired_at.astimezone(timezone.utc).isoformat()}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def release_error(release: object, acquired_at: datetime) -> str | None:
    if not isinstance(release, ReleaseMetadata):
        return "RELEASE_EVIDENCE_UNCONFIRMED"
    if (release.evidence_kind not in ("PUBLISHED_ARTIFACT", "SCHEDULE", "UNVERIFIED")
            or release.estimate_kind not in ("INITIAL", "ADVANCE", "SECOND", "THIRD", "REVISED", "UNKNOWN")
            or (release.revision_parent is not None and not nonempty(release.revision_parent))):
        return "RELEASE_EVIDENCE_UNCONFIRMED"
    if release == ReleaseMetadata():
        return None
    if release.release_at is not None and not aware(release.release_at):
        return "INVALID_TIMESTAMP"
    if release.release_at is not None and utc(release.release_at) > utc(acquired_at):
        return "INVALID_TIME_ORDER"
    if (release.evidence_kind != "PUBLISHED_ARTIFACT" or release.release_at is None
            or not nonempty(release.release_evidence_ref)):
        return "RELEASE_EVIDENCE_UNCONFIRMED"
    return None


def make_result(observations=(), reasons=(), expected=(), *, synthetic=True) -> ParseResult:
    observations = tuple(observations)
    present = {o.source_id for o in observations}
    missing = tuple(s for s in SOURCE_IDS if s in expected and s not in present)
    return ParseResult("INPUT_RESEARCH" if observations else "NOT_AVAILABLE", observations,
                       ordered_reasons(reasons), missing, synthetic)
