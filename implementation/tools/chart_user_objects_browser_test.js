'use strict';
// User-written scenarios (3.1.3) and chart notes (3.3) on the technical chart. Synthetic bars only.
// Checks: create -> move away -> back -> reload -> still there; edit; delete; timeframe/symbol anchors; user objects never
// enter the official pattern history; this-device storage only; quota failure keeps stored objects (message + export hint);
// export -> clear -> import round trip without duplicates; malformed / price-bearing imports refused; GET only; no horizontal overflow.
const {chromium} = require('playwright');
const BASE = process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/';
const ORIGIN = new URL(BASE).origin;
const KEY = 'investment.web.v1.chart-user-objects';

(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH});
  let pass = 0, fail = 0, phase = 'INIT';
  const check = (name, ok) => { if (ok) { pass++; console.log('PASS ' + name); } else { fail++; console.log('FAIL ' + name + ' at ' + phase); } };
  const attrs = page => page.evaluate(() => ({...document.querySelector('[data-chart-workbench]').dataset}));
  const stored = page => page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), KEY);
  const banned = /매수|매도|확률|승률|점수|신뢰도|probability|win rate/i;
  async function syntheticDaily(page) {
    await page.locator('[data-cw-synthetic]').click();
    await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.renderer === 'lwc' && document.querySelector('[data-chart-workbench]').dataset.source === 'synthetic');
    await page.locator('[data-cw-timeframe="daily"]').click();
    await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily' && document.querySelector('[data-chart-workbench]').dataset.barCount === '320');
  }
  async function chartBox(page) {
    await page.evaluate(() => document.querySelector('[data-cw-readout]').scrollIntoView({block: 'start'}));
    return page.locator('[data-cw-chart]').boundingBox();
  }
  async function draw(page, tool, points) {
    await page.locator('[data-user-tool="' + tool + '"]').click();
    const box = await chartBox(page);
    for (const [x, y] of points) { await page.mouse.click(box.x + box.width * x, box.y + box.height * y); await page.waitForTimeout(150); }
    if (process.env.CHART_TEST_DEBUG) console.log('DEBUG draw ' + tool + ' ' + JSON.stringify(await page.evaluate(() => [document.querySelector('[data-chart-workbench]').dataset.userCount, document.querySelector('[data-chart-workbench]').dataset.userTool, document.querySelector('[data-user-tool-status]').textContent, document.querySelector('[data-user-status]').textContent])) + ' ' + JSON.stringify(box));
  }
  try {
    for (const width of [390, 1280]) {
      phase = 'CREATE ' + width;
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});
      await context.route('**/*', route => (route.request().url().startsWith(ORIGIN) ? route.continue() : route.abort()));
      const methods = [], page = await context.newPage();
      page.on('request', r => methods.push(r.method()));
      let pageErrors = 0; page.on('pageerror', () => { pageErrors++; });
      await page.goto(BASE + '#technical');
      await page.locator('[data-chart-workbench]').waitFor();
      check('user panel says this-device storage and separation from official history ' + width, (await page.locator('[data-user-boundary]').textContent()).includes('이 기기에만 저장') && (await page.locator('[data-user-boundary]').textContent()).includes('공식 탐지 이력'));
      await syntheticDaily(page);
      const records0 = await page.locator('[data-pattern-history]').getAttribute('data-records'), cards0 = await page.locator('[data-pattern-card]').evaluateAll(n => n.map(x => x.dataset.patternCard));
      await draw(page, 'LINE', [[0.3, 0.3], [0.6, 0.45]]);
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.userCount === '1');
      await draw(page, 'RANGE', [[0.4, 0.25], [0.7, 0.35]]);
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.userCount === '2');
      await draw(page, 'MEMO', [[0.5, 0.2]]);
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.userCount === '3');
      const memoId = (await stored(page)).items.find(o => o.kind === 'MEMO').id, memo = page.locator('[data-user-item="' + memoId + '"]');
      await memo.locator('[data-user-field="text"]').fill('합성 메모 A');
      await memo.locator('[data-user-save]').click();
      await page.locator('[data-user-scenario-new] summary').click();
      const form = page.locator('[data-user-scenario-form]');
      await form.locator('[data-user-field="direction"]').selectOption('DOWN');
      await form.locator('[data-user-field="levelLabel0"]').fill('지지 후보');
      await form.locator('[data-user-field="level0"]').fill('70');
      await form.locator('[data-user-field="condition"]').fill('합성 조건');
      await form.locator('[data-user-field="invalidation"]').fill('합성 무효화');
      await form.locator('[data-user-field="invalidationPrice"]').fill('90');
      await page.locator('[data-user-scenario-save]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.userCount === '4');
      let a = await attrs(page);
      check('lines, ranges, memos and scenarios are drawn as user objects ' + width, Number(a.userDrawn) >= 8 && await page.locator('[data-user-item] [data-user-label]').evaluateAll(n => n.length === 4 && n.every(x => x.textContent === '사용자 작성')));
      check('scenario keeps path, key level, condition and invalidation ' + width, (await page.locator('[data-user-scenarios] [data-user-item]').textContent()).includes('↓ 하락') && (await page.locator('[data-user-scenarios]').textContent()).includes('합성 조건') && (await page.locator('[data-user-scenarios]').textContent()).includes('합성 무효화'));
      const records1 = await page.locator('[data-pattern-history]').getAttribute('data-records'), cards1 = await page.locator('[data-pattern-card]').evaluateAll(n => n.map(x => x.dataset.patternCard));
      check('user objects never enter the official pattern history or its cards ' + width, records1 === records0 && JSON.stringify(cards1) === JSON.stringify(cards0) && cards1.every(id => !id.startsWith('u-')));
      let saved = await stored(page);
      check('stored on this device with schema and anchors ' + width, saved.schema === 'chart-user-objects/1' && saved.items.length === 4 && saved.items.every(o => o.author === 'USER' && o.symbol === 'SYNTH' && o.interval === 'D' && o.price_basis === 'RAW_CLOSE')
        && saved.items.filter(o => o.schema === 'chart-annotation/1').length === 3 && saved.items.filter(o => o.schema === 'chart-scenario/1').length === 1);

      phase = 'KEYBOARD ' + width;
      await page.locator('[data-user-tool="MEMO"]').click();
      await page.locator('[data-cw-chart]').focus();
      await page.keyboard.press('End');
      await page.keyboard.press('n');
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.userCount === '5');
      check('keyboard N places a memo at the crosshair bar ' + width, (await stored(page)).items.some(o => o.kind === 'MEMO' && o.points[0].time === '2026-03-27'));

      phase = 'AWAY ' + width;
      await page.evaluate(() => { location.hash = 'leaderboard'; });
      await page.waitForFunction(() => !document.querySelector('[data-chart-workbench]'));
      await page.evaluate(() => { location.hash = 'technical'; });
      await page.locator('[data-chart-workbench]').waitFor();
      await syntheticDaily(page);
      check('objects are back after moving away and returning ' + width, (await attrs(page)).userCount === '5');
      phase = 'RELOAD ' + width;
      await page.reload(); await page.locator('[data-chart-workbench]').waitFor();
      await syntheticDaily(page);
      a = await attrs(page);
      check('objects survive a reload ' + width, a.userCount === '5' && Number(a.userDrawn) >= 8 && (await page.locator('[data-user-notes]').textContent()).includes('합성 메모 A'));
      await page.locator('[data-cw-timeframe="weekly"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'weekly');
      check('objects are tied to their interval ' + width, (await attrs(page)).userCount === '0');
      await page.locator('[data-cw-timeframe="daily"]').click();
      await page.waitForFunction(() => document.querySelector('[data-chart-workbench]').dataset.timeframe === 'daily');

      phase = 'EDIT ' + width;
      const memo2 = page.locator('[data-user-item="' + memoId + '"]');
      await memo2.locator('summary').click();
      await memo2.locator('[data-user-field="text"]').fill('합성 메모 B');
      await memo2.locator('[data-user-save]').click();
      const lineId = (await stored(page)).items.find(o => o.kind === 'LINE').id, line = page.locator('[data-user-item="' + lineId + '"]');
      await line.locator('summary').click();
      await line.locator('[data-user-field="time0"]').fill('not-a-date');
      await line.locator('[data-user-save]').click();
      check('invalid edits are refused and keep the stored object ' + width, (await page.locator('[data-user-status]').getAttribute('data-code')) === 'USER_OBJECT_INVALID' && (await stored(page)).items.find(o => o.id === lineId).points[0].time !== 'not-a-date');
      await page.locator('[data-user-item="' + lineId + '"] [data-user-delete]').click();
      await page.reload(); await page.locator('[data-chart-workbench]').waitFor();
      await syntheticDaily(page);
      saved = await stored(page);
      check('edit and delete persist across a reload ' + width, (await attrs(page)).userCount === '4' && !saved.items.some(o => o.id === lineId) && saved.items.some(o => o.text === '합성 메모 B'));

      phase = 'EXPORT ' + width;
      const download = page.waitForEvent('download');
      await page.locator('[data-user-export]').click();
      const exportFile = await download, exported = JSON.parse(require('node:fs').readFileSync(await exportFile.path(), 'utf8'));
      check('export saves a file on this device ' + width, exportFile.suggestedFilename() === 'chart-user-objects.json' && exported.schema === 'chart-user-objects/1' && exported.items.length === 4);

      phase = 'QUOTA ' + width;
      const rawBefore = await page.evaluate(key => localStorage.getItem(key), KEY);
      await page.evaluate(key => { window.__setItem = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (k === key) throw new DOMException('synthetic quota', 'QuotaExceededError'); return window.__setItem.call(this, k, v); }; }, KEY);
      await draw(page, 'MEMO', [[0.45, 0.25]]);
      await page.waitForFunction(() => document.querySelector('[data-user-status]').dataset.code === 'SAVE_FAILED');
      const failText = await page.locator('[data-user-status]').textContent();
      check('quota failure keeps stored objects and shows a save-failure message with the export hint ' + width, await page.evaluate(key => localStorage.getItem(key), KEY) === rawBefore
        && failText.includes('저장 실패') && failText.includes('그대로') && failText.includes('내보내기') && !banned.test(failText));
      await page.evaluate(() => { Storage.prototype.setItem = window.__setItem; delete window.__setItem; });

      phase = 'IMPORT ' + width;
      const importFile = async (obj, name) => {
        await page.evaluate(() => { delete document.querySelector('[data-user-status]').dataset.code; });
        await page.locator('[data-user-import]').setInputFiles({name, mimeType: 'application/json', buffer: Buffer.from(typeof obj === 'string' ? obj : JSON.stringify(obj))});
        await page.waitForFunction(() => !!document.querySelector('[data-user-status]').dataset.code);
        return page.locator('[data-user-status]').getAttribute('data-code');
      };
      await page.locator('[data-user-clear="all"]').click();
      check('clear all empties the device store before the round trip ' + width, await page.evaluate(key => localStorage.getItem(key), KEY) === null && (await attrs(page)).userCount === '0');
      const roundCode = await importFile(exported, 'round.json');
      saved = await stored(page);
      check('export -> clear -> import restores every note and scenario ' + width, roundCode === 'IMPORTED' && JSON.stringify(saved.items) === JSON.stringify(exported.items) && (await attrs(page)).userCount === '4'
        && (await page.locator('[data-user-notes]').textContent()).includes('합성 메모 B') && (await page.locator('[data-user-scenarios]').textContent()).includes('합성 조건'));
      await importFile(exported, 'again.json');
      check('importing the same file again adds no duplicates ' + width, (await stored(page)).items.length === 4 && (await page.locator('[data-user-status]').textContent()).includes('4'));
      const keptRaw = await page.evaluate(key => localStorage.getItem(key), KEY), first = exported.items[0], scen = exported.items.find(o => o.schema === 'chart-scenario/1');
      const refusedAll = [];
      for (const [bad, name] of [[{...exported, series: [{time: '2026-01-02', close: 1}]}, 'series.json'], [{...exported, items: [{...first, id: 'u-zz0001', close: 101}]}, 'close.json'],
        [{...exported, items: [{...scen, id: 'u-zz0002', quote: {last: 1}}]}, 'quote.json'], [{...exported, items: [{...first, id: 'u-zz0003', points: first.points.map(pt => ({...pt, volume: 9}))}]}, 'volume.json'],
        [{...exported, schema: 'chart-user-objects/9'}, 'schema.json'], ['{not json', 'broken.json']]) refusedAll.push((await importFile(bad, name)) === 'IMPORT_REFUSED' && await page.evaluate(key => localStorage.getItem(key), KEY) === keptRaw);
      check('malformed or price-bearing imports are refused and write nothing ' + width, refusedAll.length === 6 && refusedAll.every(Boolean) && !banned.test(await page.locator('[data-user-status]').textContent()));
      await page.locator('[data-user-visible]').uncheck();
      check('user objects can be hidden from the chart ' + width, (await attrs(page)).userDrawn === '0');
      await page.locator('[data-user-visible]').check();
      check('no horizontal overflow with the user panel open ' + width, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      check('no probability, win-rate, score or buy/sell wording ' + width, !banned.test(await page.locator('[data-user-panel]').textContent()));
      await page.locator('[data-user-clear="here"]').click();
      check('clear removes the objects and the device key ' + width, (await attrs(page)).userCount === '0' && await page.evaluate(key => localStorage.getItem(key), KEY) === null);
      check('only GET requests and no page errors ' + width, methods.length > 0 && methods.every(m => m === 'GET') && pageErrors === 0);
      await context.close();
    }
  } catch (error) {
    fail++; console.log('FAIL chart user objects ' + phase + ' ' + (error && error.name || 'Error'));
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);
  if (fail) process.exitCode = 1;
})();
