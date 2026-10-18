'use strict';
// Stat window radar (stat-radar.js, owner item 1.4) at 390 and 1280 on its three mount points: the Universe504 company page,
// the TARGET company summary and the 1.4 QGV tree example. REAL mode reads the sec-qgv2.json the build serves; SYNTHETIC mode
// (PR builds publish no data file) serves the strictly valid synthetic payload (qgv_v2_fixture.js) by route.
// Checks, each recomputed here independently of the page code:
//  - public axes (revenue size, operating-margin stability): raw value, average-rank percentile over the cross-section (one point
//    per CIK, the subject's issuer point replaced), industry / SIC group choice and group averages (raw mean, mean percentile, n);
//  - price axes are NA (NO_DEVICE_PRICE) without device prices, and no vertex is drawn for an NA axis (never 0);
//  - with SYNTHETIC device bars installed in the page (made-up random walks, never real prices, never committed as data): the
//    1-year volatility, max drawdown and 12-1 momentum, their percentiles and the industry average equal an independent formula;
//    liquidity is NA (the price tab has no volume) and the pure function's median trading value equals an independent median;
//  - the competitor series is NOT_AVAILABLE (REL_SOURCE_PENDING); no inline styles; no horizontal overflow; nothing is written to
//    localStorage / sessionStorage by the radar.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const F = require('./qgv_v2_fixture.js'), SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, SHOTS = process.env.STAT_RADAR_SHOTS || '';
const close = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
const WITHDRAWN = 'IDENTITY_CONFLICT_WITHDRAWN', MIN_PEERS = 8, MIN_GROUP = 5;
let phase = 'START';
async function served() { try { const r = await fetch(new URL('sec-qgv2.json', BASE)); if (r.status !== 200) return null; return JSON.parse(await r.text()); } catch (_) { return null; } }

/* ---------- independent public-axis model ---------- */
const withdrawnRow = (r) => !!r && (Object.hasOwn(r, 'detected_at') || (Array.isArray(r.reason_codes) && r.reason_codes.includes(WITHDRAWN)));
const scored = (r, p) => !!r && ['LIVE', 'STALE'].includes(r.state) && !withdrawnRow(r) && (typeof p.calc_version !== 'string' || r.calc_version === p.calc_version);
function crossSection(p) {
  const bad = new Set(Object.values(p.target || {}).filter(withdrawnRow).map((r) => r.cik)), seen = new Set(), out = [];
  for (const code of Object.keys(p.records).sort()) { const r = p.records[code];
    if (!scored(r, p) || typeof r.cik !== 'string' || bad.has(r.cik) || seen.has(r.cik)) continue; seen.add(r.cik); out.push({ code, cik: r.cik, r }); }
  return out;
}
function revenue(r) { const v = r.v_inputs_v2; if (!v || v.currency !== 'USD' || !v.revenue) return null; const x = v.revenue; return Number.isFinite(x.ttm_value) ? x.ttm_value : Number.isFinite(x.fy_value) ? x.fy_value : null; }
const marginStd = (r) => (r.metrics && Number.isFinite(r.metrics.operating_margin_std_5y_pp) ? r.metrics.operating_margin_std_5y_pp : null);
const PUBLIC = { revenue_size: { dir: 1, get: revenue }, margin_stability: { dir: -1, get: marginStd } };
// QGV average-rank percentile by direct counting (no shared code with the page).
function pct(values, x) { const n = values.length; if (n < MIN_PEERS) return null; let less = 0, eq = 0; for (const v of values) { if (v < x) less++; else if (v === x) eq++; } return 100 * (less + (eq - 1) / 2) / (n - 1); }
function groups(subject, points) {
  const r = subject.r, others = points.filter((p) => p.cik !== subject.cik);
  let ind;
  if (r.profile === 'FINANCIAL') ind = { basis: 'FINANCIAL_PROFILE', key: 'FINANCIAL', m: others.filter((p) => p.r.profile === 'FINANCIAL') };
  else { const gen = others.filter((p) => p.r.profile !== 'FINANCIAL'), m = r.industry_group ? gen.filter((p) => p.r.industry_group === r.industry_group) : [];
    ind = r.industry_group && m.length + 1 >= MIN_PEERS ? { basis: 'INDUSTRY_GROUP', key: r.industry_group, m } : { basis: 'UNIVERSE_FALLBACK', key: 'GENERAL', m: gen }; }
  const withSic = others.filter((p) => typeof p.r.sic === 'string'), m4 = withSic.filter((p) => p.r.sic === r.sic);
  const sic = m4.length + 1 >= MIN_PEERS ? { basis: 'SIC4', key: r.sic, m: m4 } : { basis: 'SIC2', key: r.sic.slice(0, 2), m: withSic.filter((p) => p.r.sic.slice(0, 2) === r.sic.slice(0, 2)) };
  return { industry: ind, sic };
}
/* values: Map code -> raw (others), own raw or null; returns company / industry / sic expectations for one axis. */
function axisExpect(dir, values, own, gr) {
  const pop = [...values.values(), ...(own === null ? [] : [own])].map((v) => dir * v), out = { population: pop.length };
  out.company = own === null ? { raw: null, pct: null } : { raw: own, pct: pct(pop, dir * own) };
  for (const k of ['industry', 'sic']) { const mem = gr[k].m.filter((p) => values.has(p.code));
    if (mem.length < MIN_GROUP) { out[k] = { raw: null, pct: null, n: mem.length }; continue; }
    const raws = mem.map((p) => values.get(p.code)), ps = raws.map((v) => pct(pop, dir * v));
    out[k] = { raw: raws.reduce((a, b) => a + b, 0) / raws.length, pct: pop.length < MIN_PEERS ? null : ps.reduce((a, b) => a + b, 0) / ps.length, n: mem.length }; }
  return out;
}
function subjectFor(p, spec) {
  if (spec.code) return { code: spec.code, cik: p.records[spec.code].cik, r: p.records[spec.code] };
  const t = p.target[spec.targetId];
  if (t && t.state === 'NOT_AVAILABLE' && t.cik) { const alt = Object.keys(p.records).filter((c) => p.records[c].cik === t.cik && scored(p.records[c], p)).sort()[0]; if (alt) return { code: alt, cik: t.cik, r: p.records[alt] }; }
  return { code: null, cik: t.cik, r: t };
}
function expectPublic(p, spec) {
  const points = crossSection(p), subject = subjectFor(p, spec), gr = groups(subject, points), others = points.filter((x) => x.cik !== subject.cik), axes = {};
  for (const [id, a] of Object.entries(PUBLIC)) { const vals = new Map(); for (const x of others) { const v = a.get(x.r); if (v !== null) vals.set(x.code, v); }
    axes[id] = axisExpect(a.dir, vals, a.get(subject.r), gr); }
  return { subject, points, gr, axes };
}

