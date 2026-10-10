import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

globalThis.fetch = async () => { throw new Error('Live network transport is disabled in these tests'); };

const module = await import('../dashboard-worker.js');
const { createHandler } = module;
const ORIGIN = 'https://kco994553-star.github.io';
const NOW = Date.UTC(2026, 9, 9, 18);
const SYMBOLS = ['ASML', 'LRCX', 'KLAC', 'NVDA', 'AMD', 'AVGO', 'QCOM', 'INTC', 'MSFT', 'GOOGL', 'AMZN', 'RTX', 'SYK', 'ETN', 'HUBB', 'GEV', 'ROK', '042700.KS', '8035.T'];
const RANGES = ['1mo', '3mo', '6mo', '1y', '2y', '5y'];
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
const clone = (value) => structuredClone(value);

function fixture(symbol = 'ASML') {
  const current = Math.floor(NOW / 1000);
  return {
    chart: {
      result: [{
        meta: {
          symbol, currency: symbol.endsWith('.KS') ? 'KRW' : symbol.endsWith('.T') ? 'JPY' : 'USD',
          exchangeName: symbol.endsWith('.KS') ? 'KSC' : symbol.endsWith('.T') ? 'JPX' : 'NMS',
          exchangeTimezoneName: symbol.endsWith('.KS') ? 'Asia/Seoul' : symbol.endsWith('.T') ? 'Asia/Tokyo' : 'America/New_York', dataGranularity: '1d',
          currentTradingPeriod: { regular: { start: current - 7200, end: current + 3600 } },
          regularMarketPrice: 999999,
        },
        timestamp: [current - 86400, current - 7200],
        indicators: {
          quote: [{ open: [100, null], high: [104, 106], low: [98, null], close: [101, 105], volume: [0, 50] }],
          adjclose: [{ adjclose: [99, 103] }],
        },
      }],
      error: null,
    },
  };
}

function setup(options = {}) {
  const clock = options.clock ?? { now: NOW };
  const calls = [];
  const env = { ALLOWED_EMAIL: 'owner@example.test', GOOGLE_CLIENT_ID: 'mock-client-id', ...options.rateEnv, ...options.env };
  const fetch = async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    if (url === 'https://oauth2.googleapis.com/tokeninfo') {
      if (options.authFetch) return options.authFetch(input, init);
      return json({ aud: env.GOOGLE_CLIENT_ID, email: env.ALLOWED_EMAIL, email_verified: true, expires_in: '3600', ...options.token });
    }
    assert.ok(url.startsWith('https://query1.finance.yahoo.com/v8/finance/chart/'), 'all fetches have a fixed upstream host');
    if (options.yahooFetch) return options.yahooFetch(input, init);
    const symbol = decodeURIComponent(new URL(url).pathname.split('/').at(-1));
    return json(options.yahoo ?? fixture(symbol));
  };
  const handler = createHandler({ fetch, now: () => clock.now, ...options.dependencies });
  const request = (path = '/history?symbol=ASML&range=1mo', headers = {}, method = 'GET') => new Request(`https://private-worker.example${path}`, {
    method, headers: { Origin: ORIGIN, Authorization: 'Bearer fake-access-token', ...headers },
  });
  return { handler, env, calls, clock, request, run: (req = request()) => handler(req, env) };
}

async function expectError(response, status, code, origin = ORIGIN) {
  assert.equal(response.status, status);
  assert.deepEqual(await response.json(), { error: { code } });
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store, max-age=0');
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), origin);
}

test('authenticated daily history preserves raw and adjusted closes with explicit nulls', async () => {
  const s = setup();
  const response = await s.run();
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store, max-age=0');
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.deepEqual(await response.json(), {
    schema: 'private-history/1', provider: 'Yahoo Finance(비공식)', symbol: 'ASML', range: '1mo', currency: 'USD',
    exchange: 'NMS', timezone: 'America/New_York', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN',
    read_at: new Date(NOW).toISOString(),
    bars: [
      { timestamp: NOW / 1000 - 86400, open: 100, high: 104, low: 98, close: 101, adjusted_close: 99, volume: 0, session_status: 'COMPLETE' },
      { timestamp: NOW / 1000 - 7200, open: null, high: 106, low: null, close: 105, adjusted_close: 103, volume: 50, session_status: 'IN_PROGRESS' },
    ],
  });
});

