import assert from 'node:assert/strict';
import { createHash, randomBytes } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';
// The pinned shard and member are read with the native arrayBuffer() when Content-Length equals the pin (owner 2026-11-28, CPU
// on the free plan). This test derives the previous reader from the source itself (both readPinned calls back to the capped
// chunk loop) and requires both builds to answer every mutated upstream answer the same: status, headers and body. Synthetic
// values only; schema names are assembled at run time (tests/test_private_boundary_static.py).
globalThis.fetch = async () => { throw new Error('Live network transport is disabled in these tests'); };
const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8');
const swaps = [
  ["return readPinned(asset, entry.bytes, 'KIS_STOCK_PIN', 'UPSTREAM_UNAVAILABLE', 503);", "return readCapped(asset.body, entry.bytes, 'KIS_STOCK_PIN', 'UPSTREAM_UNAVAILABLE', 503);"],
  ["await readPinned(response, pin.bytes, 'KIS_STOCK_INDEX_INVALID', 'UPSTREAM_UNAVAILABLE', 503);", "await readCapped(response.body, pin.bytes, 'KIS_STOCK_INDEX_INVALID', 'UPSTREAM_UNAVAILABLE', 503);"],
];
let loopSource = source;
for (const [from, to] of swaps) { assert.equal(loopSource.split(from).length, 2, 'one call site: ' + from); loopSource = loopSource.replace(from, to); }
const dir = mkdtempSync(join(tmpdir(), 'kis-native-read-'));
writeFileSync(join(dir, 'loop.mjs'), loopSource);
const NATIVE = await import('../src/index.js'), LOOP = await import(pathToFileURL(join(dir, 'loop.mjs')).href);
rmSync(dir, { recursive: true, force: true });

const K = (rest) => ['kis', rest].join('-');
const sha = (b) => createHash('sha256').update(b).digest('hex');
const ORIGIN = 'https://kco994553-star.github.io', API = 'https://api.github.com/repos/kco994553-star/investment-system1-kis-private';
const NOW = Date.UTC(2026, 10, 27, 3), OWNER = ['owner', 'example.test'].join('@'), CLIENT = 'synthetic-client';
const SIGNED = 'https://release-assets.githubusercontent.com/x/y?sig=SYNTHETICSIGNATURE';
const GEN = { publication_scope: 'OWNER_PRIVATE_ONLY', evaluation_day: '2026-11-26', release_tag: 'view-synthetic', generation_sha256: 'c'.repeat(64) };
const SYM = 'NVDA', bucket = createHash('sha256').update(SYM).digest()[0] >> 2, shardName = String(bucket).padStart(2, '0') + '.json';
const member = randomBytes(70_000), offset = 1234, packBytes = 500_000, packSha = 'a'.repeat(64);
const shard = Buffer.from(JSON.stringify({ schema: K('stock-pack-shard/1'), ...GEN, bucket,
  stocks: { [SYM]: { pack: packSha, offset, bytes: member.length, sha256: sha(member), json_bytes: 200_000, json_sha256: 'e'.repeat(64) } } }));
const shards = {};
for (let b = 0; b < 64; b++) shards[String(b).padStart(2, '0') + '.json'] = { bytes: b === bucket ? shard.length : 100, sha256: b === bucket ? sha(shard) : 'f'.repeat(64) };
const root = Buffer.from(JSON.stringify({ schema: K('stock-pack-root/1'), ...GEN, buckets: 64, bucket_rule: 'sha256(symbol)[0]>>2',
  qgv: { asset_id: 9, name: 'q.json.gz', bytes: 10, sha256: 'd'.repeat(64), json_bytes: 20, json_sha256: 'e'.repeat(64) },
  packs: { [packSha]: { asset_id: 11, bytes: packBytes } }, shards }));
const tokeninfo = Buffer.from(JSON.stringify({ aud: CLIENT, email: OWNER, email_verified: 'true', expires_in: '3599' }));
const URLS = { tokeninfo: 'https://oauth2.googleapis.com/tokeninfo', root: API + '/contents/views/kis-stock-packs.json?ref=data',
  shard: API + '/contents/views/kis-stock-packs/' + shardName + '?ref=data' };

