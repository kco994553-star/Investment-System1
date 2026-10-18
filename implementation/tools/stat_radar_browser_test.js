'use strict';
// Stat window radar (stat-radar.js, owner item 1.4; owner decision 2026-10-18: Q · G · V + 가격 안정성 · 낙폭 방어력 · 상대 강도,
// outer = better on every axis, 이익률 안정성 as an optional auxiliary axis) at 390 and 1280 on its three mount points: the
// Universe504 company page, the TARGET company summary and the 1.4 QGV tree example. REAL mode reads the sec-qgv2.json the build
// serves; SYNTHETIC mode (PR builds publish no data file) serves the strictly valid synthetic payload (qgv_v2_fixture.js).
// Everything below is recomputed here independently of the page code:
//  - Q and G equal the published axis scores; group values are the mean published score of the members (same 0–100 scale);
//  - the auxiliary margin-stability row: raw value, average-rank percentile of −std and the group means of member percentiles;
//  - V is 미산출 without device prices (해당 없음 for FINANCIAL); price axes are 미산출 (NO_DEVICE_PRICE) without device bars;
//    a 미산출 axis has no vertex and the polygon is not filled;
//  - with SYNTHETIC device bars (made-up random walks incl. a synthetic SPY, never real prices, never committed as data): the
//    252-SPY-session window, volatility / max drawdown / 6-month excess return vs SPY raw values and their percentiles (outer =
//    lower volatility, shallower drawdown, larger excess return), the industry / SIC means, the gap rule and the 90 % minimums;
//    an unadjusted 2:1 split gives CORPORATE_ACTION_UNADJUSTED, an adjusted company vs raw SPY gives BASIS_MISMATCH;
//  - identical industry and SIC member sets are drawn once ("업종 = SIC"); the area is never computed; official QGV rows are
//    unchanged; competitors are 미산출 (REL_SOURCE_PENDING); no inline styles; no horizontal overflow; nothing written to storage.
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const F = require('./qgv_v2_fixture.js'), SQ = require('../src/investment_system/product/web_assets/sec-qgv2.js');
const BASE = process.env.PAGES_COCKPIT_URL, ORIGIN = new URL(BASE).origin, SHOTS = process.env.STAT_RADAR_SHOTS || '';
const close = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
const WITHDRAWN = 'IDENTITY_CONFLICT_WITHDRAWN', MIN_PEERS = 8, MIN_GROUP = 5;
const AXES = ['q', 'g', 'v', 'price_stability', 'drawdown_defense', 'relative_strength'], PRICE = { price_stability: -1, drawdown_defense: 1, relative_strength: 1 };
let phase = 'START';
async function served() { try { const r = await fetch(new URL('sec-qgv2.json', BASE)); if (r.status !== 200) return null; return JSON.parse(await r.text()); } catch (_) { return null; } }

