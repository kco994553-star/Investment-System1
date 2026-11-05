'use strict';
// Feature 5.2.7 원천별 갱신 기록 (owner 2026-11-05): web_app/news-refresh.js against the public news-signals.json schema 2
// `refresh` block (NEWS_SIGNALS.md "공개 파일 형식 (schema_version 2, 별도 파일)").
//  - Fixture tests/fixtures/news_signals_refresh_v2_synthetic.json: SYNTHETIC, written by Codex's own news_signals.merge from
//    PR #483 (e3154ee3) on synthetic input (three runs). Every case also passes the old reader (NewsSignals.validate), so the
//    layer reads it as it would read the published file.
//  - gdelt_429_ir_updated: GDELT FAILED HTTP_429 (1 failed, 18 not run) while IR answered (UPDATED): both sources are drawn, IR as
//    갱신 with its counts, GDELT as 실패 (HTTP_429) · 이전 자료 유지 with 이월 시작; nothing of IR depends on GDELT.
//  - Values are the file's own (no sum, no derivation); a null is 미산출 / 이월 없음, never 0; a real 0 is a value; 수정 · 중복 are
//    미제공 (the public file has no count; Codex's run log does: counts.revisions = 1 in the generator run).
//  - Schema 1 copy and a schema 2 file without a run say so and draw no row. The validator refuses the whole block at its first fault.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../src/investment_system/product/web_app/news-refresh.js');
const NS = require('../src/investment_system/product/web_assets/news-signals.js');
const X = require('./web_app_news_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const FX = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/news_signals_refresh_v2_synthetic.json'), 'utf8'));
const C = (k) => structuredClone(FX.cases[k].payload);
const cells = (src) => Object.fromEntries(src.cells.map((c) => [c.key, [c.text, c.kind]]));
const refused = (p, code, at) => { const r = R.validate(p); assert.equal(r.ok, false, 'refused: ' + code); assert.deepEqual([r.code, r.path], [code, at]); };

