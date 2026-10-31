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
  assert.deepEqual(H.readStore(s).scores, { '2026-10-19': { googl: 40, msft: 55.12 } });
  assert.deepEqual(H.readStore(s).composition, { '2026-10-19': { googl: K, msft: K } });
  // DC-31: the runner no longer reads this store (no screen captures; the module goes with the cleanup PR after 11/16).
  assert.deepEqual(R.readVStore(s), {});assert.deepEqual(R.readVComposition(s), {});
});

test('a V without its composition key is not stored; /1 entries are kept with an unknown composition and upgraded on write', () => {
  const s = memory();
  assert.equal(H.record(s, '2026-10-19', { msft: 55 }, {}).reason, 'UNCHANGED');
  assert.equal(H.record(s, '2026-10-19', { msft: 55 }, { msft: 'Not A Key' }).reason, 'UNCHANGED');
  assert.equal(s.writes.length, 0);
  const old = memory({ [H.KEY]: JSON.stringify({ schema: 'virtual-trading-v-scores/1', scores: { '2026-10-19': { msft: 50 } } }) });
  assert.deepEqual(H.readStore(old).scores, { '2026-10-19': { msft: 50 } });
  assert.deepEqual(H.readStore(old).composition, {}, '/1 → composition unknown');
  assert.equal(rec(old, '2026-10-20', { msft: 51 }).state, 'RECORDED');
  assert.deepEqual(stored(old), { schema: 'virtual-trading-v-scores/2', scores: { '2026-10-19': { msft: 50 }, '2026-10-20': { msft: 51 } }, composition: { '2026-10-20': { msft: K } } });
  // The engine compares only equal compositions: the /1 day cannot anchor a slope.
  assert.deepEqual(R.vCompositionFromStore(H.readStore(old).composition), { '2026-10-20': { msft: K } });
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
  // An existing date/company value is never overwritten (msft keeps 61.5); the other companies are appended.
  storage.removeItem(H.KEY);storage.writes.length = 0;
  rec(storage, '2026-11-30', { msft: 61.5 });
  const fed = await H.capture(view, assembled);
  assert.deepEqual(stored(storage).scores['2026-11-30'], { ...v.expected.v_scores, msft: 61.5 });
  // DC-31: the runner no longer reads the store, so no stored V reaches a ledger input.
  assert.deepEqual(fed.result.ledgers.SET_A.input.v_scores, {});assert.deepEqual(fed.result.ledgers.SET_A.input.v_composition, {});
  assert.equal(storage.writes.length, 2);
  // No valuation inputs → nothing recorded; no session → nothing recorded.
  const none = await H.capture({ localStorage: memory(), DeviceValuation: { load: async () => null, parameters: DV.parameters } }, assembled);
  assert.equal(none.capture.reason, 'VALUATION_INPUTS_UNAVAILABLE');
  const notReady = await H.capture({ localStorage: memory() }, { state: 'NOT_AVAILABLE', reason_codes: ['AUTH_REQUIRED'], ledgers: {} });
  assert.equal(notReady.capture.reason, 'SESSION_NOT_AVAILABLE');
});

test('module writes only the two versioned V keys and logs nothing', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/virtual-trading-v-history.js'), 'utf8');
  assert.equal((src.match(/setItem\(/g) || []).length, 2);
  for (const word of ['console.', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'fetch(', 'indexedDB', 'removeItem']) assert.ok(!src.includes(word), word);
  const backup = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/device-backup.js'), 'utf8');
  assert.ok(!backup.includes('virtual-trading-v-scores'), 'V history is not part of the device backup');
});

test('v2 score observations are separate, append-only, same-session and reject price fields', () => {
  const s=memory(),entry={score:60,version:'v2',profile:'qgv-v2/balanced/gate-on',composition:'v_earnings_yield+v_fcf_yield',earnings_basis:'REPORTED',pool_hash:'a'.repeat(64),parameters_version:'dcf_parameters/v1.1-default',source_as_of:'2026-10-19T22:00:00Z',observed_at:'2026-10-19T22:30:00Z'};
  assert.equal(H.recordV2(s,'2026-10-19',{msft:{...entry,price:100}}).state,'NOT_RECORDED');
  assert.equal(H.recordV2(s,'2026-10-19',{msft:{...entry,source_as_of:'2026-10-19T22:00:00Z',observed_at:'2026-10-19T15:00:00Z'}}).state,'NOT_RECORDED','before NYSE close');
  assert.equal(H.recordV2(s,'2026-10-19',{msft:entry}).state,'RECORDED');
  assert.equal(s.getItem(H.KEY),null,'v1 stays untouched');
  const first=s.getItem(H.V2_KEY);assert.equal(H.recordV2(s,'2026-10-19',{msft:{...entry,score:80}}).state,'NOT_RECORDED');assert.equal(s.getItem(H.V2_KEY),first);
  assert.equal(H.recordV2(s,'2026-10-18',{msft:entry}).reason,'DATE_BEFORE_LAST_RECORDED');
  assert.equal(H.recordV2(s,'2026-10-20',{msft:{...entry,observed_at:'2026-10-20T22:30:00Z'}}).state,'NOT_RECORDED','yesterday financial source is not backdated');
  assert.deepEqual(Object.keys(H.readV2(s).records['2026-10-19'].msft).sort(),['score','version','profile','composition','earnings_basis','pool_hash','parameters_version','source_as_of','observed_at'].sort());
});

