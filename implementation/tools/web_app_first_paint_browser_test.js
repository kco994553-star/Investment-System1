'use strict';
// New frontend P2-1a · first paint on a phone (owner 2026-10-24 "휴대폰 첫 화면 비용"; docs/frontend_v2/P1_DATA_LAYER.md §1.1).
// Builds the development site (tools/web_app_test_site.js build), serves it on a loopback port the way Pages serves it (text
// gzip-compressed, fonts as they are, no-store; FIRST_PAINT_ENCODING=identity serves everything uncompressed for comparison)
// and measures cold loads in Chromium through CDP: viewport 390×844, Network.emulateNetworkConditions (150 ms latency,
// 1.6 Mbps down, 750 kbps up), Emulation.setCPUThrottlingRate 4, cache disabled, a fresh browser context per run.
//  - first screen: the later of the shell's is2-first-paint mark (two animation frames after its first render) and the
//    first-contentful-paint entry, from navigation start;
//  - first transfer: Network.loadingFinished encodedDataLength of every request that finished before that moment (requests still
//    in flight then are counted apart, not added);
//  - ready: the loader's is2-ready mark (IS2.ready); total: the bytes finished by then; all: the bytes once the fonts settled.
// Each run first proves the throttling is in effect, and fails with a clear message otherwise: a fixed busy loop takes at least
// CPU × 0.6 times as long after Emulation.setCPUThrottlingRate as before it (timed on the blank page before and after the call,
// and again in the loaded page after IS2.ready, so the setting survived the navigation); the document request takes at least
// the emulated latency; the largest response of the run (its size known from the server) takes at least the time the emulated
// bandwidth needs for its bytes, plus the latency.
// The model leaves out connection setup: a loopback HTTP/1.1 server (no DNS, TCP or TLS handshake; Pages is HTTPS + HTTP/2) and
// device scale 1, so a real first visit is slower by the setup round trips (about 3 × 150 ms); the real-phone check stays in P2-1.
// Three runs; the median of each number is asserted against the owner's targets: first screen ≤ 2,000 ms and first transfer
// ≤ 100 KB (102,400 bytes). Medians on one line: FIRST_PAINT ms=… first_kb=… ready_ms=… total_kb=…; each run on its own line.
// Each run also checks the structure at the first-paint moment: the search box, the menu and the tabs are drawn, the device chip
// says 연결 전, the layer is not loaded (no old module global, the IS2 facades answer IS2.NOT_READY, the loader still waits and
// the page holds index.html's scripts only), and the network log has no LOAD_ORDER request before the shell was drawn.
// Contract (no throttling, after the runs):
//  - Hold: the first LOAD_ORDER file held back by the server. Getters and values answer IS2.NOT_READY; an action on a real click
//    throws LAYER_NOT_READY and nothing is requested or written; a promise method waits for IS2.ready; a subscription is attached
//    when ready (one aborted before is not); after the release, a facade a screen kept forwards to the layer, the chip follows
//    the layer, and the page has loaded index.html's scripts and then LOAD_ORDER, in order.
//  - Failure: a listed file that is missing (404) or throws while it runs rejects IS2.ready with LOADER_FAILED <file>; the
//    facades are back on IS2 and refuse (IS2.LOAD_FAILED, a rejected promise, the error on a click); the chip says 연결 실패 and
//    the shell shows its fixed notice (일부 파일을 불러오지 못했습니다 · 새로고침해 주세요, no file name) with a reload button, in
//    view at 390×844 and on every later route. The button only reloads: its click makes no request but the page's own reload
//    (404 case), after which the page fails and shows the notice again.
//  - Always: no CSP violation, no request leaves the origin, nothing stored, no console error but the provoked ones.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const zlib = require('node:zlib');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');

