from datetime import date
import pytest

from investment_system.qgv.g_horizon import (
    DEFAULT_G_HORIZON, GHorizonConfig, QuarterlyFundamentalPoint,
    assess_horizon, quarterly_monitor,
)


def test_default_is_3y_and_meaning_is_structural_growth():
    c = GHorizonConfig()
    assert DEFAULT_G_HORIZON == "3Y"
    assert c.requested_quarters == 12
    assert c.meaning["label_en"] == "Structural Growth"


def test_supported_quarter_and_year_horizons_and_custom():
    assert [GHorizonConfig(h).requested_quarters for h in ("1Q", "2Q", "4Q", "2Y", "3Y", "5Y")] == [1, 2, 4, 8, 12, 20]
    assert GHorizonConfig("CUSTOM", 7).requested_quarters == 7
    with pytest.raises(ValueError):
        GHorizonConfig("CUSTOM")


def test_insufficient_history_is_partial_not_fabricated_full_horizon():
    c = assess_horizon(GHorizonConfig("5Y"), available_quarters=8)
    assert c.coverage_state == "PARTIAL"
    assert c.requested_quarters == 20
    assert c.effective_quarters == 8
    assert c.coverage_ratio == 0.4
    assert c.fallback_used is True


def test_quarterly_monitor_reports_qoq_yoy_and_acceleration_as_raw_evidence():
    pts = [
        QuarterlyFundamentalPoint(date(2025,3,31),100,1.00,0.80),
        QuarterlyFundamentalPoint(date(2025,6,30),110,1.05,0.85),
        QuarterlyFundamentalPoint(date(2025,9,30),120,1.10,0.90),
        QuarterlyFundamentalPoint(date(2025,12,31),130,1.15,0.95),
        QuarterlyFundamentalPoint(date(2026,3,31),120,1.20,1.00),
        QuarterlyFundamentalPoint(date(2026,6,30),143,1.31,1.10),
    ]
    m = quarterly_monitor(pts)
    assert m["quarter_count"] == 6
    assert m["revenue"]["qoq"] == pytest.approx(143/120-1)
    assert m["revenue"]["yoy"] == pytest.approx(143/110-1)
    assert m["revenue"]["yoy_acceleration"] == pytest.approx((143/110-1) - (120/100-1))
    assert "does not mutate Frozen G score" in m["note"]
