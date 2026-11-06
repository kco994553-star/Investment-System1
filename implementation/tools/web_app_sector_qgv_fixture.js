'use strict';
// Sector QGV (feature 2.2, owner 2026-11-06) test data — NOT a published file and NOT real data.
//  - presets(): sector-qgv-default/0.1.0 as transcribed by Main from the owner's design §5 (tests/fixtures/sector_qgv_default_v0_1_0.json).
//  - bundle(): a SYNTHETIC sector-qgv-bundle/1 around those presets: Main's provisional factor catalog (the design's candidate names,
//    calculator READY / PENDING), recommendations with their reason and evidence level, invented companies SYN-SQ-nnn (no
//    universe code: none is a real company) and invented factor scores 0–100 with the design's missing states. Codex owns the
//    real catalog, scores and presets; their synthetic bundle replaces this one byte for byte when it arrives.
const fs = require('node:fs');
const path = require('node:path');
const PRESETS = path.join(__dirname, '..', 'tests', 'fixtures', 'sector_qgv_default_v0_1_0.json');
const presets = () => JSON.parse(fs.readFileSync(PRESETS, 'utf8'));
const GEN = ['GENERAL'], FIN = ['BANK', 'INSURANCE', 'BROKER', 'MORTGAGE_REIT'], AM = ['ASSET_MANAGER'], REIT = ['EQUITY_REIT'];
const ALL = [...GEN, ...FIN, ...AM, ...REIT];
const TEMPLATES = [['GENERAL', '일반기업'], ['BANK', '은행'], ['INSURANCE', '보험'], ['BROKER', '증권'], ['MORTGAGE_REIT', 'Mortgage REIT'], ['ASSET_MANAGER', '순수 자산운용'], ['EQUITY_REIT', 'Equity REIT']];
const ROLES = [['Q', 'profitability', '수익성'], ['Q', 'accrual_quality', '회계품질'], ['Q', 'financial_strength', '재무여력'], ['Q', 'capital', '자본여력'], ['Q', 'coverage', '이자 부담 여력'],
  ['G', 'growth', '성장'], ['G', 'profitability_change', '수익성 변화'], ['V', 'earnings', '이익가치'], ['V', 'cash', '현금가치'], ['V', 'other', '기타가치']];
