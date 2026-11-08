'use strict';
// 매크로 관측 자료 · 갱신 상태 (feature 4.1.3, owner 2026-11-05; Codex #477 macro-current-query/1) in a real browser at 1440×1000
// and 390×844 on #/macro (screen-macro-live.js block, screen-macro-observed-live.js, reader IS2.macroObserved).
//  - Real source (IS2.macroObserved.source → NONE): the block says the file is not connected and why, draws no number; the fixed
//    line 공식 국면은 아직 미산출 stays; the other macro blocks are drawn as before.
//  - The SYNTHETIC files made by Codex's own tool (tools/web_app_macro_observed_fixture.js) put in place of source(): 합성 개발
//    검증 first; the query times, cache age, cache reuse and the file counts; 14 series with state / stale, 기준 기간 · data_asof,
//    frequency · unit · seasonal adjustment, 진단값 관측 / 미산출, 원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE, acquisition times,
//    값 유지 + 수정 버전 (curve), STALE (CES3000000007; five in the late case), FAILED_AFTER_SUCCESS keeping the last success (BLS
//    LNS14000000), NEVER_SUCCEEDED (every series of the never case), the source's terms under 출처 · 약관.
//  - No observed value anywhere on the page (the sentinel digits of the synthetic values never appear in text or attributes).
//  - Refused files (wrong schema; a value with NOT_COMPUTED): the block says so with the code, draws no row; the rest stays.
//  - Phone: no horizontal overflow with every 출처 · 약관 opened.
//  - Boundaries: no request after the first open (the source requests nothing), no storage, no request outside the origin, no
//    console error, no [style], CSP 0.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const site = require('./web_app_test_site');
const MF = require('./web_app_macro_fixture.js');
const X = require('./web_app_macro_observed_fixture.js');

