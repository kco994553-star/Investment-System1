'use strict';
/* G6: S06 has one sort owner (#leader-sort + direction/reset), at 390/1024/1440.
   Synthetic, price-free publications through the page's real fetch/refresh path. HARNESS_CLOCK and
   visibilitychange trigger REJUDGE. No collection, private reads or remote writes. Missing V stays
   missing (no invented official rank/model); existing priced/coverage tests remain separate.
   Check the DOM after TableSort's observer frames, including attempted legacy header clicks, same-data
   repaint, APPLIED and REJUDGE. Sorting may only reorder rows, never change S or the official model. */
const { chromium } = require('playwright'), assert = require('node:assert/strict');
const { routeEmptyPublicScreens } = require('./empty_public_screens.js');
const { displayOnlyOff } = require('./display_only_off.js');
const F = require('./qgv_v2_fixture.js');
const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const DAY1 = '2026-10-13T22:30:00Z', DAY2 = '2026-10-14T22:30:00Z', PAST = '2026-10-28T00:00:00Z';
function publication(day) {
  const p = F.strictPayload();
  if (day === 2) {
    p.as_of = DAY2; p.last_shard_index = (p.last_shard_index + 1) % p.shard_count;
    p.target.msft.acquired_at = DAY2;
    Object.assign(p.target.msft.metrics, { roic: 0.5, interest_coverage: 60, net_debt_to_ebitda: -1, dilution_3y: -0.05, revenue_acceleration: 0.2, accruals_to_assets: -0.2 });
    const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version);
    for (const [role, rows] of [['universe', p.records], ['target', p.target]]) for (const [id, r] of Object.entries(rows)) {
      const s = scores.get(role + '\u0000' + id); if (s) { r.factors = s.factors; r.axes = s.axes; }
    }
  }
  SQ.validate(p); return p;
}
const PUB = { 1: publication(1), 2: publication(2) };
const T = '[data-leaderboard-table]';
let checks = 0, snapshots = 0, phase = 'START';
function eq(a, b, why) { assert.deepEqual(a, b, phase + ': ' + why); checks++; }
function ok(a, why) { assert.ok(a, phase + ': ' + why); checks++; }
async function settle(page) {
  await page.waitForFunction(() => leaderPage?.inputs === publicScreens['sec-qgv2.json'] && document.querySelectorAll('[data-leaderboard-row]').length === officialPopulation().rows.length);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}