const RUNS = 3, LIMIT_MS = 2000, LIMIT_BYTES = 100 * 1024;
const VIEWPORT = { width: 390, height: 844 };
const NET = { offline: false, latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8 }, CPU = 4;
const CPU_MIN_RATIO = CPU * 0.6;// measured about 4.2 to 5.2 at rate 4; 1 would mean no throttling
const FAILED_NOTE = '일부 파일을 불러오지 못했습니다 · 새로고침해 주세요';
const GZIP = process.env.FIRST_PAINT_ENCODING !== 'identity';
const LOAD = R.loadOrder(), FIRST = R.firstPaint();
const OLD_GLOBALS = ['QgvScores', 'DataRefresh', 'DeviceActual', 'PriceStore', 'EntitySearch', 'TargetV1Builder'];
const PREFS = { version: 1, interests: [], groups: [] };
let phase = 'START';

// Pages-like server over the built folder: gzip for text (not woff2), no-store. Contract hooks: hold(name) keeps a file's answer
// until release(); override(name, {status, body}) answers a file differently.
function serve(dir) {
  const holds = new Map(), overrides = new Map(), gz = new Map(), sent = new Map();
  const server = http.createServer((req, res) => {
    const name = decodeURIComponent(new URL(req.url, 'http://x').pathname.slice(1)) || 'index.html';
    const send = () => {
      const o = overrides.get(name);
      if (o) { res.writeHead(o.status, { 'content-type': 'text/javascript', 'cache-control': 'no-store' }); res.end(o.body || ''); sent.set(name, Buffer.byteLength(o.body || '')); return; }
      const file = path.join(dir, name);
      if (!file.startsWith(dir + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404, { 'cache-control': 'no-store' }); res.end(); return; }
      const type = site.TYPES[path.extname(file)] || 'application/octet-stream', zip = GZIP && /gzip/.test(req.headers['accept-encoding'] || '') && path.extname(file) !== '.woff2';
      let body = fs.readFileSync(file);
      if (zip) { if (!gz.has(name)) gz.set(name, zlib.gzipSync(body)); body = gz.get(name); }
      res.writeHead(200, { 'content-type': type, 'cache-control': 'no-store', ...(zip ? { 'content-encoding': 'gzip' } : {}) });
      res.end(body); sent.set(name, body.length);
    };
    const h = holds.get(name);
    if (h) { h.arrived(); h.gate.then(send); } else send();
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({
    base: 'http://127.0.0.1:' + server.address().port + '/', origin: 'http://127.0.0.1:' + server.address().port, sent,
    hold(name) { let release, arrived; const seen = new Promise((x) => { arrived = x; }), gate = new Promise((x) => { release = x; }); holds.set(name, { gate, arrived }); return { seen, release: () => { holds.delete(name); release(); } }; },
    override(name, o) { if (o === null) overrides.delete(name); else overrides.set(name, o); },
    close: () => new Promise((x) => server.close(x)),
  })));
}

// Init script of a measured run: snapshots the page at the shell's is2-first-paint mark (inside that animation frame, before the
// loader moves) and resolves window.__done at is2-ready / is2-load-failed.
function initMeasure(oldGlobals) {
  const fp = window.__fp = { snap: null };
  let done; window.__done = new Promise((r) => { done = r; });
  const mark = performance.mark.bind(performance);
  performance.mark = function (name, opts) {
    const out = mark(name, opts);
    if (name === 'is2-first-paint' && !fp.snap) {
      const I = window.IS2 || {}, chip = document.querySelector('[data-device-chip]'), NR = I.NOT_READY;
      fp.snap = { search: !!document.querySelector('[data-search-input]'), menu: document.querySelectorAll('.top .menu a').length, tabs: document.querySelectorAll('.tabbar [data-tab]').length,
        chip: chip ? chip.textContent : null, notice: !!document.querySelector('[data-load-failed]'), state: typeof I.loadState === 'function' ? I.loadState() : null, oldGlobals: oldGlobals.filter((g) => typeof window[g] !== 'undefined'),
        facades: NR ? [I.data.FILES === NR, I.qgv.rankLabel('DEVICE_TEMPORARY') === NR, I.prices.status() === NR, I.store.prefs() === NR] : null,
        scripts: [...document.scripts].map((s) => s.getAttribute('src')) };
    }
    if (name === 'is2-ready' || name === 'is2-load-failed') done(name);
    return out;
  };
}

