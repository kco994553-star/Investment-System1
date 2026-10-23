'use strict';
// Menu 2 기술적 분석 layout (design lane D6): function-number stamp boxes 3.1–3.4 in order, the legend saying stamp numbers are
// not menu numbers, result cards moved into 3.1.4, status notes into the 3.2 / 3.3 groups, menu anchors still reachable,
// real prices stated as not judged, no buy/sell wording, no horizontal overflow at 360 / 390 / 1280. Synthetic data only.
const {chromium} = require('playwright'), assert = require('node:assert/strict');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const ORDER = ['3.1', '3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.2', '3.2.1', '3.2.2', '3.2.3', '3.2.4', '3.2.5', '3.3', '3.3.1', '3.3.2', '3.3.3', '3.4'];
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let phase = 'START';
  try {
    for (const width of [360, 390, 1280]) {
      phase = 'LAYOUT ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(BASE).origin ? route.continue() : route.abort());
      const page = await context.newPage(); let errors = 0; page.on('pageerror', () => errors++);
      await page.goto(BASE + '#technical'); await page.locator('[data-ta-layout][data-ta-arranged] [data-chart-workbench]').waitFor();
      const stamps = await page.evaluate(() => [...document.querySelectorAll('[data-ta-layout] [data-fn-group], [data-ta-layout] .fn-sec[data-fn]')].map(n => n.dataset.fnGroup || n.dataset.fn));
      assert.deepEqual(stamps, ORDER, 'stamp order ' + stamps.join());
      assert.ok((await page.locator('[data-fn-legend="3"]').textContent()).includes('기능 번호'), 'legend: stamp numbers are function numbers');
      assert.ok(await page.locator('main a[href="#technical-pattern"]').count() >= 1, 'menu strip keeps 2.2');
      assert.equal(await page.locator('[data-fn="3.1.4"] [data-cw-slot="results"] #technical-indicators [data-indicator-cards]').count(), 1, 'indicator cards in 3.1.4');
      // Official status cards stay outside the workbench (its wording rule), in their own region after it.
      for (const id of ['technical-state', 'technical-phase', 'technical-qgv-context', 'technical-scenarios', 'technical-execution', 'technical-record'])
        assert.equal(await page.locator('[data-ta-official] #' + id).count(), 1, id + ' in the official region');
      assert.ok(await page.evaluate(() => !!(document.querySelector('[data-chart-workbench]').compareDocumentPosition(document.querySelector('[data-ta-official]')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'official region after the workbench');
      assert.ok(await page.evaluate(() => !!(document.querySelector('#technical-tv-chart').compareDocumentPosition(document.querySelector('[data-chart-workbench]')) & Node.DOCUMENT_POSITION_FOLLOWING)), 'TradingView card above the workbench');
      assert.equal(await page.locator('[data-fn-group="3.2"] #technical-pattern').count(), 1);
      assert.equal(await page.locator('[data-fn-group="3.3"] #technical-notes').count(), 1);
      assert.deepEqual(await page.locator('[data-tech-status]').evaluateAll(n => n.map(x => x.dataset.techStatus)), ['chart', 'engine', 'execution', 'record']);
      assert.ok((await page.locator('[data-ta-real-price]').textContent()).includes('판정 불가'));
      assert.equal(await page.locator('[data-result-kind]').count(), 5);
      assert.equal(await page.locator('[data-pattern-state-legend] [data-state-code]').count(), 5);
      assert.ok(!/매수|매도|주문하기|확률|승률/.test(await page.locator('[data-pattern-panel]').textContent() + await page.locator('[data-user-panel]').textContent()), 'no buy/sell or probability wording in 3.2 / 3.3');
      assert.equal(await page.locator('[data-fn="3.4"] a[href="#tree/technical"]').count(), 1);
      assert.equal(await page.locator('[data-ia-screen="technical"] svg, [data-ia-screen="technical"] canvas').count(), 0, 'no SVG or canvas before data (decoration is CSS)');
      await page.locator('[data-cw-synthetic]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.source === 'synthetic');
      assert.equal(await page.locator('[data-fn="3.1.1"] [data-synthetic-label]').textContent(), '합성 자료 · 미리보기 · 실데이터 검증 아님');
      assert.equal(await page.locator('[data-fn="3.1.1"] [data-cw-judgement]').getAttribute('data-code'), 'SYNTHETIC_PREVIEW');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'no horizontal overflow ' + width);
      phase = 'ANCHOR ' + width;
      for (const hash of ['technical-pattern', 'technical-notes']) {
        await page.goto(BASE + '#' + hash); await page.locator('[data-ta-arranged] #' + hash).waitFor();
        await page.waitForFunction(h => { const b = document.getElementById(h).getBoundingClientRect(); return b.top < innerHeight && b.bottom > 0; }, hash);
      }
      assert.equal(errors, 0, 'page errors');
      await context.close();
      console.log('PASS technical layout ' + width);
    }
    phase = 'TREE';
    const context = await browser.newContext({viewport: {width: 390, height: 900}, serviceWorkers: 'block'});
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(BASE).origin ? route.continue() : route.abort());
    const page = await context.newPage();
    await page.goto(BASE + '#tree/technical'); await page.locator('[data-tree="technical"]').waitFor();
    const tree = await page.locator('[data-tree="technical"] [data-fn-stamp]').allTextContents();
    assert.deepEqual(tree, ['3.4', '3.1', '3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.2', '3.2.1', '3.2.2', '3.2.3', '3.2.4', '3.2.5', '3.3', '3.3.1', '3.3.2', '3.3.3']);
    await context.close();
    console.log('PASS technical tree stamps');
  } catch (error) { console.log('FAIL technical layout ' + phase + ' ' + (error && error.message ? error.message.split('\n')[0] : '')); process.exitCode = 1; }
  finally { await browser.close(); }
})();
