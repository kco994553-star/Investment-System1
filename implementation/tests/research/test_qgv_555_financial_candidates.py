"""Public synthetic examples: no company data or prices from held sources."""
from copy import deepcopy

import pytest

from investment_system.research.qgv_555_financial_candidates import (
    MINIMUM_PEERS, ROLE_WEIGHTS, VERSION, evaluate_raw, formula_expression, registry,
)


def context(template='BANK'):
    return dict(issuer_id='synthetic-issuer', security_id=None,
        accounting_template=template, valuation_date='2026-11-04',
        as_of='2026-11-14T00:00:00Z')


def value(number, *, period='INSTANT', end='2025-12-31', start=None, common=False):
    out = dict(value=number, period_kind=period, period_end=end,
        unit='USD', currency='USD', issuer_id='synthetic-issuer', scope='CONSOLIDATED',
        available_at='2026-02-01T00:00:00Z', retrieved_at='2026-02-02T00:00:00Z',
        provenance=['synthetic:source'], status='VALID')
    if start:
        out['period_start'] = start
    if common:
        out['equity_basis'] = 'COMMON_EXCLUDING_PREFERRED_NCI'
    return out


def fields():
    return dict(net_income_common=value(12, period='TTM', start='2025-01-01', common=True),
        net_income=value(15, period='TTM', start='2025-01-01'),
        common_equity_begin=value(80, end='2024-12-31', common=True),
        common_equity_end=value(120, common=True),
        assets_begin=value(900, end='2024-12-31'), assets_end=value(1000))


def test_registry_keeps_fifteen_questions_without_inventing_fifteen_formulas():
    reg = registry()
    assert reg['candidate_version'] == VERSION
    assert MINIMUM_PEERS == 8
    assert not reg['official'] and not reg['enabled_as_default']
    for recipe in reg['recipes'].values():
        assert len(recipe['roles']) == 15
        assert not recipe['definition_complete']
        assert all(sum(weights.values()) == 100 for weights in ROLE_WEIGHTS.values())
        for axis in 'QGV':
            assert sum(r['weight'] for r in recipe['roles'].values() if r['axis'] == axis) == 100
        for role in recipe['roles'].values():
            assert role['evidence_refs']
            if role['definition_status'] == 'PREPARING':
                assert role['basic_variant'] is None and role['formula'] is None
    reg['recipes']['BANK']['roles']['q_profitability']['weight'] = 0
    assert registry()['recipes']['BANK']['roles']['q_profitability']['weight'] == 25


def test_defined_ratios_reuse_kernel_with_hand_calculated_expectations():
    original = fields()
    out = evaluate_raw('BANK', original, context())
    assert out['roles']['q_profitability']['value'] == pytest.approx(12 / 100)
    assert out['roles']['q_financial_safety']['value'] == pytest.approx(120 / 1000)
    assert out['roles']['q_moat_proxy']['status'] == 'PREPARING'
    assert out['axes'] == dict(Q=None, G=None, V=None)
    assert out['total'] is None and out['rank'] is None and not out['candidate_adopted']
    assert not out['raw_calculation_requires_peer_sample']
    assert fields() == original


def test_no_consolidated_income_or_parent_equity_substitution():
    f = fields()
    del f['net_income_common']
    assert evaluate_raw('BANK', f, context())['roles']['q_profitability']['status'] == 'MISSING_INPUT'
    f = fields()
    del f['net_income_common']['equity_basis']
    assert evaluate_raw('BANK', f, context())['roles']['q_profitability']['status'] == 'COMMON_ATTRIBUTION_UNCONFIRMED'
    f = fields()
    f['common_equity_end']['equity_basis'] = 'TOTAL_EQUITY'
    assert evaluate_raw('BANK', f, context())['roles']['q_financial_safety']['value'] is None


