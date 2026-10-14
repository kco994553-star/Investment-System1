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

# Concept priority lists. For each period the first concept with a usable fact wins.
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
    },
}
FLOW_ITEMS = ('revenue', 'gross_profit', 'cost_of_revenue', 'ebit', 'pretax_income', 'income_tax', 'net_income',
              'operating_cash_flow', 'capital_expenditure', 'depreciation_amortization', 'interest_expense',
              'net_interest_income', 'eps_diluted', 'diluted_shares')
INSTANT_ITEMS = ('total_assets', 'equity', 'cash_and_equivalents', 'debt_total_long_term', 'debt_noncurrent',
                 'debt_current_maturities', 'debt_short_term', 'debt_current_total')
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
        self.items = {}
        for item, concepts in CONCEPTS[taxonomy].items():
            unit = self._unit(item)
            self.items[item] = [self._table(facts.get(concept), unit, item in INSTANT_ITEMS) for concept in concepts]

    def _unit(self, item):
        if item == 'diluted_shares':
            return 'shares'
        if item == 'eps_diluted':
            return self.currency + '/shares'
        return self.currency

    def _table(self, concept, unit, instant):
        """{(start|None, end): value} with latest-filed wins and same-filed conflicts dropped."""
        if not isinstance(concept, dict) or not isinstance(concept.get('units'), dict):
            return {}
        rows = concept['units'].get(unit)
        if not isinstance(rows, list):
            return {}
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
            if previous is None or filed > previous[0]:
                best[key] = (filed, value)
                dropped.discard(key)
            elif filed == previous[0] and value != previous[1]:
                dropped.add(key)
        return {key: v for key, (_, v) in best.items() if key not in dropped}

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
    def __init__(self, facts, fy0_end):
        self.f, self.fy0 = facts, fy0_end
        self._cache = {}

    def end(self, k):
        return _shift_years(self.fy0, k)

    def a(self, item, k):
        key = ('a', item, k)
        if key not in self._cache:
            hit = self.f.annual(item, self.end(k))
            self._cache[key] = hit[0] if hit else None
        return self._cache[key]

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
            self._cache[key] = self.debt_at(self.end(k))
        return self._cache[key]

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

    def per_share(self, value, k):
        return _div(value, self.a('diluted_shares', k))

    # ---- TTM ----
    def ttm(self, item):
        """(ttm_value, period_end, ttm_year_ago_value): FY0 + YTD - YTD(prior year), all from ONE concept;
        FY0 alone (period end = FY0 end) when no concept has a later 10-Q with its prior-year comparative."""
        fy0 = self.f.annual(item, self.fy0)
        if fy0 is None:
            return None
        for table in self.f.items[item]:
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
        fy1 = self.f.annual(item, _shift_years(fy0[2], 1))
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
    m['eps_cagr_3y'] = _cagr(c.a('eps_diluted', 0), c.a('eps_diluted', 3), 3)
    shares0, shares3 = c.a('diluted_shares', 0), c.a('diluted_shares', 3)
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


V_FLOW_KEYS = ('fy_value', 'fy_end', 'ttm_value', 'ttm_end')
V_INSTANT_KEYS = ('value', 'period_end')
LEGACY_V_KEYS = ('currency', 'taxonomy', 'fiscal_year_end', 'ebit', 'fcf', 'total_debt', 'cash_and_equivalents', 'diluted_shares', 'ebit_per_share_history', 'fcf_per_share_history',
          'revenue_cagr_3y', 'eps_cagr_3y', 'fcf_per_share_cagr_3y', 'revenue_ttm_growth')

V_KEYS = LEGACY_V_KEYS + ('revenue', 'operating_margin_history')

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
        hit = c.f.annual(item, c.fy0)
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
    # Latest balance sheet: the latest cash date (any 10-K/10-Q); debt at that exact date.
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
    shares = c.f.latest_duration('diluted_shares')
    if shares is not None and shares[0] > 0:
        v['diluted_shares'] = {'value': shares[0], 'period_end': shares[1].isoformat()}
    for key, value_of in (('ebit_per_share_history', lambda k: c.a('ebit', k)), ('fcf_per_share_history', c.fcf)):
        history = []
        for k in range(HISTORY_YEARS - 1, -1, -1):
            hit = c.f.annual('diluted_shares', c.end(k))
            per_share = c.per_share(value_of(k), k)
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
        return _compute(companyfacts, profile, cutoff)
    except (TypeError, ValueError, AttributeError, KeyError, OverflowError, RecursionError, ZeroDivisionError):
        return profile, None, None, dict.fromkeys(METRIC_KEYS), empty_v_inputs()


def _compute(companyfacts, profile, cutoff):
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
    return compute_reported_periods(facts, fiscal_year_end=max(ends), profile=profile, taxonomy=taxonomy, currency=currency)

def compute_reported_periods(facts, *, fiscal_year_end, profile='GENERAL', taxonomy=None, currency=None):
    """Shared Q/G definitions for source adapters, without fabricated SEC facts.

    `facts` supplies annual(item,date), instant(item,date,tolerance), annual/instant_ends,
    latest_duration and .items (reported duration observations). The adapter owns filing
    cutoff/currency/period checks. Missing inputs remain None. Source metadata is supplied
    separately by its caller; this API never assigns a SEC source to a DART observation.
    """
    if profile not in ('GENERAL', 'FINANCIAL') or not isinstance(fiscal_year_end, date):
        raise ValueError('REPORTED_PERIODS_INVALID')
    company = _Company(facts, fiscal_year_end)
    metrics = _metrics_financial(company) if profile == 'FINANCIAL' else _metrics_general(company)
    _growth_common(company, metrics)
    raw = dict(metrics)
    metrics = {k: (_round(v) if k != 'moat_return_years' else v) for k, v in metrics.items()}
    if metrics['moat_return_years'] is not None:
        metrics['moat_return_years'] = int(metrics['moat_return_years'])
    v_inputs = _v_inputs(company, raw, taxonomy, currency)
    return profile, company.fy0.isoformat(), currency, metrics, v_inputs
