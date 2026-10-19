'use strict';
/* JS side of the sec-qgv2.json -> QGV v2 engine-input parity (Python twin: qgv/qgv2_inputs.py, driver tools/qgv2_inputs_parity.py).

   convert(spec) runs the REAL device path: SecQgv2.toInputs (strict) or Qgv2Inputs.light (no strict reader) ->
   Qgv2Inputs.fromInputs -> QgvScores.compute with PlaybookEngine/PlaybookConfigDefaults on the page (cyclical basis).
   The engine records QgvScores hands to QgvV2.scoreUniverse are captured as they are passed, so `companies` is exactly the
   app's own mapping, not a re-implementation. cases() builds the shared inputs: the existing fixtures (tools/qgv_v2_fixture.js,
   tests/fixtures/sec_qgv2_vectors_v1.json valid cases), synthetic edge variants and, when QGV2_PARITY_REAL_FILE names a
   published sec-qgv2.json, that file (read only, never written or copied).
   Quotes are SYNTHETIC, made up in-test from the record keys (no price source is read). Everything stays in RAM; the CLI
   only writes to stdout for the Python test that spawned it.

   CLI: node qgv2_inputs_parity.js cases            -> JSON array of specs on stdout
        node qgv2_inputs_parity.js convert < specs  -> JSON array of outputs on stdout */
const fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const V2_PATH = require.resolve(path.join(W, 'qgv-v2.js')), V2 = require(V2_PATH);
let captured = null;
// Capture the engine call: QgvScores reads ./qgv-v2.js through require() on every call, so the cached exports are swapped once.
require.cache[V2_PATH].exports = Object.freeze({ ...V2, scoreUniverse(companies, quotes, opts) {
  const entry = { companies: structuredClone(companies), quote_codes: Object.keys(quotes || {}).sort(), opts: structuredClone(opts || {}) };
  entry.result = V2.scoreUniverse(companies, quotes, opts); if (captured) captured.push(entry); return entry.result; } });
globalThis.PlaybookEngine = require(path.join(W, 'playbook-engine.js'));
globalThis.PlaybookConfigDefaults = require(path.join(W, 'playbook-config-defaults.js'));
const SecQgv2 = require(path.join(W, 'sec-qgv2.js')), QI = require(path.join(W, 'qgv2-inputs.js')), QS = require(path.join(W, 'qgv-scores.js'));
const F = require('./qgv_v2_fixture.js');
const VECTORS = path.join(__dirname, '../tests/fixtures/sec_qgv2_vectors_v1.json');
const CODES = path.join(__dirname, '../src/investment_system/universe/universe_codes_v1.json');

/* TARGET identities as the device catalog gives them (web_assets/watchlist.js IDS: ticker -> company_id). */
const TARGET_IDENTITIES = Object.freeze([['asml', 'ASML'], ['lrcx', 'LRCX'], ['klac', 'KLAC'], ['tokyo_electron', '8035'], ['hanmi', '042700'], ['nvda', 'NVDA'],
  ['amd', 'AMD'], ['avgo', 'AVGO'], ['qcom', 'QCOM'], ['intc', 'INTC'], ['msft', 'MSFT'], ['googl', 'GOOGL'], ['amzn', 'AMZN'], ['rtx', 'RTX'], ['stry', 'SYK'],
  ['etn', 'ETN'], ['hubb', 'HUBB'], ['gev', 'GEV'], ['rok', 'ROK']].map(([company_id, ticker]) => Object.freeze({ company_id, ticker })));
const OFFICIAL = Object.keys(V2.PRESETS).flatMap((preset) => [true, false].map((gate) => ({ id: preset + '/gate-' + (gate ? 'on' : 'off'), preset, gate })));
const PERSONAL = [
  { id: 'personal/aggressive@0.1', gate: true, weights: V2.userPreset('user-preset/aggressive@0.1').weights, typeWeights: true },
  { id: 'personal/custom-inner/types-off', gate: false, typeWeights: false,
    weights: { axis: { Q: 40, G: 30, V: 30 }, inner: { Q: { q_profitability: 40, q_moat_proxy: 15, q_earnings_quality: 15, q_financial_safety: 15, q_capital_allocation: 15 },
      G: { ...V2.WEIGHTS.G }, V: { v_earnings_yield: 30, v_fcf_yield: 30, v_vs_industry: 15, v_vs_own_history: 10, v_expectation_check: 15 } } } }];

