import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
// The post-admission upstream deadline and the owner-request lease (owner 2026-11-28): after admission every upstream read of a
// request ends within UPSTREAM_DEADLINE_MS (+ the abort grace), so no live request outlives its LEASE_MS lease, and a request the
// runtime kills mid-way (CPU limit 1102: no finally, no release) frees the slot LEASE_MS after its admission. Virtual time drives
// every timer, the upstream delays and the Durable Object clock. Synthetic values only (schema names assembled at run time).
globalThis.fetch = async () => { throw new Error('Live network transport is disabled in these tests'); };
// Virtual time needs every step on the event loop: Node runs crypto.subtle.digest on its thread pool, the Workers runtime inline.
// The same SHA-256, computed inline here.
SubtleCrypto.prototype.digest = async function digest(algorithm, data) {
  assert.equal(algorithm, 'SHA-256');
  const out = createHash('sha256').update(ArrayBuffer.isView(data) ? data : new Uint8Array(data)).digest();
  return out.buffer.slice(out.byteOffset, out.byteOffset + out.length);
};
const { createHandler, HistoryRateLimiter, LIMITER_TIMING: T } = await import('../src/index.js');

test('lease outlives the deadline, its abort grace and the release call; spacing and cap unchanged', async () => {
  assert.deepEqual(T, { LEASE_MS: 15_000, UPSTREAM_DEADLINE_MS: 10_000, UPSTREAM_ABORT_GRACE_MS: 250, LIMITER_TIMEOUT_MS: 2000, MIN_SPACING_MS: 5000, WINDOW_MS: 60_000 });
  assert.ok(T.LEASE_MS > T.UPSTREAM_DEADLINE_MS + T.UPSTREAM_ABORT_GRACE_MS + T.LIMITER_TIMEOUT_MS, 'lease > deadline + grace + release timeout');
  assert.ok(T.UPSTREAM_ABORT_GRACE_MS > 0 && T.UPSTREAM_ABORT_GRACE_MS < 1000);
  const config = await readFile(new URL('../wrangler.toml', import.meta.url), 'utf8');
  assert.match(config, /REQUESTS_PER_MINUTE\s*=\s*"12"/, 'the per-minute cap stays 12');
});

const K = (rest) => ['kis', rest].join('-');
const sha = (b) => createHash('sha256').update(b).digest('hex');
const ORIGIN = 'https://kco994553-star.github.io', API = 'https://api.github.com/repos/kco994553-star/investment-system1-kis-private';
const NOW = Date.UTC(2026, 10, 27, 3), OWNER = ['owner', 'example.test'].join('@'), CLIENT = 'synthetic-client';
const SIGNED = 'https://release-assets.githubusercontent.com/x/y?sig=SYNTHETICSIGNATURE';
const GEN = { publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: '2026-11-26', release_tag: 'view-synthetic', generation_sha256: 'c'.repeat(64) };
const SYM = 'NVDA', bucket = createHash('sha256').update(SYM).digest()[0] >> 2, shardName = String(bucket).padStart(2, '0') + '.json';
const member = randomBytes(40_000), offset = 100, packBytes = 300_000, packSha = 'a'.repeat(64);
const shard = Buffer.from(JSON.stringify({ schema: K('stock-pack-shard/1'), ...GEN, bucket,
  stocks: { [SYM]: { pack: packSha, offset, bytes: member.length, sha256: sha(member), json_bytes: 100_000, json_sha256: 'e'.repeat(64) } } }));
const shards = {};
for (let b = 0; b < 64; b++) shards[String(b).padStart(2, '0') + '.json'] = { bytes: b === bucket ? shard.length : 100, sha256: b === bucket ? sha(shard) : 'f'.repeat(64) };
const root = Buffer.from(JSON.stringify({ schema: K('stock-pack-root/1'), ...GEN, buckets: 64, bucket_rule: 'sha256(symbol)[0]>>2',
  qgv: { asset_id: 9, name: 'q.json.gz', bytes: 10, sha256: 'd'.repeat(64), json_bytes: 20, json_sha256: 'e'.repeat(64) },
  packs: { [packSha]: { asset_id: 11, bytes: packBytes } }, shards }));
