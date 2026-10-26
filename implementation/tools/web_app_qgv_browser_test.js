'use strict';
// New frontend P2-2a · menu 1 QGV · 1.1 리더보드 (feature 2.1.1–2.1.7; board add/QGVLeaderboard · add/m/MQGVLeaderboard, owner draft
// QGV / MQGV columns) in a real browser, at 1440×1000 and 390×844. Builds the development site (tools/web_app_test_site.js), serves the
// live-only score inputs and a classification file as synthetic fixtures, answers Google with stand-ins, and checks #/qgv:
//  - Before IS2.ready (screen-qgv-live.js held back): main[data-route=qgv], sections exactly 1-1..1-4, seven [data-lb] blocks,
//    pending text without digits, every button disabled, no data request; after leaving and returning, the current render's
//    block nodes fill in place once the file is released.
//  - Every case first proves a non-empty table (> 1 drawn rows; > 1 distinct keys for a sort or filter case). Default state =
//    Universe504, list 전체, QGV 높은 순, no prices.
//  - Values from the layer: rank / QGV / Q / G / V / SIC / 유형 / 자료 기준일 cells equal the layer row (ko-KR 1 decimal, or NA +
//    reasonText; 참고 n; — + reason), the V header = pg.v_source.ko, the rank sub-label = rankLabel(pg); nvda / amd equal their
//    company cards; IS2.qgv.page() is the same object before and after #/qgv opened. Counts come from the layer.
//  - 2.1.1 / 2.1.5: scope and list chips (counts = listOf over layer rows), outside rows only in the outside box / scope / TARGET
//    전체 with their rank reason, list chips off in the outside scope, the 종합 순위 empty state before prices and its QG button.
//  - 2.1.2 (default state, and on 종합 순위 after the click path): every option orders as the ported rule over the layer rows,
//    rank texts never change, NA last, QGV tiers never interleaved, header button = select, aria-sort, one-way toggle off, reset,
//    cap options off before a Universe read; population boxes from the layer / model.
//  - 2.1.3: a filter hides rows without re-ranking; 분류 자료 없음 = null SIC rows; nvda under its TARGET classification; type
//    options = type_config names; 필터 모두 풀기; the phone panel (aria-expanded).
//  - 2.1.4: before load every return cell says PRICE_TABS_NOT_LOADED's text; wait chips off; the load button off with the
//    PRICE_TABS_OFF / AUTH_REQUIRED / SHEET_NOT_CONNECTED reason; synthetic clicks request and write nothing and print no code.
//  - Clicks (GIS / Sheets stand-ins with sentinel decimals): ① → ② → ③ (③ by Enter: one action) give the layer's ranks; M3 in
//    [data-ram-price] text only; assertRamOnly; leaks() empty; only the click-written keys stored; the 2.1.6 badges and the
//    2.1.7 candidates from IS2.qgv.model; a saved weights profile previews without touching the official page. A returning
//    user's price tabs (flag pre-set): the returns click gives ReportBenchmarks.priceIndex values with the 분할 미확인 note,
//    returns order the view without changing ranks; after a reload V and returns are NA again.
//  - Failures: sec-qgv2.json 404 / invalid, screen-qgv-live.js 404 (LOADER_FAILED), leaving while computing.
//  - Boundaries in every state: same-origin (only the stand-ins leave in the click contexts), FILES only, opening reads CORE +
//    actual-catalog.json + company-names-ko.json, storage 0 without clicks, blocked() 0, no console error, CSP 0, [style] 0, no
//    overflow at 390, 44 px tap targets, IS2.selection unchanged, no board example value, no visible reason code.
// Synthetic data only: sentinel values are made-up decimals; the sheet id and the token are in-memory fixtures.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const SHARES = require('./sec_universe_shares_fixture.js');
const RB = R.requireOld('report-benchmarks.js');

