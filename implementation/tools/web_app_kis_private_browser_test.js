'use strict';
// 비공개 펼치기 (owner 2026-11-05, DC-44; Codex #480 contract) on the two existing private panels, in a real browser: 2-1 of
// #/technical (tech-kis-chart) and 2.1.6 of #/qgv (qgv-kis). Google and the private Worker are stand-ins; every payload is the
// synthetic fixture tools/web_app_kis_private_fixture.js (no company, no KIS value). Checks:
//  - Public by default: before any click the panel waits for a sign-in (LOGIN_REQUIRED) with an empty body, the public part
//    (verdicts on hold, the leaderboard ranks) is drawn as before, and nothing goes to the Worker. A synthetic click does nothing.
//  - Sign-in inside clicks: the first click loads the Google script, the second asks for a token with scope exactly openid email
//    (include_granted_scopes false), the third reads. The token is never stored.
//  - Requests: only the Worker's /kis routes, only after a click, each with the Bearer header alone (no cookie, no referrer).
//  - Technical: source, price basis day, capture time, 원주가, correction, status, basis comparison (공개 기준일 없음 → 직접 비교
//    제한), the close line, adopted indicators only (raw diagnostic values never shown, the count only), held indicators as 미산출
//    with their reasons; the last close only as text inside [data-ram-price].
//  - QGV: coverage lines, the chosen company's Q / G and V 미산출 with its reason (never 0), no total without V, no private rank,
//    the line that the public official ranks and TARGET are unchanged, and the public ranks identical before / after; basis day
//    same vs different.
//  - Server refusal (403) drops the token and the panel asks to sign in again; an expired token is dropped before a read (no
//    request); 연결 끊기 and 접기 clear what was shown; a missing file is 자료 없음 (EMPTY, the session kept); a payload that
//    breaks the contract is refused whole (ERROR).
//  - Technical five measures (kis-technical-measures/1, the third read of the same click): 채택값 inside [data-ram-price] only,
//    진단값 as a count (never a value), 미산출 with reasons, windows, signal day, no rank; a missing measures file (404) makes that
//    part alone 자료 없음 and a refused one that part alone refused — the analysis and the chart stay.
//  - Macro (#/macro 4.1.3, macro-observed-private) and news (#/news 5.2.7, news-refresh-private): the private copy in the public
//    file's format, read by the public readers and drawn by the public block's own function, under 비공개 보관본 · 인증 경로 and
//    the two-layer line; macro still shows no observed value; the public block is the same before and after; 403 / 404 /
//    refused payload / 연결 끊기; one /kis read per click.
//  - Boundaries: no private value, raw value or token in storage, the address, the console or a public request; no style
//    attribute, no CSP violation, no horizontal overflow at 390.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_kis_private_fixture.js');
const MX = require('./web_app_macro_observed_fixture.js');
const NX = require('./web_app_news_fixture.js');
const NFX = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/news_signals_refresh_v2_synthetic.json'), 'utf8')).cases;

