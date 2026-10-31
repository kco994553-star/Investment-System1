'use strict';
// The synthetic central V publication for old-app browser tests (DC-31, PR-1b): tests/fixtures/qgv_official_vectors_v1.json
// base_text (a strictly valid qgv-official/1 payload built from synthetic inputs by tests/build_qgv_official_vectors.py; its input
// as_of equals the qgv_v2_fixture.js strictPayload, so the published rows join that sec-qgv2.json). No real price anywhere.
// routeOfficial(context) serves it as qgv-official.json; registered after routeEmptyPublicScreens it wins (Playwright runs the
// most recently registered matching route first).
const fs = require('node:fs'), path = require('node:path');
const VECTORS = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')), PUB_TEXT = VECTORS.base_text, PUB = JSON.parse(PUB_TEXT);
// A second strictly valid publication for 'a new publication arrives' phases: the vector case target_live_unplaced_valid (other
// published ranks) under another publication_id and a later generation time. Still synthetic; checked by qgv_official_node_test.js
// only through the same validator the page runs (QgvOfficial.validate), so a test using it fails closed if it stops validating.
function variant(caseId, edit) {
  const c = VECTORS.cases.find((x) => x.id === caseId), p = JSON.parse(PUB_TEXT), del = JSON.stringify(VECTORS.delete_marker);
  for (const op of c.ops) { let o = p;for (const k of op.path.slice(0, -1)) o = o[k];const last = op.path[op.path.length - 1];if (JSON.stringify(op.value) === del) delete o[last];else o[last] = op.value; }
  if (edit) edit(p);return p;
}
const PUB2 = variant('target_live_unplaced_valid', (p) => { p.publication_id = 'qgvpub-' + 'b'.repeat(64);p.times.generated_at = '2026-10-13T22:50:00Z'; }), PUB2_TEXT = JSON.stringify(PUB2);
async function routeOfficial(context, body = PUB_TEXT) {
  await context.route('**/qgv-official.json*', (r) => r.fulfill({ status: 200, contentType: 'application/json', body }));
}
// Published official ranks by row key, and the Q·G reference order (one place per CIK; rank_row elsewhere).
const RANKS = Object.fromEntries(Object.entries(PUB.rows).filter(([, r]) => Number.isInteger(r.rank)).map(([k, r]) => [k, r.rank]));
const QG_ORDER = Object.fromEntries(Object.entries(PUB.rows).filter(([, r]) => Number.isInteger(r.qg_reference_order)).map(([k, r]) => [k, r.qg_reference_order]));
module.exports = { PUB_TEXT, PUB, PUB2_TEXT, PUB2, RANKS, QG_ORDER, routeOfficial, variant };
