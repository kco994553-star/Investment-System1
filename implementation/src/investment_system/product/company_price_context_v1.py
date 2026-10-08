"""Inactive Historical Price Context v1 supplied-input display projection.

References and coverage declarations are required, but this module does not
authenticate them, admit sources, select prices/calendars, or enable routes.
The caller must obtain source/contract acceptance separately. All numbers are
context displays, never QGV raw-score inputs. No episode or drawdown bands run.
"""
from datetime import datetime
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

_BINDINGS = ("security_ref", "currency", "series_ref", "price_basis", "corporate_action_receipt")
_BASES = {"raw", "split_adjusted", "total_return_adjusted"}
_PRICE_FIELDS = ("current_price", "historical_ath", "percent_from_ath", "high_52w", "percent_from_high_52w")
# Parser/serialization resource budget, not an economic or inclusion threshold.
# Checked before fixed-point formatting so a compact exponent cannot expand
# into an unbounded JSON field. Ordinary supplied financial displays fit here.
_DECIMAL_SERIALIZATION_BUDGET = 128


class _Unavailable(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise _Unavailable(reason)


def _ref(record, key):
    value = record.get(key)
    _require(isinstance(value, str) and bool(value.strip()), "MISSING_" + key.upper())
    return value


def _time(record, key):
    value = _ref(record, key)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _Unavailable("INVALID_" + key.upper()) from None
    _require(result.tzinfo is not None and result.utcoffset() is not None, "NAIVE_" + key.upper())
    return result


def _number(value):
    _require(not isinstance(value, bool) and isinstance(value, (str, int, Decimal)), "INVALID_DECIMAL")
    if isinstance(value, str):
        _require(len(value) <= _DECIMAL_SERIALIZATION_BUDGET, "DECIMAL_SERIALIZATION_BUDGET")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError):
        raise _Unavailable("INVALID_DECIMAL") from None
    _require(result.is_finite(), "NONFINITE_DECIMAL")
    parts = result.as_tuple()
    _require(len(parts.digits) + max(parts.exponent, 0) <= _DECIMAL_SERIALIZATION_BUDGET
             and parts.exponent >= -_DECIMAL_SERIALIZATION_BUDGET, "DECIMAL_SERIALIZATION_BUDGET")
    return result


def _display(value):
    if value == 0:
        return "0"
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _bindings(record):
    values = {key: _ref(record, key) for key in _BINDINGS}
    _require(values["price_basis"] in _BASES, "UNKNOWN_PRICE_BASIS")
    return values


def _envelope(payload):
    _require(isinstance(payload, dict), "INVALID_ENVELOPE")
    return _time(payload, "decision_time")


def _flags():
    return {"qgv_raw_score_input": False, "source_admission": False, "runtime_enabled": False}


def price_position(payload: dict) -> dict:
    """Project one explicit price snapshot; any invalid operand clears all values.

    ATH lifetime and 52-week window declarations are supplied by the caller.
    No 252-session fallback or implicit series/adjustment convention is used.
    Decimal division uses 28 significant digits for serialization; presentation
    rounding belongs to the UI and is not a policy or scoring threshold.
    """
    result = dict(status="NOT_AVAILABLE", reason_codes=[],
                  values={key: None for key in _PRICE_FIELDS}, evidence={}, **_flags())
    try:
        decision = _envelope(payload)
        records, values, bindings, times = {}, {}, {}, {}
        for key in ("current", "ath", "high_52w"):
            record = payload.get(key)
            _require(isinstance(record, dict), "MISSING_" + key.upper())
            records[key] = record
            bindings[key] = _bindings(record)
            for field in ("coverage_ref", "window_contract_ref", "quote_kind", "source_ref"):
                _ref(record, field)
            effective, available = _time(record, "effective_at"), _time(record, "available_at")
            _require(effective <= available <= decision, "PRICE_POINT_IN_TIME_INVALID")
            times[key] = effective
            values[key] = _number(record.get("value"))
            _require(values[key] >= 0 if key == "current" else values[key] > 0, "INVALID_PRICE")
        _require(bindings["current"] == bindings["ath"] == bindings["high_52w"], "MIXED_PRICE_BINDINGS")
        _require(times["current"] == times["ath"] == times["high_52w"], "MIXED_PRICE_SNAPSHOT")
        _require(records["ath"].get("coverage_kind") == "LIFETIME", "ATH_LIFETIME_UNAVAILABLE")
        window = records["high_52w"]
        _require(window.get("coverage_kind") == "COMPLETE_WINDOW" and window.get("window_kind") == "52_WEEK",
                 "HIGH_52W_COVERAGE_UNAVAILABLE")
        start, end = _time(window, "window_start"), _time(window, "window_end")
        _require(start < end <= times["high_52w"] and start <= times["current"] <= end,
                 "HIGH_52W_WINDOW_INVALID")
        _require(values["current"] <= values["high_52w"] <= values["ath"], "INCONSISTENT_PRICE_EXTREMA")
        with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
            percent_ath = (values["current"] / values["ath"] - 1) * 100
            percent_52w = (values["current"] / values["high_52w"] - 1) * 100
        result.update(status="AVAILABLE", values=dict(
            current_price=_display(values["current"]), historical_ath=_display(values["ath"]),
            percent_from_ath=_display(percent_ath), high_52w=_display(values["high_52w"]),
            percent_from_high_52w=_display(percent_52w)),
            evidence=dict(decision_time=payload["decision_time"], bindings=bindings["current"],
                          operands={key: {field: value for field, value in record.items() if field != "value"}
                                    for key, record in records.items()}, authority_verification="NOT_PERFORMED"))
    except _Unavailable as error:
        result["reason_codes"] = [str(error)]
    return result


