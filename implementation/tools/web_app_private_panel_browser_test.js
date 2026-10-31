'use strict';
// Common base (public + private two layers, owner 2026-10-31): the one private panel every screen adds next to its public
// part (IS2.parts.privatePanel with IS2.privateArea.panelText). Builds the development site, then in Chromium at 1440 and 390:
//  - a panel starts in NOT_READY (비공개 기능 준비 중) because the private path does not exist yet; no login words appear;
//  - every state shows the same structure: the 비공개 label, one role=status line with the shared words, the drawn character only
//    on ERROR / EMPTY, the screen's own content only on READY; LOGIN_REQUIRED for the Lab area uses its own words;
//  - an ERROR code that is not a fixed code is refused; a bad panel id is refused;
//  - building and switching panels sends no request, writes no storage and adds no style attribute; no horizontal overflow.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path'), http = require('node:http'), { execFileSync } = require('node:child_process');
const ROOT = path.resolve(__dirname, '../..'), OUT = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-panel-'));
fs.rmSync(OUT, { recursive: true });
execFileSync('python3', [path.join(ROOT, 'implementation/tools/build_web_app.py'), '--out', OUT], { stdio: 'inherit' });
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.woff2': 'font/woff2', '.txt': 'text/plain' };
const server = http.createServer((req, res) => { const name = decodeURIComponent(new URL(req.url, 'http://x').pathname.slice(1)) || 'index.html'; const file = path.join(OUT, name);
  if (!file.startsWith(OUT) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res); });
let phase = 'START';
(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const BASE = 'http://127.0.0.1:' + server.address().port + '/', ORIGIN = new URL(BASE).origin;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      phase = String(width);
      const context = await browser.newContext({ viewport: { width, height } }), page = await context.newPage(), outside = [], errors = [];
      page.on('request', (r) => { if (new URL(r.url()).origin !== ORIGIN) outside.push(r.url()); });
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.goto(BASE + '#/'); await page.locator('main[data-route]').waitFor(); await page.evaluate(() => window.IS2.ready);
      const before = await page.evaluate(() => ({ ls: localStorage.length, ss: sessionStorage.length }));
      const at0 = await page.evaluate(() => performance.getEntriesByType('resource').length);
      const r = await page.evaluate(() => {
        const P = window.IS2.parts, host = document.createElement('div'); host.dataset.testHost = ''; document.querySelector('main').appendChild(host);
        const out = {}, view = (p) => ({ state: p.node.dataset.privateState, label: p.node.querySelector('[data-private-label]').textContent,
          status: p.node.querySelector('[data-private-status]').textContent, statusHidden: p.node.querySelector('[data-private-status]').hidden,
          role: p.node.querySelector('[data-private-status]').getAttribute('role'), mascot: p.node.querySelectorAll('[data-mascot]').length,
          body: p.node.querySelector('.private-body').textContent, aria: p.node.getAttribute('aria-label') });
        const p = P.privatePanel({ id: 'tech-chart', title: '실가격 차트' }), lab = P.privatePanel({ id: 'lab-results', title: '연구 결과', area: 'lab' });
        host.append(p.node, lab.node);
        out.first = view(p); out.firstLab = view(lab);
        out.login = view((p.set('LOGIN_REQUIRED'), p)); out.loginLab = view((lab.set('LOGIN_REQUIRED'), lab));
        out.loading = view((p.set('LOADING'), p)); out.error = view((p.set('ERROR', { code: 'ACCESS_REQUIRED' }), p));
        out.empty = view((p.set('EMPTY'), p));
        out.ready = view((p.set('READY', { render: (b) => b.appendChild(document.createTextNode('차트 자리')) }), p));
        out.back = view((p.set('NOT_READY'), p));
        try { p.set('ERROR', { code: 'see https://x' }); out.badCode = 'accepted'; } catch (e) { out.badCode = String(e.message); }
        try { P.privatePanel({ id: 'Bad Id' }); out.badId = 'accepted'; } catch (e) { out.badId = String(e.message); }
        out.styleAttrs = document.querySelectorAll('[style]').length;
        out.overflow = document.documentElement.scrollWidth > window.innerWidth + 1;
        return out;
      });
      assert.deepEqual(r.first, { state: 'NOT_READY', label: '비공개', status: '비공개 기능 준비 중', statusHidden: false, role: 'status', mascot: 0, body: '', aria: '비공개 · 실가격 차트' }, phase + ' first state');
      assert.equal(r.firstLab.status, '비공개 기능 준비 중', phase + ' lab first state');
      assert.equal(r.login.status, '로그인 필요'); assert.equal(r.loginLab.status, '비공개 연구 결과 · 로그인 필요');
      assert.equal(r.loading.status, '비공개 자료 불러오는 중'); assert.equal(r.loading.mascot, 0);
      assert.equal(r.error.status, '비공개 자료를 불러오지 못했습니다 · ACCESS_REQUIRED'); assert.equal(r.error.mascot, 1);
      assert.equal(r.empty.status, '비공개 자료가 아직 없습니다'); assert.equal(r.empty.mascot, 1);
      assert.equal(r.ready.statusHidden, true); assert.equal(r.ready.body, '차트 자리'); assert.equal(r.ready.mascot, 0);
      assert.equal(r.back.status, '비공개 기능 준비 중'); assert.equal(r.back.body, '');
      for (const v of Object.values(r)) if (v && typeof v === 'object') assert.doesNotMatch(v.status, /로그인됨/, phase + ' no login words');
      assert.match(r.badCode, /PRIVATE_CODE_INVALID/); assert.match(r.badId, /PANEL_ID_INVALID/);
      assert.equal(r.styleAttrs, 0, phase + ' no style attribute'); assert.equal(r.overflow, false, phase + ' no horizontal overflow');
      assert.equal(await page.evaluate(() => performance.getEntriesByType('resource').length), at0, phase + ' panels send no request');
      assert.deepEqual(await page.evaluate(() => ({ ls: localStorage.length, ss: sessionStorage.length })), before, phase + ' panels store nothing');
      assert.deepEqual(outside, [], phase + ' no request leaves the origin'); assert.deepEqual(errors, [], phase + ' no page error');
      await context.close();
    }
    console.log('web app private panel: one panel shape, shared states and words (NOT_READY first), no request, storage or style ok at 1440 and 390');
  } catch (err) { console.error('FAILED at ' + phase); console.error(err); process.exitCode = 1; }
  finally { await browser.close(); server.close(); fs.rmSync(OUT, { recursive: true, force: true }); }
})();
