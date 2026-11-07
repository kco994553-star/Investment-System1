'use strict';
// 4.5 정책·지정학 test data (owner 2026-11-07). Every file here is Codex engine output (#509 e0bb68dd,
// research/policy_impact/build.py); Main never writes a policy-impact-view/1 by hand.
//  - codexView(), states(): Codex's shared synthetic view and state cases, SHA-256 pinned as handed over on #437.
//  - variants(): REVISED / HISTORICAL / NEWS, made by tools/policy_impact_main_variants.py through Codex's build
//    (tests/test_policy_impact_main_variants.py checks the file is exactly that output).
//  - linked(ids, base): AT TEST TIME ONLY, the synthetic company ids synthetic-company-0..2 put on given company rows so the
//    company links have something to join; nothing is written to a file. edit(fn, base): a changed copy for refusal cases.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ROOT = path.join(__dirname, '..');
const CODEX = path.join(ROOT, 'docs', 'research', 'policy_impact');
const FILES = {
  contract: [path.join(CODEX, 'contract.json'), '27f19446fb1f9a8e97b9c294a8cb56cf86589cc8e5b1f5ac903f23c12af4db77'],
  job: [path.join(CODEX, 'synthetic-job.json'), '3ad15846a4c75cc13be225f48b5d8e369ec322b5e134ba938ad5b65c4e322150'],
  view: [path.join(CODEX, 'synthetic-view.json'), '5ded2d6b9f444674cde7ddcf4bbcd783d212a7a62076bd67c6b8faa98d03f2b8'],
  states: [path.join(CODEX, 'synthetic-states.json'), '8c78d04be86039110644b668bb7a527e7fba7b6a61d9be528c79976eaf0818d8'],
};
const VARIANTS = path.join(ROOT, 'tests', 'fixtures', 'policy_impact_view_main_variants.json');
const sha = (f) => crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const read = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const codexView = () => read(FILES.view[0]);
const states = () => read(FILES.states[0]);
const contract = () => read(FILES.contract[0]);
const variants = () => read(VARIANTS).variants;
const copy = (v) => JSON.parse(JSON.stringify(v));
const edit = (fn, base = codexView()) => { const out = copy(base); fn(out); return out; };
function linked(ids, base = codexView()) {
  const map = { 'synthetic-company-0': ids[0], 'synthetic-company-1': ids[1], 'synthetic-company-2': ids[2] };
  const swap = (v) => (Object.prototype.hasOwnProperty.call(map, v) && map[v] ? map[v] : v);
  return edit((v) => {
    for (const e of v.bundle.exposures) e.company_id = swap(e.company_id);
    for (const x of v.bundle.hypotheses) { x.company_ids = x.company_ids.map(swap); for (const w of x.watch_items) w.reference_id = swap(w.reference_id); }
  }, base);
}
module.exports = { FILES, VARIANTS, sha, codexView, states, contract, variants, edit, linked };
