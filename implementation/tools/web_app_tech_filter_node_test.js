'use strict';
// Feature 3.5 기술 조건 필터 (owner 2026-11-03): the pure part of web_app/tech-screen.js in node.
//  - validate: the synthetic fixture passes (deep-frozen copy, the argument unchanged); each contract rule refuses the whole file
//    with its code and path (schema, zone, commit, status enum, duplicate day / group / row, unknown and missing keys, null without
//    reason, deciles off without reason, a decile for a group the row is not in, a decile in a group without deciles, a missing
//    decile, a decile without a value, decile range, n_valid > members, obs_days > expected_days, negative volatility / volume,
//    momentum <= -100%, non-finite numbers, invalid reason codes).
//  - evaluate: only the chosen group is judged; PASS / FAIL / UNKNOWN by the owner's rule (a condition needing a missing value or
//    decile is 판정 불가, never FAIL or PASS); the four owner states: negative D10 momentum passes top10 and fails gt0; missing
//    volatility makes "D10 제외" unknown; a group too small for deciles makes top10 unknown for every row while values and the
//    median stay; zero matches with no unknown; gte_median against the group median; adv only_d10 / exclude_d1; the file's
//    stats and deciles are never changed by evaluate (the same denominators before and after any filter).
//  - format / decileText / reasonText / condText / status, conditions() order and FILTER_INVALID, source() NONE without a request.
const assert = require('node:assert/strict');
const T = require('../src/investment_system/product/web_app/tech-screen.js');
const X = require('./web_app_tech_filter_fixture.js');

const COS = Array.from({ length: 60 }, (_, i) => ({ id: 'syn' + String(i).padStart(2, '0'), ticker: 'SYN' + i }));
const base = () => X.payload(COS);
const F = (o = {}) => ({ ...T.blank(), ...o, mom: { ...T.blank().mom, ...(o.mom || {}) } });
let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };

ok('fixture validates, copy is frozen and the argument unchanged', () => {
  const p = base(), before = JSON.stringify(p), r = T.validate(p);
  assert.equal(r.ok, true, JSON.stringify(r));
  assert.equal(JSON.stringify(p), before);
  assert.ok(Object.isFrozen(r.value) && Object.isFrozen(r.value.evaluations[0].rows[0].metrics.mom_6m.decile));
  assert.equal(r.value.evaluations.length, 2);
});

const refusals = [
  ['SCHEMA_VERSION', '$.schema_version', (p) => { p.schema_version = 'tech-screen-v1'; }],
  ['GENERATED_AT_ZONE', '$.generated_at', (p) => { p.generated_at = '2026-11-03T09:00:00'; }],
  ['SOURCE_COMMIT', '$.source_commit', (p) => { p.source_commit = 'D'.repeat(40); }],
  ['ENUM', '$.data_status', (p) => { p.data_status = 'DEMO'; }],
  ['KEY_UNKNOWN', '$.extra', (p) => { p.extra = 1; }],
  ['KEY_MISSING', '$.evaluations[0].stats', (p) => { delete p.evaluations[0].stats; }],
  ['AS_OF_DUPLICATE', '$.evaluations[1].as_of', (p) => { p.evaluations[1].as_of = p.evaluations[0].as_of; }],
  ['DATE_INVALID', '$.evaluations[0].as_of', (p) => { p.evaluations[0].as_of = '2026-02-30'; }],
  ['GROUP_DUPLICATE', '$.evaluations[0].groups[1].id', (p) => { p.evaluations[0].groups[1].id = 'U_A'; }],
  ['ID_INVALID', '$.evaluations[0].groups[0].id', (p) => { p.evaluations[0].groups[0].id = 'u-a'; }],
  ['ROW_DUPLICATE', '$.evaluations[0].rows[1].company_id', (p) => { p.evaluations[0].rows[1].company_id = p.evaluations[0].rows[0].company_id; }],
  ['GROUP_UNKNOWN', '$.evaluations[0].rows[0].groups[0]', (p) => { p.evaluations[0].rows[0].groups[0] = 'U_Z'; }],
  ['NULL_REASON_MISSING', '$.evaluations[0].rows[0].metrics.mom_3m.reason', (p) => { const x = p.evaluations[0].rows[0].metrics.mom_3m; x.value = null; x.reason = null; for (const g of Object.keys(x.decile)) x.decile[g] = null; }],
  ['DECILES_OFF_REASON', '$.evaluations[0].stats.U_SMALL.mom_6m.reason', (p) => { p.evaluations[0].stats.U_SMALL.mom_6m.reason = null; }],
  ['DECILE_GROUP', '$.evaluations[0].rows[1].metrics.mom_6m.decile.U_B', (p) => { p.evaluations[0].rows[1].metrics.mom_6m.decile.U_B = 3; }],
  ['DECILES_OFF_ROW', '$.evaluations[0].rows[0].metrics.mom_6m.decile.U_SMALL', (p) => { p.evaluations[0].rows[0].metrics.mom_6m.decile.U_SMALL = 4; }],
  ['DECILE_MISSING', '$.evaluations[0].rows[0].metrics.mom_6m.decile.U_A', (p) => { p.evaluations[0].rows[0].metrics.mom_6m.decile.U_A = null; }],
  ['DECILE_RANGE', '$.evaluations[0].rows[0].metrics.mom_6m.decile.U_A', (p) => { p.evaluations[0].rows[0].metrics.mom_6m.decile.U_A = 11; }],
  ['DECILE_WITHOUT_VALUE', '$.evaluations[0].rows[3].metrics.mom_12m.decile.U_A', (p) => { p.evaluations[0].rows[3].metrics.mom_12m.decile.U_A = 2; }],
  ['N_VALID_RANGE', '$.evaluations[0].stats.U_B.vol_6m.n_valid', (p) => { p.evaluations[0].stats.U_B.vol_6m.n_valid = 999; }],
  ['OBS_DAYS_RANGE', '$.evaluations[0].rows[0].metrics.mom_6m.obs_days', (p) => { p.evaluations[0].rows[0].metrics.mom_6m.obs_days = 500; }],
  ['RANGE', '$.evaluations[0].rows[0].metrics.vol_6m.value', (p) => { p.evaluations[0].rows[0].metrics.vol_6m.value = -0.1; }],
  ['RANGE', '$.evaluations[0].rows[0].metrics.mom_6m.value', (p) => { p.evaluations[0].rows[0].metrics.mom_6m.value = -1; }],
  ['REASON_INVALID', '$.evaluations[0].rows[3].metrics.mom_12m.reason', (p) => { p.evaluations[0].rows[3].metrics.mom_12m.reason = 'short history'; }],
  ['NUMBER_NOT_FINITE', '$.evaluations[0].rows[0].metrics.adv_6m.value', (p) => { p.evaluations[0].rows[0].metrics.adv_6m.value = Infinity; }],
  ['TYPE', '$', () => 'text'],
];
ok('every contract rule refuses the whole file with its code and path', () => {
  for (const [code, path, change] of refusals) {
    const p = base(), out = change(p), r = T.validate(out === undefined ? p : out);
    assert.deepEqual({ ok: r.ok, code: r.code, path: r.path }, { ok: false, code, path }, code + ' ' + path);
  }
});