// [id, axis, role, name, aliases, templates, status, direction, unit, period, overlap, explain]
const F = [
  ['Q01_OPERATING_MARGIN', 'Q', 'profitability', '영업이익률', ['operating margin'], [...GEN, ...AM], 'READY', 'HIGHER', '%', 'TTM', null, '영업이익 ÷ 매출'],
  ['Q_ROA', 'Q', 'profitability', 'ROA', ['총자산이익률'], ALL, 'READY', 'HIGHER', '%', 'TTM · 평균자산', null, '순이익 ÷ 평균 총자산'],
  ['Q_ROE_COMMON', 'Q', 'profitability', '보통주 ROE', ['ROE', '자기자본이익률'], [...GEN, ...FIN, ...AM], 'READY', 'HIGHER', '%', 'TTM · 평균 보통주자본', null, '보통주 귀속 순이익 ÷ 평균 보통주자본'],
  ['Q_ROIC', 'Q', 'profitability', 'ROIC', ['투하자본이익률'], GEN, 'PENDING', 'HIGHER', '%', 'TTM', null, '계산기 준비 중'],
  ['Q_CFO_TO_AVG_ASSETS', 'Q', 'profitability', 'CFO/평균자산', ['CFO/자산'], [...GEN, ...REIT], 'READY', 'HIGHER', '%', 'TTM', null, '영업현금흐름 ÷ 평균 총자산'],
  ['Q05_ACCRUALS', 'Q', 'accrual_quality', '발생액 대리', ['accruals'], [...GEN, ...AM], 'READY', 'LOWER', '%', 'TTM', null, '낮을수록 우수'],
  ['Q06_DEBT_TO_ASSETS', 'Q', 'financial_strength', '차입금/자산', ['부채비율 대리'], [...GEN, ...AM, ...REIT], 'READY', 'LOWER', '%', '최신 분기말', null, '낮을수록 우수'],
  ['Q14_COMMON_EQUITY_TO_ASSETS', 'Q', 'capital', '보통주자본/총자산', [], FIN, 'READY', 'HIGHER', '%', '최신 분기말', null, '회계상 레버리지 대리 · CET1·지급여력비율 아님'],
  ['Q_INTEREST_COVERAGE', 'Q', 'coverage', '이자보상배율', [], [...GEN, ...REIT], 'READY', 'HIGHER', '배', 'TTM', null, 'EBIT ÷ 이자비용'],
  ['G02_SALES_CAGR3', 'G', 'growth', '매출 3년 CAGR', ['매출 성장률'], [...GEN, ...AM, ...REIT], 'READY', 'HIGHER', '%/년', '최신 연간 3년', null, '연간 매출 3년 복리 성장률'],
  ['G_EPS_CAGR3', 'G', 'growth', 'EPS 3년 CAGR', ['EPS 성장률'], [...GEN, ...AM], 'READY', 'HIGHER', '%/년', '최신 연간 3년', null, '희석 EPS 3년 복리 성장률(양수 시작·종료만)'],
  ['G13_COMMON_BPS_CAGR3', 'G', 'growth', '보통주 BPS 3년 CAGR', ['BPS 성장률'], FIN, 'READY', 'HIGHER', '%/년', '최신 연간 3년', null, '유형장부가 성장 G10과 별개'],
  ['G06_ROA_CHANGE3', 'G', 'profitability_change', '3년 ROA 개선', ['ROA 변화'], [...GEN, ...FIN, ...AM], 'READY', 'HIGHER', '%p', 'ROA_t − ROA_t−3', null, 't−3 계산에 t−4 자산 필요'],
  ['G14_CFO_AVG_ASSETS_CHANGE3', 'G', 'profitability_change', 'CFO/평균자산 3년 변화', [], REIT, 'READY', 'HIGHER', '%p', 't − t−3', null, 'Equity REIT 성장 보조'],
  ['V_EARNINGS_YIELD', 'V', 'earnings', 'PER · E/P', ['PER', 'P/E', 'E/P', '이익수익률'], ALL, 'READY', 'HIGHER', '%', 'TTM 희석 EPS / 주가', null, '같은 EPS·주가의 PER과 E/P는 한 요소 · 적자는 E/P 음수(유효), PER 매력으로 보상 안 함'],
  ['V_FWD_EARNINGS_YIELD', 'V', 'earnings', '예상 PER', ['forward PER', '예상 E/P'], ALL, 'PENDING', 'HIGHER', '%', 'FY1·NTM', null, '당시 전망치 이력 필요 · 계산기 준비 중'],
  ['V_PEG_FWD', 'V', 'earnings', '예상 PEG', ['PEG'], GEN, 'PENDING', 'LOWER', '배', '전망 성장', null, 'PER ÷ (성장률×100) · 이익·성장 양수만'],
  ['V_FFO_TO_MCAP', 'V', 'earnings', 'P/FFO · FFO 수익률', ['P/FFO', 'FFO'], REIT, 'READY', 'HIGHER', '%', 'TTM Nareit FFO', null, 'Equity REIT 전용'],
  ['V_CFO_YIELD', 'V', 'cash', 'PCR · CFO 수익률', ['PCR', 'P/CF', 'CFO 수익률'], [...GEN, ...AM, ...REIT], 'READY', 'HIGHER', '%', 'TTM CFO / 시총', null, 'CFO 정의만 · 다른 현금흐름 정의와 섞지 않음'],
  ['V06_FCF_TO_MCAP', 'V', 'cash', '(CFO−CAPEX)/시총 · P/FCF', ['P/FCF', 'FCF 수익률'], GEN, 'READY', 'HIGHER', '%', 'TTM', null, 'FCFE라고 부르지 않음'],
  ['V_DIVIDEND_YIELD_TTM', 'V', 'other', 'TTM 배당수익률', ['배당수익률', 'dividend yield'], ALL, 'READY', 'HIGHER', '%', 'TTM 보통주 배당', null, '확정 무배당 = 0(유효), 입력 없음 ≠ 0'],
  ['V_EBITDA_TO_EV', 'V', 'other', 'EV/EBITDA · EBITDA/EV', ['EV/EBITDA'], GEN, 'READY', 'HIGHER', '%', 'TTM', 'ENTERPRISE_VALUE', 'EV ≤ 0이면 점수 보류'],
  ['V_EBIT_TO_EV', 'V', 'other', 'EV/EBIT', ['EBIT/EV'], GEN, 'PENDING', 'HIGHER', '%', 'TTM', 'ENTERPRISE_VALUE', '계산기 준비 중'],
  ['V_SALES_TO_MCAP', 'V', 'other', 'PSR · 매출/시총', ['PSR', 'P/S'], GEN, 'READY', 'HIGHER', '%', 'TTM', 'SALES_VALUE', '마진·부채 구조와 함께 해석'],
  ['V_SALES_TO_EV', 'V', 'other', 'EV/Sales · 매출/EV', ['EV/Sales'], GEN, 'READY', 'HIGHER', '%', 'TTM', 'SALES_VALUE', 'PSR과 관련 신호이나 같은 지표 아님'],
  ['V_BOOK_YIELD', 'V', 'other', 'PBR · B/P', ['PBR', 'P/B'], [...GEN, ...FIN, ...AM], 'READY', 'HIGHER', '%', '최신 분기말 보통주자본', null, '자본 0 이하는 해석 제한'],
  ['V_TBV_YIELD', 'V', 'other', 'P/TBV · TB/P', ['P/TBV'], FIN, 'READY', 'HIGHER', '%', '최신 분기말', null, '무형자산·영업권 제외 범위 고정'],
  ['V_SHAREHOLDER_YIELD', 'V', 'other', '주주환원수익률', ['shareholder yield'], GEN, 'PENDING', 'HIGHER', '%', 'TTM', null, '배당 + 순주식수 감소 · 계산기 준비 중'],
];
const factors = () => F.map(([factor_id, axis, role, display_name, aliases, applicable_templates, calculator_status, direction, unit, period, overlap_group, explain]) =>
  ({ factor_id, axis, role, display_name, aliases, variant_id: factor_id.toLowerCase() + '.v0', formula_version: 'proposal-0', unit, direction, period, overlap_group, applicable_templates, calculator_status, explain }));
