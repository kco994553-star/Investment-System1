'use strict';
// Virtual ledger sheet storage (D-10): the JS pure part must equal the Python reference on the shared SYNTHETIC vectors
// (row text, replay verification, missing sessions, inputs hashes, tab/meta/flag parsing, weights, new-ledger rows), and
// the sheet layer must append only to the five Virtual* tabs, only missing sessions, never before the start date,
// never for a rehearsal, never after a replay mismatch or a changed header.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const S = require('../src/investment_system/product/web_assets/virtual-ledger-sheets.js');
const R = require('../src/investment_system/product/web_assets/virtual-trading-runner.js');
const VT = require('../src/investment_system/product/web_assets/virtual-trading.js');
const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_ledger_sheets_v1.json'), 'utf8'));
const inputs = JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/virtual_trading_inputs_v1.json'), 'utf8'));
const plain = (v) => JSON.parse(JSON.stringify(v));
const sha = (text) => crypto.createHash('sha256').update(text, 'utf8').digest('hex');
const vector = inputs.vectors.find((v) => v.name === fixture.base_vector);
const assembled = () => R.assemble(vector.inputs);
const base = () => assembled().ledgers.SET_A.input;
const cfg = VT.defaultConfig();
const errorOf = (fn) => { try { return plain(fn()); } catch (e) { return { error: e.message }; } };

test('fixture is marked synthetic and reproduces the recordable-through date', () => {
  assert.equal(fixture.synthetic, true);
  assert.ok(fixture.note.startsWith('SYNTHETIC'));
  assert.equal(S.recordableThrough(base()), fixture.recordable_through);
});

test('number text and canonical JSON equal Python', () => {
  for (const [x, expected] of fixture.numbers) assert.equal(S.numStr(x), expected, String(x));
  assert.equal(S.canonical(fixture.canonical.value), fixture.canonical.expected);
  assert.throws(() => S.numStr(NaN), /NUMBER_INVALID/);
});

for (const v of fixture.statuses) {
  test('replay status ' + v.name + ' equals Python', () => {
    const { status, input } = S.ledgerStatus(v.ledger, base(), v.recorded, cfg, v.through);
    assert.deepEqual(plain(status), v.expected);
    const last = status.missing.length ? status.missing.at(-1) : status.recorded_through;
    assert.equal(input && status.recorded_through ? sha(S.inputsText(input, status.recorded_through)) : null, v.recorded_sha256);
    assert.equal(input && last ? sha(S.inputsText(input, last)) : null, v.next_sha256);
  });
}

test('tab, group, meta and flag parsing equal Python', () => {
  for (const v of fixture.tabs) assert.deepEqual(errorOf(() => S.parseTab(v.values, S.HEADS[v.tab])), v.expected, v.name);
  for (const v of fixture.groups) assert.deepEqual(errorOf(() => S.groupLedgerRows(v.rows)), v.expected, v.name);
  for (const v of fixture.meta) assert.deepEqual(plain(S.parseMeta(v.rows)), v.expected, v.name);
  for (const v of fixture.flags) assert.deepEqual(errorOf(() => S.parseFlags(v.values)), v.expected, v.name);
});

test('weights, begin dates and meta rows equal Python', () => {
  for (const v of fixture.weights) assert.deepEqual(plain(S.validateWeights(v.raw, R.IDS)), v.expected, v.name);
  for (const v of fixture.begin_for) assert.equal(S.beginFor(v.now, cfg, v.previous_last), v.expected, v.now);
  for (const v of fixture.replace) assert.deepEqual(S.replaceRows(v.meta, v.kind, v.now, cfg, v.payload, v.recorded_last, v.reason), v.expected, v.name);
  const r = fixture.record_row;
  assert.deepEqual(S.recordRow('2026-10-21T23:30:00Z', r.status, cfg, r.sha256, r.rows), r.expected);
});

