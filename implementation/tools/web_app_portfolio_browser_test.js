'use strict';
// New frontend · feature 6 포트폴리오, public layer P2-6 (menu 5 · route #/portfolio; screen-portfolio.js skeleton +
// screen-portfolio-live.js; boards Portfolio · MPortfolio) in a real browser at 1440 and 390. Builds the development site
// (tools/web_app_test_site.js) and serves the synthetic score inputs (tools/qgv_v2_fixture.js) and the synthetic central V
// publication (tests/fixtures/qgv_official_vectors_v1.json) as fixtures, on a fixed clock (the basis day: not STALE). Checks:
//  - Loading (split first paint): with engines.js held back the notice MODEL_NOT_CONFIRMED is already there, every slot says
//    불러오는 중, no candidate row; after the release the cards fill.
//  - The notice stands above the first candidate row (bounding boxes) on a phone and a PC, with its words (후보 목록, 확정된
//    포트폴리오가 아님, 매매 지시 아님, TARGET v1 미확정).
//  - 모델 후보: the N15 rows equal IS2.qgv.model(page).sets.N15 (rank order, ticker, sector group, tier 핵심 / 일반 and target
//    weight 8% / 6% from the tier check, data-tier / data-weight); a table on a PC, a list on a phone; the tier check status in
//    Korean with its code, applied_to_selection false (선정은 바꾸지 않음), the rule id, the set line with its shortfall (never
//    filled), the exclusion counts and the provisional subgroup line.
//  - 적용 버전·기준일: the score refresh time (UTC) and calc_version of the page, the central basis label and its price basis day,
//    the rank wording (rankLabel), the official profile id, the rule id, the IEX attribution link; no STALE chip.
//  - TARGET v1 card: not published yet (확정 창 2026-11-09 ~ 11-15), link to the builder detail screen; the builder is never run.
//  - 실제 (내 것): exactly one private panel, NOT_READY (비공개 기능 준비 중), empty body; 모의 and 5-2 · 5-3 · 5-4: 준비 중 lines.
//  - Without a publication: the model card says the page's reason (no table, no zero); without any score file: the page state
//    card with its reason; the notice stays in both. screen-portfolio-live.js answering 404: LOADER_FAILED in every slot, the
//    notice stays, the shell notice.
//  - Boundaries everywhere: same-origin only, no price / quote / Google / Worker request, no device storage (local, session,
//    IndexedDB), no CSP violation, no [style], no console error but the intended 404s, no horizontal overflow (390 and 1440), no
//    order wording, no TARGET v0, no visible NaN / undefined.
// PORTFOLIO_SHOTS=<dir> also saves a full-page screenshot per width for review. Synthetic data only.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');

