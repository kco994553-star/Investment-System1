'use strict';
/* D12 (owner decision 2026-10-19: '공식 리더보드는 Universe 전체 평가를 기준으로 한다. 기존 TARGET 19개는 별도 목록·필터로 유지한다.')
   on the real user path at 390 and 1280, with the strictly valid SYNTHETIC sec-qgv2.json and, DC-31 (device V abolished), the
   SYNTHETIC central V publication (qgv_official_fixture.js; no Universe read, no price anywhere):
   1. ONE evaluation: S06 reads the shared QgvScores.officialPage computed itself; the company detail, the playbook candidates, the
      Universe page, the stat radar and the V panel show the same V, total and rank for the same security.
   2. Rank population = the Universe codes with a published place: one row per security (a TARGET company in the Universe IS its
      code's row, never a second row), the published ranks 1..N over rows with V and a total; Q·G-only rows only in the QG 참고 목록.
   3. TARGET outside the Universe (TSE 8035, KRX 042700) only in their own labelled list: never in the table, the ranking or the
      candidates.
   4. The TARGET filter only hides rows: the rank column never changes; the in-filter rank is shown only as '포트폴리오 내 순위'.
   5. N10 / N15 / N20 = the first N of the official order after the approved eligibility, the subgroup cap and the PLAYBOOK §16
      group cap at 100/N (recomputed here independently), with the per-N §16 feasibility and the issuer check shown, stable
      across navigation, '자료 새로고침' with a new sec-qgv2.json object and a reload (the same central publication read again).
   6. The footnote / counts data attributes name the populations. Without a central publication: no official rank, no selection.
   7. Performance: the S06 paint of all Universe rows and a fresh compute of the official result are timed and reported. */
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const fmtKo = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
// The official result as the page holds it, plus an independent recomputation of the approved model-portfolio rules.
const official = (page) => page.evaluate(async () => {
  const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), R = { ...P, computed: QgvScores.presetView(P, { v2Inputs: inputs }) };
  const S = leaderScores(), fin = (x) => typeof x === 'number' && Number.isFinite(x), codes = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:'));
  const rows = Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, { ticker: r.ticker, code: r.code, uc: r.universe_code ?? 'MISSING', rank: r.rank, qg: r.qg_reference ? r.qg_reference.order : null, v: r.primary.v, total: r.primary.total, q: r.primary.q, g: r.primary.g, gate: r.primary.value_trap_gate === true }]));
  // Approved eligibility, recomputed here on the OFFICIAL default profile (balanced, gate on: the published result itself),
  // whatever the S06 preset: official rank (Universe row), Q·G·V present, no gate, net debt/EBITDA < 3 and interest coverage >= 3
  // with both metrics present (NA excluded, owner decision 2026-10-15), at most 4 per #20 subgroup, then per N the first N whose
  // PLAYBOOK §16 sector group (semiconductors + semiconductor equipment one group) stays within 40% at 100/N each.
  const D = P.computed;
  const order = Object.entries(D.rows).filter(([, r]) => Number.isInteger(r.rank) && typeof r.universe_code === 'string').sort((a, b) => a[1].rank - b[1].rank), eligible = [];
  for (const [id, x] of order) {
    const r = { ticker: x.ticker, code: x.code, q: x.primary.q, g: x.primary.g, v: x.primary.v, gate: x.primary.value_trap_gate === true };
    const m = inputs.records[r.code]?.metrics || {}, sub = PlaybookEngine.sectorFor(PlaybookConfigDefaults, r.ticker, null, inputs.records[r.code]?.sic ?? null).sector;
    if (![r.q, r.g, r.v].every(fin) || r.gate || !fin(m.net_debt_to_ebitda) || !fin(m.interest_coverage) || m.net_debt_to_ebitda >= 3 || m.interest_coverage < 3) continue;
    eligible.push([id, sub || null, sub === 'semiconductors' || sub === 'semi_equipment' ? 'semiconductor_combined' : sub || null]); }
  const pickedN = {};
  for (const n of [10, 15, 20]) { const per = {}, grp = {}, out = [];
    for (const [id, sub, group] of eligible) { if (out.length === n) break;if (sub && (per[sub] || 0) >= 4) continue;if (group && ((grp[group] || 0) + 1) * (100 / n) > 40 + 1e-9) continue;
      if (sub) per[sub] = (per[sub] || 0) + 1;if (group) grp[group] = (grp[group] || 0) + 1;out.push(id); }
    pickedN['N' + n] = out; }
  const picked = pickedN.N20;
  return { same: S === R.computed, sameAgain: QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }) === P, source: P.source, rows, codes: codes.length,
    byCode: { ...S.official.by_code }, outside: [...S.official.outside], tin: S.official.target_in_universe.map((x) => x.company_id), ranked: S.official.ranked, targets: identityCompanies.map((c) => c.company_id),
    vPanel: Number(document.querySelector('[data-v-coverage] [data-v-full]')?.dataset.vFull ?? NaN), pubV: QgvScores.pagePublication().publication.coverage.v.full, pubRanked: QgvScores.pagePublication().publication.coverage.ranked, picked, pickedN, officialRank: Object.fromEntries(Object.entries(D.rows).map(([k, r]) => [k, r.rank])), profile: S.profile.id, officialProfile: D.profile.id };
});
const attrs = (page, sel) => page.evaluate((s) => { const n = document.querySelectorAll(s);return n.length === 1 ? Object.fromEntries([...n[0].attributes].filter((a) => a.name.startsWith('data-')).map((a) => [a.name, a.value])) : { __count: n.length }; }, sel);
const tableRows = (page) => page.locator('[data-leaderboard-table] tbody tr[data-leaderboard-row]').evaluateAll((rs) => rs.map((r) => ({ id: r.dataset.leaderboardRow, ticker: r.querySelector('a')?.textContent, rank: r.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank ?? null, prank: r.querySelector('[data-leaderboard-portfolio-rank]')?.textContent ?? null })));
// V factor count per row (user decision 2026-10-23): the shown 'V n/5' and its attribute vs the count from the same shared result.
const vCounts = (page) => page.locator('[data-leaderboard-table] tbody tr[data-leaderboard-row]').evaluateAll((rs) => rs.map((r) => {
  const c = r.querySelector('[data-leaderboard-qgv-cell] [data-leaderboard-v-count]'), p = leaderScores().rows[r.dataset.leaderboardRow]?.primary, fin = (x) => typeof x === 'number' && Number.isFinite(x);
  const want = fin(p?.v) ? Object.keys(QgvV2.WEIGHTS.V).filter((k) => fin(p.factors?.[k]?.score)).length : 0;
  return { id: r.dataset.leaderboardRow, text: c ? c.textContent : null, n: c ? c.dataset.leaderboardVCount : null, missing: c ? c.dataset.vMissing : null, title: c ? c.title : null, want: String(want) }; }));
