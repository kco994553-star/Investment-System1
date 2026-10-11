'use strict';
// D-19 judgement vocabulary and reason-code labels (JUDGEMENT_CONSISTENCY_AUDIT.md): one source (VirtualTrading), every code
// of the engine / runner / signals / V history / ledger sheet families labelled in Korean and English, no hard-coded copy
// of the level names elsewhere, and one judgement → exactly one main chip + priority-ordered auxiliary chips. Synthetic data only.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ASSETS = path.join(__dirname, '../src/investment_system/product/web_assets');
const QGV = path.join(__dirname, '../src/investment_system/qgv');
const VT = require(path.join(ASSETS, 'virtual-trading.js'));
const Runner = require(path.join(ASSETS, 'virtual-trading-runner.js'));
const Signals = require(path.join(ASSETS, 'virtual-trading-signals.js'));
const VHistory = require(path.join(ASSETS, 'virtual-trading-v-history.js'));
const Sheets = require(path.join(ASSETS, 'virtual-ledger-sheets.js'));
const R = require(path.join(ASSETS, 'daily-report.js'));
const RB = require(path.join(ASSETS, 'report-benchmarks.js'));
// ⑪⑫⑬ display codes are labelled in ReportBenchmarks (same [ko, en] shape); the scan accepts either table.
const labelled = (c) => VT.codeLabel(c) || RB.codeLabel(c);

