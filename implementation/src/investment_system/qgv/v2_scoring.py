"""QGV v2 Q·G percentile scoring over the Universe504 cross-section. PROVISIONAL, UNCALIBRATED.

Default weights are the QGV_V2_CANDIDATE.md values exactly (user decision 2026-10-13, GSQ-022 pending
approval); they are not tuned on past returns and no Holdout data is used. v1 weights are unchanged.

Rules (shared by the builder and the strict Python/JS validators, so every score is reproducible from
the published raw metrics):
- cross-section = Universe504 rows in LIVE or STALE state, one point per issuer (CIK); every row (Universe
  or TARGET) is ranked with its own issuer's point replaced by its own values, so a TARGET row fresher
  than its Universe row is ranked exactly as if it were that issuer's point;
- FINANCIAL profile rows are ranked only among FINANCIAL rows (Q and G); GENERAL rows: Q within the
  same SIC industry group (sic_industry_groups/v0) when that group has >= MIN_PEERS issuers, otherwise
  the whole GENERAL universe; G across the whole GENERAL universe;
- sub-metric percentile = 100 * (less + (equal - 1) / 2) / (n - 1) over the peer values that exist
  (average rank for ties, 0..100), direction applied by negating lower-is-better values; a sub-metric
  needs >= MIN_PEERS values (own included), else it is NOT_AVAILABLE;
- factor score = mean of its available sub-metric percentiles (fixed order); NOT_AVAILABLE if none;
- axis score = weighted mean of available factor scores, weights renormalized over available factors;
  available weight < 50% of the axis -> axis NOT_AVAILABLE (AXIS_COVERAGE_BELOW_50). Never 0-filled.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right

Q_WEIGHTS_V2 = {'q_profitability': 25, 'q_moat_proxy': 20, 'q_earnings_quality': 20, 'q_financial_safety': 20,
                'q_capital_allocation': 15}
G_WEIGHTS_V2 = {'g_revenue_growth': 25, 'g_per_share_growth': 25, 'g_growth_efficiency': 20, 'g_consistency': 15,
                'g_recent_acceleration': 15}
AXES = {'Q': Q_WEIGHTS_V2, 'G': G_WEIGHTS_V2}
FACTOR_IDS = tuple(Q_WEIGHTS_V2) + tuple(G_WEIGHTS_V2)
MIN_PEERS = 8
AXIS_COVERAGE_MIN = 50
PEER_BASES = ('INDUSTRY_GROUP', 'UNIVERSE_FALLBACK', 'UNIVERSE', 'FINANCIAL_PROFILE')
AXIS_REASONS = ('ROW_NOT_AVAILABLE', 'PEERS_BELOW_MINIMUM', 'AXIS_COVERAGE_BELOW_50')
SCORED_STATES = ('LIVE', 'STALE')

# (metric, direction): +1 higher is better, -1 lower is better.
SUBMETRICS = {
    'GENERAL': {
        'q_profitability': (('roic', 1), ('gross_profit_to_assets', 1)),
        'q_moat_proxy': (('moat_proxy', 1),),
        'q_earnings_quality': (('accruals_to_assets', -1), ('fcf_to_net_income', 1)),
        'q_financial_safety': (('net_debt_to_ebitda', -1), ('interest_coverage', 1)),
        'q_capital_allocation': (('dilution_3y', -1), ('incremental_roic_5y', 1)),
        'g_revenue_growth': (('revenue_cagr_3y', 1),),
        'g_per_share_growth': (('eps_cagr_3y', 1), ('fcf_per_share_cagr_3y', 1)),
        'g_growth_efficiency': (('incremental_roic_3y', 1),),
        'g_consistency': (('revenue_positive_growth_share', 1), ('revenue_growth_volatility', -1)),
        'g_recent_acceleration': (('revenue_acceleration', 1),),
    },
    'FINANCIAL': {
        'q_profitability': (('roe', 1), ('roa', 1), ('net_interest_income_to_assets', 1)),
        'q_moat_proxy': (('moat_proxy', 1),),
        'q_earnings_quality': (),  # not defined for financials (operating cash flow mixes funding flows)
        'q_financial_safety': (('equity_to_assets', 1),),
        'q_capital_allocation': (('dilution_3y', -1), ('incremental_roe_5y', 1)),
        'g_revenue_growth': (('revenue_cagr_3y', 1),),
        'g_per_share_growth': (('eps_cagr_3y', 1), ('book_value_per_share_cagr_3y', 1)),
        'g_growth_efficiency': (('incremental_roe_3y', 1),),
        'g_consistency': (('revenue_positive_growth_share', 1), ('revenue_growth_volatility', -1)),
        'g_recent_acceleration': (('revenue_acceleration', 1),),
    },
}


def percentile(less, equal, n):
    """Average-rank percentile 0..100 (equal counts the row itself)."""
    return 100 * (less + (equal - 1) / 2) / (n - 1)


def _axis_of(fid):
    return 'Q' if fid in Q_WEIGHTS_V2 else 'G'


class _Pool:
    """Sorted metric values of one peer set (issuer points), with per-CIK lookup for exclusion."""

    def __init__(self, points):
        self.points = points  # {cik: metrics}
        self.size = len(points)
        self._sorted = {}

    def values(self, metric, direction):
        key = (metric, direction)
        if key not in self._sorted:
            self._sorted[key] = sorted(direction * m[metric] for m in self.points.values() if m.get(metric) is not None)
        return self._sorted[key]

    def rank(self, metric, direction, own, exclude_cik):
        """(less, equal, n) for `own` inserted into the pool after removing the row's own issuer point."""
        values = self.values(metric, direction)
        x = direction * own
        less, equal, n = bisect_left(values, x), bisect_right(values, x) - bisect_left(values, x), len(values)
        if exclude_cik in self.points:
            other = self.points[exclude_cik].get(metric)
            if other is not None:
                y = direction * other
                n -= 1
                if y < x:
                    less -= 1
                elif y == x:
                    equal -= 1
        return less, equal + 1, n + 1


