'use strict';
// ONE shared Universe read (owner rule 2026-10-19; private-subset-view.js readStatus/prices/priceBasis) on the REAL user path at
// 390 and 1280: the user's own '내 기기 기준' Universe read (the real PrivateSubsetView with a stubbed sheet session in RAM) is the
// last successful read for every screen. For the same inputs and settings, S06 (leaderboard), the TARGET company detail, the
// Universe company page, the stat radar and the V coverage panel show the same V and the same states:
//   1. after the read;
//   2. after navigating away (the view is disposed) and back — the panel no longer falls back to '가격 미연결';
//   3. after a re-read that FAILS — the kept read stays, and the failure is shown next to it (view + panel);
//   4. after '자료 새로고침' with a new publication — every screen recomputes from the new inputs with the same kept prices.
// Settings: after the user changes the official preset and the value-trap gate on S06, every screen's total, V and state follow
// the same settings (QgvScores.pageProfile), also after navigating away and back and after '자료 새로고침'.
// Also: no storage write of prices (localStorage, sessionStorage, IndexedDB, Cache Storage), no Worker / Sheets / outside request
// beyond the user-pressed reads, and '기기 결과 지우기' still clears.
// Q·G side: the strictly valid synthetic fixture (qgv_v2_fixture.js strictPayload; day 2 = the same file re-published with one
// changed total debt, still valid). Price side: SYNTHETIC FIXTURE PRICES ONLY (F.strictUniverseValues: made-up numbers, never real prices).
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), path = require('node:path'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const SQ = require(path.join(__dirname, '../src/investment_system/product/web_assets/sec-qgv2.js'));
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const PRICED = 'nvda', UNPRICED = 'msft', UNI = 'NYSE:MMM', CHANGED = 'NYSE:ACN', PRESET = 'growth';
const fmt1 = (v) => (Math.round(v * 10) / 10).toFixed(1), fmtKo = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
const close = (a, b) => Math.abs(a - b) <= 1e-9;
function day1() { return F.strictPayload(); }
function day2() {
  const p = F.strictPayload(), r = p.records[CHANGED], at = '2026-10-14T22:30:00Z';
  p.as_of = at;p.last_shard_index = (p.last_shard_index + 1) % p.shard_count;r.acquired_at = at;
  r.v_inputs_v2.total_debt = { ...r.v_inputs_v2.total_debt, value: r.v_inputs_v2.total_debt.value * 8 };  // EV changes on every V basis
  SQ.validate(p);return p;
}
// The shared page result of the open page (the same call S06 and the V panel make), reduced to V per row and the panel counts.
const shared = (page) => page.evaluate(async () => {
  const inputs = publicScreens[Qgv2Inputs.FILE], R = await QgvScores.pageResult(window, { v2Inputs: inputs, catalog: await deviceCatalog().catch(() => null), identities: identityCompanies, preset: qgv2Profile.preset, gate: qgv2Profile.gate });
  const fin = (x) => typeof x === 'number' && Number.isFinite(x), cov = QgvScores.vCoverage(R, inputs), v = {}, total = {}, reason = {};
  for (const [k, r] of Object.entries(R.computed.rows)) { const p = r.primary;v[k] = fin(p.v) ? p.v : null;total[k] = fin(p.total) ? p.total : null;reason[k] = p.coverage && p.coverage.axes && p.coverage.axes.V ? p.coverage.axes.V.reason : null; }
  return { asOf: inputs.as_of, basis: R.price_basis, quotes: R.quotes, v, total, reason, profile: { ...qgv2Profile }, shared: { ...QgvScores.pageProfile() }, cov: { connected: cov.connected, v_full: cov.v ? cov.v.full : null, v_general: cov.v ? cov.v.general : null, qg: cov.qg_only_total ? cov.qg_only_total.full : null } };
});
async function settle(page, sel) { await page.locator(sel).first().waitFor();await page.waitForTimeout(150); }
async function leaderboard(page, want) {
  await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-table]').waitFor();
  await page.locator('[data-v-coverage="' + want + '"]').waitFor();if (want === 'READY') await page.locator('[data-leaderboard-rank]').first().waitFor();
  await page.waitForFunction(() => typeof leaderPage === 'object' && leaderPage && leaderPage.inputs === publicScreens[Qgv2Inputs.FILE]);await page.waitForTimeout(150);
  return page.evaluate(() => {
    const rows = {}, totals = {};for (const tr of document.querySelectorAll('[data-leaderboard-row]')) { const t = tr.querySelector('[data-leaderboard-qgv2]')?.textContent || '', m = t.match(/ · V ([\d.]+|—) · /);rows[tr.dataset.leaderboardRow] = m ? m[1] : '—';totals[tr.dataset.leaderboardRow] = tr.querySelector('[data-leaderboard-total]')?.dataset.leaderboardTotal ?? null; }
    const q = (sel, a) => document.querySelector(sel)?.getAttribute(a) ?? null;
    return { rows, totals, preset: document.querySelector('[data-qgv2-preset][aria-pressed="true"]')?.dataset.qgv2Preset || null, gate: document.querySelector('input[data-qgv2-gate]')?.checked ?? null, panel: { state: q('[data-v-coverage]', 'data-v-coverage'), v_full: q('[data-v-full]', 'data-v-full'), v_general: q('[data-v-general]', 'data-v-general'), qg: q('[data-qg-only-full]', 'data-qg-only-full'), noPrice: !!document.querySelector('[data-v-coverage-state]:not([data-v-read-failure])'),
      failure: q('[data-v-read-failure]', 'data-v-read-failure'), kept: q('[data-v-read-kept]', 'data-v-read-kept'), calc: document.querySelector('[data-v-calc-version]')?.textContent || '' },
      leaderV: Object.fromEntries(Object.entries(leaderScores().rows).map(([k, r]) => [k, Number.isFinite(r.primary.v) ? r.primary.v : null])), leaderT: Object.fromEntries(Object.entries(leaderScores().rows).map(([k, r]) => [k, Number.isFinite(r.primary.total) ? r.primary.total : null])) };
  });
}
async function radarV(page) {
  await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return c && c.dataset.srReason !== 'PENDING'; });
  return page.evaluate(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return { score: c.dataset.srScore, reason: c.dataset.srReason, qgOnly: c.querySelector('[data-sr-total-qg-only]')?.textContent || null }; });
}
async function companyDetail(page, id) {
  await page.evaluate((x) => { location.hash = 'company/' + x; }, id);await page.locator('[data-company-card="qgv"] [data-qgv="V"]').waitFor();
  await page.waitForFunction(() => document.querySelector('[data-stat-radar]'));await page.waitForTimeout(300);
  return { v: (await page.locator('[data-company-card="qgv"] [data-qgv="V"]').textContent()).trim(), total: (await page.locator('[data-company-card="qgv"] [data-qgv="total"]').textContent()).trim(), radar: await radarV(page) };
}
async function universePage(page, code) {
  await page.evaluate((x) => { location.hash = 'company/' + encodeURIComponent(x); }, code);
  await page.waitForFunction((c) => document.querySelector('[data-universe-page]')?.dataset.universePage === c && document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING', code);
  return { total: await page.evaluate(() => document.querySelector('[data-universe-card="qgv"] [data-uc-total]')?.dataset.ucTotal ?? null), score: await page.locator('[data-universe-card="qgv"] [data-uc-axis="V"]').getAttribute('data-uc-score'), priced: await page.locator('[data-universe-page]').getAttribute('data-universe-v'), radar: await radarV(page) };
}
// Every screen against the one shared result: same V (shown rounding of the same number) and the same 'no V' state.
async function sameEverywhere(page, label, want) {
  const L = await leaderboard(page, want), R = await shared(page);
  assert.equal(L.panel.state, want, label + ' panel state');
  if (want === 'READY') {
    assert.equal(L.panel.noPrice, false, label + ' panel never says 가격 미연결 while a read is kept');
    assert.equal(Number(L.panel.v_full), R.cov.v_full, label + ' panel V count == shared result');assert.equal(Number(L.panel.v_general), R.cov.v_general);assert.equal(Number(L.panel.qg), R.cov.qg);
  } else assert.equal(L.panel.v_full, '', label + ' no V count without a read');
  // Settings: S06 shows the official preset/gate, and the shared page profile every other screen reads is the same one.
  assert.deepEqual(R.shared, { preset: R.profile.preset, gate: R.profile.gate }, label + ' shared page profile == S06 qgv2Profile');
  assert.equal(L.preset, R.profile.preset || 'balanced', label + ' S06 preset button');if (R.profile.gate !== null) assert.equal(L.gate, R.profile.gate, label + ' S06 gate toggle');
  for (const [id, shown] of Object.entries(L.totals)) { const t = R.total[id];assert.equal(shown, t === null || t === undefined ? 'NOT_AVAILABLE' : fmt1(t), label + ' S06 total ' + id);assert.ok(Object.is(L.leaderT[id], t === undefined ? null : t), label + ' S06 engine total ' + id); }
  for (const [id, shown] of Object.entries(L.rows)) { const v = R.v[id];assert.equal(shown, v === null || v === undefined ? '—' : fmt1(v), label + ' S06 V ' + id);assert.ok(Object.is(L.leaderV[id], v === undefined ? null : v), label + ' S06 engine V ' + id); }
  const D = await companyDetail(page, PRICED), U = await companyDetail(page, UNPRICED);
  const totalText = (t) => (t === null ? null : fmtKo(t));
  for (const [id, x] of [[PRICED, D], [UNPRICED, U]]) { const t = R.total[id];if (t === null) assert.ok(!/\d/.test(x.total), label + ' company total NA ' + id);else assert.equal(x.total, totalText(t), label + ' company detail total ' + id); }
  // The radar shows a total only as 'Q·G만 반영(V 미포함)' when V is missing (the unpriced company): the same total as S06.
  if (R.total[UNPRICED] !== null) assert.ok(U.radar.qgOnly && U.radar.qgOnly.includes(fmtKo(R.total[UNPRICED])), label + ' radar Q·G-only total ' + U.radar.qgOnly + ' vs ' + R.total[UNPRICED]);
  if (want === 'READY') { assert.ok(R.v[PRICED] !== null, label + ' fixture: ' + PRICED + ' priced');assert.equal(D.v, fmtKo(R.v[PRICED]), label + ' company detail V');assert.ok(close(Number(D.radar.score), R.v[PRICED]), label + ' radar V ' + D.radar.score + ' vs ' + R.v[PRICED]); }
  else { assert.equal(R.v[PRICED], null);assert.ok(!/\d/.test(D.v), label + ' company detail V NA');assert.equal(D.radar.score, 'NA'); }
  assert.equal(R.v[UNPRICED], null, label + ' fixture: ' + UNPRICED + ' unpriced');assert.ok(!/\d/.test(U.v), label + ' unpriced company V NA');assert.equal(U.radar.score, 'NA');assert.equal(U.radar.reason, R.reason[UNPRICED] || 'NO_DEVICE_PRICE', label + ' radar reason');
  const W = await universePage(page, UNI);
  if (R.total[UNI] === null) assert.equal(W.total, null, label + ' Universe page total NA');else assert.ok(close(Number(W.total), R.total[UNI]), label + ' Universe page total ' + W.total + ' vs ' + R.total[UNI]);
  if (want === 'READY') { assert.ok(close(Number(W.score), R.v[UNI]), label + ' Universe page V');assert.ok(close(Number(W.radar.score), R.v[UNI]), label + ' Universe radar V');assert.equal(W.priced, 'DEVICE_PRICED'); }
  else { assert.equal(W.score, 'NA');assert.equal(W.radar.score, 'NA');assert.equal(W.priced, 'NO_DEVICE_PRICE'); }
  return { L, R };
}
async function openSubset(page) {
  await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-table]').waitFor();
  const d = page.locator('details:has(#private-subset-root)');if (!(await d.evaluate((n) => n.open))) await d.locator('> summary').click();
  await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').waitFor();
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const P1 = day1(), P2 = day2(), values = F.strictUniverseValues(), priceText = new Set(values.slice(1).map((r) => String(r[2])));
  console.log('INFO sec-qgv2.json basis=SYNTHETIC_FIXTURE codes=' + Object.keys(P1.records).length + ' · prices=SYNTHETIC_FIXTURE (' + (values.length - 1) + ' made-up rows) · day 2 changes ' + CHANGED + ' total debt');
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);let publication = P1;
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(publication) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', (e) => { errors++;console.log('PAGEERROR ' + String(e && e.message).slice(0, 200)); });
      const external = [], nonGet = [];let watching = false;
      page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url());if (watching && r.method() !== 'GET') nonGet.push(r.method() + ' ' + r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      // Storage spy: every localStorage/sessionStorage write, IndexedDB put/add and Cache Storage put/add, by key/store name + value.
      await page.addInitScript(() => {
        window.__vsWrites = [];const rec = (k) => { if (window.__vsWatch) window.__vsWrites.push(k); };
        for (const m of ['setItem', 'removeItem', 'clear']) { const o = Storage.prototype[m];Storage.prototype[m] = function (...a) { rec(m + ':' + String(a[0]) + (m === 'setItem' ? '=' + String(a[1]) : ''));return o.apply(this, a); }; }
        for (const m of ['put', 'add']) { const o = IDBObjectStore.prototype[m];IDBObjectStore.prototype[m] = function (...a) { let v = '';try { v = JSON.stringify(a[0]); } catch (_) { v = '?'; }rec('idb.' + m + ':' + this.name + '=' + v);return o.apply(this, a); }; }
        if (typeof Cache !== 'undefined') for (const m of ['put', 'add', 'addAll']) { const o = Cache.prototype[m];Cache.prototype[m] = function (...a) { rec('cache.' + m + ':' + String(a[0] && a[0].url || a[0]));return o.apply(this, a); }; }
      });
      try {
        phase = 'SETUP ' + width;await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (vals) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          // Stubbed sheet session (RAM): counts the user-pressed reads; __vsFailNext makes the next read fail like a network error.
          window.__vsReads = 0;window.__vsFailNext = false;
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { window.__vsReads++;if (window.__vsFailNext) { window.__vsFailNext = false;throw Error('NETWORK'); }return { values: vals }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, values);
        phase = 'BEFORE ' + width;await sameEverywhere(page, 'before read', 'NOT_CONNECTED');
        // 1. Universe read (the user's button). From here on: storage and requests are watched.
        phase = 'READ ' + width;await page.evaluate(() => { window.__vsWatch = true; });watching = true;
        await openSubset(page);await page.locator('[data-private-subset] [data-subset-action="read"]').click();await page.locator('[data-v-coverage="READY"]').waitFor();
        assert.equal(await page.locator('[data-subset-kept]').getAttribute('data-subset-kept'), 'KEPT');
        assert.match(await page.locator('[data-subset-kept]').textContent(), /^이 기기 마지막 성공 읽기 사용 중 · 시트 읽은 시각 \d{4}-\d\d-\d\d \d\d:\d\d UTC · \d{4}-\d\d-\d\d \d\d:\d\d KST \(가격 시각 아님\) · 모든 화면이 이 가격 사용$/);
        const a = await sameEverywhere(page, 'after read', 'READY');assert.ok(a.R.basis && typeof a.R.basis.read_id === 'string', 'read id');assert.equal(await page.evaluate(() => window.__vsReads), 1);
        // 2. Navigate away (disposes the view) and back: the same read, the same V everywhere; the view says the read is kept.
        phase = 'NAVIGATE ' + width;await page.evaluate(() => { location.hash = 'home'; });await page.locator('main').waitFor();
        assert.equal(await page.evaluate(() => PrivateSubsetView.readStatus().state), 'READY', 'kept after the view is disposed');
        const b = await sameEverywhere(page, 'after navigation', 'READY');
        assert.equal(b.R.basis.read_id, a.R.basis.read_id, 'same read');assert.deepEqual(b.R.v, a.R.v, 'same V after navigation');assert.deepEqual(b.L.panel, a.L.panel, 'same panel after navigation');
        await openSubset(page);assert.equal(await page.locator('[data-subset-kept]').getAttribute('data-subset-kept'), 'KEPT', 'remounted view names the kept read');
        // 2b. Settings: the user changes the official preset and the value-trap gate on S06; every screen follows the same settings,
        //     also after navigating away and back.
        phase = 'PRESET_GATE ' + width;await page.locator('[data-qgv2-preset="' + PRESET + '"]').click();await page.waitForFunction((x) => qgv2Profile.preset === x, PRESET);
        await page.locator('input[data-qgv2-gate]').click();await page.waitForFunction(() => qgv2Profile.gate === false);
        const g1 = await sameEverywhere(page, 'after preset/gate', 'READY');assert.deepEqual(g1.R.profile, { preset: PRESET, gate: false });
        assert.deepEqual(g1.R.v, b.R.v, 'V does not depend on the preset');assert.ok(Object.keys(g1.R.total).some((k) => !Object.is(g1.R.total[k], b.R.total[k])), 'the preset/gate changed some totals');
        await page.evaluate(() => { location.hash = 'home'; });await page.locator('main').waitFor();
        const g2 = await sameEverywhere(page, 'preset/gate after navigation', 'READY');assert.deepEqual(g2.R.total, g1.R.total, 'same totals after navigation');assert.deepEqual(g2.R.profile, g1.R.profile);
        await openSubset(page);
        // 3. A re-read that fails keeps the old success and shows the failure next to it.
        phase = 'FAILED_REREAD ' + width;await page.evaluate(() => { window.__vsFailNext = true; });await page.locator('[data-private-subset] [data-subset-action="read"]').click();
        await page.locator('[data-subset-status]').filter({ hasText: 'UNIVERSE_READ_FAILED' }).waitFor();await page.locator('[data-v-read-failure="UNIVERSE_READ_FAILED"]').waitFor();
        assert.equal(await page.locator('[data-subset-kept]').getAttribute('data-subset-kept'), 'KEPT_FAILED');assert.equal(await page.locator('[data-subset-kept]').getAttribute('data-subset-failure'), 'UNIVERSE_READ_FAILED');
        assert.match(await page.locator('[data-subset-kept]').textContent(), /^새 읽기 실패\(UNIVERSE_READ_FAILED\) · 시도 .+ UTC · .+ KST · 마지막 성공 읽기 유지 · 시트 읽은 시각 .+ KST$/);
        assert.equal(await page.locator('[data-v-read-failure]').getAttribute('data-v-read-kept'), 'KEPT');
        assert.match(await page.locator('[data-v-read-failure]').textContent(), /^새 Universe 읽기 실패\(UNIVERSE_READ_FAILED\) · 시도 .+ · 아래 수치는 마지막 성공 읽기\(시트 읽은 시각 .+ KST\) 기준$/);
        const c = await sameEverywhere(page, 'after failed re-read', 'READY');
        assert.equal(c.R.basis.read_id, a.R.basis.read_id, 'the failed read did not replace the kept read');assert.deepEqual(c.R.v, a.R.v, 'same V after the failed re-read');assert.equal(c.L.panel.failure, 'UNIVERSE_READ_FAILED');assert.equal(c.L.panel.kept, 'KEPT');
        assert.equal(await page.evaluate(() => window.__vsReads), 2);
        // 4. '자료 새로고침' with a new publication (on the company screen): every screen recomputes from the new inputs and the same kept prices.
        phase = 'REFRESH ' + width;publication = P2;await page.evaluate((x) => { location.hash = 'company/' + x; }, PRICED);await page.locator('[data-company-card="qgv"]').waitFor();
        await page.locator('[data-refresh-button]').click();await page.locator('#data-refresh[data-refresh-state="APPLIED"]').waitFor();
        await page.waitForFunction((at) => publicScreens['sec-qgv2.json'].as_of === at, P2.as_of);
        // In place on the open company screen: the detail and its radar follow the new page result (same kept prices).
        { const R2 = await shared(page);await page.waitForFunction((v) => document.querySelector('[data-company-card="qgv"] [data-qgv="V"]')?.textContent.trim() === v, fmtKo(R2.v[PRICED]));
          await page.waitForFunction((v) => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]');return c && Math.abs(Number(c.dataset.srScore) - v) <= 1e-9; }, R2.v[PRICED]); }
        const d = await sameEverywhere(page, 'after refresh', 'READY');
        assert.equal(d.R.asOf, P2.as_of, 'new inputs');assert.equal(d.R.basis.read_id, a.R.basis.read_id, 'same kept read');assert.deepEqual(d.R.quotes, a.R.quotes, 'same kept prices');assert.deepEqual(d.R.profile, { preset: PRESET, gate: false }, 'settings kept across the refresh');
        assert.ok(Object.keys(d.R.v).some((k) => !Object.is(d.R.v[k], a.R.v[k])), 'the new publication changed some V (recomputed)');assert.notEqual(d.R.v[PRICED], a.R.v[PRICED], PRICED + ' V follows the new inputs');
        assert.ok(d.L.panel.calc.includes(P2.as_of), 'panel names the new publication');
        // 5. '기기 결과 지우기' (explicit) still clears the kept read on every screen.
        phase = 'CLEAR ' + width;await openSubset(page);await page.locator('[data-private-subset] [data-subset-action="clear"]').click();await page.locator('[data-v-coverage="NOT_CONNECTED"]').waitFor();
        assert.equal(await page.evaluate(() => PrivateSubsetView.readStatus().state), 'NOT_READ');assert.equal(await page.locator('[data-subset-kept]').getAttribute('data-subset-kept'), 'NONE');
        await sameEverywhere(page, 'after clear', 'NOT_CONNECTED');
        // RAM only: no price in any storage write (the S06 view memory carries no price), no request beyond the two pressed reads.
        phase = 'RAM_ONLY ' + width;const writes = await page.evaluate(() => window.__vsWrites);
        const bad = writes.filter((w) => /^(idb|cache)\./.test(w) || /price|quote|universe|coverage/i.test(w.split('=')[0]) || [...priceText].some((t) => w.includes('"' + t + '"') || w.includes(':' + t + ',') || w.endsWith('=' + t)));
        assert.deepEqual(bad, [], 'no storage write of prices: ' + JSON.stringify(bad).slice(0, 400));
        assert.equal(await page.evaluate(() => window.__vsReads), 2, 'only the two user-pressed Sheets reads');assert.deepEqual(nonGet, [], 'nothing sent');assert.deepEqual(external, [], 'no Worker / Sheets / outside request');assert.equal(errors, 0);
        console.log('INFO ' + width + ' V rows after read=' + a.R.cov.v_full + ' after refresh=' + d.R.cov.v_full + ' · storage writes from the read on: ' + writes.length + ' (none with a price)');
        pass++;console.log('PASS shared Universe read: same V on every screen across navigation, failed re-read and refresh ' + width + ' (synthetic fixture + synthetic prices)');
      } catch (e) { fail++;console.log('FAIL shared Universe read ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e) + ' @' + String(e && e.stack || '').split('\n').filter((l) => l.includes('v_session_state')).slice(0, 2).map((l) => l.trim().replace(/.*:(\d+):\d+\)?$/, '$1')).join(',')); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
