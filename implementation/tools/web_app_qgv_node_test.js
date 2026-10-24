'use strict';
// New frontend P1 · action gate, public data and the QGV accessor (web_app/action.js, data.js, qgv.js).
//  - action: only a trusted click / Enter-Space being dispatched runs fn (a submit, a synthetic event, a plain object or a forged
//    event claiming isTrusted, and a kept event replayed after its dispatch are refused; a nested run of the same event while its
//    action is in flight passes); cancel leaves the gate at once; private destinations only for the kind in flight, Sheets only
//    for saved spreadsheets and a values GET for a read (a Request's own method counts); storage writes only inside a writing
//    action; IndexedDB never created by a read; views keep the real window as `this` for its functions (DataRefresh.proxy rule)
//    and refuse writes to window globals.
//  - data: one strict request function (fixed file list, same origin, no credentials / redirect / referrer, status kept, a body
//    over 2 MiB handed on empty so it is an invalid file), the old readers' validation through the DataRefresh core: every
//    sec_qgv2 vector keeps SecQgv2.validate's verdict on the page path and in peek; a refresh that applies dispatches
//    'public-data-updated' on the window and commits the new set; a re-judgement without network restates rows (fixed clock,
//    no wall time); a failed static read is read again by the next call; READER_MISSING instead of a lighter path.
//  - qgv: the page rows are an exact projection of QgvScores.pageResult computed with the same score view (critique #10: no
//    vector injected into the accessor); no price or price-derived field leaves; a null value always has its reason; V source
//    always DEVICE_TEMPORARY with #391's words on a device page, even if the switch changes while it is computed; v_factors =
//    TargetV1Builder.vFactors; personal preview never official and computed as the 2.2 personal call (its own gate, no preset).
// Synthetic data only (tools/qgv_v2_fixture.js, tests/fixtures); sentinel prices are made up.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');

const QGV2 = 'sec-qgv2.json';
const VECTORS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/sec_qgv2_vectors_v1.json'), 'utf8'));
const CUSTOM = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_v2_custom_vectors_v1.json'), 'utf8'));
// The public identity catalog (19 TARGET), exactly as the build writes actual-catalog.json.
const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
// #391 TargetV1Builder.V_SOURCE (origin/claude/target-v1-temp-v-label target-v1-builder.js:302), byte for byte.
const V391 = { id: 'DEVICE_TEMPORARY', ko: '임시 V', note: '기기 시세로 계산 · 중앙 V 미게시' };
// Synthetic sentinel prices of the Universe read (made-up decimals that cannot be a score).
const SENTINEL = (i) => 17 + i + 0.0731946;
const BASIS = { source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_sentinel', acquired_at: '2026-10-18T09:00:00.000Z', currency: 'USD', price_time: null };
const PRICE_KEYS = new Set(['quotes', 'quote_meta', 'month_closes', 'detail', 'reference_range', 'price', 'prices', 'market_cap', 'marketcap', 'ev', 'enterprise_value', 'ebit_yield', 'fcf_yield', 'implied_growth', 'currency_price']);
const fresh = (name) => { delete require.cache[require.resolve(R.newPath(name))]; return R.requireNew(name); };
// A fixed clock for the old modules (Date.now and new Date()): freshness boundaries without wall time.
function fixedClock(start) {
  const Real = Date; let now = start;
  class Fixed extends Real { constructor(...a) { super(...(a.length ? a : [now])); } static now() { return now; } }
  globalThis.Date = Fixed;
  return { set: (t) => { now = t; }, restore: () => { globalThis.Date = Real; } };
}

function universeView(payload = F.strictPayload()) {
  const prices = new Map(); let i = 0;
  for (const [code, r] of Object.entries(payload.records)) if (r.state === 'LIVE' && code !== 'NASDAQ:MSFT') prices.set(code, { price: SENTINEL(i++), currency: 'USD' });
  prices.set('NASDAQ:NVDA', { price: SENTINEL(i++), currency: 'USD' });
  return { view: { prices: () => prices, priceBasis: () => BASIS, readStatus: () => null }, sentinels: [...prices.values()].map((q) => String(q.price)) };
}
// universe-codes.json as the build writes it (the fixed 504-code list).
const CODES = { schema: 'universe-codes/1', codes: JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/universe/universe_codes_v1.json'), 'utf8')) };
// One page environment: a browser-like window, fresh old modules (index.html order) and fresh P1 modules.
function env({ files = {}, omit = [], prices = null, old } = {}) {
  const table = { [QGV2]: { json: F.strictPayload() }, 'actual-catalog.json': { json: CATALOG }, 'universe-codes.json': { json: CODES }, ...files };
  const win = R.nodeWindow({ files: typeof files === 'function' ? files : (name) => table[name] });
  const mods = R.loadOld(win, old);
  for (const g of omit) { delete win[g]; delete globalThis[g]; }
  const action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action });
  const qgv = fresh('qgv.js').create({ win, data, action, prices });
  return { win, mods, action, data, qgv, table };
}
// Records every QgvScores.pageResult call the accessor makes (same function, same arguments, same result).
function spy(e) { const QS = e.mods.QgvScores, calls = []; e.win.QgvScores = Object.freeze({ ...QS, pageResult: (view, opts) => { const p = QS.pageResult(view, opts); calls.push({ view, opts, p }); return p; } }); return calls; }
function keysDeep(v, out = new Set()) { if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) { if (!Array.isArray(v)) out.add(k); keysDeep(x, out); } return out; }
const finiteOrNull = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null);

