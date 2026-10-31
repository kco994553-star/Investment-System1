'use strict';
// D10 price time (PriceTime): the READ time and the price's OWN time are shown apart on the real user paths.
// SYNTHETIC FIXTURE PRICES ONLY (made-up numbers, never real prices); Google Sheets and the Worker are stubbed in RAM.
// (a) "Universe 읽기" (S06): GOOGLEFINANCE_CURRENT has no trade time -> exactly '가격 기준 시각 미확인', read time shown apart,
//     freshness '신선도 판정 불가'.
// (b) Quote import -> #N/A -> Worker daily close still runs (the holdings/charts paths keep it). DC-31 (device V abolished): the
//     company page no longer shows the device price badge or the device value card that showed these quote times (removed with
//     the value panel; public IEX prices come with the separate price-display decision GSQ-026). The PriceTime rules themselves
//     (trade date = price date, old date STALE, no trade time = 미확인) stay covered by price_time_node_test.js.
// Also: no request leaves the page origin, no page error, the Universe canary price never reaches storage.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/', ORIGIN = new URL(BASE).origin;
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const DAY = 86400, UNIVERSE_CANARY = '987.654';
const dayOf = (sec) => new Date(sec * 1000).toISOString().slice(0, 10);
// Worker history (synthetic): last COMPLETE bar `ago` days back at 14:00 UTC (same New York date), then one IN_PROGRESS bar.
function history(symbol, ago, close) {
  const base = Math.floor(Date.now() / 1000 / DAY) * DAY, done = base - ago * DAY + 14 * 3600;
  return { schema: 'private-history/1', provider: 'SYNTHETIC', symbol, range: '1mo', currency: 'USD', exchange: 'SYN', timezone: 'America/New_York', interval: '1d', basis: 'RAW_CLOSE',
    delay_status: 'UNKNOWN', read_at: new Date().toISOString(),
    bars: [{ timestamp: done - DAY, open: 1, high: close, low: 1, close: close - 1, adjusted_close: null, volume: 1, session_status: 'COMPLETE' },
      { timestamp: done, open: 1, high: close, low: 1, close, adjusted_close: null, volume: 1, session_status: 'COMPLETE' },
      ...(ago > 0 ? [{ timestamp: base + 3600, open: 1, high: close, low: 1, close: close + 1, adjusted_close: null, volume: 1, session_status: 'IN_PROGRESS' }] : [])] };
}
const READ = /^읽은 시각 (\d{4}-\d\d-\d\d \d\d:\d\d) UTC · \d{4}-\d\d-\d\d \d\d:\d\d KST$/;
function readFresh(text, what) {
  const m = READ.exec(text);assert.ok(m, what + ' read time format: ' + text);
  const at = Date.parse(m[1].replace(' ', 'T') + ':00Z');assert.ok(Math.abs(Date.now() - at) < 10 * 60 * 1000, what + ' read time is now');
}
async function stubSession(page, values, histories) {
  await page.evaluate(({ values, histories }) => {
    const session = { state: () => ({ enabled: true, connected: true, ready: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {},
      async fetchValues() { return { values }; },
      async fetchHistory(origin, symbol) { window.__workerCalls.push(symbol);if (!histories[symbol]) throw new Error('REQUEST_INVALID');return histories[symbol]; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
  }, { values, histories });
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn();pass++;console.log('PASS ' + name); } catch (e) { fail++;console.log('FAIL ' + name + ' · ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } };
  const open = async (width) => {
    const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' }), page = await context.newPage();page.setDefaultTimeout(15000);
    const state = { errors: 0, external: [] };page.on('pageerror', () => state.errors++);
    page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) state.external.push(new URL(r.url()).origin); });
    await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
    await page.addInitScript((worker) => { window.__workerCalls = [];localStorage.setItem('investment.web.v1.private-history-origin', worker); }, WORKER);
    return { context, page, state };
  };
  try {
    for (const width of [390, 1280]) await check('(a) Universe read: 가격 기준 시각 미확인 with the read time apart · ' + width, async () => {
      const { context, page, state } = await open(width);
      try {
        phase = 'A_SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async () => { await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' }); });
        await stubSession(page, [['code', 'marketcap', 'price'], ['NASDAQ:NVDA', '', Number(UNIVERSE_CANARY)], ['NYSE:ZZZZ', '', 12.5]], {});
        await page.evaluate(() => { location.hash = 'leaderboard'; });
        phase = 'A_BEFORE';const line = page.locator('[data-universe-price-time]');await line.waitFor({ state: 'attached' });
        assert.equal((await line.textContent()).trim(), '', 'no price time line before the read');
        phase = 'A_READ';await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await line.locator('.price-time').waitFor();
        const t = line.locator('.price-time');
        assert.equal(await line.locator('[data-price-source]').getAttribute('data-price-source'), 'GOOGLEFINANCE_PRIVATE_UNIVERSE');
        assert.equal(await t.getAttribute('data-price-time-status'), 'UNCONFIRMED');assert.equal(await t.getAttribute('data-price-freshness'), 'UNDETERMINED');
        assert.equal(await t.locator('[data-price-own-time]').textContent(), '가격 기준 시각 미확인');
        readFresh(await t.locator('[data-price-read-at]').textContent(), 'universe');
        assert.equal(await t.locator('[data-price-stale]').textContent(), '신선도 판정 불가');
        assert.ok(!/STALE|CURRENT|LIVE/.test(await line.textContent()), 'never fresh or stale');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide scroll');
        phase = 'A_RAM';const stored = await page.evaluate(() => JSON.stringify(Object.entries(localStorage)) + JSON.stringify(Object.entries(sessionStorage)));
        assert.ok(!stored.includes(UNIVERSE_CANARY), 'Universe price never stored');
        phase = 'A_CLEAR';await page.locator('[data-private-subset] [data-subset-action="clear"]').click();
        await page.waitForFunction(() => document.querySelector('[data-universe-price-time]').textContent.trim() === '');
        assert.equal(state.errors, 0);assert.deepEqual(state.external, []);
      } finally { await context.close(); }
    });
    await check('(b) quote import still reads the Worker close; no device price badge or value card on the company page (DC-31)', async () => {
      const { context, page, state } = await open(390);
      try {
        phase = 'B_SETUP';await page.goto(BASE + '#settings');await page.locator('[data-sheet-paste]').waitFor({ state: 'attached' });
        // The bulk paste box sits in a collapsed settings section: open it the way a user would (its <details> ancestors).
        for (let i = 0; i < 4 && !(await page.locator('[data-sheet-paste]').isVisible()); i++) await page.evaluate(() => { const d = [...document.querySelectorAll('details')].find((x) => !x.open && x.contains(document.querySelector('[data-sheet-paste]')));if (d) d.querySelector(':scope > summary').click(); });
        const old = new Date(Date.now() - 30 * DAY * 1000).toISOString().slice(0, 10) + 'T16:00:00Z';
        await stubSession(page, [], { NVDA: history('NVDA', 1, 61.25), AMD: history('AMD', 30, 41.5) });
        // Synthetic paste: NVDA/AMD #N/A (-> Worker close), ASML with an old KNOWN trade time, LRCX with no trade time (UNKNOWN).
        await page.locator('[data-sheet-paste]').fill(['code,price,tradetime', 'NASDAQ:NVDA,#N/A,', 'NASDAQ:AMD,#N/A,', 'NASDAQ:ASML,71.5,' + old, 'NASDAQ:LRCX,33.25,'].join('\n'));
        await page.locator('[data-sheet-action="paste"]').click();
        await page.waitForFunction(() => /Worker/.test(document.querySelector('[data-sheet-summary]')?.textContent || ''));
        assert.deepEqual((await page.evaluate(() => window.__workerCalls)).sort(), ['AMD', 'NVDA']);
        phase = 'B_COMPANY';for (const id of ['nvda', 'amd', 'asml', 'lrcx']) {
          await page.evaluate((x) => { location.hash = 'company/' + x; }, id);await page.waitForFunction((x) => location.hash === '#company/' + x, id);await page.locator('[data-company-card="qgv"]').waitFor();
          assert.equal(await page.locator('[data-badge="price"], #company-value, [data-value-quote-time]').count(), 0, id + ': no device price badge or value card (DC-31)'); }
        assert.equal(state.errors, 0);assert.deepEqual(state.external, []);
      } finally { await context.close(); }
    });
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
