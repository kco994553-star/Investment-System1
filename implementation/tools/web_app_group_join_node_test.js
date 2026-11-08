'use strict';
// 공통 분류 그룹 결합 /2 (owner 2026-11-08 「공통 분류 최신 계약 반영 및 소비자 반례 마무리」; Codex #516 5b0ec88a GROUP_JOIN.md):
//  - Codex's group-join-fixtures.json read directly (its SHA-256 from group-join-manifest.json, whose own SHA-256 is pinned): all
//    23 cases through Main techScreen.joinGroupRows give exactly Codex's expected success / refusal code, selected and original
//    group counts, membership validation and issuer connection count; selected rows in input order with their original score
//    and rank; inputs never changed.
//  - IS2.classification.buildGroupManifest = Codex build_group_manifest on the fixture bundles (base, confirmed empty, shared
//    issuer, other-day applicability).
//  - The call site (groupInput → joinGroupRows, connect_issuers) on the page-code run: Codex's recorded result for the normal
//    group and the three counterexamples Codex found in Main 23dd5dc5 (row hash, row record id, other-day record) plus missing /
//    duplicate rows.
//  - /1 without a roster stays identity-only (no membership_validation).
const assert = require('node:assert/strict');
const path = require('node:path');
const T = require('../src/investment_system/product/web_app/tech-screen.js');
const C = require('../src/investment_system/product/web_app/classification.js');
const X = require('./web_app_classification_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const F = X.groupFixtures(), GM = X.groupManifest();

ok('pins: group-join-manifest.json, and GROUP_JOIN.md / group-join-fixtures.json / consumer-probe.cjs as it pins them', () => {
  assert.equal(X.sha(path.join(X.HANDOFF_DIR, 'group-join-manifest.json')), X.GROUP_MANIFEST_SHA256);
  for (const f of GM.files) assert.equal(X.sha(path.join(X.HANDOFF_DIR, f.path)), f.sha256, f.path);
  assert.equal(F.cases.length, 23); assert.equal(F.data_kind, 'SYNTHETIC');
});
const outcome = (r) => (r.ok ? { ok: true, selected_count: r.selected_count, original_group_count: r.original_group_count, membership_validation: r.membership_validation,
  issuer_connections: r.issuer_connections.length } : { ok: false, code: r.code });
for (const c of F.cases) {
  ok('case ' + c.id + ': Main joinGroupRows = Codex expected (' + (c.expected.ok ? c.expected.membership_validation + ' ' + c.expected.selected_count : c.expected.code) + ')', () => {
    const v = X.applyCase(F.base, c), a = v.join, before = JSON.stringify(v);
    const r = T.joinGroupRows(a.board, a);
    assert.deepEqual(outcome(r), c.expected);
    if (r.ok) {
      const original = new Map(a.qgv_rows.map((x) => [x.code, x]));
      assert.deepEqual(r.rows.map((x) => x.code), a.qgv_rows.map((x) => x.code).filter((k) => r.rows.some((y) => y.code === k)), 'input order');
      for (const x of r.rows) { assert.deepEqual(x.score, original.get(x.code).score); assert.deepEqual(x.rank, original.get(x.code).rank); }
    }
    assert.equal(JSON.stringify(v), before, 'inputs unchanged');
  });
}
ok('issuer connection is recorded (previous field / value, record, hash, signal day, cutoff, evidence, basis); the original row keeps null', () => {
  const v = X.applyCase(F.base, F.cases.find((c) => c.id === 'issuer_evidence_connection')), a = v.join, r = T.joinGroupRows(a.board, a);
  const x = r.issuer_connections[0], m = a.group_manifest.members[0];
  assert.deepEqual({ ...x, evidence_refs: [...x.evidence_refs] }, { company_id: m.company_id, previous_field_present: true, previous_issuer_id: null, issuer_id: m.issuer_id,
    classification_record_id: m.classification_record_id, classification_hash: a.group_context.classification_hash, signal_day: a.group_context.signal_day,
    knowledge_as_of: a.group_context.knowledge_as_of, evidence_refs: m.evidence_refs, basis: 'VERIFIED_CLASSIFICATION_RECORD' });
  assert.equal(a.qgv_rows[0].issuer_id, null); assert.equal(r.rows.find((y) => y.code === m.company_id).issuer_id, m.issuer_id);
});
ok('roster port: IS2.classification.buildGroupManifest = Codex build_group_manifest on the fixture bundles', () => {
  for (const id of [null, 'confirmed_empty', 'two_codes_one_issuer']) {
    const v = id ? X.applyCase(F.base, F.cases.find((c) => c.id === id)) : structuredClone(F.base), m = C.buildGroupManifest(v.bundle.view, v.bundle.technical, v.join.group_context.group_id);
    assert.equal(m.ok, true, id); assert.deepEqual(JSON.parse(JSON.stringify(m.value)), v.join.group_manifest, id || 'base');
  }
  const off = X.applyCase(F.base, F.cases.find((c) => c.id === 'classification_not_applicable_on_day')), m = C.buildGroupManifest(off.bundle.view, off.bundle.technical, off.join.group_context.group_id).value;
  assert.equal(m.membership_status, off.join.group_manifest.membership_status); assert.deepEqual([...m.reasons], off.join.group_manifest.reasons);
  const bad = structuredClone(F.base); delete bad.bundle.view.universe_id;
  assert.equal(C.buildGroupManifest(bad.bundle.view, bad.bundle.technical, bad.join.group_context.group_id).code, 'GROUP_UNIVERSE_CONTEXT_REQUIRED');
  assert.equal(T.populationHash(F.base.join.board.group_id, F.base.join.board.signal_day, F.base.join.group_manifest.members.map((x) => x.security_id)), F.base.join.board.population_hash);
});

// ---------------- the call site on the page-code run (Codex's recorded results: main fixture universe.group_join.cases)
const GJ = X.universe().group_join, M = X.main();
const bundle = (view = GJ.view) => { const r = C.validate({ view, technical: GJ.technical, dictionary: M.dictionary }); assert.equal(r.ok, true); return r.value; };
// Page rows for the 3 members plus 2 outside the group; issuer null (Main has none), keys as the board evidences them.
const page = () => [...GJ.qgv_rows.map((r) => ({ ...r, issuer_id: null })), { id: 'NYSE:OUT1', code: 'NYSE:OUT1', issuer_id: null, signal_day: null, security_id: null, score: { total: 50 }, rank: { official: 7, of: 504 } },
  { id: 'amd', code: 'NASDAQ:AMD', issuer_id: null, signal_day: null, security_id: null, score: { total: 40 }, rank: { official: 9, of: 504 } }];
function callSite(rows, b = bundle()) {
  const gi = C.groupInput(GJ.board, rows, b);
  if (gi.code) return { ok: false, code: gi.code };
  return outcome(T.joinGroupRows(GJ.board, { qgv_rows: gi.rows, security_links: GJ.security_links, conditions: GJ.conditions, data_kind: 'SYNTHETIC', group_manifest: gi.manifest, group_context: gi.context, connect_issuers: true }));
}
const CASES = {
  normal_issuer_connected: () => callSite(page()),
  row_hash_mismatch: () => callSite(page().map((r, i) => (i ? r : { ...r, classification_hash: 'b'.repeat(64) }))),
  row_record_mismatch: () => callSite(page().map((r, i) => (i ? r : { ...r, classification_record_id: 'SYNTHETIC:WRONG' }))),
  classification_not_applicable_on_day: () => callSite(page(), bundle(GJ.view_not_applicable_on_day)),
  member_row_missing: () => callSite(page().slice(1)),
  duplicate_row: () => callSite([...page(), page()[0]]),
};
for (const [name, run] of Object.entries(CASES)) {
  ok('call site ' + name + ': groupInput → joinGroupRows = Codex (' + (GJ.cases[name].ok ? 'join ' + GJ.cases[name].selected_count : GJ.cases[name].code) + ')', () => {
    const rows = page(), before = JSON.stringify(rows);
    assert.deepEqual(run(), GJ.cases[name]);
    assert.equal(JSON.stringify(rows), before);
  });
}
ok('call site: out-of-group rows are never passed and keep their score / rank; the roster comes from the record set, not the rows', () => {
  const rows = page(), gi = C.groupInput(GJ.board, rows, bundle());
  assert.deepEqual(gi.rows.map((r) => r.code), GJ.codes);
  assert.deepEqual(rows.slice(3).map((r) => [r.code, r.score.total, r.rank.official]), [['NYSE:OUT1', 50, 7], ['NASDAQ:AMD', 40, 9]]);
  assert.equal(C.groupInput(GJ.board, rows.slice(0, 1), bundle()).manifest.members.length, 3, 'fewer rows never shrink the roster');
});
ok('/1 without a roster: identity only, completeness NOT_CHECKED (no membership_validation)', () => {
  const j = T.joinRows(F.base.join.board, F.base.join.qgv_rows, { links: F.base.join.security_links, data_kind: 'SYNTHETIC' });
  assert.equal(j.ok, true); assert.equal(j.membership_validation, undefined);
  assert.ok(T.joinText({ ok: false, code: 'GROUP_CONTEXT_MISMATCH:signal_day' }).includes('요청 문맥 ≠ 그룹 명부 문맥 · signal_day'));
});
console.log(JSON.stringify({ passed: true, checks: n }));