for (const symbol of SYMBOLS) {
  test(`allows fixed symbol ${symbol} and its expected currency`, async () => {
    const s = setup();
    const response = await s.run(s.request(`/history?symbol=${symbol}&range=1mo`));
    assert.equal(response.status, 200);
    const data = await response.json();
    assert.equal(data.symbol, symbol);
    assert.equal(data.currency, symbol.endsWith('.KS') ? 'KRW' : symbol.endsWith('.T') ? 'JPY' : 'USD');
    assert.equal(data.timezone, symbol.endsWith('.KS') ? 'Asia/Seoul' : symbol.endsWith('.T') ? 'Asia/Tokyo' : 'America/New_York');
    assert.equal(s.calls[1].url, `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1mo`);
  });
}
for (const range of RANGES) {
  test(`allows daily range ${range}`, async () => {
    const s = setup();
    const response = await s.run(s.request(`/history?symbol=ASML&range=${range}`));
    assert.equal(response.status, 200);
    assert.equal((await response.json()).range, range);
  });
}

for (const [name, token] of [
  ['wrong email', { email: 'someone@example.test' }], ['wrong audience', { aud: 'other-client' }],
  ['array audience', { aud: ['mock-client-id'] }], ['missing email', { email: undefined }],
  ['missing verification', { email_verified: undefined }], ['false verification', { email_verified: false }],
  ['false string verification', { email_verified: 'false' }], ['truthy verification', { email_verified: 1 }],
  ['missing expiry', { expires_in: undefined }], ['zero expiry', { expires_in: 0 }],
  ['negative expiry', { expires_in: '-1' }], ['nonnumeric expiry', { expires_in: '3600junk' }],
  ['expired absolute expiry', { exp: NOW / 1000 }], ['invalid absolute expiry', { exp: null }],
]) {
  test(`fails closed for ${name} before requesting Yahoo`, async () => {
    const s = setup({ token });
    await expectError(await s.run(), 403, 'AUTH_FORBIDDEN');
    assert.equal(s.calls.length, 1);
  });
}
test('accepts verified true string and validates a supplied future absolute expiry', async () => {
  const s = setup({ token: { email_verified: 'true', expires_in: 3600, exp: String(NOW / 1000 + 3600) } });
  assert.equal((await s.run()).status, 200);
});
for (const authorization of ['', 'Basic token', 'Bearer', 'Bearer token with spaces', 'Bearer abc\tdef']) {
  test(`rejects malformed authorization ${JSON.stringify(authorization)} without provider calls`, async () => {
    const s = setup();
    await expectError(await s.run(s.request(undefined, { Authorization: authorization })), 403, 'AUTH_FORBIDDEN');
    assert.equal(s.calls.length, 0);
  });
}
for (const status of [400, 401, 403]) {
  test(`rejects revoked Google token status ${status}`, async () => {
    const s = setup({ authFetch: () => json({ error: 'secret-token-details' }, status) });
    await expectError(await s.run(), 403, 'AUTH_FORBIDDEN');
    assert.equal(s.calls.length, 1);
  });
}
for (const status of [429, 500, 503]) {
  test(`reports fixed auth provider unavailable for status ${status}`, async () => {
    const s = setup({ authFetch: () => json({ error: 'secret-token-details' }, status) });
    await expectError(await s.run(), 503, 'AUTH_UNAVAILABLE');
    assert.equal(s.calls.length, 1);
  });
}
test('auth network failures and malformed JSON reveal no upstream details', async () => {
  for (const authFetch of [() => { throw new Error('secret-token-details'); }, () => new Response('secret-token-details')]) {
    const s = setup({ authFetch });
    await expectError(await s.run(), 503, 'AUTH_UNAVAILABLE');
  }
});
test('Google rejection cancels its response body before returning a fixed auth error', async () => {
  let cancelled = false;
  const stream = new ReadableStream({ cancel() { cancelled = true; } });
  const s = setup({ authFetch: () => new Response(stream, { status: 400 }) });
  await expectError(await s.run(), 403, 'AUTH_FORBIDDEN');
  assert.equal(cancelled, true);
});
test('Google validation uses POST Bearer header without placing the token in a URL or body', async () => {
  const s = setup();
  assert.equal((await s.run()).status, 200);
  const call = s.calls[0];
  assert.equal(call.url, 'https://oauth2.googleapis.com/tokeninfo');
  assert.equal(call.init.method, 'POST');
  assert.equal(new Headers(call.init.headers).get('Authorization'), 'Bearer fake-access-token');
  assert.equal(new Headers(call.init.headers).get('Content-Type'), 'application/x-www-form-urlencoded;charset=UTF-8');
  assert.equal(call.init.body, undefined);
});
test('all upstream fetches bypass caching and redirects; Yahoo receives no bearer or cookie', async () => {
  const s = setup();
  assert.equal((await s.run(s.request(undefined, { Cookie: 'private=secret' }))).status, 200);
  for (const { init } of s.calls) {
    assert.equal(init.cache, 'no-store');
    assert.deepEqual(init.cf, { cacheTtl: 0, cacheEverything: false });
    assert.equal(init.redirect, 'error');
    assert.ok(init.signal instanceof AbortSignal);
  }
  const headers = new Headers(s.calls[1].init.headers);
  assert.equal(headers.get('Authorization'), null);
  assert.equal(headers.get('Cookie'), null);
});

