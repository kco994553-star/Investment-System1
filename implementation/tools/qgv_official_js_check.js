'use strict';
/* JS twin cross-check of the central QGV publication (design D-CV12): the SAME engine records and quotes the Python publisher
   scored are piped in on stdin ({companies, quotes, preset, gate}), web_assets/qgv-v2.js scoreUniverse runs on them, and only
   the public projection (factor score/reason/basis, axes, weights, type weights, gate, flags, total) goes back on stdout to the
   Python process that spawned it. Prices arrive through the pipe only: nothing is written, logged or kept. Errors: a fixed code
   on stderr, exit 1. */
const path = require('node:path');
const V2 = require(path.join(__dirname, '../src/investment_system/product/web_assets/qgv-v2.js'));

const FACTOR_KEYS = ['score', 'reason', 'basis'], AXIS_KEYS = ['score', 'state', 'weight_available', 'factors_available', 'reason'];
const pick = (o, keys) => Object.fromEntries(keys.map((k) => [k, o[k] === undefined ? null : o[k]]));
function projection(r) {
  const factors = {}, axes = {};
  for (const k of V2.FACTORS) factors[k] = pick(r.factors[k], FACTOR_KEYS);
  for (const a of V2.PILLARS) axes[a] = pick(r.axes[a], AXIS_KEYS);
  return { factors, axes, weights: r.weights, type_weights: r.type_weights, type_reason: r.type_reason, selected_types: [...r.selected_types],
    q_industry_percentile: r.q_industry_percentile, value_trap_gate: r.value_trap_gate, v_excluded: r.v_excluded, flags: [...r.flags],
    total: r.total, total_reason: r.total_reason };
}
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (c) => { input += c; });
process.stdin.on('end', () => {
  try {
    const spec = JSON.parse(input);
    input = '';
    const result = V2.scoreUniverse(spec.companies, spec.quotes, { preset: spec.preset, gate: spec.gate });
    const out = {};
    for (const code of Object.keys(result).sort()) out[code] = projection(result[code]);
    process.stdout.write(JSON.stringify(out));
  } catch (_) {
    process.stderr.write('QGV_OFFICIAL_JS_CHECK_FAILED\n');
    process.exitCode = 1;
  }
});
