"""RIG P0 append-only relationship ledger and PIT graph reconstruction. NEW IMPLEMENTATION.

In-memory only (no store is specified by ``RIG_NEWS_ARCH_v0.1`` P0). Nothing is
deleted: every candidate and gate decision is retained, accepted candidates add a
new ``RelationshipState`` version, and a historical graph only sees states with
``available_at <= graph_as_of``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .gate import GateDecision, GateOutcome, IdentityLookup, Lineage, LineageIndex, effective_interval, evaluate
from .model import (
    Edge,
    EpistemicStatus,
    Node,
    Relationship,
    RelationshipCandidate,
    RelationshipState,
    _require_aware,
    stable_id,
)


@dataclass(frozen=True)
class RIGGraph:
    graph_as_of: datetime
    valid_on: date
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]

    def facts(self) -> tuple[Edge, ...]:
        return tuple(e for e in self.edges if e.epistemic is EpistemicStatus.FACT)

    def inferences(self) -> tuple[Edge, ...]:
        return tuple(e for e in self.edges if e.epistemic is EpistemicStatus.SUPPORTED_INFERENCE)


@dataclass(frozen=True)
class EdgeTrace:
    """Full backward lineage of one edge: Source -> ... -> Update Gate -> Edge."""

    edge: Edge
    decisions: tuple[GateDecision, ...]
    candidates: tuple[RelationshipCandidate, ...]
    lineage: Lineage


class RelationshipLedger:
    def __init__(self, identity: IdentityLookup, lineage: LineageIndex) -> None:
        self.identity = identity
        self.lineage = lineage
        self.candidates: dict[str, RelationshipCandidate] = {}
        self.decisions: dict[str, GateDecision] = {}
        self.relationships: dict[tuple[str, str, str], Relationship] = {}
        self.states: dict[tuple[str, str, str], list[RelationshipState]] = {}

    def _candidates_for(self, key) -> tuple[RelationshipCandidate, ...]:
        return tuple(c for c in self.candidates.values() if c.key() == key)

    def submit(self, cand: RelationshipCandidate, decided_at: datetime) -> GateDecision:
        if cand.candidate_id in self.candidates:
            raise ValueError(f"candidate {cand.candidate_id!r} already submitted; ledger is append-only")
        key = cand.key()
        prior_states = tuple(self.states.get(key, ())) if key else ()
        decision, lin = evaluate(
            cand, decided_at, identity=self.identity, lineage=self.lineage,
            prior_states=prior_states, prior_candidates=self._candidates_for(key) if key else ())
        self.candidates[cand.candidate_id] = cand
        self.decisions[cand.candidate_id] = decision
        if decision.outcome is GateOutcome.ACCEPTED:
            prior = prior_states[-1] if prior_states else None
            rel = self.relationships.setdefault(key, Relationship.for_key(key))
            vf, vt = effective_interval(cand, prior)
            state = RelationshipState(
                state_id=stable_id("rst", decision.decision_id),
                relationship_id=rel.relationship_id,
                epistemic=cand.epistemic,  # never upgraded by the gate
                valid_from=vf,
                valid_to=vt,
                available_at=cand.available_at,
                first_detected_at=prior.first_detected_at if prior else cand.available_at,
                last_confirmed_at=cand.available_at,
                evidence_ids=tuple(sorted(set(lin.evidence_ids) | set(prior.evidence_ids if prior else ()))),
                candidate_ids=(prior.candidate_ids if prior else ()) + (cand.candidate_id,),
                decision_id=decision.decision_id,
                confidence=cand.confidence,
            )
            self.states.setdefault(key, []).append(state)
        return decision

    def preserved(self, outcome: GateOutcome) -> tuple[tuple[RelationshipCandidate, GateDecision], ...]:
        return tuple((self.candidates[cid], d) for cid, d in self.decisions.items() if d.outcome is outcome)

    def graph_as_of(self, graph_as_of: datetime, valid_on: date | None = None) -> RIGGraph:
        _require_aware("graph_as_of", graph_as_of)
        day = graph_as_of.date() if valid_on is None else valid_on
        if day > graph_as_of.date():
            raise ValueError("PIT: valid_on cannot be after graph_as_of")
        edges: list[Edge] = []
        for key in sorted(self.states):
            known = [s for s in self.states[key] if s.available_at <= graph_as_of]
            if known and known[-1].valid_on(day):
                edges.append(Edge(self.relationships[key], known[-1], graph_as_of))
        node_ids = sorted({n for e in edges for n in (e.relationship.source_node_id, e.relationship.target_node_id)})
        nodes = tuple(Node(n, n.split(":", 1)[1]) for n in node_ids)
        return RIGGraph(graph_as_of, day, nodes, tuple(edges))

    def trace(self, edge: Edge) -> EdgeTrace:
        cands = tuple(self.candidates[c] for c in edge.state.candidate_ids)
        decisions = tuple(self.decisions[c] for c in edge.state.candidate_ids)
        if any(d.outcome is not GateOutcome.ACCEPTED for d in decisions):
            raise ValueError("edge lineage contains a non-accepted decision")
        event_ids = tuple(sorted({e for c in cands for e in c.event_ids}))
        lin = self.lineage.trace(event_ids, edge.graph_as_of)
        if set(lin.evidence_ids) != set(edge.state.evidence_ids):
            raise ValueError("edge evidence does not match its traced lineage")
        return EdgeTrace(edge, decisions, cands, lin)
