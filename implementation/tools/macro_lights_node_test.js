'use strict';
// Macro lights v1 (PLAYBOOK_V1 13-5): JS == Python reference vectors, CONFIG == macro_lights_v1.json, RAM-only state API. Synthetic only.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const M = require(path.join(W, 'macro-lights.js'));
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/macro_lights_v1_vectors.json'), 'utf8'));
const CONFIG = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/investment_system/macro/macro_lights_v1.json'), 'utf8'));
const FN = {employment_light: M.employmentLight, inflation_light: M.inflationLight, curve_light: M.curveLight, market_light: M.marketLight,
  credit_light: M.creditLight, macro_state: M.macroState};

for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true);
  const args = structuredClone(c.args), before = JSON.stringify(args);
  assert.deepStrictEqual(FN[c.fn](...args), JSON.parse(c.expected_json));
  assert.equal(JSON.stringify(args), before, 'input not mutated');
});
test('embedded CONFIG equals macro_lights_v1.json (v1 · UNCALIBRATED, sell decisions off)', () => {
  assert.deepStrictEqual(JSON.parse(JSON.stringify(M.CONFIG)), CONFIG);
  assert.equal(M.CONFIG.version, 'v1'); assert.equal(M.CONFIG.status, 'UNCALIBRATED'); assert.equal(M.CONFIG.sell_decisions, false);
  assert.equal(vectors.config_id, CONFIG.id); assert.equal(vectors.config_version, CONFIG.version);
});
test('vectors cover every light reason and state reason', () => {
  const text = JSON.stringify(vectors.cases.map(c => JSON.parse(c.expected_json)));
  for (const code of ['LIT', 'NOT_LIT', 'NO_DATA', 'INVALID_INPUT', 'CONFLICTING_DUPLICATE', 'WINDOW_INCOMPLETE', 'INSUFFICIENT_HISTORY', 'BASE_MONTH_MISSING',
    'VALUE_MISSING', 'LIT_COUNT_GE_3', 'MARKET_AND_CREDIT_LIT', 'INFLATION_GT_8PCT', 'LIT_COUNT_EQ_2', 'INFLATION_GT_5PCT_AND_GROWTH_LT_0', 'LIT_COUNT_LE_1',
    'AVAILABLE_LT_3']) assert.ok(text.includes('"' + code + '"'), code);
  for (const state of ['NORMAL', 'WARNING', 'CRISIS']) assert.ok(text.includes('"state":"' + state + '"'), state);
});
test('missing values are never zero: a null light is excluded, not counted as off', () => {
  const s = M.macroState({employment: null, inflation: null, curve: false}, null, null);
  assert.deepStrictEqual(s, {state: 'NORMAL', lit_count: 0, available_count: 1, low_confidence: true, reasons: ['LIT_COUNT_LE_1', 'AVAILABLE_LT_3']});
  assert.equal(M.employmentLight([['2031-01', null]]).lit, null);
});
test('merge: public lights + device lights; credit stays blocked until HYG/IEF are in the Worker allowlist', () => {
  assert.deepStrictEqual([...M.WORKER_ALLOWED], ['SPY']);
  M.clearDevice();
  assert.equal(M.current(), null);
  const bundle = {'macro-screen.json': {as_of: '2031-05-01T00:00:00+00:00', data: {growth_inflation_v0: {axes: {Growth: {state: 'LIVE', value: '-0.01', period: '2031Q1'}}},
    macro_lights_v1: {lights: {
      employment: {state: 'LIVE', lit: true, reason: 'LIT', as_of: '2031-04', source: 's', values: {period: '2031-04', avg3: 4.6, low12: 4, low12_count: 12, gap: 0.6}},
      inflation: {state: 'LIVE', lit: true, reason: 'LIT', as_of: '2031-04', source: 's', values: {period: '2031-04', base_period: '2030-04', yoy: 0.06}},
      curve: {state: 'NOT_AVAILABLE', lit: null, reason: 'SOURCE_NOT_COLLECTED', as_of: null, source: 's', values: {date: null, ten_year: null, three_month: null, spread: null, run_days: null}}}}}}};
  const m = M.merge(bundle);
  assert.equal(m.lights.credit.reason, 'WORKER_ALLOWLIST_REQUIRED'); assert.equal(m.lights.credit.lit, null); assert.equal(m.lights.credit.estimate, true);
  assert.equal(m.lights.market.reason, 'DEVICE_NOT_LOADED');
  assert.deepStrictEqual(m.reasons, ['LIT_COUNT_EQ_2', 'INFLATION_GT_5PCT_AND_GROWTH_LT_0', 'AVAILABLE_LT_3']);
  assert.deepStrictEqual(M.current(), {state: 'WARNING', lit_count: 2, available_count: 2, low_confidence: true});
  const withMarket = M.merge(bundle, {market: {lit: true, reason: 'LIT'}, credit: {lit: true, reason: 'LIT'}});
  assert.equal(withMarket.state, 'CRISIS'); assert.deepStrictEqual(withMarket.reasons, ['LIT_COUNT_GE_3']);
  assert.equal(withMarket.lights.credit.reason, 'WORKER_ALLOWLIST_REQUIRED', 'device credit is ignored while blocked');
  const empty = M.merge({});
  assert.deepStrictEqual(M.current(), {state: 'NORMAL', lit_count: 0, available_count: 0, low_confidence: true});
  assert.equal(empty.lights.employment.reason, 'SOURCE_NOT_COLLECTED');
  const copy = M.current(); copy.state = 'CRISIS'; assert.equal(M.current().state, 'NORMAL', 'current() returns a copy');
});
test('device readiness never requests prices without opt-in, approved origin and session', () => {
  assert.equal(M.readiness({}, {}, null), 'OFF');
  const view = {PrivateHistory: {parseWorkerOrigin: v => v}, localStorage: {getItem: () => 'https://a.b.workers.dev'}};
  assert.equal(M.readiness(view, {privateHistoryEnabled: true, privateHistoryWorkerOrigin: 'https://c.d.workers.dev'}, null), 'ORIGIN_UNAPPROVED');
  assert.equal(M.readiness(view, {privateHistoryEnabled: true, privateHistoryWorkerOrigin: 'https://a.b.workers.dev'}, null), 'AUTH_REQUIRED');
  assert.equal(M.readiness(view, {privateHistoryEnabled: true, privateHistoryWorkerOrigin: 'https://a.b.workers.dev'}, {state: () => ({connected: true})}), 'READY');
});
test('module source holds no storage writes, logging or network beyond the session Worker fetch', () => {
  const src = fs.readFileSync(path.join(W, 'macro-lights.js'), 'utf8');
  for (const bad of ['setItem', 'console.', 'indexedDB', 'sendBeacon', 'XMLHttpRequest', 'fetch(']) assert.ok(!src.includes(bad), bad);
  assert.ok(src.includes('session.fetchHistory('));
});
