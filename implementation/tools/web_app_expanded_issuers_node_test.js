'use strict';
// 확장 발행사 찾기 reader (web_app/expanded-issuers.js) against Codex #524 fb80b67b's public synthetic delivery
// (tests/fixtures/held_issuer_shards: 2 issuers, 2 shards, coverage, manifest, source-summary). Synthetic only.
//  - The delivery is accepted only when anchored to the summary of the same bundle: SHA-256 of the summary's bytes and its held scope
//    (date, population, scoring population, versions, classification, result identity).
//  - Every file byte for byte against the manifest; identity and identity_hash (Codex digest) the same everywhere; index rows unique,
//    each in its sha256(issuer_id)[:2] shard with the manifest's descriptor; count = issuer_count = population denominator.
//  - A detail shard is checked against its index row (bytes, shard, identity, membership, context_hash, index fields); a refused detail
//    is that detail only.
//  - Words: Q 0 is a value, null is 미산출; the gate input connection is not the actual gate; no total, no rank; the score population
//    (3) differs from the issuer population (2); tickers are catalog observations.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const E = require('../src/investment_system/product/web_app/expanded-issuers.js');

const D = path.join(__dirname, '..', 'tests', 'fixtures', 'held_issuer_shards');
const raw = (n) => new Uint8Array(fs.readFileSync(path.join(D, n)));
const part = (bytes) => ({ bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) });
const enc = (v) => new TextEncoder().encode(E.canonical(v) + '\n');
const clone = (v) => JSON.parse(JSON.stringify(v));
const SUMMARY = raw('source-summary.json');
const HELD = part(SUMMARY).body.calculation_counts.scopes.held_financial_subsample;
async function anchor(over = {}) { return { summarySha: await E.sha256(SUMMARY), held: HELD, ...over }; }
const files = () => ({ manifest: part(raw('manifest.json')), index: part(raw('expanded-index.json')), coverage: part(raw('coverage.json')),
  '55': part(raw('expanded-detail/55.json')), df: part(raw('expanded-detail/df.json')) });
async function sha(bytes) { return E.sha256(bytes); }
const desc = async (p, bytes) => ({ bytes: bytes.byteLength, path: p, sha256: await sha(bytes) });
// Rebuild a consistent delivery after a change (new bytes for the changed files, their descriptors in the index and the manifest).
async function rebuild(f, { index, shards = {}, coverage, keepDetails = false } = {}) {
  const out = { ...f }, m = clone(f.manifest.body);
  for (const [k, v] of Object.entries(shards)) { const b = enc(v); out[k] = { bytes: b, body: v }; }
  const ix = clone(index || f.index.body);
  if (!keepDetails) for (const r of ix.rows) { const key = 'expanded-detail/' + r.shard_key + '.json', s = out[r.shard_key]; if (s) r.detail = await desc(key, s.bytes); }
  out.index = { bytes: enc(ix), body: ix };
  if (coverage) out.coverage = { bytes: enc(coverage), body: coverage };
  const byPath = { 'expanded-index.json': out.index, 'coverage.json': out.coverage };
  for (const s of m.shards) if (out[s]) byPath['expanded-detail/' + s + '.json'] = out[s];
  m.files = await Promise.all(m.files.map((x) => byPath[x.path] ? desc(x.path, byPath[x.path].bytes) : x));
  out.manifest = { bytes: enc(m), body: m };
  return out;
}
const bundleOf = async (f, a) => E.checkBundle({ manifest: f.manifest, index: f.index, coverage: f.coverage }, a || await anchor());

test('the Codex synthetic delivery is accepted whole, anchored to its summary; both details read', async () => {
  const f = files(), r = await bundleOf(f);
  assert.equal(r.ok, true, JSON.stringify(r));
  const b = r.value;
  assert.equal(b.rows.length, 2); assert.equal(b.issuer_count, 2); assert.deepEqual([...b.shards], ['55', 'df']); assert.equal(b.data_kind, 'SYNTHETIC');
  for (const row of b.rows) {
    assert.equal(row.shard_key, (await sha(new TextEncoder().encode(row.issuer_id))).slice(0, 2));
    const d = await E.checkDetail(row, f[row.shard_key], b);
    assert.equal(d.ok, true, row.issuer_id + ' ' + JSON.stringify(d));
    assert.equal(d.value.issuer_id, row.issuer_id);
  }
  assert.equal(b.identity_hash, await E.digest(b.identity), 'identity_hash = Codex digest of identity');
});

