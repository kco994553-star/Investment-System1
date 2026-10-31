'use strict';
// S13 user preset v0.1 candidates (owner decision 2026-10-18 '프리셋 v0.1 후보 정의') at 390 and 1280: 공격형/균형형/수비형 show
// the decided axis weights and the label 'v0.1 후보 · 검증 전 · 공식 기본값 아님', selecting one fills the two-level editor (official
// inner weights, type adjustment and gate on), the three weight stages (기본 / 유형 반영 / 실제 적용) shown for the profile and the
// chosen company equal the engine's own output, a candidate saves as a versioned personal profile, and the official ranking never
// moves. Synthetic only: the strict sec-qgv2.json vector (one TARGET made weak in Q) by route interception. DC-31 (device V abolished):
// no Universe read and no price; no central publication is served (404), so every V is NA with its OFFICIAL_* reason and the
// stages are the engine's price-free ones (V axis not computed, never a device V).
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, SHOTS = process.env.PAGES_COCKPIT_EVIDENCE_DIR, E = '[data-qgv2-weights-editor]';
const CANDIDATES = [['aggressive', '공격형', 'user-preset/aggressive@0.1', { Q: 30, G: 50, V: 20 }], ['balanced', '균형형', 'user-preset/balanced@0.1', { Q: 40, G: 30, V: 30 }],
  ['defensive', '수비형', 'user-preset/defensive@0.1', { Q: 55, G: 15, V: 30 }]];
/* The strict payload with TARGET amd's Q sub-metrics made weak (recomputed with the reader's own scoreRows; a TARGET row is not in
   the cross-section, so no other row changes): its industry Q percentile falls to <= 30, so the value-trap gate drops its V in
   both the official and the personal result, which lets the (c) stage show the gate. Still strictly valid. */
function gatedPayload() {
  const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js'), p = F.strictPayload(), amd = p.target.amd;
  Object.assign(amd.metrics, { roic: -0.5, gross_profit_to_assets: -0.5, moat_proxy: -0.5, accruals_to_assets: 0.5, fcf_to_net_income: -2, net_debt_to_ebitda: 20, interest_coverage: -5, dilution_3y: 0.5, incremental_roic_5y: -0.5 });
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version), sc = scores.get('target\u0000amd');amd.factors = sc.factors;amd.axes = sc.axes;
  SQ.validate(p);return p;
}
const officialSnapshot = (page) => page.evaluate(() => JSON.stringify(Object.fromEntries(Object.entries(qgvScores().rows).map(([k, r]) => [k, [r.rank, r.primary.total, r.primary.q, r.primary.g, r.primary.v, r.primary.flags]]))));
// The engine's personal result for a candidate, from the same public inputs, identities and official page the S13 editor uses
// (QgvScores.officialPage; without a publication the price-free compute with every V NA, DC-31).
const engineResult = (page, id) => page.evaluate(async (pid) => {
  const inputs = await Qgv2Inputs.load(window), catalog = await (await fetch('actual-catalog.json', { cache: 'no-store' })).json(), identities = DeviceWatchlist.identities(catalog), d = QgvV2.userPreset(pid);
  const R = QgvScores.officialPage(window, { v2Inputs: inputs, identities }), shown = new Set(identities.map((c) => c.company_id)), only = (x) => ({ ...x, rows: Object.fromEntries(Object.entries(x.rows).filter(([k]) => shown.has(k))) });
  const base = { identities: R.identities, v2Inputs: inputs, quotes: {}, official: R.official, referenceRows: QgvScores.pageReferences(), vMissing: R.v_reason };
  const mine = only(QgvScores.compute({ ...base, gate: d.gate, weights: d.weights, typeWeights: d.type_weights })), official = only(R.computed);
  return { source: R.source, summary: DeviceProfiles.stageSummary(mine), rows: Object.fromEntries(Object.entries(mine.rows).map(([k, r]) => [k, { ticker: r.ticker, stages: r.personal.weight_stages || null, total: r.personal.total }])),
    official: Object.fromEntries(Object.entries(official.rows).map(([k, r]) => [k, [r.rank, r.primary.total]])), weights: QgvV2.WEIGHTS };
}, id);
const cellValues = (loc) => loc.evaluateAll((rows) => rows.map((r) => [r.dataset.qgv2wStageRow || r.dataset.qgv2wStagesSummaryRow, ...[...r.querySelectorAll('td[data-value]')].map((c) => [c.dataset.stage || '', c.dataset.value])]));
const num = (v) => (v === null || v === undefined ? '' : String(v));

