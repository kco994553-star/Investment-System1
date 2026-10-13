'use strict';
// Price store (Prices_D / Prices_M tabs): the JS pure part must equal the Python reference on the shared SYNTHETIC vectors,
// and the sheet layer, run on the real GoogleSheetQuotes session over an in-memory SYNTHETIC sheet and Worker, must:
// stay OFF until the user turns it on; create only its own two tabs with the fixed header; refuse a different header;
// append only rows not stored (never rewrite; a provider revision is only counted); fetch only the missing range; give the
// virtual-trading runner exactly the closes its own Worker path gives; request only allowlisted Universe504 symbols;
// never read Example_* tabs; keep closes out of localStorage and the console.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ASSETS = path.join(__dirname, '../src/investment_system/product/web_assets');
const P = require(path.join(ASSETS, 'price-store.js'));
const Q = require(path.join(ASSETS, 'google-sheet-quotes.js'));
const R = require(path.join(ASSETS, 'virtual-trading-runner.js'));
const Setup = require(path.join(ASSETS, 'google-sheet-setup.js'));
const History = require(path.join(ASSETS, 'private-history.js'));
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/price_store_v1.json'), 'utf8'));
const inputs = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_inputs_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));
const err = (fn) => { try { return plain(fn()); } catch (e) { return { error: e.message }; } };

test('fixture is marked synthetic', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
  assert.deepEqual([...P.HEAD], fixture.head);
  assert.deepEqual(plain(P.TABS), fixture.tabs_by_interval);
});

test('tab parsing and indexing equal Python', () => {
  for (const v of fixture.tabs) assert.deepEqual(err(() => P.parseTab(v.values, v.interval)), v.expected, v.name);
  for (const v of fixture.indexes) assert.deepEqual(plain(P.indexRows(v.rows, v.interval)), v.expected, v.name);
});

test('Worker payload → final closes (the runner rule) and source equal Python', () => {
  for (const v of fixture.histories) {
    assert.deepEqual(plain(P.closesFromHistory(v.payload, v.symbol)), v.expected, v.name);
    assert.equal(P.sourceOf(v.payload), v.source, v.name);
  }
});

test('month-ends, due dates, ranges, plans, rows, merged reads and runner payloads equal Python', () => {
  for (const v of fixture.month_ends) assert.deepEqual(plain(P.monthEnds(v.closes, v.as_of)), v.expected, v.name);
  for (const v of fixture.due) assert.deepEqual(err(() => P.dueDate(v.symbol, v.day, v.time)), v.expected, v.symbol + ' ' + v.day + ' ' + v.time);
  for (const v of fixture.ranges.daily) assert.equal(P.nextRange(v.last, v.due, v.today), v.expected, String(v.last));
  for (const v of fixture.ranges.monthly) { assert.equal(P.monthDue(v.today), v.due); assert.equal(P.nextMonthRange(v.last_month, v.today), v.expected, String(v.last_month)); }
  for (const v of fixture.ranges.months_back) assert.equal(P.monthsBack(v.today, v.months), v.expected);
  for (const v of fixture.plans) assert.deepEqual(plain(P.appendPlan(v.stored, v.fetched, v.interval)), v.expected, v.name);
  for (const v of fixture.rows) assert.deepEqual(P.sheetRows(v.symbol, v.rows, v.source, v.fetched_at), v.expected);
  for (const v of fixture.merged) assert.deepEqual(plain(P.monthEndClosesOf(v.daily, v.monthly, v.as_of)), v.expected, v.name);
  for (const v of fixture.daily) assert.deepEqual(plain(P.dailyClosesOf(v.daily, v.from)), v.expected);
  for (const v of fixture.runner) {
    const p = P.runnerPayload(v.closes, v.symbol, v.today, v.read_at);
    assert.deepEqual(plain(p), v.expected, v.symbol);
    assert.deepEqual(plain(R.seriesFromHistory(p, v.symbol, P.currencyFor(v.symbol))), v.runner_closes, v.symbol);
  }
  for (const v of fixture.chunks) assert.deepEqual(P.chunkRows(v.rows, v.max_bytes), v.expected);
  for (const v of fixture.universe) assert.equal(P.universeSymbol(v.code), v.expected, String(v.code));
});

