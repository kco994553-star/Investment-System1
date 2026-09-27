"""RIG P4 Impact Graph: potential impact paths from an Event or concept. NEW IMPLEMENTATION.

The Impact Graph is derived on demand and is never stored as a relationship: it
reads FACT edges and evidence-backed concept exposures and returns paths labelled
as *potential*. Concept nodes are references only — Macro owns Macro Driver
definitions; RIG stores only the id it was given.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..gate import IdentityLookup, LineageIndex
from ..ledger import RIGGraph
from ..model import _require_aware, _require_ids, _require_text
from .discovery import FactGraph

MAX_HOPS = 3


class ConceptKind(str, Enum):
    MACRO_DRIVER = "MACRO_DRIVER"  # ⬡ (definition owned by Macro)
    TECHNOLOGY = "TECHNOLOGY"  # ◆ Technology / Product
    VALUE_CHAIN_STAGE = "VALUE_CHAIN_STAGE"  # ▣


CONCEPT_SYMBOL = {ConceptKind.MACRO_DRIVER: "⬡", ConceptKind.TECHNOLOGY: "◆", ConceptKind.VALUE_CHAIN_STAGE: "▣"}


@dataclass(frozen=True)
class ConceptRef:
    concept_id: str
    kind: ConceptKind
    label: str

    def __post_init__(self) -> None:
        _require_text("concept_id", self.concept_id)
        _require_text("label", self.label)


@dataclass(frozen=True)
class Exposure:
    """Evidence-backed link from a concept to an issuer (an inference, never a Fact edge)."""

    exposure_id: str
    concept_id: str
    issuer_id: str
    available_at: datetime
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("exposure_id", "concept_id", "issuer_id"):
            _require_text(name, getattr(self, name))
        _require_aware("available_at", self.available_at)
        _require_ids("evidence_ids", self.evidence_ids)


class ConceptIndex:
    def __init__(self, identity: IdentityLookup, lineage: LineageIndex) -> None:
        self.identity = identity
        self.lineage = lineage
        self.concepts: dict[str, ConceptRef] = {}
        self.exposures: list[Exposure] = []

    def add_concept(self, c: ConceptRef) -> None:
        if c.concept_id in self.concepts and self.concepts[c.concept_id] != c:
            raise ValueError("concept already registered; append-only")
        self.concepts[c.concept_id] = c

    def add_exposure(self, x: Exposure) -> None:
        if x.concept_id not in self.concepts:
            raise ValueError("unknown concept")
        if self.identity.issuer(x.issuer_id) is None:
            raise ValueError("unknown issuer (fail closed)")
        if any(e.exposure_id == x.exposure_id for e in self.exposures):
            raise ValueError("exposure already recorded; append-only")
        for eid in x.evidence_ids:
            ev = self.lineage.evidence.get(eid)
            if ev is None or ev.available_at > x.available_at:
                raise ValueError(f"evidence {eid!r} missing or not available at exposure time")
        self.exposures.append(x)

    def exposed_issuers(self, concept_id: str, as_of: datetime) -> frozenset[str]:
        return frozenset(x.issuer_id for x in self.exposures if x.concept_id == concept_id and x.available_at <= as_of)


class Hop(str, Enum):
    EXPOSURE = "EXPOSURE"  # concept -> exposed issuer
    DOWNSTREAM = "DOWNSTREAM"  # supplier -> customer
    UPSTREAM = "UPSTREAM"  # customer -> supplier
    PEER = "PEER"  # competitor / non-flow link


@dataclass(frozen=True)
class ImpactPath:
    nodes: tuple[str, ...]  # starts at the seed (issuer id or "concept:<id>")
    hops: tuple[Hop, ...]


@dataclass(frozen=True)
class ImpactGraph:
    """Potential impact paths only. Not a Fact Graph and not persisted."""

    seed: str
    graph_as_of: datetime
    paths: tuple[ImpactPath, ...]

    def reached(self) -> frozenset[str]:
        return frozenset(p.nodes[-1] for p in self.paths)


def _step(fg: FactGraph, n: str):
    for m in sorted(fg.adjacency.get(n, ())):
        if m in fg.downstream.get(n, ()):
            yield m, Hop.DOWNSTREAM
        elif m in fg.upstream.get(n, ()):
            yield m, Hop.UPSTREAM
        else:
            yield m, Hop.PEER


def impact_graph(fg: FactGraph, graph: RIGGraph, seed_issuers: frozenset[str], seed: str,
                 max_hops: int = 2, first_hop: Hop | None = None) -> ImpactGraph:
    if not 1 <= max_hops <= MAX_HOPS:
        raise ValueError(f"max_hops must be within [1, {MAX_HOPS}]")
    paths: list[ImpactPath] = []
    seen: set[str] = set(seed_issuers)
    frontier = [ImpactPath((seed, i), (first_hop,)) if first_hop else ImpactPath((i,), ())
                for i in sorted(seed_issuers)]
    paths.extend(p for p in frontier if p.hops)
    for _ in range(max_hops):
        nxt = []
        for p in frontier:
            for m, hop in _step(fg, p.nodes[-1]):
                if m in seen:
                    continue
                seen.add(m)
                nxt.append(ImpactPath(p.nodes + (m,), p.hops + (hop,)))
        paths.extend(nxt)
        frontier = nxt
    return ImpactGraph(seed, graph.graph_as_of, tuple(paths))


def event_impact(fg: FactGraph, graph: RIGGraph, event_issuers: frozenset[str], event_id: str,
                 max_hops: int = 2) -> ImpactGraph:
    return impact_graph(fg, graph, event_issuers, f"event:{event_id}", max_hops)


def concept_impact(fg: FactGraph, graph: RIGGraph, concepts: ConceptIndex, concept_id: str,
                   max_hops: int = 2) -> ImpactGraph:
    exposed = concepts.exposed_issuers(concept_id, graph.graph_as_of)
    return impact_graph(fg, graph, exposed, f"concept:{concept_id}", max_hops, first_hop=Hop.EXPOSURE)
