// One module supports both Wrangler and the Cloudflare dashboard editor.
const ORIGIN = 'https://kco994553-star.github.io';
const TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo';
const YAHOO_ROOT = 'https://query1.finance.yahoo.com/v8/finance/chart/';
const US_SYMBOLS = ['ASML', 'LRCX', 'KLAC', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MSFT', 'GOOGL', 'AMZN', 'RTX', 'SYK', 'ETN', 'HUBB', 'GEV', 'ROK'];
const MARKETS = new Map(US_SYMBOLS.map((symbol) => [symbol, { currency: 'USD', timezone: 'America/New_York' }]));
MARKETS.set('042700.KS', { currency: 'KRW', timezone: 'Asia/Seoul' });
MARKETS.set('8035.T', { currency: 'JPY', timezone: 'Asia/Tokyo' });
const RANGES = new Set(['1mo', '3mo', '6mo', '1y', '2y', '5y']);
const MAX_BODY_BYTES = 512 * 1024;
const MAX_BARS = 1500;
const MIN_SPACING_MS = 5000;
const WINDOW_MS = 60_000;
const LEASE_MS = 30_000;
const NO_CACHE = { cache: 'no-store', cf: { cacheTtl: 0, cacheEverything: false }, redirect: 'error' };

class Failure extends Error {
  constructor(code, status) { super(code); this.code = code; this.status = status; }
}

async function closeAndFail(response, code, status) {
  try { await response.body?.cancel(); } catch { /* Return only the fixed error. */ }
  throw new Failure(code, status);
}

function headers(origin) {
  const result = new Headers({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'private, no-store, max-age=0',
    'Vary': 'Origin',
    'X-Content-Type-Options': 'nosniff',
  });
  if (origin === ORIGIN) result.set('Access-Control-Allow-Origin', ORIGIN);
  return result;
}

function failureResponse(error, origin, extraHeaders = {}) {
  const responseHeaders = headers(origin);
  for (const [key, value] of Object.entries(extraHeaders)) responseHeaders.set(key, value);
  return new Response(JSON.stringify({ error: { code: error.code } }), { status: error.status, headers: responseHeaders });
}

function positiveInteger(value) {
  const number = typeof value === 'number' ? value : typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : NaN;
  return Number.isSafeInteger(number) && number > 0 ? number : null;
}

function validateQuery(url) {
  // Reject alternate encodings, empty fields, duplicates, and every extra parameter.
  if (url.hash || !/^\?(?:symbol=[A-Z0-9.]+&range=[a-z0-9]+|range=[a-z0-9]+&symbol=[A-Z0-9.]+)$/.test(url.search)) {
    throw new Failure('REQUEST_INVALID', 400);
  }
  const symbol = url.searchParams.get('symbol');
  const range = url.searchParams.get('range');
  if (!MARKETS.has(symbol) || !RANGES.has(range)) throw new Failure('REQUEST_INVALID', 400);
  return { symbol, range };
}

async function readJson(response, limit, invalidCode, oversizedCode, status) {
  const advertised = response.headers.get('Content-Length');
  if (advertised && /^\d+$/.test(advertised) && Number(advertised) > limit) {
    await response.body?.cancel();
    throw new Failure(oversizedCode, status);
  }
  if (!response.body) throw new Failure(invalidCode, status);
  const reader = response.body.getReader();
  const chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > limit) {
        await reader.cancel();
        throw new Failure(oversizedCode, status);
      }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new Failure(invalidCode, status); }
}

function sessionStatus(timestamp, regular, readAt) {
  if (!regular || !Number.isSafeInteger(regular.start) || !Number.isSafeInteger(regular.end)
    || regular.start <= 0 || regular.end <= regular.start || regular.end - regular.start > 86400) return 'UNKNOWN';
  const nowSeconds = Math.floor(readAt / 1000);
  if (timestamp > nowSeconds || timestamp >= regular.end) return 'UNKNOWN';
  if (timestamp < regular.start || nowSeconds >= regular.end) return 'COMPLETE';
  return nowSeconds >= regular.start ? 'IN_PROGRESS' : 'UNKNOWN';
}

