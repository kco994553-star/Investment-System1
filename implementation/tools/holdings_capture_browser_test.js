/* Capture + personal AI Holdings tab, sheet #N/A → Worker close, and outside-scope holdings. Google Sheets and the Worker are mocked;
   every holding, price and FX value is synthetic and stays in memory. Logs carry check names only. */
'use strict';
const {displayOnlyOff}=require('./display_only_off.js');
const {chromium} = require('playwright');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const ID = ['synthetic', 'capture', 'sheet', 'fixture'].join('_'), TOKEN = ['synthetic', 'capture', 'ram'].join('-');
const ORIGIN = 'https://private-investment-history.kco994553.workers.dev';
const TODAY = new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
// Canary values from the Holdings tab and the Worker: must never reach storage, backups or logs. (Sheet Quotes prices are
// stored by the existing import and are not canaries.)
const CANARY = ['13.579', '24681357', '4321.987', '600.25', '8642.13'];
const HOLDINGS = [['as_of', 'symbol', 'quantity', 'avg_cost', 'currency', 'cost_krw', 'name'],
  [TODAY, 'ASML', '13.579', '700', 'USD', '24681357', 'ASML Holding'], [TODAY, '8035', '2', '30000', 'JPY', '', 'Tokyo Electron'],
  [TODAY, 'KO', '5', '60.5', 'USD', '', 'Coca-Cola'], [TODAY, 'SPY', '1', '', 'USD', '800000', 'SPDR S&P 500'], [TODAY, 'SYNQ', '3', '10', 'USD', '', 'Synthetic Q'],
  [TODAY, 'NVDA', '1,000', '', 'USD'], [TODAY, 'QQQ', '2', '10', 'USD', '', 'Unapproved ETF'], [TODAY, 'CASH_KRW', '8642.13', '', 'KRW']];
const QUOTES = [['code', 'price', 'tradetime'], ['NASDAQ:ASML', 97.531, 46000], ['TYO:8035', '', ''], ['NASDAQ:NVDA', 50, 46000], ['NASDAQ:SYNQ', 12.5, ''], ['CURRENCY:USDKRW', 1400, ''], ['CURRENCY:JPYKRW', 9.5, '']];
function bars(close) { const day = Math.floor(Date.now() / 86400000) * 86400; return [{timestamp: day - 3 * 86400, open: 1, high: close, low: 1, close: close - 1, adjusted_close: null, volume: 1, session_status: 'COMPLETE'},
  {timestamp: day - 2 * 86400, open: 1, high: close, low: 1, close, adjusted_close: null, volume: 1, session_status: 'COMPLETE'},
  {timestamp: day - 3600, open: 1, high: close + 5, low: 1, close: close + 5, adjusted_close: null, volume: 1, session_status: 'IN_PROGRESS'}]; }
