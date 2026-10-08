"""Boundaries of the supplied-input, non-admitting display adapter."""
from copy import deepcopy
from decimal import Inexact, localcontext
from importlib import import_module

import pytest


def adapter():
    try:
        return import_module("investment_system.product.company_price_context_v1")
    except ModuleNotFoundError:
        pytest.fail("Company price-context display adapter is not implemented")


def price_input():
    common = dict(security_ref="sample:A", currency="USD", series_ref="sample:daily",
                  price_basis="split_adjusted", corporate_action_receipt="sample:actions",
                  coverage_ref="sample:coverage", window_contract_ref="sample:window",
                  quote_kind="PERIOD_HIGH", source_ref="sample:prices",
                  effective_at="2026-10-08T09:00:00Z", available_at="2026-10-08T09:00:01Z")
    return dict(decision_time="2026-10-08T10:00:00Z",
                current=dict(common, value="80", quote_kind="LAST_TRADE"),
                ath=dict(common, value="100", coverage_kind="LIFETIME"),
                high_52w=dict(common, value="90", coverage_kind="COMPLETE_WINDOW",
                              window_kind="52_WEEK", window_start="2025-10-08T09:00:00Z",
                              window_end="2026-10-08T09:00:00Z"))


def period_input(kind="QUARTERLY"):
    periods = [dict(period_id=f"p{i}", label=f"Period {i}", status="COMPLETE_FULL",
                    return_percent=value, start_at=f"202{i}-01-01T00:00:00Z",
                    end_at=f"202{i + 1}-01-01T00:00:00Z",
                    available_at=f"202{i + 1}-01-01T00:00:01Z", source_ref="sample:periods")
               for i, value in enumerate(["10", "0", "-5", "2"])]
    periods += [dict(period_id="partial", label="Current", status="QTD" if kind == "QUARTERLY" else "YTD",
                     return_percent="3", start_at="2026-10-01T00:00:00Z",
                     end_at="2026-10-08T09:00:00Z", available_at="2026-10-08T09:00:01Z",
                     source_ref="sample:partial")]
    return dict(period_kind=kind, decision_time="2026-10-08T10:00:00Z",
                calendar_ref="sample:calendar", complete_full_period_roster_ref="sample:roster",
                complete_full_period_roster=[f"p{i}" for i in range(4)], periods=periods,
                security_ref="sample:A", currency="USD", series_ref="sample:daily",
                price_basis="split_adjusted", corporate_action_receipt="sample:actions",
                coverage_ref="sample:coverage", available_at="2026-10-08T09:00:02Z",
                source_ref="sample:periods")


def assert_closed(result, value_key):
    assert result["status"] == "NOT_AVAILABLE"
    assert result["reason_codes"]
    assert result["qgv_raw_score_input"] is False
    assert result["source_admission"] is False
    if value_key == "values":
        assert all(v is None for v in result["values"].values())
    else:
        assert result["positive_count"] is None
        assert result["completed_count"] is None
        assert result["positive_rate_percent"] is None
        assert result["bars"] == []


def test_price_projection_does_not_change_scores_or_admit_source():
    payload = price_input()
    original = deepcopy(payload)
    result = adapter().price_position(payload)
    assert result["status"] == "AVAILABLE"
    assert result["values"]["percent_from_ath"] == "-20"
    assert result["values"]["percent_from_high_52w"].startswith("-11.111")
    assert result["qgv_raw_score_input"] is False
    assert result["source_admission"] is False
    assert payload == original


@pytest.mark.parametrize("binding", ["security_ref", "currency", "series_ref", "price_basis", "corporate_action_receipt"])
def test_price_mixed_bindings_clear_entire_projection(binding):
    payload = price_input()
    payload["ath"][binding] = "different"
    assert_closed(adapter().price_position(payload), "values")


@pytest.mark.parametrize("field", ["source_ref", "coverage_ref", "window_contract_ref", "quote_kind", "effective_at", "available_at"])
def test_price_missing_operand_authority(field):
    payload = price_input()
    del payload["ath"][field]
    assert_closed(adapter().price_position(payload), "values")


@pytest.mark.parametrize("operand,value", [("ath", "0"), ("current", "-1"), ("ath", "NaN"),
                                          ("ath", "Infinity"), ("current", True), ("current", 80.0),
                                          ("ath", "75"), ("high_52w", "101")])
def test_price_invalid_numbers_and_inconsistent_extrema(operand, value):
    payload = price_input()
    payload[operand]["value"] = value
    assert_closed(adapter().price_position(payload), "values")


@pytest.mark.parametrize("mutation", ["future_available", "effective_after_available", "naive_time",
                                      "no_lifetime", "no_window", "future_window", "window_excludes_current"])
