'use strict';
// Feature 3.5 · 1.1.8 기술 조건 필터 (owner 2026-11-03, 2026-11-04) in a real browser at 1440×1000 and 390×844 on #/qgv.
//  - Real source (IS2.techScreen.source → NONE): the words, the flow and the five definitions (6개월 일간 변동성(%, 비연율화)).
//  - Codex's public synthetic fixture of technical-leaderboard/1 (#469 f1ca390a, byte-identical, pinned) put in place of source()
//    unchanged: one board per case; the cards show unit, basis day, group, valid N / members, median, k; the median row passes
//    중앙값 이상 and fails 중앙값 초과; adding filters keeps every shown row's ORIGINAL board rank (never renumbered, still ascending);
//    group membership unknown, valid N < 10 and "computed, zero matches" read differently; the fixture's filter_example keeps
//    exactly kept_security_ids; a null adopted dollar volume stays NA even with a raw_value in the row.
//  - A joined board (tools/web_app_tech_filter_fixture.js joined(): the leaderboard's own row ids as security ids) filters the
//    leaderboard table to PASS rows in its QGV order; with Codex's fixture (no join) the leaderboard table is left as it is.
//  - Phone: board rows as a list, tech line and 기술 상세, no horizontal overflow, 44 px controls.
//  - Boundaries: values only as [data-ram-price] text, no new data request, no storage, no request outside the origin, no console
//    error, CSP 0. TECH_SHOTS=<dir> saves screenshots (deviceScaleFactor 2).
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
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const SHOTS = process.env.TECH_SHOTS || null;
const CODEX = X.codex();
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.codexSha(), X.CODEX_SHA256, 'Codex fixture unchanged');
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
      const at = s.requests.length, B = '[data-lb="3.5"]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const drawnIds = () => page.$$eval('[data-lb-table] tbody tr[data-row]', (trs) => trs.map((t) => t.dataset.row));
      const boardRows = () => page.$$eval('[data-lb="3.5"] [data-tf-row]', (n) => n.map((x) => ({ id: x.dataset.tfRow, rank: x.querySelector('[data-tf-rank]').textContent })));
      const reopen = async () => {
        await page.evaluate(() => { location.hash = '#/macro'; }); await page.locator('main[data-route=macro]').waitFor();
        await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route=qgv]').waitFor();
        await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor(); };
      const swap = (payload) => page.evaluate((p) => { const I = window.IS2; I.__realTech = I.__realTech || I.techScreen;
        I.techScreen = Object.freeze({ ...I.__realTech, source: () => Promise.resolve({ state: 'OK', code: null, payload: p, text: '' }) }); }, payload);
      const cond = async (m, c) => { await page.selectOption('#tf-' + m, c); };
      const clear = async () => { for (const m of X.METRICS) await page.selectOption('#tf-' + m, 'none'); };

      // ---------------- real source NONE
      phase = tag + ' none';
      await page.locator(B + ' [data-tech-state=NONE]').waitFor();
      const none = await text(B);
      assert.ok(none.includes(T.TEXT.NONE) && none.includes('6개월 일간 변동성(%, 비연율화)') && none.includes('가장 크게 흔들린 10%'), 'NONE words');
      assert.equal(await page.locator('[data-lb-table] [data-cell=tech]').count(), 0);
      ok(tag + ' real source NONE');

      // ---------------- Codex fixture, unchanged
      phase = tag + ' codex';
      await swap(CODEX); await reopen();
      await page.locator(B + ' [data-tech-data=SYNTHETIC]').waitFor();
      const labels = await page.$$eval('#tf-board option', (o) => o.map((x) => x.textContent));
      assert.deepEqual(labels, Object.keys(CODEX.cases).map((k) => '2018-02-16 · SYNTHETIC:GROUP · ' + k));
      const card = await text(B + ' [data-metric-card=volatility_6m]');
      for (const w of ['6개월 일간 변동성(%, 비연율화)', '%/일', '기준일 2018-02-16', '비교 그룹 SYNTHETIC:GROUP', '유효 종목 23 / 23', '분위 매김 (D10·D1 각 2개)']) assert.ok(card.includes(w), 'card has ' + w);
      ok(tag + ' Codex fixture read unchanged; cards with unit, basis day, group, N, k');

      // ---------------- median row: 중앙값 이상 true, 중앙값 초과 false
      phase = tag + ' median';
      await page.selectOption('#tf-by', 'momentum_3m');
      await cond('momentum_3m', 'ge_median');
      await page.locator(B + ' [data-tf-row="SYNTHETIC:S011"]').waitFor();
      assert.ok((await text(B + ' [data-tf-count]')).includes('통과 12 · 조건 미충족 11 · 판정 불가 0'));
      await cond('momentum_3m', 'gt_median');
      await page.waitForFunction(() => !document.querySelector('[data-lb="3.5"] [data-tf-row="SYNTHETIC:S011"]'));
      assert.ok((await text(B + ' [data-tf-count]')).includes('통과 11 · 조건 미충족 12'));
      ok(tag + ' median row S011: 중앙값 이상 passes, 중앙값 초과 does not');

      // ---------------- original ranks kept while filters are added
      phase = tag + ' ranks';
      await clear(); await page.selectOption('#tf-by', 'momentum_6m');
      await page.waitForFunction(() => document.querySelectorAll('[data-lb="3.5"] [data-tf-row]').length === 23);
      const all = new Map((await boardRows()).map((r) => [r.id, r.rank]));
      const want = new Map(CODEX.cases.interior_remainder_23.metrics.momentum_6m.rows.map((r) => [r.security_id, String(r.rank)]));
      assert.deepEqual([...all], [...want].sort((a, b) => Number(a[1]) - Number(b[1])), 'board ranks = file ranks, ascending');
      await cond('momentum_6m', 'ge_median'); await page.waitForFunction(() => document.querySelectorAll('[data-lb="3.5"] [data-tf-row]').length === 12);
      await cond('volatility_6m', 'exclude_D10'); await page.waitForFunction(() => document.querySelectorAll('[data-lb="3.5"] [data-tf-row]').length < 12);
      const kept = await boardRows();
      assert.ok(kept.length > 0);
      for (const r of kept) assert.equal(r.rank, all.get(r.id), 'rank unchanged for ' + r.id);
      assert.deepEqual(kept.map((r) => Number(r.rank)), [...kept.map((r) => Number(r.rank))].sort((a, b) => a - b), 'still in original rank order');
      assert.equal(await text(B + ' [data-metric-card=momentum_6m] [data-valid-count]'), '유효 종목 23 / 23', 'denominator unchanged');
      ok(tag + ' adding filters keeps original board ranks and denominators');

      // ---------------- states: unknown group, N < 10, computed zero
      phase = tag + ' states';
      await clear(); await page.selectOption('#tf-board', 'unknown_group');
      await page.locator(B + ' [data-metric-card=momentum_6m][data-tech-metric-state=UNCONFIRMED]').waitFor();
      assert.ok((await text(B + ' [data-metric-card=momentum_6m]')).includes('그룹 구성 미확인 · 순위·중앙값·분위 없음'));
      assert.ok((await text(B + ' [data-metric-card=momentum_6m]')).includes('유효 종목 NA / NA'));
      await cond('momentum_6m', 'ge_median'); await page.locator(B + ' [data-empty=TECH_UNDECIDED]').waitFor();
      assert.equal(await page.locator(B + ' [data-empty=TECH_ZERO]').count(), 0);
      await clear(); await page.selectOption('#tf-board', 'small_n_9');
      await page.locator(B + ' [data-metric-card=momentum_6m][data-tech-metric-state=N_BELOW_10]').waitFor();
      assert.ok((await text(B + ' [data-metric-card=momentum_6m]')).includes('유효 종목 9 < 10 · 순위·중앙값만 · 분위 없음'));
      await cond('momentum_6m', 'top_decile'); await page.locator(B + ' [data-empty=TECH_UNDECIDED]').waitFor();
      await cond('momentum_6m', 'ge_median'); await page.waitForFunction(() => !document.querySelector('[data-lb="3.5"] [data-empty]'));
      await clear(); await page.selectOption('#tf-board', 'negative_ties_10');
      await cond('momentum_3m', 'gt_median'); await page.locator(B + ' [data-empty=TECH_ZERO]').waitFor();
      assert.ok((await text(B + ' [data-empty=TECH_ZERO]')).includes('계산 후 조건 충족 0건'));
      assert.equal(await page.locator(B + ' [data-empty=TECH_UNDECIDED]').count(), 0);
      ok(tag + ' group unconfirmed, N < 10 and computed zero matches read differently');

      // ---------------- the fixture's filter_example
      phase = tag + ' filter example';
      await clear(); const fe = CODEX.filter_example;
      await page.selectOption('#tf-board', fe.case);
      for (const c of fe.conditions) await cond(c.metric, c.condition);
      await page.waitForFunction((n) => document.querySelectorAll('[data-lb="3.5"] [data-tf-row]').length === n, fe.kept_security_ids.length);
      assert.deepEqual((await boardRows()).map((r) => r.id).sort(), [...fe.kept_security_ids].sort());
      ok(tag + ' filter_example keeps exactly kept_security_ids');

      // ---------------- no join: the leaderboard table is left as it is
      phase = tag + ' no join';
      const before = await drawnIds();
      await page.locator('[data-k=tf-on]').check(); await page.locator(B + ' [data-tf-join="0"]').waitFor();
      assert.deepEqual(await drawnIds(), before); assert.equal(await page.locator('[data-lb-table] [data-cell=tech]').count(), 0);
      await page.locator('[data-k=tf-on]').uncheck();
      ok(tag + ' Codex boards do not join leaderboard rows: table unchanged, reason shown');

      if (SHOTS) {
        await clear(); await page.selectOption('#tf-board', 'interior_remainder_23'); await cond('momentum_6m', 'ge_median'); await cond('volatility_6m', 'exclude_D10');
        await page.locator(B).screenshot({ path: path.join(SHOTS, 'tl1-' + tag + '-block.png') });
      }

      // ---------------- a null adopted dollar volume is never filled from raw_value
      phase = tag + ' raw';
      const mod = JSON.parse(X.codexText()), dv = mod.cases.unknown_group.metrics.dollar_volume_6m.rows[0];
      Object.assign(dv, { value: null, raw_value: '987654.32', null_reasons: ['TRADE_SCOPE_UNCONFIRMED'] }); dv.conditions.gt_zero = null;
      await swap(mod); await reopen(); await page.locator(B + ' [data-tech-data=SYNTHETIC]').waitFor();
      await clear(); await page.selectOption('#tf-board', 'unknown_group'); await page.locator(B + ' [data-tf-row="SYNTHETIC:S000"]').waitFor();
      const s0 = await text(B + ' [data-tf-row="SYNTHETIC:S000"]');
      assert.ok(!/987|\$9\d\d/.test(s0) && /거래대금[^·]*사유 코드 미등록/.test(s0), 'NA, not raw: ' + s0);
      ok(tag + ' null adopted dollar volume stays NA (raw_value never shown)');

      // ---------------- a joined board filters the leaderboard in QGV order
      phase = tag + ' joined';
      const ids = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page();
        const rows = Q.rows(pg, { scope: 'UNIVERSE' }).map((r) => ({ id: r.id, t: typeof r.score.total === 'number' ? r.score.total : null }));
        return rows.sort((a, b) => (a.t !== null) - (b.t !== null) || (a.t !== null ? a.t - b.t : 0) || (a.id < b.id ? -1 : 1)).map((r) => r.id); });
      const J = X.joined(ids);
      assert.equal(T.validate(J).ok, true);
      await swap(J); await reopen(); await page.locator(B + ' [data-tech-data]').waitFor();
      await clear();
      await cond('momentum_6m', 'top_decile'); await cond('volatility_6m', 'exclude_D10');
      await page.locator('[data-k=tf-on]').check();
      await page.locator('[data-lb-table] [data-cell=tech]' + (phone ? ', [data-lb-table] .tech-line' : '')).first().waitFor({ state: 'attached' });
      const wantOrder = await page.evaluate(async (b) => { const I = window.IS2, Q = I.qgv, pg = await Q.page(), v = I.techScreen.validate(b).value.boards[0].board;
        const r = I.techScreen.evaluate(v, [{ metric: 'momentum_6m', condition: 'top_decile' }, { metric: 'volatility_6m', condition: 'exclude_D10' }]);
        const p = new Set([...r.rows].filter(([, x]) => x.state === 'PASS').map(([k]) => k));
        return I.qgvLive.helpers.sortRows(Q.rows(pg, { scope: 'UNIVERSE' }).filter((x) => p.has(x.id)), 'qgv').map((x) => x.id); }, J);
      assert.ok(wantOrder.length > 0);
      assert.deepEqual(await drawnIds(), wantOrder, 'leaderboard = PASS joined rows in QGV order');
      const firstRow = '[data-lb-table] tr[data-row="' + wantOrder[0] + '"] ' + (phone ? '.tech-line' : '[data-cell=tech]');
      assert.ok(/−\d/.test(await text(firstRow)), 'market-down D10 momentum is negative');
      if (phone) {
        const row = page.locator('[data-lb-table] tr[data-row="' + wantOrder[0] + '"]');
        await row.locator('.tech-why summary').first().click();
        const det = await row.locator('.tech-why').first().evaluate((e) => e.innerText);
        assert.ok(det.includes('분모 ') && det.includes('순위 ') && det.includes('기준일 2018-02-16'), det);
      }
      await site.assertRamOnly(page, [...new Set(J.metrics.dollar_volume_6m.rows.map((r) => T.display('dollar_volume_6m', r)))], tag);
      ok(tag + ' joined board filters the leaderboard to PASS rows in QGV order; values only as RAM text');

      // ---------------- phone layout
      if (phone) {
        phase = tag + ' phone';
        assert.ok((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, 'no overflow');
        assert.equal(await page.$$eval(B + ' select, ' + B + ' .check', (els) => els.filter((e) => e.getBoundingClientRect().height < 44).length), 0, '44 px');
        assert.ok(await page.locator(B + ' ol.tf-board').count() >= 0);
        if (SHOTS) await page.locator('[data-lb="2.1.1"]').screenshot({ path: path.join(SHOTS, 'tl1-390-table.png') });
        ok(tag + ' phone: no overflow, 44 px controls');
      }

      // ---------------- invalid input
      phase = tag + ' invalid';
      const bad = JSON.parse(X.codexText()); bad.cases.interior_remainder_23.metrics.momentum_6m.k = 5;
      await swap(bad); await reopen();
      await page.locator(B + ' [data-tech-state=ERROR][data-na=K_MISMATCH]').waitFor();
      assert.ok((await drawnIds()).length > 1);
      ok(tag + ' invalid input refused whole');

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      // reopen() passes through #/macro, whose evidence block reads its attempt record (macro-evidence-status.json) once per page
      // on the first open; nothing else.
      assert.deepEqual(s.requests.slice(at).map((r) => r.name).filter((n) => n.endsWith('.json') && n !== 'macro-evidence-status.json'), [], 'no data request');
      assert.ok(s.requests.slice(at).filter((r) => r.name === 'macro-evidence-status.json').length <= 1, 'the attempt record is read at most once');
      const st = await site.storage(page); assert.deepEqual([st.local, st.session], [0, 0]);
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
