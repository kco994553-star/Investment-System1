'use strict';
// 3.5 기술 조건 필터 · QGV 결합 반례 (owner 2026-11-08 「공통 분류 계약 인수와 기술 필터 소비 오류 수정」, Codex #437 6714613662).
//  - tests/fixtures/technical_filter_join_main/cases.json: each case's expected result is Codex join_filtered_rows' OUTPUT
//    (tools/technical_filter_join_main_cases.py; pytest checks it), SHA-256 pinned. Main techScreen.joinRows + evaluate, kept the
//    way screen-tech-filter-live keep() keeps rows (input order, joined and PASS), gives exactly Codex's kept rows / ranks or code.
//  - IS2.classification.groupRows on Codex's roster (technical-filter-membership/1, #516 5b0ec88a) SMALLER than the universe: exactly
//    the group's members (both code rows of a shared issuer kept), issuer connected from the record with provenance, signal_day /
//    security_id untouched;
//    MEMBER_NOT_MAPPED when a member's row is missing; never the intersection with securities already keyed for the board;
//    out-of-group universe rows unchanged.
const assert = require('node:assert/strict');
const T = require('../src/investment_system/product/web_app/tech-screen.js');
const C = require('../src/investment_system/product/web_app/classification.js');
const X = require('./web_app_classification_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const J = X.joinCases(), B = T.validate(J.board);
const deep = (v) => JSON.parse(JSON.stringify(v));
// Main's screen path: joinRows, then the board's own conditions (evaluate), rows kept in their input order (keep()).
function main(board, c) {
  const j = T.joinRows(board, c.qgv_rows, { links: c.security_links, data_kind: 'SYNTHETIC' });
  if (!j.ok) return { ok: false, code: j.code };
  const r = T.evaluate(board, c.conditions);
  const kept = c.qgv_rows.filter((x) => j.keys.has(x.security_id) && r.rows.get(x.security_id).state === 'PASS');
  return { ok: true, kept: kept.map((x) => ({ id: x.id, issuer_id: Object.hasOwn(x, 'issuer_id') ? x.issuer_id : null, rank_of: x.rank.of, rank_official: x.rank.official, security_id: x.security_id, total: x.score.total })) };
}
const sortKeys = (o) => JSON.parse(JSON.stringify(o, (k, v) => (v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.keys(v).sort().map((x) => [x, v[x]])) : v)));

ok('pins: the case file (Codex output) unchanged; Codex board read by techScreen', () => {
  assert.equal(X.sha(X.JOIN_CASES_PATH), X.JOIN_CASES_SHA256);
  assert.equal(B.ok, true, JSON.stringify(B));
  assert.equal(Object.keys(J.cases).length, 11);
});
const board = B.value.boards[0].board;
for (const [name, c] of Object.entries(J.cases)) {
  ok('case ' + name + ': Main = Codex (' + (c.codex.ok ? 'join ' + c.codex.kept.map((r) => r.rank_official).join('·') : c.codex.code) + ')', () => {
    const before = deep(c);
    assert.deepEqual(sortKeys(main(board, c)), sortKeys(c.codex));
    assert.deepEqual(c, before, 'inputs never mutated');
  });
}
ok('f: out-of-group population rows keep their own scores and ranks; only the group rows are given to the join', () => {
  const c = J.cases.f2_group_rows_only, pop = c.population, group = new Set(c.qgv_rows.map((r) => r.security_id));
  const outside = pop.filter((r) => !group.has(r.security_id));
  assert.deepEqual(outside.map((r) => [r.rank.official, r.score.total]), [[2, 85], [5, 75]]);
  assert.equal(main(board, { ...c, qgv_rows: pop }).code, 'SECURITY_ID_NOT_IN_BOARD');
});

