"""Synthetic-only checks for sec-valuation-inputs.json (fcfe/1, price-free)."""
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


def write_company(tmp_path, latest, *, previous=None, units=None, amendment=None, synthetic=False, acquired='2026-10-10T00:00:00Z'):
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
        for year, scale in ((2024, 0.8), (2025, 1.0)):
            accn, filed = f'{CIK}-{year + 1 - 2000:02d}-000001', f'{year + 1}-02-01'
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
    assert f['components']['capital_expenditure'] == {'concepts': ['PaymentsToAcquirePropertyPlantAndEquipment'], 'value': 300.0}
    assert f['components']['diluted_shares']['value'] == 100.0
    v = row['v_inputs']
    assert v['state'] == 'LIVE' and v['eps'] == 4.0 and v['revenue'] == 5000.0 and v['revenue_prev'] == 4000.0 and v['currency'] == 'USD'
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
    ('ProceedsFromRepaymentsOfShortTermDebt', 'NET_SHORT_TERM_BORROWING_MISSING'),
    ('ProceedsFromIssuanceOfLongTermDebt', 'LONG_TERM_DEBT_ISSUANCE_MISSING'),
    ('RepaymentsOfLongTermDebt', 'LONG_TERM_DEBT_REPAYMENT_MISSING'),
    ('PaymentsToAcquirePropertyPlantAndEquipment', 'CAPITAL_EXPENDITURE_MISSING'),
    ('WeightedAverageNumberOfDilutedSharesOutstanding', 'DILUTED_SHARES_MISSING'),
])
def test_missing_component_is_not_available_never_zero(tmp_path, drop, reason):
    latest = {k: v for k, v in FULL.items() if k != drop}
    previous = {k: v * 0.9 for k, v in FULL.items()}  # an older period's value never fills the latest one
    f = nvda(build(tmp_path, write_company(tmp_path, latest, previous=previous)))['fcfe']
    assert f['state'] == 'NOT_AVAILABLE' and f['fcfe_per_share'] is None and f['reason_codes'] == [reason]
    key = next(k for k, alts in api().ALTERNATIVES.items() if any(drop in a for a in alts))
    assert f['components'][key] is None
    assert f['components']['operating_cash_flow']['value'] == 1000.0


def test_reported_zero_is_a_real_zero(tmp_path):
    latest = dict(FULL, ProceedsFromIssuanceOfLongTermDebt=0.0, RepaymentsOfLongTermDebt=0.0, ProceedsFromRepaymentsOfShortTermDebt=0.0)
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['state'] == 'LIVE' and f['fcfe_per_share'] == pytest.approx(7.0)
    assert f['components']['net_short_term_borrowing']['value'] == 0.0


def test_listed_fallback_concepts_in_order(tmp_path):
    latest = {k: v for k, v in FULL.items() if k not in ('PaymentsToAcquirePropertyPlantAndEquipment', 'ProceedsFromRepaymentsOfShortTermDebt')}
    latest.update(PaymentsToAcquireProductiveAssets=310.0, ProceedsFromShortTermDebt=40.0, RepaymentsOfShortTermDebt=65.0)
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['components']['capital_expenditure'] == {'concepts': ['PaymentsToAcquireProductiveAssets'], 'value': 310.0}
    assert f['components']['net_short_term_borrowing'] == {'concepts': ['ProceedsFromShortTermDebt', 'RepaymentsOfShortTermDebt'], 'value': -25.0}
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


def test_no_us_gaap_cash_flow(tmp_path):
    latest = {k: v for k, v in FULL.items() if k != 'NetCashProvidedByUsedInOperatingActivities'}
    f = nvda(build(tmp_path, write_company(tmp_path, latest)))['fcfe']
    assert f['reason_codes'] == ['US_GAAP_CASH_FLOW_NOT_REPORTED'] and f['fcfe_per_share'] is None


MUTATIONS = [
    lambda p: p['data']['companies']['nvda']['fcfe'].update(price=100.0),
    lambda p: p['data']['companies']['nvda'].update(v_score=50),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(fcfe_per_share=9.0),
    lambda p: p['data']['companies']['nvda']['fcfe']['components'].update(long_term_debt_issuance=None),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['capital_expenditure'].update(concepts=['CapitalExpenditure']),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(reason_codes=['free text']),
    lambda p: p['data']['companies']['nvda']['fcfe'].update(state='NOT_AVAILABLE'),
    lambda p: p['data']['companies']['nvda']['fcfe']['components']['diluted_shares'].update(value=float('nan')),
    lambda p: p['data']['companies']['nvda']['v_inputs'].update(eps=None),
    lambda p: p['data'].update(fcfe_definition='fcfe/2'),
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
    script = "const a=require(process.argv[1]);process.stdout.write(JSON.stringify({ids:a.IDS,alt:a.ALTERNATIVES,f:a.FCFE_REASONS,v:a.V_REASONS,file:a.FILE,kind:a.KIND}))"
    out = json.loads(subprocess.run(['node', '-e', script, str(ASSETS / 'device-valuation.js')], capture_output=True, text=True, check=True).stdout)
    from investment_system.qgv.portfolio import OFFICIAL_V11_TARGETS
    assert out['ids'] == list(OFFICIAL_V11_TARGETS)
    assert {k: [list(a) for a in v] for k, v in api().ALTERNATIVES.items()} == out['alt']
    assert list(api().ALTERNATIVES) == list(out['alt'])
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
