'use strict';
// Price store (Prices_D / Prices_M in the user's own sheet) on the built site. Every request is intercepted: same-origin
// files come from the local build (public screens empty), Google Sheets and the private history Worker are stateful
// SYNTHETIC mocks, anything else is aborted and counted. Checks: OFF until the user's click; the click creates only the two
// price tabs with the fixed header; app open appends the core symbols' daily bars (first run 5y); a reload asks the Worker
// for nothing already stored; a company screen reuses stored rows (Worker-allowlisted symbols only); the Universe504 button
// requests only allowlisted symbols; the S17 runner reads the store and gets READY without new Worker requests; a different
// header is never written; no close reaches localStorage, sessionStorage or the console. Also measures the read/parse time
// of a synthetic full-size store (504 × 60 month-ends + 40 × 1260 daily bars).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'price', 'store', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const SHEET = 'synthetic_existing_sheet_fixture';
const HEAD = ['symbol', 'date', 'close', 'source', 'fetched_at'];
const NOW = '2026-10-31T01:00:00Z';
const CANARY = '777.0731'; // synthetic close carried by one bar: must never reach storage or the console
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const DAY = 86400000;
const UNIVERSE = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/investment_system/universe/universe_codes_v1.json'), 'utf8')).map(code => code.split(':')[1].replace(/\./g, '-'));

function weekdays(from, to) { const out = []; for (let t = Date.parse(from + 'T00:00:00Z'); t <= Date.parse(to + 'T00:00:00Z'); t += DAY) { const d = new Date(t); if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); } return out; }
const SESSIONS = weekdays('2026-10-19', '2026-10-30');
function record(date) {
  const companies = {};
  IDS.forEach((id, i) => { companies[id] = { state: 'LIVE', Q: { score: 50 + i, coverage: 'READY', missing_factor_count: 0 }, G: { score: 60 - i / 2, coverage: 'READY', missing_factor_count: 0 } }; });
  return { date, version: V, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } },
    qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function forwardLedger(days) {
  return { schema_version: 1, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status: 'ACTIVE', as_of: days.at(-1) + 'T22:31:00+00:00', strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true,
    target: { portfolio_id: 'TARGET', version: 'v0' }, versions: { [V]: days.map(record), [VV]: [] }, version_status: { [V]: { state: 'ACTIVE', v_included: false, reason_codes: [] }, [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } } };
}
function history(symbol, range) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const days = { '1mo': 31, '3mo': 92, '6mo': 183, '1y': 366, '2y': 731, '5y': 1827 }[range];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  const bars = weekdays(new Date(Date.parse('2026-10-30T00:00:00Z') - days * DAY).toISOString().slice(0, 10), '2026-10-30').map((d, i) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null,
    close: i === 3 ? Number(CANARY) : Math.round(base * (1 + (i % 7) / 100) * 10000) / 10000, adjusted_close: null, volume: null, session_status: 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: NOW, bars };
}
// Stateful SYNTHETIC Google Sheet (tab title → rows of strings), shared by the contexts of one scenario.
function sheetState(tabs = {}) { return { tabs: new Map(Object.entries(tabs)), writes: [], reads: 0, bytes: 0 }; }
const col = (c) => c.charCodeAt(0) - 64;

