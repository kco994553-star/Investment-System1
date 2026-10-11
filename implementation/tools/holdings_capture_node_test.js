'use strict';
// Holdings tab parser (capture + personal AI): JS == Python reference vectors, prompt v1 copy, ACTUAL split, RAM store. Synthetic only.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const H = require(path.join(W, 'holdings-capture.js'));
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/holdings_capture_reference_v1.json'), 'utf8'));
const DOC = fs.readFileSync(path.join(__dirname, '../docs/virtual_trading/HOLDINGS_CAPTURE_PROMPT_V1.md'), 'utf8');
function catalog() {
  const tickers = ['ASML', 'LRCX', 'KLAC', '8035', '042700', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MSFT', 'GOOGL', 'AMZN', 'RTX', 'SYK', 'ETN', 'HUBB', 'GEV', 'ROK'];
  return {schema: 'DEVICE_ACTUAL_CATALOG/1', instruments: tickers.map((ticker, i) => ({row_index: i, ticker, label: 'Synthetic ' + ticker,
    currency: ticker === '8035' ? 'JPY' : ticker === '042700' ? 'KRW' : 'USD', security_reference: {scheme: 'SYNTHETIC', value: 'ID_' + i}}))};
}
for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true); const input = structuredClone(c.input.values), before = JSON.stringify(input);
  assert.deepEqual(H.parse(input), JSON.parse(c.expected_json)); assert.equal(JSON.stringify(input), before, 'input not mutated');
});
test('vector file covers every reason code and both cost bases', () => {
  const text = JSON.stringify(vectors.cases.map(c => JSON.parse(c.expected_json)));
  for (const code of ['COLUMN_COUNT', 'AS_OF_MISSING', 'AS_OF_FORMAT', 'AS_OF_MISMATCH', 'SYMBOL_MISSING', 'SYMBOL_FORMAT', 'QUANTITY_MISSING', 'QUANTITY_FORMAT',
    'QUANTITY_NOT_POSITIVE', 'AVG_COST_FORMAT', 'COST_KRW_FORMAT', 'CURRENCY_MISSING', 'CURRENCY_FORMAT', 'CURRENCY_MISMATCH', 'CASH_AVG_COST_PRESENT', 'NAME_FORMAT',
    'COST_RANGE', 'DUPLICATE_SYMBOL', 'HEADER_MISMATCH', 'COST_KRW_DIV_QTY', 'AVG_COST_FIELD']) assert.ok(text.includes('"' + code + '"'), code);
});
test('prompt v1 in the web asset equals the fenced block of HOLDINGS_CAPTURE_PROMPT_V1.md', () => {
  const match = /## 프롬프트 \(원문 그대로\)\n\n```text\n([\s\S]*?)\n```\n/.exec(DOC);
  assert.ok(match, 'fenced prompt block'); assert.equal(match[1], H.PROMPT_TEMPLATE);
  assert.ok(DOC.startsWith('# 잔고 캡처 변환 프롬프트 v1\n')); assert.ok(DOC.includes('prompt_id: `holdings-capture-prompt/v1`'));
  assert.ok(H.PROMPT_TEMPLATE.startsWith('[' + H.PROMPT_VERSION + ']'));
  assert.ok(H.PROMPT_TEMPLATE.includes('as_of\tsymbol\tquantity\tavg_cost\tcurrency\tcost_krw\tname'));
  for (const phrase of ['모르면 빈칸', '천 단위 쉼표', 'CASH_KRW', 'KRX 6자리', '도쿄증권거래소 4자리', 'ISO 코드', '앞뒤 설명']) assert.ok(H.PROMPT_TEMPLATE.includes(phrase), phrase);
});
test('prompt fills as_of only with a valid date; seoulDate uses Asia/Seoul', () => {
  const text = H.prompt('2031-02-03'); assert.ok(text.includes('모든 줄에 2031-02-03 값을')); assert.ok(!text.includes(H.AS_OF_TOKEN));
  assert.throws(() => H.prompt('2031-02-30'), /INVALID/); assert.throws(() => H.prompt(''), /INVALID/);
  assert.equal(H.seoulDate('2031-02-03T15:30:00Z'), '2031-02-04'); assert.equal(H.seoulDate('2031-02-03T14:59:59Z'), '2031-02-03');
});
test('toActual: 19 instruments become ACTUAL rows; outside, cash and no-cost rows are kept apart', () => {
  const c = vectors.cases.find(x => x.id === 'mixed-target-and-outside'), split = H.toActual(JSON.parse(c.expected_json), catalog());
  assert.equal(split.as_of, '2031-02-03');
  assert.deepEqual(split.rows.map(r => [r.security_reference.value, r.quantity, r.average_cost, r.currency]),
    [['ID_0', '2', '950000', 'KRW'], ['ID_3', '1', '30000', 'JPY'], ['ID_4', '10', '123456.7', 'KRW']]);
  assert.deepEqual(split.in_scope.map(r => [r.ticker, r.cost_basis]), [['ASML', 'COST_KRW_DIV_QTY'], ['8035', 'AVG_COST_FIELD'], ['042700', 'COST_KRW_DIV_QTY']]);
  assert.deepEqual(split.out_of_scope.map(r => r.symbol), ['KO']); assert.deepEqual(split.cash.map(r => r.symbol), ['CASH_KRW']);
  const noCost = H.toActual(H.parse([H.HEADER.slice(), ['2031-02-03', 'NVDA', '3', '', 'USD'], ['2031-02-03', 'KO', '1', '', 'USD']]), catalog());
  assert.deepEqual(noCost.rows, []); assert.deepEqual(noCost.review, [{row: 2, symbol: 'NVDA', reason_codes: ['COST_NOT_AVAILABLE']}]);
  assert.deepEqual(noCost.out_of_scope.map(r => [r.symbol, r.cost_basis]), [['KO', 'NOT_AVAILABLE']]);
  assert.throws(() => H.toActual({schema: H.SCHEMA, state: 'HEADER_MISMATCH'}, catalog()), /INVALID/);
});
test('missing numbers are never zero: no-cost rows keep null cost and NOT_AVAILABLE basis', () => {
  const parsed = H.parse([H.HEADER.slice(), ['2031-02-03', 'SYN', '5', '', 'USD', '', '']]);
  assert.equal(parsed.positions[0].average_cost, null); assert.equal(parsed.positions[0].cost_basis, 'NOT_AVAILABLE');
  assert.ok(!JSON.stringify(parsed).includes('"0"'));
});
test('RAM store: set/get/clear per window and change event; nothing else is touched', () => {
  const events = [], view = {document: {dispatchEvent: e => events.push(e.type)}, Event: class { constructor(type) { this.type = type; } }};
  assert.equal(H.get(view), null); const parsed = H.parse([H.HEADER.slice()]);
  H.set(view, {parsed, read_at: '2031-02-03T00:00:00.000Z', outside: {}}); assert.equal(H.get(view).parsed, parsed); assert.ok(Object.isFrozen(H.get(view)));
  assert.equal(H.get({}), null); H.clear(view); assert.equal(H.get(view), null); assert.deepEqual(events, ['device-actual-changed', 'device-actual-changed']);
  assert.throws(() => H.set(view, {parsed}), /INVALID/);
});
test('exact half-up division matches the documented examples', () => {
  assert.equal(H.divide('100', '3'), '33.333333'); assert.equal(H.divide('2', '3'), '0.666667'); assert.equal(H.divide('1', '8'), '0.125');
  assert.equal(H.divide('0.0000005', '1'), '0.000001'); assert.equal(H.divide('0.0000004', '1'), '0'); assert.equal(H.divide('1', '0'), null);
});
