"""DART annual lines through the same v2 ratio/scoring functions; reference targets only.

The current DART projection has one annual report and limited one-year comparatives.
It cannot produce five-year history, 3-year growth, EBITDA, assets, or interest expense.
Those inputs remain missing. KRW amounts are never compared with USD amounts: only
the v2 dimensionless metrics enter the US distribution, and the Korean issuer never
becomes a point in that distribution. No SIC code is guessed for a Korean issuer.
"""
from datetime import date


class _AnnualLines:
    """The period-read interface consumed by qgv.v2_factors._Company."""
    def __init__(self, annual, factor_module):
        self.values = annual['inputs']
        self.year = int(annual['bsns_year'])
        self.items = {key: [] for key in factor_module.FLOW_ITEMS}

    def annual(self, item, end, tables=None):
        aliases = {'ebit': 'operating_income', 'capital_expenditure': 'capex',
                   'eps_diluted': 'eps', 'diluted_shares': None}
        key = aliases.get(item, item)
        if end.month != 12 or end.day != 31 or end.year not in (self.year, self.year - 1):
            return None
        if end.year == self.year - 1:
            key = {'revenue': 'revenue_prev', 'eps_diluted': 'eps_prev', 'ebit': 'operating_income_prev'}.get(item)
        value = self.values.get(key)
        if value is None:
            return None
        if item == 'capital_expenditure':
            value = abs(value)
        return float(value), date(end.year, 1, 1), end

    def instant(self, item, end, tolerance=None):
        if end != date(self.year, 12, 31):
            return None
        key = {'debt_total_long_term': 'total_debt'}.get(item, item)
        # total_debt already comprises short+long+bonds+leases: never add it a second time.
        if item in ('debt_short_term', 'debt_current_total', 'debt_noncurrent', 'debt_current_maturities'):
            return None
        value = self.values.get(key)
        return float(value) if value is not None else None

    def annual_ends(self, item):
        return {date(year, 12, 31) for year in (self.year, self.year - 1)
                if self.annual(item, date(year, 12, 31)) is not None}

    def instant_ends(self, item):
        end = date(self.year, 12, 31)
        return {end} if self.instant(item, end) is not None else set()

    def latest_duration(self, item):
        return None


def annual_metrics(annual):
    from ..qgv import v2_factors as factors
    if annual.get('state') != 'LIVE' or not isinstance(annual.get('bsns_year'), int):
        return dict.fromkeys(factors.METRIC_KEYS)
    lines = _AnnualLines(annual, factors)
    return factors.compute_reported_periods(lines, fiscal_year_end=date(lines.year, 12, 31),
                                           currency='KRW', taxonomy='DART')[3]


def reference_score(company, universe):
    from ..qgv.v2_scoring import score_rows
    state = company.get('state') if company.get('state') in ('LIVE', 'STALE') else 'NOT_AVAILABLE'
    row = {'cik': None, 'state': state, 'profile': 'GENERAL', 'industry_group': None,
           'metrics': annual_metrics(company.get('annual', {}))}
    scores, summary = score_rows(universe, {'hanmi': row})
    return {'comparison_label': '참고 순위', 'comparison_basis': 'US_UNIVERSE_504_GENERAL',
            'reference_only': True, 'industry_basis': 'NOT_ASSIGNED',
            'cross_section_size': summary['cross_section_size'], **scores[('target', 'hanmi')]}


def metric_projection(company):
    state = company.get('state') if company.get('state') in ('LIVE', 'STALE') else 'NOT_AVAILABLE'
    return {'state': state, 'reference_only': True, 'comparison_label': '참고 순위',
            'comparison_basis': 'US_UNIVERSE_504_GENERAL', 'industry_basis': 'NOT_ASSIGNED',
            'currency': 'KRW', 'metrics': annual_metrics(company.get('annual', {}))}
