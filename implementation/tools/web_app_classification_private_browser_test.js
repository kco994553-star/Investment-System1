'use strict';
// 공통 분류 · 비공개 전달 (owner 2026-11-08 「통합 결과 수령」 2항: the held common classification bundle through the existing
// owner-checked private Worker, DC-44 pattern) in a real browser at 1440 and 390. Google and the private Worker are stand-ins;
// every part is Main's synthetic fixture (Codex functions on Codex cases, tools/web_app_classification_fixture.js uBundle) — no
// company record of the held bundle is here. Checks:
//  - Public by default: the company page shows 공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결 and the panel waits
//    for a sign-in; nothing goes to the Worker; a synthetic click does nothing.
//  - One click after sign-in reads the five parts, /kis/classification?part=view · technical · macro · qgv_links · dictionary,
//    one after another 5 s apart, each with the Bearer header only; the panel shows 비공개 보관본 · 인증 경로 · 게시본 아님, the
//    evaluation date, the hash, the data kind and the counts; the company block repaints from the delivered bundle (sector, the
//    accounting line kept apart: 회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님), with the delivery words.
//  - The same RAM bundle serves the QGV leaderboard's 공통 분류 filter without another read; another company page shows the
//    panel open and reads nothing; 접기 drops the bundle (the page and the QGV filter are back to NONE).
//  - 404 for the view → 자료 없음 and the source stays NONE; a view that breaks the contract → refused whole (ERROR), NONE;
//    a 403 drops the token (sign in again) and the bundle.
//  - Boundaries: no token or record id in storage, the address or another request; no style attribute, no CSP violation, no
//    horizontal overflow at 390.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_classification_fixture.js');

const NOW = '2026-11-08T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const TOKEN = ['memory', 'only', 'synthetic', 'classification', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.__gisCfg=[];window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gisCfg.push({scope:cfg.scope,igs:cfg.include_granted_scopes});'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const PARTS = ['view', 'technical', 'macro', 'qgv_links', 'dictionary'];
const PANEL = 'common-classification-private';
// The delivered bundle: the synthetic universe bundle, one fully confirmed company given an unknown accounting model (Codex #516
// 4cf2e037: independent states) so the accounting line is seen apart from the sector line.
const BUNDLE = (() => { const b = JSON.parse(JSON.stringify(X.uBundle())), r = b.view.rows.find((x) => x.company_id === 'NASDAQ:ADBE');
  r.accounting = { id: null, status: 'UNKNOWN', reasons: ['ACCOUNTING_TEMPLATE_UNCONFIRMED'], evidence_refs: [] }; return b; })();
