'use strict';
// Leaderboard table trial runner (development only; NOT a CI test, NOT listed in ci_*_tests.txt, nothing here is shipped).
// Compares the shipped QGV leaderboard table (web_app/screen-qgv-live.js) with Tabulator on the same rows, at 390×844 (CPU ×4,
// as web_app_first_paint_browser_test.js) and 1440×1000. Results doc: implementation/docs/frontend_v2/LEADERBOARD_TABLE_TRIAL_20261105.md.
//
//   TABULATOR_DIR=<scratch>/tools-tabulator/node_modules/tabulator-tables \
//   NODE_PATH=<playwright 1.58.2 node_modules> PLAYWRIGHT_BROWSERS_PATH=<browsers> node implementation/tools/leaderboard_tabulator_trial/run_trial.js
//   (optional: TRIAL_OUT=<dir for results.json>, default a new temp dir; TRIAL_RUNS=5)
//
// Tabulator is never installed into the repository: TABULATOR_DIR points at a scratch npm install (tabulator-tables 6.7.1, MIT,
// `npm i --ignore-scripts`; the package has no install scripts and no dependencies). Its two dist files are checked against the
// pinned SHA-256 below and copied into a temp folder served by this runner, with the trial page, the app's CSS and two web_app
// scripts (core.js, screen-qgv-live.js, unchanged). The page carries the app's own CSP (read from web_app/index.html).
//  A. The real app (tools/web_app_test_site.js build, synthetic fixtures qgv_v2_fixture strictPayload + the classification and
//     the synthetic central V publication, as web_app_qgv_browser_test.js): #/qgv open → first table row, header sort and the
//     업종군 filter response of the shipped code, [style] / CSP counts; the layer's Universe504 rows are dumped (display fields
//     only) for B, and the shipped table's first 50 rows are compared with the trial's existing renderer on the same rows.
//  B. The trial page per dataset (layer504, synthetic504, synthetic2000, synthetic10000) × mode (existing50, existingAll,
//     tabulator): first render, sort (Q / G header, alternating), filter (two industries, alternating), JS heap and DOM nodes
//     (CDP, after GC), rank texts unchanged after every sort and filter, NA never 0, [style] and CSP counts.
//  C. Keyboard / screen-reader / phone readability on synthetic504; D. sizes and static compatibility (lint RULES of
//     web_app_reuse_node_test.js applied to the Tabulator file, the Pages guard's content checks, loader NAME rule).
// Every value is synthetic. Requests outside 127.0.0.1 are aborted and counted. Nothing is stored or uploaded.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const zlib = require('node:zlib');
const { execFileSync } = require('node:child_process');
const TOOLS = path.join(__dirname, '..');
const R = require(path.join(TOOLS, 'web_app_reuse'));
const site = require(path.join(TOOLS, 'web_app_test_site'));
const F = require(path.join(TOOLS, 'qgv_v2_fixture.js'));
const SYN = require('./synthetic.js');

const PIN = { version: '6.7.1', license: 'MIT', 'tabulator.min.js': '4e218e8d309e9b704089e7808f5484f5257ea645ba4e4808c0ae13969500d55c', 'tabulator.min.css': 'ff598d8e961398e09a8e52ab21740e5ed952c84feebbdacec8f8a362dd3f73db' };
const RUNS = Number(process.env.TRIAL_RUNS || 5), CLICKS = 6;
const VIEWPORTS = [{ w: 1440, h: 1000, cpu: 1 }, { w: 390, h: 844, cpu: 4 }];
const MODES = ['existing50', 'existingAll', 'tabulator'];
const NOW = '2026-10-14T03:00:00.000Z';
const WEB_APP = path.join(R.ROOT, 'implementation/src/investment_system/product/web_app');
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const gz = (b) => zlib.gzipSync(b, { level: 9 }).length;
const median = (a) => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length ? (s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2) : null; };
const r1 = (x) => (x === null ? null : Math.round(x * 10) / 10);
const stat = (a) => ({ median: r1(median(a)), min: r1(Math.min(...a)), max: r1(Math.max(...a)), n: a.length });
const log = (...a) => process.stderr.write(a.join(' ') + '\n');

