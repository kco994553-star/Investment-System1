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
    PriceStore: { monthEndCloses: async (sym, o) => { storeOptions.push(o); return sym === 'NVDA' ? { '2024-12': 40, '2025-12': 45, bad: 3, '2023-12': 0 } : {}; } } };
  const storeOptions = [];
  const q = await QS.collectQuotes(win, { identities, v2Inputs: inputs, catalog: {} });
  // Click-only rule (owner decision 2026-10-23): the screen-open quote collection reads the stored month-ends only.
  assert.ok(storeOptions.length > 0 && storeOptions.every((o) => o && o.fetch === false), 'every month-end read passes fetch:false');
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
  assert.equal(strict.calc_version, 'qgv2-calc/2026-10-23.1');
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
  for (const r of Object.values(rest.rows)) { delete r.personal; delete r.personal_rank; delete r.personal_qg_reference; }
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
    // Personal ranks follow the same rule (total desc, ticker asc, NA unranked; D11: a total without V is in the personal QG
    // 참고 목록, not ranked) and never replace the official rank.
    const qgOnly = Number.isFinite(row.personal.total) && !Number.isFinite(row.personal.v) && row.personal.reference_only !== true;
    assert.equal(row.personal_rank === null, !(Number.isFinite(row.personal.total) && row.personal.reference_only !== true) || qgOnly, cid);
    assert.equal(row.personal_qg_reference !== null, qgOnly, cid);
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
    for (const r of Object.values(rest.rows)) { delete r.personal; delete r.personal_rank; delete r.personal_qg_reference; }
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
  // D11: the QGV sort lists the official ranking (rows with V) first, then the QG 참고 목록 (Q·G-only totals) in its own order, then
  // rows without a total; the two lists are never interleaved. Each segment is checked on its own.
  const qgvCheck = (id, dir) => {
    const out = L.sortRows(rows, S, id), tier = (r) => (r.rank !== null ? 0 : r.qg_reference ? 1 : 2), t = out.map((r) => tier(S.rows[r.company_id]));
    for (let i = 1; i < t.length; i++) assert.ok(t[i] >= t[i - 1], id + ' official, then QG reference, then NA');
    for (const k of [0, 1]) { const v = out.filter((_, i) => t[i] === k).map((r) => S.rows[r.company_id].primary.total);for (let i = 1; i < v.length; i++) assert.ok(dir * (v[i] - v[i - 1]) >= 0, id + ' order in segment ' + k); }
    const na = out.filter((_, i) => t[i] === 2).map((r) => r.ticker);assert.deepEqual(na, [...na].sort((a, b) => a.localeCompare(b)), id + ' NA by ticker');
    return out;
  };
  const qgvDesc = qgvCheck('qgv', -1);
  assert.deepEqual(qgvDesc.filter((r) => S.rows[r.company_id].rank !== null).map((r) => S.rows[r.company_id].rank), qgvDesc.filter((r) => S.rows[r.company_id].rank !== null).map((_, i) => i + 1));
  assert.deepEqual(qgvDesc.filter((r) => S.rows[r.company_id].qg_reference).map((r) => S.rows[r.company_id].qg_reference.order), qgvDesc.filter((r) => S.rows[r.company_id].qg_reference).map((_, i) => i + 1));
  assert.ok(Object.values(S.rows).some((r) => r.qg_reference), 'fixture has a Q·G-only row (GEV: no price)');
  qgvCheck('qgv-asc', 1);
  for (const a of ['q', 'g', 'v']) { check(a + '-desc', (r) => r.primary[a], -1); check(a + '-asc', (r) => r.primary[a], 1); }
  assert.ok(values(L.sortRows(rows, S, 'v-desc'), (r) => r.primary.v).some((x) => x === null), 'fixture has a V NA row');
  // Legacy ids are ordered by DeviceWatchlist.filter: unchanged here.
  for (const id of ['ticker', 'name', 'favorites']) assert.equal(L.sortRows(rows, S, id), rows);
  assert.deepEqual(L.sortRows(rows, S, 'ticker-desc').map((r) => r.ticker), rows.map((r) => r.ticker).sort((a, b) => b.localeCompare(a)));
  // QGV ties by the place number (the publication's tie order), not the ticker: high first = rank order (#1 'ZZZ' above #2 'BBB'),
  // low first = its exact reverse; the same in the QG list by QG order. The ticker still orders rows without a place (NA, above).
  const tieS = { rows: { a: { rank: 1, primary: { total: 50 } }, b: { rank: 2, primary: { total: 50 } }, c: { rank: null, primary: { total: null } }, d: { rank: null, qg_reference: { order: 1 }, primary: { total: 40 } }, e: { rank: null, qg_reference: { order: 2 }, primary: { total: 40 } } } };
  const tieRows = [{ company_id: 'c', ticker: 'AAA' }, { company_id: 'b', ticker: 'BBB' }, { company_id: 'a', ticker: 'ZZZ' }, { company_id: 'e', ticker: 'CCC' }, { company_id: 'd', ticker: 'YYY' }];
  assert.deepEqual(L.sortRows(tieRows, tieS, 'qgv').map((r) => r.company_id), ['a', 'b', 'd', 'e', 'c']);assert.deepEqual(L.sortRows(tieRows, tieS, 'qgv-asc').map((r) => r.company_id), ['b', 'a', 'e', 'd', 'c']);
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
  // D12: the identities are the official populations, one row per security: a TARGET identity whose ticker is a Universe code IS
  // that code (no second row), then every other Universe code; TARGET outside the Universe stay rows (never ranked).
  const U = QS.universeIdentities(inputs, identities);
  assert.deepEqual(r.identities.map((c) => c.company_id), U.identities.map((c) => c.company_id));
  assert.deepEqual(r.identities.map((c) => c.company_id), [...identities.map((c) => c.company_id), ...codes.filter((c) => !identities.some((x) => x.company_id === c || x.ticker.replaceAll('.', '-').toUpperCase() === c.slice(c.indexOf(':') + 1)))]);
  for (const { company_id, code } of U.target_in_universe) assert.ok(!r.computed.rows[code] && r.computed.rows[company_id], code + ' is the row ' + company_id);
  assert.deepEqual(r.quotes, await QS.collectQuotes(win, { identities, v2Inputs: inputs }), 'the existing collectQuotes, unchanged');
  const direct = QS.compute({ identities: r.identities, v2Inputs: inputs, quotes: structuredClone(r.quotes) }), small = QS.compute({ identities, v2Inputs: inputs, quotes: structuredClone(r.quotes) });
  let withV = 0;for (const c of r.identities) { const a = r.computed.rows[c.company_id].primary, b = direct.rows[c.company_id].primary;assert.equal(a.v, b.v, c.company_id);assert.equal(a.total, b.total, c.company_id);if (Number.isFinite(a.v)) withV++; }
  for (const c of identities) assert.equal(small.rows[c.company_id].primary.v, r.computed.rows[c.company_id].primary.v, 'identity subset ' + c.company_id);
  assert.ok(withV >= 3);
  for (const code of Object.keys(r.quotes)) assert.deepEqual(r.quote_meta[code], { source: 'UNIVERSE_SHEET', as_of: null, stale: null }, 'GOOGLEFINANCE has no price time: freshness 판정 불가 (D10)');
  // D12: per code, the row standing for it (a TARGET company's code is its TARGET row) and the record that row was scored from.
  const cov = QS.vCoverage(r, inputs), P = cov.population, rows = codes.map((c) => { const row = QS.codeRow(r.computed, c), own = inputs.records[c], src = row && row.code !== c && inputs.records[row.code] && own.identity_withdrawn !== true ? row.code : c;return { rec: inputs.records[src], p: row.primary }; });
  assert.equal(P.total, codes.length);assert.equal(P.general + P.financial + P.unknown + P.stopped, P.total);
  assert.equal(P.general, rows.filter((x) => x.rec.published_profile === 'GENERAL').length);assert.ok(P.financial >= 1);
  assert.equal(cov.v.general, rows.filter((x) => x.rec.published_profile === 'GENERAL' && Number.isFinite(x.p.v)).length);
  assert.equal(cov.target.n, Math.ceil(0.9 * P.general - 1e-9));assert.equal(cov.target.observation_only, true);assert.equal(cov.target.met, cov.v.general >= cov.target.n);
  assert.equal(cov.reasons.reduce((a, [, n]) => a + n, 0), P.general - cov.v.general);assert.ok(!cov.reasons.some(([c]) => c === 'FINANCIAL_PROFILE_V_NOT_DEFINED'));
  // Q·G-only totals exclude value-trap-gate rows (V computed, excluded by the approved rule): financial + no-V only; gate apart.
  const total = (x) => Number.isFinite(x.p.total), hasV = (x) => Number.isFinite(x.p.v);
  assert.equal(cov.qg_only_total.full, cov.qg_only_total.financial + cov.qg_only_total.no_v);
  assert.equal(cov.qg_only_total.full, rows.filter((x) => total(x) && !hasV(x)).length);
  assert.equal(cov.qg_only_total.general, rows.filter((x) => x.rec.published_profile === 'GENERAL' && total(x) && !hasV(x)).length);
  assert.equal(cov.qg_only_total.financial, rows.filter((x) => x.rec.published_profile === 'FINANCIAL' && total(x) && !hasV(x)).length);
  assert.equal(cov.qg_only_total.gate, rows.filter((x) => total(x) && hasV(x) && x.p.v_excluded).length);assert.ok(cov.qg_only_total.gate >= 1, 'fixture has gate rows');
  assert.deepEqual(cov.price_time.map((t) => [t.source, t.rows === t.unconfirmed]), [['UNIVERSE_SHEET', true]]);
  assert.deepEqual(cov.price_time.map((t) => [t.confirmed, t.stale, t.from, t.to]), [[0, 0, null, null]], 'Universe rows: never dated, never stale (D10)');assert.equal(cov.read_at, basis.acquired_at);
  // A device quote that carries its own time keeps it per source (meta); the Universe tab never does.
  const meta = {}, dq = await QS.collectQuotes({ DeviceValuation: { deviceQuote: async () => ({ price: 10, currency: 'USD', as_of: '2026-10-16', source: 'WORKER_CLOSE', stale: true }) } }, { identities, v2Inputs: inputs, catalog: {}, meta });
  assert.ok(Object.keys(dq).length >= 3);for (const code of Object.keys(dq)) assert.deepEqual(meta[code], { source: 'WORKER_CLOSE', as_of: '2026-10-16', stale: true });
  assert.ok(Object.values(dq).every((q) => Object.keys(q).sort().join() === 'currency,price'), 'quotes themselves unchanged (no time field)');
  // D10: a device quote without its own price time (ramQuote as_of null, GOOGLEFINANCE UNKNOWN) is 판정 불가, not 'not stale'.
  const meta2 = {};await QS.collectQuotes({ DeviceValuation: { deviceQuote: async () => ({ price: 10, currency: 'USD', as_of: null, read_at: '2026-10-18T09:00:00.000Z', time_status: 'UNKNOWN', freshness: 'UNDETERMINED', source: 'GOOGLEFINANCE', stale: false }) } }, { identities, v2Inputs: inputs, catalog: {}, meta: meta2 });
  for (const code of Object.keys(meta2)) assert.deepEqual(meta2[code], { source: 'GOOGLEFINANCE', as_of: null, stale: null });
  const meta3 = {};await QS.collectQuotes({ DeviceValuation: { deviceQuote: async () => ({ price: 10, currency: 'USD', as_of: '2026-10-17T20:00:00Z', freshness: 'CURRENT', source: 'GOOGLEFINANCE', stale: false }) } }, { identities, v2Inputs: inputs, catalog: {}, meta: meta3 });
  for (const code of Object.keys(meta3)) assert.deepEqual(meta3[code], { source: 'GOOGLEFINANCE', as_of: '2026-10-17T20:00:00Z', stale: false });
  assert.equal(QS.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED'), '현재 금융업 가치평가 모델 미지원');assert.equal(QS.reasonText('FINANCIAL_PROFILE_V_NOT_DEFINED', true), 'Valuation model for financials not supported yet');
});

