'use strict';
// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다') for the TARGET v1 writer candidate selection
// (PlaybookScreen.candidateRanking, 'QGV v2 총점·업종 내 순위로 후보 추림'): a candidate is ranked only when QgvScores gave it an
// official rank (a total with V); the value-trap-gate rows (V computed, left out of the total by the approved gate) stay ranked;
// Q·G-only totals (financial: V not defined; no device price) never get a rank, an industry rank or a QGV total and are kept in
// the separate 'Q·G 참고 (V 미포함)' list; the selection equals the official ranked order filtered by the existing rules
// (identity withdrawal, the given codes). Synthetic only: tools/qgv_v2_fixture.js with made-up device prices.
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets'), F = require('./qgv_v2_fixture.js');
for (const [name, file] of [['EnginePreview', 'engine-preview.js'], ['ProfileDefaults', 'profile-defaults.js'], ['TypeConfigDefaults', 'type-config-defaults.js'], ['DcfParametersDefaults', 'dcf-parameters-defaults.js'],
  ['QgvV2', 'qgv-v2.js'], ['Qgv2Inputs', 'qgv2-inputs.js'], ['QgvScores', 'qgv-scores.js']]) globalThis[name] = require(path.join(W, file));
const QS = globalThis.QgvScores, SQ = globalThis.Qgv2Inputs, V2 = globalThis.QgvV2, P = require(path.join(W, 'playbook-screen.js'));
const finite = (v) => typeof v === 'number' && Number.isFinite(v);

/* The fixture with TARGET amd made weak in Q (all Q factors 1: its industry Q percentile is the lowest, so the gate drops its V)
   and a TARGET copy of the financial Universe row SYNF1 (V not defined). GEV has no synthetic price (V not computed). */
function payload() {
  const p = F.payload(), amd = p.target.amd;
  for (const k of Object.keys(V2.WEIGHTS.Q)) amd.factors[k] = 1;
  amd.axes.Q = { ...amd.axes.Q, score: V2.axisScore(amd.factors, 'Q').score };
  p.target.synf = JSON.parse(JSON.stringify(p.records['NYSE:SYNF1']));
  return p;
}
const ids = [...Object.keys(F.TICKERS), 'asml', 'synf'].map((id) => ({ company_id: id, ticker: id === 'asml' ? 'ASML' : id === 'synf' ? 'SYNF1' : F.TICKERS[id].split(':')[1] }));
const CODES = [...Object.values(F.TICKERS), 'NASDAQ:ASML', 'NYSE:SYNF1'];
let inputs = null, screens = null, quotes = null;
test.before(async () => {
  inputs = SQ.fromInputs(SQ.light(payload()));screens = { [SQ.FILE]: inputs };
  quotes = await QS.collectQuotes({ PrivateSubsetView: { prices: () => new Map(Object.entries(F.quotes())) } }, { identities: ids, v2Inputs: inputs });
});
const tickerOf = (S, pred) => Object.values(S.rows).filter(pred).map((r) => r.ticker);
const officialOrder = (S, tickers) => Object.values(S.rows).filter((r) => Number.isInteger(r.rank) && tickers.includes(r.ticker)).sort((a, b) => a.rank - b.rank).map((r) => r.ticker);

test('fixture covers ranked, value-trap-gate and Q·G-only (financial, no price) rows', () => {
  const S = QS.compute({ identities: ids, publicScreens: screens, quotes });
  assert.equal(S.rows.amd.primary.value_trap_gate, true);assert.ok(Number.isInteger(S.rows.amd.rank), 'gate row has an official rank');
  assert.equal(S.rows.synf.qg_reference.reason, 'FINANCIAL_PROFILE_V_NOT_DEFINED');assert.equal(S.rows.gev.qg_reference.reason, 'NO_DEVICE_PRICE');
  // Mixing would have put these Q·G-only totals above ranked rows: the test would see it.
  const lowestRanked = Math.min(...Object.values(S.rows).filter((r) => Number.isInteger(r.rank)).map((r) => r.primary.total));
  assert.ok(S.rows.synf.primary.total > lowestRanked && S.rows.gev.primary.total > lowestRanked);
});

