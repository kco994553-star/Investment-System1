'use strict';
// Virtual trading runner: the JS assembly must equal the Python reference on the shared SYNTHETIC vectors, the engine
// run on the assembled inputs must equal the Python engine, and the fetch layer must degrade per symbol, stop on
// session failures, never fill a missing close and never store or log prices.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../src/investment_system/product/web_assets/virtual-trading-runner.js');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_inputs_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));
const project = (r) => ({ state: r.state, reason_codes: r.reason_codes, summary: r.summary, trades: r.trades,
  cancelled: r.days.flatMap((d) => d.cancelled.map((c) => [d.date, c.company, c.cancel_reason])),
  mains: Object.fromEntries(r.days.map((d) => [d.date, Object.fromEntries(Object.keys(d.judgements).sort().map((k) => [k, d.judgements[k].main]))])) });

test('fixture is marked synthetic', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
});

for (const v of fixture.vectors) {
  test('vector ' + v.name + ': JS assembly equals Python', () => {
    const out = R.assemble(v.inputs);
    assert.deepEqual(plain(out), v.expected);
    assert.deepEqual(R.requiredSymbols(v.inputs), v.required_symbols);
    if (v.expected_engine) {
      for (const [kind, expected] of Object.entries(v.expected_engine)) {
        const cfg = { ...VT.defaultConfig(), start_date: v.inputs.config.start_date };
        assert.deepEqual(plain(project(VT.runLedger(cfg, out.ledgers[kind].input))), expected, kind);
      }
    }
  });
}

test('full vector: missing FX on the last session surfaces EXEC_FX_MISSING, nothing is filled', () => {
  const v = fixture.vectors.find((x) => x.name === 'full_synthetic');
  const out = R.assemble(v.inputs), usd = out.ledgers.SET_A.input.fx.USD;
  assert.equal(Object.hasOwn(usd, '2026-10-30'), false);
  assert.equal(Object.hasOwn(out.ledgers.SET_A.input.companies.nvda.closes, '2026-10-30'), false, 'IN_PROGRESS bar excluded');
  assert.equal(Object.hasOwn(out.ledgers.SET_A.input.companies.nvda.closes, '2026-10-29'), true, 'UNKNOWN past bar used');
  assert.equal(Object.hasOwn(out.ledgers.SET_A.input.companies.amd.closes, '2026-10-30'), false, 'UNKNOWN bar on read day excluded');
  for (const series of [usd, ...Object.values(out.ledgers.SET_A.input.companies).map((c) => c.closes)]) for (const x of Object.values(series)) assert.ok(x > 0);
  const result = VT.runLedger(VT.defaultConfig(), out.ledgers.SET_A.input);
  assert.ok(result.days.at(-1).cancelled.some((c) => c.cancel_reason === 'EXEC_FX_MISSING'));
  assert.equal(result.days[0].date, '2026-10-19');
  // Shadow starts at the ACTUAL snapshot's New York date (2026-10-20), never earlier.
  assert.equal(out.ledgers.SHADOW.input.sessions[0], '2026-10-20');
  assert.equal(out.ledgers.SHADOW.input.id, 'shadow-2026-10-20');
  assert.deepEqual(Object.keys(out.ledgers.SHADOW.input.initial.positions), ['hanmi', 'nvda', 'tokyo_electron']);
  assert.deepEqual(out.ledgers.SET_A.input.v_scores, { '2026-10-20': { nvda: 55.5 }, '2026-10-22': { googl: 0, nvda: 61 } });
  assert.equal(out.sector.asml.etf, 'SMH');
  assert.equal(out.sector.klac.reason, 'SEMIS_MEMBERSHIP_NOT_AVAILABLE');
  assert.equal(out.ledgers.SET_A.input.companies.msft.sector_benchmark, 'XLK');
  assert.equal(Object.hasOwn(out.ledgers.SET_A.input.benchmarks, 'XLK'), false, 'rejected ETF stays absent');
});

