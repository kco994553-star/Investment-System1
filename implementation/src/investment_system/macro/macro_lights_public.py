"""Public part of the macro lights v1 (PLAYBOOK_V1 13-5): employment, inflation and curve only.

Government statistics, never prices: the market (SPY) and credit (HYG/IEF) lights are computed on the device only
and never appear here. Raw bodies stay in the caller's private directory; the projection keeps their sha256.
Pure functions: no network, environment or storage.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import math
import re
from xml.etree import ElementTree

from . import macro_lights_v1 as ml
from . import growth_inflation_v0 as macro_v0
from . import raw_axes_v0 as macro_raw

CURVE_FORMAT = "TREASURY_DAILY_PAR_YIELD_XML"
CONFIG = {k: ml.CONFIG[k] for k in ("id", "version", "status", "marker", "decided_on", "source_section")}
META = {
    "employment": {"agency": "BLS", "source_series_id": "BLS:LNS14000000",
                   "source": "BLS LNS14000000 · unemployment rate, SA, monthly"},
    "inflation": {"agency": "BLS", "source_series_id": "BLS:CUUR0000SA0",
                  "source": "BLS CUUR0000SA0 · CPI-U all items, NSA, monthly"},
    "curve": {"agency": "TREASURY", "source_series_id": "TREASURY:daily_treasury_yield_curve:BC_10YEAR-BC_3MONTH",
              "source": "U.S. Treasury daily par yield curve · 10 Yr − 3 Mo"},
}
ROW_KEYS = ("state", "lit", "reason", "as_of", "agency", "source_series_id", "source", "inputs", "values")
VALUE_KEYS = {name: tuple(k for k in ml.FIELDS[name] if k not in ("lit", "reason")) for name in ml.PUBLIC_LIGHTS}
AS_OF_KEY = {"employment": "period", "inflation": "period", "curve": "date"}
MISSING_REASONS = tuple(r for r in ml.REASONS if r not in ("LIT", "NOT_LIT", "WORKER_ALLOWLIST_REQUIRED", "DEVICE_NOT_LOADED"))
DEVICE_LIGHTS = list(ml.DEVICE_LIGHTS)
MAX_CURVE_BODIES = 2

_ATOM = "{http://www.w3.org/2005/Atom}"
_DATA = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
_META = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", re.ASCII)
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?", re.ASCII)


class CurveUnavailable(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason if reason in ml.REASONS else "SCHEMA_MISMATCH"


def _field(props, name):
    found = [e for e in props if e.tag.rsplit("}", 1)[-1] == name]
    if not found:
        return None
    if len(found) != 1 or found[0].tag != _DATA + name:
        raise CurveUnavailable("SCHEMA_MISMATCH")
    element = found[0]
    null = element.get(_META + "null")
    if null not in (None, "true", "false"):
        raise CurveUnavailable("SCHEMA_MISMATCH")
    text = (element.text or "").strip()
    if null == "true" or text == "":
        return None
    if _NUMBER.fullmatch(text) is None:
        raise CurveUnavailable("SCHEMA_MISMATCH")
    value = float(Decimal(text))
    if not math.isfinite(value):
        raise CurveUnavailable("SCHEMA_MISMATCH")
    return value


def parse_treasury_curve(body: bytes) -> dict:
    """{date: (3-month %, 10-year %)} from one Treasury daily par yield curve XML (Atom) body; None = not published."""
    probe = body.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise CurveUnavailable("SCHEMA_MISMATCH")
    try:
        root = ElementTree.fromstring(body)
    except (ElementTree.ParseError, ValueError, LookupError):
        raise CurveUnavailable("SCHEMA_MISMATCH") from None
    if root.tag != _ATOM + "feed":
        raise CurveUnavailable("SCHEMA_MISMATCH")
    rows = {}
    for entry in root.findall(_ATOM + "entry"):
        properties = entry.findall(_ATOM + "content/" + _META + "properties")
        if len(properties) != 1:
            raise CurveUnavailable("SCHEMA_MISMATCH")
        props = properties[0]
        dates = [e for e in props if e.tag.rsplit("}", 1)[-1] == "NEW_DATE"]
        if len(dates) != 1 or dates[0].tag != _DATA + "NEW_DATE":
            raise CurveUnavailable("SCHEMA_MISMATCH")
        match = _DATE.fullmatch((dates[0].text or "").strip())
        if match is None:
            raise CurveUnavailable("SCHEMA_MISMATCH")
        day = match.group(1)
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            raise CurveUnavailable("SCHEMA_MISMATCH") from None
        value = (_field(props, "BC_3MONTH"), _field(props, "BC_10YEAR"))
        if day in rows and rows[day] != value:
            raise CurveUnavailable("CONFLICTING_DUPLICATE")
        rows[day] = value
    return rows  # An empty feed (early January) contributes no rows; the merged set must not be empty.


def _float_series(rows: dict) -> list:
    return [[period, float(value)] for period, value in sorted(rows.items())]


def _fresh(acquired, as_of, stale_after):
    return "STALE" if as_of - acquired > stale_after else "LIVE"


def _inputs(captures):
    return [{"sha256": hashlib.sha256(body).hexdigest(), "acquired_at": acquired.isoformat()} for body, acquired in captures]


def _public_row(name, light, captures, as_of, stale_after):
    values = {k: light.get(k) for k in VALUE_KEYS[name]}
    lit = light["lit"]
    state = "NOT_AVAILABLE" if lit is None or not captures else _fresh(min(a for _, a in captures), as_of, stale_after)
    return {"state": state, "lit": lit, "reason": light["reason"], "as_of": values[AS_OF_KEY[name]],
            **META[name], "inputs": _inputs(captures), "values": values}


def unavailable_row(name, reason, captures=()):
    return _public_row(name, ml.unavailable(name, reason), list(captures), None, None)


def build_block(*, bls=None, bls_reason="SOURCE_NOT_COLLECTED", curves=(), curve_reason="SOURCE_NOT_COLLECTED",
                as_of: datetime, stale_after: timedelta) -> dict:
    """bls: (body, acquired) of the batched BLS v1 response or None; curves: [(body, acquired), ...] Treasury XML."""
    lights = {}
    if bls is None:
        lights["employment"] = unavailable_row("employment", bls_reason)
        lights["inflation"] = unavailable_row("inflation", bls_reason)
    else:
        body, acquired = bls
        for name, reader, light in (("employment", macro_raw.labor_series, ml.employment_light),
                                    ("inflation", macro_v0.inflation_series, ml.inflation_light)):
            try:
                series = _float_series(reader(body, acquired))
            except (macro_raw.AxisUnavailable, macro_v0.AxisUnavailable) as error:
                reason = {"MISSING_SOURCE": "NO_DATA", "PROVIDER_ERROR": "SOURCE_NOT_AVAILABLE"}.get(error.reason, error.reason)
                reason = reason if reason in MISSING_REASONS else "SCHEMA_MISMATCH"
                lights[name] = unavailable_row(name, reason, [bls])
                continue
            except (InvalidOperation, ValueError, TypeError, KeyError, RecursionError):
                lights[name] = unavailable_row(name, "SCHEMA_MISMATCH", [bls])
                continue
            lights[name] = _public_row(name, light(series), [bls], as_of, stale_after)
    curves = list(curves)
    if not curves:
        lights["curve"] = unavailable_row("curve", curve_reason)
    else:
        merged = {}
        try:
            for body, _ in curves:
                for day, value in parse_treasury_curve(body).items():
                    if day in merged and merged[day] != value:
                        raise CurveUnavailable("CONFLICTING_DUPLICATE")
                    merged[day] = value
            if not merged:
                raise CurveUnavailable("NO_DATA")
        except CurveUnavailable as error:
            lights["curve"] = unavailable_row("curve", error.reason, curves)
        else:
            rows = [[day, *merged[day]] for day in sorted(merged)]
            lights["curve"] = _public_row("curve", ml.curve_light(rows), curves, as_of, stale_after)
    return {"config": dict(CONFIG), "lights": {name: lights[name] for name in ml.PUBLIC_LIGHTS},
            "device_lights": list(DEVICE_LIGHTS)}


def _need(condition):
    if not condition:
        raise ValueError("PUBLIC_SCREEN_INVALID")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _close(a, b):
    return abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))


def require_block(block, sources, cut, ttl_seconds, states, clock):
    """Validate the published block against the envelope sources; append each light state to `states`."""
    eps = ml.CONFIG["comparison_epsilon"]
    cfg = ml.CONFIG["lights"]
    _need(isinstance(block, dict) and set(block) == {"config", "lights", "device_lights"})
    _need(block["config"] == CONFIG and block["device_lights"] == DEVICE_LIGHTS)
    _need(isinstance(block["lights"], dict) and set(block["lights"]) == set(ml.PUBLIC_LIGHTS))
    for name in ml.PUBLIC_LIGHTS:
        row = block["lights"][name]
        _need(isinstance(row, dict) and set(row) == set(ROW_KEYS))
        _need(all(row[k] == v for k, v in META[name].items()))
        _need(row["state"] in ("LIVE", "STALE", "NOT_AVAILABLE") and row["lit"] in (True, False, None))
        _need(isinstance(row["inputs"], list) and len(row["inputs"]) <= (MAX_CURVE_BODIES if name == "curve" else 1))
        stamps = []
        for item in row["inputs"]:
            _need(isinstance(item, dict) and set(item) == {"sha256", "acquired_at"})
            _need(isinstance(item["sha256"], str) and re.fullmatch("[0-9a-f]{64}", item["sha256"]) is not None)
            stamp = clock(item["acquired_at"])
            _need(sources.get((row["agency"], item["sha256"])) == stamp)
            stamps.append(stamp)
        values = row["values"]
        _need(isinstance(values, dict) and set(values) == set(VALUE_KEYS[name]))
        _need(row["as_of"] == values[AS_OF_KEY[name]])
        if row["lit"] is None:
            _need(row["state"] == "NOT_AVAILABLE" and row["reason"] in MISSING_REASONS)
        else:
            _need(stamps and row["reason"] == ("LIT" if row["lit"] else "NOT_LIT"))
            expected = "STALE" if (cut - min(stamps)).total_seconds() > ttl_seconds else "LIVE"
            _need(row["state"] == expected)
            if name == "employment":
                v = values
                _need(isinstance(v["period"], str) and re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", v["period"]) is not None)
                _need(all(_number(v[k]) for k in ("avg3", "low12", "gap")) and type(v["low12_count"]) is int)
                _need(1 <= v["low12_count"] <= cfg["employment"]["low_window_months"] and _close(v["gap"], v["avg3"] - v["low12"]))
                _need(row["lit"] == (v["gap"] >= cfg["employment"]["gap_pp_gte"] - eps))
            elif name == "inflation":
                v = values
                _need(isinstance(v["period"], str) and re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", v["period"]) is not None)
                index = int(v["period"][:4]) * 12 + int(v["period"][5:7]) - 1 - cfg["inflation"]["base_lag_months"]
                _need(v["base_period"] == "%04d-%02d" % (index // 12, index % 12 + 1) and _number(v["yoy"]))
                _need(row["lit"] == (v["yoy"] > cfg["inflation"]["yoy_gt"] + eps))
            else:
                v = values
                _need(isinstance(v["date"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v["date"]) is not None)
                _need(all(_number(v[k]) for k in ("ten_year", "three_month", "spread")) and type(v["run_days"]) is int and v["run_days"] >= 0)
                _need(_close(v["spread"], v["ten_year"] - v["three_month"]))
                _need(row["lit"] == (v["run_days"] >= cfg["curve"]["min_run_days"]))
        for k, value in values.items():
            _need(value is None or isinstance(value, str) and len(value) <= 10 or _number(value))
        states.append(row["state"])
