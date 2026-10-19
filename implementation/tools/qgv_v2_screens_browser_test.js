'use strict';
// QGV v2 on S06/S04/S05/S13 at 390 and 1280. Owner decision 2026-10-14: v2 is the ONLY score on screens, so even with
// scoring-default.js served flipped to 'v1' every screen shows v2 and no v1 comparison / [자세히] v1 reference / '임시 기본'.
// Synthetic only: sec-qgv2.json (the Q·G side's strictly valid synthetic base vector) and v1 factors by route interception, device prices from a stubbed Universe
// tab read (RAM). Public screens are the empty-state set, so the test does not depend on what the build publishes.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
function v1() {
  const at = new Date().toISOString(), a = 'a'.repeat(64), b = 'b'.repeat(64), companies = {};
  for (const id of IDS) companies[id] = { state: 'LIVE', source_hashes: { companyfacts: a, submissions: b }, factors: Object.fromEntries(FACTORS.map((f, i) => [f, { score: 40 + i * 2, state: 'LIVE' }])) };
  return { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: at, state: 'LIVE', sources: [{ agency: 'SEC_COMPANYFACTS', sha256: a, acquired_at: at }, { agency: 'SEC_SUBMISSIONS', sha256: b, acquired_at: at }], reason_codes: [], freshness_basis: 'SOURCE_ACQUISITION', stale_after_seconds: 86400, data: { companies, method_status: 'PROVISIONAL_UNCALIBRATED', availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
}
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
/* UNI-WITHDRAWN fixture: the strict payload with TARGET amd withdrawn for an identity conflict (its TARGET row and the same-CIK
   Universe code stop) and the Universe code NASDAQ:MSFT withdrawn (its symbol is the MSFT TARGET's price symbol). */
function withdrawnPayload() {
  const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js'), p = F.strictPayload();
  p.target.amd = { ...SQ.emptyRecord(SQ.WITHDRAWN_REASON), cik: p.target.amd.cik, detected_at: '2026-10-13T12:00:00Z', withdrawn_acquired_at: '2026-10-12T00:00:00Z' };
  p.records['NASDAQ:MSFT'] = { ...SQ.emptyRecord(SQ.WITHDRAWN_REASON), detected_at: '2026-10-13T12:00:00Z', withdrawn_acquired_at: '2026-10-12T00:00:00Z', withdrawn_cik: '0000789019' };
  SQ.validate(p);return p;
}
// S06 with the withdrawn fixture: AMD and MSFT have no total and no rank; ranks of the others stay contiguous from 1.
async function withdrawnS06(page) {
  for (const id of ['amd', 'msft']) {
    const row = page.locator('[data-leaderboard-row="' + id + '"]');if (!(await row.count())) continue;
    assert.equal(await row.locator('[data-leaderboard-total]').getAttribute('data-leaderboard-total'), 'NOT_AVAILABLE', id);assert.equal(await row.locator('[data-leaderboard-rank]').count(), 0, id);
  }
  const amd = page.locator('[data-leaderboard-row="amd"] [data-leaderboard-qgv2]');if (await amd.count()) assert.match(await amd.textContent(), /식별 충돌로 사용 중지/);
  const msft = page.locator('[data-leaderboard-row="msft"]');if (await msft.count()) assert.equal(await msft.locator('[data-qgv2-flag]').filter({ hasText: '가격 식별 충돌' }).count(), 1);
  const ranks = (await page.locator('[data-leaderboard-rank]').evaluateAll((n) => n.map((x) => Number(x.dataset.leaderboardRank)))).sort((a, b) => a - b);
  const all = await page.evaluate(() => Object.values(qgvScores().rows).filter((r) => r.rank !== null).map((r) => r.company_id));
  assert.ok(!all.includes('amd') && !all.includes('msft') && all.length >= 1);assert.ok(ranks.every((r) => r >= 1 && r <= all.length));
}
/* S06 structured sort (owner directive 2026-10-18 §4.4): the sort selector (#leader-sort, also the phone control) orders rows by
   structured values from qgvScores(), NA last in both directions; direction and reset buttons; the rank number is always the
   official device rank; three scopes (analysis population / rankable / shown) are named apart; PC header sort uses numeric keys. */
async function sortFlow(page, width) {
  const T = '[data-leaderboard-table]', SHOTS = process.env.PAGES_COCKPIT_EVIDENCE_DIR;
  phase = 'SORT_SETUP';await page.locator('#leader-query').fill('');await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-row]').length === 19);
  const official = await page.evaluate(() => Object.fromEntries(Object.entries(qgvScores().rows).map(([k, r]) => [k, { rank: r.rank, q: r.primary.q, v: r.primary.v, total: r.primary.total }])));
  const shownRanks = async () => Object.fromEntries(await page.locator(T + ' tbody tr').evaluateAll((rows) => rows.map((r) => [r.dataset.leaderboardRow, r.cells[0].textContent])));
  const check = async (id, key, dir) => {
    await page.locator('[data-leaderboard-sort="' + id + '"]').waitFor();
    const ids = await rowIds(page), vals = ids.map((x) => official[x][key]), firstNa = vals.findIndex((v) => v === null);
    if (firstNa >= 0) assert.ok(vals.slice(firstNa).every((v) => v === null), id + ' NA last ' + JSON.stringify(vals));
    const known = vals.slice(0, firstNa < 0 ? vals.length : firstNa);for (let i = 1; i < known.length; i++) assert.ok(dir * (known[i] - known[i - 1]) >= 0, id + ' order ' + JSON.stringify(known));
    const ranks = await shownRanks();for (const [cid, r] of Object.entries(ranks)) assert.equal(r, official[cid].rank === null ? '—' : String(official[cid].rank), id + ' official rank kept ' + cid);
    return ids;
  };
  phase = 'SORT_Q';assert.ok(await page.locator('#leader-sort').isVisible(), 'sort selector visible at ' + width);
  const options = await page.locator('#leader-sort option').evaluateAll((o) => o.map((x) => x.value));
  for (const id of ['qgv', 'qgv-asc', 'q-desc', 'q-asc', 'g-desc', 'v-desc', 'v-asc', 'ticker-desc', 'name-desc', 'asof-desc', 'cap-desc']) assert.ok(options.includes(id), id);
  assert.ok(!options.some((o) => /return|1d|5d|20d/i.test(o)), 'no return sort without data');
  await page.locator('#leader-sort').selectOption('q-desc');await check('q-desc', 'q', -1);
  assert.equal(await page.locator('[data-leaderboard-sort-dir]').getAttribute('data-leaderboard-sort-dir'), 'desc');
  await page.locator('[data-leaderboard-sort-dir]').click();assert.equal(await page.locator('#leader-sort').inputValue(), 'q-asc');await check('q-asc', 'q', 1);
  phase = 'SORT_V';await page.locator('#leader-sort').selectOption('v-asc');const vIds = await check('v-asc', 'v', 1);assert.equal(official[vIds[vIds.length - 1]].v, null, 'V NA last ascending');
  await page.locator('[data-leaderboard-sort-dir]').click();const vDesc = await check('v-desc', 'v', -1);assert.equal(official[vDesc[vDesc.length - 1]].v, null, 'V NA last descending');
  assert.match(await page.locator('[data-leaderboard-summary]').textContent(), /^정렬: V 높은 순 · /);
  phase = 'SORT_QGV_ASC';await page.locator('#leader-sort').selectOption('qgv-asc');await check('qgv-asc', 'total', 1);
  phase = 'SORT_CAP';const capOption = page.locator('#leader-sort option[value="cap-desc"]'), m3 = await page.locator('[data-leaderboard-m3-basis]').getAttribute('data-leaderboard-m3-basis');
  assert.equal(await capOption.isDisabled(), m3 !== 'READY', 'market cap only with the device subset');
  if (m3 === 'READY') { await page.locator('#leader-sort').selectOption('cap-desc');await page.locator('[data-leaderboard-sort="cap-desc"]').waitFor();
    const caps = await page.locator(T + ' tbody tr').evaluateAll((rows) => rows.map((r) => { const b = r.querySelector('[data-leaderboard-m3-rank]');return b ? Number(b.dataset.leaderboardM3Rank) : null; }));
    const firstNa = caps.indexOf(null), known = caps.slice(0, firstNa < 0 ? caps.length : firstNa);assert.ok(known.length >= 1);assert.ok(caps.slice(known.length).every((c) => c === null));for (let i = 1; i < known.length; i++) assert.ok(known[i] >= known[i - 1]); }
  phase = 'SORT_COUNTS';const counts = page.locator('[data-leaderboard-counts]');assert.match(await counts.textContent(), /^분석 모집단 \d+개 \(공개 SEC 기록 · 백분위 비교 대상\) · 순위 가능 \d+개 \(이 화면 19개 기업 중\) · 표시 19개/);
  const pop = Number(await counts.getAttribute('data-population')), rankable = Number(await counts.getAttribute('data-rankable'));
  assert.equal(pop, await page.evaluate(() => Object.values(publicScreens['sec-qgv2.json'].records).filter((r) => r.in_cross_section === true && ['LIVE', 'STALE'].includes(r.state) && r.calc_version_mismatch !== true && r.identity_withdrawn !== true).length));
  assert.equal(rankable, Object.values(official).filter((r) => r.rank !== null).length);assert.ok(pop !== 19 || rankable !== 19);
  // D3: the footnote states the device-rank population (every screen identity in qgvScores().rows and the rows with a rank), never the
  // filtered row count; a search filter changes the shown rows but not the footnote scope.
  phase = 'RANK_SCOPE';const scopeOf = async () => { const n = page.locator('[data-leaderboard-rank-scope]');return { base: Number(await n.getAttribute('data-rank-base')), ranked: Number(await n.getAttribute('data-ranked')), text: await n.textContent() }; };
  const truth = await page.evaluate(() => { const rows = Object.values(qgvScores().rows);return { base: rows.length, ranked: rows.filter((r) => Number.isInteger(r.rank)).length }; });
  let scope = await scopeOf();assert.deepEqual([scope.base, scope.ranked], [truth.base, truth.ranked], 'footnote scope = rank population');
  assert.ok(scope.text.includes('포트폴리오 대상(TARGET) ' + truth.base + '개 기업 중 순위가 매겨진 ' + truth.ranked + '개 안의 기기 순위입니다(전체 Universe 순위 아님'), 'footnote text states both counts');assert.ok(!/19개 기업 전체 기준/.test(scope.text), 'no fixed 19');
  const firstTicker = await page.locator(T + ' tbody tr[data-leaderboard-row] a').first().textContent();
  await page.locator('#leader-query').fill(firstTicker.trim());await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-row]').length < 19);
  scope = await scopeOf();assert.deepEqual([scope.base, scope.ranked], [truth.base, truth.ranked], 'a search filter does not change the footnote scope');
  await page.locator('#leader-query').fill('');await page.waitForFunction(() => document.querySelectorAll('[data-leaderboard-row]').length === 19);
  if (SHOTS && width >= 1024) await page.screenshot({ path: SHOTS + '/s06-sort-' + width + '.png' });
  phase = 'SORT_RESET';await page.locator('[data-leaderboard-sort-reset]').click();assert.equal(await page.locator('#leader-sort').inputValue(), 'qgv');
  assert.ok(await page.locator('[data-leaderboard-sort-reset]').isDisabled());const def = await check('qgv', 'total', -1);
  assert.deepEqual(def.filter((x) => official[x].rank !== null).map((x) => official[x].rank), def.filter((x) => official[x].rank !== null).map((_, i) => i + 1));
  if (width >= 1024) {
    phase = 'SORT_PC_HEADER';const th = page.locator(T + ' thead th').nth(2);await th.locator('.th-sort').click();assert.equal(await th.getAttribute('aria-sort'), 'ascending');
    const cells = await page.locator(T + ' tbody tr').evaluateAll((rows) => rows.map((r) => r.cells[2].getAttribute('data-sort-value')));
    const firstNa = cells.indexOf(''), nums = cells.slice(0, firstNa < 0 ? cells.length : firstNa).map(Number);assert.ok(cells.slice(nums.length).every((c) => c === ''), 'NA last');
    assert.deepEqual(nums, [...nums].sort((a, b) => a - b), 'numeric key, not text');
    await th.locator('.th-sort').click();await th.locator('.th-sort').click();assert.equal(await th.getAttribute('aria-sort'), 'none');
  } else if (SHOTS) await page.screenshot({ path: SHOTS + '/s06-sort-' + width + '.png' });
  phase = 'SORT_DONE';
}
/* S13 QGV v2 two-level editor (owner directive 2026-10-18 §4.2/§4.3): product presets = the v0.1 candidates (owner decision 2026-10-18), the code presets under
   their own label, 3 axis + 15 inner weights, shares, zero = excluded, lock + fit, invalid sum, reset, before/after compare
   (personal key, official result untouched) and versioned save in this browser. */
