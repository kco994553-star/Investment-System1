'use strict';
// S17 virtual ledger runner on the built site. Every request is intercepted: same-origin files are served by the local
// build (public screens empty, synthetic price-free forward ledger), the private history Worker is a synthetic mock and
// anything else is aborted and counted. Checks: NOT_STARTED before 2026-10-19 with no Worker request; after the start
// date the report shows ledger rows from synthetic history with amounts hidden by default; a missing FX close shows
// EXEC_FX_MISSING; a symbol the client/Worker rejects degrades to NOT_AVAILABLE with its code; nothing is stored or logged.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'runner', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const TARGET_SYMBOLS = ['ASML', 'LRCX', 'KLAC', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MSFT', 'GOOGL', 'AMZN', 'RTX', 'SYK', 'ETN', 'HUBB', 'GEV', 'ROK', '042700.KS', '8035.T'];
const CANARY = '777.0731'; // synthetic close carried by every bar: must never reach storage or the console

function weekdays(from, to) { const out = []; for (let d = new Date(from + 'T00:00:00Z'); d <= new Date(to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1)) if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); return out; }
const SESSIONS = weekdays('2026-10-19', '2026-10-30');
function record(date) {
  const companies = {};
  IDS.forEach((id, i) => { companies[id] = { state: 'LIVE', Q: { score: 50 + i, coverage: 'READY', missing_factor_count: 0 }, G: { score: 60 - i / 2, coverage: 'READY', missing_factor_count: 0 } }; });
  return { date, version: V, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } },
    qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function forwardLedger(days) {
  const rows = days.map(record), status = 'ACTIVE';
  return { schema_version: 1, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status, as_of: (days.at(-1) || '2026-10-19') + 'T22:31:00+00:00', strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true,
    target: { portfolio_id: 'TARGET', version: 'v0' }, versions: { [V]: rows, [VV]: [] }, version_status: { [V]: { state: status, v_included: false, reason_codes: [] }, [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } } };
}
function history(symbol, range) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  const bars = weekdays('2026-09-01', '2026-10-30').map((d, i) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null,
    close: symbol === 'KRW=X' && d === '2026-10-30' ? null : i === 3 ? Number(CANARY) : Math.round(base * (1 + (i % 7) / 100) * 10000) / 10000, adjusted_close: null, volume: null, session_status: 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: '2026-10-30T22:00:00Z', bars };
}

