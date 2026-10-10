/* Synthetic positions and market inputs are generated only in memory. Logs contain labels and counts. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const modulePath = path.join(__dirname, '../src/investment_system/product/web_assets/device-market.js');
const api = fs.existsSync(modulePath) ? require(modulePath) : {};
const now = '2030-01-09T12:00:00.000Z';
const earlier = '2030-01-09T10:00:00.000Z';
const names = ['canonical', 'validateMarket', 'makeMarket', 'emptyMarket', 'valuation', 'exportBackup', 'importBackup', 'staleness'];
let passed = 0, failed = 0;
function test(label, fn) {
  try { fn(); passed++; process.stdout.write('PASS ' + label + '\n'); }
  catch (_) { failed++; process.stdout.write('FAIL ' + label + '\n'); }
}
function ready() { for (const name of names) assert.equal(typeof api[name], 'function'); }
function catalog() {
  return {
    schema: 'DEVICE_ACTUAL_CATALOG/1', target_root_version: 'v0', target_root_sha256: 'a'.repeat(64),
    identity_map_version: 'public-map', identity_map_sha256: 'b'.repeat(64), total_units: 10000,
    themes: ['first', 'second'].map(theme_id => ({theme_id, label: theme_id, target_units: 5000})),
    instruments: Array.from({length: 19}, (_, i) => ({row_index: i, label: 'Public instrument ' + i,
      theme_id: i < 10 ? 'first' : 'second', target_units: i === 18 ? 1000 : 500,
      security_reference: {scheme: 'PUBLIC_TEST', value: 'IDENTITY_' + i, exchange: 'PUBLIC'},
      currency: ['USD', 'JPY', 'KRW'][i % 3]}))
  };
}
function rows(c, count = 3) {
  return c.instruments.slice(0, count).map((instrument, i) => ({security_reference: {...instrument.security_reference},
    quantity: String(i + 1), average_cost: String(i + 7), currency: instrument.currency}));
}
function snapshot(c, positions = rows(c)) {
  return {schema: 'device-actual-holdings/1', version: 1, kind: 'ACTUAL', ownership: 'USER_DEVICE_ONLY',
    owner: {role: 'USER', storage: 'USER_DEVICE_ONLY'}, effective_at: now, available_at: now,
    target_root_version: c.target_root_version, target_root_sha256: c.target_root_sha256,
    identity_map_version: c.identity_map_version, identity_map_sha256: c.identity_map_sha256,
    themes: c.themes.map(theme => ({theme_id: theme.theme_id, holdings: positions.filter(row =>
      c.instruments.find(instrument => JSON.stringify(instrument.security_reference) === JSON.stringify(row.security_reference)).theme_id === theme.theme_id)}))};
}
function quote(c, i, price = String((i + 1) * 10), extra = {}) {
  return {security_reference: {...c.instruments[i].security_reference}, price, currency: c.instruments[i].currency,
    as_of: earlier, available_at: now, source: 'MANUAL', ...extra};
}
function fx(currency, rate, extra = {}) { return {currency, rate, as_of: earlier, available_at: now, source: 'MANUAL', ...extra}; }
function market(c, quotes = [quote(c, 0), quote(c, 1), quote(c, 2)], rates = [fx('USD', '1300'), fx('JPY', '10')]) {
  ready(); return api.makeMarket(c, quotes, rates, null, now);
}
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function rejects(fn, expected = ['INVALID', 'INCOMPATIBLE', 'VERSION', 'CATALOG']) {
  let error; try { fn(); } catch (caught) { error = caught; }
  assert.ok(error instanceof Error); assert.ok(expected.includes(error.message));
}
function invalidMarket(change) { const c = catalog(), value = market(c); change(value); rejects(() => api.validateMarket(value, c, {now})); }

test('exports the isolated UMD and CommonJS helpers', () => {
  ready(); const context = {}; vm.runInNewContext(fs.readFileSync(modulePath, 'utf8'), context);
  for (const name of names) assert.equal(typeof context.DeviceMarket[name], 'function');
});
test('canonical identities compare complete sorted reference objects', () => {
  ready(); assert.equal(api.canonical({b: 2, a: {d: 4, c: 3}}), api.canonical({a: {c: 3, d: 4}, b: 2}));
});
test('market binds device ownership and reviewed catalogue metadata', () => {
  const c = catalog(), value = market(c); assert.equal(value.schema, 'device-market-data/1');
  assert.equal(value.version, 1); assert.equal(value.kind, 'MARKET_DATA'); assert.equal(value.ownership, 'USER_DEVICE_ONLY');
  assert.deepEqual(value.owner, {role: 'USER', storage: 'USER_DEVICE_ONLY'}); assert.equal(value.base_currency, 'KRW');
  for (const key of ['target_root_version', 'target_root_sha256', 'identity_map_version', 'identity_map_sha256']) assert.equal(value[key], c[key]);
});
test('validation and construction clone caller inputs', () => {
  const c = catalog(), quotes = [quote(c, 0)], rates = [fx('USD', '1300')], value = market(c, quotes, rates);
  quotes[0].price = '99'; rates[0].rate = '99'; assert.equal(value.quotes[0].price, '10');
  const validated = api.validateMarket(value, c, {now}); validated.quotes[0].price = '99'; assert.equal(value.quotes[0].price, '10');
});
test('empty market invents no quotes or exchange rates', () => {
  ready(); const c = catalog(), value = api.emptyMarket(c, now);
  assert.deepEqual(value.quotes, []); assert.deepEqual(value.fx, []); api.validateMarket(value, c, {now});
});
test('market revisions advance and reject unsafe or stale versions', () => {
  const c = catalog(), value = market(c), next = api.makeMarket(c, [], [], value, now);
  assert.equal(next.version, 2); rejects(() => api.validateMarket(value, c, {now, minimumVersion: 1}), ['VERSION']);
  value.version = Number.MAX_SAFE_INTEGER; rejects(() => api.makeMarket(c, [], [], value, now));
  for (const version of [0, -1, 1.5, '1', Infinity]) invalidMarket(value => { value.version = version; });
});
test('unknown envelope owner quote and FX properties fail closed', () => {
  for (const change of [value => {value.api_key = 'SYNTHETIC';}, value => {value.owner.token = 'SYNTHETIC';},
    value => {value.quotes[0].provider_key = 'SYNTHETIC';}, value => {value.fx[0].extra = true;},
    value => {value.quotes[0].security_reference.extra = true;}]) invalidMarket(change);
});
test('invalid ownership schema kind and base currency fail closed', () => {
  for (const change of [value => {value.schema = 'other';}, value => {value.kind = 'ACTUAL';},
    value => {value.ownership = 'SERVER';}, value => {value.owner.role = 'SYSTEM';},
    value => {value.owner.storage = 'SERVER';}, value => {value.base_currency = 'USD';}]) invalidMarket(change);
});
test('identity lineage mismatch is incompatible', () => {
  for (const key of ['target_root_version', 'target_root_sha256', 'identity_map_version', 'identity_map_sha256']) {
    const c = catalog(), value = market(c); value[key] = 'incompatible';
    rejects(() => api.validateMarket(value, c, {now}), ['INCOMPATIBLE']);
  }
});
test('quote references native denominations and sources are strict', () => {
  for (const change of [value => {value.quotes[0].security_reference.value = 'UNKNOWN';},
    value => {value.quotes[0].security_reference = 'UNKNOWN';}, value => {value.quotes[0].currency = 'JPY';},
    value => {value.quotes[0].source = 'ESTIMATE';}, value => {delete value.quotes[0].source;}]) invalidMarket(change);
  const c = catalog(), value = market(c, [quote(c, 0, '10', {source: 'API'})], []); assert.equal(value.quotes[0].source, 'API');
});
test('prices and FX require positive bounded decimal strings', () => {
  for (const invalid of ['0', '0.000000000000', '-1', 'NaN', 'Infinity', '1e2', ' 1', '01', '1.', '', 1, null, '9'.repeat(16), '1.1234567890123']) {
    invalidMarket(value => {value.quotes[0].price = invalid;}); invalidMarket(value => {value.fx[0].rate = invalid;});
  }
  const c = catalog(); market(c, [quote(c, 0, '0.000000000001')], [fx('USD', '999999999999999.123456789012')]);
});
test('duplicate prices and duplicate or unsupported FX currencies reject', () => {
  invalidMarket(value => {value.quotes.push(copy(value.quotes[0]));});
  invalidMarket(value => {value.fx.push(copy(value.fx[0]));});
  for (const currency of ['KRW', 'EUR', 'usd']) invalidMarket(value => {value.fx[0].currency = currency;});
  invalidMarket(value => {value.fx[0].source = 'ESTIMATE';});
});
test('future and reversed market quote and FX clocks reject', () => {
  const future = '2030-01-10T00:00:00Z';
  for (const change of [value => {value.available_at = future;}, value => {value.effective_at = future;},
    value => {value.quotes[0].available_at = future;}, value => {value.quotes[0].as_of = future;},
    value => {value.fx[0].available_at = future;}, value => {value.fx[0].as_of = future;}]) invalidMarket(change);
});
test('timestamps reject calendar rollover malformed offset and non-ISO forms', () => {
  for (const invalid of ['2030-02-30T00:00:00Z', '2030-13-01T00:00:00Z', '2030-01-09T24:00:00Z',
    '2030-01-09T00:60:00Z', '2030-01-09T00:00:60Z', '2030-01-09T00:00:00+24:00', '2030-01-09', '', null]) {
    invalidMarket(value => {value.quotes[0].as_of = invalid;}); invalidMarket(value => {value.fx[0].as_of = invalid;});
  }
});
test('missing holdings stay unavailable with KRW base', () => {
  ready(); const c = catalog(), value = api.valuation(null, c, api.emptyMarket(c, now), {now});
  assert.equal(value.state, 'NOT_AVAILABLE'); assert.equal(value.reason, 'NO_ACTUAL'); assert.equal(value.currency, 'KRW'); assert.equal(value.total, null);
});
test('three native currencies convert to a single KRW denominator', () => {
  const c = catalog(), value = api.valuation(snapshot(c), c, market(c), {now});
  assert.equal(value.state, 'AVAILABLE'); assert.equal(value.total, 13490); assert.equal(value.currency, 'KRW');
  assert.deepEqual(value.rows.map(row => row.market_value_native), [10, 40, 90]);
  assert.deepEqual(value.rows.map(row => row.market_value), [13000, 400, 90]);
  assert.ok(Math.abs(value.rows[0].weight - 13000 / 13490) < 1e-12);
  assert.ok(Math.abs(value.rows[0].delta - (13000 / 13490 - 0.05)) < 1e-12);
  assert.equal(value.themes[0].weight, 1); assert.equal(value.themes[0].delta, 0.5);
  assert.deepEqual(value.currency_totals, {USD: 10, JPY: 40, KRW: 90});
});
test('native valuation does not reinterpret average cost denomination as quote currency', () => {
  const c = catalog(), positions = rows(c, 1); positions[0].currency = 'JPY'; positions[0].average_cost = '999999999999999';
  const value = api.valuation(snapshot(c, positions), c, market(c), {now});
  assert.equal(value.total, 13000); assert.equal(value.rows[0].currency, 'JPY'); assert.equal(value.rows[0].market_currency_native, 'USD');
});
test('missing price blocks all weights while preserving known values', () => {
  const c = catalog(), value = api.valuation(snapshot(c), c, market(c, [quote(c, 0), quote(c, 2)]), {now});
  assert.equal(value.total, null); assert.equal(value.reason, 'MISSING_QUOTES'); assert.equal(value.rows[0].market_value, 13000);
  assert.equal(value.rows[1].market_value_native, null); assert.equal(value.rows[1].quote_status, 'NOT_AVAILABLE');
  assert.ok(value.rows.every(row => row.weight === null && row.delta === null)); assert.ok(value.themes.every(theme => theme.weight === null && theme.delta === null));
});
test('missing FX preserves native values and blocks denominator renormalization', () => {
  const c = catalog(), value = api.valuation(snapshot(c), c, market(c, undefined, [fx('USD', '1300')]), {now});
  assert.equal(value.total, null); assert.equal(value.reason, 'FX_NOT_AVAILABLE'); assert.equal(value.rows[1].market_value_native, 40);
  assert.equal(value.rows[1].market_value, null); assert.equal(value.rows[1].fx_status, 'NOT_AVAILABLE');
  assert.ok(value.rows.every(row => row.weight === null && row.delta === null)); assert.equal(value.rows[2].market_value, 90);
});
test('KRW positions never require an exchange rate', () => {
  const c = catalog(), value = api.valuation(snapshot(c, rows(c).slice(2)), c, market(c, [quote(c, 2)], []), {now});
  assert.equal(value.total, 90); assert.equal(value.rows[0].fx_status, 'NOT_REQUIRED'); assert.equal(value.rows[0].fx_source, null);
});
test('zero or empty positions never create weights or divide by zero', () => {
  const c = catalog(), positions = rows(c).map(row => ({...row, quantity: '0'}));
  const value = api.valuation(snapshot(c, positions), c, market(c), {now});
  assert.equal(value.state, 'NOT_AVAILABLE'); assert.equal(value.reason, 'NO_POSITIONS'); assert.equal(value.total, 0);
  assert.ok(value.rows.every(row => row.market_value === 0 && row.weight === null && row.delta === null));
  const empty = api.valuation(snapshot(c, []), c, market(c), {now}); assert.equal(empty.total, 0); assert.equal(empty.reason, 'NO_POSITIONS');
});
test('zero quantity never manufactures an absent price', () => {
  const c = catalog(), positions = rows(c, 1).map(row => ({...row, quantity: '0'}));
  const value = api.valuation(snapshot(c, positions), c, market(c, [], []), {now});
  assert.equal(value.rows[0].market_value, null); assert.equal(value.rows[0].market_value_native, null); assert.equal(value.total, null);
});
test('staleness begins at exactly seven days using observation time', () => {
  ready(); const instant = Date.parse(now), week = 7 * 24 * 60 * 60 * 1000;
  assert.equal(api.staleness(new Date(instant - week + 1).toISOString(), now), 'CURRENT');
  assert.equal(api.staleness(new Date(instant - week).toISOString(), now), 'STALE');
  assert.equal(api.staleness(new Date(instant - week - 1).toISOString(), now), 'STALE');
  assert.equal(api.staleness(null, now), 'NOT_AVAILABLE');
});
test('stale supplied values remain usable and retain quote and FX provenance', () => {
  const c = catalog(), stale = '2030-01-02T12:00:00.000Z';
  const value = api.valuation(snapshot(c, rows(c, 1)), c,
    market(c, [quote(c, 0, '10', {as_of: stale, source: 'API'})], [fx('USD', '1300', {as_of: stale})]), {now});
  assert.equal(value.state, 'AVAILABLE'); assert.equal(value.total, 13000); assert.equal(value.stale, true);
  const row = value.rows[0]; assert.equal(row.quote_status, 'STALE'); assert.equal(row.fx_status, 'STALE');
  assert.equal(row.quote_as_of, stale); assert.equal(row.quote_available_at, now); assert.equal(row.quote_source, 'API');
  assert.equal(row.fx_as_of, stale); assert.equal(row.fx_available_at, now); assert.equal(row.fx_source, 'MANUAL');
});
test('unused stale observations do not mark held positions stale', () => {
  const c = catalog(), value = api.valuation(snapshot(c, rows(c).slice(2)), c,
    market(c, [quote(c, 0, '10', {as_of: '2030-01-01T12:00:00Z'}), quote(c, 2)], [fx('USD', '1300', {as_of: '2030-01-01T12:00:00Z'})]), {now});
  assert.equal(value.state, 'AVAILABLE'); assert.equal(value.stale, false);
});
test('malformed numeric overflow inputs cannot enter valuation', () => {
  const c = catalog(), validMarket = market(c);
  for (const invalid of ['9'.repeat(400), '1e308', Infinity, NaN]) {
    const value = snapshot(c); value.themes[0].holdings[0].quantity = invalid;
    rejects(() => api.valuation(value, c, validMarket, {now}));
  }
  invalidMarket(value => {value.quotes[0].price = 1e308;}); invalidMarket(value => {value.fx[0].rate = 1e308;});
});
test('maximal permitted multiplications and totals remain finite', () => {
  const c = catalog(), maximum = '999999999999999.999999999999', positions = rows(c).map(row => ({...row, quantity: maximum}));
  const value = api.valuation(snapshot(c, positions), c,
    market(c, c.instruments.slice(0, 3).map((_, i) => quote(c, i, maximum)), [fx('USD', maximum), fx('JPY', maximum)]), {now});
  assert.equal(value.state, 'AVAILABLE'); assert.ok(Number.isFinite(value.total));
  assert.ok(value.rows.every(row => Number.isFinite(row.market_value) && Number.isFinite(row.weight)));
});
test('snapshot numeric currency identity and theme duplicates are validated locally', () => {
  const c = catalog(), validMarket = market(c);
  for (const change of [value => {value.themes[0].holdings[0].currency = 'EUR';},
    value => {value.themes[0].holdings[0].security_reference.value = 'UNKNOWN';},
    value => {value.themes[0].holdings.push(copy(value.themes[0].holdings[0]));},
    value => {value.themes[1].theme_id = 'first';}, value => {value.themes[0].holdings[0].average_cost = 'NaN';}]) {
    const value = snapshot(c); change(value); rejects(() => api.valuation(value, c, validMarket, {now}));
  }
});
test('new holdings export excludes quotes and FX', () => {
  const c=catalog(), holdings=snapshot(c), backup=api.exportBackup(holdings,market(c),c,{now});
  assert.equal(backup.schema,'device-actual-holdings/1');assert.deepEqual(backup,holdings);assert.ok(!Object.hasOwn(backup,'market_data'));
  const restored=api.importBackup(backup,c,{now});assert.deepEqual(restored.snapshot,holdings);assert.deepEqual(restored.market.quotes,[]);assert.deepEqual(restored.market.fx,[]);
});
test('legacy v2 imports validate then discard prices', () => {
  const c=catalog(),holdings=snapshot(c), backup={...holdings,schema:'device-actual-holdings/2',market_data:market(c)};
  const restored=api.importBackup(backup,c,{now});assert.deepEqual(restored.snapshot,holdings);assert.deepEqual(restored.market.quotes,[]);
});
test('legacy backup restores holdings with an empty market', () => {
  ready(); const c = catalog(), holdings = snapshot(c), restored = api.importBackup(holdings, c, {now});
  assert.deepEqual(restored.snapshot, holdings); assert.deepEqual(restored.market.quotes, []); assert.deepEqual(restored.market.fx, []);
});
test('API keys settings and unknown fields cannot be exported or imported', () => {
  const c = catalog(), holdings = snapshot(c), quotes = market(c);
  for (const change of [value => {value.api_key = 'SYNTHETIC';}, value => {value.settings = {api_key: 'SYNTHETIC'};},
    value => {value.owner.api_key = 'SYNTHETIC';}, value => {value.themes[0].holdings[0].api_key = 'SYNTHETIC';}]) {
    const value = copy(holdings); change(value); rejects(() => api.exportBackup(value, quotes, c, {now}));
    rejects(() => api.importBackup(value, c, {now}));
  }
  const value = {...holdings,schema:'device-actual-holdings/2',market_data:quotes}; value.market_data.api_key = 'SYNTHETIC';
  rejects(() => api.importBackup(value, c, {now}));
});
test('invalid v2 market or missing market cannot partially restore holdings', () => {
  const c = catalog(), backup = {...snapshot(c),schema:'device-actual-holdings/2',market_data:market(c)};
  for (const change of [value => {value.market_data.quotes[0].currency = 'KRW';}, value => {delete value.market_data;},
    value => {value.market_data.identity_map_sha256 = 'incompatible';}, value => {value.schema = 'device-actual-holdings/3';}]) {
    const value = copy(backup); change(value); rejects(() => api.importBackup(value, c, {now}));
  }
});
test('export validates original legacy holdings envelope before allowlisting', () => {
  const c = catalog(), holdings = snapshot(c), quotes = market(c);
  for (const change of [value => {value.schema = 'other';}, value => {value.version = 0;}, value => {value.available_at = '2030-01-10T00:00:00Z';},
    value => {value.ownership = 'SERVER';}, value => {value.identity_map_sha256 = 'incompatible';}]) {
    const value = copy(holdings); change(value); rejects(() => api.exportBackup(value, quotes, c, {now}));
  }
});
process.stdout.write('COUNTS pass=' + passed + ' fail=' + failed + '\n');
if (failed) process.exitCode = 1;
