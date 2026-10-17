"""QGV v2 Q·G raw metrics from SEC companyfacts (price-free). PROVISIONAL, UNCALIBRATED.

Spec: docs/qgv_scoring_standard/QGV_V2_CANDIDATE.md (user decision 2026-10-13: v2 is the provisional
default, decision record GSQ-022 pending approval). Method detail: docs/qgv_scoring_standard/QGV_V2_QG_METHOD.md.

This module only extracts exact SEC amounts and computes per-company raw ratios. It never reads a
price, never ranks, never fills a missing value with 0: a metric whose inputs are missing, or whose
denominator is not meaningful (documented per metric), is None. Percentile scoring across the
Universe504 cross-section lives in ``qgv.v2_scoring``. v1 (factors.py / raw_map.py) is untouched.

Period rules (all from one companyfacts payload, facts filed on/before the acquisition date):
- annual flow = duration 350..380 days reported in an annual form (10-K, 20-F, 40-F and amendments);
- year k (k=0 latest) = the annual fact whose end is within 10 days of FY0-end minus k years;
- instant (balance sheet) = value at that end (10 days tolerance), any 10-K/10-Q/20-F/40-F form;
- the same period reported more than once: latest `filed` wins; same `filed` with different values
  -> that period is dropped (ambiguous), never averaged;
- TTM flow = FY0 + YTD(latest 10-Q of the current fiscal year) - YTD(same span one year earlier);
  when no 10-Q follows FY0, TTM = FY0 (period end = FY0 end).
"""
from __future__ import annotations

from datetime import date, timedelta
import math
import re

# Calculation-rule version of the Q·G raw metrics (owner supplement 2026-10-15). Bump it whenever a factor rule here changes
# (concept lists, fallback lines, period rules, metric definitions). Every sec-qgv2.json row with data carries the version it
# was computed with and the file declares the current one; rows of another version are never ranked in the same percentile
# population (v2_scoring.score_rows, sec-qgv2.js, qgv2-inputs.js -> CALC_VERSION_MISMATCH). Format: qgv2-calc/<date>.<n>.
# 2026-10-15.1 = rules SW, MAA, RSG, NODEBT, EBIT, SPLIT, APPQ on top of F1-F3 (QGV_V2_QG_METHOD.md section 1).
# 2026-10-17.1 = v_inputs_v2 only: total_debt / cash_and_equivalents dated before the FY0 balance sheet are NA (V-STALE-BS);
#                diluted_shares is the latest-ending fact over all allowed diluted-share concepts and NA when its period end is
#                before FY0 end minus YEAR_TOLERANCE_DAYS (V-STALE-SHARES, owner decision 2026-10-17, same version);
#                Q·G metrics, factors and axes are unchanged from 2026-10-15.1.
CALC_VERSION = 'qgv2-calc/2026-10-17.1'
CALC_VERSION_PATTERN = r'qgv2-calc/[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]{1,4}'
ANNUAL_FORMS = frozenset({'10-K', '10-K/A', '10-KT', '10-KT/A', '20-F', '20-F/A', '40-F', '40-F/A'})
QUARTER_FORMS = frozenset({'10-Q', '10-Q/A'})
INSTANT_FORMS = ANNUAL_FORMS | QUARTER_FORMS
YEAR_TOLERANCE_DAYS = 10
YTD_TOLERANCE_DAYS = 7
ANNUAL_DAYS = (350, 380)
YTD_DAYS = (80, 300)
HISTORY_YEARS = 5
# Used only when the reported effective rate is not derivable (pretax <= 0 or missing lines). UNCALIBRATED.
DEFAULT_TAX_RATE = 0.21
TAX_RATE_BOUNDS = (0.0, 0.5)
# SIC 6000-6499: depository/non-depository credit, brokers/dealers, insurance carriers and agents.
FINANCIAL_SIC_RANGE = (6000, 6499)
PROFILES = ('GENERAL', 'FINANCIAL')