/* ---------- independent public model ---------- */
const withdrawnRow = (r) => !!r && (Object.hasOwn(r, 'detected_at') || (Array.isArray(r.reason_codes) && r.reason_codes.includes(WITHDRAWN)));
const scored = (r, p) => !!r && ['LIVE', 'STALE'].includes(r.state) && !withdrawnRow(r) && (typeof p.calc_version !== 'string' || r.calc_version === p.calc_version);
function crossSection(p) {
  const bad = new Set(Object.values(p.target || {}).filter(withdrawnRow).map((r) => r.cik)), seen = new Set(), out = [];
  for (const code of Object.keys(p.records).sort()) { const r = p.records[code];
    if (!scored(r, p) || typeof r.cik !== 'string' || bad.has(r.cik) || seen.has(r.cik)) continue; seen.add(r.cik); out.push({ code, cik: r.cik, r }); }
  return out;
}
const axisScore = (axis) => (r) => (r.axes && r.axes[axis] && Number.isFinite(r.axes[axis].score) ? r.axes[axis].score : null);
const marginStd = (r) => (r.metrics && Number.isFinite(r.metrics.operating_margin_std_5y_pp) ? r.metrics.operating_margin_std_5y_pp : null);
// QGV average-rank percentile by direct counting (no shared code with the page).
function pct(values, x) { const n = values.length; if (n < MIN_PEERS) return null; let less = 0, eq = 0; for (const v of values) { if (v < x) less++; else if (v === x) eq++; } return 100 * (less + (eq - 1) / 2) / (n - 1); }
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
function groups(subject, points) {
  const r = subject.r, others = points.filter((p) => p.cik !== subject.cik);
  let ind;
  if (r.profile === 'FINANCIAL') ind = { basis: 'FINANCIAL_PROFILE', key: 'FINANCIAL', m: others.filter((p) => p.r.profile === 'FINANCIAL') };
  else { const gen = others.filter((p) => p.r.profile !== 'FINANCIAL'), m = r.industry_group ? gen.filter((p) => p.r.industry_group === r.industry_group) : [];
    ind = r.industry_group && m.length + 1 >= MIN_PEERS ? { basis: 'INDUSTRY_GROUP', key: r.industry_group, m } : { basis: 'UNIVERSE_FALLBACK', key: 'GENERAL', m: gen }; }
  const withSic = others.filter((p) => typeof p.r.sic === 'string'), m4 = withSic.filter((p) => p.r.sic === r.sic);
  const sic = m4.length + 1 >= MIN_PEERS ? { basis: 'SIC4', key: r.sic, m: m4 } : { basis: 'SIC2', key: r.sic.slice(0, 2), m: withSic.filter((p) => p.r.sic.slice(0, 2) === r.sic.slice(0, 2)) };
  const same = ind.m.length === sic.m.length && ind.m.every((p, i) => p.code === sic.m[i].code);
  return { industry: ind, sic, same };
}
/* Published 0–100 scores (Q, G): drawn as published; a group value is the mean member score. */
function scoreExpect(values, own, gr) {
  const out = { population: values.size + (own === null ? 0 : 1), company: { raw: own, score: own } };
  for (const k of ['industry', 'sic']) { const xs = gr[k].m.filter((p) => values.has(p.code)).map((p) => values.get(p.code));
    out[k] = xs.length < MIN_GROUP ? { score: null, n: xs.length } : { score: mean(xs), n: xs.length }; }
  return out;
}
/* Percentile axes: values Map code -> raw (others), own raw or null, dir +1/−1; group value = mean of member percentiles. */
function rankExpect(dir, values, own, gr) {
  const pop = [...values.values(), ...(own === null ? [] : [own])].map((v) => dir * v), out = { population: pop.length };
  out.company = { raw: own, score: own === null ? null : pct(pop, dir * own) };
  for (const k of ['industry', 'sic']) { const mem = gr[k].m.filter((p) => values.has(p.code)), ss = mem.map((p) => pct(pop, dir * values.get(p.code))).filter((s) => s !== null);
    out[k] = ss.length < MIN_GROUP ? { score: null, n: ss.length } : { score: mean(ss), n: ss.length }; }
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
  const collect = (get) => { const m = new Map(); for (const x of others) { const v = get(x.r); if (v !== null) m.set(x.code, v); } return m; };
  axes.q = scoreExpect(collect(axisScore('Q')), axisScore('Q')(subject.r), gr);
  axes.g = scoreExpect(collect(axisScore('G')), axisScore('G')(subject.r), gr);
  axes.margin_stability = rankExpect(-1, collect(marginStd), marginStd(subject.r), gr);
  return { subject, points, gr, axes };
}

