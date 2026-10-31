'use strict';
// Virtual trading signals: on the shared SYNTHETIC runner-level vectors the JS runner assembly + engine + signal helpers
// must equal the Python reference (D-5 abnormal drop with ≥273 closes and its D-22 ETF, <273 → basis NOT_AVAILABLE,
// missing ETF → S&P 500 fallback labelled, V slope READY from stored V, rehearsal window and Q·G fill, device V scores).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const R = require('../src/investment_system/product/web_assets/virtual-trading-runner.js');
const S = require('../src/investment_system/product/web_assets/virtual-trading-signals.js');
const DV = require('../src/investment_system/product/web_assets/device-valuation.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_signals_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));
const FOCUS = ['amzn', 'googl', 'msft', 'nvda'];
function project(result) {
  const days = result.days, last = days.at(-1);
  return { state: result.state, reason_codes: result.reason_codes, sessions: days.map((d) => d.date),
    mains: Object.fromEntries(days.map((d) => [d.date, Object.fromEntries(FOCUS.filter((c) => d.judgements[c]).map((c) => [c, d.judgements[c].main]))])),
    last: Object.fromEntries(FOCUS.filter((c) => last && last.judgements[c]).map((c) => [c, { main: last.judgements[c].main, aux_levels: last.judgements[c].aux_levels, aux: last.judgements[c].aux, reason_codes: last.judgements[c].reason_codes }])),
    trade_count: result.trades.length };
}
function runVector(v) {
  const cfg = VT.defaultConfig();
  const runCfg = v.rehearsal ? S.rehearsalConfig(v.inputs.histories, cfg) : { ...cfg, start_date: v.inputs.config.start_date };
  let assembled = R.assemble({ ...v.inputs, config: { start_date: runCfg.start_date } }), filled = [];
  if (v.rehearsal) [assembled, filled] = S.applyRehearsalSnapshots(assembled, fixture.qg_rows, 'REHEARSAL');
  const plan = S.capturePlan(assembled), [vNow, vRaw, vComp, vSkipped] = S.vScoresFor(plan, fixture.valuation, DV.parameters());
  const entry = assembled.ledgers.SET_A, ready = entry.state === 'READY';
  return { runCfg, assembled, filled, plan, vNow, vRaw, vComp, vSkipped, entry, engine: ready ? project(VT.runLedger(runCfg, entry.input)) : null };
}

test('fixture is marked synthetic', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
});

for (const v of fixture.vectors) {
  test('vector ' + v.name + ': JS runner + engine + signals equal Python', () => {
    const e = v.expected, out = runVector(v), ready = out.entry.state === 'READY';
    assert.equal(out.runCfg.start_date, e.run_start_date);
    if (v.rehearsal) assert.equal(S.rehearsalStart(v.inputs.histories), e.rehearsal_start);
    assert.equal(out.assembled.state, e.state);
    assert.deepEqual(out.assembled.reason_codes, e.reason_codes);
    assert.deepEqual(ready ? out.entry.input.sessions : null, e.sessions);
    assert.deepEqual(ready ? Object.fromEntries(Object.entries(out.entry.input.companies).map(([c, x]) => [c, x.sector_benchmark])) : null, e.sector_keys);
    assert.deepEqual(ready ? Object.keys(out.entry.input.benchmarks).sort() : null, e.benchmark_keys);
    assert.deepEqual(out.filled, e.qg_filled);
    assert.deepEqual(plain(S.reportSignals(out.assembled, 'SET_A', out.runCfg, v.inputs.v_store, v.inputs.v_composition)), e.signals);
    assert.equal(out.plan ? out.plan.date : null, e.capture_date);
    assert.deepEqual(out.vNow, e.v_scores);
    assert.deepEqual(out.vComp, e.v_composition);
    assert.deepEqual(out.vSkipped, e.v_skipped);
    assert.deepEqual(Object.keys(out.vRaw).sort(), Object.keys(e.v_raw).sort());
    for (const [c, x] of Object.entries(e.v_raw)) assert.ok(Math.abs(out.vRaw[c] - x) <= 1e-9, c);
    assert.deepEqual(plain(out.engine), e.engine);
  });
}

