"""`research-request/1`: a research data request for the private area (design PRIVATE_AREA_KIS_DESIGN_20261031.md §20, §20.1).

Codex (backtest research) asks for KIS data with one JSON request, the body of an issue in the private repository (security
review A3, 10/31: Codex has read-only Contents plus Issues there, never Contents write). The private repository's one request
workflow (Main only, DC-35; triggered by `issues: opened`, schedule or dispatch, never push) validates it with this module and
fetches through the KIS adapter into `shared/research/<request_id>/` (`rr-` ids can never be the reserved `legacy` folder).
This module only validates and plans: no network, no file, no Secret, no clock (callers pass `today`). Errors carry a fixed
code and never echo the request.

Format (every key required, no other key at any level):

    {"schema": "research-request/1",
     "request_id": "rr-20261031-momentum-12m",            rr-<YYYYMMDD, not after today>-<lowercase words joined by '-'>, <= 64
     "symbols": ["AAPL", "BRK.B"],                         1..MAX_SYMBOLS unique US tickers: 1-5 capitals, optional .A / .AB class
     "period": {"start": "2016-01-04", "end": "2025-12-31"},   MIN_START <= start <= today, start <= end, <= MAX_PERIOD_DAYS
     "items": ["daily_raw", "volume"],                     non-empty unique subset of ITEMS
     "frequency": "once",                                  once: end <= today; daily: end <= today + DAILY_MAX_AHEAD_DAYS
     "purpose": "momentum backtest on real closes"}        one line, <= PURPOSE_MAX_CHARS, no URL / e-mail / key-like token

The whole file is at most MAX_REQUEST_BYTES of UTF-8 JSON (no duplicate key, no NaN). The words order / trading / balance /
account and 주문 / 매매 / 잔고 / 계좌 are refused anywhere in the request (any key or string, any case, inside longer words
too, after NFKC), and purpose may not hide them behind control or format characters.

`plan(request, backfill_done=False)` turns a validated request into KIS call descriptors: token issue, then per symbol one
overseas period quote per series (RAW: MODP 0, for daily_raw / volume / dollar_volume; ADJUSTED_CROSSCHECK: MODP 1, for
daily_adjusted_crosscheck), then token revoke. Each descriptor passes kis_routes.require_route; there is no host and no call
here. `{EXCD}` and `{SYMB}` come from the KIS master, `{BYMD}` is filled by the private collector:
- fetch BACKFILL (`pages` calls): BYMD steps back BYMD_PAGE_DAYS trading days at a time from window.end (once) or from the
  latest US trading day (daily) down to window.start;
- fetch NEWEST_PAGE (one call): a `daily` request whose first backfill is done (`backfill_done=True`) asks only for the page
  ending at the latest US trading day. The backfill-done state lives in the private repository at
  `shared/research/<request_id>/state.json` (written by the request workflow after a complete backfill, read by it before
  calling plan(); this module reads no file). A `once` request has nothing left after its backfill: REQUEST_ALREADY_DONE.

Cost (security review A8, 10/31): the returned list has `estimated_calls` = Σ over symbols of series × pages, where pages =
ceil(weekdays in [start, end] / BYMD_PAGE_DAYS) for a backfill and 1 for a newest page (token calls not counted). Weekdays
(Mon–Fri) bound US trading days from above, so the estimate never undercounts. A request whose first run would exceed
MAX_ESTIMATED_CALLS is refused with REQUEST_TOO_COSTLY (by the dataclass, so validate_request and parse_request refuse it too).
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import re
import unicodedata

from . import kis_routes

SCHEMA = "research-request/1"
MAX_REQUEST_BYTES = 16 * 1024
MAX_SYMBOLS = 600
MIN_START = dt.date(2000, 1, 1)
MAX_PERIOD_DAYS = 3653            # ten years
DAILY_MAX_AHEAD_DAYS = 366        # a daily request ends within a year
PURPOSE_MAX_CHARS = 120
ITEMS = ("daily_raw", "daily_adjusted_crosscheck", "volume", "dollar_volume")
FREQUENCIES = ("once", "daily")
FORBIDDEN_WORDS = kis_routes.FORBIDDEN_ROUTE_WORDS + ("주문", "매매", "잔고", "계좌")
KEYS = ("schema", "request_id", "symbols", "period", "items", "frequency", "purpose")
PERIOD_KEYS = ("start", "end")
REQUEST_ID_MAX_CHARS = 64
BYMD_PAGE_DAYS = 100              # trading days per overseas period-quote call (design §3.2)
MAX_ESTIMATED_CALLS = 6000        # one request's first run: about 10 minutes at 10 calls a second (security review A8)

_REQUEST_ID = re.compile(r"rr-([0-9]{8})-[a-z0-9]+(?:-[a-z0-9]+)*")
_SYMBOL = re.compile(r"[A-Z]{1,5}(?:\.[A-Z]{1,2})?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_URL = re.compile(r"(?i)[a-z][a-z0-9+.-]*://|www\.|[a-z0-9-]+\.(?:com|net|org|io|dev|app|kr|co|me|ai|gov|edu|info|xyz)\b")
_KEY_LIKE = re.compile(r"[A-Za-z0-9_+/=-]{16,}")
_LONG_DIGITS = re.compile(r"[0-9]{8,}")
_RAW_SERIES_ITEMS = ("daily_raw", "volume", "dollar_volume")


class ResearchRequestError(ValueError):
    """Fixed code only; never a value from the request."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise ResearchRequestError(code)


