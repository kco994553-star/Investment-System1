'use strict';
// Feature 3.5 · 1.1.8 기술 조건 필터 (owner 2026-11-03 "계층 3 기술적 분석 리더보드 화면") in a real browser at 1440×1000 and 390×844.
// Builds the development site (tools/web_app_test_site.js) with the leaderboard's synthetic score fixtures and checks #/qgv:
//  - Real source (IS2.techScreen.source → NONE, no request): the block says 기술 지표 자료가 아직 없습니다 with the flow and the five
//    metric definitions (변동성 D10 = 크게 흔들린 집단, 거래대금 D10 = 거래 규모가 큰 집단); the table has no tech column.
//  - A synthetic tech-screen-v0 file (tools/web_app_tech_filter_fixture.js over the leaderboard's own Universe rows) put in place of
//    source(): status 합성 데이터 · 시험용; ① 평가일 · 비교 그룹; ② five metric cards with unit, 기준일, 비교 그룹, 유효 종목 n / members
//    and the D10 reading; ③ the owner's example "U-B에서 6개월 모멘텀 D10이고 변동성 D10은 제외한 뒤 QGV 순": the table shows exactly
//    the PASS rows in the leaderboard's QGV order (I.qgvLive.helpers.sortRows), counts equal IS2.techScreen.evaluate, the 판정 불가
//    list names the company without volatility with its reason, a PASS row shows a negative 6-month momentum with D10 (market
//    down), and the cards' denominators and the rows' deciles are the same before and after the filters.
//  - Zero matches (6개월 모멘텀 0% 초과 on the down day): 계산은 정상 · 조건을 모두 만족하는 종목 0개 and the table's tech empty row.
//  - Values without deciles (group too small): cards and cells say 분위 없음 with the reason; top10 → every row 판정 불가.
//  - Phone: the tech line under each row, '기술 상세' with 분모 · 관측 · 사유, no horizontal overflow, 44 px controls.
//  - An invalid file: the whole file refused (계약과 달라 …), the leaderboard unchanged without a tech column.
//  - Boundaries: tech values only as text inside [data-ram-price] (assertRamOnly with the formatted dollar volumes), no request
//    outside the origin, no new data request, no storage, no console error, CSP 0.
// TECH_SHOTS=<dir> also saves screenshots (deviceScaleFactor 2) for the PR; nothing is written otherwise.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_tech_filter_fixture.js');
const T = require('../src/investment_system/product/web_app/tech-screen.js');

