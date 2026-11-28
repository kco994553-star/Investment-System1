'use strict';
// The one automatic retry of an owner-private read (owner 2026-11-28, Worker CPU recovery): #/technical 2-1 KIS panel at 1440 on
// the development build, against a Worker stand-in that scripts each /kis/stock answer.
//  - A read whose answer never came (the request fails, as when the runtime stops the Worker at its CPU limit, error 1102) or a
//    5xx without the Worker's code: the status line counts 「다시 시도하는 중 · N초」 down ([data-private-retry] = seconds left),
//    then exactly one more read, at least the Worker's worst case after the first send (token check 5 s + admission 2 s +
//    lease 15 s + 1 s = 23 s); its result is final.
//  - At most two sends per read in every case: lost → lost / 429 / 503 page, 429 → lost / 503 page / 429 (the layer's one
//    spaced resend on 429 is unchanged and never shows the countdown); 403 and a coded 503 are never resent.
//  - A waiting retry is dropped, never sent: after 연결 끊기 and a new sign-in (a new session), and after leaving the screen.
//  Every read carries the Bearer header only. Synthetic values only.
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
const TOKEN = ['memory', 'only', 'synthetic', 'kis', 'retry', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
// Each sign-in gets its own token (TOKEN-1, TOKEN-2, …), so a read shows which session sent it.
const GIS_STUB = 'window.__gisN=0;window.google={accounts:{oauth2:{initTokenClient:function(cfg){'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN + '-') + '+(++window.__gisN),expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const FIXTURES = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } };
const RECOVERY_MS = 5000 + 2000 + 15000 + 1000;   // prices.js KIS_RECOVERY_MS
const CORS = { 'access-control-allow-origin': '*', 'cache-control': 'no-store' };

// The one-file stock view the panel reads (the stock route's answer), from Codex #556's synthetic 'available' output.
function stockView() {
  const f = X.codex556('available', { symbol: 'NVDA' }), c = f.chart;
  const { bars, raw_bars: rawBars, schema, ...header } = c; void rawBars; void schema;
  const fields = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'SMA_20', 'SMA_60', 'SMA_120', 'BOLL_MIDDLE_20', 'BOLL_UPPER_20_2',
    'BOLL_LOWER_20_2', 'RSI_14', 'MACD_12_26', 'MACD_SIGNAL_9', 'MACD_HISTOGRAM_12_26_9'];
  return { schema: X.K('stock-view/1'), publication_scope: 'OWNER_PRIVATE_ONLY', symbol: c.symbol, evaluation_day: f.technical.evaluation_day,
    fields, rows: bars.map((b) => [b.date, b.open, b.high, b.low, b.close, b.volume, ...Array(11).fill(null)]),
    chart: { ...header, schema: X.K('chart-metadata/1') }, indicators: {},
    coverage: { scope: 'ALL_RETAINED_SESSIONS', retained_sessions: bars.length, retained_start: bars[0].date, retained_end: bars[bars.length - 1].date },
    latest: { technical: f.technical, measures: f.measures }, additional_requests_for_toggle: 0, additional_requests_for_retained_period: 0 };
}
// Scripted answers, one per /kis/stock read in order: 'lost' (the request fails), 'html503' (a 503 page without the Worker's
// code), or [status, body] (the Worker's own JSON answer); 'ok' is the view.
const ANSWERS = { ok: () => [200, stockView()], forbidden: () => [403, { error: { code: 'AUTH_FORBIDDEN' } }],
  limited: () => [429, { error: { code: 'RATE_LIMITED' } }], coded503: () => [503, { error: { code: 'UPSTREAM_UNAVAILABLE' } }] };

