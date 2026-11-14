'use strict';
// Public preview of the new frontend (DC-51; owner 2026-11-14: a preview anyone can open). Builds the real Pages artifact
// (tools/build_pages_cockpit.py, the build both deploy workflows run), serves it, and checks in Chromium at 320, 390 and 1440:
//  - app.html shows the banner "새 화면 미리보기 · 일부 기능 준비 중" once, with links to the current screens (./#home …), and
//    the new app's shell; the loader finishes (the reused current files and the new layer load from the same folder);
//  - on every menu screen, each private panel is only "준비 중" or "로그인 필요" (NOT_READY / LOGIN_REQUIRED), never READY, no
//    RAM price element exists and the sheet price button is off, and nothing is requested from another origin (no sign-in
//    script, no Worker), so no private data can arrive before login;
//  - no page error, no console error except 404s of live-only public data files, no device storage written by opening and
//    moving between screens, no horizontal overflow;
//  - the current index.html is the current screen: no banner, no new-app shell.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const site = require('./web_app_test_site');
const { ROOT } = require('./web_app_reuse');

const BANNER = '새 화면 미리보기 · 일부 기능 준비 중';
const ROUTES = ['#/', '#/qgv', '#/technical', '#/macro', '#/news', '#/portfolio', '#/prompts', '#/tree', '#/lab'];
const PRIVATE_OK = new Set(['NOT_READY', 'LOGIN_REQUIRED']);

function buildPages() {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'web-app-preview-'));
  fs.rmSync(out, { recursive: true });
  execFileSync('python3', [path.join(ROOT, 'implementation/tools/build_pages_cockpit.py'), '--out', out], { stdio: ['ignore', 'ignore', 'inherit'] });
  return out;
}

let phase = 'START';
(async () => {
  const out = buildPages();
  const server = await site.start({ out });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  let checks = 0;
  try {
    for (const [width, height] of [[320, 700], [390, 844], [1440, 1000]]) {
      phase = String(width);
      const context = await browser.newContext({ viewport: { width, height } }), page = await context.newPage();
      const seen = { outside: [], errors: [], missing: new Set() };
      let panels = 0;
      page.on('request', (r) => { if (new URL(r.url()).origin !== server.origin) seen.outside.push(r.url()); });
      page.on('response', (r) => { if (r.status() === 404) seen.missing.add(decodeURIComponent(new URL(r.url()).pathname.slice(1))); });
      page.on('console', (m) => { if (m.type() === 'error' && !/status of 404/.test(m.text())) seen.errors.push(m.text()); });
      page.on('pageerror', (e) => seen.errors.push(String(e)));

      await page.goto(server.base + 'app.html#/');
      await page.locator('main[data-route]').waitFor();
      await page.evaluate(() => window.IS2.ready);
      const head = await page.evaluate(() => {
        const b = document.querySelector('.is2-preview');
        return { count: document.querySelectorAll('.is2-preview').length, text: b && b.querySelector('strong').textContent,
          role: b && b.getAttribute('role'), links: b ? [...b.querySelectorAll('a')].map((a) => [a.textContent, a.getAttribute('href')]) : [],
          visible: !!b && b.getBoundingClientRect().height > 0, first: document.body.firstElementChild === b || document.body.children[1] === b,
          state: window.IS2.loadState() };
      });
      assert.equal(head.count, 1); assert.equal(head.text, BANNER); assert.equal(head.role, 'note'); assert.ok(head.visible);
      assert.deepEqual(head.links, [['홈', './#home'], ['리더보드', './#leaderboard'], ['기술적 분석', './#technical'], ['포트폴리오', './#portfolio']]);
      assert.equal(head.state, 'READY');
      checks += 6;

      for (const route of ROUTES) {
        phase = width + ' ' + route;
        await page.evaluate((h) => { location.hash = h; }, route);
        await page.waitForFunction((h) => document.querySelector('main[data-route]') && location.hash === h, route);
        await page.waitForTimeout(150);
        const r = await page.evaluate(() => ({
          panels: [...document.querySelectorAll('[data-private-state]')].map((p) => ({ state: p.dataset.privateState,
            status: (p.querySelector('[data-private-status]') || p).textContent })),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          banner: document.querySelectorAll('.is2-preview').length,
          ram: document.querySelectorAll('[data-ram-price]').length,
          priceButtons: [...document.querySelectorAll('[data-k=load-tabs]')].map((b) => b.disabled),
        }));
        for (const p of r.panels) {
          assert.ok(PRIVATE_OK.has(p.state), `${route}: private panel state ${p.state}`);
          assert.match(p.status, /준비 중|로그인 필요/, `${route}: private panel text`);
        }
        assert.ok(r.overflow <= 1, `${route}: horizontal overflow ${r.overflow}`);
        assert.equal(r.banner, 1);
        // Before login nothing price-like is on screen, and the sheet price button stays off.
        assert.equal(r.ram, 0, `${route}: no RAM price element before login`);
        assert.ok(r.priceButtons.every(Boolean), `${route}: price button off before login`);
        panels += r.panels.length;
        checks += 5;
      }
      // The private panels exist (technical, macro, news, Lab) and all of them were checked above.
      assert.ok(panels >= 5, `private panels seen: ${panels}`);
      checks += 1;

      const stored = await site.storage(page);
      assert.equal(stored.local, 0, 'no localStorage'); assert.equal(stored.session, 0, 'no sessionStorage'); assert.equal(stored.idb, 0, 'no IndexedDB');
      assert.deepEqual(seen.outside, [], 'no request leaves the origin');
      assert.deepEqual(seen.errors, [], 'no page or console error');
      for (const name of seen.missing) assert.match(name, /^[a-z0-9-]+\.json$/, `only live-only public data may be missing: ${name}`);
      checks += 6;

      // The current screens: same page as before, no banner, no new shell.
      phase = width + ' current';
      await page.goto(server.base + '#home');
      await page.waitForLoadState('load');
      const current = await page.evaluate(() => ({ banner: document.querySelectorAll('.is2-preview').length, shell: !!document.querySelector('#app main[data-route]'),
        css: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.getAttribute('href')).includes('preview-banner.css') }));
      assert.deepEqual(current, { banner: 0, shell: false, css: false });
      checks += 1;
      await context.close();
    }
    console.log(`web_app_preview_browser_test: ${checks} checks passed`);
  } catch (e) {
    console.error(`web_app_preview_browser_test failed at ${phase}:`, e && e.stack || e);
    process.exitCode = 1;
  } finally {
    await browser.close();
    await server.close();
    fs.rmSync(out, { recursive: true, force: true });
  }
})();
