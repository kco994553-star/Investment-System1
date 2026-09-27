"""RIG P2 Relationship Intelligence — status, materiality, Deal state, timeline, badges, priority."""
import ast
from datetime import date, timedelta
from pathlib import Path

import pytest

from investment_system.rig.intel.intel import (
    DealObservation,
    DealState,
    IntelIndex,
    Materiality,
    MaterialityObservation,
    RelationshipStatus,
)
from investment_system.rig.intel.present import intel_extras, intel_priority
from investment_system.rig.model import IdentityRef, Relationship, RelationshipType
from investment_system.rig.network.views import NewsIndex, ViewState, build_view_model
from tests.rig_fixtures import T0, Scenario, issuer_id, standard

D = timedelta(days=1)
INTEL_PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "rig" / "intel"


def rid(src, tgt, rtype=RelationshipType.SUPPLY_CHAIN):
    a, b = issuer_id(src), issuer_id(tgt)
    if rtype is RelationshipType.COMPETITOR:
        a, b = sorted((a, b))
    return Relationship.for_key((rtype.value, a, b)).relationship_id


def ev(s, tag, at):
    s.event(tag, at)
    return f"evd_{tag}_0"


n = [0]


def deal(s, deal_id, state, at, src="tsmc", tgt="apple", event=False):
    n[0] += 1
    e = ev(s, f"deal{n[0]}", at)
    return DealObservation(f"obs{n[0]}", deal_id, RelationshipType.SUPPLY_CHAIN, IdentityRef(issuer_id(src)),
                           IdentityRef(issuer_id(tgt)), state, at, (e,), (f"evt_deal{n[0]}",) if event else ())


def test_new_vs_discovered_then_stable():
    s = Scenario()
    s.rel("tsmc", "apple", T0, valid_from=T0.date() - 5 * D)  # real new relationship
    s.rel("asml", "tsmc", T0, valid_from=date(2015, 1, 1))  # long-standing, newly discovered
    s.rel("amd", "meta", T0, valid_from=None)  # start unknown
    intel = IntelIndex(s.ledger)
    assert intel.status(rid("tsmc", "apple"), T0 + D) is RelationshipStatus.NEW
    assert intel.status(rid("asml", "tsmc"), T0 + D) is RelationshipStatus.DISCOVERED
    assert intel.status(rid("amd", "meta"), T0 + D) is RelationshipStatus.DISCOVERED
    assert intel.status(rid("tsmc", "apple"), T0 + 40 * D) is RelationshipStatus.STABLE
    assert intel.status(rid("tsmc", "apple"), T0 - D) is None  # not yet known


def test_strengthened_weakened_by_materiality_and_deals_point_in_time():
    s = Scenario()
    s.rel("tsmc", "apple", T0 - 100 * D, valid_from=date(2020, 1, 1))
    intel = IntelIndex(s.ledger)
    r = rid("tsmc", "apple")
    assert intel.add_materiality(MaterialityObservation("m1", r, Materiality.MEDIUM, T0 - 90 * D,
                                                        (ev(s, "m1", T0 - 90 * D),)))
    assert intel.add_materiality(MaterialityObservation("m2", r, Materiality.HIGH, T0, (ev(s, "m2", T0),)))
    assert intel.status(r, T0 - D) is RelationshipStatus.STABLE  # the increase is not yet known
    assert intel.status(r, T0 + D) is RelationshipStatus.STRENGTHENED
    assert intel.status(r, T0 + 45 * D) is RelationshipStatus.STABLE  # outside recent window
    assert intel.add_materiality(MaterialityObservation("m3", r, Materiality.LOW, T0 + 50 * D,
                                                        (ev(s, "m3", T0 + 50 * D),)))
    assert intel.status(r, T0 + 51 * D) is RelationshipStatus.WEAKENED
    assert intel.materiality_as_of(r, T0 + 10 * D) is Materiality.HIGH
    # Deals: expansion strengthens, reduction weakens; a cancelled rumor does not weaken.
    t = T0 + 100 * D
    for st, k in ((DealState.ANNOUNCED, 0), (DealState.ACTIVE, 1), (DealState.EXPANDED, 2)):
        assert intel.add_deal(deal(s, "dA", st, t + k * D))
    assert intel.status(r, t + 3 * D) is RelationshipStatus.STRENGTHENED
    assert intel.add_deal(deal(s, "dA", DealState.REDUCED, t + 4 * D))
    assert intel.status(r, t + 5 * D) is RelationshipStatus.WEAKENED
    t2 = t + 60 * D
    assert intel.add_deal(deal(s, "dB", DealState.RUMORED, t2))
    assert intel.add_deal(deal(s, "dB", DealState.CANCELLED, t2 + D))
    assert intel.status(r, t2 + 2 * D) is RelationshipStatus.STABLE


