'use strict';
// D12 (owner decision 2026-10-19: '공식 리더보드는 Universe 전체 평가를 기준으로 한다. 기존 TARGET 19개는 별도 목록·필터로 유지한다.')
// in Node, over SYNTHETIC data only (tools/qgv_v2_fixture.js, made-up device prices):
// - QgvScores.universeIdentities: one row per security (a TARGET identity whose ticker is a Universe code IS that code), every
//   Universe code covered once, TARGET outside the Universe listed apart;
// - QgvScores.compute({official}): the same engine values as without it (no formula, weight or engine change), official ranks only
//   over Universe rows with V (D11), TARGET outside the Universe never ranked nor in the QG list, Q·G-only rows in the QG list;
// - QgvScores.pageResult: the ONE shared result carries that split; rowOf / codeRow / vCoverage read the merged row;
// - QgvScores.modelPortfolios: N10 / N15 / N20 = the first N rows of the official order that pass the approved eligibility
//   (official rank, Q·G·V all present, no value-trap gate, financial safety, at most 4 per industry subgroup, PLAYBOOK §16 limits per N
//   at equal weight: shortfall weight + cause, never filled or rescaled), the R-C tier weights on N15 as a check only, and the
//   same-issuer summed weight (recommendation, selection unchanged);
// - PlaybookScreen.candidateRanking over the official result: the candidate rank is the official rank.
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets'), F = require('./qgv_v2_fixture.js');
for (const [name, file] of [['EnginePreview', 'engine-preview.js'], ['ProfileDefaults', 'profile-defaults.js'], ['TypeConfigDefaults', 'type-config-defaults.js'], ['DcfParametersDefaults', 'dcf-parameters-defaults.js'],
  ['PlaybookConfigDefaults', 'playbook-config-defaults.js'], ['PlaybookEngine', 'playbook-engine.js'], ['QgvV2', 'qgv-v2.js'], ['Qgv2Inputs', 'qgv2-inputs.js'], ['QgvScores', 'qgv-scores.js']]) globalThis[name] = require(path.join(W, file));
const QS = globalThis.QgvScores, QI = globalThis.Qgv2Inputs, V2 = globalThis.QgvV2, P = require(path.join(W, 'playbook-screen.js'));
const finite = (v) => typeof v === 'number' && Number.isFinite(v);

// The 19 TARGET identities as the app builds them (watchlist.js ids); in this fixture ASML has no Universe code (outside), and
// 8035 / 042700 have none either. TARGET amd is made weak in Q so the approved value-trap gate fires on it.
const TARGETS = [['ASML', 'asml'], ['LRCX', 'lrcx'], ['KLAC', 'klac'], ['8035', 'tokyo_electron'], ['042700', 'hanmi'], ['NVDA', 'nvda'], ['AMD', 'amd'], ['AVGO', 'avgo'], ['QCOM', 'qcom'], ['INTC', 'intc'],
  ['MSFT', 'msft'], ['GOOGL', 'googl'], ['AMZN', 'amzn'], ['RTX', 'rtx'], ['SYK', 'stry'], ['ETN', 'etn'], ['HUBB', 'hubb'], ['GEV', 'gev'], ['ROK', 'rok']].map(([ticker, company_id]) => ({ company_id, ticker }));
function payload() {
  const p = F.payload(), amd = p.target.amd;
  for (const k of Object.keys(V2.WEIGHTS.Q)) amd.factors[k] = 1;
  amd.axes.Q = { ...amd.axes.Q, score: V2.axisScore(amd.factors, 'Q').score };
  // Synthetic financial-safety metrics (made-up): every 5th row fails (net debt / EBITDA 3.5), every 7th has no interest coverage (NA).
  Object.values(p.records).forEach((r, i) => { if (r.state === 'LIVE') r.metrics = { ...r.metrics, net_debt_to_ebitda: i % 5 === 4 ? 3.5 : 1, ...(i % 7 === 6 ? {} : { interest_coverage: 12 }) }; });
  for (const r of Object.values(p.target)) if (r.state === 'LIVE') r.metrics = { ...r.metrics, net_debt_to_ebitda: 1, interest_coverage: 12 };
  return p;
}
let inputs = null, quotes = null;
const win = () => ({ PrivateSubsetView: { prices: () => new Map(Object.entries(F.quotes())), priceBasis: () => ({ source: 'SYNTHETIC_TEST', read_id: 'synthetic-d12', acquired_at: null }) } });
test.before(async () => { inputs = QI.fromInputs(QI.light(payload())); quotes = await QS.collectQuotes(win(), { identities: TARGETS, v2Inputs: inputs }); });
const codesOf = () => Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).sort();

