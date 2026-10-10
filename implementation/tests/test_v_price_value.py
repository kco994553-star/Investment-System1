"""RAM-only V calculations: approved v1 behavior and fail-closed boundaries."""

from dataclasses import FrozenInstanceError, asdict, fields, replace
from decimal import Decimal
import json
import logging
from pathlib import Path
import socket
import subprocess
from types import MappingProxyType, SimpleNamespace
import urllib.request

import pytest

from investment_system.contracts.models import _to_json
from investment_system.personal.versioning import content_hash
from investment_system.qgv import raw_map


def _api():
    # Import in the test so the first RED run reports the missing feature.
    from investment_system.qgv.price_value import VPriceInputs, calculate_v_price_factors

    return VPriceInputs, calculate_v_price_factors


def _inputs(**values):
    cls, _ = _api()
    return cls(**values)


def _calculate(inputs, *, price):
    _, calculate = _api()
    return calculate(inputs, price=price)


def _legacy(inputs, *, price):
    return SimpleNamespace(
        price=price,
        **{item.name: getattr(inputs, item.name) for item in fields(inputs)},
    )


def _unavailable(factor, reason):
    assert factor.score is None
    assert factor.state == "NOT_AVAILABLE"
    assert factor.reason == reason


def test_result_identifies_ram_only_uncalibrated_v1_and_undefined_definitions():
    from investment_system.qgv.price_value import UNDEFINED_PRICE_DEFINITIONS

    result = _calculate(_inputs(), price=None)
    assert result.role == "RAM_ONLY_V1"
    assert result.standard == "v1"
    assert result.calibration == "UNCALIBRATED"
    assert result.standard_status == "STANDARD v1 · UNCALIBRATED"
    assert result.undefined_price_definitions == UNDEFINED_PRICE_DEFINITIONS == (
        "DCF_SOLVER",
        "REVERSE_DCF_SOLVER",
        "OWN_MULTIPLE_PRICE_MAPPING",
        "HISTORICAL_VALUATION_PRICE_MAPPING",
        "SECTOR_CONTEXT_PRICE_MAPPING",
        "THEME_PRICE_MAPPING",
    )
    assert set(result.factors) == {
        "fundamental_value", "margin_of_safety", "reverse_dcf", "peer_relative_value",
        "historical_valuation", "sector_context", "theme_premium_discount",
    }


def test_price_is_an_explicit_required_keyword_argument():
    _, calculate = _api()
    with pytest.raises(TypeError):
        calculate(_inputs())
    with pytest.raises(TypeError):
        calculate(_inputs(), 10.0)


@pytest.mark.parametrize("dcf_value", [120.0, -120.0, 80.0])
def test_dcf_truthy_branch_has_exact_approved_helper_scores(dcf_value):
    inputs = _inputs(dcf_value=dcf_value, eps=50.0, basis_confirmed=True)
    result = _calculate(inputs, price=100.0)
    raw = _legacy(inputs, price=100.0)
    assert result.factors["fundamental_value"].score == raw_map._central_value_score(raw)
    assert result.factors["margin_of_safety"].score == raw_map._mos_score(raw)
    assert result.factors["fundamental_value"].state == "CALCULATED"
    assert result.factors["fundamental_value"].reason == "APPROVED_V1_MAPPING"


def test_zero_dcf_uses_existing_eps_fallback():
    inputs = _inputs(dcf_value=0.0, eps=2.0, basis_confirmed=True)
    result = _calculate(inputs, price=30.0)
    raw = _legacy(inputs, price=30.0)
    assert result.factors["fundamental_value"].score == raw_map._central_value_score(raw)
    assert result.factors["margin_of_safety"].score == raw_map._mos_score(raw)