async function editorFlow(page, width) {
  const E = '[data-qgv2-weights-editor]', SHOTS = process.env.PAGES_COCKPIT_EVIDENCE_DIR;
  phase = 'ED_OPEN';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
  const officialBefore = await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(qgvScores().rows).map(([k, r]) => [k, [r.rank, r.primary.total, r.primary.q]]))));
  await page.goto(BASE + '#profiles');await page.locator(E).waitFor();
  phase = 'ED_PRESETS';assert.deepEqual(await page.locator(E + ' [data-product-preset]').allTextContents(), ['공격형', '균형형', '수비형', '사용자 설정']);
  assert.equal(await page.locator(E + ' [data-product-preset="custom"]').getAttribute('aria-pressed'), 'true');
  const code = await page.locator(E + ' [data-code-preset]').allTextContents();assert.equal(code.length, 4);assert.ok(code[0].startsWith('balanced · 균형 · Q34/G33/V33'));assert.ok(code.every((t) => !/공격|수비|균형형/.test(t)));
  assert.match(await page.locator(E).textContent(), /기존 축 비중 프리셋\(balanced\/quality\/growth\/value\)/);
  // Owner decision 2026-10-18 (preset v0.1): 공격형 is a CANDIDATE_UNVALIDATED preset that fills the editor (details: preset_candidates_browser_test.js).
  await page.locator(E + ' [data-product-preset="aggressive"]').click();const status = page.locator(E + ' [data-product-preset-status="aggressive"]');
  assert.match(await status.locator('[data-user-preset-label]').textContent(), /^v0\.1 후보 · 검증 전 · 공식 기본값 아님$/);assert.match(await status.locator('[data-product-preset-decision]').getAttribute('href'), /USER_DECISIONS_PENDING\.md$/);
  assert.equal(await page.locator('#qgv2w-axis-G').inputValue(), '50');
  await page.locator(E + ' [data-qgv2w-reset]').click();assert.equal(await page.locator(E + ' [data-product-preset="custom"]').getAttribute('aria-pressed'), 'true');
  await page.locator(E + ' [data-product-preset="custom"]').click();
  phase = 'ED_FIELDS';assert.equal(await page.locator(E + ' [data-qgv2w^="axis."]').count(), 3);assert.equal(await page.locator(E + ' [data-qgv2w^="inner."]').count(), 15);
  assert.equal(await page.locator(E + ' input[type="range"]').count(), 18);assert.equal(await page.locator(E + ' [data-qgv2w-lock]').count(), 18);
  assert.match(await page.locator(E + ' [data-qgv2w-row="inner.Q.q_profitability"]').textContent(), /수익성 \(Q1\)/);
  assert.equal(await page.locator(E + ' [data-qgv2w-share="inner.Q.q_profitability"]').textContent(), '축 내 25.0% · 전체 8.5%');
  assert.equal(await page.locator(E + ' [data-qgv2w-share="axis.Q"]').textContent(), '전체 34.0%');
  phase = 'ED_EDIT';await page.locator('#qgv2w-inner-Q-q_profitability').fill('40');
  assert.equal(await page.locator(E + ' [data-qgv2w-share="inner.Q.q_profitability"]').textContent(), '축 내 34.8% · 전체 11.8%');
  assert.match(await page.locator(E + ' [data-qgv2w-sum="Q"]').textContent(), /^합계 115\.0 · 계산 때 100으로 정규화$/);
  await page.locator('#qgv2w-inner-Q-q_moat_proxy').fill('0');assert.equal(await page.locator(E + ' [data-qgv2w-share="inner.Q.q_moat_proxy"]').textContent(), '0 = 제외(결측 아님)');
  phase = 'ED_INVALID';for (const a of ['Q', 'G', 'V']) await page.locator('#qgv2w-axis-' + a).fill('0');
  assert.match(await page.locator(E + ' [data-qgv2w-error]').textContent(), /축 비중 합계가 0/);assert.ok(await page.locator(E + ' [data-qgv2w-compare]').isDisabled());
  phase = 'ED_FIT';await page.locator('#qgv2w-axis-Q').fill('60');await page.locator(E + ' [data-qgv2w-lock="axis.Q"]').check();assert.ok(await page.locator('#qgv2w-axis-Q').isDisabled());
  await page.locator('#qgv2w-axis-G').fill('10');await page.locator('#qgv2w-axis-V').fill('10');await page.locator(E + ' [data-qgv2w-fit="axis"]').click();
  assert.equal(await page.locator('#qgv2w-axis-Q').inputValue(), '60');assert.equal(await page.locator('#qgv2w-axis-G').inputValue(), '20');assert.equal(await page.locator(E + ' [data-qgv2w-sum="axis"]').textContent(), '합계 100.0');
  phase = 'ED_COMPARE';await page.locator(E + ' [data-qgv2w-compare]').click();await page.locator(E + ' [data-qgv2w-result-state="READY"]').waitFor();
  assert.match(await page.locator(E + ' [data-qgv2w-result-label]').textContent(), /^개인 설정 미리보기 · 공식 점수 아님 · qgv-v2\/custom\/[0-9a-f]{16}\/gate-on$/);
  assert.equal(await page.locator(E + ' [data-qgv2w-compare-row]').count(), 19);
  const table = await page.locator(E + ' [data-qgv2w-company-table] tbody tr').evaluateAll((rows) => rows.map((r) => [...r.cells].map((c) => c.textContent)));
  assert.deepEqual(table.map((r) => r[0]), ['Q', 'G', 'V', 'QGV', '순위', '산출 요인', 'Q 축 충족률', 'G 축 충족률', 'V 축 충족률', '순위·후보 자격', '가치 함정 관문']);
  assert.ok(table.some((r) => r[1] !== r[2]), 'personal values differ from the official ones');
  const cmpRows = await page.locator(E + ' [data-qgv2w-compare-row]').evaluateAll((r) => r.map((x) => [...x.cells].map((c) => c.textContent)));
  assert.ok(cmpRows.some((r) => r[1] !== r[2] && r[1] !== '— (—)'), 'some totals move ' + JSON.stringify(cmpRows));
  // Ranked rows first (personal rank order), unranked — rows last; rank change ▲/▼/0 or — (never a number for an unranked row).
  const mineRanks = cmpRows.map((r) => (/\((\d+)\)$/.exec(r[2]) || [])[1]).map((x) => (x ? Number(x) : null)), firstNa = mineRanks.indexOf(null);
  assert.deepEqual(mineRanks.slice(0, firstNa), mineRanks.slice(0, firstNa).map((_, i) => i + 1));assert.ok(mineRanks.slice(firstNa).every((x) => x === null));
  assert.ok(cmpRows.every((r, i) => (mineRanks[i] === null ? r[3] === '—' : /^(▲\d+|▼\d+|0)$/.test(r[3]))));
  await page.locator(E + ' [data-qgv2w-company]').selectOption('msft');await page.locator(E + ' [data-qgv2w-company-table="msft"]').waitFor();
  if (SHOTS) await page.screenshot({ path: SHOTS + '/s13-compare-' + width + '.png', fullPage: false });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S13 editor');
  assert.equal(await page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(qgvScores().rows).map(([k, r]) => [k, [r.rank, r.primary.total, r.primary.q]])))), officialBefore, 'official result unchanged');
  phase = 'ED_SAVE';await page.locator('#qgv2w-name').fill('Synthetic two-level');await page.locator(E + ' [data-qgv2w-save]').click();
  await page.locator(E + ' [data-qgv2w-open]').filter({ hasText: 'Synthetic two-level · v1 · ' }).waitFor();await page.locator(E + ' [data-qgv2w-save]').click();
  await page.locator(E + ' [data-qgv2w-open]').filter({ hasText: 'Synthetic two-level · v2 · ' }).waitFor();assert.equal(await page.locator(E + ' [data-qgv2w-open]').count(), 1);
  const stored = await page.evaluate(() => localStorage.getItem(DeviceProfiles.V2_KEY));assert.ok(stored && !/rank|total|price|score/i.test(stored));assert.equal(JSON.parse(stored).schema, 'device-profile-drafts/2');
  phase = 'ED_REOPEN';await page.reload();await page.locator(E).waitFor();await page.locator(E + ' [data-qgv2w-open]').click();
  assert.equal(await page.locator('#qgv2w-axis-Q').inputValue(), '60');assert.equal(await page.locator('#qgv2w-inner-Q-q_moat_proxy').inputValue(), '0');assert.equal(await page.locator('#qgv2w-name').inputValue(), 'Synthetic two-level');
  phase = 'ED_RESET';await page.locator(E + ' [data-qgv2w-reset]').click();assert.equal(await page.locator('#qgv2w-axis-Q').inputValue(), '34');assert.equal(await page.locator('#qgv2w-inner-Q-q_profitability').inputValue(), '25');
  await page.locator(E + ' [data-qgv2w-remove]').click();assert.equal(await page.locator(E + ' [data-qgv2w-open]').count(), 0);
  await page.evaluate(() => localStorage.removeItem(DeviceProfiles.V2_KEY));
  phase = 'ED_DONE';
}
const h1Focused = (page) => page.evaluate(() => document.activeElement?.tagName === 'H1' && document.querySelector('#content h1') === document.activeElement);
const rowIds = (page) => page.locator('[data-leaderboard-row]').evaluateAll((rows) => rows.map((r) => r.dataset.leaderboardRow));
/* S06 -> S04 -> S06 flow (first frontend flow): ranks over all identities, 'QGV v2 순' default, filter/sort/scroll restored by the
   S04 back link and by browser back, S04 deep links (factors/value tabs, technical keeps the company), v2 score time, collapsed
   unconnected columns, h1 focus on route change. */
