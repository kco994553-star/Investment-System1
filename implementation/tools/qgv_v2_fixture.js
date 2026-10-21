'use strict';
// Synthetic QGV v2 test data (node + browser tests): a `sec-qgv2.json` payload in the Q·G side's published row shape
// (universe/sec_qgv2.py: records by Universe code + target by TARGET id, published Q/G axes, v_inputs_v2 with FY/TTM flows),
// synthetic device quotes and the matching Universe-tab rows. Every number is made up; nothing here is a real price.
const path = require('node:path');
const V2 = require(path.join(__dirname, '../src/investment_system/product/web_assets/qgv-v2.js'));
const TICKERS = { lrcx: 'NASDAQ:LRCX', klac: 'NASDAQ:KLAC', nvda: 'NASDAQ:NVDA', amd: 'NASDAQ:AMD', avgo: 'NASDAQ:AVGO', qcom: 'NASDAQ:QCOM', intc: 'NASDAQ:INTC',
  msft: 'NASDAQ:MSFT', googl: 'NASDAQ:GOOGL', amzn: 'NASDAQ:AMZN', rtx: 'NYSE:RTX', stry: 'NYSE:SYK', etn: 'NYSE:ETN', hubb: 'NYSE:HUBB', gev: 'NYSE:GEV', rok: 'NYSE:ROK' };
