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
  const cfg = { ...VT.defaultConfig(), start_date: null };
  const ledger = VT.runLedger(cfg, { id: 'a', kind: 'SET_A', sessions: [], target_weights: null, companies: {} });
  const m = R.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-12', ledger, config: cfg });
  const text = R.renderTemplate(m, { hidden: true, guide: false });
  assert.ok(text.includes('가상매매 시작일 미정'));
  assert.ok(text.includes('가상매매 시작일: 미정'));
  assert.ok(R.screenHtml(m, {}).includes('data-report-not-started'));
  const decided = R.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-12', ledger: VT.runLedger(VT.defaultConfig(), { id: 'a', kind: 'SET_A', sessions: [], target_weights: null, companies: {} }), config: VT.defaultConfig() });
  const t2 = R.renderTemplate(decided, { hidden: true, guide: false });
  assert.ok(t2.includes('가상매매 시작일 2026-10-19 전 · 기록 없음'));
  assert.ok(t2.includes('가상매매 시작일: 2026-10-19'));
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

test('mailbox writes only to the report tabs; Inbox sha256 is the hash of the written text', async () => {
  const crypto = require('node:crypto');
  const calls = [];
  const session = {
    sheetTitles: async () => ['Quotes'],
    addTabs: async (id, t) => calls.push(['add', t]),
    appendRows: async (id, range, rows) => calls.push(['append', range, rows[0]]),
    fetchValues: async () => ({ values: [['sha256', 'model', 'created_at', 'answer'], ['x', 'm', 't', 'other'], ['h1', 'GPT', '2026-10-12T00:00Z', 'answer one']] }),
  };
  const text = 'TEMPLATE TEXT 숨김';
  const sha = await R.postInbox(session, 'id', { report_date: '2026-10-12', kind: 'MOCK', template: text, data_sha256: 'd1', now: 'N' }, crypto.webcrypto);
  assert.deepEqual(calls[0], ['add', ['ReportInbox', 'ReportOutbox']]);
  assert.ok(calls.every((c) => c[0] === 'add' || /^'Report(Inbox|Outbox)'!A1$/.test(c[1])));
  const row = calls[calls.length - 1][2];
  assert.equal(row.length, 8);
  assert.equal(row[4], crypto.createHash('sha256').update(text, 'utf8').digest('hex'));
  assert.equal(row[4], sha);
  assert.equal(row[5], 'd1');
  assert.equal(row[7], text);
  assert.deepEqual(await R.readOutbox(session, 'id', 'h1'), { model: 'GPT', created_at: '2026-10-12T00:00Z', answer: 'answer one' });
  assert.equal(await R.readOutbox(session, 'id', 'nope'), null);
});

test('module performs no network I/O by itself', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/daily-report.js'), 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'indexedDB']) assert.ok(!src.includes(word), word);
});

