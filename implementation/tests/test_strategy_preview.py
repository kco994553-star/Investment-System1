"""Synthetic, local-only previews must preserve the adopted leaf-weight rules."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
import json
from types import MappingProxyType

import pytest

from investment_system.contracts.enums import CoverageState, ProfileKind, QualityState
from investment_system.contracts.models import FactorObservation
from investment_system.qgv.strategy_preview import (
    official_v1_weight_copy,
    recalculate_strategy_preview,
)
from investment_system.personal.weights import SIBLING_SUM_TOLERANCE
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_INITIAL_PRIOR
from tests.helpers import AS_OF, complete_obs


def vector_observations():
    observations = complete_obs()
    for weights in (Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR):
        for index, factor_id in enumerate(weights, start=1):
            score = index * 10.0
            observations[factor_id] = FactorObservation(
                factor_id, score, score, QualityState.SYNTHETIC, "synthetic-preview"
            )
    return observations


def concentrated_weights(axis, factor_id):
    return {
        axis: {
            fid: 100.0 if fid == factor_id else 0.0
            for fid in official_v1_weight_copy()[axis]
        }
    }


def test_official_copy_contains_exact_adopted_percentages_and_factor_order():
    weights = official_v1_weight_copy()
    assert weights == {
        "Q": {"competitive_advantage": 20.0, "roic_wacc": 20.0,
              "market_position": 15.0, "fcf_quality": 15.0,
              "margin_quality": 10.0, "financial_health": 10.0,
              "management_quality": 10.0},
        "G": {"next_3_5y_growth": 25.0, "growth_efficiency": 20.0,
              "revenue_growth": 15.0, "eps_fcf_per_share_growth": 15.0,
              "growth_durability": 15.0, "excess_growth_vs_industry": 10.0},
        "V": {"fundamental_value": 25.0, "reverse_dcf": 20.0,
              "peer_relative_value": 15.0, "historical_valuation": 15.0,
              "margin_of_safety": 10.0, "sector_context": 10.0,
              "theme_premium_discount": 5.0},
    }
    assert tuple(weights) == ("Q", "G", "V")
    assert tuple(weights["V"]) == tuple(V_INITIAL_PRIOR)


def test_official_copy_mutation_does_not_change_original_objects_or_next_copy():
    originals = (Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR)
    original_values = deepcopy(originals)
    first, second = official_v1_weight_copy(), official_v1_weight_copy()
    for axis in first:
        assert first[axis] is not second[axis]
        first[axis].clear()
    assert originals == original_values
    assert all(current is original for current, original in zip(
        (Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR), originals
    ))
    assert official_v1_weight_copy() == second


def test_default_vectors_use_official_leaf_weights_and_keep_v_separate():
    result = recalculate_strategy_preview(vector_observations())
    assert result.axes["Q"].score == 34.5
    assert result.axes["G"].score == 30.5
    assert result.axes["V"].score == 31.5
    assert result.qg_preview_total == 32.5
    assert all(axis.coverage == CoverageState.READY for axis in result.axes.values())
    assert all(axis.missing_factor_count == 0 for axis in result.axes.values())
    assert result.parent_mix_note == "UNDEFINED_PARENT_WEIGHTS"


def test_official_default_preview_matches_existing_analysis_float_results():
    observations = vector_observations()
    official = AnalysisEngine().analyze("synthetic", AS_OF, observations)
    result = recalculate_strategy_preview(observations)
    for axis, score in (("Q", official.Q_score), ("G", official.G_score), ("V", official.V_score)):
        assert result.axes[axis].score.hex() == score.hex()
    assert result.qg_preview_total == official.total_score
    assert result.official_weights == result.effective_weights == official_v1_weight_copy()


def test_empty_observations_report_all_missing_and_block_every_axis():
    result = recalculate_strategy_preview({})
    assert result.qg_preview_total is None
    for axis, expected_count in (("Q", 7), ("G", 6), ("V", 7)):
        preview = result.axes[axis]
        assert preview.score is None and preview.coverage == CoverageState.BLOCKED
        assert preview.missing_factor_count == expected_count
        assert preview.missing_factor_ids == tuple(result.official_weights[axis])


def test_missing_fundamental_value_keeps_52_5_without_renormalizing():
    observations = complete_obs()
    del observations["fundamental_value"]
    result = recalculate_strategy_preview(observations)
    assert result.axes["V"].score == 52.5
    assert result.axes["V"].coverage == CoverageState.PARTIAL
    assert result.axes["V"].missing_factor_ids == ("fundamental_value",)
    assert result.axes["V"].missing_factor_count == 1
    assert result.qg_preview_total == 70.0


def test_missing_quality_and_null_scores_follow_existing_missing_rule():
    for quality, score in ((QualityState.MISSING_DATA, 70.0),
                           (QualityState.PIT_UNAVAILABLE, 70.0),
                           (QualityState.OK, None),
                           (QualityState.NOT_APPLICABLE, 70.0)):
        observations = complete_obs()
        observations["fundamental_value"] = FactorObservation(
            "fundamental_value", None, score, quality, None
        )
        result = recalculate_strategy_preview(observations)
        assert result.axes["V"].score == 52.5
        assert result.axes["V"].coverage == CoverageState.PARTIAL
        assert result.axes["V"].missing_factor_ids == ("fundamental_value",)


def test_blocked_dependency_dominates_other_available_v_factors():
    observations = complete_obs()
    observations["fundamental_value"] = FactorObservation(
        "fundamental_value", None, 70.0, QualityState.BLOCKED_DEPENDENCY, None
    )
    result = recalculate_strategy_preview(observations)
    assert result.axes["V"].score is None
    assert result.axes["V"].coverage == CoverageState.BLOCKED
    assert result.axes["V"].missing_factor_ids == ("fundamental_value",)


def test_financial_roic_wacc_is_not_applicable_and_not_counted_as_missing():
    observations = complete_obs()
    del observations["roic_wacc"]
    result = recalculate_strategy_preview(observations, profile_kind=ProfileKind.FINANCIAL)
    assert result.axes["Q"].score == 56.0
    assert result.axes["Q"].coverage == CoverageState.PARTIAL
    assert result.axes["Q"].missing_factor_count == 0
    assert result.axes["Q"].not_applicable_ids == ("roic_wacc",)
    assert result.qg_preview_total == 63.0


def test_financial_profile_skips_even_a_blocked_roic_dependency():
    observations = complete_obs()
    observations["roic_wacc"] = FactorObservation(
        "roic_wacc", None, None, QualityState.BLOCKED_DEPENDENCY, None
    )
    result = recalculate_strategy_preview(observations, profile_kind=ProfileKind.FINANCIAL)
    assert result.axes["Q"].score == 56.0
    assert result.axes["Q"].missing_factor_ids == ()
    assert result.axes["Q"].not_applicable_ids == ("roic_wacc",)


def test_general_corporate_roic_wacc_remains_missing():
    observations = complete_obs()
    del observations["roic_wacc"]
    result = recalculate_strategy_preview(observations)
    assert result.axes["Q"].score == 56.0
    assert result.axes["Q"].missing_factor_ids == ("roic_wacc",)
    assert result.axes["Q"].not_applicable_ids == ()


def test_actual_zero_score_is_usable_with_complete_coverage():
    result = recalculate_strategy_preview(complete_obs(0.0))
    assert result.qg_preview_total == 0.0
    assert all(axis.score == 0.0 and axis.coverage == CoverageState.READY
               and axis.missing_factor_count == 0 for axis in result.axes.values())


def test_complete_user_axis_weights_allow_zero_and_100_percent():
    weights = concentrated_weights("Q", "competitive_advantage")
    result = recalculate_strategy_preview(vector_observations(), weights)
    assert result.axes["Q"].score == 10.0
    assert result.qg_preview_total == 20.25
    assert result.effective_weights["Q"] == weights["Q"]
    assert result.official_weights["Q"]["competitive_advantage"] == 20.0
    assert result.effective_weights["G"] == result.official_weights["G"]


def test_sparse_user_overrides_apply_to_an_official_copy():
    result = recalculate_strategy_preview(
        vector_observations(), {"Q": {"competitive_advantage": 10, "roic_wacc": 30}}
    )
    assert result.axes["Q"].score == 35.5
    assert result.effective_weights["Q"]["market_position"] == 15.0
    assert result.official_weights["Q"]["roic_wacc"] == 20.0


def test_v_preview_weights_have_no_official_candidate_5_30_constraint():
    result = recalculate_strategy_preview(
        vector_observations(), concentrated_weights("V", "fundamental_value")
    )
    assert result.axes["V"].score == 10.0
    assert result.axes["V"].coverage == CoverageState.READY
    assert result.qg_preview_total == 32.5


def test_zero_weight_missing_factor_still_counts_and_marks_partial():
    observations = complete_obs()
    del observations["fundamental_value"]
    result = recalculate_strategy_preview(
        observations, {"V": {"fundamental_value": 0, "reverse_dcf": 45}}
    )
    assert result.axes["V"].score == 70.0
    assert result.axes["V"].coverage == CoverageState.PARTIAL
    assert result.axes["V"].missing_factor_ids == ("fundamental_value",)
    assert result.axes["V"].missing_factor_count == 1


def test_zero_weight_blocked_dependency_still_blocks():
    observations = complete_obs()
    observations["fundamental_value"] = FactorObservation(
        "fundamental_value", None, None, QualityState.BLOCKED_DEPENDENCY, None
    )
    result = recalculate_strategy_preview(
        observations, {"V": {"fundamental_value": 0, "reverse_dcf": 45}}
    )
    assert result.axes["V"].score is None
    assert result.axes["V"].coverage == CoverageState.BLOCKED


def test_v_blocked_dependency_does_not_affect_qg_only_total():
    observations = complete_obs()
    observations["fundamental_value"] = FactorObservation(
        "fundamental_value", None, None, QualityState.BLOCKED_DEPENDENCY, None
    )
    result = recalculate_strategy_preview(observations)
    assert result.axes["V"].score is None
    assert result.qg_preview_total == 70.0
    assert result.parent_mix_note == "UNDEFINED_PARENT_WEIGHTS"


def test_q_or_g_blocked_dependency_prevents_qg_total():
    for factor_id in ("competitive_advantage", "next_3_5y_growth"):
        observations = complete_obs()
        observations[factor_id] = FactorObservation(
            factor_id, None, None, QualityState.BLOCKED_DEPENDENCY, None
        )
        assert recalculate_strategy_preview(observations).qg_preview_total is None


def test_qg_total_retains_existing_four_decimal_rounding():
    observations = complete_obs()
    for factors, score in ((Q_WEIGHTS, 80.123456), (G_WEIGHTS, 50.987654)):
        for factor_id in factors:
            observations[factor_id] = replace(observations[factor_id], score_0_100=score)
    result = recalculate_strategy_preview(observations)
    assert result.qg_preview_total == 65.5556
    assert result.qg_preview_total == AnalysisEngine().analyze("synthetic", AS_OF, observations).total_score


def test_sum_tolerance_is_converted_to_percent_units_without_normalization():
    value = 20.0 + SIBLING_SUM_TOLERANCE * 100 / 2
    result = recalculate_strategy_preview(complete_obs(), {"Q": {"competitive_advantage": value}})
    assert result.effective_weights["Q"]["competitive_advantage"] == value
    assert sum(result.effective_weights["Q"].values()) > 100.0
    with pytest.raises(ValueError, match="sum"):
        recalculate_strategy_preview(complete_obs(), {
            "Q": {"competitive_advantage": 20.0 + SIBLING_SUM_TOLERANCE * 100 * 2}
        })


def test_invalid_axis_totals_are_rejected_without_auto_normalization():
    for overrides in ({"Q": {"competitive_advantage": 21}},
                      {"V": {fid: 0.0 for fid in V_INITIAL_PRIOR}},
                      {"Q": {fid: 100.0 for fid in Q_WEIGHTS}}):
        with pytest.raises(ValueError, match="sum"):
            recalculate_strategy_preview(complete_obs(), overrides)


def test_unknown_axes_factors_and_nonmapping_weight_inputs_are_rejected():
    for weights in ({"TECHNICAL": {}}, {"q": {}},
                    {"Q": {"capital_allocation": 10}},
                    {"Q": {"fundamental_value": 25}},
                    {"Q": []}, [], False):
        with pytest.raises(ValueError):
            recalculate_strategy_preview(complete_obs(), weights)


def test_nonfinite_boolean_nonnumeric_and_out_of_range_weights_are_rejected():
    for value in (float("nan"), float("inf"), -float("inf"),
                  True, False, "20", None, -1, 101, 10 ** 1000):
        with pytest.raises(ValueError):
            recalculate_strategy_preview(complete_obs(), {"Q": {"competitive_advantage": value}})


def test_invalid_observation_scores_are_rejected_without_clipping():
    for score in (float("nan"), float("inf"), -float("inf"),
                  True, False, "70", -0.1, 100.1, 10 ** 1000):
        observations = complete_obs()
        observations["competitive_advantage"] = replace(
            observations["competitive_advantage"], score_0_100=score
        )
        with pytest.raises(ValueError):
            recalculate_strategy_preview(observations)


def test_invalid_observation_shape_quality_identity_and_profile_are_rejected():
    valid = complete_obs()["competitive_advantage"]
    for invalid in (None, {}, replace(valid, quality="OK"),
                    replace(valid, factor_id="roic_wacc")):
        with pytest.raises(ValueError):
            recalculate_strategy_preview({"competitive_advantage": invalid})
    with pytest.raises(ValueError):
        recalculate_strategy_preview([])
    with pytest.raises(ValueError):
        recalculate_strategy_preview(complete_obs(), profile_kind="FINANCIAL")


def test_result_role_and_every_returned_mapping_are_immutable():
    result = recalculate_strategy_preview(complete_obs())
    assert result.role == "PREVIEW"
    assert isinstance(result.axes, MappingProxyType)
    for mapping in (result.axes, result.official_weights, result.effective_weights,
                    result.official_weights["Q"], result.effective_weights["V"]):
        with pytest.raises(TypeError):
            mapping["anything"] = 0
    with pytest.raises(FrozenInstanceError):
        result.role = "OFFICIAL"
    with pytest.raises(FrozenInstanceError):
        result.axes["Q"].score = 0
    with pytest.raises(ValueError):
        replace(result, role="OFFICIAL")
    with pytest.raises(TypeError):
        type(result)(axes=result.axes, qg_preview_total=0,
                     official_weights=result.official_weights,
                     effective_weights=result.effective_weights, role="OFFICIAL")


def test_preview_scores_are_hidden_from_repr_and_generic_serialization():
    result = recalculate_strategy_preview(complete_obs(73.2468))
    assert "73.2468" not in repr(result)
    assert "73.2468" not in repr(result.axes["Q"])
    assert "PREVIEW" in repr(result)
    with pytest.raises(TypeError):
        asdict(result)
    with pytest.raises(TypeError):
        json.dumps(result)


def test_inputs_and_official_maps_remain_unchanged_and_results_are_detached():
    observations = vector_observations()
    user_weights = concentrated_weights("Q", "competitive_advantage")
    originals = (Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR)
    before_observations, before_weights, before_official = (
        deepcopy(observations), deepcopy(user_weights), deepcopy(originals)
    )
    result = recalculate_strategy_preview(observations, user_weights)
    assert observations == before_observations
    assert user_weights == before_weights
    assert originals == before_official
    user_weights["Q"]["competitive_advantage"] = 0.0
    observations.clear()
    assert result.axes["Q"].score == 10.0
    assert result.effective_weights["Q"]["competitive_advantage"] == 100.0
    assert result.official_weights == official_v1_weight_copy()