test('words: Q 0 is a value, null is 미산출; gate input ≠ actual gate; no total or rank; score population ≠ issuer population', async () => {
  const f = files(), b = (await bundleOf(f)).value, A = b.byId.get('A'), B = b.byId.get('B');
  const a = E.detailView((await E.checkDetail(A, f[A.shard_key], b)).value, b), x = E.detailView((await E.checkDetail(B, f[B.shard_key], b)).value, b);
  assert.equal(a.axes, 'Q 0 · G 50 · V 미산출');
  assert.equal(x.axes, 'Q 미산출 · G 20 · V 미산출');
  assert.deepEqual(a.tickers, ['SYN_A', 'SYN_A.B']); assert.deepEqual(a.codeRows, ['ROW:A', 'ROW:A.B']);
  assert.match(a.gate, /^공식 Q 관문 입력 연결 · 관문 통과·새 Q 점수 아님 · 기존 Universe504 공식 Q 재생값 · 연결됨$/);
  assert.match(x.gate, /연결 안 됨 · 사유 MISSING_INPUT$/);
  assert.match(a.status, /실제 관문 UNKNOWN/); assert.match(a.status, /총점 없음 · 0으로 채우지 않음/);
  assert.match(a.rank, /^순위 없음 · 비교집단 = 보관 카탈로그 점수 모집단\(전체시장 아님\)$/);
  assert.equal(a.peer, '점수의 비교집단 expanded 3개 · 발행사 모집단 2개와 다름');
  assert.match(x.sector, /^미확인 · 사유 SYNTHETIC_MISSING$/);
  assert.match(a.prices, /^가격·기술 연결 안 됨/); assert.equal(a.profile, E.W.PROFILE);
  const op = a.factors.find((y) => y.id === 'operating_margin_ttm'); assert.equal(op.score, '0'); assert.equal(op.raw, '값 0 (유효)');
  assert.equal(x.factors.find((y) => y.id === 'operating_margin_ttm').score, '미산출 · 비교 표본 부족');
  const cov = E.coverageView(b.coverage), held = cov.find((c) => c.scope === 'held_financial_subsample');
  assert.equal(held.target, '95% 목표 · QGV+최종 총점 · 필요 2/2 · 현재 0 · 목표 미달');
  assert.ok(held.causes.some((c) => /^가격 미측정/.test(c)), 'a cause not measured stays 미측정, never 0');
  assert.equal(E.marketText(b.coverage), '전체시장 분모·커버리지 미측정');
});

test('search: ids, observed tickers and names; exact and prefix first; nothing for an empty query', async () => {
  const b = (await bundleOf(files())).value;
  assert.deepEqual(E.search(b.rows, 'syn_a').map((r) => r.issuer_id), ['A']);
  assert.deepEqual(E.search(b.rows, 'SYN').map((r) => r.issuer_id), ['A', 'B']);
  assert.deepEqual(E.search(b.rows, 'ISSUER:B').map((r) => r.issuer_id), ['B']);
  assert.deepEqual(E.search(b.rows, '  '), []); assert.deepEqual(E.search(b.rows, 'ZZZ'), []);
});

test('anchor: no summary bytes, another summary, or another held scope refuses the delivery', async () => {
  const f = files();
  assert.equal((await bundleOf(f, await anchor({ summarySha: null }))).code, 'SUMMARY_UNAVAILABLE');
  assert.equal((await bundleOf(f, await anchor({ held: null }))).code, 'SUMMARY_UNAVAILABLE');
  assert.equal((await bundleOf(f, await anchor({ summarySha: 'b'.repeat(64) }))).code, 'SUMMARY_MISMATCH');
  for (const k of ['valuation_date', 'population', 'scoring_population', 'versions', 'classification', 'result_identity']) {
    const held = clone(HELD);
    if (k === 'valuation_date') held[k] = '2026-11-05'; else held[k] = { ...held[k], changed: true };
    const r = await bundleOf(f, await anchor({ held }));
    assert.equal(r.code, 'SUMMARY_MISMATCH', k); assert.match(r.path, new RegExp(k));
  }
});