// A fixed CPU busy loop run in the page: the best of three passes, in ms (the result keeps the loop from being optimised away).
function busy() { let best = Infinity, x = 0; for (let k = 0; k < 3; k++) { const t = performance.now(); for (let i = 0; i < 6e6; i++) x = (x * 31 + i) | 0; best = Math.min(best, performance.now() - t); } return [best, x]; }
const median = (xs) => { const s = [...xs].sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
const kb = (n) => (n / 1024).toFixed(1);
const nameOf = (u) => { try { return decodeURIComponent(new URL(u).pathname.slice(1)); } catch (_) { return u; } };

async function measure(browser, srv, run) {
  phase = 'run ' + run;
  const context = await browser.newContext({ viewport: VIEWPORT });
  try {
    await context.addInitScript(initMeasure, OLD_GLOBALS);
    const page = await context.newPage(), cdp = await context.newCDPSession(page), reqs = new Map();
    let offset = null;// wall ms - CDP monotonic ms (requestWillBeSent carries both)
    cdp.on('Network.requestWillBeSent', (e) => { if (offset === null && e.wallTime) offset = e.wallTime * 1000 - e.timestamp * 1000; if (!reqs.has(e.requestId)) reqs.set(e.requestId, { url: e.request.url, start: e.timestamp }); });
    cdp.on('Network.loadingFinished', (e) => { const r = reqs.get(e.requestId); if (r) { r.end = e.timestamp; r.bytes = e.encodedDataLength; } });
    cdp.on('Network.loadingFailed', (e) => { const r = reqs.get(e.requestId); if (r) { r.end = e.timestamp; r.failed = e.errorText; } });
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', NET);
    const cpuBase = (await page.evaluate(busy))[0];
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: CPU });
    const cpuSet = (await page.evaluate(busy))[0];
    assert.ok(cpuSet >= cpuBase * CPU_MIN_RATIO, `CPU throttling is not in effect: the busy loop took ${cpuSet.toFixed(1)} ms after setCPUThrottlingRate ${CPU} and ${cpuBase.toFixed(1)} ms before (ratio ${(cpuSet / cpuBase).toFixed(2)}, needs >= ${CPU_MIN_RATIO})`);
    const errors = []; page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); }); page.on('pageerror', (e) => errors.push(String(e)));
    await page.goto(srv.base + '#/', { waitUntil: 'commit' });
    assert.equal(await page.evaluate(() => window.__done), 'is2-ready', 'the layer loaded');
    const cpuPage = (await page.evaluate(busy))[0];
    assert.ok(cpuPage >= cpuBase * CPU_MIN_RATIO, `CPU throttling did not survive the navigation: the busy loop took ${cpuPage.toFixed(1)} ms in the loaded page and ${cpuBase.toFixed(1)} ms unthrottled (ratio ${(cpuPage / cpuBase).toFixed(2)}, needs >= ${CPU_MIN_RATIO})`);
    await page.evaluate(() => document.fonts.ready.then(() => new Promise((r) => setTimeout(r, 500))));
    const pg = await page.evaluate(() => {
      const marks = Object.fromEntries(performance.getEntriesByType('mark').map((m) => [m.name, m.startTime]));
      const fcp = performance.getEntriesByType('paint').find((p) => p.name === 'first-contentful-paint');
      return { origin: performance.timeOrigin, marks, fcp: fcp ? fcp.startTime : null, snap: window.__fp.snap, chip: document.querySelector('[data-device-chip]').textContent };
    });
    assert.ok(offset !== null && pg.marks['is2-first-paint'] > 0 && pg.fcp > 0 && pg.marks['is2-ready'] > 0, 'marks, paint entry and CDP clock present');
    const fpMs = Math.max(pg.marks['is2-first-paint'], pg.fcp), fpWall = pg.origin + fpMs, readyWall = pg.origin + pg.marks['is2-ready'], wall = (t) => t * 1000 + offset;
    const list = [...reqs.values()], finished = list.filter((r) => r.end !== undefined && !r.failed);
    const before = finished.filter((r) => wall(r.end) <= fpWall), byReady = finished.filter((r) => wall(r.end) <= readyWall);
    const inflight = list.filter((r) => wall(r.start) <= fpWall && !(r.end !== undefined && wall(r.end) <= fpWall));
    const sum = (rs) => rs.reduce((n, r) => n + r.bytes, 0), took = (r) => (r.end - r.start) * 1000;
    // Network throttling in effect: the document waited at least the latency; the largest response of the run took at least the
    // time its bytes (as the server sent them) need at the emulated bandwidth, plus the latency.
    const doc = list.find((r) => r.url === srv.base + '#/' || r.url === srv.base);
    assert.ok(doc && doc.end !== undefined && took(doc) >= NET.latency, `network throttling is not in effect: the document took ${doc && doc.end !== undefined ? took(doc).toFixed(0) : '?'} ms, under the emulated latency ${NET.latency} ms`);
    const big = finished.filter((r) => srv.sent.has(nameOf(r.url) || 'index.html')).map((r) => ({ r, size: srv.sent.get(nameOf(r.url) || 'index.html') })).sort((a, b) => b.size - a.size)[0];
    const floor = NET.latency + big.size / NET.downloadThroughput * 1000;
    assert.ok(took(big.r) >= floor, `network throttling is not in effect: ${nameOf(big.r.url)} (${kb(big.size)} KB) took ${took(big.r).toFixed(0)} ms, under the ${floor.toFixed(0)} ms the emulated ${NET.downloadThroughput * 8 / 1e6} Mbps and ${NET.latency} ms need`);
    const out = { ms: Math.round(fpMs), fcp: Math.round(pg.fcp), shell: Math.round(pg.marks['is2-shell-render']), first: sum(before), inflight: inflight.map((r) => nameOf(r.url)),
      ready: Math.round(pg.marks['is2-ready']), total: sum(byReady), all: sum(finished), nFirst: before.length, nReady: byReady.length, nAll: finished.length,
      cpu: cpuSet / cpuBase, cpuPage: cpuPage / cpuBase, doc: took(doc), probe: nameOf(big.r.url), probeKb: kb(big.size), probeMs: took(big.r), probeFloor: floor };
    // Structure at the first-paint moment.
    const s = pg.snap;
    assert.ok(s, 'snapshot taken at is2-first-paint');
    assert.deepEqual([s.search, s.menu, s.tabs], [true, 8, 5], 'the search box, the header menu and the phone tabs are drawn without the layer');
    assert.equal(s.chip, '연결 전', 'the device chip says 연결 전 before IS2.ready');
    assert.equal(s.notice, false, 'no loader failure notice while loading');
    assert.equal(s.state, 'WAITING', 'the loader waits for the first paint');
    assert.deepEqual(s.oldGlobals, [], 'no old module ran before the first paint');
    assert.deepEqual(s.facades, [true, true, true, true], 'IS2 facades answer IS2.NOT_READY');
    assert.deepEqual(s.scripts, FIRST, 'only index.html\'s scripts were in the page');
    if (process.env.FIRST_PAINT_DEBUG) console.log(JSON.stringify({ marks: pg.marks, fcp: pg.fcp, origin: pg.origin, reqs: list.map((r) => [nameOf(r.url), Math.round(wall(r.start) - pg.origin), r.end === undefined ? null : Math.round(wall(r.end) - pg.origin), r.bytes]) }));
    // The snapshot above is the exact proof (the loader still waited and had inserted nothing at is2-first-paint); the network
    // log agrees up to the shell's render (a clock-free margin: CDP and page clocks are only aligned to about a millisecond).
    const early = list.filter((r) => wall(r.start) <= pg.origin + pg.marks['is2-shell-render'] && LOAD.includes(nameOf(r.url))).map((r) => nameOf(r.url));
    assert.deepEqual(early, [], 'no LOAD_ORDER file was requested before the shell was drawn');
    assert.equal(pg.chip, '로그인 안 함 · 이 기기 기준', 'the chip follows the layer once it is loaded');
    assert.deepEqual(list.filter((r) => !r.url.startsWith(srv.origin)).map((r) => r.url), [], 'no request leaves the origin');
    assert.deepEqual(errors, [], 'no console error');
    console.log(`FIRST_PAINT_RUN ${run} ms=${out.ms} fcp_ms=${out.fcp} shell_ms=${out.shell} first_kb=${kb(out.first)} first_requests=${out.nFirst} inflight=${out.inflight.length}(${out.inflight.join(',')}) ready_ms=${out.ready} total_kb=${kb(out.total)} ready_requests=${out.nReady} all_kb=${kb(out.all)} all_requests=${out.nAll}`
      + ` cpu_ratio=${out.cpu.toFixed(2)}/${out.cpuPage.toFixed(2)} doc_ms=${out.doc.toFixed(0)} probe=${out.probe}:${out.probeKb}KB:${out.probeMs.toFixed(0)}ms>=${out.probeFloor.toFixed(0)}ms`);
    return out;
  } finally { await context.close(); }
}

