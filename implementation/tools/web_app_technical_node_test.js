'use strict';
// New frontend · 2. 기술적 분석 (feature 3, screen-technical-live.js helpers) and its one store member (IS2.store.chartNotes),
// on the real old modules:
//  - pattern-rules/1: the screen's copy of the research defaults equals pattern-config-defaults.js (params, version, status,
//    label), and the 3.2.2 rows are ChartWorkbench.EXPLORE_GRID with the degree's value (D / W) plus DB_SEP_MAX.
//  - SMA lines: sma(closes(bars), n) equals ResearchIndicators.calculate's SMA_20 / 60 / 120 on synthetic bars (COMPLETE closes
//    only; a missing close restarts the window), so the device chart draws the old indicator's numbers.
//  - Chart geometry: priceAt reads TechnicalChart.geometry's y backwards (rounded to six significant digits, the old pointer rule)
//    and indexAt its x; marks() places notes on bar dates inside the price range only.
//  - Notes and scenarios: noteFor / scenarioFor build objects ChartWorkbench.validUserObject accepts once the store adds id,
//    author, price_basis and times; invalid input gives null.
//  - Store: ChartWorkbench's key and schema (chart-user-objects/1) through its own device store; read freely; added / removed only
//    in a trusted click (CLICK_REQUIRED, ACTION_REQUIRED for a direct write outside one); a price series or any unknown field is
//    refused (CHART_NOTE_INVALID, storage unchanged); an unreadable stored value is never overwritten and unreadable entries are
//    written back; 500 at most; carried by the /5 backup only; one click, one action.
// Synthetic data only (tools/web_app_technical_fixture.js closes end in made-up decimals). The helpers run in their own vm realm, so
// their arrays and objects are compared as plain JSON copies.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const FX = require('./web_app_technical_fixture.js');

const plain = (v) => JSON.parse(JSON.stringify(v));
const fresh = (name) => { delete require.cache[require.resolve(R.newPath(name))]; return R.requireNew(name); };
function helpers() {
  const IS2 = { h() {}, href() {}, parts: {} };
  vm.runInNewContext(fs.readFileSync(R.newPath('screen-technical-live.js'), 'utf8'), { window: { IS2 }, Object }, { filename: 'screen-technical-live.js' });
  return IS2.technicalLive.helpers;
}
const H = helpers();
const OLD = (() => { const win = R.nodeWindow(); return R.loadOld(win); })();
const READ_AT = '2026-10-14T21:00:00Z';
const BARS = FX.history('NVDA', '1y', READ_AT).bars;

test('pattern-rules/1: the screen copy equals pattern-config-defaults.js; 3.2.2 rows follow ChartWorkbench.EXPLORE_GRID per degree', () => {
  const D = require(R.oldPath('pattern-config-defaults.js'));
  assert.deepEqual(plain(H.PATTERN_RULES.params), plain(D.params));
  assert.deepEqual([H.PATTERN_RULES.rule_version, H.PATTERN_RULES.status, H.PATTERN_RULES.label_ko], [D.rule_version, D.status, D.label_ko]);
  const grid = OLD.ChartWorkbench.EXPLORE_GRID;
  for (const tf of ['D', 'W']) {
    const rows = H.paramRows(H.PATTERN_RULES, grid, tf);
    assert.equal(rows.length, grid.length + 1, tf + ': every grid rule plus DB_SEP_MAX');
    assert.deepEqual(plain(rows.filter((r) => r[0] !== 'DB_SEP_MAX').map((r) => r[0])), grid.map((g) => g[0]), tf + ': the grid order');
    const at = rows.findIndex((r) => r[0] === 'DB_SEP_MAX'); assert.equal(rows[at - 1][0], 'BOX_MAX_BARS', 'DB_SEP_MAX right after BOX_MAX_BARS (it follows it)');
    const val = (n) => { const [h, s] = n.split('.'), v = D.params[h]; return s ? v[s] : v && typeof v === 'object' ? v[tf] : v; };
    for (const [name, label, value, choices] of rows) {
      assert.equal(value, val(name), tf + ' ' + name);
      if (name === 'DB_SEP_MAX') { assert.equal(choices, null); continue; }
      const g = grid.find((x) => x[0] === name); assert.equal(label, g[2][0]); assert.deepEqual(plain(choices), plain(Array.isArray(g[1]) ? g[1] : g[1][tf]));
      assert.ok(choices.includes(value), tf + ' ' + name + ': the default is one of the exploration choices');
    }
  }
  assert.deepEqual(OLD.ChartWorkbench.minBars(H.PATTERN_RULES.params, 'D'), OLD.ChartWorkbench.minBars(D.params, 'D'));
});