const statusRecord = Buffer.from(JSON.stringify({ schema: ['private', 'area-status/1'].join('-'), publication_scope: 'OWNER_PRIVATE_ONLY', run_at: '2026-11-27T02:00:00Z',
  worker_read_token: { state: 'NO_EXPIRY', code: null, expires_on: null, days_left: null, verification: 'NOT_CHECKED' } }));
const ROOT_URL = API + '/contents/views/kis-stock-packs.json?ref=data', SHARD_URL = API + '/contents/views/kis-stock-packs/' + shardName + '?ref=data';
const STATUS_URL = API + '/contents/status/private-area.json?ref=data';
const HANG = Infinity, DRIP = 'drip';

// Virtual time: timers, upstream delays and the limiter clock all read clock.now; run() fires the earliest timer, then lets
// the promise chains settle, until the request answers.
function world() {
  const clock = { now: NOW }, timers = new Map();
  let seq = 0, live = 0, lastSettled = null, admittedAt = null;
  const setTimeout = (fn, ms = 0) => { const id = ++seq; timers.set(id, { at: clock.now + ms, fn, id }); return id; };
  const clearTimeout = (id) => { timers.delete(id); };
  const settle = async () => { for (let i = 0; i < 30; i++) await new Promise((r) => setImmediate(r)); };
  async function run(promise) {
    let done = false;
    promise.then(() => { done = true; }, () => { done = true; });
    await settle();
    while (!done) {
      const next = [...timers.values()].sort((a, b) => a.at - b.at || a.id - b.id)[0];
      if (!next) throw new Error('no timer left and no answer');
      timers.delete(next.id); clock.now = Math.max(clock.now, next.at); next.fn(); await settle();
    }
    return promise;
  }
  const aborted = () => new DOMException('The operation was aborted.', 'AbortError');
  // One upstream answer after `delay` virtual ms (HANG: never); its body is the bytes, or with DRIP a body that never ends.
  // A call ends (live - 1) when it answers with a complete body, fails, or is aborted through its signal.
  function upstream(signal, delay, make, body) {
    live++;
    let ended = false;
    const end = () => { if (!ended) { ended = true; live--; lastSettled = clock.now; } };
    return new Promise((resolve, reject) => {
      const abort = () => { clearTimeout(id); end(); reject(aborted()); };
      if (signal?.aborted) { abort(); return; }
      signal?.addEventListener('abort', abort, { once: true });
      const id = delay === HANG ? null : setTimeout(() => {
        if (body !== DRIP) { signal?.removeEventListener('abort', abort); end(); resolve(make(null)); return; }
        // Headers now; the body never completes and fails when the request's signal aborts.
        signal?.removeEventListener('abort', abort);
        const stream = new ReadableStream({ start(c) {
          c.enqueue(new Uint8Array(8));
          signal?.addEventListener('abort', () => { end(); c.error(aborted()); }, { once: true });
        }, pull() { return new Promise(() => {}); } });
        resolve(make(stream));
      }, delay);
    });
  }
  class Storage {
    value; queue = Promise.resolve();
    async get() { return structuredClone(this.value); }
    async put(key, value) { this.value = structuredClone(value); }
    async transaction(cb) { const r = this.queue.then(() => cb(this)); this.queue = r.catch(() => {}); return r; }
  }
  const storage = new Storage(), limiter = new HistoryRateLimiter({ storage }, {}, { now: () => clock.now });
  const namespace = { idFromName: (n) => n, get: () => ({ fetch: async (input, init) => {
    const r = await limiter.fetch(new Request(input, init));
    if (String(input).endsWith('/admit') && r.status === 200) admittedAt = clock.now;
    return r;
  } }) };
  const env = { ALLOWED_EMAIL: OWNER, GOOGLE_CLIENT_ID: CLIENT, PRIVATE_REPO_READ_TOKEN: ['github', 'pat', 'SYNTHETICONLY'].join('_'), PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER',
    TIINGO_API_KEY: 'synthetic-tiingo-key', HISTORY_RATE_LIMITER: namespace };
  // delays: { root, shard, api, range, status, yahoo, tiingo } in virtual ms (HANG never answers); drip: names whose body never ends.
  function handler(delays = {}, drip = []) {
    const d = (k) => delays[k] ?? 0, b = (k) => (drip.includes(k) ? DRIP : null);
    const fetch = async (url, init = {}) => {
      if (url === 'https://oauth2.googleapis.com/tokeninfo') return new Response(JSON.stringify({ aud: CLIENT, email: OWNER, email_verified: 'true', expires_in: '3599' }));
      const s = init.signal;
      if (url === ROOT_URL) return upstream(s, d('root'), (st) => new Response(st ?? root), b('root'));
      if (url === SHARD_URL) return upstream(s, d('shard'), (st) => new Response(st ?? shard), b('shard'));
      if (url === STATUS_URL) return upstream(s, d('status'), (st) => new Response(st ?? statusRecord), b('status'));
      if (url.startsWith(API + '/releases/assets/')) return upstream(s, d('api'), () => new Response(null, { status: 302, headers: { Location: SIGNED } }));
      if (url === SIGNED) return upstream(s, d('range'), (st) => new Response(st ?? member, { status: 206,
        headers: { 'Content-Range': 'bytes ' + offset + '-' + (offset + member.length - 1) + '/' + packBytes, 'Content-Length': String(member.length) } }), b('range'));
      if (url.startsWith('https://query1.finance.yahoo.com/')) return upstream(s, d('yahoo'), () => new Response('{}', { status: 500 }));
      if (url.startsWith('https://api.tiingo.com/')) return upstream(s, d('tiingo'), () => new Response('{}', { status: 500 }));
      throw new Error('unexpected upstream in test');
    };
    return createHandler({ fetch, now: () => clock.now, setTimeout, clearTimeout });
  }
  const request = (path) => new Request('https://private-worker.example' + path, { headers: { Origin: ORIGIN, Authorization: 'Bearer synthetic-access-token' } });
  return { clock, timers, storage, env, handler, request, run, state: () => ({ live, lastSettled, admittedAt }) };
}
const code = async (r) => JSON.parse(await r.text()).error?.code;