function normalizeHistory(payload, symbol, range, readAt) {
  const invalid = () => { throw new Failure('YAHOO_FORMAT_CHANGED', 502); };
  const unavailable = () => { throw new Failure('HISTORY_UNAVAILABLE', 404); };
  const chart = payload?.chart;
  if (!chart || typeof chart !== 'object' || Array.isArray(chart)) invalid();
  if (chart.error != null || chart.result === null || (Array.isArray(chart.result) && chart.result.length === 0)) unavailable();
  if (!Array.isArray(chart.result) || chart.result.length !== 1) invalid();
  const result = chart.result[0];
  const meta = result?.meta;
  const market = MARKETS.get(symbol);
  if (!meta || meta.symbol !== symbol || meta.currency !== market.currency || meta.exchangeTimezoneName !== market.timezone
    || typeof meta.exchangeName !== 'string' || !/^[A-Za-z0-9._ -]{1,40}$/.test(meta.exchangeName)
    || meta.dataGranularity !== '1d') invalid();
  const timestamps = result.timestamp;
  if (!Array.isArray(timestamps)) invalid();
  if (timestamps.length === 0) unavailable();
  if (timestamps.length > MAX_BARS) throw new Failure('YAHOO_TOO_LARGE', 502);
  const quotes = result.indicators?.quote;
  if (!Array.isArray(quotes) || quotes.length !== 1 || !quotes[0] || typeof quotes[0] !== 'object') invalid();
  const quote = quotes[0];
  for (const key of ['open', 'high', 'low', 'close', 'volume']) {
    if (!Array.isArray(quote[key]) || quote[key].length !== timestamps.length) invalid();
  }
  let adjusted = null;
  if (result.indicators.adjclose !== undefined) {
    const series = result.indicators.adjclose;
    if (!Array.isArray(series) || series.length !== 1 || !Array.isArray(series[0]?.adjclose) || series[0].adjclose.length !== timestamps.length) invalid();
    adjusted = series[0].adjclose;
  }
  let previous = 0, hasClose = false;
  const price = (value) => {
    if (value === null) return null;
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) invalid();
    return value;
  };
  const volume = (value) => {
    if (value === null) return null;
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) invalid();
    return value;
  };
  const bars = timestamps.map((timestamp, index) => {
    if (!Number.isSafeInteger(timestamp) || timestamp <= previous || timestamp > Math.floor(readAt / 1000)) invalid();
    previous = timestamp;
    const close = price(quote.close[index]);
    hasClose ||= close !== null;
    return {
      timestamp, open: price(quote.open[index]), high: price(quote.high[index]), low: price(quote.low[index]), close,
      adjusted_close: adjusted ? price(adjusted[index]) : null, volume: volume(quote.volume[index]),
      session_status: sessionStatus(timestamp, meta.currentTradingPeriod?.regular, readAt),
    };
  });
  if (!hasClose) unavailable();
  return {
    schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol, range, currency: market.currency,
    exchange: meta.exchangeName, timezone: market.timezone, interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN',
    read_at: new Date(readAt).toISOString(), bars,
  };
}

// Provider dates are session labels, not intraday execution timestamps.
function calendarDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const time = Date.parse(value + 'T00:00:00Z');
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? value : null;
}

function localDate(time, timezone) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(time);
  const get = (name) => parts.find((p) => p.type === name).value;
  return get('year') + '-' + get('month') + '-' + get('day');
}

function dateWindow(range, readAt, timezone) {
  const end = localDate(readAt, timezone), date = new Date(end + 'T00:00:00Z'), day = date.getUTCDate();
  date.setUTCDate(1);
  date.setUTCMonth(date.getUTCMonth() - ({ '1mo': 1, '3mo': 3, '6mo': 6, '1y': 12, '2y': 24, '5y': 60 })[range]);
  const last = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
  date.setUTCDate(Math.min(day, last));
  return { start: date.toISOString().slice(0, 10), end };
}

