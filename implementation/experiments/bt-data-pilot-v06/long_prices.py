"""Fixed-ten actual SIP raw daily collection; independent of V/PIT readiness.

Annual requests, preserved page tokens, bounded retries, per-symbol private
release checkpoints. Alias streams remain separate until identity is verified.
"""
import argparse
from datetime import date, datetime, timedelta, time, timezone
import json
import os
from pathlib import Path
import time as clock
from urllib.parse import urlencode
import zipfile

from github_alpaca_probe import RAW_REPO, NY, release, normalize
from pilot import private_dir, RawDatasetStore, acquire, digest, encoded, put_once

SYMBOLS = ("ABT", "ACU", "AE", "RWC", "BKTI", "AMD", "CECE", "CECO", "MATX", "ALX", "LNG", "IDSA")
START, END = "2016-01-01", "2026-10-30"


def dates(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return [(a + timedelta(days=i)).isoformat() for i in range((b-a).days+1)]


def gaps(start, end, observed):
    chunks, first, last = [], None, None
    for day in dates(start, end):
        if day in observed:
            if first:
                chunks.append((first, last)); first = None
        else:
            first = first or day
            last = day
    if first:
        chunks.append((first, last))
    return chunks


def safe_extract(path, target):
    if release.file_sha(path) != Path(str(path)+".sha256").read_text().split()[0]:
        raise ValueError("ARCHIVE_CHECKSUM")
    with zipfile.ZipFile(path) as z:
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in z.namelist()):
            raise ValueError("ARCHIVE_PATH")
        z.extractall(target)


def reuse(imports):
    series = {s: {} for s in SYMBOLS}
    provenance = []
    for archive in sorted(imports.glob("*/private-inputs.zip")):
        restored = archive.parent / "restored"
        safe_extract(archive, restored)
        store = RawDatasetStore(restored / "store")
        for path in (restored / "requests").glob("*.json"):
            receipt = json.loads(path.read_bytes())
            request, manifest = receipt.get("request", {}), receipt.get("receipt", {})
            symbol = request.get("symbol")
            if symbol not in series or request.get("feed") != "sip" or request.get("adjustment") != "raw" or not manifest.get("sha256"):
                continue
            body = store.get_bytes(manifest["artifact_id"])
            if digest(body) != manifest["sha256"]:
                raise ValueError("REUSED_SOURCE_SHA")
            for row in normalize(body, request):
                day = row["session_date"]
                if START <= day <= END:
                    if day in series[symbol] and series[symbol][day] != row:
                        raise ValueError("REUSED_OVERLAP_CONFLICT")
                    series[symbol][day] = row
            provenance.append({"archive": archive.parent.name, "request": request, "manifest": manifest})
    return series, provenance


