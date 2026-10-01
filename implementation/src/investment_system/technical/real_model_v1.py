"""Technical REAL Model v1. M1 features and M2 regime/zone only.

Does not call the structural placeholder. Does not implement M3 scenarios or
probabilities. Does not publish to the Web. Does not apply an exchange-calendar
gap rule: there is no approved calendar contract, and a fixed calendar-day
cutoff is not a market convention. Session continuity is an explicit
session_index supplied with the stored observations, or the affected feature
is NOT_AVAILABLE.
"""

from __future__ import annotations

import math
from datetime import datetime
from statistics import stdev

from ..contracts.enums import ExecutionZone, TechnicalRegime
from .codec import semantic_hash
from .errors import FutureInputError, MissingProvenanceError, PublicationError, TechnicalProducerError
from .pit_market import bars_from_yahoo_chart

MODEL_ID = "TECHNICAL_REAL_MODEL_V1"
MODEL_VERSION = "v1"
CONTRACT = "TECHNICAL_RESEARCH_RECORD"
SCHEMA_VERSION = 1
M3_REASON = "M3_NOT_APPROVED"
WEB_REASON = "P01_DECISION_REQUIRED"
REGIME_MANDATORY = ("r_20", "r_60", "structure", "sigma_20", "sigma_252")


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TechnicalProducerError(f"{label} must be a timezone-aware datetime")
    return value


def _na(reason: str, **extra) -> dict:
    body = {"status": "NOT_AVAILABLE", "reason_code": reason, "value": None}
    body.update(extra)
    return body


def _ok(value, **extra) -> dict:
    body = {"status": "AVAILABLE", "reason_code": None, "value": value}
    body.update(extra)
    return body


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def session_bars_from_yahoo(payload: dict, decision_time: datetime, session_indexes: list[int] | None) -> list[dict]:
    """Stored chart observations at or before decision_time. Does not invent sessions.

    session_indexes is either None (continuity unverified) or one integer per
    retained observation, in stored order. Timestamp gaps are not converted
    into session numbers. Null close or volume is kept so the two eligibility
    rules can differ. adjclose is ignored.
    """
    decision_time = _aware(decision_time, "decision_time")
    _symbol, _currency, bars = bars_from_yahoo_chart(payload)
    if any(bar.violates(decision_time) for bar in bars):
        raise FutureInputError("supplied input contains a bar after decision_time")
    times = [bar.observed_at for bar in bars]
    if len(times) != len(set(times)) or times != sorted(times):
        raise TechnicalProducerError("price bars must be unique and chronological; refusing to reorder")
    if session_indexes is not None:
        if len(session_indexes) != len(bars):
            raise TechnicalProducerError("session_indexes must match the stored observation count")
        if any(not isinstance(i, int) or isinstance(i, bool) for i in session_indexes):
            raise TechnicalProducerError("session_index must be an integer")
        if session_indexes != sorted(session_indexes) or len(session_indexes) != len(set(session_indexes)):
            raise TechnicalProducerError("session_indexes must be unique and increasing")
    out = []
    for i, bar in enumerate(bars):
        out.append(
            {
                "observed_at": bar.observed_at,
                "session_index": None if session_indexes is None else session_indexes[i],
                "close": bar.close,
                "volume": bar.volume,
            }
        )
    return out


def _maps(observations: list[dict]) -> tuple[dict[int, float], dict[int, float], bool]:
    price: dict[int, float] = {}
    volume: dict[int, float] = {}
    verified = True
    for row in observations:
        idx = row["session_index"]
        if idx is None:
            verified = False
            continue
        if row["close"] is not None:
            if not _finite(row["close"]):
                raise TechnicalProducerError("close must be finite")
            price[idx] = float(row["close"])
        if row["volume"] is not None:
            if not _finite(row["volume"]):
                raise TechnicalProducerError("volume must be finite")
            volume[idx] = float(row["volume"])
    return price, volume, verified


def _endpoint_return(series: dict[int, float], end: int, steps: int) -> dict:
    left = series.get(end - steps)
    right = series.get(end)
    if left is None or right is None:
        return _na("SESSION_GAP")
    if left == 0 or not _finite(left) or not _finite(right):
        return _na("NONFINITE")
    value = right / left - 1.0
    if not _finite(value):
        return _na("NONFINITE")
    return _ok(value)


def _consecutive_closes(series: dict[int, float], end: int, steps: int) -> list[float] | None:
    closes = []
    for session in range(end - steps, end + 1):
        if session not in series:
            return None
        closes.append(series[session])
    return closes


