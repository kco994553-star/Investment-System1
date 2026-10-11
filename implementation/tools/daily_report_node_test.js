'use strict';
// S17 daily report: amount hiding (one function for screen and export), template v1 shape, AI answer checks. Synthetic data only.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../src/investment_system/product/web_assets/daily-report.js');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_reference_v1.json'), 'utf8'));

function startedModel(kind = 'MOCK') {
  const v = fixture.vectors.find((x) => x.name === 'shadow_rules');
  const ledger = VT.runLedger(v.config, v.ledger);
  const model = R.buildModel({ kind, tab: kind === 'REAL' ? 'REAL' : 'SET_A', reportDate: '2026-07-24', baseDates: { US: '2026-07-24' }, ledger, config: v.config, qg: { aaa: { q: 61.2, g: 57.4 } } });
  model.hits = VT.evaluateHits(v.config, v.ledger, ledger.trades);
  return { model, ledger };
}
// Every amount, quantity and average price that the model can show, in every format the module can print.
function sensitive(ledger) {
  const values = [];
  const s = ledger.summary;
  for (const k of ['total_value', 'initial_value', 'deposits', 'cash', 'realized_pnl', 'unrealized_pnl']) values.push(s[k]);
  for (const d of ledger.days) values.push(d.total_value, d.cash, d.positions_value);
  for (const t of ledger.trades) values.push(t.amount, t.quantity, t.price * t.fx, t.price);
  return values.filter((v) => typeof v === 'number' && Math.abs(v) >= 1).flatMap((v) => [R.formatKrw(v), R.quantity(v, { hidden: false })]);
}

test('money/quantity hide amounts in both modes and show them only when asked', () => {
  assert.equal(R.money(108300000, { hidden: true }), '●●●만원');
  assert.equal(R.money(108300000, { hidden: true, mode: 'export' }), '[숨김]');
  assert.equal(R.money(650000, { hidden: true, mode: 'export', limit: 1000000 }), '한도 대비 65%');
  assert.equal(R.money(108300000, { hidden: false }), '1억 830만원');
  assert.equal(R.money(650000, { hidden: false }), '65만원');
  assert.equal(R.quantity(12.5, { hidden: true }), '●●●');
  assert.equal(R.money(null), 'N/A');
});

test('hidden screen and hidden export contain zero amounts, quantities or average prices', () => {
  for (const kind of ['MOCK', 'REAL']) {
    const { model, ledger } = startedModel(kind);
    const outputs = [R.screenHtml(model, { hidden: true }), R.renderTemplate(model, { hidden: true, guide: true }), R.renderTemplate(model, { hidden: true, guide: false })];
    for (const out of outputs) {
      for (const text of sensitive(ledger)) assert.ok(!out.includes(text), kind + ' leaked ' + text);
      assert.equal((out.match(/\d[\d,]*\s*(?:원|만원|억)/g) || []).length, 0, kind + ' has a won amount');
    }
    const shown = R.renderTemplate(model, { hidden: false, guide: false });
    assert.ok(shown.includes(R.formatKrw(ledger.summary.total_value)));
  }
});

test('template v1 keeps section order, AI cells, guide toggle and kind line', () => {
  const { model } = startedModel();
  const withGuide = R.renderTemplate(model, { hidden: true, guide: true }), without = R.renderTemplate(model, { hidden: true, guide: false });
  assert.ok(withGuide.startsWith('[Investment-System1 · AI 해석 지침 v1 · 템플릿 v1]'));
  assert.ok(without.startsWith(R.HEADER_B));
  assert.ok(without.includes(R.KIND_LINE.MOCK));
  const order = ['## 요약', '## ①', '## ②', '## ③', '## ④', '## ⑤', '## ⑥', '## ⑦', '## ⑧', '## ⑨', '## ⑩', '## ⑪', '## ⑫', '## ⑬', '## 최종 투자판단', '## 각주'];
  let at = -1;
  for (const h of order) { const i = without.indexOf(h); assert.ok(i > at, h); at = i; }
  assert.ok((without.match(/【AI】/g) || []).length >= 10);
  assert.equal(R.renderTemplate(model, { hidden: true, guide: false }), without, 'deterministic');
  // The guide quotes banned phrases as examples; the data part must not contain them, and neither part carries sheet IDs or tokens.
  for (const word of ['지금 사야', '매수하세요', '매도하세요']) assert.ok(!without.includes(word), word);
  for (const word of ['spreadsheet', 'token', 'docs.google.com', '@']) assert.ok(!withGuide.includes(word), word);
});