for (const origin of ['https://evil.test', `${ORIGIN}/`, 'null', '']) {
  test(`rejects origin ${JSON.stringify(origin)} without CORS permission or upstream calls`, async () => {
    const s = setup();
    await expectError(await s.run(s.request(undefined, { Origin: origin })), 403, 'ORIGIN_FORBIDDEN', null);
    assert.equal(s.calls.length, 0);
  });
}
test('permits only GET and Authorization in browser preflight', async () => {
  const s = setup();
  const response = await s.run(s.request(undefined, { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization' }, 'OPTIONS'));
  assert.equal(response.status, 204);
  assert.equal(await response.text(), '');
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.equal(response.headers.get('Access-Control-Allow-Methods'), 'GET');
  assert.equal(response.headers.get('Access-Control-Allow-Headers'), 'Authorization');
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store, max-age=0');
  assert.equal(s.calls.length, 0);
});
for (const [method, headers] of [['POST', 'authorization'], ['GET', 'authorization, content-type'], ['GET', 'cookie'], ['GET', 'authorization, authorization'], ['GET', '']]) {
  test(`rejects preflight ${method}/${headers}`, async () => {
    const s = setup();
    await expectError(await s.run(s.request(undefined, { 'Access-Control-Request-Method': method, 'Access-Control-Request-Headers': headers }, 'OPTIONS')), 400, 'REQUEST_INVALID');
    assert.equal(s.calls.length, 0);
  });
}
for (const path of [
  '/history', '/history?symbol=ASML', '/history?symbol=ASML&range=1d', '/history?symbol=AAPL&range=1mo',
  '/history?symbol=asml&range=1mo', '/history?symbol=ASML&range=1mo&url=https://evil.test',
  '/history?symbol=ASML&symbol=NVDA&range=1mo', '/history?symbol=ASML&range=1mo&range=1y',
  '/history?symbol=%41SML&range=1mo', '/history?symbol=ASML%2F..&range=1mo',
  '/history?symbol=https://evil.test&range=1mo', '/history?symbol=ASML+&range=1mo',
  '/history?symbol=ASML&range=1mo&', '/history?symbol=ASML&range=1mo#fragment',
]) {
  test(`rejects noncanonical history query ${path}`, async () => {
    const s = setup();
    await expectError(await s.run(s.request(path)), 400, 'REQUEST_INVALID');
    assert.equal(s.calls.length, 0);
  });
}
test('rejects methods and other endpoints with no upstream calls', async () => {
  const s = setup();
  await expectError(await s.run(s.request('/history?symbol=ASML&range=1mo', {}, 'POST')), 405, 'METHOD_NOT_ALLOWED');
  await expectError(await s.run(s.request('/quote?symbol=ASML')), 404, 'ROUTE_NOT_FOUND');
  await expectError(await s.run(s.request('/leaderboard')), 404, 'ROUTE_NOT_FOUND');
  assert.equal(s.calls.length, 0);
});
test('missing required configuration fails closed without emitting values', async () => {
  for (const env of [{ ALLOWED_EMAIL: '' }, { GOOGLE_CLIENT_ID: '' }]) {
    const s = setup({ env });
    await expectError(await s.run(), 503, 'CONFIG_UNAVAILABLE');
    assert.equal(s.calls.length, 0);
  }
});

test('missing adjusted-close series becomes null without filling from raw close', async () => {
  const yahoo = fixture();
  delete yahoo.chart.result[0].indicators.adjclose;
  const s = setup({ yahoo });
  const response = await s.run();
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).bars.map((bar) => bar.adjusted_close), [null, null]);
});
test('null close remains null when another bar has a valid close', async () => {
  const yahoo = fixture();
  yahoo.chart.result[0].indicators.quote[0].close[0] = null;
  const s = setup({ yahoo });
  const response = await s.run();
  assert.equal(response.status, 200);
  const bars = (await response.json()).bars;
  assert.equal(bars[0].close, null);
  assert.equal(bars[1].close, 105);
});
test('session status stays UNKNOWN without valid provider regular-session evidence', async () => {
  for (const regular of [undefined, { start: 1, end: 0 }, { start: '1', end: '2' }, { start: NOW / 1000 - 7200, end: NOW / 1000 + 3600, fake: true }]) {
    const yahoo = fixture();
    yahoo.chart.result[0].meta.currentTradingPeriod = { regular };
    const s = setup({ yahoo });
    const response = await s.run();
    assert.equal(response.status, 200);
    if (!regular?.fake) assert.deepEqual((await response.json()).bars.map((bar) => bar.session_status), ['UNKNOWN', 'UNKNOWN']);
  }
});
test('provider evidence marks the current bar complete after regular close', async () => {
  const s = setup({ clock: { now: NOW + 7200_000 } });
  const response = await s.run();
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).bars.map((bar) => bar.session_status), ['COMPLETE', 'COMPLETE']);
});