const D19 = '■차단 > ▼위험재검토 > ▼비중축소검토 > ▲비중확대검토 > ●추가검토 > ●보유맥락 > ●관찰';
const FAMILIES = {
  ...Object.fromEntries(Object.entries(VT.CODES).map(([k, v]) => ['engine.' + k, v])),
  runner: Runner.CODES, signals: Signals.CODES, v_history: VHistory.CODES, ledger_sheets: Sheets.CODES,
};
// Upper-case literals in the family sources that are NOT reason codes: each is an enum shown through its own wording.
const NOT_CODES = {
  levels: VT.LEVELS,
  tickers_and_benchmarks: ['AMD', 'AMZN', 'ASML', 'AVGO', 'ETN', 'GEV', 'GOOGL', 'HUBB', 'INTC', 'KLAC', 'LRCX', 'MSFT', 'NVDA', 'QCOM', 'ROK', 'RTX', 'SYK',
    'SPY', 'SP500', 'SMH', 'VUG', 'QUAL', 'XLB', 'XLC', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLRE', 'XLU', 'XLV', 'XLY', 'SEMIS_THEME_SMH_ELSE_XLI'],
  currencies: ['KRW', 'USD', 'JPY'],
  ledger_and_report_kinds: ['SET_A', 'SET_B', 'SHADOW', 'MOCK', 'REAL', 'COMPARE', 'TARGET', 'TARGET_V0', 'USER_TARGET'],
  sides_rows_events_sources: ['BUY', 'SELL', 'INITIAL', 'EXECUTED', 'CANCELLED', 'JUDGEMENT', 'ORDER', 'SUMMARY', 'LEDGER_START', 'LEDGER_CLOSE', 'RECORD', 'RESYNC', 'MAILBOX', 'PASTE', 'NEW'],
  states: ['READY', 'PARTIAL', 'BLOCKED', 'NOT_AVAILABLE', 'NOT_STARTED', 'STARTED', 'LOADING', 'LOADED', 'ERROR', 'LIVE', 'STALE', 'ABNORMAL', 'NORMAL', 'COMPLETE',
    'IN_PROGRESS', 'UNKNOWN', 'EMPTY', 'UNAVAILABLE', 'RECORDED', 'NOT_RECORDED', 'COLLECTING', 'RECORDING', 'REHEARSAL'],
  report_periods_verdicts_series: ['SINCE_START', 'ABOVE', 'BELOW', 'EQUAL', 'LEDGER', 'INDEX'],
  config_values: ['NEXT_SESSION_CLOSE', 'INACTIVE_MAPPING_PENDING', 'PROVISIONAL_UNCALIBRATED', 'RAM_ONLY_DEVICE', 'SECTOR_ETF_CONFIRMED', 'SP500_SUBSTITUTE_D22_PENDING',
    'TYPE_WEIGHTED_QGV_ELSE_QG'],
};
const notCode = new Set(Object.values(NOT_CODES).flat());
const read = (f) => fs.readFileSync(f, 'utf8');
const literals = (src) => [...src.matchAll(/['"]([A-Z][A-Z0-9_]{2,})['"]/g)].map((m) => m[1]);

test('levels: order, symbols, Korean/English names and tones come from one table and match D-19', () => {
  assert.equal(VT.priorityText('ko-KR'), D19);
  assert.deepEqual([...VT.LEVELS], ['BLOCK', 'RISK_RECHECK', 'REDUCE_REVIEW', 'INCREASE_REVIEW', 'ADDITIONAL_REVIEW', 'HOLDING_CONTEXT', 'OBSERVE']);
  for (const table of [VT.SYMBOLS, VT.LABELS.ko, VT.LABELS.en, VT.TONES]) assert.deepEqual(Object.keys(table), [...VT.LEVELS]);
  assert.ok(Object.isFrozen(VT.LEVELS) && Object.isFrozen(VT.SYMBOLS) && Object.isFrozen(VT.LABELS.ko));
  assert.equal(VT.label('RISK_RECHECK', 'ko-KR'), '▼위험재검토');
  assert.equal(VT.label('RISK_RECHECK', 'en-US'), '▼Risk re-check');
  assert.equal(VT.DISCLAIMER.ko, '가상 · 실제 추천 아님 · 주문 기능 없음');
  for (const l of VT.LEVELS) assert.ok(VT.LABELS.en[l] && VT.LABELS.ko[l] && VT.TONES[l], l);
});

test('every code in the engine, runner, signals, V history and ledger sheet code lists has a Korean and an English label', () => {
  const missing = [];
  for (const [family, codes] of Object.entries(FAMILIES)) {
    assert.ok(Array.isArray(codes) && codes.length > 0, family);
    for (const c of codes) {
      const ko = VT.codeLabel(c, 'ko-KR'), en = VT.codeLabel(c, 'en-US');
      if (!ko || !en || ko === c || en === c || !/[가-힣]/.test(ko)) missing.push(family + ':' + c);
    }
  }
  assert.deepEqual(missing, []);
  for (const c of [...VT.CODES.execution]) assert.ok(c.startsWith('EXEC_') || ['NO_POSITION', 'CASH_INSUFFICIENT'].includes(c));
  // Every label entry is a [ko, en] pair; English carries no Hangul.
  for (const [c, pair] of Object.entries(VT.CODE_LABELS)) assert.ok(Array.isArray(pair) && pair.length === 2 && !/[가-힣]/.test(pair[1]), c);
});

test('source scan: every upper-case code literal in the JS modules, the report glue and the Python ports is labelled or a listed enum', () => {
  const files = ['virtual-trading.js', 'virtual-trading-runner.js', 'virtual-trading-signals.js', 'virtual-trading-v-history.js', 'virtual-ledger-sheets.js', 'daily-report.js']
    .map((f) => path.join(ASSETS, f))
    .concat([path.join(ASSETS, 'report-benchmarks.js')])
    .concat(['virtual_trading.py', 'virtual_trading_inputs.py', 'virtual_trading_signals.py', 'virtual_ledger_sheets.py', 'report_benchmarks.py'].map((f) => path.join(QGV, f)));
  const app = read(path.join(ASSETS, 'app.js'));
  const glue = app.slice(app.indexOf('async function paintReport'), app.indexOf('function showUnavailable'));
  assert.ok(glue.length > 1000, 'report glue found');
  const unlabelled = new Set();
  for (const src of files.map(read).concat([glue])) for (const c of literals(src)) if (!labelled(c) && !notCode.has(c)) unlabelled.add(c);
  assert.deepEqual([...unlabelled].sort(), []);
  // An enum listed as "not a code" must not also carry a code label (no double meaning).
  assert.deepEqual([...notCode].filter((c) => labelled(c) && !VT.LEVELS.includes(c)), []);
  // ReportBenchmarks labels: [ko, en] pairs, Korean in ko, no Hangul in en.
  for (const [c, pair] of Object.entries(RB.CODE_LABELS)) assert.ok(pair.length === 2 && /[가-힣]/.test(pair[0]) && !/[가-힣]/.test(pair[1]), c);
});

test('deliberate fallback: an unknown code (e.g. a Worker error passed through) is shown verbatim and marked, never dropped', () => {
  assert.equal(VT.codeLabel('UPSTREAM_TEAPOT'), null);
  assert.equal(VT.codeText('UPSTREAM_TEAPOT'), 'UPSTREAM_TEAPOT');
  assert.equal(VT.codeText('EXEC_FX_MISSING'), '체결일 환율 결측으로 가상 주문 취소 (EXEC_FX_MISSING)');
  const html = VT.reasonsHtml(['UPSTREAM_TEAPOT', 'QG_DECLINE']);
  assert.ok(html.includes('data-reason-code="UPSTREAM_TEAPOT" data-unlabeled>UPSTREAM_TEAPOT<'));
  assert.ok(html.includes('data-reason-code="QG_DECLINE">Q·G 평균이'));
  assert.equal(VT.codesText(['UPSTREAM_TEAPOT', 'NO_ACTUAL']), 'UPSTREAM_TEAPOT, 기기 실제 보유 없음 (NO_ACTUAL)');
});

test('no hard-coded copy of the level vocabulary outside VirtualTrading', () => {
  const names = VT.LEVELS.flatMap((l) => [VT.label(l, 'ko-KR'), VT.SYMBOLS[l] + ' ' + VT.LABELS.ko[l]]);
  const offenders = [];
  for (const f of fs.readdirSync(ASSETS).filter((x) => /\.(js|html|css)$/.test(x) && x !== 'virtual-trading.js')) {
    const src = read(path.join(ASSETS, f));
    for (const n of names) if (src.includes(n)) offenders.push(f + ': ' + n);
    if (/LEVEL_KO|REASON_KO/.test(src)) offenders.push(f + ': LEVEL_KO/REASON_KO');
  }
  assert.deepEqual(offenders, []);
  assert.equal(R.LEVEL_KO, undefined);
  assert.equal(R.REASON_KO, undefined);
  assert.ok(R.GUIDE_A.includes('   ' + VT.priorityText('ko-KR', ' / ')));
});

test('one main chip, auxiliary chips by priority, never the main level twice (every main × aux-level subset × signal)', () => {
  const L = VT.LEVELS, signals = Object.keys(VT.SIGNALS);
  let cases = 0;
  for (const main of L) for (let mask = 0; mask < 1 << L.length; mask++) for (let s = 0; s < 1 << signals.length; s++) {
    const aux = L.filter((_, i) => mask & (1 << i)).reverse(), auxCodes = signals.filter((_, i) => s & (1 << i)).concat(['EARNINGS_WINDOW']);
    const j = { main, aux_levels: aux, aux: auxCodes, reason_codes: [] };
    const t = VT.judgementTokens(j, 'ko-KR');
    cases++;
    assert.equal(t[0].kind, 'main');
    assert.equal(t[0].level, main);
    assert.equal(t.filter((x) => x.kind === 'main').length, 1);
    const levels = t.map((x) => x.level);
    assert.equal(new Set(levels).size, levels.length, 'a level shows once: ' + JSON.stringify(j));
    const rest = levels.slice(1).map((x) => L.indexOf(x));
    assert.deepEqual(rest, [...rest].sort((a, b) => a - b), 'auxiliary chips in priority order');
    assert.equal(VT.judgementText(j, 'ko-KR'), t.map((x) => x.text).join(' '));
    const html = VT.judgementHtml(j, { locale: 'ko-KR' });
    assert.equal((html.match(/data-chip="main"/g) || []).length, 1);
    for (const x of t) assert.ok(html.includes('data-level="' + x.level + '" data-tone="' + VT.TONES[x.level] + '"'));
  }
  assert.equal(cases, 7 * 128 * 4);
  assert.equal(VT.judgementText({ main: 'RISK_RECHECK', aux_levels: ['ADDITIONAL_REVIEW'], aux: ['INCREASE_CANDIDATE', 'OVERWEIGHT', 'EARNINGS_WINDOW'] }),
    '▼위험재검토 +▼비중 +▲확대 후보 +●추가검토');
  assert.deepEqual(VT.judgementTokens({ main: 'NOT_A_LEVEL' }), []);
  assert.deepEqual(VT.reasonCodes({ reason_codes: ['QG_DECLINE', 'OVERWEIGHT'], aux: ['OVERWEIGHT', 'EARNINGS_WINDOW'] }), ['QG_DECLINE', 'OVERWEIGHT', 'EARNINGS_WINDOW']);
});

test('S17 screen and template v1 show the same main + auxiliary text for each company and label every code they list', () => {
  const fixture = JSON.parse(read(path.join(__dirname, '../tests/fixtures/virtual_trading_reference_v1.json')));
  for (const v of fixture.vectors.filter((x) => x.expected.state === 'OK')) {
    const ledger = VT.runLedger(v.config, v.ledger), last = ledger.days[ledger.days.length - 1];
    const m = R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: last.date, ledger, config: v.config });
    const text = R.renderTemplate(m, { hidden: true, guide: false }), html = R.screenHtml(m, { hidden: true });
    for (const [cid, j] of Object.entries(last.judgements)) {
      assert.ok(text.includes('| ' + cid + ' | ') && text.includes(' | ' + VT.judgementText(j, 'ko-KR') + ' | '), v.name + ' ' + cid + ' template');
      assert.ok(html.includes(VT.judgementHtml(j, { locale: 'ko-KR' })), v.name + ' ' + cid + ' screen');
    }
    const dictionary = text.slice(text.indexOf('## 사유 코드 사전'));
    for (const c of new Set(Object.values(last.judgements).flatMap(VT.reasonCodes))) assert.ok(dictionary.includes('- ' + c + ': ' + VT.codeLabel(c)), v.name + ' ' + c);
    assert.ok(text.includes('## ⑩ 행동요령 · 가상 매매장부 (' + VT.DISCLAIMER.ko + ')'));
    assert.ok(text.includes('판단: ' + VT.DISCLAIMER.ko));
  }
});