test('no live request outlives its lease: every upstream read ends within the deadline after admission', async () => {
  const limit = T.UPSTREAM_DEADLINE_MS + T.UPSTREAM_ABORT_GRACE_MS;
  const named = [
    // [label, path, delays, dripping bodies, status, code]
    ['root 7 s, shard never answers (was 7 + 8 s)', '/kis/stock?symbol=' + SYM, { root: 7000, shard: HANG }, [], 503, 'UPSTREAM_UNAVAILABLE'],
    ['root, shard, asset API 3 s each, the Range read never answers (was up to 3 + 3 + 15 s)', '/kis/stock?symbol=' + SYM, { root: 3000, shard: 3000, api: 3000, range: HANG }, [], 503, 'UPSTREAM_UNAVAILABLE'],
    ['the root body never ends (no call timer covers a GitHub body)', '/kis/stock?symbol=' + SYM, {}, ['root'], 503, 'UPSTREAM_UNAVAILABLE'],
    ['the shard body never ends (capped loop)', '/kis/stock?symbol=' + SYM, { root: 2000 }, ['shard'], 503, 'UPSTREAM_UNAVAILABLE'],
    ['the member body never ends (native read, Content-Length exact)', '/kis/stock?symbol=' + SYM, { root: 1000, shard: 1000, api: 1000 }, ['range'], 503, 'UPSTREAM_UNAVAILABLE'],
    ['the qgv part: asset API never answers', '/kis/stock?part=qgv', { root: 4000, api: HANG }, [], 503, 'UPSTREAM_UNAVAILABLE'],
    ['/history: Yahoo never answers', '/history?symbol=AAPL&range=1mo', { yahoo: HANG }, [], 504, 'YAHOO_TIMEOUT'],
    ['/history: Yahoo fails at 9.5 s, the fallback gets only the time left', '/history?symbol=AAPL&range=1mo', { yahoo: 9500, tiingo: HANG }, [], 504, 'TIINGO_TIMEOUT'],
  ];
  for (const [label, path, delays, drip, status, c] of named) {
    const w = world(), r = await w.run(w.handler(delays, drip)(w.request(path), w.env)), s = w.state();
    assert.equal(r.status, status, label); assert.equal(await code(r), c, label);
    assert.equal(s.live, 0, label + ': no upstream read left running');
    assert.ok(s.lastSettled - s.admittedAt <= limit, label + ': upstream ended ' + (s.lastSettled - s.admittedAt) + ' ms after admission');
    assert.ok(w.clock.now - s.admittedAt < T.LEASE_MS, label + ': answered and released inside the lease');
    assert.equal(w.storage.value.activeLease, 0, label + ': the lease is released');
  }
  // /kis/status: a status body that never ends is the upstream failure, not a malformed record.
  { const w = world(), r = await w.run(w.handler({ status: 2000 }, ['status'])(w.request('/kis/status'), w.env)), s = w.state();
    assert.equal(r.status, 200); const body = JSON.parse(await r.text());
    assert.deepEqual([body.state, body.code], ['ERROR', 'UPSTREAM_UNAVAILABLE']);
    assert.equal(s.live, 0); assert.ok(s.lastSettled - s.admittedAt <= limit); }
  // Every combination of answer times (0 s to never) for the four reads of a stock request.
  const times = [0, 4000, 9000, HANG];
  let n = 0;
  for (const rt of times) for (const st of times) for (const at of times) for (const gt of times) {
    const w = world(), r = await w.run(w.handler({ root: rt, shard: st, api: at, range: gt })(w.request('/kis/stock?symbol=' + SYM), w.env)), s = w.state();
    const label = JSON.stringify([rt, st, at, gt]);
    assert.ok([200, 503].includes(r.status), label);
    // Served when each GitHub contents read keeps its own 8 s and the four reads fit the deadline; otherwise the timeout answer.
    assert.equal(r.status, rt < 8000 && st < 8000 && rt + st + at + gt < T.UPSTREAM_DEADLINE_MS ? 200 : 503, label);
    assert.equal(s.live, 0, label); assert.ok(s.lastSettled - s.admittedAt <= limit, label);
    assert.ok(w.clock.now - s.admittedAt < T.LEASE_MS, label); assert.equal(w.storage.value.activeLease, 0, label);
    n++;
  }
  assert.equal(n, 256);
});

