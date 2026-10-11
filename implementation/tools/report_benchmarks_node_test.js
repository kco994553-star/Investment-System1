'use strict';
// S17 ⑪⑫⑬: on the shared SYNTHETIC vectors the JS ReportBenchmarks equals the Python reference (qgv/report_benchmarks.py):
// index normalisation (base = session before the period = 100), gaps without interpolation, KRW/USD basis, ledger
// time-weighted chain, period table, hit-window aggregation with the 30-sample minimum and expected first dates.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const RB = require('../src/investment_system/product/web_assets/report-benchmarks.js');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/report_benchmarks_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));

function close(actual, expected, where) {
  if (typeof expected === 'number' && typeof actual === 'number') {
    assert.ok(Math.abs(actual - expected) <= 1e-12 * Math.max(1, Math.abs(expected)), where + ': ' + actual + ' != ' + expected);
  } else if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual) && actual.length === expected.length, where + ' length');
    expected.forEach((x, i) => close(actual[i], x, where + '[' + i + ']'));
  } else if (expected !== null && typeof expected === 'object') {
    assert.deepEqual(Object.keys(actual).sort(), Object.keys(expected).sort(), where + ' keys');
    for (const k of Object.keys(expected)) close(actual[k], expected[k], where + '.' + k);
  } else assert.equal(actual, expected, where);
}

test('fixture is marked synthetic', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
});

for (const v of fixture.build_vectors) {
  test('build ' + v.name + ': JS equals Python', () => close(plain(RB.build(v.inputs)), v.expected, v.name));
}
for (const v of fixture.track_vectors) {
  test('track ' + v.name + ': JS engine hits and track record equal Python', () => {
    if (v.inputs.ledger_input) close(plain(VT.evaluateHits(VT.defaultConfig(), v.inputs.ledger_input, v.inputs.trades)), v.inputs.hits, v.name + ' hits');
    close(plain(RB.trackRecord(v.inputs)), v.expected, v.name);
  });
}

test('no interpolation: a missing close is a gap (null) with a code, never the previous value', () => {
  const v = fixture.build_vectors.find((x) => x.name === 'usd_since_start'), out = RB.build(v.inputs);
  const xlk = out.dashboard.series.find((s) => s.key === 'XLK'), i = out.dashboard.sessions.indexOf('2026-11-02');
  assert.equal(xlk.points[i], null);
  assert.equal(xlk.gap_codes[i], 'CLOSE_MISSING');
  assert.notEqual(xlk.points[i - 1], null);
  const krw = RB.build({ ...v.inputs, basis: 'KRW' }).dashboard.series.find((s) => s.key === 'SP500');
  assert.equal(krw.gap_codes[out.dashboard.sessions.indexOf('2026-11-11')], 'FX_MISSING', 'KRW=X missing → gap, not the previous rate');
});

test('base = close of the session before the period start = 100; return = last/base − 1', () => {
  const v = fixture.build_vectors.find((x) => x.name === 'krw_20d');
  const ix = v.inputs.indices, cal = Object.keys(ix.SPY).sort(), w = RB.periodWindow(cal, '2026-11-30', '5D', null);
  assert.equal(w.base, cal[cal.length - 6]);
  assert.deepEqual(w.sessions, cal.slice(-5));
  const s = RB.priceIndex(ix.SPY, ix['KRW=X'], w, 'USD');
  assert.ok(Math.abs(s.return - (ix.SPY['2026-11-30'] / ix.SPY[w.base] - 1)) < 1e-15);
  assert.ok(Math.abs(s.points[4] - 100 * ix.SPY['2026-11-30'] / ix.SPY[w.base]) < 1e-9);
});