def _step_returns(closes: list[float]) -> list[float] | None:
    out = []
    for left, right in zip(closes, closes[1:]):
        if left == 0 or not _finite(left) or not _finite(right):
            return None
        value = right / left - 1.0
        if not _finite(value):
            return None
        out.append(value)
    return out


def _sigma(series: dict[int, float], end: int, steps: int) -> dict:
    closes = _consecutive_closes(series, end, steps)
    if closes is None:
        return _na("SESSION_GAP")
    returns = _step_returns(closes)
    if returns is None or len(returns) != steps:
        return _na("NONFINITE")
    # Sample standard deviation, ddof=1. Not the placeholder population stdev.
    return _ok(stdev(returns))


def _trend(r_20: dict, r_60: dict) -> dict:
    if r_20["status"] != "AVAILABLE" or r_60["status"] != "AVAILABLE":
        return _na("MISSING_RETURN")
    a = r_20["value"]
    b = r_60["value"]
    if a > 0 and b > 0:
        return _ok("UP")
    if a < 0 and b < 0:
        return _ok("DOWN")
    return _ok("MIXED")


def _structure(series: dict[int, float], end: int) -> dict:
    priors = []
    for session in range(end - 20, end):
        if session not in series:
            return _na("SESSION_GAP")
        priors.append(series[session])
    if end not in series:
        return _na("SESSION_GAP")
    close = series[end]
    if close > max(priors):
        return _ok("PRIOR_HIGH")
    if close < min(priors):
        return _ok("PRIOR_LOW")
    return _ok("INSIDE")


def _swing_at(series: dict[int, float], center: int, high: bool) -> bool:
    if center not in series:
        return False
    others = []
    for delta in range(-5, 6):
        if delta == 0:
            continue
        if center + delta not in series:
            return False
        others.append(series[center + delta])
    close = series[center]
    if high:
        return all(close > other for other in others)
    return all(close < other for other in others)


def _confirmed_swing(series: dict[int, float], end: int) -> dict:
    """Most recent swing whose ±5 neighbours are already stored at or before end.

    The current session is not confirmed: that would need five bars after it.
    """
    low = None
    high = None
    if series:
        start = min(series) + 5
        for center in range(end - 5, start - 1, -1):
            if low is None and _swing_at(series, center, high=False):
                low = {"session_index": center, "close": series[center]}
            if high is None and _swing_at(series, center, high=True):
                high = {"session_index": center, "close": series[center]}
            if low is not None and high is not None:
                break
    return _ok({"low": low, "high": high})


def _volume_ratio(volume: dict[int, float], end: int) -> dict:
    points = [(session, value) for session, value in volume.items() if session <= end]
    if len(points) < 20:
        return _na("MISSING_WINDOW")
    last = sorted(points)[-20:]
    denominator = sum(value for _, value in last) / 20.0
    current = last[-1][1]
    if denominator == 0 or not _finite(denominator) or not _finite(current):
        return _na("NONFINITE")
    return _ok(current / denominator)


def _relative_strength(stock: dict[int, float], spy: dict[int, float] | None, end: int, spy_blocked: str | None) -> dict:
    if spy_blocked is not None:
        return _na(spy_blocked)
    if spy is None:
        return _na("SPY_NOT_SUPPLIED")
    if end not in stock or end - 20 not in stock or end not in spy or end - 20 not in spy:
        return _na("RS_UNALIGNED")
    stock_return = _endpoint_return(stock, end, 20)
    spy_return = _endpoint_return(spy, end, 20)
    if stock_return["status"] != "AVAILABLE" or spy_return["status"] != "AVAILABLE":
        return _na("NONFINITE")
    base = 1.0 + spy_return["value"]
    if base == 0 or not _finite(base):
        return _na("NONFINITE")
    value = (1.0 + stock_return["value"]) / base - 1.0
    if not _finite(value):
        return _na("NONFINITE")
    return _ok(value)


def _volatility_state(sigma_20: dict, sigma_252: dict) -> dict:
    if sigma_20["status"] != "AVAILABLE" or sigma_252["status"] != "AVAILABLE":
        return _na("MISSING_VOLATILITY")
    left = sigma_20["value"]
    right = sigma_252["value"]
    if left > right:
        return _ok("EXPANDING")
    if left < right:
        return _ok("CONTRACTING")
    return _ok("EQUAL")