test('SMA lines: sma(closes(bars), n) equals ResearchIndicators SMA_20 / 60 / 120 (COMPLETE closes only, a gap restarts the window)', () => {
  const RI = require(R.oldPath('chart-indicators.js'));
  const gap = BARS.map((b, i) => (i === 100 ? { ...b, close: null } : b));
  for (const bars of [BARS, gap]) {
    const ind = RI.calculate(bars, { priceBasis: 'RAW_CLOSE' });
    assert.notEqual(ind.state, 'NOT_AVAILABLE');
    for (const n of [20, 60, 120]) {
      const want = ind.indicators.find((x) => x.indicator_id === 'SMA_' + n).values;
      assert.deepEqual(plain(H.sma(H.closes(bars), n)), plain(want), 'SMA_' + n);
    }
  }
  assert.equal(H.closes(BARS).at(-1), null, 'the IN_PROGRESS last bar has no close for indicators');
  assert.deepEqual(plain(H.sma([1, 2, null, 3, 4, 5], 2)), [null, 1.5, null, null, 3.5, 4.5]);
});

test('chart geometry: priceAt / indexAt read TechnicalChart.geometry backwards; marks() keeps notes on bar dates inside the range', () => {
  const TC = OLD.TechnicalChart, g = TC.geometry(BARS, []), n = BARS.length;
  for (const v of [181.0718293, 200, 222.5, 240.0718293]) assert.equal(H.priceAt(g, g.y(v)), Number(v.toPrecision(6)), 'price at y(' + v + ')');
  assert.equal(H.priceAt(g, 0), H.priceAt(g, 20), 'above the plot: the top price'); assert.equal(H.priceAt(g, 400), H.priceAt(g, 220), 'below: the bottom price');
  assert.ok(!String(H.priceAt(g, 123)).includes(FX.SENTINEL), 'a pointer price is never a supplier close');
  for (const i of [0, 1, 7, n - 2, n - 1]) assert.equal(H.indexAt(n, g.x(i)), i);
  assert.equal(H.indexAt(n, -50), 0); assert.equal(H.indexAt(n, 900), n - 1); assert.equal(H.indexAt(1, 300), 0);
  const dates = OLD.ChartWorkbench.dailyView(BARS, 'America/New_York').map((b) => b.time), d = (i) => dates[i];
  const o = (id, kind, points, extra = {}) => ({ schema: 'chart-annotation/1', id, kind, symbol: 'NVDA', interval: 'D', points: points.map(([i, price]) => ({ time: typeof i === 'string' ? i : d(i), price })), ...extra });
  const items = [o('u-hline1', 'HLINE', [[3, 200]]), o('u-hline2', 'HLINE', [[3, 999]]), o('u-memo01', 'MEMO', [[10, 210]]), o('u-memo02', 'MEMO', [['2001-01-01', 210]]),
    o('u-line01', 'LINE', [[5, 190], [50, 230]]), o('u-range1', 'RANGE', [[60, 230], [20, 190]]), o('u-pen001', 'PEN', [[1, 200], [2, 201], [3, 202]]), o('u-week01', 'HLINE', [[3, 200]], { interval: 'W' }),
    { schema: 'chart-scenario/1', id: 'u-scen01', symbol: 'NVDA', interval: 'D' }];
  const got = H.marks(g, dates, items), by = Object.fromEntries(got.map((m) => [m.id, m]));
  assert.deepEqual(plain(got.map((m) => m.id)), ['u-hline1', 'u-memo01', 'u-line01', 'u-range1', 'u-pen001'], 'outside the range, off the bars, weekly and scenarios are left off');
  assert.equal(by['u-hline1'].d, 'M20,' + g.y(200).toFixed(2) + ' L620,' + g.y(200).toFixed(2));
  assert.deepEqual(plain([by['u-memo01'].cx, by['u-memo01'].cy]), [g.x(10).toFixed(2), g.y(210).toFixed(2)]);
  assert.equal(by['u-line01'].d, 'M' + g.x(5).toFixed(2) + ',' + g.y(190).toFixed(2) + ' L' + g.x(50).toFixed(2) + ',' + g.y(230).toFixed(2));
  assert.deepEqual(plain([by['u-range1'].x, by['u-range1'].y]), [g.x(20).toFixed(2), g.y(230).toFixed(2)], 'a range box from its left / top corner');
  assert.equal(by['u-pen001'].d.split(' ').length, 3);
});