test('row text: a day with missing inputs keeps the engine outcome, nothing is filled; amounts are never 0 for NOT_AVAILABLE', () => {
  const v = fixture.statuses.find((x) => x.name === 'set_a_resume');
  const rows = v.expected.append_rows;
  assert.ok(rows.some((r) => r[2] === 'CANCELLED' && r[6] === 'EXEC_FX_MISSING'), 'EXEC_FX_MISSING recorded');
  assert.ok(fixture.statuses.find((x) => x.name === 'set_a_fresh_capped').expected.append_rows.some((r) => r[1] === '2026-10-21' && r[2] === 'JUDGEMENT' && r[6].includes('DATA_SNAPSHOT_MISSING')));
  for (const r of rows) { assert.equal(r.length, S.LEDGER_HEAD.length); assert.ok(r.every((c) => typeof c === 'string')); }
  // Average cost never enters a judgement: the same snapshot with other costs gives the same JUDGEMENT/ORDER rows.
  const s = fixture.statuses.find((x) => x.name === 'shadow_segment');
  const other = JSON.parse(JSON.stringify(s.ledger)); for (const p of Object.values(other.snapshot.positions)) p.average_cost *= 3;
  const pick = (rs) => rs.filter((r) => r[2] === 'JUDGEMENT' || r[2] === 'ORDER');
  assert.deepEqual(pick(S.ledgerStatus(other, base(), [], cfg, s.through).status.append_rows), pick(s.expected.append_rows));
});

/* ---------- sheet layer with an in-memory mock of the user's sheet ---------- */
function mockSheet(initial = {}) {
  const tabs = new Map(Object.entries(initial).map(([k, v]) => [k, v.map((r) => [...r])]));
  const calls = [];
  const session = {
    async sheetTitles() { calls.push(['titles']); return ['Quotes', ...tabs.keys()]; },
    async addTabs(id, titles) { calls.push(['add', titles]); for (const t of titles) { assert.ok(S.ALL_TABS.includes(t)); tabs.set(t, []); } },
    async appendRows(id, range, rows) {
      calls.push(['append', range, rows.length]);
      const m = /^'([A-Za-z]+)'!A1$/.exec(range); assert.ok(m && S.ALL_TABS.includes(m[1]), range);
      assert.ok(rows.every((r) => r.every((c) => typeof c === 'string')));
      assert.ok(JSON.stringify(rows).length <= 262144);
      tabs.get(m[1]).push(...rows.map((r) => [...r]));
    },
    async fetchValues(id, range, options) {
      calls.push(['read', range]);
      assert.equal(options.allowEmpty, true);
      const m = /^'([A-Za-z]+)'!A(\d+):([A-Z])(\d+)$/.exec(range); const rows = tabs.get(m[1]) || [];
      // Sheets omits trailing empty cells.
      return { range, values: rows.slice(Number(m[2]) - 1, Number(m[4])).map((r) => { const c = [...r]; while (c.length && c[c.length - 1] === '') c.pop(); return c; }) };
    },
  };
  return { session, tabs, calls };
}
const result = () => assembled();
const ID = 'synthetic_sheet_fixture_id_000000';
const NOW = '2026-10-31T00:10:00Z';

test('record: creates the five tabs with headers, writes Set A/Set B missing sessions, then nothing more (append-only)', async () => {
  const { session, tabs, calls } = mockSheet();
  await S.saveSetB(session, ID, { nvda: '40', msft: '35.5', hanmi: '24.5' }, { now: '2026-10-21T13:00:00Z' });
  assert.deepEqual([...tabs.keys()].sort(), [...S.ALL_TABS].sort());
  for (const t of S.ALL_TABS) assert.deepEqual(tabs.get(t)[0], [...S.HEADS[t]]);
  const r = await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  assert.deepEqual(r.ledgers, ['set_a', 'set_b-1']);
  const meta = tabs.get('VirtualMeta').slice(1);
  assert.deepEqual(meta.map((m) => [m[1], m[3]]), [['set_b-1', 'LEDGER_START'], ['set_a', 'LEDGER_START'], ['set_a', 'RECORD'], ['set_b-1', 'RECORD']]);
  assert.equal(meta[2][8], fixture.recordable_through);
  assert.match(meta[2][9], /^[0-9a-f]{64}$/);
  // Same rows the pure status said, VirtualMine untouched by a MOCK record.
  const sA = fixture.statuses.find((x) => x.name === 'set_a_fresh_capped');
  assert.deepEqual(tabs.get('VirtualA').slice(1, 1 + sA.expected.append_rows.length), sA.expected.append_rows);
  assert.equal(tabs.get('VirtualMine').length, 1);
  const before = JSON.stringify([...tabs]);
  const again = await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  assert.equal(again.sessions, 0);
  assert.equal(JSON.stringify([...tabs]), before, 'second click writes nothing');
  // Resume: the sheet state verifies by replay and reports no missing session.
  const st = S.statuses(await S.load(session, ID), result(), cfg);
  assert.deepEqual(st.ledgers.map((s) => [s.id, s.state, s.missing.length]), [['set_a', 'OK', 0], ['set_b-1', 'OK', 0]]);
  assert.ok(calls.every((c) => c[0] !== 'append' || /^'Virtual/.test(c[1])));
});

test('record: a changed cell → LEDGER_REPLAY_MISMATCH and no write; a changed header → SHEET_HEADER_MISMATCH', async () => {
  const { session, tabs } = mockSheet();
  await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  const rows = tabs.get('VirtualA'); const k = rows.findIndex((r) => r[2] === 'SUMMARY');
  rows[k] = [...rows[k]]; rows[k][13] = String(Number(rows[k][13]) + 1);
  const snapshot = JSON.stringify([...tabs]);
  const st = S.statuses(await S.load(session, ID), result(), cfg);
  assert.equal(st.ledgers[0].state, 'LEDGER_REPLAY_MISMATCH');
  assert.equal(st.ledgers[0].first_mismatch.session, rows[k][1]);
  // Drop the last recorded sessions so there would be something to write: still refused.
  tabs.set('VirtualA', rows.filter((r, i) => i === 0 || r[1] <= '2026-10-27'));
  await assert.rejects(S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW }), /LEDGER_REPLAY_MISMATCH/);
  const header = mockSheet({ VirtualA: [[...S.LEDGER_HEAD.slice(0, -1), 'total']] });
  const sheet = await S.load(header.session, ID);
  assert.deepEqual([sheet.state, sheet.reason_codes, sheet.tab], ['ERROR', ['SHEET_HEADER_MISMATCH'], 'VirtualA']);
  await assert.rejects(S.record(header.session, ID, { result: result(), kind: 'MOCK', now: NOW }), /SHEET_HEADER_MISMATCH/);
  assert.equal(header.calls.filter((c) => c[0] === 'append' || c[0] === 'add').length, 0);
  assert.ok(snapshot.length > 0);
});

