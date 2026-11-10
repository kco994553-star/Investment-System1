'use strict';
// QGV 모형 구분 (web_app/qgv-models.js; owner 2026-11-10 「통합 QGV·섹터 QGV」 queue §2). Only a READY model can be chosen: today the
// official one; the integrated and sector research models carry their state and reason and never stand in for the official table.
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../src/investment_system/product/web_app/qgv-models.js');

test('three models, kinds apart; only the official one is selectable today', () => {
  assert.deepEqual(M.MODELS.map((m) => [m.id, m.kind, m.state]), [['OFFICIAL', 'OFFICIAL', 'READY'], ['INTEGRATED', 'RESEARCH_DEFAULT', 'NOT_CONNECTED'], ['SECTOR', 'RESEARCH_DEFAULT', 'RESULT_NOT_DELIVERED']]);
  assert.equal(M.selectable('OFFICIAL'), true); assert.equal(M.selectable('INTEGRATED'), false); assert.equal(M.selectable('SECTOR'), false); assert.equal(M.selectable('X'), false);
  assert.equal(M.resolve('INTEGRATED'), 'OFFICIAL', 'a not-ready model never draws its own (empty) table'); assert.equal(M.resolve('OFFICIAL'), 'OFFICIAL');
  assert.equal(M.line(M.byId('INTEGRATED')), '통합 QGV · 연구 기본값 · 계산 연결 전 · 공통 핵심 요소 preset·결과 계약 수령 전');
  assert.equal(M.line(M.byId('OFFICIAL')), '공식 QGV · 공식 · 선택 가능');
  assert.ok(Object.isFrozen(M.MODELS) && M.MODELS.every(Object.isFrozen));
  assert.ok(!Object.values(M.KIND).some((k) => /공격형|균형형|수비형/.test(k)), 'no investor-style names as model defaults');
});

test('the rules: no common scale, no stitched rank, filters keep the originals, research never official', () => {
  const r = M.RULES.join('\n');
  assert.match(r, /평균·합산·비교 점수로 쓰지 않음/); assert.match(r, /섹터 점수를 이어 붙여 통합 순위를 만들지 않음/);
  assert.match(r, /필터는 원점수·원순위·분모·참조 N을 바꾸지 않음/); assert.match(r, /공식 QGV·포트폴리오 목표에 반영되지 않음/); assert.ok(!/TARGET/.test(r), 'DC-24: no TARGET word on the leaderboard');
});