test('noteFor / scenarioFor: objects validUserObject accepts once the store adds its fields; invalid input gives null', () => {
  const CW = OLD.ChartWorkbench, add = (o) => ({ ...o, id: 'u-abcdef12', author: 'USER', price_basis: 'RAW_CLOSE', created_at: '2026-10-14T00:00:00.000Z', updated_at: '2026-10-14T00:00:00.000Z' });
  const n = H.noteFor({ kind: 'HLINE', symbol: 'NVDA', date: '2026-10-01', price: 123.5, text: '지지선' });
  assert.deepEqual(plain(n), { schema: 'chart-annotation/1', kind: 'HLINE', symbol: 'NVDA', interval: 'D', points: [{ time: '2026-10-01', price: 123.5 }], text: '지지선' });
  assert.ok(CW.validUserObject(add(n))); assert.ok(CW.validUserObject(add(H.noteFor({ kind: 'MEMO', symbol: 'BRK.B', date: '2026-10-01', price: 1, text: '' }))));
  assert.equal(H.noteFor({ kind: 'MEMO', symbol: 'NVDA', date: '2026-10-01', price: 1, text: 'x'.repeat(600) }).text.length, 500);
  for (const bad of [{ kind: 'PEN', date: '2026-10-01', price: 1 }, { kind: 'HLINE', date: '2026-02-30', price: 1 }, { kind: 'HLINE', date: '2026-10-01', price: 0 }, { kind: 'HLINE', date: '2026-10-01', price: NaN }, { kind: 'MEMO', date: '', price: 1 }])
    assert.equal(H.noteFor({ symbol: 'NVDA', text: '', ...bad }), null, JSON.stringify(bad));
  const s = H.scenarioFor({ symbol: 'NVDA', direction: 'UP', horizon: 'swing', date: '2026-10-14', levels: [{ label: '1차 저항', price: 230 }, { label: '', price: 240 }], condition: '돌파', invalidation: '이탈', invalidationPrice: 200 });
  assert.equal(s.schema, 'chart-scenario/1'); assert.deepEqual(plain(s.levels), [{ label: '1차 저항', price: 230 }, { label: '', price: 240 }]); assert.ok(CW.validUserObject(add(s)));
  assert.ok(CW.validUserObject(add(H.scenarioFor({ symbol: 'NVDA', direction: 'SIDEWAYS', horizon: 'long', date: '2026-10-14', levels: [{ price: 1 }], invalidationPrice: null }))));
  for (const bad of [{ direction: 'FLAT' }, { horizon: 'day' }, { date: 'x' }, { levels: [] }, { levels: [{ price: -1 }] }, { invalidationPrice: 0 }])
    assert.equal(H.scenarioFor({ symbol: 'NVDA', direction: 'UP', horizon: 'swing', date: '2026-10-14', levels: [{ price: 1 }], invalidationPrice: null, ...bad }), null, JSON.stringify(bad));
  const items = [{ id: 'u-a00001', schema: 'chart-annotation/1', symbol: 'NVDA', created_at: '2026-10-01' }, { id: 'u-a00002', schema: 'chart-annotation/1', symbol: 'NVDA', created_at: '2026-10-03' },
    { id: 'u-a00003', schema: 'chart-scenario/1', symbol: 'NVDA', created_at: '2026-10-05' }, { id: 'u-a00004', schema: 'chart-annotation/1', symbol: 'AMD', created_at: '2026-10-09' }];
  assert.deepEqual(plain(H.ofSymbol(items, 'NVDA', 'chart-annotation/1').map((o) => o.id)), ['u-a00002', 'u-a00001'], 'this symbol and schema, newest first');
  const tie = [{ id: 'u-zzzzzz', schema: 'chart-annotation/1', symbol: 'NVDA', created_at: 'T' }, { id: 'u-aaaaaa', schema: 'chart-annotation/1', symbol: 'NVDA', created_at: 'T' }];
  assert.deepEqual(plain(H.ofSymbol(tie, 'NVDA', 'chart-annotation/1').map((o) => o.id)), ['u-aaaaaa', 'u-zzzzzz'], 'same time: the later stored first (the store appends)');
});

