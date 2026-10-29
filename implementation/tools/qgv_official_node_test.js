'use strict';
// qgv-official/1 reader (web_assets/qgv-official.js, PR-D, owner decision D8 (b)): every Python verdict of
// tests/fixtures/qgv_official_vectors_v1.json replays identically (validate / parse), the loader cases, the TARGET v1 use rule
// (usable: verified, same calc_version, <= 2 New York sessions), constants equal to the Python and config sources, and no
// storage, console or extra network use. Synthetic publication only (tests/build_qgv_official_vectors.py).
const path = require('node:path');
const WA = path.join(__dirname, '../src/investment_system/product/web_assets');
const before = new Set(Object.keys(require.cache));
const Q = require(path.join(WA, 'qgv-official.js'));
const loadedAtRequire = Object.keys(require.cache).filter((k) => !before.has(k)).map((k) => path.basename(k));
const assert = require('node:assert/strict'), fs = require('node:fs'), crypto = require('node:crypto');
const V2 = require(path.join(WA, 'qgv-v2.js')), TC = require(path.join(WA, 'type-config-defaults.js')), DCF = require(path.join(WA, 'dcf-parameters-defaults.js'));
const FV = require(path.join(WA, 'forward-validation.js')), W = require(path.join(__dirname, '../src/investment_system/product/web_app/qgv.js'));
const SRC = fs.readFileSync(path.join(WA, 'qgv-official.js'), 'utf8');
const FIXTURE = fs.readFileSync(path.join(__dirname, '../tests/fixtures/qgv_official_vectors_v1.json'), 'utf8');
const V = JSON.parse(FIXTURE), K = V.constants;
const enc = (s) => new TextEncoder().encode(s), hex = (h) => Uint8Array.from(h.match(/../g) || [], (b) => parseInt(b, 16));
const cat = (...parts) => { const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0)); let i = 0; for (const p of parts) { out.set(p, i); i += p.length; } return out; };
const base = () => JSON.parse(V.base_text);
function apply(p, ops) { for (const op of ops) { let t = p; for (const k of op.path.slice(0, -1)) t = t[k]; const last = op.path[op.path.length - 1]; if (op.delete) delete t[last]; else t[last] = structuredClone(op.value); } return p; }
function body(b) {
  if (b.whole !== undefined) return enc(b.whole);
  let bytes = enc(V.base_text);
  if (b.find !== undefined) { const i = V.base_text.indexOf(b.find); assert.ok(i >= 0, b.id); bytes = cat(bytes.slice(0, i), b.replace_hex !== undefined ? hex(b.replace_hex) : enc(b.replace), bytes.slice(i + b.find.length)); }
  if (b.prefix_hex) bytes = cat(hex(b.prefix_hex), bytes);
  if (b.suffix !== undefined) bytes = cat(bytes, enc(b.suffix));
  if (b.pad_to) bytes = cat(bytes, new Uint8Array(b.pad_to - bytes.length).fill(32));
  return bytes;
}
async function verdict(promise) { try { await promise; return [true, null]; } catch (e) { assert.ok(Q.ERRORS.includes(e.message), 'fixed code only: ' + e.message); return [false, e.message]; } }
function response(status, bytes = enc(V.base_text), headers = {}) {
  return { status, ok: status >= 200 && status < 300, headers: { get: (n) => (Object.hasOwn(headers, n.toLowerCase()) ? headers[n.toLowerCase()] : null) }, arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) };
}
function fetcher(make) { const calls = []; const f = async (url, init) => { calls.push({ url, init }); return make(url, init); }; f.calls = calls; return f; }
let pass = 0, fail = 0;
async function test(name, f) { try { await f(); pass++; console.log('PASS ' + name); } catch (e) { fail++; console.log('FAIL ' + name + ' ' + (e.code === 'ERR_ASSERTION' ? 'CONTRACT' : 'EXECUTION')); if (process.env.DEBUG_TEST) console.log(e); } }

