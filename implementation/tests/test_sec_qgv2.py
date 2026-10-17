"""QGV v2 Q·G: SEC factor math, percentile publication, `sec-qgv2.json` validators and daily wiring (synthetic data only)."""
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
import math
import re
from pathlib import Path
import shutil
import subprocess
import urllib.error

import pytest

from investment_system.qgv import v2_factors as vf
from investment_system.qgv import v2_scoring as vs
from investment_system.universe import sec_qgv2 as q
from investment_system.universe import sec_universe_shares as shares
from investment_system.universe import sec_universe_qg as qg

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 13, 22, 30, tzinfo=timezone.utc)
CUTOFF = NOW.date()


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_qgv2_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REF = load_tool('sec_qgv2_reference')


# ---------------- hand-checkable company ----------------
def fact(facts, concept, unit, value, end, *, start=None, form='10-K', filed=None, accn='0000000001-26-000001', taxonomy='us-gaap'):
    row = {'end': end, 'val': value, 'accn': accn, 'form': form, 'filed': filed or (str(int(end[:4]) + 1) + '-02-15'), 'fp': 'FY', 'fy': 2025}
    if start is not None:
        row['start'] = start
    facts.setdefault(taxonomy, {}).setdefault(concept, {'units': {}})['units'].setdefault(unit, []).append(row)


def simple_company(*, years=range(2019, 2026), extra=None, omit=()):
    """Revenue +10%/yr (146.41 in 2025), EBIT 20%, pretax = EBIT, tax 25%, NI = 75% of EBIT, equity 100, debt 50, cash 30."""
    facts = {}
    for year in years:
        k = 2025 - year
        rev = 146.41 / 1.1 ** k
        span = dict(start=f'{year}-01-01', end=f'{year}-12-31')
        for concept, unit, value in (('Revenues', 'USD', rev), ('OperatingIncomeLoss', 'USD', 0.2 * rev),
                                     ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'USD', 0.2 * rev),
                                     ('IncomeTaxExpenseBenefit', 'USD', 0.05 * rev), ('NetIncomeLoss', 'USD', 0.15 * rev),
                                     ('NetCashProvidedByUsedInOperatingActivities', 'USD', 0.18 * rev),
                                     ('PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 0.03 * rev),
                                     ('DepreciationDepletionAndAmortization', 'USD', 0.05 * rev), ('InterestExpense', 'USD', 2.0),
                                     ('GrossProfit', 'USD', 0.5 * rev), ('EarningsPerShareDiluted', 'USD/shares', 0.15 * rev / 10),
                                     ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 10.0)):
            if concept not in omit:
                fact(facts, concept, unit, value, span['end'], start=span['start'])
        for concept, value in (('Assets', 200.0), ('StockholdersEquity', 100.0), ('LongTermDebtNoncurrent', 40.0),
                               ('LongTermDebtCurrent', 10.0), ('CashAndCashEquivalentsAtCarryingValue', 30.0)):
            if concept not in omit:
                fact(facts, concept, 'USD', value, f'{year}-12-31')
    for args in extra or ():
        fact(facts, *args[0], **args[1])
    return {'cik': 1, 'facts': facts}


def compute(payload, sic='3674', cutoff=CUTOFF):
    return vf.compute(payload, sic=sic, cutoff=cutoff)


def test_general_metrics_match_hand_computation():
    profile, fy_end, currency, m, v = compute(simple_company())
    assert (profile, fy_end, currency) == ('GENERAL', '2025-12-31', 'USD')
    ic = 100 + 50 - 30  # equity + (noncurrent + current debt) - cash
    close = lambda a, b: math.isclose(a, b, rel_tol=1e-5)
    assert close(m['roic'], 0.2 * 146.41 * 0.75 / ic)
    assert close(m['gross_profit_to_assets'], 0.5 * 146.41 / 200)
    assert close(m['accruals_to_assets'], (0.15 - 0.18) * 146.41 / 200)
    assert close(m['fcf_to_net_income'], (0.18 - 0.03) / 0.15)
    assert close(m['net_debt_to_ebitda'], (50 - 30) / (0.25 * 146.41))
    assert close(m['interest_coverage'], 0.2 * 146.41 / 2)
    assert close(m['revenue_cagr_3y'], 0.1) and close(m['eps_cagr_3y'], 0.1) and close(m['fcf_per_share_cagr_3y'], 0.1)
    assert m['dilution_3y'] == 0.0  # constant share count: a real 0, not a fill
    assert m['incremental_roic_3y'] is None and m['incremental_roic_5y'] is None  # invested capital did not grow -> NA
    assert m['revenue_positive_growth_share'] == 1.0 and m['revenue_growth_volatility'] < 1e-6
    assert m['moat_return_years'] == 5 and close(m['moat_proxy'], m['moat_return_mean_5y'] - m['moat_return_std_5y'])
    assert close(m['revenue_ttm_growth'], 0.1) and abs(m['revenue_acceleration']) < 1e-5  # no 10-Q after FY0: TTM = FY
    for key in ('roe', 'roa', 'equity_to_assets', 'book_value_per_share_cagr_3y'):
        assert m[key] is None  # FINANCIAL-only metrics stay NA for GENERAL issuers
    assert v['ebit'] == {'fy_value': 0.2 * 146.41, 'fy_end': '2025-12-31', 'ttm_value': 0.2 * 146.41, 'ttm_end': '2025-12-31'}
    assert v['total_debt'] == {'value': 50.0, 'period_end': '2025-12-31'} and v['cash_and_equivalents'] == {'value': 30.0, 'period_end': '2025-12-31'}
    assert v['diluted_shares'] == {'value': 10.0, 'period_end': '2025-12-31'}
    assert [h['fiscal_year_end'] for h in v['ebit_per_share_history']] == [f'{y}-12-31' for y in range(2021, 2026)]


def test_ttm_uses_fy_plus_ytd_minus_prior_ytd_and_incremental_capital_rule():
    extra = []
    for year, value in ((2026, 80.0), (2025, 70.0), (2024, 60.0)):
        extra.append((('Revenues', 'USD', value, f'{year}-06-30'), {'start': f'{year}-01-01', 'form': '10-Q', 'filed': f'{year}-08-01'}))
    _, _, _, m, v = compute(simple_company(extra=extra))
    ttm = 146.41 + 80 - 70
    ttm_ago = 146.41 / 1.1 + 70 - 60
    assert math.isclose(m['revenue_ttm_growth'], ttm / ttm_ago - 1, rel_tol=1e-5)
    assert math.isclose(m['revenue_acceleration'], m['revenue_ttm_growth'] - m['revenue_cagr_3y'], abs_tol=2e-6)
    assert v['ebit']['ttm_end'] == '2025-12-31'  # no EBIT 10-Q facts -> TTM equals FY for EBIT