const NOW = '2026-10-14T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const CUSTOM = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_v2_custom_vectors_v1.json'), 'utf8'));
const UNPUBLISHED = ['sec-public-inputs.json'];
const SHEET_ID = ['synthetic', 'qgv', 'board', 'universe', 'sheet'].join('_');
const TOKEN = ['memory', 'only', 'synthetic', 'qgv', 'session'].join('-'), SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client', SHEETS = 'https://sheets.googleapis.com';
const RANGE = "'Universe'!A1:C1025";
const VALUES_URL = SHEETS + '/v4/spreadsheets/' + SHEET_ID + '/values/' + encodeURIComponent(RANGE) + '?valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=SERIAL_NUMBER';
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){return{requestAccessToken:function(){window.__gis++;cfg.callback({'
  + 'access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",scope:' + JSON.stringify(SCOPE) + '});}};},revoke:function(t,done){if(done)done({});}}}};';
// The Universe tab: every LIVE code priced but MSFT (sentinel decimals) and the share counts; as web_app_data_layer_browser_test.js.
const QGV2 = F.strictPayload();
const PRICED = Object.entries(QGV2.records).filter(([c, r]) => r.state === 'LIVE' && c !== 'NASDAQ:MSFT').map(([c]) => c);
if (!PRICED.includes('NASDAQ:NVDA')) PRICED.push('NASDAQ:NVDA');
// Share-class group codes (ShareClassGroups.CONFIG: Alphabet, Fox) need their group's own CIK and covers; left out so the M3 rank index is READY.
for (const g of R.requireOld('share-class-groups.js').CONFIG.groups) for (const c of g.codes) if (PRICED.includes(c)) PRICED.splice(PRICED.indexOf(c), 1);
const pad = (i) => String(i).padStart(2, '0');
const PRICE = PRICED.map((_, i) => String(311 + 7 * i) + '.0731' + pad(i) + '7'), CAP = PRICED.map((_, i) => String(52003 + 13 * i) + '.0419' + pad(i) + '3');
const UNIVERSE_VALUES = [['code', 'marketcap', 'price'], ...PRICED.map((c, i) => [c, Number(CAP[i]), Number(PRICE[i])])];
const SHARES_FILE = SHARES.payload(Object.fromEntries(PRICED.map((c, i) => [c, { n: 2000001 + i, shares: 1000 + i }])), Date.parse(NOW));
// The price tab of a returning user: SPY sessions and three symbols with sentinel decimals (AES falls, the others rise; the
// steps keep every return off the board's example percentages).
const SESSIONS = []; for (let t = Date.parse('2026-09-01T00:00:00Z'); t <= Date.parse('2026-10-12T00:00:00Z'); t += 86400000) { const d = new Date(t); if (d.getUTCDay() % 6) SESSIONS.push(d.toISOString().slice(0, 10)); }
const CLOSE = (sym, i) => { const base = { SPY: 500, NVDA: 120, AFL: 90, AES: 30 }[sym], step = { SPY: 0.37, NVDA: 0.37, AFL: 0.29, AES: -0.17 }[sym]; return Number((base + step * i).toFixed(2) + '0' + pad(i) + '8293'); };
const TAB_SYMBOLS = ['SPY', 'NVDA', 'AFL', 'AES'];
const CLOSES = Object.fromEntries(TAB_SYMBOLS.map((s) => [s, Object.fromEntries(SESSIONS.map((d, i) => [d, CLOSE(s, i)]))]));
const TAB_ROWS = [['symbol', 'date', 'close', 'source', 'fetched_at'], ...TAB_SYMBOLS.flatMap((s) => SESSIONS.map((d, i) => [s, d, String(CLOSE(s, i)), 'YAHOO', '2026-10-13T00:00:00Z']))];
const CLOSE_SENTINELS = TAB_SYMBOLS.flatMap((s) => SESSIONS.map((_, i) => String(CLOSE(s, i))));
const SENTINELS = [...PRICE, ...CAP];
for (const v of [...SENTINELS, ...CLOSE_SENTINELS]) if (String(Number(v)) !== v) throw new Error('SENTINEL_NOT_CANONICAL ' + v);
// Board example values and words that must never show (lookarounds: real totals such as 72.2 exist). Counts that real data can
// produce here (17 · 2 · 22 · 30 · 37, rank and 참고 numbers) are left out of the integer list.
const EXAMPLES = [/예시/, /EXA\b/, /M3 #41/, /245\/504/, /V 요인 4\/5/, /참고 3\/4/, /\(3·1·2\)/, /calc_version/, /10\/17/, /10\/16/, /10:42/, /[+\u2212-](?:4\.2|1\.1|2\.3|0\.4)%/,
  ...[81, 84, 79, 58, 72, 78, 64, 41, 66, 61, 70, 55, 69, 498, 312, 140].map((n) => new RegExp('(?<![\\d.,])' + n + '(?![\\d.,])'))];
const CODE_TEXT = /\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/;
const FORMATS = { fmt: (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v) };
let phase = 'START';

// In-page test helpers (read the layer and the drawn table; nothing here changes the page).
const HELPERS = () => {
  window.__csp = 0; window.__gis = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; });
  window.__qt = {
    fmt: (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v),
    day: (t) => { const d = Date.parse(t); return Number.isFinite(d) ? new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'UTC' }).format(d) : null; },
    known(code) { const S = window.QgvScores, I = window.IS2; return typeof code === 'string' && (Object.hasOwn(S.REASON, code) || I.qgv.reasonText(code) !== S.reasonText(code)); },
    listOf(r) { if (r.scope === 'OUTSIDE_UNIVERSE' || r.reference_only) return null; if (Number.isInteger(r.rank.official)) return 'RANKED'; if (r.rank.qg_reference_order !== null) return 'QG_REFERENCE';
      return r.rank.group === 'PARTIAL_AXES' || r.rank.group === 'CHECK_DATA' ? r.rank.group : null; },
    drawn() { return [...document.querySelectorAll('[data-lb-table] tbody tr[data-row]')].map((tr) => { const c = {}; for (const td of tr.querySelectorAll('td[data-cell]')) c[td.dataset.cell] = td.textContent; return { id: tr.dataset.row, c, title: tr.querySelector('a.co').textContent }; }); },
    // Every drawn row's cells against the layer row (the §2.1.1 rules); returns the mismatches.
    async check({ preview = null } = {}) {
      const I = window.IS2, Q = I.qgv, pg = await Q.page(), qt = window.__qt, T = window.TypeConfigDefaults, D = I.data, rec = D.get('sec-qgv2.json'), cls = D.get('company-classification.json');
      const rows = new Map((preview ? preview.rows : pg.rows).map((r) => [r.id, r])), bad = [], drawn = qt.drawn();
      const sic = (id) => { const ok = (v) => (typeof v === 'string' && /^\d{4}$/.test(v) && v !== '0000' ? v : null);
        if (id.includes(':')) { const r = rec.records[id]; return r && r.state !== 'WITHDRAWN' && r.identity_withdrawn !== true ? ok(r.sic) : null; }
        const x = cls && cls.data.companies[id] ? cls.data.companies[id].industry : null; return x && x.identity_withdrawn !== true ? ok(x.sic) : null; };
      for (const d of drawn) {
        const r = rows.get(d.id); if (!r) { bad.push(d.id + ' not a layer row'); continue; }
        const val = (k) => (typeof r.score[k] === 'number' ? qt.fmt(r.score[k]) : 'NA' + Q.reasonText(r.na_reason[k]));
        for (const [cell, k] of [['qgv', 'total'], ['q', 'q'], ['g', 'g'], ['v', 'v']]) if (d.c[cell] !== val(k)) bad.push(d.id + ' ' + cell + ': ' + d.c[cell] + ' ≠ ' + val(k));
        const n = preview ? r.rank.personal : r.rank.official;
        const rank = Number.isInteger(n) ? String(n) : r.rank.qg_reference_order !== null ? '참고 ' + r.rank.qg_reference_order : '—' + Q.reasonText(r.na_reason.rank);
        if (!Number.isInteger(n) && r.rank.qg_reference_order === null && !qt.known(r.na_reason.rank)) bad.push(d.id + ' rank reason unknown');
        if (d.c.rank !== rank) bad.push(d.id + ' rank: ' + d.c.rank + ' ≠ ' + rank);
        const s = sic(d.id); if (d.c.sic !== (s || 'NA분류 자료 없음')) bad.push(d.id + ' sic: ' + d.c.sic);
        const names = T.types.filter((t) => r.types.selected.includes(t.id)).map((t) => t.name);
        const ty = names.length ? names.join(' · ') : !r.types.selected.length && r.types.reason === 'NO_RECOGNIZED_TYPE' ? '미분류' : 'NA' + (qt.known(r.types.reason) ? Q.reasonText(r.types.reason) : '유형 자료 없음');
        if (d.c.type !== ty) bad.push(d.id + ' type: ' + d.c.type + ' ≠ ' + ty);
        if (d.c.asof !== (qt.day(r.acquired_at) || 'NA자료 기준일 없음')) bad.push(d.id + ' asof: ' + d.c.asof);
      }
      return { n: drawn.length, bad, distinctQ: new Set(drawn.map((d) => d.c.q)).size };
    },
  };
};

// Requests (route level) with the Google stand-ins; anything else outside the origin is aborted and listed.
function routes(context, origin, { tabs = false } = {}) {
  const log = [], unexpected = [], counts = { values: 0, tabs: 0, titles: 0 };
  return { log, unexpected, counts, install: () => context.route('**/*', async (route) => {
    const req = route.request(), url = new URL(req.url());
    log.push({ url: req.url(), method: req.method(), body: req.postData() || '' });
    if (url.origin === origin) { await route.continue(); return; }
    if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
    if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
    const authed = req.headers().authorization === 'Bearer ' + TOKEN && req.method() === 'GET' && !req.postData();
    if (authed && req.url() === VALUES_URL) { counts.values++; await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ range: RANGE, majorDimension: 'ROWS', values: UNIVERSE_VALUES }) }); return; }
    const base = '/v4/spreadsheets/' + SHEET_ID;
    if (tabs && authed && url.origin === SHEETS && url.pathname === base && /fields=sheets/.test(url.search)) { counts.titles++; await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sheets: [{ properties: { title: 'Prices_D' } }] }) }); return; }
    const m = tabs && authed && url.origin === SHEETS ? /^\/values\/'([^']+)'!([A-Z])(\d+)(?::([A-Z])(\d+))?$/.exec(decodeURIComponent(url.pathname.slice(base.length))) : null;
    if (m && url.pathname.startsWith(base + '/values/') && m[1] === 'Prices_D') {
      counts.tabs++; const col = (c) => c.charCodeAt(0) - 64, values = TAB_ROWS.slice(+m[3] - 1, m[5] ? +m[5] : +m[3]).map((r) => r.slice(col(m[2]) - 1, col(m[4] || m[2])));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(values.length ? { range: m[1], majorDimension: 'ROWS', values } : { range: m[1] }) }); return;
    }
    unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
  }) };
}
// Test-only buttons (not the site; no style): each passes its real click event to one store action.
async function testButtons(page) {
  await page.evaluate(({ id, weights }) => {
    if (document.querySelector('[data-test-actions]')) return;
    const I = window.IS2, out = window.__out = {}, bar = document.createElement('div'); bar.dataset.testActions = '';
    const acts = { source: (e) => I.store.universeSource.set(e, id), sheet: (e) => I.store.sheetSource.set(e, id), weights: (e) => I.store.saveWeights(e, { name: '시험 가중치', weights, gate: true }) };
    for (const [name, fn] of Object.entries(acts)) { const b = document.createElement('button'); b.type = 'button'; b.dataset.testAction = name; b.textContent = 'test ' + name;
      b.addEventListener('click', (e) => { let p; try { p = Promise.resolve(fn(e)); } catch (err) { p = Promise.reject(err); } out[name] = p.then(() => 'OK', (err) => String(err && err.message)); }); bar.appendChild(b); }
    document.body.prepend(bar);// above the page, never under the phone tab bar
  }, { id: SHEET_ID, weights: CUSTOM.cases[0].input.weights });
}
const testClick = async (page, name) => { await page.locator('[data-test-action="' + name + '"]').click(); return page.evaluate((n) => window.__out[n], name); };

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: QGV2 }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const pageFiles = new Set([...R.scripts(), ...fs.readdirSync(R.NEW)]);
  const nameOf = (u) => decodeURIComponent(new URL(u).pathname.slice(1));
  const dataNames = (urls) => urls.filter((u) => new URL(u).origin === s.origin).map(nameOf).filter((n) => n && !pageFiles.has(n));
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const phone = width < 720;
      const open = async ({ tabs = false, flag = false } = {}) => {
        const context = await browser.newContext({ viewport: { width, height } });
        await context.clock.setFixedTime(new Date(NOW));
        await context.addInitScript(HELPERS);
        // A returning user's browser: the PriceStore flag (useTabs wrote it on an earlier visit) is there before the page loads.
        if (flag) await context.addInitScript(() => { try { if (localStorage.getItem('investment.web.v1.price-store-enabled') === null) localStorage.setItem('investment.web.v1.price-store-enabled', '1'); } catch (_) {} });
        const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED }), rec = routes(context, s.origin, { tabs });
        await rec.install();
        return { context, page, seen, rec };
      };
      const tag = (p) => { phase = width + ' ' + p; };
      const ready = (page) => page.evaluate(() => window.IS2.ready.then(() => window.IS2.loadState()));
      const tableReady = (page) => page.locator('[data-lb-table] tbody tr').first().waitFor({ timeout: 20000 });
      const settle = (page) => page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      const common = async (page, label = phase) => {
        assert.equal(await page.locator('[style]').count(), 0, label + ': no style attribute');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
        for (const t of await page.locator('main [data-pending]').allTextContents()) assert.doesNotMatch(t, /\d/, label + ': pending text has no digit: ' + t);
        const text = await page.locator('main').innerText();
        for (const re of EXAMPLES) assert.doesNotMatch(text, re, label + ': no board example value ' + re);
        assert.doesNotMatch(text, CODE_TEXT, label + ': no visible reason code (' + (text.match(CODE_TEXT) || [''])[0] + ')');
        const small = await page.evaluate(() => [...document.querySelectorAll('main button, main .chip, main summary, main label.check')].filter((e) => { const b = e.getBoundingClientRect(); return b.width > 0 && b.height > 0 && getComputedStyle(e).visibility !== 'hidden'; })
          .filter((e) => e.getBoundingClientRect().height < 43.5).map((e) => e.tagName + ':' + e.textContent.slice(0, 30)));
        assert.deepEqual(small, [], label + ': every button / chip / summary / checkbox label is at least 44 px high');
      };
      const boundaries = async ({ page, seen, rec }, { stored = [], outside = [] } = {}) => {
        assert.equal(await page.evaluate(() => window.__csp), 0, phase + ': no CSP violation');
        assert.deepEqual(rec.unexpected, [], phase + ': no unexpected outside request');
        const out = [...new Set(seen.outside.map((u) => { const x = new URL(u); return x.origin + x.pathname; }))].filter((u) => !outside.some((o) => u.startsWith(o)));
        assert.deepEqual(out, [], phase + ': no request leaves the origin but the stand-ins');
        const FILES = await page.evaluate(() => window.IS2.data.FILES);
        assert.deepEqual([...new Set(dataNames(seen.requests).filter((n) => !FILES.includes(n)))], [], phase + ': data requests only in IS2.data.FILES');
        assert.deepEqual(seen.errors, [], phase + ': no console error but the intended 404s');
        const st = await site.storage(page);
        assert.deepEqual(Object.keys(st.localItems).sort(), [...stored].sort(), phase + ': only the keys the clicks may write');
        assert.equal(st.session, 0, phase + ': no sessionStorage');
        assert.deepEqual(await page.evaluate(() => window.IS2.selection.get()), null, phase + ': IS2.selection untouched');
      };

      // ================================================================ before IS2.ready
      {
        tag('before ready');
        const ctx = await open(), { page, seen } = ctx;
        let release; const gate = new Promise((r) => { release = r; });
        await page.route('**/screen-qgv-live.js', async (route) => { await gate; await route.continue(); });
        await page.goto(s.base + '#/qgv', { waitUntil: 'domcontentloaded' }); await page.locator('main[data-route=qgv]').waitFor();
        assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['1-1', '1-2', '1-3', '1-4']);
        assert.deepEqual(await page.locator('[data-lb]').evaluateAll((n) => n.map((x) => x.dataset.lb)), ['2.1.1', '2.1.2', '2.1.3', '2.1.4', '2.1.5', '2.1.6', '2.1.7']);
        assert.equal(await page.locator('[data-qgv-band]').count(), 1); assert.equal(await page.locator('[data-qgv-band] [data-section]').count(), 0, 'the band is outside every section');
        assert.equal(await page.locator('nav[aria-label="QGV 하위 화면"]').count(), 1);
        const enabled = await page.locator('main button:not([disabled])').count(); assert.equal(enabled, 0, 'every button disabled before IS2.ready');
        assert.ok(['WAITING', 'LOADING'].includes(await page.evaluate(() => window.IS2.loadState())));
        await common(page);
        assert.deepEqual(dataNames(seen.requests), [], 'no data request before IS2.ready');
        await page.evaluate(() => { location.hash = '#/macro'; }); await page.locator('main[data-route=macro]').waitFor();
        await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route=qgv]').waitFor();
        await page.evaluate(() => { for (const b of document.querySelectorAll('[data-lb] .lb-body')) b.__mark = 1; });
        release(); assert.equal(await ready(page), 'READY'); await tableReady(page);
        assert.deepEqual(await page.evaluate(() => [...document.querySelectorAll('[data-lb] .lb-body')].map((b) => b.__mark === 1 && b.isConnected && !b.querySelector('[data-pending]'))), [true, true, true, true, true, true, true],
          'the current render\'s seven block bodies filled in place');
        await common(page, phase + ' after release');
        await ctx.context.close();
      }

      // ================================================================ default state (no prices), values, lists, sort, filters
      {
        const ctx = await open(), { page, seen } = ctx;
        tag('open');
        await page.goto(s.base + '#/macro'); await ready(page);
        const before = await page.evaluate(async () => { window.__pg = await window.IS2.qgv.page(); return window.__pg.state; });
        assert.equal(before, 'READY');
        const at0 = seen.requests.length;
        await page.evaluate(() => { location.hash = '#/qgv'; }); await tableReady(page); await settle(page);
        const QGV_READS = [...(await page.evaluate(() => window.IS2.data.CORE)), 'actual-catalog.json', 'company-names-ko.json'];
        assert.deepEqual(dataNames(seen.requests.slice(at0)).filter((n) => !QGV_READS.includes(n)), [], 'a route change to #/qgv reads only CORE + catalog + names');
        assert.equal(await page.evaluate(async () => (await window.IS2.qgv.page()) === window.__pg), true, 'IS2.qgv.page() is the same object before and after #/qgv opened');
        // Values from the layer.
        tag('values');
        const v0 = await page.evaluate(() => window.__qt.check());
        assert.ok(v0.n > 1 && v0.distinctQ > 1, 'a non-empty table with different values'); assert.deepEqual(v0.bad, [], 'every drawn cell equals the layer row');
        const heads = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page(), th = [...document.querySelectorAll('[data-lb-table] thead th')];
          return { vsub: th.find((x) => x.querySelector('[data-col=v]')).querySelector('.sub').textContent, rsub: th[0].querySelector('.sub').textContent, vko: pg.v_source.ko, label: Q.rankLabel(pg) }; });
        assert.equal(heads.vsub, heads.vko, 'V header sub-label = pg.v_source.ko'); assert.equal(heads.rsub, heads.label, 'rank sub-label = rankLabel(pg)');
        // A READY page with a reason shows reasonText(pg.reason) above the table (rows still draw); without one, no such line.
        const why = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page(), e = document.querySelector('[data-page-reason]');
          return { reason: pg.reason, want: pg.reason ? Q.reasonText(pg.reason) : null, text: e ? e.textContent : null, na: e ? e.dataset.na : null }; });
        assert.equal(why.text, why.want, 'the page reason line equals reasonText(pg.reason) (or is absent)'); if (why.reason) assert.equal(why.na, why.reason);
        const tableCells = await page.evaluate(() => Object.fromEntries(window.__qt.drawn().filter((d) => ['nvda', 'amd'].includes(d.id)).map((d) => [d.id, d.c])));
        assert.deepEqual(Object.keys(tableCells).sort(), ['amd', 'nvda']);
        for (const [hash, id] of [['#/company/nvda', 'nvda'], ['#/company/NASDAQ%3AAMD', 'amd']]) {
          await page.evaluate((h) => { location.hash = h; }, hash); await page.locator('[data-card=qgv] [data-qgv]').waitFor();
          const card = await page.evaluate(() => { const c = document.querySelector('[data-card=qgv]'), v = (a) => c.querySelector('[data-axis=' + a + '] .qval').textContent; return { q: v('Q'), g: v('G'), v: v('V'), total: (c.querySelector('[data-total] b') || {}).textContent || 'NA' }; });
          for (const k of ['q', 'g', 'v']) assert.ok(tableCells[id][k].startsWith(card[k]), id + ' ' + k + ' equals its company card (' + card[k] + ')');
          assert.ok(tableCells[id].qgv.startsWith(card.total), id + ' QGV equals its company card');
        }
        await page.evaluate(() => { window.IS2.selection.set(null); location.hash = '#/qgv'; }); await tableReady(page);
        await common(page);
        // ---- 2.1.1 / 2.1.5 scope and list chips
        tag('scope and lists');
        const lists = await page.evaluate(async () => {
          const I = window.IS2, Q = I.qgv, pg = await Q.page(), qt = window.__qt, chips = (sel) => [...document.querySelectorAll(sel)].map((b) => ({ t: b.textContent, on: b.getAttribute('aria-pressed'), off: b.disabled }));
          const uni = Q.rows(pg, { scope: 'UNIVERSE' }), want = { ALL: uni.length }; for (const r of uni) { const l = qt.listOf(r); if (l) want[l] = (want[l] || 0) + 1; }
          return { lists: chips('button[data-list]'), scopes: chips('button[data-scope]'), want, target: Q.rows(pg, { scope: 'TARGET' }).length, outside: pg.rows.filter((r) => r.scope === 'OUTSIDE_UNIVERSE' || r.reference_only).map((r) => r.id),
            drawnIds: qt.drawn().map((d) => d.id), caption: document.querySelector('[data-lb-table] caption').textContent, count: document.querySelector('[data-lb-count]').textContent };
        });
        assert.ok(lists.drawnIds.length > 1, 'list 전체 with rows on open (never the 종합 순위 empty state)');
        assert.match(lists.caption, /^전체 · /);
        const chipN = (t) => Number(/(\d+)$/.exec(t)[1]);
        assert.deepEqual(lists.lists.map((c) => c.on), ['true', 'false', 'false', 'false', 'false'], '전체 is the default list');
        const ids = ['ALL', 'RANKED', 'QG_REFERENCE', 'PARTIAL_AXES', 'CHECK_DATA'];
        assert.deepEqual(lists.lists.map((c) => chipN(c.t)), ids.map((k) => lists.want[k] || 0), 'list chip counts = listOf over the layer rows (Universe count = rows(UNIVERSE).length)');
        assert.equal(lists.want.RANKED || 0, 0, 'no device price: no ranked row');
        assert.ok(lists.scopes[1].t.startsWith('TARGET ' + lists.target + ' · '), 'TARGET chip counts the layer TARGET rows');
        assert.ok(lists.outside.length >= 1 && lists.outside.every((id) => !lists.drawnIds.includes(id)), 'outside rows are not in the Universe table');
        const box = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page();
          return [...document.querySelectorAll('[data-outside]')].map((li) => { const r = pg.rows.find((x) => x.id === li.dataset.outside); return { id: r.id, text: li.querySelector('[data-reason]').textContent, want: '→ 근거: ' + Q.reasonText(r.na_reason.rank), code: r.na_reason.rank }; }); });
        assert.deepEqual(box.map((b) => b.id).sort(), [...lists.outside].sort());
        for (const b of box) { assert.equal(b.text, b.want, b.id + ' outside box reason from the layer'); assert.ok(['OUTSIDE_UNIVERSE', 'REFERENCE_ONLY'].includes(b.code)); }
        // Outside scope: list chips off, the outside rows (rank — + reason).
        await page.locator('button[data-scope=OUTSIDE]').click(); await page.locator('[data-lb-table][data-scope=OUTSIDE]').waitFor();
        const out = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page();
          return { rows: window.__qt.drawn().map((d) => ({ id: d.id, rank: d.c.rank, want: '—' + Q.reasonText(pg.rows.find((r) => r.id === d.id).na_reason.rank) })), off: [...document.querySelectorAll('button[data-list]')].map((b) => b.disabled), lock: !!document.querySelector('[data-list-lock=OUTSIDE]') }; });
        assert.deepEqual(out.rows.map((r) => r.id).sort(), [...lists.outside].sort(), 'the outside scope shows the outside rows');
        for (const r of out.rows) assert.equal(r.rank, r.want, r.id + ' rank reason');
        assert.deepEqual(out.off, [false, true, true, true, true], 'only 전체 in the outside scope'); assert.ok(out.lock);
        await common(page);
        // TARGET scope: TARGET rows, the outside rows among them under 전체, the portfolio column.
        await page.locator('button[data-scope=TARGET]').click(); await page.locator('[data-lb-table][data-scope=TARGET]').waitFor();
        const tgt = await page.evaluate(() => ({ ids: window.__qt.drawn().map((d) => d.id), port: document.querySelectorAll('[data-cell=portfolio]').length }));
        assert.equal(tgt.ids.length, lists.target); assert.ok(lists.outside.every((id) => tgt.ids.includes(id)), 'outside rows under TARGET 전체'); assert.equal(tgt.port, lists.target, '포트폴리오 내 순위 column');
        assert.deepEqual((await page.evaluate(() => window.__qt.check())).bad, []);
        await page.locator('button[data-scope=UNIVERSE]').click(); await page.locator('[data-lb-table][data-scope=UNIVERSE]').waitFor();
        // 종합 순위 without prices: the empty state; its button switches to the QG list.
        await page.locator('button[data-list=RANKED]').click(); await page.locator('[data-empty=NO_RANKING]').waitFor();
        assert.match(await page.locator('[data-empty=NO_RANKING]').innerText(), /가격 연결 전: QGV 순위 없음/);
        assert.equal(await page.locator('[data-empty=NO_RANKING] button:has-text("가격 불러오기")').isDisabled(), true, 'the mirrored price button is off');
        await common(page);
        await page.locator('[data-k=qg-list]').click(); await page.locator('[data-lb-table][data-list=QG_REFERENCE]').waitFor();
        const qg = await page.evaluate(() => window.__qt.drawn().map((d) => d.c.rank));
        assert.ok(qg.length > 1 && qg.every((t) => /^참고 \d+$/.test(t)), 'the QG list: every rank cell is 참고 n');
        assert.deepEqual((await page.evaluate(() => window.__qt.check())).bad.filter((b) => !/ v: /.test(b)), [], 'QG list values from the layer (V reads its reason)');
        const mainText = await page.locator('main').innerText();
        assert.doesNotMatch(mainText, /\d+ \/ 0|참고 null|undefined|NaN/, 'no "x / 0", no "참고 null"');
        await page.locator('button[data-list=ALL]').click(); await page.locator('[data-lb-table][data-list=ALL]').waitFor();

        // ---- 2.1.2 sort (default state, list 전체)
        const sortCheck = async (label) => {
          tag('sort ' + label);
          const res = await page.evaluate(async () => {
            const I = window.IS2, Q = I.qgv, H = I.qgvLive.helpers, pg = await Q.page(), qt = window.__qt, sel = document.querySelector('#lb-sort'), out = {};
            const ranks0 = Object.fromEntries(qt.drawn().map((d) => [d.id, d.c.rank]));
            const listName = document.querySelector('[data-lb-table]').dataset.list, scoped = Q.rows(pg, { scope: 'UNIVERSE' }).filter((r) => listName === 'ALL' || qt.listOf(r) === listName);
            const ur = I.prices.universeRanks(), cap = (r) => { if (!ur || ur.state !== 'READY') return null; const e = I.prices.rankFor({ company_id: r.id, ticker: r.ticker }); return Number.isInteger(e.rank) ? e.rank : null; };
            const wait = () => new Promise((r) => setTimeout(r, 30));
            for (const o of [...sel.options]) {
              if (o.disabled) { out[o.value] = { disabled: true }; continue; }
              const s2 = document.querySelector('#lb-sort'); s2.value = o.value; s2.dispatchEvent(new Event('change', { bubbles: true })); await wait();
              const d = qt.drawn(), th = document.querySelector('[data-lb-table] thead th[aria-sort]');
              const want = o.value === 'name' ? null : H.sortRows(scoped, o.value, { cap, interests: [] }).slice(0, d.length).map((r) => r.id);
              out[o.value] = { ids: d.map((x) => x.id), want, rankSame: d.every((x) => !(x.id in ranks0) || ranks0[x.id] === x.c.rank), sortAttr: th ? th.querySelector('[data-col]').dataset.col + ':' + th.getAttribute('aria-sort') : null,
                select: document.querySelector('#lb-sort').value, dirOff: document.querySelector('[data-k=dir]').disabled, oneWay: !!document.querySelector('[data-one-way]'), titles: d.map((x) => x.title), tickers: d.map((x) => x.id) };
            }
            // Header button and select in sync; reset.
            document.querySelector('[data-k="th-q"]').click(); await wait(); const q1 = document.querySelector('#lb-sort').value; document.querySelector('[data-k="th-q"]').click(); await wait(); const q2 = document.querySelector('#lb-sort').value;
            document.querySelector('[data-k=reset]').click(); await wait();
            return { out, q1, q2, reset: document.querySelector('#lb-sort').value, n: Object.keys(ranks0).length,
              capOff: [...sel.options].filter((x) => x.value.startsWith('cap')).map((x) => x.disabled), favOff: [...sel.options].find((x) => x.value === 'favorites').disabled };
          });
          assert.ok(res.n > 1, label + ': rows drawn');
          for (const [id, r] of Object.entries(res.out)) {
            if (r.disabled) continue;
            assert.equal(r.select, id); assert.ok(r.rankSame, label + ' ' + id + ': rank texts unchanged');
            if (r.want) assert.deepEqual(r.ids, r.want, label + ' ' + id + ': the ported rule over the layer rows');
            const oneWay = ['ticker', 'name', 'favorites'].includes(id); assert.equal(r.dirOff, oneWay, id + ' toggle'); assert.equal(r.oneWay, oneWay);
          }
          const nm = res.out.name.titles; for (let i = 1; i < nm.length; i++) assert.ok(nm[i - 1].localeCompare(nm[i], 'ko') <= 0, 'name: by the shown title');
          assert.notDeepEqual(res.out.qgv.ids, res.out['qgv-asc'].ids, 'two directions differ'); assert.notDeepEqual(res.out['q-desc'].ids, res.out['g-desc'].ids);
          assert.equal(res.out.qgv.sortAttr, 'qgv:descending'); assert.equal(res.out['qgv-asc'].sortAttr, 'qgv:ascending'); assert.equal(res.out['asof-desc'].sortAttr, 'asof:descending'); assert.equal(res.out.ticker.sortAttr, null);
          assert.deepEqual([res.q1, res.q2], ['q-desc', 'q-asc'], 'the header button drives the select'); assert.equal(res.reset, 'qgv');
          return res;
        };
        const s0 = await sortCheck('default');
        assert.deepEqual(s0.capOff, [true, true], 'cap options off before a Universe read'); assert.equal(s0.favOff, true, '관심기업 우선 off without interests');
        // NA last both ways (Q and V columns on the drawn rows).
        for (const id of ['q-desc', 'q-asc', 'v-desc']) { const vals = await page.evaluate(async (sid) => { const s2 = document.querySelector('#lb-sort'); s2.value = sid; s2.dispatchEvent(new Event('change', { bubbles: true })); await new Promise((r) => setTimeout(r, 30)); return window.__qt.drawn().map((d) => d.c[sid[0]]); }, id);
          const firstNa = vals.findIndex((x) => x.startsWith('NA')); assert.ok(firstNa === -1 || vals.slice(firstNa).every((x) => x.startsWith('NA')), id + ': NA last'); }
        await page.locator('[data-k=reset]').click();
        const pop = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page(), recs = I.data.get('sec-qgv2.json').records; let E = 0;
          for (const r of Object.values(recs)) if (r && r.in_cross_section === true && ['LIVE', 'STALE'].includes(r.state) && r.calc_version_mismatch !== true && r.identity_withdrawn !== true) E++;
          const box = (k) => document.querySelector('[data-pop=' + k + ']'); return { E, of: pg.rows[0].rank.of, ev: box('EVALUATION').textContent, rk: box('RANK').textContent, el: box('ELIGIBLE').textContent, elNa: box('ELIGIBLE').dataset.na, fl: box('FILTER').textContent, drawn: window.__qt.drawn().length }; });
        assert.ok(pop.ev.endsWith('Universe504 점수 행 ' + pop.E)); assert.ok(pop.rk.endsWith('종합점수 + V 있는 행 ' + pop.of));
        assert.doesNotMatch(pop.el, /\d/, 'no ranking: the eligibility box has no digit'); assert.ok(pop.elNa); assert.doesNotMatch(pop.el, /통과/);
        assert.ok(pop.fl.includes('표시 ' + pop.drawn + ' · 순위 다시 매기지 않음'), 'screen filter box = the drawn count');
        await common(page);

        // ---- 2.1.3 filters
        tag('filters');
        const f = await page.evaluate(async () => {
          const wait = () => new Promise((r) => setTimeout(r, 30)), set = async (sel, v) => { const e = document.querySelector(sel); e.value = v; e.dispatchEvent(new Event('change', { bubbles: true })); await wait(); };
          const qt = window.__qt, ranks0 = Object.fromEntries(qt.drawn().map((d) => [d.id, d.c.rank])), all = qt.drawn().length;
          await set('#lb-f-industry', 'manufacturing_industrial_tech'); const a = qt.drawn(), count = document.querySelector('[data-filter-count]').textContent;
          await set('#lb-f-industry', 'NOT_AVAILABLE'); const b = qt.drawn().map((d) => d.id); await set('#lb-f-industry', '');
          await set('#lb-f-sic4', 'NOT_AVAILABLE'); const c = qt.drawn().map((d) => d.c.sic); await set('#lb-f-sic4', '');
          await set('#lb-f-sic4', '7372'); const d7372 = qt.drawn().map((d) => d.c.sic);
          const types = [...document.querySelectorAll('#lb-f-type option')].map((o) => o.textContent), states = [...document.querySelectorAll('#lb-f-state option')].map((o) => o.textContent);
          document.querySelector('[data-k=clear-filters-2]').click(); await wait();
          return { all, a: a.map((x) => x.id), aRankSame: a.every((x) => ranks0[x.id] === undefined || ranks0[x.id] === x.c.rank), count, b, c, d7372, types, states, after: qt.drawn().length, sicCodes: [...document.querySelectorAll('#lb-f-sic4 option')].map((o) => o.value) };
        });
        assert.ok(f.all > 1 && f.a.length >= 1 && f.a.length < f.all, 'the industry filter matches some and hides some');
        assert.ok(f.aRankSame, 'filters never re-rank'); assert.match(f.count, /^표시 \d+개 · 순위 기준 \d+개 중$/);
        assert.ok(f.a.includes('nvda'), 'nvda filed under its TARGET classification group'); assert.ok(!f.b.includes('nvda'), 'nvda not under 업종군 자료 없음');
        assert.ok(f.c.length >= 1 && f.c.every((t) => t === 'NA분류 자료 없음'), '분류 자료 없음 = only null-SIC rows');
        assert.ok(f.d7372.length >= 1 && f.d7372.every((t) => t === '7372'));
        const T = R.requireOld('type-config-defaults.js');
        assert.deepEqual(f.types, ['전체', ...T.types.map((t) => t.name + (t.rule.kind === 'unresolved' ? ' · 규칙 결정 대기' : '')), '미분류', '유형 자료 없음'], 'type options = type_config names');
        assert.ok(f.states.includes('해당 없음 · 결정 대기 (FIN-NA-CODE)'));
        assert.equal(f.after, f.all, '필터 모두 풀기 restores');
        if (phone) {
          const panel = page.locator('[data-k=panel]');
          assert.equal(await panel.getAttribute('aria-expanded'), 'false'); assert.equal(await page.locator('#lb-filters').isVisible(), false);
          await panel.click(); assert.equal(await page.locator('[data-k=panel]').getAttribute('aria-expanded'), 'true'); assert.equal(await page.locator('#lb-filters').isVisible(), true);
          await common(page, phase + ' panel open');
          await page.locator('[data-k=panel]').click(); assert.equal(await page.locator('#lb-filters').isVisible(), false);
        }

        // ---- 2.1.4 before load, 2.1.6 official badges, 2.1.7 empty state, synthetic clicks
        tag('returns before load');
        const r0 = await page.evaluate(() => ({ cells: window.__qt.drawn().map((d) => d.c.ret), wait: [...document.querySelectorAll('button[data-period]')].filter((b) => b.disabled).map((b) => b.dataset.period),
          load: document.querySelector('[data-k=load-tabs]').disabled, why: (document.querySelector('[data-k=load-tabs]').parentElement.querySelector('[data-reason]') || {}).dataset }));
        assert.ok(r0.cells.length > 1 && r0.cells.every((t) => t === '— 가격 불러오기 전'), 'every return cell: the PRICE_TABS_NOT_LOADED text');
        assert.deepEqual(r0.wait, ['60D', '120D', 'YTD', '1Y']); assert.equal(r0.load, true); assert.equal(r0.why.reason, 'PRICE_TABS_OFF');
        const badges = await page.evaluate(async () => { const I = window.IS2, S = window.QgvScores, pg = await I.qgv.page(), el = document.querySelector('[data-badges]');
          const want = S.provenanceAttrs(S.provenance({ kind: 'QGV', profile: { preset: pg.preset, gate: pg.gate, id: pg.profile_id }, priced: false }));
          return { got: Object.fromEntries(Object.keys(want).map((k) => [k, el.getAttribute(k)])), want, text: [...el.querySelectorAll('[data-badge] .hl')].map((x) => x.textContent), vko: pg.v_source.ko,
            preview: document.querySelector('[data-k=mode-preview]').disabled, why: !!document.querySelector('[data-preview-off]') }; });
        assert.deepEqual(badges.got, badges.want, 'official badges: provenanceAttrs of the page profile, no prices');
        assert.deepEqual(badges.text, ['공식 가중치', '가격 없음', '기기 계산', badges.vko]);
        assert.equal(badges.preview, true, 'no saved profile: the preview chip is off'); assert.ok(badges.why);
        assert.equal(await page.locator('[data-empty=NO_MODEL]').count(), 1, '2.1.7 without prices: the empty state');
        assert.deepEqual(await page.locator('[data-lb="2.1.7"] a.lk').evaluateAll((n) => n.map((a) => a.getAttribute('href'))), ['#/portfolio', '#/detail/target-v1']);
        tag('synthetic clicks');
        const at1 = seen.requests.length;
        const syn = await page.evaluate(async () => { const out = []; for (const b of document.querySelectorAll('[data-qgv-band] .conn button')) { b.click(); b.dispatchEvent(new MouseEvent('click', { bubbles: true })); }
          await new Promise((r) => setTimeout(r, 100)); for (const e of document.querySelectorAll('[data-qgv-band] [data-reason]')) out.push(e.dataset.reason); return { out, gis: window.__gis, blocked: window.IS2.action.blocked() }; });
        assert.deepEqual([syn.gis, syn.blocked], [0, 0], 'synthetic clicks start nothing');
        assert.ok(syn.out.includes('CLICK_REQUIRED'), 'the refusal is kept as a code attribute');
        assert.match(await page.locator('[data-qgv-band]').innerText(), /실행하지 못했습니다/, 'only the fixed fallback text is shown');
        assert.deepEqual(seen.requests.slice(at1).filter((u) => new URL(u).origin !== s.origin), [], 'no request from synthetic clicks');
        await common(page);
        // A fresh load of #/qgv reads only CORE + catalog + names.
        tag('fresh load');
        const at2 = seen.requests.length; await page.reload(); await ready(page); await tableReady(page); await settle(page);
        assert.deepEqual(dataNames(seen.requests.slice(at2)).filter((n) => !QGV_READS.includes(n)), [], 'a fresh load of #/qgv reads only CORE + catalog + names');
        assert.ok(!dataNames(seen.requests).includes('sec-universe-shares.json'), 'no share counts on open');
        await common(page);
        if (phone) await page.screenshot({ path: path.join(require('node:os').tmpdir(), 'web-app-qgv-390.png'), fullPage: true });
        tag('boundaries (no click)');
        await boundaries(ctx);
        assert.equal(await page.evaluate(() => window.IS2.action.blocked()), 0);
        await ctx.context.close();
      }

      // ================================================================ clicks: sign-in and the Universe read on the band
      {
        tag('clicks');
        const ctx = await open(), { page, seen, rec } = ctx;
        s.fixture('sec-universe-shares.json', { json: SHARES_FILE });
        await page.goto(s.base + '#/qgv'); await ready(page); await tableReady(page);
        await testButtons(page);
        // The load button's reason before a sign-in, with the flag off: PRICE_TABS_OFF.
        assert.equal(await testClick(page, 'source'), 'OK');
        const b = (i) => page.locator('[data-qgv-band] .conn button').nth(i);
        assert.deepEqual([await b(0).isDisabled(), await b(1).isDisabled(), await b(2).isDisabled()], [false, true, true], '① on after ready; ② and ③ wait');
        await b(0).click(); await page.waitForFunction(() => { const x = document.querySelectorAll('[data-qgv-band] .conn button')[1]; return x && !x.disabled; });
        await b(1).click(); await page.waitForFunction(() => { const x = document.querySelectorAll('[data-qgv-band] .conn button')[2]; return x && !x.disabled; });
        assert.equal(await page.locator('[data-qgv-conn]').textContent(), '로그인됨');
        assert.equal(await page.locator('[data-lb="2.1.4"] .load-row [data-reason]').getAttribute('data-reason'), 'PRICE_TABS_OFF', 'signed in, store flag off: PRICE_TABS_OFF');
        assert.equal(await page.locator('[data-lb="2.1.4"] .load-row a.lk').getAttribute('href'), '#/detail/settings');
        // ③ by Enter on the focused button: exactly one read.
        await b(2).focus(); await page.keyboard.press('Enter');
        await page.waitForFunction(() => document.querySelector('[data-lb-table] tbody tr[data-row] [data-ram-price]'), null, { timeout: 20000 });
        await settle(page);
        assert.equal(rec.counts.values, 1, 'Enter on the focused ③ started exactly one Universe read');
        const after = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page(); return { of: pg.rows[0].rank.of, ranked: pg.rows.filter((r) => Number.isInteger(r.rank.official)).length, connected: pg.price_basis.connected, line: document.querySelector('[data-qgv-band] [data-qgv-status]').textContent }; });
        assert.ok(after.of > 1 && after.ranked > 1 && after.connected, 'V and ranks from the read'); assert.match(after.line, /읽은 뒤: 읽은 시각 \d\d:\d\d · RAM에만 · 새로고침하면 사라짐/);
        const v1 = await page.evaluate(() => window.__qt.check()); assert.ok(v1.n > 1); assert.deepEqual(v1.bad, [], 'after the read every drawn cell equals the layer row');
        const m3 = await page.evaluate(() => ({ attr: [...document.querySelectorAll('[data-lb-table] *')].some((e) => [...e.attributes].some((a) => /#\d/.test(a.value))), cells: [...document.querySelectorAll('[data-cell=m3]')].map((td) => ({ ram: !!td.querySelector('[data-ram-price]'), text: td.textContent })) }));
        assert.ok(m3.cells.some((c) => c.ram), 'M3 ranks drawn'); for (const c of m3.cells) if (/#\d/.test(c.text)) assert.ok(c.ram, 'an M3 rank only inside [data-ram-price]'); assert.equal(m3.attr, false, 'no M3 rank in an attribute');
        assert.equal(await page.locator('[data-m3-coverage]').count(), 1);
        await site.assertRamOnly(page, SENTINELS, phase);
        const badges = await page.evaluate(async () => { const I = window.IS2, S = window.QgvScores, pg = await I.qgv.page(), el = document.querySelector('[data-badges]');
          const want = S.provenanceAttrs(S.provenance({ kind: 'QGV', profile: { preset: pg.preset, gate: pg.gate, id: pg.profile_id }, priced: true }));
          return { got: Object.fromEntries(Object.keys(want).map((k) => [k, el.getAttribute(k)])), want, price: el.querySelector('[data-badge=prices] .hl').textContent }; });
        assert.deepEqual(badges.got, badges.want); assert.equal(badges.price, '이 기기 가격');
        // 2.1.2 again on 종합 순위.
        await page.locator('button[data-list=RANKED]').click(); await page.locator('[data-lb-table][data-list=RANKED]').waitFor();
        const ranked = await page.evaluate(() => window.__qt.drawn().map((d) => d.c.rank)); assert.ok(ranked.length > 1 && ranked.every((t) => /^\d+$/.test(t)), '종합 순위 rows ranked');
        assert.equal(await page.locator('[data-cell=vfactors]').count(), ranked.length, 'V 요인 column on 종합 순위');
        tag('sort after prices');
        const sorted = await (async () => { const res = await page.evaluate(() => [...document.querySelectorAll('#lb-sort option')].filter((o) => o.value.startsWith('cap')).map((o) => o.disabled)); assert.deepEqual(res, [false, false], 'cap options on after the read'); })();
        void sorted;
        // the sortCheck of the default context, on this list (cap included)
        {
          const res = await page.evaluate(async () => {
            const I = window.IS2, Q = I.qgv, H = I.qgvLive.helpers, pg = await Q.page(), qt = window.__qt, out = {}, ranks0 = Object.fromEntries(qt.drawn().map((d) => [d.id, d.c.rank]));
            const scoped = Q.rows(pg, { scope: 'UNIVERSE' }).filter((r) => qt.listOf(r) === 'RANKED'), cap = (r) => { const e = I.prices.rankFor({ company_id: r.id, ticker: r.ticker }); return Number.isInteger(e.rank) ? e.rank : null; };
            for (const o of [...document.querySelector('#lb-sort').options]) { if (o.disabled) continue; const s2 = document.querySelector('#lb-sort'); s2.value = o.value; s2.dispatchEvent(new Event('change', { bubbles: true })); await new Promise((r) => setTimeout(r, 30));
              const d = qt.drawn(); out[o.value] = { ids: d.map((x) => x.id), want: o.value === 'name' ? null : H.sortRows(scoped, o.value, { cap }).slice(0, d.length).map((r) => r.id), same: d.every((x) => ranks0[x.id] === x.c.rank) }; }
            document.querySelector('[data-k=reset]').click(); await new Promise((r) => setTimeout(r, 30));
            const tiers = qt.drawn().map((d) => d.c.rank); return { out, tiers, n: Object.keys(ranks0).length };
          });
          assert.ok(res.n > 1);
          for (const [id, r] of Object.entries(res.out)) { assert.ok(r.same, id + ': rank texts unchanged'); if (r.want) assert.deepEqual(r.ids, r.want, id + ' on 종합 순위'); }
          assert.notDeepEqual(res.out['cap-desc'].ids, res.out['cap-asc'].ids, 'cap sorts both ways');
          assert.deepEqual(res.tiers.map(Number), [...res.tiers.map(Number)].sort((a, b) => a - b), 'QGV 높은 순 = rank order');
        }
        await page.locator('button[data-list=ALL]').click(); await page.locator('[data-lb-table][data-list=ALL]').waitFor();
        const tiers = await page.evaluate(() => window.__qt.drawn().map((d) => (/^\d+$/.test(d.c.rank) ? 0 : /^참고/.test(d.c.rank) ? 1 : 2)));
        assert.deepEqual(tiers, [...tiers].sort((a, b) => a - b), 'ranked, then 참고, then no total: never interleaved');
        // Population boxes and 2.1.7 from IS2.qgv.model.
        tag('model');
        const model = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page(), M = I.qgv.model(pg), q = (s2) => document.querySelector(s2);
          const top = pg.rows.filter((r) => Number.isInteger(r.rank.official)).sort((a, b) => a.rank.official - b.rank.official).slice(0, 15).map((r) => r.id);
          return { M: JSON.parse(JSON.stringify(M)), el: q('[data-pop=ELIGIBLE]').textContent, picks: [...document.querySelectorAll('[data-pick]')].map((li) => li.dataset.pick), top, tops: [...document.querySelectorAll('[data-top]')].map((li) => ({ id: li.dataset.top, text: li.textContent })),
            excl: q('[data-model-excluded]').textContent, skipped: q('[data-model-skipped]').textContent, unknown: (q('[data-model-unknown]') || {}).textContent || null, status: q('[data-model-status]').textContent, text: q('[data-lb="2.1.7"]').innerText }; });
        const M = model.M;
        assert.ok(M && M.sets.N15.selected.length >= 1, 'the N15 set has a row');
        assert.ok(model.el.includes('N20 선정에서 살펴본 ' + M.checked + '행 · 자격 제외 ' + (M.excluded.AXES_50 + M.excluded.VALUE_TRAP_GATE + M.excluded.FINANCIAL_SAFETY + M.excluded.FINANCIAL_SAFETY_NA) + ' · 한도로 건너뜀 ' + (M.excluded.SUBGROUP_MAX_4 + M.sets.N20.skipped.SECTOR_GROUP_MAX_40)), 'eligibility box from the model');
        assert.doesNotMatch(model.el, /통과/);
        if (!phone) {
          assert.deepEqual(model.picks, M.sets.N15.selected.map((e) => e.id), 'N15 = model.sets.N15.selected');
          assert.deepEqual(model.tops.map((t) => t.id), model.top, 'top-N = the first 15 ranked rows');
          const chosen = new Set(M.sets.N15.selected.map((e) => e.id)), capped = new Set(M.sets.N15.group_capped.map((c) => c.id));
          for (const t of model.tops) { if (chosen.has(t.id)) continue; assert.match(t.text, capped.has(t.id) ? /업종 묶음 40% 한도로 건너뜀 · / : /— 후보 아님$/, t.id); }
        }
        assert.equal(model.excl, '제외: 축 50% ' + M.excluded.AXES_50 + ' · 가치 함정 관문 ' + M.excluded.VALUE_TRAP_GATE + ' · 재무 안전 미달 ' + M.excluded.FINANCIAL_SAFETY + ' · 재무 안전 지표 NA ' + M.excluded.FINANCIAL_SAFETY_NA + ' · 하위 묶음 상한 ' + M.excluded.SUBGROUP_MAX_4);
        assert.equal(model.skipped, '업종 묶음 40% 한도로 건너뜀 ' + M.sets.N15.skipped.SECTOR_GROUP_MAX_40);
        assert.equal(model.unknown, '하위 묶음 미정 ' + M.unknown.subgroup + '종목 · 상한 미적용 · 잠정 · 결정 대기');
        assert.ok(model.status.startsWith('N15 ' + M.sets.N15.selected.length + '/15 · 각 ' + M.sets.N15.weight_pct.toFixed(2) + '% · '));
        const ML = await page.evaluate(() => Object.values(window.QgvScores.MODEL_LABEL).map((x) => x[0]));
        for (const t of ML) assert.ok(!model.text.includes(t), 'no MODEL_LABEL rule text: ' + t);
        await common(page);
        // 2.1.6 preview from a saved profile (a real click on a test-only button).
        tag('preview');
        const keep = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page(); window.__pg2 = pg; return { profile: I.qgv.profile(), pop: document.querySelector('.pop').textContent, model: document.querySelector('[data-lb="2.1.7"]').textContent }; });
        assert.equal(await testClick(page, 'weights'), 'OK');
        await page.waitForFunction(() => { const b = document.querySelector('[data-k=mode-preview]'); return b && !b.disabled; });
        await page.locator('[data-k=mode-preview]').click(); await page.locator('[data-list-lock=PREVIEW]').waitFor();
        const pv = await page.evaluate(async () => { const I = window.IS2, S = window.QgvScores, pg = await I.qgv.page(), p = I.store.weights().value.profiles[0], prev = I.qgv.preview(pg, p.weights, { typeWeights: p.type_weights !== false, gate: p.gate === false ? false : true });
          const el = document.querySelector('[data-badges]'), want = S.provenanceAttrs(S.provenance({ kind: 'QGV', profile: { weights: p.weights, gate: p.gate === false ? false : true, id: prev.profile_id }, priced: true }));
          const check = await window.__qt.check({ preview: prev });
          return { same: pg === window.__pg2, profile: I.qgv.profile(), got: Object.fromEntries(Object.keys(want).map((k) => [k, el.getAttribute(k)])), want, weight: el.querySelector('[data-badge=weights] .hl').textContent,
            head: document.querySelector('[data-lb-table] thead th .sub').textContent, wantHead: I.qgv.rankLabel(prev) + ' · ' + (prev.v_weight_zero ? S.PERSONAL_V0_LABEL[0] : S.PERSONAL_LABEL[0]), check,
            pop: document.querySelector('.pop').textContent, model: document.querySelector('[data-lb="2.1.7"]').textContent, lists: [...document.querySelectorAll('button[data-list]')].map((b) => b.disabled) }; });
        assert.equal(pv.same, true, 'IS2.qgv.page() stays the same object'); assert.deepEqual(pv.profile, keep.profile, 'IS2.qgv.profile() unchanged');
        assert.deepEqual(pv.got, pv.want, 'preview badges: the preview provenance'); assert.equal(pv.weight, '개인 가중치');
        assert.equal(pv.head, pv.wantHead, 'preview rank label'); assert.ok(pv.check.n > 1); assert.deepEqual(pv.check.bad, [], 'preview rows from the preview result');
        assert.equal(pv.pop, keep.pop, 'population boxes unchanged'); assert.equal(pv.model, keep.model, '2.1.7 unchanged'); assert.deepEqual(pv.lists, [false, true, true, true, true]);
        assert.doesNotMatch(await page.locator('main').innerText(), /균형형\s*(=|:|\()\s*Q ?34/);
        await common(page);
        await page.locator('[data-k=mode-official]').click(); await page.locator('[data-list-lock=PREVIEW]').waitFor({ state: 'detached' });
        tag('clicks boundaries');
        const st = await site.storage(page);
        assert.deepEqual(site.leaks([...Object.values(st.localItems), ...Object.values(st.sessionItems), ...rec.log.map((r) => r.url + ' ' + r.body), ...seen.errors], SENTINELS), [], 'no sentinel in storage, requests or console');
        const KEYS = await page.evaluate(() => window.IS2.store.KEYS);
        assert.deepEqual(st.idbNames, ['investment-device-actual-v1'], 'the prepare click saved Google on (the old sign-in click did)');
        await boundaries(ctx, { stored: [KEYS.UNIVERSE_SOURCE, KEYS.PROFILES_V2], outside: [GIS_CLIENT, GIS_STYLE, SHEETS + '/v4/spreadsheets/' + SHEET_ID] });
        assert.equal(await page.evaluate(() => window.IS2.action.blocked()), 0);
        // After a reload the RAM values are gone: V and ranks NA again.
        await page.reload(); await ready(page); await tableReady(page);
        const gone = await page.evaluate(async () => { const pg = await window.IS2.qgv.page(); return { v: pg.rows.filter((r) => r.score.v !== null).length, m3: document.querySelectorAll('[data-ram-price]').length }; });
        assert.deepEqual(gone, { v: 0, m3: 0 }, 'after a reload V and M3 are NA again');
        s.fixture('sec-universe-shares.json', null);
        await ctx.context.close();
      }

      // ================================================================ a returning user's price tabs: period returns
      {
        tag('returns');
        const ctx = await open({ tabs: true, flag: true }), { page, rec } = ctx;
        await page.goto(s.base + '#/qgv'); await ready(page); await tableReady(page);
        const reason = () => page.locator('[data-lb="2.1.4"] .load-row [data-reason]').getAttribute('data-reason');
        assert.equal(await reason(), 'AUTH_REQUIRED', 'flag on, not signed in: AUTH_REQUIRED');
        await testButtons(page);
        const b = (i) => page.locator('[data-qgv-band] .conn button').nth(i);
        await b(0).click(); await page.waitForFunction(() => { const x = document.querySelectorAll('[data-qgv-band] .conn button')[1]; return x && !x.disabled; });
        await b(1).click(); await page.locator('[data-qgv-conn]:has-text("로그인됨")').waitFor();
        await settle(page);
        assert.equal(await reason(), 'SHEET_NOT_CONNECTED', 'signed in without a price sheet: SHEET_NOT_CONNECTED');
        assert.equal(await testClick(page, 'sheet'), 'OK');
        await page.waitForFunction(() => { const x = document.querySelector('[data-k=load-tabs]'); return x && !x.disabled; });
        const before = rec.log.length;
        await page.locator('[data-k=load-tabs]').click();
        await page.waitForFunction(() => document.querySelector('[data-cell=ret] [data-ram-price]'), null, { timeout: 20000 });
        const sent = rec.log.slice(before).filter((r) => new URL(r.url).origin !== s.origin);
        assert.ok(sent.length > 0 && sent.every((r) => r.method === 'GET' && r.url.startsWith(SHEETS + '/v4/spreadsheets/' + SHEET_ID)), 'the click sent only Sheets GETs to the saved sheet');
        const rows = await page.evaluate(() => window.__qt.drawn().map((d) => ({ id: d.id, ret: d.c.ret, rank: d.c.rank, cls: (document.querySelector('tr[data-row="' + CSS.escape(d.id) + '"] [data-cell=ret] [data-ram-price]') || {}).className || null })));
        const symbolOf = { nvda: 'NVDA', 'NYSE:AFL': 'AFL', 'NYSE:AES': 'AES' }, w = RB.periodWindow(SESSIONS, SESSIONS.at(-1), '1D');
        let ok = 0;
        for (const r of rows) {
          const sym = symbolOf[r.id];
          if (!sym) { assert.match(r.ret, /^— (미산출 · 근거: |가격 입력 필요|식별)/, r.id + ' NA with its reason'); continue; }
          const x = RB.priceIndex(CLOSES[sym], {}, w, 'USD'), p = Math.round(x.return * 1000) / 10, want = (p > 0 ? '+' : p < 0 ? '\u2212' : '') + FORMATS.fmt(Math.abs(p)) + '%';
          assert.equal(r.ret, want + ' 분할 미확인', r.id + ' return = ReportBenchmarks.priceIndex, with the 분할 미확인 note'); assert.equal(r.cls, p > 0 ? 'ret up' : p < 0 ? 'ret down' : 'ret'); ok++;
        }
        assert.ok(ok >= 2, 'returns drawn for the tab symbols');
        await site.assertRamOnly(page, CLOSE_SENTINELS, phase);
        assert.equal(await page.locator('[data-k=ret-sort]').isDisabled(), false);
        await page.locator('[data-k=ret-sort]').click(); await page.locator('[data-ret-status]').waitFor();
        const ordered = await page.evaluate(() => window.__qt.drawn().map((d) => ({ id: d.id, ret: d.c.ret, rank: d.c.rank })));
        const ranks = Object.fromEntries(rows.map((r) => [r.id, r.rank]));
        assert.ok(ordered.slice(0, ok).every((r) => r.ret.includes('%')), 'rows with a return first');
        for (const r of ordered) if (r.id in ranks) assert.equal(r.rank, ranks[r.id], r.id + ' rank unchanged by the return order');
        const vals = ordered.slice(0, ok).map((r) => Number(r.ret.replace('\u2212', '-').replace(/[^\d.-]/g, ''))); assert.deepEqual(vals, [...vals].sort((a, b) => b - a), 'high first');
        assert.equal(await page.locator('[data-lb-table] thead th[aria-sort] [data-col]').getAttribute('data-col'), 'ret');
        await page.locator('button[data-period="5D"]').click(); await page.waitForFunction(() => document.querySelector('[data-lb-table] thead [data-col=ret]').textContent.startsWith('수익률 5D'));
        await page.waitForFunction(() => document.querySelector('[data-cell=ret] [data-ram-price]'));
        await common(page);
        const KEYS = await page.evaluate(() => window.IS2.store.KEYS), st = await site.storage(page);
        assert.deepEqual(site.leaks([...Object.values(st.localItems), ...rec.log.map((r) => r.url + ' ' + r.body), ...ctx.seen.errors], CLOSE_SENTINELS), [], 'no close in storage, requests or console');
        await boundaries(ctx, { stored: [KEYS.PRICE_STORE_ENABLED, KEYS.SHEET_SOURCE], outside: [GIS_CLIENT, GIS_STYLE, SHEETS + '/v4/spreadsheets/' + SHEET_ID] });
        assert.equal(await page.evaluate(() => window.IS2.action.blocked()), 0);
        await page.reload(); await ready(page); await tableReady(page);
        const reloaded = await page.evaluate(() => window.__qt.drawn().map((d) => d.c.ret));
        assert.ok(reloaded.every((t) => t === '— 가격 불러오기 전'), 'after a reload the returns are NA again');
        await ctx.context.close();
      }
    }

    // ================================================================ failures (1440)
    phase = 'failures';
    for (const [label, fixture, state, reason, title] of [['404', { status: 404 }, 'NO_DATA', 'SEC_QGV2_NOT_PUBLISHED', '화면 상태 · 미게시'], ['invalid', { body: '[]', type: 'application/json' }, 'READ_FAILED', 'SEC_QGV2_INVALID', '화면 상태 · 읽기 실패']]) {
      phase = 'failure ' + label;
      s.fixture('sec-qgv2.json', fixture);
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } }); await context.clock.setFixedTime(new Date(NOW)); await context.addInitScript(HELPERS);
      const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: [...UNPUBLISHED, 'sec-qgv2.json'] });
      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready); await page.locator('[data-page-state]').first().waitFor();
      const cards = await page.evaluate(() => [...document.querySelectorAll('[data-page-state]')].map((c) => ({ state: c.dataset.pageState, na: c.dataset.na, text: c.textContent })));
      const want = await page.evaluate((r) => window.IS2.qgv.reasonText(r), reason);
      assert.equal(cards.length, 7); for (const c of cards) { assert.equal(c.state, state); assert.equal(c.na, reason); assert.equal(c.text, title + want); assert.doesNotMatch(c.text, /\d/); }
      assert.equal(await page.locator('[data-lb-table]').count(), 0, 'no table');
      assert.doesNotMatch(await page.locator('main').innerText(), CODE_TEXT);
      assert.deepEqual(seen.errors, []);
      await context.close();
    }
    s.fixture('sec-qgv2.json', { json: QGV2 });
    phase = 'failure logic file';
    {
      const context = await browser.newContext({ viewport: { width: 390, height: 844 } }), page = await context.newPage(), errors = [];
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('**/screen-qgv-live.js', (route) => route.fulfill({ status: 404, contentType: 'text/plain', body: 'gone' }));
      await page.goto(s.base + '#/qgv', { waitUntil: 'domcontentloaded' }); await page.locator('[data-na=LOADER_FAILED]').first().waitFor();
      const r = await page.evaluate(() => ({ state: window.IS2.loadState(), lines: [...document.querySelectorAll('[data-lb] [data-na=LOADER_FAILED]')].map((x) => x.textContent), notices: document.querySelectorAll('[data-load-failed]').length,
        enabled: document.querySelectorAll('main button:not([disabled])').length }));
      assert.equal(r.state, 'FAILED'); assert.equal(r.notices, 1, 'exactly one shell notice'); assert.equal(r.enabled, 0, 'buttons stay disabled');
      assert.deepEqual(r.lines, Array(7).fill('층을 불러오지 못해 리더보드를 그리지 못했습니다'));
      assert.deepEqual(errors, [], 'no pageerror');
      await context.close();
    }
    phase = 'leave while computing';
    {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } }); await context.clock.setFixedTime(new Date(NOW));
      const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      await page.goto(s.base + '#/macro'); await page.evaluate(() => window.IS2.ready);
      await page.evaluate(() => { location.hash = '#/qgv'; setTimeout(() => { location.hash = '#/news'; }, 0); });
      await page.locator('main[data-route=news]').waitFor(); await page.evaluate(() => new Promise((r) => setTimeout(r, 1500)));
      assert.deepEqual(seen.errors, [], 'no ABORTED or other console error');
      await context.close();
    }
    console.log('web app qgv: before ready, layer values, scope / lists, sort and filters never re-rank, click-only prices, M3 and returns in RAM, model, preview, failures and boundaries ok at 1440 and 390');
  } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; });
