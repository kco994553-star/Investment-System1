'use strict';
// Lab 9.1 연구 범위 · 선정 방식 (owner 2026-11-04 third, item 4): web_app/research-scope.js against Codex's #474 and #473.
//  - Coverage: tests/fixtures/operational_qgv_coverage_v1_synthetic.json is the output of Codex's #474 (572f0b5e)
//    research.operational_coverage on the public fixture qgv_official_vectors_v1.json (SYNTHETIC): as is (engine differs → every
//    preset null) and the same rows with engine_matches true (presets derived). Q, G, V, all three axes, each preset and the
//    published default total are separate rows with separate labels; the denominator says operational codes, not security ids,
//    and a count other than 504 says it differs from Universe504; a null preset is 미산출 with its reason, never 0.
//  - The validator refuses the whole file at its first fault (schema, denominators, counts, NOT_APPLICABLE, presets, whole market).
//  - Selection: Codex's count rule of select_provisional (all; min(n, N); floor(n × p / 100)), equal weights, outcomes never read,
//    and the official N15 / TARGET line.
const assert = require('node:assert/strict');
const R = require('../src/investment_system/product/web_app/research-scope.js');
const F = require('../tests/fixtures/operational_qgv_coverage_v1_synthetic.json');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const copy = (x) => JSON.parse(JSON.stringify(x));
const ids = (k) => Array.from({ length: k }, (_, i) => 'SYNTHETIC:C' + String(i).padStart(3, '0'));
const sel = (policy, e, s) => ({ selection_policy: policy, n_eligible: e, n_selected: s, selected: ids(s), weights: s ? Object.fromEntries(ids(s).map((i) => [i, 1 / s])) : null,
  outcomes: { secret: { realised: 0.123 } }, equal_weight_realized: 0.0456 });

