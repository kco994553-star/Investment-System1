"""Technical company records from PIT market bytes.

The structural engine is not a real model. This module does not invent
indicators, return definitions, weights, or BUY/SELL thresholds.
REAL_INPUT records store the PIT window and set technical outputs to
NOT_AVAILABLE. DEMO records call TechnicalEngine.evaluate unchanged and
stay synthetic.
"""

from __future__ import annotations

import json
from datetime import datetime

from ..versions import IMPLEMENTATION_KIND, TECHNICAL_STRUCTURAL
from .codec import semantic_hash
from .errors import CompanyIdentityError, MissingLookbackError, MissingProvenanceError, TechnicalProducerError
from .pit_market import InputProvenance, bars_from_yahoo_chart, select_window, series_sha256

PRODUCER_ID = "technical.real_input"
PRODUCER_VERSION = "technical-real-producer-v1"
REASON_CODE = "TECHNICAL_NO_REAL_MODEL"
PUBLISHED_REASON = "운영 Snapshot이 연결되지 않았습니다."
BLOCKER = (
    "B3: engine is v0.6 structural placeholder (synthetic); "
    "official indicator/return policy is not frozen"
)
CONTRACT = "TECHNICAL_COMPANY_RECORD"
SCHEMA_VERSION = 1
BATCH_CONTRACT = "TECHNICAL_INPUT_BATCH"

# Result-affecting policies that the approved Technical record does not freeze.
# Listed, not implemented.
POLICY_BLOCKERS = (
    {
        "id": "U-01",
        "class": "POLICY_BLOCKED",
        "detail": "official Model Indicator Set is not frozen; no new indicator is computed",
    },
    {
        "id": "PRICE_SERIES",
        "class": "POLICY_BLOCKED",
        "detail": "close vs adjclose vs Track A CLOSE_X_POST_AS_OF_SPLIT_FACTOR is not an approved Technical return input",
    },
    {
        "id": "RETURN_TRANSFORM",
        "class": "POLICY_BLOCKED",
        "detail": "simple vs log return, and any price-to-return map, is not in the approved design",
    },
    {
        "id": "U-02",
        "class": "POLICY_BLOCKED",
        "detail": "indicator parameters and the official lookback length are not frozen; caller lookback is an input identity only",
    },
    {
        "id": "U-04",
        "class": "POLICY_BLOCKED",
        "detail": "regime classification algorithm is not frozen; engine thresholds stay inside the synthetic placeholder",
    },
    {
        "id": "U-05",
        "class": "POLICY_BLOCKED",
        "detail": "S=1..N scenario generator is not frozen; placeholder shocks are not promoted",
    },
    {
        "id": "VOLUME_FEATURE",
        "class": "POLICY_BLOCKED",
        "detail": "volume is a PIT input fact only; no volume indicator or weight is defined",
    },
)


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TechnicalProducerError(f"{label} must be a timezone-aware datetime")
    return value


def _lookback_id(lookback_id: str, lookback_bars: int) -> str:
    if not isinstance(lookback_id, str) or not lookback_id.strip():
        raise MissingLookbackError("lookback_id is required and is not defaulted")
    if not isinstance(lookback_bars, int) or isinstance(lookback_bars, bool) or lookback_bars < 1:
        raise MissingLookbackError("lookback bar_count must be a positive integer supplied by the caller")
    return lookback_id


def _finalize(record: dict) -> dict:
    record["semantic_hash"] = semantic_hash(record)
    record["record_id"] = "tcr_" + record["semantic_hash"][:16]
    return record


def _not_available_outputs() -> dict:
    return {
        "status": "NOT_AVAILABLE",
        "reason_code": REASON_CODE,
        "regime": None,
        "execution_zone": None,
        "invalidation": None,
        "indicators": None,
        "scenarios": None,
        "model_applied": False,
    }


