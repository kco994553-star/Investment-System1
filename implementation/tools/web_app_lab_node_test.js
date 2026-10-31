'use strict';
// New frontend · feature 9 Lab (web_app/screen-lab-live.js, the part after the first paint; screen-lab.js is its skeleton): the pure
// parts, against the common base's IS2.lab (web_app/lab.js) and the old forward-validation reader (web_assets/forward-validation.js).
//  - panelPlan(source, IS2.lab.validate): NONE → NOT_READY / LOGIN_REQUIRED by the private state; OK → READY with the validator's
//    deep-frozen copy only when the whole file is accepted, else ERROR with exactly the validator's code (every invalid variant of
//    tools/lab_backtest_fixture.js); ERROR → the source's fixed code (anything else → LAB_SOURCE_FAILED); unknown → ERROR. The
//    screen never checks a field itself: the plan comes from validate's answer alone.
//  - metricRows: the seven metrics in the contract's order, ratios as %, sharpe 2 decimals, a null metric = IS2.lab.nullText
//    (– and its reason), a real 0 stays 0.00 % (cash benchmark), never 0 for a null.
//  - curveGeometry: months in the file's order (x strictly increasing), both lines start on the 100 line, the last point maps back
//    to the last value, one scale holds 100 and every value, fewer than 2 points → no curve, a value that is not a finite number
//    > 0 throws (backstop: the validator refused it already).
//  - statusKind: a solid chip only for REAL inputs with a recorded check and a point-in-time universe.
//  - ledgerTable / evaluationLabel / evidenceView: the old forward-validation.js table, evaluation words and operating evidence
//    on synthetic ledgers (tools/web_app_lab_fixture.js): newest first, v2 before v1, observation basis counts, NA as — with its
//    reason, segments never chained, missing days never filled.
//  - The 9.1.1–9.1.6 names equal the tree's (screen-tree-live.js); the file reads one public file, sends and stores nothing.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const R = require('./web_app_reuse');
const F = require('./lab_backtest_fixture.js');
const X = require('./web_app_lab_fixture.js');

const fresh = (n) => { delete require.cache[require.resolve(R.newPath(n))]; return R.requireNew(n); };
const M = fresh('screen-lab-live.js'), L = fresh('lab.js'), P = fresh('private.js');
const FV = (() => { delete require.cache[require.resolve(R.oldPath('forward-validation.js'))]; return R.requireOld('forward-validation.js'); })();
const plain = (x) => JSON.parse(JSON.stringify(x));
const S = X.sources(F);
const pct = (v) => (v * 100).toFixed(2) + '%';
// engines.js virtual.forward() on a validated ledger (the same mapping, P1), for the table and the evidence.
function forwardOf(p) {
  const primary = p.schema_version === 2 ? FV.V2_VERSION : FV.VERSION, line = (r) => ({ date: r.date, version: r.version, state: r.state, summary: FV.qgSummary(r), evaluation: FV.rowEvaluation(r) });
  return plain({ state: 'LOADED', reason: null, status: p.status, as_of: p.as_of, start_date: p.start_date, primary, rows: p.versions[primary].map(line),
    comparison: p.schema_version === 2 ? p.versions[FV.VERSION].map(line) : [], segments: FV.segments(p.versions[primary]), evidence: FV.evidence(p) });
}
const ledger = (make) => FV.validate(plain(make()));

/* ---------------------------------------------------------------- 9.1 private panel plan */
test('panelPlan: NONE follows the private state; the real source today is NOT_READY', async () => {
  const src = await L.create({ privateArea: P.create() }).source();
  assert.deepEqual(plain(M.panelPlan(src, L.validate)), { state: 'NOT_READY', code: null, value: null });
  assert.equal(M.panelPlan(S.login, L.validate).state, 'LOGIN_REQUIRED');
  assert.equal(M.panelPlan({ ...S.login, private: 'PRIVATE_NOT_READY' }, L.validate).state, 'NOT_READY');
  assert.equal(M.panelPlan({ ...S.login, private: 'SOMETHING_ELSE' }, L.validate).state, 'NOT_READY', 'an unknown private state is never shown as signed in');
});

