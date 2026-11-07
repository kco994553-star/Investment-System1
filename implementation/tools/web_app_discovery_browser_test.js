'use strict';
// 의외의 기업 (owner 2026-11-06; features 2.1.8 list on #/qgv · 2.4.6 mark on the company page) in a real browser at 1440×1000
// and 390×844.
//  - Real source (IS2.discovery.source → NONE): 자료 연결 전, no mark on any company page, no request.
//  - Codex's synthetic records of discovery-company/v1 (#503, byte-identical file) put on real company rows AT TEST TIME ONLY
//    (tools/web_app_discovery_fixture.js linked(); SYNTH: ids, example.invalid sources, so every row and mark says 합성 · 시험용):
//    list rows = SELECTED + REVIEW_REQUIRED only, in 최근 선정순; 기업명순; 기존 QGV순 with the no-rank group (0점 아님) and each
//    row's 공식 순위 n / N (the publication's number, not the list place); filters only from present values, 0 results keeps the
//    conditions (조건 모두 풀기 is the user's); a list click opens the exact existing company page; the mark is the same from the
//    list, the search box and a direct link; closed by default, keyboard opens it, ①–⑦ in order with risks and the evidence
//    summary in the first opening and the source list one level further; SUSPENDED / REMOVED / CANDIDATE / IN_REVIEW have no
//    mark; review and partial states; invalid file and read failure; zero listed companies.
//  - Phone: no horizontal overflow with the long Korean line, 44 px mark and controls.
//  - Boundaries: no request for discovery data, no console error, CSP 0, nothing stored by this feature.
//    DISC_SHOTS=<dir> saves screenshots (deviceScaleFactor 2).
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_discovery_fixture.js');
const D = require('../src/investment_system/product/web_app/discovery.js');
const O = require('./qgv_official_fixture.js');

