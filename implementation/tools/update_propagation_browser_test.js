'use strict';
/* Update propagation (FRONTEND_DATA_CONTRACT.md §6): two consecutive synthetic publication days are served by route on the same
   build, and every screen element that depends on a public file must follow the file, with no day-1 value left anywhere.
   Day 1 = the strict synthetic sec-qgv2.json (qgv_v2_fixture.strictPayload) + one row collected 2026-09-30 (still LIVE).
   Day 2 = day 1 after one more daily run, built the way universe/sec_qgv2.merge publishes it:
     - as_of +1 day, last_shard_index +1;
     - TARGET msft re-collected (acquired_at = day-2 as_of) with better SEC metrics -> leaderboard rank 3 -> 1;
     - Universe NASDAQ:AKAM re-collected without five Q sub-metrics -> Q policy NA (AXIS_COVERAGE_BELOW_50), never a number;
     - every factor and axis recomputed over the whole cross-section (SecQgv2.scoreRows), so NASDAQ:ABNB, NOT re-collected,
       gets a new Q percentile while its acquired_at stays the day-1 time (collection scope != recomputation scope);
     - NYSE:ABT crosses the file's own stale_after_seconds (14 days) -> STALE without any new collection;
     - sec-disclosures.json / news-signals.json one day later with the AMD 8-K and the AMD news item gone;
     - macro-screen.json with a new yield-curve observation (employment and inflation unchanged: no new release).
   Checked after a fresh load of day 2: leaderboard order, ranks and totals; TARGET and Universe504 company pages; the 1.4 tree
   example; the radar Q/G vertex when stat-radar.js is on the page (PR #311, pending merge: skipped and logged otherwise); every
   shown as_of / acquired_at / state / calc_version EQUAL to the source values (not just present); STALE; the policy-NA reason
   without a number; the filing / news list; the macro light; no day-1 value anywhere it should have changed. Also: the
   in-tab (SPA) behaviour after a publication, a failed reload (no old value shown as current), Korean names and personal
   settings never changing an official rank or score, and the service-worker / fetch cache rule (statically and with a real
   service worker). The browser clock is fixed per day. Synthetic only: no prices, no network outside the local origin. */
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const WA = path.join(__dirname, '../src/investment_system/product/web_assets');
globalThis.QgvV2 = require(path.join(WA, 'qgv-v2.js'));
const SQ = globalThis.SecQgv2 = require(path.join(WA, 'sec-qgv2.js'));
const QI = globalThis.Qgv2Inputs = require(path.join(WA, 'qgv2-inputs.js'));
globalThis.MacroLights = require(path.join(WA, 'macro-lights.js'));
const QS = require(path.join(WA, 'qgv-scores.js')), PS = require(path.join(WA, 'public-screens.js'));
const SD = require(path.join(WA, 'sec-disclosures.js')), NS = require(path.join(WA, 'news-signals.js'));
const F = require('./qgv_v2_fixture.js'), secFx = require('./sec_disclosures_fixture.js'), newsFx = require('./news_signals_fixture.js');
const { EMPTY, routeEmptyPublicScreens } = require('./empty_public_screens.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const DAYS = { 1: { as_of: '2026-10-13T22:30:00Z', now: '2026-10-14T03:00:00Z' }, 2: { as_of: '2026-10-14T22:30:00Z', now: '2026-10-15T03:00:00Z' } };
const RECOLLECTED = 'NASDAQ:AKAM', KEPT = 'NASDAQ:ABNB', AGING = 'NYSE:ABT', AGING_AT = '2026-09-30T06:00:00Z';
const clock = (x) => x.slice(0, 10) + ' ' + x.slice(11, 16) + ' UTC';
const fmt = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
const fmt1 = (v) => (Math.round(v * 10) / 10).toFixed(1);
let phase = 'BUILD', checks = 0, radarLogged = false, radarChecks = 0;
const ok = (cond, msg) => { assert.ok(cond, msg); checks++; };
const eq = (a, b, msg) => { assert.deepEqual(a, b, msg); checks++; };

// ---------- the two synthetic publications ----------
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
  const p = newsFx.payload(Date.parse(DAYS[n].now), sec); if (n === 1) return p;
  const items = p.items.filter((i) => i.company_id !== 'amd').map((i) => i.relation === 'RELATED_TO_8K' ? { ...i, occurrence: null } : { ...i, group_id: null, occurrence: null });
  NS.groups(items).forEach((g, i) => Object.assign(items[i], g)); return NS.validate({ ...p, items });
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
const PUB = {};
for (const n of [1, 2]) { const sec = secDay(n); PUB[n] = { 'sec-qgv2.json': n === 1 ? qgv2Day1() : qgv2Day2(), 'sec-disclosures.json': sec, 'news-signals.json': newsDay(n, sec), 'macro-screen.json': macroDay(n) }; }
// Expected values, from the engine modules in Node over the same payloads and the same fixed clock (independent of the page).
function inputsOf(n) { return QI.fromInputs(SQ.toInputs(PUB[n]['sec-qgv2.json'], { now: DAYS[n].now })); }
function expectedRanks(n, identities) {
  const S = QS.compute({ identities, publicScreens: { 'sec-qgv2.json': inputsOf(n) } }), out = {};
  for (const [id, r] of Object.entries(S.rows)) if (Number.isInteger(r.rank)) out[id] = { rank: r.rank, total: fmt1(r.primary.total), q: r.primary.q, g: r.primary.g };
  return out;
}

// ---------- browser helpers ----------
async function newContext(browser, state, { sw = 'block', names = null } = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: sw });
  await context.clock.setFixedTime(new Date(DAYS[state.day].now));
  await routeEmptyPublicScreens(context);
  for (const file of Object.keys(PUB[1])) await context.route('**/' + file + '*', (r) => {
    if (state.fail && state.fail.includes(file)) return r.fulfill({ status: 503, contentType: 'text/plain', body: 'unavailable' });
    return r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PUB[state.day][file]) });
  });
  if (names) await context.route('**/company-names-ko.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(names) }));
  const page = await context.newPage(); page.setDefaultTimeout(20000); const seen = { errors: [], outside: [] };
  page.on('pageerror', (e) => seen.errors.push(String(e)));
  await page.route('**/*', (r) => { const u = new URL(r.request().url()); if (u.origin === ORIGIN) return r.fallback(); seen.outside.push(u.host); return r.abort(); });
  return { context, page, seen };
}
async function go(page, hash, selector) { await page.evaluate((h) => { location.hash = h; }, hash); await page.locator(selector).first().waitFor(); }
async function leaderboard(page) {
  await go(page, 'leaderboard', '[data-leaderboard-table]');
  await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-row]').length > 0);
  return page.evaluate(() => ({
    asOf: document.querySelector('[data-score-as-of]')?.textContent || null,
    rows: [...document.querySelectorAll('[data-leaderboard-row]')].map((tr) => ({ id: tr.dataset.leaderboardRow, rank: tr.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank || null,
      total: tr.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal || null, name: tr.querySelector('[data-leaderboard-name]')?.textContent.trim() || null })),
    footnote: [...document.querySelectorAll('[data-leaderboard-screen] p.small')].map((p) => p.textContent).find((t) => t.startsWith('— = NOT_AVAILABLE')) || '' }));
}
function ranked(lb) { return Object.fromEntries(lb.rows.filter((r) => r.rank !== null).map((r) => [r.id, { rank: Number(r.rank), total: r.total }])); }
async function universePage(page, code) {
  await go(page, 'company/' + encodeURIComponent(code), '[data-universe-page]');
  await page.waitForFunction((c) => document.querySelector('[data-universe-page]')?.dataset.universePage === c && document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING', code);
  return page.evaluate(() => {
    const pg = document.querySelector('[data-universe-page]'), ax = (a) => { const r = document.querySelector('[data-universe-card="qgv"] [data-uc-axis="' + a + '"]'); return { score: r.dataset.ucScore, state: r.dataset.ucAxisState, num: r.querySelector('.num')?.textContent.trim() || null, text: r.textContent }; };
    return { state: pg.dataset.universeState, reason: pg.dataset.universeReason, Q: ax('Q'), G: ax('G'), fresh: document.querySelector('[data-universe-card="qgv"] [data-uc-fresh]').textContent.split(' · '),
      factors: Object.fromEntries([...document.querySelectorAll('[data-uc-factor]')].map((c) => [c.dataset.ucFactor, c.dataset.ucValue])),
      radar: ['q', 'g'].map((a) => document.querySelector('[data-universe-card="radar"] tr[data-sr-axis="' + a + '"] [data-sr-series="company"]')?.dataset.srScore).filter((x) => x !== undefined), text: pg.textContent };
  });
}
function freshExpected(n, code) {
  const p = PUB[n]['sec-qgv2.json'], r = p.records[code], st = SQ.restate(r, DAYS[n].now, p.stale_after_seconds).state, age = Math.floor((Date.parse(DAYS[n].now) - Date.parse(r.acquired_at)) / 864e5);
  return ['출처 sec-qgv2.json', 'as_of ' + clock(p.as_of), '수집 ' + clock(r.acquired_at), '수집 후 ' + age + '일', '상태 ' + st, 'calc_version ' + p.calc_version];
}
function checkUniverse(n, code, u) {
  const r = PUB[n]['sec-qgv2.json'].records[code];
  eq(u.fresh, freshExpected(n, code), code + ' day ' + n + ' freshness line equals the source as_of / acquired_at / state / calc_version');
  eq(u.state, freshExpected(n, code)[4].slice(3), code + ' page state');
  for (const a of ['Q', 'G']) {
    const s = r.axes[a].score;
    if (s === null) { eq([u[a].state, u[a].score], ['POLICY_NA', 'NA'], code + ' ' + a + ' policy NA'); ok(/정책상 NA/.test(u[a].text) && !/\d+[.,]\d/.test(u[a].num || ''), code + ' ' + a + ' NA has a reason and no number'); }
    else { eq(u[a].state, 'SCORED'); ok(Math.abs(Number(u[a].score) - s) <= 1e-9, code + ' ' + a + ' ' + u[a].score + ' vs ' + s); eq(u[a].num, fmt(s), code + ' ' + a + ' shown number'); }
  }
  for (const [f, v] of Object.entries(r.factors)) { if (v === null) eq(u.factors[f], 'NA', code + ' ' + f); else ok(Math.abs(Number(u.factors[f]) - v) <= 1e-9, code + ' ' + f + ' ' + u.factors[f] + ' vs ' + v); }
  if (u.radar.length !== 2 && !radarLogged) { radarLogged = true; console.log('UPDATE_PROPAGATION RADAR_ABSENT stat-radar.js not on this build (PR #311 pending merge): radar Q/G vertex checks skipped'); }
  if (u.radar.length === 2) { radarChecks++; for (const [i, a] of ['Q', 'G'].entries()) { const s = r.axes[a].score; if (s === null) eq(u.radar[i], 'NA', 'radar ' + a + ' NA'); else ok(Math.abs(Number(u.radar[i]) - s) <= 1e-9, 'radar ' + a + ' vertex ' + u.radar[i] + ' vs ' + s); } }
}
async function targetPage(page, id) {
  await go(page, 'company/' + id, '[data-company-card="qgv"]');
  await page.locator('[data-company-card="qgv"] [data-qgv="Q"]').waitFor();
  return page.evaluate(() => ({ asOf: document.querySelector('[data-company-badges] [data-score-as-of]')?.textContent || null, Q: document.querySelector('[data-company-card="qgv"] [data-qgv="Q"]').textContent.trim(),
    G: document.querySelector('[data-company-card="qgv"] [data-qgv="G"]').textContent.trim(), total: document.querySelector('[data-company-card="qgv"] [data-qgv="total"]').textContent.trim(),
    rank: document.querySelector('[data-company-card="qgv"] [data-qgv="rank"] .num')?.textContent || null, acquired: document.querySelector('[data-source-acquired]')?.textContent || null,
    used: document.querySelector('[data-source-used]')?.textContent || null }));
}
async function treeExample(page) {
  await go(page, 'tree/qgv', '[data-tree-examples="qgv"] [data-example-state]');
  return page.evaluate(() => { const b = document.querySelector('[data-tree-examples="qgv"] [data-tree-example-body]');
    return { code: b.dataset.exampleCode, asOf: b.dataset.exampleAsOf, Q: b.querySelector('[data-example-axis="Q"]')?.textContent, G: b.querySelector('[data-example-axis="G"]')?.textContent, field: b.querySelector('[data-example-field="as_of"]')?.textContent,
      values: Object.fromEntries([...b.querySelectorAll('[data-example-factor]')].map((tr) => [tr.dataset.exampleFactor, tr.querySelector('[data-example-value]').textContent])) }; });
}
function checkTree(n, t) {
  const inputs = inputsOf(n), code = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).sort().find((c) => { const r = inputs.records[c]; return r.state === 'LIVE' && r.in_cross_section && Number.isFinite(r.qg_axes?.Q?.score) && Number.isFinite(r.qg_axes?.G?.score); });
  const r = inputs.records[code], ax = (a) => fmt1(r.qg_axes[a].score) + (r.qg_axes[a].peer_basis ? ' · ' + r.qg_axes[a].peer_basis + (Number.isInteger(r.qg_axes[a].peer_count) ? ' ' + r.qg_axes[a].peer_count : '') : '');
  eq([t.code, t.asOf, t.Q, t.G], [code, PUB[n]['sec-qgv2.json'].as_of, ax('Q'), ax('G')], '1.4 tree example day ' + n);
  eq(t.field, PUB[n]['sec-qgv2.json'].as_of + ' · 수집 ' + r.acquired_at + ' · FY ' + r.fiscal_year_end, '1.4 tree example as_of / acquired / FY');
  for (const [f, v] of Object.entries(r.factors)) eq(t.values[f], v === null ? 'NA' : fmt1(v), '1.4 tree ' + f);
  return { code, r };
}
const timelineKeys = (n) => NS.timeline({ sec: PUB[n]['sec-disclosures.json'], news: PUB[n]['news-signals.json'] }).slice(0, 30).map((r) => r.channel === 'NEWS' ? 'N:' + r.item.group_id : 'D:' + r.event.accession);
async function newsScreen(page) {
  await go(page, 'news', '#news-disclosures [data-timeline] > li');
  return page.evaluate(() => ({ keys: [...document.querySelectorAll('#news-disclosures [data-timeline] > li')].map((x) => x.dataset.news ? 'N:' + x.dataset.news : 'D:' + x.dataset.disclosure),
    meta: [...document.querySelectorAll('#news-disclosures .meta')].map((m) => m.textContent), stale: document.querySelectorAll('#news-disclosures [data-disclosure-stale]').length }));
}
async function macroScreen(page) {
  await go(page, 'macro', '[data-macro-light="curve"]');
  return page.evaluate(() => Object.fromEntries([...document.querySelectorAll('[data-macro-light]')].map((li) => [li.dataset.macroLight, { state: li.dataset.macroLightState, detail: li.querySelector('[data-macro-light-detail]').textContent, meta: li.querySelector('.meta').textContent }])));
}
function checkMacro(n, m) {
  const c = CURVE[n], lit = c.run_days >= 20;
  eq(m.curve.state, lit ? 'ON' : 'OFF', 'curve light day ' + n);
  ok(m.curve.detail.endsWith('(' + c.date + ')') && m.curve.detail.includes(c.ten_year.toFixed(2) + '%') && m.curve.detail.includes(c.run_days + '거래일'), 'curve detail day ' + n + ': ' + m.curve.detail);
  ok(m.curve.meta.endsWith('기준 ' + c.date), 'curve observation date day ' + n + ': ' + m.curve.meta);
  for (const name of ['employment', 'inflation']) ok(m[name].meta.endsWith('기준 2026-09'), name + ' keeps its release period (no new release)');
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  const log = (s) => console.log('UPDATE_PROPAGATION ' + s);
  try {
    // ---------- static: the update/cache rule (service worker caches no data; every data fetch bypasses the HTTP cache) ----------
    phase = 'STATIC_CACHE_RULE';
    const sw = fs.readFileSync(path.join(WA, 'service-worker.js'), 'utf8'), pwa = fs.readFileSync(path.join(WA, 'pwa.js'), 'utf8');
    const names = JSON.parse(sw.match(/const NAMES=(\[[^\]]*\])/)[1].replace(/'/g, '"'));
    eq(names.filter((x) => x.endsWith('.json')), ['manifest.json'], 'the service worker pre-caches no data file');
    ok(/if\(!STATIC\.has\(url\.href\)\)return;/.test(sw), 'any other request (all public JSON) goes to the network untouched');
    ok(/updateViaCache:'none'/.test(pwa), 'the worker script itself is never served from the HTTP cache');
    for (const file of fs.readdirSync(WA).filter((f) => f.endsWith('.js') && !['service-worker.js', 'google-sheet-quotes.js'].includes(f))) {
      const src = fs.readFileSync(path.join(WA, file), 'utf8');
      for (const m of src.matchAll(/fetch\(/g)) { const call = src.slice(m.index, m.index + 200); ok(/cache:\s*['"]no-(store|cache)['"]/.test(call), file + ' fetch without no-store / no-cache: ' + call.slice(0, 80)); }
    }
    // ---------- sanity of the synthetic days (Node, engine modules) ----------
    phase = 'SYNTHETIC_DAYS';
    const d1 = PUB[1]['sec-qgv2.json'], d2 = PUB[2]['sec-qgv2.json'];
    ok(d2.records[KEPT].acquired_at === d1.records[KEPT].acquired_at && d2.records[KEPT].axes.Q.score !== d1.records[KEPT].axes.Q.score, 'a row that was not re-collected keeps acquired_at while its percentile moves');
    ok(d1.records[RECOLLECTED].axes.Q.score !== null && d2.records[RECOLLECTED].axes.Q.score === null && d2.records[RECOLLECTED].axes.Q.reason_codes.includes('AXIS_COVERAGE_BELOW_50'), 'policy NA flip');
    eq([SQ.restate(d1.records[AGING], DAYS[1].now, d1.stale_after_seconds).state, SQ.restate(d2.records[AGING], DAYS[2].now, d2.stale_after_seconds).state], ['LIVE', 'STALE'], 'aging row');
    ok(PUB[1]['sec-disclosures.json'].events.some((e) => e.company_id === 'amd') && !PUB[2]['sec-disclosures.json'].events.some((e) => e.company_id === 'amd'), 'filing removed on day 2');

    // ---------- day 1, then a new publication while the tab stays open, then a reload ----------
    const state = { day: 1, fail: null };
    const { context, page, seen } = await newContext(browser, state);
    phase = 'DAY1_LOAD'; await page.goto(BASE + '#home'); await page.locator('main').waitFor();
    await page.waitForFunction(() => typeof D === 'object' && D !== null && Array.isArray(identityCompanies) && identityCompanies.length > 0);
    const identities = await page.evaluate(() => JSON.parse(JSON.stringify(identityCompanies)));
    ok(identities.length > 3, 'identities read from the served catalog');
    const exp = { 1: expectedRanks(1, identities), 2: expectedRanks(2, identities) };
    eq(Object.entries(exp[1]).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id).slice(0, 3), ['nvda', 'amd', 'msft'], 'day-1 order (engine)');
    eq(Object.entries(exp[2]).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id).slice(0, 3), ['msft', 'nvda', 'amd'], 'day-2 order (engine)');
    const seenDay = {};
    async function checkDay(n, label) {
      phase = label + ' LEADERBOARD'; const lb = await leaderboard(page);
      eq(lb.asOf, '점수 기준 ' + PUB[n]['sec-qgv2.json'].as_of, 'leaderboard score time = file as_of');
      eq(ranked(lb), Object.fromEntries(Object.entries(exp[n]).map(([id, x]) => [id, { rank: x.rank, total: x.total }])), 'leaderboard ranks and totals day ' + n);
      eq(lb.rows.filter((r) => r.rank !== null).map((r) => r.id), Object.entries(exp[n]).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id), 'leaderboard order day ' + n);
      const scope = (lb.footnote.match(/(\d+)개 기업 전체 기준 순위/) || [])[1];
      if (scope !== String(identities.length)) log('GAP hard-coded rank scope in the leaderboard note: shows ' + scope + ', identities ' + identities.length);
      seenDay[n] = { lb };
      phase = label + ' TARGET msft'; const t = await targetPage(page, 'msft'), m = PUB[n]['sec-qgv2.json'].target.msft;
      eq([t.asOf, t.Q, t.G, t.acquired, t.rank], ['점수 기준 ' + PUB[n]['sec-qgv2.json'].as_of, fmt(m.axes.Q.score), fmt(m.axes.G.score), clock(m.acquired_at), String(exp[n].msft.rank)], 'TARGET msft page day ' + n);
      for (const code of [KEPT, RECOLLECTED, AGING]) { phase = label + ' UNIVERSE ' + code; checkUniverse(n, code, await universePage(page, code)); }
      phase = label + ' TREE'; seenDay[n].tree = checkTree(n, await treeExample(page));
      phase = label + ' NEWS'; const news = await newsScreen(page), sec = PUB[n]['sec-disclosures.json'], nw = PUB[n]['news-signals.json'];
      eq(news.keys, timelineKeys(n), 'news / filings list day ' + n);
      ok(news.meta.some((x) => x.startsWith('SEC 8-K · 기준: ' + sec.as_of + ' ·')) && news.meta.some((x) => x.startsWith('뉴스·신호 · 기준: ' + nw.as_of + ' ·')), 'news as_of = file as_of day ' + n + ': ' + news.meta.join(' | '));
      eq(news.stale, 0, 'fresh news files are not STALE');
      seenDay[n].news = news;
      phase = label + ' MACRO'; checkMacro(n, await macroScreen(page));
    }
    await checkDay(1, 'DAY1');
    // A new publication is deployed while this tab stays open (clock moves to day 2, routes now serve day 2).
    phase = 'SPA_AFTER_PUBLICATION'; state.day = 2; await context.clock.setFixedTime(new Date(DAYS[2].now));
    const spa = await leaderboard(page), spaDay = spa.asOf === '점수 기준 ' + DAYS[2].as_of ? 2 : 1;
    eq(ranked(spa), ranked(seenDay[spaDay].lb), 'SPA re-render shows one consistent snapshot (as_of and ranks of the same day)');
    const spaNews = await newsScreen(page), spaNewsDay = spaNews.meta.some((x) => x.includes(PUB[2]['sec-disclosures.json'].as_of)) ? 2 : 1;
    eq(spaNews.keys, timelineKeys(spaNewsDay), 'SPA news list matches its own as_of (day ' + spaNewsDay + ')');
    log('SPA_REFRESH qgv=' + (spaDay === 2 ? 'REFETCHED' : 'KEPT_UNTIL_RELOAD') + ' news=' + (spaNewsDay === 2 ? 'REFETCHED' : 'KEPT_UNTIL_RELOAD'));
    {
      const u = await universePage(page, AGING), st = u.state, age = u.fresh.find((x) => x.startsWith('수집 후 '));
      if (spaDay === 1 && st === 'LIVE') log('GAP in-tab state frozen at load: ' + AGING + ' shows 상태 LIVE with ' + age + ' after the 14-day window (reload restates it)');
    }
    phase = 'DAY2_RELOAD'; await page.reload(); await page.locator('main').waitFor();
    await checkDay(2, 'DAY2');
    // Nothing still shows a day-1 value where the data changed.
    phase = 'NO_DAY1_LEFT';
    ok(!seenDay[2].lb.rows.some((r) => r.id === 'msft' && r.total === exp[1].msft.total), 'msft day-1 total gone');
    eq(seenDay[2].tree.code, seenDay[1].tree.code, 'same example row both days');
    ok(seenDay[2].tree.r.qg_axes.Q.score !== seenDay[1].tree.r.qg_axes.Q.score, 'the example row value moved with the recomputation');
    ok(!seenDay[2].news.keys.some((k) => PUB[1]['sec-disclosures.json'].events.some((e) => e.company_id === 'amd' && k === 'D:' + e.accession)), 'removed filing gone');
    {
      const u = await universePage(page, KEPT), d1q = fmt(d1.records[KEPT].axes.Q.score);
      ok(u.Q.num !== d1q && !u.text.includes('as_of ' + clock(DAYS[1].as_of)), 'no day-1 Q / as_of on the kept row page');
      eq(u.fresh[2], '수집 ' + clock(DAYS[1].as_of), 'the kept row still says when it was really collected (day 1)');
    }
    eq(seen.errors, [], 'no page errors'); eq(seen.outside, [], 'no request outside the local origin');
    await context.close();

    // ---------- a reload where the new file fails: no old value is shown as current ----------
    phase = 'FAILED_RELOAD';
    {
      const st = { day: 2, fail: ['sec-qgv2.json'] }, { context: c, page: p, seen: s } = await newContext(browser, st);
      await p.goto(BASE + '#leaderboard'); await p.locator('[data-leaderboard-table]').waitFor();
      const lb = await p.evaluate(() => ({ asOf: document.querySelector('[data-score-as-of]')?.dataset.scoreAsOf, ranks: document.querySelectorAll('[data-leaderboard-rank]').length, v2: document.querySelector('[data-qgv2-state]')?.textContent || '' }));
      eq([lb.asOf, lb.ranks], ['NOT_AVAILABLE', 0], 'failed file: no score time and no rank');
      log('FAILED_RELOAD leaderboard says: ' + lb.v2);
      await go(p, 'company/' + encodeURIComponent(KEPT), '[data-universe-page]');
      await p.waitForFunction(() => document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING');
      const u = await p.evaluate(() => ({ state: document.querySelector('[data-universe-page]').dataset.universeState, q: document.querySelector('[data-uc-axis="Q"]').dataset.ucScore, fresh: document.querySelector('[data-uc-fresh]').textContent }));
      eq([u.state, u.q], ['NO_FILE', 'NA'], 'failed file: company page says the file is missing, no number');
      log('FAILED_RELOAD company page says: ' + u.fresh);
      eq(s.errors, [], 'no page errors (failed file)'); await c.close();
    }

    // ---------- Korean names and personal settings never move an official rank or score ----------
    phase = 'NAMES_AND_SETTINGS';
    {
      const base = await newContext(browser, { day: 2 }); await base.page.goto(BASE + '#leaderboard'); const plain = await leaderboard(base.page); await base.context.close();
      const table = JSON.parse(fs.readFileSync(path.join(WA, 'company-names-ko.json'), 'utf8')), list = Object.values(table).find((v) => Array.isArray(v) && v.some((e) => e && e.key === 'msft'));
      const row = list.find((e) => e.key === 'msft'); row.ko_name = '이름변경시험';
      const alt = await newContext(browser, { day: 2 }, { names: table });
      await alt.page.goto(BASE + '#home'); await alt.page.locator('main').waitFor();
      await alt.page.evaluate(() => { localStorage.setItem('investment.web.v1.candle-style', 'us'); localStorage.setItem('investment.web.v1.theme', 'dark');
        const c = DeviceProfiles.candidateFor('aggressive'); DeviceProfiles.writeV2(localStorage, DeviceProfiles.saveV2(DeviceProfiles.emptyV2(), { name: 'propagation test', weights: c.weights })); });
      await alt.page.reload(); await alt.page.locator('main').waitFor();
      const changed = await leaderboard(alt.page);
      eq(ranked(changed), ranked(plain), 'names, theme, candle colour and a saved personal profile leave official ranks and totals unchanged');
      eq(changed.asOf, plain.asOf);
      eq(changed.rows.find((r) => r.id === 'msft').name, '이름변경시험', 'the reviewed name table itself is shown');
      ok(plain.rows.find((r) => r.id === 'msft').name !== '이름변경시험');
      eq(alt.seen.errors, []); await alt.context.close();
    }

    // ---------- with a real service worker: a reload after the publication shows day 2, no data file in Cache Storage ----------
    phase = 'SERVICE_WORKER';
    {
      const st = { day: 1 }, { context: c, page: p, seen: s } = await newContext(browser, st, { sw: 'allow' });
      await p.goto(BASE + '#leaderboard'); await p.locator('[data-leaderboard-table]').waitFor();
      const active = await p.evaluate(async () => { if (!('serviceWorker' in navigator) || !isSecureContext) return 'NO_SW'; try { await Promise.race([navigator.serviceWorker.ready, new Promise((_, j) => setTimeout(() => j(Error('t')), 8000))]); return 'READY'; } catch (_) { return 'NOT_READY'; } });
      st.day = 2; await c.clock.setFixedTime(new Date(DAYS[2].now)); await p.reload(); const lb = await leaderboard(p);
      eq(lb.asOf, '점수 기준 ' + DAYS[2].as_of, 'reload after the publication shows day 2 with the service worker (' + active + ')');
      const cached = await p.evaluate(async () => { if (!self.caches) return []; const out = []; for (const k of await caches.keys()) for (const r of await (await caches.open(k)).keys()) out.push(new URL(r.url).pathname.split('/').pop()); return out; });
      eq(cached.filter((x) => x.endsWith('.json') && x !== 'manifest.json'), [], 'no public data file in Cache Storage');
      log('SERVICE_WORKER ' + active + ' cached=' + cached.sort().join(','));
      eq(s.errors, []); await c.close();
    }
    console.log('UPDATE_PROPAGATION_BROWSER_OK checks=' + checks + ' radar_pages=' + radarChecks);
  } catch (e) { console.error('UPDATE_PROPAGATION_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
