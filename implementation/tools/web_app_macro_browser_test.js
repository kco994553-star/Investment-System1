'use strict';
// New frontend · 3. 매크로 (feature 4.1–4.6, route #/macro, screen-macro.js; boards Macro · MMacro · add/MacroPhase · add/MacroMore)
// in a real browser at 1440 and 390. Builds the development site (tools/web_app_test_site.js) and serves synthetic public files
// (tools/web_app_macro_fixture.js), then checks in Chromium:
//  - Loading: with a layer file held back every data block says 불러오는 중 and the not-computed sections (3.2 순환매, 3.5 나비효과,
//    the 4.1.5 judgement state) are already there; nothing is read before the layer asks.
//  - Reads: a fresh open of #/macro reads exactly the page-open core set (IS2.data.CORE without dart-financials.json, the
//    MACRO_READS of web_app_data_layer_browser_test.js); leaving and coming back reads nothing new.
//  - Content: the concept ring (8 cells from MacroCycleRing.MODELS, 공식 판정 미산출 · NO_MODEL_OUTPUT, no arc / point /
//    probability), cell browsing by pointer and keys (arrows, Home, End, ◀ ▶ with wrap-around words), the cycle switch that
//    also moves the evidence tab; the evidence lines from MacroEvidence (per-cycle family counts, newest events 5 on a phone /
//    10 on a PC and the rest under 더 보기, the 13-row catalog with E14 held); the old MacroLights card equal to
//    IS2.engines.macro.current() and without a price button; the 8×6 board with its NA reasons; 3.2 / 3.5 / the official regime
//    as 준비 중 with what is missing and no percent; 3.3 industry groups from sec-qgv2.json named by the classification config;
//    3.4 user records in RAM only (first / same / changed comparison, delete, industry ring, kept across routes, gone after a
//    reload, nothing in localStorage / sessionStorage / IndexedDB); 3.6 tree nodes, the jump to 3.1, the public facts and the
//    raw values (Labor 4.6 %, FX excluded).
//  - Partial failure: macro-screen.json HTTP 500 (lights and raw values say 읽기 실패, the evidence and ring stay), macro-evidence.json
//    404 (근거 파일이 아직 게시되지 않았습니다, the lights stay), sec-qgv2.json invalid (3.3 says 읽기 실패, 3.4 offers two rings).
//  - Empty: the offline build's NOT_AVAILABLE files: 매크로 확인 불가, 아직 수집 전, no events, no group values, no public observation.
//  - Error: data.js answering 404 (LOADER_FAILED): every data block shows the failure with the alarm mascot, the static sections
//    stay, no uncaught error.
//  - Boundaries everywhere: same-origin requests only, no console error but the intended ones, no CSP violation, no [style], no
//    horizontal overflow at 390 (details open too), every control reachable by Tab with a visible focus ring, named buttons,
//    no draft example value (the boards' numbers are examples only).
// Synthetic data only; no price is requested or shown.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const site = require('./web_app_test_site');
const M = require('./web_app_macro_fixture.js');

