"""RIG P2 Relationship Intelligence. NEW IMPLEMENTATION.

Relationship status (NEW / DISCOVERED / STRENGTHENED / STABLE / WEAKENED / ENDED),
materiality, Deal state and timeline, all derived point-in-time from P0 relationship
states plus append-only, evidence-linked observations. Relationship state and Deal
state are separate: a Deal never creates, confirms or removes a relationship edge.
Nothing here is an investment score.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..gate import IdentityLookup, LineageIndex
from ..ledger import RelationshipLedger
from ..model import (
    IdentityRef,
    Relationship,
    RelationshipState,
    RelationshipType,
    _require_aware,
    _require_ids,
    _require_text,
    relationship_key,
)

RECENT_WINDOW = timedelta(days=30)


class Materiality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        return ("LOW", "MEDIUM", "HIGH", "CRITICAL").index(self.value)


class RelationshipStatus(str, Enum):
    NEW = "NEW"
    DISCOVERED = "DISCOVERED"
    STRENGTHENED = "STRENGTHENED"
    STABLE = "STABLE"
    WEAKENED = "WEAKENED"
    ENDED = "ENDED"


class DealState(str, Enum):
    RUMORED = "RUMORED"
    EXPECTED = "EXPECTED"
    NEGOTIATING = "NEGOTIATING"
    ANNOUNCED = "ANNOUNCED"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    EXPANDED = "EXPANDED"
    RENEWED = "RENEWED"
    REDUCED = "REDUCED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


PRE_ACTIVE = (DealState.RUMORED, DealState.EXPECTED, DealState.NEGOTIATING, DealState.ANNOUNCED,
              DealState.CONFIRMED, DealState.ACTIVE)
POST_ACTIVE = frozenset({DealState.EXPANDED, DealState.RENEWED, DealState.REDUCED})
TERMINAL = frozenset({DealState.CANCELLED, DealState.EXPIRED})
LIVE = frozenset({DealState.ACTIVE}) | POST_ACTIVE


class DealPhrase(str, Enum):
    """Card wording for a deal: expected vs confirmed. Not a relationship fact."""

    DEAL_EXPECTED = "DEAL_EXPECTED"
    DEAL_ANNOUNCED = "DEAL_ANNOUNCED"
    DEAL_CONFIRMED = "DEAL_CONFIRMED"
    DEAL_ENDED = "DEAL_ENDED"


def deal_phrase(state: DealState) -> DealPhrase:
    if state in (DealState.RUMORED, DealState.EXPECTED, DealState.NEGOTIATING):
        return DealPhrase.DEAL_EXPECTED
    if state is DealState.ANNOUNCED:
        return DealPhrase.DEAL_ANNOUNCED
    if state in TERMINAL:
        return DealPhrase.DEAL_ENDED
    return DealPhrase.DEAL_CONFIRMED


def transition_error(prev: DealState | None, new: DealState) -> str | None:
    if prev is None:
        if new in POST_ACTIVE or new is DealState.EXPIRED:
            return "POST_ACTIVE_STATE_WITHOUT_ACTIVE"
        return None
    if prev in TERMINAL:
        return "DEAL_ALREADY_TERMINAL"
    if new is DealState.CANCELLED:
        return None
    if new is DealState.EXPIRED:
        return None if prev in LIVE else "EXPIRED_REQUIRES_ACTIVE"
    if new in POST_ACTIVE:
        return None if prev in LIVE else "POST_ACTIVE_STATE_WITHOUT_ACTIVE"
    if prev in POST_ACTIVE:
        return "BACKWARD_TRANSITION"
    if PRE_ACTIVE.index(new) <= PRE_ACTIVE.index(prev):
        return "BACKWARD_OR_REPEATED_TRANSITION"
    return None


@dataclass(frozen=True)
class MaterialityObservation:
    obs_id: str
    relationship_id: str
    level: Materiality
    available_at: datetime
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text("obs_id", self.obs_id)
        _require_text("relationship_id", self.relationship_id)
        _require_aware("available_at", self.available_at)
        _require_ids("evidence_ids", self.evidence_ids)


@dataclass(frozen=True)
class DealObservation:
    obs_id: str
    deal_id: str
    relationship_type: RelationshipType
    seller: IdentityRef  # upstream party
    buyer: IdentityRef  # downstream party
    state: DealState
    available_at: datetime
    evidence_ids: tuple[str, ...]
    event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("obs_id", "deal_id"):
            _require_text(name, getattr(self, name))
        _require_aware("available_at", self.available_at)
        _require_ids("evidence_ids", self.evidence_ids)
        if self.event_ids:
            _require_ids("event_ids", self.event_ids)

    @property
    def relationship_id(self) -> str:
        key = relationship_key(self.relationship_type, self.seller.issuer_id, self.buyer.issuer_id)
        return Relationship.for_key(key).relationship_id


@dataclass(frozen=True)
class Rejected:
    record: object
    reasons: tuple[str, ...]


class IntelIndex:
    """Append-only P2 observations; invalid input is kept in ``rejected`` with reasons."""

    def __init__(self, ledger: RelationshipLedger) -> None:
        self.ledger = ledger
        self.lineage: LineageIndex = ledger.lineage
        self.identity: IdentityLookup = ledger.identity
        self.materiality: list[MaterialityObservation] = []
        self.deals: list[DealObservation] = []
        self.rejected: list[Rejected] = []
        self._ids: set[str] = set()

    def _evidence_reasons(self, evidence_ids, event_ids, at: datetime) -> list[str]:
        out = []
        for eid in evidence_ids:
            e = self.lineage.evidence.get(eid)
            if e is None:
                out.append(f"EVIDENCE_UNKNOWN:{eid}")
            elif e.available_at > at:
                out.append(f"PIT_EVIDENCE_AFTER_OBSERVATION:{eid}")
        for vid in event_ids:
            v = self.lineage.events.get(vid)
            if v is None:
                out.append(f"EVENT_UNKNOWN:{vid}")
            elif v.available_at > at:
                out.append(f"PIT_EVENT_AFTER_OBSERVATION:{vid}")
        return out

    def _finish(self, rec, reasons: list[str], store: list) -> bool:
        if rec.obs_id in self._ids:
            raise ValueError(f"observation {rec.obs_id!r} already recorded; append-only")
        self._ids.add(rec.obs_id)
        if reasons:
            self.rejected.append(Rejected(rec, tuple(reasons)))
            return False
        store.append(rec)
        return True

    def add_materiality(self, obs: MaterialityObservation) -> bool:
        reasons = self._evidence_reasons(obs.evidence_ids, (), obs.available_at)
        if obs.relationship_id not in {r.relationship_id for r in self.ledger.relationships.values()}:
            reasons.append("RELATIONSHIP_NOT_ACCEPTED")
        prior = [m for m in self.materiality if m.relationship_id == obs.relationship_id]
        if prior and prior[-1].available_at > obs.available_at:
            reasons.append("OUT_OF_ORDER")
        return self._finish(obs, reasons, self.materiality)

    def add_deal(self, obs: DealObservation) -> bool:
        reasons = self._evidence_reasons(obs.evidence_ids, obs.event_ids, obs.available_at)
        for side, ref in (("SELLER", obs.seller), ("BUYER", obs.buyer)):
            if self.identity.issuer(ref.issuer_id) is None:
                reasons.append(f"{side}_ISSUER_UNKNOWN")
        if obs.seller.issuer_id == obs.buyer.issuer_id:
            reasons.append("SELF_DEAL")
        prior = [d for d in self.deals if d.deal_id == obs.deal_id]
        if prior:
            last = prior[-1]
            if (last.relationship_type, last.seller, last.buyer) != (obs.relationship_type, obs.seller, obs.buyer):
                reasons.append("DEAL_PARTIES_CHANGED")
            if last.available_at > obs.available_at:
                reasons.append("OUT_OF_ORDER")
        err = transition_error(prior[-1].state if prior else None, obs.state)
        if err:
            reasons.append(err)
        return self._finish(obs, reasons, self.deals)

    # ---- point-in-time reads -------------------------------------------------

    def materiality_as_of(self, relationship_id: str, as_of: datetime) -> Materiality | None:
        known = [m for m in self.materiality if m.relationship_id == relationship_id and m.available_at <= as_of]
        return known[-1].level if known else None

    def deal_states_as_of(self, as_of: datetime) -> dict[str, DealObservation]:
        out: dict[str, DealObservation] = {}
        for d in self.deals:
            if d.available_at <= as_of:
                out[d.deal_id] = d
        return out

    def _states(self, relationship_id: str, as_of: datetime) -> list[RelationshipState]:
        for key, rel in self.ledger.relationships.items():
            if rel.relationship_id == relationship_id:
                return [s for s in self.ledger.states[key] if s.available_at <= as_of]
        return []

    def status(self, relationship_id: str, as_of: datetime, window: timedelta = RECENT_WINDOW
               ) -> RelationshipStatus | None:
        _require_aware("as_of", as_of)
        states = self._states(relationship_id, as_of)
        if not states:
            return None
        latest = states[-1]
        if latest.valid_to is not None and latest.valid_to <= as_of.date():
            return RelationshipStatus.ENDED
        since = as_of - window
        if latest.first_detected_at >= since:
            started = latest.valid_from
            real_start = started is not None and started >= (latest.first_detected_at - window).date()
            return RelationshipStatus.NEW if real_start else RelationshipStatus.DISCOVERED
        signals: list[tuple[datetime, int]] = []  # (+1 strengthen / -1 weaken, at)
        mats = [m for m in self.materiality if m.relationship_id == relationship_id and m.available_at <= as_of]
        for prev, cur in zip(mats, mats[1:]):
            if cur.available_at >= since and cur.level.rank != prev.level.rank:
                signals.append((cur.available_at, 1 if cur.level.rank > prev.level.rank else -1))
        was_live: set[str] = set()
        for d in self.deals:  # stored in available_at order per deal
            if d.relationship_id != relationship_id or d.available_at > as_of:
                continue
            if since <= d.available_at:
                if d.state in (DealState.EXPANDED, DealState.RENEWED):
                    signals.append((d.available_at, 1))
                elif d.state is DealState.REDUCED or (d.state in TERMINAL and d.deal_id in was_live):
                    signals.append((d.available_at, -1))  # ending a never-live rumor does not weaken
            if d.state in LIVE:
                was_live.add(d.deal_id)
        if not signals:
            return RelationshipStatus.STABLE
        return RelationshipStatus.STRENGTHENED if max(signals)[1] > 0 else RelationshipStatus.WEAKENED

    def timeline(self, relationship_id: str, as_of: datetime) -> tuple["TimelineEntry", ...]:
        _require_aware("as_of", as_of)
        rows = [TimelineEntry(s.available_at, "STATE", s.epistemic.value, s.state_id,
                              s.valid_from.isoformat() if s.valid_from else None,
                              s.valid_to.isoformat() if s.valid_to else None)
                for s in self._states(relationship_id, as_of)]
        rows += [TimelineEntry(m.available_at, "MATERIALITY", m.level.value, m.obs_id, None, None)
                 for m in self.materiality if m.relationship_id == relationship_id and m.available_at <= as_of]
        rows += [TimelineEntry(d.available_at, "DEAL", d.state.value, d.obs_id, d.deal_id, None)
                 for d in self.deals if d.relationship_id == relationship_id and d.available_at <= as_of]
        return tuple(sorted(rows, key=lambda r: (r.at, r.kind, r.ref_id)))


@dataclass(frozen=True)
class TimelineEntry:
    at: datetime
    kind: str  # STATE | MATERIALITY | DEAL
    value: str
    ref_id: str
    detail_a: str | None
    detail_b: str | None
