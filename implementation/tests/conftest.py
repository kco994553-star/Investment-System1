import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def offline_fred_defaults(monkeypatch):
    """Default tests never probe a real FRED key or make optional CSV requests."""
    from urllib.error import URLError
    from investment_system.providers import fred_alfred, fred_csv

    def unavailable_transport(*args, **kwargs):
        raise URLError("offline synthetic test transport")

    monkeypatch.setattr(fred_alfred, "_key", lambda: None)
    monkeypatch.setattr(fred_csv, "urlopen", unavailable_transport)