// Strict fixture variants differ in their rows, not in the engine options: one official preset per gate and one personal tree.
const QUICK = () => [OFFICIAL.find((p) => p.id === 'balanced/gate-on'), OFFICIAL.find((p) => p.id === 'value/gate-off'), PERSONAL[0]];

function payloadOf(spec) { return spec.payload_file ? JSON.parse(fs.readFileSync(spec.payload_file, 'utf8')) : structuredClone(spec.payload); }
function inputsOf(spec) {
  const p = payloadOf(spec);
  return spec.source === 'strict' ? QI.fromInputs(SecQgv2.toInputs(p, { now: spec.now })) : QI.fromInputs(QI.light(p));
}
/* QgvScores.pageResult identity list: the given identities, then every Universe code {company_id: code, ticker: symbol}. */
function pageIdentities(inputs, identities) {
  const ids = identities.map((c) => ({ company_id: c.company_id, ticker: c.ticker })), seen = new Set(ids.map((c) => c.company_id));
  for (const code of Object.keys(inputs.records)) if (!code.startsWith('TARGET:') && !seen.has(code)) ids.push({ company_id: code, ticker: code.slice(code.indexOf(':') + 1).replaceAll('.', '-').toUpperCase() });
  return ids;
}
function convert(spec) {
  const inputs = inputsOf(spec), identities = pageIdentities(inputs, spec.identities || []), out = { id: spec.id, inputs: JSON.parse(JSON.stringify(inputs)), page_identities: identities, scores: {} };
  for (const p of spec.profiles) {
    captured = [];
    const args = { identities, v2Inputs: inputs, quotes: spec.quotes, preset: p.preset, gate: p.gate };
    if (p.weights) Object.assign(args, { weights: p.weights, typeWeights: p.typeWeights });
    const computed = QS.compute(args), call = captured.find((c) => Boolean(c.opts.weights) === Boolean(p.weights));
    captured = null;
    if (!call) throw Error('ENGINE_NOT_CALLED ' + p.id + ' ' + computed.v2_reason);
    if (out.companies === undefined) { out.companies = call.companies; out.engine_quote_codes = call.quote_codes; }
    else if (JSON.stringify(out.companies) !== JSON.stringify(call.companies)) throw Error('COMPANIES_DIFFER_BETWEEN_PROFILES ' + p.id);
    out.scores[p.id] = call.result;
  }
  return JSON.parse(JSON.stringify(out));
}

/* SYNTHETIC quotes (made-up numbers, never a real price): one per record key except every 11th, EUR for every 17th
   (currency mismatch), and synthetic month-end closes on the record's own EBIT/share period ends for two of every three. */
function syntheticQuotes(inputs) {
  const out = {};
  Object.keys(inputs.records).sort().forEach((code, i) => {
    if (i % 11 === 3) return;
    const q = { price: 5 + ((i * 37) % 400) + 0.5, currency: i % 17 === 5 ? 'EUR' : 'USD' }, h = inputs.records[code].v_inputs?.ebit_per_share_history || [];
    if (h.length && i % 3) { q.month_closes = {}; h.forEach((x, j) => { q.month_closes[x.period_end.slice(0, 7)] = Math.round(q.price * (0.55 + 0.12 * j) * 100) / 100; }); }
    out[code] = q;
  });
  return out;
}
function spec(id, source, payload, now, { profiles = [...OFFICIAL, ...PERSONAL], payloadFile = null } = {}) {
  const s = { id, source, now, identities: TARGET_IDENTITIES, profiles };
  if (payloadFile) s.payload_file = payloadFile; else s.payload = payload;
  s.quotes = syntheticQuotes(inputsOf(s));
  return s;
}

