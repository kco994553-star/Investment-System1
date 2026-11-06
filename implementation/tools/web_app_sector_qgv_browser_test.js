'use strict';
// Sector QGV (owner 2026-11-06; feature 2.2) on #/qgv section 1.2 in a real browser at 1440×1000 and 390×844.
//  - Real source (IS2.sectorQgv.source → NONE): 자료 연결 전, the official 1.1 table untouched.
//  - The SYNTHETIC bundle (tools/web_app_sector_qgv_fixture.js: v0 presets from the design §5, invented companies and scores) put
//    in place of source(): badges 기본값 · 초기 설정 / 추천 / 선택됨 / 준비 중 / 부적합 / 자료 일부 부족 as words; search by PER and
//    PBR; replace a factor; preview (before → after, computed n / original population, reasons, unscored never 0); save only
//    after a matching preview; reload keeps it (this device); cancel; restore default; a bank change does not reach insurance;
//    an invalid sum blocks the preview; a late answer to an older request is dropped; the official model is the 1.1 board.
//  - Phone: no horizontal overflow, 44 px controls; keyboard: the preview runs from Enter on the focused button.
//  - Boundaries: no request leaves the origin, no new data request, nothing stored but the one sector key, no console error, CSP 0.
//    SQ_SHOTS=<dir> saves screenshots (deviceScaleFactor 2).
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_sector_qgv_fixture.js');
const S = require('../src/investment_system/product/web_app/sector-qgv.js');

