'use strict';
const {displayOnlyOff}=require('./display_only_off.js');
// S17 ⑪ Track Record, ⑫ period returns and ⑬ relative-index dashboard on the built site, at 390 and 1440.
// Every request is intercepted: same-origin files from the local build (public screens empty, synthetic forward ledger),
// the private history Worker is a synthetic 2y mock (VUG rejected, one XLK bar missing), anything else is aborted and
// counted. Checks: before 2026-10-19 ⑪ shows NOT_AVAILABLE with the expected first date per window and no Worker request;
// the runner requests the ⑬ ETFs (XLK, VUG, QUAL, XLY, XLP) even without a mapped company; the chart breaks at the
// missing bar (no interpolation); period and currency-basis selectors; amounts stay hidden; no price, index or return
// reaches storage, the console or any write request; the investment report shows the shadow ledger with Set A.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const TOKEN = ['memory', 'only', 'synthetic', 'bench', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'e'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const CLASSIFICATION = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const CANARY = '777.0731'; // synthetic close carried by one bar of every series: must never reach storage or the console
const XLK_GAP = '2026-10-27';

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
// Synthetic 2y daily history; XLK has no bar on XLK_GAP.
function history(symbol, range, last) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  const days = weekdays('2025-09-01', last).filter((d) => !(symbol === 'XLK' && d === XLK_GAP));
  const bars = days.map((d, i) => {
    let close = Math.round(base * (1 + ((i * 7 + symbol.length * 3) % 13) / 100) * 10000) / 10000;
    if (i === 3) close = Number(CANARY);
    return { timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null, close, adjusted_close: null, volume: null, session_status: 'COMPLETE' };
  });
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: last + 'T23:00:00Z', bars };
}