def checkpoint(folder, tag, name):
    archive = folder.parent / (name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file(): z.write(path, path.relative_to(folder))
    sha = release.file_sha(archive)
    release.upload(RAW_REPO, tag, archive, name+".zip", sha)
    release.download(RAW_REPO, tag, name+".zip", folder.parent/(name+"-roundtrip.zip"), sha)


def collect(output, imports, resume=None):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("RUNNER_REQUIRED")
    configured = {k: bool(os.environ.get(k)) for k in ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "RAW_REPO_TOKEN")}
    if not all(configured.values()):
        return {"status": "SECRET_BINDING_MISSING", "configured": configured}
    code, _, response = release.http("GET", f"{release.API}/repos/{RAW_REPO}")
    if code != 200 or json.loads(response).get("private") is not True:
        raise ValueError("PRIVATE_DESTINATION_REQUIRED")
    root = private_dir(output)
    info = root / "summary"; info.mkdir(exist_ok=True)
    prior, sources = reuse(imports)
    put_once(info/"reused-sources.json", encoded(sources))
    headers = {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"], "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]}
    calendar_store = RawDatasetStore(info/"calendar")
    calendar, calendar_status = [], []
    # Only the read-only calendar endpoint, never orders, positions, or accounts.
    for host in ("https://paper-api.alpaca.markets", "https://api.alpaca.markets"):
        body, receipt = acquire(calendar_store, "calendar:"+host.split('//')[1], host+"/v2/calendar?"+urlencode({"start": START, "end": END}), "ALPACA_CALENDAR_JSON", headers)
        calendar_status.append({"host": host, "http_status": receipt.get("http_status")})
        if body:
            data = json.loads(body)
            if isinstance(data, list) and data and all("date" in r and "open" in r and "close" in r for r in data):
                calendar = data; break
    (info/"calendar-status.json").write_bytes(encoded(calendar_status))
    expected = {r["date"] for r in calendar}
    tag = "bt-data-pilot-v06-long-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    summary, calls = [], 0
    for symbol in SYMBOLS:
        folder = root / symbol; folder.mkdir(exist_ok=True)
        if resume and (resume/(symbol+".zip")).exists():
            safe_extract(resume/(symbol+".zip"), folder)
        store = RawDatasetStore(folder/"store")
        (folder/"requests").mkdir(exist_ok=True)
        state_path = folder/"checkpoint.json"
        state = json.loads(state_path.read_bytes()) if state_path.exists() else {"completed_intervals": [], "results": []}
        rows = dict(prior[symbol])
        if (folder/"normalized.json").exists():
            for row in json.loads((folder/"normalized.json").read_bytes()):
                rows[row["session_date"]] = row
        initial = len(rows)
        stopped = False
        for year in range(2016, 2027):
            first, last = f"{year}-01-01", min(f"{year}-12-31", END)
            # Prior actual bars split windows; no five-day re-download.
            for a, b in gaps(first, last, {d for d in prior[symbol] if a_year(d)==year}):
                key = a+":"+b
                if key in state["completed_intervals"]:
                    continue
                token, seen, page, finished = None, set(), 0, False
                while page < 10 and calls < 400:
                    params = dict(timeframe="1Day", start=datetime.combine(date.fromisoformat(a),time.min,NY).isoformat(),
                        end=datetime.combine(date.fromisoformat(b),time.max,NY).isoformat(), feed="sip", adjustment="raw", asof="-", sort="asc", limit=1000)
                    if token: params["page_token"] = token
                    aid = f"sip:{symbol}:{a}:{b}:{page}"
                    body = None
                    for attempt in range(3):
                        attempt_id = aid+":"+str(attempt)
                        cached = store.has(attempt_id)
                        if not cached: clock.sleep(0.55 if attempt==0 else 5*attempt)
                        body, receipt = acquire(store, attempt_id, "https://data.alpaca.markets/v2/stocks/"+symbol+"/bars?"+urlencode(params), "ALPACA_STOCK_BARS_JSON", headers)
                        calls += not cached
                        (folder/"requests"/(attempt_id.replace(":","_")+".json")).write_bytes(encoded({"arguments":params,"receipt":receipt}))
                        if body is not None or receipt.get("http_status") not in (500,502,503,504): break
                    if body is None:
                        state["results"].append({"start":a,"end":b,"status":"REQUEST_FAILED","http_status":receipt.get("http_status"),"page":page})
                        stopped = receipt.get("http_status") in (401,403,429)
                        break
                    data = json.loads(body)
                    next_token = data.get("next_page_token")
                    page_data = dict(data, next_page_token=None)
                    request = {"symbol":symbol,"feed":"sip","adjustment":"raw","days":dates(a,b)}
                    parsed = normalize(encoded(page_data), request)
                    for row in parsed:
                        day = row["session_date"]
                        if day in rows and rows[day]["raw"] != row["raw"]:
                            raise ValueError("CONFLICTING_OVERLAP")
                        rows[day] = row
                    state["results"].append({"start":a,"end":b,"page":page,"rows":len(parsed),"status":"PAGE_OK","has_next":bool(next_token)})
                    page += 1
                    if not next_token:
                        finished = True; break
                    if next_token in seen or not parsed:
                        state["results"].append({"start":a,"end":b,"status":"PAGINATION_NO_PROGRESS"}); break
                    seen.add(next_token); token = next_token
                if finished: state["completed_intervals"].append(key)
                state_path.write_bytes(encoded(state))
                (folder/"normalized.json").write_bytes(encoded([rows[d] for d in sorted(rows)]))
                if stopped: break
            if stopped: break
        actual = set(rows)
        record = {"symbol":symbol,"request_start":START,"request_end":END,"first":min(actual,default=None),"last":max(actual,default=None),
                  "rows":len(rows),"reused_rows":initial,"expected_market_sessions":len(expected) if expected else None,
                  "missing_dates":sorted(expected-actual) if expected else None,"unexpected_dates":sorted(actual-expected) if expected else None,
                  "pagination_complete":all(a+":"+b in state["completed_intervals"]
                      for y in range(2016,2027) for a,b in gaps(f"{y}-01-01",min(f"{y}-12-31",END),
                          {d for d in prior[symbol] if a_year(d)==y})) and not stopped,
                  "ohlcv_missing_cells":sum(v is None for r in rows.values() for v in r["raw"].values()),
                  "security_identity_verified":False,"continuous_issuer_series_verified":False}
        (folder/"aggregate.json").write_bytes(encoded(record)); summary.append(record)
        checkpoint(folder, tag, symbol)  # durable checkpoint after every symbol
        print(json.dumps({"checkpoint":symbol,"rows":record["rows"],"first":record["first"],"last":record["last"],"complete":record["pagination_complete"]}),flush=True)
        if stopped: break
    report = {"version":"BT-DATA-PILOT v0.6","private_release_tag":tag,"stock_requests":calls,"symbols":summary,
              "calendar_status":calendar_status,"formal_backtests":0,"v_prerequisite":False}
    (info/"aggregate.json").write_bytes(encoded(report)); checkpoint(info,tag,"summary")
    return {"status":"PRIVATE_CHECKPOINTS_VERIFIED","private_release_tag":tag,"stock_requests":calls,"symbols":len(summary),"formal_backtests":0}


def a_year(day): return int(day[:4])


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir",type=Path,required=True);p.add_argument("--imports",type=Path,required=True);p.add_argument("--resume",type=Path)
    args=p.parse_args()
    try: print(json.dumps(collect(args.private_dir,args.imports,args.resume)))
    except (OSError,ValueError,KeyError,TypeError,release.ReleaseError):
        print('{"status":"COLLECTION_STOPPED_CHECK_PRIVATE_CHECKPOINTS"}');raise SystemExit(2) from None
