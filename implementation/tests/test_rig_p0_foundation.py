"""RIG P0 Foundation (RIG_NEWS_ARCH_v0.1) — identity, PIT, lineage, gate, Fact/Inference, boundaries."""
import ast
from dataclasses import fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from investment_system.contracts.global_universe import IssuerIdentity, ListingIdentity, SecurityIdentity
from investment_system.contracts.universe import DataEvent, EventKind
from investment_system.rig.adapter import to_data_event
from investment_system.rig.gate import GateCategory, GateOutcome, LineageIndex, LineagePITError
from investment_system.rig.ledger import RelationshipLedger
from investment_system.rig.model import (
    Claim,
    ClaimPolarity,
    EconomicEvent,
    EconomicEventKind,
    Edge,
    EdgeDirection,
    EpistemicStatus,
    Evidence,
    IdentityRef,
    NewsEvent,
    Node,
    RelationshipCandidate,
    RelationshipState,
    RelationshipType,
    SourceKind,
    SourceRef,
)
from investment_system.universe.events import IncrementalEngine, dirty_from_events

UTC = timezone.utc
T0 = datetime(2024, 3, 1, 14, tzinfo=UTC)
RIG_PKG = Path(__file__).resolve().parents[1] / "src" / "investment_system" / "rig"


class Ids:
    """Test double for the upstream (Track A-owned) identity records; not a RIG universe."""

    def __init__(self, issuers=(), securities=(), listings=()):
        self._i = {x.issuer_id: x for x in issuers}
        self._s = {x.security_id: x for x in securities}
        self._l = {x.listing_id: x for x in listings}

    def issuer(self, i):
        return self._i.get(i)

    def security(self, s):
        return self._s.get(s)

    def listing(self, x):
        return self._l.get(x)


TSMC = IssuerIdentity("issuer_tsmc", "Taiwan Semiconductor Manufacturing", "TW", (("CIK", "0001046179"),))
AAPL = IssuerIdentity("issuer_apple", "Apple Inc.", "US", (("CIK", "0000320193"),))
NVDA = IssuerIdentity("issuer_nvidia", "NVIDIA Corp.", "US", (("CIK", "0001045810"),))
AAPL_SEC = SecurityIdentity("security_aapl_common", AAPL.issuer_id, "COMMON_STOCK")
AAPL_LST = ListingIdentity("listing_aapl_xnas", AAPL_SEC.security_id, "AAPL", "XNAS", "USD", date(1980, 12, 12))
IDS = Ids((TSMC, AAPL, NVDA), (AAPL_SEC,), (AAPL_LST,))


def ref(issuer, security=None, listing=None):
    return IdentityRef(issuer.issuer_id, security, listing)


def world(tag, at, kind=SourceKind.PRIMARY_DISCLOSURE, polarity=ClaimPolarity.AFFIRMS, cls=NewsEvent, index=None):
    """Register Source -> Evidence -> Claim -> Event at time ``at``; returns (index, event_id)."""
    lin = index or LineageIndex()
    lin.add_source(SourceRef(f"src_{tag}", kind, "publisher", at, f"raw:{tag}"))
    lin.add_evidence(Evidence(f"evd_{tag}", f"src_{tag}", "p.1", at))
    lin.add_claim(Claim(f"clm_{tag}", (f"evd_{tag}",), "A supplies B", polarity, at))
    lin.add_event(cls(f"evt_{tag}", EconomicEventKind.CONTRACT, (f"clm_{tag}",), at, at.date()))
    return lin, f"evt_{tag}"


def cand(cid, event_ids, at, *, src=TSMC, tgt=AAPL, rtype=RelationshipType.SUPPLY_CHAIN,
         direction=EdgeDirection.UPSTREAM_TO_DOWNSTREAM, polarity=ClaimPolarity.AFFIRMS,
         epistemic=EpistemicStatus.FACT, valid_from=date(2024, 1, 1), valid_to=None,
         source_ref="auto", target_ref="auto"):
    return RelationshipCandidate(
        cid, rtype, direction, polarity, epistemic, "TSM", "AAPL",
        ref(src) if source_ref == "auto" else source_ref,
        ref(tgt) if target_ref == "auto" else target_ref,
        tuple(event_ids), at, Decimal("0.9"), valid_from, valid_to)


