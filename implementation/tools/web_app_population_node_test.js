'use strict';
// 검색·계산 범위 reader (web_app/population.js; owner 2026-11-05 follow-up item 3, Codex #482 current-expansion-research/1).
// Fixture: Codex's own evaluate() on its synthetic test inputs (tests/fixtures/current_expansion_research_v1_synthetic.json).
//  - Both synthetic cases pass and freeze; a partial roster has no full-market denominator, no coverage, no score or rank, and its
//    words say 미확정 with the reasons (never 0); the complete case keeps each stage apart (Q/G/V/세 축, ranked 0 without V).
//  - Refusals: wrong schema, official population replaced, a partial source shown as the whole market, coverage or a score without
//    an established population, counts that do not add up.
//  - Universe504 words from the company list and the public page rows.
const assert = require('node:assert/strict');
const path = require('node:path');
const P = require('../src/investment_system/product/web_app/population.js');
const F = require(path.join(__dirname, '../tests/fixtures/current_expansion_research_v1_synthetic.json'));
const fresh = (k) => JSON.parse(JSON.stringify(F.cases[k]));
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
  assert.deepEqual(v.rows.map((r) => [r.id, r.value]), [['searchable', '12 / 후보 12'], ['market', '12'], ['eligibility', '12 · 0 · 0'], ['financial', '11'],
    ['qgv', 'Q 11 · G 11 · V 0 · 세 축 0 / 12'], ['rank', '0 / 12']]);
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