// D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다'): official rank only with V; Q·G-only totals go to the QG
// 참고 목록 with the engine's reason; the value-trap-gate row (V computed, excluded by the gate) stays ranked; totals untouched;
// a personal tree with V weight 0 is labelled and ranked as that personal result only.
test('D11 rank split: official rank needs V, QG reference list, gate row ranked, personal V=0 label', () => {
  const SecQgv2 = require(path.join(W, 'sec-qgv2.js')), p = F.strictPayload(), amd = p.target.amd;
  Object.assign(amd.metrics, { roic: -0.5, gross_profit_to_assets: -0.5, moat_proxy: -0.5, accruals_to_assets: 0.5, fcf_to_net_income: -2, net_debt_to_ebitda: 20, interest_coverage: -5, dilution_3y: 0.5, incremental_roic_5y: -0.5 });
  const { scores } = SecQgv2.scoreRows(p.records, p.target, p.calc_version), sc = scores.get('target\u0000amd');amd.factors = sc.factors;amd.axes = sc.axes;
  const inputs = SQ.fromInputs(SecQgv2.toInputs(SecQgv2.validate(p), { now: '2026-10-14T00:00:00Z' }));
  const ids = [['amd', 'AMD'], ['msft', 'MSFT'], ['nvda', 'NVDA'], ['googl', 'GOOGL'], ['amzn', 'AMZN'], ['gev', 'GEV']].map(([company_id, ticker]) => ({ company_id, ticker }));
  const quotes = { 'TARGET:amd': { price: 40, currency: 'USD' }, 'TARGET:nvda': { price: 50, currency: 'USD' } };
  for (const [c, r] of Object.entries(inputs.records)) if (!c.startsWith('TARGET:') && r.state === 'LIVE' && c !== 'NASDAQ:MSFT') quotes[c] = { price: 20 + c.length, currency: 'USD' };
  const S = QS.compute({ identities: ids, v2Inputs: inputs, quotes }), R = S.rows;
  assert.equal(R.amd.primary.value_trap_gate, true);assert.ok(Number.isFinite(R.amd.primary.v));assert.equal(R.amd.primary.v_excluded, 'VALUE_TRAP_GATE');
  assert.ok(Number.isInteger(R.amd.rank) && R.amd.qg_reference === null, 'gate row stays ranked');assert.equal(QS.exploreGroup(R.amd), 'RANKED');
  assert.ok(Number.isInteger(R.nvda.rank));
  for (const [id, reason] of [['msft', 'NO_DEVICE_PRICE'], ['googl', 'FINANCIAL_PROFILE_V_NOT_DEFINED'], ['amzn', 'FINANCIAL_PROFILE_V_NOT_DEFINED']]) {
    assert.equal(R[id].rank, null, id);assert.equal(R[id].qg_reference.reason, reason, id);assert.equal(QS.exploreGroup(R[id]), 'QG_REFERENCE', id);assert.ok(Number.isFinite(R[id].primary.total), id + ' keeps its total');
  }
  assert.deepEqual(['msft', 'googl', 'amzn'].sort((a, b) => R[a].qg_reference.order - R[b].qg_reference.order), ['msft', 'googl', 'amzn'].sort((a, b) => R[b].primary.total - R[a].primary.total || (R[a].ticker < R[b].ticker ? -1 : 1)));
  assert.equal(R.gev.rank, null);assert.equal(R.gev.qg_reference, null);assert.equal(QS.exploreGroup(R.gev), 'CHECK_DATA');
  assert.deepEqual([R.amd.rank, R.nvda.rank].sort(), [1, 2]);
  assert.equal(QS.reasonText(R.googl.qg_reference.reason, false), '현재 금융업 가치평가 모델 미지원');assert.equal(QS.QG_REFERENCE_LABEL[0], 'QG 참고 목록 (V 미포함)');
  assert.equal(QS.NO_OFFICIAL_RANK[0], '공식 V 없음: 공식 QGV 순위 없음 · QG 참고 목록 보기');
  // Before any price: nobody is ranked; every total is in the QG list.
  const bare = QS.compute({ identities: ids, v2Inputs: inputs, quotes: {} });
  assert.ok(Object.values(bare.rows).every((r) => r.rank === null));assert.ok(Object.values(bare.rows).filter((r) => Number.isFinite(r.primary.total)).every((r) => r.qg_reference));
  // Personal V weight 0: labelled, every personal total ranked as that personal result; the official rows do not change.
  const tree = globalThis.QgvV2.officialWeights();tree.axis = { Q: 50, G: 50, V: 0 };const P = QS.compute({ identities: ids, v2Inputs: inputs, quotes, weights: tree });
  assert.equal(P.personal.v_weight_zero, true);assert.deepEqual(P.personal.label, QS.PERSONAL_V0_LABEL);assert.ok(P.personal.label[0].startsWith('개인 설정 결과 (V 비중 0)'));
  for (const r of Object.values(P.rows)) { assert.equal(Number.isInteger(r.personal_rank), Number.isFinite(r.personal.total), r.company_id);assert.equal(r.personal_qg_reference, null);
    assert.equal(r.rank, R[r.company_id].rank);assert.deepEqual(r.qg_reference, R[r.company_id].qg_reference); }
  const P2 = QS.compute({ identities: ids, v2Inputs: inputs, quotes, weights: globalThis.QgvV2.officialWeights() });assert.notEqual(P2.personal.v_weight_zero, true);assert.deepEqual(P2.personal.label, QS.PERSONAL_LABEL);
  assert.equal(P2.rows.msft.personal_rank, null);assert.equal(P2.rows.msft.personal_qg_reference.reason, 'NO_DEVICE_PRICE');
});
test('provenance labels (owner 2026-10-19): official weights vs personal preset vs gate off, device prices, central publication; values untouched', () => {
  const inputs = screens[SQ.FILE], V2 = globalThis.QgvV2, run = (preset, gate) => QS.compute({ identities, v2Inputs: inputs, quotes, preset, gate });
  // The four facts per profile. QGV totals, ranks and N sets are always computed on this device (no central V/QGV publication).
  const cases = [[undefined, undefined, 'OFFICIAL', 'NONE', '공식 가중치 · 이 기기 가격 · 기기 계산'], ['balanced', true, 'OFFICIAL', 'NONE', '공식 가중치 · 이 기기 가격 · 기기 계산'],
    ['growth', true, 'PERSONAL', 'PRESET', '개인 프리셋(성장 친화) · 이 기기 가격 · 기기 계산'], ['balanced', false, 'PERSONAL', 'GATE_OFF', '개인 프리셋(균형 · 관문 끔) · 이 기기 가격 · 기기 계산'],
    ['value', false, 'PERSONAL', 'PRESET GATE_OFF', '개인 프리셋(가치(관문 켬) · 관문 끔) · 이 기기 가격 · 기기 계산']];
  for (const [preset, gate, weights, setting, text] of cases) {
    const S = run(preset, gate), snap = JSON.stringify(S), x = QS.provenance({ profile: S.profile, priced: S.priced_codes > 0 });
    assert.equal(x.weights, weights, String(preset));assert.equal(x.setting.join(' ') || 'NONE', setting);assert.equal(x.prices, 'DEVICE');assert.equal(x.source, 'DEVICE_COMPUTED');assert.equal(x.profile_id, S.profile.id);
    assert.equal(QS.provenanceText(x, false), text);assert.deepEqual(QS.provenanceAttrs(x), { 'data-qgv-weights': weights, 'data-qgv-setting': setting, 'data-qgv-prices': 'DEVICE', 'data-qgv-source': 'DEVICE_COMPUTED', 'data-qgv-profile': S.profile.id });
    assert.equal(QS.rankLabel(S.profile, false), weights === 'OFFICIAL' ? 'Universe 공식 QGV 순위' : '개인 프리셋 순위 (Universe 기준)');
    // A display row carries the same profile, so a per-row label says the same.
    for (const r of Object.values(S.rows)) if (Number.isFinite(r.primary.total)) assert.equal(QS.provenance({ profile: r.primary.profile }).weights, weights, r.company_id);
    // Labels never change a value: the result is byte-identical after every label call, and equal to a fresh compute.
    assert.equal(JSON.stringify(S), snap);assert.equal(JSON.stringify(run(preset, gate)), snap);
  }
  // Q·G axes are read as published (central, sec-qgv2.json); the V axis alone is official inner weights whatever the preset/gate.
  const qg = QS.provenance({ kind: 'QG' });assert.deepEqual([qg.weights, qg.prices, qg.source], ['OFFICIAL', 'NONE', 'PUBLISHED']);assert.equal(QS.provenanceText(qg, false), '공식 가중치 · 가격 없음 · 중앙 게시(sec-qgv2.json)');
  const v = QS.provenance({ kind: 'V', profile: run('growth', false).profile, priced: true });assert.deepEqual([v.weights, v.prices, v.source], ['OFFICIAL', 'DEVICE', 'DEVICE_COMPUTED']);
  // Personal weights (S13 PERSONAL_PREVIEW) are personal for every kind but the published Q·G.
  const P = QS.compute({ identities, v2Inputs: inputs, quotes, weights: V2.officialWeights() }), pid = P.personal.profile, prow = Object.values(P.rows).find((r) => Number.isFinite(r.personal.total));
  assert.equal(QS.provenance({ profile: prow.personal.profile }).weights, 'PERSONAL');assert.equal(QS.provenance({ kind: 'V', profile: prow.personal.profile }).setting.join(), 'WEIGHTS');assert.ok(pid.id.includes('/custom/'));
  // No prices: NONE; English text.
  const bare = QS.compute({ identities, v2Inputs: inputs, quotes: {}, preset: 'growth' }), nx = QS.provenance({ profile: bare.profile, priced: bare.priced_codes > 0 });
  assert.equal(nx.prices, 'NONE');assert.equal(QS.provenanceText(nx, true), 'Personal preset (Growth friendly) · no prices · computed on this device');
  assert.equal(QS.provenanceAttrHtml(nx), ' data-qgv-weights="PERSONAL" data-qgv-setting="PRESET" data-qgv-prices="NONE" data-qgv-source="DEVICE_COMPUTED" data-qgv-profile="qgv-v2/growth/gate-on"');
  // N10/N15/N20 stay on the official default profile whatever the S06 preset: same selection, official provenance.
  const U = QS.universeIdentities(inputs, identities), off = (preset, gate) => QS.compute({ identities: U.identities, v2Inputs: inputs, quotes, preset, gate, official: U });
  const M1 = QS.officialModel({ identities: U.identities, v2Inputs: inputs, quotes, official: U, computed: off('growth', false) });
  assert.equal(QS.provenance({ profile: M1.official_profile }).weights, 'OFFICIAL');assert.deepEqual(M1.sets, QS.modelPortfolios(off('balanced', true), inputs).sets);
});