def ledger(lin):
    return RelationshipLedger(IDS, lin)


def test_identity_refs_follow_issuer_security_listing_hierarchy():
    r = IdentityRef(AAPL.issuer_id, AAPL_SEC.security_id, AAPL_LST.listing_id)
    assert r.listing_id == "listing_aapl_xnas"
    with pytest.raises(ValueError):
        IdentityRef(AAPL.issuer_id, None, AAPL_LST.listing_id)  # listing without security
    lin, e = world("h", T0)
    bad_sec = SecurityIdentity("security_other", NVDA.issuer_id, "COMMON_STOCK")
    lg = RelationshipLedger(Ids((TSMC, AAPL, NVDA), (AAPL_SEC, bad_sec), (AAPL_LST,)), lin)
    d = lg.submit(cand("c1", [e], T0, target_ref=IdentityRef(AAPL.issuer_id, "security_other")), T0)
    assert d.outcome is GateOutcome.UNRESOLVED
    assert "TARGET_SECURITY_NOT_OF_ISSUER" in d.checks[0].reasons


def test_ticker_is_not_canonical_node_identity():
    assert "ticker" not in {f.name for f in fields(IdentityRef)}
    assert "ticker" not in {f.name for f in fields(Node)}
    # Same ticker on two issuers at different times -> two distinct nodes; node id is issuer-keyed.
    old = ListingIdentity("listing_x_old", "security_x_old", "XYZ", "XNYS", "USD", date(2000, 1, 1), date(2010, 1, 1))
    new = ListingIdentity("listing_x_new", "security_x_new", "XYZ", "XNYS", "USD", date(2012, 1, 1))
    assert old.ticker == new.ticker
    assert Node.for_issuer("issuer_old").node_id != Node.for_issuer("issuer_new").node_id
    lin, e = world("t", T0)
    g_edge_ids = ledger(lin)
    assert g_edge_ids.submit(cand("c1", [e], T0), T0).outcome is GateOutcome.ACCEPTED
    g = g_edge_ids.graph_as_of(T0)
    assert {n.node_id for n in g.nodes} == {"issuer:issuer_tsmc", "issuer:issuer_apple"}
    assert all("AAPL" not in n.node_id and "TSM" not in n.node_id for n in g.nodes)


def test_cik_is_not_a_security_identity():
    lin, e = world("cik", T0)
    d = ledger(lin).submit(cand("c1", [e], T0, target_ref=IdentityRef(AAPL.issuer_id, "0000320193")), T0)
    assert d.outcome is GateOutcome.UNRESOLVED
    assert "TARGET_ISSUER_IDENTIFIER_USED_AS_SECURITY" in d.checks[0].reasons


def test_unresolved_identity_fails_closed_and_is_preserved():
    lin, e = world("u", T0)
    lg = ledger(lin)
    d1 = lg.submit(cand("c1", [e], T0, target_ref=None), T0)
    d2 = lg.submit(cand("c2", [e], T0, target_ref=IdentityRef("issuer_unknown")), T0)
    assert d1.outcome is d2.outcome is GateOutcome.UNRESOLVED
    assert lg.graph_as_of(T0).edges == ()
    assert {c.candidate_id for c, _ in lg.preserved(GateOutcome.UNRESOLVED)} == {"c1", "c2"}


