"""Synthetic-only checks for sec-valuation-inputs.json (fcfe/1.1, price-free): us-gaap, ifrs-full, assumed-zero lines."""
from datetime import datetime, timedelta, timezone
import copy
import importlib
import json
import math
from pathlib import Path
import subprocess
import pytest

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
CIK = '0001045810'
ASSETS = Path(__file__).parents[1] / 'src/investment_system/product/web_assets'
FULL = {
    'NetCashProvidedByUsedInOperatingActivities': 1000.0,
    'PaymentsToAcquirePropertyPlantAndEquipment': 300.0,
    'ProceedsFromIssuanceOfLongTermDebt': 200.0,
    'RepaymentsOfLongTermDebt': 50.0,
    'ProceedsFromRepaymentsOfShortTermDebt': -25.0,
    'WeightedAverageNumberOfDilutedSharesOutstanding': 100.0,
}


def screens():
    return importlib.import_module('investment_system.product.public_engine_screens')


def api():
    return importlib.import_module('investment_system.product.sec_valuation_inputs')


IFRS_CIK = '0000937966'
IFRS_FULL = {
    'CashFlowsFromUsedInOperatingActivities': 2000.0,
    'PurchaseOfPropertyPlantAndEquipment': 500.0,
    'ProceedsFromNoncurrentBorrowings': 300.0,
    'RepaymentsOfNoncurrentBorrowings': 100.0,
    'ProceedsFromCurrentBorrowings': 40.0,
    'RepaymentsOfCurrentBorrowings': 90.0,
    'AdjustedWeightedAverageShares': 400.0,
}


def write_ifrs(tmp_path, latest, *, revenue_years=4, form='20-F', unit='EUR', extra_candidates=None):
    """An ifrs-full 20-F filer (asml) with FY2022..FY2025 Revenue, diluted EPS and the given latest cash-flow lines."""
    filings, facts = [], {}

    def add(concept, u, year, value, accn, filed):
        facts.setdefault(concept, {'units': {}})['units'].setdefault(u, []).append(
            {'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': value, 'accn': accn, 'form': form, 'filed': filed, 'fy': year, 'fp': 'FY'})

    for year in range(2022, 2026):
        accn, filed = f'{IFRS_CIK}-{year + 1 - 2000:02d}-000001', f'{year + 1}-02-01'
        filings.append((accn, filed, form))
        if year > 2025 - revenue_years:
            add('Revenue', unit, year, 1000.0 * 1.1 ** (year - 2022), accn, filed)
        add('DilutedEarningsLossPerShare', unit + '/shares', year, 2.0 + (year - 2022), accn, filed)
        if year == 2025:
            for concept, value in latest.items():
                add(concept, 'shares' if concept == 'AdjustedWeightedAverageShares' else unit, year, value, accn, filed)
    payload = {'cik': int(IFRS_CIK), 'facts': {'ifrs-full': facts}}
    subs = {'cik': int(IFRS_CIK), 'filings': {'recent': {'form': [f[2] for f in filings], 'accessionNumber': [f[0] for f in filings],
                                                          'filingDate': [f[1] for f in filings], 'reportDate': ['2025-12-31'] * len(filings),
                                                          'acceptanceDateTime': [f[1] + 'T12:00:00Z' for f in filings]}}}
    (tmp_path / 'facts.json').write_text(json.dumps(payload))
    (tmp_path / 'submissions.json').write_text(json.dumps(subs))
    return {'schema_version': 1, 'macro': [], 'thirteen_f': [],
            'sec': [{'company_id': 'asml', 'companyfacts': 'facts.json', 'submissions': 'submissions.json', 'acquired_at': '2026-10-10T00:00:00Z', 'synthetic': False}]}


def asml(payload):
    return payload['data']['companies']['asml']


def comp(concepts, value):
    return {'concepts': concepts, 'value': value, 'assumed_zero': False, 'reason': None}


ZERO = {'concepts': [], 'value': 0.0, 'assumed_zero': True, 'reason': 'NOT_REPORTED_ASSUMED_ZERO'}