const NOW = '2026-10-14T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
const SHOTS = process.env.TECH_SHOTS || null;
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      const at = s.requests.length;
      const B = '[data-lb="3.5"]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const drawnIds = () => page.$$eval('[data-lb-table] tbody tr[data-row]', (trs) => trs.map((t) => t.dataset.row));
      const reopen = async () => {
        await page.evaluate(() => { location.hash = '#/macro'; }); await page.locator('main[data-route=macro]').waitFor();
        await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route=qgv]').waitFor();
        await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor(); };
      const swap = (answer) => page.evaluate((a) => { const I = window.IS2, real = I.techScreen; I.__realTech = I.__realTech || real;
        I.techScreen = Object.freeze({ ...I.__realTech, source: () => Promise.resolve(a) }); }, answer);

      // ---------------- real source: NONE
      phase = tag + ' none';
      await page.locator(B + ' [data-tech-state=NONE]').waitFor();
      const none = await text(B);
      assert.ok(none.includes(T.TEXT.NONE) && none.includes('① 평가일·비교 그룹'), 'NONE words and flow');
      assert.equal(await page.locator(B + ' [data-metric-def]').count(), 5);
      assert.ok(none.includes('가장 크게 흔들린 10%') && none.includes('거래 규모가 가장 큰 10%'), 'D10 readings');
      assert.equal(await page.locator('[data-lb-table] [data-cell=tech]').count(), 0, 'no tech column');
      ok(tag + ' real source NONE: words, flow, definitions, no tech column');

      // ---------------- synthetic file over the leaderboard's own rows (unscored first, so scored rows reach the top deciles)
      phase = tag + ' synthetic';
      const cos = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page();
        const rows = Q.rows(pg, { scope: 'UNIVERSE' }).map((r) => ({ id: r.id, ticker: r.ticker, t: typeof r.score.total === 'number' ? r.score.total : null }));
        return rows.sort((a, b) => (a.t !== null) - (b.t !== null) || (a.t !== null ? a.t - b.t : 0) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)).map(({ id, ticker }) => ({ id, ticker })); });
      const P = X.payload(cos), C = X.cases(P, 0);
      assert.equal(T.validate(P).ok, true);
      await swap({ state: 'OK', code: null, payload: P, text: '' }); await reopen();
      await page.locator(B + ' [data-tech-data=SYNTHETIC]').waitFor();
      assert.ok((await text(B + ' [data-tech-data]')).includes('합성 데이터 · 시험용'));
      await page.selectOption('#tf-day', X.DAYS[0]); await page.selectOption('#tf-group', 'U_B');
      await page.locator(B + ' [data-metric-card]').first().waitFor();
      const ev0 = P.evaluations[0], gB = ev0.groups.find((g) => g.id === 'U_B');
      const cards = async () => page.$$eval(B + ' [data-metric-card]', (els) => els.map((e) => ({ m: e.dataset.metricCard, t: e.innerText })));
      const before = await cards();
      assert.deepEqual(before.map((c) => c.m), T.METRICS);
      for (const c of before) {
        const st = ev0.stats.U_B[c.m];
        for (const want of ['기준일 ' + X.DAYS[0], '비교 그룹 ' + gB.label, '유효 종목 ' + st.n_valid + ' / ' + gB.members, T.META[c.m].unit, T.META[c.m].d10]) assert.ok(c.t.includes(want), c.m + ' card has ' + want);
      }
      ok(tag + ' ① day and group, ② metric cards: unit, basis day, group, valid count, D10 reading');

      // ---------------- ③ owner example: U-B · 6-month momentum D10 · volatility D10 excluded · QGV order
      phase = tag + ' example';
      await page.selectOption('#tf-mom-6m', 'top10'); await page.selectOption('#tf-vol', 'exclude_d10');
      await page.locator('[data-k=tf-on]').check();
      await page.locator('[data-lb-table] [data-cell=tech]' + (phone ? ', [data-lb-table] .tech-line' : '')).first().waitFor({ state: 'attached' });
      const want = await page.evaluate(async ({ p, day }) => {
        const I = window.IS2, Q = I.qgv, pg = await Q.page(), v = I.techScreen.validate(p).value, ev = v.evaluations.find((e) => e.as_of === day);
        const r = I.techScreen.evaluate(ev, 'U_B', { mom: { '3m': 'none', '6m': 'top10', '12m': 'none' }, vol: 'exclude_d10', adv: 'none' });
        const passIds = new Set([...r.rows].filter(([, x]) => x.state === 'PASS').map(([id]) => id));
        const rows = Q.rows(pg, { scope: 'UNIVERSE' }).filter((x) => passIds.has(x.id));
        return { order: I.qgvLive.helpers.sortRows(rows, 'qgv').map((x) => x.id), counts: { ...r.counts } };
      }, { p: P, day: X.DAYS[0] });
      assert.ok(want.order.length >= 1, 'the example passes at least one company');
      assert.deepEqual(await drawnIds(), want.order, 'table = PASS rows in the leaderboard QGV order');
      const count = await text(B + ' [data-tf-count]');
      assert.ok(count.includes('통과 ' + want.counts.PASS) && count.includes('조건 미충족 ' + want.counts.FAIL) && count.includes('판정 불가 ' + want.counts.UNKNOWN), count);
      assert.equal(want.counts.UNKNOWN, 1);
      const unknown = await text(B + ' [data-tf-unknown]');
      const noVolTicker = ev0.rows.find((r) => r.company_id === C.noVol[0]).ticker;
      assert.ok(unknown.includes('판정 불가 1개'), unknown);
      await page.locator(B + ' [data-tf-unknown] summary').click();
      const unknownOpen = await text(B + ' [data-tf-unknown]');
      assert.ok(unknownOpen.includes(noVolTicker) && unknownOpen.includes('원천 가격 자료 없음'), 'unknown row and reason');
      assert.ok(!(await drawnIds()).includes(C.noVol[0]) && !(await drawnIds()).includes(C.volTop[0]), 'unknown and failing rows are not in the table');
      // Market down: a PASS row shows a negative 6-month momentum with D10.
      const first = want.order[0], cellSel = '[data-lb-table] tr[data-row="' + first + '"] ' + (phone ? '.tech-line' : '[data-cell=tech]');
      const cell = await text(cellSel);
      assert.ok(/6개월[^\n]*−\d+\.\d% · D10/.test(cell), 'negative D10 momentum shown: ' + cell);
      const after = await cards();
      assert.deepEqual(after, before, 'denominators unchanged by the filters');
      const status = await text('[data-sort-status]');
      assert.ok(status.includes('QGV 높은 순'), 'sort stays QGV');
      ok(tag + ' ③ owner example: PASS rows in QGV order, counts, 판정 불가 with reason, negative D10, fixed denominators');

      // ---------------- phone: tech line + 기술 상세 (분모 · 관측 · 사유); overflow; tap targets
      if (phone) {
        phase = tag + ' phone';
        const row = page.locator('[data-lb-table] tr[data-row="' + first + '"]');
        assert.ok(await row.locator('.tech-line').isVisible(), 'tech line visible');
        await row.locator('.tech-why summary').first().click();
        const det = await row.locator('.tech-why').first().evaluate((e) => e.innerText);
        assert.ok(det.includes('분모 ') && det.includes('관측 ') && det.includes('기준일 ' + X.DAYS[0]) && det.includes(gB.label), 'phone detail: ' + det);
        const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        assert.ok(over <= 0, 'no horizontal overflow at 390 (' + over + ')');
        const small = await page.$$eval(B + ' select, ' + B + ' .check', (els) => els.filter((e) => e.getBoundingClientRect().height < 44).length);
        assert.equal(small, 0, '44 px controls');
        if (SHOTS) { await page.locator(B).screenshot({ path: path.join(SHOTS, 'tech-filter-390-block.png') }); await page.locator('[data-lb="2.1.1"]').screenshot({ path: path.join(SHOTS, 'tech-filter-390-table.png') }); }
        ok(tag + ' phone: tech line, 기술 상세 with 분모 · 관측 · 사유, no overflow, 44 px controls');
      } else if (SHOTS) { await page.locator(B).screenshot({ path: path.join(SHOTS, 'tech-filter-1440-block.png') }); await page.locator('[data-lb="2.1.1"]').screenshot({ path: path.join(SHOTS, 'tech-filter-1440-table.png') }); }

      // ---------------- RAM-only display of tech values
      phase = tag + ' ram';
      const sentinels = [...new Set(ev0.rows.filter((r) => r.groups.includes('U_B')).map((r) => T.format('adv_6m', r.metrics.adv_6m.value)))];
      await site.assertRamOnly(page, sentinels, tag + ' tech values');
      ok(tag + ' tech values only as [data-ram-price] text');

      // ---------------- zero matches
      phase = tag + ' zero';
      await page.selectOption('#tf-vol', 'none'); await page.selectOption('#tf-mom-6m', 'gt0');
      await page.locator(B + ' [data-empty=TECH_ZERO]').waitFor();
      assert.ok((await text(B + ' [data-empty=TECH_ZERO]')).includes('계산은 정상 · 조건을 모두 만족하는 종목 0개'));
      await page.locator('[data-lb-table] [data-empty=TECH_FILTER]').waitFor();
      ok(tag + ' zero matches: 계산은 정상 · 0개, tech empty row');

      // ---------------- values without deciles (group too small)
      phase = tag + ' small';
      await page.selectOption('#tf-mom-6m', 'none'); await page.selectOption('#tf-group', 'U_SMALL');
      await page.locator(B + ' [data-metric-card=mom_6m]').waitFor();
      const smallCard = await text(B + ' [data-metric-card=mom_6m]');
      assert.ok(smallCard.includes('분위 없음 · ' + T.REASON.GROUP_TOO_SMALL) && smallCard.includes('중앙값 '), smallCard);
      const smallRow = (await drawnIds())[0];
      assert.ok(C.small.includes(smallRow), 'the table shows the small group');
      const smallCell = await text('[data-lb-table] tr[data-row="' + smallRow + '"] ' + (phone ? '.tech-line' : '[data-cell=tech]'));
      assert.ok(smallCell.includes('분위 없음'), 'value without decile: ' + smallCell);
      await page.selectOption('#tf-mom-6m', 'top10');
      await page.locator(B + ' [data-tf-unknown="6"]').waitFor();
      assert.ok((await text(B + ' [data-tf-count]')).includes('통과 0 · 조건 미충족 0 · 판정 불가 6'));
      ok(tag + ' values without deciles: 분위 없음 with reason, top10 → 판정 불가 6');

      // ---------------- switch off: the leaderboard as before
      phase = tag + ' off';
      await page.locator('[data-k=tf-on]').uncheck();
      await page.waitForFunction(() => !document.querySelector('[data-lb-table] [data-cell=tech]'));
      assert.ok((await drawnIds()).length > 1);
      ok(tag + ' switch off: no tech column, rows back');

      // ---------------- invalid file
      phase = tag + ' invalid';
      const bad = JSON.parse(JSON.stringify(P)); bad.evaluations[0].stats.U_B.vol_6m.n_valid = 99999;
      await swap({ state: 'OK', code: null, payload: bad, text: '' }); await reopen();
      await page.locator(B + ' [data-tech-state=ERROR][data-na=N_VALID_RANGE]').waitFor();
      assert.ok((await text(B + ' [data-tech-state=ERROR]')).includes(T.TEXT.INVALID));
      assert.equal(await page.locator('[data-lb-table] [data-cell=tech]').count(), 0);
      assert.ok((await drawnIds()).length > 1, 'leaderboard unchanged');
      ok(tag + ' invalid file refused whole, leaderboard unchanged');

      // ---------------- boundaries
      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, [], 'no request outside the origin');
      assert.deepEqual(seen.errors, [], 'no console error');
      const newData = s.requests.slice(at).map((r) => r.name).filter((n) => n.endsWith('.json'));
      assert.deepEqual(newData, [], 'the tech filter reads no data file');
      const st = await site.storage(page);
      assert.deepEqual([st.local, st.session], [0, 0], 'no storage');
      assert.equal(await page.evaluate(() => window.__csp), 0, 'CSP');
      ok(tag + ' boundaries: same origin, no data request, no storage, no console error, CSP 0');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
