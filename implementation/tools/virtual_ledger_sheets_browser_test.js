'use strict';
// S17 ledger sheet storage (D-10) on the built site at 390 and 1440. Every request is intercepted: same-origin files come
// from the local build (public screens empty, synthetic price-free forward ledger), the private history Worker and the
// Google Sheets API are in-memory SYNTHETIC mocks, anything else is aborted and counted. Checks: before 2026-10-19 the
// Set B form saves a definition but nothing is recorded; after the start date "장부 시트에 기록" appends only the missing
// sessions (append-only), a second click is impossible; a changed cell (decision 2026-10-11) marks PRICE_REVISED and the
// next sessions are written from the recorded state without rewriting anything; the user's Example_* tab is never read;
// Set B needs a purpose and then the 비교 tab appears (phone: 2–3 sets picked); without the user's own target the shadow
// ledger is NOT_AVAILABLE, "세트 A 목표를 내 목표로 복사" writes the target, then TARGET → shadow snapshot → record →
// re-sync keeps the recorded rows; no amount on screen, nothing in device storage or the console.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const { routeEmptyPublicScreens } = require('./empty_public_screens');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const SHEET = 'synthetic_existing_sheet_fixture';
const TOKEN = ['memory', 'only', 'synthetic', 'ledger', 'credential'].join('-');
const SCOPE = 'email openid https://www.googleapis.com/auth/drive.file';
const V = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64);
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const CANARY = '777.0731', COST_CANARY = 4321.0987; // synthetic close / average cost: never on screen, in device storage or the console

function weekdays(from, to) { const out = []; for (let d = new Date(from + 'T00:00:00Z'); d <= new Date(to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1)) if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10)); return out; }
const SESSIONS = weekdays('2026-10-19', '2026-10-30');
function record(date) {
  const companies = {};
  IDS.forEach((id, i) => { companies[id] = { state: 'LIVE', Q: { score: 50 + i, coverage: 'READY', missing_factor_count: 0 }, G: { score: 60 - i / 2, coverage: 'READY', missing_factor_count: 0 } }; });
  return { date, version: V, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } },
    qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function forwardLedger(days) {
  const status = 'ACTIVE';
  return { schema_version: 1, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status, as_of: days.at(-1) + 'T22:31:00+00:00', strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true,
    target: { portfolio_id: 'TARGET', version: 'v0' }, versions: { [V]: days.map(record), [VV]: [] }, version_status: { [V]: { state: status, v_included: false, reason_codes: [] }, [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } } };
}
function history(symbol, range) {
  const meta = symbol.endsWith('.KS') ? ['KRW', 'Asia/Seoul'] : symbol.endsWith('.T') ? ['JPY', 'Asia/Tokyo'] : symbol.endsWith('=X') ? ['KRW', 'Europe/London'] : ['USD', 'America/New_York'];
  const base = symbol === 'KRW=X' ? 1400 : symbol === 'JPYKRW=X' ? 9.3 : 100 + symbol.length;
  const bars = weekdays('2026-09-01', '2026-10-30').map((d, i) => ({ timestamp: Date.parse(d + 'T13:30:00Z') / 1000, open: null, high: null, low: null,
    close: symbol === 'KRW=X' && d === '2026-10-30' ? null : i === 3 ? Number(CANARY) : Math.round(base * (1 + (i % 7) / 100) * 10000) / 10000, adjusted_close: null, volume: null, session_status: 'COMPLETE' }));
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: meta[0], exchange: 'SYNTHETIC', timezone: meta[1], interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: '2026-10-30T22:00:00Z', bars };
}
// In-memory Google Sheets values API for the user's (synthetic) sheet: titles, paged reads, addSheet, append.
function sheetsMock(tabs) {
  const log = [];
  async function handle(route, request, url, cors) {
    const method = request.method(), path = decodeURIComponent(url.pathname), prefix = '/v4/spreadsheets/' + SHEET;
    if (request.headers().authorization !== 'Bearer ' + TOKEN || !path.startsWith(prefix)) { log.push('UNSAFE ' + method); return route.abort(); }
    const json = (body) => route.fulfill({ headers: cors, contentType: 'application/json', body: JSON.stringify(body) });
    if (method === 'GET' && path === prefix && url.searchParams.get('fields') === 'sheets(properties(title))') { log.push('GET titles'); return json({ sheets: ['Quotes', 'Trades', 'Example_SetA_Trades', 'Example_VirtualA', ...tabs.keys()].map((title) => ({ properties: { title } })) }); }
    if (method === 'POST' && path === prefix + ':batchUpdate') {
      const body = JSON.parse(request.postData());
      for (const r of body.requests) { assert.ok(/^Virtual(A|B|C|D|Mine|Meta|Flags)$/.test(r.addSheet.properties.title)); tabs.set(r.addSheet.properties.title, []); }
      log.push('POST addSheet ' + body.requests.map((r) => r.addSheet.properties.title).join(',')); return json({ replies: [] });
    }
    let m = /^\/values\/'([A-Za-z]+)'!A1:append$/.exec(path.slice(prefix.length));
    if (method === 'POST' && m && url.searchParams.get('valueInputOption') === 'RAW') {
      const body = JSON.parse(request.postData()); tabs.get(m[1]).push(...body.values); log.push('POST append ' + m[1] + ' ' + body.values.length); return json({ updates: { updatedRows: body.values.length } });
    }
    m = /^\/values\/'([A-Za-z]+)'!A(\d+):([A-Z])(\d+)$/.exec(path.slice(prefix.length));
    if (method === 'GET' && m && tabs.has(m[1])) {
      log.push('GET ' + m[1]);
      const rows = tabs.get(m[1]).slice(Number(m[2]) - 1, Number(m[4])).map((r) => { const c = [...r]; while (c.length && c.at(-1) === '') c.pop(); return c; });
      return json(rows.length ? { range: m[1], majorDimension: 'ROWS', values: rows } : { range: m[1], majorDimension: 'ROWS' });
    }
    log.push('UNEXPECTED ' + method + ' ' + path); return route.abort();
  }
  return { tabs, log, handle };
}

