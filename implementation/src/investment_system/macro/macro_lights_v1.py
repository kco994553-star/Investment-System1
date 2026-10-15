"""Macro state v1: five warning lights and the NORMAL / WARNING / CRISIS state (PLAYBOOK_V1 13-5).

v1 · UNCALIBRATED until the 2000 / 2008 / 2020 / 2022 replay is validated. Every number lives in
macro_lights_v1.json. Pure functions only: no network, environment, storage or clock.
JS mirror: product/web_assets/macro-lights.js (vectors: tests/fixtures/macro_lights_v1_vectors.json).

Lights (each returns {lit: True/False/None, reason, ...value fields}; None = no data, excluded from the state):
  employment  BLS LNS14000000 monthly %: mean of the latest 3 months − lowest month of the 12 months ending at the
              latest month (months the source did not publish are skipped, never filled) ≥ 0.5 %p.
  inflation   BLS CUUR0000SA0 NSA index: latest month ÷ same month a year earlier − 1 > 5 %.
  curve       Treasury daily par yield curve: 10 Y − 3 M < 0 on at least 20 consecutive published days ending at the
              latest published day.
  market      SPY daily close (device only): latest ÷ highest close of the last 52 weeks − 1 ≤ −20 %, OR the 20-session
              realized volatility is in the top 5 % of its last-3-year distribution.
  credit      HYG ÷ IEF daily close ratio (device only, estimate): change over 20 joint sessions ≤ −5 %.
State: CRISIS (≥ 3 lit, or market + credit, or CPI YoY > 8 % with at least one light other than inflation also lit),
else WARNING (2 lit, or CPI YoY > 8 % with no other light lit, or CPI YoY > 5 % and growth < 0), else NORMAL.
(The CPI > 8 % split is decision M-RULE C of 2026-10-15, PLAYBOOK_V1 18, recorded as a HYPOTHESIS under validation;
config: revisions, state.crisis_inflation_other_lit_min.) Fewer than 3 available lights → low confidence. Macro never drives sell decisions.

Arithmetic uses only + − × ÷ and sqrt in a fixed order so that the JS mirror returns bit-identical numbers.
Missing values are never filled and nothing defaults to 0.
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import math
from pathlib import Path
import re

CONFIG = json.loads((Path(__file__).with_name("macro_lights_v1.json")).read_text(encoding="utf-8"))
LIGHTS = ("employment", "inflation", "curve", "market", "credit")
PUBLIC_LIGHTS = ("employment", "inflation", "curve")
DEVICE_LIGHTS = ("market", "credit")
FIELDS = {
    "employment": ("lit", "reason", "period", "avg3", "low12", "low12_count", "gap"),
    "inflation": ("lit", "reason", "period", "base_period", "yoy"),
    "curve": ("lit", "reason", "date", "ten_year", "three_month", "spread", "run_days"),
    "market": ("lit", "reason", "date", "last_close", "high_52w", "drawdown", "drawdown_lit", "rv20", "rv_count",
               "rv_above_count", "rv_lit"),
    "credit": ("lit", "reason", "date", "base_date", "ratio_change", "estimate"),
}
REASONS = ("LIT", "NOT_LIT", "NO_DATA", "INVALID_INPUT", "CONFLICTING_DUPLICATE", "WINDOW_INCOMPLETE",
           "INSUFFICIENT_HISTORY", "BASE_MONTH_MISSING", "VALUE_MISSING", "WORKER_ALLOWLIST_REQUIRED",
           "SOURCE_NOT_COLLECTED", "SOURCE_NOT_AVAILABLE", "SCHEMA_MISMATCH", "SYNTHETIC_INPUT_NOT_PUBLIC",
           "SOURCE_AFTER_AS_OF", "DEVICE_NOT_LOADED")
STATES = ("NORMAL", "WARNING", "CRISIS")
STATE_REASONS = ("LIT_COUNT_GE_3", "MARKET_AND_CREDIT_LIT", "INFLATION_GT_8PCT_WITH_OTHER_LIT", "LIT_COUNT_EQ_2",
                 "INFLATION_GT_8PCT_ALONE", "INFLATION_GT_5PCT_AND_GROWTH_LT_0", "LIT_COUNT_LE_1", "AVAILABLE_LT_3")
_MONTH = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])", re.ASCII)
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def _num(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _eps(config) -> float:
    return config["comparison_epsilon"]


def _valid_day(text: str) -> bool:
    if _DAY.fullmatch(text) is None:
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _key_ok(key, kind) -> bool:
    return isinstance(key, str) and (_MONTH.fullmatch(key) is not None if kind == "month" else _valid_day(key))


def _value(value, sign):
    if not _num(value):
        return None
    if sign == "positive" and not value > 0:
        return None
    if sign == "nonneg" and not value >= 0:
        return None
    return float(value)


def _points(series, kind, sign, width=2):
    """[[key, value(s)], ...] → (sorted [(key, values...)], reason). Invalid numbers are missing, never 0."""
    if not isinstance(series, (list, tuple)) or not series:
        return None, "NO_DATA"
    seen = {}
    for item in series:
        if not isinstance(item, (list, tuple)) or len(item) != width or not _key_ok(item[0], kind):
            return None, "INVALID_INPUT"
        values = tuple(_value(v, sign) for v in item[1:])
        if item[0] in seen:
            if seen[item[0]] != values:
                return None, "CONFLICTING_DUPLICATE"
            continue
        seen[item[0]] = values
    if not any(v is not None for values in seen.values() for v in values):
        return None, "NO_DATA"
    return [(k,) + seen[k] for k in sorted(seen)], None


def _month_index(period: str) -> int:
    return int(period[:4]) * 12 + int(period[5:7]) - 1


def _month(index: int) -> str:
    return "%04d-%02d" % (index // 12, index % 12 + 1)


def _days_back(day: str, days: int) -> str:
    return (date.fromisoformat(day) - timedelta(days=days)).isoformat()


def _years_back(day: str, years: int) -> str:
    y, m, d = int(day[:4]) - years, int(day[5:7]), int(day[8:10])
    if m == 2 and d == 29:
        d = 28
    return "%04d-%02d-%02d" % (y, m, d)


def unavailable(name: str, reason: str, **values) -> dict:
    row = dict.fromkeys(FIELDS[name])
    row.update(values, lit=None, reason=reason)
    if name == "credit":
        row["estimate"] = True
    return row


def _row(name, lit, **values):
    row = dict.fromkeys(FIELDS[name])
    row.update(values, lit=lit, reason="LIT" if lit else "NOT_LIT")
    return row


def employment_light(series, config=CONFIG) -> dict:
    """series: [["YYYY-MM", unemployment rate % or None], ...]."""
    cfg = config["lights"]["employment"]
    points, reason = _points(series, "month", "nonneg")
    if reason:
        return unavailable("employment", reason)
    values = {k: v for k, v in points}
    latest = max(k for k, v in points if v is not None)
    last = _month_index(latest)
    window = [_month(last - i) for i in range(cfg["avg_months"] - 1, -1, -1)]
    if any(values.get(k) is None for k in window):
        return unavailable("employment", "WINDOW_INCOMPLETE", period=latest)
    total = 0.0
    for k in window:
        total += values[k]
    avg = total / cfg["avg_months"]
    end = last if cfg["low_window_includes_latest"] else last - 1
    start = end - cfg["low_window_months"] + 1
    if _month_index(points[0][0]) > start:
        return unavailable("employment", "INSUFFICIENT_HISTORY", period=latest, avg3=avg)
    low_values = [values[_month(i)] for i in range(start, end + 1) if values.get(_month(i)) is not None]
    if not low_values:
        return unavailable("employment", "WINDOW_INCOMPLETE", period=latest, avg3=avg)
    low = min(low_values)
    gap = avg - low
    return _row("employment", gap >= cfg["gap_pp_gte"] - _eps(config), period=latest, avg3=avg, low12=low,
                low12_count=len(low_values), gap=gap)


def inflation_light(series, config=CONFIG) -> dict:
    """series: [["YYYY-MM", CPI-U NSA index or None], ...]."""
    cfg = config["lights"]["inflation"]
    points, reason = _points(series, "month", "positive")
    if reason:
        return unavailable("inflation", reason)
    values = {k: v for k, v in points}
    latest = max(k for k, v in points if v is not None)
    base = _month(_month_index(latest) - cfg["base_lag_months"])
    if values.get(base) is None:
        return unavailable("inflation", "BASE_MONTH_MISSING", period=latest, base_period=base)
    yoy = values[latest] / values[base] - 1
    return _row("inflation", yoy > cfg["yoy_gt"] + _eps(config), period=latest, base_period=base, yoy=yoy)


def curve_light(rows, config=CONFIG) -> dict:
    """rows: [["YYYY-MM-DD", 3-month % or None, 10-year % or None], ...] (Treasury daily par yield curve)."""
    cfg = config["lights"]["curve"]
    points, reason = _points(rows, "day", "any", width=3)
    if reason:
        return unavailable("curve", reason)
    day, three, ten = points[-1]
    if three is None or ten is None:
        return unavailable("curve", "VALUE_MISSING", date=day, ten_year=ten, three_month=three)
    spread = ten - three
    run, need, limit = 0, cfg["min_run_days"], cfg["spread_lt"] - _eps(config)
    exhausted = True
    for _, m3, y10 in reversed(points):
        if m3 is None or y10 is None:
            if run >= need:
                exhausted = False
                break
            return unavailable("curve", "VALUE_MISSING", date=day, ten_year=ten, three_month=three, spread=spread,
                               run_days=run)
        if y10 - m3 < limit:
            run += 1
        else:
            exhausted = False
            break
    if exhausted and run < need:
        return unavailable("curve", "INSUFFICIENT_HISTORY", date=day, ten_year=ten, three_month=three, spread=spread,
                           run_days=run)
    return _row("curve", run >= need, date=day, ten_year=ten, three_month=three, spread=spread, run_days=run)


def _rv(closes, index, n, annual):
    """Sample standard deviation of the n simple returns ending at `index`, × sqrt(annual); None on any gap."""
    if index < n:
        return None
    window = closes[index - n:index + 1]
    if any(c is None for c in window):
        return None
    returns = [window[i] / window[i - 1] - 1 for i in range(1, n + 1)]
    total = 0.0
    for r in returns:
        total += r
    mean = total / n
    squares = 0.0
    for r in returns:
        squares += (r - mean) * (r - mean)
    return math.sqrt(squares / (n - 1) * annual)


def market_light(series, config=CONFIG) -> dict:
    """series: [["YYYY-MM-DD", SPY close or None], ...] (device RAM only)."""
    cfg = config["lights"]["market"]
    points, reason = _points(series, "day", "positive")
    if reason:
        return unavailable("market", reason)
    days = [p[0] for p in points]
    closes = [p[1] for p in points]
    last = max(i for i, c in enumerate(closes) if c is not None)
    day, close = days[last], closes[last]
    out = {"date": day, "last_close": close}
    reasons = []
    start = _days_back(day, cfg["high_window_days"])
    if days[0] > start:
        dd_lit = None
        reasons.append("INSUFFICIENT_HISTORY")
    else:
        high = max(c for d, c in zip(days, closes) if c is not None and start <= d <= day)
        drawdown = close / high - 1
        dd_lit = drawdown <= cfg["drawdown_lte"] + _eps(config)
        out.update(high_52w=high, drawdown=drawdown)
    out["drawdown_lit"] = dd_lit
    n, annual = cfg["rv_window_returns"], cfg["rv_annualization_days"]
    current = _rv(closes, last, n, annual)
    cutoff = _years_back(day, cfg["rv_history_years"])
    if current is None:
        rv_lit = None
        reasons.append("WINDOW_INCOMPLETE")
    elif days[0] > cutoff:
        rv_lit = None
        out["rv20"] = current
        reasons.append("INSUFFICIENT_HISTORY")
    else:
        dist = [v for v in (_rv(closes, i, n, annual) for i in range(last + 1) if cutoff <= days[i]) if v is not None]
        above = 0
        for v in dist:
            if v > current:
                above += 1
        rv_lit = above < cfg["rv_top_share"] * len(dist)
        out.update(rv20=current, rv_count=len(dist), rv_above_count=above)
    out["rv_lit"] = rv_lit
    if dd_lit is True or rv_lit is True:
        return _row("market", True, **out)
    if dd_lit is False and rv_lit is False:
        return _row("market", False, **out)
    return unavailable("market", reasons[0], **out)


def credit_light(numerator, denominator, config=CONFIG) -> dict:
    """numerator HYG, denominator IEF: [["YYYY-MM-DD", close or None], ...] (device RAM only, estimate)."""
    cfg = config["lights"]["credit"]
    hyg, reason = _points(numerator, "day", "positive")
    if reason:
        return unavailable("credit", reason)
    ief, reason = _points(denominator, "day", "positive")
    if reason:
        return unavailable("credit", reason)
    h, i = dict(hyg), dict(ief)
    joint = [d for d in sorted(h) if h[d] is not None and i.get(d) is not None]
    n = cfg["window_sessions"]
    if len(joint) < n + 1:
        return unavailable("credit", "INSUFFICIENT_HISTORY", date=joint[-1] if joint else None)
    t, b = joint[-1], joint[-1 - n]
    change = (h[t] / i[t]) / (h[b] / i[b]) - 1
    return _row("credit", change <= cfg["change_lte"] + _eps(config), date=t, base_date=b, ratio_change=change,
                estimate=True)


def _lit(value):
    if isinstance(value, dict):
        value = value.get("lit")
    return value if value is True or value is False else None


def macro_state(lights, cpi_yoy=None, growth=None, config=CONFIG) -> dict:
    """lights: {name: light row or True/False/None}; missing names are no-data. cpi_yoy / growth: ratios or None."""
    cfg, eps = config["state"], _eps(config)
    lights = lights if isinstance(lights, dict) else {}
    lit = {name: _lit(lights.get(name)) for name in LIGHTS}
    available = [name for name in LIGHTS if lit[name] is not None]
    count = sum(1 for name in available if lit[name])
    others = sum(1 for name in available if name != "inflation" and lit[name])
    cpi = cpi_yoy if _num(cpi_yoy) else None
    grow = growth if _num(growth) else None
    crisis = []
    if count >= cfg["crisis_lit_count"]:
        crisis.append("LIT_COUNT_GE_3")
    if all(lit[name] is True for name in cfg["crisis_pair"]):
        crisis.append("MARKET_AND_CREDIT_LIT")
    hot = cpi is not None and cpi > cfg["crisis_inflation_gt"] + eps
    # M-RULE C (2026-10-15, hypothesis under validation): CPI > 8 % is a crisis only together with another light; alone a warning.
    if hot and others >= cfg["crisis_inflation_other_lit_min"]:
        crisis.append("INFLATION_GT_8PCT_WITH_OTHER_LIT")
    warning = []
    if count == cfg["warning_lit_count"]:
        warning.append("LIT_COUNT_EQ_2")
    if hot and others < cfg["crisis_inflation_other_lit_min"]:
        warning.append("INFLATION_GT_8PCT_ALONE")
    if cpi is not None and grow is not None and cpi > cfg["warning_inflation_gt"] + eps and grow < cfg["warning_growth_lt"] - eps:
        warning.append("INFLATION_GT_5PCT_AND_GROWTH_LT_0")
    state, reasons = ("CRISIS", crisis) if crisis else ("WARNING", warning) if warning else ("NORMAL", ["LIT_COUNT_LE_1"])
    low = len(available) < cfg["low_confidence_available_lt"]
    return {"state": state, "lit_count": count, "available_count": len(available), "low_confidence": low,
            "reasons": reasons + (["AVAILABLE_LT_3"] if low else [])}
