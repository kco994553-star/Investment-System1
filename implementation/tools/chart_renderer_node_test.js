'use strict';
// Pure parts of the chart renderer adapter and workbench (P1-8/P1-9). Synthetic values only.
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const assets = path.join(__dirname, '../src/investment_system/product/web_assets');
const R = require(path.join(assets, 'chart-renderer.js')), W = require(path.join(assets, 'chart-workbench.js'));
let pass = 0, fail = 0;
function test(name, f) { try { f(); pass++; console.log('PASS ' + name); } catch (error) { fail++; console.log('FAIL ' + name + ' ' + (error && error.code || '')); } }
const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(path.join(assets, file))).digest('hex');
const bar = (time, o, extra = {}) => ({time, open: o, high: o + 2, low: o - 2, close: o + 1, volume: 10, status: 'COMPLETE', ...extra});

test('vendored renderer files match the reviewed 5.2.1 hashes', () => {
  assert.equal(R.LWC_VERSION, '5.2.1');
  assert.equal(sha256(R.LWC_FILE), 'e21cc5caa0226ef30bd8549c50b9ef926615f2a4ee6b4e486353477a55f598cf');
  assert.equal(sha256('lightweight-charts-5.2.1.LICENSE.txt'), '70c9d5382506dd184465425c08a99ad9bd6d9ac1313c252968ba0b585e5ef823');
  assert.equal(sha256('lightweight-charts-5.2.1.NOTICE.txt'), 'f76c6afab94884448f0426e30d6e9d555ca7247894cd3484e477d2f87513036e');
  const sri = 'sha384-' + crypto.createHash('sha384').update(fs.readFileSync(path.join(assets, R.LWC_FILE))).digest('base64');
  assert.equal(R.LWC_INTEGRITY, sri);
});
test('workbench shows the upstream NOTICE text verbatim', () => {
  const notice = fs.readFileSync(path.join(assets, 'lightweight-charts-5.2.1.NOTICE.txt'), 'utf8').trim().split('\n').join(' ');
  assert.ok(fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8').includes("'" + notice + "'"));
});
test('renderer code makes no network or storage call and keeps the logo off', () => {
  const code = fs.readFileSync(path.join(assets, 'chart-renderer.js'), 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'localStorage', 'indexedDB', 'sessionStorage', 'http://', 'https://']) assert.ok(!code.includes(word), word);
  assert.ok(code.includes('attributionLogo: false'));
  const bench = fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8');
  for (const word of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'indexedDB', 'sessionStorage']) assert.ok(!bench.includes(word), word);
  assert.deepEqual([...bench.matchAll(/https?:\/\/[^'"\s)]+/g)].map(m => m[0]).sort(), ['https://www.tradingview.com/', 'https://www.tradingview.com/']);
});
test('normalizeBars keeps missing values as gaps and marks provisional bars', () => {
  const out = R.normalizeBars([bar('2025-01-06', 10), bar('2025-01-07', 11, {volume: null}), bar('2025-01-08', 12, {open: null}), bar('2025-01-09', 13, {status: 'IN_PROGRESS'})]);
  assert.equal(out.length, 4);
  assert.equal(out[1].volume, null); assert.equal(out[1].ohlc, true);
  assert.equal(out[2].ohlc, false); assert.equal(out[2].close, null);
  assert.equal(out[3].complete, false); assert.equal(out[0].start, '2025-01-06'); assert.equal(out[0].end, '2025-01-06');
  assert.equal(R.normalizeBars([bar('2025-01-06', 10, {volume: 0})])[0].volume, 0);
});
test('normalizeBars rejects unordered dates, bad status and inverted spans', () => {
  for (const input of [[bar('2025-01-07', 1), bar('2025-01-06', 1)], [bar('2025-01-06', 1, {status: 'DONE'})], [bar('2025-01-06', 1, {start: '2025-01-09', end: '2025-01-06'})], [{...bar('2025-01-06', 1), time: '6/1/2025'}], 'x'])
    assert.throws(() => R.normalizeBars(input), /RENDER_INPUT_INVALID/);
  assert.throws(() => R.normalizeBars(Array.from({length: 1501}, (_, i) => bar(new Date(Date.UTC(2020, 0, 1) + i * 86400000).toISOString().slice(0, 10), 5))), /RENDER_INPUT_INVALID/);
});
test('inconsistent OHLC is drawn as a gap, never repaired', () => {
  const out = R.normalizeBars([{time: '2025-01-06', open: 10, high: 9, low: 8, close: 9.5, volume: 1, status: 'COMPLETE'}]);
  assert.equal(out[0].ohlc, false); assert.equal(out[0].open, null);
});
test('normalizeLines keeps only aligned lines on known panes', () => {
  const lines = R.normalizeLines([{id: 'A', pane: 'price', values: [1, null]}, {id: 'B', pane: 'other', values: [1, 2]}, {id: 'C', pane: 'rsi', values: [1]}, {id: 'D', pane: 'macd', type: 'histogram', values: [NaN, 2]}], 2);
  assert.deepEqual(lines.map(l => l.id), ['A', 'D']);
  assert.deepEqual(lines[1].values, [null, 2]); assert.equal(lines[1].type, 'histogram');
});
test('mapRange keeps the visible dates between daily and weekly bars', () => {
  const daily = R.normalizeBars(['2025-01-06', '2025-01-07', '2025-01-08', '2025-01-09', '2025-01-10', '2025-01-13', '2025-01-14', '2025-01-15', '2025-01-16', '2025-01-17', '2025-01-21', '2025-01-22'].map((d, i) => bar(d, 10 + i)));
  const weekly = R.normalizeBars([bar('2025-01-06', 10, {start: '2025-01-06', end: '2025-01-10'}), bar('2025-01-13', 10, {start: '2025-01-13', end: '2025-01-17'}), bar('2025-01-20', 10, {start: '2025-01-21', end: '2025-01-22', status: 'PROVISIONAL'})]);
  assert.deepEqual(R.mapRange(daily, weekly, {from: 2, to: 6}), {from: 0, to: 1});
  assert.deepEqual(R.mapRange(weekly, daily, {from: 0, to: 1}), {from: 0, to: 9});
  assert.deepEqual(R.mapRange(weekly, daily, {from: 1, to: 2}), {from: 5, to: 11});
  assert.deepEqual(R.mapRange(daily, weekly, {from: 10.4, to: 99}), {from: 2, to: 2});
  assert.equal(R.mapRange([], weekly, {from: 0, to: 1}), null);
});
test('measure reports price difference, percent, bars and calendar days only', () => {
  const bars = R.normalizeBars([bar('2025-01-06', 10), bar('2025-01-07', 11), bar('2025-01-10', 12)]);
  const m = R.measure(bars, {index: 2, price: 120}, {index: 0, price: 100});
  assert.equal(m.from.time, '2025-01-06'); assert.equal(m.to.time, '2025-01-10');
  assert.equal(m.diff, 20); assert.equal(m.percent, 20); assert.equal(m.bars, 2); assert.equal(m.days, 4);
  assert.deepEqual(Object.keys(m).sort(), ['bars', 'days', 'diff', 'from', 'percent', 'to']);
  assert.equal(R.measure(bars, {index: 0, price: 0}, {index: 1, price: 2}), null);
  assert.equal(R.measure(bars, {index: 0, price: 1}, {index: 9, price: 2}), null);
});
test('display settings store toggles only and reject unknown values', () => {
  const store = new Map(), storage = {getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, v)};
  assert.equal(W.readSettings(storage).indicators.SMA, true);
  assert.equal(W.writeSettings(storage, {mode: 'swing', renderer: 'svg', indicators: {SMA: false, EMA: true, BOLL: false, RSI: true, MACD: false, ATR: false}}), true);
  const saved = JSON.parse(store.get(W.SETTINGS_KEY));
  assert.deepEqual(Object.keys(saved).sort(), ['indicators', 'mode', 'renderer', 'schema']);
  const back = W.readSettings(storage); assert.equal(back.mode, 'swing'); assert.equal(back.renderer, 'svg'); assert.equal(back.indicators.RSI, true);
  store.set(W.SETTINGS_KEY, JSON.stringify({schema: W.SETTINGS_SCHEMA, mode: 'auto', renderer: 'canvas', indicators: {RSI: 'yes', price: 1}}));
  const bad = W.readSettings(storage); assert.equal(bad.mode, 'long'); assert.equal(bad.renderer, 'lwc'); assert.equal(bad.indicators.RSI, false); assert.equal('price' in bad.indicators, false);
  assert.equal(W.readSettings({getItem() { throw new Error('blocked'); }}).mode, 'long');
  assert.equal(W.writeSettings({setItem() { throw new Error('blocked'); }}, back), false);
});
test('daily view uses the provider session label, else the exchange-local date', () => {
  const out = W.dailyView([{timestamp: 1736173800, open: 1, high: 1, low: 1, close: 1, volume: 1, session_status: 'COMPLETE'}, {timestamp: 1736260200, session_date: '2025-01-07', open: 1, high: 1, low: 1, close: 1, volume: 1, session_status: 'UNKNOWN'}], 'America/New_York');
  assert.deepEqual(out.map(x => [x.time, x.status]), [['2025-01-06', 'COMPLETE'], ['2025-01-07', 'UNKNOWN']]);
});
test('weekly bars come only from ChartBars; missing module is a coded state', () => {
  const data = {symbol: 'SYNTH', timezone: 'UTC', bars: []};
  assert.deepEqual(W.weeklyView({}, data), {code: 'WEEKLY_BARS_MODULE_PENDING', bars: null});
  assert.equal(W.weeklyView({ChartBars: {normalize: x => x, weekly() { throw new Error('x'); }}}, data).code, 'WEEKLY_BARS_FAILED');
  assert.equal(W.weeklyView({ChartBars: {normalize: x => x, weekly: () => ({bars: []})}}, data).code, 'WEEKLY_BARS_FAILED');
  let seen = null;
  const ok = W.weeklyView({ChartBars: {normalize: h => { seen = h; return {timeframe: 'D'}; }, weekly: () => ({bars: [{week_start: '2025-01-06', first_session: '2025-01-06', last_session: '2025-01-10', open: 1, high: 2, low: 1, close: 2, volume: 3, state: 'COMPLETE'}, {week_start: '2025-01-13', first_session: '2025-01-13', last_session: '2025-01-14', open: 1, high: 2, low: 1, close: 2, volume: null, state: 'PROVISIONAL'}]})}}, data);
  assert.equal(seen.schema, 'private-history/1'); assert.equal(seen.basis, 'RAW_CLOSE'); assert.equal(seen.interval, '1d');
  assert.equal(ok.code, 'READY'); assert.deepEqual(ok.bars.map(b => [b.time, b.start, b.end, b.status]), [['2025-01-06', '2025-01-06', '2025-01-10', 'COMPLETE'], ['2025-01-13', '2025-01-13', '2025-01-14', 'PROVISIONAL']]);
  assert.ok(!/reduce\(|groupBy|isoWeek|getUTCDay\(\)\s*===\s*5/.test(fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8').split('function syntheticHistory')[0]));
  assert.deepEqual(W.continuityCodes({}, []), ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']);
});
test('with the lane B1 chart-bars.js present, weekly W1 bars and continuity codes flow through unchanged', () => {
  const file = path.join(assets, 'chart-bars.js');
  if (!fs.existsSync(file)) { console.log('NOTE chart-bars.js not on this branch; integration check skipped'); return; }
  const ChartBars = require(file), synth = W.syntheticHistory(), view = {ChartBars};
  const weekly = W.weeklyView(view, synth);
  assert.equal(weekly.code, 'READY');
  const bars = R.normalizeBars(weekly.bars), daily = R.normalizeBars(W.dailyView(synth.bars, synth.timezone));
  assert.equal(bars.at(-1).complete, false); assert.ok(bars.length >= 60 && bars.length <= 70);
  assert.equal(bars[0].start, daily[0].start); assert.equal(bars.at(-1).end, daily.at(-1).end);
  assert.deepEqual(W.continuityCodes(view, daily).slice(0, 1), ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']);
});
test('synthetic preview is deterministic, labelled and never a real symbol', () => {
  const a = W.syntheticHistory(), b = W.syntheticHistory();
  assert.deepEqual(a.bars, b.bars); assert.equal(a.symbol, 'SYNTH'); assert.equal(a.provider, 'SYNTHETIC');
  assert.equal(a.bars.length, 320); assert.equal(a.bars.at(-1).session_status, 'IN_PROGRESS'); assert.equal(a.bars[60].volume, null); assert.equal(a.bars[120].close, null);
  assert.equal(W.SYNTHETIC_LABEL[0], '합성 자료 · 미리보기 · 실데이터 검증 아님');
  assert.doesNotThrow(() => R.normalizeBars(W.dailyView(a.bars, a.timezone)));
});
test('workbench wording has no buy/sell, probability, win-rate or score terms', () => {
  const text = fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8') + fs.readFileSync(path.join(assets, 'chart-renderer.js'), 'utf8');
  for (const word of ['매수', '매도', '확률', '승률', '점수', '신뢰도', 'probability', 'win rate', 'win-rate', 'Buy', 'Sell']) assert.ok(!text.includes(word), word);
});
console.log('COUNTS pass=' + pass + ' fail=' + fail);
if (fail) process.exitCode = 1;
