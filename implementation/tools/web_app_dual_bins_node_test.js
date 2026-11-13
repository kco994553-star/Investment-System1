'use strict';
// 구간 색인 (owner 2026-11-12, Codex #529 9a51b4ae qgv-dual-factor-bins/1 "All-bin routing companion /1"): the routing reader
// (web_app/dual-qgv.js checkBins / checkBinsPart / binsMatchGroup) against Codex's nine pinned synthetic cases
// (dual-bin-synthetic/cases.json: five stored distributions + the N 9 / 10 / 11 / 17 boundaries). Every case: Codex's bytes as delivered,
// every bin's members and saved ranks exactly as Codex lists them, counts sum to N from N 10 and are empty below; then consumer edits
// (test-made) that must refuse: another distribution, a missing / extra / foreign group, a count, rank or members-hash change, a
// member file that is not the distribution's, half a companion. A routed group never becomes an empty or shorter band.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const DQ = require('../src/investment_system/product/web_app/dual-qgv.js');
const F = require('./web_app_dual_fixture.js');
const BD = path.join(F.D, '..', 'dual-bin-synthetic');
const CASES = JSON.parse(fs.readFileSync(path.join(BD, 'cases.json'), 'utf8')).cases;
const sha256 = async (b) => crypto.createHash('sha256').update(b).digest('hex');
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const read = (dir) => Object.fromEntries(fs.readdirSync(dir).filter((f) => f.endsWith('.json')).map((f) => [f, fs.readFileSync(path.join(dir, f))]));
const file = (files, f) => { const bytes = new Uint8Array(files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
const json = (x) => Buffer.from(JSON.stringify(x, null, 2) + '\n');
// The ranking scope of each company per board, from the case's own saved source (Codex's source result or saved board).
function scopesOf(c) {
  const src = path.resolve(BD, c.source), scopes = {};
  const saved = path.join(src, '..', 'saved-board.json'), named = path.join(path.dirname(src), path.basename(src).replace(/-stored$/, '') + '-source.json');
  const boards = JSON.parse(fs.readFileSync(fs.existsSync(saved) ? saved : named, 'utf8'));
  for (const [k, b] of Object.entries(boards)) for (const r of b.rows) (scopes[r.company_id] ||= {})[k] = r.ranking_scope;
  return scopes;
}
// One case end to end; edit(docs, manifest) changes the routing first (test-made) and the bins manifest names the new bytes.
async function run(c, edit) {
  const src = read(path.resolve(BD, c.source)), routing = read(path.resolve(BD, c.output));
  if (edit) {
    const docs = Object.fromEntries(Object.keys(routing).filter((f) => f !== 'bin-manifest.json').map((f) => [f, JSON.parse(routing[f].toString('utf8'))]));
    const m = JSON.parse(routing['bin-manifest.json'].toString('utf8'));
    edit(docs, m);
    for (const k of Object.keys(routing)) delete routing[k];
    for (const [f, x] of Object.entries(docs)) routing[f] = json(x);
    m.files = Object.keys(docs).sort().map((f) => ({ path: f, size: routing[f].length, sha256: sha(routing[f]) }));
    routing['bin-manifest.json'] = json(m);
  }
  const D = await DQ.checkDistributionSynthetic({ manifest: file(src, 'distribution-manifest.json'), index: file(src, 'distribution-index.json') }, sha256, { scopes: scopesOf(c) });
  assert.equal(D.ok, true, c.output + ' ' + JSON.stringify(D));
  const parts = new Map();
  for (const f of Object.keys(D.value.entries).filter((x) => x !== 'distribution-index.json')) parts.set(f, (await DQ.checkDistributionPart(file(src, f), f, D.value, sha256)).value);
  const B = await DQ.checkBins({ manifest: file(routing, 'bin-manifest.json'), index: file(routing, 'bin-index.json') }, D.value, sha256);
  if (!B.ok) return { code: B.code, step: 'bins' };
  const recs = new Map();
  for (const f of Object.keys(B.value.entries).filter((x) => x !== 'bin-index.json')) {
    const r = await DQ.checkBinsPart(file(routing, f), f, B.value, sha256); if (!r.ok) return { code: r.code, step: 'part' };
    for (const [k, v] of r.value) recs.set(k, v);
  }
  const groups = [];
  for (const g of D.value.groups) {
    const G = DQ.distributionGroup(D.value, g.group_id, parts).value, m = await DQ.binsMatchGroup(recs.get(g.group_id), G, sha256);
    if (!m.ok) return { code: m.code, step: 'match' };
    groups.push({ g, G, rec: recs.get(g.group_id) });
  }
  return { ok: true, D: D.value, groups, routing };
}

test('Codex\'s nine routing cases: pinned bytes; every bin\'s members and saved ranks as Codex lists them; counts sum to N from N 10', async () => {
  assert.equal(CASES.length, 9);
  for (const c of CASES) {
    const routing = read(path.resolve(BD, c.output));
    assert.equal(sha(routing['bin-manifest.json']), c.manifest_sha256, c.output + ': unedited Codex bytes');
    assert.equal(sha(read(path.resolve(BD, c.source))['distribution-manifest.json']), c.source_manifest_sha256, c.output + ': its pinned distribution');
    const r = await run(c); assert.equal(r.ok, true, c.output + ' ' + JSON.stringify(r));
    for (const want of c.expected_groups) {
      const x = r.groups.find((y) => y.g.group_id === want.group_id); assert.ok(x, want.group_id);
      for (const b of want.bins) {
        const v = DQ.distributionView(r.D, x.G, { band: b.decile, page: 0 });
        const rows = x.G.rows.filter((y) => y.decile === b.decile).sort((p, q) => p.rank - q.rank);
        assert.deepEqual(rows.map((y) => y.company_id), b.members, c.output + ' D' + b.decile + ' members');
        assert.deepEqual(rows.map((y) => y.rank), b.ranks, c.output + ' D' + b.decile + ' saved ranks');
        assert.equal(v.rows.length, Math.min(b.members.length, DQ.DIST_PAGE), 'the page shows the band\'s members');
      }
      const n = x.g.evaluation_valid_n, sum = x.rec.bins.reduce((a, b) => a + b.count, 0);
      assert.equal(sum, n >= 10 ? n : 0, c.output + ': ten bins sum to N from N 10, none below');
      assert.equal(x.rec.partition_status, n >= 10 ? 'COMPLETE' : n ? 'SAMPLE_LT_10' : 'NO_VALID_SCORE');
    }
  }
});

test('boundaries: N 9 has no bins; N 10 one each; N 11 1,2,1,…; N 17 1,2,2,2,2,2,2,2,1,1 (Codex\'s stated counts)', async () => {
  const counts = async (id) => (await run(CASES.find((c) => c.output === id + '/routing'))).groups[0].rec.bins.map((b) => b.count);
  assert.deepEqual(await counts('boundary-9'), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
  assert.deepEqual(await counts('boundary-10'), [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]);
  assert.deepEqual(await counts('boundary-11'), [1, 2, 1, 1, 1, 1, 1, 1, 1, 1]);
  assert.deepEqual(await counts('boundary-17'), [1, 2, 2, 2, 2, 2, 2, 2, 1, 1]);
});

test('refused: another distribution, routes, counts, ranks, members hash, member files, a foreign group; never an empty band', async () => {
  const c = CASES.find((x) => x.output === 'all_ten-stored'), part = (d) => d['bins-000.json'].groups[0];
  const code = async (edit) => (await run(c, edit)).code;
  assert.equal(await code((d, m) => { m.source_manifest_sha256 = 'a'.repeat(64); }), 'BINS_SOURCE_MISMATCH', 'routing of another distribution');
  assert.equal(await code((d) => { d['bin-index.json'].source_index.sha256 = 'b'.repeat(64); }), 'BINS_SOURCE_MISMATCH');
  assert.equal(await code((d) => { d['bin-index.json'].boards.U1.result_hash = 'c'.repeat(64); }), 'BINS_SOURCE_MISMATCH', 'another result');
  assert.equal(await code((d) => { d['bin-index.json'].groups = []; }), 'ROUTES_INVALID', 'a group without a route');
  assert.equal(await code((d) => { d['bin-index.json'].groups.push({ group_id: 'U1|COMMON|other', path: 'bins-000.json' }); }), 'ROUTES_INVALID', 'a foreign group');
  assert.equal(await code((d) => { d['bin-index.json'].filter_changes_population = true; }), 'NOT_PROJECTION');
  assert.equal(await code((d) => { d['bin-index.json'].tie_policy = 'SPLIT'; }), 'RULE_MISMATCH');
  assert.equal(await code((d) => { part(d).bins[0].count = 3; }), 'BIN_COUNT');
  assert.equal(await code((d) => { part(d).bins[0].first_rank = 2; }), 'BIN_MEMBERS', 'ranks that are not the saved ones');
  assert.equal(await code((d) => { part(d).bins[0].members_hash = 'd'.repeat(64); }), 'BIN_MEMBERS', 'another member list');
  assert.equal(await code((d) => { part(d).bins[0].member_files[0].sha256 = 'e'.repeat(64); }), 'BIN_FILES', 'a member file that is not the distribution\'s');
  assert.equal(await code((d) => { part(d).bins[0].member_files = []; }), 'BIN_FILES', 'members without a file');
  assert.equal(await code((d) => { part(d).binned_evaluation_n = 19; }), 'BIN_PARTITION');
  assert.equal(await code((d) => { part(d).evaluation_valid_n = 21; }), 'GROUP_CONTEXT', 'a group record that is not the distribution\'s');
  assert.equal(await code((d) => { d['bins-000.json'].groups = []; }), 'GROUPS_MISMATCH', 'a routed group missing from its file');
  assert.equal(await code((d) => { d['bins-001.json'] = { schema_version: 'qgv-dual-factor-bins-part/1', groups: [] }; }), 'PART_UNREFERENCED');
  // Not checked against a distribution the reader checked.
  const r = read(path.resolve(BD, c.output));
  assert.equal((await DQ.checkBins({ manifest: file(r, 'bin-manifest.json'), index: file(r, 'bin-index.json') }, {}, sha256)).code, 'DISTRIBUTION_NOT_CHECKED');
});

// Codex #437 6848164775 counterexample (raw 77f9d153 handoffs/main-final-acceptance-20261113/bin-file-boundaries.js), ported: the
// stored rows of all_ten-stored split over two part files (ranks 1–10 / 11–20, nothing rescored); a bin must name exactly the
// distinct part files that hold its rows — another file, or the same file twice, is refused.
test('a bin\'s member_files are exactly the distinct part files holding its rows (two-file group: wrong file, duplicate refused)', async () => {
  const bytes = (x) => Buffer.from(JSON.stringify(x, null, 2) + '\n');
  const descriptor = (files, n) => ({ path: n, size: files[n].length, sha256: sha(files[n]) });
  const c = F.distCase('all_ten-stored', (docs) => {
    const p = docs['distribution-000.json'].parts[0]; p.rows.sort((a, b) => a.rank - b.rank);
    docs['distribution-001.json'] = { schema_version: 'qgv-dual-factor-distribution-part/1', parts: [{ group_id: p.group_id, rows: p.rows.splice(10) }] };
    docs['distribution-index.json'].groups[0].files.push('distribution-001.json');
  });
  const dist = (await DQ.checkDistributionSynthetic({ manifest: file(c.files, 'distribution-manifest.json'), index: file(c.files, 'distribution-index.json') }, sha256, { scopes: c.scopes })).value;
  const parts = new Map(); for (const n of ['distribution-000.json', 'distribution-001.json']) parts.set(n, (await DQ.checkDistributionPart(file(c.files, n), n, dist, sha256)).value);
  const g = dist.groups[0], G = DQ.distributionGroup(dist, g.group_id, parts).value;
  const dir = path.join(BD, 'all_ten-stored'), original = read(dir);
  async function check(mode) {
    const docs = Object.fromEntries(Object.entries(original).map(([n, b]) => [n, JSON.parse(b.toString('utf8'))])), bi = docs['bin-index.json'], r = docs['bins-000.json'].groups[0];
    bi.source_distribution_manifest = descriptor(c.files, 'distribution-manifest.json'); bi.source_index = descriptor(c.files, 'distribution-index.json'); r.files = g.files;
    for (const b of r.bins) b.member_files = b.count ? [descriptor(c.files, b.first_rank <= 10 ? 'distribution-000.json' : 'distribution-001.json')] : [];
    if (mode === 'wrong_file') r.bins[0].member_files = [descriptor(c.files, 'distribution-001.json')];
    if (mode === 'duplicate') r.bins[0].member_files.push({ ...r.bins[0].member_files[0] });
    if (mode === 'extra_file') r.bins[0].member_files.push(descriptor(c.files, 'distribution-001.json'));
    const files = Object.fromEntries(Object.entries(docs).filter(([n]) => n !== 'bin-manifest.json').map(([n, d]) => [n, bytes(d)]));
    const m = docs['bin-manifest.json']; m.source_manifest_sha256 = sha(c.files['distribution-manifest.json']); m.files = Object.keys(files).sort().map((n) => descriptor(files, n)); files['bin-manifest.json'] = bytes(m);
    const B = await DQ.checkBins({ manifest: file(files, 'bin-manifest.json'), index: file(files, 'bin-index.json') }, dist, sha256); if (!B.ok) return B;
    const P = await DQ.checkBinsPart(file(files, 'bins-000.json'), 'bins-000.json', B.value, sha256); if (!P.ok) return P;
    return DQ.binsMatchGroup(P.value.get(g.group_id), G, sha256);
  }
  assert.equal((await check('normal')).ok, true, 'the two-file group with each bin naming its own file');
  for (const mode of ['wrong_file', 'duplicate', 'extra_file']) { const r = await check(mode); assert.equal(r.ok, false, mode); assert.equal(r.code, 'BIN_FILES', mode); }
});
