"""Universe contracts. NEW IMPLEMENTATION.

C-18 RESOLVED 2026-09-23 (explicit user decision, not inferred by this engine):
Official Default Universe = US Market-Cap Top 500, PIT (as-of shares x as-of
price, ranked at each as_of; current roster never applied backward). See
OFFICIAL_UNIVERSE_* below and universe/sources.py:official_mcap500_snapshot.

S&P 500 history remains in the codebase as a Benchmark/Research candidate
(UniverseKind.SP500_HISTORY_CANDIDATE) -- kept, not deleted, not Official.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class UniverseKind(str, Enum):
    DECISION_REQUIRED = "DECISION_REQUIRED"
    RESEARCH_CANARY = "RESEARCH_CANARY"
    US_LISTINGS_WORKING = "US_LISTINGS_WORKING"
    EXPLICIT = "EXPLICIT"
    # C-18 RESOLVED 2026-09-23: this is now the Official Default Universe kind.
    US_MCAP_TOP500_OFFICIAL = "US_MCAP_TOP500_OFFICIAL"
    # Benchmark/Research only, kept per user instruction not to delete S&P code.
    SP500_HISTORY_CANDIDATE = "SP500_HISTORY_CANDIDATE"
    # Generic research builder (any N). n=500 promoted via official_mcap500_snapshot only.
    MCAP_TOP_N_CANDIDATE = "MCAP_TOP_N_CANDIDATE"


class UniversePolicyStatus(str, Enum):
    DECISION_REQUIRED = "DECISION_REQUIRED"
    RESEARCH = "RESEARCH"
    OFFICIAL = "OFFICIAL"


OFFICIAL_UNIVERSE_STATUS = UniversePolicyStatus.OFFICIAL
OFFICIAL_UNIVERSE_KIND = UniverseKind.US_MCAP_TOP500_OFFICIAL
OFFICIAL_UNIVERSE_METHOD = "PIT_SHARES_X_PIT_PRICE"
OFFICIAL_UNIVERSE_N = 500
OFFICIAL_UNIVERSE_DECIDED_AT = "2026-09-23"
OFFICIAL_UNIVERSE_DECIDED_BY = "user"  # explicit instruction, not inferred/auto-Officialized
OFFICIAL_UNIVERSE_NOTE = (
    "C-18 RESOLVED 2026-09-23 by explicit user decision: Official Default Universe "
    "is US Market-Cap Top 500, PIT (as-of shares x as-of price; current roster never "
    "applied backward). Leaderboard Spec v1.0 / Integrated Spec v1.7 listed 'US "
    "market-cap top 500 OR S&P 500' as candidates; S&P 500 is kept in the codebase as "
    "Benchmark/Research only (UniverseKind.SP500_HISTORY_CANDIDATE), not Official."
)


class EventKind(str, Enum):
    FUNDAMENTAL = "FUNDAMENTAL"
    PRICE = "PRICE"
    MACRO = "MACRO"
    NEWS = "NEWS"
    MEMBERSHIP = "MEMBERSHIP"


@dataclass(frozen=True)
class UniverseMember:
    company_id: str
    ticker: str
    entered_on: str | None = None
    # Exclusive: not a member on exited_on itself.
    exited_on: str | None = None
    cik: str | None = None


@dataclass(frozen=True)
class UniverseSnapshot:
    universe_id: str
    universe_kind: UniverseKind
    as_of: datetime
    available_at: datetime
    members: tuple[UniverseMember, ...]
    policy_status: UniversePolicyStatus = UniversePolicyStatus.RESEARCH
    source: str = "EXPLICIT"
    implementation_kind: str = "NEW IMPLEMENTATION"
    # DATED_INTERVALS | UNDATED_ROSTER | RECONSTRUCTED_LATER_VINTAGE
    membership_basis: str = "UNSPECIFIED"
    # True when membership cannot exclude names that joined after as_of.
    survivorship_risk: bool = False
    source_vintage: str | None = None

    def ids(self) -> tuple[str, ...]:
        return tuple(m.company_id for m in self.members)


@dataclass(frozen=True)
class DataEvent:
    event_id: str
    kind: EventKind
    as_of: datetime
    available_at: datetime
    company_id: str | None
    source: str
    raw_fields: tuple[str, ...] = ()
