"""Session binding in front of the unchanged Technical research record.

Calendar vintage → session binder → listing check → Yahoo bar →
session_index → close-availability guard → existing research record.

The guard is a lower bound: a daily bar is not a feature input before the
vintage's close_local. It is not a claim about when Yahoo published the bar.
observed_at on the raw bar is left as stored.
"""

from __future__ import annotations

from datetime import datetime

from ..technical.codec import semantic_hash
from ..technical.real_model_v1 import build_research_record
from .binder import SessionBinding, _require_bytes, bind_yahoo_bars, listing_refusal
from .calendar import CalendarVintage, _aware
from .errors import SessionContractError
from .listing import ListingEvidence

BINDING_CONTRACT = "US_EQUITY_TRADING_SESSION_BINDING_V1"
GUARD = {
    "kind": "CANONICAL_SESSION_CLOSE_LOWER_BOUND",
    "provider_publication_timestamp": False,
    "observed_at_overwritten": False,
}


def bind_research_inputs(
    *,
    raw_body: bytes,
    declared_sha256: str,
    decision_time: datetime,
    generated_at: datetime,
    calendar: CalendarVintage,
    listings: tuple[ListingEvidence, ...] | list[ListingEvidence],
    company_id: str,
    split_status: str,
    splits: tuple[datetime, ...] | list[datetime] = (),
    spy_raw_body: bytes | None = None,
    spy_declared_sha256: str | None = None,
    spy_calendar: CalendarVintage | None = None,
    spy_listings: tuple[ListingEvidence, ...] | list[ListingEvidence] | None = None,
    spy_split_status: str | None = None,
    synthetic: bool = False,
) -> dict:
    """Bind, then call the existing research record. Does not change its formulas."""
    decision_time = _aware(decision_time, "decision_time")
    generated_at = _aware(generated_at, "generated_at")
    if not isinstance(company_id, str) or not company_id.strip():
        raise SessionContractError("company_id is required")
    digest = _require_bytes(raw_body, declared_sha256, "Yahoo chart")
    if spy_raw_body is not None:
        if spy_declared_sha256 is None:
            raise SessionContractError("SPY sha256 is required when SPY bytes are supplied")
        _require_bytes(spy_raw_body, spy_declared_sha256, "SPY chart")
    listings = tuple(listings)
    refusal = listing_refusal(listings)
    if refusal is not None:
        return _envelope(
            status="UNBOUND",
            reason_code=refusal,
            binding=None,
            calendar=calendar,
            listing_id=None,
            yahoo_sha256=digest,
            research_record=None,
            spy_alignment=None,
        )
    listing = listings[0]
    binding = bind_yahoo_bars(
        raw_body,
        declared_sha256,
        decision_time=decision_time,
        calendar=calendar,
        listing=listing,
    )
    if binding.status != "BOUND":
        return _envelope(
            status="UNBOUND",
            reason_code=binding.reason_code,
            binding=binding,
            calendar=calendar,
            listing_id=listing.listing.listing_id,
            yahoo_sha256=binding.yahoo_sha256,
            research_record=None,
            spy_alignment=None,
        )
    observations = [bar.observation() for bar in binding.eligible]
    spy_observations = None
    spy_alignment = None
    spy_sha = None
    spy_calendar_id = None
    spy_listing_id = None
    if spy_raw_body is not None:
        if spy_calendar is None or spy_listings is None or spy_declared_sha256 is None or spy_split_status is None:
            raise SessionContractError("SPY calendar, listing, sha256, and split_status are required together")
        spy_refusal = listing_refusal(tuple(spy_listings))
        if spy_refusal is not None:
            spy_alignment = "RS_UNALIGNED"
        else:
            spy_binding = bind_yahoo_bars(
                spy_raw_body,
                spy_declared_sha256,
                decision_time=decision_time,
                calendar=spy_calendar,
                listing=tuple(spy_listings)[0],
            )
            spy_sha = spy_binding.yahoo_sha256
            spy_calendar_id = spy_binding.calendar_id
            spy_listing_id = spy_binding.listing_id
            if spy_binding.status != "BOUND":
                spy_alignment = "RS_UNALIGNED"
            else:
                shared = _shared_indexes(calendar, spy_calendar, binding, spy_binding)
                if shared is None:
                    spy_alignment = "RS_UNALIGNED"
                else:
                    spy_alignment = "SHARED"
                    spy_observations = shared
    record = build_research_record(
        company_id=company_id,
        ticker=listing.listing.ticker,
        decision_time=decision_time,
        generated_at=generated_at,
        observations=observations,
        split_status=split_status,
        source_sha256=binding.yahoo_sha256,
        splits=splits,
        spy_observations=spy_observations,
        spy_split_status=None if spy_observations is None else spy_split_status,
        spy_source_sha256=None if spy_observations is None else spy_sha,
        synthetic=synthetic,
    )
    if spy_alignment == "RS_UNALIGNED":
        record["features"]["rs_20"] = {
            "status": "NOT_AVAILABLE",
            "reason_code": "RS_UNALIGNED",
            "value": None,
        }
        record["semantic_hash"] = semantic_hash(record)
        record["record_id"] = "trm_" + record["semantic_hash"][:16]
    return _envelope(
        status="BOUND",
        reason_code=None,
        binding=binding,
        calendar=calendar,
        listing_id=listing.listing.listing_id,
        yahoo_sha256=binding.yahoo_sha256,
        research_record=record,
        spy_alignment=spy_alignment,
        spy_calendar_id=spy_calendar_id,
        spy_listing_id=spy_listing_id,
        spy_yahoo_sha256=spy_sha,
    )


