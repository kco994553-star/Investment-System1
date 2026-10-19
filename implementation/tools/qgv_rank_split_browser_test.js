'use strict';
// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다') on the real user path at 390 and 1280:
// S06 before any device price: no official QGV ranking ('가격 연결 전: 공식 QGV 순위 없음 · QG 참고 목록 보기') and the QG 참고 목록
// (V 미포함) is shown; after a Universe read with SYNTHETIC FIXTURE PRICES (made-up numbers, never real prices, a stubbed sheet read
// in RAM): only rows with V are ranked, the value-trap-gate row (V computed, excluded by the approved gate) stays ranked with its
// flag, the financial rows and the unpriced row are in the QG list with their reasons; S06 V per row == the shared
// QgvScores.pageResult V, and the V coverage panel's counts agree (QG list rows == qg_only_total.full, ranked == rows with V and a
// total, gate rows included); search and the company detail still open those companies; a personal profile with V weight 0 is
// labelled '개인 설정 결과 (V 비중 0)' and the official ranking does not move. Q·G side: the strictly valid synthetic fixture with
// TARGET amd made weak in Q (as in preset_candidates_browser_test.js) so the gate fires.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, E = '[data-leaderboard-explore]';
function gatedPayload() {
  const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js'), p = F.strictPayload(), amd = p.target.amd;
  Object.assign(amd.metrics, { roic: -0.5, gross_profit_to_assets: -0.5, moat_proxy: -0.5, accruals_to_assets: 0.5, fcf_to_net_income: -2, net_debt_to_ebitda: 20, interest_coverage: -5, dilution_3y: 0.5, incremental_roic_5y: -0.5 });
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version), sc = scores.get('target\u0000amd');amd.factors = sc.factors;amd.axes = sc.axes;
  SQ.validate(p);return p;
}
// The S06 result, the shared page result and the panel counts, read from the running page (same inputs, catalog, identities).
const state = (page) => page.evaluate(async () => {
  const inputs = publicScreens[Qgv2Inputs.FILE], R = await QgvScores.pageResult(window, { v2Inputs: inputs, catalog: await deviceCatalog().catch(() => null), identities: identityCompanies, preset: qgv2Profile.preset, gate: qgv2Profile.gate });
  const S = leaderScores(), fin = (x) => typeof x === 'number' && Number.isFinite(x), cov = QgvScores.vCoverage(R, inputs);
  const rows = Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, { rank: r.rank, qg: r.qg_reference, v: r.primary.v, total: r.primary.total, gate: r.primary.value_trap_gate === true, flags: r.primary.flags, page_v: R.computed.rows[k] ? R.computed.rows[k].primary.v : 'MISSING', page_total: R.computed.rows[k] ? R.computed.rows[k].primary.total : 'MISSING' }]));
  // D12: one row per Universe code (a TARGET company's code is its TARGET row): the rows standing for the codes of the file.
  const uni = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).map((c) => R.computed.rows[R.computed.official.by_code[c]]).filter(Boolean);
  return { rows, priced: S.priced_codes, evaluated: S.official ? S.official.evaluated : null, codes: Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).length, cov: cov ? { connected: cov.connected, qg_full: cov.qg_only_total ? cov.qg_only_total.full : null, gate: cov.qg_only_total ? cov.qg_only_total.gate : null, v_full: cov.v ? cov.v.full : null } : null,
    uni: { qg: uni.filter((r) => r.qg_reference).length, ranked: uni.filter((r) => Number.isInteger(r.rank)).length, vTotal: uni.filter((r) => fin(r.primary.v) && fin(r.primary.total)).length, gateRanked: uni.filter((r) => r.primary.value_trap_gate && Number.isInteger(r.rank)).length,
      gateRows: uni.filter((r) => fin(r.primary.v) && fin(r.primary.total) && r.primary.v_excluded).length, mixed: uni.filter((r) => Number.isInteger(r.rank) && !fin(r.primary.v)).length } };
});
const rowIds = (page) => page.locator('[data-leaderboard-table] tbody tr[data-leaderboard-row]').evaluateAll((rs) => rs.map((r) => r.dataset.leaderboardRow));
const officialSnapshot = (page) => page.evaluate(() => JSON.stringify(Object.entries(leaderScores().rows).map(([k, r]) => [k, r.rank, r.qg_reference, r.primary.total, r.primary.v])));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const payload = gatedPayload();
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, F.strictUniverseValues());
        // Before any device price: no official rank; the QG list is offered and opens.
        phase = 'BEFORE_PRICE';await page.locator('[data-leaderboard-table]').waitFor();const note = page.locator('[data-leaderboard-official="BEFORE_PRICE"]');await note.waitFor();
        assert.equal(await note.textContent(), '가격 연결 전: 공식 QGV 순위 없음 · QG 참고 목록 보기');assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        await note.locator('[data-leaderboard-qg-open]').click();await page.locator(E + '[data-leaderboard-explore="qg"]').waitFor();
        assert.equal(await page.locator('[data-leaderboard-list-title="QG_REFERENCE"]').textContent(), 'QG 참고 목록 (V 미포함)');
        const before = await rowIds(page), s0 = await state(page);
        assert.ok(before.length >= 3, 'QG list shown before prices: ' + JSON.stringify(before));assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        assert.deepEqual(before, Object.entries(s0.rows).filter(([, r]) => r.qg).sort((a, b) => a[1].qg.order - b[1].qg.order).map(([k]) => k), 'QG list in its own order by total');
        assert.ok(Object.values(s0.rows).every((r) => r.rank === null), 'no official rank before prices');
        for (const id of before) assert.match(await page.locator('[data-leaderboard-row="' + id + '"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), /^QG 참고 목록 \(V 미포함\) · \d+번 · 공식 순위 아님 · /);
        assert.equal(await page.locator('[data-leaderboard-row="msft"] [data-leaderboard-unranked="QG_REFERENCE"]').getAttribute('data-qg-reason'), 'NO_DEVICE_PRICE');
        // Universe read (synthetic prices; MSFT is left unpriced by the fixture).
        phase = 'READ';await page.locator(E + ' [data-leaderboard-explore-option="all"]').click();await page.locator(E + '[data-leaderboard-explore="all"]').waitFor();
        await page.locator('details:has(#private-subset-root) > summary').click();await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-v-coverage="READY"]').waitFor();await page.locator('[data-leaderboard-rank]').first().waitFor();
        phase = 'AFTER_PRICE';const s = await state(page), R = s.rows;
        assert.ok(s.priced > 0);assert.equal(await page.locator('[data-leaderboard-official]').count(), 0, 'official ranking exists after prices');
        // Only rows with V are ranked; the gate row (amd: V computed, excluded by the gate) stays ranked with its flag.
        for (const [id, r] of Object.entries(R)) {
          const hasV = Number.isFinite(r.v), hasTotal = Number.isFinite(r.total);
          assert.equal(Number.isInteger(r.rank), hasV && hasTotal, id + ' ranked iff V and a total');assert.equal(!!r.qg, hasTotal && !hasV, id + ' QG list iff a total without V');
          // Same input, same V: S06 equals the shared page result row by row.
          assert.ok(Object.is(r.v, r.page_v) && Object.is(r.total, r.page_total), id + ' S06 V/total == pageResult');
        }
        assert.equal(R.amd.gate, true, 'gate fixture');assert.ok(Number.isInteger(R.amd.rank), 'gate row stays ranked');assert.ok(R.amd.flags.includes('VALUE_TRAP_CAUTION'));
        assert.match(await page.locator('[data-leaderboard-row="amd"] [data-leaderboard-rank]').textContent(), /^\d+$/);
        assert.equal(await page.locator('[data-leaderboard-row="amd"] [data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 1);
        assert.equal(await page.locator('[data-leaderboard-row="amd"] [data-leaderboard-unranked]').count(), 0);
        assert.equal(R.msft.qg.reason, 'NO_DEVICE_PRICE');assert.equal(R.googl.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');assert.equal(R.amzn.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');
        assert.match(await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), / · 현재 금융업 가치평가 모델 미지원$/);
        assert.match(await page.locator('[data-leaderboard-row="msft"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), / · 가격 입력 필요: /);
        // The QG rows keep their engine total on screen (display split only, no formula change).
        assert.equal(await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-total]').getAttribute('data-leaderboard-total'), (Math.round(R.googl.total * 10) / 10).toFixed(1));
        // Default QGV order: the official ranking first, then the QG list; never interleaved.
        const order = await rowIds(page), tier = (id) => (R[id] && Number.isInteger(R[id].rank) ? 0 : R[id] && R[id].qg ? 1 : 2);
        for (let i = 1; i < order.length; i++) assert.ok(tier(order[i]) >= tier(order[i - 1]), 'order ' + JSON.stringify(order.map(tier)));
        const counts = await page.locator(E + ' button').evaluateAll((b) => Object.fromEntries(b.map((x) => [x.dataset.leaderboardExploreOption, Number(x.textContent.match(/(\d+)$/)[1])])));
        assert.equal(counts.ranked, Object.values(R).filter((r) => Number.isInteger(r.rank)).length);assert.equal(counts.qg, Object.values(R).filter((r) => r.qg).length);
        assert.equal(await page.locator('[data-leaderboard-counts]').getAttribute('data-qg-reference'), String(counts.qg));
        // The counts line and the footnote (D3, PR #320: data-ranked of [data-leaderboard-rank-scope], when present) name the same
        // official ranked count as the D11 split; the rank population stays the S06 identities.
        assert.equal(await page.locator('[data-leaderboard-counts]').getAttribute('data-rankable'), String(counts.ranked));
        const scope = page.locator('[data-leaderboard-rank-scope]');
        // D12: the rank base is the Universe of the file (one row per code), not the screen identities.
        if (await scope.count()) { assert.equal(await scope.getAttribute('data-ranked'), String(counts.ranked), 'footnote ranked == official ranked');assert.equal(s.evaluated, s.codes);assert.equal(await scope.getAttribute('data-rank-base'), String(s.codes));assert.equal(await scope.getAttribute('data-rank-population'), 'UNIVERSE'); }
        else console.log('INFO ' + width + ' footnote rank scope (D3, #320) not on this build: footnote check skipped');
        // The V coverage panel (same page result): QG list rows == qg_only_total.full; ranked == rows with V and a total (gate included).
        phase = 'PANEL';assert.equal(s.cov.connected, true);assert.equal(s.uni.qg, s.cov.qg_full);assert.equal(s.uni.ranked, s.uni.vTotal);assert.equal(s.uni.mixed, 0);
        assert.equal(s.uni.gateRows, s.cov.gate);assert.equal(s.uni.gateRanked, s.uni.gateRows);
        assert.equal(Number(await page.locator('[data-qg-only-full]').getAttribute('data-qg-only-full')), s.uni.qg, 'panel count == QG list rows');
        assert.equal(Number(await page.locator('[data-v-full]').getAttribute('data-v-full')), s.cov.v_full);
        // Explore views: titled official list and QG list.
        phase = 'VIEWS';await page.locator(E + ' [data-leaderboard-explore-option="ranked"]').click();await page.locator(E + '[data-leaderboard-explore="ranked"]').waitFor();
        assert.equal(await page.locator('[data-leaderboard-list-title="RANKED"]').textContent(), '공식 QGV 순위 (V 산출 기업)');
        assert.deepEqual((await rowIds(page)).sort(), Object.keys(R).filter((k) => Number.isInteger(R[k].rank)).sort());
        await page.locator(E + ' [data-leaderboard-explore-option="qg"]').click();await page.locator(E + '[data-leaderboard-explore="qg"]').waitFor();
        assert.deepEqual(await rowIds(page), Object.keys(R).filter((k) => R[k].qg).sort((a, b) => R[a].qg.order - R[b].qg.order));assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide scroll');
        // Detail: a QG-list company opens and says which list it is in (no official rank).
        phase = 'DETAIL';await page.locator('[data-leaderboard-row="googl"] a[href="#company/googl"]').click();await page.locator('[data-qgv-coverage]').waitFor();
        assert.equal(await page.locator('[data-qgv-usable]').getAttribute('data-qgv-usable'), 'QG_REFERENCE');
        assert.match(await page.locator('[data-qgv-usable]').textContent(), /^기기 순위: QG 참고 목록 \(V 미포함\) · \d+번 · 공식 QGV 순위 아님 · 현재 금융업 가치평가 모델 미지원$/);
        assert.match(await page.locator('[data-qgv="rank"]').textContent(), /^QG 참고 목록 \(V 미포함\) · \d+번 · 공식 QGV 순위 아님/);
        assert.notEqual(await page.locator('[data-qgv="total"]').textContent(), 'NOT_AVAILABLE');
        // Search: the unpriced company is found and its detail opens too.
        phase = 'SEARCH';await page.goto(BASE + '#home');await page.locator('#global-search').waitFor();await page.locator('#global-search').fill('MSFT');
        const hit = page.locator('#global-results li a[href="#company/msft"]').first();await hit.waitFor();await hit.click();await page.locator('[data-qgv-usable]').waitFor();
        assert.equal(await page.locator('[data-qgv-usable]').getAttribute('data-qgv-usable'), 'QG_REFERENCE');assert.match(await page.locator('[data-qgv-usable]').textContent(), /가격 입력 필요/);
        // Universe504 page of a financial code: its Q·G-only total is labelled, not a rank.
        phase = 'UNIVERSE';await page.goto(BASE + '#company/' + encodeURIComponent('NASDAQ:GOOGL'));const uc = page.locator('[data-uc-qg-reference]');await uc.waitFor();
        assert.equal(await uc.getAttribute('data-uc-qg-reference'), 'FINANCIAL_PROFILE_V_NOT_DEFINED');assert.match(await uc.textContent(), /^QG 참고 목록 \(V 미포함\) · 공식 QGV 순위 대상 아님 · 현재 금융업 가치평가 모델 미지원$/);
        // Personal profile with V weight 0: labelled as a personal-setting result; the official ranking does not move.
        phase = 'PERSONAL_V0';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();const official = await officialSnapshot(page);
        await page.goto(BASE + '#profiles');const W = '[data-qgv2-weights-editor]';await page.locator(W).waitFor();
        await page.locator('#qgv2w-axis-Q').fill('50');await page.locator('#qgv2w-axis-G').fill('50');await page.locator('#qgv2w-axis-V').fill('0');await page.locator(W + ' [data-qgv2w-compare]').click();
        const label = page.locator('[data-qgv2w-result-label="V_WEIGHT_ZERO"]');await label.waitFor();
        assert.match(await label.textContent(), /^개인 설정 결과 \(V 비중 0\) · 공식 순위 아님 · qgv-v2\/custom\//);
        assert.equal(await page.locator('[data-qgv2w-top-title="V_WEIGHT_ZERO"]').textContent(), '상위 목록 · 개인 설정 결과 (V 비중 0) 순 · 공식 순위 아님');
        await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();assert.equal(await officialSnapshot(page), official, 'official ranking unchanged by the personal V=0 result');
        assert.deepEqual(external, []);assert.equal(errors, 0);
        console.log('INFO ' + width + ' S06 ranked=' + counts.ranked + ' qg=' + counts.qg + ' · Universe ranked=' + s.uni.ranked + ' qg=' + s.uni.qg + ' (panel qg_only_total.full=' + s.cov.qg_full + ') gate ranked=' + s.uni.gateRanked + '/' + s.cov.gate + ' · before-price QG=' + before.length);
        pass++;console.log('PASS D11 rank split ' + width + ' (synthetic fixture + synthetic prices)');
      } catch (e) { fail++;console.log('FAIL D11 rank split ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