test('v1 V condition (PLAYBOOK_V1 §13-1): >= 50 weight + an anchor factor, renormalized; else V_CORE_FACTOR_MISSING, never 0; JS = Python', () => {
  assert.deepEqual(S.coreVFactors(), fixture.core_v_factors);
  assert.equal(fixture.core_v_factors.length, 7);
  for (const c of fixture.v_axis) assert.deepEqual(plain(S.vAxisDetail(c.view)), c.expected, c.name);
  const missing = fixture.v_axis.find((c) => c.name === 'core_factor_missing');
  assert.equal(S.vAxis(missing.view), missing.expected.score);assert.equal(missing.expected.weight_percent, 90);
  assert.equal(S.vLabel(S.vAxisDetail(missing.view)), 'V(부분 · 반영 가중치 90%)');assert.equal(S.vLabel(S.vAxisDetail(fixture.v_axis.find((c) => c.name === 'all_factors').view)), 'V');
  for (const name of ['anchors_missing', 'below_half_weight']) assert.equal(S.vAxis(fixture.v_axis.find((c) => c.name === name).view), null, name);
  assert.deepEqual({ ...S.V1_V_RULE, anchor_any: [...S.V1_V_RULE.anchor_any] }, { version: 'v1_v_condition/v0', status: 'V0_UNCALIBRATED', min_weight_percent: 50, anchor_any: ['fundamental_value', 'reverse_dcf'] });
  // The old behaviour (missing factor counted as 0) would have produced a lower number: it must not appear anywhere.
  const full = fixture.v_axis.find((c) => c.name === 'all_factors').expected;
  assert.equal(full.state, 'OK');
  assert.equal(full.composition, fixture.core_v_factors.join('+'));
  // The synthetic device rows have no peer / historical / sector / theme factor: every company is skipped with its reason.
  for (const v of fixture.vectors) for (const r of Object.values(v.expected.v_skipped)) assert.equal(r, 'V_CORE_FACTOR_MISSING');
});

test('V slope compares only equal compositions: unknown (V history /1) → V_COMPOSITION_CHANGED, no V_IMPROVED; progress counts /2 days only', () => {
  const v = fixture.vectors.find((x) => x.name === 'recording_v_composition_unknown'), out = runVector(v);
  const basis = S.basisRows(out.entry.input, out.runCfg), last = VT.runLedger(out.runCfg, out.entry.input).days.at(-1).judgements;
  assert.equal(basis.googl.v_slope, 'V_COMPOSITION_CHANGED');
  assert.ok(!last.googl.reason_codes.includes('V_IMPROVED'));
  assert.ok(last.googl.aux.includes('V_COMPOSITION_CHANGED'));
  assert.equal(v.expected.signals.v_progress.state, 'NOT_RECORDED');
  assert.deepEqual(S.vProgress(['2026-10-19', '2026-10-20', '2026-10-21'], { '2026-10-19': { msft: 1 }, '2026-10-20': { msft: 2 } }, 20, { '2026-10-20': { msft: 'a+b' } }).first, '2026-10-20');
});

test('rehearsal-only Q·G fill: recording mode never fills a missing day (REHEARSAL_ONLY guard)', () => {
  const v = fixture.vectors.find((x) => x.name === 'rehearsal_window_qg_fill');
  const assembled = R.assemble({ ...v.inputs, config: { start_date: '2026-11-24' } });
  for (const mode of ['RECORDING', undefined, null, 'rehearsal']) assert.throws(() => S.applyRehearsalSnapshots(assembled, fixture.qg_rows, mode), /REHEARSAL_ONLY/);
  const [filled, dates] = S.applyRehearsalSnapshots(assembled, fixture.qg_rows, 'REHEARSAL');
  assert.ok(dates.length > 0 && filled !== assembled);
  assert.equal(R.assemble({ ...v.inputs, config: { start_date: '2026-11-24' } }).ledgers.SET_A.input.snapshots['2026-11-24'], undefined, 'the runner itself never fills');
});

