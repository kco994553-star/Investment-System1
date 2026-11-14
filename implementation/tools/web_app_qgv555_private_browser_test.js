'use strict';
// QGV 555 보관 결과 읽기 (owner 2026-11-14 「#537 최신 미리보기·Top500 표시 계약 인수」 §3, §6; DC-49) on #/qgv 2.1 in a real browser at
// 1440×1000 and 390×844, through the private Worker path (a stand-in for /kis/classification serving Codex's SYNTHETIC delivery as
// staged by tools/stage_private_qgv555.py with Main's stage receipt):
//  - 기존504 × U1-555 shows 「보관 결과 불러오기」; nothing is read before a click; without a sign-in the read is refused in words.
//  - After sign-in: one click = stage + manifest + index (3 reads, 5 s apart); lines say 보관 결과 · 재계산 아님 · independent anchors;
//    coverage stages; 기업 표 = one detail file (its bytes checked); role deciles D1–D10 from the producer's groups; S1 per sector.
//  - Refusals keep what was shown: a stage receipt whose evaluation anchor differs, a detail whose bytes differ from the manifest,
//    a delivery not staged (404). Boundaries: the token only to the Worker, no console error, nothing stored.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');

const NOW = '2026-11-14T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const TOKEN = ['memory', 'only', 'synthetic', 'q555', 'session'].join('-');
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){'
  + 'return{requestAccessToken:function(){cfg.callback({access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",'
  + 'scope:"openid https://www.googleapis.com/auth/userinfo.email"});}};},revoke:function(t,done){if(done)done({});}}}};';
const STAGED = execFileSync('python3', [path.join(__dirname, 'qgv555_private_fixture.py'), '--out', fs.mkdtempSync(path.join(os.tmpdir(), 'q555b-'))], { encoding: 'utf8' }).trim();
const fileOf = (part, name) => part === 'q555_stage' ? 'stage.json' : part === 'q555_manifest' ? 'manifest.json' : name + '.json';
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const tag = String(width);
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const w = { log: [], answers: {}, unexpected: [] };
      await ctx.route('**/*', async (route) => {
        const req = route.request(), url = new URL(req.url());
        if (url.origin === s.origin) { await route.continue(); return; }
        if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
        if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
        if (url.origin === WORKER && url.pathname === '/kis/classification' && req.method() === 'GET') {
          const part = url.searchParams.get('part'), scope = url.searchParams.get('scope'), name = url.searchParams.get('name');
          w.log.push({ part, scope, name, auth: req.headers().authorization || null });
          const key = part + (name ? '/' + name : '');
          const file = path.join(STAGED, fileOf(part, name));
          const a = w.answers[key] ? w.answers[key]() : scope !== 'operating504' || !fs.existsSync(file) ? { status: 404, text: JSON.stringify({ error: { code: 'KIS_SERIES_NOT_FOUND' } }) }
            : { status: 200, text: fs.readFileSync(file, 'utf8') };
          await route.fulfill({ status: a.status, contentType: 'application/json', headers: { 'access-control-allow-origin': '*', 'cache-control': 'no-store' }, body: a.text });
          return;
        }
        w.unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
      });
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      await page.goto(s.base + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      await page.locator('[data-q5-model="U1-555"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'STORED_AVAILABLE');
      assert.match(await text('[data-q5-board-text]'), /보관 결과\(계산 담당 실자료 r2\)는 아래에서 로그인 뒤 불러옴 · 이 화면에서 재계산 아님/);
      await page.locator('[data-k="q5-stored-load"]').click();
      await page.locator('[data-q5-stored-err]').waitFor();
      assert.match(await text('[data-q5-stored-err]'), /로그인 필요/);
      assert.equal(w.log.length, 0, 'nothing read without a sign-in');
      ok(tag + ' 2.1 기존504 × U1-555: stored panel offered; no read before sign-in, the refusal in words');

      phase = tag + ' sign in';
      await page.evaluate(() => { location.hash = '#/company/' + encodeURIComponent('NASDAQ:ADBE'); });
      const btn = page.locator('[data-private-expand=classification]'); await btn.waitFor({ timeout: 20000 });
      await btn.click(); await page.waitForFunction(() => /Google 로그인 준비됨/.test(document.querySelector('[data-private-note=classification]').textContent), null, { timeout: 20000 });
      await btn.click(); await page.waitForFunction(() => /^로그인됨/.test(document.querySelector('[data-private-note=classification]').textContent));
      await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('[data-q5-select]').waitFor();
      await page.locator('[data-q5-model="U1-555"]').click();
      ok(tag + ' signed in (owner session in RAM)');

      phase = tag + ' anchor refusal';
      const stage = JSON.parse(fs.readFileSync(path.join(STAGED, 'stage.json'), 'utf8'));
      w.answers.q555_stage = () => ({ status: 200, text: JSON.stringify({ ...stage, expected_evaluation: { ...stage.expected_evaluation, input_hash: 'f'.repeat(64) } }) });
      await page.locator('[data-k="q5-stored-load"]').click();
      await page.waitForFunction(() => { const e = document.querySelector('[data-q5-stored-err]'); return e && /평가 입력이 독립 기준과 다름/.test(e.textContent); }, null, { timeout: 40000 });
      assert.equal(await page.locator('[data-q5-stored="SHOWN"]').count(), 0, 'nothing shown from a delivery whose evaluation anchor differs');
      delete w.answers.q555_stage; await page.waitForTimeout(5300);
      ok(tag + ' a stage receipt whose evaluation anchor differs: refused, nothing shown');

      phase = tag + ' load';
      const before = w.log.length;
      await page.locator('[data-k="q5-stored-load"]').click();
      await page.locator('[data-q5-stored="SHOWN"]').waitFor({ timeout: 40000 });
      assert.deepEqual(w.log.slice(before).map((x) => x.part + (x.name ? '/' + x.name : '')), ['q555_stage', 'q555_manifest', 'q555_file/index']);
      assert.ok(w.log.every((x) => x.auth === 'Bearer ' + TOKEN), 'the owner token on every Worker read');
      const lines = await text('[data-q5-stored-lines]');
      assert.match(lines, /보관 결과 · 생산자 aaaaaaaa 실행 · 계산 .* 이 화면에서 재계산 아님/);
      assert.match(lines, /둘 다 원입력에서 따로 계산한 기준과 같음/);
      assert.match(await text('[data-q5-stored-coverage="U1-555"]'), /완전 총점\(순위·95% 분자\)/);
      ok(tag + ' load: 3 reads (stage, manifest, index) with the owner token; stored-result lines; coverage stages');

      phase = tag + ' rows and deciles';
      await page.locator('[data-k="q5-stored-rows"]').click();
      await page.locator('[data-q5-stored-table="U1-555"] tbody tr').first().waitFor({ timeout: 40000 });
      assert.match(await text('[data-q5-stored-table="U1-555"] caption'), /보관 결과 묶음 1\/1 · 생산자 순서 그대로/);
      assert.ok(await page.locator('[data-q5-stored-band]').count() === 10, 'D1–D10 from the producer groups (INLINE in the synthetic delivery)');
      await page.locator('[data-q5-model="S1-555"]').click();
      await page.locator('[data-q5-stored="SHOWN"]').waitFor();
      assert.ok(await page.locator('[data-k="q5-stored-scope"]').count() <= 1);
      ok(tag + ' rows: one detail file checked against the manifest; role deciles D1–D10; S1 by its own ranking scope');

      phase = tag + ' member refusal';
      const s1name = JSON.parse(fs.readFileSync(path.join(STAGED, 'index.json'), 'utf8')).models['S1-555'].files[0].replace(/\.json$/, '');
      const good = fs.readFileSync(path.join(STAGED, s1name + '.json'), 'utf8');
      w.answers['q555_file/' + s1name] = () => ({ status: 200, text: good.replace('"rows"', ' "rows"') });
      await page.waitForTimeout(5300);
      await page.locator('[data-k="q5-stored-rows"]').click();
      await page.waitForFunction(() => { const e = document.querySelector('[data-q5-stored-err]'); return e && /파일이 목록표의 해시와 다름/.test(e.textContent); }, null, { timeout: 40000 });
      assert.equal(await page.locator('[data-q5-stored-table="S1-555"]').count(), 0, 'a member with other bytes is not shown');
      delete w.answers['q555_file/' + s1name]; await page.waitForTimeout(5300);
      await page.locator('[data-k="q5-stored-rows"]').click();
      await page.locator('[data-q5-stored-table="S1-555"] tbody tr').first().waitFor({ timeout: 40000 });
      ok(tag + ' a detail whose bytes differ from the manifest: refused, then the right one shown');

      phase = tag + ' not staged';
      await page.locator('[data-q5-pop="expanded"]').click();
      await page.waitForTimeout(5300);
      await page.locator('[data-k="q5-stored-load"]').click();
      await page.waitForFunction(() => { const e = document.querySelector('[data-q5-stored-err]'); return e && /전달 위치에 없음\(배치 전\)/.test(e.textContent); }, null, { timeout: 40000 });
      await page.locator('[data-q5-pop="universe504"]').click();
      assert.equal(await page.locator('[data-q5-stored="SHOWN"]').count(), 1, 'the operating504 stored result stays');
      ok(tag + ' held1057 not staged: 배치 전 in words; the operating504 result stays');

      phase = tag + ' boundaries';
      assert.deepEqual(w.unexpected, []); assert.deepEqual(seen.outside.filter((u) => !u.startsWith(WORKER) && !u.startsWith('https://accounts.google.com')), []);
      assert.deepEqual(seen.errors.filter((e) => !/status of 4\d\d/.test(e)), []);
      assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter((k) => /q555|qgv555/i.test(k))), []);
      const main = (await text('[data-lb="2.1.1"]'));
      assert.equal(main.match(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/), null, 'no visible reason code');
      ok(tag + ' boundaries: Worker and sign-in only, CSP 0, nothing stored, no code text');
      await ctx.close();
    }
    console.log('PASS ' + pass + ' qgv555 private browser');
  } catch (e) { console.error('FAIL at ' + phase); throw e; } finally { await browser.close(); await s.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