/* Synthetic edge variants of the light fixture payload (made-up values): every mapping branch of Qgv2Inputs.normalize/fromInputs. */
function lightVariants() {
  const out = [];
  const add = (id, edit) => { const p = F.payload(); edit(p); out.push([id, p]); };
  add('light_fixture', () => {});
  add('light_edges', (p) => {
    const r = p.records, v = (code) => r[code].v_inputs_v2;
    // V-STALE-BS / V-STALE-SHARES / V-SHARES-SCALE as published: the value is withheld (null / []), never filled.
    v('NASDAQ:LRCX').total_debt = null; v('NASDAQ:LRCX').cash_and_equivalents = null;
    v('NASDAQ:KLAC').diluted_shares = null; v('NASDAQ:KLAC').ebit_per_share_history = []; v('NASDAQ:KLAC').fcf_per_share_history = [];
    // FY/TTM flow selection: TTM without an end, FY only without an end, neither; revenue flow + margins.
    v('NASDAQ:NVDA').ebit = { fy_value: 10, fy_end: '2025-12-31', ttm_value: 12, ttm_end: null };
    v('NASDAQ:AMD').ebit = { fy_value: 10, fy_end: null, ttm_value: null, ttm_end: null };
    v('NASDAQ:AVGO').ebit = { fy_value: null, fy_end: null, ttm_value: null, ttm_end: null }; v('NASDAQ:AVGO').fcf = null;
    v('NASDAQ:QCOM').revenue = { fy_value: 900, fy_end: '2025-12-31', ttm_value: 950, ttm_end: '2026-06-30' };
    v('NASDAQ:QCOM').operating_margin_history = [{ fiscal_year_end: '2024-12-31', value: 0.2 }, { fiscal_year_end: '2022-12-31', value: 0.18 }, { fiscal_year_end: '2023-12-31', value: true },
      { fiscal_year_end: '٢٠٢١-12-31', value: 0.1 }, 'x', { fiscal_year_end: '2021-12-31', value: 0.15 }, { fiscal_year_end: '2025-12-31', value: 0.22 }];
    v('NASDAQ:QCOM').ebit_per_share_history.reverse();
    v('NASDAQ:INTC').currency = 'usd';                          // invalid currency -> no V inputs
    v('NASDAQ:MSFT').diluted_shares = { value: 9007199254740993, period_end: '2026-06-30' };
    v('NASDAQ:MSFT').revenue_cagr_3y = '0.1';
    // Factor / axis / metric types: only finite 0..100 scores, only well-formed axis metadata, finite metrics.
    Object.assign(r['NASDAQ:AMZN'].factors, { q_profitability: true, q_moat_proxy: '50', q_earnings_quality: -1, q_financial_safety: 101, q_capital_allocation: 100 });
    Object.assign(r['NASDAQ:AMZN'].axes.Q, { peer_count: 3.0, available_weight: 120, factors_available: '10/5', peer_basis: 'universe', reason_codes: ['OK_CODE', 'bad', 7] });
    r['NASDAQ:AMZN'].axes.G = 'not an axis';
    r['NASDAQ:AMZN'].metrics = { revenue_cagr_3y: 0.15, revenue_volatility_5y_rank_pct: 80, roic: '0.2', Bad: 1, flag: true, ebit_estimated_years: 2, ebit_estimated_fiscal_years: [2023, 2024] };
    r['NYSE:RTX'].metrics = { revenue_cagr_3y: 0.25, revenue_volatility_5y_rank_pct: 69.9, ebit_estimated_fiscal_years: [1899] };
    r['NYSE:ETN'].metrics = { revenue_volatility_5y_rank_pct: 70 };
    r['NYSE:HUBB'].sic = '36a4'; r['NYSE:HUBB'].industry_group = 'Bad Group';
    r['NYSE:ROK'].state = 'STALE'; r['NYSE:ROK'].acquired_at = '2026-10-13T00:00:00.1234Z';
    r['NYSE:SYK'].profile = 'financial';
    // A NOT_AVAILABLE row keeps its source reasons and is in no population.
    r['NYSE:SYNI2'] = { cik: '0000999999', state: 'NOT_AVAILABLE', reason_codes: ['NO_ANNUAL_SEC_FINANCIALS', 'bad'], fiscal_year_end: null, factors: {}, axes: {}, v_inputs_v2: {} };
  });
  add('light_calc_version', (p) => {
    p.calc_version = 'qgv2-calc/2026-10-17.1';
    for (const r of [...Object.values(p.records), ...Object.values(p.target)]) if (r.fiscal_year_end) r.calc_version = 'qgv2-calc/2026-10-17.1';
    p.records['NASDAQ:LRCX'].calc_version = 'qgv2-calc/2026-10-15.1';   // mismatch: out of every population, no memberships
    delete p.records['NASDAQ:KLAC'].calc_version;                      // missing in a versioned file: mismatch
    p.target.nvda.calc_version = 'qgv2-calc/2026-10-15.1';             // TARGET mismatch
    p.records['NASDAQ:GOOGL'].calc_version = 'qgv2-calc/2026-10-15.1';  // the first code of a CIK mismatched: GOOG becomes the point
  });
  add('light_withdrawn', (p) => {
    // TARGET withdrawal (sec_qgv2.WITHDRAWN_REASON): its TARGET record and every Universe code of the same CIK stop.
    const cik = p.records['NASDAQ:AMD'].cik;
    p.target.amd = { cik, state: 'NOT_AVAILABLE', reason_codes: ['IDENTITY_CONFLICT_WITHDRAWN'], fiscal_year_end: null, detected_at: '2026-10-12T00:00:00Z', withdrawn_acquired_at: null, factors: {}, axes: {}, v_inputs_v2: {} };
    // Universe withdrawal row (no CIK) of a TARGET ticker with data: the TARGET's price identity is in conflict (blocked quote).
    p.records['NASDAQ:QCOM'] = { cik: null, state: 'NOT_AVAILABLE', reason_codes: ['IDENTITY_CONFLICT_WITHDRAWN'], fiscal_year_end: null, detected_at: '2026-10-12T00:00:00Z', withdrawn_acquired_at: '2026-10-11T00:00:00Z', withdrawn_cik: '0001000009', factors: {}, axes: {}, v_inputs_v2: {} };
    // A withdrawal named only by its reason code (no detected_at) also stops.
    p.target.intc = { ...p.target.intc, reason_codes: ['IDENTITY_CONFLICT_WITHDRAWN'] };
  });
  return out;
}