// pulled.bytes: how much of every body the reader asked for (a capped read stops a few chunks past the pin).
const pulled = { bytes: 0 };
function stream(bytes, { chunk = 16384, breakAt = -1 } = {}) {
  let off = 0;
  return new ReadableStream({ pull(c) {
    if (breakAt >= 0 && off >= breakAt) { c.error(new TypeError('broken')); return; }
    if (off >= bytes.length) { c.close(); return; }
    const n = Math.min(chunk, bytes.length - off); c.enqueue(new Uint8Array(bytes.subarray(off, off + n))); off += n; pulled.bytes += n;
  } });
}
// m: { target, status, cl: none|exact|+1|-1|big|lead0, body: exact|+1|-1|flip|empty|x10, encoding, chunk, breakAt, nobody }
// (x10: a body ten times the pin, as a decoded encoded body can be; encoding: a Content-Encoding header on the answer)
function answer(bytes, m, extra = {}, okStatus = 200) {
  let b = bytes;
  if (m.body === '+1') b = Buffer.concat([bytes, Buffer.from(' ')]);
  if (m.body === '-1') b = bytes.subarray(0, bytes.length - 1);
  if (m.body === 'flip') { b = Buffer.from(bytes); b[b.length >> 1] ^= 1; }
  if (m.body === 'empty') b = Buffer.alloc(0);
  if (m.body === 'x10') b = Buffer.concat(Array(10).fill(bytes));
  const headers = { ...extra };
  if (m.encoding !== undefined) headers['Content-Encoding'] = m.encoding;
  const cl = { none: null, exact: String(bytes.length), '+1': String(bytes.length + 1), '-1': String(bytes.length - 1), big: '999999999', lead0: '0' + bytes.length }[m.cl ?? 'none'];
  if (cl !== null) headers['Content-Length'] = cl;
  return new Response(m.nobody ? null : stream(b, m), { status: m.status ?? okStatus, headers });
}
class Storage {
  value; queue = Promise.resolve();
  async get() { return structuredClone(this.value); }
  async put(key, value) { this.value = structuredClone(value); }
  async transaction(cb) { const r = this.queue.then(() => cb(this)); this.queue = r.catch(() => {}); return r; }
}
function run(mod, m) {
  const clock = { now: NOW }, limiter = new mod.HistoryRateLimiter({ storage: new Storage() }, {}, { now: () => clock.now });
  const env = { ALLOWED_EMAIL: OWNER, GOOGLE_CLIENT_ID: CLIENT, PRIVATE_REPO_READ_TOKEN: ['github', 'pat', 'SYNTHETICONLY'].join('_'), PRIVATE_REPO_READ_TOKEN_EXPIRES_ON: 'NEVER',
    HISTORY_RATE_LIMITER: { idFromName: (n) => n, get: () => ({ fetch: (input, init) => limiter.fetch(new Request(input, init)) }) } };
  // The answer the case mutates; the others as published (the member with its exact Content-Length, as the asset host sends it).
  const pick = (name, bytes, extra, ok) => (m.target === name ? answer(bytes, m, extra, ok) : answer(bytes, { cl: name === 'signed' ? 'exact' : 'none' }, extra, ok));
  const fetch = async (url) => {
    if (url === URLS.tokeninfo) return pick('tokeninfo', tokeninfo);
    if (url === URLS.root) return pick('root', root);
    if (url === URLS.shard) return pick('shard', shard);
    if (url.startsWith(API + '/releases/assets/')) return new Response(null, { status: 302, headers: { Location: SIGNED } });
    if (url === SIGNED) return pick('signed', member, { 'Content-Range': m.range ?? 'bytes ' + offset + '-' + (offset + member.length - 1) + '/' + packBytes }, 206);
    throw new Error('unexpected upstream in test');
  };
  const handler = mod.createHandler({ fetch, now: () => clock.now });
  return handler(new Request('https://private-worker.example/kis/stock?symbol=' + SYM, { headers: { Origin: ORIGIN, Authorization: 'Bearer synthetic-access-token' } }), env);
}
async function snapshot(r) { return { status: r.status, headers: [...r.headers].sort().map((x) => x.join(': ')), body: sha(Buffer.from(await r.arrayBuffer())) }; }

