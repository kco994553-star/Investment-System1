'use strict';
// New frontend · 2. 기술적 분석 (feature 3.1–3.4, route #/technical, screen-technical.js skeleton + screen-technical-live.js; boards
// Technical · MTechnical) in a real browser at 1440 and 390. Builds the development site (tools/web_app_test_site.js), then checks:
//  - Loading (split first paint): with screen-technical-live.js held back the skeleton shows the head, the company box and the
//    four section slots saying 불러오는 중, nothing else (no block, no private panel), and nothing is read; after the release the
//    blocks and the two private panels are drawn. A fresh open with no company reads no file at all.
//  - Verdict on hold: the band 지표 판정 보류 (NO_APPROVED_PRICE_SERIES, the IEX last-trade path is not chart OHLCV), six indicator
//    rows and five pattern rows each 판정 보류 with that code, no public chart, no price, no other verdict.
//  - Private layer: two IS2.parts.privatePanel (tech-kis-chart in 2-1, tech-kis-pattern in 2-2) in NOT_READY with the shared words,
//    empty bodies, nothing sent or stored.
//  - Company pick only through IS2.companies (the shared search part): the list is read on the first focus of the box (its two
//    files, once), a keyboard pick shows the company and sets IS2.selection; a listing-ended code (WBD) and a company outside the
//    device history path (FIX) ask for no price; the route parameter and the selection open the chosen company.
//  - No price request without a click: the 일봉 불러오기 button with a synthetic click (CLICK_REQUIRED) and with a real click but no
//    approved Worker address (ORIGIN_UNAPPROVED) sends nothing and shows the reason words, never a number.
//  - Notes and scenarios kept on this device: written only by a real click (a synthetic click stores nothing), the one key
//    investment.web.v1.chart-user-objects (chart-user-objects/1, ChartWorkbench's exact fields, price_basis RAW_CLOSE, author USER),
//    per company, newest first, delete, kept across routes and after a reload, invalid input refused.
//  - Degree: 스윙 (D) / 장기 (W) switches the pattern-rules/1 table, the minimum bars and the scenario horizon.
//  - Device chart after a sign-in (Google and Worker stand-ins, synthetic bars from tools/web_app_technical_fixture.js): one real
//    click asks the Worker once; the close line, optional SMA lines and the user's notes draw; prices show only as text inside
//    [data-ram-price] (assertRamOnly); verdicts stay on hold (PRICE_BASIS_CONTINUITY_UNCONFIRMED); a chart click fills the note
//    form with a bar date and a pointer price (never a supplier close); no sentinel in storage, requests or the console; a reload
//    drops the bars.
//  - Partial failure: the names table failing (the list without names: the route's TARGET id is not found and says which part is
//    missing; a ticker pick still works and the device path is off) and an unreadable stored notes value (never overwritten).
//  - Error: data.js answering 404 (the structure still draws, the company box and notes say why) and screen-technical-live.js
//    answering 404 (every slot shows the failure with the alarm character).
//  - Boundaries everywhere: same-origin requests only (stand-ins excepted), no console error but the intended ones, no CSP
//    violation, no [style], no horizontal overflow at 390, every control reachable by Tab with a visible focus ring, named buttons.
// Synthetic data only; no real price is requested or shown.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const site = require('./web_app_test_site');
const FX = require('./web_app_technical_fixture.js');

