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
   Checked on day 1, after '자료 새로고침' (data-refresh.js, #321) in the same tab, and after a fresh load of day 2: leaderboard
   order, ranks and totals; TARGET and Universe504 company pages; the 1.4 tree example; the stat-radar Q/G vertex (#311);
   every shown as_of / acquired_at / state / calc_version EQUAL to the source values (not just present); STALE; the policy-NA
   reason without a number; the filing / news list; the macro light; no day-1 value anywhere it should have changed. Also:
   the in-tab (SPA) behaviour after a publication (rule R: nothing is swapped until the user presses '자료 새로고침'; D2: the
   row state is re-judged by the clock), a failed reload (no old value shown as current), Korean names and personal settings
   never changing an official rank or score, and the service-worker / fetch cache rule (statically and with a real service
   worker). The browser clock is fixed per day. No network outside the local origin.
   S06 population display (D3 / D11, #320 / #318), read only from stable attributes, never from a sentence: the footnote
   [data-leaderboard-rank-scope] data-rank-base / data-ranked and the counts line [data-leaderboard-counts] data-population /
   data-rankable / data-qg-reference / data-shown, plus the visible rows. The truth is computed apart from the screen: the page's
   own leaderScores() rows (official ranked = Number.isInteger(rank); QG 참고 목록 = qg_reference), checked against the engine in
   Node over the same file (and the same device quotes), and the filters re-applied by the test. Required after every sort,
   search, group / interest filter and explore view, on day 1, in the open tab before and after '자료 새로고침', after the day-2
   reload, and with SYNTHETIC device prices (made-up numbers in RAM: the QGV / Q·G split with a non-empty official ranking):
   D12 (owner decision 2026-10-19, was D3 'TARGET identity count'): base = the Universe codes of the file (data-rank-population
   UNIVERSE; one row per security, a TARGET company in the Universe IS that code's row, checked against
   QgvScores.universeIdentities in Node); the TARGET outside the Universe only in their own list, never ranked; ranked = the
   official ranked rows; the QG list is a separate set in its own order; the TARGET filter only hides rows, and its in-filter rank
   is shown only as '포트폴리오 내 순위'; shown = the visible rows. A missing attribute or a mismatch fails the test. */
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
let phase = 'BUILD', checks = 0, radarChecks = 0, popChecks = 0;
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
const PUB = {};
for (const n of [1, 2]) { const sec = secDay(n); PUB[n] = { 'sec-qgv2.json': n === 1 ? qgv2Day1() : qgv2Day2(), 'sec-disclosures.json': sec, 'news-signals.json': newsDay(n, sec), 'macro-screen.json': macroDay(n) }; }
// Expected values, from the engine modules in Node over the same payloads and the same fixed clock (independent of the page).
function inputsAt(n, now) { return QI.fromInputs(SQ.toInputs(PUB[n]['sec-qgv2.json'], { now })); }
function inputsOf(n) { return inputsAt(n, DAYS[n].now); }
/* D11 (owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다'): these days carry no device price, so no row has V and the official
   ranking is empty; every total is in the QG 참고 목록 (V 미포함) in its own order. `rank` here is the S06 list position: the
   official rank, else the QG list order (list says which). Before D11 the Q·G-only totals were ranked directly. */
/* D12 (owner decision 2026-10-19): the official evaluation is the Universe of the file: every Universe code once (a TARGET company in
   the Universe IS that code's row), TARGET outside the Universe never ranked (QgvScores.universeIdentities). */
function officialOf(n, identities, now = DAYS[n].now) { return QS.universeIdentities(inputsAt(n, now), identities); }
function expectedRanks(n, identities, now = DAYS[n].now, quotes = {}) {
  const U = officialOf(n, identities, now), S = QS.compute({ identities: U.identities, publicScreens: { 'sec-qgv2.json': inputsAt(n, now) }, quotes, official: U }), out = {};
  for (const [id, r] of Object.entries(S.rows)) if (Number.isInteger(r.rank) || r.qg_reference) out[id] = { rank: Number.isInteger(r.rank) ? r.rank : r.qg_reference.order, list: Number.isInteger(r.rank) ? 'RANKED' : 'QG_REFERENCE', total: fmt1(r.primary.total), q: r.primary.q, g: r.primary.g };
  return out;
}
// The two lists the engine gives in Node: official ranked ids in rank order, QG 참고 목록 ids in their own order.
function expectedLists(e) {
  const of = (list) => Object.entries(e).filter(([, x]) => x.list === list).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id);
  return { ranked: of('RANKED'), qg: of('QG_REFERENCE') };
}
/* Analysis population of the counts line: the pooled sec-qgv2 cross-section points of the file (in cross-section, LIVE or STALE,
   no calc_version mismatch, not withdrawn), counted here in Node from the same file — not the screen identities. */
function populationOf(n, now = DAYS[n].now) {
  return Object.values(inputsAt(n, now).records).filter((r) => r && r.in_cross_section === true && ['LIVE', 'STALE'].includes(r.state) && r.calc_version_mismatch !== true && r.identity_withdrawn !== true).length;
}

// ---------- S06 population display: stable attributes vs. the truth from leaderScores() and the filters ----------
// Device-only filter inputs (localStorage, set before the app reads it): one group and two interests. They only hide rows.
const PREFS_KEY = 'investment.web.v1.personal', GROUP = { id: 'g-population-test', name: '모집단 시험 그룹', members: ['msft', 'nvda', 'amd', 'googl', 'amzn'] }, INTERESTS = ['msft', 'amd'];
const PREFS = { version: 1, interests: INTERESTS, groups: [GROUP] };
const SORTS_SWEPT = ['ticker', 'name-desc', 'q-desc', 'g-asc', 'v-desc', 'qgv-asc', 'asof-desc'], SEARCHES = ['a', 'MSFT', 'zz-no-such-company'];
const popSnapshot = (page) => page.evaluate(() => {
  const S = leaderScores(), fin = (x) => typeof x === 'number' && Number.isFinite(x);
  const attrs = (sel) => { const n = document.querySelectorAll(sel); return n.length === 1 ? Object.fromEntries([...n[0].attributes].filter((a) => a.name.startsWith('data-')).map((a) => [a.name, a.value])) : { __count: n.length }; };
  return {
    // D12: the S06 rows are the Universe rows of the official evaluation (names as the app filters them); TARGET outside the Universe apart.
    truth: { identities: officialPopulation().rows.map((c) => ({ id: c.company_id, ticker: c.ticker, name: c.name, target: c.target === true })), outside: officialPopulation().outside.map((c) => c.company_id), outsideRows: officialPopulation().outside.map((c) => ({ id: c.company_id, ticker: c.ticker, name: c.name })), targets: identityCompanies.map((c) => c.company_id),
      codes: Object.keys(publicScreens['sec-qgv2.json']?.records || {}).filter((c) => !c.startsWith('TARGET:')).length, asOf: publicScreens['sec-qgv2.json']?.as_of || null,
      rows: Object.fromEntries(Object.entries(S.rows || {}).map(([k, r]) => [k, { rank: Number.isInteger(r.rank) ? r.rank : null, qg: r.qg_reference ? r.qg_reference.order : null, axes: !!r.primary && [r.primary.q, r.primary.g, r.primary.v].some(fin) }])) },
    controls: { query: document.getElementById('leader-query')?.value ?? null, group: document.getElementById('leader-group')?.value ?? null, interest: document.getElementById('leader-interest')?.checked === true, target: document.getElementById('leader-target')?.checked === true, sort: document.getElementById('leader-sort')?.value ?? null, explore: leaderboardView.explore },
    dom: { scope: attrs('[data-leaderboard-rank-scope]'), counts: attrs('[data-leaderboard-counts]'), explore: document.querySelector('[data-leaderboard-explore]')?.dataset.leaderboardExplore ?? null,
      buttons: Object.fromEntries([...document.querySelectorAll('[data-leaderboard-explore-option]')].map((b) => [b.dataset.leaderboardExploreOption, Number((b.textContent.match(/(\d+)\s*$/) || [])[1])])),
      rows: [...document.querySelectorAll('[data-leaderboard-table] tbody tr[data-leaderboard-row]')].map((tr) => ({ id: tr.dataset.leaderboardRow, rank: tr.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank ?? null, qg: tr.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]')?.dataset.qgOrder ?? null,
        prank: tr.querySelector('[data-leaderboard-portfolio-rank]')?.dataset.leaderboardPortfolioRank ?? null, prankText: tr.querySelector('[data-leaderboard-portfolio-rank]')?.textContent ?? null })),
      outside: [...document.querySelectorAll('[data-leaderboard-outside-row]')].map((li) => li.dataset.leaderboardOutsideRow), outsideList: document.querySelector('[data-leaderboard-outside]')?.dataset.leaderboardOutside ?? null } };
});
const sortIds = (a) => [...a].sort();
/* One S06 state. `expect` = { asOf, population, ranked: [ids in rank order], qg: [ids in QG order] } from Node (independent of
   the page). Returns the sizes so that a sweep can show sorting moves no row in or out. */
function checkPopulation(label, { truth: T, controls: C, dom: D }, expect) {
  const L = (m) => label + ': ' + m, ids = T.identities.map((x) => x.id), R = T.rows;
  eq(T.asOf, expect.asOf, L('the leaderboard reads the expected publication'));
  // D12: the rank population = the Universe of the file, one row per security (a TARGET company in the Universe is that code's
  // row); the TARGET outside the Universe are rows of the same result but never ranked and never in the table. Truth: leaderScores()
  // and, independently, QgvScores.universeIdentities in Node over the same file (expect.official).
  eq(sortIds(Object.keys(R)), sortIds([...ids, ...T.outside]), L('leaderScores() = one row per Universe security + the TARGET outside the Universe'));
  eq([ids.length, new Set(T.identities.map((x) => x.ticker)).size, T.codes], [expect.official.codes, ids.length, expect.official.codes], L('one row per Universe code: no security twice (dedupe)'));
  eq(sortIds(ids), sortIds(expect.official.identities.filter((c) => expect.official.universe[c.company_id]).map((c) => c.company_id)), L('S06 rows = the Universe rows of the official evaluation (Node)'));
  eq([sortIds(T.outside), sortIds(T.identities.filter((x) => x.target).map((x) => x.id).concat(T.outside))], [sortIds(expect.official.outside), sortIds(T.targets)], L('TARGET split: in the Universe (merged rows) + outside = every TARGET identity'));
  eq(T.outside.filter((id) => R[id].rank !== null || R[id].qg !== null), [], L('TARGET outside the Universe: never ranked, never in the QG list'));
  const ranked = ids.filter((id) => R[id].rank !== null).sort((a, b) => R[a].rank - R[b].rank), qg = ids.filter((id) => R[id].qg !== null).sort((a, b) => R[a].qg - R[b].qg);
  eq(ids.filter((id) => R[id].rank !== null && R[id].qg !== null), [], L('QG 참고 목록 is separate: no row is both officially ranked and in the QG list'));
  eq(ranked.map((id) => R[id].rank), ranked.map((_, i) => i + 1), L('official ranks are 1..N over the identities'));
  eq([ranked, qg], [expect.ranked, expect.qg], L('official ranking and QG list (leaderScores) = the engine in Node over the same file'));
  // Footnote scope (D12): base = the Universe codes of the file, ranked = official ranked count, outside = TARGET outside the
  // Universe; never the filtered rows.
  ok(!('__count' in D.scope), L('exactly one footnote [data-leaderboard-rank-scope] (found ' + D.scope.__count + ')'));
  eq([D.scope['data-rank-population'], D.scope['data-rank-base'], D.scope['data-ranked'], D.scope['data-outside-universe']], ['UNIVERSE', String(expect.official.codes), String(ranked.length), String(expect.official.outside.length)],
    L('footnote data-rank-population = UNIVERSE, data-rank-base = Universe codes, data-ranked = official ranked, data-outside-universe = TARGET outside'));
  // The filters, applied again by the test (search over ticker + name, the device group, interests only).
  const q = (C.query || '').trim().toLocaleLowerCase(), g = C.group === GROUP.id ? GROUP : null;
  ok(C.group === '' || g, L('group filter is the test group'));
  const keep = (x) => (!q || (x.ticker + ' ' + x.name).toLocaleLowerCase().includes(q)) && (!g || g.members.includes(x.id)) && (!C.interest || INTERESTS.includes(x.id));
  const filtered = T.identities.filter((x) => keep(x) && (!C.target || x.target)).map((x) => x.id), inF = new Set(filtered);
  // TARGET outside the Universe: only in their own list (after the same filters), never in the table.
  eq(D.rows.filter((r) => T.outside.includes(r.id)), [], L('no TARGET outside the Universe in the table'));
  eq([D.outsideList, sortIds(D.outside)], [String(T.outsideRows.filter(keep).length), sortIds(T.outsideRows.filter(keep).map((x) => x.id))], L('TARGET outside the Universe only in their own list, after the same search / group / interest filters'));
  const fr = ranked.filter((id) => inF.has(id)), fq = qg.filter((id) => inF.has(id)), rest = filtered.filter((id) => R[id].rank === null && R[id].qg === null);
  const fp = rest.filter((id) => R[id].axes), fc = rest.filter((id) => !R[id].axes), visible = { all: filtered, ranked: fr, qg: fq, partial: fp, check: fc }[C.explore];
  eq(D.explore, C.explore, L('explore view shown = the chosen one'));
  ok(Array.isArray(visible), L('known explore view ' + C.explore));
  eq(sortIds(D.rows.map((r) => r.id)), sortIds(visible), L('visible rows = the identities the filters and the explore view leave'));
  if (C.explore === 'qg') eq(D.rows.map((r) => r.id), fq, L('QG 참고 목록 view in its own order'));
  if (C.explore === 'ranked') eq(D.rows.map((r) => r.id), fr, L('official ranking view in rank order'));
  const head = { all: [...fr, ...fq], ranked: fr, qg: fq }[C.explore];
  if (C.sort === 'qgv' && head) eq(D.rows.map((r) => r.id).slice(0, head.length), head, L('QGV order: official ranking first, then the QG list, never interleaved'));
  for (const r of D.rows) eq([r.rank, r.qg], [R[r.id].rank === null ? null : String(R[r.id].rank), R[r.id].qg === null ? null : String(R[r.id].qg)], L(r.id + ' shows its official rank / QG order, whatever the sort or filter'));
  // The TARGET filter only hides rows: the official rank stays; a rank inside the filter is shown only as '포트폴리오 내 순위' (the
  // official order reduced to every ranked TARGET row in the Universe), never without the filter.
  const tRanked = ranked.filter((id) => T.identities.some((x) => x.id === id && x.target));
  for (const r of D.rows) {
    const want = C.target && tRanked.includes(r.id) ? String(tRanked.indexOf(r.id) + 1) : null;
    eq(r.prank, want, L(r.id + ' 포트폴리오 내 순위 ' + want));
    if (want !== null) eq(r.prankText, ' · 포트폴리오 내 순위 ' + want, L(r.id + ' in-filter rank is labelled 포트폴리오 내 순위'));
  }
  // Counts line: population of the file, official ranked / QG rows among the filtered rows, shown = visible rows.
  ok(!('__count' in D.counts), L('exactly one counts line [data-leaderboard-counts] (found ' + D.counts.__count + ')'));
  eq([D.counts['data-population'], D.counts['data-rankable'], D.counts['data-qg-reference'], D.counts['data-shown']], [String(expect.population), String(fr.length), String(fq.length), String(visible.length)],
    L('counts line data-population / data-rankable / data-qg-reference / data-shown'));
  eq([D.counts['data-evaluated'], D.counts['data-target-in-universe'], D.counts['data-outside-universe']], [String(expect.official.codes), String(expect.official.target_in_universe.length), String(expect.official.outside.length)],
    L('counts line data-evaluated / data-target-in-universe / data-outside-universe (D12 populations)'));
  eq(D.counts['data-shown'], String(D.rows.length), L('data-shown = the rows on screen'));
  eq(D.buttons, { all: filtered.length, ranked: fr.length, qg: fq.length, partial: fp.length, check: fc.length }, L('explore option counts'));
  popChecks++;
  return { ranked: ranked.length, qg: qg.length, shown: D.rows.length, filtered: filtered.length };
}
// S06 controls, used as a user does (the app repaints synchronously on change / input / click).
async function setExplore(page, id) { await page.locator('[data-leaderboard-explore-option="' + id + '"]').click(); await page.locator('[data-leaderboard-explore="' + id + '"]').waitFor(); }
async function setSort(page, id) { await page.locator('#leader-sort').selectOption(id); await page.waitForFunction((s) => leaderboardView.sort === s, id); }
async function setQuery(page, q) { await page.locator('#leader-query').fill(q); await page.waitForFunction((s) => leaderboardView.query === s, q); }
async function setGroup(page, id) { await page.locator('#leader-group').selectOption(id); await page.waitForFunction((s) => leaderboardView.group === s, id); }
async function setInterest(page, on) { await page.locator('#leader-interest').setChecked(on); await page.waitForFunction((s) => leaderboardView.interest === s, on); }
async function setTarget(page, on) { await page.locator('#leader-target').setChecked(on); await page.waitForFunction((s) => leaderboardView.target === s, on); }
async function resetLeader(page) { await setQuery(page, ''); await setGroup(page, ''); await setInterest(page, false); await setTarget(page, false); await setSort(page, 'qgv'); await setExplore(page, 'all'); }
/* Every population check of one publication state: default, each sort, searches, the group and interest filters, each explore
   view (alone and combined with a filter). Leaves the screen back at the defaults. */
async function populationSweep(page, label, expect) {
  phase = label + ' POPULATION';
  await go(page, 'leaderboard', '[data-leaderboard-table]'); await resetLeader(page);
  const read = async (what) => checkPopulation(label + ' · ' + what, await popSnapshot(page), expect);
  const base = await read('default');
  eq(base.shown, base.filtered, label + ': default view shows every identity');
  for (const s of SORTS_SWEPT) { await setSort(page, s); const r = await read('sort ' + s); eq([r.ranked, r.qg, r.shown], [base.ranked, base.qg, base.shown], label + ': sort ' + s + ' moves no row in or out'); }
  await setSort(page, 'qgv');
  for (const s of SEARCHES) { await setQuery(page, s); await read('search "' + s + '"'); }
  await setQuery(page, 'a'); for (const e of ['ranked', 'qg', 'partial', 'check', 'all']) { await setExplore(page, e); await read('search "a" + explore ' + e); }
  await setQuery(page, '');
  await setGroup(page, GROUP.id); for (const e of ['all', 'ranked', 'qg', 'partial', 'check']) { await setExplore(page, e); await read('group + explore ' + e); }
  await setExplore(page, 'all'); await setGroup(page, '');
  await setInterest(page, true); await read('interests only'); await setInterest(page, false);
  // D12 TARGET filter: hides the non-TARGET rows, never re-ranks (alone, with each explore view, with a sort and with a search).
  await setTarget(page, true); for (const e of ['all', 'ranked', 'qg', 'partial', 'check']) { await setExplore(page, e); await read('TARGET + explore ' + e); }
  await setExplore(page, 'all'); await setSort(page, 'ticker'); await read('TARGET + sort ticker'); await setSort(page, 'qgv'); await setQuery(page, 'MSFT'); await read('TARGET + search "MSFT"'); await setQuery(page, ''); await setTarget(page, false);
  for (const e of ['ranked', 'qg', 'partial', 'check']) { await setExplore(page, e); await read('explore ' + e); }
  await resetLeader(page); const again = await read('back to default');
  eq(again, base, label + ': back at the defaults the population display is the first one again');
  console.log('UPDATE_PROPAGATION POPULATION ' + label + ' base=' + base.filtered + ' ranked=' + base.ranked + ' qg=' + base.qg + ' population=' + expect.population + ' (sorts ' + SORTS_SWEPT.length + ', searches ' + SEARCHES.length + ', group, interests, explore views)');
  return base;
}
// Synthetic device prices (made-up numbers, RAM only) through a stubbed PrivateSubsetView, as in data_refresh_browser_test.js;
// a stubbed sheet session must never be read. Re-applied after a reload (a reload drops every stub).
const PRICES = Object.fromEntries(F.strictUniverseValues().slice(1).map(([code, , price]) => [code, { price, currency: 'USD' }]));
async function stubPrices(page) {
  await page.evaluate((q) => { window.__sheetReads = 0; const real = window.PrivateSubsetView; window.PrivateSubsetView = { ...real, prices: () => new Map(Object.entries(q)), priceBasis: () => ({ source: 'SYNTHETIC_TEST', read_id: 'synthetic-propagation', acquired_at: null, currency: 'USD', price_time: null }) };
    const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { window.__sheetReads++; return { values: [] }; } };
    window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session }; location.hash = 'home'; }, PRICES);
  await page.locator('main').waitFor(); await page.evaluate(() => { location.hash = 'leaderboard'; });
}
// The leaderboard reads the shared page result of the current inputs object, with device prices, and shows official ranks.
const pricedSettled = (page, asOf) => page.waitForFunction((a) => typeof leaderPage === 'object' && leaderPage && leaderPage.inputs === publicScreens['sec-qgv2.json'] && publicScreens['sec-qgv2.json'].as_of === a
  && leaderPage.result.price_basis && document.querySelectorAll('[data-leaderboard-rank]').length > 0, asOf);