def produce_company(
    *,
    company_id: str,
    ticker: str,
    decision_time: datetime,
    lookback_bars: int,
    lookback_id: str,
    body: bytes,
    provenance: InputProvenance,
    generated_at: datetime,
    on_future: str = "exclude",
) -> dict:
    """One company. Raises on PIT/provenance/lookback/identity failure. Never calls the engine."""
    decision_time = _aware(decision_time, "decision_time")
    generated_at = _aware(generated_at, "generated_at")
    lookback_id = _lookback_id(lookback_id, lookback_bars)
    if not isinstance(company_id, str) or not company_id.strip():
        raise CompanyIdentityError("company_id required")
    if not isinstance(ticker, str) or not ticker.strip():
        raise CompanyIdentityError("ticker required")
    if not isinstance(body, (bytes, bytearray)) or not body:
        raise MissingProvenanceError("raw chart bytes required")
    provenance.validate(bytes(body))
    if provenance.source_reference != ticker:
        raise CompanyIdentityError("provenance source_reference must equal ticker")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MissingProvenanceError("chart bytes are not JSON") from exc
    if not isinstance(payload, dict):
        raise MissingProvenanceError("chart JSON must be an object")
    symbol, currency, bars = bars_from_yahoo_chart(payload)
    if not symbol:
        raise MissingProvenanceError("chart symbol missing")
    if symbol != ticker:
        raise CompanyIdentityError(f"chart symbol {symbol!r} != ticker {ticker!r}; refusing to guess identity")
    chosen = select_window(bars, decision_time, lookback_bars, on_future=on_future)
    window = chosen["window"]
    path = "REAL_INPUT" if provenance.evidence_class == "LIVE_FETCH" else "FIXTURE"
    record = {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "path": path,
        "company_id": company_id,
        "ticker": ticker,
        "as_of": decision_time.isoformat(),
        "available_at": chosen["available_at"].isoformat(),
        "lookback": {
            "lookback_id": lookback_id,
            "bar_count": lookback_bars,
            "first_observed_at": window[0].observed_at.isoformat(),
            "last_observed_at": window[-1].observed_at.isoformat(),
            "future_excluded": chosen["future_excluded"],
            "incomplete_eligible": chosen["incomplete_eligible"],
            "series_sha256": series_sha256(window),
            "role": "INPUT_IDENTITY_NOT_A_MODEL_PARAMETER",
        },
        "technical_outputs": _not_available_outputs(),
        "methodology": {
            "id": "TECHNICAL_STRUCTURAL_PLACEHOLDER",
            "version": TECHNICAL_STRUCTURAL,
            "implementation_kind": IMPLEMENTATION_KIND,
            "status": "POLICY_BLOCKED",
            "producer_id": PRODUCER_ID,
            "producer_version": PRODUCER_VERSION,
            "model_applied": False,
        },
        "input_lineage": [
            {
                "artifact_id": provenance.artifact_id,
                "sha256": provenance.sha256,
                "bytes": provenance.nbytes,
                "source_provider": provenance.source_provider,
                "source_reference": provenance.source_reference,
                "evidence_class": provenance.evidence_class,
                "currency": currency,
                "available_at_rule": "yahoo_chart.to_price_point: available_at = observed_at",
                "price_fields_retained": ["close", "adjclose"],
                "price_field_selected_for_model": None,
            }
        ],
        "source_hashes": [provenance.sha256],
        "generated_at": generated_at.isoformat(),
        "synthetic": provenance.synthetic,
        "validation": {"status": "PASS", "checks": ["pit_window", "provenance_sha256", "company_identity"]},
        "research_state": "POLICY_BLOCKED",
        "policy_blockers": list(POLICY_BLOCKERS),
        "universe_claim": False,
    }
    return _finalize(record)


def produce_demo(
    *,
    company_id: str,
    ticker: str,
    as_of: datetime,
    returns: list[float],
    generated_at: datetime,
    qgv=None,
) -> dict:
    """DEMO path. Calls the existing engine and forces synthetic=True."""
    from .engine import TechnicalEngine

    as_of = _aware(as_of, "as_of")
    generated_at = _aware(generated_at, "generated_at")
    if not isinstance(company_id, str) or not company_id or not isinstance(ticker, str) or not ticker:
        raise CompanyIdentityError("company_id and ticker required")
    snap = TechnicalEngine().evaluate(company_id, as_of, list(returns), qgv=qgv, synthetic=True)
    if snap.synthetic is not True or snap.company_id != company_id:
        raise TechnicalProducerError("demo engine result lost company identity or synthetic flag")
    record = {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "path": "DEMO",
        "company_id": company_id,
        "ticker": ticker,
        "as_of": as_of.isoformat(),
        "available_at": None,
        "lookback": None,
        "technical_outputs": {
            "status": "STRUCTURAL_PLACEHOLDER",
            "reason_code": REASON_CODE,
            "regime": snap.regime.value,
            "execution_zone": snap.execution_zone.value,
            "invalidation": snap.invalidation,
            "scenarios": [dict(s) for s in snap.scenarios],
            "drawdown_recheck": snap.drawdown_recheck,
            "mutated_qgv": snap.mutated_qgv,
            "qgv_snapshot_id_ref": snap.qgv_snapshot_id_ref,
            "technical_version": snap.technical_version,
            "implementation_kind": snap.implementation_kind,
            "indicators": None,
            "model_applied": False,
        },
        "methodology": {
            "id": "TECHNICAL_STRUCTURAL_PLACEHOLDER",
            "version": snap.technical_version,
            "implementation_kind": snap.implementation_kind,
            "status": "SYNTHETIC_PLACEHOLDER",
            "producer_id": PRODUCER_ID,
            "producer_version": PRODUCER_VERSION,
            "model_applied": False,
        },
        "input_lineage": [],
        "source_hashes": [],
        "generated_at": generated_at.isoformat(),
        "synthetic": True,
        "engine_snapshot_id": snap.technical_snapshot_id,
        "validation": {"status": "NOT_RUN", "checks": ["demo_engine_passthrough"]},
        "research_state": "DEMO",
        "policy_blockers": list(POLICY_BLOCKERS),
        "universe_claim": False,
    }
    return _finalize(record)


def produce_batch(items: list[dict]) -> dict:
    """Run produce_company per item. Failures are listed; successes are not back-filled.

    items are kwargs for produce_company. A partial batch is explicit and is not a
    universe validation.
    """
    records = []
    failures = []
    for item in items:
        company_id = item.get("company_id")
        try:
            records.append(produce_company(**item))
        except TechnicalProducerError as exc:
            failures.append({"company_id": company_id, "ticker": item.get("ticker"), "error": str(exc)})
    passed = len(records)
    failed = len(failures)
    if failed and passed:
        coverage = "PARTIAL"
    elif failed:
        coverage = "NONE"
    else:
        coverage = "COMPLETE"
    return {
        "contract": BATCH_CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "requested": len(items),
        "input_pass": passed,
        "input_fail": failed,
        "partial": coverage == "PARTIAL",
        "complete": coverage == "COMPLETE",
        "coverage": coverage,
        "universe_claim": False,
        "universe_size_claim": None,
        "records": records,
        "failures": failures,
    }
