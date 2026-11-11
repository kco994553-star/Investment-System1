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
module.exports = { D, FILES, raw, pinned, parse, delivery, anchor, coverageContext, lineage, sha };