// ---------------------------------------------------------------- action gate
test('action.run: only a trusted gesture of the window being dispatched runs fn, in the same tick; the kind stays in flight until fn settles', async () => {
  const win = R.nodeWindow(), A = fresh('action.js').create({ win });
  let ran = 0;
  // A submit is not a gesture: the browser marks form.requestSubmit() and a script's submitter.click() submits as trusted.
  const forgedProto = Object.create(win.Event.prototype, { isTrusted: { value: true }, type: { value: 'click' } });
  const forgedProxy = new Proxy(new win.Event('click'), { get: (t, k) => (k === 'isTrusted' ? true : Reflect.get(t, k)) });
  assert.ok(forgedProto instanceof win.Event && forgedProxy instanceof win.Event && forgedProxy.isTrusted === true, 'both forgeries pass instanceof and claim isTrusted');
  for (const e of [undefined, null, { type: 'click', isTrusted: true }, new Event('click'), new win.Event('click'), forgedProto, forgedProxy, win.trusted('submit'), win.trusted('mouseover'), win.trusted('keydown', { key: 'a' })])
    assert.throws(() => A.run(e, 'WRITE', () => { ran++; }), /CLICK_REQUIRED/);
  assert.throws(() => A.run(win.trusted('click'), 'NOPE', () => {}), /ACTION_KIND_UNKNOWN/);
  assert.equal(ran, 0);
  let inside = null; const out = A.run(win.trusted('click'), 'WRITE', (signal) => { inside = [A.active(), A.active('WRITE'), A.writing(), signal.aborted]; return 7; });
  assert.deepEqual(inside, [true, true, true, false], 'fn ran synchronously inside the click');
  assert.equal(out, 7); assert.equal(A.active(), false);
  for (const e of [win.trusted('keydown', { key: 'Enter' }), win.trusted('keydown', { key: ' ' })]) assert.equal(A.run(e, 'LOGIN', () => 1), 1);
  let release; const p = A.run(win.trusted('click'), 'SYNC', () => new Promise((r) => { release = r; }));
  assert.equal(A.active('SYNC'), true);
  // cancel leaves the gate at once, even while fn has not settled (a stalled step cannot keep it open).
  A.cancel('SYNC'); assert.equal(A.active('SYNC'), false, 'cancelled: out of the gate before fn settles'); release('done'); assert.equal(await p, 'done'); assert.equal(A.active(), false);
  assert.throws(() => A.run(win.trusted('click'), 'WRITE', () => { throw Error('X'); }), /X/); assert.equal(A.active(), false, 'a throwing fn leaves the gate');
  // A kept event after its dispatch: refused, whatever kind it is replayed for.
  const kept = win.trusted('click'); A.run(kept, 'WRITE', () => 1); win.ended(kept);
  for (const kind of ['WRITE', 'UNIVERSE_READ', 'LOGIN']) assert.throws(() => A.run(kept, kind, () => { ran++; }), /CLICK_REQUIRED/, kind);
  const later = win.trusted('click'); await new Promise((r) => setImmediate(r));
  assert.throws(() => A.run(later, 'WRITE', () => { ran++; }), /CLICK_REQUIRED/, 'the dispatch ended with its task');
  assert.equal(ran, 0);
  // Nested: while an action started from the event is in flight, the same event may start the next step after awaits.
  const e = win.trusted('click'); let nested = null;
  const outer = A.run(e, 'SYNC', async () => { await new Promise((r) => setImmediate(r)); nested = await A.run(e, 'SYNC', async () => A.active('SYNC')); return 'outer'; });
  assert.equal(await outer, 'outer'); assert.equal(nested, true, 'the nested run of the same event passed after its dispatch ended');
  assert.throws(() => A.run(e, 'SYNC', () => 1), /CLICK_REQUIRED/, 'once the outer action settled, the event is a replay');
  const other = win.trusted('click'); A.run(other, 'WRITE', () => 1);
  const held = A.run(win.trusted('click'), 'SYNC', () => new Promise(() => {})); void held; win.ended(other);
  assert.throws(() => A.run(other, 'SYNC', () => 1), /CLICK_REQUIRED/, 'another event in flight does not lend its permission'); A.cancel('SYNC');
  // Transient activation, where the browser reports it.
  win.navigator = { userActivation: { isActive: false } };
  assert.throws(() => A.run(win.trusted('click'), 'WRITE', () => 1), /CLICK_REQUIRED/, 'no user activation');
  win.navigator.userActivation.isActive = true; assert.equal(A.run(win.trusted('click'), 'WRITE', () => 2), 2);
});

test('action.guard: each kind reaches only its private destinations; Sheets only the saved spreadsheets; the public refresh opens none; blocked() counts refusals', async () => {
  const win = R.nodeWindow(); R.loadOld(win, ['app-config.js']); const A = fresh('action.js').create({ win });
  const W = win.InvestmentAppConfig.privateHistoryWorkerOrigin, S = 'https://sheets.googleapis.com/v4/spreadsheets/';
  const dest = { values: [S + 'x/values/A1', {}], append: [S + 'x/values/A1:append', { method: 'POST' }],
    oauth: ['https://oauth2.googleapis.com/token', {}], history: [W + '/history?symbol=SPY&range=1y', {}], worker: [W + '/quote', {}] };
  assert.equal(A.classify('sec-qgv2.json'), 'PUBLIC'); assert.equal(A.guard('sec-qgv2.json'), 'PUBLIC');
  assert.deepEqual(Object.fromEntries(Object.entries(dest).map(([k, d]) => [k, A.classify(...d)])), { values: 'SHEETS_READ', append: 'SHEETS_WRITE', oauth: 'OAUTH', history: 'WORKER_HISTORY', worker: 'WORKER' });
  // A read is a values GET; the tab list and a create are not; a Request object keeps its own method.
  assert.deepEqual([A.classify(S + 'x?fields=sheets'), A.classify(S.slice(0, -1) + '?fields=spreadsheetId', { method: 'POST' }), A.classify(S + 'x/values/A1', { method: 'put' })], ['SHEETS_WRITE', 'SHEETS_WRITE', 'SHEETS_WRITE']);
  const post = new Request(S + 'x/values/A1:append', { method: 'POST', body: '{}' });
  assert.equal(A.classify(post), 'SHEETS_WRITE'); assert.equal(A.classify(new Request(S + 'x/values/A1')), 'SHEETS_READ'); assert.equal(A.classify(new URL(S + 'x/values/A1')), 'SHEETS_READ');
  for (const d of Object.values(dest)) assert.throws(() => A.guard(...d), /CLICK_REQUIRED/);
  assert.equal(A.blocked(), 5);
  assert.throws(() => A.guard('https://example.invalid/x'), /DESTINATION_UNKNOWN/); assert.equal(A.blocked(), 6);
  const allowed = { PUBLIC_REFRESH: [], LOGIN: ['oauth'], UNIVERSE_READ: ['values'], HISTORY: ['history'], SYNC: ['values', 'append', 'history', 'worker'], WRITE: [] };
  for (const [kind, ok] of Object.entries(allowed)) {
    const seen = A.run(win.trusted('click'), kind, () => Object.keys(dest).filter((k) => { try { A.guard(...dest[k]); return true; } catch (e) { assert.match(e.message, /CLICK_REQUIRED/); return false; } }));
    assert.deepEqual(seen, ok, kind);
  }
  // Inside a read click: a POST as a Request object or a non-string target is refused, and only saved spreadsheets are reached.
  const before = A.blocked(), ids = () => ['x'];
  const inRead = A.run(win.trusted('click'), 'UNIVERSE_READ', () => Object.fromEntries(Object.entries({
    request: () => A.guard(post, undefined, { sheets: ids }), url: () => A.guard(new URL(S + 'x/values/A1'), {}, { sheets: ids }), saved: () => A.guard(S + 'x/values/A1', {}, { sheets: ids }),
    other: () => A.guard(S + 'someone_elses_sheet/values/A1', {}, { sheets: ids }), none: () => A.guard(S + 'x/values/A1', {}, { sheets: [] }) })
    .map(([k, f]) => { try { return [k, f()]; } catch (e) { return [k, e.message]; } })));
  assert.deepEqual(inRead, { request: 'DESTINATION_UNKNOWN', url: 'DESTINATION_UNKNOWN', saved: 'SHEETS_READ', other: 'DESTINATION_UNKNOWN', none: 'DESTINATION_UNKNOWN' });
  assert.equal(A.blocked() - before, 4);
  const create = A.run(win.trusted('click'), 'SYNC', () => { try { return A.guard(S.slice(0, -1) + '?fields=spreadsheetId', { method: 'POST' }, { sheets: ids }); } catch (e) { return e.message; } });
  assert.equal(create, 'DESTINATION_UNKNOWN', 'no new spreadsheet through the price view');
  assert.equal(A.active(), false);
});

