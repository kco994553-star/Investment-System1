"""RIG P3 scope, feed priority, related news, Attention inputs and overlay. NEW IMPLEMENTATION.

내 기업 = Portfolio holdings ∪ ★ 관심기업. Scope/chips only select what is shown;
the full market (ALL) is always available. Feed Priority ≠ Investment Attractiveness:
tiers order the feed and never become a score. The Attention export carries RIG-owned
inputs only; delivery (Immediate/Digest/Feed Only) belongs to the separate Attention
layer and is not decided here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol

from ..intel.intel import IntelIndex, Materiality
from ..intel.present import intel_rank
from ..ledger import RelationshipLedger
from ..network.views import NetEdge, RIGViewModel, ViewKind, ViewState, edge_priority, switch_view
from .prefs import HoldingsPort, UserOrganization


class Scope(str, Enum):
    MY = "MY"
    ALL = "ALL"


class Chip(str, Enum):
    HELD = "HELD"  # ◎ 보유
    INTEREST = "INTEREST"  # ★ 관심
    GROUP = "GROUP"  # 그룹
    RELATED = "RELATED"  # 연관 (1-hop)


class Relevance(str, Enum):
    HELD = "HELD"
    INTEREST = "INTEREST"
    GROUP = "GROUP"
    ONE_HOP = "ONE_HOP"
    NONE = "NONE"


class FeedTier(str, Enum):
    HELD_IMPORTANT = "HELD_IMPORTANT"
    INTEREST_IMPORTANT = "INTEREST_IMPORTANT"
    MY_HIGH_MATERIALITY_ONE_HOP = "MY_HIGH_MATERIALITY_ONE_HOP"
    RESEARCH_PRIORITY_NEW = "RESEARCH_PRIORITY_NEW"
    MY_OTHER = "MY_OTHER"
    MARKET = "MARKET"


TIER_ORDER = tuple(FeedTier)
IMPORTANT = frozenset({Materiality.HIGH, Materiality.CRITICAL})


@dataclass(frozen=True)
class MyViewState:
    base: ViewState = field(default_factory=ViewState)
    scope: Scope = Scope.MY
    chips: frozenset[Chip] = frozenset(Chip)
    group_id: str | None = None
    overlay_on: bool = False  # Investment Overlay is OFF by default


def switch_my_view(state: MyViewState, view: ViewKind) -> MyViewState:
    """Scope / chips / group / overlay and the P1 state all survive a News↔Network switch."""
    return replace(state, base=switch_view(state.base, view))


@dataclass(frozen=True)
class MySets:
    held: frozenset[str]
    interest: frozenset[str]
    groups: dict  # group_id -> frozenset[issuer_id]
    group_names: dict  # group_id -> name
    adjacency: dict  # issuer_id -> frozenset[issuer_id] over the visible graph

    @property
    def my(self) -> frozenset[str]:
        return self.held | self.interest

    def base(self, chips: frozenset[Chip], group_id: str | None) -> frozenset[str]:
        out: set[str] = set()
        if Chip.HELD in chips:
            out |= self.held
        if Chip.INTEREST in chips:
            out |= self.interest
        if Chip.GROUP in chips and group_id is not None:
            out |= self.groups.get(group_id, frozenset())
        return frozenset(out)

    def one_hop(self, nodes: frozenset[str]) -> frozenset[str]:
        return frozenset(n for x in nodes for n in self.adjacency.get(x, ())) - nodes

    def relevance(self, issuer_id: str) -> Relevance:
        if issuer_id in self.held:
            return Relevance.HELD
        if issuer_id in self.interest:
            return Relevance.INTEREST
        if any(issuer_id in m for m in self.groups.values()):
            return Relevance.GROUP
        if issuer_id in self.one_hop(self.my):
            return Relevance.ONE_HOP
        return Relevance.NONE


def _issuer(node_id: str) -> str:
    return node_id.split(":", 1)[1]


def build_sets(ledger: RelationshipLedger, holdings: HoldingsPort, org: UserOrganization,
               as_of: datetime) -> MySets:
    held = frozenset(holdings.held_issuer_ids(as_of))
    unknown = [h for h in held if ledger.identity.issuer(h) is None]
    if unknown:
        raise ValueError(f"holdings reference unknown issuers {sorted(unknown)} (fail closed)")
    adj: dict[str, set[str]] = {}
    for e in ledger.graph_as_of(as_of).edges:
        a, b = _issuer(e.relationship.source_node_id), _issuer(e.relationship.target_node_id)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    groups = org.groups_as_of(as_of)
    return MySets(held, org.interests_as_of(as_of), {g: x.members for g, x in groups.items()},
                  {g: x.name for g, x in groups.items()}, {k: frozenset(v) for k, v in adj.items()})


@dataclass(frozen=True)
class ScopeSelection:
    issuer_ids: frozenset[str]
    relationship_ids: frozenset[str]
    event_ids: frozenset[str]


def select(vm: RIGViewModel, sets: MySets, state: MyViewState) -> ScopeSelection:
    """What the MY scope shows. ALL shows everything in the P1 view model."""
    if state.scope is Scope.ALL:
        return ScopeSelection(frozenset(n.issuer_id for n in vm.network.nodes),
                              frozenset(e.relationship_id for e in vm.network.edges),
                              frozenset(c.event_id for c in vm.cards))
    base = sets.base(state.chips, state.group_id)
    nodes = base | (sets.one_hop(base) if Chip.RELATED in state.chips else frozenset())
    rels = frozenset(e.relationship_id for e in vm.network.edges
                     if {_issuer(e.source_node_id), _issuer(e.target_node_id)} <= nodes
                     and {_issuer(e.source_node_id), _issuer(e.target_node_id)} & base)
    events = frozenset(c.event_id for c in vm.cards if set(c.issuer_ids) & nodes)
    return ScopeSelection(nodes, rels, events)


def my_priority(intel: IntelIndex, sets: MySets, as_of: datetime):
    """Critical → Portfolio/관심 → High materiality → Recent change → P1 order."""
    def key(e: NetEdge) -> tuple:
        crit_high, change = intel_rank(intel, e.relationship_id, as_of)
        mine = 0 if {_issuer(e.source_node_id), _issuer(e.target_node_id)} & sets.my else 1
        return (0 if crit_high == 0 else 1, mine, crit_high, change) + edge_priority(e)
    return key


def _card_materiality(intel: IntelIndex, rel_ids, as_of) -> Materiality | None:
    ms = [m for m in (intel.materiality_as_of(r, as_of) for r in rel_ids) if m is not None]
    return max(ms, key=lambda m: m.rank) if ms else None


def feed_tiers(vm: RIGViewModel, intel: IntelIndex, sets: MySets,
               research_new: frozenset[str] = frozenset()) -> dict[str, FeedTier]:
    """``research_new`` (P4 hook): non-My issuers with High Research Priority."""
    as_of = vm.graph_as_of
    high_hop: set[str] = set()
    for e in vm.network.edges:
        a, b = _issuer(e.source_node_id), _issuer(e.target_node_id)
        if intel.materiality_as_of(e.relationship_id, as_of) in IMPORTANT:
            if a in sets.my and b not in sets.my:
                high_hop.add(b)
            if b in sets.my and a not in sets.my:
                high_hop.add(a)
    out = {}
    for c in vm.cards:
        who = set(c.issuer_ids)
        important = _card_materiality(intel, c.relationship_ids, as_of) in IMPORTANT
        if important and who & sets.held:
            t = FeedTier.HELD_IMPORTANT
        elif important and who & sets.interest:
            t = FeedTier.INTEREST_IMPORTANT
        elif who & high_hop:
            t = FeedTier.MY_HIGH_MATERIALITY_ONE_HOP
        elif who & research_new:
            t = FeedTier.RESEARCH_PRIORITY_NEW
        elif who & sets.my:
            t = FeedTier.MY_OTHER
        else:
            t = FeedTier.MARKET
        out[c.event_id] = t
    return out


def feed_order(vm: RIGViewModel, tiers: dict[str, FeedTier]) -> tuple[str, ...]:
    pos = {c.event_id: i for i, c in enumerate(vm.cards)}  # P1 order = most recent first
    return tuple(sorted(tiers, key=lambda e: (TIER_ORDER.index(tiers[e]), pos[e])))


@dataclass(frozen=True)
class RelatedNews:
    event_id: str
    relation: str  # DIRECT | RELATED


def related_news(vm: RIGViewModel, sets: MySets, issuer_id: str) -> tuple[RelatedNews, ...]:
    hop = sets.adjacency.get(issuer_id, frozenset())
    out = []
    for c in vm.cards:
        if issuer_id in c.issuer_ids:
            out.append(RelatedNews(c.event_id, "DIRECT"))
        elif set(c.issuer_ids) & hop:
            out.append(RelatedNews(c.event_id, "RELATED"))
    return tuple(out)


@dataclass(frozen=True)
class AttentionInput:
    """RIG-owned inputs for a separate Attention layer. Carries no delivery decision."""

    event_id: str
    event_importance: Materiality | None
    user_relevance: Relevance
    materiality: Materiality | None
    available_at: datetime  # recency is derived by the consumer from this knowledge time
    confidence: Decimal | None


def attention_inputs(vm: RIGViewModel, ledger: RelationshipLedger, intel: IntelIndex,
                     sets: MySets) -> tuple[AttentionInput, ...]:
    as_of = vm.graph_as_of
    graph = {e.relationship.relationship_id: e for e in ledger.graph_as_of(as_of).edges}
    rel_rank = list(Relevance)
    out = []
    for c in vm.cards:
        m = _card_materiality(intel, c.relationship_ids, as_of)
        rels = [sets.relevance(i) for i in c.issuer_ids] or [Relevance.NONE]
        confs = [graph[r].state.confidence for r in c.relationship_ids if r in graph]
        out.append(AttentionInput(c.event_id, m, min(rels, key=rel_rank.index), m, c.available_at,
                                  max(confs) if confs else None))
    return tuple(out)


class OverlayPort(Protocol):
    """Read-only rows from existing QGV / Technical / Macro / Portfolio / Profile owners."""

    def rows(self, issuer_id: str, as_of: datetime) -> tuple[tuple[str, str], ...]: ...


def overlay_rows(port: OverlayPort | None, sets: MySets, state: MyViewState,
                 as_of: datetime) -> dict[str, tuple[tuple[str, str], ...]]:
    if not state.overlay_on or port is None:
        return {}
    out = {}
    for issuer in sorted(sets.my):
        rows = tuple(port.rows(issuer, as_of))
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in rows):
            raise TypeError("overlay rows must be pre-formatted strings; RIG does not compute them")
        out[issuer] = rows
    return out