def period_summary(payload: dict) -> dict:
    """Project explicit completed-period roster; missing rows never shrink it.

    Calendar/full-period status is supplied, not inferred from inclusion rules.
    A completed return of zero counts only in the denominator. QTD/YTD and
    partial IPO bars are displayed separately without a historical vote.
    """
    result = dict(status="NOT_AVAILABLE", reason_codes=[], period_kind=None,
                  positive_count=None, completed_count=None, positive_rate_percent=None,
                  bars=[], current_partial_period=[], evidence={}, **_flags())
    try:
        decision = _envelope(payload)
        kind = payload.get("period_kind")
        _require(kind in ("QUARTERLY", "ANNUAL"), "UNKNOWN_PERIOD_KIND")
        binding = _bindings(payload)
        for field in ("calendar_ref", "complete_full_period_roster_ref", "source_ref", "coverage_ref"):
            _ref(payload, field)
        available = _time(payload, "available_at")
        _require(available <= decision, "PERIOD_POINT_IN_TIME_INVALID")
        roster, rows = payload.get("complete_full_period_roster"), payload.get("periods")
        _require(isinstance(roster, list) and isinstance(rows, list), "MISSING_PERIOD_ROSTER")
        _require(all(isinstance(item, str) and item.strip() for item in roster), "INVALID_PERIOD_ROSTER")
        _require(len(roster) == len(set(roster)), "DUPLICATE_PERIOD_ROSTER")
        _require(bool(roster), "EMPTY_COMPLETED_DENOMINATOR")
        bars, partials, completed, ranges, seen = [], [], [], [], set()
        for row in rows:
            _require(isinstance(row, dict), "INVALID_PERIOD_ROW")
            identity = _ref(row, "period_id")
            _require(identity not in seen, "DUPLICATE_PERIOD_ROW")
            seen.add(identity)
            _ref(row, "label")
            source = _ref(row, "source_ref")
            for field, value in binding.items():
                _require(field not in row or row[field] == value, "MIXED_PERIOD_BINDINGS")
            status = row.get("status")
            _require(status in ("COMPLETE_FULL", "PARTIAL_IPO", "QTD" if kind == "QUARTERLY" else "YTD"),
                     "UNKNOWN_OR_MISMATCHED_PERIOD_STATUS")
            start, end, row_available = _time(row, "start_at"), _time(row, "end_at"), _time(row, "available_at")
            _require(start < end <= row_available <= available <= decision, "PERIOD_POINT_IN_TIME_INVALID")
            value = _number(row.get("return_percent"))
            full = status == "COMPLETE_FULL"
            bar = dict(period_id=identity, label=row["label"], return_percent=_display(value),
                       direction="Positive" if value > 0 else "Negative" if value < 0 else "Flat",
                       historical_denominator=full, display_kind=status, source_ref=source)
            bars.append(bar)
            if full:
                completed.append((identity, value))
                ranges.append((start, end))
            else:
                partials.append(bar.copy())
        _require(set(identity for identity, _ in completed) == set(roster), "COMPLETED_ROSTER_MISMATCH")
        ordered_ranges = sorted(ranges)
        _require(all(left[1] <= right[0] for left, right in zip(ordered_ranges, ordered_ranges[1:])),
                 "OVERLAPPING_COMPLETED_PERIODS")
        positive = sum(value > 0 for _, value in completed)
        with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN)):
            rate = Decimal(positive) / Decimal(len(roster)) * 100
        result.update(status="AVAILABLE", period_kind=kind, positive_count=positive,
                      completed_count=len(roster), positive_rate_percent=_display(rate),
                      bars=bars, current_partial_period=partials,
                      evidence={field: payload[field] for field in (
                          *_BINDINGS, "calendar_ref", "complete_full_period_roster_ref", "coverage_ref",
                          "source_ref", "decision_time", "available_at")})
        result["evidence"]["authority_verification"] = "NOT_PERFORMED"
    except _Unavailable as error:
        result["reason_codes"] = [str(error)]
    return result
