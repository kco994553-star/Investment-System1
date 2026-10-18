'use strict';
// Every score consumer reads through QgvScores: S04/S05 (CompanyScreen), S06 (LeaderboardScreen), the virtual-trading rehearsal
// judgement rows, the daily report model and its export template. Owner decision 2026-10-14: QGV v2 is the ONLY score on
// screens; a stored 'v1' setting no longer brings v1 back and a missing v2 shows its NOT_AVAILABLE reason (never v1).
// Synthetic data only (tools/qgv_v2_fixture.js).
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

for (const mode of ['v1', 'v2']) test('setting ' + mode + ': every consumer shows QGV v2 only (no v1 primary, comparison or reference)', () => {
  setDefault(mode);
  try {
    assert.equal(QS.scoringDefault(), 'v2');
    const sc = QS.compute({ identities, publicScreens: screens, quotes });
    assert.equal(sc.default, 'v2');assert.equal(sc.v2_state, 'READY');
    assert.deepEqual({ basis: sc.basis.basis, label: sc.basis.label }, { basis: 'v2', label: '기본' });
    // Before v2 is computed on the device: the v2 NOT_AVAILABLE state with its reason, never v1 '임시 기본'.
    const noV2 = QS.compute({ identities, publicScreens: { 'sec-qg-factors.json': screens['sec-qg-factors.json'] } });
    assert.deepEqual([noV2.default, noV2.basis.label, noV2.basis.intended, noV2.rows.nvda.primary.version, noV2.rows.nvda.primary.state], ['v2', '기본', 'v2', 'v2', 'NOT_AVAILABLE']);
    assert.ok(QS.basisText(noV2, false).startsWith('점수 기준 v2 · PROVISIONAL · 기본') && !QS.basisText(noV2, false).includes('임시 기본'));
    assert.equal(QS.naText(noV2.rows.nvda.primary, false), 'QGV v2 산출 불가 · 이 기업의 v2 입력 없음');
    assert.equal(noV2.rows.nvda.primary.q, null, 'v1 Q is not shown in place of v2');
    assert.equal(typeof QS.judgmentRows(sc).nvda.value_trap_gate, 'boolean');
    const nvda = sc.rows.nvda;
    assert.equal(nvda.primary.version, 'v2');
    assert.equal(nvda.reference, null);assert.ok(!('v1' in nvda) && !('v1_renormalized' in nvda), 'no v1 on a display row');
    assert.equal(nvda.code, 'TARGET:nvda', 'TARGET row preferred');assert.equal(sc.rows.asml.code, 'TARGET:asml');
    assert.ok(sc.rows.asml.v2.flags.includes('V_NOT_AVAILABLE'), 'EUR filer vs USD price: no FX, V NA');
    assert.ok(typeof nvda.v2.total === 'number' && typeof nvda.v2.v === 'number', 'v2 has V from device quotes');
    assert.equal(sc.rows.gev.v2.v, null, 'no device price -> V NA, never 0');
    assert.ok(sc.rows.gev.v2.flags.includes('V_NOT_AVAILABLE'));
    // S06
    const rows = L.rowsFor(identities, { publicScreens: screens, scores: sc }), lr = rows.find((r) => r.company_id === 'nvda');
    assert.equal(lr.score.primary.version, 'v2');
    assert.ok(rows.filter((r) => r.score.rank !== null).length > 0);
    const auto = L.rowsFor(identities, { publicScreens: screens });
    assert.equal(auto.find((r) => r.company_id === 'nvda').score.primary.version, 'v2', 'rowsFor without scores uses the accessor');
    // S04 / S05
    const sum = CS.summary({ locale: 'ko-KR', id: 'nvda', screens, scores: sc, headerHtml: '', groupsHtml: '' });
    assert.ok(sum.includes('data-scoring-default="v2"'));
    const ana = CS.analysis({ locale: 'ko-KR', id: 'nvda', ticker: 'NVDA', screens, scores: sc, headerHtml: '' });
    assert.ok(sum.includes('data-qgv="total"') && sum.includes('산출 요인 '));
    for (const html of [sum, ana]) for (const gone of ['data-qgv-v1-reference', 'data-qgv-v2-compare', 'v1 참고', 'v2 비교용', '임시 기본', 'data-factor-table>', 'data-v1-axis-label', 'data-qgv-detail']) assert.ok(!html.includes(gone), gone);
    assert.ok(ana.includes('data-v2-factor-table') && ana.includes('data-overall="v2"'));
    assert.ok(sum.includes('점수 기준 v2 · PROVISIONAL') && sum.includes('DCF 참고 범위'));
    // Without v2 the company summary shows the v2 NOT_AVAILABLE reason (no v1 Q·G).
    const naSum = CS.summary({ locale: 'ko-KR', id: 'nvda', screens: { 'sec-qg-factors.json': screens['sec-qg-factors.json'] }, scores: noV2, headerHtml: '', groupsHtml: '' });
    assert.ok(naSum.includes('data-qgv2-na') && naSum.includes('QGV v2 산출 불가 · 이 기업의 v2 입력 없음') && naSum.includes('data-qgv="Q"'));
    assert.ok(!naSum.includes('점수 기준 v1') && !naSum.includes('임시 기본'));
    // Judgement rows: rehearsal snapshot + daily report + export
    const qg = QS.judgmentRows(sc);
    assert.equal(qg.nvda.version, 'v2');assert.equal(qg.nvda.compare, null);
    assert.equal(qg.nvda.q, nvda.v2.q);
    const snap = S.rehearsalSnapshot(qg);
    assert.equal(snap.nvda.q, qg.nvda.q);
    const model = R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-19', ram: { state: 'AVAILABLE', rows: [{ company_id: 'nvda', ticker: 'NVDA', weight: 0.1 }] }, qg, names: { nvda: 'NVDA' } });
    assert.equal(model.scoring, 'v2');
    const text = R.renderTemplate(model, { hidden: true, guide: false });
    assert.ok(text.includes('QGV 점수 기준 v2(PROVISIONAL)'));
    assert.ok(!text.includes('v1 참고') && !text.includes('v2 비교용') && !text.includes('점수 기준 v1'));
    const html = R.screenHtml(model, { hidden: true, locale: 'ko-KR' });
    assert.ok(html.includes('(v2 · 산출 요인 ') && !html.includes('QGV 점수 기준 v1'));
  } finally { require.cache[CONFIG].exports = original; }
});

