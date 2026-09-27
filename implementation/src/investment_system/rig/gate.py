"""RIG P0 lineage index and Update Gate. NEW IMPLEMENTATION.

``Source -> Evidence -> Claim -> NewsEvent/EconomicEvent -> Relationship Candidate
-> Update Gate -> RIG Edge``. The gate never deletes or rewrites a candidate: a
failed candidate is preserved as PENDING (or UNRESOLVED when identity fails),
and it never upgrades a candidate's epistemic status.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from ..contracts.global_universe import IssuerIdentity, ListingIdentity, SecurityIdentity
from .model import (
    SYMMETRIC_TYPES,
    Claim,
    ClaimPolarity,
    EdgeDirection,
    EpistemicStatus,
    Evidence,
    IdentityRef,
    RealWorldEvent,
    RelationshipCandidate,
    RelationshipState,
    SourceKind,
    SourceRef,
    _require_aware,
    stable_id,
)


class LineageError(ValueError):
    """Lineage is missing or structurally incomplete."""


class LineagePITError(LineageError):
    """Lineage is not available at the requested time or is temporally inconsistent."""


class IdentityLookup(Protocol):
    """Read-only view of the upstream (Track A-owned) common identity records."""

    def issuer(self, issuer_id: str) -> IssuerIdentity | None: ...

    def security(self, security_id: str) -> SecurityIdentity | None: ...

    def listing(self, listing_id: str) -> ListingIdentity | None: ...


@dataclass(frozen=True)
class Lineage:
    sources: tuple[SourceRef, ...]
    evidence: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    events: tuple[RealWorldEvent, ...]

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(e.evidence_id for e in self.evidence)


class LineageIndex:
    """Append-only registry of lineage records. Re-adding an id must be identical."""

    def __init__(self) -> None:
        self.sources: dict[str, SourceRef] = {}
        self.evidence: dict[str, Evidence] = {}
        self.claims: dict[str, Claim] = {}
        self.events: dict[str, RealWorldEvent] = {}

    @staticmethod
    def _put(table: dict, key: str, value) -> None:
        if key in table and table[key] != value:
            raise ValueError(f"conflicting record for id {key!r}; lineage is append-only")
        table[key] = value

    def add_source(self, s: SourceRef) -> None:
        self._put(self.sources, s.source_id, s)

    def add_evidence(self, e: Evidence) -> None:
        self._put(self.evidence, e.evidence_id, e)

    def add_claim(self, c: Claim) -> None:
        self._put(self.claims, c.claim_id, c)

    def add_event(self, ev: RealWorldEvent) -> None:
        self._put(self.events, ev.event_id, ev)

    def trace(self, event_ids: tuple[str, ...], as_of: datetime) -> Lineage:
        """Resolve the full chain behind ``event_ids``; fail closed on gaps or look-ahead."""
        _require_aware("as_of", as_of)

        def visible(kind: str, rid: str, table: dict, time_attr: str):
            rec = table.get(rid)
            if rec is None:
                raise LineageError(f"missing {kind} {rid!r}")
            if getattr(rec, time_attr) > as_of:
                raise LineagePITError(f"PIT: {kind} {rid!r} not available at {as_of.isoformat()}")
            return rec

        events, claims, evidence, sources = {}, {}, {}, {}
        for eid in event_ids:
            ev = visible("event", eid, self.events, "available_at")
            events[eid] = ev
            for cid in ev.claim_ids:
                c = visible("claim", cid, self.claims, "available_at")
                if c.available_at > ev.available_at:
                    raise LineagePITError(f"claim {cid!r} available after event {eid!r}")
                claims[cid] = c
                for evid in c.evidence_ids:
                    e = visible("evidence", evid, self.evidence, "available_at")
                    if e.available_at > c.available_at:
                        raise LineagePITError(f"evidence {evid!r} available after claim {cid!r}")
                    evidence[evid] = e
                    s = visible("source", e.source_id, self.sources, "published_at")
                    if e.available_at < s.published_at:
                        raise LineagePITError(f"evidence {evid!r} available before its source was published")
                    sources[s.source_id] = s
        return Lineage(
            tuple(sources[k] for k in sorted(sources)),
            tuple(evidence[k] for k in sorted(evidence)),
            tuple(claims[k] for k in sorted(claims)),
            tuple(events[k] for k in sorted(events)),
        )


class GateCategory(str, Enum):
    IDENTITY = "IDENTITY"
    EVIDENCE = "EVIDENCE"
    TEMPORAL = "TEMPORAL"
    DIRECTION = "DIRECTION"
    DUPLICATE = "DUPLICATE"
    CONTRADICTION = "CONTRADICTION"


class GateOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    PENDING = "PENDING"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class GateCheck:
    category: GateCategory
    passed: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateDecision:
    decision_id: str
    candidate_id: str
    outcome: GateOutcome
    checks: tuple[GateCheck, ...]
    decided_at: datetime
    relationship_key: tuple[str, str, str] | None
    evidence_ids: tuple[str, ...]

    def failed(self) -> tuple[GateCategory, ...]:
        return tuple(c.category for c in self.checks if not c.passed)


FACT_SOURCE_KINDS = frozenset({SourceKind.PRIMARY_DISCLOSURE, SourceKind.NEWS})
NOT_EVALUATED = "NOT_EVALUATED_IDENTITY_UNRESOLVED"


def _identity_reasons(ref: IdentityRef | None, side: str, ids: IdentityLookup) -> list[str]:
    if ref is None:
        return [f"{side}_UNRESOLVED"]
    issuer = ids.issuer(ref.issuer_id)
    if issuer is None:
        return [f"{side}_ISSUER_UNKNOWN"]
    out: list[str] = []
    if ref.security_id is not None:
        if any(value == ref.security_id for _, value in issuer.identifiers):
            out.append(f"{side}_ISSUER_IDENTIFIER_USED_AS_SECURITY")
        sec = ids.security(ref.security_id)
        if sec is None:
            out.append(f"{side}_SECURITY_UNKNOWN")
        elif sec.issuer_id != ref.issuer_id:
            out.append(f"{side}_SECURITY_NOT_OF_ISSUER")
    if ref.listing_id is not None:
        lst = ids.listing(ref.listing_id)
        if lst is None:
            out.append(f"{side}_LISTING_UNKNOWN")
        elif lst.security_id != ref.security_id:
            out.append(f"{side}_LISTING_NOT_OF_SECURITY")
    return out


def effective_interval(cand: RelationshipCandidate, prior: RelationshipState | None):
    """Unknown (None) bounds inherit the prior accepted state: unknown is not 'cleared'."""
    vf = cand.valid_from if cand.valid_from is not None else (prior.valid_from if prior else None)
    vt = cand.valid_to if cand.valid_to is not None else (prior.valid_to if prior else None)
    return vf, vt


def evaluate(
    cand: RelationshipCandidate,
    decided_at: datetime,
    *,
    identity: IdentityLookup,
    lineage: LineageIndex,
    prior_states: tuple[RelationshipState, ...],
    prior_candidates: tuple[RelationshipCandidate, ...],
) -> tuple[GateDecision, Lineage | None]:
    """Run all six gate categories. ``prior_*`` are the history for the candidate's key."""
    _require_aware("decided_at", decided_at)
    if cand.available_at > decided_at:
        raise ValueError("PIT: cannot decide a candidate before it is available")

    ident = _identity_reasons(cand.source_ref, "SOURCE", identity) + _identity_reasons(
        cand.target_ref, "TARGET", identity)
    key = cand.key() if not ident else None

    evidence_r: list[str] = []
    temporal_r: list[str] = []
    contra_r: list[str] = []
    lin: Lineage | None = None
    try:
        lin = lineage.trace(cand.event_ids, decided_at)
    except LineagePITError as exc:
        temporal_r.append(f"LINEAGE_PIT: {exc}")
    except LineageError as exc:
        evidence_r.append(f"LINEAGE_INCOMPLETE: {exc}")
    if cand.epistemic is EpistemicStatus.UNVERIFIED_SIGNAL:
        evidence_r.append("UNVERIFIED_SIGNAL_NOT_EDGE_ELIGIBLE")
    if lin is not None:
        if not lin.evidence:
            evidence_r.append("NO_EVIDENCE")
        latest = max(e.available_at for e in lin.events)
        if cand.available_at < latest:
            temporal_r.append("CANDIDATE_AVAILABLE_BEFORE_ITS_LINEAGE")
        if cand.epistemic is EpistemicStatus.FACT and not any(s.kind in FACT_SOURCE_KINDS for s in lin.sources):
            evidence_r.append("FACT_REQUIRES_PRIMARY_OR_NEWS_SOURCE")
        if any(c.polarity is not cand.polarity for c in lin.claims):
            contra_r.append("LINEAGE_POLARITY_CONFLICT")

    direction_r: list[str] = []
    if cand.source_ref is not None and cand.target_ref is not None and (
            cand.source_ref.issuer_id == cand.target_ref.issuer_id):
        direction_r.append("SELF_RELATIONSHIP")
    expected = (EdgeDirection.UNDIRECTED if cand.relationship_type in SYMMETRIC_TYPES
                else EdgeDirection.UPSTREAM_TO_DOWNSTREAM)
    if cand.direction is not expected:
        direction_r.append(f"{cand.relationship_type.value}_REQUIRES_{expected.value}")

    dup_r: list[str] = []
    if key is None:
        dup_r.append(NOT_EVALUATED)
        contra_r.append(NOT_EVALUATED)
    else:
        prior = prior_states[-1] if prior_states else None
        if prior is not None and prior.available_at > cand.available_at:
            temporal_r.append("OUT_OF_ORDER_OLDER_THAN_LATEST_STATE")
        vf, vt = effective_interval(cand, prior)
        if vf is not None and vt is not None and vt <= vf:
            temporal_r.append("EFFECTIVE_VALID_TO_NOT_AFTER_VALID_FROM")
        if cand.polarity is ClaimPolarity.DENIES:
            contra_r.append("DENIES_EXISTING_RELATIONSHIP" if prior else "DENIAL_NOT_EDGE_ELIGIBLE")
        elif any(p.polarity is ClaimPolarity.DENIES for p in prior_candidates):
            contra_r.append("PRIOR_DENIAL_ON_RECORD")
        if prior is not None and lin is not None:
            same_interval = (vf, vt) == (prior.valid_from, prior.valid_to)
            if prior.epistemic is EpistemicStatus.FACT and cand.epistemic is not EpistemicStatus.FACT:
                if same_interval:
                    dup_r.append("SUBSUMED_BY_EXISTING_FACT")
            elif same_interval and cand.epistemic is prior.epistemic and set(lin.evidence_ids) <= set(
                    prior.evidence_ids):
                dup_r.append("DUPLICATE_NO_NEW_EVIDENCE")

    checks = (
        GateCheck(GateCategory.IDENTITY, not ident, tuple(ident)),
        GateCheck(GateCategory.EVIDENCE, not evidence_r, tuple(evidence_r)),
        GateCheck(GateCategory.TEMPORAL, not temporal_r, tuple(temporal_r)),
        GateCheck(GateCategory.DIRECTION, not direction_r, tuple(direction_r)),
        GateCheck(GateCategory.DUPLICATE, not dup_r, tuple(dup_r)),
        GateCheck(GateCategory.CONTRADICTION, not contra_r, tuple(contra_r)),
    )
    if ident:
        outcome = GateOutcome.UNRESOLVED
    elif all(c.passed for c in checks):
        outcome = GateOutcome.ACCEPTED
    else:
        outcome = GateOutcome.PENDING
    decision = GateDecision(
        stable_id("gdc", cand.candidate_id), cand.candidate_id, outcome, checks, decided_at, key,
        lin.evidence_ids if lin is not None else ())
    return decision, lin