test('v2 20-session comparison needs observed endpoints with matching profile/factors/pool', () => {
  const s=memory(),days=[];let d=new Date('2026-10-19T00:00:00Z');
  while(days.length<21){if(d.getUTCDay()>0&&d.getUTCDay()<6)days.push(d.toISOString().slice(0,10));d.setUTCDate(d.getUTCDate()+1);}
  for(const[ i,date]of days.entries())assert.equal(H.recordV2(s,date,{msft:{score:i,version:'v2',profile:'qgv-v2/balanced/gate-on',composition:'v_earnings_yield+v_fcf_yield',earnings_basis:'REPORTED',pool_hash:'a'.repeat(64),parameters_version:'dcf_parameters/v1.1-default',source_as_of:date+'T22:00:00Z',observed_at:date+'T22:30:00Z'}}).state,'RECORDED');
  assert.equal(H.v2Comparison(s,'msft',days.slice(0,20)).reason,'V_HISTORY_SHORT');
  const c=H.v2Comparison(s,'msft',days);assert.equal(c.state,'READY');assert.equal(c.current,20);assert.equal(c.previous,0);
  const wrongProfile=H.v2Comparison(s,'msft',days,'qgv-v2/value/gate-on');assert.equal(wrongProfile.state,'NOT_AVAILABLE');assert.equal(wrongProfile.current,null);
  const stored=JSON.parse(s.getItem(H.V2_KEY));stored.records[days[0]].msft.pool_hash='b'.repeat(64);s.setItem(H.V2_KEY,JSON.stringify(stored));assert.equal(H.v2Comparison(s,'msft',days).reason,'V_COMPOSITION_CHANGED');
  const v=H.v2Values(s);assert.notEqual(v.composition[days[0]].msft,v.composition[days.at(-1)].msft);assert.match(v.composition[days[0]].msft,/^[a-z][a-z0-9_]*(?:\+[a-z][a-z0-9_]*)*$/);
});

test('v2 capture uses only the current completed close and never lets v1 scores into a v2 runner', async () => {
  const s=memory(),date='2026-10-19',result={state:'READY',snapshot_basis:'v2',ledgers:{SET_A:{state:'READY',input:{benchmarks:{SP500:{[date]:100}},companies:{msft:{currency:'USD',closes:{[date]:123}}}}}}};
  let calls=0,seen;
  const view={localStorage:s,crypto:require('node:crypto').webcrypto,Qgv2Inputs:{FILE:'sec-qgv2.json'},DcfParametersDefaults:{config_version:'dcf_parameters/v1.1-default'},QgvScores:{symbolOf:t=>String(t).split(':').at(-1)}};
  view.QgvScores.compute=args=>{calls++;seen=args.quotes;const v2={v:60,profile:{id:'qgv-v2/balanced/gate-on'},detail:{earnings_basis:'REPORTED'},factors:{v_earnings_yield:{score:60},v_fcf_yield:{score:60}}};return{rows:{msft:{v2}}};};
  const options={identities:[{company_id:'msft',ticker:'MSFT'}],publicScreens:{'sec-qgv2.json':{as_of:date+'T22:00:00Z',records:{'NYSE:MSFT':{},'TARGET:msft':{}}}},now:date+'T22:30:00Z'};
  const out=await H.captureV2(view,result,options);assert.equal(out.capture.state,'RECORDED');assert.equal(calls,1);assert.equal(seen['TARGET:msft'].price,123);
  assert.equal(out.result.ledgers.SET_A.input.v_scores[date].msft,60);assert.equal(s.getItem(H.KEY),null);assert.ok(!/"price"|"closes"|"currency"|123/.test(s.getItem(H.V2_KEY)));
  const old=await H.captureV2(view,result,{...options,now:'2026-10-20T22:30:00Z'});assert.equal(old.capture.state,'NOT_RECORDED');assert.equal(calls,1,'old session is never recalculated with new-day fundamentals');
});

test('v2 provenance equality is lossless in both comparisons and engine composition keys', () => {
  const days=[];let d=new Date('2026-10-19T00:00:00Z');while(days.length<21){if(d.getUTCDay()>0&&d.getUTCDay()<6)days.push(d.toISOString().slice(0,10));d.setUTCDate(d.getUTCDate()+1);}
  const base={score:50,version:'v2',profile:'qgv-v2/balanced/gate-on',composition:'v_earnings_yield+v_fcf_yield',earnings_basis:'REPORTED',pool_hash:'a'.repeat(64),parameters_version:'dcf/example-1'};
  for(const changed of [{parameters_version:'dcf/example_1'},{pool_hash:'a'.repeat(48)+'b'.repeat(16)}]){
    const s=memory();for(const[date,fields]of [[days[0],base],[days.at(-1),{...base,...changed}]])assert.equal(H.recordV2(s,date,{msft:{...fields,source_as_of:date+'T22:00:00Z',observed_at:date+'T22:30:00Z'}}).state,'RECORDED');
    assert.equal(H.readV2(s).state,'OK');assert.equal(H.v2Comparison(s,'msft',days).reason,'V_COMPOSITION_CHANGED');
    const v=H.v2Values(s);assert.notEqual(v.composition[days[0]].msft,v.composition[days.at(-1)].msft);
    const kept=require('../src/investment_system/product/web_assets/virtual-trading-runner.js').vCompositionFromStore(v.composition);assert.deepEqual(kept,v.composition);
  }
  const s=memory(),date=days[0],max={...base,profile:'qgv-v2/balanced/gate-off',composition:Object.keys(require('../src/investment_system/product/web_assets/qgv-v2.js').WEIGHTS.V).sort().join('+'),parameters_version:'P'.repeat(63),source_as_of:date+'T22:00:00Z',observed_at:date+'T22:30:00Z'};
  assert.equal(H.recordV2(s,date,{msft:max}).state,'RECORDED');const v=H.v2Values(s);assert.deepEqual(require('../src/investment_system/product/web_assets/virtual-trading-runner.js').vCompositionFromStore(v.composition),v.composition);
});
