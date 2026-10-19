'use strict';
// "V 산출 현황 · 이 기기" (v-coverage.js) on S06 at 390 and 1280.
// Q·G·V side: the REAL published sec-qgv2.json when given (V_COVERAGE_QGV2_FILE, read-only, never committed), else the copy the
// served build publishes, else the strictly valid synthetic fixture (qgv_v2_fixture.js strictPayload) on PR builds.
// Price side: SYNTHETIC FIXTURE PRICES ONLY (made-up numbers, never real prices), served through a stubbed Universe tab read (RAM).
// Checks: the counts on screen equal an independent recount of the shared QgvScores.pageResult() output, which equals a direct
// compute over a copy of the same quotes; financials are a separate
// '현재 금융업 가치평가 모델 미지원' line; no V count before the read; the 504 basis keeps not-applicable rows in its denominator;
// no storage writes, no non-GET or external request and no app console output from the read on (the browser's own 404
// network line for an absent public sidecar is not app output); no page-wide overflow.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
// Clearly labelled synthetic price layer: one made-up USD price per LIVE/STALE code, every 50th code left unpriced (NO_DEVICE_PRICE).
function syntheticUniverseValues(payload) {
  const rows = [['code', 'marketcap', 'price']];let i = 0;
  for (const [code, r] of Object.entries(payload.records)) { if (!['LIVE', 'STALE'].includes(r.state)) continue;i++;if (i % 50 === 0) continue;rows.push([code, '', 20 + ((i * 37) % 400) + 0.25]); }
  return rows;
}
async function qgv2Source() {
  const file = process.env.V_COVERAGE_QGV2_FILE;
  if (file && fs.existsSync(file)) return { basis: 'REAL_FILE', payload: JSON.parse(fs.readFileSync(file, 'utf8')) };
  try { const r = await fetch(BASE + 'sec-qgv2.json');if (r.ok) { const p = await r.json();if (p && p.kind === 'SEC_QGV2' && p.records) return { basis: 'SERVED_FILE', payload: p }; } } catch (_) { /* PR build: no published copy */ }
  return { basis: 'SYNTHETIC_FIXTURE', payload: F.strictPayload() };
}
// Independent recount (test side) of the rows the page computed: same compute() call as the summary, counted here.
function recount(rows) {
  const G = rows.filter((r) => r.cls === 'GENERAL'), reasons = {}, factor = {};
  for (const r of G.filter((x) => !x.v)) { reasons[r.vreason] = (reasons[r.vreason] || 0) + 1;for (const f of new Set(r.freasons)) factor[f] = (factor[f] || 0) + 1; }
  const periods = G.filter((r) => r.shares).map((r) => r.period).filter(Boolean).sort();
  return {
    same: rows.every((r) => r.same), sources: rows.filter((r) => r.priced).reduce((o, r) => { o[r.source] = o[r.source] || { rows: 0, unconfirmed: 0, stale: 0 };o[r.source].rows++;if (!r.asOf) o[r.source].unconfirmed++;if (r.stale === true) o[r.source].stale++;return o; }, {}),
    total: rows.length, general: G.length, financial: rows.filter((r) => r.cls === 'FINANCIAL').length, noData: rows.filter((r) => r.cls === 'NO_DATA').length, stopped: rows.filter((r) => r.cls === 'STOPPED').length,
    vFull: rows.filter((r) => r.v).length, vGeneral: G.filter((r) => r.v).length, qgvFull: rows.filter((r) => r.v && r.q && r.g).length, qgvGeneral: G.filter((r) => r.v && r.q && r.g).length,
    complete: G.filter((r) => r.missing === 0).length, upper: G.filter((r) => r.shares && (r.ebit || r.fcf)).length, sharesRows: G.filter((r) => r.shares).length, from: periods[0] || null, to: periods.at(-1) || null,
    // Q·G-only totals: no V in the row (financial or no price / V not computed). Gate rows (V computed, excluded by the rule) apart.
    qgOnly: rows.filter((r) => r.total && !r.v).length, qgOnlyGeneral: G.filter((r) => r.total && !r.v).length, qgOnlyFin: rows.filter((r) => r.cls === 'FINANCIAL' && r.total && !r.v).length,
    gateFull: rows.filter((r) => r.total && r.v && r.vx).length, gateGeneral: G.filter((r) => r.total && r.v && r.vx).length,
    qgOnlyNoV: rows.filter((r) => r.cls !== 'FINANCIAL' && r.total && !r.v).length,
    priced: rows.filter((r) => r.priced).length, mismatch: G.filter((r) => r.priced && r.vi && r.qc !== r.vic).length, reasons, factor,
  };
}
async function pageRows(page) {
  return page.evaluate(async () => {
    const inputs = publicScreens[Qgv2Inputs.FILE], codes = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:'));
    // The shared page result the panel (and the stat radar) reads; a direct compute over a copy of the same quotes must agree per row.
    const R = await QgvScores.pageResult(window, { v2Inputs: inputs, catalog: await deviceCatalog().catch(() => null), identities: identityCompanies, preset: qgv2Profile.preset, gate: qgv2Profile.gate });
    const S = R.computed, quotes = R.quotes, D = QgvScores.compute({ identities: R.identities, v2Inputs: inputs, quotes: structuredClone(R.quotes), preset: qgv2Profile.preset, gate: qgv2Profile.gate });
    const same = R.identities.every((c) => Object.is(S.rows[c.company_id].primary.v, D.rows[c.company_id].primary.v) && Object.is(S.rows[c.company_id].primary.total, D.rows[c.company_id].primary.total));
    const fin = (x) => typeof x === 'number' && Number.isFinite(x);
    return codes.map((code) => {
      const rec = inputs.records[code], row = S.rows[code], p = row && row.code === code ? row.primary : null, vi = rec.v_inputs, q = quotes[code], m = R.quote_meta[code] || null, ax = p && p.coverage && p.coverage.axes ? p.coverage.axes.V : null;
      const cls = rec.identity_withdrawn === true ? 'STOPPED' : rec.published_profile === 'GENERAL' ? 'GENERAL' : rec.published_profile === 'FINANCIAL' ? 'FINANCIAL' : 'NO_DATA';
      return { code, cls, total: !!p && fin(p.total), vx: !!p && !!p.v_excluded, v: !!p && fin(p.v), q: !!p && fin(p.q), g: !!p && fin(p.g), missing: p && p.coverage ? p.coverage.v_inputs_missing.length : -1, vreason: ax && ax.reason ? ax.reason : null,
        freasons: ax ? ax.factors.filter((f) => f.score === null && f.reason).map((f) => f.reason) : [], vi: !!vi, vic: vi ? vi.currency : null, qc: q ? q.currency : null, priced: !!q && fin(q.price) && q.price > 0,
        shares: !!vi && fin(vi.diluted_shares) && vi.diluted_shares > 0, ebit: !!vi && fin(vi.ebit), fcf: !!vi && fin(vi.fcf), period: rec.periods ? rec.periods.diluted_shares || null : null,
        source: m ? m.source : null, asOf: m ? m.as_of : null, stale: m ? m.stale : null, same };
    });
  });
}
const num = async (loc, attr) => Number(await loc.getAttribute(attr));
async function noOverflow(page, what) {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide scroll ' + what);
  assert.ok(await page.evaluate(() => { const s = document.querySelector('[data-v-coverage]');return s.scrollWidth <= s.clientWidth + 1; }), 'summary fits ' + what);
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const { basis, payload } = await qgv2Source(), values = syntheticUniverseValues(payload);
  console.log('INFO sec-qgv2.json basis=' + basis + ' codes=' + Object.keys(payload.records).length + ' · prices=SYNTHETIC_FIXTURE (' + (values.length - 1) + ' made-up rows)');
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [], writesAfter = [], nonGet = [];let watching = false;
      page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url());if (watching && r.method() !== 'GET') nonGet.push(r.method() + ' ' + r.url()); });
      page.on('console', (m) => { if (watching && !m.text().startsWith('Failed to load resource')) writesAfter.push('console:' + m.type() + ':' + m.text().slice(0, 120)); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      // Storage spy: every localStorage/sessionStorage write and every IndexedDB put/add/delete/clear is recorded by key/store name only.
      await page.addInitScript(() => {
        window.__vcovWrites = [];const rec = (k) => { if (window.__vcovWatch) window.__vcovWrites.push(k); };
        for (const m of ['setItem', 'removeItem', 'clear']) { const o = Storage.prototype[m];Storage.prototype[m] = function (...a) { rec(m + ':' + String(a[0]) + (m === 'setItem' ? '=' + String(a[1]) : ''));return o.apply(this, a); }; }
        for (const m of ['put', 'add', 'delete', 'clear']) { const o = IDBObjectStore.prototype[m];IDBObjectStore.prototype[m] = function (...a) { rec('idb.' + m + ':' + this.name);return o.apply(this, a); }; }
      });
      try {
        phase = 'SETUP ' + width;await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (vals) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values: vals }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, values);
        // Before any Universe read: the price-free facts only, and no V count anywhere in the summary.
        phase = 'BEFORE ' + width;const S = page.locator('[data-v-coverage]');await page.locator('[data-v-coverage="NOT_CONNECTED"]').waitFor();
        assert.equal(await S.locator('[data-v-coverage-state]').textContent(), '가격 미연결: V 실제 산출 수는 Universe 읽기 뒤 표시');
        for (const sel of ['[data-v-full]', '[data-v-general]', '[data-qgv-full]', '[data-qgv-general]', '[data-qg-only-full]', '[data-qg-only-general]', '[data-gate-full]', '[data-gate-general]']) { assert.equal(await S.locator(sel).textContent(), '—', sel);assert.equal(await S.locator(sel).getAttribute(sel.slice(1, -1)), '', sel + ' has no count'); }
        assert.equal(await S.locator('[data-v-met]').count(), 0);assert.equal(await S.locator('[data-v-reasons]').count(), 0);assert.equal(await S.locator('[data-currency-mismatch]').count(), 0);
        assert.match(await S.locator('[data-v-target]').textContent(), /^관찰 지표 · 목표 \d+\/\d+ \(일반 기업 90%\) · 현재 — \(가격 미연결\)$/);
        assert.equal(await S.locator('[data-v-price-time]').getAttribute('data-v-price-time'), 'NOT_READ');
        assert.equal(await S.locator('[data-v-acquired]').textContent(), '읽기 전');
        await noOverflow(page, 'before ' + width);
        phase = 'BEFORE_COUNTS ' + width;{
          const c = recount(await pageRows(page));
          assert.equal(await num(S.locator('[data-financial]'), 'data-financial'), c.financial);assert.equal(await num(S.locator('[data-no-data]'), 'data-no-data'), c.noData);
          assert.equal(await num(S.locator('[data-complete]'), 'data-complete'), c.complete);assert.equal(await num(S.locator('[data-v-upper]'), 'data-v-upper'), c.upper);
        }
        // Universe read (synthetic prices). From here on: no storage write, no non-GET or external request, no console output.
        phase = 'READ ' + width;await page.evaluate(() => { window.__vcovWatch = true; });watching = true;
        await page.locator('details:has(#private-subset-root) > summary').click();await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-v-coverage="READY"]').waitFor();
        phase = 'COUNTS ' + width;const rows = await pageRows(page), c = recount(rows);
        assert.equal(c.total, Object.keys(payload.records).length);assert.ok(c.same, 'pageResult V/total equal a direct compute over the same quotes');
        // Population, computed live from the loaded file (no hard-coded 434/391).
        for (const [k, n] of [['total', c.total], ['general', c.general], ['financial', c.financial], ['unknown', c.noData]]) assert.equal(await num(S.locator('[data-pop-' + k + ']'), 'data-pop-' + k), n, k);
        assert.match(await S.locator('[data-v-target-note]').textContent(), /TARGET 확정 조건에 쓰이지 않습니다/);
        assert.equal(await num(S.locator('[data-v-full]'), 'data-v-full'), c.vFull);assert.equal(await num(S.locator('[data-v-general]'), 'data-v-general'), c.vGeneral);
        assert.equal(await num(S.locator('[data-qgv-full]'), 'data-qgv-full'), c.qgvFull);assert.equal(await num(S.locator('[data-qgv-general]'), 'data-qgv-general'), c.qgvGeneral);
        assert.equal(await S.locator('[data-v-full]').textContent(), c.vFull + '/' + c.total);assert.equal(await S.locator('[data-v-general]').textContent(), c.vGeneral + '/' + c.general);
        assert.equal(await num(S.locator('[data-complete]'), 'data-complete'), c.complete);assert.equal(await num(S.locator('[data-v-upper]'), 'data-v-upper'), c.upper);
        // Totals made from Q·G alone (no V in the total) are counted on both bases, financials and no-V rows named apart.
        assert.equal(await num(S.locator('[data-qg-only-full]'), 'data-qg-only-full'), c.qgOnly);assert.equal(await num(S.locator('[data-qg-only-general]'), 'data-qg-only-general'), c.qgOnlyGeneral);
        assert.equal(c.qgOnly, c.qgOnlyFin + c.qgOnlyNoV);assert.equal(c.qgOnlyGeneral, c.qgOnlyNoV);
        assert.equal(await S.locator('[data-qg-only-full]').textContent(), c.qgOnly + ' (금융 ' + c.qgOnlyFin + ' · 가격 없음/V 미산출 ' + c.qgOnlyNoV + ')');
        assert.equal(await S.locator('[data-qg-only-general]').textContent(), c.qgOnlyGeneral + ' (가격 없음/V 미산출 ' + c.qgOnlyNoV + ')');
        // Value-trap gate rows: V computed, excluded from the total by the approved rule, kept in the ranking: their own line.
        assert.equal(await num(S.locator('[data-gate-full]'), 'data-gate-full'), c.gateFull);assert.equal(await num(S.locator('[data-gate-general]'), 'data-gate-general'), c.gateGeneral);
        assert.equal(c.gateFull, c.gateGeneral, 'gate rows all have V, so all are general');
        // The shared API already excludes gate rows from qg_only_total (one definition for every screen); the panel reads it as is.
        const api = await page.evaluate(async () => { const inputs = publicScreens[Qgv2Inputs.FILE], R = await QgvScores.pageResult(window, { v2Inputs: inputs, catalog: await deviceCatalog().catch(() => null), identities: identityCompanies, preset: qgv2Profile.preset, gate: qgv2Profile.gate });return QgvScores.vCoverage(R, inputs).qg_only_total; });
        assert.deepEqual(api, { full: c.qgOnly, general: c.qgOnlyGeneral, financial: c.qgOnlyFin, no_v: c.qgOnlyNoV, gate: c.gateFull });
        assert.match(await S.locator('[data-v-row="gate"]').textContent(), new RegExp('^가치 함정 관문으로 V 제외\\(공식 규칙 · 순위 유지\\)' + c.gateFull + '/' + c.total + c.gateGeneral + '/' + c.general + '$'));
        if (c.financial) assert.ok(c.qgOnlyFin >= 1, 'financial rows with a Q·G total are visible');
        assert.ok(c.vGeneral <= c.upper || basis === 'SYNTHETIC_FIXTURE', 'V count within the public-input upper bound');
        // Not-computed reasons: every engine reason code with its count, summing to the general rows without V.
        const shown = Object.fromEntries(await S.locator('[data-v-reason]').evaluateAll((n) => n.map((x) => [x.dataset.vReason, Number(x.dataset.count)])));
        assert.deepEqual(shown, c.reasons);assert.equal(Object.values(shown).reduce((a, b) => a + b, 0), c.general - c.vGeneral);
        assert.deepEqual(Object.fromEntries(await S.locator('[data-v-factor-reason]').evaluateAll((n) => n.map((x) => [x.dataset.vFactorReason, Number(x.dataset.count)]))), c.factor);
        if (c.priced < c.total - c.noData) assert.ok((shown.NO_DEVICE_PRICE || 0) >= 1, 'an unpriced general row shows NO_DEVICE_PRICE');
        // Financials: separate line with the owner's wording; never a data-shortage reason and never in the general denominator.
        phase = 'FINANCIAL ' + width;assert.equal(await num(S.locator('[data-financial]'), 'data-financial'), c.financial);
        assert.match(await S.locator('[data-v-row="financial"]').textContent(), /^금융업 · 현재 금융업 가치평가 모델 미지원\d+\/\d+해당 없음 \(분모 아님\)$/);
        assert.equal(await S.locator('[data-v-reason="FINANCIAL_PROFILE_V_NOT_DEFINED"]').count(), 0);assert.equal(await S.locator('[data-v-factor-reason="FINANCIAL_PROFILE_V_NOT_DEFINED"]').count(), 0);
        // Denominators: the full basis counts every code (general + financial + no data + stopped); the general basis is the GENERAL n.
        phase = 'DENOMINATOR ' + width;assert.equal(c.general + c.financial + c.noData + c.stopped, c.total);
        assert.equal(await S.locator('[data-v-coverage-table] thead th').nth(1).textContent(), '전체 ' + c.total + ' 기준');assert.equal(await S.locator('[data-v-coverage-table] thead th').nth(2).textContent(), '일반 기업 ' + c.general + ' 기준');
        assert.equal(await S.locator('[data-financial]').textContent(), c.financial + '/' + c.total);assert.equal(await S.locator('[data-no-data]').textContent(), c.noData + '/' + c.total);
        assert.match(await S.locator('[data-v-composition]').textContent(), new RegExp('^전체 ' + c.total + ' = 일반 ' + c.general + ' \\+ 금융 ' + c.financial + ' \\+ 미확인 ' + c.noData));
        const target = Math.ceil(0.9 * c.general - 1e-9), met = c.vGeneral >= target;
        assert.equal(await S.locator('[data-v-target]').textContent(), '관찰 지표 · 목표 ' + target + '/' + c.general + ' (일반 기업 90%) · 현재 ' + c.vGeneral + '/' + c.general + ' (' + (met ? '달성' : '미달') + ')');
        assert.equal(await S.locator('[data-v-target]').getAttribute('data-v-met'), met ? 'MET' : 'NOT_MET');
        assert.match(await S.locator('[data-v-upper]').textContent(), new RegExp('^공개 입력 기준 상한 ' + c.upper + '/' + c.general + ' · .* 상한일 뿐 산출 수가 아님$'));
        // Price basis: read time (UTC + KST), currency USD with the mismatch count, SEC diluted-share basis and the file calc_version.
        phase = 'BASIS ' + width;assert.match(await S.locator('[data-v-acquired]').textContent(), /^\d{4}-\d\d-\d\d \d\d:\d\d UTC · \d{4}-\d\d-\d\d \d\d:\d\d KST · Universe 탭을 가져온 시각 \(가격 시각 아님\)$/);
        // Price time is not the read time: GOOGLEFINANCE rows have none (미확인); per source, rows without a time are 미확인.
        const allUnconfirmed = Object.values(c.sources).every((x) => x.rows === x.unconfirmed);
        assert.equal(await S.locator('[data-v-price-time]').getAttribute('data-v-price-time'), allUnconfirmed ? 'UNCONFIRMED' : 'PER_SOURCE');
        assert.deepEqual(Object.fromEntries(await S.locator('[data-price-source]').evaluateAll((n) => n.map((x) => [x.dataset.priceSource, { rows: Number(x.dataset.rows), unconfirmed: Number(x.dataset.unconfirmed), stale: Number(x.dataset.stale) }]))), c.sources);
        assert.equal(c.sources.UNIVERSE_SHEET.rows, c.sources.UNIVERSE_SHEET.unconfirmed);assert.match(await S.locator('[data-price-source="UNIVERSE_SHEET"]').textContent(), / · 가격 기준 시각 미확인 · 신선도 판정 불가$/);assert.equal(c.sources.UNIVERSE_SHEET.stale, 0, 'Universe rows never stale (D10)');
        if (allUnconfirmed) assert.ok((await S.locator('[data-v-price-time]').textContent()).startsWith('가격 기준 시각 미확인'), 'exact D10 text');
        assert.equal(await num(S.locator('[data-currency-mismatch]'), 'data-currency-mismatch'), c.mismatch);
        assert.equal(await S.locator('[data-v-currency]').textContent(), 'USD · 가격 반영 ' + c.priced + '/' + c.total + '행 · 통화 불일치 ' + c.mismatch + '행(일반 기업, 환율 변환 없음)');
        const shares = await S.locator('[data-v-shares]').textContent();assert.ok(shares.startsWith('SEC v_inputs_v2.diluted_shares · 기간 말 ' + (c.from ? c.from + ' ~ ' + c.to : '—') + ' · ' + c.sharesRows + '/' + c.general + '행 · V-SHARES-SCALE'), shares);
        if (payload.calc_version) assert.ok((await S.locator('[data-v-calc-version]').textContent()).startsWith(payload.calc_version + ' · 공개 파일 기준 '));
        if (basis !== 'SYNTHETIC_FIXTURE' && c.total === 504) {  // the published file of 2026-10-17 (calc qgv2-calc/2026-10-17.1)
          console.log('INFO real-file counts (synthetic prices): general=' + c.general + ' financial=' + c.financial + ' no_data=' + c.noData + ' upper=' + c.upper + ' complete=' + c.complete + ' (price-free counts only)');
        }
        await noOverflow(page, 'read ' + width);
        if (process.env.PAGES_COCKPIT_EVIDENCE_DIR) await S.screenshot({ path: process.env.PAGES_COCKPIT_EVIDENCE_DIR + '/v-coverage-' + width + '.png' });
        await S.locator('[data-v-factor-details] > summary').click();await noOverflow(page, 'factor reasons open ' + width);
        // Clear device results: back to the no-price state, no V count.
        phase = 'CLEAR ' + width;await page.locator('[data-private-subset] [data-subset-action="clear"]').click();await page.locator('[data-v-coverage="NOT_CONNECTED"]').waitFor();
        assert.equal(await S.locator('[data-v-full]').textContent(), '—');assert.equal(await S.locator('[data-v-met]').count(), 0);
        // The S06 view (sort/filter/scroll, sessionStorage, existing app behaviour on scroll) may be saved; it must carry no price or count.
        phase = 'RAM_ONLY ' + width;const writes = (await page.evaluate(() => window.__vcovWrites)).filter((w) => {
          if (!w.startsWith('setItem:investment.web.v1.s06-view=')) return true;const v = JSON.parse(w.slice(w.indexOf('=') + 1));
          return Object.keys(v).some((k) => /price|quote|coverage|count|total|score/i.test(k)) || /v-coverage|V 산출/.test(JSON.stringify(v)); });
        assert.deepEqual(writes, [], 'no storage writes from the read on: ' + JSON.stringify(writes));assert.deepEqual(writesAfter, [], 'no console output from the read on: ' + JSON.stringify(writesAfter));assert.deepEqual(nonGet, [], 'nothing sent');
        assert.deepEqual(external, []);assert.equal(errors, 0);
        pass++;console.log('PASS v coverage summary ' + width + ' (' + basis + ' + synthetic prices)');
      } catch (e) { fail++;console.log('FAIL v coverage ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
