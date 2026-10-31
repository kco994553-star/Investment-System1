'use strict';
// New frontend · n+1. Lab (feature 9.1 백테스트 · 9.2 전진검증, route #/lab, screen-lab.js skeleton + screen-lab-live.js; boards Lab ·
// MLab) in a real browser at 1440 and 390. Builds the development site (tools/web_app_test_site.js), serves a synthetic price-free
// forward ledger (tools/web_app_lab_fixture.js) and puts synthetic IS2.lab.source() answers in place of the real one (which today
// answers NONE / PRIVATE_NOT_READY and requests nothing), built from tools/lab_backtest_fixture.js. Checks in Chromium:
//  - Loading (split first paint): with a layer file held back both section slots say 불러오는 중 and nothing else is drawn; after
//    the release 9.1's public part and both private panels are drawn at once while 9.2 says 불러오는 중 · 전진검증 원장 until the
//    ledger answers. A fresh open reads exactly forward-validation-ledger.json; a route change reads nothing new.
//  - 9.1 public (the real source, NONE): the owner's words 연구 결과가 아직 없습니다, the readiness checklist (9 items, their states),
//    9.1.1–9.1.6, what a result will show and the refusal rule; no percentage; the two private panels NOT_READY (비공개 기능 준비
//    중), empty bodies. The public text of both sections is the same in every Lab state below (a private answer never changes it).
//  - 9.1 private, DEV_SYSTEM §4 with fixtures: normal (two runs as tabs, the owner's status lines, facts, seven metrics with the
//    null sharpe as – and its reason, curve, limitations), empty list, 404 (ERROR LAB_RESULT_NOT_FOUND), schema mismatch, required
//    field missing (top and run), null (every metric – and its reason, no curve, no percentage), SYNTHETIC, MIXED, NOT_VALIDATED,
//    PIT not met, limitations shown, login needed (비공개 연구 결과 · 로그인 필요, never a signed-in word), a source that fails
//    (LAB_SOURCE_FAILED) and one that never answers (the panel stays NOT_READY, the public part is drawn).
//  - Curve: months in the file's order (value table = the file, x strictly increasing), both lines start on the 100 line, the end
//    value consistent with total_return and with the metric shown (as text only: the chart's label and data attributes carry no
//    result value), and the validator's refusals drawn as ERROR with nothing of
//    the file (months not ascending, start not 100, total_return off the curve, a non-finite number, a zero and a negative value).
//  - 9.2: facts, the daily table (10 rows newest first, the rest under a fold), evaluation words (PRIMARY with basis counts,
//    PREPARATORY, COMPARISON, input missing), three calc-version segments, the latest 7 session days with the PARTIAL day and the
//    missing day, 9.2.2 이후 성과 미산출, the v3 준비 중 line without a v3 number.
//  - Partial failure and empty: ledger HTTP 500 / 404 / invalid → 9.2 says it (읽지 못했습니다 / 아직 게시되지 않았습니다) and 9.1
//    stays; a schema-1 ledger (v1 only, no basis); an empty ledger (ACTIVE, 0 rows) and one before its start date.
//  - Error: data.js answering 404 (LOADER_FAILED) and screen-lab-live.js answering 404: both slots show the failure with the alarm
//    character, the shell notice, nothing read, no uncaught error.
//  - Boundaries everywhere: same-origin requests only and no request with lab / backtest in its name (no private request, no public
//    Lab file), no console error but the intended ones, no CSP violation, no [style], nothing stored, no horizontal overflow at 390
//    (folds open too), every control reachable by Tab with a visible focus ring, named buttons, the run tabs by arrows, Home, End.
// Synthetic data only; no real result, price or ledger value.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const site = require('./web_app_test_site');
const F = require('./lab_backtest_fixture.js');
const X = require('./web_app_lab_fixture.js');

const LEDGER = 'forward-validation-ledger.json';
// Live-only files (absent from the offline build) a screen of this page may ask for; their 404 is the NOT_PUBLISHED state.
const UNPUBLISHED = ['sec-public-inputs.json', 'sec-qgv2.json', 'dart-financials.json', 'qgv-official.json', 'qgv-official-status.json', LEDGER];
const FULL = { [LEDGER]: { json: X.ledgerV2() } };
const S = X.sources(F);
const PANELS = [['lab-backtest', '연구 결과', 'lab-1'], ['lab-forward-kis', '이후 수익률 (KIS)', 'lab-2']];
const CHECK_STATES = ['checked', 'pending', 'decide', 'checked', 'checked', 'pending', 'decide', 'decide', 'na'];
const STATE_WORDS = { checked: '✓ 확인됨', pending: '준비 중', decide: '결정 대기', na: '미산출', rule: '조건', private: '비공개 칸' };
const pct = (v) => (v * 100).toFixed(2) + '%';
let phase = 'START', pass = 0;

