'use strict';
// scoring_default flip: every score consumer reads through QgvScores, so flipping ScoringDefault.scoring_default ('v1'|'v2')
// flips S04/S05 (CompanyScreen), S06 (LeaderboardScreen), the virtual-trading rehearsal judgement rows, the daily report
// model and its export template. Synthetic data only (tools/qgv_v2_fixture.js).
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const F = require('./qgv_v2_fixture.js');
const CONFIG = require.resolve(path.join(W, 'scoring-default.js'));
for (const [name, file] of [['EnginePreview', 'engine-preview.js'], ['ProfileDefaults', 'profile-defaults.js'], ['TypeConfigDefaults', 'type-config-defaults.js'], ['DcfParametersDefaults', 'dcf-parameters-defaults.js'],
  ['QgvV2', 'qgv-v2.js'], ['Qgv2Inputs', 'qgv2-inputs.js'], ['QgvScores', 'qgv-scores.js']]) globalThis[name] = require(path.join(W, file));
const QS = globalThis.QgvScores, L = require(path.join(W, 'leaderboard-screen.js')), CS = require(path.join(W, 'company-screen.js'));
const R = require(path.join(W, 'daily-report.js')), S = require(path.join(W, 'virtual-trading-signals.js')), SQ = globalThis.Qgv2Inputs;
const original = require(CONFIG);
function setDefault(mode) { require.cache[CONFIG].exports = Object.freeze({ scoring_default: mode, v2_since: mode === 'v2' ? '2026-10-19' : null }); }
test.after(() => { require.cache[CONFIG].exports = original; });
const IDS = [...Object.keys(F.TICKERS), 'asml'], identities = IDS.map((id) => ({ company_id: id, ticker: id === 'asml' ? 'ASML' : F.TICKERS[id].split(':')[1] }));
const FACTORS = ['competitive_advantage', 'eps_fcf_per_share_growth', 'excess_growth_vs_industry', 'fcf_quality', 'financial_health', 'growth_durability', 'growth_efficiency', 'management_quality', 'margin_quality', 'market_position', 'next_3_5y_growth', 'revenue_growth', 'roic_wacc'];
function v1Screen() {
  const companies = {};
  for (const id of IDS) companies[id] = { state: 'LIVE', source_hashes: {}, factors: Object.fromEntries(FACTORS.map((f, i) => [f, { score: id === 'amd' && i > 6 ? null : 40 + i * 3, state: id === 'amd' && i > 6 ? 'NOT_AVAILABLE' : 'LIVE' }])) };
  return { schema_version: 1, kind: 'SEC_QG_FACTORS', as_of: '2026-10-13T00:00:00Z', state: 'LIVE', stale_after_seconds: 86400, data: { companies, availability_basis: 'OBSERVED_CAPTURE_ONLY' } };
}
const screens = { 'sec-qg-factors.json': v1Screen(), [SQ.FILE]: SQ.fromInputs(SQ.light(F.payload())) };
// Device prices as the app collects them: the Universe tab read (synthetic) mapped onto Universe codes and TARGET rows.
const universeWin = { PrivateSubsetView: { prices: () => new Map(Object.entries(F.quotes())) } };
let quotes = null;
test.before(async () => { quotes = await QS.collectQuotes(universeWin, { identities, v2Inputs: screens[SQ.FILE] }); });

test('the approved shipped setting is v2 and the accessor reads only that setting', () => {
  assert.equal(original.scoring_default, 'v2');
  assert.ok(Object.isFrozen(original));
  assert.equal(QS.scoringDefault(), 'v2');
  const src = fs.readFileSync(path.join(W, 'scoring-default.js'), 'utf8');
  assert.equal((src.match(/\{scoring_default:'v[12]',v2_since:(null|'\d{4}-\d{2}-\d{2}')\}/g) || []).length, 1, 'one-line flip');
  for (const f of ['leaderboard-screen.js', 'company-screen.js', 'daily-report.js', 'app.js', 'virtual-trading-signals.js']) assert.ok(!fs.readFileSync(path.join(W, f), 'utf8').includes('ScoringDefault'), f + ' reads scores through QgvScores only');
});

