import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { gzipSync, gunzipSync } from 'node:zlib';
// /kis/stock of the private Worker (KIS_STOCK_VIEW_RELEASES_20261120.md §5). Synthetic values only: the read token, the Google
// client id, the owner address, the signed URL and every number are made up here; no KIS value and no price exists in this file.
const OWNER_EMAIL = ['owner', 'example.test'].join('@');
const FAKE_TOKEN = ['github', 'pat', '11SYNTHETICONLY0000000000'].join('_');

globalThis.fetch = async () => { throw new Error('Live network transport is disabled in these tests'); };
const { createHandler, HistoryRateLimiter, kisStockIndexEntry, kisAssetRedirectTarget } = await import('../src/index.js');

const ORIGIN = 'https://kco994553-star.github.io';
const NOW = Date.UTC(2026, 10, 20, 3);
const API = 'https://api.github.com/repos/kco994553-star/investment-system1-kis-private';
const INDEX_URL = API + '/contents/views/kis-stock-index.json?ref=data';
const ROOT_URL = API + '/contents/views/kis-stock-packs.json?ref=data';
const SHARD_URL = (n) => API + '/contents/views/kis-stock-packs/' + n + '?ref=data';
const ASSET_HOST = 'release-assets.githubusercontent.com';
const SIGNED = 'https://' + ASSET_HOST + '/github-production-release-asset/1/2?sp=r&sig=SYNTHETICSIGNATURE';
// Schema names are assembled at run time so this file carries no private schema literal (tests/test_private_boundary_static.py).
const K = (rest) => ['kis', rest].join('-');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const FIELDS = Array.from({ length: 17 }, (_, i) => 'c' + String(i + 1).padStart(2, '0'));
const row = (n) => ['2026-11-' + String(16 + n).padStart(2, '0'), ...Array.from({ length: 16 }, (_, i) => n * 100 + i)];

function makeView(overrides = {}) {
  return { schema: K('stock-view/1'), publication_scope: 'OWNER_PRIVATE_ONLY', symbol: 'NVDA', evaluation_day: '2026-11-19',
    chart: { basis: 'RAW' }, fields: FIELDS, rows: [row(1), row(2), row(3)], indicators: { reason_runs: [] }, latest: {},
    coverage: { scope: 'ALL_RETAINED_SESSIONS', retained_sessions: 3 },
    additional_requests_for_toggle: 0, additional_requests_for_retained_period: 0, history_sha256: 'a'.repeat(64), ...overrides };
}
function makeAsset(view = makeView()) {
  const json = Buffer.from(JSON.stringify(view), 'utf8'), gz = gzipSync(json);
  return { json, gz };
}
function entryOf({ json, gz }, id = 7, symbol = 'NVDA') {
  return { symbol, asset_id: id, name: 'stock-' + sha(gz).slice(0, 16) + '.json.gz', bytes: gz.length, sha256: sha(gz), json_bytes: json.length, json_sha256: sha(json) };
}
function makeIndex(asset = makeAsset(), overrides = {}, entryOverrides = {}) {
  return { schema: K('stock-asset-index/1'), publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: '2026-11-19',
    release_tag: 'view-2026-11-19-' + 'b'.repeat(12), generation_sha256: 'c'.repeat(64),
    stocks: { NVDA: { ...entryOf(asset), ...entryOverrides } },
    qgv: { asset_id: 9, name: 'qgv.json.gz', bytes: 10, sha256: 'd'.repeat(64), json_bytes: 20, json_sha256: 'e'.repeat(64) }, ...overrides };
}

class Storage {
  value; queue = Promise.resolve();
  async get() { return structuredClone(this.value); }
  async put(key, value) { this.value = structuredClone(value); }
  async transaction(callback) { const r = this.queue.then(() => callback(this)); this.queue = r.catch(() => {}); return r; }
}