test('universeIdentities: one row per security, every Universe code once, TARGET outside apart', () => {
  const U = QS.universeIdentities(inputs, TARGETS), codes = codesOf();
  assert.equal(U.codes, codes.length);
  assert.deepEqual(Object.keys(U.by_code).sort(), codes, 'every Universe code stands for exactly one row');
  assert.equal(new Set(Object.values(U.by_code)).size, codes.length, 'no row stands for two codes');
  assert.equal(U.identities.length, codes.length + U.outside.length, 'rows = Universe codes + TARGET outside');
  assert.equal(new Set(U.identities.map((c) => c.company_id)).size, U.identities.length);
  // Dedupe: no Universe code of a TARGET company is a second row; the TARGET row stands for it.
  for (const { company_id, code } of U.target_in_universe) { assert.equal(U.by_code[code], company_id);assert.ok(!U.identities.some((c) => c.company_id === code), code + ' is not a second row'); }
  assert.deepEqual(U.target_in_universe.map((x) => x.company_id).sort(), Object.keys(F.TICKERS).sort(), 'the 16 fixture TARGET companies with a code');
  assert.deepEqual([...U.outside].sort(), ['asml', 'hanmi', 'tokyo_electron'], 'TARGET without a Universe code');
  // The share-class sibling of a TARGET company (NASDAQ:GOOG next to TARGET googl = NASDAQ:GOOGL) stays its own Universe row.
  assert.equal(U.by_code['NASDAQ:GOOG'], 'NASDAQ:GOOG');
  assert.equal(QS.universeIdentities(null, TARGETS), null, 'no file, no split');
});

test('compute({official}): same engine values, ranks only over Universe rows with V, outside never ranked', () => {
  const U = QS.universeIdentities(inputs, TARGETS), A = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes, official: U }), B = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes });
  // Engine values unchanged by the split (display/rank only): every row's V, total, axes and factors are identical.
  for (const c of U.identities) {
    const a = A.rows[c.company_id].primary, b = B.rows[c.company_id].primary;
    for (const k of ['q', 'g', 'v', 'total', 'factors_available', 'value_trap_gate']) assert.ok(Object.is(a[k], b[k]), c.company_id + ' ' + k);
    assert.deepEqual(a.factors, b.factors, c.company_id + ' factors');assert.deepEqual(a.flags, b.flags, c.company_id + ' flags');
  }
  const rows = Object.values(A.rows), ranked = rows.filter((r) => Number.isInteger(r.rank)).sort((x, y) => x.rank - y.rank);
  assert.ok(ranked.length >= 5, 'synthetic prices give an official ranking: ' + ranked.length);
  assert.deepEqual(ranked.map((r) => r.rank), ranked.map((_, i) => i + 1), 'ranks 1..N');
  for (const r of ranked) { assert.ok(finite(r.primary.v) && finite(r.primary.total), r.company_id + ' ranked with V');assert.equal(typeof r.universe_code, 'string', r.company_id + ' is a Universe row'); }
  // Q·G-only totals: the QG list, never ranked (D11); the financial row and the unpriced gev.
  const qg = rows.filter((r) => r.qg_reference);
  for (const r of qg) { assert.equal(r.rank, null);assert.ok(finite(r.primary.total) && !finite(r.primary.v)); }
  assert.ok(qg.some((r) => r.company_id === 'NYSE:SYNF1') && qg.some((r) => r.company_id === 'gev'), 'financial and unpriced rows in the QG list');
  // TARGET outside the Universe: scored (asml has a total; its EUR V basis is unconfirmed), never ranked, never in the QG list, flagged outside.
  const asml = A.rows.asml;assert.ok(finite(asml.primary.total), 'asml is evaluated');assert.equal(asml.rank, null);assert.equal(asml.qg_reference, null);assert.equal(asml.outside_universe, true);assert.equal(asml.universe_code, null);
  assert.ok(Number.isInteger(B.rows.asml.rank) || B.rows.asml.qg_reference, 'without the split it would have joined an order (the case this guards)');
  // The value-trap gate row computed V and stays ranked (D11), with its flag.
  for (const r of rows.filter((x) => x.primary.value_trap_gate === true && finite(x.primary.v) && finite(x.primary.total) && x.universe_code)) assert.ok(Number.isInteger(r.rank), r.company_id + ' gate row ranked');
  // Counts of the result.
  assert.deepEqual([A.official.evaluated, A.official.codes, A.official.ranked, A.official.qg_reference, A.official.outside.sort()], [codesOf().length, codesOf().length, ranked.length, qg.length, ['asml', 'hanmi', 'tokyo_electron']]);
  // Before any price: no official rank; the Q·G totals are all in the QG list.
  const N = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes: {}, official: U });
  assert.equal(Object.values(N.rows).filter((r) => Number.isInteger(r.rank)).length, 0);assert.ok(Object.values(N.rows).filter((r) => r.qg_reference).length > 5);
});

