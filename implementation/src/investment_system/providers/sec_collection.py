"""Bounded US17 SEC collection, separate from analysis and publication.

Importing this module performs no requests or environment lookup. The caller
provides the private descriptive User-Agent at runtime. A client serializes its
requests, including retries, below SEC's maximum 10 requests per second; other
processes/Workers still require shared operational coordination.
"""

from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..markets.us import US_LISTINGS
from ..public_price_boundary import require_financial_url
from .sec_companyfacts import SEC_FACTS_URL
from .sec_submissions import URL as SUBMISSIONS_URL


SEC_USER_AGENT_SLOT = "SEC_USER_AGENT"
MAX_BODY_BYTES = 32 * 1024 * 1024
REQUEST_TIMEOUT = 20.0
MIN_REQUEST_INTERVAL = 0.2
MAX_ATTEMPTS = 5
MAX_RETRY_WAIT = 60.0
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class SecCollectionError(OSError):
    """Fixed value-free error codes suitable for the existing batch runner."""

    def __init__(self, code, *, stage=None, http_status=None):
        super().__init__(code)
        self.stage = stage if stage in ('fetch', 'parse', 'normalize') else None
        self.http_status = http_status if type(http_status) is int and 400 <= http_status <= 599 else None


@dataclass(frozen=True)
class SecResponse:
    status: int
    body: bytes = field(repr=False)
    retry_after: str | None = field(default=None, repr=False)
    final_url: str | None = field(default=None, repr=False)


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SecCollectionError("SEC_REDIRECT_REJECTED") from None


def _require_url(url: str) -> None:
    try:
        require_financial_url(url)
    except (ValueError, TypeError):
        raise SecCollectionError("SEC_URL_NOT_ALLOWED") from None


def default_transport(
    url: str, *, headers: Mapping[str, str], timeout: float,
    max_body_bytes: int,
) -> SecResponse:
    """Use fixed SEC routes, no redirects, and a bounded body read.

    HTTP error bodies are not read. Transient network exceptions are handled by
    SecCollectionClient, which replaces their contents with fixed error codes.
    """
    _require_url(url)
    if (type(max_body_bytes) is not int or not 0 < max_body_bytes <= MAX_BODY_BYTES
            or type(timeout) not in (int, float) or not math.isfinite(timeout)
            or not 0 < timeout <= REQUEST_TIMEOUT):
        raise SecCollectionError("SEC_CONFIG_INVALID") from None
    request = Request(url, headers=dict(headers))
    try:
        with build_opener(_RejectRedirects()).open(request, timeout=timeout) as response:
            body = response.read(max_body_bytes + 1)
            if len(body) > max_body_bytes:
                raise SecCollectionError("SEC_RESPONSE_TOO_LARGE") from None
            return SecResponse(response.status, body, response.headers.get("Retry-After"),
                               response.geturl())
    except HTTPError as error:
        return SecResponse(error.code, b"",
                           error.headers.get("Retry-After") if error.headers else None,
                           error.geturl())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError("nonfinite JSON value")


def _validate_body(body: bytes, expected_cik: str) -> None:
    try:
        payload = json.loads(body.decode("utf-8"), parse_constant=_reject_constant,
                             object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, RecursionError):
        raise SecCollectionError("SEC_JSON_INVALID") from None
    if not isinstance(payload, dict):
        raise SecCollectionError("SEC_JSON_INVALID") from None
    cik = payload.get("cik")
    bound = ((type(cik) is int and 0 < cik < 10 ** 10
              and str(cik).zfill(10) == expected_cik)
             or (isinstance(cik, str) and re.fullmatch(r"[0-9]{10}", cik)
                 and cik == expected_cik))
    if not bound:
        raise SecCollectionError("SEC_CIK_MISMATCH") from None
    # JSON's ordinary decoder also accepts overflowed numeric literals (1e999).
    pending = [payload]
    while pending:
        value = pending.pop()
        if isinstance(value, float) and not math.isfinite(value):
            raise SecCollectionError("SEC_JSON_INVALID") from None
        if isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