const NOW = '2026-10-14T21:00:00.000Z', TODAY = NOW.slice(0, 10);
const NOTE_KEY = 'investment.web.v1.chart-user-objects', ORIGIN_KEY = 'investment.web.v1.private-history-origin';
const NOTE_FIELDS = ['schema', 'id', 'kind', 'symbol', 'interval', 'price_basis', 'author', 'points', 'text', 'created_at', 'updated_at'];
const SCENARIO_FIELDS = ['schema', 'id', 'symbol', 'interval', 'price_basis', 'author', 'text', 'anchor_time', 'created_at', 'updated_at', 'horizon', 'direction', 'levels', 'condition', 'invalidation', 'invalidation_price'];
const PANELS = [['tech-kis-chart', '실가격 차트 · 지표 (KIS 통합 일봉)', '2-1'], ['tech-kis-pattern', '패턴 탐색 (KIS 분할 반영 계열, 탐색 전용)', '2-2']];
const INDICATORS = ['SMA', 'EMA', 'BOLL', 'RSI', 'MACD', 'ATR'], PATTERNS = ['SUPPORT_RESISTANCE_ZONE', 'BOX_BREAKOUT_UP', 'BOX_BREAKDOWN', 'DOUBLE_BOTTOM', 'DOUBLE_TOP'];
const HOLD = 'NO_APPROVED_PRICE_SERIES', CONT = 'PRICE_BASIS_CONTINUITY_UNCONFIRMED';
// Google and Worker stand-ins for the device chart (as web_app_macro_browser_test.js): the GIS script and the Worker's /history.
const TOKEN = ['memory', 'only', 'synthetic', 'technical', 'session'].join('-'), SCOPE = 'https://www.googleapis.com/auth/drive.file email';
const GIS_STYLE = 'https://accounts.google.com/gsi/style', GIS_CLIENT = 'https://accounts.google.com/gsi/client';
const WORKER = 'https://private-investment-history.kco994553.workers.dev';
const GIS_STUB = 'window.google={accounts:{oauth2:{initTokenClient:function(cfg){return{requestAccessToken:function(){cfg.callback({'
  + 'access_token:' + JSON.stringify(TOKEN) + ',expires_in:3600,token_type:"Bearer",scope:' + JSON.stringify(SCOPE) + '});}};},revoke:function(t,done){if(done)done({});}}}};';
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({});
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  async function context(width, { allow404 = [], init = null } = {}) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.clock.setFixedTime(new Date(NOW));
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    if (init) await ctx.addInitScript(init);
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  }
  const reads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => n.endsWith('.json')).sort();
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));
  const count = (page, sel) => page.locator(sel).count();
  const settle = (page, ms = 150) => page.evaluate((t) => new Promise((r) => setTimeout(r, t)), ms);
  const drawn = (page) => page.locator('[data-block="3.4"], [data-tech-slot] [data-state=error]').first().waitFor();
  async function open(page, hash = '#/technical', opts = {}) {
    const at = s.requests.length;
    await page.goto(s.base + hash, opts); await page.locator('main[data-route=technical]').waitFor();
    return at;
  }
  const stored = async (page) => { const st = await site.storage(page); return st.localItems[NOTE_KEY] ? JSON.parse(st.localItems[NOTE_KEY]) : null; };
  const synthetic = (page, sel) => page.evaluate((q) => document.querySelector(q).dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })), sel);
  async function pick(page, query, code) {
    await page.locator('#tech-q').focus(); await page.locator('#tech-q').fill(query);
    await page.locator('[data-search-list] [role=option][data-code="' + code + '"]').waitFor();
    for (let i = 0; i < 9; i++) { await page.keyboard.press('ArrowDown'); if (await page.locator('#tech-q').getAttribute('aria-activedescendant') && await page.locator('[role=option][aria-selected=true]').getAttribute('data-code') === code) break; }
    await page.keyboard.press('Enter');
    await page.locator('[data-tech-chosen][data-tech-chosen-state=CHOSEN][data-code="' + code + '"]').waitFor();
  }
  async function boundaries(page, seen, label, { errors = [], stored: keys = [], outside = [] } = {}) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside.filter((u) => !outside.some((o) => u.startsWith(o))), [], label + ': no request leaves the origin');
    assert.deepEqual(seen.errors.filter((e) => !errors.some((x) => x.test(e))), [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    assert.doesNotMatch(await page.locator('main').innerText(), /\d\s*%/, label + ': no percentage anywhere');
    const st = await site.storage(page);
    assert.deepEqual([Object.keys(st.localItems).sort(), st.session], [[...keys].sort(), 0], label + ': nothing stored on the device but the keys a click wrote');
  }
  async function panels(page, label) {
    const got = await page.locator('[data-private-panel]').evaluateAll((n) => n.map((x) => [x.dataset.privatePanel, x.dataset.privateState, x.querySelector('[data-private-status]').textContent,
      x.querySelector('.card-title').textContent, x.closest('[data-section]').dataset.section, x.querySelectorAll('[data-mascot]').length, x.querySelector('.private-body').textContent]));
    assert.deepEqual(got, PANELS.map(([id, title, sec]) => [id, 'NOT_READY', '비공개 기능 준비 중', '비공개 ' + title, sec, 0, '']), label + ': two private panels, NOT_READY');
  }
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
    const unlabelled = await page.evaluate(() => [...document.querySelectorAll('main input, main select')].filter((x) => !(x.labels && x.labels.length) && !x.getAttribute('aria-label')).length);
    assert.equal(unlabelled, 0, label + ': every field has a label');
    await page.evaluate(() => document.querySelectorAll('[data-k]').forEach((e) => { delete e.dataset.k; }));
  }
  try {
    // ================================================================ public screen, PC and phone
    for (const width of [1440, 390]) {
      const tag = (p) => { phase = width + ' ' + p; };
      const { ctx, page, seen } = await context(width);
      // ---- loading: the live file held back
      tag('loading');
      let release; const gate = new Promise((r) => { release = r; });
      await page.route('**/screen-technical-live.js', async (route) => { await gate; await route.continue(); });
      const at = await open(page, '#/technical', { waitUntil: 'domcontentloaded' });
      assert.equal(await page.locator('main h1').innerText(), '2. 기술적 분석');
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['2-1', '2-2', '2-3', '2-4'], phase + ': the skeleton draws the four sections');
      assert.equal(await count(page, '[data-tech-slot] [data-state=loading][role=status]'), 4, phase + ': four section slots say 불러오는 중');
      assert.match(await text(page, '[data-tech-chosen] [data-state=loading]'), /^불러오는 중/);
      assert.equal(await count(page, '#tech-q[role=combobox]'), 1, phase + ': the shared company box is there at first paint');
      assert.deepEqual([await count(page, '[data-block]'), await count(page, '[data-private-panel]'), await count(page, '[data-verdict]')], [0, 0, 0], phase + ': nothing but the skeleton before the live file');
      assert.deepEqual(reads(at), [], phase + ': nothing is read before the layer');
      release();
      await drawn(page);
      assert.equal(await page.locator('[data-menu-screen=technical]').getAttribute('data-screen-state'), 'ready');
      assert.equal(await count(page, '[data-tech-slot] [data-state=loading]'), 0, phase + ': the slots are filled');
      assert.deepEqual(await page.locator('[data-block]').evaluateAll((n) => n.map((x) => x.dataset.block)), ['3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.2.1', '3.2.2', '3.2.3', '3.2.4', '3.2.5', '3.3', '3.4']);
      await panels(page, phase);
      await settle(page);
      tag('reads');
      assert.deepEqual(reads(at), [], phase + ': a fresh open without a company reads no file');
      assert.equal(await page.locator('[data-tech-chosen]').getAttribute('data-tech-chosen-state'), 'NONE');
      // ---- verdict on hold
      tag('verdict');
      assert.match(await text(page, '[data-verdict-hold]'), new RegExp('^지표 판정 보류 · 승인·검증된 차트용 가격 계열이 아직 없습니다 \\(' + HOLD + '\\) · 지금의 IEX 마지막 체결가 경로는 차트용 연속·조정 OHLCV가 아닙니다$'));
      assert.equal(await page.locator('[data-verdict-hold]').getAttribute('role'), 'status');
      assert.deepEqual(await page.locator('[data-indicator]').evaluateAll((n) => n.map((x) => x.dataset.indicator)), INDICATORS);
      assert.deepEqual(await page.locator('[data-pattern]').evaluateAll((n) => n.map((x) => x.dataset.pattern)), PATTERNS);
      for (const sel of ['[data-indicator]', '[data-pattern]']) assert.deepEqual([...new Set(await page.locator(sel + ' [data-verdict]').evaluateAll((n) => n.map((x) => x.dataset.verdict + ' ' + x.dataset.na + ' ' + x.textContent)))], ['HOLD ' + HOLD + ' 판정 보류'], phase + ' ' + sel + ': each on hold with the reason');
      assert.equal(await count(page, '[data-verdict]:not([data-verdict=HOLD])'), 0, phase + ': no other verdict');
      assert.equal(await count(page, '[data-public-chart=NONE][data-na=' + HOLD + ']'), 1, phase + ': no public chart');
      assert.deepEqual([await count(page, '[data-ram-price]'), await count(page, '[data-verdict-device]'), await count(page, 'svg[data-tech-chart-svg]')], [0, 0, 0], phase + ': no price, no device chart');
      assert.match(await text(page, '[data-private-why=tech-kis-chart]'), /KIS 원주가\(MODP=0\)는 조정 완료 가격으로 보지 않음/);
      assert.match(await text(page, '[data-suitability]'), new RegExp('실가격 창 판정 불가 · ' + CONT));
      assert.equal(await count(page, '[data-block="3.1.3"] [data-prep]'), 1, phase + ': the official scenario is 준비 중');
      // ---- before a company: the button is off, notes say why
      tag('no company');
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), true);
      assert.equal(await text(page, '[data-tech-load-why]'), '기업을 고르면 누를 수 있습니다');
      assert.equal(await count(page, '[data-notes] [data-state=empty][data-na=NO_COMPANY]'), 1);
      assert.match(await text(page, '[data-scenario-form]'), /기업을 고르면/);
      // ---- degree (3.2.2)
      tag('degree');
      const tf = () => page.locator('[data-degree-tf]').evaluateAll((n) => n.map((x) => [x.dataset.degreeTf, x.getAttribute('aria-pressed')]));
      assert.deepEqual(await tf(), [['D', 'true'], ['W', 'false']]);
      assert.equal(await page.locator('[data-param-tf]').getAttribute('data-param-tf'), 'D');
      assert.deepEqual(await page.locator('[data-param=PIVOT_K] td').allInnerTexts(), ['3', '2 · 3 · 5']);
      assert.match(await text(page, '[data-min-bar=PIVOT]'), /최소 7봉/);
      await page.locator('[data-degree-tf=W]').focus(); await page.keyboard.press('Enter');
      assert.deepEqual(await tf(), [['D', 'false'], ['W', 'true']], phase + ': the keyboard switches the degree');
      assert.equal(await page.evaluate(() => document.activeElement.dataset.degreeTf), 'W', phase + ': the focus stays on the chip');
      assert.deepEqual(await page.locator('[data-param=PIVOT_K] td').allInnerTexts(), ['2', '1 · 2 · 3']);
      assert.deepEqual(await page.locator('[data-param=DB_SEP_MAX] td').allInnerTexts(), ['52', '— · 따로 고르지 않음']);
      assert.match(await text(page, '[data-min-bar=PIVOT]'), /최소 5봉/);
      assert.match(await text(page, '[data-min-bars-tf]'), /장기 · 주봉 기준 \(W\)/);
      await page.locator('[data-degree-tf=D]').click();
      // ---- tree (3.4)
      tag('tree');
      assert.deepEqual(await page.locator('[data-tech-tree] > li').evaluateAll((n) => n.map((x) => x.dataset.treeNode)), ['입력', '3.1', '3.2', '3.3']);
      assert.equal(await count(page, '[data-tree-node^="3.2."]'), 5);
      assert.match(await text(page, '[data-tree-example]'), new RegExp('실가격 예시: — · .*' + HOLD));
      assert.match(await text(page, '[data-tree-private]'), /비공개 기능 준비 중$/);
      await page.locator('[data-jump="2-2"]').click();
      assert.equal(await page.evaluate(() => document.activeElement.id), 's-2-2', phase + ': the jump focuses the section heading');
      // ---- company pick: the list read on the first focus, a keyboard pick
      tag('pick');
      const atPick = s.requests.length;
      await pick(page, 'nvda', 'NASDAQ:NVDA');
      assert.deepEqual(reads(atPick), ['company-names-ko.json', 'universe-codes.json'], phase + ': the company list read once, on demand');
      assert.match(await text(page, '[data-tech-company]'), /^NVDA · NVIDIA CORP$/);
      assert.match(await text(page, '[data-tech-chosen]'), /NASDAQ:NVDA · Universe504/);
      assert.equal(await page.evaluate(() => window.IS2.selection.get().id), 'nvda', phase + ': the pick is the selection (RAM)');
      assert.equal(await page.locator('#tech-q').inputValue(), '');
      // ---- no price request without a click
      tag('no request');
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), false);
      assert.equal(await page.locator('[data-tech-load-why]').isHidden(), true);
      const atQ = s.requests.length, outQ = seen.outside.length;
      await synthetic(page, '[data-tech-load]');
      await page.locator('[data-tech-load-status] [data-na=CLICK_REQUIRED]').waitFor();
      assert.match(await text(page, '[data-tech-load-status]'), /^— · 버튼을 직접 눌러 주세요 · CLICK_REQUIRED$/);
      await page.locator('[data-tech-load]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-tech-load-status] [data-na=ORIGIN_UNAPPROVED]').waitFor();
      assert.match(await text(page, '[data-tech-load-status]'), /^— · Worker 주소 설정 필요 · 승인된 주소가 이 기기에 없습니다 · ORIGIN_UNAPPROVED$/, phase + ': the reason words, never a code alone');
      assert.equal(await page.locator('[data-tech-chart]').getAttribute('data-state'), 'NA');
      assert.deepEqual([s.requests.slice(atQ).map((r) => r.name), seen.outside.slice(outQ)], [[], []], phase + ': neither click requested anything');
      assert.deepEqual([await count(page, '[data-ram-price]'), await count(page, '[data-verdict-device]')], [0, 0], phase + ': no number, verdicts unchanged');
      // ---- notes kept on this device (3.3)
      tag('notes');
      assert.equal(await count(page, '[data-notes] [data-na=NO_NOTE]'), 1);
      await page.locator('[data-note-kind]').first().selectOption('HLINE');
      await page.locator('[data-note-date]').fill('2026-10-01'); await page.locator('[data-note-price]').fill('214.5'); await page.locator('[data-note-text]').fill('지지선 후보');
      await synthetic(page, '[data-note-save]');
      assert.equal(await text(page, '[data-note-status]'), '저장하지 않음 · 버튼을 직접 눌러 주세요');
      assert.equal(await stored(page), null, phase + ': a synthetic click stores nothing');
      await page.locator('[data-note-save]').click();
      assert.equal(await text(page, '[data-note-status]'), '노트를 이 기기에 저장했습니다 · 계정 단계 없음');
      await page.locator('select[data-note-kind]').selectOption('MEMO'); await page.locator('[data-note-price]').fill('199'); await page.locator('[data-note-text]').fill('메모 하나');
      await page.locator('[data-note-save]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-note-items] > li:nth-child(2)').waitFor();
      assert.deepEqual(await page.locator('[data-note-items] > li').evaluateAll((n) => n.map((x) => x.dataset.noteKind)), ['MEMO', 'HLINE'], phase + ': newest first');
      assert.match(await text(page, '[data-note-items] > li[data-note-kind=HLINE]'), /^사용자 작성 수평선 · 일봉 · 2026-10-01 · 가격 214\.5 · 지지선 후보 · 적은 날 2026-10-14 지우기$/);
      assert.equal(await page.locator('[data-note-counts]').getAttribute('data-note-counts'), '2/2');
      await page.locator('[data-note-price]').fill(''); await page.locator('[data-note-save]').click();
      assert.equal(await text(page, '[data-note-status]'), '저장하지 않음 · 날짜와 0보다 큰 가격을 적어 주세요');
      let raw = await stored(page);
      assert.equal(raw.schema, 'chart-user-objects/1'); assert.equal(raw.items.length, 2, phase + ': refused input stores nothing');
      for (const o of raw.items) {
        assert.deepEqual(Object.keys(o).sort(), [...NOTE_FIELDS].sort(), phase + ': ChartWorkbench\'s exact note fields');
        assert.deepEqual([o.schema, o.symbol, o.interval, o.price_basis, o.author], ['chart-annotation/1', 'NVDA', 'D', 'RAW_CLOSE', 'USER']);
      }
      assert.deepEqual(raw.items.map((o) => [o.kind, o.points]), [['HLINE', [{ time: '2026-10-01', price: 214.5 }]], ['MEMO', [{ time: '2026-10-01', price: 199 }]]], phase + ': the date stays in the form for the next note');
      await page.locator('[data-note-items] > li[data-note-kind=MEMO] [data-note-delete]').click();
      assert.equal(await text(page, '[data-note-status]'), '지웠습니다 · 이 기기에서만');
      assert.equal(await count(page, '[data-note-items] > li'), 1); assert.equal((await stored(page)).items.length, 1);
      // ---- scenarios kept on this device (3.1.3)
      tag('scenario');
      await page.locator('[data-sc-label="1"]').fill('1차 저항'); await page.locator('[data-sc-price="1"]').fill('230');
      await page.locator('[data-sc-price="2"]').fill('-5'); await page.locator('[data-scenario-save]').click();
      assert.equal(await text(page, '[data-scenario-status]'), '저장하지 않음 · 핵심 가격을 하나 이상 0보다 큰 수로 적어 주세요');
      await page.locator('[data-sc-price="2"]').fill(''); await page.locator('[data-sc-cond]').fill('230 위 종가'); await page.locator('[data-sc-inv]').fill('200 아래'); await page.locator('[data-sc-inv-price]').fill('200');
      await synthetic(page, '[data-scenario-save]');
      assert.equal(await text(page, '[data-scenario-status]'), '저장하지 않음 · 버튼을 직접 눌러 주세요');
      await page.locator('[data-scenario-save]').click();
      await page.locator('[data-scenarios] > li').waitFor();
      assert.match(await text(page, '[data-scenarios] > li'), /^사용자 작성 ↑ 상승 · 스윙 · 기준 2026-10-14 · 핵심 가격 1차 저항 230 · 조건: 230 위 종가 · 무효화: 200 아래 \(200\) 지우기$/);
      raw = await stored(page);
      const sc = raw.items.find((o) => o.schema === 'chart-scenario/1');
      assert.deepEqual(Object.keys(sc).sort(), [...SCENARIO_FIELDS].sort());
      assert.deepEqual([sc.symbol, sc.direction, sc.horizon, sc.levels, sc.invalidation_price], ['NVDA', 'UP', 'swing', [{ label: '1차 저항', price: 230 }], 200]);
      assert.equal(await page.locator('[data-sc-label="1"]').inputValue(), '', phase + ': the form is cleared after a save');
      // ---- kept across routes and after a reload; per company
      tag('kept');
      await page.evaluate(() => { location.hash = '#/tree'; }); await page.locator('main[data-route=tree]').waitFor();
      await page.evaluate(() => { location.hash = '#/technical'; }); await page.locator('[data-tech-chosen-state=CHOSEN][data-code="NASDAQ:NVDA"]').waitFor();
      assert.deepEqual([await count(page, '[data-note-items] > li'), await count(page, '[data-scenarios] > li')], [1, 1], phase + ': the selection reopens the company');
      await page.reload(); await drawn(page);
      assert.equal(await page.locator('[data-tech-chosen]').getAttribute('data-tech-chosen-state'), 'NONE', phase + ': the selection is RAM only');
      await page.evaluate(() => { location.hash = '#/technical/NASDAQ%3ANVDA'; }); await page.locator('[data-tech-chosen-state=CHOSEN][data-code="NASDAQ:NVDA"]').waitFor();
      assert.deepEqual([await count(page, '[data-note-items] > li'), await count(page, '[data-scenarios] > li')], [1, 1], phase + ': notes and scenarios survive a reload');
      await pick(page, 'AMD', 'NASDAQ:AMD');
      assert.deepEqual([await count(page, '[data-notes] [data-na=NO_NOTE]'), await count(page, '[data-scenario-list] [data-na=NO_SCENARIO]')], [1, 1], phase + ': another company has its own notes');
      assert.equal(await page.evaluate(() => location.hash), '#/technical/amd', phase + ': a pick on a parameter route keeps the address in step');
      // ---- listing ended, and outside the device history path
      tag('wbd / fix');
      await pick(page, 'WBD', 'NASDAQ:WBD');
      assert.equal(await page.locator('[data-tech-chosen] [data-listing-ended]').getAttribute('data-listing-ended'), '2026-10-06');
      assert.match(await text(page, '[data-tech-chosen] [data-listing-ended]'), /^상장 종료 2026-10-06 · 점수 없음 · 일봉을 묻지 않습니다$/);
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), true); assert.equal(await text(page, '[data-tech-load-why]'), '상장 종료 기업은 일봉을 묻지 않습니다');
      await pick(page, 'NYSE:FIX', 'NYSE:FIX');
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), true);
      assert.match(await text(page, '[data-tech-load-why]'), /^이 기업은 기기 일봉 경로에 없습니다 · 지원: TARGET 19개 기업 · 공개 화면은 그대로$/);
      await panels(page, phase + ' after picks');
      await keyboard(page, phase);
      await boundaries(page, seen, phase, { stored: [NOTE_KEY] });
      await ctx.close(); pass++;
    }
    // ================================================================ device chart after a sign-in (Google and Worker stand-ins), phone
    {
      phase = 'device chart 390';
      const { ctx, page, seen } = await context(390);
      const log = [], unexpected = [], worker = [];
      await ctx.route('**/*', async (route) => {
        const req = route.request(), url = new URL(req.url());
        log.push(req.method() + ' ' + req.url() + ' ' + (req.postData() || ''));
        if (url.origin === s.origin) { await route.continue(); return; }
        if (req.url() === GIS_STYLE) { await route.fulfill({ status: 200, contentType: 'text/css', body: '.g_id_signin{font-family:sans-serif}' }); return; }
        if (req.url() === GIS_CLIENT) { await route.fulfill({ status: 200, contentType: 'application/javascript', body: GIS_STUB }); return; }
        if (url.origin === WORKER && url.pathname === '/history' && req.headers().authorization === 'Bearer ' + TOKEN) {
          worker.push(url.search);
          await route.fulfill({ status: 200, contentType: 'application/json', headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify(FX.history(url.searchParams.get('symbol'), url.searchParams.get('range'), NOW)) }); return;
        }
        unexpected.push(req.method() + ' ' + url.origin + url.pathname); await route.abort();
      });
      await open(page, '#/technical/NASDAQ%3ANVDA'); await drawn(page); await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor();
      // Test-only buttons (not the site; no style): each passes its real click event to one layer action.
      await page.evaluate((origin) => {
        const I = window.IS2, out = window.__out = {}, bar = document.createElement('div'); bar.dataset.testActions = '';
        const acts = { origin: (e) => I.store.workerOrigin.set(e, origin), prepare: (e) => I.prices.prepare(e), login: (e) => I.prices.login(e) };
        for (const [name, fn] of Object.entries(acts)) { const b = document.createElement('button'); b.type = 'button'; b.dataset.testAction = name; b.textContent = 'test ' + name;
          b.addEventListener('click', (e) => { let p; try { p = Promise.resolve(fn(e)); } catch (err) { p = Promise.reject(err); } out[name] = p.then(() => 'OK', (err) => String(err && err.message)); }); bar.appendChild(b); }
        document.body.prepend(bar);
      }, WORKER);
      const testClick = async (name) => { await page.locator('[data-test-action="' + name + '"]').click(); return page.evaluate((n) => window.__out[n], name); };
      // Signed in but no Worker address: the reason, no request.
      assert.equal(await testClick('prepare'), 'OK'); assert.equal(await testClick('login'), 'OK');
      await page.locator('[data-tech-load]').click(); await page.locator('[data-tech-load-status] [data-na=ORIGIN_UNAPPROVED]').waitFor();
      assert.deepEqual(worker, [], phase + ': no Worker request without the approved address');
      assert.equal(await testClick('origin'), 'OK');
      assert.deepEqual(worker, [], phase + ': still no Worker request before the button');
      // One real click: one Worker request, the chart, prices only inside [data-ram-price], verdicts on hold.
      await page.locator('[data-tech-load]').focus(); await page.keyboard.press('Enter');
      await page.locator('[data-tech-chart][data-state=OK] svg[data-tech-chart-svg=NVDA]').waitFor({ timeout: 20000 });
      assert.deepEqual(worker, ['?symbol=NVDA&range=1y'], phase + ': exactly one Worker request for the click');
      const bars = FX.history('NVDA', '1y', NOW).bars, closes = bars.map((b) => b.close), fmt = (v) => v.toLocaleString('ko-KR', { maximumSignificantDigits: 6 });
      assert.ok(await count(page, 'svg[data-tech-chart-svg] [data-close-line]') >= 1, phase + ': the close line');
      assert.deepEqual(await page.locator('[data-ram-price]').allTextContents(), [fmt(Math.min(...closes)), fmt(Math.max(...closes)), fmt(closes.at(-1)) + ' USD'], phase + ': the scale and last close as RAM text');
      assert.match(await text(page, '[data-tech-chart-range]'), /^세로 [\d.,]+ ~ [\d.,]+ USD · 가로 \d{4}-\d{2}-\d{2} ~ 2026-10-14$/);
      assert.match(await text(page, '[data-tech-chart-facts]'), new RegExp('Yahoo Finance\\(비공식\\) · NVDA · SYNTHETIC[\\s\\S]*1년 · ' + bars.length + '봉[\\s\\S]*장중 또는 미확정[\\s\\S]*' + CONT));
      assert.equal(await text(page, '[data-tech-load-status]'), '이 기기 일봉을 이 화면에만 보였습니다 · 저장·전송 안 함 · 새로고침하면 사라짐');
      assert.equal(await count(page, '[data-verdict-hold] [data-verdict-device=' + CONT + ']'), 1, phase + ': the band says why device bars are chart only');
      assert.deepEqual([...new Set(await page.locator('[data-indicator] [data-verdict]').evaluateAll((n) => n.map((x) => x.dataset.na)))], [HOLD], phase + ': indicator verdicts still on hold');
      assert.doesNotMatch(await page.locator('svg[data-tech-chart-svg]').getAttribute('aria-label'), /\d+\.\d/, phase + ': no price in the chart label');
      // SMA lines (display only): SMA 20 on by default; SMA 60 on a toggle, the focus stays.
      assert.deepEqual(await page.locator('[data-sma-line]').evaluateAll((n) => [...new Set(n.map((x) => x.dataset.smaLine))]), ['20']);
      await page.locator('[data-tech-sma="60"]').focus(); await page.keyboard.press('Space');
      assert.deepEqual(await page.locator('[data-sma-line]').evaluateAll((n) => [...new Set(n.map((x) => x.dataset.smaLine))]), ['20', '60']);
      assert.equal(await page.evaluate(() => document.activeElement.dataset.techSma), '60', phase + ': the focus stays on the toggle');
      // Notes on the chart: a level inside the range draws; a memo on a day without a bar is listed only.
      await page.locator('select[data-note-kind]').selectOption('HLINE'); await page.locator('[data-note-price]').fill('214.5'); await page.locator('[data-note-save]').click();
      await page.locator('svg[data-tech-chart-svg] [data-note-mark][data-note-kind=HLINE]').waitFor({ state: 'attached' });
      await page.locator('select[data-note-kind]').selectOption('MEMO'); await page.locator('[data-note-date]').fill('2026-10-11'); await page.locator('[data-note-price]').fill('210'); await page.locator('[data-note-save]').click();
      await page.locator('[data-note-items] > li:nth-child(2)').waitFor();
      assert.equal(await count(page, 'svg [data-note-mark][data-note-kind=MEMO]'), 0, phase + ': a memo on a day without a bar stays off the chart');
      // A chart click fills the form: a bar date and a pointer price (six significant digits), never a supplier close.
      const chart = page.locator('svg[data-tech-chart-svg]'); await chart.scrollIntoViewIfNeeded();
      const box = await chart.boundingBox();
      await chart.click({ position: { x: box.width * 0.5, y: box.height * 0.45 } });
      assert.match(await text(page, '[data-note-status]'), /^차트에서 고른 자리를 양식에 채웠습니다 · \d{4}-\d{2}-\d{2} · 저장은 노트 저장 단추로$/);
      const pickedDate = await page.locator('[data-note-date]').inputValue(), pickedPrice = Number(await page.locator('[data-note-price]').inputValue());
      const dates = bars.map((b) => new Date(b.timestamp * 1000).toISOString().slice(0, 10));
      assert.ok(dates.includes(pickedDate), phase + ': a bar date');
      assert.ok(pickedPrice > Math.min(...closes) && pickedPrice < Math.max(...closes) && String(pickedPrice).replace('.', '').length <= 6, phase + ': a pointer price inside the range: ' + pickedPrice);
      assert.ok(!String(pickedPrice).includes(FX.SENTINEL), phase + ': never a supplier close');
      await page.locator('[data-note-save]').click();
      await page.locator('svg [data-note-mark][data-note-kind=MEMO]').waitFor({ state: 'attached' });
      await site.assertRamOnly(page, [FX.SENTINEL], phase);
      const st = await site.storage(page);
      assert.deepEqual(Object.keys(st.localItems).sort(), [NOTE_KEY, ORIGIN_KEY].sort(), phase + ': only the notes and the test click\'s Worker setting');
      assert.equal(st.session, 0);
      assert.equal(JSON.parse(st.localItems[NOTE_KEY]).items.length, 3);
      assert.deepEqual(site.leaks([...Object.values(st.localItems), ...log, ...seen.errors], [FX.SENTINEL]), [], phase + ': no bar value in storage, requests or the console');
      // Another range: one more request on its own click.
      await page.locator('[data-tech-range]').selectOption('3mo'); await page.locator('[data-tech-load]').click();
      await page.locator('[data-tech-chart-facts]:has-text("3개월")').waitFor();
      assert.deepEqual(worker, ['?symbol=NVDA&range=1y', '?symbol=NVDA&range=3mo']);
      assert.deepEqual(unexpected, [], phase + ': no unexpected outside request');
      assert.deepEqual([...new Set(seen.outside.map((u) => { const x = new URL(u); return x.origin + x.pathname; }))].filter((u) => ![GIS_CLIENT, GIS_STYLE, WORKER + '/history'].includes(u)), [], phase + ': only the stand-ins leave the origin');
      assert.deepEqual(seen.errors, [], phase + ': no console error');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), phase + ': no horizontal overflow with the chart');
      assert.equal(await count(page, '[style]'), 0);
      // A reload drops the bars; nothing is asked again.
      await page.reload(); await drawn(page); await page.locator('[data-tech-chosen-state=CHOSEN]').waitFor(); await settle(page, 300);
      assert.deepEqual([await page.locator('[data-tech-chart]').getAttribute('data-state'), await count(page, '[data-ram-price]'), worker.length], ['BEFORE', 0, 2], phase + ': a reload drops the bars');
      assert.equal(await count(page, '[data-note-items] > li'), 3, phase + ': the notes stay');
      await ctx.close(); pass++;
    }
    // ================================================================ partial failure: names table 500, unreadable stored notes
    {
      phase = 'partial 1440';
      s.fixture('company-names-ko.json', { status: 500, body: 'fail' });
      const { ctx, page, seen } = await context(1440, { init: () => { if (!localStorage.getItem('investment.web.v1.chart-user-objects')) localStorage.setItem('investment.web.v1.chart-user-objects', '{broken'); } });
      await open(page, '#/technical/nvda'); await drawn(page);
      await page.locator('[data-tech-chosen-state=PARTIAL]').waitFor();
      assert.match(await text(page, '[data-tech-chosen]'), /기업 목록 일부를 읽지 못해 고른 기업\(nvda\)을 찾지 못했습니다[\s\S]*읽지 못한 것: 영문 회사명 표/);
      assert.equal(await count(page, '[data-indicator] [data-verdict=HOLD]'), 6, phase + ': the structure stays');
      await pick(page, 'NVDA', 'NASDAQ:NVDA');
      assert.match(await text(page, '[data-index-missing]'), /일부 목록을 읽지 못했습니다/);
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), true, phase + ': without the names table there is no TARGET link, so no device path');
      assert.equal(await count(page, '[data-notes] [data-na=CHART_NOTES_STORAGE_INVALID]'), 1, phase + ': unreadable notes say so');
      assert.equal(await count(page, '[data-scenario-list] [data-na=CHART_NOTES_STORAGE_INVALID]'), 1);
      assert.equal(await count(page, '[data-note-save], [data-scenario-save]'), 0, phase + ': no save offered over an unreadable value');
      await boundaries(page, seen, phase, { stored: [NOTE_KEY], errors: [/status of 500/] });
      assert.equal((await site.storage(page)).localItems[NOTE_KEY], '{broken', phase + ': never overwritten');
      s.fixture('company-names-ko.json', null);
      await ctx.close(); pass++;
    }
    // ================================================================ errors: data.js 404 (layer failed), screen-technical-live.js 404
    {
      phase = 'layer failed 390';
      const { ctx, page, seen } = await context(390, { allow404: ['data.js'] });
      await page.route('**/data.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      await open(page); await drawn(page); await page.locator('[data-load-failed]').waitFor();
      assert.equal(await page.locator('[data-menu-screen=technical]').getAttribute('data-screen-state'), 'partial');
      assert.equal(await page.locator('[data-tech-chosen]').getAttribute('data-tech-chosen-state'), 'LOADER_FAILED');
      assert.equal(await page.locator('#tech-q').isDisabled(), true);
      assert.equal(await count(page, '[data-notes] [data-na=LOADER_FAILED]'), 1);
      assert.equal(await count(page, '[data-indicator] [data-verdict=HOLD]'), 6, phase + ': the structure still draws');
      assert.equal(await page.locator('[data-tech-load]').isDisabled(), true);
      await panels(page, phase);
      await boundaries(page, seen, phase, { errors: [/status of 404/] });
      await ctx.close();
      phase = 'live file 404 390';
      const c2 = await context(390, { allow404: ['screen-technical-live.js'] });
      await c2.page.route('**/screen-technical-live.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      await open(c2.page); await drawn(c2.page);
      assert.equal(await count(c2.page, '[data-tech-slot] [data-state=error][data-na=LOADER_FAILED] [data-mascot=alarm]'), 4, phase + ': every slot shows the failure');
      assert.equal(await count(c2.page, '[data-tech-slot] [role=alert]'), 1);
      assert.deepEqual([await count(c2.page, '[data-block]'), await c2.page.locator('[data-menu-screen=technical]').getAttribute('data-screen-state')], [0, 'error']);
      await boundaries(c2.page, c2.seen, phase, { errors: [/status of 404/] });
      await c2.ctx.close(); pass++;
    }
    console.log('web_app_technical_browser_test: PASS (' + pass + ' groups: public 1440, public 390, device chart, partial failure, errors)');
  } catch (e) {
    console.error('web_app_technical_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