test('pageResult: one shared result with the split; rowOf / codeRow / vCoverage read the merged row', async () => {
  QS.setPageIdentities(TARGETS);
  try {
    const R = await QS.pageResult(win(), { v2Inputs: inputs }), S = R.computed;
    assert.ok(S.official && R.official, 'the shared result carries the populations');
    assert.equal(Object.keys(S.rows).length, codesOf().length + 3, 'one row per security + TARGET outside');
    assert.equal(S.rows['NASDAQ:NVDA'], undefined, 'no second row for a TARGET company code');
    assert.equal(QS.rowOf(S, 'NASDAQ:NVDA'), S.rows.nvda);assert.equal(QS.codeRow(S, 'NASDAQ:NVDA'), S.rows.nvda);assert.equal(QS.codeRow(S, 'NYSE:SYNI1'), S.rows['NYSE:SYNI1']);
    assert.equal(QS.codeRow(S, 'NASDAQ:ASML'), null);assert.equal(QS.rowOf(S, 'asml'), S.rows.asml);
    // The same result twice (memo): the same object, so every screen reads the same V, total and rank.
    assert.equal(await QS.pageResult(win(), { v2Inputs: inputs }), R);
    const cov = QS.vCoverage(R, inputs), withV = codesOf().filter((c) => finite(QS.codeRow(S, c)?.primary.v)).length;
    assert.equal(cov.v.full, withV, 'V panel counts the merged rows of the same result');
    const ranked = Object.values(S.rows).filter((r) => Number.isInteger(r.rank)).length;
    assert.equal(ranked, codesOf().filter((c) => Number.isInteger(QS.codeRow(S, c)?.rank)).length, 'rank population = Universe codes with V');
  } finally { QS.setPageIdentities(null); }
});

/* Model portfolio: a hand-made official result (rank order, Universe rows) + records with the published metrics the rules read. */
function fakeResult(spec) {
  const rows = {}, records = {};
  spec.forEach((x, i) => {
    const code = x.code || 'NYSE:R' + i, id = x.id || code;
    records[code] = { metrics: { net_debt_to_ebitda: x.nd === undefined ? 1 : x.nd, interest_coverage: x.ic === undefined ? 10 : x.ic }, sic: x.sic || null, cik: x.cik || null };
    rows[id] = { company_id: id, ticker: x.ticker || code.split(':')[1], code, universe_code: x.outside ? null : code, rank: x.rank === undefined ? i + 1 : x.rank,
      primary: { q: x.q === undefined ? 60 : x.q, g: 60, v: x.v === undefined ? 60 : x.v, total: 90 - i, value_trap_gate: x.gate === true, factors_available: x.fa === undefined ? 15 : x.fa, factors_total: 15 } };
  });
  return { computed: { rows, official: { evaluated: spec.length }, profile: { id: 'qgv-v2/balanced/gate-on' }, v2_as_of: '2026-10-19T00:00:00Z' }, inputs: { records } };
}
test('modelPortfolios: approved eligibility in official rank order; N10 ⊂ N15 ⊂ N20; equal weight', () => {
  const spec = [];
  for (let i = 0; i < 30; i++) spec.push({});
  spec[1].q = null;                         // AXES_50: an axis below its 50% weight (no Q score)
  spec[2].gate = true;                      // VALUE_TRAP_GATE
  spec[3].nd = 3;                           // FINANCIAL_SAFETY: net debt / EBITDA >= 3
  spec[4].ic = 2.9;                         // FINANCIAL_SAFETY: interest coverage < 3
  spec[5].nd = null;                        // FINANCIAL_SAFETY_NA: net debt / EBITDA NA (owner decision 2026-10-15: excluded)
  spec[11].ic = null;                       // FINANCIAL_SAFETY_NA: interest coverage NA
  for (const i of [6, 7, 8, 9, 10]) spec[i].sic = '3674';   // semiconductors: the 5th one (rank 11) is over the cap of 4
  const { computed, inputs: recs } = fakeResult(spec), sector = (t, sic) => (sic === '3674' ? 'semiconductors' : null);
  const M = QS.modelPortfolios(computed, recs, { sectorOf: sector });
  assert.deepEqual(M.rules, ['OFFICIAL_RANK', 'AXES_50', 'VALUE_TRAP_GATE', 'FINANCIAL_SAFETY', 'FINANCIAL_SAFETY_NA', 'SUBGROUP_MAX_4', 'LIMITS_16']);
  assert.deepEqual(M.excluded, { AXES_50: 1, VALUE_TRAP_GATE: 1, FINANCIAL_SAFETY: 2, FINANCIAL_SAFETY_NA: 2, SUBGROUP_MAX_4: 1 });
  const expectRanks = [1, 7, 8, 9, 10, ...Array.from({ length: 30 - 12 }, (_, k) => 13 + k)].slice(0, 20);
  assert.deepEqual(M.sets.N20.selected.map((e) => e.rank), expectRanks, 'first 20 eligible rows in official rank order');
  for (const n of [10, 15, 20]) {
    const set = M.sets['N' + n];assert.equal(set.selected.length, n);assert.equal(set.complete, true);
    assert.deepEqual(set.selected.map((e) => e.rank), expectRanks.slice(0, n), 'N' + n + ' = top-' + n + ' eligible (prefix of N20)');
    for (const e of set.selected) assert.ok(Math.abs(e.weight_pct - 100 / n) < 1e-12, 'equal weight');
  }
  assert.equal(M.primary, 'N15');assert.ok(M.sets.N20.selected.every((e) => e.safety === 'PASS'), 'every selected row passes financial safety with both metrics present');
  assert.ok(!M.sets.N20.selected.some((e) => e.rank === 6 || e.rank === 12), 'NA safety rows excluded');assert.deepEqual(M.provisional, ['SUBGROUP_UNKNOWN_NOT_CAPPED']);
  assert.equal(M.sets.N20.selected.filter((e) => e.subgroup === 'semiconductors').length, 4, 'at most 4 per subgroup');
  assert.deepEqual(QS.modelPortfolios(computed, recs, { sectorOf: sector }), M, 'deterministic: the same result gives the same selection');
  // Never a TARGET outside the Universe, never a row without an official rank.
  const out = fakeResult([{ outside: true, id: 'tokyo_electron', code: 'TARGET:tokyo_electron' }, { rank: null }, {}]);
  const M2 = QS.modelPortfolios(out.computed, out.inputs, { sectorOf: () => null });
  assert.deepEqual(M2.sets.N10.selected.map((e) => e.company_id), ['NYSE:R2']);assert.equal(M2.sets.N10.complete, false);
  assert.equal(QS.modelPortfolios({ rows: {} }, out.inputs), null, 'no official result, no selection');
});

