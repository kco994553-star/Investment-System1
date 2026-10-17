'use strict';
// QGV v2 on S06/S04/S05/S13 at 390 and 1280. Owner decision 2026-10-14: v2 is the ONLY score on screens, so even with
// scoring-default.js served flipped to 'v1' every screen shows v2 and no v1 comparison / [자세히] v1 reference / '임시 기본'.
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
    for (const mode of ['v1', 'v2']) for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
      await context.route('**/scoring-default.js*', async (r) => { const res = await r.fetch(), body = (await res.text()).replace(/scoring_default:'v[12]'/, "scoring_default:'" + mode + "'"); await r.fulfill({ response: res, body }); });
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
        assert.equal(await page.locator('[data-scoring-default]').first().getAttribute('data-scoring-default'), 'v2');
        assert.equal(await page.locator('[data-qgv2-preset]').count(), 4);
        assert.equal(await page.locator('[data-qgv2-preset="balanced"]').getAttribute('aria-pressed'), 'true');
        await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        const nvda = page.locator('[data-leaderboard-row="nvda"]'), msft = page.locator('[data-leaderboard-row="msft"]'), gev = page.locator('[data-leaderboard-row="gev"]');
        {
          // DESIGN_CLEANUP_BACKLOG S06: QGV, Q, G, V are separate columns; the one-line summary rides in data-summary.
          const text = await nvda.locator('[data-leaderboard-qgv2]').getAttribute('data-summary');
          assert.match(text, /^QGV \d+\.\d · Q \d+\.\d · G \d+\.\d · V \d+\.\d · 산출 요인 1[0-5]\/15$/);
          assert.match(await nvda.locator('[data-leaderboard-total]').textContent(), /^\d+\.\d$/);
          for (const axis of ['Q', 'G', 'V']) assert.match(await nvda.locator('[data-leaderboard-axis="' + axis + '"]').textContent(), /^\d+\.\d$/, axis);
          assert.match(await nvda.locator('[data-leaderboard-factors]').textContent(), /^요인 1[0-5]\/15$/);
          assert.match(await msft.locator('[data-leaderboard-qgv2]').getAttribute('data-summary'), / V — · 산출 요인 1\d\/15$/);
          assert.equal(await msft.locator('[data-leaderboard-axis="V"]').textContent(), '—');
          assert.equal(await gev.locator('[data-leaderboard-qgv2]').getAttribute('data-leaderboard-qgv2'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-leaderboard-rank]').count()) >= 3);
          // No v1 anywhere on S06: no [자세히] v1 reference, no v1 Q·G, no v2-for-comparison line, no '임시 기본'.
          assert.equal(await page.locator('[data-leaderboard-v1-reference]').count(), 0);assert.equal(await page.locator('[data-leaderboard-v2-compare]').count(), 0);
          assert.equal(await nvda.locator('[data-qgv-detail]').count(), 0);
          assert.equal(await page.locator('[data-leaderboard-qg]').count(), 0);
          assert.ok(!/임시 기본|v1 비교용|v1 · 결측|v1 참고/.test(await page.locator('[data-leaderboard-screen]').textContent()));
          assert.ok((await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count()) >= 1, 'value-trap flag shown');
          const before = text;await page.locator('[data-qgv2-preset="value"]').click();
          await page.locator('[data-qgv2-preset="value"][aria-pressed="true"]').waitFor();
          assert.notEqual(await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qgv2]').getAttribute('data-summary'), before);
          await page.locator('[data-qgv2-gate]').uncheck();await page.locator('[data-qgv2-state]').filter({ hasText: '관문 끔' }).waitFor();
          assert.equal(await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 0);assert.equal(await msft.locator('[data-qgv2-flag]').filter({ hasText: 'V 없음' }).count(), 1);assert.equal(await gev.locator('[data-qgv2-flag]').count(), 0);
          // v2 NOT_AVAILABLE rows say why (never a v1 fallback).
          assert.match(await gev.locator('[data-leaderboard-na-reason]').textContent(), /^QGV v2 산출 불가 · /);
          assert.equal(await gev.locator('[data-leaderboard-qgv2] > details > summary').textContent(), '산출 불가');
          assert.equal(await gev.locator('[data-leaderboard-qgv2] > details').getAttribute('open'), null, 'reason folded by default');
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S06');
        phase = 'S13';await page.goto(BASE + '#profiles');await page.locator('[data-profile-editor]').waitFor();
        assert.equal(await page.locator('[data-profile-v2] h3').count(),1);
        {assert.equal(await page.locator('[data-v2-official-axis]').count(),3);assert.equal(await page.locator('[data-v2-preset]').count(),4);assert.equal(await page.locator('[data-v2-performance]').getAttribute('data-v2-performance'),'NOT_AVAILABLE');}
        assert.ok(!/v1 비교용|비교용 · v1|임시 기본/.test(await page.locator('[data-profile-official]').textContent()));assert.equal(await page.locator('[data-official-axis]').count(),0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S13');
        phase = 'S04';await page.goto(BASE + '#company/nvda');await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-badges] [data-scoring-default]').getAttribute('data-scoring-default'), 'v2');
        {
          await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
          assert.match(await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent(), /\d/);
          // The profile reads as words ('가치 · 관문 끔'); the id stays in data-profile-id.
          assert.match(await page.locator('[data-qgv2-summary]').textContent(), /산출 요인 1[0-5]\/15 · 가치 · 관문 끔/);
          assert.equal(await page.locator('[data-qgv2-summary]').getAttribute('data-profile-id'), 'qgv-v2/value/gate-off');
          assert.ok(!/qgv-v2\//.test(await page.locator('main').textContent()), 'no profile id on screen');
          assert.match(await page.locator('[data-qgv2-range]').textContent(), /DCF 참고 범위/);
          // No [자세히] v1 reference and no v2-for-comparison line on S04.
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv-detail]').count(), 0);assert.equal(await page.locator('[data-qgv-v2-compare], [data-qgv-v1-reference]').count(), 0);
          assert.ok(!/임시 기본|v1 비교용|v1 참고|점수 기준 v1/.test(await page.locator('main').textContent()));
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S04');
        phase = 'S05';await page.goto(BASE + '#analysis/nvda');await page.locator('[data-analysis-tab="factors"]').click();
        const panel = page.locator('[data-analysis-panel="factors"]');await panel.waitFor();
        {
          assert.equal(await panel.locator('[data-v2-factor-table] [data-v2-factor]').count(), 15);
          assert.ok(await panel.locator('[data-v2-factor-table]').isVisible());
          // The v1 factor table ([자세히] v1 참고) is gone from S05; raw SEC Q·G leaf scores are in Settings > 원자료 보기.
          assert.equal(await panel.locator('details[data-qgv-detail] [data-factor-table]').count(), 0);assert.equal(await page.locator('[data-factor-table], [data-v2-compare]').count(), 0);
          const earnings = await page.evaluate(() => {
            const input=publicScreens[Qgv2Inputs.FILE].records['TARGET:nvda'],engine=window.PlaybookEngine,cfg=window.PlaybookConfigDefaults;
            const configured=Boolean(engine?.classifyTypesV0&&cfg);
            return {sic:input.sic,configured,cyclical:configured?engine.classifyTypesV0(cfg,{sic:input.sic}).cyclical.member:null,
              basis:qgvScores().rows.nvda.v2.detail.earnings_basis};
          });
          assert.equal(earnings.sic,'3674');
          assert.equal(earnings.configured,true,'the approved classifier is loaded independently of the playbook UI');
          assert.equal(earnings.cyclical,true,'approved semiconductor SIC activates the cyclical earnings basis');
          assert.equal(earnings.basis,'NORMALIZED');
          assert.equal(await panel.locator('[data-v2-factor="v_vs_own_history"] [data-reason-codes]').getAttribute('data-reason-codes'), 'NORMALIZED_HISTORY_NOT_AVAILABLE');
          assert.match(await panel.locator('[data-v2-factor="v_vs_own_history"]').textContent(), /경기민감 기업이라 과거 비교 보류/);
          assert.ok(!/[A-Z]{3,}_[A-Z_]{3,}/.test((await panel.locator('[data-v2-factor-table]').textContent()).replaceAll('NOT_AVAILABLE', '')), 'no reason codes on screen');
          assert.match(await page.locator('[data-overall="v2"]').textContent(), /\d+\.\d/);
          // A device-quote refresh repaints only the score sections: the open tab and the other panels stay as they are.
          const kept = await page.evaluate(() => {
            const value=document.querySelector('[data-analysis-panel="value"]');value.dataset.keep='1';repaintScores(()=>analysis('nvda'));
            return {value:value.isConnected&&document.querySelector('[data-analysis-panel="value"]')===value,
              tab:document.querySelector('[data-analysis-tab="factors"]').getAttribute('aria-selected'),hidden:document.querySelector('[data-analysis-panel="factors"]').hidden};
          });
          assert.deepEqual(kept, {value:true,tab:'true',hidden:false});
          assert.equal(await panel.locator('[data-v2-factor-table] [data-v2-factor]').count(), 15);
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
