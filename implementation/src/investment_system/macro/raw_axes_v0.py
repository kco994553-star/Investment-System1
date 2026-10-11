"""Macro v0 raw display of the remaining six axes (user decision 2026-10-11).

"매크로 나머지 6축: 원자료 표시만 승인, 국면 판정은 보류."  Exactly one series and
one transform per axis (docs/macro_data_rights/MACRO_V0_SERIES_PROPOSAL.md):

Labor            BLS LNS14000000, monthly SA, published percent / 100.
Monetary Policy  Fed H.15 RIFSPFF_N.B, business day, mean of the month's values / 100;
                 a weekday absent from the file makes the month NOT_AVAILABLE.
Liquidity        Fed H.4.1 total assets (less eliminations from consolidation),
                 Wednesday level; level_t / level_(t-52 weeks) - 1.
Credit           Fed H.8 bank credit, all commercial banks, SA monthly level;
                 level_t / level_(t-12 months) - 1.
Fiscal           Treasury MTS Table 1 current_month_dfct_sur_amt; sum of the latest
                 12 consecutive months (all 12 required), units as published.
FX               Fed H.10 JRXWTFB_N.M is approved as an input, but the public price
                 boundary excludes FX: always NOT_AVAILABLE / PUBLIC_FX_EXCLUDED here.

Display only: no state, threshold, score or regime. Missing periods are never
filled and nothing defaults to 0. Pure functions: no network, environment or storage.
"""
from __future__ import annotations

import calendar
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
import io
import json
import re

CONFIG = {"id": "MACRO_V0_RAW_AXES/1", "marker": "v0 · 원자료 표시 · 국면 판정 보류",
          "calibration": "UNCALIBRATED", "status": "RAW_DISPLAY_ONLY", "decided_on": "2026-10-11"}
AXES = ("Labor", "Monetary Policy", "Liquidity", "Credit", "Fiscal", "FX")
FORMATS = {"Labor": ("BLS_API_V1_JSON",), "Monetary Policy": ("FED_DDP_CSV",), "Liquidity": ("FED_DDP_CSV",),
           "Credit": ("FED_DDP_CSV",), "Fiscal": ("FISCALDATA_MTS_JSON",)}  # FX is never collected for public output.
LABOR_SERIES_CODE = "LNS14000000"
H15_IDENTIFIER = "H15/H15/RIFSPFF_N.B"
AXIS_META = {
    "Labor": {"agency": "BLS", "source_series_id": "BLS:LNS14000000", "frequency": "M", "seasonal_adjustment": "SA",
              "transform": "PUBLISHED_PERCENT_DIV_100", "value_unit": "RATIO"},
    "Monetary Policy": {"agency": "FED_H15", "source_series_id": "FED:H15:RIFSPFF_N.B", "frequency": "B",
                        "seasonal_adjustment": "NSA", "transform": "MONTHLY_MEAN_PERCENT_DIV_100", "value_unit": "RATIO"},
    "Liquidity": {"agency": "FED_H41", "source_series_id": "FED:H41:TOTAL_ASSETS_LESS_ELIMINATIONS:WEDNESDAY_LEVEL",
                  "frequency": "W", "seasonal_adjustment": "NSA", "transform": "RATIO_TO_52_WEEKS_EARLIER_MINUS_1",
                  "value_unit": "RATIO"},
    "Credit": {"agency": "FED_H8", "source_series_id": "FED:H8:BANK_CREDIT:ALL_COMMERCIAL_BANKS:SA:MONTHLY",
               "frequency": "M", "seasonal_adjustment": "SA", "transform": "RATIO_TO_12_MONTHS_EARLIER_MINUS_1",
               "value_unit": "RATIO"},
    "Fiscal": {"agency": "TREASURY_MTS", "source_series_id": "TREASURY:MTS:mts_table_1:current_month_dfct_sur_amt",
               "frequency": "M", "seasonal_adjustment": "NSA", "transform": "TRAILING_12_MONTH_SUM",
               "value_unit": "CURRENCY_AS_PUBLISHED"},
    "FX": {"agency": "FED_H10", "source_series_id": "FED:H10:JRXWTFB_N.M", "frequency": "M",
           "seasonal_adjustment": "NSA", "transform": "RATIO_TO_12_MONTHS_EARLIER_MINUS_1", "value_unit": "RATIO"},
}
# Fixed series codes; Liquidity/Credit carry the DDP identifier matched by the official description.
FIXED_CODES = {"Labor": "LNS14000000", "Monetary Policy": "RIFSPFF_N.B", "Fiscal": "current_month_dfct_sur_amt",
               "FX": "JRXWTFB_N.M"}
