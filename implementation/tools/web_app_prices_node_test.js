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
//    handed the gated storage, storage unchanged); backups /1–/4 round trip, /5 refused; IndexedDB never created by a read.
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
   database is one more name). */
function fakeIdb(seed = {}) {
  const dbs = new Map(Object.entries(seed).map(([n, recs]) => [n, new Map(Object.entries(recs))])), opened = [];
  const later = (fn) => setTimeout(fn, 0);
  return { opened, dbs, databases: async () => [...dbs.keys()].map((name) => ({ name, version: 1 })), cmp: () => 0, deleteDatabase: () => ({}),
    open(name) {
      opened.push(name); const created = !dbs.has(name); if (created) dbs.set(name, new Map()); const store = dbs.get(name), req = {};
      const db = { objectStoreNames: { contains: (n) => n === 'snapshots' }, createObjectStore() {}, close() {},
        transaction() { const tx = { objectStore: () => ({ get(k) { const r = { result: store.get(k) }; queueMicrotask(() => r.onsuccess && r.onsuccess()); return r; },
          getKey(k) { const r = { result: store.has(k) ? k : undefined }; queueMicrotask(() => r.onsuccess && r.onsuccess()); return r; }, put(v, k) { store.set(k, v); return {}; }, delete(k) { store.delete(k); return {}; } }) };
        later(() => tx.oncomplete && tx.oncomplete()); return tx; } };
      req.result = db; later(() => { if (created && req.onupgradeneeded) req.onupgradeneeded(); if (req.onsuccess) req.onsuccess(); }); return req;
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
  // The QGV page prices from the kept read (universeView) and the stored month-ends (facade), never asking the network.
  const before = e.priv().length, pg = await e.qgv.page();
  assert.equal(e.priv().length, before, 'the score path sent nothing');
  assert.equal(pg.price_basis.read_id, read.read_id); assert.equal(pg.price_basis.connected, true); assert.ok(pg.coverage.priced > 0);
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

test('quote: the kept Universe read first, then a stored device quote only from an existing device database; NA with a reason otherwise', async () => {
  const idb = fakeIdb(), e = env({ s: site({ tabs: { Universe: M3_VALUES } }), idb });
  assert.deepEqual(await e.prices.quote({ code: 'NASDAQ:ADBE', ticker: 'ADBE' }), { state: 'NA', reason: 'NO_DEVICE_PRICE' });
  assert.deepEqual(idb.opened, [], 'no device database, so none opened (and none created)');
  await connect(e); await sources(e); await e.prices.readUniverse(e.click());
  const q = await e.prices.quote({ code: 'NASDAQ:ADBE' });
  assert.deepEqual(q, { state: 'OK', price: px(10), currency: 'USD', source: 'UNIVERSE_SHEET', read_at: e.prices.universeView.priceBasis().acquired_at, as_of: null, time_status: 'UNCONFIRMED', freshness: 'UNDETERMINED' });
  assert.equal((await e.prices.quote({ ticker: 'BRK.B' })).price, px(1), 'by ticker (class share dots)');
  assert.deepEqual(await e.prices.quote({ ticker: 'NVDA' }), { state: 'NA', reason: 'NO_DEVICE_PRICE' }); assert.deepEqual(idb.opened, []);
});

// ---------------------------------------------------------------- store
test('store writes: without a trusted click nothing runs (CLICK_REQUIRED); an old writer handed the gated storage outside a click gets ACTION_REQUIRED; storage unchanged', async () => {
  const e = env(), K = e.store.KEYS, snapshot = () => JSON.stringify([...e.win.localStorage.map]);
  e.win.localStorage.setItem(K.PERSONAL, JSON.stringify({ version: 1, interests: ['nvda'], groups: [] }));
  const before = snapshot(), w = CUSTOM.cases[0].input.weights;
  const WRITES = { savePrefs: (ev) => e.store.savePrefs(ev, { version: 1, interests: ['amd'], groups: [] }), saveWeights: (ev) => e.store.saveWeights(ev, { name: '내 가중치', weights: w }),
    saveThesis: (ev) => e.store.saveThesis(ev, 'NVDA', 't', 'i'), saveHold: (ev) => e.store.saveHold(ev, 'NVDA', { reason: 'r', release_condition: 'c', release_date: '2026-12-31' }),
    saveRecord: (ev) => e.store.saveRecord(ev, { id: 'x' }), toggleStar: (ev) => e.store.toggleStar(ev, '0000000001'), restore: (ev) => e.store.backup.restore(ev, '{}'), download: (ev) => e.store.backup.download(ev),
    sheetSource: (ev) => e.store.sheetSource.set(ev, ID), universeSource: (ev) => e.store.universeSource.set(ev, ID), workerOrigin: (ev) => e.store.workerOrigin.set(ev, WORKER) };
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

test('store reads and settings: prefs (unreadable value never overwritten), weights versions, playbook, stars, V history read-only, sources never returned', async () => {
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
  const before = JSON.stringify([...L.map]); const h = e.store.vHistory(); assert.equal(h.v1.state, 'OK'); assert.equal(h.v2.state, 'EMPTY'); assert.equal(JSON.stringify([...L.map]), before, 'read only');
  // Sources: has() / set() only; the id or address never comes back.
  assert.equal(e.store.sheetSource.has(), false); const set = await e.store.sheetSource.set(e.click(), 'https://docs.google.com/spreadsheets/d/' + ID + '/edit');
  assert.deepEqual(set, { set: true }); assert.equal(L.getItem(K.SHEET_SOURCE), ID); assert.equal(e.store.sheetSource.has(), true);
  assert.throws(() => e.store.sheetSource.set(e.click(), 'not a sheet'), /SHEET_SOURCE_INVALID/); assert.equal(L.getItem(K.SHEET_SOURCE), ID);
  assert.deepEqual(await e.store.universeSource.set(e.click(), ID), { set: true }); assert.equal(e.store.universeSource.has(), true);
  assert.deepEqual(await e.store.universeSource.set(e.click(), ''), { set: false }); assert.equal(L.getItem(K.UNIVERSE_SOURCE), null);
  assert.throws(() => e.store.workerOrigin.set(e.click(), 'http://x.example'), /REQUEST_INVALID/);
  assert.deepEqual(await e.store.workerOrigin.set(e.click(), WORKER + '/'), { set: true, approved: true }); assert.equal(e.store.workerOrigin.approved(), true); assert.equal(L.getItem(K.WORKER_ORIGIN), WORKER);
  assert.deepEqual(await e.store.workerOrigin.set(e.click(), 'https://other-worker.someone.workers.dev'), { set: true, approved: false });
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
  assert.deepEqual(fresh('store.js').KEYS, K); assert.ok(Object.isFrozen(K));
});

test('backup: /4 round trip through the old module (no price, sheet id or Worker address); /1–/3 accepted; /5 refused; no device database created', async () => {
  const idb = fakeIdb(), e = env({ s: site({ tabs: { Universe: M3_VALUES } }), idb }), K = e.store.KEYS;
  await e.store.savePrefs(e.click(), { version: 1, interests: ['nvda', 'amd'], groups: [{ id: 'g1', name: '반도체', members: ['nvda'] }] });
  await e.store.toggleStar(e.click(), '0000000002'); await e.store.saveThesis(e.click(), 'NVDA', '논지', '무효화'); await connect(e); await sources(e); await e.prices.readUniverse(e.click());
  const payload = await e.store.backup.create(), text = JSON.stringify(payload);
  assert.equal(payload.schema, 'investment-device-backup/4'); assert.equal(payload.portfolio, null); assert.deepEqual(payload.investor_stars, ['0000000002']);
  assert.doesNotMatch(text, PX); assert.ok(!text.includes(ID) && !text.includes(WORKER) && !text.includes(TOKEN), 'no sheet id, Worker address or token');
  const e2 = env({ idb: fakeIdb() });
  assert.deepEqual(await e2.store.backup.restore(e2.click(), text), { schema: payload.schema });
  assert.deepEqual(plain(await e2.store.backup.create()), plain(payload), 'restored device gives the same backup');
  for (const k of [K.PERSONAL, K.INVESTOR_STARS, K.PLAYBOOK]) assert.equal(e2.win.localStorage.getItem(k), e.win.localStorage.getItem(k), k);
  assert.equal(e2.store.backup.restored().schema, payload.schema);
  for (const schema of ['investment-device-backup/3', 'investment-device-backup/2', 'investment-device-backup/1']) {
    const old = { ...payload, schema }; delete old.playbook; if (schema !== 'investment-device-backup/3') delete old.investor_stars; if (schema === 'investment-device-backup/1') delete old.profiles;
    const e3 = env(); assert.deepEqual(await e3.store.backup.restore(e3.click(), JSON.stringify(old)), { schema }); assert.equal(e3.store.prefs().value.interests.length, 2, schema);
  }
  const e5 = env(), before = JSON.stringify([...e5.win.localStorage.map]);
  await assert.rejects(e5.store.backup.restore(e5.click(), JSON.stringify({ ...payload, schema: 'investment-device-backup/5', user_objects: { chart: null, macro: null } })), /BACKUP_USER_OBJECTS_UNSUPPORTED/);
  await assert.rejects(e5.store.backup.restore(e5.click(), '{not json'), /BACKUP_INVALID/);
  await assert.rejects(e5.store.backup.restore(e5.click(), JSON.stringify({ ...payload, extra: 1 })), /BACKUP_/);
  await assert.rejects(e5.store.backup.restore(e5.click(), 'x'.repeat(e5.mods.DeviceBackup.MAX_BYTES + 1)), /BACKUP_TOO_LARGE/);
  assert.equal(JSON.stringify([...e5.win.localStorage.map]), before, 'a refused backup changes nothing');
  assert.deepEqual(idb.opened, [], 'a device without the database: the backup read none and the restore created none');
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
});