for (const [name, alter] of [
  ['wrong symbol', (r) => { r.meta.symbol = 'NVDA'; }], ['wrong currency', (r) => { r.meta.currency = 'EUR'; }],
  ['missing timezone', (r) => { delete r.meta.exchangeTimezoneName; }], ['missing exchange', (r) => { delete r.meta.exchangeName; }],
  ['wrong market timezone', (r) => { r.meta.exchangeTimezoneName = 'Asia/Seoul'; }],
  ['wrong interval', (r) => { r.meta.dataGranularity = '1m'; }], ['missing meta', (r) => { delete r.meta; }],
  ['short close array', (r) => { r.indicators.quote[0].close.pop(); }], ['long open array', (r) => { r.indicators.quote[0].open.push(1); }],
  ['short adjusted array', (r) => { r.indicators.adjclose[0].adjclose.pop(); }],
  ['duplicate timestamp', (r) => { r.timestamp[1] = r.timestamp[0]; }], ['unordered timestamp', (r) => { r.timestamp.reverse(); }],
  ['invalid timestamp', (r) => { r.timestamp[0] = null; }], ['zero price', (r) => { r.indicators.quote[0].close[0] = 0; }],
  ['future timestamp', (r) => { r.timestamp[1] = NOW / 1000 + 1; }],
  ['out-of-range timestamp', (r) => { r.timestamp[1] = Number.MAX_SAFE_INTEGER; }],
  ['negative adjusted price', (r) => { r.indicators.adjclose[0].adjclose[0] = -1; }],
  ['string price', (r) => { r.indicators.quote[0].high[0] = '104'; }],
  ['negative volume', (r) => { r.indicators.quote[0].volume[0] = -1; }],
  ['missing quote field', (r) => { delete r.indicators.quote[0].low; }],
]) {
  test(`rejects Yahoo format change: ${name}`, async () => {
    const yahoo = fixture(); alter(yahoo.chart.result[0]);
    await expectError(await setup({ yahoo }).run(), 502, 'YAHOO_FORMAT_CHANGED');
  });
}
test('missing all raw closes and absent history have a fixed unavailable code', async () => {
  const yahoo = fixture(); yahoo.chart.result[0].indicators.quote[0].close = [null, null];
  for (const value of [yahoo, { chart: { result: null, error: { description: 'provider-private-details' } } }, { chart: { result: [], error: null } }]) {
    await expectError(await setup({ yahoo: value }).run(), 404, 'HISTORY_UNAVAILABLE');
  }
});
test('empty timestamps are unavailable and malformed response JSON is format changed', async () => {
  const yahoo = fixture(); yahoo.chart.result[0].timestamp = [];
  await expectError(await setup({ yahoo }).run(), 404, 'HISTORY_UNAVAILABLE');
  await expectError(await setup({ yahooFetch: () => new Response('provider-private-details') }).run(), 502, 'YAHOO_FORMAT_CHANGED');
});
for (const status of [401, 403, 429]) {
  test(`reports Yahoo block status ${status} without upstream payload`, async () => {
    await expectError(await setup({ yahooFetch: () => json({ error: 'provider-private-details' }, status) }).run(), 502, 'YAHOO_BLOCKED');
  });
}
test('Yahoo rejection cancels its response body before releasing the request lease', async () => {
  let cancelled = false;
  const stream = new ReadableStream({ cancel() { cancelled = true; } });
  const s = setup({ yahooFetch: () => new Response(stream, { status: 403 }) });
  await expectError(await s.run(), 502, 'YAHOO_BLOCKED');
  assert.equal(cancelled, true);
});
for (const status of [500, 502, 503]) {
  test(`reports Yahoo unavailable status ${status} without upstream payload`, async () => {
    await expectError(await setup({ yahooFetch: () => json({ error: 'provider-private-details' }, status) }).run(), 503, 'YAHOO_UNAVAILABLE');
  });
}
test('Yahoo network errors have a fixed unavailable code and release the lease', async () => {
  const s = setup({ yahooFetch: () => { throw new Error('provider-private-details'); } });
  await expectError(await s.run(), 503, 'YAHOO_UNAVAILABLE');
});
test('Yahoo 404 means history is unavailable', async () => {
  await expectError(await setup({ yahooFetch: () => json({ secret: 'provider-private-details' }, 404) }).run(), 404, 'HISTORY_UNAVAILABLE');
});
test('Yahoo body limit is enforced while streaming without trusting Content-Length', async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    start(controller) { controller.enqueue(new Uint8Array(512 * 1024)); controller.enqueue(new Uint8Array(1)); },
    cancel() { cancelled = true; },
  });
  await expectError(await setup({ yahooFetch: () => new Response(stream, { headers: { 'Content-Length': '1' } }) }).run(), 502, 'YAHOO_TOO_LARGE');
  assert.equal(cancelled, true);
});
test('Yahoo advertised body limit and bar-count cap reject oversized responses', async () => {
  await expectError(await setup({ yahooFetch: () => json(fixture(), 200, { 'Content-Length': String(512 * 1024 + 1) }) }).run(), 502, 'YAHOO_TOO_LARGE');
  const yahoo = fixture(); yahoo.chart.result[0].timestamp = Array.from({ length: 1501 }, (_, i) => NOW / 1000 - 2000 + i);
  await expectError(await setup({ yahoo }).run(), 502, 'YAHOO_TOO_LARGE');
});
function immediateTimeout() {
  const active = new Set();
  return {
    setTimeout(fn) { const id = {}; active.add(id); queueMicrotask(() => { if (active.has(id)) fn(); }); return id; },
    clearTimeout(id) { active.delete(id); },
  };
}
test('auth timeout fails closed before Yahoo', async () => {
  const s = setup({ authFetch: () => new Promise(() => {}), dependencies: immediateTimeout() });
  await expectError(await s.run(), 503, 'AUTH_UNAVAILABLE');
  assert.equal(s.calls.length, 1);
});
test('Yahoo timeout aborts the request and releases the lease', async () => {
  let signal;
  let timers = 0;
  const active = new Map();
  const dependencies = {
    setTimeout(fn) { const id = ++timers; active.set(id, fn); return id; },
    clearTimeout(id) { active.delete(id); },
  };
  const s = setup({ yahooFetch: (_input, init) => {
    signal = init.signal;
    queueMicrotask(() => active.get(timers)?.());
    return new Promise(() => {});
  }, dependencies });
  await expectError(await s.run(), 504, 'YAHOO_TIMEOUT');
  assert.equal(signal.aborted, true);
});

