"""User-fixed Scoring Standard v1; numeric expectations predate its adoption."""

import ast
from dataclasses import fields
from datetime import datetime
import hashlib
import inspect

from investment_system.contracts.enums import CalibrationLifecycle, ProfileKind, QualityState
from investment_system.contracts.models import FactorObservation, QGVSnapshot
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_CANDIDATES, V_INITIAL_PRIOR, validate_v_candidate_weights
from investment_system.qgv.g_horizon import DEFAULT_G_HORIZON
from investment_system.qgv import raw_map
from investment_system.qgv.scoring import production_v_score
from tests.helpers import AS_OF, complete_obs


def test_v1_exact_q_g_v_weights_horizon_and_constraints():
    assert Q_WEIGHTS == {
        "competitive_advantage": 0.20, "roic_wacc": 0.20, "market_position": 0.15,
        "fcf_quality": 0.15, "margin_quality": 0.10, "financial_health": 0.10,
        "management_quality": 0.10,
    }
    assert G_WEIGHTS == {
        "next_3_5y_growth": 0.25, "growth_efficiency": 0.20, "revenue_growth": 0.15,
        "eps_fcf_per_share_growth": 0.15, "growth_durability": 0.15,
        "excess_growth_vs_industry": 0.10,
    }
    assert V_INITIAL_PRIOR == {
        "fundamental_value": 0.25, "reverse_dcf": 0.20, "peer_relative_value": 0.15,
        "historical_valuation": 0.15, "margin_of_safety": 0.10,
        "sector_context": 0.10, "theme_premium_discount": 0.05,
    }
    for weights in (Q_WEIGHTS, G_WEIGHTS, V_INITIAL_PRIOR):
        assert abs(sum(weights.values()) - 1.0) < 1e-12
        assert all(0.05 <= value <= 0.30 for value in weights.values())
    assert validate_v_candidate_weights(V_INITIAL_PRIOR) == []
    assert DEFAULT_G_HORIZON == "3Y"


def test_v1_weight_boundaries_remain_fail_closed():
    for lower, upper in ((0.04, 0.26), (0.31, -0.01)):
        bad = dict(V_INITIAL_PRIOR, fundamental_value=lower, theme_premium_discount=upper)
        assert validate_v_candidate_weights(bad)
    assert validate_v_candidate_weights(dict(V_INITIAL_PRIOR, fundamental_value=0.24))


def test_v1_d10_all_current_mapping_rules_are_fixed():
    # Pin expressions and literals, ignoring comments/status-only module text.
    expected = {
        "_clip_score": "d3d7ac1572b6e29301245d5ccbb7e90387e25cbd3e25b236ff51ad99b78392f6",
        "_obs": "486a0b3a6c69d1b104ac72712669bfcaee270eaaf289bbf40d9fe029e994822d",
        "_ratio": "ddc14b344df4148d9f4ba9b105dbd6ddb72b8b1f5d7d2381a83b6ee216aec5f8",
        "_yoy": "234b42766d8f8fdd41dbbf1888e1f0bdd64151e6d18486404009cae6b38df264",
        "_growth_to_score": "44977abb7db4f5f93b55b5639e0ffa8a51afc3e31712d762907f8e946ed8afe0",
        "_spread_to_score": "4487ebb14f456e8f0d8cc1b69046d58c5e0b2c80b7bdf63d2d094e1b669b6188",
        "_central_value_score": "6e24dec1fe62c0df55ea285bbef3dc411935e0e8d4694ad2ce74c5704ebc326a",
        "_mos_score": "84a57f377b37edf2361cee81275bb5a506e9c788ee174a834c66cfd4d3cd32c1",
        "_reverse_dcf_score": "257290a7af24e6c2e52df2b7494716e74473378d74222402b08484c7651004fe",
        "map_raw": "1c6006fd3480a7be77641f02bed905c80996bd7bd371c7eebb04eb39d0895ce5",
    }
    for name, digest in expected.items():
        node = ast.parse(inspect.getsource(getattr(raw_map, name))).body[0]
        assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == digest


