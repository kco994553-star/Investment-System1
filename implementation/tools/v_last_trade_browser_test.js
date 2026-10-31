'use strict';
/* Owner decision 2026-10-31 (docs/qgv_official/LAST_TRADE_TIME_20261031.md): "마지막 체결 HH:MM (뉴욕)" next to a shown official V,
   only when the IEX last trade was at least 30 minutes before the publication's session close; nothing when the time is absent or
   later. In a real browser, phone 390 px and PC width, on ONE synthetic publication: the vector case last_trade_every_v_row_valid
   (tests/fixtures/qgv_official_vectors_v1.json; close 16:00 New York) with TARGET:amd retimed to 10:05 New York (note) and
   TARGET:nvda left at 15:45 (no note). Synthetic data only; nothing here is a price.
   - New app (development site, tools/web_app_test_site.js): 1.1 leaderboard V cells (PC) and the phone row line carry exactly the
     layer row's v_last_trade.text (= QgvOfficial.lastTradeText of the row's own publication row), rows without a note show none,
     the V cells keep the layer value; the company QGV card under its V bar (amd: 10:05, nvda: none).
   - Old app (PAGES_COCKPIT_URL, as the other old-app browser tests): S06 row detail line, the company QGV card V cell and its radar
     V cell (amd note, nvda none), the Universe company page V line (NASDAQ:ADBE 15:30 = exactly 30 minutes: note; NASDAQ:ABNB
     15:59:59: none) and the home search result's QGV card under its bars (amd note, nvda none). Skipped (and said so) without
     PAGES_COCKPIT_URL.
   - Every page: no horizontal overflow at 390 px, no page error, no request outside the origin. */
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const site = require('./web_app_test_site'), F = require('./qgv_v2_fixture.js'), O = require('./qgv_official_fixture.js'), { routeEmptyPublicScreens } = require('./empty_public_screens.js'), { displayOnlyOff } = require('./display_only_off.js');
const NOTE = '마지막 체결 10:05 (뉴욕)';
// The synthetic publication: every V row timed (15:59:59 / 15:30 / 09:30 / 15:45 ...), amd at 10:05 New York (14:05Z, EDT).
const PUB = O.variant('last_trade_every_v_row_valid', (p) => { p.rows['TARGET:amd'].v_last_trade_at = '2026-10-13T14:05:00Z'; });
const PUB_TEXT = JSON.stringify(PUB), QGV2 = F.strictPayload();
assert.equal(PUB.rows['TARGET:nvda'].v_last_trade_at, '2026-10-13T19:45:00Z'); assert.equal(PUB.rows['NASDAQ:ADBE'].v_last_trade_at, '2026-10-13T19:30:00Z');
assert.equal(PUB.rows['NASDAQ:ABNB'].v_last_trade_at, '2026-10-13T19:59:59Z'); assert.equal(PUB.times.price_session_close_at, '2026-10-13T20:00:00Z');
let phase = 'START', checks = 0;
const eq = (a, b, m) => { checks++; assert.deepEqual(a, b, m); }, ok = (c, m) => { checks++; assert.ok(c, m); };
const noOverflow = async (page, label) => ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), label + ': no horizontal overflow');