/* §16 (PLAYBOOK_V1 §16 via TARGET v1 (c), owner decision 2026-10-14): single name 10%, sector group 40% with semiconductors and
   semiconductor equipment as ONE group, at least 10 names; per N at equal weight 100/N. Known groups only from the sectorOf below. */
const SECTOR_BY_SIC = (t, sic) => (sic === '3674' ? 'semiconductors' : sic === '3559' ? 'semi_equipment' : sic === null ? null : 'sector_' + sic);
const ranksOf = (set) => set.selected.map((e) => e.rank);
test('§16 limits: the frozen copy is the approved config; tiers are the 2026-10-14 R-C rule', () => {
  const C = globalThis.PlaybookConfigDefaults.portfolio_limits;
  assert.equal(QS.LIMITS_16.single_max_pct, C.single_max_pct);assert.equal(QS.LIMITS_16.sector_group_max_pct, C.sector_group_max_pct);assert.equal(QS.LIMITS_16.min_holdings, C.min_holdings);
  assert.deepEqual(QS.LIMITS_16.combined_groups.map((g) => [g.id, [...g.sectors]]), C.combined_groups.map((g) => [g.id, [...g.sectors]]));
  assert.deepEqual([QS.LIMITS_16.single_max_pct, QS.LIMITS_16.sector_group_max_pct, QS.LIMITS_16.min_holdings], [10, 40, 10], 'PLAYBOOK_V1 §16 values');
  assert.deepEqual({ ...QS.TIERS_RC }, { n: 15, core_n: 5, core_pct: 8, general_pct: 6, core_factors_min: 0.8 }, '10-14: core 5 x 8% + general 10 x 6%');
  assert.equal(QS.TIERS_RC.core_n * QS.TIERS_RC.core_pct + (QS.TIERS_RC.n - QS.TIERS_RC.core_n) * QS.TIERS_RC.general_pct, 100);
});
test('§16 group cap per N: semiconductors + equipment one 40% group; skipped rows replaced by the next eligible rank', () => {
  const spec = [];for (let i = 0; i < 30; i++) spec.push({ sic: String(5000 + i) });
  for (const i of [0, 1, 2, 3]) spec[i].sic = '3674';for (const i of [4, 5, 6]) spec[i].sic = '3559';   // 7 rows of the combined group
  const { computed, inputs: recs } = fakeResult(spec), M = QS.modelPortfolios(computed, recs, { sectorOf: SECTOR_BY_SIC });
  // N10 (10% each): 4 names = 40% -> equipment ranks 5-7 skipped; N15 (6.67%): 6 names = 40% -> rank 7 skipped; N20 (5%): 8 names fit.
  assert.deepEqual(ranksOf(M.sets.N10), [1, 2, 3, 4, 8, 9, 10, 11, 12, 13]);
  assert.deepEqual(ranksOf(M.sets.N15), [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16]);
  assert.deepEqual(ranksOf(M.sets.N20), Array.from({ length: 20 }, (_, k) => k + 1));
  assert.deepEqual(M.sets.N10.group_capped.map((c) => [c.rank, c.group]), [[5, 'semiconductor_combined'], [6, 'semiconductor_combined'], [7, 'semiconductor_combined']]);
  assert.equal(M.sets.N15.skipped.SECTOR_GROUP_MAX_40, 1);assert.equal(M.sets.N20.skipped.SECTOR_GROUP_MAX_40, 0);
  for (const n of [10, 15, 20]) {
    const s = M.sets['N' + n], g = s.limits.group.groups.find((x) => x.id === 'semiconductor_combined');
    assert.equal(s.status, 'FEASIBLE', 'N' + n);assert.equal(s.shortfall_pct, 0);assert.deepEqual(s.causes, []);
    assert.ok(g.pct <= 40 + 1e-9, 'N' + n + ' combined group ' + g.pct);assert.equal(s.limits.group.status, 'PASS');assert.ok(s.limits.single.ok);assert.ok(s.limits.min_holdings.ok);
    assert.ok(Math.abs(s.limits.sum_pct - 100) < 1e-9);for (const e of s.selected) assert.ok(Math.abs(e.weight_pct - 100 / n) < 1e-12, 'equal weight, never rescaled');
  }
  assert.ok(Math.abs(M.sets.N10.limits.group.top_pct - 40) < 1e-9);assert.ok(M.sets.N10.selected.every((e) => M.sets.N15.selected.some((x) => x.company_id === e.company_id)), 'N10 within N15 here');
});
test('§16 shortfall: not enough eligible replacements -> short set, shortfall weight and cause; never filled or rescaled', () => {
  const spec = [];for (let i = 0; i < 12; i++) spec.push({ sic: String(6000 + i) });
  for (const i of [0, 1, 2, 3]) spec[i].sic = '3674';for (const i of [4, 5, 6, 7]) spec[i].sic = '3559';
  spec.push({ nd: 4 }, { ic: null });   // two more ranked rows, both excluded (safety fail / NA): never put back
  const { computed, inputs: recs } = fakeResult(spec), M = QS.modelPortfolios(computed, recs, { sectorOf: SECTOR_BY_SIC });
  const want = { N10: [8, 20, 4], N15: [10, 100 / 3, 2], N20: [12, 40, 0] };
  for (const [k, [picked, short, capped]] of Object.entries(want)) {
    const s = M.sets[k];assert.equal(s.selected.length, picked, k);assert.equal(s.complete, false);assert.equal(s.status, 'SHORTFALL');
    assert.ok(Math.abs(s.shortfall_pct - short) < 1e-9, k + ' shortfall ' + s.shortfall_pct);assert.ok(Math.abs(s.limits.sum_pct + s.shortfall_pct - 100) < 1e-9, k + ' sum + shortfall = 100');
    for (const e of s.selected) assert.ok(Math.abs(e.weight_pct - s.weight_pct) < 1e-12, 'weights stay 100/N');
    assert.equal(s.causes[0].code, 'ELIGIBLE_EXHAUSTED');assert.equal(s.skipped.SECTOR_GROUP_MAX_40, capped, k);
    if (capped) assert.deepEqual(s.causes.find((c) => c.code === 'SECTOR_GROUP_MAX_40'), { code: 'SECTOR_GROUP_MAX_40', count: capped, groups: ['semiconductor_combined'] });
    assert.ok(!s.selected.some((e) => e.rank > 12), 'excluded rows are never put back');
  }
  assert.ok(M.sets.N10.causes.some((c) => c.code === 'MIN_HOLDINGS'), 'N10 with 8 names is below the §16 minimum of 10');assert.ok(!M.sets.N15.causes.some((c) => c.code === 'MIN_HOLDINGS'));
});
test('§16 unknown group: not capped (provisional) and the 40% check is UNVERIFIED unless it provably holds', () => {
  const none = [];for (let i = 0; i < 20; i++) none.push({});
  const A = QS.modelPortfolios(fakeResult(none).computed, fakeResult(none).inputs, { sectorOf: () => null });
  assert.equal(A.sets.N10.status, 'UNVERIFIED');assert.deepEqual(A.sets.N10.causes, [{ code: 'GROUP_UNKNOWN', count: 10, pct: 100 }]);assert.equal(A.sets.N10.selected.length, 10);
  const one = [];for (let i = 0; i < 20; i++) one.push({ sic: i === 0 ? null : String(7000 + i) });
  const B = QS.modelPortfolios(fakeResult(one).computed, fakeResult(one).inputs, { sectorOf: SECTOR_BY_SIC });
  assert.equal(B.sets.N10.status, 'FEASIBLE', 'one unknown (10%) + largest known group (10%) <= 40%');assert.equal(B.sets.N10.limits.group.unknown.count, 1);
});
test('issuer check: GOOG / GOOGL stay two securities and both keep their seats; the summed weight is a recommendation check', () => {
  const spec = [{ code: 'NASDAQ:GOOG', cik: '0001652044' }, { code: 'NASDAQ:GOOGL', id: 'googl', ticker: 'GOOGL', cik: '0001652044' }];for (let i = 0; i < 20; i++) spec.push({ cik: 'C' + i });
  const { computed, inputs: recs } = fakeResult(spec), M = QS.modelPortfolios(computed, recs, { sectorOf: () => null });
  for (const n of [10, 15, 20]) {
    const s = M.sets['N' + n], c = s.issuer_check;
    assert.deepEqual(ranksOf(s).slice(0, 2), [1, 2], 'both share classes selected: the selection does not apply the recommendation');
    assert.equal(c.status, 'RECOMMENDATION_DECISION_NEEDED');assert.equal(c.applied, false);assert.equal(c.rule, 'ISSUER_ONE_SEAT');
    assert.deepEqual(c.issuers.map((x) => [x.issuer, x.tickers]), [['0001652044', ['GOOG', 'GOOGL']]]);assert.ok(Math.abs(c.issuers[0].pct - 200 / n) < 1e-9);
    assert.equal(c.issuers[0].over_single_max, 200 / n > 10 + 1e-9, 'N' + n);assert.ok(Math.abs(c.max_issuer_pct - 200 / n) < 1e-9);
  }
  assert.deepEqual(M.sets.N20.selected.slice(0, 2).map((e) => [e.code, e.issuer]), [['NASDAQ:GOOG', '0001652044'], ['NASDAQ:GOOGL', '0001652044']]);
});
test('R-C tier check on N15 (check only): core = top 5 with factors >= 80% and safety passed; weights never change the selection', () => {
  const spec = [];for (let i = 0; i < 20; i++) spec.push({ sic: String(8000 + i) });
  let M = QS.modelPortfolios(fakeResult(spec).computed, fakeResult(spec).inputs, { sectorOf: SECTOR_BY_SIC });
  let t = M.sets.N15.tier_check;assert.equal(t.status, 'PASS');assert.equal(t.core, 5);assert.deepEqual(t.rows.slice(0, 6).map((r) => [r.tier, r.weight_pct]), [['CORE', 8], ['CORE', 8], ['CORE', 8], ['CORE', 8], ['CORE', 8], ['GENERAL', 6]]);
  assert.equal(t.applied_to_selection, false);assert.ok(Math.abs(t.limits.sum_pct - 100) < 1e-9);assert.equal(M.sets.N10.tier_check, null);assert.equal(M.sets.N20.tier_check, null);
  spec[2].fa = 11;   // 11/15 = 73% < 80%: not core, and nothing is promoted in its place (core 4, sum 98%)
  M = QS.modelPortfolios(fakeResult(spec).computed, fakeResult(spec).inputs, { sectorOf: SECTOR_BY_SIC });t = M.sets.N15.tier_check;
  assert.equal(t.status, 'CORE_SHORT');assert.equal(t.core, 4);assert.ok(Math.abs(t.limits.sum_pct - 98) < 1e-9);assert.equal(t.rows[2].tier, 'GENERAL');
  assert.deepEqual(ranksOf(M.sets.N15), Array.from({ length: 15 }, (_, k) => k + 1), 'selection unchanged by the tier check');
  const semi = [];for (let i = 0; i < 20; i++) semi.push({ sic: i < 6 ? (i < 4 ? '3674' : '3559') : String(8100 + i) });   // 6 combined names: 5 core x 8 + 1 x 6 = 46%
  t = QS.modelPortfolios(fakeResult(semi).computed, fakeResult(semi).inputs, { sectorOf: SECTOR_BY_SIC }).sets.N15.tier_check;
  assert.equal(t.status, 'FAIL', 'tier weights can break §16 even when the equal-weight N15 passes');assert.ok(Math.abs(t.limits.group.groups.find((g) => g.id === 'semiconductor_combined').pct - 46) < 1e-9);
});

