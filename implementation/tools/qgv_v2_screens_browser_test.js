'use strict';
// QGV v2 on S06/S04/S05 at 390 and 1440, with scoring_default v1 (shipped) and v2 (scoring-default.js served flipped).
// Synthetic only: sec-qgv2.json (the Q·G side's strictly valid synthetic base vector) and v1 factors by route interception, device prices from a stubbed Universe
// tab read (RAM). Public screens are the empty-state set, so the test does not depend on what the build publishes.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
function v1() {
  const at = new Date().toISOString(), a = 'a'.repeat(64), b = 'b'.repeat(64), companies = {};
  for (const id of IDS) companies[id] = { state: 'LIVE', source_hashes: { companyfacts: a, submissions: b }, factors: Object.fromEntries(FACTORS.map((f, i) => [f, { score: 40 + i * 2, state: 'LIVE' }])) };
  return { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_COMPANYFACTS', sha256: a, acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: b, acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400, data: { companies, method_status: 'PROVISIONAL_UNCALIBRATED', availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
}
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0, phase = 'START';
  try {
    for (const mode of ['v1', 'v2']) for (const width of [390, 1440]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
      if (mode === 'v2') await context.route('**/scoring-default.js*', async (r) => { const res = await r.fetch(), body = (await res.text()).replace("scoring_default:'v1'", "scoring_default:'v2'"); await r.fulfill({ response: res, body }); });
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        const keysBefore = await page.evaluate(() => Object.keys(localStorage).sort());
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, F.strictUniverseValues());
        phase = 'S06';await page.locator('[data-leaderboard-table]').waitFor();
        assert.equal(await page.locator('[data-scoring-default]').first().getAttribute('data-scoring-default'), mode);
        assert.equal(await page.locator('[data-qgv2-preset]').count(), 4);
        assert.equal(await page.locator('[data-qgv2-preset="balanced"]').getAttribute('aria-pressed'), 'true');
        await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        const nvda = page.locator('[data-leaderboard-row="nvda"]'), msft = page.locator('[data-leaderboard-row="msft"]'), gev = page.locator('[data-leaderboard-row="gev"]');
        if (mode === 'v2') {
          const text = await nvda.locator('[data-leaderboard-qgv2]').textContent();
          assert.match(text, /^QGV \d+\.\d · Q \d+\.\d · G \d+\.\d · V \d+\.\d · 요인 1[0-5]\/15$/);
          assert.match(await msft.locator('[data-leaderboard-qgv2]').textContent(), / V — · 요인 1\d\/15$/);
          assert.equal(await gev.locator('[data-leaderboard-qgv2]').getAttribute('data-leaderboard-qgv2'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-leaderboard-rank]').count()) >= 3);
          assert.match(await nvda.locator('[data-leaderboard-v1-reference]').textContent(), /v1 · 결측 재정규화 · 참고 · Q \d/);
          assert.equal(await page.locator('[data-leaderboard-qg]').count(), 0);
          assert.ok((await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count()) >= 1, 'value-trap flag shown');
          const before = text;await page.locator('[data-qgv2-preset="value"]').click();
          await page.locator('[data-qgv2-preset="value"][aria-pressed="true"]').waitFor();
          assert.notEqual(await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qgv2]').textContent(), before);
          await page.locator('[data-qgv2-gate]').uncheck();await page.locator('[data-qgv2-state]').filter({ hasText: '관문 끔' }).waitFor();
          assert.equal(await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 0);assert.equal(await msft.locator('[data-qgv2-flag]').filter({ hasText: 'V 없음' }).count(), 1);assert.equal(await gev.locator('[data-qgv2-flag]').count(), 0);
        } else {
          assert.match(await nvda.locator('[data-leaderboard-qg]').textContent(), /Q \d+\.\d · G \d+\.\d · 요인 13\/13/);
          assert.match(await nvda.locator('[data-leaderboard-v2-compare]').textContent(), /v2 비교용 QGV \d+\.\d · Q .* V \d+\.\d · 요인/);
          assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
          assert.equal(await page.locator('[data-leaderboard-qgv2]').count(), 0);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S06');
        phase = 'S04';await page.goto(BASE + '#company/nvda');await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-badges] [data-scoring-default]').getAttribute('data-scoring-default'), mode);
        if (mode === 'v2') {
          await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
          assert.match(await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent(), /\d/);
          assert.match(await page.locator('[data-qgv2-summary]').textContent(), /산출 요인 1[0-5]\/15 · qgv-v2\/value\/gate-off/);
          assert.match(await page.locator('[data-qgv2-range]').textContent(), /DCF 참고 범위/);
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv-detail]').count(), 1);
        } else {
          await page.locator('[data-qgv-v2-compare]').waitFor();assert.match(await page.locator('[data-qgv-v2-compare]').textContent(), /v2 비교용 · QGV \d/);
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="total"]').count(), 0);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S04');
        phase = 'S05';await page.goto(BASE + '#analysis/nvda');await page.locator('[data-analysis-tab="factors"]').click();
        const panel = page.locator('[data-analysis-panel="factors"]');await panel.waitFor();
        if (mode === 'v2') {
          assert.equal(await panel.locator('[data-v2-factor-table] [data-v2-factor]').count(), 15);
          assert.ok(await panel.locator('[data-v2-factor-table]').isVisible());
          assert.equal(await panel.locator('details[data-qgv-detail] [data-factor-table]').count(), 1);
          assert.match(await panel.locator('[data-v2-factor="v_vs_own_history"]').textContent(), /PRICE_HISTORY_NOT_AVAILABLE/);
          assert.match(await page.locator('[data-overall="v2"]').textContent(), /\d+\.\d/);
        } else {
          assert.ok(await panel.locator('[data-factor-table]').first().isVisible());
          assert.equal(await panel.locator('details[data-v2-compare] [data-v2-factor]').count(), 15);
          assert.equal(await page.locator('[data-overall="v2"]').count(), 0);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S05');
        phase = 'BOUNDARY';const keysAfter = await page.evaluate(() => Object.keys(localStorage).sort());
        assert.deepEqual(keysAfter.filter((k) => !keysBefore.includes(k) && !/google-sheet|sheet-settings/.test(k)), []);
        assert.equal(await page.evaluate(() => Object.keys(localStorage).some((k) => /qgv|price|scor/i.test(k) && !/virtual-trading-v-scores/.test(k))), false);
        assert.equal(errors, 0);pass++;console.log('PASS QGV v2 screens ' + mode + ' ' + width);
      } catch (e) { fail++;console.log('FAIL QGV v2 screens ' + mode + ' ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);process.exitCode = fail ? 1 : 0;
})();