const NOW = '2026-11-06T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json'];
const KEY = 'investment.web.v2.sector-qgv-user-config';
const SHOTS = process.env.SQ_SHOTS || null;
const BUNDLE = X.bundle();
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(S.validate(BUNDLE).ok, true);
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
      const B = '[data-sq-body]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const go = async (hash, route) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator('main[data-route=' + route + ']').waitFor(); };
      const reopen = async () => { await go('#/macro', 'macro'); await go('#/qgv', 'qgv'); await page.locator(B + ' [data-sq-state], ' + B + ' [data-sq-data]').first().waitFor(); };
      const swap = (payload, delayFirst = 0) => page.evaluate(([p, d]) => { const I = window.IS2; I.__realSq = I.__realSq || I.sectorQgv; let n = 0;
        const preview = (...a) => { n++; const out = I.__realSq.preview(...a); return n === 1 && d ? new Promise((r) => setTimeout(() => r(out), d)) : out; };
        I.sectorQgv = Object.freeze({ ...I.__realSq, preview, source: () => Promise.resolve({ state: 'OK', code: null, payload: p, text: '' }) }); }, [payload, delayFirst]);
      const tableRows = () => page.locator('[data-lb-table] tbody tr[data-row]').count();
      const factorIds = () => page.$$eval(B + ' [data-sq-factor]', (n) => n.map((x) => x.dataset.sqFactor));
      const setAxis = async (a, value, sum) => { await page.fill(B + ' [data-k=sq-axis-' + a + ']', value); await page.locator(B + ' [data-k=sq-axis-' + a + ']').press('Tab');
        await page.locator(B + ' [data-sq-axis-sum="' + sum + '"]').waitFor(); };
      const preview = async () => { await page.locator(B + ' [data-k=sq-preview]').click(); await page.locator(B + ' [data-sq-preview]').waitFor(); };

      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();
      const boardRows = await tableRows();

      // ---------------- real source NONE
      phase = tag + ' none';
      await page.locator(B + ' [data-sq-state=NONE]').waitFor();
      assert.ok((await text(B)).includes(S.TEXT.NONE));
      ok(tag + ' real source NONE; official board untouched (' + boardRows + ' rows)');

      // ---------------- synthetic bundle: badges, search, replace
      phase = tag + ' bundle';
      await swap(BUNDLE); await reopen(); await page.locator(B + ' [data-sq-data=SYNTHETIC]').waitFor();
      const all = await text(B);
      assert.ok(!/\b(null|undefined)\b/.test(all), 'no null / undefined text');
      for (const w of [S.TEXT.SYNTHETIC, '연구 프리셋 sector-qgv-default/0.1.0 · 기본값 · 초기 설정', '이 기기(이 브라우저)에만 저장 · 다른 기기와 동기화 안 됨', '린치 유형 태그는 점수에 영향 없음'])
        assert.ok(all.includes(w), w);
      await page.selectOption('#sq-sector', 'ENERGY');
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_CFO_YIELD', 'V_EBITDA_TO_EV']);
      const ep = B + ' [data-sq-factor=V_EARNINGS_YIELD]';
      assert.deepEqual(await page.$$eval(ep + ' [data-sq-badge]', (n) => n.map((x) => x.dataset.sqBadge)), ['BASE', 'RECOMMENDED', 'SELECTED']);
      assert.ok((await text(ep)).includes('기본값 · 초기 설정') && (await text(ep)).includes('✓ 선택됨'), 'badges are words');
      await page.fill('#sq-q', 'PER');
      assert.equal(await page.locator(B + ' [data-sq-cand=V_EARNINGS_YIELD] button').isDisabled(), true, 'PER = E/P: already selected');
      assert.ok((await text(B + ' [data-sq-cand=V_FWD_EARNINGS_YIELD]')).includes('계산 기능 준비 중'));
      assert.equal(await page.locator(B + ' [data-sq-cand=V_FWD_EARNINGS_YIELD] button').isDisabled(), true, 'pending: not selectable');
      await page.fill('#sq-q', 'P/TBV');
      assert.ok((await text(B + ' [data-sq-cand=V_TBV_YIELD]')).includes('산식 적용 부적합'));
      await page.fill('#sq-q', 'PBR');
      assert.equal(await page.locator(B + ' [data-sq-cand=V_BOOK_YIELD] button').isDisabled(), false, 'not recommended but selectable');
      await page.fill('#sq-q', '');
      await page.selectOption(B + ' [data-k="sq-replace-V_EBITDA_TO_EV"]', 'V_BOOK_YIELD');
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_CFO_YIELD', 'V_BOOK_YIELD']);
      assert.ok((await text(B + ' [data-sq-factor=V_BOOK_YIELD]')).includes('총점 실효 15.0%'), 'V 50 % × other 30 %');
      ok(tag + ' badges as words, PER search = E/P, pending / unfit not selectable, PBR replaces EV/EBITDA in its role');

      // ---------------- preview → save → reload
      phase = tag + ' preview';
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), true, 'no save before a preview');
      if (phone) { await preview(); } else { await page.locator(B + ' [data-k=sq-preview]').focus(); await page.keyboard.press('Enter'); await page.locator(B + ' [data-sq-preview]').waitFor(); }
      const sum = await text(B + ' [data-sq-summary]');
      assert.match(sum, /총점 산출 · 전 \d+ \/ 281 \([\d.]+%\) → 후 \d+ \/ 281/);
      assert.match(sum, /미산출 사유\(후\) · .*입력 없음 \d+/); assert.match(sum, /섹터·회계모형 대응 미확인 3/);
      const rows = await page.locator(B + ' [data-sq-row]').count(); assert.equal(rows, 25, 'the 25 ENERGY companies');
      assert.ok(!/\b(null|undefined)\b/.test(await text(B)), 'no null / undefined text with a preview');
      const naCells = await page.$$eval(B + ' [data-sq-row] .na', (n) => n.map((x) => x.innerText));
      assert.ok(naCells.every((t) => t.startsWith('미산출 · ')), 'unscored shows its reason');
      assert.ok(!(await page.$$eval(B + ' [data-sq-row]', (n) => n.map((x) => x.innerText).join('\n'))).match(/(^|\s)0\.0(\s|$)/), 'never 0 for unscored');
      assert.equal(await page.locator(B + ' [data-k=sq-save]').isDisabled(), false);
      await page.locator(B + ' [data-k=sq-save]').click();
      assert.ok((await text(B + ' [data-sq-msg]')).startsWith('이 기기에 저장함'));
      const stored = JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY));
      assert.equal(S.validateConfig(stored, S.validate(BUNDLE).value).ok, true);
      assert.deepEqual(Object.keys(stored.overrides), ['ENERGY|GENERAL']);
      assert.equal(await tableRows(), boardRows, 'official board unchanged');
      await page.reload(); await page.evaluate(() => window.IS2.ready); await swap(BUNDLE); await reopen(); await page.locator(B + ' [data-sq-data]').waitFor();
      await page.selectOption('#sq-sector', 'ENERGY'); await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_CFO_YIELD', 'V_BOOK_YIELD'], 'saved on this device');
      ok(tag + ' preview (n / 281, reasons, never 0), save after a matching preview, kept after reload, official board unchanged');

      // ---------------- cancel, restore, invalid sum
      phase = tag + ' cancel';
      await setAxis('Q', '50', '11500');
      await page.locator(B + ' [data-sq-fault=AXIS_SUM]').waitFor();
      assert.equal(await page.locator(B + ' [data-k=sq-preview]').isDisabled(), true, 'invalid sum: no preview');
      await page.locator(B + ' [data-k=sq-cancel]').click();
      assert.equal(await page.locator(B + ' [data-sq-fault]').count(), 0); assert.equal(await page.inputValue(B + ' [data-k=sq-axis-Q]'), '35');
      await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_CFO_YIELD', 'V_BOOK_YIELD'], 'cancel = last saved');
      await page.locator(B + ' [data-k=sq-restore]').click();
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_CFO_YIELD', 'V_EBITDA_TO_EV'], 'restore = base preset');
      assert.ok((await text(B + ' [data-sq-msg]')).includes('기본값(sector-qgv-default/0.1.0)'));
      assert.deepEqual(Object.keys(JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY)).overrides), ['ENERGY|GENERAL'], 'not saved until the user saves');
      ok(tag + ' invalid sum blocks preview; cancel = last saved; restore = base preset, saved only on save');

      // ---------------- a bank change stays in banks
      phase = tag + ' bank';
      await page.selectOption('#sq-sector', 'FINANCIALS'); await page.selectOption('#sq-template', 'FINANCIALS|BANK'); await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.ok((await text(B + ' [data-sq-factor=V_BOOK_YIELD]')).includes('추천'), 'bank: PBR recommended');
      await page.selectOption(B + ' [data-k="sq-replace-V_BOOK_YIELD"]', 'V_TBV_YIELD');
      await preview(); await page.locator(B + ' [data-k=sq-save]').click();
      const st2 = JSON.parse(await page.evaluate((k) => localStorage.getItem(k), KEY));
      assert.deepEqual(Object.keys(st2.overrides).sort(), ['ENERGY|GENERAL', 'FINANCIALS|BANK'].sort());
      await page.selectOption('#sq-template', 'FINANCIALS|INSURANCE'); await page.locator(B + ' [data-k=sq-tab-V]').click();
      assert.deepEqual(await factorIds(), ['V_EARNINGS_YIELD', 'V_BOOK_YIELD'], 'insurance keeps its base preset');
      await page.locator(B + ' [data-k=sq-preview]').click(); await page.locator(B + ' [data-sq-preview]').waitFor();
      assert.ok((await text(B + ' [data-sq-preview]')).includes('비교집단 표본 부족'), 'small peer group named, not 0');
      ok(tag + ' bank override saved; insurance keeps its base; small peer group named');

      // ---------------- a late answer to an older request never wins
      phase = tag + ' order';
      await swap(BUNDLE, 400); await reopen(); await page.locator(B + ' [data-sq-data]').waitFor();
      await page.selectOption('#sq-sector', 'ENERGY');
      await page.locator(B + ' [data-k=sq-preview]').click();                          // request 1 (slow)
      await setAxis('Q', '30', '9500'); await setAxis('V', '55', '10000');
      await page.locator(B + ' [data-k=sq-preview]').click();                          // request 2 (fast)
      await page.locator(B + ' [data-sq-preview]').waitFor();
      const k2 = await page.locator(B + ' [data-sq-preview]').getAttribute('data-sq-preview');
      await page.waitForTimeout(600);
      assert.equal(await page.locator(B + ' [data-sq-preview]').getAttribute('data-sq-preview'), k2, 'the late answer to request 1 did not replace request 2');
      assert.equal(await page.locator(B + ' [data-sq-dropped]').getAttribute('data-sq-dropped'), '1');
      ok(tag + ' request order: the older, slower answer is dropped');

      // ---------------- official model
      phase = tag + ' official';
      await page.locator(B + ' [data-k=sq-model-OFFICIAL]').click();
      assert.ok((await text(B + ' [data-sq-state=OFFICIAL]')).includes('공식 QGV는 1.1 리더보드의 게시본 그대로'));
      assert.equal(await tableRows(), boardRows);
      await page.locator(B + ' [data-k=sq-model-DEFAULT]').click();
      assert.equal(await page.locator(B + ' [data-k=sq-save]').count(), 0, 'the research preset is read only');
      await page.locator(B + ' [data-k=sq-model-MINE]').click();
      ok(tag + ' official model = the 1.1 board; research preset read only');

      // ---------------- phone
      if (phone) {
        phase = tag + ' phone';
        await page.locator(B + ' [data-k=sq-preview]').click(); await page.locator(B + ' [data-sq-preview]').waitFor();
        assert.ok((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, 'no horizontal overflow');
        const small = await page.$$eval(B + ' select, ' + B + ' input[type=number], ' + B + ' .btn', (els) => els.filter((e) => e.offsetParent && e.getBoundingClientRect().height < 44).map((e) => e.dataset.k || e.tagName));
        assert.deepEqual(small, [], '44 px');
        ok(tag + ' phone: no overflow, 44 px controls');
      }
      if (SHOTS) await page.locator('[data-section="1-2"]').screenshot({ path: path.join(SHOTS, 'sq-' + tag + '.png') });

      // ---------------- invalid bundle
      phase = tag + ' invalid';
      const bad = JSON.parse(JSON.stringify(BUNDLE)); bad.presets[0].axis_weights.Q += 1;
      await swap(bad); await reopen(); await page.locator(B + ' [data-sq-state=INVALID]').waitFor();
      assert.match(await text(B), /AXIS_SUM/); assert.equal(await tableRows(), boardRows);
      ok(tag + ' invalid bundle refused whole; official board untouched');

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      assert.deepEqual(seen.requests.filter((u) => /sector/i.test(u) && !/\/(sector-qgv|screen-sector-qgv-live)\.js$/.test(new URL(u).pathname)), [], 'no sector data request');
      const st = await site.storage(page);
      assert.deepEqual(Object.keys(st.localItems).filter((k) => !/recent-search/.test(k)), [KEY], 'only the sector key is written by this screen');
      assert.equal(await page.evaluate(() => window.__csp), 0);
      ok(tag + ' boundaries');
      await ctx.close();
    }
    console.log(JSON.stringify({ passed: true, checks: pass }));
  } catch (e) {
    console.error('FAIL ' + phase + ': ' + (e && e.stack || e));
    process.exitCode = 1;
  } finally { await browser.close(); await s.close(); }
})();