/* ---------- synthetic device bars (made-up, deterministic; not prices of anything) ---------- */
function weekdays(n, end) { const out = []; let t = Date.parse(end + 'T00:00:00Z'); while (out.length < n) { const d = new Date(t); if (d.getUTCDay() % 6) out.unshift(d.toISOString().slice(0, 10)); t -= 864e5; } return out; }
function walk(seed, n, end) {
  let s = seed >>> 0; const rnd = () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 2 ** 32; }, out = {}; let px = 50 + (seed % 70);
  const vol = 0.008 + (seed % 7) * 0.003, drift = ((seed % 5) - 2) * 0.0004;
  for (const d of weekdays(n, end)) { px = px * (1 + drift + vol * (rnd() * 2 - 1) * 1.7); out[d] = Math.round(px * 1e4) / 1e4; }
  return out;
}
const symbolOf = (code) => code.slice(code.indexOf(':') + 1).replace(/\./g, '-');
// Independent 1-year metrics: last 253 closes, sample std of simple returns × √252, running-peak drawdown, C[-22]/C[-253]-1.
function metrics(closes) {
  const c = Object.keys(closes).sort().map((d) => closes[d]).slice(-253); if (c.length < 253) return null;
  const r = []; for (let i = 1; i < c.length; i++) r.push(c[i] / c[i - 1] - 1);
  const m = r.reduce((a, b) => a + b, 0) / r.length, sd = Math.sqrt(r.reduce((a, x) => a + (x - m) ** 2, 0) / (r.length - 1));
  let peak = -Infinity, mdd = 0; for (const x of c) { peak = Math.max(peak, x); mdd = Math.min(mdd, x / peak - 1); }
  return { volatility_1y: sd * Math.sqrt(252), max_drawdown_1y: mdd, momentum_12_1: c[c.length - 22] / c[c.length - 253] - 1 };
}
const DEVICE = { volatility_1y: 1, max_drawdown_1y: -1, momentum_12_1: 1 };

