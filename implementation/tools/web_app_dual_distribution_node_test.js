'use strict';
// 요소 10분위 전체 조회 (owner 2026-11-12): the full factor distribution reader (web_app/dual-qgv.js checkDistribution /
// checkDistributionPart / distributionGroup / distributionView) against Codex #529's synthetic cases (dual-distribution-synthetic,
// cases.json pins each manifest; 10 outputs = 5 inputs × 2 explicit display policies) and against a distribution bound to the
// fixture delivery (test-made projection of its stored factor values). Checks: all ten bands with their stored counts and the
// unavailable rows apart; a band's rows in the stored rank order, paged; empty bands confirmed; ties, small samples and missing
// reference kept as the producer gave them; sector groups never merged; nothing re-ranked; the reference-score candidate refused
// on private data; missing / duplicate / foreign rows, wrong bytes, wrong model / result / date / comparison group refused.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const DQ = require('../src/investment_system/product/web_app/dual-qgv.js');
const F = require('./web_app_dual_fixture.js');
const sha256 = async (b) => crypto.createHash('sha256').update(b).digest('hex');
const file = (files, f) => { const bytes = new Uint8Array(files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
const CASES = JSON.parse(fs.readFileSync(path.join(F.D, '..', 'dual-distribution-synthetic', 'cases.json'), 'utf8')).cases;
const parts = (files) => ({ manifest: file(files, 'distribution-manifest.json'), index: file(files, 'distribution-index.json') });
async function load(D, files) { const m = new Map();
  for (const f of Object.keys(D.entries).filter((x) => x !== 'distribution-index.json')) { const r = await DQ.checkDistributionPart(file(files, f), f, D, sha256); assert.equal(r.ok, true, JSON.stringify(r)); m.set(f, r.value); }
  return m; }
async function synthetic(id, edit) { const c = F.distCase(id, edit); return { c, r: await DQ.checkDistributionSynthetic(parts(c.files), sha256, { scopes: c.scopes }) }; }

test('Codex\'s ten synthetic cases: pinned bytes; every group complete; stored counts and unavailable rows as expected', async () => {
  assert.equal(CASES.length, 10);
  for (const k of CASES) {
    const { c, r } = await synthetic(k.case_id);
    assert.equal(F.sha(c.files['distribution-manifest.json']), k.manifest_sha256, k.case_id + ': unedited Codex bytes');
    assert.equal(r.ok, true, k.case_id + ' ' + JSON.stringify(r)); assert.equal(r.value.bound, false, 'a synthetic case is not bound to a delivery');
    assert.equal(r.value.display_policy, k.display_policy);
    const m = await load(r.value, c.files);
    r.value.groups.forEach((g, i) => {
      const G = DQ.distributionGroup(r.value, g.group_id, m); assert.equal(G.ok, true, k.case_id + ' ' + JSON.stringify(G));
      assert.deepEqual(g.bins, k.expected_bins[i], k.case_id + ' bins'); assert.equal(g.unavailable_count, k.expected_unavailable[i], k.case_id + ' unavailable');
      // The query example: bands 10 and 1 are the stored rows themselves (rank, N, context unchanged).
      const v10 = DQ.distributionView(r.value, G.value, { band: 10 }), v1 = DQ.distributionView(r.value, G.value, { band: 1 });
      const want = (d) => G.value.rows.filter((x) => x.decile === d).sort((a, b) => a.rank - b.rank).map((x) => x.company_id);
      assert.deepEqual(v10.rows.map((x) => x.company_id), want(10)); assert.deepEqual(v1.rows.map((x) => x.company_id), want(1));
      for (const x of v10.rows) { const o = G.value.rows.find((y) => y.company_id === x.company_id); assert.equal(x.rank, o.rank === null ? '순위 없음' : o.rank + ' / ' + o.rank_n); }
    });
  }
});

test('ten bands in the producer\'s words; a band shows its rows in stored rank order; empty bands and unavailable rows apart', async () => {
  const { c, r } = await synthetic('all_ten-stored'), m = await load(r.value, c.files), g = r.value.groups[0], G = DQ.distributionGroup(r.value, g.group_id, m).value;
  const v = DQ.distributionView(r.value, G);
  assert.deepEqual(v.bands.map((b) => b.label), ['상위 0–10%', '상위 10–20%', '상위 20–30%', '상위 30–40%', '상위 40–50%', '상위 50–60%', '상위 60–70%', '상위 70–80%', '상위 80–90%', '상위 90–100%']);
  assert.deepEqual(v.bands.map((b) => b.count), [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]); assert.equal(v.selected, null); assert.deepEqual(v.rows, []);
  assert.match(v.context, /^평가 유효 20 \/ 범위 내 20 · 참조 N \d+\(순위 분모 아님\) · 원지표 .+ · 점수는 높을수록 좋음 · 평가일 2026-11-04$/);
  assert.match(v.policy, /^분위 기준: 저장된 평가 순위 분위\(기존 규칙\)/);
  const top = DQ.distributionView(r.value, G, { band: 10 });
  assert.equal(top.selected, '상위 0–10% · 분위 10 · 2개'); assert.deepEqual(top.rows.map((x) => x.rank), ['1 / 20', '2 / 20']); assert.match(top.rows[0].band, /^상위 0–10%\(분위 10\)$/);
  assert.ok(top.bands.find((b) => b.decile === 10).selected && top.bands.filter((b) => b.selected).length === 1);
  // Small evaluation sample: no stored band, every row unavailable with its reason (not an empty result).
  const s = await synthetic('small_evaluation-stored'), sm = await load(s.r.value, s.c.files), sg = DQ.distributionGroup(s.r.value, s.r.value.groups[0].group_id, sm).value;
  const sv = DQ.distributionView(s.r.value, sg, { band: 'NONE' });
  assert.equal(sv.selected, '분위 없음 · 3개'); assert.deepEqual(sv.unavailable.reasons, ['평가 유효 10개 미만 · 분위 없음 3']);
  assert.equal(DQ.distributionView(s.r.value, sg, { band: 10 }).selected, '상위 0–10% · 분위 10 · 0개 · 확인된 빈 구간');
  assert.ok(sv.rows.every((x) => x.rank !== '순위 없음' && /^분위 없음 · /.test(x.band)), 'ranked, scored, no band below N 10');
  // Missing reference (19 < 20): unscored, outside all ten bands, with the reason.
  const mr = await synthetic('missing_reference-stored'), mm = await load(mr.r.value, mr.c.files), mg = DQ.distributionGroup(mr.r.value, mr.r.value.groups[0].group_id, mm).value;
  const mv = DQ.distributionView(mr.r.value, mg, { band: 'NONE' });
  assert.equal(mv.unavailable.count, 20); assert.ok(mv.rows.every((x) => x.score === '미산출' && x.rank === '순위 없음'));
});

test('ties stay as stored and are named; the reference-score candidate is labelled research only and refused on private data', async () => {
  const e = await synthetic('equal_scores-stored'), m = await load(e.r.value, e.c.files), g = e.r.value.groups[0], G = DQ.distributionGroup(e.r.value, g.group_id, m).value;
  assert.ok(g.legacy_tie_splits.length > 0, 'twenty equal scores split by company id across the stored bands');
  assert.match(DQ.distributionView(e.r.value, G).policy, /같은 점수가 구간 경계에서 갈린 곳 \d+곳\(회사 ID 순 · 오너 기준 확인 중\)/);
  const cand = await synthetic('equal_scores-reference-candidate'), cm = await load(cand.r.value, cand.c.files);
  const cv = DQ.distributionView(cand.r.value, DQ.distributionGroup(cand.r.value, cand.r.value.groups[0].group_id, cm).value);
  assert.match(cv.policy, /연구 표시 후보 · 오너 기준 확인 전 · 합성만/); assert.deepEqual(cv.bands.map((b) => b.count), [0, 0, 0, 0, 20, 0, 0, 0, 0, 0]);
  const privCase = await synthetic('equal_scores-reference-candidate', (docs, mf) => { mf.data_kind = 'PRIVATE'; docs['distribution-index.json'].data_kind = 'PRIVATE'; });
  assert.equal(privCase.r.code, 'SYNTHETIC_ONLY');
  const d = F.delivery('operating504'), v = (await DQ.checkDelivery({ manifest: file(d.files, 'manifest.json'), summary: file(d.files, 'summary.json'), index: file(d.files, 'index.json') }, { scope: 'operating504', anchor: F.anchor(), sha256 })).value;
  const refPriv = F.distribution(d, (docs, mf) => { mf.display_policy = 'reference-score-deciles/1'; mf.data_kind = 'PRIVATE'; });
  assert.equal((await DQ.checkDistribution(parts(refPriv), v, sha256)).code, 'POLICY_NOT_CONFIRMED', 'the candidate is never read as private data');
  const priv = F.distribution(d, (docs, mf) => { mf.data_kind = 'PRIVATE'; });
  assert.equal((await DQ.checkDistribution(parts(priv), v, sha256)).code, 'SCOPE_MISMATCH', 'a private manifest beside a synthetic delivery');
});

test('two sector groups stay apart (own N, own bands); a row from another ranking scope is refused', async () => {
  const s = await synthetic('sector_groups-stored'), m = await load(s.r.value, s.c.files);
  assert.equal(s.r.value.groups.length, 2); assert.ok(s.r.value.groups.every((g) => /^SECTOR\|/.test(g.ranking_scope)));
  assert.notEqual(s.r.value.groups[0].ranking_scope, s.r.value.groups[1].ranking_scope);
  for (const g of s.r.value.groups) { const G = DQ.distributionGroup(s.r.value, g.group_id, m); assert.equal(G.ok, true); assert.ok(G.value.rows.every((x) => s.c.scopes[x.company_id].S1 === g.ranking_scope)); }
  const x = await synthetic('sector_groups-stored', (docs) => { const p = docs['distribution-000.json'].parts; const a = p.find((q) => q.group_id === s.r.value.groups[0].group_id), b = p.find((q) => q.group_id === s.r.value.groups[1].group_id);
    const moved = b.rows.pop(); a.rows.push(moved); b.rows.push(JSON.parse(JSON.stringify(a.rows.shift()))); });
  const xm = await load(x.r.value, x.c.files);
  assert.equal(DQ.distributionGroup(x.r.value, x.r.value.groups[0].group_id, xm).code, 'RANKING_SCOPE');
});

test('refused: missing / duplicate rows, wrong bytes, unknown parts, recalculation flags, band words, decile not stored, part not loaded', async () => {
  const id = 'all_ten-stored', grp = async (edit) => { const s = await synthetic(id, edit); if (!s.r.ok) return s.r.code; const m = await load(s.r.value, s.c.files); return DQ.distributionGroup(s.r.value, s.r.value.groups[0].group_id, m).code; };
  const rows = (docs) => docs['distribution-000.json'].parts[0].rows;
  assert.equal(await grp((docs) => { rows(docs).pop(); }), 'GROUP_ROWS', 'a missing row');
  assert.equal(await grp((docs) => { rows(docs)[1] = JSON.parse(JSON.stringify(rows(docs)[0])); }), 'GROUP_ROWS', 'a duplicate row');
  assert.equal(await grp((docs) => { const r = rows(docs).find((x) => x.decile === 10); r.decile = 9; r.stored_decile = 9; }), 'BINS_MISMATCH', 'a moved band');
  assert.equal(await grp((docs) => { rows(docs).find((x) => x.decile === 10).decile = 9; }), 'DECILE_INVALID', 'a display band that is not the stored one');
  assert.equal(await grp((docs) => { const v = rows(docs).filter((x) => x.rank !== null).sort((a, b) => a.rank - b.rank); [v[0].rank, v[1].rank] = [v[1].rank, v[0].rank]; }), 'STORED_ORDER', 'a re-ranked pair');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].rank_recalculated = true; }), 'NOT_PROJECTION');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].filter_changes_population = true; }), 'NOT_PROJECTION');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].bands[0].label = '상위 10%'; }), 'BANDS_INVALID');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].groups[0].comparison_group.n += 1; }), 'COMPARISON_GROUP');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].groups[0].unavailable_count = 1; }), 'BINS_INVALID');
  assert.equal(await grp((docs) => { docs['distribution-index.json'].groups[0].score_direction = 'LOWER_IS_BETTER'; }), 'DIRECTION', 'the score already carries the direction');
  const c = F.distCase(id);
  const r = await DQ.checkDistributionSynthetic(parts(c.files), sha256, { scopes: c.scopes }), part = file(c.files, 'distribution-000.json');
  part.bytes = new Uint8Array(Buffer.concat([Buffer.from(part.bytes), Buffer.from(' ')]));
  assert.equal((await DQ.checkDistributionPart(part, 'distribution-000.json', r.value, sha256)).code, 'BYTES_MISMATCH', 'bytes not the manifest\'s');
  assert.equal((await DQ.checkDistributionPart(file(c.files, 'distribution-000.json'), 'distribution-001.json', r.value, sha256)).code, 'NOT_IN_MANIFEST');
  assert.equal(DQ.distributionGroup(r.value, r.value.groups[0].group_id, new Map()).code, 'PART_NOT_LOADED', 'a part that failed to load is never an empty band');
  const extra = F.distCase(id, (docs) => { docs['distribution-001.json'] = { schema_version: 'qgv-dual-factor-distribution-part/1', parts: [] }; });
  assert.equal((await DQ.checkDistributionSynthetic(parts(extra.files), sha256, { scopes: extra.scopes })).code, 'PART_UNREFERENCED');
});

