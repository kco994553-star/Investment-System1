from investment_system.providers import fred_alfred


def test_runtime_key_file_is_outside_repo():
    assert fred_alfred._RUNTIME_KEY_FILE.startswith("/tmp/")
    assert "artifacts" not in fred_alfred._RUNTIME_KEY_FILE
    assert "Investment-System1" not in fred_alfred._RUNTIME_KEY_FILE
