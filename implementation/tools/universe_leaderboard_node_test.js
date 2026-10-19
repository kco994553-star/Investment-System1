'use strict';
// D12 (owner decision 2026-10-19: '공식 리더보드는 Universe 전체 평가를 기준으로 한다. 기존 TARGET 19개는 별도 목록·필터로 유지한다.')
// in Node, over SYNTHETIC data only (tools/qgv_v2_fixture.js, made-up device prices):
// - QgvScores.universeIdentities: one row per security (a TARGET identity whose ticker is a Universe code IS that code), every
//   Universe code covered once, TARGET outside the Universe listed apart;
// - QgvScores.compute({official}): the same engine values as without it (no formula, weight or engine change), official ranks only
//   over Universe rows with V (D11), TARGET outside the Universe never ranked nor in the QG list, Q·G-only rows in the QG list;
// - QgvScores.pageResult: the ONE shared result carries that split; rowOf / codeRow / vCoverage read the merged row;
// - QgvScores.modelPortfolios: N10 / N15 / N20 = the first N rows of the official order that pass the approved eligibility
//   (official rank, Q·G·V all present, no value-trap gate, financial safety, at most 4 per industry subgroup), equal weight;
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
    records[code] = { metrics: { net_debt_to_ebitda: x.nd === undefined ? 1 : x.nd, interest_coverage: x.ic === undefined ? 10 : x.ic }, sic: x.sic || null };
    rows[id] = { company_id: id, ticker: x.ticker || code.split(':')[1], code, universe_code: x.outside ? null : code, rank: x.rank === undefined ? i + 1 : x.rank,
      primary: { q: x.q === undefined ? 60 : x.q, g: 60, v: x.v === undefined ? 60 : x.v, total: 90 - i, value_trap_gate: x.gate === true } };
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
  assert.deepEqual(M.rules, ['OFFICIAL_RANK', 'AXES_50', 'VALUE_TRAP_GATE', 'FINANCIAL_SAFETY', 'FINANCIAL_SAFETY_NA', 'SUBGROUP_MAX_4']);
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