test('panelPlan: OK draws only a whole accepted file (the validator\'s frozen copy), else ERROR with exactly its code', () => {
  for (const [name, make] of F.valid) {
    const payload = make(), r = M.panelPlan({ state: 'OK', payload }, L.validate), want = L.validate(payload);
    assert.equal(r.state, 'READY', name); assert.deepEqual(plain(r.value), plain(want.value), name);
    assert.ok(Object.isFrozen(r.value) && Object.isFrozen(r.value.runs), name + ': deep-frozen copy'); assert.notEqual(r.value, payload, name + ': not the argument');
  }
  for (const [name, code, , make] of F.invalid) {
    const r = M.panelPlan({ state: 'OK', payload: make() }, L.validate);
    assert.deepEqual(plain(r), { state: 'ERROR', code, value: null }, name);
  }
  for (const [k, { src, code }] of Object.entries(S.refused)) assert.deepEqual(plain(M.panelPlan(src, L.validate)), { state: 'ERROR', code, value: null }, k);
  // Only validate's answer decides: a spy sees the payload once and its verdict is used as given.
  const seen = []; const spy = (p) => { seen.push(p); return { ok: false, code: 'CURVE_ORDER', path: '$' }; };
  assert.deepEqual(plain(M.panelPlan(S.normal, spy)), { state: 'ERROR', code: 'CURVE_ORDER', value: null }); assert.equal(seen.length, 1); assert.equal(seen[0], S.normal.payload);
  assert.equal(M.panelPlan(S.normal, () => ({ ok: false, code: 'see https://x' })).code, 'INVALID', 'a code that is not fixed is not shown');
  assert.equal(M.panelPlan(S.normal, () => null).state, 'ERROR');
});

test('panelPlan: ERROR keeps a fixed code only; anything unknown is an ERROR, never a result', () => {
  assert.deepEqual(plain(M.panelPlan(S.notFound, L.validate)), { state: 'ERROR', code: 'LAB_RESULT_NOT_FOUND', value: null });
  for (const code of ['lab_404', 'HTTP 404', 'https://x', '', null, 404]) assert.equal(M.panelPlan({ state: 'ERROR', code }, L.validate).code, 'LAB_SOURCE_FAILED', String(code));
  for (const src of [null, undefined, 'OK', [S.normal], 7]) assert.deepEqual(plain(M.panelPlan(src, L.validate)), { state: 'ERROR', code: 'LAB_SOURCE_INVALID', value: null }, String(src));
  for (const state of ['READY', 'SIGNED_IN', 'LOADING', undefined]) assert.equal(M.panelPlan({ state, payload: F.payload() }, L.validate).code, 'LAB_SOURCE_UNKNOWN', String(state));
});

/* ---------------------------------------------------------------- metrics, curve, status */
test('metricRows: contract order, % and 2 decimals, a null is nullText (– and its reason), a real 0 stays 0.00 %', () => {
  const p = L.validate(F.payload()).value, [pilot, synth] = p.runs;
  for (const run of [pilot, synth]) {
    const rows = M.metricRows(run, { metrics: L.METRICS, nullText: L.nullText });
    assert.deepEqual(rows.map((r) => r.key), [...L.METRICS]);
    for (const r of rows) {
      const v = run.metrics[r.key];
      if (v === null) { assert.equal(r.na, true); assert.equal(r.value, null); assert.equal(r.text, L.nullText(run, r.key)); assert.match(r.text, /^– · \S/); }
      else { assert.equal(r.na, false); assert.equal(r.text, r.key === 'sharpe' ? v.toFixed(2) : pct(v)); }
      assert.ok(r.label && r.label !== r.key, r.key + ' has a Korean label');
    }
  }
  assert.equal(M.metricRows(pilot, { metrics: L.METRICS, nullText: L.nullText }).find((r) => r.key === 'sharpe').text, '– · 무위험 수익률 기준 미정 (시험용)');
  const none = L.validate(S.allNull.payload).value.runs[0], rows = M.metricRows(none, { metrics: L.METRICS, nullText: L.nullText });
  assert.ok(rows.every((r) => r.na && r.value === null && r.text === '– · 시험용 · 계산 안 함'), 'every null metric shows – and its reason');
  assert.ok(rows.every((r) => !/\d/.test(r.text)), 'no number at all for null metrics (never 0)');
  const zero = { ...pilot, metrics: { ...pilot.metrics, benchmark_cagr: 0 } };
  assert.equal(M.metricRows(zero, { metrics: L.METRICS, nullText: L.nullText }).find((r) => r.key === 'benchmark_cagr').text, '0.00%', 'a real 0 (cash benchmark) is a value');
});