// ---------------------------------------------------------------- Tabulator files (pinned)
const TAB_DIR = process.env.TABULATOR_DIR;
if (!TAB_DIR) throw new Error('TABULATOR_DIR not set (a scratch npm install of tabulator-tables@' + PIN.version + ')');
const TAB_PKG = JSON.parse(fs.readFileSync(path.join(TAB_DIR, 'package.json'), 'utf8'));
assert.equal(TAB_PKG.version, PIN.version); assert.equal(TAB_PKG.license, PIN.license);
assert.deepEqual(Object.keys(TAB_PKG.dependencies || {}), [], 'no runtime dependencies');
for (const k of ['preinstall', 'install', 'postinstall', 'prepare']) assert.ok(!(TAB_PKG.scripts || {})[k] || k === 'prepare', 'no install script: ' + k);
const TAB = { js: fs.readFileSync(path.join(TAB_DIR, 'dist/js/tabulator.min.js')), css: fs.readFileSync(path.join(TAB_DIR, 'dist/css/tabulator.min.css')) };
assert.equal(sha(TAB.js), PIN['tabulator.min.js'], 'pinned tabulator.min.js'); assert.equal(sha(TAB.css), PIN['tabulator.min.css'], 'pinned tabulator.min.css');
assert.match(fs.readFileSync(path.join(TAB_DIR, 'LICENSE'), 'utf8'), /^The MIT License \(MIT\)/);
const CSP = /http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(fs.readFileSync(path.join(WEB_APP, 'index.html'), 'utf8'))[1];

// ---------------------------------------------------------------- page helpers
const INIT = () => {
  window.__csp = []; document.addEventListener('securitypolicyviolation', (e) => { window.__csp.push(e.violatedDirective + ' ' + (e.sample || '').slice(0, 40)); });
  window.__firstRow = null; new MutationObserver((_, o) => { if (document.querySelector('[data-lb-table] tbody tr[data-row]')) { window.__firstRow = performance.now(); o.disconnect(); } }).observe(document, { childList: true, subtree: true });
};
async function newPage(browser, vp, origin) {
  const context = await browser.newContext({ viewport: { width: vp.w, height: vp.h } });
  await context.clock.setFixedTime(new Date(NOW)); await context.addInitScript(INIT);
  const outside = []; await context.route('**/*', (route) => { const u = new URL(route.request().url()); if (u.origin === origin) return route.continue(); outside.push(u.origin + u.pathname); return route.abort(); });
  const page = await context.newPage(), errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); }); page.on('pageerror', (e) => errors.push(String(e).slice(0, 160)));
  const cdp = await context.newCDPSession(page);
  if (vp.cpu > 1) await cdp.send('Emulation.setCPUThrottlingRate', { rate: vp.cpu });
  await cdp.send('Performance.enable');
  return { context, page, cdp, errors, outside };
}
async function heap(cdp) { await cdp.send('HeapProfiler.collectGarbage'); const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((x) => [x.name, x.value])); return { heap: m.JSHeapUsedSize, nodes: m.Nodes }; }
const styleInfo = (page, sel) => page.evaluate((s) => { const els = [...document.querySelectorAll(s + ' [style], ' + s + '[style]')], props = {};
  for (const e of els) for (let i = 0; i < e.style.length; i++) props[e.style[i]] = (props[e.style[i]] || 0) + 1;
  return { elements: els.length, props: Object.entries(props).sort((a, b) => b[1] - a[1]).slice(0, 12) }; }, sel);

