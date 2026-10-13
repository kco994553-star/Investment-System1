'use strict';
// S17 rehearsal (리허설 · 기록 없음), D-5 basis labels and the device V history on the built site, at 390 and 1440.
// Every request is intercepted: same-origin files come from the local build (public screens empty, synthetic price-free
// valuation inputs and forward ledger), the private history Worker is a synthetic 2y mock, anything else is aborted and
// counted. Checks: before 2026-10-19 the report stays NOT_STARTED with no Worker request until '리허설 실행'; the rehearsal
// shows judgements + D-5 basis per company (sector ETF, S&P 500 fallback when XLI is rejected, basis N/A below 273
// closes) with a distinct badge; only V numbers reach storage (no price, ledger or sheet write); back to 기록 모드.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'rehearsal', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
// Synthetic public classification (test fixture): D-22 → msft XLK, nvda SMH, asml XLI (the Worker rejects XLI here).
const CLASSIFICATION = JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname, '../tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const CANARY = '777.0731'; // synthetic close carried by one bar of every series: must never reach storage or the console

function weekdays(from, to) { const out = []; for (let d = new Date(from + 'T00:00:00Z'); d <= new Date(to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1)) if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); return out; }
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
// Synthetic 2y daily history: ~290 sessions, NVDA only 100 (D-5 basis N/A), MSFT falls 5 % a day over its last 8 sessions.
function history(symbol, range, last) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  let days = weekdays('2025-09-01', last);
  if (symbol === 'NVDA') days = days.slice(-100);
  const n = days.length;
  const bars = days.map((d, i) => {
    let close = Math.round(base * (1 + ((i * 7 + symbol.length) % 11) / 100) * 10000) / 10000;
    if (symbol === 'MSFT') close = Math.round(close * 0.95 ** Math.max(0, i - (n - 9)) * 10000) / 10000;
    if (i === 3) close = Number(CANARY);
    return { timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null, close, adjusted_close: null, volume: null, session_status: 'COMPLETE' };
  });
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: last + 'T23:00:00Z', bars };
}
const COMPONENTS = ['operating_cash_flow', 'capital_expenditure', 'long_term_debt_issuance', 'long_term_debt_repayment', 'net_short_term_borrowing', 'diluted_shares'];
function valuationInputs() {
  const at = '2026-10-14T12:00:00Z', h = (c) => c.repeat(64), companies = {};
  for (const id of IDS) companies[id] = { state: 'NOT_AVAILABLE', source_hashes: {}, fcfe: { state: 'NOT_AVAILABLE', reason_codes: ['SEC_INPUT_NOT_AVAILABLE'], fcfe_per_share: null, taxonomy: null, currency: null, fiscal_period_start: null, fiscal_period_end: null, accn: null, form: null, components: Object.fromEntries(COMPONENTS.map((k) => [k, null])) }, v_inputs: { state: 'NOT_AVAILABLE', reason_codes: ['SEC_INPUT_NOT_AVAILABLE'], eps: null, revenue: null, revenue_prev: null, revenue_cagr_3y: null, currency: null } };
  const c = (concept, value) => ({ concepts: [concept], value, assumed_zero: false, reason: null });
  companies.nvda = { state: 'LIVE', source_hashes: { companyfacts: h('a'), submissions: h('b') }, fcfe: { state: 'LIVE', reason_codes: [], fcfe_per_share: 8.25, taxonomy: 'us-gaap', currency: 'USD', fiscal_period_start: '2025-01-01', fiscal_period_end: '2025-12-31', accn: '000104581026000001', form: '10-K',
    components: { operating_cash_flow: c('NetCashProvidedByUsedInOperatingActivities', 1000), capital_expenditure: c('PaymentsToAcquirePropertyPlantAndEquipment', 300), long_term_debt_issuance: c('ProceedsFromIssuanceOfLongTermDebt', 200), long_term_debt_repayment: c('RepaymentsOfLongTermDebt', 50), net_short_term_borrowing: c('ProceedsFromRepaymentsOfShortTermDebt', -25), diluted_shares: c('WeightedAverageNumberOfDilutedSharesOutstanding', 100) } },
    v_inputs: { state: 'LIVE', reason_codes: [], eps: 4, revenue: 5000, revenue_prev: 4900, revenue_cagr_3y: 0.08, currency: 'USD' } };
  return { schema_version: 1, kind: 'SEC_VALUATION_INPUTS', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_COMPANYFACTS', sha256: h('a'), acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: h('b'), acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400,
    data: { companies, method_status: 'PROVISIONAL_UNCALIBRATED', availability_basis: 'OBSERVED_CAPTURE_ONLY', fcfe_definition: 'fcfe/1.1', share_basis: 'WEIGHTED_AVERAGE_DILUTED' } };
}