test('not started: no ledger rows, rule sentence says so', () => {
  const ledger = VT.runLedger(VT.defaultConfig(), { id: 'a', kind: 'SET_A', sessions: [], target_weights: null, companies: {} });
  const m = R.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-12', ledger, config: VT.defaultConfig() });
  const text = R.renderTemplate(m, { hidden: true, guide: false });
  assert.ok(text.includes('가상매매 시작일 미정'));
  assert.ok(text.includes('가상매매 시작일: 미정'));
  assert.ok(R.screenHtml(m, {}).includes('data-report-not-started'));
});

test('AI answer check: foreign numbers counted, missing check lines flagged', () => {
  const { model } = startedModel();
  const t = R.renderTemplate(model, { hidden: true, guide: false });
  const good = t.replace('한 줄 요약: 【AI】', '한 줄 요약: 시장 대비 약세') + '\n' + R.CHECK_LINES.join('\n');
  const r1 = R.checkAnswer(good, t);
  assert.equal(r1.format_ok, true);
  assert.deepEqual(r1.foreign_numbers, []);
  const r2 = R.checkAnswer(t + '\n목표가 312.5달러, 확률 70%', t);
  assert.equal(r2.format_ok, false);
  assert.ok(r2.foreign_numbers.includes('312.5') && r2.foreign_numbers.includes('70'));
});

test('answers are stored per template hash on this device only, newest kept', async () => {
  const store = new Map(), storage = { getItem: (k) => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)) };
  const key = await R.hash('abc', require('node:crypto').webcrypto);
  assert.equal(key, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  for (let i = 0; i < 35; i++) R.saveAnswer(storage, 'k' + i, { answer: 'a' + i, saved_at: '2026-10-' + String(10 + (i % 20)).padStart(2, '0') + 'T00:00:' + String(i).padStart(2, '0') + 'Z', source: 'PASTE' });
  assert.equal(Object.keys(R.answers(storage)).length, 30);
  assert.equal(R.hiddenSetting(storage), true);
  R.hiddenSetting(storage, false);
  assert.equal(R.hiddenSetting(storage), false);
  assert.equal(R.hiddenSetting({ getItem() { throw new Error('blocked'); } }), true);
});

test('mailbox writes only to the report tabs and matches by hash', async () => {
  const calls = [];
  const session = {
    sheetTitles: async () => ['Quotes'],
    addTabs: async (id, t) => calls.push(['add', t]),
    appendRows: async (id, range, rows) => calls.push(['append', range, rows[0].length]),
    fetchValues: async () => ({ values: [['sha256', 'model', 'created_at', 'answer'], ['x', 'm', 't', 'other'], ['h1', 'GPT', '2026-10-12T00:00Z', 'answer one']] }),
  };
  await R.postInbox(session, 'id', { report_date: '2026-10-12', kind: 'MOCK', sha256: 'h1', template: 'T', now: 'N' });
  assert.deepEqual(calls[0], ['add', ['ReportInbox', 'ReportOutbox']]);
  assert.ok(calls.every((c) => c[0] === 'add' || /^'Report(Inbox|Outbox)'!A1$/.test(c[1])));
  assert.deepEqual(await R.readOutbox(session, 'id', 'h1'), { model: 'GPT', created_at: '2026-10-12T00:00Z', answer: 'answer one' });
  assert.equal(await R.readOutbox(session, 'id', 'nope'), null);
});

test('module performs no network I/O by itself', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/daily-report.js'), 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'indexedDB']) assert.ok(!src.includes(word), word);
});