// ---------------------------------------------------------------- A. the real app
async function realApp(browser) {
  const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
  const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' },
    'qgv-official-status.json': { json: STATUS(JSON.parse(PUB_TEXT)) }, 'sec-public-inputs.json': { status: 404, body: '' } } });
  const out = { viewports: {} }; let rows = null;
  try {
    for (const vp of VIEWPORTS) {
      const runs = { open: [], sort: [], filter: [], style: null, csp: null, cross: null, errors: null, outside: null };
      for (let run = 0; run < RUNS; run++) {
        const p = await newPage(browser, vp, s.origin), { page } = p;
        await page.goto(s.base + '#/qgv');
        await page.evaluate(() => window.IS2.ready); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 60000 });
        runs.open.push(await page.evaluate(() => window.__firstRow));
        if (!rows) rows = await page.evaluate(dumpRows);
        // Two industries that have rows (the shipped select's own options).
        const ind = await page.evaluate(() => [...document.querySelectorAll('#lb-f-industry option')].map((o) => o.value).filter((v) => v && v !== 'NOT_AVAILABLE'));
        if (run === 0) runs.cross = { default: await page.evaluate(drawnRanks) };
        for (let i = 0; i < CLICKS; i++) {
          const col = i % 2 ? 'g' : 'q';
          runs.sort.push(await page.evaluate(async (c) => { const b = document.querySelector('[data-k="th-' + c + '"]'), t0 = performance.now(); b.click(); await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0))); return performance.now() - t0; }, col));
        }
        // back to Q (desc) for the cross-check: the last click above was G; one Q click = Q 높은 순.
        await page.evaluate(() => document.querySelector('[data-k="th-q"]').click());
        if (run === 0) runs.cross.q = await page.evaluate(drawnRanks);
        const pickable = [];
        for (const v of ind) { const n = await page.evaluate(async (val) => { const s = document.querySelector('#lb-f-industry'); s.value = val; s.dispatchEvent(new Event('change')); await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0))); return document.querySelectorAll('[data-lb-table] tbody tr[data-row]').length; }, v); if (n > 0) pickable.push(v); if (pickable.length === 2) break; }
        for (let i = 0; i < CLICKS; i++) {
          const v = pickable[i % pickable.length];
          runs.filter.push(await page.evaluate(async (val) => { const s = document.querySelector('#lb-f-industry'), t0 = performance.now(); s.value = val; s.dispatchEvent(new Event('change')); await new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0))); return performance.now() - t0; }, v));
        }
        if (run === 0) { runs.cross.filter = { industry: pickable[pickable.length - 1], drawn: await page.evaluate(drawnRanks) }; runs.style = await page.locator('[style]').count(); runs.csp = await page.evaluate(() => window.__csp); runs.errors = p.errors; runs.outside = p.outside; runs.industries = pickable; }
        await p.context.close();
      }
      out.viewports[vp.w] = { open_to_first_row_ms: stat(runs.open), sort_ms: stat(runs.sort), filter_ms: stat(runs.filter), style_attrs: runs.style, csp: runs.csp, console_errors: runs.errors, outside: runs.outside, industries: runs.industries, cross: runs.cross };
      log('A', vp.w, JSON.stringify({ open: out.viewports[vp.w].open_to_first_row_ms.median, sort: out.viewports[vp.w].sort_ms.median, filter: out.viewports[vp.w].filter_ms.median }));
    }
  } finally { await s.close(); }
  return { out, rows };
}
// The status file of web_app_qgv_browser_test.js (a later failed attempt; the publication stays shown).
function STATUS(PUB) { return { schema: 'qgv-official-status/1', kind: 'QGV_OFFICIAL_STATUS', last_attempt_at: '2026-10-14T01:50:00Z', attempt_state: 'SUPPLY_FAILED', reason_code: 'IEX_SUPPLY_BELOW_MINIMUM',
  official_publication_id: PUB.publication_id, official_price_basis_date: PUB.times.price_basis_date, official_verified_at: PUB.times.verified_at, latest_inputs: { sha256: 'b'.repeat(64), as_of: '2026-10-14T01:30:00Z' }, attribution: PUB.attribution }; }