// ---------------------------------------------------------------- official (publication) mode, DC-31
// A publication-shaped row set built from the device engine on the same synthetic inputs and quotes (what the publisher does,
// without the strict file): compute({publication}) must give the same official Q·G·V and totals with no engine call and no price,
// and the personal recompute from the published factor scores must equal the device engine's personal result exactly.
// Q factor scores in another order than the fixture's (so a personal Q inner tree re-orders Q and the gate percentile is recomputed).
const SHUFFLED = (() => { const p = F.payload(); Object.values(p.records).forEach((r, i) => { if (r.factors) r.factors.q_profitability = (i * 37) % 100; }); return SQ.fromInputs(SQ.light(p)); })();
async function publicationOf(inputs = screens[SQ.FILE]) {
  const V2 = globalThis.QgvV2, TC = globalThis.TypeConfigDefaults;
  const ids = Object.keys(inputs.records).map((code) => ({ company_id: code.startsWith('TARGET:') ? code.slice(7) : code, ticker: QS.symbolOf(code) })).filter((c) => c.company_id !== 'tokyo_electron');
  const q = await QS.collectQuotes(universeWin, { identities: ids, v2Inputs: inputs }), dev = QS.compute({ identities: ids, v2Inputs: inputs, quotes: q }), rows = {};
  for (const c of ids) {
    const r = dev.rows[c.company_id], p = r.primary, rec = inputs.records[r.code];
    rows[r.code] = { cik: rec.cik, profile: rec.published_profile, industry_group: rec.industry_group, in_cross_section: rec.in_cross_section !== false, state: rec.state, source_reason_codes: [], acquired_at: null, fiscal_year_end: null,
      factors: Object.fromEntries(Object.entries(p.factors).map(([k, f]) => [k, { score: f.score, reason: f.reason, basis: f.basis }])),
      axes: Object.fromEntries(['Q', 'G', 'V'].map((a) => [a, { score: p.axes[a].score, state: p.axes[a].state, weight_available: p.axes[a].weight_available, factors_available: p.axes[a].factors_available, reason: p.axes[a].reason ?? null }])),
      weights: p.weights, type_weights: V2.typeAxisWeights(V2.pricefreeMemberships(rec.metrics), TC)[0], type_reason: p.type_reason, selected_types: p.selected_types, q_industry_percentile: p.q_industry_percentile,
      value_trap_gate: p.value_trap_gate, v_excluded: p.v_excluded, flags: p.flags, total: p.total, total_reason: p.total === null ? p.total_reason : null,
      price_status: Object.hasOwn(q, r.code) ? 'SUPPLIED' : 'NO_IEX_TRADE', rank: null, qg_reference_order: null, rank_row: null };
  }
  return { ids, quotes: q, dev, pub: { publication_id: 'qgvpub-' + '0'.repeat(64), calc_version: inputs.calc_version, inputs: [{ as_of: inputs.as_of }], rows } };
}

