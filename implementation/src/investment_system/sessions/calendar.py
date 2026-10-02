"""Explicit US equity session vintages.

A vintage is stored evidence. It is not a weekday rule, a federal-holiday
rule, or a weekend-observance function. Rows that are absent are not sessions.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import ProvenanceMismatch, SessionContractError

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TOP_KEYS = frozenset({
    "contract",
    "schema_version",
    "venue_mic",
    "timezone",
    "session_kind",
    "coverage_start",
    "coverage_end",
    "tzdata_version",
    "sources",
    "rows",
})
_SOURCE_KEYS = frozenset({"source_id", "source_url", "sha256"})
_ROW_KEYS = frozenset({
    "venue_mic",
    "session_date",
    "open_local",
    "close_local",
    "status",
    "row_available_at",
    "source_id",
})
CONTRACT = "US_EQUITY_SESSION_CALENDAR_V1"
TIMEZONE = "America/New_York"


def runtime_tzdata_version() -> str:
    """Version string of the IANA data this process will actually apply."""
    import zoneinfo

    for root in zoneinfo.TZPATH:
        path = Path(root) / "tzdata.zi"
        if not path.is_file():
            continue
        line = path.open("r", encoding="utf-8", errors="replace").readline().strip()
        if line.startswith("# version "):
            version = line[len("# version "):].strip()
            if version:
                return version
    raise SessionContractError("tzdata version is not reproducible")


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SessionContractError(f"{label} must be a timezone-aware datetime")
    return value


def _parse_aware(text: str, label: str) -> datetime:
    if not isinstance(text, str) or not text.strip():
        raise SessionContractError(f"{label} must be an ISO timestamp")
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise SessionContractError(f"{label} is not an ISO timestamp") from exc
    return _aware(parsed, label)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


@dataclass(frozen=True)
class SessionRow:
    venue_mic: str
    session_date: date
    open_local: str
    close_local: str
    status: str
    row_available_at: datetime
    source_id: str
    open_utc: datetime
    close_utc: datetime


@dataclass(frozen=True)
class CalendarVintage:
    calendar_id: str
    venue_mic: str
    timezone_name: str
    session_kind: str
    coverage_start: date
    coverage_end: date
    tzdata_version: str
    rows: tuple[SessionRow, ...]
    open_index: MappingProxyType

    def index_for(self, day: date) -> int | None:
        return self.open_index.get(day)

    def open_dates_between(self, start: date, end: date) -> frozenset[date]:
        if end < start:
            raise SessionContractError("session window is reversed")
        return frozenset(day for day in self.open_index if start <= day <= end)

    def admissible_at(self, decision_time: datetime) -> bool:
        decision_time = _aware(decision_time, "decision_time")
        return all(row.row_available_at <= decision_time for row in self.rows)


def load_calendar_vintage(
    body: bytes,
    *,
    declared_sha256: str,
    notices: dict[str, bytes] | None = None,
) -> CalendarVintage:
    """Load one immutable vintage. Does not fill missing dates."""
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise SessionContractError("calendar body must be non-empty bytes")
    digest = _sha256(bytes(body))
    if not isinstance(declared_sha256, str) or declared_sha256 != digest:
        raise ProvenanceMismatch("calendar bytes do not match the declared sha256")
    try:
        payload = json.loads(bytes(body).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SessionContractError("calendar body is not UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise SessionContractError("calendar body must be a JSON object")
    extra = set(payload) - _TOP_KEYS
    if extra:
        raise SessionContractError("calendar vintage has undeclared keys")
    if payload.get("contract") != CONTRACT or payload.get("schema_version") != 1:
        raise SessionContractError("calendar contract is not US_EQUITY_SESSION_CALENDAR_V1")
    if payload.get("timezone") != TIMEZONE or payload.get("session_kind") != "REGULAR":
        raise SessionContractError("v1 calendars are REGULAR sessions in America/New_York")
    venue = payload.get("venue_mic")
    if not isinstance(venue, str) or not venue.strip():
        raise SessionContractError("venue_mic is required")
    tz_version = payload.get("tzdata_version")
    runtime = runtime_tzdata_version()
    if not isinstance(tz_version, str) or tz_version != runtime:
        raise SessionContractError(
            f"tzdata_version {tz_version!r} does not match runtime {runtime!r}"
        )
    try:
        zone = ZoneInfo(TIMEZONE)
    except ZoneInfoNotFoundError as exc:
        raise SessionContractError("America/New_York is not available") from exc
    coverage_start = _date(payload.get("coverage_start"), "coverage_start")
    coverage_end = _date(payload.get("coverage_end"), "coverage_end")
    if coverage_end < coverage_start:
        raise SessionContractError("coverage_end is before coverage_start")
    sources = _sources(payload.get("sources"), notices)
    rows = _rows(payload.get("rows"), venue=venue, zone=zone, sources=sources,
                 coverage_start=coverage_start, coverage_end=coverage_end)
    open_rows = [row for row in rows if row.status == "OPEN"]
    opens = [row.open_utc for row in open_rows]
    if len(opens) != len(set(opens)):
        raise SessionContractError("two OPEN rows share an open instant")
    index = MappingProxyType({row.session_date: i for i, row in enumerate(open_rows)})
    return CalendarVintage(
        calendar_id=digest,
        venue_mic=venue,
        timezone_name=TIMEZONE,
        session_kind="REGULAR",
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        tzdata_version=runtime,
        rows=tuple(rows),
        open_index=index,
    )


def _date(value: object, label: str) -> date:
    if not isinstance(value, str) or not _DATE.match(value):
        raise SessionContractError(f"{label} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SessionContractError(f"{label} is not a date") from exc


def _sources(value: object, notices: dict[str, bytes] | None) -> dict[str, str]:
    if not isinstance(value, list) or not value:
        raise SessionContractError("calendar sources are required")
    found: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict) or set(item) - _SOURCE_KEYS:
            raise SessionContractError("calendar source has undeclared keys")
        source_id = item.get("source_id")
        url = item.get("source_url")
        digest = item.get("sha256")
        if not isinstance(source_id, str) or not source_id.strip():
            raise SessionContractError("source_id is required")
        if source_id in found:
            raise SessionContractError("duplicate calendar source_id")
        if not isinstance(url, str) or not url.strip():
            raise SessionContractError("source_url is required")
        if not isinstance(digest, str) or not _HEX64.match(digest):
            raise SessionContractError("source sha256 must be 64 lowercase hex")
        if notices is not None:
            blob = notices.get(source_id)
            if blob is None or hashlib.sha256(blob).hexdigest() != digest:
                raise ProvenanceMismatch(f"notice bytes do not match source {source_id}")
        found[source_id] = digest
    return found


def _rows(
    value: object,
    *,
    venue: str,
    zone: ZoneInfo,
    sources: dict[str, str],
    coverage_start: date,
    coverage_end: date,
) -> list[SessionRow]:
    if not isinstance(value, list) or not value:
        raise SessionContractError("calendar rows are required")
    rows: list[SessionRow] = []
    seen: set[date] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) - _ROW_KEYS:
            raise SessionContractError("calendar row has undeclared keys")
        if item.get("venue_mic") != venue:
            raise SessionContractError("row venue_mic does not match the vintage")
        status = item.get("status")
        if status not in ("OPEN", "CLOSED"):
            raise SessionContractError("row status must be OPEN or CLOSED")
        day = _date(item.get("session_date"), "session_date")
        if day in seen:
            raise SessionContractError("duplicate session_date")
        seen.add(day)
        if day < coverage_start or day > coverage_end:
            raise SessionContractError("session_date is outside coverage")
        open_local = item.get("open_local")
        close_local = item.get("close_local")
        if not isinstance(open_local, str) or not _CLOCK.match(open_local):
            raise SessionContractError("open_local must be HH:MM:SS")
        if not isinstance(close_local, str) or not _CLOCK.match(close_local):
            raise SessionContractError("close_local must be HH:MM:SS")
        open_clock = time.fromisoformat(open_local)
        close_clock = time.fromisoformat(close_local)
        if close_clock <= open_clock:
            raise SessionContractError("close_local must be after open_local")
        source_id = item.get("source_id")
        if source_id not in sources:
            raise SessionContractError("row source_id is not in sources")
        open_utc = datetime.combine(day, open_clock, tzinfo=zone).astimezone(timezone.utc)
        close_utc = datetime.combine(day, close_clock, tzinfo=zone).astimezone(timezone.utc)
        rows.append(
            SessionRow(
                venue_mic=venue,
                session_date=day,
                open_local=open_local,
                close_local=close_local,
                status=status,
                row_available_at=_parse_aware(item.get("row_available_at"), "row_available_at"),
                source_id=source_id,
                open_utc=open_utc,
                close_utc=close_utc,
            )
        )
    rows.sort(key=lambda row: row.session_date)
    return rows
