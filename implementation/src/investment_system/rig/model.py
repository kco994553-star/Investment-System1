"""RIG P0 domain records (``RIG_NEWS_ARCH_v0.1``). NEW IMPLEMENTATION.

Consumers of the common C-39 identity contract only: every company reference is
an ``IdentityRef`` into ``IssuerIdentity -> SecurityIdentity -> ListingIdentity``.
There is deliberately no ticker/CIK field and no RIG-owned identity universe.

Time semantics (never mixed):

- ``valid_from`` / ``valid_to``: real-world business validity (dates, ``valid_to`` exclusive).
- ``available_at``: when the information became publicly available (PIT knowledge time).
- ``first_detected_at``: ``available_at`` of the earliest accepted assertion of a relationship.
- ``last_confirmed_at``: ``available_at`` of the latest evidence confirming it.
- ``decided_at`` (gate only): system processing time; never used for PIT visibility.

``NewsEvent`` / ``EconomicEvent`` are real-world events. They are not ``DataEvent``
and connect to the incremental pipeline only through ``rig.adapter``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


def _require_text(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware(field_name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware datetime")


def _require_ids(field_name: str, values: tuple[str, ...]) -> None:
    if not isinstance(values, tuple) or not values:
        raise ValueError(f"{field_name} requires at least one id")
    for v in values:
        _require_text(field_name, v)
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} contains duplicates")


def _require_validity(valid_from: date | None, valid_to: date | None) -> None:
    for name, v in (("valid_from", valid_from), ("valid_to", valid_to)):
        if v is not None and (not isinstance(v, date) or isinstance(v, datetime)):
            raise ValueError(f"{name} must be a date")
    if valid_from is not None and valid_to is not None and valid_to <= valid_from:
        raise ValueError("valid_to must be after valid_from (exclusive)")


def stable_id(prefix: str, *parts: str) -> str:
    """Deterministic content id: same inputs, same id, independent of process/order."""
    digest = hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:16]}"


class SourceKind(str, Enum):
    PRIMARY_DISCLOSURE = "PRIMARY_DISCLOSURE"  # issuer / regulator / exchange
    NEWS = "NEWS"
    COMMUNITY = "COMMUNITY"
    OTHER = "OTHER"


class EpistemicStatus(str, Enum):
    FACT = "FACT"
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"
    UNVERIFIED_SIGNAL = "UNVERIFIED_SIGNAL"


class EconomicEventKind(str, Enum):
    CONTRACT = "CONTRACT"
    CUSTOMER_WIN = "CUSTOMER_WIN"
    CUSTOMER_LOSS = "CUSTOMER_LOSS"
    SUPPLIER_CHANGE = "SUPPLIER_CHANGE"
    PARTNERSHIP = "PARTNERSHIP"
    INVESTMENT = "INVESTMENT"
    CAPACITY_EXPANSION = "CAPACITY_EXPANSION"
    REGULATORY_ACTION = "REGULATORY_ACTION"


class RelationshipType(str, Enum):
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    CUSTOMER = "CUSTOMER"
    COMPETITOR = "COMPETITOR"
    VALUE_CHAIN = "VALUE_CHAIN"


SYMMETRIC_TYPES = frozenset({RelationshipType.COMPETITOR})


class EdgeDirection(str, Enum):
    UPSTREAM_TO_DOWNSTREAM = "UPSTREAM_TO_DOWNSTREAM"
    UNDIRECTED = "UNDIRECTED"
    UNKNOWN = "UNKNOWN"


class ClaimPolarity(str, Enum):
    AFFIRMS = "AFFIRMS"
    DENIES = "DENIES"


@dataclass(frozen=True)
class IdentityRef:
    """Reference into the common C-39 hierarchy. The issuer is the graph key."""

    issuer_id: str
    security_id: str | None = None
    listing_id: str | None = None

    def __post_init__(self) -> None:
        _require_text("issuer_id", self.issuer_id)
        for name in ("security_id", "listing_id"):
            v = getattr(self, name)
            if v is not None:
                _require_text(name, v)
        if self.listing_id is not None and self.security_id is None:
            raise ValueError("listing_id requires security_id (Issuer -> Security -> Listing)")


@dataclass(frozen=True)
class Node:
    node_id: str
    issuer_id: str

    @classmethod
    def for_issuer(cls, issuer_id: str) -> "Node":
        _require_text("issuer_id", issuer_id)
        return cls(f"issuer:{issuer_id}", issuer_id)


@dataclass(frozen=True)
class SourceRef:
    """Where evidence came from; ``raw_artifact_id`` links to raw store provenance."""

    source_id: str
    kind: SourceKind
    publisher: str
    published_at: datetime
    raw_artifact_id: str

    def __post_init__(self) -> None:
        for name in ("source_id", "publisher", "raw_artifact_id"):
            _require_text(name, getattr(self, name))
        _require_aware("published_at", self.published_at)


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_id: str
    locator: str
    available_at: datetime

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_id", "locator"):
            _require_text(name, getattr(self, name))
        _require_aware("available_at", self.available_at)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    evidence_ids: tuple[str, ...]
    statement: str
    polarity: ClaimPolarity
    available_at: datetime

    def __post_init__(self) -> None:
        _require_text("claim_id", self.claim_id)
        _require_text("statement", self.statement)
        _require_ids("evidence_ids", self.evidence_ids)
        _require_aware("available_at", self.available_at)


@dataclass(frozen=True)
class _RealWorldEvent:
    event_id: str
    kind: EconomicEventKind
    claim_ids: tuple[str, ...]
    available_at: datetime
    occurred_on: date | None = None  # None = real-world date unknown

    def __post_init__(self) -> None:
        _require_text("event_id", self.event_id)
        if not isinstance(self.kind, EconomicEventKind):
            raise ValueError("kind must be an EconomicEventKind")
        _require_ids("claim_ids", self.claim_ids)
        _require_aware("available_at", self.available_at)
        _require_validity(self.occurred_on, None)


@dataclass(frozen=True)
class NewsEvent(_RealWorldEvent):
    """Real-world event first surfaced through news reporting."""


@dataclass(frozen=True)
class EconomicEvent(_RealWorldEvent):
    """Real-world event established from issuer/regulator/exchange disclosure."""


RealWorldEvent = NewsEvent | EconomicEvent


def relationship_key(rtype: RelationshipType, source_issuer_id: str, target_issuer_id: str) -> tuple[str, str, str]:
    if rtype in SYMMETRIC_TYPES:
        a, b = sorted((source_issuer_id, target_issuer_id))
        return rtype.value, a, b
    return rtype.value, source_issuer_id, target_issuer_id


@dataclass(frozen=True)
class RelationshipCandidate:
    """Unaccepted assertion. Identity refs may be missing (unresolved mention)."""

    candidate_id: str
    relationship_type: RelationshipType
    direction: EdgeDirection
    polarity: ClaimPolarity
    epistemic: EpistemicStatus
    source_mention: str
    target_mention: str
    source_ref: IdentityRef | None
    target_ref: IdentityRef | None
    event_ids: tuple[str, ...]
    available_at: datetime
    confidence: Decimal
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        for name in ("candidate_id", "source_mention", "target_mention"):
            _require_text(name, getattr(self, name))
        _require_ids("event_ids", self.event_ids)
        _require_aware("available_at", self.available_at)
        _require_validity(self.valid_from, self.valid_to)
        if not isinstance(self.confidence, Decimal) or not self.confidence.is_finite() or not (
            Decimal(0) <= self.confidence <= Decimal(1)
        ):
            raise ValueError("confidence must be a Decimal in [0, 1]")

    def key(self) -> tuple[str, str, str] | None:
        if self.source_ref is None or self.target_ref is None:
            return None
        return relationship_key(self.relationship_type, self.source_ref.issuer_id, self.target_ref.issuer_id)


@dataclass(frozen=True)
class Relationship:
    """Time-invariant relationship identity; its history lives in ``RelationshipState``."""

    relationship_id: str
    relationship_type: RelationshipType
    source_node_id: str
    target_node_id: str

    @classmethod
    def for_key(cls, key: tuple[str, str, str]) -> "Relationship":
        rtype, src, tgt = key
        return cls(stable_id("rel", *key), RelationshipType(rtype),
                   Node.for_issuer(src).node_id, Node.for_issuer(tgt).node_id)


@dataclass(frozen=True)
class RelationshipState:
    """One accepted, append-only bitemporal version of a relationship."""

    state_id: str
    relationship_id: str
    epistemic: EpistemicStatus
    valid_from: date | None
    valid_to: date | None
    available_at: datetime
    first_detected_at: datetime
    last_confirmed_at: datetime
    evidence_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    decision_id: str
    confidence: Decimal

    def __post_init__(self) -> None:
        for name in ("state_id", "relationship_id", "decision_id"):
            _require_text(name, getattr(self, name))
        if self.epistemic is EpistemicStatus.UNVERIFIED_SIGNAL:
            raise ValueError("UNVERIFIED_SIGNAL is never an accepted relationship state")
        _require_validity(self.valid_from, self.valid_to)
        for name in ("available_at", "first_detected_at", "last_confirmed_at"):
            _require_aware(name, getattr(self, name))
        if not (self.first_detected_at <= self.last_confirmed_at <= self.available_at):
            raise ValueError("require first_detected_at <= last_confirmed_at <= available_at")
        _require_ids("evidence_ids", self.evidence_ids)
        _require_ids("candidate_ids", self.candidate_ids)

    def valid_on(self, day: date) -> bool:
        # Unknown start: only known-valid from the day the information became available.
        start = self.valid_from if self.valid_from is not None else self.available_at.date()
        return start <= day and (self.valid_to is None or day < self.valid_to)


@dataclass(frozen=True)
class Edge:
    """PIT projection of one relationship state onto a graph as of ``graph_as_of``."""

    relationship: Relationship
    state: RelationshipState
    graph_as_of: datetime

    def __post_init__(self) -> None:
        _require_aware("graph_as_of", self.graph_as_of)
        if self.state.available_at > self.graph_as_of:
            raise ValueError("PIT violation: state available_at is after graph_as_of")
        if self.state.relationship_id != self.relationship.relationship_id:
            raise ValueError("state does not belong to relationship")

    @property
    def epistemic(self) -> EpistemicStatus:
        return self.state.epistemic