function history(symbol, close) {
  return {schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range: '1mo', currency: symbol.endsWith('.T') ? 'JPY' : 'USD', exchange: 'SYN',
    timezone: symbol.endsWith('.T') ? 'Asia/Tokyo' : 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: new Date().toISOString(), bars: bars(close)};
}
function verify(value, label) { if (!value) { const error = new Error(label); error.safe = label; throw error; } }
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, phase = 'INIT';
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});await displayOnlyOff(context);
      await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: new URL(BASE).origin});
      const page = await context.newPage(); page.setDefaultTimeout(10000);
      const mock = {headerBroken: false, posts: [], workerCalls: [], unsafe: 0, holdingsReads: 0}; let errors = 0, leaked = 0;
      page.on('pageerror', () => errors++); page.on('console', message => { if (CANARY.some(c => message.text().includes(c))) leaked++; });
      await page.addInitScript(({id, origin, token}) => {
        localStorage.setItem('investment.web.v1.unified-sheet-source', id); localStorage.setItem('investment.web.v1.private-history-origin', origin);
        // Pause only the settings response at the Quotes mount boundary; storage itself stays real.
        // This makes the initial read finish after a newer user action without sleeps or network timing.
        const settingsGate = {armed: true, release: null, enabled: null}; let actualApi;
        window.__armSettingsRead = () => { settingsGate.armed = true; settingsGate.release = null; settingsGate.enabled = null; };
        window.__settingsReadPaused = () => !!settingsGate.release;
        window.__settingsReadEnabled = () => settingsGate.enabled;
        window.__releaseSettingsRead = () => { const release = settingsGate.release; settingsGate.release = null; if (release) release(); };
        Object.defineProperty(window, 'DeviceActual', {configurable: true, get: () => actualApi, set(api) {
          actualApi = {...api, sheetSettings(...args) {
            const read = api.sheetSettings(...args);
            if (args.length !== 1 || !settingsGate.armed || !new Error().stack.includes('google-sheet-quotes.js')) return read;
            settingsGate.armed = false;
            return read.then(value => new Promise(resolve => {
              settingsGate.enabled = value.enabled; settingsGate.release = () => resolve(value);
            }));
          }};
        }});
        window.__pendingGrants = []; window.__holdGrant = false; window.__grantRequests = 0;
        window.__finishGrant = () => { for (const complete of window.__pendingGrants.splice(0)) complete(); };
        window.__opened = []; window.open = (url) => { window.__opened.push(String(url)); return null; };
        window.google = {accounts: {oauth2: {initTokenClient(config) { return {requestAccessToken() {
          window.__grantRequests++;
          const complete = () => config.callback({access_token: token, expires_in: 3600, scope: 'https://www.googleapis.com/auth/drive.file email'});
          if (window.__holdGrant) window.__pendingGrants.push(complete); else complete();
        }}; }, revoke(_, done) { done({}); }}}};
      }, {id: ID, origin: ORIGIN, token: TOKEN});
      await page.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (url.origin === new URL(BASE).origin) return route.continue();
        const cors = {'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST'};
        if (request.method() === 'OPTIONS') return route.fulfill({status: 204, headers: cors});
        if (request.headers().authorization !== 'Bearer ' + TOKEN || request.headers().referer || request.headers().cookie) mock.unsafe++;
        if (url.origin === ORIGIN && url.pathname === '/history') {
          const symbol = url.searchParams.get('symbol'); mock.workerCalls.push(symbol);
          const payload = symbol === '8035.T' ? history('8035.T', 4321.987) : symbol === 'SPY' ? history('SPY', 600.25) : symbol === 'KO' ? history('KO', 600.25) : null;
          if (!payload) { mock.unsafe++; return route.fulfill({status: 400, headers: cors, contentType: 'application/json', body: JSON.stringify({error: {code: 'REQUEST_INVALID'}})}); }
          return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify(payload)});
        }
        if (url.origin === 'https://sheets.googleapis.com') {
          if (!url.pathname.includes(ID)) mock.unsafe++;
          if (request.method() === 'POST') { mock.posts.push(JSON.parse(request.postData())); return route.fulfill({headers: cors, contentType: 'application/json', body: '{"replies":[]}'}); }
          if (url.pathname.includes('/values/')) {
            const range = decodeURIComponent(url.pathname.split('/values/')[1]);
            let values;
            if (range === "'Quotes'!A1:C1025") values = QUOTES;
            else if (range === "'Holdings'!A1:H1025") { mock.holdingsReads++; values = mock.headerBroken ? [['date', 'symbol', 'quantity'], [TODAY, 'ASML', '1']] : HOLDINGS; }
            else if (/^'(Quotes|Trades|Universe)'!A1:[CD]1$/.test(range)) values = [range.startsWith("'Trades'") ? ['date', 'symbol', 'b/s', 'quantity'] : range.startsWith("'Quotes'") ? ['code', 'price', 'tradetime'] : ['code', 'marketcap', 'price']];
            else { mock.unsafe++; return route.abort(); }
            return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify({values})});
          }
          const tabs = ['Quotes', 'Trades', 'Universe', ...(mock.posts.length ? ['Holdings'] : [])].map((title, sheetId) => ({properties: {title, sheetId}}));
          return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify({sheets: tabs})});
        }
        mock.unsafe++; return route.abort();
      });
      phase = 'SIGN_IN_GOTO';
      await page.goto(BASE + '#settings'); const setup = page.locator('[data-google-first-setup]');
      phase = 'SIGN_IN_INITIAL_READ';
      await page.waitForFunction(() => window.__settingsReadPaused());
      verify(await page.evaluate(() => window.__settingsReadEnabled() === false), 'initial native settings are disabled');
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().ready), 'the synthetic OAuth SDK is ready before the user signs in');
      phase = 'SIGN_IN_CLICK';
      await setup.locator('[data-setup-action="login"]').click();
      phase = 'SIGN_IN_CONNECTED';
      await page.waitForFunction(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().connected);
      verify(await page.evaluate(() => window.__grantRequests === 1), 'the user signs in with exactly one grant request');
      phase = 'SIGN_IN_HYDRATION';
      await page.evaluate(() => window.__releaseSettingsRead());
      await page.locator('[data-sheet-google-controls]').waitFor({state: 'attached'});
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().connected), 'delayed initial settings keep the newer successful sign-in');
      // Authorization is shared; explicitly opt into this Quotes panel before checking its controls.
      // Other consumers may have mounted an OFF Quotes panel before the grant completed.
      await page.locator('[data-sheet-enabled]').check();
      verify(await page.locator('[data-sheet-enabled]').isChecked(), 'the user explicitly enables the Quotes input panel');
      verify(await page.evaluate(() => {
        const state = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state();
        return state.enabled && state.connected && window.__grantRequests === 1;
      }), 'enabling the Quotes panel preserves the existing grant without another popup');
      verify(await page.locator('[data-sheet-google-controls]').isVisible(), 'connected sheet controls remain visible after delayed hydration');
      await page.evaluate(async id => { await DeviceActual.sheetSettings(window, {schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: id, range: "'Quotes'!A1:C1025"}); }, ID);
      await page.goto(BASE + '#home'); await page.goto(BASE + '#settings');

      phase = 'A_SHEET_NA_TO_WORKER';
      await page.locator('[data-sheet-action="fetch"]').click();
      await page.waitForFunction(() => /Worker 종가 · 일봉 · 정보용 1 \/ NOT_AVAILABLE 0/.test(document.querySelector('[data-sheet-summary]')?.textContent || ''));
      verify(JSON.stringify(mock.workerCalls) === '["8035.T"]', 'only the #N/A TARGET symbol reaches the Worker');
      verify(await page.evaluate(() => WorkerQuoteFallback.status(window, '8035').session_date.length === 10), 'session date');

      phase = 'A_VALUE_CARD';
      await page.goto(BASE + '#company/tokyo_electron');
      const card = page.locator('[data-value-quote-source="WORKER_CLOSE"]'); await card.waitFor();
      verify((await card.textContent()).includes('Worker 종가 · 일봉 · 정보용'), 'value card label');

      phase = 'B_GUIDE_COPY';
      await page.goto(BASE + '#actual'); const guide = page.locator('[data-broker-guide]'); await guide.waitFor();
      verify((await guide.locator('h3').textContent()) === '내 증권사 연결 방법', 'guide title');
      await guide.locator('[data-capture-action="copy"]').click(); await page.locator('[data-capture-status][data-code="PROMPT_COPIED"]').waitFor();
      const copied = await page.evaluate(() => navigator.clipboard.readText());
      verify(copied.startsWith('[잔고 캡처 변환 프롬프트 v1]') && copied.includes('모든 줄에 ' + TODAY + ' 값을') && !copied.includes('{{AS_OF}}') && copied.includes('as_of\tsymbol\tquantity\tavg_cost\tcurrency\tcost_krw\tname'), 'prompt with as_of');

      phase = 'B_OPEN_TAB';
      await guide.locator('[data-capture-action="open"]').click(); await page.locator('[data-capture-status][data-code="TAB_CREATED"]').waitFor();
      const opened = await page.evaluate(() => window.__opened);
      verify(opened.length === 1 && opened[0] === 'https://docs.google.com/spreadsheets/d/' + ID + '/edit', 'sheet opened in a new tab');
      const post = mock.posts[0], requests = post && post.requests || [];
      verify(requests.length === 3 && requests[0].addSheet.properties.title === 'Holdings' && requests[1].repeatCell.cell.userEnteredFormat.numberFormat.type === 'TEXT'
        && JSON.stringify(requests[2].updateCells.rows[0].values.map(v => v.userEnteredValue.stringValue)) === JSON.stringify(HOLDINGS[0]), 'Holdings tab created with the exact header');
      await guide.locator('[data-capture-action="open"]').click(); await page.locator('[data-capture-status][data-code="TAB_EXISTS"]').waitFor();
      verify(mock.posts.length === 1, 'an existing Holdings tab is never modified');

      phase = 'B_RETURN_PREVIEW';
      const workerBefore = mock.workerCalls.length;
      await page.evaluate(() => window.dispatchEvent(new Event('focus')));
      await page.locator('[data-capture-preview="OK"]').waitFor();
      // Click-only rule (owner decision 2026-10-23): the automatic read on return asks no Worker; the outside symbols wait for
      // the user's 'Holdings 탭 다시 읽기' click.
      await page.locator('[data-actual-summary] [data-outside-symbol="KO"]').waitFor();
      verify(mock.workerCalls.length === workerBefore, 'the automatic read on return makes no Worker request');
      verify((await page.locator('[data-actual-summary] [data-outside-symbol="KO"]').textContent()).includes('PRICE_NOT_FETCHED'), 'KO waits for the click (PRICE_NOT_FETCHED)');
      await guide.locator('[data-capture-action="read"]').click();
      for (let i = 0; i < 200 && !mock.workerCalls.includes('KO'); i++) await page.waitForTimeout(50);
      await page.waitForFunction(() => (document.querySelector('[data-actual-summary] [data-outside-symbol="KO"]')?.textContent || '').includes('Worker 종가'));
      await page.locator('[data-capture-preview="OK"]').waitFor();
      verify(await page.locator('[data-capture-positions] tbody tr').count() === 6, 'six readable positions');
      const review = await page.locator('[data-capture-review] li').allTextContents();
      verify(review.length === 1 && review[0].includes('행 7') && review[0].includes('QUANTITY_FORMAT'), 'thousands separator row needs review with row and reason');
      verify((await page.locator('[data-capture-cash="CASH_KRW"]').count()) === 1, 'cash row');
      verify((await page.locator('[data-capture-row="2"]').textContent()).includes('cost_krw ÷ quantity'), 'cost basis label');
      verify((await page.locator('[data-capture-row="3"]').textContent()).includes('avg_cost (cost_krw 없음)'), 'avg_cost fallback label');

      phase = 'B_C_SUMMARY';
      const summary = page.locator('[data-actual-summary]');
      await summary.locator('[data-holdings-source="HOLDINGS_TAB"]').waitFor();
      const summaryText = await summary.textContent();
      verify(summaryText.includes('Worker 종가 · 일봉 · 정보용') && summaryText.includes('가격 기준일 '), 'TEL valued with the Worker close in the actual view');
      verify(summaryText.includes('cost_krw ÷ quantity (원화 매입금액 기준)'), 'in-scope cost basis shown');
      const ko = await summary.locator('[data-outside-symbol="KO"]').textContent();
      verify(ko.includes('Worker 종가 · 일봉 · 정보용') && ko.includes('QGV') && ko.includes('OUT_OF_SCOPE'), 'approved Universe KO has price without expanding QGV allocation');
      verify((await summary.locator('[data-outside-symbol="QQQ"]').textContent()).includes('NOT_AVAILABLE · QUOTE_NOT_AVAILABLE_OUT_OF_SCOPE'), 'unapproved QQQ remains without price');
      const spy = await summary.locator('[data-outside-symbol="SPY"]').textContent(), synq = await summary.locator('[data-outside-symbol="SYNQ"]').textContent();
      verify(spy.includes('Worker 종가 · 일봉 · 정보용') && spy.includes('cost_krw') && spy.includes('QGV') && spy.includes('OUT_OF_SCOPE'), 'allowlisted outside symbol uses the Worker close');
      verify(synq.includes('GOOGLEFINANCE') && synq.includes('avg_cost'), 'outside symbol from the sheet Quotes row');
      verify(mock.workerCalls.includes('KO') && !mock.workerCalls.includes('QQQ') && !mock.workerCalls.includes('SYNQ'), 'KO approved; QQQ never requested and SYNQ uses the existing sheet quote');
      verify((await summary.locator('[data-cash-row="CASH_KRW"]').count()) === 1, 'cash shown apart from positions');
      const eff = await page.evaluate(async () => { const c = await (await fetch('actual-catalog.json')).json(), r = await DeviceActual.effectiveHoldings(window, c); return {source: r.source, rows: r.snapshot.themes.flatMap(t => t.holdings).length}; });
      verify(eff.source === 'HOLDINGS_TAB' && eff.rows === 2, 'shadow-ledger input uses the Holdings tab');

      phase = 'A_FILL_BUTTON';
      await page.locator('[data-worker-fallback-action="fill"]').click(); await page.locator('[data-worker-fallback-status][data-code="FILLED"]').waitFor();

      phase = 'B_HEADER_MISMATCH';
      mock.headerBroken = true; await guide.locator('[data-capture-action="read"]').click(); await page.locator('[data-capture-preview="HEADER_MISMATCH"]').waitFor();
      verify((await page.locator('[data-actual-status]').textContent()).includes('NOT_AVAILABLE'), 'no rows read on header mismatch');
      mock.headerBroken = false; await guide.locator('[data-capture-action="read"]').click(); await page.locator('[data-capture-preview="OK"]').waitFor();

      phase = 'B_PRECEDENCE';
      const row = page.locator('[data-security-index="0"]'); await row.locator('[data-field="quantity"]').fill('2'); await row.locator('[data-field="average_cost"]').fill('3');
      await page.locator('[data-action="save"]').click(); await page.locator('[data-actual-notice][data-notice="saved"]').waitFor();
      await summary.locator('[data-holdings-source="DEVICE_ACTUAL"]').waitFor();
      verify((await page.locator('[data-capture-state="OLDER"]').count()) === 1, 'older Holdings tab is shown as not used');

      phase = 'PRIVACY';
      const dump = await page.evaluate(async () => {
        const db = await new Promise((resolve, reject) => { const r = indexedDB.open('investment-device-actual-v1'); r.onsuccess = () => resolve(r.result); r.onerror = () => reject(Error('x')); });
        const records = await new Promise(resolve => { const out = [], tx = db.transaction('snapshots', 'readonly'), c = tx.objectStore('snapshots').openCursor(); c.onsuccess = () => { if (c.result) { out.push(c.result.value); c.result.continue(); } }; tx.oncomplete = () => resolve(out); });
        db.close(); const catalog = await (await fetch('actual-catalog.json')).json();
        return JSON.stringify({records, local: {...localStorage}, session: {...sessionStorage}, backup: await DeviceBackup.read(window, catalog)});
      });
      verify(!CANARY.some(c => dump.includes(c)) && !dump.includes('WORKER_CLOSE') && !dump.includes('HOLDINGS_TAB') && !dump.includes('Coca-Cola'), 'nothing from the Holdings tab or Worker closes is stored or backed up');
      verify(mock.unsafe === 0 && leaked === 0 && errors === 0, 'no unsafe request, console leak or page error');
      verify(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'no horizontal page scroll');

      // Remount with an old native settings snapshot. OFF/sign-out/pending OAuth must win.
      async function pausedMount(enabled, withClient = true) {
        await page.evaluate(async ({value, withClient}) => {
          const saved = await DeviceActual.sheetSettings(window);
          await DeviceActual.sheetSettings(window, {...saved, enabled: value});
          window.__armSettingsRead();
          const host = document.createElement('div'); host.dataset.captureRaceHost = '';
          document.body.append(host); window.__captureRaceHost = host;
          const catalog = await (await fetch('actual-catalog.json')).json();
          window.__captureRaceMount = GoogleSheetQuotes.mount(host, {catalog, locale: 'ko-KR', ...(withClient ? {clientId: InvestmentAppConfig.googleSheetsClientId} : {})});
        }, {value: enabled, withClient});
        await page.waitForFunction(() => window.__settingsReadPaused());
        verify(await page.evaluate(value => window.__settingsReadEnabled() === value, enabled), 'native delayed snapshot matches the stored enabled mode');
      }
      async function finishMount() {
        await page.evaluate(async () => { window.__releaseSettingsRead(); await window.__captureRaceMount; });
      }
      phase = 'DELAYED_SETTINGS_OFF';
      await pausedMount(true);
      await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).setEnabled(false));
      await finishMount();
      verify(await page.evaluate(() => {
        const state = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state();
        return !state.enabled && !state.connected && !window.__captureRaceHost.querySelector('[data-sheet-enabled]').checked;
      }), 'explicit OFF stays off after the old enabled settings return');
      await page.evaluate(() => window.__captureRaceHost.remove());

      phase = 'DELAYED_SETTINGS_SIGN_OUT';
      await page.evaluate(() => { const session = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId); session.setEnabled(true); session.login(); });
      await pausedMount(false);
      await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).disconnect());
      await finishMount();
      verify(await page.evaluate(() => {
        const state = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state();
        return state.enabled && !state.connected && window.__captureRaceHost.querySelector('[data-sheet-enabled]').checked;
      }), 'sign-out clears the grant and keeps the newer enabled mode after the old disabled settings return');
      await page.evaluate(() => window.__captureRaceHost.remove());

      phase = 'DELAYED_SETTINGS_PENDING_GRANT';
      await pausedMount(false);
      await page.evaluate(() => {
        window.__holdGrant = true;
        const session = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId); session.setEnabled(true); session.login();
      });
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().pending), 'OAuth grant is pending before the old read completes');
      await finishMount();
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().pending), 'delayed settings keep the newer pending OAuth request');
      await page.evaluate(() => { window.__holdGrant = false; window.__finishGrant(); });
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().connected), 'the preserved pending grant completes normally');
      await page.evaluate(() => window.__captureRaceHost.remove());

      phase = 'DELAYED_PASTE_ONLY_MOUNT';
      await pausedMount(false, false);
      await page.evaluate(async () => {
        const session = GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId);
        await session.disconnect(); session.setEnabled(true); session.login();
      });
      await finishMount();
      verify(await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).state().connected), 'a stale paste-only mount does not disconnect a newer grant');
      await page.evaluate(() => window.__captureRaceHost.remove());

      phase = 'SIGN_OUT';
      await page.evaluate(() => GoogleSheetQuotes.sessionFor(window, InvestmentAppConfig.googleSheetsClientId).disconnect());
      verify(await page.evaluate(() => HoldingsCapture.get(window) === null && !WorkerQuoteFallback.has(window)), 'RAM holdings and closes cleared on sign-out');
      pass++; console.log('PASS holdings capture, Worker close fallback and outside-scope holdings ' + width); await context.close();
    }
  } catch (error) { fail++; const kind = ['Error', 'TimeoutError', 'AssertionError'].includes(error && error.name) ? error.name : 'TEST_ERROR'; console.log('FAIL holdings capture browser ' + phase + ' · ' + kind + (error && error.safe ? ' · ' + error.safe : '')); }
  finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail); if (fail) process.exitCode = 1;
})();