// ---------------------------------------------------------------- store: IS2.store.chartNotes on the real layer
const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
function memoryStorage() {
  const m = new Map();
  return { map: m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); }, clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; } };
}
function env() {
  const win = R.nodeWindow({ files: (name) => ({ 'actual-catalog.json': { json: CATALOG } }[name] || null) }), mods = R.loadOld(win);
  win.localStorage = memoryStorage(); win.sessionStorage = memoryStorage(); win.crypto = { getRandomValues: (b) => require('node:crypto').getRandomValues(b), subtle: globalThis.crypto.subtle };
  const action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action }), store = fresh('store.js').create({ win, action, data });
  return { win, mods, store, click: () => win.trusted('click') };
}
const NOTE = { schema: 'chart-annotation/1', kind: 'HLINE', symbol: 'NVDA', interval: 'D', points: [{ time: '2026-10-01', price: 123.5 }], text: '지지선 후보' };

test('store.chartNotes: ChartWorkbench\'s key and schema; read freely; written only in a click; the store sets id / author / basis / times', () => {
  const e = env(), K = e.store.KEYS, L = e.win.localStorage, C = e.store.chartNotes, CW = e.mods.ChartWorkbench;
  assert.equal(K.CHART_USER_OBJECTS, CW.USER_KEY);
  assert.deepEqual(plain(C.read()), { state: 'EMPTY', items: [], unreadable: 0 }); assert.ok(Object.isFrozen(C.read()));
  for (const ev of [undefined, new Event('click'), { type: 'click', isTrusted: true }]) { assert.throws(() => C.add(ev, NOTE), /CLICK_REQUIRED/); assert.throws(() => C.remove(ev, 'u-abcdef'), /CLICK_REQUIRED/); }
  assert.equal(L.getItem(K.CHART_USER_OBJECTS), null, 'nothing written without a click');
  assert.equal(CW.createDeviceUserStore(e.store.storage).save([{ ...NOTE, id: 'u-abcdef12', author: 'USER', price_basis: 'RAW_CLOSE', created_at: 'x', updated_at: 'x' }]), false, 'the old store handed the gated storage writes nothing outside a click');
  assert.equal(L.getItem(K.CHART_USER_OBJECTS), null);
  const notes = []; e.store.subscribe((w) => notes.push(w));
  const a = C.add(e.click(), { ...NOTE, id: 'u-mine00', author: 'X', price_basis: 'ADJ', created_at: 'then' });
  assert.match(a.id, /^u-[a-z0-9]{6,32}$/); assert.notEqual(a.id, 'u-mine00', 'the store makes the id');
  assert.deepEqual([a.author, a.price_basis], ['USER', 'RAW_CLOSE']); assert.ok(Number.isFinite(Date.parse(a.created_at)) && a.created_at === a.updated_at);
  const b = C.add(e.click(), { schema: 'chart-scenario/1', symbol: 'NVDA', interval: 'D', text: '', anchor_time: '2026-10-14', horizon: 'swing', direction: 'UP', levels: [{ label: '저항', price: 230 }], condition: '', invalidation: '', invalidation_price: null });
  assert.deepEqual(notes, ['CHART_USER_OBJECTS', 'CHART_USER_OBJECTS']);
  const raw = JSON.parse(L.getItem(K.CHART_USER_OBJECTS));
  assert.equal(raw.schema, CW.USER_SCHEMA); assert.deepEqual(raw.items.map((o) => o.id), [a.id, b.id]);
  assert.deepEqual(plain(CW.createDeviceUserStore(e.store.storage).load().items), plain(C.read().items), 'the old module reads what the store wrote');
  assert.deepEqual(plain(CW.parseUserExport({ schema: CW.USER_SCHEMA, items: raw.items })), raw.items, 'every stored item passes the old export check');
  assert.equal(C.read().state, 'OK');
  // A price series, quote fields or any unknown field: refused, storage unchanged.
  const before = L.getItem(K.CHART_USER_OBJECTS);
  for (const bad of [{ ...NOTE, close: 1 }, { ...NOTE, bars: [] }, { ...NOTE, points: [{ time: '2026-10-01', price: 0 }] }, { ...NOTE, kind: 'CANDLE' }, { ...NOTE, schema: 'chart-bars/1' }, { ...NOTE, symbol: 'nvda lower' }, null, 'x'])
    assert.throws(() => C.add(e.click(), bad), /CHART_NOTE_INVALID/, JSON.stringify(bad));
  assert.equal(L.getItem(K.CHART_USER_OBJECTS), before, 'a refused object changes nothing');
  assert.throws(() => e.store.storage.setItem(K.CHART_USER_OBJECTS, '{}'), /ACTION_REQUIRED/, 'the gated storage refuses a write outside a click');
  // Delete one by id; the last one removes the key (the old store's save of an empty list).
  assert.equal(C.remove(e.click(), a.id), 1); assert.throws(() => C.remove(e.click(), a.id), /CHART_NOTE_NOT_FOUND/);
  assert.equal(C.remove(e.click(), b.id), 0); assert.equal(L.getItem(K.CHART_USER_OBJECTS), null, 'no objects: no key');
  // One click, one action.
  const ev = e.click(); C.add(ev, NOTE); assert.throws(() => C.add(ev, NOTE), /ACTION_ALREADY_STARTED/); assert.equal(C.read().items.length, 1);
});