def write_company(tmp_path, latest, *, previous=None, units=None, amendment=None, synthetic=False, acquired='2026-10-10T00:00:00Z', revenue_years=2):
    """Two annual 10-K filings (FY2024, FY2025) plus an optional later 10-K/A for given concepts."""
    units = units or {}
    filings, facts = [], {}

    def add(concept, unit, start, end, value, accn, form, filed):
        facts.setdefault(concept, {'units': {}})['units'].setdefault(unit, []).append(
            {'start': start, 'end': end, 'val': value, 'accn': accn, 'form': form, 'filed': filed, 'fy': int(end[:4]), 'fp': 'FY'})

    years = {2024: previous if previous is not None else {k: v * 0.9 for k, v in latest.items()}, 2025: latest}
    for year, values in years.items():
        accn, filed = f'{CIK}-{year + 1 - 2000:02d}-000001', f'{year + 1}-02-01'
        filings.append((accn, filed, '10-K'))
        for concept, value in values.items():
            unit = units.get(concept, 'shares' if concept.startswith('WeightedAverage') else 'USD')
            add(concept, unit, f'{year}-01-01', f'{year}-12-31', value, accn, '10-K', filed)
            if year == 2025:  # comparative prior-year rows reported again in the latest filing
                pass
    for concept, value in {'Revenues': 5000.0, 'EarningsPerShareDiluted': 4.0}.items():
        for year, scale in ((2022, 0.5), (2023, 0.64), (2024, 0.8), (2025, 1.0))[4 - revenue_years:]:
            accn, filed = f'{CIK}-{year + 1 - 2000:02d}-000001', f'{year + 1}-02-01'
            if (accn, filed, '10-K') not in filings:
                filings.append((accn, filed, '10-K'))
            unit = 'USD/shares' if concept.startswith('Earnings') else 'USD'
            add(concept, unit, f'{year}-01-01', f'{year}-12-31', value * scale, accn, '10-K', filed)
    if amendment:
        accn, filed = f'{CIK}-26-000009', '2026-03-01'
        filings.append((accn, filed, '10-K/A'))
        for concept, value in amendment.items():
            add(concept, 'USD', '2025-01-01', '2025-12-31', value, accn, '10-K/A', filed)
    payload = {'cik': int(CIK), 'facts': {'us-gaap': facts, 'dei': {'StockPrice': {'units': {'USD': [{'val': 99999}]}}}}, 'private_value': 'TEST_ONLY_CANARY'}
    subs = {'cik': int(CIK), 'filings': {'recent': {'form': [f[2] for f in filings], 'accessionNumber': [f[0] for f in filings],
                                                     'filingDate': [f[1] for f in filings], 'reportDate': ['2025-12-31'] * len(filings),
                                                     'acceptanceDateTime': [f[1] + 'T12:00:00Z' for f in filings]}}}
    (tmp_path / 'facts.json').write_text(json.dumps(payload))
    (tmp_path / 'submissions.json').write_text(json.dumps(subs))
    return {'schema_version': 1, 'macro': [], 'thirteen_f': [],
            'sec': [{'company_id': 'nvda', 'companyfacts': 'facts.json', 'submissions': 'submissions.json', 'acquired_at': acquired, 'synthetic': synthetic}]}


def build(tmp_path, manifest):
    return screens().generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW, stale_after=timedelta(days=2))['sec-valuation-inputs.json']


def nvda(payload):
    return payload['data']['companies']['nvda']


