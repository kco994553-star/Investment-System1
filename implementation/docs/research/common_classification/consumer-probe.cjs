// Offline intake diagnostic. Runs the supplied Main SHA's actual reader functions.
// No browser, source fetch, production changes or replacement consumer algorithm.
// Usage: node consumer-probe.cjs /path/to/Main-checkout [group-join-fixtures.json]
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(process.argv[2]);
const fixture = JSON.parse(fs.readFileSync(process.argv[3] || path.join(__dirname, 'group-join-fixtures.json')));
const C = require(path.join(root, 'implementation/src/investment_system/product/web_app/classification.js'));
const T = require(path.join(root, 'implementation/src/investment_system/product/web_app/tech-screen.js'));
function apply(c) {
  const v = structuredClone(fixture.base);
  for (const [keys, value] of c.sets) {
    let p = v; for (const key of keys.slice(0, -1)) p = p[key]; p[keys.at(-1)] = structuredClone(value);
  }
  for (const keys of c.removes) {
    let p = v; for (const key of keys.slice(0, -1)) p = p[key]; delete p[keys.at(-1)];
  }
  return v;
}
function run(v) {
  const a = v.join, checked = C.validate(v.bundle);
  if (!checked.ok) return { ok: false, stage: 'classification', code: checked.code };
  const g = C.groupRowsWhy(a.board, a.qgv_rows, checked.value);
  if (g.code) return { ok: false, stage: 'group', code: g.code };
  const joined = T.joinRows(a.board, g.rows, { links: a.security_links, data_kind: a.data_kind });
  if (!joined.ok) return { ok: false, stage: 'join', code: joined.code };
  const evaluated = T.evaluate(a.board, a.conditions);
  const kept = g.rows.filter(r => evaluated.rows.get(r.security_id)?.state === 'PASS');
  return { ok: true, selected_count: kept.length, original_group_count: g.rows.length,
    rows: kept.map(r => ({ code: r.code, issuer_id: r.issuer_id, classification_record_id: r.classification_record_id,
      classification_hash: r.classification_hash ?? null, score: r.score, rank: r.rank })),
    membership_validation: null, issuer_connection_audit: null };
}
const results = fixture.cases.map(c => {
  const v = apply(c), before = JSON.stringify(v), actual = run(v);
  // Only acceptance/count equivalence; this is not /2 contract or browser acceptance.
  return { case: c.id, expected: c.expected, actual, input_unchanged: JSON.stringify(v) === before,
    comparison_note: c.id === 'outside_group_row' ? 'Different scope: strict join rejects extras; upstream population selector may exclude extras without mutation.' :
      ['roster_unknown','roster_absent','requested_date_mismatch','requested_hash_mismatch','requested_population_mismatch',
       'issuer_explicit_null','issuer_connection_without_evidence'].includes(c.id) ? 'New /2 request inputs/options are not consumed by this /1 reader.' : null,
    acceptance_count_match: actual.ok === c.expected.ok && (!actual.ok || actual.selected_count === c.expected.selected_count) };
});
// Outer population and group rows have different scopes. groupRows must leave
// rows outside the group untouched, not accidentally send them to strict join.
const outside = { id: 'SYNTHETIC:DISPLAY:OUTSIDE', code: 'SYNTHETIC:OUTSIDE', issuer_id: null,
  score: { total: 93 }, rank: { official: 7, of: 504 } };
const outer = structuredClone(fixture.base); outer.join.qgv_rows.push(outside);
const before = JSON.stringify(outer); const outerResult = run(outer);
console.log(JSON.stringify({ consumer_sha: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  scope: 'Node classification.validate -> groupRowsWhy -> techScreen.joinRows -> evaluate; not DOM/browser',
  cases: results, acceptance_count_matches: results.filter(r => r.acceptance_count_match).length,
  full_population_extra_row: { group_selected_count: outerResult.selected_count, input_unchanged: JSON.stringify(outer) === before,
    outside_row_unchanged: JSON.stringify(outer.join.qgv_rows.at(-1)) === JSON.stringify(outside) } }, null, 2));
