"""RIG P3 Personal UX — 내 기업 scope, ★ 관심기업, My Groups, feed priority, related news, Attention, overlay."""
import ast
from dataclasses import fields
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from investment_system.rig.intel.intel import IntelIndex, Materiality, MaterialityObservation
from investment_system.rig.model import Relationship
from investment_system.rig.myview.prefs import (
    Actor,
    GroupAction,
    GroupOp,
    InterestAction,
    InterestOp,
    UserOrganization,
)
from investment_system.rig.myview.present import build_my_page
from investment_system.rig.myview.scope import (
    AttentionInput,
    Chip,
    FeedTier,
    MyViewState,
    Relevance,
    Scope,
    attention_inputs,
    build_sets,
    feed_order,
    feed_tiers,
    my_priority,
    overlay_rows,
    related_news,
    select,
    switch_my_view,
)
from investment_system.rig.network.views import NewsIndex, ViewKind, ViewState, Viewport, build_view_model
from tests.rig_fixtures import IDS, T0, issuer_id, standard

D = timedelta(days=1)
AS_OF = T0 + 30 * D
MY_PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "rig" / "myview"


class Holdings:
    def __init__(self, ids):
        self.ids = frozenset(issuer_id(i) for i in ids)

    def held_issuer_ids(self, as_of):
        return self.ids


def org_with(interest=(), groups=None):
    org = UserOrganization(IDS)
    k = 0
    for i in interest:
        k += 1
        org.record_interest(InterestAction(f"i{k}", InterestOp.ADD, issuer_id(i), T0 + k * timedelta(minutes=1),
                                           Actor.USER))
    for g, members in (groups or {}).items():
        k += 1
        org.record_group(GroupAction(f"g{k}", GroupOp.CREATE, g, T0 + k * timedelta(minutes=1), Actor.USER, name=g))
        for m in members:
            k += 1
            org.record_group(GroupAction(f"g{k}", GroupOp.ADD_MEMBER, g, T0 + k * timedelta(minutes=1), Actor.USER,
                                         issuer_id=issuer_id(m)))
    return org


def rid(src, tgt, rtype="SUPPLY_CHAIN"):
    return Relationship.for_key((rtype, issuer_id(src), issuer_id(tgt))).relationship_id


def test_interest_is_single_list_changed_only_by_explicit_user_actions():
    org = UserOrganization(IDS)
    org.record_interest(InterestAction("a1", InterestOp.ADD, issuer_id("apple"), T0, Actor.USER))
    org.record_interest(InterestAction("a2", InterestOp.ADD, issuer_id("nvidia"), T0 + D, Actor.USER))
    org.record_interest(InterestAction("a3", InterestOp.REMOVE, issuer_id("apple"), T0 + 2 * D, Actor.USER))
    assert org.interests_as_of(T0 + D) == {issuer_id("apple"), issuer_id("nvidia")}
    assert org.interests_as_of(T0 + 3 * D) == {issuer_id("nvidia")}
    assert org.interests_as_of(T0 - D) == frozenset()
    with pytest.raises(PermissionError):
        org.record_interest(InterestAction("s1", InterestOp.ADD, issuer_id("amd"), T0 + 4 * D, Actor.SYSTEM))
    with pytest.raises(ValueError):
        org.record_interest(InterestAction("x1", InterestOp.ADD, "issuer_unknown", T0 + 4 * D, Actor.USER))
    with pytest.raises(ValueError):
        org.record_interest(InterestAction("a1", InterestOp.ADD, issuer_id("amd"), T0 + 4 * D, Actor.USER))
    with pytest.raises(ValueError):
        org.record_interest(InterestAction("old", InterestOp.ADD, issuer_id("amd"), T0, Actor.USER))


def test_my_groups_are_many_to_many_organization_only():
    org = org_with(interest=["apple"], groups={"AI": ["nvidia", "tsmc", "apple"], "Foundry": ["tsmc"]})
    gs = org.groups_as_of(T0 + D)
    assert gs["AI"].members == {issuer_id("nvidia"), issuer_id("tsmc"), issuer_id("apple")}
    assert issuer_id("tsmc") in gs["Foundry"].members  # one company, many groups
    names = {f.name for f in fields(type(gs["AI"]))}
    assert names == {"group_id", "name", "members"}  # no weights / scores / classification
    at = T0 + 2 * D
    org.record_group(GroupAction("r1", GroupOp.RENAME, "AI", at, Actor.USER, name="AI chain"))
    org.record_group(GroupAction("r2", GroupOp.REMOVE_MEMBER, "AI", at, Actor.USER, issuer_id=issuer_id("apple")))
    org.record_group(GroupAction("r3", GroupOp.DELETE, "Foundry", at, Actor.USER))
    after = org.groups_as_of(at)
    assert after["AI"].name == "AI chain" and issuer_id("apple") not in after["AI"].members and "Foundry" not in after
    assert org.groups_as_of(T0 + D)["AI"].name == "AI"  # point-in-time
    with pytest.raises(PermissionError):
        org.record_group(GroupAction("s", GroupOp.CREATE, "Auto", at, Actor.SYSTEM, name="auto"))
    with pytest.raises(ValueError):
        org.record_group(GroupAction("r4", GroupOp.ADD_MEMBER, "Foundry", at, Actor.USER, issuer_id=issuer_id("amd")))


