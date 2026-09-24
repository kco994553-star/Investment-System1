from datetime import datetime, timezone

from investment_system.contracts.enums import StrategyStyle, TrackScope
from investment_system.contracts.models import DataStamp
from investment_system.contracts.strategy import custom_profile, builtin_profile
from investment_system.providers.catalog import iter_official_raw
from investment_system.qgv.portfolio import PortfolioEngine
from investment_system.qgv.simulation import SimulationConfig, SimulationEngine
from investment_system.contracts.enums import SimulationMode
from investment_system.validation.ablation import run_ablation
from investment_system.validation.adapters import MacroAdapter, QGVAdapter, TechnicalAdapter
from investment_system.validation.integrated import run_integrated_session
from investment_system.validation.records import ScopedTrackStore

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_profile_hash_stable_and_custom_blocks_frozen():
    a = builtin_profile(StrategyStyle.BALANCED)
    b = builtin_profile(StrategyStyle.BALANCED)
    assert a.parameter_set_hash() == b.parameter_set_hash()
    assert len(a.parameter_set_hash()) == 64
    assert a.profile_version.endswith("PROVISIONAL")
    try:
        custom_profile({"q_weights": {}})
        assert False
    except ValueError:
        pass
    custom = custom_profile({"cash_buffer": 0.12})
    assert custom.global_style == StrategyStyle.CUSTOM
    assert custom.portfolio.params["cash_buffer"] == 0.12
    assert custom.parameter_set_hash() != a.parameter_set_hash()


def test_adapters_do_not_mutate_qgv():
    raw = next(r for r in iter_official_raw(AS_OF) if r.company_id == "nvda")
    qgv = QGVAdapter().snapshot(raw, AS_OF)
    before = (qgv.Q_score, qgv.G_score, qgv.V_score)
    TechnicalAdapter().snapshot("nvda", AS_OF, [0.01, 0.02], qgv=qgv)
    MacroAdapter().snapshot(AS_OF, {"growth": 0.02, "inflation": 0.02}, qgv=qgv)
    assert (qgv.Q_score, qgv.G_score, qgv.V_score) == before
    assert qgv.V_policy_status.value == "PROVISIONAL_INITIAL_PRIOR"


def test_ablation_and_shared_engine_purpose():
    stamp = DataStamp("s1", "mem", "px", "nvda", AS_OF, AS_OF, AS_OF, synthetic=True)
    table = run_ablation(
        [stamp],
        AS_OF,
        {
            "qgv": {"s1": 0.10},
            "technical": {"s1": 0.02},
            "macro": {"s1": -0.01},
        },
    )
    assert table["official_pass"] is False
    assert "qgv+technical+macro" in table["rows"]
    assert table["rows"]["qgv"]["purpose"] == "VALIDATION_BACKTEST"
    sim = SimulationEngine().run(
        SimulationConfig(SimulationMode.HISTORICAL, AS_OF, AS_OF, AS_OF),
        [stamp],
        {"s1": 0.10},
    )
    assert abs(sim.ending_value - table["rows"]["qgv"]["ending_value"]) < 1e-9


def test_track_record_schema_and_integrated_decision_source():
    store = ScopedTrackStore()
    rec = store.record(
        TrackScope.INTEGRATED,
        "book",
        AS_OF,
        ("snap-q", "snap-t", "snap-m"),
        {
            "profile_id": "profile-balanced-provisional",
            "parameter_set_hash": builtin_profile(StrategyStyle.BALANCED).parameter_set_hash(),
            "prediction": {"gate": "PASS"},
            "decision": {"source": "integration"},
            "evaluation_horizon": "20d",
        },
    )
    assert rec.payload["not_backtest"] is True
    assert rec.payload["prediction_id"]
    assert rec.payload["parameter_set_hash"]
    assert rec.payload["purpose"] == "TRACK_RECORD"
    raws = [r for r in iter_official_raw(AS_OF) if r.company_id == "nvda"]
    qgv = QGVAdapter().snapshot(raws[0], AS_OF)
    tech = {"nvda": TechnicalAdapter().snapshot("nvda", AS_OF, [0.01], qgv)}
    pf = PortfolioEngine().us_working(AS_OF, {"nvda": qgv})
    integ = run_integrated_session(AS_OF, pf, tech, {"growth": 0.02, "inflation": 0.02})
    assert integ["decision_source"] == "integration"
    assert integ["orders_from_modules"] is False
    assert integ["official_pass"] is False
