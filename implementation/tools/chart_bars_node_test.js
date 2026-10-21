'use strict';
// ChartBars (chart-bars.js): JS == Python reference vectors (synthetic only), W1 weekly rule, missing/zero volume,
// price-basis continuity without re-adjustment, merge revisions, purity (no network/storage, input not mutated).
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const W = path.join(__dirname, '../src/investment_system/product/web_assets'), SOURCE = path.join(W, 'chart-bars.js');
const CB = require(SOURCE);
const vectors = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/chart_bars_reference_v1.json'), 'utf8'));

function run(c) {
  const i = c.input;
  switch (c.operation) {
    case 'normalize': return CB.normalize(i.history);
    case 'weekly': return CB.weekly(CB.normalize(i.history), i.actions);
    case 'continuity': return CB.continuity(i.actions, i.start, i.end);
    case 'merge': return CB.merge(CB.normalize(i.previous), CB.normalize(i.incoming));
    case 'session_set_mismatch': return CB.sessionSetMismatch(CB.normalize(i.history), i.store_dates);
    default: throw new Error(c.operation);
  }
}
assert.ok(vectors.cases.length >= 20);
for (const c of vectors.cases) test('python reference vector ' + c.id, () => {
  assert.equal(c.synthetic, true); const before = JSON.stringify(c.input);
  assert.deepEqual(JSON.parse(JSON.stringify(run(c))), JSON.parse(c.expected_json));
  assert.equal(JSON.stringify(c.input), before, 'input not mutated');
});
const vector = id => vectors.cases.find(c => c.id === id);
test('real zero volume stays 0 and missing volume stays null with a reason', () => {
  const s = run(vector('normalize_codes'));
  assert.equal(s.bars[2].volume, 0); assert.equal(s.bars[2].volume_state, 'REPORTED'); assert.deepEqual(s.bars[2].codes, []);
  assert.equal(s.bars[3].volume, null); assert.equal(s.bars[3].volume_state, 'MISSING'); assert.deepEqual(s.bars[3].codes, ['VOLUME_MISSING']);
  assert.equal(s.bars[4].ohlc, 'MISSING'); assert.equal(s.bars[4].close, null);
  assert.equal(s.bars[5].ohlc, 'MISSING'); assert.ok(s.bars[5].codes.includes('OHLC_INCONSISTENT')); assert.equal(s.bars[5].open, 30, 'raw value kept, never repaired');
  assert.deepEqual(s.bars[6].codes, ['NON_COMPLETE_IN_HISTORY', 'PROVISIONAL_SESSION']); assert.equal(s.bars[11].state, 'PROVISIONAL');
});
test('weekly W1: Friday holiday completes at next session; missing OHLC/volume never partial', () => {
  const w = run(vector('weekly_w1_holiday_missing')).bars, by = d => w.find(b => b.week_start === d);
  assert.equal(by('2030-01-07').known_at, '2030-01-11');
  assert.equal(by('2030-01-14').known_at, '2030-01-21'); assert.equal(by('2030-01-14').session_count, 4);
  assert.equal(by('2030-01-28').open, null); assert.ok(by('2030-01-28').codes.includes('OHLC_MISSING_IN_WEEK')); assert.equal(by('2030-01-28').volume, 500);
  assert.equal(by('2030-02-04').volume, null); assert.equal(by('2030-02-04').high, 52);
  assert.equal(by('2030-02-11').volume, 300, 'a real zero counts as zero'); assert.equal(by('2030-02-11').state, 'PROVISIONAL');
  assert.equal(run(vector('weekly_tail_not_closed')).bars.at(-1).state, 'PROVISIONAL');
  assert.equal(run(vector('weekly_friday_in_progress')).bars.at(-1).state, 'PROVISIONAL');
  assert.equal(run(vector('weekly_provisional_inside')).bars[1].state, 'PROVISIONAL');
});
test('continuity: no events / lookup failed / invalid are distinct and never judgeable; split crossing is CORPORATE_ACTION_IN_WINDOW', () => {
  assert.deepEqual(run(vector('continuity_not_provided')).reason_codes, ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']);
  assert.deepEqual(run(vector('continuity_lookup_failed')).reason_codes, ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_LOOKUP_FAILED']);
  assert.deepEqual(run(vector('continuity_invalid_kind')).reason_codes, ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_INVALID']);
  assert.equal(run(vector('continuity_no_events')).state, 'CONFIRMED');
  assert.equal(run(vector('continuity_dividend_only_window')).state, 'CONFIRMED');
  assert.deepEqual(run(vector('continuity_split_in_window')).reason_codes, ['CORPORATE_ACTION_IN_WINDOW']);
  assert.equal(run(vector('continuity_starts_on_split')).state, 'CONFIRMED');
  assert.equal(run(vector('continuity_coverage_gap')).state, 'NOT_JUDGEABLE');
});
test('a split never changes any price value (no re-adjustment)', () => {
  const c = vector('weekly_split_straddles_week'), daily = CB.normalize(c.input.history), weekly = CB.weekly(daily, c.input.actions);
  const plain = CB.weekly(CB.normalize(c.input.history), null);
  weekly.bars.forEach((b, n) => { if (!b.codes.includes('CORPORATE_ACTION_IN_BAR')) for (const k of ['open', 'high', 'low', 'close', 'volume']) assert.equal(b[k], plain.bars[n][k]); });
  assert.equal(weekly.bars[1].close, null); assert.ok(weekly.bars[1].codes.includes('CORPORATE_ACTION_IN_BAR'));
});
test('merge keeps earlier complete values and records PRICE_REVISED', () => {
  const r = run(vector('merge_revision'));
  assert.deepEqual(r.revised, ['2030-01-10']);
  const bar = r.series.bars.find(b => b.session_date === '2030-01-10'); assert.equal(bar.close, 10); assert.ok(bar.codes.includes('PRICE_REVISED'));
  assert.equal(r.series.bars.find(b => b.session_date === '2030-01-14').volume, 101); assert.ok(r.series.quality.codes.includes('PROVIDER_MIXED'));
});
test('invalid input fails closed with fixed codes only', () => {
  assert.throws(() => CB.normalize({schema: 'x'}), /CHART_BARS_INPUT_INVALID/);
  const h = JSON.parse(JSON.stringify(vector('normalize_codes').input.history)); h.bars[1].timestamp = h.bars[0].timestamp;
  assert.throws(() => CB.normalize(h), /^Error: CHART_BARS_INPUT_INVALID$/);
  const n = JSON.parse(JSON.stringify(vector('normalize_codes').input.history)); n.bars[0].volume = -1;
  assert.throws(() => CB.normalize(n), /CHART_BARS_INPUT_INVALID/);
});
test('pure module: runs without network or storage globals', () => {
  const context = {Intl, Date, fetch() { throw Error('IO'); }};
  Object.defineProperty(context, 'localStorage', {get() { throw Error('STORAGE'); }});
  vm.runInNewContext(fs.readFileSync(SOURCE, 'utf8'), context);
  assert.equal(context.ChartBars.normalize(vector('normalize_codes').input.history).schema, 'chart-bars/1');
  const text = fs.readFileSync(SOURCE, 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'indexedDB', 'document.']) assert.ok(!text.includes(word), word);
});
