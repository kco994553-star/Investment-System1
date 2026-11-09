'use strict';
// Lab 9.1 연구 범위 · 선정 방식 (owner 2026-11-04 third, item 4) in a real browser at 1440×1000 and 390×844 on #/lab.
//  - Real source (IS2.researchScope.source → NONE): the block says no result is connected and keeps the official N15 / TARGET line;
//    no number, no request.
//  - Codex's #474 output on the public synthetic fixture (tests/fixtures/operational_qgv_coverage_v1_synthetic.json) put in place of
//    source(): the denominator words (운영 게시본 코드 30개 · Universe504와 다름 · 고정 증권 ID 아님), Q / G / V / 세 축 동시 / 7
//    presets / 게시본 기본 총점 as separate rows (table on PC, list on the phone), engine mismatch → every preset 미산출 with the
//    reason; engine matched → preset counts; the 15 factors in a fold.
//  - Selection (#473 fields): 조건 충족 전부 · 상위 N · 상위 % words, eligible → selected, equal weight; outcomes in the same
//    object never shown.
//  - A refused file shows its code and path and draws no row. Boundaries: no request outside the origin, no Lab request, no console
//    error, no CSP violation, nothing stored, no horizontal overflow at 390 (fold open). SCOPE_SHOTS=<dir> saves screenshots.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const X = require('./web_app_lab_fixture.js');