// ---------------------------------------------------------------- contract helpers (no throttling)
async function open(browser, srv) {
  const context = await browser.newContext({ viewport: VIEWPORT });
  await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
  const page = await context.newPage(), seen = { errors: [], outside: [] };
  page.on('console', (m) => { if (m.type() === 'error') seen.errors.push({ text: m.text(), url: m.location() && m.location().url }); });
  page.on('pageerror', (e) => seen.errors.push({ text: String(e), url: null }));
  page.on('request', (r) => { if (!r.url().startsWith(srv.origin)) seen.outside.push(r.url()); });
  // Not 'load': the window's load event also waits for the scripts the loader inserts (a held one keeps it back).
  await page.goto(srv.base + '#/', { waitUntil: 'domcontentloaded' }); await page.locator('main[data-route]').waitFor();
  return { context, page, seen };
}
// A test-only button (one at a time, fixed at the top) whose click handler calls one layer action with its event; the returned
// function clicks it, removes it and gives the outcome.
async function button(page, name, call) {
  await page.evaluate(([n, c]) => {
    const b = document.createElement('button'); b.type = 'button'; b.dataset.testAction = n; b.textContent = 'test ' + n;
    for (const [k, v] of [['position', 'fixed'], ['top', '0'], ['left', '0'], ['z-index', '2147483647']]) b.style.setProperty(k, v);
    b.addEventListener('click', (e) => { const I = window.IS2, prefs = { version: 1, interests: [], groups: [] }; window.__out = window.__out || {};
      try { const v = c === 'savePrefs' ? I.store.savePrefs(e, prefs) : I.prices.prepare(e); window.__out[n] = Promise.resolve(v).then(() => 'OK', (err) => String(err && err.message)); }
      catch (err) { window.__out[n] = Promise.resolve(String(err && err.message)); } });
    document.body.appendChild(b);
  }, [name, call]);
  return async () => { await page.locator('[data-test-action="' + name + '"]').click(); const v = await page.evaluate((n) => window.__out[n], name); await page.evaluate((n) => document.querySelector('[data-test-action="' + n + '"]').remove(), name); return v; };
}
async function quiet(page, seen, label, allowed = []) {
  assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
  assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
  assert.deepEqual(seen.errors.filter((e) => !allowed.some((f) => f(e))).map((e) => e.text), [], label + ': no console error but the provoked ones');
  assert.deepEqual(await site.storage(page).then((s) => [s.local, s.session, s.idb]), [0, 0, 0], label + ': nothing stored');
}

