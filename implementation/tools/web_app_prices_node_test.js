'use strict';
// New frontend P1 · device prices and device storage (web_app/prices.js, store.js), on the real old modules.
//  - Click rule: without a trusted click of the right kind no private request leaves (Sheets, OAuth, Worker), whoever asks:
//    the prices API, the price view itself, or an old module handed the price view; a synthetic event or a plain object
//    claiming isTrusted is refused. The fake fetch records every request, so "refused" means zero private calls.
//  - One price view: GoogleSheetQuotes.sessionFor and every PriceStore call receive it (spies), including through the facade
//    and the QGV score path; the facade answers {} / null until a click read the tabs in this sign-in and never enters
//    PriceStore's reads before (a fetch:false read would still load the tabs from the Sheet).
//  - The Universe read equals PrivateSubsetView.mount's click run with a fake session on the M3 rows (same kept prices,
//    basis, status and rank index); sign-out clears it, an expired sign-in keeps it, a failed read keeps it and records why.
//  - Store: old keys unchanged; reads free; writes only in a click (CLICK_REQUIRED before, ACTION_REQUIRED for an old writer
//    handed the gated storage, storage unchanged); backups /1–/5 round trip (/5 user objects through the old validators);
//    IndexedDB never created by a read. Recent searches (P2-1): the old home's key and shape (entity keys only, at most 6,
//    newest first, invalid entries dropped on read, the query text never stored); pushRecent / clearRecent only in a click.
//  - Device quotes stopped (owner 2026-10-24, DC-18): a valid stored 'market' record that the old path reads is never read by
//    quote() or the score path, never written by an old writer even inside a click, never deleted automatically;
//    marketQuotes.count() gives a number without opening a missing database, clear() works only on a trusted click and keeps
//    every other record; no price value comes back.
//  - Google on/off (owner 2026-10-24, Main pick): saved only inside the prepare click (the old sign-in click), read only from an
//    existing database, left as it is by a sign-out.
//  - Period returns (P2-2a): periodReturns is async; NOT_LOADED and no request before the price-tab click; 60D/120D/YTD/1Y/
//    SINCE_START PERIOD_PENDING; values equal ReportBenchmarks.periodWindow + priceIndex (USD) over the loaded closes; a
//    Universe code reads PriceStore.universeSymbol, a ticker '.' -> '-'; identity stops come first (before and after the tabs);
//    no SPY -> RETURN_SESSIONS_NOT_AVAILABLE, a short calendar -> RETURN_HISTORY_TOO_SHORT; frozen, no storage write.
// Synthetic data only: the sheet, Worker and share counts are in-memory fixtures; sentinel prices are made-up decimals.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const nodeCrypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');
const SHARES = require('./sec_universe_shares_fixture.js');

const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
const CUSTOM = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_v2_custom_vectors_v1.json'), 'utf8'));
const CODES_FILE = { schema: 'universe-codes/1', codes: SHARES.CODES };
const SHEETS = 'https://sheets.googleapis.com', WORKER = 'https://private-investment-history.kco994553.workers.dev';
const ID = ['synthetic', 'price', 'layer', 'sheet', 'id'].join('_');
const TOKEN = ['memory', 'only', 'synthetic', 'session'].join('-'), SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const UNIVERSE_RANGE = "'Universe'!A1:C1025", DAY = 86400000, READ_AT = '2026-10-13T21:00:00Z';
const HEAD = ['symbol', 'date', 'close', 'source', 'fetched_at'];
// Synthetic sentinel prices: made-up decimals (.0731946 for the Universe tab, .0718293 for closes) that no score can contain.
const px = (v) => v + 0.0731946, PX = /\.0731946/, CLOSE = /\.0718293/;
const close = (symbol, d) => 211 + symbol.length + (Date.parse(d + 'T00:00:00Z') / DAY % 13) + 0.0718293;
// The M3 end-to-end rows of the M3 reference tests (sec_universe_shares_browser_test.js): single class within tolerance, share-class
// basis shown uncorrected, basis unconfirmed, stale row, the Alphabet group with its unlisted class B valued at GOOGL, Fox with a
// member price missing, and 16 Universe rows without public share counts.
const ABC = ['CommonClassAMember', 'CommonClassBMember', 'CommonClassCMember'];
const M3_ROWS = { 'NASDAQ:ADBE': { n: 1 }, 'NYSE:MMM': { n: 3, basis: 'SHARE_CLASS_BASIS', shares: 500 }, 'NASDAQ:AMD': { n: 4, basis: 'BASIS_UNCONFIRMED' }, 'NYSE:BRK.B': { n: 2, stale: true },
  'NASDAQ:GOOGL': { n: 1652044, basis: 'SHARE_CLASS_BASIS', shares: 5800, members: ABC, member: 'CommonClassAMember', unlisted: [{ class_member: 'CommonClassBMember', shares: 300 }] },
  'NASDAQ:GOOG': { n: 1652044, basis: 'SHARE_CLASS_BASIS', shares: 5400, members: ABC, member: 'CommonClassCMember' },
  'NASDAQ:FOXA': { n: 1754301, basis: 'SHARE_CLASS_BASIS', shares: 300 }, 'NASDAQ:FOX': { n: 1754301, basis: 'SHARE_CLASS_BASIS', shares: 200, member: 'CommonClassBMember' } };
const M3_VALUES = [['code', 'marketcap', 'price'], ['NASDAQ:ADBE', 10500, px(10)], ['NYSE:MMM', 9000, px(10)], ['NASDAQ:AMD', 1, px(1)], ['NYSE:BRK.B', 1, px(1)], ['NASDAQ:GOOGL', 1735000, px(150)],
  ['NASDAQ:GOOG', 1735000, px(151)], ['NASDAQ:FOXA', 15000, px(30)], ['NASDAQ:FOX', 15000, ''], ...SHARES.CODES.filter((c) => !M3_ROWS[c]).slice(0, 16).map((c, i) => [c, 1, px(1 + i)])];
const fresh = (name) => { delete require.cache[require.resolve(R.newPath(name))]; return R.requireNew(name); };
const plain = (v) => JSON.parse(JSON.stringify(v));

function weekdays(from, to) { const out = []; for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += DAY) { const d = new Date(t); if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); } return out; }
// A private-history/1 answer of the Worker (same shape as price_store_node_test's), synthetic closes.
function workerPayload(symbol, range, readAt) {
  const days = { '1mo': 31, '3mo': 92, '6mo': 183, '1y': 366, '2y': 731, '5y': 1827 }[range], end = readAt.slice(0, 10), start = new Date(Date.parse(end + 'T00:00:00Z') - days * DAY).toISOString().slice(0, 10);
  const bars = weekdays(start, end).map((d) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null, close: close(symbol, d), adjusted_close: null, volume: null, session_status: d === end ? 'IN_PROGRESS' : 'COMPLETE' }));
  const currency = symbol.endsWith('.KS') ? 'KRW' : symbol.endsWith('.T') ? 'JPY' : 'USD', timezone = symbol.endsWith('.KS') ? 'Asia/Seoul' : symbol.endsWith('.T') ? 'Asia/Tokyo' : 'America/New_York';
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency, exchange: 'SYNTHETIC', timezone, interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: readAt, bars };
}
/* The site: public files, the user's sheet (in memory, the Sheets v4 calls the old modules make) and the Worker. */
function site({ tabs = {}, codes = CODES_FILE, shares = SHARES.payload(M3_ROWS), extra = {} } = {}) {
  const sheet = new Map(Object.entries(tabs).map(([k, v]) => [k, v.map((r) => [...r])])), state = { failValues: false };
  const reply = (body, status = 200) => ({ status, json: body }), col = (c) => c.charCodeAt(0) - 64;
  const files = (name, init = {}) => {
    if (!/^https:\/\//.test(name)) return { 'sec-qgv2.json': { json: F.strictPayload() }, 'actual-catalog.json': { json: CATALOG }, 'universe-codes.json': { json: codes }, 'sec-universe-shares.json': { json: shares }, ...extra }[name] || null;
    const u = new URL(name), method = String(init.method || 'GET').toUpperCase();
    if (u.origin === WORKER) return u.pathname === '/history' ? reply(workerPayload(u.searchParams.get('symbol'), u.searchParams.get('range'), READ_AT)) : reply({ error: { code: 'REQUEST_INVALID' } }, 400);
    if (u.origin !== SHEETS) return reply({}, 599);
    const p = decodeURIComponent(u.pathname).replace('/v4/spreadsheets/' + ID, '');
    if (method === 'GET' && p === '') return reply({ sheets: [...sheet.keys()].map((title) => ({ properties: { title } })) });
    if (method === 'POST' && p === ':batchUpdate') { for (const r of JSON.parse(init.body).requests) sheet.set(r.addSheet.properties.title, []); return reply({ replies: [] }); }
    const m = /^\/values\/'([^']+)'!([A-Z])(\d+)(?::([A-Z])(\d+))?(:append)?$/.exec(p);
    if (!m || state.failValues) return reply({ error: 'unexpected' }, 500);
    const rows = sheet.get(m[1]); if (!rows) return reply({ error: 'no tab' }, 400);
    if (m[6]) { for (const r of JSON.parse(init.body).values) rows.push([...r]); return reply({ updates: {} }); }
    const values = rows.slice(+m[3] - 1, +m[5]).map((r) => r.slice(col(m[2]) - 1, col(m[4])));
    while (values.length && !values[values.length - 1].some((c) => c !== '')) values.pop();
    return reply(values.length ? { range: m[1], majorDimension: 'ROWS', values } : { range: m[1] });
  };
  return { sheet, state, files };
}
function memoryStorage(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { map: m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); }, clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; } };
}
// GIS stand-in (the CSP-allowed script is never loaded in node): the token answer arrives inside the click, synchronously.
function gis() {
  const calls = { init: 0, revoke: 0 };
  return { calls, accounts: { oauth2: { initTokenClient(cfg) { calls.init++; return { requestAccessToken() { cfg.callback({ access_token: TOKEN, expires_in: 3600, token_type: 'Bearer', scope: SCOPE }); } }; }, revoke(_t, done) { calls.revoke++; if (done) done({}); } } } };
}
/* A minimal IndexedDB: databases(), and open() of DeviceActual's one store ('snapshots'); records every open (a created
   database is one more name), every record key read and every write; an aborted transaction ends with onabort (no rollback:
   the tests only abort before a write). */
