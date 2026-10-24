'use strict';
// Network-recording test for the self-hosted chart renderer (design §4.5, P1-7).
// Nothing is routed or aborted: every request is recorded from Playwright (page + context, which
// includes service workers) and from CDP Network (beacons, prefetch, WebSocket). Synthetic bars and a
// mocked private session only. Output holds counts and host names only, never URLs or values.
const {chromium} = require('playwright');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const ORIGIN = new URL(BASE).origin;
const SYMBOL = 'NVDA', PRICE_MARK = '4321.9';   // test symbol and the leading digits of every test price

function installChartBarsDouble() {
  // Test double for the lane B1 ChartBars API (chart-bars.js: normalize -> weekly, rule W1), used only when the
  // real module is absent so the real one is exercised once it ships. Product code never aggregates bars.
  if (window.ChartBars) { window.__chartBarsDouble = false; return; }
  window.__chartBarsDouble = true;
  window.ChartBars = {
    normalize(history) { return {timeframe: 'D', bars: history.bars.map(raw => ({...raw, session_date: raw.session_date || new Date(raw.timestamp * 1000).toISOString().slice(0, 10)}))}; },
    weekly(series) {
      const groups = new Map();
      for (const b of series.bars) {
        const d = new Date(b.session_date + 'T00:00:00Z'), monday = new Date(d.getTime() - ((d.getUTCDay() + 6) % 7) * 86400000).toISOString().slice(0, 10);
        if (!groups.has(monday)) groups.set(monday, []);
        groups.get(monday).push(b);
      }
      return {timeframe: 'W', bars: [...groups].map(([week, list]) => {
        const ok = list.every(b => b.open !== null), vol = list.every(b => b.volume !== null);
        return {week_start: week, first_session: list[0].session_date, last_session: list.at(-1).session_date, open: ok ? list[0].open : null, high: ok ? Math.max(...list.map(b => b.high)) : null, low: ok ? Math.min(...list.map(b => b.low)) : null, close: ok ? list.at(-1).close : null, volume: vol ? list.reduce((a, b) => a + b.volume, 0) : null, state: list.every(b => b.session_status === 'COMPLETE') && list.length === 5 ? 'COMPLETE' : 'PROVISIONAL'};
      })};
    }
  };
}

