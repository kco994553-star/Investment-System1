'use strict';
// Device V history (schema /2): append-only per date, never overwrites, never backfills before the latest recorded date,
// keeps at most 400 dates, stores V numbers + factor composition only (no prices), never stores a V whose core factor is
// missing, keeps /1 entries with an unknown composition, survives blocked/unreadable storage, and the runner reads it back.
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
const K = 'fundamental_value+historical_valuation+margin_of_safety+peer_relative_value+reverse_dcf+sector_context+theme_premium_discount';
const keys = (values) => Object.fromEntries(Object.keys(values).map((c) => [c, K]));
const rec = (s, d, values, comps = keys(values)) => H.record(s, d, values, comps);

test('same key and schema as the runner reader', () => {
  assert.equal(H.KEY, R.V_KEY);
  const s = memory();
  assert.equal(rec(s, '2026-10-19', { msft: 55.123, googl: 40 }).state, 'RECORDED');
  assert.deepEqual(stored(s), { schema: 'virtual-trading-v-scores/2', scores: { '2026-10-19': { googl: 40, msft: 55.12 } }, composition: { '2026-10-19': { googl: K, msft: K } } });
  assert.deepEqual(R.readVStore(s), { '2026-10-19': { googl: 40, msft: 55.12 } });
  assert.deepEqual(R.readVComposition(s), { '2026-10-19': { googl: K, msft: K } });
});

test('a V without its composition key is not stored; /1 entries are kept with an unknown composition and upgraded on write', () => {
  const s = memory();
  assert.equal(H.record(s, '2026-10-19', { msft: 55 }, {}).reason, 'UNCHANGED');
  assert.equal(H.record(s, '2026-10-19', { msft: 55 }, { msft: 'Not A Key' }).reason, 'UNCHANGED');
  assert.equal(s.writes.length, 0);
  const old = memory({ [H.KEY]: JSON.stringify({ schema: 'virtual-trading-v-scores/1', scores: { '2026-10-19': { msft: 50 } } }) });
  assert.deepEqual(R.readVStore(old), { '2026-10-19': { msft: 50 } });
  assert.deepEqual(R.readVComposition(old), {}, '/1 → composition unknown');
  assert.equal(rec(old, '2026-10-20', { msft: 51 }).state, 'RECORDED');
  assert.deepEqual(stored(old), { schema: 'virtual-trading-v-scores/2', scores: { '2026-10-19': { msft: 50 }, '2026-10-20': { msft: 51 } }, composition: { '2026-10-20': { msft: K } } });
  // The engine compares only equal compositions: the /1 day cannot anchor a slope.
  assert.deepEqual(R.vCompositionFromStore(R.readVComposition(old)), { '2026-10-20': { msft: K } });
});

test('append-only: an existing value is never overwritten, a new company on the same date is added', () => {
  const s = memory();
  rec(s, '2026-10-19', { msft: 50 });
  let r = rec(s, '2026-10-19', { msft: 99, googl: 41.256 });
  assert.deepEqual([r.state, r.added], ['RECORDED', ['googl']]);
  assert.deepEqual(stored(s).scores['2026-10-19'], { googl: 41.26, msft: 50 });
  r = rec(s, '2026-10-19', { msft: 1 });
  assert.deepEqual([r.state, r.reason], ['NOT_RECORDED', 'UNCHANGED']);
  assert.equal(s.writes.length, 2, 'no write when nothing is added');
});

test('no backfill: a date before the latest recorded date is refused', () => {
  const s = memory();
  rec(s, '2026-10-20', { msft: 50 });
  const r = rec(s, '2026-10-19', { msft: 51 });
  assert.deepEqual([r.state, r.reason], ['NOT_RECORDED', 'DATE_BEFORE_LAST_RECORDED']);
  assert.deepEqual(Object.keys(stored(s).scores), ['2026-10-20']);
  assert.equal(rec(s, 'bad', { msft: 1 }).reason, 'DATE_INVALID');
});

