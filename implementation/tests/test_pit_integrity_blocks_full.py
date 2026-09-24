from investment_system.validation.historical import pit_integrity_report

def test_companyfacts_restatement_blocks_full_pit():
    report = pit_integrity_report({"rows": [], "official_pass": False})
    assert report["full_pit_pass"] is False
    assert report["ladder_rung"] == "PIT_PROBE"
    assert "SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED" in report["blocking_gaps"]
    assert report["calibrated"] is False