def _empty_axis(reason):
    return {'score': None, 'factors_available': '0/5', 'available_weight': 0, 'peer_basis': None, 'peer_count': 0,
            'reason_codes': [reason]}


def score_rows(universe, target=None):
    """Score Universe rows and TARGET rows (inputs are not modified).

    `universe` / `target`: {key: row} with row keys cik, state, profile, industry_group, metrics.
    Returns (scores, summary) where scores[(role, key)] = {'factors': {...}, 'axes': {...}} and summary
    has cross_section_size and per-profile issuer counts. Universe issuer points are deduplicated by CIK
    (codes of one issuer carry identical rows)."""
    target = target or {}
    points = {}
    for key in sorted(universe):
        row = universe[key]
        if row['state'] in SCORED_STATES and row['cik'] is not None and row['cik'] not in points:
            points[row['cik']] = row
    by_profile = {p: {cik: r['metrics'] for cik, r in points.items() if r['profile'] == p} for p in ('GENERAL', 'FINANCIAL')}
    pools = {('profile', p): _Pool(m) for p, m in by_profile.items()}
    groups = {}
    for cik, r in points.items():
        if r['profile'] == 'GENERAL' and r['industry_group'] is not None:
            groups.setdefault(r['industry_group'], {})[cik] = r['metrics']
    for group, members in groups.items():
        pools[('group', group)] = _Pool(members)
    scores = {}
    for role, rows in (('universe', universe), ('target', target)):
        for key, row in rows.items():
            scores[(role, key)] = _score_row(row, pools)
    summary = {'cross_section_size': len(points),
               'cross_section_by_profile': {p: len(m) for p, m in by_profile.items()}}
    return scores, summary


def _peer_set(row, axis, pools):
    """(pool, basis, peer_count): peer_count counts the row itself once (its own issuer point is replaced)."""
    def count(pool):
        return pool.size - (1 if row['cik'] in pool.points else 0) + 1
    if row['profile'] == 'FINANCIAL':
        pool = pools[('profile', 'FINANCIAL')]
        return pool, 'FINANCIAL_PROFILE', count(pool)
    universe = pools[('profile', 'GENERAL')]
    if axis == 'Q':
        group = pools.get(('group', row['industry_group'])) if row['industry_group'] is not None else None
        if group is not None and count(group) >= MIN_PEERS:
            return group, 'INDUSTRY_GROUP', count(group)
        return universe, 'UNIVERSE_FALLBACK', count(universe)
    return universe, 'UNIVERSE', count(universe)


def _score_row(row, pools):
    factors = dict.fromkeys(FACTOR_IDS)
    axes = {}
    if row['state'] not in SCORED_STATES or row['profile'] is None:
        return {'factors': factors, 'axes': {axis: _empty_axis('ROW_NOT_AVAILABLE') for axis in AXES}}
    specs = SUBMETRICS[row['profile']]
    metrics = row['metrics']
    for axis, weights in AXES.items():
        pool, basis, peer_count = _peer_set(row, axis, pools)
        if peer_count < MIN_PEERS:
            axes[axis] = dict(_empty_axis('PEERS_BELOW_MINIMUM'), peer_basis=basis, peer_count=peer_count)
            continue
        for fid in weights:
            pcts = []
            for metric, direction in specs[fid]:
                own = metrics.get(metric)
                if own is None:
                    continue
                less, equal, n = pool.rank(metric, direction, own, row['cik'])
                if n >= MIN_PEERS:
                    pcts.append(percentile(less, equal, n))
            if pcts:
                factors[fid] = sum(pcts) / len(pcts)
        available = [fid for fid in weights if factors[fid] is not None]
        weight = sum(weights[fid] for fid in available)
        out = {'score': None, 'factors_available': f'{len(available)}/{len(weights)}', 'available_weight': weight,
               'peer_basis': basis, 'peer_count': peer_count, 'reason_codes': []}
        if weight * 100 < AXIS_COVERAGE_MIN * sum(weights.values()):
            out['reason_codes'] = ['AXIS_COVERAGE_BELOW_50']
        else:
            out['score'] = sum(weights[fid] * factors[fid] for fid in available) / weight
        axes[axis] = out
    return {'factors': factors, 'axes': axes}