const NOW = '2026-10-14T03:00:00.000Z';
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
// Live-only files (absent from the offline build) this page may ask for; their 404 is the NOT_PUBLISHED state.
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'qgv-official.json', 'qgv-official-status.json', 'forward-validation-ledger.json'];
const FULL = { 'sec-qgv2.json': { json: F.strictPayload() }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } };
const SECTIONS = ['5-1', '5-2', '5-3', '5-4'];
// The public price-free files this page may read: IS2.data.ready()'s core files and the central V publication, the catalog and
// the financial references the shared QGV page reads (qgv.js centralPage), and the reviewed names the QGV route reads when the
// test visits it in between. No price, quote, share-count or sheet file.
const PUBLIC_READS = new Set(['actual-catalog.json', 'company-names-ko.json', 'company-classification.json', 'company-types-pricefree.json', 'dart-financials.json', 'macro-evidence.json', 'macro-screen.json',
  'qgv-official-status.json', 'qgv-official.json', 'sec-13f-changes.json', 'sec-filing-windows.json', 'sec-public-inputs.json', 'sec-qg-factors.json', 'sec-qgv2.json']);
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: FULL });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const shots = process.env.PORTFOLIO_SHOTS || null;
  async function context(width, { allow404 = UNPUBLISHED } = {}) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  }
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));
  const count = (page, sel) => page.locator(sel).count();
  async function open(page, hash = '#/portfolio') {
    const at = s.requests.length;
    await page.goto(s.base + hash); await page.locator('main[data-route=portfolio]').waitFor();
    return at;
  }
  const filled = (page) => page.locator('[data-portfolio-card=model] [data-candidates], [data-portfolio-card=model] [data-state=empty], [data-portfolio-card=model] [data-state=error], [data-portfolio-slot] [data-na=LOADER_FAILED]').first().waitFor({ timeout: 30000 });
  async function boundaries(page, seen, label, from) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin (no Google, no Worker, no price source)');
    // Data reads only (the page's scripts are the loader's list): the public files the shared QGV page reads, nothing else.
    const reads = [...new Set(s.requests.slice(from).map((r) => r.name).filter((n) => !/\.(?:js|css|woff2|html|txt|png|svg)$/.test(n) && n !== 'index.html' && n !== ''))].sort();
    assert.deepEqual(reads.filter((n) => !PUBLIC_READS.has(n)), [], label + ': only public price-free files are read (no price request)');
    assert.deepEqual(seen.errors, [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    const main = await page.locator('main').innerText();
    assert.doesNotMatch(main, /주문|매수|매도|TARGET v0|\bv0\b|19종목|NaN|undefined|로그인됨/, label + ': no order wording, no TARGET v0, no broken value, no signed-in word');
    const st = await site.storage(page);
    assert.deepEqual([st.local, st.session, st.idb], [0, 0, 0], label + ': nothing stored on the device');
  }
  async function notice(page, label) {
    const n = page.locator('[data-portfolio-notice=MODEL_NOT_CONFIRMED]');
    assert.equal(await n.count(), 1, label + ': one notice');
    assert.equal(await n.evaluate((x) => x.closest('[data-section]').dataset.section), '5-1');
    const t = await n.innerText();
    for (const re of [/모델 후보.*공식 평가로 계산한 후보 목록/, /확정된 포트폴리오가 아니고/, /매매 지시도 아닙니다/, /TARGET v1은 아직 확정되지 않았습니다/]) assert.match(t, re, label + ': notice words');
    assert.ok(await n.isVisible(), label + ': notice visible');
  }
  async function sections(page, label) {
    assert.deepEqual(await page.locator('[data-section]').evaluateAll((x) => x.map((e) => e.dataset.section)), SECTIONS, label + ': the menu sections 5-1 … 5-4');
  }

  try {
    for (const width of [1440, 390]) {
      const phone = width < 720;
      // ================================================================ loading, then the full public layer
      {
        phase = width + ' loading';
        const { ctx, page, seen } = await context(width);
        let release; const gate = new Promise((r) => { release = r; });
        await page.route('**/engines.js', async (route) => { await gate; await route.continue(); });
        const at = await open(page);
        await sections(page, phase); await notice(page, phase);
        assert.equal(await count(page, '[data-portfolio-slot] [data-state=loading]'), 4, phase + ': every slot says 불러오는 중');
        assert.equal(await count(page, '[data-candidate-row]'), 0, phase + ': no candidate row before the layer');
        release(); await filled(page); await page.unroute('**/engines.js');
        phase = width + ' full';
        const L = await page.evaluate(async () => {
          const I = window.IS2, pg = await I.qgv.page(), M = I.qgv.model(pg), set = M.sets.N15;
          return { as_of: pg.as_of, calc: pg.calc_version, rank: I.qgv.rankLabel(pg), label: pg.price_basis.label, basisDay: pg.price_basis.price_basis_date, profile: M.official_profile.id,
            attr: pg.price_basis.attribution, set: { n: set.selected.length, status: set.status, complete: set.complete, shortfall: set.shortfall_pct, ids: set.selected.map((e) => e.id), tickers: set.selected.map((e) => e.ticker), ranks: set.selected.map((e) => e.rank) },
            tier: set.tier_check, excluded: M.excluded, unknown: M.unknown.subgroup };
        });
        assert.ok(L.set.n > 1, phase + ': the fixture gives N15 rows');
        // Rows: the model's N15 selection with tier and weight; a list on a phone, a table on a PC.
        const rows = await page.locator('[data-candidate-row]').evaluateAll((x) => x.map((e) => ({ id: e.dataset.candidateRow, tier: e.dataset.tier, weight: e.dataset.weight, tag: e.tagName, text: e.innerText })));
        assert.deepEqual(rows.map((r) => r.id), L.set.ids, phase + ': the N15 selection in rank order');
        assert.deepEqual([...new Set(rows.map((r) => r.tag))], [phone ? 'LI' : 'TR'], phase + ': a list on a phone, a table on a PC');
        for (const [i, r] of rows.entries()) {
          const t = L.tier.rows[i];
          assert.deepEqual([r.tier, r.weight], [t.tier, String(t.weight_pct)], phase + ': ' + r.id + ' tier and weight from the tier check');
          assert.equal(t.weight_pct, t.tier === 'CORE' ? 8 : 6);
          assert.ok(r.text.includes(L.set.tickers[i]) && r.text.includes(String(L.set.ranks[i])), phase + ': rank and ticker shown');
          assert.ok(r.text.includes(t.tier === 'CORE' ? '핵심' : '일반') && r.text.includes(t.weight_pct + '%'), phase + ': tier word and weight shown');
        }
        assert.ok(rows.some((r) => r.tier === 'CORE' && r.weight === '8') && rows.some((r) => r.tier === 'GENERAL' && r.weight === '6'), phase + ': both 8% and 6% rows');
        // The notice is above the first candidate row.
        const box = await page.evaluate(() => { const n = document.querySelector('[data-portfolio-notice]').getBoundingClientRect(), r = document.querySelector('[data-candidate-row]').getBoundingClientRect(); return { nb: n.bottom, rt: r.top, nw: n.width }; });
        assert.ok(box.nb <= box.rt, phase + ': the notice (bottom ' + box.nb + ') stands above the first candidate row (top ' + box.rt + ')');
        assert.ok(box.nw <= width, phase + ': the notice fits the width');
        // Tier check, set, rule, exclusions.
        const tc = page.locator('[data-tier-check]');
        assert.deepEqual(await tc.evaluate((e) => [e.dataset.tierCheck, e.dataset.tierApplied, e.dataset.tierCore, e.dataset.tierSum]), [L.tier.status, 'false', String(L.tier.core), L.tier.sum_pct.toFixed(2)]);
        const tct = await tc.innerText();
        assert.match(tct, new RegExp('\\(' + L.tier.status + '\\)'), phase + ': the status code next to its words');
        assert.match(tct, /선정은 바꾸지 않음$/);
        if (L.tier.status === 'INCOMPLETE') assert.match(tct, /N15 미완성 \(INCOMPLETE\)/);
        assert.match(await text(page, '[data-tier-rule]'), /등급 규칙 TIERS_RC_20261014 · 오너 결정 2026-10-14 · 핵심 5 × 8% \+ 일반 10 × 6%/);
        const sl = page.locator('[data-model-set]');
        assert.deepEqual(await sl.evaluate((e) => [e.dataset.modelSet, e.dataset.modelComplete]), [L.set.status, String(L.set.complete)]);
        const slt = await sl.innerText();
        assert.ok(slt.startsWith('N15 ' + L.set.n + '/15'), phase + ': set line ' + slt);
        if (!L.set.complete) assert.match(slt, new RegExp('부족 비중 ' + L.set.shortfall.toFixed(2).replace('.', '\\.') + '% · 채우지 않음 · 비중 재조정 없음'));
        assert.equal(await text(page, '[data-model-excluded]'), '제외: 축 50% ' + L.excluded.AXES_50 + ' · 가치 함정 관문 ' + L.excluded.VALUE_TRAP_GATE + ' · 재무 안전 미달 ' + L.excluded.FINANCIAL_SAFETY + ' · 재무 안전 지표 NA ' + L.excluded.FINANCIAL_SAFETY_NA + ' · 하위 묶음 상한 ' + L.excluded.SUBGROUP_MAX_4);
        assert.equal(await text(page, '[data-model-unknown]'), '하위 묶음 미정 ' + L.unknown + '종목 · 상한 미적용 · 잠정 · 결정 대기');
        if (!phone) assert.match(await text(page, '[data-portfolio-card=model] caption'), new RegExp('순위 = ' + L.rank));
        // Basis: as_of, calc_version, central label, profile, rule, attribution; not STALE on the basis day.
        const basis = await page.locator('[data-portfolio-basis] dd').evaluateAll((x) => x.map((e) => [e.textContent, { ...e.dataset }]));
        const dd = (k) => basis.find(([, d]) => k in d);
        const day = new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' }).format(Date.parse(L.as_of)) + ' UTC';
        assert.deepEqual(dd('basisAsOf'), [day, { basisAsOf: L.as_of }], phase + ': 기준일 = the page as_of (UTC)');
        assert.deepEqual(dd('basisCalc'), [L.calc, { basisCalc: L.calc }], phase + ': calc_version of the page');
        assert.equal(dd('basisV')[0], L.label); assert.match(dd('basisPublished')[0], new RegExp('^' + L.basisDay + ' · \\d{4}\\. \\d\\d\\. \\d\\d\\. \\d\\d:\\d\\d UTC$'));
        assert.equal(dd('basisProfile')[0], L.profile);
        const all = await text(page, '[data-portfolio-basis]');
        assert.ok(all.includes(L.rank) && all.includes('TIERS_RC_20261014'), phase + ': rank wording and rule id');
        assert.equal(await count(page, '[data-basis-stale]'), 0, phase + ': fresh on the basis day');
        assert.equal(await page.locator('[data-portfolio-card=basis] [data-attribution] a').getAttribute('href'), L.attr.terms_url);
        // TARGET v1, private panel, mock, next steps.
        assert.match(await text(page, '[data-target-v1=NOT_PUBLISHED]'), /TARGET v1 확정본은 아직 게시되지 않았습니다[\s\S]*확정 창 2026-11-09 ~ 11-15/);
        assert.equal(await page.locator('[data-portfolio-card=target-v1] a.lk').getAttribute('href'), '#/detail/target-v1');
        const panels = await page.locator('[data-private-panel]').evaluateAll((x) => x.map((e) => [e.dataset.privatePanel, e.dataset.privateState, e.querySelector('[data-private-status]').textContent, e.querySelector('.private-body').textContent, e.closest('[data-section]').dataset.section]));
        assert.deepEqual(panels, [['portfolio-actual', 'NOT_READY', '비공개 기능 준비 중', '', '5-1']], phase + ': exactly one private panel, not ready, empty');
        assert.match(await text(page, '[data-actual-note]'), /보유는 이 기기와 내 시트에만 있습니다/);
        assert.match(await text(page, '[data-portfolio-card=mock]'), /준비 중 · 모의 포트폴리오 기록은 다음 P2-6 단계에서 붙입니다/);
        for (const id of ['5-2', '5-3', '5-4']) assert.match(await text(page, '[data-portfolio-slot="' + id + '"]'), /준비 중 · /, phase + ': ' + id + ' says what comes next');
        assert.equal(await count(page, 'main button'), 0, phase + ': no button (no price button, no builder run)');
        assert.equal(await count(page, '[data-portfolio-slot] [data-state=loading]'), 0, phase + ': no loading line left');
        await boundaries(page, seen, phase, at);
        if (shots) { fs.mkdirSync(shots, { recursive: true }); await page.screenshot({ path: path.join(shots, 'portfolio-' + width + '.png'), fullPage: true }); }
        // A route change and back draws the same rows (the page is shared, nothing new is stored).
        await page.evaluate(() => { location.hash = '#/qgv'; }); await page.locator('main[data-route=qgv]').waitFor();
        await page.evaluate(() => { location.hash = '#/portfolio'; }); await page.locator('main[data-route=portfolio]').waitFor(); await filled(page);
        assert.deepEqual(await page.locator('[data-candidate-row]').evaluateAll((x) => x.map((e) => e.dataset.candidateRow)), L.set.ids, phase + ': same rows after a route change');
        await boundaries(page, seen, phase + ' again', at);
        await ctx.close(); pass++;
      }
    }
    // ================================================================ no publication: the page's reason, never an empty table
    {
      phase = '390 no publication';
      s.fixture('qgv-official.json', { status: 404, body: '' });
      const { ctx, page, seen } = await context(390);
      const at = await open(page); await filled(page);
      await notice(page, phase);
      const why = await page.evaluate(async () => { const I = window.IS2, pg = await I.qgv.page(); return { code: pg.price_basis.reason, text: I.qgv.reasonText(pg.price_basis.reason), model: I.qgv.model(pg) }; });
      assert.equal(why.model, null);
      const card = page.locator('[data-portfolio-card=model] [data-state=empty]');
      assert.equal(await card.getAttribute('data-na'), why.code);
      assert.match(await card.innerText(), new RegExp(why.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' · 후보를 고르지 않습니다'));
      assert.equal(await count(page, '[data-candidate-row]'), 0, phase + ': no candidate row'); assert.equal(await count(page, '[data-candidates]'), 0, phase + ': no table');
      assert.match(await text(page, '[data-portfolio-basis]'), /계산 버전/);
      assert.equal(await count(page, '[data-private-panel=portfolio-actual][data-private-state=NOT_READY]'), 1);
      await boundaries(page, seen, phase, at);
      await ctx.close(); pass++;
    }
    // ================================================================ no score file at all: the page state card with its reason
    {
      phase = '1440 no score file';
      s.fixture('sec-qgv2.json', { status: 404, body: '' });
      const { ctx, page, seen } = await context(1440);
      const at = await open(page); await filled(page);
      await notice(page, phase);
      const pg = await page.evaluate(async () => { const I = window.IS2, p = await I.qgv.page(); return { state: p.state, reason: p.reason, text: I.qgv.reasonText(p.reason) }; });
      assert.equal(pg.state, 'NO_DATA');
      const card = page.locator('[data-portfolio-card=model] [data-page-state]');
      assert.deepEqual([await card.getAttribute('data-page-state'), await card.getAttribute('data-na')], ['NO_DATA', pg.reason]);
      assert.ok((await card.innerText()).includes(pg.text), phase + ': the page reason in words');
      assert.equal(await page.locator('[data-portfolio-basis] [data-basis-calc]').textContent(), '없음', phase + ': no calc_version, never a made-up one');
      assert.equal(await count(page, '[data-candidate-row]'), 0);
      await boundaries(page, seen, phase, at);
      await ctx.close(); pass++;
      s.fixture('sec-qgv2.json', FULL['sec-qgv2.json']); s.fixture('qgv-official.json', FULL['qgv-official.json']);
    }
    // ================================================================ error: screen-portfolio-live.js answering 404
    {
      phase = '390 live file 404';
      const { ctx, page, seen } = await context(390, { allow404: [...UNPUBLISHED, 'screen-portfolio-live.js'] });
      await page.route('**/screen-portfolio-live.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      const at = await open(page); await filled(page);
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED screen-portfolio-live.js');
      assert.equal(await count(page, '[data-portfolio-slot] [data-state=error][data-na=LOADER_FAILED]'), 4, phase + ': every slot shows the failure');
      assert.equal(await count(page, '[data-portfolio-slot] [data-mascot=alarm]'), 4);
      assert.match(await text(page, '[data-portfolio-slot="5-1"] [data-state=error]'), /층을 불러오지 못해 포트폴리오 자료를 그리지 못했습니다/);
      await notice(page, phase);
      assert.deepEqual([await count(page, '[data-state=loading]'), await count(page, '[data-private-panel]'), await count(page, '[data-candidate-row]')], [0, 0, 0]);
      await page.locator('[data-load-failed]').waitFor();
      await boundaries(page, seen, phase, at);
      await ctx.close(); pass++;
    }
    console.log('web_app_portfolio_browser_test: PASS (' + pass + ' contexts: full 1440, full 390, no publication, no score file, live-file error)');
  } catch (e) {
    console.error('web_app_portfolio_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
