'use strict';
// Codex #529's synthetic dual delivery (docs/research/sector_qgv/dual-synthetic: summary, index, detail-000, each pinned in its
// manifest.json) wrapped as one qgv-dual-delivery/1 scope for Main's tests: the files byte for byte, plus the delivery manifest the
// producer writes for a real scope (qgv-dual-delivery-manifest/1, size and SHA-256 of each file). Synthetic only.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const D = path.join(__dirname, '..', 'docs', 'research', 'sector_qgv', 'dual-synthetic');
const FILES = ['summary.json', 'index.json', 'detail-000.json'];
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const raw = Object.fromEntries(FILES.map((f) => [f, fs.readFileSync(path.join(D, f))]));
const pins = JSON.parse(fs.readFileSync(path.join(D, 'manifest.json'), 'utf8')).files;
// Every file is Codex's pinned bytes (its own manifest).
function pinned() { return FILES.every((f) => { const p = pins.find((x) => x.path === f); return p && p.sha256 === sha(raw[f]) && p.bytes === raw[f].length; }); }
const parse = (f) => JSON.parse(raw[f].toString('utf8'));
// The delivery for one scope: {files: name → bytes (Buffer)}. edit(docs) may change the parsed files first (a counterexample);
// edited files are re-serialized and the manifest names their new bytes, so the reader's own checks are what refuse them.
function delivery(scope, edit) {
  const docs = Object.fromEntries(FILES.map((f) => [f, parse(f)]));
  const bytes = {};
  if (edit) { edit(docs); for (const f of FILES) bytes[f] = Buffer.from(JSON.stringify(docs[f], null, 2) + '\n'); } else Object.assign(bytes, raw);
  // Codex's own synthetic delivery manifest (#529 84ab03eb, delivery-manifest.json, sha b758176c…) names these bytes as operating504;
  // it is used as is for that scope; another scope or an edited file gets a manifest of the same shape naming its bytes.
  if (scope === 'operating504' && !edit) {
    bytes['manifest.json'] = fs.readFileSync(path.join(D, 'delivery-manifest.json'));
    return { files: bytes, manifest: JSON.parse(bytes['manifest.json'].toString('utf8')), docs };
  }
  const manifest = { schema_version: 'qgv-dual-delivery-manifest/1', data_kind: 'SYNTHETIC', scope, files: FILES.map((f) => ({ path: f, size: bytes[f].length, sha256: sha(bytes[f]) })) };
  bytes['manifest.json'] = Buffer.from(JSON.stringify(manifest, null, 2) + '\n');
  return { files: bytes, manifest, docs };
}
// The anchor (IS2.referenceView.anchorOf shape) a checked held issuer bundle would give for this synthetic evaluation: operating names
// the evaluation input, held_financial_subsample the reference source input.
function anchor(over = {}) {
  const b = parse('summary.json').boards.U1, e = b.evaluation_population;
  const base = { valuation_date: e.valuation_date, population_id: e.id, population_version: e.version, members_hash: e.members_hash, denominator: e.code_rows, config_hash: null };
  return { scopes: [{ scope: 'operating', ...base, input_hash: e.input_hash, ...(over.operating || {}) },
    { scope: 'held_financial_subsample', ...base, input_hash: b.reference_population.input_hash, ...(over.held_financial_subsample || {}) }] };
}
// The coverage context a held issuer bundle carries for that anchor (for the browser fixture's coverage.json).
function coverageContext(scope) {
  const b = parse('summary.json').boards.U1, e = b.evaluation_population;
  return { valuation_date: e.valuation_date, population: { id: e.id, version: e.version, members_hash: e.members_hash, denominator: e.code_rows },
    result_identity: { input_hash: scope === 'operating' ? e.input_hash : b.reference_population.input_hash } };
}
// A synthetic projection proof (qgv-dual-input-projection-proof/1, the shape of Codex's real input-lineage.json) binding this
// synthetic evaluation and reference source, for the held1057 scope. Test-made: Codex's synthetic set has no proof file.
function lineage(edit) {
  const b = parse('summary.json').boards.U1;
  const x = { schema_version: 'qgv-dual-input-projection-proof/1', evaluation: b.evaluation_population, reference_source: b.bindings.reference,
    evaluation_byte_sha256: 'a'.repeat(64), reference_byte_sha256: 'b'.repeat(64), held_financials_byte_sha256: 'c'.repeat(64),
    selection_rule: 'financials[issuer_id].state != NOT_AVAILABLE', selected_issuer_count: b.evaluation_population.issuers, selected_issuer_members_hash: 'd'.repeat(64),
    rows_equal_source_projection: true, row_values_or_classification_changed: false, changed_top_level_fields: ['rows', 'members', 'snapshot_id', 'universe_id', 'universe_version'],
    reference_source_is_not_eligible_whole_market: true, whole_market_denominator: null, new_score_calculations: 0 };
  if (edit) edit(x);
  return Buffer.from(JSON.stringify(x, null, 2) + '\n');
}
// Codex's synthetic factor leaders companion (dual-factor-leaders-synthetic, pinning Codex's delivery-manifest.json = operating504).
// Unedited for operating504 over the unedited delivery; for another delivery (scope or bytes) the same files re-pointed at that
// delivery's manifest bytes (test-made); edit(docs) changes the parsed index / shard first, and the leaders manifest names the bytes.
const LD = path.join(D, '..', 'dual-factor-leaders-synthetic');
const LFILES = ['factor-leaders.json', 'factor-leaders-000.json'];
function leaders(d, edit) {
  const raw = Object.fromEntries([...LFILES, 'factor-leaders-manifest.json'].map((f) => [f, fs.readFileSync(path.join(LD, f))]));
  const src = sha(d.files['manifest.json']), m0 = JSON.parse(raw['factor-leaders-manifest.json'].toString('utf8'));
  if (!edit && src === m0.source_delivery_manifest_sha256 && d.manifest.scope === m0.scope) return { files: raw };
  const docs = Object.fromEntries(LFILES.map((f) => [f, JSON.parse(raw[f].toString('utf8'))]));
  docs['factor-leaders.json'].scope = d.manifest.scope; docs['factor-leaders.json'].data_kind = d.manifest.data_kind;
  docs['factor-leaders.json'].source_delivery_manifest_sha256 = src;
  if (edit) edit(docs);
  const files = Object.fromEntries(LFILES.map((f) => [f, Buffer.from(JSON.stringify(docs[f], null, 2) + '\n')]));
  const m = { schema_version: m0.schema_version, scope: d.manifest.scope, data_kind: d.manifest.data_kind, source_delivery_manifest_sha256: src,
    files: LFILES.slice().sort().map((f) => ({ path: f, size: files[f].length, sha256: sha(files[f]) })) };
  files['factor-leaders-manifest.json'] = Buffer.from(JSON.stringify(m, null, 2) + '\n');
  return { files };
}
// Codex's synthetic selection contract (dual-leader-selection-synthetic, pinning Codex's synthetic leaders manifest). Unedited when the
// leaders are Codex's own; else re-pointed at those leaders' manifest and delivery (test-made); edit(body) changes it first.
const SD = path.join(D, '..', 'dual-leader-selection-synthetic');
function selection(L, edit) {
  const rawM = fs.readFileSync(path.join(SD, 'factor-leaders-selection-manifest.json')), rawB = fs.readFileSync(path.join(SD, 'factor-leaders-selection.json'));
  const m0 = JSON.parse(rawM.toString('utf8')), src = sha(L.files['factor-leaders-manifest.json']), index = JSON.parse(L.files['factor-leaders.json'].toString('utf8'));
  if (!edit && src === m0.source_leaders_manifest_sha256) return { files: { 'factor-leaders-selection-manifest.json': rawM, 'factor-leaders-selection.json': rawB } };
  const body = JSON.parse(rawB.toString('utf8'));
  Object.assign(body, { scope: index.scope, data_kind: index.data_kind, source_leaders_manifest_sha256: src, source_delivery_manifest_sha256: index.source_delivery_manifest_sha256 });
  if (edit) edit(body);
  const b = Buffer.from(JSON.stringify(body, null, 2) + '\n');
  const m = { schema_version: m0.schema_version, scope: index.scope, data_kind: index.data_kind, source_leaders_manifest_sha256: src, files: [{ path: 'factor-leaders-selection.json', size: b.length, sha256: sha(b) }] };
  return { files: { 'factor-leaders-selection-manifest.json': Buffer.from(JSON.stringify(m, null, 2) + '\n'), 'factor-leaders-selection.json': b } };
}
// Codex's synthetic full factor distributions (#529 430f89ca, dual-distribution-synthetic: cases.json pins each case's manifest).
// distCase(id) gives a case's files as delivered and the ranking scope of each company per board (from the case's own source
// result, as the reader needs it); edit(docs) changes the parsed index / parts first (test-made) and the manifest names the bytes.
const XD = path.join(D, '..', 'dual-distribution-synthetic');
const json = (x) => Buffer.from(JSON.stringify(x, null, 2) + '\n');
function distCase(id, edit) {
  const c = JSON.parse(fs.readFileSync(path.join(XD, 'cases.json'), 'utf8')).cases.find((x) => x.case_id === id), dir = path.join(XD, c.output);
  const files = Object.fromEntries(fs.readdirSync(dir).map((f) => [f, fs.readFileSync(path.join(dir, f))]));
  const src = JSON.parse(fs.readFileSync(path.join(XD, c.source), 'utf8')), scopes = {};
  for (const [k, b] of Object.entries(src)) for (const r of b.rows) (scopes[r.company_id] ||= {})[k] = r.ranking_scope;
  if (edit) remanifest(files, edit);
  return { files, scopes, case: c };
}
function remanifest(files, edit) {
  const names = Object.keys(files).filter((f) => f !== 'distribution-manifest.json'), docs = Object.fromEntries(names.map((f) => [f, JSON.parse(files[f].toString('utf8'))]));
  const m = JSON.parse(files['distribution-manifest.json'].toString('utf8'));
  edit(docs, m);
  for (const f of Object.keys(docs)) files[f] = json(docs[f]);
  m.files = Object.keys(docs).sort().map((f) => ({ path: f, size: files[f].length, sha256: sha(files[f]) }));
  files['distribution-manifest.json'] = json(m);
  return files;
}
// A distribution bound to one fixture delivery (test-made: the stored factor values of its detail rows regrouped per model ×
// ranking scope × factor, the shape of Codex's stored-evaluation-deciles/1 projection; nothing scored). edit(docs, manifest) first.
function distribution(d, edit) {
  const summary = JSON.parse(d.files['summary.json'].toString('utf8')), index = JSON.parse(d.files['index.json'].toString('utf8'));
  const detail = JSON.parse(d.files['detail-000.json'].toString('utf8')).rows, boards = {}, groups = [], parts = [];
  for (const [k, b] of Object.entries(summary.boards)) {
    boards[k] = { model_id: b.model_id, model_version: b.model_version, evaluation_population: b.evaluation_population, reference_population: b.reference_population,
      bindings: b.bindings, result_hash: b.result_hash, normalization_version: b.normalization_version, engine_version: b.engine_version, adapter_version: b.adapter_version,
      configuration_hash: b.configuration_hash, source_result_sha256: sha(Buffer.from(k + b.result_hash)) };
    const by = new Map();
    for (const r of detail) { const x = r.boards[k]; for (const [v, f] of Object.entries(x.factors)) {
      const key = x.ranking_scope + '|' + v; if (!by.has(key)) by.set(key, { scope: x.ranking_scope, v, ref: f.valid_n, rows: [] });
      by.get(key).rows.push({ company_id: r.company_id, score: f.score, rank: f.rank, rank_n: f.rank_n, stored_decile: f.decile, stored_decile_status: f.decile_status,
        decile: f.decile, decile_status: f.score === null ? f.score_status : f.decile_status, score_status: f.score_status, raw_status: f.raw_status, kind: f.kind }); } }
    for (const [, g] of [...by].sort()) {
      const valid = g.rows.filter((r) => r.score !== null), reasons = {}, gid = k + '|' + g.scope + '|' + g.v;
      for (const r of g.rows) if (r.decile === null) reasons[r.decile_status] = (reasons[r.decile_status] || 0) + 1;
      groups.push({ group_id: gid, board: k, ranking_scope: g.scope, variant_id: g.v, raw_direction: 'HIGHER', score_direction: 'HIGHER_IS_BETTER',
        evaluation_rows_in_scope: g.rows.length, evaluation_valid_n: valid.length, reference_valid_n: g.ref || 0,
        comparison_group: { role: 'EVALUATION_VALID', unit: 'EVALUATION_CODE_ROW', n: valid.length, members_hash: sha(Buffer.from(valid.map((r) => r.company_id).sort().join(','))) },
        reference_members_hash: null, reference_issuer_members_hash: null,
        bins: Array.from({ length: 10 }, (_, j) => ({ decile: 10 - j, count: g.rows.filter((r) => r.decile === 10 - j).length })),
        unavailable_count: Object.values(reasons).reduce((a, n) => a + n, 0), unavailable_reasons: reasons, legacy_tie_splits: [], files: ['distribution-000.json'] });
      parts.push({ group_id: gid, rows: g.rows });
    }
  }
  const docs = { 'distribution-index.json': { schema_version: 'qgv-dual-factor-distribution/1', scope: d.manifest.scope, data_kind: 'SYNTHETIC', display_policy: 'stored-evaluation-deciles/1',
    policy_state: 'EXISTING_RULE', bands: Array.from({ length: 10 }, (_, j) => ({ decile: 10 - j, top_percent_from: j * 10, top_percent_to: j * 10 + 10, label: '상위 ' + j * 10 + '–' + (j * 10 + 10) + '%' })),
    boards, companies: index.rows.map((r) => ({ company_id: r.company_id, issuer_id: r.issuer_id, security_id: r.security_id })), groups,
    rank_policy: 'UNROUNDED_FACTOR_SCORE_DESC_COMPANY_ID_ASC_ORDINAL', minimum_reference_score_n: 20, minimum_stored_evaluation_decile_n: 10, complete_evaluation_rows: true,
    filter_changes_population: false, rank_recalculated: false, additional_factor_score_contribution: 0, new_score_calculations: 0, whole_market_denominator: null, whole_market_coverage: null },
    'distribution-000.json': { schema_version: 'qgv-dual-factor-distribution-part/1', parts } };
  const files = { 'distribution-manifest.json': json({ schema_version: 'qgv-dual-factor-distribution-manifest/1', scope: d.manifest.scope, data_kind: 'SYNTHETIC',
    display_policy: 'stored-evaluation-deciles/1', source_results: Object.fromEntries(Object.entries(boards).map(([k, b]) => [k, { result_hash: b.result_hash, sha256: b.source_result_sha256 }])), files: [] }) };
  for (const f of Object.keys(docs)) files[f] = json(docs[f]);
  return remanifest(files, edit || (() => {}));
}
// A synthetic independent reference anchor (qgv-dual-reference-anchor/1, the shape of Codex's real operating-reference-anchor.json)
// naming this synthetic delivery's reference binding, for the operating504 scope. Test-made: Codex's synthetic set has no anchor.
function referenceAnchor(edit) {
  const b = parse('summary.json').boards.U1, e = b.bindings.reference;
  const x = { schema_version: 'qgv-dual-reference-anchor/1', scope: 'operating504', expected_reference: JSON.parse(JSON.stringify(e)),
    source_snapshot_sha256: 'a'.repeat(64), source_reference_view_sha256: 'b'.repeat(64), source_reference_view_path: 'accepted/reference-view.json',
    source_reference_view_input_hash_field: 'reference_population.input_hash', source_reference_view_members_not_interchangeable: true,
    source_original_catalog_binding: { id: 'SYN-CATALOG', input_hash: 'c'.repeat(64) }, matches_all_dual_boards: true, eligible_members_are_not_candidate_members: true,
    old_selected_reference_rows: b.reference_population.code_rows, candidate_rows: e.code_rows, generation_rule: 'synthetic', new_score_calculations: 0 };
  if (edit) edit(x);
  return Buffer.from(JSON.stringify(x, null, 2) + '\n');
}
// All-bin routing for a fixture distribution (test-made, Codex's qgv-dual-factor-bins/1 shape): every group routed to bins-000.json
// with its ten bins (count, saved first/last rank, members hash = SHA-256 of the canonical id list in saved rank order, member files).
const canon = (ids) => '[' + ids.map((x) => JSON.stringify(x)).join(',') + ']';
function bins(dist, edit) {
  const m0 = JSON.parse(dist['distribution-manifest.json'].toString('utf8')), index = JSON.parse(dist['distribution-index.json'].toString('utf8'));
  const desc = Object.fromEntries(m0.files.map((f) => [f.path, f])), rows = {};
  for (const f of Object.keys(dist).filter((x) => /^distribution-\d{3}\.json$/.test(x))) for (const q of JSON.parse(dist[f].toString('utf8')).parts) for (const r of q.rows) (rows[q.group_id] ||= []).push([r, f]);
  const groups = index.groups.map((g) => {
    const b = g.bins.map((x) => { const ms = (rows[g.group_id] || []).filter(([r]) => r.decile === x.decile).sort(([a], [c]) => a.rank - c.rank);
      return { ...x, first_rank: ms.length ? ms[0][0].rank : null, last_rank: ms.length ? ms[ms.length - 1][0].rank : null, members_hash: sha(Buffer.from(canon(ms.map(([r]) => r.company_id)))),
        member_files: [...new Set(ms.map(([, f]) => f))].sort().map((f) => desc[f]) }; });
    const n = g.evaluation_valid_n;
    return { ...g, bins: b, binned_evaluation_n: b.reduce((a, x) => a + x.count, 0), partition_status: n >= 10 ? 'COMPLETE' : n ? 'SAMPLE_LT_10' : 'NO_VALID_SCORE' };
  });
  const docs = { 'bin-index.json': { schema_version: 'qgv-dual-factor-bins/1', scope: index.scope, data_kind: index.data_kind,
    source_distribution_manifest: { path: 'distribution-manifest.json', size: dist['distribution-manifest.json'].length, sha256: sha(dist['distribution-manifest.json']) },
    source_index: desc['distribution-index.json'], display_policy: index.display_policy, boards: index.boards, bands: index.bands, groups: groups.map((g) => ({ group_id: g.group_id, path: 'bins-000.json' })),
    rank_policy: index.rank_policy, minimum_reference_score_n: 20, minimum_stored_evaluation_decile_n: 10, tie_policy: 'PRESERVE_STORED_ORDINAL_COMPANY_ID_BOUNDARIES',
    remainder_policy: 'D10_D1_FLOOR_N_OVER_10;MIDDLE_REMAINDER_D9_TO_D2', new_score_calculations: 0, additional_factor_score_contribution: 0, filter_changes_population: false,
    whole_market_denominator: null, whole_market_coverage: null }, 'bins-000.json': { schema_version: 'qgv-dual-factor-bins-part/1', groups } };
  const m = { schema_version: 'qgv-dual-factor-bins-manifest/1', scope: index.scope, data_kind: index.data_kind, source_manifest_sha256: sha(dist['distribution-manifest.json']), files: [] };
  if (edit) edit(docs, m);
  const out = {};
  for (const f of Object.keys(docs)) out[f] = json(docs[f]);
  m.files = Object.keys(docs).sort().map((f) => ({ path: f, size: out[f].length, sha256: sha(out[f]) }));
  out['bin-manifest.json'] = json(m);
  return out;
}
// Codex #534's 3/3/3 boundary deliveries (qgv333-examples/boundary-delivery/<case>, pinned in its manifest.json), unedited for their
// own population, or re-pointed (test-made) at this synthetic population so a checked held issuer bundle names it: every board's
// evaluation population and binding, and its reference population, become the reduced synthetic delivery's (same members, dates
// and row count), the index names the same evaluation, and a manifest of the same shape names the bytes for the scope. Nothing scored.
const QD = path.join(D, '..', 'qgv333-examples', 'boundary-delivery');
const Q_FILES = ['summary.json', 'index.json', 'detail-000.json'];
function q333(scope, caseId = 'core-missing', edit, { evaluation } = {}) {
  const docs = Object.fromEntries(Q_FILES.map((f) => [f, JSON.parse(fs.readFileSync(path.join(QD, caseId, f), 'utf8'))]));
  const old = parse('summary.json').boards;
  if (scope) {
    for (const b of Object.values(docs['summary.json'].boards)) {
      const o = b.model_id === 'sector-333/0.1.0' ? old.S1 : old.U1;
      b.evaluation_population = o.evaluation_population; b.bindings.evaluation = o.evaluation_population;
      b.reference_population = o.reference_population; b.bindings.reference = o.bindings.reference;
    }
    docs['index.json'].evaluation_population = old.U1.evaluation_population;
  }
  // Or only the evaluation population re-pointed (test-made: another synthetic evaluation of the same members, e.g. the one a
  // browser fixture's coverage names), the reference left as Codex wrote it.
  if (evaluation) {
    for (const b of Object.values(docs['summary.json'].boards)) { b.evaluation_population = evaluation; b.bindings.evaluation = evaluation; }
    docs['index.json'].evaluation_population = evaluation;
  }
  if (edit) edit(docs);
  const made = scope || edit || evaluation;
  const files = Object.fromEntries(Q_FILES.map((f) => [f, made ? Buffer.from(JSON.stringify(docs[f], null, 2) + '\n') : fs.readFileSync(path.join(QD, caseId, f))]));
  const manifest = made ? { schema_version: 'qgv-dual-delivery-manifest/1', data_kind: 'SYNTHETIC', scope: scope || 'operating504', files: Q_FILES.map((f) => ({ path: f, size: files[f].length, sha256: sha(files[f]) })) }
    : JSON.parse(fs.readFileSync(path.join(QD, caseId, 'manifest.json'), 'utf8'));
  files['manifest.json'] = made ? Buffer.from(JSON.stringify(manifest, null, 2) + '\n') : fs.readFileSync(path.join(QD, caseId, 'manifest.json'));
  return { files, manifest, docs };
}
// The 3/3/3 EPS input connection follow-up (test-made, the shape of Codex #534's qgv-333-eps handoff files with made-up counts):
// diagnostic summary / run comparison / continuation inputs and Main's qgv-333-eps-delivery/1 index naming their bytes. deliveries:
// {operating504, held1057} fixture deliveries whose boards' result hashes become each comparison's "before" side. edit(docs) first.
function eps(deliveries, edit) {
  const docs = { diag: {}, comparison: {}, inputs: { schema_version: 'qgv-333-eps-continuation/1', valuation_date: null, retained_as_of: null, new_external_data_requests: 0 } };
  const models = { 'U2-333': 'unified-333-eps/0.1.0', 'U1-333': 'unified-333-persistence/0.1.0', 'S1-333': 'sector-333/0.1.0' };
  let day = null, asOf = null;
  for (const [scope, dk] of [['operating504', 'operating'], ['held1057', 'held']]) {
    const sum = JSON.parse(deliveries[scope].files['summary.json'].toString('utf8')).boards, ev = sum['U2-333'].evaluation_population;
    day = ev.valuation_date; asOf = ev.as_of;
    docs.diag[dk] = { valuation_date: day, as_of: asOf, denominator_issuers: 3, code_rows: 3, target95: 3, security_id_rows: 0,
      endpoint_categories: { NUMERIC_ENDPOINT_CANDIDATE: 2, NONPOSITIVE_ENDPOINT: 1 }, components_any: 3, full_four_year_components: 3, numeric_candidates: 2, adopted_raw: 0,
      structural_bounds: { accounting_only: 3, accounting_incompatible: 0, eps_nonpositive: 1, intersection: 0, union: 1, combined_upper: 2, qualifier: 'CONDITIONAL_UPPER_NOT_COVERAGE; test-made' },
      whole_market_denominator: null };
    docs.comparison[scope] = {};
    for (const k of Object.keys(models)) {
      const b = sum[k], after = { ...b.bindings, evaluation: { ...b.bindings.evaluation, input_hash: 'a'.repeat(64) }, reference: { ...b.bindings.reference, input_hash: 'b'.repeat(64) } };
      const st = (n) => ({ before: n, after: n, new: 0, lost: 0, common_changed: 0 });
      docs.comparison[scope][k] = { stages: { Q: st(b.coverage.stages.Q.issuers), G: st(b.coverage.stages.G.issuers), V: st(0), joint: st(0), total: st(0) },
        factors: { eps_diluted_cagr_3y: { raw_value: { before: 0, after: 0, new: 0, lost: 0 }, score: { before: 0, after: 0, new: 0, lost: 0 } } },
        coverage: {}, before_result_hash: b.result_hash, after_result_hash: 'c'.repeat(64), before_bindings: b.bindings, after_bindings: after,
        overlapping_cause_counts: { input_or_definition_HISTORICAL_SHARE_BASIS_UNCONFIRMED: 3, gate_unknown: 1, accounting_unknown: 0 } };
      if (!models[k]) throw Error('model');
    }
  }
  docs.inputs.valuation_date = day; docs.inputs.retained_as_of = asOf;
  if (edit) edit(docs);
  const files = { 'diagnostic-summary.json': json(docs.diag), 'run-comparison.json': json(docs.comparison), 'continuation-inputs.json': json(docs.inputs) };
  const index = { schema_version: 'qgv-333-eps-delivery/1', data_kind: 'SYNTHETIC',
    source: { handoff_path: 'handoffs/test-made', handoff_manifest_sha256: 'd'.repeat(64), producer_sha: '1'.repeat(40), execution_sha: '2'.repeat(40) },
    valuation_date: day, input_as_of: asOf,
    files: { diagnostic: { size: files['diagnostic-summary.json'].length, sha256: sha(files['diagnostic-summary.json']) },
      comparison: { size: files['run-comparison.json'].length, sha256: sha(files['run-comparison.json']) },
      continuation: { size: files['continuation-inputs.json'].length, sha256: sha(files['continuation-inputs.json']) } },
    result_delivery: null, new_external_requests: 0 };
  if (docs.index) Object.assign(index, docs.index);
  files['eps-index.json'] = json(index);
  return { files, docs, index };
}
// The 3/3/3 Q input recovery (test-made, the shape of Codex #534 4352c8ec's qgv-q-input handoff files with made-up counts): its
// diagnostic summary / comparison chained to an eps() case (each "before" result = that case's "after" result) and Main's
// qgv-333-q-input-delivery/1 index naming their bytes. edit(docs) changes docs.diag / docs.comparison / docs.index before hashing.
function qinput(epsCase, edit) {
  const docs = { diag: {}, comparison: {} }, cutoff = '2026-02-04T12:00:00Z';
  let day = null;
  for (const scope of ['operating504', 'held1057']) {
    const prev = epsCase.docs.comparison[scope];
    day = prev['U2-333'].after_bindings.evaluation.valuation_date;
    docs.diag[scope] = { denominator_issuers: 3, code_rows: 3,
      primary_q_causes: { Q_AVAILABLE: 2, CLASSIFICATION_OR_ACCOUNTING_UNCONFIRMED: 1 },
      overlapping_q_causes: { CLASSIFICATION_OR_ACCOUNTING_UNCONFIRMED: 1, ELIGIBLE_FINANCIAL_COMPONENT_MISSING: 1 },
      gate_diagnostic: { DECISION_KNOWN_NOT_NECESSARILY_PASS: 2, OFFICIAL_INPUT_PRESENT_RECIPE_UNRESOLVED: 1 },
      official_input_linkage: { PERCENTILE_LINKED: 3 }, raw_validator_is_fail_fast: true, whole_market_denominator: null };
    docs.comparison[scope] = {};
    for (const k of ['U2-333', 'U1-333', 'S1-333']) {
      const p = prev[k], st = (b, a) => ({ before: b, after: a, gained: a - b, lost: 0, common_score_changed: 1 }), same = (n) => st(n, n);
      const bind = (b, asOf) => ({ ...b, evaluation: { ...b.evaluation, members_hash: '7'.repeat(64), as_of: asOf }, reference: { ...b.reference, members_hash: '8'.repeat(64) } });
      docs.comparison[scope][k] = { stages: { Q: st(1, 2), G: same(0), V: same(0), joint: same(0), total: same(0) },
        factors: { debt_assets: { raw_value: st(1, 2), score: st(1, 2) } },
        before_result_hash: p.after_result_hash, after_result_hash: 'e'.repeat(64),
        before_bindings: bind(p.after_bindings, p.after_bindings.evaluation.as_of), after_bindings: bind(p.after_bindings, cutoff) };
    }
  }
  if (edit) edit(docs);
  const files = { 'diagnostic-summary.json': json(docs.diag), 'comparison.json': json(docs.comparison) };
  const index = { schema_version: 'qgv-333-q-input-delivery/1', data_kind: 'SYNTHETIC',
    source: { handoff_path: 'handoffs/test-made', handoff_manifest_sha256: 'f'.repeat(64), producer_sha: '3'.repeat(40), execution_sha: '4'.repeat(40) },
    clocks: { valuation_date: day, original_input_cutoff: '2026-02-02T12:00:00Z', input_cutoff: cutoff, reviewed_at: '2026-02-04T11:00:00Z', producer_verified_at: '2026-02-04T12:05:00Z', calculated_at: null },
    result_kind: 'RETROSPECTIVE_REVIEW', historical_system_pit_complete: false,
    review_records: { operating: 1, held: 2, operating_reference: 1, catalog_reference: 2 }, source_snapshots_reused: true, producer_verification_passed: true,
    continues: { step: 'qgv-333-eps-delivery/1', eps_comparison_sha256: sha(epsCase.files['run-comparison.json']), boards: 6 },
    files: { diagnostic: { size: files['diagnostic-summary.json'].length, sha256: sha(files['diagnostic-summary.json']) },
      comparison: { size: files['comparison.json'].length, sha256: sha(files['comparison.json']) } },
    result_delivery: null };
  if (docs.index) Object.assign(index, docs.index);
  files['q-index.json'] = json(index);
  return { files, docs, index };
}
module.exports = { qinput, eps, q333, D, FILES, raw, pinned, parse, delivery, anchor, coverageContext, lineage, leaders, selection, sha, distCase, distribution, referenceAnchor, bins };