test('D-5 end to end: ≥273 closes + D-22 ETF → ▼ RECHECK_ABNORMAL_DROP; <273 → basis NA; missing ETF → S&P 500 labelled', () => {
  const v = fixture.vectors.find((x) => x.name === 'recording_d5_v_slope'), out = runVector(v);
  const basis = S.basisRows(out.entry.input, out.runCfg), last = VT.runLedger(out.runCfg, out.entry.input).days.at(-1).judgements;
  assert.deepEqual([basis.msft.benchmark, basis.msft.state, basis.msft.fallback], ['XLK', 'ABNORMAL', false]);
  assert.ok(basis.msft.aligned >= 273);
  assert.equal(last.msft.main, 'RISK_RECHECK');
  assert.ok(last.msft.reason_codes.includes('RECHECK_ABNORMAL_DROP'));
  assert.deepEqual([basis.googl.aligned, basis.googl.state, basis.googl.v_slope], [273, 'NORMAL', 'READY']);
  assert.ok(last.googl.reason_codes.includes('V_IMPROVED'), 'V slope active from the stored V history');
  assert.deepEqual([basis.nvda.aligned, basis.nvda.state, basis.nvda.reason, basis.nvda.v_slope], [272, 'NOT_AVAILABLE', 'HISTORY_INSUFFICIENT', 'BASIS_NOT_AVAILABLE']);
  assert.ok(last.nvda.reason_codes.includes('RECHECK_BASIS_NOT_AVAILABLE'));
  assert.deepEqual([basis.amzn.requested, basis.amzn.benchmark, basis.amzn.fallback, basis.amzn.state], ['XLY', 'SP500', true, 'NORMAL']);
  assert.equal(Object.hasOwn(out.entry.input.benchmarks, 'XLY'), false, 'rejected ETF stays absent');
  // The runner keeps the full 2y closes (not only sessions on/after the start date) and requests every D-22 ETF.
  assert.ok(Object.keys(out.entry.input.companies.msft.closes)[0] < '2026-01-01');
  const symbols = R.requiredSymbols(v.inputs);
  for (const etf of ['SMH', 'XLK', 'XLY', 'XLI', 'XLV']) assert.ok(symbols.includes(etf), etf);
  for (const row of Object.values(basis)) for (const k of Object.keys(row)) assert.ok(['requested', 'benchmark', 'fallback', 'state', 'reason', 'aligned', 'needed', 'v_slope'].includes(k), 'no price or z value: ' + k);
});

test('rehearsal: last 5 SPY sessions, cash 0 + deposits, today public Q·G fills unrecorded sessions, rule values unchanged', () => {
  const v = fixture.vectors.find((x) => x.name === 'rehearsal_window_qg_fill'), out = runVector(v), cfg = VT.defaultConfig();
  assert.equal(out.entry.input.sessions.length, 5);
  assert.deepEqual(out.entry.input.initial, { cash: 0, positions: {} });
  for (const k of Object.keys(cfg)) if (k !== 'start_date') assert.deepEqual(out.runCfg[k], cfg[k], k);
  assert.equal(VT.defaultConfig().start_date, '2026-10-19', 'the engine config itself is untouched');
  assert.deepEqual(S.rehearsalSnapshot({ nvda: { q: 70, g: null, partial: true }, x: { q: 1, g: 1 } }), { nvda: { q: 70, g: null, coverage: 'BLOCKED' } });
  assert.equal(S.rehearsalStart({ SPY: { error: 'REQUEST_INVALID' } }), null);
  assert.equal(S.rehearsalStart({}, 0), null);
});

