'use strict';
// Sector QGV (owner 2026-11-06; feature 2.2): web_app/sector-qgv.js against the proposed sector-qgv-bundle/1 and the v0 presets.
//  - sector-qgv-default/0.1.0 equals the design §5.1 axis table and §5.2 factor table (per-mille effective weights), state
//    draft / initial; Lynch tags carry no weight.
//  - The design's §9 checks that belong to the roll-up: role budget kept when a factor is added; Q/G/V 80/60/40 with axis bp
//    3000/2000/5000 → 56; a 0-weight axis or role is not required; a bank override does not reach insurance / asset managers /
//    REITs; models are never mixed; 100 companies with 90 per factor but 80 in common → 80 %; a changed snapshot or population
//    changes the key; only the latest request is kept (screen); identical exact alias (PER = E/P) is one factor.
//  - Strict missing: a required factor without a score leaves the axis and total unscored with its reason, never 0.
const assert = require('node:assert/strict');
const S = require('../src/investment_system/product/web_app/sector-qgv.js');
const X = require('./web_app_sector_qgv_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const R = S.validate(X.bundle()), v = R.value, BP = 10000;
const ctx = (s, t) => ({ sector_id: s, template_id: t, key: s + '|' + t });
const tree = (k) => JSON.parse(JSON.stringify(S.treeFor(v, null, k)));

ok('bundle valid; preset set sector-qgv-default/0.1.0, draft · initial, strict, no gate', () => {
  assert.equal(R.ok, true, JSON.stringify(R)); assert.equal(R.version, '0.1.0');
  for (const p of v.presets) { assert.equal(p.state, 'draft'); assert.equal(p.validation_state, 'initial'); assert.equal(p.missing_policy, 'STRICT'); assert.equal(p.gate_policy, 'NONE'); }
  assert.equal(v.presets.length, 15); assert.equal(v.sectors.length, 10);
});
ok('v0 axis weights = design §5.1 (each row 100 %)', () => {
  const want = { CONSUMER_DISCRETIONARY: [30, 25, 45], CONSUMER_STAPLES: [35, 15, 50], ENERGY: [35, 15, 50], FINANCIALS: [40, 15, 45], HEALTH_CARE: [35, 25, 40],
    INDUSTRIALS: [35, 20, 45], INFORMATION_TECHNOLOGY: [30, 25, 45], MATERIALS: [35, 15, 50], TELECOM_SERVICES: [40, 15, 45], UTILITIES: [40, 10, 50] };
  for (const p of v.presets) assert.deepEqual([p.axis_weights.Q, p.axis_weights.G, p.axis_weights.V].map((x) => x / 100), want[p.sector_id], p.sector_id + ' ' + p.template_id);
});
ok('v0 factor effective weights inside each axis = design §5.2 (to 0.1 %)', () => {
  const inAxis = (k, a) => Object.fromEntries(S.effective(tree(k)).filter((e) => e.axis === a).map((e) => [e.factor_id, Math.round(e.share / (tree(k).axis_weights[a] / BP) * 1000) / 10]));
  assert.deepEqual(inAxis('ENERGY|GENERAL', 'Q'), { Q01_OPERATING_MARGIN: 40, Q05_ACCRUALS: 30, Q06_DEBT_TO_ASSETS: 30 });
  assert.deepEqual(inAxis('ENERGY|GENERAL', 'G'), { G02_SALES_CAGR3: 60, G06_ROA_CHANGE3: 40 });
  const V = { CONSUMER_DISCRETIONARY: { V_EARNINGS_YIELD: 35, V_CFO_YIELD: 40, V06_FCF_TO_MCAP: 25 }, CONSUMER_STAPLES: { V_EARNINGS_YIELD: 35, V_CFO_YIELD: 35, V_DIVIDEND_YIELD_TTM: 30 },
    ENERGY: { V_EARNINGS_YIELD: 40, V_CFO_YIELD: 30, V_EBITDA_TO_EV: 30 }, HEALTH_CARE: { V_EARNINGS_YIELD: 40, V_CFO_YIELD: 40, V_SALES_TO_MCAP: 20 },
    INDUSTRIALS: { V_EARNINGS_YIELD: 35, V_CFO_YIELD: 35, V_EBITDA_TO_EV: 30 }, INFORMATION_TECHNOLOGY: { V_EARNINGS_YIELD: 30, V_CFO_YIELD: 40, V_SALES_TO_EV: 30 },
    MATERIALS: { V_EARNINGS_YIELD: 40, V_CFO_YIELD: 30, V_EBITDA_TO_EV: 30 }, TELECOM_SERVICES: { V_EARNINGS_YIELD: 40, V_CFO_YIELD: 40, V_EBITDA_TO_EV: 20 },
    UTILITIES: { V_EARNINGS_YIELD: 30, V_CFO_YIELD: 40, V_EBITDA_TO_EV: 30 } };
  for (const [s, want] of Object.entries(V)) assert.deepEqual(inAxis(s + '|GENERAL', 'V'), want, s);
  for (const t of ['BANK', 'INSURANCE', 'BROKER', 'MORTGAGE_REIT']) {
    assert.deepEqual(inAxis('FINANCIALS|' + t, 'Q'), { Q_ROA: 35, Q_ROE_COMMON: 35, Q14_COMMON_EQUITY_TO_ASSETS: 30 }, t);
    assert.deepEqual(inAxis('FINANCIALS|' + t, 'G'), { G13_COMMON_BPS_CAGR3: 60, G06_ROA_CHANGE3: 40 }, t);
    assert.deepEqual(inAxis('FINANCIALS|' + t, 'V'), { V_EARNINGS_YIELD: 60, V_BOOK_YIELD: 40 }, t);
  }
  assert.deepEqual(inAxis('FINANCIALS|ASSET_MANAGER', 'Q'), { Q01_OPERATING_MARGIN: 40, Q05_ACCRUALS: 30, Q06_DEBT_TO_ASSETS: 30 });
  assert.deepEqual(inAxis('FINANCIALS|ASSET_MANAGER', 'V'), { V_EARNINGS_YIELD: 60, V_BOOK_YIELD: 40 });
  assert.deepEqual(inAxis('FINANCIALS|EQUITY_REIT', 'Q'), { Q_CFO_TO_AVG_ASSETS: 40, Q_INTEREST_COVERAGE: 30, Q06_DEBT_TO_ASSETS: 30 });
  assert.deepEqual(inAxis('FINANCIALS|EQUITY_REIT', 'G'), { G02_SALES_CAGR3: 60, G14_CFO_AVG_ASSETS_CHANGE3: 40 });
  assert.deepEqual(inAxis('FINANCIALS|EQUITY_REIT', 'V'), { V_FFO_TO_MCAP: 50, V_CFO_YIELD: 30, V_DIVIDEND_YIELD_TTM: 20 });
});
ok('roll-up: Q/G/V = 80/60/40 with axis bp 3000/2000/5000 → 56 (design §9)', () => {
  const t = { axis_weights: { Q: 3000, G: 2000, V: 5000 }, roles: { Q: [{ role: 'profitability', weight_bp: BP, factors: [{ factor_id: 'Q01_OPERATING_MARGIN', weight_bp: BP }] }],
    G: [{ role: 'growth', weight_bp: BP, factors: [{ factor_id: 'G02_SALES_CAGR3', weight_bp: BP }] }], V: [{ role: 'earnings', weight_bp: BP, factors: [{ factor_id: 'V_EARNINGS_YIELD', weight_bp: BP }] }] } };
  const b = JSON.parse(JSON.stringify(X.bundle())), id = b.companies[0].company_id;
  b.scores.Q01_OPERATING_MARGIN[id] = { score: 80, status: 'VALID' }; b.scores.G02_SALES_CAGR3[id] = { score: 60, status: 'VALID' }; b.scores.V_EARNINGS_YIELD[id] = { score: 40, status: 'VALID' };
  const w = S.validate(b).value, c = b.companies[0], k = c.sector_id + '|' + c.template_id;
  const cfg = { ...S.emptyConfig(w), overrides: { [k]: t } };
  assert.equal(S.validateConfig(cfg, w).ok, true);
  const row = S.compute(w, cfg).rows.find((r) => r.company_id === id);
  assert.ok(Math.abs(row.total - 56) < 1e-9, String(row.total));
});
ok('strict: a required factor without a score leaves the axis and total unscored with its reason; never 0', () => {
  const res = S.compute(v, S.emptyConfig(v));
  const miss = res.rows.find((r) => r.total === null && r.reason === 'AXIS_UNSCORED');
  const ax = S.AXES.find((a) => miss[a] === null);
  assert.ok(S.MISSING.includes(miss.why[ax]), miss.why[ax]); assert.ok(miss.why[ax + '_factor']);
  assert.equal(miss.rank, null);
  for (const r of res.rows) if (r.total === null) for (const a of S.AXES) assert.notEqual(r[a], 0);
  const unmapped = res.rows.filter((r) => r.reason === 'MAPPING_UNRESOLVED');
  assert.equal(unmapped.length, 3, 'unmapped companies stay in the denominator'); assert.equal(res.denominator, v.companies.length);
  const ins = res.rows.filter((r) => r.template_id === 'INSURANCE');
  assert.ok(ins.every((r) => r.total === null && r.why.Q === 'PEER_SAMPLE_SMALL'), 'small peer group: unscored, not 0');
});
ok('a 0-weight axis or role is not required: the other active axes give the total, the axis says excluded', () => {
  const k = 'ENERGY|GENERAL', t = S.setAxisWeights(tree(k), { Q: 5000, G: 0, V: 5000 });
  const cfg = { ...S.emptyConfig(v), overrides: { [k]: t } };
  assert.equal(S.validateConfig(cfg, v).ok, true);
  const b = JSON.parse(JSON.stringify(X.bundle())), ids = b.companies.filter((c) => c.sector_id === 'ENERGY').map((c) => c.company_id);
  for (const id of ids) b.scores.G02_SALES_CAGR3[id] = { score: null, status: 'MISSING_INPUT' };
  const w = S.validate(b).value, res = S.compute(w, cfg);
  const rows = res.rows.filter((r) => ids.includes(r.company_id));
  assert.ok(rows.some((r) => r.total !== null), 'G missing does not block when G weight is 0');
  for (const r of rows) { assert.equal(r.G, null); assert.equal(r.why.G, 'USER_EXCLUDED'); assert.deepEqual(r.excluded, ['G']); }
  const t2 = S.setRoleWeight(S.setRoleWeight(tree(k), 'G', 'growth', 0), 'G', 'profitability_change', BP);
  const res2 = S.compute(w, { ...S.emptyConfig(w), overrides: { [k]: t2 } });
  assert.ok(res2.rows.filter((r) => ids.includes(r.company_id)).some((r) => r.G !== null), 'a 0-weight role is not required');
});
ok('edits: adding a factor keeps the role budget; removing re-splits; replace keeps the slot; duplicates refused', () => {
  const k = 'ENERGY|GENERAL';
  const t = S.addFactor(tree(k), v, 'Q', 'Q_ROA');
  const prof = t.roles.Q.find((r) => r.role === 'profitability');
  assert.equal(prof.weight_bp, 4000); assert.deepEqual(prof.factors.map((f) => f.weight_bp), [5000, 5000]);
  assert.equal(S.checkTree(t, ctx('ENERGY', 'GENERAL'), v), null);
  const eff = Object.fromEntries(S.effective(t).filter((e) => e.axis === 'Q').map((e) => [e.factor_id, e.share]));
  assert.ok(Math.abs(eff.Q01_OPERATING_MARGIN + eff.Q_ROA - 0.35 * 0.4) < 1e-12, 'role total kept: 20 % + 20 % of Q, not 80 %');
  const back = S.removeFactor(t, 'Q', 'Q_ROA'); assert.deepEqual(back.roles.Q.find((r) => r.role === 'profitability').factors, [{ factor_id: 'Q01_OPERATING_MARGIN', weight_bp: BP }]);
  const rep = S.replaceFactor(tree(k), v, 'V', 'V_EBITDA_TO_EV', 'V_BOOK_YIELD');
  assert.deepEqual(rep.roles.V.find((r) => r.role === 'other').factors, [{ factor_id: 'V_BOOK_YIELD', weight_bp: BP }]);
  assert.throws(() => S.addFactor(tree(k), v, 'V', 'V_EARNINGS_YIELD'), /DUPLICATE/);
  assert.throws(() => S.replaceFactor(tree(k), v, 'V', 'V_EARNINGS_YIELD', 'V_CFO_YIELD'), /ROLE_DIFFERS/);
  const added = S.addFactor(tree(k), v, 'Q', 'Q_INTEREST_COVERAGE');
  assert.equal(added.roles.Q.find((r) => r.role === 'coverage').weight_bp, 0, 'a new role starts at 0, never silently raised');
  assert.equal(S.split(3).join(','), '3334,3333,3333');
});
ok('PER and E/P are one factor (aliases); a pending factor and a template-unfit factor are not selectable', () => {
  const C = ctx('ENERGY', 'GENERAL'), t = tree(C.key);
  const per = S.catalog(v, C, t, 'V', 'per'), ep = S.catalog(v, C, t, 'V', 'E/P');
  assert.ok(per.length >= 1 && per[0].factor.factor_id === 'V_EARNINGS_YIELD' && ep[0].factor.factor_id === 'V_EARNINGS_YIELD');
  const row = (id, c = C) => S.catalog(v, c, S.treeFor(v, null, c.key), 'V').find((r) => r.factor.factor_id === id);
  assert.equal(row('V_FWD_EARNINGS_YIELD').state, 'PENDING'); assert.equal(row('V_FWD_EARNINGS_YIELD').selectable, false);
  assert.equal(row('V_TBV_YIELD').state, 'NOT_FIT'); assert.equal(row('V_TBV_YIELD').selectable, false);
  const ev = row('V_EBITDA_TO_EV'); assert.equal(ev.base, true); assert.equal(ev.selected, true);
  assert.ok(['READY', 'PARTIAL'].includes(row('V_BOOK_YIELD').state) && row('V_BOOK_YIELD').base === false);
  const it = row('V_SALES_TO_EV', ctx('INFORMATION_TECHNOLOGY', 'GENERAL'));
  assert.equal(it.recommended[0].reason, '정보기술의 매출가치 비교에 적합'); assert.equal(it.recommended[0].evidence_level, 'BOOK_SECTOR');
  assert.equal(S.checkTree(S.setFactorWeight(tree('FINANCIALS|BANK'), 'V', 'V_BOOK_YIELD', 9000), ctx('FINANCIALS', 'BANK'), v).code, 'FACTOR_SUM');
  const bad = JSON.parse(JSON.stringify(tree('ENERGY|GENERAL'))); bad.roles.V[0].factors[0].factor_id = 'V_FWD_EARNINGS_YIELD';
  assert.equal(S.checkTree(bad, C, v).code, 'FACTOR_PENDING');
});
ok('a bank override reaches no other template; "전체 적용" is an explicit copy that skips unfit contexts', () => {
  const B = ctx('FINANCIALS', 'BANK'), t = S.replaceFactor(tree(B.key), v, 'V', 'V_BOOK_YIELD', 'V_TBV_YIELD');
  const one = S.applyEdit(S.emptyConfig(v), v, B, t, 'CONTEXT').config;
  assert.deepEqual(Object.keys(one.overrides), ['FINANCIALS|BANK']);
  for (const k of ['FINANCIALS|INSURANCE', 'FINANCIALS|ASSET_MANAGER', 'FINANCIALS|EQUITY_REIT']) assert.deepEqual(S.treeFor(v, one, k), S.treeFor(v, null, k), k);
  const all = S.applyEdit(S.emptyConfig(v), v, B, t, 'ALL');
  assert.ok(all.skipped.includes('ENERGY|GENERAL') && all.skipped.includes('FINANCIALS|EQUITY_REIT'), 'P/TBV is not for general companies or REITs');
  assert.ok(Object.keys(all.config.overrides).includes('FINANCIALS|INSURANCE'));
});
ok('Lynch tags change nothing: scores, weights and order equal when only the tags differ', () => {
  const b = JSON.parse(JSON.stringify(X.bundle())); for (const c of b.companies) c.lynch_tags = ['회생', '자산 가치'];
  const a = S.compute(v, S.emptyConfig(v)), w = S.validate(b).value, c = S.compute(w, S.emptyConfig(w));
  assert.deepEqual(a.rows.map((r) => [r.company_id, r.total, r.rank]), c.rows.map((r) => [r.company_id, r.total, r.rank]));
});
ok('coverage counts on the original population: 100 companies, 90 per factor, 80 in common → 80 %', () => {
  const b = JSON.parse(JSON.stringify(X.bundle()));
  b.companies = Array.from({ length: 100 }, (_, i) => ({ company_id: 'C' + String(i).padStart(3, '0'), universe_code: null, sector_id: 'ENERGY', template_id: 'GENERAL', mapping_status: 'MAPPED', lynch_tags: [] }));
  for (const [fid, cells] of Object.entries(b.scores)) { const out = {}; b.companies.forEach((c, i) => { out[c.company_id] = { score: 50, status: 'VALID' }; }); b.scores[fid] = out; }
  const k = 'ENERGY|GENERAL', t = { axis_weights: { Q: 5000, G: 0, V: 5000 }, roles: { Q: [{ role: 'profitability', weight_bp: BP, factors: [{ factor_id: 'Q01_OPERATING_MARGIN', weight_bp: BP }] }], G: [],
    V: [{ role: 'earnings', weight_bp: BP, factors: [{ factor_id: 'V_EARNINGS_YIELD', weight_bp: BP }] }] } };
  b.companies.forEach((c, i) => { if (i < 10) b.scores.Q01_OPERATING_MARGIN[c.company_id] = { score: null, status: 'MISSING_INPUT' }; if (i >= 10 && i < 20) b.scores.V_EARNINGS_YIELD[c.company_id] = { score: null, status: 'MISSING_INPUT' }; });
  const w = S.validate(b); assert.equal(w.ok, true, JSON.stringify(w));
  const res = S.compute(w.value, { ...S.emptyConfig(w.value), overrides: { [k]: t } });
  assert.equal(res.denominator, 100); assert.equal(res.axes.Q, 90); assert.equal(res.axes.V, 90); assert.equal(res.computed, 80, '80 %, not 90 %');
});
ok('models never mixed; key carries snapshot, population, engine, normalization, mapping, preset version and config', () => {
  const base = S.compute(v, S.emptyConfig(v), { model: 'DEFAULT' }), mine = S.compute(v, S.emptyConfig(v));
  assert.notEqual(base.key, mine.key); assert.match(base.key, /~DEFAULT~/);
  const d = S.compare(base, mine); assert.equal(d.rows.length, v.companies.length);
  const b2 = JSON.parse(JSON.stringify(X.bundle())); b2.snapshot.universe_version = 'syn-2'; const w2 = S.validate(b2).value;
  assert.throws(() => S.compare(S.compute(w2, S.emptyConfig(w2)), mine), /COMPARE_MISMATCH/);
  for (const f of ['snapshot_id', 'universe_id', 'universe_version', 'engine_version', 'normalization_version', 'mapping_version']) {
    const b3 = JSON.parse(JSON.stringify(X.bundle())); b3.snapshot[f] = 'x'; const w3 = S.validate(b3).value; assert.notEqual(S.key(w3, S.emptyConfig(w3)), S.key(v, S.emptyConfig(v)), f); }
  const k = 'ENERGY|GENERAL', c2 = { ...S.emptyConfig(v), overrides: { [k]: S.setAxisWeights(tree(k), { Q: 4000, G: 1500, V: 4500 }) } };
  assert.notEqual(S.key(v, c2), S.key(v, S.emptyConfig(v)));
});
ok('compare: ranks among companies computed in both told apart from dropping out', () => {
  const k = 'ENERGY|GENERAL', t = S.addFactor(tree(k), v, 'V', 'V_BOOK_YIELD');
  const cfg = S.applyEdit(S.emptyConfig(v), v, ctx('ENERGY', 'GENERAL'), S.setRoleWeight(S.setRoleWeight(t, 'V', 'other', 3000), 'V', 'earnings', 4000), 'CONTEXT').config;
  assert.equal(S.validateConfig(cfg, v).ok, true, JSON.stringify(S.validateConfig(cfg, v)));
  const before = S.compute(v, S.emptyConfig(v)), after = S.compute(v, cfg), d = S.compare(before, after);
  assert.ok(d.common > 0 && d.common <= Math.min(before.computed, after.computed));
  for (const r of d.rows) if (r.before.total !== null && r.after.total !== null) { assert.ok(Number.isInteger(r.common_before) && Number.isInteger(r.common_after)); } else assert.equal(r.common_before, null);
});
ok('config: a newer base version is reported, never rewritten; refusals of the bundle', () => {
  const c = { ...S.emptyConfig(v), version: '0.0.9' }; assert.equal(S.validateConfig(c, v).code, 'BASE_VERSION_DIFFERS'); assert.equal(S.validateConfig(c).ok, true, 'shape only without a bundle');
  const cases = [
    ['SCHEMA_VERSION', (b) => { b.schema = 'sector-qgv-bundle/2'; }], ['AXIS_SUM', (b) => { b.presets[0].axis_weights.Q += 1; }],
    ['ROLE_SUM', (b) => { b.presets[0].roles.Q[0].weight_bp -= 1; }], ['FACTOR_SUM', (b) => { b.presets[0].roles.V[1].factors[0].weight_bp -= 1; }],
    ['BP_INVALID', (b) => { b.presets[0].axis_weights.Q = 3000.5; }], ['BP_INVALID', (b) => { b.presets[0].axis_weights.Q = -1; }],
    ['MATRIX_INCOMPLETE', (b) => { delete b.scores.V_CFO_YIELD[b.companies[0].company_id]; }], ['SCORE_WITH_MISSING', (b) => { const id = b.companies[0].company_id; b.scores.V_CFO_YIELD[id] = { score: 0, status: 'MISSING_INPUT' }; }],
    ['SCORE_INVALID', (b) => { const id = b.companies[0].company_id; b.scores.V_CFO_YIELD[id] = { score: 101, status: 'VALID' }; }], ['FACTOR_PENDING', (b) => { b.scores.V_PEG_FWD = {}; }],
    ['PRESET_VERSION_MIXED', (b) => { b.presets[1].version = '0.2.0'; }], ['GATE_POLICY_UNSUPPORTED', (b) => { b.presets[0].gate_policy = 'VALUE_TRAP'; }],
    ['NOT_APPLICABLE', (b) => { b.presets[1].roles.V[2].factors[0].factor_id = 'V_TBV_YIELD'; }],
  ];
  for (const [code, fn] of cases) { const b = JSON.parse(JSON.stringify(X.bundle())); fn(b); const r = S.validate(b); assert.equal(r.ok, false, code); assert.equal(r.code, code, code + ' got ' + r.code + ' ' + r.path); }
});
ok('preview(): a Promise of before / after / compare; source() is NONE (no request)', async () => {
  const p = S.preview(v, S.emptyConfig(v), S.emptyConfig(v)); assert.ok(p && typeof p.then === 'function');
  const out = await p; assert.equal(out.after.computed, out.before.computed);
  const s = await S.source(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null);
});
console.log('ok ' + n + ' checks');