(async () => {
  const s = await site.start({ fixtures: FULL });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  async function context(width, { allow404 = UNPUBLISHED } = {}) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 } });
    await ctx.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
    const page = await ctx.newPage(), seen = site.watch(page, s.origin, { allow404 });
    return { ctx, page, seen };
  }
  const reads = (from) => s.requests.slice(from).map((r) => r.name).filter((n) => n.endsWith('.json')).sort();
  const text = (page, sel) => page.locator(sel).first().evaluate((e) => (e instanceof HTMLElement ? e.innerText : e.textContent));
  const count = (page, sel) => page.locator(sel).count();
  const drawn = (page) => page.locator('[data-block="9.2.1"] [data-forward-facts], [data-block="9.2.1"] [data-state=error], [data-lab-slot] [data-state=error]').first().waitFor();
  async function open(page, hash = '#/lab', opts = {}) {
    const at = s.requests.length;
    await page.goto(s.base + hash, opts); await page.locator('main[data-route=lab]').waitFor();
    return at;
  }
  // A route change (the screen renders again and asks IS2.lab.source() again).
  async function reopen(page) {
    await page.evaluate(() => { location.hash = '#/portfolio'; }); await page.locator('main[data-route=portfolio]').waitFor();
    await page.evaluate(() => { location.hash = '#/lab'; }); await page.locator('main[data-route=lab]').waitFor(); await drawn(page);
  }
  // IS2.lab with a synthetic source() (the rest of the real reader kept: validate, status, nullText, TEXT, METRICS).
  async function source(page, src) {
    await page.evaluate((x) => {
      const I = window.IS2, real = window.__labReal || (window.__labReal = I.lab);
      const answer = x === 'reject' ? () => Promise.reject(new Error('synthetic failure')) : x === 'pending' ? () => new Promise(() => {}) : x === 'real' ? real.source : () => Promise.resolve(x);
      I.lab = Object.freeze({ ...real, source: answer });
    }, src);
  }
  const panel = (page, id) => page.locator('[data-private-panel="' + id + '"]').evaluate((x) => ({ state: x.dataset.privateState, status: x.querySelector('[data-private-status]').textContent,
    hidden: x.querySelector('[data-private-status]').hidden, mascot: x.querySelectorAll('.private-art [data-mascot]').length, body: x.querySelector('.private-body').textContent }));
  const waitPanel = (page, state) => page.locator('[data-private-panel="lab-backtest"][data-private-state="' + state + '"]').waitFor();
  // The public text of both sections without the private panels (it must not change with any private answer).
  const publicText = (page) => page.evaluate(() => ['lab-1', 'lab-2'].map((id) => { const c = document.querySelector('[data-lab-slot="' + id + '"]').cloneNode(true);
    c.querySelectorAll('[data-private-panel]').forEach((p) => p.remove()); return c.textContent; }));
  async function boundaries(page, seen, label, { errors = [] } = {}) {
    assert.equal(await count(page, '[style]'), 0, label + ': no style attribute');
    assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
    assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
    assert.deepEqual(seen.requests.filter((u) => /lab|backtest/i.test(new URL(u).pathname.replace(/screen-lab(-live)?\.js$|\/lab\.js$/, ''))), [], label + ': no private or Lab result request');
    assert.deepEqual(seen.errors.filter((e) => !errors.some((x) => x.test(e))), [], label + ': no console or page error');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
    assert.doesNotMatch(await page.locator('main').innerText(), /로그인됨|로그인 완료|signed in/i, label + ': never a signed-in word');
    const st = await site.storage(page);
    assert.deepEqual([st.local, st.session, st.idb], [0, 0, 0], label + ': nothing stored on the device');
  }
  async function panels(page, label, first = 'NOT_READY') {
    const got = await page.locator('[data-private-panel]').evaluateAll((n) => n.map((x) => [x.dataset.privatePanel, x.dataset.privateState, x.querySelector('.card-title').textContent, x.closest('[data-section]').dataset.section]));
    assert.deepEqual(got, PANELS.map(([id, title, sec], i) => [id, i ? 'NOT_READY' : first, '비공개 ' + title, sec]), label + ': two private panels');
  }
  // Every focusable control of main is reached by Tab (a roving tablist: the selected tab), with a visible focus ring.
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
    assert.ok(lists.every(([named, one]) => named && one === 1), label + ': named tablists with one selected tab');
    await page.evaluate(() => document.querySelectorAll('[data-k]').forEach((e) => { delete e.dataset.k; }));
  }
  // 9.1 public part and 9.2 with the full synthetic ledger.
  async function publicContent(page, label, phone) {
    assert.equal(await text(page, '[data-lab-public-text]'), '연구 결과가 아직 없습니다', label + ': the owner\'s words for no result');
    assert.equal(await page.locator('[data-lab-public]').getAttribute('data-na'), 'LAB_NO_PUBLIC_RESULT');
    const items = await page.locator('[data-bt-item]').evaluateAll((n) => n.map((x) => [x.dataset.btState, x.querySelector('[data-lab-state]').textContent]));
    assert.deepEqual(items, CHECK_STATES.map((st) => [st, STATE_WORDS[st]]), label + ': the readiness checklist');
    assert.deepEqual(await page.locator('[data-lab-row]').evaluateAll((n) => n.map((x) => x.dataset.labRow)), ['9.1.1', '9.1.2', '9.1.3', '9.1.4', '9.1.5', '9.1.6']);
    assert.match(await text(page, '[data-lab-rule]'), /연구 결과 파일이 계약과 달라 파일 전체를 쓰지 않습니다/);
    assert.match(await text(page, '[data-lab-rules]'), /지표 7개: 연 복리 수익률 \(CAGR\) · 총수익률 · 최대 낙폭/);
    assert.doesNotMatch(await text(page, '[data-lab-slot="lab-1"]'), /%/, label + ': no percentage on the public 9.1 part');
    // 9.2
    const facts = await page.locator('[data-forward-facts] dd').allTextContents();
    assert.equal(facts[0], '기록 중 (ACTIVE)'); assert.equal(facts[1], '2026-10-19'); assert.equal(facts[2], 'v2 기본 7건 · v1 비교용 6건');
    assert.match(facts.join('|'), /TARGET v0 · 19종목\|UNCONFIRMED_NOT_USED · 사용 금지\|원장에 가격 없음/);
    const first = await page.locator('[data-forward-days]').first().locator('[data-forward-day]').evaluateAll((n) => n.map((x) => [x.dataset.forwardDay, x.dataset.forwardVersion, x.dataset.forwardEvaluation]));
    assert.equal(first.length, 10, label + ': ten rows, then a fold');
    assert.deepEqual(first.slice(0, 3), [['2026-10-27', X.V2, 'PRIMARY'], ['2026-10-27', X.V1, 'COMPARISON'], ['2026-10-26', X.V2, 'PRIMARY']]);
    assert.ok(first.some(([d, v, e]) => d === '2026-10-23' && v === X.V2 && e === 'PREPARATORY'), label + ': the input-missing day');
    assert.equal(await page.locator('[data-forward-more]').getAttribute('data-forward-more'), '3');
    assert.match(await text(page, '[data-forward-day="2026-10-27"][data-forward-version="' + X.V2 + '"]'), new RegExp('주 평가 · ' + X.CALC_B.replace(/[.]/g, '\\.') + ' · Q 470 · G 466 · 모집단 480'));
    assert.deepEqual(await page.locator('[data-forward-segment]').evaluateAll((n) => n.map((x) => [x.dataset.forwardSegment, x.dataset.forwardPrimary, x.dataset.forwardPrep, x.tagName])),
      [['NONE', '0', '1'], [X.CALC_A, '3', '0'], [X.CALC_B, '2', '0']].map((r) => [...r, phone ? 'LI' : 'TR']), label + ': three segments, never chained (a list on a phone)');
    assert.deepEqual(await page.locator('[data-forward-day]').evaluateAll((n) => [...new Set(n.map((x) => x.tagName))]), [phone ? 'LI' : 'TR'], label + ': the daily rows are a list on a phone, a table on a PC');
    assert.match(await text(page, '[data-forward-segment="' + X.CALC_A + '"]'), /2026-10-20 → 2026-10-22/);
    assert.match(await text(page, '[data-forward-private-note]'), /KIS 분할 반영 일봉으로 D\+5 · 20 · 63 · 252 수익률과 SPY 대비/);
    assert.deepEqual(await page.locator('[data-forward-evidence-day]').evaluateAll((n) => n.map((x) => [x.dataset.forwardEvidenceDay, x.dataset.forwardEvidenceState])),
      X.SESSIONS.map((d) => [d, d === '2026-10-22' ? 'PARTIAL' : 'RECORDED']), label + ': the latest 7 session days');
    assert.match(await text(page, '[data-forward-evidence-missing]'), /^2026-10-22 · 기록 없음 · 나중에 채우지 않음/);
    assert.match(await text(page, '[data-block="9.2.2"]'), /준비 중 · 이후 성과 미산출/);
    const v3 = await text(page, '[data-forward-v3]');
    assert.match(v3, /전진검증 v3 · 설계 승인 \(#442\) · 구현 전이라 v3 숫자 없음/); assert.doesNotMatch(v3, /%|\d+\.\d/);
  }
  // The normal synthetic file: tabs, status lines, facts, metrics, curve, limitations, run switching by keys.
  async function normal(page, label) {
    const p = F.payload(), [pilot, synth] = p.runs;
    await source(page, S.normal); await reopen(page); await waitPanel(page, 'READY');
    const v = await panel(page, 'lab-backtest');
    assert.equal(v.hidden, true, label + ': READY hides the status line'); assert.equal(v.mascot, 0);
    assert.match(await text(page, '[data-lab-file]'), /판독 통과 · 생성 2026-10-31 09:00 UTC · 연구 코드 f00dfeedf00d/);
    assert.deepEqual(await page.locator('[data-lab-run-tab]').evaluateAll((n) => n.map((x) => [x.dataset.labRunTab, x.getAttribute('aria-selected')])), [[pilot.id, 'true'], [synth.id, 'false']]);
    const st = page.locator('[data-lab-run="' + pilot.id + '"] [data-lab-status]');
    assert.equal(await st.textContent(), '실데이터 파일럿 · 미검증', label + ': NOT_VALIDATED'); assert.equal(await st.getAttribute('class'), 'lab-status', label + ': dashed (unverified)');
    const metrics = await page.locator('[data-lab-metrics] [data-metric]').evaluateAll((n) => n.map((x) => [x.dataset.metric, x.dataset.na || '', x.querySelector('[data-metric-value]').textContent]));
    assert.deepEqual(metrics, ['cagr', 'total_return', 'max_drawdown', 'volatility', 'sharpe', 'benchmark_cagr', 'excess_cagr'].map((k) =>
      [k, pilot.metrics[k] === null ? 'NULL' : '', pilot.metrics[k] === null ? '– · ' + pilot.null_reasons[k] : pct(pilot.metrics[k])]), label + ': seven metrics, the null sharpe as – and its reason');
    // Curve: the file's months in order, x strictly increasing, both lines start on the 100 line, end value = total_return.
    const c = await page.locator('[data-curve="' + pilot.id + '"]').evaluate((g) => {
      const pts = (d) => [...d.matchAll(/[ML](-?[\d.]+) (-?[\d.]+)/g)].map((m) => [Number(m[1]), Number(m[2])]), svg = g.querySelector('svg');
      return { months: [...g.querySelectorAll('[data-curve-point]')].map((r) => r.dataset.curvePoint), base: Number(svg.querySelector('[data-curve-line=base]').getAttribute('d').split(' ')[1]),
        baseAttr: 'curveBase' in svg.dataset, n: Number(svg.dataset.curveMonths),
        s: pts(svg.querySelector('[data-curve-line=strategy]').getAttribute('d')), b: pts(svg.querySelector('[data-curve-line=benchmark]').getAttribute('d')),
        end: Number(g.querySelector('[data-curve-end=strategy]').textContent), endB: Number(g.querySelector('[data-curve-end=benchmark]').textContent),
        aria: svg.getAttribute('aria-label'), range: g.querySelector('[data-curve-range]').textContent };
    });
    assert.deepEqual(c.months, pilot.equity_curve.map((x) => x.date), label + ': the value table is the file, months ascending');
    assert.equal(c.n, pilot.equity_curve.length); assert.equal(c.s.length, c.n); assert.equal(c.b.length, c.n);
    for (let i = 1; i < c.s.length; i++) assert.ok(c.s[i][0] > c.s[i - 1][0], label + ': x strictly increasing');
    assert.deepEqual([c.s[0][1], c.b[0][1]], [c.base, c.base], label + ': both lines start on the 100 line');
    assert.equal(c.end, pilot.equity_curve[c.n - 1].strategy); assert.equal(c.endB, pilot.equity_curve[c.n - 1].benchmark);
    assert.ok(Math.abs(c.end / 100 - 1 - pilot.metrics.total_return) <= 1e-4, label + ': the end value is consistent with total_return');
    assert.ok(c.range.endsWith('총수익률 ' + pct(pilot.metrics.total_return)) && metrics[1][2] === pct(pilot.metrics.total_return), label + ': the same total return in the caption and the table');
    assert.equal(c.aria, '자산 곡선 · 2024-01 시작 100 · 2025-06 끝 · ' + c.n + '개 월 · 끝 값은 곡선 아래 글', label + ': a value-free chart label');
    assert.ok(!c.aria.includes(String(c.end)) && !c.aria.includes(String(c.endB)) && !c.baseAttr, label + ': no end value in the label, no derived y in a data attribute');
    assert.deepEqual(await page.locator('[data-lab-run="' + pilot.id + '"] [data-lab-limitations] li').allTextContents(), pilot.limitations, label + ': limitations shown');
    assert.match(await text(page, '[data-lab-run="' + pilot.id + '"] [data-lab-run-facts]'), /현금 \(시험용 금리\) · 배당 재투자 포함[\s\S]*수수료 5 bp · 슬리피지 10 bp/);
    // Run tabs by keys: → the SYNTHETIC run, End / Home.
    await page.locator('[data-lab-run-tab][aria-selected=true]').focus(); await page.keyboard.press('ArrowRight');
    await page.locator('[data-lab-run="' + synth.id + '"]').waitFor();
    assert.equal(await page.evaluate(() => document.activeElement.dataset.labRunTab), synth.id, label + ': the chosen tab keeps the focus');
    assert.equal(await text(page, '[data-lab-run="' + synth.id + '"] [data-lab-status]'), '합성 데이터 · 시험용', label + ': SYNTHETIC');
    await page.keyboard.press('Home'); await page.locator('[data-lab-run="' + pilot.id + '"]').waitFor();
    await page.keyboard.press('End'); await page.locator('[data-lab-run="' + synth.id + '"]').waitFor();
    await page.keyboard.press('ArrowRight'); await page.locator('[data-lab-run="' + pilot.id + '"]').waitFor();
  }
  async function refused(page, label, key) {
    const { src, code } = S.refused[key];
    await source(page, src); await reopen(page); await waitPanel(page, 'ERROR');
    const v = await panel(page, 'lab-backtest');
    assert.deepEqual([v.status, v.mascot, v.body], ['비공개 자료를 불러오지 못했습니다 · ' + code, 1, ''], label + ' ' + key + ': the whole file refused');
    assert.equal(await count(page, '[data-curve], [data-lab-run], [data-lab-metrics]'), 0, label + ' ' + key + ': nothing of the file is drawn');
  }
  try {
    // ================================================================ full ledger, real source (NONE), PC and phone
    for (const width of [1440, 390]) {
      const phone = width < 720, tag = (p) => { phase = width + ' ' + p; };
      const { ctx, page, seen } = await context(width);
      // ---- loading: a layer file held back, then the ledger answer held back
      tag('loading');
      let release, releaseLedger; const gate = new Promise((r) => { release = r; }), gateLedger = new Promise((r) => { releaseLedger = r; });
      await page.route('**/engines.js', async (route) => { await gate; await route.continue(); });
      await page.route('**/' + LEDGER, async (route) => { await gateLedger; await route.continue(); });
      const at = await open(page, '#/lab', { waitUntil: 'domcontentloaded' });
      assert.deepEqual(await page.locator('[data-section]').evaluateAll((n) => n.map((x) => x.dataset.section)), ['lab-1', 'lab-2'], phase + ': the skeleton draws the two sections');
      assert.equal(await count(page, '[data-lab-slot] [data-state=loading][role=status]'), 2, phase + ': both slots say 불러오는 중');
      assert.deepEqual([await count(page, '[data-private-panel]'), await count(page, '[data-block]'), await count(page, '[data-lab-public]')], [0, 0, 0], phase + ': nothing else before the layer');
      assert.deepEqual(reads(at), [], phase + ': nothing read before the layer asks');
      release();
      await page.locator('[data-lab-public]').waitFor();
      await page.locator('[data-block="9.2.1"] [data-state=loading]').waitFor();
      assert.match(await text(page, '[data-block="9.2.1"] [data-state=loading]'), /^불러오는 중 · 전진검증 원장/);
      assert.equal(await count(page, '[data-private-panel]'), 2, phase + ': the private panels come with the public part, not after the ledger');
      releaseLedger(); await drawn(page);
      await page.unroute('**/engines.js'); await page.unroute('**/' + LEDGER);
      await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at), [LEDGER], phase + ': a fresh open reads exactly the public ledger');
      tag('content');
      await panels(page, phase);
      for (const [id] of PANELS) assert.deepEqual(await panel(page, id), { state: 'NOT_READY', status: '비공개 기능 준비 중', hidden: false, mascot: 0, body: '' }, phase + ': ' + id);
      await publicContent(page, phase, phone);
      const base = await publicText(page);
      const at2 = s.requests.length; await reopen(page); await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
      assert.deepEqual(reads(at2), [], phase + ': a route change reads nothing new (the layer keeps the ledger)');
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      assert.equal(await count(page, '[data-forward-more] [data-forward-day]'), 3);
      await keyboard(page, phase);
      await boundaries(page, seen, phase);
      // ---- the Lab states with fixtures
      tag('normal'); await normal(page, phase);
      assert.deepEqual(await publicText(page), base, phase + ': the public text does not change with a private result');
      await page.evaluate(() => document.querySelectorAll('main details').forEach((d) => { d.open = true; }));
      await keyboard(page, phase); await boundaries(page, seen, phase);
      tag('login'); await source(page, S.login); await reopen(page); await waitPanel(page, 'LOGIN_REQUIRED');
      assert.deepEqual(await panel(page, 'lab-backtest'), { state: 'LOGIN_REQUIRED', status: '비공개 연구 결과 · 로그인 필요', hidden: false, mascot: 0, body: '' }, phase + ': login needed');
      await panels(page, phase, 'LOGIN_REQUIRED');
      assert.deepEqual(await publicText(page), base, phase + ': the public text does not change with the sign-in state');
      await boundaries(page, seen, phase);
      tag('schema'); await refused(page, phase, 'schema');
      tag('null'); await source(page, S.allNull); await reopen(page); await waitPanel(page, 'READY');
      const nul = await page.locator('[data-lab-run] [data-metric]').evaluateAll((n) => n.map((x) => [x.dataset.na, x.querySelector('[data-metric-value]').textContent]));
      assert.deepEqual(nul, Array(7).fill(['NULL', '– · 시험용 · 계산 안 함']), phase + ': every null metric is – and its reason');
      assert.equal(await text(page, '[data-lab-run] [data-curve=NONE]'), '곡선 없음 · 성과 지표가 모두 계산 불가라 그리지 않음');
      assert.doesNotMatch(await text(page, '[data-lab-run]'), /%/, phase + ': no percentage for a run without values (never 0)');
      assert.deepEqual(await publicText(page), base);
      await boundaries(page, seen, phase);
      if (!phone) {
        tag('empty'); await source(page, S.empty); await reopen(page); await waitPanel(page, 'READY');
        assert.equal(await text(page, '[data-lab-results] [data-state=empty][data-na=LAB_NO_RUNS]'), '연구 결과가 아직 없습니다');
        assert.deepEqual([await count(page, '[data-lab-results] [data-mascot=plain]'), await count(page, '[data-lab-run-tab]')], [1, 0], phase + ': the calm character, no tab');
        tag('404'); await source(page, S.notFound); await reopen(page); await waitPanel(page, 'ERROR');
        assert.deepEqual(await panel(page, 'lab-backtest'), { state: 'ERROR', status: '비공개 자료를 불러오지 못했습니다 · LAB_RESULT_NOT_FOUND', hidden: false, mascot: 1, body: '' });
        for (const key of ['missingTop', 'missingRun', 'order', 'start', 'total', 'finite', 'zero', 'negative']) { tag('refused ' + key); await refused(page, phase, key); }
        tag('four runs'); await source(page, S.fourRuns); await reopen(page); await waitPanel(page, 'READY');
        const runs = F.valid.find((r) => r[0] === 'with a MIXED and a point_in_time false run')[1]().runs;
        assert.deepEqual(await page.locator('[data-lab-run-tab]').evaluateAll((n) => n.map((x) => x.dataset.labRunTab)), runs.map((r) => r.id));
        await page.locator('[data-lab-run-tab="mixed-pilot"]').click(); await page.locator('[data-lab-run="mixed-pilot"]').waitFor();
        assert.equal(await text(page, '[data-lab-run="mixed-pilot"] [data-lab-status]'), '실데이터와 합성 데이터 혼합 · 파일럿 · 미검증', phase + ': MIXED');
        assert.match(await text(page, '[data-lab-run="mixed-pilot"] [data-lab-run-facts]'), /배당 재투자 제외/);
        await page.locator('[data-lab-run-tab="pit-false-pilot"]').click(); await page.locator('[data-lab-run="pit-false-pilot"]').waitFor();
        assert.equal(await text(page, '[data-lab-run="pit-false-pilot"] [data-lab-status]'), '실데이터 파일럿 · 미검증 · 모집단 시점 정합성 미확인', phase + ': PIT not met');
        assert.equal(await text(page, '[data-lab-run="pit-false-pilot"] [data-lab-pit=false]'), '시점 정합성 미확인');
        assert.deepEqual(await page.locator('[data-lab-run="pit-false-pilot"] [data-lab-limitations] li').allTextContents(), runs[3].limitations);
        tag('source fails'); await source(page, 'reject'); await reopen(page); await waitPanel(page, 'ERROR');
        assert.equal((await panel(page, 'lab-backtest')).status, '비공개 자료를 불러오지 못했습니다 · LAB_SOURCE_FAILED', phase + ': partial failure');
        assert.equal(await count(page, '[data-forward-facts]'), 1, phase + ': 9.2 stays');
        tag('source never answers'); await source(page, 'pending'); await reopen(page); await page.locator('[data-lab-public]').waitFor();
        await page.evaluate(() => new Promise((r) => setTimeout(r, 150)));
        assert.equal((await panel(page, 'lab-backtest')).state, 'NOT_READY', phase + ': the panel keeps its first state');
        assert.deepEqual(await publicText(page), base, phase + ': the public part never waits for the panel');
        await boundaries(page, seen, phase, { errors: [] });
      }
      tag('real source again'); await source(page, 'real'); await reopen(page);
      await page.evaluate(() => new Promise((r) => setTimeout(r, 100)));
      assert.equal((await panel(page, 'lab-backtest')).state, 'NOT_READY');
      await ctx.close(); pass++;
    }
    // ================================================================ partial failure and empty ledgers, PC
    {
      // One fresh page per ledger (the layer keeps one read per page); the context's init script counts CSP violations on each.
      const { ctx, seen } = await context(1440);
      const cases = [
        ['ledger HTTP 500', { status: 500, body: 'synthetic failure' }, 'READ_FAILED', /^전진검증 원장을 읽지 못했습니다/],
        ['ledger 404', null, 'NOT_PUBLISHED', /^전진검증 원장이 아직 게시되지 않았습니다/],
        ['ledger invalid', { json: { schema_version: 9, kind: 'FORWARD_VALIDATION_LEDGER' } }, 'READ_FAILED', /^전진검증 원장을 읽지 못했습니다/],
      ];
      let base = null;
      for (const [name, fx, na, words] of cases) {
        phase = 'partial ' + name;
        s.fixture(LEDGER, fx);
        const p = await ctx.newPage(), w = site.watch(p, s.origin, { allow404: UNPUBLISHED });
        await open(p); await drawn(p);
        assert.match(await text(p, '[data-block="9.2.1"] [data-state=error][data-na=' + na + ']'), words, phase);
        assert.equal(await count(p, '[data-block="9.2.1"] [data-mascot=alarm]'), 1);
        assert.equal(await count(p, '[data-forward-eligibility=NOT_AVAILABLE]'), 1); assert.equal(await count(p, '[data-forward-evidence=NOT_AVAILABLE]'), 1);
        assert.equal(await text(p, '[data-lab-public-text]'), '연구 결과가 아직 없습니다', phase + ': 9.1 stays');
        await panels(p, phase);
        const t = (await publicText(p))[0]; if (base === null) base = t; assert.equal(t, base, phase + ': the 9.1 public part is the same');
        await boundaries(p, w, phase, { errors: [/status of 500/] });
        await p.close();
      }
      const ledgers = [
        ['schema-1 ledger', X.ledgerV1(), async (p) => {
          assert.deepEqual(await p.locator('[data-forward-day]').evaluateAll((n) => n.map((x) => [x.dataset.forwardDay, x.dataset.forwardEvaluation])), [['2026-10-20', 'COMPARISON'], ['2026-10-19', 'COMPARISON']]);
          assert.match(await text(p, '[data-forward-day="2026-10-20"]'), /기록 · 입력 없음 · SEC_QG_FACTORS_MISSING/);
          assert.equal(await text(p, '[data-forward-eligibility=NO_BASIS]'), '관측 기준이 기록된 행이 없어 평가 구간이 없습니다');
          assert.equal((await p.locator('[data-forward-facts] dd').allTextContents())[2], 'v1 비교용 2건');
        }],
        ['empty ledger', X.ledgerEmpty(), async (p) => {
          assert.equal(await text(p, '[data-state=empty][data-na=NO_LEDGER_ROWS]'), '아직 완료된 미국 거래일 기록이 없습니다');
          assert.equal(await text(p, '[data-state=empty][data-na=NO_OBSERVATION]'), '관측일 없음 · 공개 원장 기록 0건');
          assert.equal(await count(p, '[data-forward-day]'), 0); assert.equal(await count(p, '[data-mascot=plain]') >= 2, true, 'the calm character for empty lists');
        }],
        ['ledger before its start date', X.ledgerNotStarted(), async (p) => {
          assert.equal(await text(p, '[data-state=empty][data-na=NO_LEDGER_ROWS]'), '시작일 전이라 기록이 없습니다');
          assert.equal((await p.locator('[data-forward-facts] dd').allTextContents())[0], '시작 전 (NOT_STARTED)');
        }],
      ];
      for (const [name, json, check] of ledgers) {
        phase = 'ledger ' + name;
        s.fixture(LEDGER, { json });
        const p = await ctx.newPage(), w = site.watch(p, s.origin, { allow404: UNPUBLISHED });
        await open(p); await drawn(p); await check(p);
        await boundaries(p, w, phase);
        await p.close();
      }
      s.fixture(LEDGER, FULL[LEDGER]);
      assert.deepEqual(seen.errors, []);
      await ctx.close(); pass++;
    }
    // ================================================================ error: the layer did not load (LOADER_FAILED), phone
    {
      phase = 'error 390';
      const { ctx, page, seen } = await context(390, { allow404: [...UNPUBLISHED, 'data.js'] });
      await page.route('**/data.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      const at = await open(page); await drawn(page);
      assert.equal(await count(page, '[data-lab-slot] [data-state=error][data-na=LOADER_FAILED]'), 2, phase + ': both slots show the failure');
      assert.equal(await count(page, '[data-lab-slot] [data-mascot=alarm]'), 2);
      assert.match(await text(page, '[data-lab-slot="lab-1"] [data-state=error]'), /층을 불러오지 못해 Lab 자료를 그리지 못했습니다/);
      assert.deepEqual([await count(page, '[data-state=loading]'), await count(page, '[data-block]'), await count(page, '[data-private-panel]')], [0, 0, 0], phase + ': no loading line left, no block');
      await page.locator('[data-load-failed]').waitFor();
      assert.equal(await count(page, '[data-load-failed]'), 1, phase + ': the shell notice');
      assert.deepEqual(reads(at), [], phase + ': nothing is read');
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    {
      phase = 'error 1440 (screen-lab-live.js 404)';
      const { ctx, page, seen } = await context(1440, { allow404: [...UNPUBLISHED, 'screen-lab-live.js'] });
      await page.route('**/screen-lab-live.js', (r) => r.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
      await open(page); await drawn(page);
      assert.equal(await page.evaluate(() => window.IS2.ready.then(() => 'READY', (e) => e.message)), 'LOADER_FAILED screen-lab-live.js');
      assert.equal(await count(page, '[data-lab-slot] [data-state=error][data-na=LOADER_FAILED]'), 2, phase + ': the screen\'s error state');
      assert.equal(await count(page, '[data-lab-slot] [data-mascot=alarm]'), 2);
      await page.locator('[data-load-failed]').waitFor();
      await boundaries(page, seen, phase);
      await ctx.close(); pass++;
    }
    console.log('web_app_lab_browser_test: PASS (' + pass + ' contexts: full 1440 with every Lab state, full 390, partial failure and empty ledgers, loader error, live-file error)');
  } catch (e) {
    console.error('web_app_lab_browser_test: FAIL at ' + phase);
    throw e;
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
