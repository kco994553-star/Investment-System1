'use strict';
// 검색·계산 범위 reader (web_app/population.js; owner 2026-11-05 follow-up item 3, Codex #482 current-expansion-research/1).
// Fixture: Codex's own evaluate() on its synthetic test inputs (tests/fixtures/current_expansion_research_v1_synthetic.json).
//  - Both synthetic cases pass and freeze; a partial roster has no full-market denominator, no coverage, no score or rank, and its
//    words say 미확정 with the reasons (never 0); the complete case keeps each stage apart (Q/G/V/세 축, ranked 0 without V).
//  - Refusals: wrong schema, official population replaced, a partial source shown as the whole market, coverage or a score without
//    an established population, counts that do not add up.
//  - Universe504 words from the company list and the public page rows.
//  - #500 staged evidence (current-expansion-staged-evidence/1; tests/fixtures/current_expansion_staged_evidence_v1_synthetic.json
//    from Codex's link_and_evaluate on its synthetic test inputs): one row per stage with its own count and denominator and the basis
//    day S; a documentary type is not eligibility; the older result says NA for every stage row (not 0); stage promotions, unknown
//    states and join breaks refuse the whole file.
//  - #499 financial V candidate summary (tests/fixtures/financial_v_held_bridge_v1_summary_synthetic.json): one separate line,
//    never QGV coverage; financialSource() is NONE.
const assert = require('node:assert/strict');
const path = require('node:path');
const P = require('../src/investment_system/product/web_app/population.js');
const F = require(path.join(__dirname, '../tests/fixtures/current_expansion_research_v1_synthetic.json'));
const G = require(path.join(__dirname, '../tests/fixtures/current_expansion_staged_evidence_v1_synthetic.json'));
const H = require(path.join(__dirname, '../tests/fixtures/financial_v_held_bridge_v1_summary_synthetic.json'));
const fresh = (k) => JSON.parse(JSON.stringify(F.cases[k]));
const staged = (k) => JSON.parse(JSON.stringify(G.cases[k]));
const STAGE_IDS = ['issuer', 'type', 'identity', 'external', 'representative', 'cap'];
let n = 0; const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };

ok('synthetic cases pass and freeze', () => {
  for (const k of ['partial12', 'complete12_missing1']) { const r = P.validate(fresh(k)); assert.equal(r.ok, true, k + ' ' + JSON.stringify(r)); assert.ok(Object.isFrozen(r.value.rows[0])); }
});
ok('partial roster: 부분 목록, 미확정 with reasons, never 0, synthetic label', () => {
  const v = P.expansionView(P.validate(fresh('partial12')).value);
  assert.equal(v.synthetic, true); assert.equal(v.partial, true);
  const row = (id) => v.rows.find((r) => r.id === id);
  assert.equal(row('market').value, '미확정 · 완전한 IEX 목록 없음');
  assert.match(row('qgv').value, /^미확정 · 평가일의 완전한 IEX 거래 목록 미확인/);
  assert.match(row('rank').value, /^미확정 · /);
  assert.equal(row('eligibility').value, '0 · 0 · 12');
  assert.equal(row('searchable').value, '12 / 후보 12');
  assert.match(v.basis, /SEC 티커 관측 목록 \(검색용 · IEX 목록 아님\) · 부분 목록/);
});
ok('complete synthetic roster: stages apart, ranked 0 without V', () => {
  const v = P.expansionView(P.validate(fresh('complete12_missing1')).value);
  assert.equal(v.partial, false);
  const NA = 'NA · 증거 단계 평가 없음';
  assert.deepEqual(v.rows.map((r) => [r.id, r.value]), [['searchable', '12 / 후보 12'], ['market', '12'], ...STAGE_IDS.map((id) => [id, NA]),
    ['eligibility', '12 · 0 · 0'], ['financial', '11'], ['qgv', 'Q 11 · G 11 · V 0 · 세 축 0 / 12'], ['rank', '0 / 12']]);
  assert.equal(v.staged, false);
});
ok('#500 staged evidence: both synthetic cases pass; one row per stage, own count and denominator, basis day S', () => {
  for (const k of ['staged6_one_at_basis', 'staged6_none_at_basis']) { const r = P.validate(staged(k)); assert.equal(r.ok, true, k + ' ' + JSON.stringify(r)); }
  const row = (v, id) => v.rows.find((r) => r.id === id);
  const one = P.expansionView(P.validate(staged('staged6_one_at_basis')).value);
  assert.equal(one.staged, true); assert.equal(one.synthetic, true); assert.equal(one.partial, true);
  assert.deepEqual(one.rows.map((r) => r.id), ['searchable', 'market', ...STAGE_IDS, 'eligibility', 'financial', 'qgv', 'rank']);
  assert.deepEqual(one.rows.filter((r) => STAGE_IDS.includes(r.id)).map((r) => [r.label, r.value]), [
    ['재무 연결', '5 / 티커 관측 6'], ['증권 설명', '3 / 티커 관측 6'], ['평가일 동일 증권', '1 / 티커 관측 6 · S 2026-11-02'],
    ['외부 증권 ID', '확인 0 / 티커 관측 6'], ['대표 증권', '확정 0 / 발행사 5'], ['시총 적격성', 'NA · 미산출 6 / 티커 관측 6']]);
  assert.match(row(one, 'issuer').note, /카탈로그만 1 · 발행사 5/);
  assert.match(row(one, 'type').note, /적격 판정 아님 · 평가일 S 적용 1 · 설명 없음 3/);
  assert.match(row(one, 'identity').note, /^S 밖 문서 1 · 보관 설명만 1 · 증거 없음 3/);
  assert.match(row(one, 'external').note, /입력만 있음\(미검증\) 1 · 없음 5/);
  assert.match(row(one, 'cap').note, /^전 종류 같은 날 주식수 미확인 6 · 같은 날 원 주가 없음 6 · 주가–증권 연결 없음 6 · 주가 통화 미확인 6 · 주식수·주가 조정 척도 미확인 6$/);
  // A documentary type (even at S) is not eligibility; QGV and rank stay 미확정 on the partial subset.
  assert.equal(row(one, 'eligibility').value, '0 · 0 · 6');
  assert.match(row(one, 'qgv').value, /^미확정 · /); assert.match(row(one, 'rank').value, /^미확정 · /);
  assert.match(one.basis, /^평가일\(S\) 2026-11-02 · .*보유 재무 연결 부분 목록 \(IEX 목록 아님\) · 부분 목록$/);
  assert.match(one.version, /^current-expansion-staged-evidence\/1 · /);
  // The evaluated zero: no document covers S, so 평가일 동일 증권 is a real 0 (the stage was evaluated).
  const none = P.expansionView(P.validate(staged('staged6_none_at_basis')).value);
  assert.equal(row(none, 'identity').value, '0 / 티커 관측 6 · S 2026-11-02');
  assert.match(row(none, 'identity').note, /^S 밖 문서 2 · /);
  assert.equal(row(none, 'type').value, '3 / 티커 관측 6', 'archived descriptions still counted as 증권 설명');
});
ok('#500 refusals: promotion, unknown state, join and count breaks refuse the whole file', () => {
  const R = (i) => (x) => x.rows[i].stages;
  const cases = [
    [(x) => { x.schema_version = 'current-expansion-staged-evidence/2'; }, 'SCHEMA_VERSION', '$.schema_version'],
    [(x) => { delete x.evaluation; }, 'EVALUATION_MISSING', '$.evaluation'],
    [(x) => { x.evaluation.full_market_denominator = 6; }, 'PARTIAL_AS_FULL_MARKET', '$.evaluation.full_market_denominator'],
    [(x) => { x.evaluation.basis_date = '2026-11-03'; }, 'BASIS_DATE_MISMATCH', '$.evaluation.basis_date'],
    [(x) => { x.visibility = 'PUBLIC'; }, 'VISIBILITY', '$.visibility'],
    [(x) => { R(0)(x).representative.state = 'CONFIRMED'; }, 'STAGE_STATE', '$.rows[0].stages.representative.state'],
    [(x) => { R(0)(x).representative.value = true; }, 'STAGE_PROMOTED', '$.rows[0].stages.representative.value'],
    [(x) => { R(2)(x).same_security_at_basis.value = true; }, 'STAGE_PROMOTED', '$.rows[2].stages.same_security_at_basis.value'],
    [(x) => { R(2)(x).security_type_evidence.state = 'DOCUMENTED_AT_BASIS'; R(2)(x).security_type_evidence.current_type = 'COMMON'; x.counts.stages.security_type_evidence = { DOCUMENTED_ARCHIVED_TYPE: 1, DOCUMENTED_AT_BASIS: 2, UNKNOWN: 3 }; }, 'STAGE_PROMOTED', '$.rows[2].stages.security_type_evidence.current_type'],
    [(x) => { R(4)(x).same_security_at_basis.valid_to = '2026-11-01'; }, 'STAGE_PROMOTED', '$.rows[4].stages.same_security_at_basis.valid_from'],
    [(x) => { R(5)(x).external_fixed_id.value = 'SYNTHETIC-SECURITY-ID'; }, 'STAGE_PROMOTED', '$.rows[5].stages.external_fixed_id.value'],
    [(x) => { R(0)(x).market_cap_eligibility.issuer_market_cap_usd = 1; }, 'STAGE_PROMOTED', '$.rows[0].stages.market_cap_eligibility.value'],
    [(x) => { R(0)(x).market_cap_eligibility.reasons.push('NEW_BLOCKER'); }, 'STAGE_STATE', '$.rows[0].stages.market_cap_eligibility.reasons'],
    [(x) => { R(0)(x).valuation_inputs.price.value = 1; }, 'STAGE_PROMOTED', '$.rows[0].stages.valuation_inputs'],
    [(x) => { x.rows[1].evaluation_observation_id = '2'; }, 'JOIN_MISMATCH', '$.rows[1].evaluation_observation_id'],
    [(x) => { x.rows[1].original_observation_id = x.rows[0].original_observation_id; }, 'DUPLICATE_OBSERVATION_ID', '$.rows[1].original_observation_id'],
    [(x) => { x.rows[1].pipeline_result.eligibility = 'EXCLUDED'; }, 'JOIN_MISMATCH', '$.rows[1].pipeline_result.eligibility'],
    [(x) => { x.counts.stages.same_security_at_basis.DOCUMENTED_AT_BASIS = 0; x.counts.stages.same_security_at_basis.UNKNOWN = 4; }, 'COUNT_MISMATCH', '$.counts.stages.same_security_at_basis.DOCUMENTED_AT_BASIS'],
    [(x) => { x.counts.unique_issuers = 6; }, 'COUNT_MISMATCH', '$.counts.unique_issuers'],
  ];
  for (const [change, code, at] of cases) { const x = staged('staged6_one_at_basis'); change(x); const r = P.validate(x); assert.equal(r.ok, false, code); assert.deepEqual([r.code, r.path], [code, at], JSON.stringify(r)); }
  // An ELIGIBLE row cannot come out of documentary evidence: refuse even when the evaluation itself is consistent.
  const x = staged('staged6_one_at_basis'); x.evaluation.rows[4].eligibility = 'ELIGIBLE'; x.rows[4].pipeline_result.eligibility = 'ELIGIBLE';
  x.evaluation.counts.eligible = 1; x.evaluation.counts.unknown = 5;
  assert.deepEqual(P.validate(x), { ok: false, code: 'STAGE_PROMOTED', path: '$.evaluation.rows[4].eligibility' });
  // An EXCLUDED row needs identity on S: row 4 (document covers S) may be excluded, row 3 (document outside S) may not.
  const y = staged('staged6_one_at_basis'); y.evaluation.rows[3].eligibility = 'EXCLUDED'; y.rows[3].pipeline_result.eligibility = 'EXCLUDED';
  y.evaluation.counts.excluded = 1; y.evaluation.counts.unknown = 5;
  assert.deepEqual(P.validate(y), { ok: false, code: 'STAGE_PROMOTED', path: '$.evaluation.rows[3].eligibility' });
});
ok('#499 financial candidate line: summary only, separate wording, never QGV coverage; source NONE', async () => {
  const r = P.financialValidate(JSON.parse(JSON.stringify(H.report))); assert.equal(r.ok, true, JSON.stringify(r));
  assert.deepEqual(Object.keys(r.value), ['schema_version', 'valuation_date', 'source_ref', 'summary'], 'rows and receipts are not kept');
  assert.equal(r.value.source_ref, null, 'no source_ref in this file: kept as null, never guessed');
  const v = P.financialView(r.value);
  assert.equal(v.label, '금융업 후보 입력 (연구) · 공식 QGV와 별개');
  assert.equal(v.value, '분자 준비 2 · 같은 날 주가 1 · 기준 맞는 비율 1 / 금융업 코드 2');
  assert.match(v.note, /공식 QGV 커버리지·점수·순위 아님/);
  const bad = [
    [(x) => { x.summary.scored_joint_valid = 1; }, 'QGV_COVERAGE_CLAIMED'], [(x) => { x.summary.preset_totals = {}; }, 'QGV_COVERAGE_CLAIMED'],
    [(x) => { x.summary.operational_denominator = 2; }, 'OPERATIONAL_DENOMINATOR'], [(x) => { x.schema_version = 'financial-v-research/1'; }, 'SCHEMA_VERSION'],
    [(x) => { x.summary.financial_codes = 3; }, 'COUNT_MISMATCH'], [(x) => { x.summary.subtypes.DEPOSITORY_BANK.metrics.book_yield.ratio_valid = 2; }, 'COUNT_MISMATCH'],
    [(x) => { x.rows = []; }, 'COUNT_MISMATCH']];
  for (const [change, code] of bad) { const x = JSON.parse(JSON.stringify(H.report)); change(x); const q = P.financialValidate(x); assert.equal(q.ok, false); assert.equal(q.code, code, JSON.stringify(q)); }
  const s = await P.financialSource(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); assert.match(s.text, /^금융업 후보 입력 \(연구\) · 공식 QGV와 별개 · /);
});
// Codex #437 6680388919: the two faults reproduced with a /1.1 summary (e1f1f35d) whose BUSINESS_MODEL_UNRESOLVED subtype has
// primary_metric null. Regression on Codex's own fixture() run through #499 summarize (tests/fixtures/..._v1_1_summary_synthetic.json).
const H11 = require(path.join(__dirname, '../tests/fixtures/financial_v_held_bridge_v1_1_summary_synthetic.json'));
ok('#499 /1.1 summary with primary_metric null: accepted, unresolved kept in the denominator and named; nothing else widened', () => {
  assert.deepEqual(P.FIN_SCHEMAS, ['financial-v-held-bridge/1', 'financial-v-held-bridge/1.1']);
  const doc = JSON.parse(JSON.stringify(H11.report));
  assert.equal(doc.schema_version, 'financial-v-held-bridge/1.1');
  assert.equal(doc.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_metric, null);
  const r = P.financialValidate(doc); assert.equal(r.ok, true, JSON.stringify(r));
  const v = P.financialView(r.value);
  assert.equal(v.value, '분자 준비 1 · 같은 날 주가 0 · 기준 맞는 비율 0 / 금융업 코드 2', 'the unresolved code stays in the denominator');
  assert.equal(v.unresolved, 1);
  assert.equal(v.unresolved_text, '주 지표 미산출 1코드 · 사유 BUSINESS_MODEL_UNRESOLVED(업종 모델 미정) · 분모에 포함 · 다른 지표로 대체 안 함');
  assert.equal(v.null_reason, 'BUSINESS_MODEL_UNRESOLVED');
  const bad = [
    [(x) => { x.schema_version = 'financial-v-held-bridge/1.2'; }, 'SCHEMA_VERSION', '$.schema_version'],
    [(x) => { x.schema_version = 'financial-v-held-bridge/2'; }, 'SCHEMA_VERSION', '$.schema_version'],
    [(x) => { delete x.schema_version; }, 'SCHEMA_VERSION', '$.schema_version'],
    [(x) => { x.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_available = 1; x.summary.same_date_primary_available = 1; }, 'COUNT_MISMATCH', '$.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_available'],
    [(x) => { x.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_metric = 'no_such_metric'; }, 'PRIMARY_NULL_REASON', '$.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_metric'],
    [(x) => { delete x.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_metric; }, 'SUMMARY', '$.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.primary_metric'],
    [(x) => { delete x.summary.subtypes.BUSINESS_MODEL_UNRESOLVED.codes; }, 'COUNT_INVALID', '$.summary.subtypes.BUSINESS_MODEL_UNRESOLVED'],
    [(x) => { delete x.summary.operational_denominator; }, 'OPERATIONAL_DENOMINATOR', '$.summary.operational_denominator'],
    [(x) => { delete x.valuation_date; }, 'DATE_INVALID', '$.valuation_date'],
    [(x) => { x.source_ref = 'fixture-1'; }, 'SOURCE', '$.source_ref'],
    [(x) => { x.source_ref = 7; }, 'SOURCE', '$.source_ref']];
  for (const [change, code, at] of bad) { const x = JSON.parse(JSON.stringify(H11.report)); change(x); assert.deepEqual(P.financialValidate(x), { ok: false, code, path: at }); }
  for (const ref of ['SYNTHETIC:fixture-1', 'RETAINED:' + 'a'.repeat(64)]) {
    const x = JSON.parse(JSON.stringify(H11.report)); x.source_ref = ref; const q = P.financialValidate(x); assert.equal(q.ok, true);
    assert.equal(q.value.source_ref, ref); assert.match(P.financialView(q.value).note, ref.startsWith('SYNTHETIC:') ? / · 출처 합성$/ : / · 출처 보유 자료$/);
  }
});
// Owner 2026-11-06 (3rd): one table that keeps the three apart — a normal value, a normal null (the contract's reason) and a wrong
// input — for both supported versions; /1 files read exactly as before (compatibility).
ok('#499 three kinds: normal value · normal null (BUSINESS_MODEL_UNRESOLVED → 미산출) · wrong input; /1 compatibility kept', () => {
  const v10 = P.financialValidate(JSON.parse(JSON.stringify(H.report))), view10 = P.financialView(v10.value);
  assert.equal(v10.ok, true); assert.equal(v10.value.schema_version, 'financial-v-held-bridge/1');
  assert.equal(view10.value, '분자 준비 2 · 같은 날 주가 1 · 기준 맞는 비율 1 / 금융업 코드 2', '/1 value unchanged');
  assert.equal(view10.unresolved_text, null); assert.equal(view10.null_reason, null);
  const as11 = JSON.parse(JSON.stringify(H.report)); as11.schema_version = 'financial-v-held-bridge/1.1';
  assert.deepEqual(P.financialView(P.financialValidate(as11).value).value, view10.value, 'normal value: same reading under /1.1');
  // normal null, under both versions (the same summary contract)
  for (const ver of ['financial-v-held-bridge/1', 'financial-v-held-bridge/1.1']) {
    const x = JSON.parse(JSON.stringify(H11.report)); x.schema_version = ver; const r = P.financialValidate(x);
    assert.equal(r.ok, true, ver + ' ' + JSON.stringify(r));
    const w = P.financialView(r.value);
    assert.equal(w.null_reason, 'BUSINESS_MODEL_UNRESOLVED'); assert.match(w.unresolved_text, /^주 지표 미산출 1코드 · 사유 BUSINESS_MODEL_UNRESOLVED/);
    assert.doesNotMatch(w.value + w.note + w.unresolved_text, /(^| )0점|0으로/, 'never shown as zero');
  }
  // wrong inputs: unknown version, a required field missing, a wrong value — each refused whole with its code
  const U = 'BUSINESS_MODEL_UNRESOLVED', bad = [
    ['unknown version', (x) => { x.schema_version = 'financial-v-held-bridge/1.0.1'; }, 'SCHEMA_VERSION', '$.schema_version'],
    ['unknown version', (x) => { x.schema_version = 'FINANCIAL-V-HELD-BRIDGE/1.1'; }, 'SCHEMA_VERSION', '$.schema_version'],
    ['missing field', (x) => { delete x.summary.subtypes[U].primary_metric; }, 'SUMMARY', '$.summary.subtypes.' + U + '.primary_metric'],
    ['missing field', (x) => { delete x.summary.subtypes[U].primary_available; }, 'COUNT_INVALID', '$.summary.subtypes.' + U],
    ['missing field', (x) => { delete x.summary.same_date_primary_available; }, 'COUNT_INVALID', '$.summary.same_date_primary_available'],
    ['wrong value', (x) => { x.summary.subtypes.DEPOSITORY_BANK.primary_metric = null; }, 'PRIMARY_NULL_REASON', '$.summary.subtypes.DEPOSITORY_BANK.primary_metric'],
    ['wrong value', (x) => { x.summary.subtypes[U].primary_metric = 'book_yield'; }, 'PRIMARY_NULL_REASON', '$.summary.subtypes.' + U + '.primary_metric'],
    ['wrong value', (x) => { x.summary.subtypes[U].primary_metric = 0; }, 'PRIMARY_NULL_REASON', '$.summary.subtypes.' + U + '.primary_metric'],
    ['wrong value', (x) => { x.summary.subtypes.DEPOSITORY_BANK.primary_metric = 7; }, 'SUMMARY', '$.summary.subtypes.DEPOSITORY_BANK.primary_metric'],
    ['wrong value', (x) => { x.summary.subtypes[U].codes = -1; }, 'COUNT_INVALID', '$.summary.subtypes.' + U],
    ['wrong value', (x) => { x.summary.subtypes[U].primary_available = 1; x.summary.same_date_primary_available += 1; }, 'COUNT_MISMATCH', '$.summary.subtypes.' + U + '.primary_available'],
  ];
  assert.ok(H11.report.summary.subtypes.DEPOSITORY_BANK, 'fixture has one mapped subtype');
  for (const [kind, change, code, at] of bad) { const x = JSON.parse(JSON.stringify(H11.report)); change(x); assert.deepEqual(P.financialValidate(x), { ok: false, code, path: at }, kind); }
});
ok('refusals', () => {
  const cases = [
    ['partial12', (x) => { x.schema_version = 'current-expansion-research/2'; }, 'SCHEMA_VERSION'],
    ['partial12', (x) => { x.policy.official_universe_replaced = true; }, 'OFFICIAL_REPLACED'],
    ['partial12', (x) => { x.population_reasons = x.population_reasons.filter((r) => r !== 'COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED'); }, 'PARTIAL_AS_FULL_MARKET'],
    ['partial12', (x) => { x.full_market_denominator = 12; }, 'PARTIAL_AS_FULL_MARKET'],
    ['partial12', (x) => { x.coverage.Q = 11; }, 'COVERAGE_WITHOUT_POPULATION'],
    ['partial12', (x) => { x.rows[0].rank = 1; }, 'SCORE_WITHOUT_POPULATION'],
    ['partial12', (x) => { x.counts.unknown = 11; }, 'COUNT_MISMATCH'],
    ['complete12_missing1', (x) => { x.coverage.denominator = 13; }, 'COUNT_MISMATCH'],
    ['complete12_missing1', (x) => { x.coverage.ranked = 1; }, 'COUNT_MISMATCH'],
    ['complete12_missing1', (x) => { x.coverage.Q = null; }, 'COUNT_INVALID'],
    ['complete12_missing1', (x) => { x.visibility = 'PUBLIC'; }, 'VISIBILITY'],
  ];
  for (const [k, change, code] of cases) { const x = fresh(k); change(x); const r = P.validate(x); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); }
  assert.equal(P.validate(null).code, 'NOT_OBJECT');
});
ok('Universe504 words: list, totals, official ranks; missing page is 미확정', () => {
  const rows = [{ score: { total: 70 }, rank: { official: 1 } }, { score: { total: null }, rank: { official: null } }, { score: { total: 0 }, rank: { official: null } }];
  const v = P.universeView({ codes: ['A', 'B', 'C', 'D'], rows, asOf: '2026-11-02' });
  assert.deepEqual(v.rows.map((r) => r.value), ['4', '2 / 3', '1 / 3'], 'a real 0 total is a value');
  assert.match(v.basis, /공식 운영 모집단 · 고정 504 코드 · 점수 기준 2026-11-02/);
  assert.deepEqual(P.universeView({ codes: [], rows: null }).rows.map((r) => r.value), ['0', '미확정 · 점수 파일 없음', '미확정 · 점수 파일 없음']);
  assert.deepEqual(P.universeView({ codes: ['A'], rows: undefined }).rows.map((r) => r.value).slice(1), Array(2).fill('QGV 화면을 열면 셉니다 · 첫 화면은 점수 파일을 읽지 않음'), 'not read yet is not 미확정');
});
ok('source is NONE (no request) until a private connection is approved', async () => {
  const s = await P.source(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null);
});
console.log(JSON.stringify({ passed: true, checks: n }));
