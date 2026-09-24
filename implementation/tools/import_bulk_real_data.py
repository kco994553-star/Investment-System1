"""Import bulk SEC Company Facts and Stooq US daily archives into RawDatasetStore.

This is an offline companion to fetch_real_data.py for environments where large
bulk archives are easier to obtain than thousands of HTTP requests. It does not
change PIT ranking logic; it only converts source bytes into the artifact IDs
already consumed by ingestion/replay.py.

Accepted inputs:
  --sec-companyfacts companyfacts.zip
      Official SEC nightly bulk archive. Members named CIK##########.json are
      stored verbatim as companyfacts:<CIK10>.
  --stooq-us d_us_txt.zip
      Stooq US daily ASCII archive. Each *.txt member is converted to the
      existing Yahoo-chart-compatible JSON envelope and stored as
      yahoo_chart:<SYMBOL>:<chart-range>. This lets the existing replay/parser
      path run unchanged. Source/provenance remains STOOQ_BULK, never Yahoo.

No network access is performed by this tool.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402

FETCHER = "tools/import_bulk_real_data.py v1"
SEC_SOURCE = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"
STOOQ_SOURCE = "https://static.stooq.com/db/h/d_us_txt.zip"
CIK_RE = re.compile(r"(?:^|/)CIK(\d{10})\.json$", re.I)


def import_sec(store: RawDatasetStore, path: Path, refresh: bool) -> dict:
    ok = skipped = bad = 0
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            m = CIK_RE.search(info.filename)
            if not m:
                continue
            aid = f"companyfacts:{m.group(1)}"
            if store.has(aid) and not refresh:
                skipped += 1
                continue
            body = zf.read(info)
            try:
                json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                bad += 1
                continue
            store.put(aid, body, SEC_SOURCE, "SEC_COMPANYFACTS_BULK", "application/json", FETCHER, 200,
                      notes=f"bulk member={info.filename}")
            ok += 1
    return {"source": "SEC_COMPANYFACTS_BULK", "imported": ok, "skipped": skipped, "bad": bad}


def _symbol_from_stooq_member(name: str) -> str | None:
    base = Path(name).name.lower()
    if not base.endswith(".us.txt"):
        return None
    sym = base[:-7].upper()  # remove .us.txt
    # Stooq class tickers commonly use '-' where Yahoo uses '-'; keep source symbol literal.
    return sym or None


def _stooq_to_chart(body: bytes, symbol: str) -> bytes | None:
    text = body.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    timestamps, closes = [], []
    for row in reader:
        ds = row.get("Date") or row.get("<DATE>")
        cs = row.get("Close") or row.get("<CLOSE>")
        if not ds or not cs:
            continue
        try:
            dt = datetime.strptime(ds.strip(), "%Y%m%d" if "-" not in ds else "%Y-%m-%d").replace(tzinfo=timezone.utc)
            px = float(cs)
        except (ValueError, TypeError):
            continue
        if px <= 0:
            continue
        timestamps.append(int(dt.timestamp()))
        closes.append(px)
    if not timestamps:
        return None
    payload = {"chart": {"result": [{
        "meta": {"symbol": symbol, "currency": "USD"},
        "timestamp": timestamps,
        "indicators": {"quote": [{"close": closes}]},
    }], "error": None}}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def import_stooq(store: RawDatasetStore, path: Path, chart_range: str, refresh: bool) -> dict:
    ok = skipped = bad = 0
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            sym = _symbol_from_stooq_member(info.filename)
            if sym is None:
                continue
            aid = f"yahoo_chart:{sym}:{chart_range}"
            if store.has(aid) and not refresh:
                skipped += 1
                continue
            converted = _stooq_to_chart(zf.read(info), sym)
            if converted is None:
                bad += 1
                continue
            store.put(aid, converted, STOOQ_SOURCE, "STOOQ_US_DAILY_BULK", "application/json", FETCHER, 200,
                      notes=f"converted to replay-compatible chart envelope; bulk member={info.filename}; unadjusted close")
            ok += 1
    return {"source": "STOOQ_US_DAILY_BULK", "imported": ok, "skipped": skipped, "bad": bad}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--sec-companyfacts", type=Path)
    ap.add_argument("--stooq-us", type=Path)
    ap.add_argument("--chart-range", default="max")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if not a.sec_companyfacts and not a.stooq_us:
        ap.error("provide --sec-companyfacts and/or --stooq-us")
    store = RawDatasetStore(a.store)
    results = []
    if a.sec_companyfacts:
        results.append(import_sec(store, a.sec_companyfacts, a.refresh))
    if a.stooq_us:
        results.append(import_stooq(store, a.stooq_us, a.chart_range, a.refresh))
    report = {"kind": "BULK_REAL_DATA_IMPORT", "results": results, "real_data_verified": False,
              "note": "bulk ingestion only; PIT completeness and downstream verification remain separate gates"}
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
