'use strict';
// Stat window radar (stat-radar.js, owner item 1.4; owner decision 2026-10-18: Q · G · V + 가격 안정성 · 낙폭 방어력 · 상대 강도,
// outer = better on every axis, 이익률 안정성 as an optional auxiliary axis) at 390 and 1280 on its three mount points: the
// Universe504 company page, the TARGET company summary and the 1.4 QGV tree example. REAL mode reads the sec-qgv2.json the build
// serves; SYNTHETIC mode (PR builds publish no data file) serves the strictly valid synthetic payload (qgv_v2_fixture.js).
// Everything below is recomputed here independently of the page code:
//  - Q and G equal the published axis scores; group values are the mean published score of the members (same 0–100 scale);
//  - the auxiliary margin-stability row: raw value, average-rank percentile of −std and the group means of member percentiles;
//  - V is 미산출 with the engine reason without quotes; FINANCIAL shows exactly '현재 금융업 가치평가 모델 미지원' (a model scope, not
//    a data failure) and no general V formula; the V detail lists each value input (raw, period, source) or its reason;
//    price axes are 미산출 (NO_DEVICE_PRICE) without price data, ADJUSTMENT_BASIS_UNCONFIRMED on raw closes;
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
// Independent window metrics on the SPY calendar (confirmed adjusted basis): a missing close is a gap; a daily return needs both
// adjacent sessions; volatility needs >= 227 closes and >= 226 valid returns, drawdown >= 227 closes, RS both endpoints + 113/126.
function metrics(closes, spy, cal) {
  const pts = cal.map((d) => (Object.hasOwn(closes, d) ? closes[d] : null)), sp = cal.map((d) => spy[d]), present = pts.filter((x) => x !== null).length, out = {};
  const r = []; for (let i = 1; i < pts.length; i++) if (pts[i] !== null && pts[i - 1] !== null) r.push(pts[i] / pts[i - 1] - 1);
  if (present >= 227 && r.length >= 226) { const m = mean(r); out.price_stability = Math.sqrt(r.reduce((a, x) => a + (x - m) ** 2, 0) / (r.length - 1)) * Math.sqrt(252); } else out.price_stability = null;
  if (present >= 227) { let peak = -Infinity, mdd = 0; for (const x of pts) { if (x === null) continue; peak = Math.max(peak, x); mdd = Math.min(mdd, x / peak - 1); } out.drawdown_defense = mdd; } else out.drawdown_defense = null;
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
  for (const [i, v] of scores.entries()) if (v === 'NA') assert.match(await el.locator('[data-sr-label="' + AXES[i] + '"]').textContent(), /미산출|모델 미지원/, label + ' 미산출 label ' + AXES[i]);
  assert.match(await el.textContent(), /면적은 계산하지 않습니다/); assert.equal(await el.locator('[data-sr-area]').count(), 0);
  // Detail: unit, period, as_of, basis, population on every row.
  for (const axis of [...AXES, 'margin_stability']) { const row = el.locator('tr[data-sr-axis="' + axis + '"]');
    for (const k of ['data-sr-unit', 'data-sr-period', 'data-sr-asof', 'data-sr-basis', 'data-sr-population']) assert.ok((await row.getAttribute(k)) !== null, label + ' ' + axis + ' ' + k); }
  const aria = await el.locator('svg[data-sr-svg]').getAttribute('aria-label'); assert.ok(aria.includes('Q 질') && aria.includes('낙폭 방어력') && aria.includes('면적은 점수가 아님'), label + ' aria-label');
  assert.equal(await el.locator('table caption').count(), 1);
  assert.equal(await el.getAttribute('data-sr-decision'), 'CANDIDATE'); assert.match(await el.locator('[data-sr-axis-set]').textContent(), /후보 축\(커버리지 확인 전\)/);
  for (const axis of [...AXES, 'margin_stability']) assert.equal(await el.locator('[data-sr-members="' + axis + '"]').count(), 1, label + ' comparison list ' + axis);
  for (const axis of Object.keys(PRICE)) { const row = el.locator('tr[data-sr-axis="' + axis + '"]'); assert.ok(Number(await row.getAttribute('data-sr-coverage')) >= 0); assert.match(await row.textContent(), /채택 기준 454/); }
  assert.equal(await page.locator('[data-stat-radar] [style], [data-stat-radar][style]').count(), 0, label + ' no inline styles');
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), label + ' no horizontal overflow');
}
async function checkNoDevice(el, label, financial) {
  const state = await el.getAttribute('data-sr-device'); assert.ok(['OFF', 'NOT_AVAILABLE', 'AUTH_REQUIRED', 'SHEET_NOT_CONNECTED'].includes(state), label + ' device state ' + state);
  assert.equal(await el.getAttribute('data-sr-quotes'), 'NONE', label + ' no device quotes');
  for (const axis of Object.keys(PRICE)) for (const s of ['company', 'industry', 'sic']) { const c = await cellOf(el, axis, s); if (!c) continue;
    assert.equal(c.raw, 'NA', label + ' ' + axis + ' ' + s); assert.equal(c.score, 'NA'); assert.equal(c.reason, 'NO_DEVICE_PRICE', label + ' ' + axis + ' ' + s + ' reason'); }
  for (const s of ['company', 'industry', 'sic']) { const c = await cellOf(el, 'v', s); if (!c) continue; assert.equal(c.score, 'NA', label + ' V ' + s);
    if (financial) { assert.equal(c.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED', label + ' V ' + s + ' financial'); assert.match(c.text, /현재 금융업 가치평가 모델 미지원/); assert.doesNotMatch(c.text, /미산출/, 'model scope is not a data failure');
      assert.equal(await el.locator('tr[data-sr-axis="v"] td[data-sr-series="' + s + '"] .badge.NOT_AVAILABLE').count(), 0); }
    else if (s === 'company') { assert.ok(c.reason && c.reason !== 'FINANCIAL_PROFILE_V_NOT_DEFINED'); assert.match(c.text, /미산출/); }
    else assert.equal(c.reason, 'NO_DEVICE_PRICE', label + ' V ' + s); }
  for (const axis of ['v', ...Object.keys(PRICE)]) assert.equal(await el.locator('.sr-mark[data-sr-axis="' + axis + '"]').count(), 0, label + ' no vertex for 미산출 ' + axis);
  assert.equal(await el.locator('[data-sr-freshness]').getAttribute('data-sr-freshness'), 'UNKNOWN'); assert.match(await el.locator('[data-sr-freshness]').textContent(), /가격 기준 시각: 미확인/);
}
/* V missing: any QGV total shown in the radar is labelled 'Q·G만 반영(V 미포함)' and equals the score accessor's total (one path). */
async function checkQgOnly(page, el, spec, label) {
  const want = await page.evaluate(async (spec) => { const inputs = await Qgv2Inputs.load(window), id = spec.code ? { company_id: spec.code, ticker: spec.code.slice(spec.code.indexOf(':') + 1) } : { company_id: spec.targetId, ticker: PrivateHistory.symbolFor(spec.targetId) };
    const S = QgvScores.compute({ identities: [id], v2Inputs: inputs }), d = S.rows[id.company_id].primary; return Number.isFinite(d.total) ? d.total : null; }, spec);
  const tag = el.locator('tr[data-sr-axis="v"] td[data-sr-series="company"] [data-sr-total-qg-only]');
  if (want === null) { assert.equal(await tag.count(), 0, label + ' no total'); return 1; }
  assert.match(await tag.textContent(), /Q·G만 반영\(V 미포함\)/); assert.ok((await tag.textContent()).includes(new Intl.NumberFormat('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(want)), label + ' same total as the accessor');
  return 2;
}
/* V detail: financial -> the model-scope text only; general -> each value input with its published raw value or a reason. */
async function checkVDetail(el, r, label) {
  if (r.profile === 'FINANCIAL') { const d = el.locator('[data-sr-v-detail="FINANCIAL"]'); assert.equal(await d.count(), 1, label + ' financial V detail'); assert.match(await d.textContent(), /현재 금융업 가치평가 모델 미지원/);
    assert.equal(await el.locator('[data-sr-v-input]').count(), 0, label + ' no general V formula for financials'); assert.match(await el.locator('figcaption').textContent(), /현재 금융업 가치평가 모델 미지원/); return 3; }
  const v = r.v_inputs_v2 && /^[A-Z]{3}$/.test(r.v_inputs_v2.currency || '') ? r.v_inputs_v2 : null, flow = (x) => (x && Number.isFinite(x.ttm_value) ? x.ttm_value : x && Number.isFinite(x.fy_value) ? x.fy_value : null), val = (x) => (x && Number.isFinite(x.value) ? x.value : null);
  const want = { ebit: v ? flow(v.ebit) : null, fcf: v ? flow(v.fcf) : null, total_debt: v ? val(v.total_debt) : null, cash: v ? val(v.cash_and_equivalents) : null, diluted_shares: v ? val(v.diluted_shares) : null, revenue_cagr_3y: v && Number.isFinite(v.revenue_cagr_3y) ? v.revenue_cagr_3y : null };
  for (const [k, w] of Object.entries(want)) { const row = el.locator('[data-sr-v-input="' + k + '"]'); same(await row.getAttribute('data-sr-raw'), w, label + ' V input ' + k); if (w === null) assert.ok((await row.getAttribute('data-sr-reason')).length > 3); }
  for (const k of ['ebit_yield', 'fcf_yield']) { const row = el.locator('[data-sr-v-input="' + k + '"]'); assert.equal(await row.getAttribute('data-sr-raw'), 'NA', label + ' ' + k + ' needs a quote'); assert.ok((await row.getAttribute('data-sr-reason')).length > 3); assert.match(await row.textContent(), /미산출/); }
  return 8;
}
async function shot(el, name) { if (!SHOTS) return; fs.mkdirSync(SHOTS, { recursive: true }); await el.screenshot({ path: path.join(SHOTS, name + '.png') }); }
/* A synthetic price snapshot rendered in-page through StatRadar.html ctx.device (RAM only): bases default to TOTAL_RETURN. */
async function snapshot(page, bars, code, bases) {
  await page.evaluate(async ({ bars, code, bases }) => {
    const inputs = await Qgv2Inputs.load(window), series = new Map();
    for (const [s, c] of Object.entries(bars)) series.set(s, { closes: c, basis: bases[s] || 'TOTAL_RETURN', source: 'SYNTHETIC_TEST', storage: 'TEST_RAM', as_of: Object.keys(c).sort().pop() });
    let box = document.getElementById('sr-snap'); if (!box) { box = document.createElement('div'); box.id = 'sr-snap'; document.querySelector('main').append(box); }
    box.innerHTML = StatRadar.html({ code }, { screens: { 'sec-qgv2.json': inputs }, device: { state: 'READY', series, priced: series.size - 1 } });
  }, { bars, code, bases });
  return page.locator('#sr-snap [data-stat-radar]');
}
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
        pass += await checkVDetail(el, exp.subject.r, phase); pass += await checkQgOnly(page, el, spec, phase);
        await shot(el, 'radar-' + kind.toLowerCase() + '-' + width + '-light-nodevice');
        // Financial detail: the published operating_margin_std_5y_pp (raw %p, FY basis, source) or its missing-data reason.
        const r = exp.subject.r, want = marginStd(r), hist = ((r.v_inputs_v2 && r.v_inputs_v2.operating_margin_history) || []).map((h) => h.fiscal_year_end).filter(Boolean).sort().slice(-5);
        if (spec.targetId) await page.goto(BASE + '#analysis/' + encodeURIComponent(spec.targetId) + '/financials');
        const fd = page.locator(spec.targetId ? '[data-analysis-panel="financials"] [data-sr-margin-detail]' : '[data-universe-card="financials"] [data-sr-margin-detail]');
        await fd.waitFor({ state: 'attached' }); same(await fd.getAttribute('data-sr-margin-detail'), want, phase + ' financial detail margin std');
        if (want === null) assert.ok((await fd.getAttribute('data-sr-margin-reason')).length > 3); else { assert.equal(await fd.getAttribute('data-sr-margin-years'), hist.length === 5 ? hist.join(',') : ''); assert.match(await fd.textContent(), /%p/); }
        assert.match(await fd.textContent(), /sec-qgv2\.json/); pass += 2;
      }
      if (treeCode) {
        phase = width + ' TREE'; await page.goto(BASE + '#tree/qgv'); const el = await radar(page);
        assert.equal(await el.getAttribute('data-sr-subject'), treeCode, 'tree radar uses the tree example row');
        assert.equal(await page.locator('[data-tree-examples="qgv"] [data-example-code]').getAttribute('data-example-code'), treeCode);
        assert.match(await page.locator('[data-tree-radar-node]').textContent(), /후보 축 포함|결정됨/);
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
      // 2a) Comparison series ("비교군 바꾸기", 2.4): display only. PC = toggle buttons (aria-pressed), phone = one select; the
      //     competitor average stays disabled with the REL-SOURCE "미연결" note. Axes, scores, table, official rows and browser
      //     storage are unchanged; the choice lives in RAM for this page only.
      if (uni) {
        phase = width + ' COMPARE'; await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); const el = await radar(page), exp = expectPublic(p, { code: uni.code });
        const series = exp.gr.same ? ['company', 'industry'] : ['company', 'industry', 'sic'], phone = width < 750;
        const storage = () => page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()])), st0 = await storage();
        const cells = () => el.locator('td[data-sr-series]').evaluateAll((ns) => ns.map((n) => n.dataset.srSeries + ':' + n.dataset.srRaw + ':' + n.dataset.srScore + ':' + n.dataset.srReason).join('|'));
        const drawn = () => el.locator('svg[data-sr-svg] g.sr-series').evaluateAll((ns) => ns.map((n) => [...n.classList].find((c) => c.startsWith('sr-series-')).slice(10)).sort());
        const marks = () => el.locator('.sr-mark[data-sr-series="company"]').count(), cells0 = await cells(), marks0 = await marks();
        const label0 = await el.locator('svg[data-sr-svg]').getAttribute('aria-label');
        assert.equal(await el.getAttribute('data-sr-show'), series.join(','), phase + ' every series shown by default');
        assert.deepEqual(await drawn(), [...series].sort(), phase + ' default drawing');
        const group = el.locator('[data-sr-compare]'); assert.equal(await group.count(), 1, phase + ' one comparison control');
        assert.match(await group.textContent(), /비교군 바꾸기/);
        const buttons = el.locator('[data-sr-series-toggle]'), select = el.locator('select[data-sr-compare-select]');
        assert.deepEqual(await buttons.evaluateAll((ns) => ns.map((n) => n.dataset.srSeriesToggle)), [...series, 'competitor'], phase + ' toggle per series');
        const comp = el.locator('[data-sr-series-toggle="competitor"]'); assert.equal(await comp.isDisabled(), true, phase + ' competitor disabled');
        assert.match(await comp.textContent(), /미연결/); assert.match(await group.textContent(), /REL-SOURCE/);
        assert.equal(await select.locator('option[value="competitor"]').getAttribute('disabled'), '', phase + ' competitor option disabled');
        assert.match(await select.locator('option[value="competitor"]').textContent(), /미연결/);
        assert.equal(await page.locator('label[for="' + (await select.getAttribute('id')) + '"]').count(), 1, phase + ' select has a label');
        const box = async (loc) => loc.evaluate((n) => { const r = n.getBoundingClientRect(); return { w: r.width, h: r.height }; });
        if (phone) {
          assert.equal(await select.isVisible(), true, phase + ' phone: select'); assert.equal(await buttons.first().isVisible(), false, phase + ' phone: no toggle row');
          assert.ok((await box(select)).h >= 44, phase + ' select target >= 44px'); assert.equal(await select.inputValue(), exp.gr.same ? 'industry' : 'all');
          const opts = await select.locator('option').evaluateAll((ns) => ns.map((n) => n.value));
          assert.deepEqual(opts, exp.gr.same ? ['industry', 'none', 'competitor'] : ['all', 'industry', 'sic', 'none', 'competitor'], phase + ' options');
          const steps = exp.gr.same ? [['none', ['company']], ['industry', ['company', 'industry']]] : [['industry', ['company', 'industry']], ['sic', ['company', 'sic']], ['none', ['company']], ['all', ['company', 'industry', 'sic']]];
          for (const [v, want] of steps) { await select.selectOption(v); await page.waitForFunction((w) => document.querySelector('[data-stat-radar]').dataset.srShow === w, want.join(','));
            assert.deepEqual(await drawn(), [...want].sort(), phase + ' select ' + v); assert.equal(await select.inputValue(), v, phase + ' select keeps ' + v);
            assert.equal(await page.evaluate(() => document.activeElement && document.activeElement.matches('select[data-sr-compare-select]')), true, phase + ' focus stays on the select');
            assert.equal(await cells(), cells0, phase + ' table unchanged ' + v); assert.equal(await marks(), marks0, phase + ' company vertices unchanged ' + v); pass += 3; }
        } else {
          assert.equal(await select.isVisible(), false, phase + ' PC: no select'); assert.equal(await buttons.first().isVisible(), true, phase + ' PC: toggles');
          for (const s of series) { const b = el.locator('[data-sr-series-toggle="' + s + '"]'), bb = await box(b); assert.ok(bb.h >= 44 && bb.w >= 44, phase + ' ' + s + ' target >= 44px'); assert.equal(await b.getAttribute('aria-pressed'), 'true'); }
          for (const s of series.slice(1)) {
            const b = el.locator('[data-sr-series-toggle="' + s + '"]'); await b.click();
            assert.equal(await el.locator('[data-sr-series-toggle="' + s + '"]').getAttribute('aria-pressed'), 'false', phase + ' ' + s + ' off');
            assert.deepEqual(await drawn(), series.filter((x) => x !== s).sort(), phase + ' ' + s + ' hidden'); assert.equal(await el.getAttribute('data-sr-show'), series.filter((x) => x !== s).join(','));
            assert.equal(await page.evaluate((s) => document.activeElement && document.activeElement.dataset.srSeriesToggle, s), s, phase + ' focus stays on the toggle');
            assert.equal(await el.locator('[data-sr-legend="' + s + '"]').getAttribute('data-sr-legend-shown'), 'false', phase + ' legend says hidden');
            assert.equal(await cells(), cells0, phase + ' table unchanged without ' + s); assert.equal(await marks(), marks0, phase + ' company vertices unchanged');
            assert.equal(await el.locator('svg[data-sr-svg]').getAttribute('data-sr-axes'), '6', phase + ' axes unchanged');
            await el.locator('[data-sr-series-toggle="' + s + '"]').click(); assert.deepEqual(await drawn(), [...series].sort(), phase + ' ' + s + ' back'); pass += 4; }
          // the company can be hidden too (comparison groups only); keyboard works on the real buttons
          const cb = el.locator('[data-sr-series-toggle="company"]'); await cb.focus(); await page.keyboard.press('Enter');
          assert.equal(await marks(), 0, phase + ' company hidden'); assert.equal(await el.locator('[data-sr-shape="company"]').count(), 0); assert.equal(await cells(), cells0);
          await page.keyboard.press(' '); assert.equal(await marks(), marks0, phase + ' company back'); pass += 2;
        }
        // The choice survives a repaint of the same radar (RAM), never reaches browser storage, and the summary names what is drawn.
        if (phone) await select.selectOption('none'); else await el.locator('[data-sr-series-toggle="industry"]').click();
        assert.match(await el.locator('svg[data-sr-svg]').getAttribute('aria-label'), /표시 계열/); assert.notEqual(await el.locator('svg[data-sr-svg]').getAttribute('aria-label'), label0);
        const want = phone ? 'company' : series.filter((x) => x !== 'industry').join(',');
        await page.evaluate(() => StatRadar.mount(document.querySelector('main'))); await page.waitForFunction((w) => document.querySelector('[data-stat-radar]').dataset.srShow === w, want);
        assert.equal(await storage(), st0, phase + ' nothing written to browser storage'); pass += 3;
        await shot(el, 'radar-universe-' + width + '-light-compare');
      }
      // 2b) One V path: with synthetic Universe-tab quotes (made-up prices, never real), the radar's V equals the shared
      //     QgvScores.pageResult V for the same quotes, and its peers are the rows of that same result.
      if (uni) {
        phase = width + ' V-PATH'; const general = points.filter((x) => x.r.profile === 'GENERAL').slice(0, 80), quotes = {}; if (!general.includes(uni)) general.push(uni);
        general.forEach((x, i) => { quotes[x.code] = { price: 20 + ((i * 13) % 70), currency: 'USD' }; });
        await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await radar(page);
        await page.evaluate((q) => { const real = window.PrivateSubsetView; window.PrivateSubsetView = { ...real, prices: () => new Map(Object.entries(q)), priceBasis: () => ({ source: 'SYNTHETIC_TEST', read_id: 'synthetic-v-path', acquired_at: null, currency: 'USD', price_time: null }) }; }, quotes);
        await page.goto(BASE + '#home'); await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); const el = await radar(page);
        await page.waitForFunction(() => { const c = document.querySelector('[data-stat-radar] tr[data-sr-axis="v"] td[data-sr-series="company"]'); return c && c.dataset.srReason !== 'PENDING'; });
        const shared = await page.evaluate(async (code) => { const inputs = await Qgv2Inputs.load(window), r = await QgvScores.pageResult(window, { v2Inputs: inputs, catalog: null, identities: [{ company_id: code, ticker: code.slice(code.indexOf(':') + 1) }] });
          const d = r.computed.rows[code].primary; return { v: Number.isFinite(d.v) ? d.v : null, reason: d.coverage && d.coverage.axes && d.coverage.axes.V ? d.coverage.axes.V.reason : null }; }, uni.code);
        const c = await cellOf(el, 'v', 'company'); same(c.score, shared.v, phase + ' radar V = pageResult V'); if (shared.v === null) assert.equal(c.reason, shared.reason || 'NO_DEVICE_PRICE');
        assert.equal(await el.getAttribute('data-sr-quotes'), 'PRESENT'); pass += 2; if (width === 390) console.log('V_PATH ' + uni.code + ' v=' + (shared.v === null ? 'NA:' + shared.reason : shared.v.toFixed(3)));
        await page.evaluate(() => { window.location.reload(); }); await page.waitForLoadState('load');
      }
      // 3) Price data, synthetic bars only (made-up random walks; never real prices, never committed as data).
      //    (a) The price tab's raw closes (fake PriceStore): every price axis is 미산출 ADJUSTMENT_BASIS_UNCONFIRMED — a raw series
      //        cannot confirm corporate-action handling, and the jump check never confirms continuity.
      //    (b) A confirmed TOTAL_RETURN snapshot rendered in-page (StatRadar.html ctx.device, RAM): window, raw values, relative
      //        scores, group means, the RAW-basis member left out, gaps, few members and a stale window vs independent formulas.
      if (uni) {
        phase = width + ' DEVICE'; const exp = expectPublic(p, { code: uni.code }), ind = exp.gr.industry.m, others = points.filter((x) => x.cik !== uni.cik && !ind.includes(x));
        const chosen = [uni, ...ind.slice(0, 7), ...others.slice(0, 3)], bars = { SPY: walk(7, 320, today) };
        chosen.forEach((x, i) => { bars[symbolOf(x.code)] = walk(1000 + i * 37, 320, today); });
        const cal = Object.keys(bars.SPY).sort().slice(-252), gapped = chosen[2], gapped10 = chosen[3], sparse = ind[7], short = ind[8], mixed = ind[9];
        { const c = bars[symbolOf(gapped.code)]; for (let i = 20; i < 220; i += 10) delete c[cal[i]]; }                    // 20 isolated gaps: 232 closes, 211 valid returns
        { const c = bars[symbolOf(gapped10.code)]; for (let i = 20; i < 220; i += 20) delete c[cal[i]]; }                  // 10 isolated gaps: 242 closes, 231 valid returns
        if (sparse) { const c = walk(4321, 320, today); for (let i = 5; i < 120; i += 4) delete c[cal[i]]; bars[symbolOf(sparse.code)] = c; } // 223 closes
        if (short) bars[symbolOf(short.code)] = walk(77, 100, today);
        if (mixed) bars[symbolOf(mixed.code)] = walk(555, 320, today);
        await page.goto(BASE + '#company/' + encodeURIComponent(uni.code)); await radar(page);
        const before = await page.evaluate(() => JSON.stringify([Object.keys(localStorage).sort(), Object.keys(sessionStorage).sort()]));
        const official = () => page.evaluate(async (codes) => { const inputs = await Qgv2Inputs.load(window); const S = QgvScores.compute({ identities: codes.map((c) => ({ company_id: c, ticker: c.slice(c.indexOf(':') + 1) })), v2Inputs: inputs });
          return JSON.stringify(codes.map((c) => { const d = S.rows[c].primary; return [d.q, d.g, d.v, d.total, S.rows[c].rank]; })); }, chosen.map((x) => x.code));
        const off0 = await official();
        // (a) raw closes from the price tab
        await page.evaluate(FAKE_STORE, bars); await page.goto(BASE + '#home'); await page.goto(BASE + '#company/' + encodeURIComponent(uni.code));
        { const el = await radar(page, 'READY'); assert.equal(await el.getAttribute('data-sr-basis'), 'RAW');
          for (const axis of Object.keys(PRICE)) { const c = await cellOf(el, axis, 'company'); assert.equal(c.raw, 'NA', 'raw basis: no raw value ' + axis); assert.equal(c.score, 'NA'); assert.equal(c.reason, 'ADJUSTMENT_BASIS_UNCONFIRMED', 'raw basis -> ' + axis);
            for (const k of exp.gr.same ? ['industry'] : ['industry', 'sic']) assert.equal((await cellOf(el, axis, k)).reason, 'ADJUSTMENT_BASIS_UNCONFIRMED');
            assert.match(await el.locator('tr[data-sr-axis="' + axis + '"]').getAttribute('data-sr-storage'), /구글 시트 Prices_D/);
            assert.match(await el.locator('tr[data-sr-axis="' + axis + '"] th').textContent(), /후보 축\(커버리지 확인 전\)/); }
          assert.equal(await el.locator('.sr-mark[data-sr-axis="price_stability"]').count(), 0); assert.match(await el.locator('[data-sr-device-line]').textContent(), /비공개 구글 시트 Prices_D/);
          assert.doesNotMatch(await el.textContent(), /기기 안에서만/); await checkCommon(page, el, phase + ' raw'); await shot(el, 'radar-universe-' + width + '-light-device-raw-unconfirmed'); pass += 5; }
        // (b) confirmed TOTAL_RETURN snapshot (the mixed member stays RAW)
        const bases = mixed ? { [symbolOf(mixed.code)]: 'RAW' } : {};
        const el = await snapshot(page, bars, uni.code, bases);
        const all = [...chosen, ...[sparse, short].filter(Boolean)], vals = {}; for (const x of all) vals[x.code] = metrics(bars[symbolOf(x.code)], bars.SPY, cal);
        assert.equal(await el.getAttribute('data-sr-window-end'), cal[cal.length - 1], 'window ends at the latest common session');
        assert.equal(await el.getAttribute('data-sr-stale'), 'CURRENT'); assert.equal(await el.getAttribute('data-sr-basis'), 'TOTAL_RETURN');
        assert.ok((await el.locator('tr[data-sr-axis="price_stability"]').getAttribute('data-sr-period')).startsWith(cal[0] + ' ~ ' + cal[251]), 'window = last 252 SPY sessions');
        assert.ok((await el.locator('tr[data-sr-axis="relative_strength"]').getAttribute('data-sr-period')).startsWith(cal[125] + ' ~ ' + cal[251]), 'RS window = 126 sessions');
        assert.match(await el.locator('tr[data-sr-axis="price_stability"]').getAttribute('data-sr-basis'), /총수익/);
        for (const [axis, dir] of Object.entries(PRICE)) {
          const m = new Map(all.filter((x) => x !== uni && vals[x.code][axis] !== null).map((x) => [x.code, vals[x.code][axis]])), e = rankExpect(dir, m, vals[uni.code][axis], exp.gr);
          pass += await checkAxis(el, axis, e, exp.gr, phase);
          assert.match(await el.locator('tr[data-sr-axis="' + axis + '"] td[data-sr-series="company"]').textContent(), /기기 보유 데이터 내 상대점수/);
          const best = [...m.values(), vals[uni.code][axis]].sort((a, b) => dir * b - dir * a)[0]; if (best === vals[uni.code][axis]) same((await cellOf(el, axis, 'company')).score, 100, phase + ' ' + axis + ' best is outermost');
          assert.equal(Number(await el.locator('[data-sr-members="' + axis + '"]').getAttribute('data-sr-members-n')), m.size, phase + ' ' + axis + ' comparison list');
          if (mixed) assert.match(await el.locator('[data-sr-members="' + axis + '"] [data-sr-excluded]').textContent(), new RegExp(symbolOf(mixed.code).replace(/[-.]/g, '\\$&') + ' \\(BASIS_MISMATCH\\)'), 'RAW member left out');
        }
        assert.equal(vals[gapped.code].price_stability, null, '20 isolated gaps: 211 valid returns < 226 -> volatility not measured');
        assert.notEqual(vals[gapped.code].drawdown_defense, null, '20 isolated gaps: 232 closes -> drawdown measured');
        await checkCommon(page, el, phase); await shot(el, 'radar-universe-' + width + '-light-synthetic-total-return');
        // Gap rule on the pure function: closes and valid returns counted apart; a multi-day move across a gap is no daily return.
        const gap = await page.evaluate(({ c10, c20, spy }) => { const f = (c) => StatRadar.priceAxes({ basis: 'TOTAL_RETURN', closes: c }, { basis: 'TOTAL_RETURN', closes: spy }).axes; return { a: f(c10), b: f(c20) }; }, { c10: bars[symbolOf(gapped10.code)], c20: bars[symbolOf(gapped.code)], spy: bars.SPY });
        { const pts = cal.map((d) => bars[symbolOf(gapped10.code)][d] ?? null), seq = pts.filter((x) => x !== null), naive = []; for (let i = 1; i < seq.length; i++) naive.push(seq[i] / seq[i - 1] - 1);
          const nm = mean(naive), naiveVol = Math.sqrt(naive.reduce((a, x) => a + (x - nm) ** 2, 0) / (naive.length - 1)) * Math.sqrt(252);
          assert.equal(gap.a.price_stability.closes, 242); assert.equal(gap.a.price_stability.returns, 231); assert.ok(close(gap.a.price_stability.value, vals[gapped10.code].price_stability), 'adjacent-pair volatility');
          assert.ok(!close(gap.a.price_stability.value, naiveVol), 'gap-spanning moves are not daily returns');
          assert.equal(gap.b.price_stability.closes, 232); assert.equal(gap.b.price_stability.returns, 211); assert.equal(gap.b.price_stability.reason, 'INSUFFICIENT_SAMPLE');
          assert.equal(gap.b.drawdown_defense.note, 'MDD_GAPS', 'MDD with gaps says the trough may be missed'); pass += 4; }
        // Raw value shown while the relative score is 미산출 (population below 8): the subject and 4 peers only.
        { const few = { SPY: bars.SPY }; for (const x of chosen.slice(0, 5)) few[symbolOf(x.code)] = bars[symbolOf(x.code)];
          const e2 = await snapshot(page, few, uni.code, {}); const c = await cellOf(e2, 'drawdown_defense', 'company');
          same(c.raw, vals[uni.code].drawdown_defense, 'raw shown with few members'); assert.equal(c.score, 'NA'); assert.equal(c.reason, 'PEERS_TOO_FEW'); assert.match(c.text, /원값/); assert.match(c.text, /미산출/);
          assert.equal(await e2.locator('.sr-mark[data-sr-series="company"][data-sr-axis="drawdown_defense"]').count(), 0, 'no vertex without a score'); pass += 2; }
        // Stale window: every series ends 20 calendar days ago.
        { const old = new Date(Date.now() - 20 * 864e5).toISOString().slice(0, 10), stale = { SPY: walk(7, 320, old) }; for (const [i, x] of chosen.entries()) stale[symbolOf(x.code)] = walk(1000 + i * 37, 320, old);
          const e3 = await snapshot(page, stale, uni.code, {}); assert.equal(await e3.getAttribute('data-sr-stale'), 'STALE'); assert.equal(await e3.locator('svg.sr-stale .sr-stale-label').count(), 1);
          assert.match(await e3.locator('[data-sr-freshness]').textContent(), /STALE/); assert.ok(Number(await e3.locator('[data-sr-freshness]').getAttribute('data-sr-days')) >= 20);
          await shot(e3, 'radar-universe-' + width + '-light-synthetic-stale'); pass += 2; }
        await page.evaluate(() => { const b = document.getElementById('sr-snap'); if (b) b.remove(); });
        // Pure rules: raw / unstated basis, split diagnostic, adjusted bases, mismatch, 90 % minimums, endpoints.
        const rules = await page.evaluate(({ spy, base, splitDay }) => {
          const S = StatRadar, rs = (o) => Object.fromEntries(Object.entries(o.axes).map(([k, v]) => [k, v.reason])), TR = 'TOTAL_RETURN';
          const cut = (c, n) => { const d = Object.keys(c).sort(), out = { ...c }; for (const x of d.slice(-252, -252 + n)) delete out[x]; return out; };
          const halved = { ...base }; for (const d of Object.keys(base).sort().filter((d) => d >= splitDay)) halved[d] = base[d] / 2;
          const keepRecent = (c, n) => { const d = Object.keys(c).sort().slice(-126), out = { ...c }; for (const x of d.slice(1, 1 + n)) delete out[x]; return out; };
          const noStart = { ...base }; delete noStart[Object.keys(spy).sort().slice(-127)[0]];
          const ax = (c, b, s = b) => rs(S.priceAxes({ basis: b, closes: c }, { basis: s, closes: spy }));
          return { raw: ax(base, 'RAW'), split: ax(halved, 'RAW'), unstated: ax(base, 'ADJUSTED'), splitAdj: ax(base, 'SPLIT_ADJUSTED'), trHalved: ax(halved, TR), mismatch: ax(base, TR, 'SPLIT_ADJUSTED'),
            min227: ax(cut(base, 25), TR), min226: ax(cut(base, 26), TR), rs113: ax(keepRecent(base, 13), TR), rs112: ax(keepRecent(base, 14), TR), endpoint: ax(noStart, TR),
            noSpy: rs(S.priceAxes({ basis: TR, closes: base }, { basis: TR, closes: {} })), hasArea: Object.keys(S).some((k) => /area/i.test(k)) };
        }, { spy: bars.SPY, base: bars[symbolOf(uni.code)], splitDay: cal[200] });
        const allOf = (r) => ({ price_stability: r, drawdown_defense: r, relative_strength: r });
        assert.deepEqual(rules.raw, allOf('ADJUSTMENT_BASIS_UNCONFIRMED'), 'raw basis is unconfirmed even without a jump');
        assert.deepEqual(rules.split, allOf('CORPORATE_ACTION_UNADJUSTED')); assert.deepEqual(rules.unstated, allOf('ADJUSTMENT_BASIS_UNCONFIRMED'), 'adjusted with no stated basis');
        assert.deepEqual(rules.splitAdj, allOf(null), 'split-adjusted basis on both sides'); assert.deepEqual(rules.trHalved, allOf(null), 'a confirmed adjusted basis is not jump-checked');
        assert.deepEqual(rules.mismatch, allOf('BASIS_MISMATCH'));
        assert.equal(rules.min227.price_stability, null); assert.equal(rules.min226.price_stability, 'INSUFFICIENT_SAMPLE'); assert.equal(rules.min226.drawdown_defense, 'INSUFFICIENT_SAMPLE');
        assert.equal(rules.rs113.relative_strength, null); assert.equal(rules.rs112.relative_strength, 'INSUFFICIENT_SAMPLE'); assert.equal(rules.endpoint.relative_strength, 'ENDPOINT_MISSING');
        assert.equal(rules.noSpy.price_stability, 'SPY_NOT_AVAILABLE'); assert.equal(rules.hasArea, false, 'no area function'); pass += 11;
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
          const d = await snapshot(dp, bars, uni.code, bases); await shot(d, 'radar-universe-' + width + '-dark-synthetic-total-return');
          await d.locator('[data-sr-aux-toggle]').click(); await shot(dp.locator('#sr-snap [data-stat-radar]'), 'radar-universe-' + width + '-dark-synthetic-total-return-aux7');
          await dctx.close();
        }
      }
      assert.deepEqual(errors, []); await context.close();
    }
    console.log('STAT_RADAR_BROWSER_OK checks=' + pass);
  } catch (e) { console.error('STAT_RADAR_BROWSER_FAIL phase=' + phase + ' ' + (e && e.message)); process.exitCode = 1; } finally { await browser.close(); }
})();
