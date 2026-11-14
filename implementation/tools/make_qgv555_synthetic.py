#!/usr/bin/env python3
"""Make Main's SYNTHETIC QGV 555 / Top500 contract examples (owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」).

The producer's contracts (qgv-top500-population/1, qgv-555-catalog/1, qgv-555-preset/1 — names proposed to Codex in #437
6868375798) are not delivered yet. Until then the screen is built against these Main-made examples, every file marked
data_kind SYNTHETIC and contract_state MAIN_PROPOSAL_UNCONFIRMED:
- catalog.json: the existing 51 factors of docs/research/sector_qgv/catalog.json (their names, formulas, periods, units,
  directions, scopes, statuses and evidence unchanged) regrouped into Main's PROPOSED five roles per axis, each with the input
  families its inputs come from (for the information-overlap view), alias groups (same definition = one choice), variant
  groups (registered period / formula variants of one concept) and one synthetic composite with bounded internal weights;
- presets.json: U1-555 (one COMMON preset) and S1-555 (a few SECTOR|TEMPLATE presets), equal weights, made-up;
- population-top500.json: 500 made-up issuers (SYN-I0001 …) with selection ranks, a members hash, candidate_pool_complete false.
Nothing here is a score, a factor value, a price or a market capitalisation. Output is deterministic (no clock).

  python implementation/tools/make_qgv555_synthetic.py [--out implementation/docs/frontend_v2/qgv555-synthetic]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'docs' / 'research' / 'sector_qgv' / 'catalog.json'
OUT = ROOT / 'docs' / 'frontend_v2' / 'qgv555-synthetic'
STATE = 'MAIN_PROPOSAL_UNCONFIRMED'

ROLES = {
    'Q': [('profitability', '수익성', '자산·매출 대비 이익을 얼마나 내는가'), ('accounting_quality', '회계 품질', '이익이 현금·자산 변화와 맞는가'),
          ('financial_capacity', '재무 여력', '차입·자본 구조의 여유'), ('interest_capacity', '이자 지급 능력', '이익으로 이자를 감당하는가'),
          ('stability', '안정성', '이익이 해마다 얼마나 흔들리는가')],
    'G': [('revenue_growth', '매출 성장', '매출이 늘어나는 속도와 지속성'), ('earnings_growth', '이익 성장', '영업이익·주당이익이 늘어나는 속도'),
          ('profitability_change', '수익성 개선', '수익성 비율이 나아지는가'), ('capital_growth', '자본 성장', '주당 장부가치가 쌓이는 속도'),
          ('cash_flow_growth', '현금흐름 성장', '주당 현금흐름이 늘어나는 속도')],
    'V': [('earnings_value', '이익 가치', '이익 대비 가격'), ('book_value', '장부 가치', '장부가치 대비 가격'), ('sales_value', '매출 가치', '매출 대비 가격'),
          ('cash_value', '현금 가치', '현금흐름 대비 가격'), ('shareholder_return', '주주환원', '배당·자사주로 돌려주는 몫')],
}
ROLE_OF = {
    'operating_margin_ttm': 'profitability', 'roa_ttm': 'profitability', 'roe_common_ttm': 'profitability', 'cfo_assets_ttm': 'profitability',
    'gross_profit_assets_ttm': 'profitability', 'roic_explicit': 'profitability',
    'accruals_assets_ttm': 'accounting_quality', 'noa_growth': 'accounting_quality', 'depreciation_capex': 'accounting_quality',
    'debt_assets': 'financial_capacity', 'common_equity_assets': 'financial_capacity', 'net_debt_assets': 'financial_capacity',
    'interest_coverage_ttm': 'interest_capacity', 'profit_stability_5y': 'stability',
    'revenue_cagr_3y': 'revenue_growth', 'revenue_growth_1y': 'revenue_growth', 'revenue_cagr_5y': 'revenue_growth', 'revenue_growth_consistency_3y': 'revenue_growth',
    'operating_income_cagr_3y': 'earnings_growth', 'eps_diluted_cagr_3y': 'earnings_growth', 'consensus_growth': 'earnings_growth',
    'roa_improvement_3y': 'profitability_change', 'cfo_assets_improvement_3y': 'profitability_change',
    'common_bps_cagr_3y': 'capital_growth', 'tangible_bps_growth': 'capital_growth',
    'cfo_per_share_growth': 'cash_flow_growth', 'fcf_per_share_growth': 'cash_flow_growth', 'ffo_per_share_growth': 'cash_flow_growth',
    'ep_ttm_diluted': 'earnings_value', 'ep_fy_diluted': 'earnings_value', 'ep_fy1': 'earnings_value', 'ep_ntm': 'earnings_value',
    'net_income_mcap': 'earnings_value', 'peg_historical': 'earnings_value', 'peg_forecast': 'earnings_value', 'nareit_ffo_mcap': 'earnings_value',
    'affo_mcap': 'earnings_value', 'ebit_ev': 'earnings_value',
    'common_bp': 'book_value', 'tangible_common_bp': 'book_value', 'sales_mcap': 'sales_value', 'sales_ev': 'sales_value',
    'cfo_mcap': 'cash_value', 'ni_da_mcap': 'cash_value', 'fcf_mcap': 'cash_value', 'fcf_ev': 'cash_value', 'fcff_ev': 'cash_value', 'ebitda_ev': 'cash_value',
    'dividend_yield_ttm': 'shareholder_return', 'net_share_reduction': 'shareholder_return', 'shareholder_yield': 'shareholder_return',
}
FAMILY = {  # input families: where a factor's information comes from (overlap across roles and axes)
    'net_income': ['roa_ttm', 'roe_common_ttm', 'accruals_assets_ttm', 'ep_ttm_diluted', 'ep_fy_diluted', 'net_income_mcap', 'ni_da_mcap', 'eps_diluted_cagr_3y',
                   'peg_historical', 'roa_improvement_3y', 'profit_stability_5y'],
    'forecast_eps': ['ep_fy1', 'ep_ntm', 'peg_forecast', 'consensus_growth'],
    'operating_income': ['operating_margin_ttm', 'interest_coverage_ttm', 'ebit_ev', 'ebitda_ev', 'operating_income_cagr_3y', 'roic_explicit'],
    'revenue': ['operating_margin_ttm', 'revenue_cagr_3y', 'revenue_growth_1y', 'revenue_cagr_5y', 'revenue_growth_consistency_3y', 'sales_mcap', 'sales_ev'],
    'gross_profit': ['gross_profit_assets_ttm'],
    'cfo': ['accruals_assets_ttm', 'cfo_assets_ttm', 'cfo_assets_improvement_3y', 'cfo_mcap', 'fcf_mcap', 'fcf_ev', 'cfo_per_share_growth', 'fcf_per_share_growth', 'fcff_ev'],
    'book_equity': ['roe_common_ttm', 'common_equity_assets', 'common_bps_cagr_3y', 'common_bp', 'tangible_common_bp', 'tangible_bps_growth'],
    'debt': ['debt_assets', 'net_debt_assets'],
    'shareholder_payout': ['dividend_yield_ttm', 'net_share_reduction', 'shareholder_yield'],
    'reit_ffo': ['nareit_ffo_mcap', 'affo_mcap', 'ffo_per_share_growth'],
    'operating_assets': ['noa_growth', 'depreciation_capex'],
}
VARIANT_GROUP = {'revenue_cagr_3y': 'revenue_growth_period', 'revenue_growth_1y': 'revenue_growth_period', 'revenue_cagr_5y': 'revenue_growth_period',
                 'ep_ttm_diluted': 'earnings_yield_period', 'ep_fy_diluted': 'earnings_yield_period', 'ep_fy1': 'earnings_yield_period', 'ep_ntm': 'earnings_yield_period',
                 'cfo_mcap': 'cash_yield_formula', 'ni_da_mcap': 'cash_yield_formula'}
COMPOSITE = {'variant_id': 'syn_cash_yield_composite', 'display_name': '현금수익률 합성(합성 예시)', 'axis': 'V', 'role_id': 'cash_value',
             'components': [{'variant_id': 'cfo_mcap', 'default_weight': 5000, 'min_weight': 3000, 'max_weight': 7000},
                            {'variant_id': 'fcf_mcap', 'default_weight': 5000, 'min_weight': 3000, 'max_weight': 7000}]}
S1_SCOPES = ['CONSUMER_DISCRETIONARY|GENERAL', 'FINANCIALS|BANK', 'FINANCIALS|INSURANCE', 'REAL_ESTATE|EQUITY_REIT']


def canon(v) -> str:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(v) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()


def catalog() -> dict:
    src = json.loads(CATALOG.read_text(encoding='utf-8'))
    fam = {}
    for k, vs in FAMILY.items():
        for v in vs:
            fam.setdefault(v, []).append(k)
    factors = []
    for f in src:
        v = f['variant_id']
        factors.append({'variant_id': v, 'factor_id': f['factor_id'], 'axis': f['axis'], 'role_id': ROLE_OF[v], 'display_name': f['display_name'],
                        'aliases': f['aliases'], 'alias_group': v, 'formula': f['formula'], 'formula_version': f['formula_version'], 'inputs': f['inputs'],
                        'unit': f['unit'], 'direction': f['direction'], 'period': f['period'], 'scope': f['scope'],
                        'calculator_status': f['calculator_status'], 'accounting_applicability': f['accounting_applicability'],
                        'is_default': f['is_default'], 'recommended': bool(f['recommendation'].get('recommended')),
                        'evidence_refs': f['evidence_refs'], 'input_families': sorted(fam.get(v, [])), 'variant_group': VARIANT_GROUP.get(v), 'composite': None})
    factors.append({**{k: None for k in factors[0]}, 'variant_id': COMPOSITE['variant_id'], 'factor_id': 'SYN-C1', 'axis': 'V', 'role_id': COMPOSITE['role_id'],
                    'display_name': COMPOSITE['display_name'], 'aliases': [], 'alias_group': COMPOSITE['variant_id'], 'formula': 'composite', 'formula_version': '1',
                    'inputs': [], 'unit': 'decimal', 'direction': 'HIGHER', 'period': 'TTM', 'scope': ['GENERAL'], 'calculator_status': 'IMPLEMENTED',
                    'accounting_applicability': True, 'is_default': False, 'recommended': False, 'evidence_refs': ['main:synthetic-example'],
                    'input_families': ['cfo'], 'variant_group': None, 'composite': {'components': COMPOSITE['components']}})
    return {'schema_version': 'qgv-555-catalog/1', 'data_kind': 'SYNTHETIC', 'contract_state': STATE, 'catalog_version': 'syn-0.1.0',
            'roles': {a: [{'role_id': r, 'name': n, 'economic_role': e} for r, n, e in rs] for a, rs in ROLES.items()}, 'factors': factors}


def _preset(model_id, preset_id, scope, cat, template):
    ok = lambda f: f['calculator_status'] == 'IMPLEMENTED' and template in f['scope'] and f['composite'] is None
    axes = {}
    for a, rs in ROLES.items():
        picks = {}
        for r, _, _ in rs:
            cand = [f for f in cat['factors'] if f['axis'] == a and f['role_id'] == r and ok(f)]
            picks[r] = next((f for f in cand if f['is_default']), cand[0] if cand else None)
        live = [r for r in picks if picks[r]]
        share = {r: 10000 // len(live) + (1 if i < 10000 % len(live) else 0) for i, r in enumerate(live)}
        # a role with no implemented, applicable factor in this scope stays in the axis with weight 0 (계산 준비 중 / 적용 부적합)
        axes[a] = {r: {'weight': share.get(r, 0), 'factors': {picks[r]['variant_id']: 10000} if picks[r] else {}} for r in picks}
    return {'schema_version': 'qgv-555-preset/1', 'data_kind': 'SYNTHETIC', 'contract_state': STATE, 'model_id': model_id, 'preset_id': preset_id,
            'version': '0.1.0', 'scope': scope, 'axis_weights': {'Q': 3400, 'G': 3300, 'V': 3300}, 'axes': axes}


def presets(cat) -> dict:
    out = [_preset('unified-555/0.1.0', 'qgv-555-unified-default/0.1.0', 'COMMON', cat, 'GENERAL')]
    for s in S1_SCOPES:
        out.append(_preset('sector-555/0.1.0', 'qgv-555-sector-default/0.1.0', s, cat, s.split('|')[1]))
    return {'schema_version': 'qgv-555-presets/1', 'data_kind': 'SYNTHETIC', 'contract_state': STATE, 'presets': out}


def population() -> dict:
    members = [{'issuer_id': 'SYN-I%04d' % i, 'representative_security_id': 'SYN-S%04d' % i, 'selection_rank': i, 'share_classes': 2 if i % 97 == 0 else 1}
               for i in range(1, 501)]
    return {'schema_version': 'qgv-top500-population/1', 'data_kind': 'SYNTHETIC', 'contract_state': STATE, 'population_id': 'SYN-MCAP-TOP500',
            'version': 'syn-2026-11-04/1', 'unit': 'ISSUER', 'n': 500, 'selection_date': '2026-11-04', 'effective_date': '2026-11-05',
            'shares_basis_date': '2026-09-30', 'price_basis_date': '2026-11-04', 'candidate_count': 4123, 'missing_mcap_count': 37,
            'boundary': {'rank_500_missing_neighbours': 2, 'window': 25}, 'candidate_pool_complete': False,
            'candidate_pool_basis': 'SYNTHETIC: no completeness gate run', 'previous': None, 'changes': None,
            'members_hash': sha(members), 'members': members}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', type=Path, default=OUT)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    cat = catalog()
    files = {'catalog.json': cat, 'presets.json': presets(cat), 'population-top500.json': population()}
    for n, v in files.items():
        (a.out / n).write_text(json.dumps(v, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('QGV555_SYNTHETIC ' + ' '.join(n + '=' + hashlib.sha256((a.out / n).read_bytes()).hexdigest()[:12] for n in files))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