// D11 one place per CIK, the qgv_official.assign_ranks rule written out here on its own: the representative key of each CIK.
function repKeys(pub) {
  const keys = Object.keys(pub.rows).sort(), T = 'TARGET:', uc = new Set(keys.filter((k) => !k.startsWith(T) && pub.rows[k].cik).map((k) => pub.rows[k].cik)), rep = {};
  for (const k of keys) { const r = pub.rows[k]; if (k.startsWith(T) && uc.has(r.cik) && ['LIVE', 'STALE'].includes(r.state) && r.total_reason !== 'CALC_VERSION_MISMATCH') rep[r.cik] = k; }
  for (const k of keys) { const r = pub.rows[k]; if (!k.startsWith(T) && r.in_cross_section && r.cik && !Object.hasOwn(rep, r.cik)) rep[r.cik] = k; }
  return new Set(Object.values(rep));
}
test('official mode: compute({publication}) gives the published Q·G·V and totals with no engine call and no price; missing IEX price says its price_status', async () => {
  const { ids, dev, pub } = await publicationOf(), inputs = screens[SQ.FILE], V2 = globalThis.QgvV2;
  const real = V2.scoreUniverse; let engineCalls = 0;
  const off = (() => { try { globalThis.QgvV2 = Object.freeze({ ...V2, scoreUniverse: (...a) => { engineCalls++; return real(...a); } }); return QS.compute({ identities: ids, v2Inputs: inputs, publication: pub, quotes: { 'NASDAQ:NVDA': { price: 1, currency: 'USD' } } }); } finally { globalThis.QgvV2 = V2; } })();
  assert.equal(engineCalls, 0, 'no engine call'); assert.equal(off.source, 'PUBLICATION'); assert.equal(off.inputs_match, true); assert.equal(off.priced_codes, 0, 'quotes are not used');
  let unpriced = 0;
  for (const c of ids) {
    const a = dev.rows[c.company_id].primary, b = off.rows[c.company_id].primary;
    for (const k of ['q', 'g', 'v', 'total']) assert.equal(b[k], a[k], c.company_id + ' ' + k);
    assert.deepEqual(b.flags, a.flags, c.company_id + ' flags');
    if (pub.rows[off.rows[c.company_id].code].price_status === 'NO_IEX_TRADE' && b.v === null && b.coverage.axes.V.status === 'NOT_AVAILABLE') { unpriced++; assert.equal(b.coverage.axes.V.reason, 'NO_IEX_TRADE'); assert.ok(b.coverage.states.includes('CENTRAL_V_MISSING')); }
  }
  assert.ok(unpriced >= 1, 'the fixture has an unpriced row'); assert.doesNotMatch(JSON.stringify(off), /NO_DEVICE_PRICE|PRICE_HISTORY_NOT_AVAILABLE/);
  // Publication-only records when the loaded sec-qgv2.json is another file: the same scores, flagged.
  const other = QS.compute({ identities: ids, v2Inputs: { ...inputs, as_of: '2026-10-01T00:00:00Z' }, publication: pub });
  assert.equal(other.inputs_match, false); for (const c of ids) assert.equal(other.rows[c.company_id].primary.total, off.rows[c.company_id].primary.total);
  // Ranks: only the published ones, on the CIK's rank_row (one official place per issuer); the other code of the CIK points to it.
  const U = QS.universeIdentities(inputs, identities), own = QS.compute({ identities: U.identities, v2Inputs: inputs, publication: pub, official: U });
  const keys = Object.values(own.rows).filter((r) => r.code && r.code === r.universe_code && r.primary.total !== null && r.primary.v !== null).map((r) => r.code).sort(), ranked = structuredClone(pub);
  ranked.rows[keys[0]].rank = 1; ranked.rows[keys[0]].rank_row = keys[0]; ranked.rows[keys[1]].rank_row = keys[0];
  const rr = QS.compute({ identities: U.identities, v2Inputs: inputs, publication: ranked, official: U });
  const row0 = QS.rowOf(rr, keys[0]), row1 = QS.rowOf(rr, keys[1]);
  assert.equal(row0.rank, 1); assert.equal(row1.rank, null); assert.equal(row1.rank_row, keys[0]); assert.equal(Object.values(rr.rows).filter((r) => Number.isInteger(r.rank)).length, 1);
});

test('official mode: the personal recompute from published factor scores equals the device engine exactly (inner / axis trees, type weights on and off, gate on and off); weight stages NA', async () => {
  const inputs = SHUFFLED, { ids, quotes: q, pub } = await publicationOf(inputs), V2 = globalThis.QgvV2, inner = V2.officialWeights().inner;
  const trees = [V2.officialWeights('growth'), { axis: { Q: 50, G: 30, V: 20 }, inner: { ...inner, Q: { q_profitability: 50, q_moat_proxy: 10, q_earnings_quality: 10, q_financial_safety: 20, q_capital_allocation: 10 } } },
    { axis: { Q: 20, G: 20, V: 60 }, inner: { ...inner, V: { v_earnings_yield: 50, v_fcf_yield: 10, v_vs_industry: 10, v_vs_own_history: 0, v_expectation_check: 30 } } }, { axis: { Q: 50, G: 50, V: 0 }, inner }];
  let recomputedPct = 0, traps = 0, deduped = 0;const reps = repKeys(pub);
  for (const tree of trees) for (const typeWeights of [true, false]) for (const gate of [true, false]) {
    const d = QS.compute({ identities: ids, v2Inputs: inputs, quotes: q, weights: tree, typeWeights, gate }), o = QS.compute({ identities: ids, v2Inputs: inputs, publication: pub, weights: tree, typeWeights, gate });
    // The device engine places every identity; the publication places one row per CIK: the device order restricted to the representatives.
    const place = (k) => { const m = new Map(); Object.values(d.rows).filter((r) => reps.has(r.code) && (k === 'rank' ? r.personal_rank !== null : r.personal_qg_reference)).sort((x, y) => (k === 'rank' ? x.personal_rank - y.personal_rank : x.personal_qg_reference.order - y.personal_qg_reference.order)).forEach((r, i) => m.set(r.company_id, i + 1)); return m; };
    const wantRank = place('rank'), wantQg = place('qg');
    assert.equal(o.personal.state, d.personal.state); assert.equal(o.personal.profile.id, d.personal.profile.id); assert.deepEqual(o.personal.weight_stages, { state: 'NOT_AVAILABLE', reason: 'WEIGHT_STAGES_NOT_REBUILT' });
    for (const c of ids) {
      const a = d.rows[c.company_id], b = o.rows[c.company_id];
      for (const k of ['q', 'g', 'v', 'total', 'q_industry_percentile', 'value_trap_gate']) assert.equal(b.personal[k], a.personal[k], JSON.stringify(tree.axis) + typeWeights + gate + ' ' + c.company_id + ' ' + k);
      assert.deepEqual(b.personal.flags, a.personal.flags); assert.equal(b.personal_rank, wantRank.get(c.company_id) ?? null, c.company_id + ' personal rank: one place per CIK');
      assert.equal(b.personal_qg_reference ? b.personal_qg_reference.order : null, wantQg.get(c.company_id) ?? null, c.company_id + ' personal QG order: one place per CIK');
      if (!reps.has(b.code) && (a.personal_rank !== null || a.personal_qg_reference)) deduped++;
      if (b.personal.q_industry_percentile !== b.primary.q_industry_percentile) recomputedPct++; if (a.personal.value_trap_gate) traps++;
      assert.equal(b.primary.total, o.rows[c.company_id].primary.total);
    }
  }
  assert.ok(recomputedPct > 0, 'personal Q inner weights recompute the gate percentile'); assert.ok(traps > 0, 'the gate fires in the fixture');
  assert.ok(deduped > 0, 'the fixture has a second row of an issuer that the device would place');
});

// The synthetic qgv-official vectors (dual-class GOOG/GOOGL, TARGET:amd ranked for NASDAQ:AMD), page identities as the app makes them.
async function vectorPage({ targets = true } = {}) {
  const QO = require(path.join(W, 'qgv-official.js')), OV = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')), pub = JSON.parse(OV.base_text);
  await QO.validate(pub); assert.equal(QO.state(pub), 'OFFICIAL');
  const ids = targets ? Object.keys(QO.TARGET_TICKERS).map((id) => ({ company_id: id, ticker: QO.TARGET_TICKERS[id] })) : [];
  const r = QS.officialPage({}, { publication: pub, v2Inputs: null, identities: ids });
  return { pub, r, ids };
}
test('official mode: with the official weights the personal preview gives every row the published place (one per CIK: dual class, TARGET of a Universe issuer)', async () => {
  const { pub, r } = await vectorPage(), V2 = globalThis.QgvV2, c = r.computed;
  assert.equal(r.source, 'PUBLICATION'); assert.equal(r.inputs_match, false);
  const o = QS.compute({ identities: r.identities, v2Inputs: null, publication: pub, official: r.official, weights: V2.officialWeights(), typeWeights: true, gate: true });
  let placed = 0, others = 0;
  for (const [cid, row] of Object.entries(o.rows)) {
    const off = c.rows[cid];
    assert.equal(row.rank, off.rank, cid); assert.equal(row.personal_rank, off.rank, cid + ' personal rank = published rank');
    assert.equal(row.personal_qg_reference ? row.personal_qg_reference.order : null, off.qg_reference ? off.qg_reference.order : null, cid + ' personal QG order = published order');
    assert.equal(row.personal_rank_row ?? null, off.rank_row ?? null, cid + ' the other codes of the issuer point to its place');
    if (Number.isInteger(row.rank) || row.qg_reference) placed++; if (off.rank_row) others++;
  }
  const pubPlaced = Object.values(pub.rows).filter((x) => x.rank !== null || x.qg_reference_order !== null).length;
  assert.equal(placed, pubPlaced, 'every published place is shown once'); assert.ok(others >= 1, 'GOOG points to its issuer place (NASDAQ:AMD is the TARGET amd row on the page)');
  assert.equal(QS.rowOf(o, 'NASDAQ:GOOG').personal_rank_row, 'NASDAQ:GOOGL');
});
test('official mode: a published place on a TARGET key not on the page (catalog unreadable) is shown on the row of that issuer\'s Universe code', async () => {
  const { pub, r } = await vectorPage({ targets: false }), c = r.computed;
  assert.ok(!Object.values(c.rows).some((x) => x.code === 'TARGET:amd'), 'no TARGET row on the page');
  const amd = QS.rowOf(c, 'NASDAQ:AMD');
  assert.equal(amd.rank, pub.rows['TARGET:amd'].rank, 'the issuer place on its Universe code row'); assert.equal(amd.rank_row, undefined);
  const ranks = Object.values(c.rows).map((x) => x.rank).filter(Number.isInteger).sort((a, b) => a - b);
  assert.deepEqual(ranks, Array.from({ length: pub.coverage.ranked }, (_, i) => i + 1), 'no gap: every published rank shown once');
});

