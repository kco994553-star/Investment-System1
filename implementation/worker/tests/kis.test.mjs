import assert from 'node:assert/strict';
import test from 'node:test';
// Private KIS area routes (/kis/status, /kis/chart) of the private Worker. Synthetic values only: the read token, the Google
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
const BARS = JSON.stringify({ schema: K('bars/1'), symbol: 'NVDA', source: 'SYNTHETIC', price_basis_date: '2026-11-04', bars: [] });

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
function setup({ env = {}, github = () => new Response(BARS, { status: 200 }), token = {}, authStatus = 200 } = {}) {
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
    [{ token: { email_verified: false } }, 403, 'AUTH_FORBIDDEN'], [{ authStatus: 401 }, 403, 'AUTH_FORBIDDEN'], [{ authStatus: 500 }, 503, 'AUTH_UNAVAILABLE']]) {
    for (const path of ['/kis/status', '/kis/chart?symbol=NVDA']) {
      const s = setup(opts), r = await s.run(path);
      assert.equal(r.status, status, path + ' ' + JSON.stringify(opts)); noStore(r);
      assert.equal(JSON.parse(await body(r)).error.code, code);
      assert.equal(githubCalls(s).length, 0, 'no private read without the owner');
    }
  }
  const s = setup(), r = await s.run('/kis/chart?symbol=NVDA', { Authorization: '' });
  assert.equal(r.status, 403); assert.equal(githubCalls(s).length, 0);
});

test('chart: the owner gets the private file bytes unchanged, no-store, only for the app origin', async () => {
  const s = setup(), r = await s.run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 200); noStore(r);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.equal(await body(r), BARS, 'bytes passed through');
  const [call] = githubCalls(s);
  assert.equal(call.url, 'https://api.github.com' + REPO + '/contents/chart/N/NVDA.json?ref=data');
  assert.equal(call.init.headers.Accept, 'application/vnd.github.raw+json');
  assert.equal(call.init.headers.Authorization, 'Bearer ' + FAKE_TOKEN, 'the read token goes only to GitHub');
  assert.equal(call.init.redirect, 'manual'); assert.equal(call.init.cache, 'no-store');
  const other = await setup().run('/kis/chart?symbol=NVDA', { Origin: 'https://evil.example' });
  assert.equal(other.status, 403); assert.equal(other.headers.get('Access-Control-Allow-Origin'), null);
});

test('chart: symbol checks stop path tricks before any read', async () => {
  for (const path of ['/kis/chart?symbol=../x', '/kis/chart?symbol=nvda', '/kis/chart?symbol=NVDA&x=1', '/kis/chart?symbol=ZZZZ', '/kis/chart', '/kis/chart?symbol=NVDA%2F..', '/kis/status?x=1', '/kis/other']) {
    const s = setup(), r = await s.run(path);
    assert.ok([400, 404].includes(r.status), path); assert.equal(githubCalls(s).length, 0, path);
  }
  assert.equal((await setup().run('/kis/chart?symbol=BRK-B')).status, 200, 'share-class symbol from the Universe list');
});

test('chart: missing file is EMPTY (404), a non kis-bars/1 file and an oversized file are refused', async () => {
  let r = await setup({ github: () => new Response('{"message":"Not Found"}', { status: 404 }) }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 404); assert.equal(JSON.parse(await body(r)).error.code, 'KIS_SERIES_NOT_FOUND');
  r = await setup({ github: () => new Response(JSON.stringify({ schema: K('ohlcv/1') }), { status: 200 }) }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 502); assert.equal(JSON.parse(await body(r)).error.code, 'KIS_SERIES_INVALID');
  r = await setup({ github: () => new Response('x', { status: 200, headers: { 'Content-Length': String(3 * 1024 * 1024) } }) }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 502); assert.equal(JSON.parse(await body(r)).error.code, 'KIS_SERIES_TOO_LARGE');
});

