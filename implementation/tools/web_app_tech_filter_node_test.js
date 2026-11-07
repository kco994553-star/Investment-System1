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
//  - The QGV join (owner audit 2026-11-07, joinRows): only a verified same evaluation date + same security, one to one. Refused:
//    QGV date missing, another date, no map (today's contract; a board whose security ids equal row ids/codes no longer joins),
//    the same ticker / listing key for another company or outside its validity, share classes not told apart, a missing mapping,
//    a duplicate mapping either way, a bare ticker as listing key. Joined only with a synthetic verified map.
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
// ---- the QGV join: synthetic Universe rows (listing key = code, company id = id; GOOGL/GOOG two listings of one issuer)
const D = '2026-10-13', U = [...Array.from({ length: 12 }, (_, i) => ({ id: 'co' + String(i).padStart(2, '0'), code: 'NYSE:CO' + String(i).padStart(2, '0') })),
  { id: 'googl', code: 'NASDAQ:GOOGL' }, { id: 'NASDAQ:GOOG', code: 'NASDAQ:GOOG' }];
const SEC = U.map((_, i) => 'SYNTHETIC:FIX' + String(i).padStart(2, '0')), JB = X.joined(SEC, { signal_day: D });
const GOOD = U.map((r, i) => [SEC[i], r.id, r.code]);
const J = (opts, board = JB, rows = U) => T.joinRows(board, rows, { day: D, ...opts });
const edit = (fn) => { const e = GOOD.map((x) => [...x]); fn(e); return X.securityMap(e); };
ok('join: a verified same-date, same-security map joins one to one (share classes told apart)', () => {
  assert.equal(T.validate(JB).ok, true);
  const j = J({ map: X.securityMap(GOOD) });
  assert.equal(j.ok, true, JSON.stringify(j));
  assert.deepEqual([...j.pairs], U.map((r, i) => [r.id, SEC[i]]));
  assert.equal(j.pairs.get('googl'), SEC[12]); assert.equal(j.pairs.get('NASDAQ:GOOG'), SEC[13]);
  assert.equal(T.joinText(j), null);
  // a security mapped to no Universe504 listing (explicit null) is simply not joined; the rest still are
  const k = J({ map: edit((e) => { e[0][1] = null; e[0][2] = null; }) });
  assert.equal(k.ok, true); assert.equal(k.pairs.has('co00'), false); assert.equal(k.pairs.size, U.length - 1);
});
ok('join refused: QGV evaluation date missing or different from signal_day', () => {
  const map = X.securityMap(GOOD);
  for (const day of [null, undefined, '', '2026-10-13T00:00:00Z']) assert.equal(T.joinRows(JB, U, { day, map }).code, 'QGV_DATE_MISSING', String(day));
  const j = T.joinRows(JB, U, { day: '2026-10-14', map });
  assert.deepEqual({ ...j }, { ok: false, code: 'DATE_MISMATCH', board_day: D, qgv_day: '2026-10-14' });
  assert.equal(T.joinText(j), '평가일 불일치 · 보드 2026-10-13 · QGV 2026-10-14');
  assert.equal(T.joinText(T.joinRows(JB, U, { day: null, map })), T.JOIN_TEXT.QGV_DATE_MISSING);
});
ok('join refused: no security map (today), even when board security ids equal the rows\' ids or codes', () => {
  assert.equal(J({ map: null }).code, 'MAPPING_CONTRACT_MISSING');
  for (const ids of [U.map((r) => r.id), U.map((r) => r.code)]) assert.equal(J({ map: null }, X.joined(ids, { signal_day: D })).code, 'MAPPING_CONTRACT_MISSING');
  assert.ok(T.joinText(J({})).startsWith('증권 매핑 계약 없음'));
  for (const bad of [{}, { schema: 'tech-qgv-security-map/1', entries: [] }, { ...X.securityMap(GOOD), extra: 1 }, edit((e) => { e[0][3] = '2026-13-01'; }),
    edit((e) => { e[0][4] = '2019-01-01'; }), edit((e) => { e[0][2] = null; })]) assert.equal(J({ map: bad }).code, 'MAPPING_INVALID', JSON.stringify(bad).slice(0, 80));
});
ok('join refused: the same ticker / listing key for another security', () => {
  // the listing key exists, but the map names another company: a reused ticker is not this row's security
  const j = J({ map: edit((e) => { e[3][1] = 'old-co03'; }) });
  assert.deepEqual({ ...j }, { ok: false, code: 'IDENTITY_MISMATCH', security: SEC[3], listing_key: 'NYSE:CO03' });
  assert.equal(T.joinText(j), T.JOIN_TEXT.IDENTITY_MISMATCH);
  // the entry for that listing ended before the evaluation date (an earlier holder of the ticker): no mapping on that day
  assert.deepEqual({ ...J({ map: edit((e) => { e[3][3] = '2001-01-01'; e[3][4] = '2015-12-31'; }) }) }, { ok: false, code: 'MAPPING_MISSING', count: 1 });
  // a bare ticker (or the row id) as listing key is not a listing key
  assert.equal(J({ map: edit((e) => { e[3][2] = 'CO03'; }) }).code, 'MAPPING_MISSING');
  assert.equal(J({ map: edit((e) => { e[3][2] = 'co03'; }) }).code, 'MAPPING_MISSING');
});
ok('join refused: share classes not told apart (GOOGL vs GOOG; BRK.A vs BRK.B)', () => {
  // both class securities mapped to one listing → ambiguous
  assert.equal(J({ map: edit((e) => { e[13][1] = 'googl'; e[13][2] = 'NASDAQ:GOOGL'; }) }).code, 'MAPPING_AMBIGUOUS');
  // the issuer's id with the other class's listing → not that row's security
  assert.equal(J({ map: edit((e) => { e[13][1] = 'googl'; }) }).code, 'IDENTITY_MISMATCH');
  // BRK.A on the board, only BRK.B in the Universe: the map must say which; mapping BRK.A to the BRK.B listing is refused
  const rows = [...U, { id: 'NYSE:BRK.B', code: 'NYSE:BRK.B' }], b = X.joined([...SEC, 'SYNTHETIC:BRKA'], { signal_day: D });
  assert.equal(J({ map: X.securityMap([...GOOD, ['SYNTHETIC:BRKA', 'NYSE:BRK.A', 'NYSE:BRK.B']]) }, b, rows).code, 'IDENTITY_MISMATCH');
  assert.equal(J({ map: X.securityMap([...GOOD, ['SYNTHETIC:BRKA', 'NYSE:BRK.A', 'NYSE:BRK.A']]) }, b, rows).code, 'MAPPING_MISSING');
  const k = J({ map: X.securityMap([...GOOD, ['SYNTHETIC:BRKA', null, null]]) }, b, rows);
  assert.equal(k.ok, true); assert.equal(k.pairs.has('NYSE:BRK.B'), false, 'BRK.B is not joined to the BRK.A security');
});
ok('join refused: a missing mapping (no entry, or a board row with no fixed security id)', () => {
  const j = J({ map: edit((e) => { e.splice(5, 1); }) });
  assert.deepEqual({ ...j }, { ok: false, code: 'MAPPING_MISSING', count: 1 });
  assert.equal(T.joinText(j), '매핑 없음 · 증권 1개');
  const p = JSON.parse(JSON.stringify(JB));
  for (const m of X.METRICS) p.metrics[m].rows.find((r) => r.security_id === SEC[2]).security_id = null;
  assert.equal(T.validate(p).ok, true);
  assert.equal(J({ map: X.securityMap(GOOD) }, p).code, 'MAPPING_MISSING');
  assert.equal(J({ map: X.securityMap(GOOD) }, JB, U.filter((r) => r.id !== 'co07')).code, 'MAPPING_MISSING', 'listing key not among the rows');
});
ok('join refused: a duplicate mapping (one security → two rows, two securities → one row, one row twice in the Universe)', () => {
  assert.equal(J({ map: X.securityMap([...GOOD, [SEC[4], 'co05', 'NYSE:CO05']]) }).code, 'MAPPING_AMBIGUOUS', 'one security, two rows');
  assert.equal(J({ map: X.securityMap([...GOOD, [SEC[4], 'co04', 'NYSE:CO04']]) }).code, 'MAPPING_AMBIGUOUS', 'the same entry twice');
  assert.equal(J({ map: edit((e) => { e[6][1] = 'co07'; e[6][2] = 'NYSE:CO07'; }) }).code, 'MAPPING_AMBIGUOUS', 'two securities, one row');
  assert.equal(J({ map: X.securityMap([...GOOD, ['SYNTHETIC:OTHER', 'co08', 'NYSE:CO08']]) }).code, 'MAPPING_AMBIGUOUS', 'a second security on that day');
  assert.equal(J({ map: X.securityMap(GOOD) }, JB, [...U, { id: 'co09-b', code: 'NYSE:CO09' }]).code, 'MAPPING_AMBIGUOUS', 'two rows with one listing key');
  // validity periods that do not overlap are not duplicates
  const k = J({ map: X.securityMap([...GOOD.map((x, i) => (i === 4 ? [...x, '2021-01-01'] : x)), [SEC[4], 'co05', 'NYSE:CO05', '2001-01-01', '2020-12-31']]) });
  assert.equal(k.ok, true, JSON.stringify(k));
});
ok('source() answers NONE with no security map and makes no request', () => T.source().then((s) => { assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); assert.equal(s.map, null); }));
console.log(JSON.stringify({ passed: true, checks: n }));
