'use strict';
// QGV 모형 구분 (web_app/qgv-models.js; owner 2026-11-10 queue §2, 2026-11-11 「두 모형 실제 연결」 §3). The official model is always
// selectable; U1 / U2 / S1 exactly when the checked operating504 research delivery carries their board. A not-ready model never draws.
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../src/investment_system/product/web_app/qgv-models.js');

test('models, kinds apart; research candidates selectable only with their checked board', () => {
  assert.deepEqual(M.MODELS.map((m) => [m.id, m.kind, m.research]), [['OFFICIAL', 'OFFICIAL', false], ['U1', 'RESEARCH', true], ['U2', 'RESEARCH', true], ['S1', 'RESEARCH', true],
    ['U2-333', 'RESEARCH', true], ['U1-333', 'RESEARCH', true], ['S1-333', 'RESEARCH', true]]);
  for (const ready of [undefined, null, [], ['U2']]) {
    assert.equal(M.selectable('OFFICIAL', ready), true); assert.equal(M.selectable('U1', ready), false); assert.equal(M.resolve('U1', ready), 'OFFICIAL', 'a not-ready model never draws its own table');
  }
  const all = ['U1', 'U2', 'S1'];
  for (const id of all) { assert.equal(M.selectable(id, all), true); assert.equal(M.resolve(id, all), id); assert.equal(M.stateOf(id, all), 'READY'); }
  assert.equal(M.selectable('X', all), false); assert.equal(M.resolve('X', all), 'OFFICIAL'); assert.equal(M.stateOf('X', all), null);
  assert.equal(M.line(M.byId('U1')), '통합 연구 U1 · 연구 후보 · 핵심 Q1 · G1 · V2(축소 구성 · 3/3/3 아님) · 비공개 연구 결과 읽기 전 · 0. 기업 검색 → 비공개 분류 묶음 → 운영504 두 모형 결과 불러오기 뒤 선택 가능');
  assert.equal(M.line(M.byId('S1'), all), '섹터 연구 S1 · 연구 후보 · 핵심 Q2 · G1 · V2(축소 구성 · 3/3/3 아님) · 선택 가능');
  assert.equal(M.line(M.byId('OFFICIAL')), '공식 QGV · 공식 · 선택 가능');
  assert.ok(!M.MODELS.filter((m) => !m.pending).some((m) => /계산 연결 전/.test(M.line(m, all))), 'V or the total missing never puts a whole model at 계산 연결 전');
  assert.ok(Object.isFrozen(M.MODELS) && M.MODELS.every(Object.isFrozen));
  assert.ok(!Object.values(M.KIND).some((k) => /공격형|균형형|수비형/.test(k)), 'no investor-style names as model defaults');
});

test('the rules: no common scale, no stitched rank, no rank without a total, filters keep the originals, research never official', () => {
  const r = M.RULES.join('\n');
  assert.match(r, /평균·합산·비교 점수로 쓰지 않음/); assert.match(r, /섹터 점수를 이어 붙여 통합 순위를 만들지 않음/);
  assert.match(r, /총점이 없으면 총점 순위도 없음 · V·총점이 없어도 Q·G·개별 요소·결손 사유는 조회함/);
  assert.match(r, /필터는 원점수·원순위·분모·참조 N을 바꾸지 않음/); assert.match(r, /공식 QGV·포트폴리오 목표에 반영되지 않음/); assert.ok(!/TARGET/.test(r), 'DC-24: no TARGET word on the leaderboard');
});

// The 3/3/3 candidates (owner 2026-11-13 「QGV 3/3/3」): listed with Q3 · G3 · V3, never selectable before Codex's contract, even when a
// delivery names a board of that key; never worded as a recommendation; the old reduced cores are not called the 3/3/3 result.
test('3/3/3 candidates: listed apart, contract pending, never selectable, no recommendation wording', () => {
  const pend = M.MODELS.filter((m) => m.pending);
  assert.deepEqual(pend.map((m) => [m.id, m.label, m.core]), [['U2-333', '통합 연구 U2-333', 'Q3 · G3 · V3'], ['U1-333', '통합 연구 U1-333', 'Q3 · G3 · V3'], ['S1-333', '섹터 연구 S1-333', 'Q3 · G3 · V3']]);
  for (const m of pend) {
    assert.equal(M.stateOf(m.id, [m.id]), 'CONTRACT_PENDING'); assert.equal(M.selectable(m.id, [m.id]), false); assert.equal(M.resolve(m.id, [m.id]), 'OFFICIAL');
    assert.match(M.line(m), new RegExp('^' + m.label + ' · 연구 후보 · 핵심 Q3 · G3 · V3 · 계약 미전달 · 계산 연결 전 · Codex 3/3/3 계약·합성 예시 수령 전'));
    assert.ok(!/추천|성과 우수|최적|버핏/.test(m.note.replace('추천·성과 우수 아님', '')), m.id + ': no recommendation wording');
  }
  for (const id of ['U1', 'U2', 'S1']) assert.match(M.byId(id).core, /3\/3\/3 아님/, id + ': the reduced core is not the 3/3/3 composition');
});
