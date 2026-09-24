from investment_system.contracts.enums import CalibrationLifecycle, CoverageState, ProfileKind, QualityState
from investment_system.contracts.models import FactorObservation
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import Q_WEIGHTS, validate_q_g_weights
from investment_system.qgv.scoring import production_v_score, score_q
from tests.helpers import AS_OF, complete_obs


def test_q_weights_sum_to_one():
    validate_q_g_weights()
    assert abs(sum(Q_WEIGHTS.values()) - 1) < 1e-12


def test_q7_is_management_quality_not_capital_allocation():
    assert "management_quality" in Q_WEIGHTS
    assert "capital_allocation" not in Q_WEIGHTS


def test_missing_factor_is_not_zero():
    obs = complete_obs()
    obs["competitive_advantage"] = FactorObservation(
        "competitive_advantage", None, None, QualityState.MISSING_DATA, None
    )
    score, cov, notes = score_q(obs, ProfileKind.GENERAL_CORPORATE)
    assert score is not None
    assert score < 70
    assert cov == CoverageState.PARTIAL
    assert any("MISSING" in n or "competitive_advantage" in n for n in notes)


def test_blocked_dependency_blocks_q():
    obs = complete_obs()
    obs["roic_wacc"] = FactorObservation("roic_wacc", None, None, QualityState.BLOCKED_DEPENDENCY, None)
    score, cov, _ = score_q(obs, ProfileKind.GENERAL_CORPORATE)
    assert score is None
    assert cov == CoverageState.BLOCKED


def test_financial_profile_skips_roic():
    obs = complete_obs()
    del obs["roic_wacc"]
    score, cov, notes = score_q(obs, ProfileKind.FINANCIAL)
    assert score is not None
    assert any("NOT_APPLICABLE" in n for n in notes)


def test_production_v_is_provisional_initial_prior():
    engine = AnalysisEngine()
    snap = engine.analyze("nvda", AS_OF, complete_obs(), synthetic=True, key_drivers=("scale", "cuda"))
    assert snap.V_score == 70
    assert snap.V_policy_status == CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR
    assert snap.Q_score == 70
    assert snap.G_score == 70
    assert snap.synthetic is True
    assert len(snap.v_candidates) >= 1
    v, policy = production_v_score(snap.v_candidates, snap.V_score)
    assert v == 70 and policy == CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR


def test_snapshot_contract_fields():
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(), synthetic=True)
    d = snap.to_dict()
    assert d["qgv_analysis_contract"] == "v1.7.6"
    assert d["implementation_kind"] == "NEW IMPLEMENTATION"
    assert "qgv_snapshot_id" in d
