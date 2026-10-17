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

// ---- Owner decision 2026-10-17 item 4: scope id in the device score basis; playbook growth on the same input and rule ----
test('the type-application scope id is one constant, recorded in the device score basis; calc_version and profile id unchanged', () => {
  assert.equal(V2.TYPE_SCOPE, VECTORS.type_scope);assert.match(V2.TYPE_SCOPE, /^qgv2-type-scope\/\d{4}-\d{2}-\d{2}\.\d+$/);
  assert.deepEqual([...V2.PRICEFREE_TYPE_METRICS], VECTORS.pricefree_type_metrics, 'a new metric list needs a new type_scope');
  const { nvda } = twins({ revenue_cagr_3y: 0.25 });assert.ok(nvda);
  const records = {};for (let i = 1; i <= 12; i++) records['NYSE:SYN' + i] = row(i, { revenue_cagr_3y: 0.15 });
  const inputs = SQ.fromInputs(SQ.light({ kind: 'SEC_QGV2', as_of: '2026-10-17T00:00:00Z', calc_version: 'qgv2-calc/2026-10-17.1', records: Object.fromEntries(Object.entries(records).map(([k, r]) => [k, { ...r, calc_version: 'qgv2-calc/2026-10-17.1' }])) }));
  const out = QS.compute({ identities: [{ company_id: 'syn1', ticker: 'SYN1' }], publicScreens: { [SQ.FILE]: inputs } });
  assert.equal(out.basis.type_scope, V2.TYPE_SCOPE);assert.equal(out.profile.type_scope, V2.TYPE_SCOPE);assert.ok(Object.isFrozen(out.basis));
  assert.equal(out.profile.id, 'qgv-v2/balanced/gate-on', 'profile id (V history key) is unchanged');
  assert.equal(inputs.calc_version, 'qgv2-calc/2026-10-17.1', 'the raw-metric calc_version is read as published, not replaced');
  assert.ok(QS.basisText(out, false).endsWith(' · 유형 범위 ' + V2.TYPE_SCOPE));assert.ok(QS.basisText(out, true).endsWith(' · type scope ' + V2.TYPE_SCOPE));
  assert.equal(QS.basis('v2', true).type_scope, V2.TYPE_SCOPE);
});

// playbook-screen.js loads its engine and config itself (node); no PlaybookEngine global, so the accessor's cyclical V basis stays as above.
const P = require(path.join(W, 'playbook-screen.js'));
const IDS = new Map([['NVDA', 'nvda'], ['TWIN', 'twin']]);
function universe(nvdaMetrics, { targetMetrics = nvdaMetrics, targetRow = true, calc = null, mismatch = false } = {}) {
  const stamp = (r) => (calc ? { ...r, calc_version: calc } : r), records = {};for (let i = 1; i <= 12; i++) records['NYSE:SYN' + i] = stamp(row(i, { revenue_cagr_3y: 0.05 }));
  records['NASDAQ:NVDA'] = stamp({ ...row(20, nvdaMetrics), cik: '0001045810' });records['NASDAQ:TWIN'] = stamp({ ...row(20, nvdaMetrics), cik: '0009999999' });
  const target = targetRow ? { nvda: { ...stamp({ ...row(20, targetMetrics), cik: '0001045810' }), ...(mismatch ? { calc_version: 'qgv2-calc/2026-01-01.1' } : {}) } } : {};
  return SQ.fromInputs(SQ.light({ kind: 'SEC_QGV2', as_of: '2026-10-17T00:00:00Z', ...(calc ? { calc_version: calc } : {}), records, target }));
}
const growthOf = (symbol, screens) => P.factsFor(symbol, { idByTicker: IDS, screens, heldSymbols: [], interests: [] }).memberships.growth;
const scoreOf = (symbol, screens) => QS.typeMemberships({ identity: { company_id: IDS.get(symbol), ticker: symbol }, publicScreens: screens });

for (const c of VECTORS.cases.filter((x) => Object.keys(x.metrics).every((k) => k === 'revenue_cagr_3y')))
  test('playbook growth = score-side membership for the same input — ' + c.name, () => {
    const screens = { [SQ.FILE]: universe(c.metrics) };
    const out = QS.compute({ identities: [{ company_id: 'nvda', ticker: 'NVDA' }, { company_id: 'twin', ticker: 'TWIN' }], publicScreens: screens });
    for (const symbol of ['NVDA', 'TWIN']) {
      const score = scoreOf(symbol, screens), playbook = growthOf(symbol, screens), want = c.memberships.growth;
      assert.equal(score.code, out.rows[IDS.get(symbol)].code, 'the record the score uses');assert.equal(score.type_scope, V2.TYPE_SCOPE);
      assert.equal(score.memberships.growth, want, symbol + ' score side');assert.equal(playbook, want, symbol + ' playbook');
      if (want === null) assert.notEqual(playbook, 0, 'NA stays NA, never 0');
      assert.equal(out.rows[IDS.get(symbol)].v2.selected_types.includes('growth'), want !== null && want >= 0.3, 'the score selects growth from the same membership');
    }
  });