test('action storage: writes only inside a writing action (ACTION_REQUIRED, storage unchanged); IndexedDB never created by a read', async () => {
  const win = R.nodeWindow(), store = new Map(), opened = [];
  const local = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k), clear: () => store.clear(), key: (i) => [...store.keys()][i] || null, get length() { return store.size; } };
  const dbs = ['investment-device-actual-v1'];
  win.localStorage = local; win.indexedDB = { open: (n, v) => { opened.push(n); return { n, v }; }, deleteDatabase: (n) => ({ n }), databases: async () => dbs.map((name) => ({ name, version: 1 })), cmp: () => 0 };
  const A = fresh('action.js').create({ win }), S = A.gatedStorage(() => win.localStorage);
  store.set('k', 'v');
  assert.equal(S.getItem('k'), 'v'); assert.equal(S.length, 1); assert.equal(S.key(0), 'k');
  for (const f of [() => S.setItem('k', 'x'), () => S.removeItem('k'), () => S.clear()]) assert.throws(f, /ACTION_REQUIRED/);
  assert.equal(store.get('k'), 'v'); assert.equal(A.blocked(), 3);
  assert.throws(() => A.run(win.trusted('click'), 'PUBLIC_REFRESH', () => S.setItem('k', 'x')), /ACTION_REQUIRED/, 'the public refresh writes nothing');
  A.run(win.trusted('click'), 'WRITE', () => S.setItem('k', 'w')); assert.equal(store.get('k'), 'w');
  const D = A.gatedIndexedDB(() => win.indexedDB), RO = A.gatedIndexedDB(() => win.indexedDB, { readOnly: true });
  assert.throws(() => D.open('investment-device-actual-v1', 1), /DEVICE_STORE_NOT_OPENED/, 'unknown until stores() lists it');
  assert.deepEqual(await A.stores(), { supported: true, available: true, names: ['investment-device-actual-v1'] });
  assert.deepEqual(D.open('investment-device-actual-v1', 1), { n: 'investment-device-actual-v1', v: 1 });
  assert.throws(() => D.open('other', 1), /DEVICE_STORE_NOT_OPENED/);
  assert.throws(() => A.run(win.trusted('click'), 'UNIVERSE_READ', () => RO.open('other', 1)), /DEVICE_STORE_NOT_OPENED/, 'the score path never creates a database');
  A.run(win.trusted('click'), 'WRITE', () => D.open('other', 1));
  assert.deepEqual(opened, ['investment-device-actual-v1', 'other']);
  assert.throws(() => D.deleteDatabase('other'), /ACTION_REQUIRED/);
  win.indexedDB = { open: () => ({}) };// no databases(): only what this session already opened stays known; nothing new opens outside an action
  assert.deepEqual(await A.stores(), { supported: false, available: true, names: ['investment-device-actual-v1', 'other'] });
  assert.throws(() => D.open('third', 1), /DEVICE_STORE_NOT_OPENED/);
});

test('action.view: window functions keep the real window as `this`; storage gated; window globals never written; fetch required', () => {
  const win = R.nodeWindow(), A = fresh('action.js').create({ win }), fetch = async () => 'x';
  assert.throws(() => A.view({}), /VIEW_FETCH_REQUIRED/);
  const plain = new Proxy(win, {});
  assert.throws(() => plain.dispatchEvent(new CustomEvent('t')), /Illegal invocation/, 'the fake window refuses an unbound call, as a browser does');
  const v = A.view({ fetch, PriceStore: 'facade' }); let got = 0;
  v.addEventListener('t', () => { got++; }); assert.equal(v.dispatchEvent(new CustomEvent('t')), true); assert.equal(got, 1);
  assert.equal(v.fetch, fetch); assert.equal(v.PriceStore, 'facade'); assert.equal(v.CustomEvent, CustomEvent);
  assert.throws(() => { 'use strict'; v.PriceStore = {}; }, TypeError); assert.equal(v.PriceStore, 'facade');
  assert.throws(() => { v.Anything = 1; }, TypeError); assert.equal('Anything' in win, false);
  assert.throws(() => v.localStorage.setItem('a', 'b'), /ACTION_REQUIRED/);
});

