'use strict';
// TYPE-SCOPE (owner instruction 2026-10-17): "apply the same approved type-judgement rule to every company with the same
// eligibility". Before this change only TARGET ids got type memberships (company-types-pricefree.json, TARGET only), so a
// Universe company with the same published inputs was scored with the unclassified 34/33/33 while its TARGET twin got the
// growth weights 30/50/20. Synthetic data only; the one price (100 USD for every code) is a fixed synthetic test value so
// that V and a total exist, never a real price.
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path'), fs = require('node:fs');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
for (const [name, file] of [['EnginePreview', 'engine-preview.js'], ['TypeConfigDefaults', 'type-config-defaults.js'], ['DcfParametersDefaults', 'dcf-parameters-defaults.js'],
  ['QgvV2', 'qgv-v2.js'], ['Qgv2Inputs', 'qgv2-inputs.js'], ['QgvScores', 'qgv-scores.js']]) globalThis[name] = require(path.join(W, file));
const V2 = globalThis.QgvV2, SQ = globalThis.Qgv2Inputs, QS = globalThis.QgvScores, CFG = globalThis.TypeConfigDefaults;
const VECTORS = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/type_pricefree_memberships_v1.json'), 'utf8'));
const near = (a, b, msg) => { for (const k of Object.keys(b)) assert.ok(Math.abs(a[k] - b[k]) <= 1e-12, msg + ' ' + k + ': ' + a[k] + ' vs ' + b[k]); };

test('vectors: QgvV2.pricefreeMemberships + typeAxisWeights reproduce the Python reference (qgv_v2.pricefree_memberships)', () => {
  assert.equal(VECTORS.config_version, CFG.config_version);
  for (const c of VECTORS.cases) {
    const mem = V2.pricefreeMemberships(c.metrics);
    assert.deepEqual(mem, c.memberships, c.name);
    const [w, reason, selected] = V2.typeAxisWeights(mem, CFG);
    assert.deepEqual([selected, reason], [c.selected_types, c.type_reason], c.name);near(w, c.type_weights, c.name);
  }
  assert.deepEqual([...V2.PRICEFREE_TYPE_METRICS], ['revenue_cagr_3y']);
});

function row(i, metrics) {
  const factors = {};Object.keys(V2.WEIGHTS.Q).forEach((k, j) => { factors[k] = 40 + ((i * 7 + j * 3) % 50); });Object.keys(V2.WEIGHTS.G).forEach((k, j) => { factors[k] = 35 + ((i * 11 + j * 5) % 55); });
  const ax = (a) => ({ score: V2.axisScore(factors, a).score }), ebit = 40 + i * 9, shares = 100 + i * 3;
  return { cik: String(2000000 + i).padStart(10, '0'), state: 'LIVE', reason_codes: [], sic: '3600', industry_group: 'manufacturing_industrial_tech', profile: 'GENERAL', fiscal_year_end: '2025-12-31', currency: 'USD',
    metrics, factors, axes: { Q: ax('Q'), G: ax('G') },
    v_inputs_v2: { currency: 'USD', ebit: { fy_value: ebit, fy_end: '2025-12-31' }, fcf: { fy_value: ebit * 0.8, fy_end: '2025-12-31' }, total_debt: { value: 80 + i, period_end: '2025-12-31' },
      cash_and_equivalents: { value: 20 + i, period_end: '2025-12-31' }, diluted_shares: { value: shares, period_end: '2025-12-31' }, ebit_per_share_history: [], revenue_cagr_3y: Object.hasOwn(metrics, 'revenue_cagr_3y') ? metrics.revenue_cagr_3y : null } };
}
// NASDAQ:NVDA is the TARGET company (id nvda); NASDAQ:TWIN has exactly the same published inputs and is not in the TARGET.
function twins(metrics, { targetRow = true, types = null, priced = true } = {}) {
  const records = {};for (let i = 1; i <= 12; i++) records['NYSE:SYN' + i] = row(i, { revenue_cagr_3y: 0.05 });
  const twin = row(20, metrics);
  records['NASDAQ:NVDA'] = { ...structuredClone(twin), cik: '0001045810' };records['NASDAQ:TWIN'] = { ...structuredClone(twin), cik: '0009999999' };
  const inputs = SQ.fromInputs(SQ.light({ kind: 'SEC_QGV2', as_of: '2026-10-17T00:00:00Z', records, target: targetRow ? { nvda: structuredClone(records['NASDAQ:NVDA']) } : {} }));
  const quotes = {};if (priced) for (const code of Object.keys(inputs.records)) quotes[code] = { price: 100, currency: 'USD' };
  const screens = { [SQ.FILE]: inputs };if (types) screens['company-types-pricefree.json'] = { data: { companies: { nvda: types } } };
  const out = QS.compute({ identities: [{ company_id: 'nvda', ticker: 'NVDA' }, { company_id: 'twin', ticker: 'TWIN' }], publicScreens: screens, quotes });
  return { nvda: out.rows.nvda, twin: out.rows.twin };
}
const LIVE = (growth) => ({ state: growth === null ? 'NOT_AVAILABLE' : 'LIVE', config_version: growth === null ? null : 'type_config/1', source_hashes: {}, memberships: { growth, quality: null, cyclical: null, defensive: null } });