async function press(page, expect) {
  await page.locator('#data-refresh [data-refresh-button]').click();
  await page.waitForFunction((s) => document.getElementById('data-refresh')?.dataset.refreshState === s, expect);
}

// ---------- browser helpers ----------
async function newContext(browser, state, { sw = 'block', names = null, prefs = false } = {}) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: sw });
  await context.clock.setFixedTime(new Date(DAYS[state.day].now));
  // The device group / interests the population sweep filters by: written once, before the app first reads them.
  if (prefs) await context.addInitScript(([k, v]) => { try { if (!localStorage.getItem(k)) localStorage.setItem(k, v); } catch (_) {} }, [PREFS_KEY, JSON.stringify(PREFS)]);
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
    rows: [...document.querySelectorAll('[data-leaderboard-row]')].map((tr) => ({ id: tr.dataset.leaderboardRow, rank: tr.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank || tr.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]')?.dataset.qgOrder || null,
      list: tr.querySelector('[data-leaderboard-rank]') ? 'RANKED' : tr.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]') ? 'QG_REFERENCE' : null,
      total: tr.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal || null, name: tr.querySelector('[data-leaderboard-name]')?.textContent.trim() || null })) }));
}
function ranked(lb) { return Object.fromEntries(lb.rows.filter((r) => r.rank !== null).map((r) => [r.id, { rank: Number(r.rank), list: r.list, total: r.total }])); }
async function universePage(page, code) {
  await go(page, 'company/' + encodeURIComponent(code), '[data-universe-page]');
  await page.waitForFunction((c) => document.querySelector('[data-universe-page]')?.dataset.universePage === c && document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING'
    && ['q', 'g'].every((a) => { const x = document.querySelector('[data-universe-card="radar"] tr[data-sr-axis="' + a + '"] [data-sr-series="company"]'); return x && x.dataset.srReason !== 'PENDING' && x.dataset.srScore !== undefined; }), code);
  return page.evaluate(() => {
    const pg = document.querySelector('[data-universe-page]'), ax = (a) => { const r = document.querySelector('[data-universe-card="qgv"] [data-uc-axis="' + a + '"]'); return { score: r.dataset.ucScore, state: r.dataset.ucAxisState, num: r.querySelector('.num')?.textContent.trim() || null, text: r.textContent }; };
    return { state: pg.dataset.universeState, reason: pg.dataset.universeReason, Q: ax('Q'), G: ax('G'), fresh: document.querySelector('[data-universe-card="qgv"] [data-uc-fresh]').textContent.split(' · '),
      factors: Object.fromEntries([...document.querySelectorAll('[data-uc-factor]')].map((c) => [c.dataset.ucFactor, c.dataset.ucValue])),
      radar: ['q', 'g'].map((a) => document.querySelector('[data-universe-card="radar"] tr[data-sr-axis="' + a + '"] [data-sr-series="company"]')?.dataset.srScore).filter((x) => x !== undefined), text: pg.textContent };
  });
}
function freshExpected(n, code, now = DAYS[n].now) {
  const p = PUB[n]['sec-qgv2.json'], r = p.records[code], st = SQ.restate(r, now, p.stale_after_seconds).state, age = Math.floor((Date.parse(now) - Date.parse(r.acquired_at)) / 864e5);
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
  // stat-radar.js is part of the build since #311: its Q/G vertices are required on every Universe page.
  eq(u.radar.length, 2, code + ' day ' + n + ' stat radar shows its Q and G company vertices');
  radarChecks++; for (const [i, a] of ['Q', 'G'].entries()) { const s = r.axes[a].score; if (s === null) eq(u.radar[i], 'NA', 'radar ' + a + ' NA'); else ok(Math.abs(Number(u.radar[i]) - s) <= 1e-9, 'radar ' + a + ' vertex ' + u.radar[i] + ' vs ' + s); }
}
async function targetPage(page, id) {
  await go(page, 'company/' + id, '[data-company-card="qgv"]');
  await page.locator('[data-company-card="qgv"] [data-qgv="Q"]').waitFor();
  return page.evaluate(() => ({ asOf: document.querySelector('[data-company-badges] [data-score-as-of]')?.textContent || null, Q: document.querySelector('[data-company-card="qgv"] [data-qgv="Q"]').textContent.trim(),
    G: document.querySelector('[data-company-card="qgv"] [data-qgv="G"]').textContent.trim(), total: document.querySelector('[data-company-card="qgv"] [data-qgv="total"]').textContent.trim(),
    rank: document.querySelector('[data-company-card="qgv"] [data-qgv="rank"] .num')?.textContent || document.querySelector('[data-company-card="qgv"] [data-qgv-rank="QG_REFERENCE"]')?.dataset.qgOrder || null, acquired: document.querySelector('[data-source-acquired]')?.textContent || null,
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
    const { context, page, seen } = await newContext(browser, state, { prefs: true });
    phase = 'DAY1_LOAD'; await page.goto(BASE + '#home'); await page.locator('main').waitFor();
    await page.waitForFunction(() => typeof D === 'object' && D !== null && Array.isArray(identityCompanies) && identityCompanies.length > 0);
    const identities = await page.evaluate(() => JSON.parse(JSON.stringify(identityCompanies)));
    ok(identities.length > 3, 'identities read from the served catalog');
    ok(GROUP.members.every((id) => identities.some((c) => c.company_id === id)), 'the test group members are TARGET identities');
    const exp = { 1: expectedRanks(1, identities), 2: expectedRanks(2, identities) };
    // The re-collected TARGET msft moves ahead of nvda and amd (relative order in the Universe-wide list, D12).
    const three = (e) => Object.entries(e).filter(([id]) => ['nvda', 'amd', 'msft'].includes(id)).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id);
    eq(three(exp[1]), ['nvda', 'amd', 'msft'], 'day-1 order (engine)');
    eq(three(exp[2]), ['msft', 'nvda', 'amd'], 'day-2 order (engine)');
    // Without device prices (these days) the official ranking is empty and every total is in the QG list (D11).
    const popExpect = (n, now = DAYS[n].now) => ({ asOf: PUB[n]['sec-qgv2.json'].as_of, population: populationOf(n, now), official: officialOf(n, identities, now), ...expectedLists(expectedRanks(n, identities, now)) });
    for (const n of [1, 2]) { const e = popExpect(n); eq(e.ranked, [], 'no official rank without device prices day ' + n); ok(e.qg.length > 3 && e.population > identities.length, 'day ' + n + ' QG list ' + e.qg.length + ', population ' + e.population); }
    const seenDay = {};
    async function checkDay(n, label) {
      phase = label + ' LEADERBOARD'; const lb = await leaderboard(page);
      eq(lb.asOf, '점수 기준 ' + PUB[n]['sec-qgv2.json'].as_of, 'leaderboard score time = file as_of');
      eq(ranked(lb), Object.fromEntries(Object.entries(exp[n]).map(([id, x]) => [id, { rank: x.rank, list: x.list, total: x.total }])), 'leaderboard ranks and totals day ' + n);
      ok(lb.rows.every((r) => r.list !== 'RANKED'), 'D11: no device price, so no official QGV rank (Q·G-only totals are in the QG 참고 목록) day ' + n);
      eq(lb.rows.filter((r) => r.rank !== null).map((r) => r.id), Object.entries(exp[n]).sort((a, b) => a[1].rank - b[1].rank).map(([id]) => id), 'leaderboard order day ' + n);
      await populationSweep(page, label, popExpect(n));
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
    // Rule R (FRONTEND_DATA_CONTRACT §2-3): a screen change re-reads nothing, so the tab keeps the whole day-1 set (one
    // consistent snapshot, no silent swap) until the user presses '자료 새로고침'; D2: the row states are re-judged by the clock.
    phase = 'SPA_AFTER_PUBLICATION'; state.day = 2; await context.clock.setFixedTime(new Date(DAYS[2].now));
    const spa = await leaderboard(page);
    eq([spa.asOf, ranked(spa)], ['점수 기준 ' + DAYS[1].as_of, ranked(seenDay[1].lb)], 'open tab before 자료 새로고침: the day-1 snapshot (as_of and ranks of the same day)');
    const spaNews = await newsScreen(page);
    eq(spaNews.keys, timelineKeys(1), 'open tab before 자료 새로고침: the day-1 news / filings list');
    ok(spaNews.meta.some((x) => x.startsWith('SEC 8-K · 기준: ' + PUB[1]['sec-disclosures.json'].as_of + ' ·')), 'open tab news as_of = the day-1 file: ' + spaNews.meta.join(' | '));
    {
      const u = await universePage(page, AGING);
      eq([u.state, u.fresh], ['STALE', freshExpected(1, AGING, DAYS[2].now)], 'D2: ' + AGING + ' is re-judged STALE in the open tab once the clock passes its 14-day window (no new file read)');
    }
    await populationSweep(page, 'SPA_BEFORE_REFRESH', popExpect(1, DAYS[2].now));
    // '자료 새로고침' (#321) in the same tab, no reload: the open leaderboard follows day 2 in place, then every screen shows day 2.
    phase = 'REFRESH_DAY2'; await go(page, 'leaderboard', '[data-leaderboard-table]'); await press(page, 'APPLIED');
    await page.waitForFunction((a) => document.querySelector('[data-score-as-of]')?.textContent === '점수 기준 ' + a, DAYS[2].as_of);
    checkPopulation('REFRESH_DAY2 · open leaderboard repainted in place', await popSnapshot(page), popExpect(2));
    await checkDay(2, 'DAY2_REFRESH');
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

    // ---------- the QGV / Q·G split with device prices: day 1, '자료 새로고침' to day 2 in the same tab, then a reload ----------
    // HARNESS_PRICES: synthetic Universe-tab prices (made-up numbers, never real prices) in RAM; the public files come over the
    // page's own requests. Expected lists = the engine in Node over the same file with the very quotes the page used.
    phase = 'QGV_QG_SPLIT';
    {
      const st = { day: 1 }, { context: c, page: p, seen: s } = await newContext(browser, st, { prefs: true });
      const quotes = () => p.evaluate(() => JSON.parse(JSON.stringify(leaderPage.result.quotes)));
      const priced = (n, q) => ({ asOf: PUB[n]['sec-qgv2.json'].as_of, population: populationOf(n), official: officialOf(n, identities), ...expectedLists(expectedRanks(n, identities, DAYS[n].now, q)) });
      await p.goto(BASE + '#leaderboard'); await p.locator('[data-leaderboard-table]').waitFor();
      await stubPrices(p); await pricedSettled(p, DAYS[1].as_of);
      const q1 = await quotes(), e1 = priced(1, q1);
      ok(Object.keys(q1).length > 3, 'device quotes from the synthetic price tab: ' + Object.keys(q1).length);
      ok(e1.ranked.length > 0 && e1.qg.length > 0, 'day 1 with prices has an official ranking and a separate QG list (ranked ' + e1.ranked.length + ', QG ' + e1.qg.length + ')');
      const b1 = await populationSweep(p, 'PRICED_DAY1', e1);
      st.day = 2; await c.clock.setFixedTime(new Date(DAYS[2].now));
      phase = 'PRICED_REFRESH_DAY2'; await go(p, 'leaderboard', '[data-leaderboard-table]'); await press(p, 'APPLIED'); await pricedSettled(p, DAYS[2].as_of);
      const q2 = await quotes(), e2 = priced(2, q2);
      eq(q2, q1, 'the refresh keeps the same RAM device quotes');
      ok(e2.ranked.length > 0 && e2.qg.length > 0, 'day 2 with prices has an official ranking and a separate QG list (ranked ' + e2.ranked.length + ', QG ' + e2.qg.length + ')');
      checkPopulation('PRICED_REFRESH_DAY2 · open leaderboard repainted in place', await popSnapshot(p), e2);
      const b2 = await populationSweep(p, 'PRICED_REFRESH_DAY2', e2);
      phase = 'PRICED_RELOAD_DAY2'; await p.reload(); await p.locator('[data-leaderboard-table]').waitFor();
      await stubPrices(p); await pricedSettled(p, DAYS[2].as_of);
      eq(await quotes(), q1, 'the reload uses the same synthetic quotes');
      eq(await populationSweep(p, 'PRICED_RELOAD_DAY2', e2), b2, 'reload of day 2 = the in-tab refresh of day 2 (same population display)');
      eq(await p.evaluate(() => window.__sheetReads), 0, 'no Google Sheets read'); eq(s.errors, [], 'no page errors (prices)'); eq(s.outside, [], 'no request outside the local origin (prices)');
      log('QGV_QG_SPLIT day1 ranked=' + b1.ranked + ' qg=' + b1.qg + ' · day2 ranked=' + b2.ranked + ' qg=' + b2.qg + ' · base=' + b1.filtered + ' (Universe rows; TARGET identities ' + identities.length + ')');
      await c.close();
    }

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
      eq(active, 'READY', 'the real service worker is active (localhost is a secure context)');
      st.day = 2; await c.clock.setFixedTime(new Date(DAYS[2].now)); await p.reload(); const lb = await leaderboard(p);
      eq(lb.asOf, '점수 기준 ' + DAYS[2].as_of, 'reload after the publication shows day 2 with the service worker (' + active + ')');
      const cached = await p.evaluate(async () => { if (!self.caches) return []; const out = []; for (const k of await caches.keys()) for (const r of await (await caches.open(k)).keys()) out.push(new URL(r.url).pathname.split('/').pop()); return out; });
      eq(cached.filter((x) => x.endsWith('.json') && x !== 'manifest.json'), [], 'no public data file in Cache Storage');
      log('SERVICE_WORKER ' + active + ' cached=' + cached.sort().join(','));
      eq(s.errors, []); await c.close();
    }
    console.log('UPDATE_PROPAGATION_BROWSER_OK checks=' + checks + ' radar_pages=' + radarChecks + ' population_states=' + popChecks);
  } catch (e) { console.error('UPDATE_PROPAGATION_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
