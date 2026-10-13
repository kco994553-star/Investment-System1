"""Collect the macro v0 official responses (run in GitHub Actions only).

Inflation + Labor: one BLS public API v1 request (no key), CUUR0000SA0 and
           LNS14000000, three calendar years.
Growth:    BEA NIPA quarterly flat file (no key); only when that fails and the
           optional `BEA_USERID` setting exists, the BEA API table T10101.
Monetary Policy / Liquidity / Credit: Federal Reserve Data Download Program CSV
           (H.15 / H.4.1 / H.8). The H.15 package is read from the official
           pointer file H15_FF_O.txt; the H.4.1 / H.8 package hashes are
           candidates to verify on the first Actions run (the parser selects the
           series by its official identifier/description or fails closed).
Fiscal:    Treasury FiscalData MTS Table 1 (no key), one page.
FX is never collected here: the public price boundary excludes it.

Importing performs no request or environment lookup. Raw bodies go only to the
caller's private temporary directory; the public projection keeps their sha256.
Request URLs, the BEA UserID and provider messages are never printed or returned.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Mapping
import re
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ..macro.growth_inflation_v0 import BEA_FLAT_Q_URL, INFLATION_SERIES_CODE
from ..macro.primary_contract import ENDPOINTS

BEA_KEY_SLOT = "BEA_USERID"
USER_AGENT = "Investment-System1 macro-v0 public statistics collector"
TIMEOUT = 60.0
MAX_BYTES = 256 * 1024 * 1024
BLS_MAX_BYTES = 4 * 1024 * 1024
FED_DDP_URL = "https://www.federalreserve.gov/datadownload/Output.aspx"
H15_POINTER_URL = "https://www.federalreserve.gov/releases/h15/data/Business_day/H15_FF_O.txt"
MTS_TABLE_1_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1"
ALLOWED = (ENDPOINTS["BLS"], ENDPOINTS["BEA"], BEA_FLAT_Q_URL, FED_DDP_URL, H15_POINTER_URL, MTS_TABLE_1_URL)
LABOR_SERIES_CODE = "LNS14000000"
FED_MAX_BYTES = 32 * 1024 * 1024
MTS_MAX_BYTES = 16 * 1024 * 1024
POINTER_MAX_BYTES = 1024 * 1024
# CANDIDATE_UNVERIFIED (2026-10-11): DDP package hashes seen on federalreserve.gov download links; the series
# they contain is not confirmed from this environment. The first Actions run proves or refutes them: a package
# without the target series yields SERIES_NOT_FOUND, never another series. None = not configured.
FED_DDP_PACKAGES = {
    "Liquidity": {"rel": "H41", "series": "efce2c1a8744855f2623889dffb2b39a", "package": False, "years": 2},
    "Credit": {"rel": "H8", "series": "9a538c893f62322f942501e38030aed5", "package": True, "years": 2},
}
_DDP_KEYS = ("rel", "series", "lastobs", "from", "to", "filetype", "label", "layout", "type")
_HASH = re.compile(r"[0-9a-f]{32}", re.ASCII)


class MacroV0FetchError(OSError):
    """Value-free failure; carries no URL, key or provider text.

    Diagnostics are fixed tokens only: the HTTP status number, a content-type class and a body-size class.
    """

    def __init__(self, code, *, status=None, content=None, size=None):
        super().__init__(code)
        self.code = code
        self.status = status if type(status) is int else None
        self.content = content
        self.size = size


def _content_class(value) -> str:
    """Fixed class of a Content-Type header (never the raw header text)."""
    text = str(value or "").split(";", 1)[0].strip().lower()
    for token, label in (("csv", "CSV"), ("html", "HTML"), ("json", "JSON"), ("zip", "ZIP"), ("xml", "XML"), ("text/plain", "TEXT")):
        if token in text:
            return label
    return "NONE" if not text else "OTHER"


def _size_class(n) -> str:
    if not isinstance(n, int) or n <= 0:
        return "0"
    for limit, label in ((1024, "<1KB"), (65536, "<64KB"), (1048576, "<1MB")):
        if n < limit:
            return label
    return ">=1MB"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise MacroV0FetchError("REDIRECT_REJECTED")


def _query_allowed(url: str, query: str | None) -> bool:
    """Fixed hosts and paths; Fed DDP and FiscalData queries are limited to fixed keys."""
    if url == FED_DDP_URL:
        try:
            params = parse_qsl(query or "", keep_blank_values=True, strict_parsing=True)
        except ValueError:
            return False
        keys = [k for k, _ in params]
        values = dict(params)
        return (len(keys) == len(set(keys)) and set(keys) <= set(_DDP_KEYS)
                and values.get("rel") in ("H15", "H41", "H8") and _HASH.fullmatch(values.get("series", "")) is not None
                and values.get("filetype") == "csv" and values.get("type", "package") == "package")
    if url == MTS_TABLE_1_URL:
        try:
            params = parse_qsl(query or "", keep_blank_values=True, strict_parsing=True)
        except ValueError:
            return False
        return all(k in ("filter", "sort", "format", "page[number]", "page[size]") for k, _ in params)
    return url != H15_POINTER_URL or query is None


def default_transport(url: str, *, data: bytes | None, query: str | None, max_bytes: int) -> bytes:
    if url not in ALLOWED or not _query_allowed(url, query):
        raise MacroV0FetchError("URL_NOT_ALLOWED")
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url + ("?" + query if query else ""), data=data, headers=headers,
                      method="POST" if data is not None else "GET")
    content = None
    try:
        with build_opener(_NoRedirect()).open(request, timeout=TIMEOUT) as response:
            content = _content_class(response.headers.get("Content-Type"))
            if response.status != 200:
                raise MacroV0FetchError("HTTP_STATUS", status=response.status, content=content)
            body = response.read(max_bytes + 1)
    except MacroV0FetchError:
        raise
    except HTTPError as error:
        raise MacroV0FetchError("HTTP_STATUS", status=error.code, content=_content_class(error.headers.get("Content-Type") if error.headers else None)) from None
    except Exception as error:
        timeout = isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)
        raise MacroV0FetchError("TIMEOUT" if timeout else "FETCH_FAILED") from None
    if not body or len(body) > max_bytes:
        raise MacroV0FetchError("BODY_SIZE", status=200, content=content, size=_size_class(len(body or b"")))
    return body


def _now() -> datetime:
    return datetime.now(timezone.utc)


def h15_package(pointer: bytes) -> dict:
    """The single DDP package link for RIFSPFF_N.B named in the official H15_FF_O.txt pointer file."""
    content = pointer.decode("utf-8", "replace").replace("&amp;", "&")
    found = {}
    for link in re.findall(r"https?://www\.federalreserve\.gov/datadownload/Output\.aspx\?[^\s\"'<>]+", content):
        try:
            params = dict(parse_qsl(link.split("?", 1)[1], keep_blank_values=True))
        except ValueError:
            continue
        if params.get("rel") == "H15" and _HASH.fullmatch(params.get("series", "")):
            found[params["series"]] = params.get("type") == "package"
    if len(found) != 1:
        raise MacroV0FetchError("POINTER_INVALID")
    series, package = next(iter(found.items()))
    return {"rel": "H15", "series": series, "package": package, "years": 1}


def ddp_query(package: dict, year: int) -> str:
    params = [("rel", package["rel"]), ("series", package["series"]), ("lastobs", ""),
              ("from", "01/01/%04d" % (year - package["years"])), ("to", ""), ("filetype", "csv"),
              ("label", "include"), ("layout", "seriescolumn")]
    if package["package"]:
        params.append(("type", "package"))
    return urlencode(params)


def mts_query(year: int) -> str:
    return urlencode((("filter", "record_date:gte:%04d-01-01" % (year - 2)), ("sort", "record_date"),
                      ("format", "json"), ("page[number]", "1"), ("page[size]", "10000")))


def _diagnostic(axis, stage, error, package=None) -> dict:
    """Fixed-token fetch diagnostic for the Actions log (no URL, key, body or provider text)."""
    return {"axis": axis, "stage": stage,
            "code": getattr(error, "code", None) if isinstance(error, MacroV0FetchError) else "PARSE_OR_TRANSPORT_ERROR",
            "http": getattr(error, "status", None), "content": getattr(error, "content", None), "size": getattr(error, "size", None),
            "rel": (package or {}).get("rel"), "series8": str((package or {}).get("series", ""))[:8] or None,
            "type": None if package is None else ("package" if package.get("package") else "series")}


def collect_macro_v0(root: Path, *, environ: Mapping[str, str], year: int | None = None,
                     transport: Callable[..., bytes] = default_transport,
                     clock: Callable[[], datetime] = _now, diagnostics: list | None = None) -> list[dict]:
    """Return `manifest['macro_v0']` entries; failures become reason-only entries.

    `diagnostics`, when given, receives one fixed-token dict per failed Fed fetch (pointer or DDP package).
    """
    root = Path(root)
    year = year if type(year) is int else clock().year
    entries = []

    def capture(axis, fmt, name, fetch, also=()):
        body = fetch()
        acquired = clock().astimezone(timezone.utc)
        (root / name).write_bytes(body)
        for each in (axis, *also):
            entries.append({"axis": each, "format": fmt, "file": name,
                            "acquired_at": acquired.isoformat(), "synthetic": False})

    try:
        # One batched BLS v1 request for both series (daily request limit).
        payload = json.dumps({"seriesid": [INFLATION_SERIES_CODE, LABOR_SERIES_CODE], "startyear": str(year - 2),
                              "endyear": str(year)}, separators=(",", ":")).encode()
        capture("Inflation", "BLS_API_V1_JSON", "macro-v0-bls.json",
                lambda: transport(ENDPOINTS["BLS"], data=payload, query=None, max_bytes=BLS_MAX_BYTES), also=("Labor",))
    except Exception:
        entries.extend({"axis": a, "reason": "SOURCE_NOT_AVAILABLE"} for a in ("Inflation", "Labor"))

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

    def fed(axis, package, name):
        if package is None or _HASH.fullmatch(str(package.get("series"))) is None:
            entries.append({"axis": axis, "reason": "SERIES_NOT_CONFIGURED"})
            return
        try:
            capture(axis, "FED_DDP_CSV", name, lambda: transport(FED_DDP_URL, data=None, query=ddp_query(package, year),
                                                                 max_bytes=FED_MAX_BYTES))
        except Exception as error:
            entries.append({"axis": axis, "reason": "SOURCE_NOT_AVAILABLE"})
            if diagnostics is not None:
                diagnostics.append(_diagnostic(axis, "DDP_PACKAGE", error, package))

    try:
        h15 = h15_package(transport(H15_POINTER_URL, data=None, query=None, max_bytes=POINTER_MAX_BYTES))
    except Exception as error:
        entries.append({"axis": "Monetary Policy", "reason": "SOURCE_NOT_AVAILABLE"})
        if diagnostics is not None:
            diagnostics.append(_diagnostic("Monetary Policy", "H15_POINTER", error))
    else:
        fed("Monetary Policy", h15, "macro-v0-fed-h15.csv")
    fed("Liquidity", FED_DDP_PACKAGES.get("Liquidity"), "macro-v0-fed-h41.csv")
    fed("Credit", FED_DDP_PACKAGES.get("Credit"), "macro-v0-fed-h8.csv")
    try:
        capture("Fiscal", "FISCALDATA_MTS_JSON", "macro-v0-mts-table-1.json",
                lambda: transport(MTS_TABLE_1_URL, data=None, query=mts_query(year), max_bytes=MTS_MAX_BYTES))
    except Exception:
        entries.append({"axis": "Fiscal", "reason": "SOURCE_NOT_AVAILABLE"})
    return entries