test('without sec-qgv2.json the judgement rows and the report export stay v2 NOT_AVAILABLE (never the v1 Q·G)', () => {
  const plain = QS.judgmentRows(QS.compute({ identities, publicScreens: { 'sec-qg-factors.json': screens['sec-qg-factors.json'] } }));
  for (const id of IDS) {assert.equal(plain[id].version, 'v2');assert.equal(plain[id].q, null);assert.equal(plain[id].g, null);assert.equal(plain[id].total, null);assert.equal(plain[id].compare, null);}
  const text = R.renderTemplate(R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-19', ram: { state: 'AVAILABLE', rows: [{ company_id: 'nvda', ticker: 'NVDA', weight: 0.1 }] }, qg: plain, names: { nvda: 'NVDA' } }), { hidden: true, guide: false });
  assert.ok(!text.includes('v2 비교용') && !text.includes('v1(UNCALIBRATED)') && text.includes('QGV 점수 기준 v2(PROVISIONAL)'));
  assert.ok(text.includes('N/A (v2 · 산출 요인 0/15 · 산출 불가)'));
});

test('naText states why v2 is NOT_AVAILABLE: calculated factors and the axis below 50% of its weight', () => {
  const d = { version: 'v2', q: null, g: null, v: null, total: null, total_reason: 'AXIS_WEIGHT_INSUFFICIENT', factors_available: 3, factors_total: 15, flags: ['V_NOT_AVAILABLE'], state: 'NOT_AVAILABLE',
    axes: { Q: { score: null, reason: 'AXIS_WEIGHT_INSUFFICIENT' }, G: { score: null, reason: 'AXIS_WEIGHT_INSUFFICIENT' }, V: { score: null, reason: null } } };
  assert.equal(QS.naText(d, false), 'QGV v2 산출 불가 · 산출 요인 3/15 · Q 축 비중 50% 미만 · G 축 비중 50% 미만');
  assert.equal(QS.naText(d, true), 'QGV v2 not available · calculated factors 3/15 · Q axis below 50% of its weight · G axis below 50% of its weight');
  assert.equal(QS.naText(null, false), 'QGV v2 산출 불가 · 이 기업의 v2 입력 없음');
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
  row.metrics = { ...(row.metrics || {}), ebit_estimated_years: 2, ebit_estimated_fiscal_years: [2023, 2024] };
  const marked = QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: SQ.fromInputs(SQ.light(p)) }, quotes, scoringDefault: 'v2' });
  assert.ok(marked.rows[id].v2.flags.includes('EBIT_ESTIMATED'));
  assert.ok(marked.rows[id].primary.flags.includes('EBIT_ESTIMATED'), 'the primary (v2 default) display carries it');
  assert.equal(Object.values(marked.rows).filter((r) => r.v2.flags.includes('EBIT_ESTIMATED')).length, 1);
  assert.deepEqual(QS.flagText(marked.rows[id].v2.flags.filter((f) => f === 'EBIT_ESTIMATED'), false), ['추정(대체 계산)']);
  assert.deepEqual(QS.flagText(['EBIT_ESTIMATED'], true), ['Estimate (substitute calculation)']);
  // The flag names the substituted fiscal years when the display row is given (company screen, leaderboard).
  assert.deepEqual(marked.rows[id].v2.ebit_estimated_fiscal_years, [2023, 2024]);
  assert.deepEqual(QS.flagText(['EBIT_ESTIMATED'], false, marked.rows[id].v2), ['추정(대체 계산): FY2023·FY2024']);
  assert.deepEqual(QS.flagText(['EBIT_ESTIMATED'], true, marked.rows[id].v2), ['Estimate (substitute calculation): FY2023, FY2024']);
  assert.ok(QS.judgmentRows(marked)[id].flags.includes('EBIT_ESTIMATED'));
  // A zero or missing count is not a flag (the file publishes the count only when >= 1).
  row.metrics.ebit_estimated_years = 0;
  const zero = QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: SQ.fromInputs(SQ.light(p)) }, quotes, scoringDefault: 'v2' });
  assert.ok(!zero.rows[id].v2.flags.includes('EBIT_ESTIMATED'));
});