// ---------------------------------------------------------------- data
test('data: fixed file list = the readers own names; strict request options; nothing read at create; READER_MISSING closes', async () => {
  const { win, mods, data } = env({ files: { 'entities.json': { body: 'x'.repeat(2 * 1024 * 1024 + 1) } } });
  assert.equal(win.requests.length, 0, 'creating the layer reads nothing');
  const D = mods.DataRefresh, expect = new Set([...Object.keys(mods.PublicScreens.FILES), mods.ClassificationScreens.FILE, mods.Qgv2Inputs.FILE, 'sec-public-inputs.json', 'dart-financials.json', mods.MacroEvidence.FILENAME,
    ...Object.values(D.LISTS), mods.SecUniverseShares.FILENAME, 'actual-catalog.json', 'entities.json', mods.EntitySearch.NAMES_FILE, mods.InvestmentAppConfig.universeCodeCatalogURL, mods.DeviceValuation.FILE, mods.ForwardValidation.FILENAME]);
  assert.deepEqual(new Set(data.FILES), expect); assert.equal(data.EVENT, D.EVENT); assert.equal(data.MAX_BYTES, 2 * 1024 * 1024);
  await assert.rejects(data.strictFetch('https://site.test/app/sec-qgv2.json'), /PUBLIC_FILE_UNKNOWN/);
  await assert.rejects(data.strictFetch('../sec-qgv2.json'), /PUBLIC_FILE_UNKNOWN/);
  await assert.rejects(data.strictFetch('data.json'), /PUBLIC_FILE_UNKNOWN/);
  await assert.rejects(data.strictFetch(QGV2, { method: 'POST' }), /PUBLIC_FILE_METHOD/);
  const big = await data.strictFetch('entities.json'); assert.equal(big.status, 200); assert.equal(await big.text(), '', 'over 2 MiB: an empty body with the real status (an invalid file, not a network failure)');
  assert.equal(await data.static('entities.json'), null); assert.equal(data.state('entities.json').state, 'FAILED'); assert.equal(data.state('entities.json').why, 'INVALID');
  const r404 = await data.strictFetch('macro-screen.json'); assert.equal(r404.status, 404, 'status kept (404 = not published)');
  const pub = await data.ready(); assert.equal(pub.generation, 1); assert.equal(data.ready(), data.ready());
  for (const r of win.requests) {
    assert.ok(data.FILES.includes(r.name), r.name);
    assert.deepEqual([r.init.method, r.init.credentials, r.init.redirect, r.init.referrerPolicy, r.init.mode], ['GET', 'omit', 'error', 'no-referrer', 'same-origin'], r.name);
    assert.ok(['no-store', 'no-cache'].includes(r.init.cache), r.name);
  }
  assert.equal(data.state(QGV2).state, 'OK'); assert.equal(data.state('macro-screen.json').state, 'NOT_PUBLISHED'); assert.match(data.state('macro-screen.json').text, /404/);
  assert.equal(data.state('news-signals.json').state, 'NOT_READ', 'lazy list not read yet');
  assert.equal(data.get(QGV2).count, 504 + Object.keys(mods.SecQgv2.TARGET_CIKS).length); assert.equal(data.get('macro-screen.json'), null);
  assert.throws(() => data.get('nope.json'), /PUBLIC_FILE_UNKNOWN/);
  const codes = await data.universe(); assert.deepEqual([...codes], CODES.codes); assert.ok(Object.isFrozen(codes)); assert.equal(data.state('universe-codes.json').state, 'OK');
  assert.equal(await data.universe(), codes, 'read once per page');
  for (const omit of [['PlaybookEngine'], ['SecQgv2']]) {
    const e = env({ omit }); await assert.rejects(e.data.ready(), /READER_MISSING/);
    assert.equal(e.data.state(QGV2).why, 'READER_MISSING'); assert.equal(e.win.requests.length, 0, 'no lighter path: nothing read');
    await assert.rejects(e.qgv.page(), /READER_MISSING/);
  }
});

test('sec_qgv2 vectors: the page path (DataRefresh → Qgv2Inputs → SecQgv2) and peek keep SecQgv2.validate verdicts (every case)', async () => {
  assert.equal(VECTORS.synthetic, true); assert.ok(VECTORS.cases.length >= 100);
  const base = F.strictPayload(), SQ = R.requireOld('sec-qgv2.js');
  const apply = (p, ops) => { for (const { path: keys, value } of ops) { let t = p; for (const k of keys.slice(0, -1)) t = t[k]; const last = keys[keys.length - 1]; if (JSON.stringify(value) === JSON.stringify(VECTORS.delete_marker)) delete t[last]; else t[last] = structuredClone(value); } return p; };
  const win = R.nodeWindow({ files: (name) => (name === QGV2 ? { body: current } : null) }); let current = '';
  R.loadOld(win); const action = fresh('action.js').create({ win });
  let valid = 0;
  for (const c of VECTORS.cases) {
    const p = apply(structuredClone(base), c.ops); current = JSON.stringify(p);
    let direct = true; try { SQ.validate(structuredClone(p)); } catch (_) { direct = false; }
    assert.equal(direct, c.valid, c.id + ' fixture verdict');
    R.loadOld(win, ['qgv2-inputs.js', 'data-refresh.js']);// a fresh generation store per case
    const data = fresh('data.js').create({ win, action });
    await data.ready();
    const s = data.state(QGV2);
    assert.equal(s.state === 'OK', c.valid, c.id + ' page path');
    if (c.valid) { valid++; assert.ok(data.get(QGV2) && data.get(QGV2).records, c.id); } else { assert.equal(s.state, 'FAILED', c.id); assert.ok(['INVALID', 'SCHEMA_NEWER'].includes(s.why), c.id); assert.equal(data.get(QGV2), null, c.id); }
    let peeked = true; try { const raw = await data.peek(QGV2); assert.deepEqual(raw, p, c.id + ' peek returns the raw validated JSON'); assert.ok(Object.isFrozen(raw.records)); } catch (e) { peeked = false; assert.match(e.message, /^SEC_QGV2_(INVALID|SCHEMA_NEWER)$/, c.id); }
    assert.equal(peeked, c.valid, c.id + ' peek');
  }
  assert.ok(valid >= 1 && valid < VECTORS.cases.length);
  await assert.rejects(fresh('data.js').create({ win, action }).peek('macro-screen.json'), /PEEK_UNSUPPORTED/);
});