def test_v1_linear_clip_anchors_and_missing_values():
    for raw, expected in ((-0.50, 0), (-0.25, 0), (0, 50), (0.125, 75), (0.25, 100), (0.50, 100)):
        assert raw_map._growth_to_score(raw) == expected
    for raw, expected in ((-0.20, 0), (-0.10, 0), (0, 50), (0.05, 75), (0.10, 100), (0.20, 100)):
        assert raw_map._spread_to_score(raw) == expected
    assert raw_map._growth_to_score(None) is None
    assert raw_map._spread_to_score(None) is None


def test_v1_operational_snapshot_has_explicit_uncalibrated_metadata():
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs())
    payload = snap.to_dict()
    assert payload["standard"] == "v1"
    assert payload["calibration"] == "UNCALIBRATED"
    assert payload["standard_status"] == "STANDARD v1 · UNCALIBRATED"
    assert payload["V_policy_status"] == "STANDARD v1 · UNCALIBRATED"
    assert (snap.Q_score, snap.G_score, snap.V_score, snap.total_score) == (70, 70, 70, 70)
    assert payload["qgv_standard_version"] == "v1.5-balanced"
    assert payload["qgv_analysis_contract"] == "v1.7.6"


def test_v1_statuses_and_q7_name_are_standard_with_unchanged_identity():
    from investment_system.qgv.factors import Q_WEIGHTS_STATUS, G_WEIGHTS_STATUS, V_WEIGHTS_STATUS
    from investment_system.qgv.g_horizon import G_HORIZON_STATUS
    from investment_system.qgv.raw_map import RAW_MAP_STATUS
    from investment_system.qgv.scoring_standard import Q7_LABEL_EN, Q7_LABEL_KO

    for status in (Q_WEIGHTS_STATUS, G_WEIGHTS_STATUS, V_WEIGHTS_STATUS, G_HORIZON_STATUS, RAW_MAP_STATUS):
        assert status == "STANDARD v1 · UNCALIBRATED"
    assert Q7_LABEL_EN == "Management Quality"
    assert Q7_LABEL_KO == "경영진 품질"
    assert "management_quality" in Q_WEIGHTS and "capital_allocation" not in Q_WEIGHTS
    assert Q_WEIGHTS["management_quality"] == 0.10


def test_v1_uses_initial_prior_and_keeps_research_candidates_separate():
    obs = complete_obs()
    for fid, score in zip(V_INITIAL_PRIOR, (10, 20, 30, 40, 50, 60, 70)):
        obs[fid] = FactorObservation(fid, score, score, QualityState.OK, "v1-test")
    snap = AnalysisEngine().analyze("nvda", AS_OF, obs)
    assert snap.V_score == 31.5
    assert snap.total_score == 70
    for candidate in snap.to_dict()["v_candidates"]:
        if candidate["candidate_id"] == "initial_prior":
            assert candidate["lifecycle"] == "STANDARD v1 · UNCALIBRATED"
            assert candidate["standard"] == "v1"
            assert candidate["calibration"] == "UNCALIBRATED"
        else:
            assert candidate["lifecycle"] == "RESEARCH"
            assert candidate["standard"] is None and candidate["calibration"] is None
    assert V_CANDIDATES["equal_research"]["lifecycle"] == CalibrationLifecycle.RESEARCH
    assert V_CANDIDATES["mos_tilt_research"]["lifecycle"] == CalibrationLifecycle.RESEARCH
    score, lifecycle = production_v_score(snap.v_candidates, None)
    assert score is None  # No automatic research candidate fallback.
    assert lifecycle.value == "STANDARD v1 · UNCALIBRATED"