async function newApp(browser, s, width, height) {
  const phone = width < 720, context = await browser.newContext({ viewport: { width, height } });
  await context.clock.setFixedTime(new Date('2026-10-14T03:00:00.000Z'));
  const outside = [];
  await context.route('**/*', (r) => { const u = new URL(r.request().url()); if (u.origin === s.origin) return r.continue(); outside.push(u.origin + u.pathname); return r.abort(); });
  const page = await context.newPage(); let errors = 0; page.on('pageerror', (e) => { errors++; console.log('PAGEERROR ' + String(e && e.message).slice(0, 200)); });
  try {
    phase = 'new app leaderboard ' + width;
    await page.goto(s.base + '#/qgv'); await page.evaluate(() => window.IS2.ready); await page.locator('[data-lb-table] tbody tr[data-row]').first().waitFor({ timeout: 20000 });
    const got = await page.evaluate(async () => {
      const pg = await window.IS2.qgv.page(), off = await window.IS2.data.official(), QO = window.QgvOfficial, out = [];
      for (const tr of document.querySelectorAll('[data-lb-table] tbody tr[data-row]')) {
        const r = pg.rows.find((x) => x.id === tr.dataset.row), cell = tr.querySelector('td[data-cell=v]'), lines = [...tr.querySelectorAll('.m-only.sub-line')], line = lines[lines.length - 1];
        const own = r && r.score.v !== null && r.record && Object.hasOwn(off.payload.rows, r.record) ? QO.lastTradeText(QO.lastTrade(off.payload, r.record)) : null;
        out.push({ id: r ? r.id : tr.dataset.row, layer: r && r.v_last_trade ? r.v_last_trade.text : null, own, cell: [...cell.querySelectorAll('[data-v-last-trade]')].map((x) => x.textContent),
          line: lines.flatMap((l) => [...l.querySelectorAll('[data-v-last-trade]')].map((x) => x.textContent)), qgvLine: /\bV (?:[\d.]+|NA)/.test(line.textContent), cellText: cell.textContent, v: r ? r.score.v : null,
          lineShown: getComputedStyle(line).display !== 'none', cellShown: getComputedStyle(cell).display !== 'none' });
      }
      return out;
    });
    ok(got.length > 5 && got.every((r) => r.qgvLine), 'leaderboard rows drawn with their Q · G · V phone line: ' + got.length);
    const fmt = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
    let noted = 0, quiet = 0;
    for (const r of got) {
      eq(r.layer, r.own, r.id + ' layer text = QgvOfficial.lastTradeText of its publication row');
      eq(r.cell, r.layer ? [r.layer] : [], r.id + ' V cell note'); eq(r.line, r.layer ? [r.layer] : [], r.id + ' phone line note');
      if (r.v !== null) ok(r.cellText.startsWith(fmt(r.v)), r.id + ' V cell keeps the layer value: ' + r.cellText);
      if (r.layer) noted++; else if (r.v !== null) quiet++;
    }
    ok(noted >= 2 && quiet >= 2, 'noted ' + noted + ' / V without note ' + quiet);
    ok(got.some((r) => r.layer === '마지막 체결 15:30 (뉴욕)'), 'exactly 30 minutes before the close is noted');
    eq(got.every((r) => r.lineShown === phone && r.cellShown === !phone), true, 'phone: the row line; PC: the V column');
    await noOverflow(page, phase);
    phase = 'new app company card ' + width;
    for (const [id, want] of [['amd', 'V · ' + NOTE], ['nvda', null]]) {
      await page.goto(s.base + '#/company/' + id); await page.locator('[data-card=qgv] [data-qgv]').waitFor({ timeout: 20000 });
      const c = await page.evaluate(() => [...document.querySelectorAll('[data-card=qgv] [data-v-last-trade]')].map((x) => x.textContent));
      eq(c, want ? [want] : [], id + ' company QGV card'); await noOverflow(page, phase + ' ' + id);
    }
    eq(errors, 0, 'no page error'); eq([...new Set(outside)].filter((u) => !/accounts\.google\.com/.test(u)), [], 'no request outside the origin');
  } finally { await context.close(); }
}

