'use strict';
// lab-backtest-v1 test fixture (common base 2026-10-31; web_app/lab.js IS2.lab.validate). SYNTHETIC VALUES ONLY: every number is
// made up here from fixed monthly returns, no run is a real research result, and nothing here is written to a public file.
// Each run's metrics are computed from its own curve below, so every consistency rule of the validator passes by construction:
// total_return = last strategy / 100 - 1, cagr and benchmark_cagr annualised over the period's actual days / 365.25,
// excess_cagr = cagr - benchmark_cagr, max_drawdown = the monthly curve's drawdown (or deeper, as a daily one can be),
// volatility = the monthly returns' standard deviation × √12.
//  - payload(): two runs — a REAL + NOT_VALIDATED PILOT with a cash benchmark (sharpe null with its reason; period.end in the
//    middle of June, a partial last month) and a SYNTHETIC run.
//  - empty(): runs []. mixedRun(), pitFalseRun(): one more run each (MIXED data; universe.point_in_time false).
//  - valid: more payloads the validator must accept; invalid: one payload per rejection rule, with its code and path.
const SYNTHETIC_NOTE = '시험용 합성 값 · 실제 연구 결과 아님 (fixture)';
const COMMIT = 'f00dfeed'.repeat(5);
const r6 = (x) => Math.round(x * 1e6) / 1e6;
const r4 = (x) => Math.round(x * 1e4) / 1e4;

function months(first, n) {
  let [y, m] = first.split('-').map(Number); const out = [];
  for (let i = 0; i < n; i++) { out.push(y + '-' + String(m).padStart(2, '0')); m++; if (m > 12) { m = 1; y++; } }
  return out;
}
// A curve from 100 / 100 with the given monthly returns (strategy, benchmark), values rounded to 4 decimals.
function curve(first, rs, rb) {
  const dates = months(first, rs.length + 1); let s = 100, b = 100;
  return dates.map((date, i) => { if (i) { s *= 1 + rs[i - 1]; b *= 1 + rb[i - 1]; } return { date, strategy: i ? r4(s) : 100, benchmark: i ? r4(b) : 100 }; });
}
const years = (p) => (Date.parse(p.end + 'T00:00:00Z') - Date.parse(p.start + 'T00:00:00Z')) / 864e5 / 365.25;
function drawdown(c) { let peak = -Infinity, worst = 0; for (const p of c) { peak = Math.max(peak, p.strategy); worst = Math.min(worst, p.strategy / peak - 1); } return worst; }
// Metrics from the curve: {sharpe: false} leaves sharpe null; deeper > 0 makes max_drawdown deeper than the monthly one.
function metricsOf(period, c, { sharpe = true, deeper = 0 } = {}) {
  const y = years(period), last = c[c.length - 1];
  const total = r6(last.strategy / 100 - 1), cagr = r6(Math.pow(1 + total, 1 / y) - 1), bench = r6(Math.pow(last.benchmark / 100, 1 / y) - 1);
  const rets = c.slice(1).map((p, i) => p.strategy / c[i].strategy - 1), mean = rets.reduce((a, b) => a + b, 0) / rets.length;
  const vol = r6(Math.sqrt(rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length - 1)) * Math.sqrt(12));
  return { cagr, total_return: total, max_drawdown: r6(drawdown(c) - deeper), volatility: vol, sharpe: sharpe ? r6((mean * 12) / vol) : null, benchmark_cagr: bench, excess_cagr: r6(cagr - bench) };
}
function run({ id, name, data_status, run_type = 'PILOT', validation_status = 'NOT_VALIDATED', point_in_time = true, period, benchmark, rs, rb, sharpe = true, deeper = 0, rebalance = 'monthly' }) {
  const c = curve(period.start.slice(0, 7), rs, rb), metrics = metricsOf(period, c, { sharpe, deeper });
  return {
    id, name, description: SYNTHETIC_NOTE, run_type, data_status, validation_status, qgv_version: 'v2',
    universe: { definition: 'Universe504 (시험용 정의)', point_in_time, survivorship_note: point_in_time ? '시점별 모집단 사용 (시험용 서술)' : '현재 생존 종목만 · 시점별 모집단 아님 (시험용 서술)' },
    period, rebalance, benchmark, costs: { fee_bps: 5, slippage_bps: 10 }, metrics,
    null_reasons: sharpe ? {} : { sharpe: '무위험 수익률 기준 미정 (시험용)' },
    equity_curve: c, limitations: [SYNTHETIC_NOTE, '과거 성과는 미래를 보장하지 않음'],
  };
}
const S1 = [0.021, -0.034, 0.012, 0.027, -0.018, 0.009, 0.031, -0.042, 0.016, 0.024, -0.011, 0.019, 0.008, -0.026, 0.033, 0.014, -0.007];
const CASH = S1.map(() => 0.0035);
const wave = (n, a, b, k) => Array.from({ length: n }, (_, i) => a * Math.sin((i + 1) * k) + b);
const pilot = () => run({ id: 'pilot-real-cash', name: '실데이터 파일럿 (시험용 합성 값)', data_status: 'REAL', period: { start: '2024-01-31', end: '2025-06-20' },
  benchmark: { name: '현금 (시험용 금리)', total_return: true }, rs: S1, rb: CASH, sharpe: false, deeper: 0.012 });