@pytest.mark.parametrize("price", [10, 30.0, 50.0])
def test_eps_fallback_has_exact_approved_helper_scores(price):
    inputs = _inputs(eps=2.0, revenue=105.0, revenue_prev=100.0, basis_confirmed=True)
    result = _calculate(inputs, price=price)
    raw = _legacy(inputs, price=price)
    assert result.factors["fundamental_value"].score == raw_map._central_value_score(raw)
    assert result.factors["margin_of_safety"].score == raw_map._mos_score(raw)
    assert result.factors["reverse_dcf"].score == raw_map._reverse_dcf_score(raw)


def test_finite_extreme_values_keep_existing_clip_endpoints():
    for dcf, expected in [(1.0, 0.0), (1000.0, 100.0)]:
        result = _calculate(_inputs(dcf_value=dcf, basis_confirmed=True), price=100.0)
        assert result.factors["fundamental_value"].score == expected
        assert result.factors["margin_of_safety"].score == expected


def test_margin_of_safety_remains_separate_from_central_value():
    result = _calculate(_inputs(dcf_value=100.0, basis_confirmed=True), price=90.0)
    assert result.factors["fundamental_value"].score > 50.0
    assert result.factors["margin_of_safety"].score < 50.0


def test_reverse_dcf_explicit_zero_does_not_need_price_eps_or_basis():
    inputs = _inputs(reverse_dcf_implied_growth=0.0, revenue=110.0, revenue_prev=100.0)
    result = _calculate(inputs, price=None)
    factor = result.factors["reverse_dcf"]
    assert factor.score == raw_map._reverse_dcf_score(_legacy(inputs, price=None))
    assert factor.state == "CALCULATED"
    _unavailable(result.factors["fundamental_value"], "MISSING_PRICE")


def test_reverse_dcf_explicit_growth_ignores_unneeded_invalid_price_and_eps():
    inputs = _inputs(
        reverse_dcf_implied_growth=0.05, revenue=120.0, revenue_prev=100.0, eps=float("nan"),
    )
    result = _calculate(inputs, price=False)
    assert result.factors["reverse_dcf"].score == raw_map._reverse_dcf_score(_legacy(inputs, price=False))
    _unavailable(result.factors["fundamental_value"], "INVALID_PRICE")


def test_reverse_dcf_eps_proxy_preserves_both_implied_growth_clip_limits():
    inputs = _inputs(eps=1.0, revenue=105.0, revenue_prev=100.0, basis_confirmed=True)
    for price in [1.0, 20.0, 100.0]:
        result = _calculate(inputs, price=price)
        assert result.factors["reverse_dcf"].score == raw_map._reverse_dcf_score(_legacy(inputs, price=price))


def test_missing_or_nonpositive_eps_is_unavailable_without_zero_fill():
    for eps in [None, 0.0, -2.0]:
        inputs = _inputs(eps=eps, revenue=100.0, revenue_prev=100.0, basis_confirmed=True)
        result = _calculate(inputs, price=10.0)
        for factor_id in ["fundamental_value", "margin_of_safety", "reverse_dcf"]:
            _unavailable(result.factors[factor_id], "MISSING_INPUT")


def test_reverse_dcf_missing_or_zero_revenue_denominator_is_unavailable():
    for revenue, previous in [(None, 100.0), (100.0, None), (100.0, 0.0)]:
        result = _calculate(_inputs(
            reverse_dcf_implied_growth=0.0, revenue=revenue, revenue_prev=previous,
        ), price=None)
        _unavailable(result.factors["reverse_dcf"], "MISSING_INPUT")


def test_reverse_dcf_negative_revenue_denominator_retains_approved_formula():
    inputs = _inputs(reverse_dcf_implied_growth=-0.05, revenue=-110.0, revenue_prev=-100.0)
    result = _calculate(inputs, price=None)
    assert result.factors["reverse_dcf"].score == raw_map._reverse_dcf_score(_legacy(inputs, price=None))


