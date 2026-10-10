/* Synthetic observations exist only in memory. Output contains test labels and counts. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const corePath = path.join(__dirname, '../src/investment_system/product/web_assets/google-sheet-core.js');
const core = fs.existsSync(corePath) ? require(corePath) : {};
const market = require('../src/investment_system/product/web_assets/device-market.js');
const now = '2030-01-09T12:00:00.000Z';
const identities = [
  ['NASDAQ:ASML', 'USN070592100'], ['NASDAQ:LRCX', 'US5128073062'], ['NASDAQ:KLAC', 'US4824801009'],
  ['NASDAQ:NVDA', 'US67066G1040'], ['NASDAQ:AMD', 'US0079031078'], ['NASDAQ:AVGO', 'US11135F1012'],
  ['NASDAQ:QCOM', 'US7475251036'], ['NASDAQ:INTC', 'US4581401001'], ['NASDAQ:MSFT', 'US5949181045'],
  ['NASDAQ:GOOGL', 'US02079K3059'], ['NASDAQ:AMZN', 'US0231351067'], ['NYSE:RTX', 'US75513E1010'],
  ['NYSE:SYK', 'US8636671013'], ['NYSE:ETN', 'IE00B8KQN827'], ['NYSE:HUBB', 'US4435106079'],
  ['NYSE:GEV', 'US36828A1016'], ['NYSE:ROK', 'US7739031091'], ['TYO:8035', null], ['KRX:042700', null]
];
function catalog() {
  return {schema: 'DEVICE_ACTUAL_CATALOG/1', target_root_version: 'v0', target_root_sha256: 'a'.repeat(64),
    identity_map_version: 'public-map', identity_map_sha256: 'b'.repeat(64), total_units: 10000,
    themes: [{theme_id: 'public', label: 'Public theme', target_units: 10000}],
    instruments: identities.map(([code, isin], index) => ({row_index: index, label: 'Public instrument ' + index,
      ticker: code.split(':')[1], theme_id: 'public', target_units: index === 18 ? 1000 : 500,
      security_reference: isin ? {scheme: 'ISIN', value: isin}
        : {scheme: 'EXCHANGE_CODE', exchange: index === 17 ? 'TSE' : 'KRX', code: code.split(':')[1]},
      currency: index === 17 ? 'JPY' : index === 18 ? 'KRW' : 'USD'}))};
}
function ready() { for (const name of ['parseValues', 'parsePaste', 'apply']) assert.equal(typeof core[name], 'function'); }
function serial(year, month, day, hour, minute = 0, second = 0) {
  return (Date.UTC(year, month - 1, day, hour, minute, second) - Date.UTC(1899, 11, 30)) / 86400000;
}
function observations() {
  return [['code', 'price', 'tradetime'], ...identities.map(([code], index) =>
    [code, (index + 1) * 7 + 0.125, serial(2030, 1, 8, 16, 0, 1)]),
    ['CURRENCY:USDKRW', 1200 + 7 / 10, ''], ['CURRENCY:JPYKRW', 9 + 1 / 10, '']];
}
function parse(values = observations(), c = catalog(), options = {now}) { ready(); return core.parseValues(values, c, options); }
function oldMarket(c) {
  return market.makeMarket(c, c.instruments.map((instrument, i) => ({security_reference: {...instrument.security_reference},
    price: String(i + 1), currency: instrument.currency, as_of: now, available_at: now, source: 'MANUAL'})),
  ['USD', 'JPY'].map((currency, i) => ({currency, rate: String(i + 2), as_of: now, available_at: now, source: 'MANUAL'})), null, now);
}
function snapshot(c) {
  return {schema: 'device-actual-holdings/1', version: 1, kind: 'ACTUAL', ownership: 'USER_DEVICE_ONLY',
    owner: {role: 'USER', storage: 'USER_DEVICE_ONLY'}, effective_at: now, available_at: now,
    target_root_version: c.target_root_version, target_root_sha256: c.target_root_sha256,
    identity_map_version: c.identity_map_version, identity_map_sha256: c.identity_map_sha256,
    themes: [{theme_id: 'public', holdings: [{security_reference: {...c.instruments[0].security_reference},
      quantity: String(1), average_cost: String(2), currency: 'USD'}]}]};
}
let passed = 0, failed = 0;
function test(label, fn) {
  try { fn(); passed++; process.stdout.write('PASS ' + label + '\n'); }
  catch (_) { failed++; process.stdout.write('FAIL ' + label + '\n'); }
}

test('pure core exports CommonJS and browser helpers without network', () => {
  ready(); const context = {DeviceMarket: market, Intl}; vm.runInNewContext(fs.readFileSync(corePath, 'utf8'), context);
  for (const name of ['parseValues', 'parsePaste', 'apply']) assert.equal(typeof context.GoogleSheetCore[name], 'function');
});
test('complete approved sheet maps exactly nineteen quotes and two FX rates', () => {
  const c = catalog(), result = parse(undefined, c);
  assert.equal(result.successes.length, 21); assert.equal(result.failures.length, 0); assert.equal(result.warnings.length, 0);
  assert.equal(result.quotes.length, 19); assert.equal(result.fx.length, 2);
  result.quotes.forEach((quote, index) => {
    assert.deepEqual(quote.security_reference, c.instruments[index].security_reference);
    assert.equal(quote.currency, c.instruments[index].currency); assert.equal(quote.source, 'GOOGLEFINANCE');
    assert.equal(typeof quote.price, 'string'); assert.equal(quote.available_at, now);
  });
  assert.deepEqual(result.fx.map(row => row.currency), ['USD', 'JPY']);
  assert.deepEqual(result.successes.slice(-2).map(row => row.name), ['USD/KRW', 'JPY/KRW']);
});
test('serial wall times use the exchange time zone including New York winter', () => {
  const result = parse(); assert.equal(result.quotes[0].as_of, '2030-01-08T21:00:01.000Z');
  assert.equal(result.quotes[17].as_of, '2030-01-08T07:00:01.000Z');
  assert.equal(result.quotes[18].as_of, '2030-01-08T07:00:01.000Z');
  assert.ok(result.quotes.every(row => row.time_status === 'KNOWN'));
});
test('New York summer time uses daylight saving time', () => {
  const result = parse([['NASDAQ:ASML', 7, serial(2029, 7, 8, 16)]]);
  assert.equal(result.quotes[0].as_of, '2029-07-08T20:00:00.000Z');
});
test('ambiguous or nonexistent New York local times stay unknown', () => {
  for (const [month, day, hour, minute] of [[11, 4, 1, 30], [3, 11, 2, 30]]) {
    const result = parse([['NASDAQ:ASML', 7, serial(2029, month, day, hour, minute)]]);
    assert.equal(result.quotes[0].as_of, now); assert.equal(result.quotes[0].time_status, 'UNKNOWN');
  }
});
test('observed Korean locale timestamps convert AM and PM explicitly', () => {
  const result = parse([['NASDAQ:ASML', 7, '2029. 10. 8 오후 4:00:01'],
    ['KRX:042700', 8, '2029. 10. 8 오전 12:00:01']]);
  assert.equal(result.quotes[0].as_of, '2029-10-08T20:00:01.000Z');
  assert.equal(result.quotes[1].as_of, '2029-10-07T15:00:01.000Z');
});
test('explicit ISO offsets are respected and local ISO uses exchange time', () => {
  const result = parse([['NASDAQ:ASML', 7, '2029-10-08T16:00:01-04:00'],
    ['KRX:042700', 8, '2029-10-08T16:00:01']]);
  assert.equal(result.quotes[0].as_of, '2029-10-08T20:00:01.000Z');
  assert.equal(result.quotes[1].as_of, '2029-10-08T07:00:01.000Z');
});
test('blank FX times preserve fetched time and explicit FX unknown provenance', () => {
  const result = parse(); assert.ok(result.fx.every(row => row.as_of === now && row.time_status === 'FX_UNKNOWN'));
});
test('unknown future or invalid times never prevent a valid price from saving', () => {
  for (const timestamp of ['', '10/8/2029 4:00 PM', '2029. 2. 30 오후 4:00:01',
    '2029-02-30T16:00:01Z', '2030-01-10T00:00:00Z', Infinity, -1]) {
    const result = parse([['NASDAQ:ASML', 7, timestamp]]);
    assert.equal(result.successes.length, 1); assert.equal(result.quotes[0].time_status, 'UNKNOWN');
    assert.equal(result.quotes[0].as_of, now);
  }
});
test('unsupported prices become named NOT_AVAILABLE failures and preserve existing records', () => {
  const c = catalog(), previous = oldMarket(c);
  for (const price of ['#N/A', '', '   ', 0, -1, NaN, Infinity, null, false, 'not a number', '1e400']) {
    const result = parse([['TYO:8035', price, '']], c);
    assert.equal(result.successes.length, 0); assert.equal(result.failures.length, 1);
    assert.deepEqual(result.failures[0], {code: 'TYO:8035', name: c.instruments[17].label, state: 'NOT_AVAILABLE'});
    const next = core.apply(c, previous, result, now); assert.deepEqual(next.quotes, previous.quotes); assert.deepEqual(next.fx, previous.fx);
  }
});
test('partial failures merge successful new records without deleting manual quotes or rates', () => {
  const c = catalog(), previous = oldMarket(c), values = observations(); values[18][1] = '#N/A'; values[21][1] = '#N/A';
  const result = parse(values, c), next = core.apply(c, previous, result, now);
  assert.equal(result.successes.length, 19); assert.equal(result.failures.length, 2); assert.equal(next.version, previous.version + 1);
  assert.deepEqual(next.quotes.find(row => row.currency === 'JPY'), previous.quotes.find(row => row.currency === 'JPY'));
  assert.deepEqual(next.fx.find(row => row.currency === 'JPY'), previous.fx.find(row => row.currency === 'JPY'));
  assert.equal(next.quotes[0].source, 'GOOGLEFINANCE');
});
test('unknown codes are ignored with generic warnings that never echo unknown content', () => {
  const unknown = ['PRIVATE', 'NOT', 'APPROVED'].join('_'), result = parse([['NASDAQ:ASML', 7, ''], [unknown, 8, '']]);
  assert.equal(result.successes.length, 1); assert.equal(result.failures.length, 0); assert.equal(result.warnings.length, 1);
  assert.ok(!JSON.stringify(result).includes(unknown));
});
test('fixed mapping rejects changed security references and mismatched currencies', () => {
  for (const change of [c => {c.instruments[0].security_reference.value = 'OTHER';}, c => {c.instruments[0].currency = 'KRW';},
    c => {c.instruments[0].security_reference.extra = true;}]) {
    const c = catalog(); change(c); const result = parse([['NASDAQ:ASML', 7, '']], c);
    assert.equal(result.successes.length, 0); assert.equal(result.failures.length, 1); assert.equal(result.quotes.length, 0);
  }
});
test('duplicate known codes fail that code once regardless of row order', () => {
  for (const values of [[['NASDAQ:ASML', 7, ''], ['NASDAQ:ASML', '#N/A', '']],
    [['NASDAQ:ASML', '#N/A', ''], ['NASDAQ:ASML', 7, '']], [['CURRENCY:USDKRW', 7, ''], ['CURRENCY:USDKRW', 8, '']]]) {
    const c = catalog(), previous = oldMarket(c), result = parse(values, c), next = core.apply(c, previous, result, now);
    assert.equal(result.successes.length, 0); assert.equal(result.failures.length, 1); assert.equal(result.warnings.length, 1);
    assert.deepEqual(next.quotes, previous.quotes); assert.deepEqual(next.fx, previous.fx);
  }
});
test('paste accepts tabs and CSV including quoted timestamps using the same validation', () => {
  ready(); const c = catalog(), values = observations(), expected = core.parseValues(values, c, {now});
  const tsv = values.map(row => row.join('\t')).join('\r\n');
  const csv = values.map(row => row.map(value => '"' + String(value).replace(/"/g, '""') + '"').join(',')).join('\n');
  assert.deepEqual(core.parsePaste(tsv, c, {now}), expected); assert.deepEqual(core.parsePaste(csv, c, {now}), expected);
});
test('malformed paste cannot save a partial parsed observation', () => {
  ready(); for (const text of ['"NASDAQ:ASML,7', 'NASDAQ:ASML,7,"broken', 'NASDAQ:ASML,7,extra,unexpected']) {
    assert.throws(() => core.parsePaste(text, catalog(), {now}), error => error.message === 'INVALID');
  }
});
test('numeric strings normalize safely without zero substitution or precision overflow', () => {
  for (const value of ['007.125', '1e2', ' 7.125 ']) {
    const result = parse([['NASDAQ:ASML', value, '']]); assert.equal(result.successes.length, 1);
    assert.ok(Number(result.quotes[0].price) > 0);
  }
  for (const value of [1e-20, 1e20, '9'.repeat(16), '0.0000000000001']) assert.equal(parse([['NASDAQ:ASML', value, '']]).failures.length, 1);
});
test('new GOOGLEFINANCE records propagate precise time provenance through valuation', () => {
  const c = catalog(), result = parse([['NASDAQ:ASML', 7, ''], ['CURRENCY:USDKRW', 8, '']], c);
  const next = core.apply(c, null, result, now), value = market.valuation(snapshot(c), c, next, {now});
  assert.equal(value.state, 'AVAILABLE'); assert.equal(value.rows[0].quote_source, 'GOOGLEFINANCE');
  assert.equal(value.rows[0].quote_time_status, 'UNKNOWN'); assert.equal(value.rows[0].fx_time_status, 'FX_UNKNOWN');
});
test('source-specific provenance validation stays strict and accepts legacy manual records', () => {
  const c = catalog(); market.validateMarket(oldMarket(c), c, {now});
  for (const source of ['MANUAL', 'API']) {
    const previous = oldMarket(c); previous.quotes[0].source = source; previous.quotes[0].time_status = 'UNKNOWN';
    assert.throws(() => market.validateMarket(previous, c, {now}), error => error.message === 'INVALID');
  }
  for (const status of ['OTHER', 'FX_UNKNOWN']) {
    const previous = oldMarket(c); previous.quotes[0].source = 'GOOGLEFINANCE'; previous.quotes[0].time_status = status;
    assert.throws(() => market.validateMarket(previous, c, {now}), error => error.message === 'INVALID');
  }
});
test('Google observations retain seven day staleness and backup excludes connection metadata', () => {
  const c = catalog(), result = parse([['NASDAQ:ASML', 7, '2029-12-31T16:00:00-05:00'], ['CURRENCY:USDKRW', 8, '']], c);
  const next = core.apply(c, null, result, now), value = market.valuation(snapshot(c), c, next, {now});
  assert.equal(value.rows[0].quote_status, 'STALE'); assert.equal(value.stale, true);
  const backup = market.exportBackup(snapshot(c), next, c, {now});
  assert.deepEqual(market.importBackup(backup, c, {now}).market.quotes, []);
  assert.ok(!JSON.stringify(backup).includes('market_data'));
  for (const forbidden of ['spreadsheet_id', 'range', 'access_token', 'google_settings']) assert.ok(!JSON.stringify(backup).includes(forbidden));
});
test('apply rejects observations that bypass parsed result validation', () => {
  const c = catalog(), result = parse([['NASDAQ:ASML', 7, '']], c); result.quotes[0].price = '0';
  assert.throws(() => core.apply(c, oldMarket(c), result, now), error => error.message === 'INVALID');
});
process.stdout.write('COUNTS pass=' + passed + ' fail=' + failed + '\n');
if (failed) process.exitCode = 1;
