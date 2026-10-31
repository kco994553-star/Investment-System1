'use strict';
// "V 산출 현황 · 중앙 게시" (v-coverage.js) on S06 at 390 and 1280. DC-31 (owner decision 2026-10-31, device V abolished): the panel
// shows the coverage block of the central publication qgv-official.json (the synthetic one of qgv_official_fixture.js over the
// strictly valid synthetic sec-qgv2.json of qgv_v2_fixture.js; no price anywhere, no Universe read) next to its basis line
// ('공식 V · 중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님) · 가격 기준일 · 게시 시각 (· STALE)') and the IEX attribution with its
// terms link. Checks: every count on screen equals the publication's coverage; financials are their own line; the reasons are the
// published ones; without a publication (404) the panel names the reason and shows no V count, never a device V; no storage write,
// no non-GET or external request, no device price request; no page-wide overflow.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
const num = async (loc, attr) => Number(await loc.getAttribute(attr));
async function noOverflow(page, what) {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no page-wide scroll ' + what);
  assert.ok(await page.evaluate(() => { const s = document.querySelector('[data-v-coverage]');return s.scrollWidth <= s.clientWidth + 1; }), 'summary fits ' + what);
}
async function open(browser, width, { publication }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
  await routeEmptyPublicScreens(context);
  await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
  if (publication) await O.routeOfficial(context);
  const page = await context.newPage(), seen = { errors: 0, external: [], nonGet: [], device: [] };page.on('pageerror', () => seen.errors++);
  page.on('request', (r) => { const u = r.url();if (!/^(data|blob):/.test(u) && new URL(u).origin !== ORIGIN) seen.external.push(u);if (r.method() !== 'GET') seen.nonGet.push(r.method() + ' ' + u);if (!/\.(js|css|png|svg|woff2?)(\?|$)/.test(u) && /sheets|googleapis|workers\.dev|quote|prices?[-_./]|price-store/i.test(u) && !/pricefree/.test(u)) seen.device.push(u); });
  await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
  await page.addInitScript(() => {
    window.__vcovWrites = [];const rec = (k) => window.__vcovWrites.push(k);
    for (const m of ['setItem', 'removeItem', 'clear']) { const o = Storage.prototype[m];Storage.prototype[m] = function (...a) { rec(m + ':' + String(a[0]));return o.apply(this, a); }; }
    for (const m of ['put', 'add', 'delete', 'clear']) { const o = IDBObjectStore.prototype[m];IDBObjectStore.prototype[m] = function (...a) { rec('idb.' + m + ':' + this.name);return o.apply(this, a); }; }
  });
  return { context, page, seen };
}
const clean = async (page, seen) => {
  // Allowed: the app's own settings/view keys (no price, no count, no V). Anything V-, price- or coverage-like fails.
  const writes = (await page.evaluate(() => window.__vcovWrites)).filter((w) => /price|quote|coverage|v-store|v_store|v-history|qgv-official/i.test(w));
  assert.deepEqual(writes, [], 'no V / price / coverage storage write: ' + JSON.stringify(writes));
  assert.deepEqual(seen.nonGet, [], 'nothing sent');assert.deepEqual(seen.external, []);assert.deepEqual(seen.device, [], 'no device price request ' + JSON.stringify(seen.device));assert.equal(seen.errors, 0);
};

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const C = O.PUB.coverage, P = C.population;
  try {
    for (const width of [390, 1280]) {
      // 1. With the central publication: the published coverage, its basis line and the IEX attribution.
      let { context, page, seen } = await open(browser, width, { publication: true });
      try {
        phase = 'READY ' + width;await page.goto(BASE + '#leaderboard');const S = page.locator('[data-v-coverage="READY"]');await S.waitFor();
        assert.equal(await S.locator('h2').textContent(), 'V 산출 현황 · 중앙 게시');
        const want = await page.evaluate(() => { const R = QgvScores.pagePublication();return QgvScores.centralText(QgvScores.centralBasis(R.publication, { reason: R.reason, v2Inputs: publicScreens[Qgv2Inputs.FILE] }), false); });
        assert.match(want, /^공식 V · 중앙 게시 · IEX 마지막 체결가 기준\(공식 종가 아님\) · 가격 기준일 2026-10-13 · 게시 2026-10-13 22:40 UTC/);
        assert.equal(await S.locator('[data-central-basis]').textContent(), want);assert.equal(await S.locator('[data-central-basis]').getAttribute('data-central-basis'), O.PUB.publication_id);
        assert.match(want, / · STALE$/, 'the synthetic basis day is weeks old: STALE');assert.equal(await S.locator('[data-central-basis]').getAttribute('data-central-state'), 'STALE');
        assert.ok((await S.locator('[data-attribution]').textContent()).startsWith(O.PUB.attribution.text));
        assert.equal(await S.locator('[data-attribution] a').getAttribute('href'), O.PUB.attribution.terms_url);assert.equal(await S.locator('[data-attribution] a').getAttribute('rel'), 'noopener noreferrer');
        phase = 'COUNTS ' + width;
        for (const [k, n] of [['total', P.total], ['general', P.general], ['financial', P.financial], ['unknown', P.unknown]]) assert.equal(await num(S.locator('[data-pop-' + k + ']'), 'data-pop-' + k), n, k);
        assert.equal(await S.locator('[data-v-full]').textContent(), C.v.full + '/' + P.total);assert.equal(await S.locator('[data-v-general]').textContent(), C.v.general + '/' + P.general);
        assert.equal(await num(S.locator('[data-qgv-full]'), 'data-qgv-full'), C.qgv.full);assert.equal(await num(S.locator('[data-qgv-general]'), 'data-qgv-general'), C.qgv.general);
        assert.equal(await S.locator('[data-qg-only-full]').textContent(), C.qg_only_total.full + ' (금융 ' + C.qg_only_total.financial + ' · 공식 V 없음 ' + C.qg_only_total.no_v + ')');
        assert.equal(await num(S.locator('[data-gate-full]'), 'data-gate-full'), C.qg_only_total.gate);
        assert.equal(await num(S.locator('[data-ranked]'), 'data-ranked'), C.ranked);assert.equal(await num(S.locator('[data-qg-reference]'), 'data-qg-reference'), C.qg_reference);
        assert.equal(await S.locator('[data-v-target]').textContent(), '관찰 지표 · 목표 ' + C.target.n + '/' + P.general + ' (일반 기업 90%) · 현재 ' + C.v.general + '/' + P.general + ' (' + (C.target.met ? '달성' : '미달') + ')');
        assert.match(await S.locator('[data-v-target-note]').textContent(), /TARGET 확정 조건에 쓰이지 않습니다/);
        assert.match(await S.locator('[data-v-composition]').textContent(), new RegExp('^전체 ' + P.total + ' = 일반 ' + P.general + ' \\+ 금융 ' + P.financial + ' \\+ 미확인 ' + P.unknown));
        assert.deepEqual(Object.fromEntries(await S.locator('[data-v-reason]').evaluateAll((n) => n.map((x) => [x.dataset.vReason, Number(x.dataset.count)]))), Object.fromEntries(C.reasons));
        assert.deepEqual(Object.fromEntries(await S.locator('[data-v-factor-reason]').evaluateAll((n) => n.map((x) => [x.dataset.vFactorReason, Number(x.dataset.count)]))), Object.fromEntries(C.factor_reasons));
        assert.equal(await S.locator('[data-v-reason="FINANCIAL_PROFILE_V_NOT_DEFINED"]').count(), 0, 'financials are not a data shortage');
        assert.equal(await S.locator('[data-v-price-status]').textContent(), 'IEX 가격 상태: ' + ['SUPPLIED', 'NO_IEX_TRADE', 'ODD_LOT_ONLY'].filter((k) => C.price_status[k]).map((k) => k + ' ' + C.price_status[k]).join(' · '));
        assert.ok((await S.locator('[data-v-calc-version]').textContent()).startsWith('계산 버전 ' + O.PUB.calc_version));
        assert.doesNotMatch(await S.textContent(), /이 기기 ·|Universe 읽기|가격 미연결|기기 V 기록/);
        await noOverflow(page, 'ready ' + width);await S.locator('[data-v-factor-details] > summary').click();await noOverflow(page, 'factor reasons open ' + width);
        if (process.env.PAGES_COCKPIT_EVIDENCE_DIR) await S.screenshot({ path: process.env.PAGES_COCKPIT_EVIDENCE_DIR + '/v-coverage-' + width + '.png' });
        await clean(page, seen);
        pass++;console.log('PASS v coverage central publication ' + width);
      } catch (e) { fail++;console.log('FAIL v coverage ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
      // 2. Without a publication (404): the reason, no V count, never a device V.
      ({ context, page, seen } = await open(browser, width, { publication: false }));
      try {
        phase = 'NOT_PUBLISHED ' + width;await page.goto(BASE + '#leaderboard');const S = page.locator('[data-v-coverage="NOT_PUBLISHED"]');await S.waitFor();
        await page.locator('[data-v-coverage-state="OFFICIAL_UNAVAILABLE"], [data-v-coverage-state="OFFICIAL_NOT_PUBLISHED"]').waitFor();
        const st = await S.locator('[data-v-coverage-state]').getAttribute('data-v-coverage-state');
        assert.equal(await S.locator('[data-v-coverage-state]').textContent(), (st === 'OFFICIAL_UNAVAILABLE' ? '공식 V 없음: 중앙 V 게시본을 읽지 못했습니다' : '공식 V 없음: 중앙 V 게시본이 아직 없습니다') + ' · V 산출 수 없음');
        assert.equal(await S.locator('[data-central-basis]').getAttribute('data-central-state'), 'NA');assert.equal(await S.locator('[data-attribution]').count(), 0);
        for (const sel of ['[data-v-full]', '[data-v-general]', '[data-qgv-full]', '[data-v-reason]', '[data-v-target]']) assert.equal(await S.locator(sel).count(), 0, sel + ': no V count without a publication');
        await noOverflow(page, 'not published ' + width);await clean(page, seen);
        pass++;console.log('PASS v coverage no publication ' + width);
      } catch (e) { fail++;console.log('FAIL v coverage ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
