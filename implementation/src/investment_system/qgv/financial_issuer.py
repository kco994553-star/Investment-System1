"""FINANCIAL issuer path. NEW IMPLEMENTATION. Not Stage 2 PASS."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..contracts.models import DataStamp
from ..contracts.raw import RawFundamentals
from ..providers.sec_companyfacts import facts_to_raw, try_fetch_companyfacts
from .pipeline import AnalysisPipeline

FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "jpm_financial_synthetic.json"


def synthetic_jpm(as_of: datetime | None = None) -> RawFundamentals:
    as_of = as_of or datetime(2026, 9, 14, tzinfo=timezone.utc)
    row = json.loads(FIXTURE.read_text(encoding="utf-8"))
    stamp = DataStamp(
        data_stamp_id="fix_jpm_fin",
        source_provider="fixture-catalog",
        source_type="fundamentals",
        source_reference="jpm-synthetic",
        published_at=as_of,
        available_at=as_of,
        observed_at=as_of,
        synthetic=True,
    )
    skip = {"kind", "note", "cik", "company_id"}
    fields = {k: v for k, v in row.items() if k not in skip}
    return RawFundamentals(company_id="jpm", stamp=stamp, source_kind="SYNTHETIC", **fields)


def analyze_synthetic_jpm(as_of: datetime | None = None):
    return AnalysisPipeline().analyze_raw(synthetic_jpm(as_of))


def try_sec_jpm(as_of: datetime | None = None):
    as_of = as_of or datetime.now(timezone.utc)
    payload = try_fetch_companyfacts("0000019617")
    if payload is None:
        return None
    raw = facts_to_raw("jpm", "0000019617", payload, as_of, synthetic=False)
    # Parser yields GENERAL fields; profile still FINANCIAL for scoring contract.
    raw = RawFundamentals(**{**raw.__dict__, "profile_kind": "FINANCIAL", "source_kind": "LIVE_FETCH"})
    return AnalysisPipeline().analyze_raw(raw)