test('calc_version: a row of another calculation-rule version is NA (CALC_VERSION_MISMATCH) and never in the device ranking population', () => {
  const V = 'qgv2-calc/2026-10-17.1', OLD = 'qgv2-calc/2026-10-15.1';
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

test('normal-NA rows (source data missing) keep an explicit reason, stay in the 504 denominator, never CALC_VERSION_MISMATCH', () => {
  const S = require(path.join(W, 'sec-qgv2.js')), strict = F.strictPayload();
  assert.equal(strict.calc_version, 'qgv2-calc/2026-10-17.1');
  const inputs = SQ.fromInputs(S.toInputs(S.validate(strict), { now: '2026-10-14T00:00:00Z' }));
  const codes = Object.keys(inputs.records).filter((k) => !k.startsWith('TARGET:'));
  assert.equal(codes.length, 504, 'every Universe code stays in the denominator');
  const na = codes.filter((k) => inputs.records[k].state === 'NOT_AVAILABLE');
  assert.ok(na.length > 400);
  for (const k of na) {
    const r = inputs.records[k];
    assert.notEqual(r.calc_version_mismatch, true, k);assert.equal(r.in_cross_section, false, k);
    assert.ok(r.na_reasons.length >= 1 && r.na_reasons.every((x) => ['NOT_COLLECTED', 'CIK_UNRESOLVED', 'NO_ANNUAL_SEC_FINANCIALS', 'INVALID_INPUT', 'NON_SEC_ISSUER'].includes(x)), k);
  }
  const naCode = na.find((k) => inputs.records[k].na_reasons.includes('CIK_UNRESOLVED')) || na[0], ticker = naCode.slice(naCode.indexOf(':') + 1);
  const out = QS.compute({ identities: [{ company_id: 'na_row', ticker }], publicScreens: { [SQ.FILE]: inputs }, scoringDefault: 'v2' }), d = out.rows.na_row.v2;
  assert.equal(out.rows.na_row.code, naCode);assert.equal(d.total, null);assert.equal(d.total_reason, 'SOURCE_NOT_AVAILABLE');
  assert.ok(!d.flags.includes('CALC_VERSION_MISMATCH'));assert.deepEqual(d.source_reason_codes, [...inputs.records[naCode].na_reasons]);
  assert.match(QS.naText(d, false), /원자료 없음/);assert.match(QS.naText(d, true), /source data missing/);
});

test('a strictly valid empty SEC v2 file keeps the v2 basis NOT_AVAILABLE (no v1 temporary default) and blocks readiness', () => {
  const S=require(path.join(W,'sec-qgv2.js')),empty=F.strictPayload();
  empty.records=Object.fromEntries(Object.keys(empty.records).map(code=>[code,S.emptyRecord()]));
  empty.target=Object.fromEntries(Object.keys(empty.target).map(id=>[id,S.emptyRecord(['hanmi','tokyo_electron'].includes(id)?'NON_SEC_ISSUER':'NOT_COLLECTED')]));
  empty.cross_section_size=0;empty.cross_section_by_profile={GENERAL:0,FINANCIAL:0};empty.state='NOT_AVAILABLE';empty.reason_codes=['NO_ELIGIBLE_INPUT'];
  const inputs=SQ.fromInputs(S.toInputs(S.validate(empty))),computed=QS.compute({identities,publicScreens:screens,v2Inputs:inputs,scoringDefault:'v2'});
  assert.equal(computed.v2_state,'NOT_AVAILABLE');assert.equal(computed.v2_reason,'V2_SCORES_NOT_AVAILABLE');
  assert.equal(computed.default,'v2');assert.equal(computed.basis.label,'기본');assert.equal(computed.basis.ready,false);
  assert.equal(computed.rows.nvda.primary.version,'v2');assert.equal(computed.rows.nvda.primary.total,null);
});

test('DART reference Q/G uses the same composite but never enters the US rank pool', () => {
  const factors=Object.fromEntries(SQ.FACTORS.map(f=>[f,70])),referenceRows={asml:{reference_only:true,factors,axes:{Q:{score:70},G:{score:70}}}};
  const computed=QS.compute({identities,publicScreens:screens,quotes,scoringDefault:'v2',referenceRows});
  assert.equal(computed.rows.asml.primary.q,70);assert.equal(computed.rows.asml.primary.g,70);assert.equal(computed.rows.asml.primary.v,null);
  assert.equal(computed.rows.asml.primary.reference_only,true);assert.equal(computed.rows.asml.rank,null);
  assert.ok(QS.summaryText(computed.rows.asml.primary,false).startsWith('참고 순위 · '));
});

// Owner instruction 2026-10-17 item 3: a TARGET issuer withdrawn for an identity conflict (sec-qgv2.json TARGET withdrawal
// row) is scored and selected nowhere: not via its TARGET row, not via a Universe code of the same CIK (other share class),
// not via the Universe code of its ticker, and nothing from an earlier value. The stop is in the loader (Qgv2Inputs).
test('identity-conflict withdrawal: no score or candidate via the TARGET row, same-CIK codes or the ticker fallback', () => {
  const P = require(path.join(W, 'playbook-screen.js'));
  const p = F.payload(), empty = { state: 'NOT_AVAILABLE', acquired_at: null, fiscal_year_end: null, metrics: {}, factors: {}, axes: {}, v_inputs_v2: {} };
  const withdrawal = (cik) => ({ ...empty, cik, reason_codes: [SQ.WITHDRAWN_REASON], detected_at: '2026-10-13T12:00:00Z', withdrawn_acquired_at: '2026-10-12T00:00:00Z' });
  const before = QS.compute({ identities, publicScreens: screens, quotes, scoringDefault: 'v2' });
  assert.ok(Number.isFinite(before.rows.googl.primary.total) && Number.isFinite(before.rows.nvda.primary.total));
  p.target.googl = withdrawal(p.records['NASDAQ:GOOGL'].cik);   // GOOGL and GOOG carry this CIK
  p.target.nvda = withdrawal('0000099999');                       // a CIK no Universe code carries: the ticker fallback must not apply
  const inputs = SQ.fromInputs(SQ.light(p));
  for (const key of ['TARGET:googl', 'NASDAQ:GOOGL', 'NASDAQ:GOOG', 'TARGET:nvda']) {
    const r = inputs.records[key];
    assert.deepEqual([r.state, r.identity_withdrawn, r.in_cross_section, r.v_inputs, r.qg_axes.Q.score, r.qg_axes.G.score, r.na_reasons, r.metrics],
      ['WITHDRAWN', true, false, null, null, null, ['IDENTITY_CONFLICT_WITHDRAWN'], {}], key);
    assert.ok(Object.values(r.factors).every((v) => v === null), key);
  }
  assert.equal(inputs.records['NASDAQ:NVDA'].state, 'LIVE');     // another issuer's own Universe row is not the withdrawn one
  const computed = QS.compute({ identities, publicScreens: { ...screens, [SQ.FILE]: inputs }, quotes, scoringDefault: 'v2' });
  for (const id of ['googl', 'nvda']) {
    const row = computed.rows[id];
    assert.equal(row.code, 'TARGET:' + id);                      // never the Universe code of the same ticker
    assert.deepEqual([row.primary.total, row.primary.q, row.primary.g, row.primary.v, row.rank], [null, null, null, null, null]);
    assert.equal(row.primary.total_reason, 'SOURCE_NOT_AVAILABLE');
    assert.deepEqual(row.primary.source_reason_codes, ['IDENTITY_CONFLICT_WITHDRAWN']);
    assert.ok(QS.naText(row.primary, false).includes('식별 충돌로 사용 중지'));
  }
  assert.ok(Number.isFinite(computed.rows.msft.primary.total) && computed.rows.msft.rank !== null);   // others unchanged
  // Universe listings of the same issuer (other share class) as shown on Universe screens: no score either.
  const uni = QS.compute({ identities: [{ company_id: 'NASDAQ:GOOG', ticker: 'GOOG' }, { company_id: 'NASDAQ:GOOGL', ticker: 'GOOGL' }], publicScreens: { [SQ.FILE]: inputs }, quotes, scoringDefault: 'v2' });
  assert.ok(Object.values(uni.rows).every((r) => r.primary.total === null && r.rank === null));
  // Candidate selection (TARGET v1 writer ranking): never ranked, no industry, no Q/G.
  const ranked = P.candidateRanking(computed, { [SQ.FILE]: inputs }, ['NASDAQ:GOOGL', 'NASDAQ:GOOG', 'NASDAQ:NVDA', 'NASDAQ:MSFT']);
  const by = Object.fromEntries(ranked.map((r) => [r.code, r]));
  for (const code of ['NASDAQ:GOOGL', 'NASDAQ:GOOG']) assert.deepEqual([by[code].total, by[code].rank, by[code].industry, by[code].qg_available], [null, null, null, false], code);
  assert.equal(by['NASDAQ:NVDA'].total, null);                   // the TARGET company NVDA (identity row) has no score
  assert.ok(by['NASDAQ:MSFT'].rank !== null);
  // The device V population and the hanmi reference pool exclude the stopped rows.
  assert.ok(['TARGET:googl', 'NASDAQ:GOOGL', 'NASDAQ:GOOG'].every((k) => inputs.records[k].in_cross_section === false));
});

/* FE-MISSING-2 (owner instruction 2026-10-17): the reader now keeps the published Q/G axis coverage and the row's acquired_at /
   fiscal_year_end / profile for the screens. Scores, totals, ranks, flags and reasons must be byte-identical to the same inputs
   without those fields (the shape before this change), for every preset and gate, with and without device prices. */
test('published coverage fields are display only: scores, totals and ranks are byte-identical without them', () => {
  const SecQgv2 = require(path.join(W, 'sec-qgv2.js'));
  for (const payload of [F.strictPayload(), F.missingPayload()]) {
    const full = SQ.fromInputs(SecQgv2.toInputs(payload, { now: '2026-10-14T00:00:00Z' }));
    const before = { ...full, records: Object.fromEntries(Object.entries(full.records).map(([k, r]) => { const { acquired_at, fiscal_year_end, published_profile, ...rest } = r;
      return [k, { ...rest, qg_axes: { Q: { score: r.qg_axes.Q.score }, G: { score: r.qg_axes.G.score } } }]; })) };
    assert.ok(Object.values(full.records).some((r) => typeof r.qg_axes.Q.factors_available === 'string' && r.acquired_at), 'the new fields are present');
    const ids = Object.keys(full.records).filter((k) => !k.startsWith('TARGET:')).map((c) => ({ company_id: c.toLowerCase(), ticker: c.slice(c.indexOf(':') + 1) }))
      .concat(['amd', 'msft', 'nvda'].map((id) => ({ company_id: 't_' + id, ticker: id.toUpperCase() })));
    const priced = {};let i = 0;for (const [c, r] of Object.entries(full.records)) if (r.state === 'LIVE' && i++ % 3) priced[c] = { price: 10 + (i * 7) % 90, currency: 'USD' };
    const pick = (S) => JSON.stringify(Object.entries(S.rows).map(([id, r]) => { const p = r.primary;
      return [id, r.rank, r.code, p.q, p.g, p.v, p.total, p.total_reason, p.flags, p.factors_available, p.partial, p.state, p.axes, p.factors, p.weights, p.detail, p.value_trap_gate]; }));
    for (const quotes of [{}, priced]) for (const preset of Object.keys(globalThis.QgvV2.PRESETS)) for (const gate of [true, false]) {
      const a = pick(QS.compute({ identities: ids, v2Inputs: before, quotes, preset, gate })), b = pick(QS.compute({ identities: ids, v2Inputs: full, quotes, preset, gate }));
      assert.equal(b, a, preset + ' gate ' + gate + ' quotes ' + Object.keys(quotes).length);
    }
  }
});

test('coverage: partial / below-50% axis, FINANCIAL not-applicable, STALE source, exploration groups; NA never 0', () => {
  const SecQgv2 = require(path.join(W, 'sec-qgv2.js')), inputs = SQ.fromInputs(SecQgv2.toInputs(F.missingPayload(), { now: '2026-10-17T00:00:00Z' }));
  const ids = [['amd', 'AMD'], ['msft', 'MSFT'], ['nvda', 'NVDA'], ['googl', 'GOOGL'], ['gev', 'GEV']].map(([company_id, ticker]) => ({ company_id, ticker }));
  const quotes = { 'TARGET:amd': { price: 40, currency: 'USD' }, 'TARGET:nvda': { price: 50, currency: 'USD' } };
  for (const [c, r] of Object.entries(inputs.records)) if (!c.startsWith('TARGET:') && r.state === 'LIVE' && c !== 'NASDAQ:MSFT') quotes[c] = { price: 20 + c.length, currency: 'USD' };
  const S = QS.compute({ identities: ids, v2Inputs: inputs, quotes }), cov = (id) => S.rows[id].primary.coverage;
  // AMD: Q 2/5 = 45% of the original weight -> not calculated (published AXIS_COVERAGE_BELOW_50), G 4/5 = 85% partial, renormalized.
  const amd = cov('amd');assert.equal(amd.axes.Q.status, 'NOT_AVAILABLE');assert.equal(amd.axes.Q.reason, 'AXIS_COVERAGE_BELOW_50');
  assert.equal(amd.axes.Q.factors_available, 2);assert.ok(Math.abs(amd.axes.Q.weight_available - 0.45) < 1e-12);assert.deepEqual(amd.axes.Q.published.reason_codes, ['AXIS_COVERAGE_BELOW_50']);
  assert.equal(amd.axes.G.status, 'PARTIAL');assert.ok(Math.abs(amd.axes.G.weight_available - 0.85) < 1e-12);
  const shares = Object.fromEntries(amd.axes.G.factors.map((f) => [f.id, f.share]));assert.equal(shares.g_recent_acceleration, null);
  assert.ok(Math.abs(shares.g_revenue_growth - 100 * 25 / 85) < 1e-12);assert.ok(Math.abs(Object.values(shares).filter((x) => x !== null).reduce((a, b) => a + b, 0) - 100) < 1e-9);
  // The renormalized shares reproduce the published axis score (the engine's Σ(w·s)/Σ(w available)).
  assert.ok(Math.abs(amd.axes.G.factors.filter((f) => f.score !== null).reduce((a, f) => a + f.share * f.score / 100, 0) - S.rows.amd.primary.g) < 1e-9);
  assert.equal(amd.axes.G.factors.find((f) => f.id === 'g_recent_acceleration').reason, 'SEC_ITEMS_MISSING');
  assert.ok(amd.states.includes('PARTIAL'));assert.match(QS.naText({ ...S.rows.amd.primary, total: null, total_reason: 'AXIS_WEIGHT_INSUFFICIENT' }, false), /Q 축 비중 50% 미만/);
  // GOOGL (FINANCIAL profile row): earnings quality and V are 해당 없음, not missing data; Q is complete at 80% (4/5, 1 not applicable).
  const go = cov('googl');assert.equal(go.source.profile, 'FINANCIAL');assert.equal(go.axes.Q.status, 'READY');assert.equal(go.axes.Q.not_applicable, 1);
  assert.equal(go.axes.Q.factors.find((f) => f.id === 'q_earnings_quality').category, 'NOT_APPLICABLE');assert.equal(go.axes.V.status, 'NOT_APPLICABLE');
  assert.ok(go.states.includes('NOT_APPLICABLE') && !go.states.includes('PARTIAL') && !go.states.includes('PRICE_NEEDED'));
  // MSFT TARGET: STALE source with its basis dates; NVDA: LIVE, no price -> nothing; GEV: no data.
  assert.deepEqual([cov('msft').source.state, cov('msft').source.acquired_at, cov('msft').source.fiscal_year_end], ['STALE', '2026-09-20T00:00:00Z', '2025-12-31']);assert.ok(cov('msft').states.includes('STALE'));
  assert.deepEqual(cov('gev').states, ['SOURCE_MISSING']);
  // Exploration groups: ranked rows have a rank; Q·G-only rows (value preset, FINANCIAL: Q+G < 50%) never get one.
  const value = QS.compute({ identities: ids, v2Inputs: inputs, quotes, preset: 'value' });
  assert.equal(QS.exploreGroup(value.rows.googl), 'PARTIAL_AXES');assert.equal(value.rows.googl.rank, null);assert.equal(QS.exploreGroup(value.rows.gev), 'CHECK_DATA');
  assert.equal(QS.exploreGroup(S.rows.nvda), 'RANKED');
  // Price needed: no device price -> V says so instead of '50% 미만', and the price-free V inputs are checked separately.
  const bare = QS.compute({ identities: ids, v2Inputs: inputs, quotes: {}, preset: 'value' });assert.ok(bare.rows.nvda.primary.coverage.states.includes('PRICE_NEEDED'));
  assert.match(QS.naText(bare.rows.nvda.primary, false), /V 가격 입력 필요/);assert.deepEqual(bare.rows.nvda.primary.coverage.v_inputs_missing, []);
  // Rendered S04/S05 coverage: no NA factor shows a 0 score.
  for (const id of ['amd', 'googl', 'gev', 'msft']) {
    const html = CS.coverageHtml({ S, row: S.rows[id] }, 'ko-KR', { compact: true });assert.ok(html.includes('data-qgv-coverage'));
    for (const li of html.split('<li data-factor-coverage=').slice(1)) if (/data-factor-state="(?!OK)/.test(li)) assert.ok(!/점수 0/.test(li), id);
  }
});

// PERSONAL_PREVIEW two-level weights (owner directive 2026-10-18 §4.2): own memo and output key, never `primary`.
test('personal weights: separate output key, official rows byte-identical, coverage from the effective weights', () => {
  const V2 = globalThis.QgvV2, base = { identities, publicScreens: screens, quotes };
  const official = JSON.stringify(QS.compute(base));
  const tree = V2.officialWeights(); tree.inner.Q.q_profitability = 40; tree.inner.Q.q_moat_proxy = 0; tree.axis = { Q: 50, G: 30, V: 20 };
  const S = QS.compute({ ...base, weights: tree });
  const { personal, ...rest } = JSON.parse(JSON.stringify(S)), plain = JSON.parse(official);
  for (const r of Object.values(rest.rows)) { delete r.personal; delete r.personal_rank; }
  assert.deepEqual(rest, plain);                 // official result unchanged
  assert.equal(JSON.stringify(QS.compute(base)), official);                  // official memo not overwritten
  assert.equal(personal.state, 'READY'); assert.deepEqual(personal.label, QS.PERSONAL_LABEL);
  assert.equal(personal.label[0], '개인 설정 미리보기 · 공식 점수 아님');
  assert.equal(personal.profile.namespace, 'PERSONAL_PREVIEW'); assert.match(personal.profile.id, /^qgv-v2\/custom\/[0-9a-f]{16}\/gate-on$/);
  assert.notEqual(personal.profile.id, S.profile.id);
  let moved = 0;
  for (const [cid, row] of Object.entries(S.rows)) {
    assert.ok(row.primary === row.v2 && row.personal !== row.primary);
    if (row.personal.total !== null && row.primary.total !== null && Math.abs(row.personal.total - row.primary.total) > 1e-9) moved++;
    const q = row.personal.coverage && row.personal.coverage.axes ? row.personal.coverage.axes.Q : null;
    if (q) { assert.equal(q.weights, 'PERSONAL'); assert.deepEqual(q.excluded, ['q_moat_proxy']); assert.equal(q.factors_total, 4);
      const moat = q.factors.find((f) => f.id === 'q_moat_proxy'); assert.equal(moat.weight, 0); assert.equal(moat.official_weight, 20); assert.equal(moat.excluded, true); assert.equal(moat.share, null);
      assert.equal(q.factors.find((f) => f.id === 'q_profitability').weight, 40); }
    const oq = row.primary.coverage && row.primary.coverage.axes ? row.primary.coverage.axes.Q : null;
    if (oq) { assert.equal(oq.weights, undefined); assert.equal(oq.factors_total, 5); }
    // Personal ranks follow the same rule (total desc, ticker asc, NA unranked) and never replace the official rank.
    assert.equal(row.personal_rank === null, !(Number.isFinite(row.personal.total) && row.personal.reference_only !== true), cid);
  }
  assert.ok(moved > 0);
  const order = Object.values(S.rows).filter((r) => r.personal_rank !== null).sort((a, b) => a.personal_rank - b.personal_rank);
  for (let i = 1; i < order.length; i++) assert.ok(order[i - 1].personal.total > order[i].personal.total || (order[i - 1].personal.total === order[i].personal.total && order[i - 1].ticker < order[i].ticker));
  const bad = QS.compute({ ...base, weights: { axis: { Q: 0, G: 0, V: 0 }, inner: tree.inner } });
  assert.equal(bad.personal.state, 'INVALID'); assert.equal(bad.personal.reason, 'WEIGHTS_INVALID'); assert.ok(Object.values(bad.rows).every((r) => !('personal' in r)));
  const same = QS.compute({ ...base, weights: V2.officialWeights() });
  for (const row of Object.values(same.rows)) { assert.equal(row.personal.total, row.primary.total); assert.equal(row.personal_rank, row.rank); }
});

// User preset v0.1 candidates (owner decision 2026-10-18): personal rows carry the engine's weight stages; official rows never do.
test('user preset candidates: personal weight stages from the engine, official result byte-identical', () => {
  const V2 = globalThis.QgvV2, base = { identities, publicScreens: screens, quotes }, official = JSON.stringify(QS.compute(base));
  for (const id of Object.keys(V2.USER_PRESETS)) {
    const S = QS.compute({ ...base, weights: V2.userPreset(id).weights }), { personal, ...rest } = JSON.parse(JSON.stringify(S));
    for (const r of Object.values(rest.rows)) { delete r.personal; delete r.personal_rank; }
    assert.deepEqual(rest, JSON.parse(official), id);assert.equal(personal.state, 'READY');
    let staged = 0;
    for (const row of Object.values(S.rows)) {
      assert.ok(!('weight_stages' in row.primary), 'official row has no stages');
      const ws = row.personal.weight_stages;if (!ws) { assert.equal(row.personal.flags[0], 'V2_INPUTS_NOT_AVAILABLE');continue; }
      staged++;assert.deepEqual(ws.base.axis, V2.userPreset(id).weights.axis);assert.deepEqual(ws.type_adjusted.axis, row.personal.weights);
      if (Number.isFinite(row.personal.total)) { let t = 0;for (const p of ['Q', 'G', 'V']) if (ws.applied.axis[p] > 0) t += ws.applied.axis[p] * row.personal.axes[p].score / 100;assert.ok(Math.abs(t - row.personal.total) < 1e-9); }
      else assert.ok(ws.applied.state === 'NOT_AVAILABLE' || ws.display_stop, row.company_id);
    }
    assert.ok(staged > 0);
  }
  assert.equal(JSON.stringify(QS.compute(base)), official);
});

// S06 structured sort (owner directive 2026-10-18 §4.4): numeric keys, NA last both ways, QGV ties by ticker, cap ties by company_id.
test('S06 sortRows: structured keys, NA last in both directions, ties, official rank untouched', () => {
  const S = QS.compute({ identities, publicScreens: screens, quotes }), rows = identities.map((c) => ({ ...c, name: c.ticker.toLowerCase() }));
  const before = JSON.stringify(S), ranks = Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, r.rank]));
  const values = (out, f) => out.map((r) => f(S.rows[r.company_id]));
  const check = (id, f, dir) => {
    const out = L.sortRows(rows, S, id), v = values(out, f), firstNa = v.findIndex((x) => x === null);
    if (firstNa >= 0) assert.ok(v.slice(firstNa).every((x) => x === null), id + ' NA last');
    const known = v.slice(0, firstNa < 0 ? v.length : firstNa);
    for (let i = 1; i < known.length; i++) assert.ok(dir * (known[i] - known[i - 1]) >= 0, id + ' order');
    const na = out.slice(firstNa < 0 ? out.length : firstNa).map((r) => r.ticker);assert.deepEqual(na, [...na].sort((a, b) => a.localeCompare(b)), id + ' NA by ticker');
    return out;
  };
  const qgvDesc = check('qgv', (r) => (r.rank === null ? null : r.primary.total), -1);
  assert.deepEqual(qgvDesc.filter((r) => S.rows[r.company_id].rank !== null).map((r) => S.rows[r.company_id].rank), qgvDesc.filter((r) => S.rows[r.company_id].rank !== null).map((_, i) => i + 1));
  check('qgv-asc', (r) => (r.rank === null ? null : r.primary.total), 1);
  for (const a of ['q', 'g', 'v']) { check(a + '-desc', (r) => r.primary[a], -1); check(a + '-asc', (r) => r.primary[a], 1); }
  assert.ok(values(L.sortRows(rows, S, 'v-desc'), (r) => r.primary.v).some((x) => x === null), 'fixture has a V NA row');
  // Legacy ids are ordered by DeviceWatchlist.filter: unchanged here.
  for (const id of ['ticker', 'name', 'favorites']) assert.equal(L.sortRows(rows, S, id), rows);
  assert.deepEqual(L.sortRows(rows, S, 'ticker-desc').map((r) => r.ticker), rows.map((r) => r.ticker).sort((a, b) => b.localeCompare(a)));
  // QGV ties by ticker in both directions.
  const tieS = { rows: { a: { rank: 1, primary: { total: 50 } }, b: { rank: 2, primary: { total: 50 } }, c: { rank: null, primary: { total: null } } } }, tieRows = [{ company_id: 'c', ticker: 'AAA' }, { company_id: 'b', ticker: 'BBB' }, { company_id: 'a', ticker: 'ZZZ' }];
  assert.deepEqual(L.sortRows(tieRows, tieS, 'qgv').map((r) => r.company_id), ['b', 'a', 'c']);assert.deepEqual(L.sortRows(tieRows, tieS, 'qgv-asc').map((r) => r.company_id), ['b', 'a', 'c']);
  // Market cap: M3 rank (1 = largest), ties by company_id, NA last; unavailable without the device subset.
  const ranksM3 = { state: 'READY', entries: new Map([['id:nvda', { state: 'READY', rank: 1, reason_codes: [] }], ['id:amd', { state: 'READY', rank: 2, reason_codes: [] }], ['id:asml', { state: 'READY', rank: 2, reason_codes: [] }]]) };
  const cap = L.sortRows(rows, S, 'cap-desc', { deviceRanks: ranksM3 }).map((r) => r.company_id);assert.deepEqual(cap.slice(0, 3), ['nvda', 'amd', 'asml']);
  assert.deepEqual(L.sortRows(rows, S, 'cap-asc', { deviceRanks: ranksM3 }).map((r) => r.company_id).slice(0, 3), ['amd', 'asml', 'nvda']);
  assert.equal(L.sortAvailable('cap-desc', { deviceRanks: null }), false);assert.equal(L.sortAvailable('cap-desc', { deviceRanks: ranksM3 }), true);assert.equal(L.sortAvailable('q-asc', {}), true);
  assert.equal(L.oppositeSort('qgv'), 'qgv-asc');assert.equal(L.oppositeSort('name'), 'name-desc');assert.equal(L.oppositeSort('favorites'), null);
  assert.ok(L.SORT_IDS.includes('asof-desc') && !L.SORT_IDS.some((id) => /return|1d|5d|20d/i.test(id)), 'no return sort without a return column');
  check('asof-desc', (r) => { const t = Date.parse(r.primary.coverage?.source?.acquired_at); return Number.isFinite(t) ? t : null; }, -1);
  assert.equal(JSON.stringify(S), before);assert.deepEqual(Object.fromEntries(Object.entries(S.rows).map(([k, r]) => [k, r.rank])), ranks);
  assert.equal(L.populationOf(screens), Object.values(screens[SQ.FILE].records).filter((r) => r.in_cross_section === true && ['LIVE', 'STALE'].includes(r.state) && r.calc_version_mismatch !== true).length);
});