test('chart: token and upstream states become fixed codes; the upstream body never reaches the app', async () => {
  const cases = [
    [{ env: { PRIVATE_REPO_READ_TOKEN: undefined } }, 503, 'TOKEN_UNSET', 0],
    [{ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-05' } }, 503, 'TOKEN_EXPIRED', 0],
    [{ github: () => new Response('{"message":"Bad credentials ' + FAKE_TOKEN + '"}', { status: 401 }) }, 503, 'TOKEN_REJECTED', 1],
    [{ github: () => new Response('x', { status: 403, headers: { 'x-ratelimit-remaining': '0' } }) }, 503, 'UPSTREAM_RATE_LIMITED', 1],
    [{ github: () => new Response(null, { status: 301, headers: { Location: 'https://api.github.com/x' } }) }, 502, 'REPO_MOVED', 1],
    [{ github: () => new Response('down', { status: 503 }) }, 503, 'UPSTREAM_UNAVAILABLE', 1],
    [{ github: () => { throw new TypeError('network'); } }, 503, 'UPSTREAM_UNAVAILABLE', 1],
  ];
  for (const [opts, status, code, reads] of cases) {
    const s = setup(opts), r = await s.run('/kis/chart?symbol=NVDA');
    assert.equal(r.status, status, code); noStore(r);
    assert.equal(JSON.parse(await body(r)).error.code, code);
    assert.equal(githubCalls(s).length, reads, code + ' reads');
  }
});

test('chart: EXPIRING still serves and names the date in one exposed header', async () => {
  const r = await setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-12' } }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 200); assert.equal(r.headers.get('X-Private-Token-Expires-On'), '2026-11-12');
  assert.equal(r.headers.get('Access-Control-Expose-Headers'), 'X-Private-Token-Expires-On');
});

test('status: one repository check; state, code, rebuilt date and days only', async () => {
  const at = async (opts) => { const s = setup(opts), r = await s.run('/kis/status'); assert.equal(r.status, 200); noStore(r); return { v: JSON.parse(await body(r)), reads: githubCalls(s) }; };
  let { v, reads } = await at({ github: () => new Response('{"full_name":"x"}', { status: 200 }) });
  assert.deepEqual(v, { schema: K('status/1'), state: 'OK', code: null, expires_on: '2027-01-31', days_left: 87 });
  assert.equal(reads.length, 1); assert.equal(reads[0].url, 'https://api.github.com' + REPO);
  ({ v } = await at({ github: () => new Response('{}', { status: 404 }) })); assert.deepEqual([v.state, v.code], ['REJECTED', 'TOKEN_NO_ACCESS']);
  ({ v } = await at({ github: () => new Response('{}', { status: 401 }) })); assert.deepEqual([v.state, v.code], ['REJECTED', 'TOKEN_REJECTED']);
  ({ v, reads } = await at({ env: { PRIVATE_REPO_READ_TOKEN: undefined } })); assert.deepEqual([v.state, v.code, reads.length], ['UNSET', 'TOKEN_UNSET', 0]);
  ({ v } = await at({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-10' }, github: () => new Response('{}', { status: 200 }) }));
  assert.deepEqual([v.state, v.days_left], ['EXPIRING', 5]);
});

test('a key-sorted body (the writer uses sort_keys) passes; each route only accepts its own schema and path', async () => {
  const sorted = JSON.stringify({ bars: [], schema: K('bars/1'), symbol: 'NVDA' });
  let s = setup({ github: () => new Response(sorted, { status: 200 }) }), r = await s.run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 200); assert.equal(await r.text(), sorted);
  const analysis = JSON.stringify({ adopted_count: 0, metrics: {}, schema: K('bars/1/analysis') });
  s = setup({ github: () => new Response(analysis, { status: 200 }) }); r = await s.run('/kis/analysis?symbol=NVDA');
  assert.equal(r.status, 200); assert.equal(await r.text(), analysis);
  assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/technical/N/NVDA.json?ref=data');
  const qgv = JSON.stringify({ coverage: {}, rank: null, schema: K('qgv/1') });
  s = setup({ github: () => new Response(qgv, { status: 200 }) }); r = await s.run('/kis/qgv');
  assert.equal(r.status, 200); assert.equal(await r.text(), qgv);
  assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/qgv/latest.json?ref=data');
  // A chart file on the analysis route (or any other schema) is refused; so are query strings on /kis/qgv.
  r = await setup({ github: () => new Response(sorted, { status: 200 }) }).run('/kis/analysis?symbol=NVDA');
  assert.equal(r.status, 502); assert.equal(JSON.parse(await body(r)).error.code, 'KIS_SERIES_INVALID');
  r = await setup({ github: () => new Response(analysis, { status: 200 }) }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 502);
  r = await setup({ github: () => new Response(Uint8Array.from([0x7b, 0xff, 0xfe]), { status: 200 }) }).run('/kis/qgv');
  assert.equal(r.status, 502, 'not UTF-8');
  s = setup(); r = await s.run('/kis/qgv?symbol=NVDA'); assert.equal(r.status, 400); assert.equal(githubCalls(s).length, 0);
});

test('the real writers space their keys ("schema": "…"): both spellings pass, and a body that is not one JSON object is refused', async () => {
  // Found on the retained private archive 2026-11-05: staged chart / analysis files are written with ": " separators.
  const spaced = '{"bars": [], "schema": "' + K('bars/1') + '", "symbol": "NVDA"}';
  let r = await setup({ github: () => new Response(spaced, { status: 200 }) }).run('/kis/chart?symbol=NVDA');
  assert.equal(r.status, 200); assert.equal(await r.text(), spaced, 'bytes unchanged');
  for (const bad of ['[]', '{"schema": "' + K('bars/1') + '"', 'null', '{"note": "\\"schema\\":\\"' + K('bars/1') + '\\""}']) {
    r = await setup({ github: () => new Response(bad, { status: 200 }) }).run('/kis/chart?symbol=NVDA');
    assert.equal(r.status, 502, bad); assert.equal(JSON.parse(await body(r)).error.code, 'KIS_SERIES_INVALID');
  }
});

test('technical, macro and news routes: own path and schema only; macro and news take no query', async () => {
  const cases = [
    ['/kis/technical?symbol=NVDA', '/contents/measures/N/NVDA.json?ref=data', { schema: K('technical-measures/1'), metrics: {} }],
    ['/kis/macro', '/contents/macro/current.json?ref=data', { schema_version: 'macro-current-query/1', series: [] }],
    ['/kis/news', '/contents/news/current.json?ref=data', { kind: 'NEWS_SIGNALS', schema_version: 2, items: [] }],
  ];
  for (const [route, file, payload] of cases) {
    const text = JSON.stringify(payload), s = setup({ github: () => new Response(text, { status: 200 }) }), r = await s.run(route);
    assert.equal(r.status, 200, route); assert.equal(await r.text(), text);
    assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + file);
    assert.equal(r.headers.get('Cache-Control'), 'private, no-store, max-age=0');
  }
  // Each route refuses the others' files; news needs schema 2 of NEWS_SIGNALS; macro / news refuse a query string before any read.
  for (const [route, wrong] of [['/kis/technical?symbol=NVDA', { schema: K('bars/1') }], ['/kis/macro', { schema_version: 2, kind: 'NEWS_SIGNALS' }],
    ['/kis/news', { kind: 'NEWS_SIGNALS', schema_version: 1 }], ['/kis/news', { schema_version: 'macro-current-query/1' }]]) {
    const r = await setup({ github: () => new Response(JSON.stringify(wrong), { status: 200 }) }).run(route);
    assert.equal(r.status, 502, route + ' ' + JSON.stringify(wrong));
  }
  for (const route of ['/kis/macro?x=1', '/kis/news?symbol=NVDA', '/kis/technical?symbol=../x']) {
    const s = setup(), r = await s.run(route); assert.equal(r.status, 400, route); assert.equal(githubCalls(s).length, 0);
  }
  // No owner proof: refused before any read on every new route.
  for (const route of ['/kis/technical?symbol=NVDA', '/kis/macro', '/kis/news']) {
    const s = setup({ authStatus: 400 }), r = await s.run(route);
    assert.equal(r.status, 403, route); assert.equal(githubCalls(s).length, 0);
  }
});

// The held common classification bundle (owner 2026-11-08): one route, five parts, each its own file and Codex schema.
test('classification: ?part= reads classification/<part>.json byte for byte; each part only accepts its own schema', async () => {
  const PARTS = { view: 'common-classification-view/1', technical: 'common-classification-technical/1', macro: 'common-classification-macro/1',
    qgv_links: 'common-classification-qgv-links/1', dictionary: 'common-classification-dictionary/1', expanded_summary: 'held-expanded-classification-summary/1',
    industry_macro: 'company-industry-macro-query/1' };
  for (const [part, schema] of Object.entries(PARTS)) {
    // the writer's spacing, kept as received
    const text = '{"schema_version": "' + schema + '", "rows": []}', s = setup({ github: () => new Response(text, { status: 200 }) });
    const r = await s.run('/kis/classification?part=' + part);
    assert.equal(r.status, 200, part); assert.equal(await body(r), text); noStore(r);
    assert.equal(githubCalls(s).length, 1);
    assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/' + part + '.json?ref=data');
    // another part's file under this part's name is refused (502), never served
    const other = Object.values(PARTS).find((x) => x !== schema);
    const w = await setup({ github: () => new Response(JSON.stringify({ schema_version: other }), { status: 200 }) }).run('/kis/classification?part=' + part);
    assert.equal(w.status, 502, part + ' with ' + other);
  }
  // missing file → 404 (the screen's 자료 없음); not one JSON object → 502
  assert.equal((await setup({ github: () => new Response('{}', { status: 404 }) }).run('/kis/classification?part=view')).status, 404);
  assert.equal((await setup({ github: () => new Response('[1]', { status: 200 }) }).run('/kis/classification?part=view')).status, 502);
});

test('classification: the part is checked before any read; no owner proof is refused before any read', async () => {
  for (const route of ['/kis/classification', '/kis/classification?part=', '/kis/classification?part=View', '/kis/classification?part=../view',
    '/kis/classification?part=view&x=1', '/kis/classification?symbol=NVDA', '/kis/classification?part=store', '/kis/classification?part=qgv-links',
    '/kis/classification?part=view#x', '/kis/classification/view']) {
    const s = setup(), r = await s.run(route);
    assert.ok([400, 404].includes(r.status), route + ' ' + r.status); assert.equal(githubCalls(s).length, 0, route);
  }
  const s = setup({ authStatus: 400 }), r = await s.run('/kis/classification?part=view');
  assert.equal(r.status, 403); assert.equal(githubCalls(s).length, 0);
  const u = setup({ env: { PRIVATE_REPO_READ_TOKEN: undefined } }), t = await u.run('/kis/classification?part=view');
  assert.equal(t.status, 503); assert.equal(githubCalls(u).length, 0);
  assert.match(await body(t), /TOKEN_UNSET/);
});

// The held issuer delivery (owner 2026-11-09, Codex #524): manifest / index / coverage and one detail shard, under classification/expanded/.
test('classification expanded: manifest, index, coverage and one shard read their own file; a shard must name itself', async () => {
  const FILES = { expanded_manifest: ['manifest.json', 'held-issuer-sharded/1'], expanded_index: ['expanded-index.json', 'held-issuer-search/1'],
    expanded_coverage: ['coverage.json', 'retained-default-coverage/1'], input_repair: ['input-repair-comparison.json', 'sector-qgv-input-repair-comparison/1'],
    reference_view: ['reference-view.json', 'sector-qgv-reference-view/1'] };
  for (const [part, [file, schema]] of Object.entries(FILES)) {
    const text = '{"schema_version":"' + schema + '","rows":[]}', s = setup({ github: () => new Response(text, { status: 200 }) });
    const r = await s.run('/kis/classification?part=' + part);
    assert.equal(r.status, 200, part); assert.equal(await body(r), text); noStore(r);
    assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/expanded/' + file + '?ref=data');
    const w = await setup({ github: () => new Response('{"schema_version":"held-issuer-shard/1"}', { status: 200 }) }).run('/kis/classification?part=' + part);
    assert.equal(w.status, 502, part + ' with a shard file');
  }
  const shard = '{"schema_version":"held-issuer-shard/1","shard_key":"5a","issuers":[]}';
  const s = setup({ github: () => new Response(shard, { status: 200 }) }), r = await s.run('/kis/classification?part=expanded_detail&shard=5a');
  assert.equal(r.status, 200); assert.equal(await body(r), shard); noStore(r);
  assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/expanded/expanded-detail/5a.json?ref=data');
  // another shard's file under this name is refused, never served
  const other = await setup({ github: () => new Response(shard, { status: 200 }) }).run('/kis/classification?part=expanded_detail&shard=5b');
  assert.equal(other.status, 502);
  // too large → refused (the 2 MiB limit is unchanged)
  const big = await setup({ github: () => new Response(shard, { status: 200, headers: { 'Content-Length': String(2 * 1024 * 1024 + 1) } }) }).run('/kis/classification?part=expanded_detail&shard=5a');
  assert.equal(big.status, 502); assert.match(await body(big), /TOO_LARGE/);
  assert.equal((await setup({ github: () => new Response('{}', { status: 404 }) }).run('/kis/classification?part=expanded_detail&shard=00')).status, 404);
});

test('classification expanded: only ?part=expanded_detail&shard=<2 lowercase hex>; nothing else reaches a read', async () => {
  for (const route of ['/kis/classification?part=expanded_detail', '/kis/classification?part=expanded_detail&shard=5', '/kis/classification?part=expanded_detail&shard=5A',
    '/kis/classification?part=expanded_detail&shard=5ab', '/kis/classification?part=expanded_detail&shard=..', '/kis/classification?part=expanded_detail&shard=5a&x=1',
    '/kis/classification?shard=5a&part=expanded_detail', '/kis/classification?part=expanded_index&shard=5a', '/kis/classification?part=view&shard=5a',
    '/kis/classification?part=expanded_detail&shard=5a#x', '/kis/classification?part=expanded_detail&shard=%35a', '/kis/classification?part=expanded_detail/5a',
    '/kis/classification?part=expanded']) {
    const s = setup(), r = await s.run(route);
    assert.ok([400, 404].includes(r.status), route + ' ' + r.status); assert.equal(githubCalls(s).length, 0, route);
  }
  const s = setup({ authStatus: 400 }), r = await s.run('/kis/classification?part=expanded_detail&shard=5a');
  assert.equal(r.status, 403); assert.equal(githubCalls(s).length, 0);
});

// The dual research delivery (owner 2026-11-11, Codex #529): classification/dual/<scope>/ manifest / summary / index / detail-NNN.
test('classification dual: each part reads its own file for its scope; the manifest must name the scope asked for', async () => {
  const FILES = { dual_manifest: ['manifest', 'qgv-dual-delivery-manifest/1'], dual_summary: ['summary', 'qgv-dual-delivery/1'], dual_index: ['index', 'qgv-dual-index/1'],
    dual_lineage: ['input-lineage', 'qgv-dual-input-projection-proof/1'] };
  for (const scope of ['operating504', 'held1057']) for (const [part, [file, schema]] of Object.entries(FILES)) {
    const text = '{"schema_version":"' + schema + '","scope":"' + scope + '","rows":[]}', s = setup({ github: () => new Response(text, { status: 200 }) });
    const r = await s.run('/kis/classification?part=' + part + '&scope=' + scope);
    assert.equal(r.status, 200, part + ' ' + scope); assert.equal(await body(r), text); noStore(r);
    assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/dual/' + scope + '/' + file + '.json?ref=data');
    const w = await setup({ github: () => new Response('{"schema_version":"qgv-dual-detail/1","rows":[]}', { status: 200 }) }).run('/kis/classification?part=' + part + '&scope=' + scope);
    assert.equal(w.status, 502, part + ' with a detail file');
  }
  const other = '{"schema_version":"qgv-dual-delivery-manifest/1","scope":"held1057","files":[]}';
  assert.equal((await setup({ github: () => new Response(other, { status: 200 }) }).run('/kis/classification?part=dual_manifest&scope=operating504')).status, 502, 'another scope\'s manifest');
  const detail = '{"schema_version":"qgv-dual-detail/1","rows":[]}', s = setup({ github: () => new Response(detail, { status: 200 }) });
  const r = await s.run('/kis/classification?part=dual_detail&scope=held1057&shard=045');
  assert.equal(r.status, 200); assert.equal(await body(r), detail); noStore(r);
  assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/dual/held1057/detail-045.json?ref=data');
  const big = await setup({ github: () => new Response(detail, { status: 200, headers: { 'Content-Length': String(2 * 1024 * 1024 + 1) } }) }).run('/kis/classification?part=dual_detail&scope=operating504&shard=000');
  assert.equal(big.status, 502); assert.match(await body(big), /TOO_LARGE/);
});

test('classification dual leaders: the companion reads classification/dual/<scope>/leaders/; manifest and index name the scope', async () => {
  for (const [part, file, schema] of [['dual_leaders_manifest', 'factor-leaders-manifest', 'qgv-dual-factor-leaders-manifest/1'], ['dual_leaders_index', 'factor-leaders', 'qgv-dual-factor-leaders/1'],
    ['dual_leaders_selection_manifest', 'factor-leaders-selection-manifest', 'qgv-dual-factor-leaders-selection-manifest/1'], ['dual_leaders_selection', 'factor-leaders-selection', 'qgv-dual-factor-leaders-selection/1']]) {
    for (const scope of ['operating504', 'held1057']) {
      const s = setup({ github: () => new Response(JSON.stringify({ schema_version: schema, scope }), { status: 200 }) });
      assert.equal((await s.run('/kis/classification?part=' + part + '&scope=' + scope)).status, 200, part + ' ' + scope);
      assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/dual/' + scope + '/leaders/' + file + '.json?ref=data');
    }
    const other = JSON.stringify({ schema_version: schema, scope: 'held1057' });
    assert.equal((await setup({ github: () => new Response(other, { status: 200 }) }).run('/kis/classification?part=' + part + '&scope=operating504')).status, 502, part + ': another scope');
    const wrong = JSON.stringify({ schema_version: 'qgv-dual-delivery-manifest/1', scope: 'operating504' });
    assert.equal((await setup({ github: () => new Response(wrong, { status: 200 }) }).run('/kis/classification?part=' + part + '&scope=operating504')).status, 502, part + ': another schema');
  }
  const detail = '{"schema_version":"qgv-dual-factor-leaders-detail/1","groups":[]}', s = setup({ github: () => new Response(detail, { status: 200 }) });
  assert.equal((await s.run('/kis/classification?part=dual_leaders_detail&scope=held1057&shard=000')).status, 200);
  assert.equal(githubCalls(s)[0].url, 'https://api.github.com' + REPO + '/contents/classification/dual/held1057/leaders/factor-leaders-000.json?ref=data');
  assert.equal((await setup({ github: () => new Response('{"schema_version":"qgv-dual-detail/1","rows":[]}', { status: 200 }) }).run('/kis/classification?part=dual_leaders_detail&scope=held1057&shard=000')).status, 502, 'a delivery detail is not a leaders shard');
  const big = await setup({ github: () => new Response(detail, { status: 200, headers: { 'Content-Length': String(2 * 1024 * 1024 + 1) } }) }).run('/kis/classification?part=dual_leaders_detail&scope=operating504&shard=000');
  assert.notEqual(big.status, 200, 'the same 2 MiB limit');
  for (const route of ['/kis/classification?part=dual_leaders_detail&scope=operating504', '/kis/classification?part=dual_leaders_detail&scope=operating504&shard=00',
    '/kis/classification?part=dual_leaders_index&scope=market', '/kis/classification?part=dual_leaders_index', '/kis/classification?part=dual_leaders_manifest&scope=operating504&shard=000',
    '/kis/classification?part=dual_leaders&scope=operating504']) {
    const t = setup({ github: () => new Response(detail, { status: 200 }) }), r = await t.run(route);
    assert.equal(r.status, 400, route); assert.equal(githubCalls(t).length, 0, route);
  }
});

test('classification dual: only the exact scope and 3-digit shard forms; nothing else reaches a read', async () => {
  for (const route of ['/kis/classification?part=dual_summary', '/kis/classification?part=dual_summary&scope=market', '/kis/classification?part=dual_summary&scope=Operating504',
    '/kis/classification?scope=operating504&part=dual_summary', '/kis/classification?part=dual_summary&scope=operating504&x=1', '/kis/classification?part=dual_detail&scope=operating504',
    '/kis/classification?part=dual_detail&scope=operating504&shard=00', '/kis/classification?part=dual_detail&scope=operating504&shard=0000', '/kis/classification?part=dual_detail&scope=operating504&shard=..1',
    '/kis/classification?part=dual_detail&shard=000&scope=operating504', '/kis/classification?part=dual_summary&scope=operating504&shard=000', '/kis/classification?part=dual_index&scope=%6Fperating504',
    '/kis/classification?part=dual_manifest&scope=../expanded', '/kis/classification?part=dual_detail&scope=held1057&shard=045#x']) {
    const s = setup(), r = await s.run(route);
    assert.ok([400, 404].includes(r.status), route + ' ' + r.status); assert.equal(githubCalls(s).length, 0, route);
  }
  const s = setup({ authStatus: 400 }), r = await s.run('/kis/classification?part=dual_summary&scope=operating504');
  assert.equal(r.status, 403); assert.equal(githubCalls(s).length, 0);
});

test('preflight: GET with the authorization header only, no read and no Google call', async () => {
  const s = setup();
  const r = await s.run('/kis/chart?symbol=NVDA', { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization', Authorization: '' }, 'OPTIONS');
  assert.equal(r.status, 204); assert.equal(r.headers.get('Access-Control-Allow-Headers'), 'Authorization');
  assert.equal(s.calls.length, 0);
});