def test_ended_relationship():
    s = Scenario()
    s.rel("tsmc", "apple", T0 - 100 * D, valid_from=date(2020, 1, 1))
    s.rel("tsmc", "apple", T0, valid_from=None, valid_to=T0.date() + 10 * D)
    intel = IntelIndex(s.ledger)
    assert intel.status(rid("tsmc", "apple"), T0 + 5 * D) is not RelationshipStatus.ENDED
    assert intel.status(rid("tsmc", "apple"), T0 + 11 * D) is RelationshipStatus.ENDED


def test_deal_state_machine_rejects_invalid_transitions_but_keeps_them():
    s = Scenario()
    intel = IntelIndex(s.ledger)
    assert intel.add_deal(deal(s, "d1", DealState.RUMORED, T0))
    assert intel.add_deal(deal(s, "d1", DealState.NEGOTIATING, T0 + D))  # skipping forward is fine
    bad_back = deal(s, "d1", DealState.EXPECTED, T0 + 2 * D)
    assert not intel.add_deal(bad_back)
    assert not intel.add_deal(deal(s, "d1", DealState.EXPANDED, T0 + 3 * D))  # needs ACTIVE first
    assert not intel.add_deal(deal(s, "d1", DealState.EXPIRED, T0 + 3 * D))
    assert intel.add_deal(deal(s, "d1", DealState.CONFIRMED, T0 + 4 * D))
    assert intel.add_deal(deal(s, "d1", DealState.ACTIVE, T0 + 5 * D))
    assert intel.add_deal(deal(s, "d1", DealState.RENEWED, T0 + 6 * D))
    assert intel.add_deal(deal(s, "d1", DealState.EXPANDED, T0 + 7 * D))
    assert intel.add_deal(deal(s, "d1", DealState.EXPIRED, T0 + 8 * D))
    assert not intel.add_deal(deal(s, "d1", DealState.ACTIVE, T0 + 9 * D))  # terminal
    assert not intel.add_deal(deal(s, "d1", DealState.EXPANDED, T0 + 9 * D, src="asml"))  # parties changed
    assert not intel.add_deal(deal(s, "d2", DealState.EXPANDED, T0))  # post-active first
    assert not intel.add_deal(deal(s, "d3", DealState.RUMORED, T0, tgt="tsmc"))  # self deal
    assert not intel.add_deal(deal(s, "d4", DealState.RUMORED, T0, tgt="unknown"))
    assert intel.add_deal(deal(s, "d5", DealState.CONFIRMED, T0 + 20 * D))
    assert not intel.add_deal(deal(s, "d5", DealState.ACTIVE, T0 + 19 * D))  # out of order
    kept = {r.record.obs_id: r.reasons for r in intel.rejected}
    assert kept[bad_back.obs_id] == ("BACKWARD_OR_REPEATED_TRANSITION",)
    assert len(intel.rejected) == 9
    with pytest.raises(ValueError):
        intel.add_deal(bad_back)  # append-only ids
    assert intel.deal_states_as_of(T0 + 5 * D + timedelta(hours=1))["d1"].state is DealState.ACTIVE


def test_deal_evidence_is_point_in_time():
    s = Scenario()
    intel = IntelIndex(s.ledger)
    e = ev(s, "late", T0 + 5 * D)
    obs = DealObservation("x1", "d", RelationshipType.SUPPLY_CHAIN, IdentityRef(issuer_id("tsmc")),
                          IdentityRef(issuer_id("apple")), DealState.RUMORED, T0, (e,))
    assert not intel.add_deal(obs) and intel.rejected[0].reasons == (f"PIT_EVIDENCE_AFTER_OBSERVATION:{e}",)
    obs2 = DealObservation("x2", "d", RelationshipType.SUPPLY_CHAIN, IdentityRef(issuer_id("tsmc")),
                           IdentityRef(issuer_id("apple")), DealState.RUMORED, T0, ("evd_missing",))
    assert not intel.add_deal(obs2)