/* Shared page result (owner decision 2026-10-18): the V coverage panel and the stat radar read ONE collectQuotes + compute over the
   whole loaded file. One input gives the same V per row through pageResult as through a direct compute over the same quotes. */
test('pageResult: one memoized quote set + compute over the whole file; same V per row as a direct compute; vCoverage counts', async () => {
  const inputs = screens[SQ.FILE], prices = new Map(Object.entries(F.quotes()));let basis = null;
  const win = { PrivateSubsetView: { prices: () => (basis ? prices : null), priceBasis: () => basis } };
  const before = await QS.pageResult(win, { v2Inputs: inputs, identities });
  assert.equal(before.price_basis, null);assert.deepEqual(before.quotes, {});const c0 = QS.vCoverage(before, inputs);
  assert.equal(c0.connected, false);assert.equal(c0.v, null);assert.equal(c0.reasons, null);assert.equal(c0.price_time, null);
  basis = { source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_a', acquired_at: '2026-10-18T09:00:00.000Z', currency: 'USD', price_time: null };
  const r = await QS.pageResult(win, { v2Inputs: inputs, identities });assert.notEqual(r, before, 'a Universe read is a new revision');
  assert.equal(QS.pageResult(win, { v2Inputs: inputs, identities }), QS.pageResult(win, { v2Inputs: inputs, identities }), 'memoized');
  const codes = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:'));
  assert.deepEqual(r.identities.map((c) => c.company_id), [...identities.map((c) => c.company_id), ...codes.filter((c) => !identities.some((x) => x.company_id === c))]);
  assert.deepEqual(r.quotes, await QS.collectQuotes(win, { identities, v2Inputs: inputs }), 'the existing collectQuotes, unchanged');
  const direct = QS.compute({ identities: r.identities, v2Inputs: inputs, quotes: structuredClone(r.quotes) }), small = QS.compute({ identities, v2Inputs: inputs, quotes: structuredClone(r.quotes) });
  let withV = 0;for (const c of r.identities) { const a = r.computed.rows[c.company_id].primary, b = direct.rows[c.company_id].primary;assert.equal(a.v, b.v, c.company_id);assert.equal(a.total, b.total, c.company_id);if (Number.isFinite(a.v)) withV++; }
  for (const c of identities) assert.equal(small.rows[c.company_id].primary.v, r.computed.rows[c.company_id].primary.v, 'identity subset ' + c.company_id);
  assert.ok(withV >= 3);
  for (const code of Object.keys(r.quotes)) assert.deepEqual(r.quote_meta[code], { source: 'UNIVERSE_SHEET', as_of: null, stale: false }, 'GOOGLEFINANCE has no price time');
  const cov = QS.vCoverage(r, inputs), P = cov.population, rows = codes.map((c) => ({ rec: inputs.records[c], p: r.computed.rows[c].primary }));
  assert.equal(P.total, codes.length);assert.equal(P.general + P.financial + P.unknown + P.stopped, P.total);
  assert.equal(P.general, rows.filter((x) => x.rec.published_profile === 'GENERAL').length);assert.ok(P.financial >= 1);
  assert.equal(cov.v.general, rows.filter((x) => x.rec.published_profile === 'GENERAL' && Number.isFinite(x.p.v)).length);
  assert.equal(cov.target.n, Math.ceil(0.9 * P.general - 1e-9));assert.equal(cov.target.observation_only, true);assert.equal(cov.target.met, cov.v.general >= cov.target.n);
  assert.equal(cov.reasons.reduce((a, [, n]) => a + n, 0), P.general - cov.v.general);assert.ok(!cov.reasons.some(([c]) => c === 'FINANCIAL_PROFILE_V_NOT_DEFINED'));
  assert.equal(cov.qg_only_total.full, cov.qg_only_total.financial + cov.qg_only_total.no_v + cov.qg_only_total.gate);
  assert.deepEqual(cov.price_time.map((t) => [t.source, t.rows === t.unconfirmed]), [['UNIVERSE_SHEET', true]]);assert.equal(cov.read_at, basis.acquired_at);
  // A device quote that carries its own time keeps it per source (meta); the Universe tab never does.
  const meta = {}, dq = await QS.collectQuotes({ DeviceValuation: { deviceQuote: async () => ({ price: 10, currency: 'USD', as_of: '2026-10-16', source: 'WORKER_CLOSE', stale: true }) } }, { identities, v2Inputs: inputs, catalog: {}, meta });
  assert.ok(Object.keys(dq).length >= 3);for (const code of Object.keys(dq)) assert.deepEqual(meta[code], { source: 'WORKER_CLOSE', as_of: '2026-10-16', stale: true });
  assert.ok(Object.values(dq).every((q) => Object.keys(q).sort().join() === 'currency,price'), 'quotes themselves unchanged (no time field)');
  assert.equal(QS.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED'), '현재 금융업 가치평가 모델 미지원');assert.equal(QS.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED', true), 'Valuation model for financials not supported yet');
});
