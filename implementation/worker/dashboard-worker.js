// Paste this complete module in the dashboard. Limits are best-effort per isolate.
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

export function createHandler({ fetch: fetchImpl = globalThis.fetch, now = Date.now, setTimeout: schedule = globalThis.setTimeout, clearTimeout: cancel = globalThis.clearTimeout } = {}) {
  let rateState; // Numeric request times and leases only; reset on isolate restart.

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
    // This synchronous critical section has no await: admissions cannot interleave.
    try {
      const cap = env.REQUESTS_PER_MINUTE === undefined ? 12 : positiveInteger(env.REQUESTS_PER_MINUTE);
      const readAt = now();
      if (cap === null || cap > 12 || !Number.isSafeInteger(readAt) || readAt < 0
        || readAt > Number.MAX_SAFE_INTEGER - WINDOW_MS) throw new Error();
      const record = rateRecord(rateState, readAt);
      if (record.activeLease && record.leaseUntil <= readAt) { record.activeLease = 0; record.leaseUntil = 0; }
      const last = record.times.at(-1);
      const waitUntil = Math.max(
        record.activeLease ? record.leaseUntil : readAt,
        last === undefined ? readAt : last + MIN_SPACING_MS,
        record.times.length >= cap ? record.times[0] + WINDOW_MS : readAt,
      );
      rateState = record;
      if (waitUntil > readAt) return { denied: true, retryAfter: Math.max(1, Math.ceil((waitUntil - readAt) / 1000)) };
      record.nextLease = record.nextLease >= Number.MAX_SAFE_INTEGER ? 1 : record.nextLease + 1;
      record.activeLease = record.nextLease;
      record.leaseUntil = readAt + LEASE_MS;
      record.times.push(readAt);
      return { lease: record.activeLease };
    } catch { throw new Failure('RATE_LIMIT_UNAVAILABLE', 503); }
  }

  function release(lease) {
    // A late completion must not unlock a newer admission after lease expiry.
    if (rateState?.activeLease === lease) { rateState.activeLease = 0; rateState.leaseUntil = 0; }
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
        const result = await history(symbol, range);
        response = new Response(JSON.stringify(result), { status: 200, headers: headers(origin) });
      } catch (error) { response = failureResponse(error instanceof Failure ? error : new Failure('YAHOO_UNAVAILABLE', 503), origin); }
      finally { release(admission.lease); }
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

const handle = createHandler();
export default { fetch(request, env) { return handle(request, env); } };