function fakeIdb(seed = {}) {
  const dbs = new Map(Object.entries(seed).map(([n, recs]) => [n, new Map(Object.entries(recs))])), opened = [], reads = [], writes = [], modes = [];
  const later = (fn) => setTimeout(fn, 0);
  return { opened, reads, writes, modes, dbs, databases: async () => [...dbs.keys()].map((name) => ({ name, version: 1 })), cmp: () => 0, deleteDatabase: () => ({}),
    open(name) {
      opened.push(name); const created = !dbs.has(name); if (created) dbs.set(name, new Map()); const store = dbs.get(name), req = {};
      const db = { objectStoreNames: { contains: (n) => n === 'snapshots' }, createObjectStore() {}, close() {},
        transaction(_names, mode) { modes.push(mode || 'readonly'); const tx = { objectStore: () => ({ get(k) { reads.push(k); const r = { result: store.get(k) }; queueMicrotask(() => r.onsuccess && r.onsuccess()); return r; },
          getKey(k) { reads.push(k); const r = { result: store.has(k) ? k : undefined }; queueMicrotask(() => r.onsuccess && r.onsuccess()); return r; }, put(v, k) { writes.push('put ' + k); store.set(k, v); return {}; }, delete(k) { writes.push('delete ' + k); store.delete(k); return {}; } }) };
        tx.abort = () => { tx.aborted = true; }; later(() => (tx.aborted ? tx.onabort && tx.onabort() : tx.oncomplete && tx.oncomplete())); return tx; } };
      // A creation can be aborted from onupgradeneeded (request.transaction.abort()): then the database is not created.
      req.result = db; if (created) req.transaction = { abort() { req.aborted = true; } };
      later(() => { if (created && req.onupgradeneeded) req.onupgradeneeded(); if (req.aborted) { dbs.delete(name); if (req.onerror) req.onerror(); return; } if (req.onsuccess) req.onsuccess(); }); return req;
    } };
}
// One page: a browser-like window, the 57 old modules (index.html order), fresh P1 modules.
function env({ s = site(), idb = null, qgv = false, local = {} } = {}) {
  const win = R.nodeWindow({ files: s.files }), mods = R.loadOld(win);
  win.InvestmentAppConfig = Object.freeze({ ...mods.InvestmentAppConfig, virtualTradingRequestSpacingMs: 0 });// node timers never run
  win.localStorage = memoryStorage(local); win.sessionStorage = memoryStorage(); if (idb) win.indexedDB = idb;
  win.crypto = { randomUUID: () => nodeCrypto.randomUUID(), subtle: globalThis.crypto.subtle }; win.google = gis();
  const action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action });
  const prices = fresh('prices.js').create({ win, action, data }), store = fresh('store.js').create({ win, action, data });
  const e = { win, mods, action, data, prices, store, s, click: () => win.trusted('click'), priv: () => win.requests.filter((r) => /^https:\/\//.test(r.name)) };
  e.session = () => mods.GoogleSheetQuotes.sessionFor(prices.priceView, win.InvestmentAppConfig.googleSheetsClientId);
  if (qgv) e.qgv = fresh('qgv.js').create({ win, data, prices, action });
  return e;
}
async function connect(e) { await e.prices.prepare(e.click()); e.prices.login(e.click()); assert.equal(e.prices.status().google.connected, true, 'signed in'); }
async function sources(e) { await e.store.sheetSource.set(e.click(), ID); await e.store.universeSource.set(e.click(), ID); await e.store.workerOrigin.set(e.click(), WORKER); }
// Every PriceStore function that takes a view, with the argument holding it.
const VIEW_ARG = { status: (a) => a[0] && a[0].view, subscribe: (a) => a[1] && a[1].view, coverage: (a) => a[1] && a[1].view, monthEndCloses: (a) => a[1] && a[1].view, dailyCloses: (a) => a[2] && a[2].view,
  runnerHistories: (a) => a[0], syncMany: (a) => a[0], syncUniverse: (a) => a[0], enable: (a) => a[0], disable: (a) => a[0], universeSymbols: (a) => a[0], universeProgress: (a) => a[0], coreSymbols: (a) => a[0] };
function spies(e) {
  const P = e.win.PriceStore, G = e.win.GoogleSheetQuotes, store = [], sessions = [], spy = { ...P };
  for (const [k, get] of Object.entries(VIEW_ARG)) spy[k] = (...a) => { store.push({ name: k, view: get(a), args: a }); return P[k](...a); };
  e.win.PriceStore = Object.freeze(spy); e.win.GoogleSheetQuotes = Object.freeze({ ...G, sessionFor: (view, id) => { sessions.push(view); return G.sessionFor(view, id); } });
  return { store, sessions };
}
const DAILY = ['2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01'];
const PRICE_TABS = { Prices_D: [HEAD, ...DAILY.map((d) => ['SPY', d, String(close('SPY', d)), 'YAHOO', '2026-10-02T00:00:00Z'])], Prices_M: [HEAD] };

// ---------------------------------------------------------------- click rule
test('no click: every private path is refused before any request; synthetic events and plain objects claiming isTrusted are refused', async () => {
  const e = env({ s: site({ tabs: PRICE_TABS }) }); await connect(e); await sources(e);
  e.win.localStorage.setItem(e.store.KEYS.PRICE_STORE_ENABLED, '1');// a device that turned the price tabs on in an earlier visit
  assert.deepEqual(e.priv(), [], 'signing in sends nothing through the price view (GIS is the stand-in)');
  const PRIVATE = [[SHEETS + '/v4/spreadsheets/' + ID + '/values/' + encodeURIComponent(UNIVERSE_RANGE), {}], [SHEETS + '/v4/spreadsheets/' + ID + '/values/' + encodeURIComponent("'Prices_D'!A1") + ':append', { method: 'POST', body: '{}' }],
    ['https://oauth2.googleapis.com/token', { method: 'POST' }], [WORKER + '/history?symbol=NVDA&range=1y', {}], [WORKER + '/quote', {}]];
  for (const [url, init] of PRIVATE) await assert.rejects(e.prices.priceView.fetch(url, init), /CLICK_REQUIRED/, url);
  // Old modules handed the price view while signed in, outside a click: their request is refused at the view.
  const P = e.mods.PriceStore, s = e.session();
  assert.equal(s.state().connected, true);
  await assert.rejects(s.fetchValues(ID, UNIVERSE_RANGE), /READ_FAILED/);
  await assert.rejects(s.fetchHistory(WORKER, 'NVDA', '1y', { approvedOrigin: WORKER }));
  await assert.rejects(P.enable(e.prices.priceView), /READ_FAILED/);
  assert.deepEqual(await P.monthEndCloses('SPY', { view: e.prices.priceView }), {}, 'a fetch:false read that would load the tabs gets nothing');
  // The facade does not even try before a click read the tabs.
  const FA = e.prices.storeFacade;
  assert.deepEqual(await FA.monthEndCloses('SPY', { fetch: true }), {}); assert.deepEqual(await FA.dailyCloses('SPY', null, { fetch: true }), {});
  assert.equal(await FA.runnerHistories(e.win, { session: s, origin: WORKER, symbols: ['SPY'], fetch: true }), null);
  const API = { prepare: (ev) => e.prices.prepare(ev), login: (ev) => e.prices.login(ev), logout: (ev) => e.prices.logout(ev), readUniverse: (ev) => e.prices.readUniverse(ev),
    history: (ev) => e.prices.history(ev, 'nvda'), useTabs: (ev) => e.prices.useTabs(ev), loadTabs: (ev) => e.prices.loadTabs(ev), syncSymbols: (ev) => e.prices.syncSymbols(ev, ['SPY'], '1d'),
    syncUniverse: (ev) => e.prices.syncUniverse(ev), refresh: (ev) => e.data.refresh(ev) };
  for (const [name, call] of Object.entries(API)) for (const ev of [undefined, null, new Event('click'), { type: 'click', isTrusted: true }, e.win.trusted('mouseover')]) assert.throws(() => call(ev), /CLICK_REQUIRED/, name);
  assert.deepEqual(e.priv(), [], 'no private request reached the fake network');
  assert.ok(e.action.blocked() >= PRIVATE.length + 4, 'refusals are counted');
  // Public files still pass through the same view; an unknown destination is refused outright.
  assert.equal((await e.prices.priceView.fetch('universe-codes.json')).status, 200);
  await assert.rejects(e.prices.priceView.fetch('https://example.invalid/x'), /DESTINATION_UNKNOWN/);
  assert.equal(e.win.google.calls.init, 1, 'one token request, inside the login click');
  // Inside a click, a kind reaches only its own destinations (LOGIN: no Sheets read).
  await assert.rejects(e.action.run(e.click(), 'LOGIN', () => e.prices.priceView.fetch(...PRIVATE[0])), /CLICK_REQUIRED/);
  assert.deepEqual(e.priv(), []);
});

test('inside a click: Sheets only the saved spreadsheets, a read only a values GET (a Request POST refused); a stalled GIS load leaves the LOGIN gate', async () => {
  const e = env({ s: site({ tabs: { ...PRICE_TABS, Universe: M3_VALUES } }) }); await connect(e); await sources(e);
  const V = (id, range) => SHEETS + '/v4/spreadsheets/' + id + '/values/' + encodeURIComponent(range), other = ['someone', 'elses', 'sheet', 'id', '0001'].join('_');
  const pv = e.prices.priceView, try_ = async (f) => { try { const r = await f(); return 'OK ' + r.status; } catch (err) { return err.message; } };
  const before = e.action.blocked();
  const read = await e.action.run(e.click(), 'UNIVERSE_READ', async () => ({
    saved: await try_(() => pv.fetch(V(ID, UNIVERSE_RANGE), {})), otherSheet: await try_(() => pv.fetch(V(other, 'A1'), {})),
    appendAsRequest: await try_(() => pv.fetch(new Request(V(ID, "'Prices_D'!A1") + ':append', { method: 'POST', body: '{"values":[["NO_CLICK"]]}' }))),
    appendPlain: await try_(() => pv.fetch(V(ID, "'Prices_D'!A1") + ':append', { method: 'POST', body: '{}' })), tabList: await try_(() => pv.fetch(SHEETS + '/v4/spreadsheets/' + ID + '?fields=sheets', {})) }));
  assert.deepEqual(read, { saved: 'OK 200', otherSheet: 'DESTINATION_UNKNOWN', appendAsRequest: 'DESTINATION_UNKNOWN', appendPlain: 'CLICK_REQUIRED', tabList: 'CLICK_REQUIRED' });
  assert.equal(e.action.blocked() - before, 4);
  assert.deepEqual(e.priv().map((r) => (r.init.method || 'GET') + ' ' + decodeURIComponent(new URL(r.name).pathname)), ['GET /v4/spreadsheets/' + ID + '/values/' + UNIVERSE_RANGE], 'only the values GET of the saved sheet left');
  const sync = await e.action.run(e.click(), 'SYNC', () => try_(() => pv.fetch(SHEETS + '/v4/spreadsheets?fields=spreadsheetId', { method: 'POST', body: '{}' })));
  assert.equal(sync, 'DESTINATION_UNKNOWN', 'no spreadsheet the device did not save, not even a new one');
  // A GIS load that never settles: the prepare click ends on its time limit (or a cancel) and leaves the gate.
  const e2 = env(); e2.win.google = undefined;
  const stall = { ...e2.mods.GoogleSheetQuotes, sessionFor: (view, id) => { const s = e2.mods.GoogleSheetQuotes.sessionFor(view, id); return Object.freeze({ ...s, prepare: () => new Promise(() => {}) }); } };
  e2.win.GoogleSheetQuotes = Object.freeze(stall);
  const p = e2.prices.prepare(e2.click()); assert.equal(e2.action.active('LOGIN'), true);
  const timer = e2.win.timers.find((t) => t.ms === 30000); assert.ok(timer, 'a 30 s limit on the GIS load'); timer.fn();
  await assert.rejects(p, /PREPARE_TIMEOUT/); assert.equal(e2.action.active(), false, 'the LOGIN gate is closed');
  const q = e2.prices.prepare(e2.click()); e2.action.cancel('LOGIN'); assert.equal(e2.action.active(), false);
  await assert.rejects(q, /CANCELED/);
  assert.throws(() => e2.store.storage.setItem('x', 'y'), /ACTION_REQUIRED/, 'no write after the cancelled sign-in');
});

test('quote(): collectQuotes\' order and NA rules for one company (identity withdrawn, TARGET price identity conflict); RAM only', async () => {
  const e = env({ s: site({ tabs: { Universe: M3_VALUES } }) }); await e.data.ready();
  const real = e.data.get('sec-qgv2.json'), recs = { ...real.records };
  assert.ok(recs['TARGET:amd'] && recs['TARGET:amd'].state !== 'NOT_AVAILABLE', 'the fixture has the AMD TARGET row');
  recs['NASDAQ:ADBE'] = { ...recs['NASDAQ:ADBE'], identity_withdrawn: true }; recs['NASDAQ:AMD'] = { ...recs['NASDAQ:AMD'], universe_withdrawal: true };
  const inputs = Object.freeze({ ...real, records: Object.freeze(recs) }), data = Object.freeze({ ...e.data, get: (n) => (n === 'sec-qgv2.json' ? inputs : e.data.get(n)) });
  const prices = fresh('prices.js').create({ win: e.win, action: e.action, data });
  await prices.prepare(e.click()); prices.login(e.click()); await sources(e); assert.equal((await prices.readUniverse(e.click())).state, 'READY');
  const ask = { adbe: { code: 'NASDAQ:ADBE' }, amdCode: { code: 'NASDAQ:AMD' }, amdTarget: { company_id: 'amd', ticker: 'AMD' }, mmm: { code: 'NYSE:MMM' } };
  const got = {}; for (const [k, c] of Object.entries(ask)) { const q = await prices.quote(c); got[k] = q.state === 'OK' ? 'OK' : q.reason; }
  assert.deepEqual(got, { adbe: 'IDENTITY_CONFLICT_WITHDRAWN', amdCode: 'OK', amdTarget: 'PRICE_IDENTITY_CONFLICT', mmm: 'OK' });
  // The same verdicts from the old function over the same read and records.
  const out = await e.mods.QgvScores.collectQuotes({ PrivateSubsetView: prices.universeView }, { identities: [{ company_id: 'amd', ticker: 'AMD' }], v2Inputs: inputs });
  assert.deepEqual([Object.hasOwn(out, 'NASDAQ:ADBE'), Object.hasOwn(out, 'NASDAQ:AMD'), Object.hasOwn(out, 'TARGET:amd'), Object.hasOwn(out, 'NYSE:MMM')], [false, true, false, true]);
  // Unmodified records: the TARGET gets its ticker's price, as before.
  assert.equal((await e.prices.quote({ company_id: 'amd', ticker: 'AMD' })).state, 'NA', 'the first layer has not read the tab');
  for (const t of [prices.quote, e.prices.quote]) assert.equal(typeof t, 'function');
});

test('facade: {} / null until a click read the tabs in this sign-in, for this sheet; never enters PriceStore reads before; the price view is forced', async () => {
  const e = env({ s: site({ tabs: PRICE_TABS }) }), spy = spies(e), FA = e.prices.storeFacade;
  await connect(e); await sources(e); e.win.localStorage.setItem(e.store.KEYS.PRICE_STORE_ENABLED, '1');
  const reads = () => spy.store.filter((c) => ['monthEndCloses', 'dailyCloses', 'runnerHistories'].includes(c.name));
  assert.equal(FA.status({ view: e.win }).state, 'LOADING', 'store on and signed in, tabs not read');
  assert.deepEqual(await FA.monthEndCloses('SPY'), {}); assert.deepEqual(await FA.dailyCloses('SPY'), {}); assert.equal(await FA.runnerHistories(e.win, { session: e.session(), symbols: ['SPY'] }), null);
  assert.deepEqual(reads(), [], 'PriceStore reads (and their tab loading) never entered');
  assert.deepEqual(e.priv(), []);
  assert.equal(FA.SCHEMA, e.mods.PriceStore.SCHEMA); assert.equal(FA.universeSymbol('NYSE:BRK.B'), 'BRK-B'); assert.equal(FA.syncMany, undefined, 'no sync or enable through the facade');
  const counts = await e.prices.loadTabs(e.click());
  assert.equal(counts.state, 'READY'); assert.deepEqual(counts.tabs_loaded, { daily: true, monthly: true }); assert.doesNotMatch(JSON.stringify(counts), CLOSE);
  const n = e.priv().length; assert.ok(n > 0 && e.priv().every((r) => r.name.startsWith(SHEETS) && (r.init.method || 'GET') === 'GET'), 'the click read the tabs (Sheets GET only)');
  const daily = await FA.dailyCloses('SPY', null, { view: e.win, fetch: true });
  assert.deepEqual(daily, Object.fromEntries(DAILY.map((d) => [d, close('SPY', d)])));
  const last = reads().at(-1); assert.equal(last.view, e.prices.priceView); assert.equal(last.args[2].fetch, false, 'fetch forced off');
  assert.equal(typeof (await FA.monthEndCloses('SPY', { view: e.win })), 'object');
  const hist = await FA.runnerHistories(e.win, { session: e.session(), origin: WORKER, symbols: ['SPY', 'QQQ'], fetch: true });
  assert.equal(hist.SPY.symbol, 'SPY'); assert.deepEqual(hist.QQQ, { error: 'PRICE_NOT_FETCHED' });
  assert.equal(e.priv().length, n, 'facade reads after the click are RAM only');
  // A new sign-in: the tabs read belongs to the old one, so the facade is empty again without asking the Sheet.
  await e.prices.logout(e.click()); await connect(e);
  assert.deepEqual(await FA.dailyCloses('SPY'), {}); assert.equal(e.priv().length, n);
  await e.prices.loadTabs(e.click()); assert.equal(Object.keys(await FA.dailyCloses('SPY')).length, DAILY.length);
  // Another sheet: the same.
  await e.store.sheetSource.set(e.click(), ID.replace('synthetic', 'synthetica'));
  assert.deepEqual(await FA.dailyCloses('SPY'), {});
  for (const c of spy.store) assert.equal(c.view, e.prices.priceView, c.name + ' got the price view');
  assert.ok(spy.sessions.length > 0 && spy.sessions.every((v) => v === e.prices.priceView), 'sessionFor got the price view');
});

test('one price view: sessionFor and every PriceStore call get it (spies) through prices, the facade and the QGV score path; RAM only', async () => {
  const s = site({ tabs: { Universe: M3_VALUES }, codes: { schema: 'universe-codes/1', codes: ['NASDAQ:NVDA'] } });
  const e = env({ s, qgv: true }), spy = spies(e);
  assert.equal(e.prices.status().google.connected, false);
  await connect(e); await sources(e);
  const used = await e.prices.useTabs(e.click());
  assert.equal(used.state, 'READY'); assert.deepEqual([...s.sheet.keys()].sort(), ['Prices_D', 'Prices_M', 'Universe']); assert.deepEqual(s.sheet.get('Prices_D'), [HEAD]);
  const sync = await e.prices.syncSymbols(e.click(), ['SPY'], '1d');
  assert.equal(sync.state, 'READY'); assert.equal(sync.results.SPY.code, null); assert.ok(sync.results.SPY.appended > 1000); assert.doesNotMatch(JSON.stringify(sync), CLOSE);
  assert.ok(s.sheet.get('Prices_D').length > 1000, 'appended to the user sheet');
  const uni = await e.prices.syncUniverse(e.click());
  assert.equal(uni.state, 'READY'); assert.equal(uni.universe, 1); assert.equal(uni.results, undefined); assert.ok(s.sheet.get('Prices_M').length > 1);
  assert.equal((await e.prices.loadTabs(e.click())).tabs_loaded.monthly, true);
  const read = await e.prices.readUniverse(e.click());
  assert.equal(read.state, 'READY'); assert.equal(read.inputs, 'READY'); assert.doesNotMatch(JSON.stringify(read), PX, 'the read result has codes and counts, no price');
  const hist = await e.prices.history(e.click(), 'nvda');
  assert.equal(hist.symbol, 'NVDA'); assert.ok(Object.isFrozen(hist.bars)); assert.equal(e.prices.held('NVDA'), hist); assert.equal(e.prices.held('nvda'), hist);
  // The QGV page never prices from the kept read (DC-31: the Universe read feeds the M3 ranks only) and asks no network.
  const before = e.priv().length, pg = await e.qgv.page();
  assert.equal(e.priv().length, before, 'the score path sent nothing');
  assert.equal(pg.price_basis.kind, 'CENTRAL_IEX'); assert.ok(pg.rows.length > 0 && pg.rows.every((r) => r.score.v === null), 'no screen V from the device read');
  assert.doesNotMatch(JSON.stringify(pg), PX); assert.doesNotMatch(JSON.stringify(pg), CLOSE);
  // Facade calls naming another view still use the price view.
  await e.prices.storeFacade.monthEndCloses('NVDA', { view: e.win }); e.prices.storeFacade.coverage('SPY', { view: e.win }); e.prices.storeFacade.subscribe(() => {}, { view: e.win })();
  assert.ok(spy.store.length > 5);
  for (const c of spy.store) assert.equal(c.view, e.prices.priceView, c.name + ' got the price view');
  assert.ok(spy.sessions.length > 0); assert.ok(spy.sessions.every((v) => v === e.prices.priceView), 'every sessionFor call got the price view');
  // Requests: Sheets and the Worker only inside those clicks, public files by name; nothing stored but the documented keys, no price.
  for (const r of e.win.requests) assert.ok(r.name.startsWith(SHEETS) || r.name.startsWith(WORKER + '/history?') || e.data.FILES.includes(r.name), r.name);
  const K = e.store.KEYS;
  assert.deepEqual([...e.win.localStorage.map.keys()].sort(), [K.SHEET_SOURCE, K.UNIVERSE_SOURCE, K.WORKER_ORIGIN, K.PRICE_STORE_ENABLED].sort());
  for (const v of e.win.localStorage.map.values()) { assert.doesNotMatch(v, PX); assert.doesNotMatch(v, CLOSE); }
  const st = e.prices.status(); assert.doesNotMatch(JSON.stringify(st), PX); assert.doesNotMatch(JSON.stringify(st), CLOSE); assert.ok(!JSON.stringify(st).includes(ID), 'no sheet id in the status');
  assert.deepEqual([st.sheet.set, st.universe_source.set, st.universe.state, st.worker.state, st.history.held], [true, true, 'READY', 'READY', 1]);
});

// ---------------------------------------------------------------- the Universe read
// The old click handler of PrivateSubsetView.mount, run with a fake session and a minimal DOM, on the same rows.
async function oldMountRead(mods, { values, shares, uuid, revision }) {
  const el = (tag) => ({ tag, attrs: {}, children: [], listeners: {}, textContent: '', disabled: false, setAttribute(k, v) { this.attrs[k] = String(v); }, removeAttribute(k) { delete this.attrs[k]; },
    append(...c) { this.children.push(...c); }, replaceChildren(...c) { this.children = c; }, addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); } });
  const reads = [], session = { state: () => ({ enabled: true, ready: true, connected: true, pending: false, preparing: false, error: '' }), setEnabled() {}, revision: () => revision, subscribe: () => () => {},
    fetchValues: async (id, range, o) => { reads.push([id, range, o.maxBytes]); return { range, majorDimension: 'ROWS', values: structuredClone(values) }; } };
  const view = { GoogleSheetQuotes: { sessionFor: () => session, extractSpreadsheetId: mods.GoogleSheetQuotes.extractSpreadsheetId }, DeviceActual: { sheetSettings: async () => ({ enabled: true }) },
    localStorage: { getItem: (k) => (k === 'investment.web.v1.universe-source' ? ID : null) }, PrivateSubset: mods.PrivateSubset, SecUniverseShares: mods.SecUniverseShares, ShareClassGroups: mods.ShareClassGroups,
    PriceTime: mods.PriceTime, crypto: { randomUUID: () => uuid }, AbortController, addEventListener() {}, removeEventListener() {},
    fetch: async (name) => { assert.equal(name, 'sec-universe-shares.json'); return new Response(JSON.stringify(shares), { status: 200 }); } };
  const doc = { createElement: el, defaultView: view, documentElement: {} }, host = { ownerDocument: doc, isConnected: true, children: [], replaceChildren(...c) { this.children = c; } };
  const PSV = mods.PrivateSubsetView; await PSV.mount(host, { config: { googleSheetsClientId: 'public-client-id' } });
  const find = (n) => (n && n.attrs && n.attrs['data-subset-action'] === 'read' ? n : (n.children || []).map(find).find(Boolean));
  const button = find(host); assert.equal(button.disabled, false); await button.listeners.click[0]();
  return { reads, prices: [...PSV.prices()], basis: PSV.priceBasis(), status: PSV.readStatus(), ranks: { ...PSV.ranks(), entries: [...PSV.ranks().entries] } };
}
function freezeTime(ms) { const Real = Date; class Fixed extends Real { constructor(...a) { super(...(a.length ? a : [ms])); } static now() { return ms; } } globalThis.Date = Fixed; return () => { globalThis.Date = Real; }; }