/* The screen text: one line per N with the feasibility (data attributes + Korean words), the R-C tier check and the issuer check. */
function textTree(node) { return [node.text || '', ...(node.children || []).map(textTree)].join(''); }
const fakeEl = (tag, text, attrs = {}) => ({ tag, text, attrs: { ...attrs }, children: [], append(...xs) { this.children.push(...xs); } });
test('modelChecks screen text: Korean feasibility, shortfall weight and cause, tier and issuer lines', () => {
  const LB = require(path.join(W, 'leaderboard-screen.js'));
  const spec = [];for (let i = 0; i < 12; i++) spec.push({ sic: String(6000 + i), cik: 'C' + i });
  for (const i of [0, 1, 2, 3]) spec[i].sic = '3674';for (const i of [4, 5, 6, 7]) spec[i].sic = '3559';spec[8].cik = 'C0';
  const { computed, inputs: recs } = fakeResult(spec), M = QS.modelPortfolios(computed, recs, { sectorOf: SECTOR_BY_SIC }), box = LB.modelChecks(M, QS, false, fakeEl);
  const by = (k, v) => box.children.find((c) => c.attrs[k] === v);
  const n10 = by('data-model-limits', 'N10');assert.equal(n10.attrs['data-model-feasible'], 'SHORTFALL');assert.equal(n10.attrs['data-model-shortfall-pct'], '20.00');assert.equal(n10.attrs['data-model-group-skipped'], '4');
  assert.equal(n10.attrs['data-model-causes'], 'ELIGIBLE_EXHAUSTED SECTOR_GROUP_MAX_40 MIN_HOLDINGS');
  assert.match(n10.text, /^N10 · 구성 불가 · 부족 비중 20\.00% \(8\/10 · 채우지 않음 · 비중 재조정 없음\) · 원인: 반도체 묶음 40% 한도로 4종목 초과, 대체 후보 부족, 최소 10종목 미달 · /);
  assert.match(n10.text, /업종 묶음 40% 한도로 건너뜀: R4 #5 \(반도체 묶음\), R5 #6 \(반도체 묶음\), R6 #7 \(반도체 묶음\), R7 #8 \(반도체 묶음\) → 다음 자격 순위로 대체/);
  assert.equal(JSON.parse(n10.attrs['data-model-group-pct']).semiconductor_combined, 40);
  assert.match(by('data-model-limits', 'N20').text, /^N20 · 구성 불가 · 부족 비중 40\.00% \(12\/20/);
  assert.equal(by('data-model-tier-check', 'INCOMPLETE').attrs['data-model-tier-core'], '5');
  const i10 = by('data-model-issuer', 'N10');assert.equal(i10.attrs['data-model-issuer-status'], 'RECOMMENDATION_DECISION_NEEDED');assert.equal(i10.attrs['data-model-issuer-applied'], 'false');
  assert.match(i10.text, /^N10 · 같은 발행사 합산 비중 \(권장안 · 결정 필요 · 선정 불변\): R0\+R8 20\.00% \(발행사 기준으로 읽으면 단일 10% 초과\) · 발행사 최대 20\.00%$/);
  const ok = [];for (let i = 0; i < 20; i++) ok.push({ sic: String(9000 + i) });
  const B = LB.modelChecks(QS.modelPortfolios(fakeResult(ok).computed, fakeResult(ok).inputs, { sectorOf: SECTOR_BY_SIC }), QS, false, fakeEl);
  assert.match(B.children.find((c) => c.attrs['data-model-limits'] === 'N15').text, /^N15 · 16절 한도 아래 구성 가능 · 각 6\.67% ≤ 10% · 최대 업종 묶음 /);
  assert.match(textTree(B), /참고 검사 · R-C\(TARGET v1\) 등급 비중을 N15에 넣으면 \(선정 불변\): 핵심 5 × 8% .* → 16절 통과/);
  assert.match(B.children.find((c) => c.attrs['data-model-issuer'] === 'N20').text, /같은 발행사 중복 없음 · 발행사 최대 5\.00%$/);
});

test('modelPortfolios on the shared result: subgroups from the approved #20 rule; outside / Q·G-only never selected', async () => {
  QS.setPageIdentities(TARGETS);
  try {
    const S = (await QS.pageResult(win(), { v2Inputs: inputs })).computed, M = QS.modelPortfolios(S, inputs);
    const official = Object.values(S.rows).filter((r) => Number.isInteger(r.rank)).sort((a, b) => a.rank - b.rank);
    const picked = M.sets.N20.selected.map((e) => e.company_id);
    assert.ok(picked.length > 0);assert.ok(M.excluded.FINANCIAL_SAFETY_NA >= 1, JSON.stringify(M.excluded));
    for (const id of picked) { const m = inputs.records[S.rows[id].code].metrics;assert.ok(m.net_debt_to_ebitda < 3 && m.interest_coverage >= 3, id + ' passes financial safety with both metrics'); }assert.ok(!picked.includes('asml'), 'outside row never selected');assert.ok(picked.every((id) => S.rows[id].primary.value_trap_gate !== true), 'gate rows never selected');
    assert.ok(picked.every((id) => Number.isInteger(S.rows[id].rank) && typeof S.rows[id].universe_code === 'string'));
    assert.deepEqual(picked, official.map((r) => r.company_id).filter((id) => picked.includes(id)), 'official order kept');
    const subgroups = {};for (const e of M.sets.N20.selected) if (e.subgroup) subgroups[e.subgroup] = (subgroups[e.subgroup] || 0) + 1;
    assert.ok(Object.values(subgroups).every((n) => n <= 4), JSON.stringify(subgroups));
    assert.equal(M.sets.N20.selected.find((e) => e.company_id === 'nvda')?.subgroup ?? 'semiconductors', 'semiconductors', 'TARGET assignment (#20)');
    for (const n of [10, 15, 20]) {
      const s = M.sets['N' + n];assert.ok(['FEASIBLE', 'SHORTFALL', 'UNVERIFIED'].includes(s.status), s.status);
      for (const g of s.limits.group.groups) assert.ok(g.pct <= 40 + 1e-9, 'N' + n + ' ' + g.id + ' ' + g.pct);
      for (const e of s.selected) assert.ok(Math.abs(e.weight_pct - 100 / n) < 1e-12);
      const ciks = {};for (const e of s.selected) if (e.issuer) ciks[e.issuer] = (ciks[e.issuer] || 0) + 1;
      assert.deepEqual(s.issuer_check.issuers.map((x) => x.issuer).sort(), Object.keys(ciks).filter((k) => ciks[k] > 1).sort(), 'issuer check = CIKs with two selected codes');
    }
  } finally { QS.setPageIdentities(null); }
});

test('candidateRanking over the official result: candidate rank = official rank; outside TARGET never a candidate', async () => {
  QS.setPageIdentities(TARGETS);
  try {
    const S = (await QS.pageResult(win(), { v2Inputs: inputs })).computed, c = P.candidateRanking(S, { [QI.FILE]: inputs }, codesOf());
    for (const r of c.filter((x) => x.rank !== null)) { const row = QS.codeRow(S, r.code);assert.equal(r.rank, row.rank, r.code);assert.equal(r.official_rank, row.rank);assert.ok(Object.is(r.total, row.primary.total)); }
    assert.equal(c.filter((x) => x.rank !== null).length, S.official.ranked, 'every officially ranked Universe row is a ranked candidate');
    assert.ok(!c.some((x) => x.symbol === 'ASML'), 'TARGET outside the Universe is not a Universe candidate');
    assert.equal(new Set(c.map((x) => x.code)).size, c.length, 'one candidate row per code');
  } finally { QS.setPageIdentities(null); }
});

test('officialModel: N10/N15/N20 on the official default profile (balanced, gate on), whatever the device preset', async () => {
  QS.setPageIdentities(TARGETS);
  try {
    const U = QS.universeIdentities(inputs, TARGETS), official = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes, preset: 'balanced', gate: true, official: U });
    const want = QS.modelPortfolios(official, inputs), ids = (M) => ['N10', 'N15', 'N20'].map((k) => M.sets[k].selected.map((e) => e.company_id));
    for (const [preset, gate] of [['value', true], ['growth', false], ['quality', false], ['balanced', true]]) {
      const device = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes, preset, gate, official: U });
      const M = QS.officialModel({ identities: U.identities, v2Inputs: inputs, quotes, official: U, computed: device });
      assert.deepEqual(ids(M), ids(want), preset + '/gate-' + gate + ': the selection does not follow the device preset');
      assert.deepEqual(M.official_profile, { preset: 'balanced', gate: true, id: official.profile.id });assert.equal(M.profile_id, official.profile.id);
    }
  } finally { QS.setPageIdentities(null); }
});