# Concept priority lists. For each period the first concept with a usable fact wins. Pretax income, D&A and capex then
# have documented us-gaap fallback lines (component items at the end of the list; _Company.annual_hit).
CONCEPTS = {
    'us-gaap': {
        'revenue': ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                    'RevenueFromContractWithCustomerIncludingAssessedTax', 'SalesRevenueNet', 'SalesRevenueGoodsNet',
                    'RevenuesNetOfInterestExpense',
                    # Utilities' total operating revenues (regulated + unregulated). Same amount the issuer tagged as
                    # `Revenues` in years where both were reported; last in the list, so it never overrides them.
                    'RegulatedAndUnregulatedOperatingRevenue'),
        'gross_profit': ('GrossProfit',),
        'cost_of_revenue': ('CostOfRevenue', 'CostOfGoodsAndServicesSold', 'CostOfGoodsSold'),
        'ebit': ('OperatingIncomeLoss',),
        'pretax_income': ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                          'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments'),
        'income_tax': ('IncomeTaxExpenseBenefit',),
        'net_income': ('NetIncomeLoss', 'ProfitLoss'),
        'operating_cash_flow': ('NetCashProvidedByUsedInOperatingActivities',
                                'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'),
        'capital_expenditure': ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets'),
        'depreciation_amortization': ('DepreciationDepletionAndAmortization', 'DepreciationAmortizationAndAccretionNet',
                                      'DepreciationAndAmortization'),
        'interest_expense': ('InterestExpense', 'InterestExpenseNonoperating', 'InterestExpenseDebt', 'InterestAndDebtExpense'),
        'net_interest_income': ('InterestIncomeExpenseNet',),
        'eps_diluted': ('EarningsPerShareDiluted', 'EarningsPerShareBasicAndDiluted'),
        'diluted_shares': ('WeightedAverageNumberOfDilutedSharesOutstanding',
                           'WeightedAverageNumberOfShareOutstandingBasicAndDiluted'),
        # instants
        'total_assets': ('Assets',),
        'equity': ('StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'),
        'cash_and_equivalents': ('CashAndCashEquivalentsAtCarryingValue',
                                 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents', 'Cash'),
        'debt_total_long_term': ('LongTermDebt',),
        'debt_noncurrent': ('LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligations'),
        'debt_current_maturities': ('LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent'),
        'debt_short_term': ('ShortTermBorrowings', 'CommercialPaper'),
        'debt_current_total': ('DebtCurrent',),
        # Component lines, read only by _Company.annual_hit when the item above has no usable value for a fiscal year
        # (QGV_V2_QG_METHOD.md section 1, "Fallback lines"). Never a source of their own metric.
        'pretax_income_domestic': ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic',),
        'pretax_income_foreign': ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign',),
        'depreciation': ('Depreciation',),
        'amortization_of_intangibles': ('AmortizationOfIntangibleAssets',),
        # Total capex reported under a narrower element name (INCY: OtherProductiveAssets; RL FY2026: MachineryAndEquipment;
        # GLW/SNA/IT: CapitalImprovements; LLY/WEC/ADP: OtherPropertyPlantAndEquipment). Used only when exactly one of them is
        # reported for the year and no line of 'capital_expenditure_partial_lines' is: two or more lines mean each is a
        # partial capex line, so capex stays None.
        'capital_expenditure_fallback': ('PaymentsToAcquireOtherProductiveAssets', 'PaymentsToAcquireMachineryAndEquipment',
                                         'PaymentsForCapitalImprovements', 'PaymentsToAcquireOtherPropertyPlantAndEquipment'),
        'capital_expenditure_partial_lines': ('PaymentsToAcquireOilAndGasProperty', 'PaymentsToAcquireOilAndGasPropertyAndEquipment',
                                              'PaymentsToExploreAndDevelopOilAndGasProperties', 'PaymentsToAcquireRealEstate',
                                              'PaymentsToAcquireCommercialRealEstate', 'PaymentsToAcquireResidentialRealEstate',
                                              'PaymentsToAcquireOtherRealEstate', 'PaymentsToDevelopRealEstateAssets',
                                              'PaymentsForTenantImprovements', 'PaymentsForConstructionInProcess',
                                              'PaymentsToAcquireTimberlands', 'PaymentsToAcquireBuildings', 'PaymentsToAcquireLand',
                                              'PaymentsToAcquireFurnitureAndFixtures', 'PaymentsForProceedsFromProductiveAssets'),
        # Capitalized software (owner decision Q-SW 2026-10-15: included in capex). Added to a physical capex line of the same
        # span, never on its own and never to PaymentsToAcquireProductiveAssets (_Company._capex_with_software).
        'capital_expenditure_software_total': ('PaymentsForSoftware',),
        'capital_expenditure_software_parts': ('PaymentsToAcquireSoftware', 'PaymentsToDevelopSoftware'),
        # Debt-free rule (owner decision Q-NODEBT 2026-10-15; _Company.debt_rule). Instants: borrowing concepts outside the
        # debt lines above (DXCM-type convertible notes, notes payable, credit lines, ...). Any non-zero one at the
        # balance-sheet date means the issuer reports debt that the debt lines do not capture, so debt stays NA.
        'debt_evidence': ('ConvertibleDebt', 'ConvertibleDebtNoncurrent', 'ConvertibleDebtCurrent', 'ConvertibleNotesPayable',
                          'ConvertibleNotesPayableCurrent', 'ConvertibleLongTermNotesPayable', 'ConvertibleSubordinatedDebt',
                          'ConvertibleSubordinatedDebtNoncurrent', 'SeniorNotes', 'SeniorNotesCurrent', 'SeniorNotesNoncurrent',
                          'SeniorLongTermNotes', 'SeniorSubordinatedNotes', 'SubordinatedDebt', 'SubordinatedLongTermDebt',
                          'NotesPayable', 'NotesPayableCurrent', 'LongTermNotesPayable', 'LongTermNotesPayableCurrent',
                          'NotesAndLoansPayable', 'NotesAndLoansPayableCurrent', 'LoansPayable', 'LoansPayableCurrent',
                          'LongTermLoansPayable', 'ShortTermBankLoansAndNotesPayable', 'BankOverdrafts', 'LineOfCredit',
                          'LongTermLineOfCredit', 'LongTermLineOfCreditNoncurrent', 'LinesOfCreditCurrent', 'SecuredDebt',
                          'SecuredDebtCurrent', 'SecuredLongTermDebt', 'UnsecuredDebt', 'UnsecuredDebtCurrent',
                          'UnsecuredLongTermDebt', 'OtherLongTermDebt', 'OtherLongTermDebtNoncurrent', 'OtherLongTermDebtCurrent',
                          'OtherShortTermBorrowings', 'OtherBorrowings', 'DebtInstrumentCarryingAmount', 'DebtInstrumentFaceAmount',
                          'LongTermDebtFairValue', 'DebtLongtermAndShorttermCombinedAmount', 'DebtAndCapitalLeaseObligations',
                          'LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities'),
        # Finance-lease liabilities (operating leases stay outside debt, as before): total, else noncurrent + current.
        'finance_lease_total': ('FinanceLeaseLiability', 'CapitalLeaseObligations'),
        'finance_lease_noncurrent': ('FinanceLeaseLiabilityNoncurrent', 'CapitalLeaseObligationsNoncurrent'),
        'finance_lease_current': ('FinanceLeaseLiabilityCurrent', 'CapitalLeaseObligationsCurrent'),
        # Flows: every interest-expense concept (any non-zero one blocks the zero-debt rule) and the finance-lease interest.
        'interest_expense_evidence': ('InterestExpense', 'InterestExpenseNonoperating', 'InterestExpenseDebt',
                                      'InterestAndDebtExpense', 'InterestExpenseOther', 'InterestExpenseBorrowings',
                                      'InterestExpenseLongTermDebt', 'InterestExpenseShortTermBorrowings',
                                      'InterestExpenseDebtExcludingAmortization', 'InterestExpenseRelatedParty'),
        'finance_lease_interest': ('FinanceLeaseInterestExpense',),
    },
    'ifrs-full': {
        'revenue': ('Revenue', 'RevenueFromContractsWithCustomers'),
        'gross_profit': ('GrossProfit',),
        'cost_of_revenue': ('CostOfSales',),
        'ebit': ('ProfitLossFromOperatingActivities',),
        'pretax_income': ('ProfitLossBeforeTax',),
        'income_tax': ('IncomeTaxExpenseContinuingOperations',),
        'net_income': ('ProfitLossAttributableToOwnersOfParent', 'ProfitLoss'),
        'operating_cash_flow': ('CashFlowsFromUsedInOperatingActivities',),
        'capital_expenditure': ('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
                                'PurchaseOfPropertyPlantAndEquipment'),
        'depreciation_amortization': ('DepreciationAndAmortisationExpense', 'AdjustmentsForDepreciationAndAmortisationExpense'),
        'interest_expense': ('FinanceCosts', 'InterestExpense'),
        'net_interest_income': ('InterestIncomeExpenseNet', 'NetInterestIncomeExpense'),
        'eps_diluted': ('DilutedEarningsLossPerShare',),
        'diluted_shares': ('AdjustedWeightedAverageShares',),
        'total_assets': ('Assets',),
        'equity': ('EquityAttributableToOwnersOfParent', 'Equity'),
        'cash_and_equivalents': ('CashAndCashEquivalents',),
        'debt_total_long_term': ('Borrowings',),
        'debt_noncurrent': ('NoncurrentPortionOfNoncurrentBorrowings', 'NoncurrentBorrowings'),
        'debt_current_maturities': ('CurrentPortionOfNoncurrentBorrowings',),
        'debt_short_term': ('ShorttermBorrowings', 'CurrentBorrowings'),
        'debt_current_total': ('CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings',),
        # No ifrs-full component fallbacks (us-gaap only).
        'pretax_income_domestic': (), 'pretax_income_foreign': (), 'depreciation': (), 'amortization_of_intangibles': (),
        'capital_expenditure_fallback': (), 'capital_expenditure_partial_lines': (),
        'capital_expenditure_software_total': (), 'capital_expenditure_software_parts': (),
        'debt_evidence': (), 'finance_lease_total': (), 'finance_lease_noncurrent': (), 'finance_lease_current': (),
        'interest_expense_evidence': (), 'finance_lease_interest': (),
    },
}
# Issuer exceptions (owner decision Q-RSG 2026-10-15): explicit, CIK-keyed, us-gaap only, never a blanket rule (a blanket
# "income-statement revenue first" breaks REITs, whose `Revenues` is the right total). For a listed issuer the item reads ONLY
# the listed concepts, so years never mix the two bases; a year without them is NA.
ISSUER_CONCEPT_EXCEPTIONS = {
    # RSG (Republic Services): `Revenues` is the segment-note total before intercompany eliminations (FY2025 19,027 vs the
    # income statement's 16,591); the income statement is RevenueFromContractWithCustomerExcludingAssessedTax.
    '0001060391': {'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax',)},
}
COMPONENT_ITEMS = ('pretax_income_domestic', 'pretax_income_foreign', 'depreciation', 'amortization_of_intangibles',
                   'capital_expenditure_fallback', 'capital_expenditure_partial_lines',
                   'capital_expenditure_software_total', 'capital_expenditure_software_parts',
                   'interest_expense_evidence', 'finance_lease_interest')
# REITs (SIC 6798): PaymentsForCapitalImprovements is improvement spending on existing properties, a part of capex next to
# development and acquisitions (MAA tags development elsewhere). Owner decision Q-MAA 2026-10-15: for a REIT this line is never
# the F3 fallback and, like the partial lines, its presence leaves F3 capex NA.
REIT_SIC = '6798'
REIT_PARTIAL_CAPEX_FALLBACK = frozenset({'PaymentsForCapitalImprovements'})
# Capex totals whose us-gaap definition already includes software (and other intangibles): software is never added to them.
CAPEX_INCLUDES_SOFTWARE = frozenset({'PaymentsToAcquireProductiveAssets'})
# Double-count guard: when PaymentsToAcquireProductiveAssets is also reported for the span, software is added only if that
# total is at least physical capex + software (within this relative tolerance), i.e. the total confirms they are separate.
CAPEX_SOFTWARE_TOLERANCE = 0.005
FLOW_ITEMS = ('revenue', 'gross_profit', 'cost_of_revenue', 'ebit', 'pretax_income', 'income_tax', 'net_income',
              'operating_cash_flow', 'capital_expenditure', 'depreciation_amortization', 'interest_expense',
              'net_interest_income', 'eps_diluted', 'diluted_shares') + COMPONENT_ITEMS
# D&A total that "holds only depreciation": equal to `Depreciation` within this relative tolerance (FIX: 62.4 vs 62.379).
DA_DEPRECIATION_ONLY_TOLERANCE = 0.005
INSTANT_ITEMS = ('total_assets', 'equity', 'cash_and_equivalents', 'debt_total_long_term', 'debt_noncurrent',
                 'debt_current_maturities', 'debt_short_term', 'debt_current_total',
                 'debt_evidence', 'finance_lease_total', 'finance_lease_noncurrent', 'finance_lease_current')
DEBT_ITEMS = ('debt_total_long_term', 'debt_noncurrent', 'debt_current_maturities', 'debt_short_term', 'debt_current_total')
# Lease case of the debt-free rule: interest expense is explained by the finance lease when it is at most the lease interest.
LEASE_INTEREST_TOLERANCE = 0.005
# FY0 anchor: the latest annual end of any of these defines the fiscal year sequence.
ANCHOR_ITEMS = ('net_income', 'revenue', 'operating_cash_flow', 'ebit')

