'use strict';
// Owner-private KIS panels (owner 2026-11-05 DC-44, 2026-11-14 DC-52, 2026-11-15 DC-53; Codex #480 contract) in a real browser,
// on the development build (index.html) and on the published Pages artifact (tools/build_pages_cockpit.py, app.html; owner
// 2026-11-15 narrow Pages guard exception: both owner-private files are published): 2-1 of #/technical (tech-kis-chart) and
// the KIS V panel of #/qgv (qgv-kis). Google and the private
// Worker are stand-ins; every payload is the synthetic fixture tools/web_app_kis_private_fixture.js (no company, no KIS value).
// Behaviour and boundary only (owner 2026-11-15: no appearance checks beyond these):
//  - Public by default: before any click each panel is LOGIN_REQUIRED (로그인 필요) with an empty body and nothing goes to the
//    Worker; a synthetic click sends nothing.
//  - Sign-in inside clicks (Google script, then a token for scope exactly openid email); reads only after a click, only the
//    Worker's /kis routes, each with the Bearer header alone (no cookie, no referrer), the reads of one click 5 s apart.
//  - Owner states: READY (label, price basis day, numbers; values only as text inside [data-ram-price]). Tiers from Codex #556's
//    own synthetic output: 검증됨 = VERIFIED adopted value, 검증 전(참고) = reference_value, WITHHELD = one hold line and no reference
//    value or chart, no display fields = 검증 표시 없음 and no value (fail closed); BASIS_MISMATCH (no indicator attached), EMPTY (404 KIS_SERIES_NOT_FOUND: 자료 없음, session kept) apart
//    from ERROR (a refused payload, a 500), a server 403 back to LOGIN_REQUIRED, 연결 끊기.
//  - Read token status in the 상태 box, on its own click: NO_EXPIRY reads 만료일 없음; a rejection and a mismatch have their own
//    words and one short line on the panel.
//  - QGV: label KIS · 비공개 · 공식 아님 with the price basis day, source and calc version, V 미산출 never 0, no total without V, the
//    public ranks unchanged. Each cell carries one verification tag (검증됨 / 검증 전(참고)).
//  - Boundaries: no token or private value in storage, the address, the console or a public request; no CSP violation.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_kis_private_fixture.js');