def test_fcfe_definition_components_and_diluted_per_share(tmp_path):
    out = build(tmp_path, write_company(tmp_path, FULL))
    row = nvda(out)
    f = row['fcfe']
    assert out['state'] == row['state'] == f['state'] == 'LIVE' and f['reason_codes'] == []
    # 1000 - 300 + 200 + (-25) - 50 = 825 over 100 diluted shares.
    assert f['fcfe_per_share'] == pytest.approx(8.25, rel=1e-15)
    assert (f['currency'], f['fiscal_period_start'], f['fiscal_period_end'], f['form']) == ('USD', '2025-01-01', '2025-12-31', '10-K')
    assert f['accn'] == '000104581026000001'
    assert f['taxonomy'] == 'us-gaap'
    assert f['components']['capital_expenditure'] == comp(['PaymentsToAcquirePropertyPlantAndEquipment'], 300.0)
    assert f['components']['diluted_shares']['value'] == 100.0
    assert not any(c['assumed_zero'] for c in f['components'].values())
    v = row['v_inputs']
    assert v['state'] == 'LIVE' and v['eps'] == 4.0 and v['revenue'] == 5000.0 and v['revenue_prev'] == 4000.0 and v['currency'] == 'USD'
    # Only two revenue years: no 3-year CAGR, so no explicit growth h (never invented).
    assert v['revenue_cagr_3y'] is None and v['reason_codes'] == ['REVENUE_CAGR_3Y_MISSING']
    screens().require_public_screen('sec-valuation-inputs.json', out)
    # Every other company stays NOT_AVAILABLE with a fixed reason, never zero.
    other = out['data']['companies']['amd']
    assert other['state'] == 'NOT_AVAILABLE' and other['fcfe']['fcfe_per_share'] is None and other['fcfe']['reason_codes'] == ['SEC_INPUT_NOT_AVAILABLE']


def test_public_file_carries_no_price_ratio_score_or_market_cap(tmp_path):
    out = build(tmp_path, write_company(tmp_path, FULL))
    text = json.dumps(out)
    assert 'TEST_ONLY_CANARY' not in text and 'StockPrice' not in text and '99999' not in text
    banned = ('price', 'market_cap', 'marketcap', 'score', 'ratio', 'yield', 'implied', 'intrinsic', 'margin_of_safety')
    def walk(value):
        if isinstance(value, dict):
            for k, child in value.items():
                assert not any(b in k.lower() for b in banned), k
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(out)


@pytest.mark.parametrize('drop,reason', [
    ('PaymentsToAcquirePropertyPlantAndEquipment', 'CAPITAL_EXPENDITURE_MISSING'),
    ('WeightedAverageNumberOfDilutedSharesOutstanding', 'DILUTED_SHARES_MISSING'),
])
def test_missing_core_component_is_not_available_never_zero(tmp_path, drop, reason):
    latest = {k: v for k, v in FULL.items() if k != drop}
    previous = {k: v * 0.9 for k, v in FULL.items()}  # an older period's value never fills the latest one
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=previous)))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['fcfe_per_share'] is None and f['reason_codes'] == [reason]
    key = next(k for k, alts in api().ALTERNATIVES['us-gaap'].items() if any(drop in a for a in alts))
    assert f['components'][key] is None
    assert f['components']['operating_cash_flow']['value'] == 1000.0


def test_missing_operating_cash_flow_is_never_zero(tmp_path):
    latest = {k: v for k, v in FULL.items() if k != 'NetCashProvidedByUsedInOperatingActivities'}
    previous = {k: v * 0.9 for k, v in FULL.items()}
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=previous)))['fcfe']
    # The latest operating cash flow is the FY2024 one; FY2025 lines are never pulled back into it.
    assert f['fiscal_period_end'] == '2024-12-31' and f['state'] == 'LIVE'
    assert f['components']['operating_cash_flow']['value'] == pytest.approx(900.0)


@pytest.mark.parametrize('drop,key', [
    ('ProceedsFromRepaymentsOfShortTermDebt', 'net_short_term_borrowing'),
    ('ProceedsFromIssuanceOfLongTermDebt', 'long_term_debt_issuance'),
    ('RepaymentsOfLongTermDebt', 'long_term_debt_repayment'),
])
def test_unreported_borrowing_line_is_assumed_zero_and_marked(tmp_path, drop, key):
    latest = {k: v for k, v in FULL.items() if k != drop}
    previous = {k: v * 0.9 for k, v in FULL.items()}  # an older period's value never fills the latest one
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=previous)))['fcfe']
    assert f['state'] == 'LIVE' and f['reason_codes'] == []
    assert f['components'][key] == ZERO
    assert [k for k, c in f['components'].items() if c['assumed_zero']] == [key]
    values = {'net_short_term_borrowing': -25.0, 'long_term_debt_issuance': 200.0, 'long_term_debt_repayment': -50.0}
    assert f['fcfe_per_share'] == pytest.approx((825.0 - values[key]) / 100)
    assert f['accn'] == '000104581026000001' and f['form'] == '10-K'