test('bundle refusals: bytes, identity, file set, rows, shards and denominator', async () => {
  const f = files(), A = (r) => r.code;
  // bytes changed without the manifest knowing
  const t = { ...f, index: { bytes: new Uint8Array([...f.index.bytes, 32]), body: f.index.body } };
  assert.equal(A(await bundleOf(t)), 'DELIVERY_SIZE_MISMATCH');
  const t2 = { ...f, coverage: { bytes: new Uint8Array(f.coverage.bytes).map((x, i) => i === 10 ? x ^ 1 : x), body: f.coverage.body } };
  assert.equal(A(await bundleOf(t2)), 'DELIVERY_HASH_MISMATCH');
  // identity_hash
  const m = clone(f.manifest.body); m.identity_hash = 'c'.repeat(64);
  assert.equal(A(await bundleOf({ ...f, manifest: { bytes: enc(m), body: m } })), 'IDENTITY_HASH_MISMATCH');
  // file set / routes / limit / kind
  for (const [change, code] of [[(x) => x.files.push({ path: 'extra.json', bytes: 1, sha256: 'a'.repeat(64) }), 'FILE_SET_MISMATCH'],
    [(x) => { x.routes.shard_pattern = '.*'; }, 'ROUTES_MISMATCH'], [(x) => { x.max_file_bytes = 4 * 1024 * 1024; }, 'DELIVERY_SIZE_MISMATCH'],
    [(x) => { x.data_kind = 'REAL'; }, 'DATA_KIND'], [(x) => { x.shards.push('55'); }, 'SHARD_KEY_INVALID'], [(x) => { x.issuer_count = 3; }, 'DENOMINATOR_MISMATCH']]) {
    const y = clone(f.manifest.body); change(y);
    assert.equal(A(await bundleOf({ ...f, manifest: { bytes: enc(y), body: y } })), code, code);
  }
  // index rows (rebuilt so the bytes agree): duplicate issuer, wrong shard, a row's detail not the manifest's, a missing row
  const ix = clone(f.index.body); ix.rows.push(clone(ix.rows[0]));
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix }))), 'INDEX_MEMBER_MISMATCH');
  const ix2 = clone(f.index.body); ix2.rows[0].detail = { ...ix2.rows[0].detail, sha256: 'e'.repeat(64) };
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix2, keepDetails: true }))), 'DETAIL_REF_MISMATCH');
  const ix2b = clone(f.index.body); ix2b.rows[0].shard_key = 'df';
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix2b }))), 'SHARD_MEMBERSHIP_MISMATCH', 'a row filed under another shard');
  const ix3 = clone(f.index.body); ix3.rows[1].shard_key = '55';
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix3 }))), 'SHARD_MEMBERSHIP_MISMATCH');
  const ix4 = clone(f.index.body); ix4.rows.pop();
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix4 }))), 'DENOMINATOR_MISMATCH');
  const ix5 = clone(f.index.body); ix5.identity = { ...ix5.identity, valuation_date: '2026-11-05' };
  assert.equal(A(await bundleOf(await rebuild(f, { index: ix5 }))), 'IDENTITY_MISMATCH');
  const cv = clone(f.coverage.body); cv.schema_version = 'retained-default-coverage/2';
  assert.equal(A(await bundleOf(await rebuild(f, { coverage: cv }))), 'SCHEMA');
});

test('detail refusals are that detail only: bytes, shard, identity, membership, context, index fields', async () => {
  const f = files(), b = (await bundleOf(f)).value, A = b.byId.get('A');
  const changed = new Uint8Array(f['55'].bytes).map((x, i) => i === 20 ? x ^ 1 : x);
  assert.equal((await E.checkDetail(A, { bytes: changed, body: f['55'].body }, b)).code, 'DELIVERY_HASH_MISMATCH');
  assert.equal((await E.checkDetail(A, f.df, b)).code, 'DELIVERY_SIZE_MISMATCH', 'another shard is not this row\'s file');
  const cases = [
    [(s) => { s.shard_key = 'df'; }, 'SHARD_SCHEMA'],
    [(s) => { s.identity_hash = 'c'.repeat(64); }, 'IDENTITY_MISMATCH'],
    [(s) => { s.issuers = []; }, 'DETAIL_MISSING'],
    [(s) => { s.issuers.push(clone(s.issuers[0])); }, 'SHARD_MEMBERSHIP_MISMATCH'],
    [(s) => { s.issuers[0].context = { ...s.issuers[0].context, input_as_of: '2026-11-05T02:00:00Z' }; }, 'DETAIL_CONTEXT_MISMATCH'],
    [(s) => { s.issuers[0].context_hash = 'd'.repeat(64); }, 'DETAIL_CONTEXT_MISMATCH'],
    [(s) => { s.issuers[0].calculation.status = 'COMPLETE'; }, 'INDEX_DETAIL_MISMATCH'],
    [(s) => { s.issuers[0].catalog_observations.pop(); }, 'INDEX_DETAIL_MISMATCH'],
    [(s) => { s.issuers[0].classification.sector.status = 'UNKNOWN'; }, 'INDEX_DETAIL_MISMATCH'],
  ];
  for (const [change, code] of cases) {
    const s = clone(f['55'].body); change(s);
    const g = await rebuild(f, { shards: { '55': s } }), gb = (await bundleOf(g)).value;
    assert.ok(gb, code + ': the rebuilt bundle itself is accepted');
    const r = await E.checkDetail(gb.byId.get('A'), g['55'], gb);
    assert.equal(r.code, code, code + ' ' + JSON.stringify(r));
    assert.equal((await E.checkDetail(gb.byId.get('B'), g.df, gb)).ok, true, code + ': the other issuer still reads');
  }
  assert.equal((await E.checkDetail({ ...A }, f['55'], b)).code, 'ROW_UNKNOWN', 'only a row of this checked bundle');
});
