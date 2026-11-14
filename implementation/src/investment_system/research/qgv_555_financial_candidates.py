"""Incomplete, versioned financial 555 research recipes using existing kernels.

This registry is not a financial default or a score-producing model. A role with
an unresolved economic/input definition stays PREPARING; available raw ratios
do not fill its budget. No fetching, price reconstruction or official mutation.
"""
from copy import deepcopy

from .sector_qgv import VALID, calculate_factor, digest
from .sector_qgv_registry import CATALOG

VERSION = 'financial-555-candidates/0.1.0'
MINIMUM_PEERS = 8  # Existing 555 policy; never a prerequisite for raw ratios.
ROLE_WEIGHTS = {
    'Q': dict(q_profitability=25, q_moat_proxy=20, q_earnings_quality=20,
              q_financial_safety=20, q_capital_allocation=15),
    'G': dict(g_revenue_growth=25, g_per_share_growth=25, g_growth_efficiency=20,
              g_consistency=15, g_recent_acceleration=15),
    'V': dict(v_earnings_yield=25, v_fcf_yield=25, v_vs_industry=20,
              v_vs_own_history=15, v_expectation_check=15),
}
QUESTIONS = {
    'q_profitability': '현재 자본 또는 영업기반에서 얼마의 이익을 얻는가',
    'q_moat_proxy': '수익성이 여러 회계기간에 걸쳐 유지되는가',
    'q_earnings_quality': '보고이익의 현금·추정·위험 인식 근거가 적절한가',
    'q_financial_safety': '사업모형에 맞는 자본·유동성 완충력이 있는가',
    'q_capital_allocation': '주주 자본을 어떻게 배분하고 보전하는가',
    'g_revenue_growth': '일관된 사업 수익기반이 얼마나 성장했는가',
    'g_per_share_growth': '동일 보통주 기준의 주당 성과가 성장했는가',
    'g_growth_efficiency': '성장과 함께 수익 창출 효율이 개선됐는가',
    'g_consistency': '성장이 기간별로 얼마나 일관됐는가',
    'g_recent_acceleration': '최근 성장과 장기 성장의 차이는 무엇인가',
    'v_earnings_yield': '가격 대비 적격 회계이익 또는 사업모형 이익은 얼마인가',
    'v_fcf_yield': '가격 대비 주주에게 귀속될 현금흐름은 얼마인가',
    'v_vs_industry': '동일 정의·회계모형의 동종기업 대비 가격은 어떤가',
    'v_vs_own_history': '동일 기준의 자기 과거 가치 대비 현재 가격은 어떤가',
    'v_expectation_check': '가격이 요구하는 성장과 적격 실적의 차이는 무엇인가',
}
TEMPLATES = {
    'BANK': 'BANK', 'LIFE_INSURANCE': 'INSURANCE',
    'PROPERTY_CASUALTY_INSURANCE': 'INSURANCE', 'OTHER_INSURANCE': 'INSURANCE',
    'INSURANCE_UNSPECIFIED': 'INSURANCE', 'BROKER': 'BROKER',
    'ASSET_MANAGER': 'ASSET_MANAGER', 'MORTGAGE_REIT': 'MORTGAGE_REIT',
    'EQUITY_REIT': 'EQUITY_REIT',
}
_COMMON_LIMIT = ('보통주 귀속 이익·자본만 사용. 총자본 또는 연결 순이익으로 대체하지 않음. '
                 '주당 자료는 동일 종류주·기간·기업행사 검증을 별도로 요구.')
_PENDING = {
    'q_moat_proxy': '모형별 수익성 역사·손실 처리·지속성 산식 미완결',
    'q_earnings_quality': '모형별 충당·준비금·현금흐름 의미와 이익의 질 산식 미완결',
    'q_capital_allocation': '보통주 배당·실제 매입·자본 유지·희석 기준과 평가 산식 미완결',
    'g_revenue_growth': '모형별 순이자·보험료·수수료·투자 수익의 동일 정의 연결 필요',
    'g_per_share_growth': '동일 보통주 분모·기간 연결과 모형별 주당 성과 정의 필요',
    'g_consistency': '모형별 성장 수익기반과 전체 비교기간 정의 필요',
    'g_recent_acceleration': '모형별 TTM/FY 성장 수익기반의 동일 정의 연결 필요',
    'v_fcf_yield': '금융 CFO를 배당가능 현금흐름으로 간주하지 않음; 모형별 정의 미완결',
    'v_vs_own_history': '같은 증권·분할 기준·지표 정의의 적격 가격 역사 필요',
    'v_expectation_check': '모형별 주주 현금흐름·자본 요구·성장 기대 산식 미완결',
}


