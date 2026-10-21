"""Collect the macro evidence lines inputs (MEV-1 P1 13) in the daily run; raw bodies stay in the caller's private
temporary directory, only parsed public statistics leave this module.

Reused, never fetched again (the macro v0 / lights v1 collection already holds them in the same private directory):
- E13 BLS LNS14000000 (macro-v0-bls.json), E25 BEA A191RL (macro-v0-bea-nipa-q.txt), E09 Treasury daily par yield
  curve (macro-v1-treasury-curve-YYYY.xml).
New fixed requests (no key unless stated):
- BLS public API v1, one batched POST: CES6056132001 (E16), CES3000000007 (E17), CUSR0000SA0L1E (E39);
- BEA NipaDataM.txt (E39 DPCCRG), Last-Modified kept as the posting time;
- Fed DDP CSV packages G.17 summary (E22) and SLOOS chart data (E36), plus their Choose pages ("last released" date);
- Fed Board openmarket.htm (E40 target range changes), Last-Modified kept;
- DOL ETA 539 national weekly claims XML (E14; collected, held from publication until its terms are confirmed);
- data.bts.gov TSI dataset rows (E01), Last-Modified kept;
- Census EITS time-series API (E21 M3 NXA, E26 NRC permits) only with the optional CENSUS_API_KEY setting.

Importing performs no request or environment lookup. Request URLs, keys and provider messages are never printed or
returned; failures are fixed reason codes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request, build_opener

from ..macro import evidence_sources as es
from ..macro.primary_contract import ENDPOINTS
from .macro_v0_collection import FED_DDP_URL, MacroV0FetchError, _NoRedirect, _content_class, _size_class

USER_AGENT = "Investment-System1 macro-evidence public statistics collector"
TIMEOUT = 60.0
CENSUS_KEY_SLOT = "CENSUS_API_KEY"
DOL_URL = "https://oui.doleta.gov/unemploy/wkclaims/report.asp"
BEA_FLAT_M_URL = "https://apps.bea.gov/national/Release/TXT/NipaDataM.txt"
DDP_CHOOSE_URL = "https://www.federalreserve.gov/datadownload/Choose.aspx"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/openmarket.htm"
BTS_URL = "https://data.bts.gov/resource/bw6n-ddqk.json"
CENSUS_URL = "https://api.census.gov/data/timeseries/eits/"
LIMITS = {ENDPOINTS["BLS"]: 4 << 20, BEA_FLAT_M_URL: 96 << 20, FED_DDP_URL: 16 << 20, DDP_CHOOSE_URL: 2 << 20,
          FOMC_URL: 2 << 20, DOL_URL: 4 << 20, BTS_URL: 2 << 20, CENSUS_URL + "m3": 4 << 20, CENSUS_URL + "resconst": 4 << 20}
_HASH = re.compile(r"[0-9a-f]{32}", re.ASCII)


def _params(query):
    try:
        return parse_qsl(query or "", keep_blank_values=True, strict_parsing=True)
    except ValueError:
        return None


def query_allowed(url: str, query: str | None, data: bytes | None) -> bool:
    """Fixed hosts, paths and query shapes; anything else is refused before a connection is made."""
    if url not in LIMITS:
        return False
    if url == ENDPOINTS["BLS"]:
        return query is None and data is not None
    if url == DOL_URL:
        params = _params(data.decode("ascii", "replace") if data else "")
        return (query is None and params is not None and [k for k, _ in params] == ["level", "final_yr", "strtdate", "enddate", "filetype"]
                and dict(params)["level"] == "us" and dict(params)["filetype"] == "xml"
                and all(re.fullmatch(r"\d{4}", dict(params)[k]) for k in ("final_yr", "strtdate", "enddate")))
    if data is not None:
        return False
    if url in (BEA_FLAT_M_URL, FOMC_URL):
        return query is None
    params = _params(query)
    if params is None:
        return False
    values = dict(params)
    if url == DDP_CHOOSE_URL:
        return params == [("rel", values.get("rel"))] and values.get("rel") in ("G17", "SLOOS")
    if url == FED_DDP_URL:
        allowed = {p["rel"]: p["series"] for p in es.DDP_PACKAGES.values()}
        return ([k for k, _ in params] == ["rel", "series", "lastobs", "from", "to", "filetype", "label", "layout", "type"]
                and allowed.get(values["rel"]) == values["series"] and values["filetype"] == "csv"
                and values["layout"] == "seriescolumn" and values["type"] == "package")
    if url == BTS_URL:
        return params == [("$select", "obs_date,tsi_freight"), ("$order", "obs_date DESC"), ("$limit", "180")]
    if url.startswith(CENSUS_URL):
        keys = [k for k, _ in params]
        base = ["get", "for", "time", "category_code", "data_type_code"]
        return (keys in (base, base + ["key"]) and values["for"] == "us:*"
                and any(url == CENSUS_URL + q["program"] and values["category_code"] == q["category"]
                        and values["data_type_code"] == q["data_type"] for q in es.CENSUS_QUERIES.values()))
    return False


def default_transport(url: str, *, data: bytes | None, query: str | None, form: bool = False) -> tuple[bytes, dict]:
    """(body, {'last-modified': value or None}); raises MacroV0FetchError with fixed tokens only."""
    if not query_allowed(url, query, data):
        raise MacroV0FetchError("URL_NOT_ALLOWED")
    limit = LIMITS[url]
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    request = Request(url + ("?" + query if query else ""), data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=TIMEOUT) as response:
            content = _content_class(response.headers.get("Content-Type"))
            if response.status != 200:
                raise MacroV0FetchError("HTTP_STATUS", status=response.status, content=content)
            body = response.read(limit + 1)
            modified = response.headers.get("Last-Modified")
    except MacroV0FetchError:
        raise
    except HTTPError as error:
        raise MacroV0FetchError("HTTP_STATUS", status=error.code) from None
    except Exception as error:
        timeout = isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)
        raise MacroV0FetchError("TIMEOUT" if timeout else "FETCH_FAILED") from None
    if not body or len(body) > limit:
        raise MacroV0FetchError("BODY_SIZE", status=200, content=content, size=_size_class(len(body or b"")))
    return body, {"last-modified": modified}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ddp_query(package) -> str:
    return urlencode((("rel", package["rel"]), ("series", package["series"]), ("lastobs", ""), ("from", ""), ("to", ""),
                      ("filetype", "csv"), ("label", "include"), ("layout", "seriescolumn"), ("type", "package")))


def census_query(spec, year: int, key: str | None) -> str:
    params = [("get", "cell_value,data_type_code,time_slot_id,category_code,seasonally_adj"), ("for", "us:*"),
              ("time", "from %04d" % (year - 9)), ("category_code", spec["category"]), ("data_type_code", spec["data_type"])]
    if key:
        params.append(("key", key))
    return urlencode(params)


def collect_macro_evidence(root: Path, manifest: Mapping, *, environ: Mapping[str, str], year: int | None = None,
                           transport: Callable[..., tuple] = default_transport, clock: Callable[[], datetime] = _now,
                           diagnostics: list | None = None) -> dict:
    """{series_id: capture} for evidence_lines.build. Reused series read the macro v0 / lights v1 files named in
    `manifest` (same private directory); a failed or missing source becomes {"reason": FIXED_CODE}, never 0."""
    root = Path(root)
    year = year if type(year) is int else clock().year
    captures = {}

    def fail(sids, reason, stage=None, error=None):
        for sid in sids:
            captures[sid] = {"reason": reason if reason in es.REASONS else "SOURCE_NOT_AVAILABLE"}
        if diagnostics is not None and stage:
            diagnostics.append({"stage": stage, "code": getattr(error, "code", None) if isinstance(error, MacroV0FetchError) else
                                ("PARSE_" + reason if reason in es.REASONS else "PARSE_OR_TRANSPORT_ERROR"),
                                "http": getattr(error, "status", None), "size": getattr(error, "size", None)})

    def capture(sid, rows, acquired, *, modified=None, release_date=None):
        captures[sid] = {"rows": rows, "acquired_at": acquired,
                         "release": {"at": es.http_time(modified), "date": release_date}}

    def fetch(stage, sids, url, *, data=None, query=None, form=False):
        try:
            body, headers = transport(url, data=data, query=query, form=form) if form else transport(url, data=data, query=query)
            return body, headers, clock().astimezone(timezone.utc)
        except Exception as error:
            fail(sids, "SOURCE_NOT_AVAILABLE", stage, error)
            return None

    # ---- reused files of the macro v0 / lights v1 collection
    def reused(entries, fmt):
        for entry in entries or ():
            if isinstance(entry, Mapping) and entry.get("format") == fmt and entry.get("file") and not entry.get("synthetic", True):
                path = root / entry["file"]
                if path.is_file() and not path.is_symlink():
                    return path.read_bytes(), datetime.fromisoformat(entry["acquired_at"]).astimezone(timezone.utc)
        return None

    bls = reused(manifest.get("macro_v0"), "BLS_API_V1_JSON")
    if bls is None:
        fail(("BLS:LNS14000000",), "SOURCE_NOT_COLLECTED")
    else:
        try:
            rows = es.parse_bls_v1(bls[0], ("CUUR0000SA0", "LNS14000000"))["BLS:LNS14000000"]
            capture("BLS:LNS14000000", rows, bls[1]) if isinstance(rows, dict) else fail(("BLS:LNS14000000",), rows)
        except es.SourceUnavailable as error:
            fail(("BLS:LNS14000000",), error.reason, "REUSED_BLS", error)
    bea = reused(manifest.get("macro_v0"), "BEA_NIPA_FLAT_Q")
    if bea is None:
        fail(("BEA:NIPA:A191RL:Q",), "SOURCE_NOT_COLLECTED")
    else:
        try:
            capture("BEA:NIPA:A191RL:Q", es.parse_bea_flat(bea[0], "A191RL", "Q"), bea[1])
        except es.SourceUnavailable as error:
            fail(("BEA:NIPA:A191RL:Q",), error.reason, "REUSED_BEA", error)
    curves = [(root / e["file"]).read_bytes() for e in manifest.get("macro_curve_v1") or ()
              if isinstance(e, Mapping) and e.get("file") and not e.get("synthetic", True)
              and (root / e["file"]).is_file() and not (root / e["file"]).is_symlink()]
    curve_times = [datetime.fromisoformat(e["acquired_at"]) for e in manifest.get("macro_curve_v1") or () if isinstance(e, Mapping) and e.get("file")]
    sid = "TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN"
    if not curves:
        fail((sid,), "SOURCE_NOT_COLLECTED")
    else:
        acquired = max(curve_times).astimezone(timezone.utc)
        try:
            capture(sid, es.treasury_monthly_spread(curves, before_month=acquired.strftime("%Y-%m")), acquired)
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "REUSED_CURVE", error)

    # ---- BLS v1: one batched request for the three evidence series
    bls_sids = tuple("BLS:" + s for s in es.BLS_EVIDENCE_IDS)
    payload = json.dumps({"seriesid": list(es.BLS_EVIDENCE_IDS), "startyear": str(year - 9), "endyear": str(year)},
                         separators=(",", ":")).encode()
    got = fetch("BLS_V1", bls_sids, ENDPOINTS["BLS"], data=payload)
    if got:
        try:
            for sid, rows in es.parse_bls_v1(got[0], es.BLS_EVIDENCE_IDS).items():
                capture(sid, rows, got[2]) if isinstance(rows, dict) else fail((sid,), rows)
        except es.SourceUnavailable as error:
            fail(bls_sids, error.reason, "BLS_V1", error)

    # ---- BEA monthly flat file (core PCE price index)
    sid = "BEA:NIPA:DPCCRG:M"
    got = fetch("BEA_FLAT_M", (sid,), BEA_FLAT_M_URL)
    if got:
        try:
            capture(sid, es.parse_bea_flat(got[0], "DPCCRG", "M"), got[2], modified=got[1].get("last-modified"))
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "BEA_FLAT_M", error)

    # ---- Fed DDP packages and their release dates
    for sid, package in es.DDP_PACKAGES.items():
        got = fetch("DDP_" + package["rel"], (sid,), FED_DDP_URL, query=ddp_query(package))
        if not got:
            continue
        released = None
        page = fetch("DDP_CHOOSE_" + package["rel"], (), DDP_CHOOSE_URL, query=urlencode((("rel", package["rel"]),)))
        if page:
            released = es.parse_ddp_release_date(page[0])
        try:
            capture(sid, es.parse_ddp_csv(got[0], package["column"]), got[2], release_date=released)
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "DDP_" + package["rel"], error)

    # ---- FOMC target range changes
    sid = "FED:FOMC:TARGET_RANGE"
    got = fetch("FOMC_OPENMARKET", (sid,), FOMC_URL)
    if got:
        try:
            capture(sid, {r["date"]: r["upper"] for r in es.parse_fomc_openmarket(got[0])}, got[2],
                    modified=got[1].get("last-modified"))
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "FOMC_OPENMARKET", error)

    # ---- DOL weekly claims (collected; publication held until the DOL terms are confirmed)
    sid = "DOL:ETA539:INITIAL_CLAIMS_SA"
    form = urlencode((("level", "us"), ("final_yr", str(year + 1)), ("strtdate", str(year - 5)), ("enddate", str(year)),
                      ("filetype", "xml"))).encode()
    got = fetch("DOL_ETA539", (sid,), DOL_URL, data=form, form=True)
    if got:
        try:
            capture(sid, es.parse_dol_weekly(got[0]), got[2])
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "DOL_ETA539", error)

    # ---- BTS TSI
    sid = "BTS:TSI:FREIGHT"
    got = fetch("BTS_TSI", (sid,), BTS_URL, query=urlencode((("$select", "obs_date,tsi_freight"), ("$order", "obs_date DESC"), ("$limit", "180"))))
    if got:
        try:
            capture(sid, es.parse_bts_tsi(got[0]), got[2], modified=got[1].get("last-modified"))
        except es.SourceUnavailable as error:
            fail((sid,), error.reason, "BTS_TSI", error)

    # ---- Census EITS (key required; never printed)
    key = environ.get(CENSUS_KEY_SLOT) if hasattr(environ, "get") else None
    key = key.strip() if isinstance(key, str) and key.strip() else None
    for sid, spec in es.CENSUS_QUERIES.items():
        if key is None:
            fail((sid,), "SOURCE_KEY_NOT_CONFIGURED")
            continue
        got = fetch("CENSUS_" + spec["program"].upper(), (sid,), CENSUS_URL + spec["program"], query=census_query(spec, year, key))
        if got:
            try:
                capture(sid, es.parse_census_eits(got[0], category=spec["category"], data_type=spec["data_type"]), got[2])
            except es.SourceUnavailable as error:
                fail((sid,), error.reason, "CENSUS_" + spec["program"].upper(), error)
    return captures
