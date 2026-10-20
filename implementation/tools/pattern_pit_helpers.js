'use strict';
// Point-in-time test helpers shared by pattern node tests (§13.2). Mirror: investment_system/technical/pit_checks.py.
// `run(rawBars)` turns raw daily bars into transitions carrying known_at. Helpers only compare; no I/O.
function key(items) {
  const sort = v => Array.isArray(v) ? v.map(sort) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sort(v[k])])) : v;
  return JSON.stringify(sort(items));
}
function prefixViolations(run, rawBars, cutOf, start = 1) {
  const full = run(rawBars), bad = [];
  for (let t = start; t <= rawBars.length; t++) {
    const cut = cutOf(rawBars.slice(0, t)), expected = full.filter(x => cut !== null && x.known_at <= cut);
    if (key(run(rawBars.slice(0, t))) !== key(expected)) bad.push(t);
  }
  return bad;
}
function futureMutationViolations(run, rawBars, t, mutate, cutOf) {
  const cut = cutOf(rawBars.slice(0, t)), keep = list => list.filter(x => cut !== null && x.known_at <= cut);
  const changed = rawBars.slice(0, t).concat(rawBars.slice(t).map((b, n) => mutate(t + n, {...b})));
  return key(keep(run(rawBars))) === key(keep(run(changed))) ? [] : [t];
}
function pivotLagViolations(transitions, k) {
  return transitions.filter(x => x.object_kind === 'PIVOT' && x.known_index - x.anchor_index < k).map(x => x.object_id);
}
module.exports = {key, prefixViolations, futureMutationViolations, pivotLagViolations};