async function snapshot(page, sort, reference = null) {
  await settle(page);
  const s = await page.evaluate(() => {
    const S = leaderScores(), F = leaderFiltered(), table = document.querySelector('[data-leaderboard-table]');
    const model = QgvScores.officialModel({ identities: F.pop.official.identities, v2Inputs: publicScreens[Qgv2Inputs.FILE], quotes: leaderQuotes, official: F.pop.official, computed: S });
    const rows = [...table.querySelectorAll('[data-leaderboard-row]')];
    return {
      selected: document.querySelector('#leader-sort').value, view: leaderboardView.sort,
      control: document.querySelector('[data-leaderboard-sort]').dataset.leaderboardSort,
      summary: document.querySelector('[data-leaderboard-summary]').textContent,
      label: document.querySelector('#leader-sort').selectedOptions[0].textContent,
      expected: rankOrder(F.rows, S).map(r => r.company_id), actual: rows.map(r => r.dataset.leaderboardRow),
      buttons: table.querySelectorAll('.th-sort').length, aria: table.querySelectorAll('th[aria-sort]').length,
      fingerprint: JSON.stringify({ S, model }), modelText: document.querySelector('[data-model-portfolio]')?.textContent,
      scores: Object.fromEntries(Object.entries(S.rows).map(([id, r]) => [id, { rank: r.rank, q: r.primary.q, qg: r.qg_reference, total: r.primary.total }])),
      rankCells: rows.map(r => r.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank || null),
      qgCells: rows.map(r => r.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]')?.dataset.qgOrder || null),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      asOf: publicScreens['sec-qgv2.json'].as_of,
      states: Object.fromEntries(Object.entries(publicScreens['sec-qgv2.json'].records).map(([id, r]) => [id, r.state]))
    };
  });
  eq([s.selected, s.view, s.control], [sort, sort, sort], 'selector/view/direction-control share one sort');
  ok(s.summary.startsWith('정렬: ' + s.label + ' · '), 'summary names the selected order');
  eq(s.actual, s.expected, 'rendered rows follow structured order after observer frames');
  eq([s.buttons, s.aria], [0, 0], 'S06 has no independent generic header sort');
  eq(s.rankCells, s.actual.map(id => Number.isInteger(s.scores[id].rank) ? String(s.scores[id].rank) : null), 'official rank numbers unchanged in DOM');
  eq(s.qgCells, s.actual.map(id => s.scores[id].qg ? String(s.scores[id].qg.order) : null), 'QG reference order remains separate');
  if (reference) {
    eq(s.fingerprint, reference.fingerprint, 'sort does not mutate S or the official model');
    eq(s.modelText, reference.modelText, 'official model display unchanged');
  }
  if (sort === 'q-asc' || sort === 'q-desc') {
    const vals = s.actual.map(id => s.scores[id].q), n = vals.findIndex(v => v === null), known = vals.slice(0, n < 0 ? vals.length : n);
    ok(known.length > 0 && known.length < vals.length, 'fixture has real numeric Q and missing Q');
    ok(vals.slice(known.length).every(v => v === null), 'missing Q always last');
    eq(known, [...known].sort((a, b) => sort === 'q-asc' ? a - b : b - a), 'Q numeric order independently checked');
  }
  ok(s.overflow <= 0, 'no horizontal viewport overflow');
  snapshots++; return s;
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });
  let pass = 0, fail = 0;
  try { for (const width of [390, 1024, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
    let day = 1; const traffic = { outside: 0, writes: 0 }, errors = [];
    await context.clock.setFixedTime(new Date('2026-10-14T03:00:00Z'));
    await displayOnlyOff(context); await routeEmptyPublicScreens(context);
    await context.route('**/sec-qgv2.json*', r => r.fulfill({ json: PUB[day] }));
    await context.route('**/*', r => {
      if (r.request().method() !== 'GET') { traffic.writes++; return r.abort(); }
      if (new URL(r.request().url()).origin !== ORIGIN) { traffic.outside++; return r.abort(); }
      return r.fallback();
    });
    const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
    try {
      phase = width + ' INITIAL'; await page.goto(BASE + '#leaderboard'); await settle(page); await page.evaluate(() => companyNamesPromise);
      await page.evaluate(() => { window.__g6Events = []; addEventListener('public-data-updated', e => window.__g6Events.push(e.detail.reason)); });
      await page.locator('#leader-sort').selectOption('q-desc');
      // Exercise the old conflicting interaction before checking: after the fix the same header is plain text.
      const header = page.locator(T + ' th').nth(1), legacy = header.locator('.th-sort');
      if (await legacy.count()) { await legacy.click(); await legacy.click(); } else { await header.click(); await header.click(); }
      await page.locator('#leader-sort').selectOption('q-asc');
      const initial = await snapshot(page, 'q-asc'); eq(initial.asOf, DAY1, 'first publication loaded');
      eq(initial.rankCells.filter(Boolean).length, 0, 'without prices no official V rank is invented');
      ok(initial.qgCells.filter(Boolean).length > 0, 'QG reference rows remain available');
      for (const generation of ['INITIAL', 'APPLIED', 'REJUDGE']) {
        phase = width + ' ' + generation;
        if (generation === 'APPLIED') {
          day = 2; await context.clock.setFixedTime(new Date('2026-10-15T03:00:00Z'));
          await page.evaluate(() => document.querySelector('#data-refresh [data-refresh-button]').click());
          await page.waitForFunction(() => document.querySelector('#data-refresh').dataset.refreshState === 'APPLIED');
        } else if (generation === 'REJUDGE') {
          await context.clock.setFixedTime(new Date(PAST)); await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
          await page.waitForFunction(() => window.__g6Events.includes('REJUDGE'));
        }
        const reference = await snapshot(page, 'q-asc');
        if (generation === 'APPLIED') {
          eq(reference.asOf, DAY2, 'new publication applied');
          ok(reference.scores.msft.q !== initial.scores.msft.q, 'new Q actually reaches the screen result');
          ok(await page.evaluate(() => window.__g6Events.includes('REFRESH')), 'real refresh event observed');
        }
        if (generation === 'REJUDGE') {
          eq(reference.asOf, DAY2, 'rejudge retains published basis');
          ok(Object.values(reference.states).includes('STALE'), 'clock crossing really rejudges freshness');
        }
        await page.locator('[data-leaderboard-sort-dir]').press('Enter'); await snapshot(page, 'q-desc', reference);
        await page.locator('[data-leaderboard-sort-reset]').press('Space'); await snapshot(page, 'qgv', reference);
        ok(await page.locator('[data-leaderboard-sort-reset]').isDisabled(), 'reset returns to the sole default order');
        await page.locator('#leader-sort').selectOption('q-asc'); await snapshot(page, 'q-asc', reference);
        await page.evaluate(() => paintLeaderboardScreen()); await snapshot(page, 'q-asc', reference);
      }
      eq(errors, [], 'no browser errors'); eq(traffic, { outside: 0, writes: 0 }, 'local GETs only');
      pass++; console.log('PASS G6 ' + width + ' INITIAL/APPLIED/REJUDGE');
    } catch (e) { fail++; console.error('FAIL G6 ' + phase + ': ' + e.message); }
    finally { await context.close(); }
  } } finally { await browser.close(); }
  console.log('QGV_SINGLE_SORT pass=' + pass + ' fail=' + fail + ' snapshots=' + snapshots + ' checks=' + checks);
  if (fail) process.exitCode = 1;
})().catch(e => { console.error('QGV_SINGLE_SORT_ERROR ' + e.message); process.exitCode = 1; });