test('report model: cancelled orders and runner status are shown, amounts stay hidden', () => {
  const DR = require('../src/investment_system/product/web_assets/daily-report.js');
  const v = fixture.vectors.find((x) => x.name === 'full_synthetic');
  const result = R.assemble(v.inputs), { ledger, hits } = R.ledgerFor(result, 'SET_A', VT.defaultConfig());
  const m = DR.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-31', ledger, hits, config: VT.defaultConfig(),
    runner: { state: 'READY', reason_codes: [], sources: R.statusRows(result) } });
  const screen = DR.screenHtml(m, { hidden: true }), text = DR.renderTemplate(m, { hidden: true, guide: false });
  assert.ok(screen.includes('data-cancel-reason="EXEC_FX_MISSING"') && text.includes('| 가상 주문 취소 | asml |'));
  assert.ok(screen.includes('data-source-symbol="XLK" data-source-code="REQUEST_INVALID"'));
  assert.ok(text.includes('- EXEC_FX_MISSING: 체결일 환율 결측으로 가상 주문 취소'));
  for (const out of [screen, text]) assert.equal((out.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length, 0);
  for (const t of ledger.days.at(-1).cancelled) assert.ok(!screen.includes(DR.formatKrw(t.amount)));
});

test('before the start date the engine still says NOT_STARTED and nothing is fetched', async () => {
  let calls = 0;
  const view = { localStorage: { getItem: () => null }, GoogleSheetQuotes: { sessionFor: () => { calls++; return null; } } };
  const r = await R.run(view, { config: { privateHistoryEnabled: true }, catalog: {}, reportDate: '2026-10-18' });
  assert.equal(r.state, 'NOT_STARTED');
  assert.deepEqual(r.reason_codes, ['BEFORE_START_DATE']);
  assert.equal(calls, 0);
  const l = R.ledgerFor(r, 'SET_A', VT.defaultConfig());
  assert.equal(l.ledger.state, 'NOT_STARTED');
  assert.deepEqual(l.ledger.days, []);
});

function fakeSession(handler) {
  const log = [];
  return { log, state: () => ({ enabled: true, connected: true }), revision: () => 1,
    async fetchHistory(origin, symbol, range, options) { log.push([origin, symbol, range, options.approvedOrigin]); return handler(symbol); } };
}
const fakeView = () => ({ setTimeout: (f) => setTimeout(f, 0), clearTimeout });

test('fetch layer: per-symbol degrade, SPY failure stops further requests, session failures stop the rest', async () => {
  R.clearCache();
  let s = fakeSession((symbol) => { const e = new Error(symbol === 'KRW=X' ? 'REQUEST_INVALID' : 'YAHOO_UNAVAILABLE'); if (symbol === 'ASML') return { ok: 1 }; throw e; });
  let out = await R.fetchHistories(fakeView(), { session: s, origin: 'https://a.b.workers.dev', symbols: ['SPY', 'KRW=X', 'ASML'], spacingMs: 0 });
  assert.deepEqual(out, { SPY: { error: 'YAHOO_UNAVAILABLE' } }, 'no request after SPY failed');
  assert.deepEqual(s.log.map((x) => x[1]), ['SPY']);
  assert.deepEqual(s.log[0], ['https://a.b.workers.dev', 'SPY', '2y', 'https://a.b.workers.dev']);
  R.clearCache();
  s = fakeSession((symbol) => { if (symbol === 'KRW=X') throw new Error('REQUEST_INVALID'); if (symbol === 'ASML') throw new Error('AUTH_REQUIRED'); return { symbol }; });
  out = await R.fetchHistories(fakeView(), { session: s, origin: 'https://a.b.workers.dev', symbols: ['SPY', 'KRW=X', 'ASML', 'LRCX', 'KLAC'], spacingMs: 0 });
  assert.deepEqual(out, { SPY: { symbol: 'SPY' }, 'KRW=X': { error: 'REQUEST_INVALID' }, ASML: { error: 'AUTH_REQUIRED' }, LRCX: { error: 'AUTH_REQUIRED' }, KLAC: { error: 'AUTH_REQUIRED' } });
  assert.deepEqual(s.log.map((x) => x[1]), ['SPY', 'KRW=X', 'ASML']);
  // RAM cache: a second run re-requests only what failed.
  s.log.length = 0;
  await R.fetchHistories(fakeView(), { session: s, origin: 'https://a.b.workers.dev', symbols: ['SPY', 'LRCX'], spacingMs: 0 });
  assert.deepEqual(s.log.map((x) => x[1]), ['LRCX']);
  R.clearCache();
});