const NOW = '2026-10-14T03:00:00.000Z';
const UNPUBLISHED = ['sec-public-inputs.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json'];
const FULL = { 'macro-screen.json': { json: MF.macroScreen() }, 'macro-evidence.json': { json: MF.evidence() }, 'sec-qgv2.json': { json: MF.qgv() }, 'company-classification.json': { json: MF.classification() } };
const B = '[data-block="4.1.3-observed"]';
const C = X.cases();
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.sha(), X.SHA256, 'synthetic fixture unchanged');
  const s = await site.start({ fixtures: FULL });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      await page.goto(s.base + '#/macro'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-block="4.6"] [data-node]').first().waitFor();
      const at = s.requests.length;
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const reopen = async () => {
        await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree]').waitFor();
        await page.evaluate(() => { location.hash = '#/macro'; }); await page.locator('main[data-route=macro]').waitFor();
        await page.locator(B + ' [data-obs-state], ' + B + ' [data-obs-data]').first().waitFor(); };
      const swap = (payload) => page.evaluate((p) => { const I = window.IS2; I.__realObs = I.__realObs || I.macroObserved;
        I.macroObserved = Object.freeze({ ...I.__realObs, source: () => Promise.resolve({ state: 'OK', code: null, payload: p, data_kind: 'SYNTHETIC', text: '' }) }); }, payload);
      const rowText = (id) => text(B + ' [data-obs-row="' + id + '"]');
      const noValue = async (label) => {
        const all = await page.evaluate(() => document.body.innerText + ' ' + document.documentElement.outerHTML);
        assert.doesNotMatch(all, X.SENTINEL, label + ': no observed value on the page');
      };
      const others = async (label) => {
        for (const b of ['4.1.1', '4.1.3', '4.1.4', '4.6']) assert.equal(await page.locator('[data-block="' + b + '"]').count(), 1, label + ': block ' + b);
        assert.ok((await text('[data-macro-slot="3-1"]')).includes('공식 국면은 아직 미산출'), label + ': the fixed line stays');
      };

      // ---------------- real source NONE
      phase = tag + ' none';
      await page.locator(B + ' [data-obs-state=NONE]').waitFor();
      const none = await text(B);
      for (const w of ['관측 자료 · 갱신 상태', '관측 조회 파일이 아직 연결되지 않았습니다', '공개 게시와 화면 사용은 별도 승인 전', '요청하지 않음', '채택된 국면 판단이 아님', '공식 국면은 미산출'])
        assert.ok(none.includes(w), 'NONE has ' + w);
      assert.equal(await page.locator(B + ' [data-obs-row]').count(), 0);
      assert.doesNotMatch(await text(B + ' [data-obs-state=NONE]'), /\d+\.\d/, 'no number drawn');
      const order = await page.$$eval('[data-macro-slot="3-1"] > [data-block]', (n) => n.map((x) => x.dataset.block));
      assert.deepEqual(order.slice(0, 4), ['4.1.1', '4.1.3', '4.1.3-observed', '4.1.4'], 'after the evidence lines, before the lights');
      await others(tag + ' none');
      ok(tag + ' real source NONE: words, no number, no row; other blocks and the fixed line kept');

      // ---------------- synthetic main case
      phase = tag + ' main';
      await swap(C.main); await reopen();
      await page.locator(B + ' [data-obs-data=SYNTHETIC]').waitFor();
      assert.match(await text(B + ' [data-obs-data]'), /^합성 개발 검증 · 실자료 아님/);
      const q = await text(B + ' [data-obs-query]');
      for (const w of ['조회 시각', '2026-01-04 00:00 UTC', '계산 캐시 기준', '12시간 전', '계산 캐시 재사용 · 원천을 새로 받지 않음 · 외부 요청 0건', 'OBSERVED_CAPTURE_ONLY']) assert.ok(q.includes(w), 'query has ' + w);
      assert.equal(await text(B + ' [data-obs-counts]'), '14계열 · 조회 가능 6 (신선 5 · stale 1) · 값 유지 6 · 미산출 8 · 원발표 입증 0 · 원기관 버전 입증 0 · 과거 시점 검증 가능 0');
      assert.match(await text(B + ' [data-obs-values=NOT_SHOWN]'), /값 미표시 · 현재 조회 파일은 비공개 생성/);
      assert.equal(await page.locator(B + ' [data-obs-row]').count(), 14);
      assert.equal(await page.locator(B + ' [data-obs-line=evidence]').evaluateAll((n) => n.filter((x) => x.textContent.startsWith('원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE')).length), 14, 'release words on every row');
      ok(tag + ' synthetic file: 합성 개발 검증, query times and age, cache reuse, counts, 14 rows with release words');

      phase = tag + ' rows';
      const curve = await rowText(X.IDS.curve);
      for (const w of ['E09', '조회 가능', '기준 기간 2025-11 · data_asof 2025-11', '월 · 단위 %p · 계절조정 해당 없음', '진단값 관측 · 채택된 국면 판단 아님 · 값 미표시',
        '첫 취득 2026-01-02 12:00 UTC (기록된 수신)', '선택 버전 취득 2026-01-03 12:00 UTC', '값 유지 예 · 수정 버전 예', '마지막 성공 유지']) assert.ok(curve.includes(w), 'curve has ' + w);
      assert.equal(await page.locator(B + ' [data-obs-row="' + X.IDS.curve + '"][data-obs-version=REVISION]').count(), 1);
      const hours = await rowText(X.IDS.hours);
      assert.ok(hours.includes('stale · 기준 기간 지연 (값 유지 · 진단용)') && hours.includes('기준 기간 2025-04'), 'stale row');
      assert.equal(await page.locator(B + ' [data-obs-state=STALE]').count(), 1);
      const labor = await rowText(X.IDS.labor);
      assert.ok(labor.includes('마지막 성공 수집 2026-01-02 12:00 UTC (1일 12시간 전) · 최근 수집 실패 · 마지막 성공값 유지 · 실패 사유 출처 응답 없음'), 'failed after success');
      assert.ok(labor.includes('진단값 관측'), 'the last success is kept');
      const ip = await rowText(X.IDS.ip);
      assert.ok(ip.includes('첫 취득 시각 기록 없음 · 늦어도 2026-01-03 12:00 UTC (보관본 생성 상한)'), 'upper bound only');
      const dol = await rowText(X.IDS.dol);
      assert.ok(dol.includes('자료 없음 · 약관 원문 미확인 · 공개 보류') && dol.includes('미산출') && dol.includes('성공한 수집 없음'), 'held series');
      assert.ok((await rowText(X.IDS.census)).includes('미산출 · API 키 미설정'));
      await page.locator(B + ' [data-obs-row="' + X.IDS.dol + '"] details summary').click();
      assert.match(await text(B + ' [data-obs-row="' + X.IDS.dol + '"] [data-obs-terms]'), /DOL · FREE_OFFICIAL · 약관 미확인 · 공개 보류 · 약관 확인 2026-10-20/);
      await noValue(tag + ' main');
      await others(tag + ' main');
      ok(tag + ' rows: held + 수정 버전, STALE, FAILED_AFTER_SUCCESS keeps last success, upper bound, held terms, 미산출 reasons; no value');

      // ---------------- late and never
      phase = tag + ' late';
      await swap(C.late); await reopen(); await page.locator(B + ' [data-obs-data]').waitFor();
      assert.equal(await page.locator(B + ' [data-obs-state=STALE]').count(), 5);
      assert.match(await text(B + ' [data-obs-counts]'), /조회 가능 6 \(신선 1 · stale 5\)/);
      phase = tag + ' never';
      await swap(C.never); await reopen(); await page.locator(B + ' [data-obs-data]').waitFor();
      assert.equal(await page.locator(B + ' [data-obs-update=NEVER_SUCCEEDED]').count(), 14);
      assert.equal(await page.locator(B + ' [data-obs-kind=NOT_COMPUTED]').count(), 14);
      assert.match(await text(B + ' [data-obs-counts]'), /조회 가능 0 .* 미산출 14/);
      await noValue(tag + ' never');
      ok(tag + ' late: five STALE; never: every series NEVER_SUCCEEDED and 미산출');

      // ---------------- phone layout
      if (phone) {
        phase = tag + ' phone';
        await swap(C.main); await reopen(); await page.locator(B + ' [data-obs-data]').waitFor();
        await page.$$eval(B + ' details', (d) => d.forEach((x) => { x.open = true; }));
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'no horizontal overflow at 390');
        const wide = await page.$$eval(B + ' *', (n) => n.filter((e) => e.getBoundingClientRect().right > window.innerWidth + 0.5).length);
        assert.equal(wide, 0, 'nothing in the block passes the right edge');
        ok(tag + ' phone: no overflow with every 출처 · 약관 open');
      }

      // ---------------- refused files
      phase = tag + ' refused';
      await swap(X.mutate('main', (p) => { p.schema_version = 'macro-current-query/2'; })); await reopen();
      await page.locator(B + ' [data-obs-state=ERROR][data-na=SCHEMA_VERSION]').waitFor();
      assert.match(await text(B), /관측 조회 파일이 계약과 달라 파일 전체를 쓰지 않습니다/);
      assert.equal(await page.locator(B + ' [data-obs-row]').count(), 0);
      await swap(X.mutate('main', (p) => { p.series[X.IDS.temp].value = 1.5731999; })); await reopen();
      await page.locator(B + ' [data-obs-state=ERROR][data-na=VALUE_WITH_NOT_COMPUTED]').waitFor();
      assert.equal(await page.locator(B + ' [data-obs-row]').count(), 0);
      await noValue(tag + ' refused');
      await others(tag + ' refused');
      ok(tag + ' refused whole: wrong schema, value with NOT_COMPUTED; the rest of the screen stays');

      phase = tag + ' boundaries';
      assert.deepEqual(s.requests.slice(at).map((r) => r.name), [], 'no request after the first open');
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      const st = await site.storage(page); assert.deepEqual([Object.keys(st.localItems), st.session, st.idb], [[], 0, 0], 'no storage');
      assert.equal(await page.locator('[style]').count(), 0, 'no style attribute');
      assert.equal(await page.evaluate(() => window.__csp), 0);
      ok(tag + ' boundaries: no request, no storage, same origin, no console error, no [style], CSP 0');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
