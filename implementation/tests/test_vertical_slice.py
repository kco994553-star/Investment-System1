from datetime import datetime, timezone

from investment_system.validation.vertical_slice import rank_cross_section, select_provisional


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
