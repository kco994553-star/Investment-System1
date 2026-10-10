/* Public site, synthetic memory-only fixtures. Every external request is intercepted. */
'use strict';
const { chromium } = require('playwright');
const base = new URL(process.env.PRIVATE_HISTORY_URL || 'http://127.0.0.1:8990/Investment-System1/');
const ORIGIN = 'https://private-investment-history.kco994553.workers.dev';
const OTHER_ORIGIN = 'https://another-history.example-account.workers.dev';
const SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly email';
const TOKEN = ['memory', 'only', 'synthetic', 'history', 'credential'].join('-');
const NOW = '2030-01-08T12:00:00.000Z';
const UPSTREAM = ['SYNTHETIC', 'UPSTREAM', 'DO_NOT_DISPLAY'].join('_');
const STORAGE_KEY = 'investment.web.v1.private-history-origin';
const RANGES = ['1mo', '3mo', '6mo', '1y', '2y', '5y'];
const NUMERIC_FIELDS = ['open', 'high', 'low', 'close', 'adjusted_close', 'volume'];
const PRIVATE_CANARIES = [TOKEN, UPSTREAM, 'private-history/1', '53.375', '52.875', '64.75', '61.5', '70.5'];
let browser, currentCheck = 'browser_launch';
const traffic = { unexpected: 0, unsafe: 0, consolePrivate: 0, pageErrors: 0, cspViolations: 0 };
function verify(value) { if (!value) throw new Error('CHECK_FAILED'); }
async function check(name, run) { currentCheck = name; await run(); console.log('PASS ' + name); }
function fixture(range = '1y') {
  const timestamp = day => Date.parse('2030-01-' + day + 'T21:00:00Z') / 1000;
  return { schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol: 'NVDA', range,
    currency: 'USD', exchange: 'NMS', timezone: 'America/New_York', interval: '1d',
    basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: NOW,
    bars: [
      { timestamp: timestamp('03'), open: 51.125, high: 54.625, low: 50.125, close: 53.375, adjusted_close: 52.875, volume: 103, session_status: 'COMPLETE' },
      { timestamp: timestamp('04'), open: null, high: null, low: null, close: null, adjusted_close: null, volume: null, session_status: 'UNKNOWN' },
      { timestamp: timestamp('05'), open: 62.25, high: 65.75, low: 60.5, close: 64.75, adjusted_close: 61.5, volume: 207, session_status: 'IN_PROGRESS' },
      { timestamp: timestamp('07'), open: 67.25, high: 72.5, low: 65.625, close: 70.5, adjusted_close: null, volume: 311, session_status: 'COMPLETE' }
    ] };
}
function codeLocator(page, code) { return page.locator('[data-history-status][data-code="' + code + '"]'); }
async function waitCode(page, code) { await codeLocator(page, code).waitFor(); }
async function frame(page) { await page.evaluate(() => new Promise(requestAnimationFrame)); }
async function closeContext(session) {
  traffic.cspViolations += await session.page.evaluate(() => window.__historyEvidence.csp);
  await session.context.close();
}
async function navigate(page, hash) {
  await page.evaluate(value => { location.hash = value; }, hash);
  if (hash === 'settings') await page.locator('[data-private-history-settings]').waitFor();
  if (hash.startsWith('company/')) await page.locator('[data-private-history]').waitFor();
  await frame(page);
}
async function saveOrigin(session, value = ORIGIN, expected = 'SAVED') {
  const root = session.page.locator('[data-private-history-settings]');
  await root.locator('[data-history-worker-url]').fill(value);
  await root.locator('[data-history-action="save"]').click();
  await root.locator('[data-history-settings-status][data-code="' + expected + '"]').waitFor();
}
async function login(session) {
  const { page } = session, root = page.locator('[data-google-sheet-quotes]');
  await root.locator('[data-sheet-enabled]').check();
  if (await root.locator('[data-sheet-action="prepare"]').isVisible()) {
    await root.locator('[data-sheet-action="prepare"]').click();
    await root.locator('[data-sheet-action="login"]').waitFor({ state: 'visible' });
  }
  await root.locator('[data-sheet-action="login"]').click();
  await root.locator('[data-sheet-action="disconnect"]').waitFor({ state: 'visible' });
  verify(await page.evaluate(() => window.__historyMock.scopes.every(scope => {
    const scopes = new Set(scope.trim().split(/\s+/));
    return scopes.size === 2 && scopes.has('email') && scopes.has('https://www.googleapis.com/auth/spreadsheets.readonly');
  }) && window.__historyMock.scopes.length > 0 && window.__historyMock.prompts.every(prompt => prompt === 'consent') && window.__historyMock.prompts.length > 0 && window.__historyMock.gestureFailures === 0));
}
async function logout(session) {
  await session.page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).disconnect());
}
async function persistentPrivacy(page) {
  return page.evaluate(async ({ canaries, origin, storageKey }) => {
    const local = Object.entries(localStorage), session = Object.values(sessionStorage);
    if (local.some(([key, value]) => canaries.some(canary => value.includes(canary)) || (value.includes(origin) && key !== storageKey))
      || session.some(value => canaries.some(canary => value.includes(canary)) || value.includes(origin))) return false;
    for (const descriptor of await indexedDB.databases()) {
      const db = await new Promise((resolve, reject) => { const request = indexedDB.open(descriptor.name); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(Error('STORAGE')); });
      try {
        for (const store of db.objectStoreNames) {
          const records = await new Promise((resolve, reject) => { const request = db.transaction(store, 'readonly').objectStore(store).getAll(); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(Error('STORAGE')); });
          const text = JSON.stringify(records);
          if (canaries.some(canary => text.includes(canary)) || text.includes(origin) || text.includes('adjusted_close')) return false;
        }
      } finally { db.close(); }
    }
    const catalog = await (await fetch('actual-catalog.json')).json();
    const snapshot = DeviceActual.makeSnapshot(catalog, [], null, new Date().toISOString());
    const backup = JSON.stringify(DeviceMarket.exportBackup(snapshot, DeviceMarket.emptyMarket(catalog), catalog));
    return ![...canaries, origin, storageKey, 'adjusted_close'].some(value => backup.includes(value));
  }, { canaries: PRIVATE_CANARIES, origin: ORIGIN, storageKey: STORAGE_KEY });
}
async function exportsPrivacy(page) {
  await navigate(page, 'companies');
  await page.locator('details:has(#export) > summary').click();
  await page.evaluate(canaries => {
    const create = URL.createObjectURL, click = HTMLAnchorElement.prototype.click;
    window.__historyExportAudit = [];
    URL.createObjectURL = function (blob) {
      window.__historyExportAudit.push(blob.text().then(text => !canaries.some(value => text.includes(value))));
      return create.call(this, blob);
    };
    HTMLAnchorElement.prototype.click = function () { if (!['investment-personal.json', 'device-actual-holdings.json'].includes(this.download)) return click.call(this); };
    window.__historyRestoreExport = () => { URL.createObjectURL = create; HTMLAnchorElement.prototype.click = click; };
  }, [...PRIVATE_CANARIES, ORIGIN, STORAGE_KEY, 'adjusted_close']);
  try {
    await page.locator('#export').click();
    verify(await page.evaluate(async () => window.__historyExportAudit.length === 1 && (await Promise.all(window.__historyExportAudit)).every(Boolean)));
    await navigate(page, 'actual');
    const actual = page.locator('#device-actual-root');
    await actual.locator('[data-action="save"]').click();
    await actual.locator('[data-actual-notice][data-notice="saved"]').waitFor();
    await actual.locator('[data-action="export"]').click();
    verify(await page.evaluate(async () => window.__historyExportAudit.length === 2 && (await Promise.all(window.__historyExportAudit)).every(Boolean)));
    verify(await persistentPrivacy(page));
  } finally { await page.evaluate(() => { window.__historyRestoreExport(); delete window.__historyRestoreExport; delete window.__historyExportAudit; }); }
}
async function open({ enabled = false, deployedConfig = false, approvedOrigin = ORIGIN, locale = 'en-US', width = 1280, storageUnavailable = false } = {}) {
  const context = await browser.newContext({ viewport: { width, height: 844 }, locale, serviceWorkers: 'block' });
  const mode = { reads: 0, googleReads: 0, styles: 0, scripts: 0, revokes: 0, status: 200, code: '', malformed: false, delayed: false, pending: null };
  await context.addInitScript(({ locale, origin, storageUnavailable }) => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({ version: 1, display_locale: locale, source_language: 'all' }));
    window.__historyEvidence = { requests: [], aborted: 0, csp: 0 };
    document.addEventListener('securitypolicyviolation', () => { window.__historyEvidence.csp++; });
    const original = window.fetch;
    window.fetch = function (resource, options = {}) {
      if (typeof resource === 'string' && resource.startsWith(origin)) {
        window.__historyEvidence.requests.push({ get: options.method === 'GET', omit: options.credentials === 'omit', noStore: options.cache === 'no-store', noReferrer: options.referrerPolicy === 'no-referrer', signal: !!options.signal });
        if (options.signal) options.signal.addEventListener('abort', () => { window.__historyEvidence.aborted++; }, { once: true });
      }
      return original.call(this, resource, options);
    };
    if (storageUnavailable) {
      const originalSet = Storage.prototype.setItem;
      Storage.prototype.setItem = function (key, value) { if (key === 'investment.web.v1.private-history-origin') throw Error('STORAGE'); return originalSet.call(this, key, value); };
    }
  }, { locale, origin: ORIGIN, storageUnavailable });
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    try {
      if (url.origin === base.origin) {
        verify(request.method() === 'GET' && !request.postData());
        if (!deployedConfig && url.pathname.endsWith('/app-config.js')) {
          await route.fulfill({ contentType: 'application/javascript', body: 'window.InvestmentAppConfig=Object.freeze(' + JSON.stringify({ googleSheetsClientId: 'synthetic-public.apps.googleusercontent.com', privateHistoryEnabled: enabled, privateHistoryWorkerOrigin: approvedOrigin }) + ');' });
          return;
        }
        await route.continue(); return;
      }
      if (url.href === 'https://accounts.google.com/gsi/style') {
        verify(request.method() === 'GET' && !request.postData() && !request.headers().referer);
        mode.styles++; await route.fulfill({ contentType: 'text/css', body: '.g_id_signin { font-family: Arial; }' }); return;
      }
      if (url.href === 'https://accounts.google.com/gsi/client') {
        verify(request.method() === 'GET' && !request.postData() && !request.headers().referer);
        mode.scripts++;
        await route.fulfill({ contentType: 'application/javascript', body: `window.__historyMock={scopes:[],prompts:[],gestureFailures:0};window.google={accounts:{oauth2:{initTokenClient(config){window.__historyMock.scopes.push(config.scope);return {requestAccessToken(options){window.__historyMock.prompts.push(options.prompt);if(!navigator.userActivation.isActive)window.__historyMock.gestureFailures++;config.callback({access_token:${JSON.stringify(TOKEN)},expires_in:3600,scope:${JSON.stringify(SCOPE)},token_type:'Bearer'});}};},revoke(token,done){fetch('https://oauth2.googleapis.com/revoke',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'token='+encodeURIComponent(token),credentials:'omit',referrerPolicy:'no-referrer'}).then(()=>done({}));}}}};` }); return;
      }
      if (url.origin === 'https://oauth2.googleapis.com' && url.pathname === '/revoke') {
        verify(request.method() === 'POST' && new URLSearchParams(request.postData()).get('token') === TOKEN);
        mode.revokes++; await route.fulfill({ contentType: 'application/json', body: '{}' }); return;
      }
      if (url.origin === 'https://sheets.googleapis.com') {
        mode.googleReads++; await route.fulfill({ status: 200, contentType: 'application/json', body: '{"values":[]}' }); return;
      }
      if (url.origin === ORIGIN) {
        const cors = { 'access-control-allow-origin': base.origin, 'access-control-allow-headers': 'Authorization', 'access-control-allow-methods': 'GET' };
        if (request.method() === 'OPTIONS') { await route.fulfill({ status: 204, headers: cors }); return; }
        verify(request.method() === 'GET' && !request.postData() && url.pathname === '/history');
        verify([...url.searchParams.keys()].sort().join(',') === 'range,symbol');
        verify(url.searchParams.get('symbol') === 'NVDA' && RANGES.includes(url.searchParams.get('range')));
        verify(request.headers().authorization === 'Bearer ' + TOKEN && !request.headers().cookie && !request.headers().referer);
        mode.reads++;
        const payload = fixture(url.searchParams.get('range'));
        if (mode.malformed) payload.bars[0].close = UPSTREAM;
        const body = JSON.stringify(mode.status === 200 ? payload : { error: { code: mode.code, message: UPSTREAM, detail: UPSTREAM } });
        const complete = () => route.fulfill({ status: mode.status, headers: { ...cors, 'cache-control': 'no-store' }, contentType: 'application/json', body }).catch(() => {});
        if (mode.delayed) mode.pending = complete; else await complete();
        return;
      }
      traffic.unexpected++; await route.abort();
    } catch (_) { traffic.unsafe++; await route.abort().catch(() => {}); }
  });
  const page = await context.newPage();
  page.setDefaultTimeout(6000);
  page.on('pageerror', () => { traffic.pageErrors++; });
  page.on('console', message => { if (PRIVATE_CANARIES.some(value => message.text().includes(value))) traffic.consolePrivate++; });
  await page.clock.install({ time: new Date(NOW) });
  const url = new URL(base); url.hash = 'settings';
  await page.goto(url.href, { waitUntil: 'networkidle' });
  await page.locator('[data-private-history-settings]').waitFor();
  await page.locator('[data-google-sheet-quotes]').waitFor();
  return { context, page, mode };
}
async function chart(session) { await navigate(session.page, 'company/nvda'); return session.page.locator('[data-private-history]'); }
async function fetchHistory(session, range) {
  const root = session.page.locator('[data-private-history]');
  if (range) await root.locator('[data-history-range]').selectOption(range);
  await root.locator('[data-history-action="fetch"]').click();
}
async function verifyResults(session) {
  const { page } = session, root = page.locator('[data-private-history]');
  await root.locator('[data-history-table] tbody tr').first().waitFor({ state: 'attached' });
  await root.locator('[data-history-results] summary').click();
  verify(await root.locator('[data-history-chart]').count() === 1);
  const rows = await root.locator('[data-history-table] tbody tr').allTextContents();
  verify(rows.length === 4 && rows[0].includes('53.375') && rows[0].includes('52.875') && rows[0].includes('103'));
  verify(!/53\.375|52\.875|64\.75|61\.5/.test(rows[1]));
  verify(rows[2].includes('IN_PROGRESS') && rows[3].includes('COMPLETE'));
  const expected = fixture((await root.locator('[data-history-range]').inputValue())).bars;
  const tableRows = root.locator('[data-history-table] tbody tr');
  for (let index = 0; index < expected.length; index++) {
    const cells = tableRows.nth(index).locator('td');
    verify(await cells.first().textContent() === new Date(expected[index].timestamp * 1000).toISOString());
    verify(await cells.last().textContent() === expected[index].session_status);
    for (const field of NUMERIC_FIELDS) {
      const cell = tableRows.nth(index).locator('[data-history-field="' + field + '"]');
      verify(await cell.textContent() === (expected[index][field] === null ? '—' : String(expected[index][field])));
      verify(await cell.getAttribute('data-missing') === String(expected[index][field] === null));
    }
  }
  const metadata = await root.locator('[data-history-meta]').textContent();
  for (const value of ['Yahoo Finance(비공식)', 'NVDA', 'USD', 'NMS', 'America/New_York', '1d', 'RAW_CLOSE', 'UNKNOWN', NOW]) verify(metadata.includes(value));
  const chartSafe = await root.locator('[data-history-chart]').evaluate(svg => {
    const lines = [...svg.querySelectorAll('path')].filter(node => node.getAttribute('d'));
    const polylines = [...svg.querySelectorAll('polyline')].filter(node => node.getAttribute('points'));
    return lines.some(node => (node.getAttribute('d').match(/M/g) || []).length >= 2) || lines.length + polylines.length >= 2;
  });
  verify(chartSafe);
  verify(await root.locator('[data-history-chart]').evaluate(svg => [...svg.querySelectorAll('path')].some(path => /620\.00,20\.00$/.test(path.getAttribute('d') || ''))));
  verify(await persistentPrivacy(page));
}
async function deployedChecks(locale, width) {
  const session = await open({ enabled: true, deployedConfig: true, locale, width });
  const { page, mode } = session;
  try {
    await check('deployed_config_no_auto_requests_' + locale + '_' + width, async () => {
      verify(await page.evaluate(origin => InvestmentAppConfig.privateHistoryEnabled === true && InvestmentAppConfig.privateHistoryWorkerOrigin === origin, ORIGIN));
      const settings = page.locator('[data-private-history-settings]');
      verify(await settings.locator('[data-history-worker-url]').inputValue() === ORIGIN);
      const text = await settings.textContent();
      verify(text.includes(locale === 'ko-KR' ? '이메일 확인 권한에 다시 동의' : 'consent again to email verification'));
      verify(await settings.locator('[data-history-company]').count() === 19);
      await chart(session); await waitCode(page, 'ORIGIN_UNAPPROVED');
      verify(mode.reads === 0 && mode.googleReads === 0 && mode.styles === 0 && mode.scripts === 0);
    });
    await check('deployed_consent_and_private_history_' + locale + '_' + width, async () => {
      await navigate(page, 'settings');
      await page.locator('[data-history-action="save"]').click();
      await page.locator('[data-history-settings-status][data-code="SAVED"]').waitFor();
      await chart(session); await waitCode(page, 'AUTH_REQUIRED');
      await navigate(page, 'settings'); await login(session);
      await page.locator('[data-history-company="nvda"]').click();
      await waitCode(page, 'READY');
      verify(mode.reads === 0 && mode.googleReads === 0);
      await fetchHistory(session); await verifyResults(session);
      verify(mode.reads === 1 && mode.googleReads === 0);
      verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await exportsPrivacy(page);
    });
  } finally { await closeContext(session); }
}
async function defaultChecks(locale, width) {
  const session = await open({ locale, width }), { page, mode } = session;
  try {
    await check('default_off_' + locale + '_' + width, async () => {
      await saveOrigin(session);
      verify(await page.evaluate(key => localStorage.getItem(key), STORAGE_KEY) === ORIGIN);
      const root = await chart(session); await waitCode(page, 'OFF');
      verify(!await root.locator('[data-history-action="fetch"]').isEnabled());
      verify(await root.locator('[data-history-range]').isDisabled());
      await root.locator('[data-history-range]').evaluate(select => { select.value = '1mo'; select.dispatchEvent(new Event('change')); }); await frame(page);
      verify(mode.reads === 0 && mode.googleReads === 0 && mode.scripts === 0 && mode.styles === 0);
      verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      verify(await persistentPrivacy(page));
    });
  } finally { await closeContext(session); }
}
async function enabledChecks(locale, width) {
  const session = await open({ enabled: true, locale, width }), { page, mode } = session;
  try {
    await check('settings_reject_unsafe_origins_' + locale + '_' + width, async () => {
      for (const value of ['not-a-url', 'http://synthetic-history.example-account.workers.dev', ORIGIN + '/history', ORIGIN + '?token=synthetic', ORIGIN + '#fragment', 'https://user:password@synthetic-history.example-account.workers.dev', 'https://unapproved.example.invalid']) await saveOrigin(session, value, 'REQUEST_INVALID');
      verify(await page.evaluate(key => localStorage.getItem(key), STORAGE_KEY) === null);
      await saveOrigin(session); verify(mode.reads === 0 && mode.scripts === 0);
    });
    await check('login_is_explicit_shared_and_does_not_fetch_' + locale + '_' + width, async () => {
      await chart(session); await waitCode(page, 'AUTH_REQUIRED'); verify(mode.reads === 0);
      await navigate(page, 'settings'); await login(session); verify(mode.reads === 0 && mode.googleReads === 0);
      const root = await chart(session); await waitCode(page, 'READY');
      verify(await root.locator('[data-history-range]').inputValue() === '1y');
      await root.locator('[data-history-range]').selectOption('1mo'); await frame(page); verify(mode.reads === 0);
    });
    await check('explicit_daily_history_preserves_raw_adjusted_and_gaps_' + locale + '_' + width, async () => {
      await fetchHistory(session, '1y'); await verifyResults(session); verify(mode.reads === 1 && mode.googleReads === 0);
      verify(await page.evaluate(() => window.__historyEvidence.requests.every(request => request.get && request.omit && request.noStore && request.noReferrer && request.signal)));
      verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    });
    await check('range_changes_and_navigation_do_not_fetch_' + locale + '_' + width, async () => {
      const root = page.locator('[data-private-history]');
      for (const range of RANGES) await root.locator('[data-history-range]').selectOption(range);
      await frame(page); verify(mode.reads === 1);
      await navigate(page, 'home'); await chart(session); await waitCode(page, 'READY');
      verify(mode.reads === 1 && await page.locator('[data-history-table]').count() === 0);
      await navigate(page, 'settings'); await page.locator('#display-locale').selectOption(locale === 'en-US' ? 'ko-KR' : 'en-US');
      await page.locator('[data-private-history-settings]').waitFor(); await chart(session); verify(mode.reads === 1);
      verify(await persistentPrivacy(page));
    });
    await check('exports_exclude_worker_token_and_history_' + locale + '_' + width, async () => {
      await exportsPrivacy(page); verify(mode.reads === 1 && mode.googleReads === 0);
    });
  } finally { await closeContext(session); }
}
async function errorChecks() {
  const session = await open({ enabled: true }), { page, mode } = session;
  try {
    await saveOrigin(session); await login(session); await chart(session);
    for (const code of ['RATE_LIMITED', 'AUTH_UNAVAILABLE', 'YAHOO_FORMAT_CHANGED', 'HISTORY_UNAVAILABLE']) {
      await check('fixed_server_error_' + code, async () => {
        mode.status = code === 'RATE_LIMITED' ? 429 : 503; mode.code = code;
        await fetchHistory(session); await waitCode(page, code);
        verify(!(await page.locator('[data-private-history]').textContent()).includes(UPSTREAM));
        verify(await page.locator('[data-history-table]').count() === 0);
      });
    }
    await check('unknown_error_and_malformed_success_are_redacted', async () => {
      mode.status = 502; mode.code = UPSTREAM; await fetchHistory(session); await waitCode(page, 'YAHOO_UNAVAILABLE');
      mode.status = 200; mode.malformed = true; await fetchHistory(session); await waitCode(page, 'YAHOO_FORMAT_CHANGED');
      verify(!(await page.locator('[data-private-history]').textContent()).includes(UPSTREAM)); mode.malformed = false;
    });
    await check('auth_forbidden_clears_shared_login_and_results', async () => {
      mode.status = 200; await fetchHistory(session); await verifyResults(session);
      mode.status = 403; mode.code = 'AUTH_FORBIDDEN'; await fetchHistory(session);
      await page.waitForFunction(() => ['AUTH_FORBIDDEN', 'AUTH_REQUIRED'].includes(document.querySelector('[data-history-status]')?.dataset.code));
      verify(await page.locator('[data-history-table]').count() === 0);
      await navigate(page, 'settings'); await page.locator('[data-sheet-action="login"]').waitFor({ state: 'visible' });
      verify(await persistentPrivacy(page));
    });
  } finally { await closeContext(session); }
}
async function cancelCheck(action) {
  const session = await open({ enabled: true }), { page, mode } = session;
  try {
    await saveOrigin(session); await login(session); await chart(session);
    await check('pending_request_aborted_and_stale_result_blocked_' + action, async () => {
      await fetchHistory(session); await verifyResults(session);
      mode.delayed = true; await fetchHistory(session);
      await waitCode(page, 'LOADING');
      for (let index = 0; index < 20 && !mode.pending; index++) await frame(page);
      verify(typeof mode.pending === 'function');
      const reads = mode.reads;
      if (action === 'close') await page.locator('[data-history-action="close"]').click();
      else if (action === 'navigation') await navigate(page, 'home');
      else if (action === 'logout') await logout(session);
      else if (action === 'expiry') await page.clock.fastForward(3600001);
      else if (action === 'pagehide') await page.evaluate(() => dispatchEvent(new PageTransitionEvent('pagehide')));
      await frame(page);
      verify(await page.evaluate(() => window.__historyEvidence.aborted > 0));
      await mode.pending(); await frame(page);
      verify(await page.locator('[data-history-table]').count() === 0 && mode.reads === reads);
      if (action === 'navigation') { await chart(session); await waitCode(page, 'READY'); }
      if (['logout', 'expiry', 'pagehide'].includes(action)) {
        await navigate(page, 'settings'); await page.locator('[data-sheet-action="login"]').waitFor({ state: 'visible' });
        await chart(session); await waitCode(page, 'AUTH_REQUIRED');
      }
      verify(await persistentPrivacy(page));
    });
  } finally { await closeContext(session); }
}
async function otherBoundaryChecks() {
  for (const [name, approvedOrigin] of [['mismatch', OTHER_ORIGIN], ['missing', ''], ['trailing_slash', ORIGIN + '/']]) {
    await check('unapproved_pin_cannot_fetch_' + name, async () => {
      const session = await open({ enabled: true, approvedOrigin });
      try { await saveOrigin(session); await login(session); const root = await chart(session); await waitCode(session.page, 'ORIGIN_UNAPPROVED'); verify(!await root.locator('[data-history-action="fetch"]').isEnabled() && session.mode.reads === 0); }
      finally { await closeContext(session); }
    });
  }
  await check('worker_origin_storage_failure_is_fixed_and_local', async () => {
    const session = await open({ enabled: true, storageUnavailable: true });
    try { await saveOrigin(session, ORIGIN, 'STORAGE_UNAVAILABLE'); verify(session.mode.reads === 0 && await session.page.evaluate(key => localStorage.getItem(key), STORAGE_KEY) === null); }
    finally { await closeContext(session); }
  });
}
async function main() {
  try {
    const executablePath = process.env.CHROMIUM_EXECUTABLE_PATH || process.env.WEB_TEST_CHROMIUM_PATH;
    browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
    for (const locale of ['ko-KR', 'en-US']) for (const width of [390, 1280]) await defaultChecks(locale, width);
    for (const locale of ['ko-KR', 'en-US']) for (const width of [390, 1280]) await enabledChecks(locale, width);
    for (const locale of ['ko-KR', 'en-US']) for (const width of [390, 1280]) await deployedChecks(locale, width);
    await errorChecks(); await otherBoundaryChecks();
    for (const action of ['close', 'navigation', 'logout', 'expiry', 'pagehide']) await cancelCheck(action);
    await check('external_requests_are_mocked_and_evidence_has_no_payloads', async () => verify(Object.values(traffic).every(value => value === 0)));
  } catch (error) {
    const frames = String(error.stack || '').match(/private_history_browser_test\.js:\d+:\d+/g) || [];
    console.error('FAIL ' + currentCheck + ' ' + (frames[1] || frames[0] || 'BROWSER_FAILURE'));
    process.exitCode = 1;
  }
  finally { if (browser) await browser.close(); }
}
main();
