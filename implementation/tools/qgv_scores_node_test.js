'use strict';
// scoring_default flip: every score consumer reads through QgvScores, so flipping ScoringDefault.scoring_default ('v1'|'v2')
// flips S04/S05 (CompanyScreen), S06 (LeaderboardScreen), the virtual-trading rehearsal judgement rows, the daily report
// model and its export template. Synthetic data only (tools/qgv_v2_fixture.js).
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const F = require('./qgv_v2_fixture.js');
const CONFIG = require.resolve(path.join(W, 'scoring-default.js'));
for (const [name, file] of [['EnginePreview', 'engine-preview.js'], ['ProfileDefaults', 'profile-defaults.js'], ['TypeConfigDefaults', 'type-config-defaults.js'], ['DcfParametersDefaults', 'dcf-parameters-defaults.js'],
  ['QgvV2', 'qgv-v2.js'], ['SecQgv2', 'sec-qgv2.js'], ['QgvScores', 'qgv-scores.js']]) globalThis[name] = require(path.join(W, file));
const QS = globalThis.QgvScores, L = require(path.join(W, 'leaderboard-screen.js')), CS = require(path.join(W, 'company-screen.js'));
const R = require(path.join(W, 'daily-report.js')), S = require(path.join(W, 'virtual-trading-signals.js')), SQ = globalThis.SecQgv2;
const original = require(CONFIG);
function setDefault(mode) { require.cache[CONFIG].exports = Object.freeze({ scoring_default: mode }); }
test.after(() => { require.cache[CONFIG].exports = original; });
const IDS = Object.keys(F.TICKERS), identities = IDS.map((id) => ({ company_id: id, ticker: F.TICKERS[id].split(':')[1] }));
const FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
function v1Screen() {
  const companies = {};
  for (const id of IDS) companies[id] = { state: 'LIVE', source_hashes: {}, factors: Object.fromEntries(FACTORS.map((f, i) => [f, { score: id === 'amd' && i > 6 ? null : 40 + i * 3, state: id === 'amd' && i > 6 ? 'NOT_AVAILABLE' : 'LIVE' }])) };
  return { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: '2026-10-13T00:00:00Z', state: 'LIVE', stale_after_seconds: 86400, data: { companies, availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
}
const screens = { 'sec-qg-factors.json': v1Screen(), [SQ.FILE]: SQ.toInputs(F.payload()) };
const quotes = F.quotes();

test('the shipped setting is v1 and the accessor reads only that setting', () => {
  assert.equal(original.scoring_default, 'v1');
  assert.ok(Object.isFrozen(original));
  assert.equal(QS.scoringDefault(), 'v1');
  const src = fs.readFileSync(path.join(W, 'scoring-default.js'), 'utf8');
  assert.equal((src.match(/scoring_default:'v[12]'/g) || []).length, 1, 'one-line flip');
  for (const f of ['leaderboard-screen.js', 'company-screen.js', 'daily-report.js', 'app.js', 'virtual-trading-signals.js']) assert.ok(!fs.readFileSync(path.join(W, f), 'utf8').includes('ScoringDefault'), f + ' reads scores through QgvScores only');
});

for (const mode of ['v1', 'v2']) test('flip to ' + mode + ': every consumer follows', () => {
  setDefault(mode);
  try {
    assert.equal(QS.scoringDefault(), mode);
    const sc = QS.compute({ identities, publicScreens: screens, quotes });
    assert.equal(sc.default, mode);assert.equal(sc.v2_state, 'READY');
    const nvda = sc.rows.nvda;
    assert.equal(nvda.primary.version, mode);
    assert.equal(nvda.reference.version, mode === 'v2' ? 'v1_renormalized' : 'v2');
    assert.ok(typeof nvda.v2.total === 'number' && typeof nvda.v2.v === 'number', 'v2 has V from device quotes');
    assert.equal(sc.rows.gev.v2.v, null, 'no device price -> V NA, never 0');
    assert.ok(sc.rows.gev.v2.flags.includes('V_NOT_AVAILABLE'));
    // S06
    const rows = L.rowsFor(identities, { publicScreens: screens, scores: sc }), lr = rows.find((r) => r.company_id === 'nvda');
    assert.equal(lr.score.primary.version, mode);
    assert.equal(rows.filter((r) => r.score.rank !== null).length > 0, mode === 'v2');
    const auto = L.rowsFor(identities, { publicScreens: screens });
    assert.equal(auto.find((r) => r.company_id === 'nvda').score.primary.version, mode, 'rowsFor without scores uses the accessor');
    // S04 / S05
    const sum = CS.summary({ locale: 'ko-KR', id: 'nvda', screens, scores: sc, headerHtml: '', groupsHtml: '' });
    assert.ok(sum.includes('data-scoring-default="' + mode + '"'));
    const ana = CS.analysis({ locale: 'ko-KR', id: 'nvda', ticker: 'NVDA', screens, scores: sc, headerHtml: '' });
    if (mode === 'v2') {
      assert.ok(sum.includes('data-qgv="total"') && sum.includes('data-qgv-v1-reference') && sum.includes('산출 요인 '));
      assert.ok(ana.indexOf('data-v2-factor-table') < ana.indexOf('data-factor-table>') && ana.includes('data-overall="v2"') && ana.includes('자세히 · v1 참고'));
      assert.ok(sum.includes('점수 기준 v2 · PROVISIONAL') && sum.includes('DCF 참고 범위'));
    } else {
      assert.ok(sum.includes('data-qgv-v2-compare') && sum.includes('v2 비교용') && !sum.includes('data-qgv="total"'));
      assert.ok(ana.indexOf('data-factor-table>') < ana.indexOf('data-v2-factor-table') && ana.includes('data-v2-compare') && !ana.includes('data-overall="v2"'));
      assert.ok(sum.includes('점수 기준 v1 · 보정 전'));
    }
    // Judgement rows: rehearsal snapshot + daily report + export
    const qg = QS.judgmentRows(sc);
    assert.equal(qg.nvda.version, mode);
    assert.equal(qg.nvda.q, mode === 'v2' ? nvda.v2.q : nvda.v1.q);
    const snap = S.rehearsalSnapshot(qg);
    assert.equal(snap.nvda.q, qg.nvda.q);
    const model = R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-19', ram: { state: 'AVAILABLE', rows: [{ company_id: 'nvda', ticker: 'NVDA', weight: 0.1 }] }, qg, names: { nvda: 'NVDA' } });
    assert.equal(model.scoring, mode);
    const text = R.renderTemplate(model, { hidden: true, guide: false });
    assert.ok(text.includes(mode === 'v2' ? 'QGV 점수 기준 v2(PROVISIONAL)' : 'QGV 점수 기준 v1(UNCALIBRATED)'));
    assert.ok(text.includes(mode === 'v2' ? 'v1 참고(결측 재정규화): NVDA' : 'v2 비교용(PROVISIONAL): NVDA'));
    const html = R.screenHtml(model, { hidden: true, locale: 'ko-KR' });
    assert.equal(html.includes('(v2 · 요인 '), mode === 'v2');
  } finally { require.cache[CONFIG].exports = original; }
});

test('v1 judgement rows keep the previous Q·G values exactly (official v1 engine path)', () => {
  const sc = QS.compute({ identities, publicScreens: screens, quotes });
  const qg = QS.judgmentRows(sc), E = globalThis.EnginePreview;
  for (const id of IDS) {
    const obs = {};
    for (const [f, v] of Object.entries(screens['sec-qg-factors.json'].data.companies[id].factors)) if (v.score !== null) obs[f] = { score: v.score, quality: 'OK' };
    const r = E.strategy({ observations: obs });
    assert.equal(qg[id].q, r.axes.Q.score);assert.equal(qg[id].g, r.axes.G.score);
  }
  // Without sec-qgv2.json the v1 template has no comparison line (byte-compatible with the previous export).
  const plain = QS.judgmentRows(QS.compute({ identities, publicScreens: { 'sec-qg-factors.json': screens['sec-qg-factors.json'] } }));
  const text = R.renderTemplate(R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-19', ram: { state: 'AVAILABLE', rows: [{ company_id: 'nvda', ticker: 'NVDA', weight: 0.1 }] }, qg: plain, names: { nvda: 'NVDA' } }), { hidden: true, guide: false });
  assert.ok(!text.includes('v2 비교용') && text.includes('QGV 점수 기준 v1(UNCALIBRATED)'));
});

test('sec-qgv2 reader: assumed shape normalized; price-like keys and bad codes fail closed; collectQuotes RAM only', async () => {
  const inputs = SQ.toInputs(F.payload()), r = inputs.records['NASDAQ:NVDA'];
  assert.equal(r.v_inputs.fcf, r.v_inputs.fcf);
  assert.equal(typeof r.v_inputs.ebit, 'number');assert.equal(r.periods.ebit, '2025-12-31');assert.equal(r.industry_group, 'semiconductors');
  assert.equal(inputs.records['NASDAQ:INTC'].factors.g_revenue_growth, null);
  const bad = F.payload();bad.records['NASDAQ:NVDA'].price = 1;assert.throws(() => SQ.toInputs(bad), /SEC_QGV2_INVALID/);
  const code = F.payload();code.records['nvda'] = code.records['NASDAQ:NVDA'];assert.throws(() => SQ.toInputs(code), /SEC_QGV2_INVALID/);
  assert.throws(() => SQ.toInputs({ kind: 'OTHER', records: {} }), /SEC_QGV2_INVALID/);
  const universe = new Map([['NASDAQ:NVDA', { price: 50, currency: 'USD' }], ['NYSE:NOPE', { price: 9, currency: 'USD' }]]);
  const win = { PrivateSubsetView: { prices: () => universe }, DeviceValuation: { deviceQuote: async (w, c, t) => (t === 'AMD' ? { price: 30, currency: 'USD' } : null) },
    PriceStore: { monthEndCloses: async (s) => (s === 'NVDA' ? { '2024-12': 40, '2025-12': 45, bad: 3, '2023-12': 0 } : {}) } };
  const q = await QS.collectQuotes(win, { identities, v2Inputs: inputs, catalog: {} });
  assert.deepEqual(Object.keys(q).sort(), ['NASDAQ:AMD', 'NASDAQ:NVDA']);
  assert.deepEqual(q['NASDAQ:NVDA'].month_closes, { '2024-12': 40, '2025-12': 45 });
  assert.equal(q['NASDAQ:AMD'].month_closes, undefined);
  const none = await QS.collectQuotes({}, { identities, v2Inputs: inputs });assert.deepEqual(none, {});
});
