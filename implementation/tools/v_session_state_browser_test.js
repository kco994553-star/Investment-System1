'use strict';
// ONE central V read per page (DC-31, owner decision 2026-10-31: screens show only the central V of qgv-official.json, read once on
// open and again on '자료 새로고침'; no device V, no device V history, no price) on the real user path at 390 and 1280:
//   1. while the one read is pending, S06, the V panel and the company card say '공식 V 확인 중' (OFFICIAL_LOADING), never
//      '게시본이 아직 없습니다' and never a device V; the playbook candidates wait for the read;
//   2. once it lands every screen shows the publication with its basis line (basis day, publication time, STALE past 2 completed
//      New York sessions: the synthetic basis day is weeks old) and the IEX attribution with its terms link;
//   3. navigating away and back reads nothing again (one request per page);
//   4. a re-read that FAILS keeps the last publication (same V, same ranks) and names the failure next to the basis line;
//   5. without any publication (first read fails) every V is NA with OFFICIAL_UNAVAILABLE, no rank, never a device V;
//   6. the S06 preset/gate (QgvScores.pageProfile) is the same on S06 and the company page (personal preset labelled 개인).
// Also: no storage write of the publication or a V, no request to another origin, no device price request.
// Synthetic only: qgv_v2_fixture.js strictPayload + qgv_official_fixture.js (no price anywhere).
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, TGT = 'amd';
const shared = (page, id) => page.evaluate((id) => { const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), C = QgvScores.presetView(P, { v2Inputs: inputs }), r = QgvScores.rowOf(C, id);
  return { source: P.source, reason: P.v_reason, v: r ? r.primary.v : null, total: r ? r.primary.total : null, rank: r ? r.rank : null, profile: C.profile.id }; }, id);