// Owner decision 2026-10-31 (docs/qgv_official/LAST_TRADE_TIME_20261031.md): the synthetic vector case last_trade_every_v_row_valid
// gives the V rows, in key order, 15:59:59 (no note), 15:30:00 (exactly 30 minutes: note), 09:30:00 (note), then 15:45:00 (no note).
test('last-trade time: rows carry the publication\'s v_last_trade; summaryText / lastTradeText / lastTradeHtml and the company V cell name it only >= 30 min before close; values unchanged; absent = nothing', async () => {
  const QO = require(path.join(W, 'qgv-official.js')), OV = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/qgv_official_vectors_v1.json'), 'utf8'));
  const c = OV.cases.find((x) => x.id === 'last_trade_every_v_row_valid'), pub = JSON.parse(OV.base_text);
  for (const op of c.ops) { let t = pub; for (const k of op.path.slice(0, -1)) t = t[k]; t[op.path[op.path.length - 1]] = structuredClone(op.value); }
  await QO.validate(pub);
  const ids = Object.keys(QO.TARGET_TICKERS).map((id) => ({ company_id: id, ticker: QO.TARGET_TICKERS[id] }));
  const r = QS.officialPage({}, { publication: pub, v2Inputs: null, identities: ids }), plain = (await vectorPage()).r;
  const vKeys = Object.keys(pub.rows).sort().filter((k) => pub.rows[k].axes.V.score !== null && pub.rows[k].price_status === 'SUPPLIED');
  let noted = 0, quiet = 0;
  for (const [cid, row] of Object.entries(r.computed.rows)) {
    const p = row.primary, before = plain.computed.rows[cid].primary, info = row.code && Object.hasOwn(pub.rows, row.code) ? QO.lastTrade(pub, row.code) : null;
    assert.deepEqual([p.v, p.total, row.rank, row.qg_reference && row.qg_reference.order], [before.v, before.total, plain.computed.rows[cid].rank, plain.computed.rows[cid].qg_reference && plain.computed.rows[cid].qg_reference.order], cid + ' values unchanged');
    assert.equal(before.v_last_trade, undefined, cid + ' the publication without times gives nothing');
    assert.equal(QS.lastTradeText(before), null); assert.equal(QS.lastTradeHtml(before), ''); assert.doesNotMatch(QS.summaryText(before), /마지막 체결/);
    assert.deepEqual(p.v_last_trade || null, info, cid + ' = QgvOfficial.lastTrade of its own publication row');
    const text = QS.lastTradeText(p);
    if (info && info.note) {
      noted++; assert.equal(text, '마지막 체결 ' + info.ny_time + ' (뉴욕)'); assert.equal(QS.lastTradeText(p, true), 'last trade ' + info.ny_time + ' (New York)');
      assert.ok(QS.summaryText(p).includes(' · V ' + (Math.round(p.v * 10) / 10).toFixed(1) + ' · ' + text + ' · 산출 요인 '), cid);
      assert.equal(QS.lastTradeHtml(p), '<span class="small" data-v-last-trade="' + info.ny_time + '">' + text + '</span>');
      const html = CS.qgvBody({}, cid, 'ko-KR', { row });
      assert.match(html, new RegExp('<dd data-qgv="V"><span class="num">[^<]+</span> <span class="small" data-v-last-trade="' + info.ny_time + '">' + text.replace(/[()]/g, '\\$&') + '</span></dd>'), cid + ' company V cell');
    } else {
      if (info) quiet++;
      assert.equal(text, null, cid); assert.doesNotMatch(QS.summaryText(p), /마지막 체결/, cid); assert.doesNotMatch(CS.qgvBody({}, cid, 'ko-KR', { row }), /data-v-last-trade/, cid);
    }
    if (p.v === null) assert.equal(p.v_last_trade, undefined, cid + ' no V, no time');
  }
  assert.ok(noted >= 2 && quiet >= 2, noted + ' noted / ' + quiet + ' quiet rows');
  assert.ok(vKeys.length >= 4);
  // the personal recompute keeps the note on the row it belongs to (same price, same time); a V the recompute cannot give has none
  const o = QS.compute({ identities: r.identities, v2Inputs: null, publication: pub, official: r.official, weights: globalThis.QgvV2.officialWeights('balanced'), typeWeights: true, gate: true });
  for (const [cid, row] of Object.entries(o.rows)) assert.deepEqual(row.personal.v_last_trade || null, Number.isFinite(row.personal.v) ? r.computed.rows[cid].primary.v_last_trade || null : row.personal.v_last_trade || null, cid);
  // a publication QgvOfficial did not validate never gives a time (compute is handed the raw object)
  const raw = JSON.parse(JSON.stringify(pub)), unvalidated = QS.compute({ identities: r.identities, v2Inputs: null, publication: raw, official: r.official });
  assert.ok(Object.values(unvalidated.rows).every((x) => x.primary.v_last_trade === undefined));
  // a recomputed V that is NA has no note even if the row had a time
  assert.equal(QS.lastTradeText({ v: null, v_last_trade: { ny_time: '10:00', note: true } }), null);
  assert.equal(QS.lastTradeText({ v: 50, v_last_trade: { ny_time: '10:00', note: true } }), '마지막 체결 10:00 (뉴욕)');
  assert.equal(QS.lastTradeText({ v: 50, v_last_trade: { ny_time: '15:45', note: false } }), null);
});

