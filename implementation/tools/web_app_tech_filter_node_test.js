'use strict';
// Feature 3.5 기술 조건 필터 (owner 2026-11-03, 2026-11-04): web_app/tech-screen.js against Codex's technical-leaderboard/1 (#469).
//  - Codex's public synthetic fixture (tests/fixtures/technical_leaderboard_v1.json, byte-identical to #469 f1ca390a, sha256
//    pinned) is read unchanged: five boards, one per case, with signal_day · group_id labels.
//  - The owner's checks: a row equal to the median is ge_median true and gt_median false (interior_remainder_23 S011, the all-tied
//    negative_ties_10 momentum_3m); group membership unknown, valid N < 10 and "computed, zero matches" are told apart; the
//    fixture's own filter_example keeps exactly kept_security_ids; filtering never changes ranks, N, medians or deciles.
//  - A null adopted value is null on display even when raw_value exists (never filled from the raw arithmetic).
//  - The validator refuses the whole input at its first fault (schema, decimal strings, k, ranks, N, conditions, unconfirmed groups).
//  - The joined-board generator follows Codex's decile allocation (N=23 → 2,3,3,3,2,2,2,2,2,2) and passes the same validator.
const assert = require('node:assert/strict');
const T = require('../src/investment_system/product/web_app/tech-screen.js');
const X = require('./web_app_tech_filter_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const P = X.codex(), V = T.validate(P), B = V.ok ? Object.fromEntries(V.value.boards.map((b) => [b.id, b.board])) : {};
const C = (m, c) => ({ metric: m, condition: c });
const pass = (r) => [...r.rows].filter(([, x]) => x.state === 'PASS').map(([k]) => k).sort();

ok('Codex fixture: byte-identical to #469 f1ca390a and read unchanged', () => {
  assert.equal(X.codexSha(), X.CODEX_SHA256);
  assert.equal(V.ok, true, JSON.stringify(V));
  assert.deepEqual(V.value.boards.map((b) => b.id), ['interior_remainder_23', 'negative_ties_10', 'small_n_9', 'unknown_group', 'missing_volatility']);
  assert.equal(V.value.boards[0].label, '2018-02-16 · SYNTHETIC:GROUP · interior_remainder_23');
  assert.equal(V.value.data_kind, 'SYNTHETIC');
  assert.ok(Object.isFrozen(V.value.boards[0].board.metrics.momentum_6m.rows[0].conditions));
  assert.equal(T.validate(P.cases.interior_remainder_23).ok, true, 'one board alone');
  assert.equal(T.validate(Object.values(P.cases)).ok, true, 'an array of boards');
});
ok('median-equal rows: ge_median true, gt_median false (interior_remainder_23 S011; negative_ties_10 momentum_3m all tied)', () => {
  for (const m of X.METRICS) {
    const x = B.interior_remainder_23.metrics[m], row = x.rows.find((r) => r.value === x.median);
    assert.equal(row.security_id, 'SYNTHETIC:S011'); assert.equal(row.conditions.ge_median, true, m); assert.equal(row.conditions.gt_median, false, m);
  }
  const ge = T.evaluate(B.negative_ties_10, [C('momentum_3m', 'ge_median')]), gt = T.evaluate(B.negative_ties_10, [C('momentum_3m', 'gt_median')]);
  assert.deepEqual({ ...ge.counts }, { PASS: 10, FAIL: 0, UNKNOWN: 0 });
  assert.deepEqual({ ...gt.counts }, { PASS: 0, FAIL: 10, UNKNOWN: 0 }, 'computed, zero matches (no unknown)');
});
ok('states kept apart: group unconfirmed, valid N < 10, computed zero matches', () => {
  assert.deepEqual(X.METRICS.map((m) => T.metricState(B.unknown_group, m)), X.METRICS.map(() => 'UNCONFIRMED'));
  assert.deepEqual(X.METRICS.map((m) => T.metricState(B.small_n_9, m)), X.METRICS.map(() => 'N_BELOW_10'));
  assert.equal(T.metricState(B.interior_remainder_23, 'momentum_6m'), 'OK');
  const u = T.evaluate(B.unknown_group, [C('momentum_6m', 'ge_median')]);
  assert.deepEqual({ ...u.counts }, { PASS: 0, FAIL: 0, UNKNOWN: 2 });
  for (const [, x] of u.rows) assert.deepEqual(x.unknown, [{ metric: 'momentum_6m', reason: 'GROUP_MEMBERSHIP_UNCONFIRMED' }]);
  assert.equal(T.evaluate(B.unknown_group, [C('momentum_6m', 'gt_zero')]).counts.UNKNOWN, 0, 'an absolute condition is still decided');
  const s = T.evaluate(B.small_n_9, [C('momentum_6m', 'top_decile')]);
  assert.deepEqual({ ...s.counts }, { PASS: 0, FAIL: 0, UNKNOWN: 9 });
  for (const [, x] of s.rows) assert.equal(x.unknown[0].reason, 'N_BELOW_10');
  assert.equal(T.evaluate(B.small_n_9, [C('momentum_6m', 'ge_median')]).counts.UNKNOWN, 0, 'N < 10 keeps ranks and the median');
});
ok('the fixture filter_example keeps exactly kept_security_ids; missing volatility never passes exclude_D10', () => {
  const fe = P.filter_example, r = T.evaluate(B[fe.case], fe.conditions.map((c) => C(c.metric, c.condition)));
  assert.deepEqual(pass(r), [...fe.kept_security_ids].sort());
  const s0 = r.rows.get('SYNTHETIC:S000');
  assert.notEqual(s0.state, 'PASS');
  const v = T.evaluate(B.missing_volatility, [C('volatility_6m', 'exclude_D10')]).rows.get('SYNTHETIC:S000');
  assert.deepEqual(v.unknown, [{ metric: 'volatility_6m', reason: 'METRIC_NOT_AVAILABLE' }]);
});
ok('filtering never changes ranks, N, medians or deciles', () => {
  const snap = JSON.stringify(B);
  for (const b of Object.values(B)) for (const m of X.METRICS) for (const c of T.CHOICES[m]) T.evaluate(b, [C(m, c), C('momentum_6m', 'ge_median')]);
  assert.equal(JSON.stringify(B), snap);
});
ok('a null adopted value is never filled from raw_value', () => {
  const p = JSON.parse(X.codexText()), row = p.cases.unknown_group.metrics.dollar_volume_6m.rows[0];
  Object.assign(row, { value: null, raw_value: '987654.32', null_reasons: ['TRADE_SCOPE_UNCONFIRMED'] });
  row.conditions.gt_zero = null;
  const r = T.validate(p); assert.equal(r.ok, true, JSON.stringify(r));
  const got = r.value.boards.find((b) => b.id === 'unknown_group').board.metrics.dollar_volume_6m.rows[0];
  assert.equal(T.display('dollar_volume_6m', got), null);
  assert.equal(T.display('dollar_volume_6m', { value: '1025.00' }), '$1.0K');
  assert.equal(T.display('volatility_6m', { value: '0.8123' }), '0.81%/일');
  assert.equal(T.display('momentum_6m', { value: '-5.5' }), '−5.5%');
  assert.equal(T.META.volatility_6m.label, '6개월 일간 변동성(%, 비연율화)');
});
const refusals = [
  ['SCHEMA_VERSION', '$.cases.small_n_9.schema', (p) => { p.cases.small_n_9.schema = 'technical-leaderboard/2'; }],
  ['DECIMAL_INVALID', '$.cases.small_n_9.metrics.momentum_6m.rows[0].value', (p) => { p.cases.small_n_9.metrics.momentum_6m.rows[0].value = 8; }],
  ['K_MISMATCH', '$.cases.interior_remainder_23.metrics.momentum_6m.k', (p) => { p.cases.interior_remainder_23.metrics.momentum_6m.k = 3; }],
  ['RANK_INVALID', '$.cases.interior_remainder_23.metrics.momentum_6m.rows[1].rank', (p) => { p.cases.interior_remainder_23.metrics.momentum_6m.rows[1].rank = 1; }],
  ['N_VALID_MISMATCH', '$.cases.missing_volatility.metrics.volatility_6m.n_valid', (p) => { p.cases.missing_volatility.metrics.volatility_6m.n_valid = 12; }],
  ['CONDITION_MISMATCH', '$.cases.interior_remainder_23.metrics.momentum_3m.rows[11].conditions.gt_median',
    (p) => { const r = p.cases.interior_remainder_23.metrics.momentum_3m.rows.find((x) => x.security_id === 'SYNTHETIC:S011'); r.conditions.gt_median = true; }],
  ['GROUP_UNCONFIRMED_VALUES', '$.cases.unknown_group.metrics.momentum_6m', (p) => { p.cases.unknown_group.metrics.momentum_6m.median = '1'; }],
  ['DECILE_BELOW_10', '$.cases.small_n_9.metrics.momentum_6m.rows[0].decile', (p) => { const r = p.cases.small_n_9.metrics.momentum_6m.rows[0]; r.decile = 10; }],
  ['KEY_UNKNOWN', '$.cases.small_n_9.metrics.momentum_6m.rows[0].score', (p) => { p.cases.small_n_9.metrics.momentum_6m.rows[0].score = 1; }],
  ['ENUM', '$.cases.small_n_9.membership_status', (p) => { p.cases.small_n_9.membership_status = 'PARTIAL'; }],
];
ok('every rule refuses the whole input with its code and path', () => {
  for (const [code, at, change] of refusals) {
    const p = JSON.parse(X.codexText()); change(p);
    const r = T.validate(p);
    assert.deepEqual({ ok: r.ok, code: r.code, path: r.path }, { ok: false, code, path: at }, code);
  }
  assert.throws(() => T.evaluate(B.small_n_9, [C('volatility_6m', 'gt_zero')]), /FILTER_INVALID/);
});
ok('joined-board generator: Codex allocation, valid, market-down D10 negative, missing volatility', () => {
  const counts = (n) => { const c = {}; for (const d of X.deciles(n)) c[d] = (c[d] || 0) + 1; return [10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((d) => c[d]); };
  assert.deepEqual(counts(23), [2, 3, 3, 3, 2, 2, 2, 2, 2, 2]);
  assert.equal(X.deciles(9), null);
  const ids = Array.from({ length: 40 }, (_, i) => 'co' + String(i).padStart(2, '0')), b = X.joined(ids), r = T.validate(b);
  assert.equal(r.ok, true, JSON.stringify(r));
  const top = b.metrics.momentum_6m.rows.filter((x) => x.decile === 10);
  assert.ok(top.length && top.every((x) => x.value.startsWith('-')), 'D10 of a down market is negative');
  assert.equal(b.metrics.volatility_6m.rows.filter((x) => x.value === null).length, 2);
});
ok('source() answers NONE and makes no request', () => T.source().then((s) => { assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); }));
console.log(JSON.stringify({ passed: true, checks: n }));