def test_v1_missing_and_blocked_v_preserve_existing_numeric_behavior():
    obs = complete_obs()
    del obs["fundamental_value"]
    snap = AnalysisEngine().analyze("nvda", AS_OF, obs)
    assert snap.V_score == 52.5  # Existing partial, non-renormalized prior.
    assert snap.factor_breakdown["v_coverage"] == "PARTIAL"
    assert snap.to_dict()["standard"] == "v1"
    assert snap.to_dict()["calibration"] == "UNCALIBRATED"
    obs["fundamental_value"] = FactorObservation("fundamental_value", None, None, QualityState.BLOCKED_DEPENDENCY, None)
    blocked = AnalysisEngine().analyze("nvda", AS_OF, obs)
    assert blocked.V_score is None
    assert blocked.factor_breakdown["v_coverage"] == "BLOCKED"
    assert blocked.to_dict()["calibration"] == "UNCALIBRATED"


def test_v1_type_adjustment_is_identity_for_both_existing_profiles():
    for profile in ProfileKind:
        snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(), profile_kind=profile)
        assert snap.type_adjusted_score_100 == snap.total_score


def test_v1_adoption_is_forward_only_separate_from_historical_as_of():
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs())
    payload = snap.to_dict()
    assert payload["standard_effective_at"] == "2026-10-08T11:50:25Z"
    assert datetime.fromisoformat(payload["standard_effective_at"].replace("Z", "+00:00")) > AS_OF
    assert snap.as_of == AS_OF  # Historical input date does not backdate adoption.
    for name in ("standard", "calibration", "standard_status", "standard_effective_at"):
        assert next(f for f in fields(QGVSnapshot) if f.name == name).default is None
    metadata_names = {"standard", "calibration", "standard_status", "standard_effective_at"}
    legacy_args = {f.name: getattr(snap, f.name) for f in fields(QGVSnapshot) if f.name not in metadata_names}
    legacy_args["V_policy_status"] = CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR
    legacy = QGVSnapshot(**legacy_args).to_dict()
    assert all(legacy[name] is None for name in metadata_names)
    assert legacy["V_policy_status"] == "PROVISIONAL_INITIAL_PRIOR"
    assert CalibrationLifecycle("PROVISIONAL_INITIAL_PRIOR").value == "PROVISIONAL_INITIAL_PRIOR"
    assert CalibrationLifecycle("PROVISIONAL").value == "PROVISIONAL"


def test_v1_operational_leaderboard_copies_metadata_without_relabelling_legacy():
    from investment_system.qgv.leaderboard import LeaderboardEngine

    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs())
    row = LeaderboardEngine().build("v1-test", AS_OF, [snap]).to_dict()["rows"][0]
    assert row["V_score"] == 70
    assert row["standard"] == "v1" and row["calibration"] == "UNCALIBRATED"
    metadata_names = {"standard", "calibration", "standard_status", "standard_effective_at"}
    legacy_args = {f.name: getattr(snap, f.name) for f in fields(QGVSnapshot) if f.name not in metadata_names}
    legacy = QGVSnapshot(**legacy_args)
    legacy_row = LeaderboardEngine().build("old-test", AS_OF, [legacy]).to_dict()["rows"][0]
    assert legacy_row["V_score"] == 70
    assert legacy_row["standard"] is None and legacy_row["calibration"] is None


def test_v1_us_session_output_and_html_display_existing_v_with_labels():
    from investment_system.qgv.us_live import evaluate_current_session
    from investment_system.qgv.html_sample import render_us_book_html

    session = evaluate_current_session(live_prices={"prices": {}})
    assert len(session["rows"]) == 17
    for row in session["rows"]:
        assert row["standard"] == "v1" and row["calibration"] == "UNCALIBRATED"
    sample = {
        "names": 1, "standard_status": "STANDARD v1 · UNCALIBRATED",
        "rows": [{"company_id": "nvda", "yahoo": "NVDA", "exchange": "NASDAQ",
                  "target_weight": 0.10, "Q": 70, "G": 70, "V": 31.5,
                  "standard": "v1", "calibration": "UNCALIBRATED"}],
    }
    html = render_us_book_html(sample)
    assert "31.5" in html
    assert "STANDARD v1 · UNCALIBRATED" in html
    assert "v1 · UNCALIBRATED" in html
    assert "V 생산점수는 null" not in html


