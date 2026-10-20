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
  assert.deepEqual(Object.keys(saved).sort(), ['indicators', 'mode', 'patterns', 'renderer', 'schema']);
  assert.deepEqual(saved.patterns, {ZONES: true, BOX: true, DOUBLE: true});
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

test('pattern helpers read engine output without detecting anything themselves', () => {
  const code = fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8');
  for (const word of ['function pivots', 'function atr', 'formBox', 'formDouble', 'recluster', 'ResearchIndicators.calculate(series']) assert.ok(!code.includes(word), word);
  const Defaults = require(path.join(assets, 'pattern-config-defaults.js'));
  const {params, diff} = W.applyChanges(Defaults.params, {PIVOT_K: 5, BOX_MAX_BARS: 60, 'BOX_HEIGHT_ATR.min': 3, ZONE_TOL_ATR: 0.5}, 'D');
  assert.equal(params.PIVOT_K.D, 5); assert.equal(params.PIVOT_K.W, Defaults.params.PIVOT_K.W); assert.equal(params.DB_SEP_MAX.D, 60); assert.equal(params.BOX_HEIGHT_ATR.min, 3);
  assert.deepEqual(diff.map(x => x.name), ['PIVOT_K', 'BOX_MAX_BARS', 'BOX_HEIGHT_ATR.min']);
  assert.equal(Defaults.params.PIVOT_K.D, 3);
  assert.throws(() => W.applyChanges(Defaults.params, {PIVOT_K: 4}, 'D'), /PATTERN_SETTING_OUT_OF_GRID/);
  assert.deepEqual(W.minBars(Defaults.params, 'D'), [['ATR14', 15], ['PIVOT', 7], ['ZONE', 15], ['BOX', 33], ['DOUBLE', 31], ['VOLUME_NOTE', 20]]);
  for (const [name, spec] of W.EXPLORE_GRID) for (const tf of ['D', 'W']) {
    const [head, sub] = name.split('.'), value = Defaults.params[head], def = sub ? value[sub] : value && typeof value === 'object' ? value[tf] : value;
    assert.ok((Array.isArray(spec) ? spec : spec[tf]).includes(def), name + ' grid holds the default');
  }
});
test('user-settings params hash uses the engine canonical JSON and reproduces the shipped hash', () => {
  const E = require(path.join(assets, 'pattern-engine.js')), Defaults = require(path.join(assets, 'pattern-config-defaults.js'));
  assert.equal(crypto.createHash('sha256').update(E.canonicalJson(Defaults.params)).digest('hex'), Defaults.params_sha256);
});
test('synthetic engine run: official result is recorded, user settings are refused by the history', () => {
  const E = require(path.join(assets, 'pattern-engine.js')), B = require(path.join(assets, 'chart-bars.js')), H = require(path.join(assets, 'pattern-history.js')), Defaults = require(path.join(assets, 'pattern-config-defaults.js'));
  const s = W.syntheticHistory(), daily = B.normalize({schema: 'private-history/1', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', symbol: s.symbol, provider: '', currency: '', timezone: 'UTC', read_at: '', bars: s.bars});
  const actions = W.syntheticActions(daily), official = E.run(daily, Defaults, actions), objects = W.patternObjects(official);
  assert.deepEqual(actions, {status: 'AVAILABLE', covered_from: '2025-01-06', covered_to: '2026-03-27', events: []});
  assert.ok(objects.length > 0 && objects.every(o => o.judgeable) && objects.every(o => o.kind !== 'PIVOT'));
  assert.ok(objects.some(o => o.pattern === 'SUPPORT_RESISTANCE_ZONE') && objects.some(o => o.pattern && o.pattern.startsWith('BOX')) && objects.some(o => o.pattern && o.pattern.startsWith('DOUBLE')));
  const book = H.createBook(); assert.ok(book.append(official, 't').added > 0);
  const {params} = W.applyChanges(Defaults.params, {PIVOT_K: 5}, 'D');
  const user = E.run(daily, {...Defaults, params, params_sha256: crypto.createHash('sha256').update(E.canonicalJson(params)).digest('hex')}, actions);
  assert.equal(user.run_mode, 'USER_SETTINGS');
  assert.throws(() => book.append(user, 't'), /HISTORY_USER_SETTINGS_REFUSED/);
  const real = E.run(daily, Defaults, null), realObjects = W.patternObjects(real);
  assert.ok(realObjects.length > 0 && realObjects.every(o => !o.judgeable) && realObjects.every(o => o.reasons.includes('PRICE_BASIS_CONTINUITY_UNCONFIRMED')));
  assert.equal(H.createBook().append(real, 't').added, 0);
});

test('device continuity follows the Worker split block; older responses and unconfirmed info are never judged', () => {
  const E = require(path.join(assets, 'pattern-engine.js')), B = require(path.join(assets, 'chart-bars.js')), Defaults = require(path.join(assets, 'pattern-config-defaults.js'));
  const view = {ChartBars: B}, s = W.syntheticHistory(), bars = s.bars.slice(0, -1).map(b => ({...b, session_status: 'COMPLETE'}));
  const daily = R.normalizeBars(W.dailyView(bars, s.timezone)), first = daily[0].start, last = daily.at(-1).end, mid = daily.find((b, i) => i > 150 && new Date(b.start + 'T00:00:00Z').getUTCDay() === 3).start;
  const data = splitInfo => ({symbol: 'SYNTH', provider: 'Yahoo Finance(비공식)', timezone: s.timezone, readAt: '', bars, splitInfo});
  const block = (status, splits, price = 'SPLIT_ADJUSTED') => ({split_coverage: {status, from: status === 'CONFIRMED' ? first : null, to: status === 'CONFIRMED' ? last : null},
    splits: status === 'CONFIRMED' ? splits : null, split_basis: {price, volume: price === 'SPLIT_ADJUSTED' ? 'UNKNOWN' : price, source: 'PROVIDER_CONVENTION'}});
  assert.equal(W.deviceActions(view, data(null)), null, 'older Worker response: NOT_PROVIDED');
  assert.deepEqual(W.continuityOf(view, daily, W.deviceActions(view, data(null))).reason_codes, ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED']);
  for (const status of ['NOT_REPORTED', 'NOT_AVAILABLE', 'INVALID']) assert.equal(W.continuityOf(view, daily, W.deviceActions(view, data(block(status)))).state, 'NOT_JUDGEABLE', status);
  assert.deepEqual(W.continuityOf(view, daily, W.deviceActions(view, data(block('CONFIRMED', [])))), {state: 'CONFIRMED', reason_codes: []});
  assert.deepEqual(W.continuityCodes(view, daily, W.deviceActions(view, data(block('CONFIRMED', [])))), []);
  const split = [{date: mid, numerator: 2, denominator: 1}];
  assert.deepEqual(W.continuityOf(view, daily, W.deviceActions(view, data(block('CONFIRMED', split)))), {state: 'CONFIRMED', reason_codes: ['SPLIT_IN_WINDOW_PRICE_ADJUSTED']});
  assert.deepEqual(W.continuityOf(view, daily, W.deviceActions(view, data(block('CONFIRMED', split, 'UNADJUSTED')))).reason_codes, ['CORPORATE_ACTION_IN_WINDOW', 'PRICE_BASIS_UNADJUSTED']);
  const series = B.normalize({schema: 'private-history/1', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', symbol: 'SYNTH', provider: '', currency: '', timezone: s.timezone, read_at: '', bars});
  const confirmed = W.patternObjects(E.run(series, Defaults, W.deviceActions(view, data(block('CONFIRMED', [])))));
  assert.ok(confirmed.length > 0 && confirmed.every(o => o.judgeable), 'confirmed none: judgeable');
  const adjusted = W.patternObjects(E.run(series, Defaults, W.deviceActions(view, data(block('CONFIRMED', split)))));
  assert.ok(adjusted.some(o => o.judgeable && o.reasons.includes('SPLIT_IN_WINDOW_PRICE_ADJUSTED')), 'adjusted split: judgeable with a note');
  const raw = W.patternObjects(E.run(series, Defaults, W.deviceActions(view, data(block('CONFIRMED', split, 'UNADJUSTED')))));
  assert.ok(raw.some(o => o.state === 'NOT_JUDGEABLE' && o.reasons.includes('PRICE_BASIS_UNADJUSTED')), 'unadjusted split: live objects end not judgeable with a reason');
  assert.ok(adjusted.every(o => !o.reasons.includes('CORPORATE_ACTION_IN_WINDOW')), 'adjusted split: no object ends at the split');
  assert.equal(W.weeklyView(view, data(block('CONFIRMED', split, 'UNADJUSTED')), W.deviceActions(view, data(block('CONFIRMED', split, 'UNADJUSTED')))).bars.filter(b => b.open === null).length,
    W.weeklyView(view, data(null)).bars.filter(b => b.open === null).length + 1, 'only the week straddling an unadjusted split becomes NA');
  assert.deepEqual(W.syntheticActions(series), {status: 'AVAILABLE', covered_from: first, covered_to: last, events: []}, 'synthetic record unchanged');
});
test('user-written objects: anchors validated, this-device store, never routed to the pattern history', () => {
  const now = '2026-10-20T00:00:00.000Z', base = {id: 'u-abc123', symbol: 'SYNTH', interval: 'D', price_basis: 'RAW_CLOSE', author: 'USER', text: '', created_at: now, updated_at: now};
  const line = {...base, schema: 'chart-annotation/1', kind: 'LINE', points: [{time: '2025-01-06', price: 100}, {time: '2025-02-03', price: 110}]};
  const scenario = {...base, id: 'u-def456', schema: 'chart-scenario/1', horizon: 'swing', direction: 'SIDEWAYS', levels: [{label: 'a', price: 95}], condition: 'c', invalidation: 'i', invalidation_price: null, anchor_time: '2025-02-03'};
  assert.ok(W.validUserObject(line) && W.validUserObject(scenario));
  for (const bad of [{...line, author: 'AUTO'}, {...line, interval: 'M'}, {...line, points: [{time: 'x', price: 1}, {time: '2025-01-07', price: 1}]}, {...line, points: [{time: '2025-01-06', price: 0}, {time: '2025-01-07', price: 1}]},
    {...line, kind: 'MEMO'}, {...line, text: 'x'.repeat(501)}, {...line, id: 'BOX|SYNTH'}, {...scenario, direction: 'BUY'}, {...scenario, levels: []}, {...scenario, horizon: 'day'}, {...line, schema: 'pattern-history/1'}]) assert.equal(W.validUserObject(bad), false);
  const map = new Map(), storage = {getItem: k => (map.has(k) ? map.get(k) : null), setItem: (k, v) => map.set(k, v), removeItem: k => map.delete(k)}, store = W.createDeviceUserStore(storage);
  assert.equal(store.kind, 'THIS_BROWSER'); assert.equal(store.load().code, 'EMPTY');
  assert.ok(store.save([line, scenario])); assert.deepEqual(JSON.parse(map.get(W.USER_KEY)).schema, 'chart-user-objects/1');
  assert.equal(store.load().items.length, 2);
  map.set(W.USER_KEY, JSON.stringify({schema: 'chart-user-objects/1', items: [line, {...line, author: 'AUTO'}]}));
  assert.deepEqual([store.load().code, store.load().items.length], ['PARTLY_INVALID', 1]);
  map.set(W.USER_KEY, '{'); assert.equal(store.load().code, 'STORE_INVALID');
  assert.ok(store.clear()); assert.equal(map.has(W.USER_KEY), false);
  assert.equal(W.createDeviceUserStore({getItem() { throw new Error('x'); }}).load().code, 'STORAGE_UNAVAILABLE');
  const code = fs.readFileSync(path.join(assets, 'chart-workbench.js'), 'utf8'), userLayer = code.slice(code.indexOf('/* ---------- user layer'), code.indexOf('/* ---------- rendering'));
  assert.ok(userLayer.length > 1000 && !/books|PatternHistory|\.append\(official|fetch\(|XMLHttpRequest|sheets|gapi/.test(userLayer));
});
console.log('COUNTS pass=' + pass + ' fail=' + fail);
if (fail) process.exitCode = 1;
