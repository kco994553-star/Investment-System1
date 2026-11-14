'use strict';
// QGV 555 · 시총 Top500 · 사용자 설정 (owner 2026-11-14, DC-49) on #/qgv in a real browser at 1440×1000, 390×844 and 320×700, with
// the development engine route calling Codex #537 research.qgv_555 / top500_selection (SYNTHETIC inputs only):
//  - 2.1: 모집단 기존504 / 시총 Top500 / 확장 연구 × 모형 기존 공식 / U1-555 / S1-555 / 내 설정. Only 기존504 × 기존 공식 keeps the
//    official table; other pairs show their state panel and none of the official rows / lists. Top500 lines from the engine's
//    selection (public view): 검증된 연구 후보 / 확정 아님 with the reason, no price or market cap.
//  - 2.2.7: nothing sent on open; 「555 계약 불러오기」 = context + two selections; five roles per axis (the official 15); a second
//    metric splits the role (weights 1:1, role weight unchanged); exclude a role → active count; 「실제 재계산」 = one engine call →
//    the engine's before / after (same input, population effect none), coverage stages, D1–D10 of a role, company detail with
//    lineage; 저장 (the engine's record, this device's own key) → 내 설정 on 2.1; 저장 설정 재현 = REPRODUCED; 기본값 복원; S1
//    bank = 준비 중 (not editable, no run); an S1 edit stays in its own sector.
//  - Keyboard (Tab to the load button, Enter), 200% zoom at 1440 without horizontal overflow, phone 44 px targets and no overflow,
//    no reason code or 예시 visible in the 555 block and 2.1.1.
//  - Boundaries: no request leaves the origin, engine route POST only, only the 555 key stored, no console error, CSP 0.
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
const KEY = 'investment.web.v2.qgv555-saved';
const SHOTS = process.env.Q5_SHOTS || null;
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const eng = E.start({ env: {} });
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
      const setNum = async (k, v) => { const el = page.locator('[data-k="' + k + '"]'); await el.fill(String(v)); await el.dispatchEvent('change'); };
      await page.goto(s.base + '#/qgv');
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      await page.locator(Q5).waitFor();
      assert.deepEqual(posts, [], 'nothing sent when #/qgv opens');
      ok(tag + ' open: official table, 555 block idle, no request');

      phase = tag + ' 2.1 before load';
      for (const k of ['universe504', 'top500', 'expanded']) assert.equal(await page.locator('[data-q5-pop="' + k + '"]').count(), 1);
      for (const k of ['OFFICIAL', 'U1-555', 'S1-555', 'MY']) assert.equal(await page.locator('[data-q5-model="' + k + '"]').count(), 1);
      await page.locator('[data-q5-pop="top500"]').click();
      await page.locator('[data-q5-board]').waitFor();
      assert.equal(await page.locator('[data-lb-table] tbody tr[data-row]').count(), 0, 'no official row under 시총 Top500');
      assert.match(await text('[data-q5-board-text]'), /기존504에서만 계산됨/);
      assert.ok(await page.locator('[data-q5-held]').count() >= 5, 'the other 2.1 blocks are held');
      await page.locator('[data-q5-model="U1-555"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'RESULT_NOT_DELIVERED');
      assert.match(await text('[data-q5-board-text]'), /실제 Top500 미선정 · 다른 모형 결과를 이 이름으로 보이지 않음/);
      assert.match(await text('[data-q5-pop-lines]'), /선정 결과 전달 전/);
      await page.locator('[data-q5-pop="universe504"]').click(); await page.locator('[data-q5-model="MY"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'NO_SAVED');
      await page.locator('[data-q5-pop="expanded"]').click(); await page.locator('[data-q5-model="OFFICIAL"]').click();
      assert.match(await text('[data-q5-board-text]'), /확장 연구 모집단에는 공식 QGV 없음/);
      await page.locator('[data-q5-pop="universe504"]').click();
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      assert.equal(await page.locator('[data-q5-board]').count(), 0);
      ok(tag + ' 2.1: 3 populations × 4 models; only 기존504 × 기존 공식 shows the official table');

      phase = tag + ' load';
      const load = page.locator('[data-k="q5-load"]');
      if (width === 1440) { await load.focus(); await page.keyboard.press('Enter'); } else await load.click();
      await page.locator(Q5 + ' [data-q5-role]').first().waitFor();
      assert.deepEqual(posts, [['POST', 'qgv555_context'], ['POST', 'qgv555_population'], ['POST', 'qgv555_population']]);
      for (const a of ['Q', 'G', 'V']) {
        await page.locator('[data-q5-tab="' + a + '"]').click();
        assert.equal(await page.locator('[data-q5-roles="' + a + '"] [data-q5-role]').count(), 5, a + ' has five roles');
      }
      assert.deepEqual(await page.locator('[data-q5-roles="V"] [data-q5-role]').evaluateAll((n) => n.map((x) => x.dataset.q5Role)),
        ['v_earnings_yield', 'v_fcf_yield', 'v_vs_industry', 'v_vs_own_history', 'v_expectation_check']);
      await page.locator('[data-q5-tab="Q"]').click();
      assert.equal(await page.locator('[data-q5-active]').getAttribute('data-q5-active'), 'Q5/G5/V5');
      assert.match(await text('[data-q5-base]'), /U1-555 기본 설정 0\.1\.0 · 통합 공통/);
      ok(tag + ' 2.2.7: one click = context + two selections; the official 15 roles, five per axis; Q5/G5/V5');

      phase = tag + ' edit';
      const moat = '[data-q5-role="q_moat_proxy"]';
      await page.locator('[data-k="q5-add-q_moat_proxy"]').click();
      await page.locator('[data-q5-cards="q_moat_proxy"] [data-k="q5-pick-roic"]').click();
      assert.deepEqual(await page.locator(moat + ' input[data-k^="q5-share-"]').evaluateAll((n) => n.map((x) => Number(x.value))), [1, 1]);
      assert.equal(await page.locator('[data-k="q5-role-q_moat_proxy"]').inputValue(), '20');
      await page.locator('[data-k="q5-add-q_profitability"]').click();
      const dupe = page.locator('[data-q5-cards="q_profitability"] [data-q5-card="roic"]');
      assert.equal(await dupe.getAttribute('data-q5-selectable'), 'false', 'a chosen metric is not offered twice');
      await page.locator('[data-k="q5-add-q_profitability"]').click();
      ok(tag + ' add: role budget split 1:1, role weight unchanged, no double selection');

      await page.locator('[data-q5-tab="G"]').click();
      await page.locator('[data-k="q5-ex-g_recent_acceleration"]').click();
      assert.equal(await page.locator('[data-q5-active]').getAttribute('data-q5-active'), 'Q5/G4/V5');
      ok(tag + ' exclude: active Q5/G4/V5');

      phase = tag + ' recalc';
      await page.locator('[data-k="q5-recalc"]').click();
      await page.locator('[data-q5-preview="SHOWN"]').waitFor();
      assert.deepEqual(posts.slice(-1), [['POST', 'qgv555_preview']]);
      assert.match(await text('[data-q5-pop-effect]'), /같은 평가·참조 입력 · 모집단 효과 없음/);
      assert.equal(await page.locator('[data-q5-table] tbody tr').count(), 21);
      assert.match(await text('[data-q5-coverage]'), /15역할 모두 충족\s+21 → 0/);
      assert.equal(await page.locator('[data-q5-band]').count(), 10);
      assert.match(await text('[data-q5-deciles]'), /D10 = 상위 · 유효 21\/21/);
      assert.match(await text('[data-q5-versions]'), /unified-555\/0\.1\.0 · 설정 전 .* → 후 /);
      await page.locator('[data-q5-table] tbody tr').first().locator('button').click();
      await page.locator('[data-q5-detail]').waitFor();
      assert.match(await text('[data-q5-detail]'), /명목 .*% · 실효 /);
      await page.locator('[data-q5-overlap] summary').click();
      assert.match(await text('[data-q5-overlap]'), /return_level .* 명목 [0-9.]+% · 실효 /);
      ok(tag + ' recalc: one engine call; same input; 21 rows; coverage 21 → 0 (15 roles); D1–D10; versions; detail lineage');

      phase = tag + ' save';
      await page.locator('[data-k="q5-save"]').click();
      await page.locator('[data-q5-msg]').waitFor();
      assert.match(await text('[data-q5-msg]'), /이 기기에 저장함 · U1-555/);
      assert.deepEqual(posts.slice(-1), [['POST', 'qgv555_preview']], 'saving sends nothing');
      assert.deepEqual(await page.evaluate(() => Object.keys(localStorage).filter((k) => /qgv/i.test(k))), [KEY]);
      await page.locator('[data-k="q5-replay"]').click();
      await page.locator('[data-q5-replay="REPRODUCED"]').waitFor();
      await page.locator('[data-q5-model="MY"]').click();
      assert.equal(await page.locator('[data-q5-board]').getAttribute('data-q5-board'), 'SAVED_SYNTHETIC');
      await page.locator('[data-q5-model="OFFICIAL"]').click();
      ok(tag + ' save: the engine record on this device only; replay REPRODUCED; 내 설정 on 2.1');

      phase = tag + ' restore';
      await page.locator('[data-k="q5-restore"]').click();
      assert.match(await text('[data-q5-msg]'), /기본값 복원 · U1-555 기본 설정 0\.1\.0/);
      assert.equal(await page.locator('[data-q5-active]').getAttribute('data-q5-active'), 'Q5/G5/V5');
      assert.equal(await page.locator('[data-q5-preview="SHOWN"]').count(), 0, 'the preview of another setting is not shown');
      ok(tag + ' restore: own candidate and version, Q5/G5/V5, the old preview hidden');

      phase = tag + ' S1';
      await page.locator('[data-q5-m2="S1-555"]').click();
      await page.locator('[data-k="q5-scope"]').selectOption('ENERGY|GENERAL');
      await page.locator('[data-q5-tab="Q"]').click();
      await setNum('q5-role-q_profitability', 40);
      await page.locator('[data-k="q5-scope"]').selectOption('INFORMATION_TECHNOLOGY|GENERAL');
      assert.equal(await page.locator('[data-k="q5-role-q_profitability"]').inputValue(), '25', 'the energy edit does not reach IT');
      await page.locator('[data-k="q5-scope"]').selectOption('FINANCIALS|BANK');
      assert.match(await text('[data-q5-base]'), /은행 · 555 정의 준비 중/);
      assert.equal(await page.locator('[data-k="q5-recalc"]').isDisabled(), true);
      assert.equal(await page.locator('[data-k="q5-role-q_profitability"]').isDisabled(), true);
      ok(tag + ' S1: an edit stays in its sector; bank = 준비 중, not editable, no run');

      phase = tag + ' top500';
      await page.locator('[data-q5-pop="top500"]').click(); await page.locator('[data-q5-model="U1-555"]').click();
      assert.match(await text('[data-q5-pop-lines]'), /검증된 연구 후보 .* 공식 모집단 교체 아님/);
      await page.locator('[data-q5-sel-kind="SYNTHETIC_ROSTER_UNPROVEN"]').click();
      const lines = await text('[data-q5-pop-lines]');
      assert.match(lines, /자료가 있는 기업 중 상위 500\(전체시장 Top500 확정 아님\)/);
      assert.match(lines, /후보 명부 완전성 근거 없음/); assert.match(lines, /분모 확정 전/); assert.match(lines, /QGV 순위가 아님/);
      assert.doesNotMatch(lines, /\$|USD|시가총액 [0-9]/);
      ok(tag + ' Top500: research candidate / 확정 아님 with the reason, no price');

      phase = tag + ' layout';
      const main = (await text(Q5)) + '\n' + (await text('[data-lb="2.1.1"]'));
      const code = main.match(/\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b/);
      assert.equal(code, null, 'no visible reason code: ' + (code && code[0]));
      assert.doesNotMatch(main, /예시/);
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
      ok(tag + ' layout: no code text, no overflow' + (phone ? ', 44 px' : ', 200% zoom'));

      phase = tag + ' boundaries';
      assert.equal(await page.evaluate(() => window.__csp), 0);
      assert.ok(posts.every(([m]) => m === 'POST'));
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      ok(tag + ' boundaries: POST only, CSP 0, same origin, no console error');
      await ctx.close();
    }
    console.log('PASS ' + pass + ' qgv555 browser');
  } catch (e) { console.error('FAIL at ' + phase); throw e; } finally { await browser.close(); await s.close(); await eng.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
