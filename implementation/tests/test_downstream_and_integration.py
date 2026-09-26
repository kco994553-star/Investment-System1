from datetime import datetime, timezone

import pytest

from investment_system.contracts.enums import GateDecision, MacroState
from investment_system.integration.engine import IntegrationEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.compatibility import CompatibilityHarness
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.portfolio import PortfolioEngine
from investment_system.qgv.track_record import ImmutableTrackRecordError, TrackRecordStore
from investment_system.technical.engine import TechnicalEngine
from investment_system.versions import MACRO_CONFIRMED
from tests.helpers import AS_OF, complete_obs


def test_leaderboard_does_not_recompute_qgv():
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(), synthetic=True)
    lb = LeaderboardEngine().build("us500", AS_OF, [snap])
    assert lb.recomputed_qgv is False
    assert lb.rows[0].qgv_snapshot_id == snap.qgv_snapshot_id
    assert lb.rows[0].Q_score == snap.Q_score


def test_track_record_immutable_and_outcome_is_new_record():
    store = TrackRecordStore()
    rec = store.record_decision("ANALYSIS", "nvda", AS_OF, ("qgv_x",), {"Q": 70})
    with pytest.raises(ImmutableTrackRecordError):
        store.overwrite(rec.track_record_id, payload={"Q": 99})
    child = store.evaluate_outcome(rec.track_record_id, "20D", {"price_return": 0.02})
    assert child.track_record_id != rec.track_record_id
    assert store.get(rec.track_record_id).payload["Q"] == 70
    assert child.outcome_metrics["price_return"] == 0.02


def test_technical_does_not_mutate_qgv():
    snap = AnalysisEngine().analyze("nvda", AS_OF, complete_obs(), synthetic=True)
    before = snap.Q_score
    ta = TechnicalEngine().evaluate("nvda", AS_OF, [0.01, 0.02, -0.01, 0.03, 0.02], qgv=snap)
    assert ta.mutated_qgv is False
    assert snap.Q_score == before
    assert ta.qgv_snapshot_id_ref == snap.qgv_snapshot_id


def test_macro_uses_confirmed_not_candidate():
    mac = MacroEngine().evaluate(AS_OF, {"growth": 0.04, "inflation": 0.02})
    assert mac.macro_version == MACRO_CONFIRMED
    assert mac.mutated_qgv is False
    assert "v0.1.4" in mac.environment["candidate_not_applied"]


def test_integration_blocks_on_emergency_macro():
    pf = PortfolioEngine().official_v11(AS_OF)
    tech = {h.company_id: TechnicalEngine().evaluate(h.company_id, AS_OF, [0.0]) for h in list(pf.holdings)[:3]}
    mac = MacroEngine().evaluate(AS_OF, {"growth": -0.02, "inflation": 0.09})
    assert mac.state == MacroState.EMERGENCY
    result = IntegrationEngine().run(AS_OF, pf, tech, mac)
    assert result.gate == GateDecision.BLOCK
    assert result.policy_status == "PROVISIONAL"
    assert all(v == 0.0 for v in result.target_weights.values())
    assert result.order_intents == []


def test_compatibility_does_not_claim_originals():
    inv = CompatibilityHarness().inventory()
    assert all(item["present_in_hub"] is False for item in inv)
    cmp_ = CompatibilityHarness().compare_if_present("qgv-analysis-python", {"pass": 10})
    assert cmp_["status"] == "ORIGINAL_MISSING"


def test_integration_zero_actual_weight_is_a_gap_not_missing():
    """actual_weight 0.0 (position not held) must not be read as 'missing' (falsy); None stays missing (no intent)."""
    from dataclasses import replace

    pf = PortfolioEngine().official_v11(AS_OF)
    first, second = pf.holdings[0], pf.holdings[1]
    holdings = (replace(first, actual_weight=0.0), replace(second, actual_weight=None)) + tuple(pf.holdings[2:])
    pf0 = replace(pf, holdings=holdings)
    mac = MacroEngine().evaluate(AS_OF, {"growth": 0.03, "inflation": 0.02})
    result = IntegrationEngine().run(AS_OF, pf0, {}, mac)
    assert result.gate != GateDecision.BLOCK
    by_id = {o["company_id"]: o for o in result.order_intents}
    assert by_id[first.company_id]["side"] == "BUY" and by_id[first.company_id]["intent_weight"] > 0
    assert second.company_id not in by_id
