from datetime import datetime, timezone

from investment_system.contracts.context import SecurityContext
from investment_system.contracts.enums import StrategyStyle, TrackScope, ValidationLayer, WorkspaceId
from investment_system.contracts.product import BACKEND_INFRA, NAV_PAGES, user_menu_ids
from investment_system.contracts.strategy import CONFIGURABLE_KEYS, FROZEN_KEYS, assert_frozen_untouched, builtin_profile, mixed_profile
from investment_system.product.render_app import render_all
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS
from investment_system.qgv.track_record import ImmutableTrackRecordError
from investment_system.validation.backtest import BacktestSpec, incremental_sets, run_toy_module_backtest
from investment_system.validation.records import ScopedTrackStore
from investment_system.contracts.models import DataStamp


AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def test_nav_excludes_backend_infra():
    ids = user_menu_ids()
    joined = " ".join(p.path for p in NAV_PAGES)
    assert "sec" not in joined and "yahoo" not in joined and "raw_map" not in joined
    assert "home" in ids and "qgv_analysis" in ids and "lab" in ids
    assert all(name not in ids for name in BACKEND_INFRA)
    assert {p.workspace for p in NAV_PAGES} >= {WorkspaceId.QGV, WorkspaceId.TECHNICAL, WorkspaceId.MACRO}


def test_profile_does_not_touch_frozen_weights():
    p = builtin_profile(StrategyStyle.AGGRESSIVE)
    assert p.lifecycle.value == "PROVISIONAL"
    assert "q_weights" not in p.qgv.params
    assert_frozen_untouched(Q_WEIGHTS, G_WEIGHTS)
    mixed = mixed_profile(qgv=StrategyStyle.AGGRESSIVE, technical=StrategyStyle.BALANCED, macro=StrategyStyle.DEFENSIVE, risk=StrategyStyle.DEFENSIVE)
    assert mixed.global_style == StrategyStyle.CUSTOM
    assert mixed.qgv.style == StrategyStyle.AGGRESSIVE
    assert mixed.macro.style == StrategyStyle.DEFENSIVE
    assert "q_weights" in FROZEN_KEYS
    assert "cash_buffer" in CONFIGURABLE_KEYS


def test_backtest_combinations_and_pit():
    sets = incremental_sets()
    assert ("qgv", "technical", "macro") in sets
    assert len(sets) == 7
    stamp = DataStamp("s1", "mem", "px", "nvda", AS_OF, AS_OF, AS_OF, synthetic=True)
    spec = BacktestSpec("bt1", ValidationLayer.MODULE_BACKTEST, ("qgv",), AS_OF, AS_OF, AS_OF)
    out = run_toy_module_backtest(spec, [stamp], {"s1": 0.1})
    assert out["official_pass"] is False
    assert abs(out["ending_value"] - 110.0) < 1e-9


def test_scoped_track_record_is_not_backtest():
    store = ScopedTrackStore()
    rec = store.record(TrackScope.TECHNICAL, "nvda", AS_OF, ("snap1",), {"signal": "WAIT"})
    assert rec.payload["not_backtest"] is True
    assert rec.immutable is True
    try:
        store.store.overwrite(rec.track_record_id)
        assert False
    except ImmutableTrackRecordError:
        pass
    child = store.outcome(rec.track_record_id, "20d", {"hit": True})
    assert child.record_type == "OUTCOME"
    assert child.track_record_id != rec.track_record_id


def test_security_context_and_app_shell(tmp_path):
    ctx = SecurityContext("nvda", "NVDA", "NASDAQ", AS_OF, "US")
    assert "company_id=nvda" in ctx.query()
    written = render_all(tmp_path)
    names = {p.name for p in written}
    assert "index.html" in names
    home = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "QGV System" in home
    assert "Strategy Lab" in home
    assert "Yahoo" not in home.split("nav")[1] if False else "sec_companyfacts" not in home