// In-page: the layer's Universe504 rows as the trial's display rows (the same helpers the shipped screen uses).
async function dumpRows() {
  const I = window.IS2, Q = I.qgv, D = I.data, Hp = I.qgvLive.helpers, pg = await Q.page(), names = await D.static('company-names-ko.json').catch(() => null);
  const ps = { 'sec-qgv2.json': D.get('sec-qgv2.json'), 'company-classification.json': D.get('company-classification.json') };
  const groups = new Map(((ps['company-classification.json'].data || {}).industry_config || { groups: [] }).groups.map((g) => [g.id, g.name]));
  const T = window.TypeConfigDefaults, ES = window.EntitySearch;
  return Q.rows(pg, { scope: 'UNIVERSE' }).map((r) => {
    const rec = names ? names.get(r.id) || (r.code ? names.get(r.code) : null) : null, ind = Hp.industryOf({ company_id: r.id }, ps);
    const tnames = T.types.filter((t) => r.types.selected.includes(t.id)).map((t) => t.name);
    const rank_text = Number.isInteger(r.rank.official) ? String(r.rank.official) : r.rank.qg_reference_order !== null && !(r.scope === 'OUTSIDE_UNIVERSE' || r.reference_only) ? '참고 ' + r.rank.qg_reference_order : '—';
    const txt = (c) => (c ? Q.reasonText(c) : null);
    return { id: r.id, ticker: r.ticker, title: ES ? ES.companyTitle(rec, r.ticker, 'ko-KR') : r.ticker, industry: ind || '', industry_label: ind ? groups.get(ind) || ind : '', sic: Hp.sicOf({ company_id: r.id }, ps),
      types_text: tnames.length ? tnames.join(' · ') : null, acquired_at: r.acquired_at, score: { total: r.score.total, q: r.score.q, g: r.score.g, v: r.score.v },
      rank: { official: r.rank.official, qg_reference_order: r.rank.qg_reference_order }, rank_text,
      na_reason: { total: txt(r.na_reason.total), q: txt(r.na_reason.q), g: txt(r.na_reason.g), v: txt(r.na_reason.v), rank: txt(r.na_reason.rank) } };
  });
}
function drawnRanks() { return [...document.querySelectorAll('[data-lb-table] tbody tr[data-row]')].map((tr) => [tr.dataset.row, tr.querySelector('td[data-cell=rank]').textContent.replace(/^—.*$/, '—')]); }