async function candidateFlow(page, width) {
  phase = 'OFFICIAL';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();const officialBefore = await officialSnapshot(page);
  await page.goto(BASE + '#profiles');await page.locator(E).waitFor();
  phase = 'LABELS';assert.deepEqual(await page.locator(E + ' [data-product-preset]').allTextContents(), ['공격형', '균형형', '수비형', '사용자 설정']);
  const code = await page.locator(E + ' [data-code-preset]').allTextContents();assert.equal(code.length, 4);assert.ok(code[0].startsWith('balanced · 균형 · Q34/G33/V33'));
  assert.ok(code.every((t) => !/공격형|수비형|균형형|v0\.1/.test(t)), 'code presets keep their own names');
  const W = await page.evaluate(() => QgvV2.WEIGHTS);
  for (const [key, name, id, axis] of CANDIDATES) {
    phase = 'CANDIDATE_' + key;await page.locator(E + ' [data-product-preset="' + key + '"]').click();
    const card = page.locator(E + ' [data-product-preset-status="' + key + '"]');await card.waitFor();
    assert.equal(await card.getAttribute('data-user-preset-id'), id);assert.equal(await page.locator(E + ' [data-product-preset="' + key + '"]').getAttribute('aria-pressed'), 'true');
    assert.equal(await card.locator('[data-user-preset-label]').textContent(), 'v0.1 후보 · 검증 전 · 공식 기본값 아님');
    assert.equal(await card.locator('[data-user-preset-ident]').textContent(), id);assert.equal(await card.locator('[data-user-preset-axis]').textContent(), 'Q ' + axis.Q + ' / G ' + axis.G + ' / V ' + axis.V);
    assert.equal(await card.locator('[data-user-preset-inner]').textContent(), '현재 공식 15요인 비중 공통 · ' + ['Q', 'G', 'V'].map((p) => p + ' ' + Object.values(W[p]).join('/')).join(' · '));
    assert.equal(await card.locator('[data-user-preset-toggles]').textContent(), '기본 켬');assert.match(await card.locator('[data-user-preset-validation]').textContent(), /^검증 전 후보 \(CANDIDATE_UNVALIDATED\)/);
    assert.match(await card.textContent(), /공식 기본값\(균형 34\/33\/33 · 관문 켬\)을 바꾸지 않는/);assert.match(await card.locator('[data-product-preset-decision]').getAttribute('href'), /USER_DECISIONS_PENDING\.md$/);
    assert.equal(await card.locator('[data-product-preset-modified]').getAttribute('data-product-preset-modified'), 'false');
    // Selecting fills the editor: axis weights, the official inner weights, type adjustment and gate on, a version-labelled name.
    for (const p of ['Q', 'G', 'V']) { assert.equal(await page.locator('#qgv2w-axis-' + p).inputValue(), String(axis[p]), name + ' ' + p);
      for (const [f, w] of Object.entries(W[p])) assert.equal(await page.locator('#qgv2w-inner-' + p + '-' + f).inputValue(), String(w), f); }
    assert.ok(await page.locator(E + ' [data-qgv2w-types]').isChecked());assert.ok(await page.locator(E + ' [data-qgv2w-gate]').isChecked());
    assert.equal(await page.locator('#qgv2w-name').inputValue(), name + ' v0.1');assert.equal(await page.locator(E + ' [data-qgv2w-sum="axis"]').textContent(), '합계 100.0');
    assert.equal(await page.locator(E + ' [data-qgv2w-share="axis.G"]').textContent(), '전체 ' + axis.G.toFixed(1) + '%');
  }
  phase = 'EDIT_BOTH_LEVELS';await page.locator(E + ' [data-product-preset="aggressive"]').click();await page.locator('#qgv2w-inner-V-v_vs_industry').fill('30');
  assert.equal(await page.locator(E + ' [data-product-preset-modified]').getAttribute('data-product-preset-modified'), 'true');
  await page.locator('#qgv2w-axis-Q').fill('35');await page.locator('#qgv2w-axis-G').fill('45');assert.equal(await page.locator(E + ' [data-qgv2w-sum="axis"]').textContent(), '합계 100.0');
  phase = 'SAVE';await page.locator('#qgv2w-name').fill('공격형 v0.1 내 수정');await page.locator(E + ' [data-qgv2w-save]').click();
  await page.locator(E + ' [data-qgv2w-open]').filter({ hasText: '공격형 v0.1 내 수정 · v1 · ' }).waitFor();await page.locator('#qgv2w-inner-Q-q_profitability').fill('30');await page.locator(E + ' [data-qgv2w-save]').click();
  await page.locator(E + ' [data-qgv2w-open]').filter({ hasText: '공격형 v0.1 내 수정 · v2 · ' }).waitFor();
  const stored = JSON.parse(await page.evaluate(() => localStorage.getItem(DeviceProfiles.V2_KEY)));assert.equal(stored.schema, 'device-profile-drafts/2');
  assert.deepEqual(stored.profiles[0].weights.axis, { Q: 35, G: 45, V: 20 });assert.equal(stored.profiles[0].weights.inner.V.v_vs_industry, 30);assert.equal(stored.profiles[0].weights.inner.Q.q_profitability, 30);
  assert.ok(stored.profiles[0].type_weights && stored.profiles[0].gate);assert.ok(!/rank|total|price|score/i.test(JSON.stringify(stored)));
  await page.evaluate(() => localStorage.removeItem(DeviceProfiles.V2_KEY));

  phase = 'COMPARE';await page.locator(E + ' [data-product-preset="aggressive"]').click();await page.locator(E + ' [data-qgv2w-compare]').click();
  await page.locator(E + ' [data-qgv2w-result-state="READY"]').waitFor();
  assert.equal(await page.locator(E + ' [data-qgv2w-result-preset]').textContent(), '공격형 v0.1 · v0.1 후보 · 검증 전 · 공식 기본값 아님');
  assert.match(await page.locator(E + ' [data-qgv2w-result-label]').textContent(), /^개인 설정 미리보기 · 공식 점수 아님 · qgv-v2\/custom\/[0-9a-f]{16}\/gate-on$/);
  const eng = await engineResult(page, 'user-preset/aggressive@0.1');assert.equal(eng.source, 'NONE', 'no publication served');
  phase = 'SUMMARY_STAGES';const sm = eng.summary;assert.ok(sm.rows > 0);
  assert.deepEqual(await page.locator(E + ' [data-qgv2w-stages-summary-table] thead th').allTextContents(), ['축', '(a) 기본', '(b) 유형 반영 · 평균', '(c) 실제 적용 · 평균']);
  assert.deepEqual(await cellValues(page.locator(E + ' [data-qgv2w-stages-summary-row]')),
    ['Q', 'G', 'V'].map((p) => [p, ['', num(sm.base[p])], ['', num(sm.type.mean[p])], ['', num(sm.applied.mean ? sm.applied.mean[p] : null)]]));
  assert.equal(await page.locator(E + ' [data-qgv2w-stages-counts="applied"]').textContent(),
    '가치 함정 관문으로 V 제외 ' + sm.counts.VALUE_TRAP_GATE + '개 · 결측 요인 재정규화 ' + sm.counts.MISSING + '개 · 축 산출 불가 ' + (['Q', 'G', 'V'].filter((p) => sm.counts.AXIS_NOT_AVAILABLE[p]).map((p) => p + ' ' + sm.counts.AXIS_NOT_AVAILABLE[p]).join(' · ') || '0') + ' · 총점 산출 불가 ' + sm.counts.TOTAL_NOT_AVAILABLE + '개' + (sm.counts.STOPPED ? ' · 사용 중지 ' + sm.counts.STOPPED + '개' : ''));
  // Company stages: a gated company (V dropped), a type-adjusted one and one with a missing factor, each equal to the engine.
  const rows = Object.entries(eng.rows).filter(([, r]) => r.stages && r.stages.applied.state === 'READY' && !r.stages.display_stop);
  const pick = (fn) => { const hit = rows.find(([, r]) => fn(r.stages));return hit ? hit[0] : null; };
  // Without a central V (DC-31) the gate cannot drop a V that is not there: a gated company appears only with a published V.
  const gated = pick((s) => s.applied.axis_status.V.status === 'VALUE_TRAP_GATE'), typed = pick((s) => s.type_adjusted.changes.length > 0), missing = pick((s) => s.applied.changes.some((c) => c.reason === 'MISSING'));
  assert.ok(typed && missing, 'fixture has typed and missing companies ' + [typed, missing]);assert.equal(gated, null, 'no V, so no value-trap drop of V');
  assert.ok(rows.every(([, r]) => r.stages.applied.axis.V === 0), 'V carries no applied weight without the central V');
  for (const cid of [...new Set([typed, missing])]) {
    phase = 'COMPANY_STAGES_' + cid;await page.locator(E + ' [data-qgv2w-company]').selectOption(cid);const box = page.locator(E + ' [data-qgv2w-stages-company="' + cid + '"]');await box.waitFor();
    const s = eng.rows[cid].stages;assert.equal(await box.locator('[data-qgv2w-stages-state]').getAttribute('data-qgv2w-stages-state'), 'READY');
    assert.deepEqual(await box.locator('thead th').allTextContents(), ['항목', '(a) 기본', '(b) 유형 반영', '(c) 실제 적용']);
    const want = [];for (const p of ['Q', 'G', 'V']) { want.push(['axis.' + p, ['base', num(s.base.axis[p])], ['type', num(s.type_adjusted.axis[p])], ['applied', num(s.applied.axis[p])]]);
      for (const f of Object.keys(eng.weights[p])) want.push(['factor.' + f, ['base', num(s.base.factor[f])], ['type', num(s.type_adjusted.factor[f])], ['applied', num(s.applied.factor[f])]]); }
    assert.deepEqual(await cellValues(box.locator('tbody tr[data-qgv2w-stage-row]')), want, cid);
    let axisSum = 0, factorSum = 0;for (const p of ['Q', 'G', 'V']) axisSum += s.applied.axis[p];for (const v of Object.values(s.applied.factor)) factorSum += v;
    assert.ok(Math.abs(axisSum - 100) < 1e-9 && Math.abs(factorSum - 100) < 1e-9, 'applied sums to 100');
    const reason = (row) => box.locator('[data-qgv2w-stage-reason-for="' + row + '"] [data-stage-reason]').textContent();
    if (cid === gated) { assert.equal(s.applied.axis.V, 0);assert.match(await reason('axis.V'), /가치 함정 관문: 업종 내 Q 백분위 30 이하 · V 제외/);assert.match(await reason('axis.Q'), /남은 비중으로 다시 나눔/); }
    if (cid === typed) assert.match(await reason('axis.' + s.type_adjusted.changes[0].key), /^기업 유형 반영 \(/);
    if (cid === missing) { const c = s.applied.changes.find((x) => x.reason === 'MISSING');assert.match(await reason('factor.' + c.key), /^결측 · 남은 요인 비중으로 다시 나눔\(0점 아님\)/); }
    const unchanged = Object.keys(s.applied.factor_status).find((f) => s.applied.factor_status[f].status === 'USED' && !s.applied.changes.some((c) => c.key === f));
    if (unchanged) assert.equal(await box.locator('[data-qgv2w-stage-reason-for="factor.' + unchanged + '"]').count(), 0, 'no reason line without a change');
  }
  phase = 'LAYOUT';await page.locator(E + ' [data-qgv2w-company]').selectOption(missing);await page.locator(E + ' [data-qgv2w-stages-company="' + missing + '"]').waitFor();
  assert.equal(await page.locator(E + ' [data-qgv2w-central] [data-central-basis]').getAttribute('data-central-state'), 'NA', 'S13 basis line without a publication');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal page scroll at ' + width);
  for (const t of ['[data-qgv2w-stages-summary-table]', '[data-qgv2w-stages-table]']) assert.equal(await page.locator(E + ' ' + t).evaluate((n) => n.parentElement.classList.contains('table-scroll')), true, t);
  if (SHOTS) { await page.locator(E + ' [data-product-preset-status]').screenshot({ path: SHOTS + '/s13-preset-card-' + width + '.png' });
    await page.locator(E + ' [data-qgv2w-stages-summary]').screenshot({ path: SHOTS + '/s13-stages-summary-' + width + '.png' });
    await page.locator(E + ' [data-qgv2w-stages-company]').screenshot({ path: SHOTS + '/s13-stages-company-' + width + '.png' }); }
  phase = 'OFFICIAL_UNCHANGED';
  for (const [k, r] of Object.entries(eng.official)) assert.deepEqual(r, JSON.parse(officialBefore)[k].slice(0, 2), k);
  await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();assert.equal(await officialSnapshot(page), officialBefore, 'official ranking unchanged');
  assert.equal(await page.locator('[data-qgv2-preset="balanced"]').getAttribute('aria-pressed'), 'true');
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(gatedPayload()) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'SETUP';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
        await page.waitForFunction(() => QgvScores.pagePublication().reason !== 'OFFICIAL_LOADING');
        await candidateFlow(page, width);
        assert.deepEqual(external, [], 'no request to another origin');assert.equal(errors, 0);pass++;console.log('PASS preset candidates ' + width);
      } catch (e) { fail++;console.log('FAIL preset candidates ' + width + ' ' + phase + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT ' + e.message.split('\n').slice(0, 6).join(' | ') + ' @' + (e.stack.match(/browser_test.js:(\d+)/) || [])[1] : 'EXECUTION ' + String(e.message).split('\n')[0])); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);process.exit(fail ? 1 : 0);
})();
