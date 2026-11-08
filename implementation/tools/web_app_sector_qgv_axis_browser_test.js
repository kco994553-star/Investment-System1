'use strict';
// Q/G 부분 비교 on #/qgv 1.2 in a real browser (owner 2026-11-07 「#505 실자료 부분 비교 계약 추가 인수」), with the development
// engine route (Codex #505 sector_qgv + sector_qgv_partial, SYNTHETIC only):
//  - A preview carries Codex's compare_axes of its two previews: Q / G before → after (delta), transition, reasons and the counts,
//    the config / input / classification versions, V / total as 산출 없음 (never 0), no axis rank / total / market rank.
//  - 「비교 파일 목록」 (a click) lists Codex's synthetic D1 and Main's synthetic I1 (engine output); no private file without the
//    process setting. D1: 요소·비중 변경, Q rows shown with total common 0. I1: 분류 보완·비교집단 확대, "기업 실적이 … 아님",
//    reclassified row, filters choose rows only (the counts and the comparison stay), factor detail on opening a row.
//  - 1440 / 390 / 320: nothing in the block past the viewport, 44 px controls on phones, keyboard; origin only, CSP 0, no console
//    error, nothing stored by the comparison.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const E = require('./web_app_sector_qgv_engine.js');

const NOW = '2026-11-07T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const eng = E.start({ env: {} });
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } }, posts: { [E.ROUTE]: eng.route } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390, 320]) {
      const phone = width < 720, tag = String(width);
      phase = tag + ' preview';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const B = '[data-sq-body]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      // The loader's own state, polled: a waitForFunction re-binds when the page's execution context is replaced right after
      // load, where a single page.evaluate(IS2.ready) bound to the replaced context failed with "Execution context was destroyed"
      // (CI #521 build 128696968965 at 1440; reproduced locally 1 in 6 under parallel load, no second frame navigation logged).
      // Interval polling: the fixed clock (ctx.clock) replaces performance and animation frames, so marks and rAF polling never fire.
      let navs = 0; page.on('framenavigated', (f) => { if (f === page.mainFrame()) navs++; });
      await page.goto(s.base + '#/qgv');
      await page.waitForFunction(() => window.IS2 && typeof window.IS2.loadState === 'function' && ['READY', 'FAILED'].includes(window.IS2.loadState()), null, { polling: 100 });
      assert.equal(await page.evaluate(() => window.IS2.loadState()), 'READY', phase + ': the layer loaded');
      assert.equal(navs, 1, phase + ': one main-frame navigation by the time the layer is ready (an app reload would fail here, not be waited out)');
      await page.locator(B + ' [data-k=sq-connect]').click(); await page.locator(B + ' [data-sq-role]').first().waitFor();
      for (const [a, v] of [['Q', '34'], ['G', '33'], ['V', '33']]) { await page.fill(B + ' [data-k=sq-axis-' + a + ']', v); await page.locator(B + ' [data-k=sq-axis-' + a + ']').press('Tab'); }
      const c0 = eng.calls.length;
      await page.locator(B + ' [data-k=sq-preview]').click(); await page.locator(B + ' [data-sq-preview] [data-sq-axis][data-sq-axis-kind=PREVIEW]').waitFor();
      assert.deepEqual(eng.calls.slice(c0).map((c) => c.op), ['preview'], 'the comparison came with the one preview call');
      const P = B + ' [data-sq-axis-kind=PREVIEW]';
      const head = await text(P);
      assert.ok(head.includes('요소·비중 변경') && head.includes('이 미리보기의 비교'), head.slice(0, 200));
      for (const x of ['Q', 'G']) assert.ok((await text(P + ' [data-sq-axis-summary=' + x + ']')).includes('/ 전체 20'), x);
      assert.ok((await text(P + ' [data-sq-axis-vt]')).includes('총점이 없어도 Q/G 비교는 따로 보임'));
      assert.ok((await text(P + ' [data-sq-axis-rank=NONE]')).includes('축별 순위·총점·시장 순위 없음'));
      assert.equal(await page.locator(P + ' [data-sq-identity=config_hash][data-sq-diff=""]').count(), 1, 'settings differ');
      assert.equal(await page.locator(P + ' [data-sq-identity=input_hash][data-sq-diff=no]').count(), 1, 'same input');
      ok(tag + ' a preview carries the engine comparison: Q / G counts of the whole 20, versions, no rank / total, one engine call');

      // ---------------- Codex V resume (synthetic pack + market delivery) through the same preview call: V is computed 20 / 20
      phase = tag + ' v resume';
      await page.selectOption('#sq-input', 'V_RESUMED');
      const c2 = eng.calls.length;
      await page.locator(B + ' [data-k=sq-preview]').click(); await page.waitForFunction((b) => { const p = document.querySelector(b + ' [data-sq-computed]'); return p && p.dataset.sqComputed === '20/20'; }, B);
      assert.deepEqual(eng.calls.slice(c2).map((c) => [c.op, c.input_id]), [['preview', 'V_RESUMED']]);
      assert.ok((await text(B + ' [data-sq-summary]')).includes('V 20 / 20'), 'V computed from the resumed synthetic delivery');
      assert.ok((await text(B + ' [data-sq-summary]')).includes('합성 · V 재개(가격 전달 반영)'));
      await page.selectOption('#sq-input', 'NORMAL');
      ok(tag + ' V resume (Codex resume on the synthetic pack and market delivery): one preview call, V 20 / 20, labelled synthetic');

      // ---------------- comparison files (clicks): synthetic D1 and I1
      phase = tag + ' files';
      const c1 = eng.calls.length;
      await page.locator(B + ' [data-k=sq-axis-list]').focus(); await page.keyboard.press('Enter');
      await page.locator(B + ' [data-sq-axis-files=READY]').waitFor();
      assert.deepEqual(await page.$$eval(B + ' [data-sq-axis-file]', (n) => n.map((x) => [x.dataset.sqAxisFile, x.dataset.sqAxisFileKind])), [['PARTIAL_SYNTHETIC', 'SYNTHETIC'], ['MAIN_SYNTHETIC_I1', 'SYNTHETIC']], 'no private file without the process setting');
      await page.locator(B + ' [data-k=sq-axis-open-PARTIAL_SYNTHETIC]').click(); await page.locator(B + ' [data-sq-axis=SYNTHETIC-D1]').waitFor();
      const D = B + ' [data-sq-axis=SYNTHETIC-D1]';
      assert.ok((await text(D + ' [data-sq-axis-cause]')).startsWith('요소·비중 변경'));
      assert.ok((await text(D + ' [data-sq-axis-summary=Q]')).includes('공통 20') && (await text(D + ' [data-sq-axis-summary=Q]')).includes('공통 중 바뀜 20'));
      assert.ok((await text(D + ' [data-sq-axis-summary=G]')).includes('공통 중 바뀜 0'));
      assert.equal(await page.locator(D + ' [data-sq-axis-vt="0/0/0"]').count(), 1, 'total common 0');
      assert.equal(await page.locator(D + ' [data-sq-axis-rows="20"] [data-sq-axis-row]').count(), 20, 'Q / G rows are not hidden by total common 0');
      assert.ok((await text(D + ' [data-sq-axis-row] summary')).includes('산출 없음'), 'V / total null read 산출 없음');
      assert.ok(!/\b0점\b/.test(await text(D)));
      await page.selectOption(D + ' [data-k=sq-axis-axis]', 'G'); await page.selectOption(D + ' [data-k=sq-axis-show]', 'CHANGED');
      await page.locator(D + ' [data-sq-axis-rows="0"]').waitFor();
      assert.ok((await text(D + ' [data-sq-axis-summary=Q]')).includes('공통 중 바뀜 20'), 'a filter never changes the counts');
      ok(tag + ' synthetic D1: 요소·비중 변경, Q changed 20 / G 0, total common 0 with all 20 Q / G rows, filters choose rows only');

      await page.locator(B + ' [data-k=sq-axis-open-MAIN_SYNTHETIC_I1]').click(); await page.locator(B + ' [data-sq-axis=SYNTHETIC-I1]').waitFor();
      const I = B + ' [data-sq-axis=SYNTHETIC-I1]';
      assert.ok((await text(I + ' [data-sq-axis-cause]')).startsWith('분류 보완·비교집단 확대'));
      assert.ok((await text(I + ' [data-sq-axis-note]')).includes('기업 실적이 좋아지거나 나빠졌다는 뜻이 아님'));
      for (const k of ['input_version', 'snapshot_id', 'input_hash']) assert.equal(await page.locator(I + ' [data-sq-identity=' + k + '][data-sq-diff=""]').count(), 1, k);
      assert.equal(await page.locator(I + ' [data-sq-identity=config_hash][data-sq-diff=no]').count(), 1, 'same settings');
      assert.equal(await page.locator(I + ' [data-sq-identity=mapping_version]').count(), 1, 'classification version shown');
      assert.ok((await text(I + ' [data-sq-axis-summary=Q]')).includes('새로 산출 20'));
      await page.selectOption(I + ' [data-k=sq-axis-show]', 'RECLASSIFIED'); await page.locator(I + ' [data-sq-axis-rows="1"]').waitFor();
      const row = I + ' [data-sq-axis-row]';
      assert.ok((await text(row + ' summary')).includes('(분류 바뀜)') && (await text(row + ' summary')).includes('분류 미확정'));
      assert.ok((await text(row + ' summary')).includes('분류 보완 (섹터·회계모형 바뀜)'));
      await page.locator(row + ' summary').click(); await page.locator(row + ' [data-sq-axis-factors=Q]').waitFor();
      assert.ok((await page.locator(row + ' [data-sq-factor]').count()) > 0, 'factor detail on opening');
      await page.selectOption(I + ' [data-k=sq-axis-show]', 'ALL');
      assert.ok((await text(I)).includes('비교집단 변화로 상대점수 재계산 (실적 변화 아님)'));
      assert.deepEqual(eng.calls.slice(c1).map((c) => c.op), ['comparisons', 'comparison', 'comparison'], 'only clicks sent requests');
      assert.ok(!/\b(null|undefined|NaN)\b/.test(await text(B)), 'no null / undefined text');
      ok(tag + ' synthetic I1: 분류 보완·비교집단 확대, not a company improvement, input versions differ, reclassified row, peer rescoring, factor detail');

      phase = tag + ' layout';
      const wide = await page.$$eval(B + ' .sq-axis, ' + B + ' .sq-axis *', (els) => els.filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > window.innerWidth + 1 && !e.closest('.tbl-wrap') && !e.closest('.scroll'); }).map((e) => e.tagName + '.' + e.className));
      assert.deepEqual(wide, [], width + ': nothing in the comparison past the viewport');
      if (phone) {
        const small = await page.$$eval(B + ' .sq-axis-files .btn, ' + B + ' .sq-axis select', (els) => els.filter((e) => e.offsetParent && e.getBoundingClientRect().height < 44).map((e) => e.dataset.k || e.tagName));
        assert.deepEqual(small, [], width + ': 44 px');
      }
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []); assert.equal(await page.evaluate(() => window.__csp), 0);
      const st = await site.storage(page);
      assert.deepEqual(Object.keys(st.localItems).filter((k) => !/recent-search/.test(k)), [], 'the comparison stores nothing');
      ok(tag + ' layout and boundaries: nothing past the viewport, 44 px on phones, origin only, no console error, CSP 0, nothing stored');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); await eng.close(); }
})();