test('minimum five-second spacing applies within one isolate', async () => {
  const s = setup();
  assert.equal((await s.run()).status, 200);
  s.clock.now += 4999;
  const denied = await s.run();
  assert.equal(denied.headers.get('Retry-After'), '1');
  await expectError(denied, 429, 'RATE_LIMITED');
  assert.equal(s.calls.filter((call) => call.url.includes('yahoo.com')).length, 1);
  s.clock.now += 1;
  assert.equal((await s.run()).status, 200);
});

test('rolling cap expires exactly at the sixty-second boundary', async () => {
  const s = setup({ rateEnv: { REQUESTS_PER_MINUTE: '2' } });
  assert.equal((await s.run()).status, 200);
  s.clock.now += 5000;
  assert.equal((await s.run()).status, 200);
  s.clock.now += 5000;
  const denied = await s.run();
  assert.equal(denied.headers.get('Retry-After'), '50');
  await expectError(denied, 429, 'RATE_LIMITED');
  s.clock.now = NOW + 59999;
  await expectError(await s.run(), 429, 'RATE_LIMITED');
  s.clock.now = NOW + 60000;
  assert.equal((await s.run()).status, 200);
});

test('default cap allows twelve spaced requests and recovers after the window', async () => {
  const s = setup();
  for (let i = 0; i < 12; i++) {
    s.clock.now = NOW + i * 5000;
    assert.equal((await s.run()).status, 200);
  }
  await expectError(await s.run(), 429, 'RATE_LIMITED');
  s.clock.now = NOW + 60000;
  assert.equal((await s.run()).status, 200);
});