test('curveGeometry: file order on x, both lines start on the 100 line, the last point maps back, one scale, refusals', () => {
  const runs = [...L.validate(F.payload()).value.runs, ...L.validate(S.fourRuns.payload).value.runs];
  const pts = (d) => [...d.matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)].map((m) => [Number(m[1]), Number(m[2])]);
  for (const run of runs) {
    const c = run.equity_curve, g = M.curveGeometry(c);
    assert.ok(g, run.id); assert.equal(g.xs.length, c.length);
    for (let i = 1; i < g.xs.length; i++) assert.ok(g.xs[i] > g.xs[i - 1], run.id + ': x strictly increasing (the file\'s month order)');
    const s = pts(g.s), b = pts(g.b);
    assert.equal(s.length, c.length); assert.equal(b.length, c.length);
    assert.deepEqual([s[0][1], b[0][1]], [g.base, g.base], run.id + ': both lines start on the 100 line');
    assert.ok(g.lo <= 100 && g.hi >= 100 && c.every((p) => p.strategy >= g.lo && p.strategy <= g.hi && p.benchmark >= g.lo && p.benchmark <= g.hi), run.id + ': one scale for all values');
    const back = (y) => g.hi - (y - g.pad) / (g.h - 2 * g.pad) * (g.hi - g.lo), tol = (g.hi - g.lo) / (g.h - 2 * g.pad) * 0.01;
    assert.ok(Math.abs(back(s[s.length - 1][1]) - c[c.length - 1].strategy) <= tol, run.id + ': the last strategy point maps back to its value');
    assert.equal(g.last, c[c.length - 1]); assert.equal(g.first, c[0]);
    if (run.metrics.total_return !== null) assert.ok(Math.abs(g.last.strategy / 100 - 1 - run.metrics.total_return) <= L.TOL.total, run.id + ': final value consistent with total_return (validated)');
  }
  assert.equal(M.curveGeometry([]), null); assert.equal(M.curveGeometry([{ date: '2024-01', strategy: 100, benchmark: 100 }]), null); assert.equal(M.curveGeometry(null), null);
  const flat = M.curveGeometry([{ date: '2024-01', strategy: 100, benchmark: 100 }, { date: '2024-02', strategy: 100, benchmark: 100 }]);
  assert.ok(Number.isFinite(flat.base) && !/NaN|Infinity/.test(flat.s + flat.b), 'a flat curve has a finite drawing');
  for (const bad of [0, -5, Infinity, NaN, '101', null]) assert.throws(() => M.curveGeometry([{ date: '2024-01', strategy: 100, benchmark: 100 }, { date: '2024-02', strategy: bad, benchmark: 100 }]), /CURVE_VALUE/, String(bad));
});

test('statusKind: solid only for REAL inputs with a recorded check and a point-in-time universe', () => {
  const base = L.validate(F.payload()).value.runs[0], k = (o, u) => M.statusKind({ ...base, ...o, universe: { ...base.universe, ...(u || {}) } });
  assert.equal(k({}), 'unchecked', 'REAL + NOT_VALIDATED');
  assert.equal(k({ validation_status: 'PIT_VERIFIED' }), 'checked'); assert.equal(k({ validation_status: 'REVIEWED' }), 'checked');
  assert.equal(k({ validation_status: 'REVIEWED' }, { point_in_time: false }), 'unchecked');
  assert.equal(k({ data_status: 'SYNTHETIC', validation_status: 'REVIEWED' }), 'unchecked'); assert.equal(k({ data_status: 'MIXED', validation_status: 'REVIEWED' }), 'unchecked');
});

