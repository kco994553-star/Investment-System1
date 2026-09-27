"""RIG P1 Basic Network — News | Network over one model, relationship visuals, focus/expansion, page."""
import ast
import json
import re
from dataclasses import fields
from datetime import timedelta
from pathlib import Path

import pytest

from investment_system.rig.model import EpistemicStatus, RelationshipType
from investment_system.rig.network.labels import Language, term
from investment_system.rig.network.render import PageExtras, render_page
from investment_system.rig.network.views import (
    EventLink,
    EventPresentation,
    NewsIndex,
    NewsStatus,
    ViewFilter,
    ViewKind,
    ViewState,
    Viewport,
    build_view_model,
    neighborhood,
    switch_view,
)
from tests.rig_fixtures import T0, standard

LATE = T0 + timedelta(days=30)
NET_PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "rig" / "network"


def _news(s):
    return NewsIndex(s.lin)


def test_same_information_two_views_share_ids():
    s = standard()
    vm = build_view_model(s.ledger, _news(s), LATE)
    edge_ids = {e.relationship_id for e in vm.network.edges}
    node_issuers = {n.issuer_id for n in vm.network.nodes}
    linked = [c for c in vm.cards if c.relationship_ids]
    assert linked and all(set(c.relationship_ids) <= edge_ids for c in linked)
    assert set().union(*(c.issuer_ids for c in linked)) <= node_issuers
    graph_ids = {e.relationship.relationship_id for e in s.ledger.graph_as_of(LATE).edges}
    assert edge_ids == graph_ids  # no second relationship store


def test_switch_view_preserves_scope_filter_focus_and_viewport():
    st = ViewState(filters=ViewFilter(frozenset({RelationshipType.CUSTOMER})), focus_node_id="issuer:issuer_tsmc",
                   expansion_steps=1, viewport=Viewport(2.0, 10.0, -5.0))
    net = switch_view(st, ViewKind.NETWORK)
    assert net.view is ViewKind.NETWORK
    assert (net.filters, net.focus_node_id, net.expansion_steps, net.viewport) == (
        st.filters, st.focus_node_id, st.expansion_steps, st.viewport)
    assert switch_view(net, ViewKind.NEWS) == st
    with pytest.raises(ValueError):
        Viewport(zoom=0.0)


def test_filters_apply_identically_to_both_views():
    s = standard()
    only_comp = ViewState(filters=ViewFilter(frozenset({RelationshipType.COMPETITOR})))
    vm = build_view_model(s.ledger, _news(s), LATE, only_comp)
    assert {e.relationship_type for e in vm.network.edges} == {RelationshipType.COMPETITOR}
    rel_ids = {e.relationship_id for e in vm.network.edges}
    assert all(set(c.relationship_ids) <= rel_ids for c in vm.cards)
    facts_only = ViewState(filters=ViewFilter(epistemic=frozenset({EpistemicStatus.FACT})))
    vm2 = build_view_model(s.ledger, _news(s), LATE, facts_only)
    assert all(e.epistemic is EpistemicStatus.FACT for e in vm2.network.edges)


def test_relationship_visual_contract():
    s = standard()
    edges = {(e.source_node_id, e.target_node_id): e for e in build_view_model(s.ledger, _news(s), LATE).network.edges}
    sup = edges[("issuer:issuer_tsmc", "issuer:issuer_apple")]
    assert (sup.line, sup.arrow) == ("SOLID", True)
    inf = edges[("issuer:issuer_skhynix", "issuer:issuer_nvidia")]
    assert (inf.line, inf.arrow) == ("DASHED", True)
    comp = [e for e in edges.values() if e.relationship_type is RelationshipType.COMPETITOR][0]
    assert comp.arrow is False
    assert {e.relationship_type for e in edges.values()} == set(RelationshipType)


def test_focus_shows_core_relationships_and_collapses_the_rest():
    s = standard()
    focus = "issuer:issuer_tsmc"  # 9 customers + ASML + Samsung = 11 relationships
    vm = build_view_model(s.ledger, _news(s), LATE, ViewState(view=ViewKind.NETWORK, focus_node_id=focus))
    assert len(vm.network.edges) == 8 and vm.network.hidden_edge_count == 3
    assert all(focus in (e.source_node_id, e.target_node_id) for e in vm.network.edges)
    ctr = [n for n in vm.network.nodes if n.node_id == focus][0]
    assert (ctr.x, ctr.y) == (500.0, 500.0)
    vm2 = build_view_model(s.ledger, _news(s), LATE, ViewState(focus_node_id=focus, expansion_steps=1))
    assert len(vm2.network.edges) == 11 and vm2.network.hidden_edge_count == 0
    assert vm.network.neighbor_order[focus][:8] == [e.relationship_id for e in vm.network.edges]
    with pytest.raises(ValueError):
        neighborhood(list(vm.network.edges), focus, 9, 0)
    # Facts are ordered before inferences.
    nv = build_view_model(s.ledger, _news(s), LATE, ViewState(focus_node_id="issuer:issuer_nvidia")).network.edges
    assert nv[-1].epistemic is EpistemicStatus.SUPPORTED_INFERENCE


