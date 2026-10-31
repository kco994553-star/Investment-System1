'use strict';
// New frontend P0 (docs/frontend_v2/FRONTEND_V2_PLAN.md): builds the development site itself (tools/build_web_app.py), serves it
// on a loopback port and checks every route at 1440 and 390:
//  - the draft's menu 0 ~ n+1, each menu's numbered sections in the draft's order, the detail screens, unknown routes -> 0;
//  - the header menu marks the current menu; phone: header menu hidden, bottom tabs (홈 · QGV · 포트폴리오 · 뉴스 · 전체) and the
//    전체 메뉴 drawer (menus + detail screens, Escape closes and returns focus);
//  - no request leaves the page's origin, no console error (CSP violations included; the one exception is the intended 404 of a
//    live-only public file this offline build does not contain, read by a screen that shows public data: P2-1 company page),
//    no style attribute in the DOM,
//    nothing written to localStorage / sessionStorage / IndexedDB, no horizontal overflow, the three self-hosted fonts load;
//  - a 연결 전 block shows no digits (the draft's numbers are examples only).
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path'), http = require('node:http'), { execFileSync } = require('node:child_process');
const ROOT = path.resolve(__dirname, '../..'), OUT = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-'));
fs.rmSync(OUT, { recursive: true });
execFileSync('python3', [path.join(ROOT, 'implementation/tools/build_web_app.py'), '--out', OUT], { stdio: 'inherit' });
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2', '.txt': 'text/plain' };
const server = http.createServer((req, res) => { const name = decodeURIComponent(new URL(req.url, 'http://x').pathname.slice(1)) || 'index.html'; const file = path.join(OUT, name);
  if (!file.startsWith(OUT) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res); });
const MENUS = { qgv: ['1-1', '1-2', '1-3', '1-4'], technical: ['2-1', '2-2', '2-3', '2-4'], macro: ['3-1', '3-2', '3-3', '3-4', '3-5', '3-6'], news: ['4-1', '4-2', '4-3'],
  portfolio: ['5-1', '5-2', '5-3', '5-4'], prompts: ['6-1', '6-2'], tree: ['n-1'], lab: ['lab-1', 'lab-2'] };