async function flow(page, width) {
  const T = '[data-leaderboard-table]';
  // Columns: 5 drawn on PC, 3 on a phone (rank, company, QGV; the rest behind the per-row button), all th scope=col and none hidden;
  // the always-— columns are named in one note instead.
  const cols = width < 750 ? 3 : 5;assert.equal(await page.locator(T + ' thead th').count(), cols);assert.equal(await page.locator(T + ' thead th[scope="col"]').count(), cols);
  assert.deepEqual(await page.locator(T + ' thead th').evaluateAll((ths) => ths.map((th) => th.dataset.leaderboardCol)), ['rank', 'company', 'qgv', 'qgv_detail', 'earnings'].slice(0, cols));
  assert.match(await page.locator('[data-leaderboard-unconnected]').textContent(), /일간 · 컨센서스 · 목표 · QGV 시나리오 · 재평가 · VMR/);
  const nvdaRow = page.locator('[data-leaderboard-row="nvda"]');
  if (width < 750) {
    assert.equal(await page.locator(T + ' th[data-leaderboard-col="qgv_detail"]').isVisible(), false, 'phone hides the detail column');
    const toggle = nvdaRow.locator('.lb-toggle');assert.ok(await toggle.isVisible());assert.equal(await toggle.getAttribute('aria-expanded'), 'false');
    await toggle.click();assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
    const detail = nvdaRow.locator('[data-leaderboard-detail]');assert.ok(await detail.isVisible());assert.match(await detail.textContent(), /^QGV \d+\.\d · Q .*실적 /);
    const box = await toggle.boundingBox();assert.ok(box.height >= 44 && box.width >= 44, 'detail button target size');
  } else {
    assert.ok(await page.locator(T + ' th[data-leaderboard-col="qgv_detail"]').isVisible());assert.equal(await nvdaRow.locator('.lb-toggle').isVisible(), false);
  }
  // Default sort 'QGV v2 순': ranked rows first in rank order, NOT_AVAILABLE (—) last; never 0.
  phase = 'FLOW_RANK';assert.equal(await page.locator('#leader-sort').inputValue(), 'qgv');
  const ranks = await page.locator(T + ' tbody tr').evaluateAll((rows) => rows.map((r) => r.cells[0].textContent));
  const firstNa = ranks.indexOf('—'), ranked = ranks.slice(0, firstNa < 0 ? ranks.length : firstNa).map(Number);
  assert.ok(ranked.length >= 2, JSON.stringify(ranks));assert.deepEqual(ranked, ranked.map((_, i) => i + 1));assert.ok(ranks.slice(ranked.length).every((r) => r === '—'));
  assert.equal(await page.locator(T + ' [data-leaderboard-total="0.0"]').count(), 0);
  const gev = page.locator('[data-leaderboard-row="gev"] [data-leaderboard-total]');assert.equal(await gev.getAttribute('data-leaderboard-total'), 'NOT_AVAILABLE');assert.equal(await gev.textContent(), '—');
  // A filter only hides rows: the second-ranked company keeps rank 2 among all 19 when it is the only row shown.
  const second = (await rowIds(page))[1], secondTicker = await page.locator('[data-leaderboard-row="' + second + '"] a').first().textContent();
  await page.locator('#leader-query').fill(secondTicker);await page.waitForFunction((id) => document.querySelectorAll('[data-leaderboard-row]').length === 1 && document.querySelector('[data-leaderboard-row="' + id + '"]'), second);
  assert.equal(await page.locator('[data-leaderboard-row="' + second + '"] [data-leaderboard-rank]').getAttribute('data-leaderboard-rank'), '2');
  // Filter + sort + scroll, then S04 and back.
  phase = 'FLOW_STATE';await page.locator('#leader-query').fill('a');await page.locator('#leader-sort').selectOption('name');
  const ids = await rowIds(page);assert.ok(ids.includes('nvda') && ids.length < 19);
  const summary = await page.locator('[data-leaderboard-summary]').textContent();assert.match(summary, /정렬: 기업명 순 · 필터: 검색 “a” · 보기: 기본 · 프로필: 가치\(관문 켬\) · 관문 끔 · 19개 중 \d+개 표시/);
  const nvdaRank = await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-rank]').getAttribute('data-leaderboard-rank'), nvdaTotal = await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-total]').getAttribute('data-leaderboard-total');
  const asOf = await page.locator('[data-leaderboard-screen] [data-score-as-of="v2"]').textContent();assert.match(asOf, /^점수 기준 20\d\d-/);
  await page.evaluate(() => { const r = document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect();window.scrollTo(0, Math.max(1, r.top + scrollY - innerHeight / 2)); });
  await page.waitForTimeout(300);assert.ok(await page.evaluate(() => scrollY) > 0);
  // Where the NVDA row sat in the viewport when it was clicked (capture phase, before the route changes). The browser may
  // adjust scrollY by a few pixels after the return (scroll anchoring while late content settles), so the row position is compared.
  await page.evaluate(() => document.addEventListener('click', () => { if (location.hash.startsWith('#leaderboard')) window.__leaveTop = document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top; }, true));
  const restored = async (how) => {
    const top = await page.evaluate(() => window.__leaveTop);await page.locator(T).waitFor();
    await page.waitForFunction((v) => scrollY > 0 && Math.abs(document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top - v) <= 2, top, { timeout: 5000 })
      .catch(async () => { throw Error(how + ' scroll ' + JSON.stringify(await page.evaluate(() => [scrollY, document.querySelector('[data-leaderboard-row="nvda"]').getBoundingClientRect().top])) + ' want row top ' + top); });
    assert.equal(await page.locator('#leader-sort').inputValue(), 'name', how + ' sort');assert.equal(await page.locator('#leader-query').inputValue(), 'a', how + ' query');
    assert.deepEqual(await rowIds(page), ids, how + ' rows');assert.equal(await page.locator('[data-leaderboard-summary]').textContent(), summary, how + ' summary');
    assert.ok(await h1Focused(page), how + ' focus h1');
  };
  const toCompany = async () => {
    await page.locator('[data-leaderboard-row="nvda"] a').first().click();await page.locator('[data-company-card="qgv"]').waitFor();await page.waitForFunction(() => location.hash === '#company/nvda');
  };
  phase = 'FLOW_S04';await toCompany();assert.ok(await h1Focused(page), 'S04 focus h1');
  assert.equal(await page.evaluate(() => scrollY), 0);
  const back = page.locator('[data-origin-link="leaderboard"]');assert.equal((await back.textContent()).trim(), '← 리더보드');assert.equal(await back.getAttribute('href'), '#leaderboard');
  // Same rank and total as S06 (same population, preset and gate).
  await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
  assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').textContent(), nvdaRank);assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').textContent(), nvdaTotal);
  assert.equal(await page.locator('[data-company-badges] [data-score-as-of="v2"]').textContent(), asOf, 'S04 shows the v2 score time');
  assert.match(await page.locator('[data-company-badges] [data-v1-preview-as-of]').textContent(), /^v1 미리보기 입력 /);
  // Price badge = the value card's device quote state (no static 'NOT_AVAILABLE' while the card shows a quote).
  await page.waitForFunction(() => document.querySelector('[data-badge="price"]')?.dataset.priceState !== 'PENDING');
  const priceState = await page.locator('[data-badge="price"]').getAttribute('data-price-state'), cardQuote = await page.locator('#company-value [data-value-quote-source]').count();
  assert.equal(priceState, cardQuote ? 'AVAILABLE' : 'NOT_AVAILABLE');
  assert.equal(await page.locator('[data-company-card="technical"] a[href="#technical/nvda"]').count(), 1);
  assert.equal(await page.locator('[data-analysis-link="factors"]').getAttribute('href'), '#analysis/nvda/factors');assert.equal(await page.locator('[data-analysis-link="value"]').getAttribute('href'), '#analysis/nvda/value');
  phase = 'FLOW_BACKLINK';await back.click();await restored('back link');
  phase = 'FLOW_HISTORY';await toCompany();await page.goBack();await restored('browser back');
  // S04 -> S05 deep links open the matching tab; a tab change replaces the hash, so back returns to S04.
  phase = 'FLOW_TABS';await toCompany();await page.locator('[data-analysis-link="factors"]').click();
  await page.locator('[data-analysis-tab="factors"][aria-selected="true"]').waitFor();assert.ok(await page.locator('[data-analysis-panel="factors"]').isVisible());assert.equal(await page.locator('[data-analysis-panel="summary"]').isVisible(), false);
  assert.ok(await h1Focused(page), 'S05 focus h1');
  await page.locator('[data-analysis-tab="factors"]').focus();await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('[data-analysis-tab="value"]').getAttribute('aria-selected'), 'true');assert.equal(await page.evaluate(() => location.hash), '#analysis/nvda/value');
  await page.goBack();await page.locator('[data-company-card="qgv"]').waitFor();assert.equal(await page.evaluate(() => location.hash), '#company/nvda');
  await page.locator('[data-analysis-link="value"]').click();await page.locator('[data-analysis-tab="value"][aria-selected="true"]').waitFor();assert.ok(await page.locator('[data-analysis-panel="value"] [data-company-value]').isVisible());
  assert.equal(await page.locator('[data-analysis-panel="events"] a[href="#technical/nvda"]').count(), 1);
  // S04 -> S08 keeps the company (was ASML).
  phase = 'FLOW_TECH';await page.goBack();await page.locator('[data-company-card="technical"] a[href="#technical/nvda"]').click();
  await page.locator('[data-technical-symbol]').waitFor();assert.equal(await page.locator('[data-technical-symbol]').inputValue(), 'nvda');
  phase = 'FLOW_DONE';
}
/* FE-MISSING-2: S06 exploration filter + S04/S05 calculation status on the missing-data fixture (F.missingPayload: TARGET amd Q 2/5
   below 50% and G 4/5 partial; TARGET msft STALE; NASDAQ:GOOGL/AMZN FINANCIAL). Q·G-only rows are listed without a rank, NA is
   never 0, the filter survives S04 and back. */
