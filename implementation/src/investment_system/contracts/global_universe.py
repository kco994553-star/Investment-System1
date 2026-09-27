"""Shared Global/Korea identity and point-in-time context contracts.

This module implements the identity/context boundary frozen in
``Investment-System1 · Global-Korea Universe and Information Source Contract
2026-09-24.md``.  It intentionally contains no provider, ranking, news, RIG,
or portfolio behavior.

Economic identity is hierarchical::

    IssuerIdentity -> SecurityIdentity -> ListingIdentity

A ticker belongs only to a dated listing.  Analysis-universe, network-region,
and news-region scope are independent.  PIT records fail closed when their
evidence was not available by ``as_of``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from .universe import UniversePolicyStatus


class Region(str, Enum):
    US = "US"
    KOREA = "KOREA"
    GLOBAL = "GLOBAL"


def _require_text(field_name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware(field_name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_pit(as_of: datetime, available_at: datetime) -> None:
    _require_aware("as_of", as_of)
    _require_aware("available_at", available_at)
    if available_at > as_of:
        raise ValueError("available_at must be on or before as_of")


def _require_identifiers(identifiers: tuple[tuple[str, str], ...]) -> None:
    seen: set[str] = set()
    for scheme, value in identifiers:
        _require_text("identifier scheme", scheme)
        _require_text("identifier value", value)
        normalized = scheme.strip().upper()
        if normalized in seen:
            raise ValueError(f"duplicate identifier scheme: {normalized}")
        seen.add(normalized)


@dataclass(frozen=True)
class IssuerIdentity:
    """An economic issuer; listing symbols are deliberately not accepted."""

    issuer_id: str
    legal_name: str
    country_code: str
    identifiers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in ("issuer_id", "legal_name", "country_code"):
            _require_text(name, getattr(self, name))
        _require_identifiers(self.identifiers)


@dataclass(frozen=True)
class SecurityIdentity:
    """A security issued by exactly one issuer, independent of its listings."""

    security_id: str
    issuer_id: str
    security_type: str
    share_class: str | None = None
    identifiers: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in ("security_id", "issuer_id", "security_type"):
            _require_text(name, getattr(self, name))
        _require_identifiers(self.identifiers)


@dataclass(frozen=True)
class ListingIdentity:
    """A dated exchange listing.  Ticker is an attribute, never the key."""

    listing_id: str
    security_id: str
    ticker: str
    mic: str
    currency: str
    valid_from: date
    valid_to: date | None = None

    def __post_init__(self) -> None:
        for name in ("listing_id", "security_id", "ticker", "mic", "currency"):
            _require_text(name, getattr(self, name))
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from (exclusive)")

    def active_on(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day < self.valid_to)


@dataclass(frozen=True)
class AnalysisUniverse:
    """Named analysis scope; Korea/Global remain non-Official until promoted."""

    universe_id: str
    region: Region
    policy_status: UniversePolicyStatus
    method: str

    def __post_init__(self) -> None:
        _require_text("universe_id", self.universe_id)
        _require_text("method", self.method)
        if self.region in (Region.KOREA, Region.GLOBAL) and self.policy_status is UniversePolicyStatus.OFFICIAL:
            raise ValueError("Korea/Global universes are not validated for Official promotion")


@dataclass(frozen=True)
class UniverseContext:
    """Independent analysis, graph-discovery, and news scopes at one PIT boundary."""

    analysis_universe: AnalysisUniverse
    network_region: Region
    news_region: Region
    as_of: datetime
    available_at: datetime

    def __post_init__(self) -> None:
        _require_pit(self.as_of, self.available_at)


@dataclass(frozen=True)
class FXSnapshot:
    fx_snapshot_id: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    as_of: datetime
    available_at: datetime
    source: str
    raw_artifact_id: str

    def __post_init__(self) -> None:
        for name in ("fx_snapshot_id", "base_currency", "quote_currency", "source", "raw_artifact_id"):
            _require_text(name, getattr(self, name))
        if self.base_currency.upper() == self.quote_currency.upper():
            raise ValueError("base_currency and quote_currency must differ")
        if not isinstance(self.rate, Decimal) or not self.rate.is_finite() or self.rate <= 0:
            raise ValueError("rate must be a positive finite Decimal")
        _require_pit(self.as_of, self.available_at)

    def convert_base_to_quote(self, amount: Decimal) -> Decimal:
        if not isinstance(amount, Decimal):
            raise TypeError("amount must be Decimal")
        return amount * self.rate


@dataclass(frozen=True)
class EligibilityRecord:
    eligibility_id: str
    listing_id: str
    universe_id: str
    eligible: bool
    as_of: datetime
    available_at: datetime
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("eligibility_id", "listing_id", "universe_id"):
            _require_text(name, getattr(self, name))
        if not self.evidence_ids or any(not x or not x.strip() for x in self.evidence_ids):
            raise ValueError("at least one evidence_id is required")
        if not self.eligible and not self.reason_codes:
            raise ValueError("an ineligible listing requires a reason_code")
        _require_pit(self.as_of, self.available_at)