def test_missing_price_clears_price_dependent_factors_in_each_new_result():
    inputs = _inputs(dcf_value=100.0, eps=5.0, revenue=110.0, revenue_prev=100.0, basis_confirmed=True)
    calculated = _calculate(inputs, price=90.0)
    missing = _calculate(inputs, price=None)
    for factor_id in ["fundamental_value", "margin_of_safety", "reverse_dcf"]:
        assert calculated.factors[factor_id].state == "CALCULATED"
        _unavailable(missing.factors[factor_id], "MISSING_PRICE")


def test_price_rejects_nonpositive_nonfinite_bool_and_non_plain_numbers():
    class FloatSubclass(float):
        pass

    inputs = _inputs(dcf_value=100.0, eps=5.0, revenue=110.0, revenue_prev=100.0, basis_confirmed=True)
    for price in [0, -1.0, float("nan"), float("inf"), -float("inf"), True, False, "10", Decimal("10"), FloatSubclass(10.0), 10**1000]:
        result = _calculate(inputs, price=price)
        for factor_id in ["fundamental_value", "margin_of_safety", "reverse_dcf"]:
            _unavailable(result.factors[factor_id], "INVALID_PRICE")


def test_price_dependent_paths_require_explicit_boolean_basis_confirmation():
    for basis in [False, None, 1, "confirmed"]:
        inputs = _inputs(dcf_value=100.0, eps=5.0, revenue=110.0, revenue_prev=100.0, basis_confirmed=basis)
        result = _calculate(inputs, price=90.0)
        for factor_id in ["fundamental_value", "margin_of_safety", "reverse_dcf"]:
            _unavailable(result.factors[factor_id], "BASIS_UNCONFIRMED")


def test_invalid_selected_numeric_inputs_are_unavailable_with_fixed_reasons():
    field_to_factor = {
        "dcf_value": "fundamental_value", "eps": "margin_of_safety",
        "revenue": "reverse_dcf", "revenue_prev": "reverse_dcf",
        "reverse_dcf_implied_growth": "reverse_dcf", "own_multiple": "peer_relative_value",
        "peer_median_multiple": "peer_relative_value", "hist_valuation_percentile": "historical_valuation",
        "sector_context_score": "sector_context", "theme_premium_score": "theme_premium_discount",
    }
    base = _inputs(
        eps=2.0, revenue=100.0, revenue_prev=100.0, reverse_dcf_implied_growth=0.0,
        own_multiple=15.0, peer_median_multiple=20.0, basis_confirmed=True,
    )
    for name, factor_id in field_to_factor.items():
        for invalid in [float("nan"), float("inf"), -float("inf"), True, "bad", Decimal("1"), 10**1000]:
            result = _calculate(replace(base, **{name: invalid}), price=30.0)
            _unavailable(result.factors[factor_id], "INVALID_INPUT")


def test_unused_bad_eps_does_not_replace_the_valid_dcf_priority_branch():
    inputs = _inputs(dcf_value=120.0, eps=float("nan"), basis_confirmed=True)
    result = _calculate(inputs, price=100.0)
    raw = _legacy(inputs, price=100.0)
    assert result.factors["fundamental_value"].score == raw_map._central_value_score(raw)
    assert result.factors["margin_of_safety"].score == raw_map._mos_score(raw)


def test_supplied_history_sector_and_theme_scores_pass_through_without_price_or_basis():
    for score in [0, 42.5, 100.0]:
        result = _calculate(_inputs(
            hist_valuation_percentile=score, sector_context_score=score, theme_premium_score=score,
        ), price=None)
        for factor_id in ["historical_valuation", "sector_context", "theme_premium_discount"]:
            factor = result.factors[factor_id]
            assert factor.score == score
            assert factor.state == "PASSTHROUGH"
            assert factor.reason == "SUPPLIED_SCORE"


def test_missing_history_sector_and_theme_mappings_are_explicitly_undefined():
    result = _calculate(_inputs(), price=100.0)
    for factor_id in ["historical_valuation", "sector_context", "theme_premium_discount"]:
        _unavailable(result.factors[factor_id], "UNDEFINED_PRICE_MAPPING")


