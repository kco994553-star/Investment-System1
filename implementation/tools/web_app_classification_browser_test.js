'use strict';
// 공통 분류 (DC-48, owner 2026-11-07) in a real browser at 1440×1000 and 390×844 on Codex common-classification/1 output.
//  - Real source (IS2.classification.source → NONE): the company page says 공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결 with its three lines and the three
//    ids apart (검증된 증권 ID 없음); the QGV filter is off with the same words; no new request on open.
//  - Codex output (tests/fixtures/common_classification_main/main_fixture.json, pinned; the Universe504-code runs) put in place
//    of source() unchanged: every record state on the company page in its own words (확인 / 섹터 확인 · 하위 산업 미확인 / 분류
//    충돌 · 근거 불일치 / 평가일 …에 적용되는 분류 없음 / 분류 자료 없음 / 섹터 대응 미확인 · 근거 부족 (CODE)).
//  - Same record: the company page, the QGV row, the technical board rows (via the verified security) and 매크로 4.2 read the same
//    classification_record_id and classification_hash for the same company and date.
//  - QGV 공통 섹터 → 하위 산업 filter apart from the 원천 SIC filters: hides rows only (ranks unchanged), shows original N, valid N,
//    the comparison set and the evaluation date; keyboard reachable.
//  - Hash context: QGV filter → 4.2 (#/macro/cc:…) → QGV (#/qgv/cc:…) → company page → back, back, back returns to the same
//    selection; a token of another record set is not applied (분류 버전 불일치).
//  - Tech filter at the real call site, technical-filter-join/2 (owner 2026-11-08, Codex #516 5b0ec88a) on Codex's group-join
//    base renamed to page codes: Main rows without signal_day refused; keyed rows of the roster join in QGV order (VERIFIED,
//    issuers connected from the record), 그룹 밖 N행 line, filter off restores the identical table; Codex's three
//    counterexamples (row hash, row record id, other-day record) and missing / duplicate row, issuer conflict, missing link
//    refused with the table unchanged and the reason shown; confirmed empty group VERIFIED_EMPTY; views without universe context
//    and another run's projection refused; N<10 shows ranks + median without decile, unconfirmed shows neither.
//  - 4.3 keeps its text and adds the SIC basis line; phone: no overflow, 44 px. (The 4.5 exposure line's 공통 섹터 context is wired
//    in screen-policy-impact-live.js but not exercised here: this test serves no policy file.)
//  - Boundaries: no request outside the origin, no data request on route changes, no storage, no console error, CSP 0.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const X = require('./web_app_classification_fixture.js');

const NOW = '2026-11-08T03:00:00.000Z';
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const UNPUBLISHED = ['sec-public-inputs.json', 'qgv-official.json', 'qgv-official-status.json', 'macro-evidence-status.json'];
const M = X.main(), U = M.universe, IT = 'INFORMATION_TECHNOLOGY';
let phase = 'START', pass = 0;
const ok = (name) => { pass++; console.log('PASS ' + name); };