# Published raw metric keys (one fixed set for every row; a metric outside the row's profile is None).
METRIC_KEYS = (
    # GENERAL Q
    'roic', 'gross_profit_to_assets', 'accruals_to_assets', 'fcf_to_net_income', 'net_debt_to_ebitda',
    'interest_coverage', 'incremental_roic_5y',
    # FINANCIAL Q
    'roe', 'roa', 'net_interest_income_to_assets', 'equity_to_assets', 'incremental_roe_5y',
    # shared Q (moat basis: ROIC for GENERAL, ROE for FINANCIAL)
    'moat_return_mean_5y', 'moat_return_std_5y', 'moat_return_years', 'moat_proxy', 'dilution_3y',
    # G
    'revenue_cagr_3y', 'eps_cagr_3y', 'fcf_per_share_cagr_3y', 'book_value_per_share_cagr_3y',
    'incremental_roic_3y', 'incremental_roe_3y', 'revenue_positive_growth_share', 'revenue_growth_volatility',
    'revenue_ttm_growth', 'revenue_acceleration',
    'revenue_growth_std_5y', 'revenue_volatility_5y_rank_pct',
)
# Stock-split adjustment of per-share histories (rule SPLIT, owner decision Q-SPLIT 2026-10-15; _Company.share_factor).
# Split-ratio facts that confirm a share-count restatement (us-gaap, unit 'pure'; 2 = 2-for-1, a reverse split may be tagged
# as 0.2 or 5: the direction always comes from the restated share counts themselves).
SPLIT_RATIO_CONCEPTS = ('StockholdersEquityNoteStockSplitConversionRatio1', 'StockholdersEquityNoteStockSplitConversionRatio')
# Two filings reporting the same share-count period: values within this relative distance are one basis (ordinary revision).
SHARE_REVISION_TOLERANCE = 0.05
# Otherwise the restatement ratio must match a reported split ratio (or its reciprocal) within this relative tolerance.
SPLIT_MATCH_TOLERANCE = 0.03
# An adjusted share count more than this factor away from FY0's is an unexplained discontinuity (e.g. a unit error): NA.
SHARE_JUMP_LIMIT = 3.0
# Price-free descriptors published only in the SEC file `sec-qgv2.json` (never ranked, never in the DART reference block,
# whose key set is METRIC_KEYS exactly), with the profiles allowed to carry each (validators: universe/sec_qgv2.py, sec-qgv2.js).
# ebit_estimated_years: number of fiscal years FY0..FY-5 whose EBIT is the substitute pretax + interest (rule EBIT); present
# only when >= 1, so its absence means every EBIT used is the reported operating income (or EBIT is not available).
# roic_avg_3y, operating_margin_std_5y_pp (owner decision Q-APPQ 2026-10-15): the PLAYBOOK §6-2 / §17 #19 quality inputs
# (3-year average ROIC >= 15%, 5-year operating-margin population std < 3 percentage points), price-free.
# ebit_estimated_fiscal_years (owner decision Q-EBIT-SCOPE 2026-10-15): WHICH fiscal years those are, as the calendar year
# of each substituted fiscal-year end (ascending, unique; FY ending 2026-03-31 -> 2026). Same presence and length as the count.
EXTRA_METRIC_PROFILES = {'ebit_estimated_years': ('GENERAL',), 'ebit_estimated_fiscal_years': ('GENERAL',), 'roic_avg_3y': ('GENERAL',),
                         'operating_margin_std_5y_pp': ('GENERAL', 'FINANCIAL')}
QUALITY_ROIC_YEARS = 3
QUALITY_MARGIN_YEARS = 5
EXTRA_METRIC_KEYS = tuple(EXTRA_METRIC_PROFILES)
INTEGER_METRICS = frozenset({'moat_return_years', 'ebit_estimated_years'})
LIST_METRICS = frozenset({'ebit_estimated_fiscal_years'})
# Metrics that are counts/descriptors, not ranked directly.
DESCRIPTIVE_METRICS = frozenset({'moat_return_mean_5y', 'moat_return_std_5y', 'moat_return_years', 'revenue_ttm_growth',
                               'revenue_growth_std_5y', 'revenue_volatility_5y_rank_pct'})


def _finite(value):
    try:
        return type(value) in (int, float) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _round(value):
    """Published raw ratios carry 6 significant digits; scores are ranked from the published value."""
    if not _finite(value):
        return None
    out = float(f'{value:.6g}')
    return 0.0 if out == 0 else out


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _shift_years(day, years):
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # Feb 29
        return day.replace(year=day.year - years, day=28)


def profile_for_sic(sic):
    """FINANCIAL for SIC 6000-6499, GENERAL otherwise (also when SIC is missing; documented)."""
    if isinstance(sic, str) and re.fullmatch(r'[0-9]{4}', sic):
        code = int(sic)
        if FINANCIAL_SIC_RANGE[0] <= code <= FINANCIAL_SIC_RANGE[1]:
            return 'FINANCIAL'
    return 'GENERAL'


class _Facts:
    """Per-item period tables for one taxonomy/currency, after PIT and revision rules."""

    def __init__(self, payload, taxonomy, currency, cutoff):
        self.taxonomy, self.currency, self.cutoff = taxonomy, currency, cutoff
        facts = payload.get('facts') if isinstance(payload.get('facts'), dict) else {}
        facts = facts.get(taxonomy) if isinstance(facts.get(taxonomy), dict) else {}
        self.items, self.concepts, self.sources = {}, {}, {}
        cik = payload.get('cik')
        cik = str(cik).zfill(10) if type(cik) in (int, str) and str(cik).isdigit() else None
        exceptions = ISSUER_CONCEPT_EXCEPTIONS.get(cik, {}) if taxonomy == 'us-gaap' else {}
        self.issuer_exceptions = tuple(sorted(exceptions))
        for item, concepts in CONCEPTS[taxonomy].items():
            concepts = exceptions.get(item, concepts)
            unit = self._unit(item)
            self.concepts[item] = tuple(concepts)
            tables = [self._table(facts.get(concept), unit, item in INSTANT_ITEMS) for concept in concepts]
            self.items[item] = [table for table, _ in tables]
            self.sources[item] = [source for _, source in tables]
        self._share_filings(facts)
        self._split_ratios(payload)

    def _share_filings(self, facts):
        """{filing: {(concept index, start, end): diluted shares}} for every annual-form annual span and 10-Q YTD/quarter
        span (filed <= cutoff, > 0); a filing = (accession, filed date). A period reported twice in one filing with two
        values is dropped. Used only to detect restatements (splits) between filings."""
        self.share_filings = {}
        dropped = set()
        for n, concept in enumerate(self.concepts.get('diluted_shares', ())):
            node = facts.get(concept)
            rows = node.get('units', {}).get('shares') if isinstance(node, dict) and isinstance(node.get('units'), dict) else None
            for row in rows if isinstance(rows, list) else ():
                if not isinstance(row, dict):
                    continue
                form, filed, value = row.get('form'), _day(row.get('filed')), row.get('val')
                start, end = _day(row.get('start')), _day(row.get('end'))
                if None in (start, end, filed) or filed > self.cutoff or not _finite(value) or value <= 0:
                    continue
                days = (end - start).days
                if not (ANNUAL_DAYS[0] <= days <= ANNUAL_DAYS[1] and form in ANNUAL_FORMS
                        or YTD_DAYS[0] <= days <= YTD_DAYS[1] and form in QUARTER_FORMS):
                    continue
                filing, key = (row.get('accn') if isinstance(row.get('accn'), str) else None, filed), (n, start, end)
                values = self.share_filings.setdefault(filing, {})
                if key in values and values[key] != value:
                    dropped.add((filing, key))
                values.setdefault(key, value)
        for filing, key in dropped:
            self.share_filings[filing].pop(key, None)

    def _split_ratios(self, payload):
        """[(filed, ratio)] of the us-gaap stock-split ratio facts filed <= cutoff (any taxonomy of the row)."""
        facts = payload.get('facts') if isinstance(payload.get('facts'), dict) else {}
        group = facts.get('us-gaap') if isinstance(facts.get('us-gaap'), dict) else {}
        self.split_ratios = []
        for concept in SPLIT_RATIO_CONCEPTS:
            node = group.get(concept)
            units = node.get('units') if isinstance(node, dict) and isinstance(node.get('units'), dict) else {}
            for rows in units.values():
                for row in rows if isinstance(rows, list) else ():
                    filed, value = _day(row.get('filed')) if isinstance(row, dict) else None, row.get('val') if isinstance(row, dict) else None
                    if filed is not None and filed <= self.cutoff and _finite(value) and value > 0 and abs(value - 1.0) > SHARE_REVISION_TOLERANCE:
                        self.split_ratios.append((filed, float(value)))

    def _unit(self, item):
        if item == 'diluted_shares':
            return 'shares'
        if item == 'eps_diluted':
            return self.currency + '/shares'
        return self.currency

    def _table(self, concept, unit, instant):
        """({(start|None, end): value}, {key: filing}) with latest-filed wins and same-filed conflicts dropped;
        filing = (accession, filed date) of the kept value."""
        if not isinstance(concept, dict) or not isinstance(concept.get('units'), dict):
            return {}, {}
        rows = concept['units'].get(unit)
        if not isinstance(rows, list):
            return {}, {}
        best, dropped = {}, set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            form, filed, value = row.get('form'), _day(row.get('filed')), row.get('val')
            end = _day(row.get('end'))
            if end is None or filed is None or filed > self.cutoff or not _finite(value):
                continue
            if instant:
                if form not in INSTANT_FORMS or row.get('start') is not None and _day(row.get('start')) is not None:
                    continue
                key = (None, end)
            else:
                start = _day(row.get('start'))
                if start is None:
                    continue
                days = (end - start).days
                # Annual spans only from annual forms; year-to-date spans only from 10-Q forms.
                if not (ANNUAL_DAYS[0] <= days <= ANNUAL_DAYS[1] and form in ANNUAL_FORMS
                        or YTD_DAYS[0] <= days <= YTD_DAYS[1] and form in QUARTER_FORMS):
                    continue
                key = (start, end)
            previous = best.get(key)
            accn = row.get('accn') if isinstance(row.get('accn'), str) else None
            if previous is None or filed > previous[0]:
                best[key] = (filed, value, accn)
                dropped.discard(key)
            elif filed == previous[0] and value != previous[1]:
                dropped.add(key)
        kept = {key: entry for key, entry in best.items() if key not in dropped}
        return {key: v for key, (_, v, _) in kept.items()}, {key: (accn, filed) for key, (filed, _, accn) in kept.items()}

    # ---- lookups ----
    def annual_ends(self, item):
        ends = set()
        for table in self.items[item]:
            ends.update(end for (start, end) in table if start is not None and ANNUAL_DAYS[0] <= (end - start).days <= ANNUAL_DAYS[1])
        return ends

    def annual(self, item, target, tables=None):
        """(value, start, end) for the fiscal year ending within tolerance of `target`; first concept wins."""
        for table in self.items[item] if tables is None else tables:
            hits = [(abs((end - target).days), start, end, v) for (start, end), v in table.items()
                    if start is not None and ANNUAL_DAYS[0] <= (end - start).days <= ANNUAL_DAYS[1]
                    and abs((end - target).days) <= YEAR_TOLERANCE_DAYS]
            if hits:
                hits.sort()
                _, start, end, value = hits[0]
                return value, start, end
        return None

    def annual_filing(self, item, target):
        """The filing (accession, filed) of the value annual(item, target) returns; None when there is none."""
        for table, source in zip(self.items[item], self.sources[item]):
            hits = [(abs((end - target).days), start, end) for (start, end) in table
                    if start is not None and ANNUAL_DAYS[0] <= (end - start).days <= ANNUAL_DAYS[1]
                    and abs((end - target).days) <= YEAR_TOLERANCE_DAYS]
            if hits:
                hits.sort()
                return source.get(hits[0][1:])
        return None

    def latest_duration_filing(self, item):
        """The filing of the value latest_duration(item) returns."""
        for table, source in zip(self.items[item], self.sources[item]):
            if table:
                key = max(table, key=lambda k: (k[1], -(k[1] - k[0]).days))
                return source.get(key)
        return None

    def ytd(self, item, start_near, end_near, tables=None):
        for table in self.items[item] if tables is None else tables:
            hits = [(abs((s - start_near).days) + abs((e - end_near).days), s, e, v) for (s, e), v in table.items()
                    if s is not None and YTD_DAYS[0] <= (e - s).days <= YTD_DAYS[1]
                    and abs((s - start_near).days) <= YTD_TOLERANCE_DAYS and abs((e - end_near).days) <= YTD_TOLERANCE_DAYS]
            if hits:
                hits.sort()
                return hits[0][3], hits[0][1], hits[0][2]
        return None

    def latest_ytd_end(self, item, fiscal_start, tables=None):
        """Latest end of a YTD fact that starts at `fiscal_start` (first concept with any such fact)."""
        for table in self.items[item] if tables is None else tables:
            ends = [e for (s, e) in table if s is not None and YTD_DAYS[0] <= (e - s).days <= YTD_DAYS[1]
                    and abs((s - fiscal_start).days) <= YTD_TOLERANCE_DAYS]
            if ends:
                return max(ends)
        return None

    def instant(self, item, target, tolerance=YEAR_TOLERANCE_DAYS):
        for table in self.items[item]:
            hits = [(abs((end - target).days), end, v) for (_, end), v in table.items() if abs((end - target).days) <= tolerance]
            if hits:
                hits.sort()
                return hits[0][2]
        return None

    def instant_ends(self, item):
        out = set()
        for table in self.items[item]:
            out.update(end for (_, end) in table)
        return out

    def latest_duration(self, item):
        """(value, end) of the latest-ending annual or quarterly-span fact (first concept with any fact)."""
        for table in self.items[item]:
            if table:
                (start, end), value = max(table.items(), key=lambda kv: (kv[0][1], -(kv[0][1] - kv[0][0]).days))
                return value, end
        return None

    def latest_duration_any_concept(self, item):
        """(value, end, filing) of the latest-ending positive annual or quarterly-span fact over ALL allowed concepts of
        `item` (V-STALE-SHARES, calc_version 2026-10-17.1): the latest period end wins; at the same end the earlier-listed
        concept; within one concept the shortest span (as latest_duration). Only facts the tables kept (filed <= cutoff,
        annual spans from annual forms, YTD/quarter spans from 10-Q forms). Read only for v_inputs_v2.diluted_shares;
        latest_duration keeps its first-concept rule."""
        best = None
        for n, (table, source) in enumerate(zip(self.items[item], self.sources[item])):
            for (start, end), value in table.items():
                if start is None or not _finite(value) or value <= 0:
                    continue
                rank = (end, -n, -(end - start).days)
                if best is None or rank > best[0]:
                    best = (rank, value, end, source.get((start, end)))
        return None if best is None else best[1:]