def test_historical_graph_enforces_available_at_and_never_backfills():
    # Relationship valid since 2020 but only publicly known at T0 (2024).
    lin, e = world("late", T0)
    lg = ledger(lin)
    lg.submit(cand("c1", [e], T0, valid_from=date(2020, 1, 1)), T0 + timedelta(days=400))
    assert lg.graph_as_of(datetime(2022, 6, 1, tzinfo=UTC)).edges == ()
    assert lg.graph_as_of(T0 - timedelta(seconds=1)).edges == ()
    assert len(lg.graph_as_of(T0).edges) == 1
    with pytest.raises(ValueError):
        lg.graph_as_of(datetime(2024, 3, 1))  # naive
    with pytest.raises(ValueError):
        lg.graph_as_of(T0, valid_on=date(2025, 1, 1))  # no projection into the future
    with pytest.raises(ValueError):
        Edge(lg.relationships[("SUPPLY_CHAIN", "issuer_tsmc", "issuer_apple")],
             lg.states[("SUPPLY_CHAIN", "issuer_tsmc", "issuer_apple")][0], T0 - timedelta(days=1))


def test_future_evidence_is_rejected():
    lin, e_now = world("now", T0)
    world("future", T0 + timedelta(days=5), index=lin)
    lg = ledger(lin)
    with pytest.raises(ValueError):
        lg.submit(cand("c0", ["evt_future"], T0 + timedelta(days=5)), T0)  # decide before available
    d = lg.submit(cand("c1", [e_now, "evt_future"], T0), T0 + timedelta(days=1))
    assert d.outcome is GateOutcome.PENDING and GateCategory.TEMPORAL in d.failed()
    with pytest.raises(LineagePITError):
        lin.trace(("evt_future",), T0)
    # Candidate claiming availability before its own event.
    d2 = lg.submit(cand("c2", ["evt_future"], T0 + timedelta(days=4)), T0 + timedelta(days=6))
    assert GateCategory.TEMPORAL in d2.failed() and "CANDIDATE_AVAILABLE_BEFORE_ITS_LINEAGE" in d2.checks[2].reasons
    # Evidence available before its source was published.
    lin.add_source(SourceRef("src_bad", SourceKind.NEWS, "p", T0 + timedelta(days=1), "raw:bad"))
    lin.add_evidence(Evidence("evd_bad", "src_bad", "p.1", T0))
    lin.add_claim(Claim("clm_bad", ("evd_bad",), "x", ClaimPolarity.AFFIRMS, T0))
    lin.add_event(NewsEvent("evt_bad", EconomicEventKind.CONTRACT, ("clm_bad",), T0))
    assert GateCategory.TEMPORAL in lg.submit(cand("c3", ["evt_bad"], T0), T0 + timedelta(days=2)).failed()


def test_temporal_reconstruction_start_confirm_end():
    lin, e1 = world("start", T0)
    world("confirm", T0 + timedelta(days=30), index=lin)
    world("end", T0 + timedelta(days=90), index=lin)
    lg = ledger(lin)
    assert lg.submit(cand("c1", [e1], T0, valid_from=date(2024, 2, 1)), T0).outcome is GateOutcome.ACCEPTED
    c2 = cand("c2", ["evt_confirm"], T0 + timedelta(days=30), valid_from=None)
    assert lg.submit(c2, T0 + timedelta(days=30)).outcome is GateOutcome.ACCEPTED
    c3 = cand("c3", ["evt_end"], T0 + timedelta(days=90), valid_from=None, valid_to=date(2024, 5, 1))
    assert lg.submit(c3, T0 + timedelta(days=90)).outcome is GateOutcome.ACCEPTED

    mid = lg.graph_as_of(T0 + timedelta(days=45)).edges[0].state
    assert mid.first_detected_at == T0 and mid.last_confirmed_at == T0 + timedelta(days=30)
    assert mid.valid_from == date(2024, 2, 1) and mid.valid_to is None
    # As known on day 45, the relationship was believed active; the later end is not back-filled.
    assert len(lg.graph_as_of(T0 + timedelta(days=45)).edges) == 1
    late = T0 + timedelta(days=100)
    assert lg.graph_as_of(late).edges == ()  # ended 2024-05-01
    past = lg.graph_as_of(late, valid_on=date(2024, 4, 1)).edges[0].state
    assert past.valid_to == date(2024, 5, 1) and past.first_detected_at == T0
    assert lg.graph_as_of(late, valid_on=date(2024, 1, 15)).edges == ()  # before valid_from
    assert len(lg.states[("SUPPLY_CHAIN", "issuer_tsmc", "issuer_apple")]) == 3  # append-only history
    # Unknown start is only known-valid from the day it became available.
    lin2, e = world("nostart", T0)
    lg2 = ledger(lin2)
    lg2.submit(cand("n1", [e], T0, valid_from=None), T0)
    assert lg2.graph_as_of(T0 + timedelta(days=1), valid_on=T0.date() - timedelta(days=1)).edges == ()
    # Backfill older than the latest state fails closed.
    world("old", T0 - timedelta(days=10), index=lin)
    d = lg.submit(cand("c4", ["evt_old"], T0 - timedelta(days=10)), late)
    assert d.outcome is GateOutcome.PENDING and "OUT_OF_ORDER_OLDER_THAN_LATEST_STATE" in d.checks[2].reasons


