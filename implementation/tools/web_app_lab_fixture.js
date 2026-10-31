'use strict';
// Feature 9 Lab test fixture (tools/web_app_lab_browser_test.js, tools/web_app_lab_node_test.js). SYNTHETIC VALUES ONLY: made-up
// Q·G scores and dates in the shape web_assets/forward-validation.js validates (ForwardValidation.validate); the ledger is price
// free like the published one; nothing here is written to a public file.
//  - ledgerV2(): schema 2, 7 US session days 2026-10-19 .. 2026-10-27. v2 rows: 10/19 PREPARATORY (no calc version, low coverage,
//    segment NONE), 10/20-10/22 PRIMARY under calc version A, 10/23 NOT_AVAILABLE (input missing), 10/26-10/27 PRIMARY under B
//    (three segments, never chained); v1 rows on every day but 10/22 (a PARTIAL day in the evidence). 13 table rows.
//  - ledgerV1(): schema 1, v1 only (10/19 recorded, 10/20 input missing), no observation basis.
//  - ledgerEmpty(): schema 2 after the start date with no row (ACTIVE, 0 records); ledgerNotStarted(): before the start date.
//  - sources(F): IS2.lab.source() answers for each Lab state, from tools/lab_backtest_fixture.js (F).
const V1 = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', V2 = 'forward_validation/v2', H = 'c'.repeat(64);
// Two made-up calc version names (the app never hard-codes one; these are only data of the synthetic ledger).
const CALC_A = ['qgv2', 'calc/2026-10-15.1'].join('-'), CALC_B = ['qgv2', 'calc/2026-10-23.1'].join('-');
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const SESSIONS = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-26', '2026-10-27'];
const target = () => ({ portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } });
// Companies of a recorded row: every 4th company NOT_AVAILABLE, the rest `live` (LIVE or STALE); scores move a little with the day index k.
function companies(k, size, live = 'LIVE') {
  const out = {};
  IDS.forEach((id, i) => {
    out[id] = i % 4 ? { state: live, Q: { score: 40 + i + k, coverage: 'PARTIAL', missing_factor_count: 1 }, G: { score: 60 - i + k / 2, coverage: 'PARTIAL', missing_factor_count: 2 } }
      : { state: 'NOT_AVAILABLE', Q: { score: null, coverage: 'BLOCKED', missing_factor_count: size.Q }, G: { score: null, coverage: 'BLOCKED', missing_factor_count: size.G } };
  });
  return out;
}
function v1Row(date, k) {
  return { date, version: V1, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: target(), qg_as_of: date + 'T22:10:00+00:00',
    qg_screen_state: 'LIVE', companies: companies(k, { Q: 7, G: 6 }), source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function v1Missing(date) {
  return { date, version: V1, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'NOT_AVAILABLE', reason_codes: ['SEC_QG_FACTORS_MISSING'], target: target(), qg_as_of: null,
    qg_screen_state: null, companies: null, source_sha256: { 'sec-qg-factors.json': null, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' };
}
function v2Row(date, k, basis) {
  return { date, version: V2, strategy: 'QGV_STANDARD_V2', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: target(), qg_as_of: date + 'T22:10:00+00:00',
    qg_screen_state: k === 1 ? 'STALE' : 'LIVE', companies: companies(k, { Q: 5, G: 5 }, k === 1 ? 'STALE' : 'LIVE'), source_sha256: { 'sec-qgv2.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00', basis };
}
function v2Missing(date) {
  return { date, version: V2, strategy: 'QGV_STANDARD_V2', calibration: 'UNCALIBRATED', state: 'NOT_AVAILABLE', reason_codes: ['SEC_QGV2_MISSING'], target: target(), qg_as_of: null,
    qg_screen_state: null, companies: null, source_sha256: { 'sec-qgv2.json': null, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00',
    basis: { calc_version: null, q_scored: null, g_scored: null, population: null, acquired: null, evaluation: { eligible: false, status: 'PREPARATORY', reasons: ['RECORD_NOT_AVAILABLE'] }, segment: null } };
}
const prep = (d) => ({ calc_version: null, q_scored: 300, g_scored: 290, population: { n: 310, id: '0123456789abcdef' }, acquired: [d, d], evaluation: { eligible: false, status: 'PREPARATORY', reasons: ['Q_BELOW_454', 'G_BELOW_454', 'CALC_VERSION_MISSING'] }, segment: 'NONE' });
const primary = (d, calc) => ({ calc_version: calc, q_scored: 470, g_scored: 466, population: { n: 480, id: 'fedcba9876543210' }, acquired: [d, d], evaluation: { eligible: true, status: 'PRIMARY', reasons: [] }, segment: calc });
function top(schema, asOf, versions) {
  const status = (d) => ({ state: d, v_included: false, reason_codes: [] }), st = asOf.slice(0, 10) >= '2026-10-19' ? 'ACTIVE' : 'NOT_STARTED';
  const vs = { [V1]: status(st), [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } };
  if (schema === 2) vs[V2] = status(st);
  return { schema_version: schema, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status: st, as_of: asOf, strategy: schema === 2 ? 'QGV_STANDARD_V2' : 'QGV_STANDARD_V1',
    calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true, target: { portfolio_id: 'TARGET', version: 'v0' }, versions, version_status: vs };
}
function ledgerV2() {
  const v2 = SESSIONS.map((d, k) => (d === '2026-10-23' ? v2Missing(d) : v2Row(d, k, k === 0 ? prep(d) : primary(d, k < 4 ? CALC_A : CALC_B))));
  const v1 = SESSIONS.filter((d) => d !== '2026-10-22').map((d) => v1Row(d, SESSIONS.indexOf(d)));
  return top(2, '2026-10-27T22:31:00+00:00', { [V1]: v1, [VV]: [], [V2]: v2 });
}
const ledgerV1 = () => top(1, '2026-10-20T22:31:00+00:00', { [V1]: [v1Row('2026-10-19', 0), v1Missing('2026-10-20')], [VV]: [] });
const ledgerEmpty = () => top(2, '2026-10-20T22:31:00+00:00', { [V1]: [], [VV]: [], [V2]: [] });
const ledgerNotStarted = () => top(2, '2026-10-16T22:31:00+00:00', { [V1]: [], [VV]: [], [V2]: [] });

// IS2.lab.source() answers (the common base shape: {state, code, payload, private, text, private_text}). Payloads come from the
// lab-backtest-v1 fixture; an invalid one is looked up by its name there.
function sources(F) {
  const bad = (name) => { const x = F.invalid.find((r) => r[0] === name); if (!x) throw new Error('no invalid fixture ' + name); return { code: x[1], payload: x[3]() }; };
  const good = (name) => { const x = F.valid.find((r) => r[0] === name); if (!x) throw new Error('no valid fixture ' + name); return x[1](); };
  const ok = (payload) => ({ state: 'OK', code: null, payload, private: 'PRIVATE_SIGNED_IN', text: null, private_text: null });
  const refused = (name) => { const b = bad(name); return { src: ok(b.payload), code: b.code }; };
  return {
    normal: ok(F.payload()),
    empty: ok(F.empty()),
    notFound: { state: 'ERROR', code: 'LAB_RESULT_NOT_FOUND', payload: null, private: 'PRIVATE_SIGNED_IN', text: null, private_text: null },
    login: { state: 'NONE', code: 'LAB_NO_PUBLIC_RESULT', payload: null, private: 'PRIVATE_LOGIN_REQUIRED', text: '연구 결과가 아직 없습니다', private_text: '비공개 연구 결과 · 로그인 필요' },
    allNull: ok(good('every metric null with its reason and an empty curve')),
    fourRuns: ok(good('with a MIXED and a point_in_time false run')),
    refused: {
      schema: refused('wrong schema_version'), missingTop: refused('missing top key'), missingRun: refused('missing run key'),
      order: refused('months not ascending'), start: refused('first strategy not 100'), total: refused('total_return off the last point'),
      finite: refused('non-finite number (JSON 1e999)'), zero: refused('zero strategy value'), negative: refused('negative benchmark value'),
    },
  };
}

module.exports = Object.freeze({ V1, V2, VV, CALC_A, CALC_B, SESSIONS, ledgerV2, ledgerV1, ledgerEmpty, ledgerNotStarted, sources });
