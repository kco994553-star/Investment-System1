import assert from 'node:assert/strict';
import test from 'node:test';
// Private KIS area routes (/kis/status, /kis/stock) of the private Worker; the four older per-file routes are gone. Synthetic values only: the read token, the Google
// client id and the owner address are made up at run time; no KIS value exists in these tests.
const OWNER_EMAIL = ['owner', 'example.test'].join('@');
const FAKE_TOKEN = ['github', 'pat', '11SYNTHETICONLY0000000000'].join('_');

globalThis.fetch = async () => { throw new Error('Live network transport is disabled in these tests'); };
const { createHandler, HistoryRateLimiter, kisTokenDate, seoulToday, kisUpstreamState } = await import('../src/index.js');

const ORIGIN = 'https://kco994553-star.github.io';
// 2026-11-05 03:00 UTC = 12:00 KST.
const NOW = Date.UTC(2026, 10, 5, 3);
const REPO = '/repos/kco994553-star/investment-system1-kis-private';
// Schema names are assembled at run time so this file carries no private schema literal (tests/test_private_boundary_static.py).
const K = (rest) => ['kis', rest].join('-');
const statusRecord = (expires = '2027-01-31') => JSON.stringify({
  schema: ['private', 'area-status/1'].join('-'), publication_scope: 'OWNER_PRIVATE_ONLY', run_at: '2026-11-05T03:00:00Z',
  worker_read_token: { ...kisTokenDate({ PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: expires }, NOW), verification: 'NOT_CHECKED' },
});

class Storage {
  value; queue = Promise.resolve();
  async get() { return structuredClone(this.value); }
  async put(key, value) { this.value = structuredClone(value); }
  async transaction(callback) { const r = this.queue.then(() => callback(this)); this.queue = r.catch(() => {}); return r; }
}
function namespace(clock) {
  const limiter = new HistoryRateLimiter({ storage: new Storage() }, {}, { now: () => clock.now });
  return { idFromName: (n) => n, get: () => ({ fetch: (input, init) => limiter.fetch(input instanceof Request ? input : new Request(input, init)) }) };
}
function setup({ env = {}, github = () => new Response(statusRecord(), { status: 200 }), token = {}, authStatus = 200 } = {}) {
  const clock = { now: NOW }, calls = [];
  const e = { ALLOWED_EMAIL: OWNER_EMAIL, GOOGLE_CLIENT_ID: 'mock-client-id', HISTORY_RATE_LIMITER: namespace(clock),
    PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-01-31', ...env };
  for (const k of Object.keys(e)) if (e[k] === undefined) delete e[k];
  const fetch = async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    if (url === 'https://oauth2.googleapis.com/tokeninfo') {
      if (authStatus !== 200) return new Response('{}', { status: authStatus });
      return new Response(JSON.stringify({ aud: e.GOOGLE_CLIENT_ID, email: e.ALLOWED_EMAIL, email_verified: true, expires_in: '3600', ...token }), { status: 200 });
    }
    assert.ok(url.startsWith('https://api.github.com' + REPO), 'only the private repository is read: ' + url);
    return github(url, init);
  };
  const handler = createHandler({ fetch, now: () => clock.now });
  const req = (path, headers = {}, method = 'GET') => new Request('https://private-worker.example' + path, { method, headers: { Origin: ORIGIN, Authorization: 'Bearer fake-access-token', ...headers } });
  return { run: (path, headers, method) => handler(req(path, headers, method), e), calls, env: e };
}
const noStore = (r) => { assert.equal(r.headers.get('Cache-Control'), 'private, no-store, max-age=0'); assert.equal(r.headers.get('Vary'), 'Origin'); assert.equal(r.headers.get('X-Content-Type-Options'), 'nosniff'); };
const githubCalls = (s) => s.calls.filter((c) => c.url.startsWith('https://api.github.com'));
const STOCK = '/kis/stock?symbol=NVDA';
const ROOT_URL = 'https://api.github.com' + REPO + '/contents/views/kis-stock-packs.json?ref=data';
const OLD_ROUTES = ['/kis/chart', '/kis/analysis', '/kis/technical', '/kis/qgv'];
async function body(r) { const t = await r.text(); assert.doesNotMatch(t, /github_pat_|SYNTHETICONLY|mock-client-id|owner@|example\.test/, 'no secret or address in a body'); return t; }

