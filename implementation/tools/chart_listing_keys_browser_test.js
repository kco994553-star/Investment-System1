'use strict';
// IA-7 + owner decision 2026-10-23 (TARGET v0 결합 해소): chart drawings are keyed by the Listing (Universe code EXCHANGE:SYMBOL).
// A chart opened for a listing shows the objects written before the decision under the provider ticker (read, never rewritten or
// removed) and the new ones under the listing; a new object is stored with the listing key. Synthetic bars only; no request.
const {chromium} = require('playwright');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const KEY = 'investment.web.v1.chart-user-objects';
const note = (id, symbol) => ({schema: 'chart-annotation/1', id, kind: 'MEMO', symbol, interval: 'D', price_basis: 'RAW_CLOSE', author: 'USER', points: [{time: '2026-01-05', price: 100}], text: 'synthetic ' + id, created_at: '2026-01-05T00:00:00.000Z', updated_at: '2026-01-05T00:00:00.000Z'});
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, phase = 'INIT';
  const check = (name, ok) => { if (ok) { pass++; console.log('PASS ' + name); } else { fail++; console.log('FAIL ' + name + ' at ' + phase); } };
  try {
    for (const width of [390, 1280]) {
      phase = 'OPEN ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'}), page = await context.newPage();
      let errors = 0, history = 0; page.on('pageerror', () => errors++); page.on('request', r => { if (/\/history\?|workers\.dev/.test(r.url())) history++; });
      const seeded = [note('u-legacy01', 'SYK'), note('u-listing1', 'NYSE:SYK'), note('u-other001', 'AAPL')];
      await context.addInitScript(([k, v]) => { if (localStorage.getItem(k) === null) localStorage.setItem(k, v); }, [KEY, JSON.stringify({schema: 'chart-user-objects/1', items: seeded})]);
      await page.goto(BASE + '#technical');
      await page.waitForFunction(() => window.ChartWorkbench && document.querySelector('#technical-workbench [data-chart-workbench]'));
      check('validator accepts listing and legacy ticker keys ' + width, await page.evaluate(([a, b]) => ChartWorkbench.validUserObject(a) && ChartWorkbench.validUserObject(b) && !ChartWorkbench.validUserObject({...a, symbol: 'nyse:syk'}) && !ChartWorkbench.validUserObject({...a, symbol: 'NYSE:'}), [seeded[1], seeded[0]]));
      phase = 'MOUNT ' + width;
      await page.evaluate(() => {
        const host = document.createElement('div'); host.id = 'listing-key-bench'; document.querySelector('#content').append(host);
        const bench = ChartWorkbench.mount(host, {locale: 'ko-KR'}), data = ChartWorkbench.syntheticHistory();
        window.__bench = bench; return bench.update({symbol: 'SYK', listing: 'NYSE:SYK', provider: 'SYNTHETIC', timezone: 'UTC', currency: 'USD', readAt: '2026-01-06T00:00:00.000Z', bars: data.bars});
      });
      const bench = page.locator('#listing-key-bench [data-chart-workbench]');
      await page.waitForFunction(() => document.querySelector('#listing-key-bench [data-chart-workbench]')?.dataset.source === 'device');
      await page.locator('#listing-key-bench [data-cw-timeframe="daily"]').click();
      const attr = name => bench.getAttribute(name);
      check('legacy ticker object and listing object both shown for the listing ' + width, await attr('data-user-count') === '2' && await attr('data-user-total') === '3');
      phase = 'DRAW ' + width;
      await page.locator('#listing-key-bench [data-user-tool="MEMO"]').click();
      await page.evaluate(() => document.querySelector('#listing-key-bench [data-cw-readout]').scrollIntoView({block: 'start'}));
      const box = await page.locator('#listing-key-bench [data-cw-chart]').boundingBox();
      await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.3); await page.waitForTimeout(200);
      const items = await page.evaluate(k => JSON.parse(localStorage.getItem(k)).items, KEY);
      const added = items.filter(o => !seeded.some(s => s.id === o.id));
      check('a new drawing is stored with the listing key ' + width, added.length === 1 && added[0].symbol === 'NYSE:SYK');
      check('old objects are kept unchanged ' + width, seeded.every(s => JSON.stringify(items.find(o => o.id === s.id)) === JSON.stringify(s)));
      check('no price request, no errors, no overflow ' + width, history === 0 && errors === 0 && await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await context.close();
    }
  } catch (error) { fail++; console.log('FAIL chart-listing-keys at ' + phase + ' ' + String(error && error.message || '').slice(0, 160)); }
  finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail); if (fail) process.exitCode = 1;
})();
