"""M1/M2 research record. M3 stays unavailable. Placeholder engine is not used."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import stdev

import pytest

from investment_system.contracts.models import TechnicalSnapshot
from investment_system.technical.engine import TechnicalEngine
from investment_system.technical.errors import FutureInputError, PublicationError, TechnicalProducerError
from investment_system.technical.exporter import export_producer_snapshot
from investment_system.technical.producer import produce_demo
from investment_system.technical.real_model_v1 import (
    build_research_record,
    publish_web_research,
    session_bars_from_yahoo,
)

ROOT = Path(__file__).resolve().parents[1]
AS_OF = datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc)
GENERATED = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
SHA = "a" * 64
SPY_SHA = "b" * 64
# ---- technical/engine.py pin history (history-preserving; each state is exact) ----
# Pre-adoption pin, recorded 2026-10-01 with PR #15 (code commit 4c69ced): canonical b8e39a2 bytes.
ENGINE_SHA256_PRE_ADOPTION = "f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf"
# Adopted pin: C-28 upstream adoption of Track C 2137883 per user CDR-004 2026-10-03 (additive
# lineage fields + evaluate_stamped; legacy evaluate() byte-identical). This model never calls the
# engine, so its records are identical either way:
# docs/technical_real_model/evidence/c28_adoption_invariance_2026-10-03.json (PASS).
# Owner adoption record: docs/technical_real_producer/C28_UPSTREAM_ADOPTION_2026-10-03.md
ENGINE_SHA256_C28_ADOPTED = "86607bf7004804b923f50cda1db7dbffaf4dd782002a7e0f56ca3c95be625c2c"


def _expected_engine_sha256() -> str:
    """Select the exact pin from the adopted feature itself, never from bytes.

    A partially adopted tree gets a digest no file has, so the byte check fails.
    """
    stamped = hasattr(TechnicalEngine, "evaluate_stamped")
    fields = {"available_at", "data_stamp_refs", "source_vintages", "input_hash"} <= {
        f.name for f in dataclasses.fields(TechnicalSnapshot)
    }
    if stamped and fields:
        return ENGINE_SHA256_C28_ADOPTED
    if not stamped and not fields:
        return ENGINE_SHA256_PRE_ADOPTION
    return "C28_ADOPTION_STATE_INCONSISTENT"


def _series(closes, volumes=True, session_gap_at=None, day_step=1):
    rows = []
    session = 0
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for i, close in enumerate(closes):
        if i:
            session += 2 if session_gap_at == i else 1
        volume = None if volumes is False else 1_000_000.0 + i
        rows.append(
            {
                "observed_at": start + timedelta(days=i * day_step),
                "session_index": session,
                "close": float(close),
                "volume": volume,
            }
        )
    return rows


def _flat(n=253, volume=True):
    return _series([100.0] * n, volumes=volume)


def _rise(n=253):
    return _series([100.0 * (1.001 ** i) for i in range(n)])


def _record(observations, **kw):
    return build_research_record(
        company_id=kw.pop("company_id", "aapl"),
        ticker=kw.pop("ticker", "AAPL"),
        decision_time=kw.pop("decision_time", AS_OF),
        generated_at=kw.pop("generated_at", GENERATED),
        observations=observations,
        split_status=kw.pop("split_status", "NONE"),
        source_sha256=kw.pop("source_sha256", SHA),
        **kw,
    )


def test_constant_rise_is_trend_up_add_and_has_no_scenario():
    record = _record(_rise(), spy_observations=_flat(), spy_split_status="NONE", spy_source_sha256=SPY_SHA)
    assert record["features"]["trend"]["value"] == "UP"
    assert record["features"]["structure"]["value"] == "PRIOR_HIGH"
    assert record["regime"]["value"] == "TREND_UP"
    assert record["zone"]["value"] == "ADD"
    assert record["scenarios"] == {"status": "NOT_AVAILABLE", "reason_code": "M3_NOT_APPROVED", "value": None}
    assert record["scenario_applied"] is False
    assert record["order_emitted"] is False
    assert record["integration_multiplier_applied"] is False
    assert record["web_publication"]["reason_code"] == "P01_DECISION_REQUIRED"
    assert record["methodology"]["placeholder_engine"] == "NOT_USED"
    assert record["continuity"]["gap_rule_days"] is None
    assert "structural-placeholder" not in json.dumps(record)


def test_flat_series_is_range_wait():
    record = _record(_flat())
    assert record["features"]["trend"]["value"] == "MIXED"
    assert record["features"]["structure"]["value"] == "INSIDE"
    assert record["regime"]["value"] == "RANGE"
    assert record["zone"]["value"] == "WAIT"


def test_high_vol_precedes_trend_and_uses_sample_stdev():
    closes = [100.0] * 233
    price = 100.0
    steps = []
    for shock in (0.05, -0.04, 0.03, -0.06, 0.02, -0.05, 0.04, -0.03, 0.02, -0.08,
                  0.01, -0.02, 0.03, -0.04, 0.02, -0.03, 0.01, -0.05, 0.02, -0.04):
        price *= 1.0 + shock
        steps.append(shock)
        closes.append(price)
    record = _record(_series(closes))
    sigma_20 = record["features"]["sigma_20"]["value"]
    sigma_252 = record["features"]["sigma_252"]["value"]
    assert sigma_20 == pytest.approx(stdev(steps))
    assert sigma_20 > sigma_252
    assert record["features"]["r_20"]["value"] < 0
    assert record["regime"]["value"] == "HIGH_VOL"
    assert record["zone"]["value"] == "RISK_REDUCTION"


def test_steady_decline_is_trend_down_wait():
    record = _record(_series([100.0 * (0.999 ** i) for i in range(253)]))
    assert record["features"]["trend"]["value"] == "DOWN"
    assert record["features"]["structure"]["value"] == "PRIOR_LOW"
    assert record["regime"]["value"] == "TREND_DOWN"
    assert record["zone"]["value"] == "WAIT"


def test_pullback_inside_prior_range_is_entry_not_add():
    closes = [100.0 * (1.001 ** i) for i in range(251)]
    closes.append(closes[-1] * 0.999)
    closes.append(closes[-1] * 0.999)
    record = _record(_series(closes))
    assert record["features"]["r_20"]["value"] > 0
    assert record["features"]["r_60"]["value"] > 0
    assert record["features"]["structure"]["value"] == "INSIDE"
    assert record["regime"]["value"] == "TREND_UP"
    assert record["zone"]["value"] == "ENTRY"


def test_missing_endpoint_does_not_delete_shorter_features_or_emit_wait():
    rows = _flat()
    end = rows[-1]["session_index"]
    rows = [row for row in rows if row["session_index"] != end - 60]
    record = _record(rows)
    assert record["features"]["r_5"]["status"] == "AVAILABLE"
    assert record["features"]["sigma_20"]["status"] == "AVAILABLE"
    assert record["features"]["r_60"]["reason_code"] == "SESSION_GAP"
    assert record["features"]["sigma_252"]["reason_code"] == "SESSION_GAP"
    assert record["regime"]["status"] == "NOT_AVAILABLE"
    assert record["regime"]["value"] is None
    assert record["zone"]["value"] is None
    assert record["zone"]["value"] != "WAIT"


def test_volume_gap_does_not_remove_price_features():
    rows = _flat(volume=False)
    record = _record(rows)
    assert record["features"]["v_20"]["status"] == "NOT_AVAILABLE"
    assert record["features"]["r_20"]["status"] == "AVAILABLE"
    assert record["regime"]["value"] == "RANGE"


def test_unknown_corporate_action_blocks_price_features_not_volume():
    record = _record(_flat(), split_status="UNKNOWN")
    assert record["features"]["r_20"]["reason_code"] == "CORPORATE_ACTION_UNKNOWN"
    assert record["features"]["sigma_20"]["value"] is None
    assert record["features"]["v_20"]["status"] == "AVAILABLE"
    assert record["regime"]["value"] is None
    assert record["corporate_action"]["close_rewritten"] is False
    assert record["corporate_action"]["total_return"] is False


def test_known_split_does_not_rewrite_close_return():
    base = _record(_rise())
    stamped = _record(
        _rise(),
        split_status="KNOWN",
        splits=(datetime(2021, 6, 1, tzinfo=timezone.utc),),
    )
    assert stamped["features"]["r_20"]["value"] == pytest.approx(base["features"]["r_20"]["value"])
    assert stamped["corporate_action"]["close_rewritten"] is False


def test_relative_strength_uses_same_session_and_close_not_a_cross_section():
    stock = _series([100.0] * 233 + [110.0] * 20)
    spy = _flat()
    record = _record(stock, spy_observations=spy, spy_split_status="NONE", spy_source_sha256=SPY_SHA)
    assert record["features"]["rs_20"]["value"] == pytest.approx(record["features"]["r_20"]["value"])
    broken = [row for row in spy if row["session_index"] != stock[-1]["session_index"] - 20]
    missed = _record(stock, spy_observations=broken, spy_split_status="NONE", spy_source_sha256=SPY_SHA)
    assert missed["features"]["rs_20"]["reason_code"] == "RS_UNALIGNED"
    assert missed["features"]["r_20"]["status"] == "AVAILABLE"


def test_spy_absence_does_not_block_regime():
    record = _record(_flat())
    assert record["features"]["rs_20"]["reason_code"] == "SPY_NOT_SUPPLIED"
    assert record["regime"]["value"] == "RANGE"


def test_calendar_gap_is_not_a_session_rule():
    late = datetime(2040, 1, 1, tzinfo=timezone.utc)
    wide_rows = _series([100.0 * (1.001 ** i) for i in range(253)], day_step=10)
    wide = _record(wide_rows, decision_time=late)
    assert wide["regime"]["value"] == "TREND_UP"
    assert wide["continuity"]["gap_rule_days"] is None
    gapped = _series([100.0 * (1.001 ** i) for i in range(253)], session_gap_at=10)
    blocked = _record(gapped)
    assert blocked["features"]["sigma_252"]["reason_code"] == "SESSION_GAP"
    assert blocked["zone"]["value"] is None


def test_unverified_session_index_fails_closed():
    rows = _flat()
    for row in rows:
        row["session_index"] = None
    record = _record(rows)
    assert record["features"]["r_5"]["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"
    assert record["features"]["v_20"]["reason_code"] == "SESSION_CONTINUITY_UNVERIFIED"
    assert record["regime"]["value"] is None


def test_confirmed_swing_does_not_use_bars_after_the_decision_session():
    closes = [10.0] * 253
    closes[100] = 1.0
    closes[252] = 1.0
    record = _record(_series(closes))
    low = record["features"]["confirmed_swing"]["value"]["low"]
    assert low["session_index"] == 100
    assert low["close"] == 1.0
    assert record["features"]["confirmed_swing"]["value"]["high"] is None


def test_duplicate_or_future_or_non_monotonic_input_fails():
    rows = _flat(5)
    rows[2]["observed_at"] = rows[0]["observed_at"]
    with pytest.raises(TechnicalProducerError, match="chronological"):
        _record(rows)
    future = _flat(5)
    future[-1]["observed_at"] = AS_OF + timedelta(days=1)
    with pytest.raises(FutureInputError):
        _record(future)
    dup = _flat(5)
    dup[3]["session_index"] = dup[2]["session_index"]
    with pytest.raises(TechnicalProducerError, match="session_indexes"):
        _record(dup)


def test_yahoo_parser_ignores_adjusted_close_and_does_not_invent_sessions():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stamps = [int((start + timedelta(days=i)).timestamp()) for i in range(6)]
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "AAPL", "currency": "USD"},
                    "timestamp": stamps,
                    "indicators": {
                        "quote": [{"close": [100, 101, 102, 103, 104, 105], "volume": [1, 1, 1, 1, 1, 1]}],
                        "adjclose": [{"adjclose": [1, 1, 1, 1, 1, 1]}],
                    },
                }
            ]
        }
    }
    bars = session_bars_from_yahoo(payload, AS_OF, list(range(6)))
    assert all(set(row) == {"observed_at", "session_index", "close", "volume"} for row in bars)
    record = _record(bars, split_status="NONE")
    assert record["features"]["r_5"]["value"] == pytest.approx(105 / 100 - 1.0)
    with pytest.raises(TechnicalProducerError, match="session_indexes"):
        session_bars_from_yahoo(payload, AS_OF, [0, 1])


def test_same_input_same_hash_and_generated_at_is_excluded():
    left = _record(_rise())
    right = _record(_rise(), generated_at=GENERATED + timedelta(hours=3))
    assert left["semantic_hash"] == right["semantic_hash"]
    changed = _rise()
    changed[-1]["close"] += 1.0
    assert _record(changed)["semantic_hash"] != left["semantic_hash"]


def test_web_publication_and_existing_exporter_stay_blocked():
    record = _record(_rise())
    with pytest.raises(PublicationError, match="P01"):
        publish_web_research(record, data_state="LIVE")
    exported = export_producer_snapshot(requested_as_of=AS_OF, generated_at=GENERATED)
    assert exported["data"] is None
    assert exported["data_state"] == "NOT_AVAILABLE"
    assert record["regime"]["value"] not in json.dumps(exported["data"])


def test_placeholder_engine_is_unchanged_and_not_used_by_the_real_model():
    source = (ROOT / "src/investment_system/technical/real_model_v1.py").read_text()
    engine = (ROOT / "src/investment_system/technical/engine.py").read_text()
    assert "TechnicalEngine" not in source
    assert "IntegrationEngine" not in source
    assert "timedelta(days=5)" not in source
    assert hashlib.sha256(engine.encode()).hexdigest() == _expected_engine_sha256()
    demo = produce_demo(
        company_id="aapl",
        ticker="AAPL",
        as_of=AS_OF,
        returns=[0.01, -0.02, 0.03, 0.005, 0.01, -0.001],
        generated_at=GENERATED,
    )
    assert demo["technical_outputs"]["status"] == "STRUCTURAL_PLACEHOLDER"
