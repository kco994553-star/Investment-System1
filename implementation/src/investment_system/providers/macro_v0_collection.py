"""Collect the two macro v0 official responses (run in GitHub Actions only).

Inflation: BLS public API v1 (no key), series CUUR0000SA0, three calendar years.
Growth:    BEA NIPA quarterly flat file (no key); only when that fails and the
           optional `BEA_USERID` setting exists, the BEA API table T10101.

Importing performs no request or environment lookup. Raw bodies go only to the
caller's private temporary directory; the public projection keeps their sha256.
Request URLs, the BEA UserID and provider messages are never printed or returned.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..macro.growth_inflation_v0 import BEA_FLAT_Q_URL, INFLATION_SERIES_CODE
from ..macro.primary_contract import ENDPOINTS

BEA_KEY_SLOT = "BEA_USERID"
USER_AGENT = "Investment-System1 macro-v0 public statistics collector"
TIMEOUT = 60.0
MAX_BYTES = 256 * 1024 * 1024
BLS_MAX_BYTES = 4 * 1024 * 1024
ALLOWED = (ENDPOINTS["BLS"], ENDPOINTS["BEA"], BEA_FLAT_Q_URL)


class MacroV0FetchError(OSError):
    """Value-free failure; carries no URL, key or provider text."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise MacroV0FetchError("REDIRECT_REJECTED")


def default_transport(url: str, *, data: bytes | None, query: str | None, max_bytes: int) -> bytes:
    if url not in ALLOWED:
        raise MacroV0FetchError("URL_NOT_ALLOWED")
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url + ("?" + query if query else ""), data=data, headers=headers,
                      method="POST" if data is not None else "GET")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                raise MacroV0FetchError("HTTP_STATUS")
            body = response.read(max_bytes + 1)
    except MacroV0FetchError:
        raise
    except Exception:
        raise MacroV0FetchError("FETCH_FAILED") from None
    if not body or len(body) > max_bytes:
        raise MacroV0FetchError("BODY_SIZE")
    return body


def _now() -> datetime:
    return datetime.now(timezone.utc)


def collect_macro_v0(root: Path, *, environ: Mapping[str, str], year: int | None = None,
                     transport: Callable[..., bytes] = default_transport,
                     clock: Callable[[], datetime] = _now) -> list[dict]:
    """Return `manifest['macro_v0']` entries; failures become reason-only entries."""
    root = Path(root)
    year = year if type(year) is int else clock().year
    entries = []

    def capture(axis, fmt, name, fetch):
        body = fetch()
        acquired = clock().astimezone(timezone.utc)
        (root / name).write_bytes(body)
        entries.append({"axis": axis, "format": fmt, "file": name,
                        "acquired_at": acquired.isoformat(), "synthetic": False})

    try:
        payload = json.dumps({"seriesid": [INFLATION_SERIES_CODE], "startyear": str(year - 2),
                              "endyear": str(year)}, separators=(",", ":")).encode()
        capture("Inflation", "BLS_API_V1_JSON", "macro-v0-bls-cpi.json",
                lambda: transport(ENDPOINTS["BLS"], data=payload, query=None, max_bytes=BLS_MAX_BYTES))
    except Exception:
        entries.append({"axis": "Inflation", "reason": "SOURCE_NOT_AVAILABLE"})

    try:
        capture("Growth", "BEA_NIPA_FLAT_Q", "macro-v0-bea-nipa-q.txt",
                lambda: transport(BEA_FLAT_Q_URL, data=None, query=None, max_bytes=MAX_BYTES))
    except Exception:
        key = environ.get(BEA_KEY_SLOT) if hasattr(environ, "get") else None
        if not (isinstance(key, str) and key.strip()):
            entries.append({"axis": "Growth", "reason": "SOURCE_KEY_NOT_CONFIGURED"})
        else:
            query = urlencode((("UserID", key.strip()), ("method", "GetData"), ("DataSetName", "NIPA"),
                               ("TableName", "T10101"), ("Frequency", "Q"),
                               ("Year", ",".join(str(y) for y in range(year - 2, year + 1))),
                               ("ResultFormat", "JSON")))
            try:
                capture("Growth", "BEA_API_NIPA_JSON", "macro-v0-bea-api-t10101.json",
                        lambda: transport(ENDPOINTS["BEA"], data=None, query=query, max_bytes=BLS_MAX_BYTES))
            except Exception:
                entries.append({"axis": "Growth", "reason": "SOURCE_NOT_AVAILABLE"})
    return entries