/* ---------- harness: real GoogleSheetQuotes session over an in-memory SYNTHETIC sheet and Worker ---------- */
const ID = ['synthetic', 'price', 'store', 'sheet', 'id'].join('_');
const ORIGIN = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'price', 'store'].join('-');
const SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const DAY_MS = 86400000;
function weekdays(from, to) { const out = []; for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += DAY_MS) { const d = new Date(t); if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); } return out; }
function workerPayload(symbol, range, readAt, closeFor) {
  const days = { '1mo': 31, '3mo': 92, '6mo': 183, '1y': 366, '2y': 731, '5y': 1827 }[range];
  const end = readAt.slice(0, 10), start = new Date(Date.parse(end + 'T00:00:00Z') - days * DAY_MS).toISOString().slice(0, 10);
  const bars = weekdays(start, end).map((d) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null, close: closeFor(symbol, d), adjusted_close: null, volume: null,
    session_status: d === end ? 'IN_PROGRESS' : 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: P.currencyFor(symbol), exchange: 'SYNTHETIC', timezone: P.timezoneFor(symbol), interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: readAt, bars };
}
const synthClose = (symbol, d) => 100 + symbol.length + (Date.parse(d + 'T00:00:00Z') / DAY_MS % 17) / 4;
function harness({ tabs = {}, worker = null, codes = ['NASDAQ:NVDA', 'NYSE:BRK.B', 'NYSE:MMM', 'NASDAQ:MSFT'] } = {}) {
  const sheet = new Map(Object.entries(tabs)), requests = [], workerCalls = [], local = new Map();
  let callbacks, readAt = '2026-10-13T21:00:00Z';
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
  const col = (c) => c.charCodeAt(0) - 64;
  const view = {
    setTimeout: (f, ms) => { const t = setTimeout(f, ms); t.unref(); return t; }, clearTimeout: (t) => clearTimeout(t), AbortController,
    google: { accounts: { oauth2: { initTokenClient(config) { callbacks = config; return { requestAccessToken() {} }; }, revoke(_t, done) { done({}); } } } },
    localStorage: { getItem: (k) => (local.has(k) ? local.get(k) : null), setItem: (k, v) => local.set(k, String(v)), removeItem: (k) => local.delete(k) },
    async fetch(url, options = {}) {
      const method = options.method || 'GET';
      if (url === 'universe-codes.json') return new Response(JSON.stringify({ schema: 'universe-codes/1', codes }), { status: 200 });
      const u = new URL(url);
      if (u.origin === ORIGIN) {
        const symbol = u.searchParams.get('symbol'), range = u.searchParams.get('range');
        workerCalls.push([symbol, range]);
        const answer = worker ? worker(symbol, range, readAt) : null;
        if (answer && answer.error) return json({ error: { code: answer.error } }, answer.status || 400);
        return json(answer || workerPayload(symbol, range, readAt, synthClose));
      }
      const p = decodeURIComponent(u.pathname).replace('/v4/spreadsheets/' + ID, '');
      requests.push([method, p.split('!')[0]]);
      if (method === 'GET' && p === '' && u.searchParams.get('fields') === 'sheets(properties(title))') return json({ sheets: [...sheet.keys()].map((title) => ({ properties: { title } })) });
      if (method === 'POST' && p === ':batchUpdate') { const body = JSON.parse(options.body); for (const r of body.requests) sheet.set(r.addSheet.properties.title, []); return json({ replies: [] }); }
      const m = /^\/values\/'([^']+)'!([A-Z])(\d+)(?::([A-Z])(\d+))?(:append)?$/.exec(p);
      if (!m) return json({ error: 'unexpected' }, 404);
      const rows = sheet.get(m[1]);
      if (!rows) return json({ error: 'no tab' }, 400);
      if (m[6]) { for (const r of JSON.parse(options.body).values) rows.push([...r]); return json({ updates: {} }); }
      const from = +m[3], to = +m[5], c1 = col(m[2]) - 1, c2 = col(m[4]);
      const values = rows.slice(from - 1, to).map((r) => r.slice(c1, c2));
      while (values.length && !values[values.length - 1].some((c) => c !== '')) values.pop();
      return json(values.length ? { range: m[1], values } : { range: m[1] });
    },
  };
  const session = Q.createSession(view, { clientId: 'public-client-id' });
  session.setEnabled(true);
  view.InvestmentAppConfig = { googleSheetsClientId: 'public-client-id', privateHistoryEnabled: true, privateHistoryWorkerOrigin: ORIGIN, virtualTradingRequestSpacingMs: 0, universeCodeCatalogURL: 'universe-codes.json' };
  view.GoogleSheetQuotes = { sessionFor: () => session, HISTORY_SYMBOLS: Q.HISTORY_SYMBOLS, extractSpreadsheetId: Q.extractSpreadsheetId };
  view.GoogleSheetSetup = { source: () => ID, codes: Setup.codes };
  view.PrivateHistory = { parseWorkerOrigin: History.parseWorkerOrigin };
  local.set('investment.web.v1.private-history-origin', ORIGIN);
  return { view, session, sheet, requests, workerCalls, local, setReadAt: (v) => { readAt = v; },
    connect: async () => { await session.prepare(); session.login(); callbacks.callback({ access_token: TOKEN, expires_in: 3600, scope: SCOPE }); } };
}
const at = (iso) => () => Date.parse(iso);
const HEADER = [...P.HEAD];

