'use strict';
// Technical chart workbench (P1-8, P1-9 subset): synthetic bars and a mocked private session only.
// Third-party requests are aborted here; the separate network-recording test records without blocking.
const {chromium} = require('playwright'), assert = require('node:assert/strict');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';

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

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, phase = 'INIT';
  const check = (name, ok) => { if (ok) { pass++; console.log('PASS ' + name); } else { fail++; console.log('FAIL ' + name + ' at ' + phase); } };
  const attrs = page => page.evaluate(() => ({...document.querySelector('[data-chart-workbench]').dataset}));
  const noOverflow = page => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  try {
    for (const width of [390, 1280, 1440]) {
      phase = 'BOOT ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});
      await context.addInitScript(installChartBarsDouble);
      // CHART_TEST_SLOW_FRAMES=ms delays every animation frame like a slow CI runner.
      if (Number(process.env.CHART_TEST_SLOW_FRAMES) > 0) await context.addInitScript(ms => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(t => setTimeout(() => cb(t), ms)); }, Number(process.env.CHART_TEST_SLOW_FRAMES));
      await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(BASE).origin ? route.continue() : route.abort());
      const page = await context.newPage();
      let pageErrors = 0; page.on('pageerror', error => { pageErrors++; if (process.env.CHART_TEST_DEBUG) console.log('DEBUG pageerror ' + error.message + ' ' + String(error.stack).split('\n').slice(0, 4).join(' | ')); });
      await page.goto(BASE + '#technical');
      const bench = page.locator('[data-chart-workbench]');
      await bench.waitFor();
      check('empty state has no data, no renderer and a judgement code ' + width, (await attrs(page)).source === 'none' && (await page.locator('[data-cw-judgement]').getAttribute('data-code')) === 'NO_DATA' && await page.locator('script[data-chart-renderer-vendor]').count() === 0);

      phase = 'SYNTHETIC ' + width;
      await page.locator('[data-cw-synthetic]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'synthetic' && document.querySelector('[data-chart-workbench]').dataset.renderer !== 'none');
      const first = await attrs(page);
      check('long mode opens weekly structure first ' + width, first.mode === 'long' && first.timeframe === 'weekly' && Number(first.provisionalCount) >= 1);
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.barCount === '320');
      let a = await attrs(page);
      const label = await page.locator('[data-synthetic-label]').textContent();
      check('synthetic preview is labelled and never judged ' + width, a.source === 'synthetic' && label === '합성 자료 · 미리보기 · 실데이터 검증 아님' && (await page.locator('[data-cw-judgement]').getAttribute('data-code')) === 'SYNTHETIC_PREVIEW');
      check('lightweight charts renders candles and volume with provisional bar marked ' + width, a.renderer === 'lwc' && a.provisionalCount === '1' && Number(await page.locator('[data-cw-chart]').getAttribute('data-panes')) >= 2 && await page.locator('[data-cw-chart] canvas').count() > 0);
      check('no logo, no injected style and no CSP violation ' + width, await page.locator('[data-cw-chart] a').count() === 0 && await page.evaluate(() => document.querySelectorAll('style').length) === 0 && await page.evaluate(() => window.__csp) === 0);
      const vendor = await page.evaluate(() => { const s = document.querySelector('script[data-chart-renderer-vendor]'); return s && {src: s.getAttribute('src'), integrity: s.integrity, version: window.LightweightCharts.version()}; });
      check('vendored 5.2.1 file loads from this site with integrity ' + width, vendor && vendor.src === 'lightweight-charts-5.2.1.standalone.js' && vendor.integrity.startsWith('sha384-') && vendor.version === '5.2.1');
      check('no horizontal overflow with the chart ' + width, await noOverflow(page));

      phase = 'NOTICE ' + width;
      const notice = await page.evaluate(async () => ({shown: document.querySelector('[data-cw-notice-text]').textContent, file: (await (await fetch('lightweight-charts-5.2.1.NOTICE.txt')).text()).trim().split('\n').join(' '),
        link: [...document.querySelectorAll('[data-cw-attribution-link]')].map(x => [x.href, x.rel]), files: await Promise.all(['lightweight-charts-5.2.1.LICENSE.txt', 'third-party-notices.txt'].map(async f => (await fetch(f)).status))}));
      check('NOTICE text and plain TradingView link are shown, licence files are served ' + width, notice.shown === notice.file && notice.link.length === 1 && notice.link[0][0] === 'https://www.tradingview.com/' && notice.link[0][1] === 'noopener noreferrer' && notice.files.every(s => s === 200));

      phase = 'ZOOM ' + width;
      const chart = page.locator('[data-cw-chart]');
      const place = async () => { await page.evaluate(() => document.querySelector('[data-cw-readout]').scrollIntoView({block: 'start'})); return chart.boundingBox(); };
      let box;
      const before = await attrs(page);
      await page.locator('[data-cw-zoom="in"]').click();
      await page.waitForFunction(from => document.querySelector('[data-chart-workbench]').dataset.visibleFrom > from, before.visibleFrom);
      const zoomed = await attrs(page);
      box = await place();
      await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.3);
      await page.mouse.down(); await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.3, {steps: 8}); await page.mouse.up();
      await page.waitForFunction(from => document.querySelector('[data-chart-workbench]').dataset.visibleFrom < from, zoomed.visibleFrom);
      check('zoom and pan change the visible range ' + width, zoomed.visibleFrom > before.visibleFrom && (await attrs(page)).visibleFrom < zoomed.visibleFrom);

      phase = 'CROSSHAIR ' + width;
      box = await place();
      await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.35);
      await page.waitForFunction(() => document.querySelector('[data-cw-readout]').dataset.tracking === 'pointer');
      const readout = await page.locator('[data-cw-readout]').textContent();
      check('crosshair pins date, OHLC, volume and status ' + width, /^\d{4}-\d{2}-\d{2} · (시가 .+|OHLC 결측) · 거래량 .+ · (확정|잠정)$/.test(readout));
      if (process.env.CHART_TEST_DEBUG) console.log('DEBUG readout ' + readout);

      phase = 'KEYBOARD ' + width;
      await chart.focus();
      await page.keyboard.press('End');
      await page.waitForFunction(() => /잠정$/.test(document.querySelector('[data-cw-live]').textContent));
      const endText = await page.locator('[data-cw-live]').textContent();
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('Shift+ArrowLeft');
      const liveAfter = await page.locator('[data-cw-live]').textContent(), index = await page.locator('[data-cw-readout]').getAttribute('data-index');
      check('keyboard moves one and ten bars and aria-live reads the bar ' + width, endText.startsWith('2026-03-27') && index === '308' && /확정$/.test(liveAfter) && (await page.locator('[data-cw-live]').getAttribute('aria-live')) === 'polite');
      const role = await chart.evaluate(el => [el.getAttribute('role'), el.getAttribute('aria-label')]);
      check('chart container is a labelled group, not an application ' + width, role[0] === 'group' && /SYNTH · 일봉 · 보이는 기간 \d{4}-\d{2}-\d{2} ~ \d{4}-\d{2}-\d{2} · 선택 패턴 없음/.test(role[1]));
      await page.keyboard.press('Escape');

      phase = 'MEASURE ' + width;
      await page.locator('[data-cw-measure]').click();
      box = await place();
      await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.3);
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.measureState === 'first-point');
      await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.45);
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.measureState === 'done');
      const measure = await page.locator('[data-cw-measure-out]').textContent();
      check('measure shows price difference, percent, bars and days, not a signal ' + width, /가격 차 [+-]?[\d.,]+ · [+-]?[\d.,]+% · \d+봉 · \d+일 · 측정 표시만 · 신호 아님$/.test(measure));
      await page.locator('[data-cw-measure]').click();

      phase = 'WEEKLY ' + width;
      const daily = await attrs(page);
      await page.locator('[data-cw-timeframe="weekly"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'weekly');
      const weekly = await attrs(page), days = (x, y) => (Date.parse(y) - Date.parse(x)) / 86400000;
      check('daily to weekly keeps the visible date range ' + width, weekly.visibleFrom <= daily.visibleFrom && days(weekly.visibleFrom, daily.visibleFrom) < 7 && weekly.visibleTo <= daily.visibleTo && days(weekly.visibleTo, daily.visibleTo) < 7 && Number(weekly.barCount) < 80);
      check('weekly view draws no indicator and says why ' + width, (await page.locator('[data-cw-chart]').getAttribute('data-panes')) === '2' && (await page.locator('[data-cw-indicator-note]').textContent()).includes('TA-G3'));
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily');
      const back = await attrs(page);
      check('weekly to daily returns the first and last sessions of those weeks ' + width, back.visibleFrom <= daily.visibleFrom && back.visibleFrom >= weekly.visibleFrom && back.visibleTo >= daily.visibleTo && days(daily.visibleTo, back.visibleTo) < 7);

      phase = 'SETTINGS ' + width;
      await page.locator('[data-cw-settings] summary').click();
      for (const key of ['RSI', 'MACD', 'ATR', 'BOLL']) await page.locator('[data-cw-indicator="' + key + '"]').check();
      await page.waitForFunction(() => document.querySelector('[data-cw-chart]').dataset.panes === '5');
      const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('investment.web.v1.chart-display-settings')));
      check('indicator toggles add panes and store display toggles only ' + width, stored.schema === 'chart-display-settings/1' && stored.indicators.RSI && stored.indicators.MACD && stored.indicators.ATR && Object.keys(stored).sort().join() === 'indicators,mode,patterns,renderer,schema' && await page.locator('[data-cw-pattern]').count() === 3);
      check('no overflow with indicator panes ' + width, await noOverflow(page));

      phase = 'SVG ' + width;
      await page.locator('[data-cw-renderer="svg"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'svg');
      check('SVG fallback draws the existing chart and shows its limits ' + width, await page.locator('[data-cw-chart] svg[data-history-chart]').count() === 1 && await page.locator('[data-cw-limits]').isVisible() && await page.locator('[data-cw-measure]').isDisabled() && await noOverflow(page));

      phase = 'RELOAD ' + width;
      await page.reload(); await bench.waitFor();
      await page.locator('[data-cw-settings] summary').click();
      check('device settings survive reload ' + width, await page.locator('[data-cw-indicator="RSI"]').isChecked() && (await page.locator('[data-cw-renderer="svg"]').getAttribute('aria-pressed')) === 'true');
      await page.locator('[data-cw-renderer="lwc"]').click();
      await page.locator('[data-cw-mode="swing"]').click();
      check('swing mode keeps a scenario slot with no drawing ' + width, (await attrs(page)).mode === 'swing' && (await page.locator('[data-cw-swing-slot]').textContent()).includes('주문 아님 · 가정 계산'));
      await page.locator('[data-cw-mode="long"]').click();
      check('long mode is shown beside QGV and changes nothing ' + width, (await page.locator('[data-cw-mode-panel]').textContent()).includes('QGV·TARGET·플레이북을 바꾸지 않고') && await page.locator('[data-cw-qgv-link]').count() === 1);
      const words = await bench.textContent();
      check('no buy/sell, probability, win-rate or score wording ' + width, !/매수|매도|확률|승률|점수|신뢰도/.test(words));
      check('no page errors ' + width, pageErrors === 0 && await page.evaluate(() => window.__csp) === 0);
      await context.close();
    }

    phase = 'TOUCH';
    {
      const context = await browser.newContext({viewport: {width: 390, height: 844}, hasTouch: true, isMobile: true, deviceScaleFactor: 2, serviceWorkers: 'block'});
      await context.addInitScript(installChartBarsDouble);
      // CHART_TEST_SLOW_FRAMES=ms delays every animation frame like a slow CI runner.
      if (Number(process.env.CHART_TEST_SLOW_FRAMES) > 0) await context.addInitScript(ms => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(t => setTimeout(() => cb(t), ms)); }, Number(process.env.CHART_TEST_SLOW_FRAMES));
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(BASE).origin ? route.continue() : route.abort());
      const page = await context.newPage();
      await page.goto(BASE + '#technical');
      await page.locator('[data-cw-synthetic]').tap();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'synthetic' && document.querySelector('[data-chart-workbench]').dataset.barCount !== '0');
      const chart = page.locator('[data-cw-chart]'); await chart.scrollIntoViewIfNeeded();
      const box = await chart.boundingBox(), cdp = await context.newCDPSession(page), x = box.x + box.width * 0.5, y = box.y + box.height * 0.3;
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x, y}]});
      await page.waitForTimeout(900);
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x: x + 30, y}]});
      await page.waitForTimeout(200);
      const tracking = await page.locator('[data-cw-readout]').getAttribute('data-tracking'), text = await page.locator('[data-cw-readout]').textContent();
      await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []});
      check('long-press tracks bars in the pinned panel on touch', tracking === 'touch' && /^\d{4}-\d{2}-\d{2}( \(\d{4}-\d{2}-\d{2} ~ \d{4}-\d{2}-\d{2}\))? · .+ · (확정|잠정)$/.test(text));
      if (process.env.CHART_TEST_DEBUG) console.log('DEBUG touch ' + tracking + ' ' + text);
      check('no overflow on a touch phone', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await context.close();
    }

    phase = 'DEVICE';
    {
      const context = await browser.newContext({viewport: {width: 390, height: 900}, serviceWorkers: 'block'});
      // Decision 2026-10-23 (TA G2): the chart range is ACTUAL ∪ watchlist ∪ TARGET v1 candidates; this device watches NVIDIA (issuer key).
      await context.addInitScript(()=>{if(localStorage.getItem('investment.web.v1.personal')===null)localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['sec:0001045810'],groups:[]}));});
      await context.addInitScript(installChartBarsDouble);
      // CHART_TEST_SLOW_FRAMES=ms delays every animation frame like a slow CI runner.
      if (Number(process.env.CHART_TEST_SLOW_FRAMES) > 0) await context.addInitScript(ms => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(t => setTimeout(() => cb(t), ms)); }, Number(process.env.CHART_TEST_SLOW_FRAMES));
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(BASE).origin ? route.continue() : route.abort());
      const page = await context.newPage();
      await page.goto(BASE + '#settings'); await page.locator('#device-backup-export').waitFor();
      await page.evaluate(async () => {
        await DeviceActual.sheetSettings(window, {schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22'});
        localStorage.setItem('investment.web.v1.private-history-origin', InvestmentAppConfig.privateHistoryWorkerOrigin);
        let connected = true, epoch = 1; const listeners = new Set(); window.__chartLogout = () => { connected = false; epoch++; listeners.forEach(f => f()); };
        const session = {state: () => ({enabled: true, connected}), revision: () => epoch, setEnabled() {}, subscribe: f => { listeners.add(f); return () => listeners.delete(f); }, async fetchHistory(origin, symbol, range) {
          const start = Date.UTC(2025, 0, 6) / 1000; const bars = []; let day = 0;
          while (bars.length < 260) { const t = start + day * 86400; const wd = new Date(t * 1000).getUTCDay(); if (wd >= 1 && wd <= 5) bars.push({timestamp: t + 52200, open: 50 + bars.length * 0.1, high: 52 + bars.length * 0.1, low: 49 + bars.length * 0.1, close: 51 + bars.length * 0.1, adjusted_close: null, volume: 1000, session_status: 'COMPLETE'}); day++; }
          return {schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: 'USD', exchange: 'NMS', timezone: 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: new Date().toISOString(), bars};
        }};
        window.GoogleSheetQuotes = {...GoogleSheetQuotes, sessionFor: () => session}; location.hash = 'technical/nvda';
      });
      await page.locator('[data-private-history] [data-history-action="fetch"]:enabled').waitFor();
      check('workbench does not read prices by itself', (await attrs(page)).source === 'none');
      await page.locator('[data-private-history] [data-history-action="fetch"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'device');
      let a = await attrs(page);
      check('device bars are never judged without price-basis continuity', (await page.locator('[data-cw-judgement]').getAttribute('data-code')) === 'PRICE_BASIS_CONTINUITY_UNCONFIRMED' && await page.locator('[data-synthetic-label]').count() === 0);
      check('long mode opens weekly structure first when weekly bars exist', a.timeframe === 'weekly' && a.mode === 'long' && a.barCount === '52');
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily');
      check('all device daily bars reach the renderer in RAM', (await attrs(page)).barCount === '260');
      check('existing SVG price chart still renders beside the workbench', await page.locator('[data-private-history] [data-candle-index]').count() === 260);
      const stored = await page.evaluate(() => Object.keys(localStorage).map(k => k + '=' + localStorage.getItem(k)).join('\n'));
      check('no price value reaches device storage', !/51\.1|52\.1|"close"|"open"/.test(stored));
      await page.evaluate(() => window.__chartLogout());
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'none');
      check('sign-out clears workbench bars from RAM', (await attrs(page)).barCount === '0');
      await context.close();
    }
  } catch (error) {
    fail++; console.log('FAIL chart workbench ' + phase + ' ' + (error && error.name || 'Error'));
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  if (fail) process.exitCode = 1;
})();
