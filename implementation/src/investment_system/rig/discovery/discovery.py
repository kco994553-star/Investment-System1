"""RIG P4 Discovery over the Fact Graph: position, emerging, common connections, research priority.

NEW IMPLEMENTATION. Every output is a descriptive label computed point-in-time from
FACT edges (and P2 status); none is an investment score or BUY/SELL/HOLD. Research
Priority is a High/Medium/Low *research* ordering only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..intel.intel import IntelIndex, Materiality, RelationshipStatus
from ..ledger import RIGGraph
from ..model import EpistemicStatus, RelationshipType

HUB_MIN_DEGREE = 5
BOTTLENECK_MIN_DEPENDENTS = 2
EMERGING_MIN_NEW = 2
FLOW_TYPES = frozenset({RelationshipType.SUPPLY_CHAIN, RelationshipType.CUSTOMER, RelationshipType.VALUE_CHAIN})


class Position(str, Enum):
    HUB = "HUB"
    BRIDGE = "BRIDGE"
    BOTTLENECK = "BOTTLENECK"


class ResearchPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def _iss(node_id: str) -> str:
    return node_id.split(":", 1)[1]


@dataclass(frozen=True)
class FactGraph:
    """Undirected adjacency and directed flow over FACT edges only."""

    nodes: frozenset[str]
    adjacency: dict  # issuer -> frozenset[issuer]
    upstream: dict  # issuer -> frozenset[suppliers] (flow types only)
    downstream: dict  # issuer -> frozenset[customers]
    relationship_ids: dict  # frozenset({a, b}) -> tuple[relationship_id, ...]


def fact_graph(graph: RIGGraph) -> FactGraph:
    adj: dict[str, set[str]] = {}
    up: dict[str, set[str]] = {}
    down: dict[str, set[str]] = {}
    rels: dict[frozenset, list[str]] = {}
    for e in graph.edges:
        if e.epistemic is not EpistemicStatus.FACT:
            continue
        a, b = _iss(e.relationship.source_node_id), _iss(e.relationship.target_node_id)
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
        rels.setdefault(frozenset((a, b)), []).append(e.relationship.relationship_id)
        if e.relationship.relationship_type in FLOW_TYPES:
            down.setdefault(a, set()).add(b)
            up.setdefault(b, set()).add(a)
    fz = lambda d: {k: frozenset(v) for k, v in sorted(d.items())}  # noqa: E731
    return FactGraph(frozenset(adj), fz(adj), fz(up), fz(down), {k: tuple(sorted(v)) for k, v in rels.items()})


def articulation_points(fg: FactGraph) -> frozenset[str]:
    """Nodes whose removal disconnects part of their component (iterative Tarjan)."""
    disc: dict[str, int] = {}
    low: dict[str, int] = {}
    out: set[str] = set()
    t = 0
    for root in sorted(fg.nodes):
        if root in disc:
            continue
        disc[root] = low[root] = t
        t += 1
        children = 0
        stack = [(root, None, iter(sorted(fg.adjacency.get(root, ()))))]
        while stack:
            v, parent, it = stack[-1]
            w = next(it, None)
            if w is None:
                stack.pop()
                if parent is not None:
                    low[parent] = min(low[parent], low[v])
                    if parent != root and low[v] >= disc[parent]:
                        out.add(parent)
                continue
            if w == parent:
                continue
            if w in disc:
                low[v] = min(low[v], disc[w])
            else:
                disc[w] = low[w] = t
                t += 1
                if v == root:
                    children += 1
                stack.append((w, v, iter(sorted(fg.adjacency.get(w, ())))))
        if children >= 2:
            out.add(root)
    return frozenset(out)


def positions(fg: FactGraph) -> dict[str, frozenset[Position]]:
    bridges = articulation_points(fg)
    out: dict[str, frozenset[Position]] = {}
    for n in sorted(fg.nodes):
        p: set[Position] = set()
        if len(fg.adjacency.get(n, ())) >= HUB_MIN_DEGREE:
            p.add(Position.HUB)
        if n in bridges:
            p.add(Position.BRIDGE)
        sole = [c for c in fg.downstream.get(n, ()) if fg.upstream.get(c, frozenset()) == {n}]
        if len(sole) >= BOTTLENECK_MIN_DEPENDENTS:
            p.add(Position.BOTTLENECK)
        if p:
            out[n] = frozenset(p)
    return out


def emerging(graph: RIGGraph, intel: IntelIndex, as_of: datetime) -> frozenset[str]:
    counts: dict[str, int] = {}
    for e in graph.edges:
        if intel.status(e.relationship.relationship_id, as_of) in (RelationshipStatus.NEW,
                                                                    RelationshipStatus.DISCOVERED):
            for n in (e.relationship.source_node_id, e.relationship.target_node_id):
                counts[_iss(n)] = counts.get(_iss(n), 0) + 1
    return frozenset(n for n, c in counts.items() if c >= EMERGING_MIN_NEW)


def common_connections(fg: FactGraph, a: str, b: str) -> frozenset[str]:
    return (fg.adjacency.get(a, frozenset()) & fg.adjacency.get(b, frozenset())) - {a, b}


def my_common_connections(fg: FactGraph, my: frozenset[str]) -> frozenset[str]:
    """Non-My companies directly connected to at least two My companies."""
    return frozenset(n for n in fg.nodes - my if len(fg.adjacency.get(n, frozenset()) & my) >= 2)


def research_priority(fg: FactGraph, intel: IntelIndex, graph: RIGGraph, my: frozenset[str],
                      as_of: datetime) -> dict[str, ResearchPriority]:
    """Non-My companies only. HIGH: high/critical FACT link to a My company, or sole supplier of one;
    MEDIUM: any FACT link to My, emerging, or a common connection of My; else LOW."""
    pos = positions(fg)
    emerg = emerging(graph, intel, as_of)
    common = my_common_connections(fg, my)
    out: dict[str, ResearchPriority] = {}
    for n in sorted(fg.nodes - my):
        links = fg.adjacency.get(n, frozenset()) & my
        mats = [intel.materiality_as_of(r, as_of) for m in links for r in fg.relationship_ids[frozenset((n, m))]]
        sole_for_my = any(fg.upstream.get(m, frozenset()) == {n} for m in my)
        if any(x in (Materiality.HIGH, Materiality.CRITICAL) for x in mats) or sole_for_my:
            out[n] = ResearchPriority.HIGH
        elif links or n in emerg or n in common or Position.BOTTLENECK in pos.get(n, ()):
            out[n] = ResearchPriority.MEDIUM
        else:
            out[n] = ResearchPriority.LOW
    return out
