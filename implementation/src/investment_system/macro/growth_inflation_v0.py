"""Macro v0 Growth/Inflation axes (user decision 2026-10-11), v0 UNCALIBRATED defaults.

Growth    = BEA NIPA T10101 line 1 (series A191RL), published percent change from
            preceding period at a seasonally adjusted annual rate, used as-is / 100.
Inflation = BLS CPI-U all items NSA (CUUR0000SA0), index_t / index_{t-12} - 1.

Both values feed the unchanged MacroEngine v0.1.1 thresholds. No new threshold,
weight or regime mapping exists here: the overall 8-axis regime stays
NOT_AVAILABLE. Missing months are never filled and nothing defaults to 0.
Pure functions only: no network, credentials, environment or storage.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import io
import re

from .engine import MacroEngine
from .primary_contract import ENDPOINTS, SourceReceipt
from ..versions import MACRO_CONFIRMED

CONFIG = {"id": "MACRO_V0_GROWTH_INFLATION/1", "marker": "v0 · UNCALIBRATED",
          "calibration": "UNCALIBRATED", "status": "DEFAULT_EDITABLE", "decided_on": "2026-10-11"}
GROWTH_SOURCE = "BEA:NIPA:T10101:1:Q"
GROWTH_SERIES_CODE = "A191RL"
INFLATION_SOURCE = "BLS:CUUR0000SA0"
INFLATION_SERIES_CODE = "CUUR0000SA0"
# Published flat file of all quarterly NIPA series (no API key).
BEA_FLAT_Q_URL = "https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt"
FORMATS = {"Growth": ("BEA_NIPA_FLAT_Q", "BEA_API_NIPA_JSON"), "Inflation": ("BLS_API_V1_JSON",)}
AXIS_META = {
    "Growth": {"agency": "BEA", "source_series_id": GROWTH_SOURCE, "source_series_code": GROWTH_SERIES_CODE,
               "frequency": "Q", "seasonal_adjustment": "SAAR", "transform": "PUBLISHED_PERCENT_DIV_100"},
    "Inflation": {"agency": "BLS", "source_series_id": INFLATION_SOURCE, "source_series_code": INFLATION_SERIES_CODE,
                  "frequency": "M", "seasonal_adjustment": "NSA", "transform": "YOY_INDEX_RATIO_MINUS_1"},
}
AXIS_KEYS = {
    "Growth": ("state", "value", "period", "published_percent", "agency", "source_series_id", "source_series_code",
               "frequency", "seasonal_adjustment", "transform", "release_at", "release_basis", "acquired_at",
               "source_sha256", "reason_codes"),
    "Inflation": ("state", "value", "period", "base_period", "index_value", "base_index_value", "agency",
                  "source_series_id", "source_series_code", "frequency", "seasonal_adjustment", "transform",
                  "release_at", "release_basis", "acquired_at", "source_sha256", "reason_codes"),
}
REASONS = ("SOURCE_NOT_COLLECTED", "SOURCE_NOT_AVAILABLE", "SOURCE_KEY_NOT_CONFIGURED", "SYNTHETIC_INPUT_NOT_PUBLIC",
           "SOURCE_AFTER_AS_OF", "INVALID_RECEIPT", "PROVIDER_ERROR", "SCHEMA_MISMATCH", "MISSING_SOURCE",
           "INVALID_VALUE", "CONFLICTING_DUPLICATE", "BASE_MONTH_MISSING", "AXIS_NOT_AVAILABLE",
           "EIGHT_AXIS_MAPPING_NOT_ADOPTED")
ENGINE_STATES = ("NORMAL", "WARNING", "EMERGENCY", "NOT_AVAILABLE")
ENGINE_LABELS = ("NEUTRAL", "INFLATION_SHOCK", "STAGFLATION_RISK", "EXPANSION")
YOY_QUANTUM = Decimal("1E-10")
_MISSING = ("", "N/A", "NA", "(NA)", "--", "---", "...", "(D)", "-")
_NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", re.ASCII)


class AxisUnavailable(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason if reason in REASONS else "SCHEMA_MISMATCH"


def _decimal(raw: str) -> Decimal | None:
    raw = raw.strip()
    if raw in _MISSING:
        return None
    if _NUMBER.fullmatch(raw) is None:
        raise AxisUnavailable("INVALID_VALUE")
    value = Decimal(raw.replace(",", ""))
    if not value.is_finite():
        raise AxisUnavailable("INVALID_VALUE")
    return value


def text(value: Decimal) -> str:
    return format(value, "f")


def parse_bea_flat_quarterly(body: bytes, series_code: str = GROWTH_SERIES_CODE) -> dict[str, Decimal]:
    """Rows of one series from BEA NipaDataQ.txt (`%SeriesCode%,Period,Value`)."""
    try:
        content = body.decode("utf-8-sig")
    except UnicodeError:
        raise AxisUnavailable("SCHEMA_MISMATCH") from None
    lines = content.splitlines()
    if not lines:
        raise AxisUnavailable("SCHEMA_MISMATCH")
    header = [h.strip().strip("%").strip().casefold() for h in next(csv.reader([lines[0]]))]
    if header != ["seriescode", "period", "value"]:
        raise AxisUnavailable("SCHEMA_MISMATCH")
    values: dict[str, Decimal] = {}
    prefix = series_code + ","
    for line in lines[1:]:
        if not line.lstrip('"').startswith(prefix):
            continue
        row = next(csv.reader([line]))
        if len(row) != 3 or row[0].strip() != series_code:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        period = row[1].strip()
        if re.fullmatch(r"[0-9]{4}Q[1-4]", period) is None:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        value = _decimal(row[2])
        if value is None:
            continue  # Published as missing: never filled.
        if period in values and values[period] != value:
            raise AxisUnavailable("CONFLICTING_DUPLICATE")
        values[period] = value
    if not values:
        raise AxisUnavailable("MISSING_SOURCE")
    return values


def _receipt(provider: str, body: bytes, acquired: datetime) -> SourceReceipt:
    return SourceReceipt(provider, ENDPOINTS[provider], hashlib.sha256(body).hexdigest(), acquired, False, "CLEARED_SCOPE")


def _parsed_reason(result) -> str:
    for reason in ("PROVIDER_ERROR", "SCHEMA_MISMATCH", "INVALID_VALUE", "CONFLICTING_DUPLICATE", "INVALID_RECEIPT"):
        if reason in result.reason_codes:
            return reason
    return "MISSING_SOURCE"


def growth_series(fmt: str, body: bytes, acquired: datetime) -> dict[str, Decimal]:
    if fmt == "BEA_NIPA_FLAT_Q":
        return parse_bea_flat_quarterly(body)
    from ..providers.macro_primary import parse_bea_nipa
    result = parse_bea_nipa(body, _receipt("BEA", body, acquired), expected_table="T10101")
    rows = [o for o in result.observations if o.source_id == GROWTH_SOURCE]
    if not rows:
        raise AxisUnavailable(_parsed_reason(result))
    if any(o.source_series_code != GROWTH_SERIES_CODE for o in rows):
        raise AxisUnavailable("SCHEMA_MISMATCH")
    return {o.observation_period: o.value for o in rows}


def inflation_series(body: bytes, acquired: datetime) -> dict[str, Decimal]:
    from ..providers.macro_primary import parse_bls
    result = parse_bls(body, _receipt("BLS", body, acquired), expected_series_ids=(INFLATION_SERIES_CODE,))
    rows = {o.observation_period: o.value for o in result.observations if o.source_id == INFLATION_SOURCE}
    if not rows:
        raise AxisUnavailable(_parsed_reason(result))
    return rows


def base_month(period: str) -> str:
    year, month = int(period[:4]), int(period[5:7])
    return f"{year - 1:04d}-{month:02d}"


def growth_value(published_percent: Decimal) -> Decimal:
    return published_percent / Decimal(100)


def yoy(index_value: Decimal, base_index_value: Decimal) -> Decimal:
    if base_index_value <= 0 or index_value <= 0:
        raise AxisUnavailable("INVALID_VALUE")
    return (index_value / base_index_value - 1).quantize(YOY_QUANTUM, rounding=ROUND_HALF_EVEN)


def unavailable_axis(axis: str, reason: str, *, acquired: datetime | None = None, sha: str | None = None) -> dict:
    row = dict.fromkeys(AXIS_KEYS[axis])
    row.update(AXIS_META[axis], state="NOT_AVAILABLE", release_basis="NOT_VERIFIED",
               acquired_at=acquired.isoformat() if acquired else None, source_sha256=sha, reason_codes=[reason])
    return row


def build_axis(axis: str, fmt: str, body: bytes, acquired: datetime, freshness: str) -> dict:
    """One axis from one captured official response; NOT_AVAILABLE on any doubt."""
    sha = hashlib.sha256(body).hexdigest()
    try:
        if fmt not in FORMATS[axis]:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        row = dict.fromkeys(AXIS_KEYS[axis])
        row.update(AXIS_META[axis], state=freshness, release_basis="NOT_VERIFIED",
                   acquired_at=acquired.isoformat(), source_sha256=sha, reason_codes=[])
        if axis == "Growth":
            series = growth_series(fmt, body, acquired)
            period = max(series)
            row.update(period=period, published_percent=text(series[period]), value=text(growth_value(series[period])))
        else:
            series = inflation_series(body, acquired)
            period = max(series)
            base = base_month(period)
            if base not in series:
                raise AxisUnavailable("BASE_MONTH_MISSING")
            row.update(period=period, base_period=base, index_value=text(series[period]),
                       base_index_value=text(series[base]), value=text(yoy(series[period], series[base])))
        return row
    except AxisUnavailable as error:
        return unavailable_axis(axis, error.reason, acquired=acquired, sha=sha)
    except (InvalidOperation, ValueError, TypeError, KeyError, RecursionError):
        return unavailable_axis(axis, "SCHEMA_MISMATCH", acquired=acquired, sha=sha)


def evaluate_engine(axes: dict, as_of: datetime) -> dict:
    """Existing MacroEngine v0.1.1 only when both axes are available; never default inputs."""
    base = {"name": "MacroEngine", "version": MACRO_CONFIRMED, "state": "NOT_AVAILABLE",
            "rule_label": None, "reason_codes": ["AXIS_NOT_AVAILABLE"]}
    if any(axes[a]["state"] == "NOT_AVAILABLE" or axes[a]["value"] is None for a in ("Growth", "Inflation")):
        return base
    snapshot = MacroEngine().evaluate(as_of.astimezone(timezone.utc), {
        "growth": float(Decimal(axes["Growth"]["value"])), "inflation": float(Decimal(axes["Inflation"]["value"]))},
        synthetic=False)
    return dict(base, state=snapshot.state.value, rule_label=snapshot.regime, reason_codes=[])


def build_block(axes: dict, as_of: datetime) -> dict:
    return {"config": dict(CONFIG), "axes": axes, "engine": evaluate_engine(axes, as_of),
            "regime": {"state": "NOT_AVAILABLE", "value": None, "reason_codes": ["EIGHT_AXIS_MAPPING_NOT_ADOPTED"]}}


def fresh(acquired: datetime, as_of: datetime, stale_after: timedelta) -> str:
    return "STALE" if as_of - acquired > stale_after else "LIVE"
