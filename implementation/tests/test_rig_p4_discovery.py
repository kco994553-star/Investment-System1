"""RIG P4 Discovery — graph position, emerging, common connections, Impact Graph, Research Priority."""
import ast
import random
from datetime import timedelta
from pathlib import Path

import pytest

from investment_system.rig.discovery.discovery import (
    FactGraph,
    Position,
    ResearchPriority,
    articulation_points,
    common_connections,
    emerging,
    fact_graph,
    my_common_connections,
    positions,
    research_priority,
)
from investment_system.rig.discovery.impact import (
    ConceptIndex,
    ConceptKind,
    ConceptRef,
    Exposure,
    Hop,
    concept_impact,
    event_impact,
)
from investment_system.rig.discovery.present import build_rig_page, discovery_priority
from investment_system.rig.intel.intel import IntelIndex, Materiality, MaterialityObservation
from investment_system.rig.model import Relationship
from investment_system.rig.myview.prefs import UserOrganization
from investment_system.rig.myview.scope import build_sets
from investment_system.rig.network.views import NewsIndex, ViewState, build_view_model
from tests.rig_fixtures import IDS, T0, issuer_id, standard

D = timedelta(days=1)
LATER = T0 + 60 * D  # every standard relationship is STABLE by now
DISC_PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "rig" / "discovery"
I = issuer_id


class Holdings:
    def __init__(self, ids):
        self.ids = frozenset(I(i) for i in ids)

    def held_issuer_ids(self, as_of):
        return self.ids


def rid(src, tgt, rtype="SUPPLY_CHAIN"):
    return Relationship.for_key((rtype, I(src), I(tgt))).relationship_id


def test_graph_positions_hub_bridge_bottleneck_use_fact_edges_only():
    s = standard()
    fg = fact_graph(s.ledger.graph_as_of(LATER))
    assert I("skhynix") not in fg.nodes  # SUPPORTED_INFERENCE edge is not part of the Fact Graph
    pos = positions(fg)
    assert pos[I("tsmc")] == {Position.HUB, Position.BRIDGE, Position.BOTTLENECK}
    assert pos[I("nvidia")] == {Position.BRIDGE}  # Meta only reaches the graph through NVIDIA
    assert I("google") not in pos and I("asml") not in pos  # google has two suppliers; asml has one dependent
    # Two suppliers serving the same two customers: neither is a sole-supplier bottleneck.
    from tests.rig_fixtures import Scenario
    t = Scenario()
    for sup in ("intel", "amd"):
        for cust in ("microsoft", "amazon"):
            t.rel(sup, cust, T0)
    assert positions(fact_graph(t.ledger.graph_as_of(T0 + D))) == {}


def _brute_force(fg: FactGraph):
    def comps(nodes):
        seen, c = set(), 0
        for n in nodes:
            if n in seen:
                continue
            c += 1
            stack = [n]
            while stack:
                v = stack.pop()
                if v in seen:
                    continue
                seen.add(v)
                stack.extend(w for w in fg.adjacency.get(v, ()) if w in nodes and w not in seen)
        return c
    base = comps(fg.nodes)
    return frozenset(n for n in fg.nodes if comps(fg.nodes - {n}) > base)


def test_articulation_points_match_brute_force_on_random_graphs():
    rng = random.Random(7)
    for _ in range(60):
        n = rng.randint(2, 12)
        adj = {str(i): set() for i in range(n)}
        for a in range(n):
            for b in range(a + 1, n):
                if rng.random() < 0.25:
                    adj[str(a)].add(str(b))
                    adj[str(b)].add(str(a))
        nodes = frozenset(k for k, v in adj.items() if v)
        fg = FactGraph(nodes, {k: frozenset(v) for k, v in adj.items() if v}, {}, {}, {})
        assert articulation_points(fg) == _brute_force(fg)


def test_emerging_and_common_connections():
    s = standard()
    early = T0 + 30 * D
    assert {I("tsmc"), I("nvidia"), I("broadcom"), I("google")} <= emerging(s.ledger.graph_as_of(early),
                                                                          IntelIndex(s.ledger), early)
    assert emerging(s.ledger.graph_as_of(LATER), IntelIndex(s.ledger), LATER) == frozenset()
    fg = fact_graph(s.ledger.graph_as_of(LATER))
    assert common_connections(fg, I("apple"), I("nvidia")) == {I("tsmc")}
    assert my_common_connections(fg, frozenset({I("apple"), I("amd")})) == {I("tsmc")}
    assert my_common_connections(fg, frozenset({I("apple")})) == frozenset()


def test_research_priority_labels_not_scores():
    s = standard()
    intel = IntelIndex(s.ledger)
    g = s.ledger.graph_as_of(LATER)
    fg = fact_graph(g)
    rp = research_priority(fg, intel, g, frozenset({I("google")}), LATER)
    assert I("google") not in rp  # My companies are never ranked
    assert rp[I("broadcom")] is ResearchPriority.MEDIUM and rp[I("asml")] is ResearchPriority.LOW
    s.event("mh", LATER)
    intel.add_materiality(MaterialityObservation("mh", rid("broadcom", "google", "CUSTOMER"), Materiality.HIGH,
                                                 LATER, ("evd_mh_0",)))
    assert research_priority(fg, intel, g, frozenset({I("google")}), LATER)[I("broadcom")] is ResearchPriority.HIGH
    # Sole supplier of a My company is HIGH.
    assert research_priority(fg, intel, g, frozenset({I("meta")}), LATER)[I("nvidia")] is ResearchPriority.HIGH
    assert {v.value for v in ResearchPriority} == {"HIGH", "MEDIUM", "LOW"}


