"""Synthetic daily-bar validation and an injected existing-engine adapter.

No calendar inference, price repair, provider access, persistence or model changes.
"""
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
import math
from typing import Literal, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..contracts.models import QGVSnapshot, TechnicalSnapshot


@dataclass(frozen=True)
class ExpectedSession:
    session: date
    close_at: datetime


@dataclass(frozen=True)
class CorporateActionEvent:
    kind: Literal["SPLIT", "DIVIDEND", "OTHER"]
    effective_session: date
    published_at: datetime | None
    available_at: datetime | None
    source_reference: str | None = field(repr=False)


@dataclass(frozen=True)
class DailyBar:
    company_id: str
    listing_id: str
    symbol: str
    currency: str
    provider: str
    session: date
    observed_at: datetime
    available_at: datetime | None
    published_at: datetime | None
    complete: bool | None
    price_basis: Literal["RAW_CLOSE", "PROVIDER_ADJUSTED_CLOSE"]
    close: float | None = field(repr=False)
    adjclose: float | None = field(repr=False)
    open: float | None = field(default=None, repr=False)
    high: float | None = field(default=None, repr=False)
    low: float | None = field(default=None, repr=False)
    volume: float | None = field(default=None, repr=False)
    ohlc_basis: Literal["RAW"] | None = None


@dataclass(frozen=True)
class DailyInputSeries:
    company_id: str
    listing_id: str
    symbol: str
    currency: str
    provider: str
    exchange: str
    market_timezone: str
    source_reference: str = field(repr=False)
    interval: Literal["1d"]
    price_basis: Literal["RAW_CLOSE", "PROVIDER_ADJUSTED_CLOSE"]
    read_at: datetime
    synthetic: bool
    bars: tuple[DailyBar, ...] = field(repr=False)
    expected_sessions: tuple[ExpectedSession, ...] | None
    calendar_reference: str | None = field(repr=False)
    basis_status: Literal["CONFIRMED_SYNTHETIC", "UNKNOWN"]
    corporate_action_status: Literal["CONFIRMED_SYNTHETIC", "UNKNOWN"]
    action_covered_sessions: tuple[date, ...]
    adjustment_reference: str | None = field(repr=False)
    events: tuple[CorporateActionEvent, ...] = field(repr=False)


@dataclass(frozen=True)
class PreparedDailyReturns:
    state: Literal["READY", "NOT_AVAILABLE"]
    returns: tuple[float, ...] | None = field(repr=False)
    reason_codes: tuple[str, ...]
    input_bar_count: int
    eligible_bar_count: int
    excluded_future_bar_count: int
    return_count: int
    quality_flags: tuple[str, ...]
    synthetic: bool = True
    pit_status: Literal["NOT_VERIFIED"] = "NOT_VERIFIED"
    model_status: Literal["PLACEHOLDER_UNVALIDATED"] = "PLACEHOLDER_UNVALIDATED"


@dataclass(frozen=True)
class DailyTechnicalResult:
    state: Literal["DEMO", "NOT_AVAILABLE"]
    data: TechnicalSnapshot | None = field(repr=False)
    prepared: PreparedDailyReturns


class TechnicalEvaluator(Protocol):
    def evaluate(self, company_id: str, as_of: datetime, returns: list[float],
                 qgv: QGVSnapshot | None = None, synthetic: bool = True) -> TechnicalSnapshot: ...


def _text(value):
    return type(value) is str and bool(value.strip())


def _aware(value):
    if not isinstance(value,datetime):
        return False
    try:
        if value.tzinfo is None or value.utcoffset() is None:
            return False
        value.astimezone(timezone.utc)
        return True
    except (OverflowError,ValueError,TypeError):
        return False


def _utc(value):
    return value.astimezone(timezone.utc)


def _number(value, *, positive=True):
    if type(value) not in (int,float):
        return False
    try:
        return math.isfinite(value) and (value > 0 if positive else value >= 0)
    except (OverflowError,ValueError):
        return False