test('invalid caps fail closed before Yahoo', async () => {
  for (const cap of ['13', '1000', '0', '-1', 'invalid', null]) {
    const s = setup({ rateEnv: { REQUESTS_PER_MINUTE: cap } });
    await expectError(await s.run(), 503, 'RATE_LIMIT_UNAVAILABLE');
    assert.equal(s.calls.length, 1);
  }
});

test('one isolate admits one of several simultaneous requests', async () => {
  const s = setup();
  const responses = await Promise.all([s.run(), s.run(), s.run()]);
  assert.deepEqual(responses.map((response) => response.status).sort(), [200, 429, 429]);
  assert.equal(s.calls.filter((call) => call.url.includes('yahoo.com')).length, 1);
});

test('a pending Yahoo request blocks another request after the spacing window', async () => {
  let finish, entered;
  let pending = true;
  const started = new Promise((resolve) => { entered = resolve; });
  const s = setup({ yahooFetch: () => {
    if (!pending) return json(fixture());
    entered();
    return new Promise((resolve) => { finish = () => { pending = false; resolve(json(fixture())); }; });
  } });
  const running = s.run();
  await started;
  s.clock.now += 6000;
  const denied = await s.run();
  assert.equal(denied.headers.get('Retry-After'), '24');
  await expectError(denied, 429, 'RATE_LIMITED');
  finish();
  assert.equal((await running).status, 200);
  assert.equal((await s.run()).status, 200);
});