def _pending(role):
    axis = role[0].upper()
    return dict(role_id=role, axis=axis, question=QUESTIONS[role], weight=ROLE_WEIGHTS[axis][role],
        definition_status='PREPARING', evidence_status='PREPARING', basic_variant=None,
        user_candidates=[], formula=None, period=None, unit=None, direction=None,
        required_inputs=[], attribution_scope=None, overlap_groups=[],
        reason=_PENDING.get(role, '모형별 정확한 산식·귀속·입력 계약 미완결'),
        missing_policy='NULL_WITH_REASON_NO_SUBSTITUTION', peer_minimum=MINIMUM_PEERS,
        evidence_refs=['owner:financial-555-draft-20261114'],
        initial_weight_basis='EXISTING_555_ROLE_BUDGET_NOT_EMPIRICAL_OPTIMUM')


def _defined(role, variant, *, proxy=False, candidates=(), limitation='', overlap=()):
    f = CATALOG[variant]
    out = _pending(role)
    out.update(definition_status='FORMULA_DEFINED', evidence_status='PROXY' if proxy else 'DIRECT',
        basic_variant=variant, user_candidates=list(candidates), formula=f['formula'],
        period=f['period'], unit=f['unit'], direction=f['direction'],
        required_inputs=deepcopy(f['inputs']),
        attribution_scope=(_COMMON_LIMIT if variant in ('roe_common_ttm', 'common_equity_assets',
            'common_bps_cagr_3y', 'common_bp', 'tangible_common_bp') else
            '검증된 보통주 귀속 희석 EPS와 같은 종류주 가격' if variant.startswith('ep_') else
            '보고 Nareit FFO의 보통주 귀속·조정표와 대응 시가총액' if variant == 'nareit_ffo_mcap' else
            '동일 발행사 연결 범위의 명시된 수익·자산·현금흐름; 보통주 지표로 바꾸지 않음'),
        overlap_groups=list(overlap or (f['overlap_group'],)),
        limitation=limitation, reason=None,
        formula_evidence='EXISTING_SYSTEM_DEFINITION_NOT_CLAIM_OF_PERFORMANCE',
        evidence_refs=deepcopy(f['evidence_refs']) + ['research:financial_v.CONFIG'])
    return out


def formula_expression(variant):
    """Expand the existing formula operation without introducing new math."""
    f = CATALOG[variant]
    names = [x['field'] for x in f['inputs']]
    op = f['formula']
    if op == 'ratio':
        return f'{names[0]} / {names[1]}'
    if op == 'ratio_average':
        return f'{names[0]} / mean({", ".join(names[1:])})'
    if op == 'difference_ratio':
        return f'({names[0]} - {names[1]}) / {names[2]}'
    if op == 'difference_average':
        return f'({names[0]} - {names[1]}) / mean({", ".join(names[2:])})'
    if op == 'difference':
        return f'{names[0]} - {names[1]}'
    if op.startswith('cagr'):
        return f'({names[0]} / {names[-1]})^(1/{op[-1]}) - 1; positive endpoints; all specified FY inputs required'
    if op == 'positive_growth_share':
        return f'count(positive adjacent FY changes in {", ".join(names)}) / {len(names)-1}'
    return op + '(' + ', '.join(names) + ')'


