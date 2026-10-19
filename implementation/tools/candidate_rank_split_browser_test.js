'use strict';
// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다') on the TARGET v1 writer (#playbook, 'QGV v2 총점·업종 내
// 순위로 후보 추림') at 390 and 1280, after a Universe read with SYNTHETIC FIXTURE PRICES (made-up numbers, a stubbed sheet read in
// RAM, never real prices): the candidate table lists only rows with an official QGV rank, in the official order (the playbook's
// own QgvScores result filtered by the existing rules); the value-trap-gate row (amd: V computed, left out by the approved gate)
// stays in it; the Q·G-only rows (financial GOOGL / AMZN, unpriced MSFT) are only in the separate list labelled
// 'Q·G 참고 (V 미포함) · 공식 QGV 순위 아님' and their candidate option says so; nothing is stored. Q·G side: the strictly valid
// synthetic fixture with TARGET amd made weak in Q (as in qgv_rank_split_browser_test.js) so the gate fires.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
function gatedPayload() {
  const SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js'), p = F.strictPayload(), amd = p.target.amd;
  Object.assign(amd.metrics, { roic: -0.5, gross_profit_to_assets: -0.5, moat_proxy: -0.5, accruals_to_assets: 0.5, fcf_to_net_income: -2, net_debt_to_ebitda: 20, interest_coverage: -5, dilution_3y: 0.5, incremental_roic_5y: -0.5 });
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version), sc = scores.get('target\u0000amd');amd.factors = sc.factors;amd.axes = sc.axes;
  SQ.validate(p);return p;
}
// The playbook's own score result (the same call PlaybookScreen.mount makes) and its candidate view, read from the running page.
const expected = (page) => page.evaluate(async () => {
  const catalog = await deviceCatalog(), idByTicker = new Map(identityCompanies.map((r) => [r.ticker, r.company_id]));
  const universeCodes = await fetch('universe-codes.json', { cache: 'no-store' }).then((r) => r.json()).then((p) => p.codes);
  const S = await PlaybookScreen.prepareScores(window, { catalog, screens: publicScreens, idByTicker, universeCodes, scoreOptions: playbookScoreOptions });
  const tickers = new Set(universeCodes.map((c) => c.slice(c.indexOf(':') + 1))), rows = Object.values(S.rows);
  const official = rows.filter((r) => Number.isInteger(r.rank) && tickers.has(r.ticker) && publicScreens[Qgv2Inputs.FILE].records[universeCodes.find((c) => c.endsWith(':' + r.ticker))]?.identity_withdrawn !== true).sort((a, b) => a.rank - b.rank).map((r) => r.ticker);
  const qg = rows.filter((r) => r.qg_reference && tickers.has(r.ticker)).sort((a, b) => a.qg_reference.order - b.qg_reference.order).map((r) => r.ticker);
  const by = Object.fromEntries(rows.map((r) => [r.ticker, { rank: r.rank, qg: r.qg_reference, v: r.primary.v, total: r.primary.total, gate: r.primary.value_trap_gate === true }]));
  return { official, qg, by, label: PlaybookScreen.QG_CANDIDATE_LABEL };
});
const cells = (loc) => loc.evaluateAll((rs) => rs.map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent)));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const payload = gatedPayload();
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) }));
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        phase = 'SETUP';await page.goto(BASE + '#settings');await page.locator('[data-universe-source]').waitFor();
        await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
        await page.evaluate(async (values) => {
          await DeviceActual.sheetSettings(window, { schema: 'device-google-sheet-settings/1', enabled: true, spreadsheet_id: '', range: 'Quotes!A1:C22' });
          const session = { state: () => ({ enabled: true, connected: true }), revision: () => 1, setEnabled() {}, subscribe: () => () => {}, async fetchValues() { return { values }; } };
          window.GoogleSheetQuotes = { ...GoogleSheetQuotes, sessionFor: () => session };location.hash = 'leaderboard';
        }, F.strictUniverseValues());
        phase = 'READ';await page.locator('[data-leaderboard-table]').waitFor();
        await page.locator('details:has(#private-subset-root) > summary').click();await page.locator('[data-private-subset] [data-subset-action="read"]:enabled').click();
        await page.locator('[data-v-coverage="READY"]').waitFor();await page.locator('[data-leaderboard-rank]').first().waitFor();
        // Same page session (device quotes stay in RAM): open the TARGET v1 writer.
        phase = 'PLAYBOOK';await page.evaluate(() => { location.hash = 'playbook'; });
        const writer = page.locator('[data-target-v1]');await writer.waitFor();await writer.locator('[data-target-rank-row]').first().waitFor();
        const x = await expected(page);
        assert.equal(x.by.AMD.gate, true, 'gate fixture');assert.ok(Number.isInteger(x.by.AMD.rank), 'gate row has an official rank');
        for (const t of ['MSFT', 'GOOGL', 'AMZN']) assert.ok(x.by[t].qg && x.by[t].rank === null && Number.isFinite(x.by[t].total) && !Number.isFinite(x.by[t].v), t + ' is Q·G only');
        assert.equal(x.by.MSFT.qg.reason, 'NO_DEVICE_PRICE');assert.equal(x.by.GOOGL.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');
        // (1) Candidate table = the official ranked order (first 30), ranks 1.., then rows without any total (NA); no Q·G-only row.
        phase = 'RANKED';const shown = await writer.locator('[data-target-ranking] [data-target-rank-row]').evaluateAll((rs) => rs.map((r) => r.dataset.targetRankRow));
        const main = await cells(writer.locator('[data-target-ranking] [data-target-rank-row]')), ranked = main.filter((c) => c[1] !== '—');
        assert.deepEqual(ranked.map((c) => c[0]), x.official.slice(0, 30), 'selection == official ranked order');
        assert.deepEqual(ranked.map((c) => c[1]), ranked.map((_, i) => String(i + 1)));
        for (const c of ranked) assert.equal(c[2], x.by[c[0]].total.toFixed(1), c[0]);
        for (const c of main.filter((c) => c[1] === '—')) assert.equal(c[2], 'NA', c[0] + ' unranked rows show no total');
        for (const t of x.qg) assert.ok(!shown.includes(t), t + ' (Q·G only) never in the QGV candidate table');
        assert.ok(shown.includes('AMD'), 'the gate row stays a candidate');
        assert.match(await writer.locator('[data-target-ranking] > p').textContent(), /공식 QGV 순위\(V 포함\) 순/);
        // (2) The separate, labelled Q·G list in its own order.
        phase = 'QG_LIST';const qgBox = writer.locator('[data-target-qg-reference]');
        assert.equal(await qgBox.locator('[data-target-qg-label]').textContent(), x.label + ' · 공식 QGV 순위 아님');assert.equal(x.label, 'Q·G 참고 (V 미포함)');
        const qgRows = await cells(qgBox.locator('[data-target-qg-row]'));
        assert.deepEqual(qgRows.map((c) => c[0]), x.qg, 'Q·G list = its own order');assert.deepEqual(qgRows.map((c) => c[1]), qgRows.map((_, i) => String(i + 1)));
        for (const c of qgRows) assert.equal(c[2], x.by[c[0]].total.toFixed(1), c[0]);
        assert.equal(await writer.locator('[data-target-ranking] [data-target-qg-row]').count(), 0, 'lists never mixed');
        assert.match(qgRows.find((c) => c[0] === 'GOOGL')[4], /금융업/);
        // (3) Candidate options: a Q·G-only total is labelled, never shown as a QGV total or an industry rank.
        phase = 'OPTIONS';const opt = async (t) => writer.locator('[data-target-candidate] option[value="' + t + '"]').textContent();
        for (const t of ['MSFT', 'GOOGL', 'AMZN']) { const o = await opt(t);assert.match(o, /^\S+ · Q·G 참고 \(V 미포함\) \d+\.\d · 공식 QGV 순위 아님$/, o);assert.ok(!/QGV \d|업종 순위/.test(o), o); }
        assert.match(await opt('AMD'), /^AMD · QGV \d+\.\d · 업종 순위 \d+$/);
        // (4) The industry filter narrows both lists by the same rule.
        phase = 'FILTER';const industries = await writer.locator('[data-target-industry] option').evaluateAll((os) => os.map((o) => o.value).filter(Boolean));
        for (const ind of industries) {
          await writer.locator('[data-target-industry]').selectOption(ind);
          const rk = (await cells(writer.locator('[data-target-ranking] [data-target-rank-row]'))).filter((c) => c[1] !== '—').map((c) => c[0]);
          assert.ok(rk.every((t) => !x.qg.includes(t)), ind);assert.deepEqual(rk, x.official.filter((t) => rk.includes(t)), ind + ' keeps the official order');
        }
        await writer.locator('[data-target-industry]').selectOption('');
        assert.deepEqual(external, []);assert.equal(errors, 0);
        console.log('INFO ' + width + ' candidates ranked=' + ranked.length + '/' + x.official.length + ' qg=' + qgRows.length + ' industries=' + industries.length);
        pass++;console.log('PASS D11 candidate split ' + width + ' (synthetic fixture + synthetic prices)');
      } catch (e) { fail++;console.log('FAIL D11 candidate split ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
