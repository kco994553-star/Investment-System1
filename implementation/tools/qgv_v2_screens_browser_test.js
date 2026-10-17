'use strict';
// QGV v2 on S06/S04/S05/S13 at 390 and 1280. Owner decision 2026-10-14: v2 is the ONLY score on screens, so even with
// scoring-default.js served flipped to 'v1' every screen shows v2 and no v1 comparison / [자세히] v1 reference / '임시 기본'.
// Synthetic only: sec-qgv2.json (the Q·G side's strictly valid synthetic base vector) and v1 factors by route interception, device prices from a stubbed Universe
// tab read (RAM). Public screens are the empty-state set, so the test does not depend on what the build publishes.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
function v1() {
  const at = new Date().toISOString(), a = 'a'.repeat(64), b = 'b'.repeat(64), companies = {};
  for (const id of IDS) companies[id] = { state: 'LIVE', source_hashes: { companyfacts: a, submissions: b }, factors: Object.fromEntries(FACTORS.map((f, i) => [f, { score: 40 + i * 2, state: 'LIVE' }])) };
  return { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_COMPANYFACTS', sha256: a, acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: b, acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400, data: { companies, method_status: 'PROVISIONAL_UNCALIBRATED', availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
}
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const h1Focused = (page) => page.evaluate(() => document.activeElement?.tagName === 'H1' && document.querySelector('#content h1') === document.activeElement);
const rowIds = (page) => page.locator('[data-leaderboard-row]').evaluateAll((rows) => rows.map((r) => r.dataset.leaderboardRow));
/* S06 -> S04 -> S06 flow (first frontend flow): ranks over all identities, 'QGV v2 순' default, filter/sort/scroll restored by the
   S04 back link and by browser back, S04 deep links (factors/value tabs, technical keeps the company), v2 score time, collapsed
   unconnected columns, h1 focus on route change. */
async function flow(page, width) {
  const T = '[data-leaderboard-table]';
  // Columns: 5 drawn on PC, 3 on a phone (rank, company, QGV; the rest behind the per-row button), all th scope=col and none hidden;
  // the always-— columns are named in one note instead.
  const cols = width < 750 ? 3 : 5;assert.equal(await page.locator(T + ' thead th').count(), cols);assert.equal(await page.locator(T + ' thead th[scope="col"]').count(), cols);
  assert.deepEqual(await page.locator(T + ' thead th').evaluateAll((ths) => ths.map((th) => th.dataset.leaderboardCol)), ['rank', 'company', 'qgv', 'qgv_detail', 'earnings'].slice(0, cols));
  assert.match(await page.locator('[data-leaderboard-unconnected]').textContent(), /일간 · 컨센서스 · 목표 · QGV 시나리오 · 재평가 · VMR/);
  const nvdaRow = page.locator('[data-leaderboard-row="nvda"]');
  if (width < 750) {
    assert.equal(await page.locator(T + ' th[data-leaderboard-col="qgv_detail"]').isVisible(), false, 'phone hides the detail column');
    const toggle = nvdaRow.locator('.lb-toggle');assert.ok(await toggle.isVisible());assert.equal(await toggle.getAttribute('aria-expanded'), 'false');
    await toggle.click();assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
    const detail = nvdaRow.locator('[data-leaderboard-detail]');assert.ok(await detail.isVisible());assert.match(await detail.textContent(), /^QGV \d+\.\d · Q .*실적 /);
    const box = await toggle.boundingBox();assert.ok(box.height >= 44 && box.width >= 44, 'detail button target size');
  } else {
    assert.ok(await page.locator(T + ' th[data-leaderboard-col="qgv_detail"]').isVisible());assert.equal(await nvdaRow.locator('.lb-toggle').isVisible(), false);
  }
  // Default sort 'QGV v2 순': ranked rows first in rank order, NOT_AVAILABLE (—) last; never 0.
  phase = 'FLOW_RANK';assert.equal(await page.locator('#leader-sort').inputValue(), 'qgv');
  const ranks = await page.locator(T + ' tbody tr').evaluateAll((rows) => rows.map((r) => r.cells[0].textContent));
  const firstNa = ranks.indexOf('—'), ranked = ranks.slice(0, firstNa < 0 ? ranks.length : firstNa).map(Number);
  assert.ok(ranked.length >= 2, JSON.stringify(ranks));assert.deepEqual(ranked, ranked.map((_, i) => i + 1));assert.ok(ranks.slice(ranked.length).every((r) => r === '—'));
  assert.equal(await page.locator(T + ' [data-leaderboard-total="0.0"]').count(), 0);
  const gev = page.locator('[data-leaderboard-row="gev"] [data-leaderboard-total]');assert.equal(await gev.getAttribute('data-leaderboard-total'), 'NOT_AVAILABLE');assert.equal(await gev.textContent(), '—');
  // A filter only hides rows: the second-ranked company keeps rank 2 among all 19 when it is the only row shown.
  const second = (await rowIds(page))[1], secondTicker = await page.locator('[data-leaderboard-row="' + second + '"] a').first().textContent();
  await page.locator('#leader-query').fill(secondTicker);await page.waitForFunction((id) => document.querySelectorAll('[data-leaderboard-row]').length === 1 && document.querySelector('[data-leaderboard-row="' + id + '"]'), second);
  assert.equal(await page.locator('[data-leaderboard-row="' + second + '"] [data-leaderboard-rank]').getAttribute('data-leaderboard-rank'), '2');
  // Filter + sort + scroll, then S04 and back.
  phase = 'FLOW_STATE';await page.locator('#leader-query').fill('a');await page.locator('#leader-sort').selectOption('name');
  const ids = await rowIds(page);assert.ok(ids.includes('nvda') && ids.length < 19);
  const summary = await page.locator('[data-leaderboard-summary]').textContent();assert.match(summary, /정렬: 기업명 순 · 필터: 검색 “a” · 보기: 기본 · 프로필: 가치\(관문 켬\) · 관문 끔 · 19개 중 \d+개 표시/);
  const nvdaRank = await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-rank]').getAttribute('data-leaderboard-rank'), nvdaTotal = await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-total]').getAttribute('data-leaderboard-total');
  const asOf = await page.locator('[data-leaderboard-screen] [data-score-as-of="v2"]').textContent();assert.match(asOf, /^점수 기준 20\d\d-/);
  await page.evaluate(() => { const r = document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect();window.scrollTo(0, Math.max(1, r.top + scrollY - innerHeight / 2)); });
  await page.waitForTimeout(300);assert.ok(await page.evaluate(() => scrollY) > 0);
  // Where the NVDA row sat in the viewport when it was clicked (capture phase, before the route changes). The browser may
  // adjust scrollY by a few pixels after the return (scroll anchoring while late content settles), so the row position is compared.
  await page.evaluate(() => document.addEventListener('click', () => { if (location.hash.startsWith('#leaderboard')) window.__leaveTop = document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top; }, true));
  const restored = async (how) => {
    const top = await page.evaluate(() => window.__leaveTop);await page.locator(T).waitFor();
    await page.waitForFunction((v) => scrollY > 0 && Math.abs(document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top - v) <= 2, top, { timeout: 5000 })
      .catch(async () => { throw Error(how + ' scroll ' + JSON.stringify(await page.evaluate(() => [scrollY, document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top])) + ' want row top ' + top); });
    assert.equal(await page.locator('#leader-sort').inputValue(), 'name', how + ' sort');assert.equal(await page.locator('#leader-query').inputValue(), 'a', how + ' query');
    assert.deepEqual(await rowIds(page), ids, how + ' rows');assert.equal(await page.locator('[data-leaderboard-summary]').textContent(), summary, how + ' summary');
    assert.ok(await h1Focused(page), how + ' focus h1');
  };
  const toCompany = async () => {
    await page.locator('[data-leaderboard-row="nvda"] a').first().click();await page.locator('[data-company-card="qgv"]').waitFor();await page.waitForFunction(() => location.hash === '#company/nvda');
  };
  phase = 'FLOW_S04';await toCompany();assert.ok(await h1Focused(page), 'S04 focus h1');
  assert.equal(await page.evaluate(() => scrollY), 0);
  const back = page.locator('[data-origin-link="leaderboard"]');assert.equal((await back.textContent()).trim(), '← 리더보드');assert.equal(await back.getAttribute('href'), '#leaderboard');
  // Same rank and total as S06 (same population, preset and gate).
  await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
  assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').textContent(), nvdaRank);assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').textContent(), nvdaTotal);
  assert.equal(await page.locator('[data-company-badges] [data-score-as-of="v2"]').textContent(), asOf, 'S04 shows the v2 score time');
  assert.match(await page.locator('[data-company-badges] [data-v1-preview-as-of]').textContent(), /^v1 미리보기 입력 /);
  // Price badge = the value card's device quote state (no static 'NOT_AVAILABLE' while the card shows a quote).
  await page.waitForFunction(() => document.querySelector('[data-badge="price"]')?.dataset.priceState !== 'PENDING');
  const priceState = await page.locator('[data-badge="price"]').getAttribute('data-price-state'), cardQuote = await page.locator('#company-value [data-value-quote-source]').count();
  assert.equal(priceState, cardQuote ? 'AVAILABLE' : 'NOT_AVAILABLE');
  assert.equal(await page.locator('[data-company-card="technical"] a[href="#technical/nvda"]').count(), 1);
  assert.equal(await page.locator('[data-analysis-link="factors"]').getAttribute('href'), '#analysis/nvda/factors');assert.equal(await page.locator('[data-analysis-link="value"]').getAttribute('href'), '#analysis/nvda/value');
  phase = 'FLOW_BACKLINK';await back.click();await restored('back link');
  phase = 'FLOW_HISTORY';await toCompany();await page.goBack();await restored('browser back');
  // S04 -> S05 deep links open the matching tab; a tab change replaces the hash, so back returns to S04.
  phase = 'FLOW_TABS';await toCompany();await page.locator('[data-analysis-link="factors"]').click();
  await page.locator('[data-analysis-tab="factors"][aria-selected="true"]').waitFor();assert.ok(await page.locator('[data-analysis-panel="factors"]').isVisible());assert.equal(await page.locator('[data-analysis-panel="summary"]').isVisible(), false);
  assert.ok(await h1Focused(page), 'S05 focus h1');
  await page.locator('[data-analysis-tab="factors"]').focus();await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('[data-analysis-tab="value"]').getAttribute('aria-selected'), 'true');assert.equal(await page.evaluate(() => location.hash), '#analysis/nvda/value');
  await page.goBack();await page.locator('[data-company-card="qgv"]').waitFor();assert.equal(await page.evaluate(() => location.hash), '#company/nvda');
  await page.locator('[data-analysis-link="value"]').click();await page.locator('[data-analysis-tab="value"][aria-selected="true"]').waitFor();assert.ok(await page.locator('[data-analysis-panel="value"] [data-company-value]').isVisible());
  assert.equal(await page.locator('[data-analysis-panel="events"] a[href="#technical/nvda"]').count(), 1);
  // S04 -> S08 keeps the company (was ASML).
  phase = 'FLOW_TECH';await page.goBack();await page.locator('[data-company-card="technical"] a[href="#technical/nvda"]').click();
  await page.locator('[data-technical-symbol]').waitFor();assert.equal(await page.locator('[data-technical-symbol]').inputValue(), 'nvda');
  phase = 'FLOW_DONE';
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  try {
    for (const mode of ['v1', 'v2']) for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
      await context.route('**/scoring-default.js*', async (r) => { const res = await r.fetch(), body = (await res.text()).replace(/scoring_default:'v[12]'/, "scoring_default:'" + mode + "'"); await r.fulfill({ response: res, body }); });
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      // Every request the flow makes; the app must not reach any other origin (external requests are also aborted below).
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
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
        // TYPE-SCOPE (owner decision 2026-10-17 item 4): the basis badge names the type-application scope id the scores use.
        assert.match(await page.locator('[data-scoring-default]').first().textContent(), /유형 범위 qgv2-type-scope\/\d{4}-\d{2}-\d{2}\.\d+$/);
        assert.equal(await page.locator('[data-qgv2-preset]').count(), 4);
        assert.equal(await page.locator('[data-qgv2-preset="balanced"]').getAttribute('aria-pressed'), 'true');
        await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        const nvda = page.locator('[data-leaderboard-row="nvda"]'), msft = page.locator('[data-leaderboard-row="msft"]'), gev = page.locator('[data-leaderboard-row="gev"]');
        {
          const text = await nvda.locator('[data-leaderboard-qgv2]').textContent();
          assert.match(text, /^QGV \d+\.\d · Q \d+\.\d · G \d+\.\d · V \d+\.\d · 산출 요인 1[0-5]\/15$/);
          assert.match(await msft.locator('[data-leaderboard-qgv2]').textContent(), / V — · 산출 요인 1\d\/15$/);
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
          assert.notEqual(await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qgv2]').textContent(), before);
          await page.locator('[data-qgv2-gate]').uncheck();await page.locator('[data-qgv2-state]').filter({ hasText: '관문 끔' }).waitFor();
          assert.equal(await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 0);assert.equal(await msft.locator('[data-qgv2-flag]').filter({ hasText: 'V 없음' }).count(), 1);assert.equal(await gev.locator('[data-qgv2-flag]').count(), 0);
          // v2 NOT_AVAILABLE rows say why (never a v1 fallback).
          assert.match(await gev.locator('[data-leaderboard-qgv2]').textContent(), /^QGV v2 산출 불가 · /);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S06');
        if (mode === 'v2') await flow(page, width);
        phase = 'S13';await page.goto(BASE + '#profiles');await page.locator('[data-profile-editor]').waitFor();
        assert.equal(await page.locator('[data-profile-v2] h3').count(),1);
        {assert.equal(await page.locator('[data-v2-official-axis]').count(),3);assert.equal(await page.locator('[data-v2-preset]').count(),4);assert.equal(await page.locator('[data-v2-performance]').getAttribute('data-v2-performance'),'NOT_AVAILABLE');}
        assert.ok(!/v1 비교용|비교용 · v1|임시 기본/.test(await page.locator('[data-profile-official]').textContent()));assert.equal(await page.locator('[data-official-axis]').count(),0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S13');
        phase = 'S04';await page.goto(BASE + '#company/nvda');await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-badges] [data-scoring-default]').getAttribute('data-scoring-default'), 'v2');
        assert.ok((await page.locator('[data-company-badges] [data-scoring-default]').textContent()).includes(' · 유형 범위 qgv2-type-scope/'), 'S04/S05 basis badge records the type scope');
        {
          await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
          assert.match(await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent(), /\d/);
          assert.match(await page.locator('[data-qgv2-summary]').textContent(), /산출 요인 1[0-5]\/15 · qgv-v2\/value\/gate-off/);
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
          assert.match(await panel.locator('[data-v2-factor="v_vs_own_history"]').textContent(), /NORMALIZED_HISTORY_NOT_AVAILABLE/);
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
        if (mode === 'v2') {
          // A star toggled from the S06 list keeps keyboard focus after the list is re-rendered.
          phase = 'STAR_FOCUS';await page.goto(BASE + '#leaderboard');const starButton = page.locator('#leader-company-list [data-star="amd"]');await starButton.focus();await page.keyboard.press('Enter');
          await page.waitForFunction(() => document.activeElement?.dataset?.star === 'amd' && document.activeElement.isConnected && document.activeElement.getAttribute('aria-pressed') === 'true');
        }
        assert.deepEqual(external, [], 'no request to another origin');
        assert.equal(errors, 0);pass++;console.log('PASS QGV v2 screens ' + mode + ' ' + width);
      } catch (e) { fail++;console.log('FAIL QGV v2 screens ' + mode + ' ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);process.exitCode = fail ? 1 : 0;
})();