test('seoulToday counts the Asia/Seoul date', () => {
  assert.equal(seoulToday(Date.UTC(2026, 10, 4, 14, 59)), '2026-11-04');
  assert.equal(seoulToday(Date.UTC(2026, 10, 4, 15, 0)), '2026-11-05');
});

test('token date rows 1–2 and the OK / EXPIRING tail (§4.4)', () => {
  const at = (env) => kisTokenDate({ PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, ...env }, NOW);
  assert.deepEqual(kisTokenDate({}, NOW), { state: 'UNSET', code: 'TOKEN_UNSET', expires_on: null, days_left: null });
  assert.equal(at({}).code, 'TOKEN_DATE_INVALID');
  assert.equal(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-02-30' }).code, 'TOKEN_DATE_INVALID', 'not a calendar date');
  assert.equal(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-1-31' }).code, 'TOKEN_DATE_INVALID');
  assert.equal(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-11-08' }).code, 'TOKEN_DATE_INVALID', 'more than 367 days ahead');
  assert.equal(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: FAKE_TOKEN }).code, 'TOKEN_DATE_IS_TOKEN');
  assert.deepEqual(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-05' }), { state: 'EXPIRED', code: 'TOKEN_EXPIRED', expires_on: '2026-11-05', days_left: 0 });
  assert.deepEqual(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-19' }), { state: 'EXPIRING', code: null, expires_on: '2026-11-19', days_left: 14 });
  assert.deepEqual(at({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-20' }), { state: 'OK', code: null, expires_on: '2026-11-20', days_left: 15 });
});

test('upstream rows 3–7 map to fixed states (§4.4)', () => {
  const r = (status, headers = {}) => new Response(null, { status, headers });
  const d = (days) => ({ days_left: days });
  assert.equal(kisUpstreamState(r(200), d(30)), null);
  assert.equal(kisUpstreamState(r(401), d(2)).code, 'TOKEN_EXPIRED');
  assert.equal(kisUpstreamState(r(401), d(30)).code, 'TOKEN_REJECTED');
  assert.equal(kisUpstreamState(r(403, { 'x-ratelimit-remaining': '0' }), d(30)).code, 'UPSTREAM_RATE_LIMITED');
  assert.equal(kisUpstreamState(r(429, { 'retry-after': '60' }), d(30)).code, 'UPSTREAM_RATE_LIMITED');
  assert.equal(kisUpstreamState(r(403), d(30)).code, 'TOKEN_REJECTED');
  assert.equal(kisUpstreamState(r(301), d(30)).code, 'REPO_MOVED');
  assert.equal(kisUpstreamState(r(502), d(30)).code, 'UPSTREAM_UNAVAILABLE');
});

test('no Google proof: 403 before any private read; Google down: 503 (closed)', async () => {
  for (const [opts, status, code] of [[{ token: { email: ['someone', 'else.test'].join('@') } }, 403, 'AUTH_FORBIDDEN'], [{ token: { aud: 'other-app' } }, 403, 'AUTH_FORBIDDEN'],
    [{ token: { email_verified: false } }, 403, 'AUTH_FORBIDDEN'], [{ authStatus: 401 }, 403, 'AUTH_FORBIDDEN'], [{ authStatus: 400 }, 403, 'AUTH_FORBIDDEN'], [{ authStatus: 500 }, 503, 'AUTH_UNAVAILABLE']]) {
    for (const path of ['/kis/status', STOCK, '/kis/stock?part=qgv']) {
      const s = setup(opts), r = await s.run(path);
      assert.equal(r.status, status, path + ' ' + JSON.stringify(opts)); noStore(r);
      assert.equal(JSON.parse(await body(r)).error.code, code);
      assert.equal(githubCalls(s).length, 0, 'no private read without the owner');
    }
  }
  for (const path of ['/kis/status', STOCK]) {
    const s = setup(), r = await s.run(path, { Authorization: '' });
    assert.equal(r.status, 403, path); assert.equal(githubCalls(s).length, 0);
  }
});

test('the read token goes only to GitHub (raw Contents, redirect manual, no-store); only the app origin gets an answer', async () => {
  for (const [path, url] of [['/kis/status', 'https://api.github.com' + REPO + '/contents/status/private-area.json?ref=data'], [STOCK, ROOT_URL]]) {
    const s = setup({ github: (u) => u === ROOT_URL ? new Response('{}', { status: 401 }) : new Response(statusRecord(), { status: 200 }) });
    const r = await s.run(path);
    assert.equal(r.headers.get('Access-Control-Allow-Origin'), ORIGIN, path); noStore(r);
    const [call] = githubCalls(s);
    assert.equal(call.url, url);
    assert.equal(call.init.headers.Accept, 'application/vnd.github.raw+json');
    assert.equal(call.init.headers.Authorization, 'Bearer ' + FAKE_TOKEN, 'the read token goes only to GitHub');
    assert.equal(call.init.redirect, 'manual'); assert.equal(call.init.cache, 'no-store');
    const other = setup(), refused = await other.run(path, { Origin: 'https://evil.example' });
    assert.equal(refused.status, 403); assert.equal(refused.headers.get('Access-Control-Allow-Origin'), null);
    assert.equal(JSON.parse(await body(refused)).error.code, 'ORIGIN_FORBIDDEN'); assert.equal(other.calls.length, 0, path + ': nothing read');
  }
});

test('the four old per-file routes are gone: ROUTE_NOT_FOUND 404 before Google or GitHub, with or without a query', async () => {
  for (const route of OLD_ROUTES) {
    for (const path of [route, route + '?symbol=NVDA', route + '?symbol=BRK-B', route + '?part=qgv']) {
      for (const method of ['GET', 'OPTIONS']) {
        const headers = method === 'OPTIONS' ? { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization' } : {};
        const s = setup(), r = await s.run(path, headers, method);
        assert.equal(r.status, 404, method + ' ' + path); noStore(r);
        assert.equal(r.headers.get('Access-Control-Allow-Origin'), ORIGIN);
        assert.equal(JSON.parse(await body(r)).error.code, 'ROUTE_NOT_FOUND', path);
        assert.equal(s.calls.length, 0, path + ': no Google and no GitHub call');
        assert.equal(githubCalls(s).length, 0);
      }
    }
  }
  // Another origin is still refused first, exactly like any other path.
  const s = setup(), r = await s.run('/kis/chart?symbol=NVDA', { Origin: 'https://evil.example' });
  assert.equal(r.status, 403); assert.equal(JSON.parse(await body(r)).error.code, 'ORIGIN_FORBIDDEN'); assert.equal(s.calls.length, 0);
});

test('stock and status: query checks stop path tricks before any read', async () => {
  for (const path of ['/kis/stock?symbol=../x', '/kis/stock?symbol=nvda', '/kis/stock?symbol=NVDA&x=1', '/kis/stock', '/kis/stock?symbol=NVDA%2F..',
    '/kis/stock?symbol=BRK_B', '/kis/stock?symbol=BRK%2FB', '/kis/stock?symbol=BRK.B', '/kis/status?x=1', '/kis/status#x', '/kis/other']) {
    const s = setup(), r = await s.run(path);
    assert.ok([400, 404].includes(r.status), path); assert.equal(githubCalls(s).length, 0, path);
  }
});

test('stock: token and upstream states become fixed codes; the upstream body never reaches the app', async () => {
  const cases = [
    [{ env: { PRIVATE_REPO_READ_TOKEN: undefined } }, 503, 'TOKEN_UNSET', 0],
    [{ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-05' } }, 503, 'TOKEN_EXPIRED', 0],
    [{ github: () => new Response('{"message":"Bad credentials ' + FAKE_TOKEN + '"}', { status: 401 }) }, 503, 'TOKEN_REJECTED', 1],
    [{ github: () => new Response('x', { status: 403, headers: { 'x-ratelimit-remaining': '0' } }) }, 503, 'UPSTREAM_RATE_LIMITED', 1],
    [{ github: () => new Response(null, { status: 301, headers: { Location: 'https://api.github.com/x' } }) }, 502, 'REPO_MOVED', 1],
    [{ github: () => new Response('down', { status: 503 }) }, 503, 'UPSTREAM_UNAVAILABLE', 1],
    [{ github: () => { throw new TypeError('network'); } }, 503, 'UPSTREAM_UNAVAILABLE', 1],
  ];
  for (const path of [STOCK, '/kis/stock?part=qgv']) {
    for (const [opts, status, code, reads] of cases) {
      const s = setup(opts), r = await s.run(path);
      assert.equal(r.status, status, path + ' ' + code); noStore(r);
      assert.equal(JSON.parse(await body(r)).error.code, code);
      assert.equal(githubCalls(s).length, reads, code + ' reads');
      if (reads) assert.equal(githubCalls(s)[0].url, ROOT_URL, 'the root read comes first');
    }
  }
});

test('status: one Contents permission check; state, code, rebuilt date and days only', async () => {
  const at = async (opts) => { const s = setup(opts), r = await s.run('/kis/status'); assert.equal(r.status, 200); noStore(r); return { v: JSON.parse(await body(r)), reads: githubCalls(s) }; };
  let { v, reads } = await at({ github: () => new Response(statusRecord(), { status: 200 }) });
  assert.deepEqual(v, { schema: K('status/1'), state: 'OK', code: null, expires_on: '2027-01-31', days_left: 87 });
  assert.equal(reads.length, 1); assert.equal(reads[0].url, 'https://api.github.com' + REPO + '/contents/status/private-area.json?ref=data');
  ({ v } = await at({ github: () => new Response('{}', { status: 404 }) })); assert.deepEqual([v.state, v.code], ['REJECTED', 'TOKEN_NO_ACCESS']);
  ({ v } = await at({ github: () => new Response('{}', { status: 401 }) })); assert.deepEqual([v.state, v.code], ['REJECTED', 'TOKEN_REJECTED']);
  ({ v, reads } = await at({ env: { PRIVATE_REPO_READ_TOKEN: undefined } })); assert.deepEqual([v.state, v.code, reads.length], ['UNSET', 'TOKEN_UNSET', 0]);
  ({ v } = await at({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-10' }, github: () => new Response(statusRecord('2026-11-10'), { status: 200 }) }));
  assert.deepEqual([v.state, v.days_left], ['EXPIRING', 5]);
});

test('NEVER is explicit; absent, invalid, lookalike and credential values stay closed', () => {
  const at = raw => kisTokenDate({ PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: raw }, NOW);
  assert.deepEqual(at('NEVER'), { state: 'NO_EXPIRY', code: null, expires_on: null, days_left: null });
  for (const raw of [undefined, null, '', 'never', ' NEVER', 'NEVER ', 'null', '2027-02-30']) assert.equal(at(raw).code, 'TOKEN_DATE_INVALID');
  assert.equal(at(FAKE_TOKEN).code, 'TOKEN_DATE_IS_TOKEN');
  assert.equal(kisTokenDate({ PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, NOW).code, 'TOKEN_UNSET');
});

test('NEVER status requires owner proof and real GitHub Contents access, never expiry inference', async () => {
  for (const [status, headers, state, code] of [
    [200, {}, 'NO_EXPIRY', null], [401, {}, 'REJECTED', 'TOKEN_REJECTED'],
    [403, {}, 'REJECTED', 'TOKEN_REJECTED'], [404, {}, 'REJECTED', 'TOKEN_NO_ACCESS'],
    [429, { 'retry-after': '60' }, 'RATE_LIMITED', 'UPSTREAM_RATE_LIMITED'],
    [503, {}, 'ERROR', 'UPSTREAM_UNAVAILABLE'], [301, {}, 'ERROR', 'REPO_MOVED'],
  ]) {
    const s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, github: () => new Response(status === 200 ? statusRecord('NEVER') : FAKE_TOKEN, { status, headers }) });
    const r = await s.run('/kis/status'); noStore(r);
    const v = JSON.parse(await body(r));
    assert.deepEqual([v.state, v.code, v.expires_on, v.days_left], [state, code, null, null]);
    assert.equal(githubCalls(s).length, 1);
  }
  for (const token of [{ email: ['other', 'example.test'].join('@') }, { expires_in: '0' }, { aud: 'wrong-app' }]) {
    const s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, token });
    assert.equal((await s.run('/kis/status')).status, 403); assert.equal(githubCalls(s).length, 0);
  }
});

test('NEVER status refuses stale dated metadata, missing status and malformed metadata without echo', async () => {
  for (const [payload, code] of [
    [statusRecord(), 'TOKEN_EXPIRY_MISMATCH'], ['{}', 'TOKEN_STATUS_INVALID'],
    [JSON.stringify({ ...JSON.parse(statusRecord('NEVER')), worker_read_token: { state: 'NO_EXPIRY', code: null, expires_on: '2027-02-13', days_left: null, verification: 'NOT_CHECKED' } }), 'TOKEN_STATUS_INVALID'],
    [JSON.stringify({ ...JSON.parse(statusRecord('NEVER')), run_at: FAKE_TOKEN }), 'TOKEN_STATUS_INVALID'],
  ]) {
    const s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, github: () => new Response(payload) });
    const r = await s.run('/kis/status'), v = JSON.parse(await body(r));
    assert.deepEqual([v.state, v.code], ['ERROR', code]);
  }
});

test('NEVER stock reads retain upstream rejection and no-store; dated expiry still blocks before GitHub', async () => {
  // A NEVER token's successful stock read (no expiry header) is in kis-stock.test.mjs, which carries the release fixture.
  let s, r;
  for (const status of [401, 403]) {
    s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER' }, github: () => new Response(FAKE_TOKEN, { status }) });
    r = await s.run(STOCK); assert.equal(r.status, 503); noStore(r); assert.equal(JSON.parse(await body(r)).error.code, 'TOKEN_REJECTED');
    assert.equal(r.headers.get('X-Private-Token-Expires-On'), null);
  }
  s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-05' } });
  r = await s.run(STOCK); assert.equal(r.status, 503); assert.equal(githubCalls(s).length, 0);
});

test('dated status validates the stored countdown at capture time, not the current day', async () => {
  const record = JSON.parse(statusRecord());
  record.run_at = '2026-11-04T03:00:00Z'; record.worker_read_token.days_left = 88;
  const s = setup({ github: () => new Response(JSON.stringify(record)) });
  const r = await s.run('/kis/status'), v = JSON.parse(await body(r));
  assert.deepEqual([v.state, v.expires_on, v.days_left], ['OK', '2027-01-31', 87]);
});

test('dated 401 near expiry retains the existing expiry diagnosis; NEVER outages never become expiry', async () => {
  for (const [expires, github, state, code] of [
    ['2026-11-07', () => new Response(FAKE_TOKEN, { status: 401 }), 'EXPIRED', 'TOKEN_EXPIRED'],
    ['NEVER', () => { throw new TypeError('unavailable'); }, 'ERROR', 'UPSTREAM_UNAVAILABLE'],
    ['NEVER', () => new Response(statusRecord('NEVER'), { headers: { 'Content-Length': '16385' } }), 'ERROR', 'TOKEN_STATUS_INVALID'],
  ]) {
    const s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: expires }, github });
    const r = await s.run('/kis/status'), v = JSON.parse(await body(r));
    assert.deepEqual([v.state, v.code], [state, code]);
  }
});

test('routes outside the private area scope (classification, macro, news) do not exist: 404 before Google or GitHub', async () => {
  for (const route of ['/kis/classification?part=view', '/kis/macro', '/kis/news']) {
    const s = setup(), r = await s.run(route);
    assert.equal(r.status, 404, route); noStore(r);
    assert.equal(JSON.parse(await body(r)).error.code, 'ROUTE_NOT_FOUND');
    assert.equal(s.calls.length, 0, route + ': no Google and no GitHub call');
  }
});

test('an expired Google session (exp in the past) is refused before any private read', async () => {
  for (const path of ['/kis/status', STOCK, '/kis/stock?part=qgv']) {
    const s = setup({ token: { exp: String(Math.floor(NOW / 1000) - 1) } }), r = await s.run(path);
    assert.equal(r.status, 403, path); assert.equal(JSON.parse(await body(r)).error.code, 'AUTH_FORBIDDEN');
    assert.equal(githubCalls(s).length, 0);
  }
});

test('preflight: GET with the authorization header only, no read and no Google call', async () => {
  for (const path of ['/kis/status', STOCK, '/kis/stock?part=qgv']) {
    const s = setup();
    const r = await s.run(path, { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization', Authorization: '' }, 'OPTIONS');
    assert.equal(r.status, 204, path); assert.equal(r.headers.get('Access-Control-Allow-Headers'), 'Authorization');
    assert.equal(r.headers.get('Access-Control-Allow-Methods'), 'GET');
    assert.equal(s.calls.length, 0);
    const bad = setup(), refused = await bad.run(path, { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization, cookie', Authorization: '' }, 'OPTIONS');
    assert.equal(refused.status, 400, path); assert.equal(bad.calls.length, 0);
  }
});

test('limiter: one admission per request on both routes; a request inside the spacing is refused before GitHub', async () => {
  for (const path of ['/kis/status', STOCK]) {
    const s = setup({ github: () => new Response('{}', { status: 401 }) });
    assert.notEqual((await s.run(path)).status, 429, path);
    const before = githubCalls(s).length, r = await s.run(path);
    assert.equal(r.status, 429, path); noStore(r); assert.equal(JSON.parse(await body(r)).error.code, 'RATE_LIMITED');
    assert.ok(Number(r.headers.get('Retry-After')) >= 1);
    assert.equal(githubCalls(s).length, before, path + ': no GitHub call when refused');
  }
});
