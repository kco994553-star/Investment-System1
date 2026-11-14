"""Frozen, incomplete mapping of official FINANCIAL raw metrics into 555 roles.

This module supplies definitions, validation and contribution disclosure only.
It neither copies official scores nor chooses peers or calculates percentiles.
The research engine retains its existing minimum-eight and 50%-axis kernels.
"""
from collections import defaultdict
from fractions import Fraction
import math

from ..qgv import v2_factors as vf
from ..qgv.qgv_v2 import WEIGHTS
from ..qgv.v2_scoring import SUBMETRICS, MIN_PEERS, AXIS_COVERAGE_MIN


VERSION = 'financial-555-temporary-official/0.1.0'
STATUS = 'TEMPORARY_OFFICIAL_FINANCIAL'
CALC_VERSION = 'qgv2-calc/2026-10-23.1'
NAMESPACE = 'financial::'
HISTORICAL_SHARE_METRICS = frozenset((
    'eps_cagr_3y', 'dilution_3y', 'book_value_per_share_cagr_3y'))

# Fixed before measuring coverage; a source metric can occupy only one role.
_MAPPING = {
    'q_profitability': (('roe', 1), ('roa', 1), ('net_interest_income_to_assets', 1)),
    'q_moat_proxy': (('moat_proxy', 1),),
    'q_earnings_quality': (),
    'q_financial_safety': (('equity_to_assets', 1),),
    'q_capital_allocation': (('dilution_3y', -1), ('incremental_roe_5y', 1)),
    'g_revenue_growth': (('revenue_cagr_3y', 1),),
    'g_per_share_growth': (('eps_cagr_3y', 1), ('book_value_per_share_cagr_3y', 1)),
    'g_growth_efficiency': (('incremental_roe_3y', 1),),
    'g_consistency': (('revenue_positive_growth_share', 1), ('revenue_growth_volatility', -1)),
    'g_recent_acceleration': (('revenue_acceleration', 1),),
    'v_earnings_yield': (), 'v_fcf_yield': (), 'v_vs_industry': (),
    'v_vs_own_history': (), 'v_expectation_check': (),
}

_QUESTIONS = {
    'q_profitability': '현재 이익과 자본·자산·이자수익 기반의 수익성은 어떤가',
    'q_moat_proxy': 'ROE의 수준과 지속성이 여러 회계기간에 걸쳐 유지되는가',
    'q_earnings_quality': '보고이익의 현금·추정·위험 인식 근거가 적절한가',
    'q_financial_safety': '장부 자본 완충력은 어느 정도인가',
    'q_capital_allocation': '주식수 변화와 장기 추가 자기자본 수익은 어떤가',
    'g_revenue_growth': '공식 정의의 수익 기반이 얼마나 성장했는가',
    'g_per_share_growth': '공식 희석 EPS와 장부자본/희석주식수가 성장했는가',
    'g_growth_efficiency': '최근 추가 자기자본 대비 추가 이익은 얼마인가',
    'g_consistency': '연간 수익 증가의 빈도와 변동성은 어떤가',
    'g_recent_acceleration': '최근 TTM 수익 성장과 3년 FY 성장의 차이는 무엇인가',
    'v_earnings_yield': '가격 대비 적격 금융 이익은 얼마인가',
    'v_fcf_yield': '가격 대비 주주 귀속 현금흐름은 얼마인가',
    'v_vs_industry': '동일 회계모형의 동종기업 대비 가격은 어떤가',
    'v_vs_own_history': '동일 기준의 자기 과거 가치 대비 가격은 어떤가',
    'v_expectation_check': '가격이 요구하는 성장과 적격 실적의 차이는 무엇인가',
}

