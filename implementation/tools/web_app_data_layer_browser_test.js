'use strict';
// New frontend P1 · data layer in a real browser (design §3 phases A–D; P1 implementation spec, Main decisions 2–5, 15).
// Builds the development site itself (tools/web_app_test_site.js), serves the live-only public files as synthetic fixtures and
// answers Google with stand-ins, then checks the built page in Chromium:
//  - Build: every reused old file is byte-identical to web_assets, every web_app file is copied as is, no unreferenced old
//    frontend file is served, and the page loads exactly index.html's scripts in order.
//  - A (no user action): opening any route reads nothing (each route opened in a fresh load, and again on a route change
//    before the test's own call); every route can call IS2.data.ready() / IS2.qgv.page() and gets the same page; each render's
//    route.signal is aborted by the next one and the device chip's subscription ends with it; requests stay same-origin and
//    every data request is a name in IS2.data.FILES; read-only layer calls add no request either; zero Sheets / OAuth /
//    Worker / Google requests, zero localStorage / sessionStorage / IndexedDB, action.blocked() 0; every row is the temporary
//    device V (source and label from the accessor) with V null and a reason.
//  - B (imitated actions): direct calls, plain objects claiming isTrusted, forged events (a fake Event prototype, a Proxy
//    answering isTrusted), synthetic events (dispatchEvent, el.click()) and script-made submits (form.requestSubmit(),
//    submitter.click(): the browser marks those submits trusted) are refused with CLICK_REQUIRED; the price view refuses
//    private destinations and old writers get ACTION_REQUIRED; zero requests, storage unchanged.
//  - C (real clicks): Playwright clicks test-only buttons (trusted events) that save the Universe tab source, prepare and
//    sign in to Google (routed GIS stand-in) and read the Universe tab (Sheets stand-in answering unique synthetic sentinel
//    prices and market caps). Exactly the expected requests leave; V is computed; no sentinel appears in the page record,
//    the layer's status / read result / ranks, device storage, the console, any request URL or body, or the document text
//    outside [data-ram-price] (assertRamOnly, the P2 display rule, itself checked to catch a leak). No CSP violation.
//  - C2 (kept events): a real click's event kept and replayed after its dispatch (from the test, from a timer of the same
//    handler, for another kind than the click's own) is refused with no request; a nested run of the same event while its
//    action is in flight passes.
//  - D: a reload drops every RAM value (sign-in, Universe read, ranks, V) and sends nothing private; only the setting the
//    user saved by a click stays.
// Synthetic data only: sentinel values are made-up decimals; the sheet id and the token are fixtures that exist in memory.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const SHARES = require('./sec_universe_shares_fixture.js');

// The sec-qgv2.json fixture rows were collected 2026-10-13 (14-day window): a fixed clock keeps them LIVE.
const NOW = '2026-10-14T03:00:00.000Z';
const SHEET_ID = ['synthetic', 'data', 'layer', 'universe', 'sheet'].join('_');
const TOKEN = ['memory', 'only', 'synthetic', 'browser', 'session'].join('-'), SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client', SHEETS = 'https://sheets.googleapis.com';
const RANGE = "'Universe'!A1:C1025";// PrivateSubsetView.RANGE
const APPEND_URL = SHEETS + '/v4/spreadsheets/' + SHEET_ID + '/values/' + encodeURIComponent("'Prices_D'!A1") + ':append?valueInputOption=RAW&insertDataOption=INSERT_ROWS';
const VALUES_URL = SHEETS + '/v4/spreadsheets/' + SHEET_ID + '/values/' + encodeURIComponent(RANGE) + '?valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=SERIAL_NUMBER';
const UNIVERSE_SOURCE_KEY = 'investment.web.v1.universe-source';
// Live-only public files this test leaves unpublished: their 404 is intended (no console error is accepted for anything else).
const UNPUBLISHED = ['sec-public-inputs.json', 'forward-validation-ledger.json'];
const FRONTEND_SUFFIXES = ['.html', '.css', '.js', '.woff2', '.txt', '.png', '.svg'];

