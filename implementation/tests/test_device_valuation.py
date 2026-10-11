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
    inputs = {c['id']: c['input'] for c in cases()}
    for i, e in by.items():
        assert e['role'] == 'RAM_ONLY_DEVICE' and 'price' not in json.dumps(e).replace('PRICE', '')
        # Reverse DCF V factor only from a solved implied growth, never the legacy P/E proxy.
        if e['reverse_dcf']['implied_growth'] is None:
            assert e['v_factors']['reverse_dcf']['state'] == 'NOT_AVAILABLE'
        # Margin of safety only from the approved DCF branch; never the 12 x EPS fallback.
        if e['dcf']['value_per_share'] is None:
            assert e['v_factors']['margin_of_safety'] == {'score': None, 'state': 'NOT_AVAILABLE', 'reason': 'DCF_NOT_AVAILABLE'}
        # h is the own 3y revenue CAGR clamped to [0, 0.15], or nothing.
        g = e['explicit_growth']
        cagr = (inputs[i]['row'] or {}).get('v_inputs', {}).get('revenue_cagr_3y')
        if g['state'] == 'PROVISIONAL':
            assert g['value'] == min(0.15, max(0.0, cagr)) and g['revenue_cagr_3y'] == cagr and g['clamped'] == (g['value'] != cagr)
        else:
            assert g['value'] is None and g['clamped'] is None and len(g['reason_codes']) == 1
            assert e['dcf']['state'] == 'NOT_AVAILABLE' and g['reason_codes'][0] in e['dcf']['reason_codes']
    full = by['full']
    assert full['version'] == 'v1+dcf_v1_1_default' and by['custom-parameters-versioned']['version'] == 'v1+dcf_custom'
    assert full['explicit_growth']['value'] == 0.08 and full['dcf']['state'] == 'PROVISIONAL' and full['dcf']['value_per_share'] > 0
    # The approved raw_map DCF branches (central: /0.4; margin of safety: 0.75 x value, /0.3) with the transient price 100.
    v = full['dcf']['value_per_share']
    assert full['v_factors']['fundamental_value']['score'] == pytest.approx(min(100, max(0, 50 + (v / 100 - 1) / 0.4 * 50)))
    assert full['v_factors']['margin_of_safety']['score'] == pytest.approx(min(100, max(0, 50 + (0.75 * v / 100 - 1) / 0.3 * 50)))
    assert -0.5 < full['reverse_dcf']['implied_growth'] < 1.0
    assert by['cagr-above-upper-clamped']['explicit_growth'] == {'state': 'PROVISIONAL', 'reason_codes': [], 'value': 0.15, 'revenue_cagr_3y': 0.31, 'clamped': True}
    assert by['cagr-negative-clamped-to-lower']['explicit_growth']['value'] == 0.0
    assert by['cagr-inside-range-unclamped']['explicit_growth']['clamped'] is False
    assert by['cagr-missing-dcf-not-available']['dcf'] == {'state': 'NOT_AVAILABLE', 'reason_codes': ['EXPLICIT_GROWTH_NOT_AVAILABLE'], 'value_per_share': None}
    assert by['cagr-missing-dcf-not-available']['v_factors']['fundamental_value']['state'] == 'CALCULATED'  # approved EPS branch
    # The forward DCF is price-free: it exists without a device price, but nothing price-relative does.
    assert by['no-device-price']['dcf']['state'] == 'PROVISIONAL' and by['no-device-price']['v_factors']['margin_of_safety']['reason'] == 'MISSING_PRICE'
    assert by['no-device-price']['reverse_dcf']['reason_codes'] == ['NO_DEVICE_PRICE']
    # No FX: an EUR filer against a USD price or the USD basis stays unavailable.
    eur = by['ifrs-eur-filer-usd-price-no-fx']
    assert eur['dcf']['reason_codes'] == ['CURRENCY_BASIS_UNCONFIRMED'] and eur['reverse_dcf']['reason_codes'] == ['CURRENCY_BASIS_UNCONFIRMED']
    assert eur['v_factors']['fundamental_value']['reason'] == 'BASIS_UNCONFIRMED'
    assert by['price-currency-mismatch']['v_factors']['margin_of_safety']['reason'] == 'BASIS_UNCONFIRMED'
    assert by['zero-fcfe-dcf-value-zero']['v_factors']['margin_of_safety']['reason'] == 'DCF_VALUE_ZERO'
    assert by['v1-history-parameters-growth-undecided']['version'] == 'v1+dcf_v1_default'
    assert by['v1-history-parameters-growth-undecided']['dcf']['reason_codes'] == ['EXPLICIT_GROWTH_UNDECIDED']
    assert by['invalid-growth-rule']['dcf']['reason_codes'] == ['EXPLICIT_GROWTH_RULE_INVALID']
    assert by['price-above-bracket-no-pe-proxy']['v_factors']['reverse_dcf']['reason'] == 'REVERSE_DCF_NOT_AVAILABLE'


def test_live_cases_refused():
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        tool().replay({'synthetic': False})


def test_node_port_matches_every_vector():
    out = subprocess.run(['node', str(ROOT / 'tools/device_valuation_node_test.js')], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-2000:]
