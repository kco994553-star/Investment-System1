"""Python reference for the device value view: fixture currency, fixed semantics, Node parity."""
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / 'tests/fixtures/device_valuation_reference_v1.json'


def tool():
    spec = importlib.util.spec_from_file_location('device_valuation_reference', ROOT / 'tools/device_valuation_reference.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cases():
    return json.loads(FIXTURE.read_text())['cases']


def same(a, e):
    if type(e) is dict:
        assert set(a) == set(e)
        for k in e:
            same(a[k], e[k])
    elif type(e) is list:
        assert len(a) == len(e)
        for x, y in zip(a, e):
            same(x, y)
    elif type(e) in (int, float):
        assert type(a) in (int, float) and a == pytest.approx(e, rel=1e-10, abs=1e-10)
    else:
        assert type(a) is type(e) and a == e


def test_fixture_inputs_are_current_generator_output():
    assert [{k: c[k] for k in ('id', 'synthetic', 'operation', 'input')} for c in cases()] == tool().cases()


@pytest.mark.parametrize('case', cases(), ids=lambda c: c['id'])
def test_python_reference_replays_golden(case):
    same(tool().replay(case), case['expected'])


def test_semantics_fixed_by_decision():
    by = {c['id']: c['expected'] for c in cases()}
    for e in by.values():
        # Forward DCF and DCF margin of safety: explicit growth h undecided.
        assert e['dcf'] == {'state': 'NOT_AVAILABLE', 'reason_codes': ['EXPLICIT_GROWTH_UNDECIDED'], 'value_per_share': None}
        assert e['v_factors']['margin_of_safety'] == {'score': None, 'state': 'NOT_AVAILABLE', 'reason': 'EXPLICIT_GROWTH_UNDECIDED'}
        assert e['role'] == 'RAM_ONLY_DEVICE' and 'price' not in json.dumps(e).replace('PRICE', '')
        # Reverse DCF V factor only from a solved implied growth, never the legacy P/E proxy.
        if e['reverse_dcf']['implied_growth'] is None:
            assert e['v_factors']['reverse_dcf']['state'] == 'NOT_AVAILABLE'
    assert by['full']['version'] == 'v1+dcf_v1_default' and by['custom-parameters-versioned']['version'] == 'v1+dcf_custom'
    assert -0.5 < by['full']['reverse_dcf']['implied_growth'] < 1.0
    assert by['price-above-bracket-no-pe-proxy']['v_factors']['reverse_dcf']['reason'] == 'REVERSE_DCF_NOT_AVAILABLE'
    assert by['no-device-price']['reverse_dcf']['reason_codes'] == ['NO_DEVICE_PRICE']


def test_live_cases_refused():
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        tool().replay({'synthetic': False})


def test_node_port_matches_every_vector():
    out = subprocess.run(['node', str(ROOT / 'tools/device_valuation_node_test.js')], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]
