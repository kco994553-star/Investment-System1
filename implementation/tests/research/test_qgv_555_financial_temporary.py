"""Hand-calculated synthetic FINANCIAL definitions; no held-company values."""
from copy import deepcopy
from statistics import mean, pstdev

import pytest

from investment_system.qgv import v2_factors as vf
from investment_system.qgv.qgv_v2 import WEIGHTS
from investment_system.research.qgv_555_financial_temporary import (
    CALC_VERSION, STATUS, contribution_metadata, financial_catalog,
    financial_role_recipes, validate_official_financial_record, validate_role_recipes,
)


class SyntheticCompany:
    roe = vf._Company.roe
    per_share = vf._Company.per_share

    def __init__(self):
        self.annual = dict(net_income=[20, 18, 14, 10, 8, 5],
            net_interest_income=[45], revenue=[400, 320, 250, 200, 160, 100])
        self.instant = dict(equity=[200, 100, 90, 80, 60, 50],
            total_assets=[1000, 800])
        self.share_values = [10] * 6
        self.eps_values = [2, 1.8, 1.4, 1, .8, .5]

    def a(self, item, k):
        values = self.annual.get(item, [])
        return values[k] if k < len(values) else None

    def i(self, item, k):
        values = self.instant.get(item, [])
        return values[k] if k < len(values) else None

    def shares(self, k):
        return self.share_values[k]

    def eps(self, k):
        return self.eps_values[k]

    def ttm(self, item):
        return 450, '2026-06-30', 300


def raw_metrics(company=None):
    company = SyntheticCompany() if company is None else company
    metrics = vf._metrics_financial(company)
    vf._growth_common(company, metrics)
    return metrics


def result_roles():
    return {role: dict(score=50 if spec['metrics'] else None,
        metrics=[dict(metric=m, weight=w, score=50) for m, w in spec['metrics'].items()])
        for role, spec in financial_role_recipes().items()}


def clear_role(roles, role):
    roles[role]['score'] = None
    for item in roles[role]['metrics']:
        item['score'] = None


def test_frozen_fifteen_roles_have_fourteen_unique_raw_metrics_and_six_nulls():
    recipes = financial_role_recipes()
    cats = financial_catalog()
    assert len(recipes) == 15 and len(cats) == 14
    assert sum(bool(r['metrics']) for r in recipes.values()) == 9
    assert {r: x['weight'] for r, x in recipes.items()} == {
        r: w for weights in WEIGHTS.values() for r, w in weights.items()}
    assert all(sum(x['weight'] for x in recipes.values() if x['axis'] == a) == 100 for a in 'QGV')
    metrics = [cats[m]['source_metric'] for spec in recipes.values() for m in spec['metrics']]
    assert len(metrics) == len(set(metrics))
    assert recipes['q_earnings_quality']['metrics'] == {}
    assert all(not recipes[r]['metrics'] for r in recipes if r.startswith('v_'))
    assert all(s['temporary_status'] == STATUS for s in recipes.values())
    recipes['q_profitability']['weight'] = 0
    cats['financial::roe']['accounting_scope'].append('GENERAL')
    assert financial_role_recipes()['q_profitability']['weight'] == 25
    assert financial_catalog()['financial::roe']['accounting_scope'] == ['FINANCIAL']


def test_exact_official_raw_arithmetic_matches_hand_calculation():
    m = raw_metrics()
    assert m['roe'] == pytest.approx(20 / 150)
    assert m['roa'] == pytest.approx(20 / 900)
    assert m['net_interest_income_to_assets'] == pytest.approx(45 / 900)
    assert m['equity_to_assets'] == pytest.approx(200 / 1000)
    assert m['incremental_roe_5y'] == pytest.approx(15 / 150)
    assert m['incremental_roe_3y'] == pytest.approx(10 / 120)
    returns = [20 / 150, 18 / 95, 14 / 85, 10 / 70, 8 / 55]
    assert m['moat_proxy'] == pytest.approx(mean(returns) - pstdev(returns))
    assert m['dilution_3y'] == 0
    assert m['eps_cagr_3y'] == pytest.approx(2 ** (1 / 3) - 1)
    assert m['book_value_per_share_cagr_3y'] == pytest.approx(2.5 ** (1 / 3) - 1)
    assert m['revenue_cagr_3y'] == pytest.approx(2 ** (1 / 3) - 1)
    assert m['revenue_positive_growth_share'] == 1
    assert m['revenue_growth_volatility'] == pytest.approx(pstdev([.25, .28, .25, .25, .6]))
    assert m['revenue_acceleration'] == pytest.approx(.5 - (2 ** (1 / 3) - 1))