def _strings(value: object):
    """Every key and string of a parsed JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _forbidden(text: str) -> bool:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return any(word in folded for word in FORBIDDEN_WORDS)


def _date(text: object, code: str) -> dt.date:
    _need(type(text) is str and _DATE.fullmatch(text) is not None, code)
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ResearchRequestError(code) from None


def _request_id_date(request_id: str) -> dt.date:
    digits = _REQUEST_ID.fullmatch(request_id).group(1)
    try:
        return dt.date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
    except ValueError:
        raise ResearchRequestError("REQUEST_ID_INVALID") from None


def _purpose_ok(purpose: str) -> bool:
    if not purpose.strip() or purpose != purpose.strip() or len(purpose) > PURPOSE_MAX_CHARS:
        return False
    # One line of visible text: no control, format (zero-width, bidi), surrogate, private-use or unassigned character.
    if any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"} for ch in purpose):
        return False
    if "@" in purpose or _URL.search(purpose) or _LONG_DIGITS.search(purpose):
        return False
    return not any(any(c.isdigit() for c in token) or len(token) >= 24 for token in _KEY_LIKE.findall(purpose))


def weekdays(start: dt.date, end: dt.date) -> int:
    """Mon–Fri days in [start, end] (0 when end < start): an upper bound on US trading days (holidays are not subtracted)."""
    if end < start:
        return 0
    full_weeks, rest = divmod((end - start).days + 1, 7)
    first = start.weekday()
    return full_weeks * 5 + sum(1 for k in range(rest) if (first + k) % 7 < 5)


def _series(items: tuple) -> list:
    """(series name, MODP, items) per KIS series a request needs."""
    series = []
    raw_items = [i for i in ITEMS if i in items and i in _RAW_SERIES_ITEMS]
    if raw_items:
        series.append(("RAW", "0", raw_items))
    if "daily_adjusted_crosscheck" in items:
        series.append(("ADJUSTED_CROSSCHECK", "1", ["daily_adjusted_crosscheck"]))
    return series


def _pages(start: dt.date, end: dt.date, newest_only: bool) -> int:
    return 1 if newest_only else max(1, -(-weekdays(start, end) // BYMD_PAGE_DAYS))


@dataclass(frozen=True)
class ResearchRequest:
    """A request that passed every check that does not depend on today's date (validate_request adds those)."""

    request_id: str
    symbols: tuple
    start: dt.date
    end: dt.date
    items: tuple
    frequency: str
    purpose: str

    def __post_init__(self):
        _need(type(self.request_id) is str and len(self.request_id) <= REQUEST_ID_MAX_CHARS
              and _REQUEST_ID.fullmatch(self.request_id) is not None, "REQUEST_ID_INVALID")
        _request_id_date(self.request_id)
        _need(type(self.symbols) is tuple and 1 <= len(self.symbols) <= MAX_SYMBOLS, "SYMBOLS_COUNT")
        _need(all(type(s) is str and _SYMBOL.fullmatch(s) is not None for s in self.symbols), "SYMBOL_INVALID")
        _need(len(set(self.symbols)) == len(self.symbols), "SYMBOL_DUPLICATE")
        _need(type(self.start) is dt.date and type(self.end) is dt.date, "PERIOD_INVALID")
        _need(MIN_START <= self.start <= self.end, "PERIOD_BOUNDS")
        _need((self.end - self.start).days <= MAX_PERIOD_DAYS, "PERIOD_TOO_LONG")
        _need(type(self.items) is tuple and self.items and all(type(i) is str and i in ITEMS for i in self.items), "ITEMS_INVALID")
        _need(len(set(self.items)) == len(self.items), "ITEMS_INVALID")
        _need(type(self.frequency) is str and self.frequency in FREQUENCIES, "FREQUENCY_INVALID")
        _need(type(self.purpose) is str and _purpose_ok(self.purpose), "PURPOSE_INVALID")
        _need(not any(_forbidden(text) for text in (self.request_id, self.purpose, *self.symbols)), "FORBIDDEN_WORD")
        _need(len(self.symbols) * len(_series(self.items)) * _pages(self.start, self.end, False) <= MAX_ESTIMATED_CALLS,
              "REQUEST_TOO_COSTLY")

    def as_dict(self) -> dict:
        return {"schema": SCHEMA, "request_id": self.request_id, "symbols": list(self.symbols),
                "period": {"start": self.start.isoformat(), "end": self.end.isoformat()}, "items": list(self.items),
                "frequency": self.frequency, "purpose": self.purpose}