const NOW = '2026-10-31T06:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text, PUB = JSON.parse(PUB_TEXT);
const TOKEN = ['memory', 'only', 'synthetic', 'kis', 'private', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
// Google's answer for openid email (Google spells email as the userinfo URL); window.__gisCfg keeps what the page asked for.
const GIS_STUB = 'window.__gisCfg=[];window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gisCfg.push({scope:cfg.scope,igs:cfg.include_granted_scopes});'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const RAW = ['101.25', '55.5'];                                  // raw diagnostic values in the analysis fixture: never on the page
const CLOSES = X.bars().bars.map((b) => b.close);               // synthetic closes: only inside [data-ram-price]
const ADOPTED = '12.4242';                                       // the adopted 3m momentum of X.measures(): only inside [data-ram-price]
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' },
    'sec-disclosures.json': { json: NX.sec() }, 'news-signals.json': { json: NFX.gdelt_429_ir_updated.payload }, 'dart-disclosures.json': { json: NX.dart() } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  // The Worker stand-in: answers[route] = () => {status, body}; requests are logged with the headers that matter.
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
        const route_ = url.pathname.slice(5);
        // The real Worker admits one owner request at a time, at least 5 s apart (MIN_SPACING_MS); the stand-in refuses the same way,
        // so a screen that sends a click's reads together fails here as it did on the retained-archive replay (2026-11-05).
        const at = Date.now(), early = w.lastAt !== undefined && at - w.lastAt < 5000;
        if (early) { w.refused = (w.refused || 0) + 1; await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ error: { code: 'RATE_LIMITED' } }) }); return; }
        w.lastAt = at;
        w.log.push({ at, path: url.pathname + url.search, auth: hd.authorization || null, cookie: hd.cookie || null, referer: hd.referer || null });
        const a = (w.answers[route_] || (() => ({ status: 500, body: { error: { code: 'UPSTREAM_UNAVAILABLE' } } })))(url.searchParams.get('symbol'));
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: JSON.stringify(a.body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    return { ctx, page, seen, w };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));
  const count = (page, sel) => page.locator(sel).count();
  const state = (page, id) => page.locator('[data-private-panel="' + id + '"]').getAttribute('data-private-state');
  const waitState = (page, id, st) => page.locator('[data-private-panel="' + id + '"][data-private-state="' + st + '"]').waitFor({ timeout: 20000 });
  const note = (page, kind) => text(page, '[data-private-note="' + kind + '"]');
  const body = (page, id) => text(page, '[data-private-panel="' + id + '"] .private-body');
  async function signIn(page, kind, id) {
    const btn = page.locator('[data-private-expand="' + kind + '"]');
    await btn.click(); await page.waitForFunction((k) => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note="' + k + '"]').textContent), kind, { timeout: 20000 });
    assert.equal(await state(page, id), 'LOGIN_REQUIRED', phase + ': loading the Google script is not a sign-in');
    await btn.click(); await page.waitForFunction((k) => /^로그인됨/.test(document.querySelector('[data-private-note="' + k + '"]').textContent), kind);
    assert.equal(await state(page, id), 'READY', phase + ': signed in, still folded');
    assert.equal(await count(page, '[data-private-panel="' + id + '"] [data-private-closed]'), 1);
    assert.equal(await page.locator('[data-private-disconnect="' + kind + '"]').isVisible(), true, phase + ': 연결 끊기 shown once signed in');
  }
  async function boundaries(page, seen, w, label) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    assert.deepEqual(seen.errors.filter((e) => !/status of (403|404|429)/.test(e)), [], label + ': no console or page error but the stand-in refusals');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    for (const l of w.log) assert.deepEqual([l.auth, l.cookie, l.referer], ['Bearer ' + TOKEN, null, null], label + ': Bearer header only, no cookie, no referrer');
    const st = await site.storage(page);
    assert.equal(st.session, 0, label + ': nothing in session storage');
    assert.ok(!Object.keys(st.localItems).some((k) => /kis|token|private-layer/i.test(k)), label + ': no private key on the device');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), page.url(), await page.evaluate(() => JSON.stringify(history.state)), ...seen.errors, ...w.all.filter((u) => !u.includes(WORKER))],
      [TOKEN, ...RAW, ...CLOSES, ...X.MEASURE_RAW, ADOPTED, '70.3', 'SYNTHETIC-SECURITY-1']), [], label + ': no token or private value in storage, the address, the console or another request');
  }

  try {
    // ================================================================ technical 2-1, 1440
    {
      phase = 'technical 1440';
      const { ctx, page, seen, w } = await context(1440);
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      w.answers.chart = (sym) => ({ status: 200, body: X.bars({ symbol: sym }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym }) });
      await page.goto(s.base + '#/technical/NASDAQ%3ANVDA'); await page.locator('main[data-route=technical]').waitFor();
      await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor({ timeout: 20000 }); await page.locator('[data-private-expand=technical]').waitFor();
      const holds = await count(page, '[data-indicator] [data-verdict]');
      assert.equal(await state(page, 'tech-kis-chart'), 'LOGIN_REQUIRED', phase + ': public by default, the panel waits for a sign-in');
      assert.equal(await body(page, 'tech-kis-chart'), '', phase + ': empty body before a sign-in');
      assert.equal(await page.locator('[data-private-expand=technical]').getAttribute('aria-expanded'), 'false');
      assert.equal(await page.locator('[data-private-disconnect=technical]').isVisible(), false, phase + ': 연결 끊기 hidden before a sign-in');
      // A synthetic click is refused by the action gate: no Google script, no Worker request.
      await page.evaluate(() => document.querySelector('[data-private-expand=technical]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })));
      await page.waitForTimeout(200);
      assert.deepEqual([w.log.length, w.all.filter((u) => u.includes('accounts.google.com')).length], [0, 0], phase + ': a synthetic click sends nothing');
      await signIn(page, 'technical', 'tech-kis-chart');
      assert.deepEqual(await page.evaluate(() => window.__gisCfg.filter((c) => c.scope === 'openid email')), [{ scope: 'openid email', igs: false }], phase + ': one token request for openid email only');
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');
      // One click: the analysis, the chart and the five measures for this company, through the server's owner check.
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-layer=technical]').waitFor({ timeout: 20000 });
      assert.deepEqual(w.log.map((l) => l.path).sort(), ['/kis/analysis?symbol=NVDA', '/kis/chart?symbol=NVDA', '/kis/technical?symbol=NVDA'], phase + ': exactly the three reads for the click');
      assert.equal(w.refused || 0, 0, phase + ': no read of the click is refused by the one-at-a-time limiter');
      assert.ok(w.log.slice(1).every((l, i) => l.at - w.log[i].at >= 5000), phase + ': the reads of one click run one after another, 5 s apart');
      assert.equal(await page.locator('[data-private-expand=technical]').textContent(), '비공개 접기');
      const meta = await page.locator('[data-private-meta=technical] dd').allTextContents();
      assert.deepEqual(meta.slice(0, 7), ['KIS 보관 일봉 (MODP=0)', '원주가', '2026-10-30', '2026-10-31T04:00:00Z', '정정 증거 없음', '평가일 기준 정상 · 현재 시세 최신 아님 (평가일 2026-10-30)',
        '공개 기준일 없음 · 비공개 기준일 2026-10-30 · 직접 비교 제한'], phase + ': source, basis, basis day, capture time, correction, status, comparison');
      assert.equal(await page.locator('[data-private-basis-compare]').getAttribute('data-private-basis-compare'), 'DIFFERENT');
      assert.equal(await text(page, '[data-private-layer-note]'), '공개와 같은 계산식·규칙·판 · 공급처·기준일·확보 범위는 다를 수 있음 · 공개 결과는 바뀌지 않음', phase + ': the two-layer line');
      assert.equal(await count(page, 'svg[data-private-chart=NVDA] [data-private-close-line]'), 1, phase + ': the close line');
      assert.equal(await text(page, '[data-private-counts]'), '진단값(원시 계산) 2개 · 채택값 0개 · 미산출 3개', phase + ': raw diagnostics as a count');
      assert.equal(await page.locator('[data-private-adopted]').getAttribute('data-private-adopted'), '0');
      assert.match(await text(page, '[data-private-adopted]'), /채택된 기술 지표 없음/);
      assert.deepEqual(await page.locator('[data-private-held]').evaluateAll((n) => n.map((x) => [x.dataset.privateHeld, /^[A-Z0-9_]+ · 미산출 · /.test(x.textContent)])),
        [['MACD_12_26', true], ['RSI_14', true], ['SMA_20', true]], phase + ': each held indicator says 미산출 with its reason');
      assert.deepEqual(site.leaks([await page.content()], [...RAW, ...X.MEASURE_RAW]), [], phase + ': no raw diagnostic value anywhere on the page');
      assert.deepEqual(await page.locator('[data-private-panel=tech-kis-chart] [data-ram-price]').allTextContents(), ['2026-10-30 · 105.5', ADOPTED + ' %'], phase + ': the last close and the adopted measure as RAM text');
      // The five measures: 채택값 only when adopted, 진단값 a count, 미산출 with reasons, windows, signal day, no rank.
      assert.equal(await count(page, '[data-private-measures=READY]'), 1, phase + ': the measures part');
      assert.deepEqual(await page.locator('[data-private-measure]').evaluateAll((n) => n.map((x) => [x.dataset.privateMeasure, x.dataset.privateMeasureKind])),
        [['momentum_3m', 'VALUE'], ['momentum_6m', 'DIAGNOSTIC'], ['momentum_12m', 'NOT_COMPUTED'], ['volatility_6m', 'NOT_COMPUTED'], ['dollar_volume_6m', 'NOT_COMPUTED']], phase + ': five measures in order');
      assert.equal(await text(page, '[data-private-measures-counts]'), '진단값(원시 계산) 2개 · 채택값 1개 · 미산출 4개');
      assert.match(await text(page, '[data-private-measure=momentum_6m]'), /^모멘텀 6개월 · 미산출 · 증권 신원 기간 미확인 · 진단값만 있음 \(값 미표시\)/, phase + ': a diagnostic is 미산출, not a value');
      assert.match(await text(page, '[data-private-measure=dollar_volume_6m]'), /거래량 창이 모자라거나 맞지 않음 · 거래 범위 미확인 · 관측 창 2026-05-01 ~ 2026-10-30 · 100 \/ 126 거래일/);
      assert.match(await text(page, '[data-private-measure=momentum_3m]'), /^모멘텀 3개월 · 채택값 12\.4242 % · 관측 창 2026-07-30 ~ 2026-10-30 · 64 \/ 64 종가$/);
      assert.deepEqual((await page.locator('[data-private-meta=measures] dd').allTextContents()).slice(0, 3), ['2026-10-30', '2026-10-30', '2026-10-31T04:00:00Z'], phase + ': signal day, data_asof, capture time');
      assert.match(await text(page, '[data-private-measures-rank]'), /^그룹 순위 미산출 · 한 기업 측정만 있음/, phase + ': no rank');
      assert.ok(!/ · 0 %|채택값 0/.test(await text(page, '[data-private-measures]')), phase + ': a null measure is never 0');
      await site.assertRamOnly(page, CLOSES.filter((c) => c !== '101.5' && c !== '103.5'), phase);
      assert.equal(await count(page, '[data-indicator] [data-verdict]'), holds, phase + ': the public verdicts are unchanged');
      assert.deepEqual([...new Set(await page.locator('[data-indicator] [data-verdict]').evaluateAll((n) => n.map((x) => x.dataset.na)))], ['NO_APPROVED_PRICE_SERIES'], phase + ': public verdicts still on hold');
      // 접기 clears what was shown, sends nothing; 펼치기 again asks the server again.
      await page.locator('[data-private-expand=technical]').click();
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': folding clears the private result');
      assert.equal(w.log.length, 3, phase + ': folding sends nothing');
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-layer=technical]').waitFor();
      assert.equal(w.log.length, 6, phase + ': each expansion is checked by the server again');
      // A missing measures file (404 on that route alone): only the measures part is 자료 없음; the analysis and the chart stay.
      await page.locator('[data-private-expand=technical]').click();
      w.answers.technical = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-measures=EMPTY]').waitFor({ timeout: 20000 });
      assert.equal(await state(page, 'tech-kis-chart'), 'READY', phase + ': a missing measures file does not hide the panel');
      assert.deepEqual([await count(page, 'svg[data-private-chart=NVDA]'), await count(page, '[data-private-counts]'), await count(page, '[data-private-measure]')], [1, 1, 0], phase + ': chart and analysis stay, no measure');
      assert.match(await text(page, '[data-private-measures=EMPTY]'), /자료 없음 · 이 기업의 비공개 측정 파일이 아직 없습니다/);
      // A measures file with a rank is refused whole: that part alone, nothing of it shown.
      await page.locator('[data-private-expand=technical]').click();
      w.answers.technical = (sym) => { const m = X.measures({ symbol: sym }); m.rank_count = 1; return { status: 200, body: m }; };
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-measures=REFUSED]').waitFor({ timeout: 20000 });
      assert.equal(await page.locator('[data-private-measures=REFUSED] [data-na]').getAttribute('data-na'), 'RANK_NOT_ALLOWED');
      assert.deepEqual([await state(page, 'tech-kis-chart'), await count(page, '[data-private-measure]'), await count(page, 'svg[data-private-chart=NVDA]')], ['READY', 0, 1], phase + ': refused measures, the rest stays');
      assert.deepEqual(site.leaks([await page.content()], [ADOPTED]), [], phase + ': nothing of a refused measures file');
      await page.locator('[data-private-expand=technical]').click();
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym }) });
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-measures=READY]').waitFor();
      await boundaries(page, seen, w, phase);
      // A server refusal (the owner check fails): the token is dropped and the panel asks to sign in again.
      await page.locator('[data-private-expand=technical]').click();
      w.answers.analysis = w.answers.chart = w.answers.technical = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await page.locator('[data-private-expand=technical]').click(); await waitState(page, 'tech-kis-chart', 'LOGIN_REQUIRED');
      assert.equal(await note(page, 'technical'), '서버가 오너 확인을 거부했습니다 · 다시 로그인하세요', phase + ': 403 words');
      assert.equal(await count(page, '[data-private-layer]'), 0); assert.equal(await page.locator('[data-private-disconnect=technical]').isVisible(), false, phase + ': the token is dropped');
      const n403 = w.log.length;
      // Sign in again (Google already loaded: one click) → a missing file is 자료 없음 and keeps the session.
      w.answers.analysis = w.answers.chart = w.answers.technical = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await page.locator('[data-private-expand=technical]').click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
      await page.locator('[data-private-expand=technical]').click(); await waitState(page, 'tech-kis-chart', 'EMPTY');
      assert.equal(await note(page, 'technical'), '이 기업의 비공개 자료가 아직 없습니다');
      assert.ok(w.log.length > n403);
      // A payload that breaks the contract (a raw value presented as adopted with a reason) is refused whole.
      w.answers.analysis = () => { const a = X.analysis(); a.metrics.SMA_20.value = '1'; return { status: 200, body: a }; };
      w.answers.chart = (sym) => ({ status: 200, body: X.bars({ symbol: sym }) });
      w.answers.technical = (sym) => ({ status: 200, body: X.measures({ symbol: sym }) });
      await page.locator('[data-private-expand=technical]').click(); await waitState(page, 'tech-kis-chart', 'ERROR');
      assert.equal(await note(page, 'technical'), '비공개 자료가 형식과 달라 보이지 않습니다');
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': nothing of a refused payload is shown');
      // 연결 끊기 clears and drops the token.
      w.answers.analysis = () => ({ status: 200, body: X.analysis() });
      await page.locator('[data-private-expand=technical]').click(); await page.locator('[data-private-layer=technical]').waitFor();
      await page.locator('[data-private-disconnect=technical]').click(); await waitState(page, 'tech-kis-chart', 'LOGIN_REQUIRED');
      assert.equal(await note(page, 'technical'), '비공개 연결을 끊었습니다'); assert.equal(await count(page, '[data-private-layer]'), 0);
      // Expiry: sign in, then the clock passes the token's life → the next click reads nothing and asks to sign in.
      await page.locator('[data-private-expand=technical]').click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=technical]').textContent));
      const before = w.log.length;
      await ctx.clock.setFixedTime(new Date(Date.parse(NOW) + 3600 * 1000));
      await page.locator('[data-private-expand=technical]').click();
      await page.waitForFunction(() => /Google 로그인 준비됨|^로그인됨|만료/.test(document.querySelector('[data-private-note=technical]').textContent) && document.querySelector('[data-private-panel=tech-kis-chart]').dataset.privateState !== 'LOADING');
      assert.equal(w.log.length, before, phase + ': an expired token is dropped before a read (no request)');
      assert.equal(await count(page, '[data-private-layer]'), 0);
      await boundaries(page, seen, w, phase + ' after refusals');
      // A reload keeps nothing: the panel waits for a sign-in again.
      await page.reload(); await page.locator('[data-private-expand=technical]').waitFor({ timeout: 20000 });
      assert.equal(await state(page, 'tech-kis-chart'), 'LOGIN_REQUIRED', phase + ': nothing survives a reload');
      await ctx.close(); pass++;
    }
    // ================================================================ QGV 2.1.6, 1440 and 390
    for (const width of [1440, 390]) {
      phase = 'qgv ' + width;
      const { ctx, page, seen, w } = await context(width);
      await page.goto(s.base + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
      await page.locator('[data-private-expand=qgv]').waitFor();
      const ranks = () => page.locator('[data-lb-table] tbody tr[data-row]').evaluateAll((n) => n.map((tr) => [tr.dataset.row, (tr.querySelector('td[data-cell=rank]') || {}).textContent || null]));
      // data-row is the company id; the private file is keyed by the universe code (IS2.companies maps one to the other).
      const r0 = await ranks(), id = r0[0][0];
      const [code, other] = await page.evaluate((ids) => ids.map((x) => { const c = window.IS2.companies.get(x); return c && c.code ? c.code : x; }), [id, r0[1][0]]);
      assert.equal(await state(page, 'qgv-kis'), 'LOGIN_REQUIRED', phase + ': public by default');
      assert.equal(w.log.length, 0);
      const basis = PUB.times.price_basis_date;
      w.answers.qgv = () => ({ status: 200, body: X.qgv({ codes: [code, other], priceBasis: basis }) });
      await signIn(page, 'qgv', 'qgv-kis');
      // No company chosen: the coverage and the official line, no row.
      await page.locator('[data-private-expand=qgv]').click(); await page.locator('[data-private-layer=qgv]').waitFor({ timeout: 20000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/qgv'], phase + ': one read for the click');
      assert.deepEqual(await page.locator('[data-private-coverage] li').allTextContents(), ['Q 산출 2 / 2', 'G 산출 2 / 2', 'V 산출 0 / 2', 'Q·G·V 모두 0 / 2']);
      assert.equal(await page.locator('[data-private-row]').getAttribute('data-private-row'), 'NONE');
      assert.match(await text(page, '[data-private-layer=qgv]'), /공개 공식 순위·TARGET은 이 결과로 바뀌지 않음/);
      assert.match(await text(page, '[data-private-rank]'), /^비공개 순위 없음 · /);
      assert.match(await text(page, '[data-private-layer-note]'), /^공개와 같은 계산식·규칙·판 · 공급처·기준일·확보 범위는 다를 수 있음/);
      assert.equal(await page.locator('[data-private-basis-compare]').getAttribute('data-private-basis-compare'), 'SAME', phase + ': same basis day');
      // Choose the company → fold and expand: its axes, V 미산출 with the reason, no total, no rank.
      await page.locator('[data-private-expand=qgv]').click();
      await page.evaluate((c) => window.IS2.selection.set(c), id);
      w.answers.qgv = () => ({ status: 200, body: X.qgv({ codes: [code, other], priceBasis: '2026-10-30' }) });
      await page.locator('[data-private-expand=qgv]').click(); await page.locator('[data-private-row="' + code + '"]').waitFor({ timeout: 20000 });
      const axes = await page.locator('[data-private-row="' + code + '"] [data-private-axis]').allTextContents();
      assert.deepEqual(axes, ['Q 70.3', 'G 60.5', 'V 미산출 · 사유 코드 V_INPUTS_NOT_AVAILABLE'], phase + ': Q / G computed, V 미산출 with its reason');
      assert.ok(!axes.some((t) => /^V 0(\.0)?$/.test(t)), phase + ': 미산출 is never 0');
      assert.equal(await text(page, '[data-private-total]'), 'QGV 총점 미산출 · V 미산출', phase + ': no total without V');
      assert.match(await text(page, '[data-private-basis-compare]'), /기준일이 달라 직접 비교 제한/, phase + ': different basis days say so');
      assert.deepEqual(await ranks(), r0, phase + ': the public ranks are unchanged by the private layer');
      await site.assertRamOnly(page, ['70.3', '60.5'], phase);
      // 403 → sign in again; 연결 끊기 clears.
      await page.locator('[data-private-expand=qgv]').click();
      w.answers.qgv = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await page.locator('[data-private-expand=qgv]').click(); await waitState(page, 'qgv-kis', 'LOGIN_REQUIRED');
      assert.equal(await note(page, 'qgv'), '서버가 오너 확인을 거부했습니다 · 다시 로그인하세요');
      assert.equal(await count(page, '[data-private-layer]'), 0);
      assert.deepEqual(await ranks(), r0, phase + ': public ranks unchanged after a refusal');
      // A private file with a rank is refused whole.
      w.answers.qgv = () => { const q = X.qgv({ codes: [code, other] }); q.rank = 1; return { status: 200, body: q }; };
      await page.locator('[data-private-expand=qgv]').click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=qgv]').textContent));
      await page.locator('[data-private-expand=qgv]').click(); await waitState(page, 'qgv-kis', 'ERROR');
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': a ranked private file is not shown');
      await page.locator('[data-private-disconnect=qgv]').click(); await waitState(page, 'qgv-kis', 'LOGIN_REQUIRED');
      await boundaries(page, seen, w, phase);
      await ctx.close(); pass++;
    }
    // ================================================================ macro 4.1.3 and news 5.2.7, 1440 and 390
    // The public block keeps its own source (macro NONE; news the layer's file); the private panel under it reads the private copy.
    const SHARED = [
      { kind: 'macro', id: 'macro-observed-private', hash: '#/macro', pub: '[data-block="4.1.3-observed"]', ready: '[data-block="4.1.3-observed"] [data-obs-state=NONE]',
        good: () => MX.cases().main, bad: () => MX.mutate('main', (p) => { p.schema_version = 'macro-current-query/2'; }), empty: '비공개 보관 관측 자료가 아직 없습니다',
        shown: async (page, label) => {
          const P = '[data-private-panel=macro-observed-private] ';
          assert.equal(await count(page, P + '[data-obs-row]'), 14, label + ': the 14 series drawn by the public block function');
          assert.equal(await count(page, P + '[data-obs-values=NOT_SHOWN]'), 1, label + ': the same no-value rule');
          assert.ok(!MX.SENTINEL.test(await page.content()), label + ': no observed value on the page');
        } },
      { kind: 'news', id: 'news-refresh-private', hash: '#/news', pub: '[data-news-status] > [data-news-source-refresh]', ready: '[data-news-status] > [data-news-source-refresh=RECORDED]',
        good: () => NFX.both_no_new_items.payload, bad: () => { const p = structuredClone(NFX.both_no_new_items.payload); p.refresh.result = 'UPDATED'; return p; }, empty: '비공개 보관 재생 결과가 아직 없습니다',
        shown: async (page, label) => {
          const P = '[data-private-panel=news-refresh-private] ';
          assert.equal(await page.locator(P + '[data-news-source-refresh]').getAttribute('data-news-source-refresh'), 'RECORDED', label + ': the table drawn by the public function');
          assert.equal(await page.locator(P + '[data-news-source-refresh-overall]').getAttribute('data-news-source-refresh-overall'), 'NO_NEW_ITEMS', label + ': the private run');
          assert.match(await page.locator(P + '[data-news-source-refresh-overall]').innerText(), /^보관 재생 시각 .* \(재생 시각 · 원천 성공·기사 발행 시각 아님\)/, label + ': the replay time is named as such (Codex #483)');
          assert.match(await page.locator('[data-news-status] > [data-news-source-refresh] [data-news-source-refresh-overall]').innerText(), /^이번 실행 /, label + ': the public line keeps its words');
          assert.equal(await page.locator('[data-news-status] > [data-news-source-refresh] [data-news-source-refresh-overall]').getAttribute('data-news-source-refresh-overall'), 'PARTIAL_FAILED', label + ': the public run unchanged');
          assert.deepEqual(await page.locator(P + 'th[data-news-source-row]').evaluateAll((n) => n.map((x) => x.dataset.newsSourceRow)), ['GDELT', 'IR'], label + ': both sources');
        } },
    ];
    for (const S of SHARED) for (const width of [1440, 390]) {
      phase = S.kind + ' ' + width;
      const { ctx, page, seen, w } = await context(width);
      await page.goto(s.base + S.hash); await page.locator(S.ready).first().waitFor({ timeout: 20000 });
      await page.locator('[data-private-expand=' + S.kind + ']').waitFor();
      const pub = () => text(page, S.pub), pub0 = await pub();
      assert.equal(await state(page, S.id), 'LOGIN_REQUIRED', phase + ': public by default, the panel waits for a sign-in');
      assert.equal(await body(page, S.id), '', phase + ': empty body');
      w.answers[S.kind] = () => ({ status: 200, body: S.good() });
      await signIn(page, S.kind, S.id);
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await page.locator('[data-private-layer=' + S.kind + ']').waitFor({ timeout: 20000 });
      assert.deepEqual(w.log.map((l) => l.path), ['/kis/' + S.kind], phase + ': one read for the click, no query');
      assert.match(await text(page, '[data-private-layer=' + S.kind + ']'), /^비공개 보관본 · 인증 경로/, phase + ': the source words');
      assert.equal(await text(page, '[data-private-panel=' + S.id + '] [data-private-layer-note]'), '공개와 같은 계산식·규칙·판 · 공급처·기준일·확보 범위는 다를 수 있음 · 공개 결과는 바뀌지 않음', phase + ': the two-layer line');
      await S.shown(page, phase);
      assert.equal(await pub(), pub0, phase + ': the public block is unchanged');
      await boundaries(page, seen, w, phase);
      // 접기 clears; 403 drops the token; a refused file is refused whole; 404 is 자료 없음; 연결 끊기 clears.
      await page.locator('[data-private-expand=' + S.kind + ']').click();
      assert.deepEqual([await count(page, '[data-private-layer]'), w.log.length], [0, 1], phase + ': folding clears and sends nothing');
      w.answers[S.kind] = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await waitState(page, S.id, 'LOGIN_REQUIRED');
      assert.equal(await note(page, S.kind), '서버가 오너 확인을 거부했습니다 · 다시 로그인하세요');
      assert.equal(await page.locator('[data-private-disconnect=' + S.kind + ']').isVisible(), false, phase + ': the token is dropped');
      w.answers[S.kind] = () => ({ status: 200, body: S.bad() });
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await page.waitForFunction((k) => /^로그인됨/.test(document.querySelector('[data-private-note="' + k + '"]').textContent), S.kind);
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await waitState(page, S.id, 'ERROR');
      assert.equal(await note(page, S.kind), '비공개 자료가 형식과 달라 보이지 않습니다');
      assert.equal(await count(page, '[data-private-layer]'), 0, phase + ': nothing of a refused file');
      w.answers[S.kind] = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await waitState(page, S.id, 'EMPTY');
      assert.equal(await note(page, S.kind), S.empty);
      w.answers[S.kind] = () => ({ status: 200, body: S.good() });
      await page.locator('[data-private-expand=' + S.kind + ']').click(); await page.locator('[data-private-layer=' + S.kind + ']').waitFor({ timeout: 20000 });
      await page.locator('[data-private-disconnect=' + S.kind + ']').click(); await waitState(page, S.id, 'LOGIN_REQUIRED');
      assert.equal(await note(page, S.kind), '비공개 연결을 끊었습니다'); assert.equal(await count(page, '[data-private-layer]'), 0);
      assert.deepEqual(w.log.map((l) => l.path), Array(5).fill('/kis/' + S.kind), phase + ': only this route, once per click');
      assert.equal(await pub(), pub0, phase + ': the public block is unchanged after every private state');
      await boundaries(page, seen, w, phase + ' after refusals');
      await ctx.close(); pass++;
    }
    console.log('web_app_kis_private_browser_test: PASS (' + pass + ' groups: technical 1440 (sign-in, three reads, five measures, measures 404 / refused alone, fold, 403, 404, refused payload, disconnect, expiry, reload), qgv 1440, qgv 390, macro 1440, macro 390, news 1440, news 390)');
  } catch (e) {
    console.error('web_app_kis_private_browser_test: FAIL at ' + phase); console.error(e); process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