class SecCollectionClient:
    """Serial, retry-bounded loader compatible with sec_m1_inputs.run_batch.

    collect returns the supplied SEC bytes and their final UTC acquisition bound,
    not a historical first-publication timestamp. It performs no persistence,
    scheduling, scoring or public serialization.
    """

    def __init__(
        self, user_agent: str, *, transport: Callable = default_transport,
        sleep: Callable = time.sleep, monotonic: Callable = time.monotonic,
        now: Callable = _utc_now,
    ) -> None:
        if not isinstance(user_agent, str) or not re.fullmatch(r"[\x20-\x7e]{1,512}", user_agent):
            raise SecCollectionError("SEC_USER_AGENT_INVALID") from None
        contact = re.search(r"\S+@\S+\.\S+", user_agent)
        if (contact is None or not (user_agent[:contact.start()] + user_agent[contact.end():]).strip()
                or ".invalid" in user_agent.lower()):
            raise SecCollectionError("SEC_USER_AGENT_INVALID") from None
        if not all(callable(value) for value in (transport, sleep, monotonic, now)):
            raise SecCollectionError("SEC_CONFIG_INVALID") from None
        self._user_agent = user_agent
        self._transport = transport
        self._sleep = sleep
        self._monotonic = monotonic
        self._now = now
        self._last_request_at: float | None = None
        self._lock = threading.Lock()

    def _time(self) -> float:
        try:
            value = self._monotonic()
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError()
            return float(value)
        except Exception:
            raise SecCollectionError("SEC_CLOCK_INVALID") from None

    def _utc(self) -> datetime:
        try:
            value = self._now()
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise ValueError()
            return value.astimezone(timezone.utc)
        except Exception:
            raise SecCollectionError("SEC_CLOCK_INVALID") from None

    def _pause(self, seconds: float) -> None:
        try:
            self._sleep(seconds)
        except Exception:
            raise SecCollectionError("SEC_SLEEP_FAILED") from None

    def _pace(self) -> None:
        current = self._time()
        if self._last_request_at is not None:
            if current < self._last_request_at:
                raise SecCollectionError("SEC_CLOCK_INVALID") from None
            deadline = self._last_request_at + MIN_REQUEST_INTERVAL
            wait = deadline - current
            if wait > 0:
                self._pause(wait)
                current = self._time()
                # Allow a single representational rounding step, not a sleeper
                # or clock that failed to advance to the request deadline.
                if current + math.ulp(current) < deadline:
                    raise SecCollectionError("SEC_CLOCK_INVALID") from None
        self._last_request_at = current

    def _retry_wait(self, header: str | None, backoff: float) -> float:
        wait = backoff
        if header is not None:
            if re.fullmatch(r"[0-9]+", header):
                # Avoid converting an arbitrarily large header to an integer.
                normalized = header.lstrip("0") or "0"
                if len(normalized) > 2 or int(normalized) > MAX_RETRY_WAIT:
                    raise SecCollectionError("SEC_RETRY_AFTER_EXCEEDS_BUDGET") from None
                wait = max(wait, float(normalized))
            else:
                try:
                    retry_at = parsedate_to_datetime(header)
                except (ValueError, TypeError, OverflowError):
                    retry_at = None
                if retry_at is not None and retry_at.tzinfo is not None:
                    wait = max(wait, (retry_at.astimezone(timezone.utc) - self._utc()).total_seconds())
        if wait > MAX_RETRY_WAIT:
            raise SecCollectionError("SEC_RETRY_AFTER_EXCEEDS_BUDGET") from None
        return wait

    def _request(self, url: str, cik: str) -> bytes:
        _require_url(url)
        for attempt in range(MAX_ATTEMPTS):
            self._pace()
            try:
                response = self._transport(
                    url, headers={"User-Agent": self._user_agent, "Accept": "application/json"},
                    timeout=REQUEST_TIMEOUT, max_body_bytes=MAX_BODY_BYTES,
                )
            except SecCollectionError as error:
                # The default transport emits these fixed codes. An injected
                # transport cannot smuggle its own values through this class.
                allowed = {"SEC_URL_NOT_ALLOWED", "SEC_CONFIG_INVALID",
                           "SEC_REDIRECT_REJECTED", "SEC_RESPONSE_TOO_LARGE"}
                code = error.args[0] if len(error.args) == 1 else None
                raise SecCollectionError(
                    code if isinstance(code, str) and code in allowed else "SEC_TRANSPORT_FAILED") from None
            except HTTPError as error:
                response = SecResponse(error.code, b"",
                                       error.headers.get("Retry-After") if error.headers else None,
                                       error.geturl())
            except (URLError, OSError):
                if attempt == MAX_ATTEMPTS - 1:
                    raise SecCollectionError("SEC_TRANSPORT_RETRIES_EXHAUSTED") from None
                self._pause(2.0 ** (attempt + 1))
                continue
            except Exception:
                raise SecCollectionError("SEC_TRANSPORT_FAILED") from None
            if (not isinstance(response, SecResponse) or type(response.status) is not int
                    or not 100 <= response.status <= 599 or not isinstance(response.body, bytes)
                    or response.retry_after is not None and not isinstance(response.retry_after, str)):
                raise SecCollectionError("SEC_RESPONSE_INVALID") from None
            if response.final_url != url:
                raise SecCollectionError("SEC_RESPONSE_URL_MISMATCH") from None
            if len(response.body) > MAX_BODY_BYTES:
                raise SecCollectionError("SEC_RESPONSE_TOO_LARGE") from None
            if response.status == 200:
                try: _validate_body(response.body, cik)
                except SecCollectionError as error:
                    raise SecCollectionError(error.args[0], stage='parse') from None
                return response.body
            if response.status not in RETRY_STATUSES:
                raise SecCollectionError(f"SEC_HTTP_{response.status}", stage="fetch", http_status=response.status) from None
            if attempt == MAX_ATTEMPTS - 1:
                raise SecCollectionError("SEC_HTTP_RETRIES_EXHAUSTED", stage="fetch", http_status=response.status) from None
            self._pause(self._retry_wait(response.retry_after, 2.0 ** (attempt + 1)))
        raise SecCollectionError("SEC_TRANSPORT_FAILED") from None

    def collect(self, company_id: str, cik: str) -> tuple[bytes, bytes, datetime]:
        if (not isinstance(company_id, str) or company_id not in US_LISTINGS
                or not isinstance(cik, str) or cik != US_LISTINGS[company_id]["cik"]):
            raise SecCollectionError("SEC_ISSUER_NOT_ALLOWED") from None
        with self._lock:
            facts = self._request(SEC_FACTS_URL.format(cik=cik), cik)
            submissions = self._request(SUBMISSIONS_URL.format(cik=cik), cik)
            return facts, submissions, self._utc()