MATCHED_CODE = {"Liquidity": r"H41/H41/[A-Z0-9_.]{1,40}", "Credit": r"H8/H8/[A-Z0-9_.]{1,40}"}
KEYS = ("state", "value", "value_unit", "period", "base_period", "published_value", "base_value", "observation_count",
        "agency", "source_series_id", "source_series_code", "frequency", "seasonal_adjustment", "transform",
        "release_at", "release_basis", "acquired_at", "source_sha256", "reason_codes")
DETAIL = ("value", "period", "base_period", "published_value", "base_value", "observation_count")
REASONS = ("SOURCE_NOT_COLLECTED", "SOURCE_NOT_AVAILABLE", "SERIES_NOT_CONFIGURED", "SYNTHETIC_INPUT_NOT_PUBLIC",
           "SOURCE_AFTER_AS_OF", "PROVIDER_ERROR", "SCHEMA_MISMATCH", "SERIES_NOT_FOUND", "MISSING_SOURCE",
           "INVALID_VALUE", "CONFLICTING_DUPLICATE", "BASE_PERIOD_MISSING", "INCOMPLETE_PERIOD",
           "PUBLIC_FX_EXCLUDED", "REGIME_JUDGEMENT_DEFERRED")
REGIME = {"state": "NOT_AVAILABLE", "value": None, "reason_codes": ["REGIME_JUDGEMENT_DEFERRED"]}
QUANTUM = Decimal("1E-10")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", re.ASCII)
_DDP_MISSING = ("ND", "NA", "", "N/A")