def registry():
    """Return independent configuration objects; no existing default is changed."""
    recipes = {}
    for model, template in TEMPLATES.items():
        roles = {r: _pending(r) for rs in ROLE_WEIGHTS.values() for r in rs}
        if template in ('BANK', 'INSURANCE', 'BROKER', 'MORTGAGE_REIT'):
            roles['q_profitability'] = _defined('q_profitability', 'roe_common_ttm',
                candidates=('roa_ttm',), overlap=('common_equity_return',),
                limitation='ROA는 다른 분모의 선택 후보이며 ROE의 자동 대체가 아님.')
            roles['q_financial_safety'] = _defined('q_financial_safety', 'common_equity_assets', proxy=True,
                overlap=('common_equity_capital',),
                limitation='장부 자본 완충 대리값; CET1/RBC/규제 순자본·유동성·금리 위험을 입증하지 않음.')
            roles['g_per_share_growth'] = _defined('g_per_share_growth', 'common_bps_cagr_3y', proxy=True,
                overlap=('common_equity_growth',),
                limitation='분모와 배당·환매 영향을 별도 확인; 이익·FCF 성장과 동일하지 않음.')
            roles['g_growth_efficiency'] = _defined('g_growth_efficiency', 'roa_improvement_3y', proxy=True,
                overlap=('asset_return',),
                limitation='수익성 변화 대리값; ROIC 또는 추가 자본의 인과 수익으로 부르지 않음.')
            roles['v_earnings_yield'] = _defined('v_earnings_yield', 'ep_ttm_diluted',
                candidates=('ep_fy_diluted',), overlap=('common_earnings',),
                limitation='TTM·연간 variant를 혼합하거나 순이익/현재 주식수로 EPS를 만들지 않음.')
            book = 'tangible_common_bp' if model == 'BANK' else 'common_bp'
            roles['v_vs_industry'] = _defined('v_vs_industry', book, proxy=True,
                candidates=('common_bp',) if book != 'common_bp' else ('tangible_common_bp',),
                overlap=('common_equity_capital',),
                limitation='원시 B/P 계열만 계산; 동일 모형·정의의 비교집단과 정규화 연결 전 상대가치 점수 없음.')
        elif template == 'ASSET_MANAGER':
            for role, variant, proxy in (
                ('q_profitability', 'operating_margin_ttm', False),
                ('q_earnings_quality', 'accruals_assets_ttm', True),
                ('q_financial_safety', 'debt_assets', True),
                ('g_revenue_growth', 'revenue_cagr_3y', False),
                ('g_per_share_growth', 'eps_diluted_cagr_3y', False),
                ('g_growth_efficiency', 'roa_improvement_3y', True),
                ('g_consistency', 'revenue_growth_consistency_3y', False),
                ('v_earnings_yield', 'ep_ttm_diluted', False),
                ('v_fcf_yield', 'fcf_mcap', True),
            ):
                roles[role] = _defined(role, variant, proxy=proxy,
                    limitation='수수료 사업 회계모형이 확인된 자산운용에 한정; 브로커·자기계정 투자·보험으로 자동 확장하지 않음.')
        else:  # Equity REIT; never silently General or Financial.
            for role, variant, proxy in (
                ('q_profitability', 'cfo_assets_ttm', True),
                ('q_financial_safety', 'debt_assets', True),
                ('g_revenue_growth', 'revenue_cagr_3y', False),
                ('g_growth_efficiency', 'cfo_assets_improvement_3y', True),
                ('g_consistency', 'revenue_growth_consistency_3y', False),
                ('v_earnings_yield', 'nareit_ffo_mcap', False),
            ):
                roles[role] = _defined(role, variant, proxy=proxy,
                    limitation='Nareit FFO 조정표·연결범위 별도 확인; CFO/자산은 FFO 또는 AFFO가 아님.')
            roles['g_per_share_growth']['reason'] = 'FFO/주 성장의 기간·보통주 분모·조정표 정의 준비 중'
            roles['g_per_share_growth']['user_candidates'] = ['ffo_per_share_growth']
            roles['v_fcf_yield']['reason'] = 'AFFO/유지보수 투자·임대 조정의 회사별 조정표 정의 준비 중'
            roles['v_fcf_yield']['user_candidates'] = ['affo_mcap']
        if model == 'LIFE_INSURANCE':
            roles['q_earnings_quality']['reason'] = '보험부채·보증·할인·해약·경험차의 모형별 검증 정의 준비 중'
        elif model == 'PROPERTY_CASUALTY_INSURANCE':
            roles['q_earnings_quality']['reason'] = ('합산비율·손해준비금 발전은 별도 지표; 순경과보험료·'
                '손해액·사업비의 총액/순액·재보험 범위 정의 준비 중. 낮은 대손/손해비용만으로 고품질 판정 금지.')
        elif model == 'MORTGAGE_REIT':
            roles['q_financial_safety']['limitation'] += ' 담보·repo·헤지·듀레이션/금리 위험은 별도 결손.'
        recipes[model] = dict(model_id=model, accounting_template=template, roles=roles,
            status='RESEARCH_INCOMPLETE_NOT_DEFAULT', axis_weights=dict(Q=40, G=15, V=45),
            axis_weight_basis='FINANCIALS_SECTOR_INITIAL_WEIGHTS_NOT_OPTIMUM',
            missing_policy='NULL_WITH_REASON_NO_ROLE_REPLACEMENT',
            peer_policy='SAME_MODEL_VARIANT_DATE_REPRESENTATIVE_ISSUER_MIN8_NO_AUTOMATIC_MERGE',
            definition_complete=all(r['definition_status'] == 'FORMULA_DEFINED' for r in roles.values()))
    return dict(schema_version='financial-555-candidates/1', candidate_version=VERSION,
        official=False, enabled_as_default=False, peer_minimum=MINIMUM_PEERS,
        source_scope='EXISTING_APPROVED_HELD_INPUTS', recipes=recipes)