# (exact official expression, fiscal period, shared input family, attribution)
_DEFINITIONS = {
    'roe': ('FY net_income / avg_pair(equity_FY0, equity_FY-1); closing>0, opening>0 if present',
        'FY', 'financial_return_level', 'OFFICIAL_NET_INCOME_OVER_OFFICIAL_EQUITY'),
    'roa': ('FY net_income / avg_pair(assets_FY0, assets_FY-1); denominator>0',
        'FY', 'financial_return_level', 'OFFICIAL_NET_INCOME_OVER_TOTAL_ASSETS'),
    'net_interest_income_to_assets': ('FY net_interest_income / avg_pair(assets_FY0, assets_FY-1); denominator>0',
        'FY', 'financial_return_level', 'OFFICIAL_NET_INTEREST_INCOME_OVER_TOTAL_ASSETS'),
    'moat_proxy': ('ROE FY0..FY-4, min3 available: mu * max(0, 1-population_std/mu) if mu>0 else mu',
        'FY_5Y_MIN3', 'financial_return_level', 'OFFICIAL_ROE_HISTORY'),
    'equity_to_assets': ('equity_FY0 / assets_FY0; assets>0',
        'FY_END', 'financial_equity', 'OFFICIAL_EQUITY_NOT_REGULATORY_OR_CONFIRMED_COMMON'),
    'dilution_3y': ('(shares_FY0 / shares_FY-3)^(1/3)-1; positive endpoints, official FY0 share basis',
        'FY_3Y_ENDPOINTS', 'financial_share_basis', 'WEIGHTED_AVERAGE_DILUTED_SHARES_NOT_ACTUAL_ISSUANCE'),
    'incremental_roe_5y': ('(net_income_FY0-net_income_FY-5)/(equity_FY0-equity_FY-5); delta_equity>0',
        'FY_5Y_ENDPOINTS', 'financial_incremental_return', 'OFFICIAL_NET_INCOME_OVER_CHANGE_IN_OFFICIAL_EQUITY'),
    'revenue_cagr_3y': ('(revenue_FY0/revenue_FY-3)^(1/3)-1; positive endpoints',
        'FY_3Y_ENDPOINTS', 'financial_revenue_growth', 'OFFICIAL_REVENUE_CONCEPT_PRIORITY'),
    'eps_cagr_3y': ('(reported_diluted_EPS_FY0/reported_diluted_EPS_FY-3)^(1/3)-1; positive endpoints, official FY0 share basis',
        'FY_3Y_ENDPOINTS', 'financial_earnings_growth', 'REPORTED_DILUTED_EPS_NOT_NET_INCOME_DIVIDED_BY_SHARES'),
    'book_value_per_share_cagr_3y': ('((equity_FY0/shares_FY0)/(equity_FY-3/shares_FY-3))^(1/3)-1; positive equity and share endpoints, official FY0 share basis',
        'FY_3Y_ENDPOINTS', 'financial_equity', 'OFFICIAL_EQUITY_OVER_WEIGHTED_AVERAGE_DILUTED_SHARES_NOT_CONFIRMED_COMMON_BPS'),
    'incremental_roe_3y': ('(net_income_FY0-net_income_FY-3)/(equity_FY0-equity_FY-3); delta_equity>0',
        'FY_3Y_ENDPOINTS', 'financial_incremental_return', 'OFFICIAL_NET_INCOME_OVER_CHANGE_IN_OFFICIAL_EQUITY'),
    'revenue_positive_growth_share': ('count(g>0)/count(g), g=revenue_FY-k/revenue_FY-k-1-1, k=0..4, old>0, min3 available',
        'FY_5Y_CHANGES_MIN3', 'financial_revenue_growth', 'OFFICIAL_REVENUE_CONCEPT_PRIORITY'),
    'revenue_growth_volatility': ('population_std(g), g=revenue_FY-k/revenue_FY-k-1-1, k=0..4, old>0, min3 available',
        'FY_5Y_CHANGES_MIN3', 'financial_revenue_growth', 'OFFICIAL_REVENUE_CONCEPT_PRIORITY'),
    'revenue_acceleration': ('(TTM_revenue/prior_TTM_revenue-1)-revenue_cagr_3y; prior_TTM>0 and FY CAGR available',
        'TTM_AND_FY_3Y', 'financial_revenue_growth', 'OFFICIAL_REVENUE_CONCEPT_PRIORITY'),
}

