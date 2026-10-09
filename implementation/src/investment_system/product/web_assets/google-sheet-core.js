/* Pure device-side Google Sheet parsing. No credentials, persistence, or network calls. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./device-market.js'));
  else root.GoogleSheetCore = factory(root.DeviceMarket);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (market) {
  'use strict';
  const DAY = 86400000, SERIAL_EPOCH = Date.UTC(1899, 11, 30);
  const FIXED = [
    ['NASDAQ:ASML', 'ASML Holding', 'USN070592100'],
    ['NASDAQ:LRCX', 'Lam Research', 'US5128073062'],
    ['NASDAQ:KLAC', 'KLA Corporation', 'US4824801009'],
    ['NASDAQ:NVDA', 'NVIDIA', 'US67066G1040'],
    ['NASDAQ:AMD', 'Advanced Micro Devices', 'US0079031078'],
    ['NASDAQ:AVGO', 'Broadcom', 'US11135F1012'],
    ['NASDAQ:QCOM', 'Qualcomm', 'US7475251036'],
    ['NASDAQ:INTC', 'Intel', 'US4581401001'],
    ['NASDAQ:MSFT', 'Microsoft', 'US5949181045'],
    ['NASDAQ:GOOGL', 'Alphabet', 'US02079K3059'],
    ['NASDAQ:AMZN', 'Amazon', 'US0231351067'],
    ['NYSE:RTX', 'RTX Corporation', 'US75513E1010'],
    ['NYSE:SYK', 'Stryker', 'US8636671013'],
    ['NYSE:ETN', 'Eaton', 'IE00B8KQN827'],
    ['NYSE:HUBB', 'Hubbell', 'US4435106079'],
    ['NYSE:GEV', 'GE Vernova', 'US36828A1016'],
    ['NYSE:ROK', 'Rockwell Automation', 'US7739031091']
  ].map(([code, name, isin]) => ({code, name, kind: 'quote', currency: 'USD', timeZone: 'America/New_York',
    security_reference: {scheme: 'ISIN', value: isin}}));
  FIXED.push({code: 'TYO:8035', name: 'Tokyo Electron', kind: 'quote', currency: 'JPY', timeZone: 'Asia/Tokyo',
    security_reference: {scheme: 'EXCHANGE_CODE', exchange: 'TSE', code: '8035'}},
  {code: 'KRX:042700', name: '한미반도체', kind: 'quote', currency: 'KRW', timeZone: 'Asia/Seoul',
    security_reference: {scheme: 'EXCHANGE_CODE', exchange: 'KRX', code: '042700'}},
  {code: 'CURRENCY:USDKRW', name: 'USD/KRW', kind: 'fx', currency: 'USD'},
  {code: 'CURRENCY:JPYKRW', name: 'JPY/KRW', kind: 'fx', currency: 'JPY'});
  const CODE_MAP = new Map(FIXED.map(item => [item.code, item]));

  function fail() { throw new Error('INVALID'); }
  function safe(fn) { return function (...args) { try { return fn(...args); } catch (_) { fail(); } }; }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function instant(value) {
    const timestamp = value === undefined ? Date.now() : typeof value === 'number' ? value : Date.parse(value);
    if (!Number.isFinite(timestamp) || timestamp < Date.UTC(1970, 0, 1)) fail();
    return timestamp;
  }
  function price(value) {
    if (!['number', 'string'].includes(typeof value)) return null;
    const text = String(value).trim();
    if (!/^(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(text)) return null;
    const number = Number(text);
    if (!Number.isFinite(number) || number <= 0 || number >= 1e15) return null;
    // Preserve decimal strings; expand numeric/scientific inputs without silently rounding small values to zero.
    const parts = text.toLowerCase().split('e'), decimal = parts[0].split('.');
    let digits = (decimal[0] || '0') + (decimal[1] || ''), point = (decimal[0] || '0').length + Number(parts[1] || 0);
    if (point < -12 || point > 15 || digits.length > 128) return null;
    let normalized = point <= 0 ? '0.' + '0'.repeat(-point) + digits
      : point >= digits.length ? digits + '0'.repeat(point - digits.length) : digits.slice(0, point) + '.' + digits.slice(point);
    normalized = normalized.replace(/^0+(?=\d)/, '').replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
    if (!/^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/.test(normalized) || Number(normalized) <= 0) return null;
    return normalized;
  }
  function validWall(fields) {
    const [year, month, day, hour, minute, second, millisecond] = fields;
    if (!fields.every(Number.isInteger) || year < 1970 || year > 9999 || month < 1 || month > 12
      || day < 1 || day > new Date(Date.UTC(year, month, 0)).getUTCDate()
      || hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59
      || millisecond < 0 || millisecond > 999) return false;
    return true;
  }
  function wallMillis(fields) { return Date.UTC(fields[0], fields[1] - 1, ...fields.slice(2)); }
  function localInstant(fields, timeZone) {
    if (!validWall(fields) || !timeZone) return null;
    const format = new Intl.DateTimeFormat('en-US', {timeZone, hourCycle: 'h23', year: 'numeric', month: '2-digit',
      day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'});
    const wall = wallMillis(fields);
    function at(timestamp) {
      const parts = Object.fromEntries(format.formatToParts(new Date(timestamp)).filter(part => part.type !== 'literal').map(part => [part.type, Number(part.value)]));
      return [parts.year, parts.month, parts.day, parts.hour, parts.minute, parts.second, ((timestamp % 1000) + 1000) % 1000];
    }
    const offsets = new Set([-36, -12, 0, 12, 36].map(hours => {
      const timestamp = wall + hours * 3600000; return wallMillis(at(timestamp)) - timestamp;
    }));
    const candidates = [...offsets].map(offset => wall - offset).filter(timestamp => at(timestamp).every((value, index) => value === fields[index]));
    return candidates.length === 1 ? candidates[0] : null;
  }
  function tradeInstant(value, timeZone) {
    if (typeof value === 'number' || (typeof value === 'string' && /^\d+(?:\.\d+)?$/.test(value.trim()))) {
      const serial = Number(value), surrogate = new Date(SERIAL_EPOCH + Math.round(serial * DAY));
      if (!Number.isFinite(serial) || serial <= 0 || !Number.isFinite(surrogate.getTime())) return null;
      return localInstant([surrogate.getUTCFullYear(), surrogate.getUTCMonth() + 1, surrogate.getUTCDate(),
        surrogate.getUTCHours(), surrogate.getUTCMinutes(), surrogate.getUTCSeconds(), surrogate.getUTCMilliseconds()], timeZone);
    }
    if (typeof value !== 'string') return null;
    const text = value.trim();
    const iso = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})?$/.exec(text);
    if (iso) {
      const fields = iso.slice(1, 7).map(Number).concat(Number((iso[7] || '').padEnd(3, '0')));
      if (!validWall(fields)) return null;
      if (!iso[8]) return localInstant(fields, timeZone);
      if (iso[8] !== 'Z' && (Number(iso[8].slice(1, 3)) > 23 || Number(iso[8].slice(4)) > 59)) return null;
      const timestamp = Date.parse(text); return Number.isFinite(timestamp) ? timestamp : null;
    }
    const korean = /^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s+(오전|오후)\s+(\d{1,2}):(\d{2}):(\d{2})$/.exec(text);
    if (!korean || Number(korean[5]) < 1 || Number(korean[5]) > 12) return null;
    return localInstant([Number(korean[1]), Number(korean[2]), Number(korean[3]),
      Number(korean[5]) % 12 + (korean[4] === '오후' ? 12 : 0), Number(korean[6]), Number(korean[7]), 0], timeZone);
  }
  function timing(value, mapping, fetchedAt) {
    let parsed = null;
    try { parsed = tradeInstant(value, mapping.timeZone); } catch (_) { /* Unknown local times never become guessed timestamps. */ }
    const known = parsed !== null && parsed >= Date.UTC(1970, 0, 1) && parsed <= fetchedAt;
    return {as_of: new Date(known ? parsed : fetchedAt).toISOString(), available_at: new Date(fetchedAt).toISOString(),
      source: 'GOOGLEFINANCE', time_status: known ? 'KNOWN' : mapping.kind === 'fx' ? 'FX_UNKNOWN' : 'UNKNOWN'};
  }
  function parseValues(values, catalog, options = {}) {
    if (!market || !Array.isArray(values) || values.length > 1000) fail();
    const fetchedAt = instant(options.now); market.emptyMarket(catalog, fetchedAt);
    const catalogMap = new Map(catalog.instruments.map(instrument => [market.canonical(instrument.security_reference), instrument]));
    const rows = new Map(), result = {quotes: [], fx: [], successes: [], failures: [], warnings: []};
    for (const row of values) {
      if (!Array.isArray(row) || row.length > 3) fail();
      if (!row.length || row.every(value => value === '' || value === null || value === undefined)) continue;
      if (row.length === 3 && row.map(value => String(value).trim().toLowerCase()).join('|') === 'code|price|tradetime') continue;
      const code = typeof row[0] === 'string' ? row[0].trim() : '';
      if (!CODE_MAP.has(code)) { result.warnings.push('UNKNOWN_CODE_IGNORED'); continue; }
      if (!rows.has(code)) rows.set(code, []); rows.get(code).push(row);
    }
    for (const [code, observations] of rows) {
      const mapping = CODE_MAP.get(code), instrument = mapping.kind === 'quote' ? catalogMap.get(market.canonical(mapping.security_reference)) : null;
      const name = instrument && instrument.currency === mapping.currency ? instrument.label : mapping.name;
      const identity = {code, name};
      const numeric = observations.length === 1 ? price(observations[0][1]) : null;
      if (observations.length > 1) result.warnings.push('DUPLICATE_CODE_NOT_AVAILABLE');
      if (numeric === null || (mapping.kind === 'quote' && (!instrument || instrument.currency !== mapping.currency))) {
        result.failures.push({...identity, state: 'NOT_AVAILABLE'}); continue;
      }
      const observation = timing(observations[0][2], mapping, fetchedAt);
      if (mapping.kind === 'quote') result.quotes.push({security_reference: clone(mapping.security_reference), price: numeric, currency: mapping.currency, ...observation});
      else result.fx.push({currency: mapping.currency, rate: numeric, ...observation});
      result.successes.push(identity);
    }
    return result;
  }
  function pasteRows(text) {
    if (typeof text !== 'string' || text.length > 100000) fail();
    const separator = text.includes('\t') ? '\t' : ',', rows = [];
    let row = [], field = '', quoted = false, afterQuote = false;
    function finishField() { row.push(field); field = ''; afterQuote = false; }
    function finishRow() { finishField(); if (row.some(value => value !== '')) rows.push(row); row = []; }
    for (let index = 0; index < text.length; index++) {
      const char = text[index];
      if (quoted) {
        if (char === '"' && text[index + 1] === '"') { field += '"'; index++; }
        else if (char === '"') { quoted = false; afterQuote = true; }
        else field += char;
      } else if (char === separator) finishField();
      else if (char === '\n' || char === '\r') { if (char === '\r' && text[index + 1] === '\n') index++; finishRow(); }
      else if (char === '"' && !field && !afterQuote) quoted = true;
      else { if (afterQuote || char === '"') fail(); field += char; }
    }
    if (quoted) fail(); finishRow(); return rows;
  }
  function parsePaste(text, catalog, options = {}) { return parseValues(pasteRows(text), catalog, options); }
  function apply(catalog, previous, result, now) {
    const current = instant(now), old = previous === null || previous === undefined ? market.emptyMarket(catalog, current) : market.validateMarket(previous, catalog, {now: current});
    if (!result || !Array.isArray(result.quotes) || !Array.isArray(result.fx)) fail();
    // Validate the imported observations separately so malformed duplicates cannot hide behind map merging.
    market.makeMarket(catalog, result.quotes, result.fx, null, current);
    const quotes = new Map(old.quotes.map(quote => [market.canonical(quote.security_reference), quote]));
    const rates = new Map(old.fx.map(rate => [rate.currency, rate]));
    for (const quote of result.quotes) quotes.set(market.canonical(quote.security_reference), quote);
    for (const rate of result.fx) rates.set(rate.currency, rate);
    return market.makeMarket(catalog, [...quotes.values()], [...rates.values()], previous || null, current);
  }
  return Object.freeze({parseValues: safe(parseValues), parsePaste: safe(parsePaste), apply: safe(apply)});
});