for (const mode of ['v1', 'v2']) test('flip to ' + mode + ': every consumer follows', () => {
  setDefault(mode);
  try {
    assert.equal(QS.scoringDefault(), mode);
    const sc = QS.compute({ identities, publicScreens: screens, quotes });
    assert.equal(sc.default, mode);assert.equal(sc.v2_state, 'READY');
    assert.deepEqual({ basis: sc.basis.basis, label: sc.basis.label }, mode === 'v2' ? { basis: 'v2', label: '기본' } : { basis: 'v1', label: '임시 기본' });
    // PLAYBOOK_V1 §13-11: until v2 is computed on the device, the basis is v1 labelled '임시 기본' even when the setting is v2.
    const noV2 = QS.compute({ identities, publicScreens: { 'sec-qg-factors.json': screens['sec-qg-factors.json'] } });
    assert.deepEqual([noV2.default, noV2.basis.label, noV2.basis.intended, noV2.rows.nvda.primary.version], ['v1', '임시 기본', mode, 'v1']);
    assert.ok(QS.basisText(noV2, false).endsWith('· 임시 기본'));
    assert.equal(typeof QS.judgmentRows(sc).nvda.value_trap_gate, 'boolean');
    const nvda = sc.rows.nvda;
    assert.equal(nvda.primary.version, mode);
    assert.equal(nvda.reference.version, mode === 'v2' ? 'v1_renormalized' : 'v2');
    assert.equal(nvda.code, 'TARGET:nvda', 'TARGET row preferred');assert.equal(sc.rows.asml.code, 'TARGET:asml');
    assert.ok(sc.rows.asml.v2.flags.includes('V_NOT_AVAILABLE'), 'EUR filer vs USD price: no FX, V NA');
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
    assert.equal(html.includes('(v2 · 산출 요인 '), mode === 'v2');
  } finally { require.cache[CONFIG].exports = original; }
});

