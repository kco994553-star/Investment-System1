'use strict';
// Pattern screen (functional hierarchy 3.1 / 3.2): data input -> ChartBars -> PatternEngine -> PatternHistory -> chart + cards.
// Functional verification with synthetic bars and a mocked private session only. Not an analysis of real prices.
const {chromium} = require('playwright');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const ORIGIN = new URL(BASE).origin;

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, phase = 'INIT';
  const check = (name, ok) => { if (ok) { pass++; console.log('PASS ' + name); } else { fail++; console.log('FAIL ' + name + ' at ' + phase); } };
  const attrs = page => page.evaluate(() => ({...document.querySelector('[data-chart-workbench]').dataset}));
  const noOverflow = page => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  const open = async (context, hash) => {
    const methods = [], page = await context.newPage();
    page.on('request', r => methods.push(r.method()));
    // Optional slow-runner reproduction: CHART_TEST_CPU_THROTTLE=4..6 slows the page CPU like a loaded CI runner.
    // CHART_TEST_SLOW_FRAMES=ms delays every animation frame like a slow CI runner (frames arrive late, not lost).
    if (Number(process.env.CHART_TEST_SLOW_FRAMES) > 0) await page.addInitScript(ms => { const raf = window.requestAnimationFrame.bind(window); window.requestAnimationFrame = cb => raf(t => setTimeout(() => cb(t), ms)); }, Number(process.env.CHART_TEST_SLOW_FRAMES));
    if (Number(process.env.CHART_TEST_CPU_THROTTLE) > 1) await (await context.newCDPSession(page)).send('Emulation.setCPUThrottlingRate', {rate: Number(process.env.CHART_TEST_CPU_THROTTLE)});
    await page.goto(BASE + hash);
    return {page, methods};
  };
  const banned = /매수|매도|확률|승률|점수|신뢰도|probability|win rate/i;
  try {
    for (const width of [390, 1280]) {
      phase = 'SYNTHETIC ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});
      await context.route('**/*', route => (route.request().url().startsWith(ORIGIN) ? route.continue() : route.abort()));
      const {page, methods} = await open(context, '#technical');
      await page.locator('[data-chart-workbench]').waitFor();
      check('empty state has no pattern output ' + width, (await page.locator('[data-pattern-status]').getAttribute('data-code')) === 'NO_DATA' && await page.locator('[data-pattern-card]').count() === 0);
      await page.locator('[data-cw-synthetic]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc');
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily' && document.querySelector('[data-pattern-status]').dataset.code === 'SHOWN');
      let a = await attrs(page);
      const label = await page.locator('[data-pattern-synthetic-label]').textContent();
      const run = await page.locator('[data-pattern-run]').evaluate(el => [el.dataset.runMode, el.textContent]);
      const history = await page.locator('[data-pattern-history]').evaluate(el => ({...el.dataset}));
      check('synthetic input runs the engine and is labelled for function check ' + width, label === '합성 자료 · 기능 확인용 · 실데이터 검증 아님' && run[0] === 'OFFICIAL' && run[1].includes('연구 기본값 · 투자 유용성 미검증 · pattern-rules/1 · params 941af1ff'));
      check('official run is appended to the RAM history ' + width, Number(history.records) > 0 && Number(history.added) > 0 && history.notJudgeable === '0');
      check('zones, boxes and double bottoms/tops are drawn on the chart ' + width, Number(a.patternDrawn) > 0);
      const cards = await page.locator('[data-pattern-card]').evaluateAll(n => n.map(x => ({id: x.dataset.patternCard, state: x.dataset.patternState, kind: x.dataset.patternKind, label: x.querySelector('[data-pattern-label]').textContent})));
      const states = new Set(['FORMED', 'CONFIRMED', 'FAILED', 'INVALIDATED', 'EXPIRED', 'ACTIVE', 'BROKEN', 'SUPERSEDED']);
      check('pattern cards carry state, kind and the research label ' + width, cards.length === 6 && cards.every(c => states.has(c.state) && c.kind === 'OFFICIAL' && c.label === '연구 기본값 · 투자 유용성 미검증'));
      const fields = await page.locator('[data-pattern-card-fields]').first().evaluate(dl => [...dl.querySelectorAll('dt')].map(x => x.textContent));
      const fieldText = await page.locator('[data-pattern-card-fields]').first().textContent();
      check('card fields follow design §11.1 ' + width, ['기준 가격', '탐지 근거', '무효화', '일봉·주봉', '자료 품질', '투자 유용성', '규칙'].every(f => fields.includes(f)) && fieldText.includes('pattern-rules/1 · 941af1ff') && fieldText.includes('미검증'));
      const suit = await page.locator('[data-pattern-suitability] dd').evaluateAll(n => Object.fromEntries(n.map(x => [x.dataset.suitability, x.dataset.code])));
      check('data suitability shows bars, corporate actions and continuity ' + width, suit.BARS === 'OK' && suit.ACTIONS === 'AVAILABLE' && suit.CONTINUITY === 'CONFIRMED');

      phase = 'SELECT ' + width;
      const before = await attrs(page), first = cards[0].id;
      await page.locator('[data-pattern-card]').first().click();
      await page.waitForFunction(id => document.querySelector('[data-chart-workbench]').dataset.patternSelected === id, first);
      a = await attrs(page);
      check('card selection zooms the chart and highlights only that pattern ' + width, a.visibleFrom !== before.visibleFrom && Number(a.patternDrawn) > 0 && Number(a.patternDrawn) <= 6 && (await page.locator('[data-pattern-card]').first().getAttribute('aria-pressed')) === 'true');
      await page.locator('[data-pattern-card]').first().click();
      check('selecting again clears the selection ' + width, (await attrs(page)).patternSelected === '');
      const chart = page.locator('[data-cw-chart]');
      await chart.focus();
      await page.keyboard.press('End');
      await page.keyboard.press('Enter');
      if (process.env.CHART_TEST_DEBUG) console.log('DEBUG', JSON.stringify(await page.evaluate(() => [document.activeElement.className, document.querySelector('[data-cw-readout]').dataset.index, document.querySelector('[data-chart-workbench]').dataset.patternSelected, document.querySelectorAll('[data-cw-pattern]:checked').length])));
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.patternSelected !== '');
      const picked = (await attrs(page)).patternSelected;
      check('Enter on the chart picks the card at the crosshair ' + width, (await page.locator('[data-pattern-card][aria-pressed="true"]').getAttribute('data-pattern-card')) === picked);

      phase = 'USER ' + width;
      const recordsBefore = await page.locator('[data-pattern-history]').getAttribute('data-records');
      await page.locator('[data-cw-settings] summary').click();
      await page.locator('[data-pattern-param="PIVOT_K"]').selectOption('5');
      await page.locator('[data-pattern-explore-run]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.patternView === 'user');
      const userRun = await page.locator('[data-pattern-run]').evaluate(el => [el.dataset.runMode, el.textContent]);
      const userCards = await page.locator('[data-pattern-card]').evaluateAll(n => n.map(x => [x.dataset.patternKind, x.querySelector('[data-pattern-label]').textContent]));
      check('user-settings exploration is shown separately with its changed values and hash ' + width, userRun[0] === 'USER_SETTINGS' && userRun[1].includes('PIVOT_K D 3→5') && !userRun[1].includes('params 941af1ff') && userCards.every(([k, l]) => k === 'USER_SETTINGS' && l === '사용자 설정 탐색 · 공식 이력 아님'));
      await page.locator('[data-pattern-view-button="official"]').click();
      const after = await page.locator('[data-pattern-history]').evaluate(el => ({...el.dataset}));
      check('user-settings runs never enter the official history ' + width, after.records === recordsBefore && (await page.locator('[data-pattern-run]').getAttribute('data-run-mode')) === 'OFFICIAL');
      await page.locator('[data-pattern-explore-reset]').click();
      check('back to defaults removes the exploration view ' + width, await page.locator('[data-pattern-view-button="user"]').isDisabled() && (await page.locator('[data-pattern-param="PIVOT_K"]').inputValue()) === '3');
      await page.locator('[data-cw-pattern="ZONES"]').uncheck();
      const zonesShown = await page.locator('[data-pattern-card^="ZONE|"]').count(), stored = await page.evaluate(() => JSON.parse(localStorage.getItem('investment.web.v1.chart-display-settings')).patterns);
      check('pattern display toggles filter the screen only and are stored per device ' + width, zonesShown === 0 && stored.ZONES === false && (await page.locator('[data-pattern-history]').getAttribute('data-records')) === recordsBefore);
      await page.locator('[data-cw-pattern="ZONES"]').check();

      phase = 'SVG ' + width;
      await page.locator('[data-cw-renderer="svg"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'svg');
      check('SVG fallback keeps the cards and says patterns are not drawn ' + width, (await attrs(page)).patternDrawn === '0' && await page.locator('[data-pattern-card]').count() > 0 && (await page.locator('[data-pattern-overlay-note]').textContent()).includes('SVG'));
      await page.locator('[data-cw-renderer="lwc"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc');

      check('no overflow with pattern cards and settings open ' + width, await noOverflow(page));
      check('no probability, win-rate, score or buy/sell wording in the pattern panel ' + width, !banned.test(await page.locator('[data-pattern-panel]').textContent()) && !banned.test(await page.locator('[data-pattern-explore]').textContent()));
      check('only GET requests ' + width, methods.length > 0 && methods.every(m => m === 'GET'));
      await context.close();
    }

    phase = 'DEVICE';
    {
      const context = await browser.newContext({viewport: {width: 390, height: 900}, serviceWorkers: 'block'});
      await context.route('**/*', route => (route.request().url().startsWith(ORIGIN) ? route.continue() : route.abort()));
      const {page, methods} = await open(context, '#settings');
      await page.locator('#device-backup-export').waitFor();
      await page.evaluate(async () => {
        await DeviceActual.sheetSettings(window, {schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22'});
        localStorage.setItem('investment.web.v1.private-history-origin', InvestmentAppConfig.privateHistoryWorkerOrigin);
        let connected = true, epoch = 1; const listeners = new Set(); window.__logout = () => { connected = false; epoch++; listeners.forEach(f => f()); };
        const synth = ChartWorkbench.syntheticHistory();
        const session = {state: () => ({enabled: true, connected}), revision: () => epoch, setEnabled() {}, subscribe: f => { listeners.add(f); return () => listeners.delete(f); }, async fetchHistory(origin, symbol, range) {
          // Same synthetic bars as the preview, delivered through the private-history path (no split events, as from the Worker today).
          return {schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: 'USD', exchange: 'NMS', timezone: 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', read_at: new Date().toISOString(),
            bars: synth.bars.slice(0, -1).map(b => ({timestamp: b.timestamp, open: b.open, high: b.high, low: b.low, close: b.close, adjusted_close: null, volume: b.volume, session_status: 'COMPLETE'}))};
        }};
        window.GoogleSheetQuotes = {...GoogleSheetQuotes, sessionFor: () => session}; location.hash = 'technical/nvda';
      });
      await page.locator('[data-private-history] [data-history-action="fetch"]:enabled').waitFor();
      await page.locator('[data-private-history] [data-history-action="fetch"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'device');
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily');
      const status = await page.locator('[data-pattern-status]').evaluate(el => ({code: el.dataset.code, reasons: el.dataset.reasons, text: el.textContent}));
      const history = await page.locator('[data-pattern-history]').evaluate(el => ({...el.dataset}));
      const suit = await page.locator('[data-pattern-suitability] dd').evaluateAll(n => Object.fromEntries(n.map(x => [x.dataset.suitability, x.dataset.code])));
      check('real-data path is not judgeable and says why', status.code === 'NOT_JUDGEABLE' && status.reasons.includes('PRICE_BASIS_CONTINUITY_UNCONFIRMED') && status.reasons.includes('CORPORATE_ACTION_EVENTS_NOT_PROVIDED') && status.text.startsWith('판정 불가'));
      check('no pattern state is shown or drawn as a signal on real-data input', await page.locator('[data-pattern-card]').count() === 0 && (await attrs(page)).patternDrawn === '0' && await page.locator('[data-pattern-synthetic-label]').count() === 0);
      check('official history withholds every not-judgeable object', history.added === '0' && Number(history.notJudgeable) > 0 && history.records === '0');
      check('suitability shows missing split events and unconfirmed continuity', suit.ACTIONS === 'NOT_PROVIDED' && suit.CONTINUITY === 'NOT_JUDGEABLE');
      await page.locator('[data-cw-settings] summary').click();
      await page.locator('[data-pattern-param="PIVOT_K"]').selectOption('2');
      await page.locator('[data-pattern-explore-run]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.patternView === 'user');
      check('user settings on real-data input stay not judgeable', (await page.locator('[data-pattern-status]').getAttribute('data-code')) === 'NOT_JUDGEABLE' && await page.locator('[data-pattern-card]').count() === 0);
      await page.locator('[data-indicator-mode="research"]').click();
      check('structure card points to the pattern cards instead of the old NA text', (await page.locator('[data-card-value="STRUCTURE"]').textContent()).includes('패턴 카드'));
      await page.evaluate(() => window.__logout());
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'none');
      check('sign-out clears pattern output from RAM', (await page.locator('[data-pattern-status]').getAttribute('data-code')) === 'NO_DATA' && await page.locator('[data-pattern-history]').isHidden());
      check('only GET requests on the device path', methods.every(m => m === 'GET'));
      check('no overflow on the device path', await noOverflow(page));
      await context.close();
    }
  } catch (error) {
    fail++; console.log('FAIL chart patterns ' + phase + ' ' + (error && error.name || 'Error'));
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  if (fail) process.exitCode = 1;
})();