_SHARED_INPUTS = {
    'roe': ('financial_net_income', 'financial_equity'),
    'roa': ('financial_net_income', 'financial_assets'),
    'net_interest_income_to_assets': ('financial_net_interest_income', 'financial_assets'),
    'moat_proxy': ('financial_net_income', 'financial_equity'),
    'equity_to_assets': ('financial_equity', 'financial_assets'),
    'dilution_3y': ('financial_share_basis',),
    'incremental_roe_5y': ('financial_net_income', 'financial_equity'),
    'revenue_cagr_3y': ('financial_revenue_growth',),
    'eps_cagr_3y': ('financial_reported_eps', 'financial_share_basis'),
    'book_value_per_share_cagr_3y': ('financial_equity', 'financial_share_basis'),
    'incremental_roe_3y': ('financial_net_income', 'financial_equity'),
    'revenue_positive_growth_share': ('financial_revenue_growth',),
    'revenue_growth_volatility': ('financial_revenue_growth',),
    'revenue_acceleration': ('financial_revenue_growth',),
}


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _required_inputs(metric):
    """Official source primitives, including conditional balance/YTD inputs.

    These are definition metadata, never observations or presence assertions.
    Historical filing routes remain in required_evidence, separate from values.
    """
    def field(name, period, accessor, *, required=True, condition='REQUIRED_FOR_FORMULA'):
        return dict(field=name, period=period, accessor=accessor,
            required=required, condition=condition)

    def average_return(numerator, denominator, k=0, *, sample=False):
        period = 'FY0' if k == 0 else f'FY-{k}'
        sample_condition = 'MINIMUM_3_OF_5_VALID_ROE_SAMPLES' if sample else 'REQUIRED_FOR_FORMULA'
        return [field(numerator, period, 'a', required=not sample, condition=sample_condition),
            field(denominator, period, 'i', required=not sample, condition=sample_condition),
            field(denominator, f'FY-{k+1}', 'i', required=False,
                condition='OPTIONAL_OPENING_BALANCE_CLOSING_ONLY_FALLBACK_IF_MISSING')]

    if metric == 'roe':
        return average_return('net_income', 'equity')
    if metric in ('roa', 'net_interest_income_to_assets'):
        return average_return('net_income' if metric == 'roa' else 'net_interest_income', 'total_assets')
    if metric == 'moat_proxy':
        return [p for k in range(5) for p in average_return('net_income', 'equity', k, sample=True)]
    if metric == 'equity_to_assets':
        return [field('equity', 'FY0', 'i'), field('total_assets', 'FY0', 'i')]
    if metric.startswith('incremental_roe_'):
        years = 5 if metric.endswith('5y') else 3
        return [field(name, period, accessor) for name, accessor in (('net_income', 'a'), ('equity', 'i'))
            for period in ('FY0', f'FY-{years}')]
    if metric == 'dilution_3y':
        return [field('diluted_shares', period, 'shares') for period in ('FY0', 'FY-3')]
    if metric == 'eps_cagr_3y':
        return [field('eps_diluted', period, 'eps') for period in ('FY0', 'FY-3')] + [
            field('diluted_shares', period, 'shares', required=False,
                condition='WHEN_REPORTED_OFFICIAL_BASIS_OR_HISTORICAL_SHARE_JUMP_VALIDATION')
            for period in ('FY0', 'FY-3')]
    if metric == 'book_value_per_share_cagr_3y':
        return [field(name, period, accessor) for name, accessor in (('equity', 'i'), ('diluted_shares', 'shares'))
            for period in ('FY0', 'FY-3')]
    if metric == 'revenue_cagr_3y':
        return [field('revenue', period, 'a') for period in ('FY0', 'FY-3')]
    if metric in ('revenue_positive_growth_share', 'revenue_growth_volatility'):
        return [field('revenue', 'FY0' if k == 0 else f'FY-{k}', 'a', required=False,
            condition='MINIMUM_3_OF_5_VALID_ADJACENT_YOY_PAIRS_PRIOR_REVENUE_POSITIVE') for k in range(6)]
    if metric == 'revenue_acceleration':
        return [field('revenue', period, 'a/ttm') for period in ('FY0', 'FY-1', 'FY-3')] + [
            field('revenue', period, 'ytd', required=False,
                condition='REQUIRED_FOR_SAME_CONCEPT_YTD_TTM_ROUTE_ELSE_FY0_FY_MINUS1_FALLBACK')
            for period in ('YTD_CURRENT', 'YTD_PRIOR_YEAR', 'YTD_TWO_YEARS_AGO')]
    raise ValueError('FINANCIAL_UNKNOWN_METRIC')


def _official_definition_guard():
    if vf.CALC_VERSION != CALC_VERSION or SUBMETRICS['FINANCIAL'] != {
            r: m for r, m in _MAPPING.items() if r.startswith(('q_', 'g_'))}:
        raise ValueError('OFFICIAL_FINANCIAL_DEFINITION_CHANGED')