def test_official_missing_opening_signed_values_and_endpoint_rules_are_preserved():
    c = SyntheticCompany()
    c.instant['equity'][1] = None
    c.instant['total_assets'][1] = None
    m = raw_metrics(c)
    assert m['roe'] == .1 and m['roa'] == .02
    c.annual['net_income'][0] = -20
    assert raw_metrics(c)['roe'] == -.1
    c.annual['net_income'][0] = 0
    assert raw_metrics(c)['roe'] == 0
    c.instant['equity'][0] = -200
    assert raw_metrics(c)['roe'] is None
    assert raw_metrics(c)['equity_to_assets'] == -.2
    assert raw_metrics(c)['book_value_per_share_cagr_3y'] is None
    c = SyntheticCompany()
    c.instant['equity'][0] = c.instant['equity'][3]
    c.eps_values[3] = 0
    assert raw_metrics(c)['incremental_roe_3y'] is None
    assert raw_metrics(c)['eps_cagr_3y'] is None
    c = SyntheticCompany()
    c.annual['revenue'][1:3] = [None, None]
    assert raw_metrics(c)['revenue_cagr_3y'] is not None  # endpoints only
    assert raw_metrics(c)['revenue_positive_growth_share'] is None  # only two YoY observations


def test_same_raw_metric_in_two_roles_or_economic_reassignment_is_rejected():
    recipes = financial_role_recipes()
    recipes['q_earnings_quality']['metrics'] = {'financial::roe': 1}
    with pytest.raises(ValueError, match='FINANCIAL_DUPLICATE_SOURCE_METRIC'):
        validate_role_recipes(recipes)
    recipes = financial_role_recipes()
    recipes['q_earnings_quality']['metrics'] = recipes['q_moat_proxy']['metrics']
    recipes['q_moat_proxy']['metrics'] = {}
    with pytest.raises(ValueError, match='FINANCIAL_FROZEN_ROLE_MAPPING'):
        validate_role_recipes(recipes)
    recipes = financial_role_recipes()
    recipes['q_financial_safety']['weight'] = 21
    with pytest.raises(ValueError, match='FINANCIAL_ROLE_BUDGET'):
        validate_role_recipes(recipes)


def test_catalog_discloses_share_basis_and_fiscal_attribution_limitations():
    cats = financial_catalog()
    bps = cats['financial::book_value_per_share_cagr_3y']
    assert bps['historical_share_evidence_required']
    assert bps['denominator_definition'] == 'WEIGHTED_AVERAGE_DILUTED_SHARES'
    assert bps['historical_share_periods'] == ['FY0', 'FY-3']
    assert 'EQUITY_ENDPOINT_SOURCE_PERIODS' in bps['required_evidence']
    assert not bps['common_attribution_confirmed']
    assert bps['peer_accounting_model_policy'] == 'RETAIN_CONFIRMED_MODEL'
    assert cats['financial::roe']['opening_balance_policy'] == 'CLOSING_ONLY_IF_OPENING_MISSING'
    assert cats['financial::roe']['period'] == 'FY'
    assert 'TTM' not in cats['financial::roe']['formula']


def test_raw_record_validation_reads_no_official_scores_or_invents_share_proof():
    record = dict(calc_version=CALC_VERSION, profile='FINANCIAL', state='STALE',
        metrics=raw_metrics(), axes='invalid score structure is never read', factors=object())
    result = validate_official_financial_record(record)
    assert result['valid'] and result['supported_metrics'] == 14
    assert not result['official_scores_read'] and not result['historical_share_basis_validated']
    assert not result['peer_accounting_model_inferred']
    for field, value, reason in [('profile', 'GENERAL', 'PROFILE'),
            ('calc_version', 'other', 'CALC_VERSION'), ('state', 'MISSING', 'STATE')]:
        changed = dict(record, **{field: value})
        with pytest.raises(ValueError, match=reason):
            validate_official_financial_record(changed)
    for value in (True, '1', float('nan'), float('inf')):
        changed = dict(record, metrics=dict(record['metrics'], roe=value))
        with pytest.raises(ValueError, match='NONFINITE'):
            validate_official_financial_record(changed)
    changed = dict(record, metrics=dict(record['metrics'], roe=None, roa=-.1, equity_to_assets=0))
    assert validate_official_financial_record(changed)['supported_metrics'] == 13


def test_nominal_effective_contributions_include_family_overlap_and_unmapped_budget():
    roles = result_roles()
    before = deepcopy(roles)
    out = contribution_metadata(roles, included_axes=['Q', 'G'], total_available=True)
    assert roles == before
    assert out['minimum_peers'] == 8 and out['minimum_axis_available_weight'] == 50
    assert out['axis_available_weight'] == dict(Q=80, G=100, V=0)
    assert sum(r['nominal'] for r in out['role_contributions'].values()) == pytest.approx(1)
    assert sum(r['effective'] for r in out['role_contributions'].values()) == pytest.approx(1)
    assert sum(r['nominal'] for r in out['lineage']) == pytest.approx(.602)
    assert out['unmapped_nominal'] == pytest.approx(.398)
    assert out['role_contributions']['q_profitability']['effective'] == pytest.approx(34 / 67 * 25 / 80)
    families = {x['input_family']: x['roles'] for x in out['family_overlap_disclosures']}
    assert families['financial_return_level'] == ['q_moat_proxy', 'q_profitability']
    assert families['financial_incremental_return'] == ['g_growth_efficiency', 'q_capital_allocation']
    assert len(families['financial_revenue_growth']) == 3
    assert not out['financial_model_complete'] and out['duplicate_source_metric_count'] == 0


