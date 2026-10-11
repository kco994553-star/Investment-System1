'use strict';
// Sheet #N/A → Worker close fallback (RAM only) and the WORKER_CLOSE source in DeviceMarket. Synthetic bars and prices only.
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const F = require(path.join(W, 'worker-quote-fallback.js')), M = require(path.join(W, 'device-market.js')), Q = require(path.join(W, 'google-sheet-quotes.js'));
const ORIGIN = 'https://synthetic-history.example.workers.dev';
function catalog() {
  const tickers = ['ASML', 'LRCX', 'KLAC', '8035', '042700', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MSFT', 'GOOGL', 'AMZN', 'RTX', 'SYK', 'ETN', 'HUBB', 'GEV', 'ROK'];
  return {schema: 'DEVICE_ACTUAL_CATALOG/1', target_root_version: 'v0', target_root_sha256: 'a'.repeat(64), identity_map_version: 'm', identity_map_sha256: 'b'.repeat(64), total_units: 10000,
    themes: [{theme_id: 't', target_units: 10000}],
    instruments: tickers.map((ticker, i) => ({row_index: i, ticker, label: 'Synthetic ' + ticker, theme_id: 't', target_units: i === 18 ? 1000 : 500,
      currency: ticker === '8035' ? 'JPY' : ticker === '042700' ? 'KRW' : 'USD', security_reference: {scheme: 'SYNTHETIC', value: 'ID_' + i}}))};
}
function history(symbol, bars, extra = {}) {
  return {schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range: '1mo', currency: symbol.endsWith('.T') ? 'JPY' : symbol.endsWith('.KS') ? 'KRW' : 'USD',
    exchange: 'SYN', timezone: symbol.endsWith('.T') ? 'Asia/Tokyo' : 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: '2025-02-05T08:00:00Z', bars, ...extra};
}
// 2025-02-03 and 2025-02-04 09:00 JST bars (00:00Z), then an in-progress bar.
const TEL_BARS = [{timestamp: Date.UTC(2025, 1, 3) / 1000, close: 101.5, session_status: 'COMPLETE'}, {timestamp: Date.UTC(2025, 1, 4) / 1000, close: 182.31000518798828, session_status: 'COMPLETE'},
  {timestamp: Date.UTC(2025, 1, 5) / 1000, close: 190, session_status: 'IN_PROGRESS'}];
function harness({connected = true, origin = ORIGIN, enabled = true, payloads = {}} = {}) {
  const listeners = new Set(), calls = [], events = [];
  let rev = 1, isConnected = connected;
  const session = {state: () => ({connected: isConnected}), revision: () => rev, subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    async fetchHistory(o, symbol, range, options) { calls.push([o, symbol, range, options.approvedOrigin]); const p = payloads[symbol]; if (p instanceof Error) throw p; if (!p) throw new Error('REQUEST_INVALID'); return p; }};
  const view = {localStorage: {getItem: key => key === 'investment.web.v1.private-history-origin' ? origin : null}, GoogleSheetQuotes: {historyOrigin: Q.historyOrigin, sessionFor: () => session, HISTORY_SYMBOLS: Q.HISTORY_SYMBOLS},
    DeviceMarket: M, document: {dispatchEvent: e => events.push(e.type)}, Event: class { constructor(type) { this.type = type; } }, addEventListener() {}};
  const config = {privateHistoryEnabled: enabled, privateHistoryWorkerOrigin: ORIGIN, googleSheetsClientId: 'synthetic-client'};
  return {view, session, config, calls, events, disconnect() { isConnected = false; for (const fn of listeners) fn(); }, bump() { rev++; for (const fn of listeners) fn(); }};
}
test('latestComplete picks the last COMPLETE close and labels its session date', () => {
  const r = F.latestComplete(history('8035.T', TEL_BARS), {symbol: '8035.T', currency: 'JPY'});
  assert.deepEqual(r, {price: '182.310005', currency: 'JPY', session_date: '2025-02-04'});
  const fallback = F.latestComplete(history('NVDA', [{timestamp: 1, session_date: '2025-02-03', close: 10, session_status: 'COMPLETE'}, {timestamp: 2, close: null, session_status: 'COMPLETE'}]), {symbol: 'NVDA'});
  assert.equal(fallback.session_date, '2025-02-03'); assert.equal(fallback.price, '10');
  assert.throws(() => F.latestComplete(history('8035.T', [TEL_BARS[2]]), {symbol: '8035.T'}), /NO_COMPLETE_SESSION/);
  assert.throws(() => F.latestComplete(history('8035.T', TEL_BARS), {symbol: '8035.T', currency: 'USD'}), /WORKER_FORMAT_CHANGED/);
  assert.throws(() => F.latestComplete(history('8035.T', [TEL_BARS[1], TEL_BARS[0]]), {symbol: '8035.T'}), /WORKER_FORMAT_CHANGED/);
  assert.throws(() => F.latestComplete(history('8035.T', TEL_BARS, {schema: 'x'}), {symbol: '8035.T'}), /WORKER_FORMAT_CHANGED/);
  assert.throws(() => F.latestComplete(history('8035.T', TEL_BARS), {symbol: 'NVDA'}), /WORKER_FORMAT_CHANGED/);
});
test('worker symbols and readiness codes', () => {
  assert.equal(F.workerSymbol('8035'), '8035.T'); assert.equal(F.workerSymbol('042700'), '042700.KS'); assert.equal(F.workerSymbol('KO'), 'KO'); assert.equal(F.workerSymbol('ko'), null);
  let h = harness(); assert.equal(F.readiness(h.view, h.config, h.session), 'READY');
  h = harness({enabled: false}); assert.equal(F.readiness(h.view, h.config, h.session), 'OFF');
  h = harness({origin: ''}); assert.equal(F.readiness(h.view, h.config, h.session), 'ORIGIN_UNAPPROVED');
  h = harness({origin: 'https://other-name.example.workers.dev'}); assert.equal(F.readiness(h.view, h.config, h.session), 'ORIGIN_UNAPPROVED');
  h = harness({connected: false}); assert.equal(F.readiness(h.view, h.config, h.session), 'AUTH_REQUIRED');
  assert.equal(F.label('ko-KR'), 'Worker 종가 · 일봉 · 정보용'); assert.equal(F.label('en-US'), 'Worker close · Daily bar · For information only');
});
test('after a sheet import, a #N/A TARGET quote gets the Worker close in RAM; the stored market never accepts it', async () => {
  const h = harness({payloads: {'8035.T': history('8035.T', TEL_BARS)}}), c = catalog();
  const result = {quotes: [], fx: [], successes: [{code: 'NASDAQ:NVDA', name: 'Synthetic NVDA'}], failures: [{code: 'TYO:8035', name: 'Synthetic 8035', state: 'NOT_AVAILABLE'}], warnings: []};
  const summary = await F.afterImport(h.view, {catalog: c, result, config: h.config, session: h.session, now: Date.UTC(2025, 1, 5, 8)});
  assert.deepEqual(summary, {filled: 1, failed: 0, tickers: ['8035']}); assert.deepEqual(h.calls, [[ORIGIN, '8035.T', '1mo', ORIGIN]]);
  assert.deepEqual(F.status(h.view, '8035'), {state: 'AVAILABLE', source: 'WORKER_CLOSE', session_date: '2025-02-04'});
  const market = F.overlay(h.view, c, null), quote = market.quotes[0];
  assert.equal(quote.source, 'WORKER_CLOSE'); assert.equal(quote.time_status, 'SESSION_CLOSE'); assert.equal(quote.as_of, '2025-02-04T00:00:00Z'); assert.equal(quote.price, '182.310005');
  assert.throws(() => M.makeMarket(c, [quote], [], null), /INVALID/); assert.throws(() => M.validateMarket(market, c), /INVALID/);
  assert.equal(M.validateMarket(market, c, {ramOverlay: true}).quotes.length, 1);
  assert.throws(() => M.withRamQuotes(null, c, [{...quote, time_status: 'KNOWN'}]), /INVALID/);
  assert.throws(() => M.withRamQuotes(null, c, [{...quote, as_of: '2025-02-04T06:30:00Z'}]), /INVALID/);
  const snapshot = {schema: 'device-actual-holdings/1', version: 1, kind: 'ACTUAL', ownership: 'USER_DEVICE_ONLY', owner: {role: 'USER', storage: 'USER_DEVICE_ONLY'},
    effective_at: '2025-02-01T00:00:00.000Z', available_at: '2025-02-01T00:00:00.000Z', target_root_version: 'v0', target_root_sha256: 'a'.repeat(64), identity_map_version: 'm', identity_map_sha256: 'b'.repeat(64),
    themes: [{theme_id: 't', holdings: [{security_reference: {scheme: 'SYNTHETIC', value: 'ID_3'}, quantity: '2', average_cost: '1', currency: 'JPY'}]}]};
  const row = M.valuation(snapshot, c, market, {ramOverlay: true}).rows[0];
  assert.equal(row.quote_source, 'WORKER_CLOSE'); assert.equal(row.market_value_native, 2 * 182.310005); assert.equal(row.fx_status, 'NOT_AVAILABLE');
  assert.throws(() => M.valuation(snapshot, c, market), /INVALID/);
});
test('overlay rule: MANUAL and newer sheet values win; older GOOGLEFINANCE values from before the #N/A import are replaced', async () => {
  const h = harness({payloads: {'8035.T': history('8035.T', TEL_BARS)}}), c = catalog(), ref = {scheme: 'SYNTHETIC', value: 'ID_3'};
  await F.fill(h.view, {catalog: c, tickers: ['8035'], config: h.config, session: h.session, now: Date.UTC(2025, 1, 5, 8)});
  const make = (source, at) => M.makeMarket(c, [{security_reference: ref, price: '90', currency: 'JPY', as_of: at, available_at: at, source, ...(source === 'GOOGLEFINANCE' ? {time_status: 'KNOWN'} : {})}], [], null);
  assert.equal(F.overlay(h.view, c, make('MANUAL', '2025-02-01T00:00:00.000Z')).quotes[0].source, 'MANUAL');
  assert.equal(F.overlay(h.view, c, make('GOOGLEFINANCE', '2025-02-01T00:00:00.000Z')).quotes[0].source, 'WORKER_CLOSE');
  assert.equal(F.overlay(h.view, c, make('GOOGLEFINANCE', '2025-02-05T09:00:00.000Z')).quotes[0].source, 'GOOGLEFINANCE');
});
test('Worker unavailable → NOT_AVAILABLE with the reason; a stop code ends the remaining reads', async () => {
  let h = harness({connected: false}); const c = catalog();
  await F.fill(h.view, {catalog: c, tickers: ['8035'], config: h.config, session: h.session});
  assert.deepEqual(F.status(h.view, '8035'), {state: 'NOT_AVAILABLE', reason: 'AUTH_REQUIRED'}); assert.equal(h.calls.length, 0); assert.equal(F.overlay(h.view, c, null), null);
  h = harness({payloads: {'8035.T': new Error('RATE_LIMITED'), 'NVDA': history('NVDA', TEL_BARS.slice(0, 1))}});
  await F.fill(h.view, {catalog: c, tickers: ['8035', 'NVDA'], config: h.config, session: h.session});
  assert.deepEqual(F.status(h.view, '8035'), {state: 'NOT_AVAILABLE', reason: 'RATE_LIMITED'}); assert.deepEqual(F.status(h.view, 'NVDA'), {state: 'NOT_AVAILABLE', reason: 'RATE_LIMITED'}); assert.equal(h.calls.length, 1);
  h = harness({payloads: {'8035.T': history('8035.T', [TEL_BARS[2]])}});
  await F.fill(h.view, {catalog: c, tickers: ['8035', 'NOT_IN_CATALOG'], config: h.config, session: h.session});
  assert.deepEqual(F.status(h.view, '8035'), {state: 'NOT_AVAILABLE', reason: 'NO_COMPLETE_SESSION'}); assert.equal(F.status(h.view, 'NOT_IN_CATALOG'), null);
});
test('RAM entries vanish on sign-out or a new session and when the sheet quote works again', async () => {
  const c = catalog(), h = harness({payloads: {'8035.T': history('8035.T', TEL_BARS)}});
  await F.fill(h.view, {catalog: c, tickers: ['8035'], config: h.config, session: h.session}); assert.ok(F.has(h.view));
  h.disconnect(); assert.equal(F.has(h.view), false); assert.equal(F.status(h.view, '8035'), null); assert.ok(h.events.includes('device-actual-changed'));
  const g = harness({payloads: {'8035.T': history('8035.T', TEL_BARS)}});
  await F.fill(g.view, {catalog: c, tickers: ['8035'], config: g.config, session: g.session}); g.bump(); assert.equal(F.has(g.view), false);
  const k = harness({payloads: {'8035.T': history('8035.T', TEL_BARS)}});
  await F.fill(k.view, {catalog: c, tickers: ['8035'], config: k.config, session: k.session});
  await F.afterImport(k.view, {catalog: c, result: {quotes: [], fx: [], successes: [{code: 'TYO:8035', name: 'x'}], failures: [], warnings: []}, config: k.config, session: k.session});
  assert.equal(F.status(k.view, '8035'), null); assert.equal(k.calls.length, 1);
});
