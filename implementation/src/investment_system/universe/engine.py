"""Generic Universe engine. NEW IMPLEMENTATION. Not Official S&P or top-500."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from ..contracts.universe import (
    OFFICIAL_UNIVERSE_DECIDED_AT,
    OFFICIAL_UNIVERSE_DECIDED_BY,
    OFFICIAL_UNIVERSE_KIND,
    OFFICIAL_UNIVERSE_METHOD,
    OFFICIAL_UNIVERSE_N,
    OFFICIAL_UNIVERSE_STATUS,
    UniverseKind,
    UniverseMember,
    UniversePolicyStatus,
    UniverseSnapshot,
)
from ..markets.us import US_LISTINGS

CANARY_IDS = ("nvda", "msft", "amzn", "avgo", "amd", "qcom", "lrcx", "intc")


def _day(value: str | None, field: str, cid: str) -> str | None:
    """Membership dates are compared as ISO strings, so the format must be strict."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError(f"membership {field} for {cid} is not ISO YYYY-MM-DD: {value!r}")


def validate_roster(roster: tuple[UniverseMember, ...]) -> None:
    """Reject rosters whose intervals would make as_of membership ambiguous."""
    by_id: dict[str, list[tuple[str, str]]] = {}
    for m in roster:
        start = _day(m.entered_on, "entered_on", m.company_id) or "0000-01-01"
        end = _day(m.exited_on, "exited_on", m.company_id) or "9999-12-31"
        if end <= start:
            raise ValueError(f"membership interval for {m.company_id} ends on/before it starts")
        by_id.setdefault(m.company_id, []).append((start, end))
    for cid, spans in by_id.items():
        spans.sort()
        for (_, e0), (s1, _) in zip(spans, spans[1:]):
            if s1 < e0:
                raise ValueError(f"overlapping membership intervals for {cid}")


def members_at(as_of: datetime, roster: tuple[UniverseMember, ...]) -> tuple[UniverseMember, ...]:
    """Point-in-time membership. Current roster is not applied backward."""
    validate_roster(roster)
    day = as_of.date().isoformat()
    out = []
    for m in roster:
        if m.entered_on and _day(m.entered_on, "entered_on", m.company_id) > day:
            continue
        if m.exited_on and _day(m.exited_on, "exited_on", m.company_id) <= day:
            continue
        out.append(m)
    return tuple(out)


def membership_basis(roster: tuple[UniverseMember, ...], as_of: datetime, source_vintage: str | None) -> tuple[str, bool]:
    """Label how trustworthy as_of membership is. Labels only; never alters members."""
    if roster and any(m.entered_on is None for m in roster):
        # Without entry dates a name that joined later cannot be excluded.
        return "UNDATED_ROSTER", True
    if source_vintage and _day(source_vintage, "source_vintage", "roster") > as_of.date().isoformat():
        # Dated intervals compiled later: no hindsight in dates, but the list itself is a later vintage.
        return "RECONSTRUCTED_LATER_VINTAGE", False
    return "DATED_INTERVALS", False


class UniverseEngine:
    def snapshot(
        self,
        as_of: datetime,
        *,
        roster: tuple[UniverseMember, ...] | None = None,
        kind: UniverseKind = UniverseKind.EXPLICIT,
        available_at: datetime | None = None,
        policy_status: UniversePolicyStatus | None = None,
        source: str = "EXPLICIT",
        source_vintage: str | None = None,
    ) -> UniverseSnapshot:
        roster = roster or tuple()
        members = members_at(as_of, roster)
        basis, surv = membership_basis(roster, as_of, source_vintage)
        if policy_status is UniversePolicyStatus.OFFICIAL:
            # C-18 RESOLVED: Official is minted in exactly one place —
            # universe/sources.py:official_mcap500_snapshot — never through this
            # generic constructor. That keeps every other caller unable to
            # self-declare Official by accident.
            raise ValueError(
                "snapshot() cannot mint OFFICIAL directly; use "
                "universe.sources.official_mcap500_snapshot()"
            )
        return UniverseSnapshot(
            universe_id=f"uni_{uuid4().hex[:12]}",
            universe_kind=kind,
            as_of=as_of,
            available_at=available_at or as_of,
            members=members,
            policy_status=policy_status or UniversePolicyStatus.RESEARCH,
            source=source,
            membership_basis=basis,
            survivorship_risk=surv,
            source_vintage=source_vintage,
        )

    def research_canary(self, as_of: datetime) -> UniverseSnapshot:
        roster = tuple(
            UniverseMember(cid, US_LISTINGS[cid]["yahoo"], cik=US_LISTINGS[cid]["cik"])
            for cid in CANARY_IDS
            if cid in US_LISTINGS
        )
        return self.snapshot(
            as_of,
            roster=roster,
            kind=UniverseKind.RESEARCH_CANARY,
            policy_status=UniversePolicyStatus.RESEARCH,
            source="CANARY",
        )

    def official_status(self) -> dict:
        # C-18 RESOLVED 2026-09-23: Official Default Universe is US mcap Top 500 PIT.
        # This function reports the decision; it does not itself mint an Official
        # snapshot -- that is universe/sources.py:official_mcap500_snapshot, the one
        # sanctioned path (see the OFFICIAL-status guard in snapshot() below).
        return {
            "official_universe_status": OFFICIAL_UNIVERSE_STATUS.value,
            "official_kind": OFFICIAL_UNIVERSE_KIND.value,
            "official_method": OFFICIAL_UNIVERSE_METHOD,
            "official_n": OFFICIAL_UNIVERSE_N,
            "decided_at": OFFICIAL_UNIVERSE_DECIDED_AT,
            "decided_by": OFFICIAL_UNIVERSE_DECIDED_BY,
            "sp500_equals_mcap500": False,
            "sp500_status": "BENCHMARK_RESEARCH_ONLY",
            "decision_required": False,
        }