test('bound to the checked delivery: same models, results, populations, date and companies; anything else is refused', async () => {
  const d = F.delivery('operating504'), v = (await DQ.checkDelivery({ manifest: file(d.files, 'manifest.json'), summary: file(d.files, 'summary.json'), index: file(d.files, 'index.json') }, { scope: 'operating504', anchor: F.anchor(), sha256 })).value;
  const ok = await DQ.checkDistribution(parts(F.distribution(d)), v, sha256);
  assert.equal(ok.ok, true, JSON.stringify(ok)); assert.equal(ok.value.bound, true); assert.equal(ok.value.delivery, v);
  const m = await load(ok.value, F.distribution(d));
  for (const g of ok.value.groups) assert.equal(DQ.distributionGroup(ok.value, g.group_id, m).ok, true, g.group_id);
  const u1 = ok.value.groups.find((g) => g.board === 'U1'), G = DQ.distributionGroup(ok.value, u1.group_id, m).value, gv = DQ.distributionView(ok.value, G, { band: 'NONE' });
  assert.match(gv.head, /U1 · .+ · 통합 비교집단\(평가 집단 전체\)$/); assert.equal(gv.unavailable.count, 3);
  assert.ok(ok.value.groups.filter((g) => g.board === 'S1').every((g) => /^SECTOR\|/.test(g.ranking_scope)), 'S1 groups are sector groups only');
  const bad = async (edit) => (await DQ.checkDistribution(parts(F.distribution(d, edit)), v, sha256)).code;
  assert.equal(await bad((docs) => { docs['distribution-index.json'].boards.U1.result_hash = 'a'.repeat(64); }), 'DIST_BOARD_MISMATCH', 'another result');
  assert.equal(await bad((docs) => { docs['distribution-index.json'].boards.U1.model_id = 'other/1'; }), 'DIST_BOARD_MISMATCH', 'another model');
  assert.equal(await bad((docs) => { docs['distribution-index.json'].boards.S1.evaluation_population.valuation_date = '2026-11-05'; }), 'DIST_BOARD_MISMATCH', 'another valuation date');
  assert.equal(await bad((docs, mf) => { mf.source_results.U1.sha256 = 'b'.repeat(64); }), 'DIST_BOARD_MISMATCH', 'the manifest names another source');
  assert.equal(await bad((docs) => { docs['distribution-index.json'].companies.pop(); }), 'COMPANIES_MISMATCH');
  assert.equal(await bad((docs) => { docs['distribution-index.json'].companies[0].issuer_id = 'issuer:other'; }), 'COMPANIES_MISMATCH');
  assert.equal(await bad((docs, mf) => { mf.scope = 'held1057'; docs['distribution-index.json'].scope = 'held1057'; }), 'SCOPE_MISMATCH');
  assert.equal(await bad((docs) => { docs['distribution-index.json'].groups[0].ranking_scope = 'SECTOR|X|GENERAL'; }), 'RANKING_SCOPE', 'a U1 group is the integrated group');
  assert.equal((await DQ.checkDistribution(parts(F.distribution(d)), { scope: 'operating504' }, sha256)).code, 'DELIVERY_NOT_CHECKED');
});

