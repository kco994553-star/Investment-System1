'use strict';
// Quality pass over the new frontend's first flow: 0. 기업 검색 (#/) → 1.1 QGV 리더보드 (#/qgv) → 기업 화면 (#/company/<id>), in a real
// browser at 1440×1000, 390×844 and 200 % zoom of 1440 (viewport halved to 720×500 CSS px with deviceScaleFactor 2: the CSS width a
// browser gives at 200 %, so the page's own media queries answer as they would). Synthetic fixtures only (the ones the menu 0 and
// menu 1 tests use); nothing real is read. Audit doc: implementation/docs/frontend_v2/QUALITY_AUDIT_FLOW_20261105.md.
//  - Hard checks (always): keyboard only through the flow (Tab to the search box, type, ArrowDown + Enter, Tab to the QGV card link,
//    Enter, Tab to the first leaderboard company link, Enter), a visible focus mark on every stop (an outline ≥ 2 px, or the search
//    box's own outline while its input has focus) and no stop hidden under the phone tab bar; at 200 % no horizontal overflow and
//    no control cut off at the viewport edge or clipped inside its own box; every state below renders its words (no blank screen),
//    no [style], no CSP violation, no uncaught error, nothing leaves the origin, nothing is stored.
//  - States: normal (score file + central V publication), loading (sec-qgv2.json held back by page.route), empty (종합 순위 without
//    a publication, a search with no match, an unknown company), not published (sec-qgv2.json and the publication 404), read failure
//    (an invalid score file), STALE (a clock 3 New York sessions after the publication's basis day), partial missing (the
//    missing-data score file: an axis below 50 %, a STALE TARGET row; rows without V), real 0 vs NA (a valid publication with a V of
//    exactly 0), personal preview (a saved weights profile, a real click on a test-only button).
//  - Distinguishable on the leaderboard and the company page: the population (Universe504), the basis day, the filter state, official
//    result vs personal preview, and a real 0 vs NA.
//  - axe-core rules wcag2a / wcag2aa / wcag21aa on every page and state, when an axe build is available: AXE_CORE_PATH (axe.min.js
//    from a pinned scratch install) or a resolvable axe-core package. It is evaluated in the page through the DevTools protocol
//    (page.evaluate), never added to web_app, the build or the Pages artifact, and the CSP is not relaxed. Violations are counted
//    by page|width|rule and compared with tools/fixtures/web_app_flow_axe_baseline.json: the pre-existing ones there do not fail,
//    anything new does. Without an axe build the rule scan is skipped and says so; QUALITY_REQUIRE_AXE=1 (set by the required
//    cockpit-pages build) makes a missing build, or a build other than the pinned axe 4.14.0 bytes (AXE_SHA256), a failure, so a
//    green CI there means the rule scan ran. The hard checks always run. AXE_WRITE_BASELINE=<file> writes the observed counts.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const site = require('./web_app_test_site');
const F = require('./qgv_v2_fixture.js');
const DATA = require(path.join(R.NEW, 'data.js'));

const ASSETS = R.OLD;
const V2 = require(path.join(ASSETS, 'qgv-v2.js'));
const OFFICIAL = require(path.join(ASSETS, 'qgv-official.js'));
const NOW = '2026-10-14T03:00:00.000Z', STALE_AT = '2026-10-17T03:00:00.000Z';
const fixture = (name) => JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures', name), 'utf8'));
const CLASS = fixture('company_classification_v0_payloads.json').live;
const PUB = JSON.parse(fixture('qgv_official_vectors_v1.json').base_text);
const WEIGHTS = fixture('qgv_v2_custom_vectors_v1.json').cases[0].input.weights;
const BASELINE_FILE = path.join(__dirname, 'fixtures/web_app_flow_axe_baseline.json');
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21aa'];
// axe-core 4.14.0 axe.min.js (npm axe-core@4.14.0, integrity sha512-9WTZxEjs…zzpcQ==): the only build the required CI run accepts.
const AXE_SHA256 = '20c09fe157a8a34a30e241aaa1fcdade657734f08ab379ecfbeb7d45cc46e878';