def financial_catalog():
    """Return isolated catalog metadata; values remain official FY definitions."""
    _official_definition_guard()
    out = {}
    for role, metrics in _MAPPING.items():
        for metric, direction in metrics:
            formula, period, family, attribution = _DEFINITIONS[metric]
            key = NAMESPACE + metric
            out[key] = dict(canonical_id=key, source_metric=metric,
                variant=f'{metric}/financial-official-calc23.1-1', display_name=metric,
                aliases=[], formula=formula, period=period, unit='decimal', direction=direction,
                axis=role[0].upper(), roles=[role], accounting_scope=['FINANCIAL'],
                formula_application_profile='FINANCIAL', peer_accounting_model_policy='RETAIN_CONFIRMED_MODEL',
                input_family=family, attribution=attribution, common_attribution_confirmed=False,
                shared_input_families=list(_SHARED_INPUTS[metric]),
                formula_source=('v2_factors._growth_common' if role.startswith('g_') and
                    metric not in ('incremental_roe_3y', 'book_value_per_share_cagr_3y') or
                    metric == 'dilution_3y' else 'v2_factors._metrics_financial'),
                source_formula_version=CALC_VERSION, source='OFFICIAL_FINANCIAL_RAW_DEFINITION',
                implementation_status='EXISTING_KERNEL', availability='PER_INPUT',
                validation='REQUIRES_SOURCE_BOUND_EVIDENCE', default=False, temporary_status=STATUS,
                historical_share_evidence_required=metric in HISTORICAL_SHARE_METRICS,
                denominator_definition=('WEIGHTED_AVERAGE_DILUTED_SHARES' if
                    metric in HISTORICAL_SHARE_METRICS else None),
                numerator_definition=('OFFICIAL_EQUITY_NOT_CONFIRMED_COMMON' if
                    metric == 'book_value_per_share_cagr_3y' else
                    'REPORTED_DILUTED_EPS' if metric == 'eps_cagr_3y' else
                    'WEIGHTED_AVERAGE_DILUTED_SHARE_COUNT' if metric == 'dilution_3y' else None),
                historical_share_periods=['FY0', 'FY-3'] if metric in HISTORICAL_SHARE_METRICS else [],
                historical_share_validation=('METRIC_SPECIFIC_OFFICIAL_BASIS_REQUIRED' if
                    metric in HISTORICAL_SHARE_METRICS else None),
                required_evidence=(['OFFICIAL_SOURCE_RECORD', 'FY0_AND_FY_MINUS_3_SHARE_FILINGS',
                    'OFFICIAL_SHARE_BASIS_ROUTE', 'EQUITY_ENDPOINT_SOURCE_PERIODS'] if
                    metric == 'book_value_per_share_cagr_3y' else
                    ['OFFICIAL_SOURCE_RECORD', 'FY0_AND_FY_MINUS_3_SHARE_FILINGS', 'OFFICIAL_SHARE_BASIS_ROUTE'] if
                    metric in HISTORICAL_SHARE_METRICS else ['OFFICIAL_SOURCE_RECORD']),
                required_inputs=_required_inputs(metric),
                opening_balance_policy='CLOSING_ONLY_IF_OPENING_MISSING' if metric in
                    ('roe', 'roa', 'net_interest_income_to_assets', 'moat_proxy') else None,
                recommendation='TEMPORARY_RESEARCH_NOT_FINANCIAL_MODEL_COMPLETION')
    return out


def financial_role_recipes():
    """Keep all 15 budgets, including six explicitly unsupported empty roles."""
    cats = financial_catalog()
    out = {}
    for axis, weights in WEIGHTS.items():
        for role, weight in weights.items():
            keys = [NAMESPACE + metric for metric, _ in _MAPPING[role]]
            out[role] = dict(axis=axis, weight=weight, metrics={key: 1 for key in keys},
                economic_question=_QUESTIONS[role], temporary_status=STATUS,
                definition_status='OFFICIAL_RAW_RECIPE' if keys else 'NOT_DEFINED',
                null_reason=None if keys else 'FINANCIAL_CASHFLOW_QUALITY_NOT_DEFINED' if
                    role == 'q_earnings_quality' else 'FINANCIAL_PROFILE_V_NOT_DEFINED',
                measurement='PROXY' if keys else 'NOT_DEFINED',
                overlap_families=sorted({cats[key]['input_family'] for key in keys}))
    validate_role_recipes(out)
    return out