// ---------------------------------------------------------------- B/C. the trial page
function serveTrial(dir) {
  const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2' };
  const server = http.createServer((req, res) => { const name = decodeURIComponent(new URL(req.url, 'http://x').pathname.slice(1)) || 'trial.html', file = path.join(dir, name);
    if (!file.startsWith(dir + path.sep) || !fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res); });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({ server, base: 'http://127.0.0.1:' + server.address().port + '/' })));
}
function trialDir(datasets) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'leaderboard-trial-'));
  fs.writeFileSync(path.join(dir, 'trial.html'), fs.readFileSync(path.join(__dirname, 'trial.html'), 'utf8').replace('__APP_CSP__', CSP));
  for (const f of ['trial.js', 'trial.css']) fs.copyFileSync(path.join(__dirname, f), path.join(dir, f));
  for (const f of ['core.js', 'screen-qgv-live.js', 'app.css', 'jua-regular-ksx1001.woff2']) fs.copyFileSync(path.join(WEB_APP, f), path.join(dir, f));
  fs.writeFileSync(path.join(dir, 'tabulator.min.js'), TAB.js); fs.writeFileSync(path.join(dir, 'tabulator.min.css'), TAB.css);
  for (const [name, rows] of Object.entries(datasets)) fs.writeFileSync(path.join(dir, 'rows-' + name + '.json'), JSON.stringify(rows));
  return dir;
}
async function trialRuns(browser, base, origin, ds, mode, vp, rows) {
  const byId = new Map(rows.map((r) => [r.id, r]));
  const acc = { load: [], render: [], sort: [], filter: [], heap: [], nodes: [], domRows: null, rankBad: 0, dataBad: 0, naZero: 0, checks: 0, style: null, csp: null, errors: null, outside: null, order: null };
  for (let run = 0; run < RUNS; run++) {
    const p = await newPage(browser, vp, origin), { page, cdp } = p;
    await page.goto(base + 'trial.html?ds=' + ds + '&mode=' + mode);
    acc.load.push((await page.evaluate(() => window.TRIAL.ready)).load);
    const before = await heap(cdp), r = await page.evaluate(() => window.TRIAL.render()), after = await heap(cdp);
    acc.render.push(r.ms); acc.heap.push(after.heap - before.heap); acc.nodes.push(after.nodes - before.nodes); acc.domRows = r.domRows;
    const check = async () => { const c = await page.evaluate(() => window.TRIAL.check()); acc.checks++; acc.rankBad += c.bad.length; acc.dataBad += c.dataBad; acc.naZero += c.zero.length; return c; };
    await check();
    for (let i = 0; i < CLICKS; i++) { acc.sort.push(await page.evaluate((c) => window.TRIAL.sortBy(c), i % 2 ? 'g' : 'q')); await check(); }
    if (run === 0) { // order after a single G 높은 순 header click: equal ids, or equal G values (ties ordered differently)?
      acc.order = await page.evaluate(() => { const T = window.TRIAL, got = T.order(), want = T.expectedOrder('g-desc', '');
        return { n: got.length, sameIds: got.length === want.length && got.every((id, i) => id === want[i]), idMismatch: got.filter((id, i) => id !== want[i]).length }; });
      acc.order.sameValues = await page.evaluate(async (dsName) => { const T = window.TRIAL, rows = new Map((await (await fetch('rows-' + dsName + '.json')).json()).map((x) => [x.id, x.score.g]));
        const got = T.order().map((id) => rows.get(id)), want = T.expectedOrder('g-desc', '').map((id) => rows.get(id)); return got.every((v, i) => v === want[i]); }, ds);
    }
    if (run === 0) { // one QGV header click (높은 순): are ranked rows kept ahead of the unranked ones (D11 tiers), and what does aria-sort say?
      const q = await page.evaluate(async () => { const T = window.TRIAL; await T.sortBy('qgv'); const th = document.querySelector('#trial-host .tabulator-col[tabulator-field="total"]') || document.querySelector('#trial-host button[data-col="qgv"]').closest('th');
        return { ids: T.order(), ariaSort: th.getAttribute('aria-sort') }; });
      const ranked = (id) => Number.isInteger(byId.get(id).rank.official), first = q.ids.findIndex((id) => !ranked(id));
      acc.qgvTiers = { ariaSort: q.ariaSort, rankedAfterFirstUnranked: first < 0 ? 0 : q.ids.slice(first).filter(ranked).length, firstUnrankedAt: first };
    }
    const groups = await page.evaluate(() => window.TRIAL.groups());
    for (let i = 0; i < CLICKS; i++) { acc.filter.push(await page.evaluate((g) => window.TRIAL.filterTo(g), groups[i % 2])); const c = await check(); if (i === 0) acc.filterShown = c.shown; }
    if (run === 0) { acc.style = await styleInfo(page, '#trial-host'); acc.csp = await page.evaluate(() => window.__csp); acc.errors = p.errors; acc.outside = p.outside; }
    await p.context.close();
  }
  return { load_ms: stat(acc.load), render_ms: stat(acc.render), sort_ms: stat(acc.sort), filter_ms: stat(acc.filter), heap_delta_kb: r1(median(acc.heap) / 1024), dom_nodes_delta: median(acc.nodes),
    dom_rows: acc.domRows, rank_checks: acc.checks, rank_text_changed: acc.rankBad, active_data_rank_changed: acc.dataBad, na_drawn_as_zero: acc.naZero, order_after_g_click: acc.order, qgv_header_click: acc.qgvTiers,
    style_attrs: acc.style, csp: acc.csp, console_errors: acc.errors, outside: acc.outside };
}
// C. Keyboard, names, phone readability (one fresh page per mode and viewport, synthetic504).
async function access(browser, base, origin, mode, vp) {
  const p = await newPage(browser, vp, origin), { page } = p;
  await page.goto(base + 'trial.html?ds=synthetic504&mode=' + mode); await page.evaluate(() => window.TRIAL.ready); await page.evaluate(() => window.TRIAL.render());
  const sortCol = vp.w < 720 ? 'total' : 'q', seq = [];
  await page.locator('body').focus();
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press('Tab');
    seq.push(await page.evaluate((col) => { const a = document.activeElement; if (!a || a === document.body) return null; const cs = getComputedStyle(a);
      const header = a.closest('th, .tabulator-col'), field = header ? (header.getAttribute('tabulator-field') || (a.dataset && a.dataset.col === 'qgv' ? 'total' : a.dataset && a.dataset.col)) : null;
      return { tag: a.tagName.toLowerCase(), cls: String(a.className).slice(0, 40), header: !!header, field, sortControl: !!header && field === col, inRow: !!a.closest('tr[data-row], .tabulator-row'), holder: a.classList.contains('tabulator-tableholder'),
        focusRing: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2, outline: cs.outlineStyle + ' ' + cs.outlineWidth }; }, sortCol));
  }
  const reachedSort = seq.findIndex((x) => x && x.sortControl), reachedRow = seq.findIndex((x) => x && x.inRow), holder = seq.findIndex((x) => x && x.holder);
  let enterSorts = null;
  if (reachedSort >= 0) { // focus that control again by Tab count, press Enter, see whether the order changed
    await page.reload(); await page.evaluate(() => window.TRIAL.ready); await page.evaluate(() => window.TRIAL.render()); await page.locator('body').focus();
    for (let i = 0; i <= reachedSort; i++) await page.keyboard.press('Tab');
    const o1 = await page.evaluate(() => window.TRIAL.order().slice(0, 5).join()); await page.keyboard.press('Enter'); await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0))));
    enterSorts = o1 !== (await page.evaluate(() => window.TRIAL.order().slice(0, 5).join()));
  }
  // Tabulator: header cells are role=columnheader divs; is any of them focusable at all?
  const headerFocusable = await page.evaluate(() => [...document.querySelectorAll('#trial-host th button, #trial-host .tabulator-col')].filter((e) => e.tabIndex >= 0).length);
  const aria = (await page.locator('#trial-host').ariaSnapshot()).split('\n');
  const roles = await page.evaluate(() => ({ grid: document.querySelectorAll('#trial-host [role=grid], #trial-host table').length, colheaders: [...document.querySelectorAll('#trial-host th, #trial-host [role=columnheader]')].map((e) => e.getAttribute('aria-sort') || '-').join(' '),
    rowsInDom: document.querySelectorAll('#trial-host tr[data-row], #trial-host .tabulator-row').length }));
  const phone = await page.evaluate(() => { const holder = document.querySelector('#trial-host .tbl-wrap, #trial-host .tabulator-tableholder'), cells = [...document.querySelectorAll('#trial-host td, #trial-host .tabulator-cell')].slice(0, 200);
    const sizes = cells.flatMap((c) => [c, ...c.querySelectorAll('*')]).filter((e) => e.textContent.trim() && e.getBoundingClientRect().width > 0).map((e) => parseFloat(getComputedStyle(e).fontSize));
    const heads = [...document.querySelectorAll('#trial-host th, #trial-host .tabulator-col')].filter((e) => e.getBoundingClientRect().width > 0);
    const sortables = [...document.querySelectorAll('#trial-host th button, #trial-host .tabulator-col.tabulator-sortable')].filter((e) => e.getBoundingClientRect().width > 0).map((e) => Math.round(e.getBoundingClientRect().height));
    const row = document.querySelector('#trial-host tr[data-row], #trial-host .tabulator-row');
    return { pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1, tableScrollsX: !!holder && holder.scrollWidth > holder.clientWidth + 1, minFontPx: Math.min(...sizes), headerCount: heads.length,
      headersInView: heads.filter((e) => e.getBoundingClientRect().right <= window.innerWidth + 1).length, sortTargetMinPx: Math.min(...sortables), rowHeightPx: row ? Math.round(row.getBoundingClientRect().height) : null }; });
  await p.context.close();
  return { tabs_to_sort_control: reachedSort >= 0 ? reachedSort + 1 : null, enter_sorts: enterSorts, tabs_to_first_row_item: reachedRow >= 0 ? reachedRow + 1 : null, tabs_to_scroll_holder: holder >= 0 ? holder + 1 : null,
    focus_ring_on_every_stop: seq.filter(Boolean).every((x) => x.focusRing), focus_misses: seq.filter((x) => x && !x.focusRing).map((x) => x.tag + '.' + x.cls + ' ' + x.outline).slice(0, 4),
    header_focusable: headerFocusable, roles, aria_head: aria.slice(0, 18), phone };
}