// Directive §9 (2026-10-18): review before save. Pasting stores nothing; the review is pure; saving writes only AI_KEY.
test('AI answer review before save: pure parse and checks, explicit save writes only the answer store', () => {
  const { model } = startedModel();
  const t = R.renderTemplate(model, { hidden: true, guide: false });
  const good = t.replace('한 줄 요약: 【AI】', '한 줄 요약: 시장 대비 약세') + '\n' + R.CHECK_LINES.join('\n');
  const writes = [], base = { 'investment.web.v1.personal': '{"keep":1}', 'investment.web.v1.playbook': '{"theses":{}}' };
  const store = new Map(Object.entries(base)), storage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => { writes.push(k); store.set(k, String(v)); } };
  const r = R.reviewAnswer(good, t);
  assert.equal(writes.length, 0, 'review never writes');
  assert.equal(r.format_ok, true);
  assert.deepEqual(r.foreign_numbers, []);
  assert.equal(r.sections.length, R.SECTION_HEADS.length);
  assert.deepEqual(r.missing_sections, []);
  assert.ok(r.summary_line.startsWith('시장 대비 약세'));
  assert.deepEqual(r.effects, { stores: R.AI_KEY, holdings: false, official_judgements: false, ledgers: false, sheets: false });
  const bad = R.reviewAnswer('## 요약\n지금 사야 합니다. 목표가 312.5', t);
  assert.equal(bad.format_ok, false);
  assert.ok(bad.foreign_numbers.includes('312.5'));
  assert.deepEqual(bad.banned_phrases, ['지금 사야']);
  assert.ok(bad.missing_sections.includes('## ⑬'));
  const html = R.reviewHtml(bad);
  for (const id of ['format', 'date', 'numbers', 'sections', 'phrases']) assert.ok(html.includes('data-review-check="' + id + '"'), id);
  assert.ok(html.includes('아직 보관 전') && html.includes('data-review-cancel') && html.includes('data-review-effects'));
  assert.ok(R.saveAnswer(storage, 'k', { answer: good, saved_at: '2026-10-18T00:00:00Z', source: 'PASTE' }));
  assert.deepEqual(writes, [R.AI_KEY]);
  for (const [k, v] of Object.entries(base)) assert.equal(store.get(k), v, k + ' unchanged');
  // The screen asks for a review first: the save button is rendered disabled.
  const screen = R.screenHtml(model, { hidden: true });
  assert.ok(/<button type="button" data-save-answer disabled/.test(screen));
  assert.ok(screen.includes('data-review-answer') && screen.includes('data-answer-review'));
});

const SECTIONS_TEXT = ['대상:', '기간:', '버전:', '가용 자료', '누락 자료', '출처:', '계산 가능 범위:'];
test('보고 불가: not started mock report → reason, minimum missing inputs and a copyable prompt without numbers', () => {
  const m = R.buildModel({ kind: 'MOCK', tab: 'SET_A', reportDate: '2026-10-18', config: VT.defaultConfig(), ledger: { state: 'NOT_STARTED', reason_codes: ['BEFORE_START_DATE'] }, runner: { state: 'NOT_STARTED', reason_codes: ['BEFORE_START_DATE'], sources: [] } });
  const u = R.unavailability(m);
  assert.equal(u.state, 'UNAVAILABLE');
  assert.ok(u.sentence.includes('가상매매 시작일 전(BEFORE_START_DATE)'));
  assert.deepEqual(u.missing.map((x) => x.key), ['FIRST_SESSION', 'SIC', 'CONTRIB', 'TA', 'MACRO', 'DRIVER', 'RISK']);
  assert.equal(u.areas.find((a) => a.id === '8').state, 'AI');
  const prompt = R.unavailablePrompt(m);
  for (const s of SECTIONS_TEXT) assert.ok(prompt.includes(s), s);
  assert.ok(prompt.includes('자료가 없는 수익률·손익·평가액·기여도·적중률·점수·가격을 추정하거나 만들지 마라'));
  assert.ok(prompt.includes('보고일 2026-10-18') && prompt.includes('가상매매 시작일 2026-10-19') && prompt.includes(R.TEMPLATE_VERSION));
  assert.ok(!/%|원\b|\d+만원/.test(prompt), 'no return or amount');
  const screen = R.screenHtml(m, { hidden: true });
  assert.ok(screen.includes('data-report-unavailable data-unavailable-state="UNAVAILABLE"'));
  assert.ok(screen.indexOf('data-report-unavailable') < screen.indexOf('data-report-section="3"'), 'card comes before the sections');
  assert.ok(screen.includes('data-unavailable-copy="all"') && screen.includes('data-unavailable-prompt readonly'));
  // Export is unchanged: template v1 has no 보고 불가 block.
  assert.ok(!R.renderTemplate(m, { hidden: true, guide: false }).includes('보고 불가'));
});