def validate_role_recipes(recipes):
    """Reject reassignment, duplicated source metrics and changed 555 budgets."""
    _official_definition_guard()
    expected = {r: (a, w) for a, rs in WEIGHTS.items() for r, w in rs.items()}
    if set(recipes) != set(expected):
        raise ValueError('FINANCIAL_ROLE_IDS')
    cats = financial_catalog()
    seen = set()
    for role, spec in recipes.items():
        if (spec.get('axis'), spec.get('weight')) != expected[role]:
            raise ValueError('FINANCIAL_ROLE_BUDGET')
        metrics = spec.get('metrics')
        if not isinstance(metrics, dict):
            raise ValueError('FINANCIAL_ROLE_METRICS')
        for key, weight in metrics.items():
            if key not in cats:
                raise ValueError('FINANCIAL_UNKNOWN_METRIC')
            metric = cats[key]['source_metric']
            if metric in seen:
                raise ValueError('FINANCIAL_DUPLICATE_SOURCE_METRIC')
            seen.add(metric)
            if not _finite(weight) or weight <= 0:
                raise ValueError('FINANCIAL_SUBMETRIC_WEIGHT')
    for role, spec in recipes.items():
        if spec['metrics'] != {NAMESPACE + m: 1 for m, _ in _MAPPING[role]}:
            raise ValueError('FINANCIAL_FROZEN_ROLE_MAPPING')
        expected_reason = (None if _MAPPING[role] else 'FINANCIAL_CASHFLOW_QUALITY_NOT_DEFINED' if
            role == 'q_earnings_quality' else 'FINANCIAL_PROFILE_V_NOT_DEFINED')
        if spec.get('null_reason') != expected_reason:
            raise ValueError('FINANCIAL_UNDEFINED_ROLE_REASON')
    return recipes


def validate_official_financial_record(record):
    """Validate source scope only; this does not approve historical share basis.

    Source binding, time, issuer, publication evidence and individual share
    routes remain the input adapter's responsibility. No score field is read.
    """
    _official_definition_guard()
    if record.get('calc_version') != CALC_VERSION:
        raise ValueError('FINANCIAL_SOURCE_CALC_VERSION')
    if record.get('profile') != 'FINANCIAL':
        raise ValueError('FINANCIAL_SOURCE_PROFILE')
    if record.get('state') not in ('LIVE', 'STALE'):
        raise ValueError('FINANCIAL_SOURCE_STATE')
    metrics = record.get('metrics')
    if not isinstance(metrics, dict):
        raise ValueError('FINANCIAL_SOURCE_METRICS')
    for metric in _DEFINITIONS:
        if metrics.get(metric) is not None and not _finite(metrics[metric]):
            raise ValueError('FINANCIAL_SOURCE_NONFINITE_METRIC:' + metric)
    return dict(valid=True, formula_application_profile='FINANCIAL', temporary_status=STATUS,
        historical_share_basis_validated=False, peer_accounting_model_inferred=False,
        official_scores_read=False, supported_metrics=sum(metrics.get(m) is not None for m in _DEFINITIONS))


