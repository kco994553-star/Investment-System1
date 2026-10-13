"""DART annual lines through the same v2 ratio/scoring functions; reference targets only.

The optional history collector supplies up to six actual fiscal reports and exact
standard account IDs. Old one-report projections remain readable; absent periods
and lines stay missing. KRW amounts are never compared with USD amounts: only
the v2 dimensionless metrics enter the US distribution, and the Korean issuer never
becomes a point in that distribution. No SIC code is guessed for a Korean issuer.
"""
from datetime import date


class _AnnualLines:
    """The period-read interface consumed by qgv.v2_factors._Company."""
    def __init__(self, annual, factor_module, history=()):
        self.values = annual['inputs']
        self.year = int(annual['bsns_year'])
        basis = annual.get('fs_div')
        self.reports = {int(r['bsns_year']): r for r in (*history, annual) if r.get('state') == 'LIVE' and r.get('fs_div') == basis}
        self.items = {key: [] for key in factor_module.FLOW_ITEMS}

    def annual(self, item, end, tables=None):
        aliases = {'ebit': 'operating_income', 'capital_expenditure': 'capex'}
        key = aliases.get(item, item)
        if end.month != 12 or end.day != 31:
            return None
        report = self.reports.get(end.year)
        if report is not None:
            values = report.get('v2_inputs', {}).get('inputs') or report['inputs']
            if 'v2_inputs' not in report:
                key = {'eps_diluted': 'eps', 'diluted_shares': None}.get(item, key)
            value = values.get(key)
        elif end.year == self.year - 1:
            key = {'revenue': 'revenue_prev', 'eps_diluted': 'eps_prev', 'ebit': 'operating_income_prev'}.get(item)
            value = self.values.get(key)
        else:
            return None
        if value is None:
            return None
        if item == 'capital_expenditure':
            value = abs(value)
        return float(value), date(end.year, 1, 1), end

    def instant(self, item, end, tolerance=None):
        if end.month != 12 or end.day != 31 or end.year not in self.reports:
            return None
        key = {'debt_total_long_term': 'total_debt'}.get(item, item)
        # total_debt already comprises short+long+bonds+leases: never add it a second time.
        if item in ('debt_short_term', 'debt_current_total', 'debt_noncurrent', 'debt_current_maturities'):
            return None
        report = self.reports[end.year]
        values = report.get('v2_inputs', {}).get('inputs') or report['inputs']
        value = values.get(key)
        return float(value) if value is not None else None

    def annual_ends(self, item):
        return {date(year, 12, 31) for year in (*self.reports, self.year - 1)
                if self.annual(item, date(year, 12, 31)) is not None}

    def instant_ends(self, item):
        return {date(year, 12, 31) for year in self.reports if self.instant(item, date(year, 12, 31)) is not None}

    def latest_duration(self, item):
        for year in sorted(self.reports, reverse=True):
            hit = self.annual(item, date(year, 12, 31))
            if hit is not None:
                return hit[0], hit[2]
        return None


def annual_metrics(annual, history=()):
    from ..qgv import v2_factors as factors
    if annual.get('state') != 'LIVE' or not str(annual.get('bsns_year', '')).isdigit():
        return dict.fromkeys(factors.METRIC_KEYS)
    lines = _AnnualLines(annual, factors, history)
    return factors.compute_reported_periods(lines, fiscal_year_end=date(lines.year, 12, 31),
                                           currency='KRW', taxonomy='DART')[3]


def reference_score(company, universe):
    from ..qgv.v2_scoring import score_rows
    state = company.get('state') if company.get('state') in ('LIVE', 'STALE') else 'NOT_AVAILABLE'
    row = {'cik': None, 'state': state, 'profile': 'GENERAL', 'industry_group': None,
           'metrics': annual_metrics(company.get('annual', {}), company.get('annual_history', ()))}
    scores, summary = score_rows(universe, {'hanmi': row})
    return {'comparison_label': '참고 순위', 'comparison_basis': 'US_UNIVERSE_504_GENERAL',
            'reference_only': True, 'industry_basis': 'NOT_ASSIGNED',
            'cross_section_size': summary['cross_section_size'], **scores[('target', 'hanmi')]}


def metric_projection(company):
    state = company.get('state') if company.get('state') in ('LIVE', 'STALE') else 'NOT_AVAILABLE'
    annual = company.get('annual', {})
    basis = annual.get('fs_div')
    history = [r for r in company.get('annual_history', ()) if r.get('state') == 'LIVE' and r.get('fs_div') == basis]
    inputs = annual.get('v2_inputs', {}).get('inputs', {})
    reasons = []
    if inputs.get('total_assets') is None:
        reasons.append('DART_V2_ASSETS_NOT_COLLECTED')
    if inputs.get('interest_expense') is None:
        reasons.append('DART_V2_INTEREST_NOT_COLLECTED')
    years = {int(r['bsns_year']) for r in history}
    fy = int(annual['bsns_year']) if str(annual.get('bsns_year', '')).isdigit() else None
    for length, code in ((4, 'DART_V2_3Y_HISTORY_NOT_COLLECTED'), (6, 'DART_V2_5Y_HISTORY_NOT_COLLECTED')):
        if fy is None or not set(range(fy-length+1, fy+1)) <= years:
            reasons.append(code)
    if any(r.get('fs_div') != basis for r in company.get('annual_history', ())):
        reasons.append('DART_V2_HISTORY_BASIS_MISMATCH')
    return {'state': state, 'reference_only': True, 'comparison_label': '참고 순위',
            'comparison_basis': 'US_UNIVERSE_504_GENERAL', 'industry_basis': 'NOT_ASSIGNED',
            'currency': 'KRW', 'reason_codes': reasons,
            'metrics': annual_metrics(annual, history)}