// A real 0: the publication with NYSE:ABBV's last published V factor at 0, so its V axis is exactly 0, re-derived through the
// reader's own engine (axis, total, ranks, coverage) and checked by the reader's validate() before use. Synthetic.
async function zeroPublication() {
  const Z = structuredClone(PUB), r = Z.rows['NYSE:ABBV'];
  r.factors.v_fcf_yield.score = 0;
  const vs = {}; for (const k of Object.keys(V2.WEIGHTS.V)) vs[k] = r.factors[k].score;
  const v = V2.axisScore(vs, 'V'); r.axes.V.score = v.score; r.axes.V.state = v.state;
  const inc = V2.PILLARS.filter((p) => r.axes[p].score !== null && !(p === 'V' && r.value_trap_gate)); let acc = 0, used = 0;
  for (const p of inc) { acc += r.weights[p] * r.axes[p].score; used += r.weights[p]; } r.total = acc / used;
  const sym = (k) => OFFICIAL.symbol(k), cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  Object.keys(Z.rows).filter((k) => Z.rows[k].rank !== null).sort((a, b) => Z.rows[b].total - Z.rows[a].total || cmp(sym(a), sym(b)) || cmp(a, b)).forEach((k, i) => { Z.rows[k].rank = i + 1; });
  Z.coverage = OFFICIAL.coverage(Z.rows, V2);
  await OFFICIAL.validate(structuredClone(Z));
  assert.equal(Z.rows['NYSE:ABBV'].axes.V.score, 0, 'the fixture has a real 0 V');
  return Z;
}