def contribution_metadata(roles, *, axis_weights=None, included_axes=(), total_available=False):
    """Disclose nominal/effective exposure from recomputed 555 result roles.

    `roles` uses the engine's score/metrics output; this function never creates
    role or axis scores. Effective total contributions are zero without a total.
    """
    recipes = financial_role_recipes()
    cats = financial_catalog()
    if type(total_available) is not bool:
        raise ValueError('FINANCIAL_TOTAL_AVAILABILITY')
    axis_weights = dict(Q=34, G=33, V=33) if axis_weights is None else dict(axis_weights)
    if set(axis_weights) != set('QGV') or any(not _finite(w) or w < 0 for w in axis_weights.values()) or sum(axis_weights.values()) <= 0:
        raise ValueError('FINANCIAL_AXIS_WEIGHTS')
    if set(roles) != set(recipes):
        raise ValueError('FINANCIAL_RESULT_ROLE_IDS')
    if len(set(included_axes)) != len(included_axes) or not set(included_axes) <= set('QGV'):
        raise ValueError('FINANCIAL_INCLUDED_AXES')
    role_scores, by_role = {}, {}
    for role, result in roles.items():
        score = result.get('score')
        if score is not None and (not _finite(score) or not 0 <= score <= 100):
            raise ValueError('FINANCIAL_RESULT_SCORE')
        items = result.get('metrics', [])
        if len(items) != len(recipes[role]['metrics']) or {i['metric'] for i in items} != set(recipes[role]['metrics']):
            raise ValueError('FINANCIAL_RESULT_METRICS')
        for item in items:
            if item.get('weight') != recipes[role]['metrics'][item['metric']]:
                raise ValueError('FINANCIAL_RESULT_METRIC_WEIGHT')
            if item.get('score') is not None and (not _finite(item['score']) or not 0 <= item['score'] <= 100):
                raise ValueError('FINANCIAL_RESULT_SCORE')
        has_scores = any(i.get('score') is not None for i in items)
        if (score is not None) != has_scores:
            raise ValueError('FINANCIAL_RESULT_ROLE_AVAILABILITY')
        role_scores[role], by_role[role] = score, items
    coverage = {a: sum(spec['weight'] for r, spec in recipes.items()
        if spec['axis'] == a and role_scores[r] is not None) for a in 'QGV'}
    available = {a for a in 'QGV' if coverage[a] >= AXIS_COVERAGE_MIN}
    if not set(included_axes) <= available or total_available and (not included_axes or
            set(included_axes) != available or
            sum(axis_weights[a] for a in included_axes) <= 0 or
            sum(axis_weights[a] for a in available) < .5 * sum(axis_weights.values())):
        raise ValueError('FINANCIAL_EFFECTIVE_AXIS_COVERAGE')
    families = defaultdict(lambda: dict(nominal=0., effective=0., roles=set()))
    shared = defaultdict(lambda: dict(nominal=0., effective=0., roles=set()))
    lineage, role_contributions = [], {}
    for role, spec in recipes.items():
        axis, weight = spec['axis'], spec['weight']
        nominal = Fraction(str(axis_weights[axis])) / Fraction(str(sum(axis_weights.values()))) * Fraction(weight, 100)
        axis_effective = weight / coverage[axis] if axis in available and role_scores[role] is not None else 0.
        effective = axis_weights[axis] / sum(axis_weights[a] for a in included_axes) * axis_effective if (
            total_available and axis in included_axes) else 0.
        role_contributions[role] = dict(axis=axis, nominal=float(nominal),
            nominal_ratio=[nominal.numerator, nominal.denominator], effective=effective,
            within_axis_nominal=weight / 100, within_axis_effective=axis_effective,
            null_reason=spec['null_reason'])
        items = by_role[role]
        used = sum(i['weight'] for i in items if i.get('score') is not None)
        for item in items:
            metric = item['metric']
            metric_nominal = nominal * Fraction(str(item['weight'])) / Fraction(str(sum(i['weight'] for i in items)))
            metric_effective = effective * item['weight'] / used if item.get('score') is not None and used else 0.
            family = cats[metric]['input_family']
            lineage.append(dict(axis=axis, role=role, metric=metric, source_metric=cats[metric]['source_metric'],
                input_family=family, nominal=float(metric_nominal),
                nominal_ratio=[metric_nominal.numerator, metric_nominal.denominator], effective=metric_effective))
            families[family]['nominal'] += float(metric_nominal)
            families[family]['effective'] += metric_effective
            families[family]['roles'].add(role)
            for common_family in cats[metric]['shared_input_families']:
                shared[common_family]['nominal'] += float(metric_nominal)
                shared[common_family]['effective'] += metric_effective
                shared[common_family]['roles'].add(role)
    disclosures = [dict(input_family=family, roles=sorted(node['roles']),
        reason='RELATED_INPUT_FAMILY_DISTINCT_RAW_METRICS_NOT_INDEPENDENT_SIGNALS')
        for family, node in families.items() if len(node['roles']) > 1]
    return dict(temporary_status=STATUS, official=False, financial_model_complete=False,
        score_origin_required='RESEARCH_RECOMPUTED_RAW_PERCENTILES', minimum_peers=MIN_PEERS,
        minimum_axis_available_weight=AXIS_COVERAGE_MIN, axis_available_weight=coverage,
        role_contributions=role_contributions, lineage=lineage,
        input_family_contributions={f: dict(nominal=n['nominal'], effective=n['effective']) for f, n in families.items()},
        family_overlap_disclosures=disclosures, duplicate_source_metric_count=0,
        shared_input_exposures={f: dict(nominal=n['nominal'], effective=n['effective'], roles=sorted(n['roles']))
            for f, n in shared.items()}, shared_input_exposures_additive=False,
        unmapped_nominal=sum(r['nominal'] for r in role_contributions.values() if r['null_reason']),
        effective_total_available=bool(total_available))
