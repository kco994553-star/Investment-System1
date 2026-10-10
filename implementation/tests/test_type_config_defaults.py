"""The device copy of the official type configuration must equal the Python source file."""
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parents[1] / 'src/investment_system'


def test_device_type_config_copy_matches_official_json():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(BASE / 'product/web_assets/type-config-defaults.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == json.loads((BASE / 'qgv/type_config_v1.json').read_text())