async function noWideScroll(page, what) { assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll ' + what); }
async function missingFlow(page) {
  const E = '[data-leaderboard-explore]';
  phase = 'M_FILTER';await page.locator(E).waitFor();assert.equal(await page.locator(E + ' button').count(), 4);
  assert.equal(await page.locator(E + ' [data-leaderboard-explore-option="all"]').getAttribute('aria-pressed'), 'true');
  const counts = await page.locator(E + ' button').evaluateAll((b) => Object.fromEntries(b.map((x) => [x.dataset.leaderboardExploreOption, Number(x.textContent.match(/(\d+)$/)[1])])));
  assert.equal(counts.ranked + counts.partial + counts.check, counts.all);assert.equal(counts.all, 19);
  // Value preset: FINANCIAL rows have only Q·G (25+20 < 50% of the preset weight) -> no total, no rank, listed under '일부 축만 가능'.
  await page.locator('[data-qgv2-preset="value"]').click();await page.locator('[data-qgv2-preset="value"][aria-pressed="true"]').waitFor();
  // In 'all' the ranked rows come first in rank order and no unranked row is mixed into them.
  const order = await page.locator('[data-leaderboard-table] tbody tr').evaluateAll((rows) => rows.map((r) => r.cells[0].textContent));
  const firstNa = order.indexOf('—');assert.ok(firstNa > 0 && order.slice(firstNa).every((x) => x === '—'), JSON.stringify(order));
  await page.locator(E + ' [data-leaderboard-explore-option="partial"]').click();await page.locator(E + '[data-leaderboard-explore="partial"]').waitFor();
  assert.equal(await page.locator(E + ' [data-leaderboard-explore-option="partial"]').getAttribute('aria-pressed'), 'true');
  const ids = await rowIds(page);assert.ok(ids.includes('googl') && ids.includes('amzn') && !ids.includes('nvda') && !ids.includes('gev'), JSON.stringify(ids));
  assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0, 'no rank in the partial view');
  for (const id of ids) { const label = page.locator('[data-leaderboard-row="' + id + '"] [data-leaderboard-unranked="PARTIAL_AXES"]');assert.ok(await label.isVisible(), id);assert.match(await label.textContent(), /QGV 종합 순위 밖 · Q \d+\.\d · G \d+\.\d/); }
  assert.match(await page.locator('[data-leaderboard-explore-note="partial"]').textContent(), /QGV 종합 순서에 넣지 않으며 순위가 없습니다/);
  const summary = await page.locator('[data-leaderboard-summary]').textContent();assert.match(summary, /필터: 일부 축만 가능 · 보기: 기본/);assert.match(summary, new RegExp('19개 중 ' + ids.length + '개 표시'));
  assert.equal(await page.locator('[data-leaderboard-table] [data-leaderboard-total="0.0"]').count(), 0);await noWideScroll(page, 'S06 partial');
  // S04 FINANCIAL (GOOGL): earnings quality and V are '해당 없음', separate from missing data; Q fill against the original weights.
  phase = 'M_S04_FIN';await page.locator('[data-leaderboard-row="googl"] a').first().click();await page.locator('[data-qgv-coverage]').waitFor();
  const q = page.locator('[data-qgv-coverage] [data-axis-coverage="Q"]');assert.equal(await q.getAttribute('data-axis-status'), 'READY');
  assert.match(await q.locator('[data-axis-fill]').textContent(), /^충족률 80% · 4\/5 요인 \(해당 없음 1개 제외\)$/);
  await q.locator('summary').first().click();const eq = q.locator('[data-factor-coverage="q_earnings_quality"]');assert.equal(await eq.getAttribute('data-factor-state'), 'NOT_APPLICABLE');
  assert.ok(await eq.isVisible());assert.match(await eq.textContent(), /해당 없음: 금융업 기준에는/);
  const v = page.locator('[data-qgv-coverage] [data-axis-coverage="V"]');assert.equal(await v.getAttribute('data-axis-status'), 'NOT_APPLICABLE');assert.match(await v.textContent(), /현재 금융업 가치평가 모델 미지원/);
  assert.equal(await page.locator('[data-data-state="NOT_APPLICABLE"]').count(), 1);assert.equal(await page.locator('[data-data-state="SOURCE_MISSING"], [data-data-state="PARTIAL"]').count(), 0);
  assert.equal(await page.locator('[data-qgv-usable]').getAttribute('data-qgv-usable'), 'EXCLUDED');assert.match(await page.locator('[data-source-period]').textContent(), /^FY \d{4}-\d{2}-\d{2}$/);
  await noWideScroll(page, 'S04 financial');
  phase = 'M_BACK';await page.locator('[data-origin-link="leaderboard"]').click();await page.locator('[data-leaderboard-table]').waitFor();
  assert.equal(await page.locator(E + ' [data-leaderboard-explore-option="partial"]').getAttribute('aria-pressed'), 'true', 'filter restored');assert.deepEqual(await rowIds(page), ids);
  assert.equal(await page.locator('[data-leaderboard-summary]').textContent(), summary);
  phase = 'M_HISTORY';await page.locator('[data-leaderboard-row="amzn"] a').first().click();await page.locator('[data-qgv-coverage]').waitFor();await page.goBack();await page.locator('[data-leaderboard-table]').waitFor();
  assert.equal(await page.locator(E + ' [data-leaderboard-explore-option="partial"]').getAttribute('aria-pressed'), 'true', 'filter restored by browser back');assert.deepEqual(await rowIds(page), ids);
  // '자료 확인 필요': rows without any axis score, labelled.
  await page.locator(E + ' [data-leaderboard-explore-option="check"]').click();await page.locator(E + '[data-leaderboard-explore="check"]').waitFor();
  const check = await rowIds(page);assert.ok(check.includes('gev') && !check.includes('googl'));assert.equal(await page.locator('[data-leaderboard-row="gev"] [data-leaderboard-unranked="CHECK_DATA"]').textContent(), '자료 확인 필요');
  await page.locator(E + ' [data-leaderboard-explore-option="all"]').click();await page.locator(E + '[data-leaderboard-explore="all"]').waitFor();
  // S04 partial axis (AMD TARGET row): Q 2/5 = 45% -> 미산출 with the published reason, G 4/5 = 85% -> 부분 산출 with renormalized weights.
  phase = 'M_S04_PARTIAL';await page.goto(BASE + '#company/amd');await page.locator('[data-qgv-coverage]').waitFor();
  const qa = page.locator('[data-qgv-coverage] [data-axis-coverage="Q"]'), ga = page.locator('[data-qgv-coverage] [data-axis-coverage="G"]');
  assert.equal(await qa.getAttribute('data-axis-status'), 'NOT_AVAILABLE');assert.equal(await qa.locator('[data-axis-fill]').textContent(), '충족률 45% · 2/5 요인');
  assert.match(await qa.locator('[data-axis-reason]').textContent(), /원래 가중치 기준 충족률이 50% 미만/);
  assert.equal(await ga.getAttribute('data-axis-status'), 'PARTIAL');assert.equal(await ga.locator('[data-axis-fill]').textContent(), '충족률 85% · 4/5 요인');
  await ga.locator('summary').first().click();const acc = ga.locator('[data-factor-coverage="g_recent_acceleration"]');assert.equal(await acc.getAttribute('data-factor-state'), 'PARTIAL');
  assert.match(await acc.textContent(), /원래 15% → 제외/);assert.match(await acc.locator('[data-factor-reason]').textContent(), /^자료 미확보: SEC 공시에서/);
  await acc.locator('[data-evidence] summary').click();assert.match(await acc.locator('[data-evidence]').textContent(), /SEC_FACTOR_NOT_AVAILABLE.*revenue_acceleration/);
  assert.match(await ga.locator('[data-factor-coverage="g_revenue_growth"]').textContent(), /원래 25% → 재배분 29\.4%/);
  assert.equal(await page.locator('[data-data-state="PARTIAL"]').count(), 1);
  for (const li of await page.locator('[data-qgv-coverage] [data-factor-coverage]').all()) if ((await li.getAttribute('data-factor-state')) !== 'OK') assert.ok(!/점수 0/.test(await li.textContent()), 'NA is never 0');
  await noWideScroll(page, 'S04 partial');
  // S05 factors tab: renormalized column, the NA rows show — and a sentence (raw code under 근거).
  phase = 'M_S05';await page.goto(BASE + '#analysis/amd/factors');const panel = page.locator('[data-analysis-panel="factors"]');await panel.locator('[data-v2-factor-table]').waitFor();
  const row = panel.locator('[data-v2-factor="g_recent_acceleration"]');assert.equal(await row.getAttribute('data-factor-state'), 'PARTIAL');assert.equal(await row.locator('[data-factor-score]').textContent(), '—');
  assert.equal(await row.locator('[data-factor-share]').textContent(), '—');assert.match(await panel.locator('[data-v2-factor="g_revenue_growth"] [data-factor-share]').textContent(), /^29\.4%$/);
  assert.equal(await panel.locator('[data-qgv-coverage] [data-axis-coverage]').count(), 3);
  for (const cell of await panel.locator('[data-v2-factor][data-factor-state] [data-factor-score]').all()) assert.equal(await cell.textContent(), '—');
  await noWideScroll(page, 'S05');
  // STALE (MSFT TARGET row collected 2026-09-20): the chip names the last valid value's fiscal period and the collection day.
  phase = 'M_STALE';await page.goto(BASE + '#company/msft');await page.locator('[data-qgv-coverage]').waitFor();
  assert.match(await page.locator('[data-data-state="STALE"]').textContent(), /^오래된 자료 · 마지막 유효 값 기준 FY 2025-12-31 · 수집 2026-09-20$/);
  assert.equal(await page.locator('[data-source-acquired]').textContent(), '2026-09-20 00:00 UTC');assert.match(await page.locator('[data-source-used]').textContent(), /반영 · 오래된 자료/);
  phase = 'M_DONE';
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  try {
    for (const mode of ['v1', 'v2']) for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
      await context.route('**/scoring-default.js*', async (r) => { const res = await r.fetch(), body = (await res.text()).replace(/scoring_default:'v[12]'/, "scoring_default:'" + mode + "'"); await r.fulfill({ response: res, body }); });
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      // Every request the flow makes; the app must not reach any other origin (external requests are also aborted below).
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        const keysBefore = await page.evaluate(() => Object.keys(localStorage).sort());
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, F.strictUniverseValues());
        phase = 'S06';await page.locator('[data-leaderboard-table]').waitFor();
        assert.equal(await page.locator('[data-scoring-default]').first().getAttribute('data-scoring-default'), 'v2');
        // TYPE-SCOPE (owner decision 2026-10-17 item 4): the basis badge names the type-application scope id the scores use.
        assert.match(await page.locator('[data-scoring-default]').first().textContent(), /유형 범위 qgv2-type-scope\/\d{4}-\d{2}-\d{2}\.\d+$/);
        assert.equal(await page.locator('[data-qgv2-preset]').count(), 4);
        assert.equal(await page.locator('[data-qgv2-preset="balanced"]').getAttribute('aria-pressed'), 'true');
        await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        const nvda = page.locator('[data-leaderboard-row="nvda"]'), msft = page.locator('[data-leaderboard-row="msft"]'), gev = page.locator('[data-leaderboard-row="gev"]');
        {
          const text = await nvda.locator('[data-leaderboard-qgv2]').textContent();
          assert.match(text, /^QGV \d+\.\d · Q \d+\.\d · G \d+\.\d · V \d+\.\d · 산출 요인 1[0-5]\/15$/);
          assert.match(await msft.locator('[data-leaderboard-qgv2]').textContent(), / V — · 산출 요인 1\d\/15$/);
          assert.equal(await gev.locator('[data-leaderboard-qgv2]').getAttribute('data-leaderboard-qgv2'), 'NOT_AVAILABLE');
          assert.ok((await page.locator('[data-leaderboard-rank]').count()) >= 3);
          // No v1 anywhere on S06: no [자세히] v1 reference, no v1 Q·G, no v2-for-comparison line, no '임시 기본'.
          assert.equal(await page.locator('[data-leaderboard-v1-reference]').count(), 0);assert.equal(await page.locator('[data-leaderboard-v2-compare]').count(), 0);
          assert.equal(await nvda.locator('[data-qgv-detail]').count(), 0);
          assert.equal(await page.locator('[data-leaderboard-qg]').count(), 0);
          assert.ok(!/임시 기본|v1 비교용|v1 · 결측|v1 참고/.test(await page.locator('[data-leaderboard-screen]').textContent()));
          assert.ok((await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count()) >= 1, 'value-trap flag shown');
          const before = text;await page.locator('[data-qgv2-preset="value"]').click();
          await page.locator('[data-qgv2-preset="value"][aria-pressed="true"]').waitFor();
          assert.notEqual(await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qgv2]').textContent(), before);
          await page.locator('[data-qgv2-gate]').uncheck();await page.locator('[data-qgv2-state]').filter({ hasText: '관문 끔' }).waitFor();
          assert.equal(await page.locator('[data-qgv2-flag]').filter({ hasText: '가치 함정 주의' }).count(), 0);assert.equal(await msft.locator('[data-qgv2-flag]').filter({ hasText: 'V 없음' }).count(), 1);assert.equal(await gev.locator('[data-qgv2-flag]').count(), 0);
          // v2 NOT_AVAILABLE rows say why (never a v1 fallback).
          assert.match(await gev.locator('[data-leaderboard-qgv2]').textContent(), /^QGV v2 산출 불가 · /);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S06');
        if (mode === 'v2') { await flow(page, width);await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();await sortFlow(page, width); }
        phase = 'S13';await page.goto(BASE + '#profiles');await page.locator('[data-profile-editor]').waitFor();
        assert.equal(await page.locator('[data-profile-v2] h3').count(),1);
        {assert.equal(await page.locator('[data-v2-official-axis]').count(),3);assert.equal(await page.locator('[data-v2-preset]').count(),4);assert.equal(await page.locator('[data-v2-performance]').getAttribute('data-v2-performance'),'NOT_AVAILABLE');}
        assert.ok(!/v1 비교용|비교용 · v1|임시 기본/.test(await page.locator('[data-profile-official]').textContent()));assert.equal(await page.locator('[data-official-axis]').count(),0);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S13');
        phase = 'S04';await page.goto(BASE + '#company/nvda');await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-badges] [data-scoring-default]').getAttribute('data-scoring-default'), 'v2');
        assert.ok((await page.locator('[data-company-badges] [data-scoring-default]').textContent()).includes(' · 유형 범위 qgv2-type-scope/'), 'S04/S05 basis badge records the type scope');
        {
          await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').waitFor();
          assert.match(await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent(), /\d/);
          assert.match(await page.locator('[data-qgv2-summary]').textContent(), /산출 요인 1[0-5]\/15 · qgv-v2\/value\/gate-off/);
          assert.match(await page.locator('[data-qgv2-range]').textContent(), /DCF 참고 범위/);
          // No [자세히] v1 reference and no v2-for-comparison line on S04.
          assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv-detail]').count(), 0);assert.equal(await page.locator('[data-qgv-v2-compare], [data-qgv-v1-reference]').count(), 0);
          assert.ok(!/임시 기본|v1 비교용|v1 참고|점수 기준 v1/.test(await page.locator('main').textContent()));
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S04');
        phase = 'S05';await page.goto(BASE + '#analysis/nvda');await page.locator('[data-analysis-tab="factors"]').click();
        const panel = page.locator('[data-analysis-panel="factors"]');await panel.waitFor();
        {
          assert.equal(await panel.locator('[data-v2-factor-table] [data-v2-factor]').count(), 15);
          assert.ok(await panel.locator('[data-v2-factor-table]').isVisible());
          // The v1 factor table ([자세히] v1 참고) is gone from S05; raw SEC Q·G leaf scores are in Settings > 원자료 보기.
          assert.equal(await panel.locator('details[data-qgv-detail] [data-factor-table]').count(), 0);assert.equal(await page.locator('[data-factor-table], [data-v2-compare]').count(), 0);
          const earnings = await page.evaluate(() => {
            const input=publicScreens[Qgv2Inputs.FILE].records['TARGET:nvda'],engine=window.PlaybookEngine,cfg=window.PlaybookConfigDefaults;
            const configured=Boolean(engine?.classifyTypesV0&&cfg);
            return {sic:input.sic,configured,cyclical:configured?engine.classifyTypesV0(cfg,{sic:input.sic}).cyclical.member:null,
              basis:qgvScores().rows.nvda.v2.detail.earnings_basis};
          });
          assert.equal(earnings.sic,'3674');
          assert.equal(earnings.configured,true,'the approved classifier is loaded independently of the playbook UI');
          assert.equal(earnings.cyclical,true,'approved semiconductor SIC activates the cyclical earnings basis');
          assert.equal(earnings.basis,'NORMALIZED');
          assert.match(await panel.locator('[data-v2-factor="v_vs_own_history"]').textContent(), /NORMALIZED_HISTORY_NOT_AVAILABLE/);
          assert.match(await page.locator('[data-overall="v2"]').textContent(), /\d+\.\d/);
          // A device-quote refresh repaints only the score sections: the open tab and the other panels stay as they are.
          const kept = await page.evaluate(() => {
            const value=document.querySelector('[data-analysis-panel="value"]');value.dataset.keep='1';repaintScores(()=>analysis('nvda'));
            return {value:value.isConnected&&document.querySelector('[data-analysis-panel="value"]')===value,
              tab:document.querySelector('[data-analysis-tab="factors"]').getAttribute('aria-selected'),hidden:document.querySelector('[data-analysis-panel="factors"]').hidden};
          });
          assert.deepEqual(kept, {value:true,tab:'true',hidden:false});
          assert.equal(await panel.locator('[data-v2-factor-table] [data-v2-factor]').count(), 15);
        }
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll S05');
        phase = 'BOUNDARY';const keysAfter = await page.evaluate(() => Object.keys(localStorage).sort());
        assert.deepEqual(keysAfter.filter((k) => !keysBefore.includes(k) && !/google-sheet|sheet-settings/.test(k)), []);
        assert.equal(await page.evaluate(() => Object.keys(localStorage).some((k) => /qgv|price|scor/i.test(k) && !/virtual-trading-v-scores/.test(k))), false);
        if (mode === 'v2') await editorFlow(page, width);
        if (mode === 'v2') {
          // A star toggled from the S06 list keeps keyboard focus after the list is re-rendered.
          phase = 'STAR_FOCUS';await page.goto(BASE + '#leaderboard');const starButton = page.locator('#leader-company-list [data-star="amd"]');await starButton.focus();await page.keyboard.press('Enter');
          await page.waitForFunction(() => document.activeElement?.dataset?.star === 'amd' && document.activeElement.isConnected && document.activeElement.getAttribute('aria-pressed') === 'true');
        }
        assert.deepEqual(external, [], 'no request to another origin');
        assert.equal(errors, 0);pass++;console.log('PASS QGV v2 screens ' + mode + ' ' + width);
      } catch (e) { fail++;console.log('FAIL QGV v2 screens ' + mode + ' ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
    // UNI-WITHDRAWN (#289) on the S06 -> S04 flow: a withdrawn TARGET (AMD) and a withdrawn Universe code (NASDAQ:MSFT, which puts
    // the MSFT TARGET price identity in conflict) get no score, total or rank on S06/S04 and no candidate place, while the S06
    // filter/sort/scroll round trip still works around them.
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(withdrawnPayload()) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);const external = [];
      page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'W_SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, [...F.strictUniverseValues(), ['NASDAQ:MSFT', 7000, 33], ['NASDAQ:AMD', 7100, 34]]);
        await page.locator('[data-leaderboard-table]').waitFor();await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        phase = 'W_S06';await withdrawnS06(page);
        // Scores, ranks and the candidate ranking (playbook TARGET writer) all leave the stopped rows out.
        const state = await page.evaluate(() => { const S = qgvScores(), c = PlaybookScreen.candidateRanking(S, publicScreens, ['NASDAQ:AMD', 'NASDAQ:MSFT', 'NASDAQ:NVDA']), by = Object.fromEntries(c.map((r) => [r.code, r]));
          return { amd: [S.rows.amd.primary.total, S.rows.amd.primary.q, S.rows.amd.rank], msft: [S.rows.msft.primary.total, S.rows.msft.primary.v, S.rows.msft.rank, typeof S.rows.msft.primary.q], nvdaRank: S.rows.nvda.rank,
            cand: ['NASDAQ:AMD', 'NASDAQ:MSFT'].map((k) => [by[k]?.total ?? null, by[k]?.rank ?? null]) }; });
        assert.deepEqual(state.amd, [null, null, null]);assert.deepEqual(state.msft, [null, null, null, 'number']);assert.ok(Number.isInteger(state.nvdaRank));
        assert.deepEqual(state.cand, [[null, null], [null, null]]);
        // Filter/sort/scroll round trip with the stopped rows on screen.
        phase = 'W_STATE';await page.locator('#leader-sort').selectOption('ticker');await page.locator('#leader-query').fill('a');
        const ids = await rowIds(page);assert.ok(ids.includes('amd') && ids.includes('nvda') && ids.length < 19);
        await page.evaluate(() => { const r = document.querySelector('[data-leaderboard-row="amd"]').getBoundingClientRect();window.scrollTo(0, Math.max(1, r.top + scrollY - innerHeight / 2)); });
        await page.waitForTimeout(300);
        await page.evaluate(() => document.addEventListener('click', (e) => { const row = e.target.closest && e.target.closest('[data-leaderboard-row]'); if (row) { window.__leaveId = row.dataset.leaderboardRow;window.__leaveTop = row.getBoundingClientRect().top; } }, true));
        const back = async (how) => {
          await page.locator('[data-leaderboard-table]').waitFor();const [id, top] = await page.evaluate(() => [window.__leaveId, window.__leaveTop]);
          await page.waitForFunction(([i, v]) => scrollY > 0 && Math.abs(document.querySelector('[data-leaderboard-row="' + i + '"]').getBoundingClientRect().top - v) <= 2, [id, top], { timeout: 5000 });
          assert.equal(await page.locator('#leader-sort').inputValue(), 'ticker', how);assert.equal(await page.locator('#leader-query').inputValue(), 'a', how);assert.deepEqual(await rowIds(page), ids, how);
          assert.ok(await h1Focused(page), how + ' focus h1');await withdrawnS06(page);
        };
        phase = 'W_S04_AMD';await page.locator('[data-leaderboard-row="amd"] a').first().click();await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').count(), 0);assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').count(), 0);
        assert.match(await page.locator('[data-company-card="qgv"] [data-qgv2-na]').textContent(), /식별 충돌로 사용 중지/);
        await page.locator('[data-origin-link="leaderboard"]').click();phase = 'W_BACKLINK';await back('back link');
        phase = 'W_S04_MSFT';await page.locator('#leader-query').fill('');await page.locator('[data-leaderboard-row="msft"]').waitFor();const ids2 = await rowIds(page);assert.equal(ids2.length, 19);
        await page.evaluate(() => { const r = document.querySelector('[data-leaderboard-row="msft"]').getBoundingClientRect();window.scrollTo(0, Math.max(1, r.top + scrollY - innerHeight / 2)); });await page.waitForTimeout(300);
        await page.locator('[data-leaderboard-row="msft"] a').first().click();await page.locator('[data-company-card="qgv"]').waitFor();
        assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="total"] .num').count(), 0);assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="V"] .num').count(), 0);
        assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').count(), 0);assert.match(await page.locator('[data-company-card="qgv"] [data-qgv="Q"]').textContent(), /\d/);
        assert.match(await page.locator('[data-company-card="qgv"]').textContent(), /가격 식별 충돌로 가격·V·종합 점수 사용 중지/);
        phase = 'W_HISTORY';await page.goBack();await page.locator('[data-leaderboard-table]').waitFor();
        const [id, top] = await page.evaluate(() => [window.__leaveId, window.__leaveTop]);assert.equal(id, 'msft');
        await page.waitForFunction(([i, v]) => scrollY > 0 && Math.abs(document.querySelector('[data-leaderboard-row="' + i + '"]').getBoundingClientRect().top - v) <= 2, [id, top], { timeout: 5000 });
        assert.equal(await page.locator('#leader-query').inputValue(), '');assert.deepEqual(await rowIds(page), ids2);assert.ok(await h1Focused(page));await withdrawnS06(page);
        assert.deepEqual(external, [], 'no request to another origin');assert.equal(errors, 0);pass++;console.log('PASS QGV v2 withdrawn flow ' + width);
      } catch (e) { fail++;console.log('FAIL QGV v2 withdrawn flow ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
    // FE-MISSING-2 missing-data flow (S06 filter -> S04/S05 status -> back) at 390 and 1280.
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qg-factors.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(v1()) }));
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.missingPayload()) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);const external = [];
      page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'M_SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, F.strictUniverseValues());
        await page.locator('[data-leaderboard-table]').waitFor();await page.locator('details:has(#private-subset-root) > summary').click();
        await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();await page.locator('[data-qgv2-state="READY"]').filter({ hasText: /가격 [1-9]\d/ }).waitFor();
        await missingFlow(page);
        assert.deepEqual(external, [], 'no request to another origin');assert.equal(errors, 0);pass++;console.log('PASS QGV v2 missing-data flow ' + width);
      } catch (e) { fail++;console.log('FAIL QGV v2 missing-data flow ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);process.exitCode = fail ? 1 : 0;
})();
