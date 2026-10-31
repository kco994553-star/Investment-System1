'use strict';
/* 'V 일치' (owner instruction 2026-10-19: '동일 입력·버전·설정에서 모든 화면의 값과 상태가 같은지 시험한다') at 390 and 1280, under
   DC-31 (owner decision 2026-10-31, device V abolished: every screen shows only the central V of qgv-official.json, read once on
   open; no Universe read, no price). ONE synthetic central publication (qgv_official_fixture.js), the same published input (the
   strictly valid synthetic sec-qgv2.json, qgv_v2_fixture.js) and the same settings. A round trip visits every screen that shows a
   V, a V state/reason, a QGV total, an official rank, the QG 참고 목록 membership or the publication basis: S06 rows + outside list +
   V panel + model portfolio N10/N15/N20, the company detail (S04 QGV card) and its stat radar, the Universe company page and its
   radar, the playbook candidates (ranked list + Q·G 참고 list) and the S13 two-level weights compare (official column + personal
   column). For a sample of rows (TARGET rows of every group, a ranked Universe-only code, a value-trap-gate code, a financial code,
   outside the Universe, and the Universe page of a TARGET company = the same security) the data-cx-* marks (QgvScores.marks: V,
   V status/reason, total, official rank, QG order, group, scope, publication id, its generation time, re-read failure) are
   IDENTICAL on every screen, equal the shared official page result, and the visible numbers equal the marks.
   Phases: 1. the publication read on open; 2. S13 device profile = a non-official product preset (공격형 → 수비형 candidates): the
   personal values (labelled 개인) change and agree with the recompute from the published factor scores, while every official mark
   and the N sets stay; 3. a failed re-read (503): every screen keeps the same values (the last central V, never a device V) and
   names the same failure; 4. a new valid publication (other ranks): every screen moves to it together (no screen keeps the old id). */
