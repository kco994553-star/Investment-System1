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

2026-09-25 (Claude Code r6) additive, fail-closed:
  * every archive is integrity-verified BEFORE any store write (size, sha256,
    PK signature, zipfile open = EOCD/central directory present, full testzip()
    CRC pass, member count). A truncated or corrupt archive (see
    reports/gate_evidence/sec_bulk_integrity_2026-09-25_gpt_r5.json) is rejected
    and nothing is imported. --verify-only runs the check alone.
  * the verification (incl. archive sha256) is stored in the import report and
    each artifact's manifest notes; STORE_INDEX.json is rewritten after import.
  * the chart range must match what the gate chain reads (default 5y there);
    pass --chart-range 5y unless the chain is run with --chart-range max.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
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


def verify_archive(path: Path, member_re: "re.Pattern[str]", expected_sha256: str | None = None) -> dict:
    """Fail-closed ZIP integrity check. Reads the whole file (sha256) and CRC-tests every member."""
    rep: dict = {"path": str(path), "exists": path.exists(), "passed": False, "reasons": []}
    if not path.exists():
        rep["reasons"].append("ARCHIVE_NOT_FOUND")
        return rep
    h = hashlib.sha256()
    with path.open("rb") as f:
        head = f.read(4)
        h.update(head)
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    rep.update({"bytes": path.stat().st_size, "sha256": h.hexdigest(), "first_signature": head.hex()})
    if head != b"PK\x03\x04":
        rep["reasons"].append("NOT_A_ZIP_LOCAL_HEADER")
    if expected_sha256 and expected_sha256.lower() != rep["sha256"]:
        rep["reasons"].append("SHA256_MISMATCH")
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            rep["n_members"] = len(infos)
            rep["n_matching_members"] = sum(1 for i in infos if member_re.search(i.filename))
            bad = zf.testzip()
            rep["first_bad_member"] = bad
            if bad is not None:
                rep["reasons"].append("MEMBER_CRC_FAILED")
            if rep["n_matching_members"] == 0:
                rep["reasons"].append("NO_EXPECTED_MEMBERS")
    except (zipfile.BadZipFile, OSError, EOFError) as e:
        rep["reasons"].append("ZIP_UNREADABLE_NO_CENTRAL_DIRECTORY_OR_TRUNCATED")
        rep["error"] = f"{type(e).__name__}: {e}"
    rep["passed"] = not rep["reasons"]
    return rep


STOOQ_MEMBER_RE = re.compile(r"\.us\.txt$", re.I)


def import_sec(store: RawDatasetStore, path: Path, refresh: bool, archive_sha256: str = "") -> dict:
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
                      notes=f"bulk member={info.filename}" + (f"; archive_sha256={archive_sha256}" if archive_sha256 else ""))
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
            # Stamp the daily bar after the US close (21:00 UTC): a date-only 00:00 stamp would make
            # day D's close look available at the start of D (look-ahead under an as_of filter).
            dt = datetime.strptime(ds.strip(), "%Y%m%d" if "-" not in ds else "%Y-%m-%d").replace(hour=21, tzinfo=timezone.utc)
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


def import_stooq(store: RawDatasetStore, path: Path, chart_range: str, refresh: bool, archive_sha256: str = "") -> dict:
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
                      notes=f"converted to replay-compatible chart envelope; bulk member={info.filename}; unadjusted close" + (f"; archive_sha256={archive_sha256}" if archive_sha256 else ""))
            ok += 1
    return {"source": "STOOQ_US_DAILY_BULK", "imported": ok, "skipped": skipped, "bad": bad}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--sec-companyfacts", type=Path)
    ap.add_argument("--stooq-us", type=Path)
    ap.add_argument("--chart-range", default="max")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--verify-only", action="store_true", help="integrity-check the archives and exit; no store writes")
    ap.add_argument("--sec-sha256", help="expected sha256 of --sec-companyfacts (optional)")
    ap.add_argument("--stooq-sha256", help="expected sha256 of --stooq-us (optional)")
    ap.add_argument("--report-out", type=Path)
    a = ap.parse_args()
    if not a.sec_companyfacts and not a.stooq_us:
        ap.error("provide --sec-companyfacts and/or --stooq-us")
    verification = []
    if a.sec_companyfacts:
        verification.append({"source": "SEC_COMPANYFACTS_BULK", **verify_archive(a.sec_companyfacts, CIK_RE, a.sec_sha256)})
    if a.stooq_us:
        verification.append({"source": "STOOQ_US_DAILY_BULK", **verify_archive(a.stooq_us, STOOQ_MEMBER_RE, a.stooq_sha256)})
    ok = all(v["passed"] for v in verification)
    if a.verify_only or not ok:
        report = {"kind": "BULK_ARCHIVE_INTEGRITY", "passed": ok, "verification": verification,
                  "imported": False, "real_data_verified": False,
                  "note": "fail-closed: nothing is written to RawDatasetStore unless every archive passes"}
        s = json.dumps(report, indent=2)
        if a.report_out:
            a.report_out.write_text(s + "\n", encoding="utf-8")
        print(s)
        return 0 if ok else 2
    store = RawDatasetStore(a.store)
    results = []
    if a.sec_companyfacts:
        results.append(import_sec(store, a.sec_companyfacts, a.refresh, verification[0]["sha256"]))
    if a.stooq_us:
        results.append(import_stooq(store, a.stooq_us, a.chart_range, a.refresh, verification[-1]["sha256"]))
    report = {"kind": "BULK_REAL_DATA_IMPORT", "verification": verification, "results": results, "real_data_verified": False,
              "note": "bulk ingestion only; PIT completeness and downstream verification remain separate gates"}
    spec = importlib.util.spec_from_file_location("_frd_index", ROOT / "tools" / "fetch_real_data.py")
    frd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frd)
    frd.write_store_index(store)
    s = json.dumps(report, indent=2)
    if a.report_out:
        a.report_out.write_text(s + "\n", encoding="utf-8")
    print(s)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