const RECS = [
  ['V_SALES_TO_EV', 'INFORMATION_TECHNOLOGY', null, '정보기술의 매출가치 비교에 적합', 'BOOK_SECTOR', ['What Works on Wall Street 4판 24장 (섹터 연구)']],
  ['V_BOOK_YIELD', 'FINANCIALS', 'BANK', '은행의 장부가치 비교에 적합', 'ACCOUNTING_FIT', ['Damodaran, Valuing Financial Service Firms']],
  ['V_TBV_YIELD', 'FINANCIALS', 'BANK', '은행의 유형자본 대비 가격 비교', 'ACCOUNTING_FIT', ['Damodaran, Valuing Financial Service Firms']],
  ['V_EARNINGS_YIELD', null, null, '이익 대비 가격의 공통 기준', 'QUANT_RESEARCH', ['What Works on Wall Street 4판']],
  ['V_CFO_YIELD', null, 'GENERAL', '현금흐름 대비 가격의 공통 기준', 'QUANT_RESEARCH', ['What Works on Wall Street 4판']],
  ['V_DIVIDEND_YIELD_TTM', 'CONSUMER_STAPLES', null, '필수소비재의 주주환원 비교', 'BOOK_SECTOR', ['What Works on Wall Street 4판 24장']],
  ['V_FFO_TO_MCAP', 'FINANCIALS', 'EQUITY_REIT', 'Equity REIT의 운영성과 대비 가격', 'ACCOUNTING_FIT', ['Nareit FFO 정의']],
];
const recommendations = () => RECS.map(([factor_id, sector_id, template_id, reason, evidence_level, source_refs]) => ({ factor_id, sector_id, template_id, reason, evidence_level, source_refs, reviewed_at: '2026-11-06' }));
const LYNCH = ['저성장', '대형 우량', '고성장', '경기순환', '회생', '자산 가치'];
// Deterministic pseudo-random in [0, 1) from a string.
function rnd(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; } return (h % 100000) / 100000; }
function companies(P) {
  const out = []; let n = 0; const add = (sector_id, template_id, count, status = 'MAPPED') => { for (let i = 0; i < count; i++) { n++;
    out.push({ company_id: 'SYN-SQ-' + String(n).padStart(3, '0'), universe_code: null, sector_id, template_id, mapping_status: status, lynch_tags: [LYNCH[n % LYNCH.length]] }); } };
  for (const s of P.sectors) { if (s.id === 'FINANCIALS') continue; add(s.id, 'GENERAL', 25); }
  add('FINANCIALS', 'BANK', 22); add('FINANCIALS', 'INSURANCE', 6); add('FINANCIALS', 'ASSET_MANAGER', 4); add('FINANCIALS', 'EQUITY_REIT', 21);
  for (let i = 0; i < 3; i++) { n++; out.push({ company_id: 'SYN-SQ-' + String(n).padStart(3, '0'), universe_code: null, sector_id: null, template_id: null, mapping_status: 'MAPPING_UNRESOLVED', lynch_tags: [] }); }
  return out;
}
// Scores: NOT_APPLICABLE outside the factor's templates, PEER_SAMPLE_SMALL for groups under 20 (insurance, asset managers),
// about 4 % MISSING_INPUT, otherwise an invented percentile; a few VALID_NEGATIVE marks on the earnings yield.
function scores(fs_, cs) {
  const size = {}; for (const c of cs) if (c.mapping_status === 'MAPPED') { const k = c.sector_id + '|' + c.template_id; size[k] = (size[k] || 0) + 1; }
  const out = {};
  for (const f of fs_) { if (f.calculator_status !== 'READY') continue; const cells = out[f.factor_id] = {};
    for (const c of cs) { const id = c.company_id;
      if (c.mapping_status !== 'MAPPED') { cells[id] = { score: null, status: 'MAPPING_UNRESOLVED' }; continue; }
      if (!f.applicable_templates.includes(c.template_id)) { cells[id] = { score: null, status: 'NOT_APPLICABLE' }; continue; }
      if (size[c.sector_id + '|' + c.template_id] < 20) { cells[id] = { score: null, status: 'PEER_SAMPLE_SMALL' }; continue; }
      const r = rnd(f.factor_id + id);
      if (r < 0.04) { cells[id] = { score: null, status: 'MISSING_INPUT' }; continue; }
      const score = Math.round(rnd(id + f.factor_id + 's') * 1000) / 10;
      cells[id] = { score, status: f.factor_id === 'V_EARNINGS_YIELD' && score < 5 ? 'VALID_NEGATIVE' : 'VALID' }; } }
  return out;
}
function bundle() {
  const P = presets(), fs_ = factors(), cs = companies(P);
  return { schema: 'sector-qgv-bundle/1', data_kind: 'SYNTHETIC',
    snapshot: { snapshot_id: 'SYN-SNAPSHOT-1', as_of: '2026-11-02', universe_id: 'SYNTHETIC-UNIVERSE', universe_version: 'syn-1', engine_version: 'proposal-0', normalization_version: 'midrank-pct-20.proposal', mapping_version: 'book10-syn-1' },
    method_note: '합성 예시 · 요소 점수는 지어낸 값 · 실제 재계산 아님',
    sectors: P.sectors, templates: TEMPLATES.map(([id, label]) => ({ id, label })), roles: ROLES.map(([axis, role, label]) => ({ axis, role, label })),
    factors: fs_, recommendations: recommendations(), presets: P.presets, companies: cs, scores: scores(fs_, cs) };
}
module.exports = { PRESETS, presets, bundle, factors, rnd };