test('store.chartNotes: an unreadable value is never overwritten; unreadable entries are kept; 500 at most; in the /5 backup only', async () => {
  const e = env(), K = e.store.KEYS, L = e.win.localStorage, C = e.store.chartNotes, CW = e.mods.ChartWorkbench;
  L.setItem(K.CHART_USER_OBJECTS, '{broken'); assert.deepEqual(plain(C.read()), { state: 'INVALID', items: [], unreadable: 0 });
  assert.throws(() => C.add(e.click(), NOTE), /CHART_NOTES_STORAGE_INVALID/); assert.throws(() => C.remove(e.click(), 'u-abcdef'), /CHART_NOTES_STORAGE_INVALID/);
  assert.equal(L.getItem(K.CHART_USER_OBJECTS), '{broken', 'never overwritten');
  const odd = { schema: 'chart-annotation/2', id: 'u-future1', kind: 'ARROW' };
  L.setItem(K.CHART_USER_OBJECTS, JSON.stringify({ schema: CW.USER_SCHEMA, items: [odd] }));
  assert.deepEqual(plain(C.read()), { state: 'PARTLY_INVALID', items: [], unreadable: 1 });
  const a = C.add(e.click(), NOTE);
  assert.deepEqual(JSON.parse(L.getItem(K.CHART_USER_OBJECTS)).items.map((o) => o.id), [a.id, 'u-future1'], 'the unreadable entry is written back unchanged');
  C.remove(e.click(), a.id); assert.deepEqual(JSON.parse(L.getItem(K.CHART_USER_OBJECTS)).items, [odd]);
  // 500 at most (ChartWorkbench.USER_LIMIT); a full device can still delete.
  const full = Array.from({ length: CW.USER_LIMIT }, (_, i) => ({ ...NOTE, id: 'u-full' + String(i).padStart(4, '0'), author: 'USER', price_basis: 'RAW_CLOSE', created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }));
  L.setItem(K.CHART_USER_OBJECTS, JSON.stringify({ schema: CW.USER_SCHEMA, items: full }));
  assert.throws(() => C.add(e.click(), NOTE), /CHART_NOTES_FULL/); assert.equal(C.remove(e.click(), 'u-full0003'), CW.USER_LIMIT - 1);
  // The /5 backup carries them (DeviceBackup reads ChartWorkbench's store itself); /4 does not.
  L.removeItem(K.CHART_USER_OBJECTS); const n = C.add(e.click(), NOTE);
  const p5 = await e.store.backup.create({ userObjects: true });
  assert.deepEqual(p5.user_objects.chart.items.map((o) => o.id), [n.id]); assert.equal((await e.store.backup.create()).user_objects, undefined);
});
