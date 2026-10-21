'use strict';
// PatternEngine (pattern-engine.js) pivots: JS == Python reference vectors (synthetic only), pattern-rules/1 config copy and
// parameter hash, PIT prefix invariance / future mutation / pivot lag (§13.2), provisional tail, continuity judgement.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto'), vm = require('node:vm');
const W = path.join(__dirname, '../src/investment_system/product/web_assets'), SOURCE = path.join(W, 'pattern-engine.js');
const E = require(SOURCE), CB = require(path.join(W, 'chart-bars.js')), CFG = require(path.join(W, 'pattern-config-defaults.js'));
const PIT = require('./pattern_pit_helpers.js');
const JSON_RULES = JSON.parse(fs.readFileSync(path.join(__dirname, '../src/investment_system/technical/pattern_rules_v1.json'), 'utf8'));
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/pattern_engine_reference_v1.json'), 'utf8'));
const sha = text => crypto.createHash('sha256').update(text, 'ascii').digest('hex');
function rulesWith(params) {
  const rules = JSON.parse(JSON.stringify(CFG)); Object.assign(rules.params, params); rules.params_sha256 = sha(E.canonicalJson(rules.params)); return rules;
}
function seriesFor(i) { const daily = CB.normalize(i.history); return i.timeframe === 'D' ? daily : CB.weekly(daily, i.actions); }
function run(c) {
  const i = c.input, rules = i.params ? rulesWith(i.params) : CFG;
  if (c.operation === 'pivots') return E.runPivots(seriesFor(i), rules, i.actions);
  throw new Error(c.operation);
}
const vector = id => vectors.cases.find(c => c.id === id);

