'use strict';
// New frontend P1 · engine wiring (web_app/engines.js) on the real old modules: TARGET v1, playbook, virtual trading, macro lights.
//  - TARGET (2026-11-15, DC-31: the central V only): the draft equals the one TargetV1Builder makes from officialComputed of the
//    publication data.official() validated (no device price); the builder gets the old screen's arguments plus that publication
//    (spies); without a usable one (not published, stale on the New York clock, another calc_version) nothing is drafted, built or
//    selected and finalize is BLOCKED with OFFICIAL_V_REQUIRED; finalize re-checks against the RAW published JSON (data.peek),
//    regenerates a draft on a changed basis or V source (a saved device draft loads and is regenerated), and saves only
//    OFFICIAL_CENTRAL versions; every write needs a trusted click (CLICK_REQUIRED, storage unchanged); price paths are SYNC clicks on
//    PriceStore with the one price view.
//  - Playbook: judge() reproduces openPanel's R1_FILING rule (playbook_screen_browser_test 'manual R1') and its macro
//    reference-only display without writing, equals the old openPanel's judgement, and record(event) writes what openPanel wrote
//    on open; a judgement says recorded:false / JUDGEMENT_NOT_RECORDED until its occurrences are in the store, then recorded:true
//    (owner 2026-10-24: recorded only on the click), read from the store, so a judgement made again, after a reload too, says the
//    same; NOTHING_TO_RECORD when there is no occurrence to write; facts() reads the page's central result (DC-31: the official V,
//    v_prev20 NA with V_HISTORY_NOT_PUBLISHED) after the news list; TARGET reads the central V (no forEngines).
//  - One event, one top-level action: syncScoringPrices' tab sync is a nested step presenting its SYNC action's signal.
//  - Virtual: stored() is the runner's open pass on the price view with fetch:false (NOT_AVAILABLE before sign-in with zero
//    requests; PRICE_NOT_FETCHED after it with zero private requests); compare / forward / rehearse; run() is NOT_IN_P1.
//  - Macro: MacroLights.setPublic once per public data generation.
// Synthetic data only: sentinel prices are made-up decimals, the forward ledger is price free.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const nodeCrypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');