(async () => {
  await test('module: side-effect free at load (dependencies bound lazily), one same-origin no-store fetch, no storage / console / DOM / eval', async () => {
    assert.deepEqual(loadedAtRequire, ['qgv-official.js']);
    for (const token of ['localStorage', 'sessionStorage', 'indexedDB', 'console', 'document', 'window', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'eval(', 'new Function', 'innerHTML', 'setTimeout', 'setInterval', 'importScripts', 'http://', ...['hist', 'monthend'].map((x) => 'iex' + '_' + x)])   // adapter names (built, so tools/ stays clean)
      assert.ok(!SRC.includes(token), token);
    const calls = [...SRC.matchAll(/fetch\(/g)];
    assert.equal(calls.length, 1);
    assert.match(SRC.slice(calls[0].index, calls[0].index + 200), /cache:'no-store'/);
    assert.equal((SRC.match(/https:\/\//g) || []).length, 1, 'only the IEX terms link, compared, never requested');
    assert.ok(Object.isFrozen(Q) && Object.isFrozen(Q.ATTRIBUTION) && Object.isFrozen(Q.V_SOURCES.OFFICIAL_CENTRAL) && Object.isFrozen(Q.TOP_KEYS));
  });

  await test('constants equal the Python validator, the engine and config modules, and web_app V_SOURCES', async () => {
    assert.equal(V.synthetic, true); assert.ok(!FIXTURE.includes('4321.09'), 'canary absent');
    assert.deepEqual([Q.SCHEMA, Q.KIND, Q.FILENAME, Q.MAX_BYTES, Q.TARGET_PREFIX], [K.schema, K.kind, K.filename, K.max_bytes, K.target_prefix]);
    assert.deepEqual([...Q.TOP_KEYS], K.top_keys); assert.deepEqual([...Q.ROW_KEYS], K.row_keys); assert.deepEqual([...Q.FACTOR_KEYS], K.factor_keys); assert.deepEqual([...Q.AXIS_KEYS], K.axis_keys);
    assert.deepEqual([...Q.FORBIDDEN_KEYS], K.forbidden_keys); assert.deepEqual([...Q.PRICE_DEPENDENT], K.price_dependent); assert.equal(Q.PRICE_DEPENDENT_PUBLIC, K.price_dependent_public);
    assert.deepEqual([...Q.STATUS_CODES], K.status_codes); assert.equal(K.supplied, 'SUPPLIED'); assert.deepEqual({ ...Q.TARGET_TICKERS }, K.target_tickers);
    assert.deepEqual({ ...Q.ATTRIBUTION }, K.attribution); assert.deepEqual({ ...Q.PRICE_SOURCE }, K.price_source); assert.deepEqual({ ...Q.MONTH_END }, K.month_end);
    assert.deepEqual([Q.MAX_MONTHS, Q.SUPPLY_MIN, Q.V_TARGET_SHARE, Q.POPULATION_VERSION, Q.INPUTS_FILE], [K.max_months, K.supply_min, K.v_target_share, K.population_version, K.inputs_file]);
    assert.deepEqual([...Q.SHARE_BASIS_SINCE], K.share_basis_since); assert.equal(K.calc_version_pattern, 'qgv2-calc/[0-9]{4}-[0-9]{2}-[0-9]{2}\\.[0-9]{1,4}');
    assert.deepEqual(K.weights, { default_preset: V2.DEFAULT_PRESET, gate: true, type_weights: true, profile_id: V2.VERSION + '/' + V2.DEFAULT_PRESET + '/gate-on', weights_version: V2.weightsId(V2.officialWeights(V2.DEFAULT_PRESET), true) });
    assert.deepEqual(K.config_versions, { type_config: TC.config_version, dcf_parameters: DCF.config_version });
    assert.deepEqual([K.type_scope, K.engine.version, K.engine.status, K.min_axis_weight], [V2.TYPE_SCOPE, V2.VERSION, V2.STATUS, V2.MIN_AXIS_WEIGHT]);
    assert.deepEqual([...V2.FACTORS], K.factors); assert.deepEqual([...V2.PILLARS], K.pillars); assert.deepEqual(Object.keys(V2.WEIGHTS.V), K.v_factors);
    assert.deepEqual(JSON.parse(JSON.stringify(Q.V_SOURCES)), JSON.parse(JSON.stringify(W.V_SOURCES)));
    assert.equal(Q.FRESH_SESSIONS, 2); assert.deepEqual([...Q.REASONS], ['OFFICIAL_NOT_PUBLISHED', 'OFFICIAL_UNAVAILABLE', 'OFFICIAL_INVALID', 'OFFICIAL_CALC_VERSION_DIFFERS', 'OFFICIAL_STALE']);
  });

  await test('Python require_qgv_official verdicts replay identically (' + V.cases.length + ' vectors; js_stricter ones are refused)', async () => {
    assert.ok(V.cases.length >= 120);
    let stricter = 0;
    for (const c of V.cases) {
      const got = await verdict(Q.validate(apply(base(), c.ops), c.max_bytes === undefined ? {} : { maxBytes: c.max_bytes }));
      if (c.js_stricter) { stricter++; assert.equal(c.valid, true, c.id); assert.deepEqual(got, [false, c.js_stricter], c.id); }
      else assert.deepEqual(got, [c.valid, c.code], c.id);
    }
    assert.equal(stricter, 1);
    assert.deepEqual(V.cases.filter((c) => c.code === 'OFFICIAL_TOO_LARGE').map((c) => c.id), ['size_cap_below_estimate']);
  });

  await test('Python parse verdicts on bytes replay identically (' + V.bodies.length + ' bodies: BOM, UTF-8, duplicate keys, NaN, caps)', async () => {
    let divergent = 0;
    for (const b of V.bodies) {
      const got = await verdict(Q.parse(body(b), b.max_bytes === undefined ? {} : { maxBytes: b.max_bytes }));
      if (b.divergence) { divergent++; assert.equal(b.divergence, 'INT_FLOAT_SPELLING'); assert.equal(b.valid, false); assert.deepEqual(got, [true, null], b.id + ' (documented: the Pages guard refuses it)'); }
      else assert.deepEqual(got, [b.valid, b.code], b.id);
    }
    assert.equal(divergent, 1);
  });

  await test('pooled digest (Web Crypto SHA-256), canonical length emulation, duplicate-key scan', async () => {
    for (const d of V.digest_cases) assert.equal(await Q.pooledDigest(Object.fromEntries(d.keys.map((k) => [k, { in_cross_section: true }]))), d.sha256);
    assert.equal(await Q.pooledDigest({ 'NYSE:A': { in_cross_section: true }, 'NYSE:B': { in_cross_section: false } }), crypto.createHash('sha256').update('NYSE:A').digest('hex'));
    for (const c of V.canonical_length_cases) assert.equal(Q.canonicalLength(c.value), c.length, JSON.stringify(c.value));
    assert.equal(Q.canonicalLength(base()), V.base_estimate_length); assert.ok(V.base_estimate_length <= V.base_canonical_length && V.base_canonical_length === V.base_text.length);
    assert.equal(Q.duplicateKeys('{"a":{"b":1,"c":[{"b":2}]},"b":"a"}'), false);
    assert.equal(Q.duplicateKeys('{"a":1,"x":{"a":1},"a":2}'), true);
    assert.equal(Q.duplicateKeys('{"a\\"":1,"a\\u0022":2}'), true);
    assert.equal(Q.duplicateKeys('["a","a",{"k":"a","v":"k"}]'), false);
  });

  await test('loader: 404 = NOT_PUBLISHED, other status / network / redirect = UNAVAILABLE, BOM / bad UTF-8 / oversize = INVALID', async () => {
    const ok = fetcher(() => response(200));
    const got = await Q.load(ok);
    assert.equal(got.state, 'OFFICIAL'); assert.equal(Q.state(got.payload), 'OFFICIAL'); assert.ok(Object.isFrozen(got.payload.rows[Object.keys(got.payload.rows)[0]].factors));
    assert.equal(ok.calls.length, 1); assert.equal(ok.calls[0].url, 'qgv-official.json');
    assert.deepEqual({ ...ok.calls[0].init, signal: undefined, headers: undefined }, { cache: 'no-store', credentials: 'omit', redirect: 'error', referrerPolicy: 'no-referrer', signal: undefined, headers: undefined });
    const view = { calls: 0, fetch(url, init) { this.calls++; assert.equal(init.cache, 'no-store'); return Promise.resolve(response(404)); } };
    assert.deepEqual(await Q.load(view), { state: 'NOT_PUBLISHED', payload: null }); assert.equal(view.calls, 1);
    for (const status of [500, 503, 403, 304, 0]) await assert.rejects(Q.load(fetcher(() => response(status))), /^Error: OFFICIAL_UNAVAILABLE$/);
    await assert.rejects(Q.load(fetcher(() => { throw new TypeError('Failed to fetch (redirect)'); })), /OFFICIAL_UNAVAILABLE/);
    await assert.rejects(Q.load(fetcher(() => null)), /OFFICIAL_UNAVAILABLE/);
    await assert.rejects(Q.load(null), /OFFICIAL_UNAVAILABLE/);
    await assert.rejects(Q.load(fetcher(() => ({ ...response(200), arrayBuffer: async () => { throw new Error('aborted'); } }))), /OFFICIAL_UNAVAILABLE/);
    await assert.rejects(Q.load(fetcher(() => response(200, cat(hex('efbbbf'), enc(V.base_text))))), /OFFICIAL_INVALID/);
    await assert.rejects(Q.load(fetcher(() => response(200, cat(enc('{"a":"'), hex('ff'), enc('"}'))))), /OFFICIAL_INVALID/);
    await assert.rejects(Q.load(fetcher(() => response(200, cat(enc(V.base_text), new Uint8Array(Q.MAX_BYTES).fill(32))))), /OFFICIAL_INVALID/);
    let read = false;
    await assert.rejects(Q.load(fetcher(() => ({ ...response(200, enc('{}'), { 'content-length': String(Q.MAX_BYTES + 1) }), arrayBuffer: async () => { read = true; return new ArrayBuffer(2); } }))), /OFFICIAL_INVALID/);
    assert.equal(read, false, 'a declared oversize body is not read');
    await assert.rejects(Q.load(fetcher(() => response(200, enc('{"rows":{"NYSE:A":{"Price":1}}}')))), /OFFICIAL_INVALID/);   // key set first
  });

  await test('no Web Crypto: fail closed with the JS environment code, reported as OFFICIAL_UNAVAILABLE', async () => {
    const desc = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
    Object.defineProperty(globalThis, 'crypto', { value: undefined, configurable: true, writable: true });
    try {
      let err = null; try { await Q.validate(base()); } catch (e) { err = e; }
      assert.equal(err && err.message, 'OFFICIAL_DIGEST_UNAVAILABLE'); assert.equal(Q.reasonOf(err), 'OFFICIAL_UNAVAILABLE');
      const r = await Q.resolve(fetcher(() => response(200)), { secCalcVersion: 'qgv2-calc/2026-10-23.1', nyToday: '2026-10-14' });
      assert.deepEqual(r, { ok: false, reason: 'OFFICIAL_UNAVAILABLE', sessions: null, payload: null });
      await assert.rejects(Q.validate({ schema: 'x' }), /OFFICIAL_INVALID/, 'a broken file is INVALID before the digest is needed');
    } finally { if (desc) Object.defineProperty(globalThis, 'crypto', desc); else delete globalThis.crypto; }
    assert.equal(typeof globalThis.crypto.subtle.digest, 'function');
  });

  await test('use rule (spec M4): validated + verified_at + same calc_version + price basis <= 2 completed New York sessions', async () => {
    const pub = await Q.validate(base()), calc = pub.calc_version, basis = pub.times.price_basis_date;
    assert.deepEqual([calc, basis], ['qgv2-calc/2026-10-23.1', '2026-10-13']);
    const use = (today, sec = calc) => Q.usable(pub, { secCalcVersion: sec, nyToday: today });
    assert.deepEqual(use('2026-10-13'), { ok: true, reason: null, sessions: 0 });
    assert.deepEqual(use('2026-10-14'), { ok: true, reason: null, sessions: 1 });
    assert.deepEqual(use('2026-10-15'), { ok: true, reason: null, sessions: 2 });
    assert.deepEqual(use('2026-10-16'), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 });
    assert.deepEqual(use('2027-10-16'), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 });
    assert.deepEqual(use('2026-10-12'), { ok: false, reason: 'OFFICIAL_STALE', sessions: null }, 'a basis day in the future is never fresh');
    for (const bad of [null, '', '2026-10-32', '2026-1-14', 20261014]) assert.equal(use(bad).reason, 'OFFICIAL_STALE');
    assert.deepEqual(use('2026-10-14', 'qgv2-calc/2026-10-23.2'), { ok: false, reason: 'OFFICIAL_CALC_VERSION_DIFFERS', sessions: null });
    assert.equal(use('2026-10-14', null).reason, 'OFFICIAL_CALC_VERSION_DIFFERS');
    assert.equal(Q.usable(base(), { secCalcVersion: calc, nyToday: '2026-10-14' }).reason, 'OFFICIAL_INVALID', 'only a payload that passed validate()');
    assert.equal(Q.usable(null).reason, 'OFFICIAL_INVALID'); assert.equal(Q.state(base()), null);
    assert.throws(() => { pub.rows[Object.keys(pub.rows)[0]].total = 0; }, TypeError, 'frozen after validation');
    // the NYSE calendar of ForwardValidation (holidays, weekends); counting stops above the threshold; past its end: not countable
    assert.equal(Q.sessionsAfter('2026-11-25', '2026-11-30'), 2);       // Thanksgiving 11-26, weekend 11-28/29
    assert.equal(Q.sessionsAfter('2026-11-25', '2026-12-01'), 3);
    assert.equal(Q.sessionsAfter('2026-10-16', '2026-10-19'), 1);       // Friday -> Monday
    assert.equal(Q.sessionsAfter('2026-12-24', '2026-12-28'), 1);       // Christmas, weekend
    assert.equal(Q.sessionsAfter('2028-12-29', '2029-01-03'), null);    // beyond ForwardValidation's calendar: fail closed
    assert.equal(Q.sessionsAfter('2026-02-30', '2026-03-02'), null);
    assert.equal(FV.sessionDay('2026-11-26'), false);
    assert.equal(Q.nyToday(Date.parse('2026-11-27T00:37:00Z')), '2026-11-26');   // the daily run's UTC midnight is the NY evening before
    assert.equal(Q.nyToday(Date.parse('2026-10-14T04:30:00Z')), '2026-10-14');
  });

  await test('use rule (spec M4): only COMPLETED sessions count; today\'s from 16:00 New York (nyMinutes), unknown time counts it', async () => {
    const pub = await Q.validate(base()), calc = pub.calc_version;   // basis Tue 2026-10-13
    const use = (today, minutes) => Q.usable(pub, { secCalcVersion: calc, nyToday: today, nyMinutes: minutes });
    assert.equal(Q.CLOSE_MINUTES, 16 * 60);
    // Fri 2026-10-16: during the session only Wed and Thu are completed (2, fresh); from the close Fri is the 3rd (stale).
    assert.deepEqual(use('2026-10-16', 9 * 60 + 35), { ok: true, reason: null, sessions: 2 });
    assert.deepEqual(use('2026-10-16', 15 * 60 + 59), { ok: true, reason: null, sessions: 2 });
    assert.deepEqual(use('2026-10-16', 16 * 60), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 });
    assert.deepEqual(use('2026-10-16', 16 * 60 + 30), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 });
    assert.deepEqual(use('2026-10-15', 20 * 60), { ok: true, reason: null, sessions: 2 });               // Thu after the close
    assert.deepEqual(use('2026-10-17', 10 * 60), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 });  // Saturday: Fri completed
    assert.deepEqual(use('2026-10-13', 0), { ok: true, reason: null, sessions: 0 });
    // A time that is not a minute of the day is unknown → today counts (fail closed), as without nyMinutes.
    for (const bad of [null, undefined, -1, 1440, 575.5, '575', NaN]) assert.deepEqual(use('2026-10-16', bad), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3 }, String(bad));
    assert.equal(use('2026-10-12', 600).reason, 'OFFICIAL_STALE', 'a basis day in the future stays stale');
    assert.equal(Q.sessionsAfter('2026-10-13', '2026-10-16', false), 2); assert.equal(Q.sessionsAfter('2026-10-13', '2026-10-16'), 3);
    assert.equal(Q.sessionsAfter('2026-11-25', '2026-11-30', false), 1);  // Thanksgiving 11-26, Fri 11-27 completed, Mon not yet
    assert.equal(Q.sessionsAfter('2026-10-16', '2026-10-17', false), 0);  // Saturday after a Friday basis
    // nyNow: one clock read, the New York day and minute (EDT / EST).
    assert.deepEqual({ ...Q.nyNow(Date.parse('2026-10-16T13:35:00Z')) }, { date: '2026-10-16', minutes: 9 * 60 + 35 });
    assert.deepEqual({ ...Q.nyNow(Date.parse('2026-11-27T00:37:00Z')) }, { date: '2026-11-26', minutes: 19 * 60 + 37 });
    assert.ok(Object.isFrozen(Q.nyNow()));
    const fresh = await Q.resolve(fetcher(() => response(200)), { secCalcVersion: calc, nyToday: '2026-10-16', nyMinutes: 9 * 60 + 35 });
    assert.deepEqual([fresh.ok, fresh.reason, fresh.sessions, Q.state(fresh.payload)], [true, null, 2, 'OFFICIAL']);
    assert.deepEqual(await Q.resolve(fetcher(() => response(200)), { secCalcVersion: calc, nyToday: '2026-10-16', nyMinutes: 16 * 60 + 30 }), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3, payload: null });
  });

  await test('resolve: one call for the TARGET v1 click, never throws, payload only when usable', async () => {
    const opts = { secCalcVersion: 'qgv2-calc/2026-10-23.1', nyToday: '2026-10-14' };
    const ok = await Q.resolve(fetcher(() => response(200)), opts);
    assert.deepEqual([ok.ok, ok.reason, ok.sessions, Q.state(ok.payload)], [true, null, 1, 'OFFICIAL']);
    assert.deepEqual(await Q.resolve(fetcher(() => response(404)), opts), { ok: false, reason: 'OFFICIAL_NOT_PUBLISHED', sessions: null, payload: null });
    assert.deepEqual(await Q.resolve(fetcher(() => response(500)), opts), { ok: false, reason: 'OFFICIAL_UNAVAILABLE', sessions: null, payload: null });
    assert.deepEqual(await Q.resolve(fetcher(() => response(200, cat(hex('efbbbf'), enc(V.base_text)))), opts), { ok: false, reason: 'OFFICIAL_INVALID', sessions: null, payload: null });
    const forbidden = V.cases.find((c) => c.code === 'OFFICIAL_FORBIDDEN_KEY');
    assert.equal((await Q.resolve(fetcher(() => response(200, enc(JSON.stringify(apply(base(), forbidden.ops))))), opts)).reason, 'OFFICIAL_INVALID');
    const unverified = V.cases.find((c) => c.id === 'verified_at_null');
    assert.equal((await Q.resolve(fetcher(() => response(200, enc(JSON.stringify(apply(base(), unverified.ops))))), opts)).reason, 'OFFICIAL_INVALID');
    assert.deepEqual(await Q.resolve(fetcher(() => response(200)), { ...opts, nyToday: '2026-10-19' }), { ok: false, reason: 'OFFICIAL_STALE', sessions: 3, payload: null });
    assert.deepEqual(await Q.resolve(fetcher(() => response(200)), { ...opts, secCalcVersion: 'qgv2-calc/2026-10-17.1' }), { ok: false, reason: 'OFFICIAL_CALC_VERSION_DIFFERS', sessions: null, payload: null });
    assert.equal(Q.reasonOf(new Error('OFFICIAL_TOO_LARGE')), 'OFFICIAL_INVALID'); assert.equal(Q.reasonOf(new Error('OFFICIAL_FORBIDDEN_KEY')), 'OFFICIAL_INVALID'); assert.equal(Q.reasonOf(null), 'OFFICIAL_INVALID');
  });

  await test('NA never becomes 0: published nulls stay null with their reasons; ranks, rank_row and the TARGET row come through unchanged', async () => {
    const pub = await Q.validate(base()), rows = pub.rows;
    const noV = Object.entries(rows).filter(([, r]) => r.axes.V.score === null);
    assert.ok(noV.length > 5);
    for (const [k, r] of noV) { assert.ok(r.axes.V.reason !== null || r.total_reason !== null, k); assert.notEqual(r.axes.V.score, 0); }
    for (const r of Object.values(rows)) for (const f of Object.values(r.factors)) assert.ok(f.score !== null || f.reason !== null, 'a missing factor carries its reason');
    assert.equal(rows['NYSE:ARE'].axes.V.score, null); assert.equal(rows['NYSE:ARE'].price_status, 'NO_IEX_TRADE'); assert.equal(rows['NYSE:ARE'].rank, null);
    assert.ok(rows['NYSE:ARE'].qg_reference_order >= 1);
    assert.equal(rows['NASDAQ:ALGN'].factors.v_earnings_yield.reason, Q.PRICE_DEPENDENT_PUBLIC);
    assert.equal(rows['NASDAQ:AMD'].rank_row, 'TARGET:amd'); assert.equal(rows['NASDAQ:AMD'].rank, null); assert.ok(rows['TARGET:amd'].rank >= 1); assert.equal(Q.symbol('TARGET:amd'), 'AMD');
    assert.equal(rows['NASDAQ:GOOG'].rank_row, 'NASDAQ:GOOGL');
    assert.deepEqual([Q.symbol('NYSE:BRK.B'), Q.symbol('NYSE:Q.R.S'), Q.symbol('TARGET:stry'), Q.symbol('TARGET:constructor')], ['BRK-B', 'Q-R-S', 'SYK', 'TARGET:constructor']);
    assert.deepEqual(JSON.parse(JSON.stringify(Q.coverage(rows))), JSON.parse(JSON.stringify(pub.coverage)));
  });

  await test('full-size synthetic form (~520 rows, JS-derived) validates and parses well under a click budget', async () => {
    const p = base(), rows = p.rows, empty = Object.keys(rows).find((k) => !k.startsWith('TARGET:') && rows[k].cik === null && rows[k].price_status === 'SUPPLIED');
    for (let i = 0; i < 480; i++) rows['NYSE:Z' + String(i).padStart(3, '0')] = structuredClone(rows[empty]);
    const n = Object.keys(rows).length, universe = Object.keys(rows).filter((k) => !k.startsWith('TARGET:'));
    Object.assign(p.population, { row_count: n, universe_code_count: universe.length });
    p.price_source.supplied = universe.filter((k) => rows[k].price_status === 'SUPPLIED').length;
    p.coverage = JSON.parse(JSON.stringify(Q.coverage(rows)));
    const bytes = enc(JSON.stringify(p));
    assert.ok(bytes.length > 800000 && bytes.length < Q.MAX_BYTES, String(bytes.length));
    const t0 = process.hrtime.bigint(); const got = await Q.parse(bytes); const ms = Number(process.hrtime.bigint() - t0) / 1e6;
    assert.equal(Q.state(got), 'OFFICIAL'); assert.ok(ms < 3000, ms + ' ms');
  });

  await test('no storage or console use at run time (load, validate, usable, resolve)', async () => {
    const touched = [], trap = (name) => new Proxy({}, { get(_, k) { touched.push(name + '.' + String(k)); throw new Error('touched ' + name); } });
    const saved = { log: console.log, warn: console.warn, error: console.error, info: console.info, debug: console.debug };
    for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) Object.defineProperty(globalThis, name, { value: trap(name), configurable: true });
    for (const k of Object.keys(saved)) console[k] = () => { touched.push('console.' + k); };
    try {
      const r = await Q.resolve(fetcher(() => response(200)), { secCalcVersion: 'qgv2-calc/2026-10-23.1', nyToday: '2026-10-15' });
      await Q.resolve(fetcher(() => response(200, enc('{}'))), {}); await Q.resolve(fetcher(() => response(404)), {});
      if (!r.ok) throw new Error('resolve failed');
    } finally { for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) delete globalThis[name]; Object.assign(console, saved); }
    assert.deepEqual(touched, []);
    assert.equal(typeof globalThis.localStorage, 'undefined');
  });

  console.log('COUNTS pass=' + pass + ' fail=' + fail); if (fail) process.exitCode = 1;
})();
