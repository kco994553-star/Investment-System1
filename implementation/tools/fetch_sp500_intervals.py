"""Fetch + ingest the public S&P 500 interval file (C-18 candidate A). Needs network.

NOT RUN in the 2026-09-23 Claude session: sandbox egress disabled, and the raw
GitHub URL is robots-disallowed for the chat fetch tool. Run where network works.

Writes the raw file with sha256 + fetch time (= source_vintage), and a parse
report. Does not Officialize anything and does not resolve tickers to CIKs
(unresolved tickers keep tkr: ids; ticker reuse is a known source limitation).

Usage: python tools/fetch_sp500_intervals.py [--out-dir data/universe] [--verify-closed]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import time  # noqa: E402

from investment_system.providers.sec_submissions import fetch_submissions  # noqa: E402
from investment_system.universe.resolve import resolve_roster  # noqa: E402
from investment_system.universe.sources import parse_ticker_intervals_csv, sp500_history_snapshot  # noqa: E402

URL = "https://raw.githubusercontent.com/fja05680/sp500/master/sp500_ticker_start_end.csv"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
# SEC asks for a descriptive User-Agent with contact; set INVESTMENT_SYSTEM_SEC_UA.
SEC_UA = __import__("os").environ.get("INVESTMENT_SYSTEM_SEC_UA", "Investment-System1 research contact@example.invalid")


def _get(url: str, ua: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": ua}), timeout=30) as resp:
        return resp.read()


def main(out_dir: Path, verify_closed: bool = False) -> dict:
    req = Request(URL, headers={"User-Agent": "Investment-System1 research (universe candidate ingest)"})
    with urlopen(req, timeout=20) as resp:
        body = resp.read()
    fetched = datetime.now(timezone.utc)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"sp500_ticker_start_end_{fetched.date().isoformat()}.csv"
    raw_path.write_bytes(body)
    parsed = parse_ticker_intervals_csv(body.decode("utf-8"))
    probes = {}
    for d in ("2008-09-15", "2016-06-30", "2020-03-31", "2024-12-31"):
        snap = sp500_history_snapshot(parsed, datetime.fromisoformat(d).replace(tzinfo=timezone.utc), fetched.date().isoformat())
        probes[d] = len(snap.ids())
    tick_body = _get(SEC_TICKERS, SEC_UA)
    (out_dir / f"sec_company_tickers_{fetched.date().isoformat()}.json").write_bytes(tick_body)
    cache: dict = {}

    def subs(cik):
        if cik not in cache:
            time.sleep(0.15)  # stay under SEC fair-access 10 req/s
            cache[cik] = fetch_submissions(cik)
        return cache[cik]

    resolved = resolve_roster(
        parsed["roster"], json.loads(tick_body), fetched.date().isoformat(),
        submissions_for=subs if verify_closed else None,
    )
    (out_dir / f"sp500_resolved_roster_{fetched.date().isoformat()}.json").write_text(json.dumps(
        [m.__dict__ for m in resolved["roster"]], indent=1))
    report = {
        "sec_tickers_sha256": hashlib.sha256(tick_body).hexdigest(),
        "resolve_methods": resolved["methods"],
        "n_unresolved": len(resolved["unresolved"]),
        "verify_closed": verify_closed,
        "kind": "SP500_INTERVAL_INGEST",
        "url": URL,
        "fetched_at": fetched.isoformat(),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "n_rows": parsed["n_rows"],
        "bad_rows": parsed["bad_rows"],
        "n_unresolved_tickers": len(parsed["unresolved_tickers"]),
        "end_date_inclusive_assumed": parsed["end_date_inclusive_assumed"],
        "member_count_probes": probes,
        "c18": "candidate only; not Official",
        "real_data_verified": False,
    }
    (out_dir / f"sp500_ingest_report_{fetched.date().isoformat()}.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "data" / "universe"))
    ap.add_argument("--verify-closed", action="store_true", help="check closed intervals via SEC submissions (slow)")
    a = ap.parse_args()
    print(json.dumps(main(Path(a.out_dir), a.verify_closed), indent=2))