def test_scope_my_is_holdings_plus_interest_and_all_is_unrestricted():
    s = standard()
    sets = build_sets(s.ledger, Holdings(["apple"]), org_with(interest=["meta"]), AS_OF)
    assert sets.my == {issuer_id("apple"), issuer_id("meta")}
    vm = build_view_model(s.ledger, NewsIndex(s.lin), AS_OF)
    my = select(vm, sets, MyViewState())
    assert my.issuer_ids == {issuer_id(x) for x in ("apple", "meta", "tsmc", "nvidia")}  # + 1-hop related
    assert my.relationship_ids == {rid("tsmc", "apple"), rid("nvidia", "meta", "VALUE_CHAIN")}
    held_only = select(vm, sets, MyViewState(chips=frozenset({Chip.HELD})))
    assert held_only.issuer_ids == {issuer_id("apple")} and held_only.relationship_ids == frozenset()
    everything = select(vm, sets, MyViewState(scope=Scope.ALL))
    assert everything.relationship_ids == {e.relationship_id for e in vm.network.edges}
    assert everything.event_ids == {c.event_id for c in vm.cards}
    with pytest.raises(ValueError):
        build_sets(s.ledger, Holdings(["unknown"]), org_with(), AS_OF)  # fail closed


def test_group_chip_selects_group_members():
    s = standard()
    org = org_with(groups={"EUV": ["asml"]})
    sets = build_sets(s.ledger, Holdings([]), org, AS_OF)
    vm = build_view_model(s.ledger, NewsIndex(s.lin), AS_OF)
    sel = select(vm, sets, MyViewState(chips=frozenset({Chip.GROUP, Chip.RELATED}), group_id="EUV"))
    assert sel.issuer_ids == {issuer_id("asml"), issuer_id("tsmc")} and sel.relationship_ids == {rid("asml", "tsmc")}


def test_view_switch_preserves_scope_chips_group_and_viewport():
    st = MyViewState(base=ViewState(viewport=Viewport(1.7, 3.0, 4.0), focus_node_id="issuer:issuer_tsmc"),
                     scope=Scope.MY, chips=frozenset({Chip.HELD}), group_id="AI", overlay_on=True)
    net = switch_my_view(st, ViewKind.NETWORK)
    assert net.base.view is ViewKind.NETWORK
    assert (net.scope, net.chips, net.group_id, net.overlay_on, net.base.viewport, net.base.focus_node_id) == (
        st.scope, st.chips, st.group_id, st.overlay_on, st.base.viewport, st.base.focus_node_id)


def test_feed_priority_tiers_and_order():
    s = standard()
    intel = IntelIndex(s.ledger)
    s.event("m1", T0 + 20 * D)
    s.event("m2", T0 + 20 * D)
    intel.add_materiality(MaterialityObservation("m1", rid("tsmc", "apple"), Materiality.HIGH, T0 + 20 * D,
                                                 ("evd_m1_0",)))
    intel.add_materiality(MaterialityObservation("m2", rid("nvidia", "meta", "VALUE_CHAIN"), Materiality.CRITICAL,
                                                 T0 + 20 * D, ("evd_m2_0",)))
    sets = build_sets(s.ledger, Holdings(["apple", "intel"]), org_with(interest=["meta"]), AS_OF)
    vm = build_view_model(s.ledger, NewsIndex(s.lin), AS_OF)
    tiers = feed_tiers(vm, intel, sets, research_new=frozenset({issuer_id("google")}))
    assert tiers["evt_r1"] is FeedTier.HELD_IMPORTANT  # tsmc -> apple (held, HIGH)
    assert tiers["evt_r13"] is FeedTier.INTEREST_IMPORTANT  # nvidia -> meta (interest, CRITICAL)
    assert tiers["evt_r2"] is FeedTier.MY_HIGH_MATERIALITY_ONE_HOP  # tsmc -> nvidia; tsmc is a high 1-hop of apple
    assert tiers["evt_r6"] is FeedTier.MY_HIGH_MATERIALITY_ONE_HOP  # held but not important -> not tier 1
    assert tiers["evt_r14"] is FeedTier.RESEARCH_PRIORITY_NEW  # broadcom -> google (P4 hook)
    assert tiers["evt_m1"] is FeedTier.MARKET  # no relationship to My companies
    order = feed_order(vm, tiers)
    assert order[:2] == ("evt_r1", "evt_r13") and order[-1] in {e for e, t in tiers.items() if t is FeedTier.MARKET}