let phase = 'START', checks = 0;
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, E = '[data-qgv2-weights-editor]';
const CX = ['data-cx-v', 'data-cx-v-status', 'data-cx-v-reason', 'data-cx-total', 'data-cx-rank', 'data-cx-qg-order', 'data-cx-group', 'data-cx-scope', 'data-cx-read-id', 'data-cx-read-at', 'data-cx-read-failure'];
const READ = ['data-cx-read-id', 'data-cx-read-at', 'data-cx-read-failure'];
const fmt1 = (v) => (Math.round(v * 10) / 10).toFixed(1), fmtKo = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
const eq = (a, b, m) => { checks++;assert.deepEqual(a, b, m); }, ok = (c, m) => { checks++;assert.ok(c, m); };
const pick = (el, names) => Object.fromEntries(names.map((n) => [n, el.getAttribute(n)]));
// The shared official page result (the same call the screens make: officialPage under the S06 preset view) reduced to the marks
// of the sample ids, and the registered publication.
const expected = (page, ids) => page.evaluate((ids) => {
  const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), C = QgvScores.presetView(P, { v2Inputs: inputs }), b = QgvScores.publicationBasis();
  const out = {};for (const id of ids) { const row = QgvScores.rowOf(C, id);out[id] = { marks: QgvScores.marks(row, b, window), v: row ? row.primary.v : null, total: row ? row.primary.total : null, rank: row ? row.rank : null, gate: !!row && row.primary.value_trap_gate === true, id: row ? row.company_id : null }; }
  return { out, basis: b, source: P.source, profile: C.profile.id };
}, ids);
async function waitMarks(page, sel, want, label) {
  try { await page.waitForFunction(([s, w]) => { const n = document.querySelector(s);return !!n && n.getAttribute('data-cx-read-id') === w.id && n.getAttribute('data-cx-read-failure') === w.failure; }, [sel, want], { timeout: 12000 }); } catch (_) { /* asserted below with the actual value */ }
  const got = await page.evaluate((s) => { const n = document.querySelector(s);return n ? [n.getAttribute('data-cx-read-id'), n.getAttribute('data-cx-read-failure')] : null; }, sel);
  eq(got, [want.id, want.failure], label + ' names the current read (' + sel + ')');
}
const marksOf = (page, sel) => page.evaluate(([s, names]) => { const n = document.querySelector(s);return n ? Object.fromEntries(names.map((k) => [k, n.getAttribute(k)])) : null; }, [sel, CX]);
async function s06(page, ids, want) {
  await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-table]').waitFor();await page.locator('[data-v-coverage]').first().waitFor();
  await page.waitForFunction(() => typeof leaderPage === 'object' && leaderPage && leaderPage === QgvScores.officialPage(window, { v2Inputs: publicScreens[Qgv2Inputs.FILE], identities: identityCompanies }));
  await waitMarks(page, '[data-leaderboard-screen]', want, 'S06');await waitMarks(page, '[data-v-coverage]', want, 'V panel');
  if ((await page.locator('[data-model-portfolio]').getAttribute('open')) === null) await page.locator('[data-model-portfolio] > summary').click();
  return page.evaluate(([ids, names, read]) => {
    const rows = {}, visible = {};
    for (const id of ids) { const n = document.querySelector('[data-leaderboard-row="' + CSS.escape(id) + '"]') || document.querySelector('[data-leaderboard-outside-row="' + CSS.escape(id) + '"]');if (!n) continue;rows[id] = Object.fromEntries(names.map((k) => [k, n.getAttribute(k)]));
      const t = n.querySelector('[data-leaderboard-qgv2]')?.textContent || '', m = t.match(/ · V ([\d.]+|—) · /);
      visible[id] = { rank: n.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank ?? null, total: n.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal ?? null, v: m ? m[1] : null, qg: n.querySelector('[data-leaderboard-unranked="QG_REFERENCE"]')?.dataset.qgOrder ?? null, outside: n.matches('[data-leaderboard-outside-row]') }; }
    const card = document.querySelector('[data-leaderboard-screen]'), panel = document.querySelector('[data-v-coverage]');
    const model = [...document.querySelectorAll('[data-model-portfolio] [data-model-row]')].map((r) => [r.dataset.modelRow, r.dataset.modelRank, r.dataset.modelIn, r.cells[2].textContent]);
    return { rows, visible, card: Object.fromEntries(read.map((k) => [k, card.getAttribute(k)])), panel: Object.fromEntries(read.map((k) => [k, panel.getAttribute(k)])), basisLine: panel.querySelector('[data-central-basis]')?.textContent || null,
      basisId: panel.querySelector('[data-central-basis]')?.dataset.centralBasis || null, model, profile: document.querySelector('[data-model-counts]')?.dataset.modelProfile || null };
  }, [ids, CX, READ]);
}
async function radarSettled(page, want) {
  await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return c && c.dataset.srReason !== 'PENDING'; });
  await waitMarks(page, '[data-stat-radar]', want, 'radar');
  const m = await marksOf(page, '[data-stat-radar]'), c = await page.evaluate(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return { score: c.dataset.srScore, reason: c.dataset.srReason }; });
  return { marks: m, visible: c };
}
async function company(page, id, want) {
  await page.evaluate((x) => { location.hash = 'company/' + encodeURIComponent(x); }, id);await page.locator('[data-company-card="qgv"] [data-cx-company]').waitFor();
  await waitMarks(page, '[data-company-card="qgv"] [data-cx-company]', want, 'company ' + id);
  const marks = await marksOf(page, '[data-company-card="qgv"] [data-cx-company]');
  const visible = await page.evaluate(() => { const q = (s) => document.querySelector('[data-company-card="qgv"] ' + s);return { v: q('[data-qgv="V"]')?.textContent.trim() ?? null, total: q('[data-qgv="total"]')?.textContent.trim() ?? null, rank: q('[data-qgv="rank"] .num')?.textContent ?? null, qg: q('[data-qgv-rank="QG_REFERENCE"]')?.dataset.qgOrder ?? null, outside: !!q('[data-qgv-rank="OUTSIDE_UNIVERSE"]') }; });
  return { marks, visible, radar: await radarSettled(page, want) };
}
async function universe(page, code, want) {
  await page.evaluate((x) => { location.hash = 'company/' + encodeURIComponent(x); }, code);
  await page.waitForFunction((c) => { const p = document.querySelector('[data-universe-page]');return p && p.dataset.universePage === c && p.dataset.universeV !== 'PENDING'; }, code);
  await waitMarks(page, '[data-universe-card="qgv"]', want, 'Universe page ' + code);
  const marks = await marksOf(page, '[data-universe-card="qgv"]');
  const visible = await page.evaluate(() => ({ score: document.querySelector('[data-universe-card="qgv"] [data-uc-axis="V"]')?.getAttribute('data-uc-score') ?? null, total: document.querySelector('[data-universe-card="qgv"] [data-uc-total]')?.dataset.ucTotal ?? null, same: document.querySelector('[data-uc-same-security]')?.dataset.ucSameSecurity ?? null }));
  return { marks, visible, radar: await radarSettled(page, want) };
}
async function playbook(page, tickers, want) {
  await page.evaluate(() => { location.hash = 'playbook'; });const w = page.locator('[data-target-v1]');await w.locator('[data-target-rank-row]').first().waitFor();
  const rows = await page.evaluate(([tickers, names]) => { const out = {};for (const t of tickers) { const n = document.querySelector('[data-target-v1] [data-target-rank-row="' + t + '"]') || document.querySelector('[data-target-v1] [data-target-qg-row="' + t + '"]');if (!n) continue;
    out[t] = { marks: Object.fromEntries(names.map((k) => [k, n.getAttribute(k)])), list: n.matches('[data-target-rank-row]') ? 'RANKED' : 'QG', c1: n.cells[1].textContent, c2: n.cells[2].textContent }; }return out; }, [tickers, CX]);
  for (const [t, r] of Object.entries(rows)) eq([r.marks['data-cx-read-id'], r.marks['data-cx-read-failure']], [want.id, want.failure], 'playbook ' + t + ' read');
  return rows;
}
async function s13(page, preset, want) {
  await page.evaluate(() => { location.hash = 'profiles'; });await page.locator(E).waitFor();
  await page.locator(E + ' [data-product-preset="' + preset + '"]').click();await page.locator(E + ' [data-product-preset-status="' + preset + '"]').waitFor();
  await page.locator(E + ' [data-qgv2w-compare]').click();await page.locator(E + ' [data-qgv2w-result-state="READY"]').waitFor();
  await waitMarks(page, E + ' [data-qgv2w-results]', want, 'S13');
  return page.evaluate(([names, sel]) => ({ label: document.querySelector(sel + ' [data-qgv2w-result-label]')?.textContent || '', title: document.querySelector(sel + ' [data-qgv2w-top-title]')?.dataset.qgv2wTopTitle || null,
    rows: Object.fromEntries([...document.querySelectorAll(sel + ' [data-qgv2w-compare-row]')].map((r) => [r.dataset.qgv2wCompareRow, { marks: Object.fromEntries(names.map((k) => [k, r.getAttribute(k)])),
      personal: { total: r.getAttribute('data-cx-personal-total'), v: r.getAttribute('data-cx-personal-v'), rank: r.getAttribute('data-cx-personal-rank') }, official: r.cells[1].textContent, mine: r.cells[2].textContent }])) }), [CX, E]);
}
// The engine's personal result for a product preset over the same population, quotes and reference rows as the shared page result.
// DC-31: the recompute from the published factor scores (QgvScores.compute({publication, weights})), as the S13 compare makes it.
const personalOf = (page, presetKey) => page.evaluate(async (key) => {
  const inputs = publicScreens[Qgv2Inputs.FILE], catalog = await deviceCatalog().catch(() => null), ids = catalog ? DeviceWatchlist.identities(catalog) : identityCompanies, R = QgvScores.officialPage(window, { v2Inputs: inputs, identities: ids }), pub = QgvScores.pagePublication().publication;
  const id = Object.keys(QgvV2.USER_PRESETS).find((k) => QgvV2.USER_PRESETS[k].key === key), d = QgvV2.userPreset(id);
  const mine = QgvScores.compute({ identities: R.identities, v2Inputs: inputs, quotes: {}, official: R.official, referenceRows: QgvScores.pageReferences(), publication: pub, gate: d.gate, weights: d.weights, typeWeights: d.type_weights });
  const n = (v) => (typeof v === 'number' && Number.isFinite(v) ? String(v) : 'NA');
  return Object.fromEntries(identityCompanies.map((c) => { const r = mine.rows[c.company_id];return [c.company_id, { total: n(r && r.personal.total), v: n(r && r.personal.v), rank: r && Number.isInteger(r.personal_rank) ? String(r.personal_rank) : '' }]; }));
}, presetKey);