async function open(browser, { now, width = 390, sheet }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR' });
  const traffic = { worker: 0, unexpected: [], console: 0, errors: 0 };
  await context.addInitScript(({ token, scope, sheetId }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: 'ko-KR', source_language: 'all' }));
    localStorage.setItem('investment.web.v1.unified-sheet-source', sheetId);
    localStorage.setItem('investment.web.v1.private-history-origin', 'https://private-investment-history.kco994553.workers.dev');
    window.google = { accounts: { oauth2: { initTokenClient(config) { return { requestAccessToken() { config.callback({ access_token: token, expires_in: 3600, scope, token_type: 'Bearer' }); } }; }, revoke(_t, done) { done({}); } } } };
  }, { token: TOKEN, scope: SCOPE, sheetId: SHEET });
  await routeEmptyPublicScreens(context);
  await context.route('**/*', async (route) => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === new URL(BASE).origin) {
      if (url.pathname.endsWith('/app-config.js')) { await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: true, privateHistoryWorkerOrigin: WORKER, virtualTradingRequestSpacingMs: 0 }) + ');' }); return; }
      if (url.pathname.endsWith('/forward-validation-ledger.json')) {
        if (new Date(now).toISOString().slice(0, 10) < '2026-10-19') { await route.fulfill({ status: 404, body: '' }); return; }
        await route.fulfill({ contentType: 'application/json', body: JSON.stringify(forwardLedger(SESSIONS)) }); return;
      }
      return route.fallback();
    }
    if (url.origin === WORKER) {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      traffic.worker++;
      await route.fulfill({ status: 200, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body: JSON.stringify(history(url.searchParams.get('symbol'), url.searchParams.get('range'))) });
      return;
    }
    if (url.origin === 'https://sheets.googleapis.com') {
      const cors = { 'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST' };
      if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
      await sheet.handle(route, request, url, cors); return;
    }
    traffic.unexpected.push(url.origin);
    await route.abort();
  });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  page.on('pageerror', (e) => { traffic.errors++; console.log('pageerror ' + String(e.message).slice(0, 200)); });
  page.on('console', (m) => { const t = m.text(); if (t.includes(CANARY) || t.includes(String(COST_CANARY)) || t.includes(TOKEN) || t.includes(SHEET)) traffic.console++; });
  await page.clock.install({ time: new Date(now) });
  await page.goto(BASE + '#home');
  await page.locator('[data-report-link="mock"]').waitFor();
  await prepare(page);
  return { context, page, traffic };
}
// Same Google session (memory token) plus the deployed Worker allowlist (SPY/ETF/FX) simulated with the same token and
// request shape; then sign in. Also used after a reload (the token lives only in page memory).
async function prepare(page) {
  await page.evaluate((token) => {
    const real = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId);
    const session = { ...real, async fetchHistory(origin, symbol, range, options = {}) {
      const r = await fetch(origin + '/history?symbol=' + encodeURIComponent(symbol) + '&range=' + encodeURIComponent(range), { method: 'GET', headers: { Authorization: 'Bearer ' + token }, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', redirect: 'error', signal: options.signal });
      const body = await r.json(); if (!r.ok) throw new Error(body && body.error ? body.error.code : 'YAHOO_UNAVAILABLE'); return body; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
    real.setEnabled(true); real.login();
  }, TOKEN);
  assert.equal(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().connected), true);
}
async function go(page, hash) { await page.evaluate((h) => { location.hash = h; }, hash); }
async function settled(page) { await page.locator('[data-ledger-sheets][data-sheet-state="READY"]').waitFor(); }
async function clean(page) {
  return page.evaluate(({ canary, cost }) => {
    const values = [...Object.values(localStorage), ...Object.values(sessionStorage)].join('\n');
    return !values.includes(canary) && !values.includes(cost) && !/VirtualA|LEDGER_START|"closes"/.test(values);
  }, { canary: CANARY, cost: String(COST_CANARY) });
}
const noWonAmount = (text) => (text.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length === 0;
const writes = (sheet) => sheet.log.filter((x) => x.startsWith('POST'));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  const check = async (name, fn) => { try { await fn(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + String(e.message).slice(0, 400)); } };
  try {
    await check('before 2026-10-19: Set B is saved as a definition, nothing is recorded (390)', async () => {
      const sheet = sheetsMock(new Map());
      const { context, page, traffic } = await open(browser, { now: '2026-10-15T03:00:00Z', sheet });
      try {
        await go(page, 'report/mock-set_b'); await settled(page);
        assert.equal(await page.locator('[data-ledger-before-start]').count(), 1);
        assert.equal(await page.locator('[data-ledger-record]').isDisabled(), true);
        const form = page.locator('[data-weight-form="SET_B"]');
        assert.equal(await form.getAttribute('data-weight-state'), 'NOT_AVAILABLE');
        await form.locator('[data-weight="nvda"]').fill('70'); await form.locator('[data-weight="amd"]').fill('40');
        assert.equal(await form.getAttribute('data-weight-state'), 'INVALID');
        await form.locator('[data-weight-save]').click();
        await page.locator('[data-weight-status="SET_B"]', { hasText: 'WEIGHT_SUM_OVER_100' }).waitFor();
        assert.deepEqual(writes(sheet), []);
        await form.locator('[data-weight="amd"]').fill('25.5');
        await form.locator('[data-weight="smh"]').fill('4.5');
        await form.locator('[data-weight-save]').click();
        await page.locator('[data-weight-status="SET_B"]', { hasText: 'PURPOSE_REQUIRED' }).waitFor();
        assert.deepEqual(writes(sheet), [], 'a set needs its one-line purpose');
        await page.locator('[data-set-purpose="SET_B"]').fill('반도체 집중과 ETF 비교');
        await form.locator('[data-weight-save]').click();
        await page.locator('[data-weight-status="SET_B"]', { hasText: '세트 B 구성을 저장했습니다' }).waitFor();
        await page.waitForFunction(() => document.querySelector('[data-ledger-sheets]')?.dataset.sheetState === 'READY' && document.querySelector('[data-weight="nvda"]')?.value === '70' && document.querySelector('[data-weight="amd"]')?.value === '25.5');
        assert.equal(await page.locator('[data-weight-form="SET_B"]').getAttribute('data-weight-state'), 'OK');
        assert.ok((await page.locator('[data-set-purpose-shown]').textContent()).includes('반도체 집중과 ETF 비교'));
        const meta = sheet.tabs.get('VirtualMeta');
        assert.deepEqual(meta.slice(1).map((r) => [r[1], r[3], r[4], JSON.parse(r[10]).purpose]), [['set_b-1', 'LEDGER_START', '2026-10-19', '반도체 집중과 ETF 비교']]);
        for (const t of ['VirtualA', 'VirtualB', 'VirtualC', 'VirtualD', 'VirtualMine']) assert.equal(sheet.tabs.get(t).length, 1, t + ' has only its header');
        assert.ok(!sheet.log.some((x) => x.includes('Example_')), 'Example_* tabs are never read or written');
        // Two sets (A + B) → the 비교 tab appears; on a phone 2–3 sets are picked, the table is numbers only.
        await page.locator('[data-report-tabs] a', { hasText: '비교' }).waitFor();
        await go(page, 'report/mock-compare');
        await page.locator('[data-compare][data-compare-state="READY"][data-compare-layout="PHONE"]').waitFor();
        assert.equal(await page.locator('[data-compare-pick]').count(), 2);
        assert.equal(await page.locator('[data-compare-set]').count(), 2);
        assert.equal(await page.locator('[data-compare-row="period_return"] [data-state="NOT_AVAILABLE"]').count(), 2, 'before the start date: NA, never 0');
        assert.ok(!/장점|약점|관찰항목/.test(await page.locator('[data-compare]').textContent()));
        assert.equal(traffic.worker, 0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0); assert.equal(traffic.console, 0);
      } finally { await context.close(); }
    });
    for (const width of [390, 1440]) {
      await check('record missing sessions, resume, changed cell → PRICE_REVISED and continue from the recorded state (' + width + ')', async () => {
        const sheet = sheetsMock(new Map());
        const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', width, sheet });
        try {
          await go(page, 'report/mock');
          await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
          await page.locator('[data-ledger-id="set_a"][data-ledger-missing="10"]').waitFor();
          assert.ok((await page.locator('[data-missing-sessions]').textContent()).includes('기록할 거래일: set_a 2026-10-19'));
          assert.ok((await page.locator('[data-ledger-sheets] h2').textContent()).includes('가상 · 실제 추천 아님 · 주문 기능 없음'));
          assert.deepEqual(writes(sheet), [], 'no write before the click');
          await page.locator('[data-ledger-record]').click();
          await page.locator('[data-ledger-status]', { hasText: '10거래일을 기록했습니다' }).waitFor();
          const rows = sheet.tabs.get('VirtualA');
          assert.deepEqual(rows[0].slice(0, 3), ['ledger_id', 'session_date', 'row_type']);
          assert.deepEqual([...new Set(rows.slice(1).map((r) => r[1]))], SESSIONS);
          assert.ok(rows.slice(1).some((r) => r[2] === 'CANCELLED' && r[6] === 'EXEC_FX_MISSING'), 'missing FX day recorded with the engine outcome');
          assert.deepEqual(sheet.tabs.get('VirtualMeta').slice(1).map((r) => [r[1], r[3], r[8]]), [['set_a', 'LEDGER_START', ''], ['set_a', 'RECORD', '2026-10-30']]);
          await page.locator('[data-ledger-id="set_a"][data-ledger-check="OK"][data-ledger-missing="0"]').waitFor();
          assert.equal(await page.locator('[data-ledger-record]').isDisabled(), true);
          // Resume after a reload: the recorded rows replay to the same rows, nothing to append.
          const count = writes(sheet).length;
          await page.reload(); await page.locator('[data-ledger-sheets][data-sheet-state="NOT_CONNECTED"]').waitFor();
          await prepare(page);
          await page.locator('[data-ledger-id="set_a"][data-ledger-check="OK"]').waitFor({ timeout: 40000 });
          assert.equal(await page.locator('[data-ledger-id="set_a"]').getAttribute('data-ledger-missing'), '0');
          // A changed cell in the private sheet (e.g. bars revised after recording): PRICE_REVISED, the recorded rows stay,
          // and the missing sessions are written from the recorded state (decision 2026-10-11).
          const k = rows.findIndex((r) => r[2] === 'SUMMARY' && r[1] === '2026-10-22'); rows[k] = [...rows[k]]; rows[k][13] = String(Number(rows[k][13]) + 1);
          const truncated = rows.filter((r, i) => i === 0 || r[1] <= '2026-10-27');
          sheet.tabs.set('VirtualA', truncated);
          await go(page, 'report/mock-set_b'); await go(page, 'report/mock');
          await page.locator('[data-ledger-price-revised]').waitFor({ timeout: 40000 });
          assert.equal(await page.locator('[data-ledger-id="set_a"]').getAttribute('data-ledger-check'), 'OK');
          assert.equal(await page.locator('[data-ledger-id="set_a"]').getAttribute('data-price-revised'), '2026-10-22');
          assert.ok((await page.locator('[data-ledger-id="set_a"]').textContent()).includes('첫 차이 2026-10-22'));
          await page.locator('[data-ledger-id="set_a"][data-ledger-missing="3"]').waitFor();
          assert.equal(writes(sheet).length, count);
          const kept = JSON.stringify(truncated), keptRows = truncated.length;
          await page.locator('[data-ledger-record]:enabled').click();
          await page.locator('[data-ledger-status]', { hasText: '3거래일을 기록했습니다' }).waitFor();
          const after = sheet.tabs.get('VirtualA');
          assert.equal(JSON.stringify(after.slice(0, keptRows)), kept, 'recorded rows are never rewritten');
          assert.deepEqual([...new Set(after.slice(keptRows).map((r) => r[1]))], ['2026-10-28', '2026-10-29', '2026-10-30']);
          assert.ok(!sheet.log.some((x) => x.includes('Example_')), 'Example_* tabs are never read or written');
          const text = await page.locator('#virtual-ledger-sheets').textContent();
          assert.ok(noWonAmount(text) && !text.includes(CANARY), 'amount on screen');
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
          assert.ok(await clean(page), 'ledger reached device storage');
          assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0); assert.equal(traffic.console, 0);
          assert.ok(!sheet.log.some((x) => x.startsWith('UNSAFE') || x.startsWith('UNEXPECTED')), sheet.log.join('|'));
        } finally { await context.close(); }
      });
    }
    await check('TARGET → shadow snapshot → record → re-sync keeps rows (390)', async () => {
      const sheet = sheetsMock(new Map());
      const { context, page, traffic } = await open(browser, { now: '2026-10-31T01:00:00Z', sheet });
      try {
        // Synthetic ACTUAL holdings on this device (two catalog instruments).
        await page.evaluate((cost) => {
          const snapshot = { effective_at: '2026-10-20T01:00:00Z', themes: [{ holdings: [
            { security_reference: { scheme: 'ISIN', value: 'US67066G1040' }, quantity: '12.5', average_cost: String(cost), currency: 'USD' },
            { security_reference: { code: '042700', exchange: 'KRX', scheme: 'EXCHANGE_CODE' }, quantity: '30', average_cost: '70000', currency: 'KRW' }] }] };
          // The runner reads holdings through effectiveHoldings (stored ACTUAL or the RAM Holdings tab, #204); stub both.
          window.DeviceActual = { ...DeviceActual, readHoldings: async () => snapshot, effectiveHoldings: async () => ({ snapshot, source: 'ACTUAL', as_of: snapshot.effective_at }) };
        }, COST_CANARY);
        await go(page, 'report/real'); await settled(page);
        assert.equal(await page.locator('[data-shadow-ledger]').getAttribute('data-shadow-state'), 'NOT_STARTED');
        // Decision 2026-10-11: no user target → NA with the '내 목표 설정' guide; TARGET v0 is never substituted.
        assert.equal(await page.locator('[data-target-basis]').getAttribute('data-target-basis'), 'NOT_AVAILABLE');
        assert.equal(await page.locator('[data-user-target-guide]').getAttribute('data-user-target-state'), 'NOT_AVAILABLE');
        assert.equal(await page.locator('[data-shadow-create]').isDisabled(), true);
        assert.deepEqual(writes(sheet), []);
        await page.locator('[data-copy-set-a-target]:enabled').click();
        await page.locator('[data-copy-status]', { hasText: '세트 A 목표(19종목)를 내 목표로 복사' }).waitFor();
        await page.locator('[data-target-basis="USER_TARGET"]').waitFor();
        const copied = sheet.tabs.get('VirtualMeta').find((r) => r[3] === 'USER_TARGET');
        assert.equal(Object.keys(JSON.parse(copied[10]).target_weights).length, 19, 'Set A (v1.1 example) weights copied to the sheet');
        const form = page.locator('[data-weight-form="TARGET"]');
        for (const input of await form.locator('[data-weight]').all()) await input.fill('');
        await form.locator('[data-weight="nvda"]').fill('30'); await form.locator('[data-weight="hanmi"]').fill('20');
        await form.locator('[data-weight-save]').click();
        await page.locator('[data-weight-status="TARGET"]', { hasText: '내 목표를 저장했습니다' }).waitFor();
        await page.locator('[data-target-basis="USER_TARGET"]').waitFor();
        await page.locator('[data-shadow-create]:enabled').click();
        await page.locator('[data-shadow-status]', { hasText: '출발 스냅샷을 저장했습니다' }).waitFor();
        await page.locator('[data-shadow-ledger][data-shadow-state="STARTED"]').waitFor();
        const start = sheet.tabs.get('VirtualMeta').find((r) => r[3] === 'LEDGER_START' && r[1] === 'shadow-1');
        assert.equal(start[4], '2026-10-30');
        assert.equal(JSON.parse(start[10]).target_basis, 'USER_TARGET');
        await page.locator('[data-report-inputs][data-runner-state="READY"]').waitFor({ timeout: 30000 });
        await page.locator('[data-ledger-id="shadow-1"][data-ledger-missing="1"]').waitFor();
        await page.locator('[data-ledger-record]').click();
        await page.locator('[data-ledger-status]', { hasText: '1거래일을 기록했습니다(shadow-1)' }).waitFor();
        const mine = sheet.tabs.get('VirtualMine');
        assert.deepEqual(mine.slice(1).filter((r) => r[2] === 'INITIAL').map((r) => r[3]), ['hanmi', 'nvda']);
        assert.equal(sheet.tabs.get('VirtualA').length, 1, 'REAL record writes only the shadow ledger');
        const kept = JSON.stringify(mine);
        page.once('dialog', (d) => d.accept());
        await page.locator('[data-shadow-resync]:enabled').click();
        await page.locator('[data-shadow-status]', { hasText: '다시 맞췄습니다' }).waitFor();
        await page.locator('[data-segment="shadow-2"]').waitFor();
        const meta = sheet.tabs.get('VirtualMeta').slice(1).map((r) => [r[1], r[3], r[4] || r[5]]);
        assert.deepEqual(meta.slice(-2), [['shadow-1', 'LEDGER_CLOSE', '2026-10-31'], ['shadow-2', 'LEDGER_START', '2026-10-31']]);
        assert.equal(JSON.stringify(sheet.tabs.get('VirtualMine')), kept, 're-sync never rewrites recorded rows');
        const text = await page.locator('#content').textContent();
        assert.ok(!text.includes(String(COST_CANARY)) && !text.includes('12.5') && noWonAmount(await page.locator('#virtual-ledger-sheets').textContent()));
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        assert.ok(await clean(page), 'snapshot reached device storage');
        assert.deepEqual(traffic.unexpected, []); assert.equal(traffic.errors, 0); assert.equal(traffic.console, 0);
      } finally { await context.close(); }
    });
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  process.exitCode = fail ? 1 : 0;
})();