const synthetic = () => run({ id: 'synthetic-demo', name: '합성 데이터 시험 실행', data_status: 'SYNTHETIC', period: { start: '2023-01-01', end: '2024-12-31' },
  benchmark: { name: '합성 지수 (시험용)', total_return: true }, rs: wave(23, 0.03, 0.006, 0.9), rb: wave(23, 0.02, 0.005, 0.7), rebalance: 'quarterly' });
const mixedRun = () => run({ id: 'mixed-pilot', name: '혼합 자료 파일럿 (시험용 합성 값)', data_status: 'MIXED', period: { start: '2022-01-03', end: '2022-12-30' },
  benchmark: { name: '합성 지수 (시험용)', total_return: false }, rs: wave(11, 0.025, 0.004, 1.3), rb: wave(11, 0.015, 0.003, 1.1) });
const pitFalseRun = () => run({ id: 'pit-false-pilot', name: '현재 생존 종목 파일럿 (시험용 합성 값)', data_status: 'REAL', point_in_time: false, period: { start: '2021-03-01', end: '2022-02-28' },
  benchmark: { name: '합성 지수 (시험용)', total_return: true }, rs: wave(11, 0.02, 0.003, 0.5), rb: wave(11, 0.01, 0.004, 0.6) });
const wrap = (runs) => ({ schema_version: 'lab-backtest-v1', generated_at: '2026-10-31T09:00:00Z', source_commit: COMMIT, runs });
const payload = () => wrap([pilot(), synthetic()]);
const empty = () => wrap([]);