function fallbackBar(row, day, end, code, adjusted = null) {
  const invalid = () => { throw new Failure(code, 502); };
  const fields = ['open', 'high', 'low', 'close'];
  if (!calendarDate(day) || !fields.every((k) => typeof row[k] === 'number' && Number.isFinite(row[k]) && row[k] > 0)
    || row.low > Math.min(row.open, row.close) || row.high < Math.max(row.open, row.close) || row.low > row.high
    || typeof row.volume !== 'number' || !Number.isFinite(row.volume) || row.volume < 0
    || (adjusted !== null && (typeof adjusted !== 'number' || !Number.isFinite(adjusted) || adjusted <= 0))) invalid();
  return { timestamp: Date.parse(day + 'T00:00:00Z') / 1000, session_date: day,
    open: row.open, high: row.high, low: row.low, close: row.close, adjusted_close: adjusted, volume: row.volume,
    session_status: day < end ? 'COMPLETE' : 'UNKNOWN' };
}

function fallbackResult(provider, symbol, range, readAt, exchange, bars) {
  if (!bars.length) throw new Failure('HISTORY_UNAVAILABLE', 404);
  const market = MARKETS.get(symbol);
  return { schema: 'private-history/1', provider, symbol, range, currency: market.currency, exchange,
    timezone: market.timezone, interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN',
    timestamp_kind: 'PROVIDER_SESSION_LABEL', read_at: new Date(readAt).toISOString(), bars };
}

function providerSecret(env, name) {
  const value = env[name];
  return typeof value === 'string' && /^[\x21-\x7e]{1,4096}$/.test(value) ? value : null;
}

function krxNumber(value) {
  if (typeof value !== 'string' || !/^(?:\d+|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d+)?$/.test(value)) throw new Failure('KRX_FORMAT_CHANGED', 502);
  const result = Number(value.replaceAll(',', ''));
  if (!Number.isFinite(result)) throw new Failure('KRX_FORMAT_CHANGED', 502);
  return result;
}