def test_supplied_scores_outside_0_100_are_unavailable_instead_of_clipped():
    for invalid in [-0.1, 100.1]:
        result = _calculate(_inputs(
            hist_valuation_percentile=invalid, sector_context_score=invalid, theme_premium_score=invalid,
        ), price=None)
        for factor_id in ["historical_valuation", "sector_context", "theme_premium_discount"]:
            _unavailable(result.factors[factor_id], "INVALID_INPUT")


def test_peer_relative_value_uses_only_supplied_truthy_multiples():
    for own, peer in [(18.0, 20.0), (20.0, 20.0), (-18.0, -20.0), (-18.0, 20.0)]:
        result = _calculate(_inputs(own_multiple=own, peer_median_multiple=peer), price=None)
        expected = raw_map._clip_score(50.0 + ((peer - own) / peer) / 0.3 * 50.0)
        assert result.factors["peer_relative_value"].score == expected
        assert result.factors["peer_relative_value"].state == "CALCULATED"


def test_peer_multiple_is_not_inferred_from_price_and_eps():
    result = _calculate(_inputs(eps=2.0, peer_median_multiple=20.0, basis_confirmed=True), price=30.0)
    _unavailable(result.factors["peer_relative_value"], "MISSING_INPUT")


def test_zero_peer_or_own_multiple_preserves_the_existing_missing_branch():
    for own, peer in [(0.0, 20.0), (20.0, 0.0), (None, 20.0), (20.0, None)]:
        result = _calculate(_inputs(own_multiple=own, peer_median_multiple=peer), price=None)
        _unavailable(result.factors["peer_relative_value"], "MISSING_INPUT")


def test_nonfinite_intermediates_are_calculation_errors_before_any_clip():
    cases = [
        (_inputs(dcf_value=1e308, basis_confirmed=True), 1e-308, "fundamental_value"),
        (_inputs(dcf_value=1e308, basis_confirmed=True), 1e-308, "margin_of_safety"),
        (_inputs(eps=1e-308, basis_confirmed=True), 1e308, "fundamental_value"),
        (_inputs(eps=1e308, basis_confirmed=True), 1e308, "margin_of_safety"),
        (_inputs(eps=1e-308, revenue=100.0, revenue_prev=100.0, basis_confirmed=True), 1e308, "reverse_dcf"),
        (_inputs(reverse_dcf_implied_growth=0.0, revenue=1e308, revenue_prev=1e-308), None, "reverse_dcf"),
        (_inputs(reverse_dcf_implied_growth=-1e308, revenue=1e308, revenue_prev=1.0), None, "reverse_dcf"),
        (_inputs(reverse_dcf_implied_growth=-1e306, revenue=1.0, revenue_prev=1.0), None, "reverse_dcf"),
        (_inputs(own_multiple=-1e308, peer_median_multiple=1e308), None, "peer_relative_value"),
        (_inputs(own_multiple=1e308, peer_median_multiple=1e-308), None, "peer_relative_value"),
    ]
    for inputs, price, factor_id in cases:
        result = _calculate(inputs, price=price)
        _unavailable(result.factors[factor_id], "CALCULATION_ERROR")


def test_large_but_finite_intermediates_can_still_clip_normally():
    result = _calculate(_inputs(dcf_value=1e100, basis_confirmed=True), price=1.0)
    assert result.factors["fundamental_value"].score == 100.0
    assert result.factors["margin_of_safety"].score == 100.0


def test_finite_integer_arithmetic_keeps_legacy_rounding_above_float_precision():
    price = 2**53 + 2
    inputs = _inputs(dcf_value=2**53 + 3, basis_confirmed=True)
    result = _calculate(inputs, price=price)
    raw = _legacy(inputs, price=price)
    assert result.factors["fundamental_value"].score == raw_map._central_value_score(raw)
    assert result.factors["margin_of_safety"].score == raw_map._mos_score(raw)
    peer = _inputs(own_multiple=-(10**308), peer_median_multiple=10**308)
    expected = raw_map._clip_score(50.0 + ((peer.peer_median_multiple - peer.own_multiple) / peer.peer_median_multiple) / 0.3 * 50.0)
    assert _calculate(peer, price=None).factors["peer_relative_value"].score == expected