// One round trip over every screen; every mark of every sample id must equal the shared result (and so each other).
async function roundTrip(page, label, S, want) {
  const ids = [...S.target, ...S.codes], E0 = await expected(page, [...ids, S.sameCode]), X = E0.out, seen = {};
  eq(E0.source, 'PUBLICATION', label + ' the shared result is the central publication');eq(E0.basis.read_id, want.id, label + ' publication id');
  const add = (id, screen, m) => { (seen[id] = seen[id] || {})[screen] = m; };
  // S06 (rows, outside list, V panel, model portfolio) → company → back → V panel → playbook → company of another code → S06.
  const L = await s06(page, ids, want);
  for (const k of READ) { eq(L.card[k], X[S.target[0]].marks[k], label + ' S06 card ' + k);eq(L.panel[k], X[S.target[0]].marks[k], label + ' V panel ' + k); }
  eq(L.basisId, want.id, label + ' V panel basis line names the publication');ok(want.failure ? L.basisLine.includes('다시 읽기 실패(' + want.failure + ') · 마지막 게시본 표시') : !L.basisLine.includes('다시 읽기 실패'), label + ' V panel names the re-read failure: ' + L.basisLine);
  for (const id of ids) { ok(L.rows[id], label + ' S06 shows ' + id);add(id, 'S06', L.rows[id]);const v = L.visible[id], x = X[id];
    eq(v.rank, x.rank === null ? null : String(x.rank), label + ' S06 rank ' + id);if (!v.outside) eq(v.total, x.total === null ? 'NOT_AVAILABLE' : fmt1(x.total), label + ' S06 total ' + id);
    if (v.v !== null) eq(v.v, x.v === null ? '—' : fmt1(x.v), label + ' S06 V ' + id);eq(v.qg, L.rows[id]['data-cx-group'] === 'QG_REFERENCE' ? L.rows[id]['data-cx-qg-order'] : null, label + ' S06 QG order ' + id); }
  for (const [id, rank, , total] of L.model) { const x = X[id] || (await expected(page, [id])).out[id];eq(rank, String(x.rank), label + ' model rank = official rank ' + id);eq(total, fmt1(x.total), label + ' model total ' + id); }
  for (const id of S.target) { const C = await company(page, id, want), x = X[id];add(id, 'COMPANY', C.marks);add(id, 'COMPANY_RADAR', C.radar.marks);
    eq(C.visible.v, x.v === null ? C.visible.v : fmtKo(x.v), label + ' company V ' + id);if (x.v === null) ok(!/\d/.test(C.visible.v), label + ' company V NA ' + id);
    if (x.total === null) ok(!/\d/.test(C.visible.total), label + ' company total NA ' + id);else eq(C.visible.total, fmtKo(x.total), label + ' company total ' + id);
    eq(C.visible.rank, x.rank === null ? null : String(x.rank), label + ' company rank ' + id);eq(C.visible.qg, C.marks['data-cx-group'] === 'QG_REFERENCE' ? C.marks['data-cx-qg-order'] : null, label + ' company QG order ' + id);
    eq(C.visible.outside, C.marks['data-cx-scope'] === 'OUTSIDE_UNIVERSE', label + ' company outside line ' + id);
    eq(C.radar.visible.score, x.v === null ? 'NA' : C.radar.visible.score, label + ' radar V NA ' + id);if (x.v !== null) ok(Math.abs(Number(C.radar.visible.score) - x.v) <= 1e-9, label + ' radar V ' + id);
    else eq(C.radar.visible.reason, C.marks['data-cx-v-reason'] || C.radar.visible.reason, label + ' radar V reason ' + id); }
  const L2 = await s06(page, ids, want);eq(L2.rows, L.rows, label + ' S06 the same after the company page');eq(L2.model, L.model, label + ' N sets the same after the company page');
  const P = await playbook(page, ids.map((id) => S.ticker[id]).filter(Boolean), want);
  for (const id of ids) { const x = X[id], t = S.ticker[id], r = P[t], grp = x.marks['data-cx-group'];
    if (grp === 'RANKED' || grp === 'QG_REFERENCE') ok(r, label + ' playbook lists ' + t);if (!r) continue;add(id, 'PLAYBOOK', r.marks);
    if (grp === 'RANKED') { eq([r.list, r.c1, r.c2], ['RANKED', String(x.rank), x.total.toFixed(1)], label + ' playbook rank/total ' + t); }
    else if (grp === 'QG_REFERENCE') eq([r.list, r.c1, r.c2], ['QG', x.marks['data-cx-qg-order'], x.total.toFixed(1)], label + ' playbook QG order/total ' + t);
    else eq([r.list, r.c1, r.c2], ['RANKED', '—', 'NA'], label + ' playbook row without a rank ' + t + ' (' + grp + ')'); }
  for (const code of [...S.codes, S.sameCode]) { const U = await universe(page, code, want), x = X[code];add(code, 'UNIVERSE', U.marks);add(code, 'UNIVERSE_RADAR', U.radar.marks);
    eq(U.visible.score, x.v === null ? 'NA' : U.visible.score, label + ' Universe V NA ' + code);if (x.v !== null) ok(Math.abs(Number(U.visible.score) - x.v) <= 1e-9, label + ' Universe V ' + code);
    if (x.total === null) ok(U.visible.total === null || U.visible.total === 'NA', label + ' Universe total NA ' + code);else ok(Math.abs(Number(U.visible.total) - x.total) <= 1e-9, label + ' Universe total ' + code); }
  { const U = seen[S.sameCode];eq(U.UNIVERSE, X[S.target[0]].marks, label + ' ' + S.sameCode + ' Universe page = the ' + S.target[0] + ' row (same security)'); }
  const L3 = await s06(page, ids, want);eq(L3.rows, L.rows, label + ' S06 the same after the round trip');eq(L3.model, L.model, label + ' N sets the same after the round trip');
  // Every screen of every sample id: the same marks, equal to the shared result.
  for (const [id, screens] of Object.entries(seen)) for (const [screen, m] of Object.entries(screens)) eq(m, X[id].marks, label + ' ' + screen + ' marks ' + id);
  return { X, L, seen, model: L.model };
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const P1 = F.strictPayload();
  console.log('INFO sec-qgv2.json basis=SYNTHETIC_FIXTURE codes=' + Object.keys(P1.records).length + ' · central V = synthetic qgv-official.json ' + O.PUB.publication_id.slice(0, 14) + '… then ' + O.PUB2.publication_id.slice(0, 14) + '… (no price)');
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(P1) }));
      // The served central publication: 1 = the base one, 'FAIL' = 503 (a failed re-read), 2 = the second valid one. Requests counted.
      const served = { pub: 1, reads: 0 };await context.route('**/qgv-official.json*', (r) => { served.reads++;return r.fulfill(served.pub === 'FAIL' ? { status: 503, contentType: 'text/plain', body: 'synthetic unavailable' } : { status: 200, contentType: 'application/json', body: served.pub === 2 ? O.PUB2_TEXT : O.PUB_TEXT }); });
      const page = await context.newPage();let errors = 0;page.on('pageerror', (e) => { errors++;console.log('PAGEERROR ' + String(e && e.message).slice(0, 200)); });
      const external = [], device = [];page.on('request', (r) => { const u = r.url();if (!/^(data|blob):/.test(u) && new URL(u).origin !== ORIGIN) external.push(u);if (!/\.(js|css|png|svg|woff2?)(\?|$)/.test(u) && /sheets|workers\.dev|price-store/i.test(u)) device.push(u); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      const before = checks;
      try {
        // A re-read of the central publication (as '자료 새로고침' does: public-data-updated, not a freshness re-judge).
        const reread = async (want) => {
          await page.evaluate(() => { window.dispatchEvent(new CustomEvent('public-data-updated', { detail: { reason: 'APPLIED' } })); });
          await page.waitForFunction((w) => { const R = QgvScores.pagePublication();return R.publication && R.publication.publication_id === w.id && (R.last_attempt_reason || '') === w.failure; }, want);
        };
        // 1. The publication read on open; the sample is chosen from the shared result and its groups are asserted.
        phase = 'OPEN ' + width;await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
        await page.waitForFunction(() => QgvScores.pagePublication().publication !== null);
        const S = await page.evaluate(() => {
          const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), rows = P.computed.rows;
          const codes = Object.entries(rows).filter(([k]) => Object.hasOwn(inputs.records, k)), V = (r) => r.primary.coverage && r.primary.coverage.axes ? r.primary.coverage.axes.V.status : null;
          const ranked = codes.find(([, r]) => Number.isInteger(r.rank) && r.primary.value_trap_gate !== true), gate = codes.find(([, r]) => Number.isInteger(r.rank) && r.primary.value_trap_gate === true), fin = codes.find(([, r]) => r.qg_reference && V(r) === 'NOT_APPLICABLE');
          const ticker = Object.fromEntries(Object.values(rows).map((r) => [r.company_id, r.ticker]));
          return { target: ['amd', 'nvda', 'msft', 'googl', 'tokyo_electron'], codes: [ranked && ranked[0], gate && gate[0], fin && fin[0]].filter(Boolean), sameCode: 'NASDAQ:AMD', ticker };
        });
        eq(S.codes.length, 3, 'fixture has a ranked Universe-only code, a value-trap gate code and a financial code: ' + S.codes.join(','));
        const want1 = { id: O.PUB.publication_id, failure: '' }, A = await roundTrip(page, 'publication 1', S, want1), G = (id) => A.X[id].marks['data-cx-group'];
        eq([G('amd'), G('googl'), G('tokyo_electron'), G(S.codes[0]), G(S.codes[1]), G(S.codes[2])], ['RANKED', 'QG_REFERENCE', 'CHECK_DATA', 'RANKED', 'RANKED', 'QG_REFERENCE'], 'sample groups');
        eq(A.X.amd.rank, O.RANKS['TARGET:amd'], 'amd: the published rank of its TARGET row');
        eq(A.X.tokyo_electron.marks['data-cx-scope'], 'OUTSIDE_UNIVERSE', 'outside the Universe');eq(A.X.googl.marks['data-cx-v-status'], 'NOT_APPLICABLE', 'financial V not defined');
        eq(A.X[S.codes[2]].marks['data-cx-v-reason'], 'FINANCIAL_PROFILE_V_NOT_DEFINED', 'financial code V reason');
        ok(A.X[S.codes[1]].gate, 'gate row');ok(A.model.length > 0 && !A.model.some((m) => m[0] === S.codes[1]), 'the value-trap gate row is excluded from the N sets');
        ok(A.model.some((m) => m[0] === 'amd' || m[0] === S.codes[0]), 'a ranked sample row is in the N sets');
        // S13 official column = the official marks of the same rows (the shared result, official default profile).
        phase = 'S13_OFFICIAL ' + width;const base13 = await s13(page, 'aggressive', want1);
        for (const id of S.target) { eq(base13.rows[id].marks, A.X[id].marks, 'S13 official marks ' + id);const x = A.X[id];
          eq(base13.rows[id].official, x.total === null ? '— (—)' : fmt1(x.total) + (x.rank !== null ? ' (' + x.rank + ')' : x.marks['data-cx-group'] === 'QG_REFERENCE' ? ' (QG 참고 ' + x.marks['data-cx-qg-order'] + ')' : ' (—)'), 'S13 official text ' + id); }
        // 2. Device profile = non-official product presets (공격형, then 수비형): personal values (개인) follow the engine over the same
        //    population and read and change with the preset; official marks, ranks and N sets do not change anywhere.
        phase = 'PROFILE ' + width;const pers = {};
        for (const key of ['aggressive', 'defensive']) { const res = key === 'aggressive' ? base13 : await s13(page, key, want1);
          ok(/^개인 설정 미리보기 · 공식 점수 아님 · qgv-v2\/custom\//.test(res.label), key + ' labelled 개인 설정 미리보기 · 공식 점수 아님');eq(res.title, 'PERSONAL', key + ' top list is the personal order');
          const want = await personalOf(page, key);pers[key] = {};
          for (const id of S.target) { eq(res.rows[id].personal, want[id], key + ' personal ' + id);pers[key][id] = res.rows[id].personal;eq(res.rows[id].marks, A.X[id].marks, key + ' official marks unchanged ' + id);
            if (want[id].total === 'NA') eq(res.rows[id].mine, '— (—)', key + ' personal text NA ' + id);
            else { ok(res.rows[id].mine.startsWith(fmt1(Number(want[id].total)) + ' ('), key + ' personal total text ' + id);if (want[id].rank) ok(res.rows[id].mine.endsWith(' (' + want[id].rank + ')'), key + ' personal rank text ' + id); } }
          // The company table of the selected company: '공식' = the official values, '내 설정' = the personal values.
          await page.locator(E + ' [data-qgv2w-company]').selectOption('amd');const tbl = await page.locator(E + ' [data-qgv2w-company-table="amd"] tbody tr').evaluateAll((rs) => Object.fromEntries(rs.map((r) => [r.cells[0].textContent, [r.cells[1].textContent, r.cells[2].textContent]])));
          eq(tbl.QGV, [fmt1(A.X.amd.total), fmt1(Number(want.amd.total))], key + ' company table QGV');eq(tbl.V, [fmt1(A.X.amd.v), fmt1(Number(want.amd.v))], key + ' company table V');eq(tbl['순위'][0], String(A.X.amd.rank), key + ' company table official rank');
        }
        ok(S.target.some((id) => pers.aggressive[id].total !== pers.defensive[id].total), 'the personal totals change with the device profile');
        const B = await roundTrip(page, 'after profile', S, want1);eq(B.X, A.X, 'official values unchanged by the device profile');eq(B.model, A.model, 'N sets unchanged by the device profile');
        // 3. A failed re-read (503): every screen keeps the last central V and names the same failure (never a device V).
        phase = 'FAILED_REREAD ' + width;served.pub = 'FAIL';const wantF = { id: O.PUB.publication_id, failure: 'OFFICIAL_UNAVAILABLE' };await reread(wantF);
        const C = await roundTrip(page, 'after failed re-read', S, wantF);
        for (const id of Object.keys(A.X)) { const strip = (m) => Object.fromEntries(Object.entries(m).filter(([k]) => k !== 'data-cx-read-failure'));eq(strip(C.X[id].marks), strip(A.X[id].marks), 'kept values after the failed re-read ' + id); }
        eq(C.model, A.model, 'N sets kept after the failed re-read');
        { const c13 = await s13(page, 'aggressive', wantF);for (const id of S.target) eq(c13.rows[id].marks, C.X[id].marks, 'S13 after the failed read ' + id); }
        // 4. A new valid publication (other published ranks): every screen moves to it together.
        phase = 'PUBLICATION2 ' + width;served.pub = 2;const want2 = { id: O.PUB2.publication_id, failure: '' };await reread(want2);
        const D = await roundTrip(page, 'publication 2', S, want2);
        ok(Object.keys(D.X).some((id) => D.X[id].rank !== A.X[id].rank), 'the new publication changed some rank');
        for (const [id, screens] of Object.entries(D.seen)) for (const [screen, m] of Object.entries(screens)) ok(m['data-cx-read-id'] !== O.PUB.publication_id, 'no old publication id on ' + screen + ' ' + id);
        { const d13 = await s13(page, 'aggressive', want2);for (const id of S.target) eq(d13.rows[id].marks, D.X[id].marks, 'S13 on read 2 ' + id); }
        eq(served.reads, 3, 'three reads of qgv-official.json (open, failed re-read, new publication), nothing else');eq(device, [], 'no device price request');eq(external, [], 'no outside request');eq(errors, 0, 'no page error');
        console.log('INFO ' + width + ' sample=' + [...S.target, ...S.codes, S.sameCode].join(',') + ' N20=' + A.model.length + ' checks=' + (checks - before));
        pass++;console.log('PASS V cross-screen consistency ' + width + ' (synthetic fixture + synthetic central publications)');
      } catch (e) { fail++;console.log('FAIL V cross-screen consistency ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 12).join(' | ') : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail + ' checks=' + checks);if (fail) process.exitCode = 1;
})();