class AxisUnavailable(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason if reason in REASONS else "SCHEMA_MISMATCH"


def text(value: Decimal) -> str:
    return format(value, "f")


def _decimal(raw) -> Decimal:
    if type(raw) is not str or _NUMBER.fullmatch(raw.strip()) is None:
        raise AxisUnavailable("INVALID_VALUE")
    value = Decimal(raw.strip())
    if not value.is_finite():
        raise AxisUnavailable("INVALID_VALUE")
    return value


def ratio(value: Decimal, base: Decimal) -> Decimal:
    if value <= 0 or base <= 0:
        raise AxisUnavailable("INVALID_VALUE")
    return (value / base - 1).quantize(QUANTUM, rounding=ROUND_HALF_EVEN)


def percent_to_ratio(value: Decimal) -> Decimal:
    return value / Decimal(100)


def base_month(period: str, months: int = 12) -> str:
    index = int(period[:4]) * 12 + int(period[5:7]) - 1 - months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def base_week(period: str) -> str:
    return (date.fromisoformat(period) - timedelta(weeks=52)).isoformat()


def mean_percent(values: list[Decimal]) -> Decimal:
    return (sum(values, Decimal(0)) / len(values)).quantize(QUANTUM, rounding=ROUND_HALF_EVEN)


# --- BLS (Labor) -------------------------------------------------------------------------------

def labor_series(body: bytes, acquired: datetime) -> dict[str, Decimal]:
    from ..providers.macro_primary import parse_bls
    from .primary_contract import ENDPOINTS, SourceReceipt
    receipt = SourceReceipt("BLS", ENDPOINTS["BLS"], hashlib.sha256(body).hexdigest(), acquired, False, "CLEARED_SCOPE")
    # The BLS request is batched with CPI (CUUR0000SA0); both ids are expected in one body.
    result = parse_bls(body, receipt, expected_series_ids=("CUUR0000SA0", LABOR_SERIES_CODE))
    rows = {o.observation_period: o.value for o in result.observations if o.source_id == "BLS:" + LABOR_SERIES_CODE}
    if not rows:
        for reason in ("PROVIDER_ERROR", "SCHEMA_MISMATCH", "INVALID_VALUE", "CONFLICTING_DUPLICATE"):
            if reason in result.reason_codes:
                raise AxisUnavailable(reason)
        raise AxisUnavailable("MISSING_SOURCE")
    return rows


# --- Federal Reserve Data Download Program CSV ---------------------------------------------------

def parse_ddp_csv(body: bytes) -> list[dict]:
    """Columns of a DDP CSV (label=include, layout=seriescolumn); strict, values never filled."""
    try:
        content = body.decode("utf-8-sig")
    except UnicodeError:
        raise AxisUnavailable("SCHEMA_MISMATCH") from None
    try:
        rows = list(csv.reader(io.StringIO(content)))
    except csv.Error:
        raise AxisUnavailable("SCHEMA_MISMATCH") from None
    header, index = {}, 0
    while index < len(rows):
        row = rows[index]
        index += 1
        if not row:
            continue
        label = row[0].strip().rstrip(":").strip().casefold()
        if label in header:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        header[label] = [cell.strip() for cell in row[1:]]
        if label == "time period":
            break
    required = ("series description", "unit", "multiplier", "unique identifier", "time period")
    if any(k not in header for k in required):
        raise AxisUnavailable("SCHEMA_MISMATCH")
    width = len(header["time period"])
    if width < 1 or any(len(v) != width for v in header.values()):
        raise AxisUnavailable("SCHEMA_MISMATCH")
    columns = [{"identifier": header["unique identifier"][i], "description": header["series description"][i],
                "unit": header["unit"][i], "multiplier": header["multiplier"][i], "values": {}} for i in range(width)]
    for row in rows[index:]:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) != width + 1:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        period = row[0].strip()
        if re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", period) is None:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        for column, raw in zip(columns, row[1:]):
            raw = raw.strip()
            value = None if raw in _DDP_MISSING else _decimal(raw)
            if period in column["values"]:
                if column["values"][period] != value:
                    raise AxisUnavailable("CONFLICTING_DUPLICATE")
                continue
            column["values"][period] = value
    return columns


def _description_ok(axis: str, description: str) -> bool:
    d = " ".join(description.casefold().split())
    if axis == "Liquidity":
        return "total assets" in d and "less eliminations from consolidation" in d and "wednesday level" in d
    return ("bank credit" in d and "all commercial banks" in d and "seasonally adjusted" in d
            and "not seasonally adjusted" not in d)


def select_ddp_column(axis: str, columns: list[dict]) -> dict:
    if axis == "Monetary Policy":
        found = [c for c in columns if c["identifier"] == H15_IDENTIFIER]
    else:
        # Levels only: growth-rate / percent columns of the same aggregate are never the series.
        found = [c for c in columns if re.fullmatch(MATCHED_CODE[axis], c["identifier"]) and _description_ok(axis, c["description"])
                 and "percent" not in c["unit"].casefold() and "growth" not in c["description"].casefold()
                 and "rate" not in c["description"].casefold().split()]
    if not found:
        raise AxisUnavailable("SERIES_NOT_FOUND")
    if len(found) > 1:
        raise AxisUnavailable("SCHEMA_MISMATCH")
    column = found[0]
    multiplier = _decimal(column["multiplier"])
    if multiplier <= 0:
        raise AxisUnavailable("SCHEMA_MISMATCH")
    if axis == "Monetary Policy" and ("percent" not in column["unit"].casefold() or multiplier != 1):
        raise AxisUnavailable("SCHEMA_MISMATCH")
    return column


