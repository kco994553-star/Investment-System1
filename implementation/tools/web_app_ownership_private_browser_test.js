'use strict';
// 관계 자료 인증 전달 (owner 2026-11-13, Codex #531 company-ownership-view/1 + Main company-ownership-delivery/1). The company page's
// relation slot (under 4. 이 기업 소식) and 5.1 against a stand-in of the private Worker's /kis/classification ownership parts, the
// owner signed in through the same Google stub as the classification panel test:
//  - signed out: nothing is added (no button, no read); signed in: one button reads Main's index (one read), a company the index
//    lists gets a second button that reads its view and its optional refresh receipt (two reads, 5 s apart, Bearer only);
//  - the index not staged (404), a refused sign-in (401), damaged view bytes, an unlisted company, a receipt not bound to the view:
//    each its own words, none of them 「관계 없음」; the view is drawn only with the bytes the index names;
//  - a delivered view with a FAILED refresh receipt shows the retained view and the failed attempt beside it, its own times unchanged;
//    5.1 draws the same RAM view with no new read; signing out drops it;
//  - 1440 · 390 · 320: the relation slot within the page width, 44 px buttons on phones; nothing stored, no CSP violation.
// The views are Codex's consumer cases with the centre's company ids re-pointed at Universe504 pages (test-made), served as staged bytes.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');