def validate_request(value: object, *, today: dt.date) -> ResearchRequest:
    """A parsed `research-request/1` object -> ResearchRequest, or ResearchRequestError(code)."""
    _need(type(today) is dt.date, "TODAY_INVALID")
    _need(type(value) is dict, "NOT_AN_OBJECT")
    # Order / trading / balance / account words anywhere: checked first, on every key and string at any depth.
    _need(not any(_forbidden(text) for text in _strings(value)), "FORBIDDEN_WORD")
    _need(set(value) == set(KEYS), "UNKNOWN_OR_MISSING_KEY")
    _need(value["schema"] == SCHEMA and type(value["schema"]) is str, "SCHEMA_INVALID")
    period = value["period"]
    _need(type(period) is dict and set(period) == set(PERIOD_KEYS), "UNKNOWN_OR_MISSING_KEY")
    symbols, items = value["symbols"], value["items"]
    _need(type(symbols) is list, "SYMBOLS_COUNT")
    _need(type(items) is list, "ITEMS_INVALID")
    _need(len(set(i for i in items if type(i) is str)) == len(items), "ITEMS_INVALID")
    request = ResearchRequest(
        request_id=value["request_id"], symbols=tuple(symbols),
        start=_date(period["start"], "PERIOD_INVALID"), end=_date(period["end"], "PERIOD_INVALID"),
        items=tuple(sorted(items, key=lambda i: ITEMS.index(i) if i in ITEMS else len(ITEMS))),
        frequency=value["frequency"], purpose=value["purpose"])
    _need(_request_id_date(request.request_id) <= today, "REQUEST_ID_INVALID")
    _need(request.start <= today, "PERIOD_BOUNDS")
    ahead = 0 if request.frequency == "once" else DAILY_MAX_AHEAD_DAYS
    _need(request.end <= today + dt.timedelta(days=ahead), "PERIOD_BOUNDS")
    return request


def _unique_pairs(pairs: list) -> dict:
    result = {}
    for key, child in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = child
    return result


def _reject_constant(_name: str) -> None:
    raise ValueError("non-finite number")


def parse_request(raw: bytes, *, today: dt.date) -> ResearchRequest:
    """The bytes of one request file -> ResearchRequest. The size limit applies before decoding."""
    _need(type(raw) is bytes, "NOT_BYTES")
    _need(len(raw) <= MAX_REQUEST_BYTES, "REQUEST_TOO_LARGE")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_pairs,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise ResearchRequestError("INVALID_JSON") from None
    return validate_request(value, today=today)


class Plan(list):
    """plan()'s result: the call descriptors in order (a plain list otherwise) and `estimated_calls`, the number of overseas
    period-quote calls the collector will make for them (token calls not counted)."""

    estimated_calls = 0


def plan(request: ResearchRequest, *, backfill_done: bool = False) -> Plan:
    """KIS call descriptors for a validated request (see the module notes). Every descriptor passes require_route."""
    _need(type(request) is ResearchRequest, "PLAN_NEEDS_VALIDATED_REQUEST")
    _need(type(backfill_done) is bool, "PLAN_BACKFILL_STATE_INVALID")
    _need(not (backfill_done and request.frequency == "once"), "REQUEST_ALREADY_DONE")
    series = _series(request.items)
    pages = _pages(request.start, request.end, backfill_done)
    fetch = "NEWEST_PAGE" if backfill_done else "BACKFILL"

    def call(name: str, params: dict, **extra) -> dict:
        route = kis_routes.ROUTES[name]
        return {"route": name, "method": route["method"], "path": route["path"], "tr_id": route["tr_id"], "params": params,
                **extra}

    calls = [call("TOKEN_ISSUE", {})]
    window = {"start": request.start.isoformat(), "end": request.end.isoformat()}
    for symbol in request.symbols:
        for name, modp, items in series:
            params = {"AUTH": "", "EXCD": "{EXCD}", "SYMB": "{SYMB}", "GUBN": "0", "BYMD": "{BYMD}", "MODP": modp}
            calls.append(call("OVERSEAS_DAILY_PRICE", params, symbol=symbol, series=name, items=list(items),
                              window=dict(window), frequency=request.frequency, fetch=fetch, pages=pages))
    calls.append(call("TOKEN_REVOKE", {}))
    for descriptor in calls:
        kis_routes.require_route(descriptor)
    result = Plan(calls)
    result.estimated_calls = sum(c.get("pages", 0) for c in calls)
    _need(result.estimated_calls <= MAX_ESTIMATED_CALLS, "REQUEST_TOO_COSTLY")
    return result