/* ---------- page checks ---------- */
async function radar(page, want = null) {
  const el = page.locator('[data-stat-radar]').first(); await el.waitFor();
  await page.waitForFunction((w) => { const r = document.querySelector('[data-stat-radar]'); return r && (w ? r.dataset.srDevice === w : r.dataset.srDevice !== 'PENDING' && r.dataset.srDevice !== 'LOADING'); }, want);
  return el;
}
async function cellOf(el, axis, series) { const c = el.locator('tr[data-sr-axis="' + axis + '"] td[data-sr-series="' + series + '"]');
  const g = async (k) => c.getAttribute(k); return { raw: await g('data-sr-raw'), pct: await g('data-sr-pct'), reason: await g('data-sr-reason'), n: await g('data-sr-n') }; }
function same(shown, want, label) {
  if (want === null || want === undefined) { assert.equal(shown, 'NA', label + ' should be NA, got ' + shown); return; }
  assert.ok(shown !== 'NA' && close(Number(shown), want), label + ' ' + shown + ' vs ' + want);
}
async function checkPublic(el, exp, label) {
  assert.equal(await el.getAttribute('data-sr-industry-basis'), exp.gr.industry.basis, label + ' industry basis');
  assert.equal(await el.getAttribute('data-sr-industry-key'), exp.gr.industry.key, label + ' industry key');
  assert.equal(await el.getAttribute('data-sr-sic-basis'), exp.gr.sic.basis, label + ' sic basis');
  assert.equal(await el.getAttribute('data-sr-sic-key'), exp.gr.sic.key, label + ' sic key');
  let checks = 0;
  for (const [id, a] of Object.entries(exp.axes)) {
    assert.equal(Number(await el.locator('tr[data-sr-axis="' + id + '"]').getAttribute('data-sr-population')), a.population, label + ' ' + id + ' population');
    const c = await cellOf(el, id, 'company'); same(c.raw, a.company.raw, label + ' ' + id + ' raw'); same(c.pct, a.company.pct, label + ' ' + id + ' pct'); checks += 2;
    for (const k of ['industry', 'sic']) { const x = await cellOf(el, id, k); assert.equal(Number(x.n), a[k].n, label + ' ' + id + ' ' + k + ' n');
      same(x.raw, a[k].raw, label + ' ' + id + ' ' + k + ' raw'); same(x.pct, a[k].pct, label + ' ' + id + ' ' + k + ' pct'); if (a[k].raw === null) assert.equal(x.reason, 'GROUP_TOO_SMALL'); checks += 3; }
  }
  return checks;
}
async function checkCommon(page, el, label) {
  for (const axis of ['revenue_size', 'margin_stability', 'volatility_1y', 'max_drawdown_1y', 'liquidity', 'momentum_12_1']) {
    const c = await cellOf(el, axis, 'competitor'); assert.equal(c.raw, 'NA'); assert.equal(c.pct, 'NA'); assert.equal(c.reason, 'REL_SOURCE_PENDING', label + ' competitor ' + axis); }
  assert.equal(await el.locator('[data-sr-legend="competitor"]').getAttribute('data-sr-legend-state'), 'NOT_AVAILABLE');
  assert.match(await el.locator('[data-sr-legend="competitor"]').textContent(), /REL-SOURCE/);
  // A vertex only where the company has a percentile (an NA axis is never drawn at 0); the polygon is filled only when complete.
  const pcts = await el.locator('td[data-sr-series="company"]').evaluateAll((ns) => ns.map((n) => n.dataset.srPct));
  assert.equal(await el.locator('.sr-mark[data-sr-series="company"]').count(), pcts.filter((v) => v !== 'NA').length, label + ' company vertices');
  assert.equal(await el.locator('[data-sr-shape="company"].sr-fill').count(), pcts.every((v) => v !== 'NA') ? 1 : 0, label + ' fill only when complete');
  const aria = await el.locator('svg[data-sr-svg]').getAttribute('aria-label'); assert.ok(aria.includes('매출 규모') && aria.includes('면적은 점수가 아님'), label + ' aria-label');
  assert.equal(await el.locator('table caption').count(), 1);
  for (const s of ['company', 'industry', 'sic', 'competitor']) assert.equal(await el.locator('[data-sr-legend="' + s + '"] b').count(), 1, label + ' legend text ' + s);
  assert.equal(await page.locator('[data-stat-radar] [style], [data-stat-radar][style]').count(), 0, label + ' no inline styles');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label + ' no horizontal overflow');
}
async function checkNoDevice(el, label) {
  const state = await el.getAttribute('data-sr-device'); assert.ok(['OFF', 'NOT_AVAILABLE', 'AUTH_REQUIRED', 'SHEET_NOT_CONNECTED'].includes(state), label + ' device state ' + state);
  for (const axis of ['volatility_1y', 'max_drawdown_1y', 'liquidity', 'momentum_12_1']) for (const s of ['company', 'industry', 'sic']) {
    const c = await cellOf(el, axis, s); assert.equal(c.raw, 'NA', label + ' ' + axis + ' ' + s); assert.equal(c.pct, 'NA'); assert.equal(c.reason, 'NO_DEVICE_PRICE', label + ' ' + axis + ' ' + s + ' reason'); }
  assert.equal(await el.locator('.sr-mark[data-sr-axis="volatility_1y"]').count(), 0, label + ' no vertex for an NA price axis');
}
async function shot(el, name) { if (!SHOTS) return; fs.mkdirSync(SHOTS, { recursive: true }); await el.screenshot({ path: path.join(SHOTS, name + '.png') }); }

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH }); let pass = 0;
  try {
    const live = await served(), mode = live ? 'REAL' : 'SYNTHETIC', p = live || F.strictPayload(); SQ.validate(p);
    const points = crossSection(p);
    const uni = points.find((x) => x.r.profile === 'GENERAL' && x.r.industry_group && x.r.sic && revenue(x.r) !== null && marginStd(x.r) !== null && groups({ cik: x.cik, r: x.r }, points).industry.basis === 'INDUSTRY_GROUP') || points.find((x) => x.r.profile === 'GENERAL' && x.r.sic);
    const fin = points.find((x) => x.r.profile === 'FINANCIAL' && x.r.sic);
    const targetId = Object.keys(p.target || {}).sort().find((id) => scored(p.target[id], p) && typeof p.target[id].sic === 'string') || null;
    const treeCode = Object.keys(p.records).filter((c) => !c.startsWith('TARGET:')).sort().find((c) => points.some((x) => x.code === c) && p.records[c].state === 'LIVE' && Number.isFinite(p.records[c].axes.Q.score) && Number.isFinite(p.records[c].axes.G.score));
    const cases = [['UNIVERSE', { code: uni && uni.code }], ['FINANCIAL', { code: fin && fin.code }], ['TARGET', { targetId }]].filter(([k, s]) => { const ok = s.code || s.targetId; if (!ok) console.log('CASE_ABSENT ' + k + ' mode=' + mode); return ok; });
    console.log('STAT_RADAR mode=' + mode + ' as_of=' + p.as_of + ' cross_section=' + points.length + ' cases=' + cases.map(([k, s]) => k + ':' + (s.code || s.targetId)).join(',') + ' tree=' + treeCode);
    const today = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' }), page = await context.newPage(); page.setDefaultTimeout(20000);
      const errors = []; page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      if (!live) await page.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(p) }));
      // 1) public axes, groups, no device prices, competitor NA on every mount point
      for (const [kind, spec] of cases) {
        phase = width + ' ' + kind; await page.goto(BASE + '#company/' + encodeURIComponent(spec.code || spec.targetId));
        const el = await radar(page), exp = expectPublic(p, spec);
        assert.equal(await el.getAttribute('data-stat-radar'), spec.code ? 'code:' + spec.code : 'target:' + spec.targetId);
        pass += await checkPublic(el, exp, phase); await checkNoDevice(el, phase); await checkCommon(page, el, phase); pass += 3;
        await shot(el, 'radar-' + kind.toLowerCase() + '-' + width + '-light-nodevice');
      }
      if (treeCode) {
        phase = width + ' TREE'; await page.goto(BASE + '#tree/qgv'); const el = await radar(page);
        assert.equal(await el.getAttribute('data-sr-subject'), treeCode, 'tree radar uses the tree example row');
        assert.equal(await page.locator('[data-tree-examples="qgv"] [data-example-code]').getAttribute('data-example-code'), treeCode);
        assert.match(await page.locator('[data-tree-radar-node]').textContent(), /PROVISIONAL/);
        pass += await checkPublic(el, expectPublic(p, { code: treeCode }), phase); await checkNoDevice(el, phase); await checkCommon(page, el, phase); pass += 3;
        await shot(el, 'radar-tree-' + width + '-light-nodevice');
      }
      // 2) synthetic device bars in RAM: the subject, 7 same-industry peers, 3 other issuers, 1 industry peer with only 100 bars.
      if (uni) {
        phase = width + ' DEVICE'; const exp = expectPublic(p, { code: uni.code }), ind = exp.gr.industry.m, others = points.filter((x) => x.cik !== uni.cik && !ind.includes(x));
        const chosen = [uni, ...ind.slice(0, 7), ...others.slice(0, 3)], short = ind[7], bars = {};
        chosen.forEach((x, i) => { bars[symbolOf(x.code)] = walk(1000 + i * 37, 300, today); }); if (short) bars[symbolOf(short.code)] = walk(77, 100, today);
        await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await radar(page);
        const before = await page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]));
        await page.evaluate((b) => { const real = window.PriceStore; window.PriceStore = { ...real, status: () => ({ state: 'READY' }), subscribe: () => () => {}, dailyCloses: async (s) => (Object.hasOwn(b, s) ? { ...b[s] } : {}) }; }, bars);
        await page.goto(BASE + '#home'); await page.goto(BASE + '#company/' + encodeURIComponent(uni.code));
        const el = await radar(page, 'READY');
        const vals = {}; for (const x of chosen) vals[x.code] = metrics(bars[symbolOf(x.code)]);
        for (const [axis, dir] of Object.entries(DEVICE)) {
          const others2 = new Map(chosen.filter((x) => x !== uni).map((x) => [x.code, vals[x.code][axis]])), e = axisExpect(dir, others2, vals[uni.code][axis], exp.gr);
          const c = await cellOf(el, axis, 'company'); same(c.raw, e.company.raw, phase + ' ' + axis + ' raw'); same(c.pct, e.company.pct, phase + ' ' + axis + ' pct');
          assert.equal(Number(await el.locator('tr[data-sr-axis="' + axis + '"]').getAttribute('data-sr-population')), 11, 'population excludes the short history');
          for (const k of ['industry', 'sic']) { const x = await cellOf(el, axis, k); assert.equal(Number(x.n), e[k].n, phase + ' ' + axis + ' ' + k + ' n'); same(x.raw, e[k].raw, phase + ' ' + axis + ' ' + k); same(x.pct, e[k].pct, phase + ' ' + axis + ' ' + k + ' pct'); }
          pass += 6;
        }
        const liq = await cellOf(el, 'liquidity', 'company'); assert.equal(liq.raw, 'NA'); assert.equal(liq.reason, 'VOLUME_NOT_IN_PRICE_STORE');
        assert.equal(await el.locator('.sr-mark[data-sr-series="company"][data-sr-axis="volatility_1y"]').count(), 1, 'priced axis gets a vertex');
        await checkCommon(page, el, phase);
        await shot(el, 'radar-universe-' + width + '-light-synthetic-device');
        // Pure function with volume (synthetic): median of close × volume over the last 252 sessions.
        const synth = walk(4242, 260, today), days = Object.keys(synth).sort(), withVol = days.map((d, i) => ({ date: d, close: synth[d], volume: 1000 + ((i * 7919) % 5000) }));
        const got = await page.evaluate((b) => StatRadar.priceMetrics(b).liquidity.value, withVol);
        const tv = withVol.slice(-252).map((b) => b.close * b.volume).sort((a, b) => a - b), med = (tv[125] + tv[126]) / 2; assert.ok(close(got, med), 'median trading value'); pass++;
        const after = await page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]));
        assert.equal(after, before, 'the radar writes nothing to browser storage');
        const leaked = await page.evaluate((v) => [JSON.stringify(localStorage), JSON.stringify(sessionStorage)].some((s) => s.includes(String(v))), Object.values(bars[symbolOf(uni.code)])[10]);
        assert.equal(leaked, false, 'no synthetic close in storage'); pass++;
        if (SHOTS) for (const scheme of ['dark']) {
          const dctx = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', colorScheme: scheme }), dp = await dctx.newPage(); dp.setDefaultTimeout(20000);
          await dp.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
          if (!live) await dp.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(p) }));
          await dp.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await shot(await radar(dp), 'radar-universe-' + width + '-dark-nodevice');
          await dp.evaluate((b) => { const real = window.PriceStore; window.PriceStore = { ...real, status: () => ({ state: 'READY' }), subscribe: () => () => {}, dailyCloses: async (s) => (Object.hasOwn(b, s) ? { ...b[s] } : {}) }; }, bars);
          await dp.goto(BASE + '#home'); await dp.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await shot(await radar(dp, 'READY'), 'radar-universe-' + width + '-dark-synthetic-device');
          await dctx.close();
        }
      }
      assert.deepEqual(errors, []); await context.close();
    }
    console.log('STAT_RADAR_BROWSER_OK checks=' + pass);
  } catch (e) { console.error('STAT_RADAR_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