// User decision 2026-10-23: the leaderboard shows per row how many of the 5 V factors V was computed from ('V n/5'); a null V is
// 0/5 (never filled). Synthetic fixture prices only; the count is read from the same shared result (no separate computation).
test('V factor count n/5 per row from the shared result; V null → 0/5', () => {
  const L = require(path.join(W, 'leaderboard-screen.js')), U = QS.universeIdentities(inputs, TARGETS), A = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes, official: U });
  const VF = Object.keys(V2.WEIGHTS.V), seen = new Set();
  for (const r of Object.values(A.rows)) {
    const p = r.primary, c = L.vCount(p), have = finite(p.v) ? VF.filter((k) => finite(p.factors?.[k]?.score)) : [];
    assert.equal(c.total, 5);assert.equal(c.n, have.length, r.company_id);assert.deepEqual(c.missing.map((x) => x[0]), VF.filter((k) => !have.includes(k)), r.company_id);
    if (!finite(p.v)) assert.equal(c.n, 0, r.company_id + ' V null is 0/5');seen.add(c.n);
  }
  assert.ok(seen.has(0) && [...seen].some((n) => n > 0), 'fixture has rows with and without V: ' + [...seen]);
  assert.deepEqual(L.vCount(null), { n: 0, total: 5, missing: L.vCount(undefined).missing });
  assert.equal(L.vCount({ v: 40, factors: { v_earnings_yield: { score: 50 }, v_fcf_yield: { score: null }, v_vs_industry: { score: 60 }, v_vs_own_history: { score: null }, v_expectation_check: { score: 30 } } }).n, 3);
  // Before any price: every row has no V → 0/5.
  const N = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes: {}, official: U });
  assert.ok(Object.values(N.rows).every((r) => L.vCount(r.primary).n === 0));
});