def test_fact_and_inference_are_separate_and_never_auto_promoted():
    lin, e1 = world("inf", T0, kind=SourceKind.COMMUNITY)
    world("fact", T0 + timedelta(days=10), index=lin)
    world("sig", T0, index=lin)
    lg = ledger(lin)
    # COMMUNITY-only lineage cannot be a FACT.
    d0 = lg.submit(cand("c0", [e1], T0), T0)
    assert d0.outcome is GateOutcome.PENDING and "FACT_REQUIRES_PRIMARY_OR_NEWS_SOURCE" in d0.checks[1].reasons
    d1 = lg.submit(cand("c1", [e1], T0, epistemic=EpistemicStatus.SUPPORTED_INFERENCE), T0)
    assert d1.outcome is GateOutcome.ACCEPTED
    g = lg.graph_as_of(T0 + timedelta(days=5))
    assert g.facts() == () and len(g.inferences()) == 1
    # UNVERIFIED_SIGNAL never becomes an edge.
    d2 = lg.submit(cand("c2", ["evt_sig"], T0, src=NVDA, epistemic=EpistemicStatus.UNVERIFIED_SIGNAL), T0)
    assert d2.outcome is GateOutcome.PENDING and "UNVERIFIED_SIGNAL_NOT_EDGE_ELIGIBLE" in d2.checks[1].reasons
    with pytest.raises(ValueError):
        RelationshipState("s", "r", EpistemicStatus.UNVERIFIED_SIGNAL, None, None, T0, T0, T0, ("e",), ("c",), "d",
                          Decimal("0.5"))
    # Only a new FACT candidate with its own evidence creates a FACT version; inference history is kept.
    d3 = lg.submit(cand("c3", ["evt_fact"], T0 + timedelta(days=10)), T0 + timedelta(days=10))
    assert d3.outcome is GateOutcome.ACCEPTED
    g2 = lg.graph_as_of(T0 + timedelta(days=11))
    assert len(g2.facts()) == 1 and g2.inferences() == ()
    assert lg.graph_as_of(T0 + timedelta(days=5)).inferences()[0].state.epistemic is EpistemicStatus.SUPPORTED_INFERENCE
    # An inference arriving after a FACT with the same interval does not downgrade it.
    world("inf2", T0 + timedelta(days=20), index=lin)
    d4 = lg.submit(cand("c4", ["evt_inf2"], T0 + timedelta(days=20), epistemic=EpistemicStatus.SUPPORTED_INFERENCE),
                   T0 + timedelta(days=20))
    assert d4.outcome is GateOutcome.PENDING and "SUBSUMED_BY_EXISTING_FACT" in d4.checks[4].reasons