ok('fixture: SYNTHETIC, made by #483 merge, every case passes the old reader and this reader', () => {
  assert.match(FX._comment, /^SYNTHETIC\./); assert.match(FX._comment, /#483/); assert.match(FX._comment, /e3154ee3/);
  for (const k of Object.keys(FX.cases)) { assert.doesNotThrow(() => NS.validate(C(k)), k); assert.equal(R.validate(C(k)).ok, true, k); }
  assert.deepEqual(FX.cases.gdelt_429_ir_updated.log_counts, { revisions: 1 }, 'the run log counted a corrected title; the file has no such field');
});
ok('GDELT FAILED HTTP_429 + IR UPDATED: both sources drawn, IR not hidden by GDELT', () => {
  const v = R.view(R.validate(C('gdelt_429_ir_updated')).value);
  assert.equal(v.kind, 'RECORDED');
  assert.deepEqual([v.overall.result, v.overall.when], ['PARTIAL_FAILED', '2026-10-14 02:30 UTC']);
  assert.deepEqual(v.sources.map((s) => [s.source, s.result, s.code, s.bad]), [['GDELT', 'FAILED', 'HTTP_429', true], ['IR', 'UPDATED', null, false]]);
  const g = cells(v.sources[0]), i = cells(v.sources[1]);
  assert.deepEqual(g, {
    last_success_at: ['2026-10-13 00:58 UTC', 'VALUE'], last_attempt_at: ['2026-10-14 02:30 UTC', 'VALUE'],
    last_result: ['실패 (HTTP_429) · 이전 자료 유지', 'VALUE'], companies: ['성공 0 · 실패 1 · 미실행 18', 'VALUE'], new_items: ['0건', 'VALUE'],
    items_carried_from: ['2026-10-13 00:58 UTC 수집분', 'VALUE'], revisions: [R.TEXT.NOT_IN_FILE, 'NA'], duplicates: [R.TEXT.NOT_IN_FILE, 'NA'] });
  assert.deepEqual(i, {
    last_success_at: ['2026-10-14 02:29 UTC', 'VALUE'], last_attempt_at: ['2026-10-14 02:30 UTC', 'VALUE'],
    last_result: ['갱신', 'VALUE'], companies: ['성공 10 · 실패 0 · 미실행 0', 'VALUE'], new_items: ['2건', 'VALUE'],
    items_carried_from: ['이월 없음 · 모든 회사 응답', 'NA'], revisions: [R.TEXT.NOT_IN_FILE, 'NA'], duplicates: [R.TEXT.NOT_IN_FILE, 'NA'] });
});
ok('values are the file\'s own: changing a count in the file changes only that text (no recomputation)', () => {
  const p = C('gdelt_429_ir_updated'); p.refresh.sources.IR.new_items = 7;
  const v = R.view(R.validate(p).value);
  assert.equal(cells(v.sources[1]).new_items[0], '7건');
  const q = C('gdelt_429_ir_updated'), s = q.refresh.sources.GDELT; s.companies = { succeeded: 0, failed: 3, not_run: 16 };
  assert.equal(cells(R.view(R.validate(q).value).sources[0]).companies[0], '성공 0 · 실패 3 · 미실행 16');
});
ok('both answered, nothing new; first run: 새 항목 없음 / 갱신, real 0 shown as 0', () => {
  const v = R.view(R.validate(C('both_no_new_items')).value);
  assert.deepEqual([v.overall.result, ...v.sources.map((s) => s.result)], ['NO_NEW_ITEMS', 'NO_NEW_ITEMS', 'NO_NEW_ITEMS']);
  assert.equal(cells(v.sources[0]).new_items[0], '0건'); assert.equal(cells(v.sources[0]).last_result[0], '새 항목 없음');
  const f = R.view(R.validate(C('first_run')).value);
  assert.deepEqual(f.sources.map((s) => cells(s).new_items[0]), ['4건', '1건']);
});
ok('the screen fixtures: 10/19 GDELT 429 shape (IR partly failed), schema 1 copy, a file without a run', () => {
  const v = R.view(R.validate(X.news(X.NOW, { scenario: 'GDELT_429' })).value);
  assert.deepEqual(v.sources.map((s) => [s.result, s.code]), [['FAILED', 'HTTP_429'], ['PARTIAL_FAILED', 'HTTP_FAILED']]);
  assert.equal(cells(v.sources[1]).last_result[0], '일부 실패 (HTTP_FAILED) · 이전 자료 유지');
  assert.equal(cells(v.sources[1]).companies[0], '성공 1 · 실패 9 · 미실행 0');
  const one = R.view(R.validate(X.newsV1()).value); assert.deepEqual([one.kind, one.text, one.sources.length], ['UNRECORDED', R.TEXT.UNRECORDED, 0]);
  const none = R.view(R.validate(X.newsNoRun()).value); assert.deepEqual([none.kind, none.text, none.sources.length], ['NO_RUN', R.TEXT.NO_RUN, 0]);
});
ok('a failed source with nothing before: 미산출 last success, 이전 자료 없음 (never 0, never a time)', () => {
  const p = C('gdelt_429_ir_updated'), g = p.refresh.sources.GDELT; g.last_success_at = null; g.items_carried_from = null;
  const c = cells(R.view(R.validate(p).value).sources[0]);
  assert.deepEqual([c.last_success_at, c.items_carried_from, c.last_result[0]], [['미산출 · 응답 받은 적 없음', 'NA'], ['이월 없음 · 이전 자료 없음', 'NA'], '실패 (HTTP_429) · 이전 자료 없음']);
});
ok('source(): the layer value is OK with no data kind; none is NONE with words; no request', () => {
  const p = C('first_run');
  assert.deepEqual({ ...R.source(p) }, { state: 'OK', payload: p, data_kind: null, text: '' });
  assert.deepEqual({ ...R.source(null) }, { state: 'NONE', payload: null, data_kind: null, text: R.TEXT.NONE });
});
ok('validated value is a deep-frozen copy', () => {
  const p = C('gdelt_429_ir_updated'), v = R.validate(p).value;
  assert.ok(Object.isFrozen(v.refresh.sources.GDELT.companies)); p.refresh.sources.GDELT.new_items = 99; assert.equal(v.refresh.sources.GDELT.new_items, 0);
});
ok('refusals: the whole block at its first fault', () => {
  const base = () => C('gdelt_429_ir_updated');
  let p = base(); p.schema_version = 3; refused(p, 'SCHEMA_VERSION', '$.schema_version');
  p = base(); delete p.refresh; refused(p, 'KEY_MISSING', '$.refresh');
  p = X.newsV1(); p = structuredClone(p); p.refresh = null; refused(p, 'KEY_UNKNOWN', '$.refresh');
  p = base(); p.refresh.extra = 1; refused(p, 'KEY_UNKNOWN', '$.refresh.extra');
  p = base(); delete p.refresh.sources.IR; refused(p, 'KEY_MISSING', '$.refresh.sources.IR');
  p = base(); p.refresh.sources.IR.counts = { revisions: 0 }; refused(p, 'KEY_UNKNOWN', '$.refresh.sources.IR.counts');
  p = base(); p.refresh.attempted_at = '2026-10-14T02:31:00+00:00'; refused(p, 'ATTEMPT_MISMATCH', '$.refresh.attempted_at');
  p = base(); p.refresh.sources.GDELT.last_attempt_at = '2026-10-14T02:29:00+00:00'; refused(p, 'ATTEMPT_MISMATCH', '$.refresh.sources.GDELT.last_attempt_at');
  p = base(); p.refresh.sources.GDELT.last_success_at = '2026-10-13 00:58:48'; refused(p, 'INSTANT_INVALID', '$.refresh.sources.GDELT.last_success_at');
  p = base(); p.refresh.sources.GDELT.last_success_at = '2026-10-14T02:31:00+00:00'; refused(p, 'SUCCESS_AFTER_ATTEMPT', '$.refresh.sources.GDELT.last_success_at');
  p = base(); p.refresh.sources.GDELT.last_result = 'CACHED'; refused(p, 'ENUM', '$.refresh.sources.GDELT.last_result');
  p = base(); p.refresh.sources.GDELT.last_result_code = null; refused(p, 'CODE_INVALID', '$.refresh.sources.GDELT.last_result_code');
  p = base(); p.refresh.sources.IR.last_result_code = 'HTTP_429'; refused(p, 'CODE_UNEXPECTED', '$.refresh.sources.IR.last_result_code');
  p = base(); p.refresh.sources.IR.new_items = null; refused(p, 'TYPE', '$.refresh.sources.IR.new_items');
  p = base(); p.refresh.sources.IR.new_items = 0; refused(p, 'RESULT_MISMATCH', '$.refresh.sources.IR.last_result');
  p = base(); p.refresh.sources.GDELT.new_items = 1; refused(p, 'NEW_ITEMS_WITHOUT_ANSWER', '$.refresh.sources.GDELT.new_items');
  p = base(); p.refresh.sources.GDELT.companies.failed = -1; refused(p, 'RANGE', '$.refresh.sources.GDELT.companies.failed');
  p = base(); p.refresh.sources.GDELT.companies.succeeded = 2; refused(p, 'RESULT_MISMATCH', '$.refresh.sources.GDELT.last_result');
  p = base(); p.refresh.sources.IR.items_carried_from = p.refresh.sources.IR.last_success_at; refused(p, 'CARRIED_WITHOUT_FAILURE', '$.refresh.sources.IR.items_carried_from');
  p = base(); p.refresh.sources.GDELT.items_carried_from = '2026-10-14T00:00:00+00:00'; refused(p, 'CARRIED_AFTER_SUCCESS', '$.refresh.sources.GDELT.items_carried_from');
  p = base(); p.refresh.result = 'FAILED'; refused(p, 'RESULT_MISMATCH', '$.refresh.result');
  p = base(); p.reason_codes = []; refused(p, 'REASON_MISMATCH', '$.reason_codes');
  p = base(); p.refresh.sources.IR.new_items = Infinity; refused(p, 'NUMBER_NOT_FINITE', '$.refresh.sources.IR.new_items');
  assert.equal(R.validate(null).ok, false); assert.equal(R.validate([]).ok, false);
});
ok('combined result = Codex refresh_result (both sources)', () => {
  const t = [[['UPDATED', 'NO_NEW_ITEMS'], 'UPDATED'], [['NO_NEW_ITEMS', 'NO_NEW_ITEMS'], 'NO_NEW_ITEMS'], [['FAILED', 'UPDATED'], 'PARTIAL_FAILED'],
    [['PARTIAL_FAILED', 'FAILED'], 'PARTIAL_FAILED'], [['FAILED', 'NOT_RUN'], 'FAILED'], [['NOT_RUN', 'NOT_RUN'], 'NOT_RUN']];
  for (const [r, want] of t) { assert.equal(R.combined(r), want, r.join('+')); assert.equal(NS.refreshResult({ GDELT: { last_result: r[0] }, IR: { last_result: r[1] } }), want); }
});
ok('words: no score, no summary, no price; the five results never share words', () => {
  assert.equal(new Set(Object.values(R.RESULT_TEXT)).size, 5);
  assert.deepEqual({ ...R.RESULT_TEXT }, { UPDATED: '갱신', NO_NEW_ITEMS: '새 항목 없음', PARTIAL_FAILED: '일부 실패', FAILED: '실패', NOT_RUN: '미실행' });
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_app/news-refresh.js'), 'utf8');
  for (const bad of ['fetch(', 'localStorage', 'sessionStorage', 'indexedDB', 'XMLHttpRequest']) assert.ok(!src.includes(bad), 'no ' + bad);
});
console.log('# web_app_news_refresh_node_test: ' + n + ' passed');