/* ---------------------------------------------------------------- 9.2 ledger */
test('ledgerTable: the old table on a schema-2 ledger — newest first, v2 before v1, basis counts, NA with its reason', () => {
  const p = ledger(X.ledgerV2), fw = forwardOf(p), rows = M.ledgerTable(fw, p, FV);
  assert.equal(rows.length, 13);
  const order = rows.map((r) => r.date + ' ' + (r.version === FV.V2_VERSION ? 'v2' : 'v1'));
  assert.deepEqual(order.slice(0, 5), ['2026-10-27 v2', '2026-10-27 v1', '2026-10-26 v2', '2026-10-26 v1', '2026-10-23 v2']);
  assert.ok(order.includes('2026-10-22 v2') && !order.includes('2026-10-22 v1'), 'the v1 day without a record is not invented');
  const at = (d, v) => rows.find((r) => r.date === d && r.version === v);
  assert.deepEqual(plain(at('2026-10-27', FV.V2_VERSION)), {
    date: '2026-10-27', version: FV.V2_VERSION, vname: 'v2 기본', recorded: true, state: 'LIVE',
    q: (() => { const s = FV.qgSummary(p.versions[FV.V2_VERSION][6]); return s.Q.available + '/19 · ' + s.Q.weighted_mean.toFixed(2); })(),
    g: (() => { const s = FV.qgSummary(p.versions[FV.V2_VERSION][6]); return s.G.available + '/19 · ' + s.G.weighted_mean.toFixed(2); })(),
    evaluation: 'PRIMARY', evaluationText: '주 평가 · ' + X.CALC_B + ' · Q 470 · G 466 · 모집단 480 (fedcba9876543210) · 수집 2026-10-27~2026-10-27' });
  const miss = at('2026-10-23', FV.V2_VERSION);
  assert.deepEqual([miss.recorded, miss.state, miss.q, miss.g, miss.evaluation, miss.evaluationText], [false, '기록 · 입력 없음 · SEC_QGV2_MISSING', '—', '—', 'PREPARATORY', '준비 관측 · 주 평가 대상 아님 · RECORD_NOT_AVAILABLE']);
  assert.equal(at('2026-10-19', FV.V2_VERSION).evaluationText, '준비 관측 · 주 평가 대상 아님 · Q_BELOW_454, G_BELOW_454, CALC_VERSION_MISSING · NONE · Q 300 · G 290 · 모집단 310 (0123456789abcdef) · 수집 2026-10-19~2026-10-19');
  assert.equal(at('2026-10-20', FV.V2_VERSION).state, 'STALE');
  for (const r of rows.filter((x) => x.version === FV.VERSION)) assert.deepEqual([r.vname, r.evaluation, r.evaluationText], ['v1 비교용', 'COMPARISON', '비교용 · 평가 대상 아님']);
});

test('ledgerTable: schema 1 (v1 only, no basis) and a recorded day without any score (— and the reason, never 0)', () => {
  const p = ledger(X.ledgerV1), rows = M.ledgerTable(forwardOf(p), p, FV);
  assert.deepEqual(rows.map((r) => [r.date, r.vname, r.recorded, r.evaluation]), [['2026-10-20', 'v1 비교용', false, 'COMPARISON'], ['2026-10-19', 'v1 비교용', true, 'COMPARISON']]);
  assert.equal(rows[0].state, '기록 · 입력 없음 · SEC_QG_FACTORS_MISSING');
  const raw = { version: FV.V2_VERSION, state: 'RECORDED', qg_screen_state: 'LIVE' };
  const fw = { primary: FV.V2_VERSION, comparison: [], rows: [{ date: '2026-10-19', version: FV.V2_VERSION, state: 'RECORDED', summary: { state: 'RECORDED', companies: 19, Q: { available: 0, covered_units: 0, weighted_mean: null }, G: { available: 0, covered_units: 0, weighted_mean: null } }, evaluation: {} }] };
  const [r] = M.ledgerTable(fw, { versions: { [FV.V2_VERSION]: [raw] } }, FV);
  assert.deepEqual([r.q, r.g, r.evaluation], ['0/19 · — (점수 있는 종목 없음)', '0/19 · — (점수 있는 종목 없음)', 'LEGACY']);
  assert.equal(M.evaluationLabel({ version: FV.V2_VERSION, state: 'NOT_AVAILABLE' }, FV).text, '—');
});