// D11 one place per issuer on ONE representative security (owner rule restated 2026-10-31 '시총은 발행사 단위, 점수는 대표 증권
// 하나'): the representative is the publication's (qgv_official.assign_ranks), the seat is that key's row or, for a TARGET key,
// the Universe code row that TARGET identity maps to (D12); the other codes carry rank_row; the S06 chips count only own places,
// so the ranked / QG counts equal the publication's; ties as Python order() (total, then the key's symbol, then the key).
const O = require('./qgv_official_fixture.js');
async function validatedCase(caseId) { const QO = require(path.join(W, 'qgv-official.js')), p = O.variant(caseId);await QO.validate(p);assert.equal(QO.state(p), 'OFFICIAL', caseId);return p; }
// The page result over a publication alone (publication-only records), with the given page identities (D12 dedupe).
function pubPage(pub, ids = [], extra = {}) { const U = QS.universeIdentities({ records: pub.rows }, ids);return QS.compute({ identities: U.identities, v2Inputs: null, publication: pub, official: U, ...extra }); }
const placedCount = (c, k) => Object.values(c.rows).filter((x) => x.universe_code && (k === 'rank' ? Number.isInteger(x.rank) : x.qg_reference)).length;
test('one place per issuer: GOOG and GOOGL both have Q·G totals, only the representative GOOGL holds the CIK place; S06 counts == the publication counts', async () => {
  const { pub, r } = await vectorPage(), c = r.computed, uni = Object.values(c.rows).filter((x) => x.universe_code);
  const goog = QS.rowOf(c, 'NASDAQ:GOOG'), googl = QS.rowOf(c, 'NASDAQ:GOOGL');
  assert.equal(pub.rows['NASDAQ:GOOG'].cik, pub.rows['NASDAQ:GOOGL'].cik, 'one issuer (CIK), two share classes');assert.equal(pub.rows['NASDAQ:GOOG'].rank_row, 'NASDAQ:GOOGL');
  assert.ok(Number.isFinite(goog.primary.total) && Number.isFinite(googl.primary.total) && goog.primary.total > googl.primary.total, 'both classes have a total (GOOG even the higher one)');
  assert.deepEqual([googl.qg_reference && googl.qg_reference.order, googl.rank, googl.rank_row ?? null], [pub.rows['NASDAQ:GOOGL'].qg_reference_order, null, null], 'GOOGL holds the published QG place');
  assert.deepEqual([goog.qg_reference, goog.rank, goog.rank_row], [null, null, 'NASDAQ:GOOGL'], 'GOOG points to GOOGL\'s place and has none of its own');
  const pubRanked = Object.values(pub.rows).filter((x) => Number.isInteger(x.rank)).length, pubQg = Object.values(pub.rows).filter((x) => Number.isInteger(x.qg_reference_order)).length;
  assert.deepEqual([placedCount(c, 'rank'), placedCount(c, 'qg'), c.official.ranked, c.official.qg_reference], [pubRanked, pubQg, pubRanked, pubQg], 'ranked / QG list == the publication');
  assert.deepEqual([pub.coverage.ranked, pub.coverage.qg_reference], [pubRanked, pubQg]);
  // S06 explore chips (LeaderboardScreen.exploreOf): ranked / QG = rows with a place of their own; GOOG is in no list (only 'all').
  const chip = (x) => L.exploreOf({ score: x }), count = (g) => uni.filter((x) => chip(x) === g).length;
  assert.equal(QS.exploreGroup(goog), 'QG_REFERENCE', 'GOOG\'s score shape is Q·G only');assert.equal(chip(goog), null, 'GOOG: no QG chip without an order');assert.equal(chip(googl), 'qg');
  assert.deepEqual([count('ranked'), count('qg')], [pubRanked, pubQg], 'S06 chips == the publication counts');
  assert.ok(uni.filter((x) => chip(x) === null).every((x) => x.rank_row), 'a row in no list is another share class of a placed issuer');
  // The personal result uses the same seats: GOOG points to GOOGL there too.
  const o = pubPage(pub, [], { weights: globalThis.QgvV2.officialWeights(), typeWeights: true, gate: true });
  assert.deepEqual([QS.rowOf(o, 'NASDAQ:GOOGL').personal_qg_reference.order, QS.rowOf(o, 'NASDAQ:GOOG').personal_qg_reference, QS.rowOf(o, 'NASDAQ:GOOG').personal_rank_row], [pub.rows['NASDAQ:GOOGL'].qg_reference_order, null, 'NASDAQ:GOOGL']);
});
test('one place per issuer: a TARGET representative not on the page holds its place on the code that TARGET maps to by the D12 dedupe (TARGET googl IS NASDAQ:GOOGL), not on the issuer\'s first cross-section code', async () => {
  const pub = structuredClone(await validatedCase('target_for_two_share_classes_valid')), t = pub.rows['TARGET:googl'], cik = t.cik;
  assert.equal(pub.rows['NASDAQ:GOOG'].rank_row, 'TARGET:googl');assert.ok(Number.isInteger(t.rank), 'the TARGET row is the published representative (ranked)');
  // Real-data shape: GOOG is the issuer's first cross-section code, GOOGL is not; GOOGL reads the same general scores as its TARGET row.
  pub.rows['NASDAQ:GOOGL'] = { ...structuredClone(t), cik, in_cross_section: false, rank: null, qg_reference_order: null, rank_row: 'TARGET:googl' };pub.rows['NASDAQ:GOOG'].in_cross_section = true;
  const c = pubPage(pub), goog = QS.rowOf(c, 'NASDAQ:GOOG'), googl = QS.rowOf(c, 'NASDAQ:GOOGL');
  assert.ok(!Object.values(c.rows).some((x) => x.code && x.code.startsWith('TARGET:')), 'no TARGET identity on the page');
  assert.deepEqual([googl.rank, googl.rank_row], [t.rank, undefined], 'the TARGET place on GOOGL (D12), never on GOOG');
  assert.deepEqual([goog.rank, goog.qg_reference, goog.rank_row], [null, null, 'NASDAQ:GOOGL'], 'GOOG points to GOOGL\'s place');
  assert.equal(placedCount(c, 'rank'), Object.values(pub.rows).filter((x) => Number.isInteger(x.rank)).length, 'every published rank shown once');
  // With the TARGET identity on the page the seat is its own row (code TARGET:googl, GOOGL merged into it); GOOG points to it.
  const d = pubPage(pub, [{ company_id: 'googl', ticker: 'GOOGL' }]);
  assert.deepEqual([d.rows.googl.code, d.rows.googl.universe_code, d.rows.googl.rank], ['TARGET:googl', 'NASDAQ:GOOGL', t.rank]);assert.deepEqual([d.rows['NASDAQ:GOOG'].rank, d.rows['NASDAQ:GOOG'].rank_row], [null, 'TARGET:googl']);
  // Personal (same seats): the place on GOOGL / the TARGET row, GOOG pointing to it.
  const p = pubPage(pub, [], { weights: globalThis.QgvV2.officialWeights(), typeWeights: true, gate: true });
  assert.ok(Number.isInteger(QS.rowOf(p, 'NASDAQ:GOOGL').personal_rank));assert.deepEqual([QS.rowOf(p, 'NASDAQ:GOOG').personal_rank, QS.rowOf(p, 'NASDAQ:GOOG').personal_rank_row], [null, 'NASDAQ:GOOGL']);
});
test('one place per issuer without a publication (official page, Q·G list): no TARGET row -> the first cross-section Universe code in key order; a live TARGET row -> that row', () => {
  const p = F.payload(), cik = p.target.googl.cik;
  p.target.googl = { cik, state: 'NOT_AVAILABLE', reason_codes: ['SEC_SOURCE_NOT_AVAILABLE'], fiscal_year_end: null, factors: {}, axes: {}, v_inputs_v2: {} };
  const inputs = SQ.fromInputs(SQ.light(p)), U = QS.universeIdentities(inputs, identities), c = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes: {}, official: U, vMissing: 'OFFICIAL_NOT_PUBLISHED' });
  assert.deepEqual(['NASDAQ:GOOG', 'NASDAQ:GOOGL'].map((k) => [inputs.records[k].cik, inputs.records[k].in_cross_section]), [[cik, true], [cik, false]], 'one issuer, GOOG its cross-section code');
  const goog = c.rows['NASDAQ:GOOG'], googl = c.rows.googl;
  assert.equal(googl.code, 'NASDAQ:GOOGL', 'the googl identity reads NASDAQ:GOOGL (its TARGET row has no data)');assert.ok(Number.isFinite(goog.primary.total) && Number.isFinite(googl.primary.total), 'both have Q·G totals');
  assert.ok(goog.qg_reference && Number.isInteger(goog.qg_reference.order), 'GOOG (first cross-section code) holds the issuer place');assert.deepEqual([googl.qg_reference, googl.rank_row], [null, 'NASDAQ:GOOG']);
  const ciks = Object.values(c.rows).filter((x) => x.qg_reference).map((x) => inputs.records[x.code].cik);assert.equal(new Set(ciks).size, ciks.length, 'one QG place per CIK');
  // Orders stay 1..N with no gap; the device path (quotes, no vMissing) and callers without the official split are unchanged.
  assert.deepEqual(Object.values(c.rows).map((x) => x.qg_reference && x.qg_reference.order).filter(Number.isInteger).sort((a, b) => a - b), Array.from({ length: ciks.length }, (_, i) => i + 1));
  const plain = QS.compute({ identities: U.identities, v2Inputs: inputs, quotes: {}, vMissing: 'OFFICIAL_NOT_PUBLISHED' });assert.ok(plain.rows.googl.qg_reference && plain.rows['NASDAQ:GOOG'].qg_reference, 'without the official split both keep an order (unchanged)');
});
test('ties: equal totals are ordered by the key\'s symbol (\'.\' -> \'-\'), then the key (assign_ranks order()), never by the shown ticker; personal places equal the published ones', async () => {
  const pub = await validatedCase('tie_dot_symbols_valid'), V2 = globalThis.QgvV2, top = Object.keys(pub.rows).filter((k) => Number.isInteger(pub.rows[k].rank)).sort((a, b) => pub.rows[a].rank - pub.rows[b].rank);
  assert.deepEqual(top.slice(0, 2), ['NYSE:AB.C', 'NYSE:AB-D'], 'Python order: AB-C before AB-D');assert.equal(pub.rows['NYSE:AB.C'].total, pub.rows['NYSE:AB-D'].total, 'a tie');
  // Shown tickers as a catalog could give them ('AB.C' sorts after 'AB-D' as text): the places follow the key's symbol. The TARGET
  // identities are on the page as the app makes them (TARGET amd holds its own place).
  const QO = require(path.join(W, 'qgv-official.js')), ids = [...Object.keys(QO.TARGET_TICKERS).map((id) => ({ company_id: id, ticker: QO.TARGET_TICKERS[id] })), { company_id: 'NYSE:AB.C', ticker: 'AB.C' }, { company_id: 'NYSE:Q.R.S', ticker: 'Q.R.S' }], off = pubPage(pub, ids), o = pubPage(pub, ids, { weights: V2.officialWeights(), typeWeights: true, gate: true });
  for (const [cid, row] of Object.entries(o.rows)) { assert.equal(row.personal_rank, off.rows[cid].rank, cid + ' personal rank = published rank (ties included)');assert.equal(row.personal_qg_reference ? row.personal_qg_reference.order : null, off.rows[cid].qg_reference ? off.rows[cid].qg_reference.order : null, cid); }
  assert.equal(o.rows['NYSE:AB.C'].personal_rank + 1, o.rows['NYSE:AB-D'].personal_rank);assert.equal(o.rows['NYSE:Q.R.S'].personal_rank + 1, o.rows['NYSE:Q.R-T'].personal_rank);
  // Same symbol, another key: the key decides (NASDAQ:AB-C before NYSE:AB.C).
  const more = structuredClone(pub);more.rows['NASDAQ:AB-C'] = { ...structuredClone(pub.rows['NYSE:AB.C']), cik: '0000003099', rank: null, qg_reference_order: null, rank_row: null };
  const m = pubPage(more, ids, { weights: V2.officialWeights(), typeWeights: true, gate: true }), at = (k) => QS.rowOf(m, k).personal_rank;
  assert.deepEqual([at('NASDAQ:AB-C'), at('NYSE:AB.C'), at('NYSE:AB-D')], [at('NASDAQ:AB-C'), at('NASDAQ:AB-C') + 1, at('NASDAQ:AB-C') + 2], 'symbol AB-C (key NASDAQ < NYSE), then AB-D');
});
const TARGET_IDS = () => { const QO = require(path.join(W, 'qgv-official.js')); return Object.keys(QO.TARGET_TICKERS).map((id) => ({ company_id: id, ticker: QO.TARGET_TICKERS[id] })); };
test('every valid publication vector: S06 ranked / QG counts and chips == the publication, with the TARGET identities on the page (as app.js registers them) and without (catalog unreadable)', async () => {
  const OV = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')), V2 = globalThis.QgvV2, chip = (x) => L.exploreOf({ score: x });
  const ids = OV.cases.filter((c) => c.id.endsWith('_valid')).map((c) => c.id);assert.ok(ids.includes('target_calc_mismatch_valid') && ids.includes('target_for_two_share_classes_valid') && ids.length >= 20, 'the valid vectors');
  for (const id of ids) {
    const pub = await validatedCase(id), want = [Object.values(pub.rows).filter((x) => Number.isInteger(x.rank)).length, Object.values(pub.rows).filter((x) => Number.isInteger(x.qg_reference_order)).length];
    for (const targets of [true, false]) {
      const r = QS.officialPage({}, { publication: pub, v2Inputs: null, identities: targets ? TARGET_IDS() : [] }), c = r.computed, uni = Object.values(c.rows).filter((x) => x.universe_code), at = id + (targets ? ' (TARGET identities)' : ' (no TARGET identity)');
      assert.deepEqual([placedCount(c, 'rank'), placedCount(c, 'qg')], want, at + ': ranked / QG list == the publication');
      assert.deepEqual([uni.filter((x) => chip(x) === 'ranked').length, uni.filter((x) => chip(x) === 'qg').length], want, at + ': S06 chips == the publication');
      assert.deepEqual(uni.map((x) => x.rank).filter(Number.isInteger).sort((a, b) => a - b), Array.from({ length: want[0] }, (_, i) => i + 1), at + ': every published rank once');
      // With the TARGET identities on the page every place is on a row that reads its key: the personal result with the official
      // weights gives every row the published place. (Without them a holder may read another record of the issuer; see below.)
      if (targets) { const o = QS.compute({ identities: r.identities, v2Inputs: null, publication: pub, official: r.official, weights: V2.officialWeights(), typeWeights: true, gate: true });
        for (const [cid, x] of Object.entries(o.rows)) { assert.equal(x.personal_rank, c.rows[cid].rank, at + ' ' + cid + ' personal rank');assert.equal(x.personal_qg_reference ? x.personal_qg_reference.order : null, c.rows[cid].qg_reference ? c.rows[cid].qg_reference.order : null, at + ' ' + cid + ' personal QG order'); } }
    }
  }
});
test('CALC_VERSION_MISMATCH TARGET (publication path only): the TARGET identity reads its Universe code, the published representative NASDAQ:AMD, and shows its rank; the device codeIndex is unchanged', async () => {
  const pub = await validatedCase('target_calc_mismatch_valid'), a = pub.rows['NASDAQ:AMD'];
  assert.deepEqual([pub.rows['TARGET:amd'].state, pub.rows['TARGET:amd'].total_reason, a.rank_row], ['LIVE', 'CALC_VERSION_MISMATCH', 'NASDAQ:AMD']);assert.ok(Number.isInteger(a.rank), 'NASDAQ:AMD is the ranked representative');
  const r = QS.officialPage({}, { publication: pub, v2Inputs: null, identities: TARGET_IDS() }), amd = r.computed.rows.amd;
  assert.deepEqual([amd.code, amd.universe_code, amd.rank, amd.primary.total, amd.primary.v], ['NASDAQ:AMD', 'NASDAQ:AMD', a.rank, a.total, a.axes.V.score], 'the amd row shows the published NASDAQ:AMD row and its rank');
  assert.equal(QS.rowOf(r.computed, 'NASDAQ:AMD'), amd, 'one row for the security (D12)');assert.equal(r.computed.official.ranked, pub.coverage.ranked);
  // Without a publication (device path / any other codeIndex caller) a TARGET row with data still stands for its identity.
  const view = { records: Object.fromEntries(Object.entries(pub.rows).map(([k, x]) => [k, { cik: x.cik, state: x.state, calc_version_mismatch: x.total_reason === 'CALC_VERSION_MISMATCH' }])) };
  assert.equal(QS.compute({ identities: [{ company_id: 'amd', ticker: 'AMD' }], v2Inputs: view, quotes: {} }).rows.amd.code, 'TARGET:amd', 'device path unchanged');
});
test('TARGET representative not on the page, D12 seat of the other kind (target_for_two_share_classes_valid as published): the place goes to the same-CIK row of the same kind (GOOG), never dropped', async () => {
  const pub = await validatedCase('target_for_two_share_classes_valid'), t = pub.rows['TARGET:googl'];
  const c = pubPage(pub), goog = QS.rowOf(c, 'NASDAQ:GOOG'), googl = QS.rowOf(c, 'NASDAQ:GOOGL');
  assert.ok(Number.isInteger(t.rank) && googl.primary.v === null && Number.isFinite(goog.primary.v), 'the D12 seat GOOGL has no V, GOOG has one');
  assert.deepEqual([goog.rank, goog.rank_row], [t.rank, undefined], 'GOOG (same CIK, ranked kind) holds the TARGET place');
  assert.deepEqual([googl.rank, googl.qg_reference, googl.rank_row, L.exploreOf({ score: googl })], [null, null, 'NASDAQ:GOOG', null], 'GOOGL points to GOOG and is in no list');
  assert.deepEqual([placedCount(c, 'rank'), placedCount(c, 'qg')], [pub.coverage.ranked, pub.coverage.qg_reference], 'counts == the publication');
  const p = pubPage(pub, [], { weights: globalThis.QgvV2.officialWeights(), typeWeights: true, gate: true });
  assert.ok(Number.isInteger(QS.rowOf(p, 'NASDAQ:GOOG').personal_rank));assert.deepEqual([QS.rowOf(p, 'NASDAQ:GOOGL').personal_rank, QS.rowOf(p, 'NASDAQ:GOOGL').personal_rank_row], [null, 'NASDAQ:GOOG'], 'personal: the same holder');
});
test('S06 QGV sort: equal totals follow the place numbers (rank, then QG order; reversed for low first), so the table order equals the rank numbers', async () => {
  const pub = await validatedCase('tie_dot_symbols_valid'), ids = [...TARGET_IDS(), { company_id: 'NYSE:AB.C', ticker: 'AB.C' }, { company_id: 'NYSE:Q.R.S', ticker: 'Q.R.S' }];
  const r = QS.officialPage({}, { publication: pub, v2Inputs: null, identities: ids }), c = r.computed, rows = r.identities.filter((x) => r.official.universe[x.company_id]).map((x) => ({ company_id: x.company_id, ticker: x.ticker }));
  const placeOf = (x) => { const s = c.rows[x.company_id];return Number.isInteger(s.rank) ? [0, s.rank] : s.qg_reference ? [1, s.qg_reference.order] : null; };
  const head = (id) => L.sortRows(rows, c, id).map(placeOf).filter(Boolean), n = Object.values(c.rows).filter((x) => Number.isInteger(x.rank) || x.qg_reference).length;
  const desc = head('qgv'), asc = head('qgv-asc'), byTier = (a, t) => a.filter((x) => x[0] === t).map((x) => x[1]);
  assert.equal(desc.length, n);assert.deepEqual(byTier(desc, 0), byTier(desc, 0).slice().sort((x, y) => x - y), 'QGV high first: ranks 1..N in order, ties included (AB.C #1 above AB-D #2)');
  assert.deepEqual(byTier(desc, 1), byTier(desc, 1).slice().sort((x, y) => x - y), 'then the QG list in its order');
  assert.deepEqual(byTier(asc, 0), byTier(desc, 0).slice().reverse(), 'QGV low first: the exact reverse of the rank order');assert.deepEqual(byTier(asc, 1), byTier(desc, 1).slice().reverse());
  const t = L.sortRows(rows, c, 'qgv').map((x) => x.company_id);assert.ok(t.indexOf('NYSE:AB.C') < t.indexOf('NYSE:AB-D') && t.indexOf('NYSE:Q.R.S') < t.indexOf('NYSE:Q.R-T'), 'the tied pairs in rank order');
});