def test_all_borrowing_lines_unreported(tmp_path):
    latest = {k: FULL[k] for k in ('NetCashProvidedByUsedInOperatingActivities', 'PaymentsToAcquirePropertyPlantAndEquipment',
                                   'WeightedAverageNumberOfDilutedSharesOutstanding')}
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=latest)))['fcfe']
    assert f['state'] == 'LIVE' and f['fcfe_per_share'] == pytest.approx(7.0)
    assert all(f['components'][k] == ZERO for k in api().OPTIONAL_COMPONENTS)


def partial(concepts, value):
    return {'concepts': concepts, 'value': value, 'assumed_zero': False, 'reason': 'BORROWING_PAIR_PARTIAL'}


@pytest.mark.parametrize('concept,value,expected', [('ProceedsFromShortTermDebt', 40.0, 40.0), ('RepaymentsOfShortTermDebt', 30.0, -30.0)])
def test_half_reported_pair_missing_side_is_zero(tmp_path, concept, value, expected):
    # User decision 2026-10-11: one side of a borrowing pair reported, the other reported nowhere -> missing side 0, BORROWING_PAIR_PARTIAL.
    latest = {k: v for k, v in FULL.items() if k != 'ProceedsFromRepaymentsOfShortTermDebt'}
    latest[concept] = value
    payload = build(tmp_path, write_company(tmp_path, latest))
    f = nvda(payload)['fcfe']
    assert f['state'] == 'LIVE' and f['reason_codes'] == []
    assert f['components']['net_short_term_borrowing'] == partial([concept], expected)
    assert f['fcfe_per_share'] == pytest.approx((1000 - 300 + 200 - 50 + expected) / 100)
    screens().require_public_screen('sec-valuation-inputs.json', payload)
    js = subprocess.run(['node', '-e', "require(process.argv[1]).validate('sec-valuation-inputs.json',JSON.parse(require('fs').readFileSync(0,'utf8')))",
                         str(ASSETS / 'device-valuation.js')], input=json.dumps(payload), text=True, capture_output=True)
    assert js.returncode == 0, js.stderr


def test_half_reported_pair_other_side_unusable_stays_not_available(tmp_path):
    latest = {k: v for k, v in FULL.items() if k != 'ProceedsFromRepaymentsOfShortTermDebt'}
    latest['ProceedsFromShortTermDebt'] = 40.0
    m1 = {'selected_input_facts': [], 'revision_candidates': [
        {'taxonomy': 'us-gaap', 'concept': 'RepaymentsOfShortTermDebt', 'start': '2025-01-27', 'end': '2026-01-25', 'exclusion_reasons': ['NOT_ANNUAL']}]}
    base = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    start, end = base['fiscal_period_start'], base['fiscal_period_end']
    m1['revision_candidates'][0].update(start=start, end=end)
    by = {('ProceedsFromShortTermDebt', 'USD', start, end): {'value': 40.0}}
    alts = dict(api().COMPONENTS['us-gaap'])['net_short_term_borrowing']
    assert api()._pair_partial(alts, by, m1['revision_candidates'], 'us-gaap', 'USD', start, end) is None
    assert api()._pair_partial(alts, by, [], 'us-gaap', 'USD', start, end) is not None


def test_ifrs_half_reported_current_pair_is_partial(tmp_path):
    latest = {k: v for k, v in IFRS_FULL.items() if k != 'RepaymentsOfCurrentBorrowings'}
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['state'] == 'LIVE' and f['components']['net_short_term_borrowing'] == partial(['ProceedsFromCurrentBorrowings'], 40.0)
    assert f['fcfe_per_share'] == pytest.approx((2000 - 500 + 300 - 100 + 40) / 400)