const NOW = '2026-10-14T03:00:00.000Z';
// Files the offline build does not publish (answered 404 by the server when no fixture is set).
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'macro-evidence.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json'];
// The boards' example numbers and words (never shown on a public screen).
const DRAFT = /\(예상\)|강세 중반|스타벅스|브라질|커피|(?<![\d.])(?:35|50|15|40)%|3674|4512|5812|\+0\.35%p|21\.5만|20번 중|7번 \/ 20번|예시기업|반도체 \(16곳\)/;
const FULL = { 'macro-screen.json': { json: M.macroScreen() }, 'macro-evidence.json': { json: M.evidence() }, 'sec-qgv2.json': { json: M.qgv() }, 'company-classification.json': { json: M.classification() } };
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: FULL });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const set = (fx) => { for (const n of Object.keys(FULL)) s.fixture(n, Object.hasOwn(fx, n) ? fx[n] : null); };
  async function context(width, { allow404 = UNPUBLISHED } = {}) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  }
  const reads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => n.endsWith('.json')).sort();
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));// SVG text has no innerText
  const count = (page, sel) => page.locator(sel).count();
  const drawn = (page) => page.locator('[data-block="4.6"] [data-node], [data-block="4.6"] [data-state=error]').first().waitFor();
  let CORE = null;
  async function open(page, hash = '#/macro', opts = {}) {
    const at = s.requests.length;
    await page.goto(s.base + hash, opts); await page.locator('main[data-route=macro]').waitFor();
    return at;
  }
  async function boundaries(page, seen, label, { errors = [] } = {}) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
    assert.deepEqual(seen.errors.filter((e) => !errors.some((x) => x.test(e))), [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    const draft = (await page.locator('main').innerText()).match(DRAFT);
    assert.equal(draft && draft[0], null, label + ': no draft example value');
    const st = await site.storage(page);
    assert.deepEqual([st.local, st.session, st.idb], [0, 0, 0], label + ': nothing stored on the device');
  }
  // Every focusable control of main is reached by Tab (roving tablists: the selected tab), with a visible focus ring.
  async function keyboard(page, label) {
    const n = await page.evaluate(() => {
      const els = [...document.querySelectorAll('main button, main select, main input, main summary, main a[href], main [tabindex]')]
        .filter((e) => !e.disabled && e.tabIndex >= 0 && e.getClientRects().length && !e.closest('details:not([open]) > :not(summary)'));
      els.forEach((e, i) => { e.dataset.k = String(i); });
      document.getElementById('main').focus();
      return els.length;
    });
    const got = new Set(); let ring = 0;
    for (let i = 0; i < n + 40; i++) {
      await page.keyboard.press('Tab');
      const a = await page.evaluate(() => { const e = document.activeElement, cs = getComputedStyle(e); return { k: e.dataset ? e.dataset.k : undefined, inMain: !!e.closest('main'), ring: cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 }; });
      if (!a.inMain) { if (got.size) break; continue; }
      if (a.k !== undefined) got.add(a.k); if (a.ring) ring++;
    }
    assert.equal(got.size, n, label + ': every control is reached by Tab (' + got.size + '/' + n + ')');
    assert.ok(ring >= got.size, label + ': each focused control shows a focus ring');
    const unnamed = await page.evaluate(() => [...document.querySelectorAll('main button')].filter((b) => !(b.getAttribute('aria-label') || b.textContent.trim())).length);
    assert.equal(unnamed, 0, label + ': every button has a name');
    const lists = await page.evaluate(() => [...document.querySelectorAll('main [role=tablist]')].map((t) => [!!t.getAttribute('aria-label'), t.querySelectorAll('[role=tab][aria-selected=true]').length]));
    assert.ok(lists.length >= 3 && lists.every(([named, one]) => named && one === 1), label + ': named tablists with one selected tab');
    const panel = await page.evaluate(() => { const p = document.querySelector('[role=tabpanel]'); return !!document.getElementById(p.getAttribute('aria-labelledby')); });
    assert.ok(panel, label + ': the cell panel is labelled by its tab');
    await page.evaluate(() => document.querySelectorAll('[data-k]').forEach((e) => { delete e.dataset.k; }));
  }
  try {
    // ================================================================ full data, PC and phone
    for (const width of [1440, 390]) {
      const phone = width < 720, N = phone ? 5 : 10, tag = (p) => { phase = width + ' ' + p; };
      set(FULL);
      const { ctx, page, seen } = await context(width);
      // ---- loading: a layer file held back
      tag('loading');
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/engines.js', async (route) => { await gate; await route.continue(); });
      const at = await open(page, '#/macro', { waitUntil: 'domcontentloaded' });
      assert.equal(await count(page, '[data-block] [data-state=loading]'), 6, phase + ': six data blocks say 불러오는 중');
      assert.match(await text(page, '[data-block="4.1.1"] [data-state=loading]'), /^불러오는 중/);
      assert.equal(await count(page, '[data-prep]'), 2, phase + ': 3.2 and 3.5 are drawn at once as 준비 중');
      assert.equal(await count(page, '[data-judge]'), 2, phase + ': the judgement state is drawn at once');
      assert.deepEqual(reads(at), [], phase + ': nothing is read before the layer');
      release();
      await drawn(page); await page.locator('[data-ring]').waitFor();
      if (!CORE) CORE = await page.evaluate(() => window.IS2.data.CORE);
      const MACRO_READS = CORE.filter((n) => n !== 'dart-financials.json').sort();
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      tag('reads');
      assert.deepEqual(reads(at), MACRO_READS, phase + ': a fresh open reads exactly the page-open core set');
      assert.equal(await count(page, '[data-state=loading]'), 0, phase + ': no block is left loading');
      assert.deepEqual(await page.locator('[data-file]').evaluateAll((n) => n.map((x) => [x.dataset.file, x.dataset.fileState])), [['macro-screen.json', 'OK'], ['macro-evidence.json', 'OK'], ['sec-qgv2.json', 'OK']]);
      // ---- 3.1 ring
      tag('ring');
      const ring = page.locator('[data-block="4.1.1"]');
      assert.equal(await count(page, 'svg[data-ring=economy] path[data-cell]'), 8, phase + ': eight concept cells');
      assert.equal(await text(page, '[data-center]'), '회복 초입');
      assert.equal(await ring.locator('[data-official=NOT_COMPUTED]').count(), 1);
      assert.match(await ring.locator('[data-official]').innerText(), /공식 판정: 미산출[\s\S]*NO_MODEL_OUTPUT/);
      assert.equal(await text(page, '[data-probability]'), '확률 미산출 · 링 위 점 좌표 없음');
      assert.equal(await count(page, '[data-user-arc]'), 0, phase + ': no arc before a user record');
      assert.doesNotMatch(await ring.innerText(), /\d+(\.\d+)?%/, phase + ': no probability number in the ring block');
      await page.locator('[data-cell-tab="0"]').focus(); await page.keyboard.press('ArrowRight');
      assert.deepEqual(await page.evaluate(() => [document.activeElement.dataset.cellTab, document.activeElement.getAttribute('aria-selected')]), ['1', 'true'], phase + ': arrow moves the cell and the focus');
      assert.equal(await text(page, '[data-center]'), '회복 후반');
      await page.keyboard.press('End'); assert.equal(await text(page, '[data-center]'), '수축 후반');
      await page.locator('[data-cell-next]').focus(); await page.keyboard.press('Enter');
      assert.equal(await text(page, '[data-center]'), '회복 초입');
      assert.match(await page.locator('[data-ring-live]').textContent(), /수축 후반 다음은 회복 초입 · 처음으로/);
      await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Enter');// ◀ from 회복 초입
      assert.match(await page.locator('[data-ring-live]').textContent(), /마지막으로/);
      await page.locator('svg[data-ring] path[data-cell="2"]').click();
      assert.equal(await text(page, '[data-center]'), '확장 초입', phase + ': a pointer on a cell views it');
      assert.match(await text(page, '[data-cell-panel]'), /확장 초입 · 3\/8 · 추정 구간 없음 \(미산출\)/);
      await page.locator('[data-ring-tab=economy]').focus(); await page.keyboard.press('ArrowRight');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.ringTab), 'market');
      assert.equal(await count(page, 'svg[data-ring=market]'), 1);
      assert.equal(await text(page, '[data-center]'), '바닥 초입');
      assert.equal(await page.locator('[data-ev-tab=market]').getAttribute('aria-selected'), 'true', phase + ': the evidence tab follows the cycle');
      assert.equal(await text(page, '[data-summary-counts]'), '유효 경고 0계열 · 유효 개선 0계열');
      assert.match(await text(page, '[data-summary=market]'), /가격 기반 시장 근거선은 기기 전용/);
      assert.equal(await count(page, '[data-events=market] > li'), Math.min(7, N));
      await page.keyboard.press('ArrowLeft'); assert.equal(await count(page, 'svg[data-ring=economy]'), 1);
      assert.equal(await text(page, '[data-center]'), '확장 초입', phase + ': each cycle keeps its viewed cell');
      // ---- 3.1 evidence
      tag('evidence');
      assert.equal(await text(page, '[data-summary-counts]'), '유효 경고 2계열 · 유효 개선 3계열');
      assert.match(await text(page, '[data-summary=economy]'), /경고: 금리곡선, 운송 · 개선: 은행 대출, 노동 수요 선행, 생산·산출/);
      assert.equal(await count(page, '[data-events=economy] > li'), N, phase + ': the newest events first');
      assert.equal(await page.locator('[data-events-more]').getAttribute('data-events-more'), String(14 - N));
      assert.match(await text(page, '[data-events=economy] > li'), /^2026-10-08 10:00 UTC · E13 Sahm 규칙/);
      assert.equal(await count(page, '[data-catalog-row]'), 13);
      assert.match(await page.locator('[data-catalog-row=E14]').textContent(), /약관 원문 미확인 · 이름과 상태만 표시/);
      assert.match(await page.locator('[data-catalog-row=E21]').textContent(), /자료 없음 · SOURCE_KEY_NOT_CONFIGURED \(API 키 미설정\)/);
      await page.locator('[data-ev-tab=economy]').focus(); await page.keyboard.press('End');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.evTab), 'industry');
      assert.equal(await text(page, '[data-summary-counts]'), '유효 경고 1계열 · 유효 개선 0계열');
      assert.equal(await count(page, '[data-events=industry] > li'), 1);
      await page.keyboard.press('Home');
      // ---- 3.1 lights and board
      tag('lights');
      const engine = await page.evaluate(async () => { const c = await window.IS2.engines.macro.current(); return [c.state, c.available_count, c.lit_count]; });
      assert.deepEqual(engine, ['WARNING', 3, 2]);
      assert.equal(await page.locator('[data-macro-lights]').getAttribute('data-macro-lights-state'), engine[0], phase + ': the card is the engine state');
      assert.equal(await page.locator('[data-macro-lights-count]').getAttribute('data-macro-lights-count'), String(engine[1]));
      assert.deepEqual(await page.locator('[data-macro-light]').evaluateAll((n) => n.map((x) => [x.dataset.macroLight, x.dataset.macroLightState])),
        [['employment', 'ON'], ['inflation', 'OFF'], ['curve', 'ON'], ['market', 'NO_DATA'], ['credit', 'NO_DATA']]);
      assert.equal(await count(page, '[data-macro-lights-load]'), 0, phase + ': no price button, no price request');
      assert.match(await text(page, '[data-device-lights]'), /가격을 부르지 않음/);
      await page.locator('[data-board] > summary').click();
      assert.equal(await count(page, '[data-board] td'), 48);
      assert.deepEqual([...new Set(await page.locator('[data-board] tr[data-axis=FX] td').evaluateAll((n) => n.map((x) => x.dataset.na)))], ['PUBLIC_FX_EXCLUDED']);
      assert.deepEqual([...new Set(await page.locator('[data-board] tr[data-axis=Labor] td').evaluateAll((n) => n.map((x) => x.dataset.na)))], ['SOURCE_NOT_COLLECTED', 'NO_APPROVED_STATE_RULE']);
      assert.equal(await count(page, '[data-judge] [data-na=NO_MODEL_OUTPUT]'), 2);
      // ---- 3.2 / 3.5: not computed
      tag('not computed');
      const s32 = await text(page, '[data-section="3-2"]'), s35 = await text(page, '[data-section="3-5"]');
      assert.match(s32, /준비 중 · 지금 위치 미산출 · 순환매 위치 모델 없음/); assert.match(s32, /없는 것: 순환매 위치 모델/);
      assert.doesNotMatch(s32, /\d+(\.\d+)?%/, phase + ': no probability number in 3.2');
      assert.equal(await count(page, '[data-section="3-2"] [data-prob=NOT_COMPUTED] dd[data-na=NOT_COMPUTED]'), 3);
      assert.match(s35, /준비 중 · 나비효과 엔진 없음/); assert.match(s35, /REL-SOURCE/);
      assert.deepEqual(await page.locator('[data-chain] [data-na]').allTextContents(), ['—', '—', '—']);
      assert.equal(await count(page, '[data-section="3-5"] button:disabled'), 4);
      // ---- 3.3 industry groups
      tag('industry');
      const G = M.groups();
      assert.deepEqual(await page.locator('[data-group] option').evaluateAll((n) => n.map((o) => [o.value, o.textContent])),
        [['', '선택 안 함'], ...G.map((g) => [g.id, g.name + ' (' + g.id + ')'])], phase + ': groups of sec-qgv2.json in the config order, with their names');
      assert.equal(await count(page, '[data-block="4.3"] [data-na=NO_GROUP]'), 1);
      await page.locator('[data-group]').focus(); await page.locator('[data-group]').selectOption(G[0].id);
      await page.locator('[data-industry-card="' + G[0].id + '"]').waitFor();
      assert.equal(await page.evaluate(() => document.activeElement.matches('[data-group]')), true, phase + ': the focus stays on the select');
      assert.match(await text(page, '[data-industry-card]'), /미산출 · 산업 사이클 모델 없음/);
      assert.equal(await count(page, '[data-industry-card] dd[data-na=NOT_IMPLEMENTED]'), 3);
      // ---- 3.4 my position (RAM only)
      tag('mine');
      assert.deepEqual(await page.locator('[data-mine-ring] option').evaluateAll((n) => n.map((o) => o.value)), ['economy', 'market', 'industry:' + G[0].id]);
      assert.equal(await count(page, '[data-mine-empty]'), 1);
      await page.locator('[data-mine-from]').selectOption('1'); await page.locator('[data-mine-to]').selectOption('2');
      await page.locator('[data-mine-note]').focus(); await page.keyboard.type('제조 주문 회복');
      assert.equal(await text(page, '[data-note-count]'), '8 / 200');
      await page.locator('[data-mine-record]').focus(); await page.keyboard.press('Enter');
      assert.equal(await count(page, '[data-mine-entry]'), 1);
      const first = await text(page, '[data-mine-entry]');
      assert.match(first, /경기 · 회복 후반 ~ 확장 초입/); assert.match(first, /근거: 제조 주문 회복 · 그때 시스템 표시: 미산출 · 이전 내 기록과: 첫 기록/);
      assert.match(await text(page, '[data-mine-status]'), /이 화면에 기록했습니다 · 경기 회복 후반 ~ 확장 초입 · 기기에는 저장하지 않음/);
      assert.equal(await page.evaluate(() => document.activeElement.matches('[data-mine-record]')), true);
      assert.equal(await page.locator('[data-user-arc]').getAttribute('data-user-arc'), '회복 후반 ~ 확장 초입', phase + ': the ring draws the latest user estimate');
      assert.match(await page.locator('svg[data-ring]').getAttribute('aria-label'), /내 추정 회복 후반 ~ 확장 초입 \(공식 판정 아님\)/);
      await page.keyboard.press('Space');
      assert.match(await text(page, '[data-mine-entry]'), /이전 내 기록과: 같음/);
      await page.locator('[data-mine-from]').selectOption('0'); await page.locator('[data-mine-to]').selectOption('');
      await page.locator('[data-mine-record]').focus(); await page.keyboard.press('Enter');
      assert.match(await text(page, '[data-mine-entry]'), /경기 · 회복 초입 · [\s\S]*근거: — · 근거 안 씀[\s\S]*바뀜: 회복 후반 ~ 확장 초입 → 회복 초입/);
      await page.locator('[data-mine-delete]').first().focus(); await page.keyboard.press('Enter');
      assert.equal(await count(page, '[data-mine-entry]'), 2);
      assert.equal(await text(page, '[data-mine-status]'), '기록 하나를 지웠습니다');
      await page.locator('[data-mine-ring]').selectOption('industry:' + G[0].id);
      assert.deepEqual(await page.locator('[data-mine-from] option').allTextContents(), ['회복', '확장', '둔화', '수축'].flatMap((p) => [p + ' 초입', p + ' 후반']));
      await page.locator('[data-mine-record]').focus(); await page.keyboard.press('Enter');
      assert.match(await text(page, '[data-mine-entry]'), new RegExp('업종 그룹 · ' + G[0].name + ' · 회복 초입'));
      assert.equal(await count(page, '[data-mine-entry]'), 3);
      // ---- 3.6 tree
      tag('tree');
      assert.equal(await count(page, '[data-node]'), 5);
      await page.locator('[data-node=phase]').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.locator('[data-node=phase]').getAttribute('aria-pressed'), 'true');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.node), 'phase');
      assert.match(await text(page, '[data-node-text]'), /^국면 · 경기 링 · 주식시장 링/);
      assert.deepEqual(await page.locator('[data-facts] li').allTextContents(), ['경고등 · 자료 있는 경고등 3/5 · 참고 모드', '근거 지표 · 목록 13개 중 수집됨 10개', '상태판 8×6 · Level 원자료 0칸 · 나머지 NA']);
      assert.deepEqual(await page.locator('[data-raw-axis]').evaluateAll((n) => n.map((x) => [x.dataset.rawAxis, x.dataset.rawState])),
        [['Growth', 'NOT_AVAILABLE'], ['Inflation', 'NOT_AVAILABLE'], ['Labor', 'LIVE'], ['Monetary Policy', 'NOT_AVAILABLE'], ['Liquidity', 'NOT_AVAILABLE'], ['Credit', 'NOT_AVAILABLE'], ['Fiscal', 'NOT_AVAILABLE'], ['FX', 'NOT_AVAILABLE']]);
      assert.equal(await text(page, '[data-raw-axis=Labor] [data-raw-value]'), '4.6%');
      assert.equal(await page.locator('[data-raw-axis=FX] [data-na]').getAttribute('data-na'), 'PUBLIC_FX_EXCLUDED');
      await page.locator('[data-jump]').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.activeElement.id), 's-3-1', phase + ': the jump moves the focus to 3.1');
      // ---- keyboard, phone overflow with every details open, boundaries
      tag('keyboard');
      await keyboard(page, phase);
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      await boundaries(page, seen, phase + ' (details open)');
      // ---- route change keeps the RAM records and reads nothing; a reload drops them
      tag('route change');
      const at2 = s.requests.length;
      await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree]').waitFor();
      await page.evaluate(() => { location.hash = '#/macro'; }); await drawn(page);
      assert.equal(await count(page, '[data-mine-entry]'), 3, phase + ': RAM records are kept across routes of one page load');
      assert.equal(await text(page, '[data-center]'), '확장 초입', phase + ': the viewed cell is kept');
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at2), [], phase + ': a route change reads nothing new');
      const at3 = s.requests.length; await page.reload(); await drawn(page);
      assert.equal(await count(page, '[data-mine-empty]'), 1, phase + ': a reload drops the RAM records');
      assert.deepEqual(reads(at3), MACRO_READS, phase + ': a reload reads the same set once');
      await boundaries(page, seen, phase + ' (after reload)');
      await ctx.close(); pass++;
    }
    // ================================================================ partial failure (one file each time; the others stay)
    {
      phase = 'partial 1440';
      const { ctx, page, seen } = await context(1440);
      set({ ...FULL, 'macro-screen.json': { status: 500, body: 'x' } });
      await open(page); await drawn(page);
      assert.match(await text(page, '[data-block="4.1.4"] [data-na=READ_FAILED]'), /경고등·상태판 파일을 읽지 못했습니다 · 읽기 실패\(HTTP 500\)/);
      assert.equal(await count(page, '[data-block="4.1.4"] [data-mascot=alarm]'), 1);
      assert.equal(await count(page, '[data-macro-lights]'), 0, phase + ': no lights from a failed file');
      assert.equal(await count(page, '[data-events=economy] > li'), 10, phase + ': the evidence stays');
      assert.equal(await count(page, 'svg[data-ring]'), 1, phase + ': the ring stays');
      assert.equal(await page.locator('[data-file="macro-screen.json"]').getAttribute('data-file-state'), 'FAILED');
      assert.match(await text(page, '[data-facts]'), /경고등 · 파일을 읽지 못해 표시 안 함/);
      assert.equal(await count(page, '[data-block="4.6"] [data-na=READ_FAILED]'), 1);
      await boundaries(page, seen, phase + ' macro-screen 500', { errors: [/status of 500/] });
      seen.errors.length = 0;
      set({ ...FULL, 'macro-evidence.json': { status: 404, body: 'not found' } });
      await page.reload(); await drawn(page);
      assert.match(await text(page, '[data-block="4.1.3"] [data-na=NOT_PUBLISHED]'), /근거 파일이 아직 게시되지 않았습니다/);
      assert.equal(await page.locator('[data-macro-lights]').getAttribute('data-macro-lights-state'), 'WARNING', phase + ': the lights stay');
      assert.match(await text(page, '[data-facts]'), /근거 지표 · 파일을 읽지 못해 표시 안 함/);
      await boundaries(page, seen, phase + ' evidence 404');
      set({ ...FULL, 'sec-qgv2.json': { body: '{', type: 'application/json' } });
      await page.reload(); await drawn(page);
      assert.match(await text(page, '[data-block="4.3"] [data-na=READ_FAILED]'), /업종 그룹\(sec-qgv2\.json\) 파일을 읽지 못했습니다 · 읽기 실패/);
      assert.deepEqual(await page.locator('[data-mine-ring] option').evaluateAll((n) => n.map((o) => o.value)), ['economy', 'market']);
      assert.equal(await count(page, '[data-macro-lights]'), 1);
      await boundaries(page, seen, phase + ' sec-qgv2 invalid');
      await ctx.close(); pass++;
    }
    // ================================================================ empty public files (offline build), phone
    {
      phase = 'empty 390';
      const { ctx, page, seen } = await context(390);
      set({ 'macro-screen.json': { json: M.emptyScreen() }, 'macro-evidence.json': { json: M.emptyEvidence() }, 'sec-qgv2.json': { status: 404, body: 'not found' }, 'company-classification.json': { json: M.classification() } });
      const at = await open(page); await drawn(page);
      assert.equal(await page.locator('[data-macro-lights-verdict]').getAttribute('data-macro-lights-verdict'), 'NOT_AVAILABLE');
      assert.match(await text(page, '[data-macro-lights-summary]'), /매크로 확인 불가/);
      assert.deepEqual([...new Set(await page.locator('[data-macro-light]').evaluateAll((n) => n.map((x) => x.dataset.macroLightState)))], ['NO_DATA']);
      assert.equal(await count(page, '[data-not-collected]'), 1);
      assert.equal(await text(page, '[data-summary-counts]'), '유효 경고 0계열 · 유효 개선 0계열');
      assert.match(await text(page, '[data-no-events]'), /^실시간 기록 사건 없음/);
      assert.equal(await count(page, '[data-catalog-row][data-catalog-state=NOT_AVAILABLE]'), 13);
      assert.match(await text(page, '[data-block="4.3"] [data-na=NOT_PUBLISHED]'), /업종 그룹\(sec-qgv2\.json\) 파일이 아직 게시되지 않았습니다 · 아직 게시되지 않음\(HTTP 404\)/);
      assert.deepEqual(await page.locator('[data-mine-ring] option').evaluateAll((n) => n.map((o) => o.value)), ['economy', 'market']);
      assert.match(await text(page, '[data-na=NO_PUBLIC_OBSERVATION]'), /macro-screen\.json에 공개 관측이 없습니다 · 예시를 지어내지 않음/);
      assert.equal(await count(page, '[data-raw-axis][data-raw-state=NOT_AVAILABLE]'), 8);
      assert.match(await text(page, '[data-facts]'), /자료 있는 경고등 0\/5/);
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at), CORE.filter((n) => n !== 'dart-financials.json').sort());
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      await keyboard(page, phase);
      await boundaries(page, seen, phase);
      // A published sec-qgv2.json whose rows carry no industry_group (stubbed read result: see web_app_macro_fixture.js qgv).
      await page.evaluate(() => { const D = window.IS2.data; window.__realData = D;
        window.IS2.data = Object.freeze({ ...D, get: (n) => (n === 'sec-qgv2.json' ? { records: { 'NYSE:X': { industry_group: null } } } : D.get(n)),
          state: (n) => (n === 'sec-qgv2.json' ? Object.freeze({ state: 'OK', why: null, as_of: null, text: '' }) : D.state(n)) }); });
      await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree]').waitFor();
      await page.evaluate(() => { location.hash = '#/macro'; }); await drawn(page);
      assert.match(await text(page, '[data-block="4.3"] [data-state=empty][data-na=NO_GROUP_VALUES]'), /공개 파일에 업종 그룹 값이 없습니다/);
      assert.equal(await count(page, '[data-block="4.3"] [data-mascot=plain]'), 1, phase + ': the calm character for an empty list');
      await page.evaluate(() => { window.IS2.data = window.__realData; });
      await boundaries(page, seen, phase + ' no group values');
      await ctx.close(); pass++;
    }
    // ================================================================ error: the layer did not load (LOADER_FAILED), phone
    {
      phase = 'error 390';
      set(FULL);
      const { ctx, page, seen } = await context(390, { allow404: [...UNPUBLISHED, 'data.js'] });
      await page.route('**/data.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      const at = await open(page); await drawn(page);
      assert.equal(await count(page, '[data-block] [data-state=error][data-na=LOADER_FAILED]'), 6, phase + ': every data block shows the failure');
      assert.equal(await count(page, '[data-block] [data-mascot=alarm]'), 6);
      assert.match(await text(page, '[data-block="4.1.1"] [data-state=error]'), /층을 불러오지 못해 매크로 자료를 그리지 못했습니다/);
      assert.equal(await count(page, '[data-prep]'), 2, phase + ': the static 준비 중 sections stay');
      assert.equal(await count(page, '[data-load-failed]'), 1, phase + ': the shell notice');
      assert.deepEqual(reads(at), [], phase + ': nothing is read');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    console.log('web_app_macro_browser_test: PASS (' + pass + ' contexts: full 1440, full 390, partial failure, empty, error)');
  } catch (e) {
    console.error('web_app_macro_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