def _shared_indexes(
    stock_calendar: CalendarVintage,
    spy_calendar: CalendarVintage,
    stock: SessionBinding,
    spy: SessionBinding,
) -> list[dict] | None:
    dates = [bar.session_date for bar in stock.eligible] + [bar.session_date for bar in spy.eligible]
    if not dates:
        return None
    start = min(dates)
    end = max(dates)
    from datetime import date as date_cls

    start_day = date_cls.fromisoformat(start)
    end_day = date_cls.fromisoformat(end)
    if stock_calendar.open_dates_between(start_day, end_day) != spy_calendar.open_dates_between(start_day, end_day):
        return None
    remapped = []
    for bar in spy.eligible:
        index = stock_calendar.index_for(date_cls.fromisoformat(bar.session_date))
        if index is None:
            return None
        observation = bar.observation()
        observation["session_index"] = index
        remapped.append(observation)
    return remapped


def _envelope(
    *,
    status: str,
    reason_code: str | None,
    binding: SessionBinding | None,
    calendar: CalendarVintage | None,
    listing_id: str | None,
    yahoo_sha256: str,
    research_record: dict | None,
    spy_alignment: str | None,
    spy_calendar_id: str | None = None,
    spy_listing_id: str | None = None,
    spy_yahoo_sha256: str | None = None,
) -> dict:
    eligible = [] if binding is None else [bar.audit() for bar in binding.eligible]
    excluded = [] if binding is None else [bar.audit() for bar in binding.excluded_before_close]
    return {
        "contract": BINDING_CONTRACT,
        "schema_version": 1,
        "status": status,
        "reason_code": reason_code,
        "close_availability_guard": dict(GUARD),
        "lineage": {
            "calendar_id": None if calendar is None else calendar.calendar_id,
            "listing_id": listing_id,
            "tzdata_version": None if calendar is None else calendar.tzdata_version,
            "yahoo_sha256": yahoo_sha256,
            "spy_calendar_id": spy_calendar_id,
            "spy_listing_id": spy_listing_id,
            "spy_yahoo_sha256": spy_yahoo_sha256,
            "spy_alignment": spy_alignment,
        },
        "eligible_observations": eligible,
        "excluded_before_close": excluded,
        "research_record": research_record,
        "official_ready": False,
        "research_ready": False,
    }