test('ledger index equals the engine time-weighted chain on an engine run without gaps', () => {
  const inputs = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_inputs_v1.json'), 'utf8'));
  const v = inputs.vectors.find((x) => x.name === 'full_synthetic'), input = v.expected.ledgers.SET_A.input;
  const result = VT.runLedger({ ...VT.defaultConfig(), start_date: v.inputs.config.start_date }, input);
  assert.equal(result.state, 'OK');
  const days = result.days.map((d) => ({ date: d.date, total_value: d.total_value, deposit: d.deposit }));
  assert.ok(days.length > 5 && days.every((d) => typeof d.total_value === 'number'));
  const out = RB.build({ indices: { SPY: input.benchmarks.SP500 }, ledgers: [{ key: 'SET_A', state: 'OK', reason_codes: [], days }], period: 'SINCE_START', basis: 'KRW' });
  const row = out.periods.find((p) => p.period === 'SINCE_START');
  assert.equal(row.target.state, 'OK');
  assert.ok(Math.abs(row.target.return - result.summary.twr) < 1e-12);
});

test('track record: hit rate hidden below 30 samples, shown from 30', () => {
  const v = fixture.track_vectors.find((x) => x.name === 'enough_samples'), out = RB.trackRecord(v.inputs);
  const d5 = out.windows.find((w) => w.window === 5), d63 = out.windows.find((w) => w.window === 63);
  assert.equal(d5.state, 'OK'); assert.ok(d5.samples >= 30 && typeof d5.hit_rate === 'number');
  assert.equal(d63.state, 'INSUFFICIENT_SAMPLE'); assert.ok(d63.samples > 0 && d63.samples < 30);
  assert.equal(d63.hit_rate, null); assert.equal(d63.hits, null);
  const before = RB.trackRecord(fixture.track_vectors.find((x) => x.name === 'before_start').inputs);
  assert.deepEqual(before.windows.map((w) => [w.window, w.state, w.reason, w.expected_first]),
    [[5, 'NOT_AVAILABLE', 'BEFORE_START_DATE', '2026-10-27'], [20, 'NOT_AVAILABLE', 'BEFORE_START_DATE', '2026-11-17'], [63, 'NOT_AVAILABLE', 'BEFORE_START_DATE', '2027-01-21']]);
});

test('estimated sessions skip weekends and the listed NYSE holidays', () => {
  assert.deepEqual(RB.nthSessionAfter([], '2026-11-25', 1), ['2026-11-27', true]);
  assert.deepEqual(RB.nthSessionAfter(['2026-10-19', '2026-10-20'], '2026-10-18', 2), ['2026-10-20', false]);
  assert.deepEqual(RB.nthSessionAfter(['2026-10-19'], '2026-10-18', 2), ['2026-10-20', true]);
});

test('chart: one path per series run, gaps break lines, no price or amount text', () => {
  const v = fixture.build_vectors.find((x) => x.name === 'usd_since_start'), out = RB.build(v.inputs);
  const svg = RB.chartSvg(out.dashboard, { target: 'SET_A' });
  assert.ok(svg.startsWith('<svg') && svg.includes('data-bench-line="SET_A"') && svg.includes('data-bench-line="SP500"'));
  assert.equal((svg.match(/data-bench-line="XLK"/g) || []).length, 2, 'XLK gap splits its line');
  assert.ok(!svg.includes('data-bench-line="VUG"'), 'unavailable series is not drawn');
  for (const close of Object.values(v.inputs.indices.SPY).slice(-3)) assert.ok(!svg.includes(String(close)), 'no raw close in the chart');
  assert.equal(RB.chartSvg({ state: 'NOT_AVAILABLE' }), '');
});

test('module is pure: no network, storage or console', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/report-benchmarks.js'), 'utf8');
  for (const bad of ['fetch(', 'localStorage', 'sessionStorage', 'indexedDB', 'console.', 'XMLHttpRequest', 'sendBeacon']) assert.ok(!src.includes(bad), bad);
});
test('user sets C and D have series labels and colours (⑬ on the Set C/D tabs)', () => {
  for (const key of ['SET_C', 'SET_D']) { assert.ok(Array.isArray(RB.SERIES_LABELS[key]) && RB.SERIES_LABELS[key].length === 2, key); assert.match(RB.COLORS[key], /^#[0-9a-f]{6}$/, key); }
});