let phase = 'START';
(async () => {
  let s = null;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  async function open(script) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: [] });
    const w = { reads: [], unexpected: [], script: [...script] };
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url());
      if (url.origin === s.origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER && url.pathname === '/kis/stock' && req.method() === 'GET') {
        const kind = w.script.shift() || 'unscripted';
        w.reads.push({ at: Date.now(), kind, path: url.pathname + url.search, auth: req.headers().authorization || null, cookie: req.headers().cookie || null });
        if (kind === 'lost') { await route.abort('failed'); return; }
        if (kind === 'html503') { await route.fulfill({ status: 503, contentType: 'text/html', headers: CORS, body: '<!doctype html><title>Worker exceeded resource limits</title>' }); return; }
        const [status, body] = (ANSWERS[kind] || (() => [500, { error: { code: 'UNSCRIPTED' } }]))();
        await route.fulfill({ status, contentType: 'application/json', headers: CORS, body: JSON.stringify(body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    await page.goto(s.base + '#/technical/NASDAQ%3ANVDA'); await page.locator('main[data-route=technical]').waitFor();
    await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 }); await page.locator('[data-private-expand=technical]').waitFor();
    const note = () => page.locator('[data-private-note=technical]').evaluate((e) => [e.textContent, e.dataset.privateRetry === undefined ? null : e.dataset.privateRetry]);
    const expand = () => page.locator('[data-private-expand=technical]').click();
    // Sign in (the first click loads the Google script, the second asks for the token).
    await expand(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 20000 });
    await expand(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
    // Every text the status line shows from here on.
    await page.evaluate(() => { const n = document.querySelector('[data-private-note=technical]'); window.__notes = [];
      new MutationObserver(() => window.__notes.push([n.textContent, n.dataset.privateRetry === undefined ? null : n.dataset.privateRetry])).observe(n, { childList: true, characterData: true, subtree: true, attributes: true }); });
    return { ctx, page, seen, w, note, expand, notes: () => page.evaluate(() => window.__notes) };
  }
  const panelState = (page) => page.locator('[data-private-panel=tech-kis-chart]').getAttribute('data-private-state');
  function common(w, seen, label, perClick = [w.reads.length], also = null) {
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    for (const k of perClick) assert.ok(k <= 2, label + ': at most two sends per read (' + k + ')');
    for (const r of w.reads) { assert.deepEqual([r.path, r.cookie], ['/kis/stock?symbol=NVDA', null], label + ': the stock read, no cookie');
      assert.match(r.auth, new RegExp('^Bearer ' + TOKEN + '-\\d+$'), label + ': the Bearer header only'); }
    assert.deepEqual(seen.errors.filter((e) => !/status of (403|429|503)|ERR_FAILED|Failed to fetch/.test(e) && !(also && also.test(e))), [], label + ': no page error but the stand-in refusals');
  }
  const RETRY_TEXT = /^다시 시도하는 중 · (\d+)초$/;
  try {
    s = await site.start({ fixtures: FIXTURES });

    for (const [label, script] of [['a lost read (request failed)', ['lost', 'ok']], ['a 503 page without the Worker\'s code', ['html503', 'ok']]]) {
      phase = label + ', then served';
      const { ctx, page, seen, w, note, expand, notes } = await open(script);
      await expand();
      await page.waitForFunction(() => /^다시 시도하는 중 · \d+초$/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 15000 });
      const first = await note();
      assert.match(first[0], RETRY_TEXT, phase + ': the countdown line');
      assert.equal(first[1], RETRY_TEXT.exec(first[0])[1], phase + ': [data-private-retry] holds the seconds left');
      assert.ok(Number(first[1]) >= 21 && Number(first[1]) <= 23, phase + ': about 23 s to wait (' + first[1] + ')');
      await page.waitForTimeout(2200);
      const later = await note();
      assert.match(later[0], RETRY_TEXT); assert.ok(Number(later[1]) <= Number(first[1]) - 2, phase + ': counting down (' + first[1] + ' → ' + later[1] + ')');
      assert.equal(w.reads.length, 1, phase + ': no second read while it counts down');
      await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.equal(await panelState(page), 'READY', phase + ': the retry is served');
      assert.deepEqual(w.reads.map((r) => r.kind), script, phase + ': exactly one more read');
      assert.ok(w.reads[1].at - w.reads[0].at >= RECOVERY_MS - 300, phase + ': the retry waits out the Worker\'s worst case (' + (w.reads[1].at - w.reads[0].at) + ' ms)');
      assert.deepEqual(await note(), ['', null], phase + ': the countdown is gone once served');
      const seenNotes = await notes();
      const secs = seenNotes.map(([t]) => RETRY_TEXT.exec(t)).filter(Boolean).map((m) => Number(m[1]));
      assert.ok(secs.length >= 10 && secs.every((x, i) => i === 0 || x <= secs[i - 1]), phase + ': one line per second, never counting up');
      assert.ok(seenNotes.some(([t, r]) => t === '다시 시도하는 중' && r === '0'), phase + ': 다시 시도하는 중 while the retry runs');
      common(w, seen, phase); await ctx.close();
    }

    for (const [second, line] of [['lost', '비공개 자료 서버 응답 없음'], ['limited', '요청이 많아 잠시 뒤 다시'], ['html503', '비공개 자료 서버 응답 없음']]) {
      phase = 'lost, then ' + second + ': the retry\'s answer is final';
      const { ctx, page, seen, w, note, expand } = await open(['lost', second, 'ok']);
      await expand();
      await page.locator('[data-private-panel=tech-kis-chart][data-private-state=ERROR]').waitFor({ timeout: 45000 });
      assert.deepEqual(await note(), [line, null], phase + ': its fixed line, no countdown left');
      await page.waitForTimeout(7000);
      assert.deepEqual(w.reads.map((r) => r.kind), ['lost', second], phase + ': exactly one retry, no third send');
      common(w, seen, phase); await ctx.close();
    }

    for (const [label, script, endState, line, reads] of [
      ['403 (the Worker refused the owner)', ['forbidden', 'ok'], 'LOGIN_REQUIRED', /오너 확인을 거부/, ['forbidden']],
      ['a coded 503 (the Worker\'s own UPSTREAM_UNAVAILABLE)', ['coded503', 'ok'], 'ERROR', /^비공개 자료 서버 응답 없음$/, ['coded503']],
      ['429 twice (the layer\'s one spaced resend, no countdown)', ['limited', 'limited', 'ok'], 'ERROR', /^요청이 많아 잠시 뒤 다시$/, ['limited', 'limited']],
      ['429, then lost (the resend\'s failure is final, no unreachable retry)', ['limited', 'lost', 'ok'], 'ERROR', /^비공개 자료 서버 응답 없음$/, ['limited', 'lost']],
      ['429, then a 503 page', ['limited', 'html503', 'ok'], 'ERROR', /^비공개 자료 서버 응답 없음$/, ['limited', 'html503']],
    ]) {
      phase = label;
      const { ctx, page, seen, w, note, expand, notes } = await open(script);
      await expand();
      await page.locator('[data-private-panel=tech-kis-chart][data-private-state=' + endState + ']').waitFor({ timeout: 30000 });
      assert.match((await note())[0], line, phase + ': its own line');
      await page.waitForTimeout(reads.length === 2 && reads[1] !== 'limited' ? 7000 : 3000);
      assert.deepEqual(w.reads.map((r) => r.kind), reads, phase + ': no unreachable retry');
      assert.ok(!(await notes()).some(([t, r]) => /다시 시도하는 중/.test(t) || r !== null), phase + ': the countdown never shows');
      common(w, seen, phase); await ctx.close();
    }
    // A waiting retry belongs to its click and its session.
    phase = 'lost, then 연결 끊기 and a new sign-in while counting down: the old retry is never sent';
    { const { ctx, page, seen, w, note, expand } = await open(['lost', 'ok', 'ok']);
      await expand();
      await page.waitForFunction(() => /^다시 시도하는 중 · \d+초$/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 15000 });
      await page.locator('[data-private-disconnect=technical]').click();
      await page.waitForFunction(() => /연결을 끊었습니다/.test(document.querySelector('[data-private-note=technical]').textContent));
      await expand(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
      assert.equal(await page.evaluate(() => window.__gisN), 2, phase + ': a second sign-in, a new token');
      await page.waitForTimeout(Math.max(0, w.reads[0].at + RECOVERY_MS + 3000 - Date.now()));
      assert.deepEqual(w.reads.map((r) => r.kind), ['lost'], phase + ': the first click\'s retry never went out');
      assert.ok(!(await note())[0].includes('다시 시도하는 중'), phase + ': no countdown left');
      const clicked = Date.now();
      await expand(); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 30000 });
      assert.equal(w.reads.length, 2, phase + ': the new click\'s one read');
      assert.equal(w.reads[1].auth, 'Bearer ' + TOKEN + '-2', phase + ': sent in the new session');
      assert.ok(w.reads[1].at >= clicked, phase + ': after the new click');
      common(w, seen, phase, [1, 1]); await ctx.close(); }

    phase = 'lost, then leaving the screen while counting down: the retry is never sent';
    { const { ctx, page, seen, w } = await open(['lost', 'ok']);
      await page.locator('[data-private-expand=technical]').click();
      await page.waitForFunction(() => /^다시 시도하는 중 · \d+초$/.test(document.querySelector('[data-private-note=technical]').textContent), null, { timeout: 15000 });
      await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route=qgv]').waitFor({ timeout: 20000 });
      await page.waitForTimeout(Math.max(0, w.reads[0].at + RECOVERY_MS + 3000 - Date.now()));
      assert.deepEqual(w.reads.map((r) => r.kind), ['lost'], phase + ': no retry after the screen is gone');
      // The public #/qgv screen asks for public files this test site does not serve (404): not part of this check.
      common(w, seen, phase, undefined, /status of 404/); await ctx.close(); }

    console.log('web_app_kis_private_retry_browser_test: PASS (development build, technical 1440: lost read → countdown 다시 시도하는 중 · N초 → one retry after 23 s → READY; 503 page without a code → the same; lost → lost / 429 / 503 page final, no third send; 429 → 429 / lost / 503 page final; 403 / coded 503 never resent; at most two sends per read; a waiting retry dropped after 연결 끊기 + a new sign-in and after leaving the screen)');
  } catch (e) {
    console.error('web_app_kis_private_retry_browser_test failed at ' + phase + ':', e && e.stack || e);
    process.exitCode = 1;
  } finally {
    await browser.close();
    if (s) await s.close();
  }
})();