const cases = [{}];
for (const target of ['shard', 'signed']) {
  for (const cl of ['none', 'exact', '+1', '-1', 'big', 'lead0']) for (const body of ['exact', '+1', '-1', 'flip', 'empty']) cases.push({ target, cl, body });
  for (const chunk of [1, 7, 4096, 65536, 1 << 20]) cases.push({ target, chunk }, { target, chunk, cl: 'exact' });
  for (const breakAt of [0, 1, 5000, 16384]) cases.push({ target, breakAt }, { target, breakAt, cl: 'exact' });
  for (const status of [200, 206, 301, 401, 403, 404, 429, 500, 503]) cases.push({ target, status }, { target, status, cl: 'exact' });
  cases.push({ target, nobody: true }, { target, nobody: true, cl: 'exact' });
}
for (const target of ['shard', 'signed']) for (const encoding of ['gzip', 'br', 'identity', '']) for (const body of ['exact', '+1', 'x10']) cases.push({ target, cl: 'exact', encoding, body });
cases.push({ target: 'signed', range: 'bytes 0-1/2', cl: 'exact' }, { target: 'root', cl: 'exact' }, { target: 'root', chunk: 1 });

test('native pinned read: the shard and member answers equal the capped chunk loop for every mutated upstream answer', async () => {
  for (const m of cases) assert.deepEqual(await snapshot(await run(NATIVE, m)), await snapshot(await run(LOOP, m)), JSON.stringify(m));
  const ok = await run(NATIVE, {});
  assert.equal(ok.status, 200);
  assert.deepEqual(Buffer.from(await ok.arrayBuffer()), member, 'exactly the pinned member bytes');
  assert.equal(cases.length, 164, 'every mutated case ran');
});

test('native pinned read: the whole-body read is used only when Content-Length is exactly the pin', async () => {
  let wholeBody = 0;
  const original = Response.prototype.arrayBuffer;
  Response.prototype.arrayBuffer = function arrayBuffer() { wholeBody += 1; return original.call(this); };
  try {
    for (const [m, expected] of [[{}, 1], [{ target: 'shard', cl: 'exact' }, 2], [{ target: 'signed', cl: 'none' }, 0], [{ target: 'signed', cl: 'lead0' }, 0], [{ target: 'signed', cl: '-1' }, 0],
      [{ target: 'signed', cl: 'exact', encoding: 'gzip' }, 0], [{ target: 'shard', cl: 'exact', encoding: 'gzip' }, 1], [{ target: 'signed', cl: 'exact', encoding: '' }, 1]]) {
      wholeBody = 0;
      const r = await run(NATIVE, m), status = r.status, seen = wholeBody; // the handler's own reads, before the answer is read here
      await r.arrayBuffer();
      assert.equal(seen, expected, JSON.stringify(m) + ' status ' + status);
    }
  } finally { Response.prototype.arrayBuffer = original; }
});

test('native pinned read: an encoded answer goes the capped path even with Content-Length equal to the pin, and its oversize decoded body is refused by the cap', async () => {
  let wholeBody = 0;
  const original = Response.prototype.arrayBuffer;
  Response.prototype.arrayBuffer = function arrayBuffer() { wholeBody += 1; return original.call(this); };
  try {
    for (const [target, pin, status, c] of [['signed', member.length, 502, 'KIS_STOCK_PIN'], ['shard', shard.length, 502, 'KIS_STOCK_INDEX_INVALID']]) {
      for (const encoding of ['gzip', 'br', 'deflate']) {
        wholeBody = 0; pulled.bytes = 0;
        const m = { target, cl: 'exact', encoding, body: 'x10', chunk: 4096 };
        const r = await run(NATIVE, m), seenWhole = wholeBody, seenPulled = pulled.bytes;
        assert.equal(r.status, status, JSON.stringify(m));
        assert.equal(JSON.parse(await r.text()).error.code, c, JSON.stringify(m));
        assert.equal(seenWhole, 0, JSON.stringify(m) + ': no whole-body read of an encoded answer');
        // The other answers of the request (root, tokeninfo, and the shard or member as published) add their own bytes;
        // the mutated body stops a few chunks past its pin (the read-ahead of the stream) instead of its ten-fold length.
        const others = target === 'signed' ? root.length + shard.length + tokeninfo.length : root.length + tokeninfo.length;
        assert.ok(seenPulled - others <= pin + 3 * 4096, JSON.stringify(m) + ': read ' + (seenPulled - others) + ' bytes of ' + 10 * pin);
      }
      // Without Content-Encoding the same Content-Length takes the native read; the size pin refuses the ten-fold body after it.
      wholeBody = 0;
      const r = await run(NATIVE, { target, cl: 'exact', body: 'x10' }), seenWhole = wholeBody;
      assert.equal(r.status, status); assert.equal(seenWhole, 1, target + ': the native read when nothing is encoded');
      await r.arrayBuffer();
    }
  } finally { Response.prototype.arrayBuffer = original; }
});