PARTIAL_MUTATIONS = [
    lambda c: c['net_short_term_borrowing'].update(concepts=['ProceedsFromShortTermDebt', 'RepaymentsOfShortTermDebt']),
    lambda c: c['net_short_term_borrowing'].update(concepts=['ProceedsFromRepaymentsOfShortTermDebt']),
    lambda c: c['net_short_term_borrowing'].update(concepts=[]),
    lambda c: c['net_short_term_borrowing'].update(assumed_zero=True),
    lambda c: c['capital_expenditure'].update(reason='BORROWING_PAIR_PARTIAL'),
    lambda c: c['long_term_debt_issuance'].update(reason='BORROWING_PAIR_PARTIAL'),
]


@pytest.mark.parametrize('mutate', PARTIAL_MUTATIONS)
def test_validators_reject_malformed_pair_partial(tmp_path, mutate):
    latest = {k: v for k, v in FULL.items() if k != 'ProceedsFromRepaymentsOfShortTermDebt'}
    latest['ProceedsFromShortTermDebt'] = 40.0
    payload = copy.deepcopy(build(tmp_path, write_company(tmp_path, latest)))
    mutate(payload['data']['companies']['nvda']['fcfe']['components'])
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        screens().require_public_screen('sec-valuation-inputs.json', payload)
    result = subprocess.run(['node', '-e', "const a=require(process.argv[1]);try{a.validate('sec-valuation-inputs.json',JSON.parse(require('fs').readFileSync(0,'utf8')));process.exit(0)}catch(e){process.exit(e.message==='PUBLIC_SCREEN_INVALID'?3:4)}",
                             str(ASSETS / 'device-valuation.js')], input=json.dumps(payload), text=True, capture_output=True)
    assert result.returncode == 3


def test_borrowing_line_reported_only_in_another_filing_is_not_assumed_zero(tmp_path):
    latest = {k: v for k, v in FULL.items() if k != 'RepaymentsOfLongTermDebt'}
    f = nvda(build(tmp_path, write_company(tmp_path, latest, amendment={'RepaymentsOfLongTermDebt': 60.0})))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['MIXED_FILINGS']
    assert f['components']['long_term_debt_repayment'] == comp(['RepaymentsOfLongTermDebt'], 60.0)


def test_borrowing_line_in_other_currency_is_not_assumed_zero(tmp_path):
    f = nvda(build(tmp_path, write_company(tmp_path, FULL, units={'RepaymentsOfLongTermDebt': 'EUR'})))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['COMPONENT_CURRENCY_MISMATCH']
    assert f['components']['long_term_debt_repayment'] is None


def test_reported_zero_is_a_real_zero(tmp_path):
    latest = dict(FULL, ProceedsFromIssuanceOfLongTermDebt=0.0, RepaymentsOfLongTermDebt=0.0, ProceedsFromRepaymentsOfShortTermDebt=0.0)
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['state'] == 'LIVE' and f['fcfe_per_share'] == pytest.approx(7.0)
    assert f['components']['net_short_term_borrowing'] == comp(['ProceedsFromRepaymentsOfShortTermDebt'], 0.0)


def test_listed_fallback_concepts_in_order(tmp_path):
    latest = {k: v for k, v in FULL.items() if k not in ('PaymentsToAcquirePropertyPlantAndEquipment', 'ProceedsFromRepaymentsOfShortTermDebt')}
    latest.update(PaymentsToAcquireProductiveAssets=310.0, ProceedsFromShortTermDebt=40.0, RepaymentsOfShortTermDebt=65.0)
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['components']['capital_expenditure'] == comp(['PaymentsToAcquireProductiveAssets'], 310.0)
    assert f['components']['net_short_term_borrowing'] == comp(['ProceedsFromShortTermDebt', 'RepaymentsOfShortTermDebt'], -25.0)
    assert f['fcfe_per_share'] == pytest.approx((1000 - 310 + 200 - 25 - 50) / 100)
    # The primary concept wins when both are reported.
    latest['PaymentsToAcquirePropertyPlantAndEquipment'] = 300.0
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['components']['capital_expenditure']['concepts'] == ['PaymentsToAcquirePropertyPlantAndEquipment']


