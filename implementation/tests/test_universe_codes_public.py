"""Public universe-codes.json: price-free code list for new sheets, strict guard validation and JS parity."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

import pytest

from investment_system.universe.universe_codes import FILENAME, SCHEMA, public_payload, require_universe_codes, source_codes

ROOT = Path(__file__).parents[1]
SETUP = ROOT / 'src/investment_system/product/web_assets/google-sheet-setup.js'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_payload_is_the_reviewed_price_free_list():
    payload = public_payload()
    assert FILENAME == 'universe-codes.json' and payload['schema'] == SCHEMA == 'universe-codes/1'
    assert list(payload) == ['schema', 'codes'] and payload['codes'] == source_codes() and len(payload['codes']) == 504
    assert all(isinstance(code, str) and ':' in code for code in payload['codes'])
    text = json.dumps(payload)
    for word in ('price', 'marketcap', 'rank', 'quantity'):
        assert word not in text.lower()


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(extra=1),
    lambda p: p.update(schema='universe-codes/2'),
    lambda p: p['codes'].append(p['codes'][0]),
    lambda p: p['codes'].__setitem__(0, 'NYSE:mmm'),
    lambda p: p['codes'].__setitem__(0, 'LSE:VOD'),
    lambda p: p['codes'].__setitem__(0, {'code': 'NYSE:MMM', 'price': 1}),
    lambda p: p['codes'].reverse(),
    lambda p: p['codes'].pop(),
    lambda p: p.update(codes=[]),
])
def test_strict_validator_rejects_changes(mutate):
    payload = copy.deepcopy(public_payload())
    mutate(payload)
    with pytest.raises(ValueError):
        require_universe_codes(payload)


def test_build_publishes_it_and_the_guard_checks_it():
    build = load('build_pages_cockpit', ROOT / 'tools/build_pages_cockpit.py')
    guard = load('pages_artifact_guard', ROOT / 'tools/pages_artifact_guard.py')
    with tempfile.TemporaryDirectory() as folder:
        site = Path(folder) / 'site'
        build.build_public_cockpit(site)
        published = json.loads((site / FILENAME).read_text(encoding='utf-8'))
        assert published == public_payload()
        assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
        for bad in ({**published, 'codes': published['codes'][:-1]}, {**published, 'price': 1}):
            (site / FILENAME).write_text(json.dumps(bad), encoding='utf-8')
            receipt = guard.scan_artifact(site)
            assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('universe_codes_boundary') == 1


def test_browser_setup_accepts_the_published_file():
    script = ('const S=require(process.argv[1]);const p=JSON.parse(require("fs").readFileSync(0,"utf8"));'
              'const c=S.codes(p);process.stdout.write(String(c.length));')
    out = subprocess.run(['node', '-e', script, str(SETUP)], input=json.dumps(public_payload()), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout == '504'