test('data.refresh: trusted click only; APPLIED dispatches public-data-updated on the window and commits the new set; FAILED keeps it', async () => {
  const table = { [QGV2]: null, 'actual-catalog.json': { json: CATALOG } };
  const { win, data, qgv, mods } = env({ files: (name) => table[name] });
  await data.ready(); assert.equal(data.state(QGV2).state, 'NOT_PUBLISHED'); assert.equal(data.get(QGV2), null);
  assert.equal((await qgv.page()).state, 'NO_DATA'); assert.equal((await qgv.page()).reason, 'SEC_QGV2_NOT_PUBLISHED');
  assert.throws(() => data.refresh(new Event('click')), /CLICK_REQUIRED/); assert.throws(() => data.refresh({ type: 'click', isTrusted: true }), /CLICK_REQUIRED/);
  const onWindow = [], onData = []; win.addEventListener(mods.DataRefresh.EVENT, (e) => onWindow.push(e.detail)); data.subscribe((d) => onData.push([d.reason, data.get(QGV2)]));
  table[QGV2] = { json: F.strictPayload() };
  const before = win.requests.length;
  assert.equal(await data.refresh(win.trusted('click')), 'APPLIED');
  assert.equal(onWindow.length, 1, 'the bound dispatchEvent reached the window (critique #1)'); assert.equal(onWindow[0].reason, 'REFRESH'); assert.equal(onWindow[0].generation, 2);
  assert.ok(onWindow[0].changed.includes(QGV2));
  assert.equal(onData.length, 1); assert.ok(onData[0][1] && onData[0][1].records, 'subscribers see the committed set');
  assert.ok(win.requests.slice(before).every((r) => data.FILES.includes(r.name)));
  const inputs = data.get(QGV2); assert.equal(data.publication().generation, 2);
  assert.equal(win.timers.filter((t) => t.ms === 30000).length, 0, 'DataRefresh could not swap window.PriceStore (view refuses global writes)');
  const pg = await qgv.page(); assert.equal(pg.state, 'READY'); assert.equal(pg.generation, 2);
  table[QGV2] = { body: '{not json' };
  assert.equal(await data.refresh(win.trusted('click')), 'FAILED'); assert.equal(data.get(QGV2), inputs, 'all or nothing'); assert.equal(onWindow.length, 1);
  table[QGV2] = { json: F.strictPayload() };
  assert.equal(await data.refresh(win.trusted('click')), 'UNCHANGED'); assert.equal(data.get(QGV2), inputs);
  assert.equal(await qgv.page(), pg, 'same inputs, same shared page');
});

test('data re-judgement: no network, sec-qgv2 rows restated when their freshness boundary passes (timer, visibility, hashchange)', async () => {
  // Fixed clock one hour after the fixture's collection (2026-10-13T22:30Z, 14-day window); MMM's window ends one minute later.
  const p = F.strictPayload(), t0 = Date.parse(p.as_of) + 3600000, bound = t0 + 60000, at = (ms) => new Date(ms).toISOString().replace(/\.\d+Z$/, 'Z');
  p.records['NYSE:MMM'].acquired_at = at(bound - p.stale_after_seconds * 1000);
  const clock = fixedClock(t0);
  try {
    const { win, data } = env({ files: { [QGV2]: { json: p } } });
    await data.ready();
    assert.equal(data.get(QGV2).records['NYSE:MMM'].state, 'LIVE');
    const tick = win.timers.find((t) => t.ms === 60000); assert.ok(tick, 'a one-minute re-judgement timer');
    tick.fn(); await new Promise((r) => setImmediate(r));
    assert.equal(data.get(QGV2).records['NYSE:MMM'].state, 'LIVE', 'before the boundary nothing changes');
    clock.set(bound + 1000);
    const before = win.requests.length, seen = new Promise((r) => data.subscribe((d) => { if (d.reason === 'REJUDGE') r(d); }));
    tick.fn();
    const d = await seen;
    assert.ok(d.changed.includes(QGV2)); assert.equal(win.requests.length, before, 're-judged from the text already read');
    assert.equal(data.get(QGV2).records['NYSE:MMM'].state, 'STALE');
    win.dispatchEvent(new Event('hashchange')); win.document.dispatchEvent(new Event('visibilitychange'));
    assert.equal(win.requests.length, before);
  } finally { clock.restore(); }
});

test('data.static: a failed read is read again by the next call (state keeps the failure until then); the page says the catalog is missing', async () => {
  let offline = true; const table = { [QGV2]: { json: F.strictPayload() }, 'actual-catalog.json': { json: CATALOG }, 'universe-codes.json': { json: CODES } };
  const { win, data, qgv } = env({ files: (name) => (name === 'actual-catalog.json' && offline ? new TypeError('offline') : table[name]) });
  const asked = () => win.requests.filter((r) => r.name === 'actual-catalog.json').length;
  const a = await qgv.page();
  assert.equal(a.state, 'READY'); assert.deepEqual(a.identities, { state: 'NOT_AVAILABLE', reason: 'CATALOG_NOT_AVAILABLE', count: 0 }, 'no TARGET rows, and the page says why');
  assert.equal(qgv.rows(a, { scope: 'TARGET' }).length, 0); assert.notEqual(qgv.reasonText('CATALOG_NOT_AVAILABLE'), '계산 불가 (CATALOG_NOT_AVAILABLE)');
  assert.deepEqual([data.state('actual-catalog.json').state, data.state('actual-catalog.json').why], ['FAILED', 'NETWORK']);
  offline = false;
  const b = await qgv.page();
  assert.deepEqual(b.identities, { state: 'OK', reason: null, count: 19 }); assert.equal(qgv.rows(b, { scope: 'TARGET' }).length, 19, 'the next page read the catalog again');
  assert.equal(data.state('actual-catalog.json').state, 'OK'); assert.equal(asked(), 2);
  assert.equal(await data.static('actual-catalog.json'), await data.static('actual-catalog.json')); assert.equal(asked(), 2, 'a good read is kept for the page');
});