def test_inputs_results_and_factor_mapping_are_immutable():
    inputs = _inputs(dcf_value=120.0, basis_confirmed=True)
    result = _calculate(inputs, price=100.0)
    assert isinstance(result.factors, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        inputs.dcf_value = 1.0
    with pytest.raises(FrozenInstanceError):
        result.role = "PUBLIC"
    with pytest.raises(FrozenInstanceError):
        result.factors["fundamental_value"].score = 1.0
    with pytest.raises(TypeError):
        result.factors["fundamental_value"] = None


def test_reprs_hide_inputs_price_and_factor_scores():
    inputs = _inputs(dcf_value=123.4567, eps=6.789, hist_valuation_percentile=37.1234, basis_confirmed=True)
    result = _calculate(inputs, price=93.2468)
    assert "123.4567" not in repr(inputs)
    assert "6.789" not in repr(inputs)
    assert "37.1234" not in repr(inputs)
    assert "93.2468" not in repr(result)
    assert "37.1234" not in repr(result)
    assert "37.1234" not in repr(result.factors["historical_valuation"])
    assert "score=" not in repr(result.factors["historical_valuation"])


def test_public_json_and_canonical_serializers_reject_the_ram_only_result():
    result = _calculate(_inputs(dcf_value=100.0, basis_confirmed=True), price=90.0)
    with pytest.raises(TypeError):
        json.dumps(result)
    with pytest.raises(TypeError):
        json.dumps(_to_json(result.factors))
    with pytest.raises(TypeError):
        asdict(result)
    with pytest.raises(TypeError):
        content_hash(result)


def test_calculation_performs_no_io_logging_or_serialization(monkeypatch):
    import builtins

    def forbidden(*args, **kwargs):
        raise AssertionError("RAM-only calculation attempted a side effect")

    inputs = _inputs(
        dcf_value=120.0, eps=5.0, revenue=110.0, revenue_prev=100.0,
        own_multiple=18.0, peer_median_multiple=20.0, hist_valuation_percentile=40.0,
        sector_context_score=50.0, theme_premium_score=60.0, basis_confirmed=True,
    )
    with monkeypatch.context() as guard:
        guard.setattr(builtins, "open", forbidden)
        guard.setattr(builtins, "print", forbidden)
        for method in ["open", "read_text", "read_bytes", "write_text", "write_bytes"]:
            guard.setattr(Path, method, forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(urllib.request, "urlopen", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(logging.Logger, "_log", forbidden)
        guard.setattr(json, "dump", forbidden)
        guard.setattr(json, "dumps", forbidden)
        result = _calculate(inputs, price=100.0)
    assert all(factor.score is not None for factor in result.factors.values())


def test_repeated_prices_are_independent_and_do_not_modify_inputs():
    inputs = _inputs(dcf_value=120.0, basis_confirmed=True)
    before = asdict(inputs)
    first = _calculate(inputs, price=100.0)
    second = _calculate(inputs, price=120.0)
    assert first.factors["fundamental_value"].score != second.factors["fundamental_value"].score
    assert _calculate(inputs, price=100.0) == first
    assert asdict(inputs) == before


def test_result_retains_no_price_inputs_or_aggregate_fields():
    result = _calculate(_inputs(dcf_value=100.0, basis_confirmed=True), price=90.0)
    assert {item.name for item in fields(result)} == {
        "factors", "role", "standard", "calibration", "standard_status", "undefined_price_definitions",
    }
    for name in ["price", "inputs", "dcf_value", "eps", "v_score", "weights", "total_score", "to_dict"]:
        assert not hasattr(result, name)