async function recorder(context, page) {
  const log = [], ws = [];
  let phase = 'boot';
  const add = (via, url, headers, body) => log.push({phase, via, url: String(url || ''), headers: JSON.stringify(headers || {}), body: String(body || '')});
  context.on('request', request => add('context', request.url(), request.headers(), request.postData()));
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  cdp.on('Network.requestWillBeSent', e => add('cdp', e.request.url, e.request.headers, e.request.postData));
  cdp.on('Network.requestWillBeSentExtraInfo', e => add('cdp-extra', '', e.headers, ''));
  cdp.on('Network.webSocketCreated', e => { ws.push(phase); add('cdp-ws', e.url, {}, ''); });
  await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
  let cspConsole = 0;
  page.on('console', m => { if (m.text().includes('Content Security Policy')) cspConsole++; });
  return {
    set phase(value) { phase = value; },
    log, ws, csp: async () => cspConsole + await page.evaluate(() => window.__csp || 0),
    thirdParty: phases => log.filter(r => r.url && phases.includes(r.phase) && !r.url.startsWith(ORIGIN) && !/^(data|blob|about|chrome-extension):/.test(r.url)),
    hosts: rows => [...new Set(rows.map(r => { try { return new URL(r.url).host; } catch (_) { return 'invalid'; } }))].sort()
  };
}

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, step = 'INIT';
  const check = (name, ok) => { if (ok) { pass++; console.log('PASS ' + name); } else { fail++; console.log('FAIL ' + name + ' at ' + step); } };
  const chartPhases = ['load', 'interact', 'touch'];
  try {
    for (const width of [390, 1440]) {
      step = 'RECORD ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'allow'});
      // Decision 2026-10-23 (TA G2): the chart range is ACTUAL ∪ watchlist ∪ TARGET v1 candidates; this device watches NVIDIA (issuer key).
      await context.addInitScript(()=>{if(localStorage.getItem('investment.web.v1.personal')===null)localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['sec:0001045810'],groups:[]}));});
      await context.addInitScript(installChartBarsDouble);
      const page = await context.newPage(), rec = await recorder(context, page);
      await page.goto(BASE + '#settings'); await page.locator('#device-backup-export').waitFor();
      await page.evaluate(async ({symbolMark}) => {
        await DeviceActual.sheetSettings(window, {schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22'});
        localStorage.setItem('investment.web.v1.private-history-origin', InvestmentAppConfig.privateHistoryWorkerOrigin);
        const session = {state: () => ({enabled: true, connected: true}), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchHistory(origin, symbol, range) {
          const start = Date.UTC(2025, 0, 6) / 1000, bars = []; let day = 0;
          while (bars.length < 300) { const t = start + day * 86400, wd = new Date(t * 1000).getUTCDay(); if (wd >= 1 && wd <= 5) { const p = Number(symbolMark) + 0.00001 * bars.length; bars.push({timestamp: t + 52200, open: p, high: p + 0.0005, low: p - 0.0005, close: p + 0.0002, adjusted_close: null, volume: 1000 + bars.length, session_status: bars.length === 299 ? 'IN_PROGRESS' : 'COMPLETE'}); } day++; }
          return {schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: 'USD', exchange: 'NMS', timezone: 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: new Date().toISOString(), bars};
        }};
        window.GoogleSheetQuotes = {...GoogleSheetQuotes, sessionFor: () => session}; location.hash = 'technical/nvda';
      }, {symbolMark: PRICE_MARK + '8'});
      await page.locator('[data-private-history] [data-history-action="fetch"]:enabled').waitFor();

      rec.phase = 'load';
      await page.locator('[data-private-history] [data-history-action="fetch"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'device' && document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc');

      rec.phase = 'interact';
      const bench = page.locator('[data-chart-workbench]'), chart = page.locator('[data-cw-chart]');
      const place = async () => { await page.evaluate(() => document.querySelector('[data-cw-readout]').scrollIntoView({block: 'start'})); return chart.boundingBox(); };
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily');
      let box = await place();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height * 0.3);
      await page.mouse.wheel(0, -400);
      await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.3, {steps: 6}); await page.mouse.up();
      await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4);
      await page.locator('[data-cw-measure]').click();
      box = await place();
      await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.3);
      await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.4);
      const done = await bench.evaluate(el => el.dataset.measureState);
      await chart.focus();
      for (const key of ['End', 'ArrowLeft', 'Shift+ArrowLeft', '+', '-', 'Home', 'm', 'Escape']) await page.keyboard.press(key);
      await page.locator('[data-cw-timeframe="weekly"]').click();
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.locator('[data-cw-settings] summary').click();
      for (const key of ['RSI', 'MACD', 'ATR', 'BOLL', 'EMA']) await page.locator('[data-cw-indicator="' + key + '"]').check();
      await page.locator('[data-cw-renderer="svg"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'svg');
      await page.locator('[data-cw-renderer="lwc"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc');
      await page.locator('[data-cw-mode="swing"]').click();
      await page.locator('[data-cw-synthetic]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'synthetic');
      await page.waitForTimeout(1500);

      rec.phase = 'after';
      const third = rec.thirdParty(['boot', ...chartPhases]), chartReq = rec.log.filter(r => chartPhases.includes(r.phase) && r.url);
      const carries = (rows, mark) => rows.filter(r => (r.url + r.headers + r.body).includes(mark)).length;
      check('interactions ran (measure, keyboard, weekly, settings, SVG) ' + width, done === 'done');
      check('zero third-party requests while the chart loads and is used ' + width, third.length === 0);
      check('no request carries a test price string ' + width, carries(rec.log, PRICE_MARK) === 0);
      check('no chart-phase request carries the test symbol ' + width, carries(chartReq, SYMBOL) === 0 && carries(chartReq, SYMBOL.toLowerCase()) === 0);
      check('no WebSocket and no beacon-like request ' + width, rec.ws.length === 0 && rec.log.every(r => !/beacon|collect|analytics|utm_/i.test(r.url)));
      check('no CSP violation ' + width, await rec.csp() === 0);
      const sameOrigin = rec.hosts(chartReq), worker = rec.log.filter(r => /workers\.dev/.test(r.url)).length;
      check('chart-phase requests stay on this site; private Worker reads are classified separately ' + width, sameOrigin.every(h => h === new URL(BASE).host) && worker === 0);
      console.log('RECORD width=' + width + ' requests=' + rec.log.filter(r => r.url).length + ' chart_phase=' + chartReq.length + ' third_party=' + third.length + ' worker=' + worker + ' hosts=' + JSON.stringify(rec.hosts(rec.log.filter(r => r.url))));
      await context.close();
    }

    step = 'TOUCH';
    {
      const context = await browser.newContext({viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true, serviceWorkers: 'allow'});
      await context.addInitScript(installChartBarsDouble);
      const page = await context.newPage(), rec = await recorder(context, page);
      await page.goto(BASE + '#technical'); await page.locator('[data-chart-workbench]').waitFor();
      rec.phase = 'touch';
      await page.locator('[data-cw-synthetic]').tap();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc');
      const chart = page.locator('[data-cw-chart]'); await chart.scrollIntoViewIfNeeded();
      const box = await chart.boundingBox(), cdp = await context.newCDPSession(page), x = box.x + box.width / 2, y = box.y + box.height * 0.3;
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y}]}); await page.waitForTimeout(900);
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x: x + 40, y}]}); await page.waitForTimeout(200);
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y}]});
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x: x - 80, y}]});
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
      await page.waitForTimeout(1000);
      const tracked = await page.locator('[data-cw-readout]').getAttribute('data-tracking');
      check('touch long-press and drag ran', tracked !== 'off');
      check('zero third-party requests during touch use', rec.thirdParty(['boot', 'touch']).length === 0 && await rec.csp() === 0);
      await context.close();
    }

    step = 'CONTROL';
    {
      // Control run: the existing TradingView widget, switched on, must be caught by the same recorder.
      const context = await browser.newContext({viewport: {width: 1280, height: 900}, serviceWorkers: 'allow'});
      await context.addInitScript(() => { try { localStorage.setItem('investment.web.v1.tradingview-widgets', 'on'); } catch (_) {} });
      // The #technical picker opens on the first company of the device range (decision 2026-10-23); this device watches NVIDIA.
      await context.addInitScript(() => { try { if (localStorage.getItem('investment.web.v1.personal') === null) localStorage.setItem('investment.web.v1.personal', JSON.stringify({version: 1, interests: ['sec:0001045810'], groups: []})); } catch (_) {} });
      // Recorded at creation, then answered locally so the control never sends real third-party traffic.
      await context.route(url => !String(url).startsWith(ORIGIN), route => route.fulfill({status: 200, contentType: 'text/html', body: '<!doctype html><title>stub</title>'}));
      const page = await context.newPage(), rec = await recorder(context, page);
      await page.goto(BASE + '#technical'); await page.locator('[data-chart-workbench]').waitFor();
      await page.waitForTimeout(3000);
      const widget = rec.thirdParty(['boot']).filter(r => /tradingview-widget\.com|tradingview\.com/.test(r.url));
      check('control: recorder catches the TradingView widget when it is switched on', widget.length > 0);
      console.log('CONTROL widget_requests=' + widget.length + ' hosts=' + JSON.stringify(rec.hosts(widget)));
      await context.close();
    }
  } catch (error) {
    fail++; console.log('FAIL network recording ' + step + ' ' + (error && error.name || 'Error'));
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  if (fail) process.exitCode = 1;
})();