test('record: never before the start date, never a rehearsal, never with inputs not ready', async () => {
  const { session, calls } = mockSheet();
  await assert.rejects(S.record(session, ID, { result: result(), kind: 'MOCK', rehearsal: true }), /REHEARSAL_NOT_RECORDED/);
  await assert.rejects(S.record(session, ID, { result: { ...result(), rehearsal: true }, kind: 'MOCK' }), /REHEARSAL_NOT_RECORDED/);
  // A rehearsal-style input that replays sessions before 2026-10-19 is refused even when not flagged.
  const early = result(); early.ledgers.SET_A.input = { ...early.ledgers.SET_A.input, sessions: ['2026-10-16', ...early.ledgers.SET_A.input.sessions] };
  early.ledgers.SET_A.input.companies = Object.fromEntries(Object.entries(early.ledgers.SET_A.input.companies).map(([k, c]) => [k, { ...c, closes: { ...c.closes } }]));
  const st = S.statuses({ state: 'READY', reason_codes: [], tabs: {}, headerless: [], meta: { ledgers: [{ id: 'set_a', kind: 'SET_A', begin: '2026-10-12', end: null, target_basis: 'TARGET_V0', target_weights: early.ledgers.SET_A.input.target_weights, snapshot: null }], records: {}, user_target: null }, rows: {}, flags: [] }, early, cfg);
  assert.ok(st.ledgers[0].missing.every((d) => d >= '2026-10-19'), 'engine replays from the start date only');
  await assert.rejects(S.record(session, ID, { result: { state: 'NOT_STARTED', reason_codes: ['BEFORE_START_DATE'], ledgers: {} }, kind: 'MOCK' }), /BEFORE_START_DATE/);
  assert.equal(calls.filter((c) => c[0] === 'append' || c[0] === 'add').length, 0);
});

test('Set B: validated, a redefinition closes the old ledger and starts the next one after its recorded sessions', async () => {
  const { session, tabs } = mockSheet();
  await assert.rejects(S.saveSetB(session, ID, { nvda: '70', amd: '40' }), /WEIGHT_SUM_OVER_100/);
  await assert.rejects(S.saveSetB(session, ID, {}), /WEIGHTS_EMPTY/);
  await S.saveSetB(session, ID, { nvda: '40', msft: '35.5', hanmi: '24.5' }, { now: '2026-10-19T13:00:00Z' });
  await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  const rows = await S.saveSetB(session, ID, { amd: '50' }, { now: '2026-10-29T01:00:00Z' });
  assert.deepEqual(rows.map((r) => [r[1], r[3], r[4], r[5]]), [['set_b-1', 'LEDGER_CLOSE', '', '2026-10-31'], ['set_b-2', 'LEDGER_START', '2026-10-31', '']]);
  const sheet = await S.load(session, ID);
  assert.deepEqual(plain(S.active(sheet.meta, 'SET_B').target_weights), { amd: 50 });
  const st = S.statuses(sheet, result(), cfg);
  assert.deepEqual(st.ledgers.map((s) => [s.id, s.state]), [['set_a', 'OK'], ['set_b-1', 'OK'], ['set_b-2', 'NOT_STARTED']]);
  // Runner hook: the stored Set B reaches the report through apply().
  const shown = S.apply(R.assemble({ ...vector.inputs, set_b: { target_weights: { amd: 50 } } }), sheet);
  assert.equal(shown.ledgers.SET_B.input.id, 'set_b-2');
  assert.ok(tabs.get('VirtualB').length > 1);
});