def test_news_status_grouping_and_duplicates():
    s = standard()
    news = _news(s)
    base = "evt_r1"
    s.event("upd", T0 + timedelta(days=20), sources=3)
    s.event("fol", T0 + timedelta(days=21))
    s.event("dup", T0 + timedelta(days=22))
    news.add_link(EventLink("evt_upd", base, NewsStatus.UPDATE, T0 + timedelta(days=20)))
    news.add_link(EventLink("evt_fol", base, NewsStatus.FOLLOW_UP, T0 + timedelta(days=21)))
    news.add_link(EventLink("evt_dup", base, NewsStatus.DUPLICATE, T0 + timedelta(days=22)))
    news.add_presentation(EventPresentation("evt_upd", "TSMC expands Apple order", ("line 1", "line 2"),
                                            T0 + timedelta(days=20)))
    cards = {c.event_id: c for c in build_view_model(s.ledger, news, LATE).cards}
    assert cards["evt_r1"].status is NewsStatus.NEW
    assert cards["evt_upd"].status is NewsStatus.UPDATE and cards["evt_upd"].source_count == 3
    assert cards["evt_upd"].headline == "TSMC expands Apple order"
    assert cards["evt_fol"].status is NewsStatus.FOLLOW_UP and cards["evt_fol"].headline == "relationship reported"
    assert "evt_dup" not in cards
    from investment_system.rig.network.views import build_cards
    g = s.ledger.graph_as_of(LATE)
    assert "evt_dup" in {c.event_id for c in build_cards(s.ledger, news, g, ViewState(), include_duplicates=True)}
    with pytest.raises(ValueError):
        EventLink("evt_x", "evt_x", NewsStatus.UPDATE, T0)
    with pytest.raises(ValueError):
        EventLink("evt_a", "evt_b", NewsStatus.NEW, T0)
    with pytest.raises(ValueError):
        news.add_link(EventLink("evt_r1", "evt_upd", NewsStatus.UPDATE, LATE))  # parent is later than child
    with pytest.raises(ValueError):
        EventPresentation("evt_r1", "h", ("1", "2", "3", "4"), T0)


def test_views_are_point_in_time():
    s = standard()
    news = _news(s)
    s.event("later", T0 + timedelta(days=20))
    news.add_link(EventLink("evt_later", "evt_r1", NewsStatus.UPDATE, T0 + timedelta(days=25)))
    early = T0 + timedelta(days=3, hours=1)
    vm = build_view_model(s.ledger, news, early)
    assert {c.event_id for c in vm.cards} == {"evt_r1", "evt_r2", "evt_r3", "evt_r4"}
    assert len(vm.network.edges) == 4
    mid = build_view_model(s.ledger, news, T0 + timedelta(days=22))
    assert {c.event_id: c.status for c in mid.cards}["evt_later"] is NewsStatus.NEW  # link not yet known
    assert {c.event_id: c.status for c in build_view_model(s.ledger, news, LATE).cards}["evt_later"] \
        is NewsStatus.UPDATE


def test_untraceable_event_is_not_shown():
    s = standard()
    from investment_system.rig.model import EconomicEventKind, NewsEvent
    s.lin.add_event(NewsEvent("evt_orphan", EconomicEventKind.CONTRACT, ("clm_missing",), T0))
    assert "evt_orphan" not in {c.event_id for c in build_view_model(s.ledger, _news(s), LATE).cards}


def _payload(page):
    return json.loads(re.search(r'<script type="application/json" id="rig-data">(.*?)</script>', page, re.S)
                      .group(1).replace("<\\/", "</"))


def test_page_is_deterministic_escaped_and_language_only_changes_labels():
    s = standard()
    news = _news(s)
    s.event("xss", T0 + timedelta(days=16))
    news.add_presentation(EventPresentation("evt_xss", "<script>alert(1)</script>", ("a</script>b",),
                                            T0 + timedelta(days=16)))
    vm = build_view_model(s.ledger, news, LATE)
    pages = {lang: render_page(vm, lang) for lang in Language}
    assert render_page(vm, Language.KO) == pages[Language.KO]
    assert "<script>alert(1)</script>" not in pages[Language.KO] and "&lt;script&gt;" in pages[Language.KO]
    datas = [_payload(p) for p in pages.values()]
    for d in datas:
        d.pop("lang")
    assert datas[0] == datas[1] == datas[2]
    assert term("network", Language.KO) == "관계망" and term("network", Language.EN_KO) == "Network (관계망)"
    p = pages[Language.KO]
    assert 'id="pane-NEWS"' in p and 'id="pane-NETWORK"' in p and "addEventListener('wheel'" in p
    assert "pointermove" in p and "dblclick" in p and "⌂" in p
    assert p.count("<line ") == len(vm.network.edges) and p.count("data-event=") == len(vm.cards)
    extras = PageExtras(edge_badges={e.relationship_id: ("b1", "b2", "b3") for e in vm.network.edges},
                        terms={"b1": ("BadgeOne", "B1"), "b2": ("BadgeTwo", "B2"), "b3": ("BadgeThree", "B3")})
    lines = "".join(re.findall(r"<line .*?</line>", render_page(vm, Language.EN, extras)))
    assert "BadgeOne" in lines and "BadgeTwo" in lines and "BadgeThree" not in lines  # max 2 edge badges


def test_no_scores_or_trading_fields_in_view_model():
    from investment_system.rig.network import views
    for cls in (views.NewsCard, views.NetNode, views.NetEdge, views.NetworkView, views.RIGViewModel):
        names = {f.name for f in fields(cls)}
        tokens = {t for n in names for t in n.split("_")}
        assert not tokens & {"score", "buy", "sell", "hold", "rating", "attractiveness"}, (cls, tokens)


def test_network_package_boundaries():
    for f in NET_PKG.glob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                mod = ("." * node.level) + (node.module or "")
                if node.level == 0:
                    assert not (node.module or "").startswith("investment_system"), (f.name, mod)
                    continue
                assert node.level in (1, 2), (f.name, mod)  # only rig-internal relative imports
                if node.level == 2:
                    assert (node.module or "").split(".")[0] in {"gate", "ledger", "model"}, (f.name, mod)
            elif isinstance(node, ast.Import):
                assert not any(a.name.startswith("investment_system") for a in node.names), f.name
