'use strict';
// Browser test of the frontend at 390 and 1440 px against the fixture public dir (tools/fixture_public_dir.js, ledger active)
// served by tools/dev_server.py. Run with tools/run_browser_test.sh. Checks: every route renders without page errors or
// horizontal scroll, results-only text (no raw codes), missing is never 0, no storage writes, no other-origin requests,
// and the empty state when sec-qgv2.json is not published.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const BASE = process.env.FRONTEND_URL || 'http://127.0.0.1:8994/app/';
const ORIGIN = new URL(BASE).origin;
const CODE = /\b[A-Z]{3,}_[A-Z_]{3,}\b/;
const ROUTES = [['#/', 'today'], ['#/qgv', 'qgv'], ['#/qgv/target', 'target'], ['#/qgv/market', 'market'], ['#/company/nvda', 'company'], ['#/macro', 'macro'], ['#/technical', 'technical'], ['#/validation', 'validation'], ['#/settings', 'settings']];

async function go(page, hash) {
  await page.evaluate((h) => { location.hash = h; }, hash);
  await page.waitForFunction((h) => location.hash === h && document.querySelector('main h1'), hash);
}
const visible = (page) => page.evaluate(() => document.querySelector('main').innerText);
const noScroll = (page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0, phase = 'START';
  try {
    for (const width of [390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      const page = await context.newPage();
      const errors = [], foreign = [];
      page.on('pageerror', (e) => errors.push(e.message));
      page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
      page.on('request', (r) => { if (new URL(r.url()).origin !== ORIGIN) foreign.push(r.url()); });
      try {
        phase = 'LOAD'; await page.goto(BASE + '#/'); await page.locator('main h1').waitFor();
        for (const [hash, name] of ROUTES) {
          phase = 'ROUTE ' + name; await go(page, hash);
          assert.ok(await noScroll(page), 'no horizontal scroll ' + name);
          const text = await visible(page);
          assert.ok(!CODE.test(text.replaceAll('NOT_AVAILABLE', '')), 'no raw codes on ' + name + ': ' + (text.match(CODE) || [])[0]);
          assert.ok(!/undefined|NaN|\[object/.test(text), 'no broken values on ' + name);
        }
        phase = 'TODAY'; await go(page, '#/');
        assert.match(await page.locator('[data-today-stats] .stat').first().textContent(), /Q 산출\d+\/504 종목/);
        assert.equal(await page.locator('[data-system-flow] li').count(), 4);
        assert.equal(await page.locator('[data-target-row]').count(), 19);
        assert.equal(await page.locator('#primary-nav [aria-current="page"]').getAttribute('data-tab'), 'today');

        phase = 'QGV'; await go(page, '#/qgv');
        assert.equal(await page.locator('[data-leaderboard-table] tbody tr').count(), 50, 'first page of 50');
        assert.match(await page.locator('[data-count]').textContent(), /^\d+개 · QGV 점수 있음 \d+개$/);
        // A NOT_AVAILABLE row shows '—' and keeps its reason folded; never a 0 or a v1 score.
        const na = page.locator('[data-leaderboard-table] tr[data-state="NOT_AVAILABLE"]').first();
        assert.equal((await na.locator('td').nth(2).locator('.na').textContent()).trim(), '—');
        assert.equal(await na.locator('details.why').getAttribute('open'), null);
        assert.match(await na.locator('[data-reason]').textContent(), /^QGV v2 산출 불가/);
        await page.fill('[data-search]', 'nvda'); await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-table] tbody tr').length === 1);
        assert.equal(await page.locator('[data-leaderboard-table] tbody tr').getAttribute('data-row'), 'nvda');
        await page.fill('[data-search]', ''); await page.selectOption('[data-scope]', 'target');
        await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-table] tbody tr').length === 19);
        await page.selectOption('[data-sort]', 'q');
        const qs = await page.locator('[data-leaderboard-table] tbody tr td:nth-child(4)').allTextContents();
        const nums = qs.map((x) => x.trim()).filter((x) => x !== '—').map(Number);
        assert.deepEqual(nums, [...nums].sort((a, b) => b - a), 'Q high first');
        assert.ok(qs.slice(nums.length).every((x) => x.trim() === '—'), 'missing last');
        const before = await page.locator('tr[data-row="nvda"] td:nth-child(3)').textContent();
        await page.locator('[data-preset="growth"]').click(); await page.locator('[data-preset="growth"][aria-pressed="true"]').waitFor();
        assert.notEqual(await page.locator('tr[data-row="nvda"] td:nth-child(3)').textContent(), before, 'profile changes the total');
        await page.locator('[data-preset="balanced"]').click(); await page.locator('[data-preset="balanced"][aria-pressed="true"]').waitFor();

        phase = 'COMPANY'; await go(page, '#/company/nvda');
        assert.equal(await page.locator('main h1').textContent(), 'NVDA');
        assert.match(await page.locator('[data-score="total"] .value').textContent(), /^\d+\.\d$/);
        assert.equal(await page.locator('[data-score="V"] .value').textContent(), '—');
        assert.match(await page.locator('[data-score="V"]').textContent(), /가격 필요/);
        assert.equal(await page.locator('[data-factor]').count(), 15);
        assert.equal(await page.locator('[data-factor][data-reason-code="NO_DEVICE_PRICE"]').count(), 5, 'V factors wait for prices');
        assert.equal(await page.locator('[data-classification] [data-axis]').count(), 3);
        assert.match(await page.locator('[data-next-earnings]').textContent(), /^다음 실적 (\d\d\/\d\d경 \(확정 아님\) · (D-\d+|제출 구간 진행 중)|확인 불가)$/);
        await go(page, '#/company/unknown'); assert.equal(await page.locator('main h1').textContent(), '기업을 찾을 수 없습니다');

        phase = 'MACRO'; await go(page, '#/macro');
        assert.equal(await page.locator('[data-light]').count(), 5);
        assert.deepEqual(await page.locator('[data-light]').evaluateAll((n) => n.map((x) => x.dataset.lit)), ['off', 'off', 'on', 'na', 'na']);
        assert.match(await page.locator('[data-macro-state]').textContent(), /켜짐 1 \/ 확인 가능 3 \/ 전체 5/);

        phase = 'VALIDATION'; await go(page, '#/validation');
        assert.equal(await page.locator('[data-ledger-day]').count(), 3);
        assert.match(await page.locator('[data-ledger-day="2026-10-19"]').textContent(), /준비 기록/);
        assert.match(await page.locator('[data-ledger-day="2026-10-21"]').textContent(), /본 기록/);

        phase = 'SETTINGS'; await go(page, '#/settings');
        assert.equal(await page.locator('[data-raw]').getAttribute('open'), null, 'raw data collapsed by default');
        await page.locator('[data-raw] > summary').click();
        await page.selectOption('[data-raw-company]', 'msft');
        assert.match(await page.locator('[data-raw-json]').textContent(), /"qg_axes"/);
        assert.equal(await page.locator('[data-source]').count(), 10);

        phase = 'BOUNDARY';
        assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0, 'nothing stored');
        assert.deepEqual(foreign, [], 'no other-origin requests');
        assert.deepEqual(errors, [], 'no page errors');
        pass++; console.log('PASS frontend screens ' + width);
      } catch (e) {
        fail++; console.log('FAIL frontend screens ' + width + ' ' + phase + ' ' + String(e.message).split('\n')[0]);
      } finally { await context.close(); }

      // Empty state: sec-qgv2.json not published (a PR build) -> NOT_AVAILABLE everywhere, nothing invented.
      const ctx2 = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await ctx2.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      await ctx2.route('**/forward-validation-ledger.json*', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      const p2 = await ctx2.newPage(); const err2 = []; p2.on('pageerror', (e) => err2.push(e.message));
      try {
        phase = 'EMPTY'; await p2.goto(BASE + '#/'); await p2.locator('main h1').waitFor();
        assert.match(await p2.locator('main .lede').first().textContent(), /공개 QGV 자료가 아직 없습니다/);
        assert.equal(await p2.locator('[data-today-stats] .stat').first().locator('.value').textContent(), '—');
        assert.ok((await p2.locator('[data-target-row] td.num .na').count()) >= 19 * 3, 'TARGET scores are — without v2 inputs');
        await go(p2, '#/qgv');
        assert.equal(await p2.locator('[data-leaderboard-table] tbody tr').count(), 19, 'TARGET identities only');
        assert.equal(await p2.locator('[data-leaderboard-table] tr[data-state="NOT_AVAILABLE"]').count(), 19);
        await go(p2, '#/validation'); assert.match(await p2.locator('[data-card="ledger"]').textContent(), /원장 파일이 아직 게시되지 않았습니다/);
        assert.ok(await noScroll(p2));
        assert.deepEqual(err2, []);
        pass++; console.log('PASS frontend empty state ' + width);
      } catch (e) {
        fail++; console.log('FAIL frontend empty state ' + width + ' ' + phase + ' ' + String(e.message).split('\n')[0]);
      } finally { await ctx2.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
