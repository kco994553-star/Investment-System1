from datetime import datetime, timezone

import pytest

from investment_system.contracts.enums import SimulationMode
from investment_system.contracts.models import DataStamp
from investment_system.pit.resolver import PITViolation, require_available
from investment_system.qgv.simulation import SimulationConfig, SimulationEngine

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)


def _stamp(sid, avail):
    return DataStamp(
        data_stamp_id=sid,
        source_provider="fixture",
        source_type="price",
        source_reference="synthetic",
        published_at=avail,
        available_at=avail,
        observed_at=avail,
        synthetic=True,
    )


def test_pit_rejects_future_stamp():
    future = _stamp("f1", datetime(2026, 9, 20, tzinfo=timezone.utc))
    with pytest.raises(PITViolation):
        require_available(future, AS_OF)


def test_simulation_rejects_lookahead():
    engine = SimulationEngine()
    cfg = SimulationConfig(
        mode=SimulationMode.HISTORICAL,
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=AS_OF,
        as_of=AS_OF,
    )
    ok = _stamp("ok", datetime(2026, 6, 1, tzinfo=timezone.utc))
    future = _stamp("bad", datetime(2026, 10, 1, tzinfo=timezone.utc))
    with pytest.raises(PITViolation):
        engine.run(cfg, [ok, future], {"ok": 0.01, "bad": 0.5})


def test_simulation_runs_on_available_stamps():
    engine = SimulationEngine()
    cfg = SimulationConfig(
        mode=SimulationMode.HISTORICAL,
        start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end=AS_OF,
        as_of=AS_OF,
    )
    a = _stamp("a", datetime(2026, 3, 1, tzinfo=timezone.utc))
    b = _stamp("b", datetime(2026, 6, 1, tzinfo=timezone.utc))
    result = engine.run(cfg, [a, b], {"a": 0.10, "b": -0.05})
    assert result.synthetic is True
    assert abs(result.ending_value - 100 * 1.10 * 0.95) < 1e-9