def _regime(features: dict) -> dict:
    missing = [name for name in REGIME_MANDATORY if features[name]["status"] != "AVAILABLE"]
    if missing:
        return _na("MISSING_MANDATORY_FEATURE", missing=missing)
    sigma_20 = features["sigma_20"]["value"]
    sigma_252 = features["sigma_252"]["value"]
    r_20 = features["r_20"]["value"]
    trend = features["trend"]["value"]
    structure = features["structure"]["value"]
    if sigma_20 > sigma_252 and r_20 < 0:
        regime = TechnicalRegime.HIGH_VOL.value
    elif trend == "UP" and structure != "PRIOR_LOW":
        regime = TechnicalRegime.TREND_UP.value
    elif trend == "DOWN" and structure != "PRIOR_HIGH":
        regime = TechnicalRegime.TREND_DOWN.value
    else:
        regime = TechnicalRegime.RANGE.value
    return _ok(regime, missing=[])


def _zone_for(regime: dict, structure: dict) -> dict:
    if regime["status"] != "AVAILABLE":
        return _na("MISSING_MANDATORY_FEATURE", missing=regime.get("missing", []))
    if regime["value"] == TechnicalRegime.HIGH_VOL.value:
        return _ok(ExecutionZone.RISK_REDUCTION.value)
    if regime["value"] in {TechnicalRegime.TREND_DOWN.value, TechnicalRegime.RANGE.value}:
        return _ok(ExecutionZone.WAIT.value)
    if regime["value"] == TechnicalRegime.TREND_UP.value:
        if structure["status"] == "AVAILABLE" and structure["value"] == "PRIOR_HIGH":
            return _ok(ExecutionZone.ADD.value)
        return _ok(ExecutionZone.ENTRY.value)
    return _na("MISSING_MANDATORY_FEATURE")


def _blocked_price(reason: str) -> dict:
    return {
        "r_5": _na(reason),
        "r_20": _na(reason),
        "r_60": _na(reason),
        "trend": _na(reason),
        "structure": _na(reason),
        "confirmed_swing": _na(reason),
        "sigma_20": _na(reason),
        "sigma_252": _na(reason),
        "volatility_state": _na(reason),
        "rs_20": _na(reason),
    }


def _ensure_sequence(observations: list[dict], decision_time: datetime, label: str) -> None:
    for row in observations:
        if row["observed_at"] > decision_time:
            raise FutureInputError(f"{label} contains a bar after decision_time")
    times = [row["observed_at"] for row in observations]
    if times != sorted(times) or len(times) != len(set(times)):
        raise TechnicalProducerError(f"{label} bars must be unique and chronological; refusing to reorder")
    indexes = [row["session_index"] for row in observations]
    if any(idx is None for idx in indexes) and any(idx is not None for idx in indexes):
        raise TechnicalProducerError(f"{label} session_index must be set on every observation or on none")
    if indexes and indexes[0] is not None:
        if any(not isinstance(idx, int) or isinstance(idx, bool) for idx in indexes):
            raise TechnicalProducerError(f"{label} session_index must be an integer")
        if indexes != sorted(indexes) or len(indexes) != len(set(indexes)):
            raise TechnicalProducerError(f"{label} session_indexes must be unique and increasing")


def _check_split_status(status: str, label: str) -> str:
    if status not in {"UNKNOWN", "NONE", "KNOWN"}:
        raise TechnicalProducerError(f"{label} must be UNKNOWN, NONE, or KNOWN")
    return status


def _normalize_splits(status: str, splits: tuple[datetime, ...] | list[datetime]) -> list[str]:
    if status != "KNOWN" and splits:
        raise TechnicalProducerError("split timestamps require split_status KNOWN")
    out = []
    for stamp in splits:
        out.append(_aware(stamp, "split").isoformat())
    return out