export function createHandler({ fetch: fetchImpl = globalThis.fetch, now = Date.now, setTimeout: schedule = globalThis.setTimeout, clearTimeout: cancel = globalThis.clearTimeout } = {}) {
  async function timed(milliseconds, code, status, operation) {
    const controller = new AbortController();
    let timer;
    const deadline = new Promise((_, reject) => {
      timer = schedule(() => { controller.abort(); reject(new Failure(code, status)); }, milliseconds);
    });
    try { return await Promise.race([operation(controller.signal), deadline]); }
    finally { cancel(timer); }
  }

  async function authenticate(request, env) {
    if (typeof env.ALLOWED_EMAIL !== 'string' || !env.ALLOWED_EMAIL || env.ALLOWED_EMAIL.trim() !== env.ALLOWED_EMAIL
      || typeof env.GOOGLE_CLIENT_ID !== 'string' || !env.GOOGLE_CLIENT_ID || env.GOOGLE_CLIENT_ID.trim() !== env.GOOGLE_CLIENT_ID) throw new Failure('CONFIG_UNAVAILABLE', 503);
    const authorization = request.headers.get('Authorization');
    if (!authorization || authorization.length > 8192 || !/^Bearer [A-Za-z0-9._~+\/-]+=*$/i.test(authorization)) throw new Failure('AUTH_FORBIDDEN', 403);
    let info;
    try {
      info = await timed(5000, 'AUTH_UNAVAILABLE', 503, async (signal) => {
        const response = await fetchImpl(TOKENINFO_URL, {
          ...NO_CACHE, method: 'POST', signal,
          headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', Authorization: authorization },
        });
        if ([400, 401, 403].includes(response.status)) return closeAndFail(response, 'AUTH_FORBIDDEN', 403);
        if (!response.ok) return closeAndFail(response, 'AUTH_UNAVAILABLE', 503);
        return readJson(response, 32 * 1024, 'AUTH_UNAVAILABLE', 'AUTH_UNAVAILABLE', 503);
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure('AUTH_UNAVAILABLE', 503);
    }
    if (!info || info.aud !== env.GOOGLE_CLIENT_ID || info.email !== env.ALLOWED_EMAIL
      || ![true, 'true'].includes(info.email_verified) || positiveInteger(info.expires_in) === null
      || (Object.hasOwn(info, 'exp') && (positiveInteger(info.exp) === null || Number(info.exp) <= Math.floor(now() / 1000)))) throw new Failure('AUTH_FORBIDDEN', 403);
  }

  async function admit(env) {
    try {
      const namespace = env.HISTORY_RATE_LIMITER;
      const stub = namespace.get(namespace.idFromName('history-owner-v1'));
      const { status, result } = await timed(2000, 'RATE_LIMIT_UNAVAILABLE', 503, async (signal) => {
        const response = await stub.fetch('https://history-rate.internal/admit', { method: 'POST', signal });
        return { status: response.status, result: await response.json() };
      });
      if (status === 429 && result.allowed === false && positiveInteger(result.retry_after) !== null) {
        return { denied: true, retryAfter: result.retry_after };
      }
      if (status !== 200 || result.allowed !== true || positiveInteger(result.lease) === null) throw new Error();
      return { stub, lease: result.lease };
    } catch { throw new Failure('RATE_LIMIT_UNAVAILABLE', 503); }
  }

  async function history(symbol, range) {
    try {
      return await timed(10_000, 'YAHOO_TIMEOUT', 504, async (signal) => {
        const response = await fetchImpl(`${YAHOO_ROOT}${symbol}?interval=1d&range=${range}`, {
          ...NO_CACHE, method: 'GET', signal, headers: { Accept: 'application/json' },
        });
        if ([401, 403, 429].includes(response.status)) return closeAndFail(response, 'YAHOO_BLOCKED', 502);
        if (response.status === 404) return closeAndFail(response, 'HISTORY_UNAVAILABLE', 404);
        if (!response.ok) return closeAndFail(response, 'YAHOO_UNAVAILABLE', 503);
        const payload = await readJson(response, MAX_BODY_BYTES, 'YAHOO_FORMAT_CHANGED', 'YAHOO_TOO_LARGE', 502);
        return normalizeHistory(payload, symbol, range, now());
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure('YAHOO_UNAVAILABLE', 503);
    }
  }

  async function fallbackHistory(symbol, range, env, yahooError) {
    const provider = US_SYMBOLS.includes(symbol) ? 'TIINGO' : symbol === '042700.KS' ? 'KRX' : null;
    const secret = provider && providerSecret(env, provider + '_API_KEY');
    // Existing installs remain Yahoo-only until the corresponding Secret is set.
    if (!secret || !yahooError || !(yahooError.code.startsWith('YAHOO_') || yahooError.code === 'HISTORY_UNAVAILABLE')) throw yahooError;
    if (provider === 'KRX' && range !== '1mo') throw new Failure('KRX_RANGE_UNSUPPORTED', 422);
    const readAt = now(), window = dateWindow(range, readAt, MARKETS.get(symbol).timezone);
    try {
      return await timed(15_000, provider + '_TIMEOUT', 504, async (signal) => {
        const request = async (url, limit = MAX_BODY_BYTES) => {
          if (signal.aborted) throw new Failure(provider + '_TIMEOUT', 504);
          const response = await fetchImpl(url, { ...NO_CACHE, method: 'GET', signal,
            headers: provider === 'TIINGO' ? { Accept: 'application/json', Authorization: 'Token ' + secret } : { Accept: 'application/json', AUTH_KEY: secret } });
          if (!response.ok) return closeAndFail(response, provider + '_UNAVAILABLE', 503);
          return readJson(response, limit, provider + '_FORMAT_CHANGED', provider + '_TOO_LARGE', 502);
        };
        if (provider === 'TIINGO') {
          const root = 'https://api.tiingo.com/tiingo/daily/' + symbol.toLowerCase();
          const meta = await request(root, 32 * 1024);
          if (!meta || typeof meta.ticker !== 'string' || meta.ticker.toUpperCase() !== symbol
            || !['NASDAQ', 'NYSE', 'NYSE ARCA', 'NYSE MKT', 'BATS'].includes(meta.exchangeCode)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
          const rows = await request(root + '/prices?startDate=' + window.start + '&endDate=' + window.end + '&resampleFreq=daily');
          if (!Array.isArray(rows)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
          if (rows.length > MAX_BARS) throw new Failure('TIINGO_TOO_LARGE', 502);
          let previous = '';
          const bars = rows.map((row) => {
            if (!row || typeof row.date !== 'string' || !/^\d{4}-\d{2}-\d{2}T00:00:00(?:\.000)?Z$/.test(row.date)) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
            const day = row.date.slice(0, 10);
            if (day <= previous || day < window.start || day > window.end) throw new Failure('TIINGO_FORMAT_CHANGED', 502);
            previous = day;
            return fallbackBar(row, day, window.end, 'TIINGO_FORMAT_CHANGED', row.adjClose === undefined ? null : row.adjClose);
          });
          return fallbackResult('Tiingo EOD', symbol, range, readAt, meta.exchangeCode, bars);
        }
        const bars = [], start = Date.parse(window.start + 'T00:00:00Z'), end = Date.parse(window.end + 'T00:00:00Z');
        // One market-wide response per calendar day. No long-range truncation or cache.
        if ((end - start) / 86400000 + 1 > 32) throw new Failure('KRX_RANGE_UNSUPPORTED', 422);
        for (let time = start; time <= end; time += 86400000) {
          const date = new Date(time);
          if ([0, 6].includes(date.getUTCDay())) continue;
          const day = date.toISOString().slice(0, 10), compact = day.replaceAll('-', '');
          const payload = await request('https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd?basDd=' + compact, 1024 * 1024);
          if (!payload || !Array.isArray(payload.OutBlock_1) || payload.OutBlock_1.length > 5000) throw new Failure('KRX_FORMAT_CHANGED', 502);
          const rows = payload.OutBlock_1.filter((row) => row && row.ISU_CD === '042700');
          if (rows.length > 1) throw new Failure('KRX_FORMAT_CHANGED', 502);
          if (!rows.length) continue; // Holidays and missing listings remain absent.
          const row = rows[0];
          if (row.BAS_DD !== compact || row.MKT_NM !== 'KOSPI') throw new Failure('KRX_FORMAT_CHANGED', 502);
          bars.push(fallbackBar({ open: krxNumber(row.TDD_OPNPRC), high: krxNumber(row.TDD_HGPRC), low: krxNumber(row.TDD_LWPRC),
            close: krxNumber(row.TDD_CLSPRC), volume: krxNumber(row.ACC_TRDVOL) }, day, window.end, 'KRX_FORMAT_CHANGED'));
        }
        return fallbackResult('KRX OPEN API', symbol, range, readAt, 'KOSPI', bars);
      });
    } catch (error) {
      if (error instanceof Failure) throw error;
      throw new Failure(provider + '_UNAVAILABLE', 503);
    }
  }

  return async function handle(request, env) {
    const origin = request.headers.get('Origin');
    if (origin !== ORIGIN) return failureResponse(new Failure('ORIGIN_FORBIDDEN', 403));
    try {
      const url = new URL(request.url);
      if (url.pathname !== '/history') throw new Failure('ROUTE_NOT_FOUND', 404);
      if (!['GET', 'OPTIONS'].includes(request.method)) throw new Failure('METHOD_NOT_ALLOWED', 405);
      const { symbol, range } = validateQuery(url);
      if (request.method === 'OPTIONS') {
        if (request.headers.get('Access-Control-Request-Method') !== 'GET'
          || request.headers.get('Access-Control-Request-Headers')?.trim().toLowerCase() !== 'authorization') throw new Failure('REQUEST_INVALID', 400);
        const responseHeaders = headers(origin);
        responseHeaders.delete('Content-Type');
        responseHeaders.set('Access-Control-Allow-Methods', 'GET');
        responseHeaders.set('Access-Control-Allow-Headers', 'Authorization');
        responseHeaders.set('Access-Control-Max-Age', '0');
        return new Response(null, { status: 204, headers: responseHeaders });
      }
      await authenticate(request, env);
      const admission = await admit(env);
      if (admission.denied) return failureResponse(new Failure('RATE_LIMITED', 429), origin, { 'Retry-After': String(admission.retryAfter) });
      let response;
      try {
        let result;
        try { result = await history(symbol, range); }
        catch (error) { result = await fallbackHistory(symbol, range, env, error); }
        response = new Response(JSON.stringify(result), { status: 200, headers: headers(origin) });
      } catch (error) { response = failureResponse(error instanceof Failure ? error : new Failure('YAHOO_UNAVAILABLE', 503), origin); }
      finally {
        try {
          await timed(2000, 'RATE_LIMIT_UNAVAILABLE', 503, async (signal) => {
            const released = await admission.stub.fetch('https://history-rate.internal/release', {
              method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ lease: admission.lease }),
            });
            if (released.status !== 204) throw new Error();
          });
        } catch { response = failureResponse(new Failure('RATE_LIMIT_UNAVAILABLE', 503), origin); }
      }
      return response;
    } catch (error) { return failureResponse(error instanceof Failure ? error : new Failure('CONFIG_UNAVAILABLE', 503), origin); }
  };
}

function rateRecord(value, now) {
  if (value === undefined) return { times: [], activeLease: 0, leaseUntil: 0, nextLease: 0 };
  if (!value || typeof value !== 'object' || Array.isArray(value)
    || Object.keys(value).sort().join(',') !== 'activeLease,leaseUntil,nextLease,times'
    || !Array.isArray(value.times) || value.times.length > 12
    || !value.times.every((time, index) => Number.isSafeInteger(time) && time >= 0 && time <= now && (index === 0 || time > value.times[index - 1]))
    || !['activeLease', 'leaseUntil', 'nextLease'].every((key) => Number.isSafeInteger(value[key]) && value[key] >= 0)
    || value.activeLease > value.nextLease) throw new Error();
  return { ...value, times: value.times.filter((time) => time > now - WINDOW_MS) };
}

// This object stores only request times and numeric lease counters for one owner.
export class HistoryRateLimiter {
  constructor(state, env, { now = Date.now } = {}) { this.storage = state.storage; this.env = env; this.now = now; }

  async fetch(request) {
    const origin = request.headers.get('Origin');
    try {
      const path = new URL(request.url).pathname;
      if (request.method !== 'POST' || !['/admit', '/release'].includes(path)) throw new Error();
      const cap = this.env.REQUESTS_PER_MINUTE === undefined ? 12 : positiveInteger(this.env.REQUESTS_PER_MINUTE);
      if (cap === null || cap > 12) throw new Error();
      let lease;
      if (path === '/release') {
        if (Number(request.headers.get('Content-Length')) > 128) throw new Error();
        const body = await request.text();
        if (body.length > 128) throw new Error();
        const data = JSON.parse(body);
        if (Object.keys(data).length !== 1 || positiveInteger(data.lease) === null) throw new Error();
        lease = data.lease;
      }
      return await this.storage.transaction(async (storage) => {
        const now = this.now();
        if (!Number.isSafeInteger(now) || now < 0) throw new Error();
        const record = rateRecord(await storage.get('rate'), now);
        if (record.activeLease && record.leaseUntil <= now) { record.activeLease = 0; record.leaseUntil = 0; }
        if (path === '/release') {
          if (record.activeLease === lease) { record.activeLease = 0; record.leaseUntil = 0; }
          await storage.put('rate', record);
          return new Response(null, { status: 204, headers: headers(origin) });
        }
        const last = record.times.at(-1);
        const waitUntil = Math.max(
          record.activeLease ? record.leaseUntil : now,
          last === undefined ? now : last + MIN_SPACING_MS,
          record.times.length >= cap ? record.times[0] + WINDOW_MS : now,
        );
        if (waitUntil > now) {
          await storage.put('rate', record);
          return new Response(JSON.stringify({ allowed: false, retry_after: Math.max(1, Math.ceil((waitUntil - now) / 1000)) }), { status: 429, headers: headers(origin) });
        }
        record.nextLease = record.nextLease >= Number.MAX_SAFE_INTEGER ? 1 : record.nextLease + 1;
        record.activeLease = record.nextLease;
        record.leaseUntil = now + LEASE_MS;
        record.times.push(now);
        await storage.put('rate', record);
        return new Response(JSON.stringify({ allowed: true, lease: record.activeLease }), { status: 200, headers: headers(origin) });
      });
    } catch { return failureResponse(new Failure('RATE_LIMIT_UNAVAILABLE', 503), origin); }
  }
}

const handle = createHandler();
export default { fetch(request, env) { return handle(request, env); } };