def prepare_daily_returns(series: DailyInputSeries, as_of: datetime) -> PreparedDailyReturns:
    count = len(series.bars) if isinstance(series,DailyInputSeries) and type(series.bars) is tuple else 0
    eligible_count, excluded = 0, 0
    flags = ["PIT_UNAVAILABLE"]

    def fail(reason):
        return PreparedDailyReturns("NOT_AVAILABLE",None,(reason,),count,eligible_count,excluded,0,tuple(dict.fromkeys(flags)))

    if not isinstance(series,DailyInputSeries) or type(series.bars) is not tuple or type(series.events) is not tuple or any(not isinstance(b,DailyBar) or type(b.session) is not date for b in series.bars) or any(not isinstance(e,CorporateActionEvent) for e in series.events):
        return fail("INVALID_INPUT_TYPE")
    if any(not _text(getattr(series,k)) for k in ("company_id","listing_id","symbol","currency","provider","exchange","market_timezone","source_reference")):
        return fail("MISSING_METADATA")
    try:
        ZoneInfo(series.market_timezone)
    except (ZoneInfoNotFoundError,ValueError):
        return fail("MISSING_METADATA")
    if series.interval != "1d":
        return fail("INVALID_INTERVAL")
    if series.synthetic is not True:
        return fail("REAL_INPUT_NOT_AUTHORIZED")
    times = [as_of,series.read_at]+[b.observed_at for b in series.bars]
    times += [t for b in series.bars for t in (b.available_at,b.published_at) if t is not None]
    if series.expected_sessions is not None:
        if type(series.expected_sessions) is not tuple or any(not isinstance(s,ExpectedSession) or type(s.session) is not date for s in series.expected_sessions):
            return fail("INVALID_CALENDAR")
        times += [s.close_at for s in series.expected_sessions]
    times += [t for e in series.events for t in (e.available_at,e.published_at) if t is not None]
    if any(not _aware(t) for t in times):
        return fail("INVALID_TIMESTAMP")
    if any(_utc(t)>_utc(series.read_at) for b in series.bars for t in (b.available_at,) if t is not None) or any(_utc(e.available_at)>_utc(series.read_at) for e in series.events if e.available_at is not None):
        return fail("INVALID_TIME_ORDER")
    sessions=[b.session for b in series.bars]; observed=[_utc(b.observed_at) for b in series.bars]
    if len(set(sessions))!=count or len(set(observed))!=count:
        return fail("DUPLICATE_BAR")
    if sessions!=sorted(sessions) or observed!=sorted(observed):
        return fail("UNSORTED_BARS")
    bars=tuple(b for b in series.bars if _utc(b.observed_at)<=_utc(as_of))
    eligible_count=len(bars); excluded=count-eligible_count
    if eligible_count<2:
        return fail("INSUFFICIENT_BARS")
    if series.expected_sessions is None or not _text(series.calendar_reference):
        return fail("CALENDAR_UNCONFIRMED")
    calendar=series.expected_sessions; dates=[s.session for s in calendar]; closes=[_utc(s.close_at) for s in calendar]
    if len(set(dates))!=len(dates) or dates!=sorted(dates) or len(set(closes))!=len(closes) or closes!=sorted(closes):
        return fail("INVALID_CALENDAR")
    expected=tuple(s for s in calendar if _utc(s.close_at)<=_utc(as_of))
    actual=tuple(b.session for b in bars)
    if any(s.session not in actual for s in expected):
        return fail("MISSING_SESSION")
    if any(b.session not in {s.session for s in expected} for b in bars):
        return fail("UNEXPECTED_SESSION")
    if any(_utc(b.observed_at)!=_utc(s.close_at) for b,s in zip(bars,expected)):
        return fail("SESSION_TIME_MISMATCH")
    if any(b.complete is not True for b in bars):
        return fail("INCOMPLETE_SESSION")
    if any(getattr(b,k)!=getattr(series,k) for b in bars for k in ("company_id","listing_id","symbol","currency","provider")):
        return fail("IDENTITY_MISMATCH")
    for b in bars:
        if b.available_at is None:
            return fail("AVAILABILITY_UNKNOWN")
        if _utc(b.available_at)>_utc(as_of):
            return fail("AVAILABLE_AFTER_AS_OF")
        if b.published_at is not None and _utc(b.published_at)>_utc(as_of):
            return fail("PUBLISHED_AFTER_AS_OF")
        if _utc(b.observed_at)>_utc(b.available_at) or (b.published_at is not None and not _utc(b.observed_at)<=_utc(b.published_at)<=_utc(b.available_at)):
            return fail("INVALID_TIME_ORDER")
        if b.published_at is None:
            flags.append("PUBLICATION_TIME_UNKNOWN")
    for b in bars:
        if not _number(b.close) or any(v is not None and not _number(v) for v in (b.adjclose,b.open,b.high,b.low)):
            return fail("INVALID_PRICE")
        if series.price_basis=="PROVIDER_ADJUSTED_CLOSE" and b.adjclose is None:
            return fail("ADJUSTED_CLOSE_MISSING")
        if b.price_basis!=series.price_basis:
            return fail("MIXED_BASIS")
    for b in bars:
        ohlc=(b.open,b.high,b.low)
        if any(v is not None for v in ohlc) and (any(v is None for v in ohlc) or b.ohlc_basis!="RAW" or not b.low<=min(b.open,b.close)<=max(b.open,b.close)<=b.high):
            return fail("INVALID_OHLC")
    for b in bars:
        if b.volume is not None and not _number(b.volume,positive=False):
            return fail("INVALID_VOLUME")
    if series.price_basis not in ("RAW_CLOSE","PROVIDER_ADJUSTED_CLOSE") or series.basis_status!="CONFIRMED_SYNTHETIC":
        return fail("BASIS_UNCONFIRMED")
    if series.corporate_action_status!="CONFIRMED_SYNTHETIC":
        return fail("ACTION_COVERAGE_UNCONFIRMED")
    if type(series.action_covered_sessions) is not tuple or series.action_covered_sessions!=actual:
        return fail("ACTION_COVERAGE_MISMATCH")
    if series.price_basis=="PROVIDER_ADJUSTED_CLOSE" and not _text(series.adjustment_reference):
        return fail("ADJUSTMENT_METADATA_MISSING")
    for e in series.events:
        if e.kind not in ("SPLIT","DIVIDEND","OTHER") or type(e.effective_session) is not date or e.effective_session not in actual or not _text(e.source_reference):
            return fail("ACTION_METADATA_INVALID")
        if e.available_at is None:
            return fail("ACTION_AVAILABILITY_UNKNOWN")
        if _utc(e.available_at)>_utc(as_of):
            return fail("ACTION_AVAILABLE_AFTER_AS_OF")
        if e.published_at is not None and (_utc(e.published_at)>_utc(e.available_at) or _utc(e.published_at)>_utc(as_of)):
            return fail("ACTION_METADATA_INVALID")
        if e.published_at is None:
            flags.append("PUBLICATION_TIME_UNKNOWN")
        if series.price_basis=="RAW_CLOSE":
            return fail("UNRESOLVED_CORPORATE_ACTION")
    prices=[b.adjclose if series.price_basis=="PROVIDER_ADJUSTED_CLOSE" else b.close for b in bars]
    try:
        returns=tuple(cur/prev-1.0 for prev,cur in zip(prices,prices[1:]))
    except ArithmeticError:
        return fail("NONFINITE_RETURN")
    if any(not math.isfinite(r) for r in returns):
        return fail("NONFINITE_RETURN")
    returns=returns[-20:]
    return PreparedDailyReturns("READY",returns,(),count,eligible_count,excluded,len(returns),tuple(dict.fromkeys(flags)))


def evaluate_daily_input(series: DailyInputSeries, as_of: datetime, *, engine: TechnicalEvaluator,
                         qgv: QGVSnapshot | None = None) -> DailyTechnicalResult:
    prepared=prepare_daily_returns(series,as_of)
    if prepared.state!="READY":
        return DailyTechnicalResult("NOT_AVAILABLE",None,prepared)
    try:
        data=engine.evaluate(series.company_id,as_of,list(prepared.returns),qgv=qgv,synthetic=True)
    except ArithmeticError:
        return DailyTechnicalResult("NOT_AVAILABLE",None,replace(prepared,state="NOT_AVAILABLE",returns=None,return_count=0,reason_codes=("CALCULATION_ERROR",)))
    return DailyTechnicalResult("DEMO",data,prepared)