// axe-core: the given build, else a resolvable package, else none (the rule scan is skipped and reported).
function axeSource() {
  let file = process.env.AXE_CORE_PATH || null;
  if (!file) { try { file = path.join(path.dirname(require.resolve('axe-core/package.json')), 'axe.min.js'); } catch (_) { file = null; } }
  if (!file || !fs.existsSync(file)) return null;
  const bytes = fs.readFileSync(file), text = bytes.toString('utf8'), version = (/axe v([\d.]+)/.exec(text.slice(0, 400)) || [])[1] || 'unknown';
  return { text, version, file, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
}

let phase = 'START';
(async () => {
  const AXE = axeSource();
  if (process.env.QUALITY_REQUIRE_AXE === '1') {
    if (!AXE) throw new Error('AXE_NOT_AVAILABLE: QUALITY_REQUIRE_AXE=1 and no axe build (set AXE_CORE_PATH to the pinned axe.min.js)');
    if (AXE.sha256 !== AXE_SHA256) throw new Error('AXE_BUILD_UNEXPECTED: ' + AXE.version + ' sha256 ' + AXE.sha256 + ' is not the pinned 4.14.0 build');
  }
  if (!AXE) console.log('AXE_NOT_AVAILABLE: rule scan skipped (set AXE_CORE_PATH); hard checks run');
  const baseline = JSON.parse(fs.readFileSync(BASELINE_FILE, 'utf8'));
  const ZERO = await zeroPublication();
  const MISSING = F.missingPayload(), INVALID = F.strictPayload(); INVALID.cross_section_size += 1;
  const base = { 'sec-qgv2.json': { json: F.strictPayload() }, 'company-classification.json': { json: CLASS }, 'qgv-official.json': { json: PUB } };
  const s = await site.start({ fixtures: base });
  const use = (over = {}) => { for (const [k, v] of Object.entries({ ...base, ...over })) s.fixture(k, v); };
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
  const observed = {}, incomplete = {}, scans = [];
  const T0 = Date.now();
  try {
    const open = async ({ width, height, scale = 1, at = NOW }) => {
      const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: scale });
      await context.clock.setFixedTime(new Date(at));
      await context.addInitScript(() => { window.__csp = 0; document.addEventListener('securitypolicyviolation', () => { window.__csp++; }); });
      const page = await context.newPage(), seen = site.watch(page, s.origin, { allow404: DATA.FILES });
      return { context, page, seen };
    };
    const ready = (page) => page.evaluate(() => (window.IS2.ready || Promise.reject()).then(() => 'READY', () => 'FAILED'));
    const settle = (page, ms = 200) => page.evaluate((t) => new Promise((r) => setTimeout(r, t)), ms);
    const go = async (page, hash, selector) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator(selector).first().waitFor({ timeout: 20000 }); await settle(page); };
    const text = (page, sel) => page.evaluate((q) => { const e = document.querySelector(q); return e ? e.innerText.replace(/\s+/g, ' ').trim() : null; }, sel);

    // Every page: no [style], no CSP violation, no overflow, no blank main; axe when available.
    async function scan(page, name, width) {
      const label = width + ' ' + name;
      assert.equal(await page.locator('[style]').count(), 0, label + ': no style attribute');
      assert.equal(await page.evaluate(() => window.__csp), 0, label + ': no CSP violation');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');
      assert.ok(((await text(page, 'main')) || '').length > 20, label + ': main says something');
      // Label in name (WCAG 2.5.3; axe's rule for it is experimental and off in a tag run): a control with an aria-label has its
      // visible words (aria-hidden parts left out) as whole words, in order, inside that label (내림 is not a word of 내림차순).
      const mismatch = await page.evaluate(() => {
        const words = (t) => String(t || '').toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(Boolean), out = [];
        const inside = (a, b) => { for (let i = 0; i + a.length <= b.length; i++) if (a.every((w, j) => b[i + j] === w)) return true; return false; };
        for (const e of document.querySelectorAll('main button[aria-label], main a[aria-label], main [role=button][aria-label]')) {
          if (!e.getClientRects().length) continue;
          // Visible words: text nodes and the rendered children that are not aria-hidden (innerText of an unrendered element is its
          // textContent, so a display:none child is left out by its client rects).
          const vis = words([...e.childNodes].map((n) => (n.nodeType === 3 ? n.nodeValue : n.nodeType !== 1 || n.getAttribute('aria-hidden') === 'true' || !n.getClientRects().length ? '' : n.innerText)).join(''));
          if (vis.length && !inside(vis, words(e.getAttribute('aria-label')))) out.push(e.tagName + ' "' + e.innerText.trim().slice(0, 30) + '" / "' + e.getAttribute('aria-label') + '"');
        }
        return out;
      });
      assert.deepEqual(mismatch, [], label + ': every aria-label holds the visible words');
      // Headings in main never skip a level going down (h1 → h3 without an h2), and main has one h1.
      const heads = await page.evaluate(() => [...document.querySelectorAll('main h1, main h2, main h3, main h4, main h5, main h6')].filter((e) => e.getClientRects().length).map((e) => Number(e.tagName[1])));
      assert.equal(heads.filter((n) => n === 1).length, 1, label + ': one h1 in main');
      assert.deepEqual(heads.map((n, i) => (i && n > heads[i - 1] + 1 ? heads[i - 1] + '→' + n : null)).filter(Boolean), [], label + ': no heading level skipped');
      if (!AXE) return;
      if (!(await page.evaluate(() => typeof window.axe === 'object'))) await page.evaluate(AXE.text);
      const r = await page.evaluate((tags) => window.axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations', 'incomplete'] })
        .then((x) => ({ v: x.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, at: v.nodes.slice(0, 3).map((n) => n.target.join(' ')) })), i: x.incomplete.map((v) => ({ id: v.id, n: v.nodes.length })) })), TAGS);
      for (const v of r.v) observed[name + '|' + width + '|' + v.id] = (observed[name + '|' + width + '|' + v.id] || 0) + v.n;
      for (const v of r.i) incomplete[name + '|' + width + '|' + v.id] = (incomplete[name + '|' + width + '|' + v.id] || 0) + v.n;
      scans.push({ name, width, violations: r.v });
      assert.equal(await page.evaluate(() => window.__csp), 0, label + ': axe caused no CSP violation');
    }
    const boundaries = async ({ page, seen }, label) => {
      assert.deepEqual(seen.outside, [], label + ': no request leaves the origin');
      assert.deepEqual(seen.errors.filter((e) => !/status of 404/.test(e)), [], label + ': no uncaught error or console error but a 404');
      const st = await site.storage(page); assert.deepEqual([st.local, st.session], [0, 0], label + ': nothing stored without a click');
    };

    // ---- keyboard: Tab until a selector has focus; every stop on the way must show a focus mark and stay above the tab bar.
    async function tabTo(page, selector, label, max = 200) {
      const stops = [];
      for (let i = 1; i <= max; i++) {
        await page.keyboard.press('Tab');
        const a = await page.evaluate((sel) => {
          const e = document.activeElement; if (!e || e === document.body) return { none: true };
          const cs = getComputedStyle(e), ring = (x) => { const c = getComputedStyle(x); return c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) >= 2; };
          const box = e.closest('.search-box'), mark = ring(e) || (!!box && e.matches('.search-box input') && ring(box));
          const r = e.getBoundingClientRect(), bar = document.querySelector('.tabbar'), b = bar && getComputedStyle(bar).display !== 'none' && !bar.contains(e) ? bar.getBoundingClientRect() : null;
          const hidden = !!b && r.top >= b.top - 1, cut = !!b && r.bottom > b.top + 1 && !hidden;
          return { tag: e.tagName, k: (e.getAttribute('href') || e.dataset.k || e.id || e.textContent || '').slice(0, 40), mark, hidden, cut, visible: cs.visibility !== 'hidden' && r.width > 0 && r.height > 0, hit: e.matches(sel) };
        }, selector);
        if (a.none) continue;
        stops.push(a);
        if (a.hit) break;
      }
      const last = stops[stops.length - 1];
      assert.ok(last && last.hit, label + ': ' + selector + ' reached by Tab within ' + max);
      assert.deepEqual(stops.filter((x) => !x.mark).map((x) => x.tag + ' ' + x.k), [], label + ': every Tab stop shows a focus mark');
      assert.deepEqual(stops.filter((x) => x.hidden).map((x) => x.tag + ' ' + x.k), [], label + ': no Tab stop is hidden under the tab bar');
      return { tabs: stops.length, cut: stops.filter((x) => x.cut).length };
    }

    // ================================================================ 1440 and 390: states, flow, distinctions
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      const tag = (p) => { phase = width + ' ' + p; };
      // ---------------- normal + keyboard flow
      {
        tag('normal'); use();
        const ctx = await open({ width, height }), { page } = ctx;
        await page.goto(s.base + '#/'); assert.equal(await ready(page), 'READY');
        await page.locator('[data-quote] .quote-ko').waitFor(); await settle(page);
        await scan(page, 'home', width);
        // Keyboard only: the search box, a pick with the arrow keys, Enter.
        tag('keyboard');
        const kb = {};
        kb.search = await tabTo(page, '[data-search-input]', phase + ' home');
        await page.keyboard.type('nvda'); await page.locator('#q-list [role=option]').first().waitFor();
        await settle(page); await scan(page, 'home-list', width);
        await page.keyboard.press('ArrowDown');
        assert.equal(await page.locator('#q-list [role=option][aria-selected=true]').count(), 1, phase + ': ArrowDown makes an option active');
        await page.keyboard.press('Enter'); await page.waitForFunction(() => location.hash === '#/company/nvda');
        await page.locator('[data-card=qgv] [data-qgv]').waitFor(); await settle(page);
        assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.id), 'main', phase + ': after the route change the focus is on main');
        await scan(page, 'company', width);
        kb.card = await tabTo(page, 'main a[href="#/qgv"]', phase + ' company');
        await page.keyboard.press('Enter'); await page.waitForFunction(() => location.hash === '#/qgv');
        await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 }); await settle(page);
        await scan(page, 'qgv', width);
        kb.row = await tabTo(page, '[data-lb-table] tbody tr[data-row] a.co', phase + ' qgv', 300);
        const target = await page.evaluate(() => document.activeElement.getAttribute('href'));
        await page.keyboard.press('Enter'); await page.waitForFunction((h) => location.hash === h, target);
        await page.locator('[data-card=qgv] [data-qgv]').waitFor(); await settle(page);
        console.log(phase + ': Tab presses to the search box ' + kb.search.tabs + ', to the QGV card link ' + kb.card.tabs + ', to the first leaderboard company ' + kb.row.tabs
          + ' (stops partly under the tab bar: ' + (kb.search.cut + kb.card.cut + kb.row.cut) + ')');
        // ---- distinctions on the company page (official V, its basis day, the population)
        tag('company distinctions');
        const head = await text(page, '.result-head'), card = await text(page, '[data-card=qgv]');
        assert.match(head, /Universe504/, phase + ': the company header names its population');
        assert.match(card, /V 출처: 공식 V/, phase + ': the QGV card says the V is the official one');
        assert.match(card, /가격 기준일 2026-10-13/, phase + ': the QGV card shows the price basis day');
        assert.match(card, /점수 갱신 2026\. 10\. 13\. 22:30 UTC/, phase + ': the QGV card shows the score refresh time');
        // ---- distinctions on the leaderboard: population, basis day, official vs preview, filter state
        await go(page, '#/qgv', '[data-lb-table] tbody tr[data-row]');
        tag('leaderboard distinctions');
        assert.match(await text(page, '[data-lb-count]'), /^평가: Universe504 중 점수 행 \d+$/, phase + ': the population is named');
        assert.match(await text(page, '[data-qgv-chips]'), /가격 기준일 2026-10-13/, phase + ': the basis day is shown');
        const b6 = await text(page, '[data-lb="2.1.6"]');
        assert.match(b6, /공식 가중치 결과/); assert.match(b6, /내 설정 결과\(미리보기\)/); assert.match(b6, /공식 점수 아님/, phase + ': the preview is said not to be official');
        const cap0 = await text(page, '[data-lb-table] caption');
        assert.doesNotMatch(cap0, /필터/, phase + ': no filter, no filter word in the caption');
        if (width < 720) { await page.locator('[data-k=panel]').click(); }
        const opts = await page.evaluate(() => [...document.querySelector('[data-k="f-industry"]').options].filter((o) => o.value && !o.disabled).map((o) => o.value));
        let rows = 0;
        for (const o of opts) { await page.locator('[data-k="f-industry"]').selectOption(o); await settle(page, 80); rows = await page.locator('[data-lb-table] tbody tr[data-row]').count(); if (rows > 0) break; }
        assert.ok(rows > 0, phase + ': an industry filter that leaves rows');
        const cap1 = await text(page, '[data-lb-table] caption');
        assert.match(cap1, /필터 적용/, phase + ': with a filter on, the table caption says so next to the table (' + cap1 + ')');
        await scan(page, 'qgv-filtered', width);
        await page.locator('[data-k=clear-filters-2]').click(); await settle(page);
        assert.doesNotMatch(await text(page, '[data-lb-table] caption'), /필터/, phase + ': filters cleared, the caption word goes');
        // ---- personal preview (a saved profile through a real click on a test-only button, removed before the scan)
        tag('preview');
        await page.evaluate((weights) => { const b = document.createElement('button'); b.type = 'button'; b.dataset.testAction = 'weights'; b.textContent = 'test weights';
          b.addEventListener('click', (e) => { window.__saved = Promise.resolve().then(() => window.IS2.store.saveWeights(e, { name: '시험 가중치', weights, gate: true })).then(() => 'OK', (x) => String(x && x.message)); });
          document.body.prepend(b); }, WEIGHTS);
        await page.locator('[data-test-action=weights]').click(); assert.equal(await page.evaluate(() => window.__saved), 'OK');
        await page.evaluate(() => document.querySelector('[data-test-action]').remove());
        await page.waitForFunction(() => { const b = document.querySelector('[data-k=mode-preview]'); return b && !b.disabled; });
        await page.locator('[data-k=mode-preview]').click(); await page.locator('[data-list-lock=PREVIEW]').waitFor(); await settle(page);
        const sub = await text(page, '[data-lb-table] thead th .sub'), capP = await text(page, '[data-lb-table] caption');
        assert.match(sub + ' ' + capP, /개인|내 설정/, phase + ': the preview table says it is personal (' + sub + ')');
        assert.doesNotMatch(sub, /^공식 순위/, phase + ': the preview rank header is not the official one');
        await scan(page, 'qgv-preview', width);
        await ctx.context.close();
      }
      // ---------------- loading: the score file held back
      {
        tag('loading'); use();
        const ctx = await open({ width, height }), { page } = ctx;
        let release; const gate = new Promise((r) => { release = r; });
        await page.route('**/sec-qgv2.json', async (route) => { await gate; await route.continue(); });
        await page.goto(s.base + '#/qgv', { waitUntil: 'domcontentloaded' }); await page.locator('main[data-route=qgv]').waitFor(); await settle(page, 400);
        assert.equal(await page.locator('[data-lb-table] tbody tr[data-row]').count(), 0, phase + ': no row before the score file');
        assert.ok(await page.locator('main [data-pending]').count() > 0, phase + ': the blocks say they are waiting');
        await scan(page, 'qgv@loading', width);
        await go(page, '#/company/nvda', '[data-result-code="nvda"]'); await settle(page, 300);
        assert.ok(await page.locator('[data-card=qgv] [data-pending], [data-card=qgv] [data-na]').count() > 0, phase + ': the QGV card waits');
        await scan(page, 'company@loading', width);
        release(); await page.locator('[data-card=qgv] [data-qgv]').waitFor({ timeout: 20000 });
        await boundaries(ctx, phase); await ctx.context.close();
      }
      // ---------------- empty: 종합 순위 without a publication, a search without a match, an unknown company
      {
        tag('empty'); use({ 'qgv-official.json': { status: 404 } });
        const ctx = await open({ width, height }), { page } = ctx;
        await page.goto(s.base + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
        await page.locator('button[data-list=RANKED]').click(); await page.locator('[data-empty=NO_RANKING]').waitFor(); await settle(page);
        assert.equal(await page.locator('[data-empty=NO_RANKING] svg.mascot').count(), 1, phase + ': the empty list has the state character');
        await scan(page, 'qgv@empty-ranking', width);
        await go(page, '#/', '[data-search-input]'); await page.locator('[data-search-input]').fill('zzzzq');
        await page.locator('#q-list [data-search-state=empty]').waitFor(); await scan(page, 'home@no-match', width);
        await go(page, '#/company/NOPE-QA', '[data-not-found]'); await scan(page, 'company@not-found', width);
        await boundaries(ctx, phase); await ctx.context.close();
      }
      // ---------------- not published (404) and read failure (invalid score file)
      for (const [name, over, word] of [['unpublished', { 'sec-qgv2.json': { status: 404 }, 'qgv-official.json': { status: 404 } }, /미게시/], ['read-failed', { 'sec-qgv2.json': { json: INVALID }, 'qgv-official.json': { status: 404 } }, /읽기 실패/]]) {
        tag(name); use(over);
        const ctx = await open({ width, height }), { page } = ctx;
        await page.goto(s.base + '#/qgv'); await page.locator('[data-lb="2.1.1"] .state-card').waitFor({ timeout: 20000 }); await settle(page);
        assert.match(await text(page, '[data-lb="2.1.1"] .state-card'), word, phase + ': the state card names the state');
        assert.equal(await page.locator('[data-lb="2.1.1"] .state-card svg.mascot').count(), 1, phase + ': the state character');
        await scan(page, 'qgv@' + name, width);
        await go(page, '#/company/nvda', '[data-card=qgv] [data-na]');
        assert.match(await text(page, '[data-card=qgv]'), /점수 입력 파일/, phase + ': the QGV card says why it has no values');
        assert.equal(await page.locator('[data-card=qgv] .qval').count(), 0, phase + ': no number in the QGV card');
        await scan(page, 'company@' + name, width);
        await boundaries(ctx, phase); await ctx.context.close();
      }
      // ---------------- STALE: the publication 3 New York sessions old
      {
        tag('stale'); use();
        const ctx = await open({ width, height, at: STALE_AT }), { page } = ctx;
        await page.goto(s.base + '#/qgv'); await page.locator('[data-central-state=STALE]').waitFor({ timeout: 20000 }); await settle(page);
        assert.match(await text(page, '[data-qgv-chips]'), /STALE · 기준일 뒤 끝난 뉴욕 정규장 2회 초과 · 마지막 게시본 그대로/);
        await scan(page, 'qgv@stale', width);
        await go(page, '#/company/nvda', '[data-card=qgv] [data-qgv]');
        assert.match(await text(page, '[data-card=qgv] [data-v-source]'), /STALE/, phase + ': the company card says STALE too');
        await scan(page, 'company@stale', width);
        await boundaries(ctx, phase); await ctx.context.close();
      }
      // ---------------- partial missing: an axis below 50 %, a STALE TARGET row, rows without V
      {
        tag('partial'); use({ 'sec-qgv2.json': { json: MISSING }, 'qgv-official.json': { status: 404 } });
        const ctx = await open({ width, height }), { page } = ctx;
        await page.goto(s.base + '#/qgv'); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 }); await settle(page);
        const na = await page.evaluate(() => [...document.querySelectorAll('[data-lb-table] td[data-cell=v]')].map((td) => td.textContent));
        assert.ok(na.length > 1 && na.every((t) => /^NA/.test(t)), phase + ': without a publication every V cell is NA with its reason');
        await scan(page, 'qgv@partial', width);
        await go(page, '#/company/amd', '[data-card=qgv] [data-qgv]');
        assert.equal(await page.locator('[data-card=qgv] [data-axis=Q][data-state=NA]').count(), 1, phase + ': amd Q is NA (axis below 50 %)');
        assert.match(await text(page, '[data-card=qgv] [data-why=Q]'), /^Q NA · /, phase + ': with its reason');
        await scan(page, 'company@partial', width);
        await boundaries(ctx, phase); await ctx.context.close();
      }
      // ---------------- a real 0 next to NA
      {
        tag('zero'); use({ 'qgv-official.json': { json: ZERO } });
        const ctx = await open({ width, height }), { page } = ctx;
        await page.goto(s.base + '#/qgv'); await page.locator('tr[data-row="NYSE:ABBV"]').waitFor({ timeout: 20000 }); await settle(page);
        const cells = await page.evaluate(() => { const v = (id) => { const td = document.querySelector('tr[data-row="' + id + '"] td[data-cell=v]'); return td ? { t: td.textContent, na: !!td.querySelector('.na, [data-na]') || td.classList.contains('na') } : null; };
          return { zero: v('NYSE:ABBV'), na: v('NYSE:MO') }; });
        assert.equal(cells.zero.t, '0.0', phase + ': a real 0 V shows 0.0'); assert.equal(cells.zero.na, false, phase + ': and is not marked NA');
        assert.match(cells.na.t, /^NA./, phase + ': a missing V shows NA with its reason'); assert.equal(cells.na.na, true);
        await scan(page, 'qgv@zero', width);
        await go(page, '#/company/NYSE%3AABBV', '[data-card=qgv] [data-qgv]');
        const bar = await page.evaluate(() => { const r = document.querySelector('[data-card=qgv] [data-axis=V]'); return { state: r.dataset.state, val: r.querySelector('.qval').textContent, dashed: r.querySelector('svg.qbar').classList.contains('na') }; });
        assert.deepEqual(bar, { state: 'OK', val: '0.0', dashed: false }, phase + ': the company bar shows 0.0 on a solid track, not the dashed NA track');
        await scan(page, 'company@zero', width);
        await boundaries(ctx, phase); await ctx.context.close();
      }
    }

    // ================================================================ 200 % zoom of 1440 (720×500 CSS px, deviceScaleFactor 2)
    {
      phase = '720z'; use();
      const ctx = await open({ width: 720, height: 500, scale: 2 }), { page } = ctx;
      const clipped = () => page.evaluate(() => {
        const W = window.innerWidth, out = [];
        const scroller = (e) => { for (let p = e.parentElement; p; p = p.parentElement) { const c = getComputedStyle(p); if (/(auto|scroll)/.test(c.overflowX) && p.scrollWidth > p.clientWidth + 1) return true; } return false; };
        for (const e of document.querySelectorAll('a[href], button, input, select, summary, .chip')) {
          const r = e.getBoundingClientRect(), c = getComputedStyle(e); if (!r.width || !r.height || c.visibility === 'hidden') continue;
          if ((r.left < -1 || r.right > W + 1) && !scroller(e)) out.push('edge ' + e.tagName + ' ' + (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 30));
          if (/(hidden|clip)/.test(c.overflowX) && e.scrollWidth > e.clientWidth + 1 && e.tagName !== 'INPUT') out.push('clip ' + e.tagName + ' ' + e.textContent.trim().slice(0, 30));
        }
        return out;
      });
      for (const [hash, sel, name] of [['#/', '[data-quote] .quote-ko', 'home'], ['#/qgv', '[data-lb-table] tbody tr[data-row]', 'qgv'], ['#/company/nvda', '[data-card=qgv] [data-qgv]', 'company']]) {
        await page.goto(s.base + hash); await page.locator(sel).first().waitFor({ timeout: 20000 }); await settle(page);
        assert.deepEqual(await clipped(), [], phase + ' ' + name + ': no control cut off or clipped');
        await scan(page, name, '720z');
      }
      await boundaries(ctx, phase); await ctx.context.close();
    }

    // ================================================================ axe: no violation beyond the baseline
    if (AXE) {
      const allowed = baseline.counts || {}, fresh = Object.entries(observed).filter(([k, n]) => n > (allowed[k] || 0)).map(([k, n]) => k + ' ' + n + ' > ' + (allowed[k] || 0));
      if (process.env.AXE_WRITE_BASELINE) fs.writeFileSync(process.env.AXE_WRITE_BASELINE, JSON.stringify({ axe: AXE.version, tags: TAGS, counts: observed, incomplete, scans }, null, 1) + '\n');
      const fixed = Object.keys(allowed).filter((k) => !(k in observed));
      console.log('axe ' + AXE.version + ' ' + TAGS.join(',') + ': ' + scans.length + ' scans, violations ' + JSON.stringify(observed) + ', needs review ' + JSON.stringify(incomplete) + (fixed.length ? ', baseline entries now clean: ' + fixed.join(' ') : ''));
      assert.deepEqual(fresh, [], 'no axe violation beyond tools/fixtures/web_app_flow_axe_baseline.json');
    }
    console.log('web app flow quality: keyboard flow, focus marks, states (normal, loading, empty, unpublished, read failure, STALE, partial, real 0 vs NA, preview), distinctions and 200 % zoom ok at 1440, 390 and 720z (' + Math.round((Date.now() - T0) / 1000) + ' s)');
  } finally {
    await browser.close(); await s.close();
  }
})().catch((e) => { console.error('FAILED at ' + phase + ':', e && e.stack || e); process.exit(1); });
