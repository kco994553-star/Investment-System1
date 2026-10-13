'use strict';
// Virtual ledger sheet storage (D-10): the JS pure part must equal the Python reference on the shared SYNTHETIC vectors
// (row text, continuation from the recorded state, PRICE_REVISED, missing sessions, inputs hashes, tab/meta/flag parsing,
// weights, set definitions, new-ledger rows), and the sheet layer must append only to the seven Virtual* tabs, only
// missing sessions, never before the start date, never for a rehearsal, never with malformed rows or a changed header.
// Decision 2026-10-11: recorded rows are canonical; a replay that differs marks PRICE_REVISED and recording goes on.
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
const revised = (v) => { if (!v.revise) return base(); const b = base(); b.companies[v.revise.company].closes = { ...b.companies[v.revise.company].closes, [v.revise.date]: v.revise.close }; return b; };
const PURPOSE = '반도체·소프트웨어 혼합 비교';

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
    const { status, input } = S.ledgerStatus(v.ledger, revised(v), v.recorded, cfg, v.through);
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

test('recorded state, set definitions, Set A versions, deletion and ids equal Python', () => {
  for (const v of fixture.recorded_states) assert.deepEqual(errorOf(() => S.recordedState(v.rows)), v.expected, v.name);
  for (const v of fixture.sets) assert.deepEqual(plain(S.validateSet(v.raw, v.purpose, v.kind, Object.keys(R.MEMBERS))), v.expected, v.name);
  for (const v of fixture.set_a_change) assert.deepEqual(S.setAChangeRows(v.meta, base(), v.now, cfg, v.payload, v.recorded_last), v.expected, v.name);
  for (const v of fixture.deletes) assert.deepEqual(errorOf(() => S.deleteRows(v.meta, v.kind, v.now, cfg, v.recorded_last)), v.expected, v.name);
  for (const v of fixture.next_ids) assert.equal(S.nextId(v.meta, v.kind), v.expected);
  assert.deepEqual(Object.keys(R.MEMBERS).sort(), fixture.members);
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

test('record: creates the missing tabs with headers, writes Set A/Set B missing sessions, then nothing more (append-only)', async () => {
  // The user's VirtualFlags tab holds the same flag as the synthetic runner vector (googl HOLD on 2026-10-22).
  const { session, tabs, calls } = mockSheet({ VirtualFlags: [[...S.FLAGS_HEAD], ['', '2026-10-22', 'GOOGL', 'hold']] });
  await S.saveSetB(session, ID, { nvda: '40', msft: '35.5', hanmi: '24.5' }, { now: '2026-10-21T13:00:00Z', purpose: PURPOSE });
  assert.deepEqual([...tabs.keys()].sort(), [...S.ALL_TABS].sort());
  for (const t of S.ALL_TABS) assert.deepEqual(tabs.get(t)[0], [...S.HEADS[t]]);
  assert.equal(tabs.get('VirtualFlags').length, 2, 'an existing tab is not rewritten');
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

test('record: a changed cell → PRICE_REVISED, recorded rows kept, recording continues from the recorded state; malformed rows and a changed header block', async () => {
  const { session, tabs } = mockSheet();
  await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  const rows = tabs.get('VirtualA'); const k = rows.findIndex((r) => r[2] === 'SUMMARY');
  rows[k] = [...rows[k]]; rows[k][13] = String(Number(rows[k][13]) + 1);
  const st = S.statuses(await S.load(session, ID), result(), cfg);
  assert.equal(st.ledgers[0].state, 'OK');
  assert.ok(st.ledgers[0].reason_codes.includes('PRICE_REVISED'));
  assert.equal(st.ledgers[0].price_revised.session, rows[k][1]);
  // Drop the last recorded sessions so there is something to write: written from the recorded (changed) state.
  tabs.set('VirtualA', rows.filter((r, i) => i === 0 || r[1] <= '2026-10-27'));
  const kept = JSON.stringify(tabs.get('VirtualA'));
  const r = await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  assert.deepEqual(r.ledgers, ['set_a']);
  assert.equal(JSON.stringify(tabs.get('VirtualA').slice(0, JSON.parse(kept).length)), kept, 'recorded rows never rewritten');
  const appended = tabs.get('VirtualA').slice(JSON.parse(kept).length);
  assert.ok(appended.length > 0 && appended.every((x) => x[1] > '2026-10-27'));
  const firstCash = appended.find((x) => x[2] === 'SUMMARY')[13], replayed = S.ledgerStatus(S.setALedger({ ledgers: [] }, base(), cfg), base(), [], cfg, '2026-10-30').status.append_rows;
  assert.notEqual(firstCash, replayed.find((x) => x[1] === appended[0][1] && x[2] === 'SUMMARY')[13], 'continued from the recorded cash (+1), not the replay');
  // A malformed recorded row blocks writes (structural check kept).
  const broken = mockSheet();
  await S.record(broken.session, ID, { result: result(), kind: 'MOCK', now: NOW });
  const b = broken.tabs.get('VirtualA');
  broken.tabs.set('VirtualA', b.filter((x, i) => i === 0 || x[1] < '2026-10-28').map((x) => (x[2] === 'SUMMARY' && x[1] === '2026-10-27' ? [...x.slice(0, 13), 'abc', x[14]] : x)));
  const bst = S.statuses(await S.load(broken.session, ID), result(), cfg);
  assert.equal(bst.ledgers[0].state, 'SHEET_ROWS_INVALID');
  await assert.rejects(S.record(broken.session, ID, { result: result(), kind: 'MOCK', now: NOW }), /SHEET_ROWS_INVALID/);
  const header = mockSheet({ VirtualA: [[...S.LEDGER_HEAD.slice(0, -1), 'total']] });
  const sheet = await S.load(header.session, ID);
  assert.deepEqual([sheet.state, sheet.reason_codes, sheet.tab], ['ERROR', ['SHEET_HEADER_MISMATCH'], 'VirtualA']);
  await assert.rejects(S.record(header.session, ID, { result: result(), kind: 'MOCK', now: NOW }), /SHEET_HEADER_MISMATCH/);
  assert.equal(header.calls.filter((c) => c[0] === 'append' || c[0] === 'add').length, 0);
});

test('record: never before the start date, never a rehearsal, never with inputs not ready', async () => {
  const { session, calls } = mockSheet();
  await assert.rejects(S.record(session, ID, { result: result(), kind: 'MOCK', rehearsal: true }), /REHEARSAL_NOT_RECORDED/);
  await assert.rejects(S.record(session, ID, { result: { ...result(), rehearsal: true }, kind: 'MOCK' }), /REHEARSAL_NOT_RECORDED/);
  // Rehearsal mode (vt-signals-rehearsal) marks its results mode:'REHEARSAL': never written, not for REAL either.
  await assert.rejects(S.record(session, ID, { result: { ...result(), mode: 'REHEARSAL' }, kind: 'MOCK' }), /REHEARSAL_NOT_RECORDED/);
  await assert.rejects(S.record(session, ID, { result: { ...result(), mode: 'REHEARSAL' }, kind: 'REAL' }), /REHEARSAL_NOT_RECORDED/);
  // Decision 2026-10-11: today's public Q·G fill is rehearsal-only; a result carrying filled days is never recorded.
  await assert.rejects(S.record(session, ID, { result: { ...result(), qg_filled: ['2026-10-30'] }, kind: 'MOCK' }), /REHEARSAL_NOT_RECORDED/);
  await assert.rejects(S.record(session, ID, { result: { ...result(), rehearsal: { start_date: '2026-10-26', window: 5, qg_filled: [] } }, kind: 'MOCK' }), /REHEARSAL_NOT_RECORDED/);
  // A transient history failure (rate limit) waits: it is not written as a permanent NOT_AVAILABLE.
  const flaky = result(); flaky.sources = { ...flaky.sources, NVDA: { state: 'NOT_AVAILABLE', code: 'RATE_LIMITED', sessions: 0 } };
  assert.deepEqual(S.inputsIncomplete(flaky), ['NVDA']);
  assert.deepEqual(S.inputsIncomplete(result()), [], 'REQUEST_INVALID / NOT_REQUESTED are lasting states');
  await assert.rejects(S.record(session, ID, { result: flaky, kind: 'MOCK' }), /INPUTS_INCOMPLETE/);
  // A rehearsal-style input that replays sessions before 2026-10-19 is refused even when not flagged.
  const early = result(); early.ledgers.SET_A.input = { ...early.ledgers.SET_A.input, sessions: ['2026-10-16', ...early.ledgers.SET_A.input.sessions] };
  early.ledgers.SET_A.input.companies = Object.fromEntries(Object.entries(early.ledgers.SET_A.input.companies).map(([k, c]) => [k, { ...c, closes: { ...c.closes } }]));
  const st = S.statuses({ state: 'READY', reason_codes: [], tabs: {}, headerless: [], meta: { ledgers: [{ id: 'set_a', kind: 'SET_A', begin: '2026-10-12', end: null, target_basis: 'TARGET_V0', target_weights: early.ledgers.SET_A.input.target_weights, snapshot: null }], records: {}, user_target: null }, rows: {}, flags: [] }, early, cfg);
  assert.ok(st.ledgers[0].missing.every((d) => d >= '2026-10-19'), 'engine replays from the start date only');
  await assert.rejects(S.record(session, ID, { result: { state: 'NOT_STARTED', reason_codes: ['BEFORE_START_DATE'], ledgers: {} }, kind: 'MOCK' }), /BEFORE_START_DATE/);
  assert.equal(calls.filter((c) => c[0] === 'append' || c[0] === 'add').length, 0);
  // A RECORDING-mode result is written normally.
  assert.ok((await S.record(session, ID, { result: { ...result(), mode: 'RECORDING' }, kind: 'MOCK', now: NOW })).sessions > 0);
});

test('Set B: validated, a redefinition closes the old ledger and starts the next one after its recorded sessions', async () => {
  const { session, tabs } = mockSheet();
  await assert.rejects(S.saveSetB(session, ID, { nvda: '70', amd: '40' }, { purpose: PURPOSE }), /WEIGHT_SUM_OVER_100/);
  await assert.rejects(S.saveSetB(session, ID, {}, { purpose: PURPOSE }), /WEIGHTS_EMPTY/);
  await assert.rejects(S.saveSetB(session, ID, { nvda: '40' }), /PURPOSE_REQUIRED/, 'a one-line purpose is required at creation');
  await S.saveSetB(session, ID, { nvda: '40', msft: '35.5', hanmi: '24.5' }, { now: '2026-10-19T13:00:00Z', purpose: PURPOSE });
  await S.record(session, ID, { result: result(), kind: 'MOCK', now: NOW });
  const rows = await S.saveSetB(session, ID, { amd: '50' }, { now: '2026-10-29T01:00:00Z', purpose: PURPOSE });
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

test('user sets C/D and Set A versions: VirtualC/VirtualD tabs, ETF members, deletion closes only, Set A v1.1 example kept', async () => {
  const { session, tabs, calls } = mockSheet();
  await assert.rejects(S.saveSet(session, ID, 'SET_C', { tsla: '10' }, PURPOSE), /COMPANY_NOT_SUPPORTED/, 'outside the Worker allowlist');
  await assert.rejects(S.saveSet(session, ID, 'SET_C', Object.fromEntries(Object.keys(R.MEMBERS).slice(0, 31).map((c) => [c, '3'])), PURPOSE), /SET_MEMBERS_OVER_30/);
  await S.saveSet(session, ID, 'SET_C', { smh: '30', nvda: '20' }, 'ETF와 개별 종목 비교', { now: '2026-10-20T13:00:00Z' });
  await S.saveSet(session, ID, 'SET_D', { msft: '50' }, '단일 종목 기준선', { now: '2026-10-20T13:00:00Z' });
  const catalog = vector.inputs.catalog;
  await S.saveSetA(session, ID, { amd: '40', xlk: '10' }, { now: '2026-10-22T13:00:00Z', catalog });
  let sheet = await S.load(session, ID);
  assert.deepEqual(sheet.meta.ledgers.map((l) => [l.id, l.end, l.target_basis]), [['set_c-1', null, 'SET_C'], ['set_d-1', null, 'SET_D'], ['set_a', '2026-10-22', 'TARGET_V0'], ['set_a@v2', null, 'SET_A']]);
  const defs = S.definitions(sheet, catalog);
  assert.deepEqual([defs.SET_A.id, defs.SET_A.example, defs.SET_B, defs.SET_C.purpose, defs.count], ['set_a@v2', false, null, 'ETF와 개별 종목 비교', 3]);
  // Recording writes Set A v1.1 (until its close) and v2, C and D, each to its own tab.
  const withSets = R.assemble({ ...vector.inputs, sets: { SET_A: { target_weights: { amd: 40, xlk: 10 } }, SET_C: { target_weights: { smh: 30, nvda: 20 } }, SET_D: { target_weights: { msft: 50 } } } });
  const r = await S.record(session, ID, { result: withSets, kind: 'MOCK', now: NOW });
  assert.deepEqual(r.ledgers.sort(), ['set_a', 'set_a@v2', 'set_c-1', 'set_d-1']);
  assert.ok(tabs.get('VirtualC').length > 1 && tabs.get('VirtualD').length > 1);
  assert.ok(tabs.get('VirtualA').slice(1).every((x) => x[0] !== 'set_a' || x[1] < '2026-10-22'), 'the closed v1.1 ledger stops at its end');
  // Deleting set D only closes it ('종료'); its rows stay.
  const keptD = JSON.stringify(tabs.get('VirtualD'));
  const del = await S.deleteSet(session, ID, 'SET_D', { now: '2026-11-02T13:00:00Z' });
  assert.deepEqual([del[0][1], del[0][3], JSON.parse(del[0][10]).reason], ['set_d-1', 'LEDGER_CLOSE', 'SET_DELETED']);
  assert.equal(JSON.stringify(tabs.get('VirtualD')), keptD);
  sheet = await S.load(session, ID);
  assert.equal(S.active(sheet.meta, 'SET_D'), null);
  assert.equal(S.apply(withSets, sheet).ledgers.SET_D.state, 'NOT_AVAILABLE');
  await assert.rejects(S.deleteSet(session, ID, 'SET_D'), /SET_NOT_DEFINED/);
  assert.ok(calls.every((c) => c[0] !== 'append' || /^'Virtual/.test(c[1])));
});

test('TARGET and shadow snapshot: user target is the basis, re-sync closes the segment and keeps its rows', async () => {
  const { session, tabs } = mockSheet();
  const holdings = vector.inputs.holdings;
  const catalogWeights = Object.fromEntries(R.catalogTargets(vector.inputs.catalog).map((t) => [t.cid, t.weight]));
  await assert.rejects(S.startShadow(session, ID, holdings, { resync: true }), /SHADOW_NOT_STARTED/);
  await assert.rejects(S.startShadow(session, ID, { positions: {} }), /NO_ACTUAL/);
  // Decision 2026-10-11: no user target → the shadow ledger never falls back to TARGET v0.
  await assert.rejects(S.startShadow(session, ID, holdings, { now: '2026-10-20T13:00:00Z' }), /TARGET_NOT_AVAILABLE/);
  assert.equal(S.apply(result(), await S.load(session, ID)).ledgers.SHADOW.state, 'NOT_AVAILABLE');
  assert.equal(R.assemble({ ...vector.inputs, user_target: null }).ledgers.SHADOW.reason_codes[0], 'TARGET_NOT_AVAILABLE');
  assert.ok(catalogWeights);
  await S.saveTarget(session, ID, { nvda: '30', hanmi: '20', tokyo_electron: '10', msft: '20' }, { now: '2026-10-19T12:00:00Z' });
  const start = await S.startShadow(session, ID, holdings, { now: '2026-10-20T13:00:00Z' });
  assert.deepEqual([start[0][1], start[0][3], start[0][4]], ['shadow-1', 'LEDGER_START', '2026-10-20']);
  assert.equal(JSON.parse(start[0][10]).target_basis, 'USER_TARGET');
  await assert.rejects(S.startShadow(session, ID, holdings), /SHADOW_ALREADY_STARTED/);
  const shadowStatus = fixture.statuses.find((x) => x.name === 'shadow_segment');
  const r = await S.record(session, ID, { result: result(), kind: 'REAL', now: NOW });
  assert.deepEqual(r.ledgers, ['shadow-1']);
  assert.deepEqual(tabs.get('VirtualMine').slice(1), shadowStatus.expected.append_rows);
  assert.equal(tabs.get('VirtualA').length, 1, 'REAL record touches only the shadow ledger');
  const kept = JSON.stringify(tabs.get('VirtualMine'));
  const re = await S.startShadow(session, ID, holdings, { now: '2026-11-01T01:00:00Z', resync: true });
  assert.deepEqual(re.map((x) => [x[1], x[3], x[4] || x[5]]), [['shadow-1', 'LEDGER_CLOSE', '2026-10-31'], ['shadow-2', 'LEDGER_START', '2026-10-31']]);
  assert.equal(JSON.parse(re[1][10]).reason, 'RESYNC');
  assert.equal(JSON.stringify(tabs.get('VirtualMine')), kept, 're-sync never rewrites recorded rows');
  const sheet = await S.load(session, ID);
  assert.deepEqual(sheet.meta.ledgers.map((l) => [l.id, l.end]), [['shadow-1', '2026-10-31'], ['shadow-2', null]]);
  assert.deepEqual(S.statuses(sheet, result(), cfg).ledgers.filter((s) => s.kind === 'SHADOW').map((s) => [s.id, s.state]), [['shadow-1', 'OK'], ['shadow-2', 'NOT_STARTED']]);
  // Without a stored shadow ledger the preview uses the saved user target (the runner gets it from runnerOptions).
  const t = mockSheet();
  await S.saveTarget(t.session, ID, { nvda: '50' });
  const loaded = await S.load(t.session, ID);
  assert.deepEqual(plain(S.apply(R.assemble({ ...vector.inputs, user_target: loaded.meta.user_target }), loaded).ledgers.SHADOW.input.target_weights), { nvda: 50 });
  // "[세트 A 목표를 내 목표로 복사]": Set A's current weights (the v1.1 example here) become the user's target row.
  const c = mockSheet();
  const copied = await S.copySetATarget(c.session, ID, { catalog: vector.inputs.catalog, now: '2026-10-19T12:00:00Z' });
  assert.deepEqual(plain(copied), catalogWeights);
  assert.deepEqual(plain((await S.load(c.session, ID)).meta.user_target), catalogWeights);
  await S.saveSetA(c.session, ID, { amd: '40', xlk: '10' }, { catalog: vector.inputs.catalog, now: '2026-10-21T12:00:00Z' });
  assert.deepEqual(plain(await S.copySetATarget(c.session, ID, { catalog: vector.inputs.catalog })), { amd: 40, xlk: 10 }, 'the changed Set A version is copied');
});

test('flags from VirtualFlags reach the runner input; module has no console/storage/network use', () => {
  const src = fs.readFileSync(path.join(__dirname, '../src/investment_system/product/web_assets/virtual-ledger-sheets.js'), 'utf8');
  for (const bad of ['console.', 'localStorage', 'sessionStorage', 'indexedDB', 'fetch(', 'XMLHttpRequest', 'sendBeacon']) assert.ok(!src.includes(bad), bad);
  assert.ok(src.includes("engine().disclaimerHtml('ko-KR')") && VT.DISCLAIMER.ko === '가상 · 실제 추천 아님 · 주문 기능 없음');
  const out = R.assemble({ ...vector.inputs, flags: S.parseFlags(fixture.flags[0].values).flags });
  assert.deepEqual(out.ledgers.SET_A.input.flags.map((f) => f.company), ['googl', 'nvda', 'tokyo_electron', 'rok']);
});