def test_revision_cutoff_and_ambiguity_rules():
    # Later 10-K/A restates FY2025 revenue: latest filed wins. A fact filed after the cutoff is ignored.
    extra = [(('Revenues', 'USD', 150.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K/A', 'filed': '2026-05-01'}),
             (('Revenues', 'USD', 999.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K/A', 'filed': '2026-12-01'})]
    _, _, _, m, _ = compute(simple_company(extra=extra))
    assert math.isclose(m['revenue_cagr_3y'], (150 / 110) ** (1 / 3) - 1, rel_tol=1e-5)
    # Same filed date, different values -> the period is dropped (FY0 falls back to the next concept or NA).
    clash = [(('Revenues', 'USD', 151.0, '2025-12-31'), {'start': '2025-01-01', 'form': '10-K', 'filed': '2026-02-15'})]
    _, _, _, m, _ = compute(simple_company(extra=clash))
    assert m['revenue_cagr_3y'] is None and m['revenue_acceleration'] is None


def test_missing_or_meaningless_inputs_are_none_never_zero():
    _, _, _, m, v = compute(simple_company(omit=('InterestExpense', 'DepreciationDepletionAndAmortization', 'LongTermDebtNoncurrent',
                                                  'LongTermDebtCurrent', 'GrossProfit'),
                                            extra=[(('ConvertibleNotesPayable', 'USD', 50.0, f'{y}-12-31'), {}) for y in range(2019, 2026)]))
    assert m['interest_coverage'] is None and m['net_debt_to_ebitda'] is None and m['gross_profit_to_assets'] is None
    # Invested capital needs a usable debt line: debt reported only outside the debt lines is NA, never 0 (rule NODEBT).
    assert m['roic'] is None
    assert v['total_debt'] is None
    # Negative earnings: FCF/NI and EPS CAGR are not meaningful.
    loss = simple_company()
    for row in loss['facts']['us-gaap']['NetIncomeLoss']['units']['USD']:
        row['val'] = -abs(row['val'])
    for row in loss['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']:
        row['val'] = -abs(row['val'])
    _, _, _, m, _ = compute(loss)
    assert m['fcf_to_net_income'] is None and m['eps_cagr_3y'] is None
    # No annual facts at all -> no fiscal year, nothing published.
    assert compute({'cik': 1, 'facts': {}})[1] is None
    assert compute(b'not json')[1] is None and compute({'cik': 1, 'facts': {'us-gaap': []}})[1] is None


def test_financial_profile_uses_roe_capital_ratio_nim_and_skips_earnings_quality():
    extra = [(('InterestIncomeExpenseNet', 'USD', 30.0, f'{y}-12-31'), {'start': f'{y}-01-01'}) for y in range(2019, 2026)]
    profile, _, _, m, _ = compute(simple_company(extra=extra), sic='6021')
    assert profile == 'FINANCIAL'
    assert math.isclose(m['roe'], 0.15 * 146.41 / 100, rel_tol=1e-5) and math.isclose(m['equity_to_assets'], 0.5)
    assert math.isclose(m['net_interest_income_to_assets'], 30 / 200) and math.isclose(m['roa'], 0.15 * 146.41 / 200, rel_tol=1e-5)
    assert m['roic'] is None and m['accruals_to_assets'] is None and m['fcf_to_net_income'] is None
    assert vs.SUBMETRICS['FINANCIAL']['q_earnings_quality'] == ()
    assert vf.profile_for_sic('6499') == 'FINANCIAL' and vf.profile_for_sic('6500') == 'GENERAL' and vf.profile_for_sic(None) == 'GENERAL'


def test_ifrs_filer_and_52_53_week_years():
    facts = {}
    for year, end in ((2022, '2022-12-25'), (2023, '2023-12-31'), (2024, '2024-12-29'), (2025, '2025-12-28')):
        start = {2022: '2021-12-27', 2023: '2022-12-26', 2024: '2024-01-01', 2025: '2024-12-30'}[year]
        fact(facts, 'Revenue', 'EUR', 100.0 * 1.2 ** (year - 2022), end, start=start, form='20-F', taxonomy='ifrs-full')
        fact(facts, 'ProfitLoss', 'EUR', 10.0, end, start=start, form='20-F', taxonomy='ifrs-full')
    profile, fy_end, currency, m, v = compute({'cik': 1, 'facts': facts})
    assert (fy_end, currency, v['taxonomy']) == ('2025-12-28', 'EUR', 'ifrs-full')
    assert math.isclose(m['revenue_cagr_3y'], 0.2, rel_tol=1e-5)


def test_debt_current_total_taxonomy_switch_and_single_concept_ttm():
    # DebtCurrent replaces current maturities + short-term borrowings (no double count).
    extra = [(('DebtCurrent', 'USD', 25.0, '2025-12-31'), {}), (('ShortTermBorrowings', 'USD', 15.0, '2025-12-31'), {})]
    _, _, _, _, v = compute(simple_company(omit=('LongTermDebtCurrent',), extra=extra))
    assert v['total_debt'] == {'value': 65.0, 'period_end': '2025-12-31'}
    # Latest debt date is chosen on its own (a later 10-Q with debt lines but no cash line).
    later = [(('LongTermDebtNoncurrent', 'USD', 70.0, '2026-06-30'), {'form': '10-Q', 'filed': '2026-08-01'})]
    _, _, _, _, v = compute(simple_company(extra=later))
    assert v['total_debt'] == {'value': 70.0, 'period_end': '2026-06-30'} and v['cash_and_equivalents']['period_end'] == '2025-12-31'
    # A YTD fact of another revenue concept never mixes with FY0 of the first concept: TTM falls back to FY0.
    mixed = [(('RevenueFromContractWithCustomerExcludingAssessedTax', 'USD', 80.0, '2026-06-30'),
              {'start': '2026-01-01', 'form': '10-Q', 'filed': '2026-08-01'})]
    _, _, _, m, _ = compute(simple_company(extra=mixed))
    assert math.isclose(m['revenue_ttm_growth'], 0.1, rel_tol=1e-5)
    # A filer whose latest annual data is in ifrs-full uses ifrs-full even with older us-gaap facts.
    old = simple_company(years=range(2010, 2014))
    for year in (2022, 2023, 2024, 2025):
        fact(old['facts'], 'Revenue', 'EUR', 100.0 + year, f'{year}-12-31', start=f'{year}-01-01', form='20-F', taxonomy='ifrs-full')
    _, fy_end, currency, _, v = compute(old)
    assert (fy_end, currency, v['taxonomy']) == ('2025-12-31', 'EUR', 'ifrs-full')


def test_utility_revenue_concept_fills_years_without_revenues_and_never_overrides_them():
    # Utility: `Revenues` up to 2021 (2021 also under the regulated+unregulated concept, same amount), the
    # regulated+unregulated total only from 2022. Every FY revenue resolves; the 3y CAGR is the +10%/yr path.
    payload = simple_company(omit=('Revenues',))
    for year in range(2019, 2026):
        rev = 146.41 / 1.1 ** (2025 - year)
        if year <= 2021:
            fact(payload['facts'], 'Revenues', 'USD', rev, f'{year}-12-31', start=f'{year}-01-01')
        if year >= 2021:
            fact(payload['facts'], 'RegulatedAndUnregulatedOperatingRevenue', 'USD', rev, f'{year}-12-31', start=f'{year}-01-01')
    _, fy_end, _, m, v = compute(payload, sic='4931')
    assert fy_end == '2025-12-31'
    assert math.isclose(m['revenue_cagr_3y'], 0.1, rel_tol=1e-5)
    assert m['revenue_positive_growth_share'] == 1.0 and m['revenue_growth_std_5y'] is not None
    assert math.isclose(v['revenue']['fy_value'], 146.41, rel_tol=1e-9)
    # Without the utility concept the same issuer has no FY0 revenue: NOT_AVAILABLE, never 0.
    only_old = simple_company(omit=('Revenues',))
    for year in range(2019, 2022):
        fact(only_old['facts'], 'Revenues', 'USD', 146.41 / 1.1 ** (2025 - year), f'{year}-12-31', start=f'{year}-01-01')
    _, _, _, m, v = compute(only_old, sic='4931')
    assert m['revenue_cagr_3y'] is None and v['revenue'] is None
    # Lowest priority: an issuer reporting `Revenues` keeps it even if it also tags a different regulated total.
    both = simple_company(extra=[(('RegulatedAndUnregulatedOperatingRevenue', 'USD', 999.0, '2025-12-31'), {'start': '2025-01-01'})])
    _, _, _, m, v = compute(both)
    assert math.isclose(v['revenue']['fy_value'], 146.41, rel_tol=1e-9) and math.isclose(m['revenue_cagr_3y'], 0.1, rel_tol=1e-5)


# ---------------- fallback lines (QGV_V2_QG_METHOD.md section 1) ----------------
def _annual_lines(shares_of_revenue, years=range(2019, 2026)):
    """[(concept, share of that year's revenue)] -> fact() args for every year (same span as simple_company)."""
    out = []
    for year in years:
        rev = 146.41 / 1.1 ** (2025 - year)
        out += [((concept, 'USD', share * rev, f'{year}-12-31'), {'start': f'{year}-01-01'}) for concept, share in shares_of_revenue]
    return out


BASE_ND_EBITDA = (50 - 30) / (0.25 * 146.41)  # simple_company: D&A 5% of revenue, EBIT 20%


def test_da_from_depreciation_plus_intangible_amortization_only_when_no_double_count():
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    dda = 'DepreciationDepletionAndAmortization'
    # (a) No total D&A concept: Depreciation + AmortizationOfIntangibleAssets of the same year (EME).
    gap = simple_company(omit=(dda,), extra=_annual_lines((('Depreciation', 0.02), ('AmortizationOfIntangibleAssets', 0.03))))
    assert close(compute(gap)[3]['net_debt_to_ebitda'], BASE_ND_EBITDA)
    # One component alone is not a D&A total: NA, the missing one is never 0-filled.
    only_dep = simple_company(omit=(dda,), extra=_annual_lines((('Depreciation', 0.05),)))
    assert compute(only_dep)[3]['net_debt_to_ebitda'] is None
    # A negative component is not used.
    negative = simple_company(omit=(dda,), extra=_annual_lines((('Depreciation', 0.06), ('AmortizationOfIntangibleAssets', -0.01))))
    assert compute(negative)[3]['net_debt_to_ebitda'] is None
    # (b) The total equals Depreciation and the intangible amortization is larger than the total, so the total cannot
    # contain it (FIX: DepreciationAndAmortization 62.4 = Depreciation 62.379, amortization 79.6): use the sum.
    fix = simple_company(omit=(dda,), extra=_annual_lines((('DepreciationAndAmortization', 0.0200), ('Depreciation', 0.019995),
                                                           ('AmortizationOfIntangibleAssets', 0.030005))))
    assert close(compute(fix)[3]['net_debt_to_ebitda'], BASE_ND_EBITDA)
    # The total equals Depreciation but the amortization is smaller than the total: it may already be inside the
    # total (BBY), so the total is kept and nothing is added (no double count).
    small = simple_company(extra=_annual_lines((('Depreciation', 0.05), ('AmortizationOfIntangibleAssets', 0.01))))
    assert close(compute(small)[3]['net_debt_to_ebitda'], BASE_ND_EBITDA)
    # A total that already is the sum (or any total not equal to Depreciation) is kept as reported.
    total_is_sum = simple_company(extra=_annual_lines((('Depreciation', 0.02), ('AmortizationOfIntangibleAssets', 0.03))))
    assert close(compute(total_is_sum)[3]['net_debt_to_ebitda'], BASE_ND_EBITDA)
    partial_total = simple_company(extra=_annual_lines((('Depreciation', 0.01), ('AmortizationOfIntangibleAssets', 0.08))))
    assert close(compute(partial_total)[3]['net_debt_to_ebitda'], BASE_ND_EBITDA)
    # Components of different fiscal spans are not added.
    shifted = simple_company(omit=(dda,), extra=_annual_lines((('Depreciation', 0.02),))
                             + [(('AmortizationOfIntangibleAssets', 'USD', 4.0, '2025-12-31'), {'start': '2024-12-25'})])
    assert compute(shifted)[3]['net_debt_to_ebitda'] is None


def test_pretax_income_from_domestic_plus_foreign_only_when_the_total_is_missing():
    pretax = 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
    ic = 100 + 50 - 30
    reported = 0.2 * 146.41 * 0.75 / ic  # 25% = tax / pretax
    default = 0.2 * 146.41 * (1 - vf.DEFAULT_TAX_RATE) / ic
    split = (('IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic', 0.15),
             ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign', 0.05))
    m = compute(simple_company(omit=(pretax,), extra=_annual_lines(split)))[3]
    assert math.isclose(m['roic'], reported, rel_tol=1e-5)  # DECK: domestic + foreign = pretax total
    # Only the domestic part: no total, default rate (the foreign part is never assumed to be 0).
    m = compute(simple_company(omit=(pretax,), extra=_annual_lines(split[:1])))[3]
    assert math.isclose(m['roic'], default, rel_tol=1e-5)
    # A reported total always wins over the split.
    m = compute(simple_company(extra=_annual_lines((split[0][:1] + (0.5,), split[1]))))[3]
    assert math.isclose(m['roic'], reported, rel_tol=1e-5)


def test_capex_fallback_lines_fill_only_an_unambiguous_single_line():
    ppe, close = 'PaymentsToAcquirePropertyPlantAndEquipment', lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    fcf_ni = (0.18 - 0.03) / 0.15
    for concept in ('PaymentsToAcquireOtherProductiveAssets', 'PaymentsToAcquireMachineryAndEquipment',
                    'PaymentsForCapitalImprovements', 'PaymentsToAcquireOtherPropertyPlantAndEquipment'):
        _, _, _, m, v = compute(simple_company(omit=(ppe,), extra=_annual_lines(((concept, 0.03),))))
        assert close(m['fcf_to_net_income'], fcf_ni) and close(m['fcf_per_share_cagr_3y'], 0.1), concept
        assert close(v['fcf']['fy_value'], 0.15 * 146.41) and v['fcf']['fy_end'] == '2025-12-31'
    # RL: ProductiveAssets up to FY-1, MachineryAndEquipment only in the FY0 10-K. Each year resolves.
    rl = simple_company(omit=(ppe,), extra=_annual_lines((('PaymentsToAcquireProductiveAssets', 0.03),), years=range(2019, 2025))
                        + _annual_lines((('PaymentsToAcquireMachineryAndEquipment', 0.03),), years=(2025,)))
    m = compute(rl)[3]
    assert close(m['fcf_to_net_income'], fcf_ni) and close(m['fcf_per_share_cagr_3y'], 0.1)
    # Two fallback lines in one year (LNT: utility + "other"), or one beside a partial capex line (EOG: oil and gas
    # property): each is a part of capex, so capex stays NA.
    for lines in ((('PaymentsToAcquireOtherProductiveAssets', 0.01), ('PaymentsToAcquireOtherPropertyPlantAndEquipment', 0.02)),
                  (('PaymentsToAcquireOtherPropertyPlantAndEquipment', 0.01), ('PaymentsToAcquireOilAndGasPropertyAndEquipment', 0.02))):
        _, _, _, m, v = compute(simple_company(omit=(ppe,), extra=_annual_lines(lines)))
        assert m['fcf_to_net_income'] is None and v['fcf'] is None
    # The priority list wins over every fallback line; capitalized software alone is not capex (rule SW adds it only to a
    # physical capex line).
    m = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireOtherProductiveAssets', 0.10),))))[3]
    assert close(m['fcf_to_net_income'], fcf_ni)
    _, _, _, m, v = compute(simple_company(omit=(ppe,), extra=_annual_lines((('PaymentsToAcquireSoftware', 0.03),))))
    assert m['fcf_to_net_income'] is None and v['fcf'] is None
    # TTM of a fallback line comes from that one concept (FY0 + YTD - prior YTD), like any other concept.
    ytd = [(('PaymentsToAcquireOtherProductiveAssets', 'USD', value, f'{year}-06-30'), {'start': f'{year}-01-01', 'form': '10-Q', 'filed': f'{year}-08-01'})
           for year, value in ((2026, 3.0), (2025, 2.0))]
    ytd += [(('NetCashProvidedByUsedInOperatingActivities', 'USD', value, f'{year}-06-30'), {'start': f'{year}-01-01', 'form': '10-Q', 'filed': f'{year}-08-01'})
            for year, value in ((2026, 15.0), (2025, 12.0))]
    v = compute(simple_company(omit=(ppe,), extra=_annual_lines((('PaymentsToAcquireOtherProductiveAssets', 0.03),)) + ytd))[4]
    assert v['fcf']['ttm_end'] == '2026-06-30'
    assert math.isclose(v['fcf']['ttm_value'], (0.18 * 146.41 + 15 - 12) - (0.03 * 146.41 + 3 - 2), rel_tol=1e-9)


def _ytd(concept, values, start_month='01'):
    """10-Q half-year YTD facts {year: value} (filed after the half year)."""
    return [((concept, 'USD', value, f'{year}-06-30'), {'start': f'{year}-{start_month}-01', 'form': '10-Q', 'filed': f'{year}-08-01'})
            for year, value in values.items()]


def test_capex_includes_capitalized_software_without_double_count():
    """Rule SW (owner decision Q-SW 2026-10-15): capitalized software is part of capex, added once to a physical line."""
    ppe, close = 'PaymentsToAcquirePropertyPlantAndEquipment', lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    fcf = lambda capex_share: (0.18 - capex_share) / 0.15
    # MA: PP&E 3% + PaymentsToAcquireSoftware 1% -> capex 4% every year (FCF, FCF/NI, FY FCF input).
    _, _, _, m, v = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireSoftware', 0.01),))))
    assert close(m['fcf_to_net_income'], fcf(0.04)) and close(m['fcf_per_share_cagr_3y'], 0.1)
    assert close(v['fcf']['fy_value'], 0.14 * 146.41) and close(v['fcf']['ttm_value'], 0.14 * 146.41)
    # Both parts are added (purchased + developed software).
    m = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireSoftware', 0.01), ('PaymentsToDevelopSoftware', 0.005)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.045))
    # PaymentsForSoftware is the total of the parts: used alone, the parts are not added a second time.
    m = compute(simple_company(extra=_annual_lines((('PaymentsForSoftware', 0.015), ('PaymentsToAcquireSoftware', 0.01),
                                                     ('PaymentsToDevelopSoftware', 0.005)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.045))
    # PaymentsToAcquireProductiveAssets already includes software by definition: nothing is added to it.
    m = compute(simple_company(omit=(ppe,), extra=_annual_lines((('PaymentsToAcquireProductiveAssets', 0.03),
                                                                  ('PaymentsToAcquireSoftware', 0.01)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.03))
    # A reported productive-assets total equal to PP&E means the software sits inside the PP&E line: not added.
    m = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireProductiveAssets', 0.03), ('PaymentsToAcquireSoftware', 0.01)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.03))
    # A productive-assets total that equals PP&E + software confirms separate lines: added.
    m = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireProductiveAssets', 0.04), ('PaymentsToAcquireSoftware', 0.01)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.04))
    # Added to the one F3 fallback line as well (INCY-type filer with software).
    m = compute(simple_company(omit=(ppe,), extra=_annual_lines((('PaymentsToAcquireOtherProductiveAssets', 0.03),
                                                                  ('PaymentsToAcquireSoftware', 0.01)))))[3]
    assert close(m['fcf_to_net_income'], fcf(0.04))
    # A software line of another span, or a negative one, is not added.
    shifted = simple_company(extra=[(('PaymentsToAcquireSoftware', 'USD', 1.0, '2025-12-31'), {'start': '2025-01-05'})])
    assert close(compute(shifted)[3]['fcf_to_net_income'], fcf(0.03))
    negative = simple_company(extra=_annual_lines((('PaymentsToAcquireSoftware', -0.01),)))
    assert close(compute(negative)[3]['fcf_to_net_income'], fcf(0.03))
    # TTM: PP&E TTM + software TTM when both end on the same 10-Q date.
    q = (_ytd(ppe, {2026: 3.0, 2025: 2.0}) + _ytd('PaymentsToAcquireSoftware', {2026: 1.5, 2025: 1.0})
         + _ytd('NetCashProvidedByUsedInOperatingActivities', {2026: 15.0, 2025: 12.0}))
    v = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireSoftware', 0.01),)) + q))[4]
    ocf_ttm, capex_ttm = 0.18 * 146.41 + 15 - 12, 0.03 * 146.41 + 3 - 2 + 0.01 * 146.41 + 1.5 - 1.0
    assert v['fcf']['ttm_end'] == '2026-06-30' and math.isclose(v['fcf']['ttm_value'], ocf_ttm - capex_ttm, rel_tol=1e-9)
    # Software without 10-Q facts while PP&E has them: the spans differ, so TTM capex (and TTM FCF) is NA; FY stays.
    v = compute(simple_company(extra=_annual_lines((('PaymentsToAcquireSoftware', 0.01),)) + q[:2] + q[4:]))[4]
    assert v['fcf']['ttm_value'] is None and close(v['fcf']['fy_value'], 0.14 * 146.41)


def test_reit_capital_improvements_are_never_the_capex_fallback():
    """Owner decision Q-MAA 2026-10-15: for SIC 6798 PaymentsForCapitalImprovements is a partial capex line (MAA)."""
    ppe, close = 'PaymentsToAcquirePropertyPlantAndEquipment', lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    improvements = _annual_lines((('PaymentsForCapitalImprovements', 0.03),))
    # Non-REIT (GLW, SNA, IT): the one fallback line is total capex, as before.
    _, _, _, m, v = compute(simple_company(omit=(ppe,), extra=improvements), sic='3357')
    assert close(m['fcf_to_net_income'], (0.18 - 0.03) / 0.15) and v['fcf'] is not None
    # REIT (MAA): capital improvements are only a part of capex, so F3 capex and FCF stay NA (never a partial FCF).
    _, _, _, m, v = compute(simple_company(omit=(ppe,), extra=improvements), sic='6798')
    assert m['fcf_to_net_income'] is None and m['fcf_per_share_cagr_3y'] is None and v['fcf'] is None
    # ... also when another fallback line is reported beside them: the improvements still mark F3 as partial.
    both = improvements + _annual_lines((('PaymentsToAcquireOtherProductiveAssets', 0.02),))
    assert compute(simple_company(omit=(ppe,), extra=both), sic='6798')[4]['fcf'] is None
    # A REIT's other single fallback line, and a REIT's reported PP&E capex, are unchanged.
    other = _annual_lines((('PaymentsToAcquireOtherProductiveAssets', 0.03),))
    assert close(compute(simple_company(omit=(ppe,), extra=other), sic='6798')[3]['fcf_to_net_income'], (0.18 - 0.03) / 0.15)
    assert close(compute(simple_company(extra=improvements), sic='6798')[3]['fcf_to_net_income'], (0.18 - 0.03) / 0.15)


def test_rsg_issuer_exception_uses_income_statement_revenue_only_for_the_listed_cik():
    """Owner decision Q-RSG 2026-10-15: CIK-keyed exception, not a blanket rule (REITs keep `Revenues`)."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    rfc = 'RevenueFromContractWithCustomerExcludingAssessedTax'

    def gross_company(cik, years=range(2019, 2026)):
        # `Revenues` is the gross segment total (+15% in FY0 only, so its CAGR differs); the income statement grows 10%/yr.
        payload = simple_company(omit=('Revenues', 'GrossProfit'), extra=_annual_lines((('CostOfRevenue', 0.6),)))
        payload['cik'] = cik
        for year in range(2019, 2026):
            rev = 146.41 / 1.1 ** (2025 - year)
            fact(payload['facts'], 'Revenues', 'USD', rev * (1.15 if year == 2025 else 1.0), f'{year}-12-31', start=f'{year}-01-01')
            if year in years:
                fact(payload['facts'], rfc, 'USD', rev, f'{year}-12-31', start=f'{year}-01-01')
        return payload

    _, _, _, m, v = compute(gross_company(1060391), sic='4953')
    assert close(m['revenue_cagr_3y'], 0.1) and close(v['revenue']['fy_value'], 146.41)
    assert close(m['gross_profit_to_assets'], 0.4 * 146.41 / 200)  # revenue - cost from the income-statement revenue
    assert close(v['operating_margin_history'][-1]['value'], 0.2)
    # The same CIK as a zero-padded string is recognized.
    assert close(compute(gross_company('0001060391'), sic='4953')[3]['revenue_cagr_3y'], 0.1)
    # Any other issuer keeps the priority list (`Revenues` first): the exception is not a blanket rule.
    _, _, _, m, v = compute(gross_company(1060392), sic='4953')
    assert close(v['revenue']['fy_value'], 146.41 * 1.15) and close(m['revenue_cagr_3y'], (1.15 * 1.1 ** 3) ** (1 / 3) - 1)
    # For the listed issuer a year without the listed concept is NA, never filled from the gross `Revenues`.
    _, _, _, m, v = compute(gross_company(1060391, years=(2023, 2024, 2025)), sic='4953')
    assert m['revenue_cagr_3y'] is None and close(v['revenue']['fy_value'], 146.41)
    assert vf.ISSUER_CONCEPT_EXCEPTIONS == {'0001060391': {'revenue': (rfc,)}}


def _instants(concept, value, years=range(2019, 2026)):
    return [((concept, 'USD', value, f'{year}-12-31'), {}) for year in years]


def test_debt_is_zero_only_without_any_debt_concept_and_without_interest_expense():
    """Owner decision Q-NODEBT 2026-10-15: conditional zero debt; finance-lease-only issuers carry the lease liability."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    debt_lines = ('LongTermDebtNoncurrent', 'LongTermDebtCurrent')
    nopat, ebitda = 0.2 * 146.41 * 0.75, 0.25 * 146.41
    # EME/INCY/DECK: no debt concept at all and no interest expense -> debt 0 (ROIC, net debt/EBITDA, debt input at FY0).
    _, _, _, m, v = compute(simple_company(omit=debt_lines + ('InterestExpense',)))
    assert close(m['roic'], nopat / (100 - 30)) and close(m['net_debt_to_ebitda'], -30 / ebitda)
    assert v['total_debt'] == {'value': 0.0, 'period_end': '2025-12-31'} and m['interest_coverage'] is None
    # An interest expense reported as exactly 0 is the same as unreported.
    zero_interest = simple_company(omit=debt_lines + ('InterestExpense',), extra=_annual_lines((('InterestExpense', 0.0),)))
    assert close(compute(zero_interest)[3]['roic'], nopat / (100 - 30))
    # ORCL/F/GM-type: no debt line in companyfacts but interest expense is reported -> debt is somewhere else: NA, never 0.
    _, _, _, m, v = compute(simple_company(omit=debt_lines))
    assert m['roic'] is None and m['net_debt_to_ebitda'] is None and v['total_debt'] is None
    for concept in ('InterestExpenseNonoperating', 'InterestExpenseDebt', 'InterestExpenseOther'):
        other = simple_company(omit=debt_lines + ('InterestExpense',), extra=_annual_lines(((concept, 0.01),)))
        assert compute(other)[3]['roic'] is None, concept
    # DXCM-type: debt reported under another concept (convertible notes) -> NA even without interest expense.
    for concept in ('ConvertibleDebtNoncurrent', 'SeniorNotes', 'LongTermLineOfCredit', 'DebtInstrumentCarryingAmount',
                    'NotesPayable', 'LongTermDebtCurrent'):
        other = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants(concept, 25.0))
        assert compute(other)[3]['roic'] is None and compute(other)[4]['total_debt'] is None, concept
    # A debt-evidence concept reported as 0 is a reported zero, not a debt.
    assert close(compute(simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('LineOfCredit', 0.0)))[3]['roic'],
                 nopat / (100 - 30))
    # Finance-lease liabilities only: debt = the lease liability (total, else noncurrent + current).
    lease = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('FinanceLeaseLiability', 12.0))
    assert close(compute(lease)[3]['roic'], nopat / (100 + 12 - 30)) and compute(lease)[4]['total_debt']['value'] == 12.0
    parts = simple_company(omit=debt_lines + ('InterestExpense',),
                           extra=_instants('FinanceLeaseLiabilityNoncurrent', 9.0) + _instants('FinanceLeaseLiabilityCurrent', 3.0))
    assert close(compute(parts)[3]['roic'], nopat / (100 + 12 - 30))
    only_noncurrent = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('FinanceLeaseLiabilityNoncurrent', 9.0))
    assert compute(only_noncurrent)[3]['roic'] is None  # the current part is never assumed 0
    # ... interest equal to the lease interest is the lease's; a larger interest expense means other debt: NA.
    lease_interest = _annual_lines((('FinanceLeaseInterestExpense', 0.004),))
    explained = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('FinanceLeaseLiability', 12.0)
                               + _annual_lines((('InterestExpense', 0.004),)) + lease_interest)
    assert close(compute(explained)[3]['roic'], nopat / (100 + 12 - 30))
    unexplained = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('FinanceLeaseLiability', 12.0)
                                 + _annual_lines((('InterestExpense', 0.02),)) + lease_interest)
    assert compute(unexplained)[3]['roic'] is None
    # MNST: a debt line at FY-1 that is gone at FY0 (repaid). FY0 debt is 0 and the latest debt input is the FY0 zero,
    # not the FY-1 amount.
    repaid = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('LongTermDebt', 374.0, years=(2024,)))
    _, _, _, m, v = compute(repaid)
    assert v['total_debt'] == {'value': 0.0, 'period_end': '2025-12-31'}
    assert close(m['roic'], nopat / ((100 - 30) + (100 + 374 - 30)) * 2)  # average of FY0 (0 debt) and FY-1 (374) capital
    # Issuers with debt lines keep the previous behavior exactly.
    assert compute(simple_company())[4]['total_debt'] == {'value': 50.0, 'period_end': '2025-12-31'}
    # ifrs-full payloads are unchanged (no debt line -> NA).
    facts = {}
    for year in (2023, 2024, 2025):
        for concept, value in (('Revenue', 100.0), ('ProfitLossFromOperatingActivities', 20.0), ('ProfitLoss', 15.0)):
            fact(facts, concept, 'EUR', value, f'{year}-12-31', start=f'{year}-01-01', form='20-F', taxonomy='ifrs-full')
        for concept, value in (('EquityAttributableToOwnersOfParent', 100.0), ('CashAndCashEquivalents', 30.0)):
            fact(facts, concept, 'EUR', value, f'{year}-12-31', form='20-F', taxonomy='ifrs-full')
    _, _, _, m, v = compute({'cik': 1, 'facts': facts})
    assert m['roic'] is None and v['total_debt'] is None


def test_ebit_substitute_is_pretax_plus_interest_and_is_flagged_as_an_estimate():
    """Owner decision Q-EBIT 2026-10-15: without operating income, EBIT = pretax income + interest expense, marked as an
    estimate (metrics.ebit_estimated_years; the app shows "추정(대체 계산)")."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5)
    ebit = lambda year: 0.2 * 146.41 / 1.1 ** (2025 - year) + 2.0  # pretax (= reported EBIT here) + interest 2.0
    ic = 100 + 50 - 30
    # KLAC/ETN-type: OperatingIncomeLoss never reported.
    _, _, _, m, v = compute(simple_company(omit=('OperatingIncomeLoss',)))
    assert close(m['roic'], ebit(2025) * 0.75 / ic) and close(m['interest_coverage'], ebit(2025) / 2.0)
    assert close(m['net_debt_to_ebitda'], (50 - 30) / (ebit(2025) + 0.05 * 146.41))
    assert m['moat_return_years'] == 5 and m['ebit_estimated_years'] == 6  # FY0..FY-5 all substituted
    assert m['ebit_estimated_fiscal_years'] == [2020, 2021, 2022, 2023, 2024, 2025]  # which years (owner Q-EBIT-SCOPE)
    assert close(v['ebit']['fy_value'], ebit(2025)) and v['ebit']['ttm_end'] == '2025-12-31' and close(v['ebit']['ttm_value'], ebit(2025))
    assert close(v['operating_margin_history'][-1]['value'], ebit(2025) / 146.41) and len(v['operating_margin_history']) == 5
    # ROK-type: operating income only for the last three years; the older years are substituted (and counted).
    recent = simple_company(omit=('OperatingIncomeLoss',), extra=_annual_lines((('OperatingIncomeLoss', 0.2),), years=(2023, 2024, 2025)))
    _, _, _, m, v = compute(recent)
    assert close(m['roic'], 0.2 * 146.41 * 0.75 / ic) and m['ebit_estimated_years'] == 3
    assert m['ebit_estimated_fiscal_years'] == [2020, 2021, 2022]  # the reported years 2023-2025 are not estimates
    assert close(v['ebit']['fy_value'], 0.2 * 146.41)
    # A reported operating income always wins: no estimate count is published.
    assert compute(simple_company())[3]['ebit_estimated_years'] is None
    assert compute(simple_company())[3]['ebit_estimated_fiscal_years'] is None
    # Both parts are needed: without an interest expense EBIT stays NA (never pretax + 0), and nothing is flagged.
    _, _, _, m, v = compute(simple_company(omit=('OperatingIncomeLoss', 'InterestExpense')))
    assert m['roic'] is None and m['interest_coverage'] is None and m['ebit_estimated_years'] is None and v['ebit'] is None
    # Parts of different spans are not added.
    shifted = simple_company(omit=('OperatingIncomeLoss', 'InterestExpense'),
                             extra=[(('InterestExpense', 'USD', 2.0, '2025-12-31'), {'start': '2025-01-05'})])
    assert compute(shifted)[4]['ebit'] is None
    # FINANCIAL issuers: interest expense is an operating cost of a bank, so no substitute (and no flag).
    _, _, _, m, v = compute(simple_company(omit=('OperatingIncomeLoss',)), sic='6021')
    assert m['ebit_estimated_years'] is None and v['ebit'] is None and v['operating_margin_history'] == []
    # TTM = TTM pretax + TTM interest when both end on the same 10-Q date; otherwise TTM EBIT is NA and FY stays.
    pretax = 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
    ytd = _ytd(pretax, {2026: 20.0, 2025: 15.0}) + _ytd('InterestExpense', {2026: 1.2, 2025: 1.0})
    v = compute(simple_company(omit=('OperatingIncomeLoss',), extra=ytd))[4]
    assert v['ebit']['ttm_end'] == '2026-06-30' and math.isclose(v['ebit']['ttm_value'], ebit(2025) + 20 - 15 + 1.2 - 1.0, rel_tol=1e-9)
    v = compute(simple_company(omit=('OperatingIncomeLoss',), extra=ytd[:2]))[4]
    assert v['ebit']['ttm_value'] is None and close(v['ebit']['fy_value'], ebit(2025))
    # Published through the SEC row and accepted by the strict validator; the DART key set stays METRIC_KEYS exactly.
    facts, subs = REF.synthetic_sec('0000001000', omit=('OperatingIncomeLoss',))
    row = q_build(facts, subs)
    assert row['metrics']['ebit_estimated_years'] == 6 and type(row['metrics']['ebit_estimated_years']) is int
    assert row['metrics']['ebit_estimated_fiscal_years'] == [2020, 2021, 2022, 2023, 2024, 2025]
    updates = REF.synthetic_universe_updates()
    updates[REF._codes()[0]] = row
    q.merge(None, updates, as_of=NOW, shard_index=0)  # require_qgv2 inside
    payload = json.loads(facts)
    tax, currency = vf._taxonomy_and_currency(payload, CUTOFF)
    plain = vf.compute_reported_periods(vf._Facts(payload, tax, currency, CUTOFF), fiscal_year_end=date(2025, 12, 31))[3]
    assert set(plain) == set(vf.METRIC_KEYS)


def q_build(facts, subs, cik='0000001000'):
    return q.build_row(cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=NOW - timedelta(hours=1))


def _split_company(*, factor=10.0, ratio_fact=10.0, split_filed='2026-02-15', comparatives=2, unit_error_fy=None, cik=1):
    """Each 10-K (FY y, filed y+1-02-15) reports diluted shares/EPS for y and `comparatives` earlier years. A split by
    `factor` (shares x factor) becomes effective before the filing dated `split_filed`: filings from then on report the
    post-split basis (100 shares every year), earlier ones the pre-split basis (100 / factor). `ratio_fact` is the
    StockholdersEquityNoteStockSplitConversionRatio1 value filed with it (None: not tagged)."""
    payload = simple_company(omit=('EarningsPerShareDiluted', 'WeightedAverageNumberOfDilutedSharesOutstanding'))
    payload['cik'] = cik
    for fy in range(2019, 2026):
        filed, accn = f'{fy + 1}-02-15', f'0000000001-{fy + 1 - 2000:02d}-000100'
        shares = 100.0 if filed >= split_filed else 100.0 / factor
        for year in range(max(2019, fy - comparatives), fy + 1):
            ni = 0.15 * 146.41 / 1.1 ** (2025 - year)
            reported = shares * (1000.0 if fy == unit_error_fy else 1.0)
            kw = dict(start=f'{year}-01-01', filed=filed, accn=accn)
            fact(payload['facts'], 'WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', reported, f'{year}-12-31', **kw)
            fact(payload['facts'], 'EarningsPerShareDiluted', 'USD/shares', ni / shares, f'{year}-12-31', **kw)
    if ratio_fact is not None:
        fact(payload['facts'], 'StockholdersEquityNoteStockSplitConversionRatio1', 'pure', ratio_fact, '2025-11-20',
             filed=split_filed, accn='0000000001-26-000100')
    return payload


def test_per_share_histories_are_split_adjusted_only_when_sec_facts_establish_the_ratio():
    """Owner decision Q-SPLIT 2026-10-15. KLAC/NFLX-type: FY-3 comes from a pre-split 10-K (the latest 10-K restates only
    FY0..FY-2). The restatement ratio of the periods both 10-Ks report, confirmed by the split-ratio fact, adjusts it."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-9)
    _, _, _, m, v = compute(_split_company())
    assert close(m['dilution_3y'], 0.0) and close(m['eps_cagr_3y'], 0.1) and close(m['fcf_per_share_cagr_3y'], 0.1)
    assert [h['fiscal_year_end'] for h in v['ebit_per_share_history']] == [f'{y}-12-31' for y in range(2021, 2026)]
    for h in v['ebit_per_share_history']:
        assert close(h['value'], 0.2 * 146.41 / 1.1 ** (2025 - int(h['fiscal_year_end'][:4])) / 100)
    assert close(v['eps_cagr_3y'], 0.1) and close(v['fcf_per_share_cagr_3y'], 0.1)
    # Reverse split (AMCR-type 1-for-5), tagged either as 0.2 or as 5: the direction comes from the restated counts.
    for tagged in (0.2, 5.0):
        m = compute(_split_company(factor=0.2, ratio_fact=tagged))[3]
        assert close(m['dilution_3y'], 0.0) and close(m['eps_cagr_3y'], 0.1), tagged
    # No split-ratio fact confirms the 10x restatement: the ratio is not established, so FY-3 per-share values are NA
    # (never guessed); FY0..FY-2 (restated in the latest 10-K) stay.
    _, _, _, m, v = compute(_split_company(ratio_fact=None))
    assert m['dilution_3y'] is None and m['eps_cagr_3y'] is None and m['fcf_per_share_cagr_3y'] is None
    assert [h['fiscal_year_end'] for h in v['ebit_per_share_history']] == ['2023-12-31', '2024-12-31', '2025-12-31']
    # A restatement that matches no reported ratio (WRB-type 1,000x unit change next to a real 3-for-2 split fact): NA.
    m = compute(_split_company(factor=1000.0, ratio_fact=1.5))[3]
    assert m['dilution_3y'] is None and m['eps_cagr_3y'] is None
    # Filings that share no period: a split-ratio fact filed between them means the basis is unknown -> NA ...
    m = compute(_split_company(comparatives=0))[3]
    assert m['dilution_3y'] is None and m['eps_cagr_3y'] is None
    # ... without one, nothing suggests a split and values are used as reported (simple_company: one year per 10-K).
    assert compute(simple_company())[3]['dilution_3y'] == 0.0
    # An unexplained discontinuity (a 1,000x share count in one older filing, no shared period, no split fact): NA.
    m = compute(_split_company(factor=1.0, ratio_fact=None, comparatives=0, unit_error_fy=2022))[3]
    assert m['dilution_3y'] is None and m['eps_cagr_3y'] is None and m['fcf_per_share_cagr_3y'] is None
    # Ordinary revisions (within 5%) are one basis: no adjustment, values as reported.
    m = compute(_split_company(factor=1.03, ratio_fact=None))[3]
    assert close(m['dilution_3y'], (1.0 / (1.0 / 1.03)) ** (1 / 3) - 1)


def test_split_after_fy0_blocks_per_share_history_until_the_basis_is_established():
    """The device pairs the per-share histories with the latest share count. A split filed in a 10-Q after FY0 that no
    shared period links to the FY0 10-K leaves the histories NA; the FY0-basis Q/G metrics are unaffected."""
    payload = simple_company()
    q = dict(start='2026-04-01', form='10-Q', filed='2026-08-01', accn='0000000001-26-000200')
    fact(payload['facts'], 'WeightedAverageNumberOfDilutedSharesOutstanding', 'shares', 100.0, '2026-06-30', **q)
    fact(payload['facts'], 'StockholdersEquityNoteStockSplitConversionRatio1', 'pure', 10.0, '2026-06-30',
         form='10-Q', filed='2026-08-01', accn='0000000001-26-000200')
    _, _, _, m, v = compute(payload)
    assert v['diluted_shares'] == {'value': 100.0, 'period_end': '2026-06-30'}
    assert v['ebit_per_share_history'] == [] and v['fcf_per_share_history'] == []
    assert m['dilution_3y'] == 0.0 and math.isclose(m['eps_cagr_3y'], 0.1, rel_tol=1e-5)
    # Without the split fact the latest 10-Q count is taken as the same basis (as before).
    payload['facts']['us-gaap'].pop('StockholdersEquityNoteStockSplitConversionRatio1')
    assert len(compute(payload)[4]['ebit_per_share_history']) == 5


def test_quality_inputs_roic_avg_3y_and_operating_margin_std_are_published_pricefree():
    """Owner decision Q-APPQ 2026-10-15: public fields for the PLAYBOOK §17 #19 quality judgement."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-12)
    roic = lambda year: 0.2 * 146.41 / 1.1 ** (2025 - year) * 0.75 / 120
    m = compute(simple_company())[3]
    assert close(m['roic_avg_3y'], (roic(2025) + roic(2024) + roic(2023)) / 3)
    assert m['operating_margin_std_5y_pp'] == 0.0  # a constant 20% margin: a real zero spread, not a fill
    # Population std of FY0..FY-4 EBIT/revenue, in percentage points.
    margins = {2021: 0.25, 2022: 0.20, 2023: 0.18, 2024: 0.22, 2025: 0.20}
    varied = simple_company(omit=('OperatingIncomeLoss',), extra=[(('OperatingIncomeLoss', 'USD', share * 146.41 / 1.1 ** (2025 - year),
                                                                    f'{year}-12-31'), {'start': f'{year}-01-01'})
                                                                  for year, share in margins.items()])
    mu = sum(margins.values()) / 5
    assert close(compute(varied)[3]['operating_margin_std_5y_pp'], 100 * math.sqrt(sum((x - mu) ** 2 for x in margins.values()) / 5))
    # All years are needed: two ROIC years or four margins give NA, never a partial value.
    assert compute(simple_company(years=range(2024, 2026)))[3]['roic_avg_3y'] is None  # only two fiscal years
    m = compute(simple_company(years=range(2022, 2026)))[3]
    assert m['roic_avg_3y'] is not None and m['operating_margin_std_5y_pp'] is None
    # FINANCIAL rows: no ROIC (so no 3-year average); the margin spread is published when operating income exists.
    m = compute(simple_company(), sic='6021')[3]
    assert m['roic_avg_3y'] is None and m['operating_margin_std_5y_pp'] == 0.0
    # Published in the SEC row (sparse, rounded like every metric) and accepted by the strict validator.
    facts, subs = REF.synthetic_sec('0000001000')
    row = q_build(facts, subs)
    assert {'roic_avg_3y', 'operating_margin_std_5y_pp'} <= set(row['metrics'])
    updates = REF.synthetic_universe_updates()
    updates[REF._codes()[0]] = row
    q.merge(None, updates, as_of=NOW, shard_index=0)
    # The app's quality rule reads exactly these keys: 3 conditions pass / one fails / one missing -> NA.
    from investment_system.qgv import playbook as pb
    cfg = pb.load_config()
    facts = lambda **kw: {'sic': 3674, 'net_debt_to_ebitda': 1.0, 'roic_avg_3y': 0.2, 'operating_margin_std_5y_pp': 2.0, **kw}
    assert pb.classify_types_v0(cfg, facts())['quality']['member'] is True
    assert pb.classify_types_v0(cfg, facts(operating_margin_std_5y_pp=3.0))['quality']['member'] is False
    missing = facts()
    missing.pop('roic_avg_3y')
    assert pb.classify_types_v0(cfg, missing)['quality']['member'] is None


def test_nodebt_issuers_reporting_debt_under_other_tags_are_never_zero_debt():
    """Owner supplement 2026-10-15 (Q-NODEBT): DXCM/ORCL/F/GM-type patterns. Debt is the reported amount or NA, never 0."""
    debt_lines = ('LongTermDebtNoncurrent', 'LongTermDebtCurrent')
    base = dict(omit=debt_lines + ('InterestExpense',))
    # Only one standard debt line: that line is the debt (never replaced by the debt-free rule).
    for concept, amount in (('LongTermDebtNoncurrent', 40.0), ('CommercialPaper', 15.0), ('LongTermDebt', 55.0)):
        _, _, _, m, v = compute(simple_company(**base, extra=_instants(concept, amount)))
        assert v['total_debt'] == {'value': amount, 'period_end': '2025-12-31'}, concept
        assert m['net_debt_to_ebitda'] is not None and m['net_debt_to_ebitda'] > -30 / (0.25 * 146.41), concept
    # Debt only under other borrowing concepts (convertible notes, debt instrument amounts): NA, not 0, with or without
    # interest expense.
    for concept in ('ConvertibleNotesPayable', 'ConvertibleDebtNoncurrent', 'DebtInstrumentCarryingAmount', 'SeniorLongTermNotes'):
        for interest in ([], _annual_lines((('InterestExpense', 0.01),))):
            _, _, _, m, v = compute(simple_company(**base, extra=_instants(concept, 30.0) + interest))
            assert v['total_debt'] is None and m['roic'] is None and m['net_debt_to_ebitda'] is None, concept
    # Debt under the issuer's own extension tags (invisible in companyfacts) shows up as interest expense: NA, not 0.
    for concept in ('InterestExpense', 'InterestExpenseNonoperating', 'InterestAndDebtExpense', 'InterestExpenseDebt'):
        _, _, _, m, v = compute(simple_company(**base, extra=_annual_lines(((concept, 0.02),))))
        assert v['total_debt'] is None and m['roic'] is None, concept
    # No zero anywhere in the published debt input for these patterns (a 0.0 would only come from the debt-free rule).
    _, _, _, _, v = compute(simple_company(**base, extra=_instants('ConvertibleNotesPayable', 30.0)))
    assert v['total_debt'] is None


def _device_v(v, closes=None):
    """Device V for one v_inputs_v2 (qgv2-inputs.js normalize -> qgv-v2.js scoreUniverse, synthetic price 10 USD;
    `closes` = device month-end closes {YYYY-MM: close}, default none)."""
    script = ("const W=process.argv[1],I=require(W+'/qgv2-inputs.js'),V2=require(W+'/qgv-v2.js');"
              "const TC=require(W+'/type-config-defaults.js'),P=require(W+'/dcf-parameters-defaults.js'),v=JSON.parse(process.argv[2]);"
              "const row={cik:'0000001000',state:'LIVE',fiscal_year_end:v.fiscal_year_end,profile:'GENERAL',industry_group:'g',sic:'3674',"
              "currency:'USD',metrics:{},factors:{},axes:{},v_inputs_v2:v},rec=I.normalize(row,true);"
              "const o=V2.scoreUniverse({'X:A':rec},{'X:A':{price:10,currency:'USD',month_closes:JSON.parse(process.argv[3])}},{typeConfig:TC,parameters:P})['X:A'];"
              "process.stdout.write(JSON.stringify({total_debt:rec.v_inputs.total_debt,cash:rec.v_inputs.cash,diluted_shares:rec.v_inputs.diluted_shares,"
              "fcf_yield:o.detail.fcf_yield,ebit_yield:o.detail.ebit_yield,implied_growth:o.detail.implied_growth,"
              "reasons:Object.fromEntries(Object.entries(o.factors).filter(([k])=>k.startsWith('v_')).map(([k,f])=>[k,f.reason])),"
              "v_scores:Object.fromEntries(Object.entries(o.factors).filter(([k])=>k.startsWith('v_')).map(([k,f])=>[k,f.score])),"
              "v_axis:o.axes.V.score,reference_range:o.reference_range,"
              "fcf_reason:o.factors.v_fcf_yield.reason,ebit_reason:o.factors.v_earnings_yield.reason}));")
    out = subprocess.run(['node', '-e', script, str(ROOT / 'src/investment_system/product/web_assets'), json.dumps(v),
                          json.dumps(closes or {})], text=True, capture_output=True, timeout=60, check=True)
    return json.loads(out.stdout)


def test_v_inputs_stale_balance_sheet_values_are_na():
    """V-STALE-BS (2026-10-17 number check, calc_version 2026-10-17.1): total_debt / cash_and_equivalents dated before the FY0
    balance sheet are NA, never the last value reported years earlier; Q-NODEBT-INT issuers get no debt and so no EV, and the
    device FCF / EBIT yield is NA with reason DEBT_CASH_NOT_AVAILABLE (missing never becomes 0)."""
    assert vf.CALC_VERSION == 'qgv2-calc/2026-10-17.1' and re.fullmatch(vf.CALC_VERSION_PATTERN, vf.CALC_VERSION)
    debt_lines = ('LongTermDebtNoncurrent', 'LongTermDebtCurrent')
    # INCY/EME/DECK-type: the only debt fact is years before FY0 and the NODEBT rule is NA (interest expense reported):
    # total_debt NA (was 19,094 from 2018 / 5.3 from 2023 / 0 from 2021), Q metrics as before (they use FY0 debt only).
    for year, amount in ((2018, 19094.0), (2023, 5.3), (2021, 0.0)):
        _, _, _, m, v = compute(simple_company(omit=debt_lines, extra=_instants('LongTermDebt', amount, years=(year,))))
        assert v['total_debt'] is None and m['net_debt_to_ebitda'] is None and m['roic'] is None, year
        assert v['cash_and_equivalents'] == {'value': 30.0, 'period_end': '2025-12-31'}
    # The same through the published SEC row (strict row shape, current calc_version).
    facts, subs = REF.synthetic_sec('0000001000', omit=('LongTermDebtNoncurrent',))
    payload = json.loads(facts)
    payload['facts']['us-gaap']['LongTermDebt'] = {'units': {'USD': [{'end': '2018-12-31', 'val': 19094.0, 'accn': '0000001000-19-000010',
                                                                       'form': '10-K', 'filed': '2019-02-15', 'fy': 2018, 'fp': 'FY'}]}}
    row = q_build(json.dumps(payload).encode(), subs)
    assert row['calc_version'] == vf.CALC_VERSION and row['fiscal_year_end'] == '2025-12-31'
    assert row['v_inputs_v2']['total_debt'] is None and row['v_inputs_v2']['cash_and_equivalents'] is not None
    # FY0 debt: unchanged (FY0 line; a later 10-Q date is the latest balance sheet, as before).
    assert compute(simple_company())[4]['total_debt'] == {'value': 50.0, 'period_end': '2025-12-31'}
    later = simple_company(extra=[(('LongTermDebtNoncurrent', 'USD', 45.0, '2026-06-30'), {'form': '10-Q', 'filed': '2026-08-01'})])
    assert compute(later)[4]['total_debt'] == {'value': 45.0, 'period_end': '2026-06-30'}
    # A balance sheet dated within the FY0 instant tolerance (52/53-week years) is the FY0 balance sheet: kept.
    near = simple_company(omit=debt_lines, extra=[(('LongTermDebt', 'USD', 44.0, '2025-12-27'), {})])
    assert compute(near)[4]['total_debt'] == {'value': 44.0, 'period_end': '2025-12-27'}
    # MNST-type (approved NODEBT zero): a debt line at FY-1 only and no interest expense -> 0 at FY0 is allowed.
    repaid = simple_company(omit=debt_lines + ('InterestExpense',), extra=_instants('LongTermDebt', 374.0, years=(2024,)))
    assert compute(repaid)[4]['total_debt'] == {'value': 0.0, 'period_end': '2025-12-31'}
    # PCAR-type cash: the latest cash fact is years before FY0 -> cash NA (never the stale value, never 0); FY0 cash kept.
    stale_cash = simple_company(omit=('CashAndCashEquivalentsAtCarryingValue',),
                                extra=_instants('CashAndCashEquivalentsAtCarryingValue', 30.0, years=(2019,)))
    _, _, _, _, v = compute(stale_cash)
    assert v['cash_and_equivalents'] is None and v['total_debt'] == {'value': 50.0, 'period_end': '2025-12-31'}
    assert compute(simple_company())[4]['cash_and_equivalents'] == {'value': 30.0, 'period_end': '2025-12-31'}
    if shutil.which('node') is None:
        return
    # Device: no EV -> FCF yield (and EBIT yield) NA with reason DEBT_CASH_NOT_AVAILABLE; never a zero-filled debt or cash.
    stale = compute(simple_company(omit=debt_lines, extra=_instants('LongTermDebt', 19094.0, years=(2018,))))[4]
    for v in (stale, compute(stale_cash)[4]):
        d = _device_v(v)
        assert d['fcf_yield'] is None and d['ebit_yield'] is None
        assert d['fcf_reason'] == d['ebit_reason'] == 'DEBT_CASH_NOT_AVAILABLE'
    assert _device_v(stale)['total_debt'] is None and _device_v(compute(stale_cash)[4])['cash'] is None
    d = _device_v(compute(simple_company())[4])  # FY0 debt: EV = 10 x 10 + 50 - 30 = 120
    assert math.isclose(d['fcf_yield'], (0.18 - 0.03) * 146.41 / 120, rel_tol=1e-6)
    d = _device_v(compute(repaid)[4])  # zero debt: EV = 100 - 30 = 70
    assert d['total_debt'] == 0 and math.isclose(d['fcf_yield'], (0.18 - 0.03) * 146.41 / 70, rel_tol=1e-6)


DILUTED = 'WeightedAverageNumberOfDilutedSharesOutstanding'
BASIC_AND_DILUTED = 'WeightedAverageNumberOfShareOutstandingBasicAndDiluted'


def _shares(concept, value, start, end, form='10-Q', filed=None):
    return ((concept, 'shares', value, end), {'start': start, 'form': form, 'filed': filed or ('2026-08-01' if end >= '2026' else None)})


def _other_share_counts():
    """Fresh share counts under concepts that are NOT allowed for diluted shares (never a substitute)."""
    return [(('WeightedAverageNumberOfSharesOutstandingBasic', 'shares', 9.0, '2026-06-30'), {'start': '2026-04-01', 'form': '10-Q', 'filed': '2026-08-01'}),
            (('CommonStockSharesOutstanding', 'shares', 9.5, '2026-06-30'), {'form': '10-Q', 'filed': '2026-08-01'}),
            (('EntityCommonStockSharesOutstanding', 'shares', 9.6, '2026-07-25'), {'form': '10-Q', 'filed': '2026-08-01', 'taxonomy': 'dei'})]


def test_v_inputs_diluted_shares_newest_allowed_concept_by_period_end_else_na():
    """V-STALE-SHARES (owner decision 2026-10-17, calc_version 2026-10-17.1): v_inputs_v2.diluted_shares is the latest-ending
    positive fact over ALL allowed diluted-share concepts (latest_duration read only the first concept with any fact: BKR 2021,
    REG 2020, TTWO 2024, HSY 2015, LYB 2019, SJM 2023, ERIE 2021), judged by its period END against FY0 end minus the
    YEAR_TOLERANCE_DAYS of V-STALE-BS, only from facts filed by the cutoff; else NA. Never basic shares / shares outstanding.
    The shared selection functions and the Q·G metrics are unchanged."""
    assert vf.CALC_VERSION == 'qgv2-calc/2026-10-17.1'
    assert vf.CONCEPTS['us-gaap']['diluted_shares'] == (DILUTED, BASIC_AND_DILUTED)
    q = dict(form='10-Q', filed='2026-08-01')
    # (a) First allowed concept stale (2021 quarter only), the second allowed concept fresh (FY0 annual + 2026 Q2):
    #     the newest period end of the allowed concepts is used (quarter span, as latest_duration within a concept).
    stale_first = [_shares(DILUTED, 806.0, '2021-04-01', '2021-06-30', filed='2021-07-23')]
    fresh_second = [_shares(BASIC_AND_DILUTED, 10.0, '2025-01-01', '2025-12-31', form='10-K', filed='2026-02-15'),
                    _shares(BASIC_AND_DILUTED, 10.4, '2026-01-01', '2026-06-30', **q),
                    _shares(BASIC_AND_DILUTED, 10.5, '2026-04-01', '2026-06-30', **q)]
    payload = simple_company(omit=(DILUTED,), extra=stale_first + fresh_second + _other_share_counts())
    facts = vf._Facts(payload, 'us-gaap', 'USD', CUTOFF)
    assert facts.latest_duration('diluted_shares') == (806.0, date(2021, 6, 30))  # shared first-concept rule: unchanged
    v = compute(payload)[4]
    assert v['diluted_shares'] == {'value': 10.5, 'period_end': '2026-06-30'}
    # ... and only facts filed by the cutoff (as_of): the same 2026 Q2 value filed after the cutoff is not available.
    late = [_shares(BASIC_AND_DILUTED, 10.5, '2026-04-01', '2026-06-30', form='10-Q', filed='2026-08-01')]
    early_cut = date(2026, 7, 31)
    assert compute(simple_company(omit=(DILUTED,), extra=stale_first + late), cutoff=early_cut)[4]['diluted_shares'] is None
    assert compute(simple_company(omit=(DILUTED,), extra=stale_first + late))[4]['diluted_shares'] == {'value': 10.5, 'period_end': '2026-06-30'}
    # (b) All allowed concepts stale (BKR/TTWO-type: 2021 and 2017; HSY-type: one concept, 2015) -> NA, never another
    #     concept (basic, shares outstanding, dei cover count are fresh here), never 0; Q·G metrics are unchanged by it.
    for extra in (stale_first + [_shares(BASIC_AND_DILUTED, 100.0, '2017-04-01', '2017-06-30', filed='2017-07-28')],
                  [_shares(DILUTED, 220.0, '2015-07-06', '2015-10-04', filed='2015-10-30')]):
        payload = simple_company(omit=(DILUTED,), extra=extra + _other_share_counts())
        _, fy0, _, m, v = compute(payload)
        assert fy0 == '2025-12-31' and v['diluted_shares'] is None, extra
        assert m == compute(simple_company(omit=(DILUTED,), extra=_other_share_counts()))[3]
    # Period end, not the filing date: a fresh filing (2026) restating an old period (2019) is still stale.
    restated = [_shares(DILUTED, 9.0, '2019-01-01', '2019-12-31', form='10-K', filed='2026-02-15')]
    assert compute(simple_company(omit=(DILUTED,), extra=restated))[4]['diluted_shares'] is None
    # The FY0 tolerance of V-STALE-BS: an end within YEAR_TOLERANCE_DAYS before FY0 end (52/53-week year) is FY0's count;
    # one day further is stale.
    assert vf.YEAR_TOLERANCE_DAYS == 10
    for end, expected in (('2025-12-21', {'value': 9.0, 'period_end': '2025-12-21'}), ('2025-12-20', None)):
        near = [_shares(DILUTED, 9.0, '2025-09-21', end, filed='2026-01-30')]
        assert compute(simple_company(omit=(DILUTED,), extra=near))[4]['diluted_shares'] == expected, end
    # (c) A valid fresh value is kept unchanged: FY0 annual of the first concept; a later 10-Q quarter of it; at the same
    #     period end the first concept wins over the second (no change for issuers whose first concept is current).
    assert compute(simple_company())[4]['diluted_shares'] == {'value': 10.0, 'period_end': '2025-12-31'}
    later = [_shares(DILUTED, 10.2, '2026-04-01', '2026-06-30', **q), _shares(BASIC_AND_DILUTED, 99.0, '2026-04-01', '2026-06-30', **q),
             _shares(BASIC_AND_DILUTED, 98.0, '2025-01-01', '2025-12-31', form='10-K', filed='2026-02-15')]
    v = compute(simple_company(extra=later + _other_share_counts()))[4]
    assert v['diluted_shares'] == {'value': 10.2, 'period_end': '2026-06-30'}
    assert len(v['ebit_per_share_history']) == 5 and len(v['fcf_per_share_history']) == 5
    assert v['ebit_per_share_history'] == compute(simple_company())[4]['ebit_per_share_history']
    # Through the published SEC row (strict row shape): stale diluted shares -> null in v_inputs_v2.
    facts_b, subs = REF.synthetic_sec('0000001000')
    payload = json.loads(facts_b)
    payload['facts']['us-gaap'][DILUTED] = {'units': {'shares': [{'start': '2015-07-06', 'end': '2015-10-04', 'val': 220.0, 'accn': '0000001000-15-000030',
                                                                  'form': '10-Q', 'filed': '2015-10-30', 'fy': 2015, 'fp': 'Q3'}]}}
    for concept, row in (('WeightedAverageNumberOfSharesOutstandingBasic', {'start': '2026-04-01'}), ('CommonStockSharesOutstanding', {})):
        payload['facts']['us-gaap'][concept] = {'units': {'shares': [dict(row, end='2026-06-30', val=101.0, accn='0000001000-26-000020', form='10-Q', filed='2026-08-01')]}}
    row = q_build(json.dumps(payload).encode(), subs)
    assert row['calc_version'] == vf.CALC_VERSION and row['fiscal_year_end'] == '2025-12-31' and row['state'] == 'LIVE'
    assert row['v_inputs_v2']['diluted_shares'] is None and row['v_inputs_v2']['total_debt'] is not None
    if shutil.which('node') is None:
        return
    # (d) Device (qgv2-inputs.js -> qgv-v2.js): no share count -> every per-share and EV-based V metric NA with the existing
    #     reason SHARES_NOT_AVAILABLE (EBIT/FCF yield, industry, own history, expectation check), DCF reference range NA;
    #     the device reads only v_inputs_v2.diluted_shares, so no other share value (cover count, basic) can stand in.
    closes = {f'{y}-12': 100.0 for y in range(2015, 2026)}
    v = dict(row['v_inputs_v2'], shares_outstanding={'value': 101.0, 'period_end': '2026-06-30'})
    for d in (_device_v(row['v_inputs_v2'], closes), _device_v(v, closes)):
        assert d['diluted_shares'] is None and d['ebit_yield'] is None and d['fcf_yield'] is None and d['implied_growth'] is None
        assert d['reasons'] == {k: 'SHARES_NOT_AVAILABLE' for k in ('v_earnings_yield', 'v_fcf_yield', 'v_vs_industry',
                                                                    'v_vs_own_history', 'v_expectation_check')}
        assert set(d['v_scores'].values()) == {None} and d['v_axis'] is None
        assert d['reference_range'] == {'state': 'NOT_AVAILABLE', 'reason': 'FCF_NOT_AVAILABLE', 'low': None, 'high': None}
    # The fresh row of the same issuer keeps its device V (control).
    fresh = q_build(*REF.synthetic_sec('0000001000'))
    d = _device_v(fresh['v_inputs_v2'], closes)
    assert d['diluted_shares'] == fresh['v_inputs_v2']['diluted_shares']['value'] and d['fcf_yield'] is not None
    assert d['reasons']['v_fcf_yield'] != 'SHARES_NOT_AVAILABLE'


COVER = 'EntityCommonStockSharesOutstanding'
K_ACCN, Q_ACCN = '0000000001-26-000001', '0000000001-26-000200'  # simple_company's 10-K accession; a 2026 Q2 10-Q


def _cover(value, accn=K_ACCN, end='2026-02-10', form='10-K', filed='2026-02-15'):
    """dei cover share count (EntityCommonStockSharesOutstanding) reported in filing `accn`."""
    return ((COVER, 'shares', value, end), {'form': form, 'filed': filed, 'accn': accn, 'taxonomy': 'dei'})


def _q2(concept, value, start='2026-04-01', accn=Q_ACCN):
    return ((concept, 'shares', value, '2026-06-30'), {'start': start, 'form': '10-Q', 'filed': '2026-08-01', 'accn': accn})


def test_v_inputs_diluted_shares_scale_unconfirmed_is_na_never_rescaled():
    """V-SHARES-SCALE (owner decision 2026-10-17 on the MCD/WAT unit errors, calc_version 2026-10-17.1, no bump):
    v_inputs_v2.diluted_shares is NA with reason SHARES_SCALE_UNCONFIRMED when its ratio to the dei cover share count of the
    SAME filing is outside SHARES_SCALE_BAND (0.1..10); the per-share histories are NA when their FY0-basis count is. Never
    multiplied/divided by 1,000 or 1,000,000, never replaced by the cover, basic or balance-sheet count. Normal counts, counts
    without a same-filing cover (no reference) and every Q·G metric are unchanged."""
    assert vf.CALC_VERSION == 'qgv2-calc/2026-10-17.1'
    assert vf.SHARES_SCALE_BAND == (0.1, 10.0) and vf.SHARES_SCALE_UNCONFIRMED == 'SHARES_SCALE_UNCONFIRMED'
    base_v, base_m = compute(simple_company())[4], compute(simple_company())[3]
    assert len(base_v['ebit_per_share_history']) == 5

    def run(extra):
        diag = {}
        _, fy0, _, m, v = vf.compute(simple_company(extra=extra), sic='3674', cutoff=CUTOFF, diagnostics=diag)
        assert fy0 == '2025-12-31'
        return m, v, diag

    # (a) Normal: FY0 10-K count 10 vs its cover 10.3; a 10-Q count 10.2 vs its cover 10.25 -> kept, histories unchanged.
    m, v, diag = run([_cover(10.3)])
    assert v['diluted_shares'] == base_v['diluted_shares'] and v == base_v and m == base_m
    assert diag['diluted_shares']['status'] == 'IN_BAND' and diag['per_share_histories']['status'] == 'IN_BAND'
    m, v, diag = run([_cover(10.3), _q2(DILUTED, 10.2), _cover(10.25, Q_ACCN, '2026-07-25', '10-Q', '2026-08-01')])
    assert v['diluted_shares'] == {'value': 10.2, 'period_end': '2026-06-30'} and m == base_m
    assert v['ebit_per_share_history'] == base_v['ebit_per_share_history'] and diag['diluted_shares']['accn'] == Q_ACCN
    # Band edges are inclusive (ratio exactly 10 and 0.1 kept); just outside -> NA.
    for value, kept in ((100.0, True), (1.0, True), (100.5, False), (0.99, False)):
        _, v, diag = run([_q2(DILUTED, value), _cover(10.0, Q_ACCN, '2026-07-25', '10-Q', '2026-08-01')])
        assert (v['diluted_shares'] == {'value': value, 'period_end': '2026-06-30'}) is kept, value
        assert diag['diluted_shares']['status'] == ('IN_BAND' if kept else 'SHARES_SCALE_UNCONFIRMED'), value

    # (b) MCD-like: every filing tags the counts in millions (10.0 for 10,000,000; the 10-Q 9.9 for 9,900,000). The cover of
    #     the same filing says 10,000,000 / 9,950,000 -> diluted_shares NA, per-share histories NA (their FY0 basis is the
    #     same mis-scaled count); Q·G metrics unchanged (they only use ratios of counts of one basis).
    mcd = [_cover(10_000_000.0), _q2(DILUTED, 9.9), _cover(9_950_000.0, Q_ACCN, '2026-06-30', '10-Q', '2026-08-01')]
    m, v, diag = run(mcd)
    assert v['diluted_shares'] is None and v['ebit_per_share_history'] == [] and v['fcf_per_share_history'] == []
    assert m == compute(simple_company(extra=[_q2(DILUTED, 9.9)]))[3] == base_m
    d = diag['diluted_shares']
    assert d['status'] == 'SHARES_SCALE_UNCONFIRMED' and d['value'] == 9.9 and d['reference'] == 9_950_000.0
    assert d['accn'] == Q_ACCN and d['concept'] == DILUTED and d['period_end'] == '2026-06-30'
    assert d['reference_concept'] == 'dei:EntityCommonStockSharesOutstanding' and math.isclose(d['ratio'], 9.9 / 9_950_000.0)
    assert diag['per_share_histories']['status'] == 'SHARES_SCALE_UNCONFIRMED' and diag['per_share_histories']['value'] == 10.0
    # Without a newer 10-Q: the FY0 10-K count itself is checked against the 10-K cover.
    _, v, diag = run([_cover(10_000_000.0)])
    assert v['diluted_shares'] is None and v['ebit_per_share_history'] == [] and diag['diluted_shares']['accn'] == K_ACCN

    # (c) WAT-like: the 10-Ks are correct (10 vs cover 10.1); one 2026 10-Q tags the count 1,000x (10,200 vs its cover 10.25).
    #     The basic count of the same table is wrong the same way and the balance-sheet count is right: neither is used.
    wat = [_cover(10.1), _q2(DILUTED, 10_200.0), _q2(DILUTED, 10_150.0, start='2026-01-01'),
           _q2('WeightedAverageNumberOfSharesOutstandingBasic', 10_150.0),
           (('CommonStockSharesOutstanding', 'shares', 10.2, '2026-06-30'), {'form': '10-Q', 'filed': '2026-08-01', 'accn': Q_ACCN}),
           _cover(10.25, Q_ACCN, '2026-08-07', '10-Q', '2026-08-01')]
    m, v, diag = run(wat)
    assert v['diluted_shares'] is None and diag['diluted_shares']['status'] == 'SHARES_SCALE_UNCONFIRMED'
    assert math.isclose(diag['diluted_shares']['ratio'], 10_200.0 / 10.25)
    # Histories keep the correctly scaled FY0 10-K basis (IN_BAND against the 10-Q cover); Q·G unchanged.
    assert v['ebit_per_share_history'] == base_v['ebit_per_share_history'] and v['fcf_per_share_history'] == base_v['fcf_per_share_history']
    assert diag['per_share_histories']['status'] == 'IN_BAND' and m == base_m
    assert {k: x for k, x in v.items() if k != 'diluted_shares'} == {k: x for k, x in base_v.items() if k != 'diluted_shares'}

    # (d) BKNG-like: 25-for-1 split after FY0 with no split-ratio fact. The 10-Q count (250) matches its cover (251): kept; the
    #     FY0-basis histories (10 shares) are 1/25 of it -> NA, so the device never compares pre-split per-share history
    #     with the post-split count.
    m, v, diag = run([_cover(10.0), _q2(DILUTED, 250.0), _cover(251.0, Q_ACCN, '2026-07-27', '10-Q', '2026-08-01')])
    assert v['diluted_shares'] == {'value': 250.0, 'period_end': '2026-06-30'} and m == base_m
    assert v['ebit_per_share_history'] == [] and v['fcf_per_share_history'] == []
    assert diag['per_share_histories']['status'] == 'SHARES_SCALE_UNCONFIRMED' and math.isclose(diag['per_share_histories']['ratio'], 10.0 / 251.0)

    # (e) No reference -> never blocked for it: no same-filing cover (class-dimensioned covers are not in companyfacts; a cover
    #     of ANOTHER filing is not a reference), or several distinct values in the filing (ambiguous).
    for extra in ([_q2(DILUTED, 10_200.0)], [_q2(DILUTED, 10_200.0), _cover(10.25)],
                  [_q2(DILUTED, 10_200.0), _cover(6.0, Q_ACCN, '2026-07-25', '10-Q', '2026-08-01'),
                   _cover(4.0, Q_ACCN, '2026-07-25', '10-Q', '2026-08-01')]):
        _, v, diag = run(extra)
        assert v['diluted_shares'] == {'value': 10_200.0, 'period_end': '2026-06-30'} and diag['diluted_shares']['status'] == 'NO_REFERENCE'
    # A stale count (V-STALE-SHARES) is not checked; a cover filed after the cutoff is not a reference.
    _, v, diag = run([_q2(DILUTED, 9.9), ((COVER, 'shares', 9_950_000.0, '2026-06-30'), {'form': '10-Q', 'filed': '2026-10-20', 'accn': Q_ACCN, 'taxonomy': 'dei'})])
    assert v['diluted_shares'] == {'value': 9.9, 'period_end': '2026-06-30'} and diag['diluted_shares']['status'] == 'NO_REFERENCE'

    # (f) Through the published SEC row (strict validators, unchanged row shape): MCD-like -> null count, LIVE row, Q·G as before.
    facts_b, subs = REF.synthetic_sec('0000001000')
    payload = json.loads(facts_b)
    latest = vf._Facts(payload, 'us-gaap', 'USD', CUTOFF).latest_duration_any_concept('diluted_shares')
    payload['facts']['dei'] = {COVER: {'units': {'shares': [{'end': latest[1].isoformat(), 'val': latest[0] * 1_000_000, 'accn': latest[2][0],
                                                             'form': '10-Q', 'filed': latest[2][1].isoformat(), 'fy': 2026, 'fp': 'Q2'}]}}}
    row, control = q_build(json.dumps(payload).encode(), subs), q_build(facts_b, subs)
    assert row['calc_version'] == vf.CALC_VERSION and row['state'] == 'LIVE' and row['reason_codes'] == []
    assert row['v_inputs_v2']['diluted_shares'] is None and control['v_inputs_v2']['diluted_shares'] is not None
    assert row['v_inputs_v2']['ebit_per_share_history'] == [] and row['metrics'] == control['metrics']
    updates = REF.synthetic_universe_updates()
    updates[REF._codes()[0]] = row
    published = q.merge(None, updates, as_of=NOW, shard_index=0)
    assert published['records'][REF._codes()[0]]['v_inputs_v2']['diluted_shares'] is None
    if shutil.which('node') is None:
        return
    # (g) Device (qgv2-inputs.js -> qgv-v2.js, unchanged): the blocked count is not replaced by any other share value (a
    #     cover/basic count injected next to it is ignored): every per-share and EV-based V is NA with SHARES_NOT_AVAILABLE.
    closes = {f'{y}-12': 100.0 for y in range(2015, 2026)}
    for v in (row['v_inputs_v2'], dict(row['v_inputs_v2'], shares_outstanding={'value': latest[0], 'period_end': '2026-06-30'}),
              run(wat)[1]):
        d = _device_v(v, closes)
        assert d['diluted_shares'] is None and d['ebit_yield'] is None and d['fcf_yield'] is None and d['implied_growth'] is None
        assert d['reasons'] == {k: 'SHARES_NOT_AVAILABLE' for k in ('v_earnings_yield', 'v_fcf_yield', 'v_vs_industry',
                                                                    'v_vs_own_history', 'v_expectation_check')}
        assert set(d['v_scores'].values()) == {None} and d['v_axis'] is None
        assert d['reference_range'] == {'state': 'NOT_AVAILABLE', 'reason': 'FCF_NOT_AVAILABLE', 'low': None, 'high': None}
    # Normal count: device V computed as before. BKNG-like: yields computed, own-history NA (no history), never mixed bases.
    d = _device_v(run([_cover(10.3)])[1], closes)
    assert d['diluted_shares'] == 10.0 and d['fcf_yield'] is not None and d['reasons']['v_vs_own_history'] != 'SHARES_NOT_AVAILABLE'
    d = _device_v(run([_cover(10.0), _q2(DILUTED, 250.0), _cover(251.0, Q_ACCN, '2026-07-27', '10-Q', '2026-08-01')])[1], closes)
    assert d['diluted_shares'] == 250.0 and d['fcf_yield'] is not None and d['reasons']['v_vs_own_history'] == 'HISTORY_TOO_SHORT'


def test_split_adjustment_never_adjusts_already_restated_values_twice():
    """Owner supplement 2026-10-15 (Q-SPLIT): a split-ratio fact alone never rescales values that the filings already report
    on the post-split basis."""
    close = lambda a, b: a is not None and math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-9)
    # Split effective before every filing that supplies FY0..FY-5 values: all of them are already post-split. The ratio fact
    # (10) is reported, but every link ratio is 1, so nothing is multiplied by 10.
    _, _, _, m, v = compute(_split_company(split_filed='2022-02-15'))
    assert close(m['dilution_3y'], 0.0) and close(m['eps_cagr_3y'], 0.1) and close(m['fcf_per_share_cagr_3y'], 0.1)
    for h in v['ebit_per_share_history']:
        assert close(h['value'], 0.2 * 146.41 / 1.1 ** (2025 - int(h['fiscal_year_end'][:4])) / 100)
    # Issuer restated its whole history (every filing reports the same counts, factor 1) while a split-ratio fact is filed
    # between the FY-3 filing and the basis: the shared periods prove one basis, so no second adjustment.
    _, _, _, m, v = compute(_split_company(factor=1.0, ratio_fact=10.0))
    assert close(m['dilution_3y'], 0.0) and close(m['eps_cagr_3y'], 0.1)
    assert [round(h['value'], 6) for h in v['ebit_per_share_history']] == [
        round(0.2 * 146.41 / 1.1 ** (2025 - y) / 100, 6) for y in range(2021, 2026)]
    # The adjusted case for contrast: pre-split FY-3 is multiplied exactly once (10x, not 100x).
    _, _, _, m, _ = compute(_split_company())
    assert close(m['dilution_3y'], 0.0)


def test_calc_version_rows_of_another_version_never_share_a_percentile():
    """Owner supplement 2026-10-15: calc_version on every row and file; a mismatched (or legacy) row is not ranked with the
    current rows (CALC_VERSION_MISMATCH) and an unversioned legacy file stays readable as one population."""
    assert re.fullmatch(vf.CALC_VERSION_PATTERN, vf.CALC_VERSION)
    facts, subs = REF.synthetic_sec('0000001000')
    row = q_build(facts, subs)
    assert row['calc_version'] == vf.CALC_VERSION and q.empty_record()['calc_version'] is None
    # Scoring: 10 current rows + 10 rows of an older version. The older ones are outside the cross-section and NA.
    rows = {f'X:{n}': {**_row(n, revenue_cagr_3y=float(n), revenue_growth_volatility=1.0, revenue_positive_growth_share=1.0,
                              revenue_acceleration=0.0, eps_cagr_3y=float(n)),
                       'calc_version': vf.CALC_VERSION if n <= 10 else 'qgv2-calc/2026-10-14.1'} for n in range(1, 21)}
    scores, summary = vs.score_rows(rows, calc_version=vf.CALC_VERSION)
    assert summary['cross_section_size'] == 10
    old = scores[('universe', 'X:15')]
    assert old['axes']['G']['reason_codes'] == ['CALC_VERSION_MISMATCH'] and old['axes']['G']['score'] is None
    assert all(v is None for v in old['factors'].values())
    current_only = {k: r for k, r in rows.items() if r['calc_version'] == vf.CALC_VERSION}
    assert scores[('universe', 'X:3')] == vs.score_rows(current_only, calc_version=vf.CALC_VERSION)[0][('universe', 'X:3')]
    # Legacy (unversioned) scoring = one population, exactly the previous behavior.
    assert vs.score_rows(rows)[1]['cross_section_size'] == 20
    # Files: the published file declares the version; an unversioned legacy file (no calc_version anywhere) still validates.
    p = payload()
    assert p['calc_version'] == vf.CALC_VERSION and all('calc_version' in r for r in p['records'].values())
    legacy = json.loads(json.dumps(p))
    legacy.pop('calc_version')
    for r in [*legacy['records'].values(), *legacy['target'].values()]:
        r.pop('calc_version')
    q.require_qgv2(legacy)
    # Merging today's shard into a legacy previous copy: the kept legacy rows stay (data never erased) but are outside the
    # ranking population; today's current-version rows are ranked only among themselves.
    code = REF._codes()[0]
    merged = q.merge(legacy, {code: json.loads(json.dumps(p['records'][code]))}, as_of=NOW, shard_index=4)
    assert merged['calc_version'] == vf.CALC_VERSION and merged['cross_section_size'] == 1
    kept = merged['records'][REF._codes()[1]]
    legacy_metrics = {k: x for k, x in legacy['records'][REF._codes()[1]]['metrics'].items() if k != 'revenue_volatility_5y_rank_pct'}
    assert kept['calc_version'] is None and kept['state'] == 'LIVE' and kept['metrics'] == legacy_metrics
    assert kept['axes']['Q']['reason_codes'] == ['CALC_VERSION_MISMATCH'] and 'revenue_volatility_5y_rank_pct' not in kept['metrics']
    assert merged['records'][code]['axes']['Q']['reason_codes'] == ['PEERS_BELOW_MINIMUM']
    # A mixed file whose mismatched row still carries ranked scores is rejected (versions are never mixed).
    bad = json.loads(json.dumps(p))
    bad['records'][REF._codes()[1]]['calc_version'] = 'qgv2-calc/2026-10-14.1'
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        q.require_qgv2(bad)
    for value in ('qgv2-calc/latest', 7, ''):
        bad['calc_version'] = value
        with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
            q.require_qgv2(bad)


def test_normal_na_rows_keep_an_explicit_source_reason_and_are_never_calc_version_mismatch():
    """Owner decision 2026-10-15 evening: a row that is NA because its source data is missing carries its own reason, is outside
    every ranking population but stays in the 504-code denominator; only rows WITH values of another version are
    CALC_VERSION_MISMATCH."""
    codes = shares.universe_codes()
    p = payload()
    na = {code: r for code, r in p['records'].items() if r['state'] == 'NOT_AVAILABLE'}
    assert len(p['records']) == p['code_count'] == len(codes) == 504 and len(na) > 400
    assert {'NOT_COLLECTED', 'CIK_UNRESOLVED'} <= {x for r in na.values() for x in r['reason_codes']}
    for r in na.values():
        assert r['reason_codes'] and r['calc_version'] is None and r['metrics'] == {}
        assert all(r['axes'][ax]['reason_codes'] == ['ROW_NOT_AVAILABLE'] for ax in ('Q', 'G'))
    assert p['cross_section_size'] == len({r['cik'] for r in p['records'].values() if r['state'] != 'NOT_AVAILABLE'})
    # Other NA kinds from build_row: no annual financials, invalid bytes.
    no_fin = q.build_row(cik='0000001000', companyfacts_body=json.dumps({'cik': 1000, 'facts': {}}).encode(),
                         submissions_body=json.dumps({'cik': 1000, 'sic': '3674'}).encode(), acquired_at=NOW - timedelta(hours=1))
    bad = q.build_row(cik='0000001000', companyfacts_body=b'{', submissions_body=b'{}', acquired_at=NOW - timedelta(hours=1))
    assert no_fin['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and bad['reason_codes'] == ['INVALID_INPUT']
    assert no_fin['calc_version'] is None and bad['calc_version'] is None
    # Scored under a version: NA rows are ROW_NOT_AVAILABLE, never CALC_VERSION_MISMATCH, also when kept from a legacy copy.
    rows = {'X:1': {**_row(1, revenue_cagr_3y=0.1), 'calc_version': vf.CALC_VERSION},
            'X:2': {**_row(2, state='NOT_AVAILABLE'), 'profile': None, 'calc_version': None},
            'X:3': {'cik': None, 'state': 'NOT_AVAILABLE', 'profile': None, 'industry_group': None, 'metrics': {}}}
    scores, summary = vs.score_rows(rows, calc_version=vf.CALC_VERSION)
    assert summary['cross_section_size'] == 1
    for key in ('X:2', 'X:3'):
        assert all(scores[('universe', key)]['axes'][ax]['reason_codes'] == ['ROW_NOT_AVAILABLE'] for ax in ('Q', 'G'))
    legacy = json.loads(json.dumps(p))
    legacy.pop('calc_version')
    for r in [*legacy['records'].values(), *legacy['target'].values()]:
        r.pop('calc_version')
    merged = q.merge(legacy, {}, as_of=NOW, shard_index=4)
    reasons = [r['axes']['Q']['reason_codes'] for r in merged['records'].values() if r['state'] == 'NOT_AVAILABLE']
    assert reasons and all(x == ['ROW_NOT_AVAILABLE'] for x in reasons)
    assert all(r['axes']['Q']['reason_codes'] == ['CALC_VERSION_MISMATCH'] for r in merged['records'].values() if r['state'] != 'NOT_AVAILABLE')
    # A NA row can never claim a calc_version (it has no computed values).
    tampered = json.loads(json.dumps(p))
    tampered['records'][next(iter(na))]['calc_version'] = vf.CALC_VERSION
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        q.require_qgv2(tampered)


# ---------------- percentile publication ----------------
def test_percentile_formula_ties_and_direction():
    assert vs.percentile(0, 1, 9) == 0 and vs.percentile(8, 1, 9) == 100 and vs.percentile(4, 1, 9) == 50
    assert vs.percentile(0, 9, 9) == 50  # all tied -> average rank
    rows = {f'X:{n}': {'cik': str(n).zfill(10), 'state': 'LIVE', 'profile': 'GENERAL', 'industry_group': 'g',
                       'metrics': {'revenue_cagr_3y': float(n % 5), 'revenue_growth_volatility': float(n)}} for n in range(1, 11)}
    scores, summary = vs.score_rows(rows)
    assert summary == {'cross_section_size': 10, 'cross_section_by_profile': {'GENERAL': 10, 'FINANCIAL': 0}}
    top, low = scores[('universe', 'X:4')], scores[('universe', 'X:5')]
    assert top['factors']['g_revenue_growth'] == 100 * (8 + 0.5) / 9  # value 4 (twice) above 8 others
    assert low['factors']['g_revenue_growth'] == 100 * 0.5 / 9  # value 0 (twice) is the lowest
    assert scores[('universe', 'X:1')]['factors']['g_consistency'] == 100  # lowest volatility is best
    axis = top['axes']['G']
    # only 2 of 5 G factors (weights 25 + 15 = 40 < 50) -> axis NA with the fixed reason; factors_available still published
    assert axis['score'] is None and axis['reason_codes'] == ['AXIS_COVERAGE_BELOW_50'] and axis['factors_available'] == '2/5'
    assert axis['available_weight'] == 40 and axis['peer_basis'] == 'UNIVERSE' and axis['peer_count'] == 10


def _row(n, profile='GENERAL', group='g', state='LIVE', **metrics):
    return {'cik': str(n).zfill(10), 'state': state, 'profile': profile, 'industry_group': group, 'metrics': metrics}


def test_peer_groups_fallback_financial_isolation_and_target_replacement():
    universe = {f'A:{n}': _row(n, group='big', roic=n / 100, revenue_cagr_3y=n / 50) for n in range(1, 9)}
    universe.update({f'B:{n}': _row(n, group='small', roic=n / 10) for n in range(20, 23)})
    universe.update({f'F:{n}': _row(n, profile='FINANCIAL', group='finance_real_estate', roe=n / 100) for n in range(40, 47)})
    universe['N:1'] = _row(99, state='NOT_AVAILABLE', roic=9.0)  # not in the cross-section
    target = {'t': _row(5, group='big', roic=0.5, revenue_cagr_3y=0.5)}  # same CIK as A:5, fresher values
    scores, summary = vs.score_rows(universe, target)
    assert summary['cross_section_size'] == 18 and summary['cross_section_by_profile'] == {'GENERAL': 11, 'FINANCIAL': 7}
    a1 = scores[('universe', 'A:1')]['axes']['Q']
    assert a1['peer_basis'] == 'INDUSTRY_GROUP' and a1['peer_count'] == 8
    b = scores[('universe', 'B:20')]['axes']['Q']
    assert b['peer_basis'] == 'UNIVERSE_FALLBACK' and b['peer_count'] == 11  # group of 3 < 8
    fin = scores[('universe', 'F:40')]['axes']
    assert fin['Q']['reason_codes'] == ['PEERS_BELOW_MINIMUM'] and fin['Q']['peer_count'] == 7 and fin['Q']['peer_basis'] == 'FINANCIAL_PROFILE'
    t = scores[('target', 't')]
    # TARGET replaces its own issuer point: still 8 peers in the group, and 0.5 is the top ROIC there.
    assert t['axes']['Q']['peer_count'] == 8 and t['factors']['q_profitability'] == 100
    assert scores[('universe', 'A:8')]['factors']['q_profitability'] == 100  # the universe row itself is unchanged by TARGET
    assert scores[('universe', 'N:1')]['axes']['Q']['reason_codes'] == ['ROW_NOT_AVAILABLE']


def test_group_submetric_with_too_few_values_is_ranked_in_the_universe():
    # Group of 8 issuers, only 3 report gross_profit_to_assets: that sub-metric uses the GENERAL universe (10 values).
    universe = {f'A:{n}': _row(n, group='big', roic=n / 100, **({'gross_profit_to_assets': n / 10} if n <= 3 else {})) for n in range(1, 9)}
    universe.update({f'B:{n}': _row(n, group='other', gross_profit_to_assets=n / 10) for n in range(20, 27)})
    scores, _ = vs.score_rows(universe)
    a3 = scores[('universe', 'A:3')]
    assert a3['axes']['Q']['peer_basis'] == 'INDUSTRY_GROUP' and a3['axes']['Q']['submetric_fallbacks'] == 1
    gp = vs.percentile(2, 1, 10)  # 0.3 among {0.1..0.3} + {2.0..2.6}
    assert a3['factors']['q_profitability'] == (vs.percentile(2, 1, 8) + gp) / 2
    assert scores[('universe', 'A:5')]['axes']['Q']['submetric_fallbacks'] == 0  # no own value -> nothing to rank


def test_weights_are_the_candidate_defaults_and_v1_is_unchanged():
    assert vs.Q_WEIGHTS_V2 == {'q_profitability': 25, 'q_moat_proxy': 20, 'q_earnings_quality': 20, 'q_financial_safety': 20, 'q_capital_allocation': 15}
    assert vs.G_WEIGHTS_V2 == {'g_revenue_growth': 25, 'g_per_share_growth': 25, 'g_growth_efficiency': 20, 'g_consistency': 15, 'g_recent_acceleration': 15}
    from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS
    assert Q_WEIGHTS['competitive_advantage'] == 0.20 and G_WEIGHTS['next_3_5y_growth'] == 0.25 and len(Q_WEIGHTS) == 7
    assert set(vs.FACTOR_IDS).isdisjoint(Q_WEIGHTS) and set(vs.FACTOR_IDS).isdisjoint(G_WEIGHTS)
    for profile in vs.SUBMETRICS.values():
        assert set(profile) == set(vs.FACTOR_IDS)
        for specs in profile.values():
            assert all(metric in vf.METRIC_KEYS and direction in (1, -1) for metric, direction in specs)


# ---------------- public file ----------------
def payload():
    return REF.base()


def test_publication_scores_universe_and_target_with_coverage_and_no_price():
    p = payload()
    assert p['cross_section_size'] == 27 and p['cross_section_by_profile'] == {'GENERAL': 18, 'FINANCIAL': 9}
    rows = [p['records'][c] for c in REF._codes()]
    assert all(r['state'] == 'LIVE' and r['axes']['Q']['score'] is not None and r['axes']['G']['score'] is not None for r in rows)
    semis = p['records'][REF._codes()[0]]
    assert semis['industry_group'] == 'manufacturing_industrial_tech' and semis['axes']['Q']['peer_basis'] == 'INDUSTRY_GROUP'
    software = p['records'][REF._codes()[11]]
    assert software['axes']['Q']['peer_basis'] == 'UNIVERSE_FALLBACK' and software['axes']['G']['peer_basis'] == 'UNIVERSE'
    fin = p['records'][REF._codes()[20]]
    assert fin['profile'] == 'FINANCIAL' and fin['axes']['Q']['factors_available'] == '4/5' and fin['factors']['q_earnings_quality'] is None
    assert p['target']['hanmi']['reason_codes'] == ['NON_SEC_ISSUER'] and p['target']['tokyo_electron']['state'] == 'NOT_AVAILABLE'
    assert p['target']['nvda']['state'] == 'LIVE' and p['target']['nvda']['axes']['Q']['peer_count'] == 14
    assert p['target']['asml']['reason_codes'] == ['NOT_COLLECTED']
    empty = p['records']['NYSE:MMM'] if 'NYSE:MMM' not in REF._codes() else p['records'][shares.universe_codes()[100]]
    assert empty['metrics'] == {} and all(v is None for v in empty['factors'].values())
    text = q.encode(p).decode().lower()
    assert '987654321' not in text and 'stockprice' not in text and '"price"' not in text and 'market_cap' not in text and '"rank' not in text
    v = p['target']['nvda']['v_inputs_v2']
    assert set(v) == set(vf.V_KEYS) and v['ebit']['ttm_end'] == '2026-06-30' and v['fcf']['fy_end'] == '2025-12-31'
    assert len(v['ebit_per_share_history']) == 5 and v['diluted_shares']['value'] > 0


def test_merge_carries_rows_never_erases_and_ages_them():
    p = payload()
    code = REF._codes()[0]
    later = NOW + timedelta(days=3)
    nodata = q.build_row(cik=p['records'][code]['cik'], companyfacts_body=b'{"cik":1000,"facts":{}}',
                         submissions_body=b'{"cik":1000,"sic":"3674"}', acquired_at=later)
    assert nodata['reason_codes'] == ['NO_ANNUAL_SEC_FINANCIALS'] and nodata['sic'] == '3674'
    # Owner rule 2026-10-17: a successful collection without data is published with its reason and own acquired_at
    # (it leaves the cross-section); only a row without its own collection record keeps the kept data.
    replaced = q.merge(p, {code: nodata}, as_of=later, shard_index=4)
    row = replaced['records'][code]
    assert (row['state'], row['reason_codes'], row['metrics'], row['calc_version']) == ('NOT_AVAILABLE', ['NO_ANNUAL_SEC_FINANCIALS'], {}, None)
    assert row['acquired_at'] == nodata['acquired_at'] and replaced['cross_section_size'] == p['cross_section_size'] - 1
    failed = q.empty_record(cik=p['records'][code]['cik'], reasons=('INVALID_INPUT',))
    kept = q.merge(p, {code: failed}, as_of=later, shard_index=4)
    assert kept['records'][code]['metrics'] == p['records'][code]['metrics'] and kept['records'][code]['acquired_at'] == p['records'][code]['acquired_at']
    stale = q.merge(kept, {}, as_of=NOW + timedelta(days=15), shard_index=5)
    row = stale['records'][code]
    assert row['state'] == 'STALE' and row['reason_codes'] == ['STALE_INPUT'] and row['axes']['Q']['score'] is not None
    assert stale['cross_section_size'] == 27  # STALE rows stay in the cross-section
    assert stale['target']['nvda']['state'] == 'STALE'  # TARGET rows age by the same window when not refreshed
    bad = json.loads(json.dumps(p['records'][code]))
    bad['metrics']['roic'] = float('inf')
    downgraded = q.merge(None, {code: bad}, as_of=NOW, shard_index=0)
    assert downgraded['records'][code]['reason_codes'] == ['INVALID_INPUT'] and downgraded['records'][code]['state'] == 'NOT_AVAILABLE'
    unresolved = q.merge(None, {}, as_of=NOW, shard_index=0, unresolved={'BATS:CBOE'})
    assert unresolved['records']['BATS:CBOE']['reason_codes'] == ['CIK_UNRESOLVED'] and unresolved['state'] == 'NOT_AVAILABLE'


def test_issuer_codes_share_one_row_and_one_cross_section_point():
    facts, subs = REF.synthetic_sec('0001652044', seed=3)
    rows = q.build_issuer_records(codes=('NASDAQ:GOOGL', 'NASDAQ:GOOG'), cik='0001652044', companyfacts_body=facts,
                                  submissions_body=subs, acquired_at=NOW)
    p = q.merge(payload(), rows, as_of=NOW, shard_index=1)
    live = [r for r in p['records'].values() if r['state'] != 'NOT_AVAILABLE']
    assert p['records']['NASDAQ:GOOGL'] == p['records']['NASDAQ:GOOG']
    assert sum(1 for r in live if r['cik'] == '0001652044') == 2 and p['cross_section_size'] == len({r['cik'] for r in live}) == len(live) - 1


def test_build_row_rejects_cik_mismatch_and_untrusted_bytes():
    facts, subs = REF.synthetic_sec('0000001000')
    assert q.build_row(cik='0000001001', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)['reason_codes'] == ['INVALID_INPUT']
    for bad in (b'{"cik":1000,"a":NaN}', b'{"cik":1000,"cik":2}', b'\xff', b'[]'):
        r = q.build_row(cik='0000001000', companyfacts_body=bad, submissions_body=subs, acquired_at=NOW)
        assert r['state'] == 'NOT_AVAILABLE' and r['reason_codes'] == ['INVALID_INPUT']
    assert q.build_row(cik='1', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW)['cik'] is None
    assert q.build_row(cik='0000001000', companyfacts_body=facts, submissions_body=subs, acquired_at=NOW.replace(tzinfo=None))['acquired_at'] is None


def test_size_at_504_issuers_stays_below_the_public_file_limit():
    from investment_system.universe.sec_universe_shares import universe_codes
    updates = {}
    for n, code in enumerate(universe_codes()):
        cik = str(5000 + n).zfill(10)
        facts, subs = REF.synthetic_sec(cik, sic=['3674', '7372', '2834', '6021', '4911', '5411'][n % 6], seed=n,
                                        growth=0.01 * (n % 13), financial=n % 6 == 3, revenue0=391035000000.0 + n * 7919)
        updates.update(q.build_issuer_records(codes=(code,), cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=NOW))
    full = q.merge(None, updates, as_of=NOW, shard_index=1, target_updates=REF.synthetic_target_updates())
    body = q.encode(full)
    assert full['cross_section_size'] == 504 and len(body) < 1.8 * 1024 * 1024 < q.MAX_BYTES
    assert len(q.encode(q.merge(None, {}, as_of=NOW, shard_index=None))) < 700 * 1024


# ---------------- validators (Python; JS parity through the shared vectors) ----------------
def test_vectors_fixture_is_regenerated_from_the_python_validator():
    fixture = json.loads((ROOT / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_text())
    assert fixture == json.loads(json.dumps(REF.build()))
    assert fixture['synthetic'] is True and len(fixture['cases']) >= 40
    assert [c['id'] for c in fixture['cases'] if c['valid']] == ['base_valid', 'null_shard_and_registry_valid', 'ebit_estimated_years_valid',
                                                                            'calc_version_legacy_file_valid', 'calc_version_mixed_population_valid',
                                                                            'target_withdrawn_valid', 'target_withdrawn_without_observation_valid',
                                                                            'universe_withdrawn_valid', 'schema_v1_valid',
                                                                            'target_withdrawn_in_schema_v1_file_valid']


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_js_validator_reaches_the_python_verdict_and_recomputes_scores():
    result = subprocess.run(['node', str(ROOT / 'tools/sec_qgv2_node_test.js')], text=True, capture_output=True, timeout=180)
    assert result.returncode == 0 and 'fail=0' in result.stdout


@pytest.mark.parametrize('path,value', [
    (('price',), 1), (('records', 'NYSE:MMM', 'factors', 'q_profitability'), 50.0), (('target', 'nvda', 'axes', 'Q', 'score'), 1.0),
    (('method', 'weights', 'G', 'g_consistency'), 16), (('cross_section_size',), 1), (('standard_status',), 'CALIBRATED'),
])
def test_validator_is_strict(path, value):
    p = payload()
    target = p
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        q.require_qgv2(p)


def test_json_parser_rejects_nonfinite_duplicates_and_oversize():
    for body in (b'{"a":NaN}', b'{"a":1,"a":2}', b'\xff', b'x' * (q.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
            q.parse_json(body)
    assert q.require_qgv2(q.parse_json(q.encode(payload())))['state'] == 'LIVE'


def test_pages_guard_allows_valid_file_and_rejects_tampered_or_priced_values(tmp_path):
    build = load_tool('build_pages_cockpit')
    guard = load_tool('pages_artifact_guard')
    site = tmp_path / 'site'
    build.build_public_cockpit(site)
    assert not (site / q.FILENAME).exists() and (site / 'sec-qgv2.js').exists()  # offline builds do not publish the data file
    (site / q.FILENAME).write_bytes(q.encode(payload()))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    tampered = payload()
    tampered['target']['nvda']['factors']['g_revenue_growth'] = 0
    (site / q.FILENAME).write_text(json.dumps(tampered))
    receipt = guard.scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('qgv2_boundary') == 1
    priced = payload()
    priced['target']['nvda']['v_inputs_v2']['price'] = 1
    (site / q.FILENAME).write_text(json.dumps(priced))
    violations = guard.scan_artifact(site)['violations']
    assert violations.get('sensitive_json_fields') == 1 and violations.get('qgv2_boundary') == 1


# ---------------- daily wiring: shard tool + TARGET stage (mocked transports only) ----------------
from tests.test_sec_universe_qg import UA, client_kwargs, day_for, pages, ticker_body, transport_for  # noqa: E402


def staged_target(folder, when):
    rows = REF.synthetic_target_updates(acquired_at=when - timedelta(minutes=30))
    (folder / q.FILENAME).write_bytes(q.encode(q.merge(None, {}, as_of=when - timedelta(minutes=20), shard_index=None, target_updates=rows)))


def test_shard_tool_one_fetch_feeds_v2_and_carries_the_staged_target(tmp_path, capsys):
    from investment_system.providers.sec_universe_collection import daily_partition, universe_registry
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    staged_target(tmp_path, when)
    calls = []
    code = tool.run(tmp_path, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when,
                    client_kwargs=client_kwargs(transport_for(calls), when), open_previous=pages({}))
    out = capsys.readouterr().out
    shard = [i.cik for i in daily_partition(universe_registry(ticker_body()), shard_count=7, shard_index=when.date().toordinal() % 7)]
    assert code == 0 and len(calls) == len(set(calls)) == 1 + 3 * len(shard)  # no extra SEC request for v2
    p = q.require_qgv2(json.loads((tmp_path / q.FILENAME).read_text()))
    assert p['records']['NYSE:BRK.B']['state'] == 'LIVE' and p['records']['NYSE:BRK.B']['metrics']['revenue_cagr_3y'] is not None
    assert p['target']['nvda']['state'] == 'LIVE' and p['target']['amd']['acquired_at'] == '2026-' + p['target']['amd']['acquired_at'][5:]
    assert p['last_shard_index'] == when.date().toordinal() % 7 and p['registry_sha256'] == sha256(ticker_body()).hexdigest()
    lines = [l for l in out.splitlines() if l.startswith('SEC_QGV2')]
    assert 'SEC_QGV2 PREVIOUS_RESTORED staged_target=3' in lines and any(l.startswith(f'SEC_QGV2 shard={when.date().toordinal() % 7}/7 ') for l in lines)
    for secret in (UA, 'tester@', '0000000002', 'sec.gov', 'BRK', 'nvda', 'revenue'):
        assert secret not in out
    assert (tmp_path / qg.FILENAME).exists() and (tmp_path / shares.FILENAME).exists()


def test_shard_tool_v2_failures_never_change_the_other_files(tmp_path, monkeypatch, capsys):
    tool = load_tool('sec_universe_shares')
    when = day_for('0000000002')
    base_dir, broken = tmp_path / 'a', tmp_path / 'b'
    base_dir.mkdir()
    broken.mkdir()
    tool.run(base_dir, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when, client_kwargs=client_kwargs(transport_for([]), when), open_previous=pages({}))
    def boom(*_, **__):
        raise RuntimeError('synthetic')
    monkeypatch.setattr(tool.qgv2, 'build_issuer_records', boom)
    monkeypatch.setattr(tool.qgv2, 'merge', boom)
    assert tool.run(broken, live=True, environ={'SEC_USER_AGENT': UA}, now=lambda: when, client_kwargs=client_kwargs(transport_for([]), when),
                    open_previous=pages({})) == 0
    assert 'SEC_QGV2 OUTPUT_FAILED previous_kept' in capsys.readouterr().out
    for name in (shares.FILENAME, qg.FILENAME):
        assert (broken / name).read_bytes() == (base_dir / name).read_bytes()
    assert not (broken / q.FILENAME).exists()


def test_shard_tool_previous_handling(tmp_path, capsys):
    tool = load_tool('sec_universe_shares')
    previous = q.encode(payload())
    # preserve-only restores the previous copy (ages rows) and keeps its scores
    keep = tmp_path / 'keep'
    keep.mkdir()
    assert tool.run(keep, live=False, preserve_only=True, now=lambda: NOW + timedelta(hours=1), open_previous=pages({q.FILENAME: previous})) == 0
    assert 'SEC_QGV2 PREVIOUS_RESTORED' in capsys.readouterr().out
    restored = q.require_qgv2(json.loads((keep / q.FILENAME).read_text()))
    assert restored['records'][REF._codes()[0]]['axes'] == json.loads(previous)['records'][REF._codes()[0]]['axes']
    # an invalid previous copy is discarded; nothing to write in preserve-only
    other = tmp_path / 'other'
    other.mkdir()
    assert tool.run(other, live=False, preserve_only=True, open_previous=pages({q.FILENAME: b'{"price":1}'})) == 0
    out = capsys.readouterr().out
    assert 'SEC_QGV2 PREVIOUS_DISCARDED' in out and 'SEC_QGV2 PREVIOUS_NOT_AVAILABLE' in out and not (other / q.FILENAME).exists()
    # a network failure on the previous v2 copy writes nothing and exits 1 (same rule as the other two files)
    net = tmp_path / 'net'
    net.mkdir()
    assert tool.run(net, live=True, environ={'SEC_USER_AGENT': UA}, open_previous=pages({q.FILENAME: urllib.error.URLError('x')})) == 1
    assert 'SEC_QGV2 PREVIOUS_FETCH_FAILED' in capsys.readouterr().out and not list(net.iterdir())
    # an invalid staged TARGET file is discarded, never published as is
    bad = tmp_path / 'bad'
    bad.mkdir()
    (bad / q.FILENAME).write_text('{"price":1}')
    assert tool.run(bad, live=False, preserve_only=True, open_previous=pages({q.FILENAME: previous}), now=lambda: NOW) == 0
    assert 'SEC_QGV2 STAGED_TARGET_DISCARDED' in capsys.readouterr().out
    assert q.require_qgv2(json.loads((bad / q.FILENAME).read_text()))['target']['nvda']['state'] == 'LIVE'


def test_target_stage_writes_valid_file_from_pipeline_bytes(tmp_path, capsys):
    pipeline = load_tool('public_screens_pipeline')
    root = tmp_path / 'raw'
    root.mkdir()
    site = tmp_path / 'site'
    site.mkdir()
    manifest = {'sec': []}
    for n, company_id in enumerate(('nvda', 'msft')):
        facts, subs = REF.synthetic_sec(q.target_cik(company_id), seed=n)
        (root / f'{company_id}-f.json').write_bytes(facts)
        (root / f'{company_id}-s.json').write_bytes(subs)
        manifest['sec'].append({'company_id': company_id, 'companyfacts': f'{company_id}-f.json', 'submissions': f'{company_id}-s.json',
                                'acquired_at': NOW.isoformat(), 'synthetic': False})
    staged = pipeline.stage_qgv2_target(site, manifest, root, now=NOW + timedelta(minutes=5))
    assert 'SEC_QGV2_TARGET staged companies=2 with_data=2' in capsys.readouterr().out
    p = q.require_qgv2(json.loads((site / q.FILENAME).read_text()))
    assert p == staged and p['target']['nvda']['state'] == 'LIVE' and p['target']['nvda']['metrics']
    # no Universe peers yet: TARGET axes are NA with a fixed reason, never 0
    assert p['target']['nvda']['axes']['Q']['reason_codes'] == ['PEERS_BELOW_MINIMUM'] and p['target']['nvda']['axes']['Q']['score'] is None
    assert p['records']['NYSE:MMM']['reason_codes'] == ['NOT_COLLECTED'] and p['target']['hanmi']['reason_codes'] == ['NON_SEC_ISSUER']
    assert pipeline.stage_qgv2_target(tmp_path / 'missing', manifest, root) is None
    assert 'SEC_QGV2_TARGET STAGE_FAILED' in capsys.readouterr().out


def test_workflows_manifests_and_offline_fixture_are_wired():
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    target_step = daily.index('python implementation/tools/public_screens_pipeline.py --live')
    shard_step = daily.index('python implementation/tools/sec_universe_shares.py --live --out "$RUNNER_TEMP/public-cockpit"')
    assert target_step < shard_step < daily.index('actions/upload-pages-artifact')  # TARGET stage first, shard publish second
    pages_yml = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    assert 'python implementation/tools/sec_universe_shares.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"' in pages_yml
    assert 'sec_qgv2_node_test.js' in (ROOT / 'tools/ci_node_tests.txt').read_text().split()
    assert "'sec-qgv2.json'" in (ROOT / 'tools/empty_public_screens.js').read_text()
    assert '<script src="sec-qgv2.js"></script>' in (ROOT / 'src/investment_system/product/web_assets/index.html').read_text()
    guard = (ROOT / 'tools/pages_artifact_guard.py').read_text()
    assert guard.count('\nALLOWED_NAMES') == 1 and 'QGV2_FILENAME' in guard.split('\nALLOWED_NAMES', 1)[1].split('\n', 1)[0]


def test_normalized_earnings_inputs_are_reported_pricefree_and_legacy_readable():
    row = next(r for r in payload()['records'].values() if r['state'] != 'NOT_AVAILABLE')
    value = row['v_inputs_v2']
    assert value['revenue'] is not None
    assert len(value['operating_margin_history']) == 5
    assert all(h['value'] is not None for h in value['operating_margin_history'])
    prior = payload()
    for r in [*prior['records'].values(), *prior['target'].values()]:
        r['v_inputs_v2'].pop('revenue')
        r['v_inputs_v2'].pop('operating_margin_history')
    prior['decision_ref'] = 'GSQ-022_PENDING_APPROVAL'
    q.require_qgv2(prior)


def test_playbook_volatility_requires_all_six_revenues_and_leaves_g_consistency_unchanged():
    full = compute(simple_company(years=range(2020, 2026)))[3]
    assert full['revenue_growth_std_5y'] is not None
    assert full['revenue_growth_std_5y'] < 1e-12
    short = compute(simple_company(years=range(2022, 2026)))[3]
    assert short['revenue_growth_volatility'] is not None  # Existing >=3-growth G rule.
    assert short['revenue_growth_std_5y'] is None          # New descriptor never uses the short history.


def test_playbook_volatility_rank_deduplicates_issuers_and_replaces_target_point():
    rows = {str(n): _row(n + 1, revenue_growth_std_5y=float(n)) for n in range(8)}
    rows['duplicate'] = dict(rows['0'])
    target = {'newer': _row(1, revenue_growth_std_5y=100.0), 'missing': _row(10)}
    ranked = vs.volatility_rank_rows(rows, target)
    assert ranked[('universe', '0')] == ranked[('universe', 'duplicate')] == 0
    assert ranked[('universe', '7')] == 100
    assert ranked[('target', 'newer')] == 100
    assert ranked[('target', 'missing')] is None
    assert all(v is None for v in vs.volatility_rank_rows({k: rows[k] for k in list(rows)[:7]}).values())


def test_published_volatility_is_a_descriptor_not_a_new_qg_factor():
    p = payload()
    assert any('revenue_growth_std_5y' in r['metrics'] for r in p['records'].values())
    original = {c: (r['factors'], r['axes']) for c, r in p['records'].items()}
    for r in [*p['records'].values(), *p['target'].values()]:
        r['metrics'].pop('revenue_growth_std_5y', None)
        r['metrics'].pop('revenue_volatility_5y_rank_pct', None)
    q.require_qgv2(p)  # Optional legacy shape remains valid, and Q/G factor bytes did not change.
    assert original == {c: (r['factors'], r['axes']) for c, r in p['records'].items()}
