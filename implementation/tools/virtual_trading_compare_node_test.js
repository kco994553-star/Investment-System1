'use strict';
// Set comparison (decision 2026-10-11): the JS metrics must equal the Python reference on the shared SYNTHETIC vectors
// (returns through ReportBenchmarks ⑫⑬, capture ratios, max drawdown, volatility, concentration, type exposure, virtual
// trading), every metric below its minimum sample is NA (never 0), the table is numeric only (no strength / weakness /
// watch-item narrative), the only 【AI】 field is the one-line summary, amounts are hidden by the shared money function.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ASSETS = path.join(__dirname, '../src/investment_system/product/web_assets');
const C = require(path.join(ASSETS, 'virtual-trading-compare.js'));
const VT = require(path.join(ASSETS, 'virtual-trading.js'));
const DR = require(path.join(ASSETS, 'daily-report.js'));
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_compare_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));

test('fixture is synthetic and minimums are the documented ones', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
  assert.deepEqual(plain(C.MIN), fixture.min);
  assert.deepEqual(plain(C.MIN), { capture_days: 20, max_drawdown: 20, volatility: 20 });
});

for (const v of fixture.vectors) {
  test('vector ' + v.name + ': JS metrics equal Python', () => {
    assert.deepEqual(plain(C.metrics({ days: v.days, indices: v.indices, basis: v.basis, types: v.types, hits: v.hits, summary: v.summary })), v.expected);
  });
}

test('NA below the minimum samples, never 0; NA reasons are labelled', () => {
  const short = fixture.vectors.find((x) => x.name === 'short_set_below_minimums').expected;
  for (const k of ['volatility', 'max_drawdown', 'upside_capture', 'downside_capture']) assert.deepEqual([short[k].state, short[k].value, short[k].reason], ['NOT_AVAILABLE', null, 'INSUFFICIENT_SAMPLE'], k);
  const none = fixture.vectors.find((x) => x.name === 'not_started').expected;
  for (const x of Object.values(none)) assert.equal(x.value, null);
  for (const c of C.CODES) assert.ok(VT.codeLabel(c, 'ko-KR') && VT.codeLabel(c, 'en-US'), c);
  // Period return equals the ⑫ SINCE_START return of ReportBenchmarks (same gap rules, one source).
  const RB = require(path.join(ASSETS, 'report-benchmarks.js'));
  const v = fixture.vectors.find((x) => x.name === 'gaps_in_spy_and_fx');
  const days = C.compareDays(v.days).map((d) => ({ date: d.date, total_value: d.total_value, deposit: d.deposit }));
  const row = RB.build({ indices: v.indices, ledgers: [{ key: 'X', state: 'OK', reason_codes: [], days }], period: 'SINCE_START' }).periods.find((p) => p.period === 'SINCE_START');
  assert.equal(v.expected.period_return.value, row.target.return);
  assert.equal(v.expected.excess_return.value, row.excess);
});

test('view: ≥ 2 sets, numeric rows only, one 【AI】 line, amounts hidden, phone picks 2–3 sets, PC shows all', () => {
  const long = fixture.vectors.find((x) => x.name === 'long_set_krw');
  const ledger = (x) => ({ state: 'OK', reason_codes: [], days: x.days, summary: x.summary });
  const entries = [{ id: 'set_a', kind: 'SET_A', label: '세트 A', ledger: ledger(long), hits: long.hits },
    { id: 'set_b-1', kind: 'SET_B', label: '세트 B', purpose: '반도체 비교', ledger: ledger(fixture.vectors.find((x) => x.name === 'short_set_below_minimums')), hits: null },
    { id: 'set_c-1', kind: 'SET_C', label: '세트 C', purpose: '아직 시작 전', ledger: { state: 'NOT_STARTED', reason_codes: ['BEFORE_START_DATE'], days: [] } }];
  assert.equal(C.build(entries.slice(0, 1), { indices: long.indices }).state, 'NOT_AVAILABLE');
  const view = C.build(entries, { indices: long.indices, types: long.types });
  assert.equal(view.state, 'READY');
  const money = (x) => DR.money(x, { hidden: true });
  const pc = C.html(view, { money, wide: true }), phone = C.html(view, { money, wide: false, picked: ['set_a', 'set_b-1'] });
  for (const [, name] of C.ROWS) assert.ok(pc.includes(name.replace(/&/g, '&amp;')), name);
  assert.equal((pc.match(/data-compare-set=/g) || []).length, 3);
  assert.equal((phone.match(/data-compare-set=/g) || []).length, 2);
  assert.ok(phone.includes('data-compare-pick="set_c-1"') && !pc.includes('data-compare-pick'));
  for (const out of [pc, phone]) {
    assert.ok(!/장점|약점|관찰항목|관찰 항목/.test(out), 'no narrative fields');
    assert.equal((out.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length, 0, 'amounts hidden');
    assert.ok(out.includes(VT.DISCLAIMER.ko));
  }
  const text = C.template(view, { money: (x) => DR.money(x, { hidden: true, mode: 'export' }) });
  assert.equal((text.match(/【AI】/g) || []).length, 1);
  assert.ok(text.includes('한 줄 요약: 【AI】'));
  assert.ok(!/장점|약점|관찰항목/.test(text));
  assert.ok(text.includes('[숨김]') && !text.includes('112371485'));
});

test('module performs no I/O and logs nothing', () => {
  const src = fs.readFileSync(path.join(ASSETS, 'virtual-trading-compare.js'), 'utf8');
  for (const w of ['fetch(', 'localStorage', 'sessionStorage', 'indexedDB', 'console.', 'sendBeacon', 'XMLHttpRequest']) assert.ok(!src.includes(w), w);
});