def _taxonomy_and_currency(payload, cutoff):
    facts = payload.get('facts') if isinstance(payload, dict) else None
    if not isinstance(facts, dict):
        return None, None
    best = None
    for taxonomy in ('us-gaap', 'ifrs-full'):
        group = facts.get(taxonomy)
        if not isinstance(group, dict):
            continue
        # Currency of the latest annual anchor fact (net income, then revenue).
        latest = None
        for item in ('net_income', 'revenue'):
            for concept in CONCEPTS[taxonomy][item]:
                units = group.get(concept, {}).get('units') if isinstance(group.get(concept), dict) else None
                if not isinstance(units, dict):
                    continue
                for unit, rows in units.items():
                    if not re.fullmatch(r'[A-Z]{3}', str(unit)) or not isinstance(rows, list):
                        continue
                    for row in rows:
                        if not isinstance(row, dict) or row.get('form') not in ANNUAL_FORMS:
                            continue
                        end, start, filed = _day(row.get('end')), _day(row.get('start')), _day(row.get('filed'))
                        if end is None or start is None or filed is None or filed > cutoff or not _finite(row.get('val')):
                            continue
                        if not ANNUAL_DAYS[0] <= (end - start).days <= ANNUAL_DAYS[1]:
                            continue
                        key = (end, unit == 'USD', unit)
                        if latest is None or key > latest:
                            latest = key
        # The taxonomy with the latest annual anchor wins (a filer that moved from us-gaap to ifrs-full or back);
        # us-gaap on an equal end date.
        if latest is not None and (best is None or latest[0] > best[0]):
            best = (latest[0], taxonomy, latest[2])
    return (best[1], best[2]) if best is not None else (None, None)


def _div(num, den, *, positive_den=True):
    if num is None or den is None:
        return None
    if positive_den and den <= 0 or den == 0:
        return None
    out = num / den
    return out if math.isfinite(out) else None


def _cagr(new, old, years):
    if new is None or old is None or new <= 0 or old <= 0:
        return None
    out = (new / old) ** (1.0 / years) - 1.0
    return out if math.isfinite(out) else None


def _mean(values):
    return math.fsum(values) / len(values)


def _pstdev(values):
    mu = _mean(values)
    return math.sqrt(math.fsum((v - mu) ** 2 for v in values) / len(values))


def _avg_pair(a, b):
    """Average of opening and closing balances when both exist, else the closing balance."""
    if a is None:
        return None
    return a if b is None else (a + b) / 2.0