const LEDGER = 'forward-validation-ledger.json';
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json', LEDGER];
const COV = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/operational_qgv_coverage_v1_synthetic.json'), 'utf8'));
const SHOTS = process.env.SCOPE_SHOTS || null;
const HANDOFF = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/research_selection_handoff_v1_synthetic.json'), 'utf8'));
const ids = (k) => Array.from({ length: k }, (_, i) => 'SYNTHETIC:C' + String(i).padStart(3, '0'));
const sel = (policy, e, s) => ({ selection_policy: policy, n_eligible: e, n_selected: s, selected: ids(s), weights: s ? Object.fromEntries(ids(s).map((i) => [i, 1 / s])) : null,
  outcomes: { 'SYNTHETIC:C000': { realised: 0.123456 } }, equal_weight_realized: 0.045678 });
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const s = await site.start({ fixtures: { [LEDGER]: { json: X.ledgerV2() } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      await page.goto(s.base + '#/lab'); await page.evaluate(() => window.IS2.ready);
      const B = '[data-lab-slot="lab-1"] [data-block="research-scope"]';
      const reopen = async () => {
        await page.evaluate(() => { location.hash = '#/portfolio'; }); await page.locator('main[data-route=portfolio]').waitFor();
        await page.evaluate(() => { location.hash = '#/lab'; }); await page.locator('main[data-route=lab]').waitFor(); };
      const put = async (src) => { await page.evaluate((x) => { const I = window.IS2, real = window.__rsReal || (window.__rsReal = I.researchScope);
        I.researchScope = Object.freeze({ ...real, source: () => Promise.resolve(x) }); }, src); await reopen(); };
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const shot = async (name) => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await page.locator(B).screenshot({ path: path.join(SHOTS, tag + '-' + name + '.png') }); } };

      phase = tag + ' NONE';
      await page.locator(B + ' [data-na=RESEARCH_SCOPE_NOT_CONNECTED]').waitFor();
      const none = await text(B);
      assert.match(none, /연결된 연구 결과 없음/); assert.match(none, /공식 모델은 기존 N15 구간·TARGET 규칙 그대로/);
      assert.doesNotMatch(none, /\d+ \/ \d+/, 'no count without a result');
      ok(tag + ' real source NONE: no result, official line, no number');

      phase = tag + ' coverage engine mismatch';
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: COV.engine_mismatch, selection: sel({ mode: 'top_n', value: 20 }, 137, 20) });
      await page.locator(B + ' [data-block="scope-coverage"]').waitFor();
      assert.match(await text(B + ' [data-scope-kind]'), /합성 자료 · 시험용/);
      assert.equal(await text(B + ' [data-scope-basis]'), '운영 게시본 코드 30개 기준 · Universe504(504개)와 다름 · 게시 행 36개 중 TARGET 6개 제외 · 고정 증권 ID 아님 · 발행사 CIK 수 미확인(CIK 없는 행 3개)');
      const kinds = await page.locator(B + ' [data-scope-row]').evaluateAll((n) => n.map((x) => x.dataset.scopeKind));
      assert.deepEqual(kinds, ['axis', 'axis', 'axis', 'all_axes', 'preset', 'preset', 'preset', 'preset', 'preset', 'preset', 'preset', 'published_total']);
      assert.equal(await page.locator(B + (phone ? ' ol[data-scope-rows] li' : ' table[data-scope-rows] tbody tr')).count(), 12, phone ? 'phone: a list' : 'PC: a table');
      const presets = await page.locator(B + ' [data-scope-kind=preset]').evaluateAll((n) => n.map((x) => x.innerText));
      for (const p of presets) { assert.match(p, /미산출/); assert.doesNotMatch(p, /\b0 \/ 30/); }
      assert.match(await text(B + ' [data-scope-engine=MISMATCH]'), /프리셋 총점 7개 모두 미산출: 엔진 버전이 게시본과 달라/, 'the reason once');
      assert.match(await text(B + ' [data-scope-row=axis-V]'), /V 축 단독.*계산 가능 15 \/ 30/s);
      assert.match(await text(B + ' [data-scope-row=all-axes]'), /Q·G·V 세 축 동시.*계산 가능 15 \/ 30/s);
      assert.match(await text(B + ' [data-scope-row=published-total]'), /있음 27 \/ 30/);
      assert.match(await text(B + ' [data-scope-scope]'), /과거 전체 시장 커버리지 아님/);
      ok(tag + ' coverage (engine mismatch): denominator words, 12 separate rows, presets 미산출 with reason, never 0');

      phase = tag + ' selection';
      const card = B + ' [data-block="scope-selection"]';
      assert.equal(await text(card + ' [data-scope-label]'), '상위 20개');
      assert.equal(await text(card + ' [data-scope-count]'), '조건 충족 137개 중 20개 선정');
      assert.equal(await text(card + ' [data-scope-rule]'), '순서: Q → G → V(없으면 뒤) → 회사 ID(동점은 회사 ID 순) · 앞에서 20개');
      assert.equal(await page.locator(card + ' [data-scope-shortfall]').count(), 0, 'no shortfall when enough names');
      assert.match(await text(card + ' [data-scope-absent]'), /이 엔진 계약에 없음 · 화면에서 만들지 않음/);
      assert.match(await text(card + ' [data-scope-scope]'), /실제 보유·공식 모델 결과와 섞지 않음/);
      assert.equal(await text(card + ' [data-scope-weight]'), '같은 비중 · 각 5%');
      assert.match(await text(card + ' [data-scope-official]'), /공식 모델은 기존 N15 구간·TARGET 규칙 그대로/);
      assert.doesNotMatch(await text(B), /0\.123456|0\.045678|12\.35|4\.57/, 'outcomes and realised returns never shown');
      await shot('mismatch-top-n');
      ok(tag + ' selection top N: words, counts, equal weight, official line, no outcome');

      phase = tag + ' engine matched + top %';
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: COV.engine_matched, selection: sel({ mode: 'top_percent', value: 10 }, 137, 13) });
      await page.waitForFunction((b) => { const x = document.querySelector(b + ' [data-scope-row=preset-balanced]'); return x && /계산 가능 27 \/ 30/.test(x.innerText); }, B);
      assert.match(await text(B + ' [data-scope-row=preset-value]'), /계산 가능 15 \/ 30/);
      assert.equal(await page.locator(B + ' [data-scope-engine]').count(), 0);
      assert.equal(await text(B + ' [data-block="scope-selection"] [data-scope-label]'), '상위 10% (소수점 아래 버림)');
      assert.equal(await text(B + ' [data-block="scope-selection"] [data-scope-count]'), '조건 충족 137개 중 13개 선정');
      await page.locator(B + ' details.why summary').click();
      assert.equal(await page.locator(B + ' [data-scope-factor]').count(), 15);
      assert.match(await text(B + ' [data-scope-factor=v_fcf_yield]'), /해당 없음 9 · 결손 6/);
      if (phone) assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'no horizontal overflow at 390 (fold open)');
      await shot('matched-top-pct');
      ok(tag + ' coverage (engine matched) preset counts; top %; factors fold' + (phone ? '; no overflow' : ''));

      // Codex #473 70672bc0 handoff cases: the 33.3333334 % boundary is accepted with the producer's count (1 of 3), the case just
      // below gives 0; selection_details lines replace the "not in the contract" line; no overflow at 390.
      phase = tag + ' #473 handoff';
      const HC = (id) => JSON.parse(JSON.stringify(HANDOFF.cases.find((c) => c.id === id).expected));
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: null, selection: HC('percent_boundary') });
      await page.locator(B + ' [data-block="scope-selection"] [data-scope-details]').waitFor();
      assert.equal(await page.locator(B + ' [data-scope-refused]').count(), 0, 'the boundary case is not refused');
      assert.equal(await text(B + ' [data-block="scope-selection"] [data-scope-count]'), '조건 충족 3개 중 1개 선정');
      assert.match(await text(B + ' [data-scope-detail=excluded]'), /선정 한도 밖 2/);
      assert.match(await text(B + ' [data-scope-detail=replay]'), /QGV 계산·시점\(PIT\)·성과 재현 아님/);
      assert.equal(await page.locator(B + ' [data-scope-absent]').count(), 0);
      if (phone) assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'no horizontal overflow at 390 (details)');
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: null, selection: HC('below_boundary') });
      await page.locator(B + ' [data-scope-detail=cash]').waitFor();
      assert.equal(await text(B + ' [data-block="scope-selection"] [data-scope-count]'), '조건 충족 3개 중 0개 선정');
      assert.match(await text(B + ' [data-scope-detail=cash]'), /포트폴리오 미형성 · 현금 비중 없음/);
      ok(tag + ' #473 handoff: 33.3333334 % → 1 of 3, 33.3333333 % → 0; selection_details lines');

      phase = tag + ' all + refused';
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: { ...COV.engine_matched, schema_version: 'operational-qgv-coverage/2' }, selection: sel(null, 137, 137) });
      await page.locator(B + ' [data-scope-refused=coverage]').waitFor();
      assert.match(await text(B + ' [data-scope-refused=coverage]'), /SCHEMA_VERSION · \$\.schema_version/);
      assert.equal(await page.locator(B + ' [data-scope-row]').count(), 0, 'a refused file draws no row');
      assert.equal(await text(B + ' [data-block="scope-selection"] [data-scope-label]'), '조건 충족 전부 (선정 방식 지정 없음)');
      await put({ state: 'OK', data_kind: 'SYNTHETIC', coverage: null, selection: sel({ mode: 'top_percent', value: 10 }, 137, 14) });
      await page.locator(B + ' [data-scope-refused=selection]').waitFor();
      assert.match(await text(B + ' [data-scope-refused=selection]'), /SELECTED_COUNT_MISMATCH/);
      ok(tag + ' refused coverage / selection: code and path, no row; all mode words');

      phase = tag + ' boundaries';
      await page.evaluate(() => { const I = window.IS2; if (window.__rsReal) I.researchScope = window.__rsReal; }); await reopen();
      await page.locator(B + ' [data-na=RESEARCH_SCOPE_NOT_CONNECTED]').waitFor();
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.deepEqual(s.requests.map((r) => r.name).filter((n) => n.endsWith('.json') && /lab|backtest|coverage|selection|scope/i.test(n)), [], 'no Lab or research data request');
      const st = await site.storage(page); assert.deepEqual([st.local, st.session], [0, 0]);
      ok(tag + ' boundaries: no outside or research request, no console error, CSP 0, nothing stored');
      await ctx.close();
    }
  } catch (e) { console.error('FAIL ' + phase + ': ' + (e && e.stack || e)); process.exitCode = 1; }
  finally { await browser.close(); await s.close(); }
  console.log(JSON.stringify({ passed: process.exitCode !== 1, checks: pass }));
})();
