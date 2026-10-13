'use strict';
// Synthetic QGV v2 test data (node + browser tests): a `sec-qgv2.json` payload in the ASSUMED shape (QGV_V2_V_DEVICE.md §6),
// synthetic device quotes and the matching Universe-tab rows. All numbers are made up; nothing here is a real price.
const TICKERS = { asml: 'NASDAQ:ASML', lrcx: 'NASDAQ:LRCX', klac: 'NASDAQ:KLAC', nvda: 'NASDAQ:NVDA', amd: 'NASDAQ:AMD', avgo: 'NASDAQ:AVGO', qcom: 'NASDAQ:QCOM', intc: 'NASDAQ:INTC',
  msft: 'NASDAQ:MSFT', googl: 'NASDAQ:GOOGL', amzn: 'NASDAQ:AMZN', rtx: 'NYSE:RTX', stry: 'NYSE:SYK', etn: 'NYSE:ETN', hubb: 'NYSE:HUBB', gev: 'NYSE:GEV', rok: 'NYSE:ROK' };
const Q = ['q_profitability', 'q_moat_proxy', 'q_earnings_quality', 'q_financial_safety', 'q_capital_allocation'];
const G = ['g_revenue_growth', 'g_per_share_growth', 'g_growth_efficiency', 'g_consistency', 'g_recent_acceleration'];
const SEMIS = new Set(['NASDAQ:ASML', 'NASDAQ:LRCX', 'NASDAQ:KLAC', 'NASDAQ:NVDA', 'NASDAQ:AMD', 'NASDAQ:AVGO', 'NASDAQ:QCOM', 'NASDAQ:INTC', 'NASDAQ:SYNS1']);
function codes() { return [...Object.values(TICKERS), 'NASDAQ:SYNS1', 'NYSE:SYNI1', 'NYSE:SYNI2', 'NYSE:SYNF1']; }
function record(code, i) {
  const q = 40 + ((i * 7) % 45), g = 35 + ((i * 11) % 50), factors = {};
  Q.forEach((k, j) => { factors[k] = { score: Math.round((q + j * 2) * 10) / 10 }; });
  G.forEach((k, j) => { factors[k] = Math.round((g - j * 1.5) * 10) / 10; });
  if (code === 'NASDAQ:INTC') { factors.g_revenue_growth = null; factors.g_per_share_growth = null; }
  const ebit = 40 + i * 9, shares = 100 + i * 3;
  return {
    state: 'LIVE', sic: SEMIS.has(code) ? '3674' : code === 'NYSE:SYNF1' ? '6022' : '3600',
    industry_group: SEMIS.has(code) ? 'semiconductors' : code === 'NYSE:SYNF1' ? 'banks' : 'industrial_equipment',
    profile: code === 'NYSE:SYNF1' ? 'FINANCIAL' : 'GENERAL', factors,
    v_inputs_v2: {
      currency: 'USD', ebit: { value: ebit, period_end: '2025-12-31' }, ocf: { value: 30 + i * 6, period_end: '2025-12-31' }, capex: { value: 5 + i, period_end: '2025-12-31' },
      total_debt: { value: 80 + i * 4, period_end: '2025-12-31' }, cash: { value: 20 + i * 2, period_end: '2025-12-31' }, diluted_shares: { value: shares, period_end: '2025-12-31' },
      ebit_per_share_history: [2021, 2022, 2023, 2024, 2025].map((y, j) => ({ period_end: y + '-12-31', value: Math.round(ebit / shares * (0.7 + 0.07 * j) * 1e4) / 1e4 })),
      revenue_cagr_3y: { value: 0.03 + (i % 5) * 0.02, period_label: 'FY2022-FY2025' },
    },
  };
}
function payload() {
  const records = {};
  codes().forEach((c, i) => { records[c] = record(c, i + 1); });
  return { schema_version: 1, kind: 'SEC_QGV2', as_of: '2026-10-13T00:00:00Z', config_version: 'qgv-v2/assumed', method_status: 'PROVISIONAL', records };
}
// Synthetic device quotes {code: {price, currency}} for every code but one (no price -> V NA).
function quotes() {
  const out = {};
  codes().forEach((c, i) => { if (c !== 'NYSE:GEV') out[c] = { price: 20 + ((i * 13) % 70), currency: 'USD' }; });
  return out;
}
function universeValues() { return [['code', 'marketcap', 'price'], ...Object.entries(quotes()).map(([c, q]) => [c, 1000 + q.price, q.price])]; }
module.exports = { TICKERS, codes, payload, quotes, universeValues };