const modelRows = (page) => page.locator('[data-model-portfolio] [data-model-row]').evaluateAll((rs) => rs.map((r) => [r.dataset.modelRow, r.dataset.modelRank, r.dataset.modelIn]));
async function settle(page) { await page.waitForFunction(() => QgvScores.pagePublication().reason !== 'OFFICIAL_LOADING' && typeof leaderPage === 'object' && leaderPage && leaderPage === QgvScores.officialPage(window, { v2Inputs: publicScreens['sec-qgv2.json'], identities: identityCompanies })); }

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;const perf = [];
  const day1 = F.strictPayload(), day2 = structuredClone(day1);  // day2: a new object with the same rows (joins the same publication)
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' }), served = { p: day1 };
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(served.p) }));
      await context.route('**/qgv-official.json*', (r) => r.fulfill(served.pub ? { status: 200, contentType: 'application/json', body: O.PUB_TEXT } : { status: 404, contentType: 'text/plain', body: 'not found' }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        // 6. Without a central publication: the Universe population is shown, no official rank, no model selection.
        phase = 'NO_PUBLICATION';await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();await page.locator('[data-leaderboard-official="NO_OFFICIAL_V"]').waitFor();
        const s0 = await attrs(page, '[data-leaderboard-rank-scope]'), codes0 = await page.evaluate(() => Object.keys(publicScreens['sec-qgv2.json'].records).filter((c) => !c.startsWith('TARGET:')).length);
        assert.deepEqual([s0['data-rank-population'], s0['data-rank-base'], s0['data-ranked'], s0['data-outside-universe']], ['UNIVERSE', String(codes0), '0', '2']);
        assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);assert.equal(await page.locator('[data-model-portfolio]').getAttribute('data-model-portfolio'), 'NO_OFFICIAL_RANK');
        assert.equal(await page.locator('[data-leaderboard-row]').count(), codes0, 'one table row per Universe code without a publication too');
        // V factor count: no V without a publication → every row 'V 0/5' (never filled).
        { const vc = await vCounts(page);assert.equal(vc.length, codes0);for (const r of vc) assert.deepEqual([r.text, r.n], ['V 0/5', '0'], r.id + ' V 0/5 without a publication'); }
        // The central publication (the page opened again: the one read on open).
        phase = 'PUBLICATION';served.pub = true;await page.reload();await page.locator('[data-leaderboard-table]').waitFor();await settle(page);await page.locator('[data-leaderboard-rank]').first().waitFor();
        const X = await official(page), R = X.rows;assert.equal(X.source, 'PUBLICATION');
        // 1. ONE result.
        phase = 'ONE_RESULT';assert.equal(X.same, true, 'S06 reads the shared page result itself');assert.equal(X.sameAgain, true, 'the shared result is memoized (one result)');
        // 2. Rank population and dedupe.
        phase = 'POPULATION';const codes = X.codes, ids = Object.keys(R);
        assert.equal(ids.length, codes + X.outside.length, 'one row per Universe security + TARGET outside');
        assert.deepEqual([...X.tin, ...X.outside].sort(), [...X.targets].sort(), 'every TARGET is in the Universe (merged) or outside');
        assert.deepEqual(X.outside.sort(), ['hanmi', 'tokyo_electron'], 'TSE 8035 / KRX 042700 are outside the Universe');
        for (const id of X.tin) { const code = Object.keys(X.byCode).find((c) => X.byCode[c] === id);assert.ok(code && !Object.hasOwn(R, code), id + ' merged into ' + code + ' (no second row)'); }
        const ranked = ids.filter((id) => Number.isInteger(R[id].rank)).sort((a, b) => R[a].rank - R[b].rank);
        assert.deepEqual(ranked.map((id) => R[id].rank), ranked.map((_, i) => i + 1), 'ranks 1..N');assert.equal(ranked.length, X.ranked);assert.equal(ranked.length, X.pubRanked, 'the published ranks');
        for (const id of ids) {
          const r = R[id], withV = Number.isFinite(r.v) && Number.isFinite(r.total);
          // The ranks are the published ones (one place per issuer): a ranked row is a Universe row with V and a total; a QG row a Universe Q·G-only total.
          if (Number.isInteger(r.rank)) assert.ok(withV && typeof r.uc === 'string', id + ' ranked => a Universe row with V and a total');
          if (r.qg !== null) assert.ok(Number.isFinite(r.total) && !Number.isFinite(r.v) && typeof r.uc === 'string', id + ' QG list => a Universe Q·G-only total');
        }
        assert.ok(ranked.length > 5 && ids.some((id) => R[id].qg !== null), 'an official ranking and a separate QG list');
        assert.ok(ranked.includes('NASDAQ:ABNB') && R['NASDAQ:ABNB'].gate, 'the value-trap gate row stays ranked (D11)');
        const shown = await tableRows(page);
        assert.equal(shown.length, codes, 'table = the Universe rows');assert.equal(new Set(shown.map((r) => r.ticker)).size, codes, 'no security twice on screen');
        for (const r of shown) assert.equal(r.rank, Number.isInteger(R[r.id].rank) ? String(R[r.id].rank) : null, r.id + ' shows its official rank');
        assert.equal(await page.locator('[data-leaderboard-rank]').count(), ranked.length, 'Q·G-only rows carry no rank');
        // V factor count (2026-10-23): every row shows 'V n/5' = the V factors its V was computed from in the same result; V null → 0/5.
        phase = 'V_COUNT';{ const vc = await vCounts(page);assert.equal(vc.length, codes);
          for (const r of vc) { assert.equal(r.n, r.want, r.id + ' V count');assert.equal(r.text, 'V ' + r.want + '/5', r.id + ' V text');if (!Number.isFinite(R[r.id].v)) assert.equal(r.n, '0', r.id + ' V null is 0/5'); }
          const part = vc.find((r) => r.n !== '0' && r.n !== '5');
          if (part) { assert.match(part.title, new RegExp('^V 산출 요인 ' + part.n + '/5 · 빠진 요인: '));assert.ok(part.missing.split(' ').length === 5 - Number(part.n), part.id + ' missing ids'); }
          assert.ok(vc.some((r) => r.n === '0'), 'rows without V show 0/5'); }
        // 6. Footnote / counts attributes.
        phase = 'ATTRS';const sc = await attrs(page, '[data-leaderboard-rank-scope]'), ct = await attrs(page, '[data-leaderboard-counts]');
        assert.deepEqual([sc['data-rank-population'], sc['data-rank-base'], sc['data-ranked'], sc['data-outside-universe']], ['UNIVERSE', String(codes), String(ranked.length), '2']);
        assert.deepEqual([ct['data-evaluated'], ct['data-target-in-universe'], ct['data-outside-universe'], ct['data-rankable'], ct['data-shown']], [String(codes), String(X.tin.length), '2', String(ranked.length), String(codes)]);
        assert.match(await page.locator('[data-leaderboard-rank-scope]').textContent(), new RegExp('Universe ' + codes + '개 종목 중 V가 산출된 ' + ranked.length + '개 안의 순위입니다'));
        // 3. Outside the Universe: only the separate list.
        phase = 'OUTSIDE';assert.equal(await page.locator('[data-leaderboard-list-title="OUTSIDE_UNIVERSE"]').textContent(), 'Universe 밖 TARGET · 공식 순위 대상 아님');
        assert.deepEqual((await page.locator('[data-leaderboard-outside-row]').evaluateAll((n) => n.map((x) => x.dataset.leaderboardOutsideRow))).sort(), ['hanmi', 'tokyo_electron']);
        for (const id of X.outside) { assert.equal(await page.locator('[data-leaderboard-table] [data-leaderboard-row="' + id + '"]').count(), 0, id + ' not in the table');assert.equal(R[id].rank, null);assert.equal(R[id].qg, null); }
        // 4. TARGET filter: hides only, never re-ranks; the in-filter rank is labelled.
        phase = 'TARGET_FILTER';await page.locator('#leader-target').check();await page.waitForFunction(() => leaderboardView.target === true);
        const tRows = await tableRows(page), tRanked = X.tin.filter((id) => Number.isInteger(R[id].rank)).sort((a, b) => R[a].rank - R[b].rank);
        assert.deepEqual(tRows.map((r) => r.id).sort(), [...X.tin].sort(), 'TARGET filter = the TARGET rows in the Universe');
        for (const r of tRows) { assert.equal(r.rank, Number.isInteger(R[r.id].rank) ? String(R[r.id].rank) : null, r.id + ' rank unchanged by the filter');
          assert.equal(r.prank, tRanked.includes(r.id) ? ' · 포트폴리오 내 순위 ' + (tRanked.indexOf(r.id) + 1) : null, r.id + ' 포트폴리오 내 순위'); }
        assert.equal((await attrs(page, '[data-leaderboard-rank-scope]'))['data-rank-base'], String(codes), 'the filter does not change the rank base');
        await page.locator('#leader-target').uncheck();await page.waitForFunction(() => leaderboardView.target === false);assert.equal(await page.locator('[data-leaderboard-portfolio-rank]').count(), 0, 'no in-filter rank without the filter');
        // 5. Model portfolio N10 / N15 / N20.
        phase = 'MODEL';await page.locator('[data-model-portfolio] > summary').click();const m1 = await modelRows(page);
        assert.equal(await page.locator('[data-model-portfolio]').getAttribute('data-model-portfolio'), 'READY');
        const union = [...new Set([...X.pickedN.N10, ...X.pickedN.N15, ...X.pickedN.N20])].sort((a, b) => X.officialRank[a] - X.officialRank[b]);
        assert.deepEqual(m1.map((x) => x[0]), union, 'table = the N sets in official rank order (independent recomputation)');
        for (const k of ['N10', 'N15', 'N20']) {
          assert.deepEqual(m1.filter((x) => x[2].split(' ').includes(k)).map((x) => x[0]), X.pickedN[k], k + ' = first eligible under the subgroup and §16 caps');
          const a = await attrs(page, '[data-model-limits="' + k + '"]'), n = Number(k.slice(1)), short = (n - X.pickedN[k].length) * 100 / n;
          assert.equal(a['data-model-feasible'], X.pickedN[k].length < n ? 'SHORTFALL' : a['data-model-group-status'] === 'UNVERIFIED' ? 'UNVERIFIED' : 'FEASIBLE', k);assert.equal(a['data-model-shortfall-pct'], short.toFixed(2), k);
          for (const v of Object.values(JSON.parse(a['data-model-group-pct']))) assert.ok(v <= 40 + 1e-9, k + ' group ' + v);
          assert.match(await page.locator('[data-model-limits="' + k + '"]').textContent(), new RegExp('^' + k + ' · (16절 한도 아래 구성 가능 · |구성 불가 · 부족 비중 ' + short.toFixed(2).replace('.', '\\.') + '% \\(' + X.pickedN[k].length + '/' + n + ' · 채우지 않음 · 비중 재조정 없음\\) · 원인: |' + n + '종목 구성 · 업종 묶음 40% 확인 불가 · )'));
          const iss = await attrs(page, '[data-model-issuer="' + k + '"]');assert.equal(iss['data-model-issuer-status'], 'RECOMMENDATION_DECISION_NEEDED');assert.equal(iss['data-model-issuer-applied'], 'false');
          assert.match(await page.locator('[data-model-issuer="' + k + '"]').textContent(), new RegExp('^' + k + ' · 같은 발행사 합산 비중 \\(권장안 · 결정 필요 · 선정 불변\\): '));
        }
        assert.ok(['PASS', 'UNVERIFIED', 'FAIL', 'CORE_SHORT', 'INCOMPLETE'].includes(await page.locator('[data-model-tier-check]').getAttribute('data-model-tier-check')));
        for (const [id, rank] of m1) { assert.equal(rank, String(X.officialRank[id]));assert.ok(!X.outside.includes(id) && R[id].qg === null, id + ' eligible'); }
        assert.equal(await page.locator('[data-model-rules]').getAttribute('data-model-rules'), 'OFFICIAL_RANK AXES_50 VALUE_TRAP_GATE FINANCIAL_SAFETY FINANCIAL_SAFETY_NA SUBGROUP_MAX_4 LIMITS_16');
        { const ex = JSON.parse(await page.locator('[data-model-excluded]').getAttribute('data-model-excluded'));assert.deepEqual(Object.keys(ex), ['AXES_50', 'VALUE_TRAP_GATE', 'FINANCIAL_SAFETY', 'FINANCIAL_SAFETY_NA', 'SUBGROUP_MAX_4']);
          assert.match(await page.locator('[data-model-excluded]').textContent(), new RegExp('재무 안전 지표 NA ' + ex.FINANCIAL_SAFETY_NA + ' · '));assert.match(await page.locator('[data-model-not-applied]').textContent(), /^미적용 · 소유자 결정 필요: 10-K 숫자 대조 · 하위 묶음·16절 한도 밖의 업종 분산\(BT-14\) · 같은 발행사 한 자리\(권장안\) · /); }
        assert.equal(await page.locator('[data-model-counts]').getAttribute('data-model-profile'), X.officialProfile);assert.equal(X.officialProfile, 'qgv-v2/balanced/gate-on');
        // A different device preset/gate on S06 changes the S06 ranking but never the N sets (official default profile).
        phase = 'MODEL_PRESET';await page.locator('[data-qgv2-preset="growth"]').click();await page.locator('[data-qgv2-preset="growth"][aria-pressed="true"]').waitFor();
        await page.locator('[data-qgv2-gate]').uncheck();await page.waitForFunction(() => qgv2Profile.gate === false);await settle(page);
        if ((await page.locator('[data-model-portfolio]').getAttribute('open')) === null) await page.locator('[data-model-portfolio] > summary').click();
        assert.deepEqual(await modelRows(page), m1, 'N sets unchanged by the device preset');assert.equal(await page.locator('[data-model-counts]').getAttribute('data-model-profile-differs'), 'true');
        assert.match(await page.locator('[data-model-counts]').textContent(), /이 기기 S06 프로필 qgv-v2\/growth\/gate-off은 이 선정에 영향 없음/);
        await page.locator('[data-qgv2-preset="balanced"]').click();await page.locator('[data-qgv2-gate]').check();await page.waitForFunction(() => qgv2Profile.gate === true && qgv2Profile.preset === 'balanced');await settle(page);
        if ((await page.locator('[data-model-portfolio]').getAttribute('open')) === null) await page.locator('[data-model-portfolio] > summary').click();
        assert.equal(await page.locator('[data-model-counts]').getAttribute('data-model-profile-differs'), 'false');
        // 1. The same V / total / rank on the company detail, the radar, the Universe page and the candidates.
        phase = 'DETAIL';const tgt = ranked.find((id) => X.tin.includes(id)), uni = ranked.find((id) => !X.tin.includes(id) && !X.outside.includes(id));
        await page.evaluate((id) => { location.hash = 'company/' + id; }, tgt);await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').waitFor();
        assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').textContent(), String(R[tgt].rank), tgt + ' detail rank = S06 rank');
        assert.equal(await page.locator('[data-qgv-rank-scope]').getAttribute('data-qgv-rank-scope'), 'UNIVERSE');
        assert.equal((await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent()).trim(), fmtKo(R[tgt].v));assert.equal((await page.locator('[data-company-card="qgv"] [data-qgv="total"]').textContent()).trim(), fmtKo(R[tgt].total));
        await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return c && c.dataset.srReason !== 'PENDING'; });
        assert.ok(Math.abs(Number(await page.locator('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]').getAttribute('data-sr-score')) - R[tgt].v) <= 1e-9, 'radar V = S06 V');
        // The Universe page of that TARGET company's code is the same security: the same total and rank, and it says so.
        const tcode = Object.keys(X.byCode).find((c) => X.byCode[c] === tgt);
        await page.evaluate((c) => { location.hash = 'company/' + encodeURIComponent(c); }, tcode);await page.locator('[data-uc-same-security]').waitFor();
        assert.equal(await page.locator('[data-uc-same-security]').getAttribute('data-uc-same-security'), tgt);
        assert.ok(Math.abs(Number(await page.locator('[data-uc-total]').getAttribute('data-uc-total')) - R[tgt].total) <= 1e-9);assert.match(await page.locator('[data-uc-total-line]').textContent(), new RegExp('Universe 공식 QGV 순위 ' + R[tgt].rank + ' '));
        await page.evaluate((c) => { location.hash = 'company/' + encodeURIComponent(c); }, uni);await page.locator('[data-uc-total-line]').filter({ hasText: '공식 QGV 순위' }).waitFor();
        assert.ok(Math.abs(Number(await page.locator('[data-uc-total]').getAttribute('data-uc-total')) - R[uni].total) <= 1e-9);assert.match(await page.locator('[data-uc-total-line]').textContent(), new RegExp('Universe 공식 QGV 순위 ' + R[uni].rank + ' '));
        await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return c && c.dataset.srReason !== 'PENDING'; });
        assert.ok(Math.abs(Number(await page.locator('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]').getAttribute('data-sr-score')) - R[uni].v) <= 1e-9, 'Universe page radar V = S06 V');
        // The V panel shows the publication's own count.
        assert.equal(X.vPanel, X.pubV, 'V panel = the publication coverage');
        // The playbook candidates: candidate rank = official rank for every ranked candidate.
        phase = 'CANDIDATES';await page.evaluate(() => { location.hash = 'playbook'; });const writer = page.locator('[data-target-v1]');await writer.locator('[data-target-rank-row]').first().waitFor();
        const cand = await writer.locator('[data-target-ranking] [data-target-rank-row]').evaluateAll((rs) => rs.map((r) => [r.dataset.targetRankRow, r.cells[1].textContent, r.cells[2].textContent]));
        const byTicker = Object.fromEntries(ids.map((id) => [R[id].ticker, id])), cRanked = cand.filter((c) => c[1] !== '—');
        assert.deepEqual(cRanked.map((c) => c[0]), ranked.slice(0, 30).map((id) => R[id].ticker), 'candidates = the official order');
        for (const [t, rank, total] of cRanked) { assert.equal(rank, String(R[byTicker[t]].rank), t + ' candidate rank = official rank');assert.equal(total, R[byTicker[t]].total.toFixed(1)); }
        for (const id of X.outside) assert.ok(!cand.some((c) => c[0] === R[id].ticker), id + ' not a candidate');
        // 5. Stable across navigation, a refresh with a new publication object (same rows) and a reload with the same read.
        phase = 'STABLE_NAV';await page.evaluate(() => { location.hash = 'home'; });await page.locator('main').waitFor();await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-table]').waitFor();await settle(page);
        await page.locator('[data-model-portfolio] > summary').click();assert.deepEqual(await modelRows(page), m1, 'same selection after navigation');
        phase = 'STABLE_REFRESH';served.p = day2;await page.locator('#data-refresh [data-refresh-button]').click();
        // The same rows again: DataRefresh reports UNCHANGED (same as_of; the publication join needs that as_of) and re-judges.
        await page.waitForFunction(() => ['APPLIED', 'UNCHANGED'].includes(document.getElementById('data-refresh')?.dataset.refreshState));await settle(page);
        const X2 = await official(page);assert.deepEqual(Object.fromEntries(Object.entries(X2.rows).map(([k, r]) => [k, [r.rank, r.total, r.v]])), Object.fromEntries(Object.entries(R).map(([k, r]) => [k, [r.rank, r.total, r.v]])), 'same ranks after the refresh (same rows, same publication)');
        if (!(await page.locator('[data-model-portfolio]').getAttribute('open') !== null)) await page.locator('[data-model-portfolio] > summary').click();
        assert.deepEqual(await modelRows(page), m1, 'same selection after 자료 새로고침');
        phase = 'STABLE_RELOAD';await page.reload();await page.locator('main').waitFor();await settle(page);await page.locator('[data-leaderboard-rank]').first().waitFor();
        await page.locator('[data-model-portfolio] > summary').click();assert.deepEqual(await modelRows(page), m1, 'same selection after a reload (the same publication read again)');
        // 7. Performance: one S06 paint of every Universe row, and a fresh compute of the official result (new quotes object).
        phase = 'PERF';const t = await page.evaluate(async () => {
          const R = leaderPage, inputs = publicScreens['sec-qgv2.json'], c0 = performance.now();QgvScores.compute({ identities: R.identities, v2Inputs: inputs, quotes: {}, official: R.official, publication: QgvScores.pagePublication().publication });const compute = performance.now() - c0;
          const p0 = performance.now();paintLeaderboardScreen();const paint = performance.now() - p0;await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
          return { compute, paint, rows: document.querySelectorAll('[data-leaderboard-row]').length }; });
        perf.push({ width, ...t });assert.ok(t.paint < 2000 && t.compute < 3000, 'S06 stays responsive: paint ' + t.paint.toFixed(0) + 'ms, compute ' + t.compute.toFixed(0) + 'ms');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide horizontal scroll');
        assert.equal(await page.evaluate(() => Object.keys(localStorage).filter((k) => /price|quote|model/i.test(k) && /\d{2}\.\d/.test(localStorage.getItem(k) || '')).length), 0, 'no price or selection stored');
        assert.deepEqual(external, []);assert.equal(errors, 0);
        console.log('INFO ' + width + ' codes=' + codes + ' ranked=' + ranked.length + ' qg=' + ids.filter((id) => R[id].qg !== null).length + ' target_in_universe=' + X.tin.length + ' outside=' + X.outside.join(',') + ' N20=' + X.pickedN.N20.length + ' (N10 ' + X.pickedN.N10.length + ', N15 ' + X.pickedN.N15.length + ')');
        console.log('PERF ' + width + ' paint_ms=' + t.paint.toFixed(1) + ' compute_ms=' + t.compute.toFixed(1) + ' rows=' + t.rows);
        pass++;console.log('PASS D12 Universe leaderboard ' + width + ' (synthetic fixture + synthetic central publication)');
      } catch (e) { fail++;console.log('FAIL D12 Universe leaderboard ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 6).join(' | ') + ' @' + ((e.stack || '').match(/browser_test.js:(\d+)/) || [])[1] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
