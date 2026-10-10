/* User-supplied market observations stay on the device. This module has no provider or network calls. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DeviceMarket = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'device-market-data/1', ACTUAL_SCHEMA = 'device-actual-holdings/1', BACKUP_SCHEMA = 'device-actual-holdings/2';
  const CURRENCIES = ['USD', 'JPY', 'KRW'], FX_CURRENCIES = ['USD', 'JPY'];
  const DECIMAL = /^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/, WEEK = 7 * 24 * 60 * 60 * 1000;
  const LINEAGE_KEYS = ['target_root_version', 'target_root_sha256', 'identity_map_version', 'identity_map_sha256'];
  const COMMON_KEYS = ['schema', 'version', 'kind', 'ownership', 'owner', 'effective_at', 'available_at', ...LINEAGE_KEYS];
  const ACTUAL_KEYS = [...COMMON_KEYS, 'themes'], MARKET_KEYS = [...COMMON_KEYS, 'base_currency', 'quotes', 'fx'];
  const ERROR_CODES = ['INVALID', 'INCOMPATIBLE', 'VERSION', 'CATALOG'];

  function fail(code = 'INVALID') { throw new Error(code); }
  function safe(fn) {
    return function (...args) {
      try { return fn(...args); }
      catch (error) { throw new Error(error && ERROR_CODES.includes(error.message) ? error.message : 'INVALID'); }
    };
  }
  function plain(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value)
      && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
  }
  function keys(value, expected) {
    if (!plain(value) || Object.keys(value).length !== expected.length
      || expected.some(key => !Object.prototype.hasOwnProperty.call(value, key))) fail();
  }
  function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (plain(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
    return JSON.stringify(value);
  }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function decimal(value, positive = false) {
    if (typeof value !== 'string' || !DECIMAL.test(value)) fail();
    const number = Number(value);
    if (!Number.isFinite(number) || (positive && number <= 0)) fail();
    return number;
  }
  function clock(value) {
    if (typeof value !== 'string') fail();
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
    if (!match) fail();
    const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
    if (year < 1970 || month < 1 || month > 12 || day < 1
      || day > new Date(Date.UTC(year, month, 0)).getUTCDate()
      || Number(match[4]) > 23 || Number(match[5]) > 59 || Number(match[6]) > 59) fail();
    if (match[8] !== 'Z' && (Number(match[8].slice(1, 3)) > 23 || Number(match[8].slice(4)) > 59)) fail();
    const result = Date.parse(value); if (!Number.isFinite(result)) fail(); return result;
  }
  function nowMillis(now) {
    const result = now === undefined ? Date.now() : typeof now === 'number' ? now : clock(now);
    if (!Number.isFinite(result)) fail(); return result;
  }
  function catalogIndex(catalog) {
    if (!plain(catalog) || catalog.schema !== 'DEVICE_ACTUAL_CATALOG/1' || !Array.isArray(catalog.themes)
      || !Array.isArray(catalog.instruments) || !catalog.themes.length || !catalog.instruments.length
      || catalog.instruments.length > 100 || catalog.total_units !== 10000) fail('CATALOG');
    for (const field of ['target_root_version', 'identity_map_version']) {
      if (typeof catalog[field] !== 'string' || !catalog[field]) fail('CATALOG');
    }
    for (const field of ['target_root_sha256', 'identity_map_sha256']) {
      if (typeof catalog[field] !== 'string' || !/^[a-f0-9]{64}$/.test(catalog[field])) fail('CATALOG');
    }
    const themes = new Map(), instruments = new Map();
    for (const theme of catalog.themes) {
      if (!plain(theme) || typeof theme.theme_id !== 'string' || !theme.theme_id || themes.has(theme.theme_id)
        || !Number.isSafeInteger(theme.target_units) || theme.target_units < 0) fail('CATALOG');
      themes.set(theme.theme_id, theme);
    }
    for (const instrument of catalog.instruments) {
      if (!plain(instrument) || !plain(instrument.security_reference) || !themes.has(instrument.theme_id)
        || !CURRENCIES.includes(instrument.currency) || !Number.isSafeInteger(instrument.target_units)
        || instrument.target_units < 0) fail('CATALOG');
      const id = canonical(instrument.security_reference);
      if (instruments.has(id)) fail('CATALOG'); instruments.set(id, instrument);
    }
    if (catalog.themes.reduce((sum, theme) => sum + theme.target_units, 0) !== catalog.total_units
      || catalog.instruments.reduce((sum, instrument) => sum + instrument.target_units, 0) !== catalog.total_units) fail('CATALOG');
    return {themes, instruments};
  }
  function envelope(value, catalog, schema, kind, options) {
    if (value.schema !== schema || value.kind !== kind || value.ownership !== 'USER_DEVICE_ONLY'
      || !Number.isSafeInteger(value.version) || value.version < 1) fail();
    if (options.minimumVersion !== undefined
      && (!Number.isSafeInteger(options.minimumVersion) || options.minimumVersion < 0 || value.version <= options.minimumVersion)) fail('VERSION');
    keys(value.owner, ['role', 'storage']);
    if (value.owner.role !== 'USER' || value.owner.storage !== 'USER_DEVICE_ONLY') fail();
    for (const field of LINEAGE_KEYS) if (value[field] !== catalog[field]) fail('INCOMPATIBLE');
    if (clock(value.effective_at) > clock(value.available_at) || clock(value.available_at) > nowMillis(options.now)) fail();
  }
  function observation(value, current) {
    if (!['MANUAL', 'API', 'GOOGLEFINANCE'].includes(value.source)) fail();
    if (clock(value.as_of) > clock(value.available_at) || clock(value.available_at) > current) fail();
  }
  function observationKeys(value, expected, isFX = false) {
    const hasStatus = plain(value) && Object.prototype.hasOwnProperty.call(value, 'time_status');
    keys(value, hasStatus ? [...expected, 'time_status'] : expected);
    if (value.source === 'GOOGLEFINANCE') {
      if (!hasStatus || !(isFX ? ['KNOWN', 'UNKNOWN', 'FX_UNKNOWN'] : ['KNOWN', 'UNKNOWN']).includes(value.time_status)) fail();
      if (value.time_status !== 'KNOWN' && value.as_of !== value.available_at) fail();
    } else if (hasStatus) fail();
  }
  function validateMarket(market, catalog, options = {}) {
    const index = catalogIndex(catalog), current = nowMillis(options.now);
    keys(market, MARKET_KEYS); envelope(market, catalog, SCHEMA, 'MARKET_DATA', options);
    if (market.base_currency !== 'KRW' || !Array.isArray(market.quotes) || !Array.isArray(market.fx)
      || market.quotes.length > index.instruments.size || market.fx.length > FX_CURRENCIES.length) fail();
    const seenQuotes = new Set(), seenFX = new Set();
    for (const quote of market.quotes) {
      observationKeys(quote, ['security_reference', 'price', 'currency', 'as_of', 'available_at', 'source']);
      if (!plain(quote.security_reference)) fail();
      const id = canonical(quote.security_reference), instrument = index.instruments.get(id);
      if (!instrument || seenQuotes.has(id) || quote.currency !== instrument.currency) fail();
      seenQuotes.add(id); decimal(quote.price, true); observation(quote, current);
    }
    for (const rate of market.fx) {
      observationKeys(rate, ['currency', 'rate', 'as_of', 'available_at', 'source'], true);
      if (!FX_CURRENCIES.includes(rate.currency) || seenFX.has(rate.currency)) fail();
      seenFX.add(rate.currency); decimal(rate.rate, true); observation(rate, current);
    }
    return clone(market);
  }
  function makeMarket(catalog, quotes, fx, previous = null, now) {
    catalogIndex(catalog);
    if (!Array.isArray(quotes) || !Array.isArray(fx)) fail();
    if (previous !== null) validateMarket(previous, catalog, {now});
    const timestamp = new Date(nowMillis(now)).toISOString();
    const market = {
      schema: SCHEMA, version: previous === null ? 1 : previous.version + 1, kind: 'MARKET_DATA', ownership: 'USER_DEVICE_ONLY',
      owner: {role: 'USER', storage: 'USER_DEVICE_ONLY'}, effective_at: timestamp, available_at: timestamp,
      target_root_version: catalog.target_root_version, target_root_sha256: catalog.target_root_sha256,
      identity_map_version: catalog.identity_map_version, identity_map_sha256: catalog.identity_map_sha256,
      base_currency: 'KRW', quotes, fx
    };
    return validateMarket(market, catalog, {now});
  }
  function emptyMarket(catalog, now) { return makeMarket(catalog, [], [], null, now); }
  function validateActual(snapshot, catalog, options = {}) {
    const index = catalogIndex(catalog); keys(snapshot, ACTUAL_KEYS);
    envelope(snapshot, catalog, ACTUAL_SCHEMA, 'ACTUAL', options);
    if (!Array.isArray(snapshot.themes) || snapshot.themes.length !== index.themes.size) fail();
    const seenThemes = new Set(), seenRows = new Set();
    for (const theme of snapshot.themes) {
      keys(theme, ['theme_id', 'holdings']);
      if (!index.themes.has(theme.theme_id) || seenThemes.has(theme.theme_id) || !Array.isArray(theme.holdings)
        || theme.holdings.length > index.instruments.size) fail();
      seenThemes.add(theme.theme_id);
      for (const row of theme.holdings) {
        keys(row, ['security_reference', 'quantity', 'average_cost', 'currency']);
        if (!plain(row.security_reference)) fail();
        const id = canonical(row.security_reference), instrument = index.instruments.get(id);
        if (!instrument || instrument.theme_id !== theme.theme_id || seenRows.has(id) || !CURRENCIES.includes(row.currency)) fail();
        seenRows.add(id); decimal(row.quantity); decimal(row.average_cost);
      }
    }
    return clone(snapshot);
  }
  function staleness(asOf, now) {
    if (asOf === null || asOf === undefined) return 'NOT_AVAILABLE';
    const age = nowMillis(now) - clock(asOf); if (age < 0) fail();
    return age >= WEEK ? 'STALE' : 'CURRENT';
  }
  function finiteSum(values) {
    let result = 0;
    for (const value of values) {
      if (value === null || !Number.isFinite(value)) return null;
      result += value; if (!Number.isFinite(result)) return null;
    }
    return result;
  }
  function valuation(snapshot, catalog, market, options = {}) {
    const index = catalogIndex(catalog), current = nowMillis(options.now);
    const empty = {state: 'NOT_AVAILABLE', reason: 'NO_ACTUAL', total: null, currency: 'KRW', rows: [], themes: [], currency_totals: {}, stale: false};
    if (snapshot === null || snapshot === undefined) return empty;
    const actual = validateActual(snapshot, catalog, options);
    const data = market === null || market === undefined ? emptyMarket(catalog, current) : validateMarket(market, catalog, options);
    const quotes = new Map(data.quotes.map(quote => [canonical(quote.security_reference), quote]));
    const rates = new Map(data.fx.map(rate => [rate.currency, rate]));
    let missingQuote = false, missingFX = false, calculationError = false;
    const rows = actual.themes.flatMap(theme => theme.holdings.map(row => {
      const instrument = index.instruments.get(canonical(row.security_reference)), currency = instrument.currency;
      const quote = quotes.get(canonical(row.security_reference)), rate = rates.get(currency), quantity = decimal(row.quantity);
      let native = null, converted = null;
      if (quote) {
        native = quantity * decimal(quote.price, true);
        if (!Number.isFinite(native)) { native = null; calculationError = true; }
      } else missingQuote = true;
      if (currency !== 'KRW' && !rate) missingFX = true;
      if (native !== null && (currency === 'KRW' || rate)) {
        converted = currency === 'KRW' ? native : native * decimal(rate.rate, true);
        if (!Number.isFinite(converted)) { converted = null; calculationError = true; }
      }
      return {...row, theme_id: theme.theme_id, target_units: instrument.target_units,
        market_currency_native: currency, market_value_native: native, market_value: converted, weight: null, delta: null,
        quote_as_of: quote ? quote.as_of : null, quote_available_at: quote ? quote.available_at : null,
        quote_time_status: quote ? quote.time_status || 'KNOWN' : null,
        quote_source: quote ? quote.source : null, quote_status: staleness(quote ? quote.as_of : null, current),
        fx_as_of: currency !== 'KRW' && rate ? rate.as_of : null,
        fx_available_at: currency !== 'KRW' && rate ? rate.available_at : null,
        fx_time_status: currency !== 'KRW' && rate ? rate.time_status || 'KNOWN' : null,
        fx_source: currency !== 'KRW' && rate ? rate.source : null,
        fx_status: currency === 'KRW' ? 'NOT_REQUIRED' : staleness(rate ? rate.as_of : null, current)};
    }));
    const total = finiteSum(rows.map(row => row.market_value));
    if (!missingQuote && !missingFX && total === null) calculationError = true;
    const available = total !== null && total > 0 && !calculationError;
    const positive = rows.some(row => decimal(row.quantity) > 0), currencyTotals = {};
    for (const currency of new Set(rows.map(row => row.market_currency_native))) {
      currencyTotals[currency] = finiteSum(rows.filter(row => row.market_currency_native === currency).map(row => row.market_value_native));
    }
    if (available) for (const row of rows) {
      row.weight = row.market_value / total; row.delta = row.weight - row.target_units / catalog.total_units;
    }
    const themes = catalog.themes.map(theme => {
      const value = available ? finiteSum(rows.filter(row => row.theme_id === theme.theme_id).map(row => row.market_value)) : null;
      const weight = available && value !== null ? value / total : null;
      return {theme_id: theme.theme_id, market_value: value, weight, delta: weight === null ? null : weight - theme.target_units / catalog.total_units};
    });
    return {state: available ? 'AVAILABLE' : 'NOT_AVAILABLE',
      reason: available ? 'QUOTED' : !positive ? 'NO_POSITIONS' : calculationError ? 'CALCULATION_ERROR'
        : missingQuote ? 'MISSING_QUOTES' : missingFX ? 'FX_NOT_AVAILABLE' : 'NO_POSITIONS',
      total, currency: 'KRW', rows, themes, currency_totals: currencyTotals,
      stale: rows.some(row => row.quote_status === 'STALE' || row.fx_status === 'STALE')};
  }
  function exportBackup(snapshot, market, catalog, options = {}) {
    const actual = validateActual(snapshot, catalog, options);
    return actual; // Market quotes, FX and imported prices are never backed up.
  }
  function importBackup(payload, catalog, options = {}) {
    if (!plain(payload)) fail();
    if (payload.schema === ACTUAL_SCHEMA) {
      return {snapshot: validateActual(payload, catalog, options), market: emptyMarket(catalog, options.now)};
    }
    keys(payload, [...ACTUAL_KEYS, 'market_data']); if (payload.schema !== BACKUP_SCHEMA) fail();
    const snapshot = {};
    for (const field of ACTUAL_KEYS) snapshot[field] = payload[field];
    snapshot.schema = ACTUAL_SCHEMA;
    return {snapshot: validateActual(snapshot, catalog, options), market: (validateMarket(payload.market_data, catalog, options), emptyMarket(catalog, options.now))};
  }
  return Object.freeze({canonical: safe(canonical), validateMarket: safe(validateMarket), makeMarket: safe(makeMarket),
    emptyMarket: safe(emptyMarket), valuation: safe(valuation), exportBackup: safe(exportBackup), importBackup: safe(importBackup), staleness: safe(staleness)});
});