function expand(base, codes, emptyRecord) { const p = structuredClone(base), sparse = p.records; p.records = Object.fromEntries(codes.map((c) => [c, sparse[c] ? sparse[c] : emptyRecord()])); return p; }
function applyOps(p, ops, marker) { for (const { path: keys, value } of ops) { let t = p; for (const k of keys.slice(0, -1)) t = t[k]; const last = keys[keys.length - 1]; if (JSON.stringify(value) === JSON.stringify(marker)) delete t[last]; else t[last] = structuredClone(value); } return p; }
function addDays(clock, days) { return new Date(Date.parse(clock) + days * 86400000).toISOString(); }

function cases({ realFile = process.env.QGV2_PARITY_REAL_FILE || null } = {}) {
  const out = lightVariants().map(([id, p]) => spec(id, 'light', p, null));
  const vectors = JSON.parse(fs.readFileSync(VECTORS, 'utf8')), codes = JSON.parse(fs.readFileSync(CODES, 'utf8'));
  for (const c of vectors.cases.filter((x) => x.valid)) {
    const p = applyOps(expand(vectors.base, codes, SecQgv2.emptyRecord), c.ops, vectors.delete_marker);
    out.push(spec('strict_' + c.id, 'strict', p, p.as_of, c.id === 'base_valid' ? {} : { profiles: QUICK() }));
  }
  const base = expand(vectors.base, codes, SecQgv2.emptyRecord);
  out.push(spec('strict_base_valid_stale_now', 'strict', base, addDays(base.as_of, 400), { profiles: OFFICIAL.slice(0, 2) }));
  const missing = F.missingPayload();
  out.push(spec('strict_fixture_missing', 'strict', missing, missing.as_of, { profiles: QUICK() }));
  if (realFile && fs.existsSync(realFile)) {
    const asOf = JSON.parse(fs.readFileSync(realFile, 'utf8')).as_of;
    out.push(spec('real_published_file', 'strict', null, asOf, { payloadFile: realFile }));
    out.push(spec('real_published_file_stale_now', 'strict', null, addDays(asOf, 30), { payloadFile: realFile, profiles: OFFICIAL.slice(0, 1) }));
  }
  return out;
}

module.exports = { TARGET_IDENTITIES, OFFICIAL, PERSONAL, cases, convert, syntheticQuotes, pageIdentities };

if (require.main === module) {
  const mode = process.argv[2];
  if (mode === 'cases') process.stdout.write(JSON.stringify(cases()));
  else if (mode === 'convert') process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0, 'utf8')).map(convert)));
  else { process.stderr.write('usage: qgv2_inputs_parity.js cases|convert\n'); process.exit(2); }
}