test('playbook growth reads the record the score uses (TARGET row when it has data), not another row or the TARGET-only file', () => {
  // The TARGET row (fresher) and the Universe row differ: the score and the playbook both use the TARGET row for NVDA.
  const screens = { [SQ.FILE]: universe({ revenue_cagr_3y: 0.11 }, { targetMetrics: { revenue_cagr_3y: 0.2 } }), 'company-types-pricefree.json': { data: { companies: { nvda: LIVE(0) } } } };
  assert.equal(scoreOf('NVDA', screens).code, 'TARGET:nvda');assert.equal(scoreOf('NVDA', screens).memberships.growth, 1);
  assert.equal(growthOf('NVDA', screens), 1, 'a contradicting company-types-pricefree.json row is not read');
  const universeOnly = { [SQ.FILE]: universe({ revenue_cagr_3y: 0.15 }, { targetRow: false }) };
  assert.equal(scoreOf('NVDA', universeOnly).code, 'NASDAQ:NVDA');assert.ok(Math.abs(growthOf('NVDA', universeOnly) - 0.5) < 1e-12);
  // A non-TARGET company gets growth from the same rule (before: NA, the TARGET-only file had no row for it).
  assert.ok(Math.abs(growthOf('TWIN', universeOnly) - 0.5) < 1e-12);
  // No v2 record for the symbol, or no QgvScores on the page: NA (null), never 0.
  assert.equal(growthOf('NONE', universeOnly), null);
  const saved = globalThis.QgvScores;try { delete globalThis.QgvScores;assert.equal(growthOf('TWIN', universeOnly), null); } finally { globalThis.QgvScores = saved; }
});

test('a row of another calc_version: no score and no playbook growth (NA, never 0)', () => {
  const screens = { [SQ.FILE]: universe({ revenue_cagr_3y: 0.25 }, { calc: 'qgv2-calc/2026-10-17.1', mismatch: true }) };
  assert.equal(screens[SQ.FILE].records['TARGET:nvda'].calc_version_mismatch, true);
  const out = QS.compute({ identities: [{ company_id: 'nvda', ticker: 'NVDA' }], publicScreens: screens });
  assert.equal(out.rows.nvda.code, 'TARGET:nvda');assert.equal(out.rows.nvda.v2.total, null);
  assert.equal(scoreOf('NVDA', screens), null);assert.equal(growthOf('NVDA', screens), null);
  assert.equal(growthOf('TWIN', screens), 1, 'same-version rows are unaffected');
});

test('the other playbook type rules (quality / cyclical / defensive v0) are unchanged by the growth link', () => {
  for (const sic of ['3674', '2834', '7372']) for (const cagr of [0.05, 0.25]) {
    const base = row(20, { revenue_cagr_3y: cagr, revenue_volatility_5y_rank_pct: 20, roic_avg_3y: 0.2, operating_margin_std_5y_pp: 2, net_debt_to_ebitda: 1 });
    const records = { 'NASDAQ:TWIN': { ...base, sic } };for (let i = 1; i <= 12; i++) records['NYSE:SYN' + i] = row(i, { revenue_cagr_3y: 0.05 });
    const screens = { [SQ.FILE]: SQ.fromInputs(SQ.light({ kind: 'SEC_QGV2', as_of: '2026-10-17T00:00:00Z', records, target: {} })) };
    const facts = P.factsFor('TWIN', { idByTicker: IDS, screens, heldSymbols: [], interests: [] });
    const v0 = P.playbookTypeFacts(SQ.normalize(screens[SQ.FILE].records['NASDAQ:TWIN'], false), {}, null, facts.sector);
    for (const t of ['quality', 'cyclical', 'defensive']) assert.equal(facts.memberships[t], v0.memberships[t], sic + ' ' + t);
    assert.deepEqual(facts.type_classification, v0.classification);
    assert.equal(facts.memberships.growth, cagr >= 0.2 ? 1 : 0);
    for (const t of ['value', 'dividend', 'leader']) assert.equal(facts.memberships[t] ?? null, null, t + ' is never evaluated');
  }
});
