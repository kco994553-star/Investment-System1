"""RIG P1 Basic Network: one view model, two views (News | Network). NEW IMPLEMENTATION.

Same Information, Two Views: News cards and Network nodes/edges are projections of
the same P0 ``RIGGraph`` (same event / relationship / node ids). Only transient
viewport state differs between the views; switching views keeps scope, filters,
focus and viewport. Nothing here scores, ranks for investment, or writes back.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from ..gate import IdentityLookup, LineageError, LineageIndex
from ..ledger import RelationshipLedger, RIGGraph
from ..model import SYMMETRIC_TYPES, Edge, EpistemicStatus, RelationshipType, _require_aware, _require_text

FOCUS_MIN, FOCUS_MAX = 5, 8
OVERVIEW_MAX_EDGES = 60
CANVAS = 1000.0


class NewsStatus(str, Enum):
    NEW = "NEW"
    UPDATE = "UPDATE"
    FOLLOW_UP = "FOLLOW_UP"
    DUPLICATE = "DUPLICATE"


class ViewKind(str, Enum):
    NEWS = "NEWS"
    NETWORK = "NETWORK"


@dataclass(frozen=True)
class EventLink:
    """How a later event relates to an earlier one (absence of a link = NEW)."""

    event_id: str
    parent_event_id: str
    status: NewsStatus
    available_at: datetime

    def __post_init__(self) -> None:
        _require_text("event_id", self.event_id)
        _require_text("parent_event_id", self.parent_event_id)
        if self.status is NewsStatus.NEW:
            raise ValueError("NEW is the absence of a link")
        if self.event_id == self.parent_event_id:
            raise ValueError("an event cannot link to itself")
        _require_aware("available_at", self.available_at)


@dataclass(frozen=True)
class EventPresentation:
    event_id: str
    headline: str
    summary: tuple[str, ...]
    available_at: datetime

    def __post_init__(self) -> None:
        _require_text("event_id", self.event_id)
        _require_text("headline", self.headline)
        if not isinstance(self.summary, tuple) or not 1 <= len(self.summary) <= 3:
            raise ValueError("summary must be 1-3 lines")
        for line in self.summary:
            _require_text("summary line", line)
        _require_aware("available_at", self.available_at)


class NewsIndex:
    """Append-only news-view metadata keyed by P0 event ids (no second Event store)."""

    def __init__(self, lineage: LineageIndex) -> None:
        self.lineage = lineage
        self.links: dict[str, EventLink] = {}
        self.presentations: dict[str, EventPresentation] = {}

    def _event(self, event_id: str):
        ev = self.lineage.events.get(event_id)
        if ev is None:
            raise ValueError(f"unknown event {event_id!r}")
        return ev

    def add_link(self, link: EventLink) -> None:
        ev, parent = self._event(link.event_id), self._event(link.parent_event_id)
        if parent.available_at > ev.available_at or link.available_at < ev.available_at:
            raise ValueError("PIT: link must follow both events' availability")
        if link.event_id in self.links and self.links[link.event_id] != link:
            raise ValueError("event already linked; news metadata is append-only")
        self.links[link.event_id] = link

    def add_presentation(self, p: EventPresentation) -> None:
        if p.available_at < self._event(p.event_id).available_at:
            raise ValueError("PIT: presentation cannot precede its event")
        if p.event_id in self.presentations and self.presentations[p.event_id] != p:
            raise ValueError("presentation already recorded; append-only")
        self.presentations[p.event_id] = p

    def status(self, event_id: str, as_of: datetime) -> NewsStatus:
        link = self.links.get(event_id)
        return link.status if link is not None and link.available_at <= as_of else NewsStatus.NEW


@dataclass(frozen=True)
class Viewport:
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def __post_init__(self) -> None:
        if not (math.isfinite(self.zoom) and 0.2 <= self.zoom <= 5.0):
            raise ValueError("zoom must be within [0.2, 5]")


@dataclass(frozen=True)
class ViewFilter:
    relationship_types: frozenset[RelationshipType] = frozenset(RelationshipType)
    epistemic: frozenset[EpistemicStatus] = frozenset(
        {EpistemicStatus.FACT, EpistemicStatus.SUPPORTED_INFERENCE})

    def accepts(self, edge: Edge) -> bool:
        return edge.relationship.relationship_type in self.relationship_types and edge.epistemic in self.epistemic


@dataclass(frozen=True)
class ViewState:
    view: ViewKind = ViewKind.NEWS
    filters: ViewFilter = field(default_factory=ViewFilter)
    focus_node_id: str | None = None
    expansion_steps: int = 0
    viewport: Viewport = field(default_factory=Viewport)

    def __post_init__(self) -> None:
        if self.expansion_steps < 0:
            raise ValueError("expansion_steps must be >= 0")


def switch_view(state: ViewState, view: ViewKind) -> ViewState:
    """Only the view changes; scope, filters, focus and viewport are preserved."""
    return replace(state, view=view)


@dataclass(frozen=True)
class NewsCard:
    event_id: str
    status: NewsStatus
    headline: str
    summary: tuple[str, ...]
    available_at: datetime
    source_count: int
    issuer_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]


@dataclass(frozen=True)
class NetNode:
    node_id: str
    issuer_id: str
    label: str
    symbol: str
    x: float
    y: float


@dataclass(frozen=True)
class NetEdge:
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: RelationshipType
    epistemic: EpistemicStatus
    line: str  # SOLID = confirmed fact, DASHED = expected/unconfirmed
    arrow: bool  # product/service/value flow (upstream -> downstream)
    available_at: datetime
    last_confirmed_at: datetime


@dataclass(frozen=True)
class NetworkView:
    nodes: tuple[NetNode, ...]
    edges: tuple[NetEdge, ...]
    hidden_edge_count: int  # rendered as "+N relationships"
    neighbor_order: dict = field(default_factory=dict)  # node_id -> ordered relationship ids


@dataclass(frozen=True)
class RIGViewModel:
    graph_as_of: datetime
    state: ViewState
    cards: tuple[NewsCard, ...]
    network: NetworkView


def edge_priority(e: NetEdge) -> tuple:
    """P1 ordering: confirmed facts, then most recently confirmed, then stable id."""
    return (0 if e.epistemic is EpistemicStatus.FACT else 1, -e.last_confirmed_at.timestamp(), e.relationship_id)


def _net_edge(e: Edge) -> NetEdge:
    rtype = e.relationship.relationship_type
    return NetEdge(
        e.relationship.relationship_id, e.relationship.source_node_id, e.relationship.target_node_id, rtype,
        e.epistemic, "SOLID" if e.epistemic is EpistemicStatus.FACT else "DASHED", rtype not in SYMMETRIC_TYPES,
        e.state.available_at, e.state.last_confirmed_at)


def neighborhood(edges: list[NetEdge], node_id: str, limit: int, steps: int,
                 priority=None) -> tuple[list[NetEdge], int]:
    if not FOCUS_MIN <= limit <= FOCUS_MAX:
        raise ValueError(f"focus limit must be within [{FOCUS_MIN}, {FOCUS_MAX}]")
    adj = sorted((e for e in edges if node_id in (e.source_node_id, e.target_node_id)), key=priority or edge_priority)
    shown = adj[: limit * (1 + steps)]
    return shown, len(adj) - len(shown)


def _layout(node_ids: list[str], center: str | None) -> dict[str, tuple[float, float]]:
    pos: dict[str, tuple[float, float]] = {}
    ring = [n for n in node_ids if n != center]
    if center is not None:
        pos[center] = (CANVAS / 2, CANVAS / 2)
    for i, n in enumerate(ring):
        a = 2 * math.pi * i / max(len(ring), 1) - math.pi / 2
        pos[n] = (round(CANVAS / 2 + 380 * math.cos(a), 2), round(CANVAS / 2 + 380 * math.sin(a), 2))
    return pos


def build_network(graph: RIGGraph, identity: IdentityLookup, state: ViewState, limit: int = FOCUS_MAX,
                  priority=None) -> NetworkView:
    """``priority`` is an extension point for later phases; the default is the frozen P1 order."""
    priority = priority or edge_priority
    all_edges = sorted((_net_edge(e) for e in graph.edges if state.filters.accepts(e)), key=priority)
    ids = sorted({n for e in all_edges for n in (e.source_node_id, e.target_node_id)})
    order = {n: [e.relationship_id for e in neighborhood(all_edges, n, FOCUS_MAX, 10 ** 6, priority)[0]] for n in ids}
    if state.focus_node_id is not None:
        shown, hidden = neighborhood(all_edges, state.focus_node_id, limit, state.expansion_steps, priority)
    else:
        cap = OVERVIEW_MAX_EDGES * (1 + state.expansion_steps)
        shown, hidden = all_edges[:cap], max(0, len(all_edges) - cap)
    node_ids = sorted({n for e in shown for n in (e.source_node_id, e.target_node_id)} |
                      ({state.focus_node_id} if state.focus_node_id in ids else set()))
    pos = _layout(node_ids, state.focus_node_id if state.focus_node_id in node_ids else None)
    nodes = []
    for n in node_ids:
        issuer_id = n.split(":", 1)[1]
        rec = identity.issuer(issuer_id)
        nodes.append(NetNode(n, issuer_id, rec.legal_name if rec else issuer_id, "●", *pos[n]))
    return NetworkView(tuple(nodes), tuple(shown), hidden, order)


def build_cards(ledger: RelationshipLedger, news: NewsIndex, graph: RIGGraph, state: ViewState,
                include_duplicates: bool = False) -> tuple[NewsCard, ...]:
    as_of = graph.graph_as_of
    rels_by_event: dict[str, set[str]] = {}
    issuers_by_event: dict[str, set[str]] = {}
    for e in graph.edges:
        if not state.filters.accepts(e):
            continue
        for cid in e.state.candidate_ids:
            c = ledger.candidates[cid]
            for ev in c.event_ids:
                rels_by_event.setdefault(ev, set()).add(e.relationship.relationship_id)
                issuers_by_event.setdefault(ev, set()).update((c.source_ref.issuer_id, c.target_ref.issuer_id))
    cards = []
    for ev in sorted(news.lineage.events.values(), key=lambda x: (-x.available_at.timestamp(), x.event_id)):
        if ev.available_at > as_of:
            continue
        status = news.status(ev.event_id, as_of)
        if status is NewsStatus.DUPLICATE and not include_duplicates:
            continue  # one Event, no repeated card
        try:
            lin = news.lineage.trace((ev.event_id,), as_of)
        except LineageError:
            continue  # untraceable news is never shown as a card (fail closed)
        pres = news.presentations.get(ev.event_id)
        if pres is not None and pres.available_at <= as_of:
            headline, summary = pres.headline, pres.summary
        else:
            headline, summary = lin.claims[0].statement, ()
        cards.append(NewsCard(
            ev.event_id, status, headline, summary, ev.available_at, len(lin.sources),
            tuple(sorted(issuers_by_event.get(ev.event_id, ()))),
            tuple(sorted(rels_by_event.get(ev.event_id, ())))))
    return tuple(cards)


def build_view_model(ledger: RelationshipLedger, news: NewsIndex, graph_as_of: datetime,
                     state: ViewState | None = None, priority=None) -> RIGViewModel:
    state = state or ViewState()
    graph = ledger.graph_as_of(graph_as_of)
    return RIGViewModel(graph_as_of, state, build_cards(ledger, news, graph, state),
                        build_network(graph, ledger.identity, state, priority=priority))
