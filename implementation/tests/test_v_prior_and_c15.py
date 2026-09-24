from dataclasses import replace

from investment_system.contracts.enums import CalibrationLifecycle, TechnicalRegime
from investment_system.integration.compatibility import CompatibilityLabel, annotate
from investment_system.qgv.factors import V_INITIAL_PRIOR, validate_v_candidate_weights
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.raw_map import _central_value_score, _mos_score
from investment_system.technical.engine import TechnicalEngine
from tests.helpers import AS_OF, complete_obs
from investment_system.qgv.analysis import AnalysisEngine


def test_initial_prior_weights_and_lifecycle():
    assert abs(sum(V_INITIAL_PRIOR.values()) - 1.0) < 1e-12
    assert validate_v_candidate_weights(V_INITIAL_PRIOR) == []
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs())
    assert snap.V_policy_status == CalibrationLifecycle.PROVISIONAL_INITIAL_PRIOR
    assert snap.V_policy_status.value not in {"STANDARD", "CALIBRATED", "VALIDATED"}


def test_fv_and_mos_are_not_identical(tmp_path=None):
    from investment_system.contracts.models import DataStamp
    from investment_system.contracts.raw import RawFundamentals
    from datetime import timezone

    stamp = DataStamp("s", "mem", "fundamentals", "x", AS_OF, AS_OF, AS_OF, False, (), True)
    raw = RawFundamentals("nvda", stamp, dcf_value=120.0, price=100.0, eps=5.0)
    assert _central_value_score(raw) != _mos_score(raw)


def test_technical_ignores_qgv_scores():
    qgv_hi = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(90))
    qgv_lo = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(10))
    rets = [0.01] * 8
    a = TechnicalEngine().evaluate("nvda", AS_OF, rets, qgv=qgv_hi, synthetic=True)
    b = TechnicalEngine().evaluate("nvda", AS_OF, rets, qgv=qgv_lo, synthetic=True)
    c = TechnicalEngine().evaluate("nvda", AS_OF, rets, qgv=None, synthetic=True)
    assert a.regime == b.regime == c.regime
    assert a.execution_zone == b.execution_zone == c.execution_zone
    assert a.mutated_qgv is False
    note = annotate(qgv_hi, a)
    assert note["mutates_qgv"] is False
    assert note["emits_target_weight"] is False
    assert note["label"] in {x.value for x in CompatibilityLabel}
