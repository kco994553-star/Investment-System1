'use strict';
// 공통 분류 (DC-48, owner 2026-11-07) test helpers (tools/web_app_classification_node_test.js, web_app_classification_browser_test.js).
//  - MAIN: tests/fixtures/common_classification_main/main_fixture.json, the output of Codex's own functions on Codex's own cases
//    (tools/common_classification_main_fixture.py; pytest tests/test_common_classification_main_fixture.py checks it byte for byte),
//    SHA-256 pinned here. Nothing in it is written by Main.
//  - HANDOFF: Codex's handoff files (docs/research/common_classification, #516 9343b5e6) with the SHA-256 of its manifest.
//  - payload(...): the IS2.classification source payload a test puts in place of source() — parts of the fixture as they are.
// SYNTHETIC VALUES ONLY; nothing here is written to a public file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { ROOT } = require('./web_app_reuse');

const MAIN_PATH = path.join(ROOT, 'implementation/tests/fixtures/common_classification_main/main_fixture.json');
const MAIN_SHA256 = '31c71cddaafcbd896c228e5677e32a2584e32a3e1a95851aceaaa398087465fe';
const HANDOFF_DIR = path.join(ROOT, 'implementation/docs/research/common_classification');
const HANDOFF_SHA256 = { 'CONTRACT.md': '00bccc2c38ae03e037ff820d6010a251b87f35983dadf1986217d0a1989258ea',
  'fixtures.json': '526cbf85defddbc4b255ea8dc5194ccab034c5eb9b317ef94142b5338c26ebcf', 'dictionary.json': '9ae49c5f849535d325aaa64689da9fa61147347a9c8f8dafcf4055c0ef6d5776' };
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const main = () => JSON.parse(fs.readFileSync(MAIN_PATH, 'utf8'));
const mainSha = () => sha(MAIN_PATH);
const handoffSha = (name) => sha(path.join(HANDOFF_DIR, name));
const codexFixtures = () => JSON.parse(fs.readFileSync(path.join(HANDOFF_DIR, 'fixtures.json'), 'utf8'));
// The CLI run's four parts and the dictionary (the bundle that carries one record per company in every part).
const bundle = (M = main()) => ({ view: M.bundle.view, qgv_links: M.bundle.qgv_links, technical: M.bundle.technical, macro: M.bundle.macro, dictionary: M.dictionary });
// A technical case: its view, its technical projection and (normal only) its macro projection.
const technicalCase = (name, M = main()) => { const c = M.technical_cases[name]; return { view: c.view, technical: c.technical, macro: c.macro, dictionary: M.dictionary }; };
const recordCase = (name, M = main()) => { const c = M.record_cases[name]; return { view: c.view, macro: c.macro, dictionary: M.dictionary }; };
// The same Codex runs on the browser page's Universe504 codes (only the input company ids renamed; Codex computed the rest).
const universe = (M = main()) => M.universe;
const uBundle = (M = main()) => { const { qgv_preview, ...b } = M.universe.bundle; return { ...b, dictionary: M.dictionary }; };
const uTechnical = (M = main()) => { const t = M.universe.technical_normal; return { view: t.view, technical: t.technical, macro: t.macro, dictionary: M.dictionary }; };
const uRecord = (name, M = main()) => { const c = M.universe.record_cases[name]; return { view: c.view, macro: c.macro, dictionary: M.dictionary }; };
// Another technical run on the page codes: 'nine_valid', 'missing_security' or 'shared_issuer' (view + technical; no macro).
const uTech = (name, M = main()) => { const t = M.universe['technical_' + name]; return { view: t.view, technical: t.technical, dictionary: M.dictionary }; };
// The Codex join counterexamples (tools/technical_filter_join_main_cases.py; pytest checks them against Codex join_filtered_rows).
const JOIN_CASES_PATH = path.join(ROOT, 'implementation/tests/fixtures/technical_filter_join_main/cases.json');
const JOIN_CASES_SHA256 = 'a527c51062c038cea8e0ca6e047476ad3ee48732e0c49cec2d720f10d999a3a1';
const joinCases = () => JSON.parse(fs.readFileSync(JOIN_CASES_PATH, 'utf8'));
// Codex #516 5b0ec88a group join handoff: group-join-manifest.json (its own SHA-256 pinned here) pins GROUP_JOIN.md,
// group-join-fixtures.json (23 cases + expected) and consumer-probe.cjs.
const GROUP_MANIFEST_SHA256 = 'bee3740c437ce07c60895f3093e19d106122c95143150cacf52f9faf7d27e2e1';
const groupManifest = () => JSON.parse(fs.readFileSync(path.join(HANDOFF_DIR, 'group-join-manifest.json'), 'utf8'));
const groupFixtures = () => JSON.parse(fs.readFileSync(path.join(HANDOFF_DIR, 'group-join-fixtures.json'), 'utf8'));
// Codex's case application (consumer-probe.cjs / technical_membership_cases.apply_case): sets, then removes, on a deep copy.
function applyCase(base, c) { const v = structuredClone(base);
  for (const [keys, value] of c.sets) { let p = v; for (const k of keys.slice(0, -1)) p = p[k]; p[keys.at(-1)] = structuredClone(value); }
  for (const keys of c.removes) { let p = v; for (const k of keys.slice(0, -1)) p = p[k]; delete p[keys.at(-1)]; }
  return v; }