test('readUniverse equals PrivateSubsetView.mount run with a fake session on the M3 rows (kept prices, basis, status, rank index)', async () => {
  const NOW = Date.parse('2026-10-20T09:00:00Z'), UUID = '00000000-0000-4000-8000-000000000391', shares = SHARES.payload(M3_ROWS, NOW);
  const s = site({ tabs: { Universe: M3_VALUES }, shares }), e = env({ s }); e.win.crypto.randomUUID = () => UUID;
  await connect(e); await sources(e);
  const thaw = freezeTime(NOW);
  try {
    const before = e.priv().length, result = await e.prices.readUniverse(e.click()), U = e.prices.universeView;
    const sheetReads = e.priv().slice(before);
    assert.equal(sheetReads.length, 1, 'one Sheets values GET'); assert.ok(decodeURIComponent(sheetReads[0].name).includes(UNIVERSE_RANGE));
    assert.equal(e.win.requests.filter((r) => r.name === 'sec-universe-shares.json').length, 1, 'the public share counts read at the read time');
    const mine = { prices: [...U.prices()], basis: U.priceBasis(), status: U.readStatus(), ranks: { ...e.prices.universeRanks(), entries: [...e.prices.universeRanks().entries] } };
    const old = await oldMountRead(e.mods, { values: M3_VALUES, shares, uuid: UUID, revision: e.session().revision() });
    assert.deepEqual(old.reads, [[ID, UNIVERSE_RANGE, 1048576]]);
    assert.deepEqual(plain(mine), plain({ ...old, reads: undefined }), 'same read as the old click handler');
    assert.deepEqual(mine.prices, old.prices, 'same kept prices (exact numbers)'); assert.deepEqual(mine.ranks.entries, old.ranks.entries);
    // Content checks so the comparison is not empty: US prices kept, the read id and time, the Alphabet group ranked once.
    assert.equal(mine.prices.length, M3_VALUES.length - 2, 'every US row with a positive price (FOX has none)');
    assert.deepEqual(mine.basis, { source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_' + UUID, acquired_at: new Date(NOW).toISOString(), currency: 'USD', price_time: null });
    assert.equal(mine.ranks.state, 'READY'); assert.equal(e.prices.rankFor({ company_id: 'x', ticker: 'GOOG' }).group_id, 'alphabet');
    assert.equal(e.prices.rankFor({ company_id: 'x', ticker: 'GOOGL' }), e.prices.rankFor({ company_id: 'y', ticker: 'GOOG' }), 'a group answers for its members');
    assert.equal(e.prices.rankFor({ company_id: 'x', ticker: 'BRK.B' }).state, 'NOT_AVAILABLE');
    assert.deepEqual(result.ranks, { state: 'READY', status: mine.ranks.status, verified_count: mine.ranks.verified_count, row_count: M3_VALUES.length - 1, reason_codes: [] });
    assert.equal(result.config_status, 'DEFAULT_V0_UNCALIBRATED'); assert.doesNotMatch(JSON.stringify(result), PX);
  } finally { thaw(); }
  assert.deepEqual([...e.win.localStorage.map.keys()].sort(), [e.store.KEYS.SHEET_SOURCE, e.store.KEYS.UNIVERSE_SOURCE, e.store.KEYS.WORKER_ORIGIN].sort(), 'the read stored nothing');
});

test('kept read: sign-out clears it (and held histories); an expired sign-in keeps it; a failed read keeps it and records the code; without inputs ranks say why', async () => {
  const s = site({ tabs: { Universe: M3_VALUES } }), e = env({ s }), U = e.prices.universeView;
  assert.equal(U.prices(), null); assert.equal(U.readStatus().state, 'NOT_READ');
  await assert.rejects(Promise.resolve().then(() => e.prices.readUniverse(e.click())), /UNIVERSE_SOURCE_NOT_SET/);
  await connect(e); await sources(e);
  let notes = 0; e.prices.subscribe(() => { notes++; });
  const first = await e.prices.readUniverse(e.click()); const basis = U.priceBasis();
  assert.ok(notes > 0, 'subscribers hear the new read');
  s.state.failValues = true;
  await assert.rejects(e.prices.readUniverse(e.click()), /UNIVERSE_READ_FAILED/);
  assert.equal(U.priceBasis(), basis, 'the last successful read stays'); assert.equal(U.readStatus().failure.code, 'UNIVERSE_READ_FAILED'); assert.equal(U.readStatus().state, 'READY');
  s.state.failValues = false;
  await e.prices.readUniverse(e.click()); assert.equal(U.readStatus().failure, null); assert.notEqual(U.priceBasis().read_id, first.read_id);
  await e.prices.history(e.click(), 'nvda'); assert.ok(e.prices.held('nvda'));
  // An expired token (AUTH_REQUIRED) keeps the read; the rank index belongs to the sign-in and goes.
  const thaw = freezeTime(Date.now() + 2 * 3600e3);
  try { assert.equal(e.prices.status().google.error, 'AUTH_REQUIRED'); } finally { thaw(); }
  assert.ok(U.priceBasis(), 'kept across an expired sign-in'); assert.equal(e.prices.universeRanks(), null); assert.ok(e.prices.held('nvda'));
  await e.prices.logout(e.click());
  assert.equal(U.prices(), null); assert.equal(U.priceBasis(), null); assert.deepEqual(U.readStatus(), { state: 'NOT_READ', basis: null, failure: null }); assert.equal(e.prices.held('nvda'), null);
  assert.equal(e.prices.rankFor({ company_id: 'x', ticker: 'ADBE' }).state, 'NOT_AVAILABLE');
  // No public share counts (404): the read keeps prices, ranks are NOT_AVAILABLE with the old reason.
  const s2 = site({ tabs: { Universe: M3_VALUES }, extra: { 'sec-universe-shares.json': null } }), e3 = env({ s: s2 }); await connect(e3); await sources(e3);
  const r3 = await e3.prices.readUniverse(e3.click());
  assert.equal(r3.inputs, 'SEC_INPUTS_NOT_CONNECTED'); assert.deepEqual([...e3.prices.universeRanks().reason_codes], ['SEC_INPUTS_NOT_CONNECTED']); assert.ok(e3.prices.universeView.prices().size > 0);
});

test('quote: the kept Universe read only (a stored device quote is never read, DC-18); NA with a reason otherwise', async () => {
  const idb = fakeIdb(), e = env({ s: site({ tabs: { Universe: M3_VALUES } }), idb });
  assert.deepEqual(await e.prices.quote({ code: 'NASDAQ:ADBE', ticker: 'ADBE' }), { state: 'NA', reason: 'NO_DEVICE_PRICE' });
  assert.deepEqual(idb.opened, [], 'no device database, so none opened (and none created)');
  await connect(e); await sources(e); await e.prices.readUniverse(e.click());
  const q = await e.prices.quote({ code: 'NASDAQ:ADBE' });
  assert.deepEqual(q, { state: 'OK', price: px(10), currency: 'USD', source: 'UNIVERSE_SHEET', read_at: e.prices.universeView.priceBasis().acquired_at, as_of: null, time_status: 'UNCONFIRMED', freshness: 'UNDETERMINED' });
  assert.equal((await e.prices.quote({ ticker: 'BRK.B' })).price, px(1), 'by ticker (class share dots)');
  assert.deepEqual(await e.prices.quote({ ticker: 'NVDA' }), { state: 'NA', reason: 'NO_DEVICE_PRICE' });
  assert.deepEqual([...idb.dbs.get(e.store.KEYS.DEVICE_DB).keys()], ['google-sheet-settings'], 'the only record: Google on, saved by the prepare click');
  assert.ok(!idb.reads.some((k) => k === 'market' || k === 'market-import-history'), 'no stored quote was read');
});

// ---------------------------------------------------------------- store
test('store writes: without a trusted click nothing runs (CLICK_REQUIRED); an old writer handed the gated storage outside a click gets ACTION_REQUIRED; storage unchanged', async () => {
  const e = env(), K = e.store.KEYS, snapshot = () => JSON.stringify([...e.win.localStorage.map]);
  e.win.localStorage.setItem(K.PERSONAL, JSON.stringify({ version: 1, interests: ['nvda'], groups: [] }));
  const before = snapshot(), w = CUSTOM.cases[0].input.weights;
  const WRITES = { savePrefs: (ev) => e.store.savePrefs(ev, { version: 1, interests: ['amd'], groups: [] }), saveWeights: (ev) => e.store.saveWeights(ev, { name: '내 가중치', weights: w }),
    saveThesis: (ev) => e.store.saveThesis(ev, 'NVDA', 't', 'i'), saveHold: (ev) => e.store.saveHold(ev, 'NVDA', { reason: 'r', release_condition: 'c', release_date: '2026-12-31' }),
    saveRecord: (ev) => e.store.saveRecord(ev, { id: 'x' }), toggleStar: (ev) => e.store.toggleStar(ev, '0000000001'), restore: (ev) => e.store.backup.restore(ev, '{}'), download: (ev) => e.store.backup.download(ev),
    sheetSource: (ev) => e.store.sheetSource.set(ev, ID), universeSource: (ev) => e.store.universeSource.set(ev, ID), workerOrigin: (ev) => e.store.workerOrigin.set(ev, WORKER),
    useSheet: (ev) => e.store.universeSource.useSheet(ev), marketQuotes: (ev) => e.store.marketQuotes.clear(ev),
    pushRecent: (ev) => e.store.pushRecent(ev, 'COMPANY:nvda'), clearRecent: (ev) => e.store.clearRecent(ev) };
  for (const [name, call] of Object.entries(WRITES)) for (const ev of [undefined, new Event('click'), { type: 'click', isTrusted: true }]) assert.throws(() => call(ev), /CLICK_REQUIRED/, name);
  const S = e.store.storage, M = e.mods;
  for (const [name, call] of Object.entries({ playbook: () => M.PlaybookScreen.saveThesis(S, 'NVDA', 't', 'i'), stars: () => M.PublicScreens.toggleStar(S, '0000000001'), weights: () => M.DeviceProfiles.writeV2(S, M.DeviceProfiles.emptyV2()),
    prefs: () => S.setItem(K.PERSONAL, '{}'), remove: () => S.removeItem(K.PERSONAL), clear: () => S.clear(), sheet: () => M.GoogleSheetSetup.source(e.prices.priceView, ID) }))
    assert.throws(call, /ACTION_REQUIRED/, name);
  await assert.rejects(M.DeviceBackup.restore({ localStorage: S, AppLanguage: M.AppLanguage, DeviceMarket: M.DeviceMarket, DeviceActual: { restoreHoldings: async () => null } }, CATALOG,
    M.DeviceBackup.create({ version: 1, interests: [], groups: [] }, M.AppLanguage.settings(), null, CATALOG, M.DeviceMarket, M.AppLanguage)), /BACKUP_/);
  assert.equal(snapshot(), before, 'storage unchanged'); assert.ok(e.action.blocked() >= 8);
  // Inside a click the same write lands, through the old module.
  assert.deepEqual(plain(await e.store.savePrefs(e.click(), { version: 1, interests: ['amd', 'amd'], groups: [] })), { version: 1, interests: ['amd'], groups: [] });
  assert.equal(e.win.localStorage.getItem(K.PERSONAL), JSON.stringify({ version: 1, interests: ['amd'], groups: [] }));
});

test('store reads and settings: prefs (unreadable value never overwritten), weights versions, playbook, stars, device V history stopped (count / clear click), sources never returned', async () => {
  const e = env(), K = e.store.KEYS, L = e.win.localStorage;
  assert.deepEqual(plain(e.store.prefs()), { state: 'EMPTY', value: { version: 1, interests: [], groups: [] } });
  L.setItem(K.PERSONAL, '{broken'); assert.deepEqual(plain(e.store.prefs()), { state: 'INVALID', value: null });
  // Store writes are synchronous inside the click (the backup's are async).
  assert.throws(() => e.store.savePrefs(e.click(), { version: 1, interests: [], groups: [] }), /PREFS_STORAGE_INVALID/); assert.equal(L.getItem(K.PERSONAL), '{broken', 'original kept');
  L.removeItem(K.PERSONAL); assert.throws(() => e.store.savePrefs(e.click(), { version: 2 }), /PREFS_INVALID/); assert.equal(L.getItem(K.PERSONAL), null);
  const w = CUSTOM.cases[0].input.weights, a = await e.store.saveWeights(e.click(), { name: '내 가중치', weights: w });
  assert.equal(a.version, 1); const b = await e.store.saveWeights(e.click(), { id: a.id, name: '내 가중치', weights: w }); assert.equal(b.id, a.id); assert.equal(b.version, 2);
  assert.equal(e.store.weights().value.profiles.length, 1); assert.deepEqual(e.store.PRODUCT_PRESETS, e.mods.DeviceProfiles.PRODUCT_PRESETS);
  assert.throws(() => e.store.saveWeights(e.click(), { name: '', weights: w }), /WEIGHTS_INVALID/);
  await e.store.saveThesis(e.click(), 'NVDA', '논지', '무효화 조건'); assert.equal(e.store.playbook().value.theses.NVDA.thesis, '논지');
  assert.deepEqual([...(await e.store.toggleStar(e.click(), '0000000001'))], ['0000000001']); assert.deepEqual([...e.store.stars()], ['0000000001']);
  let notes = []; e.store.subscribe((what) => notes.push(what)); await e.store.toggleStar(e.click(), '0000000001'); assert.deepEqual(notes, ['INVESTOR_STARS']); assert.deepEqual([...e.store.stars()], []);
  const vh = JSON.stringify({ schema: 'virtual-trading-v-scores/2', scores: { '2026-10-01': { nvda: 61 } }, composition: {} }); L.setItem(K.V_HISTORY, vh);
  // Device V history (DC-31): stopped at the gate (reads absent, writes refused); a count and the user's clear click only.
  const before = JSON.stringify([...L.map]); assert.equal(e.store.vHistory, undefined); assert.equal(e.store.storage.getItem(K.V_HISTORY), null, 'reads absent');
  assert.throws(() => e.action.run(e.click(), 'WRITE', () => e.store.storage.setItem(K.V_HISTORY_V2, vh)), /V_HISTORY_STOPPED/);
  assert.equal(e.store.vHistoryKeys.count(), 1); assert.equal(JSON.stringify([...L.map]), before, 'nothing changed on its own');
  assert.throws(() => e.store.vHistoryKeys.clear(new Event('click')), /CLICK_REQUIRED/); assert.equal(e.store.vHistoryKeys.clear(e.click()), 1); assert.equal(L.getItem(K.V_HISTORY), null); assert.equal(e.store.vHistoryKeys.count(), 0);
  // Sources: has() / set() only; the id or address never comes back.
  assert.equal(e.store.sheetSource.has(), false); const set = await e.store.sheetSource.set(e.click(), 'https://docs.google.com/spreadsheets/d/' + ID + '/edit');
  assert.deepEqual(set, { set: true }); assert.equal(L.getItem(K.SHEET_SOURCE), ID); assert.equal(e.store.sheetSource.has(), true);
  assert.throws(() => e.store.sheetSource.set(e.click(), 'not a sheet'), /SHEET_SOURCE_INVALID/); assert.equal(L.getItem(K.SHEET_SOURCE), ID);
  assert.deepEqual(await e.store.universeSource.set(e.click(), ID), { set: true }); assert.equal(e.store.universeSource.has(), true);
  assert.deepEqual(await e.store.universeSource.set(e.click(), ''), { set: false }); assert.equal(L.getItem(K.UNIVERSE_SOURCE), null);
  // "통합 시트와 같게" (Main pick: the Universe source keeps its own key): the unified sheet copied on a click, never returned.
  assert.deepEqual(e.store.universeSource.useSheet(e.click()), { set: true }); assert.equal(L.getItem(K.UNIVERSE_SOURCE), ID); assert.equal(L.getItem(K.SHEET_SOURCE), ID);
  const e9 = env(); assert.throws(() => e9.store.universeSource.useSheet(e9.click()), /SHEET_SOURCE_NOT_SET/); assert.equal(e9.win.localStorage.getItem(K.UNIVERSE_SOURCE), null);
  await e.store.universeSource.set(e.click(), '');
  assert.throws(() => e.store.workerOrigin.set(e.click(), 'http://x.example'), /REQUEST_INVALID/);
  assert.deepEqual(await e.store.workerOrigin.set(e.click(), WORKER + '/'), { set: true, approved: true }); assert.equal(e.store.workerOrigin.approved(), true); assert.equal(L.getItem(K.WORKER_ORIGIN), WORKER);
  assert.deepEqual(await e.store.workerOrigin.set(e.click(), 'https://other-worker.someone.workers.dev'), { set: true, approved: false });
});

test('recent searches: the old home key and shape; read freely (invalid entries dropped), written only in a click; COMPANY keys only', () => {
  const e = env(), K = e.store.KEYS, L = e.win.localStorage;
  const old = fs.readFileSync(R.oldPath('home-screen.js'), 'utf8');
  assert.match(old, /RECENT_MAX=6/); assert.match(old, /KEY_SHAPE=\/\^\(COMPANY\|INDUSTRY\|INVESTOR\|MACRO\):\[A-Za-z0-9_\.:\\-\]\{1,64\}\$\//, 'the old key shape the store reads');
  assert.deepEqual([...e.store.recent()], []); assert.ok(Object.isFrozen(e.store.recent()));
  // What the old home stored is read the old way: valid keys, once each, the first 6.
  L.setItem(K.RECENT, JSON.stringify(['COMPANY:nvda', 'INDUSTRY:semis', 'COMPANY:nvda', 'nvda', 7, 'COMPANY:<b>', 'MACRO:cpi', 'COMPANY:NYSE:FIX', 'COMPANY:amd', 'COMPANY:msft', 'COMPANY:intc']));
  assert.deepEqual([...e.store.recent()], ['COMPANY:nvda', 'INDUSTRY:semis', 'MACRO:cpi', 'COMPANY:NYSE:FIX', 'COMPANY:amd', 'COMPANY:msft']);
  L.setItem(K.RECENT, '{broken'); assert.deepEqual([...e.store.recent()], []);
  L.setItem(K.RECENT, JSON.stringify({ x: 1 })); assert.deepEqual([...e.store.recent()], []);
  L.removeItem(K.RECENT);
  for (const ev of [undefined, new Event('click'), { type: 'click', isTrusted: true }]) { assert.throws(() => e.store.pushRecent(ev, 'COMPANY:nvda'), /CLICK_REQUIRED/); assert.throws(() => e.store.clearRecent(ev), /CLICK_REQUIRED/); }
  assert.equal(L.getItem(K.RECENT), null, 'nothing written without a click');
  // In a click: newest first, a repeat moves to the front, at most 6; only COMPANY:<id> keys are written (never query text).
  let notes = []; e.store.subscribe((what) => notes.push(what));
  for (const id of ['nvda', 'amd', 'msft', 'NYSE:FIX', 'intc', 'qcom', 'avgo', 'amd']) e.store.pushRecent(e.click(), 'COMPANY:' + id);
  assert.deepEqual(JSON.parse(L.getItem(K.RECENT)), ['COMPANY:amd', 'COMPANY:avgo', 'COMPANY:qcom', 'COMPANY:intc', 'COMPANY:NYSE:FIX', 'COMPANY:msft']);
  assert.deepEqual([...e.store.recent()], JSON.parse(L.getItem(K.RECENT)));
  assert.equal(notes.length, 8); assert.ok(notes.every((n) => n === 'RECENT'));
  for (const bad of ['INDUSTRY:semis', 'nvda', 'COMPANY:', 'COMPANY:a b', 'COMPANY:' + 'x'.repeat(65), null]) assert.throws(() => e.store.pushRecent(e.click(), bad), /RECENT_KEY_INVALID/, String(bad));
  assert.equal(JSON.parse(L.getItem(K.RECENT)).length, 6, 'a refused key changes nothing');
  // One click, one action: a second store write from the same click is refused.
  const ev = e.click(); e.store.pushRecent(ev, 'COMPANY:nvda'); assert.throws(() => e.store.clearRecent(ev), /ACTION_ALREADY_STARTED/);
  assert.deepEqual([...e.store.clearRecent(e.click())], []); assert.equal(L.getItem(K.RECENT), null); assert.deepEqual([...e.store.recent()], []);
});

test('KEYS equal the old modules\' constants (existing devices keep their data)', () => {
  const e = env(), K = e.store.KEYS, M = e.mods, lit = (file, re) => { const m = re.exec(fs.readFileSync(R.oldPath(file), 'utf8')); assert.ok(m, file); return m[1]; };
  assert.equal(K.PERSONAL, lit('device-backup.js', /PERSONAL_KEY='([^']+)'/)); assert.equal(K.PERSONAL, lit('app.js', /const KEY = "([^"]+)"/));
  assert.equal(K.SETTINGS, M.AppLanguage.KEY); assert.equal(K.PROFILES, M.DeviceProfiles.KEY); assert.equal(K.PROFILES_V2, M.DeviceProfiles.V2_KEY); assert.equal(K.PLAYBOOK, M.PlaybookScreen.KEY);
  assert.equal(K.INVESTOR_STARS, M.PublicScreens.STAR_KEY); assert.equal(K.INVESTOR_STARS, M.DeviceBackup.STAR_KEY); assert.equal(K.BACKUP_RESTORED, M.DeviceBackup.RESTORED_KEY);
  assert.equal(K.V_HISTORY, M.VirtualTradingVHistory.KEY); assert.equal(K.V_HISTORY_V2, M.VirtualTradingVHistory.V2_KEY); assert.equal(K.SHEET_SOURCE, M.GoogleSheetSetup.KEY);
  assert.equal(K.UNIVERSE_SOURCE, lit('private-subset-view.js', /const KEY='([^']+)'/)); assert.equal(e.prices.UNIVERSE_SOURCE_KEY, K.UNIVERSE_SOURCE);
  assert.equal(K.WORKER_ORIGIN, lit('private-history.js', /STORAGE_KEY = '([^']+)'/)); assert.equal(K.WORKER_ORIGIN, lit('price-store.js', /HISTORY_KEY='([^']+)'/)); assert.equal(e.prices.WORKER_ORIGIN_KEY, K.WORKER_ORIGIN);
  assert.equal(K.PRICE_STORE_ENABLED, M.PriceStore.FLAG_KEY); assert.equal(K.DEVICE_DB, lit('device-actual.js', /DB_NAME = '([^']+)'/));
  assert.equal(K.CHART_USER_OBJECTS, M.ChartWorkbench.USER_KEY); assert.equal(K.MACRO_USER_ESTIMATES, M.MacroCycleRing.USER_KEY);
  assert.equal(K.RECENT, lit('home-screen.js', /RECENT_KEY='([^']+)'/));
  assert.deepEqual(fresh('store.js').KEYS, K); assert.ok(Object.isFrozen(K));
});

test('backup: /4 round trip through the old module (no price, sheet id or Worker address); /1–/3 accepted; /5 user objects round trip through the old validators; no device database created by a restore', async () => {
  const idb = fakeIdb(), e = env({ s: site({ tabs: { Universe: M3_VALUES } }), idb }), K = e.store.KEYS;
  await e.store.savePrefs(e.click(), { version: 1, interests: ['nvda', 'amd'], groups: [{ id: 'g1', name: '반도체', members: ['nvda'] }] });
  await e.store.toggleStar(e.click(), '0000000002'); await e.store.saveThesis(e.click(), 'NVDA', '논지', '무효화'); await connect(e); await sources(e); await e.prices.readUniverse(e.click());
  const payload = await e.store.backup.create(), text = JSON.stringify(payload);
  assert.equal(payload.schema, 'investment-device-backup/4'); assert.equal(payload.portfolio, null); assert.deepEqual(payload.investor_stars, ['0000000002']);
  assert.doesNotMatch(text, PX); assert.ok(!text.includes(ID) && !text.includes(WORKER) && !text.includes(TOKEN), 'no sheet id, Worker address or token');
  const idb2 = fakeIdb(), e2 = env({ idb: idb2 });
  assert.deepEqual(await e2.store.backup.restore(e2.click(), text), { schema: payload.schema });
  assert.deepEqual(plain(await e2.store.backup.create()), plain(payload), 'restored device gives the same backup');
  for (const k of [K.PERSONAL, K.INVESTOR_STARS, K.PLAYBOOK]) assert.equal(e2.win.localStorage.getItem(k), e.win.localStorage.getItem(k), k);
  assert.equal(e2.store.backup.restored().schema, payload.schema);
  for (const schema of ['investment-device-backup/3', 'investment-device-backup/2', 'investment-device-backup/1']) {
    const old = { ...payload, schema }; delete old.playbook; if (schema !== 'investment-device-backup/3') delete old.investor_stars; if (schema === 'investment-device-backup/1') delete old.profiles;
    const e3 = env(); assert.deepEqual(await e3.store.backup.restore(e3.click(), JSON.stringify(old)), { schema }); assert.equal(e3.store.prefs().value.interests.length, 2, schema);
  }
  // /5 (owner 2026-10-24): the opt-in user objects, validated by ChartWorkbench / MacroCycleRing themselves (DeviceBackup looks them
  // up); synthetic anchors only (device_backup_node_test fixtures).
  const CW = e.mods.ChartWorkbench, MC = e.mods.MacroCycleRing, AT = '2026-10-20T00:00:00.000Z', ANCHOR = { symbol: 'SYNTH', interval: 'D', price_basis: 'RAW_CLOSE', author: 'USER', text: '', created_at: AT, updated_at: AT };
  const NOTE = { ...ANCHOR, id: 'u-note001', schema: 'chart-annotation/1', kind: 'LINE', points: [{ time: '2025-01-06', price: 100 }, { time: '2025-02-03', price: 110 }] }, MINE = { ...NOTE, id: 'u-mine001', points: [{ time: '2025-03-03', price: 120 }, { time: '2025-03-10', price: 121 }] };
  const ENTRY = (i) => ({ seq: i, saved_at: '2026-10-01T00:0' + i + ':00Z', from: { phase: '회복', part: '초입' }, to: { phase: '확장', part: '후반' }, note: 'synthetic ' + i, system: { state: 'NOT_COMPUTED', text: '미산출', reason: 'NO_MODEL_OUTPUT', layer: null, model_id: null, as_of: null } });
  e.win.localStorage.setItem(K.CHART_USER_OBJECTS, JSON.stringify({ schema: CW.USER_SCHEMA, items: [NOTE] })); e.win.localStorage.setItem(K.MACRO_USER_ESTIMATES, JSON.stringify({ schema: MC.USER_SCHEMA, rings: { economy: [ENTRY(1), ENTRY(2)] } }));
  assert.deepEqual(plain(await e.store.backup.create()), plain(payload), 'without the opt-in the backup stays /4, as before');
  const p5 = await e.store.backup.create({ userObjects: true }), t5 = JSON.stringify(p5);
  assert.equal(p5.schema, 'investment-device-backup/5'); assert.deepEqual([p5.user_objects.chart.items.map((o) => o.id), p5.user_objects.macro.rings.economy.length], [['u-note001'], 2]);
  assert.doesNotMatch(t5, PX); assert.ok(!t5.includes(ID) && !t5.includes(WORKER) && !t5.includes(TOKEN));
  const e6 = env({ idb: fakeIdb() }); e6.win.localStorage.setItem(K.CHART_USER_OBJECTS, JSON.stringify({ schema: CW.USER_SCHEMA, items: [MINE] }));
  assert.deepEqual(await e6.store.backup.restore(e6.click(), t5), { schema: p5.schema }); assert.deepEqual(await e6.store.backup.restore(e6.click(), t5), { schema: p5.schema });
  assert.deepEqual(JSON.parse(e6.win.localStorage.getItem(K.CHART_USER_OBJECTS)).items.map((o) => o.id), ['u-mine001', 'u-note001'], 'merged, nothing removed, no duplicate');
  assert.equal(JSON.parse(e6.win.localStorage.getItem(K.MACRO_USER_ESTIMATES)).rings.economy.length, 2);
  assert.deepEqual(plain(await e6.store.backup.create({ userObjects: true })).user_objects.chart.items.map((o) => o.id), ['u-mine001', 'u-note001']);
  assert.equal(e6.store.backup.restored().schema, 'investment-device-backup/5');
  assert.throws(() => e6.store.backup.restore(undefined, t5), /CLICK_REQUIRED/);
  const e5 = env(), before = JSON.stringify([...e5.win.localStorage.map]);
  await assert.rejects(e5.store.backup.restore(e5.click(), JSON.stringify({ ...p5, user_objects: { chart: { schema: 'chart-user-objects/9', items: [] }, macro: null } })), /BACKUP_INVALID/, 'the old validator refuses a bad section');
  await assert.rejects(e5.store.backup.restore(e5.click(), JSON.stringify({ ...p5, user_objects: { chart: null, macro: { schema: MC.USER_SCHEMA, rings: { economy: [{ ...ENTRY(1), price: 1 }] } } } })), /BACKUP_INVALID/, 'no price in a macro estimate');
  await assert.rejects(e5.store.backup.restore(e5.click(), '{not json'), /BACKUP_INVALID/);
  await assert.rejects(e5.store.backup.restore(e5.click(), JSON.stringify({ ...payload, extra: 1 })), /BACKUP_/);
  await assert.rejects(e5.store.backup.restore(e5.click(), 'x'.repeat(e5.mods.DeviceBackup.MAX_BYTES + 1)), /BACKUP_TOO_LARGE/);
  assert.equal(JSON.stringify([...e5.win.localStorage.map]), before, 'a refused backup changes nothing');
  assert.deepEqual(idb2.opened, [], 'a device without the database: the restore (no holdings) created none');
  assert.deepEqual([[...idb.dbs.get(K.DEVICE_DB).keys()], idb.writes], [['google-sheet-settings'], ['put google-sheet-settings']], 'the first device: only the Google on record of its prepare click; the backup wrote nothing');
});

test('device quotes stopped (DC-18): a stored record the old path reads is never read by quote() or the score path, never written even in a click, never deleted on its own; count() / clear(event)', async () => {
  const STORED = /\.0761937/, AT = '2026-10-13T20:00:00.000Z', DB = 'investment-device-actual-v1', asml = CATALOG.instruments.find((i) => i.ticker === 'ASML'), lrcx = CATALOG.instruments.find((i) => i.ticker === 'LRCX');
  const SETTINGS = { schema: 'device-google-sheet-settings/1', enabled: false, spreadsheet_id: '', range: 'Quotes!A1:C22' };
  const idb = fakeIdb(), e = env({ s: site(), idb, qgv: true }), M = e.mods, DA = M.DeviceActual, QS = M.QgvScores;
  const market = M.DeviceMarket.makeMarket(CATALOG, [{ security_reference: asml.security_reference, price: '612.0761937', currency: asml.currency, as_of: AT, available_at: AT, source: 'MANUAL' }], [], null, Date.parse(AT));
  const history = { schema: 'device-market-import-history/1', entries: [{ at: AT, quotes: [{ price: '401.0761937' }] }] };
  const seed = () => new Map([['actual', { synthetic: 'holdings placeholder' }], ['market', market], ['market-import-history', history], ['google-sheet-settings', SETTINGS]]);
  idb.dbs.set(DB, seed());// what the old screens stored on this device before
  // The old path reads that record: DeviceActual.ramQuote on the raw database gives its price, and collectQuotes would score with it.
  const raw = { indexedDB: idb, DeviceMarket: M.DeviceMarket, PriceTime: M.PriceTime, DeviceActual: DA, DeviceValuation: M.DeviceValuation };
  assert.match(String((await DA.ramQuote(raw, CATALOG, 'ASML')).price), STORED, 'a valid stored quote');
  await e.data.ready(); const inputs = e.data.get('sec-qgv2.json'), ids = [{ company_id: 'asml', ticker: 'ASML' }];
  const oldQuotes = await QS.collectQuotes(raw, { identities: ids, v2Inputs: inputs, catalog: CATALOG });
  assert.ok(Object.values(oldQuotes).some((q) => STORED.test(String(q.price))), 'the old score path takes it');
  idb.reads.length = 0; idb.opened.length = 0;
  // The new frontend never does: quote(), the score path (same old function, the score view), the page.
  assert.deepEqual(await e.prices.quote({ company_id: 'asml', ticker: 'ASML' }), { state: 'NA', reason: 'NO_DEVICE_PRICE' });
  assert.deepEqual(await QS.collectQuotes(e.qgv.scoreView, { identities: ids, v2Inputs: inputs, catalog: CATALOG }), {});
  const pg = await e.qgv.page(), row = e.qgv.row(pg, 'asml');
  if (row) assert.equal(row.score.v, null);
  assert.equal(pg.price_basis.kind, 'CENTRAL_IEX', 'no device price on the page');
  assert.ok(idb.opened.length > 0, 'the existing database was opened (holdings, settings)');
  assert.ok(!idb.reads.some((k) => k === 'market' || k === 'market-import-history'), 'no read of a stored quote record');
  assert.ok(idb.reads.includes('MARKET_STORE_STOPPED'), 'asked under the no-record key instead');
  // An old writer: the same import lands on the raw database, never through a view, not even inside a WRITE click.
  const result = { quotes: [{ security_reference: lrcx.security_reference, price: '401.0761937', currency: lrcx.currency, as_of: AT, available_at: AT, source: 'GOOGLEFINANCE', time_status: 'KNOWN' }], fx: [], successes: [{ name: lrcx.label }], failures: [], warnings: [] };
  const idbRaw = fakeIdb({ [DB]: {} });
  await DA.applyMarketImport({ indexedDB: idbRaw, DeviceMarket: M.DeviceMarket, GoogleSheetCore: M.GoogleSheetCore }, CATALOG, result, { method: 'paste', now: Date.parse(AT) });
  assert.deepEqual(idbRaw.writes.sort(), ['put market', 'put market-import-history'], 'the import itself is valid (the raw database takes it)');
  const blocked = e.action.blocked();
  await assert.rejects(e.action.run(e.click(), 'WRITE', () => DA.applyMarketImport(e.prices.priceView, CATALOG, result, { method: 'paste', now: Date.parse(AT) })), /STORAGE/);
  await assert.rejects(DA.applyMarketImport(e.prices.priceView, CATALOG, result, { method: 'paste', now: Date.parse(AT) }), /STORAGE/, 'outside a click the write transaction itself is refused');
  assert.equal(e.action.blocked() - blocked, 2, 'MARKET_STORE_STOPPED in the click, ACTION_REQUIRED outside');
  assert.deepEqual(idb.writes, [], 'nothing reached the database');
  assert.deepEqual([...idb.dbs.get(DB)], [...seed()], 'the stored records are untouched: never deleted automatically');
  // count(): a number, no value; a device without the database is not opened (nothing created); a browser that cannot list
  // its databases answers null and opens nothing.
  assert.equal(await e.store.marketQuotes.count(), 2);
  const none = fakeIdb(), e0 = env({ idb: none }); assert.equal(await e0.store.marketQuotes.count(), 0); assert.deepEqual([none.opened, none.dbs.size], [[], 0]);
  const blind = fakeIdb({ [DB]: { actual: { synthetic: 'holdings placeholder' }, market } }); delete blind.databases; const e1 = env({ idb: blind }); assert.equal(await e1.store.marketQuotes.count(), null); assert.deepEqual(blind.opened, []);
  assert.equal(await env().store.marketQuotes.count(), null, 'no IndexedDB at all');
  // clear(event): only on a trusted click; removes the two quote records and nothing else.
  for (const ev of [undefined, new Event('click'), { type: 'click', isTrusted: true }, e.win.trusted('mouseover')]) assert.throws(() => e.store.marketQuotes.clear(ev), /CLICK_REQUIRED/);
  assert.throws(() => e.action.stoppedRecords.clear(new AbortController().signal), /ACTION_REQUIRED/);
  assert.equal(idb.dbs.get(DB).size, 4, 'still there after every refusal');
  let notes = []; e.store.subscribe((what) => notes.push(what));
  assert.equal(await e.store.marketQuotes.clear(e.click()), 2); assert.deepEqual(notes, ['MARKET_QUOTES']);
  assert.deepEqual([...idb.dbs.get(DB).keys()], ['actual', 'google-sheet-settings'], 'holdings and the Google setting stay');
  assert.deepEqual(idb.writes, ['delete market', 'delete market-import-history']);
  assert.equal(await e.store.marketQuotes.count(), 0); assert.equal(await e.store.marketQuotes.clear(e.click()), 0);
  assert.equal(await e0.store.marketQuotes.clear(e0.click()), 0); assert.deepEqual([none.opened, none.dbs.size], [[], 0], 'clearing on a device without the database creates none');
  // A browser that cannot list its databases: the settings button still works inside its click (the database opened by name),
  // count() stays unknown, and on a device without the database the creation is aborted (none is created).
  assert.throws(() => e1.store.marketQuotes.clear(undefined), /CLICK_REQUIRED/); assert.deepEqual(blind.opened, [], 'nothing opened without the click');
  assert.equal(await e1.store.marketQuotes.clear(e1.click()), 1); assert.deepEqual([...blind.dbs.get(DB).keys()], ['actual'], 'the quote record went, the holdings stay');
  assert.deepEqual(blind.writes, ['delete market', 'delete market-import-history']); assert.equal(await e1.store.marketQuotes.count(), null);
  const gone = fakeIdb(); delete gone.databases; const e7 = env({ idb: gone });
  assert.equal(await e7.store.marketQuotes.clear(e7.click()), 0); assert.deepEqual([gone.opened, gone.dbs.size, gone.writes], [[DB], 0, []], 'opened by name, its creation aborted: no database');
  assert.doesNotMatch(JSON.stringify([pg, await e.prices.quote({ ticker: 'ASML' }), e.prices.status()]), STORED, 'no stored price value came back');
});

test('Google on/off: saved only inside the prepare click (the old sign-in click), read only from an existing database, left as it is by a sign-out', async () => {
  const idb = fakeIdb(), e = env({ idb }), DB = e.store.KEYS.DEVICE_DB;
  assert.deepEqual(await e.prices.deviceSettings(), { stored: false, enabled: false }); assert.deepEqual(idb.opened, [], 'no database: nothing opened or created');
  assert.throws(() => e.prices.prepare(undefined), /CLICK_REQUIRED/); assert.equal(idb.dbs.size, 0);
  await e.prices.prepare(e.click());
  assert.deepEqual(idb.dbs.get(DB).get('google-sheet-settings'), { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' }, 'the prepare click saved Google on');
  assert.deepEqual(idb.writes, ['put google-sheet-settings']);
  e.prices.login(e.click()); assert.equal(e.prices.status().google.connected, true); await e.prices.logout(e.click());
  assert.deepEqual([idb.writes, idb.dbs.get(DB).get('google-sheet-settings').enabled], [['put google-sheet-settings'], true], 'sign-in and sign-out write nothing (the old disconnect kept it)');
  // A returning device: the saved on is read without a click (a flag, no request, no write); prepare there writes nothing new.
  const e2 = env({ idb }); assert.equal(e2.prices.status().google.enabled, false);
  assert.deepEqual(await e2.prices.deviceSettings(), { stored: true, enabled: true }); assert.deepEqual(e2.priv(), []);
  await e2.prices.prepare(e2.click()); assert.deepEqual(idb.writes, ['put google-sheet-settings']);
  assert.equal(e2.prices.status().google.ready, true);
  // No device storage at all: the sign-in still goes on (the old click did too).
  const e3 = env(); await e3.prices.prepare(e3.click()); e3.prices.login(e3.click()); assert.equal(e3.prices.status().google.connected, true);
});

test('IndexedDB: a read never creates the device database (not even inside a click); an existing one is read', async () => {
  const idb = fakeIdb(), e = env({ idb }), DA = e.mods.DeviceActual;
  assert.deepEqual(plain(await e.store.holdings()), { state: 'NOT_AVAILABLE', reason: 'DEVICE_STORE_NOT_OPENED', snapshot: null, source: null, as_of: null });
  assert.deepEqual(await e.prices.deviceSettings(), { stored: false, enabled: false });
  await e.action.run(e.click(), 'WRITE', async () => { await e.store.holdings(); await e.prices.quote({ ticker: 'NVDA' }); await e.store.backup.create(); });
  await assert.rejects(e.action.run(e.click(), 'WRITE', () => DA.readHoldings(e.prices.priceView, CATALOG)), /STORAGE/, 'the price view never creates one');
  assert.deepEqual(idb.opened, []); assert.equal(idb.dbs.size, 0);
  // A device that has the database: reads open it, nothing is written.
  const settings = { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' };
  const idb2 = fakeIdb({ 'investment-device-actual-v1': { 'google-sheet-settings': settings } }), e2 = env({ idb: idb2 });
  assert.deepEqual(plain(await e2.store.holdings()), { state: 'EMPTY', reason: null, snapshot: null, source: null, as_of: null });
  assert.deepEqual(await e2.prices.deviceSettings(), { stored: true, enabled: true }, 'saved Google on: the session is on (no request)');
  assert.deepEqual(e2.priv(), []); assert.ok(idb2.opened.length >= 2 && idb2.opened.every((n) => n === 'investment-device-actual-v1'));
  assert.deepEqual([...idb2.dbs.get('investment-device-actual-v1').keys()], ['google-sheet-settings'], 'nothing written');
  // A browser without indexedDB.databases(): nothing opens outside a click; inside a storage-writing click the store reads the
  // existing database (so a backup there still carries the stored holdings).
  const idb3 = fakeIdb({ 'investment-device-actual-v1': { 'google-sheet-settings': settings } }); delete idb3.databases; const e3 = env({ idb: idb3 });
  assert.deepEqual(plain(await e3.store.holdings()), { state: 'NOT_AVAILABLE', reason: 'DEVICE_STORE_NOT_OPENED', snapshot: null, source: null, as_of: null });
  await e3.store.backup.create(); assert.deepEqual(idb3.opened, [], 'outside a click: not opened');
  const inClick = await e3.action.run(e3.click(), 'WRITE', async () => plain(await e3.store.holdings()));
  assert.deepEqual(inClick, { state: 'EMPTY', reason: null, snapshot: null, source: null, as_of: null }, 'inside a click: the stored database is read');
  assert.ok(idb3.opened.length >= 1 && idb3.opened.every((n) => n === 'investment-device-actual-v1'));
  assert.deepEqual([...idb3.dbs.get('investment-device-actual-v1').keys()], ['google-sheet-settings'], 'nothing written');
});

// ---------------------------------------------------------------- P2-2a: period returns (RAM only, after the price-tab click)
test('periodReturns: async; NOT_LOADED and no request before the tabs; PERIOD_PENDING; values = ReportBenchmarks over the loaded closes; symbol rule; identity stops first; frozen; no storage write', async () => {
  const SESSIONS = weekdays('2026-09-15', '2026-10-01');// 13 sessions: 1D and 5D have a window, 20D is too short
  assert.equal(SESSIONS.length, 13);
  const SYMS = ['SPY', 'NVDA', 'BRK-B', 'XY-Z', 'AMD', 'ADBE'];
  const tab = (syms) => ({ Prices_D: [HEAD, ...syms.flatMap((s) => SESSIONS.map((d) => [s, d, String(close(s, d)), 'YAHOO', '2026-10-02T00:00:00Z']))], Prices_M: [HEAD] });
  const COMPANIES = [{ id: 'nvda', ticker: 'NVDA', code: 'NASDAQ:NVDA' }, { id: 'NYSE:BRK.B', ticker: 'BRK.B', code: 'NYSE:BRK.B' }, { id: 'NYSE:MMM', ticker: 'MMM', code: 'NYSE:MMM' },
    { id: 'NASDAQ:ADBE', ticker: 'ADBE', code: 'NASDAQ:ADBE' }, { id: 'amd', ticker: 'AMD', code: null }, { id: 'xyz', ticker: 'XY.Z', code: null }];
  const make = async (syms) => {
    const e = env({ s: site({ tabs: tab(syms) }) }); await e.data.ready();
    // ADBE withdrawn for an identity conflict; the AMD Universe code withdrawn, so the amd TARGET is a price identity conflict.
    const real = e.data.get('sec-qgv2.json'), recs = { ...real.records };
    recs['NASDAQ:ADBE'] = { ...recs['NASDAQ:ADBE'], identity_withdrawn: true }; recs['NASDAQ:AMD'] = { ...recs['NASDAQ:AMD'], universe_withdrawal: true };
    const inputs = Object.freeze({ ...real, records: Object.freeze(recs) }), data = Object.freeze({ ...e.data, get: (n) => (n === 'sec-qgv2.json' ? inputs : e.data.get(n)) });
    return { e, p: fresh('prices.js').create({ win: e.win, action: e.action, data }) };
  };
  const { e, p } = await make(SYMS);
  assert.equal(p.periodReturns.constructor.name, 'AsyncFunction', 'an async function (the loader facade member is a promise)');
  for (const bad of ['60D', '120D', 'YTD', '1Y', 'SINCE_START', '1d', null]) await assert.rejects(p.periodReturns(bad, COMPANIES), /PERIOD_PENDING/, String(bad));
  await assert.rejects(p.periodReturns('1D', null), /COMPANIES_INVALID/); await assert.rejects(p.periodReturns('1D', [{ ticker: 'X' }]), /COMPANIES_INVALID/);
  const stops = { 'NASDAQ:ADBE': 'IDENTITY_CONFLICT_WITHDRAWN', amd: 'PRICE_IDENTITY_CONFLICT' };
  const before = await p.periodReturns('1D', COMPANIES);
  assert.equal(before.state, 'NOT_LOADED'); assert.equal(before.as_of, null);
  for (const c of COMPANIES) assert.deepEqual(before.rows[c.id], { state: 'NA', reason: stops[c.id] || 'PRICE_TABS_NOT_LOADED' }, c.id + ' before the tabs');
  assert.deepEqual(e.priv(), [], 'no request before the click');
  // Signed in with a sheet but the PriceStore flag off: loadTabs reads nothing, periodReturns stays NOT_LOADED.
  await p.prepare(e.click()); p.login(e.click()); await sources(e);
  const offLoad = await p.loadTabs(e.click());
  assert.equal(offLoad.tabs_loaded.daily, false, 'store OFF: no tabs'); assert.equal((await p.periodReturns('5D', COMPANIES)).state, 'NOT_LOADED');
  const local0 = JSON.stringify([...e.win.localStorage.map]);
  e.win.localStorage.setItem(e.store.KEYS.PRICE_STORE_ENABLED, '1');
  const local1 = JSON.stringify([...e.win.localStorage.map]);
  assert.equal((await p.loadTabs(e.click())).tabs_loaded.daily, true);
  const n = e.priv().length, RB = e.mods.ReportBenchmarks, cal = [...SESSIONS];
  for (const period of ['1D', '5D', '20D']) {
    const r = await p.periodReturns(period, COMPANIES), w = RB.periodWindow(cal, cal.at(-1), period);
    assert.equal(r.state, 'READY'); assert.equal(r.as_of, cal.at(-1)); assert.equal(r.period, period);
    assert.ok(Object.isFrozen(r) && Object.isFrozen(r.rows) && Object.isFrozen(r.rows.nvda), 'frozen');
    for (const c of COMPANIES) {
      const got = r.rows[c.id];
      if (stops[c.id]) { assert.deepEqual(got, { state: 'NA', reason: stops[c.id] }, c.id + ' stopped after the tabs too: no value'); continue; }
      if (c.id === 'NYSE:MMM') { assert.deepEqual(got, { state: 'NA', reason: 'NO_DEVICE_PRICE' }); continue; }
      if (period === '20D') { assert.equal(w.reason, 'HISTORY_TOO_SHORT'); assert.deepEqual(got, { state: 'NA', reason: 'RETURN_HISTORY_TOO_SHORT' }, c.id); continue; }
      const sym = { nvda: 'NVDA', 'NYSE:BRK.B': 'BRK-B', xyz: 'XY-Z' }[c.id], closes = Object.fromEntries(SESSIONS.map((d) => [d, close(sym, d)]));
      const want = RB.priceIndex(closes, {}, w, 'USD');
      assert.equal(want.state, 'OK'); assert.deepEqual(got, { state: 'OK', value: want.return, end: w.sessions.at(-1) }, c.id + ' ' + period + ' = ReportBenchmarks.priceIndex');
    }
  }
  assert.equal(e.priv().length, n, 'returns read RAM only (no request after the click)');
  assert.equal(JSON.stringify([...e.win.localStorage.map]), local1, 'no storage write by periodReturns'); assert.notEqual(local0, local1);
  // No SPY in the loaded tab: no session calendar.
  const x = await make(['NVDA']);
  await x.p.prepare(x.e.click()); x.p.login(x.e.click()); await sources(x.e); x.e.win.localStorage.setItem(x.e.store.KEYS.PRICE_STORE_ENABLED, '1');
  assert.equal((await x.p.loadTabs(x.e.click())).tabs_loaded.daily, true);
  const ns = await x.p.periodReturns('1D', COMPANIES);
  assert.equal(ns.state, 'READY'); assert.equal(ns.as_of, null);
  assert.deepEqual(ns.rows.nvda, { state: 'NA', reason: 'RETURN_SESSIONS_NOT_AVAILABLE' }); assert.deepEqual(ns.rows.amd, { state: 'NA', reason: 'PRICE_IDENTITY_CONFLICT' });
});