test('OFF until the user turns it on: no sheet or Worker request, runner keeps its own path, API returns NA', async () => {
  const h = harness(); await h.connect();
  assert.equal(P.status({ view: h.view }).state, 'OFF');
  assert.equal(await P.runnerHistories(h.view, { session: h.session, origin: ORIGIN, symbols: ['SPY'] }), null);
  assert.deepEqual(await P.monthEndCloses('NVDA', { view: h.view }), {});
  assert.deepEqual(await P.dailyCloses('SPY', null, { view: h.view }), {});
  assert.deepEqual([h.requests.length, h.workerCalls.length], [0, 0]);
});

test('turning it on creates only Prices_D / Prices_M with the fixed header; a different header is never written', async () => {
  const h = harness({ tabs: { Quotes: [['code', 'price', 'tradetime']], Example_Prices_D: [['x']] } }); await h.connect();
  const s = await P.enable(h.view);
  assert.equal(s.state, 'READY');
  assert.deepEqual(h.sheet.get('Prices_D'), [HEADER]);
  assert.deepEqual(h.sheet.get('Prices_M'), [HEADER]);
  assert.deepEqual(h.sheet.get('Quotes'), [['code', 'price', 'tradetime']]);
  assert.ok(h.requests.every(([, p]) => !p.includes('Example_')), 'Example_* tab never touched');
  assert.equal(h.local.get(P.FLAG_KEY), '1');
  const bad = harness({ tabs: { Prices_D: [['symbol', 'date', 'interval', 'close', 'source', 'fetched_at'], ['SPY', '2026-10-01', '1d', '1']] } }); await bad.connect();
  await assert.rejects(P.enable(bad.view), /SHEET_HEADER_MISMATCH/);
  assert.equal(bad.sheet.has('Prices_M'), false);
  assert.equal(bad.sheet.get('Prices_D').length, 2);
  assert.equal(bad.requests.filter(([m]) => m === 'POST').length, 0, 'no write at all');
  assert.equal(bad.local.has(P.FLAG_KEY), false);
});

test('daily sync: first run 5y, then only the missing range; stored rows never rewritten; revisions counted; RAM only', async () => {
  const h = harness(); await h.connect(); await P.enable(h.view);
  const logs = []; const orig = { log: console.log, error: console.error, warn: console.warn };
  console.log = console.error = console.warn = (...a) => logs.push(a.join(' '));
  try {
    const first = await P.syncMany(h.view, ['SPY', 'KRW=X'], '1d', { now: at('2026-10-13T21:00:00Z') });
    assert.deepEqual(h.workerCalls, [['SPY', '5y'], ['KRW=X', '5y']]);
    assert.equal(first.failed && Object.keys(first.failed).length, 0);
    const rows = h.sheet.get('Prices_D');
    assert.deepEqual(rows[0], HEADER);
    const spy = rows.filter((r) => r[0] === 'SPY');
    assert.ok(spy.length > 1200 && spy.every((r) => r.length === 5 && typeof r[2] === 'string' && r[3] === 'YAHOO'));
    assert.equal(spy.at(-1)[1], '2026-10-12', 'the in-progress bar of the read day is not stored');
    assert.equal(h.sheet.get('Prices_M').length, 1, 'daily sync writes no month-end rows');
    // Same session, same day: nothing requested again.
    await P.syncMany(h.view, ['SPY'], '1d', { now: at('2026-10-13T22:00:00Z') });
    assert.equal(h.workerCalls.length, 2);
    // A new sign-in two days later: only the tail is requested (1mo window), the stored rows stay, a revised close is ignored.
    await h.connect(); h.setReadAt('2026-10-15T21:00:00Z');
    const before = h.sheet.get('Prices_D').map((r) => r.join('|'));
    const revised = (symbol, d) => (d === '2026-10-09' ? 1 : synthClose(symbol, d));
    const h2worker = (symbol, range, readAt) => workerPayload(symbol, range, readAt, revised);
    h.view.fetch = ((orig) => async (url, o) => { const u = String(url); if (u.startsWith(ORIGIN)) { const q = new URL(u); h.workerCalls.push([q.searchParams.get('symbol'), q.searchParams.get('range')]); return new Response(JSON.stringify(h2worker(q.searchParams.get('symbol'), q.searchParams.get('range'), '2026-10-15T21:00:00Z')), { status: 200 }); } return orig(url, o); })(h.view.fetch);
    const second = await P.syncMany(h.view, ['SPY'], '1d', { now: at('2026-10-15T21:00:00Z') });
    assert.deepEqual(h.workerCalls.at(-1), ['SPY', '1mo']);
    const after = h.sheet.get('Prices_D').map((r) => r.join('|'));
    assert.deepEqual(after.slice(0, before.length), before, 'existing rows unchanged');
    assert.deepEqual(after.slice(before.length).map((r) => r.split('|').slice(0, 2).join(' ')), ['SPY 2026-10-13', 'SPY 2026-10-14']);
    assert.equal(second.appended_rows, 2);
    assert.equal(P.status({ view: h.view }).revised_ignored, 1);
    const closes = await P.dailyCloses('SPY', '2026-10-08', { view: h.view, fetch: false });
    assert.deepEqual(Object.keys(closes), ['2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14']);
    assert.equal(closes['2026-10-09'], synthClose('SPY', '2026-10-09'), 'the stored close wins over the revision');
    const cov = P.coverage('SPY', { view: h.view });
    assert.equal(cov.daily.last, '2026-10-14');
    assert.ok(!JSON.stringify(cov).includes(String(closes['2026-10-09'])), 'coverage has dates and counts only');
  } finally { Object.assign(console, orig); }
  assert.deepEqual(logs, [], 'nothing logged');
  assert.deepEqual([...h.local.keys()].sort(), [P.FLAG_KEY, 'investment.web.v1.private-history-origin'].sort());
  assert.ok(![...h.local.values()].some((v) => /\d+\.\d+/.test(v) && !v.startsWith('https://')), 'no close in localStorage');
});