// A fresh payload changed by fn(p) (p.runs[0] is the REAL pilot, p.runs[1] the SYNTHETIC run).
const edit = (fn, base = payload) => () => { const p = base(); fn(p, p.runs[0], p.runs[1]); return p; };
const allNull = (r) => { for (const k of Object.keys(r.metrics)) { r.metrics[k] = null; r.null_reasons[k] = '시험용 · 계산 안 함'; } };
const valid = [
  ['empty runs', empty],
  ['with a MIXED and a point_in_time false run', () => wrap([pilot(), synthetic(), mixedRun(), pitFalseRun()])],
  ['generated_at with an offset and fractions', edit((p) => { p.generated_at = '2026-10-31T18:00:00.123+09:00'; })],
  ['every metric null with its reason and an empty curve', edit((p, r) => { allNull(r); r.equity_curve = []; })],
  ['every metric null and a one-point curve in a one-month period', edit((p, r) => { allNull(r); r.period = { start: '2024-01-02', end: '2024-01-30' }; r.equity_curve = [{ date: '2024-01', strategy: 100, benchmark: 100 }]; })],
  ['FORMAL, PIT_VERIFIED and REVIEWED runs', edit((p, r, s) => { r.run_type = 'FORMAL'; r.validation_status = 'PIT_VERIFIED'; s.validation_status = 'REVIEWED'; })],
  ['zero costs and no limitations', edit((p, r) => { r.costs = { fee_bps: 0, slippage_bps: 0 }; r.limitations = []; })],
  ['max_drawdown exactly the monthly drawdown', edit((p, r) => { r.metrics.max_drawdown = r6(drawdown(r.equity_curve)); })],
];
// [name, code, path, make]: the first fault of each payload is the one named.
const R0 = '$.runs[0]';
const invalid = [
  ['not an object: array', 'NOT_OBJECT', '$', () => [payload()]],
  ['not an object: JSON text', 'NOT_OBJECT', '$', () => JSON.stringify(payload())],
  ['not an object: null', 'NOT_OBJECT', '$', () => null],
  ['wrong schema_version', 'SCHEMA_VERSION', '$.schema_version', edit((p) => { p.schema_version = 'lab-backtest-v2'; })],
  ['missing top key', 'KEY_MISSING', '$.source_commit', edit((p) => { delete p.source_commit; })],
  ['unknown top key', 'KEY_UNKNOWN', '$.note', edit((p) => { p.note = 'x'; })],
  ['missing nested key', 'KEY_MISSING', R0 + '.universe.survivorship_note', edit((p, r) => { delete r.universe.survivorship_note; })],
  ['unknown metric key', 'KEY_UNKNOWN', R0 + '.metrics.alpha', edit((p, r) => { r.metrics.alpha = 0.1; })],
  ['unknown curve point key', 'KEY_UNKNOWN', R0 + '.equity_curve[2].price', edit((p, r) => { r.equity_curve[2].price = 10; })],
  ['missing run key', 'KEY_MISSING', R0 + '.limitations', edit((p, r) => { delete r.limitations; })],
  ['runs not a list', 'TYPE', '$.runs', edit((p) => { p.runs = {}; })],
  ['point_in_time not a boolean', 'TYPE', R0 + '.universe.point_in_time', edit((p, r) => { r.universe.point_in_time = 'yes'; })],
  ['metric as a string', 'TYPE', R0 + '.metrics.cagr', edit((p, r) => { r.metrics.cagr = String(r.metrics.cagr); })],
  ['curve value as a string', 'TYPE', R0 + '.equity_curve[3].strategy', edit((p, r) => { r.equity_curve[3].strategy = String(r.equity_curve[3].strategy); })],
  ['empty description', 'TYPE', R0 + '.description', edit((p, r) => { r.description = ' '; })],
  ['empty limitation', 'TYPE', R0 + '.limitations[1]', edit((p, r) => { r.limitations[1] = ''; })],
  ['name too long', 'TOO_LARGE', R0 + '.name', edit((p, r) => { r.name = 'x'.repeat(201); })],
  ['bad run id', 'ID_INVALID', R0 + '.id', edit((p, r) => { r.id = 'bad id'; })],
  ['wrong data_status', 'ENUM', R0 + '.data_status', edit((p, r) => { r.data_status = 'REALISH'; })],
  ['wrong run_type', 'ENUM', R0 + '.run_type', edit((p, r) => { r.run_type = 'pilot'; })],
  ['wrong validation_status', 'ENUM', R0 + '.validation_status', edit((p, r) => { r.validation_status = 'VALIDATED'; })],
  ['wrong qgv_version', 'ENUM', R0 + '.qgv_version', edit((p, r) => { r.qgv_version = 'v1'; })],
  ['wrong rebalance', 'ENUM', R0 + '.rebalance', edit((p, r) => { r.rebalance = 'hourly'; })],
  ['impossible start day', 'DATE_INVALID', R0 + '.period.start', edit((p, r) => { r.period.start = '2024-02-30'; })],
  ['bad curve month', 'DATE_INVALID', R0 + '.equity_curve[1].date', edit((p, r) => { r.equity_curve[1].date = '2024-13'; })],
  ['start equals end', 'PERIOD_ORDER', R0 + '.period', edit((p, r) => { r.period.end = r.period.start; })],
  ['start after end', 'PERIOD_ORDER', R0 + '.period', edit((p, r) => { r.period = { start: '2025-07-01', end: '2024-01-31' }; })],
  ['generated_at without a zone', 'GENERATED_AT_ZONE', '$.generated_at', edit((p) => { p.generated_at = '2026-10-31T09:00:00'; })],
  ['generated_at impossible hour', 'DATE_INVALID', '$.generated_at', edit((p) => { p.generated_at = '2026-10-31T25:00:00Z'; })],
  ['generated_at a date only', 'DATE_INVALID', '$.generated_at', edit((p) => { p.generated_at = '2026-10-31'; })],
  ['source_commit 39 hex', 'SOURCE_COMMIT', '$.source_commit', edit((p) => { p.source_commit = COMMIT.slice(1); })],
  ['source_commit not hex', 'SOURCE_COMMIT', '$.source_commit', edit((p) => { p.source_commit = 'g'.repeat(40); })],
  ['duplicate run id', 'RUN_ID_DUPLICATE', '$.runs[1].id', edit((p, r, s) => { s.id = r.id; })],
  ['non-finite number (JSON 1e999)', 'NUMBER_NOT_FINITE', R0 + '.metrics.volatility', () => JSON.parse(JSON.stringify(payload()).replace(/"volatility":[^,]+/, '"volatility":1e999'))],
  ['NaN cost', 'NUMBER_NOT_FINITE', R0 + '.costs.fee_bps', edit((p, r) => { r.costs.fee_bps = NaN; })],
  ['null metric without a reason', 'NULL_REASON_MISSING', R0 + '.null_reasons.sharpe', edit((p, r) => { delete r.null_reasons.sharpe; })],
  ['null metric with a blank reason', 'NULL_REASON_MISSING', R0 + '.null_reasons.sharpe', edit((p, r) => { r.null_reasons.sharpe = '  '; })],
  ['null_reasons key that is not a metric', 'NULL_REASON_KEY', R0 + '.null_reasons.alpha', edit((p, r) => { r.null_reasons.alpha = '시험용'; })],
  ['null_reasons for a metric that is not null', 'NULL_REASON_UNUSED', R0 + '.null_reasons.cagr', edit((p, r) => { r.null_reasons.cagr = '시험용'; })],
  ['max_drawdown above 0', 'MAX_DRAWDOWN_RANGE', R0 + '.metrics.max_drawdown', edit((p, r) => { r.metrics.max_drawdown = 0.05; })],
  ['max_drawdown below -1', 'MAX_DRAWDOWN_RANGE', R0 + '.metrics.max_drawdown', edit((p, r) => { r.metrics.max_drawdown = -1.2; })],
  ['negative volatility', 'VOLATILITY_RANGE', R0 + '.metrics.volatility', edit((p, r) => { r.metrics.volatility = -0.1; })],
  ['negative fee', 'COST_NEGATIVE', R0 + '.costs.fee_bps', edit((p, r) => { r.costs.fee_bps = -1; })],
  ['negative slippage', 'COST_NEGATIVE', R0 + '.costs.slippage_bps', edit((p, r) => { r.costs.slippage_bps = -0.5; })],
  ['excess_cagr off by 1e-5', 'EXCESS_CAGR_MISMATCH', R0 + '.metrics.excess_cagr', edit((p, r) => { r.metrics.excess_cagr += 1e-5; })],
  ['excess_cagr with benchmark_cagr null', 'EXCESS_CAGR_MISMATCH', R0 + '.metrics.excess_cagr', edit((p, r) => { r.metrics.benchmark_cagr = null; r.null_reasons.benchmark_cagr = '시험용'; })],
  ['total_return off the last point', 'TOTAL_RETURN_MISMATCH', R0 + '.metrics.total_return', edit((p, r) => { r.metrics.total_return = r6(r.metrics.total_return + 0.001); })],
  ['cagr off total_return', 'CAGR_MISMATCH', R0 + '.metrics.cagr', edit((p, r) => { r.metrics.cagr = r6(r.metrics.cagr + 0.01); r.metrics.excess_cagr = r6(r.metrics.cagr - r.metrics.benchmark_cagr); })],
  ['cagr off the curve with total_return null', 'CAGR_MISMATCH', R0 + '.metrics.cagr', edit((p, r) => { r.metrics.total_return = null; r.null_reasons.total_return = '시험용'; r.metrics.cagr = r6(r.metrics.cagr - 0.01); r.metrics.excess_cagr = r6(r.metrics.cagr - r.metrics.benchmark_cagr); })],
  ['benchmark_cagr off the benchmark curve', 'BENCHMARK_CAGR_MISMATCH', R0 + '.metrics.benchmark_cagr', edit((p, r) => { r.metrics.benchmark_cagr = r6(r.metrics.benchmark_cagr + 0.01); r.metrics.excess_cagr = r6(r.metrics.cagr - r.metrics.benchmark_cagr); })],
  ['max_drawdown milder than the curve', 'MAX_DRAWDOWN_MISMATCH', R0 + '.metrics.max_drawdown', edit((p, r) => { r.metrics.max_drawdown = r6(drawdown(r.equity_curve) + 0.01); })],
  ['first month not period.start month', 'CURVE_START', R0 + '.equity_curve[0].date', edit((p, r) => { r.period.start = '2023-12-29'; })],
  ['first strategy not 100', 'CURVE_START', R0 + '.equity_curve[0]', edit((p, r) => { r.equity_curve[0].strategy = 101; })],
  ['first benchmark not 100', 'CURVE_START', R0 + '.equity_curve[0]', edit((p, r) => { r.equity_curve[0].benchmark = 99.5; })],
  ['last month not period.end month', 'CURVE_END', R0 + '.equity_curve[17].date', edit((p, r) => { r.period.end = '2025-07-15'; })],
  ['months not ascending', 'CURVE_ORDER', R0 + '.equity_curve[5].date', edit((p, r) => { const c = r.equity_curve; [c[4].date, c[5].date] = [c[5].date, c[4].date]; })],
  ['duplicate month', 'CURVE_DUPLICATE', R0 + '.equity_curve[2].date', edit((p, r) => { r.equity_curve[2].date = r.equity_curve[1].date; })],
  ['one point with metrics', 'CURVE_TOO_SHORT', R0 + '.equity_curve', edit((p, r) => { r.equity_curve = r.equity_curve.slice(0, 1); })],
  ['empty curve with total_return', 'CURVE_TOO_SHORT', R0 + '.equity_curve', edit((p, r) => { allNull(r); r.metrics.total_return = 0.1; delete r.null_reasons.total_return; r.equity_curve = []; })],
  ['empty curve with cagr', 'CURVE_TOO_SHORT', R0 + '.equity_curve', edit((p, r) => { allNull(r); r.metrics.cagr = 0.1; delete r.null_reasons.cagr; r.equity_curve = []; })],
  ['zero strategy value', 'CURVE_VALUE', R0 + '.equity_curve[3].strategy', edit((p, r) => { r.equity_curve[3].strategy = 0; })],
  ['negative benchmark value', 'CURVE_VALUE', R0 + '.equity_curve[4].benchmark', edit((p, r) => { r.equity_curve[4].benchmark = -5; })],
];

module.exports = Object.freeze({ SYNTHETIC_NOTE, COMMIT, payload, empty, mixedRun, pitFalseRun, wrap, metricsOf, drawdown, years, valid, invalid });