function setup({ asset = makeAsset(), index, indexResponse, assetApi, target, authStatus = 200, env = {}, packs = null } = {}) {
  const clock = { now: NOW }, calls = [], limiterCalls = [];
  const limiter = new HistoryRateLimiter({ storage: new Storage() }, {}, { now: () => clock.now });
  const ns = { idFromName: (n) => n, get: () => ({ fetch: (input, init) => {
    const r = input instanceof Request ? input : new Request(input, init);
    limiterCalls.push(new URL(r.url).pathname);
    return limiter.fetch(r);
  } }) };
  const e = { ALLOWED_EMAIL: OWNER_EMAIL, GOOGLE_CLIENT_ID: 'mock-client-id', HISTORY_RATE_LIMITER: ns,
    PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-01-31', ...env };
  for (const k of Object.keys(e)) if (e[k] === undefined) delete e[k];
  const idx = index ?? makeIndex(asset);
  const fetch = async (input, init) => {
    const url = String(input);
    calls.push({ url, init });
    if (url === 'https://oauth2.googleapis.com/tokeninfo') {
      if (authStatus !== 200) return new Response('{}', { status: authStatus });
      return new Response(JSON.stringify({ aud: e.GOOGLE_CLIENT_ID, email: e.ALLOWED_EMAIL, email_verified: true, expires_in: '3600' }), { status: 200 });
    }
    if (url === ROOT_URL) return packs ? (packs.rootResponse ? packs.rootResponse() : new Response(packs.rootBytes, { status: 200 })) : new Response('{}', { status: 404 });
    if (packs && url.startsWith(API + '/contents/views/kis-stock-packs/')) {
      const name = url.slice((API + '/contents/views/kis-stock-packs/').length).split('?')[0];
      return packs.shards[name] ? new Response(packs.shards[name], { status: 200 }) : new Response('{}', { status: 404 });
    }
    if (url === INDEX_URL) return indexResponse ? indexResponse() : new Response(JSON.stringify(idx), { status: 200 });
    if (url.startsWith(API + '/releases/assets/')) return assetApi ? assetApi(url) : new Response(null, { status: 302, headers: { Location: SIGNED } });
    if (new URL(url).hostname === ASSET_HOST) return target ? target(url, init) : packs ? packs.serve(init) : new Response(asset.gz, { status: 200 });
    throw new Error('unexpected upstream in test: ' + new URL(url).hostname);
  };
  const handler = createHandler({ fetch, now: () => clock.now });
  const req = (path, headers = {}, method = 'GET') => new Request('https://private-worker.example' + path, { method, headers: { Origin: ORIGIN, Authorization: 'Bearer fake-access-token', ...headers } });
  return { run: (path = '/kis/stock?symbol=NVDA', headers, method) => handler(req(path, headers, method), e), calls, limiterCalls, clock,
    // Without a bundle root the root probe (one 404 read) is left out here; 'bundle path' tests below count it explicitly.
    upstream: () => calls.filter((c) => c.url !== 'https://oauth2.googleapis.com/tokeninfo' && (packs || c.url !== ROOT_URL)) };
}
const noStore = (r) => { assert.equal(r.headers.get('Cache-Control'), 'private, no-store, max-age=0'); assert.equal(r.headers.get('Vary'), 'Origin'); assert.equal(r.headers.get('X-Content-Type-Options'), 'nosniff'); };
async function code(r) {
  const t = await r.text();
  assert.doesNotMatch(t, /github_pat_|SYNTHETICONLY|SYNTHETICSIGNATURE|release-assets|mock-client-id|owner@|example\.test/, 'no secret, signed URL or address in an error');
  return JSON.parse(t).error.code;
}
const headerNames = (init) => Object.keys(init.headers ?? {}).map((k) => k.toLowerCase());

// ---- the pure checks ----------------------------------------------------------------------------------------------------
test('index reader: the top level and the requested entry are checked; unknown keys, bad types, ranges and hex are refused', () => {
  const good = makeIndex();
  const e = good.stocks.NVDA;
  const nvda = (v) => kisStockIndexEntry(JSON.parse(JSON.stringify(v ?? null)), 'NVDA');
  assert.deepEqual(nvda(good), e);
  assert.deepEqual(kisStockIndexEntry(good, null), good.qgv, 'the qgv part');
  const bad = [
    { ...good, extra: 1 }, (() => { const v = { ...good }; delete v.qgv; return v; })(), { ...good, schema: K('stock-view/1') },
    { ...good, publication_scope: 'PUBLIC' }, { ...good, evaluation_day: '2026-02-30' }, { ...good, evaluation_day: '2026-11-19T00:00:00Z' },
    { ...good, release_tag: '' }, { ...good, release_tag: 'a/b' }, { ...good, release_tag: 7 },
    { ...good, generation_sha256: 'C'.repeat(64) }, { ...good, generation_sha256: 'c'.repeat(63) },
    { ...good, stocks: [] }, { ...good, stocks: null },
    { ...good, stocks: { NVDA: { ...e, extra: 1 } } }, { ...good, stocks: { NVDA: { ...e, symbol: undefined } } },
    { ...good, stocks: { NVDA: { ...e, symbol: 'nvda' } } }, { ...good, stocks: { NVDA: { ...e, name: '../x' } } },
    ...[0, -1, 1.5, '7', 2 ** 53, null].map((asset_id) => ({ ...good, stocks: { NVDA: { ...e, asset_id } } })),
    ...[0, 1_800_001, '10', 2.5].map((bytes) => ({ ...good, stocks: { NVDA: { ...e, bytes } } })),
    ...[0, 1_800_001].map((json_bytes) => ({ ...good, stocks: { NVDA: { ...e, json_bytes } } })),
    { ...good, stocks: { NVDA: { ...e, sha256: 'A'.repeat(64) } } }, { ...good, stocks: { NVDA: { ...e, json_sha256: 'f'.repeat(65) } } },
    { ...good, stocks: { NVDA: { ...e, asset_id: good.qgv.asset_id } } }, { ...good, stocks: { NVDA: null } }, { ...good, stocks: { NVDA: [e] } },
    { ...good, qgv: { ...good.qgv, symbol: 'X' } }, { ...good, qgv: { ...good.qgv, bytes: 1_800_001 } }, [good], null, 'x',
  ];
  for (const [i, v] of bad.entries()) assert.equal(nvda(v), 'INVALID', 'case ' + i);
  for (const v of [[good], null, { ...good, qgv: { ...good.qgv, bytes: 0 } }]) assert.equal(kisStockIndexEntry(v, null), 'INVALID', 'qgv part');
  assert.equal(kisStockIndexEntry(good, 'ZZZZ'), 'INVALID', 'a symbol outside the Worker list');
  assert.equal(nvda({ ...good, stocks: {} }), 'MISSING', 'an empty stock map: every request is 404');
  assert.equal(nvda({ ...good, stocks: { AAPL: { ...e, symbol: 'AAPL' } } }), 'MISSING');
  assert.equal(nvda(JSON.parse(JSON.stringify(good).replace('"stocks":{', '"stocks":{"__proto__":{},'))).asset_id, e.asset_id, 'own keys only');
  assert.equal(kisStockIndexEntry({ ...good, stocks: { 'BRK-B': { ...e, symbol: 'BRK/B' } } }, 'BRK-B').symbol, 'BRK/B', 'request symbol key, view symbol value');
  assert.equal(nvda({ ...good, stocks: { NVDA: { ...e, bytes: 1_800_000, json_bytes: 1_800_000 } } }).bytes, 1_800_000, 'the cap itself');
  // Proposal A: the other entries are not read per request (the publish workflow checks all of them before it writes the index).
  for (const others of [{ ZZZZ: e }, { BRK_B: e }, { AAPL: { ...e, symbol: 'AAPL' } }, { AAPL: { ...e, extra: 1 } }]) {
    assert.deepEqual(nvda({ ...good, stocks: { NVDA: e, ...others } }), e, 'another entry does not stop this one');
  }
});

test('redirect target: only https on exactly the release asset host, default port, no user info, status 302', () => {
  const r = (status, location) => new Response(null, { status, headers: location === undefined ? {} : { Location: location } });
  assert.equal(kisAssetRedirectTarget(r(302, SIGNED)), SIGNED);
  for (const location of [
    'https://' + ASSET_HOST + '.evil.test/x', 'https://evil.test/' + ASSET_HOST + '/x', 'https://x.' + ASSET_HOST + '/x',
    'http://' + ASSET_HOST + '/x', 'https://user:pass@' + ASSET_HOST + '/x', 'https://user@' + ASSET_HOST + '/x',
    'https://' + ASSET_HOST + ':8443/x', 'https://' + ASSET_HOST + ':443/x', 'https://' + ASSET_HOST + './x', 'https://' + ASSET_HOST,
    '/x', '//' + ASSET_HOST + '/x', ASSET_HOST + '/x', 'https:' + ASSET_HOST + '/x', 'https:\\\\' + ASSET_HOST + '/x',
    'https://objects.githubusercontent.com/x', 'https://' + ASSET_HOST.toUpperCase() + '/x', 'ftp://' + ASSET_HOST + '/x', '',
  ]) assert.equal(kisAssetRedirectTarget(r(302, location)), null, location);
  assert.equal(kisAssetRedirectTarget(r(302)), null, 'no Location');
  for (const status of [200, 301, 303, 307, 308, 404]) assert.equal(kisAssetRedirectTarget(r(status, SIGNED)), null, String(status));
  assert.equal(kisAssetRedirectTarget(new Response(makeAsset().gz, { status: 200 })), null, 'a 200 stream');
});

// The view itself is no longer checked here (owner 2026-11-21 light read): the app's stockParts and its readers check it
// (implementation/tools/web_app_kis_private_node_test.js 'stockParts' cases). The Worker keeps every pin below.

// ---- the route ------------------------------------------------------------------------------------------------------------
test('happy path: index, asset API, one credential-free hop; the pinned gzip bytes go out as they are, Content-Encoding gzip', async () => {
  const asset = makeAsset(), s = setup({ asset }), r = await s.run();
  assert.equal(r.status, 200); noStore(r);
  assert.equal(r.headers.get('Access-Control-Allow-Origin'), ORIGIN);
  assert.equal(r.headers.get('Content-Type'), 'application/json; charset=utf-8');
  assert.equal(r.headers.get('Content-Encoding'), 'gzip');
  const out = new Uint8Array(await r.arrayBuffer());
  assert.deepEqual(out, new Uint8Array(asset.gz), 'the published gzip bytes, not inflated, not re-compressed');
  assert.deepEqual(new Uint8Array(gunzipSync(out)), new Uint8Array(asset.json), 'they inflate to the published JSON');
  const [index, api, hop, ...rest] = s.upstream();
  assert.equal(rest.length, 0, 'three upstream reads, no more');
  assert.equal(index.url, INDEX_URL);
  assert.equal(index.init.headers.Authorization, 'Bearer ' + FAKE_TOKEN); assert.equal(index.init.redirect, 'manual');
  assert.equal(api.url, API + '/releases/assets/7');
  assert.equal(api.init.headers.Accept, 'application/octet-stream');
  assert.equal(api.init.headers.Authorization, 'Bearer ' + FAKE_TOKEN);
  assert.equal(api.init.headers['X-GitHub-Api-Version'], '2022-11-28'); assert.ok(api.init.headers['User-Agent']);
  assert.equal(api.init.redirect, 'manual'); assert.equal(api.init.cache, 'no-store');
  assert.equal(hop.url, SIGNED);
  assert.equal(hop.init.redirect, 'manual'); assert.equal(hop.init.cache, 'no-store');
  assert.ok(!headerNames(hop.init).includes('authorization'), 'no Authorization on the redirect');
  assert.ok(!headerNames(hop.init).includes('cookie'), 'no cookie on the redirect');
  assert.doesNotMatch(JSON.stringify(hop.init.headers), /SYNTHETICONLY|github_pat_/);
  assert.deepEqual(s.limiterCalls, ['/admit', '/release'], 'one admission, one release');
  assert.equal(s.calls.length, 5, 'tokeninfo + root probe (404) + index + asset API + redirect target');
});

test('EXPIRING still serves with the one exposed date header; the share-class key reads the view symbol', async () => {
  let s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-27' } }), r = await s.run();
  assert.equal(r.status, 200); assert.equal(r.headers.get('X-Private-Token-Expires-On'), '2026-11-27');
  assert.equal(r.headers.get('Access-Control-Expose-Headers'), 'X-Private-Token-Expires-On');
  const asset = makeAsset(makeView({ symbol: 'BRK/B' }));
  s = setup({ asset, index: makeIndex(asset, { stocks: { 'BRK-B': entryOf(asset, 7, 'BRK/B') } }) });
  r = await s.run('/kis/stock?symbol=BRK-B');
  assert.equal(r.status, 200); assert.deepEqual(new Uint8Array(await r.arrayBuffer()), new Uint8Array(asset.gz));
});

test('?part=qgv: the index QGV object through the same pins and hop; nothing else is a part', async () => {
  const stock = makeAsset(), qgvJson = Buffer.from(JSON.stringify({ schema: K('qgv/1'), rows: {} }), 'utf8'), qgvGz = gzipSync(qgvJson);
  const index = makeIndex(stock, { qgv: { asset_id: 9, name: 'q.json.gz', bytes: qgvGz.length, sha256: sha(qgvGz), json_bytes: qgvJson.length, json_sha256: sha(qgvJson) } });
  let s = setup({ asset: stock, index, target: () => new Response(qgvGz, { status: 200 }) }), r = await s.run('/kis/stock?part=qgv');
  assert.equal(r.status, 200); assert.equal(r.headers.get('Content-Encoding'), 'gzip');
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), new Uint8Array(qgvGz));
  assert.equal(s.upstream()[1].url, API + '/releases/assets/9', 'the QGV asset id from the index');
  assert.deepEqual(s.limiterCalls, ['/admit', '/release'], 'one admission like a stock read');
  s = setup({ asset: stock, index, target: () => new Response(stock.gz, { status: 200 }) }); r = await s.run('/kis/stock?part=qgv');
  assert.equal(r.status, 502); assert.equal(await code(r), 'KIS_STOCK_PIN', 'another asset under the QGV id is refused by its pins');
  for (const path of ['/kis/stock?part=QGV', '/kis/stock?part=qgv&symbol=NVDA', '/kis/stock?part=stock', '/kis/stock?part=qgv#x', '/kis/qgv?part=qgv']) {
    s = setup(); r = await s.run(path);
    assert.equal(r.status, 400, path); assert.equal(await code(r), 'REQUEST_INVALID', path); assert.equal(s.calls.length, 0, path);
  }
});