const NOW = '2026-11-06T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-universe-shares.json', 'forward-validation-ledger.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const SHOTS = process.env.DISC_SHOTS || null;
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS },
    // the synthetic central V publication (qgv_official_fixture.js) so some rows carry an official rank and some do not
    'qgv-official.json': { body: O.PUB_TEXT, type: 'application/json' } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 }, deviceScaleFactor: SHOTS ? 2 : 1 });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const B = '[data-lb="2.1.8"]';
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const go = async (hash, route) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator('main[data-route=' + route + ']').waitFor(); };
      const qgv = async () => { await go('#/macro', 'macro'); await go('#/qgv', 'qgv'); };
      const company = async (id) => { await go('#/search', 'search'); await go('#/company/' + encodeURIComponent(id), 'company');
        await page.locator('[data-result-facts] .facts-line, [data-not-found]').first().waitFor(); };
      const swap = (payload, mode = 'OK') => page.evaluate(([p, m]) => { const I = window.IS2; I.__realDisc = I.__realDisc || I.discovery;
        const src = m === 'REJECT' ? () => Promise.reject(Error('x')) : () => Promise.resolve({ state: 'OK', code: null, payload: p, text: '' });
        I.discovery = Object.freeze({ ...I.__realDisc, source: src }); }, [payload, mode]);
      const listRows = () => page.$$eval(B + ' [data-disc-row]', (n) => n.map((x) => x.dataset.discRow));
      const settle = () => page.locator(B + ' [data-disc-state], ' + B + ' [data-disc-list]').first().waitFor();

      await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor();

      // ---------------- real source NONE: list says so, company page has no mark
      phase = tag + ' none';
      await page.locator(B + ' [data-disc-state=NONE]').waitFor();
      assert.ok((await text(B)).includes(D.TEXT.NONE), 'NONE words');
      const firstId = await page.evaluate(async () => { await window.IS2.companies.ready(); return window.IS2.companies.list()[0].id; });
      await company(firstId);
      assert.equal(await page.locator('[data-disc-mark], [data-disc-mark-state]').count(), 0, 'no mark without data');
      ok(tag + ' real source NONE: 자료 연결 전, no mark');

      // ---------------- Codex's synthetic records on real rows (test time only): listed 2 (SELECTED), 3 (REVIEW, no QGV rank), 6 (SELECTED, partial)
      phase = tag + ' linked';
      const rows = await page.evaluate(async () => { const I = window.IS2, Q = I.qgv, pg = await Q.page(); await I.companies.ready();
        const all = I.companies.list().filter((c) => c.status === 'ACTIVE'), rank = (c) => { const r = Q.row(pg, c.id) || Q.row(pg, c.code); return r && Number.isInteger(r.rank.official) ? r.rank.official : null; };
        const ranked = all.filter((c) => rank(c) !== null), none = all.filter((c) => rank(c) === null);
        const pick = [ranked[0], ranked[1], ranked[2], none[0], ranked[3], ranked[4], ranked[5]];
        return pick.map((c) => ({ id: c.id, code: c.code, ticker: c.ticker, rank: rank(c), title: c.name_ko || c.name_en || c.ticker })); });
      assert.ok(rows.every(Boolean) && rows[3].rank === null && rows[2].rank !== null, 'rows picked: ' + JSON.stringify(rows.map((r) => r.rank)));
      const LONG = '합성 기업은 산업용 장비의 유지보수와 교체용 필터를 전국 단위로 대신 맡아 주는 일을 하며, 이 문장은 좁은 화면에서 줄바꿈을 시험하려고 일부러 길게 썼습니다';
      const L = X.linked(rows);
      for (const j of [...L[2].judgments, ...L[2].display.business]) if (j.category === 'BUSINESS') j.claim = LONG;
      assert.equal(D.validate(L).ok, true, JSON.stringify(D.validate(L)));
      await swap(L); await qgv(); await settle();
      const R2 = rows[2], R3 = rows[3], R6 = rows[6], at = (r) => '[data-disc-row="' + r.code + '"]';
      assert.deepEqual(await listRows(), [R2.code, R3.code, R6.code], '최근 선정순: SELECTED and REVIEW_REQUIRED only, newest first');
      const all = await text(B);
      assert.ok(all.includes(D.TEXT.SYNTHETIC) && all.includes('보류·해제·검토 중 4건'), 'synthetic and hidden count (CANDIDATE, IN_REVIEW, SUSPENDED, REMOVED)');
      assert.ok(!/\b(null|undefined)\b/.test(all), 'no null / undefined text');
      assert.ok((await text(B + ' ' + at(R2) + ' [data-disc-what]')).includes('교체용 필터'), 'business claim as 하는 일');
      assert.ok((await text(B + ' ' + at(R2) + ' [data-disc-why]')).includes('교체 필터의 반복 수요를 조사할 이유가 있다'), 'discovery claim as 발견 이유');
      assert.equal(await page.locator(B + ' ' + at(R6) + ' [data-disc-partial]').count(), 1, 'an unconfirmed claim: partial');
      assert.equal(await page.locator(B + ' ' + at(R3) + ' [data-disc-review=REVIEW_REQUIRED]').count(), 1);
      assert.ok((await text(B + ' ' + at(R3))).includes('자료 경과로 재검토 필요 — 부정 평가 아님'), 'review reason in the list');
      assert.ok((await text(B + ' ' + at(R2) + ' [data-disc-qgv]')).includes('공식 순위 ' + R2.rank + ' / '), 'official rank shown');
      assert.ok(/공식 QGV 순위 미산출[\s\S]*0점 아님/.test(await text(B + ' ' + at(R3) + ' [data-disc-qgv]')), 'no QGV: listed, not 0');
      ok(tag + ' list (Codex v1): listed states only, recent order, synthetic, partial / review, QGV rank and 미산출');

      // ---------------- sorts
      phase = tag + ' sort';
      await page.selectOption('#disc-sort', 'qgv'); await settle();
      const byRank = [R2, R6].sort((a, b) => a.rank - b.rank).map((r) => r.code);
      assert.deepEqual(await listRows(), [...byRank, R3.code], 'QGV: official rank, then the no-rank group');
      assert.deepEqual(await page.$$eval(B + ' [data-disc-group]', (n) => n.map((x) => x.dataset.discGroup)), ['RANKED', 'NO_RANK']);
      await page.selectOption('#disc-sort', 'name'); await settle();
      const byName = [R2, R3, R6].sort((a, b) => a.title.localeCompare(b.title, 'ko') || (a.code < b.code ? -1 : 1)).map((r) => r.code);
      assert.deepEqual(await listRows(), byName, '기업명순');
      await page.selectOption('#disc-sort', 'recent'); await settle();
      ok(tag + ' sorts: recent, name, QGV with the no-rank group');

      // ---------------- filters: present values only; 0 results keeps the conditions
      phase = tag + ' filter';
      assert.deepEqual(await page.$$eval('#disc-type option', (o) => o.map((x) => x.value)), ['', 'FAST_GROWER', 'NONE', 'CYCLICAL']);
      assert.ok((await text('#disc-type')).includes('고성장'));
      await page.selectOption('#disc-strength', '반복 구매'); await settle();
      assert.deepEqual(await listRows(), [R2.code, R6.code]);
      await page.selectOption('#disc-type', 'NONE'); await page.locator(B + ' [data-disc-state=FILTER_EMPTY]').waitFor();
      assert.equal(await page.$eval('#disc-type', (e) => e.value), 'NONE'); assert.equal(await page.$eval('#disc-strength', (e) => e.value), '반복 구매');
      assert.ok((await text(B + ' [data-disc-count]')).includes('3개 중 0개'));
      await page.locator(B + ' [data-k=disc-clear]').click(); await settle();
      assert.deepEqual(await listRows(), [R2.code, R3.code, R6.code]);
      ok(tag + ' filters: present values only, 0 results kept with the conditions, cleared only by the user');
      if (SHOTS) await page.locator(B).screenshot({ path: path.join(SHOTS, 'disc-list-' + tag + '.png') });

      // ---------------- list click → the exact existing company page, mark closed, keyboard opens ①–⑦
      phase = tag + ' click';
      await page.locator(B + ' ' + at(R2) + ' a[data-disc-link]').click();
      await page.locator('main[data-route=company]').waitFor();
      assert.equal(decodeURIComponent(await page.evaluate(() => location.hash)), '#/company/' + R2.id);
      const mark = page.locator('[data-disc-mark]');
      await mark.waitFor();
      assert.equal(await mark.getAttribute('data-disc-code'), R2.code); assert.equal(await mark.getAttribute('aria-expanded'), 'false');
      const panelId = await mark.getAttribute('aria-controls'), panel = page.locator('#' + panelId);
      assert.equal(await panel.isHidden(), true, 'closed by default');
      assert.equal(await page.locator('.disc-name-row h1.result-name').count(), 1, 'mark next to the name');
      await mark.focus(); await page.keyboard.press('Enter');
      assert.equal(await mark.getAttribute('aria-expanded'), 'true'); assert.equal(await panel.isVisible(), true);
      assert.deepEqual(await panel.locator('[data-disc-section]').evaluateAll((n) => n.map((x) => x.dataset.discSection)), [...D.SECTIONS, 'evidence']);
      const ptxt = await panel.evaluate((e) => e.innerText);
      for (const w of ['① 이 기업을 발견한 이유', '② 기업 유형', '③ 눈여겨볼 사업 강점', '④ 사업지역과 성장 여력', '⑤ 추가로 주목할 신호', '⑥ 함께 확인할 위험', '⑦ 확인 근거']) assert.ok(ptxt.includes(w), w);
      assert.ok(ptxt.includes('교체 필터의 반복 수요를 조사할 이유가 있다') && ptxt.includes('반대 근거'), 'discovery claim with its opposing fact');
      assert.ok(ptxt.includes('고성장 · 합성 유형 판단') && ptxt.includes('자사주 매입 실행 · 합성 자사주 매입 판단') && ptxt.includes('매출 지역'), 'type, signal, region words');
      assert.ok(ptxt.includes('One customer'), 'risk fact in the first opening');
      assert.ok(/원문 근거 \d+건 · 기준 시각 2026-11-06 · 마지막 검토일 2026-11-06/.test(ptxt) && ptxt.includes('모르는 것 · 시장 인지도 미측정'), 'evidence summary and unknowns in the first opening');
      assert.ok(ptxt.includes('인지도(시장 관심) · 미측정'), 'awareness not measured');
      assert.ok(!/린치\s*유형|8장\s*특성/.test(ptxt)); assert.ok(!/\b(null|undefined)\b/.test(ptxt), 'no null / undefined text in the panel');
      const det = panel.locator('[data-disc-sources]');
      assert.equal(await det.evaluate((e) => e.open), false, 'long source list one level further');
      await det.locator('summary').focus(); await page.keyboard.press('Enter');
      assert.equal(await det.evaluate((e) => e.open), true);
      assert.equal(await panel.locator('[data-disc-source] a').count(), 0, 'example.invalid sources are not links');
      assert.ok((await det.evaluate((e) => e.innerText)).includes('SHA-256 '));
      for (const k of ['qgv', 'technical', 'macro', 'news', 'portfolio']) assert.equal(await page.locator('[data-card=' + k + ']').count(), 1, 'existing card ' + k);
      await mark.focus(); await page.keyboard.press('Space');
      assert.equal(await panel.isHidden(), true, 'Space closes');
      if (SHOTS) { await mark.click(); await page.locator('main').screenshot({ path: path.join(SHOTS, 'disc-mark-' + tag + '.png') }); await mark.click(); }
      ok(tag + ' list click → the exact company page; mark closed; keyboard opens ①–⑦; claims with status and counterevidence; sources one level further');

      // ---------------- the same mark from a direct link and from the search box
      phase = tag + ' direct';
      await company(R3.code);
      await page.locator('[data-disc-mark=REVIEW_REQUIRED]').waitFor();
      assert.ok((await text('[data-disc-mark]')).includes('재검토 필요'));
      await page.locator('[data-disc-mark]').click();
      const rv = await text('[data-disc-panel]');
      assert.ok(rv.includes(D.TEXT.REVIEW) && rv.includes('자료 경과로 재검토 필요 — 부정 평가 아님'), 'review in the panel = list');
      await go('#/search', 'search');
      await page.locator('#q').fill(R2.ticker); await page.locator('#q').press('Enter');
      await page.locator('main[data-route=company]').waitFor(); await page.locator('[data-disc-mark]').waitFor();
      assert.equal(await page.locator('[data-disc-mark]').getAttribute('data-disc-code'), R2.code, 'search box → same mark');
      ok(tag + ' direct link and search box show the same mark and status as the list');

      // ---------------- hidden states (CANDIDATE — e.g. a company still under research — IN_REVIEW, SUSPENDED, REMOVED): no mark anywhere
      phase = tag + ' hidden';
      for (const r of [rows[0], rows[1], rows[4], rows[5]]) { await company(r.code); await page.locator('[data-card=qgv] .card-body > :not([data-pending])').first().waitFor();
        assert.equal(await page.locator('[data-disc-mark], [data-disc-panel]').count(), 0, 'no mark for ' + r.code); }
      ok(tag + ' CANDIDATE / IN_REVIEW / SUSPENDED / REMOVED: no mark');

      // ---------------- removal reflected: a selected company turned REMOVED loses list row and mark
      phase = tag + ' removed';
      const gone = X.caseOf('REMOVED'); gone.qgv_ref.company_id = R2.id;
      await swap(L.map((r, i) => (i === 2 ? gone : r))); await qgv(); await settle();
      assert.deepEqual(await listRows(), [R3.code, R6.code]);
      await company(R2.id); await page.locator('[data-card=qgv] .card-body > :not([data-pending])').first().waitFor();
      assert.equal(await page.locator('[data-disc-mark]').count(), 0);
      ok(tag + ' removal: list row and mark both gone');

      // ---------------- phone layout
      if (phone) {
        phase = tag + ' phone';
        await swap(L); await qgv(); await settle();
        assert.ok((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, 'no overflow (list)');
        assert.equal(await page.$$eval(B + ' select', (els) => els.filter((e) => e.getBoundingClientRect().height < 44).length), 0, '44 px controls');
        const wrap = await page.$eval(B + ' ' + at(R2) + ' [data-disc-what]', (e) => ({ h: e.getBoundingClientRect().height, sw: e.scrollWidth, cw: e.clientWidth }));
        assert.ok(wrap.sw <= wrap.cw && wrap.h > 40, 'long Korean line wraps: ' + JSON.stringify(wrap));
        await company(R2.id); await page.locator('[data-disc-mark]').waitFor();
        assert.ok((await page.locator('[data-disc-mark]').evaluate((e) => e.getBoundingClientRect().height)) >= 44, '44 px mark');
        await page.locator('[data-disc-mark]').click();
        assert.ok((await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)) <= 0, 'no overflow (panel)');
        ok(tag + ' phone: no overflow, long Korean wraps, 44 px');
      }

      // ---------------- data errors and zero listed
      phase = tag + ' errors';
      await swap(L.map((r, i) => (i === 2 ? X.edit((x) => { x.display.mark = null; }, r) : r))); await qgv();
      await page.locator(B + ' [data-disc-state=INVALID]').waitFor();
      assert.ok((await text(B)).includes(D.TEXT.INVALID) && (await text(B)).includes('DISPLAY_STATE_MISMATCH'));
      assert.ok((await page.locator('[data-lb-table] tbody tr[data-row]').count()) > 1, 'leaderboard untouched');
      await company(R2.id); await page.locator('[data-disc-mark-state=INVALID]').waitFor();
      assert.equal(await page.locator('[data-disc-mark]').count(), 0, 'no mark from a refused file');
      await swap(null, 'REJECT'); await qgv(); await page.locator(B + ' [data-disc-state=ERROR]').waitFor();
      assert.equal(await page.locator(B + ' [data-k=disc-retry]').count(), 1);
      await swap([L[0], L[1], L[4], L[5]]); await qgv(); await page.locator(B + ' [data-disc-state=EMPTY]').waitFor();
      assert.ok((await text(B)).includes(D.TEXT.EMPTY));
      ok(tag + ' invalid file, read failure, zero listed: told apart; leaderboard untouched');

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      assert.deepEqual(seen.requests.filter((u) => /discover/i.test(u) && !/\/(discovery|screen-discovery-live)\.js$/.test(new URL(u).pathname)), [], 'no discovery data request (only the two scripts)');
      const st = await site.storage(page);
      assert.deepEqual(Object.keys({ ...st.localItems, ...st.sessionItems }).filter((k) => /disc/i.test(k)), [], 'nothing stored by this feature');
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
