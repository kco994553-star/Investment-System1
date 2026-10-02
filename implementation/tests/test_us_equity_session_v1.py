"""US_EQUITY_TRADING_SESSION_V1. Fixtures are explicit rows, not a holiday rule."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from investment_system.contracts.global_universe import ListingIdentity
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.sessions.binder import DuplicateSessionBar
from investment_system.sessions.calendar import load_calendar_vintage, runtime_tzdata_version
from investment_system.sessions.errors import ProvenanceMismatch, SessionContractError
from investment_system.sessions.listing import ListingEvidence
from investment_system.sessions.research import bind_research_inputs

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
NOTICE = b"fixture-notice"
NOTICE_SHA = hashlib.sha256(NOTICE).hexdigest()
GENERATED = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
MODEL_SHA = "419b792c121b35ddf8ceacb15a6440f8243ad3acf65fc350bde860c6c069c4b6"
ENGINE_SHA = "f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf"
PIT_SHA = "9c2a56deec51d6b4cd97d9d9ef5afc9236a3bb32018918b6b7e575fb0119f32e"
YAHOO_SHA = "1a1c98653f4ab0dbcfdf796344edf3fd11734c58604a926325ec32505d6ac534"


def _unix(day: str) -> int:
    stamp = datetime.combine(date.fromisoformat(day), time(9, 30), tzinfo=NY)
    return int(stamp.timestamp())


def _local(day: str, hour: int, minute: int) -> datetime:
    return datetime.combine(date.fromisoformat(day), time(hour, minute), tzinfo=NY)


def _after(day: str) -> datetime:
    nxt = date.fromisoformat(day) + timedelta(days=1)
    return datetime(nxt.year, nxt.month, nxt.day, 17, 0, tzinfo=timezone.utc)


def _calendar(mic: str, open_days: list[str], closed_days: list[str] | None = None, *,
              early: dict[str, str] | None = None, available: str = "2023-06-01T00:00:00+00:00",
              when: dict[str, str] | None = None) -> object:
    early = early or {}
    when = when or {}
    closed_days = closed_days or []
    rows = []
    for day in open_days:
        rows.append(_row(mic, day, "OPEN", early.get(day, "16:00:00"), when.get(day, available)))
    for day in closed_days:
        rows.append(_row(mic, day, "CLOSED", "16:00:00", when.get(day, available)))
    rows.sort(key=lambda item: item["session_date"])
    days = [item["session_date"] for item in rows]
    payload = {
        "contract": "US_EQUITY_SESSION_CALENDAR_V1",
        "schema_version": 1,
        "venue_mic": mic,
        "timezone": "America/New_York",
        "session_kind": "REGULAR",
        "coverage_start": days[0],
        "coverage_end": days[-1],
        "tzdata_version": runtime_tzdata_version(),
        "sources": [{"source_id": "notice", "source_url": "fixture://session-calendar", "sha256": NOTICE_SHA}],
        "rows": rows,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    vintage = load_calendar_vintage(body, declared_sha256=hashlib.sha256(body).hexdigest(), notices={"notice": NOTICE})
    return vintage


def _row(mic: str, day: str, status: str, close_local: str, available: str) -> dict:
    return {
        "venue_mic": mic,
        "session_date": day,
        "open_local": "09:30:00",
        "close_local": close_local,
        "status": status,
        "row_available_at": available,
        "source_id": "notice",
    }


def _listing(ticker: str, mic: str, *, start: str = "2020-01-01", end: str | None = None,
             security: str | None = None, listing_id: str | None = None,
             available: str = "2020-01-01T00:00:00+00:00") -> ListingEvidence:
    return ListingEvidence(
        listing=ListingIdentity(
            listing_id=listing_id or f"lst-{ticker}-{mic}",
            security_id=security or f"sec-{ticker}",
            ticker=ticker,
            mic=mic,
            currency="USD",
            valid_from=date.fromisoformat(start),
            valid_to=None if end is None else date.fromisoformat(end),
        ),
        available_at=datetime.fromisoformat(available),
        evidence_id=f"ev-{ticker}-{mic}-{start}",
        source_sha256="ab" * 32,
    )


def _chart(symbol: str, exchange: str, bars: list[tuple]) -> tuple[bytes, str]:
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "USD",
                        "exchangeName": exchange,
                        "exchangeTimezoneName": "America/New_York",
                        "gmtoffset": -14400,
                        "symbol": symbol,
                    },
                    "timestamp": [item[0] if isinstance(item[0], int) else _unix(item[0]) for item in bars],
                    "indicators": {
                        "quote": [
                            {
                                "close": [item[1] for item in bars],
                                "volume": [item[2] for item in bars],
                            }
                        ]
                    },
                }
            ]
        }
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return body, hashlib.sha256(body).hexdigest()


def _run(days: list[str], closes: list[float], *, mic: str = "XNAS", exchange: str = "NMS",
         symbol: str = "AAPL", closed: list[str] | None = None, early: dict | None = None,
         when: dict | None = None, listing: ListingEvidence | None = None,
         listings: list[ListingEvidence] | None = None, decision: datetime | None = None,
         volumes: list | None = None, spy: dict | None = None) -> dict:
    calendar = _calendar(mic, days, closed, early=early, when=when)
    bars = []
    for i, day in enumerate(days):
        if closes is None:
            break
        volume = 1000.0 + i if volumes is None else volumes[i]
        bars.append((day, closes[i], volume))
    # `days` here are the bar days; callers that need a calendar wider than the bars
    # pass the calendar through `listing` only. This helper uses the same days.
    body, digest = _chart(symbol, exchange, bars)
    use_listings = listings if listings is not None else [listing or _listing(symbol, mic)]
    kwargs = {}
    if spy is not None:
        kwargs.update(spy)
    return bind_research_inputs(
        raw_body=body,
        declared_sha256=digest,
        decision_time=decision or _after(days[-1]),
        generated_at=GENERATED,
        calendar=calendar,
        listings=use_listings,
        company_id=symbol.lower(),
        split_status="NONE",
        **kwargs,
    )


def _bars(calendar_days: list[str], bar_days: list[str], closes: list[float], **kw) -> dict:
    """Calendar days and Yahoo bars can differ. Extra calendar days stay explicit."""
    mic = kw.pop("mic", "XNAS")
    exchange = kw.pop("exchange", "NMS")
    symbol = kw.pop("symbol", "AAPL")
    closed = kw.pop("closed", None)
    early = kw.pop("early", None)
    when = kw.pop("when", None)
    volumes = kw.pop("volumes", None)
    calendar = _calendar(mic, calendar_days, closed, early=early, when=when)
    bars = []
    for i, day in enumerate(bar_days):
        volume = None if volumes is None else volumes[i]
        if volumes is None:
            volume = 1000.0 + i
        bars.append((day, closes[i], volume))
    body, digest = _chart(symbol, exchange, bars)
    return bind_research_inputs(
        raw_body=body,
        declared_sha256=digest,
        decision_time=kw.pop("decision", _after(max(bar_days))),
        generated_at=GENERATED,
        calendar=calendar,
        listings=kw.pop("listings", [_listing(symbol, mic, **kw.pop("listing_kw", {}))]),
        company_id=kw.pop("company_id", symbol.lower()),
        split_status="NONE",
        **kw,
    )


def test_normal_trading_day_binds_open_and_keeps_close():
    bound = _bars(["2024-01-02", "2024-01-03"], ["2024-01-02", "2024-01-03"], [100.0, 110.0])
    assert bound["status"] == "BOUND"
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1]
    assert bound["eligible_observations"][1]["close"] == 110.0
    assert bound["research_record"]["features"]["r_5"]["status"] == "NOT_AVAILABLE"
    assert bound["research_record"]["methodology"]["price_field"] == "close"
    assert bound["official_ready"] is False
    assert bound["research_ready"] is False


def test_weekend_bar_is_unbound_and_not_dropped():
    calendar = _calendar("XNAS", ["2024-12-20", "2024-12-23"])
    body, digest = _chart("AAPL", "NMS", [("2024-12-20", 10.0, 1.0), ("2024-12-21", 11.0, 1.0), ("2024-12-23", 12.0, 1.0)])
    bound = bind_research_inputs(
        raw_body=body, declared_sha256=digest, decision_time=_after("2024-12-23"), generated_at=GENERATED,
        calendar=calendar, listings=[_listing("AAPL", "XNAS")], company_id="aapl", split_status="NONE",
    )
    assert bound["status"] == "UNBOUND"
    assert bound["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"
    assert bound["eligible_observations"] == []
    assert bound["research_record"] is None


def test_ordinary_holiday_does_not_consume_an_index():
    bound = _bars(
        ["2024-12-24", "2024-12-26"],
        ["2024-12-24", "2024-12-26"],
        [10.0, 12.0],
        closed=["2024-12-25"],
    )
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1]
    holiday = _bars(["2024-12-24", "2024-12-26"], ["2024-12-25"], [11.0], closed=["2024-12-25"])
    assert holiday["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"


def test_good_friday_is_an_explicit_row():
    bound = _bars(
        ["2024-03-28", "2024-04-01"],
        ["2024-03-28", "2024-04-01"],
        [10.0, 12.0],
        closed=["2024-03-29"],
    )
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1]
    closed = _bars(["2024-03-28", "2024-04-01"], ["2024-03-29"], [11.0], closed=["2024-03-29"])
    assert closed["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"


def test_observed_holiday_is_not_invented_when_the_vintage_lists_the_day_open():
    # 2026-07-04 is a Saturday. A weekend-observance rule would close Friday 2026-07-03.
    # This vintage lists that Friday as OPEN, so the bar must bind and consume an index.
    bound = _bars(
        ["2026-07-02", "2026-07-03", "2026-07-06"],
        ["2026-07-02", "2026-07-03", "2026-07-06"],
        [10.0, 11.0, 12.0],
    )
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1, 2]
    closed = _bars(
        ["2026-07-02", "2026-07-06"],
        ["2026-07-02", "2026-07-06"],
        [10.0, 12.0],
        closed=["2026-07-03"],
    )
    assert [row["session_index"] for row in closed["eligible_observations"]] == [0, 1]


def test_early_close_is_one_session_and_uses_its_own_close():
    calendar_days = ["2024-07-03", "2024-07-05"]
    early = {"2024-07-03": "13:00:00"}
    before = _bars(calendar_days, calendar_days, [10.0, 12.0], early=early, closed=["2024-07-04"],
                   decision=_local("2024-07-03", 12, 59))
    assert before["status"] == "BOUND"
    assert before["eligible_observations"] == []
    assert [row["session_index"] for row in before["excluded_before_close"]] == [0, 1]
    assert before["excluded_before_close"][0]["close_local"] == "13:00:00"
    at_close = _bars(calendar_days, calendar_days, [10.0, 12.0], early=early, closed=["2024-07-04"],
                     decision=_local("2024-07-03", 13, 0))
    assert [row["session_index"] for row in at_close["eligible_observations"]] == [0]
    assert [row["session_index"] for row in at_close["excluded_before_close"]] == [1]
    assert at_close["eligible_observations"][0]["close"] == 10.0


def test_dst_spring_and_fall_bind_the_exchange_open():
    assert _unix("2024-03-08") == 1709908200
    assert _unix("2024-03-11") == 1710163800
    spring = _bars(["2024-03-08", "2024-03-11"], ["2024-03-08", "2024-03-11"], [10.0, 11.0])
    assert [row["session_index"] for row in spring["eligible_observations"]] == [0, 1]
    assert spring["eligible_observations"][0]["observed_at"].endswith("14:30:00+00:00")
    assert spring["eligible_observations"][1]["observed_at"].endswith("13:30:00+00:00")
    assert _unix("2024-11-01") == 1730467800
    assert _unix("2024-11-04") == 1730730600
    fall = _bars(["2024-11-01", "2024-11-04"], ["2024-11-01", "2024-11-04"], [10.0, 11.0])
    assert [row["session_index"] for row in fall["eligible_observations"]] == [0, 1]
    assert fall["eligible_observations"][0]["observed_at"].endswith("13:30:00+00:00")
    assert fall["eligible_observations"][1]["observed_at"].endswith("14:30:00+00:00")
    assert fall["lineage"]["tzdata_version"] == runtime_tzdata_version()


def test_unscheduled_closure_revision_does_not_rewrite_the_earlier_vintage():
    after = datetime(2025, 1, 10, 22, 0, tzinfo=timezone.utc)
    early = _bars(
        ["2025-01-08", "2025-01-09", "2025-01-10"],
        ["2025-01-08", "2025-01-09", "2025-01-10"],
        [10.0, 11.0, 12.0],
        decision=after,
    )
    assert early["status"] == "BOUND"
    assert [row["session_index"] for row in early["eligible_observations"]] == [0, 1, 2]
    revised_too_soon = _bars(
        ["2025-01-08", "2025-01-10"],
        ["2025-01-08", "2025-01-10"],
        [10.0, 12.0],
        closed=["2025-01-09"],
        when={"2025-01-09": "2025-01-02T15:00:00+00:00"},
        decision=datetime(2024, 12, 31, 21, 0, tzinfo=timezone.utc),
    )
    assert revised_too_soon["status"] == "UNBOUND"
    assert revised_too_soon["reason_code"] == "CALENDAR_NOT_ADMISSIBLE"
    assert revised_too_soon["research_record"] is None
    assert revised_too_soon["lineage"]["calendar_id"] != early["lineage"]["calendar_id"]
    later = _bars(
        ["2025-01-08", "2025-01-10"],
        ["2025-01-08", "2025-01-10"],
        [10.0, 12.0],
        closed=["2025-01-09"],
        when={"2025-01-09": "2025-01-02T15:00:00+00:00"},
        decision=after,
    )
    assert [row["session_index"] for row in later["eligible_observations"]] == [0, 1]
    still_open = _bars(
        ["2025-01-08", "2025-01-10"],
        ["2025-01-09"],
        [11.0],
        closed=["2025-01-09"],
        when={"2025-01-09": "2025-01-02T15:00:00+00:00"},
        decision=after,
    )
    assert still_open["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"
    replay = _bars(
        ["2025-01-08", "2025-01-09", "2025-01-10"],
        ["2025-01-08", "2025-01-09", "2025-01-10"],
        [10.0, 11.0, 12.0],
        decision=after,
    )
    assert replay["lineage"]["calendar_id"] == early["lineage"]["calendar_id"]
    assert [row["session_index"] for row in replay["eligible_observations"]] == [0, 1, 2]


def test_missing_yahoo_bar_on_an_open_session_leaves_the_index_gap():
    days = [f"2024-01-{day:02d}" for day in range(2, 23)]
    kept = [day for day in days if day != "2024-01-10"]
    closes = [100.0] * len(kept)
    bound = _bars(days, kept, closes)
    indexes = [row["session_index"] for row in bound["eligible_observations"]]
    assert indexes[0] == 0
    assert indexes[-1] == 20
    assert 8 not in indexes
    assert bound["research_record"]["features"]["sigma_20"]["reason_code"] == "SESSION_GAP"
    assert bound["research_record"]["features"]["r_20"]["status"] == "AVAILABLE"


def test_duplicate_yahoo_bar_fails():
    calendar = _calendar("XNAS", ["2024-01-02"])
    body, digest = _chart("AAPL", "NMS", [("2024-01-02", 10.0, 1.0), ("2024-01-02", 10.0, 1.0)])
    with pytest.raises(DuplicateSessionBar, match="duplicate"):
        bind_research_inputs(
            raw_body=body, declared_sha256=digest, decision_time=_after("2024-01-02"), generated_at=GENERATED,
            calendar=calendar, listings=[_listing("AAPL", "XNAS")], company_id="aapl", split_status="NONE",
        )


def test_null_close_is_not_dropped_before_numbering():
    bound = _bars(["2024-01-02", "2024-01-03", "2024-01-04"], ["2024-01-02", "2024-01-03", "2024-01-04"],
                  [10.0, None, 12.0])
    rows = bound["eligible_observations"]
    assert [row["session_index"] for row in rows] == [0, 1, 2]
    assert rows[1]["close"] is None
    assert rows[2]["close"] == 12.0


def test_null_volume_is_not_dropped_before_numbering():
    bound = _bars(
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        [10.0, 11.0, 12.0],
        volumes=[1.0, None, 3.0],
    )
    rows = bound["eligible_observations"]
    assert [row["session_index"] for row in rows] == [0, 1, 2]
    assert rows[1]["volume"] is None
    assert bound["research_record"]["features"]["r_5"]["status"] == "NOT_AVAILABLE"


def test_listing_start_does_not_renumber_and_a_pre_list_bar_fails():
    denied = _bars(
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        [10.0, 11.0, 12.0],
        listing_kw={"start": "2024-01-03"},
    )
    assert denied["reason_code"] == "LISTING_UNVERIFIED"
    assert denied["research_record"] is None
    allowed = _bars(
        ["2024-01-02", "2024-01-03", "2024-01-04"],
        ["2024-01-03", "2024-01-04"],
        [11.0, 12.0],
        listing_kw={"start": "2024-01-03"},
    )
    assert [row["session_index"] for row in allowed["eligible_observations"]] == [1, 2]


def test_listing_end_is_exclusive():
    denied = _bars(
        ["2024-01-03", "2024-01-04"],
        ["2024-01-03", "2024-01-04"],
        [11.0, 12.0],
        listing_kw={"start": "2024-01-03", "end": "2024-01-04"},
    )
    assert denied["reason_code"] == "LISTING_UNVERIFIED"
    allowed = _bars(
        ["2024-01-03", "2024-01-04"],
        ["2024-01-03"],
        [11.0],
        listing_kw={"start": "2024-01-03", "end": "2024-01-04"},
    )
    assert [row["session_index"] for row in allowed["eligible_observations"]] == [0]


def test_ticker_reuse_is_not_concatenated():
    calendar = _calendar("XNAS", ["2024-01-02"])
    body, digest = _chart("AAPL", "NMS", [("2024-01-02", 10.0, 1.0)])
    listings = [
        _listing("AAPL", "XNAS", security="sec-old", listing_id="old", end="2024-01-03"),
        _listing("AAPL", "XNAS", security="sec-new", listing_id="new", start="2024-01-03"),
    ]
    bound = bind_research_inputs(
        raw_body=body, declared_sha256=digest, decision_time=_after("2024-01-02"), generated_at=GENERATED,
        calendar=calendar, listings=listings, company_id="aapl", split_status="NONE",
    )
    assert bound["reason_code"] == "TICKER_REUSE"
    assert bound["eligible_observations"] == []
    assert bound["research_record"] is None


def test_exchange_transfer_is_not_concatenated():
    listings = [
        _listing("AAPL", "XNAS", security="sec-aapl", listing_id="nas", end="2024-06-01"),
        _listing("AAPL", "XNYS", security="sec-aapl", listing_id="nys", start="2024-06-01"),
    ]
    calendar = _calendar("XNAS", ["2024-01-02"])
    body, digest = _chart("AAPL", "NMS", [("2024-01-02", 10.0, 1.0)])
    bound = bind_research_inputs(
        raw_body=body, declared_sha256=digest, decision_time=_after("2024-01-02"), generated_at=GENERATED,
        calendar=calendar, listings=listings, company_id="aapl", split_status="NONE",
    )
    assert bound["reason_code"] == "EXCHANGE_TRANSFER"
    single = _bars(["2024-01-02"], ["2024-01-02"], [10.0], mic="XNYS", exchange="NMS",
                   listings=[_listing("AAPL", "XNYS")])
    assert single["reason_code"] == "EXCHANGE_TRANSFER"


def test_unknown_yahoo_exchange_code_is_unbound():
    bound = _bars(["2024-01-02"], ["2024-01-02"], [10.0], exchange="OTCM")
    assert bound["reason_code"] == "UNKNOWN_EXCHANGE"
    assert bound["research_record"] is None


def test_mismatched_spy_calendar_is_unaligned_and_stock_return_stands():
    stock_days = [f"2024-01-{day:02d}" for day in range(2, 24) if day != 10]
    spy_days = sorted(stock_days + ["2024-01-10"])
    stock_calendar = _calendar("XNAS", stock_days)
    spy_calendar = _calendar("ARCX", spy_days)
    stock_body, stock_sha = _chart("AAPL", "NMS", [(day, 100.0, 1.0) for day in stock_days])
    stock_body_closes = [(day, 100.0 if day != stock_days[-1] else 110.0, 1.0) for day in stock_days]
    stock_body, stock_sha = _chart("AAPL", "NMS", stock_body_closes)
    spy_body, spy_sha = _chart("SPY", "PCX", [(day, 100.0, 1.0) for day in spy_days])
    bound = bind_research_inputs(
        raw_body=stock_body, declared_sha256=stock_sha, decision_time=_after(stock_days[-1]),
        generated_at=GENERATED, calendar=stock_calendar, listings=[_listing("AAPL", "XNAS")],
        company_id="aapl", split_status="NONE",
        spy_raw_body=spy_body, spy_declared_sha256=spy_sha, spy_calendar=spy_calendar,
        spy_listings=[_listing("SPY", "ARCX")], spy_split_status="NONE",
    )
    assert bound["status"] == "BOUND"
    assert bound["lineage"]["spy_alignment"] == "RS_UNALIGNED"
    record = bound["research_record"]
    assert record["features"]["rs_20"]["reason_code"] == "RS_UNALIGNED"
    assert record["features"]["r_20"]["value"] == pytest.approx(110.0 / 100.0 - 1.0)
    assert record["regime"]["status"] == "NOT_AVAILABLE"


def test_aligned_spy_calendar_shares_the_stock_session_index():
    days = [f"2024-01-{day:02d}" for day in range(2, 23)]
    stock_calendar = _calendar("XNAS", days)
    spy_calendar = _calendar("ARCX", days)
    stock_bars = [(day, 100.0 if day != days[-1] else 110.0, 1.0) for day in days]
    stock_body, stock_sha = _chart("AAPL", "NMS", stock_bars)
    spy_body, spy_sha = _chart("SPY", "PCX", [(day, 100.0, 1.0) for day in days])
    bound = bind_research_inputs(
        raw_body=stock_body, declared_sha256=stock_sha, decision_time=_after(days[-1]),
        generated_at=GENERATED, calendar=stock_calendar, listings=[_listing("AAPL", "XNAS")],
        company_id="aapl", split_status="NONE",
        spy_raw_body=spy_body, spy_declared_sha256=spy_sha, spy_calendar=spy_calendar,
        spy_listings=[_listing("SPY", "ARCX")], spy_split_status="NONE",
    )
    assert bound["lineage"]["spy_alignment"] == "SHARED"
    record = bound["research_record"]
    assert record["features"]["r_20"]["value"] == pytest.approx(0.1)
    assert record["features"]["rs_20"]["value"] == pytest.approx(0.1)


def test_decision_before_session_close_does_not_expose_that_close():
    days = [f"2024-01-{day:02d}" for day in range(2, 9)]
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 999.0]
    bound = _bars(days, days, closes, decision=_local("2024-01-08", 9, 31))
    assert bound["status"] == "BOUND"
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1, 2, 3, 4, 5]
    assert bound["excluded_before_close"][0]["session_index"] == 6
    assert bound["excluded_before_close"][0]["observed_at"].endswith("14:30:00+00:00")
    assert bound["excluded_before_close"][0]["close"] == 999.0
    features = bound["research_record"]["features"]
    assert features["r_5"]["value"] == pytest.approx(105.0 / 100.0 - 1.0)
    assert "999" not in json.dumps(features)
    assert bound["close_availability_guard"]["provider_publication_timestamp"] is False
    assert bound["close_availability_guard"]["observed_at_overwritten"] is False


def test_decision_after_session_close_uses_the_completed_bar():
    days = [f"2024-01-{day:02d}" for day in range(2, 9)]
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 999.0]
    bound = _bars(days, days, closes, decision=_local("2024-01-08", 16, 0))
    assert [row["session_index"] for row in bound["eligible_observations"]] == [0, 1, 2, 3, 4, 5, 6]
    assert bound["research_record"]["features"]["r_5"]["value"] == pytest.approx(999.0 / 101.0 - 1.0)


def test_deterministic_rebuild_and_provenance_mismatch(tmp_path):
    first = _bars(["2024-01-02", "2024-01-03"], ["2024-01-02", "2024-01-03"], [10.0, 12.0])
    second = _bars(["2024-01-02", "2024-01-03"], ["2024-01-02", "2024-01-03"], [10.0, 12.0])
    assert first["lineage"]["calendar_id"] == second["lineage"]["calendar_id"]
    assert first["research_record"]["semantic_hash"] == second["research_record"]["semantic_hash"]
    calendar = _calendar("XNAS", ["2024-01-02"])
    body, digest = _chart("AAPL", "NMS", [("2024-01-02", 10.0, 1.0)])
    with pytest.raises(ProvenanceMismatch, match="sha256"):
        bind_research_inputs(
            raw_body=body, declared_sha256="0" * 64, decision_time=_after("2024-01-02"), generated_at=GENERATED,
            calendar=calendar, listings=[_listing("AAPL", "XNAS")], company_id="aapl", split_status="NONE",
        )
    store = RawDatasetStore(tmp_path / "raw")
    artifact = "session_calendar:XNAS:fixture"
    payload = {
        "contract": "US_EQUITY_SESSION_CALENDAR_V1",
        "schema_version": 1,
        "venue_mic": "XNAS",
        "timezone": "America/New_York",
        "session_kind": "REGULAR",
        "coverage_start": "2024-01-02",
        "coverage_end": "2024-01-02",
        "tzdata_version": runtime_tzdata_version(),
        "sources": [{"source_id": "notice", "source_url": "fixture://session-calendar", "sha256": NOTICE_SHA}],
        "rows": [_row("XNAS", "2024-01-02", "OPEN", "16:00:00", "2023-06-01T00:00:00+00:00")],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    store.put(artifact, blob, "fixture://session-calendar", "EXCHANGE_SESSION_CALENDAR", "application/json", "test")
    stored = store.get_bytes(artifact)
    manifest = store.get_manifest(artifact)
    assert manifest["sha256"] == hashlib.sha256(stored).hexdigest()
    assert manifest["fetched_at"] != "2023-06-01T00:00:00+00:00"
    loaded = load_calendar_vintage(stored, declared_sha256=manifest["sha256"], notices={"notice": NOTICE})
    assert loaded.admissible_at(datetime(2024, 6, 1, tzinfo=timezone.utc))
    path = store.root / "blobs" / artifact.replace(":", "__")
    path.write_bytes(stored + b"\n")
    with pytest.raises(ProvenanceMismatch):
        load_calendar_vintage(store.get_bytes(artifact), declared_sha256=manifest["sha256"])


def test_model_bytes_and_session_source_stay_in_contract():
    assert hashlib.sha256((ROOT / "src/investment_system/technical/real_model_v1.py").read_bytes()).hexdigest() == MODEL_SHA
    assert hashlib.sha256((ROOT / "src/investment_system/technical/engine.py").read_bytes()).hexdigest() == ENGINE_SHA
    assert hashlib.sha256((ROOT / "src/investment_system/technical/pit_market.py").read_bytes()).hexdigest() == PIT_SHA
    assert hashlib.sha256((ROOT / "src/investment_system/providers/yahoo_chart.py").read_bytes()).hexdigest() == YAHOO_SHA
    source = "\n".join(path.read_text() for path in (ROOT / "src/investment_system/sessions").glob("*.py"))
    for banned in (".weekday(", "easter", "gmtoffset", "pandas_market", "relativedelta", "BDay", "holiday_calendar"):
        assert banned not in source
    body = _calendar("XNAS", ["2024-01-02"])
    raw = json.dumps({
        "contract": body.calendar_id and "US_EQUITY_SESSION_CALENDAR_V1",
    })
    del raw
    bad = {
        "contract": "US_EQUITY_SESSION_CALENDAR_V1",
        "schema_version": 1,
        "venue_mic": "XNAS",
        "timezone": "America/New_York",
        "session_kind": "REGULAR",
        "coverage_start": "2024-01-02",
        "coverage_end": "2024-01-02",
        "tzdata_version": runtime_tzdata_version(),
        "rules": ["weekdays-minus-holidays"],
        "sources": [{"source_id": "notice", "source_url": "fixture://session-calendar", "sha256": NOTICE_SHA}],
        "rows": [_row("XNAS", "2024-01-02", "OPEN", "16:00:00", "2023-06-01T00:00:00+00:00")],
    }
    encoded = json.dumps(bad, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(SessionContractError, match="undeclared"):
        load_calendar_vintage(encoded, declared_sha256=hashlib.sha256(encoded).hexdigest())