test('pages: 50 rows a page in stored rank order; the page never changes a rank or N', async () => {
  // Test-made from Codex's all_ten case: 120 equal-width rows (ranks kept from a stored order) to exercise paging only.
  const { c, r } = await synthetic('all_ten-stored'), m = await load(r.value, c.files), G = DQ.distributionGroup(r.value, r.value.groups[0].group_id, m).value;
  const big = { group: G.group, rows: Array.from({ length: 120 }, (_, i) => ({ ...G.rows[0], company_id: 'P' + String(i).padStart(3, '0'), rank: i + 1, decile: 10 })) };
  const p0 = DQ.distributionView(r.value, big, { band: 10 }), p2 = DQ.distributionView(r.value, big, { band: 10, page: 2 }), p9 = DQ.distributionView(r.value, big, { band: 10, page: 9 });
  assert.deepEqual([p0.pages, p0.range, p0.rows.length, p0.rows[0].company_id], [3, '1–50 / 120', 50, 'P000']);
  assert.deepEqual([p2.page, p2.range, p2.rows.length, p2.rows[0].company_id], [2, '101–120 / 120', 20, 'P100']);
  assert.equal(p9.page, 2, 'a page past the end shows the last page');
  assert.equal(p2.rows[0].rank, '101 / ' + G.rows[0].rank_n, 'the stored rank and N as delivered');
});