test('v1 judgement rows keep the previous Q·G values exactly (official v1 engine path)', () => {
  const sc = QS.compute({ identities, publicScreens: screens, quotes, scoringDefault:'v1' });
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

test('sec-qgv2 adapter: published shape normalized (TTM first, FY fallback, TARGET rows, one point per CIK); price-like keys fail closed; collectQuotes RAM only', async () => {
  const inputs = SQ.fromInputs(SQ.light(F.payload())), r = inputs.records['NASDAQ:NVDA'], t = inputs.records['TARGET:nvda'];
  assert.equal(r.v_inputs.ebit, F.payload().records['NASDAQ:NVDA'].v_inputs_v2.ebit.ttm_value ?? F.payload().records['NASDAQ:NVDA'].v_inputs_v2.ebit.fy_value);
  assert.equal(inputs.records['NASDAQ:LRCX'].v_inputs.ebit, F.payload().records['NASDAQ:LRCX'].v_inputs_v2.ebit.ttm_value);
  assert.equal(r.v_inputs.cash, F.payload().records['NASDAQ:NVDA'].v_inputs_v2.cash_and_equivalents.value);
  assert.equal(r.v_inputs.ebit_per_share_history.length, 5);assert.equal(r.v_inputs.ebit_per_share_history[0].period_end, '2021-12-31');
  assert.equal(r.qg_axes.Q.score, F.payload().records['NASDAQ:NVDA'].axes.Q.score);assert.equal(r.in_cross_section, true);assert.equal(t.in_cross_section, false);
  assert.deepEqual([inputs.records['NASDAQ:GOOG'].in_cross_section, inputs.records['NASDAQ:GOOGL'].in_cross_section], [true, false], 'one cross-section point per CIK (first code)');
  assert.equal(inputs.records['TARGET:tokyo_electron'].v_inputs, null);assert.equal(inputs.records['NASDAQ:INTC'].factors.g_revenue_growth, null);
  const bad = F.payload();bad.records['NASDAQ:NVDA'].price = 1;assert.throws(() => SQ.light(bad), /SEC_QGV2_INVALID/);
  const code = F.payload();code.records['nvda'] = code.records['NASDAQ:NVDA'];assert.throws(() => SQ.fromInputs(code), /SEC_QGV2_INVALID/);
  assert.throws(() => SQ.light({ kind: 'OTHER', records: {} }), /SEC_QGV2_INVALID/);
  let used = null;const strict = { SecQgv2: { loadInputs: async () => { used = 'strict';return F.payload(); } } };
  assert.equal((await SQ.load(strict)).records['TARGET:nvda'].in_cross_section, false);assert.equal(used, 'strict');
  const universe = new Map([['NASDAQ:NVDA', { price: 50, currency: 'USD' }], ['NYSE:NOPE', { price: 9, currency: 'USD' }]]);
  const win = { PrivateSubsetView: { prices: () => universe }, DeviceValuation: { deviceQuote: async (w, c, tk) => (tk === 'AMD' ? { price: 30, currency: 'USD' } : null) },
    PriceStore: { monthEndCloses: async (sym) => (sym === 'NVDA' ? { '2024-12': 40, '2025-12': 45, bad: 3, '2023-12': 0 } : {}) } };
  const q = await QS.collectQuotes(win, { identities, v2Inputs: inputs, catalog: {} });
  assert.deepEqual(Object.keys(q).sort(), ['NASDAQ:NVDA', 'TARGET:amd', 'TARGET:nvda']);
  assert.deepEqual(q['TARGET:nvda'].month_closes, { '2024-12': 40, '2025-12': 45 });assert.equal(q['TARGET:nvda'].price, 50);
  assert.equal(q['TARGET:amd'].month_closes, undefined);
  assert.deepEqual(await QS.collectQuotes({}, { identities, v2Inputs: inputs }), {});
});

test('adapter on the real SecQgv2 validator output (Q·G side synthetic base vector): TARGET rows, published axes, device V', async () => {
  const SecQgv2 = require(path.join(W, 'sec-qgv2.js')), raw = SecQgv2.toInputs(F.strictPayload(), { now: '2026-10-14T00:00:00Z' }), inputs = SQ.fromInputs(raw);
  assert.deepEqual(inputs.target.nvda,raw.target.nvda,'the strict TARGET source row is preserved for exact-period confirmation');
  assert.notEqual(inputs.target.nvda,raw.target.nvda);
  assert.ok(Object.isFrozen(inputs.target)&&Object.isFrozen(inputs.target.nvda)&&Object.isFrozen(inputs.target.nvda.v_inputs_v2));
  assert.equal(inputs.count, 504 + Object.keys(SecQgv2.TARGET_CIKS).length);
  const ids = [{ company_id: 'nvda', ticker: 'NVDA' }, { company_id: 'msft', ticker: 'MSFT' }];
  const vals = F.strictUniverseValues().slice(1), q = await QS.collectQuotes({ PrivateSubsetView: { prices: () => new Map(vals.map((r) => [r[0], { price: r[2], currency: 'USD' }])) } }, { identities: ids, v2Inputs: inputs });
  const sc = QS.compute({ identities: ids, publicScreens: { [SQ.FILE]: inputs }, quotes: q, scoringDefault: 'v2' }), nv = sc.rows.nvda.v2;
  assert.equal(sc.rows.nvda.code, 'TARGET:nvda');assert.equal(nv.q, raw.target.nvda.axes.Q.score);assert.equal(nv.g, raw.target.nvda.axes.G.score);
  assert.ok(typeof nv.v === 'number' && typeof nv.total === 'number');assert.equal(sc.rows.msft.v2.v, null);assert.ok(sc.rows.msft.v2.flags.includes('V_NOT_AVAILABLE'));
});


test('approved playbook cyclical basis changes earnings basis without changing type weights', () => {
  const oldEngine=globalThis.PlaybookEngine,oldConfig=globalThis.PlaybookConfigDefaults;
  try {
    globalThis.PlaybookConfigDefaults={};
    globalThis.PlaybookEngine={sectorFor:()=>({sector:'semiconductors'}),classifyTypesV0:(_cfg,info)=>({cyclical:{member:info.sic==='3674'}})};
    const inputs=structuredClone(screens[SQ.FILE]);inputs.records['TARGET:nvda'].sic='3674';
    const calculated=QS.compute({identities,publicScreens:screens,v2Inputs:inputs,quotes,scoringDefault:'v2'}).rows.nvda.v2;
    assert.equal(calculated.detail.earnings_basis,'NORMALIZED');
    assert.equal(calculated.factors.v_earnings_yield.reason,'NORMALIZED_EARNINGS_NOT_AVAILABLE');
    assert.deepEqual(calculated.selected_types,[]);
  } finally {globalThis.PlaybookEngine=oldEngine;globalThis.PlaybookConfigDefaults=oldConfig;}
});


test('EBIT substitute rows (metrics.ebit_estimated_years) carry the EBIT_ESTIMATED flag "추정(대체 계산)"', () => {
  const base = QS.compute({ identities, publicScreens: screens, quotes, scoringDefault: 'v2' });
  const id = identities.map((c) => c.company_id).find((cid) => base.rows[cid].code && base.rows[cid].v2.state !== 'NOT_AVAILABLE');
  assert.ok(id, 'a v2 row to mark');
  for (const r of Object.values(base.rows)) assert.ok(!r.v2.flags.includes('EBIT_ESTIMATED'), 'no flag without the published count');
  const p = F.payload(), code = base.rows[id].code, row = code.startsWith('TARGET:') ? p.target[code.slice(7)] : p.records[code];
  row.metrics = { ...(row.metrics || {}), ebit_estimated_years: 2 };
  const marked = QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: SQ.fromInputs(SQ.light(p)) }, quotes, scoringDefault: 'v2' });
  assert.ok(marked.rows[id].v2.flags.includes('EBIT_ESTIMATED'));
  assert.ok(marked.rows[id].primary.flags.includes('EBIT_ESTIMATED'), 'the primary (v2 default) display carries it');
  assert.equal(Object.values(marked.rows).filter((r) => r.v2.flags.includes('EBIT_ESTIMATED')).length, 1);
  assert.deepEqual(QS.flagText(marked.rows[id].v2.flags.filter((f) => f === 'EBIT_ESTIMATED'), false), ['추정(대체 계산)']);
  assert.deepEqual(QS.flagText(['EBIT_ESTIMATED'], true), ['Estimate (substitute calculation)']);
  assert.ok(QS.judgmentRows(marked)[id].flags.includes('EBIT_ESTIMATED'));
  // A zero or missing count is not a flag (the file publishes the count only when >= 1).
  row.metrics.ebit_estimated_years = 0;
  const zero = QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: SQ.fromInputs(SQ.light(p)) }, quotes, scoringDefault: 'v2' });
  assert.ok(!zero.rows[id].v2.flags.includes('EBIT_ESTIMATED'));
});