async function open(browser, { sheet, enabled = false, width = 390 }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR' });
  const traffic = { worker: [], unexpected: [], console: 0, errors: 0 };
  await context.addInitScript(({ token, scope, id, enabled }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: 'ko-KR', source_language: 'all' }));
    localStorage.setItem('investment.web.v1.unified-sheet-source', id);
    localStorage.setItem('investment.web.v1.private-history-origin', 'https://private-investment-history.kco994553.workers.dev');
    if (enabled) localStorage.setItem('investment.web.v1.price-store-enabled', '1');
    window.google = { accounts: { oauth2: { initTokenClient(config) { return { requestAccessToken() { config.callback({ access_token: token, expires_in: 3600, scope, token_type: 'Bearer' }); } }; }, revoke(_t, done) { done({}); } } } };
  }, { token: TOKEN, scope: SCOPE, id: SHEET, enabled });
  await routeEmptyPublicScreens(context);
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === new URL(BASE).origin) {
      if (url.pathname.endsWith('/app-config.js')) {
        await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: true, privateHistoryWorkerOrigin: WORKER, virtualTradingRequestSpacingMs: 0, universeCodeCatalogURL: 'universe-codes.json' }) + ');' });
        return;
      }
      if (url.pathname.endsWith('/forward-validation-ledger.json')) { await route.fulfill({ contentType: 'application/json', body: JSON.stringify(forwardLedger(SESSIONS)) }); return; }
      return route.fallback();
    }
    if (url.origin === WORKER) {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      const symbol = url.searchParams.get('symbol'), range = url.searchParams.get('range');
      traffic.worker.push({ symbol, range, auth: request.headers().authorization === 'Bearer ' + TOKEN });
      await route.fulfill({ status: 200, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(history(symbol, range)) });
      return;
    }
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST, PUT' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      const reply = async (body, status = 200) => { const text = JSON.stringify(body); sheet.bytes += text.length; await route.fulfill({ status, headers: cors, contentType: 'application/json', body: text }); };
      const p = decodeURIComponent(url.pathname).replace('/v4/spreadsheets/' + SHEET, ''), method = request.method();
      if (method === 'GET' && p === '' && url.searchParams.get('fields') === 'sheets(properties(title))') { await reply({ sheets: [...sheet.tabs.keys()].map((title) => ({ properties: { title } })) }); return; }
      if (method === 'GET' && p === '' && url.searchParams.get('fields') === 'sheets(properties(title,sheetId))') { await reply({ sheets: [...sheet.tabs.keys()].map((title, i) => ({ properties: { title, sheetId: i } })) }); return; }
      if (method === 'POST' && p === ':batchUpdate') { const body = JSON.parse(request.postData()); for (const r of body.requests) { sheet.writes.push('ADD ' + r.addSheet.properties.title); sheet.tabs.set(r.addSheet.properties.title, []); } await reply({ replies: [] }); return; }
      const m = /^\/values\/'([^']+)'!([A-Z])(\d+)(?::([A-Z])(\d+))?(:append)?$/.exec(p), rows = m && sheet.tabs.get(m[1]);
      if (m && rows && m[6] && method === 'POST') { const values = JSON.parse(request.postData()).values; sheet.writes.push('APPEND ' + m[1] + ' ' + values.length); for (const r of values) rows.push(r); await reply({ updates: {} }); return; }
      if (m && rows && method === 'GET') { sheet.reads++; const values = rows.slice(+m[3] - 1, +m[5]).map((r) => r.slice(col(m[2]) - 1, col(m[4]))); await reply(values.length ? { range: m[1], values } : { range: m[1] }); return; }
      await reply({ error: { code: 400 } }, 400);
      return;
    }
    traffic.unexpected.push(url.origin);
    await route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  page.on('pageerror', (e) => { traffic.errors++; console.log('pageerror ' + String(e.message).slice(0, 200)); });
  page.on('console', (m) => { if (m.text().includes(CANARY) || m.text().includes(TOKEN)) traffic.console++; });
  await page.clock.install({ time: new Date(NOW) });
  await page.goto(BASE + '#home');
  await page.locator('[data-report-link="mock"]').waitFor();
  return { context, page, traffic };
}
// Google sheet use is on in the device settings (as after the first-setup sign-in), so Settings keeps the session.
async function login(page) {
  assert.equal(await page.evaluate(async (id) => {
    await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: id, range: "'Quotes'!A1:C22" });
    const s = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId); s.setEnabled(true); s.login(); return s.state().connected; }, SHEET), true);
  await page.evaluate(() => { location.hash = 'settings'; });
  await page.locator('[data-price-store]').waitFor();
}
async function storageClean(page) {
  return page.evaluate(({ canary }) => {
    const keys = Object.keys(localStorage), values = [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n');
    return !values.includes(canary) && !/"closes"|Prices_D|"close"/.test(values) && sessionStorage.length === 0 && keys.filter((k) => k.includes('price-store')).every((k) => localStorage.getItem(k) === '1');
  }, { canary: CANARY });
}
const lastLine = (page) => page.locator('[data-price-store-last]').textContent();
async function waitFor(page, selector, timeout = 30000) {
  try { await page.locator(selector).first().waitFor({ timeout }); }
  catch (e) { const s = await page.evaluate(() => JSON.stringify({ hash: location.hash, company: document.querySelector('[data-price-store-company]')?.outerHTML || null, runner: document.querySelector('[data-report-inputs]')?.getAttribute('data-runner-state') || null, summary: (document.querySelector('[data-runner-summary]')?.textContent || '').slice(0, 300) })); throw new Error('WAIT_TIMEOUT ' + selector + ' ' + s); }
}
// Waits until the last sync line names the run; on timeout the error carries the store status (codes and counts only).
async function waitSync(page, kind) {
  try { await page.waitForFunction((k) => (document.querySelector('[data-price-store-last]')?.textContent || '').includes(k), kind, { timeout: kind === 'UNIVERSE504' ? 180000 : 60000 }); }
  catch (e) { const s = await page.evaluate(() => { const x = PriceStore.status(); return JSON.stringify({ state: x.state, fetch: x.fetch, reason_codes: x.reason_codes, busy: x.busy, progress: x.progress, last: x.last_sync, hash: location.hash }); }); throw new Error('SYNC_TIMEOUT ' + kind + ' ' + s); }
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 400)); } };
  try {
    const sheet = sheetState({ Quotes: [['code', 'price', 'tradetime']], Example_Prices_D: [['do', 'not', 'touch']] });
    await check('OFF until the click; the click creates Prices_D / Prices_M; app open stores the core daily bars (5y)', async () => {
      const { context, page, traffic } = await open(browser, { sheet });
      try {
        await login(page);
        await page.locator('[data-price-store][data-price-store-state="OFF"]').waitFor();
        await page.waitForTimeout(300);
        assert.equal(traffic.worker.length, 0, 'no Worker request while OFF');
        assert.equal(sheet.writes.length, 0);
        await page.locator('[data-price-store-action="enable"]').click();
        await waitSync(page, 'CORE');
        assert.deepEqual(sheet.tabs.get('Prices_D')[0], HEAD);
        assert.deepEqual(sheet.tabs.get('Prices_M'), [HEAD]);
        assert.deepEqual(sheet.tabs.get('Example_Prices_D'), [['do', 'not', 'touch']]);
        assert.ok(sheet.writes.every((w) => /^(ADD|APPEND) Prices_[DM]\b/.test(w)), sheet.writes.join(','));
        const symbols = traffic.worker.map((w) => w.symbol);
        for (const s of ['SPY', 'KRW=X', 'NVDA', 'ASML', '042700.KS', '8035.T']) assert.ok(symbols.includes(s), s);
        assert.ok(traffic.worker.every((w) => w.range === '5y' && w.auth), 'first run: 5y once per symbol');
        assert.equal(new Set(symbols).size, symbols.length);
        const daily = sheet.tabs.get('Prices_D').slice(1);
        assert.ok(daily.length > symbols.length * 1200, String(daily.length));
        assert.ok(daily.every((r) => r.length === 5 && typeof r[2] === 'string' && r[3] === 'YAHOO'));
        const status = await page.locator('[data-price-store-status]').textContent();
        assert.ok(status.includes('Prices_D ' + daily.length), status);
        assert.ok(!status.includes(CANARY) && !(await lastLine(page)).includes(CANARY));
        assert.ok(await storageClean(page), 'a close reached device storage');
        assert.equal(traffic.console, 0); assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('reload: nothing stored is fetched again; company screen and Universe504 use stored rows; runner READY with no Worker request', async () => {
      const { context, page, traffic } = await open(browser, { sheet, enabled: true });
      try {
        const rows = sheet.tabs.get('Prices_D').length;
        await login(page);
        await waitSync(page, 'CORE');
        assert.equal(traffic.worker.length, 0, 'every core symbol is current in the sheet');
        assert.equal(sheet.tabs.get('Prices_D').length, rows, 'no row appended twice');
        await page.evaluate(() => { location.hash = 'company/nvda'; });
        const company = page.locator('[data-price-store-company]');
        await waitFor(page, '[data-price-store-company="READY"]');
        assert.ok(+(await company.getAttribute('data-month-ends')) >= 59);
        await page.evaluate(() => { location.hash = 'company/NYSE:MMM'; });
        await waitFor(page, '[data-price-store-company="READY"]');
        assert.deepEqual(traffic.worker.map(({ symbol, range }) => [symbol, range]), [['MMM', '5y']], 'newly approved MMM is fetched once');
        assert.ok(+(await page.locator('[data-price-store-company]').getAttribute('data-month-ends')) >= 59);
        const stored = new Set([...sheet.tabs.get('Prices_D').slice(1), ...sheet.tabs.get('Prices_M').slice(1)].map(row => row[0]));
        const missing = UNIVERSE.filter(symbol => !stored.has(symbol));
        const beforeUniverse = traffic.worker.length;
        await page.evaluate(() => { location.hash = 'settings'; });
        await page.locator('[data-price-store-action="universe"]:not([disabled])').click();
        await waitSync(page, 'UNIVERSE504');
        const line = await lastLine(page);
        const notAllowed = await page.evaluate(() => PriceStore.status().last_sync.not_allowed);
        assert.equal(notAllowed, 0, line);
        assert.ok(!line.includes('WORKER_ALLOWLIST'), line);
        const fetched = traffic.worker.slice(beforeUniverse);
        assert.deepEqual(fetched.map(request => request.symbol).sort(), missing.sort(), 'each missing Universe symbol is fetched once; existing daily and monthly rows are reused');
        assert.ok(fetched.every(request => request.range === '5y' && request.auth));
        const monthlySymbols = new Set(sheet.tabs.get('Prices_M').slice(1).map(row => row[0]));
        for (const symbol of ['AAPL', 'BRK-B', 'BF-B', 'MMM']) assert.ok(monthlySymbols.has(symbol), symbol);
        const afterUniverse = traffic.worker.length;
        await page.locator('[data-price-store-action="universe"]:not([disabled])').click();
        await page.waitForFunction(() => PriceStore.status().busy === null);
        assert.equal(traffic.worker.length, afterUniverse, 'a repeat requests no stored month-end series');
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await waitFor(page, '[data-report-inputs][data-runner-state="READY"]', 60000);
        assert.equal(await page.locator('[data-report-section="3"] tbody tr').count(), 19);
        assert.equal(traffic.worker.length, afterUniverse, 'the runner read the store and needed no new Worker request');
        assert.equal(sheet.tabs.get('Prices_D').length, rows);
        assert.ok(await storageClean(page), 'a close reached device storage');
        assert.equal(traffic.console, 0); assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('a different Prices_D header is never written (SHEET_HEADER_MISMATCH)', async () => {
      const bad = sheetState({ Prices_D: [['symbol', 'date', 'interval', 'close', 'source', 'fetched_at'], ['SPY', '2026-10-01', '1d', '1']] });
      const { context, page, traffic } = await open(browser, { sheet: bad });
      try {
        await login(page);
        await page.locator('[data-price-store-action="enable"]').click();
        await page.locator('[data-price-store-note]', { hasText: 'SHEET_HEADER_MISMATCH' }).waitFor();
        assert.deepEqual(bad.writes, []);
        assert.equal(bad.tabs.has('Prices_M'), false);
        assert.equal(traffic.worker.length, 0);
        assert.equal(await page.evaluate(() => localStorage.getItem('investment.web.v1.price-store-enabled')), null);
        assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('size and speed: synthetic full store (504 × 60 month-ends + 40 × 1260 daily) read and parsed', async () => {
      const tabs = { Prices_D: [HEAD], Prices_M: [HEAD] };
      const at = '2026-10-13T00:00:00Z', days = weekdays('2021-10-13', '2026-10-12').slice(-1260);
      for (let s = 0; s < 40; s++) { const sym = 'S' + String(s).padStart(3, '0'); for (let i = 0; i < days.length; i++) tabs.Prices_D.push([sym, days[i], String(100 + s + (i % 97) / 7), 'YAHOO', at]); }
      for (let s = 0; s < 504; s++) { const sym = 'U' + String(s).padStart(3, '0'); for (let i = 0; i < 60; i++) { const y = 2021 + Math.floor((9 + i) / 12), m = (9 + i) % 12 + 1; tabs.Prices_M.push([sym, y + '-' + String(m).padStart(2, '0') + '-28', String(50 + s / 3 + i / 11), 'YAHOO', at]); } }
      const big = sheetState(tabs);
      const { context, page, traffic } = await open(browser, { sheet: big, enabled: true });
      try {
        await login(page);
        const ms = await page.evaluate(async () => { const t = performance.now(); await PriceStore.dailyCloses('S000', null, { fetch: false }); const t1 = performance.now(); await PriceStore.monthEndCloses('U000', { fetch: false }); return { daily: t1 - t, monthly: performance.now() - t1 }; });
        const status = await page.evaluate(() => PriceStore.status());
        assert.ok(status.tabs.Prices_D.rows >= 40 * 1260, 'app open may append the core symbols meanwhile'); assert.equal(status.tabs.Prices_M.rows, 504 * 60);
        const parse = await page.evaluate(({ head }) => {
          const daily = [head], monthly = [head];
          for (let s = 0; s < 40; s++) for (let i = 0; i < 1260; i++) daily.push(['S' + s, '2022-01-03', String(100 + i / 7)]);
          for (let s = 0; s < 504; s++) for (let i = 0; i < 60; i++) monthly.push(['U' + s, (2021 + Math.floor(i / 12)) + '-' + String(i % 12 + 1).padStart(2, '0') + '-28', String(50 + i / 11)]);
          const text = [JSON.stringify({ values: daily }), JSON.stringify({ values: monthly })], t0 = performance.now();
          const values = text.map((x) => JSON.parse(x).values), t1 = performance.now();
          const d = PriceStore.parseTab(values[0], '1d'), m = PriceStore.parseTab(values[1], '1mo'); PriceStore.indexRows(d.rows, '1d'); PriceStore.indexRows(m.rows, '1mo');
          return { json_ms: t1 - t0, parse_index_ms: performance.now() - t1, bytes: text[0].length + text[1].length };
        }, { head: HEAD });
        console.log('PERF full store end-to-end load (local mock, ' + big.reads + ' value reads, ' + Math.round(big.bytes / 1024) + ' KiB): Prices_D ' + ms.daily.toFixed(0) + ' ms, Prices_M (on first month-end use) ' + ms.monthly.toFixed(0) + ' ms; JSON.parse ' + parse.json_ms.toFixed(0) + ' ms + parse/index ' + parse.parse_index_ms.toFixed(0) + ' ms for ' + Math.round(parse.bytes / 1024) + ' KiB (A:C)');
        assert.ok(ms.daily + ms.monthly < 20000);
        assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