async function contractHold(browser, srv) {
  phase = 'contract hold';
  const held = srv.hold(LOAD[0]);
  const { context, page, seen } = await open(browser, srv);
  try {
    await held.seen;
    const pre = await page.evaluate(() => {
      const I = window.IS2, NR = I.NOT_READY; window.__f = { data: I.data, prices: I.prices, store: I.store, qgv: I.qgv, engines: I.engines }; window.__log = []; window.__sub = 0;
      window.__count = I.store.marketQuotes.count().then((v) => { window.__log.push('count ' + v); return v; });
      I.ready.then(() => window.__log.push('ready'));
      I.qgv.subscribe(() => { window.__sub++; });
      const ac = new AbortController(); I.qgv.subscribe(() => { window.__sub += 100; }, { signal: ac.signal }); ac.abort();
      return { state: I.loadState(), chip: document.querySelector('[data-device-chip]').textContent, globals: typeof window.QgvScores,
        getters: [I.prices.status(), I.data.FILES, I.qgv.rankLabel('DEVICE_TEMPORARY'), I.store.prefs(), I.engines.target.state(), I.prices.universeView.prices(), typeof I.store.marketQuotes.clear === 'function'].map((x) => x === NR || x),
        marker: NR, log: [...window.__log] };
    });
    assert.deepEqual(pre.marker, { state: 'NOT_READY', reason: 'LAYER_NOT_READY' });
    assert.deepEqual([pre.state, pre.chip, pre.globals], ['LOADING', '연결 전', 'undefined'], 'held: the layer is not there and the chip says 연결 전');
    assert.deepEqual(pre.getters, [true, true, true, true, true, true, true], 'getters and values answer IS2.NOT_READY');
    assert.deepEqual(pre.log, [], 'a promise method waits for IS2.ready');
    assert.equal(await (await button(page, 'save', 'savePrefs'))(), 'LAYER_NOT_READY', 'a write on a real click before ready: LAYER_NOT_READY');
    assert.equal(await (await button(page, 'prepare', 'prepare'))(), 'LAYER_NOT_READY', 'a sign-in on a real click before ready: LAYER_NOT_READY (no GIS request)');
    held.release();
    assert.equal(await page.evaluate(() => window.IS2.ready.then(() => window.IS2.loadState())), 'READY');
    await page.evaluate(() => window.__count);
    const post = await page.evaluate(() => {
      const I = window.IS2, F = window.__f; I.qgv.setProfile({ preset: null, gate: null });
      return { log: [...window.__log], sub: window.__sub, chip: document.querySelector('[data-device-chip]').textContent, notice: !!document.querySelector('[data-load-failed]'), replaced: Object.keys(F).every((k) => I[k] !== F[k]),
        rank: F.qgv.rankLabel('DEVICE_TEMPORARY'), connected: F.prices.status().google.connected, files: Array.isArray(F.data.FILES) && F.data.FILES.includes('sec-qgv2.json'),
        nested: F.engines.target.ruleBDue === I.engines.target.ruleBDue ? 'same' : typeof F.engines.target.ruleBDue(), scripts: [...document.scripts].map((s) => s.getAttribute('src')) };
    });
    assert.deepEqual(post.log, ['ready', 'count 0'], 'the promise method ran on the layer after ready');
    assert.equal(post.sub, 1, 'the subscription made before ready was attached; the aborted one was not');
    assert.equal(post.chip, '로그인 안 함 · 이 기기 기준');
    assert.equal(post.notice, false, 'no failure notice once the layer is ready');
    assert.equal(post.replaced, true, 'the layer files replaced the facades on IS2');
    assert.deepEqual([post.rank, post.connected, post.files, post.nested], ['임시 V 기준 순위 · 공식 순위 아님', false, true, 'boolean'], 'a kept facade forwards to the layer');
    assert.deepEqual(post.scripts, R.scripts(), 'index.html\'s scripts, then LOAD_ORDER, in order');
    await quiet(page, seen, 'hold');
  } finally { await context.close(); }
}