test('candidate selection = the official ranked order; Q·G-only rows never ranked; gate rows stay; Q·G list separate and labelled', () => {
  for (const preset of Object.keys(V2.PRESETS)) for (const gate of [true, false]) {
    const S = QS.compute({ identities: ids, publicScreens: screens, quotes, preset, gate }), tag = preset + '/gate-' + gate;
    const ranked = P.candidateRanking(S, screens, CODES), by = Object.fromEntries(ranked.map((r) => [r.symbol, r]));
    const qgOnly = tickerOf(S, (r) => r.qg_reference), gates = tickerOf(S, (r) => r.primary.value_trap_gate === true && Number.isInteger(r.rank));
    // The default preset has three Q·G-only totals and the AMD gate row (another preset may need V for any total).
    if (preset === V2.DEFAULT_PRESET) { assert.ok(qgOnly.length >= 3, tag);if (gate) assert.ok(gates.includes('AMD'), tag); }
    // (1) Q·G-only rows never get a candidate rank, an industry rank or a QGV total.
    for (const t of qgOnly) { const r = by[t];assert.deepEqual([r.rank, r.official_rank, r.industry_rank, r.total, r.group], [null, null, null, null, 'QG_REFERENCE'], tag + ' ' + t);
      assert.equal(r.qg_reference.total, S.rows[Object.keys(S.rows).find((k) => S.rows[k].ticker === t)].primary.total, tag + ' ' + t + ' keeps its Q·G total apart'); }
    // (2) Value-trap-gate rows stay eligible (ranked with their total).
    for (const t of gates) { assert.ok(Number.isInteger(by[t].rank), tag + ' gate ' + t);assert.ok(finite(by[t].total)); }
    // (3) Selection order == the official ranked order reduced to these codes; rank renumbers 1.., official_rank is QgvScores'.
    const sel = ranked.filter((r) => r.rank !== null);
    assert.deepEqual(sel.map((r) => r.symbol), officialOrder(S, CODES.map((c) => c.split(':')[1])), tag);
    assert.deepEqual(sel.map((r) => r.rank), sel.map((_, i) => i + 1), tag);
    for (const r of sel) { const row = Object.values(S.rows).find((x) => x.ticker === r.symbol);assert.equal(r.official_rank, row.rank, tag);assert.equal(r.total, row.primary.total, tag);assert.ok(finite(row.primary.v), tag + ' ranked rows have V'); }
    // Industry rank counts only ranked rows, in the official order.
    const groups = {};for (const r of sel) if (r.industry) { groups[r.industry] = (groups[r.industry] || 0) + 1;assert.equal(r.industry_rank, groups[r.industry], tag + ' ' + r.symbol); }
    // (4) The Q·G reference list: separate, in its own order (QgvScores qg_reference order), after every ranked row.
    const ref = P.candidateQgReference(ranked);
    assert.deepEqual(ref.map((r) => r.symbol), Object.values(S.rows).filter((r) => r.qg_reference).sort((a, b) => a.qg_reference.order - b.qg_reference.order).map((r) => r.ticker), tag);
    assert.deepEqual(ref.map((r) => r.qg_reference.order), ref.map((_, i) => i + 1));
    if (ref.length) assert.ok(ranked.findIndex((r) => r.qg_reference) > ranked.findLastIndex((r) => r.rank !== null), tag + ' Q·G list never interleaved');
    assert.equal(P.QG_CANDIDATE_LABEL, 'Q·G 참고 (V 미포함)');
  }
});

test('before any device price: no candidate rank at all, every total is in the Q·G list', () => {
  const S = QS.compute({ identities: ids, publicScreens: screens, quotes: {} }), ranked = P.candidateRanking(S, screens, CODES);
  assert.ok(Object.values(S.rows).every((r) => r.rank === null));
  assert.ok(ranked.every((r) => r.rank === null && r.total === null && r.industry_rank === null));
  assert.ok(P.candidateQgReference(ranked).length >= 15);
});

test('existing rules still apply: an identity-withdrawn code gets no place; codes outside the list are not selected', () => {
  const S = QS.compute({ identities: ids, publicScreens: screens, quotes });
  const stopped = { [SQ.FILE]: { ...inputs, records: { ...inputs.records, 'NASDAQ:MSFT': { ...inputs.records['NASDAQ:MSFT'], identity_withdrawn: true } } } };
  const ranked = P.candidateRanking(S, stopped, CODES), msft = ranked.find((r) => r.symbol === 'MSFT');
  assert.deepEqual([msft.rank, msft.total, msft.qg_reference, msft.group], [null, null, null, null]);
  assert.deepEqual(ranked.filter((r) => r.rank !== null).map((r) => r.symbol), officialOrder(S, CODES.map((c) => c.split(':')[1])).filter((t) => t !== 'MSFT'));
  const few = P.candidateRanking(S, screens, ['NASDAQ:AMD', 'NYSE:SYNF1', 'NYSE:GEV']);
  assert.deepEqual(few.map((r) => [r.symbol, r.rank, r.qg_reference && r.qg_reference.order]), [['AMD', 1, null], ['SYNF1', null, 1], ['GEV', null, 2]]);
  // The official engine output is untouched by the candidate view.
  assert.ok(Number.isInteger(S.rows.msft.rank) && S.rows.synf.rank === null && S.rows.synf.qg_reference.order >= 1);
});