const DETAILS = ['settings', 'data-status', 'financials', 'sec-cover', 'playbook', 'virtual-trading', 'target-v1'];
const HEADER = ['qgv', 'technical', 'macro', 'news', 'portfolio', 'prompts', 'tree', 'lab'];
// Published by the data workflow only (absent from the offline build; checked below): their 404 is the NOT_PUBLISHED state.
// Exactly the two core files IS2.data.ready() reads that this build lacks (the company page calls it) and the two central V files
// IS2.data.official() reads for the QGV page (DC-31), and the price-free forward ledger the Lab page reads (feature 9.2); nothing
// else is excused.
const LIVE_ONLY = ['sec-qgv2.json', 'sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'forward-validation-ledger.json'];
for (const f of LIVE_ONLY) if (fs.existsSync(path.join(OUT, f))) throw new Error(f + ' is in the offline build: not live-only');
let phase = 'START';
(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const BASE = 'http://127.0.0.1:' + server.address().port + '/', ORIGIN = new URL(BASE).origin;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const phone = width < 720, context = await browser.newContext({ viewport: { width, height } }), page = await context.newPage();
      const outside = [], errors = [];
      page.on('request', (r) => { if (new URL(r.url()).origin !== ORIGIN) outside.push(r.url()); });
      page.on('console', (m) => { if (m.type() !== 'error') return; const at = m.location() && m.location().url ? new URL(m.location().url, ORIGIN) : null;
        if (at && at.origin === ORIGIN && /status of 404/.test(m.text()) && LIVE_ONLY.includes(decodeURIComponent(at.pathname.slice(1)))) return; errors.push(m.text()); });
      page.on('pageerror', (e) => errors.push(String(e)));
      const visit = async (hash) => { phase = width + ' ' + hash; await page.goto(BASE + hash); await page.locator('main[data-route]').waitFor(); };
      const common = async () => {
        assert.equal(await page.locator('[style]').count(), 0, phase + ': no style attribute');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
        for (const t of await page.locator('[data-pending]').allTextContents()) assert.doesNotMatch(t, /\d/, phase + ': pending block has no number: ' + t);
      };
      // 0. 기업 검색 and the result page.
      await visit('#/');
      assert.equal(await page.locator('main').getAttribute('data-route'), 'search');
      assert.match(await page.locator('.hero-title').textContent(), /어떤 기업을 볼까요\?/);
      await common();
      // The shared search (DC-23) submits after IS2.ready (before it a submit does nothing): wait for the layer, then the exact code.
      await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-search-input]').fill('NYSE:FIX'); await page.locator('[data-search-form] button[type=submit]').click();
      await page.locator('[data-result-code="NYSE:FIX"]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/company/NYSE%3AFIX');
      assert.deepEqual(await page.locator('[data-card]').evaluateAll((n) => n.map((x) => x.dataset.card)), ['qgv', 'technical', 'macro', 'news', 'portfolio']);
      await common();
      // Menus 1 ~ n+1 in the draft's section order; the header (PC) marks the current one.
      for (const [id, sections] of Object.entries(MENUS)) {
        await visit('#/' + id);
        assert.equal(await page.locator('main').getAttribute('data-route'), id);
        assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), sections, phase);
        if (!phone) assert.deepEqual(await page.locator('.menu a[aria-current=page]').evaluateAll((n) => n.map((x) => x.dataset.menu)), [id]);
        await common();
      }
      for (const d of DETAILS) { await visit('#/detail/' + d); assert.equal(await page.locator('[data-detail]').getAttribute('data-detail'), d); await common(); }
      await visit('#/nowhere/x'); assert.equal(await page.locator('main').getAttribute('data-route'), 'search');
      // Shell per width.
      phase = width + ' shell';
      assert.equal(await page.locator('.top .menu').isVisible(), !phone);
      assert.deepEqual(await page.locator('.top .menu a').evaluateAll((n) => n.map((x) => x.dataset.menu)), HEADER);
      assert.equal(await page.locator('.tabbar').isVisible(), phone);
      if (phone) {
        assert.deepEqual(await page.locator('.tabbar [data-tab]').evaluateAll((n) => n.map((x) => x.dataset.tab)), ['search', 'qgv', 'portfolio', 'news', 'all']);
        await visit('#/news'); assert.equal(await page.locator('.tabbar [data-tab=news]').getAttribute('aria-current'), 'page');
        await page.locator('.tabbar [data-tab=all]').click(); await page.locator('[data-drawer]:not([hidden])').waitFor();
        assert.equal(await page.locator('[data-drawer-menu]').count(), 9); assert.equal(await page.locator('[data-drawer-detail]').count(), DETAILS.length);
        await page.keyboard.press('Escape'); assert.equal(await page.locator('[data-drawer]').isHidden(), true);
        assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.dataset.tab), 'all', 'focus returns to the 전체 tab');
        await page.locator('.tabbar [data-tab=all]').click(); await page.locator('[data-drawer-detail=settings]').click();
        await page.locator('[data-detail=settings]').waitFor(); assert.equal(await page.locator('[data-drawer]').isHidden(), true);
      }
      phase = width + ' fonts';
      // DC-25: Jua is the one self-hosted face (titles); body text is the device's Korean gothic.
      assert.deepEqual(await page.evaluate(async () => { await document.fonts.ready; return ['IS Jua'].map((f) => document.fonts.check('16px "' + f + '"', '가')); }), [true]);
      phase = width + ' boundaries';
      assert.deepEqual(outside, [], 'no request leaves the origin');
      assert.deepEqual(errors, [], 'no console error');
      assert.deepEqual(await page.evaluate(async () => ({ local: localStorage.length, session: sessionStorage.length, idb: indexedDB.databases ? (await indexedDB.databases()).length : 0 })), { local: 0, session: 0, idb: 0 });
      await context.close();
    }
    console.log('web app shell: menus, sections, details, tabs, drawer, fonts and boundaries ok at 1440 and 390');
  } finally { await browser.close(); server.close(); fs.rmSync(OUT, { recursive: true, force: true }); }
})().catch((e) => { console.error('FAILED at', phase); console.error(e); process.exitCode = 1; server.close(); });