for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true); const before = JSON.stringify(c.input);
  assert.deepEqual(JSON.parse(JSON.stringify(run(c))), JSON.parse(c.expected_json));
  assert.equal(JSON.stringify(c.input), before, 'input not mutated');
});
test('device config copy equals pattern_rules_v1.json, is frozen, and its parameter hash is the canonical SHA-256', () => {
  assert.deepEqual(JSON.parse(JSON.stringify(CFG)), JSON_RULES);
  assert.equal(CFG.rule_version, 'pattern-rules/1'); assert.equal(CFG.status, 'RESEARCH_DEFAULT'); assert.equal(CFG.label_ko, '연구 기본값 · 투자 유용성 미검증');
  assert.ok(Object.isFrozen(CFG) && Object.isFrozen(CFG.params) && Object.isFrozen(CFG.params.PIVOT_K));
  assert.equal(sha(E.canonicalJson(CFG.params)), CFG.params_sha256);
  assert.equal(E.runMode(CFG), 'OFFICIAL'); assert.equal(E.runMode(JSON.parse(JSON.stringify(CFG))), 'USER_SETTINGS');
});
test('no probability, win rate, percentage or score field or wording', () => {
  const text = JSON.stringify(CFG) + vectors.cases.map(c => JSON.stringify(Object.keys(JSON.parse(c.expected_json))) + c.expected_json.replace(/"(object_id|superseded_by)":"[^"]*"/g, '')).join('');
  for (const word of ['probability', 'win_rate', 'winrate', 'score', 'confidence', '확률', '승률', '신뢰도', '%', '매수', '매도', 'buy', 'sell', 'order']) assert.ok(!text.toLowerCase().includes(word), word);
});

const daily = raw => CB.normalize({...vector('pivots_random_walk_provisional_tail').input.history, bars: raw});
const lastDay = raw => raw.length ? CB.normalize({...vector('pivots_random_walk_provisional_tail').input.history, bars: raw}).bars.at(-1).session_date : null;
const SPLIT_FREE = vector('pivots_zigzag_daily').input.actions;
function pivotRun(timeframe, actions = SPLIT_FREE) {
  return raw => { if (!raw.length) return []; const s = daily(raw); return E.runPivots(timeframe === 'D' ? s : CB.weekly(s, actions), CFG, actions).transitions; };
}
for (const id of ['pivots_zigzag_daily', 'pivots_random_walk_provisional_tail', 'pivots_superseded', 'pivots_missing_bar_in_window']) {
  test('PIT prefix invariance (P1) and pivot lag (P3): ' + id, () => {
    const raw = vector(id).input.history.bars;
    assert.deepEqual(PIT.prefixViolations(pivotRun('D'), raw, lastDay), []);
    assert.deepEqual(PIT.pivotLagViolations(pivotRun('D')(raw), 3), []);
  });
}
test('PIT prefix invariance on weekly bars built from daily prefixes (P1/P6)', () => {
  const raw = vector('pivots_zigzag_weekly').input.history.bars;
  assert.deepEqual(PIT.prefixViolations(pivotRun('W'), raw, lastDay, 40), []);
  assert.deepEqual(PIT.pivotLagViolations(pivotRun('W')(raw), 2), []);
});
test('PIT future mutation (P2): extreme later bars never change earlier transitions', () => {
  const raw = vector('pivots_random_walk_provisional_tail').input.history.bars.slice(0, -1);
  for (const t of [30, 77, 150, 220]) {
    const extreme = (i, b) => ({...b, open: 1, high: 9999, low: 0.5, close: i % 2 ? 9000 : 1, volume: 0});
    const missing = (i, b) => ({...b, open: null, high: null, low: null, close: null});
    assert.deepEqual(PIT.futureMutationViolations(pivotRun('D'), raw, t, extreme, lastDay), []);
    assert.deepEqual(PIT.futureMutationViolations(pivotRun('D'), raw, t, missing, lastDay), []);
  }
});
test('provisional tail bars never change pivot transitions', () => {
  const raw = vector('pivots_random_walk_provisional_tail').input.history.bars, done = raw.slice(0, -1);
  assert.deepEqual(pivotRun('D')(raw), pivotRun('D')(done));
  const spiked = done.concat([{...raw.at(-1), high: 9999, low: 0.5, session_status: 'UNKNOWN'}]);
  assert.deepEqual(pivotRun('D')(spiked), pivotRun('D')(done));
});
test('without split events every pivot is NOT_JUDGEABLE (PRICE_BASIS_CONTINUITY_UNCONFIRMED); lookup failure is distinct', () => {
  const none = run(vector('pivots_zigzag_not_provided'));
  assert.ok(none.transitions.length > 0);
  for (const t of none.transitions) assert.deepEqual(t.judgement, {state: 'NOT_JUDGEABLE', reason_codes: ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']});
  const failed = E.runPivots(seriesFor(vector('pivots_zigzag_daily').input), CFG, {status: 'LOOKUP_FAILED'});
  for (const t of failed.transitions) assert.deepEqual(t.judgement.reason_codes, ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_LOOKUP_FAILED']);
  for (const t of run(vector('pivots_zigzag_daily')).transitions) assert.equal(t.judgement.state, 'CONFIRMED');
});
test('split effective date bounds every pivot window and restarts ATR (prices untouched)', () => {
  const r = run(vector('pivots_split_segments')), [first, second] = r.segments;
  assert.equal(second[0], first[1] + 1);
  for (const t of r.transitions) assert.ok(t.anchor_index - 3 >= second[0] || t.known_index <= first[1]);
  const after = r.transitions.filter(t => t.anchor_index >= second[0]);
  assert.ok(after.length && after[0].anchor_index - second[0] >= 14, 'no pivot before ATR warm-up in the new segment');
});
test('tie rule and same-kind supersede are append-only', () => {
  const tie = run(vector('pivots_tie_and_alternation')).transitions;
  assert.equal(tie[0].anchor_index, 20); assert.ok(!tie.some(t => t.anchor_index === 22));
  const sup = run(vector('pivots_superseded')).transitions.map(t => [t.event, t.anchor_index, t.known_index]);
  assert.deepEqual(sup.slice(0, 3), [['PIVOT_CONFIRMED', 20, 23], ['SUPERSEDED', 20, 34], ['PIVOT_CONFIRMED', 31, 34]]);
});
test('pure module: no network or storage', () => {
  const ctx = {Intl, Date, fetch() { throw Error('IO'); }};
  Object.defineProperty(ctx, 'localStorage', {get() { throw Error('STORAGE'); }});
  for (const file of ['chart-indicators.js', 'chart-bars.js', 'pattern-config-defaults.js', 'pattern-engine.js']) vm.runInNewContext(fs.readFileSync(path.join(W, file), 'utf8'), ctx);
  const c = vector('pivots_zigzag_daily');
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.PatternEngine.runPivots(ctx.ChartBars.normalize(c.input.history), ctx.PatternConfigDefaults, c.input.actions))), JSON.parse(c.expected_json));
  const text = fs.readFileSync(SOURCE, 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB', 'document.', 'Date.now', 'new Date(']) assert.ok(!text.includes(word), word);
});