def test_currency_and_share_basis_are_never_converted(tmp_path):
    f = nvda(build(tmp_path, write_company(tmp_path, FULL, units={'PaymentsToAcquirePropertyPlantAndEquipment': 'EUR'})))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['COMPONENT_CURRENCY_MISMATCH']
    f = nvda(build(tmp_path, write_company(tmp_path, dict(FULL, WeightedAverageNumberOfDilutedSharesOutstanding=0.0))))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['DILUTED_SHARES_NON_POSITIVE']


def test_components_from_different_filings_are_not_mixed(tmp_path):
    f = nvda(build(tmp_path, write_company(tmp_path, FULL, amendment={'NetCashProvidedByUsedInOperatingActivities': 1100.0})))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['MIXED_FILINGS'] and f['accn'] is None


def test_stale_synthetic_and_future_inputs(tmp_path):
    assert nvda(build(tmp_path, write_company(tmp_path, FULL, acquired='2026-10-01T00:00:00Z')))['fcfe']['state'] == 'STALE'
    out = build(tmp_path, write_company(tmp_path, FULL, synthetic=True))
    assert out['state'] == 'NOT_AVAILABLE' and nvda(out)['fcfe']['reason_codes'] == ['SEC_INPUT_NOT_AVAILABLE']
    assert build(tmp_path, write_company(tmp_path, FULL, acquired='2026-10-11T00:00:00Z'))['state'] == 'NOT_AVAILABLE'


def test_no_cash_flow(tmp_path):
    latest = {k: v for k, v in FULL.items() if k != 'NetCashProvidedByUsedInOperatingActivities'}
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=latest)))['fcfe']
    assert f['reason_codes'] == ['CASH_FLOW_NOT_REPORTED'] and f['fcfe_per_share'] is None and f['taxonomy'] is None


def test_revenue_cagr_3y_matches_the_published_type_metric(tmp_path):
    bundle = screens().generate_screen_bundle(manifest=write_company(tmp_path, FULL, revenue_years=4), input_root=tmp_path, as_of=NOW, stale_after=timedelta(days=2))
    v = nvda(bundle['sec-valuation-inputs.json'])['v_inputs']
    assert v['revenue_cagr_3y'] == pytest.approx(2 ** (1 / 3) - 1, rel=1e-12) and v['reason_codes'] == []
    # Exact calendar years: the type metric (QGV v2 period rule, 6 significant digits as in sec-qgv2.json) agrees.
    assert bundle['company-types-pricefree.json']['data']['companies']['nvda']['metrics']['revenue_cagr_3y'] == pytest.approx(v['revenue_cagr_3y'], rel=1e-5)


def test_ifrs_20f_filer(tmp_path):
    out = build(tmp_path, write_ifrs(tmp_path, IFRS_FULL))
    row = asml(out)
    f = row['fcfe']
    assert f['state'] == 'LIVE' and f['reason_codes'] == [] and f['taxonomy'] == 'ifrs-full'
    assert (f['currency'], f['form'], f['fiscal_period_end'], f['accn']) == ('EUR', '20-F', '2025-12-31', '000093796626000001')
    # 2000 - 500 + 300 + (40 - 90) - 100 = 1650 over 400 adjusted weighted average shares.
    assert f['fcfe_per_share'] == pytest.approx(4.125, rel=1e-15)
    assert f['components']['net_short_term_borrowing'] == comp(['ProceedsFromCurrentBorrowings', 'RepaymentsOfCurrentBorrowings'], -50.0)
    assert f['components']['capital_expenditure'] == comp(['PurchaseOfPropertyPlantAndEquipment'], 500.0)
    assert f['components']['diluted_shares'] == comp(['AdjustedWeightedAverageShares'], 400.0)
    v = row['v_inputs']
    assert (v['state'], v['currency'], v['eps'], v['revenue']) == ('LIVE', 'EUR', 5.0, pytest.approx(1331.0))
    assert v['revenue_cagr_3y'] == pytest.approx(0.1, rel=1e-12) and v['reason_codes'] == []
    screens().require_public_screen('sec-valuation-inputs.json', out)