def test_zero_score_partial_metric_and_exact_fifty_weight_boundary():
    roles = result_roles()
    clear_role(roles, 'g_growth_efficiency')
    clear_role(roles, 'g_consistency')
    clear_role(roles, 'g_recent_acceleration')
    roles['q_profitability']['score'] = 0
    roles['q_profitability']['metrics'][0]['score'] = 0
    for item in roles['q_profitability']['metrics'][1:]:
        item['score'] = None
    out = contribution_metadata(roles, included_axes=['Q', 'G'], total_available=True)
    assert out['axis_available_weight']['G'] == 50
    profit = [x for x in out['lineage'] if x['role'] == 'q_profitability']
    assert profit[0]['effective'] > 0
    assert profit[1]['effective'] == profit[2]['effective'] == 0
    clear_role(roles, 'g_per_share_growth')
    with pytest.raises(ValueError, match='EFFECTIVE_AXIS_COVERAGE'):
        contribution_metadata(roles, included_axes=['Q', 'G'], total_available=True)
    out = contribution_metadata(roles)
    assert out['axis_available_weight']['G'] == 25
    assert all(x['effective'] == 0 for x in out['lineage'])
    assert all(x['within_axis_effective'] == 0 for r, x in out['role_contributions'].items() if r.startswith('g_'))


def test_undefined_role_score_cannot_enter_contribution_metadata():
    roles = result_roles()
    roles['v_earnings_yield']['score'] = 80
    with pytest.raises(ValueError, match='ROLE_AVAILABILITY'):
        contribution_metadata(roles)


def test_total_cannot_be_declared_when_available_axis_budget_is_below_half():
    roles = result_roles()
    with pytest.raises(ValueError, match='EFFECTIVE_AXIS_COVERAGE'):
        contribution_metadata(roles, included_axes=['Q'], total_available=True)
    for role in roles:
        if role.startswith('g_'):
            clear_role(roles, role)
    with pytest.raises(ValueError, match='EFFECTIVE_AXIS_COVERAGE'):
        contribution_metadata(roles, included_axes=['Q'], total_available=True)
    out = contribution_metadata(roles, axis_weights=dict(Q=50, G=25, V=25),
        included_axes=['Q'], total_available=True)
    assert sum(x['effective'] for x in out['lineage']) == pytest.approx(1)
    recipes = financial_role_recipes()
    recipes['v_earnings_yield']['null_reason'] = None
    with pytest.raises(ValueError, match='UNDEFINED_ROLE_REASON'):
        validate_role_recipes(recipes)


def test_catalog_required_inputs_identifies_primitives_periods_and_conditional_fallbacks():
    cats = financial_catalog()
    for spec in cats.values():
        assert spec['required_inputs'] and spec['required_evidence']
        for primitive in spec['required_inputs']:
            assert set(primitive) == {'field', 'period', 'accessor', 'required', 'condition'}
            assert primitive['field'] in {'net_income', 'equity', 'total_assets',
                'net_interest_income', 'diluted_shares', 'eps_diluted', 'revenue'}
            assert type(primitive['required']) is bool
    roe = cats['financial::roe']['required_inputs']
    assert [(x['field'], x['period'], x['required']) for x in roe] == [
        ('net_income', 'FY0', True), ('equity', 'FY0', True), ('equity', 'FY-1', False)]
    assert roe[-1]['condition'] == 'OPTIONAL_OPENING_BALANCE_CLOSING_ONLY_FALLBACK_IF_MISSING'
    bps = cats['financial::book_value_per_share_cagr_3y']['required_inputs']
    assert {(x['field'], x['period']) for x in bps} == {
        ('equity', 'FY0'), ('equity', 'FY-3'), ('diluted_shares', 'FY0'), ('diluted_shares', 'FY-3')}
    assert all(x['required'] for x in bps)
    moat = cats['financial::moat_proxy']['required_inputs']
    assert {x['period'] for x in moat if x['field'] == 'net_income'} == {'FY0', 'FY-1', 'FY-2', 'FY-3', 'FY-4'}
    assert all(not x['required'] for x in moat)
    assert any(x['condition'] == 'MINIMUM_3_OF_5_VALID_ROE_SAMPLES' for x in moat)
    growth = cats['financial::revenue_growth_volatility']['required_inputs']
    assert len(growth) == 6 and all(not x['required'] for x in growth)
    acceleration = cats['financial::revenue_acceleration']['required_inputs']
    assert {x['period'] for x in acceleration if x['required']} == {'FY0', 'FY-1', 'FY-3'}
    assert {x['period'] for x in acceleration if not x['required']} == {
        'YTD_CURRENT', 'YTD_PRIOR_YEAR', 'YTD_TWO_YEARS_AGO'}
    assert all('FALLBACK' in x['condition'] for x in acceleration if not x['required'])
