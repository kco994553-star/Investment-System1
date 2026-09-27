"""Shared RIG test scenario builders (test double for upstream identity; not a RIG identity universe)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from investment_system.contracts.global_universe import IssuerIdentity
from investment_system.rig.gate import LineageIndex
from investment_system.rig.ledger import RelationshipLedger
from investment_system.rig.model import (
    Claim,
    ClaimPolarity,
    EconomicEventKind,
    EdgeDirection,
    EpistemicStatus,
    Evidence,
    IdentityRef,
    NewsEvent,
    RelationshipCandidate,
    RelationshipType,
    SourceKind,
    SourceRef,
)

UTC = timezone.utc
T0 = datetime(2024, 3, 1, 14, tzinfo=UTC)
NAMES = {
    "tsmc": "TSMC", "apple": "Apple", "nvidia": "NVIDIA", "amd": "AMD", "asml": "ASML", "intel": "Intel",
    "samsung": "Samsung Electronics", "skhynix": "SK hynix", "microsoft": "Microsoft", "meta": "Meta",
    "google": "Alphabet", "amazon": "Amazon", "broadcom": "Broadcom", "qualcomm": "Qualcomm",
}


class Ids:
    def __init__(self, issuers):
        self._i = {x.issuer_id: x for x in issuers}

    def issuer(self, i):
        return self._i.get(i)

    def security(self, s):
        return None

    def listing(self, x):
        return None


def issuer_id(short):
    return f"issuer_{short}"


IDS = Ids([IssuerIdentity(issuer_id(k), v, "US") for k, v in NAMES.items()])


class Scenario:
    def __init__(self):
        self.lin = LineageIndex()
        self.ledger = RelationshipLedger(IDS, self.lin)
        self.n = 0

    def event(self, tag, at, kind=SourceKind.PRIMARY_DISCLOSURE, polarity=ClaimPolarity.AFFIRMS,
              sources=1, statement="relationship reported", ekind=EconomicEventKind.CONTRACT):
        ev_ids = []
        for i in range(sources):
            self.lin.add_source(SourceRef(f"src_{tag}_{i}", kind, f"pub{i}", at, f"raw:{tag}:{i}"))
            self.lin.add_evidence(Evidence(f"evd_{tag}_{i}", f"src_{tag}_{i}", "p.1", at))
            ev_ids.append(f"evd_{tag}_{i}")
        self.lin.add_claim(Claim(f"clm_{tag}", tuple(ev_ids), statement, polarity, at))
        self.lin.add_event(NewsEvent(f"evt_{tag}", ekind, (f"clm_{tag}",), at, at.date()))
        return f"evt_{tag}"

    def rel(self, src, tgt, at, *, rtype=RelationshipType.SUPPLY_CHAIN, epistemic=EpistemicStatus.FACT,
            tag=None, valid_from=date(2023, 1, 1), valid_to=None, event=None, decided=None, **ekw):
        self.n += 1
        tag = tag or f"r{self.n}"
        ev = event or self.event(tag, at, **ekw)
        direction = EdgeDirection.UNDIRECTED if rtype is RelationshipType.COMPETITOR else \
            EdgeDirection.UPSTREAM_TO_DOWNSTREAM
        c = RelationshipCandidate(
            f"cand_{tag}", rtype, direction, ClaimPolarity.AFFIRMS, epistemic, src, tgt,
            IdentityRef(issuer_id(src)), IdentityRef(issuer_id(tgt)), (ev,), at, Decimal("0.8"),
            valid_from, valid_to)
        return self.ledger.submit(c, decided or at)


def standard():
    """TSMC hub: supplies 9 customers; competitors; one inference; ASML upstream."""
    s = Scenario()
    for i, cust in enumerate(["apple", "nvidia", "amd", "qualcomm", "broadcom", "intel", "google", "amazon",
                              "microsoft"]):
        s.rel("tsmc", cust, T0 + timedelta(days=i))
    s.rel("asml", "tsmc", T0 + timedelta(days=12))
    s.rel("samsung", "tsmc", T0 + timedelta(days=13), rtype=RelationshipType.COMPETITOR)
    s.rel("skhynix", "nvidia", T0 + timedelta(days=14), epistemic=EpistemicStatus.SUPPORTED_INFERENCE,
          kind=SourceKind.COMMUNITY)
    s.rel("nvidia", "meta", T0 + timedelta(days=15), rtype=RelationshipType.VALUE_CHAIN)
    s.rel("broadcom", "google", T0 + timedelta(days=15, hours=1), rtype=RelationshipType.CUSTOMER)
    return s