test('at most 400 dates, oldest dropped', () => {
  let scores = {}, composition = {};
  const start = Date.parse('2026-01-01T00:00:00Z');
  for (let i = 0; i < 405; i++) ({ scores, composition } = H.merge(scores, new Date(start + i * 86400000).toISOString().slice(0, 10), { msft: i % 100 }, { compositions: { msft: K }, composition }));
  const dates = Object.keys(scores);
  assert.equal(dates.length, 400);
  assert.deepEqual(Object.keys(composition), dates, 'composition dropped with its date');
  assert.equal(dates[0], new Date(start + 5 * 86400000).toISOString().slice(0, 10));
  assert.equal(H.MAX_DATES, 400);
});

test('V numbers only: prices, junk companies, out-of-range and missing values are not stored (never 0 for missing)', () => {
  const s = memory();
  const values = { msft: 55.5, nvda: null, amd: NaN, googl: 101, x: 50, intc: '40', price: 777.0731, close: 123 };
  const r = rec(s, '2026-10-19', values);
  assert.deepEqual(r.added, ['msft']);
  const text = s.getItem(H.KEY);
  for (const word of ['777', 'close', 'price', 'quantity', 'fx', 'KRW', 'null']) assert.ok(!text.includes(word), word);
  assert.equal(rec(s, '2026-10-20', {}).reason, 'NO_VALUES');
});

test('storage blocked or unreadable: nothing is written and nothing is destroyed', () => {
  const blocked = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
  assert.equal(rec(blocked, '2026-10-19', { msft: 1 }).reason, 'DEVICE_STORAGE_UNAVAILABLE');
  const full = memory();
  full.setItem = () => { throw new Error('quota'); };
  assert.equal(rec(full, '2026-10-19', { msft: 1 }).reason, 'DEVICE_STORAGE_UNAVAILABLE');
  const bad = memory({ [H.KEY]: '{not json' });
  assert.equal(rec(bad, '2026-10-19', { msft: 1 }).reason, 'V_STORE_INVALID');
  assert.equal(bad.getItem(H.KEY), '{not json');
});

test('capture (PLAYBOOK_V1 §13-1): V below the condition is NA and never stored (never 0); a partial V meeting it is stored with its composition; stored V feeds the ledger inputs', async () => {
  const v = fixture.vectors.find((x) => x.name === 'rehearsal_window_qg_fill');
  const cfg = S.rehearsalConfig(v.inputs.histories, VT.defaultConfig());
  const assembled = R.assemble({ ...v.inputs, config: { start_date: cfg.start_date } });
  const storage = memory();
  const view = { localStorage: storage, DeviceValuation: { load: async () => fixture.valuation, parameters: DV.parameters } };
  const out = await H.capture(view, assembled);
  assert.deepEqual(out.capture, { state: 'RECORDED', reason: null, date: '2026-11-30', added: Object.keys(v.expected.v_scores).sort(), skipped: Object.keys(v.expected.v_skipped).sort() });
  assert.equal(storage.writes.length, 1);
  const kept = stored(storage);
  assert.deepEqual(kept.scores['2026-11-30'], v.expected.v_scores);assert.deepEqual(kept.composition['2026-11-30'], v.expected.v_composition);
  assert.ok(!Object.hasOwn(kept.scores['2026-11-30'], 'amzn'), 'nothing stored for an NA V');
  // A V recorded with its composition reaches every READY ledger input (scores + composition).
  storage.removeItem(H.KEY);storage.writes.length = 0;
  rec(storage, '2026-11-30', { msft: 61.5 });
  const fed = await H.capture(view, assembled);
  // An existing date/company value is never overwritten (msft keeps 61.5); the other companies are appended.
  assert.deepEqual(fed.result.ledgers.SET_A.input.v_scores, { '2026-11-30': { ...v.expected.v_scores, msft: 61.5 } });
  assert.deepEqual(fed.result.ledgers.SET_A.input.v_composition, { '2026-11-30': { ...v.expected.v_composition, msft: K } });
  assert.equal(storage.writes.length, 2);
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
