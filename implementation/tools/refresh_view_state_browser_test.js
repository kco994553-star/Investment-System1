'use strict';
/* G2 (FRONTEND_INTERACTION_CONTRACT_20261019.md §3-3): a FULL screen drawn again by '자료 새로고침' or by a freshness re-judgement
   (data-refresh.js) keeps the user's view state — page scroll, focus, open details, filter / sort / search fields, the chosen view
   button — and shows the values of the new publication. A screen the user opens still starts at the top.
   Inputs:
     REAL_FETCH    the page's own requests; the test only decides what the local server answers (day 1 → day 2 publication).
     HARNESS_CLOCK the browser clock is moved by the test (Playwright context.clock) past the rows' own 14-day window.
     HARNESS_EVENT the tab's 'visibilitychange' (a phone coming back to the app) starts the re-judgement instead of the 1-minute timer.
     HARNESS_CLICK the refresh button's own click handler is run with element.click(): a pointer click would first scroll the page
                   to the bar, which is what the user does, not what the screen does.
   Publications are synthetic and price-free (the same day 1 / day 2 as data_refresh_browser_test.js, plus a 13F file). */
const { chromium } = require('playwright'), assert = require('node:assert/strict'), path = require('node:path');
const WA = path.join(__dirname, '../src/investment_system/product/web_assets');
globalThis.QgvV2 = require(path.join(WA, 'qgv-v2.js'));
const SQ = globalThis.SecQgv2 = require(path.join(WA, 'sec-qgv2.js'));
globalThis.Qgv2Inputs = require(path.join(WA, 'qgv2-inputs.js'));
globalThis.MacroLights = require(path.join(WA, 'macro-lights.js'));
const PS = require(path.join(WA, 'public-screens.js')), SD = require(path.join(WA, 'sec-disclosures.js'));
const F = require('./qgv_v2_fixture.js'), secFx = require('./sec_disclosures_fixture.js'), newsFx = require('./news_signals_fixture.js');
const { EMPTY, routeEmptyPublicScreens } = require('./empty_public_screens.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const WIDTHS = (process.env.VIEW_STATE_WIDTHS || '390,1280').split(',').map(Number);
const DAYS = { 1: { as_of: '2026-10-13T22:30:00Z', now: '2026-10-14T03:00:00Z' }, 2: { as_of: '2026-10-14T22:30:00Z', now: '2026-10-15T03:00:00Z' } };
// Past the 14-day window of the day-1 rows (acquired 2026-10-13T22:30Z) and the 1-day / 2-day windows of the other files.
const PAST = '2026-10-28T00:00:00Z';
const H = (c) => c.repeat(64);

// ---------- the synthetic publications ----------
function recompute(p) {
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version);
  for (const [role, rows] of [['universe', p.records], ['target', p.target]]) for (const [k, r] of Object.entries(rows)) { const s = scores.get(role + '\u0000' + k); if (s) { r.factors = s.factors; r.axes = s.axes; } }
}
function qgv2Day(n) {
  const p = F.strictPayload(); if (n === 1) { SQ.validate(p); return p; }
  p.as_of = DAYS[2].as_of; p.last_shard_index = (p.last_shard_index + 1) % p.shard_count;
  const m = p.target.msft; m.acquired_at = DAYS[2].as_of;
  Object.assign(m.metrics, { roic: 0.5, interest_coverage: 60, net_debt_to_ebitda: -1, dilution_3y: -0.05, revenue_acceleration: 0.2, accruals_to_assets: -0.2 });
  recompute(p); SQ.validate(p); return p;
}
function secDay(n) {
  const p = secFx.payload(Date.parse(DAYS[n].now)); if (n === 1) return p;
  const events = p.events.filter((e) => e.company_id !== 'amd').map((e) => ({ ...e, group_id: null, occurrence: null }));
  SD.groups(events).forEach((g, i) => Object.assign(events[i], g)); return SD.validate({ ...p, events });
}
function newsDay(n, sec) {
  // news-signals schema 2: a later day without amd's items is built by the fixture so the refresh summary stays consistent.
  return newsFx.payload(Date.parse(DAYS[n].now), sec, n === 1 ? {} : { without: ['amd'] });
}
const CURVE = { 1: { date: '2026-10-12', ten_year: 4.2, three_month: 4.5, run_days: 25 }, 2: { date: '2026-10-13', ten_year: 4.4, three_month: 4.1, run_days: 0 } };
function macroDay(n) {
  const p = structuredClone(EMPTY['macro-screen.json']), at = DAYS[n].as_of.replace('Z', '+00:00'), A = H('a'), B = H(n === 1 ? 'b' : 'c');
  p.as_of = at; p.state = 'LIVE'; p.sources = [{ agency: 'BLS', sha256: A, acquired_at: at }, { agency: 'TREASURY', sha256: B, acquired_at: at }];
  const L = p.data.macro_lights_v1.lights, c = CURVE[n];
  Object.assign(L.employment, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', avg3: 4.6, low12: 4.0, low12_count: 12, gap: 4.6 - 4.0 } });
  Object.assign(L.inflation, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', base_period: '2025-09', yoy: 0.03 } });
  Object.assign(L.curve, { state: 'LIVE', lit: c.run_days >= 20, reason: c.run_days >= 20 ? 'LIT' : 'NOT_LIT', as_of: c.date, inputs: [{ sha256: B, acquired_at: at }], values: { date: c.date, ten_year: c.ten_year, three_month: c.three_month, spread: c.ten_year - c.three_month, run_days: c.run_days } });
  PS.validate('macro-screen.json', JSON.parse(JSON.stringify(p))); return p;
}
function thirteenfDay(n) {
  const at = DAYS[n].as_of, change = (cusip, a, b, kind) => ({ cusip, security_key: H('c'), unit: 'SH', kind, reported_before: a, reported_after: b, reported_delta: b - a });
  const changes = n === 1 ? [change('A00000000', 0, 5, 'NEW'), change('B00000000', 4, 0, 'EXIT')] : [change('A00000000', 0, 5, 'NEW'), change('C00000000', 1, 9, 'ADD')];
  const p = { schema_version: 1, kind: 'SEC_13F', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_13F', sha256: H('a'), acquired_at: at }, { agency: 'SEC_13F', sha256: H('b'), acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400,
    data: { role: 'REPORTED_QUANTITY_CHANGE_NOT_TRADES', reports: [{ manager_cik: '0000000001', previous_quarter: '2026-03-31', current_quarter: '2026-06-30', state: 'LIVE', source_hashes: { previous: H('a'), current: H('b') }, changes },
      { manager_cik: '0000000002', previous_quarter: '2026-03-31', current_quarter: '2026-06-30', state: 'LIVE', source_hashes: { previous: H('a'), current: H('b') }, changes: [change('A00000000', 2, 3, 'ADD')] }] } };
  PS.validate('sec-13f-changes.json', JSON.parse(JSON.stringify(p))); return p;
}
const PUB = {};
for (const n of [1, 2]) { const sec = secDay(n); PUB[n] = { 'sec-qgv2.json': qgv2Day(n), 'sec-disclosures.json': sec, 'news-signals.json': newsDay(n, sec), 'macro-screen.json': macroDay(n), 'sec-13f-changes.json': thirteenfDay(n) }; }

// ---------- the FULL screens (data-refresh.js FULL) and what the user does on each ----------
// act: what the user does (scroll is added for every screen). read: values of the publication on that screen.
// change(before, after, mode): the values the new set must show. Every screen is also checked to be a new drawing (old nodes gone).
// A re-judgement changes what a screen shows only where it shows a time-judged state (13F / macro STALE line, tree example,
// system example); news, watchlist, QGV hub, companies and entity show none, so there the same values are drawn again.
const S = (sel) => `document.querySelector(${JSON.stringify(sel)})`;
const ROUTES = [
  { name: 'qgv', hash: 'qgv', ready: '[data-hub="qgv"]', focus: '[data-hub="qgv"] a[href="#leaderboard"]',
    read: () => ({ basis: document.getElementById('data-refresh').dataset.refreshBasis }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.basis !== a.basis : true },
  { name: 'thirteenf', hash: 'thirteenf', ready: '[data-13f-view]', tab: '[data-13f-view="security"]', focus: '[data-13f-view="security"]',
    read: () => ({ asOf: [...document.querySelectorAll('[data-public-screen="thirteenf"] .meta')].map((m) => m.textContent).join('|'), stale: !!document.querySelector('[data-public-screen="thirteenf"] [data-public-stale]'),
      securities: [...document.querySelectorAll('[data-13f-security]')].map((x) => x.dataset['13fSecurity']) }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.asOf !== a.asOf && b.securities.join() === 'A00000000,C00000000' && a.securities.join() === 'A00000000,B00000000' : !a.stale && b.stale },
  { name: 'thirteenf-style', hash: 'thirteenf', ready: '[data-13f-style]', tab: '[data-13f-style]:nth-of-type(2)', focus: '[data-13f-style-all]',
    read: () => ({ asOf: [...document.querySelectorAll('[data-public-screen="thirteenf"] .meta')].map((m) => m.textContent).join('|'), stale: !!document.querySelector('[data-public-screen="thirteenf"] [data-public-stale]') }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.asOf !== a.asOf : !a.stale && b.stale },
  { name: 'news', hash: 'news', ready: '#news-disclosures [data-timeline] > li', field: ['#news-scope', 'interest'], tab: '#show-network', focus: '#show-network',
    read: () => ({ keys: [...document.querySelectorAll('#news-disclosures [data-timeline] > li')].map((x) => x.dataset.news ? 'N:' + x.dataset.news : 'D:' + x.dataset.disclosure).join(), stale: [...document.querySelectorAll('#news-disclosures .meta')].map((m) => m.textContent).join('|') }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.keys !== a.keys : b.keys === a.keys },
  { name: 'watchlist', hash: 'watchlist', ready: '#watch-disclosures [data-timeline] > li', field: ['#watch-sort', null], text: ['#group-name', '반도체 후보'], details: '#content details:has(#group-name)', focus: '#group-name',
    read: () => ({ keys: [...document.querySelectorAll('#watch-disclosures [data-timeline] > li')].map((x) => x.dataset.news ? 'N:' + x.dataset.news : 'D:' + x.dataset.disclosure).join(), stale: [...document.querySelectorAll('#watch-disclosures .meta')].map((m) => m.textContent).join('|') }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.keys !== a.keys : b.keys === a.keys },
  { name: 'macro', hash: 'macro', ready: '[data-macro-light="curve"]', details: 'details[data-macro-legacy]', focus: 'details[data-macro-legacy] > summary',
    read: () => { const li = document.querySelector('[data-macro-light="curve"]'); return { curve: li.dataset.macroLightState + ' ' + li.querySelector('.meta').textContent, stale: !!document.querySelector('[data-public-screen="macro"] [data-public-stale]') }; },
    change: (a, b, mode) => mode === 'REFRESH' ? b.curve !== a.curve : !a.stale && b.stale },
  { name: 'tree', hash: 'tree/qgv', ready: '[data-tree-examples="qgv"] [data-example-state]', focus: '[data-tree-examples="qgv"] a, #content a[href^="#"]',
    read: () => { const b = document.querySelector('[data-tree-examples="qgv"] [data-tree-example-body]'); const st = document.querySelector('[data-tree-examples="qgv"] [data-example-state]'); return { asOf: b ? b.dataset.exampleAsOf : null, Q: b ? b.querySelector('[data-example-axis="Q"]')?.textContent : null, state: st ? st.dataset.exampleState + ' ' + st.textContent : null }; },
    change: (a, b, mode) => mode === 'REFRESH' ? b.asOf !== a.asOf : b.state !== a.state || b.Q !== a.Q },
  { name: 'system', hash: 'system', ready: '[data-system-example="qgv"]', focus: '#content a[href^="#"]',
    read: () => ({ qgv: document.querySelector('[data-system-example="qgv"]').textContent, macro: document.querySelector('[data-system-example="macro"]')?.textContent }),
    change: (a, b, mode) => b.qgv !== a.qgv },
  { name: 'companies', hash: 'companies', ready: '#company-list li', field: ['#company-sort', 'name'], text: ['#search', 'a'], details: '#content details:has(#group-name)', focus: '#search', more: '#more-companies',
    read: () => ({ basis: document.getElementById('data-refresh').dataset.refreshBasis, rows: [...document.querySelectorAll('#company-list li a .ticker')].map((x) => x.textContent).join() }),
    change: (a, b, mode) => (mode === 'REFRESH' ? b.basis !== a.basis : true) && b.rows === a.rows },
  { name: 'entity', hash: 'entity/COMPANY:nvda', ready: '#content details:has([data-source-original])', details: '#content details:has([data-source-original])', focus: '#content details:has([data-source-original]) > summary',
    read: () => ({ basis: document.getElementById('data-refresh').dataset.refreshBasis }),
    change: (a, b, mode) => mode === 'REFRESH' ? b.basis !== a.basis : true },
];

// ---------- browser helpers ----------
let phase = 'BUILD';
const counts = {};
function ok(label, cond, msg) { assert.ok(cond, '[' + label + '] ' + msg); counts[label] = (counts[label] || 0) + 1; }
function eq(label, a, b, msg) { assert.deepEqual(a, b, '[' + label + '] ' + msg); counts[label] = (counts[label] || 0) + 1; }
async function newContext(browser, state, width) {
  const context = await browser.newContext({ viewport: { width, height: 800 }, serviceWorkers: 'block' });
  await context.clock.setFixedTime(new Date(DAYS[state.day].now));
  await routeEmptyPublicScreens(context);
  // state.gate: the answers wait for it, so the test can read the screen while the bar says '확인 중…' (just before the new set
  // is drawn). The bar's own height change while checking moves the page through the browser's scroll anchoring, not the redraw.
  for (const file of Object.keys(PUB[1])) await context.route('**/' + file + '*', async (r) => { if (state.gate) await state.gate; return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PUB[state.day][file]) }); });
  // Interest companies with 8-K / news on day 1 (amd's items are gone on day 2): the watchlist lists follow the publication.
  await context.addInitScript(() => { try { if (!localStorage.getItem('investment.web.v1.personal')) localStorage.setItem('investment.web.v1.personal', JSON.stringify({ version: 1, interests: ['amd', 'nvda', 'msft'], groups: [] })); } catch (_) {} });
  const page = await context.newPage(); page.setDefaultTimeout(20000);
  const seen = { errors: [], outside: [] };
  page.on('pageerror', (e) => seen.errors.push(String(e)));
  await page.route('**/*', (r) => { const u = new URL(r.request().url()); if (u.origin === ORIGIN) return r.fallback(); seen.outside.push(u.host); return r.abort(); });
  return { context, page, seen };
}
// The view state a user sees: the page position (a heading, link, button or label that starts inside the window, and its height
// in the window: the bar above the screen changes height with its text, so the scroll offset alone is not the position), the
// focused element (by id or its data / href attribute), the details the user opened, the fields the user changed, the view buttons
// of the screen and (companies) how many rows were asked for. Lists whose length follows the publication are not part of it.
const viewState = (page, R, anchor = null) => page.evaluate(([R, anchor]) => {
  const c = document.getElementById('content'), a = document.activeElement, one = (s) => s ? c.querySelector(s) : null;
  // Headings, links, buttons and labels first; a screen with none in the window (a long tree diagram) uses its text blocks.
  const inWindow = (n) => { const r = n.getBoundingClientRect(); return r.height > 0 && r.top >= 0 && r.top < innerHeight; };
  const firstMarks = [...c.querySelectorAll('h1,h2,h3,h4,summary,label,a,button')], marks = anchor && anchor.startsWith('2:') || !anchor && !firstMarks.some(inWindow) ? [...c.querySelectorAll('p,li,dt,dd,pre,svg,figure,section')] : firstMarks;
  const pass = marks === firstMarks ? '1:' : '2:', text = (n) => n.tagName + '|' + n.textContent.trim().slice(0, 30);
  const descOf = (n) => pass + text(n) + '|' + marks.filter((m) => text(m) === text(n)).indexOf(n);
  const at = anchor ? marks.find((n) => descOf(n) === anchor) : marks.find(inWindow);
  const where = (n) => { if (!n || n === document.body) return 'BODY'; return n.tagName + (n.id ? '#' + n.id : '') + ':' + (n.getAttribute('data-13f-view') || n.getAttribute('data-13f-style') || n.getAttribute('href') || (n.hasAttribute('data-13f-style-all') ? 'all' : '')) + ':' + n.textContent.trim().slice(0, 40); };
  const field = (s) => { const n = one(s); return n ? (n.type === 'checkbox' ? n.checked : n.value) : null; };
  return { x: Math.round(scrollX), y: Math.round(scrollY), anchor: at ? { desc: descOf(at), top: Math.round(at.getBoundingClientRect().top) } : null, focus: c.contains(a) ? where(a) : 'OUTSIDE:' + (a && a.tagName),
    caret: a && typeof a.selectionStart === 'number' && c.contains(a) ? [a.selectionStart, a.selectionEnd] : null,
    details: R.details ? one(R.details)?.open ?? null : null, field: R.field ? field(R.field[0]) : null, text: R.text ? field(R.text[0]) : null,
    pressed: [...c.querySelectorAll('[role="group"] button[aria-pressed]:not([data-star]):not([data-investor-star])')].map((b) => (b.id || b.getAttribute('data-13f-view') || b.getAttribute('data-13f-style') || 'all') + '=' + b.getAttribute('aria-pressed')),
    rows: R.more ? document.querySelectorAll('#company-list li').length : null };
}, [{ details: R.details || null, field: R.field || null, text: R.text || null, more: R.more || null }, anchor]);
// Same view: the same element at the same height in the window (±2 px), page not at the top, everything else equal.
function sameView(label, after, before, what) {
  ok(label, after.y > 0, what + ': page not sent to the top (y ' + after.y + ')');
  ok(label, before.anchor && after.anchor && Math.abs(after.anchor.top - before.anchor.top) <= 2, what + ': ' + (before.anchor && before.anchor.desc) + ' stays at ' + (before.anchor && before.anchor.top) + 'px (now ' + (after.anchor && after.anchor.top) + ')');
  const rest = (v) => ({ ...v, y: undefined, anchor: undefined });
  eq(label, rest(after), rest(before), what);
}
const read = (page, R) => page.evaluate(`(${R.read.toString()})()`);
// Old nodes of the screen: a marked node must be gone after the screen was drawn again (no old DOM kept).
const mark = (page) => page.evaluate(() => { window.__oldNodes = [...document.querySelectorAll('#content > *')]; });
const redrawn = (page) => page.evaluate(() => window.__oldNodes.every((n) => !n.isConnected));
async function settle(page) { await page.waitForTimeout(250); }

async function act(page, R, width) {
  if (R.more) { const more = page.locator(R.more); if (await more.isVisible()) await page.evaluate((s) => document.querySelector(s).click(), R.more); }
  if (R.tab) { await page.evaluate((s) => document.querySelector(s).click(), R.tab); }
  if (R.details) await page.evaluate((s) => { const d = document.querySelector(s); d.open = true; }, R.details);
  if (R.field) {
    const [sel, value] = R.field; await page.evaluate(([s, v]) => { const n = document.querySelector(s); const opts = [...n.options].map((o) => o.value); n.value = v !== null && opts.includes(v) ? v : opts[opts.length - 1]; n.dispatchEvent(new Event('change', { bubbles: true })); }, [sel, value]);
  }
  if (R.text) { await page.locator(R.text[0]).fill(R.text[1]); }
  // Focus without scrolling (as a keyboard user who tabbed there), then scroll the page as a reader does.
  await page.evaluate(([s, t]) => { const n = document.querySelector(s); if (!n) throw new Error('no focus target ' + s); n.focus({ preventScroll: true }); if (t && typeof n.setSelectionRange === 'function') n.setSelectionRange(1, 1); }, [R.focus, !!R.text]);
  const y = await page.evaluate(() => { const max = document.documentElement.scrollHeight - innerHeight; return Math.max(0, Math.min(700, Math.floor(max * 0.6))); });
  await page.evaluate((v) => scrollTo(0, v), y);
  await settle(page);
  return y;
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  const only = process.env.VIEW_STATE_ROUTES ? new Set(process.env.VIEW_STATE_ROUTES.split(',')) : null;
  try {
    for (const width of WIDTHS) for (const R of ROUTES) {
      if (only && !only.has(R.name)) continue;
      phase = R.name + ' ' + width + ' OPEN';
      const state = { day: 1 }, { context, page, seen } = await newContext(browser, state, width);
      await page.goto(BASE + '#' + R.hash); await page.locator(R.ready).first().waitFor();
      await page.waitForFunction(() => document.getElementById('data-refresh')?.dataset.refreshBasis);
      await settle(page);
      const y = await act(page, R, width);
      const before = await viewState(page, R);
      ok('SETUP', before.y > 0 && before.y === y && before.anchor, R.name + ' ' + width + ': page scrolled to ' + y + ' (got ' + before.y + ', anchor ' + JSON.stringify(before.anchor) + ')');
      ok('SETUP', before.focus !== 'BODY' && !before.focus.startsWith('OUTSIDE'), R.name + ' ' + width + ': an element of the screen has focus (' + before.focus + ')');
      await page.evaluate(() => { window.__events = []; addEventListener('public-data-updated', (e) => window.__events.push(e.detail.reason)); });

      // (a) '자료 새로고침' with a new publication (day 2).
      phase = R.name + ' ' + width + ' REFRESH';
      let v0 = await read(page, R); await mark(page);
      state.day = 2; await context.clock.setFixedTime(new Date(DAYS[2].now));
      let release; state.gate = new Promise((res) => { release = res; });
      await page.evaluate(() => document.querySelector('#data-refresh [data-refresh-button]').click());
      await page.waitForFunction(() => document.getElementById('data-refresh')?.dataset.refreshState === 'LOADING'); await settle(page);
      const checking = await viewState(page, R, before.anchor.desc);
      ok('SETUP', checking.anchor && Math.abs(checking.anchor.top - before.anchor.top) <= 16, R.name + ' ' + width + ': the bar\'s checking line moves the page by its own height change only (' + JSON.stringify(checking.anchor) + ')');
      state.gate = null; release();
      await page.waitForFunction(() => document.getElementById('data-refresh')?.dataset.refreshState === 'APPLIED');
      await page.waitForFunction(() => window.__oldNodes.every((n) => !n.isConnected));
      await page.waitForFunction(`(() => { const a = ${JSON.stringify(v0)}, b = (${R.read.toString()})(); return (${R.change.toString()})(a, b, 'REFRESH'); })()`, null, { timeout: 10000 }).catch(() => {});
      await settle(page);
      let v1 = await read(page, R), after = await viewState(page, R, before.anchor.desc);
      sameView('REAL_FETCH+HARNESS_CLICK', after, { ...before, anchor: checking.anchor }, R.name + ' ' + width + ': view state kept after a refresh');
      ok('REAL_FETCH+HARNESS_CLICK', await redrawn(page), R.name + ' ' + width + ': the screen was drawn again (no old nodes)');
      ok('REAL_FETCH+HARNESS_CLICK', R.change(v0, v1, 'REFRESH'), R.name + ' ' + width + ': values follow day 2: ' + JSON.stringify(v0) + ' → ' + JSON.stringify(v1));
      eq('REAL_FETCH+HARNESS_CLICK', await page.evaluate(() => publicScreens['sec-qgv2.json'].as_of), DAYS[2].as_of, 'the app holds the day-2 set');

      // (b) the clock passes the rows' own windows: re-judged with no user action and no new publication.
      phase = R.name + ' ' + width + ' REJUDGE';
      v0 = v1; await mark(page);
      const judging = await viewState(page, R, before.anchor.desc);
      await context.clock.setFixedTime(new Date(PAST));
      await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      await page.waitForFunction(() => window.__events.includes('REJUDGE'));
      await page.waitForFunction(() => window.__oldNodes.every((n) => !n.isConnected));
      await page.waitForFunction(`(() => { const a = ${JSON.stringify(v0)}, b = (${R.read.toString()})(); return (${R.change.toString()})(a, b, 'REJUDGE'); })()`, null, { timeout: 10000 }).catch(() => {});
      await settle(page);
      v1 = await read(page, R); after = await viewState(page, R, before.anchor.desc);
      sameView('HARNESS_CLOCK+HARNESS_EVENT', after, { ...before, anchor: judging.anchor }, R.name + ' ' + width + ': view state kept after a re-judgement');
      ok('HARNESS_CLOCK+HARNESS_EVENT', await redrawn(page), R.name + ' ' + width + ': the screen was drawn again (no old nodes)');
      ok('HARNESS_CLOCK+HARNESS_EVENT', R.change(v0, v1, 'REJUDGE'), R.name + ' ' + width + ': values follow the re-judged states: ' + JSON.stringify(v0) + ' → ' + JSON.stringify(v1));
      const judged = await page.evaluate((at) => { const p = publicScreens['sec-qgv2.json'], rows = [...Object.values(p.records), ...Object.values(p.target)]; return { live: rows.filter((r) => r.state === 'LIVE').every((r) => r.acquired_at === at), stale: rows.filter((r) => r.state === 'STALE').length }; }, DAYS[2].as_of);
      ok('HARNESS_CLOCK+HARNESS_EVENT', judged.live && judged.stale > 0, 'the app holds the re-judged rows: only rows collected on day 2 stay LIVE, ' + judged.stale + ' STALE');

      // (c) a screen the user opens still starts at the top, focus on its heading.
      phase = R.name + ' ' + width + ' NAVIGATE';
      const next = R.hash === 'news' ? 'macro' : 'news';
      await page.evaluate((h) => { location.hash = h; }, next); await page.waitForFunction((h) => location.hash === '#' + h && document.querySelector('#content h1'), next);
      await settle(page);
      const nav = await viewState(page, R);
      eq('NAVIGATE', nav.y, 0, R.name + ' ' + width + ' → ' + next + ': opened at the top');
      await page.evaluate((h) => { location.hash = h; }, R.hash); await page.locator(R.ready).first().waitFor(); await settle(page);
      eq('NAVIGATE', (await viewState(page, R)).y, 0, next + ' → ' + R.name + ' ' + width + ': back at the top (not a refresh)');

      eq('REAL_FETCH', seen.errors, [], 'no page errors'); eq('REAL_FETCH', seen.outside.filter((h) => !/tradingview|s3\.tradingview|youtube/.test(h)), [], 'no request outside the local origin');
      console.log('PASS ' + R.name + ' ' + width);
      await context.close();
    }
    console.log('COUNTS ' + Object.entries(counts).map(([k, v]) => k + '=' + v).join(' '));
    console.log('PASS refresh_view_state');
  } catch (e) {
    console.log('FAIL refresh_view_state ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION') + ' ' + e.message);
    process.exitCode = 1;
  } finally { await browser.close(); }
})();