for (const [label, metrics, selected, reason] of [['growth 1.0 (CAGR 25%)', { revenue_cagr_3y: 0.25 }, ['growth'], null], ['growth 0.4 (CAGR 14%)', { revenue_cagr_3y: 0.14 }, ['growth'], null],
  ['growth 0.2 < 0.3 (CAGR 12%)', { revenue_cagr_3y: 0.12 }, [], 'NO_RECOGNIZED_TYPE'], ['CAGR not published', {}, [], 'TYPE_UNCONFIRMED']]) {
  for (const targetRow of [true, false]) test('same inputs, TARGET vs non-TARGET: identical type, weights, axes and total — ' + label + (targetRow ? '' : ' (no TARGET row: Universe code)'), () => {
    const g = Object.hasOwn(metrics, 'revenue_cagr_3y') ? Math.min(1, Math.max(0, (metrics.revenue_cagr_3y - 0.1) / 0.1)) : null;
    const { nvda, twin } = twins(metrics, { targetRow, types: LIVE(g) });
    assert.equal(nvda.code, targetRow ? 'TARGET:nvda' : 'NASDAQ:NVDA');assert.equal(twin.code, 'NASDAQ:TWIN');
    for (const r of [nvda, twin]) assert.deepEqual([r.v2.selected_types, r.v2.type_reason], [selected, reason], r.code);
    assert.deepEqual(nvda.v2.weights, twin.v2.weights);
    if (selected.length) near(twin.v2.weights, { Q: 30, G: 50, V: 20 }, 'growth weights for the non-TARGET twin');else near(twin.v2.weights, { Q: 34, G: 33, V: 33 }, 'unclassified');
    for (const k of ['q', 'g', 'v', 'total']) assert.equal(nvda.v2[k], twin.v2[k], k);
    assert.equal(typeof twin.v2.total, 'number');
  });
}

test('price-free: without any price the twins still get identical type weights (and a Q·G-only total)', () => {
  const { nvda, twin } = twins({ revenue_cagr_3y: 0.25 }, { priced: false, types: LIVE(1) });
  assert.equal(nvda.v2.v, null);assert.deepEqual(twin.v2.selected_types, ['growth']);
  assert.deepEqual(nvda.v2.weights, twin.v2.weights);assert.equal(nvda.v2.total, twin.v2.total);
});

test('company-types-pricefree.json (TARGET-only, display) no longer decides scoring weights', () => {
  // A contradicting or missing TARGET file row changes nothing: the row's own published metric decides.
  const base = twins({ revenue_cagr_3y: 0.25 }), contradicting = twins({ revenue_cagr_3y: 0.25 }, { types: LIVE(0) }), absent = twins({ revenue_cagr_3y: 0.05 }, { types: LIVE(1) });
  assert.deepEqual(contradicting.nvda.v2.weights, base.nvda.v2.weights);assert.deepEqual(contradicting.nvda.v2.selected_types, ['growth']);
  assert.deepEqual(absent.nvda.v2.selected_types, []);assert.equal(absent.nvda.v2.type_reason, 'NO_RECOGNIZED_TYPE');
  const src = fs.readFileSync(path.join(W, 'qgv-scores.js'), 'utf8');
  assert.ok(!src.includes("'company-types-pricefree.json',"), 'the accessor does not read the TARGET type file for weights');
});

test('price-dependent or unresolved type inputs in a row never produce a type (no invented rule)', () => {
  const { twin } = twins({ dividend_yield: 0.05, sector_marketcap_rank: 1, roic: 0.4 });
  assert.deepEqual(twin.v2.selected_types, []);assert.equal(twin.v2.type_reason, 'TYPE_UNCONFIRMED');
});
