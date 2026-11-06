'use strict';
// 의외의 기업 (features 2.1.8 · 2.4.6) test data.
//  - codex(): Codex's public synthetic file of discovery-company/v1, byte-identical to #503 998414635aa4f1899748b1b76fc7ebf3ddc9d12f
//    implementation/docs/research/discovery_company/synthetic.json (sha256 pinned): six cases of one synthetic company SYNTH:001,
//    one per state, each with Codex's expected list / mark / null behaviour.
//  - linked(rows): AT TEST TIME ONLY, the six records put on given company rows ({id}) by qgv_ref.company_id, plus a second
//    SELECTED record (made from Codex's SELECTED case: an earlier first selection, one unconfirmed strength claim) and display
//    claims for type / strength / region / signal on the first SELECTED one, so filters and sections have something to show.
//    Everything stays synthetic (SYNTH: company ids, example.invalid sources); nothing is written to a file.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const FILE = path.join(__dirname, '..', 'tests', 'fixtures', 'discovery_company_v1_codex_synthetic.json');
const CODEX_SHA256 = '4ed5883d277032ebc9012f7966754ad1193765c163f1df548fc6ad03b4246cff';
const codexText = () => fs.readFileSync(FILE, 'utf8');
const codexSha = () => crypto.createHash('sha256').update(fs.readFileSync(FILE)).digest('hex');
const codex = () => JSON.parse(codexText());
const copy = (x) => JSON.parse(JSON.stringify(x));
const caseOf = (state) => copy(codex().cases.find((c) => c.case_id === state).record);
// A display claim added to both judgments and the display list (the reader requires the display to be the record's own).
function addClaim(r, key, category, topic, claim, status = 'CONFIRMED') {
  const ev = r.evidence[0].evidence_id;
  const j = { judgment_id: key + '-' + (topic || 'x').toLowerCase(), category, topic, claim, evidence_ids: [ev], counterevidence_ids: [], status,
    reason: '합성 수작업 대조', reviewed_by: 'synthetic-reviewer', rule_version: 'discovery-rules/1', core: false, material: false };
  r.judgments.push(j); r.display[key].push(copy(j)); return r;
}
function enrich(r, { type, strength, strengthStatus = 'CONFIRMED' }) {
  addClaim(r, 'types', 'TYPE', type, '합성 유형 판단');
  addClaim(r, 'strengths', 'STRENGTH', strength, '합성 강점 판단', strengthStatus);
  addClaim(r, 'regions', 'REGION', 'REVENUE', '합성 매출 지역 판단');
  addClaim(r, 'signals', 'SIGNAL', 'BUYBACK_EXECUTED', '합성 자사주 매입 판단');
  return r;
}
function linked(rows) {
  if (rows.length < 7) throw Error('ROWS_TOO_FEW');
  const states = ['CANDIDATE', 'IN_REVIEW', 'SELECTED', 'REVIEW_REQUIRED', 'SUSPENDED', 'REMOVED'];
  const out = states.map((s, i) => { const r = caseOf(s); r.qgv_ref.company_id = rows[i].id; return r; });
  enrich(out[2], { type: 'FAST_GROWER', strength: '반복 구매' });
  out[3].first_selected_at = '2026-10-20T12:00:00Z';
  const second = enrich(caseOf('SELECTED'), { type: 'CYCLICAL', strength: '반복 구매', strengthStatus: 'UNCONFIRMED' });
  second.qgv_ref.company_id = rows[6].id; second.first_selected_at = '2026-10-01T12:00:00Z';
  out.push(second);
  return out;
}
const edit = (fn, base) => { const out = copy(base); fn(out); return out; };
module.exports = { FILE, CODEX_SHA256, codexText, codexSha, codex, caseOf, linked, edit, enrich };
