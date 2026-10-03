"""Bind stored Yahoo daily bars to an explicit session vintage.

The timestamp is a session identity only. It is not the time at which the
daily close became knowable. This module does not renumber the bars it has,
and it does not invent sessions for timestamps the vintage does not list.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from ..technical.pit_market import bars_from_yahoo_chart
from .calendar import CalendarVintage, _aware
from .errors import DuplicateSessionBar, ProvenanceMismatch, SessionContractError
from .listing import ListingEvidence

# Explicit vendor codes observed for US cash equities. Not a name parser.
YAHOO_EXCHANGE_MIC = {
    "NMS": "XNAS",
    "NYQ": "XNYS",
    "PCX": "ARCX",
}


@dataclass(frozen=True)
class BoundBar:
    observed_at: datetime
    session_date: str
    session_index: int
    close: float | None
    volume: float | None
    close_local: str
    eligible: bool

    def observation(self) -> dict:
        return {
            "observed_at": self.observed_at,
            "session_index": self.session_index,
            "close": self.close,
            "volume": self.volume,
        }

    def audit(self) -> dict:
        body = self.observation()
        body["session_date"] = self.session_date
        body["close_local"] = self.close_local
        body["observed_at"] = self.observed_at.isoformat()
        return body


@dataclass(frozen=True)
class SessionBinding:
    status: str
    reason_code: str | None
    calendar_id: str | None
    listing_id: str | None
    tzdata_version: str | None
    yahoo_sha256: str
    symbol: str | None
    eligible: tuple[BoundBar, ...]
    excluded_before_close: tuple[BoundBar, ...]


def listing_refusal(listings: tuple[ListingEvidence, ...] | list[ListingEvidence]) -> str | None:
    """More than one interval is not stitched. Reuse and venue changes stay split."""
    if len(listings) == 1:
        return None
    if len(listings) == 0:
        return "LISTING_UNVERIFIED"
    tickers = {item.listing.ticker for item in listings}
    securities = {item.listing.security_id for item in listings}
    mics = {item.listing.mic for item in listings}
    if len(mics) > 1:
        return "EXCHANGE_TRANSFER"
    if len(tickers) == 1 and len(securities) > 1:
        return "TICKER_REUSE"
    return "LISTING_UNVERIFIED"


def bind_yahoo_bars(
    raw_body: bytes,
    declared_sha256: str,
    *,
    decision_time: datetime,
    calendar: CalendarVintage,
    listing: ListingEvidence,
) -> SessionBinding:
    decision_time = _aware(decision_time, "decision_time")
    digest = _require_bytes(raw_body, declared_sha256, "Yahoo chart")
    if not calendar.admissible_at(decision_time):
        return _unbound("CALENDAR_NOT_ADMISSIBLE", digest, calendar, listing)
    if listing.available_at > decision_time:
        return _unbound("LISTING_UNVERIFIED", digest, calendar, listing)
    if listing.listing.mic != calendar.venue_mic:
        return _unbound("EXCHANGE_TRANSFER", digest, calendar, listing)
    payload = _payload(raw_body)
    result = (payload.get("chart") or {}).get("result") or []
    if not result or not isinstance(result[0], dict):
        return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
    meta = result[0].get("meta") or {}
    symbol = meta.get("symbol")
    if symbol != listing.listing.ticker:
        return _unbound("LISTING_UNVERIFIED", digest, calendar, listing)
    code = meta.get("exchangeName")
    if code not in YAHOO_EXCHANGE_MIC:
        return _unbound("UNKNOWN_EXCHANGE", digest, calendar, listing)
    if YAHOO_EXCHANGE_MIC[code] != listing.listing.mic:
        return _unbound("EXCHANGE_TRANSFER", digest, calendar, listing)
    timestamps = result[0].get("timestamp")
    if not isinstance(timestamps, list) or not timestamps:
        return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
    if any(item is None for item in timestamps):
        return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
    _symbol, _currency, bars = bars_from_yahoo_chart(payload)
    if len(bars) != len(timestamps):
        return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
    times = [bar.observed_at for bar in bars]
    if len(times) != len(set(times)):
        raise DuplicateSessionBar("duplicate Yahoo timestamp")
    if times != sorted(times):
        raise SessionContractError("Yahoo bars must be unique and chronological; refusing to reorder")
    bound: list[BoundBar] = []
    seen_sessions: set[str] = set()
    for bar in bars:
        matches = [
            row for row in calendar.rows
            if row.status == "OPEN" and _same_instant(bar.observed_at, row.open_utc)
        ]
        if len(matches) != 1:
            return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
        row = matches[0]
        if not listing.listing.active_on(row.session_date):
            return _unbound("LISTING_UNVERIFIED", digest, calendar, listing)
        key = row.session_date.isoformat()
        if key in seen_sessions:
            raise DuplicateSessionBar(f"more than one bar maps to {key}")
        seen_sessions.add(key)
        index = calendar.index_for(row.session_date)
        if index is None:
            return _unbound("SESSION_CONTINUITY_UNVERIFIED", digest, calendar, listing)
        bound.append(
            BoundBar(
                observed_at=bar.observed_at,
                session_date=key,
                session_index=index,
                close=bar.close,
                volume=bar.volume,
                close_local=row.close_local,
                eligible=decision_time >= row.close_utc,
            )
        )
    eligible = tuple(item for item in bound if item.eligible)
    excluded = tuple(item for item in bound if not item.eligible)
    return SessionBinding(
        status="BOUND",
        reason_code=None,
        calendar_id=calendar.calendar_id,
        listing_id=listing.listing.listing_id,
        tzdata_version=calendar.tzdata_version,
        yahoo_sha256=digest,
        symbol=str(symbol),
        eligible=eligible,
        excluded_before_close=excluded,
    )


def _same_instant(left: datetime, right: datetime) -> bool:
    return int(left.timestamp()) == int(right.timestamp())


def _require_bytes(body: bytes, declared: str, label: str) -> str:
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise SessionContractError(f"{label} body must be non-empty bytes")
    digest = hashlib.sha256(bytes(body)).hexdigest()
    if not isinstance(declared, str) or declared != digest:
        raise ProvenanceMismatch(f"{label} bytes do not match the declared sha256")
    return digest


def _payload(body: bytes) -> dict:
    try:
        parsed = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SessionContractError("Yahoo chart body is not UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise SessionContractError("Yahoo chart body must be a JSON object")
    return parsed


def _unbound(
    reason: str,
    digest: str,
    calendar: CalendarVintage | None,
    listing: ListingEvidence | None,
) -> SessionBinding:
    return SessionBinding(
        status="UNBOUND",
        reason_code=reason,
        calendar_id=None if calendar is None else calendar.calendar_id,
        listing_id=None if listing is None else listing.listing.listing_id,
        tzdata_version=None if calendar is None else calendar.tzdata_version,
        yahoo_sha256=digest,
        symbol=None,
        eligible=(),
        excluded_before_close=(),
    )
