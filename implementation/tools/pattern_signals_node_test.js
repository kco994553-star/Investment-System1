'use strict';
// PatternEngine.run / PatternHistory (pattern-engine.js, pattern-history.js): JS == Python vectors for every TA_PREP §6 case
// (B1-B13, D1-D7, P4-P7; synthetic only), PIT prefix invariance and future mutation on full runs (P1/P2), mirrored cases,
// provisional preview (B3), official history append-only / dedupe / DATA_REVISION / version and user-settings separation.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto'), vm = require('node:vm');
const W = path.join(__dirname, '../src/investment_system/product/web_assets');
const E = require(path.join(W, 'pattern-engine.js')), CB = require(path.join(W, 'chart-bars.js')), CFG = require(path.join(W, 'pattern-config-defaults.js'));
const H = require(path.join(W, 'pattern-history.js')), PIT = require('./pattern_pit_helpers.js');
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/pattern_signals_reference_v1.json'), 'utf8'));
const vector = id => vectors.cases.find(c => c.id === id);
const sha = text => crypto.createHash('sha256').update(text, 'ascii').digest('hex');
function rulesWith(params) { const r = JSON.parse(JSON.stringify(CFG)); Object.assign(r.params, params); r.params_sha256 = sha(E.canonicalJson(r.params)); return r; }
function runHistory(h, timeframe, actions, rules = CFG) { const d = CB.normalize(h); return E.run(timeframe === 'D' ? d : CB.weekly(d, actions), rules, actions); }
function refused(fn) { try { fn(); return 'ACCEPTED'; } catch (error) { return error.message; } }
const strip = records => records.map(r => { const {seq, computed_at, ...rest} = r; return rest; });
function historySteps(i) { // mirror of tools/pattern_reference.py history_steps
  const daily = CB.normalize(i.history), full = E.run(daily, CFG, i.actions), log = [];
  const hist = H.create(full.symbol, full.timeframe, full.rule_version, full.params_sha256);
  for (const n of [30, 43, 44, 45, daily.bars.length]) log.push(['prefix', n, hist.append(E.run(CB.normalize({...i.history, bars: i.history.bars.slice(0, n)}), CFG, i.actions), 'T' + String(n).padStart(3, '0'))]);
  log.push(['repeat', hist.append(full, 'T999')]);
  log.push(['user_settings', refused(() => hist.append(E.run(daily, rulesWith({SWING_MIN_ATR: 2}), i.actions), 'TX'))]);
  log.push(['version_mixed', refused(() => hist.append({...full, rule_version: 'pattern-rules/2'}, 'TX'))]);
  const once = H.create(full.symbol, full.timeframe, full.rule_version, full.params_sha256);
  log.push(['full_once', once.append(full, 'T999')]);
  log.push(['prefix_order_equals_full_once', JSON.stringify(strip(once.records())) === JSON.stringify(strip(hist.records()))]);
  const na = H.create(full.symbol, full.timeframe, full.rule_version, full.params_sha256);
  log.push(['no_split_events', na.append(E.run(CB.normalize(i.not_judgeable_history), CFG, null), 'T999'), na.records().length]);
  const partial = H.create(full.symbol, full.timeframe, full.rule_version, full.params_sha256);
  partial.append({...full, transitions: full.transitions.filter(t => t.pattern !== 'BOX_BREAKOUT_UP')}, 'T999');
  log.push(['late_object', partial.append(full, 'T1000')]);
  const incoming = CB.normalize(i.revised_incoming), held = CB.merge(daily, incoming), view = CB.merge(daily, incoming, 'INCOMING');
  const official = E.run(held.series, CFG, i.actions), revised = E.run(view.series, CFG, i.actions);
  log.push(['revised_dates', held.revised]);
  log.push(['revision', hist.recordRevision(official, revised, held.revised, incoming.bars[incoming.bars.length - 1].session_date, 'T1000')]);
  log.push(['after_revision_append', hist.append(official, 'T1001')]);
  return {log, records: hist.records()};
}
function run(c) {
  const i = c.input;
  if (c.operation === 'run') return runHistory(i.history, i.timeframe, i.actions);
  if (c.operation === 'preview') { const s = CB.normalize(i.history); return E.preview(s, E.run(s, CFG, i.actions)); }
  if (c.operation === 'history') return historySteps(i);
  throw new Error(c.operation);
}
for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true); const before = JSON.stringify(c.input);
  assert.deepEqual(JSON.parse(JSON.stringify(run(c))), JSON.parse(c.expected_json));
  assert.equal(JSON.stringify(c.input), before, 'input not mutated');
});