def test_impact_graph_is_potential_and_never_stored():
    s = standard()
    g = s.ledger.graph_as_of(LATER)
    fg = fact_graph(g)
    before = {k: list(v) for k, v in s.ledger.states.items()}
    ig = event_impact(fg, g, frozenset({I("asml")}), "evt_r10", max_hops=2)
    reached = ig.reached()
    assert I("tsmc") in reached and I("apple") in reached and I("samsung") in reached
    assert I("meta") not in reached  # 3 hops away
    path = [p for p in ig.paths if p.nodes[-1] == I("apple")][0]
    assert path.hops == (Hop.DOWNSTREAM, Hop.DOWNSTREAM)
    assert [p for p in ig.paths if p.nodes[-1] == I("samsung")][0].hops[-1] is Hop.PEER
    assert {k: list(v) for k, v in s.ledger.states.items()} == before  # nothing persisted
    for p in ig.paths:
        assert len(set(p.nodes)) == len(p.nodes)  # no cycles
    assert len(ig.paths) == len(ig.reached())  # each company reached once, by its shortest path
    assert I("meta") in event_impact(fg, g, frozenset({I("asml")}), "evt_r10", max_hops=3).reached()
    with pytest.raises(ValueError):
        event_impact(fg, g, frozenset({I("asml")}), "evt_r10", max_hops=4)
    up = event_impact(fg, g, frozenset({I("apple")}), "e", max_hops=1)
    assert [p.hops for p in up.paths] == [(Hop.UPSTREAM,)]


def test_concept_nodes_are_references_with_evidence_backed_exposure():
    s = standard()
    concepts = ConceptIndex(IDS, s.lin)
    concepts.add_concept(ConceptRef("macro:rates", ConceptKind.MACRO_DRIVER, "US rates"))
    concepts.add_concept(ConceptRef("tech:euv", ConceptKind.TECHNOLOGY, "EUV"))
    s.event("x1", T0 + 20 * D)
    concepts.add_exposure(Exposure("x1", "tech:euv", I("asml"), T0 + 20 * D, ("evd_x1_0",)))
    s.event("x2", LATER + D)
    with pytest.raises(ValueError):  # evidence later than exposure
        concepts.add_exposure(Exposure("x2", "tech:euv", I("tsmc"), LATER, ("evd_x2_0",)))
    with pytest.raises(ValueError):
        concepts.add_exposure(Exposure("x3", "tech:none", I("tsmc"), LATER, ("evd_x1_0",)))
    with pytest.raises(ValueError):
        concepts.add_exposure(Exposure("x4", "tech:euv", "issuer_unknown", LATER, ("evd_x1_0",)))
    g = s.ledger.graph_as_of(LATER)
    ig = concept_impact(fact_graph(g), g, concepts, "tech:euv", max_hops=1)
    assert ig.paths[0].nodes == ("concept:tech:euv", I("asml")) and ig.paths[0].hops == (Hop.EXPOSURE,)
    assert I("tsmc") in ig.reached()
    early = s.ledger.graph_as_of(T0 + 10 * D)
    assert concept_impact(fact_graph(early), early, concepts, "tech:euv").paths == ()  # exposure not yet known
    assert concept_impact(fact_graph(g), g, concepts, "macro:rates").paths == ()


def test_common_connection_expansion_slot():
    s = standard()
    intel = IntelIndex(s.ledger)
    sets = build_sets(s.ledger, Holdings(["apple", "amd"]), UserOrganization(IDS), LATER)
    common = my_common_connections(fact_graph(s.ledger.graph_as_of(LATER)), sets.my)
    news = NewsIndex(s.lin)
    st = ViewState(focus_node_id="issuer:issuer_nvidia")
    p1 = build_view_model(s.ledger, news, LATER, st).network.edges
    p4 = build_view_model(s.ledger, news, LATER, st, priority=discovery_priority(intel, sets, common, LATER)
                          ).network.edges
    assert p1[0].relationship_id == rid("nvidia", "meta", "VALUE_CHAIN")
    assert p4[0].relationship_id == rid("tsmc", "nvidia")  # touches common connection TSMC


def test_full_page_has_discovery_and_impact_panels():
    s = standard()
    g = s.ledger.graph_as_of(LATER)
    ig = event_impact(fact_graph(g), g, frozenset({I("asml")}), "evt_r10")
    vm, page = build_rig_page(s.ledger, NewsIndex(s.lin), IntelIndex(s.ledger), Holdings(["google"]),
                              UserOrganization(IDS), LATER, impacts=(ig,))
    assert 'id="discovery"' in page and "조사 우선순위 (매수·매도 판단 아님)" in page
    assert page.count('class="impact-path"') == len({p.nodes[-2:] for p in ig.paths if len(p.nodes) > 1})
    assert 'stroke-dasharray="2 5"' in page and "잠재 영향 경로 (사실 아님)" in page
    assert 'data-scope="MY"' in page  # P3 composition kept


def test_discovery_package_boundaries():
    for f in DISC_PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    assert not (node.module or "").startswith("investment_system"), f.name
                else:
                    assert node.level in (1, 2), f.name
                    if node.level == 2:
                        assert (node.module or "").split(".")[0] in {"gate", "ledger", "model", "network", "intel",
                                                                      "myview"}, f.name
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("investment_system") for a in node.names), f.name