test('TARGET and shadow snapshot: user target is the basis, re-sync closes the segment and keeps its rows', async () => {
  const { session, tabs } = mockSheet();
  const holdings = vector.inputs.holdings;
  const catalogWeights = Object.fromEntries(R.catalogTargets(vector.inputs.catalog).map((t) => [t.cid, t.weight]));
  await assert.rejects(S.startShadow(session, ID, holdings, { resync: true, catalogWeights }), /SHADOW_NOT_STARTED/);
  await assert.rejects(S.startShadow(session, ID, { positions: {} }, { catalogWeights }), /NO_ACTUAL/);
  await S.saveTarget(session, ID, { nvda: '30', hanmi: '20', tokyo_electron: '10', msft: '20' }, { now: '2026-10-19T12:00:00Z' });
  const start = await S.startShadow(session, ID, holdings, { now: '2026-10-20T13:00:00Z', catalogWeights });
  assert.deepEqual([start[0][1], start[0][3], start[0][4]], ['shadow-1', 'LEDGER_START', '2026-10-20']);
  assert.equal(JSON.parse(start[0][10]).target_basis, 'USER_TARGET');
  await assert.rejects(S.startShadow(session, ID, holdings, { catalogWeights }), /SHADOW_ALREADY_STARTED/);
  const shadowStatus = fixture.statuses.find((x) => x.name === 'shadow_segment');
  const r = await S.record(session, ID, { result: result(), kind: 'REAL', now: NOW });
  assert.deepEqual(r.ledgers, ['shadow-1']);
  assert.deepEqual(tabs.get('VirtualMine').slice(1), shadowStatus.expected.append_rows);
  assert.equal(tabs.get('VirtualA').length, 1, 'REAL record touches only the shadow ledger');
  const kept = JSON.stringify(tabs.get('VirtualMine'));
  const re = await S.startShadow(session, ID, holdings, { now: '2026-11-01T01:00:00Z', resync: true, catalogWeights });
  assert.deepEqual(re.map((x) => [x[1], x[3], x[4] || x[5]]), [['shadow-1', 'LEDGER_CLOSE', '2026-10-31'], ['shadow-2', 'LEDGER_START', '2026-10-31']]);
  assert.equal(JSON.parse(re[1][10]).reason, 'RESYNC');
  assert.equal(JSON.stringify(tabs.get('VirtualMine')), kept, 're-sync never rewrites recorded rows');
  const sheet = await S.load(session, ID);
  assert.deepEqual(sheet.meta.ledgers.map((l) => [l.id, l.end]), [['shadow-1', '2026-10-31'], ['shadow-2', null]]);
  assert.deepEqual(S.statuses(sheet, result(), cfg).ledgers.filter((s) => s.kind === 'SHADOW').map((s) => [s.id, s.state]), [['shadow-1', 'OK'], ['shadow-2', 'NOT_STARTED']]);
  // Without a stored shadow ledger the preview uses the saved user target.
  const t = mockSheet();
  await S.saveTarget(t.session, ID, { nvda: '50' });
  assert.deepEqual(plain(S.apply(result(), await S.load(t.session, ID)).ledgers.SHADOW.input.target_weights), { nvda: 50 });
});

test('flags from VirtualFlags reach the runner input; module has no console/storage/network use', () => {
  const src = fs.readFileSync(path.join(__dirname, '../src/investment_system/product/web_assets/virtual-ledger-sheets.js'), 'utf8');
  for (const bad of ['console.', 'localStorage', 'sessionStorage', 'indexedDB', 'fetch(', 'XMLHttpRequest', 'sendBeacon']) assert.ok(!src.includes(bad), bad);
  assert.ok(src.includes('가상 · 실제 추천 아님 · 주문 기능 없음'));
  const out = R.assemble({ ...vector.inputs, flags: S.parseFlags(fixture.flags[0].values).flags });
  assert.deepEqual(out.ledgers.SET_A.input.flags.map((f) => f.company), ['googl', 'nvda', 'tokyo_electron', 'rok']);
});