test('month-ends: first open of a viewed symbol stores 5 years once; then no request; non-allowlisted symbols are not requested', async () => {
  const h = harness(); await h.connect(); await P.enable(h.view);
  h.setReadAt('2026-10-13T21:00:00Z');
  const now = at('2026-10-13T21:00:00Z');
  {
    const m = await P.monthEndCloses('NVDA', { view: h.view, now });
    assert.deepEqual(h.workerCalls, [['NVDA', '5y']]);
    const keys = Object.keys(m);
    assert.equal(keys.at(-1), '2026-09', 'only complete months');
    assert.ok(keys.length >= 59 && keys.length <= 61);
    const rows = h.sheet.get('Prices_M').slice(1);
    assert.equal(rows.length, keys.length);
    assert.ok(rows.every((r) => r[0] === 'NVDA' && /^\d{4}-\d{2}-\d{2}$/.test(r[1])));
    assert.equal(rows.find((r) => r[1].startsWith('2026-09'))[1], '2026-09-30');
    assert.deepEqual(await P.monthEndCloses('NVDA', { view: h.view, now }), m);
    assert.equal(h.workerCalls.length, 1);
    assert.deepEqual(await P.monthEndCloses('BRK-B', { view: h.view, now }), {});
    assert.equal(h.workerCalls.length, 1, 'BRK-B is outside the Worker allowlist: no request');
  }
});

test('Universe504 button: allowlisted symbols get month-ends, the rest count as WORKER_ALLOWLIST; core symbols reuse daily rows', async () => {
  const h = harness(); await h.connect(); await P.enable(h.view);
  await P.syncMany(h.view, ['MSFT'], '1d', { now: at('2026-10-13T21:00:00Z') });
  h.workerCalls.length = 0;
  const r = await P.syncUniverse(h.view, { now: at('2026-10-13T21:00:00Z') });
  assert.equal(r.state, 'READY');
  assert.equal(r.universe, 4);
  assert.equal(r.not_allowed, 2);
  assert.deepEqual(h.workerCalls, [['NVDA', '5y']], 'MSFT month-ends come from its stored daily rows; BRK-B and MMM are not requested');
  const again = await P.syncUniverse(h.view, { now: at('2026-10-14T21:00:00Z') });
  assert.equal(again.fetched, 0);
  assert.equal(h.workerCalls.length, 1);
});