def test_ifrs_intangibles_are_not_capex(tmp_path):
    latest = dict(IFRS_FULL, PurchaseOfIntangibleAssets=70.0)
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['fcfe_per_share'] == pytest.approx(4.125) and f['components']['capital_expenditure']['value'] == 500.0


def test_ifrs_current_borrowings_unreported_assumed_zero_and_total_fallback(tmp_path):
    latest = {k: v for k, v in IFRS_FULL.items() if 'Current' not in k and 'Noncurrent' not in k}
    latest.update(ProceedsFromBorrowingsClassifiedAsFinancingActivities=300.0, RepaymentsOfBorrowingsClassifiedAsFinancingActivities=100.0)
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['state'] == 'LIVE' and f['components']['net_short_term_borrowing'] == ZERO
    assert f['components']['long_term_debt_issuance'] == comp(['ProceedsFromBorrowingsClassifiedAsFinancingActivities'], 300.0)
    assert f['fcfe_per_share'] == pytest.approx((2000 - 500 + 300 - 100) / 400)


def test_ifrs_total_borrowing_fallback_with_current_pair_would_double_count(tmp_path):
    latest = {k: v for k, v in IFRS_FULL.items() if 'Noncurrent' not in k}
    latest.update(ProceedsFromBorrowingsClassifiedAsFinancingActivities=340.0, RepaymentsOfNoncurrentBorrowings=100.0)
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['BORROWING_SCOPE_OVERLAP']


def test_ifrs_core_lines_never_zero(tmp_path):
    latest = {k: v for k, v in IFRS_FULL.items() if k != 'AdjustedWeightedAverageShares'}
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['reason_codes'] == ['DILUTED_SHARES_MISSING']
    latest = {k: v for k, v in IFRS_FULL.items() if k != 'PurchaseOfPropertyPlantAndEquipment'}
    f = asml(build(tmp_path, write_ifrs(tmp_path, latest)))['fcfe']
    assert f['reason_codes'] == ['CAPITAL_EXPENDITURE_MISSING']


def test_ifrs_40f_and_short_revenue_history(tmp_path):
    out = asml(build(tmp_path, write_ifrs(tmp_path, IFRS_FULL, form='40-F', unit='USD', revenue_years=3)))
    assert out['fcfe']['state'] == 'LIVE' and out['fcfe']['form'] == '40-F' and out['fcfe']['currency'] == 'USD'
    assert out['v_inputs']['revenue_cagr_3y'] is None and out['v_inputs']['reason_codes'] == ['REVENUE_CAGR_3Y_MISSING']


def test_us_gaap_and_ifrs_on_the_same_latest_period_is_ambiguous():
    m1 = {'selected_input_facts': [
        {'taxonomy': t, 'concept': c, 'unit': 'USD', 'start': '2025-01-01', 'end': '2025-12-31', 'value': 1.0, 'accn': '0' * 18, 'form': '10-K'}
        for t, c in (('us-gaap', 'NetCashProvidedByUsedInOperatingActivities'), ('ifrs-full', 'CashFlowsFromUsedInOperatingActivities'))]}
    assert api().project_fcfe(m1, 'LIVE')['reason_codes'] == ['TAXONOMY_AMBIGUOUS']