test('calc_version: a row of another calculation-rule version is NA (CALC_VERSION_MISMATCH) and never in the device ranking population', () => {
  const V = 'qgv2-calc/2026-10-15.1', OLD = 'qgv2-calc/2026-10-14.1';
  const versioned = (mutate) => { const p = F.payload(); p.calc_version = V; for (const r of [...Object.values(p.records), ...Object.values(p.target || {})]) if (r && r.fiscal_year_end) r.calc_version = V; mutate(p); return SQ.fromInputs(SQ.light(p)); };
  const run = (inputs) => QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: inputs }, quotes, scoringDefault: 'v2' });
  const base = run(SQ.fromInputs(SQ.light(F.payload()))), same = run(versioned(() => {}));
  const ids = identities.map((c) => c.company_id).filter((cid) => base.rows[cid].code && base.rows[cid].v2.state !== 'NOT_AVAILABLE');
  assert.ok(ids.length >= 2, 'two v2 rows');
  for (const cid of ids) assert.equal(same.rows[cid].v2.total, base.rows[cid].v2.total, 'one version everywhere = the unversioned result');
  // Displayed row of another version: NA, no rank, flag text.
  const [odd] = ids, oddCode = base.rows[odd].code, pick = (p) => (oddCode.startsWith('TARGET:') ? p.target[oddCode.slice(7)] : p.records[oddCode]);
  const shown = versioned((p) => { pick(p).calc_version = OLD; });
  assert.equal(shown.calc_version, V);assert.equal(shown.records[oddCode].calc_version_mismatch, true);assert.equal(shown.records[oddCode].in_cross_section, false);
  const out = run(shown), row = out.rows[odd].v2;
  assert.equal(row.state, 'NOT_AVAILABLE');assert.equal(row.total, null);assert.equal(row.q, null);assert.equal(row.reason, 'CALC_VERSION_MISMATCH');
  assert.deepEqual(QS.flagText(row.flags, false), ['계산 규칙 버전이 달라 순위에서 제외']);
  assert.ok(QS.flagText(row.flags, true)[0].includes('calculation-rule version'));assert.equal(out.rows[odd].rank, null);
  // A pooled Universe point of another version leaves the population: every other row ranks exactly as if it were absent.
  const pooled = Object.keys(F.payload().records).find((code) => same.rows && SQ.fromInputs(SQ.light(F.payload())).records[code].in_cross_section && !ids.some((cid) => base.rows[cid].code === code));
  assert.ok(pooled, 'a pooled Universe row not shown directly');
  const mixed = run(versioned((p) => { p.records[pooled].calc_version = OLD; })), removed = run(versioned((p) => { delete p.records[pooled]; }));
  let changed = 0;for (const cid of ids) { assert.equal(mixed.rows[cid].v2.total, removed.rows[cid].v2.total, cid); if (mixed.rows[cid].v2.total !== same.rows[cid].v2.total) changed++; }
  assert.ok(changed > 0, 'the excluded point really changes the population');
  // A row without calc_version inside a versioned file is a legacy row: also excluded. A wholly unversioned file is one population.
  assert.equal(versioned((p) => { delete pick(p).calc_version; }).records[oddCode].calc_version_mismatch, true);
  const legacy = SQ.fromInputs(SQ.light(F.payload()));
  assert.equal(legacy.calc_version, null);assert.ok(Object.values(legacy.records).every((r) => r.calc_version_mismatch !== true));
});