test('evidenceView: the latest 7 session days, per-version lines, missing days never filled, an empty ledger', () => {
  const p = ledger(X.ledgerV2), e = M.evidenceView(FV.evidence(p), FV);
  assert.deepEqual(e.days.map((d) => [d.date, d.state]), X.SESSIONS.map((d) => [d, d === '2026-10-22' ? 'PARTIAL' : 'RECORDED']));
  assert.equal(e.days.find((d) => d.date === '2026-10-22').text, '10-22 · v2 ✓ · v1 기록 없음');
  assert.equal(e.days.find((d) => d.date === '2026-10-23').text, '10-23 · v2 기록 · 입력 없음 · v1 ✓');
  assert.deepEqual(e.versions.map((v) => [v.name, v.text]), [['v2 기본', '7건 · 2026-10-19 ~ 2026-10-27 · 빠진 거래일 없음'], ['v1 비교용', '6건 · 2026-10-19 ~ 2026-10-27 · 빠진 거래일 2026-10-22']]);
  assert.equal(e.missing, '2026-10-22 · 기록 없음 · 나중에 채우지 않음 · 범위 2026-10-19 ~ 2026-10-27 · 미국 거래일 7일');
  assert.deepEqual([e.latest, e.total, e.missingCount, e.as_of], ['2026-10-27', 7, 1, p.as_of]);
  const z = M.evidenceView(FV.evidence(ledger(X.ledgerEmpty)), FV);
  assert.deepEqual([z.days.length, z.latest, z.missing], [0, null, '범위 없음 · 기록 0건']);
  assert.deepEqual(z.versions.map((v) => v.text), ['0건 · 관측일 없음', '0건 · 관측일 없음']);
});

/* ---------------------------------------------------------------- static content and file rules */
test('9.1 rows carry the tree\'s 9.1.1–9.1.6 names; the checklist states are known words; nothing is a result', () => {
  const tree = fs.readFileSync(R.newPath('screen-tree-live.js'), 'utf8'), names = [...tree.matchAll(/L\('(9\.1\.\d)','([^']+)'\)/g)].map((m) => [m[1], m[2]]);
  assert.deepEqual(M.ROWS91.map(([n, name]) => [n, name]), names);
  assert.deepEqual([...new Set(M.CHECKLIST.map((c) => c[1]))].sort(), ['checked', 'decide', 'na', 'pending']);
  assert.ok(M.CHECKLIST.every(([k, , t]) => /^[a-z-]+$/.test(k) && t.length > 10 && !/%/.test(t)), 'checklist items are words, never a percentage');
  assert.deepEqual(Object.keys(M.METRIC_LABEL), [...L.METRICS], 'one label per contract metric');
});

test('screen-lab-live.js reads one public file and nothing private, sends and stores nothing; it loads without touching the layer', () => {
  const text = fs.readFileSync(R.newPath('screen-lab-live.js'), 'utf8'), code = text.replace(/\/\*[\s\S]*?\*\//g, '');
  assert.deepEqual([...new Set(code.match(/[a-z0-9-]+\.json/g))], ['forward-validation-ledger.json'], 'the only file named is the public ledger');
  assert.doesNotMatch(code, /fetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|clipboard|workers\.dev|\/lab\/backtest/, 'no request, storage, copy or private address');
  assert.doesNotMatch(code, /로그인됨|signed in/i, 'never pretends a signed-in state');
  assert.doesNotMatch(code, /lab-results[^'\s)]*\.json|backtest[^'\s)]*\.json/, 'no public Lab result file (the contract name lab-results/1 is only named)');
  const touched = [], IS2 = new Proxy({ h() {}, href() {}, parts: {} }, { get(t, k) { if (!['h', 'href', 'parts', 'append', 'labLive'].includes(k)) touched.push(k); return t[k]; }, set(t, k, v) { t[k] = v; return true; } });
  vm.runInNewContext(text, { window: { IS2 }, Object }, { filename: 'screen-lab-live.js' });
  assert.deepEqual(touched, [], 'nothing of the layer is read while the file loads');
  assert.deepEqual(Object.keys(IS2.labLive), ['screen']);
});
