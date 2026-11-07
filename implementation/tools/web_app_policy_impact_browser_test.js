'use strict';
// 4.5 정책·지정학 (owner 2026-11-07) in a real browser on Codex's policy-impact-view/1 (#509): #/macro 3.5 나비효과, the company
// page 관련 정책 card and 5.2 → 4.5.
//  - Not published (404): opening #/macro sends no policy request; 「정책·지정학 열기」 says 자료 없음 · 정책 파일 미게시 (never a
//    synthetic stand-in). Invalid file → 규격 불일치 · 파일 전체 거부; HTTP 500 → 불러오기 실패 + 다시 읽기.
//  - Engine output only (tools/web_app_policy_impact_fixture.js; company ids put on real rows AT TEST TIME ONLY):
//    Codex synthetic-view.json; REVISED (p0 revision 2 current, its exposure / hypothesis on revision 1 REVIEW_REQUIRED, a
//    suspended unit): list in the engine order, filters, 0 results keep the conditions, detail ① ~ ⑤ with the current judgment
//    apart from 이전 분석 · 재검토 필요, history, sources, review records; policy → company → 관련 정책 → policy → 뒤로 ×3 → the
//    list with its filter and scroll; an older revision; a wrong id. HISTORICAL: 역사 사례 · 현재 상태 미확인 everywhere,
//    tariff / export control readable with no exposure (연결 근거 미확인, never 영향 없음), FINAL_AWARD ≠ 지급. NEWS: 5.2 → 4.5.
//  - 320 / 390 / 720 (1440 at 200 %) / 1440: nothing in 3.5 past the viewport, 44 px controls; keyboard Enter.
//  - Boundaries: no request leaves the origin, nothing stored, no console error but the intended 404, CSP 0.
//    POL_SHOTS=<dir> saves screenshots.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const N = require('./web_app_news_fixture.js');
const X = require('./web_app_policy_impact_fixture.js');
const P = require('../src/investment_system/product/web_app/policy-impact.js');