async function oldApp(browser, base, width) {
  const origin = new URL(base).origin, context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
  await displayOnlyOff(context); await routeEmptyPublicScreens(context); await context.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(QGV2) }));
  await O.routeOfficial(context, PUB_TEXT);
  const page = await context.newPage(); let errors = 0; page.on('pageerror', (e) => { errors++; console.log('PAGEERROR ' + String(e && e.message).slice(0, 200)); });
  const external = []; page.on('request', (r) => { const u = r.url(); if (!/^(data|blob):/.test(u) && new URL(u).origin !== origin) external.push(u); });
  await page.route('**/*', (r) => (new URL(r.request().url()).origin === origin ? r.fallback() : r.abort()));
  try {
    phase = 'old app S06 ' + width;
    await page.goto(base + '#leaderboard'); await page.locator('[data-leaderboard-table]').waitFor();
    await page.waitForFunction(() => QgvScores.pagePublication().publication !== null && document.querySelectorAll('[data-leaderboard-row] [data-leaderboard-qgv2]').length > 5);
    const rows = await page.evaluate(() => {
      const inputs = publicScreens[Qgv2Inputs.FILE], P = QgvScores.officialPage(window, { v2Inputs: inputs, identities: identityCompanies }), C = QgvScores.presetView(P, { v2Inputs: inputs });
      return [...document.querySelectorAll('[data-leaderboard-row]')].map((tr) => { const id = tr.dataset.leaderboardRow, row = QgvScores.rowOf(C, id), d = row ? row.primary : null;
        return { id, want: d ? QgvScores.lastTradeText(d) : null, text: (tr.querySelector('[data-leaderboard-qgv2]') || {}).textContent || '' }; });
    });
    let noted = 0;
    for (const r of rows) { if (r.want) { noted++; ok(r.text.includes(' · ' + r.want + ' · '), r.id + ' S06 detail names ' + r.want + ': ' + r.text); } else ok(!r.text.includes('마지막 체결'), r.id + ' S06 detail without note: ' + r.text); }
    ok(noted >= 2, 'S06 noted rows ' + noted); eq(rows.find((r) => r.id === 'amd').want, NOTE, 'amd S06 note');
    await noOverflow(page, phase);
    for (const [id, want] of [['amd', NOTE], ['nvda', null]]) {
      phase = 'old app company ' + id + ' ' + width;
      await page.evaluate((x) => { location.hash = 'company/' + encodeURIComponent(x); }, id); await page.locator('[data-company-card="qgv"] [data-qgv="V"]').waitFor();
      await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]'); return c && c.dataset.srReason !== 'PENDING'; });
      const c = await page.evaluate(() => ({ card: [...document.querySelectorAll('[data-company-card="qgv"] [data-qgv="V"] [data-v-last-trade]')].map((x) => x.textContent),
        radar: [...document.querySelectorAll('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"] [data-v-last-trade]')].map((x) => x.textContent),
        v: (document.querySelector('[data-company-card="qgv"] [data-qgv="V"] .num') || {}).textContent || null }));
      eq(c.card, want ? [want] : [], id + ' company V cell'); eq(c.radar, want ? [want] : [], id + ' radar V cell'); ok(c.v !== null, id + ' V shown');
      await noOverflow(page, phase);
    }
    for (const [code, want] of [['NASDAQ:ADBE', '마지막 체결 15:30 (뉴욕)'], ['NASDAQ:ABNB', null]]) {
      phase = 'old app Universe page ' + code + ' ' + width;
      await page.evaluate((x) => { location.hash = 'company/' + encodeURIComponent(x); }, code);
      await page.waitForFunction((c) => { const p = document.querySelector('[data-universe-page]'); return p && p.dataset.universePage === c && p.dataset.universeV !== 'PENDING'; }, code);
      const u = await page.evaluate(() => ({ line: [...document.querySelectorAll('[data-universe-card="qgv"] [data-uc-axis="V"] [data-v-last-trade]')].map((x) => x.textContent),
        score: document.querySelector('[data-universe-card="qgv"] [data-uc-axis="V"]').getAttribute('data-uc-score') }));
      eq(u.line, want ? [want] : [], code + ' Universe V line'); ok(u.score !== 'NA', code + ' V shown');
      await noOverflow(page, phase);
    }
    phase = 'old app home search result ' + width;
    await page.evaluate(() => { location.hash = 'home'; }); await page.locator('#home-search-slot #global-search').waitFor(); await page.waitForFunction(() => typeof window.investmentSearch === 'function');
    for (const [id, ticker, want] of [['amd', 'AMD', 'V · ' + NOTE], ['nvda', 'NVDA', null]]) {
      await page.fill('#global-search', ticker); const host = page.locator('#home-result[data-result-company="' + id + '"]'); await host.waitFor();
      await host.locator('[data-result-card="qgv"] .res-bar[data-axis="V"][data-res-state="AVAILABLE"]').waitFor();
      eq(await host.locator('[data-result-card="qgv"] [data-res-v-last-trade]').allTextContents(), want ? [want] : [], id + ' home QGV card');
      await noOverflow(page, phase + ' ' + id);
    }
    eq(errors, 0, 'no page error'); eq(external, [], 'no outside request');
  } finally { await context.close(); }
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined }); let pass = 0, fail = 0;
  const s = await site.start({ fixtures: { 'sec-qgv2.json': { json: QGV2 }, 'qgv-official.json': { body: PUB_TEXT, type: 'application/json' } } });
  try {
    for (const [width, height] of [[1440, 1000], [390, 844]]) {
      try { await newApp(browser, s, width, height); pass++; console.log('PASS last-trade note · new app ' + width); }
      catch (e) { fail++; console.log('FAIL last-trade note · ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 8).join(' | ') : e)); }
    }
    if (!process.env.PAGES_COCKPIT_URL) console.log('SKIP last-trade note · old app (PAGES_COCKPIT_URL not set)');
    else for (const width of [390, 1280]) {
      try { await oldApp(browser, process.env.PAGES_COCKPIT_URL, width); pass++; console.log('PASS last-trade note · old app ' + width); }
      catch (e) { fail++; console.log('FAIL last-trade note · ' + phase + ' · ' + (e && e.message ? e.message.split('\n').slice(0, 8).join(' | ') : e)); }
    }
  } finally { await browser.close(); await s.close(); }
  console.log('COUNTS pass=' + pass + ' fail=' + fail + ' checks=' + checks); if (fail || !pass) process.exitCode = 1;
})();
