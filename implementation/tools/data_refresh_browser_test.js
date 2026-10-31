'use strict';
/* '자료 새로고침' (data-refresh.js; FRONTEND_DATA_CONTRACT.md D1, D2, D4, D5, D6). The page is never reloaded in the in-tab checks.
   Every check is labelled by how its input reached the page:
     REAL_FETCH    the page's own requests to the local origin; the test only decides what the server answers (route) — the
                   same path a deployed publication takes. The user presses the real '자료 새로고침' button.
     HARNESS_CLOCK the browser clock is moved by the test (Playwright clock); the data still comes over REAL_FETCH.
     HARNESS_EVENT the test fires the tab's 'visibilitychange' (what a phone does when the app comes back) instead of waiting
                   for the one-minute timer.
     HARNESS_PRICES synthetic device prices (made-up numbers) through a stubbed PrivateSubsetView, a stubbed sheet session that
                   counts reads, and a fake loaded price tab that records the fetch option of every read — all in RAM.
     NODE / STATIC expected values from the engine modules in Node, and source checks.
   Publications (synthetic, price-free; the same two days as update_propagation_browser_test.js):
     day 1 = strict sec-qgv2.json fixture + NYSE:ABT collected 2026-09-30T06:00Z (LIVE until 2026-10-14T06:00Z);
     day 2 = msft and NASDAQ:AKAM re-collected, whole cross-section recomputed, ABT past its 14-day window, the AMD 8-K and news
             item gone, a new yield-curve observation.
   Checked: the open leaderboard follows day 2 in place, every other screen and the calculation inputs show day 2 (one set),
   no Worker / Sheets / outside request, settings unchanged, a failed refresh keeps every old value with '갱신 실패' and the old
   basis time, re-judging makes a row STALE as the clock passes its window (no new publication), the v1 badge names its input,
   and a failed read and a not-published file read differently. With the central V publication (DC-31, synthetic
   qgv-official.json): the D11 official ranking / QG list, the V coverage panel counts and the stat-radar V stay the published
   ones across the refresh (the publication is read again; no device price makes a V), and every price-tab read the refresh causes
   is RAM only (no Worker sync, no Sheets read). */
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const WA = path.join(__dirname, '../src/investment_system/product/web_assets');
globalThis.QgvV2 = require(path.join(WA, 'qgv-v2.js'));
const SQ = globalThis.SecQgv2 = require(path.join(WA, 'sec-qgv2.js'));
const QI = globalThis.Qgv2Inputs = require(path.join(WA, 'qgv2-inputs.js'));
globalThis.MacroLights = require(path.join(WA, 'macro-lights.js'));
const QS = require(path.join(WA, 'qgv-scores.js')), PS = require(path.join(WA, 'public-screens.js'));
const SD = require(path.join(WA, 'sec-disclosures.js')), NS = require(path.join(WA, 'news-signals.js'));
const O = require('./qgv_official_fixture.js'), F = require('./qgv_v2_fixture.js'), secFx = require('./sec_disclosures_fixture.js'), newsFx = require('./news_signals_fixture.js');
const { EMPTY, routeEmptyPublicScreens } = require('./empty_public_screens.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const DAYS = { 1: { as_of: '2026-10-13T22:30:00Z', now: '2026-10-14T03:00:00Z' }, 2: { as_of: '2026-10-14T22:30:00Z', now: '2026-10-15T03:00:00Z' } };
const RECOLLECTED = 'NASDAQ:AKAM', KEPT = 'NASDAQ:ABNB', AGING = 'NYSE:ABT', AGING_AT = '2026-09-30T06:00:00Z', PAST_WINDOW = '2026-10-14T07:00:00Z';
const PRESET = 'growth';
const PUBLIC = new Set(['sec-qgv2.json', 'qgv-official.json', 'sec-public-inputs.json', 'company-classification.json', 'dart-financials.json', 'sec-disclosures.json', 'news-signals.json', 'dart-disclosures.json', 'sec-universe-shares.json', 'macro-evidence.json', ...Object.keys(PS.FILES)]);
const clock = (x) => x.slice(0, 10) + ' ' + x.slice(11, 16) + ' UTC';
const fmt = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
const fmt1 = (v) => (Math.round(v * 10) / 10).toFixed(1);
let phase = 'BUILD';
const counts = {};
function ok(label, cond, msg) { assert.ok(cond, '[' + label + '] ' + msg); counts[label] = (counts[label] || 0) + 1; }
function eq(label, a, b, msg) { assert.deepEqual(a, b, '[' + label + '] ' + msg); counts[label] = (counts[label] || 0) + 1; }

// ---------- the synthetic publications ----------
function recompute(p) {
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version);
  for (const [role, rows] of [['universe', p.records], ['target', p.target]]) for (const [k, r] of Object.entries(rows)) { const s = scores.get(role + '\u0000' + k); if (s) { r.factors = s.factors; r.axes = s.axes; } }
}
function qgv2Day1() { const p = F.strictPayload(); p.records[AGING].acquired_at = AGING_AT; SQ.validate(p); return p; }
function qgv2Day2() {
  const p = qgv2Day1(); p.as_of = DAYS[2].as_of; p.last_shard_index = (p.last_shard_index + 1) % p.shard_count;
  const m = p.target.msft; m.acquired_at = DAYS[2].as_of;
  Object.assign(m.metrics, { roic: 0.5, interest_coverage: 60, net_debt_to_ebitda: -1, dilution_3y: -0.05, revenue_acceleration: 0.2, accruals_to_assets: -0.2 });
  const a = p.records[RECOLLECTED]; a.acquired_at = DAYS[2].as_of;
  for (const k of ['moat_proxy', 'net_debt_to_ebitda', 'interest_coverage', 'dilution_3y', 'incremental_roic_5y']) delete a.metrics[k];
  Object.assign(p.records[AGING], { state: 'STALE', reason_codes: ['STALE_INPUT'] });
  recompute(p); SQ.validate(p); return p;
}
function secDay(n) {
  const p = secFx.payload(Date.parse(DAYS[n].now)); if (n === 1) return p;
  const events = p.events.filter((e) => e.company_id !== 'amd').map((e) => ({ ...e, group_id: null, occurrence: null }));
  SD.groups(events).forEach((g, i) => Object.assign(events[i], g)); return SD.validate({ ...p, events });
}
function newsDay(n, sec) {
  // Day 2: the AMD news item is gone (the fixture regroups the rest and records AMD as answered with nothing new).
  return newsFx.payload(Date.parse(DAYS[n].now), sec, { without: n === 1 ? [] : ['amd'] });
}
const CURVE = { 1: { date: '2026-10-12', ten_year: 4.2, three_month: 4.5, run_days: 25 }, 2: { date: '2026-10-13', ten_year: 4.4, three_month: 4.1, run_days: 0 } };
function macroDay(n) {
  const p = structuredClone(EMPTY['macro-screen.json']), at = DAYS[n].as_of.replace('Z', '+00:00'), A = 'a'.repeat(64), B = (n === 1 ? 'b' : 'c').repeat(64);
  p.as_of = at; p.state = 'LIVE'; p.sources = [{ agency: 'BLS', sha256: A, acquired_at: at }, { agency: 'TREASURY', sha256: B, acquired_at: at }];
  const L = p.data.macro_lights_v1.lights, c = CURVE[n];
  Object.assign(L.employment, { state: 'LIVE', lit: true, reason: 'LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', avg3: 4.6, low12: 4.0, low12_count: 12, gap: 4.6 - 4.0 } });
  Object.assign(L.inflation, { state: 'LIVE', lit: false, reason: 'NOT_LIT', as_of: '2026-09', inputs: [{ sha256: A, acquired_at: at }], values: { period: '2026-09', base_period: '2025-09', yoy: 0.03 } });
  Object.assign(L.curve, { state: 'LIVE', lit: c.run_days >= 20, reason: c.run_days >= 20 ? 'LIT' : 'NOT_LIT', as_of: c.date, inputs: [{ sha256: B, acquired_at: at }], values: { date: c.date, ten_year: c.ten_year, three_month: c.three_month, spread: c.ten_year - c.three_month, run_days: c.run_days } });
  PS.validate('macro-screen.json', JSON.parse(JSON.stringify(p))); return p;
}
// sec-qg-factors.json (v1 PREVIEW input): LIVE, its own 1-day window ends 2026-10-14T06:00Z (same instant as ABT's row window).
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const QG_FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
function qgFactors() {
  const at = '2026-10-13T06:00:00Z', H = (c) => c.repeat(64), companies = {};
  for (const id of IDS) companies[id] = { state: 'NOT_AVAILABLE', source_hashes: {}, factors: Object.fromEntries(QG_FACTORS.map((f) => [f, { score: null, state: 'NOT_AVAILABLE' }])) };
  companies.msft = { state: 'LIVE', source_hashes: { companyfacts: H('a'), submissions: H('b') }, factors: Object.fromEntries(QG_FACTORS.map((f) => [f, { score: 50, state: 'LIVE' }])) };
  const p = { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_COMPANYFACTS', sha256: H('a'), acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: H('b'), acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400, data: { companies, method_status: 'PROVISIONAL_UNCALIBRATED', availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
  PS.validate('sec-qg-factors.json', JSON.parse(JSON.stringify(p))); return p;
}
const PUB = {};
for (const n of [1, 2]) { const sec = secDay(n); PUB[n] = { 'sec-qgv2.json': n === 1 ? qgv2Day1() : qgv2Day2(), 'sec-disclosures.json': sec, 'news-signals.json': newsDay(n, sec), 'macro-screen.json': macroDay(n) }; }
// Day 3 (only served while sec-qgv2.json fails): every other file moves on. None of it may show (all or nothing).
PUB[3] = { ...PUB[2], 'macro-screen.json': macroDay(1) };
const inputsAt = (n, now) => QI.fromInputs(SQ.toInputs(PUB[n]['sec-qgv2.json'], { now }));
// D11 (#318): without device prices there is no official rank; rows with a Q·G total are in the QG reference list (own order).
// D12: the official evaluation = every Universe code of the file once (a TARGET in the Universe is that code's row), TARGET outside
// the Universe never ranked (QgvScores.universeIdentities, the population the leaderboard ranks).
function expectedRanks(n, now, identities, preset = null, quotes = {}) {
  const inputs = inputsAt(n, now), U = QS.universeIdentities(inputs, identities);
  const S = QS.compute({ identities: U.identities, publicScreens: { 'sec-qgv2.json': inputs }, quotes, preset, gate: null, official: U }), out = {};
  for (const [id, r] of Object.entries(S.rows)) if (Number.isInteger(r.rank) || r.qg_reference) out[id] = { rank: Number.isInteger(r.rank) ? r.rank : r.qg_reference.order, list: Number.isInteger(r.rank) ? 'RANKED' : 'QG_REFERENCE', total: fmt1(r.primary.total) };
  return out;
}
function freshExpected(n, code, now) {
  const p = PUB[n]['sec-qgv2.json'], r = p.records[code], st = SQ.restate(r, now, p.stale_after_seconds).state, age = Math.floor((Date.parse(now) - Date.parse(r.acquired_at)) / 864e5);
  return ['출처 sec-qgv2.json', 'as_of ' + clock(p.as_of), '수집 ' + clock(r.acquired_at), '수집 후 ' + age + '일', '상태 ' + st, 'calc_version ' + p.calc_version];
}

// ---------- browser helpers ----------
async function newContext(browser, state, extra = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: 'block' });
  await context.clock.setFixedTime(new Date(state.now || DAYS[state.day].now));
  await routeEmptyPublicScreens(context);
  for (const file of Object.keys(PUB[1])) await context.route('**/' + file + '*', (r) => {
    if (state.fail && state.fail[file]) return r.fulfill({ status: state.fail[file], contentType: 'text/plain', body: 'unavailable' });
    return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PUB[state.day][file]) });
  });
  for (const [file, body] of Object.entries(extra)) await context.route('**/' + file + '*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) }));
  const page = await context.newPage(); page.setDefaultTimeout(20000);
  const seen = { errors: [], outside: [], requests: [] };
  page.on('pageerror', (e) => seen.errors.push(String(e)));
  page.on('request', (q) => seen.requests.push(q.url()));
  await page.route('**/*', (r) => { const u = new URL(r.request().url()); if (u.origin === ORIGIN) return r.fallback(); seen.outside.push(u.host); return r.abort(); });
  return { context, page, seen };
}
async function go(page, hash, selector) { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator(selector).first().waitFor(); }
const readLeaderboard = (page) => page.evaluate(() => ({
  asOf: document.querySelector('[data-score-as-of]')?.textContent || null,
  rows: [...document.querySelectorAll('[data-leaderboard-row]')].map((tr) => ({ id: tr.dataset.leaderboardRow, rank: tr.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank || tr.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]')?.dataset.qgOrder || null,
    list: tr.querySelector('[data-leaderboard-rank]') ? 'RANKED' : tr.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]') ? 'QG_REFERENCE' : null, total: tr.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal || null })),
  scope: (() => { const n = document.querySelector('[data-leaderboard-rank-scope]'); return n ? { ranked: n.dataset.ranked, base: n.dataset.rankBase } : null; })(),
  counts: (() => { const n = document.querySelector('[data-leaderboard-counts]'); return n ? { rankable: n.dataset.rankable, qg: n.dataset.qgReference } : null; })() }));
async function leaderboard(page) { await go(page, 'leaderboard', '[data-leaderboard-table]'); await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-row]').length > 0); return readLeaderboard(page); }
const ranked = (lb) => Object.fromEntries(lb.rows.filter((r) => r.rank !== null).map((r) => [r.id, { rank: Number(r.rank), list: r.list, total: r.total }]));
const readUniverse = (page) => page.evaluate(() => {
  const pg = document.querySelector('[data-universe-page]'), ax = (a) => { const r = document.querySelector('[data-universe-card="qgv"] [data-uc-axis="' + a + '"]'); return { score: r.dataset.ucScore, state: r.dataset.ucAxisState, num: r.querySelector('.num')?.textContent.trim() || null, text: r.textContent }; };
  return { code: pg.dataset.universePage, state: pg.dataset.universeState, Q: ax('Q'), G: ax('G'), fresh: document.querySelector('[data-universe-card="qgv"] [data-uc-fresh]').textContent.split(' · '),
    factors: Object.fromEntries([...document.querySelectorAll('[data-uc-factor]')].map((c) => [c.dataset.ucFactor, c.dataset.ucValue])), read: document.querySelector('[data-uc-read]')?.textContent || null, readState: document.querySelector('[data-uc-read]')?.dataset.ucRead || null };
});
async function universePage(page, code) {
  await go(page, 'company/' + encodeURIComponent(code), '[data-universe-page]');
  await page.waitForFunction((c) => document.querySelector('[data-universe-page]')?.dataset.universePage === c && document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING', code);
  return readUniverse(page);
}
function checkUniverse(label, n, code, now, u) {
  const r = PUB[n]['sec-qgv2.json'].records[code];
  eq(label, u.fresh, freshExpected(n, code, now), code + ' day ' + n + ' freshness line = source as_of / acquired_at / state / calc_version');
  for (const a of ['Q', 'G']) {
    const s = r.axes[a].score;
    if (s === null) eq(label, [u[a].state, u[a].score], ['POLICY_NA', 'NA'], code + ' ' + a + ' policy NA');
    else { ok(label, Math.abs(Number(u[a].score) - s) <= 1e-9, code + ' ' + a + ' ' + u[a].score + ' vs ' + s); eq(label, u[a].num, fmt(s), code + ' ' + a + ' shown number'); }
  }
  for (const [f, v] of Object.entries(r.factors)) { if (v === null) eq(label, u.factors[f], 'NA', code + ' ' + f); else ok(label, Math.abs(Number(u.factors[f]) - v) <= 1e-9, code + ' ' + f); }
}
async function targetPage(page, id) {
  await go(page, 'company/' + id, '[data-company-card="qgv"]'); await page.locator('[data-company-card="qgv"] [data-qgv="Q"]').waitFor();
  return page.evaluate(() => ({ asOf: document.querySelector('[data-company-badges] [data-score-as-of]')?.textContent || null, Q: document.querySelector('[data-company-card="qgv"] [data-qgv="Q"]').textContent.trim(),
    G: document.querySelector('[data-company-card="qgv"] [data-qgv="G"]').textContent.trim(), acquired: document.querySelector('[data-source-acquired]')?.textContent || null,
    rank: document.querySelector('[data-company-card="qgv"] [data-qgv="rank"] .num')?.textContent || document.querySelector('[data-company-card="qgv"] [data-qgv-rank="QG_REFERENCE"]')?.dataset.qgOrder || null,
    v1Stale: [...document.querySelectorAll('[data-company-badges] .badge.freshness.STALE')].map((b) => b.textContent) }));
}
async function treeQgv(page) {
  await go(page, 'tree/qgv', '[data-tree-examples="qgv"] [data-example-state]');
  return page.evaluate(() => { const b = document.querySelector('[data-tree-examples="qgv"] [data-tree-example-body]'); return { code: b.dataset.exampleCode, asOf: b.dataset.exampleAsOf, Q: b.querySelector('[data-example-axis="Q"]')?.textContent }; });
}
async function treeNews(page) {
  await go(page, 'tree/news', '[data-tree-examples="news"] [data-example-source="sec-disclosures.json"]');
  return page.evaluate(() => Object.fromEntries([...document.querySelectorAll('[data-tree-examples="news"] [data-example-source]')].map((d) => [d.dataset.exampleSource, { count: d.dataset.exampleCount, text: d.textContent }])));
}
const timelineKeys = (n) => NS.timeline({ sec: PUB[n]['sec-disclosures.json'], news: PUB[n]['news-signals.json'] }).slice(0, 30).map((r) => r.channel === 'NEWS' ? 'N:' + r.item.group_id : 'D:' + r.event.accession);
async function newsScreen(page) {
  await go(page, 'news', '#news-disclosures [data-timeline] > li');
  return page.evaluate(() => ({ keys: [...document.querySelectorAll('#news-disclosures [data-timeline] > li')].map((x) => x.dataset.news ? 'N:' + x.dataset.news : 'D:' + x.dataset.disclosure), meta: [...document.querySelectorAll('#news-disclosures .meta')].map((m) => m.textContent) }));
}
async function macroCurve(page) {
  await go(page, 'macro', '[data-macro-light="curve"]');
  return page.evaluate(() => { const li = document.querySelector('[data-macro-light="curve"]'); return { state: li.dataset.macroLightState, meta: li.querySelector('.meta').textContent }; });
}
const bar = (page) => page.evaluate(() => { const b = document.getElementById('data-refresh'); return b ? { state: b.dataset.refreshState, basis: b.dataset.refreshBasis, checked: b.dataset.refreshChecked, button: b.querySelector('[data-refresh-button]').textContent,
  line: b.querySelector('[data-refresh-status]').textContent, files: Object.fromEntries([...b.querySelectorAll('[data-refresh-file]')].map((li) => [li.dataset.refreshFile, { state: li.dataset.refreshFileState, text: li.textContent }])) } : null; });
async function press(page, expect) {
  await page.locator('#data-refresh [data-refresh-button]').click();
  await page.waitForFunction((s) => document.getElementById('data-refresh')?.dataset.refreshState === s, expect);
}
// Settings of this tab and device. The leaderboard's remembered scroll position is not a setting: pressing a button at the top
// scrolls the page there, as a user does.
const settings = (page) => page.evaluate(() => ({ local: Object.fromEntries(Object.keys(localStorage).sort().map((k) => [k, localStorage.getItem(k)])),
  session: Object.fromEntries(Object.keys(sessionStorage).sort().map((k) => { let v = sessionStorage.getItem(k); try { const o = JSON.parse(v); if (o && typeof o === 'object' && 'scrollY' in o) { delete o.scrollY; delete o.anchor; delete o.offset; v = JSON.stringify(o); } } catch (_) {} return [k, v]; })),
  profile: JSON.stringify(qgv2Profile), theme: document.documentElement.dataset.theme || null, lang: document.documentElement.lang }));
function requestsCheck(label, reqs, what) {
  const private_ = reqs.filter((u) => /workers\.dev|googleapis|google\.com/.test(u));
  eq(label, private_, [], what + ': no Worker or Google Sheets request');
  const other = reqs.filter((u) => new URL(u).origin !== ORIGIN); eq(label, other, [], what + ': no request outside the local origin');
  const json = reqs.map((u) => new URL(u).pathname.split('/').pop()).filter((f) => f.endsWith('.json'));
  eq(label, json.filter((f) => !PUBLIC.has(f)), [], what + ': only the public publication files are read (' + [...new Set(json)].sort().join(',') + ')');
  return json;
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  const log = (s) => console.log('DATA_REFRESH ' + s);
  try {
    // ---------- static ----------
    phase = 'STATIC';
    const src = fs.readFileSync(path.join(WA, 'data-refresh.js'), 'utf8'), code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
    ok('STATIC', !/\.style\b|style=|setAttribute\(\s*['"]style/.test(code), 'data-refresh.js sets no inline style (CSP)');
    ok('STATIC', !/localStorage|sessionStorage|indexedDB|caches\./.test(code), 'data-refresh.js writes no storage and no Cache Storage');
    ok('STATIC', !/fetch\(/.test(src), 'data-refresh.js starts no request of its own (the readers keep their no-store / no-cache requests)');
    const sw = fs.readFileSync(path.join(WA, 'service-worker.js'), 'utf8'), names = JSON.parse(sw.match(/const NAMES=(\[[^\]]*\])/)[1].replace(/'/g, '"'));
    eq('STATIC', names.filter((x) => x.endsWith('.json')), ['manifest.json'], 'the service worker still pre-caches no data file');
    const html = fs.readFileSync(path.join(WA, 'index.html'), 'utf8');
    ok('STATIC', html.indexOf('src="data-refresh.js"') > 0 && html.indexOf('src="data-refresh.js"') < html.indexOf('src="app.js"'), 'index.html loads data-refresh.js before app.js');

    // ---------- A. a new publication applied by the button, page never reloaded ----------
    const state = { day: 1 };
    const { context, page, seen } = await newContext(browser, state);
    phase = 'A_DAY1';
    await page.addInitScript(() => { if (!sessionStorage.getItem('__seeded')) { sessionStorage.setItem('__seeded', '1'); localStorage.setItem('investment.web.v1.theme', 'dark'); localStorage.setItem('investment.web.v1.candle-style', 'us'); } });
    await page.goto(BASE + '#leaderboard'); await page.locator('[data-leaderboard-table]').waitFor();
    await page.waitForFunction(() => typeof D === 'object' && D !== null && identityCompanies.length > 0 && document.querySelectorAll('[data-leaderboard-row]').length > 0);
    const identities = await page.evaluate(() => JSON.parse(JSON.stringify(identityCompanies)));
    // User settings of this tab: a v2 profile (RAM), a leaderboard sort (sessionStorage), theme and candle colour (localStorage).
    await page.locator('[data-qgv2-preset="' + PRESET + '"]').click();
    await page.waitForFunction((p) => document.querySelector('[data-qgv2-preset="' + p + '"]')?.getAttribute('aria-pressed') === 'true', PRESET);
    await page.locator('#leader-sort').selectOption('name');
    const exp1 = expectedRanks(1, DAYS[1].now, identities, PRESET), exp2 = expectedRanks(2, DAYS[2].now, identities, PRESET);
    ok('NODE', JSON.stringify(exp1) !== JSON.stringify(exp2), 'the two days rank differently with the chosen profile');
    let lb = await readLeaderboard(page);
    eq('REAL_FETCH', [lb.asOf, ranked(lb)], ['점수 기준 ' + DAYS[1].as_of, exp1], 'day 1 leaderboard (profile ' + PRESET + ')');
    let b = await bar(page);
    eq('REAL_FETCH', [b.state, b.basis, b.button], ['IDLE', DAYS[1].as_of, '자료 새로고침'], 'the bar shows the basis of the open publication and the button');
    ok('REAL_FETCH', b.line.includes('점수 기준 ' + DAYS[1].as_of) && b.line.includes('마지막 확인 ' + clock(DAYS[1].now)), 'basis and last-check time: ' + b.line);
    await page.evaluate(() => { window.__sameDocument = true; window.__events = []; addEventListener('public-data-updated', (e) => window.__events.push(JSON.parse(JSON.stringify(e.detail)))); });
    const before = await settings(page);
    eq('REAL_FETCH', [before.local['investment.web.v1.theme'], JSON.parse(before.profile).preset], ['dark', PRESET], 'settings in place before the refresh');

    phase = 'A_PUBLISH_DAY2';
    state.day = 2; await context.clock.setFixedTime(new Date(DAYS[2].now));
    const mark = seen.requests.length;
    await press(page, 'APPLIED');
    await page.waitForFunction((a) => document.querySelector('[data-score-as-of]')?.textContent === '점수 기준 ' + a, DAYS[2].as_of);
    const refreshReqs = seen.requests.slice(mark);
    const read = requestsCheck('REAL_FETCH', refreshReqs, 'refresh');
    for (const f of ['sec-qgv2.json', 'macro-screen.json', 'sec-disclosures.json', 'news-signals.json']) ok('REAL_FETCH', read.includes(f), 'refresh re-read ' + f);
    eq('REAL_FETCH', await page.evaluate(() => window.__sameDocument === true), true, 'no page reload');
    lb = await readLeaderboard(page);
    eq('REAL_FETCH', [lb.asOf, ranked(lb)], ['점수 기준 ' + DAYS[2].as_of, exp2], 'the open leaderboard now shows day 2 in place (profile kept)');
    b = await bar(page);
    eq('REAL_FETCH', [b.state, b.basis], ['APPLIED', DAYS[2].as_of], 'bar: new publication applied');
    ok('REAL_FETCH', b.line.startsWith('새 게시본 적용 · 점수 기준 ' + DAYS[1].as_of + ' → ' + DAYS[2].as_of) && b.line.includes('마지막 확인 ' + clock(DAYS[2].now)), 'bar names old → new basis and the check time: ' + b.line);
    const after = await settings(page);
    eq('REAL_FETCH', after, before, 'settings unchanged: localStorage, sessionStorage, v2 profile, device quotes in RAM, theme, language');
    eq('REAL_FETCH', await page.locator('#leader-sort').inputValue(), 'name', 'the leaderboard sort the user chose is kept');
    // One consistent input set behind every screen and calculation cache.
    const caches = await page.evaluate(() => { const S = leaderScores(), S2 = leaderScores();
      return { file: publicScreens['sec-qgv2.json'].as_of, v2: S.v2_as_of, memo: S.rows === S2.rows || JSON.stringify(S.rows) === JSON.stringify(S2.rows), macro: publicScreens['macro-screen.json'].as_of, pub: DataRefresh.publication().basis,
        ranks: Object.fromEntries(Object.entries(S.rows).filter(([, r]) => Number.isInteger(r.rank) || r.qg_reference).map(([id, r]) => [id, Number.isInteger(r.rank) ? 'R' + r.rank : 'QG' + r.qg_reference.order])), events: window.__events }; });
    eq('REAL_FETCH', [caches.file, caches.v2, caches.pub, caches.macro], [DAYS[2].as_of, DAYS[2].as_of, DAYS[2].as_of, DAYS[2].as_of.replace('Z', '+00:00')], 'publicScreens, the QgvScores result and the publication all carry day 2');
    eq('REAL_FETCH', caches.ranks, Object.fromEntries(Object.entries(exp2).map(([id, x]) => [id, (x.list === 'RANKED' ? 'R' : 'QG') + x.rank])), 'leaderScores (QgvScores memo) recomputed on the new inputs = engine day 2 (rank / QG list)');
    eq('REAL_FETCH', caches.events.length, 1, 'one public-data-updated event');
    const ev = caches.events[0];
    eq('REAL_FETCH', [ev.reason, ev.publication.basis, ev.previous.basis], ['REFRESH', DAYS[2].as_of, DAYS[1].as_of], 'event: reason, new and previous basis');
    // The lists were not read in this tab before (lazy), so they are new reads, not changes of something already shown.
    for (const f of ['sec-qgv2.json', 'macro-screen.json']) ok('REAL_FETCH', ev.changed.includes(f), 'event names the changed file ' + f);
    // Every other screen, reached by navigation inside the same document, shows day 2.
    phase = 'A_SCREENS';
    const t = await targetPage(page, 'msft'), m = PUB[2]['sec-qgv2.json'].target.msft;
    eq('REAL_FETCH', [t.asOf, t.Q, t.G, t.acquired, t.rank], ['점수 기준 ' + DAYS[2].as_of, fmt(m.axes.Q.score), fmt(m.axes.G.score), clock(m.acquired_at), String(exp2.msft.rank)], 'TARGET msft day 2');
    for (const c of [KEPT, RECOLLECTED, AGING]) checkUniverse('REAL_FETCH', 2, c, DAYS[2].now, await universePage(page, c));
    const tq = await treeQgv(page); eq('REAL_FETCH', tq.asOf, DAYS[2].as_of, '1.4 tree example reads day 2');
    const news = await newsScreen(page); eq('REAL_FETCH', news.keys, timelineKeys(2), '4.2 filing / news list = day 2 (AMD items gone)');
    ok('REAL_FETCH', news.meta.some((x) => x.startsWith('SEC 8-K · 기준: ' + PUB[2]['sec-disclosures.json'].as_of)), '4.2 list as_of = day 2');
    const tn = await treeNews(page);
    ok('REAL_FETCH', tn['sec-disclosures.json'].text.includes('파일 기준 ' + PUB[2]['sec-disclosures.json'].as_of) && tn['news-signals.json'].text.includes('파일 기준 ' + PUB[2]['news-signals.json'].as_of), '4.3 tree example shows the same files as the 4.2 list (D6)');
    eq('REAL_FETCH', Number(tn['sec-disclosures.json'].count), PUB[2]['sec-disclosures.json'].events.length, '4.3 example count = day-2 file');
    const mc = await macroCurve(page); eq('REAL_FETCH', [mc.state, mc.meta.endsWith('기준 ' + CURVE[2].date)], ['OFF', true], 'macro curve light = day 2');
    const navReqs = seen.requests.slice(mark).map((u) => new URL(u).pathname.split('/').pop()).filter((f) => ['sec-disclosures.json', 'news-signals.json'].includes(f));
    eq('REAL_FETCH', navReqs.sort(), ['news-signals.json', 'sec-disclosures.json'], 'the lists were read once (by the refresh) and shared by 4.2 and 4.3');

    // ---------- B. a failed refresh keeps every old value ----------
    phase = 'B_FAILED_REFRESH';
    await leaderboard(page);
    state.day = 3; state.fail = { 'sec-qgv2.json': 503 };
    const evCount = (await page.evaluate(() => window.__events.length));
    await press(page, 'FAILED');
    b = await bar(page);
    eq('REAL_FETCH', b.basis, DAYS[2].as_of, 'failed refresh: the basis stays the old one');
    ok('REAL_FETCH', b.line.startsWith('갱신 실패 · 이전 값 유지 · 점수 기준 ' + DAYS[2].as_of) && b.line.includes('sec-qgv2.json 읽기 실패(HTTP 503)'), 'failed refresh says 갱신 실패, the old basis time and the failed file: ' + b.line);
    lb = await readLeaderboard(page);
    eq('REAL_FETCH', [lb.asOf, ranked(lb)], ['점수 기준 ' + DAYS[2].as_of, exp2], 'failed refresh: the leaderboard keeps the day-2 values');
    eq('REAL_FETCH', await page.evaluate(() => [publicScreens['macro-screen.json'].as_of, window.__events.length]), [DAYS[2].as_of.replace('Z', '+00:00'), evCount], 'nothing from the half-read day 3 was applied (macro file kept), no update event');
    const mc3 = await macroCurve(page); eq('REAL_FETCH', mc3.meta.endsWith('기준 ' + CURVE[2].date), true, 'macro screen still day 2 after the failed refresh');
    // The server recovers with the same publication: nothing new.
    state.day = 2; state.fail = null; await leaderboard(page);
    await press(page, 'UNCHANGED');
    b = await bar(page); ok('REAL_FETCH', b.line.startsWith('새 게시본 없음 · 점수 기준 ' + DAYS[2].as_of), 'same publication: 새 게시본 없음 · ' + b.line);
    eq('REAL_FETCH', seen.errors, [], 'no page errors'); eq('REAL_FETCH', seen.outside, [], 'no request outside the local origin');
    await context.close();

    // ---------- C. re-judging as time passes, no new publication ----------
    for (const trigger of ['HARNESS_EVENT', 'BUTTON']) {
      phase = 'C_REJUDGE_' + trigger;
      const st = { day: 1 }, { context: c, page: p, seen: s } = await newContext(browser, st, { 'sec-qg-factors.json': qgFactors() });
      await p.goto(BASE + '#company/msft'); await p.locator('[data-company-card="qgv"] [data-qgv="Q"]').waitFor();
      let tp = await targetPage(p, 'msft');
      eq('REAL_FETCH', tp.v1Stale, [], 'v1 input inside its window: no v1 STALE badge');
      let u = await universePage(p, AGING);
      eq('REAL_FETCH', [u.state, u.fresh[3], u.fresh[4]], ['LIVE', '수집 후 13일', '상태 LIVE'], AGING + ' inside its 14-day window');
      await p.evaluate(() => { window.__sameDocument = true; window.__events = []; addEventListener('public-data-updated', (e) => window.__events.push(JSON.parse(JSON.stringify(e.detail)))); });
      const mark2 = s.requests.length;
      await c.clock.setFixedTime(new Date(PAST_WINDOW));
      if (trigger === 'HARNESS_EVENT') await p.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      else await press(p, 'UNCHANGED');
      await p.waitForFunction(() => document.querySelector('[data-universe-page]')?.dataset.universeState === 'STALE');
      u = await readUniverse(p);
      const label = trigger === 'BUTTON' ? 'REAL_FETCH+HARNESS_CLOCK' : 'HARNESS_EVENT+HARNESS_CLOCK';
      eq(label, u.fresh, freshExpected(1, AGING, PAST_WINDOW), AGING + ' re-judged STALE in place (same publication, its own 14-day rule)');
      eq(label, await p.evaluate(() => window.__sameDocument === true), true, 'no page reload');
      const ev2 = await p.evaluate(() => window.__events);
      eq(label, [ev2.length, ev2[0].reason, ev2[0].publication.basis], [1, 'REJUDGE', DAYS[1].as_of], 'one REJUDGE event, same publication');
      ok(label, ev2[0].changed.includes('sec-qgv2.json') && ev2[0].changed.includes('sec-qg-factors.json'), 'event names the files whose window was passed: ' + ev2[0].changed.join(','));
      const reqs = requestsCheck(label, s.requests.slice(mark2), 're-judge');
      if (trigger === 'HARNESS_EVENT') eq(label, reqs, [], 're-judging by the clock reads nothing');
      const inputsState = await p.evaluate((code) => publicScreens['sec-qgv2.json'].records[code].state, AGING);
      eq(label, inputsState, 'STALE', 'the calculation input row itself is STALE (one input set for every screen)');
      tp = await targetPage(p, 'msft');
      eq(label, tp.v1Stale, ['v1 입력 STALE'], 'the v1 badge past its window names its input (D4), next to the v2 score time');
      eq(label, tp.asOf, '점수 기준 ' + DAYS[1].as_of, 'the v2 score time beside it is unchanged');
      const lbc = await leaderboard(p);
      eq(label, ranked(lbc), expectedRanks(1, PAST_WINDOW, identities), 'leaderboard = engine on the re-judged inputs');
      eq(label, s.errors, [], 'no page errors'); await c.close();
    }

    // ---------- E. with the central V publication: rank / QG list, V panel and radar V stay the published ones ----------
    // DC-31: the synthetic qgv-official.json (qgv_official_fixture.js) is served; a stubbed sheet session counts reads (none may
    // happen) and a fake loaded price tab records the fetch option of every read. No device price makes a V.
    phase = 'E_CENTRAL';
    {
      const st = { day: 1 }, { context: c, page: p, seen: s } = await newContext(browser, st);await O.routeOfficial(c);
      await p.goto(BASE + '#leaderboard'); await p.locator('[data-leaderboard-table]').waitFor();
      await p.evaluate(() => { window.__sheetReads = 0;
        const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { window.__sheetReads++; return { values: [] }; } };
        window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };
        window.__storeCalls = []; const PS = window.PriceStore; window.PriceStore = { ...PS, status: () => ({ ...PS.status(), state: 'READY', tabs: { Prices_D: { present: true, read: true, rows: 0 }, Prices_M: { present: true, read: true, rows: 0 } } }),
          monthEndCloses: async (sym, o) => { window.__storeCalls.push(o && o.fetch); return {}; }, dailyCloses: async (sym, from, o) => { window.__storeCalls.push(o && o.fetch); return {}; } };
        location.hash = 'home'; });
      await p.locator('main').waitFor(); await p.evaluate(() => { location.hash = 'leaderboard'; });
      const settled = (asOf) => p.waitForFunction((a) => publicScreens['sec-qgv2.json'] && publicScreens['sec-qgv2.json'].as_of === a && document.querySelector('[data-v-coverage="READY"]') && document.querySelectorAll('[data-leaderboard-rank]').length > 0, asOf);
      await settled(DAYS[1].as_of);
      const snap = () => p.evaluate(() => { const S = leaderScores(), q = (sel, a) => document.querySelector(sel)?.getAttribute(a) ?? null;
        return { source: S.source, asOf: publicScreens['sec-qgv2.json'].as_of, read: q('[data-v-coverage]', 'data-cx-read-id'),
          rows: Object.fromEntries(Object.values(S.rows).filter((r) => Number.isInteger(r.rank)).map((r) => [r.code, r.rank])),
          dom: [...document.querySelectorAll('[data-leaderboard-rank]')].length, panel: { v: q('[data-v-full]', 'data-v-full'), qg: q('[data-qg-only-full]', 'data-qg-only-full'), ranked: q('[data-v-coverage] [data-ranked]', 'data-ranked') } }; });
      const s1 = await snap(), label = 'REAL_FETCH+CENTRAL';
      eq(label, [s1.source, s1.rows, s1.read], ['PUBLICATION', O.RANKS, O.PUB.publication_id], 'day 1: the official ranks are the published ones (no Universe read, no device price)');
      eq(label, [s1.panel.v, s1.panel.qg, s1.panel.ranked], [String(O.PUB.coverage.v.full), String(O.PUB.coverage.qg_only_total.full), String(O.PUB.coverage.ranked)], 'V panel counts = the publication coverage');
      const opened = await p.evaluate(() => window.__storeCalls.splice(0));
      ok(label, opened.every((x) => x === false), 'a normal screen open reads the price tab stored-only (fetch:false, zero automatic requests): ' + opened.length + ' reads');
      eq(label, s.requests.filter((u) => /workers\.dev/.test(u)), [], 'no Worker request from opening home, the leaderboard and the V panel');
      st.day = 2; await c.clock.setFixedTime(new Date(DAYS[2].now)); const mark3 = s.requests.length, reads0 = await p.evaluate(() => window.__sheetReads);
      await press(p, 'APPLIED'); await settled(DAYS[2].as_of);
      const s2 = await snap();
      const reqs = requestsCheck(label, s.requests.slice(mark3), 'refresh with the central publication (leaderboard open)');
      ok(label, reqs.includes('qgv-official.json'), 'the refresh reads the central V publication again');
      eq(label, await p.evaluate(() => window.__sheetReads), reads0, 'no Google Sheets read during the refresh');
      const during = await p.evaluate(() => window.__storeCalls.splice(0));
      ok(label, during.every((x) => x === false), 'every price-tab read caused by the refresh is RAM only (fetch:false, no Worker sync): ' + during.length + ' reads');
      eq(label, [s2.asOf, s2.source, s2.rows, s2.panel], [DAYS[2].as_of, 'PUBLICATION', O.RANKS, s1.panel], 'after the refresh: day-2 Q·G inputs, the same published ranks and coverage (a new score file never changes the central V)');
      // Radar V on a Universe page = the published V of that code.
      const code = 'NYSE:AFL', pubV = O.PUB.rows[code].axes.V.score;
      await go(p, 'company/' + encodeURIComponent(code), '[data-universe-page] [data-stat-radar]');
      await p.waitForFunction(() => { const c2 = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]'); return c2 && c2.dataset.srReason !== 'PENDING'; });
      const rv = await p.evaluate(() => { const cell = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]'); return { score: Number(cell.dataset.srScore), central: document.querySelector('[data-stat-radar]').dataset.srCentral }; });
      ok(label, rv.central === 'PUBLICATION' && Math.abs(rv.score - pubV) <= 1e-9, 'radar V on the Universe page = the published V (' + rv.score + ' vs ' + pubV + ')');
      await go(p, 'leaderboard', '[data-leaderboard-table]');
      ok(label, !reqs.some((f) => /^prices?/i.test(f)), 'no price file read');
      // The explicit button still requests: with the real price store on (synthetic sheet session that records history
      // requests, no network), opening a Universe company page asks for nothing; its '이 종목 월말 종가 받기' button asks once.
      const sym = KEPT.slice(KEPT.indexOf(':') + 1);
      await p.evaluate(() => { window.__historyCalls = []; localStorage.setItem('investment.web.v1.price-store-enabled', '1'); localStorage.setItem('investment.web.v1.unified-sheet-source', 'syntheticRefreshSheetIdForClickOnlyCheck0001');
        localStorage.setItem('investment.web.v1.private-history-origin', InvestmentAppConfig.privateHistoryWorkerOrigin);
        const session = GoogleSheetQuotes.sessionFor(); session.sheetTitles = async () => ['Prices_D', 'Prices_M']; session.addTabs = async () => ({}); session.appendRows = async () => ({});
        session.fetchHistory = async (origin, symbol, range) => { window.__historyCalls.push([symbol, range]); throw new Error('HISTORY_UNAVAILABLE'); }; });
      await go(p, 'company/' + encodeURIComponent(KEPT), '[data-price-store-company="READY"]');
      await p.waitForTimeout(300);
      eq('HARNESS_PRICES', await p.evaluate(() => window.__historyCalls), [], 'opening the company page with the price store on makes no history request');
      await p.locator('[data-price-store-company-fetch]').click();
      await p.waitForFunction(() => window.__historyCalls.length > 0);
      eq('HARNESS_PRICES', await p.evaluate(() => window.__historyCalls), [[sym, '5y']], 'the explicit button requests the 5-year month-ends once');
      await p.locator('[data-price-store-company="HISTORY_UNAVAILABLE"]').waitFor();
      eq(label, s.errors, [], 'no page errors'); await c.close();
    }

    // ---------- D. failed read vs not published (page open) ----------
    phase = 'D_READ_STATUS';
    const said = {};
    for (const status of [404, 503]) {
      const st = { day: 2, fail: { 'sec-qgv2.json': status } }, { context: c, page: p, seen: s } = await newContext(browser, st);
      await p.goto(BASE + '#leaderboard'); await p.locator('[data-leaderboard-table]').waitFor();
      const ranks = await p.evaluate(() => document.querySelectorAll('[data-leaderboard-rank]').length);
      eq('REAL_FETCH', ranks, 0, 'HTTP ' + status + ': no rank and no old value');
      const u = await universePage(p, KEPT), bb = await bar(p);
      said[status] = { page: u.read, pageState: u.readState, bar: bb.files['sec-qgv2.json'] };
      eq('REAL_FETCH', u.state, 'NO_FILE', 'HTTP ' + status + ': company page has no file');
      eq(st.fail['sec-qgv2.json'] === 404 ? 'REAL_FETCH' : 'REAL_FETCH', said[status].pageState, status === 404 ? 'NOT_PUBLISHED' : 'FAILED', 'HTTP ' + status + ': read state on the company page');
      eq('REAL_FETCH', said[status].bar.state, status === 404 ? 'NOT_PUBLISHED' : 'FAILED', 'HTTP ' + status + ': read state in the bar');
      eq('REAL_FETCH', s.errors, [], 'no page errors'); await c.close();
    }
    eq('REAL_FETCH', said[404].page, '아직 게시되지 않음(HTTP 404)', 'not published: its own words');
    eq('REAL_FETCH', said[503].page, '읽기 실패(HTTP 503)', 'failed read: its own words');
    ok('REAL_FETCH', said[404].bar.text !== said[503].bar.text && !said[404].bar.text.includes('실패') && said[503].bar.text.includes('읽기 실패'), 'the bar never uses the same words for both: ' + said[404].bar.text + ' | ' + said[503].bar.text);
    log('READ_STATUS 404="' + said[404].page + '" 503="' + said[503].page + '"');

    const total = Object.values(counts).reduce((a, x) => a + x, 0);
    log('CHECKS ' + Object.entries(counts).map(([k, v]) => k + '=' + v).join(' '));
    console.log('DATA_REFRESH_BROWSER_OK checks=' + total);
  } catch (e) { console.error('DATA_REFRESH_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