const RECORD_IDS = BUNDLE.view.rows.map((r) => r.record_id).filter(Boolean);
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.mainSha(), X.MAIN_SHA256, 'Main fixture (Codex output) unchanged');
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  async function context(width) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
    const w = { log: [], answers: {}, unexpected: [], all: [] };
    await ctx.route('**/*', async (route) => {
      const req = route.request(), url = new URL(req.url()), hd = req.headers();
      w.all.push(req.method() + ' ' + req.url());
      if (url.origin === s.origin) { await route.continue(); return; }
      if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
      if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
      if (url.origin === WORKER && url.pathname === '/kis/classification' && req.method() === 'GET') {
        // The real Worker admits one owner request at a time, at least 5 s apart; the stand-in refuses the same way.
        const at = Date.now(), early = w.lastAt !== undefined && at - w.lastAt < 5000;
        if (early) { w.refused = (w.refused || 0) + 1; await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ error: { code: 'RATE_LIMITED' } }) }); return; }
        w.lastAt = at;
        w.log.push({ at, path: url.pathname + url.search, auth: hd.authorization || null, cookie: hd.cookie || null, referer: hd.referer || null });
        const part = url.searchParams.get('part'), a = (w.answers[part] || (() => ({ status: 200, body: BUNDLE[part] })))();
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: JSON.stringify(a.body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    return { ctx, page, seen, w };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.innerText);
  const count = (page, sel) => page.locator(sel).count();
  const state = (page) => page.locator('[data-private-panel="' + PANEL + '"]').getAttribute('data-private-state');
  const go = async (page, hash, sel) => { await page.evaluate((h) => { location.hash = h; }, hash); if (sel) await page.locator(sel).first().waitFor({ timeout: 20000 }); };
  const DONE = '[data-cc]:not([data-cc=LOADING]):not([data-cc=NOT_LOADED])';
  const company = async (page, code) => { await go(page, '#/search'); await go(page, '#/company/' + encodeURIComponent(code), DONE); await page.locator('[data-private-expand=classification]').waitFor(); };
  async function signIn(page) {
    const btn = page.locator('[data-private-expand=classification]');
    await btn.click(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
    await btn.click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=classification]').textContent));
    assert.equal(await state(page), 'READY', phase + ': signed in, still folded');
  }
  async function read(page) { await page.locator('[data-private-expand=classification]').click(); }
  async function boundaries(page, seen, w, label) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    assert.deepEqual(seen.errors.filter((e) => !/status of (403|404|429)/.test(e)), [], label + ': no console or page error but the stand-in refusals');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    for (const l of w.log) assert.deepEqual([l.auth, l.cookie, l.referer], ['Bearer ' + TOKEN, null, null], label + ': Bearer header only, no cookie, no referrer');
    const st = await site.storage(page);
    assert.equal(st.session, 0, label + ': nothing in session storage');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), ...Object.keys(st.localItems), page.url(), await page.evaluate(() => JSON.stringify(history.state)), ...seen.errors, ...w.all.filter((u) => !u.includes(WORKER))],
      [TOKEN, ...RECORD_IDS]), [], label + ': no token or record id in storage, the address, the console or another request');
  }

  try {
    for (const width of [1440, 390]) {
      const tag = width < 720 ? '390' : '1440';
      phase = tag + ' public';
      const { ctx, page, seen, w } = await context(width);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      assert.equal(await page.locator('[data-cc]').first().getAttribute('data-cc'), 'NONE');
      assert.ok((await text(page, '.cc-block')).includes('공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결'), phase + ': NONE words before the delivery');
      assert.equal(await state(page), 'LOGIN_REQUIRED', phase + ': the panel waits for a sign-in');
      await page.evaluate(() => document.querySelector('[data-private-expand=classification]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })));
      await page.waitForTimeout(200);
      assert.deepEqual([w.log.length, w.all.filter((u) => u.includes('accounts.google.com')).length], [0, 0], phase + ': a synthetic click sends nothing');
      ok(tag + ' public by default: NONE words, the panel waits, nothing sent');

      phase = tag + ' delivery';
      await signIn(page);
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');
      await read(page); await page.locator('[data-private-layer=classification]').waitFor({ timeout: 45000 });
      assert.deepEqual(w.log.map((l) => l.path), PARTS.map((p) => '/kis/classification?part=' + p), phase + ': exactly the five parts, in order');
      assert.equal(w.refused || 0, 0, phase + ': no read refused by the one-at-a-time limiter');
      assert.ok(w.log.slice(1).every((l, i) => l.at - w.log[i].at >= 5000), phase + ': one after another, 5 s apart');
      assert.match(await text(page, '[data-private-layer=classification]'), /^비공개 보관본 · 인증 경로 · 게시본 아님 · 같은 화면 같은 형식/);
      const dd = await page.locator('[data-private-meta=classification] dd').allTextContents();
      assert.deepEqual(dd.slice(0, 3), [BUNDLE.view.valuation_date, BUNDLE.view.classification_hash.slice(0, 12), '합성 데이터 · 시험용'], phase + ': date, hash, data kind');
      assert.equal(await page.locator('[data-cc-private-parts]').getAttribute('data-cc-private-parts'), PARTS.join(','));
      const n = (k) => BUNDLE.view.rows.filter((r) => r[k].status === 'CONFIRMED').length;
      assert.equal(await text(page, '[data-cc-count=rows]'), '기업 행 ' + BUNDLE.view.rows.length + '개(원래 분모 그대로)');
      assert.equal(await text(page, '[data-cc-count=sector]'), '섹터 확인 ' + n('sector') + '개');
      assert.equal(await text(page, '[data-cc-count=accounting]'), '회계모형 확인 ' + n('accounting') + '개 · 섹터와 따로 셈');
      assert.equal(await text(page, '[data-cc-count=peer]'), '섹터·회계모형 둘 다 확인 ' + (n('accounting')) + '개 · 나머지는 QGV 비교집단 완결 아님');
      // The company block repaints from the delivered bundle.
      await page.locator('.cc-block[data-cc=CONFIRMED], .cc-block[data-cc=SECTOR_ONLY]').waitFor();
      assert.equal(await count(page, '[data-cc-delivery=PRIVATE]'), 1, phase + ': delivery words in the company block');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-peer-complete'), 'YES');
      ok(tag + ' one click reads five parts 5 s apart; panel words, date, hash, counts; the company block repaints (PRIVATE)');

      phase = tag + ' same bundle';
      const before = w.log.length;
      await company(page, 'NASDAQ:ADBE');
      assert.equal(await page.locator('[data-private-expand=classification]').getAttribute('aria-expanded'), 'true', phase + ': another page shows the panel open');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-accounting'), 'UNKNOWN');
      assert.equal(await text(page, '[data-cc-line=accounting]'), '회계모형 회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님', phase + ': the accounting line apart');
      assert.equal(await page.locator('[data-cc-line=accounting]').getAttribute('data-cc-peer-complete'), 'NO');
      assert.equal(await page.locator('[data-cc-line=sector]').evaluate((e) => /확인|정보기술|IT|섹터/.test(e.innerText)), true);
      await go(page, '#/macro', 'main[data-route=macro]'); await go(page, '#/qgv', 'main[data-route=qgv]');
      await page.locator('[data-cc-filter]:not([data-cc-filter=NONE])').first().waitFor({ timeout: 20000 });
      assert.equal(w.log.length, before, phase + ': the QGV filter and another company read the same RAM bundle, no new read');
      ok(tag + ' the same RAM bundle on another company (accounting line apart) and the QGV filter, no new read');

      phase = tag + ' fold';
      await company(page, 'NYSE:MMM');
      await page.locator('[data-private-expand=classification]').click();
      await page.locator('.cc-block[data-cc=NONE]').waitFor();
      assert.equal(await count(page, '[data-cc-delivery=PRIVATE]'), 0);
      await go(page, '#/macro', 'main[data-route=macro]'); await go(page, '#/qgv', 'main[data-route=qgv]');
      await page.locator('[data-cc-filter=NONE]').first().waitFor({ timeout: 20000 });
      await boundaries(page, seen, w, phase);
      ok(tag + ' 접기 drops the bundle: company block and QGV filter back to NONE; boundaries');
      await ctx.close();
    }

    // ---------------- refusals (1440)
    {
      phase = 'refusals';
      const { ctx, page, seen, w } = await context(1440);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      await signIn(page);
      w.answers.view = () => ({ status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } });
      await read(page); await page.locator('[data-private-panel="' + PANEL + '"][data-private-state=EMPTY]').waitFor({ timeout: 20000 });
      assert.match(await text(page, '[data-private-note=classification]'), /비공개 보관 분류 묶음이 아직 없습니다/);
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE', phase + ': a missing view leaves NONE');
      assert.equal(w.log.length, 1, phase + ': the required view missing stops the click');
      ok('404 view: 자료 없음, NONE kept, the click stops');
      const broken = JSON.parse(JSON.stringify(BUNDLE.view)); broken.rows[0].sector.status = 'MAYBE';
      w.answers.view = () => ({ status: 200, body: broken });
      await page.waitForTimeout(5300);
      await read(page); await page.locator('[data-private-panel="' + PANEL + '"][data-private-state=ERROR]').waitFor({ timeout: 45000 });
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE', phase + ': a refused bundle is never used');
      ok('a view that breaks the contract is refused whole (ERROR), NONE kept');
      delete w.answers.view; await page.waitForTimeout(5300);
      await read(page); await page.locator('[data-private-layer=classification]').waitFor({ timeout: 45000 });
      await page.locator('[data-cc-delivery=PRIVATE]').waitFor();
      w.answers.view = () => ({ status: 403, body: { error: { code: 'AUTH_FORBIDDEN' } } });
      await page.locator('[data-private-expand=classification]').click();          // 접기
      await page.locator('.cc-block[data-cc=NONE]').waitFor();
      await page.waitForTimeout(5300);
      await read(page);
      await page.waitForFunction(() => /다시 로그인하세요/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
      assert.equal(await state(page), 'LOGIN_REQUIRED', phase + ': a 403 drops the token');
      assert.equal(await page.locator('.cc-block').getAttribute('data-cc'), 'NONE');
      await boundaries(page, seen, w, phase);
      ok('403 drops the token; the source stays NONE; boundaries');
      await ctx.close();
    }
  } catch (e) { console.error('FAIL at ' + phase + ': ' + (e && e.stack || e)); process.exitCode = 1; }
  finally { await browser.close(); await s.close(); }
  if (!process.exitCode) console.log(JSON.stringify({ passed: true, checks: pass }));
})();
