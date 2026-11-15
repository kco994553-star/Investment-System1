'use strict';
// Owner-private KIS panels (owner 2026-11-05 DC-44, 2026-11-14 DC-52, 2026-11-15 DC-53; Codex #480 contract) on the development
// build, in a real browser: 2-1 of #/technical (tech-kis-chart) and the KIS V panel of #/qgv (qgv-kis). Google and the private
// Worker are stand-ins; every payload is the synthetic fixture tools/web_app_kis_private_fixture.js (no company, no KIS value).
// Behaviour and boundary only (owner 2026-11-15: no appearance checks beyond these):
//  - Public by default: before any click each panel is LOGIN_REQUIRED (로그인 필요) with an empty body and nothing goes to the
//    Worker; a synthetic click sends nothing.
//  - Sign-in inside clicks (Google script, then a token for scope exactly openid email); reads only after a click, only the
//    Worker's /kis routes, each with the Bearer header alone (no cookie, no referrer), the reads of one click 5 s apart.
//  - Owner states: READY (label, price basis day, numbers; raw diagnostic values never on the page; values only as text inside
//    [data-ram-price]), BASIS_MISMATCH (no indicator attached), EMPTY (404 KIS_SERIES_NOT_FOUND: 자료 없음, session kept) apart
//    from ERROR (a refused payload, a 500), a server 403 back to LOGIN_REQUIRED, 연결 끊기.
//  - Read token status in the 상태 box, on its own click: NO_EXPIRY reads 만료일 없음; a rejection and a mismatch have their own
//    words and one short line on the panel.
//  - QGV: label KIS · 비공개 · 공식 아님 with the price basis day, source and calc version, V 미산출 never 0, no total without V, the
//    public ranks unchanged. Each cell carries one verification tag (검증됨 / 검증 전(참고)).
//  - Boundaries: no token or private value in storage, the address, the console or a public request; no CSP violation.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
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
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
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
        const a = (w.answers[url.pathname.slice(5)] || (() => ({ status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } })))(url.searchParams.get('symbol'));
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
    // ================================================================ technical 2-1, 1440
    {
      phase = 'technical 1440';
      const { ctx, page, seen, w } = await context(1440);
      await page.goto(s.base + '#/technical/NASDAQ%3ANVDA'); await page.locator('main[data-route=technical]').waitFor();
      await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 }); await page.locator('[data-private-expand=technical]').waitFor();
      const holds = await count(page, '[data-indicator] [data-verdict]');
      await publicByDefault(page, w, 'technical', 'tech-kis-chart');
      await signIn(page, 'technical', 'tech-kis-chart');
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');

      // Read token status, on its own click inside the 상태 box (DC-53).
      phase = 'technical read token status';
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

      phase = 'technical READY';
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      w.answers.chart = (sym) => ({ status: 200, body: X.bars({ symbol: sym }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym }) });
      delete w.lastAt;
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/analysis?symbol=NVDA', '/kis/chart?symbol=NVDA', '/kis/technical?symbol=NVDA'], phase + ': exactly the three reads for the click');
      assert.equal(w.refused || 0, 0, phase + ': no read refused by the one-at-a-time limiter');
      assert.match(await text(page, '[data-private-layer=technical]'), /^KIS · 비공개 · 가격 기준일 2026-10-30 · 원주가 검증 전\(참고\)$/, phase + ': label, basis day, basis and the verification tag');
      assert.equal(await page.locator('[data-private-layer=technical] [data-private-verification]').getAttribute('data-private-verification'), 'REFERENCE');
      assert.equal(await count(page, 'svg[data-private-chart=NVDA] [data-private-close-line]'), 1, phase + ': the close line');
      assert.deepEqual(await page.locator('[data-private-held]').evaluateAll((n) => n.map((x) => x.dataset.privateHeld)), ['MACD_12_26', 'RSI_14', 'SMA_20'], phase + ': held indicators as 미산출');
      assert.equal(await count(page, '[data-private-measures=READY]'), 1);
      assert.deepEqual(await page.locator('[data-private-measure]').evaluateAll((n) => n.map((x) => [x.dataset.privateMeasure, x.dataset.privateMeasureKind])),
        [['momentum_3m', 'VALUE'], ['momentum_6m', 'DIAGNOSTIC'], ['momentum_12m', 'NOT_COMPUTED'], ['volatility_6m', 'NOT_COMPUTED'], ['dollar_volume_6m', 'NOT_COMPUTED']]);
      assert.deepEqual(site.leaks([await page.content()], [...RAW, ...X.MEASURE_RAW]), [], phase + ': no raw diagnostic value anywhere on the page');
      assert.deepEqual(await page.locator('[data-private-panel=tech-kis-chart] [data-ram-price]').allTextContents(), ['2026-10-30 · 105.5', '12.4242 %'], phase + ': values as RAM text only');
      await site.assertRamOnly(page, ['105.5', '12.4242'], phase);
      assert.ok((await text(page, '[data-private-facts=technical]')).includes('KIS 보관 일봉 (MODP=0)'), phase + ': the file facts are in the 상태 box');
      assert.equal(await count(page, '[data-indicator] [data-verdict]'), holds, phase + ': the public verdicts are unchanged');

      phase = 'technical BASIS_MISMATCH';
      await expand(page, 'technical'); w.log.length = 0; delete w.lastAt;
      w.answers.analysis = () => ({ status: 200, body: X.analysis({ adopted: true, basis: 'SPLIT_ADJUSTED' }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym, basis: 'SPLIT_ADJUSTED' }) });
      await expand(page, 'technical'); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.deepEqual(await page.locator('[data-private-basis-agreement]').evaluateAll((n) => n.map((x) => [x.dataset.privateBasisPart, x.dataset.privateBasisAgreement])),
        [['analysis', 'BASIS_MISMATCH'], ['measures', 'BASIS_MISMATCH']], phase + ': both results refused on a 원주가 chart');
      assert.deepEqual([await count(page, '[data-private-indicator]'), await count(page, '[data-private-measure]')], [0, 0], phase + ': no value attached');

      phase = 'technical measures 404 alone';
      await expand(page, 'technical'); delete w.lastAt;
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      w.answers.technical = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await expand(page, 'technical'); await page.locator('[data-private-measures=EMPTY]').waitFor({ timeout: 30000 });
      assert.equal(await state(page, 'tech-kis-chart'), 'READY', phase + ': the analysis and chart stay');

      phase = 'technical EMPTY vs ERROR';
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

      phase = 'technical 403 and disconnect';
      await page.waitForTimeout(5100);
      w.answers.analysis = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await expand(page, 'technical'); await waitState(page, 'tech-kis-chart', 'LOGIN_REQUIRED');
      assert.equal(await note(page, 'technical'), '서버가 오너 확인을 거부했습니다 · 다시 로그인하세요');
      assert.deepEqual([await page.locator('[data-private-disconnect=technical]').isVisible(), await page.locator('[data-private-status-area=technical]').isVisible()], [false, false], phase + ': the session and the 상태 box are gone');
      await boundaries(page, seen, w, phase); await ctx.close(); pass++;
    }
    // ================================================================ QGV KIS V, 390
    {
      phase = 'qgv 390';
      const { ctx, page, seen, w } = await context(390);
      await page.goto(s.base + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
      await page.locator('[data-private-expand=qgv]').waitFor();
      const ranks = () => page.locator('[data-lb-table] tbody tr[data-row]').evaluateAll((n) => n.map((tr) => [tr.dataset.row, (tr.querySelector('td[data-cell=rank]') || {}).textContent || null]));
      const r0 = await ranks(), id = r0[0][0];
      const [code, other] = await page.evaluate((ids) => ids.map((x) => { const c = window.IS2.companies.get(x); return c && c.code ? c.code : x; }), [id, r0[1][0]]);
      await publicByDefault(page, w, 'qgv', 'qgv-kis');
      await signIn(page, 'qgv', 'qgv-kis');
      await page.evaluate((c) => window.IS2.selection.set(c), id);
      w.answers.qgv = () => ({ status: 200, body: X.qgv({ codes: [code, other], priceBasis: '2026-10-30' }) });
      await expand(page, 'qgv'); await page.locator('[data-private-row="' + code + '"]').waitFor({ timeout: 20000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/qgv'], phase + ': one read for the click');
      assert.equal(await text(page, '[data-private-layer=qgv]'), 'KIS · 비공개 · 공식 아님 · 가격 기준일 2026-10-30 · 출처 KIS · 계산 판 SYNTHETIC-CALC 검증 전(참고)', phase + ': label, price basis day, source, calc version and the verification tag');
      assert.deepEqual(await page.locator('[data-private-row="' + code + '"] [data-private-axis] td').allTextContents(), ['70.3', '60.5', '미산출 · 사유 코드 V_INPUTS_NOT_AVAILABLE'], phase + ': V 미산출 with its reason, never 0');
      assert.equal(await text(page, '[data-private-total] td'), 'QGV 총점 미산출 · V 미산출', phase + ': no total without V');
      assert.deepEqual(await ranks(), r0, phase + ': the public ranks are unchanged');
      await site.assertRamOnly(page, ['70.3', '60.5'], phase);
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
    console.log('web_app_kis_private_browser_test: PASS (' + pass + ' groups: technical 1440 (public default, sign-in, read token status NO_EXPIRY / rejected / mismatch / malformed, three reads, BASIS_MISMATCH, measures 404 alone, EMPTY vs ERROR, 500, 403), qgv 390 (KIS V label, V 미산출, ERROR / EMPTY / 403, public ranks unchanged))');
  } catch (e) {
    console.error('web_app_kis_private_browser_test failed at ' + phase + ':', e && e.stack || e);
    process.exitCode = 1;
  } finally {
    await browser.close();
    await s.close();
  }
})();