def test_price_coverage_and_point_in_time(mutation):
    payload = price_input()
    if mutation == "future_available": payload["ath"]["available_at"] = "2026-10-09T00:00:00Z"
    if mutation == "effective_after_available": payload["ath"]["effective_at"] = "2026-10-08T09:30:00Z"
    if mutation == "naive_time": payload["decision_time"] = "2026-10-08T10:00:00"
    if mutation == "no_lifetime": payload["ath"]["coverage_kind"] = "SAMPLED"
    if mutation == "no_window": del payload["high_52w"]["window_start"]
    if mutation == "future_window": payload["high_52w"]["window_end"] = "2026-10-09T00:00:00Z"
    if mutation == "window_excludes_current": payload["high_52w"]["window_end"] = "2026-10-07T00:00:00Z"
    assert_closed(adapter().price_position(payload), "values")


@pytest.mark.parametrize("kind", ["QUARTERLY", "ANNUAL"])
def test_flat_in_denominator_and_current_partial_excluded(kind):
    payload = period_input(kind)
    original = deepcopy(payload)
    result = adapter().period_summary(payload)
    assert result["status"] == "AVAILABLE"
    assert (result["positive_count"], result["completed_count"], result["positive_rate_percent"]) == (2, 4, "50")
    assert result["bars"][1]["direction"] == "Flat"
    assert result["bars"][-1]["historical_denominator"] is False
    assert len(result["current_partial_period"]) == 1
    assert "negative_count" not in result
    assert result["qgv_raw_score_input"] is False and result["source_admission"] is False
    assert payload == original


def test_partial_ipo_is_separate_from_full_period_statistics():
    payload = period_input()
    payload["periods"][-1]["status"] = "PARTIAL_IPO"
    result = adapter().period_summary(payload)
    assert result["completed_count"] == 4
    assert result["bars"][-1]["historical_denominator"] is False


@pytest.mark.parametrize("mutation", ["unknown_return", "missing_return", "missing_row", "extra_complete",
                                      "duplicate_row", "duplicate_roster", "unknown_status", "empty_roster",
                                      "future_available", "future_complete", "wrong_binding", "wrong_partial",
                                      "overlap", "nonfinite"])
def test_period_roster_missing_data_and_point_in_time_are_fail_closed(mutation):
    payload = period_input()
    if mutation == "unknown_return": payload["periods"][0]["return_percent"] = None
    if mutation == "missing_return": del payload["periods"][0]["return_percent"]
    if mutation == "missing_row": payload["periods"].pop(0)
    if mutation == "extra_complete": payload["periods"][-1]["status"] = "COMPLETE_FULL"
    if mutation == "duplicate_row": payload["periods"].append(deepcopy(payload["periods"][0]))
    if mutation == "duplicate_roster": payload["complete_full_period_roster"].append("p0")
    if mutation == "unknown_status": payload["periods"][0]["status"] = "UNKNOWN"
    if mutation == "empty_roster": payload["complete_full_period_roster"] = []; payload["periods"] = []
    if mutation == "future_available": payload["available_at"] = "2026-10-09T00:00:00Z"
    if mutation == "future_complete": payload["periods"][0]["end_at"] = "2027-01-01T00:00:00Z"
    if mutation == "wrong_binding": payload["periods"][0]["security_ref"] = "sample:B"
    if mutation == "wrong_partial": payload["periods"][-1]["status"] = "YTD"
    if mutation == "overlap": payload["periods"][1]["start_at"] = payload["periods"][0]["start_at"]
    if mutation == "nonfinite": payload["periods"][0]["return_percent"] = "NaN"
    assert_closed(adapter().period_summary(payload), "bars")


@pytest.mark.parametrize("payload", [None, [], "unknown", {}])
def test_malformed_envelope_is_unavailable_not_an_exception(payload):
    assert_closed(adapter().price_position(payload), "values")
    assert_closed(adapter().period_summary(payload), "bars")


def test_display_division_is_independent_of_callers_decimal_traps():
    periods = period_input("ANNUAL")
    periods["complete_full_period_roster"].pop()
    periods["periods"].pop(3)
    with localcontext() as context:
        context.traps[Inexact] = True
        context.prec = 2
        assert adapter().price_position(price_input())["status"] == "AVAILABLE"
        assert adapter().period_summary(periods)["positive_rate_percent"].startswith("33.333")


@pytest.mark.parametrize("value", ["1e1000000", "1e-1000000", "9" * 129])
def test_unbounded_decimal_serialization_is_rejected(value):
    prices = price_input()
    prices["current"]["value"] = value
    assert_closed(adapter().price_position(prices), "values")
    periods = period_input()
    periods["periods"][0]["return_percent"] = value
    assert_closed(adapter().period_summary(periods), "bars")