def test_evidence_lineage_is_fully_traceable():
    lin, e = world("lin", T0, cls=EconomicEvent)
    lg = ledger(lin)
    lg.submit(cand("c1", [e], T0), T0 + timedelta(hours=1))
    edge = lg.graph_as_of(T0 + timedelta(days=1)).edges[0]
    tr = lg.trace(edge)
    assert [s.source_id for s in tr.lineage.sources] == ["src_lin"]
    assert [x.evidence_id for x in tr.lineage.evidence] == ["evd_lin"]
    assert [c.claim_id for c in tr.lineage.claims] == ["clm_lin"]
    assert [x.event_id for x in tr.lineage.events] == ["evt_lin"]
    assert [c.candidate_id for c in tr.candidates] == ["c1"]
    assert tr.decisions[0].outcome is GateOutcome.ACCEPTED
    assert {c.category for c in tr.decisions[0].checks} == set(GateCategory)
    assert edge.state.decision_id == tr.decisions[0].decision_id
    # Missing lineage fails the Evidence gate and is preserved.
    d = lg.submit(cand("c2", ["evt_missing"], T0, src=NVDA), T0)
    assert d.outcome is GateOutcome.PENDING and GateCategory.EVIDENCE in d.failed()
    # Lineage is append-only: an id cannot be silently rewritten.
    with pytest.raises(ValueError):
        lin.add_evidence(Evidence("evd_lin", "src_lin", "p.2", T0))


def test_duplicate_candidate_is_preserved_not_double_counted():
    lin, e = world("dup", T0)
    world("dup2", T0 + timedelta(days=1), index=lin)
    lg = ledger(lin)
    assert lg.submit(cand("c1", [e], T0), T0).outcome is GateOutcome.ACCEPTED
    d = lg.submit(cand("c2", [e], T0), T0 + timedelta(hours=1))
    assert d.outcome is GateOutcome.PENDING and d.failed() == (GateCategory.DUPLICATE,)
    with pytest.raises(ValueError):
        lg.submit(cand("c1", [e], T0), T0)  # same candidate id resubmitted
    # Same relationship with new evidence = confirmation, not a second edge.
    assert lg.submit(cand("c3", ["evt_dup2"], T0 + timedelta(days=1)), T0 + timedelta(days=1)).outcome \
        is GateOutcome.ACCEPTED
    g = lg.graph_as_of(T0 + timedelta(days=2))
    assert len(g.edges) == 1 and g.edges[0].state.evidence_ids == ("evd_dup", "evd_dup2")
    assert g.edges[0].state.last_confirmed_at == T0 + timedelta(days=1)
    # Symmetric competitor edges deduplicate regardless of endpoint order.
    world("cmp", T0, index=lin)
    kw = dict(rtype=RelationshipType.COMPETITOR, direction=EdgeDirection.UNDIRECTED)
    assert lg.submit(cand("k1", ["evt_cmp"], T0, src=NVDA, tgt=AAPL, **kw), T0).outcome is GateOutcome.ACCEPTED
    assert lg.submit(cand("k2", ["evt_cmp"], T0, src=AAPL, tgt=NVDA, **kw), T0).failed() == (GateCategory.DUPLICATE,)


def test_contradictory_evidence_goes_pending_without_deleting_edges():
    lin, e = world("aff", T0)
    world("den", T0 + timedelta(days=3), polarity=ClaimPolarity.DENIES, index=lin)
    world("aff2", T0 + timedelta(days=6), index=lin)
    lg = ledger(lin)
    lg.submit(cand("c1", [e], T0), T0)
    d = lg.submit(cand("c2", ["evt_den"], T0 + timedelta(days=3), polarity=ClaimPolarity.DENIES),
                  T0 + timedelta(days=3))
    assert d.outcome is GateOutcome.PENDING and "DENIES_EXISTING_RELATIONSHIP" in d.checks[5].reasons
    assert len(lg.graph_as_of(T0 + timedelta(days=4)).edges) == 1  # not auto-deleted
    d2 = lg.submit(cand("c3", ["evt_aff2"], T0 + timedelta(days=6)), T0 + timedelta(days=6))
    assert d2.outcome is GateOutcome.PENDING and "PRIOR_DENIAL_ON_RECORD" in d2.checks[5].reasons
    # Mixed-polarity lineage behind one candidate is itself a contradiction.
    d3 = lg.submit(cand("c4", [e, "evt_den"], T0 + timedelta(days=3), src=NVDA), T0 + timedelta(days=7))
    assert "LINEAGE_POLARITY_CONFLICT" in d3.checks[5].reasons
    assert {c.candidate_id for c, _ in lg.preserved(GateOutcome.PENDING)} == {"c2", "c3", "c4"}