/* ---------- synthetic device bars (made-up, deterministic; not prices of anything) ---------- */
function weekdays(n, end) { const out = []; let t = Date.parse(end + 'T00:00:00Z'); while (out.length < n) { const d = new Date(t); if (d.getUTCDay() % 6) out.unshift(d.toISOString().slice(0, 10)); t -= 864e5; } return out; }
function walk(seed, n, end) {
  let s = seed >>> 0; const rnd = () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 2 ** 32; }, out = {}; let px = 50 + (seed % 70);
  const vol = 0.006 + (seed % 7) * 0.002, drift = ((seed % 5) - 2) * 0.0004;
  for (const d of weekdays(n, end)) { px = px * (1 + drift + vol * (rnd() * 2 - 1) * 1.7); out[d] = Math.round(px * 1e4) / 1e4; }
  return out;
}
const symbolOf = (code) => code.slice(code.indexOf(':') + 1).replace(/\./g, '-');
// Independent window metrics on the SPY calendar: a missing close is a gap (no return across it), never filled.
function metrics(closes, spy, cal) {
  const pts = cal.map((d) => (Object.hasOwn(closes, d) ? closes[d] : null)), sp = cal.map((d) => spy[d]), present = pts.filter((x) => x !== null).length, out = {};
  // Raw closes: a split-like close-to-close ratio (±3 % of 2, 3, 4, 5, 10 or their inverses, 3/2, 2/3) -> not measured.
  const ratios = [2, 3, 4, 5, 10, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 3 / 2, 2 / 3], seq = pts.filter((x) => x !== null);
  if (seq.some((x, i) => i > 0 && ratios.some((q) => Math.abs(x / seq[i - 1] / q - 1) <= 0.03))) return { price_stability: null, drawdown_defense: null, relative_strength: null };
  if (present >= 227) {
    const r = []; for (let i = 1; i < pts.length; i++) if (pts[i] !== null && pts[i - 1] !== null) r.push(pts[i] / pts[i - 1] - 1);
    const m = mean(r); out.price_stability = Math.sqrt(r.reduce((a, x) => a + (x - m) ** 2, 0) / (r.length - 1)) * Math.sqrt(252);
    let peak = -Infinity, mdd = 0; for (const x of pts) { if (x === null) continue; peak = Math.max(peak, x); mdd = Math.min(mdd, x / peak - 1); } out.drawdown_defense = mdd;
  } else { out.price_stability = null; out.drawdown_defense = null; }
  const t = pts.length - 1, b = t - 126, recent = pts.slice(t - 125).filter((x) => x !== null).length;
  out.relative_strength = pts[t] !== null && pts[b] !== null && recent >= 113 ? (pts[t] / pts[b] - 1) - (sp[t] / sp[b] - 1) : null;
  return out;
}

/* ---------- page checks ---------- */
async function radar(page, want = null) {
  const el = page.locator('[data-stat-radar]').first(); await el.waitFor();
  await page.waitForFunction((w) => { const r = document.querySelector('[data-stat-radar]'); return r && (w ? r.dataset.srDevice === w : r.dataset.srDevice !== 'PENDING' && r.dataset.srDevice !== 'LOADING'); }, want);
  return el;
}
async function cellOf(el, axis, series) { const c = el.locator('tr[data-sr-axis="' + axis + '"] td[data-sr-series="' + series + '"]');
  if (!(await c.count())) return null; const g = async (k) => c.getAttribute(k); return { raw: await g('data-sr-raw'), score: await g('data-sr-score'), reason: await g('data-sr-reason'), n: await g('data-sr-n'), text: await c.textContent() }; }
