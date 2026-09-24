from pathlib import Path

from investment_system.validation.e2e import run_integrated_e2e, run_live_candidate


def test_integrated_e2e_reload_and_immutable_outcome(tmp_path):
    result = run_integrated_e2e(path=tmp_path / "track_store.json")
    assert result["reloaded"] is True
    assert result["parent_immutable"] is True
    assert result["decision_source"] == "integration"
    assert result["official_pass"] is False
    assert result["real_data_verified"] is False
    assert result["names"] == 17
    store = Path(result["store_path"])
    assert store.exists() and store.stat().st_size > 0


def test_live_candidate_never_self_promotes():
    result = run_live_candidate(("nvda",))
    assert result["real_data_verified"] is False
    assert result["stage2"] is False
    assert result["kind"] == "REAL_DATA_CANDIDATE"
