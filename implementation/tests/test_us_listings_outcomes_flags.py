from investment_system.validation.historical import run_us_listings_outcomes


def test_outcome_probe_function_exists_and_is_labeled():
    assert run_us_listings_outcomes.__doc__
    assert "Not REAL-DATA VERIFIED" in run_us_listings_outcomes.__doc__
