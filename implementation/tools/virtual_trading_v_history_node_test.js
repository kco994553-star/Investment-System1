'use strict';
// Device V history: append-only per date, never overwrites, never backfills before the latest recorded date, keeps at
// most 400 dates, stores V numbers only (no prices), survives blocked/unreadable storage, and the runner reads it back.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const H = require('../src/investment_system/product/web_assets/virtual-trading-v-history.js');
const R = require('../src/investment_system/product/web_assets/virtual-trading-runner.js');
const S = require('../src/investment_system/product/web_assets/virtual-trading-signals.js');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const DV = require('../src/investment_system/product/web_assets/device-valuation.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_signals_v1.json'), 'utf8'));

function memory(initial = {}) {
  const data = new Map(Object.entries(initial)), writes = [];
  return { data, writes, getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => { writes.push([k, v]); data.set(k, String(v)); }, removeItem: (k) => data.delete(k) };
}
const stored = (s) => JSON.parse(s.getItem(H.KEY));

test('same key and schema as the runner reader', () => {
  assert.equal(H.KEY, R.V_KEY);
  const s = memory();
  assert.equal(H.record(s, '2026-10-19', { msft: 55.123, googl: 40 }).state, 'RECORDED');
  assert.deepEqual(stored(s), { schema: 'virtual-trading-v-scores/1', scores: { '2026-10-19': { googl: 40, msft: 55.12 } } });
  assert.deepEqual(R.readVStore(s), { '2026-10-19': { googl: 40, msft: 55.12 } });
});

test('append-only: an existing value is never overwritten, a new company on the same date is added', () => {
  const s = memory();
  H.record(s, '2026-10-19', { msft: 50 });
  let r = H.record(s, '2026-10-19', { msft: 99, googl: 41.256 });
  assert.deepEqual([r.state, r.added], ['RECORDED', ['googl']]);
  assert.deepEqual(stored(s).scores['2026-10-19'], { googl: 41.26, msft: 50 });
  r = H.record(s, '2026-10-19', { msft: 1 });
  assert.deepEqual([r.state, r.reason], ['NOT_RECORDED', 'UNCHANGED']);
  assert.equal(s.writes.length, 2, 'no write when nothing is added');
});

test('no backfill: a date before the latest recorded date is refused', () => {
  const s = memory();
  H.record(s, '2026-10-20', { msft: 50 });
  const r = H.record(s, '2026-10-19', { msft: 51 });
  assert.deepEqual([r.state, r.reason], ['NOT_RECORDED', 'DATE_BEFORE_LAST_RECORDED']);
  assert.deepEqual(Object.keys(stored(s).scores), ['2026-10-20']);
  assert.equal(H.record(s, 'bad', { msft: 1 }).reason, 'DATE_INVALID');
});

test('at most 400 dates, oldest dropped', () => {
  let scores = {};
  const start = Date.parse('2026-01-01T00:00:00Z');
  for (let i = 0; i < 405; i++) scores = H.merge(scores, new Date(start + i * 86400000).toISOString().slice(0, 10), { msft: i % 100 }).scores;
  const dates = Object.keys(scores);
  assert.equal(dates.length, 400);
  assert.equal(dates[0], new Date(start + 5 * 86400000).toISOString().slice(0, 10));
  assert.equal(H.MAX_DATES, 400);
});

test('V numbers only: prices, junk companies, out-of-range and missing values are not stored (never 0 for missing)', () => {
  const s = memory();
  const r = H.record(s, '2026-10-19', { msft: 55.5, nvda: null, amd: NaN, googl: 101, x: 50, intc: '40', price: 777.0731, close: 123 });
  assert.deepEqual(r.added, ['msft']);
  const text = s.getItem(H.KEY);
  for (const word of ['777', 'close', 'price', 'quantity', 'fx', 'KRW', 'null']) assert.ok(!text.includes(word), word);
  assert.equal(H.record(s, '2026-10-20', {}).reason, 'NO_VALUES');
});

test('storage blocked or unreadable: nothing is written and nothing is destroyed', () => {
  const blocked = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
  assert.equal(H.record(blocked, '2026-10-19', { msft: 1 }).reason, 'DEVICE_STORAGE_UNAVAILABLE');
  const full = memory();
  full.setItem = () => { throw new Error('quota'); };
  assert.equal(H.record(full, '2026-10-19', { msft: 1 }).reason, 'DEVICE_STORAGE_UNAVAILABLE');
  const bad = memory({ [H.KEY]: '{not json' });
  assert.equal(H.record(bad, '2026-10-19', { msft: 1 }).reason, 'V_STORE_INVALID');
  assert.equal(bad.getItem(H.KEY), '{not json');
});

test('capture: V from the latest completed session close, stored, and fed back into the ledger inputs', async () => {
  const v = fixture.vectors.find((x) => x.name === 'rehearsal_window_qg_fill');
  const cfg = S.rehearsalConfig(v.inputs.histories, VT.defaultConfig());
  const assembled = R.assemble({ ...v.inputs, config: { start_date: cfg.start_date } });
  const storage = memory();
  const view = { localStorage: storage, DeviceValuation: { load: async () => fixture.valuation, parameters: DV.parameters } };
  const out = await H.capture(view, assembled);
  assert.deepEqual(out.capture, { state: 'RECORDED', reason: null, date: '2026-11-30', added: Object.keys(v.expected.v_scores).sort() });
  assert.deepEqual(stored(storage).scores, { '2026-11-30': v.expected.v_scores });
  assert.deepEqual(out.result.ledgers.SET_A.input.v_scores, { '2026-11-30': v.expected.v_scores });
  // Second capture of the same session adds nothing; the ledger inputs are unchanged.
  const again = await H.capture(view, assembled);
  assert.equal(again.capture.reason, 'UNCHANGED');
  assert.equal(storage.writes.length, 1);
  // No valuation inputs → nothing recorded; no session → nothing recorded.
  const none = await H.capture({ localStorage: memory(), DeviceValuation: { load: async () => null, parameters: DV.parameters } }, assembled);
  assert.equal(none.capture.reason, 'VALUATION_INPUTS_UNAVAILABLE');
  const notReady = await H.capture({ localStorage: memory() }, { state: 'NOT_AVAILABLE', reason_codes: ['AUTH_REQUIRED'], ledgers: {} });
  assert.equal(notReady.capture.reason, 'SESSION_NOT_AVAILABLE');
});

test('module writes only the V key and logs nothing', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/virtual-trading-v-history.js'), 'utf8');
  assert.equal((src.match(/setItem\(/g) || []).length, 1);
  for (const word of ['console.', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'fetch(', 'indexedDB', 'removeItem']) assert.ok(!src.includes(word), word);
  const backup = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/device-backup.js'), 'utf8');
  assert.ok(!backup.includes('virtual-trading-v-scores'), 'V history is not part of the device backup');
});
