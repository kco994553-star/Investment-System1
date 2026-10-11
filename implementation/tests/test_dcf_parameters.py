"""Adopted DCF defaults (dcf_parameters/v1-default): values, validator, device copy equality, type_config untouched."""
import copy
import json
from pathlib import Path
import subprocess
import pytest

from investment_system.qgv.dcf import reverse_dcf, two_stage_dcf
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters, validate_dcf_parameters

BASE = Path(__file__).resolve().parents[1] / 'src/investment_system'


def test_values_match_user_decision_2026_10_11():
    p = load_default_dcf_parameters()
    assert p['status'] == 'V1_UNCALIBRATED_DEFAULT' and p['confirmed'] is True and p['config_version'] == 'dcf_parameters/v1-default'
    assert (p['explicit_years'], p['discount_rate'], p['terminal_growth']) == (5, 0.10, 0.02)
    assert (p['solver']['growth_lower'], p['solver']['growth_upper']) == (-0.5, 1.0)
    assert (p['solver']['relative_price_tolerance'], p['solver']['maximum_iterations']) == (1e-10, 200)
    assert (p['cashflow_basis'], p['discount_rate_basis'], p['share_basis'], p['fcfe_definition']) == ('FCFE_PER_SHARE', 'COST_OF_EQUITY', 'WEIGHTED_AVERAGE_DILUTED', 'fcfe/1')
    # Explicit-period growth h is undecided; no value is invented.
    assert p['explicit_growth'] is None and p['explicit_growth_status'] == 'EXPLICIT_GROWTH_UNDECIDED'
    assert p['output_version'] == 'v1+dcf_v1_default'


def test_defaults_drive_the_existing_dcf_engine():
    p = load_default_dcf_parameters()
    value = two_stage_dcf(cashflow_per_share=1.0, growth_rate=0.07, parameters=p, cashflow_currency='USD').value_per_share
    r = reverse_dcf(cashflow_per_share=1.0, price=value, parameters=p, cashflow_currency='USD', price_currency='USD')
    assert r.state == 'PROVISIONAL' and r.implied_growth == pytest.approx(0.07, abs=1e-9)


@pytest.mark.parametrize('mutate,code', [
    (lambda p: p.update(confirmed=False), 'PARAMETERS_STATUS'),
    (lambda p: p.update(discount_rate=0.02), 'PARAMETERS_RATES'),
    (lambda p: p.update(explicit_years=5.0), 'PARAMETERS_YEARS'),
    (lambda p: p.update(explicit_growth=0.05), 'PARAMETERS_EXPLICIT_GROWTH'),
    (lambda p: p['solver'].update(growth_lower=1.5), 'PARAMETERS_SOLVER'),
    (lambda p: p.update(cashflow_basis='FCFF'), 'PARAMETERS_BASIS'),
    (lambda p: p.update(extra=1), 'PARAMETERS_SHAPE'),
])
def test_validator_fails_closed(mutate, code):
    p = copy.deepcopy(load_default_dcf_parameters())
    mutate(p)
    assert code in validate_dcf_parameters(p)


def test_device_copy_matches_python_source():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(BASE / 'product/web_assets/dcf-parameters-defaults.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == json.loads((BASE / 'qgv/dcf_parameters_v1_default.json').read_text())


def test_official_type_config_dcf_block_is_untouched():
    # GSQ-017: type_config/1 is immutable; the adopted defaults live only in dcf_parameters/v1-default.
    block = json.loads((BASE / 'qgv/type_config_v1.json').read_text())['dcf']
    assert block == {'explicit_years': 5, 'discount_rate': None, 'terminal_growth': None, 'confirmed': False, 'cashflow_basis': None}