test('officialPage: only a QgvOfficial-validated publication; without one the price-free Q·G rows, every V NA with the OFFICIAL_* reason, Q·G totals in the QG reference list', async () => {
  const inputs = screens[SQ.FILE], { pub } = await publicationOf();
  for (const [publication, reason, want] of [[null, undefined, 'OFFICIAL_NOT_PUBLISHED'], [null, 'OFFICIAL_UNAVAILABLE', 'OFFICIAL_UNAVAILABLE'], [pub, undefined, 'OFFICIAL_INVALID']]) {
    const r = QS.officialPage({}, { publication, v2Inputs: inputs, identities, reason });
    assert.equal(r.source, 'NONE'); assert.equal(r.v_reason, want); assert.equal(r.price_basis, null); assert.deepEqual(r.quotes, {});
    const rows = Object.values(r.computed.rows);
    assert.ok(rows.every((x) => x.primary.v === null && x.rank === null), want + ': no V and no official rank');
    const general = rows.filter((x) => x.universe_code && x.primary.total !== null && inputs.records[x.code] && inputs.records[x.code].published_profile === 'GENERAL');
    // One place per issuer (D11, owner rule 2026-10-31): every Q·G total is in the QG reference list once per CIK — on the
    // representative's row (TARGET googl), the other share class (NASDAQ:GOOG) points to it and has no order of its own.
    const placed = (x) => x.qg_reference && Number.isInteger(x.qg_reference.order), seatOf = (x) => rows.find((y) => y.code === x.rank_row);
    assert.ok(general.length > 0 && general.every((x) => placed(x) || (x.rank_row && placed(seatOf(x)) && x.qg_reference === null && x.rank === null)), want + ': Q·G totals in the QG reference list (one place per CIK)');
    assert.deepEqual(rows.filter((x) => x.rank_row).map((x) => [x.company_id, x.rank_row]), [['NASDAQ:GOOG', 'TARGET:googl']], want + ': the second share class points to the representative TARGET row');
    const ciks = rows.filter(placed).map((x) => inputs.records[x.code].cik).filter(Boolean);assert.equal(new Set(ciks).size, ciks.length, want + ': one QG place per CIK');
    assert.ok(general.some((x) => x.qg_reference && x.qg_reference.reason === want), want + ' is the V reason'); assert.doesNotMatch(JSON.stringify(r.computed), /NO_DEVICE_PRICE|PRICE_HISTORY_NOT_AVAILABLE/);
  }
  assert.equal(QS.officialPage({}, { publication: null, v2Inputs: null }), null);
  assert.equal(QS.officialPage({}, { publication: null, v2Inputs: inputs, identities }), QS.officialPage({}, { publication: null, v2Inputs: inputs, identities }), 'memoized');
});