// ---------------------------------------------------------------- qgv
test('qgv.page: rows are an exact projection of QgvScores.pageResult computed with the same score view; no price leaves; NA has a reason', async () => {
  const U = universeView(), E = env({ prices: { universeView: U.view } }), { win, mods, qgv, data } = E, calls = spy(E);
  const QS = mods.QgvScores, TB = mods.TargetV1Builder;
  const pg = await qgv.page();
  assert.equal(calls.length, 1); const { view, opts } = calls[0], result = await calls[0].p;
  assert.equal(await QS.pageResult(view, opts), result, 'the same memoized result for the same view and inputs');
  // The score view: no request, the Universe read from the price layer, no stored price tabs before a click, no storage writes.
  await assert.rejects(view.fetch(QGV2), /SCORE_PATH_NO_NETWORK/);
  assert.equal(view.PrivateSubsetView, U.view); assert.deepEqual(await view.PriceStore.monthEndCloses('SPY', { fetch: false }), {});
  assert.throws(() => view.localStorage.setItem('a', 'b'), /ACTION_REQUIRED/); assert.throws(() => view.indexedDB.open('investment-device-actual-v1', 1), /DEVICE_STORE_NOT_OPENED/);
  assert.equal(view.dispatchEvent(new CustomEvent('probe')), true, 'bound like DataRefresh.proxy');
  assert.equal(opts.v2Inputs, data.get(QGV2)); assert.equal(opts.catalog.schema, 'DEVICE_ACTUAL_CATALOG/1'); assert.equal(opts.identities.length, 19);
  const c = result.computed;
  assert.equal(pg.state, 'READY'); assert.equal(pg.as_of, c.v2_as_of); assert.equal(pg.profile_id, c.profile.id); assert.equal(pg.calc_version, opts.v2Inputs.calc_version);
  assert.deepEqual(pg.rows.map((r) => r.id), Object.keys(c.rows), 'QgvScores order, no sorting or filtering');
  assert.deepEqual(JSON.parse(JSON.stringify(pg.coverage)), JSON.parse(JSON.stringify(QS.vCoverage(result, opts.v2Inputs))));
  const priced = pg.coverage.priced; assert.ok(priced >= 10);
  assert.deepEqual(pg.price_basis, { kind: 'DEVICE_RAM', connected: true, source: BASIS.source, read_id: BASIS.read_id, read_at: BASIS.acquired_at, time_status: 'UNCONFIRMED', freshness: 'UNDETERMINED',
    times: [{ source: 'UNIVERSE_SHEET', rows: priced, confirmed: 0, unconfirmed: priced, stale: 0, from: null, to: null }] }, 'the Universe read has no price time (D10): unconfirmed, freshness undetermined');
  const targets = new Set(opts.identities.map((x) => x.company_id)); let withV = 0, ranked = 0, qgRef = 0;
  for (const r of pg.rows) {
    const row = c.rows[r.id], p = row.primary;
    assert.deepEqual(r.score, { total: finiteOrNull(p.total), q: finiteOrNull(p.q), g: finiteOrNull(p.g), v: finiteOrNull(p.v) }, r.id);
    assert.equal(r.rank.official, Number.isInteger(row.rank) ? row.rank : null, r.id); assert.equal(r.rank.qg_reference_order, row.qg_reference ? row.qg_reference.order : null, r.id);
    assert.equal(r.rank.group, QS.exploreGroup(row), r.id); assert.equal(r.rank.weights, 'OFFICIAL'); assert.equal(r.rank.of, c.official.ranked);
    assert.equal(r.code, typeof row.universe_code === 'string' ? row.universe_code : null); assert.equal(r.record, row.code); assert.equal(r.scope, row.outside_universe ? 'OUTSIDE_UNIVERSE' : 'UNIVERSE');
    assert.equal(r.target, targets.has(r.id)); assert.deepEqual(r.flags, p.flags); assert.equal(r.value_trap_gate, p.value_trap_gate === true);
    assert.deepEqual(r.coverage.v_factors, TB.vFactors(p), r.id + ' v_factors = TargetV1Builder.vFactors');
    assert.equal(r.coverage.factors.available, p.factors_available); assert.equal(r.coverage.factors.total, p.factors_total);
    for (const a of ['Q', 'G', 'V']) assert.equal(r.coverage.axes[a] ? r.coverage.axes[a].status : null, p.coverage && p.coverage.axes ? p.coverage.axes[a].status : null, r.id + a);
    for (const k of ['total', 'q', 'g', 'v']) { assert.equal(r.score[k] === null, typeof r.na_reason[k] === 'string' && r.na_reason[k].length > 0, r.id + ' ' + k + ' null ⇔ reason'); }
    assert.equal(r.rank.official === null, typeof r.na_reason.rank === 'string', r.id + ' rank null ⇔ reason');
    if (r.score.v === null) assert.equal(r.na_reason.v, p.coverage && p.coverage.axes && p.coverage.axes.V.reason ? p.coverage.axes.V.reason : p.total_reason || 'V2_INPUTS_NOT_AVAILABLE', r.id + ' V reason = vCoverage rule');
    assert.equal(r.source, 'DEVICE_TEMPORARY'); assert.equal(r.source_label, '임시 V');
    if (r.score.v !== null) withV++; if (r.rank.official !== null) ranked++; if (r.rank.qg_reference_order !== null) { qgRef++; assert.equal(r.na_reason.rank, 'QG_REFERENCE'); }
  }
  assert.ok(withV >= 10 && ranked >= 10 && qgRef >= 1, 'fixture covers ranked and Q·G reference rows');
  assert.equal(pg.rows.filter((r) => r.target).length, 19);
  // No price or price-derived field; the sentinel prices of the Universe read appear nowhere in the page.
  const keys = keysDeep(pg); for (const k of PRICE_KEYS) assert.ok(!keys.has(k), 'no ' + k);
  const text = JSON.stringify(pg); for (const s of U.sentinels) assert.ok(!text.includes(s), 'sentinel price leaked');
  assert.ok(Object.isFrozen(pg) && Object.isFrozen(pg.rows) && Object.isFrozen(pg.rows[0].score));
  // Shared: every screen gets the same page for the same inputs; row / rows / coverage read it.
  assert.equal(await qgv.page(), pg); assert.equal(qgv.coverage(pg), pg.coverage);
  assert.equal(qgv.row(pg, 'nvda').id, 'nvda'); assert.equal(qgv.row(pg, 'NASDAQ:NVDA'), qgv.row(pg, 'nvda'), 'a TARGET in the Universe is that code row');
  assert.equal(qgv.rows(pg, { scope: 'TARGET' }).length, 19); assert.equal(qgv.rows(pg, { scope: 'UNIVERSE' }).length, pg.rows.filter((r) => r.scope === 'UNIVERSE').length);
  assert.equal(qgv.rows(pg, { scope: 'UNIVERSE' }).length, Object.keys(opts.v2Inputs.records).filter((k) => !k.startsWith('TARGET:')).length);
  assert.throws(() => qgv.rows(pg, { scope: 'X' }), /SCOPE_UNKNOWN/); assert.throws(() => qgv.rows({ rows: [] }), /PAGE_UNKNOWN/);
  assert.equal(qgv.forEngines(pg), c, 'engines get the computed result as QgvScores made it');
  assert.deepEqual(win.requests.filter((r) => !data.FILES.includes(r.name)), [], 'only public files were requested');
});