(async () => {
  assert.equal(X.mainSha(), X.MAIN_SHA256, 'Main fixture (Codex output) unchanged');
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS } } });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  try {
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = phone ? '390' : '1440';
      phase = tag + ' open';
      const ctx = await browser.newContext({ viewport: { width, height: phone ? 844 : 1000 } });
      await ctx.clock.setFixedTime(new Date(NOW));
      await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404: UNPUBLISHED });
      const text = (sel) => page.locator(sel).first().evaluate((e) => e.innerText);
      const attr = (sel, a) => page.locator(sel).first().getAttribute(a);
      const go = async (hash, sel) => { await page.evaluate((h) => { location.hash = h; }, hash); if (sel) await page.locator(sel).first().waitFor(); };
      const DONE = '[data-cc]:not([data-cc=LOADING]):not([data-cc=NOT_LOADED])';
      const company = async (code) => { await go('#/search'); await go('#/company/' + encodeURIComponent(code), DONE); };
      const openPanel = async () => { if (phone && !(await page.locator('#lb-filters.open').count())) await page.locator('[data-k=panel]').click(); };
      const qgv = async (hash = '#/qgv') => { await go('#/macro', 'main[data-route=macro]'); await go(hash, 'main[data-route=qgv]'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor(); };
      const useCC = (payload) => page.evaluate((p) => { const I = window.IS2; I.__realCC = I.__realCC || I.classification;
        I.classification = Object.freeze({ ...I.__realCC, source: p ? () => Promise.resolve({ state: 'OK', code: null, payload: p }) : I.__realCC.source }); }, payload);
      const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      // The QGV row id is Main's company id (a TARGET catalog company keeps its own id, e.g. 'amd' for NASDAQ:AMD); the record's
      // company_id is the row's Universe504 code, so rows are compared by code.
      const drawn = () => page.$$eval('[data-lb-table] tbody tr[data-row]', (trs) => trs.map((t) => ({ id: t.dataset.row, code: t.dataset.ccCompany || null, rank: t.querySelector('[data-cell=rank]').innerText, rec: t.dataset.ccRecord || null, hash: t.dataset.ccHash || null })));

      await page.goto(s.base + '#/company/NYSE%3AMMM'); await page.evaluate(() => window.IS2.ready);
      await page.locator('[data-cc]:not([data-cc=LOADING]):not([data-cc=NOT_LOADED])').waitFor();
      const at = s.requests.length;

      // ---------------- real source NONE
      phase = tag + ' none';
      assert.equal(await attr('[data-cc]', 'data-cc'), 'NONE');
      const none = await text('[data-cc]');
      for (const w of ['섹터 분류 자료 없음', '하위 산업 분류 자료 없음', '원천 SIC 원천 SIC 기록 없음', '공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결', '기업 ID NYSE:MMM', '발행사 ID 발행사 ID 미확인', '증권 ID 검증된 증권 ID 없음']) assert.ok(none.includes(w), 'NONE has ' + w + ': ' + none);
      assert.equal(await page.locator('[data-cc-link]').count(), 0, 'no context link without a record');
      await qgv();
      assert.ok((await text('[data-cc-filter=NONE]')).includes('공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결'));
      assert.equal(await page.locator('#lb-f-cc-sector').isDisabled(), true);
      assert.ok((await text('[data-filter=industry] label')).includes('원천 SIC'), 'the old filter is named 원천 SIC');
      ok(tag + ' real source NONE: words, three lines, three ids apart, filter off, 원천 SIC label');

      // ---------------- every record state on the company page (Codex runs on the page's codes)
      phase = tag + ' states';
      const WANT = { normal: ['CONFIRMED', '확인', '정보기술', '소프트웨어'], sector_only: ['SECTOR_ONLY', '섹터 확인 · 하위 산업 미확인', '정보기술', '하위 산업 미확인'],
        conflicting_primary_sector: ['CONFLICT', '분류 충돌 · 근거 불일치', '분류 충돌 · 근거 불일치', '분류 자료 없음'],
        outside_interval: ['NOT_APPLICABLE_ON_DATE', '평가일 2026-11-04에 적용되는 분류 없음', '평가일 2026-11-04에 적용되는 분류 없음', '분류 자료 없음'],
        reit_exception: ['UNRESOLVED', '섹터 대응 미확인 · 근거 부족 (REIT_UPPER_SECTOR_UNRESOLVED)', '섹터 대응 미확인', '분류 자료 없음'],
        unclassified: ['NO_DATA', '분류 자료 없음', '분류 자료 없음', '분류 자료 없음'] };
      const states = new Set();
      for (const [name, [st, words, sec, ind]] of Object.entries(WANT)) {
        await useCC(X.uRecord(name)); const code = U.record_cases[name].view.rows.find((r) => r.company_id === 'NYSE:MMM') ? 'NYSE:MMM' : U.record_cases[name].view.rows[0].company_id;
        await company(code);
        assert.equal(await attr('[data-cc]', 'data-cc'), st, name); states.add(st);
        assert.ok((await text('[data-cc-state]')).includes('분류 상태 · ' + words), name + ': ' + await text('[data-cc-state]'));
        assert.ok((await text('[data-cc-line=sector]')).includes(sec), name); assert.ok((await text('[data-cc-line=industry]')).includes(ind), name);
        const row = U.record_cases[name].view.rows.find((r) => r.company_id === code);
        assert.equal(await attr('[data-cc-record]', 'data-cc-record'), row.record_id || '');
        assert.equal(await attr('.cc-ids', 'data-cc-issuer'), row.issuer_id || '');
        assert.ok((await text('.cc-ids')).includes('증권 ID 검증된 증권 ID 없음'));
        if (name === 'normal') { assert.ok((await text('[data-cc-line=sic]')).includes('7372 · SEC 제출')); assert.equal(await page.locator('[data-cc-link]').count(), 2); }
        assert.ok(!/(^|\s)0(\s|$)|기타/.test(await text('[data-cc-state]')), 'unknown never 0 / 기타');
      }
      assert.equal(states.size, Object.keys(WANT).length, 'six different states');
      if (phone) assert.ok(await overflow() <= 0, 'company page: no overflow');
      ok(tag + ' company page: six record states in their own words, record id / issuer / no security id');

      // ---------------- same record on the company page, the QGV row and 매크로 4.2 (one CLI run)
      phase = tag + ' same record';
      const B = X.uBundle(), H = B.view.classification_hash;
      await useCC(B); await company('NYSE:MMM');
      const recMMM = B.view.rows.find((r) => r.company_id === 'NYSE:MMM').record_id;
      assert.equal(await attr('[data-cc-record]', 'data-cc-record'), recMMM); assert.equal(await attr('[data-cc-record]', 'data-cc-hash'), H);
      await qgv();
      await page.locator('[data-cc-filter=ALL]').waitFor(); await openPanel();
      const row = page.locator('[data-lb-table] tr[data-row="NYSE:MMM"]');
      if (!(await row.count())) { await page.selectOption('#lb-f-cc-sector', IT); await page.locator('[data-cc-filter=' + IT + ']').waitFor(); }
      assert.equal(await page.locator('[data-lb-table] tr[data-row="NYSE:MMM"]').getAttribute('data-cc-record'), recMMM);
      assert.equal(await page.locator('[data-lb-table] tr[data-row="NYSE:MMM"]').getAttribute('data-cc-hash'), H);
      assert.equal(await attr('[data-cc-filter]', 'data-cc-hash'), H);
      assert.equal(await attr('[data-cc-qgv-links]', 'data-cc-qgv-links'), B.qgv_links.preview_identity.preview_id);
      const parts = await page.evaluate((c) => ['qgv_links', 'technical', 'macro'].map((p) => window.IS2.classification.partRecord(p, c)), 'NYSE:MMM');
      for (const p of parts) { assert.equal(p.classification_record_id, recMMM); assert.equal(p.classification_hash, H); }
      await page.locator('[data-k=f-cc-sector]').selectOption('');
      ok(tag + ' company page, QGV row, QGV links, technical and macro rows: one record id and hash');

      // ---------------- the QGV filter: hides rows only, counts, keyboard
      phase = tag + ' filter';
      await qgv();
      const all = new Map((await drawn()).map((r) => [r.id, r.rank]));
      const original = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page(); return Q.rows(pg, { scope: 'UNIVERSE' }).length; });
      await openPanel();
      await page.locator('#lb-f-state').focus(); await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.id), 'lb-f-cc-sector', 'Tab reaches the 공통 섹터 filter');
      await page.selectOption('#lb-f-cc-sector', IT); await page.locator('[data-cc-filter=' + IT + ']').waitFor();
      const it = await drawn();
      assert.deepEqual(it.map((r) => r.code).sort(), [...U.codes].sort(), 'the 20 records of the sector (by Universe504 code)');
      assert.ok(it.some((r) => r.id === 'amd' && r.code === 'NASDAQ:AMD'), 'a TARGET catalog id stays the row id; the record is found by its code');
      const ranksOf = await page.evaluate(async (ids) => { const Q = window.IS2.qgv, pg = await Q.page(); const m = {}; for (const r of Q.rows(pg, { scope: 'UNIVERSE' })) if (ids.includes(r.code)) m[r.id] = r.rank.official; return m; }, U.codes);
      for (const r of it) { assert.equal(r.rec, B.view.rows.find((x) => x.company_id === r.code).record_id); if (all.has(r.id)) assert.equal(r.rank, all.get(r.id), 'rank unchanged ' + r.id);
        assert.ok(r.rank.includes(ranksOf[r.id] === null || ranksOf[r.id] === undefined ? '' : String(ranksOf[r.id])), 'layer rank ' + r.id); }
      const status = await text('[data-cc-filter=' + IT + ']');
      assert.ok(status.includes('공통 분류 · 원래 ' + original + '개 · 분류 확인 20개 · 실제 비교 집합 20개 · 분류 평가일 2026-11-02') && status.includes('순위·점수·분모 그대로'), status);
      const industries = await page.$$eval('#lb-f-cc-industry option', (o) => o.map((x) => x.textContent));
      assert.deepEqual(industries, ['전체', '하위 산업 미확인'], 'no industry is confirmed in this run: no industry option is made up');
      await page.selectOption('#lb-f-cc-industry', 'UNCLASSIFIED'); await page.waitForFunction(() => document.querySelector('[data-lb-table] tbody') && document.querySelectorAll('[data-lb-table] tbody tr[data-row]').length === 20);
      await page.selectOption('#lb-f-cc-sector', 'UNCLASSIFIED');
      await page.waitForFunction((n) => /실제 비교 집합 (\d+)개/.exec(document.querySelector('[data-cc-filter]').textContent)?.[1] === String(n), original - 20);
      assert.ok((await text('[data-cc-filter]')).includes('분류 확인 20개'), 'valid N stays the records\' count');
      const un = await drawn(); assert.ok(un.length > 0 && un.every((r) => !U.codes.includes(r.code)));
      if (phone) assert.ok(await overflow() <= 0, 'QGV with the filter: no overflow');
      if (phone) assert.equal(await page.$$eval('#lb-f-cc-sector, #lb-f-cc-industry', (els) => els.filter((e) => e.getBoundingClientRect().height < 44).length), 0, '44 px');
      ok(tag + ' QGV 공통 섹터 → 하위 산업 filter: rows hidden only, ranks unchanged, original / valid / comparison N + date, keyboard, 44 px');

      // ---------------- hash context: QGV → 4.2 → QGV → company → back ×3
      phase = tag + ' context';
      await page.selectOption('#lb-f-cc-sector', IT); await page.locator('[data-cc-filter=' + IT + ']').waitFor();
      const token = 'cc:' + IT + ':-:2026-11-02:' + H.slice(0, 12);
      await page.locator('a[data-cc-link=macro]').first().click();
      await page.locator('[data-cc-etf]').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/macro/' + encodeURIComponent(token));
      assert.equal(await page.locator('#macro-cc-sector').inputValue(), IT);
      const etf = await text('[data-cc-etf]');
      assert.ok(etf.includes('섹터 ETF 대리 · XLK (20개 기업)') && etf.includes('섹터 ETF는 비교 가격계열 · 구성 범위가 공통 섹터와 다를 수 있음'), etf);
      assert.equal(await attr('[data-cc-etf]', 'data-cc-hash'), H);
      assert.ok((await text('[data-cc-stat]')).includes('통계 산업 대응 0건 · 자체 섹터 수익률 미산출 · 순환매 확률 미산출'));
      const basis = await text('[data-cc-basis=SIC]'); assert.ok(basis.includes('SIC 업종군 기준(원천 분류) · 공통 산업 분류와 다름'));
      assert.ok((await text('[data-macro-slot="3-3"]')).includes('산업 사이클 상태'), '4.3 keeps its title');
      if (phone) assert.ok(await overflow() <= 0, 'macro: no overflow');
      await page.locator('a[data-cc-link=qgv]').first().click();
      await page.locator('[data-cc-filter=' + IT + ']').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/qgv/' + encodeURIComponent(token));
      assert.equal(await page.locator('#lb-f-cc-sector').inputValue(), IT);
      await page.locator('[data-lb-table] tr[data-row="NYSE:MMM"] a.co').click();
      await page.locator('[data-cc=SECTOR_ONLY]').waitFor();
      assert.equal(await attr('[data-cc-record]', 'data-cc-record'), recMMM);
      await page.goBack(); await page.locator('[data-cc-filter=' + IT + ']').waitFor();
      assert.equal(await page.locator('#lb-f-cc-sector').inputValue(), IT, 'back: the same filter');
      await page.goBack(); await page.locator('[data-cc-etf]').waitFor();
      assert.equal(await page.locator('#macro-cc-sector').inputValue(), IT, 'back: the same 4.2 sector');
      await page.goBack(); await page.locator('[data-cc-filter=' + IT + ']').waitFor();
      assert.equal(await page.evaluate(() => location.hash), '#/qgv');
      assert.equal(await page.locator('#lb-f-cc-sector').inputValue(), IT, 'back: the saved filter restored');
      // A token of another record set is not applied.
      await page.selectOption('#lb-f-cc-sector', ''); await page.locator('[data-cc-filter=ALL]').waitFor();
      await qgv('#/qgv/' + encodeURIComponent('cc:' + IT + ':-:2026-11-02:' + '0'.repeat(12)));
      await page.locator('[data-cc-token=VERSION_MISMATCH]').waitFor();
      assert.ok((await text('[data-cc-token]')).includes('분류 버전 불일치')); assert.equal(await page.locator('#lb-f-cc-sector').inputValue(), '');
      ok(tag + ' hash context QGV → 4.2 → QGV → company, back ×3 to the same selections; another version not applied; 4.3 basis line');

      // ---------------- the tech filter at the real call site (screen-qgv-live → techFilterLive.keep → classification.groupInput →
      // techScreen.joinGroupRows, technical-filter-join/2 of Codex #516 5b0ec88a), on Codex's group-join base renamed to page codes.
      phase = tag + ' tech';
      const GJ = U.group_join, GB = GJ.board, EB = GJ.technical.groups.find((g) => g.sector_id === 'ENERGY').board;
      const gjPayload = (view = GJ.view) => ({ view, technical: GJ.technical, dictionary: M.dictionary });
      const swapTech = (boards, links) => page.evaluate(([b, l]) => { const I = window.IS2; I.__realTech = I.__realTech || I.techScreen;
        I.techScreen = Object.freeze({ ...I.__realTech, source: () => Promise.resolve({ state: 'OK', code: null, payload: { data_kind: 'SYNTHETIC', cases: b }, security_links: l, text: '' }) }); }, [boards, links]);
      // Evidenced join keys on the first n page codes (the run's securities); opts.drop removes one code's row, opts.issuer / opts.set
      // put a field on one code's row, opts.dup appends a second copy of one code's row.
      const keys = (n, opts = {}) => page.evaluate(([k, codes, o]) => { const I = window.IS2; I.__realQ = I.__realQ || I.qgv; const Rq = I.__realQ;
        I.qgv = k === null ? Rq : Object.freeze({ ...Rq, rows: (pg, x) => { const out = Rq.rows(pg, x).filter((r) => r.code !== o.drop).map((r) => { const i = codes.indexOf(r.code);
          let y = i >= 0 && i < k ? { ...r, ticker: 'SYNTHETIC:TICKER:' + i, signal_day: '2017-01-06', security_id: 'SYNTHETIC:SECURITY:' + i } : r;
          if (o.issuer && r.code === o.issuer[0]) y = { ...y, issuer_id: o.issuer[1] };
          if (o.set && r.code === o.set[0]) y = { ...y, [o.set[1]]: o.set[2] };
          return y; }); return o.dup ? [...out, out.find((r) => r.code === o.dup)] : out; } }); }, [n, U.codes, opts]);
      const B35 = '[data-lb="3.5"]';
      const full = () => page.$$eval('[data-lb-table] tbody tr[data-row]', (trs) => trs.map((t) => t.dataset.row + '|' + t.innerText.replace(/\s+/g, ' ')));
      const refusedAt = async (code, group, words) => { const was = await full();
        await page.locator('[data-k=tf-on]').check(); await page.locator(B35 + ' [data-tf-join="' + code + '"]' + (group ? '[data-tf-group="' + group + '"]' : '')).waitFor();
        const t = await text(B35 + ' [data-tf-join]'); assert.ok(t.includes(words) && t.includes('리더보드는 기술 조건 없이 그대로'), code + ': ' + t);
        assert.deepEqual(await full(), was, code + ': table unchanged'); assert.equal(await page.locator('[data-lb-table] [data-cell=tech]').count(), 0); await page.locator('[data-k=tf-on]').uncheck(); return t; };
      const setup = async (payload, n, opts, boards = { it: GB }, links = GJ.security_links) => { await useCC(payload); await swapTech(boards, links); await keys(n, opts); await qgv(); };

      await setup(gjPayload(), null);
      await page.locator(B35 + ' [data-cc-tech=OK]').waitFor();
      assert.ok((await text(B35 + ' [data-cc-tech]')).includes('공통 분류 그룹 · 섹터 정보기술') && (await text(B35 + ' [data-cc-tech]')).includes('구성원 3개 기업'));
      const brows = await page.$$eval(B35 + ' [data-tf-row]', (n) => n.map((x) => ({ sec: x.dataset.tfRow, company: x.dataset.ccCompany, rec: x.dataset.ccRecord })));
      assert.equal(brows.length, 3);
      for (const r of brows) assert.equal(r.rec, GJ.view.rows.find((x) => x.company_id === r.company).record_id, 'board row record = view record');
      await company(brows[0].company); assert.equal(await attr('[data-cc-record]', 'data-cc-record'), brows[0].rec, 'company page reads the same record');
      await qgv();
      // Main rows carry no signal_day: the /2 join refuses (Codex code), nothing is made up.
      await refusedAt('SIGNAL_DAY_MISMATCH', null, '평가일 불일치');
      // (i) evidenced keys: the roster's 3 rows join (VERIFIED, issuers connected from the record) and show in QGV order.
      await keys(3); await qgv();
      const off = await full();
      const universeN = await page.evaluate(async () => { const Q = window.IS2.qgv, pg = await Q.page(); return Q.rows(pg, { scope: 'UNIVERSE' }).length; });
      await page.locator('[data-k=tf-on]').check(); await page.locator(B35 + ' [data-tf-join="3"]').waitFor();
      assert.equal(await attr(B35 + ' [data-tf-validation]', 'data-tf-validation'), 'VERIFIED'); assert.equal(await attr(B35 + ' [data-tf-validation]', 'data-tf-issuer-connections'), '3');
      assert.ok((await text(B35 + ' [data-tf-join]')).includes('결합 /2 · 그룹 명부 확인 3행 · 발행사 연결 3행'));
      const wantOrder = await page.evaluate(async (codes) => { const I = window.IS2, Q = I.__realQ, pg = await Q.page();
        return I.qgvLive.helpers.sortRows(Q.rows(pg, { scope: 'UNIVERSE' }).filter((r) => codes.includes(r.code)), 'qgv').map((r) => r.id); }, GJ.codes);
      assert.deepEqual((await drawn()).map((r) => r.id), wantOrder, '(i) the group\'s PASS rows in QGV order');
      // (ii) the rows outside the group are untouched; off restores the identical table.
      assert.equal(await attr(B35 + ' [data-tf-outside]', 'data-tf-outside'), String(universeN - 3));
      assert.ok((await text(B35 + ' [data-tf-outside]')).includes('그룹 밖 ' + (universeN - 3) + '행 · 조건 적용 대상 아님 · 원래 점수·순위 그대로'));
      await page.locator('[data-k=tf-on]').uncheck(); await page.waitForFunction((n) => document.querySelectorAll('[data-lb-table] tbody tr[data-row]').length === n, off.length);
      assert.deepEqual(await full(), off, '(ii) filter off: the full table with identical scores and ranks');
      // The three counterexamples Codex found in Main 23dd5dc5, then the other contract refusals; each leaves the table unchanged.
      await keys(3, { set: [U.codes[0], 'classification_hash', 'b'.repeat(64)] }); await qgv();
      await refusedAt('ROW_CLASSIFICATION_MISMATCH', null, '행의 분류 해시·기록 ID ≠ 그룹 명부 · 덮어쓰지 않음');
      await keys(3, { set: [U.codes[0], 'classification_record_id', 'SYNTHETIC:WRONG'] }); await qgv();
      await refusedAt('ROW_CLASSIFICATION_MISMATCH', null, '행의 분류 해시·기록 ID ≠ 그룹 명부 · 덮어쓰지 않음');
      await setup(gjPayload(GJ.view_not_applicable_on_day), 3);
      await refusedAt('GROUP_MEMBERSHIP_UNCONFIRMED', null, '비교 그룹 구성원 미확인');
      await setup(gjPayload(), 3, { drop: U.codes[1] });
      await refusedAt('GROUP_MEMBER_MISSING', null, '그룹 구성원 행 누락 · 나머지만으로 결합하지 않음');
      await keys(3, { dup: U.codes[2] }); await qgv();
      await refusedAt('DUPLICATE_GROUP_ROW', null, '같은 기업 코드 행 중복');
      await keys(3, { issuer: [U.codes[2], 'SYNTHETIC:ISSUER:WRONG'] }); await qgv();
      await refusedAt('ISSUER_CLASSIFICATION_MISMATCH', null, '행의 발행사 ≠ 그룹 명부 발행사 · 바꾸지 않음');
      await setup(gjPayload(), 3, {}, { it: GB }, GJ.security_links.filter((l) => l.security_id !== 'SYNTHETIC:SECURITY:1'));
      await refusedAt('FIXED_SECURITY_LINK_MISSING', null, '매핑 없음');
      // A confirmed empty group: VERIFIED_EMPTY, 0 rows (a known empty group, not an unknown one).
      await setup(gjPayload(), 3, {}, { it: GB, energy: EB });
      await page.selectOption('#tf-board', 'energy'); await page.locator(B35 + ' [data-metric-card=momentum_6m] [data-valid-count]').waitFor();
      assert.equal(await text(B35 + ' [data-metric-card=momentum_6m] [data-valid-count]'), '유효 종목 0 / 0');
      await page.locator('[data-k=tf-on]').check(); await page.locator(B35 + ' [data-tf-join="0"]').waitFor();
      assert.equal(await attr(B35 + ' [data-tf-validation]', 'data-tf-validation'), 'VERIFIED_EMPTY'); await page.locator('[data-k=tf-on]').uncheck();
      await page.selectOption('#tf-board', 'it');
      // Codex technical-case views carry no universe context: no roster, no join.
      const TC = X.uTechnical(), TB = TC.technical.groups.find((g) => g.sector_id === IT).board;
      await setup(TC, 10, {}, { it: TB }, U.technical_normal.security_links);
      await refusedAt('BOARD_GROUP_ROWS_UNRESOLVED', 'GROUP_UNIVERSE_CONTEXT_REQUIRED', '분류 기록에 모집단 문맥(universe) 없음');
      // Another run's technical part: 분류 버전 불일치, no join.
      await setup({ ...X.uBundle(), technical: GJ.technical }, 3);
      await page.locator('[data-cc-mismatch=technical]').waitFor(); assert.ok((await text('[data-cc-mismatch]')).includes('분류 버전 불일치'));
      await refusedAt('BOARD_GROUP_ROWS_UNRESOLVED', 'CLASSIFICATION_VERSION_MISMATCH', '분류 버전 불일치');
      assert.equal(await attr(B35 + ' [data-cc-tech]', 'data-cc-tech'), 'VERSION_MISMATCH');
      // (v) small sample vs unconfirmed identity: different words; ranks / median only for the confirmed small group.
      for (const [name, st, words] of [['nine_valid', 'N_BELOW_10', '유효 종목 9 < 10 · 순위·중앙값만 · 분위 없음'], ['missing_security', 'UNCONFIRMED', '그룹 구성 미확인 · 순위·중앙값·분위 없음']]) {
        const P = X.uTech(name), PB = P.technical.groups.find((g) => g.sector_id === IT).board;
        await setup(P, 10, {}, { it: PB }, U['technical_' + name].security_links);
        const card = B35 + ' [data-metric-card=momentum_6m][data-tech-metric-state=' + st + ']'; await page.locator(card).waitFor();
        const ct = await text(card); assert.ok(ct.includes(words), ct);
        const ranks = await page.$$eval(B35 + ' [data-tf-row] [data-tf-rank]', (n) => n.map((x) => x.textContent));
        if (st === 'N_BELOW_10') { assert.ok(ct.includes('중앙값 ') && !ct.includes('중앙값 없음') && ranks.some((r) => /^\d+$/.test(r)), 'N<10: ranks and median');
          assert.ok(!/D\d/.test(await text(B35 + ' .tf-board')), 'N<10: no decile'); }
        else assert.ok(ct.includes('중앙값 없음') && ranks.every((r) => r === '—'), 'unconfirmed: no rank, no median');
      }
      await keys(null); await useCC(null);
      if (phone) assert.ok(await overflow() <= 0, 'tech block: no overflow');
      ok(tag + ' tech filter /2 at the call site: no signal_day refused; 3-row roster joins in QGV order (VERIFIED, 3 issuers connected), 그룹 밖 N행, off restores; row hash / row record / other-day record (Codex counterexamples), missing / duplicate row, issuer conflict, missing link refused with the table unchanged; empty group VERIFIED_EMPTY; no universe context / other run refused; N<10 vs unconfirmed');

      // ---------------- an invalid payload is refused whole
      phase = tag + ' invalid';
      const bad = JSON.parse(JSON.stringify(X.uBundle())); bad.view.mapping_version = 'common-classification-map/2';
      await useCC(bad); await company('NYSE:MMM');
      assert.equal(await attr('[data-cc]', 'data-cc'), 'INVALID'); assert.ok((await text('[data-cc]')).includes('공통 분류 파일이 계약과 달라 쓰지 않습니다'));
      await useCC(null);
      ok(tag + ' invalid record set refused whole');

      phase = tag + ' boundaries';
      assert.deepEqual(seen.outside, []); assert.deepEqual(seen.errors, []);
      // After the first page: only the existing screens' own public files (IS2.data.FILES, each read once per page as before);
      // the classification adds none and nothing is read again on a route change.
      const FILES = await page.evaluate(() => [...window.IS2.data.FILES]), after = s.requests.slice(at).map((r) => r.name).filter((n) => n.endsWith('.json'));
      assert.deepEqual(after.filter((n) => !FILES.includes(n) && n !== 'macro-evidence-status.json'), [], 'no new data file');
      assert.equal(new Set(after).size, after.length, 'no file read twice: ' + after.join(' '));
      assert.ok(s.requests.every((r) => !/common-classification|classification-view|qgv-classification-links/.test(r.name)), 'no classification file is requested');
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