class _Company:
    def __init__(self, facts, fy0_end, *, sic=None, profile='GENERAL'):
        self.f, self.fy0, self.sic, self.profile = facts, fy0_end, sic, profile
        self._cache = {}
        # The SEC-only rules (software capex, ...) read component tables of a companyfacts payload; other period
        # adapters (DART) keep the shared definitions only.
        self.sec = isinstance(facts, _Facts)

    def end(self, k):
        return _shift_years(self.fy0, k)

    def a(self, item, k):
        key = ('a', item, k)
        if key not in self._cache:
            hit = self.annual_hit(item, self.end(k))
            self._cache[key] = hit[0] if hit else None
        return self._cache[key]

    # ---- fallback lines (QGV_V2_QG_METHOD.md section 1). Each needs every component it names: never 0-filled. ----
    def _component(self, item, target):
        """Per-concept hits of a component item for one fiscal year: [(hit, table)]. Adapters without the item: []."""
        return [(hit, table) for hit, table, _ in self._component_named(item, target)]

    def _component_named(self, item, target):
        """[(hit, table, concept name)] in list order (concept name None for adapters without names)."""
        out = []
        names = getattr(self.f, 'concepts', {}).get(item, ())
        for n, table in enumerate(self.f.items.get(item) or ()):
            hit = self.f.annual(item, target, [table])
            if hit is not None:
                out.append((hit, table, names[n] if n < len(names) else None))
        return out

    def _single(self, item, target):
        hits = self._component(item, target)
        return hits[0][0] if hits else None

    def _pair_sum(self, first, second, target):
        a, b = self._single(first, target), self._single(second, target)
        if a is None or b is None or a[1:] != b[1:]:
            return None
        return a[0] + b[0], a[1], a[2]

    def capex_fallback(self, target):
        """(hit, table) of the one fallback capex line reported for the year; None when none or ambiguous."""
        found = self._capex_fallback_named(target)
        return found[:2] if found else None

    def _capex_fallback_named(self, target):
        hits = self._component_named('capital_expenditure_fallback', target)
        partial = bool(self._component('capital_expenditure_partial_lines', target))
        if self.sic == REIT_SIC:  # Q-MAA: a REIT's capital improvements are a partial capex line
            partial = partial or any(name in REIT_PARTIAL_CAPEX_FALLBACK for _, _, name in hits)
            hits = [h for h in hits if h[2] not in REIT_PARTIAL_CAPEX_FALLBACK]
        if len(hits) != 1 or partial:
            return None
        return hits[0]

    def _capex_base(self, target):
        """(hit, table, concept) of the physical capex line: the priority list first (first concept wins), then F3."""
        hits = self._component_named('capital_expenditure', target)
        if hits:
            return hits[0]
        return self._capex_fallback_named(target)

    def _software(self, span):
        """[(hit, table, concept)] of the capitalized-software lines of exactly `span` (start, end), each >= 0:
        PaymentsForSoftware alone when reported (a total of the parts), else every reported part. [] when none."""
        pick = lambda item: [h for h in self._component_named(item, span[1]) if h[0][1:] == span and h[0][0] >= 0]
        total = pick('capital_expenditure_software_total')
        return total[:1] if total else pick('capital_expenditure_software_parts')

    def _capex_with_software(self, target):
        """(hit, software lines) for one fiscal year (QGV_V2_QG_METHOD.md section 1, rule SW). Software is added only to a
        physical capex line of the same span, never to PaymentsToAcquireProductiveAssets (its definition includes software),
        and not when a reported PaymentsToAcquireProductiveAssets total of the span is smaller than PP&E + software (the
        software would then already be inside the PP&E line). Software alone is not capex."""
        base = self._capex_base(target)
        if base is None:
            return None, []
        hit, _, concept = base
        if concept in CAPEX_INCLUDES_SOFTWARE:
            return hit, []
        software = self._software(hit[1:])
        if not software:
            return hit, []
        added = math.fsum(h[0][0] for h in software)
        for total_hit, _, name in self._component_named('capital_expenditure', target):
            if name in CAPEX_INCLUDES_SOFTWARE and total_hit[1:] == hit[1:]:
                if total_hit[0] < (hit[0] + added) * (1.0 - CAPEX_SOFTWARE_TOLERANCE):
                    return hit, []
        return (hit[0] + added, hit[1], hit[2]), software

    def _depreciation_amortization(self, total, target):
        """Depreciation + AmortizationOfIntangibleAssets (same period, both >= 0) replaces the total D&A line when
        (a) no total D&A concept is reported for the year, or (b) the total equals Depreciation within
        DA_DEPRECIATION_ONLY_TOLERANCE and the intangible amortization is larger than the total, so the total cannot
        contain it (FIX). Otherwise the total is kept: a total that may already include the amortization is never
        added to again (no double count)."""
        dep, amo = self._single('depreciation', target), self._single('amortization_of_intangibles', target)
        if dep is None or amo is None or dep[1:] != amo[1:] or dep[0] < 0 or amo[0] < 0:
            return total
        combined = (dep[0] + amo[0], dep[1], dep[2])
        if total is None:
            return combined
        if (total[1:] == dep[1:] and abs(total[0] - dep[0]) <= DA_DEPRECIATION_ONLY_TOLERANCE * abs(dep[0])
                and amo[0] > total[0]):
            return combined
        return total

    # ---- EBIT substitute (rule EBIT, owner decision Q-EBIT 2026-10-15) ----
    def ebit_substitute_on(self):
        """SEC GENERAL issuers only: for a bank or insurer the interest expense is an operating cost, so pretax + interest is
        not an operating result; the DART adapter always reports operating income."""
        return self.sec and self.profile == 'GENERAL'

    def _ebit_substitute(self, target):
        """EBIT = pretax income (incl. F1) + interest expense of the same span (>= 0) when no operating income is reported
        for the year. Both are needed: a missing interest expense is never taken as 0."""
        pretax, interest = self.annual_hit('pretax_income', target), self.f.annual('interest_expense', target)
        if pretax is None or interest is None or pretax[1:] != interest[1:] or interest[0] < 0:
            return None
        return pretax[0] + interest[0], pretax[1], pretax[2]

    def ebit_estimated(self, k):
        """True when year k's EBIT is the substitute (no reported operating income, substitute available)."""
        return self.ebit_substitute_on() and self.f.annual('ebit', self.end(k)) is None and self.a('ebit', k) is not None

    def annual_hit(self, item, target):
        """(value, start, end) for one fiscal year: the item's concept list first, then its documented fallback."""
        if item == 'capital_expenditure' and self.sec:
            return self._capex_with_software(target)[0]
        hit = self.f.annual(item, target)
        if item == 'depreciation_amortization':
            return self._depreciation_amortization(hit, target)
        if hit is not None:
            return hit
        if item == 'pretax_income':
            return self._pair_sum('pretax_income_domestic', 'pretax_income_foreign', target)
        if item == 'ebit' and self.ebit_substitute_on():
            return self._ebit_substitute(target)
        if item == 'capital_expenditure':
            found = self.capex_fallback(target)
            return found[0] if found else None
        return None

    def i(self, item, k):
        key = ('i', item, k)
        if key not in self._cache:
            self._cache[key] = self.f.instant(item, self.end(k))
        return self._cache[key]

    # ---- composite lines ----
    def debt_at(self, target, tolerance=YEAR_TOLERANCE_DAYS):
        """Long-term debt incl. current maturities + short-term borrowings; None when no debt concept is reported."""
        inst = lambda item: self.f.instant(item, target, tolerance)
        total_lt = inst('debt_total_long_term')
        if total_lt is not None:
            long_term = total_lt
        else:
            noncurrent = inst('debt_noncurrent')
            current = inst('debt_current_maturities')
            if current is None and noncurrent is not None:
                # DebtCurrent already includes short-term borrowings: use it instead of adding them again.
                combined = inst('debt_current_total')
                if combined is not None:
                    return noncurrent + combined
            long_term = None if noncurrent is None else noncurrent + (current if current is not None else 0.0)
        short = inst('debt_short_term')
        if long_term is None and short is None:
            return None
        return (long_term if long_term is not None else 0.0) + (short if short is not None else 0.0)

    def debt(self, k):
        key = ('debt', k)
        if key not in self._cache:
            debt = self.debt_at(self.end(k))
            self._cache[key] = debt if debt is not None else self.debt_rule(self.end(k))
        return self._cache[key]

    def _any_instant(self, item, target, tolerance=YEAR_TOLERANCE_DAYS):
        """Values of every concept of `item` reported at `target` (the per-concept nearest end)."""
        out = []
        for table in self.f.items.get(item) or ():
            hits = sorted((abs((end - target).days), v) for (_, end), v in table.items() if abs((end - target).days) <= tolerance)
            if hits:
                out.append(hits[0][1])
        return out

    def debt_rule(self, target):
        """Debt at a fiscal-year-end balance sheet that reports none of the debt lines (QGV_V2_QG_METHOD.md section 1, rule
        NODEBT; owner decision Q-NODEBT 2026-10-15). us-gaap SEC payloads only; None (NA) unless every condition holds:
        - a balance sheet exists at `target` (total assets or equity reported);
        - no debt line and no debt-evidence concept (convertible/senior notes, notes/loans payable, credit lines, ...) has a
          non-zero value at `target` (a reported 0 is a reported zero, not a debt);
        - without finance-lease liabilities: every interest-expense concept of the fiscal year is 0 or unreported -> debt 0;
        - with finance-lease liabilities only: debt = the lease liability (total, else noncurrent + current, both needed),
          and every non-zero interest expense of the year is at most FinanceLeaseInterestExpense (the interest is the lease's).
        An issuer with debt under other concepts (DXCM) or under extension tags with interest expense (ORCL, F, GM) stays NA."""
        if not self.sec or self.f.taxonomy != 'us-gaap':
            return None
        if self.f.instant('total_assets', target) is None and self.f.instant('equity', target) is None:
            return None
        if any(v != 0 for item in DEBT_ITEMS + ('debt_evidence',) for v in self._any_instant(item, target)):
            return None
        interest = [hit[0] for hit, _, _ in self._component_named('interest_expense_evidence', target) if hit[0] != 0]
        lease_total = self.f.instant('finance_lease_total', target)
        lease_parts = (self.f.instant('finance_lease_noncurrent', target), self.f.instant('finance_lease_current', target))
        if lease_total is None and all(v is None or v == 0 for v in lease_parts):
            return 0.0 if not interest else None
        lease = lease_total if lease_total is not None else (None if None in lease_parts else lease_parts[0] + lease_parts[1])
        if lease is None or lease < 0:
            return None
        if interest:
            lease_interest = self._single('finance_lease_interest', target)
            if lease_interest is None or any(v < 0 or v > lease_interest[0] * (1.0 + LEASE_INTEREST_TOLERANCE) for v in interest):
                return None
        return float(lease)

    def tax_rate(self, k):
        pretax, tax = self.a('pretax_income', k), self.a('income_tax', k)
        if pretax is not None and tax is not None and pretax > 0:
            return min(TAX_RATE_BOUNDS[1], max(TAX_RATE_BOUNDS[0], tax / pretax))
        return DEFAULT_TAX_RATE

    def nopat(self, k):
        ebit = self.a('ebit', k)
        return None if ebit is None else ebit * (1.0 - self.tax_rate(k))

    def invested_capital(self, k):
        equity, debt, cash = self.i('equity', k), self.debt(k), self.i('cash_and_equivalents', k)
        if equity is None or debt is None or cash is None:
            return None
        ic = equity + debt - cash
        return ic if ic > 0 else None

    def roic(self, k):
        nopat, closing, opening = self.nopat(k), self.invested_capital(k), self.invested_capital(k + 1)
        return _div(nopat, _avg_pair(closing, opening))

    def roe(self, k):
        ni, closing, opening = self.a('net_income', k), self.i('equity', k), self.i('equity', k + 1)
        if closing is None or closing <= 0 or opening is not None and opening <= 0:
            return None
        return _div(ni, _avg_pair(closing, opening))

    def gross_profit(self, k):
        gp = self.a('gross_profit', k)
        if gp is not None:
            return gp
        revenue, cost = self.a('revenue', k), self.a('cost_of_revenue', k)
        return None if revenue is None or cost is None else revenue - cost

    def fcf(self, k):
        ocf, capex = self.a('operating_cash_flow', k), self.a('capital_expenditure', k)
        return None if ocf is None or capex is None else ocf - capex

    # ---- stock-split adjustment (rule SPLIT, owner decision Q-SPLIT 2026-10-15) ----
    def _basis(self):
        """The filing whose share basis all per-share values are restated to: that of the FY0 diluted share count (else of
        FY0 diluted EPS)."""
        if 'basis' not in self._cache:
            self._cache['basis'] = self.f.annual_filing('diluted_shares', self.fy0) or self.f.annual_filing('eps_diluted', self.fy0)
        return self._cache['basis']

    def _edge(self, a, b):
        """Factor turning a share count of filing a's basis into filing b's, from the periods both report: 1 for an ordinary
        revision (within SHARE_REVISION_TOLERANCE), a reported split ratio (or reciprocal) the restatement matches, 'X' for an
        unconfirmed restatement, None when they share no period."""
        va, vb = self.f.share_filings.get(a, {}), self.f.share_filings.get(b, {})
        ratios = [vb[key] / va[key] for key in va.keys() & vb.keys()]
        if not ratios:
            return None
        if all(abs(r - 1.0) <= SHARE_REVISION_TOLERANCE for r in ratios):
            return 1.0
        candidates = sorted({c for _, s in self.f.split_ratios for c in (s, 1.0 / s)})
        for c in candidates:
            if all(abs(r / c - 1.0) <= SPLIT_MATCH_TOLERANCE for r in ratios):
                return c
        return 'X'

    def share_factor(self, filing, target=None):
        """Multiply a share count reported in `filing` by this factor to restate it to `target`'s basis (default: the FY0
        basis); divide a per-share value by it. 1.0 outside SEC payloads. None when the basis cannot be established:
        - filings are linked through periods both report (a confirmed split or an ordinary revision on every link);
        - linked only through an unconfirmed restatement (no matching split-ratio fact, e.g. a 1,000x unit change): None;
        - not linked at all: 1.0 unless a split-ratio fact was filed between the two filings (then None)."""
        if not self.sec:
            return 1.0
        target = self._basis() if target is None else target
        if filing is None or target is None or filing == target:
            return 1.0
        key = ('share_factor', filing, target)
        if key in self._cache:
            return self._cache[key]
        nodes, index = self.f.share_filings, self._period_index()
        result, seen, frontier = None, {filing: 1.0}, [filing]
        while frontier and result is None:  # breadth-first over confirmed links
            nxt = []
            for node in frontier:
                for other in sorted({o for period in nodes.get(node, {}) for o in index[period]} - {node}, key=str):
                    edge = self._edge(node, other)
                    if edge is None or edge == 'X' or other in seen:
                        continue
                    seen[other] = seen[node] * edge
                    if other == target:
                        result = seen[other]
                        break
                    nxt.append(other)
                if result is not None:
                    break
            frontier = nxt
        if result is None:
            reachable = self._linked(filing, index)
            if target in reachable:
                result = None  # only through an unconfirmed restatement
            else:
                low, high = sorted((filing[1], target[1]))
                result = None if any(low < filed <= high for filed, _ in self.f.split_ratios) else 1.0
        self._cache[key] = result
        return result

    def _period_index(self):
        if 'period_index' not in self._cache:
            index = {}
            for node, values in self.f.share_filings.items():
                for period in values:
                    index.setdefault(period, set()).add(node)
            self._cache['period_index'] = index
        return self._cache['period_index']

    def _linked(self, filing, index):
        nodes, seen, stack = self.f.share_filings, {filing}, [filing]
        while stack:
            node = stack.pop()
            for period in nodes.get(node, {}):
                for other in index[period] - seen:
                    seen.add(other)
                    stack.append(other)
        return seen

    def _raw_shares(self, k):
        return self.a('diluted_shares', k)

    def shares(self, k):
        """Diluted share count of year k on the FY0 basis (split-adjusted); None when the basis cannot be established or
        the adjusted count is more than SHARE_JUMP_LIMIT away from FY0's (unexplained discontinuity)."""
        key = ('shares', k)
        if key not in self._cache:
            raw = self._raw_shares(k)
            out = raw
            if raw is not None and self.sec:
                factor = self.share_factor(self.f.annual_filing('diluted_shares', self.end(k)))
                out = None if factor is None else raw * factor
                if out is not None and k > 0 and self._jump(out):
                    out = None
            self._cache[key] = out
        return self._cache[key]

    def _jump(self, adjusted):
        base = self.shares(0)
        return base is not None and base > 0 and not 1.0 / SHARE_JUMP_LIMIT <= adjusted / base <= SHARE_JUMP_LIMIT

    def eps(self, k):
        """Diluted EPS of year k on the FY0 share basis; None when its filing's basis cannot be established or year k's
        share count is an unexplained discontinuity."""
        raw = self.a('eps_diluted', k)
        if raw is None or not self.sec:
            return raw
        factor = self.share_factor(self.f.annual_filing('eps_diluted', self.end(k)))
        if factor is None or k > 0 and self._raw_shares(k) is not None and self.shares(k) is None:
            return None
        return raw / factor

    def per_share(self, value, k):
        return _div(value, self.shares(k))

    # ---- TTM ----
    def ttm(self, item):
        """(ttm_value, period_end, ttm_year_ago_value): FY0 + YTD - YTD(prior year), all from ONE concept;
        FY0 alone (period end = FY0 end) when no concept has a later 10-Q with its prior-year comparative.
        Capex with capitalized software (SEC): TTM of the physical line + TTM of each software line, only when every one
        ends on the same date (else None: FY and TTM never mix spans); the year-ago TTM is then not derived."""
        software = self._capex_with_software(self.fy0)[1] if item == 'capital_expenditure' and self.sec else []
        if software:
            base = self._capex_base(self.fy0)
            out = self._ttm_one(item, base[0], [base[1]], single=True)
            parts = [out] + [self._ttm_one(item, h, [table], single=True) for h, table, _ in software]
            if any(p[1] != out[1] for p in parts):
                return None
            return math.fsum(p[0] for p in parts), out[1], None
        if item == 'ebit' and self.f.annual(item, self.fy0) is None and self.ebit_substitute_on():
            # Substitute TTM = TTM pretax + TTM interest, only when both end on the same date (never mixed spans).
            if self._ebit_substitute(self.fy0) is None:
                return None
            pretax, interest = self.ttm('pretax_income'), self.ttm('interest_expense')
            if pretax is None or interest is None or pretax[1] != interest[1]:
                return None
            ago = None if pretax[2] is None or interest[2] is None else pretax[2] + interest[2]
            return pretax[0] + interest[0], pretax[1], ago
        fy0, tables = self.f.annual(item, self.fy0), self.f.items[item]
        if fy0 is None and item == 'capital_expenditure':
            found = self.capex_fallback(self.fy0)  # the one fallback line, still a single concept for FY0 and YTD
            if found is not None:
                fy0, tables = found[0], [found[1]]
        if fy0 is None:
            return None
        return self._ttm_one(item, fy0, tables)

    def _ttm_one(self, item, fy0, tables, single=False):
        """TTM over `tables` (first table with FY0 + later 10-Q YTD + prior-year YTD), else FY0 alone. `single`: the
        year-ago value also comes from `tables` only (a component line), not from the item's full rule."""
        for table in tables:
            one = [table]
            hit = self.f.annual(item, self.fy0, one)
            if hit is None:
                continue
            value0, start0, end0 = hit
            fiscal_start = end0 + timedelta(days=1)
            latest = self.f.latest_ytd_end(item, fiscal_start, one)
            if latest is None or latest <= end0:
                continue
            cur = self.f.ytd(item, fiscal_start, latest, one)
            prev = self.f.ytd(item, start0, _shift_years(latest, 1), one)
            if cur is None or prev is None:
                continue
            ago = None
            fy1 = self.f.annual(item, _shift_years(end0, 1), one)
            if fy1 is not None:
                prev2 = self.f.ytd(item, fy1[1], _shift_years(latest, 2), one)
                if prev2 is not None:
                    ago = fy1[0] + prev[0] - prev2[0]
            return value0 + cur[0] - prev[0], cur[2], ago
        fy1 = self.f.annual(item, _shift_years(fy0[2], 1), tables) if single else self.annual_hit(item, _shift_years(fy0[2], 1))
        return fy0[0], fy0[2], (fy1[0] if fy1 else None)


