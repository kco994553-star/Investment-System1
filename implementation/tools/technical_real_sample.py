"""Three-name LIVE_FETCH sample. Does not commit Yahoo payloads.

Writes a price-free evidence summary. Not a Top-500 validation.
Network is used only when --fetch is passed. Replay (--from-store) is offline.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.ingestion.raw_store import RawDatasetStore  # noqa: E402
from investment_system.providers.yahoo_chart import USER_AGENT, YAHOO_CHART  # noqa: E402
from investment_system.technical.pit_market import InputProvenance  # noqa: E402
from investment_system.technical.producer import produce_batch  # noqa: E402

NAMES = (("aapl", "AAPL"), ("nvda", "NVDA"), ("msft", "MSFT"))
DECISION = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
LOOKBACK_BARS = 60
LOOKBACK_ID = "caller-window-60-not-a-model-parameter"


def fetch_into(store: RawDatasetStore, chart_range: str) -> None:
    from urllib.request import Request, urlopen

    for _cid, ticker in NAMES:
        url = YAHOO_CHART.format(symbol=ticker, range=chart_range)
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urlopen(req, timeout=20) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
        store.put(
            f"yahoo_chart:{ticker}:{chart_range}",
            body,
            url,
            "YAHOO_CHART",
            "application/json",
            "technical_real_sample.py",
            status,
        )


def run(store: RawDatasetStore, chart_range: str, generated_at: datetime) -> dict:
    items = []
    for company_id, ticker in NAMES:
        aid = f"yahoo_chart:{ticker}:{chart_range}"
        body = store.get_bytes(aid)
        manifest = store.get_manifest(aid)
        items.append(
            dict(
                company_id=company_id,
                ticker=ticker,
                decision_time=DECISION,
                lookback_bars=LOOKBACK_BARS,
                lookback_id=LOOKBACK_ID,
                body=body,
                provenance=InputProvenance(
                    artifact_id=aid,
                    sha256=manifest["sha256"],
                    nbytes=manifest["bytes"],
                    source_provider="yahoo-chart",
                    source_reference=ticker,
                    evidence_class="LIVE_FETCH",
                    synthetic=False,
                ),
                generated_at=generated_at,
            )
        )
    batch = produce_batch(items)
    return {
        "kind": "TECHNICAL_REAL_INPUT_SAMPLE",
        "universe_claim": False,
        "n_companies": len(NAMES),
        "not_top500": True,
        "decision_time": DECISION.isoformat(),
        "lookback_id": LOOKBACK_ID,
        "lookback_bars": LOOKBACK_BARS,
        "chart_range": chart_range,
        "coverage": batch["coverage"],
        "partial": batch["partial"],
        "input_pass": batch["input_pass"],
        "input_fail": batch["input_fail"],
        "failures": batch["failures"],
        "records": [
            {
                "company_id": r["company_id"],
                "ticker": r["ticker"],
                "path": r["path"],
                "synthetic": r["synthetic"],
                "as_of": r["as_of"],
                "available_at": r["available_at"],
                "validation": r["validation"]["status"],
                "research_state": r["research_state"],
                "technical_outputs": r["technical_outputs"]["status"],
                "reason_code": r["technical_outputs"]["reason_code"],
                "model_applied": r["technical_outputs"]["model_applied"],
                "future_excluded": r["lookback"]["future_excluded"],
                "incomplete_eligible": r["lookback"]["incomplete_eligible"],
                "first_observed_at": r["lookback"]["first_observed_at"],
                "last_observed_at": r["lookback"]["last_observed_at"],
                "series_sha256": r["lookback"]["series_sha256"],
                "source_hashes": r["source_hashes"],
                "semantic_hash": r["semantic_hash"],
            }
            for r in batch["records"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--range", default="5y")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--generated-at", default="2026-10-01T11:15:00+00:00")
    args = parser.parse_args()
    store = RawDatasetStore(args.store)
    if args.fetch:
        fetch_into(store, args.range)
    generated = datetime.fromisoformat(args.generated_at)
    summary = run(store, args.range, generated)
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.evidence:
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if summary["input_pass"] == summary["n_companies"] and summary["input_fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
