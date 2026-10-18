'use strict';
// Universe504 company page (universe-company.js, IA-18 (b)) at 390 and 1280, checked against the sec-qgv2.json the page reads.
// REAL mode: the served build carries the published sec-qgv2.json (deploy builds, or a local build after the preserve steps); its
// rows are read back here and every Q/G axis score, factor percentile, peer basis/count, SIC/group/profile and source state on the
// page must equal them. SYNTHETIC mode (PR builds publish no data file): the strictly valid synthetic payload (qgv_v2_fixture.js)
// plus one Universe identity-conflict withdrawal is served by route. Cases: a LIVE general row, a policy-NA row (LIVE, an axis
// below 50% of its weight), a NOT_COLLECTED / CIK_UNRESOLVED code, a FINANCIAL row and (synthetic) a withdrawn code. No device
// prices exist in this browser, so V must be NOT_AVAILABLE with the engine's reason (financial: not applicable). Never 0 for NA.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const F = require('./qgv_v2_fixture.js'), SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, SHOTS = process.env.PAGES_COCKPIT_EVIDENCE_DIR || '';
const Q = Object.keys(SQ.Q_WEIGHTS), G = Object.keys(SQ.G_WEIGHTS), TARGET_CIKS = new Set(Object.values(SQ.TARGET_CIKS).filter(Boolean));
const close = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
const fmt = (v) => new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
let phase = 'START';
async function served() {
  try { const r = await fetch(new URL('sec-qgv2.json', BASE)); if (r.status !== 200) return null; return JSON.parse(await r.text()); } catch (_) { return null; }
}
function synthetic() {
  // A not-collected code turned into a Universe identity-conflict withdrawal row (UNI-WITHDRAWN): no other row changes.
  const p = F.strictPayload(), code = 'NYSE:XOM';
  if (p.records[code] && p.records[code].state === 'NOT_AVAILABLE') {
    const q = structuredClone(p);q.records[code] = { ...SQ.emptyRecord(SQ.WITHDRAWN_REASON), detected_at: '2026-10-13T12:00:00Z', withdrawn_acquired_at: '2026-10-12T00:00:00Z', withdrawn_cik: '0000000001' };
    try { SQ.validate(q);return { payload: q, withdrawn: code }; } catch (_) { /* keep the plain payload */ }
  }
  return { payload: p, withdrawn: null };
}
const fresh = (r, p) => Date.now() - Date.parse(r.acquired_at) <= p.stale_after_seconds * 1000 ? 'LIVE' : 'STALE';
function pick(p, test) { const rows = Object.entries(p.records).filter(([, r]) => test(r)); return (rows.find(([, r]) => !TARGET_CIKS.has(r.cik)) || rows[0] || [null])[0]; }
function cases(p, withdrawn, real) {
  const scored = (r) => ['LIVE', 'STALE'].includes(r.state);
  const out = [
    ['LIVE', pick(p, (r) => scored(r) && r.profile === 'GENERAL' && r.axes.Q.score !== null && r.axes.G.score !== null)],
    ['POLICY_NA', pick(p, (r) => scored(r) && r.profile === 'GENERAL' && [r.axes.Q, r.axes.G].some((a) => a.score === null && a.reason_codes.includes('AXIS_COVERAGE_BELOW_50')))],
    ['FINANCIAL', pick(p, (r) => scored(r) && r.profile === 'FINANCIAL')]];
  for (const reason of ['NOT_COLLECTED', 'CIK_UNRESOLVED']) out.push(['SOURCE_NA', pick(p, (r) => r.state === 'NOT_AVAILABLE' && r.reason_codes.includes(reason))]);
  if (withdrawn) out.push(['WITHDRAWN', withdrawn]);
  // A kind the served data does not contain is reported, not failed: the daily verify step runs this on whatever was collected.
  for (const [kind, code] of out) if (!code) console.log('CASE_ABSENT ' + kind + ' mode=' + (real ? 'REAL' : 'SYNTHETIC'));
  const list = out.filter(([, c]) => c);if (!list.length) throw Error('NO_CASES');return list;
}
async function check(page, p, kind, code) {
  const r = p.records[code], file = r.state === 'NOT_AVAILABLE' ? null : fresh(r, p), pg = page.locator('[data-universe-page]');
  phase = kind + ' ' + code;
  await page.goto(BASE + '#company/' + encodeURIComponent(code));await pg.waitFor();
  await page.waitForFunction(() => document.querySelector('[data-universe-page]')?.dataset.universeV !== 'PENDING');
  assert.equal(await pg.getAttribute('data-universe-page'), code);
  assert.equal(await page.locator('main h1').textContent(), code.slice(code.indexOf(':') + 1));
  const state = await pg.getAttribute('data-universe-state'), reason = await pg.getAttribute('data-universe-reason');
  if (kind === 'WITHDRAWN') assert.equal(state, 'WITHDRAWN');
  else if (kind === 'SOURCE_NA') { assert.equal(state, 'SOURCE_NA'); assert.equal(reason, r.reason_codes[0]); }
  else assert.equal(state, file);
  // Q / G axes: the published score or the NA kind, never 0 for NA.
  for (const axis of ['Q', 'G']) {
    const a = r.axes[axis], row = page.locator('[data-universe-card="qgv"] [data-uc-axis="' + axis + '"]'), shown = await row.getAttribute('data-uc-score'), st = await row.getAttribute('data-uc-axis-state');
    if (kind === 'WITHDRAWN') { assert.equal(st, 'WITHDRAWN');assert.equal(shown, 'NA');assert.match(await row.textContent(), /식별 충돌로 사용 중지/); continue; }
    if (kind === 'SOURCE_NA') { assert.equal(st, 'SOURCE_NA');assert.equal(shown, 'NA');assert.match(await row.textContent(), r.reason_codes[0] === 'CIK_UNRESOLVED' ? /CIK 미확인/ : /미수집/); continue; }
    if (a.score === null) { assert.equal(st, 'POLICY_NA');assert.equal(shown, 'NA');assert.match(await row.textContent(), /정책상 NA/);assert.ok(!/\b0\.0\b/.test(await row.locator('.num').textContent())); }
    else { assert.equal(st, 'SCORED');assert.ok(close(Number(shown), a.score), axis + ' ' + shown + ' vs ' + a.score);assert.equal((await row.locator('.num').textContent()).trim(), fmt(a.score)); }
    const meta = page.locator('[data-uc-axis-meta="' + axis + '"]');
    assert.equal(await meta.getAttribute('data-uc-peer-basis'), a.peer_basis || '');assert.equal(await meta.getAttribute('data-uc-peer-count'), String(a.peer_count));
    assert.ok((await meta.textContent()).includes(a.factors_available));
  }
  // Factor percentiles Q1…Q5 / G1…G5: each equals the published value; NA cells show — and a reason.
  for (const f of [...Q, ...G]) {
    const cell = page.locator('[data-uc-factor="' + f + '"]'), v = await cell.getAttribute('data-uc-value'), want = ['WITHDRAWN', 'SOURCE_NA'].includes(kind) ? null : r.factors[f];
    if (want === null) { assert.equal(v, 'NA', f);assert.equal((await cell.locator('[data-uc-pct]').textContent()).trim(), '—');assert.ok((await cell.locator('td').last().textContent()).trim().length > 3, f + ' reason'); }
    else { assert.ok(close(Number(v), want), f + ' ' + v + ' vs ' + want);assert.equal((await cell.locator('[data-uc-pct]').textContent()).trim(), fmt(want)); }
  }
  const labels = await page.locator('[data-uc-factor] th b').allTextContents();
  assert.deepEqual(labels, ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'G1', 'G2', 'G3', 'G4', 'G5', 'V1', 'V2', 'V3', 'V4', 'V5']);
  assert.match(await page.locator('[data-uc-factor="q_profitability"] th').textContent(), /수익성/);
  // V: no device price in this browser -> NOT_AVAILABLE with the engine reason; financial -> not applicable.
  phase = kind + ' V';assert.equal(await pg.getAttribute('data-universe-v'), 'NO_DEVICE_PRICE');
  const v = page.locator('[data-universe-card="qgv"] [data-uc-axis="V"]');assert.equal(await v.getAttribute('data-uc-score'), 'NA');
  if (kind === 'FINANCIAL') { assert.equal(await v.getAttribute('data-uc-axis-state'), 'NOT_APPLICABLE');assert.match(await v.textContent(), /해당 없음/); }
  else if (kind === 'LIVE' || kind === 'POLICY_NA') { assert.equal(await v.getAttribute('data-uc-axis-state'), 'DEVICE_NA');assert.match(await v.textContent(), /가격 입력 필요/); }
  for (const f of Object.keys(require('../src/investment_system/product/web_assets/qgv-v2.js').WEIGHTS.V)) assert.equal(await page.locator('[data-uc-factor="' + f + '"]').getAttribute('data-uc-value'), 'NA');
  // Freshness and classification blocks.
  phase = kind + ' FRESH';const fl = await page.locator('[data-universe-card="qgv"] [data-uc-fresh]').first().textContent();
  assert.ok(fl.includes(p.as_of.slice(0, 10)), 'as_of');if (file) { assert.ok(fl.includes(r.acquired_at.slice(0, 10)) && fl.includes('상태 ' + file)); if (p.calc_version) assert.ok(fl.includes(p.calc_version)); }
  assert.equal(await page.locator('[data-uc-sic]').getAttribute('data-uc-sic'), file ? r.sic : 'NA');
  assert.equal(await page.locator('[data-uc-group]').getAttribute('data-uc-group'), file ? r.industry_group : 'NA');
  assert.equal(await page.locator('[data-uc-profile]').getAttribute('data-uc-profile'), file ? r.profile : 'NA');
  assert.equal(await page.locator('[data-uc-filing-windows="NA"]').count(), 1);
  if (!TARGET_CIKS.has(r.cik)) assert.equal(await page.locator('[data-uc-chart="NA"]').count(), 1);
  assert.equal(await page.locator('[data-uc-name="NOT_PUBLISHED"]').count(), 1);
  assert.equal(await page.locator('[data-universe-company]').count(), 1);
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'no horizontal scroll');
  assert.equal(await page.locator('[data-universe-page] [style]').count(), 0, 'no inline styles');
}
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH });let pass = 0;
  try {
    const live = await served(), mode = live ? 'REAL' : 'SYNTHETIC', fx = live ? { payload: live, withdrawn: null } : synthetic(), p = fx.payload;
    SQ.validate(p);const list = cases(p, fx.withdrawn, !!live);console.log('UNIVERSE_COMPANY mode=' + mode + ' as_of=' + p.as_of + ' cases=' + list.map(([k, c]) => k + ':' + c).join(','));
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' }), page = await context.newPage();page.setDefaultTimeout(20000);
      const errors = [];page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('**/*', (r) => new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort());
      if (!live) await page.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(p) }));
      for (const [kind, code] of list) {
        await check(page, p, kind, code);pass++;
        if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true });await page.screenshot({ path: path.join(SHOTS, 'universe-company-' + kind.toLowerCase() + '-' + width + '.png'), fullPage: true }); }
      }
      assert.deepEqual(errors, []);await context.close();
    }
    console.log('UNIVERSE_COMPANY_BROWSER_OK checks=' + pass);
  } catch (e) { console.error('UNIVERSE_COMPANY_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