def test_v1_new_historical_fixture_results_keep_adoption_time_and_metadata():
    from investment_system.validation.historical import run_as_of
    from investment_system.validation.records import ScopedTrackStore
    from tests.test_macro_pit_flag import AS_OF as FIXTURE_AS_OF, PAYLOAD

    store = ScopedTrackStore()
    row = run_as_of(FIXTURE_AS_OF, {"nvda": PAYLOAD}, {"nvda": []}, store, ("nvda",))
    quality = row["quality"]["nvda"]
    assert quality["standard"] == "v1" and quality["calibration"] == "UNCALIBRATED"
    assert quality["standard_effective_at"] == "2026-10-08T11:50:25Z"
    prediction = store.store.get(row["name_records"]["nvda"]).payload["prediction"]
    assert prediction["standard"] == "v1" and prediction["calibration"] == "UNCALIBRATED"
    assert prediction["as_of"] == FIXTURE_AS_OF.isoformat()
    assert row["official_pass"] is False and row["full_pit_pass"] is False


def test_v1_golden_projection_preserves_all_numeric_unknown_and_historical_fields():
    from copy import deepcopy
    import json
    from tools.qgv_contract_audit import DOCS, evaluate_case, expected_with_v1_metadata

    source = (DOCS / "golden_cases.json").read_bytes()
    assert hashlib.sha256(source).hexdigest() == "ed01c7f25e6a01b23c9f474b9f66f1f204828834bbdbc25efc286d96050c5040"
    cases = json.loads(source)["cases"]
    for case in cases:
        before = deepcopy(case["expected"])
        expected = expected_with_v1_metadata(case["expected"])
        assert case["expected"] == before
        assert evaluate_case(case) == expected
        for name in ("Q_score", "G_score", "V_score", "total_score", "attractiveness_10", "type_adjusted_score_100", "score_hex"):
            assert expected[name] == before[name]
    extra = deepcopy(cases[0]["expected"])
    extra["future_unknown_field"] = {"must_remain": 123}
    assert expected_with_v1_metadata(extra)["future_unknown_field"] == {"must_remain": 123}
    numeric_change = deepcopy(evaluate_case(cases[0]))
    numeric_change["Q_score"] += 1
    assert numeric_change != expected_with_v1_metadata(cases[0]["expected"])
    for mutation in ("policy", "factor_lifecycle", "research_lifecycle", "candidate_order", "already_adopted"):
        bad = deepcopy(cases[0]["expected"])
        if mutation == "policy":
            bad["V_policy_status"] = "CALIBRATED"
        elif mutation == "factor_lifecycle":
            bad["factor_breakdown"]["v_lifecycle"] = "CALIBRATED"
        elif mutation == "research_lifecycle":
            bad["v_candidates"][1]["lifecycle"] = "STANDARD"
        elif mutation == "candidate_order":
            bad["v_candidates"].reverse()
        else:
            bad["standard"] = "v1"
        try:
            expected_with_v1_metadata(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("unexpected lifecycle/schema must not be silently projected: " + mutation)
    assert (DOCS / "golden_cases.json").read_bytes() == source


def test_v1_active_product_descriptions_show_adopted_uncalibrated_v():
    from investment_system.product.render_app import bodies

    pages = bodies()
    for name in ("home", "qgv_analysis"):
        text = pages[name][1]
        assert "STANDARD v1 · UNCALIBRATED" in text
        assert "V production null" not in text
        assert "V_score는 생산 경로에서 null" not in text