def test_network_priority_puts_my_relationships_after_critical_only():
    s = standard()
    intel = IntelIndex(s.ledger)
    s.event("mc", T0 + 20 * D)
    intel.add_materiality(MaterialityObservation("mc", rid("tsmc", "amd"), Materiality.CRITICAL, T0 + 20 * D,
                                                 ("evd_mc_0",)))
    s.event("mh", T0 + 20 * D)
    intel.add_materiality(MaterialityObservation("mh", rid("tsmc", "intel"), Materiality.HIGH, T0 + 20 * D,
                                                 ("evd_mh_0",)))
    sets = build_sets(s.ledger, Holdings(["nvidia"]), org_with(), AS_OF)
    vm = build_view_model(s.ledger, NewsIndex(s.lin), AS_OF, ViewState(focus_node_id="issuer:issuer_tsmc"),
                          priority=my_priority(intel, sets, AS_OF))
    ids = [e.relationship_id for e in vm.network.edges]
    assert ids[:3] == [rid("tsmc", "amd"), rid("tsmc", "nvidia"), rid("tsmc", "intel")]  # critical, mine, high


def test_related_news_and_attention_inputs():
    s = standard()
    intel = IntelIndex(s.ledger)
    sets = build_sets(s.ledger, Holdings(["meta"]), org_with(interest=["apple"]), AS_OF)
    vm = build_view_model(s.ledger, NewsIndex(s.lin), AS_OF)
    rel = {r.event_id: r.relation for r in related_news(vm, sets, issuer_id("nvidia"))}
    assert rel["evt_r13"] == "DIRECT" and rel["evt_r1"] == "RELATED"  # tsmc->apple via tsmc (1-hop of nvidia)
    ai = {a.event_id: a for a in attention_inputs(vm, s.ledger, intel, sets)}
    assert ai["evt_r13"].user_relevance is Relevance.HELD
    assert ai["evt_r1"].user_relevance is Relevance.INTEREST
    assert ai["evt_r2"].user_relevance is Relevance.ONE_HOP  # tsmc/nvidia are 1-hop of apple/meta
    assert ai["evt_r1"].confidence == Decimal("0.8")
    names = {f.name for f in fields(AttentionInput)}
    assert not names & {"channel", "delivery", "notify", "immediate", "digest", "score"}


class Overlay:
    def rows(self, issuer, as_of):
        return (("QGV", "read-only snapshot label"),)


def test_investment_overlay_is_off_by_default_and_read_only():
    s = standard()
    sets = build_sets(s.ledger, Holdings(["apple"]), org_with(), AS_OF)
    assert overlay_rows(Overlay(), sets, MyViewState(), AS_OF) == {}
    on = overlay_rows(Overlay(), sets, MyViewState(overlay_on=True), AS_OF)
    assert on == {issuer_id("apple"): (("QGV", "read-only snapshot label"),)}

    class Bad:
        def rows(self, issuer, as_of):
            return (("QGV", 0.73),)
    with pytest.raises(TypeError):
        overlay_rows(Bad(), sets, MyViewState(overlay_on=True), AS_OF)
    _, _, page = build_my_page(s.ledger, NewsIndex(s.lin), IntelIndex(s.ledger), Holdings(["apple"]), org_with(),
                               AS_OF, overlay_port=Overlay())
    assert 'id="overlay"' not in page
    _, _, page_on = build_my_page(s.ledger, NewsIndex(s.lin), IntelIndex(s.ledger), Holdings(["apple"]), org_with(),
                                  AS_OF, MyViewState(overlay_on=True), overlay_port=Overlay())
    assert 'id="overlay"' in page_on and "read-only snapshot label" in page_on


def test_page_marks_held_and_interest_nodes_and_orders_feed():
    s = standard()
    vm, sets, page = build_my_page(s.ledger, NewsIndex(s.lin), IntelIndex(s.ledger), Holdings(["apple"]),
                                   org_with(interest=["nvidia"]), AS_OF)
    assert '>◎</text>' in page and '>★</text>' in page
    assert 'data-scope="MY"' in page and 'data-chip="RELATED"' in page and 'id="rig-scope"' in page
    first_card = page.index('data-event="')
    assert page[first_card:first_card + 30].startswith('data-event="evt_r')


def test_myview_package_boundaries():
    for f in MY_PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    assert not (node.module or "").startswith("investment_system"), f.name
                else:
                    assert node.level in (1, 2), f.name
                    if node.level == 2:
                        assert (node.module or "").split(".")[0] in {"gate", "ledger", "model", "network",
                                                                      "intel"}, f.name
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("investment_system") for a in node.names), f.name
    # Track B stays untouched and is never imported by any RIG module.
    for f in (MY_PKG.parent).rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert "personal" not in (node.module or ""), f