// DC-31 old-app central basis line (centralBasis / centralText / centralHtml), the page publication getter and the S06 preset view.
async function withNow(iso, fn) { const real = Date.now; Date.now = () => (iso === null ? NaN : Date.parse(iso)); try { return await fn(); } finally { Date.now = real; } }
test('centralBasis: fresh / STALE past 2 completed New York sessions / not countable, 계산 버전 다름, IEX attribution and terms link; never a price', async () => {
  const { pub } = await vectorPage(), inputs = { calc_version: pub.calc_version };
  const fresh = await withNow('2026-10-14T21:00:00Z', () => QS.centralBasis(pub, { v2Inputs: inputs }));
  assert.equal(fresh.sessions, 1); assert.equal(fresh.stale, false); assert.equal(fresh.calc_differs, false); assert.equal(fresh.publication_id, pub.publication_id);
  const ft = QS.centralText(fresh, false);
  assert.match(ft, /^공식 V · 중앙 게시 · IEX 마지막 체결가 기준\(공식 종가 아님\) · 가격 기준일 2026-10-13 · 게시 2026-10-13 22:40 UTC$/);
  const fh = QS.centralHtml(fresh, false);
  assert.match(fh, /data-central-state="OK"/); assert.ok(fh.includes('data-central-basis="' + pub.publication_id + '"'));
  assert.ok(fh.includes(pub.attribution.text) && fh.includes('href="' + pub.attribution.terms_url + '"') && fh.includes('rel="noopener noreferrer"'), 'IEX attribution text and terms link');
  const stale = await withNow('2026-10-16T21:00:00Z', () => QS.centralBasis(pub, { v2Inputs: inputs }));
  assert.equal(stale.stale, true); assert.ok(stale.sessions > 2); assert.match(QS.centralText(stale, false), / · STALE$/); assert.match(QS.centralHtml(stale, false), /data-central-state="STALE"/);
  assert.match(QS.centralText(stale, true), /Official V · published centrally · IEX last trade \(not an official close\).* · STALE$/);
  const unknown = await withNow(null, () => QS.centralBasis(pub, { v2Inputs: null }));
  assert.equal(unknown.sessions, null); assert.equal(unknown.stale, null); assert.equal(unknown.calc_differs, null); assert.match(QS.centralText(unknown, false), / · STALE 판정 불가$/);
  const other = await withNow('2026-10-14T21:00:00Z', () => QS.centralBasis(pub, { v2Inputs: { calc_version: 'qgv2-calc/other' } }));
  assert.equal(other.calc_differs, true); assert.match(QS.centralText(other, false), / · 계산 버전 다름$/);
  assert.doesNotMatch(JSON.stringify([fresh, stale, other]), /"price"|last_price|close"/, 'no price in the basis');
  // Without a validated publication: the reason in words, state NA, no attribution, never a device V.
  for (const [publication, reason, want] of [[null, null, 'OFFICIAL_NOT_PUBLISHED'], [null, 'OFFICIAL_UNAVAILABLE', 'OFFICIAL_UNAVAILABLE'], [null, 'OFFICIAL_LOADING', 'OFFICIAL_LOADING'], [structuredClone(pub), null, 'OFFICIAL_INVALID']]) {
    const b = QS.centralBasis(publication, { reason }), h = QS.centralHtml(b, false);
    assert.equal(b.reason, want); assert.equal(b.publication_id, null); assert.equal(QS.centralText(b, false), QS.reasonText(want, false));
    assert.match(h, /data-central-state="NA"/); assert.ok(h.includes('data-na="' + want + '"')); assert.doesNotMatch(h, /data-attribution|기기 V/);
  }
  assert.equal(QS.reasonText('OFFICIAL_LOADING', false), '공식 V 확인 중: 중앙 V 게시본을 읽는 중입니다');
});
test('page publication: a pending read is OFFICIAL_LOADING (never "not published"); a failed re-read keeps the held payload and says so; ready resolves', async () => {
  const { pub, ids } = await vectorPage();
  let read = { publication: null, reason: null, promise: new Promise((res) => setTimeout(res, 5)) };
  QS.setPagePublication(() => read);
  try {
    assert.equal(QS.pagePublication().reason, 'OFFICIAL_LOADING');
    const pending = QS.officialPage({}, { v2Inputs: null, identities: ids });
    assert.equal(pending, null, 'no inputs and no publication: nothing to show');
    const withInputs = QS.officialPage({}, { v2Inputs: screens[SQ.FILE], identities });
    assert.equal(withInputs.v_reason, 'OFFICIAL_LOADING'); assert.equal(withInputs.source, 'NONE');
    assert.ok(Object.values(withInputs.computed.rows).every((r) => r.primary.v === null && r.rank === null));
    await QS.pagePublicationReady();
    read = { publication: null, reason: 'OFFICIAL_NOT_PUBLISHED', promise: Promise.resolve() };
    assert.equal(QS.officialPage({}, { v2Inputs: screens[SQ.FILE], identities }).v_reason, 'OFFICIAL_NOT_PUBLISHED');
    read = { publication: pub, reason: null, last_attempt_reason: 'OFFICIAL_UNAVAILABLE', promise: Promise.resolve() };
    const P = QS.officialPage({}, { v2Inputs: null, identities: ids });
    assert.equal(P.source, 'PUBLICATION'); assert.equal(P.inputs_match, false, 'publication-only rows when no sec-qgv2.json joins');
    assert.ok(Object.values(P.computed.rows).some((r) => Number.isFinite(r.primary.v)), 'the held official V is still shown');
    const b = await withNow('2026-10-14T21:00:00Z', () => QS.centralBasis(QS.pagePublication().publication, {}));
    assert.equal(b.last_attempt_reason, 'OFFICIAL_UNAVAILABLE'); assert.match(QS.centralText(b, false), / · 다시 읽기 실패\(OFFICIAL_UNAVAILABLE\) · 마지막 게시본 표시$/);
    // S06 preset view: the official default is the page result itself; another preset is the personal recompute labelled by its profile.
    assert.equal(QS.presetView(P, {}), P.computed);
    QS.setPageProfile(() => ({ preset: 'growth', gate: true }));
    const G = QS.presetView(P, {});
    assert.equal(G.preset_view, true); assert.equal(G.profile.id, 'qgv-v2/growth/gate-on'); assert.equal(QS.presetView(P, {}), G, 'memoized');
    assert.ok(Object.values(G.rows).every((r) => r.primary.profile.id === 'qgv-v2/growth/gate-on'));
  } finally { QS.setPagePublication(null); QS.setPageProfile(() => ({ preset: null, gate: null })); }
  assert.equal(QS.pagePublication().reason, null, 'no registered read: no reason'); await QS.pagePublicationReady();
});