const out = id => run(vector(id)), ofPattern = (r, pattern) => r.transitions.filter(t => t.pattern === pattern).map(t => [t.event, t.known_index]);
test('B1/B2/B4/B5/B6/B7 box state machine', () => {
  assert.deepEqual(ofPattern(out('B1_box_breakout_confirmed'), 'BOX_BREAKOUT_UP'), [['FORMED', 42], ['CONFIRMED', 44], ['OBSERVATION_ENDED', 49]]);
  assert.deepEqual(ofPattern(out('B2_close_equal_to_level_is_not_confirmed'), 'BOX_BREAKOUT_UP'), [['FORMED', 42]]);
  assert.deepEqual(ofPattern(out('B4_failed_within_fail_window'), 'BOX_BREAKOUT_UP'), [['FORMED', 42], ['CONFIRMED', 44], ['FAILED', 45]]);
  assert.deepEqual(ofPattern(out('B5_return_after_fail_window'), 'BOX_BREAKOUT_UP'), [['FORMED', 42], ['CONFIRMED', 44], ['OBSERVATION_ENDED', 49]]);
  const b6 = out('B6_breakdown_first_invalidates_breakout');
  assert.deepEqual(ofPattern(b6, 'BOX_BREAKOUT_UP'), [['FORMED', 42], ['INVALIDATED', 44]]); assert.deepEqual(ofPattern(b6, 'BOX_BREAKDOWN').slice(0, 2), [['FORMED', 42], ['CONFIRMED', 44]]);
  assert.deepEqual(ofPattern(out('B7_expired_at_box_max_bars'), 'BOX_BREAKOUT_UP').slice(0, 2), [['FORMED', 42], ['EXPIRED', 144]]);
});
test('B3 provisional bar: no history change, preview note only', () => {
  const r = out('B3_provisional_bar_only');
  assert.deepEqual(ofPattern(r, 'BOX_BREAKOUT_UP'), [['FORMED', 42]]);
  assert.deepEqual(out('B3_preview_note').map(x => x.note_ko), ['잠정 봉 기준 조건 충족 · 확정 아님', '잠정 봉 기준 조건 충족 · 확정 아님']);
});
test('B8 each formation condition broken alone gives no box', () => {
  for (const id of ['B8_1_length_below_min', 'B8_2_one_upper_touch', 'B8_3_one_lower_touch', 'B8_4_close_outside_box', 'B8_5_too_shallow', 'B8_5b_too_deep']) {
    const r = out(id);
    assert.ok(r.transitions.filter(t => t.object_kind === 'PIVOT' && t.event === 'PIVOT_CONFIRMED').length >= 4, id + ' has pivots');
    assert.equal(r.transitions.filter(t => ['BOX_BREAKOUT_UP', 'BOX_BREAKDOWN', 'BOX'].includes(t.pattern)).length, 0, id);
  }
  assert.deepEqual(ofPattern(out('B8_1b_length_at_min_forms'), 'BOX_BREAKOUT_UP'), [['FORMED', 36]]);
});
test('B9 levels fixed at formation ATR; B10 gap; B11 volume NA without blocking', () => {
  const b9 = runHistory(vector('B9_levels_fixed_when_atr_changes').input.history, 'D', vector('B1_box_breakout_confirmed').input.actions);
  const formed = b9.transitions.find(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'FORMED');
  assert.equal(formed.detail.confirm_level, out('B1_box_breakout_confirmed').transitions.find(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'FORMED').detail.confirm_level);
  const ctx = E.prepare(CB.normalize(vector('B9_levels_fixed_when_atr_changes').input.history), CFG, vector('B1_box_breakout_confirmed').input.actions);
  assert.ok(ctx.atr[46] > 2 * formed.detail.atr && ctx.bars[46].close < formed.detail.upper + 0.25 * ctx.atr[46], 'a moving level would not confirm');
  assert.deepEqual(ofPattern(b9, 'BOX_BREAKOUT_UP').slice(0, 2), [['FORMED', 42], ['CONFIRMED', 46]]);
  assert.equal(out('B10_gap_breakout').transitions.find(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'CONFIRMED').detail.gap, true);
  assert.equal(out('B1_box_breakout_confirmed').transitions.find(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'CONFIRMED').detail.gap, false);
  assert.deepEqual(out('B11_confirm_bar_volume_missing').transitions.find(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'CONFIRMED').detail.volume, {state: 'NOT_AVAILABLE', reason_code: 'VOLUME_MISSING'});
});
test('B12 missing bars and B13 corporate actions are NOT_JUDGEABLE with reasons', () => {
  assert.deepEqual(out('B12_missing_bar_in_box_window').transitions.filter(t => t.pattern === 'BOX').map(t => [t.event, t.detail.reason_codes]), [['NOT_JUDGEABLE', ['MISSING_BARS_IN_WINDOW']]]);
  assert.deepEqual(ofPattern(out('B12b_missing_bar_while_formed'), 'BOX_BREAKOUT_UP'), [['FORMED', 42], ['NOT_JUDGEABLE', 43]]);
  const split = out('B13_split_crosses_live_window').transitions.filter(t => t.known_index === 45 && t.object_kind !== 'PIVOT');
  assert.ok(split.length >= 2 && split.every(t => t.event === 'NOT_JUDGEABLE' && t.detail.reason_codes[0] === 'CORPORATE_ACTION_IN_WINDOW' && t.judgement.reason_codes[0] === 'CORPORATE_ACTION_IN_WINDOW'));
  for (const [id, sub] of [['B13b_split_lookup_failed', 'CORPORATE_ACTION_LOOKUP_FAILED'], ['B13c_no_split_events', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']])
    for (const t of out(id).transitions) assert.deepEqual(t.judgement, {state: 'NOT_JUDGEABLE', reason_codes: ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', sub]});
});
test('D1-D7 double bottom state machine and P1 selection', () => {
  assert.deepEqual(ofPattern(out('D1_double_bottom_confirmed'), 'DOUBLE_BOTTOM'), [['FORMED', 37], ['CONFIRMED', 39], ['OBSERVATION_ENDED', 44]]);
  assert.deepEqual(ofPattern(out('D2_double_bottom_failed'), 'DOUBLE_BOTTOM'), [['FORMED', 37], ['CONFIRMED', 39], ['FAILED', 40]]);
  assert.deepEqual(ofPattern(out('D3_double_bottom_invalidated'), 'DOUBLE_BOTTOM'), [['FORMED', 37], ['INVALIDATED', 39]]);
  assert.deepEqual(ofPattern(out('D4_double_bottom_expired'), 'DOUBLE_BOTTOM'), [['FORMED', 37], ['EXPIRED', 48]]);
  assert.deepEqual(ofPattern(out('D5_neckline_passed_before_known'), 'DOUBLE_BOTTOM'), []);
  const d6 = out('D6_nearest_p1_only').transitions.filter(t => t.pattern === 'DOUBLE_BOTTOM' && t.event === 'FORMED');
  assert.deepEqual(d6.map(t => [t.detail.p1_at, t.detail.p2_at]), [['2030-02-08', '2030-02-22'], ['2030-02-22', '2030-03-08']]);
  assert.deepEqual(ofPattern(out('D7_separation_min_minus_one'), 'DOUBLE_BOTTOM'), []);
  assert.deepEqual(ofPattern(out('D7b_separation_max_plus_one'), 'DOUBLE_BOTTOM'), []);
  assert.equal(out('D7c_separation_max_forms').transitions.find(t => t.pattern === 'DOUBLE_BOTTOM').detail.separation_bars, 120);
});
test('mirrored cases swap the pattern and keep the timing', () => {
  const swap = {BOX_BREAKOUT_UP: 'BOX_BREAKDOWN', BOX_BREAKDOWN: 'BOX_BREAKOUT_UP', DOUBLE_BOTTOM: 'DOUBLE_TOP', DOUBLE_TOP: 'DOUBLE_BOTTOM'};
  const key = r => r.transitions.filter(t => swap[t.pattern]).map(t => [t.pattern, t.event, t.known_index]).sort().join(';');
  const flipped = r => r.transitions.filter(t => swap[t.pattern]).map(t => [swap[t.pattern], t.event, t.known_index]).sort().join(';');
  assert.equal(key(out('B1_mirror_breakdown')), flipped(out('B1_box_breakout_confirmed')));
  assert.equal(key(out('B4_mirror_breakdown_failed')), flipped(out('B4_failed_within_fail_window')));
  assert.equal(key(out('D1_mirror_double_top')), flipped(out('D1_double_bottom_confirmed')));
});
test('P6 weekly patterns use W1 known_at dates', () => {
  const r = out('P6_weekly_patterns'), daily = CB.normalize(vector('P6_weekly_patterns').input.history), weekly = CB.weekly(daily, vector('P6_weekly_patterns').input.actions);
  assert.ok(r.transitions.some(t => t.pattern === 'BOX_BREAKOUT_UP' && t.event === 'CONFIRMED'));
  for (const t of r.transitions) assert.equal(t.known_at, weekly.bars[t.known_index].known_at);
});
const lastDay = raw => (raw.length ? CB.normalize({...vector('B1_box_breakout_confirmed').input.history, bars: raw}).bars.at(-1).session_date : null);
function fullRun(timeframe, actions) {
  return raw => { if (!raw.length) return []; const s = CB.normalize({...vector('B1_box_breakout_confirmed').input.history, bars: raw}); return E.run(timeframe === 'D' ? s : CB.weekly(s, actions), CFG, actions).transitions; };
}
for (const id of ['B1_box_breakout_confirmed', 'B6_breakdown_first_invalidates_breakout', 'B12_missing_bar_in_box_window', 'B13_split_crosses_live_window', 'D6_nearest_p1_only', 'random_walk_3']) {
  test('P1 prefix invariance and P3 pivot lag on full runs: ' + id, () => {
    const c = vector(id), raw = c.input.history.bars;
    assert.deepEqual(PIT.prefixViolations(fullRun('D', c.input.actions), raw, lastDay), []);
    assert.deepEqual(PIT.pivotLagViolations(fullRun('D', c.input.actions)(raw), 3), []);
  });
}
test('P1 prefix invariance on weekly full runs', () => {
  const c = vector('P6_weekly_patterns');
  assert.deepEqual(PIT.prefixViolations(fullRun('W', c.input.actions), c.input.history.bars, lastDay, 150), []);
});
test('P2 future mutation never changes known transitions', () => {
  const c = vector('random_walk_3'), raw = c.input.history.bars;
  for (const t of [50, 120, 180]) {
    assert.deepEqual(PIT.futureMutationViolations(fullRun('D', c.input.actions), raw, t, (i, b) => ({...b, open: 1, high: 9999, low: 0.5, close: i % 2 ? 9000 : 1, volume: 0}), lastDay), []);
    assert.deepEqual(PIT.futureMutationViolations(fullRun('D', c.input.actions), raw, t, (i, b) => ({...b, open: null, high: null, low: null, close: null}), lastDay), []);
  }
});
test('history: user-settings runs and user drawings never alter the official history', () => {
  const c = vector('B1_box_breakout_confirmed'), d = CB.normalize(c.input.history), full = E.run(d, CFG, c.input.actions);
  const book = H.createBook(); book.append(full, 'T1'); const before = JSON.stringify(book.historyFor(full).records());
  assert.throws(() => book.append(E.run(d, rulesWith({BREAK_BUFFER_ATR: 0}), c.input.actions), 'T2'), /HISTORY_USER_SETTINGS_REFUSED/);
  const userCopy = JSON.parse(JSON.stringify(full.transitions[0])); userCopy.detail.price = 1; // a dragged user copy is a separate object
  assert.equal(JSON.stringify(book.historyFor(full).records()), before);
  assert.ok(Object.isFrozen(book.historyFor(full).records()[0]) && Object.isFrozen(book.historyFor(full).records()[0].detail));
  const v2 = {...full, params_sha256: 'f'.repeat(64)}; book.historyFor(v2);
  assert.equal(book.keys().length, 2, 'versions are kept apart');
});
test('pure modules: no network or storage', () => {
  const ctx = {Intl, Date, fetch() { throw Error('IO'); }};
  Object.defineProperty(ctx, 'localStorage', {get() { throw Error('STORAGE'); }});
  for (const file of ['chart-indicators.js', 'chart-bars.js', 'pattern-config-defaults.js', 'pattern-engine.js', 'pattern-history.js']) vm.runInNewContext(fs.readFileSync(path.join(W, file), 'utf8'), ctx);
  const c = vector('D1_double_bottom_confirmed');
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.PatternEngine.run(ctx.ChartBars.normalize(c.input.history), ctx.PatternConfigDefaults, c.input.actions))), JSON.parse(c.expected_json));
  for (const file of ['pattern-engine.js', 'pattern-history.js']) {
    const text = fs.readFileSync(path.join(W, file), 'utf8');
    for (const word of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB', 'document.', 'Date.now', 'new Date(']) assert.ok(!text.includes(word), file + ' ' + word);
  }
  const all = vectors.cases.map(x => x.expected_json.replace(/"(object_id|superseded_by|box_id)":"[^"]*"/g, '')).join('').toLowerCase();
  for (const word of ['probability', 'win_rate', 'score', 'confidence', '확률', '승률', '%', 'buy', 'sell']) assert.ok(!all.includes(word), word);
});