const Q = Object.keys(V2.WEIGHTS.Q), G = Object.keys(V2.WEIGHTS.G);
const SEMIS = new Set(['NASDAQ:LRCX', 'NASDAQ:KLAC', 'NASDAQ:NVDA', 'NASDAQ:AMD', 'NASDAQ:AVGO', 'NASDAQ:QCOM', 'NASDAQ:INTC', 'NASDAQ:SYNS1', 'NASDAQ:SYNS2']);
function codes() { return [...Object.values(TICKERS), 'NASDAQ:GOOG', 'NASDAQ:SYNS1', 'NASDAQ:SYNS2', 'NYSE:SYNI1', 'NYSE:SYNI2', 'NYSE:SYNF1']; }
function row(code, i) {
  const fin = code === 'NYSE:SYNF1', q = 40 + ((i * 7) % 45), g = 35 + ((i * 11) % 50), factors = {};
  Q.forEach((k, j) => { factors[k] = Math.round((q + j * 2) * 10) / 10; });
  G.forEach((k, j) => { factors[k] = Math.round((g - j * 1.5) * 10) / 10; });
  if (code === 'NASDAQ:INTC') { factors.g_revenue_growth = null; factors.g_per_share_growth = null; }
  const axis = (a) => { const r = V2.axisScore(factors, a); return { score: r.score, factors_available: r.factors_available + '/5', available_weight: r.weight_available, peer_basis: 'UNIVERSE', peer_count: 22, reason_codes: [] }; };
  const ebit = 40 + i * 9, shares = 100 + i * 3, ocf = 30 + i * 6, capex = 5 + i;
  return {
    cik: String(1000000 + (code === 'NASDAQ:GOOG' ? codes().indexOf('NASDAQ:GOOGL') + 1 : i)).padStart(10, '0'), acquired_at: '2026-10-13T00:00:00Z', source_sha256: { companyfacts: 'a'.repeat(64), submissions: 'b'.repeat(64) },
    state: 'LIVE', reason_codes: [], sic: SEMIS.has(code) ? '3674' : fin ? '6022' : '3600', industry_group: SEMIS.has(code) ? 'manufacturing_industrial_tech' : fin ? 'finance_real_estate' : 'services_software_health',
    profile: fin ? 'FINANCIAL' : 'GENERAL', fiscal_year_end: '2025-12-31', currency: 'USD', metrics: {}, factors, axes: { Q: axis('Q'), G: axis('G') },
    v_inputs_v2: {
      currency: 'USD', taxonomy: 'us-gaap', fiscal_year_end: '2025-12-31',
      ebit: { fy_value: ebit, fy_end: '2025-12-31', ttm_value: i % 2 ? ebit + 3 : null, ttm_end: i % 2 ? '2026-06-30' : null },
      fcf: { fy_value: ocf - capex, fy_end: '2025-12-31', ttm_value: null, ttm_end: null },
      total_debt: { value: 80 + i * 4, period_end: '2026-06-30' }, cash_and_equivalents: { value: 20 + i * 2, period_end: '2026-06-30' }, diluted_shares: { value: shares, period_end: '2026-06-30' },
      ebit_per_share_history: [2021, 2022, 2023, 2024, 2025].map((y, j) => ({ fiscal_year_end: y + '-12-31', value: Math.round(ebit / shares * (0.7 + 0.07 * j) * 1e4) / 1e4 })),
      fcf_per_share_history: [], revenue_cagr_3y: 0.03 + (i % 5) * 0.02, eps_cagr_3y: 0.05, fcf_per_share_cagr_3y: 0.04, revenue_ttm_growth: 0.06,
    },
  };
}
function payload() {
  const records = {}, target = {};
  codes().forEach((c, i) => { records[c] = row(c, i + 1); });
  for (const [id, code] of Object.entries(TICKERS)) target[id] = JSON.parse(JSON.stringify(records[code]));
  target.asml = row('NASDAQ:ASML', 40);  // not in the Universe: scored against it, not added
  target.asml.v_inputs_v2.currency = 'EUR';target.asml.currency = 'EUR';
  target.tokyo_electron = { cik: null, state: 'NOT_AVAILABLE', reason_codes: ['NON_SEC_ISSUER'], fiscal_year_end: null, factors: {}, axes: {}, v_inputs_v2: {} };
  return { schema_version: 1, kind: 'SEC_QGV2', as_of: '2026-10-13T00:00:00Z', standard: 'QGV_V2', standard_status: 'PROVISIONAL_DEFAULT_UNCALIBRATED', records, target };
}
// Synthetic device quotes {code: {price, currency}} for every code but one (no price -> V NA).
function quotes() {
  const out = {};
  codes().forEach((c, i) => { if (c !== 'NYSE:GEV') out[c] = { price: 20 + ((i * 13) % 70), currency: 'USD' }; });
  return out;
}
function universeValues() { return [['code', 'marketcap', 'price'], ...Object.entries(quotes()).map(([c, q]) => [c, 1000 + q.price, q.price])]; }
// Strictly valid `sec-qgv2.json` (the Q·G side's synthetic base vector expanded to Universe504, as in its node test), so
// browser tests pass the real SecQgv2 validator. Universe-tab rows price every LIVE code plus NVDA (TARGET row via ticker);
// MSFT is left without a price (V NA).
function strictPayload() {
  const fs = require('node:fs'), reader = require(path.join(__dirname, '../src/investment_system/product/web_assets/sec-qgv2.js'));
  const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/sec_qgv2_vectors_v1.json'), 'utf8'));
  const all = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/investment_system/universe/universe_codes_v1.json'), 'utf8'));
  const p = structuredClone(vectors.base), sparse = p.records;
  p.records = Object.fromEntries(all.map((c) => [c, sparse[c] ? sparse[c] : reader.emptyRecord()]));
  return p;
}
function strictUniverseValues() {
  const p = strictPayload(), rows = [['code', 'marketcap', 'price']];let i = 0;
  for (const [code, r] of Object.entries(p.records)) if (r.state === 'LIVE' && code !== 'NASDAQ:MSFT') { i++;rows.push([code, 5000 + i, 15 + ((i * 17) % 80)]); }
  rows.push(['NASDAQ:NVDA', 9000, 42]);
  return rows;
}
/* Missing-data variant of strictPayload (FE-MISSING-2 screens), still strictly valid: TARGET amd lacks the SEC sub-metrics of
   moat proxy, financial safety, capital allocation and recent acceleration (Q 2/5 = 45% of the original weight -> Q not
   calculated, AXIS_COVERAGE_BELOW_50; G 4/5 = 85% -> partial), with its factors and axes recomputed by the reader's own
   scoreRows (TARGET rows are not in the cross-section, so no other row changes); TARGET msft was collected 2026-09-20, past the
   14-day freshness window (STALE, last valid value FY 2025-12-31). NASDAQ:GOOGL / AMZN stay the FINANCIAL profile rows. */
function missingPayload() {
  const SQ = require(path.join(__dirname, '../src/investment_system/product/web_assets/sec-qgv2.js')), p = strictPayload(), amd = p.target.amd;
  for (const k of ['moat_proxy', 'net_debt_to_ebitda', 'interest_coverage', 'dilution_3y', 'incremental_roic_5y', 'revenue_acceleration']) delete amd.metrics[k];
  const { scores } = SQ.scoreRows(p.records, p.target, p.calc_version), s = scores.get('target\u0000amd');amd.factors = s.factors;amd.axes = s.axes;
  Object.assign(p.target.msft, { acquired_at: '2026-09-20T00:00:00Z', state: 'STALE', reason_codes: ['STALE_INPUT'] });
  SQ.validate(p);return p;
}
module.exports = { TICKERS, codes, payload, quotes, universeValues, strictPayload, strictUniverseValues, missingPayload };