test('V source: DEVICE_TEMPORARY with #391 words on every page and row; central V not readable yet; engines record DEVICE_TEMPORARY', async () => {
  const { qgv, mods } = env(), Q = qgv;
  assert.deepEqual(Q.V_SOURCES.DEVICE_TEMPORARY, V391); assert.ok(Object.isFrozen(Q.V_SOURCES) && Object.isFrozen(Q.V_SOURCES.DEVICE_TEMPORARY));
  assert.deepEqual(Q.V_SOURCES.OFFICIAL_CENTRAL, { id: 'OFFICIAL_CENTRAL', ko: '공식 V', note: '중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님)' });
  if (mods.TargetV1Builder.V_SOURCE) assert.deepEqual(Q.V_SOURCES.DEVICE_TEMPORARY, { ...mods.TargetV1Builder.V_SOURCE }, 'after #391: the builder constant');
  assert.equal(qgv.vSource(), 'DEVICE_TEMPORARY');
  const pg = await qgv.page();
  assert.equal(pg.v_source, Q.V_SOURCES.DEVICE_TEMPORARY); assert.equal(pg.engine_v_source, Q.V_SOURCES.DEVICE_TEMPORARY); assert.equal(qgv.vSource(), 'DEVICE_TEMPORARY');
  assert.ok(pg.rows.every((r) => r.source === 'DEVICE_TEMPORARY' && r.source_label === '임시 V'));
  const src = fs.readFileSync(R.newPath('qgv.js'), 'utf8');
  assert.equal((src.match(/const OFFICIAL_READER=null;/g) || []).length, 1, 'one switch, unset');
  for (const code of ['NO_OFFICIAL_YET', 'SUPPLY_FAILED', 'VERIFY_FAILED', 'PRICE_DEPENDENT_NOT_COMPUTABLE']) assert.match(qgv.reasonText(code), /초안 문구\)$/, code + ' pre-registered (draft wording)');
  assert.doesNotMatch(src, /OFFICIAL_NOT_AVAILABLE/);
  assert.equal(qgv.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED'), mods.QgvScores.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED'));
  assert.equal(qgv.reasonText('QG_REFERENCE', true), 'No V: in the Q·G reference list, not the official ranking');
});

test('V source switch: a device page is labelled DEVICE_TEMPORARY even if the switch turns while it is computed; an OFFICIAL route fails loudly (no central page yet)', async () => {
  // A copy of qgv.js whose one switch reads a test reader (only that line differs).
  const src = fs.readFileSync(R.newPath('qgv.js'), 'utf8'), line = 'const OFFICIAL_READER=null;';
  assert.equal(src.split(line).length, 2);
  const tmp = path.join(require('node:os').tmpdir(), 'web_app_qgv_switch_' + process.pid + '.js');
  fs.writeFileSync(tmp, src.replace(line, 'const OFFICIAL_READER=globalThis.__webAppTestReader;'));
  try {
    let mode = 'DEVICE'; globalThis.__webAppTestReader = { state: () => mode };
    delete require.cache[tmp]; const Copy = require(tmp), E = env();
    const QS = E.win.QgvScores; E.win.QgvScores = Object.freeze({ ...QS, pageResult: (...a) => { mode = 'OFFICIAL'; return QS.pageResult(...a); } });
    const q = Copy.create({ win: E.win, data: E.data, action: E.action, prices: null });
    const pg = await q.page();
    assert.equal(mode, 'OFFICIAL', 'the switch turned during the computation');
    assert.equal(pg.v_source.id, 'DEVICE_TEMPORARY'); assert.equal(pg.engine_v_source.id, 'DEVICE_TEMPORARY');
    assert.ok(pg.rows.length > 500 && pg.rows.every((r) => r.source === 'DEVICE_TEMPORARY'), 'device quotes: the temporary V label');
    assert.equal(q.preview(pg, CUSTOM.cases[0].input.weights).v_source.id, 'DEVICE_TEMPORARY');
    // Routed to the central page, which does not exist yet: a fixed code, never a device result labelled official.
    await assert.rejects(q.page(), /NO_OFFICIAL_YET/);
  } finally { delete globalThis.__webAppTestReader; delete require.cache[tmp]; fs.rmSync(tmp, { force: true }); }
});

test('qgv states without a usable file: NO_DATA (404), DATA_FORMAT_NEWER (newer schema), READ_FAILED (invalid); rows empty', async () => {
  const newer = F.strictPayload(); newer.schema_version = 99;
  const huge = { body: JSON.stringify({ pad: 'x'.repeat(3 * 1024 * 1024) }) };
  for (const [f, state, reason] of [[null, 'NO_DATA', 'SEC_QGV2_NOT_PUBLISHED'], [{ json: newer }, 'DATA_FORMAT_NEWER', 'SEC_QGV2_SCHEMA_NEWER'], [{ body: '[]' }, 'READ_FAILED', 'SEC_QGV2_INVALID'], [huge, 'READ_FAILED', 'SEC_QGV2_INVALID']]) {
    const { qgv, data } = env({ files: { [QGV2]: f } }), pg = await qgv.page();
    if (f === huge) assert.deepEqual([data.state(QGV2).state, data.state(QGV2).why], ['FAILED', 'INVALID'], 'over 2 MiB: an invalid file, not a network failure');
    assert.equal(pg.state, state); assert.equal(pg.reason, reason); assert.deepEqual(pg.rows, []); assert.deepEqual(qgv.rows(pg, { scope: 'TARGET' }), []);
    assert.equal(pg.v_source.id, 'DEVICE_TEMPORARY'); assert.equal(pg.identities, null); assert.throws(() => qgv.forEngines(pg), /PAGE_NOT_READY/);
    assert.notEqual(qgv.reasonText(reason), '계산 불가 (' + reason + ')', reason + ' worded');
  }
});