async function open(browser, { now, last, width }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR', permissions: ['clipboard-read', 'clipboard-write'] });
  const traffic = { worker: [], unexpected: [], writes: 0, console: 0, errors: 0 };
  await context.addInitScript(({ token, scope }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: 'ko-KR', source_language: 'all' }));
    localStorage.setItem('investment.web.v1.unified-sheet-source', 'synthetic_existing_sheet_fixture');
    localStorage.setItem('investment.web.v1.private-history-origin', 'https://private-investment-history.kco994553.workers.dev');
    window.google = { accounts: { oauth2: { initTokenClient(config) { return { requestAccessToken() { config.callback({ access_token: token, expires_in: 3600, scope, token_type: 'Bearer' }); } }; }, revoke(_t, done) { done({}); } } } };
  }, { token: TOKEN, scope: SCOPE });
  await routeEmptyPublicScreens(context);
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (request.method() !== 'GET' && request.method() !== 'OPTIONS') traffic.writes++;
    if (url.origin === new URL(BASE).origin) {
      if (url.pathname.endsWith('/app-config.js')) {
        await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: true, privateHistoryWorkerOrigin: WORKER, virtualTradingRequestSpacingMs: 0 }) + ');' });
        return;
      }
      if (url.pathname.endsWith('/sec-valuation-inputs.json')) { await route.fulfill({ contentType: 'application/json', body: JSON.stringify(valuationInputs()) }); return; }
      if (url.pathname.endsWith('/company-classification.json')) { await route.fulfill({ contentType: 'application/json', body: JSON.stringify(CLASSIFICATION) }); return; }
      if (url.pathname.endsWith('/forward-validation-ledger.json')) {
        if (last < '2026-10-19') { await route.fulfill({ status: 404, body: '' }); return; }
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(forwardLedger(weekdays('2026-10-19', last))) });
        return;
      }
      return route.fallback();
    }
    if (url.origin === WORKER) {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      const symbol = url.searchParams.get('symbol'), range = url.searchParams.get('range');
      traffic.worker.push({ symbol, range, auth: request.headers().authorization === 'Bearer ' + TOKEN });
      const rejected = symbol === 'XLI';
      await route.fulfill({ status: rejected ? 400 : 200, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(rejected ? { error: { code: 'REQUEST_INVALID' } } : history(symbol, range, last)) });
      return;
    }
    // The ledger sheet card (VirtualLedgerSheets) reads the connected sheet's tab titles: a sheet without Virtual* tabs.
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
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
// Signed-in session; the client allowlist is replaced by the same request shape (SPY/ETF/FX allowlisted after deploy).
async function signIn(page) {
  await page.evaluate((token) => {
    const real = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId);
    real.setEnabled(true); real.login();
    const session = { ...real, async fetchHistory(origin, symbol, range, options = {}) {
      const r = await fetch(origin + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: options.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body && body.error ? body.error.code : 'YAHOO_UNAVAILABLE'); return body; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
    // Today's public Q·G screen (empty in this build) → synthetic rows, so the rehearsal has judgements to show.
    window.LeaderboardScreen = { ...LeaderboardScreen, rowsFor: (ids) => ids.map((c, i) => ({ company_id: c.company_id, ticker: c.ticker, name: c.name, q: 50 + (i % 9), g: 55 + (i % 5), partial: false, qg_total: null, next_window: null })) };
  }, TOKEN);
}
async function storageOnlyV(page) {
  return page.evaluate(({ canary }) => {
    const values = [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n');
    const raw = localStorage.getItem('investment.web.v1.virtual-trading-v-scores');
    let vOk = true;
    if (raw) { const v = JSON.parse(raw); vOk = (v.schema === 'virtual-trading-v-scores/1' || v.schema === 'virtual-trading-v-scores/2') && Object.entries(v.scores).every(([d, row]) => /^\d{4}-\d{2}-\d{2}$/.test(d) && Object.values(row).every((x) => typeof x === 'number' && x >= 0 && x <= 100 && Math.round(x * 100) / 100 === x)); }
    return { clean: !values.includes(canary) && !values.includes('private-history/1') && !/"closes"|"trades"|"positions"|EXEC_|RECHECK_/.test(values), vOk, raw };
  }, { canary: CANARY });
}
const noWonAmount = (text) => (text.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length === 0;

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 300)); } };
  try {
    for (const width of [390, 1440]) {
      await check('rehearsal before 2026-10-19: NOT_STARTED until clicked, labelled, D-5 basis, V only stored (' + width + ')', async () => {
        const { context, page, traffic } = await open(browser, { now: '2026-10-15T03:00:00Z', last: '2026-10-14', width });
        try {
          await signIn(page);
          await page.evaluate(() => { location.hash = 'report/mock'; });
          await page.locator('[data-report-inputs][data-runner-state="NOT_STARTED"]').waitFor();
          assert.equal((await page.locator('[data-report-mode]').textContent()).trim(), '기록 모드');
          assert.ok((await page.locator('[data-report-not-started]').textContent()).includes('2026-10-19 전'));
          assert.equal((await page.locator('[data-rehearsal-run]').textContent()).trim(), '리허설 실행');
          assert.ok((await page.locator('[data-v-progress]').textContent()).includes('V 기록 0/20일'));
          await page.waitForTimeout(300);
          assert.equal(traffic.worker.length, 0, 'no Worker request before the rehearsal is asked for');
          await page.locator('[data-rehearsal-run]').click();
          await page.locator('[data-report-mode="REHEARSAL"]').waitFor();
          await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
          assert.equal((await page.locator('[data-report-mode]').textContent()).trim(), '리허설 · 기록 없음');
          assert.ok((await page.locator('[data-rehearsal-note]').textContent()).includes('어떤 장부·시트에도 기록하지 않음'));
          assert.ok((await page.locator('[data-report-section="10"] h2').textContent()).includes('리허설 · 기록 없음'));
          const bg = await page.locator('[data-report-mode="REHEARSAL"]').evaluate((n) => getComputedStyle(n).backgroundColor);
          assert.equal(bg, 'rgb(236, 228, 247)', 'distinct rehearsal colour');
          assert.equal(await page.locator('[data-report-section="3"] tbody tr').count(), 19);
          assert.equal(await page.locator('[data-basis="msft"]').getAttribute('data-basis-benchmark'), 'XLK');
          assert.equal(await page.locator('[data-basis="msft"]').getAttribute('data-basis-state'), 'ABNORMAL');
          assert.ok((await page.locator('[data-report-section="3"]').textContent()).includes('▼위험재검토'));
          assert.equal(await page.locator('[data-basis="nvda"]').getAttribute('data-basis-state'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-basis="nvda"]').textContent()).includes('HISTORY_INSUFFICIENT 100/273'));
          assert.equal(await page.locator('[data-basis="asml"]').getAttribute('data-basis-benchmark'), 'SP500');
          assert.ok((await page.locator('[data-basis="asml"]').textContent()).includes('S&P 500 (XLI 없음 → 대체)'));
          assert.equal(await page.locator('[data-source-symbol="XLI"][data-source-code="REQUEST_INVALID"]').count(), 1);
          // Decision 2026-10-13 §13-1: an eligible anchor plus >=50% computed weight can record partial V; prices stay in RAM.
          assert.equal(await page.locator('[data-v-capture="RECORDED"]').count(), 1);
          assert.ok((await page.locator('[data-v-capture]').textContent()).includes('오늘 V 기록: 2026-10-14 · 1개 기업'));
          assert.ok(noWonAmount(await page.locator('#daily-report').textContent()), 'won amount visible while hidden');
          await page.locator('[data-export-template]').click();
          await page.waitForFunction(() => /복사|표시/.test(document.querySelector('[data-report-status]')?.textContent || ''));
          const text = await page.evaluate(async () => { try { return await navigator.clipboard.readText(); } catch (_) { return document.querySelector('[data-export-fallback]')?.value || ''; } });
          assert.ok(text.includes('리허설 · 기록 없음: 오늘 데이터로 규칙만'), 'template labelled as rehearsal');
          assert.ok(text.includes('업종 기준(D-5): '));
          const store = await storageOnlyV(page);
          assert.ok(store.clean, 'price, ledger or judgement reached storage');
          assert.ok(store.vOk && store.raw, 'approved partial V is stored without prices or ledger');
          assert.ok(traffic.worker.every((w) => w.auth && w.range === '2y'));
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'horizontal scroll ' + await page.evaluate(() => [...document.querySelectorAll('body *')].filter((n) => n.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map((n) => n.tagName + '.' + n.className + ':' + (n.textContent || '').slice(0, 40)).join(' | ')));
          await page.locator('[data-recording-mode]').click();
          await page.locator('[data-report-inputs][data-runner-state="NOT_STARTED"]').waitFor();
          assert.equal((await page.locator('[data-report-mode]').textContent()).trim(), '기록 모드');
          assert.equal(await page.locator('[data-rehearsal-run]').count(), 1);
          assert.equal(traffic.writes, 0, 'no write request (sheet or otherwise)');
          assert.equal(traffic.console, 0);
          assert.deepEqual(traffic.unexpected, []);
          assert.equal(traffic.errors, 0);
        } finally { await context.close(); }
      });
    }
    await check('recording mode after the start date shows basis per company; rehearsal toggle reuses RAM history', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', last: '2026-10-30', width: 390 });
      try {
        await signIn(page);
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        assert.equal((await page.locator('[data-report-mode]').textContent()).trim(), '기록 모드');
        assert.equal(await page.locator('[data-basis="msft"]').getAttribute('data-basis-benchmark'), 'XLK');
        assert.equal(await page.locator('[data-basis="asml"]').getAttribute('data-basis-fallback'), '1');
        assert.equal(await page.locator('[data-basis="nvda"]').getAttribute('data-v-slope'), 'BASIS_NOT_AVAILABLE');
        const before = traffic.worker.length;
        await page.locator('[data-rehearsal-run]').click();
        await page.locator('[data-report-mode="REHEARSAL"]').waitFor();
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        assert.ok((await page.locator('[data-rehearsal-note]').textContent()).includes('2026-10-26부터 최근 5거래일'));
        assert.deepEqual(traffic.worker.slice(before).map((w) => w.symbol), ['XLI'], 'rehearsal reuses the RAM history; only the rejected symbol is asked again');
        await page.locator('[data-recording-mode]').click();
        await page.locator('[data-report-mode="RECORDING"]').waitFor();
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        const store = await storageOnlyV(page);
        assert.ok(store.clean && store.vOk);
        assert.equal(traffic.writes, 0);
        assert.equal(traffic.console, 0);
        assert.deepEqual(traffic.unexpected, []);
        assert.equal(traffic.errors, 0);
      } finally { await context.close(); }
    });
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