test('fetch layer spaces Worker requests (5.2 s default, Worker allows one per 5 s)', async () => {
  R.clearCache();
  const waits = [], view = { setTimeout: (f, ms) => { waits.push(ms); return setTimeout(f, 0); }, clearTimeout };
  const s = fakeSession((symbol) => { if (symbol === 'KRW=X') throw new Error('REQUEST_INVALID'); return { symbol }; });
  await R.fetchHistories(view, { session: s, origin: 'https://a.b.workers.dev', symbols: ['SPY', 'KRW=X', 'ASML', 'LRCX'] });
  assert.deepEqual(waits, [5200, 5200], 'no wait for the first request nor after a client-side rejection');
  R.clearCache();
});

test('holdingsFromSnapshot maps catalog rows to company ids, drops zero quantities', () => {
  const catalog = fixture.vectors[0].inputs.catalog;
  const ref = (i) => catalog.instruments[i].security_reference;
  const snap = { effective_at: '2026-10-21T01:00:00+09:00', themes: [{ theme_id: 'x', holdings: [
    { security_reference: ref(5), quantity: '12.5', average_cost: '101.25', currency: 'USD' },
    { security_reference: ref(4), quantity: '0', average_cost: '1', currency: 'KRW' }] }] };
  assert.deepEqual(R.holdingsFromSnapshot(snap, catalog), { effective_at: snap.effective_at, positions: { nvda: { quantity: 12.5, average_cost: 101.25, currency: 'USD' } } });
  assert.equal(R.holdingsFromSnapshot(null, catalog), null);
});

test('DC-31: the stored device V history is never read (the key is left untouched), so the ledger gets no V scores', () => {
  const reads = [], store = { getItem: (k) => { reads.push(k); return k === R.V_KEY ? JSON.stringify({ schema: 'virtual-trading-v-scores/2', scores: { '2026-10-20': { nvda: 50 } }, composition: {} }) : null; } };
  assert.deepEqual(R.readVStore(store), {});assert.deepEqual(R.readVComposition(store), {});
  assert.deepEqual(reads, [], 'the V store key is not read');
  assert.deepEqual(R.readVStore({ getItem: () => { throw new Error('x'); } }), {});
});

test('module writes nothing: no storage writes, no logging, no network other than the session', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/virtual-trading-runner.js'), 'utf8');
  for (const word of ['setItem', 'indexedDB', 'console.', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'fetch(']) assert.ok(!src.includes(word), word);
});

test('v2 forward snapshots start on the prepared day, never join v1 scores or stored V', () => {
  const inputs=structuredClone(fixture.vectors.find(x=>x.name==='full_synthetic').inputs);
  inputs.forward_ledger.schema_version=2;
  inputs.forward_ledger.versions['forward_validation/v2']=[];
  let result=R.assemble(inputs);
  assert.equal(result.snapshot_basis,'v2');
  assert.deepEqual(result.ledgers.SET_A.input.sessions,[]);
  assert.deepEqual(result.ledgers.SET_A.input.snapshots,{});
  assert.deepEqual(result.ledgers.SET_A.input.v_scores,{});
  const record=structuredClone(inputs.forward_ledger.versions['forward_validation/v1'].find(r=>r.date==='2026-10-22'));
  record.version='forward_validation/v2';
  for(const row of Object.values(record.companies)){row.Q.score=90;row.G.score=80;}
  const unprepared=structuredClone(record);unprepared.date='2026-10-20';for(const row of Object.values(unprepared.companies)){row.Q.score=null;row.G.score=null;}
  inputs.forward_ledger.versions['forward_validation/v2']=[unprepared,record];
  result=R.assemble(inputs);
  assert.equal(result.ledgers.SET_A.input.sessions[0],'2026-10-22');
  assert.deepEqual(Object.keys(result.ledgers.SET_A.input.snapshots),['2026-10-20','2026-10-22']);
  assert.equal(result.ledgers.SET_A.input.snapshots['2026-10-22'].nvda.q,90);
  assert.deepEqual(result.ledgers.SET_A.input.v_scores,{});
  assert.deepEqual(result.ledgers.SET_A.input.v_composition,{});
});