const QGV2 = 'sec-qgv2.json', DATE = '2026-10-20', WORKER = 'https://private-investment-history.kco994553.workers.dev';
const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
// The synthetic central V publication (tests/fixtures/qgv_official_vectors_v1.json base_text; its input as_of = the fixture's).
const PUB_TEXT = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
const CODES = { schema: 'universe-codes/1', codes: JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/universe/universe_codes_v1.json'), 'utf8')) };
const TOKEN = ['memory', 'only', 'synthetic', 'engines'].join('-'), SCOPE = 'https://www.googleapis.com/auth/drive.file email';
// Universe-tab prices of the fixture (every LIVE code but MSFT, plus NVDA, as qgv_v2_fixture.strictUniverseValues), made-up decimals.
const SENTINEL = /\.0731946/;
function universe() {
  const prices = new Map(); let i = 0;
  for (const [code, r] of Object.entries(F.strictPayload().records)) if (r.state === 'LIVE' && code !== 'NASDAQ:MSFT') prices.set(code, { price: 15 + ((i++ * 17) % 80) + 0.0731946, currency: 'USD' });
  prices.set('NASDAQ:NVDA', { price: 42.0731946, currency: 'USD' });
  return { prices, view: { prices: () => prices, priceBasis: () => ({ source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_sentinel', acquired_at: '2026-10-18T09:00:00.000Z', currency: 'USD', price_time: null }), readStatus: () => null } };
}
// The price-free public forward ledger of virtual_trading_runner_browser_test (synthetic Q·G rows, TARGET v0 units).
const IDS = ['asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl', 'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok'];
const UNITS = { asml: 900, lrcx: 600, klac: 550, tokyo_electron: 500, hanmi: 450, nvda: 800, amd: 500, avgo: 500, qcom: 400, intc: 300, msft: 700, googl: 700, amzn: 600, rtx: 600, stry: 550, etn: 500, hubb: 350, gev: 300, rok: 200 };
const V1 = 'forward_validation/v1', VV = 'forward_validation/v1+dcf_v1_default', H = 'd'.repeat(64), SESSIONS = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22'];
function ledger() {
  const record = (date) => { const companies = {}; IDS.forEach((id, i) => { companies[id] = { state: 'LIVE', Q: { score: 50 + i, coverage: 'READY', missing_factor_count: 0 }, G: { score: 60 - i / 2, coverage: 'READY', missing_factor_count: 0 } }; });
    return { date, version: V1, strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', state: 'RECORDED', reason_codes: [], target: { portfolio_id: 'TARGET', version: 'v0', root_sha256: H, total_units: 10000, weights_units: { ...UNITS } },
      qg_as_of: date + 'T22:10:00+00:00', qg_screen_state: 'LIVE', companies, source_sha256: { 'sec-qg-factors.json': H, 'actual-catalog.json': H }, created_at: date + 'T22:30:00+00:00' }; };
  return { schema_version: 1, kind: 'FORWARD_VALIDATION_LEDGER', start_date: '2026-10-19', status: 'ACTIVE', as_of: SESSIONS.at(-1) + 'T22:31:00+00:00', strategy: 'QGV_STANDARD_V1', calibration: 'UNCALIBRATED', holdout: 'UNCONFIRMED_NOT_USED', price_free: true,
    target: { portfolio_id: 'TARGET', version: 'v0' }, versions: { [V1]: SESSIONS.map(record), [VV]: [] }, version_status: { [V1]: { state: 'ACTIVE', v_included: false, reason_codes: [] }, [VV]: { state: 'NOT_AVAILABLE', v_included: true, reason_codes: ['V_REQUIRES_DEVICE_PRICES'] } } };
}
function memoryStorage(seed = {}) {
  const m = new Map(Object.entries(seed));
  return { map: m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => { m.set(k, String(v)); }, removeItem: (k) => { m.delete(k); }, clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; } };
}
// GIS stand-in (the CSP-allowed script is never loaded in node): the token answer arrives inside the click.
const gis = () => ({ accounts: { oauth2: { initTokenClient(cfg) { return { requestAccessToken() { cfg.callback({ access_token: TOKEN, expires_in: 3600, token_type: 'Bearer', scope: SCOPE }); } }; }, revoke(_t, done) { if (done) done({}); } } } });
const fresh = (name) => { delete require.cache[require.resolve(R.newPath(name))]; return R.requireNew(name); };
const plain = (v) => JSON.parse(JSON.stringify(v));
/* One page: a browser-like window, the reused old modules (index.html order), fresh P1 modules. The QGV accessor reads the Universe
   tab above (no price click in these tests); every other price path goes through the real price layer. */
// ny: the New York day / minutes QgvOfficial.usable counts sessions with (engines' test seam); default one day after the
// publication's basis day 2026-10-13, so the synthetic publication is fresh.
const NY = Object.freeze({ date: '2026-10-14', minutes: 720 });
function env({ files = {}, ny = NY } = {}) {
  const table = { [QGV2]: { json: F.strictPayload() }, 'actual-catalog.json': { json: CATALOG }, 'universe-codes.json': { json: CODES }, 'forward-validation-ledger.json': { json: ledger() }, 'qgv-official.json': { body: PUB_TEXT }, ...files };
  const win = R.nodeWindow({ files: (name) => table[name] || null }), mods = R.loadOld(win);
  win.InvestmentAppConfig = Object.freeze({ ...mods.InvestmentAppConfig, virtualTradingRequestSpacingMs: 0 });
  win.localStorage = memoryStorage(); win.sessionStorage = memoryStorage(); win.google = gis();
  win.crypto = { randomUUID: () => nodeCrypto.randomUUID(), subtle: globalThis.crypto.subtle };
  const U = universe(), action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action });
  const prices = fresh('prices.js').create({ win, action, data }), store = fresh('store.js').create({ win, action, data });
  const qgv = fresh('qgv.js').create({ win, data, action, prices: { universeView: U.view, storeFacade: prices.storeFacade, subscribe: prices.subscribe } });
  const engines = fresh('engines.js').create({ win, action, data, prices, store, qgv, nyNow: () => ny });
  return { win, mods, table, U, action, data, prices, store, qgv, engines, click: () => win.trusted('click'), priv: () => win.requests.filter((r) => /^https?:\/\//.test(r.name)), saved: () => win.localStorage.getItem(mods.PlaybookScreen.KEY) };
}
// Records every call of the named functions of an old module (same function, same arguments), installed on the window.
function spy(e, global, names) {
  const M = e.win[global], calls = Object.fromEntries(names.map((n) => [n, []])), wrapped = { ...M };
  for (const n of names) wrapped[n] = (...a) => { calls[n].push(a); return M[n](...a); };
  e.win[global] = Object.freeze(wrapped); return calls;
}
const NOT_CLICKS = [undefined, new Event('click'), { type: 'click', isTrusted: true }];

// ---------------------------------------------------------------- TARGET v1
test('TARGET draft (2026-11-15, central V only): the draft TargetV1Builder makes from officialComputed of the publication data.official() validated; same builder arguments; none without a usable publication', async () => {
  const e = env(), { mods, qgv, data, engines } = e, TB = mods.TargetV1Builder, calls = spy(e, 'TargetV1Builder', ['buildDraft']);
  const pg = await qgv.page(), inputs = data.get(QGV2), off = await data.official();
  assert.equal(pg.state, 'READY'); assert.equal(inputs.as_of, F.strictPayload().as_of); assert.equal(off.state, 'OFFICIAL'); assert.equal(mods.QgvOfficial.state(off.payload), 'OFFICIAL');
  const got = await engines.target.draft({ date: DATE });
  // Reference without the engines: TargetV1Builder.buildDraft over officialComputed of the same publication (no device price, no compute).
  const computed = TB.officialComputed(off.payload);
  const ref = TB.buildDraft({ computed, inputs, universeCodes: CODES.codes, existing: mods.TargetV1Screen.existingSymbols(CATALOG), date: DATE, basis: null, official: off.payload, cfg: mods.TargetV1ConfigDefaults });
  assert.deepEqual(got, plain(ref), 'the builder\'s central draft');
  assert.equal(got.v_source, 'OFFICIAL_CENTRAL'); assert.deepEqual(got.official, plain(TB.officialRecord(off.payload)));
  assert.equal(got.official.price_basis_date, off.payload.times.price_basis_date, 'the publication\'s own price basis day, as published');
  assert.ok(got.pool.length >= 5 && got.eligible_count === got.pool.length, 'fixture gives a real candidate pool');
  assert.equal(calls.buildDraft.length, 1); const [a] = calls.buildDraft[0];
  assert.deepEqual(Object.keys(a).sort(), ['basis', 'cfg', 'computed', 'date', 'existing', 'inputs', 'official', 'universeCodes']);
  assert.equal(a.computed, computed); assert.equal(a.official, off.payload); assert.notEqual(a.computed, qgv.centralComputed(pg), 'the builder\'s own adapter of the publication'); assert.equal(a.inputs, inputs); assert.equal(a.cfg, mods.TargetV1ConfigDefaults);
  assert.deepEqual([...a.universeCodes], CODES.codes); assert.deepEqual(a.existing, mods.TargetV1Screen.existingSymbols(CATALOG)); assert.equal(a.date, DATE); assert.equal(a.basis, null);
  assert.equal(qgv.forEngines, undefined, 'no hidden device result');
  assert.ok(Object.isFrozen(got) && Object.isFrozen(got.pool[0]));
  assert.ok(!SENTINEL.test(JSON.stringify(got)), 'no device price in the draft');
  await assert.rejects(engines.target.draft({ date: 'x' }), /DATE_INVALID/);
  // Only a page from qgv.page(): a look-alike (a preview, a plain object) is a fixed code, never a TypeError on its fields.
  for (const page of [qgv.preview(pg, JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_v2_custom_vectors_v1.json'), 'utf8')).cases[0].input.weights), { v_source: { id: 'OFFICIAL_CENTRAL' } }])
    for (const call of [() => engines.target.draft({ date: DATE, page }), () => engines.target.basis({ page })]) await assert.rejects(call(), /^Error: PAGE_UNKNOWN$/);
  // No usable central V → no draft (never one from another V): not published, stale on the New York clock, another calc_version.
  const later = { ...F.strictPayload(), calc_version: 'qgv2-calc/2026-10-23.2' };
  for (const [opts, reason] of [[{ files: { 'qgv-official.json': null } }, 'OFFICIAL_NOT_PUBLISHED'], [{ ny: { date: '2026-10-19', minutes: 720 } }, 'OFFICIAL_STALE'], [{ files: { [QGV2]: { json: later } }, peekOnly: true }, 'OFFICIAL_CALC_VERSION_DIFFERS']]) {
    const x = env(opts); await x.qgv.page(); if (opts.peekOnly) x.table[QGV2] = { json: later };
    await assert.rejects(x.engines.target.draft({ date: DATE }), (err) => err.message === 'OFFICIAL_V_REQUIRED' && err.reason === reason, reason);
  }
  assert.deepEqual(e.priv(), []);
});

test('TARGET writes: build / answer / R-B only in a trusted click (storage unchanged otherwise); build keeps the raw-file basis; no usable central V → nothing built or selected', async () => {
  const e = env(), { mods, engines, data } = e, TB = mods.TargetV1Builder, cfg = mods.TargetV1ConfigDefaults;
  for (const ev of NOT_CLICKS) {
    assert.throws(() => engines.target.build(ev, { date: DATE }), /CLICK_REQUIRED/);
    assert.throws(() => engines.target.answer(ev, { symbol: 'NVDA', answer: 'AGREE', date: DATE }), /CLICK_REQUIRED/);
    assert.throws(() => engines.target.selectRuleB(ev, { date: DATE }), /CLICK_REQUIRED/);
    assert.throws(() => engines.target.finalize(ev, { date: DATE }), /CLICK_REQUIRED/);
  }
  assert.equal(e.saved(), null, 'nothing written');
  assert.deepEqual(engines.target.state(), plain(TB.emptyState()));
  const basis = await engines.target.basis();
  assert.deepEqual(basis, await TB.inputBasis(F.strictPayload()), 'basis of the raw published file (same as_of as the page inputs)');
  const draft = await engines.target.build(e.click(), { date: DATE });
  assert.deepEqual(engines.target.state().draft, draft); assert.deepEqual(draft, await engines.target.draft({ date: DATE, basis }));
  assert.equal(draft.v_source, 'OFFICIAL_CENTRAL', 'the saved draft is the central V\'s'); assert.equal((await engines.target.blockers({ date: DATE })).v_source, 'OFFICIAL_CENTRAL'); assert.equal((await engines.target.blockers({ date: DATE })).official_reason, null);
  assert.ok(draft.basis && draft.basis.shard_count === F.strictPayload().shard_count);
  // A card answer: the old judgement record (TV1-… id, the builder's record) and the latest answer per name.
  const sel = TB.currentSelection(engines.target.state(), cfg), name = sel.rows.find((r) => !mods.TargetV1Screen.existingSymbols(CATALOG).includes(r.symbol)).symbol;
  const a = await engines.target.answer(e.click(), { symbol: name, answer: 'AGREE', date: DATE });
  assert.equal(a.symbol, name); assert.deepEqual(engines.target.state().answers, [{ symbol: name, answer: 'AGREE', reason: '', date: DATE }]);
  const rec = mods.PlaybookScreen.read(e.win.localStorage).records.at(-1);
  assert.match(rec.id, new RegExp('^TV1-' + DATE + '-' + name.replace('.', '\\.') + '-AGREE-')); assert.equal(rec.primary_code, cfg.cards.record_primary_code); assert.equal(rec.symbol, name);
  assert.throws(() => engines.target.answer(e.click(), { symbol: name, answer: 'DISAGREE', reason: '', date: DATE }), /DISAGREE_REASON_REQUIRED/);
  // Rebuilding over answers needs reset:true (the old button's second tap); without it nothing changes.
  const before = e.saved();
  await assert.rejects(engines.target.build(e.click(), { date: DATE }), /TARGET_V1_ANSWERS_RESET/); assert.equal(e.saved(), before);
  await engines.target.build(e.click(), { date: DATE, reset: true }); assert.deepEqual(engines.target.state().answers, []);
  // R-B on a due day: the builder's universeRows / exclusions / ruleBSegment over the central V; written only when ready.
  assert.equal(engines.target.ruleBDue(DATE), TB.ruleBDue(engines.target.state(), DATE, cfg));
  const st = e.saved(), r = await engines.target.selectRuleB(e.click(), { date: DATE });
  if (r.state === 'SELECTED') { assert.equal(engines.target.state().rule_b.length, 1); assert.equal(engines.target.state().rule_b[0].v_source, 'OFFICIAL_CENTRAL'); assert.equal(r.v_source, 'OFFICIAL_CENTRAL'); }
  else { assert.equal(r.state, 'NOT_READY'); assert.equal(e.saved(), st); }
  // A saved R-B row of the earlier device source still passes the state check (validateState fixes only date and rows of a row).
  const withRow = { ...engines.target.state(), rule_b: [{ date: DATE, rows: [{ symbol: 'NVDA', pct: 10 }], v_source: 'DEVICE_TEMPORARY' }] };
  assert.doesNotThrow(() => TB.validateState(withRow));
  assert.equal(data.get(QGV2).as_of, draft.v2_as_of); assert.deepEqual(e.priv(), []); assert.equal(e.action.blocked(), 0);
  // Without a usable central V (stale on the New York clock): build is refused and R-B is not selected; nothing is written.
  const x = env({ ny: { date: '2026-10-19', minutes: 720 } }); await x.qgv.page();
  await assert.rejects(x.engines.target.build(x.click(), { date: DATE }), (err) => err.message === 'OFFICIAL_V_REQUIRED' && err.reason === 'OFFICIAL_STALE');
  assert.deepEqual(await x.engines.target.selectRuleB(x.click(), { date: DATE }), { state: 'OFFICIAL_V_REQUIRED', reason: 'OFFICIAL_STALE' }); assert.equal(x.saved(), null);
});

test('TARGET finalize: re-checks the RAW published JSON (data.peek) and the central V, regenerates on a changed basis or V source, saves only OFFICIAL_CENTRAL versions; no usable central V → BLOCKED (OFFICIAL_V_REQUIRED)', async () => {
  const e = env(), { mods, engines, qgv, data } = e, TB = mods.TargetV1Builder, raw = F.strictPayload();
  const pg = await qgv.page(), off = await data.official(), rec = TB.officialRecord(off.payload); await engines.target.build(e.click(), { date: DATE });
  const calls = spy(e, 'TargetV1Builder', ['finalizeBlockers', 'finalize', 'inputBasis', 'regenerateDraft']), before = e.saved();
  const f = await engines.target.finalize(e.click(), { date: DATE });
  assert.equal(f.outcome, 'BLOCKED'); assert.ok(f.blockers.includes('TARGET_V1_CARDS_PENDING') && f.blockers.includes('Q_COVERAGE_LOW'), f.blockers.join(',')); assert.ok(!f.blockers.includes('OFFICIAL_V_REQUIRED')); assert.equal(f.official_reason, null);
  assert.equal(e.saved(), before, 'a blocked finalize writes nothing');
  for (const [name, at] of [['finalizeBlockers', 1], ['finalize', 1], ['inputBasis', 0]]) {
    const p = name === 'inputBasis' ? calls[name][0][0] : calls[name][0][at].published;
    assert.deepEqual(p, raw, name + ' gets the raw published file'); assert.notEqual(p, data.get(QGV2));
    assert.equal(p.kind, 'SEC_QGV2'); assert.ok(Object.values(p.records).every((r) => !('qg_axes' in r)), 'not the Qgv2Inputs value');
  }
  assert.equal(calls.finalizeBlockers[0][1].official, off.payload); assert.equal(calls.finalize[0][1].official, off.payload, 'the central V usable now');
  assert.deepEqual(calls.finalize[0][1].basis, await TB.inputBasis(raw)); assert.equal(calls.finalize[0][1].cfg, mods.TargetV1ConfigDefaults); assert.equal(calls.finalize[0][1].date, DATE);
  assert.deepEqual((await engines.target.blockers({ date: DATE })).blockers, f.blockers);
  // While the file cannot be re-read there is no calc_version to match the central V against: no build (nothing written).
  e.table[QGV2] = { status: 500, body: '' }; const unread = e.saved();
  await assert.rejects(engines.target.build(e.click(), { date: DATE, reset: true }), (err) => err.message === 'OFFICIAL_V_REQUIRED' && err.reason === 'OFFICIAL_CALC_VERSION_DIFFERS'); assert.equal(e.saved(), unread);
  e.table[QGV2] = { json: raw };
  // A saved draft without a basis (one from before the basis was kept): finalize regenerates it from the central V (answers kept).
  const nob = JSON.parse(e.saved()); nob.target_v1.draft.basis = null; e.win.localStorage.setItem(mods.PlaybookScreen.KEY, JSON.stringify(nob));
  assert.equal(engines.target.state().draft.basis, null);
  const g = await engines.target.finalize(e.click(), { date: DATE });
  assert.equal(g.outcome, 'DRAFT_REGENERATED'); assert.deepEqual(engines.target.state().draft.basis, await TB.inputBasis(raw));
  assert.equal(engines.target.state().draft.v_source, 'OFFICIAL_CENTRAL', 'a regenerated draft is the central V\'s');
  const [, o] = calls.regenerateDraft[0]; assert.equal(o.computed, TB.officialComputed(off.payload)); assert.equal(o.official, off.payload); assert.equal(o.inputs, qgv.engineInputs(pg)); assert.equal(o.date, DATE);
  // A saved draft of the earlier device source (before 2026-11-15) still loads; finalize calls it V_SOURCE_CHANGED and regenerates
  // it from the central V.
  const legacy = JSON.parse(e.saved()); delete legacy.target_v1.draft.official; legacy.target_v1.draft.v_source = 'DEVICE_TEMPORARY'; e.win.localStorage.setItem(mods.PlaybookScreen.KEY, JSON.stringify(legacy));
  assert.equal(engines.target.state().draft.v_source, 'DEVICE_TEMPORARY'); assert.ok((await engines.target.blockers({ date: DATE })).blockers.includes('V_SOURCE_CHANGED'));
  const h = await engines.target.finalize(e.click(), { date: DATE }); assert.equal(h.outcome, 'DRAFT_REGENERATED'); assert.equal(engines.target.state().draft.v_source, 'OFFICIAL_CENTRAL');
  // No usable central V (stale on the New York clock): BLOCKED with OFFICIAL_V_REQUIRED and why; nothing regenerated or saved.
  const x = env({ ny: { date: '2026-10-19', minutes: 720 } }); x.win.localStorage.setItem(mods.PlaybookScreen.KEY, e.saved()); const xs = x.saved();
  const w = await x.engines.target.finalize(x.click(), { date: DATE }); assert.equal(w.outcome, 'BLOCKED'); assert.ok(w.blockers.includes('OFFICIAL_V_REQUIRED')); assert.equal(w.official_reason, 'OFFICIAL_STALE'); assert.equal(x.saved(), xs);
  assert.equal((await x.engines.target.blockers({ date: DATE })).official_reason, 'OFFICIAL_STALE');
  // A version that passes is saved only when the builder wrote the central source; any other (or none) is V_SOURCE_MISMATCH.
  const B = mods.TargetV1Builder, pass = (extra) => Object.freeze({ ...B, finalizeBlockers: () => ({ blockers: [], check: { reasons: [] }, basis_changed: false }),
    finalize: (s, y) => ({ ...s, versions: [...s.versions, { version: 'v1', date: y.date, rows: [{ symbol: 'NVDA', pct: 10 }], ...extra }], rule_c: { start: y.date, version: 'v1' } }) });
  for (const bad of [{ v_source: 'ELSEWHERE' }, {}, { v_source: 'DEVICE_TEMPORARY' }]) {
    e.win.TargetV1Builder = pass(bad); const keep = e.saved();
    await assert.rejects(engines.target.finalize(e.click(), { date: DATE }), /V_SOURCE_MISMATCH/, JSON.stringify(bad)); assert.equal(e.saved(), keep);
  }
  e.win.TargetV1Builder = pass({ v_source: 'OFFICIAL_CENTRAL', publication_id: rec.publication_id, price_basis_date: rec.price_basis_date, official_inputs_as_of: rec.inputs_as_of });
  const ok = await engines.target.finalize(e.click(), { date: DATE });
  assert.equal(ok.outcome, 'FINALIZED'); assert.equal(Object.hasOwn(pg, 'engine_v_source'), false);
  assert.equal(engines.target.state().versions.at(-1).v_source, 'OFFICIAL_CENTRAL'); assert.equal(engines.target.state().versions.at(-1).price_basis_date, off.payload.times.price_basis_date); assert.deepEqual(ok.version, engines.target.state().versions.at(-1));
  const kept = e.saved();
  await assert.rejects(engines.target.finalize(e.click(), { date: DATE, page: { v_source: { id: 'OFFICIAL_CENTRAL' } } }), /PAGE_UNKNOWN/); assert.equal(e.saved(), kept);
  assert.deepEqual(e.priv(), []);
});

test('TARGET prices: syncScoringPrices / compare only in a SYNC click, PriceStore with the one price view (syncMany TV1 allowlist only)', async () => {
  const e = env(), { mods, engines, prices } = e, cfg = mods.TargetV1ConfigDefaults;
  await engines.target.build(e.click(), { date: DATE });
  const sel = mods.TargetV1Builder.currentSelection(engines.target.state(), cfg), name = sel.rows.find((r) => !mods.TargetV1Screen.existingSymbols(CATALOG).includes(r.symbol)).symbol;
  await engines.target.answer(e.click(), { symbol: name, answer: 'AGREE', date: DATE });
  const p = await engines.target.scoringPending();
  assert.deepEqual(p.pending.map((n) => n.symbol), [name]); assert.equal(p.confirm_text, mods.TargetV1Screen.confirmText(p.pending, cfg), 'the old confirm text (symbols only)');
  for (const ev of NOT_CLICKS) { assert.throws(() => engines.target.syncScoringPrices(ev), /CLICK_REQUIRED/); assert.throws(() => engines.target.compare(ev, { date: DATE }), /CLICK_REQUIRED/); }
  const calls = spy(e, 'PriceStore', ['syncMany', 'dailyCloses']), before = e.saved();
  const r = await engines.target.syncScoringPrices(e.click());
  assert.equal(calls.syncMany.length, 1); const [view, symbols, interval, o] = calls.syncMany[0];
  assert.equal(view, prices.priceView); assert.deepEqual(symbols, mods.TargetV1Builder.addPriceSymbols(engines.target.state(), p.pending, cfg).price_symbols); assert.equal(interval, '1d');
  assert.equal(o.kind, 'TV1'); assert.equal(o.allowlistOnly, true);
  // That sync was a nested step (it presented the SYNC action's signal): the same event without it is refused.
  const ev = e.click();
  await assert.rejects(e.action.run(ev, 'SYNC', async () => { await null; return prices.syncSymbols(ev, ['SPY'], '1d'); }), /ACTION_ALREADY_STARTED/);
  await assert.rejects(e.action.run(e.click(), 'SYNC', async () => { await new Promise((r) => setImmediate(r)); return prices.syncSymbols(ev, ['SPY'], '1d'); }), /CLICK_REQUIRED/, 'nor an earlier event later');
  assert.equal(calls.syncMany.length, 1, 'neither reached PriceStore');
  assert.notEqual(r.state, 'READY', 'no sheet or sign-in here: the store says why'); assert.equal(e.saved(), before, 'symbols kept only after a READY sync');
  const c = await engines.target.compare(e.click(), { date: DATE });
  assert.ok(calls.dailyCloses.length >= 1 && calls.dailyCloses.every(([, , x]) => x.view === prices.priceView && x.fetch === true));
  assert.ok(calls.dailyCloses.some(([s]) => s === cfg.virtual_sets.benchmark.symbol));
  assert.equal(c.compare.A.state, 'NOT_AVAILABLE'); assert.equal(c.compare.A.reason, 'R_C_NOT_STARTED'); assert.equal(c.review.state, 'NOT_DUE');
  assert.equal(await engines.target.refreshScoring(), 0, 'no tracked name, nothing read');
  assert.deepEqual(e.priv(), [], 'not signed in: no request left');
  const src = fs.readFileSync(R.newPath('engines.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '$1');
  assert.equal((src.match(/\bfetch\s*:\s*true\b/g) || []).length, 1, 'one price fetch, inside the SYNC compare action');
  assert.doesNotMatch(src, /\b(?:localStorage|sessionStorage|indexedDB|setItem|removeItem|sessionFor)\b/, 'engines own no storage or session');
});

// ---------------------------------------------------------------- playbook
const MANUAL = { held: true, data: { price_missing: false, fx_missing: false, snapshot_missing: false }, coverage: 'READY', quarterly_check_due: true, memberships: {}, q_now: 70, g_now: 60, q_prev: 70, g_prev: 60, macro_state: 'NORMAL', structural_news: true };
// A host for the old openPanel without a DOM: openPanel judges and records before it draws, then wires handlers on these stubs.
function stubHost() { const el = () => ({ elements: { namedItem: () => null }, addEventListener() {}, querySelectorAll: () => [], textContent: '' }); return { set innerHTML(v) { this.html = v; }, querySelector: el, querySelectorAll: () => [] }; }

test('playbook judge: openPanel R1_FILING rule (manual R1) reproduced without writing; same judgement as openPanel; record(event) writes what it wrote', async () => {
  const e = env(), { mods, engines, store } = e, P = mods.PlaybookScreen;
  await store.saveThesis(e.click(), 'SYNTHETIC', 'Synthetic reason', 'Synthetic condition', { status: 'OCCURRED', source: 'Synthetic news link', grade: 'SIGNAL' });
  const before = e.saved();
  const j = await engines.playbook.judge({ symbol: 'SYNTHETIC', date: '2026-10-13', situation: MANUAL });
  assert.equal(j.code, 'R1'); assert.equal(j.judgement.primary.code, 'R1'); assert.equal(j.v_source, null, 'a caller situation that names no V source');
  const filing = j.judgement.choices_by_code.R1.find((c) => c.id === 'R1_FILING');
  assert.equal(filing.enabled, false); assert.ok(filing.disabled_reasons.includes('FILING_EVIDENCE_REQUIRED'), 'a SIGNAL-grade event cannot back a filing choice');
  assert.equal(j.judgement.choices.find((c) => c.id === 'R1_FILING').enabled, false);
  assert.ok(j.judgement.choices_by_code.R1.some((c) => c.id === 'R1_NEWS' && c.enabled), 'R1_NEWS stays open');
  assert.equal(mods.PlaybookConfigDefaults.codes.find((c) => c.code === 'E4').information_only, true, 'E4 is information only (no verdict)');
  assert.equal(e.saved(), before, 'judge writes nothing');
  assert.deepEqual([j.recorded, j.recorded_reason], [false, 'JUDGEMENT_NOT_RECORDED'], 'not recorded until the click (shown as 기록 안 됨)');
  assert.equal(e.qgv.reasonText(j.recorded_reason), '기록 안 됨');
  assert.deepEqual([plain(j).recorded, plain(j).recorded_reason], [false, 'JUDGEMENT_NOT_RECORDED'], 'in its JSON too');
  // The old openPanel on a copy of the same device record: the same judgement, and the occurrences it wrote on open.
  const copy = memoryStorage({ [P.KEY]: before }), old = P.openPanel(stubHost(), { symbol: 'SYNTHETIC', date: '2026-10-13', storage: copy, situation: MANUAL });
  assert.deepEqual(j.judgement, plain(old)); assert.notEqual(copy.getItem(P.KEY), before, 'openPanel wrote on open');
  for (const ev of NOT_CLICKS) assert.throws(() => engines.playbook.record(ev, j), /CLICK_REQUIRED/);
  assert.throws(() => engines.playbook.record(e.click(), plain(j)), /JUDGEMENT_UNKNOWN/);
  assert.equal(j.recorded, false, 'a refused record leaves it unrecorded');
  const occ = await engines.playbook.record(e.click(), j);
  assert.deepEqual([j.recorded, j.recorded_reason], [true, null], 'the same judgement now reads recorded');
  const again = await engines.playbook.judge({ symbol: 'SYNTHETIC', date: '2026-10-13', situation: MANUAL });
  assert.deepEqual([again.recorded, again.recorded_reason], [true, null], 'judged again (a re-render, back on the panel): its occurrences are stored, so recorded');
  assert.deepEqual([plain(again).recorded, plain(again).recorded_reason], [true, null]);
  const once = e.saved(); assert.deepEqual(plain(await engines.playbook.record(e.click(), again)), plain(occ)); assert.equal(e.saved(), once, 'recording it again changes nothing (one per date, name, code)');
  assert.equal(again.recorded, true);
  // After a reload (a new layer on the same device storage) the stored occurrences still say recorded; another day does not.
  const reloaded = fresh('engines.js').create({ win: e.win, action: e.action, data: e.data, prices: e.prices, store, qgv: e.qgv });
  const r1 = await reloaded.playbook.judge({ symbol: 'SYNTHETIC', date: '2026-10-13', situation: MANUAL }), r2 = await reloaded.playbook.judge({ symbol: 'SYNTHETIC', date: '2026-10-14', situation: MANUAL });
  assert.deepEqual([r1.recorded, r1.recorded_reason, r2.recorded, r2.recorded_reason], [true, null, false, 'JUDGEMENT_NOT_RECORDED'], 'read from the store, not from this page');
  // A stored occurrence of the same code that lacks one of the reasons record() would add is not the judgement recorded.
  const partial = P.read(e.win.localStorage); partial.occurrences = partial.occurrences.map((o) => ({ ...o, reasons: o.reasons.filter((x) => x !== 'NEWS_STRUCTURAL_EVENT') }));
  await e.action.run(e.click(), 'WRITE', () => P.write(e.win.localStorage, partial));
  assert.deepEqual([j.recorded, j.recorded_reason], [false, 'JUDGEMENT_NOT_RECORDED'], 'the same object follows the store');
  await engines.playbook.record(e.click(), j); assert.deepEqual([j.recorded, again.recorded, r1.recorded], [true, true, true]);
  // Nothing to record (no candidate signal, no structural news, no 13F exit): its own reason, never "recorded".
  const quiet = await engines.playbook.judge({ symbol: 'SYNQUIET', date: '2026-10-13', situation: { ...MANUAL, structural_news: false } });
  assert.deepEqual(quiet.judgement.candidate_signals, [], 'fixture: no candidate signal');
  assert.deepEqual([quiet.recorded, quiet.recorded_reason], [false, 'NOTHING_TO_RECORD']); assert.equal(e.qgv.reasonText('NOTHING_TO_RECORD'), '기록할 발생 신호 없음');
  const beforeQuiet = P.read(e.win.localStorage).occurrences; await engines.playbook.record(e.click(), quiet);
  assert.deepEqual(P.read(e.win.localStorage).occurrences, beforeQuiet, 'recording it adds no occurrence'); assert.equal(quiet.recorded_reason, 'NOTHING_TO_RECORD');
  assert.deepEqual(P.read(e.win.localStorage).occurrences, P.read(copy).occurrences, 'record(event) writes exactly what openPanel wrote');
  assert.deepEqual(occ.map((o) => o.code), ['E4']);
  assert.deepEqual(engines.playbook.due('2026-10-13'), plain(P.due(P.read(e.win.localStorage), '2026-10-13')));
  const rows = [{ symbol: 'NVDA', sector: 'semiconductors', pct: 10 }];
  assert.deepEqual(engines.playbook.limits(rows, 90), plain(mods.PlaybookEngine.portfolioLimits(mods.PlaybookConfigDefaults, rows, 90)));
  assert.deepEqual(e.priv(), []);
});

test('playbook macro reference only and facts: CRISIS shown, no U3, no macro block; facts through the score view after the news list', async () => {
  const e = env(), { mods, engines, data, qgv } = e, ML = mods.MacroLights, crisis = { state: 'CRISIS', lit_count: 4, available_count: 5, low_confidence: false };
  const stub = Object.freeze({ ...ML, current: () => ({ ...crisis }), setPublic: () => null }); e.win.MacroLights = stub; globalThis.MacroLights = stub;
  try {
    const S = { held: true, watched: false, memberships: {}, sector: 'software_internet', data: { price_missing: false, fx_missing: false, snapshot_missing: false }, coverage: 'READY', coverage_prev: 'READY', q_now: 70, q_prev: 70, g_now: 60, g_prev: 60, v_now: 60, v_prev20: 50,
      excess_20: -0.01, excess_mean_252: 0, excess_sd_252: 0.02, actual_pct: 5, target_pct: 5, earnings_days_until: 40, leaderboard_rank: 120, operating_margin_5y_position: 0.5, sector_marketcap_rank: 1, theme_weight_pct: 20, safety_margin_pct: 30,
      basis: 'v1', v_industry_pct: 80, expectation_check_passed: true, value_trap_gate: false, market_explained_ratio_60: 0.7, q_industry_pct: 50, net_debt_to_ebitda: 1.4, interest_coverage: 8.1 };
    const j = await engines.playbook.judge({ symbol: 'SYNMACRO', date: '2026-10-13', situation: S });
    assert.equal(j.situation.macro_state, 'CRISIS'); assert.equal(j.judgement.macro.gate, 'REFERENCE_ONLY'); assert.match(j.judgement.macro.label, /CRISIS$/);
    const codes = [j.judgement.primary && j.judgement.primary.code, ...j.judgement.secondary.map((c) => c.code), ...j.judgement.candidate_signals.map((c) => c.code)];
    assert.ok(!codes.includes('U3'), codes.join(',')); assert.doesNotMatch(JSON.stringify(j.judgement), /MACRO_(CRISIS|BLOCK|WARNING)/);
    assert.deepEqual(j.judgement, plain(mods.PlaybookScreen.openPanel(stubHost(), { symbol: 'SYNMACRO', date: '2026-10-13', storage: memoryStorage(), situation: S })));
  } finally { e.win.MacroLights = ML; globalThis.MacroLights = ML; }
  // facts(): the old assembly (prepareScores on the score view, heldSymbolsFor, factsFor) after DataRefresh's news list.
  // Old modules reach DataRefresh through globalThis (the window in a browser): the spy goes on both.
  const order = [], DR = e.win.DataRefresh, listSpy = Object.freeze({ ...DR, list: (view, k) => { order.push(['list', view, k]); return DR.list(view, k); } });
  e.win.DataRefresh = listSpy; globalThis.DataRefresh = listSpy;
  const calls = spy(e, 'PlaybookScreen', ['prepareScores', 'heldSymbolsFor', 'factsFor']);
  const pg = await qgv.page(), f = await engines.playbook.facts('NVDA', { date: '2026-10-13' });
  assert.equal(order[0][2], 'news'); assert.notEqual(order[0][1], qgv.scoreView, 'the news list is first read through the public view');
  const [view, o] = calls.prepareScores[0];
  assert.equal(view, qgv.scoreView); assert.equal(o.screens[QGV2], null, 'prepareScores only fills the news RAM: no sec-qgv2.json, no device V'); assert.equal(o.catalog.schema, 'DEVICE_ACTUAL_CATALOG/1'); assert.equal(o.idByTicker.get('NVDA'), 'nvda'); assert.equal(o.idByTicker.size, 19);
  assert.equal(order.length, 2); assert.equal(order[1][1], qgv.scoreView, 'prepareScores re-reads the cached list through the score view');
  globalThis.DataRefresh = DR;
  assert.equal(calls.heldSymbolsFor[0][0], e.prices.priceView);
  const [sym, fo] = calls.factsFor[0]; assert.equal(sym, 'NVDA'); assert.equal(fo.storage, e.store.storage); assert.equal(fo.date, '2026-10-13'); assert.equal(fo.screens, data.screens());
  assert.equal(fo.computed, qgv.centralComputed(pg), 'the page\'s central result');
  assert.equal(f.v_now, qgv.centralComputed(pg).rows.nvda.primary.v); assert.equal(typeof f.v_now, 'number', 'the official V of the publication'); assert.equal(f.sector, 'semiconductors');
  assert.equal(f.v_prev20, null); assert.equal(f.v_comparison_reason, 'V_HISTORY_NOT_PUBLISHED', 'no device V history (DC-31)');
  assert.equal(f.v_source, 'OFFICIAL_CENTRAL', 'facts say the V source of v_now');
  const fj = await engines.playbook.judge({ symbol: 'NVDA', date: '2026-10-13', situation: f });
  assert.equal(fj.v_source, 'OFFICIAL_CENTRAL'); assert.ok(!('v_source' in fj.situation), 'the engine gets the old situation keys only');
  assert.deepEqual(fj.judgement, plain(mods.PlaybookEngine.evaluate(mods.PlaybookConfigDefaults, fj.situation)));
  assert.ok(e.win.requests.every((r) => data.FILES.includes(r.name)), 'only public files; the score path made none'); assert.deepEqual(e.priv(), []);
});

// ---------------------------------------------------------------- virtual trading
test('virtual: stored() = runner open pass on the price view (fetch:false): NOT_AVAILABLE before sign-in, PRICE_NOT_FETCHED after, no private request', async () => {
  const e = env(), { mods, engines, data, prices, store } = e, R0 = 'VirtualTradingRunner';
  await data.static('actual-catalog.json'); await data.ready();
  const calls = spy(e, R0, ['run']), ingest = spy(e, 'PlaybookScreen', ['ingestRunner']), n = e.win.requests.length;
  const a = await engines.virtual.stored({ reportDate: '2026-10-23' });
  assert.equal(a.state, 'NOT_AVAILABLE'); assert.deepEqual(a.reason_codes, ['ORIGIN_UNAPPROVED'], 'no approved Worker address saved');
  assert.equal(e.win.requests.length, n, 'zero requests');
  const [view, o] = calls.run[0];
  assert.equal(view, prices.priceView); assert.deepEqual(Object.keys(o).sort(), ['catalog', 'config', 'fetch', 'reportDate', 'signal']);
  assert.equal(o.fetch, false); assert.equal(o.config, e.win.InvestmentAppConfig); assert.equal(o.reportDate, '2026-10-23'); assert.equal(o.catalog.schema, 'DEVICE_ACTUAL_CATALOG/1');
  assert.deepEqual(ingest.ingestRunner[0][1], Object.fromEntries(mods.DeviceWatchlist.identities(CATALOG).map((c) => [c.company_id, c.ticker])));
  assert.equal((await engines.virtual.stored({ reportDate: '2026-10-18' })).state, 'NOT_STARTED');
  await store.workerOrigin.set(e.click(), WORKER);
  assert.deepEqual((await engines.virtual.stored({ reportDate: '2026-10-23' })).reason_codes, ['AUTH_REQUIRED']);
  await prices.prepare(e.click()); prices.login(e.click()); assert.equal(prices.status().google.connected, true);
  const b = await engines.virtual.stored({ reportDate: '2026-10-23' });
  const sources = Object.values(b.sources);
  assert.ok(sources.length >= 19 && sources.every((s) => s.code === 'PRICE_NOT_FETCHED'), 'stored rows only: nothing fetched on open');
  assert.deepEqual(e.priv(), [], 'no Sheets / Worker / OAuth request'); assert.equal(e.action.blocked(), 0);
  assert.ok(e.win.requests.every((r) => data.FILES.includes(r.name)));
  // 비교 needs two sets (the user's ledger sheet sets are not read in P1); run() is not in P1.
  const c = engines.virtual.compare(b);
  assert.equal(c.state, 'NOT_AVAILABLE'); assert.deepEqual(c.reason_codes, ['COMPARE_NEEDS_TWO_SETS']); assert.deepEqual(c.sets.map((s) => s.kind), ['SET_A']);
  assert.throws(() => engines.virtual.run(e.click()), /NOT_IN_P1/);
  const r = await engines.virtual.rehearse({ reportDate: '2026-10-23' });
  assert.equal(r.result.mode, 'REHEARSAL'); assert.equal(r.result.snapshot_basis, e.qgv.centralComputed(await e.qgv.page()).default, 'the central Q·G rows'); assert.deepEqual(e.priv(), []);
});

test('virtual rehearse without a usable sec-qgv2.json: as app.js, the TARGET Q·G rows (null) and the v2 basis from the old compute', async () => {
  const e = env({ files: { [QGV2]: null, 'qgv-official.json': null } }), { mods, engines, qgv } = e, calls = spy(e, 'VirtualTradingSignals', ['rehearse']);
  const pg = await qgv.page(); assert.equal(pg.state, 'NO_DATA');
  const r = await engines.virtual.rehearse({ reportDate: '2026-10-23' });
  assert.equal(r.result.mode, 'REHEARSAL'); assert.equal(r.result.snapshot_basis, 'v2', 'QgvScores.basis is v2 whatever the file');
  const [, o] = calls.rehearse[0], ids = mods.DeviceWatchlist.identities(CATALOG);
  assert.deepEqual(Object.keys(o.qgRows).sort(), ids.map((c) => c.company_id).sort(), 'the 19 TARGET rows, as app.js passed them');
  assert.ok(Object.values(o.qgRows).every((x) => x.q === null && x.g === null && x.total_reason), 'null Q·G with a reason (BLOCKED snapshots)');
  const ref = mods.QgvScores.judgmentRows(mods.QgvScores.compute({ identities: ids, publicScreens: e.data.screens(), preset: null, gate: null, referenceRows: {} }));
  assert.deepEqual(plain(o.qgRows), plain(ref));
  await assert.rejects(engines.virtual.rehearse({ reportDate: '2026-10-23', page: { rows: [] } }), /PAGE_UNKNOWN/, 'a page error is thrown, not swallowed');
  assert.deepEqual(e.priv(), []);
});

test('virtual forward: the published price-free ledger through the old evaluation (qgSummary / rowEvaluation / segments / evidence)', async () => {
  const e = env(), FV = e.mods.ForwardValidation, p = ledger(), f = await e.engines.virtual.forward();
  assert.equal(f.state, 'LOADED'); assert.equal(f.primary, V1); assert.equal(f.as_of, p.as_of);
  assert.deepEqual(f.rows, plain(p.versions[V1].map((r) => ({ date: r.date, version: r.version, state: r.state, summary: FV.qgSummary(r), evaluation: FV.rowEvaluation(r) }))));
  assert.deepEqual(f.segments, plain(FV.segments(p.versions[V1]))); assert.deepEqual(f.evidence, plain(FV.evidence(p)));
  const none = env({ files: { 'forward-validation-ledger.json': null } }), g = await none.engines.virtual.forward();
  assert.equal(g.state, 'NOT_PUBLISHED'); assert.deepEqual(g.rows, []);
});

// ---------------------------------------------------------------- macro lights
test('macro: MacroLights.setPublic once per public data generation with its set; an applied refresh calls it again, a re-judgement does not', async () => {
  const e = env({ files: { [QGV2]: null } }), { data, engines } = e, calls = spy(e, 'MacroLights', ['setPublic']);
  const c = await engines.macro.current();
  assert.equal(calls.setPublic.length, 1); assert.equal(calls.setPublic[0][0], data.screens(), 'the generation set, as app.js passed publicScreens');
  assert.deepEqual(c, plain(e.mods.MacroLights.current()));
  await engines.macro.current(); await engines.playbook.judge({ symbol: 'SYNTHETIC', date: '2026-10-13', situation: MANUAL });
  assert.equal(calls.setPublic.length, 1, 'same generation, no second call');
  e.table[QGV2] = { json: F.strictPayload() };
  const applied = new Promise((r) => data.subscribe((d) => { if (d.reason === 'REFRESH') r(); }));
  assert.equal(await data.refresh(e.click()), 'APPLIED'); await applied; await new Promise((r) => setTimeout(r, 0));
  assert.equal(calls.setPublic.length, 2); assert.equal(calls.setPublic[1][0], data.screens());
  await engines.macro.current(); assert.equal(calls.setPublic.length, 2);
  e.win.dispatchEvent(new CustomEvent(e.mods.DataRefresh.EVENT, { detail: { reason: 'REJUDGE', generation: data.publication().generation, changed: [] } }));
  await engines.macro.current(); assert.equal(calls.setPublic.length, 2, 'a re-judgement keeps the generation');
});