test('a request killed mid-way (no finally, no release) frees the slot LEASE_MS after its admission', async () => {
  const w = world();
  // The first request is admitted and its root read is in flight when the runtime ends it: none of its timers, its finally or
  // its release ever run (as after error 1102), and its upstream read never answers.
  const first = w.handler({ root: HANG })(w.request('/kis/stock?symbol=' + SYM), w.env);
  for (let i = 0; i < 30 && w.state().admittedAt === null; i++) await new Promise((r) => setImmediate(r));
  const admitted = w.state().admittedAt;
  assert.equal(admitted, NOW, 'admitted');
  void first; w.timers.clear();
  assert.notEqual(w.storage.value.activeLease, 0, 'the killed request still holds the lease');
  const next = async (at) => { w.clock.now = admitted + at; return w.run(w.handler()(w.request('/kis/stock?symbol=' + SYM), w.env)); };
  let r = await next(T.MIN_SPACING_MS);
  assert.equal(r.status, 429); assert.equal(await code(r), 'RATE_LIMITED');
  assert.equal(r.headers.get('Retry-After'), String((T.LEASE_MS - T.MIN_SPACING_MS) / 1000), 'refused until the lease ends');
  r = await next(T.LEASE_MS - 1);
  assert.equal(r.status, 429, 'still the killed request\'s lease');
  r = await next(T.LEASE_MS);
  assert.equal(r.status, 200, 'the slot is free LEASE_MS after the admission');
  assert.deepEqual(Buffer.from(await r.arrayBuffer()), member);
  assert.equal(w.storage.value.activeLease, 0, 'and the new request released its own lease');
});