def evaluate_raw(model, inputs, context):
    """Calculate only defined ratios, preserving period/identity/price validation.

    No percentile, role score, axis, gate or total is manufactured from a partial
    recipe. DIRECT means directly defined measurement, not evidence verification.
    """
    reg = registry()
    if model not in reg['recipes']:
        raise ValueError('UNKNOWN_FINANCIAL_RESEARCH_MODEL')
    recipe = reg['recipes'][model]
    if context.get('accounting_template') != recipe['accounting_template']:
        raise ValueError('ACCOUNTING_MODEL_CONTEXT_MISMATCH')
    roles = {}
    for role, spec in recipe['roles'].items():
        variant = spec['basic_variant']
        if variant is None:
            roles[role] = dict(status='PREPARING', variant=None, value=None,
                              reason=spec['reason'], factor_score=None, role_score=None)
            continue
        required = spec['required_inputs']
        present = [s['field'] for s in required if isinstance(inputs.get(s['field']), dict)
                   and inputs[s['field']].get('value') is not None]
        common = [s['field'] for s in required if s['field'].startswith(('common_equity', 'net_income_common'))]
        common_invalid = any(isinstance(inputs.get(f), dict) and inputs[f].get('value') is not None
            and inputs[f].get('equity_basis') != 'COMMON_EXCLUDING_PREFERRED_NCI' for f in common)
        if common_invalid:
            obs = dict(status='COMMON_ATTRIBUTION_UNCONFIRMED', value=None)
        else:
            obs = calculate_factor(variant, inputs, context)
        roles[role] = dict(variant=variant, status=obs['status'], value=obs.get('value'),
            required_fields=[s['field'] for s in required], present_fields=present,
            missing_fields=[s['field'] for s in required if s['field'] not in present],
            numeric_inputs_present=len(present) == len(required),
            raw_valid=obs['status'] in VALID, observation=obs,
            factor_score=None, role_score=None, evidence_status=spec['evidence_status'])
    return dict(schema_version='financial-555-raw-result/1', candidate_version=VERSION,
        model_id=model, issuer_id=context.get('issuer_id'), valuation_date=context['valuation_date'],
        as_of=context['as_of'], input_hash=digest(inputs), recipe_hash=digest(recipe),
        roles=roles, axes=dict(Q=None, G=None, V=None), total=None, rank=None,
        candidate_adopted=False, score_status='RECIPE_INCOMPLETE_NO_NORMALIZATION_CONNECTED',
        peer_minimum=MINIMUM_PEERS, raw_calculation_requires_peer_sample=False,
        nominal_role_contribution={r: recipe['axis_weights'][s['axis']]*s['weight']/100
                                   for r,s in recipe['roles'].items()},
        effective_role_contribution=None,
        official=False, historical_pit=False)
