'use strict';
// QGV 555 · 시총 Top500 · 사용자 설정 (owner 2026-11-14, DC-49) on #/qgv in a real browser at 1440×1000, 390×844 and 320×700, with
// the development engine route (tools/sector_qgv_engine_bridge.py qgv555_context / qgv555_preview, Main's SYNTHETIC proposal files):
//  - 2.1: 모집단 기존504 / 시총 Top500 / 확장 연구 × 모형 기존 공식 / U1-555 / S1-555 / 내 설정. 기존504 × 기존 공식 keeps the official
//    table; every other pair shows its state panel and none of the official rows / lists under its name.
//  - 2.2.7: nothing sent on open; 「555 합성 계약 불러오기」 (one POST) → five roles per axis, Q/G/V tabs, active count, a second factor
//    splits the role's budget, alias / not-fit refusals in words with alternatives, exclude a role → count drops and the sums say so,
//    variant / composite bounds, cancel / restore (base preset id), S1 bank edit leaves insurance as its base; 「실제 재계산」 = one
//    engine call answered ENGINE_CONTRACT_PENDING → no number in the preview, 저장 off; Top500 lines 「확정 아님」 after loading.
//  - D1–D10 all ten bands named (never a top-20), coverage stages, 475/500.
//  - Keyboard (Tab to the load button, Enter), 200% zoom at 1440 without horizontal overflow, phone 44 px targets and no overflow.
//  - Boundaries: no request leaves the origin, engine route POST only, nothing stored, no console error, CSP 0.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const E = require('./web_app_sector_qgv_engine.js');