test('V progress counts sessions since the first stored V, else stored dates', () => {
  assert.deepEqual(S.vProgress([], {}, 20), { state: 'NOT_RECORDED', first: null, last: null, recorded: 0, elapsed: 0, needed: 20 });
  assert.deepEqual(S.vProgress(['2026-10-19', '2026-10-20', '2026-10-21'], { '2026-10-19': { msft: 1 } }, 20).elapsed, 2);
  assert.deepEqual(S.vProgress([], { '2026-10-19': { msft: 1 }, '2026-10-21': { msft: 2 }, bad: { msft: 3 } }, 20).elapsed, 1);
  assert.equal(S.round2(13.4345), 13.43);
  assert.equal(S.round2(0.125), 0.13);
});

test('module itself stores, logs and sends nothing', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/virtual-trading-signals.js'), 'utf8');
  for (const word of ['setItem', 'localStorage', 'indexedDB', 'console.', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'fetch(']) assert.ok(!src.includes(word), word);
});

test('S17 model: rehearsal is labelled on screen and in the export, recording mode offers 리허설 실행, basis per company', () => {
  const DR = require('../src/investment_system/product/web_assets/daily-report.js');
  const v = fixture.vectors.find((x) => x.name === 'rehearsal_window_qg_fill'), out = runVector(v), cfg = VT.defaultConfig();
  const ledger = VT.runLedger(out.runCfg, out.entry.input), signals = S.reportSignals(out.assembled, 'SET_A', out.runCfg, {});
  const rehearsal = { start_date: out.runCfg.start_date, window: 5, qg_filled: out.filled };
  const m = DR.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-12-01', ledger, config: cfg, mode: 'REHEARSAL', signals, rehearsal,
    runner: { state: 'READY', reason_codes: [], sources: R.statusRows(out.assembled) } });
  const screen = DR.screenHtml(m, { hidden: true }), text = DR.renderTemplate(m, { hidden: true, guide: false });
  assert.ok(screen.includes('data-report-mode="REHEARSAL">리허설 · 기록 없음<'));
  assert.ok(screen.includes('data-recording-mode') && !screen.includes('data-rehearsal-run'));
  assert.ok(screen.includes('data-basis="msft" data-basis-benchmark="XLK" data-basis-state="ABNORMAL"'));
  assert.ok(screen.includes('data-basis="nvda" data-basis-benchmark="SMH" data-basis-state="NOT_AVAILABLE"'));
  assert.ok(screen.includes('S&amp;P 500 (XLY 없음 → 대체)'));
  assert.ok(text.includes('리허설 · 기록 없음: 오늘 데이터로 규칙만 돌려 본 결과이며 어떤 장부·시트에도 기록하지 않음 · ' + out.runCfg.start_date + '부터 최근 5거래일'));
  assert.ok(text.includes('기록된 Q·G가 없는 5거래일은 오늘 공개 화면 Q·G 사용'));
  assert.ok(text.includes('## ⑩ 행동요령 · 가상 매매장부 (가상 · 실제 추천 아님 · 주문 기능 없음)\n리허설 · 기록 없음 · 세트 A 가상 장부'));
  assert.ok(text.includes('nvda SMH · 기준 N/A(HISTORY_INSUFFICIENT 272/273 · 정렬된 일봉 부족) · V 기울기 미사용'));
  for (const s of [screen, text]) assert.equal((s.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length, 0);
  const rec = DR.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-15', ledger: null, config: cfg, signals: S.reportSignals(null, 'SET_A', cfg, {}) });
  const recScreen = DR.screenHtml(rec, { hidden: true }), recText = DR.renderTemplate(rec, { hidden: true, guide: false });
  assert.ok(recScreen.includes('data-report-mode="RECORDING">기록 모드<') && recScreen.includes('data-rehearsal-run>리허설 실행<'));
  assert.ok(recScreen.includes('V 기울기 NA · 중앙 V 이력 미게시 · 기기에 V 이력을 쌓지 않음(DC-31)'), 'DC-31: no device V history line');
  assert.ok(!recText.includes('리허설'), 'recording export unchanged');
  assert.ok(DR.screenHtml(rec, { hidden: true, locale: 'en-US' }).includes('>Recording mode<'));
  assert.ok(DR.screenHtml(m, { hidden: true, locale: 'en-US' }).includes('>Rehearsal · not recorded<'));
});
