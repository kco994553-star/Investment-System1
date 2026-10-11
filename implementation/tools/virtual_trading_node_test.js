'use strict';
// Virtual trading v1: the JS port must reproduce the Python reference vectors exactly (synthetic inputs only).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_reference_v1.json'), 'utf8'));
const config = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/investment_system/qgv/virtual_trading_v1_provisional.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));

test('embedded config equals the provisional JSON', () => {
  assert.deepEqual(plain(VT.CONFIG), config);
  assert.equal(VT.CONFIG.start_date, '2026-10-19');
});

for (const v of fixture.vectors) {
  test('vector ' + v.name, () => {
    const result = VT.runLedger(v.config, v.ledger);
    assert.deepEqual(plain(result), v.expected);
    if (v.expected_hits !== null) assert.deepEqual(plain(VT.evaluateHits(v.config, v.ledger, result.trades)), v.expected_hits);
  });
}

test('no start date means no ledger records', () => {
  const v = fixture.vectors.find((x) => x.name === 'set_a_deposit_buys');
  const r = VT.runLedger({ ...VT.defaultConfig(), start_date: null }, v.ledger);
  assert.equal(r.state, 'NOT_STARTED');
  assert.deepEqual(r.trades, []);
  assert.deepEqual(r.days, []);
});

test('limits: buy and sell totals per day never exceed 100만원 each', () => {
  for (const v of fixture.vectors.filter((x) => x.expected.state === 'OK')) {
    for (const d of v.expected.days) {
      const sum = (side) => d.orders.filter((o) => o.side === side).reduce((a, o) => a + o.amount, 0);
      assert.ok(sum('BUY') <= v.config.buy_limit && sum('SELL') <= v.config.sell_limit, v.name + ' ' + d.date);
    }
  }
});

test('module performs no I/O', () => {
  const src = fs.readFileSync(require.resolve('../src/investment_system/product/web_assets/virtual-trading.js'), 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'localStorage', 'indexedDB', 'sendBeacon', 'WebSocket']) assert.ok(!src.includes(word), word);
  assert.equal(VT.label('INCREASE_REVIEW', 'ko-KR'), '▲ 비중확대검토');
});
