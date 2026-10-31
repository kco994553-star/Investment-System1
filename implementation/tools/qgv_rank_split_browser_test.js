'use strict';
// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다') on the real user path at 390 and 1280, DC-31 (owner
// decision 2026-10-31, device V abolished: screens show only the central V of qgv-official.json, no Universe read, no price):
// S06 without a central publication: no official QGV ranking ('공식 V 없음: 공식 QGV 순위 없음 · <reason>') and the QG 참고 목록
// (V 미포함) is shown, every V NA with its OFFICIAL_* reason; with the synthetic central publication (qgv_official_fixture.js over
// the strictly valid synthetic sec-qgv2.json of qgv_v2_fixture.js): only rows with a published V are ranked, in the published
// order; the value-trap-gate row (NASDAQ:ABNB: V published, left out by the gate) stays ranked with its flag; the financial rows and
// the row without an IEX trade (NYSE:MMM) are in the QG list with their reasons; S06 equals the shared QgvScores.officialPage
// row by row and the V coverage panel shows the publication's counts (ranked, QG list); S06 and S04 show the central basis line
// and the IEX attribution; search and the company detail still open those companies; a personal profile with V weight 0 is
// labelled '개인 설정 결과 (V 비중 0)' and the official ranking does not move.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, E = '[data-leaderboard-explore]';
// The S06 result and the shared official page result, read from the running page (same inputs and identities).
const state = (page) => page.evaluate(() => {
  const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), C = QgvScores.presetView(P, { v2Inputs: inputs });
  const S = leaderScores(), fin = (x) => typeof x === 'number' && Number.isFinite(x), inU = new Set(Object.values(C.official.by_code));
  const rows = Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, { rank: r.rank, qg: r.qg_reference, v: r.primary.v, total: r.primary.total, gate: r.primary.value_trap_gate === true, flags: r.primary.flags, page_v: C.rows[k] ? C.rows[k].primary.v : 'MISSING', page_total: C.rows[k] ? C.rows[k].primary.total : 'MISSING', page_rank: C.rows[k] ? C.rows[k].rank : 'MISSING', universe: inU.has(k), group: QgvScores.exploreGroup(r), rank_row: r.rank_row || null }]));
  // D12: one row per Universe code (a TARGET company's code is its TARGET row): the rows standing for the codes of the file.
  const uni = [...new Set(Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).map((c) => C.official.by_code[c]).filter(Boolean))].map((id) => C.rows[id]).filter(Boolean);
  return { source: P.source, v_reason: P.v_reason, rows, evaluated: S.official ? S.official.evaluated : null, codes: Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).length,
    uni: { qg: uni.filter((r) => r.qg_reference).length, ranked: uni.filter((r) => Number.isInteger(r.rank)).length, vTotal: uni.filter((r) => fin(r.primary.v) && fin(r.primary.total)).length, gateRanked: uni.filter((r) => r.primary.value_trap_gate && Number.isInteger(r.rank)).length, mixed: uni.filter((r) => Number.isInteger(r.rank) && !fin(r.primary.v)).length } };
});
const rowIds = (page) => page.locator('[data-leaderboard-table] tbody tr[data-leaderboard-row]').evaluateAll((rs) => rs.map((r) => r.dataset.leaderboardRow));
const officialSnapshot = (page) => page.evaluate(() => JSON.stringify(Object.entries(leaderScores().rows).map(([k, r]) => [k, r.rank, r.qg_reference, r.primary.total, r.primary.v])));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const payload = F.strictPayload(), C = O.PUB.coverage;
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) }));
      const served = { pub: false };await context.route('**/qgv-official.json*', (r) => r.fulfill(served.pub ? { status: 200, contentType: 'application/json', body: O.PUB_TEXT } : { status: 404, contentType: 'text/plain', body: 'not found' }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        // Without a central publication: no official rank; the QG list is offered and opens; every V NA with the OFFICIAL_* reason.
        phase = 'NO_PUBLICATION';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
        const note = page.locator('[data-leaderboard-official="NO_OFFICIAL_V"]');await note.waitFor();await page.waitForFunction(() => QgvScores.pagePublication().reason !== 'OFFICIAL_LOADING');
        const s0 = await state(page);assert.equal(s0.source, 'NONE');assert.match(s0.v_reason, /^OFFICIAL_(NOT_PUBLISHED|UNAVAILABLE)$/);
        assert.equal(await note.textContent(), '공식 V 없음: 공식 QGV 순위 없음 · ' + await page.evaluate((r) => QgvScores.reasonText(r, false), s0.v_reason) + ' · QG 참고 목록 보기');assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        assert.equal(await page.locator('[data-leaderboard-central] [data-central-basis]').getAttribute('data-central-state'), 'NA');assert.equal(await page.locator('[data-leaderboard-central] [data-attribution]').count(), 0);
        await note.locator('[data-leaderboard-qg-open]').click();await page.locator(E + '[data-leaderboard-explore="qg"]').waitFor();
        assert.equal(await page.locator('[data-leaderboard-list-title="QG_REFERENCE"]').textContent(), 'QG 참고 목록 (V 미포함)');
        const before = await rowIds(page);
        assert.ok(before.length >= 3, 'QG list shown without a publication: ' + JSON.stringify(before));
        assert.deepEqual(before, Object.entries(s0.rows).filter(([, r]) => r.qg).sort((a, b) => a[1].qg.order - b[1].qg.order).map(([k]) => k), 'QG list in its own order by total');
        assert.ok(Object.values(s0.rows).every((r) => r.rank === null && !Number.isFinite(r.v)), 'no official rank and no V without a publication');
        for (const id of before) assert.match(await page.locator('[data-leaderboard-row="' + id + '"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), /^QG 참고 목록 \(V 미포함\) · \d+번 · 공식 순위 아님 · /);
        assert.equal(await page.locator('[data-leaderboard-row="msft"] [data-leaderboard-unranked="QG_REFERENCE"]').getAttribute('data-qg-reason'), s0.v_reason);
        // The central publication arrives (page opened again: the one read on open).
        phase = 'PUBLICATION';served.pub = true;await page.reload();await page.locator('[data-leaderboard-table]').waitFor();
        await page.locator(E + ' [data-leaderboard-explore-option="all"]').click();await page.locator(E + '[data-leaderboard-explore="all"]').waitFor();await page.locator('[data-leaderboard-rank]').first().waitFor();
        phase = 'AFTER_PUBLICATION';const s = await state(page), R = s.rows;
        assert.equal(s.source, 'PUBLICATION');assert.equal(await page.locator('[data-leaderboard-official]').count(), 0, 'official ranking exists with the publication');
        assert.equal(await page.locator('[data-leaderboard-central] [data-central-basis]').getAttribute('data-central-basis'), O.PUB.publication_id);
        assert.equal(await page.locator('[data-leaderboard-central] [data-attribution] a').getAttribute('href'), O.PUB.attribution.terms_url);
        // Only rows with a published V are ranked; the gate row (NASDAQ:ABNB: V published, left out by the gate) stays ranked with its flag.
        for (const [id, r] of Object.entries(R)) {
          const hasV = Number.isFinite(r.v), hasTotal = Number.isFinite(r.total);
          if (!r.universe) { assert.equal(r.rank, null, id + ' outside the Universe: no official rank');continue; }
          // The rank is the published one: a ranked row has V and a total; a QG row has a total without V; never both.
          if (Number.isInteger(r.rank)) assert.ok(hasV && hasTotal && !r.qg, id + ' ranked => V and a total');if (r.qg) assert.ok(hasTotal && !hasV && r.rank === null, id + ' QG list => a total without V');
          // Same publication, same V: S06 equals the shared official page result row by row.
          assert.ok(Object.is(r.v, r.page_v) && Object.is(r.total, r.page_total) && Object.is(r.rank, r.page_rank), id + ' S06 V/total/rank == officialPage');
        }
        const G = 'NASDAQ:ABNB', M = 'NYSE:MMM';
        assert.equal(R[G].gate, true, 'gate fixture');assert.equal(R[G].rank, O.RANKS[G], 'gate row keeps its published rank');assert.ok(R[G].flags.includes('VALUE_TRAP_CAUTION'));assert.equal(R.amd.rank, O.RANKS['TARGET:amd']);
        assert.match(await page.locator('[data-leaderboard-row="' + G + '"] [data-leaderboard-rank]').textContent(), /^\d+$/);
        assert.equal(await page.locator('[data-leaderboard-row="' + G + '"] [data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 1);
        assert.equal(await page.locator('[data-leaderboard-row="' + G + '"] [data-leaderboard-unranked]').count(), 0);
        assert.equal(R[M].qg.reason, 'NO_IEX_TRADE');assert.equal(R.googl.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');assert.equal(R.amzn.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');
        assert.match(await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), / · 현재 금융업 가치평가 모델 미지원$/);
        assert.match(await page.locator('[data-leaderboard-row="' + M + '"] [data-leaderboard-unranked="QG_REFERENCE"]').textContent(), / · 공식 V 없음: /);
        // The QG rows keep their engine total on screen (display split only, no formula change).
        assert.equal(await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-total]').getAttribute('data-leaderboard-total'), (Math.round(R.googl.total * 10) / 10).toFixed(1));
        // Default QGV order: the official ranking first, then the QG list; never interleaved.
        const order = await rowIds(page), tier = (id) => (R[id] && Number.isInteger(R[id].rank) ? 0 : R[id] && R[id].qg ? 1 : 2);
        for (let i = 1; i < order.length; i++) assert.ok(tier(order[i]) >= tier(order[i - 1]), 'order ' + JSON.stringify(order.map(tier)));
        const counts = await page.locator(E + ' button').evaluateAll((b) => Object.fromEntries(b.map((x) => [x.dataset.leaderboardExploreOption, Number(x.textContent.match(/(\d+)$/)[1])])));
        assert.equal(counts.ranked, Object.values(R).filter((r) => r.universe && Number.isInteger(r.rank)).length);assert.equal(counts.qg, Object.values(R).filter((r) => r.universe && r.group === 'QG_REFERENCE').length);
        // D11 one place per issuer: a second code of an issuer (rank_row) has a Q·G total but no place of its own in the list order.
        for (const r of Object.values(R).filter((x) => x.universe && x.group === 'QG_REFERENCE' && !x.qg)) assert.ok(r.rank_row, 'a QG-group row without an order points to its issuer place');
        assert.equal(await page.locator('[data-leaderboard-counts]').getAttribute('data-qg-reference'), String(counts.qg));
        // The counts line and the footnote (D3, PR #320: data-ranked of [data-leaderboard-rank-scope], when present) name the same
        // official ranked count as the D11 split; the rank population stays the S06 identities.
        assert.equal(await page.locator('[data-leaderboard-counts]').getAttribute('data-rankable'), String(counts.ranked));
        const scope = page.locator('[data-leaderboard-rank-scope]');
        // D12: the rank base is the Universe of the file (one row per code), not the screen identities.
        if (await scope.count()) { assert.equal(await scope.getAttribute('data-ranked'), String(counts.ranked), 'footnote ranked == official ranked');assert.equal(s.evaluated, s.codes);assert.equal(await scope.getAttribute('data-rank-base'), String(s.codes));assert.equal(await scope.getAttribute('data-rank-population'), 'UNIVERSE'); }
        else console.log('INFO ' + width + ' footnote rank scope (D3, #320) not on this build: footnote check skipped');
        // The V coverage panel shows the publication's counts: ranked and QG list == the S06 Universe rows (one place per issuer).
        phase = 'PANEL';assert.equal(s.uni.ranked, C.ranked);assert.equal(s.uni.qg, C.qg_reference);assert.ok(s.uni.ranked <= s.uni.vTotal, 'only published places are ranked');assert.equal(s.uni.mixed, 0);assert.ok(s.uni.gateRanked >= 1);
        assert.equal(Number(await page.locator('[data-v-coverage] [data-ranked]').getAttribute('data-ranked')), s.uni.ranked, 'panel ranked == S06 ranked');
        assert.equal(Number(await page.locator('[data-v-coverage] [data-qg-reference]').getAttribute('data-qg-reference')), s.uni.qg, 'panel QG list == S06 QG list');
        assert.equal(Number(await page.locator('[data-v-coverage] [data-v-full]').getAttribute('data-v-full')), C.v.full);
        // Explore views: titled official list and QG list.
        phase = 'VIEWS';await page.locator(E + ' [data-leaderboard-explore-option="ranked"]').click();await page.locator(E + '[data-leaderboard-explore="ranked"]').waitFor();
        assert.equal(await page.locator('[data-leaderboard-list-title="RANKED"]').textContent(), '공식 QGV 순위 (V 산출 기업)');
        assert.deepEqual((await rowIds(page)).sort(), Object.keys(R).filter((k) => Number.isInteger(R[k].rank)).sort());
        await page.locator(E + ' [data-leaderboard-explore-option="qg"]').click();await page.locator(E + '[data-leaderboard-explore="qg"]').waitFor();
        const qgShown = await rowIds(page), ordered = Object.keys(R).filter((k) => R[k].qg).sort((a, b) => R[a].qg.order - R[b].qg.order);
        assert.deepEqual(qgShown.filter((k) => R[k].qg), ordered, 'the QG list in its published order');assert.ok(qgShown.every((k) => R[k].qg || R[k].rank_row), 'other rows only as the second code of an issuer');assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide scroll');
        // Detail: a QG-list company opens and says which list it is in (no official rank).
        phase = 'DETAIL';await page.locator('[data-leaderboard-row="googl"] a[href="#company/googl"]').click();await page.locator('[data-qgv-coverage]').waitFor();
        assert.equal(await page.locator('[data-qgv-usable]').getAttribute('data-qgv-usable'), 'QG_REFERENCE');
        assert.match(await page.locator('[data-qgv-usable]').textContent(), /^순위: QG 참고 목록 \(V 미포함\) · \d+번 · 공식 QGV 순위 아님 · 현재 금융업 가치평가 모델 미지원$/);
        assert.equal(await page.locator('[data-qgv-central] [data-central-basis]').getAttribute('data-central-basis'), O.PUB.publication_id, 'S04 basis line');
        assert.equal(await page.locator('[data-qgv-central] [data-attribution] a').getAttribute('href'), O.PUB.attribution.terms_url, 'S04 IEX terms link');
        assert.match(await page.locator('[data-qgv="rank"]').textContent(), /^QG 참고 목록 \(V 미포함\) · \d+번 · 공식 QGV 순위 아님/);
        assert.notEqual(await page.locator('[data-qgv="total"]').textContent(), 'NOT_AVAILABLE');
        // Search: a TARGET company is found and its detail opens too.
        phase = 'SEARCH';await page.goto(BASE + '#home');await page.locator('#global-search').waitFor();await page.locator('#global-search').fill('MSFT');
        const hit = page.locator('#global-results li a[href="#company/msft"]').first();await hit.waitFor();await hit.click();await page.locator('[data-qgv-usable]').waitFor();
        assert.doesNotMatch(await page.locator('[data-qgv-usable]').textContent(), /가격 입력 필요|기기 순위/);
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
        console.log('INFO ' + width + ' S06 ranked=' + counts.ranked + ' qg=' + counts.qg + ' · Universe ranked=' + s.uni.ranked + ' qg=' + s.uni.qg + ' (publication ranked=' + C.ranked + ' qg=' + C.qg_reference + ') gate ranked=' + s.uni.gateRanked + ' · no-publication QG=' + before.length);
        pass++;console.log('PASS D11 rank split ' + width + ' (synthetic fixture + synthetic central publication)');
      } catch (e) { fail++;console.log('FAIL D11 rank split ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 6).join(' | ') + ' @' + ((e.stack || '').match(/browser_test.js:(\d+)/) || [])[1] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
