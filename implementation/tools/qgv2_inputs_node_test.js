'use strict';
/* sec-qgv2.json -> QGV v2 engine input: the JS device path (SecQgv2.toInputs / Qgv2Inputs.fromInputs / QgvScores.compute with
   PlaybookEngine) == the Python twin qgv/qgv2_inputs.py (+ qgv_v2.score_universe), on the shared cases of
   tools/qgv2_inputs_parity.js: the fixtures, synthetic edge variants and, with QGV2_PARITY_REAL_FILE, a published file (read
   only). Converted records, engine company records and engine quote codes must be identical; engine results identical except
   the DCF reference_range (the engine vectors' 1e-9 tolerance, tools/qgv_v2_node_test.js). Quotes are SYNTHETIC test numbers;
   specs go to Python over stdin and nothing is written to disk. Python test: tests/test_qgv2_inputs.py. */
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path'), { spawnSync } = require('node:child_process');
const P = require('./qgv2_inputs_parity.js');
const ROOT = path.resolve(__dirname, '..'), W = path.join(ROOT, 'src/investment_system/product/web_assets');

function python(specs) {
  const p = spawnSync(process.env.PYTHON || 'python', [path.join(__dirname, 'qgv2_inputs_parity.py'), 'convert'],
    { input: JSON.stringify(specs), encoding: 'utf8', maxBuffer: 1 << 30, env: { ...process.env, PYTHONPATH: path.join(ROOT, 'src') } });
  assert.equal(p.status, 0, p.stderr && p.stderr.slice(-2000));
  return JSON.parse(p.stdout);
}
// JSON values compared strictly (keys, lengths, types); numbers exactly, or within 1e-9 under reference_range only.
function diff(a, b, at, out, tolerated) {
  if (typeof a === 'number' && typeof b === 'number') { if (a !== b && !(tolerated && Math.abs(a - b) <= Math.max(1e-9, Math.abs(b) * 1e-9))) out.push([at, a, b]); return out; }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') { if (a !== b) out.push([at, a, b]); return out; }
  if (Array.isArray(a) !== Array.isArray(b)) { out.push([at, 'TYPE']); return out; }
  if (Array.isArray(a)) { if (a.length !== b.length) out.push([at, 'LENGTH', a.length, b.length]); else a.forEach((x, i) => diff(x, b[i], at + '[' + i + ']', out, tolerated)); return out; }
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  if (JSON.stringify(ka) !== JSON.stringify(kb)) { out.push([at, 'KEYS']); return out; }
  for (const k of ka) diff(a[k], b[k], at + '.' + k, out, tolerated || k === 'reference_range');
  return out;
}

test('TARGET identities equal the device catalog mapping (watchlist.js)', () => {
  const DW = require(path.join(W, 'watchlist.js'));
  const ids = DW.identities({ schema: 'DEVICE_ACTUAL_CATALOG/1', instruments: P.TARGET_IDENTITIES.map((c) => ({ ticker: c.ticker, label: c.ticker })) });
  const pairs = (rows) => rows.map((c) => c.company_id + '=' + c.ticker).sort();
  assert.deepEqual(pairs(ids), pairs(P.TARGET_IDENTITIES));
});

const cases = P.cases();
test('cases cover the fixtures, the mapping branches and (when named) the published file', () => {
  const ids = cases.map((c) => c.id);
  for (const id of ['light_fixture', 'light_edges', 'light_calc_version', 'light_withdrawn', 'strict_base_valid', 'strict_calc_version_mixed_population_valid',
    'strict_target_withdrawn_valid', 'strict_universe_withdrawn_valid', 'strict_fixture_missing', 'strict_base_valid_stale_now']) assert.ok(ids.includes(id), id);
  assert.equal(new Set(ids).size, ids.length);
});

for (const spec of cases) {
  test('JS == Python twin: ' + spec.id, () => {
    const js = P.convert(spec), [py] = python([spec]);
    for (const part of ['inputs', 'page_identities', 'companies', 'engine_quote_codes']) assert.deepEqual(diff(js[part], py[part], part, [], false), [], spec.id + ' ' + part);
    assert.deepEqual(Object.keys(py.scores).sort(), spec.profiles.map((p) => p.id).sort());
    for (const [profile, rows] of Object.entries(js.scores)) {
      assert.deepEqual(Object.keys(rows).sort(), Object.keys(js.companies).sort());
      assert.deepEqual(diff(rows, py.scores[profile], profile, [], false), [], spec.id + ' ' + profile);
      for (const [code, r] of Object.entries(rows)) {   // factor, axis and total results: exactly equal
        const m = py.scores[profile][code];
        assert.deepStrictEqual([r.factors, r.axes, r.total, r.total_reason, r.flags], [m.factors, m.axes, m.total, m.total_reason, m.flags], spec.id + ' ' + profile + ' ' + code);
      }
    }
    if (spec.id.startsWith('real_')) console.log('# ' + spec.id + ': rows ' + Object.keys(js.inputs.records).length + ', engine companies ' + Object.keys(js.companies).length + ', profiles ' + spec.profiles.length + ', mismatches 0');
  });
}