def _metrics_general(c):
    m = dict.fromkeys(METRIC_KEYS)
    m['roic'] = c.roic(0)
    m['gross_profit_to_assets'] = _div(c.gross_profit(0), c.i('total_assets', 0))
    ni, ocf = c.a('net_income', 0), c.a('operating_cash_flow', 0)
    assets = _avg_pair(c.i('total_assets', 0), c.i('total_assets', 1))
    m['accruals_to_assets'] = None if ni is None or ocf is None else _div(ni - ocf, assets)
    m['fcf_to_net_income'] = _div(c.fcf(0), ni)  # NI <= 0 -> None
    ebit, da = c.a('ebit', 0), c.a('depreciation_amortization', 0)
    ebitda = None if ebit is None or da is None else ebit + da
    debt, cash = c.debt(0), c.i('cash_and_equivalents', 0)
    m['net_debt_to_ebitda'] = None if debt is None or cash is None else _div(debt - cash, ebitda)
    m['interest_coverage'] = _div(ebit, c.a('interest_expense', 0))
    m['incremental_roic_5y'] = _incremental(c.nopat(0), c.nopat(5), c.invested_capital(0), c.invested_capital(5))
    m['incremental_roic_3y'] = _incremental(c.nopat(0), c.nopat(3), c.invested_capital(0), c.invested_capital(3))
    _moat(m, [c.roic(k) for k in range(HISTORY_YEARS)])
    m['fcf_per_share_cagr_3y'] = _cagr(c.per_share(c.fcf(0), 0), c.per_share(c.fcf(3), 3), 3)
    return m


