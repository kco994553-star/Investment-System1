'use strict';
// 검색·계산 범위 on the search home (web_app/population.js + screen-population-live.js; owner 2026-11-05 follow-up item 3, Codex
// #482 current-expansion-research/1) in a real browser at 1440 and 390:
//  - Universe504 and the expansion population are two cards, never merged, each with its own searchable / QGV / rank rows; the line
//    that they are different populations and that the expansion result changes no official score, rank or TARGET.
//  - Universe504 from the layer: searchable = the company list, QGV totals and official ranks = the public page rows (the same
//    numbers IS2.qgv gives the leaderboard).
//  - Real source NONE: the expansion card says it is not connected and shows no number.
//  - Codex's synthetic outputs put in place of source(): partial roster → 합성 개발 검증, 부분 목록 · 전체 시장 분모 미확정, every
//    QGV / rank row 미확정 with reasons (no 0); complete synthetic roster → the stages apart (Q 11 · G 11 · V 0 · 세 축 0 / 12, 순위 0 / 12).
//  - A payload that breaks the contract (a partial roster with a full-market denominator) is refused whole.
//  - #500 staged evidence (synthetic, Codex's link_and_evaluate): the expansion card adds 재무 연결 · 증권 설명 · 평가일 동일 증권 ·
//    외부 증권 ID · 대표 증권 · 시총 적격성 rows, each with its own count and denominator, and the basis day S; an older result shows
//    NA in those rows; a staged file promoting a stage is refused whole.
//  - #499 financial V candidates: one line outside both cards, 금융업 후보 입력 (연구) · 공식 QGV와 별개; NONE in production (no
//    number); with the synthetic summary it says 합성 개발 검증 and never appears in the Universe504 card.
//  - Boundaries: no request of its own (same-origin reads only, no new file), nothing stored, no style attribute, no CSP violation,
//    no horizontal overflow at 390.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require(path.join(__dirname, '../tests/fixtures/current_expansion_research_v1_synthetic.json'));
const G = require(path.join(__dirname, '../tests/fixtures/current_expansion_staged_evidence_v1_synthetic.json'));
const H = require(path.join(__dirname, '../tests/fixtures/financial_v_held_bridge_v1_summary_synthetic.json'));
const H11 = require(path.join(__dirname, '../tests/fixtures/financial_v_held_bridge_v1_1_summary_synthetic.json'));
const STAGE_IDS = ['issuer', 'type', 'identity', 'external', 'representative', 'cap'];
const NOW = '2026-11-04T03:00:00.000Z';
// The public files this synthetic site does not publish (as web_app_home_browser_test.js).
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json', 'qgv-official.json', 'qgv-official-status.json'];
let phase = 'START';

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  let pass = 0;
  try {
    for (const width of [1440, 390]) {
      phase = 'home ' + width;
      const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const ready = () => page.locator('[data-population] [data-population-card=EXPANSION]').waitFor({ timeout: 20000 });
      const rows = (card) => page.locator('[data-population-card=' + card + '] [data-population-row]').evaluateAll((n) => n.map((x) => [x.dataset.populationRow, x.innerText.replace(/\s+/g, ' ').trim()]));
      const expansion = () => page.locator('[data-population-card=EXPANSION]').innerText();
      const at = s.requests.length;
      await page.goto(s.base + '#/'); await page.locator('main[data-route=search]').waitFor(); await ready();
      // Two cards and the separation line.
      assert.equal(await page.locator('[data-population] [data-population-card]').count(), 2, phase + ': two cards');
      assert.match(await page.locator('[data-population-separate]').innerText(), /Universe504\(공식 운영\)와 확장 모집단\(연구\)은 다른 모집단입니다 · 확장 결과는 공식 점수·순위·TARGET을 바꾸지 않습니다/);
      // A fresh home reads only its company index: the QGV rows say where they are counted, and no core file is read.
      const u0 = await rows('UNIVERSE504');
      assert.deepEqual(u0.map((x) => x[0]), ['searchable', 'qgv', 'rank']);
      assert.ok(u0.slice(1).every((x) => x[1].includes('QGV 화면을 열면 셉니다')), phase + ': no score file read for the home');
      assert.deepEqual(s.requests.slice(at).map((r) => r.name).filter((n) => /^(sec-qgv2|macro-screen|sec-public-inputs)\.json$/.test(n)), [], phase + ': the home reads no core file');
      // Real source NONE: words, no number.
      assert.match(await expansion(), /확장 모집단 연구 결과 미연결 · 비공개 연구 결과이며 공개 화면 연결은 승인 전입니다/);
      assert.equal(await page.locator('[data-population-card=EXPANSION] [data-population-row]').count(), 0);
      assert.doesNotMatch((await expansion()).replace('확장 모집단', ''), /\d/, phase + ': no number without a result');
      // #499 line: outside both cards, NONE in production, words only.
      const finLine = page.locator('[data-population] > [data-population-financial]');
      assert.equal(await finLine.getAttribute('data-population-financial'), 'NONE');
      assert.equal(await finLine.innerText(), '금융업 후보 입력 (연구) · 공식 QGV와 별개 · 비공개 연구 결과 미연결');
      assert.equal(await page.locator('[data-population-card] [data-population-financial]').count(), 0, phase + ': not inside a card');
      const put = async (payload, fin) => {
        await page.evaluate(([x, f]) => { const I = window.IS2, real = I.population; I.population = Object.freeze({ ...real, source: () => Promise.resolve(Object.freeze({ state: 'OK', payload: x })),
          financialSource: f ? () => Promise.resolve(Object.freeze({ state: 'OK', synthetic: true, payload: f })) : real.financialSource }); }, [payload, fin || null]);
        await page.goto(s.base + '#/qgv'); await page.locator('main[data-route=qgv] [data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
        await page.goto(s.base + '#/'); await page.locator('main[data-route=search]').waitFor(); await ready();
      };
      // Partial synthetic roster (put() opens #/qgv first, so the public page is now held and Universe504 is counted).
      await put(X.cases.partial12);
      const expect = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page({}), r = I.qgv.rows(pg, { scope: 'UNIVERSE' });
        return { codes: I.companies.list().length, n: r.length, total: r.filter((x) => x.score.total !== null).length, ranked: r.filter((x) => Number.isInteger(x.rank.official)).length }; });
      const u = await rows('UNIVERSE504');
      assert.ok(u[0][1].includes(String(expect.codes)) && expect.codes > 0, phase + ': searchable = the company list (' + expect.codes + ')');
      assert.ok(u[1][1].includes(expect.total + ' / ' + expect.n), phase + ': QGV totals from the public page');
      assert.ok(u[2][1].includes(expect.ranked + ' / ' + expect.n), phase + ': official ranks from the public page');
      assert.equal(await page.locator('[data-population-synthetic]').innerText(), '합성 개발 검증 · 실제 시장 자료 아님');
      assert.equal(await page.locator('[data-population-partial]').innerText(), '부분 목록 · 전체 시장 분모 미확정 · 점수·순위 없음');
      const p = Object.fromEntries(await rows('EXPANSION'));
      assert.match(p.market, /미확정 · 완전한 IEX 목록 없음/); assert.match(p.qgv, /미확정 · 평가일의 완전한 IEX 거래 목록 미확인/); assert.match(p.rank, /미확정/);
      assert.doesNotMatch(p.qgv + p.rank, /(?<![\d.])0(?![\d.])/, phase + ': 미확정 is never 0');
      assert.match(await page.locator('[data-population-reasons]').innerText(), /미확정 사유 · 평가일의 완전한 IEX 거래 목록 미확인 · 적격 여부 미확정 행 있음/);
      // Complete synthetic roster.
      await put(X.cases.complete12_missing1);
      assert.equal(await page.locator('[data-population-partial]').count(), 0);
      const c = Object.fromEntries(await rows('EXPANSION'));
      assert.match(c.qgv, /Q 11 · G 11 · V 0 · 세 축 0 \/ 12/); assert.match(c.rank, /0 \/ 12/); assert.match(c.market, /12/);
      assert.equal(await page.locator('[data-population-synthetic]').count(), 1, phase + ': still synthetic');
      // Universe504 card is unchanged by the expansion result.
      assert.deepEqual(await rows('UNIVERSE504'), u, phase + ': Universe504 unchanged');
      // The older result has no stages: each stage row is NA, never 0.
      for (const id of STAGE_IDS) assert.ok(c[id] && c[id].includes('NA · 증거 단계 평가 없음') && !/(?<![\d.-])0(?![\d.-])/.test(c[id]), phase + ': ' + id + ' NA, not 0: ' + c[id]);
      assert.equal(await page.locator('[data-population-stages]').count(), 0);
      // #500 staged evidence with the #499 synthetic summary.
      await put(G.cases.staged6_one_at_basis, H.report);
      const g = Object.fromEntries(await rows('EXPANSION'));
      assert.deepEqual(Object.keys(g), ['searchable', 'market', ...STAGE_IDS, 'eligibility', 'financial', 'qgv', 'rank'], phase + ': one row per stage');
      const want = { issuer: '재무 연결 · 5 / 티커 관측 6', type: '증권 설명 · 3 / 티커 관측 6', identity: '평가일 동일 증권 · 1 / 티커 관측 6 · S 2026-11-02',
        external: '외부 증권 ID · 확인 0 / 티커 관측 6', representative: '대표 증권 · 확정 0 / 발행사 5', cap: '시총 적격성 · NA · 미산출 6 / 티커 관측 6' };
      for (const [id, text] of Object.entries(want)) { const [label, value] = text.split(/ · (.*)/s); assert.ok(g[id].includes(label) && g[id].includes(value), phase + ': ' + id + ' ' + g[id]); }
      assert.match(g.type, /적격 판정 아님/); assert.match(g.eligibility, /0 · 0 · 6/); assert.match(g.qgv, /미확정/);
      assert.match(await page.locator('[data-population-card=EXPANSION] [data-population-state]').innerText(), /^평가일\(S\) 2026-11-02 · /);
      assert.equal(await page.locator('[data-population-stages]').innerText(), '증거 단계는 따로 셉니다 · 문서상 증권 종류는 적격이 아니며 대표 증권도 아닙니다');
      assert.equal(await page.locator('[data-population-partial]').count(), 1); assert.equal(await page.locator('[data-population-synthetic]').count(), 1);
      assert.equal(await finLine.getAttribute('data-population-financial'), 'OK');
      assert.equal((await finLine.innerText()).replace(/\s+/g, ' '), '합성 개발 검증 · 실제 시장 자료 아님 · 금융업 후보 입력 (연구) · 공식 QGV와 별개 · 분자 준비 2 · 같은 날 주가 1 · 기준 맞는 비율 1 / 금융업 코드 2 · 업종별 주 지표 기준 · 평가일 2026-11-02 · 공식 QGV 커버리지·점수·순위 아님 · 하위 업종 1');
      assert.doesNotMatch(await page.locator('[data-population-card=UNIVERSE504]').innerText(), /금융업|재무 연결|증권 설명|대표 증권|시총/, phase + ': nothing of it in Universe504');
      assert.deepEqual(await rows('UNIVERSE504'), u, phase + ': Universe504 unchanged by staged evidence');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with stage rows');
      // #499 /1.1 with a normal primary_metric null: read, the null shown as 미산출 with the contract's reason code (never 0).
      await put(JSON.parse(JSON.stringify(G.cases.staged6_one_at_basis)), JSON.parse(JSON.stringify(H11.report)));
      assert.equal(await finLine.getAttribute('data-population-financial'), 'OK');
      assert.equal(await finLine.locator('[data-na=BUSINESS_MODEL_UNRESOLVED]').innerText(), '주 지표 미산출 1코드 · 사유 BUSINESS_MODEL_UNRESOLVED(업종 모델 미정) · 분모에 포함 · 다른 지표로 대체 안 함');
      assert.match(await finLine.innerText(), /금융업 코드 2/);
      // A staged file promoting documentary evidence is refused whole; a #499 summary claiming QGV coverage is refused.
      const promoted = JSON.parse(JSON.stringify(G.cases.staged6_one_at_basis)); promoted.rows[0].stages.representative.value = true;
      const claimed = JSON.parse(JSON.stringify(H.report)); claimed.summary.scored_joint_valid = 2;
      await put(promoted, claimed);
      assert.match(await page.locator('[data-population-card=EXPANSION] [data-population-state=REFUSED]').innerText(), /STAGE_PROMOTED · \$\.rows\[0\]\.stages\.representative\.value/);
      assert.equal(await page.locator('[data-population-card=EXPANSION] [data-population-row]').count(), 0);
      assert.equal(await finLine.getAttribute('data-population-financial'), 'REFUSED');
      assert.match(await finLine.innerText(), /QGV_COVERAGE_CLAIMED · \$\.summary\.scored_joint_valid/);
      assert.doesNotMatch(await finLine.innerText(), /분자 준비/);
      // A partial roster that claims a full-market denominator is refused whole.
      const bad = JSON.parse(JSON.stringify(X.cases.partial12)); bad.full_market_denominator = 12;
      await put(bad);
      assert.match(await page.locator('[data-population-card=EXPANSION] [data-population-state=REFUSED]').innerText(), /PARTIAL_AS_FULL_MARKET · \$\.full_market_denominator/);
      assert.equal(await page.locator('[data-population-card=EXPANSION] [data-population-row]').count(), 0);
      // Boundaries.
      assert.deepEqual(seen.outside, [], phase + ': no request leaves the origin');
      assert.deepEqual(s.requests.slice(at).map((r) => r.name).filter((n) => n.endsWith('.json') && /expansion|population/i.test(n)), [], phase + ': no new data file is read');
      assert.deepEqual(seen.errors, [], phase + ': no console error');
      assert.equal(await page.locator('[style]').count(), 0); assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow');
      const st = await site.storage(page); assert.deepEqual([st.local, st.session], [0, 0], phase + ': nothing stored');
      await ctx.close(); pass++;
    }
    console.log('web_app_population_browser_test: PASS (' + pass + ' widths: two cards, Universe504 from the layer, NONE, partial and complete synthetic, #500 stage rows, #499 separate line, refusals, boundaries)');
  } catch (e) { console.error('web_app_population_browser_test: FAIL at ' + phase); console.error(e); process.exitCode = 1; }
  finally { await browser.close(); await s.close(); }
})();