test('보고 불가: real report lists holdings, sign-in and device prices date; unknown codes stay verbatim', () => {
  const runner = { state: 'NOT_AVAILABLE', reason_codes: ['AUTH_REQUIRED'], sources: [{ symbol: 'AAA', state: 'NOT_AVAILABLE', code: 'HISTORY_UNAVAILABLE' }, { symbol: 'BBB', state: 'NOT_AVAILABLE', code: 'WORKER_E42' }] };
  const none = R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-20', baseDates: { NYSE: '2026-10-19' }, config: VT.defaultConfig(), ledger: null, ram: { state: 'NOT_AVAILABLE', reason: 'NO_ACTUAL', rows: [] }, runner });
  const u = R.unavailability(none);
  assert.equal(u.state, 'UNAVAILABLE');
  const keys = u.missing.map((x) => x.key);
  for (const k of ['HOLDINGS', 'SIGN_IN', 'PRICES', 'LEDGER', 'CODE:WORKER_E42']) assert.ok(keys.includes(k), k);
  const prices = u.missing.find((x) => x.key === 'PRICES').text;
  assert.ok(prices.includes('NYSE 2026-10-19') && prices.includes('AAA'), prices);
  assert.equal(u.missing.find((x) => x.key === 'CODE:WORKER_E42').kind, 'CHECK');
  const area = R.unavailablePrompt(none, { area: '3' });
  assert.ok(area.includes('영역 ③ 전 종목 장부') && area.includes('NO_ACTUAL') && !area.includes('SIGN_IN'));
  // With ACTUAL weights but no shadow ledger the report is partial: ③ and ⑤ are computable.
  const held = R.buildModel({ kind: 'REAL', tab: 'REAL', reportDate: '2026-10-20', config: VT.defaultConfig(), ledger: null, ram: { state: 'OK', rows: [{ ticker: 'AAA', weight: 0.6 }, { ticker: 'BBB', weight: 0.4 }] }, qg: { AAA: { total: 61.2, factors_available: 9, factors_total: 10 } }, runner });
  const p = R.unavailability(held);
  assert.equal(p.state, 'PARTIAL');
  assert.equal(p.areas.find((a) => a.id === '3').state, 'OK');
  assert.equal(p.areas.find((a) => a.id === '5').state, 'PARTIAL');
  assert.ok(R.unavailablePrompt(held).includes('QGV v2 총점 1/2종목'));
});

test('보고 불가: a started report is partial (unconnected areas only) and its card leaks no amount', () => {
  const { model, ledger } = startedModel();
  const u = R.unavailability(model);
  assert.equal(u.state, 'PARTIAL');
  for (const id of ['2', '4', '6', '7', '9']) assert.equal(u.areas.find((a) => a.id === id).state, 'UNAVAILABLE', id);
  for (const id of ['summary', '1', '3', '10']) assert.equal(u.areas.find((a) => a.id === id).state, 'OK', id);
  assert.ok(u.missing.every((x) => x.kind === 'SYSTEM'), JSON.stringify(u.missing));
  assert.ok(u.missing.some((x) => x.key === 'BENCH'), 'no ⑪⑫⑬ inputs in this fixture');
  const card = R.unavailableCard(model), prompt = R.unavailablePrompt(model);
  for (const text of sensitive(ledger)) { assert.ok(!card.includes(text), text); assert.ok(!prompt.includes(text), text); }
  const screen = R.screenHtml(model, { hidden: false });
  assert.ok(screen.indexOf('data-report-section="rest"') < screen.indexOf('data-report-unavailable'), 'partial card follows the section cards');
  assert.ok(screen.indexOf('data-report-unavailable') < screen.indexOf('data-report-section="11"'));
});

test('an answer pasted with the guide is checked without it (rule numbers, quoted words and check lines ignored)', () => {
  const { model } = startedModel();
  const t = R.renderTemplate(model, { hidden: true, guide: false }), withGuide = R.renderTemplate(model, { hidden: true, guide: true });
  const r = R.reviewAnswer(withGuide, t);
  assert.deepEqual(r.banned_phrases, [], 'the guide quotes the banned words');
  assert.deepEqual(r.foreign_numbers, [], 'the guide rule numbers are not foreign numbers');
  assert.equal(r.format_ok, false, 'the guide check lines do not satisfy the answer check');
  assert.deepEqual(R.checkAnswer(withGuide, t).foreign_numbers, r.foreign_numbers, 'review and post-save check agree');
});
