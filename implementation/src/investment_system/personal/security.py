"""Security identity (PIL §12). Broker symbols are never primary keys; an internal security_id is assigned only when the
mapping is certain. Uncertain -> fail-closed. Similar tickers are never auto-mapped.

C-25: security_id is NOT unified with the existing company_id (C-06/D-27). A link to company_id is a separate, explicit,
reviewed record (CompanyLink) and is not created here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class SecurityIdentifiers:
    ticker: Optional[str] = None
    exchange: Optional[str] = None  # MIC or exchange code
    share_class: Optional[str] = None
    cik: Optional[str] = None
    isin: Optional[str] = None
    figi: Optional[str] = None


@dataclass(frozen=True)
class SecurityRecord:
    """One internal security with the identifiers valid during [effective_from, effective_to)."""

    security_id: str
    identifiers: SecurityIdentifiers
    effective_from: date
    effective_to: Optional[date] = None

    def active_on(self, d: date) -> bool:
        return self.effective_from <= d and (self.effective_to is None or d < self.effective_to)


@dataclass(frozen=True)
class CompanyLink:
    """Explicit security_id -> legacy company_id link. Placeholder contract for C-25; status stays PROPOSED until the
    identifier model is decided (no automatic creation)."""

    security_id: str
    company_id: str
    evidence: str
    status: str = "PROPOSED"


@dataclass(frozen=True)
class Resolution:
    status: ResolutionStatus
    security_id: Optional[str] = None
    matched_on: Optional[str] = None
    candidates: tuple[str, ...] = field(default_factory=tuple)
    reason: Optional[str] = None


def _norm(x: Optional[str]) -> Optional[str]:
    return x.strip().upper() if x and x.strip() else None


class InMemorySecurityResolver:
    """Deterministic resolver over explicit SecurityRecords.

    Strong keys (each alone may resolve): ISIN, FIGI. Otherwise ticker + exchange must both match, plus share_class when
    the record has one. A ticker alone, or any key matching more than one active record, never resolves."""

    def __init__(self, records: list[SecurityRecord]):
        keys = [(r.security_id, r.effective_from) for r in records]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate security_id/effective_from")
        self._records = list(records)

    def resolve(self, ident: SecurityIdentifiers, on: date) -> Resolution:
        active = [r for r in self._records if r.active_on(on)]
        for key in ("isin", "figi"):
            v = _norm(getattr(ident, key))
            if v:
                hits = sorted({r.security_id for r in active if _norm(getattr(r.identifiers, key)) == v})
                if len(hits) == 1:
                    return Resolution(ResolutionStatus.RESOLVED, hits[0], key)
                if len(hits) > 1:
                    return Resolution(ResolutionStatus.AMBIGUOUS, candidates=tuple(hits), reason=f"{key} matches several")
                return Resolution(ResolutionStatus.UNRESOLVED, reason=f"{key} not found")  # a strong key that misses is not retried by ticker
        t, x = _norm(ident.ticker), _norm(ident.exchange)
        if not t or not x:
            return Resolution(ResolutionStatus.UNRESOLVED, reason="ticker alone is not an identity (exchange required)")
        hits = sorted({r.security_id for r in active if _norm(r.identifiers.ticker) == t and _norm(r.identifiers.exchange) == x
                       and (_norm(r.identifiers.share_class) is None or _norm(r.identifiers.share_class) == _norm(ident.share_class))})
        if len(hits) == 1:
            return Resolution(ResolutionStatus.RESOLVED, hits[0], "ticker+exchange")
        if len(hits) > 1:
            return Resolution(ResolutionStatus.AMBIGUOUS, candidates=tuple(hits), reason="ticker+exchange matches several")
        return Resolution(ResolutionStatus.UNRESOLVED, reason="no active record for ticker+exchange")