def test_direction_gate():
    lin, e = world("dir", T0)
    lg = ledger(lin)
    d1 = lg.submit(cand("c1", [e], T0, direction=EdgeDirection.UNKNOWN), T0)
    d2 = lg.submit(cand("c2", [e], T0, rtype=RelationshipType.COMPETITOR), T0)
    d3 = lg.submit(cand("c3", [e], T0, src=AAPL, tgt=AAPL), T0)
    assert all(d.outcome is GateOutcome.PENDING and GateCategory.DIRECTION in d.failed() for d in (d1, d2, d3))


def test_data_event_and_news_event_are_separate():
    assert not issubclass(NewsEvent, DataEvent) and not issubclass(EconomicEvent, DataEvent)
    assert {f.name for f in fields(DataEvent)} == {
        "event_id", "kind", "as_of", "available_at", "company_id", "source", "raw_fields"}
    lin, e = world("ad", T0)
    ev = lin.events[e]
    de = to_data_event(ev, "cmp_apple")
    assert isinstance(de, DataEvent) and de.kind is EventKind.NEWS and de.available_at == T0
    with pytest.raises(ValueError):
        to_data_event(ev, "")  # issuer_id is never silently used as company_id
    with pytest.raises(TypeError):
        to_data_event(de, "cmp_apple")
    # NEWS stays evidence-only: it does not dirty QGV/Technical, and future news is deferred.
    dirty = dirty_from_events([de])
    assert dirty["qgv"] == set() and dirty["technical"] == set() and dirty["evidence"] == {"cmp_apple"}
    eng = IncrementalEngine()
    calls = []
    from investment_system.contracts.universe import UniverseKind, UniverseMember, UniverseSnapshot
    uni = UniverseSnapshot("u", UniverseKind.EXPLICIT, T0, T0, (UniverseMember("cmp_apple", "AAPL"),))
    out = eng.process([de], T0 - timedelta(seconds=1), uni, lambda c, a: calls.append(c))
    assert out["deferred_not_available"] == ["rig:evt_ad"] and calls == []
    out = eng.process([de], T0, uni, lambda c, a: calls.append(c))
    assert out["qgv_recomputed"] == [] and calls == [] and eng.evidence == {"cmp_apple": ["rig:evt_ad"]}


def _imports(path):
    mods = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            mods.append(("." * node.level) + (node.module or ""))
        elif isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
    return mods


ALLOWED_RIG_IMPORTS = {"..contracts.global_universe", "..contracts.universe"}


def test_rig_does_not_import_track_b_or_other_tracks():
    files = sorted(RIG_PKG.glob("*.py"))
    assert {f.name for f in files} == {"__init__.py", "adapter.py", "gate.py", "ledger.py", "model.py"}
    for f in files:
        for m in _imports(f):
            if m.startswith(".."):
                assert m in ALLOWED_RIG_IMPORTS, (f.name, m)
            else:
                assert not m.startswith("investment_system"), (f.name, m)
                assert "personal" not in m, (f.name, m)
            assert "personal" not in m and "qgv" not in m and "validation" not in m, (f.name, m)


def test_no_other_package_depends_on_rig():
    src = RIG_PKG.parent
    for f in src.rglob("*.py"):
        if RIG_PKG in f.parents:
            continue
        assert not any("rig" in m.split(".") for m in _imports(f)), f
