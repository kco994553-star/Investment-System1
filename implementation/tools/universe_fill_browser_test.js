/* "Universe 탭 채우기" for an existing sheet whose Universe tab has only the header. Google Sheets is mocked; no values are published. */
'use strict';
const {chromium} = require('playwright'); const assert = require('node:assert/strict');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/', EXISTING = 'u'.repeat(30), TOKEN = ['synthetic', 'universe', 'ram'].join('-');
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH}); let pass = 0, fail = 0, phase = 'INIT';
  try {
    for (const width of [390, 1440]) {
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'}), page = await context.newPage(); page.setDefaultTimeout(10000);
      const mock = {universe: 'header', puts: [], unsafe: 0, codesServed: 0}; let errors = 0; page.on('pageerror', () => errors++);
      await page.addInitScript(({id, token}) => {
        localStorage.setItem('investment.web.v1.unified-sheet-source', id);
        window.google = {accounts: {oauth2: {initTokenClient(config) { return {requestAccessToken() { config.callback({access_token: token, expires_in: 3600, scope: 'https://www.googleapis.com/auth/drive.file email'}); }}; }, revoke(_, done) { done({}); }}}};
      }, {id: EXISTING, token: TOKEN});
      await page.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (url.origin === new URL(BASE).origin) { if (url.pathname.endsWith('/universe-codes.json')) mock.codesServed++; return route.continue(); }
        if (url.origin !== 'https://sheets.googleapis.com') { mock.unsafe++; return route.abort(); }
        const cors = {'access-control-allow-origin': new URL(BASE).origin, 'access-control-allow-headers': 'Authorization, Content-Type', 'access-control-allow-methods': 'GET, POST, PUT'};
        if (request.method() === 'OPTIONS') return route.fulfill({status: 204, headers: cors});
        if (request.headers().authorization !== 'Bearer ' + TOKEN || !url.pathname.includes(EXISTING)) mock.unsafe++;
        if (request.method() === 'PUT') { mock.puts.push({path: decodeURIComponent(url.pathname), query: url.search, body: JSON.parse(request.postData())}); return route.fulfill({headers: cors, contentType: 'application/json', body: '{"updatedRows":1}'}); }
        if (request.method() !== 'GET') { mock.unsafe++; return route.abort(); }
        if (url.pathname.includes('/values/')) {
          const range = decodeURIComponent(url.pathname.split('/values/')[1]);
          if (range === "'Universe'!A1:C1025") {
            const values = mock.universe === 'header' ? [['code', 'marketcap', 'price']] : mock.universe === 'filled' ? [['code', 'marketcap', 'price'], ['NYSE:MMM', '', '']] : [['symbol', 'marketcap', 'price']];
            return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify({values})});
          }
          const headers = {"'Quotes'!A1:C1": ['code', 'price', 'tradetime'], "'Trades'!A1:D1": ['date', 'symbol', 'b/s', 'quantity'], "'Universe'!A1:C1": ['code', 'marketcap', 'price']};
          if (!headers[range]) { mock.unsafe++; return route.abort(); }
          return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify({values: [headers[range]]})});
        }
        return route.fulfill({headers: cors, contentType: 'application/json', body: JSON.stringify({sheets: ['Quotes', 'Trades', 'Universe'].map(title => ({properties: {title}}))})});
      });
      phase = 'SIGN_IN'; await page.goto(BASE + '#settings'); const root = page.locator('[data-google-first-setup]');
      await root.locator('[data-setup-action="login"]').click(); if (await root.locator('[data-setup-action="login"]').isVisible()) await root.locator('[data-setup-action="login"]').click();
      const fill = root.locator('[data-setup-action="fill-universe"]'); await page.locator('[data-setup-action="fill-universe"]:enabled').waitFor();
      phase = 'FILL'; await fill.click(); await root.locator('[data-setup-status]').filter({hasText: 'UNIVERSE_FILLED'}).waitFor();
      const codes = await (await page.request.get(BASE + 'universe-codes.json')).json();
      assert.equal(mock.puts.length, 1); const put = mock.puts[0];
      assert.ok(put.path.endsWith("/values/'Universe'!A2:C" + (codes.codes.length + 1)) && put.query === '?valueInputOption=USER_ENTERED');
      assert.equal(put.body.values.length, codes.codes.length); assert.ok(mock.codesServed >= 1);
      assert.deepEqual(put.body.values[0], [codes.codes[0], '=IFERROR(GOOGLEFINANCE(A2,"marketcap"),"")', '=IFERROR(GOOGLEFINANCE(A2,"price"),"")']);
      const n = codes.codes.length + 1; assert.deepEqual(put.body.values.at(-1), [codes.codes.at(-1), '=IFERROR(GOOGLEFINANCE(A' + n + ',"marketcap"),"")', '=IFERROR(GOOGLEFINANCE(A' + n + ',"price"),"")']);
      phase = 'NOT_EMPTY'; mock.universe = 'filled'; await fill.click(); await root.locator('[data-setup-status]').filter({hasText: 'UNIVERSE_TAB_NOT_EMPTY'}).waitFor(); assert.equal(mock.puts.length, 1);
      phase = 'HEADER'; mock.universe = 'broken'; await fill.click(); await root.locator('[data-setup-status]').filter({hasText: 'UNIVERSE_HEADER_INVALID'}).waitFor(); assert.equal(mock.puts.length, 1);
      assert.equal(mock.unsafe, 0); assert.equal(errors, 0); assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      pass++; console.log('PASS universe tab fill for a header-only existing sheet ' + width); await context.close();
    }
  } catch (_) { fail++; console.log('FAIL universe fill browser ' + phase); } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail); if (fail) process.exitCode = 1;
})();