// ---------------------------------------------------------------- D. sizes and static compatibility
function staticChecks() {
  const src = fs.readFileSync(path.join(TOOLS, 'web_app_reuse_node_test.js'), 'utf8'), body = /const RULES = \[([\s\S]*?)\n\];/.exec(src)[1];
  // Only the rules' names and patterns are taken (each rule line's regex literal); allow-lists do not apply to a new file.
  const rules = [...body.matchAll(/^\s*\['([^']+)',\s*(\/.*\/[a-z]*),\s*(?:\[[^\]]*\]|[A-Z0-9_]+|\[[A-Z0-9_]+\])\],?\s*$/gm)].map((m) => [m[1], m[2]]);
  const text = TAB.js.toString('utf8'), lint = {};
  for (const [name, lit] of rules) { const m = /^\/(.*)\/([a-z]*)$/.exec(lit), re = new RegExp(m[1], m[2].replace('g', '') + 'g'); lint[name] = (text.match(re) || []).length; }
  const LOAD_NAME = /^[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.js$/;
  // The Pages guard's content checks on the two files alone: SECRET_PATTERNS, KIS markers, private paths, text format. In this
  // python process only (the guard file is not changed) each file's own SHA-256 is put in APPROVED_SHA256, i.e. what pinning it
  // would look like, so the counts show whether a pin alone would be enough; allowed_name_today says whether it is allowed now.
  const py = 'import importlib.util,sys,json\nfrom collections import Counter\ns=importlib.util.spec_from_file_location("g",sys.argv[1]);g=importlib.util.module_from_spec(s);s.loader.exec_module(g)\nout={}\n'
    + 'import hashlib\nfor p in sys.argv[2:]:\n  n=p.rsplit("/",1)[-1];allowed=n in g.ALLOWED_NAMES\n  g.APPROVED_SHA256[n]=hashlib.sha256(open(p,"rb").read()).hexdigest()\n  v=Counter();g._check_payload(p.rsplit("/",1)[-1],open(p,"rb").read(),v);out[p.rsplit("/",1)[-1]]={"violations":dict(v),"allowed_name_today":allowed,"under_max_bytes":len(open(p,"rb").read())<=g.MAX_FILE_BYTES}\nprint(json.dumps(out))';
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'trial-guard-')); fs.writeFileSync(path.join(tmp, 'tabulator.min.js'), TAB.js); fs.writeFileSync(path.join(tmp, 'tabulator.min.css'), TAB.css);
  const guard = JSON.parse(execFileSync('python3', ['-I', '-c', py, path.join(TOOLS, 'pages_artifact_guard.py'), path.join(tmp, 'tabulator.min.js'), path.join(tmp, 'tabulator.min.css')], { encoding: 'utf8' }));
  fs.rmSync(tmp, { recursive: true, force: true });
  const live = fs.readFileSync(path.join(WEB_APP, 'screen-qgv-live.js')), liveText = live.toString('utf8');
  const a = liveText.indexOf(' function table(v){'), b = liveText.indexOf(' // The 2.1.5 empty state'), slice = Buffer.from(liveText.slice(a, b));
  return {
    sizes: { 'tabulator.min.js': { raw: TAB.js.length, gz: gz(TAB.js) }, 'tabulator.min.css': { raw: TAB.css.length, gz: gz(TAB.css) }, tabulator_total_gz: gz(TAB.js) + gz(TAB.css),
      'screen-qgv-live.js (whole, unminified, as shipped)': { raw: live.length, gz: gz(live) }, 'screen-qgv-live.js table()..row() slice': { raw: slice.length, gz: gz(slice) },
      'app.css (whole)': { raw: fs.statSync(path.join(WEB_APP, 'app.css')).size, gz: gz(fs.readFileSync(path.join(WEB_APP, 'app.css'))) } },
    lint_rule_hits_in_tabulator_min_js: lint, loader_name_ok: LOAD_NAME.test('tabulator.min.js'), pages_guard_content: guard,
    network_apis: { fetch: (text.match(/\bfetch\(/g) || []).length, xhr: (text.match(/XMLHttpRequest/g) || []).length, storage: (text.match(/\b(?:localStorage|sessionStorage)\b/g) || []).length } };
}

(async () => {
  const OUT = process.env.TRIAL_OUT || fs.mkdtempSync(path.join(os.tmpdir(), 'leaderboard-trial-out-'));
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const result = { tabulator: { version: PIN.version, license: PIN.license, sha256: { js: PIN['tabulator.min.js'], css: PIN['tabulator.min.css'] } }, csp: CSP, runs: RUNS, clicks: CLICKS, viewports: VIEWPORTS };
  try {
    result.static = staticChecks(); log('D', JSON.stringify(result.static.sizes));
    const A = await realApp(browser); result.real_app = A.out;
    const datasets = { layer504: A.rows, synthetic504: SYN.rows(504), synthetic2000: SYN.rows(2000), synthetic10000: SYN.rows(10000) };
    result.datasets = Object.fromEntries(Object.entries(datasets).map(([k, v]) => [k, { rows: v.length, ranked: v.filter((r) => Number.isInteger(r.rank.official)).length, qg_reference: v.filter((r) => r.rank.qg_reference_order !== null).length, no_rank: v.filter((r) => r.rank_text === '—').length }]));
    const dir = trialDir(datasets), { server, base } = await serveTrial(dir), origin = new URL(base).origin;
    try {
      // Cross-check: the trial's existing renderer orders the dumped layer rows exactly as the shipped table did (first 50).
      { const p = await newPage(browser, VIEWPORTS[0], origin); await p.page.goto(base + 'trial.html?ds=layer504&mode=existing50'); await p.page.evaluate(() => window.TRIAL.ready);
        const cross = A.out.viewports[1440].cross, ind = cross.filter.industry;
        const exp = await p.page.evaluate((i) => ({ def: window.TRIAL.expectedOrder('qgv', ''), q: window.TRIAL.expectedOrder('q-desc', ''), f: window.TRIAL.expectedOrder('q-desc', i) }), ind);
        const rk = new Map(datasets.layer504.map((r) => [r.id, r.rank_text]));
        const same = (drawn, ids) => drawn.length === Math.min(50, ids.length) && drawn.every(([id, t], i) => id === ids[i] && t === rk.get(id));
        result.cross_check = { default_sort_first50_equal: same(cross.default, exp.def), q_sort_first50_equal: same(cross.q, exp.q), filter_q_sort_equal: same(cross.filter.drawn, exp.f), filter_industry: ind, drawn: cross.default.length };
        await p.context.close(); log('X', JSON.stringify(result.cross_check)); }
      result.trial = {};
      for (const vp of VIEWPORTS) for (const ds of Object.keys(datasets)) for (const mode of MODES) {
        const key = vp.w + ' ' + ds + ' ' + mode; result.trial[key] = await trialRuns(browser, base, origin, ds, mode, vp, datasets[ds]);
        const t = result.trial[key]; log('B', key, JSON.stringify({ render: t.render_ms.median, sort: t.sort_ms.median, filter: t.filter_ms.median, heapKB: t.heap_delta_kb, nodes: t.dom_nodes_delta, bad: t.rank_text_changed + t.active_data_rank_changed, style: t.style_attrs.elements, csp: t.csp.length }));
      }
      result.access = {};
      for (const vp of VIEWPORTS) for (const mode of ['existing50', 'tabulator']) { result.access[vp.w + ' ' + mode] = await access(browser, base, origin, mode, vp); log('C', vp.w, mode, JSON.stringify(result.access[vp.w + ' ' + mode].phone)); }
    } finally { server.close(); fs.rmSync(dir, { recursive: true, force: true }); }
  } finally { await browser.close(); }
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(result, null, 1));
  log('RESULTS', path.join(OUT, 'results.json'));
})().catch((e) => { console.error(e); process.exit(1); });
