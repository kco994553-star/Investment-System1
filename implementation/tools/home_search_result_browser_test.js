'use strict';
// Menu 0 search result (owner draft "투자시스템 화면 시안 (손그림 칠판)", 2026-10-18; owner decision 2026-10-20 item 5) at
// 390 / 1280 / 1440: typing a company on home shows the "검색 결과" stamp, the company line and five cards (1 QGV · 2 기술적
// 분석 · 3 매크로 · 4 이 기업 소식 · 5 내 포트폴리오에서), each in its menu colour and linking into the right menu.
// Pass A serves the empty public screens (tools/empty_public_screens.js): every value reads 미산출/없음, nothing invented.
// Pass B serves the SYNTHETIC QGV v2 test payload (qgv_v2_fixture.js, made-up numbers, test only): Q/G on the card are exactly
// the app's own shared score result (leaderScores), V stays 미산출 without device prices, the rank is the Q·G reference.
// Every pass: no horizontal overflow, GET only, same origin only, no page error, no order/buy/sell wording, the result follows
// the highlighted row, and an empty query removes it.
const { chromium } = require('playwright'), assert = require('node:assert/strict');
const { routeEmptyPublicScreens } = require('./empty_public_screens.js'), { displayOnlyOff } = require('./display_only_off.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const CARDS = { qgv: '1', technical: '2', macro: '3', news: '4', portfolio: '5' };
const LINKS = { leaderboard: '#leaderboard', profiles: '#profiles', radar: '#company/nvda', scenario: '#technical/nvda', pattern: '#technical-pattern/nvda', notes: '#technical-notes/nvda',
  evidence: '#macro-cycle', conditions: '#macro-rotation', probability: '#macro-industry', news: '#news/nvda', network: '#news-network', report: '#report/real', portfolio: '#portfolio', company: '#company/nvda' };
let phase = 'START';
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  try {
    for (const fixture of [false, true]) for (const width of [390, 1280, 1440]) {
      phase = (fixture ? 'FIXTURE_' : 'EMPTY_') + width;
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await displayOnlyOff(context);await routeEmptyPublicScreens(context);
      if (fixture) await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
      const page = await context.newPage(), traffic = { unsafe: 0, external: 0 };let errors = 0;
      page.on('pageerror', () => errors++);
      await page.route('**/*', (r) => { const q = r.request();if (q.method() !== 'GET') { traffic.unsafe++;return r.abort(); }if (!/^(data|blob):/.test(q.url()) && new URL(q.url()).origin !== ORIGIN) { traffic.external++;return r.abort(); }return r.fallback(); });
      await page.goto(BASE + '#home');await page.locator('#home-search-slot #global-search').waitFor();
      assert.equal(await page.locator('#home-result').isHidden(), true);
      assert.match(await page.locator('[data-home-device]').textContent(), /로그인 안 함 · 이 기기 기준/);
      await page.waitForFunction(() => typeof window.investmentSearch === 'function');
      await page.fill('#global-search', 'NVDA');
      const host = page.locator('#home-result[data-result-company="nvda"]');await host.waitFor();
      assert.equal(await host.locator('.res-stamp').textContent(), '검색 결과');
      assert.match(await host.locator('.res-name').textContent(), /NVDA/);
      assert.match(await host.locator('[data-res-fact="ticker"]').textContent(), /NVDA · NASDAQ/);
      // classification is absent in both passes: SIC and type read 미산출, never a guessed group.
      assert.equal(await host.locator('[data-res-fact="sic"] [data-res-state="NOT_AVAILABLE"]').count(), 1);
      // five cards, in order, numbered and coloured by their menu
      assert.deepEqual(await host.locator('[data-result-card]').evaluateAll((a) => a.map((x) => [x.dataset.resultCard, x.dataset.menu, x.querySelector('.res-num').textContent])), Object.entries(CARDS).map(([k, n]) => [k, k, n]));
      const shadow = await host.locator('[data-result-card]').evaluateAll((a) => a.map((x) => getComputedStyle(x).boxShadow));
      assert.equal(new Set(shadow).size, 5);
      // links go to the right menus
      const links = await host.locator('a[data-result-link]').evaluateAll((a) => a.map((x) => [x.dataset.resultLink, x.getAttribute('href')]));
      assert.deepEqual(Object.fromEntries(links), LINKS);
      // technical and macro: device-only / official 미산출, no marker, no line drawn from data
      for (const k of ['signal', 'pattern']) assert.equal(await host.locator('[data-result-card="technical"] [data-res-row="' + k + '"] [data-res-state="NOT_AVAILABLE"]').count(), 1);
      assert.equal(await host.locator('[data-result-card="macro"] [data-res-row="economy"] [data-res-state="NOT_AVAILABLE"]').count(), 1);
      assert.equal(await host.locator('[data-result-card="macro"] circle, [data-result-card="technical"] .res-wave').count(), 0);
      // news (empty public files): 없음, never a sample item; Q·G effect and relations 미산출
      await host.locator('[data-res-news]:not([aria-busy])').waitFor();
      assert.equal(await host.locator('[data-res-news-item]').count(), 0);
      assert.equal(await host.locator('[data-res-news-empty] [data-res-state="EMPTY"]').count(), 1);
      for (const k of ['effect', 'relation']) assert.equal(await host.locator('[data-result-card="news"] [data-res-row="' + k + '"] [data-res-state="NOT_AVAILABLE"]').count(), 1);
      // portfolio: the public TARGET model weight (price-free); no ACTUAL on this device; paper 미산출
      await host.locator('[data-res-portfolio]:not([aria-busy])').waitFor();
      const model = await page.evaluate(async () => { const c = await deviceCatalog(), i = c.instruments.find((x) => x.ticker === 'NVDA');return i ? new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(i.target_units / c.total_units * 100) + '%' : null; });
      if (model) assert.equal(await host.locator('[data-res-row="model"] .num').textContent(), model);
      assert.equal(await host.locator('[data-res-row="actual"] [data-res-state="EMPTY"]').count(), 1);
      assert.equal(await host.locator('[data-res-row="paper"] [data-res-state="NOT_AVAILABLE"]').count(), 1);
      // QGV: exactly the app's shared result, or 미산출
      const expected = await page.evaluate(() => { const r = QgvScores.rowOf(leaderScores(), 'nvda'), d = r ? r.primary : null;return d ? { q: d.q, g: d.g, v: d.v, total: d.total, rank: r.rank } : null; });
      const fmt = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
      for (const a of ['Q', 'G', 'V']) {
        const v = expected ? expected[a.toLowerCase()] : null, bar = host.locator('.res-bar[data-axis="' + a + '"]');
        if (Number.isFinite(v)) { assert.equal(await bar.getAttribute('data-res-state'), 'AVAILABLE');assert.equal(await bar.locator('.num').textContent(), fmt(v)); }
        else { assert.equal(await bar.getAttribute('data-res-state'), 'NOT_AVAILABLE');assert.equal(await bar.locator('.res-bar-fill').count(), 0); }
      }
      if (fixture) { assert.ok(Number.isFinite(expected.q) && Number.isFinite(expected.g));assert.equal(Number.isFinite(expected.v), false);assert.equal(await host.locator('[data-res-row="rank"] [data-res-state="QG_REFERENCE"]').count(), 1); }
      else assert.equal(expected === null || (expected.q === null && expected.g === null), true);
      // wording and layout
      const text = await host.innerText();
      assert.doesNotMatch(text, /매수|매도|주문|사세요|파세요|\bbuy\b|\bsell\b|\border\b/i);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      assert.ok(await host.evaluate((h) => [...h.querySelectorAll('*')].every((x) => x.getBoundingClientRect().right <= innerWidth + 0.5)));
      if (width >= 1024) { const top = await host.locator('[data-result-card]').evaluateAll((a) => a.map((x) => Math.round(x.getBoundingClientRect().top)));assert.ok(top[0] === top[1] && top[1] === top[2] && top[3] === top[4] && top[3] > top[0]); }
      // the result follows the highlighted company row
      await page.fill('#global-search', 'a');await page.waitForFunction(() => document.querySelectorAll('#global-results [role="option"]').length > 1);
      await page.locator('#global-search').press('ArrowDown');await page.locator('#global-search').press('ArrowDown');
      const sel = await page.locator('#global-results [aria-selected="true"]').getAttribute('data-entity-id');
      if (sel.startsWith('COMPANY:')) assert.equal(await page.locator('#home-result').getAttribute('data-result-entity'), sel);
      // empty query: no result block
      await page.fill('#global-search', '');assert.equal(await page.locator('#home-result').isHidden(), true);assert.equal(await page.locator('#home-result > *').count(), 0);
      // a card link opens its menu and is remembered as a recent search
      await page.fill('#global-search', 'NVDA');await host.waitFor();
      await host.locator('a[data-result-link="leaderboard"]').click();await page.waitForFunction(() => location.hash === '#leaderboard');
      assert.ok(await page.evaluate(() => JSON.parse(localStorage.getItem('investment.web.v1.recent-search') || '[]').includes('COMPANY:nvda')));
      assert.equal(errors, 0);assert.deepEqual(traffic, { unsafe: 0, external: 0 });
      pass++;console.log('PASS home search result ' + phase);await context.close();
    }
  } catch (e) { fail++;console.log('FAIL home search result ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'ASSERTION ' + e.message.split('\n')[0] : 'BROWSER ' + e.message.split('\n')[0])); }
  finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