def _weekdays(year: int, month: int) -> list[str]:
    days = calendar.monthrange(year, month)[1]
    return [date(year, month, d).isoformat() for d in range(1, days + 1) if date(year, month, d).weekday() < 5]


def monetary_policy(values: dict) -> dict:
    """Mean of one complete month. ND on a weekday is a published non-business day; an absent weekday is missing."""
    for period in values:
        if len(period) != 10:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        date.fromisoformat(period)
    months = sorted({p[:7] for p in values}, reverse=True)
    if not months:
        raise AxisUnavailable("MISSING_SOURCE")
    # The newest month may still be in progress; only it and the month before are candidates.
    for month in months[:2]:
        weekdays = _weekdays(int(month[:4]), int(month[5:7]))
        if all(d in values for d in weekdays):
            observed = [values[d] for d in weekdays if values[d] is not None]
            if not observed:
                raise AxisUnavailable("MISSING_SOURCE")
            published = mean_percent(observed)
            return {"period": month, "published_value": text(published), "observation_count": len(observed),
                    "value": text(percent_to_ratio(published))}
    raise AxisUnavailable("INCOMPLETE_PERIOD")


def liquidity(values: dict) -> dict:
    present = {}
    for period, value in values.items():
        if len(period) != 10 or date.fromisoformat(period).weekday() != 2:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        if value is not None:
            present[period] = value
    if not present:
        raise AxisUnavailable("MISSING_SOURCE")
    period = max(present)
    base = base_week(period)
    if base not in present:
        raise AxisUnavailable("BASE_PERIOD_MISSING")
    return {"period": period, "base_period": base, "published_value": text(present[period]),
            "base_value": text(present[base]), "value": text(ratio(present[period], present[base]))}


def credit(values: dict) -> dict:
    present = {}
    for period, value in values.items():
        if re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", period) is None:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        if value is not None:
            present[period] = value
    if not present:
        raise AxisUnavailable("MISSING_SOURCE")
    period = max(present)
    base = base_month(period)
    if base not in present:
        raise AxisUnavailable("BASE_PERIOD_MISSING")
    return {"period": period, "base_period": base, "published_value": text(present[period]),
            "base_value": text(present[base]), "value": text(ratio(present[period], present[base]))}


# --- Treasury FiscalData MTS Table 1 -----------------------------------------------------------

_FY = re.compile(r"(?:FY|Fiscal Year)\s*(\d{4})", re.IGNORECASE)