async function open(browser, { now, last, width }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR', permissions: ['clipboard-read', 'clipboard-write'] });await displayOnlyOff(context);
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
      if (url.pathname.endsWith('/sec-valuation-inputs.json')) { await route.fulfill({ status: 404, body: '' }); return; }
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
      const rejected = symbol === 'VUG';
      await route.fulfill({ status: rejected ? 400 : 200, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(rejected ? { error: { code: 'REQUEST_INVALID' } } : history(symbol, range, last)) });
      return;
    }
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      if (request.method() === 'GET' && url.searchParams.get('fields') === 'sheets(properties(title))') { await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ sheets: [{ properties: { title: 'Quotes' } }, { properties: { title: 'VirtualMeta' } }] }) }); return; }
      // The user's own target (decision 2026-10-11: the shadow ledger never falls back to TARGET v0): one synthetic
      // USER_TARGET row in VirtualMeta (the TARGET v0 units as %, read only).
      if (request.method() === 'GET' && decodeURIComponent(url.pathname).includes("/values/'VirtualMeta'!A1:")) {
        const meta = [['recorded_at', 'ledger_id', 'kind', 'event', 'start_date', 'end_date', 'config_version', 'engine_version', 'last_recorded_session', 'inputs_sha256', 'payload'],
          ['2026-10-12T00:00:00Z', '', 'TARGET', 'USER_TARGET', '', '', '', '', '', '', JSON.stringify({ target_weights: Object.fromEntries(IDS.map((id) => [id, UNITS[id] / 100])) })]];
        await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ range: 'VirtualMeta', majorDimension: 'ROWS', values: meta }) }); return;
      }
      if (request.method() === 'GET' && decodeURIComponent(url.pathname).includes("/values/'VirtualMeta'!A")) { await route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify({ range: 'VirtualMeta', majorDimension: 'ROWS' }) }); return; }
    }
    traffic.unexpected.push(url.origin);
    await route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('pageerror', (e) => { traffic.errors++; console.log('pageerror ' + String(e.message).slice(0, 200)); });
  page.on('console', (m) => { if (m.text().includes(CANARY) || m.text().includes(TOKEN) || /\b1\d\d\.\d{4,}/.test(m.text())) traffic.console++; });
  await page.clock.install({ time: new Date(now) });
  await page.goto(BASE + '#home');
  await page.locator('[data-report-link="mock"]').waitFor();
  return { context, page, traffic };
}
// Signed-in session with the same request shape (client allowlist replaced, as in the rehearsal test).
async function signIn(page, { holdings = false } = {}) {
  await page.evaluate(async ({ token, holdings }) => {
    const real = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId);
    real.setEnabled(true); real.login();
    const session = { ...real, async fetchHistory(origin, symbol, range, options = {}) {
      const r = await fetch(origin + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: options.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body && body.error ? body.error.code : 'YAHOO_UNAVAILABLE'); return body; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
    window.LeaderboardScreen = { ...LeaderboardScreen, rowsFor: (ids) => ids.map((c, i) => ({ company_id: c.company_id, ticker: c.ticker, name: c.name, q: 50 + (i % 9), g: 55 + (i % 5), partial: false, qg_total: null, next_window: null })) };
    if (holdings) {
      // Synthetic ACTUAL snapshot (two catalog rows); readHoldings and effectiveHoldings are stubbed together.
      const catalog = await (await fetch('actual-catalog.json')).json(), rows = catalog.instruments.filter((r) => [10, 5].includes(r.row_index));
      const snapshot = { effective_at: '2026-10-16T20:00:00Z', themes: [{ holdings: rows.map((r, i) => ({ security_reference: r.security_reference, quantity: 3 + i, average_cost: 101 + i, currency: r.currency })) }] };
      window.DeviceActual = { ...DeviceActual, readHoldings: async () => snapshot, effectiveHoldings: async () => ({ source: 'SYNTHETIC', snapshot }) };
    }
  }, { token: TOKEN, holdings });
}
async function storageClean(page) {
  return page.evaluate(({ canary }) => {
    const values = [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n'), keys = Object.keys(localStorage).concat(Object.keys(sessionStorage));
    return !values.includes(canary) && !values.includes('private-history/1') && !/"closes"|"indices"|"points"|report-benchmarks|bench/i.test(values) && !keys.some((k) => /bench|index/i.test(k));
  }, { canary: CANARY });
}
const noWonAmount = (text) => (text.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length === 0;
const noOverflow = (page) => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
const sectionText = (page, n) => page.locator('[data-report-section="' + n + '"]').textContent();

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 300)); } };
  try {
    for (const width of [390, 1440]) {
      await check('before 2026-10-19: ⑪ expected first dates, ⑫⑬ NOT_AVAILABLE without requests; rehearsal draws ⑬ (' + width + ')', async () => {
        const { context, page, traffic } = await open(browser, { now: '2026-10-15T03:00:00Z', last: '2026-10-14', width });
        try {
          await signIn(page);
          await page.evaluate(() => { location.hash = 'report/mock'; });
          await page.locator('[data-report-inputs][data-runner-state="NOT_STARTED"]').waitFor();
          const rows = await page.locator('[data-track-windows] tbody tr').evaluateAll((r) => r.map((x) => [x.dataset.trackWindow, x.dataset.trackState, x.cells[2].textContent]));
          assert.deepEqual(rows.map((r) => r.slice(0, 2)), [['5', 'NOT_AVAILABLE'], ['20', 'NOT_AVAILABLE'], ['63', 'NOT_AVAILABLE']]);
          assert.ok(rows[0][2].includes('BEFORE_START_DATE') && rows[0][2].includes('첫 평가 예상 ≈ 2026-10-27'), rows[0][2]);
          assert.ok(rows[1][2].includes('≈ 2026-11-17') && rows[2][2].includes('≈ 2027-01-21'));
          assert.ok((await sectionText(page, 11)).includes('30건 미만이면 적중률을 숫자로 보이지 않습니다'));
          assert.ok((await sectionText(page, 12)).includes('NOT_AVAILABLE · 시작일 전 (BEFORE_START_DATE)'));
          assert.ok((await sectionText(page, 13)).includes('BEFORE_START_DATE'));
          assert.equal(await page.locator('[data-bench-chart]').count(), 0);
          await page.waitForTimeout(300);
          assert.equal(traffic.worker.length, 0, 'no Worker request before the rehearsal');
          await page.locator('[data-rehearsal-run]').click();
          await page.locator('[data-report-mode="REHEARSAL"]').waitFor();
          await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
          const symbols = traffic.worker.map((w) => w.symbol);
          for (const etf of ['XLK', 'VUG', 'QUAL', 'XLY', 'XLP']) assert.equal(symbols.filter((s) => s === etf).length, 1, etf + ' requested once');
          assert.ok(symbols.indexOf('QUAL') > symbols.indexOf('ROK'), 'dashboard ETFs after the companies');
          await page.locator('[data-bench-chart]').waitFor();
          // Default 20D: the rehearsal ledger (5 sessions) is shorter → NOT_AVAILABLE; indices are drawn.
          assert.equal(await page.locator('[data-bench-series-row="SET_A"]').getAttribute('data-bench-series-state'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-bench-series-row="SET_A"]').textContent()).includes('PERIOD_BEFORE_LEDGER_START'));
          assert.equal(await page.locator('[data-bench-series-row="VUG"]').getAttribute('data-bench-series-state'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-bench-series-row="VUG"]').textContent()).includes('REQUEST_INVALID'));
          assert.equal(await page.locator('[data-bench-series-row="SP500"]').getAttribute('data-bench-series-state'), 'OK');
          assert.ok(await page.locator('[data-bench-line="SP500"]').count() >= 1);
          await page.locator('[data-bench-period="SINCE_START"]').click();
          await page.locator('[data-bench-period="SINCE_START"][aria-pressed="true"]').waitFor();
          assert.equal(await page.locator('[data-bench-series-row="SET_A"]').getAttribute('data-bench-series-state'), 'OK');
          assert.ok(await page.locator('[data-bench-line="SET_A"]').count() >= 1);
          assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.dataset.benchPeriod), 'SINCE_START', 'focus kept on the period button');
          assert.ok(noWonAmount(await page.locator('#daily-report').textContent()), 'won amount visible while hidden');
          assert.ok(await noOverflow(page), 'horizontal scroll');
          assert.ok(await storageClean(page), 'price, index or return reached storage');
          assert.equal(traffic.writes, 0);
          assert.equal(traffic.console, 0);
          assert.deepEqual(traffic.unexpected, []);
          assert.equal(traffic.errors, 0);
        } finally { await context.close(); }
      });
      await check('recording after start: ⑫ periods, ⑬ gap + basis, ⑪ sample minimum, export (' + width + ')', async () => {
        const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', last: '2026-10-30', width });
        try {
          await signIn(page);
          await page.evaluate(() => { location.hash = 'report/mock'; });
          await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
          await page.locator('[data-bench-chart]').waitFor();
          const periods = await page.locator('[data-bench-periods] tbody tr').evaluateAll((r) => r.map((x) => [x.dataset.benchPeriodRow, x.dataset.benchRowState, x.textContent + ' ' + [...x.querySelectorAll('[data-bench-reason]')].map((n) => n.dataset.benchReason).join(' ')]));
          assert.deepEqual(periods.map((p) => p[0]), ['1D', '5D', '20D', '60D', '120D', '시작 이후'].map((x) => x === '시작 이후' ? 'SINCE_START' : x));
          assert.ok(periods.every((p) => p[1] === 'OK'));
          const since = periods.find((p) => p[0] === 'SINCE_START')[2];
          assert.ok(/기준 2026-10-16/.test(since) && /[+−]\d+\.\d{2}%/.test(since) && /(상회|하회|같음)/.test(since), since);
          assert.ok(periods.find((p) => p[0] === '20D')[2].includes('PERIOD_BEFORE_LEDGER_START'), '20D is longer than the ledger');
          assert.ok((await page.locator('[data-bench-basis-line]').textContent()).includes('원화 기준'));
          // ⑬ default 20D: XLK has a missing bar inside the period → its line breaks, nothing interpolated.
          assert.equal(await page.locator('[data-bench-line="XLK"]').count(), 2, 'XLK gap splits the line');
          assert.ok((await page.locator('[data-bench-series-row="XLK"]').textContent()).includes('결측 1세션(보간 없음)'));
          const tip = await page.locator('[data-bench-hover="' + XLK_GAP + '"] title').textContent();
          assert.ok(tip.includes('XLK N/A'), tip);
          await page.locator('[data-bench-basis]').selectOption('USD');
          await page.locator('[data-bench-basis-line][data-basis="USD"]').waitFor();
          assert.ok((await page.locator('[data-bench-basis-note]').textContent()).includes('달러 기준'));
          await page.locator('[data-bench-period="5D"]').click();
          await page.locator('[data-bench-period="5D"][aria-pressed="true"]').waitFor();
          assert.equal(await page.locator('[data-bench-series-row="SET_A"]').getAttribute('data-bench-series-state'), 'OK');
          assert.equal(await page.locator('[data-bench-series-row="SET_B"]').getAttribute('data-bench-series-state'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-bench-series-row="SET_B"]').textContent()).includes('SET_B_NOT_DEFINED'));
          // ⑪: many trades since 2026-10-20 → D+5 has ≥ 30 samples (hit rate shown with hits/samples); D+20 and D+63 not elapsed.
          const track = await page.locator('[data-track-windows] tbody tr').evaluateAll((r) => r.map((x) => [x.dataset.trackWindow, x.dataset.trackState, x.cells[1].textContent, x.cells[2].textContent]));
          assert.equal(track[0][1], 'OK', JSON.stringify(track));
          assert.ok(Number(track[0][2]) >= 30 && /^\d+\.\d% \(\d+\/\d+\)$/.test(track[0][3]), track[0][3]);
          assert.ok(track[1][3].includes('WINDOW_NOT_ELAPSED') && track[1][3].includes('첫 평가 예상 ≈ 2026-11-17'), track[1][3]);
          assert.equal(track[2][1], 'NOT_AVAILABLE');
          assert.ok(track[2][3].includes('WINDOW_NOT_ELAPSED') && track[2][3].includes('첫 평가 예상 ≈ 2027-01-'), track[2][3]);
          assert.ok(await page.locator('[data-track-recent] tbody tr').count() >= 1);
          assert.ok((await sectionText(page, 11)).includes('●●●만원'), 'realized P&L follows money() hiding');
          for (const n of [11, 12, 13]) assert.ok(noWonAmount(await sectionText(page, n)), 'won amount in ⑪⑫⑬');
          await page.locator('[data-export-template]').click();
          await page.waitForFunction(() => /복사|표시/.test(document.querySelector('[data-report-status]')?.textContent || ''));
          const text = await page.evaluate(async () => { try { return await navigator.clipboard.readText(); } catch (_) { return document.querySelector('[data-export-fallback]')?.value || ''; } });
          assert.ok(/\| D\+5 \| \d+ \| \d+\.\d% \(\d+\/\d+\) \| S&P 500 \|/.test(text) && text.includes('| D+63 | 0 | N/A · '), 'template ⑪ rows');
          assert.ok(/\| 시작 이후 \(기준 2026-10-16 종가\) \| [+−]\d/.test(text), 'template ⑫ row');
          assert.ok(text.includes('달러 기준') && text.includes('| 시리즈 | 5D 수익률 |') && text.includes('| S&P 500 (SPY) | '), 'template ⑬ follows the selection');
          assert.ok(!text.includes(CANARY));
          assert.ok(await noOverflow(page), 'horizontal scroll');
          if (process.env.REPORT_BENCH_SHOTS) { await page.locator('[data-bench-period="SINCE_START"]').click(); await page.locator('[data-bench-period="SINCE_START"][aria-pressed="true"]').waitFor();
            for (const n of [11, 12, 13]) await page.locator('[data-report-section="' + n + '"]').screenshot({ path: path.join(process.env.REPORT_BENCH_SHOTS, 's17-' + n + '-' + width + '.png') }); }
          if (width >= 1024) {
            const f = await page.evaluate(() => { const r = (s) => document.querySelector(s).getBoundingClientRect(), host = r('#daily-report'), w = r('[data-report-section="13"]');
              return { wide: w.width >= host.width - 2, pair: Math.abs(r('[data-report-section="11"]').top - r('[data-report-section="12"]').top) < 2 }; });
            assert.ok(f.wide, '⑬ full width on PC'); assert.ok(f.pair, '⑪ and ⑫ side by side on PC');
          }
          assert.ok(await storageClean(page), 'price, index or return reached storage');
          assert.equal(traffic.writes, 0);
          assert.equal(traffic.console, 0);
          assert.deepEqual(traffic.unexpected, []);
          assert.equal(traffic.errors, 0);
        } finally { await context.close(); }
      });
    }
    await check('⑪ fewer than 30 samples: hit rate hidden as 표본 부족(n<30)', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-28T01:00:00Z', last: '2026-10-27', width: 390 });
      try {
        await signIn(page);
        await page.evaluate(() => { location.hash = 'report/mock'; });
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        const d5 = await page.locator('[data-track-window="5"]').evaluate((x) => [x.dataset.trackState, x.cells[1].textContent, x.cells[2].textContent]);
        assert.equal(d5[0], 'INSUFFICIENT_SAMPLE', JSON.stringify(d5));
        assert.ok(Number(d5[1]) > 0 && Number(d5[1]) < 30 && d5[2] === '표본 부족(n<30)');
        assert.ok(!/%/.test(d5[2]), 'no hit-rate number below the minimum');
        assert.equal(traffic.errors, 0);
        assert.deepEqual(traffic.unexpected, []);
      } finally { await context.close(); }
    });
    await check('investment report: shadow ledger is the target, Set A compared, same RAM history', async () => {
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', last: '2026-10-30', width: 1440 });
      try {
        await signIn(page, { holdings: true });
        await page.evaluate(() => { location.hash = 'report/real'; });
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        await page.locator('[data-bench-chart]').waitFor();
        const keys = await page.locator('[data-bench-series] tbody tr').evaluateAll((r) => r.map((x) => x.dataset.benchSeriesRow));
        assert.deepEqual(keys, ['SHADOW', 'SET_A', 'SP500', 'XLK', 'VUG', 'QUAL', 'XLY', 'XLP']);
        assert.ok((await page.locator('[data-bench-series-row="SHADOW"]').textContent()).includes('그림자 장부 · 대상'));
        await page.locator('[data-bench-period="5D"]').click();
        await page.locator('[data-bench-period="5D"][aria-pressed="true"]').waitFor();
        assert.equal(await page.locator('[data-bench-series-row="SHADOW"]').getAttribute('data-bench-series-state'), 'OK');
        assert.equal(await page.locator('[data-bench-series-row="SET_A"]').getAttribute('data-bench-series-state'), 'OK');
        assert.ok(await page.locator('[data-bench-line="SHADOW"]').count() >= 1 && await page.locator('[data-bench-line="SET_A"]').count() >= 1);
        assert.ok(noWonAmount(await page.locator('#daily-report').textContent()));
        assert.ok(await storageClean(page));
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
