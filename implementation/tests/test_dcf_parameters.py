"""Adopted DCF defaults: v1.1 (current) and v1 (history) values, validator, growth rule, device copy equality, type_config untouched."""
import copy
import json
from pathlib import Path
import subprocess
import pytest

from investment_system.qgv.dcf import reverse_dcf, two_stage_dcf
from investment_system.qgv.dcf_parameters import (
    explicit_growth, load_default_dcf_parameters, load_v1_dcf_parameters, validate_dcf_parameters,
)

BASE = Path(__file__).resolve().parents[1] / 'src/investment_system'


def test_v1_1_values_match_user_decision_2026_10_11():
    p = load_default_dcf_parameters()
    assert p['status'] == 'V1_1_UNCALIBRATED_DEFAULT' and p['confirmed'] is True and p['config_version'] == 'dcf_parameters/v1.1-default'
    assert p['supersedes'] == 'dcf_parameters/v1-default'
    assert (p['explicit_years'], p['discount_rate'], p['terminal_growth']) == (5, 0.10, 0.02)
    assert (p['solver']['growth_lower'], p['solver']['growth_upper']) == (-0.5, 1.0)
    assert (p['solver']['relative_price_tolerance'], p['solver']['maximum_iterations']) == (1e-10, 200)
    assert (p['cashflow_basis'], p['discount_rate_basis'], p['share_basis'], p['fcfe_definition']) == ('FCFE_PER_SHARE', 'COST_OF_EQUITY', 'WEIGHTED_AVERAGE_DILUTED', 'fcfe/1.1')
    assert p['explicit_growth_rule'] == {'kind': 'REVENUE_CAGR_3Y_CLAMP', 'metric': 'revenue_cagr_3y', 'lower': 0.0, 'upper': 0.15, 'status': 'PROVISIONAL'}
    assert p['output_version'] == 'v1+dcf_v1_1_default' and p['currency'] == 'USD'


def test_v1_is_kept_as_history_unchanged():
    p = load_v1_dcf_parameters()
    assert p['status'] == 'V1_UNCALIBRATED_DEFAULT' and p['config_version'] == 'dcf_parameters/v1-default'
    assert p['explicit_growth'] is None and p['explicit_growth_status'] == 'EXPLICIT_GROWTH_UNDECIDED'
    assert p['output_version'] == 'v1+dcf_v1_default' and p['fcfe_definition'] == 'fcfe/1'


@pytest.mark.parametrize('cagr,expected', [(0.08, 0.08), (0.31, 0.15), (-0.04, 0.0), (0.0, 0.0), (0.15, 0.15)])
def test_explicit_growth_is_the_clamped_own_revenue_cagr(cagr, expected):
    assert explicit_growth(load_default_dcf_parameters(), cagr) == (expected, None)


def test_explicit_growth_is_never_invented():
    p = load_default_dcf_parameters()
    for missing in (None, float('nan'), float('inf'), True, '0.1'):
        assert explicit_growth(p, missing) == (None, 'EXPLICIT_GROWTH_NOT_AVAILABLE')
    assert explicit_growth(load_v1_dcf_parameters(), 0.08) == (None, 'EXPLICIT_GROWTH_UNDECIDED')
    bad = copy.deepcopy(p)
    bad['explicit_growth_rule']['upper'] = -0.1
    assert explicit_growth(bad, 0.08) == (None, 'EXPLICIT_GROWTH_RULE_INVALID')


def test_defaults_drive_the_existing_dcf_engine():
    p = load_default_dcf_parameters()
    value = two_stage_dcf(cashflow_per_share=1.0, growth_rate=0.07, parameters=p, cashflow_currency='USD').value_per_share
    r = reverse_dcf(cashflow_per_share=1.0, price=value, parameters=p, cashflow_currency='USD', price_currency='USD')
    assert r.state == 'PROVISIONAL' and r.implied_growth == pytest.approx(0.07, abs=1e-9)
    # No currency conversion: an EUR cash flow against the USD basis stays unavailable.
    assert two_stage_dcf(cashflow_per_share=1.0, growth_rate=0.07, parameters=p, cashflow_currency='EUR').reason_codes == ('CURRENCY_BASIS_UNCONFIRMED',)


@pytest.mark.parametrize('mutate,code', [
    (lambda p: p.update(confirmed=False), 'PARAMETERS_STATUS'),
    (lambda p: p.update(output_version='v1+dcf_v1_default'), 'PARAMETERS_STATUS'),
    (lambda p: p.update(discount_rate=0.02), 'PARAMETERS_RATES'),
    (lambda p: p.update(explicit_years=5.0), 'PARAMETERS_YEARS'),
    (lambda p: p['explicit_growth_rule'].update(upper=-0.5), 'PARAMETERS_EXPLICIT_GROWTH'),
    (lambda p: p['explicit_growth_rule'].update(kind='FIXED'), 'PARAMETERS_EXPLICIT_GROWTH'),
    (lambda p: p['explicit_growth_rule'].update(status='CONFIRMED'), 'PARAMETERS_EXPLICIT_GROWTH'),
    (lambda p: p['solver'].update(growth_lower=1.5), 'PARAMETERS_SOLVER'),
    (lambda p: p.update(cashflow_basis='FCFF'), 'PARAMETERS_BASIS'),
    (lambda p: p.update(fcfe_definition='fcfe/1'), 'PARAMETERS_BASIS'),
    (lambda p: p.update(extra=1), 'PARAMETERS_SHAPE'),
    (lambda p: p.update(explicit_growth=0.05), 'PARAMETERS_SHAPE'),
])
def test_validator_fails_closed(mutate, code):
    p = copy.deepcopy(load_default_dcf_parameters())
    mutate(p)
    assert code in validate_dcf_parameters(p)


def test_v1_history_validator_still_fails_closed():
    p = copy.deepcopy(load_v1_dcf_parameters())
    p['explicit_growth'] = 0.05
    assert 'PARAMETERS_EXPLICIT_GROWTH' in validate_dcf_parameters(p)


def test_device_copy_matches_python_source():
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(BASE / 'product/web_assets/dcf-parameters-defaults.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == json.loads((BASE / 'qgv/dcf_parameters_v1_1_default.json').read_text())


def test_js_explicit_growth_matches_python():
    script = ("const v=require(process.argv[1]),p=require(process.argv[2]);"
              "process.stdout.write(JSON.stringify([0.08,0.31,-0.04,null,0.15].map(c=>v.explicitGrowth(p,c))))")
    out = json.loads(subprocess.run(['node', '-e', script, str(BASE / 'product/web_assets/device-valuation.js'),
                                     str(BASE / 'product/web_assets/dcf-parameters-defaults.js')], capture_output=True, text=True, check=True).stdout)
    p = load_default_dcf_parameters()
    assert out == [list(explicit_growth(p, c)) for c in (0.08, 0.31, -0.04, None, 0.15)]


def test_official_type_config_dcf_block_is_untouched():
    # GSQ-017: type_config/1 is immutable; the adopted defaults live only in dcf_parameters/*.
    block = json.loads((BASE / 'qgv/type_config_v1.json').read_text())['dcf']
    assert block == {'explicit_years': 5, 'discount_rate': None, 'terminal_growth': None, 'confirmed': False, 'cashflow_basis': None}