const NOW = '2026-11-07T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence.json', 'dart-financials.json'];
const FILE = 'policy-impact.json';
const SHOTS = process.env.POL_SHOTS || null;
const VAR = X.variants();
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const NEWS = N.news(Date.parse(NOW));
  assert.equal(NEWS.items[0].link, 'https://wire.example.org/nvda-revenue', 'the NEWS variant cites this link');
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS },
    'sec-disclosures.json': { json: N.sec(Date.parse(NOW)) }, 'news-signals.json': { json: NEWS }, 'dart-disclosures.json': { json: N.dart() } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const open = async (width, { allow404 = UNPUBLISHED } = {}) => {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  };
  const go = async (page, hash, route) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator('main[data-route=' + route + ']').waitFor(); };
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => e.innerText);
  const B = '[data-policy-body]';
  const cards = (page) => page.$$eval(B + ' [data-pol-card]', (n) => n.map((x) => x.dataset.polCard));
  const polReads = (from) => s.requests.slice(from).filter((r) => r.name === FILE).length;
  const noNull = async (page) => { const all = await text(page, B), m = all.match(/.{0,60}\b(null|undefined|NaN)\b.{0,30}/); assert.ok(!m, m && m[0]); };
  try {
    // ---------------- not published / invalid / failed
    phase = 'states';
    {
      s.fixture(FILE, { status: 404 });
      const { ctx, page, seen } = await open(1440, { allow404: [...UNPUBLISHED, FILE] });
      await page.goto(s.base + '#/macro'); await page.evaluate(() => window.IS2.ready); await page.locator(B + ' [data-k=pol-open]').waitFor();
      const r0 = s.requests.length; await page.waitForTimeout(300);
      assert.equal(polReads(0), 0, 'opening #/macro sends no policy request');
      await page.locator(B + ' [data-k=pol-open]').focus(); await page.keyboard.press('Enter');
      await page.locator(B + ' [data-pol-state=NONE]').waitFor();
      assert.ok((await text(page, B)).includes('자료 없음 · 정책 파일 미게시')); assert.equal(polReads(r0), 1);
      assert.equal(await page.locator(B + ' [data-pol-card]').count(), 0, 'no synthetic stand-in');
      s.fixture(FILE, { json: X.edit((v) => { v.bundle.score_effect = 'RANK'; }) }); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-state=INVALID]').waitFor();
      assert.ok((await text(page, B)).includes('FORBIDDEN_EFFECT · $.bundle.score_effect'));
      s.fixture(FILE, { json: X.codexView().bundle }); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-state=INVALID]').waitFor();
      assert.ok((await text(page, B)).includes('KEY_MISSING'), 'a bare bundle without the view envelope is refused');
      s.fixture(FILE, { status: 500 }); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-state=FAILED]').waitFor();
      assert.equal(await page.locator(B + ' [data-k=pol-retry]').count(), 1);
      s.fixture(FILE, { json: X.codexView() }); await page.locator(B + ' [data-k=pol-retry]').click(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      assert.deepEqual(await cards(page), ['p0', 'p1', 'p2'], 'Codex synthetic-view.json in the engine order after 다시 읽기');
      assert.deepEqual(seen.outside, []);
      await ctx.close();
      ok('not published = 자료 없음 (no stand-in, no request on open); invalid / bare bundle = 파일 전체 거부; HTTP 500 = 불러오기 실패 → 다시 읽기 → Codex synthetic view');
    }

    for (const width of [1440, 390]) {
      const tag = String(width);
      phase = tag + ' list';
      const { ctx, page, seen } = await open(width, { allow404: [...UNPUBLISHED, FILE] });
      await page.goto(s.base + '#/macro'); await page.evaluate(() => window.IS2.ready);
      const ids = await page.evaluate(async () => { await window.IS2.companies.ready(); return window.IS2.companies.list().filter((c) => c.status === 'ACTIVE').slice(0, 3).map((c) => c.id); });
      s.fixture(FILE, { json: X.linked(ids, VAR.REVISED) });
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      assert.deepEqual(await cards(page), ['unit-exception', 'p0', 'p1', 'p2'], 'the engine order');
      const band = await text(page, B + ' [data-pol-band]');
      assert.ok(band.includes('합성 · 시험용') && band.includes('관세 · 수출통제 · 산업 보조금') && band.includes('선별 소표본') && band.includes('조회 기준 2026-11-07 02:00:00 UTC'), band);
      assert.ok((await text(page, B + ' [data-pol-refresh]')).includes('자동 수집 결과가 아님'));
      assert.ok((await text(page, B + ' [data-pol-count]')).startsWith('4건 · 수집·검토한 범위의 수 · 0건은 영향 없음'));
      const p0 = B + ' [data-pol-card="p0"]';
      assert.ok((await text(page, p0)).includes('시행(근거 확인)') && (await text(page, p0)).includes('이전 개정 1개'), 'current revision 2 as the engine named it');
      assert.equal(await page.locator(p0 + ' [data-pol-stale]').count(), 1);
      assert.ok((await text(page, B + ' [data-pol-card="unit-exception"]')).includes('유예') && (await text(page, B + ' [data-pol-card="unit-exception"]')).includes('상위 p0'));
      assert.ok((await text(page, B + ' [data-pol-card="p1"]')).includes('발표 2026-11-01 (날짜만)'));
      await page.selectOption('#pol-type', 'INDUSTRIAL_SUBSIDY'); await page.selectOption('#pol-company', ids[0]);
      await page.locator(B + ' [data-pol-empty=FILTER]').waitFor();
      assert.equal(await page.inputValue('#pol-type'), 'INDUSTRIAL_SUBSIDY', 'conditions kept at 0');
      await page.locator(B + ' [data-k=pol-clear]').click(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      await page.selectOption('#pol-type', 'TARIFF');
      assert.deepEqual(await cards(page), ['unit-exception', 'p0']);
      ok(tag + ' list: engine order, 합성 · 시험용, 조회 기준, manual review, current revision as named, stale chip, unit, filters, 0 results keep the conditions');

      // ---------------- detail
      phase = tag + ' detail';
      await page.locator(p0).scrollIntoViewIfNeeded(); await page.evaluate(() => window.scrollBy(0, -40)); const y0 = await page.evaluate(() => window.scrollY);
      await page.locator(B + ' [data-k="pol-open-p0"]').click();
      await page.waitForFunction(() => location.hash === '#/macro/policy/p0'); await page.locator(B + ' [data-pol-detail="p0"]').waitFor();
      assert.deepEqual(await page.$$eval(B + ' [data-pol-section]', (n) => n.map((x) => x.dataset.polSection)), ['①', '②', '③', '④', '⑤']);
      assert.equal(await page.locator(B + ' [data-pol-old-revision]').count(), 0, 'the current revision is not "older"');
      assert.ok((await text(page, B + ' [data-pol-children]')).includes('유예'), 'the suspended unit is its own line');
      assert.equal(await page.locator(B + ' [data-pol-group=LINKED]').count(), 0, 'no current exposure on revision 2');
      assert.deepEqual(await page.$$eval(B + ' [data-pol-group=OLD] [data-pol-exposure]', (n) => n.map((x) => x.dataset.polExposure)), ['e0']);
      assert.ok((await text(page, B + ' [data-pol-group=OLD] [data-pol-exposure=e0]')).includes('비율 없음 · 비율 미공시 · 0%가 아님'));
      assert.ok((await text(page, B + ' [data-pol-group=OLD] [data-pol-exposure=e0]')).includes('정책 적용 미확인'), 'region evidence is not applicability');
      assert.ok((await text(page, B + ' [data-pol-section="③"]')).includes('현재 판단 가설 없음'));
      assert.ok((await text(page, B + ' [data-pol-group=OLD_HYPOTHESES]')).includes('이전 분석 · 재검토 필요'));
      assert.equal(await page.locator(B + ' [data-pol-hypothesis=h0][data-pol-review=REVIEW_REQUIRED] [data-pol-counter]').count(), 1);
      assert.equal(await page.locator(B + ' [data-pol-history="2"] [data-pol-current]').count(), 1);
      assert.ok((await text(page, B + ' [data-pol-sources]')).includes('합성 정책 원문') && (await text(page, B + ' [data-pol-sources]')).includes('원문 확인'));
      await page.$$eval(B + ' details', (n) => n.forEach((d) => { d.open = true; }));
      assert.ok((await text(page, B + ' [data-pol-review-method]')).includes('AI 독립 원문 대조 · 사람 검토 아님'));
      assert.equal(await page.locator(B + ' a[href^="https://"]').count(), 0, 'reserved test domains are text, never links');
      await noNull(page);
      ok(tag + ' detail ① ~ ⑤: current revision, unit, no current exposure, 이전 개정 기준 연결 · 재검토 필요, ratio null not 0 %, 이전 분석 hypotheses apart, history, sources, AI review not human');

      // ---------------- policy → company → 관련 정책 → policy → back ×3 → list (filter and scroll back)
      phase = tag + ' navigation';
      await page.locator(B + ' [data-pol-group=OLD] [data-pol-company] >> nth=0').click(); await page.locator('main[data-route=company]').waitFor();
      const cardSel = '[data-pol-company-card="' + ids[0] + '"]';
      await page.locator(cardSel + ' summary').waitFor(); const r1 = s.requests.length;
      await page.locator(cardSel + ' summary').focus(); await page.keyboard.press('Enter');
      await page.locator(cardSel + ' [data-pol-company-summary]').waitFor();
      assert.ok((await text(page, cardSel)).includes('관련 정책 1건 · 노출·적용 근거 확인 0건 · 확인 필요 0건 · 이전 분석 · 재검토 필요 1건'), await text(page, cardSel));
      assert.ok(polReads(r1) <= 1);
      await page.locator(cardSel + ' a[href="#/macro/policy/p0"]').click(); await page.locator(B + ' [data-pol-detail="p0"]').waitFor();
      await page.goBack(); await page.locator('main[data-route=company]').waitFor();
      await page.goBack(); await page.locator(B + ' [data-pol-detail="p0"]').waitFor();
      await page.goBack(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      assert.equal(await page.inputValue('#pol-type'), 'TARIFF', 'filter back');
      await page.waitForTimeout(300); { const y1 = await page.evaluate(() => window.scrollY); assert.ok(Math.abs(y1 - y0) <= 2, 'scroll back ' + y0 + ' ' + y1); }
      ok(tag + ' policy → company 관련 정책 (keyboard) → policy → 뒤로 ×3 → the list with its filter and scroll');

      phase = tag + ' revisions';
      await go(page, '#/macro/policy/p0/1', 'macro'); await page.locator(B + ' [data-pol-old-revision="1"]').waitFor();
      assert.ok((await text(page, B + ' [data-pol-old-revision]')).includes('현재 판단 아님'));
      assert.ok((await text(page, B + ' [data-pol-section="①"]')).includes('채택'));
      await go(page, '#/macro/policy/p2', 'macro'); await page.locator(B + ' [data-pol-subsidy]').waitFor();
      assert.ok((await text(page, B + ' [data-pol-subsidy]')).includes('예비 조건 · 지급 아님'));
      await go(page, '#/macro/policy/nope', 'macro'); await page.locator(B + ' [data-pol-state=NOT_FOUND]').waitFor();
      ok(tag + ' an older revision says 현재 판단 아님; subsidy stage words; a wrong id = 정책 없음');

      // ---------------- the real-case shape (synthetic): historical, no exposure for tariff / export, final award
      phase = tag + ' historical';
      s.fixture(FILE, { json: X.linked(ids, VAR.HISTORICAL) }); await page.goto(s.base + '#/macro'); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator(B + ' [data-k=pol-open]').click(); await page.locator(B + ' [data-pol-card]').first().waitFor();
      assert.deepEqual(await cards(page), ['p0', 'p1', 'p2']);
      for (const c of ['p0', 'p1', 'p2']) assert.equal(await page.locator(B + ' [data-pol-card="' + c + '"] [data-pol-historical]').innerText(), '역사 사례 · 현재 상태 미확인');
      assert.ok((await text(page, B + ' [data-pol-bundle-reasons]')).includes('역사 사례 · 현재 상태 미확인 · 법적 효력 PDF 원문 미확인(웹 게시본 기준) · 선별 사례 · 시장 전체 범위 아님'));
      assert.ok((await text(page, B + ' [data-pol-review-due=NULL]')).includes('다음 검토 예정일 미정'));
      for (const c of ['p0', 'p1']) assert.ok((await text(page, B + ' [data-pol-card="' + c + '"] [data-pol-links="0"]')).includes('연결 근거 미확인 (영향 없음이라는 뜻이 아님)'), c);
      await go(page, '#/macro/policy/p1', 'macro'); await page.locator(B + ' [data-pol-no-exposure]').waitFor();
      assert.ok((await text(page, B + ' [data-pol-section="②"]')).includes('연결된 기업 노출 기록 없음 · 연결 근거 미확인 (영향 없음이라는 뜻이 아님)'));
      assert.ok(!/영향 없음(?!이라는 뜻이 아님)/.test(await text(page, B)), '영향 없음 only ever as "not 영향 없음"');
      await go(page, '#/macro/policy/p2', 'macro'); await page.locator(B + ' [data-pol-subsidy=FINAL_AWARD]').waitFor();
      assert.ok((await text(page, B + ' [data-pol-subsidy]')).includes('확정 지원 발표 · 실제 지급 아님(지급 미확인)'));
      assert.ok((await text(page, B + ' [data-pol-exposure]')).includes('비율 없음 · 비율 해당 없음 · 현재 지급 미확인 · 0%가 아님'));
      assert.ok(!(await text(page, B)).includes('지급 확인'), 'a final award never reads as a disbursement');
      await noNull(page);
      ok(tag + ' historical shape: 역사 사례 · 현재 상태 미확인 on every policy, tariff / export readable with 연결 근거 미확인 (never 영향 없음), FINAL_AWARD ≠ 지급, review date 미정');

      phase = tag + ' news';
      s.fixture(FILE, { json: X.linked(ids, VAR.NEWS) }); await page.goto(s.base + '#/news'); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-policy-news] [data-k=pol-news]').waitFor();
      await page.locator('[data-file="news-signals.json"][data-file-state=OK]').first().waitFor({ state: 'attached' });
      await page.locator('[data-policy-news] [data-k=pol-news]').click(); await page.locator('[data-policy-news] [data-pol-news-hits]').waitFor();
      assert.equal(await page.locator('[data-policy-news] [data-pol-news-hits]').getAttribute('data-pol-news-hits'), '1');
      await page.locator('[data-policy-news] [data-pol-news-link="p0"] a[href="#/macro/policy/p0"]').click();
      await page.locator(B + ' [data-pol-detail="p0"]').waitFor();
      assert.ok((await text(page, B + ' [data-pol-sources]')).includes('뉴스 참조') && (await text(page, B + ' [data-pol-sources]')).includes('처음 발견 2026-11-06 12:00:00 UTC (게시 시각 아님)'));
      assert.ok((await text(page, B + ' [data-pol-sources]')).includes('관련 기사(참조) · 정책 검증 근거 아님'));
      s.fixture(FILE, { json: X.linked(ids, VAR.REVISED) }); await page.goto(s.base + '#/news'); await page.reload(); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-policy-news] [data-k=pol-news]').click(); await page.locator('[data-policy-news] [data-pol-news-state=NO_LINK_DATA]').waitFor();
      assert.ok((await text(page, '[data-policy-news]')).includes('연결 자료 없음') && (await text(page, '[data-policy-news]')).includes('연결 기능 자체는 합성 시험으로 확인됨'));
      ok(tag + ' 5.2 관련 정책 연결 보기 → the policy citing the news link (a reference, not evidence); a file without links says 연결 자료 없음, apart from the tested function');

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      const st = await site.storage(page);
      assert.deepEqual(Object.keys(st.localItems).filter((k) => !/recent-search/.test(k)), [], 'nothing stored by this feature');
      assert.equal(await page.evaluate(() => window.__csp), 0);
      if (SHOTS) await page.locator('[data-section="3-5"]').screenshot({ path: path.join(SHOTS, 'policy-' + tag + '.png') });
      ok(tag + ' boundaries: origin only, nothing stored, no console error, CSP 0');
      await ctx.close();
    }

    // ---------------- widths: 320 / 390 / 720 (= 1440 at 200 %) / 1440
    phase = 'widths';
    // A long unbreakable official-style title (the real file had one: an identifier-shaped title ran 18 px past 320) wraps in place.
    const LONG = JSON.parse(JSON.stringify(VAR.REVISED)), LONG_TITLE = 'SYNTHETIC:AGENCY20241210:LONG-UNBROKEN-IDENTIFIER-TITLE-0123456789';
    LONG.bundle.policies.filter((p) => p.policy_id === 'p0').forEach((p) => { p.title = LONG_TITLE; });
    assert.ok(P.validate(LONG).ok, 'the long-title variant is still a valid file');
    s.fixture(FILE, { json: LONG });
    for (const width of [320, 390, 720, 1440]) {
      const { ctx, page } = await open(width, { allow404: [...UNPUBLISHED, FILE] });
      await page.goto(s.base + '#/macro/policy/p0'); await page.evaluate(() => window.IS2.ready); await page.locator(B + ' [data-pol-detail]').waitFor();
      await page.$$eval(B + ' details', (n) => n.forEach((d) => { d.open = true; }));
      assert.equal(await page.locator(B + ' .pol-detail-title').innerText(), LONG_TITLE, 'the long title is shown whole');
      // The policy section itself never runs past the viewport (its chips wrap; scroll strips scroll inside themselves).
      const wide = await page.$$eval('[data-section="3-5"] *', (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > window.innerWidth + 1 && !e.closest('.scroll'); }).map((e) => e.tagName + ' ' + (e.textContent || '').slice(0, 30)));
      assert.deepEqual(wide, [], width + ': nothing in 3.5 past the viewport');
      // The whole page, 320 included: the 3.1 cycle ring scales inside its card (owner 2026-11-07 3차; no overflow hiding).
      const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      assert.ok(over <= 0, width + ': no horizontal overflow (' + over + ' px)');
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).overflowX), 'visible', 'the page does not hide overflow');
      await go(page, '#/macro', 'macro');
      const ring = await page.locator('svg[data-ring]').first().evaluate((e) => { const r = e.getBoundingClientRect(); return { w: Math.round(r.width), right: r.right, vw: window.innerWidth }; });
      assert.ok(ring.right <= ring.vw + 0.5 && ring.w >= Math.min(240, ring.vw - 80), width + ': the 3.1 ring fits and stays readable ' + JSON.stringify(ring));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth) <= 0, width + ': #/macro no horizontal overflow');
      if (width < 720) {
        await go(page, '#/macro', 'macro'); await page.locator(B + ' [data-pol-card]').first().waitFor();
        const small = await page.$$eval(B + ' select, ' + B + ' .btn', (els) => els.filter((e) => e.offsetParent && e.getBoundingClientRect().height < 44).map((e) => e.dataset.k || e.tagName));
        assert.deepEqual(small, [], width + ': 44 px');
      }
      await ctx.close();
    }
    ok('320 / 390 / 720 (1440 at 200 %) / 1440: nothing in 3.5 past the viewport (a long unbroken title wraps), page overflow 0 everywhere (the 3.1 ring scales), 44 px controls on phones');
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