@pytest.mark.parametrize('change,status', [
    ('future', 'NOT_YET_AVAILABLE'), ('unit', 'UNIT_MISMATCH'),
    ('currency', 'CURRENCY_MISMATCH'), ('period', 'PERIOD_MISMATCH'),
    ('conflict', 'LATEST_FILING_CONFLICT'),
])
def test_invalid_common_inputs_remain_null(change, status):
    f = fields()
    if change == 'future':
        f['net_income_common']['available_at'] = '2027-01-01T00:00:00Z'
    elif change == 'unit':
        f['net_income_common']['unit'] = 'shares'
    elif change == 'currency':
        f['net_income_common'].update(unit='EUR', currency='EUR')
    elif change == 'period':
        f['common_equity_begin']['period_end'] = '2025-01-31'
    else:
        f['net_income_common']['status'] = 'LATEST_FILING_CONFLICT'
    role = evaluate_raw('BANK', f, context())['roles']['q_profitability']
    assert role['value'] is None and role['status'] == status


def test_negative_common_income_is_valid_signed_measure_not_missing():
    f = fields()
    f['net_income_common']['value'] = -12
    role = evaluate_raw('BANK', f, context())['roles']['q_profitability']
    assert role['value'] == pytest.approx(-.12)
    assert role['status'] == 'VALID_NEGATIVE'


def test_insurance_submodels_and_reit_models_are_distinct():
    models = registry()['recipes']
    life = models['LIFE_INSURANCE']['roles']['q_earnings_quality']
    pc = models['PROPERTY_CASUALTY_INSURANCE']['roles']['q_earnings_quality']
    assert life['reason'] != pc['reason']
    assert life['basic_variant'] is None and pc['basic_variant'] is None
    equity = models['EQUITY_REIT']['roles']
    mortgage = models['MORTGAGE_REIT']['roles']
    assert equity['v_earnings_yield']['basic_variant'] == 'nareit_ffo_mcap'
    assert mortgage['v_earnings_yield']['basic_variant'] == 'ep_ttm_diluted'
    assert equity['v_fcf_yield']['basic_variant'] is None  # AFFO is not CFO.
    assert models['BANK']['roles']['v_fcf_yield']['basic_variant'] is None


def test_context_must_match_confirmed_accounting_model_and_price_identity_is_not_filled():
    with pytest.raises(ValueError, match='ACCOUNTING_MODEL_CONTEXT_MISMATCH'):
        evaluate_raw('BANK', fields(), context('GENERAL'))
    with pytest.raises(ValueError, match='UNKNOWN_FINANCIAL_RESEARCH_MODEL'):
        evaluate_raw('UNKNOWN', fields(), context())
    f = fields()
    f['eps_ttm_diluted'] = value(2, period='TTM', start='2025-01-01')
    f['eps_ttm_diluted']['unit'] = 'USD/share'
    f['price'] = value(10, period='PRICE', end='2026-11-04')
    f['price']['unit'] = 'USD/share'
    assert evaluate_raw('BANK', f, context())['roles']['v_earnings_yield']['status'] == 'SCOPE_MISMATCH'


def test_proxy_is_not_direct_measure_and_missing_role_weight_is_not_redistributed():
    reg = registry()['recipes']['BANK']
    assert reg['roles']['q_financial_safety']['evidence_status'] == 'PROXY'
    f = fields()
    before = deepcopy(reg)
    out = evaluate_raw('BANK', f, context())
    assert reg == before
    assert out['roles']['q_profitability']['role_score'] is None
    assert out['roles']['q_financial_safety']['role_score'] is None
    assert sum(r['weight'] for r in reg['roles'].values() if r['axis'] == 'Q') == 100


def test_exact_formula_and_nominal_contribution_do_not_claim_effective_score():
    assert formula_expression('roe_common_ttm') == 'net_income_common / mean(common_equity_begin, common_equity_end)'
    out = evaluate_raw('BANK', fields(), context())
    assert out['nominal_role_contribution']['q_profitability'] == 10
    assert sum(out['nominal_role_contribution'].values()) == 100
    assert out['effective_role_contribution'] is None


def test_observed_zero_is_not_a_missing_input_or_zero_score():
    f = fields()
    f['net_income_common']['value'] = 0
    role = evaluate_raw('BANK', f, context())['roles']['q_profitability']
    assert role['status'] == 'VALID_ZERO' and role['value'] == 0
    assert role['raw_valid'] and role['factor_score'] is None