def _unique_json(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate")
        out[key] = value
    return out


def _bad_constant(_):
    raise ValueError("constant")


def parse_mts_months(body: bytes) -> dict[str, Decimal]:
    """Each month's own-statement `current_month_dfct_sur_amt` (later restatements are not mixed in)."""
    try:
        obj = json.loads(body, object_pairs_hook=_unique_json, parse_constant=_bad_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise AxisUnavailable("SCHEMA_MISMATCH") from None
    if type(obj) is not dict or type(obj.get("data")) is not list:
        raise AxisUnavailable("PROVIDER_ERROR" if type(obj) is dict and "error" in obj else "SCHEMA_MISMATCH")
    meta = obj.get("meta")
    if type(meta) is not dict:
        raise AxisUnavailable("SCHEMA_MISMATCH")
    pages = meta.get("total-pages")
    if pages is not None and str(pages) != "1":
        raise AxisUnavailable("SCHEMA_MISMATCH")  # A partial page is never summed.
    statements: dict[str, list[dict]] = {}
    for row in obj["data"]:
        if type(row) is not dict or type(row.get("record_date")) is not str or type(row.get("classification_desc")) is not str:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["record_date"]) is None:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        date.fromisoformat(row["record_date"])
        statements.setdefault(row["record_date"], []).append(row)
    months: dict[str, Decimal] = {}
    for record_date, rows in statements.items():
        day = date.fromisoformat(record_date)
        name = calendar.month_name[day.month]
        labels = (name, f"{name} {day.year}")
        candidates = [r for r in rows if r["classification_desc"].strip() in labels]
        if len(candidates) > 1:
            # Table 1 lists the prior fiscal year's months too: keep the row under this statement's fiscal year.
            ids = {r.get("classification_id"): r for r in rows if r.get("classification_id") not in (None, "", "null")}
            fiscal = str(rows[0].get("record_fiscal_year", "")).strip()
            chosen = []
            for r in candidates:
                parent = ids.get(r.get("parent_id"))
                match = _FY.search(parent["classification_desc"]) if parent else None
                if match and match.group(1) == fiscal:
                    chosen.append(r)
            candidates = chosen
        if len(candidates) != 1:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        raw = candidates[0].get("current_month_dfct_sur_amt")
        if raw is None or (type(raw) is str and raw.strip() in ("", "null")):
            continue  # Published as missing: never filled.
        period = record_date[:7]
        if period in months:
            raise AxisUnavailable("CONFLICTING_DUPLICATE")
        months[period] = _decimal(raw)
    if not months:
        raise AxisUnavailable("MISSING_SOURCE")
    return months


def fiscal(months: dict[str, Decimal]) -> dict:
    period = max(months)
    window = [base_month(period, n) for n in range(11, -1, -1)]
    if any(m not in months for m in window):
        raise AxisUnavailable("BASE_PERIOD_MISSING")
    return {"period": period, "base_period": window[0], "observation_count": 12,
            "value": text(sum((months[m] for m in window), Decimal(0)))}


# --- Assembly ----------------------------------------------------------------------------------

def unavailable_axis(axis: str, reason: str, *, acquired: datetime | None = None, sha: str | None = None) -> dict:
    row = dict.fromkeys(KEYS)
    row.update(AXIS_META[axis], source_series_code=FIXED_CODES.get(axis), state="NOT_AVAILABLE",
               release_basis="NOT_VERIFIED", acquired_at=acquired.isoformat() if acquired else None,
               source_sha256=sha, reason_codes=[reason])
    return row


def build_axis(axis: str, fmt: str, body: bytes, acquired: datetime, freshness: str) -> dict:
    """One axis from one captured official response; NOT_AVAILABLE on any doubt."""
    sha = hashlib.sha256(body).hexdigest()
    try:
        if axis not in FORMATS or fmt not in FORMATS[axis]:
            raise AxisUnavailable("SCHEMA_MISMATCH")
        code = FIXED_CODES.get(axis)
        if axis == "Labor":
            series = labor_series(body, acquired)
            period = max(series)
            detail = {"period": period, "published_value": text(series[period]),
                      "value": text(percent_to_ratio(series[period]))}
        elif axis == "Fiscal":
            detail = fiscal(parse_mts_months(body))
        else:
            column = select_ddp_column(axis, parse_ddp_csv(body))
            if axis != "Monetary Policy":
                code = column["identifier"]
            detail = {"Monetary Policy": monetary_policy, "Liquidity": liquidity, "Credit": credit}[axis](column["values"])
        row = dict.fromkeys(KEYS)
        row.update(AXIS_META[axis], source_series_code=code, state=freshness, release_basis="NOT_VERIFIED",
                   acquired_at=acquired.isoformat(), source_sha256=sha, reason_codes=[])
        row.update(detail)
        return row
    except AxisUnavailable as error:
        return unavailable_axis(axis, error.reason, acquired=acquired, sha=sha)
    except (InvalidOperation, ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
        return unavailable_axis(axis, "SCHEMA_MISMATCH", acquired=acquired, sha=sha)


def build_block(axes: dict) -> dict:
    axes = dict(axes)
    axes["FX"] = unavailable_axis("FX", "PUBLIC_FX_EXCLUDED")
    return {"config": dict(CONFIG), "axes": {axis: axes[axis] for axis in AXES}, "regime": dict(REGIME, reason_codes=list(REGIME["reason_codes"]))}