def _metrics_financial(c):
    m = dict.fromkeys(METRIC_KEYS)
    ni = c.a('net_income', 0)
    assets = _avg_pair(c.i('total_assets', 0), c.i('total_assets', 1))
    m['roe'] = c.roe(0)
    m['roa'] = _div(ni, assets)
    m['net_interest_income_to_assets'] = _div(c.a('net_interest_income', 0), assets)
    m['equity_to_assets'] = _div(c.i('equity', 0), c.i('total_assets', 0))
    m['incremental_roe_5y'] = _incremental(ni, c.a('net_income', 5), c.i('equity', 0), c.i('equity', 5))
    m['incremental_roe_3y'] = _incremental(ni, c.a('net_income', 3), c.i('equity', 0), c.i('equity', 3))
    _moat(m, [c.roe(k) for k in range(HISTORY_YEARS)])
    bvps = lambda k: None if c.i('equity', k) is None or c.i('equity', k) <= 0 else c.per_share(c.i('equity', k), k)
    m['book_value_per_share_cagr_3y'] = _cagr(bvps(0), bvps(3), 3)
    return m


def _incremental(new_return, old_return, new_capital, old_capital):
    if None in (new_return, old_return, new_capital, old_capital):
        return None
    return _div(new_return - old_return, new_capital - old_capital)  # capital must have grown


def _moat(m, returns):
    """Level x persistence over up to 5 fiscal years (>= 3 required): mean x max(0, 1 - std/mean); mean <= 0 -> mean."""
    values = [r for r in returns if r is not None]
    if len(values) < 3:
        return
    mu, sigma = _mean(values), _pstdev(values)
    m['moat_return_mean_5y'], m['moat_return_std_5y'], m['moat_return_years'] = mu, sigma, len(values)
    m['moat_proxy'] = mu * max(0.0, 1.0 - sigma / mu) if mu > 0 else mu


def _growth_common(c, m):
    m['revenue_cagr_3y'] = _cagr(c.a('revenue', 0), c.a('revenue', 3), 3)
    m['eps_cagr_3y'] = _cagr(c.eps(0), c.eps(3), 3)
    shares0, shares3 = c.shares(0), c.shares(3)
    m['dilution_3y'] = _cagr(shares0, shares3, 3)
    growth = []
    for k in range(HISTORY_YEARS):
        new, old = c.a('revenue', k), c.a('revenue', k + 1)
        if new is not None and old is not None and old > 0:
            growth.append(new / old - 1.0)
    if len(growth) >= 3:
        m['revenue_positive_growth_share'] = sum(1 for g in growth if g > 0) / len(growth)
        m['revenue_growth_volatility'] = _pstdev(growth)
    # PLAYBOOK decision #18 requires all five annual growth observations, hence six reported FY revenues.
    # Keep the existing >=3-observation G consistency metric unchanged.
    if len(growth) == HISTORY_YEARS:
        m['revenue_growth_std_5y'] = _pstdev(growth)
    ttm = c.ttm('revenue')
    if ttm is not None and ttm[2] is not None and ttm[2] > 0 and ttm[0] is not None:
        m['revenue_ttm_growth'] = ttm[0] / ttm[2] - 1.0
        if m['revenue_cagr_3y'] is not None:
            m['revenue_acceleration'] = m['revenue_ttm_growth'] - m['revenue_cagr_3y']


def _extra_metrics(c, m):
    """SEC-only descriptors (EXTRA_METRIC_KEYS); a profile outside a key's EXTRA_METRIC_PROFILES leaves it None."""
    m.update(dict.fromkeys(EXTRA_METRIC_KEYS))
    years = sorted({c.annual_hit('ebit', c.end(k))[2].year for k in range(HISTORY_YEARS + 1) if c.ebit_estimated(k)})
    if years and c.profile in EXTRA_METRIC_PROFILES['ebit_estimated_years']:
        m['ebit_estimated_years'], m['ebit_estimated_fiscal_years'] = len(years), years
    # roic_avg_3y = mean of ROIC FY0, FY-1, FY-2 (all three needed; same ROIC as `roic`, GENERAL only).
    roic = [c.roic(k) for k in range(QUALITY_ROIC_YEARS)]
    if c.profile in EXTRA_METRIC_PROFILES['roic_avg_3y'] and None not in roic:
        m['roic_avg_3y'] = _mean(roic)
    # operating_margin_std_5y_pp = population std of EBIT / revenue over FY0..FY-4, in percentage points (all five needed,
    # revenue > 0; the margins of v_inputs_v2.operating_margin_history before rounding).
    margins = []
    for k in range(QUALITY_MARGIN_YEARS):
        revenue, ebit = c.a('revenue', k), c.a('ebit', k)
        if revenue is None or revenue <= 0 or ebit is None:
            break
        margins.append(ebit / revenue)
    if len(margins) == QUALITY_MARGIN_YEARS:
        m['operating_margin_std_5y_pp'] = 100.0 * _pstdev(margins)


V_FLOW_KEYS = ('fy_value', 'fy_end', 'ttm_value', 'ttm_end')
V_INSTANT_KEYS = ('value', 'period_end')
LEGACY_V_KEYS = ('currency', 'taxonomy', 'fiscal_year_end', 'ebit', 'fcf', 'total_debt', 'cash_and_equivalents', 'diluted_shares', 'ebit_per_share_history', 'fcf_per_share_history',
          'revenue_cagr_3y', 'eps_cagr_3y', 'fcf_per_share_cagr_3y', 'revenue_ttm_growth')

V_KEYS = LEGACY_V_KEYS + ('revenue', 'operating_margin_history')
# EV balance-sheet inputs that must be on or after the FY0 balance sheet (V-STALE-BS, calc_version 2026-10-17.1).
STALE_BALANCE_SHEET_V_KEYS = ('total_debt', 'cash_and_equivalents')

def empty_v_inputs():
    return {'currency': None, 'taxonomy': None, 'fiscal_year_end': None,
            'ebit': None, 'fcf': None, 'total_debt': None, 'cash_and_equivalents': None, 'diluted_shares': None,
            'ebit_per_share_history': [], 'fcf_per_share_history': [], 'revenue': None, 'operating_margin_history': [],
            'revenue_cagr_3y': None, 'eps_cagr_3y': None, 'fcf_per_share_cagr_3y': None, 'revenue_ttm_growth': None}


def _flow(c, item_value_fy, ttm):
    fy_value, fy_end = item_value_fy
    out = {'fy_value': fy_value, 'fy_end': fy_end, 'ttm_value': None, 'ttm_end': None}
    if ttm is not None:
        out['ttm_value'], out['ttm_end'] = ttm
    return out if out['fy_value'] is not None or out['ttm_value'] is not None else None