async function open(browser, { now, width = 390, workerAcceptsBenchmarks }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR' });
  const traffic = { worker: [], sheets: [], unexpected: [], console: 0, errors: 0 };
  await context.addInitScript(({ token, scope }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: 'ko-KR', source_language: 'all' }));
    localStorage.setItem('investment.web.v1.unified-sheet-source', 'synthetic_existing_sheet_fixture');
    localStorage.setItem('investment.web.v1.private-history-origin', 'https://private-investment-history.kco994553.workers.dev');
    // Google Identity Services stand-in: no script is loaded from Google, the token stays in page memory.
    window.google = { accounts: { oauth2: { initTokenClient(config) { return { requestAccessToken() { config.callback({ access_token: token, expires_in: 3600, scope, token_type: 'Bearer' }); } }; }, revoke(_t, done) { done({}); } } } };
  }, { token: TOKEN, scope: SCOPE });
  await routeEmptyPublicScreens(context);
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === new URL(BASE).origin) {
      if (url.pathname.endsWith('/app-config.js')) {
        await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: true, privateHistoryWorkerOrigin: WORKER, virtualTradingRequestSpacingMs: 0 }) + ');' });
        return;
      }
      if (url.pathname.endsWith('/forward-validation-ledger.json')) {
        const today = new Date(now).toISOString().slice(0, 10);
        if (today < '2026-10-19') { await route.fulfill({ status: 404, body: '' }); return; }
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(forwardLedger(SESSIONS)) });
        return;
      }
      return route.fallback();
    }
    if (url.origin === WORKER) {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      const symbol = url.searchParams.get('symbol'), range = url.searchParams.get('range');
      traffic.worker.push({ symbol, range, auth: request.headers().authorization === 'Bearer ' + TOKEN, get: request.method() === 'GET' });
      const allowed = TARGET_SYMBOLS.includes(symbol) || workerAcceptsBenchmarks;
      await route.fulfill({ status: allowed ? 200 : 400, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(allowed ? history(symbol, range) : { error: { code: 'REQUEST_INVALID' } }) });
      return;
    }
    // The ledger sheet card (VirtualLedgerSheets) reads the connected sheet's tab titles: a sheet without Virtual* tabs.
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      traffic.sheets.push(request.method() + ' ' + decodeURIComponent(url.pathname));
      if (request.method() === 'GET' && url.searchParams.get('fields') === 'sheets(properties(title))') { await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ sheets: [{ properties: { title: 'Quotes' } }] }) }); return; }
    }
    traffic.unexpected.push(url.origin);
    await route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', (e) => { traffic.errors++; console.log('pageerror ' + String(e.message).slice(0, 200)); });
  page.on('console', (m) => { if (m.text().includes(CANARY) || m.text().includes(TOKEN)) traffic.console++; });
  await page.clock.install({ time: new Date(now) });
  await page.goto(BASE + '#home');
  await page.locator('[data-report-link="mock"]').waitFor();
  return { context, page, traffic };
}
async function login(page) {
  assert.equal(await page.evaluate(() => { const s = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId); s.setEnabled(true); s.login(); return s.state().connected; }), true);
}
// After the Worker benchmark/FX change is deployed the client allowlist includes SPY, ETFs and FX. Until then this test
// simulates it with the same session: same token, same Worker origin and request shape, only the client allowlist is skipped.
async function postDeployClient(page) {
  await page.evaluate(() => {
    const real = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId);
    const token = window.__runnerToken;
    const session = { ...real, async fetchHistory(origin, symbol, range, options = {}) {
      const r = await fetch(origin + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: options.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body && body.error ? body.error.code : 'YAHOO_UNAVAILABLE'); return body; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
  });
}
async function storageClean(page) {
  return page.evaluate(({ canary }) => {
    const values = [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n');
    return !values.includes(canary) && !values.includes('private-history/1') && !/"closes"|EXEC_FX_MISSING/.test(values);
  }, { canary: CANARY });
}
const noWonAmount = (text) => (text.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length === 0;

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 300)); } };
  try {
    await check('virtual runner not started before 2026-10-19', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-15T03:00:00Z', workerAcceptsBenchmarks: true });
      try {
        await login(page);
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="NOT_STARTED"]').waitFor();
        assert.ok((await page.locator('[data-report-not-started]').textContent()).includes('2026-10-19 전'));
        await page.waitForTimeout(300);
        assert.equal(traffic.worker.length, 0);
        assert.deepEqual(traffic.unexpected, []);
        assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('virtual runner ledger rows, hidden amounts, EXEC_FX_MISSING (390)', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', workerAcceptsBenchmarks: true });
      try {
        await login(page);
        await page.evaluate((t) => { window.__runnerToken = t; }, TOKEN);
        await postDeployClient(page);
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        assert.equal(await page.locator('[data-report-not-started]').count(), 0);
        assert.equal(await page.locator('[data-report-section="3"] tbody tr').count(), 19);
        assert.equal(await page.locator('[data-hide-amounts]').isChecked(), true);
        assert.equal((await page.locator('[data-report-summary] .big').textContent()).trim(), '●●●만원');
        assert.ok(noWonAmount(await page.locator('#daily-report').textContent()), 'won amount visible while hidden');
        assert.ok(await page.locator('[data-report-cancelled] [data-cancel-reason="EXEC_FX_MISSING"]').count() >= 1);
        assert.ok((await page.locator('[data-report-section="10"]').textContent()).includes('가상 · 실제 추천 아님'));
        assert.ok((await page.locator('[data-report-section="10"]').textContent()).includes('주문 기능은 없습니다'));
        const symbols = traffic.worker.map((w) => w.symbol);
        assert.equal(symbols[0], 'SPY');
        for (const s of ['KRW=X', 'JPYKRW=X', 'ASML', '042700.KS', '8035.T']) assert.ok(symbols.includes(s), s);
        assert.ok(traffic.worker.every((w) => w.auth && w.get && w.range === '2y'));
        // Tab switch reuses the RAM history: no new Worker request. Without the user's own target the shadow ledger is
        // NOT_AVAILABLE (decision 2026-10-11: TARGET v0 is never substituted) and the '내 목표 설정' guide is shown.
        const before = traffic.worker.length;
        await page.evaluate(() => { location.hash = 'report/real'; });
        await page.locator('[data-report-inputs][data-runner-state="NOT_AVAILABLE"]').waitFor({ timeout: 30000 });
        assert.ok((await page.locator('[data-runner-summary]').textContent()).includes('TARGET_NOT_AVAILABLE'));
        await page.locator('[data-user-target-guide][data-user-target-state="NOT_AVAILABLE"]').waitFor({ timeout: 30000 });
        assert.equal(await page.locator('[data-copy-set-a-target]').count(), 1);
        assert.equal(traffic.worker.length, before);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        assert.ok(await storageClean(page), 'price or ledger reached storage');
        assert.ok(traffic.sheets.length > 0 && traffic.sheets.every((x) => x.startsWith('GET ')), 'ledger sheet is read, never written without a click');
        assert.equal(traffic.console, 0);
        assert.deepEqual(traffic.unexpected, []);
        assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('virtual runner degrades when SPY/ETF/FX are rejected by the client or Worker', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', width: 1440, workerAcceptsBenchmarks: false });
      try {
        await login(page);
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="NOT_AVAILABLE"]').waitFor({ timeout: 30000 });
        assert.equal(await page.locator('[data-source-symbol="SPY"][data-source-code="REQUEST_INVALID"]').count(), 1);
        assert.ok((await page.locator('[data-runner-summary]').textContent()).includes('SESSIONS_NOT_AVAILABLE'));
        assert.ok((await page.locator('[data-report-not-started]').textContent()).includes('SESSIONS_NOT_AVAILABLE'));
        assert.ok(traffic.worker.every((w) => w.symbol === 'SPY'), 'no request after SPY was rejected');
        assert.deepEqual(traffic.unexpected, []);
        assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
    await check('virtual runner without Google sign-in shows AUTH_REQUIRED and calls no Worker', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', workerAcceptsBenchmarks: true });
      try {
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="NOT_AVAILABLE"]').waitFor({ timeout: 30000 });
        assert.ok((await page.locator('[data-runner-summary]').textContent()).includes('AUTH_REQUIRED'));
        assert.equal(traffic.worker.length, 0);
        assert.deepEqual(traffic.unexpected, []);
      } finally { await context.close(); }
    });
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
