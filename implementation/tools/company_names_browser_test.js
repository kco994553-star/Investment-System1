'use strict';
// KR-NAMES (owner decision 2026-10-18): the reviewed company-names-ko.json in the served build, checked in the real app.
// - Korean name, English (SEC) name, ticker and alias searches find the same company (case- and space-insensitive).
// - An UNREGISTERED company is still found by its English name and ticker and shows "English name · TICKER".
// - Share classes of one issuer are told apart ("알파벳 A · GOOGL" vs "알파벳 C · GOOG").
// - Titles read "한국어명 · 티커"; the company page lists the English name and the name source.
// - QGV values on the page are the same with and without the names file (names are display/search only).
// Synthetic Universe identity rows (sec_universe_shares_fixture.js) make the 504 codes searchable; sec-qgv2.json is the served
// file when the build carries one (REAL) or the strict synthetic payload (qgv_v2_fixture.js). External requests are aborted.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), path = require('node:path');
const ES = require('../src/investment_system/product/web_assets/entity-search.js'), SHARES = require('./sec_universe_shares_fixture.js'), F = require('./qgv_v2_fixture.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, SHOTS = process.env.PAGES_COCKPIT_EVIDENCE_DIR || '';
let phase = 'START';
async function get(name) { try { const r = await fetch(new URL(name, BASE)); return r.status === 200 ? JSON.parse(await r.text()) : null; } catch (_) { return null; } }

async function context(browser, width, { names, qgv }) {
  const ctx = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', locale: 'ko-KR' });
  const page = await ctx.newPage();page.setDefaultTimeout(20000);const errors = [];page.on('pageerror', (e) => errors.push(String(e)));
  await page.route('**/*', (r) => new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort());
  await page.route('**/sec-universe-shares.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SHARES.payload({})) }));
  if (qgv) await page.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(qgv) }));
  if (!names) await page.route('**/company-names-ko.json*', (r) => r.fulfill({ status: 404, body: '' }));
  return { ctx, page, errors };
}
async function search(page, q, id) {
  await page.locator('#global-search').fill(q);
  await page.waitForFunction((want) => document.querySelector('#global-results li')?.dataset.entityId === want, 'COMPANY:' + id).catch(() => {});
  const first = await page.locator('#global-results li').first().getAttribute('data-entity-id');
  assert.equal(first, 'COMPANY:' + id, 'query ' + JSON.stringify(q));
  return page.locator('#global-results li').first();
}
// QGV numbers of one company page, as the page exposes them (axis scores, factor values, total).
async function qgvValues(page, hash) {
  await page.goto(BASE + '#' + hash);
  if (hash.includes('%3A')) { await page.locator('[data-universe-page]').waitFor();await page.waitForFunction(() => document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING'); }
  else await page.locator('[data-company-card="qgv"]').waitFor();
  return page.evaluate(() => {
    const pick = (sel, attrs) => [...document.querySelectorAll(sel)].map((e) => attrs.map((a) => e.getAttribute(a)).join('='));
    const card = document.querySelector('[data-company-card="qgv"]');
    return { axes: pick('[data-uc-axis]', ['data-uc-axis', 'data-uc-axis-state', 'data-uc-score']), factors: pick('[data-uc-factor]', ['data-uc-factor', 'data-uc-value', 'data-uc-factor-state']),
      total: pick('[data-uc-total]', ['data-uc-total']), target: card ? card.innerText.replace(/\s+/g, ' ').trim() : null };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0;
  try {
    const raw = await get('company-names-ko.json');assert.ok(raw, 'the build must serve company-names-ko.json');
    const N = ES.nameIndex(raw);assert.ok(N, 'names file valid for the browser reader');
    const served = await get('sec-qgv2.json'), qgv = served ? null : F.strictPayload(), mode = served ? 'REAL' : 'SYNTHETIC';
    const recs = raw.records;
    const unreg = recs.find((r) => r.key_kind === 'UNIVERSE_CODE' && r.ko_status === 'UNREGISTERED' && r.en_name && !r.class_label && !recs.some((x) => x !== r && x.en_name === r.en_name));
    const meta = N.get('NASDAQ:META'), nvda = N.get('nvda'), goog = N.get('NASDAQ:GOOG'), googl = N.get('googl');
    assert.ok(meta && meta.ko_name === '메타' && meta.aliases.some((a) => a.text === '페이스북'), 'META record');
    console.log('COMPANY_NAMES mode=' + mode + ' records=' + raw.counts.records + ' unregistered_sample=' + unreg.key);

    for (const width of [390, 1440]) {
      const { ctx, page, errors } = await context(browser, width, { names: true, qgv });
      try {
        phase = width + ' SEARCH_SAME_COMPANY';await page.goto(BASE + '#home');await page.locator('#global-search').waitFor();
        // Universe code with a COMMON Korean name: Korean name, English name, ticker, alias; case and spaces ignored.
        for (const q of ['메타', '메 타', 'Meta Platforms, Inc.', 'meta platforms inc', 'META', 'meta', '페이스북', '메타플랫폼스']) await search(page, q, 'NASDAQ:META');
        // TARGET company with an OFFICIAL Korean name (Latin brand on the official Korean page) and a sourced Hangul alias.
        for (const q of ['NVIDIA', 'NVIDIA CORP', 'nvda', '엔비디아', '엔 비디아']) await search(page, q, 'nvda');
        for (const q of ['램리서치', '램 리서치', 'LAM RESEARCH CORP', 'LRCX']) await search(page, q, 'lrcx');
        phase = width + ' DISPLAY';
        const hit = await search(page, '메타', 'NASDAQ:META');
        assert.equal((await hit.locator('.hit-name').textContent()).trim(), '메타 · META');assert.equal(await hit.getAttribute('data-name-status'), 'COMMON');
        assert.ok((await hit.locator('.hit-sub').textContent()).includes(meta.en_name), 'English name under the Korean name');
        phase = width + ' UNREGISTERED';
        for (const q of [unreg.en_name, unreg.en_name.toLowerCase(), unreg.ticker]) {
          const h = await search(page, q, unreg.key);
          assert.equal((await h.locator('.hit-name').textContent()).trim(), unreg.en_name + ' · ' + unreg.ticker);assert.equal(await h.getAttribute('data-name-status'), 'UNREGISTERED');
        }
        phase = width + ' SHARE_CLASS';
        await page.locator('#global-search').fill('알파벳');
        await page.waitForFunction(() => document.querySelectorAll('#global-results [data-entity-id="COMPANY:googl"], #global-results [data-entity-id="COMPANY:NASDAQ:GOOG"]').length === 2);
        assert.equal((await page.locator('#global-results [data-entity-id="COMPANY:googl"] .hit-name').textContent()).trim(), '알파벳 A · GOOGL');
        assert.equal((await page.locator('#global-results [data-entity-id="COMPANY:NASDAQ:GOOG"] .hit-name').textContent()).trim(), '알파벳 C · GOOG');
        assert.equal(ES.companyTitle(goog, null, 'ko-KR'), '알파벳 C · GOOG');assert.equal(ES.companyTitle(googl, null, 'ko-KR'), '알파벳 A · GOOGL');
        assert.equal(await page.locator('#global-results [data-entity-id="COMPANY:NASDAQ:GOOGL"]').count(), 0, 'GOOGL is the TARGET record, not a second entry');
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll (search)');
        if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'company-names-search-' + width + '.png') });
        await page.locator('#global-search').press('Escape');

        phase = width + ' PAGES';
        await page.goto(BASE + '#company/NASDAQ%3AMETA');await page.waitForFunction(() => document.querySelector('main h1')?.textContent === '메타 · META');
        const box = page.locator('[data-universe-page] [data-company-names="COMMON"]');
        assert.equal((await box.locator('[data-name-en="PRESENT"]').textContent()).includes(meta.en_name), true);
        assert.equal(await box.locator('[data-name-ko="COMMON"] a').getAttribute('href'), meta.ko_source);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll (Universe page)');
        if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'company-names-universe-' + width + '.png'), fullPage: false });
        await page.goto(BASE + '#company/' + encodeURIComponent(unreg.key));await page.waitForFunction((t) => document.querySelector('main h1')?.textContent === t, unreg.en_name + ' · ' + unreg.ticker);
        assert.equal(await page.locator('[data-company-names="UNREGISTERED"] [data-name-ko="UNREGISTERED"]').count(), 1);
        await page.goto(BASE + '#company/googl');await page.waitForFunction(() => document.querySelector('main h1')?.textContent === '알파벳 A · GOOGL');
        assert.ok((await page.locator('[data-company-names] [data-name-class="A"]').textContent()).includes('Class A'));
        await page.goto(BASE + '#company/nvda');await page.waitForFunction(() => document.querySelector('main h1')?.textContent === 'NVIDIA · NVDA');
        assert.ok((await page.locator('[data-company-names="OFFICIAL"] [data-name-en="PRESENT"]').textContent()).includes(nvda.en_name));
        assert.ok((await page.locator('[data-company-names="OFFICIAL"] [data-name-aliases]').textContent()).includes('엔비디아'));
        if (SHOTS) await page.screenshot({ path: path.join(SHOTS, 'company-names-target-' + width + '.png') });
        assert.deepEqual(errors, []);
      } finally { await ctx.close(); }
    }
    pass++;console.log('PASS search by Korean name / English name / ticker / alias, unregistered fallback, share classes, titles');

    phase = 'QGV_UNCHANGED';
    const sample = Object.entries(served || qgv).length ? Object.entries((served || qgv).records).filter(([, r]) => ['LIVE', 'STALE'].includes(r.state)).slice(0, 6).map(([c]) => c) : [];
    assert.ok(sample.length >= 3, 'sample rows');
    const hashes = [...sample.map((c) => 'company/' + encodeURIComponent(c)), 'company/nvda', 'company/googl'];
    const withNames = await context(browser, 1440, { names: true, qgv }), without = await context(browser, 1440, { names: false, qgv });
    try {
      for (const h of hashes) {
        const a = await qgvValues(withNames.page, h), b = await qgvValues(without.page, h);
        assert.deepEqual(a, b, 'QGV values differ with the names file on ' + h);
        assert.ok(a.axes.length || a.target, 'values read on ' + h);
      }
      // Without the file the page falls back to the ticker and says so; the company is still there.
      await without.page.goto(BASE + '#company/' + encodeURIComponent(sample[0]));await without.page.locator('[data-uc-name="NOT_LOADED"]').waitFor();
      assert.equal(await without.page.locator('main h1').textContent(), sample[0].slice(sample[0].indexOf(':') + 1));
      assert.deepEqual(withNames.errors, []);assert.deepEqual(without.errors, []);
    } finally { await withNames.ctx.close();await without.ctx.close(); }
    pass++;console.log('PASS QGV values unchanged with and without company-names-ko.json (' + hashes.length + ' pages, mode=' + mode + ')');
    console.log('COMPANY_NAMES_BROWSER_OK checks=' + pass);
  } catch (e) {
    console.log('COMPANY_NAMES_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message ? e.message.split('\n').slice(0, 6).join(' | ') : e));process.exitCode = 1;
  } finally { await browser.close(); }
})();