def _v_inputs(c, m, taxonomy, currency):
    v = empty_v_inputs()
    v.update(currency=currency, taxonomy=taxonomy, fiscal_year_end=c.fy0.isoformat())

    def fy(item):
        hit = c.annual_hit(item, c.fy0)
        return (hit[0], hit[2].isoformat()) if hit else (None, None)

    def ttm(item):
        hit = c.ttm(item)
        return (hit[0], hit[1].isoformat()) if hit else None

    v['ebit'] = _flow(c, fy('ebit'), ttm('ebit'))
    # FCF = operating cash flow - capital expenditure, both from the same period (FY and TTM separately).
    ocf = _flow(c, fy('operating_cash_flow'), ttm('operating_cash_flow'))
    capex = _flow(c, fy('capital_expenditure'), ttm('capital_expenditure'))
    if ocf is not None and capex is not None:
        fcf = {'fy_value': None, 'fy_end': None, 'ttm_value': None, 'ttm_end': None}
        if ocf['fy_value'] is not None and capex['fy_value'] is not None and ocf['fy_end'] == capex['fy_end']:
            fcf['fy_value'], fcf['fy_end'] = ocf['fy_value'] - capex['fy_value'], ocf['fy_end']
        if ocf['ttm_value'] is not None and capex['ttm_value'] is not None and ocf['ttm_end'] == capex['ttm_end']:
            fcf['ttm_value'], fcf['ttm_end'] = ocf['ttm_value'] - capex['ttm_value'], ocf['ttm_end']
        v['fcf'] = fcf if fcf['fy_value'] is not None or fcf['ttm_value'] is not None else None
    # Latest balance sheet values, each with its own date (any 10-K/10-Q); debt on a date where its lines exist.
    cash_ends = c.f.instant_ends('cash_and_equivalents')
    if cash_ends:
        latest = max(cash_ends)
        v['cash_and_equivalents'] = {'value': c.f.instant('cash_and_equivalents', latest, 0), 'period_end': latest.isoformat()}
    debt_ends = set()
    for item in ('debt_total_long_term', 'debt_noncurrent', 'debt_short_term'):
        debt_ends |= c.f.instant_ends(item)
    for end in sorted(debt_ends, reverse=True):
        debt = c.debt_at(end, 0)
        if debt is not None:
            v['total_debt'] = {'value': debt, 'period_end': end.isoformat()}
            break
    # Debt-free rule at the FY0 balance sheet when no debt line gives a value on or after FY0 end (MNST: a FY-1 debt line
    # repaid in FY0 is not carried forward as the latest debt).
    if v['total_debt'] is None or v['total_debt']['period_end'] < c.fy0.isoformat():
        rule = c.debt_rule(c.fy0) if c.debt_at(c.fy0) is None else None
        if rule is not None:
            v['total_debt'] = {'value': rule, 'period_end': c.fy0.isoformat()}
    # V-STALE-BS (2026-10-17 number check; Q-NODEBT-INT): a debt or cash value dated before the FY0 balance sheet (FY0 end minus
    # the usual instant tolerance) is NA, never the last value reported years earlier (INCY 2018, EME 2023, DECK 2021, PCAR cash
    # 2019). Debt is 0 only when an FY0 line or the approved NODEBT rule says so. The device then shows ebit_yield/fcf_yield
    # as NA with reason DEBT_CASH_NOT_AVAILABLE (qgv-v2.js metrics); missing is never 0.
    oldest = (c.fy0 - timedelta(days=YEAR_TOLERANCE_DAYS)).isoformat()
    for key in STALE_BALANCE_SHEET_V_KEYS:
        if v[key] is not None and v[key]['period_end'] < oldest:
            v[key] = None
    # V-STALE-SHARES (owner decision 2026-10-17, calc_version 2026-10-17.1): the diluted share count is the latest-ending
    # positive fact over ALL allowed diluted-share concepts (not the first concept's last value: BKR 2021, REG 2020, TTWO 2024,
    # HSY 2015, LYB 2019, SJM 2023, ERIE 2021), judged by its period END: an end before FY0 end minus the same tolerance as
    # V-STALE-BS is NA. Never basic shares, shares outstanding or another concept. The device then shows the per-share and
    # EV-based V metrics as NA with reason SHARES_NOT_AVAILABLE (qgv-v2.js metrics); missing is never filled.
    if c.sec:
        shares = c.f.latest_duration_any_concept('diluted_shares')
    else:  # other period adapters (DART): their single annual series
        shares = c.f.latest_duration('diluted_shares')
        shares = None if shares is None else (shares[0], shares[1], None)
    shares_filing = None
    if shares is not None and shares[0] > 0 and shares[1].isoformat() >= oldest:
        v['diluted_shares'] = {'value': shares[0], 'period_end': shares[1].isoformat()}
        shares_filing = shares[2]
    # Per-share histories are on the basis of the latest share count (v['diluted_shares']), which the device pairs with the
    # current price: FY0 basis x the FY0 -> latest factor (the filing of that count; none -> the FY0 basis). Unknown factor
    # (a split filed after FY0 that no shared period confirms) -> both histories NA.
    latest = c.share_factor(c._basis(), shares_filing) if c.sec else 1.0
    for key, value_of in (('ebit_per_share_history', lambda k: c.a('ebit', k)), ('fcf_per_share_history', c.fcf)):
        if latest is None:
            v[key] = []
            continue
        history = []
        for k in range(HISTORY_YEARS - 1, -1, -1):
            hit = c.f.annual('diluted_shares', c.end(k))
            per_share = _div(c.per_share(value_of(k), k), latest)
            if per_share is not None and hit is not None:
                history.append({'fiscal_year_end': hit[2].isoformat(), 'value': _round(per_share)})
        ends = [h['fiscal_year_end'] for h in history]
        v[key] = history if len(set(ends)) == len(ends) else []
    v['revenue'] = _flow(c, fy('revenue'), ttm('revenue'))
    # Price-free annual operating margins. Missing years are absent, never zero-filled.
    margins = []
    for k in range(4, -1, -1):
        revenue, ebit = c.a('revenue', k), c.a('ebit', k)
        hit = c.f.annual('revenue', c.end(k))
        if revenue is not None and revenue > 0 and ebit is not None and hit is not None:
            margins.append({'fiscal_year_end': hit[2].isoformat(), 'value': _round(ebit / revenue)})
    v['operating_margin_history'] = margins
    # Realized growth for the device expectation check (same definitions as the G metrics).
    for key in ('revenue_cagr_3y', 'eps_cagr_3y', 'revenue_ttm_growth'):
        v[key] = _round(m.get(key))
    v['fcf_per_share_cagr_3y'] = _round(_cagr(c.per_share(c.fcf(0), 0), c.per_share(c.fcf(3), 3), 3))
    return v


def compute(companyfacts, *, sic, cutoff):
    """(profile, fiscal_year_end, currency, metrics, v_inputs_v2) for one issuer; metrics rounded for publication.

    `companyfacts` is the parsed SEC JSON; `cutoff` is a date (facts filed later are ignored).
    Missing or unusable inputs give None metrics (never 0). Raises nothing for bad content."""
    profile = profile_for_sic(sic)
    try:
        return _compute(companyfacts, profile, cutoff, sic)
    except (TypeError, ValueError, AttributeError, KeyError, OverflowError, RecursionError, ZeroDivisionError):
        return profile, None, None, dict.fromkeys(METRIC_KEYS), empty_v_inputs()


def _compute(companyfacts, profile, cutoff, sic=None):
    """SEC companyfacts path: the shared metrics plus the SEC-only descriptors EXTRA_METRIC_KEYS."""
    if not isinstance(companyfacts, dict) or not isinstance(cutoff, date):
        return profile, None, None, dict.fromkeys(METRIC_KEYS), empty_v_inputs()
    taxonomy, currency = _taxonomy_and_currency(companyfacts, cutoff)
    if taxonomy is None:
        return profile, None, None, dict.fromkeys(METRIC_KEYS), empty_v_inputs()
    facts = _Facts(companyfacts, taxonomy, currency, cutoff)
    ends = set()
    for item in ANCHOR_ITEMS:
        ends |= facts.annual_ends(item)
    if not ends:
        return profile, None, None, dict.fromkeys(METRIC_KEYS), empty_v_inputs()
    return compute_reported_periods(facts, fiscal_year_end=max(ends), profile=profile, taxonomy=taxonomy, currency=currency,
                                    sic=sic, extra_metrics=True)

def compute_reported_periods(facts, *, fiscal_year_end, profile='GENERAL', taxonomy=None, currency=None, sic=None,
                             extra_metrics=False):
    """Shared Q/G definitions for source adapters, without fabricated SEC facts.

    `facts` supplies annual(item,date), instant(item,date,tolerance), annual/instant_ends,
    latest_duration and .items (reported duration observations). The adapter owns filing
    cutoff/currency/period checks. Missing inputs remain None. Source metadata is supplied
    separately by its caller; this API never assigns a SEC source to a DART observation.
    `extra_metrics` adds EXTRA_METRIC_KEYS (SEC file only); the default key set is METRIC_KEYS exactly.
    """
    if profile not in ('GENERAL', 'FINANCIAL') or not isinstance(fiscal_year_end, date):
        raise ValueError('REPORTED_PERIODS_INVALID')
    company = _Company(facts, fiscal_year_end, sic=sic, profile=profile)
    metrics = _metrics_financial(company) if profile == 'FINANCIAL' else _metrics_general(company)
    _growth_common(company, metrics)
    if extra_metrics:
        _extra_metrics(company, metrics)
    raw = dict(metrics)
    metrics = {k: (_round(v) if k not in INTEGER_METRICS | LIST_METRICS else v) for k, v in metrics.items()}
    for key in INTEGER_METRICS:
        if metrics.get(key) is not None:
            metrics[key] = int(metrics[key])
    v_inputs = _v_inputs(company, raw, taxonomy, currency)
    return profile, company.fy0.isoformat(), currency, metrics, v_inputs