function same(shown, want, label) {
  if (want === null || want === undefined) { assert.equal(shown, 'NA', label + ' should be 미산출, got ' + shown); return; }
  assert.ok(shown !== 'NA' && close(Number(shown), want), label + ' ' + shown + ' vs ' + want);
}
async function checkAxis(el, id, a, gr, label) {
  assert.equal(Number(await el.locator('tr[data-sr-axis="' + id + '"]').getAttribute('data-sr-population')), a.population, label + ' ' + id + ' population');
  const c = await cellOf(el, id, 'company'); same(c.raw, a.company.raw, label + ' ' + id + ' raw'); same(c.score, a.company.score, label + ' ' + id + ' score');
  for (const k of gr.same ? ['industry'] : ['industry', 'sic']) { const x = await cellOf(el, id, k); assert.equal(Number(x.n), a[k].n, label + ' ' + id + ' ' + k + ' n');
    same(x.score, a[k].score, label + ' ' + id + ' ' + k + ' score'); if (a[k].score === null) assert.match(x.reason, /GROUP_TOO_SMALL|PEERS_TOO_FEW/); }
  if (gr.same) assert.equal(await cellOf(el, id, 'sic'), null, label + ' identical groups shown once');
  return 4;
}
async function checkPublic(el, exp, label) {
  assert.equal(await el.getAttribute('data-sr-industry-basis'), exp.gr.industry.basis, label + ' industry basis');
  assert.equal(await el.getAttribute('data-sr-industry-key'), exp.gr.industry.key, label + ' industry key');
  assert.equal(await el.getAttribute('data-sr-sic-basis'), exp.gr.sic.basis, label + ' sic basis');
  assert.equal(await el.getAttribute('data-sr-groups'), exp.gr.same ? 'SAME' : 'DISTINCT', label + ' identical-group rule');
  let checks = 0; for (const [id, a] of Object.entries(exp.axes)) checks += await checkAxis(el, id, a, exp.gr, label);
  // Q/G are the published axis scores exactly (no re-ranking).
  for (const [id, axis] of [['q', 'Q'], ['g', 'G']]) { const pub = axisScore(axis)(exp.subject.r), c = await cellOf(el, id, 'company'); same(c.score, pub, label + ' ' + id + ' = published'); }
  return checks + 2;
}
async function checkCommon(page, el, label) {
  for (const axis of [...AXES, 'margin_stability']) { const c = await cellOf(el, axis, 'competitor'); assert.equal(c.raw, 'NA'); assert.equal(c.score, 'NA'); assert.equal(c.reason, 'REL_SOURCE_PENDING', label + ' competitor ' + axis); assert.match(c.text, /미산출/); }
  assert.equal(await el.locator('[data-sr-legend="competitor"]').getAttribute('data-sr-legend-state'), 'NOT_AVAILABLE');
  // Default radar: 6 axes in the decided order, outer = better; the auxiliary margin row is in the detail table only.
  assert.equal(await el.locator('svg[data-sr-svg]').getAttribute('data-sr-axes'), '6', label + ' default hexagon');
  assert.deepEqual(await el.locator('[data-sr-label]').evaluateAll((ns) => ns.map((n) => n.dataset.srLabel)), AXES, label + ' axis order');
  assert.match(await el.locator('[data-sr-label="relative_strength"]').textContent(), /SPY 대비 6개월/);
  assert.match(await el.locator('tr[data-sr-axis="relative_strength"] th').textContent(), /RSI가 아님/);
  assert.equal(await el.locator('tr[data-sr-aux-row][data-sr-axis="margin_stability"]').count(), 1, label + ' margin stability kept as an auxiliary row');
  // A vertex only where the company has a score; the polygon is filled only when complete. The area is never computed.
  const scores = await el.locator('td[data-sr-series="company"]').evaluateAll((ns) => ns.filter((n) => !n.closest('[data-sr-aux-row]')).map((n) => n.dataset.srScore));
  assert.equal(await el.locator('.sr-mark[data-sr-series="company"]').count(), scores.filter((v) => v !== 'NA').length, label + ' company vertices');
  assert.equal(await el.locator('[data-sr-shape="company"].sr-fill').count(), scores.every((v) => v !== 'NA') ? 1 : 0, label + ' fill only when complete');
  for (const [i, v] of scores.entries()) if (v === 'NA') assert.match(await el.locator('[data-sr-label="' + AXES[i] + '"]').textContent(), /미산출|해당 없음/, label + ' 미산출 label ' + AXES[i]);
  assert.match(await el.textContent(), /면적은 계산하지 않습니다/); assert.equal(await el.locator('[data-sr-area]').count(), 0);
  // Detail: unit, period, as_of, basis, population on every row.
  for (const axis of [...AXES, 'margin_stability']) { const row = el.locator('tr[data-sr-axis="' + axis + '"]');
    for (const k of ['data-sr-unit', 'data-sr-period', 'data-sr-asof', 'data-sr-basis', 'data-sr-population']) assert.ok((await row.getAttribute(k)) !== null, label + ' ' + axis + ' ' + k); }
  const aria = await el.locator('svg[data-sr-svg]').getAttribute('aria-label'); assert.ok(aria.includes('Q 질') && aria.includes('낙폭 방어력') && aria.includes('면적은 점수가 아님'), label + ' aria-label');
  assert.equal(await el.locator('table caption').count(), 1);
  assert.equal(await page.locator('[data-stat-radar] [style], [data-stat-radar][style]').count(), 0, label + ' no inline styles');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label + ' no horizontal overflow');
}
async function checkNoDevice(el, label, financial) {
  const state = await el.getAttribute('data-sr-device'); assert.ok(['OFF', 'NOT_AVAILABLE', 'AUTH_REQUIRED', 'SHEET_NOT_CONNECTED'].includes(state), label + ' device state ' + state);
  assert.equal(await el.getAttribute('data-sr-quotes'), 'NONE', label + ' no device quotes');
  for (const axis of Object.keys(PRICE)) for (const s of ['company', 'industry', 'sic']) { const c = await cellOf(el, axis, s); if (!c) continue;
    assert.equal(c.raw, 'NA', label + ' ' + axis + ' ' + s); assert.equal(c.score, 'NA'); assert.equal(c.reason, 'NO_DEVICE_PRICE', label + ' ' + axis + ' ' + s + ' reason'); }
  for (const s of ['company', 'industry', 'sic']) { const c = await cellOf(el, 'v', s); if (!c) continue; assert.equal(c.score, 'NA', label + ' V ' + s);
    if (financial) { assert.equal(c.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED', label + ' V ' + s + ' financial'); assert.match(c.text, /해당 없음/); }
    else if (s === 'company') { assert.ok(c.reason && c.reason !== 'FINANCIAL_PROFILE_V_NOT_DEFINED'); assert.match(c.text, /미산출/); }
    else assert.equal(c.reason, 'NO_DEVICE_PRICE', label + ' V ' + s); }
  for (const axis of ['v', ...Object.keys(PRICE)]) assert.equal(await el.locator('.sr-mark[data-sr-axis="' + axis + '"]').count(), 0, label + ' no vertex for 미산출 ' + axis);
}
async function shot(el, name) { if (!SHOTS) return; fs.mkdirSync(SHOTS, { recursive: true }); await el.screenshot({ path: path.join(SHOTS, name + '.png') }); }
const FAKE_STORE = (b) => { const real = window.PriceStore; window.PriceStore = { ...real, status: () => ({ state: 'READY' }), subscribe: () => () => {}, dailyCloses: async (s) => (Object.hasOwn(b, s) ? { ...b[s] } : {}) }; };

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH }); let pass = 0;
  try {
    const live = await served(), mode = live ? 'REAL' : 'SYNTHETIC', p = live || F.strictPayload(); SQ.validate(p);
    const points = crossSection(p);
    const uni = points.find((x) => x.r.profile === 'GENERAL' && x.r.industry_group && x.r.sic && axisScore('Q')(x.r) !== null && axisScore('G')(x.r) !== null && marginStd(x.r) !== null && groups({ cik: x.cik, r: x.r }, points).industry.basis === 'INDUSTRY_GROUP') || points.find((x) => x.r.profile === 'GENERAL' && x.r.sic);
    const fin = points.find((x) => x.r.profile === 'FINANCIAL' && x.r.sic);
    const targetId = Object.keys(p.target || {}).sort().find((id) => scored(p.target[id], p) && typeof p.target[id].sic === 'string') || null;
    const treeCode = Object.keys(p.records).filter((c) => !c.startsWith('TARGET:')).sort().find((c) => points.some((x) => x.code === c) && p.records[c].state === 'LIVE' && Number.isFinite(p.records[c].axes.Q.score) && Number.isFinite(p.records[c].axes.G.score));
    const cases = [['UNIVERSE', { code: uni && uni.code }], ['FINANCIAL', { code: fin && fin.code }], ['TARGET', { targetId }]].filter(([k, s]) => { const ok = s.code || s.targetId; if (!ok) console.log('CASE_ABSENT ' + k + ' mode=' + mode); return ok; });
    console.log('STAT_RADAR mode=' + mode + ' as_of=' + p.as_of + ' cross_section=' + points.length + ' cases=' + cases.map(([k, s]) => k + ':' + (s.code || s.targetId)).join(',') + ' tree=' + treeCode);
    const today = new Date(Date.now() - 864e5).toISOString().slice(0, 10);
    for (const width of [390, 1280]) {
      const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' }), page = await context.newPage(); page.setDefaultTimeout(30000);
      const errors = []; page.on('pageerror', (e) => errors.push(String(e)));
      await page.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
      if (!live) await page.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(p) }));
      // 1) Q/G published, margin row, groups, no device prices, competitors on every mount point.
      for (const [kind, spec] of cases) {
        phase = width + ' ' + kind; await page.goto(BASE + '#company/' + encodeURIComponent(spec.code || spec.targetId));
        const el = await radar(page), exp = expectPublic(p, spec);
        assert.equal(await el.getAttribute('data-stat-radar'), spec.code ? 'code:' + spec.code : 'target:' + spec.targetId);
        pass += await checkPublic(el, exp, phase); await checkNoDevice(el, phase, exp.subject.r.profile === 'FINANCIAL'); await checkCommon(page, el, phase); pass += 3;
        await shot(el, 'radar-' + kind.toLowerCase() + '-' + width + '-light-nodevice');
      }
      if (treeCode) {
        phase = width + ' TREE'; await page.goto(BASE + '#tree/qgv'); const el = await radar(page);
        assert.equal(await el.getAttribute('data-sr-subject'), treeCode, 'tree radar uses the tree example row');
        assert.equal(await page.locator('[data-tree-examples="qgv"] [data-example-code]').getAttribute('data-example-code'), treeCode);
        assert.match(await page.locator('[data-tree-radar-node]').textContent(), /PROVISIONAL|결정됨/);
        const te = expectPublic(p, { code: treeCode }); pass += await checkPublic(el, te, phase); await checkNoDevice(el, phase, te.subject.r.profile === 'FINANCIAL'); await checkCommon(page, el, phase); pass += 3;
        await shot(el, 'radar-tree-' + width + '-light-nodevice');
      }
      // 2) Auxiliary axis toggle: 6 -> 7 -> 6, RAM only.
      if (uni) {
        phase = width + ' AUX'; await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); const el = await radar(page);
        await el.locator('[data-sr-aux-toggle]').click(); assert.equal(await el.locator('svg[data-sr-svg]').getAttribute('data-sr-axes'), '7'); assert.equal(await el.getAttribute('data-sr-aux'), 'ON');
        assert.equal(await el.locator('[data-sr-label="margin_stability"]').count(), 1); assert.equal(await el.locator('[data-sr-aux-toggle]').getAttribute('aria-pressed'), 'true');
        const m = expectPublic(p, { code: uni.code }).axes.margin_stability; if (m.company.score !== null) assert.equal(await el.locator('.sr-mark[data-sr-series="company"][data-sr-axis="margin_stability"]').count(), 1);
        await el.locator('[data-sr-aux-toggle]').click(); assert.equal(await el.locator('svg[data-sr-svg]').getAttribute('data-sr-axes'), '6'); pass += 3;
      }
      // 3) Synthetic device bars: SPY, the subject, 7 industry peers, 3 other issuers, one gapped peer (still >= 90 %), one peer
      //    below the 90 % minimum, one 2:1 unadjusted split and one 100-bar history.
      if (uni) {
        phase = width + ' DEVICE'; const exp = expectPublic(p, { code: uni.code }), ind = exp.gr.industry.m, others = points.filter((x) => x.cik !== uni.cik && !ind.includes(x));
        const chosen = [uni, ...ind.slice(0, 7), ...others.slice(0, 3)], bars = { SPY: walk(7, 320, today) };
        chosen.forEach((x, i) => { bars[symbolOf(x.code)] = walk(1000 + i * 37, 320, today); });
        const gapped = chosen[2], sparse = ind[7], split = ind[8], short = ind[9], cal = Object.keys(bars.SPY).sort().slice(-252);
        { const c = bars[symbolOf(gapped.code)]; for (let i = 20; i < 220; i += 10) delete c[cal[i]]; }               // 20 gaps -> 232 present
        if (sparse) { const c = walk(4321, 320, today); for (let i = 5; i < 120; i += 4) delete c[cal[i]]; bars[symbolOf(sparse.code)] = c; } // 29 gaps -> 223 present, RS window intact
        if (split) { const c = walk(999, 320, today); for (const d of cal.slice(200)) c[d] = Math.round(c[d] / 2 * 1e4) / 1e4; bars[symbolOf(split.code)] = c; }
        if (short) bars[symbolOf(short.code)] = walk(77, 100, today);
        await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await radar(page);
        const before = await page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]));
        // Official QGV rows before the radar reads device data (same accessor, same identities).
        const official = () => page.evaluate(async (codes) => { const inputs = await Qgv2Inputs.load(window); const S = QgvScores.compute({ identities: codes.map((c) => ({ company_id: c, ticker: c.slice(c.indexOf(':') + 1) })), v2Inputs: inputs });
          return JSON.stringify(codes.map((c) => { const d = S.rows[c].primary; return [d.q, d.g, d.v, d.total, S.rows[c].rank]; })); }, chosen.map((x) => x.code));
        const off0 = await official();
        await page.evaluate(FAKE_STORE, bars);
        await page.goto(BASE + '#home'); await page.goto(BASE + '#company/' + encodeURIComponent(uni.code));
        const el = await radar(page, 'READY');
        const all = [...chosen, ...[sparse, split, short].filter(Boolean)], vals = {}; for (const x of all) vals[x.code] = metrics(bars[symbolOf(x.code)], bars.SPY, cal);
        assert.equal(await el.getAttribute('data-sr-window-end'), cal[cal.length - 1], 'window ends at the latest common session');
        assert.ok((await el.locator('tr[data-sr-axis="price_stability"]').getAttribute('data-sr-period')).startsWith(cal[0] + ' ~ ' + cal[251]), 'window = last 252 SPY sessions');
        assert.ok((await el.locator('tr[data-sr-axis="relative_strength"]').getAttribute('data-sr-period')).startsWith(cal[125] + ' ~ ' + cal[251]), 'RS window = 126 sessions');
        assert.match(await el.locator('tr[data-sr-axis="price_stability"]').getAttribute('data-sr-basis'), /미수정 종가/);
        for (const [axis, dir] of Object.entries(PRICE)) {
          const m = new Map(all.filter((x) => x !== uni && vals[x.code][axis] !== null).map((x) => [x.code, vals[x.code][axis]])), e = rankExpect(dir, m, vals[uni.code][axis], exp.gr);
          pass += await checkAxis(el, axis, e, exp.gr, phase);
          // Outer = better: the best raw value in the population has the top score.
          const best = [...m.values(), vals[uni.code][axis]].sort((a, b) => dir * b - dir * a)[0]; if (best === vals[uni.code][axis]) same((await cellOf(el, axis, 'company')).score, 100, phase + ' ' + axis + ' best is outermost');
        }
        // Minimum observations and the split: excluded members are named by their raw-value absence in the population counts.
        assert.equal(vals[gapped.code].price_stability !== null, true, 'gapped peer (>= 90 %) is measured');
        if (sparse) assert.equal(vals[sparse.code].price_stability, null, 'sparse peer (< 90 %) is excluded');
        assert.equal(await el.locator('.sr-mark[data-sr-series="company"][data-sr-axis="price_stability"]').count(), 1, 'priced axis gets a vertex');
        await checkCommon(page, el, phase);
        await shot(el, 'radar-universe-' + width + '-light-synthetic-device');
        // Pure rules in the page: split, basis mismatch, adjusted basis, 90 % minimums, endpoints.
        const rules = await page.evaluate(({ spy, base, splitDay }) => {
          const S = StatRadar, rs = (o) => Object.fromEntries(Object.entries(o.axes).map(([k, v]) => [k, v.reason]));
          const cut = (c, n) => { const d = Object.keys(c).sort(), out = { ...c }; for (const x of d.slice(-252, -252 + n)) delete out[x]; return out; };
          const halved = { ...base }; for (const d of Object.keys(base).sort().filter((d) => d >= splitDay)) halved[d] = base[d] / 2;
          const keepRecent = (c, n) => { const d = Object.keys(c).sort().slice(-126), out = { ...c }; for (const x of d.slice(1, 1 + n)) delete out[x]; return out; };
          const noStart = { ...base }; delete noStart[Object.keys(spy).sort().slice(-127)[0]];
          return { split: rs(S.priceAxes({ basis: 'RAW', closes: halved }, { basis: 'RAW', closes: spy })), splitAdjusted: rs(S.priceAxes({ basis: 'ADJUSTED', closes: halved }, { basis: 'ADJUSTED', closes: spy })),
            mismatch: rs(S.priceAxes({ basis: 'ADJUSTED', closes: base }, { basis: 'RAW', closes: spy })), min227: rs(S.priceAxes({ basis: 'RAW', closes: cut(base, 25) }, { basis: 'RAW', closes: spy })),
            min226: rs(S.priceAxes({ basis: 'RAW', closes: cut(base, 26) }, { basis: 'RAW', closes: spy })), rs113: rs(S.priceAxes({ basis: 'RAW', closes: keepRecent(base, 13) }, { basis: 'RAW', closes: spy })),
            rs112: rs(S.priceAxes({ basis: 'RAW', closes: keepRecent(base, 14) }, { basis: 'RAW', closes: spy })), endpoint: rs(S.priceAxes({ basis: 'RAW', closes: noStart }, { basis: 'RAW', closes: spy })),
            noSpy: rs(S.priceAxes({ basis: 'RAW', closes: base }, { basis: 'RAW', closes: {} })), hasArea: Object.keys(S).some((k) => /area/i.test(k)) };
        }, { spy: bars.SPY, base: bars[symbolOf(uni.code)], splitDay: cal[200] });
        assert.deepEqual(rules.split, { price_stability: 'CORPORATE_ACTION_UNADJUSTED', drawdown_defense: 'CORPORATE_ACTION_UNADJUSTED', relative_strength: 'CORPORATE_ACTION_UNADJUSTED' });
        assert.deepEqual(rules.splitAdjusted, { price_stability: null, drawdown_defense: null, relative_strength: null }, 'adjusted basis is not split-checked');
        assert.deepEqual(rules.mismatch, { price_stability: 'BASIS_MISMATCH', drawdown_defense: 'BASIS_MISMATCH', relative_strength: 'BASIS_MISMATCH' });
        assert.equal(rules.min227.price_stability, null); assert.equal(rules.min226.price_stability, 'INSUFFICIENT_SAMPLE'); assert.equal(rules.min226.drawdown_defense, 'INSUFFICIENT_SAMPLE');
        assert.equal(rules.rs113.relative_strength, null); assert.equal(rules.rs112.relative_strength, 'INSUFFICIENT_SAMPLE'); assert.equal(rules.endpoint.relative_strength, 'ENDPOINT_MISSING');
        assert.equal(rules.noSpy.price_stability, 'SPY_NOT_AVAILABLE'); assert.equal(rules.hasArea, false, 'no area function'); pass += 10;
        if (split) { const v = await page.evaluate(({ c, s }) => StatRadar.priceAxes({ basis: 'RAW', closes: c }, { basis: 'RAW', closes: s }).axes.price_stability.reason, { c: bars[symbolOf(split.code)], s: bars.SPY }); assert.equal(v, 'CORPORATE_ACTION_UNADJUSTED', 'split peer'); }
        // Identical industry / SIC member sets are drawn once ("업종 = SIC"): synthetic normalized rows, same SIC and group.
        const once = await page.evaluate(() => { const rec = (i) => ({ state: 'LIVE', in_cross_section: true, cik: String(9000000 + i), profile: 'GENERAL', industry_group: 'manufacturing_industrial_tech', sic: '3674', qg_axes: { Q: { score: 40 + i }, G: { score: 30 + i } }, metrics: { operating_margin_std_5y_pp: 1 + i / 10 }, factors: {}, na_reasons: [] });
          const records = {}; for (let i = 0; i < 9; i++) records['NYSE:SYNT' + i] = rec(i); const box = document.createElement('div'); box.innerHTML = StatRadar.html({ code: 'NYSE:SYNT0' }, { screens: { 'sec-qgv2.json': { as_of: null, records } } });
          const el = box.firstElementChild; return { groups: el.dataset.srGroups, sic: el.querySelectorAll('[data-sr-legend="sic"], td[data-sr-series="sic"], .sr-series-sic').length, label: el.querySelector('[data-sr-legend="industry"]').textContent, q: el.querySelector('tr[data-sr-axis="q"] td[data-sr-series="industry"]').dataset.srScore }; });
        assert.equal(once.groups, 'SAME'); assert.equal(once.sic, 0); assert.match(once.label, /업종 = SIC/); assert.ok(close(Number(once.q), 44.5), 'same 0–100 scale: mean member Q (41…48)'); pass += 4;
        assert.equal(await official(), off0, 'official QGV rows unchanged by the radar'); pass++;
        const after = await page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]));
        assert.equal(after, before, 'the radar writes nothing to browser storage');
        const leaked = await page.evaluate((v) => [JSON.stringify(localStorage), JSON.stringify(sessionStorage)].some((s) => s.includes(String(v))), Object.values(bars[symbolOf(uni.code)])[10]);
        assert.equal(leaked, false, 'no synthetic close in storage'); pass++;
        if (SHOTS) {
          const dctx = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block', colorScheme: 'dark' }), dp = await dctx.newPage(); dp.setDefaultTimeout(30000);
          await dp.route('**/*', (r) => (new URL(r.request().url()).origin === ORIGIN ? r.fallback() : r.abort()));
          if (!live) await dp.route('**/sec-qgv2.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(p) }));
          await dp.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await shot(await radar(dp), 'radar-universe-' + width + '-dark-nodevice');
          await dp.evaluate(FAKE_STORE, bars); await dp.goto(BASE + '#home'); await dp.goto(BASE + '#company/' + encodeURIComponent(uni.code));
          const d = await radar(dp, 'READY'); await shot(d, 'radar-universe-' + width + '-dark-synthetic-device');
          await d.locator('[data-sr-aux-toggle]').click(); await shot(d, 'radar-universe-' + width + '-dark-synthetic-device-aux7');
          await dctx.close();
        }
      }
      assert.deepEqual(errors, []); await context.close();
    }
    console.log('STAT_RADAR_BROWSER_OK checks=' + pass);
  } catch (e) { console.error('STAT_RADAR_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
