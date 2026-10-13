"""Six fiscal reports, exact standard account IDs, receipt lineage, and v2 peer scoring."""
from datetime import datetime, timezone
import copy
import json
from urllib.parse import parse_qs, urlsplit

from tests.dart_fake_opendart import FakeOpenDart, FAKE_KEY, CORP_CODE, NOW, LISTS, _fs, _row
from tests.test_dart_collection import no_previous
from investment_system.product import dart_public as public
from investment_system.product.dart_qgv2 import reference_score
import dart_daily


class SixAnnualDart(FakeOpenDart):
    def __call__(self, url, *, timeout, max_bytes):
        parsed = urlsplit(url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        endpoint = parsed.path.rsplit('/', 1)[-1]
        if endpoint == 'list.json' and params.get('pblntf_ty') == 'A':
            self.requests.append((endpoint, params))
            rows = copy.deepcopy(LISTS['A']) + [_row(f'{year+1}0320000101', f'{year+1}0320', f'사업보고서 ({year}.12)') for year in range(2020, 2025)]
            rows = [r for r in rows if params['bgn_de'] <= r['rcept_dt'] <= params['end_de']]
            return self.json({'status': '000', 'page_no': 1, 'page_count': 100, 'total_count': len(rows), 'total_page': 1, 'list': rows})
        if endpoint == 'fnlttSinglAcntAll.json' and params['reprt_code'] == '11011' and params['fs_div'] == 'CFS':
            self.requests.append((endpoint, params))
            year = int(params['bsns_year']); growth = 1.1 ** (year - 2020)
            rows = []
            for account, statement, base in [
                ('ifrs-full_Revenue', 'IS', 200), ('dart_OperatingIncomeLoss', 'IS', 30),
                ('ifrs-full_ProfitLoss', 'IS', 20), ('ifrs-full_GrossProfit', 'IS', 70),
                ('ifrs-full_ProfitLossBeforeTax', 'IS', 25), ('ifrs-full_IncomeTaxExpenseContinuingOperations', 'IS', 5),
                ('ifrs-full_InterestExpense', 'IS', 2), ('ifrs-full_AdjustmentsForDepreciationAndAmortisationExpense', 'CF', 5),
                ('ifrs-full_CashFlowsFromUsedInOperatingActivities', 'CF', 25), ('ifrs-full_PurchaseOfPropertyPlantAndEquipment', 'CF', -5),
                ('ifrs-full_Assets', 'BS', 180), ('ifrs-full_CashAndCashEquivalents', 'BS', 10), ('ifrs-full_Equity', 'BS', 100),
                ('ifrs-full_ShorttermBorrowings', 'BS', 10), ('ifrs-full_LongtermBorrowings', 'BS', 20),
                ('ifrs-full_CurrentPortionOfLongtermBorrowings', 'BS', 2), ('ifrs-full_BondsIssued', 'BS', 5),
                ('ifrs-full_NoncurrentLeaseLiabilities', 'BS', 3), ('ifrs-full_CurrentLeaseLiabilities', 'BS', 1),
            ]:
                rows.append(_fs(account, statement, str(round(base*growth*1_000_000)), str(round(base*growth/1.1*1_000_000))))
            rows += [_fs('ifrs-full_DilutedEarningsLossPerShare', 'IS', str(round(20*growth, 6)), str(round(20*growth/1.1, 6))),
                     _fs('ifrs-full_AdjustedWeightedAverageShares', 'IS', '1000000')]
            receipt = f'{year+1}0320000101'
            return self.json({'status': '000', 'list': [{**r, 'rcept_no': receipt, 'reprt_code': '11011', 'bsns_year': str(year)} for r in rows]})
        return super().__call__(url, timeout=timeout, max_bytes=max_bytes)


def collect_history(tmp_path, budget=30):
    provider = SixAnnualDart()
    code = dart_daily.run(tmp_path, environ={'DART_API_KEY': FAKE_KEY}, transport=provider, now=NOW,
                          max_calls=budget, open_previous=no_previous, include_qgv2=True, collect_history=True)
    payload = public.require_financials(public.parse_json((tmp_path/public.FINANCIALS_FILENAME).read_bytes()))
    return provider, payload['companies']['hanmi'], code


def test_six_reported_fiscal_years_make_both_v2_axes_computable(tmp_path, capsys):
    provider, company, code = collect_history(tmp_path)
    assert code == 0 and len(provider.requests) <= 30
    history = company['annual_history']
    assert [r['bsns_year'] for r in history] == ['2025', '2024', '2023', '2022', '2021', '2020']
    assert all(r['source_sha256']['statements'] and r['v2_inputs']['units']['diluted_shares'] == 'SHARES' for r in history)
    assert company['qgv2']['reason_codes'] == []
    metrics = company['qgv2']['metrics']
    assert abs(metrics['revenue_cagr_3y'] - 0.1) < 1e-5
    assert metrics['moat_return_years'] == 5 and metrics['interest_coverage'] == 15
    universe = {str(i): {'cik': str(i), 'state': 'LIVE', 'profile': 'GENERAL', 'industry_group': None,
                         'metrics': {k: v*(0.5+i/10) if v is not None else None for k, v in metrics.items()}} for i in range(1, 10)}
    result = reference_score(company, universe)
    assert result['axes']['Q']['available_weight'] == result['axes']['G']['available_weight'] == 100
    assert result['axes']['Q']['factors_available'] == result['axes']['G']['factors_available'] == '5/5'
    assert result['cross_section_size'] == 9 and result['reference_only'] is True
    assert FAKE_KEY not in capsys.readouterr().out


def test_history_budget_stops_without_repeated_requests_and_keeps_missing_years_na(tmp_path):
    provider, company, code = collect_history(tmp_path, budget=12)
    assert code == 0 and len(provider.requests) == 12
    assert len(company.get('annual_history', [])) < 6
    assert 'DART_V2_5Y_HISTORY_NOT_COLLECTED' in company['qgv2']['reason_codes']


def test_wrong_fiscal_year_is_not_projected_into_the_requested_period(tmp_path):
    class WrongFiscalYear(SixAnnualDart):
        def __call__(self, url, **kwargs):
            response = super().__call__(url, **kwargs)
            params = parse_qs(urlsplit(url).query)
            if 'fnlttSinglAcntAll' in url and params.get('bsns_year') == ['2025']:
                payload = json.loads(response.body)
                for row in payload.get('list', []):
                    row['bsns_year'] = '2024'
                return self.json(payload)
            return response
    provider = WrongFiscalYear()
    assert dart_daily.run(tmp_path, environ={'DART_API_KEY': FAKE_KEY}, transport=provider, now=NOW,
                          open_previous=no_previous, include_qgv2=True, collect_history=True) == 0
    company = public.require_financials(public.parse_json((tmp_path/public.FINANCIALS_FILENAME).read_bytes()))['companies']['hanmi']
    assert company['annual']['state'] == 'NOT_AVAILABLE'
    assert company['annual']['reason_codes'] == ['DART_IDENTITY_MISMATCH']
    assert company['annual_history'] == []
    assert all(value is None for value in company['qgv2']['metrics'].values())


def test_finance_costs_are_not_assumed_to_be_interest_expense():
    from investment_system.providers import dart_collection as provider
    # FinanceCosts may include foreign exchange and other financial costs.
    payload = {'status': '000', 'list': [{**_fs('ifrs-full_FinanceCosts', 'IS', '2000000'), 'reprt_code': '11011'}]}
    inputs = provider.extract_v2_financials(payload, reprt_code='11011')
    assert inputs['inputs']['interest_expense'] is None
    assert inputs['missing']['interest_expense'] == 'MISSING'