ok('Codex #474 output (both variants) passes and stays frozen', () => {
  for (const k of ['engine_mismatch', 'engine_matched']) {
    const r = R.validateCoverage(F[k]); assert.equal(r.ok, true, k + ' ' + JSON.stringify(r));
    assert.ok(Object.isFrozen(r.value.presets.balanced));
  }
  assert.deepEqual(Object.keys(F.engine_matched.factors).sort(), [...R.FACTORS].sort());
  assert.deepEqual(Object.keys(F.engine_matched.presets).sort(), [...R.PRESETS].sort());
});
ok('Q, G, V each, all three axes, each preset and the published total are separate rows', () => {
  const v = R.coverageView(R.validateCoverage(F.engine_matched).value);
  assert.deepEqual(v.rows.map((x) => x.kind), ['axis', 'axis', 'axis', 'all_axes', ...R.PRESETS.map(() => 'preset'), 'published_total']);
  assert.equal(new Set(v.rows.map((x) => x.label)).size, v.rows.length, 'no two rows share a label');
  const at = Object.fromEntries(v.rows.map((x) => [x.id, x]));
  assert.equal(at['axis-Q'].value, '계산 가능 27 / 30 · 결손 3');
  assert.equal(at['axis-V'].value, '계산 가능 15 / 30 · 결손 15');
  assert.equal(at['all-axes'].value, '계산 가능 15 / 30');
  assert.equal(at['preset-balanced'].value, '계산 가능 27 / 30', 'balanced total 27/30 while three axes 15/30');
  assert.equal(at['preset-value'].value, '계산 가능 15 / 30');
  assert.equal(at['published-total'].value, '있음 27 / 30');
  assert.equal(v.factors.length, 15);
  assert.match(v.factors.find((f) => f.id === 'v_fcf_yield').value, /해당 없음 9 · 결손 6/, 'NOT_APPLICABLE stays apart from missing');
});
ok('engine mismatch: every preset 미산출 with its reason, never 0', () => {
  const v = R.coverageView(R.validateCoverage(F.engine_mismatch).value);
  for (const x of v.rows.filter((r) => r.kind === 'preset')) { assert.equal(x.value, '미산출'); assert.equal(x.valid, null); assert.equal(x.note, null, 'the reason is said once, not on seven rows'); }
  assert.match(v.engine, /엔진 버전/);
});
ok('denominator words: operational codes, not security ids; 504 or the difference', () => {
  const v = R.coverageView(R.validateCoverage(F.engine_matched).value);
  assert.equal(v.basis, '운영 게시본 코드 30개 기준 · Universe504(504개)와 다름 · 게시 행 36개 중 TARGET 6개 제외 · 고정 증권 ID 아님 · 발행사 CIK 수 미확인(CIK 없는 행 3개)');
  assert.match(R.basisText({ count: 504, published_rows: 510, target_rows_excluded: 6, unique_issuer_ciks: 501, missing_cik_rows: 0 }), /^운영 Universe504 코드 504개 기준 · .* · 고정 증권 ID 아님 · 발행사 CIK 501개$/);
  assert.match(v.scope, /과거 전체 시장 커버리지 아님/);
  assert.match(v.presetBasis, /저장된 프리셋 총점이나 과거 시점 재구성이 아님/);
});
const refusals = [
  ['SCHEMA_VERSION', '$.schema_version', (c) => { c.schema_version = 'operational-qgv-coverage/2'; }],
  ['KEY_UNKNOWN', '$.score', (c) => { c.score = 1; }],
  ['DENOMINATOR_MISMATCH', '$.axes.Q.denominator', (c) => { c.axes.Q.denominator = 31; }],
  ['COUNT_MISMATCH', '$.axes.G.missing', (c) => { c.axes.G.missing = 2; }],
  ['COUNT_MISMATCH', '$.factors.v_fcf_yield.reason_categories.NOT_APPLICABLE', (c) => { c.factors.v_fcf_yield.not_applicable = 8; }],
  ['COUNT_RANGE', '$.all_axes.valid', (c) => { c.all_axes.valid = 16; }],
  ['PRESET_VALID_MISMATCH', '$.presets.balanced.valid', (c) => { c.presets.balanced.valid = 0; }],
  ['ENGINE_MISMATCH_NOT_NULL', '$.presets.balanced', (c) => { c.engine_matches = false; }],
  ['WHOLE_MARKET_NOT_ALLOWED', '$.historical_whole_market_coverage', (c) => { c.historical_whole_market_coverage = { valid: 1 }; }],
  ['SECURITY_ID_NOT_ALLOWED', '$.denominator.unique_securities', (c) => { c.denominator.unique_securities = 30; }],
  ['CODE_INVALID', '$.membership_codes[0]', (c) => { c.membership_codes[0] = 'TARGET:x'; }],
  ['COUNT_MISMATCH', '$.denominator.published_rows', (c) => { c.denominator.published_rows = 35; }],
];
ok('every coverage rule refuses the whole file with its code and path', () => {
  for (const [code, at, change] of refusals) {
    const c = copy(F.engine_matched); change(c);
    const r = R.validateCoverage(c);
    assert.deepEqual({ ok: r.ok, code: r.code, path: r.path }, { ok: false, code, path: at }, code + ' ' + at);
  }
  assert.equal(R.validateCoverage(null).ok, false);
});
ok('selection: all · top N · top % follow Codex counts; weights equal; outcomes never read', () => {
  const view = (x) => { const r = R.validateSelection(x); assert.equal(r.ok, true, JSON.stringify(r)); return R.selectionView(r.value); };
  assert.equal(view(sel(null, 137, 137)).label, '조건 충족 전부 (선정 방식 지정 없음)');
  assert.equal(view(sel({ mode: 'all', value: null }, 137, 137)).count, '조건 충족 137개 중 137개 선정');
  const t = view(sel({ mode: 'top_n', value: 20 }, 137, 20));
  assert.deepEqual([t.label, t.count, t.weight], ['상위 20개', '조건 충족 137개 중 20개 선정', '같은 비중 · 각 5%']);
  assert.equal(view(sel({ mode: 'top_n', value: 20 }, 12, 12)).count, '조건 충족 12개 중 12개 선정', 'top N bounded by eligible names');
  assert.equal(view(sel({ mode: 'top_percent', value: 10 }, 137, 13)).label, '상위 10% (소수점 아래 버림)');
  assert.equal(view(sel({ mode: 'top_percent', value: 0.5 }, 137, 0)).weight, '선정 0개 · 비중 없음');
  // The engine's rules as words (Codex #473 select_provisional): order and ties, the percent arithmetic, a top N above the eligible
  // count selects only what is there (never filled), and what the contract does not carry is said, not made up.
  const p10 = view(sel({ mode: 'top_percent', value: 10 }, 137, 13));
  assert.equal(p10.rule, '순서: Q → G → V(없으면 뒤) → 회사 ID(동점은 회사 ID 순) · 조건 충족 137개 × 10% → 내림 13개');
  assert.equal(p10.shortfall, null);
  const n20 = view(sel({ mode: 'top_n', value: 20 }, 13, 13));
  assert.equal(n20.shortfall, '요청 20개 · 조건 충족 13개뿐 · 13개만 선정(종목 부족 · 채우지 않음)');
  assert.equal(view(sel({ mode: 'top_n', value: 20 }, 137, 20)).shortfall, null);
  assert.equal(view(sel({ mode: 'all', value: null }, 137, 137)).rule, '조건 충족 전부 · 순위로 자르지 않음');
  assert.match(n20.absent, /제외 사유\(기업별\)·중복 발행사·현금 처리는 이 엔진 계약에 없음/);
  assert.match(n20.scope, /화면 필터는 선정 모집단을 바꾸지 않음/);
  const v = view(sel({ mode: 'top_n', value: 3 }, 10, 3));
  assert.match(v.official, /공식 모델은 기존 N15 구간·TARGET 규칙 그대로/);
  assert.doesNotMatch(JSON.stringify(v), /0\.123|0\.0456|secret/, 'outcomes and realised returns are not in the view');
});
const badSel = [
  ['SELECTED_COUNT_MISMATCH', '$.n_selected', sel({ mode: 'top_percent', value: 10 }, 137, 14)],
  ['SELECTED_COUNT_MISMATCH', '$.n_selected', sel({ mode: 'top_n', value: 20 }, 137, 19)],
  ['POLICY_INVALID', '$.selection_policy.value', sel({ mode: 'top_n', value: 0 }, 137, 0)],
  ['POLICY_INVALID', '$.selection_policy.value', sel({ mode: 'top_percent', value: 120 }, 137, 137)],
  ['ENUM', '$.selection_policy.mode', sel({ mode: 'n15', value: 15 }, 137, 15)],
  ['KEY_MISSING', '$.weights', (() => { const x = sel(null, 5, 5); delete x.weights; return x; })()],
  ['WEIGHTS_NOT_EQUAL', '$.weights.SYNTHETIC:C000', (() => { const x = sel(null, 5, 5); x.weights['SYNTHETIC:C000'] = 0.3; return x; })()],
];
ok('selection refusals: count rule, policy values, unknown mode, weights', () => {
  for (const [code, at, x] of badSel) { const r = R.validateSelection(x); assert.deepEqual({ ok: r.ok, code: r.code, path: r.path }, { ok: false, code, path: at }, code); }
});
ok('source() answers NONE and makes no request', () => R.source().then((s) => { assert.equal(s.state, 'NONE'); assert.equal(s.coverage, null); assert.equal(s.selection, null); }));
// Codex #473 70672bc0 handoff (PORTFOLIO_LAB_HANDOFF_20261108.md): the seven public synthetic cases, read as the producer wrote them.
const H = require('../tests/fixtures/research_selection_handoff_v1_synthetic.json');
const hcase = (id) => copy(H.cases.find((c) => c.id === id).expected);
ok('#473 handoff: all seven synthetic cases are accepted with the producer\'s counts; 33.3333334 % of 3 → 1, 33.3333333 % → 0', () => {
  assert.equal(H.cases.length, 7);
  for (const c of H.cases) {
    const r = R.validateSelection(copy(c.expected));
    assert.equal(r.ok, true, c.id + ' ' + JSON.stringify(r));
    assert.equal(r.value.n_selected, c.expected.n_selected, c.id);
    assert.ok(r.value.details, c.id + ': selection_details read');
  }
  assert.equal(R.validateSelection(hcase('percent_boundary')).value.n_selected, 1);
  assert.equal(R.validateSelection(hcase('below_boundary')).value.n_selected, 0);
  // The same numbers through the rule itself: the stored percent's own decimal digits, no fixed precision.
  assert.deepEqual([R.floorPercent(3, 33.3333334), R.floorPercent(3, 33.3333333), R.floorPercent(3, 100), R.floorPercent(137, 10), R.floorPercent(1e9, 1e-7), R.floorPercent(7, 14.2857143)], [1, 0, 3, 13, 1, 1]);
  // The old consumer rounding (6 decimals) gave 0 for the boundary case: kept here as the counterexample it was.
  assert.equal(Math.floor(3 * Math.round(33.3333334 * 1e6) / 1e8), 0);
  // A count that does not follow the rule is still refused (the precision fix widens nothing).
  const bad = hcase('percent_boundary'); bad.n_selected = 0; bad.selected = []; bad.weights = null;
  assert.equal(R.validateSelection(bad).code, 'SELECTED_COUNT_MISMATCH');
  const bad2 = hcase('below_boundary'); bad2.n_selected = 1; bad2.selected = ['SYN:A']; bad2.weights = { 'SYN:A': 1 };
  assert.equal(R.validateSelection(bad2).code, 'SELECTED_COUNT_MISMATCH');
});
ok('#473 selection_details: exclusion reasons, cash, issuers and replay ids shown as written; the old "not in the contract" line goes', () => {
  const v = (id) => R.selectionView(R.validateSelection(hcase(id)).value);
  const m = v('missing');
  assert.equal(m.details.population, '원래 모집단 2개 · 조건 충족 1개 · 선정 1개');
  assert.match(m.details.excluded, /^제외 사유 · Q 없음 1 · G 없음 0 · 선정 한도 밖 0/);
  assert.equal(m.details.cash, '현금 비중 0%');
  assert.match(m.details.issuers, /^발행사 미연결 2개 · 같은 발행사 묶음 0개 · 같은 발행사의 여러 회사 ID는 현행 엔진대로 각각 유지/);
  assert.match(m.details.replay, /QGV 계산·시점\(PIT\)·성과 재현 아님/);
  assert.equal(m.absent, null);
  assert.match(v('empty').details.cash, /^선정 0개 · 포트폴리오 미형성 · 현금 비중 없음/);
  assert.match(v('percent_boundary').details.excluded, /선정 한도 밖 2/);
  // Without the sidecar the old line stays (nothing is made up on the screen).
  const plain = hcase('normal'); delete plain.selection_details;
  const pv = R.selectionView(R.validateSelection(plain).value);
  assert.equal(pv.details, null); assert.match(pv.absent, /이 엔진 계약에 없음/);
});
ok('#473 selection_details refusals: a sidecar that does not describe its own result refuses the whole input', () => {
  const at = '$.selection_details';
  const cases = [
    ['SCHEMA', at + '.schema_version', (d) => { d.schema_version = 'research-selection-details/2'; }],
    ['DETAILS_POLICY_MISMATCH', at + '.selection_policy', (d) => { d.selection_policy = { mode: 'top_percent', value: 33.3333333 }; }],
    ['DETAILS_RULE_UNKNOWN', at + '.percent_rule', (d) => { d.percent_rule = 'ROUND_6'; }],
    ['DETAILS_ROWS_MISMATCH', at + '.rows', (d) => { d.rows.pop(); }],
    ['DETAILS_SELECTED_MISMATCH', at + '.rows', (d) => { d.rows[1].selected = true; d.rows[1].exclusion_reasons = []; }],
    ['DETAILS_INVALID', at + '.rows[1].exclusion_reasons', (d) => { d.rows[1].exclusion_reasons = []; }],
    ['DETAILS_INVALID', at + '.rows[0].selected', (d) => { d.rows[0].exclusion_reasons = ['Q_MISSING']; }],
    ['DETAILS_PORTFOLIO_MISMATCH', at + '.portfolio.weights', (d) => { d.portfolio.weights['SYN:A'] = 0.9; }],
    ['DETAILS_INVALID', at + '.issuers', (d) => { d.issuers.security_identity_verified = true; }],
    ['DETAILS_INVALID', at + '.reproduction', (d) => { d.reproduction.result_hash = 'x'; }],
    ['DETAILS_INVALID', at + '.performance_verified', (d) => { d.performance_verified = true; }],
    ['KEY_UNKNOWN', at + '.outcomes', (d) => { d.outcomes = {}; }],
  ];
  for (const [code, path, f] of cases) { const x = hcase('percent_boundary'); f(x.selection_details); const r = R.validateSelection(x); assert.deepEqual({ code: r.code, path: r.path }, { code, path }, code + ' ' + path); }
  const e = hcase('empty'); e.selection_details.portfolio.cash_weight = 1; assert.equal(R.validateSelection(e).code, 'DETAILS_PORTFOLIO_MISMATCH', 'no all-cash portfolio is made for 0 selected');
});
console.log(JSON.stringify({ passed: true, checks: n }));
