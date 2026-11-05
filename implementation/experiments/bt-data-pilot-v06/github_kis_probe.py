"""Owner-requested KIS/Alpaca private quote probe, BT-DATA-PILOT v0.6.

Official KIS sample pinned at 3a9be59a3ed8745720dc3aa9d584bdf3b7830362.
Only tokenP and dailyprice are allowed. No account or trading endpoints.
Reuse the existing raw store, OHLCV validator and private release transport.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener
import zipfile

from github_alpaca_probe import (RAW_REPO, PRIMARY_DAYS, EVENT_DAYS, normalize as alpaca_normalize,
                                summary_for, release)
from pilot import private_dir, encoded, digest, put_once, normalize_tiingo, acquire, RawDatasetStore

BASE = "https://openapi.koreainvestment.com:9443"
ENDPOINT = "/uapi/overseas-price/v1/quotations/dailyprice"
RECENT = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
# KIS current master supplies query routing only, NOT historical membership.
# Ended AE/IDSA are retained; their old exchange is a query candidate only.
FIXED = [(1800, "ABT", "NYS", "ABT"), (2098, "ACU", "AMS", "ACU"),
         (2178, "AE", "AMS", "AE"), (2186, "BKTI", "AMS", "RWC"),
         (2488, "AMD", "NAS", "AMD"), (3197, "CECO", "AMS", "CECE"),
         (3453, "MATX", "NYS", "MATX"), (3499, "ALX", "NYS", "ALX"),
         (3570, "LNG", "NYS", "LNG"), (4187, "IDSA", "NAS", "IDSA")]
FIELDS = ("open", "high", "low", "close", "volume")
KEY_PAIRS = (("KIS_APP_KEY", "KIS_APP_SECRET"), ("KIS_APPKEY", "KIS_APPSECRET"))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credential headers to another destination.


def transport(url, headers, payload=None):
    """Return bytes privately; never print exceptions, headers or token responses."""
    started = time.monotonic()
    req = Request(url, headers=headers, data=payload)
    try:
        with build_opener(NoRedirect).open(req, timeout=25) as response:
            body = response.read(12 * 1024 * 1024 + 1)
            if len(body) > 12 * 1024 * 1024:
                raise ValueError("RESPONSE_TOO_LARGE")
            return response.status, body, response.headers.get("tr_cont", ""), time.monotonic() - started
    except HTTPError as error:
        return error.code, error.read(65536), "", time.monotonic() - started
    except (URLError, TimeoutError, OSError):
        return None, b"", "", time.monotonic() - started


def choose_keys(env):
    found = [(env[a], env[b]) for a, b in KEY_PAIRS if env.get(a) and env.get(b)]
    if len(set(found)) > 1:
        return None, "AMBIGUOUS_SECRET_BINDINGS"
    return (found[0], "CONFIGURED") if found else (None, "SECRET_BINDING_MISSING")


def kis_normalize(body, symbol, modp, bymd):
    data = json.loads(body)
    if data.get("rt_cd") != "0" or not isinstance(data.get("output2"), list):
        raise ValueError("KIS_RESPONSE_SCHEMA")
    mapped, original = [], {}
    for row in data["output2"]:
        day = datetime.strptime(row["xymd"], "%Y%m%d").date().isoformat()
        if day.replace("-", "") > bymd:
            raise ValueError("AFTER_QUERY_DATE")
        values = {}
        for target, source in zip(FIELDS, ("open", "high", "low", "clos", "tvol")):
            value = row.get(source)
            values[target] = None if value in (None, "") else float(value)
        mapped.append({"date": day, **values})
        original[day] = row
    rows = normalize_tiingo(encoded(mapped), symbol, "USD")
    for row in rows:
        row.update(provider="KIS", provider_payload=original[row["session_date"]],
                   currency_evidence="US_EXCHANGE_QUERY_SCOPE_NOT_RESPONSE_FIELD",
                   timezone="America/New_York", timezone_evidence="US_MARKET_INFERENCE",
                   session_scope="PROVIDER_UNCONFIRMED", publication_at=None,
                   v_input_ready=False, historical_security_identity_verified=False,
                   execution_open_verified=False, corporate_actions_verified=False)
        if modp == "1":
            observed = row["raw"]
            row.update(price_basis="KIS_MODP1_ADJUSTED_METHOD_UNCONFIRMED", observed=observed,
                       raw={k: None for k in FIELDS},
                       adjusted={"adj" + k.title(): v for k, v in observed.items()})
    return rows


def kis_partition(body,symbol,modp,bymd):
    """Keep original response; quarantine bad bars through the existing validator.

    Date scope and duplicate dates remain page-wide fail-closed boundaries.
    No prices are corrected, imputed, or taken from an adjacent day.
    """
    obj=json.loads(body)
    if obj.get('rt_cd')!='0' or not isinstance(obj.get('output2'),list):raise ValueError('KIS_RESPONSE_SCHEMA')
    days=[]
    for row in obj['output2']:
        day=datetime.strptime(row['xymd'],'%Y%m%d').date().isoformat()
        if day.replace('-','')>bymd:raise ValueError('AFTER_QUERY_DATE')
        if day in days:raise ValueError('DUPLICATE_DATE')
        days.append(day)
    rows=[];rejected=[]
    for index,(day,row)in enumerate(zip(days,obj['output2'])):
        try:rows.extend(kis_normalize(encoded({'rt_cd':'0','output2':[row]}),symbol,modp,bymd))
        except (ValueError,KeyError,TypeError)as error:
            rejected.append({'row_index':index,'date':day,'reason':str(error),'status':'BLOCKED_ROW_QUALITY'})
    return rows,rejected


def progress(previous, rows):
    dates = {r["session_date"] for r in rows}
    if not dates:
        return "EMPTY_PAGE"
    if previous and not dates - previous:
        return "REPEATED_PAGE"
    if previous and min(dates) >= min(previous):
        return "NO_BACKWARD_PROGRESS"
    return "PROGRESS"


class KIS:
    def __init__(self, root, store, keys, max_calls=60):
        self.root, self.store, self.keys = root, store, keys
        self.headers = None
        self.calls = 0
        self.stopped = False
        self.request_label = ""
        self.pause_seconds = 1.1
        if type(max_calls) is not int or not 1 <= max_calls <= 240:
            raise ValueError("INVALID_LOCAL_REQUEST_BUDGET")
        self.max_calls = max_calls

    def authenticate(self):
        code, body, _, elapsed = transport(BASE + "/oauth2/tokenP", {"Content-Type": "application/json"},
            encoded({"grant_type": "client_credentials", "appkey": self.keys[0], "appsecret": self.keys[1]}))
        try:
            token = json.loads(body).get("access_token") if code == 200 else None
        except (ValueError, AttributeError):
            token = None
        # Auth response is NEVER stored; tokens only live in process memory.
        if token:
            self.headers = {"authorization": "Bearer " + token, "appkey": self.keys[0],
                            "appsecret": self.keys[1], "tr_id": "HHDFS76240000", "custtype": "P",
                            "Content-Type": "application/json", "Accept": "text/plain", "charset": "UTF-8",
                            "User-Agent": "Investment-System1 BT-DATA-PILOT personal research"}
        return {"status": "AUTHENTICATED" if token else "AUTHENTICATION_FAILED" if code else "NETWORK_REQUEST_FAILED",
                "http_status": code, "elapsed_seconds": round(elapsed, 3), "requests": 1}

    def page(self, symbol, exchange, bymd, modp, continuation="", *, attempt=0):
        params = dict(AUTH="", EXCD=exchange, SYMB=symbol, GUBN="0", BYMD=bymd, MODP=modp)
        aid = "kis:" + ":".join((symbol, exchange, bymd, modp, continuation or "first"))
        if self.request_label:
            aid += ":" + self.request_label
        if not isinstance(attempt,int) or not 0<=attempt<=2:
            raise ValueError("RETRY_ATTEMPT_LIMIT")
        if attempt:
            aid += ":retry"+str(attempt)
        url = BASE + ENDPOINT + "?" + urlencode(params)
        receipt_path = self.root / "requests" / (aid.replace(":", "_") + ".json")
        if self.store.has(aid):
            body = self.store.get_bytes(aid)
            receipt = self.store.get_manifest(aid)
            if digest(body) != receipt["sha256"]:
                raise ValueError("CACHE_CHECKSUM")
            meta = json.loads(receipt_path.read_bytes())
            return body, meta
        if self.stopped or self.calls >= self.max_calls:
            return None, {"status": "PROVIDER_STOPPED_OR_LOCAL_REQUEST_BUDGET"}
        time.sleep(self.pause_seconds)
        self.calls += 1
        code, body, cont, elapsed = transport(url, {**self.headers, "tr_cont": continuation})
        meta = {"request": params, "request_tr_cont": continuation, "response_tr_cont": cont,
                "http_status": code, "elapsed_seconds": round(elapsed, 3),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "provider_published_at": None, "assumed_available_at": None}
        if code in (401, 403, 429):
            self.stopped = True  # no token retry or rate-limit hammering
        # Quote responses may contain unexpected credential echoes: refuse persistence.
        sensitive = (*self.keys, self.headers["authorization"].removeprefix("Bearer "))
        if body and any(s.encode() in body for s in sensitive):
            meta["status"] = "SENSITIVE_RESPONSE_WITHHELD"
            body = b""
        if body:
            meta["receipt"] = self.store.put(aid, body, url, "KIS_DAILYPRICE_JSON",
                "application/json", "BT-DATA-PILOT v0.6", code).to_dict()
        put_once(receipt_path, encoded(meta))
        return body or None, meta

    def window(self, cik, symbol, exchange, days, modp, cohort, pages=1):
        bymd, cont, dates, selected = days[-1].replace("-", ""), "", set(), {}
        result = {"provider": "KIS", "cik": cik, "symbol": symbol, "exchange": exchange,
                  "cohort": cohort, "adjustment": "raw" if modp == "0" else "kis_modp1",
                  "status": "NOT_REQUESTED", "pages": [], "duplicate_across_pages": 0}
        for _ in range(pages):
            body, meta = self.page(symbol, exchange, bymd, modp, cont)
            page_result = {k: meta.get(k) for k in ("http_status", "elapsed_seconds", "response_tr_cont")}
            result["pages"].append(page_result)
            if body is None:
                result["status"] = meta.get("status", "NETWORK_REQUEST_FAILED")
                break
            try:
                data = json.loads(body)
                if data.get("rt_cd") != "0":
                    msg = str(data.get("msg_cd", ""))
                    result["provider_code"] = msg if re.fullmatch(r"[A-Z0-9_-]{0,30}", msg) else "WITHHELD"
                    result["status"] = "API_REJECTED"
                    if msg == "EGW00201" or (msg == "OPSQ1002" and self.request_label):
                        self.stopped = True
                    break
                rows = kis_normalize(body, symbol, modp, bymd)
                key = digest(encoded({"raw": digest(body), "params": meta["request"]}))
                put_once(self.root / "normalized" / (key + ".json"), encoded(rows))
                state = progress(dates, rows)
                page_result.update(rows=len(rows), progress=state)
                result["duplicate_across_pages"] += sum(r["session_date"] in dates for r in rows)
                if state != "PROGRESS":
                    result["pagination_stop"] = state
                    result["status"] = "ACQUIRED" if selected else "REQUESTED_DATA_ABSENT"
                    break
                dates.update(r["session_date"] for r in rows)
                selected.update({r["session_date"]: r for r in rows if r["session_date"] in days})
                result["status"] = "ACQUIRED" if selected else "REQUESTED_DATA_ABSENT"
                # Test official continuation when indicated; otherwise move explicit BYMD backward.
                if meta["response_tr_cont"] in ("M", "F") and not cont:
                    cont = "N"
                else:
                    bymd = (date.fromisoformat(min(dates)) - timedelta(days=1)).strftime("%Y%m%d")
                    cont = ""
            except (ValueError, KeyError, TypeError):
                result["status"] = "RESPONSE_QUALITY_FAILED"
                break
        values = [r["raw"] if modp == "0" else r["observed"] for r in selected.values()]
        result.update(rows=len(selected), expected_sessions=len(days), missing_dates=sorted(set(days)-selected.keys()),
                      missing_fields={k: sum(v[k] is None for v in values) for k in FIELDS},
                      date_min=min(selected, default=None), date_max=max(selected, default=None),
                      all_page_date_min=min(dates, default=None), all_page_date_max=max(dates, default=None),
                      all_page_unique_rows=len(dates), ledger_ready=False, v_input_ready=False)
        result["missing_day_rate"] = len(result["missing_dates"]) / len(days)
        result["complete_ohlcv"] = (result["status"] == "ACQUIRED" and len(selected) == len(days)
                                     and not any(result["missing_fields"].values()))
        return result


def alpaca_window(root, store, symbol, days, cohort):
    request = dict(symbol=symbol, feed="sip", adjustment="raw", days=days, cohort=cohort)
    params = dict(timeframe="1Day", start=days[0]+"T00:00:00-04:00", end=days[-1]+"T23:59:59-04:00",
                  feed="sip", adjustment="raw", asof="-", sort="asc", limit=1000)
    aid = "alpaca_kis_compare:" + symbol + ":" + days[0]
    url = "https://data.alpaca.markets/v2/stocks/" + symbol + "/bars?" + urlencode(params)
    body, receipt = acquire(store, aid, url, "ALPACA_STOCK_BARS_JSON",
        {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]})
    put_once(root / "requests" / (aid.replace(":", "_")+".json"), encoded({"request": request, "arguments": params, "receipt": receipt}))
    if body is None:
        return {"provider": "ALPACA", "symbol": symbol, "cohort": cohort,
                "status": "HTTP_REQUEST_FAILED" if receipt.get("http_status") else "NETWORK_REQUEST_FAILED",
                "http_status": receipt.get("http_status")}
    try:
        rows = alpaca_normalize(body, request)
        put_once(root / "normalized" / (digest(encoded({"raw": digest(body), "request": request}))+".json"), encoded(rows))
        return {"provider": "ALPACA", "status": "ACQUIRED" if rows else "REQUESTED_DATA_ABSENT",
                "http_status": receipt.get("http_status"), **summary_for(rows, request)}
    except (ValueError, KeyError, TypeError):
        return {"provider": "ALPACA", "symbol": symbol, "cohort": cohort, "status": "RESPONSE_QUALITY_FAILED"}


def run(output, kis_only=False, resume_zip=None):
    names = [x for pair in KEY_PAIRS for x in pair] + ["APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "RAW_REPO_TOKEN"]
    configured = {name: bool(os.environ.get(name)) for name in names}
    report = {"version": "BT-DATA-PILOT v0.6", "configured": configured, "results": [],
              "formal_backtests": 0, "ledger_runs": 0, "v_factor_slots_complete": 0}
    if os.environ.get("GITHUB_ACTIONS") != "true" or not configured["RAW_REPO_TOKEN"]:
        return {**report, "status": "RUNNER_OR_PRIVATE_STORAGE_BINDING_MISSING"}
    status, _, body = release.http("GET", f"{release.API}/repos/{RAW_REPO}")
    if status != 200 or json.loads(body).get("private") is not True:
        return {**report, "status": "PRIVATE_STORAGE_PREFLIGHT_FAILED"}
    root = private_dir(output)
    prior = None
    if resume_zip:
        expected = Path(str(resume_zip) + ".sha256").read_text().split()[0]
        if release.file_sha(resume_zip) != expected:
            raise ValueError("RESUME_ARCHIVE_SHA")
        with zipfile.ZipFile(resume_zip) as zipped:
            if any(Path(n).is_absolute() or ".." in Path(n).parts for n in zipped.namelist()):
                raise ValueError("RESUME_PATH")
            zipped.extractall(root)
        prior = json.loads((root / "aggregate.json").read_bytes())
        (root / "aggregate.json").rename(root / "prior-aggregate.json")
        report["resumed_private_archive"] = "bt-data-pilot-v06-kis-41167695581-1"
    for child in ("requests", "normalized"):
        (root / child).mkdir(exist_ok=True, mode=0o700)
    store = RawDatasetStore(root / "store")
    for aid in store.list_ids():
        if digest(store.get_bytes(aid)) != store.get_manifest(aid)["sha256"]:
            raise ValueError("RESUME_BLOB_SHA")
    keys, state = choose_keys(os.environ)
    report["kis_auth"] = {"status": state, "requests": 0}
    if keys:
        client = KIS(root, store, keys)
        report["kis_auth"] = client.authenticate()
        if client.headers and prior:
            client.request_label = "cooldown_retry"
            client.pause_seconds = 10
            # Retry only actually failed requests once, not successful or empty responses.
            failed = [r for r in prior["results"] if r["status"] == "API_REJECTED"]
            for old in failed[:14]:
                days = RECENT if old["cohort"] == "FIXED10_RECENT" else PRIMARY_DAYS
                report["results"].append(client.window(old["cik"], old["symbol"], old["exchange"], days,
                    "0" if old["adjustment"] == "raw" else "1", old["cohort"]))
                if client.stopped:
                    break
            if not client.stopped:
                report["results"].append(client.window(1800, "ABT", "NYS", ["2026-06-01", "2026-06-02"],
                    "0", "EXPLICIT_BYMD_PROGRESS"))
        elif client.headers:
            first = client.window(1800, "ABT", "NYS", RECENT, "0", "FIXED10_RECENT", pages=3)
            report["results"].append(first)
            if first["complete_ohlcv"]:
                for cik, symbol, exchange, historical in FIXED:
                    if symbol != "ABT":
                        report["results"].append(client.window(cik, symbol, exchange, RECENT, "0", "FIXED10_RECENT"))
                    report["results"].append(client.window(cik, symbol, exchange, RECENT, "1", "FIXED10_RECENT"))
                    # Historical routing is a candidate and stays unverified until identity audit.
                    old_exchange = "NAS" if historical == "CECE" else "AMS" if symbol == "LNG" else exchange
                    report["results"].append(client.window(cik, historical, old_exchange, PRIMARY_DAYS, "0", "FIXED10_2016"))
                    report["results"].append(client.window(cik, historical, old_exchange, PRIMARY_DAYS, "1", "FIXED10_2016"))
                for modp in ("0", "1"):
                    report["results"].append(client.window(1045810, "NVDA", "NAS", EVENT_DAYS, modp, "NVDA_SPLIT_2024"))
        report["kis_market_requests"] = client.calls
    # Alpaca is independent of KIS secret/authentication/data failures.
    if kis_only:
        report["alpaca_status"] = "REUSE_PREVIOUS_PRIVATE_ARCHIVE_NO_NEW_REQUESTS"
    elif configured["APCA_API_KEY_ID"] and configured["APCA_API_SECRET_KEY"]:
        for _, symbol, _, historical in FIXED:
            for days, ticker, cohort in ((RECENT, symbol, "FIXED10_RECENT"), (PRIMARY_DAYS, historical, "FIXED10_2016")):
                # Existing verified ABT 2016 SIP archive will be reused offline.
                if ticker == "ABT" and days == PRIMARY_DAYS:
                    continue
                result = alpaca_window(root, store, ticker, days, cohort)
                report["results"].append(result)
                if result.get("http_status") in (401, 403, 429):
                    break
                time.sleep(0.5)
            if result.get("http_status") in (401, 403, 429):
                break
    else:
        report["alpaca_status"] = "SECRET_BINDING_MISSING"
    (root / "aggregate.json").write_bytes(encoded(report))
    archive = root.parent / (root.name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(root))
    tag = "bt-data-pilot-v06-kis-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    sha = release.file_sha(archive)
    release.upload(RAW_REPO, tag, archive, "private-inputs.zip", sha)
    release.download(RAW_REPO, tag, "private-inputs.zip", root.parent / (root.name + "-roundtrip.zip"), sha)
    report.update(status="PRIVATE_ARCHIVE_ROUNDTRIP_VERIFIED", private_release_tag=tag)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--kis-only", action="store_true", help="Reuse already acquired Alpaca prices offline")
    parser.add_argument("--resume-zip", type=Path, help="Verified previous private archive; retry only failed KIS requests")
    args = parser.parse_args()
    try:
        result = run(args.private_dir, args.kis_only, args.resume_zip)
        print(json.dumps(result, sort_keys=True))  # aggregate only, no price/body/token/hash
        if result["status"] != "PRIVATE_ARCHIVE_ROUNDTRIP_VERIFIED":
            raise SystemExit(2)
    except (release.ReleaseError, OSError, ValueError, KeyError, TypeError):
        print('{"status":"PROBE_OR_PRIVATE_ARCHIVE_FAILED","formal_backtests":0}')
        raise SystemExit(2) from None