const NOW = '2026-11-14T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
const SHOTS = process.env.Q5_SHOTS || null;
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const eng = E.start();
  const fixtures = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } };
  const s = await site.start({ fixtures, posts: { [E.ROUTE]: (b) => eng.route(b) } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const [width, height] of [[1440, 1000], [390, 844], [320, 700]]) {
      const phone = width < 720, tag = String(width);
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const posts = []; page.on('request', (r) => { if (r.url().endsWith('/' + E.ROUTE)) posts.push([r.method(), JSON.parse(r.postData() || '{}').op]); });
      const Q5 = '[data-q5-block]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      await page.goto(s.base + '#/qgv');
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      await page.locator(Q5).waitFor();
      assert.deepEqual(posts, [], 'nothing sent when #/qgv opens');
      ok(tag + ' open: official table, 555 block idle, no request');

      phase = tag + ' 2.1 selector';
      for (const k of ['universe504', 'top500', 'expanded']) assert.equal(await page.locator('[data-q5-pop="' + k + '"]').count(), 1);
      for (const k of ['OFFICIAL', 'U1-555', 'S1-555', 'MY']) assert.equal(await page.locator('[data-q5-model="' + k + '"]').count(), 1);
      await page.locator('[data-q5-pop="top500"]').click();
      await page.locator('[data-q5-board]').waitFor();
      assert.equal(await page.locator('[data-lb-table] tbody tr[data-row]').count(), 0, 'no official row under 시총 Top500');
      assert.match(await text('[data-q5-board-text]'), /기존504에서만 계산됨/);
      assert.ok(await page.locator('[data-q5-held]').count() >= 5, 'the other 2.1 blocks are held');
      await page.locator('[data-q5-model="U1-555"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'RESULT_NOT_DELIVERED');
      assert.match(await text('[data-q5-board-text]'), /모집단 계약 전 · 다른 모형 결과를 이 이름으로 보이지 않음/);
      assert.match(await text('[data-q5-pop-lines]'), /계약·전달 전/);
      await page.locator('[data-q5-pop="universe504"]').click(); await page.locator('[data-q5-model="MY"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'NO_SAVED');
      await page.locator('[data-q5-pop="expanded"]').click(); await page.locator('[data-q5-model="OFFICIAL"]').click();
      assert.match(await text('[data-q5-board-text]'), /확장 연구 모집단에는 공식 QGV 없음/);
      await page.locator('[data-q5-pop="universe504"]').click();
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      assert.equal(await page.locator('[data-q5-board]').count(), 0);
      ok(tag + ' 2.1: 3 populations × 4 models; only 기존504 × 기존 공식 shows the official table, others held');

      phase = tag + ' load';
      const load = page.locator('[data-k="q5-load"]');
      if (width === 1440) { await load.focus(); await page.keyboard.press('Enter'); } else await load.click();
      await page.locator(Q5 + ' [data-q5-role]').first().waitFor();
      assert.deepEqual(posts, [['POST', 'qgv555_context']]);
      for (const a of ['Q', 'G', 'V']) {
        await page.locator('[data-q5-tab="' + a + '"]').click();
        assert.equal(await page.locator('[data-q5-roles="' + a + '"] [data-q5-role]').count(), 5, a + ' has five roles');
      }
      await page.locator('[data-q5-tab="Q"]').click();
      const active0 = await page.locator('[data-q5-active]').getAttribute('data-q5-active');
      assert.match(active0, /^Q\d\/G\d\/V\d$/);
      assert.match(await text('[data-q5-base]'), /qgv-555-unified-default\/0\.1\.0 · 0\.1\.0 · 통합 공통/);
      ok(tag + ' 2.2.7: one click = one POST; five roles per axis; active ' + active0);

      phase = tag + ' edit';
      const prof = '[data-q5-role="profitability"]';
      await page.locator(prof + ' [data-k="q5-add-profitability"]').click();
      const pick = page.locator(prof + ' [data-q5-card][data-q5-selectable="true"] [data-k^="q5-pick-"]').first();
      await pick.click();
      const shares = await page.locator(prof + ' input[data-k^="q5-share-"]').evaluateAll((n) => n.map((x) => Number(x.value)));
      assert.deepEqual(shares, [5000, 5000], 'a second factor splits the role budget');
      assert.equal(await page.locator(prof + ' input[data-k="q5-role-profitability"]').inputValue(), '2500');
      assert.equal(await page.locator('[data-q5-problems]').getAttribute('data-q5-problems'), '0');
      ok(tag + ' add: role budget split 5000/5000, role weight unchanged, sums fine');

      await page.locator('[data-q5-tab="V"]').click();
      const vRole = page.locator('[data-q5-roles="V"] [data-q5-role-on="true"]').first(), vId = await vRole.getAttribute('data-q5-role');
      await vRole.locator('[data-k="q5-ex-' + vId + '"]').click();
      const active1 = await page.locator('[data-q5-active]').getAttribute('data-q5-active');
      assert.equal(Number(active1.split('/V')[1]), Number(active0.split('/V')[1]) - 1);
      assert.match(await text('[data-q5-problems]'), /역할 비중 합이 10000이 아님/);
      assert.equal(await page.locator('[data-k="q5-recalc"]').isDisabled(), true, 'no recalculation while sums are off');
      ok(tag + ' exclude: active ' + active1 + ', sums say so, recalculation off');

      await page.locator('[data-k="q5-restore"]').click();
      assert.equal(await page.locator('[data-q5-active]').getAttribute('data-q5-active'), active0);
      assert.match(await text('[data-q5-msg]'), /기본값 복원 · qgv-555-unified-default\/0\.1\.0 · 0\.1\.0 · 통합 공통/);
      ok(tag + ' restore: base preset id / version / scope, active back to ' + active0);

      phase = tag + ' not fit';
      await page.locator('[data-q5-m2="S1-555"]').click();
      await page.locator('[data-k="q5-scope"]').selectOption('FINANCIALS|BANK');
      assert.match(await text('[data-q5-base]'), /은행/);
      await page.locator('[data-q5-tab="Q"]').click();
      let found = false;
      for (const r of await page.locator('[data-q5-roles="Q"] [data-q5-role]').evaluateAll((n) => n.map((x) => x.dataset.q5Role))) {
        await page.locator('[data-k="q5-add-' + r + '"]').click();
        const unfit = page.locator('[data-q5-cards="' + r + '"] [data-q5-selectable="false"]').filter({ hasText: '부적합' });
        if (await unfit.count()) { found = true; assert.equal(await unfit.first().locator('[data-k^="q5-pick-"]').count(), 0); break; }
        await page.locator('[data-k="q5-add-' + r + '"]').click();
      }
      assert.ok(found, 'a not-fit factor is shown with its reason and no pick');
      ok(tag + ' bank: not-fit factor shown in words, not selectable');

      await page.locator('[data-k="q5-axis-Q"]').fill('4400'); await page.locator('[data-k="q5-axis-Q"]').dispatchEvent('change');
      await page.locator('[data-k="q5-axis-G"]').fill('2300'); await page.locator('[data-k="q5-axis-G"]').dispatchEvent('change');
      await page.locator('[data-k="q5-scope"]').selectOption('FINANCIALS|INSURANCE');
      const ins = await page.locator('[data-k="q5-axis-Q"]').inputValue();
      assert.notEqual(ins, '4400', 'the bank edit is not copied to insurance');
      ok(tag + ' bank → insurance: no propagation');

      phase = tag + ' recalc';
      await page.locator('[data-q5-m2="U1-555"]').click();
      await page.locator('[data-k="q5-recalc"]').click();
      await page.locator('[data-q5-preview="ENGINE_CONTRACT_PENDING"]').waitFor();
      assert.deepEqual(posts.slice(-1), [['POST', 'qgv555_preview']]);
      const pv = await text('[data-q5-preview]');
      assert.match(pv, /재계산 엔진 계약 전 · 555 미리보기 결과 없음/);
      assert.doesNotMatch(pv, /\d+\.\d/, 'no number in the preview');
      assert.equal(await page.locator('[data-k="q5-save"]').isDisabled(), true);
      ok(tag + ' recalc: one engine call → ENGINE_CONTRACT_PENDING, no number, save off');

      phase = tag + ' deciles';
      assert.equal(await page.locator('[data-q5-deciles] .chip').count(), 10);
      assert.match(await text('[data-q5-deciles]'), /상위 20개로 대신하지 않음/);
      assert.match(await text('[data-q5-coverage]'), /475\/500/);
      ok(tag + ' D1–D10 all named, coverage 475/500');

      phase = tag + ' top500 lines';
      await page.locator('[data-q5-pop="top500"]').click(); await page.locator('[data-q5-model="U1-555"]').click();
      const lines = await text('[data-q5-pop-lines]');
      assert.match(lines, /자료가 있는 기업 중 상위 500\(전체시장 Top500 확정 아님\)/);
      assert.match(lines, /선정 기준일 2026-11-04 · 적용일 2026-11-05/);
      assert.match(lines, /원래 분모 500 고유 발행사/);
      assert.doesNotMatch(await text('[data-q5-board-text]'), /모집단 계약 전/);
      ok(tag + ' Top500 after load: 확정 아님, dates, denominator, no price');

      const main = (await text(Q5)) + '\n' + (await text('[data-lb="2.1.1"]'));
      const code = main.match(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/);
      assert.equal(code, null, 'no visible reason code: ' + (code && code[0]));
      assert.doesNotMatch(main, /예시/, 'no board example word');
      phase = tag + ' layout';
      assert.ok(await overflow() <= 0, 'no horizontal overflow');
      if (phone) {
        const small = await page.$$eval(Q5 + ' button:not([disabled]), [data-q5-select] button', (n) => n.filter((b) => b.offsetParent && b.getBoundingClientRect().height < 43.5).length);
        assert.equal(small, 0, 'phone targets ≥ 44 px');
      } else {
        await page.evaluate(() => { document.body.style.zoom = '2'; });
        assert.ok(await overflow() <= 0, '200% zoom: no horizontal overflow');
        await page.evaluate(() => { document.body.style.zoom = ''; });
      }
      if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'qgv555-' + tag + '.png'), fullPage: false });
      ok(tag + ' layout: no overflow' + (phone ? ', 44 px' : ', 200% zoom'));

      phase = tag + ' boundaries';
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter((k) => /555|top500/i.test(k))), []);
      assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.ok(posts.every(([m]) => m === 'POST'));
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      ok(tag + ' boundaries: nothing stored, POST only, CSP 0, same origin, no console error');
      await ctx.close();
    }
    console.log('PASS ' + pass + ' qgv555 browser');
  } catch (e) { console.error('FAIL at ' + phase); throw e; } finally { await browser.close(); await s.close(); await eng.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