test('qgv.preview: the custom vectors weight trees give PERSONAL rows (the 2.2 personal call: own gate, no preset), never an official rank; page unchanged', async () => {
  const U = universeView(), E = env({ prices: { universeView: U.view } }), { qgv, mods } = E, QS = mods.QgvScores, calls = spy(E);
  const pg = await qgv.page(), before = JSON.stringify(pg), result = await calls[0].p; let gateOff = 0;
  for (const c of CUSTOM.cases) {
    const pv = qgv.preview(pg, c.input.weights, { typeWeights: c.input.type_weights, gate: c.input.gate });
    assert.equal(pv.weights, 'PERSONAL'); assert.equal(pv.state, 'READY', c.id); assert.equal(pv.v_source.id, 'DEVICE_TEMPORARY');
    assert.ok(pv.rows.every((r) => r.rank.official === null && r.rank.weights === 'PERSONAL' && r.source === 'DEVICE_TEMPORARY'), c.id + ' never official');
    // The old 2.2 personal call (device-profiles.js compare): base = the shared result's population, quotes and official ranks,
    // then compute({...base, gate: the profile's gate, weights, typeWeights}) with no preset.
    const base = { identities: result.identities, v2Inputs: calls[0].opts.v2Inputs, quotes: structuredClone(result.quotes), official: result.official, referenceRows: QS.pageReferences() };
    const direct = QS.compute({ ...base, gate: c.input.gate, weights: c.input.weights, typeWeights: c.input.type_weights });
    assert.equal(pv.profile_id, direct.personal.profile.id, c.id); assert.deepEqual(pv.rows.map((r) => r.id), Object.keys(direct.rows));
    if (c.input.gate === false) { assert.match(pv.profile_id, /gate-off/, c.id + ' a gate-off profile is previewed gate off'); gateOff++; }
    for (const r of pv.rows) {
      const d = direct.rows[r.id];
      assert.deepEqual(r.score, { total: finiteOrNull(d.personal.total), q: finiteOrNull(d.personal.q), g: finiteOrNull(d.personal.g), v: finiteOrNull(d.personal.v) }, c.id + ' ' + r.id);
      assert.equal(r.rank.personal, Number.isInteger(d.personal_rank) ? d.personal_rank : null, c.id + ' ' + r.id);
      for (const k of ['total', 'q', 'g', 'v']) assert.equal(r.score[k] === null, typeof r.na_reason[k] === 'string', c.id + r.id + k);
    }
    assert.equal(pv.v_weight_zero, c.input.weights.axis.V === 0);
    const keys = keysDeep(pv); for (const k of PRICE_KEYS) assert.ok(!keys.has(k), 'no ' + k);
  }
  assert.equal(gateOff, 1, 'the fixture has one gate-off profile');
  assert.throws(() => qgv.preview(pg, CUSTOM.cases[0].input.weights, { gate: 'off' }), /GATE_INVALID/);
  for (const bad of CUSTOM.units.invalid) { const pv = qgv.preview(pg, bad.weights); assert.equal(pv.state, 'INVALID', bad.id); assert.equal(pv.reason, 'WEIGHTS_INVALID'); assert.deepEqual(pv.rows, []); }
  assert.equal(JSON.stringify(pg), before, 'the official page is untouched');
});

test('qgv profile, constants and subscriptions: RAM only; a profile change reaches every page; data updates notify', async () => {
  const { qgv, data, win, mods } = env();
  const notes = []; const ac = new AbortController(); qgv.subscribe((w) => notes.push(w), { signal: ac.signal });
  const a = await qgv.page();
  assert.throws(() => qgv.setProfile({ preset: 'nope' }), /PRESET_UNKNOWN/); assert.throws(() => qgv.setProfile({ gate: 'on' }), /GATE_INVALID/);
  const other = Object.keys(mods.QgvV2.PRESETS).find((k) => k !== mods.QgvV2.DEFAULT_PRESET);
  qgv.setProfile({ preset: other, gate: false }); assert.deepEqual(qgv.profile(), { preset: other, gate: false });
  const b = await qgv.page(); assert.notEqual(a, b); assert.equal(b.preset, other); assert.equal(b.gate, false); assert.equal(b.rows[0].rank.weights, 'PERSONAL', 'not the official default profile');
  const x = await qgv.page({ preset: mods.QgvV2.DEFAULT_PRESET, gate: true });
  assert.equal(x.profile_id, a.profile_id); assert.equal(JSON.stringify(x.rows), JSON.stringify(a.rows), 'a caller\'s explicit official profile gives the official values');
  const k = qgv.constants(); assert.deepEqual(k.WEIGHTS, JSON.parse(JSON.stringify(mods.QgvV2.WEIGHTS))); assert.deepEqual(k.SUBMETRICS, JSON.parse(JSON.stringify(mods.SecQgv2.SUBMETRICS)));
  assert.deepEqual(k.V_FACTORS, [...mods.TargetV1Builder.V_FACTORS]); assert.ok(Object.isFrozen(k.WEIGHTS.Q));
  win.document.dispatchEvent(new Event('device-actual-changed'));
  assert.deepEqual(notes, ['PROFILE', 'DEVICE']);
  ac.abort(); qgv.setProfile({}); assert.equal(notes.length, 2, 'unsubscribed on abort');
  const sig = new AbortController(); sig.abort(); await assert.rejects(qgv.page({ signal: sig.signal }), /ABORTED/);
  assert.equal(win.requests.filter((r) => !data.FILES.includes(r.name)).length, 0);
});
