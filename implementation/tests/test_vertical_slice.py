from datetime import datetime, timezone

from investment_system.validation.vertical_slice import rank_cross_section, select_provisional

import pytest
from investment_system.validation import vertical_slice as vs
from investment_system.qgv.portfolio import PortfolioEngine


@pytest.mark.parametrize("mode,value,count", [("all", None, 137), ("top_n", 20, 20), ("top_percent", 10, 13)])
def test_research_selection_reaches_actual_portfolio_without_common_cap(mode, value, count):
    quality = {f"id{i:03}": {"Q": 100 - i / 10, "G": 70, "V": 50} for i in range(137)}
    ranked = rank_cross_section(quality)
    selected = select_provisional(ranked, vs.SelectionPolicy(mode, value))
    at = datetime(2026, 11, 2, tzinfo=timezone.utc)
    book = vs.to_portfolio(selected, at)
    snapshot = PortfolioEngine().from_input(book, at)
    assert len(snapshot.holdings) == count
    assert sum(h.target_weight for h in snapshot.holdings) == pytest.approx(1)
    assert snapshot.holdings[0].target_weight == pytest.approx(1 / count)


def test_policy_preserves_legacy_and_resolves_cutoff_ties_by_company_id():
    ranked = rank_cross_section({"b": {"Q": 80, "G": 70}, "a": {"Q": 80, "G": 70}, "missing": {"Q": 99}})
    assert select_provisional(ranked) == ["b", "a"]
    assert select_provisional(ranked, vs.SelectionPolicy("top_n", 1)) == ["a"]
    assert select_provisional(ranked, vs.SelectionPolicy("top_n", 20)) == ["a", "b"]
    assert select_provisional(ranked, vs.SelectionPolicy("top_percent", 10)) == []
    empty = select_provisional(rank_cross_section({"x": {"G": 90}}), vs.SelectionPolicy("all"))
    assert empty == []
    assert vs.to_portfolio(empty, datetime.now(timezone.utc)) is None


@pytest.mark.parametrize("mode,value", [("unknown", None), ("all", 20), ("top_n", None), ("top_n", 0), ("top_n", True), ("top_n", 2.5), ("top_percent", 0), ("top_percent", 101), ("top_percent", float("nan"))])
def test_invalid_policy_cannot_silently_change_selection(mode, value):
    with pytest.raises(ValueError):
        vs.SelectionPolicy(mode, value)


def test_selection_is_qg_present_not_return_cutoff():
    quality = {
        "a": {"Q": 0.8, "G": 0.7, "V": 0.1},
        "b": {"Q": 0.2, "G": 0.2, "V": 0.9},
        "c": {"Q": 0.9, "G": None, "V": 0.5},
        "d": {"Q": None, "G": None, "V": None},
    }
    ranked = rank_cross_section(quality)
    selected = select_provisional(ranked)
    assert selected == ["a", "b"]
    assert "c" not in selected
    assert ranked[0]["company_id"] == "a"


def test_missing_is_allowed():
    ranked = rank_cross_section({"gev": {"Q": None, "G": None, "V": None}})
    assert select_provisional(ranked) == []
    assert ranked[0]["eligible"] is False