const NOW = '2026-11-13T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json', 'sec-qgv2.json', 'macro-evidence.json', 'dart-financials.json', 'sec-disclosures.json', 'news-signals.json', 'dart-disclosures.json'];
const TOKEN = ['memory', 'only', 'synthetic', 'ownership', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.__gisCfg=[];window.google={accounts:{oauth2:{initTokenClient:function(cfg){window.__gisCfg.push({scope:cfg.scope,igs:cfg.include_granted_scopes});'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const CX = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/docs/research/company_ownership/consumer-synthetic.json'), 'utf8')).cases.map((c) => [c.case_id, c]));
const canon = (x) => Array.isArray(x) ? '[' + x.map(canon).join(',') + ']' : x !== null && typeof x === 'object' ? '{' + Object.keys(x).sort().map((k) => JSON.stringify(k) + ':' + canon(x[k])).join(',') + '}' : JSON.stringify(x);
const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');
// SYN-A → NYSE:MMM (and SYN-B → NASDAQ:ADBE as the counterparty, a Universe504 page), as staged bytes.
function viewFor(c) { const v = JSON.parse(JSON.stringify(c.expected_view));
  for (const e of v.entities) e.company_ids = e.entity_id === 'SYN-A' ? ['NYSE:MMM'] : e.entity_id === 'SYN-B' ? ['NASDAQ:ADBE'] : e.company_ids;
  return canon(v) + '\n'; }
const VIEW = viewFor(CX.refresh_failed), VIEW_OBJ = JSON.parse(VIEW);
const receiptFor = (view, edit) => { const r = { ...CX.refresh_failed.refresh, retained_view_sha256: sha(view) }; if (edit) edit(r); return JSON.stringify(r, null, 2) + '\n'; };
const RECEIPT = receiptFor(VIEW), LATE = receiptFor(VIEW, (r) => { r.attempt = { ...r.attempt, attempted_at: '2000-01-01T00:00:00Z' }; });
const indexFor = (receipt) => JSON.stringify({ schema_version: 'company-ownership-delivery/1', data_kind: 'SYNTHETIC', new_external_requests: 0,
  sources: [{ handoff_path: 'handoffs/test-made', handoff_manifest_sha256: 'a'.repeat(64) }],
  views: [{ entity_id: 'SYN-A', company_ids: ['NYSE:MMM'], dataset_hash: VIEW_OBJ.dataset_hash, view: { size: Buffer.byteLength(VIEW), sha256: sha(VIEW) },
    receipt: receipt ? { size: Buffer.byteLength(receipt), sha256: sha(receipt) } : null }] }, null, 2) + '\n';
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
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
        const at = Date.now(), early = w.lastAt !== undefined && at - w.lastAt < 5000;
        if (early) { await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify({ error: { code: 'RATE_LIMITED' } }) }); return; }
        w.lastAt = at; w.log.push({ at, path: url.pathname + url.search, auth: hd.authorization || null, cookie: hd.cookie || null, referer: hd.referer || null });
        const part = url.searchParams.get('part'), key = part + (url.searchParams.get('entity') ? '/' + url.searchParams.get('entity') : '');
        const nf = { status: 404, body: { error: { code: 'KIS_SERIES_NOT_FOUND' } } };
        const a = (w.answers[key] || (() => nf))();
        await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: a.text !== undefined ? a.text : JSON.stringify(a.body) }); return;
      }
      w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
    });
    return { ctx, page, seen, w };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.innerText);
  const count = (page, sel) => page.locator(sel).count();
  const go = async (page, hash, sel) => { await page.evaluate((h) => { location.hash = h; }, hash); if (sel) await page.locator(sel).first().waitFor({ timeout: 20000 }); };
  const DONE = '[data-cc]:not([data-cc=LOADING]):not([data-cc=NOT_LOADED])';
  const company = async (page, code) => { await go(page, '#/search'); await go(page, '#/company/' + encodeURIComponent(code), DONE); await page.locator('[data-own-slot="' + code + '"]').waitFor({ state: 'attached', timeout: 20000 }); };
  async function signIn(page) {
    const btn = page.locator('[data-private-expand=classification]');
    await btn.click(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
    await btn.click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=classification]').textContent));
  }
  const stateText = async (page, st) => { await page.locator('[data-own-private-state=' + st + ']').waitFor({ timeout: 45000 }); return text(page, '[data-own-private-state]'); };
  async function boundaries(page, seen, w, label) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(w.unexpected, [], label + ': no other outside request');
    assert.deepEqual(seen.errors.filter((e) => !/status of (401|403|404|429)/.test(e)), [], label + ': no console or page error but the stand-in refusals');
    for (const l of w.log) assert.deepEqual([l.auth, l.cookie, l.referer], ['Bearer ' + TOKEN, null, null], label + ': Bearer header only, no cookie, no referrer');
    const st = await site.storage(page);
    assert.equal(st.session, 0, label + ': nothing in session storage');
    assert.deepEqual(site.leaks([...Object.values(st.localItems), ...Object.keys(st.localItems), page.url(), ...seen.errors], [TOKEN, VIEW_OBJ.dataset_hash]), [], label + ': no token or dataset in storage, the address or the console');
  }
  const NOT_NONE = / · 관계가 없다는 뜻이 아님$/;

  try {
    {
      phase = '1440 signed out';
      const { ctx, page, seen, w } = await context(1440);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-own-slot="NYSE:MMM"]').waitFor({ state: 'attached' });
      assert.equal(await count(page, '[data-own-private-open]'), 0, phase + ': nothing for a signed-out visitor');
      assert.equal(w.log.length, 0);
      ok('1440 signed out: the relation slot adds nothing, no read');

      phase = '1440 index states';
      await signIn(page);
      await page.locator('[data-own-private-open]').waitFor({ timeout: 20000 });
      assert.match(await text(page, '[data-own-private-state=IDLE]'), /^비공개 보관본 · 인증 경로 · 연구 자료\(현재 지분·완결 목록 아님\)$/);
      assert.equal(w.log.length, 0, phase + ': signing in reads nothing');
      await page.locator('[data-own-private-open]').click();
      assert.match(await stateText(page, 'ERROR'), /^관계 자료 목록표 없음 · 전달 위치에 아직 배치되지 않음 · 관계가 없다는 뜻이 아님$/, phase + ': not staged ≠ no relationships');
      w.answers.ownership_index = () => ({ status: 401, body: { error: { code: 'AUTH_REQUIRED' } } });
      await page.waitForTimeout(5200); await page.locator('[data-own-private-open]').click();
      await page.waitForFunction(() => /로그인이 필요하거나 권한이 없습니다/.test((document.querySelector('[data-own-private-state]') || {}).textContent || ''), null, { timeout: 45000 });
      assert.match(await text(page, '[data-own-private-state]'), NOT_NONE, phase + ': a refused sign-in ≠ no relationships');
      w.answers.ownership_index = () => ({ status: 200, text: indexFor(RECEIPT) });
      await page.waitForTimeout(5200); await page.locator('[data-own-private-open]').click();
      assert.match(await stateText(page, 'LISTED'), /^목록표에 있음 · 실체 SYN-A · 갱신 기록 있음$/);
      assert.deepEqual(w.log.map((l) => l.path), Array(3).fill('/kis/classification?part=ownership_index'), phase + ': one read a click');
      ok('1440 index: not staged, refused sign-in and listed each in their own words; one read a click, Bearer only');

      phase = '1440 view states';
      w.answers['ownership_view/SYN-A'] = () => ({ status: 200, text: VIEW.replace('"SYN-A"', '"SYN-A" ') });
      w.answers['ownership_receipt/SYN-A'] = () => ({ status: 200, text: RECEIPT });
      await page.waitForTimeout(5200); await page.locator('[data-own-private-show=SYN-A]').click();
      assert.match(await stateText(page, 'ERROR'), /^파일이 목록표와 다릅니다\(손상 또는 다른 파일\) · 쓰지 않음 · \$view · 관계가 없다는 뜻이 아님$/, phase + ': damaged bytes refused');
      assert.equal(await count(page, '[data-own-block]'), 0, phase + ': nothing drawn from a damaged file');
      w.answers['ownership_view/SYN-A'] = () => ({ status: 200, text: VIEW });
      await page.waitForTimeout(5200);
      const v0 = w.log.length; await page.locator('[data-own-private-show=SYN-A]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-own-block=SYN-A]').waitFor({ timeout: 45000 });
      assert.deepEqual(w.log.slice(v0).map((l) => l.path), ['/kis/classification?part=ownership_view&entity=SYN-A', '/kis/classification?part=ownership_receipt&entity=SYN-A'], phase + ': view then receipt');
      assert.ok(w.log[v0 + 1].at - w.log[v0].at >= 5000, phase + ': 5 s apart');
      assert.match(await text(page, '[data-own-refresh]'), new RegExp('^마지막 갱신 시도 실패 · 시도 ' + CX.refresh_failed.refresh.attempt.attempted_at.replace(/[.+]/g, '\\$&') + ' · 이전에 성공한 자료를 보임\\(성공 '), phase + ': the failed refresh beside the retained view');
      assert.match(await text(page, '[data-own-delivery]'), /^비공개 보관본 · 인증 경로 · 합성 자료 · 시험용$/);
      assert.equal(await count(page, '[data-own-private]:not(:empty)'), 0, phase + ': the loader gives way to the block');
      ok('1440 view: damaged bytes refused; then view + receipt (5 s apart) drawn with the failed refresh beside it');

      phase = '1440 5.1 and sign-out';
      const n = w.log.length;
      await go(page, '#/news/' + encodeURIComponent('NYSE:MMM'), '[data-center-code="NYSE:MMM"]'); await page.locator('[data-news-center] [data-own-block=SYN-A]').waitFor({ timeout: 20000 });
      assert.equal(w.log.length, n, phase + ': 5.1 draws the same RAM view, no read');
      await company(page, 'NASDAQ:ADBE');
      assert.match(await stateText(page, 'ABSENT'), /^이 기업은 전달된 관계 자료 목록에 없음 · 목록 1개 기업 · 관계가 없다는 뜻이 아님$/, phase + ': a company the index does not list');
      assert.equal(w.log.length, n, phase + ': the index in RAM, no read');
      await page.locator('[data-private-disconnect=classification]').click();
      await go(page, '#/company/NYSE%3AMMM', DONE);
      assert.equal(await page.evaluate(() => window.IS2.ownershipView.ram.all().length), 0, phase + ': signing out drops the delivered view');
      assert.equal(await count(page, '[data-own-block]'), 0); assert.equal(await count(page, '[data-own-private-open]'), 0, phase + ': and adds nothing signed out');
      await boundaries(page, seen, w, phase);
      ok('1440 5.1 the same RAM view; an unlisted company in its own words; sign-out drops it; boundaries');
      await ctx.close();
    }
    {
      phase = '390 receipt refused';
      const { ctx, page, seen, w } = await context(390);
      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator(DONE).waitFor(); await page.locator('[data-private-expand=classification]').waitFor();
      await signIn(page);
      w.answers.ownership_index = () => ({ status: 200, text: indexFor(LATE) });
      w.answers['ownership_view/SYN-A'] = () => ({ status: 200, text: VIEW });
      w.answers['ownership_receipt/SYN-A'] = () => ({ status: 200, text: LATE });
      await page.locator('[data-own-private-open]').waitFor({ timeout: 20000 });
      const b = await page.locator('[data-own-private-open]').boundingBox(); assert.ok(b.height >= 44, phase + ': 44 px button');
      await page.locator('[data-own-private-open]').click(); await page.locator('[data-own-private-show=SYN-A]').waitFor({ timeout: 45000 });
      await page.waitForTimeout(5200); await page.locator('[data-own-private-show=SYN-A]').click();
      await page.locator('[data-own-block=SYN-A]').waitFor({ timeout: 45000 });
      assert.equal(await count(page, '[data-own-refresh]'), 0, phase + ': a receipt not bound to the view gives no refresh line');
      assert.match(await text(page, '[data-own-delivery]'), /^갱신 기록을 쓰지 않음 · RECEIPT_TIME · 보관된 관계 자료만 보임 · 비공개 보관본 · 인증 경로 · 합성 자료 · 시험용$/);
      for (const width of [390, 320]) {
        await page.setViewportSize({ width, height: 844 });
        assert.ok(await page.evaluate(() => { const a = document.querySelector('[data-own-block=SYN-A]'), r = a.getBoundingClientRect();
          return r.right <= window.innerWidth + 1 && [...a.querySelectorAll('p, summary, li, a, span')].every((e) => e.getBoundingClientRect().right <= window.innerWidth + 1); }), phase + ': ' + width + ' px, the relation block within the page');
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await boundaries(page, seen, w, phase);
      ok('390 · 320 a receipt not bound to the view is refused (view kept, no refresh line, the reason named); the block fits; 44 px');
      await ctx.close();
    }
    if (!process.exitCode) console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e)); process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