test('runner integration: stored + missing ranges give exactly the closes of the runner\'s own Worker path', async () => {
  const v = inputs.vectors.find((x) => x.name === 'full_synthetic');
  const symbols = R.requiredSymbols(v.inputs);
  const answer = (symbol) => (Object.prototype.hasOwnProperty.call(v.inputs.histories, symbol) ? v.inputs.histories[symbol] : { error: 'HISTORY_UNAVAILABLE', status: 404 });
  const worker = (symbol) => { const a = answer(symbol); return a && a.error ? { error: a.error, status: a.error === 'REQUEST_INVALID' ? 400 : 404 } : a; };
  const now = at('2026-10-30T22:00:00Z');
  // Own path (store OFF).
  const own = harness({ worker }); await own.connect();
  R.clearCache();
  const direct = await R.fetchHistories(own.view, { session: own.session, origin: ORIGIN, symbols, spacingMs: 0 });
  // Store path.
  const h = harness({ worker }); await h.connect(); await P.enable(h.view);
  const viaStore = await P.runnerHistories(h.view, { session: h.session, origin: ORIGIN, symbols, spacingMs: 0, now });
  assert.ok(viaStore);
  for (const s of symbols) assert.deepEqual(plain(R.seriesFromHistory(viaStore[s], s, P.currencyFor(s))), plain(R.seriesFromHistory(direct[s], s, P.currencyFor(s))), s);
  const a = R.assemble({ ...v.inputs, histories: direct }), b = R.assemble({ ...v.inputs, histories: viaStore });
  assert.deepEqual(plain(b), plain(a));
  // Second run in the same session: only the symbols that failed are requested again (as the runner's own cache does).
  const calls = h.workerCalls.length, failed = symbols.filter((s) => direct[s].error);
  assert.ok(failed.includes('XLK') && failed.length < symbols.length);
  const again = await P.runnerHistories(h.view, { session: h.session, origin: ORIGIN, symbols, spacingMs: 0, now });
  assert.deepEqual(h.workerCalls.slice(calls).map((c) => c[0]), failed);
  assert.deepEqual(plain(R.assemble({ ...v.inputs, histories: again })), plain(a));
});

test('runner integration: a failed missing range gives the same {error} (never a stale series); SPY failure stops', async () => {
  let fail = false;
  const worker = (symbol, range, readAt) => (fail && symbol !== 'SPY' ? { error: 'YAHOO_UNAVAILABLE', status: 503 } : workerPayload(symbol, range, readAt, synthClose));
  const h = harness({ worker }); await h.connect(); await P.enable(h.view);
  await P.runnerHistories(h.view, { session: h.session, origin: ORIGIN, symbols: ['SPY', 'NVDA'], spacingMs: 0, now: at('2026-10-13T21:00:00Z') });
  await h.connect(); fail = true; h.setReadAt('2026-10-15T21:00:00Z');
  const out = await P.runnerHistories(h.view, { session: h.session, origin: ORIGIN, symbols: ['SPY', 'NVDA'], spacingMs: 0, now: at('2026-10-15T21:00:00Z') });
  assert.deepEqual(out.NVDA, { error: 'YAHOO_UNAVAILABLE' });
  assert.equal(out.SPY.provider, 'PRICE_STORE');
  const h2 = harness({ worker: () => ({ error: 'YAHOO_UNAVAILABLE', status: 503 }) }); await h2.connect(); await P.enable(h2.view);
  const stopped = await P.runnerHistories(h2.view, { session: h2.session, origin: ORIGIN, symbols: ['SPY', 'NVDA'], spacingMs: 0, now: at('2026-10-13T21:00:00Z') });
  assert.deepEqual(stopped, { SPY: { error: 'YAHOO_UNAVAILABLE' } });
  assert.deepEqual(h2.workerCalls, [['SPY', '5y']]);
});

test('malformed and duplicate stored rows are skipped and counted, never rewritten', async () => {
  const h = harness({ tabs: { Prices_D: [HEADER, ['SPY', '2026-10-09', '100.5', 'YAHOO', 'x'], ['SPY', '2026-10-09', '99', 'YAHOO', 'x'], ['SPY', 'bad', '1', 'YAHOO', 'x'], ['SPY', '2026-10-12', 101.5, 'YAHOO', 'x']], Prices_M: [HEADER] } });
  await h.connect(); h.local.set(P.FLAG_KEY, '1');
  const closes = await P.dailyCloses('SPY', null, { view: h.view, fetch: false });
  assert.deepEqual(closes, { '2026-10-09': 100.5 });
  const s = P.status({ view: h.view });
  assert.deepEqual([s.state, s.invalid_rows, s.duplicate_rows], ['READY', 2, 1]);
  assert.equal(h.requests.filter(([m]) => m === 'POST').length, 0);
  P.disable(h.view);
  assert.equal(P.status({ view: h.view }).state, 'OFF');
  assert.equal(h.local.has(P.FLAG_KEY), false);
});