test('provider failure releases the local lease but still consumes rate budget', async () => {
  let broken = true;
  const s = setup({ yahooFetch: () => broken ? json({}, 503) : json(fixture()) });
  await expectError(await s.run(), 503, 'YAHOO_UNAVAILABLE');
  broken = false;
  await expectError(await s.run(), 429, 'RATE_LIMITED');
  s.clock.now += 5000;
  assert.equal((await s.run()).status, 200);
});

test('local lease is released on a Yahoo timeout', async () => {
  let broken = true;
  let latest;
  const timers = new Map();
  const s = setup({
    dependencies: {
      setTimeout(fn) { latest = {}; timers.set(latest, fn); return latest; },
      clearTimeout(id) { timers.delete(id); },
    },
    yahooFetch: () => {
      if (!broken) return json(fixture());
      const timer = latest;
      queueMicrotask(() => timers.get(timer)?.());
      return new Promise(() => {});
    },
  });
  await expectError(await s.run(), 504, 'YAHOO_TIMEOUT');
  broken = false;
  s.clock.now += 5000;
  assert.equal((await s.run()).status, 200);
  assert.equal(timers.size, 0);
});

test('a fresh isolate resets the best-effort memory limit', async () => {
  const clock = { now: NOW };
  const first = setup({ clock });
  assert.equal((await first.run()).status, 200);
  await expectError(await first.run(), 429, 'RATE_LIMITED');
  const fresh = setup({ clock });
  assert.equal((await fresh.run()).status, 200);
});

test('an expired lease can recover and a stale completion cannot release its successor', async () => {
  const finishes = [];
  let entered;
  const started = new Promise((resolve) => { entered = resolve; });
  const s = setup({
    dependencies: { setTimeout: () => ({}), clearTimeout: () => {} },
    yahooFetch: () => { entered(); return new Promise((resolve) => { finishes.push(() => resolve(json(fixture()))); }); },
  });
  const first = s.run();
  await started;
  s.clock.now += 29999;
  await expectError(await s.run(), 429, 'RATE_LIMITED');
  s.clock.now += 1;
  const second = s.run();
  // Wait until the real handler reaches the second mocked upstream.
  while (finishes.length < 2) await new Promise((resolve) => setImmediate(resolve));
  finishes[0]();
  assert.equal((await first).status, 200);
  s.clock.now += 6000;
  await expectError(await s.run(), 429, 'RATE_LIMITED');
  finishes[1]();
  assert.equal((await second).status, 200);
});

test('invalid or backwards clocks fail closed without Yahoo', async () => {
  const s = setup();
  assert.equal((await s.run()).status, 200);
  for (const time of [NOW - 1, NaN, -1, Number.MAX_SAFE_INTEGER]) {
    s.clock.now = time;
    await expectError(await s.run(), 503, 'RATE_LIMIT_UNAVAILABLE');
  }
  assert.equal(s.calls.filter((call) => call.url.includes('yahoo.com')).length, 1);
});

test('dashboard source is self-contained with no binding, storage or logging APIs', async () => {
  assert.equal(typeof module.default?.fetch, 'function');
  const source = await readFile(new URL('../dashboard-worker.js', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /\bimport\b|\bHistoryRateLimiter\b|HISTORY_RATE_LIMITER|\bstorage\b|\bconsole\s*\.|\bcaches\s*\.|\b(?:KV|R2|D1)\b/);
});

test('authentication, response normalization and privacy contract match the existing Worker', async () => {
  const original = await readFile(new URL('../src/index.js', import.meta.url), 'utf8');
  const dashboard = await readFile(new URL('../dashboard-worker.js', import.meta.url), 'utf8');
  const between = (source, start, end) => source.slice(source.indexOf(start), source.indexOf(end));
  assert.equal(between(dashboard, 'const ORIGIN', 'export function createHandler'), between(original, 'const ORIGIN', 'export function createHandler'));
  assert.equal(between(dashboard, '  async function timed', '  async function admit'), between(original, '  async function timed', '  async function admit'));
  assert.equal(between(dashboard, '  async function history', '      const admission = await admit'), between(original, '  async function history', '      const admission = await admit'));
});