// ---- fixtures: the published score inputs, the public share counts, and the user's Universe tab with sentinel values
const QGV2 = F.strictPayload();
const PRICED = Object.entries(QGV2.records).filter(([c, r]) => r.state === 'LIVE' && c !== 'NASDAQ:MSFT').map(([c]) => c);// MSFT keeps no price
if (!PRICED.includes('NASDAQ:NVDA')) PRICED.push('NASDAQ:NVDA');
const pad = (i) => String(i).padStart(2, '0');
// Unique made-up decimals that no score, count or time can contain (strings first, ending in a non-zero digit, so the text
// is exactly how the number prints and what a leak would show).
const PRICE = PRICED.map((_, i) => String(311 + 7 * i) + '.0731' + pad(i) + '7'), CAP = PRICED.map((_, i) => String(52003 + 13 * i) + '.0419' + pad(i) + '3');
const SENTINELS = [...PRICE, ...CAP];
for (const v of SENTINELS) if (String(Number(v)) !== v) throw new Error('SENTINEL_NOT_CANONICAL ' + v);
const UNIVERSE_VALUES = [['code', 'marketcap', 'price'], ...PRICED.map((c, i) => [c, Number(CAP[i]), Number(PRICE[i])])];
const SHARE_ROWS = Object.fromEntries(PRICED.map((c, i) => [c, { n: 2000001 + i, shares: 1000 + i }]));
const SHARES_FILE = SHARES.payload(SHARE_ROWS, Date.parse(NOW));
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gis.init++;return{requestAccessToken:function(){window.__gis.tokens++;cfg.callback({'
  + 'access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",scope:' + JSON.stringify(SCOPE) + '});}};},revoke:function(t,done){window.__gis.revoke++;if(done)done({});}}}};';

const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const isFile = (p) => fs.existsSync(p) && fs.statSync(p).isFile();
const nameOf = (u) => decodeURIComponent(new URL(u).pathname.slice(1));
let phase = 'START';

// Built output: reused files byte-identical to web_assets, web_app files copied, no unreferenced old frontend file.
function checkBuild(out) {
  phase = 'build output';
  const reused = R.reused(), served = fs.readdirSync(out).filter((n) => isFile(path.join(out, n)));
  assert.equal(reused.length, 57);
  for (const name of reused) assert.equal(sha(path.join(out, name)), sha(R.oldPath(name)), name + ' byte-identical to web_assets');
  for (const name of fs.readdirSync(R.NEW).filter((n) => isFile(R.newPath(n)))) assert.equal(sha(path.join(out, name)), sha(R.newPath(name)), name + ' from web_app');
  const stray = fs.readdirSync(R.OLD).filter((n) => (FRONTEND_SUFFIXES.includes(path.extname(n)) || n === 'manifest.json') && !reused.includes(n) && !isFile(R.newPath(n)) && served.includes(n));
  assert.deepEqual(stray, [], 'unreferenced old frontend files are not served');
}

// Every request the browser makes (route level: URL, method, body), and every console message.
function record(context, page) {
  const log = [], consoleText = [], counts = { style: 0, client: 0, values: 0, unexpected: [] };
  return { log, consoleText, counts, async install(origin) {
    await context.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url());
      log.push({ url: req.url(), method: req.method(), body: req.postData() || '', auth: req.headers().authorization || '' });
      if (url.origin === origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { counts.style++; await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { counts.client++; await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (req.url() === VALUES_URL && req.method() === 'GET' && !req.postData() && req.headers().authorization === 'Bearer ' + TOKEN) {
        counts.values++; await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ range: "'Universe'!A1:C1025", majorDimension: 'ROWS', values: UNIVERSE_VALUES }) }); return;
      }
      counts.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    page.on('console', (m) => consoleText.push(m.text()));
  } };
}

// Test-only buttons (not part of the site): each handler passes its event to one layer action and keeps the outcome
// ({ok, value} or {ok:false, code}) for the test to read. 'keep' runs a WRITE action and keeps its event, which a timer of the
// same handler then replays for a write and a Universe read; 'nest' runs a SYNC action whose second step, after a timer, is a
// nested run of the same event. The bar is fixed at the top (CSSOM) so no screen element covers it.
async function addButtons(page) {
  await page.evaluate((id) => {
    if (document.querySelector('[data-test-actions]')) return;
    const I = window.IS2, out = window.__out = {};
    const outcome = async (f) => { try { await f(); return 'OK'; } catch (err) { return String(err && err.message); } };
    const prefs = { version: 1, interests: [], groups: [] };
    const acts = { source: (e) => I.store.universeSource.set(e, id), prepare: (e) => I.prices.prepare(e), login: (e) => I.prices.login(e), read: (e) => I.prices.readUniverse(e),
      keep: (e) => { window.__kept = e; window.__replay = new Promise((done) => setTimeout(async () => done({ write: await outcome(() => I.store.savePrefs(e, prefs)), read: await outcome(() => I.prices.readUniverse(e)) }), 50)); return I.action.run(e, 'WRITE', () => 'kept'); },
      nest: (e) => { window.__nested = e; return I.action.run(e, 'SYNC', async () => { await new Promise((r) => setTimeout(r, 30)); return I.action.run(e, 'WRITE', () => 'nested'); }); } };
    const bar = document.createElement('div'); bar.dataset.testActions = '';
    for (const [k, v] of [['position', 'fixed'], ['top', '0'], ['left', '0'], ['z-index', '2147483647']]) bar.style.setProperty(k, v);
    for (const [name, fn] of Object.entries(acts)) {
      const b = document.createElement('button'); b.type = 'button'; b.dataset.testAction = name; b.textContent = 'test ' + name;
      b.addEventListener('click', (e) => {
        let p; try { p = Promise.resolve(fn(e)); } catch (err) { p = Promise.reject(err); }
        out[name] = p.then((v) => ({ ok: true, value: v === undefined ? null : JSON.parse(JSON.stringify(v)) }), (err) => ({ ok: false, code: String(err && err.message) }));
      });
      bar.appendChild(b);
    }
    document.body.appendChild(bar);
  }, SHEET_ID);
}
async function click(page, name) { await page.locator('[data-test-action="' + name + '"]').click(); return page.evaluate((n) => window.__out[n], name); }

// The page record with summaries the checks need (the whole record goes back for the sentinel check).
async function scores(page) {
  return page.evaluate(async () => {
    const Q = window.IS2.qgv, pg = await Q.page(), again = await Q.page(), rows = pg.rows, msft = Q.row(pg, 'NASDAQ:MSFT');
    return { json: JSON.stringify(pg), coverage: JSON.stringify(Q.coverage(pg)), same: pg === again, state: pg.state, v_source: pg.v_source, engine_v_source: pg.engine_v_source,
      expected: Q.V_SOURCES.DEVICE_TEMPORARY, price_basis: pg.price_basis, n: rows.length,
      labels: [...new Set(rows.map((r) => r.source + '|' + r.source_label))], v: rows.filter((r) => r.score.v !== null).length,
      vNullWithoutReason: rows.filter((r) => r.score.v === null && !(typeof r.na_reason.v === 'string' && r.na_reason.v)).length,
      vWithReason: rows.filter((r) => r.score.v !== null && r.na_reason.v !== null).length, msft: msft ? { v: msft.score.v, reason: msft.na_reason.v } : null };
  });
}

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: QGV2 }, 'sec-universe-shares.json': { json: SHARES_FILE } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    checkBuild(s.out);
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.clock.setFixedTime(new Date(NOW));
    await context.addInitScript(() => { window.__csp = 0; window.__gis = { init: 0, tokens: 0, revoke: 0 }; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED }), rec = record(context, page);
    await rec.install(s.origin);
    const FILES = new Set(), pageFiles = new Set([...R.scripts(), ...fs.readdirSync(R.NEW)]);
    const since = (at) => rec.log.slice(at);
    const outside = (list) => list.filter((r) => new URL(r.url).origin !== s.origin).map((r) => r.method + ' ' + r.url);
    const all = (list) => list.map((r) => r.method + ' ' + r.url);
    const dataNames = (list) => list.filter((r) => new URL(r.url).origin === s.origin).map((r) => nameOf(r.url)).filter((n) => n && !pageFiles.has(n));

    // ---------------------------------------------------------------- A: no user action
    phase = 'A open';
    await page.goto(s.base + '#/'); await page.locator('main[data-route]').waitFor();
    assert.deepEqual(dataNames(rec.log), [], 'opening the page reads no data file (screens call IS2.data.ready())');
    assert.deepEqual(await page.evaluate(() => [...document.scripts].map((x) => x.getAttribute('src'))), R.scripts(), 'the page loads index.html\'s scripts in order');
    for (const n of await page.evaluate(() => window.IS2.data.FILES)) FILES.add(n);
    const routes = await page.evaluate(() => { const I = window.IS2; return [...I.MENU.map((m) => I.href(m.id)), I.href('company', 'NYSE:FIX'), ...I.DETAILS.map((d) => I.href('detail', d.id)), '#/nowhere/x']; });
    assert.equal(routes.length, 9 + 1 + 7 + 1);
    const settle = () => page.evaluate(() => new Promise((r) => setTimeout(r, 100)));
    for (const hash of routes) {
      phase = 'A fresh ' + hash;
      const at0 = rec.log.length;
      await page.goto(s.base + hash); await page.reload(); await page.locator('main[data-route]').waitFor(); await settle();
      assert.deepEqual(dataNames(since(at0)), [], hash + ': opening the route in a fresh load reads no data file');
    }
    for (const hash of routes) {
      phase = 'A ' + hash;
      const at0 = rec.log.length;
      await page.goto(s.base + hash); await page.locator('main[data-route]').waitFor(); await settle();
      assert.deepEqual(dataNames(since(at0)), [], hash + ': a route change reads nothing before a screen asks');
      const r = await page.evaluate(async () => { const I = window.IS2, pub = await I.data.ready(), pg = await I.qgv.page(); window.__first = window.__first || pg; return { generation: pub.generation, same: pg === window.__first, state: pg.state }; });
      assert.deepEqual(r, { generation: 1, same: true, state: 'READY' }, hash + ': every screen shares one page of one generation');
    }
    phase = 'A route signals';
    const sig = await page.evaluate(async () => {
      const I = window.IS2, P = I.prices, seen = []; let live = 0;
      I.prices = Object.freeze({ ...P, subscribe: (fn, o) => { live++; if (o && o.signal) o.signal.addEventListener('abort', () => { live--; }, { once: true }); return P.subscribe(fn, o); } });
      I.register('lab', (route) => { seen.push(route.signal); return I.h('p', null, 'lab'); });
      const go = (h) => new Promise((r) => { window.addEventListener('hashchange', () => setTimeout(r, 0), { once: true }); location.hash = h; });
      try {
        await go('#/lab'); const first = seen[seen.length - 1]; await go('#/qgv'); const firstAborted = first.aborted;
        for (let i = 0; i < 10; i++) await go(i % 2 ? '#/lab' : '#/news');
        return { firstAborted, live, lastAborted: seen[seen.length - 1].aborted, renders: seen.length };
      } finally { I.prices = P; }
    });
    assert.deepEqual(sig, { firstAborted: true, live: 1, lastAborted: false, renders: 6 }, 'the next render aborts route.signal; the chip keeps one subscription');
    phase = 'A read-only calls';
    const reads = await page.evaluate(async () => {
      const I = window.IS2, keep = (x) => (x && typeof x === 'object' ? { state: x.state, reason: x.reason !== undefined ? x.reason : null } : x);
      await I.data.list('news'); await I.data.list('sec'); await I.data.shares(); await I.data.static('entities.json');
      return { quote: await I.prices.quote({ code: 'NASDAQ:NVDA', ticker: 'NVDA' }), settings: await I.prices.deviceSettings(), holdings: keep(await I.store.holdings()),
        stored: (await I.engines.virtual.stored({ reportDate: '2026-10-20' })).state, forward: (await I.engines.virtual.forward()).state, draft: typeof (await I.engines.target.draft()), macro: (await I.engines.macro.current()) !== undefined,
        status: I.prices.status(), shares: I.data.state('sec-universe-shares.json').state, ledger: I.data.state('forward-validation-ledger.json').state };
    });
    assert.deepEqual(reads.quote, { state: 'NA', reason: 'NO_DEVICE_PRICE' });
    assert.deepEqual(reads.settings, { stored: false, enabled: false }, 'no device database: the saved Google setting is not read (nothing created)');
    assert.deepEqual(reads.holdings, { state: 'NOT_AVAILABLE', reason: 'DEVICE_STORE_NOT_OPENED' });
    assert.equal(reads.stored, 'NOT_AVAILABLE', 'stored run after the start day, without sign-in and Worker address');
    assert.equal(reads.forward, 'NOT_PUBLISHED');
    assert.equal(reads.draft, 'object');
    assert.deepEqual([reads.status.google.connected, reads.status.universe.state, reads.status.sheet.set, reads.status.universe_source.set], [false, 'NOT_READ', false, false]);
    assert.deepEqual([reads.shares, reads.ledger], ['OK', 'NOT_PUBLISHED']);
    phase = 'A boundaries';
    assert.deepEqual(outside(rec.log), [], 'no Sheets / OAuth / Worker / accounts.google.com request (none leaves the origin)');
    assert.deepEqual(seen.outside, []);
    const dataA = dataNames(rec.log);
    assert.ok(dataA.includes('sec-qgv2.json') && dataA.includes('actual-catalog.json'), 'the score inputs were read');
    assert.deepEqual(dataA.filter((n) => !FILES.has(n)), [], 'every data request is a name in IS2.data.FILES');
    assert.deepEqual(rec.log.filter((r) => r.method !== 'GET' || r.body), [], 'every request is a plain GET');
    assert.deepEqual(seen.errors, [], 'no console error except the intended 404s');
    const stA = await site.storage(page);
    assert.deepEqual([stA.local, stA.session, stA.idb], [0, 0, 0], 'nothing in localStorage / sessionStorage / IndexedDB');
    assert.equal(await page.evaluate(() => window.IS2.action.blocked()), 0, 'nothing was refused: no layer call tried a private request or a write');
    const a = await scores(page);
    assert.equal(a.state, 'READY'); assert.equal(a.same, true);
    assert.ok(a.n > 500, 'the whole Universe plus TARGET rows');
    assert.deepEqual(a.expected, { id: 'DEVICE_TEMPORARY', ko: '임시 V', note: '기기 시세로 계산 · 중앙 V 미게시' });
    assert.deepEqual([a.v_source, a.engine_v_source], [a.expected, a.expected]);
    assert.deepEqual(a.labels, ['DEVICE_TEMPORARY|' + a.expected.ko], 'every row is the temporary device V, labelled by the accessor');
    assert.deepEqual([a.v, a.vNullWithoutReason], [0, 0], 'no device price yet: every V is null and carries its reason');
    assert.deepEqual(a.msft, { v: null, reason: 'NO_DEVICE_PRICE' });
    assert.equal(a.price_basis.connected, false);

    // ---------------------------------------------------------------- B: imitated actions
    phase = 'B imitated actions';
    await addButtons(page);
    const atB = rec.log.length, blockedB = await page.evaluate(() => window.IS2.action.blocked());
    const b = await page.evaluate(async ({ id, values, append }) => {
      const I = window.IS2, T = I.engines.target, W = window.InvestmentAppConfig;
      const outcome = async (f) => { try { await f(); return 'OK'; } catch (e) { return String(e && e.message); } };
      const calls = {
        'data.refresh': (e) => I.data.refresh(e), 'store.universeSource.set': (e) => I.store.universeSource.set(e, id), 'store.sheetSource.set': (e) => I.store.sheetSource.set(e, id),
        'store.savePrefs': (e) => I.store.savePrefs(e, { version: 1, interests: [], groups: [] }), 'store.backup.restore': (e) => I.store.backup.restore(e, '{}'),
        'prices.prepare': (e) => I.prices.prepare(e), 'prices.login': (e) => I.prices.login(e), 'prices.logout': (e) => I.prices.logout(e), 'prices.readUniverse': (e) => I.prices.readUniverse(e),
        'prices.useTabs': (e) => I.prices.useTabs(e), 'prices.loadTabs': (e) => I.prices.loadTabs(e), 'prices.syncSymbols': (e) => I.prices.syncSymbols(e, ['SPY'], '1d'),
        'prices.syncUniverse': (e) => I.prices.syncUniverse(e), 'prices.history': (e) => I.prices.history(e, 'nvda'),
        'target.build': (e) => T.build(e), 'target.finalize': (e) => T.finalize(e), 'target.answer': (e) => T.answer(e, { symbol: 'NVDA', answer: 'AGREE' }),
        'target.selectRuleB': (e) => T.selectRuleB(e), 'target.compare': (e) => T.compare(e), 'target.syncScoringPrices': (e) => T.syncScoringPrices(e),
      };
      const events = { none: () => undefined, object: () => ({ type: 'click', isTrusted: true }), mouse: () => new MouseEvent('click'), enter: () => new KeyboardEvent('keydown', { key: 'Enter' }), submit: () => new Event('submit'),
        forgedProto: () => Object.create(Event.prototype, { isTrusted: { value: true }, type: { value: 'click' } }),
        forgedProxy: () => new Proxy(new MouseEvent('click'), { get: (t, k) => (k === 'isTrusted' ? true : Reflect.get(t, k)) }) };
      const refused = {};
      for (const [name, f] of Object.entries(calls)) for (const [kind, ev] of Object.entries(events)) { const o = await outcome(() => f(ev())); if (o !== 'CLICK_REQUIRED') refused[name + ' / ' + kind] = o; }
      // Synthetic clicks on the test buttons (isTrusted false): dispatchEvent and HTMLElement.click().
      const synthetic = {};
      for (const el of document.querySelectorAll('[data-test-action]')) {
        const n = el.dataset.testAction;
        el.dispatchEvent(new MouseEvent('click', { bubbles: true })); synthetic[n + ' dispatch'] = (await window.__out[n]).code;
        el.click(); synthetic[n + ' click()'] = (await window.__out[n]).code;
      }
      // Script-made submits: form.requestSubmit() and a script's submitter.click() (the browser marks those submits trusted).
      const form = document.createElement('form'), submitter = document.createElement('button'), submits = [];
      submitter.type = 'submit'; form.appendChild(submitter); document.body.appendChild(form);
      form.addEventListener('submit', (ev) => { ev.preventDefault(); submits.push([ev.isTrusted, outcome(() => I.store.savePrefs(ev, { version: 1, interests: [], groups: [] })), outcome(() => I.prices.prepare(ev))]); });
      submitter.addEventListener('click', (ev) => { submits.push([ev.isTrusted, outcome(() => I.store.savePrefs(ev, { version: 1, interests: [], groups: [] })), outcome(() => I.prices.prepare(ev))]); });
      form.requestSubmit(); submitter.click(); form.remove();
      const submitted = []; for (const [trusted, a, b2] of submits) submitted.push([trusted, await a, await b2]);
      // The price view itself, outside a click: every private destination refused; old writers handed gated storage refused.
      const worker = W.privateHistoryWorkerOrigin, pv = I.prices.priceView;
      const views = {
        values: await outcome(() => pv.fetch(values, {})), append: await outcome(() => pv.fetch(append, { method: 'POST', body: '{}' })),
        oauth: await outcome(() => pv.fetch('https://oauth2.googleapis.com/token', { method: 'POST' })), history: await outcome(() => pv.fetch(worker + '/history?symbol=NVDA&range=1y', {})),
        worker: await outcome(() => pv.fetch(worker + '/quote', {})), storeWrite: await outcome(() => I.store.storage.setItem('x', 'y')), viewWrite: await outcome(() => pv.localStorage.setItem('x', 'y')),
        sessionWrite: await outcome(() => pv.sessionStorage.setItem('x', 'y')), idb: await outcome(() => pv.indexedDB.open('investment-device-actual-v1', 1)),
      };
      return { refused, count: Object.keys(calls).length * Object.keys(events).length, synthetic, submitted, views, blocked: I.action.blocked() };
    }, { id: SHEET_ID, values: VALUES_URL, append: APPEND_URL });
    assert.ok(b.count >= 100);
    assert.deepEqual(b.refused, {}, 'every direct call / plain object / forged or synthetic event is refused with CLICK_REQUIRED');
    assert.deepEqual(Object.values(b.synthetic), Array(12).fill('CLICK_REQUIRED'), 'synthetic clicks on the buttons are refused');
    assert.equal(b.submitted.length, 3, 'requestSubmit → submit; submitter.click() → click, then submit');
    assert.ok(b.submitted.filter(([trusted]) => trusted).length >= 1, 'the browser marked a script-made submit trusted');
    assert.deepEqual(b.submitted.map(([, a, c]) => [a, c]), Array(3).fill(['CLICK_REQUIRED', 'CLICK_REQUIRED']), 'and it is refused: a submit is not a gesture');
    assert.deepEqual(b.views, { values: 'CLICK_REQUIRED', append: 'CLICK_REQUIRED', oauth: 'CLICK_REQUIRED', history: 'CLICK_REQUIRED', worker: 'CLICK_REQUIRED',
      storeWrite: 'ACTION_REQUIRED', viewWrite: 'ACTION_REQUIRED', sessionWrite: 'ACTION_REQUIRED', idb: 'DEVICE_STORE_NOT_OPENED' });
    assert.equal(b.blocked - blockedB, 8, 'the five private requests and three storage writes were counted as blocked');
    assert.deepEqual(since(atB), [], 'imitated actions sent no request at all');
    const stB = await site.storage(page);
    assert.deepEqual([stB.local, stB.session, stB.idb], [0, 0, 0], 'storage unchanged, no database created');

    // ---------------------------------------------------------------- C: real clicks
    phase = 'C save source';
    let at = rec.log.length;
    assert.deepEqual(await click(page, 'source'), { ok: true, value: { set: true } });
    assert.deepEqual(since(at), [], 'saving the source sends nothing');
    assert.deepEqual(Object.keys((await site.storage(page)).localItems), [UNIVERSE_SOURCE_KEY], 'the click wrote its own key only');
    phase = 'C prepare';
    at = rec.log.length;
    assert.deepEqual(await click(page, 'prepare'), { ok: true, value: null });
    assert.deepEqual(all(since(at)), ['GET ' + GIS_STYLE, 'GET ' + GIS_CLIENT], 'prepare loads the GIS stylesheet, then the GIS script, nothing else');
    phase = 'C login';
    at = rec.log.length;
    assert.deepEqual(await click(page, 'login'), { ok: true, value: null });
    assert.deepEqual(since(at), [], 'the token arrives inside the click with no request');
    const g = await page.evaluate(() => ({ google: window.IS2.prices.status().google, gis: window.__gis }));
    assert.deepEqual([g.google.enabled, g.google.ready, g.google.connected], [true, true, true]);
    assert.deepEqual(g.gis, { init: 1, tokens: 1, revoke: 0 });
    phase = 'C read';
    at = rec.log.length;
    const read = await click(page, 'read');
    assert.equal(read.ok, true, JSON.stringify(read));
    assert.deepEqual([read.value.state, read.value.inputs, read.value.read_at], ['READY', 'READY', NOW]);
    const readRequests = since(at);
    assert.deepEqual(all(readRequests), ['GET ' + VALUES_URL, 'GET ' + s.base + 'sec-universe-shares.json'], 'exactly one Sheets values read, then the share counts re-read through the strict public path');
    phase = 'C scores';
    at = rec.log.length;
    const c = await scores(page);
    assert.deepEqual(since(at), [], 'the score path sends nothing');
    assert.equal(c.state, 'READY'); assert.equal(c.same, true);
    assert.deepEqual([c.v_source, c.engine_v_source], [c.expected, c.expected]);
    assert.deepEqual(c.labels, ['DEVICE_TEMPORARY|' + c.expected.ko]);
    assert.ok(c.v >= 8, 'V computed from the device prices (' + c.v + ' rows)');
    assert.deepEqual([c.vNullWithoutReason, c.vWithReason], [0, 0], 'a value has no reason, a null always has one');
    assert.deepEqual(c.msft, { v: null, reason: 'NO_DEVICE_PRICE' }, 'the row without a sheet price keeps V null with its reason');
    assert.deepEqual([c.price_basis.connected, c.price_basis.source, c.price_basis.read_at], [true, 'GOOGLEFINANCE_PRIVATE_UNIVERSE', NOW]);
    assert.equal(c.price_basis.time_status, 'UNCONFIRMED', 'the Universe tab carries no price time');
    phase = 'C RAM display';
    const quote = await page.evaluate(async (code) => { const q = await window.IS2.prices.quote({ code }); const el = document.createElement('p'); el.dataset.ramPrice = ''; el.textContent = String(q.price) + ' ' + q.currency; document.body.appendChild(el); return q; }, PRICED[0]);
    assert.deepEqual([quote.state, String(quote.price), quote.source, quote.time_status], ['OK', PRICE[0], 'UNIVERSE_SHEET', 'UNCONFIRMED'], 'quote() is the one way out, for [data-ram-price]');
    await site.assertRamOnly(page, SENTINELS, 'C');
    await page.evaluate((v) => { const el = document.createElement('p'); el.dataset.testLeak = ''; el.textContent = v; document.body.appendChild(el); }, PRICE[1]);
    await assert.rejects(site.assertRamOnly(page, SENTINELS), /sentinel price outside/, 'the display rule check catches a price outside [data-ram-price]');
    await page.evaluate(() => { document.querySelector('[data-test-leak]').remove(); });
    phase = 'C sentinels';
    const layer = await page.evaluate(() => { const P = window.IS2.prices; return { status: JSON.stringify(P.status()), ranks: JSON.stringify(P.universeRanks(), (k, v) => (v instanceof Map ? [...v] : v)), rank: JSON.stringify(P.rankFor({ ticker: 'NVDA' })) }; });
    const stC = await site.storage(page);
    assert.deepEqual([stC.local, stC.session, stC.idb], [1, 0, 0], 'only the saved source; no price stored; no database created');
    const requestText = rec.log.map((r) => r.url + '\n' + r.body);
    const where = {
      page: site.leaks([c.json, c.coverage], SENTINELS), layer: site.leaks([layer.status, layer.ranks, layer.rank, JSON.stringify(read.value)], SENTINELS),
      storage: site.leaks([stC.localItems, stC.sessionItems, stC.idbNames], SENTINELS), console: site.leaks(rec.consoleText, SENTINELS), requests: site.leaks(requestText, SENTINELS),
    };
    assert.deepEqual(where, { page: [], layer: [], storage: [], console: [], requests: [] }, 'no sentinel price or market cap outside RAM');
    const sameOrigin = rec.log.filter((r) => new URL(r.url).origin === s.origin);
    assert.deepEqual(site.leaks([c.json, layer.status, layer.ranks, stC.localItems, stC.sessionItems, stC.idbNames, ...rec.consoleText, ...sameOrigin.map((r) => r.url + r.body + r.auth)], [TOKEN]), [], 'the token stays in memory');
    assert.deepEqual(site.leaks([c.json, layer.status, ...rec.consoleText], [SHEET_ID]), [], 'the sheet id never comes back to a screen');
    assert.deepEqual(rec.counts, { style: 1, client: 1, values: 1, unexpected: [] }, 'every Google request was the expected stand-in');
    assert.equal(await page.evaluate(() => window.IS2.action.blocked()), b.blocked, 'the real clicks needed no refusal');
    assert.equal(await page.evaluate(() => window.__csp), 0, 'no CSP violation (GIS stylesheet and script are allowed sources)');
    assert.deepEqual(seen.errors, [], 'no console error');

    // ---------------------------------------------------------------- C2: kept events
    phase = 'C2 kept events';
    at = rec.log.length;
    const blockedC2 = await page.evaluate(() => window.IS2.action.blocked()), storeC2 = JSON.stringify((await site.storage(page)).localItems);
    assert.deepEqual(await click(page, 'keep'), { ok: true, value: 'kept' }, 'a real click runs its own action');
    const replayed = await page.evaluate(async () => {
      const I = window.IS2, e = window.__kept, outcome = async (f) => { try { await f(); return 'OK'; } catch (err) { return String(err && err.message); } };
      return { timer: await window.__replay, later: { read: await outcome(() => I.prices.readUniverse(e)), write: await outcome(() => I.store.savePrefs(e, { version: 1, interests: [], groups: [] })), login: await outcome(() => I.prices.prepare(e)) },
        trusted: e.isTrusted, phase: e.eventPhase };
    });
    assert.deepEqual([replayed.trusted, replayed.phase], [true, 0], 'the kept event is still trusted, but its dispatch is over');
    assert.deepEqual(replayed.timer, { write: 'CLICK_REQUIRED', read: 'CLICK_REQUIRED' }, 'replayed from a timer of the same handler, for a write and for another kind: refused');
    assert.deepEqual(replayed.later, { read: 'CLICK_REQUIRED', write: 'CLICK_REQUIRED', login: 'CLICK_REQUIRED' }, 'replayed later without a gesture: refused');
    assert.deepEqual(await click(page, 'nest'), { ok: true, value: 'nested' }, 'a nested run of the same event while its action is in flight passes');
    assert.equal(await page.evaluate(async () => { try { await window.IS2.action.run(window.__nested, 'WRITE', () => 1); return 'OK'; } catch (err) { return err.message; } }), 'CLICK_REQUIRED', 'once its action settled, the event is a replay');
    assert.deepEqual(since(at), [], 'no request from any replay'); assert.equal(rec.counts.values, 1, 'no second Sheets read');
    assert.equal(JSON.stringify((await site.storage(page)).localItems), storeC2, 'no write from any replay');
    assert.equal(await page.evaluate(() => window.IS2.action.blocked()), blockedC2, 'refused at the gate before any request or write was tried');
    assert.deepEqual(seen.errors, [], 'no console error');

    // ---------------------------------------------------------------- D: reload clears RAM
    phase = 'D reload';
    at = rec.log.length;
    await page.reload(); await page.locator('main[data-route]').waitFor();
    assert.deepEqual(outside(since(at)), [], 'nothing private after a reload');
    assert.deepEqual(dataNames(since(at)), [], 'and no data file before a screen asks');
    const d = await page.evaluate(() => { const P = window.IS2.prices, st = P.status(); return { google: st.google.connected, enabled: st.google.enabled, universe: st.universe.state, ranks: P.universeRanks(), gis: typeof window.google }; });
    assert.deepEqual(d, { google: false, enabled: false, universe: 'NOT_READ', ranks: null, gis: 'undefined' }, 'sign-in, the Universe read and ranks were RAM only');
    const after = await scores(page);
    assert.deepEqual([after.v, after.vNullWithoutReason, after.price_basis.connected], [0, 0, false], 'V back to null with reasons');
    assert.deepEqual(after.msft, { v: null, reason: 'NO_DEVICE_PRICE' });
    await addButtons(page);
    at = rec.log.length;
    assert.deepEqual(await click(page, 'read'), { ok: false, code: 'AUTH_REQUIRED' }, 'a read after the reload needs a new sign-in');
    assert.deepEqual(outside(since(at)), [], 'refused before any request');
    const stD = await site.storage(page);
    assert.deepEqual([Object.keys(stD.localItems), stD.session, stD.idb], [[UNIVERSE_SOURCE_KEY], 0, 0], 'only the setting the user saved stays on the device');
    assert.deepEqual(site.leaks([after.json, stD.localItems, stD.sessionItems, await page.evaluate(() => document.documentElement.textContent), ...rec.consoleText, ...rec.log.map((r) => r.url + r.body)], SENTINELS), []);
    assert.deepEqual(rec.counts, { style: 1, client: 1, values: 1, unexpected: [] }, 'no further Google request');
    assert.deepEqual(seen.outside.filter((u) => ![GIS_STYLE, GIS_CLIENT, VALUES_URL].includes(u)), []);
    assert.deepEqual(seen.errors, [], 'no console error');
    await context.close();
    console.log('web app data layer: build reuse, no-action reads (A), refused imitations (B), click-only prices with no leak (C), kept events refused (C2), RAM cleared on reload (D) ok');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
