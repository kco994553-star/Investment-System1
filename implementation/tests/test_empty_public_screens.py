"""The empty-public-screens fixture used by browser tests must equal what an offline build publishes."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_empty_public_screens_fixture_is_current():
    result = subprocess.run([sys.executable, str(ROOT / 'tools/empty_public_screens.py'), '--check'], capture_output=True, text=True)
    assert result.stdout.strip() == 'EMPTY_PUBLIC_SCREENS_OK', 'run: python tools/empty_public_screens.py'