// Synthetic calculation_counts (Codex #523 common-classification-calculation-counts/1, the full producer shape) tied to a test view
// and summary: the operating scope is the view's universe (id, version, members, issuers, the producer's members hash: sha256 of the
// sorted member ids as compact JSON) and names the view's hash, day and versions; the expanded scopes repeat the summary's
// denominators and counts, the held subsample ranked in the catalog. Test numbers only (they show where each value lands on the
// page); the real counts come from Codex's retained results.
function syntheticCounts(view, summary, { opQ, opG, heldGate, catGate }) {
  const H = (c) => c.repeat(64), digest = (ids) => crypto.createHash('sha256').update(JSON.stringify([...ids].sort())).digest('hex');
  const count = (valid, den, reason = 'NULL_IN_RETAINED_RESULT') => ({ valid, denominator: den, uncomputed: den - valid,
    status: den === 0 ? 'EMPTY_POPULATION' : valid === 0 ? 'NOT_COMPUTED' : valid === den ? 'COMPLETE' : 'PARTIAL', reason: valid === den ? null : reason });
  const ref = (name, c) => ({ ref: 'synthetic://' + name, sha256: H(c) });
  const gate = (valid, den) => ({ ...count(valid, den), reason: null, meaning: 'CONNECTED_INPUT_NOT_GATE_PASS_NOT_SECTOR_Q', calc_version: 'qgv2-calc/synthetic',
    basis: 'RETAINED_UNIVERSE504_OFFICIAL_Q_REPLAY_NOT_EXPANDED_Q', sources: { gate_linkage: ref('official-gate-linkage.json', 'a'), held_cohort: ref('held.json', 'b') } });
  const versions = (universe) => ({ model_version: 'sector-qgv-default/0.1.0', engine_version: 'sector-qgv-engine/0.1.0', normalization_version: 'sector-midrank-strict20/1',
    mapping_version: 'book-sector-map/1', input_version: 'common-classification-qgv/1', snapshot_id: 'synthetic-snapshot', universe_id: universe.id, universe_version: universe.version });
  const scope = (pop, scoring, counts, gateCount, cls) => ({ population: pop, scoring_population: scoring, valuation_date: summary.valuation_date,
    input_as_of: summary.valuation_date + 'T02:00:00Z', versions: versions(scoring), classification: cls,
    result_identity: { preview_id: H('2'), config_hash: H('c'), input_hash: H('7'), cache_key: H('8') },
    sources: { snapshot: ref('snapshot.json', '4'), preview: ref('preview.json', '9'), view: ref('view.json', '3') }, counts, official_q_gate_input: gateCount });
  const counts = (n, q, g, v = 0, joint = 0, total = 0) => ({ Q: count(q, n), G: count(g, n), V: count(v, n), joint: count(joint, n), total: count(total, n) });
  const opCls = { schema_version: 'common-classification-view/1', classification_hash: view.classification_hash, dictionary_version: view.dictionary_version,
    mapping_version: view.mapping_version, knowledge_as_of: view.knowledge_as_of };
  const exCls = { ...opCls, classification_hash: H('5') }, n = view.members.length;
  const opPop = { id: view.universe_id, version: view.universe_version, unit: 'CODE_ROW', denominator: n, unique_issuers: new Set(view.rows.map((r) => r.issuer_id)).size, members_hash: digest(view.members) };
  const issuers = (k, tag) => Array.from({ length: k }, (_, i) => 'ISSUER:' + tag + String(i).padStart(6, '0'));
  const catIds = issuers(summary.catalog.issuers, 'C'), heldIds = catIds.slice(0, summary.held_financial_subsample.issuers);
  const catPop = { id: 'catalog', version: 'synthetic/1', unit: 'ISSUER', denominator: catIds.length, unique_issuers: catIds.length, members_hash: digest(catIds) };
  const heldPop = { id: 'catalog:held', version: 'synthetic/1', unit: 'ISSUER', denominator: heldIds.length, unique_issuers: heldIds.length, members_hash: digest(heldIds) };
  const catScore = { id: catPop.id, version: catPop.version, denominator: catPop.denominator, members_hash: catPop.members_hash };
  const c = summary.catalog, h = summary.held_financial_subsample;
  return { schema_version: 'common-classification-calculation-counts/1', data_kind: view.data_kind, valuation_date: summary.valuation_date,
    operation: 'EXTRACT_EXISTING_RESULTS_NO_RECALCULATION', source_summary: ref('summary.json', '6'), full_market_denominator: null, full_market_coverage: null,
    scopes: { operating: scope(opPop, { id: opPop.id, version: opPop.version, denominator: n, members_hash: opPop.members_hash }, counts(n, opQ, opG),
      { valid: null, denominator: n, uncomputed: null, status: 'NOT_MEASURED', reason: 'NO_OPERATING_GATE_AUDIT_REQUESTED' }, opCls),
      held_financial_subsample: scope(heldPop, catScore, counts(h.issuers, h.Q, h.G, h.V, h.joint, h.total), gate(heldGate, h.issuers), exCls),
      catalog: scope(catPop, catScore, counts(c.issuers, c.Q, c.G, c.V, c.joint, c.total), gate(catGate, c.issuers), exCls) } };
}
module.exports = { syntheticCounts, GROUP_MANIFEST_SHA256, groupManifest, groupFixtures, applyCase, uTech, JOIN_CASES_PATH, JOIN_CASES_SHA256, joinCases, universe, uBundle, uTechnical, uRecord, MAIN_PATH, MAIN_SHA256, HANDOFF_DIR, HANDOFF_SHA256, sha, main, mainSha, handoffSha, codexFixtures, bundle, technicalCase, recordCase };