MUTATIONS = [
    lambda p: p['data']['companies']['nvda']['fcfe'].update(price=100.0),
    lambda p: p['data']['companies']['nvda'].update(v_score=50),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(fcfe_per_share=9.0),
    lambda p: p['data']['companies']['nvda']['fcfe']['components'].update(long_term_debt_issuance=None),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['capital_expenditure'].update(concepts=['CapitalExpenditure']),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['capital_expenditure'].update(concepts=['PurchaseOfPropertyPlantAndEquipment']),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['capital_expenditure'].update(concepts=[], value=0.0, assumed_zero=True, reason='NOT_REPORTED_ASSUMED_ZERO'),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['long_term_debt_issuance'].update(assumed_zero=True),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['long_term_debt_issuance'].update(reason='NOT_REPORTED_ASSUMED_ZERO'),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['long_term_debt_issuance'].pop('assumed_zero'),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(taxonomy='ifrs-full'),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(taxonomy=None),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(form='S-1'),
    lambda p: p['data']['companies']['nvda']['v_inputs'].update(revenue_cagr_3y=1000.0),
    lambda p: p['data']['companies']['nvda']['v_inputs'].update(revenue_cagr_3y=0.1),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(reason_codes=['free text']),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(state='NOT_AVAILABLE'),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['diluted_shares'].update(value=float('nan')),
    lambda p: p['data']['companies']['nvda']['v_inputs'].update(eps=None),
    lambda p: p['data'].update(fcfe_definition='fcfe/1'),
    lambda p: p['data']['companies'].pop('amd'),
    lambda p: p.update(state='STALE'),
    lambda p: p['data']['companies']['nvda'].update(source_hashes={}),
]


@pytest.mark.parametrize('mutate', MUTATIONS)
def test_python_and_js_validators_reject_tampering(tmp_path, mutate):
    payload = copy.deepcopy(build(tmp_path, write_company(tmp_path, FULL)))
    mutate(payload)
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        screens().require_public_screen('sec-valuation-inputs.json', payload)
    text = json.dumps(payload, allow_nan=True).replace('NaN', '"NaN"')
    result = subprocess.run(['node', '-e', "const a=require(process.argv[1]);try{a.validate('sec-valuation-inputs.json',JSON.parse(require('fs').readFileSync(0,'utf8')));process.exit(0)}catch(e){process.exit(e.message==='PUBLIC_SCREEN_INVALID'?3:4)}",
                             str(ASSETS / 'device-valuation.js')], input=text, text=True, capture_output=True)
    assert result.returncode == 3


def test_js_constants_match_python():
    script = "const a=require(process.argv[1]);process.stdout.write(JSON.stringify({ids:a.IDS,alt:a.ALTERNATIVES,optional:a.OPTIONAL,f:a.FCFE_REASONS,v:a.V_REASONS,file:a.FILE,kind:a.KIND}))"
    out = json.loads(subprocess.run(['node', '-e', script, str(ASSETS / 'device-valuation.js')], capture_output=True, text=True, check=True).stdout)
    from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS
    assert out['ids'] == list(OFFICIAL_V11_TARGETS)
    assert {t: {k: [list(a) for a in v] for k, v in alts.items()} for t, alts in api().ALTERNATIVES.items()} == out['alt']
    assert list(api().ALTERNATIVES) == list(out['alt']) and all(list(api().ALTERNATIVES[t]) == list(out['alt'][t]) for t in out['alt'])
    assert out['optional'] == list(api().OPTIONAL_COMPONENTS)
    assert set(out['f']) == set(api().FCFE_REASONS) and len(out['f']) == len(api().FCFE_REASONS)
    assert set(out['v']) == set(api().V_REASONS)
    assert (out['file'], out['kind']) == (api().FILENAME, api().KIND)


def test_fcfe_total_uses_one_fixed_order():
    c = {k: {'concepts': [], 'value': v} for k, v in zip(api().COMPONENT_KEYS, (0.1, 0.2, 0.3, 0.4, 0.5, 1.0))}
    expected = 0.1 - 0.2 + 0.3 + 0.5 - 0.4
    assert api().fcfe_total(c) == expected
    js = subprocess.run(['node', '-e', "const a=require(process.argv[1]);process.stdout.write(JSON.stringify(a.fcfeTotal(JSON.parse(process.argv[2]))))", str(ASSETS / 'device-valuation.js'), json.dumps(c)],
                        capture_output=True, text=True, check=True).stdout
    assert json.loads(js) == expected and math.isfinite(expected)