// ---------------- groupRows on Codex technical output (renamed to Universe504 codes)
const IT = 'INFORMATION_TECHNOLOGY', M = X.main(), codes = M.universe.codes;
const valid = (p) => { const r = C.validate(p); assert.equal(r.ok, true, JSON.stringify(r)); return r.value; };
const uni = (list) => list.map((code, i) => ({ id: code === 'NASDAQ:AMD' ? 'amd' : code, code, ticker: 'T' + i, issuer_id: null, signal_day: null, security_id: null, rank: { official: i + 1, of: list.length }, score: { total: 100 - i } }));
// The roster now comes from Codex technical-filter-membership/1 (#516 5b0ec88a): the group-join base renamed to page codes.
const GJ = M.universe.group_join;
ok('groupRows: the confirmed roster (3) smaller than the universe (20): exactly its members, issuer connected with provenance, keys untouched, universe unchanged', () => {
  const b = valid({ view: GJ.view, technical: GJ.technical }), bd = GJ.board, u = uni(codes), before = deep(u);
  const g = C.groupRowsWhy(bd, u, b);
  assert.equal(g.code, null); assert.deepEqual(g.rows.map((r) => r.code), GJ.codes);
  for (const r of g.rows) { const m = GJ.group_manifest.members.find((x) => x.company_id === r.code); assert.equal(r.issuer_id, m.issuer_id); assert.equal(r.issuer_connection.basis, 'VERIFIED_CLASSIFICATION_RECORD');
    assert.equal(r.signal_day, null); assert.equal(r.security_id, null); }
  assert.deepEqual(u, before, 'universe rows (including the 17 outside the group) unchanged');
  const keyed = u.map((r, i) => (i < 1 ? { ...r, signal_day: bd.signal_day, security_id: 'SYNTHETIC:SECURITY:' + i } : r));
  assert.equal(C.groupRowsWhy(bd, keyed, b).rows.length, 3, 'never the intersection');
  assert.equal(C.groupRowsWhy(bd, u.filter((r) => r.code !== GJ.codes[1]), b).code, 'MEMBER_NOT_MAPPED', 'a member\'s row missing');
  assert.equal(C.groupRows(bd, u), null, 'no loaded record set: null');
});
ok('groupRows: two code rows of one issuer both kept (never merged) — Codex case two_codes_one_issuer', () => {
  const F = require('../docs/research/common_classification/group-join-fixtures.json'), c = F.cases.find((x) => x.id === 'two_codes_one_issuer'), v = structuredClone(F.base);
  for (const [k, x] of c.sets) { let p = v; for (const q of k.slice(0, -1)) p = p[q]; p[k.at(-1)] = structuredClone(x); }
  const b = valid(v.bundle), g = C.groupRowsWhy(v.join.board, v.join.qgv_rows, b);
  assert.equal(g.code, null); assert.equal(g.rows.length, 3);
  assert.deepEqual(g.rows.filter((r) => r.issuer_id === 'SYNTHETIC:SHARED_ISSUER').map((r) => r.code), ['SYNTHETIC:COMPANY:0', 'SYNTHETIC:COMPANY:1']);
});
ok('groupRows: unknown identity / small sample kept apart', () => {
  const miss = valid(X.uTech('missing_security')), nine = valid(X.uTech('nine_valid'));
  const bm = miss.technical.groups.find((g) => g.sector_id === IT).board, b9 = nine.technical.groups.find((g) => g.sector_id === IT).board;
  // These Codex technical-case views have no universe context, so no /2 roster is made from them (the board states stay apart).
  assert.equal(C.groupRowsWhy(bm, uni(codes), miss).code, 'GROUP_UNIVERSE_CONTEXT_REQUIRED');
  assert.equal(C.groupRowsWhy(b9, uni(codes), nine).code, 'GROUP_UNIVERSE_CONTEXT_REQUIRED');
  assert.equal(T.metricState(bm, 'momentum_6m'), 'UNCONFIRMED'); assert.equal(T.metricState(b9, 'momentum_6m'), 'N_BELOW_10');
  const r9 = b9.metrics.momentum_6m;
  assert.ok(r9.median !== null && r9.rows.some((r) => r.rank !== null) && r9.rows.every((r) => r.decile === null), 'N<10: ranks and median, no decile');
  assert.ok(bm.metrics.momentum_6m.median === null && bm.metrics.momentum_6m.rows.every((r) => r.rank === null), 'unconfirmed: no rank, no median');
});
console.log(JSON.stringify({ passed: true, checks: n }));