test('unauthenticated or wrong symbol: refused before any GitHub call or admission', async () => {
  for (const authStatus of [401, 403]) {
    const s = setup({ authStatus }), r = await s.run();
    assert.equal(r.status, 403); assert.equal(await code(r), 'AUTH_FORBIDDEN');
    assert.equal(s.upstream().length, 0); assert.deepEqual(s.limiterCalls, []);
  }
  let s = setup(), r = await s.run('/kis/stock?symbol=NVDA', { Authorization: '' });
  assert.equal(r.status, 403); assert.equal(s.calls.length, 0);
  for (const path of ['/kis/stock', '/kis/stock?symbol=nvda', '/kis/stock?symbol=ZZZZ', '/kis/stock?symbol=NVDA&x=1', '/kis/stock?symbol=../x', '/kis/stock?symbol=BRK_B']) {
    s = setup(); r = await s.run(path);
    assert.equal(r.status, 400, path); assert.equal(await code(r), 'REQUEST_INVALID'); assert.equal(s.calls.length, 0, path);
  }
  s = setup(); r = await s.run('/kis/stock?symbol=NVDA', { 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization', Authorization: '' }, 'OPTIONS');
  assert.equal(r.status, 204); assert.equal(s.calls.length, 0);
  s = setup({ env: { PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2026-11-20' } }); r = await s.run();
  assert.equal(r.status, 503); assert.equal(await code(r), 'TOKEN_EXPIRED'); assert.equal(s.upstream().length, 0);
});

test('rate limit: one admission per request, the second request inside the spacing is refused before GitHub', async () => {
  const s = setup();
  assert.equal((await s.run()).status, 200);
  const before = s.upstream().length, r = await s.run();
  assert.equal(r.status, 429); assert.equal(await code(r), 'RATE_LIMITED'); assert.ok(Number(r.headers.get('Retry-After')) >= 1);
  assert.equal(s.upstream().length, before, 'no GitHub call when refused');
  assert.deepEqual(s.limiterCalls, ['/admit', '/release', '/admit']);
});

test('index: missing file and missing symbol are 404, an invalid or oversized index is KIS_STOCK_INDEX_INVALID', async () => {
  let s = setup({ indexResponse: () => new Response('{"message":"Not Found"}', { status: 404 }) }), r = await s.run();
  assert.equal(r.status, 404); assert.equal(await code(r), 'KIS_SERIES_NOT_FOUND'); assert.equal(s.upstream().length, 1);
  s = setup(); r = await s.run('/kis/stock?symbol=AAPL');
  assert.equal(r.status, 404); assert.equal(await code(r), 'KIS_SERIES_NOT_FOUND'); assert.equal(s.upstream().length, 1, 'no asset call');
  for (const indexResponse of [() => new Response('{"schema":"x"}'), () => new Response('not json'), () => new Response(Uint8Array.from([0x7b, 0xff])),
    () => new Response(JSON.stringify({ ...makeIndex(), extra: true })), () => new Response('x', { headers: { 'Content-Length': '262145' } }),
    () => new Response(JSON.stringify(makeIndex()) + ' '.repeat(262_144))]) {
    s = setup({ indexResponse }); r = await s.run();
    assert.equal(r.status, 502); assert.equal(await code(r), 'KIS_STOCK_INDEX_INVALID'); assert.equal(s.upstream().length, 1);
  }
  for (const [indexResponse, status, c] of [[() => new Response(FAKE_TOKEN, { status: 401 }), 503, 'TOKEN_REJECTED'],
    [() => new Response(null, { status: 301, headers: { Location: SIGNED } }), 502, 'REPO_MOVED'], [() => { throw new TypeError('down'); }, 503, 'UPSTREAM_UNAVAILABLE']]) {
    s = setup({ indexResponse }); r = await s.run();
    assert.equal(r.status, status, c); assert.equal(await code(r), c); assert.equal(s.upstream().length, 1, c + ': the index redirect is not followed');
  }
});

test('asset API: anything but the one accepted 302 is refused and nothing further is fetched', async () => {
  const cases = [
    () => new Response(makeAsset().gz, { status: 200 }),
    ...[301, 303, 307, 308].map((status) => () => new Response(null, { status, headers: { Location: SIGNED } })),
    () => new Response(null, { status: 302 }),
    ...['https://evil.test/x', 'https://' + ASSET_HOST + '.evil.test/x', 'http://' + ASSET_HOST + '/x', '/x', 'https://u:p@' + ASSET_HOST + '/x',
      'https://' + ASSET_HOST + ':444/x'].map((Location) => () => new Response(null, { status: 302, headers: { Location } })),
    () => new Response('{}', { status: 404 }),
  ];
  for (const [i, assetApi] of cases.entries()) {
    const s = setup({ assetApi }), r = await s.run();
    assert.equal(r.status, 502, 'case ' + i); assert.equal(await code(r), 'KIS_STOCK_ASSET_REDIRECT');
    assert.equal(s.upstream().length, 2, 'case ' + i + ': index and asset API only');
    assert.deepEqual(s.limiterCalls, ['/admit', '/release']);
  }
  for (const [assetApi, status, c] of [[() => new Response(FAKE_TOKEN, { status: 401 }), 503, 'TOKEN_REJECTED'],
    [() => new Response('x', { status: 403, headers: { 'x-ratelimit-remaining': '0' } }), 503, 'UPSTREAM_RATE_LIMITED'],
    [() => new Response('x', { status: 502 }), 503, 'UPSTREAM_UNAVAILABLE'], [() => { throw new TypeError('down'); }, 503, 'UPSTREAM_UNAVAILABLE']]) {
    const s = setup({ assetApi }), r = await s.run();
    assert.equal(r.status, status, c); assert.equal(await code(r), c); assert.equal(s.upstream().length, 2);
  }
});

test('redirect target: a second hop is refused, a non-200 is refused, the second Location is never fetched', async () => {
  for (const status of [301, 302, 303, 307, 308]) {
    const s = setup({ target: () => new Response(null, { status, headers: { Location: SIGNED + '&again=1' } }) }), r = await s.run();
    assert.equal(r.status, 502, String(status)); assert.equal(await code(r), 'KIS_STOCK_ASSET_REDIRECT');
    assert.equal(s.upstream().length, 3, 'exactly one hop');
  }
  for (const target of [() => new Response('expired', { status: 403 }), () => new Response('x', { status: 404 }), () => new Response('x', { status: 206 }),
    () => { throw new TypeError('down'); }]) {
    const s = setup({ target }), r = await s.run();
    assert.equal(r.status, 503); assert.equal(await code(r), 'UPSTREAM_UNAVAILABLE'); assert.equal(s.upstream().length, 3);
  }
});

test('pins: gzip size and sha256; a body over the pinned size is cut off', async () => {
  const asset = makeAsset(), e = entryOf(asset);
  const tampered = Buffer.from(asset.gz); tampered[tampered.length - 9] ^= 1;
  const cases = [
    { index: makeIndex(asset, {}, { sha256: 'f'.repeat(64) }) },
    { index: makeIndex(asset, {}, { bytes: e.bytes + 1 }) },
    { index: makeIndex(asset, {}, { bytes: e.bytes - 1 }) },
    { target: () => new Response(tampered, { status: 200 }) },
    { target: () => new Response(Buffer.concat([asset.gz, Buffer.alloc(4096)]), { status: 200 }), note: 'gzip over its cap' },
    { target: () => new Response(asset.gz, { status: 200, headers: { 'Content-Length': String(e.bytes + 1) } }), note: 'advertised over the cap' },
    { target: () => new Response(null, { status: 200 }) },
  ];
  for (const [i, opts] of cases.entries()) {
    const s = setup({ asset, ...opts }), r = await s.run();
    assert.equal(r.status, 502, 'case ' + i); assert.equal(await code(r), 'KIS_STOCK_PIN', 'case ' + i + ' ' + (opts.note ?? ''));
  }
  // A stream that keeps sending is cancelled once it passes the pinned gzip size.
  let pulled = 0, cancelled = false;
  const endless = () => new Response(new ReadableStream({ pull(c) { pulled += 1; c.enqueue(new Uint8Array(65_536)); }, cancel() { cancelled = true; } }), { status: 200 });
  const r = await setup({ asset, target: endless }).run();
  assert.equal(await code(r), 'KIS_STOCK_PIN'); assert.ok(cancelled, 'cancelled'); assert.ok(pulled <= 3, 'stops near the cap');
});

test('content is not read here: a pinned view of any shape passes as published (the app refuses a wrong one)', async () => {
  for (const view of [makeView({ evaluation_day: '2026-11-18' }), makeView({ schema: K('bars/1') }), makeView({ rows: [row(1).slice(0, 16)] })]) {
    const asset = makeAsset(view), r = await setup({ asset }).run();
    assert.equal(r.status, 200); assert.deepEqual(new Uint8Array(await r.arrayBuffer()), new Uint8Array(asset.gz));
  }
  // Pinned bytes that are not gzip still go out as pinned; the browser's inflate fails and the app shows its error code.
  const junk = Buffer.from('not gzip at all, synthetic'), r = await setup({ asset: { json: Buffer.from('{}'), gz: junk } }).run();
  assert.equal(r.status, 200); assert.equal(r.headers.get('Content-Encoding'), 'gzip');
});

test('the other routes keep their own reads: /kis/chart still reads its Contents file and refuses any redirect', async () => {
  const s = setup({ indexResponse: () => new Response('{}') });
  const handler = createHandler({ fetch: async (input, init) => {
    const url = String(input);
    s.calls.push({ url, init });
    if (url === 'https://oauth2.googleapis.com/tokeninfo') return new Response(JSON.stringify({ aud: 'mock-client-id', email: OWNER_EMAIL, email_verified: true, expires_in: '3600' }));
    return new Response(null, { status: 302, headers: { Location: SIGNED } });
  }, now: () => NOW });
  const limiter = new HistoryRateLimiter({ storage: new Storage() }, {}, { now: () => NOW });
  const env = { ALLOWED_EMAIL: OWNER_EMAIL, GOOGLE_CLIENT_ID: 'mock-client-id', PRIVATE_REPO_READ_TOKEN: FAKE_TOKEN, PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: '2027-01-31',
    HISTORY_RATE_LIMITER: { idFromName: (n) => n, get: () => ({ fetch: (i, init) => limiter.fetch(i instanceof Request ? i : new Request(i, init)) }) } };
  const r = await handler(new Request('https://w.example/kis/chart?symbol=NVDA', { headers: { Origin: ORIGIN, Authorization: 'Bearer x' } }), env);
  assert.equal(r.status, 502); assert.equal(await code(r), 'REPO_MOVED');
  const reads = s.calls.filter((c) => c.url !== 'https://oauth2.googleapis.com/tokeninfo');
  assert.deepEqual(reads.map((c) => c.url), [API + '/contents/chart/N/NVDA.json?ref=data'], 'the 302 to the asset host is not followed elsewhere');
});

// ---- bundle path (owner 2026-11-22: GitHub private release bundles + 64 index shards) ------------------------------------
const bucketOf = (symbol) => createHash('sha256').update(symbol).digest()[0] >> 2;
const shardName = (b) => String(b).padStart(2, '0') + '.json';
const GEN = { publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: '2026-11-19', release_tag: 'view-2026-11-19-' + 'b'.repeat(12), generation_sha256: 'c'.repeat(64) };
// One bundle holding the members in order; the root pins every shard. qgv is a separate whole asset (id 9).
function makePacks(members, { shardOverrides = {}, rootOverrides = {}, qgv } = {}) {
  const pack = Buffer.concat(members.map((m) => m.asset.gz)), packSha = sha(pack);
  const shards = {}, files = {};
  let offset = 0;
  for (const m of members) {
    const b = bucketOf(m.symbol), name = shardName(b);
    shards[name] ??= { schema: K('stock-pack-shard/1'), ...GEN, bucket: b, stocks: {} };
    shards[name].stocks[m.symbol] = { pack: packSha, offset, bytes: m.asset.gz.length, sha256: sha(m.asset.gz), json_bytes: m.asset.json.length, json_sha256: sha(m.asset.json) };
    offset += m.asset.gz.length;
  }
  const pins = {};
  for (const [name, shard] of Object.entries(shards)) {
    const bytes = Buffer.from(JSON.stringify({ ...shard, ...(shardOverrides[name] ?? {}) }), 'utf8');
    files[name] = bytes; pins[name] = { bytes: bytes.length, sha256: sha(bytes) };
  }
  const root = { schema: K('stock-pack-root/1'), ...GEN, buckets: 64, bucket_rule: 'sha256(symbol)[0]>>2',
    qgv: qgv ?? { asset_id: 9, name: 'qgv.json.gz', bytes: 10, sha256: 'd'.repeat(64), json_bytes: 20, json_sha256: 'e'.repeat(64) },
    packs: { [packSha]: { asset_id: 11, bytes: pack.length } }, shards: pins, ...rootOverrides };
  // The release-asset host answers a Range request with the exact 206 slice.
  const serve = (init) => {
    const m = /^bytes=(\d+)-(\d+)$/.exec(init?.headers?.Range ?? '');
    if (!m) return new Response(pack, { status: 200 });
    const a = Number(m[1]), z = Number(m[2]);
    return new Response(pack.subarray(a, z + 1), { status: 206, headers: { 'Content-Range': 'bytes ' + a + '-' + z + '/' + pack.length, 'Content-Length': String(z - a + 1) } });
  };
  return { rootBytes: Buffer.from(JSON.stringify(root), 'utf8'), shards: files, serve, pack, root };
}
const NV = () => ({ symbol: 'NVDA', asset: makeAsset() });
const AA = () => ({ symbol: 'AAPL', asset: makeAsset(makeView({ symbol: 'AAPL' })) });

test('bundle path: root, the symbol\'s pinned shard, asset API, one credential-free Range read of the member', async () => {
  const nv = NV(), aa = AA(), packs = makePacks([aa, nv]), s = setup({ packs }), r = await s.run();
  assert.equal(r.status, 200); noStore(r); assert.equal(r.headers.get('Content-Encoding'), 'gzip');
  assert.deepEqual(new Uint8Array(await r.arrayBuffer()), new Uint8Array(nv.asset.gz), 'exactly the member, not the bundle');
  const [root, shard, api, hop, ...rest] = s.upstream();
  assert.equal(rest.length, 0, 'four upstream reads');
  assert.equal(root.url, ROOT_URL); assert.equal(shard.url, SHARD_URL(shardName(bucketOf('NVDA'))));
  assert.equal(shard.init.headers.Authorization, 'Bearer ' + FAKE_TOKEN); assert.equal(shard.init.redirect, 'manual');
  assert.equal(api.url, API + '/releases/assets/11', 'the bundle asset id');
  assert.equal(hop.url, SIGNED); assert.equal(hop.init.redirect, 'manual');
  assert.equal(hop.init.headers.Authorization, undefined, 'no credentials on the redirect target');
  assert.equal(hop.init.headers.Range, 'bytes=' + aa.asset.gz.length + '-' + (aa.asset.gz.length + nv.asset.gz.length - 1));
  assert.ok(!s.calls.some((c) => c.url === INDEX_URL), 'the single index is not read while the root exists');
});

test('bundle path: shard pin, generation and membership are checked before any asset call', async () => {
  const nv = NV(), name = shardName(bucketOf('NVDA'));
  let packs = makePacks([nv]); packs.shards[name] = Buffer.concat([packs.shards[name], Buffer.from(' ')]);
  let s = setup({ packs }), r = await s.run();
  assert.equal(r.status, 502); assert.equal(await code(r), 'KIS_STOCK_INDEX_INVALID', 'a shard that does not match its pin');
  assert.equal(s.upstream().length, 2);
  packs = makePacks([nv], { shardOverrides: { [name]: { release_tag: 'view-2026-11-18-' + 'f'.repeat(12) } } });
  s = setup({ packs }); r = await s.run();
  assert.equal(r.status, 502); assert.equal(await code(r), 'KIS_STOCK_INDEX_INVALID', 'a shard of another generation'); assert.equal(s.upstream().length, 2);
  packs = makePacks([AA()]); s = setup({ packs }); r = await s.run();
  assert.ok([404, 502].includes(r.status), 'a symbol with no member is not served');
  assert.ok(['KIS_SERIES_NOT_FOUND', 'KIS_STOCK_INDEX_INVALID'].includes(await code(r)));
  assert.equal(s.upstream().filter((c) => c.url.startsWith(API + '/releases/')).length, 0, 'no asset call');
  for (const over of [{ buckets: 32 }, { bucket_rule: 'x' }, { schema: 'x' }, { packs: [] }]) {
    s = setup({ packs: makePacks([nv], { rootOverrides: over }) }); r = await s.run();
    assert.equal(r.status, 502); assert.equal(await code(r), 'KIS_STOCK_INDEX_INVALID', JSON.stringify(over)); assert.equal(s.upstream().length, 1);
  }
});

test('bundle path: the member must come back as exactly the requested 206 range with its pinned bytes', async () => {
  const nv = NV(), aa = AA();
  const cases = [
    [(p) => () => new Response(p.pack, { status: 200 }), 502, 'KIS_STOCK_PIN', 'the whole bundle (200) is refused unread'],
    [(p) => () => new Response(p.pack.subarray(0, nv.asset.gz.length), { status: 206, headers: { 'Content-Range': 'bytes 0-' + (nv.asset.gz.length - 1) + '/' + p.pack.length } }), 502, 'KIS_STOCK_PIN', 'another range'],
    [(p) => (url, init) => { const res = p.serve(init); return new Response(Buffer.alloc(nv.asset.gz.length), { status: 206, headers: { 'Content-Range': res.headers.get('Content-Range') } }); }, 502, 'KIS_STOCK_PIN', 'right range, wrong bytes'],
    [() => () => new Response('x', { status: 500 }), 503, 'UPSTREAM_UNAVAILABLE', 'an error status'],
  ];
  for (const [make, status, c, why] of cases) {
    const packs = makePacks([aa, nv]), s = setup({ packs, target: make(packs) }), r = await s.run();
    assert.equal(r.status, status, why); assert.equal(await code(r), c, why); assert.equal(s.upstream().length, 4, why);
  }
});

test('bundle path: ?part=qgv reads the root\'s qgv asset whole; no root (404) keeps the single index', async () => {
  const qgvJson = Buffer.from(JSON.stringify({ schema: K('qgv/1'), rows: {} }), 'utf8'), qgvGz = gzipSync(qgvJson);
  const packs = makePacks([NV()], { qgv: { asset_id: 9, name: 'q.json.gz', bytes: qgvGz.length, sha256: sha(qgvGz), json_bytes: qgvJson.length, json_sha256: sha(qgvJson) } });
  let s = setup({ packs, target: (url, init) => { assert.equal(init.headers.Range, undefined, 'no Range for a whole asset'); return new Response(qgvGz, { status: 200 }); } });
  let r = await s.run('/kis/stock?part=qgv');
  assert.equal(r.status, 200); assert.deepEqual(new Uint8Array(await r.arrayBuffer()), new Uint8Array(qgvGz));
  assert.deepEqual(s.upstream().map((c) => c.url), [ROOT_URL, API + '/releases/assets/9', SIGNED]);
  s = setup(); r = await s.run();
  assert.equal(r.status, 200);
  assert.deepEqual(s.calls.filter((c) => c.url.startsWith(API)).map((c) => c.url), [ROOT_URL, INDEX_URL, API + '/releases/assets/7'], 'root probe, then the single index as before');
});