def test_deal_never_creates_or_removes_relationship_edges():
    s = Scenario()
    intel = IntelIndex(s.ledger)
    assert intel.add_deal(deal(s, "d1", DealState.CONFIRMED, T0))
    assert s.ledger.graph_as_of(T0 + D).edges == ()
    assert intel.status(rid("tsmc", "apple"), T0 + D) is None
    s.rel("tsmc", "apple", T0 + 2 * D)
    assert intel.add_deal(deal(s, "d1", DealState.CANCELLED, T0 + 3 * D))
    g = s.ledger.graph_as_of(T0 + 4 * D)
    assert len(g.edges) == 1 and g.edges[0].state.epistemic.value == "FACT"
    # Materiality needs an accepted relationship.
    assert not intel.add_materiality(MaterialityObservation("mx", rid("asml", "tsmc"), Materiality.HIGH, T0 + 5 * D,
                                                            (ev(s, "mx", T0 + 5 * D),)))


def test_timeline_is_ordered_and_point_in_time():
    s = Scenario()
    s.rel("tsmc", "apple", T0, valid_from=date(2023, 1, 1))
    intel = IntelIndex(s.ledger)
    r = rid("tsmc", "apple")
    intel.add_materiality(MaterialityObservation("m1", r, Materiality.HIGH, T0 + D, (ev(s, "tm1", T0 + D),)))
    intel.add_deal(deal(s, "d1", DealState.ANNOUNCED, T0 + 2 * D))
    s.rel("tsmc", "apple", T0 + 3 * D, valid_from=None, valid_to=date(2025, 1, 1))
    full = intel.timeline(r, T0 + 10 * D)
    assert [x.kind for x in full] == ["STATE", "MATERIALITY", "DEAL", "STATE"]
    assert full[-1].detail_b == "2025-01-01"
    assert [x.kind for x in intel.timeline(r, T0 + D + timedelta(hours=1))] == ["STATE", "MATERIALITY"]


def test_presentation_badges_width_cards_and_priority():
    s = standard()
    intel = IntelIndex(s.ledger)
    as_of = T0 + 30 * D
    crit = rid("tsmc", "amd")  # hidden (+N) under the P1 recency order
    intel.add_materiality(MaterialityObservation("mc", crit, Materiality.CRITICAL, T0 + 20 * D,
                                                 (ev(s, "mc", T0 + 20 * D),)))
    intel.add_deal(deal(s, "dd", DealState.CONFIRMED, T0 + 21 * D, src="asml", tgt="tsmc", event=True))
    news = NewsIndex(s.lin)
    focus = ViewState(focus_node_id="issuer:issuer_tsmc")
    p1 = build_view_model(s.ledger, news, as_of, focus)
    p2 = build_view_model(s.ledger, news, as_of, focus, priority=intel_priority(intel, as_of))
    assert p1.network.edges[0].relationship_id != crit and p2.network.edges[0].relationship_id == crit
    assert {e.relationship_id for e in p1.network.edges} != {e.relationship_id for e in p2.network.edges}
    x = intel_extras(intel, p2)
    assert x.edge_width[crit] == 5.0
    assert all(len(b) <= 2 for b in x.edge_badges.values())
    assert x.edge_badges[rid("asml", "tsmc")][-1] == "DEAL_CONFIRMED"
    deal_event = [e for e in s.lin.events if e.startswith("evt_deal")][-1]
    assert x.card_badges[deal_event] == ("DEAL_CONFIRMED",)
    assert "IMP_CRITICAL" in x.card_badges["evt_r3"]
    # P2 never changes epistemic status of edges.
    ep1 = {e.relationship_id: e.epistemic for e in p1.network.edges}
    ep2 = {e.relationship_id: e.epistemic for e in p2.network.edges}
    assert all(ep1[k] == ep2[k] for k in ep1.keys() & ep2.keys())


def test_intel_package_boundaries():
    for f in INTEL_PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    assert not (node.module or "").startswith("investment_system"), f.name
                else:
                    assert node.level in (1, 2), f.name
                    if node.level == 2:
                        assert (node.module or "").split(".")[0] in {"gate", "ledger", "model", "network"}, f.name
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("investment_system") for a in node.names), f.name