const V = T.validate(base()).value, D0 = V.evaluations[0], D1 = V.evaluations[1], C = X.cases(base());
ok('owner state: market down, 6-month momentum D10 is negative and passes top10, fails gt0', () => {
  const pass = T.evaluate(D0, 'U_B', F({ mom: { '6m': 'top10' } }));
  const ids = [...pass.rows].filter(([, x]) => x.state === 'PASS').map(([id]) => id);
  assert.deepEqual(ids.sort(), [...C.d10].sort());
  for (const id of ids) assert.ok(D0.rows.find((r) => r.company_id === id).metrics.mom_6m.value < 0);
  const gt0 = T.evaluate(D0, 'U_B', F({ mom: { '6m': 'gt0' } }));
  assert.deepEqual({ ...gt0.counts }, { PASS: 0, FAIL: D0.rows.filter((r) => r.groups.includes('U_B')).length, UNKNOWN: 0 }, 'zero matches, no unknown');
});
ok('owner state: missing volatility makes "D10 제외" 판정 불가 (not pass, not fail); the D10-volatility row fails', () => {
  const r = T.evaluate(D0, 'U_B', F({ mom: { '6m': 'top10' }, vol: 'exclude_d10' }));
  assert.equal(r.rows.get(C.noVol[0]).state, 'UNKNOWN');
  assert.deepEqual(r.rows.get(C.noVol[0]).unknown, [{ metric: 'vol_6m', reason: 'SOURCE_MISSING' }]);
  assert.equal(r.rows.get(C.volTop[0]).state, 'FAIL');
  assert.deepEqual(r.rows.get(C.volTop[0]).fails, ['vol_6m']);
  assert.equal(r.counts.PASS, C.d10.length - 2);
  assert.equal(r.counts.UNKNOWN, 1);
  // A FAIL wins over an unknown on the same row.
  const both = T.evaluate(D0, 'U_B', F({ mom: { '6m': 'gt0' }, vol: 'exclude_d10' }));
  assert.equal(both.rows.get(C.noVol[0]).state, 'FAIL');
});
ok('owner state: values present, group too small for deciles: top10 unknown for every row, median still judged', () => {
  const st = D0.stats.U_SMALL.mom_6m;
  assert.equal(st.deciles, false); assert.equal(st.reason, 'GROUP_TOO_SMALL'); assert.equal(st.n_valid, 6); assert.notEqual(st.median, null);
  for (const id of C.small) { const row = D0.rows.find((x) => x.company_id === id); assert.notEqual(row.metrics.mom_6m.value, null); assert.equal(row.metrics.mom_6m.decile.U_SMALL, null); }
  const r = T.evaluate(D0, 'U_SMALL', F({ mom: { '6m': 'top10' } }));
  assert.deepEqual({ ...r.counts }, { PASS: 0, FAIL: 0, UNKNOWN: 6 });
  for (const [, x] of r.rows) assert.deepEqual(x.unknown, [{ metric: 'mom_6m', reason: 'GROUP_TOO_SMALL' }]);
  const m = T.evaluate(D0, 'U_SMALL', F({ mom: { '6m': 'gte_median' } }));
  assert.equal(m.counts.PASS, 3); assert.equal(m.counts.FAIL, 3);
});
ok('only the chosen group is judged; no filter = every member passes; adv rules; second day', () => {
  const all = T.evaluate(D1, 'U_A', T.blank());
  assert.deepEqual({ ...all.counts }, { PASS: D1.rows.length, FAIL: 0, UNKNOWN: 0 });
  const ub = T.evaluate(D1, 'U_B', T.blank());
  assert.equal(ub.rows.size, D1.groups.find((g) => g.id === 'U_B').members);
  const top = T.evaluate(D1, 'U_A', F({ adv: 'only_d10' })), d1 = T.evaluate(D1, 'U_A', F({ adv: 'exclude_d1' }));
  const want = (pred) => D1.rows.filter((r) => pred(r.metrics.adv_6m.decile.U_A)).length;
  assert.equal(top.counts.PASS, want((d) => d === 10)); assert.equal(d1.counts.PASS, want((d) => d !== 1));
  assert.ok(T.evaluate(D1, 'U_B', F({ mom: { '6m': 'gt0' } })).counts.PASS > 0, 'positive day');
  assert.throws(() => T.evaluate(D1, 'U_Z', T.blank()), /GROUP_UNKNOWN/);
});
ok('filters never change the file\'s stats or deciles (denominators fixed to the chosen group)', () => {
  const snap = JSON.stringify(D0);
  for (const f of [F({ mom: { '3m': 'gt0', '6m': 'top10', '12m': 'gte_median' }, vol: 'exclude_d10', adv: 'exclude_d1' }), F({ vol: 'only_d10' }), T.blank()])
    for (const g of ['U_A', 'U_B', 'U_SMALL']) T.evaluate(D0, g, f);
  assert.equal(JSON.stringify(D0), snap);
});
ok('12-month momentum missing for one row: gt0 / gte_median / top10 are unknown with its reason', () => {
  const id = D0.rows[3].company_id;
  for (const rule of ['gt0', 'gte_median', 'top10']) {
    const r = T.evaluate(D0, 'U_A', F({ mom: { '12m': rule } }));
    assert.deepEqual(r.rows.get(id).unknown, [{ metric: 'mom_12m', reason: 'PRICE_HISTORY_SHORT' }], rule);
  }
});
ok('conditions() order and FILTER_INVALID', () => {
  assert.deepEqual(T.conditions(F({ adv: 'only_d10', vol: 'exclude_d10', mom: { '12m': 'gt0', '3m': 'top10' } })).map((c) => c.metric), ['mom_3m', 'mom_12m', 'vol_6m', 'adv_6m']);
  assert.throws(() => T.conditions(F({ vol: 'top10' })), /FILTER_INVALID/);
  assert.throws(() => T.conditions(F({ mom: { '6m': 'only_d10' } })), /FILTER_INVALID/);
  assert.equal(T.active(T.blank()), false); assert.equal(T.active(F({ adv: 'exclude_d1' })), true);
});
ok('format / decileText / reasonText / condText / status', () => {
  assert.equal(T.format('mom_6m', -0.1234), '−12.3%'); assert.equal(T.format('mom_6m', 0.05), '+5.0%'); assert.equal(T.format('mom_3m', 0), '0.0%');
  assert.equal(T.format('vol_6m', 0.2345), '23.5%'); assert.equal(T.format('adv_6m', 98765432.1), '$98.8M'); assert.equal(T.format('adv_6m', 1.25e9), '$1.3B');
  assert.equal(T.format('adv_6m', 512), '$512'); assert.equal(T.format('mom_6m', null), null);
  assert.equal(T.decileText(10), 'D10'); assert.equal(T.decileText(null), null);
  assert.equal(T.reasonText('GROUP_TOO_SMALL'), '비교 그룹의 유효 종목이 적어 분위를 매기지 않음'); assert.equal(T.reasonText('NEW_CODE'), '사유 코드 미등록');
  assert.equal(T.condText('vol_6m', 'exclude_d10'), '6개월 변동성 · D10 제외 (가장 크게 흔들린 10% 빼기)');
  assert.ok(T.META.vol_6m.d10.includes('크게 흔들린')); assert.ok(T.META.adv_6m.d10.includes('거래 규모가 가장 큰'));
  assert.equal(T.status(V), '합성 데이터 · 시험용'); assert.equal(T.status({ data_status: 'REAL' }), '실데이터'); assert.equal(T.status(null), '기술 지표 자료가 아직 없습니다');
});
ok('source() answers NONE and makes no request', async () => {
  const before = globalThis.fetch; let called = 0; globalThis.fetch = () => { called++; return Promise.reject(new Error('no')); };
  return T.source().then((s) => { globalThis.fetch = before; assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); assert.equal(called, 0); });
});
console.log(JSON.stringify({ passed: true, checks: n }));