test('a strictly valid empty SEC v2 file keeps v1 temporary default and blocks readiness', () => {
  const S=require(path.join(W,'sec-qgv2.js')),empty=F.strictPayload();
  empty.records=Object.fromEntries(Object.keys(empty.records).map(code=>[code,S.emptyRecord()]));
  empty.target=Object.fromEntries(Object.keys(empty.target).map(id=>[id,S.emptyRecord(['hanmi','tokyo_electron'].includes(id)?'NON_SEC_ISSUER':'NOT_COLLECTED')]));
  empty.cross_section_size=0;empty.cross_section_by_profile={GENERAL:0,FINANCIAL:0};empty.state='NOT_AVAILABLE';empty.reason_codes=['NO_ELIGIBLE_INPUT'];
  const inputs=SQ.fromInputs(S.toInputs(S.validate(empty))),computed=QS.compute({identities,publicScreens:screens,v2Inputs:inputs,scoringDefault:'v2'});
  assert.equal(computed.v2_state,'NOT_AVAILABLE');assert.equal(computed.v2_reason,'V2_SCORES_NOT_AVAILABLE');
  assert.equal(computed.default,'v1');assert.equal(computed.basis.label,'임시 기본');
});

test('DART reference Q/G uses the same composite but never enters the US rank pool', () => {
  const factors=Object.fromEntries(SQ.FACTORS.map(f=>[f,70])),referenceRows={asml:{reference_only:true,factors,axes:{Q:{score:70},G:{score:70}}}};
  const computed=QS.compute({identities,publicScreens:screens,quotes,scoringDefault:'v2',referenceRows});
  assert.equal(computed.rows.asml.primary.q,70);assert.equal(computed.rows.asml.primary.g,70);assert.equal(computed.rows.asml.primary.v,null);
  assert.equal(computed.rows.asml.primary.reference_only,true);assert.equal(computed.rows.asml.rank,null);
  assert.ok(QS.summaryText(computed.rows.asml.primary,false).startsWith('참고 순위 · '));
});