// The shell's loader failure notice as drawn: its text, its button, in view at 390×844, and the chip.
async function notice(page) {
  await page.locator('[data-load-failed]').waitFor();
  return page.evaluate(() => {
    const n = document.querySelectorAll('[data-load-failed]'), el = n[0], b = el.querySelector('button[data-reload]'), box = el.getBoundingClientRect();
    return { count: n.length, role: el.getAttribute('role'), text: el.querySelector('span').textContent, button: b ? [b.type, b.textContent] : null, all: el.textContent,
      inView: box.top >= 0 && box.bottom <= window.innerHeight && box.width > 0 && box.height > 0, beforeMain: el.nextElementSibling === document.querySelector('main'),
      chip: document.querySelector('[data-device-chip]').textContent };
  });
}
async function contractFailure(browser, srv, file, answer, provoked, followers = [], reload = false) {
  phase = 'contract failure ' + file;
  srv.override(file, answer);
  const { context, page, seen } = await open(browser, srv);
  try {
    const r = await page.evaluate(async () => {
      const I = window.IS2, message = await I.ready.then(() => 'OK', (e) => e.message);
      return { message, state: I.loadState(), chip: document.querySelector('[data-device-chip]').textContent, value: I.data.FILES === I.LOAD_FAILED, getter: I.prices.status() === I.LOAD_FAILED,
        page: await I.qgv.page().then(() => 'OK', (e) => e.message), sub: typeof I.store.subscribe(() => {}), marker: I.LOAD_FAILED };
    });
    assert.deepEqual(r, { message: 'LOADER_FAILED ' + file, state: 'FAILED', chip: '연결 실패', value: true, getter: true, page: 'LOADER_FAILED ' + file, sub: 'function',
      marker: { state: 'NOT_READY', reason: 'LOADER_FAILED' } }, file + ': IS2.ready rejects, the facades are back and refuse, the chip says 연결 실패');
    const want = { count: 1, role: 'alert', text: FAILED_NOTE, button: ['button', '새로고침'], all: FAILED_NOTE + '새로고침', inView: true, beforeMain: true, chip: '연결 실패' };
    assert.deepEqual(await notice(page), want, file + ': the shell shows the fixed failure notice (no file name) with a reload button, in view');
    const save = await button(page, 'save', 'savePrefs');
    assert.equal(await save(), 'LOADER_FAILED ' + file, 'an action on a real click gets the failure');
    // A later route draws the notice and the chip too.
    await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route="qgv"]').waitFor();
    assert.deepEqual(await notice(page), want, file + ': the notice stays on the next route');
    await quiet(page, seen, file, [provoked, ...followers]);
    if (reload) {
      // The button only reloads: from the click on, the first request is the page's own navigation; the reloaded page fails
      // the same way and shows the notice again.
      const after = [], onRequest = (q) => after.push({ url: q.url(), navigation: q.isNavigationRequest(), type: q.resourceType() });
      page.on('request', onRequest);
      await Promise.all([page.waitForRequest((q) => q.isNavigationRequest()), page.locator('[data-reload]').click()]);
      await page.waitForFunction(() => window.IS2 && typeof window.IS2.loadState === 'function' && window.IS2.loadState() === 'FAILED');
      page.off('request', onRequest);
      assert.ok(after.length > 0, file + ': the reload button reloaded the page');
      assert.deepEqual([after[0].navigation, after[0].type, new URL(after[0].url).pathname], [true, 'document', '/'], file + ': the reload button makes no request of its own; the first one is the page reloading: ' + JSON.stringify(after.slice(0, 3)));
      assert.ok(after.some((q) => nameOf(q.url) === file), file + ': the reload asked for every file again');
      assert.deepEqual(await notice(page), want, file + ': after the reload the page fails again and shows the notice');
      await quiet(page, seen, file + ' after reload', [provoked, ...followers]);
    }
    assert.ok(seen.errors.some(provoked), file + ': the provoked error was seen');
  } finally { srv.override(file, null); await context.close(); }
}