def build_research_record(
    *,
    company_id: str,
    ticker: str,
    decision_time: datetime,
    generated_at: datetime,
    observations: list[dict],
    split_status: str,
    source_sha256: str,
    splits: tuple[datetime, ...] | list[datetime] = (),
    spy_observations: list[dict] | None = None,
    spy_split_status: str | None = None,
    spy_source_sha256: str | None = None,
    synthetic: bool = False,
) -> dict:
    """M1 features, M2 regime/zone, M3 explicitly unavailable. No Web publication."""
    decision_time = _aware(decision_time, "decision_time")
    generated_at = _aware(generated_at, "generated_at")
    split_status = _check_split_status(split_status, "split_status")
    if not isinstance(company_id, str) or not company_id.strip():
        raise TechnicalProducerError("company_id required")
    if not isinstance(ticker, str) or not ticker.strip():
        raise TechnicalProducerError("ticker required")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise MissingProvenanceError("source_sha256 required")
    split_ids = _normalize_splits(split_status, splits)
    if spy_observations is not None:
        if spy_split_status is None:
            raise TechnicalProducerError("spy_split_status required when SPY observations are supplied")
        spy_split_status = _check_split_status(spy_split_status, "spy_split_status")
        if not isinstance(spy_source_sha256, str) or len(spy_source_sha256) != 64:
            raise MissingProvenanceError("spy_source_sha256 required")
    _ensure_sequence(observations, decision_time, "price")
    price, volume, verified = _maps(observations)
    end = max(price) if price else None
    if split_status == "UNKNOWN":
        price_reason = "CORPORATE_ACTION_UNKNOWN"
    elif not verified:
        price_reason = "SESSION_CONTINUITY_UNVERIFIED"
    elif end is None:
        price_reason = "MISSING_WINDOW"
    else:
        price_reason = None
    if price_reason is not None:
        features = _blocked_price(price_reason)
    else:
        features = {
            "r_5": _endpoint_return(price, end, 5),
            "r_20": _endpoint_return(price, end, 20),
            "r_60": _endpoint_return(price, end, 60),
            "structure": _structure(price, end),
            "confirmed_swing": _confirmed_swing(price, end),
            "sigma_20": _sigma(price, end, 20),
            "sigma_252": _sigma(price, end, 252),
        }
        features["trend"] = _trend(features["r_20"], features["r_60"])
        features["volatility_state"] = _volatility_state(features["sigma_20"], features["sigma_252"])
        spy_price = None
        spy_blocked = None
        if spy_observations is None:
            spy_blocked = "SPY_NOT_SUPPLIED"
        else:
            _ensure_sequence(spy_observations, decision_time, "SPY")
            spy_price, _spy_volume, spy_verified = _maps(spy_observations)
            if spy_split_status == "UNKNOWN":
                spy_blocked = "CORPORATE_ACTION_UNKNOWN"
            elif not spy_verified:
                spy_blocked = "SESSION_CONTINUITY_UNVERIFIED"
        features["rs_20"] = _relative_strength(price, spy_price, end, spy_blocked)
    if not verified:
        features["v_20"] = _na("SESSION_CONTINUITY_UNVERIFIED")
    elif not volume or end is None:
        features["v_20"] = _na("MISSING_WINDOW")
    else:
        capped = [session for session in volume if session <= end]
        features["v_20"] = _na("MISSING_WINDOW") if not capped else _volume_ratio(volume, max(capped))
    regime = _regime(features)
    zone = _zone_for(regime, features["structure"])
    record = {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "methodology": {
            "id": MODEL_ID,
            "version": MODEL_VERSION,
            "m1": "APPROVED",
            "m2": "APPROVED",
            "m3": "NOT_APPROVED",
            "m4": "APPROVED",
            "placeholder_engine": "NOT_USED",
            "price_field": "close",
            "return_transform": "simple",
            "composite_weight": None,
            "regime_mandatory": list(REGIME_MANDATORY),
            "exchange_calendar": "UNBOUND",
            "continuity_unit": "EXPLICIT_SESSION_INDEX",
        },
        "company_id": company_id,
        "ticker": ticker,
        "as_of": decision_time.isoformat(),
        "features": features,
        "regime": regime,
        "zone": zone,
        "scenarios": {"status": "NOT_AVAILABLE", "reason_code": M3_REASON, "value": None},
        "web_publication": {"status": "BLOCKED", "reason_code": WEB_REASON},
        "corporate_action": {
            "split_status": split_status,
            "splits": split_ids,
            "close_rewritten": False,
            "total_return": False,
        },
        "continuity": {
            "verified": verified and price_reason != "SESSION_CONTINUITY_UNVERIFIED",
            "exchange_calendar": "UNBOUND",
            "gap_rule_days": None,
        },
        "input_lineage": {
            "source_sha256": source_sha256,
            "spy_source_sha256": spy_source_sha256,
            "price_field": "close",
        },
        "generated_at": generated_at.isoformat(),
        "synthetic": bool(synthetic),
        "scenario_applied": False,
        "order_emitted": False,
        "integration_multiplier_applied": False,
        "universe_claim": False,
    }
    record["semantic_hash"] = semantic_hash(record)
    record["record_id"] = "trm_" + record["semantic_hash"][:16]
    return record


def publish_web_research(record: dict, *, data_state: str = "NOT_AVAILABLE") -> dict:
    """P01 is not decided. Research regime/zone must not become a Web snapshot."""
    del record, data_state
    raise PublicationError("technical research publication is blocked until P01")