async function open(browser, width, mode) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
  await routeEmptyPublicScreens(context);await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(F.strictPayload()) }));
  // mode.hold: the first answer waits for release(); mode.serve: 'PUB' | 'FAIL'. Every read of qgv-official.json is counted.
  const st = { reads: 0, serve: mode.serve, release: null };const held = new Promise((res) => { st.release = res; });
  await context.route('**/qgv-official.json*', async (r) => { st.reads++;if (mode.hold && st.reads === 1) await held;return r.fulfill(st.serve === 'FAIL' ? { status: 503, contentType: 'text/plain', body: 'synthetic unavailable' } : { status: 200, contentType: 'application/json', body: O.PUB_TEXT }); });
  const page = await context.newPage(), seen = { errors: 0, external: [], device: [] };page.on('pageerror', () => seen.errors++);
  page.on('request', (r) => { const u = r.url();if (!/^(data|blob):/.test(u) && new URL(u).origin !== ORIGIN) seen.external.push(u);if (!/\.(js|css|png|svg|woff2?)(\?|$)/.test(u) && /sheets|workers\.dev|price-store|quote/i.test(u)) seen.device.push(u); });
  await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
  await page.addInitScript(() => { window.__writes = [];const o = Storage.prototype.setItem;Storage.prototype.setItem = function (k, v) { window.__writes.push(String(k) + '=' + String(v).slice(0, 200));return o.call(this, k, v); }; });
  return { context, page, st, seen };
}
const clean = async (page, seen) => {
  const bad = (await page.evaluate(() => window.__writes)).filter((w) => /qgvpub-|qgv-official|v_store|v-store|v-history|"v":\d/i.test(w));
  assert.deepEqual(bad, [], 'no publication or V in storage: ' + JSON.stringify(bad));assert.deepEqual(seen.external, []);assert.deepEqual(seen.device, [], 'no device price request');assert.equal(seen.errors, 0);
};
const basisOf = (page, sel) => page.evaluate((s) => { const n = document.querySelector(s + ' [data-central-basis]');return n ? { id: n.dataset.centralBasis, state: n.dataset.centralState, na: n.dataset.na || null, text: n.textContent, attribution: !!document.querySelector(s + ' [data-attribution] a[href]') } : null; }, sel);

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  try {
    for (const width of [390, 1280]) {
      let { context, page, st, seen } = await open(browser, width, { hold: true, serve: 'PUB' });
      try {
        // 1. Pending: '확인 중', never 'not published', never a device V.
        phase = 'PENDING ' + width;await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
        assert.equal(await page.evaluate(() => QgvScores.pagePublication().reason), 'OFFICIAL_LOADING');
        const note = page.locator('[data-leaderboard-official="NO_OFFICIAL_V"]');await note.waitFor();assert.match(await note.textContent(), /공식 V 확인 중: 중앙 V 게시본을 읽는 중입니다/);
        assert.doesNotMatch(await page.locator('#leaderboard-screen').textContent(), /게시본이 아직 없습니다|기기 V/);
        await page.locator('[data-v-coverage-state="OFFICIAL_LOADING"]').waitFor();
        assert.equal((await basisOf(page, '[data-leaderboard-central]')).na, 'OFFICIAL_LOADING');
        await page.evaluate((id) => { location.hash = 'company/' + id; }, TGT);await page.locator('[data-qgv-central] [data-central-basis]').waitFor();
        assert.equal((await basisOf(page, '[data-qgv-central]')).na, 'OFFICIAL_LOADING');
        await page.evaluate(() => { location.hash = 'playbook'; });await page.locator('#playbook-screen').waitFor({ state: 'attached' });await page.waitForTimeout(400);
        assert.equal(await page.locator('[data-target-rank-row]').count(), 0, 'the candidates wait for the one read');
        // 2. The read lands: every screen shows the publication; the waiting playbook mounts with the official order.
        phase = 'LANDED ' + width;st.release();await page.locator('[data-target-v1] [data-target-rank-row]').first().waitFor();
        const x = await shared(page, TGT);assert.equal(x.source, 'PUBLICATION');assert.equal(x.rank, O.RANKS['TARGET:amd']);
        const tc = await basisOf(page, '[data-target-central]');assert.equal(tc.id, O.PUB.publication_id);assert.equal(tc.state, 'STALE');assert.ok(tc.attribution, 'playbook IEX terms link');
        assert.match(tc.text, /^공식 V · 중앙 게시 · IEX 마지막 체결가 기준\(공식 종가 아님\) · 가격 기준일 2026-10-13 · 게시 2026-10-13 22:40 UTC · STALE/);
        await page.evaluate((id) => { location.hash = 'company/' + id; }, TGT);await page.locator('[data-qgv-central] [data-central-basis="' + O.PUB.publication_id + '"]').waitFor();
        assert.equal(await page.locator('[data-company-card="qgv"] [data-qgv="rank"] .num').textContent(), String(x.rank));
        await page.evaluate(() => { location.hash = 'leaderboard'; });await page.locator('[data-leaderboard-rank]').first().waitFor();
        const lb = await basisOf(page, '[data-leaderboard-central]');assert.equal(lb.id, O.PUB.publication_id);assert.equal(lb.state, 'STALE');assert.ok(lb.attribution);
        assert.equal(await page.locator('[data-leaderboard-row="' + TGT + '"] [data-leaderboard-rank]').getAttribute('data-leaderboard-rank'), String(x.rank));
        await page.locator('[data-v-coverage="READY"]').waitFor();
        // 3. Away and back: nothing read again.
        phase = 'NAVIGATION ' + width;for (const h of ['home', 'portfolio', 'company/' + TGT, 'leaderboard']) { await page.evaluate((x) => { location.hash = x; }, h);await page.waitForTimeout(150); }
        await page.locator('[data-leaderboard-rank]').first().waitFor();assert.equal(st.reads, 1, 'one read of qgv-official.json per page');
        // 4. A failed re-read keeps the last publication and says so.
        phase = 'FAILED_REREAD ' + width;st.serve = 'FAIL';await page.evaluate(() => window.dispatchEvent(new CustomEvent('public-data-updated', { detail: { reason: 'APPLIED' } })));
        await page.waitForFunction(() => QgvScores.pagePublication().last_attempt_reason === 'OFFICIAL_UNAVAILABLE');assert.equal(st.reads, 2);
        const y = await shared(page, TGT);assert.deepEqual([y.source, y.v, y.total, y.rank], [x.source, x.v, x.total, x.rank], 'the last central V is kept');
        await page.locator('[data-leaderboard-central] [data-central-basis]').filter({ hasText: '다시 읽기 실패(OFFICIAL_UNAVAILABLE) · 마지막 게시본 표시' }).waitFor();
        assert.equal(await page.locator('[data-leaderboard-row="' + TGT + '"]').getAttribute('data-cx-read-failure'), 'OFFICIAL_UNAVAILABLE');
        // A freshness re-judge reads nothing.
        await page.evaluate(() => window.dispatchEvent(new CustomEvent('public-data-updated', { detail: { reason: 'REJUDGE' } })));await page.waitForTimeout(300);assert.equal(st.reads, 2, 'a re-judge reads nothing');
        // 6. The S06 preset follows on the company page (personal preset, labelled; never the official ranking).
        phase = 'PRESET ' + width;await page.locator('[data-qgv2-preset="growth"]').click();await page.waitForFunction(() => QgvScores.pageProfile().preset === 'growth');
        const g = await shared(page, TGT);assert.equal(g.profile, 'qgv-v2/growth/gate-on');
        await page.evaluate((id) => { location.hash = 'company/' + id; }, TGT);await page.waitForFunction((p) => document.querySelector('[data-qgv-rank-scope]')?.dataset.qgvProfile === p, g.profile);
        assert.ok(!(await page.locator('[data-qgv-rank-scope]').textContent()).includes('공식 QGV 순위'), 'a personal preset rank is never called official');
        await clean(page, seen);pass++;console.log('PASS v session state (pending / landed / kept / failed re-read / preset) ' + width);
      } catch (e) { fail++;console.log('FAIL v session state ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 4).join(' | ') : e)); } finally { await context.close(); }
      // 5. No publication at all (the first read fails): V NA with its reason everywhere, no rank, never a device V.
      ({ context, page, st, seen } = await open(browser, width, { hold: false, serve: 'FAIL' }));
      try {
        phase = 'NO_PUBLICATION ' + width;await page.goto(BASE + '#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
        await page.waitForFunction(() => QgvScores.pagePublication().reason === 'OFFICIAL_UNAVAILABLE');
        const z = await shared(page, TGT);assert.deepEqual([z.source, z.reason, z.v, z.rank], ['NONE', 'OFFICIAL_UNAVAILABLE', null, null]);
        await page.locator('[data-v-coverage-state="OFFICIAL_UNAVAILABLE"]').waitFor();assert.equal(await page.locator('[data-leaderboard-rank]').count(), 0);
        assert.match(await page.locator('[data-leaderboard-official="NO_OFFICIAL_V"]').textContent(), /공식 V 없음: 중앙 V 게시본을 읽지 못했습니다/);
        await page.evaluate((id) => { location.hash = 'company/' + id; }, TGT);const cb = page.locator('[data-qgv-central] [data-central-basis]');await cb.waitFor();
        assert.equal(await cb.getAttribute('data-na'), 'OFFICIAL_UNAVAILABLE');assert.equal(await page.locator('[data-qgv-central] [data-attribution]').count(), 0);
        assert.doesNotMatch(await page.locator('[data-company-card="qgv"]').textContent(), /기기 V|가격 입력 필요/);
        await clean(page, seen);pass++;console.log('PASS v session state (no publication) ' + width);
      } catch (e) { fail++;console.log('FAIL v session state ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 4).join(' | ') : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