(async () => {
  const out = site.build(), srv = await serve(out);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    phase = 'build';
    assert.deepEqual(R.scripts(), [...FIRST, ...LOAD]);
    for (const name of [...FIRST, ...LOAD]) assert.ok(fs.existsSync(path.join(out, name)), name + ' built');
    const runs = [];
    for (let i = 1; i <= RUNS; i++) runs.push(await measure(browser, srv, i));
    const m = { ms: median(runs.map((r) => r.ms)), first: median(runs.map((r) => r.first)), ready: median(runs.map((r) => r.ready)), total: median(runs.map((r) => r.total)), all: median(runs.map((r) => r.all)) };
    console.log(`FIRST_PAINT ms=${m.ms} first_kb=${kb(m.first)} ready_ms=${m.ready} total_kb=${kb(m.total)}`);
    console.log(`FIRST_PAINT_CONTEXT encoding=${GZIP ? 'gzip' : 'identity'} runs=${RUNS} viewport=${VIEWPORT.width}x${VIEWPORT.height} dpr=1 latency_ms=${NET.latency} down_mbps=1.6 up_kbps=750 cpu=${CPU}`
      + ` measured: cpu_ratio_median=${median(runs.map((r) => r.cpu)).toFixed(2)} cpu_ratio_after_load_median=${median(runs.map((r) => r.cpuPage)).toFixed(2)} doc_ms_median=${median(runs.map((r) => r.doc)).toFixed(0)}`
      + ` probe_ms_median=${median(runs.map((r) => r.probeMs)).toFixed(0)}(floor ${runs[0].probeFloor.toFixed(0)}, ${runs[0].probe})`
      + ` model: loopback http/1.1, no dns/tcp/tls setup (a real first visit adds about 3 x ${NET.latency} ms) all_kb_median=${kb(m.all)} targets: ms<=${LIMIT_MS} first_kb<=${LIMIT_BYTES / 1024}`);
    phase = 'targets';
    assert.ok(m.ms <= LIMIT_MS, `first screen median ${m.ms} ms is over ${LIMIT_MS} ms`);
    assert.ok(m.first <= LIMIT_BYTES, `first transfer median ${kb(m.first)} KB is over ${LIMIT_BYTES / 1024} KB`);
    await contractHold(browser, srv);
    // engines.js then refuses a layer without the QGV accessor / the store (LAYER_MISSING): it follows from the provoked failure.
    await contractFailure(browser, srv, 'qgv.js', { status: 404 }, (e) => /status of 404/.test(e.text) && /\/qgv\.js$/.test(e.url || ''), [(e) => e.text === 'Error: LAYER_MISSING'], true);
    await contractFailure(browser, srv, 'store.js', { status: 200, body: "throw Error('SYNTHETIC_LOAD_ERROR');" }, (e) => /SYNTHETIC_LOAD_ERROR/.test(e.text), [(e) => e.text === 'Error: LAYER_MISSING']);
    console.log('web app first paint: throttling proven in every run, shell first without the layer, targets met on the median of ' + RUNS + ' throttled runs, loader facades / ready / failures / failure notice ok');
  } finally { await browser.close(); await srv.close(); fs.rmSync(out, { recursive: true, force: true }); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