const NOW = '2026-10-31T06:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
const TOKEN = ['memory', 'only', 'synthetic', 'kis', 'private', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.__gisCfg=[];window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gisCfg.push({scope:cfg.scope,igs:cfg.include_granted_scopes});'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const RAW = ['101.25', '55.5'];                                  // raw diagnostic values in the analysis fixture: never on the page
const status = (state, code = null, expires_on = null, days_left = null) => ({ schema: X.K('status/1'), state, code, expires_on, days_left });
const FIXTURES = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } };
function buildPages() {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-kis-pages-'));
  fs.rmSync(out, { recursive: true });
  execFileSync('python3', [path.join(R.ROOT, 'implementation/tools/build_pages_cockpit.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  for (const name of ['kis-private.js', 'private-expand-live.js', 'loader.js']) {
    assert.ok(fs.readFileSync(path.join(out, name)).equals(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/product/web_app', name))), name + ' is published byte-identical');
  }
  return out;
}
// [label, build (null = the development build site.start makes), entry page]
const SITES = [['dev', null, ''], ['pages', buildPages, 'app.html']];
let phase = 'START', pass = 0, where = '';

(async () => {
  let s = null, pagesOut = null;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  // The stock route (owner 2026-11-20 switch) answers one kis-stock-view/1 assembled from the part answers the cases set
  // (analysis, chart, technical = measures): a non-200 analysis or chart answer is the route's answer; a 404 measures answer
  // leaves the view without measures; the chart header loses its bars and keeps its fields; the rows carry the six price columns.
  const STOCK_FIELDS = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'SMA_20', 'SMA_60', 'SMA_120', 'BOLL_MIDDLE_20', 'BOLL_UPPER_20_2',
    'BOLL_LOWER_20_2', 'RSI_14', 'MACD_12_26', 'MACD_SIGNAL_9', 'MACD_HISTOGRAM_12_26_9'];
  const fail = () => ({ status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } });
  function stockAnswer(w, sym) {
    const a = (w.answers.analysis || fail)(sym), c = (w.answers.chart || fail)(sym), m = (w.answers.technical || fail)(sym);
    for (const x of [a, c]) if (x.status !== 200) return x;
    if (m.status !== 200 && m.status !== 404) return m;
    const { bars, raw_bars: rawBars, schema, ...header } = c.body;
    const row = (b) => [b.date, b.open, b.high, b.low, b.close, b.volume, ...Array(11).fill(null)];
    const view = { schema: X.K('stock-view/1'), publication_scope: 'OWNER_PRIVATE_ONLY', symbol: c.body.symbol, evaluation_day: a.body.evaluation_day,
      fields: STOCK_FIELDS, rows: bars.map(row), chart: { ...header, schema: X.K('chart-metadata/1') }, indicators: {}, coverage: {},
      latest: m.status === 200 ? { technical: a.body, measures: m.body } : { technical: a.body },
      additional_requests_for_toggle: 0, additional_requests_for_retained_period: 0 };
    if (c.body.basis === 'SPLIT_ADJUSTED') view.raw_rows = rawBars.map(row);
    return { status: 200, body: view };
  }
  // The Worker stand-in: answers[route] = (symbol) => {status, body}; one owner request at a time, at least 5 s apart, like the real one.
  async function context(width) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: [] });
    const w = { log: [], answers: {}, unexpected: [], all: [] };
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url()), hd = req.headers();
      w.all.push(req.method() + ' ' + req.url());
      if (url.origin === s.origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER && url.pathname.startsWith('/kis/') && req.method() === 'GET') {
        const at = Date.now();
        if (w.lastAt !== undefined && at - w.lastAt < 5000) { w.refused = (w.refused || 0) + 1; await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ error: { code: 'RATE_LIMITED' } }) }); return; }
        w.lastAt = at;
        w.log.push({ at, path: url.pathname + url.search, auth: hd.authorization || null, cookie: hd.cookie || null, referer: hd.referer || null });
        // KIS V reads the qgv part of the stock route (owner 2026-11-21 light read): answered by answers.qgv.
        const a = url.pathname === '/kis/stock' && url.search === '?part=qgv' ? (w.answers.qgv || fail)(null)
          : url.pathname === '/kis/stock' ? stockAnswer(w, url.searchParams.get('symbol'))
          : (w.answers[url.pathname.slice(5)] || (() => ({ status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } })))(url.searchParams.get('symbol'));
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: a.raw !== undefined ? a.raw : JSON.stringify(a.body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    return { ctx, page, seen, w };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.textContent);
  const count = (page, sel) => page.locator(sel).count();
  const state = (page, id) => page.locator('[data-private-panel="' + id + '"]').getAttribute('data-private-state');
  const waitState = (page, id, st) => page.locator('[data-private-panel="' + id + '"][data-private-state="' + st + '"]').waitFor({ timeout: 30000 });
  const note = (page, kind) => text(page, '[data-private-note="' + kind + '"]');
  const body = (page, id) => text(page, '[data-private-panel="' + id + '"] .private-body');
  const expand = (page, kind) => page.locator('[data-private-expand="' + kind + '"]').click();
  async function publicByDefault(page, w, kind, id) {
    assert.equal(await state(page, id), 'LOGIN_REQUIRED', phase + ': public by default, the panel waits for a sign-in');
    assert.equal(await text(page, '[data-private-panel="' + id + '"] [data-private-status]'), '로그인 필요');
    assert.equal(await body(page, id), '', phase + ': empty body before a sign-in');
    assert.equal(await page.locator('[data-private-status-area="' + kind + '"]').isVisible(), false, phase + ': no 상태 box before a sign-in');
    await page.evaluate((k) => document.querySelector('[data-private-expand="' + k + '"]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })), kind);
    await page.waitForTimeout(200);
    assert.deepEqual([w.log.length, w.all.filter((u) => u.includes('accounts.google.com') || u.startsWith('GET ' + WORKER)).length], [0, 0], phase + ': a synthetic click sends nothing');
  }
  async function signIn(page, kind, id) {
    await expand(page, kind); await page.waitForFunction((k) => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note="' + k + '"]').textContent), kind, { timeout: 20000 });
    assert.equal(await state(page, id), 'LOGIN_REQUIRED', phase + ': loading the Google script is not a sign-in');
    await expand(page, kind); await page.waitForFunction((k) => /^로그인됨/.test(document.querySelector('[data-private-note="' + k + '"]').textContent), kind);
    assert.equal(await state(page, id), 'READY', phase + ': signed in, still folded');
    assert.deepEqual(await page.evaluate(() => window.__gisCfg.filter((c) => c.scope === 'openid email')), [{ scope: 'openid email', igs: false }], phase + ': one token request for openid email only');
  }
  async function boundaries(page, seen, w, label) {
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    assert.deepEqual(seen.errors.filter((e) => !/status of (403|404|429|500|502)/.test(e)), [], label + ': no console or page error but the stand-in refusals');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    for (const l of w.log) assert.deepEqual([l.auth, l.cookie, l.referer], ['Bearer ' + TOKEN, null, null], label + ': Bearer header only, no cookie, no referrer');
    const st = await site.storage(page);
    assert.equal(st.session, 0, label + ': nothing in session storage');
    assert.ok(!Object.keys(st.localItems).some((k) => /kis|token|private-layer/i.test(k)), label + ': no private key on the device');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), page.url(), ...seen.errors, ...w.all.filter((u) => !u.includes(WORKER))],
      [TOKEN, ...RAW, ...X.MEASURE_RAW, '12.4242', 'SYNTHETIC-SECURITY-1']), [], label + ': no token or private value in storage, the address, the console or another request');
  }

  try {
   for (const [label, build, entry] of SITES) {
    pagesOut = build ? build() : null;
    s = await site.start({ out: pagesOut, fixtures: FIXTURES });
    where = label + ' ';
    // ================================================================ technical 2-1, 1440
    {
      phase = where + 'technical 1440';
      const { ctx, page, seen, w } = await context(1440);
      await page.goto(s.base + entry + '#/technical/NASDAQ%3ANVDA'); await page.locator('main[data-route=technical]').waitFor();
      await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 }); await page.locator('[data-private-expand=technical]').waitFor();
      const holds = await count(page, '[data-indicator] [data-verdict]');
      await publicByDefault(page, w, 'technical', 'tech-kis-chart');
      await signIn(page, 'technical', 'tech-kis-chart');
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');

      // Read token status, on its own click inside the 상태 box (DC-53).
      phase = where + 'technical read token status';
      await page.locator('[data-private-status-area=technical] summary').click();
      const tokenLine = '[data-private-token-status=technical]';
      for (const [answer, st, words] of [
        [{ status: 200, body: status('NO_EXPIRY') }, 'NO_EXPIRY', /만료일 없음/],
        [{ status: 200, body: status('REJECTED', 'TOKEN_REJECTED') }, 'REJECTED', /토큰 거부/],
        [{ status: 200, body: status('ERROR', 'TOKEN_EXPIRY_MISMATCH') }, 'ERROR', /만료 설정.*일치하지 않/],
        [{ status: 200, body: status('OK') }, 'ERROR', /상태 파일 확인 필요/],
      ]) {
        w.answers.status = () => answer; delete w.lastAt;
        await page.locator('[data-private-token-check=technical]').click();
        await page.waitForFunction(({ sel, st: x }) => document.querySelector(sel).dataset.privateTokenState === x, { sel: tokenLine, st });
        assert.match(await text(page, tokenLine), words, phase + ' ' + st);
        if (st !== 'NO_EXPIRY') { assert.doesNotMatch(await text(page, tokenLine), /만료일 없음/); assert.match(await note(page, 'technical'), words, phase + ': one short line on the panel'); }
      }
      assert.ok(w.log.every((l) => l.path === '/kis/status'), phase + ': the status route only');
      w.log.length = 0;

      // Codex #556's own synthetic output (tools/web_app_kis_private_fixture.js codex556): the tiers as the producer writes them.
      phase = where + 'technical READY (available)';
      const answer = (kase) => { const f = X.codex556(kase, { symbol: 'NVDA' });
        w.answers.analysis = () => ({ status: 200, body: f.technical }); w.answers.chart = () => ({ status: 200, body: f.chart }); w.answers.technical = () => ({ status: 200, body: f.measures }); };
      const tiers = () => page.locator('[data-private-metric]').evaluateAll((n) => n.map((x) => [x.dataset.privateMetric, x.dataset.privateTier]));
      answer('available'); delete w.lastAt;
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/stock?symbol=NVDA'], phase + ': one read of the stock route for the click (owner 2026-11-20 switch)');
      assert.equal(w.refused || 0, 0, phase + ': no read refused by the one-at-a-time limiter');
      assert.match(await text(page, '[data-private-layer=technical]'), /^KIS · 비공개 · 가격 기준일 2026-10-23 · 원주가 검증 전\(참고\)$/, phase + ': label, basis day, basis and the chart\'s tag');
      assert.equal(await count(page, 'svg[data-private-chart=NVDA] [data-private-close-line]'), 1, phase + ': the close line');
      assert.deepEqual((await tiers()).filter(([, t]) => t !== 'HELD'), [['SMA_5', 'VERIFIED']], phase + ': the one adopted indicator');
      assert.match(await text(page, '[data-private-metric=SMA_5]'), /^이동평균\(5\)\s*11 검증됨$/, phase + ': its readable name; its adopted value keeps 검증됨, which differs from the cell\'s top tag');
      assert.ok((await tiers()).some(([, t]) => t === 'HELD'), phase + ': held indicators by their one-line reason');
      assert.equal(await count(page, '[data-private-measures=READY]'), 1);
      assert.deepEqual(await page.locator('[data-private-panel=tech-kis-chart] [data-ram-price]').allTextContents(), ['2026-10-23 · 11', '11'], phase + ': values as RAM text only');
      assert.ok((await text(page, '[data-private-facts=technical]')).includes('공급처'), phase + ': the file facts are in the 상태 box');
      // One check line (owner 2026-11-21): first / last session, bar count and split basis read off the view, nothing recomputed.
      assert.match(await text(page, '[data-private-facts=technical] [data-private-range=RAW]'), /^\d{4}-\d{2}-\d{2} ~ 2026-10-23 · \d+봉 · 분할 반영 아니오 \(0건\)$/, phase + ': the range line');
      assert.equal(await count(page, '[data-indicator] [data-verdict]'), holds, phase + ': the public verdicts are unchanged');

      assert.equal(await count(page, '[data-private-timing]'), 0, phase + ': the 새 경로 시간 재기 button is gone after the switch');

      phase = where + 'technical reference';
      await expand(page, 'technical'); answer('reference'); delete w.lastAt;
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual((await tiers()).filter(([, t]) => t !== 'HELD'), [['SMA_5', 'REFERENCE']], phase + ': the reference value, not an adopted one');
      assert.match(await text(page, '[data-private-metric=SMA_5]'), /^이동평균\(5\)\s*11$/, phase + ': no tag on the row, the cell names 검증 전(참고) once at the top');
      assert.equal(await count(page, '[data-private-verification=VERIFIED]'), 0, phase + ': no 검증됨');
      assert.equal(await count(page, '[data-private-tier-head]'), 0, phase + ': the chart\'s tag is the one top tag, no second head');

      // Owner 2026-11-18 (DC-56 screen text): long values shown to two decimals, the file's value unchanged; readable names.
      phase = where + 'technical reference display';
      await expand(page, 'technical'); delete w.lastAt;
      { const f = X.codex556('reference', { symbol: 'NVDA' }), m = f.technical.metrics;
        Object.assign(m.ATR_14, { reference_value: 8.217935450167728, reference_reasons: ['IDENTITY_UNCONFIRMED'] });
        Object.assign(m.BOLL_LOWER_20_2, { reference_value: -0.004, reference_reasons: ['IDENTITY_UNCONFIRMED'] });
        Object.assign(m.MACD_HISTOGRAM_12_26_9, { reference_value: 1.005, reference_reasons: ['IDENTITY_UNCONFIRMED'] });
        w.answers.analysis = () => ({ status: 200, body: f.technical }); w.answers.chart = () => ({ status: 200, body: f.chart }); w.answers.technical = () => ({ status: 200, body: f.measures }); }
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.match(await text(page, '[data-private-metric=ATR_14]'), /^ATR\(14\)\s*8\.22$/, phase + ': two decimals, no row tag');
      assert.match(await text(page, '[data-private-metric=BOLL_LOWER_20_2]'), /^볼린저 하단\(20, 2σ\)\s*0\.00$/, phase + ': no -0.00');
      assert.match(await text(page, '[data-private-metric=MACD_HISTOGRAM_12_26_9]'), /^MACD 히스토그램\(12, 26, 9\)\s*1\.0[01]$/, phase + ': the histogram name');
      assert.match(await text(page, '[data-private-metric=BOLL_UPPER_20_2]'), /^볼린저 상단\(20, 2σ\)\s*미산출/, phase + ': held rows get the readable name too');
      assert.match(await text(page, '[data-private-metric=RSI_14]'), /^RSI\(14\)/);
      assert.match(await text(page, '[data-private-metric=MACD_SIGNAL_9]'), /^MACD 시그널\(9\)/);
      assert.match(await text(page, '[data-private-metric=BOLL_MIDDLE_20]'), /^볼린저 중심\(20\)/);
      assert.match(await text(page, '[data-private-metric=EMA_20]'), /^지수이동평균\(20\)/);
      assert.match(await text(page, '[data-private-metric=MACD_12_26]'), /^MACD\(12, 26\)/);
      assert.deepEqual(site.leaks([await page.content()], ['8.217935450167728', '8.2179']), [], phase + ': the long value is not on the page, only its two-decimal form');
      assert.equal(await count(page, '[data-private-tier=REFERENCE] [data-private-verification]'), 0, phase + ': no tag repeated per row');

      phase = where + 'technical WITHHELD';
      await expand(page, 'technical'); answer('withheld'); delete w.lastAt;
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(await page.locator('[data-private-display=WITHHELD]').allTextContents(), Array(3).fill('보류 · 분할 같은 원주가 급변 · 검토 필요'), phase + ': one hold line per file (chart, indicators, measures)');
      assert.equal(await count(page, '[data-private-tier=REFERENCE]'), 0, phase + ': no reference value');
      assert.equal(await count(page, 'svg[data-private-chart]'), 0, phase + ': no chart of withheld closes');
      assert.deepEqual((await tiers()).map(([, t]) => t), ['VERIFIED'], phase + ': only the producer\'s verified adopted value stays');

      phase = where + 'technical fail closed (no display fields)';
      await expand(page, 'technical'); delete w.lastAt;
      w.answers.analysis = () => ({ status: 200, body: X.analysis({ adopted: true }) });
      w.answers.chart = (sym) => ({ status: 200, body: X.bars({ symbol: sym }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym }) });
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(await page.locator('[data-private-display=UNKNOWN]').allTextContents(), Array(3).fill('검증 표시 없음'), phase + ': one line per file');
      assert.deepEqual([await count(page, '[data-private-verification]'), await count(page, '[data-private-panel=tech-kis-chart] [data-ram-price]'), await count(page, 'svg[data-private-chart]')], [0, 0, 0], phase + ': no tag, no value, no chart');
      assert.deepEqual(site.leaks([await page.content()], [...RAW, ...X.MEASURE_RAW, '12.4242', '105.5']), [], phase + ': none of the file\'s values anywhere on the page');

      phase = where + 'technical BASIS_MISMATCH';
      await expand(page, 'technical'); w.log.length = 0; delete w.lastAt;
      w.answers.analysis = () => ({ status: 200, body: X.analysis({ adopted: true, basis: 'SPLIT_ADJUSTED' }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym, basis: 'SPLIT_ADJUSTED' }) });
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(await page.locator('[data-private-basis-agreement]').evaluateAll((n) => n.map((x) => [x.dataset.privateBasisPart, x.dataset.privateBasisAgreement])),
        [['analysis', 'BASIS_MISMATCH'], ['measures', 'BASIS_MISMATCH']], phase + ': both results refused on a 원주가 chart');
      assert.equal(await count(page, '[data-private-metric]'), 0, phase + ': no value attached');

      phase = where + 'technical SYMBOL_MISMATCH';
      // The Worker passes the pinned view through unread (owner 2026-11-21 light read): the screen refuses a view of another company.
      await expand(page, 'technical'); delete w.lastAt;
      const chartBefore = w.answers.chart;
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      w.answers.chart = () => ({ status: 200, body: X.bars({ symbol: 'AMD' }) });
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'ERROR');
      assert.match(await note(page, 'technical'), /SYMBOL_MISMATCH/, phase + ': a view of another company is refused with its code');
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': nothing of the refused view');
      w.answers.chart = chartBefore; delete w.lastAt;
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'READY');

      phase = where + 'technical measures 404 alone';
      await expand(page, 'technical'); delete w.lastAt;
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      w.answers.technical = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await expand(page, 'technical'); await page.locator('[data-private-measures=EMPTY]').waitFor({ timeout: 30000 });
      assert.equal(await state(page, 'tech-kis-chart'), 'READY', phase + ': the analysis and chart stay');

      phase = where + 'technical EMPTY vs ERROR';
      await expand(page, 'technical'); delete w.lastAt;
      w.answers.analysis = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'EMPTY');
      assert.equal(await note(page, 'technical'), '자료 없음', phase + ': no file is 자료 없음');
      assert.equal(await page.locator('[data-private-disconnect=technical]').isVisible(), true, phase + ': a missing file keeps the session');
      delete w.lastAt;
      w.answers.analysis = () => { const a = X.analysis(); a.schema = X.K('bars/2/analysis'); return { status: 200, body: a }; };
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'ERROR');
      assert.match(await note(page, 'technical'), /^형식 오류 · SCHEMA_VERSION$/, phase + ': a refused file is ERROR with its code');
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': nothing of a refused file');
      await page.waitForTimeout(5100);
      w.answers.analysis = () => ({ status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } });
      await expand(page, 'technical'); await page.waitForFunction(() => document.querySelector('[data-private-note=technical]').textContent === '비공개 자료 서버 응답 없음', null, { timeout: 30000 });
      assert.equal(await state(page, 'tech-kis-chart'), 'ERROR');

      phase = where + 'technical 403 and disconnect';
      await page.waitForTimeout(5100);
      w.answers.analysis = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'LOGIN_REQUIRED');
      assert.equal(await note(page, 'technical'), '서버가 오너 확인을 거부했습니다 · 다시 로그인하세요');
      assert.deepEqual([await page.locator('[data-private-disconnect=technical]').isVisible(), await page.locator('[data-private-status-area=technical]').isVisible()], [false, false], phase + ': the session and the 상태 box are gone');
      await boundaries(page, seen, w, phase); await ctx.close(); pass++;
    }
    // ================================================================ QGV KIS V, 390
    {
      phase = where + 'qgv 390';
      const { ctx, page, seen, w } = await context(390);
      await page.goto(s.base + entry + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
      await page.locator('[data-private-expand=qgv]').waitFor();
      const ranks = () => page.locator('[data-lb-table] tbody tr[data-row]').evaluateAll((n) => n.map((tr) => [tr.dataset.row, (tr.querySelector('td[data-cell=rank]') || {}).textContent || null]));
      const r0 = await ranks(), id = r0[0][0];
      const [code, other] = await page.evaluate((ids) => ids.map((x) => { const c = window.IS2.companies.get(x); return c && c.code ? c.code : x; }), [id, r0[1][0]]);
      await publicByDefault(page, w, 'qgv', 'qgv-kis');
      await signIn(page, 'qgv', 'qgv-kis');
      await page.evaluate((c) => window.IS2.selection.set(c), id);
      // Codex #556 official_reference output (codexQgv): the chosen company gets a kept row that has Q and G.
      const Q556 = X.codexQgv([other, code, 'NYSE:ZZZZ']), row = Q556.rows[code], r1 = (x) => String(Math.round(x * 10) / 10);
      w.answers.qgv = () => ({ status: 200, body: Q556 });
      await expand(page, 'qgv'); await page.locator('[data-private-row="' + code + '"]').waitFor({ timeout: 20000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/stock?part=qgv'], phase + ': one read of the qgv part of the stock route for the click');
      assert.equal(await count(page, '[data-private-timing]'), 0, phase + ': no timing button');
      assert.equal(await text(page, '[data-private-layer=qgv]'), 'KIS · 비공개 · 공식 아님 · 가격 기준일 2026-10-23 · 출처 KIS · 계산 판 ' + Q556.calc_version + ' 검증 전(참고)', phase + ': label, price basis day, source, calc version and the producer\'s tag');
      assert.deepEqual(await page.locator('[data-private-row="' + code + '"] [data-private-axis] td').allTextContents(),
        [r1(row.axes.Q.score), r1(row.axes.G.score), '미산출 · 사유 코드 ' + row.axes.V.reason], phase + ': the file\'s scores as given, V 미산출 with its reason, never 0');
      assert.equal(await text(page, '[data-private-total] td'), '총점 미산출 · 세 축 필요', phase + ': the producer masked the partial total: no total, one short reason');
      assert.deepEqual(await ranks(), r0, phase + ': the public ranks are unchanged');
      // RAM rule for the private values (the synthetic scores also occur on the public board, so they cannot be page-wide sentinels):
      // each private score is text inside [data-ram-price] only, and no attribute of the panel carries it.
      assert.deepEqual(await page.locator('[data-private-row="' + code + '"] [data-private-axis] td [data-ram-price]').allTextContents(), [r1(row.axes.Q.score), r1(row.axes.G.score), '미산출 · 사유 코드 ' + row.axes.V.reason], phase + ': private values as RAM text');
      assert.ok(await page.locator('[data-private-panel=qgv-kis]').evaluate((p, v) => ![...p.querySelectorAll('*')].some((e) => [...e.attributes].some((a) => v.some((x) => a.value.includes(x)))), [r1(row.axes.Q.score), r1(row.axes.G.score)]), phase + ': no private value in an attribute');
      // No display fields (the #493 shape): fail closed, no value.
      await expand(page, 'qgv'); delete w.lastAt;
      w.answers.qgv = () => ({ status: 200, body: X.qgv({ codes: [code, other] }) });
      await expand(page, 'qgv'); await page.locator('[data-private-display=UNKNOWN]').waitFor({ timeout: 20000 });
      assert.deepEqual([await text(page, '[data-private-display=UNKNOWN]'), await count(page, '[data-private-axis]'), await count(page, '[data-private-verification]')], ['검증 표시 없음', 0, 0], phase + ': fail closed');
      // A refused file (a rank) is ERROR, a missing one EMPTY, 403 back to a sign-in.
      await expand(page, 'qgv'); delete w.lastAt;
      w.answers.qgv = () => { const q = X.qgv({ codes: [code, other] }); q.rank = 1; return { status: 200, body: q }; };
      await expand(page, 'qgv'); await waitState(page, 'qgv-kis', 'ERROR');
      assert.match(await note(page, 'qgv'), /RANK_NOT_ALLOWED/);
      delete w.lastAt; w.answers.qgv = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await expand(page, 'qgv'); await waitState(page, 'qgv-kis', 'EMPTY');
      delete w.lastAt; w.answers.qgv = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await expand(page, 'qgv'); await waitState(page, 'qgv-kis', 'LOGIN_REQUIRED');
      assert.deepEqual(await ranks(), r0, phase + ': public ranks unchanged after a refusal');
      await boundaries(page, seen, w, phase); await ctx.close(); pass++;
    }
    await s.close(); s = null;
    if (pagesOut) { fs.rmSync(pagesOut, { recursive: true, force: true }); pagesOut = null; }
   }
    console.log('web_app_kis_private_browser_test: PASS (' + pass + ' groups, development build and Pages artifact app.html: technical 1440 (public default, sign-in, read token status NO_EXPIRY / rejected / mismatch / malformed, one stock-route read, BASIS_MISMATCH, SYMBOL_MISMATCH, measures 404 alone, EMPTY vs ERROR, 500, 403), technical tiers from Codex #556 output (검증됨, 검증 전(참고), WITHHELD, fail closed), qgv 390 (the qgv part of the stock route, Codex #556 kis-qgv/1, KIS V label, V 미산출, fail closed, ERROR / EMPTY / 403, public ranks unchanged))');
  } catch (e) {
    console.error('web_app_kis_private_browser_test failed at ' + phase + ':', e && e.stack || e);
    process.exitCode = 1;
  } finally {
    await browser.close();
    if (s) await s.close();
    if (pagesOut) fs.rmSync(pagesOut, { recursive: true, force: true });
  }
})();
