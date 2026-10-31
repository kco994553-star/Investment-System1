'use strict';
// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다') on the TARGET v1 writer (#playbook, 'QGV v2 총점·업종 내
// 순위로 후보 추림') at 390 and 1280. DC-31 (owner decision 2026-10-31, device V abolished): the candidates read the ONE official
// result of the central publication (QgvScores.officialPage over the synthetic qgv-official.json of qgv_official_fixture.js and the
// strictly valid synthetic sec-qgv2.json of qgv_v2_fixture.js; no price anywhere, no Universe read): the candidate table lists only
// rows with a published official rank, in the published order; the value-trap-gate row (ABNB: V published, left out by the gate)
// stays in it; the Q·G-only rows (financial GOOGL / AMZN, MMM without an IEX trade) are only in the separate list labelled
// 'Q·G 참고 (V 미포함) · 공식 QGV 순위 아님' and their candidate option says so; nothing is stored.
let phase = 'START';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin;
// The playbook's official score result (the same QgvScores.officialPage call PlaybookScreen.mount makes) and its candidate view.
const expected = (page) => page.evaluate(async () => {
  const idByTicker = new Map(identityCompanies.map((r) => [r.ticker, r.company_id]));
  const universeCodes = await fetch('universe-codes.json', { cache: 'no-store' }).then((r) => r.json()).then((p) => p.codes);
  const S = QgvScores.officialPage(window, { v2Inputs: publicScreens[Qgv2Inputs.FILE], identities: [...idByTicker].map(([ticker, company_id]) => ({ ticker, company_id })) }).computed;
  const tickers = new Set(universeCodes.map((c) => c.slice(c.indexOf(':') + 1))), rows = Object.values(S.rows);
  const official = rows.filter((r) => Number.isInteger(r.rank) && tickers.has(r.ticker) && publicScreens[Qgv2Inputs.FILE].records[universeCodes.find((c) => c.endsWith(':' + r.ticker))]?.identity_withdrawn !== true).sort((a, b) => a.rank - b.rank).map((r) => r.ticker);
  const qg = rows.filter((r) => r.qg_reference && tickers.has(r.ticker)).sort((a, b) => a.qg_reference.order - b.qg_reference.order).map((r) => r.ticker);
  const by = Object.fromEntries(rows.map((r) => [r.ticker, { rank: r.rank, qg: r.qg_reference, v: r.primary.v, total: r.primary.total, gate: r.primary.value_trap_gate === true }]));
  return { official, qg, by, label: PlaybookScreen.QG_CANDIDATE_LABEL, source: S.source };
});
const cells = (loc) => loc.evaluateAll((rs) => rs.map((r) => [...r.querySelectorAll('td')].map((c) => c.textContent)));

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0, fail = 0;
  const payload = F.strictPayload();
  try {
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
      await routeEmptyPublicScreens(context);
      await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) }));
      await O.routeOfficial(context);
      const page = await context.newPage();let errors = 0;page.on('pageerror', () => errors++);
      const external = [];page.on('request', (r) => { if (!/^(data|blob):/.test(r.url()) && new URL(r.url()).origin !== ORIGIN) external.push(r.url()); });
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      try {
        // No Universe read: the candidates come from the central publication only (a device price never makes a rank).
        phase = 'PLAYBOOK';await page.goto(BASE + '#playbook');
        const writer = page.locator('[data-target-v1]');await writer.waitFor();await writer.locator('[data-target-rank-row]').first().waitFor();
        const x = await expected(page);
        assert.equal(x.source, 'PUBLICATION');assert.equal(x.by.AMD.rank, O.RANKS['TARGET:amd'], 'AMD: the published rank of its TARGET row');
        assert.equal(x.by.ABNB.gate, true, 'gate fixture');assert.equal(x.by.ABNB.rank, O.RANKS['NASDAQ:ABNB'], 'gate row keeps its published rank');
        for (const t of ['MMM', 'GOOGL', 'AMZN']) assert.ok(x.by[t].qg && x.by[t].rank === null && Number.isFinite(x.by[t].total) && !Number.isFinite(x.by[t].v), t + ' is Q·G only');
        assert.equal(x.by.MMM.qg.reason, 'NO_IEX_TRADE');assert.equal(x.by.GOOGL.qg.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');
        // (1) Candidate table = the official ranked order (first 30), ranks 1.., then rows without any total (NA); no Q·G-only row.
        phase = 'RANKED';const shown = await writer.locator('[data-target-ranking] [data-target-rank-row]').evaluateAll((rs) => rs.map((r) => r.dataset.targetRankRow));
        const main = await cells(writer.locator('[data-target-ranking] [data-target-rank-row]')), ranked = main.filter((c) => c[1] !== '—');
        assert.deepEqual(ranked.map((c) => c[0]), x.official.slice(0, 30), 'selection == official ranked order');
        assert.deepEqual(ranked.map((c) => c[1]), ranked.map((_, i) => String(i + 1)));
        for (const c of ranked) assert.equal(c[2], x.by[c[0]].total.toFixed(1), c[0]);
        for (const c of main.filter((c) => c[1] === '—')) assert.equal(c[2], 'NA', c[0] + ' unranked rows show no total');
        for (const t of x.qg) assert.ok(!shown.includes(t), t + ' (Q·G only) never in the QGV candidate table');
        assert.ok(shown.includes('ABNB') && shown.includes('AMD'), 'the gate row stays a candidate');
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
        for (const t of ['MMM', 'GOOGL', 'AMZN']) { const o = await opt(t);assert.match(o, /^\S+ · Q·G 참고 \(V 미포함\) \d+\.\d · 공식 QGV 순위 아님$/, o);assert.ok(!/QGV \d|업종 순위/.test(o), o); }
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
        pass++;console.log('PASS D11 candidate split ' + width + ' (synthetic fixture + synthetic central publication)');
      } catch (e) { fail++;console.log('FAIL D11 candidate split ' + width + ' ' + phase + ' · ' + (e && e.message ? e.message.split('\n')[0] : e)); } finally { await context.close(); }
    }
  } finally { await browser.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail);if (fail) process.exitCode = 1;
})();
