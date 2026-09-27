"""P2 presentation: edge badges/width, card badges and expansion priority. NEW IMPLEMENTATION.

Consumes P1 through its public extension points (``PageExtras`` and the ``priority``
hook); P1 modules are not modified by this layer.
"""

from __future__ import annotations

from datetime import datetime

from ..network.render import PageExtras
from ..network.views import NetEdge, RIGViewModel, edge_priority
from .intel import IntelIndex, Materiality, RelationshipStatus, deal_phrase

EDGE_WIDTH = {Materiality.LOW: 1.0, Materiality.MEDIUM: 2.0, Materiality.HIGH: 3.5, Materiality.CRITICAL: 5.0}

TERMS_P2: dict[str, tuple[str, str]] = {
    "DISCOVERED": ("Discovered", "발견"),
    "STRENGTHENED": ("↑ Strengthened", "↑강화"),
    "WEAKENED": ("↓ Weakened", "↓약화"),
    "STABLE": ("Stable", "유지"),
    "ENDED": ("Ended", "종료"),
    "DEAL_EXPECTED": ("Expected", "예상"),
    "DEAL_ANNOUNCED": ("Announced", "발표"),
    "DEAL_CONFIRMED": ("✓ Confirmed", "✓확정"),
    "DEAL_ENDED": ("Deal ended", "계약 종료"),
    "IMP_CRITICAL": ("Materiality: Critical", "중요도: 매우 높음"),
    "IMP_HIGH": ("Materiality: High", "중요도: 높음"),
    "IMP_MEDIUM": ("Materiality: Medium", "중요도: 보통"),
    "IMP_LOW": ("Materiality: Low", "중요도: 낮음"),
}

_CHANGE = frozenset({RelationshipStatus.NEW, RelationshipStatus.DISCOVERED, RelationshipStatus.STRENGTHENED,
                     RelationshipStatus.WEAKENED})


def _latest_deal(intel: IntelIndex, relationship_id: str, as_of: datetime):
    ds = [d for d in intel.deal_states_as_of(as_of).values() if d.relationship_id == relationship_id]
    return max(ds, key=lambda d: (d.available_at, d.obs_id)) if ds else None


def intel_rank(intel: IntelIndex, relationship_id: str, as_of: datetime) -> tuple[int, int]:
    """(materiality slot, recent-change slot): Critical → High → Recent Change → rest."""
    m = intel.materiality_as_of(relationship_id, as_of)
    slot = 0 if m is Materiality.CRITICAL else 1 if m is Materiality.HIGH else 2
    return slot, 0 if intel.status(relationship_id, as_of) in _CHANGE else 1


def intel_priority(intel: IntelIndex, as_of: datetime):
    def key(e: NetEdge) -> tuple:
        return intel_rank(intel, e.relationship_id, as_of) + edge_priority(e)
    return key


def edge_badges(intel: IntelIndex, relationship_id: str, as_of: datetime) -> tuple[str, ...]:
    out: list[str] = []
    st = intel.status(relationship_id, as_of)
    if st is not None and st is not RelationshipStatus.STABLE:
        out.append(st.value)
    d = _latest_deal(intel, relationship_id, as_of)
    if d is not None:
        out.append(deal_phrase(d.state).value)
    return tuple(out[:2])


def intel_extras(intel: IntelIndex, vm: RIGViewModel) -> PageExtras:
    as_of = vm.graph_as_of
    e_badges, widths = {}, {}
    for e in vm.network.edges:
        e_badges[e.relationship_id] = edge_badges(intel, e.relationship_id, as_of)
        m = intel.materiality_as_of(e.relationship_id, as_of)
        if m is not None:
            widths[e.relationship_id] = EDGE_WIDTH[m]
    deal_by_event: dict[str, str] = {}
    for d in intel.deals:
        if d.available_at <= as_of:
            for ev in d.event_ids:
                deal_by_event[ev] = deal_phrase(d.state).value
    c_badges = {}
    for c in vm.cards:
        b: list[str] = []
        if c.event_id in deal_by_event:
            b.append(deal_by_event[c.event_id])
        statuses = {intel.status(r, as_of) for r in c.relationship_ids}
        for st in (RelationshipStatus.STRENGTHENED, RelationshipStatus.WEAKENED):
            if st in statuses:
                b.append(st.value)
        mats = [m for m in (intel.materiality_as_of(r, as_of) for r in c.relationship_ids) if m is not None]
        if mats:
            b.append("IMP_" + max(mats, key=lambda m: m.rank).value)
        if b:
            c_badges[c.event_id] = tuple(b)
    return PageExtras(card_badges=c_badges, edge_badges=e_badges, edge_width=widths, terms=dict(TERMS_P2))
