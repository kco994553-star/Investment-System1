'use strict';
// New frontend P2-2a · menu 1 QGV leaderboard: the small pure parts ported from web_assets/leaderboard-screen.js into
// web_app/screen-qgv-live.js (Main decision 2026-10-25: the 67 KB old screen stays out of LOAD_ORDER) equal the old functions.
//  - screen-qgv-live.js runs in a vm with a stub IS2; IS2.qgvLive.helpers gives the ports. Nothing touches the layer at load.
//  - Input: the reader output (Qgv2Inputs over qgv_v2_fixture.strictPayload(), as IS2.data.get('sec-qgv2.json') gives it) with
//    edited copies of records (STALE, WITHDRAWN + identity_withdrawn, calc_version_mismatch, in_cross_section false, SIC '0000',
//    industry_group null; each branch shown to be reached first) and a company-classification fixture with a TARGET inside the
//    Universe (nvda, classified from its TARGET classification, row.id 'nvda') and one outside (tokyo_electron).
//  - sortRows = LeaderboardScreen.sortRows for qgv / q / g / v / asof / cap (both directions; cap with a READY M3 index stub) over
//    the page rows of the central V publication fixture (DC-31) (ranked, QG reference and no-total rows); ticker / favorites = DeviceWatchlist.filter;
//    name = its own stated rule (shown title, localeCompare 'ko', ties by ticker); the toggle is null for the one-way keys.
//  - sicOf, populationOf, the industry part of classificationOf and the industry / SIC filters of filterClassifications, all with
//    company_id = row.id.
//  - Every case is also compared to frozen vectors (tools/fixtures/web_app_qgv_screen_expected.json, written by the old
//    functions with --write): after P3 deletes leaderboard-screen.js only the live comparison goes.
// Synthetic data only; the sentinel prices of the Universe read are made-up decimals and never compared.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');

const NOW = Date.parse('2026-10-14T03:00:00.000Z');// the fixture rows were collected 2026-10-13: LIVE at this time
const EXPECTED = path.join(__dirname, 'fixtures/web_app_qgv_screen_expected.json');
const QGV2 = 'sec-qgv2.json', CLS = 'company-classification.json';
const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
const CLASS = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/company_classification_v0_payloads.json'), 'utf8')).live;
const fresh = (name) => { delete require.cache[require.resolve(R.newPath(name))]; return R.requireNew(name); };
{ const Real = Date; class Fixed extends Real { constructor(...a) { super(...(a.length ? a : [NOW])); } static now() { return NOW; } } globalThis.Date = Fixed; }

// The ports, from the file as the page loads it (a vm with only window.IS2: core's h / href).
function ports() {
  const core = fresh('core.js'), IS2 = { ...core, parts: {} };
  vm.runInNewContext(fs.readFileSync(R.newPath('screen-qgv-live.js'), 'utf8'), { window: { IS2 }, Object }, { filename: 'screen-qgv-live.js' });
  assert.deepEqual(Object.keys(IS2.qgvLive), ['leaderboard', 'helpers']);
  return IS2.qgvLive.helpers;
}
// A priced page (the Universe read stand-in of web_app_qgv_node_test.js) and the reader output it was computed from.
async function page() {
  // The central V publication (DC-31; synthetic base_text, its input as_of = the fixture's): the page's ranks and V come from it.
  const pub = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')).base_text;
  const win = R.nodeWindow({ files: (n) => ({ [QGV2]: { json: F.strictPayload() }, 'actual-catalog.json': { json: CATALOG }, 'qgv-official.json': { body: pub } })[n] });
  const mods = R.loadOld(win), action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action });
  const prices = new Map(); let i = 0;
  for (const [code, r] of Object.entries(F.strictPayload().records)) if (r.state === 'LIVE' && code !== 'NASDAQ:MSFT') prices.set(code, { price: 17 + i++ + 0.0731946, currency: 'USD' });
  prices.set('NASDAQ:NVDA', { price: 17 + i + 0.0731946, currency: 'USD' });
  const view = { prices: () => prices, priceBasis: () => ({ source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_s', acquired_at: '2026-10-14T02:00:00.000Z', currency: 'USD', price_time: null }), readStatus: () => null };
  const qgv = fresh('qgv.js').create({ win, data, action, prices: { universeView: view } });
  const pg = await qgv.page();
  return { win, mods, pg, inputs: data.get(QGV2) };
}
// Edited copies of reader records: every branch of the ports' record rules.
function edited(inputs) {
  const recs = { ...inputs.records }, live = Object.keys(recs).filter((k) => !k.startsWith('TARGET:') && recs[k].in_cross_section === true && recs[k].state === 'LIVE');
  assert.ok(live.length >= 8, 'enough cross-section rows to edit');
  const [stale, gone, mismatch, outCs, zero, noGroup] = live;
  recs[stale] = { ...recs[stale], state: 'STALE' };
  recs[gone] = { ...recs[gone], state: 'WITHDRAWN', identity_withdrawn: true };
  recs[mismatch] = { ...recs[mismatch], calc_version_mismatch: true };
  recs[outCs] = { ...recs[outCs], in_cross_section: false };
  recs[zero] = { ...recs[zero], sic: '0000' };
  recs[noGroup] = { ...recs[noGroup], industry_group: null };
  return { inputs: { ...inputs, records: recs }, codes: { stale, gone, mismatch, outCs, zero, noGroup } };
}
function classification() {
  const c = structuredClone(CLASS);
  c.data.companies.tokyo_electron.industry = { ...structuredClone(c.data.companies.nvda.industry), sic: '3559', group: 'manufacturing_industrial_tech' };// a TARGET outside the Universe, classified
  c.data.companies.gev.industry = { ...structuredClone(c.data.companies.nvda.industry), identity_withdrawn: true };// a withdrawn TARGET classification
  return c;
}

let ENV = null;
async function setup() {
  if (ENV) return ENV;
  const H = ports(), P = await page(), old = R.requireOld('leaderboard-screen.js'), E = edited(P.inputs), cls = classification();
  const ps = { [QGV2]: E.inputs, [CLS]: cls }, plain = { [QGV2]: P.inputs, [CLS]: cls };
  const rows = P.pg.rows, index = new Map(rows.map((r, i) => [r.id, i]));
  ENV = { H, P, old, E, cls, ps, plain, rows, index, out: {} };
  return ENV;
}
// Page-row indexes in order (the frozen vectors' form).
const order = (env, list, key = (x) => x.id) => list.map((x) => env.index.get(key(x)));
function frozenCheck(env, name, value) {
  env.out[name] = value;
  if (process.argv.includes('--write')) return;
  const want = JSON.parse(fs.readFileSync(EXPECTED, 'utf8'));
  assert.ok(Object.hasOwn(want.cases, name), name + ' is in the frozen vectors');
  assert.deepEqual(value, want.cases[name], name + ' equals the frozen vector');
}

test('setup: the edited branches are reached; the fixture has ranked, QG reference and no-total rows', async () => {
  const env = await setup(), { old, E, P, ps, plain, H } = env, c = E.codes, sic = (id, x) => old.sicOf({ company_id: id }, x);
  const ranked = env.rows.filter((r) => Number.isInteger(r.rank.official)), qg = env.rows.filter((r) => r.rank.qg_reference_order !== null), none = env.rows.filter((r) => r.score.total === null);
  assert.ok(ranked.length >= 2 && qg.length >= 2 && none.length >= 1, 'ranked ' + ranked.length + ' · QG ' + qg.length + ' · no total ' + none.length);
  assert.notEqual(old.populationOf(ps), old.populationOf(plain), 'the edits change the population count');
  assert.equal(old.populationOf(plain) - old.populationOf(ps), 3, 'withdrawn, mismatch and out of the cross-section leave it; STALE stays');
  assert.equal(E.inputs.records[c.stale].state, 'STALE'); assert.equal(old.classificationOf({ company_id: c.stale }, ps).industry, P.inputs.records[c.stale].industry_group, 'a STALE row keeps its group');
  assert.notEqual(sic(c.gone, ps), sic(c.gone, plain)); assert.equal(sic(c.gone, ps), null, 'withdrawn: no SIC');
  assert.notEqual(sic(c.zero, ps), sic(c.zero, plain)); assert.equal(sic(c.zero, ps), null, '0000: no SIC');
  assert.equal(old.classificationOf({ company_id: c.noGroup }, ps).industry, null); assert.notEqual(old.classificationOf({ company_id: c.noGroup }, plain).industry, null);
  assert.equal(old.classificationOf({ company_id: c.gone }, ps).industry, null, 'withdrawn: no group');
  // The TARGET inside the Universe is classified from its TARGET classification (its Universe record has no data in the fixture).
  const nvda = env.rows.find((r) => r.id === 'nvda');
  assert.equal(nvda.code, 'NASDAQ:NVDA'); assert.equal(E.inputs.records['NASDAQ:NVDA'].state, 'NOT_AVAILABLE');
  assert.deepEqual([H.sicOf({ company_id: 'nvda' }, ps), H.industryOf({ company_id: 'nvda' }, ps)], ['3674', 'manufacturing_industrial_tech']);
  assert.deepEqual([H.sicOf({ company_id: 'NASDAQ:NVDA' }, ps), H.industryOf({ company_id: 'NASDAQ:NVDA' }, ps)], [null, null], 'never keyed by row.code');
  const outside = env.rows.find((r) => r.id === 'tokyo_electron');
  assert.equal(outside.scope, 'OUTSIDE_UNIVERSE'); assert.deepEqual([H.sicOf({ company_id: 'tokyo_electron' }, ps), H.industryOf({ company_id: 'tokyo_electron' }, ps)], ['3559', 'manufacturing_industrial_tech']);
  assert.equal(H.sicOf({ company_id: 'gev' }, ps), null, 'a withdrawn TARGET classification: no SIC');
});

test('sicOf, populationOf, industry (classificationOf) and the industry / SIC filters (filterClassifications) equal the old functions, keyed by row.id', async () => {
  const env = await setup(), { H, old, ps, rows } = env, ids = rows.map((r) => ({ company_id: r.id }));
  for (const x of [ps, env.plain]) {
    assert.equal(H.populationOf(x), old.populationOf(x));
    for (const c of ids) {
      assert.equal(H.sicOf(c, x), old.sicOf(c, x), c.company_id + ' sic');
      assert.equal(H.industryOf(c, x), old.classificationOf(c, x).industry, c.company_id + ' industry');
    }
  }
  assert.equal(H.populationOf(null), old.populationOf(null)); assert.equal(H.populationOf({}), null);
  frozenCheck(env, 'population', H.populationOf(ps));
  frozenCheck(env, 'sic', ids.map((c) => H.sicOf(c, ps)));
  frozenCheck(env, 'industry', ids.map((c) => H.industryOf(c, ps)));
  const groups = [...new Set(ids.map((c) => H.industryOf(c, ps)).filter(Boolean))].sort(), sics = [...new Set(ids.map((c) => H.sicOf(c, ps)).filter(Boolean))].sort();
  assert.ok(groups.length >= 2 && sics.length >= 2);
  const filters = [{}, { industry: 'NOT_AVAILABLE' }, ...groups.map((g) => ({ industry: g })), { sic2: 'NOT_AVAILABLE' }, { sic4: 'NOT_AVAILABLE' }, ...sics.map((s) => ({ sic4: s })),
    ...[...new Set(sics.map((s) => s.slice(0, 2)))].map((s) => ({ sic2: s })), { industry: groups[0], sic2: sics[0].slice(0, 2) }, { industry: groups[0], sic4: sics[sics.length - 1] }];
  for (const f of filters) {
    const mine = Array.from(H.filterClassified(ids, ps, f)), theirs = old.filterClassifications(ids, { publicScreens: ps, filters: { industry: '', sic2: '', sic4: '', type: '', ...f } });
    assert.deepEqual(mine.map((c) => c.company_id), theirs.map((c) => c.company_id), JSON.stringify(f));
    frozenCheck(env, 'filter ' + JSON.stringify(f), order(env, mine, (c) => c.company_id));
  }
  assert.ok(H.filterClassified(ids, ps, { industry: groups[0] }).length > 0 && H.filterClassified(ids, ps, { industry: groups[0] }).length < ids.length, 'a filter matches some and hides some');
});

test('sortRows equals LeaderboardScreen.sortRows for the ids it orders; ticker / favorites equal DeviceWatchlist.filter; name keeps its own rule; the toggle', async () => {
  const env = await setup(), { H, old, P, rows } = env, W = P.mods.DeviceWatchlist, PSV = P.mods.PrivateSubsetView;
  // Old adapter: identities {company_id, ticker, name} + a QgvScores-shaped result over the same page rows.
  const ids = rows.map((r) => ({ company_id: r.id, ticker: r.ticker, name: 'Name ' + r.ticker }));
  const S = { rows: Object.fromEntries(rows.map((r) => [r.id, { rank: r.rank.official, qg_reference: r.rank.qg_reference_order !== null ? { order: r.rank.qg_reference_order } : null,
    primary: { total: r.score.total, q: r.score.q, g: r.score.g, v: r.score.v, coverage: { source: { acquired_at: r.acquired_at } } } }])) };
  // A READY M3 index stub: some rows by company id, some by symbol, equal ranks for a cap tie, the rest absent.
  const entries = new Map(); let n = 0;
  for (const r of rows.filter((x) => x.score.total !== null).slice(0, 24)) { n++; const e = { state: 'RANKED', rank: n % 7 === 0 ? n - 1 : n, quality: null, group_id: null, reason_codes: [] }; entries.set(n % 2 ? 'id:' + r.id : 'sym:' + r.ticker.replaceAll('.', '-'), e); }
  const deviceRanks = { state: 'READY', entries, reason_codes: [] }, cap = (r) => { const e = PSV.rankFor(deviceRanks, { company_id: r.id, ticker: r.ticker }); return Number.isInteger(e.rank) ? e.rank : null; };
  const priced = rows.filter((r) => cap(r) !== null).length; assert.ok(priced >= 20, 'cap ranks found for ' + priced + ' rows');
  for (const id of ['qgv', 'qgv-asc', 'q-desc', 'q-asc', 'g-desc', 'g-asc', 'v-desc', 'v-asc', 'asof-desc', 'asof-asc', 'cap-desc', 'cap-asc']) {
    const mine = Array.from(H.sortRows(rows, id, { cap }), (r) => r.id), theirs = old.sortRows(ids, S, id, { deviceRanks }).map((r) => r.company_id);
    assert.deepEqual(mine, theirs, id);
    assert.notDeepEqual(mine, rows.map((r) => r.id), id + ' reorders');
    frozenCheck(env, 'sort ' + id, order(env, mine.map((x) => ({ id: x }))));
  }
  // QGV keeps the tiers: ranked, then the QG reference order, then the rest; never interleaved.
  const tiers = H.sortRows(rows, 'qgv', { cap }).map((r) => (Number.isInteger(r.rank.official) ? 0 : r.rank.qg_reference_order !== null ? 1 : 2));
  assert.deepEqual(tiers, [...tiers].sort((a, b) => a - b), 'ranked, then QG reference, then no total');
  assert.deepEqual(H.sortRows(rows, 'qgv-asc', { cap }).map((r) => (Number.isInteger(r.rank.official) ? 0 : r.rank.qg_reference_order !== null ? 1 : 2)).filter((t, i, a) => i && t < a[i - 1]), [], 'tiers kept ascending too');
  const prefs = { version: 1, interests: [rows[40].id, rows[3].id, 'nvda'], groups: [] };
  for (const id of ['ticker', 'favorites']) {
    const mine = Array.from(H.sortRows(rows, id, { interests: prefs.interests }), (r) => r.id), theirs = W.filter(ids, prefs, { sort: id }).map((r) => r.company_id);
    assert.deepEqual(mine, theirs, id + ' = DeviceWatchlist.filter');
    frozenCheck(env, 'sort ' + id, order(env, mine.map((x) => ({ id: x }))));
  }
  // name: the shown title (Korean when reviewed), localeCompare 'ko', ties by ticker (titles repeat here on purpose).
  const KO = ['가나', '다라', '마바', 'Apple', '사아'], title = (r) => KO[r.ticker.length % KO.length];
  const want = [...rows].sort((a, b) => title(a).localeCompare(title(b), 'ko') || a.ticker.localeCompare(b.ticker)).map((r) => r.id);
  const got = Array.from(H.sortRows(rows, 'name', { title }), (r) => r.id);// Array.from: the vm realm's arrays have their own prototype
  assert.deepEqual(got, want, 'name: title localeCompare ko, ties by ticker'); frozenCheck(env, 'sort name', order(env, got.map((x) => ({ id: x }))));
  for (const id of ['ticker', 'name', 'favorites']) assert.equal(H.oppositeSort(id), null, id + ' has one direction');
  for (const id of ['qgv', 'qgv-asc', 'q-desc', 'q-asc', 'g-desc', 'g-asc', 'v-desc', 'v-asc', 'asof-desc', 'asof-asc', 'cap-desc', 'cap-asc']) assert.equal(H.oppositeSort(id), old.oppositeSort(id), id + ' toggle = oppositeSort');
  assert.deepEqual(Array.from(H.SORTS, (s) => s[0]), old.SORTS.map((s) => s[0]).filter((x) => x !== 'ticker-desc' && x !== 'name-desc'), 'the old ids, without the two reverse ones');
  for (const s of H.SORTS) { const o = old.SORTS.find((x) => x[0] === s[0]); assert.deepEqual(Array.of(s[1], s[2]), [o[1], o[2]], s[0] + ' key and direction'); }
  // Sorting returns a new array and never touches rank numbers.
  const copy = rows.map((r) => r.rank.official); H.sortRows(rows, 'v-asc'); assert.deepEqual(rows.map((r) => r.rank.official), copy);
});

test('listOf / returnOrder: D12 lists (outside rows in none, a QG_REFERENCE group without an order in none); no portfolio rank (DC-24); returns high first, NA last', async () => {
  const env = await setup(), { H, rows } = env;
  const lists = rows.map(H.listOf), count = (l) => lists.filter((x) => x === l).length;
  assert.equal(count('RANKED'), rows.filter((r) => Number.isInteger(r.rank.official)).length);
  assert.equal(count('QG_REFERENCE'), rows.filter((r) => r.rank.qg_reference_order !== null).length);
  for (const r of rows.filter((x) => x.scope === 'OUTSIDE_UNIVERSE' || x.reference_only)) assert.equal(H.listOf(r), null, r.id);
  const fake = { ...rows[0], scope: 'UNIVERSE', reference_only: false, rank: { official: null, qg_reference_order: null, group: 'QG_REFERENCE' } };
  assert.equal(H.listOf(fake), null, 'a QG_REFERENCE group without an order has no list');
  assert.equal(H.listOf({ ...fake, scope: 'OUTSIDE_UNIVERSE', rank: { ...fake.rank, official: 3 } }), null, 'outside: no list even with a rank');
  frozenCheck(env, 'lists', lists);
  assert.equal(H.portfolioRanks, undefined, 'no TARGET v0 portfolio rank on a QGV screen (DC-24)');
  const val = (r) => (r.score.q === null ? null : r.score.q / 100 - 0.5), ro = H.returnOrder(rows, val), vs = ro.map(val);
  assert.deepEqual(vs.filter((x, i) => i && x !== null && (vs[i - 1] === null || x > vs[i - 1])), [], 'high first, NA last');
  assert.ok(vs.indexOf(null) > 0 && vs.slice(vs.indexOf(null)).every((x) => x === null));
});

test('frozen vectors file', async () => {
  const env = await setup();
  if (process.argv.includes('--write')) {
    fs.mkdirSync(path.dirname(EXPECTED), { recursive: true });
    fs.writeFileSync(EXPECTED, JSON.stringify({ note: 'Expected outputs of the leaderboard-screen.js parity cases (page-row indexes in order, counts), written by tools/web_app_qgv_screen_node_test.js --write from the old functions. P3 keeps only this comparison.',
      rows: env.rows.map((r) => r.id), cases: env.out }) + '\n');
    return;
  }
  const want = JSON.parse(fs.readFileSync(EXPECTED, 'utf8'));
  assert.deepEqual(want.rows, env.rows.map((r) => r.id), 'the same page rows as when the vectors were written');
  assert.deepEqual(Object.keys(want.cases).sort(), Object.keys(env.out).sort(), 'every frozen case was compared');
});

// The D12 case the browser fixture cannot publish (the strict sec-qgv2.json validator keeps all 504 codes and gives a non-SEC
// TARGET no data, so every TARGET with data stands for a Universe code): an outside TARGET with a Q·G total and no V. QgvScores
// gives it the QG_REFERENCE group but no reference order (official split); the screen's listOf puts it in no list.
test('an outside TARGET with Q and G but no V: exploreGroup QG_REFERENCE, no QG order, in no 2.1.5 list', async () => {
  const env = await setup(), { H, P } = env, QS = P.mods.QgvScores, p = F.strictPayload();
  p.target.asml = { ...structuredClone(p.target.msft), cik: '0000937966' };
  P.mods.SecQgv2.validate(p);// still a valid publication (inside the Universe it would be NASDAQ:ASML's row)
  const v2Inputs = { ...env.P.inputs, records: { ...env.P.inputs.records, 'TARGET:asml': { ...env.P.inputs.records['TARGET:msft'] } } };
  const ids = [{ company_id: 'asml', ticker: 'ASML' }, { company_id: 'msft', ticker: 'MSFT' }];
  const official = { universe: { asml: null, msft: 'NASDAQ:MSFT' }, by_code: { 'NASDAQ:MSFT': 'msft' }, target_in_universe: [{ company_id: 'msft', code: 'NASDAQ:MSFT' }], outside: ['asml'], codes: 1 };
  const S = QS.compute({ identities: ids, v2Inputs, quotes: {}, official }), a = S.rows.asml, m = S.rows.msft;
  assert.ok(Number.isFinite(a.primary.total) && Number.isFinite(a.primary.q) && Number.isFinite(a.primary.g) && a.primary.v === null, 'Q·G total, no V');
  assert.equal(a.outside_universe, true); assert.equal(QS.exploreGroup(a), 'QG_REFERENCE'); assert.equal(a.qg_reference, null, 'no QG reference order outside the Universe'); assert.equal(a.rank, null);
  assert.equal(QS.exploreGroup(m), 'QG_REFERENCE'); assert.ok(m.qg_reference && m.qg_reference.order === 1, 'the same row inside the Universe gets an order');
  const row = { scope: 'OUTSIDE_UNIVERSE', reference_only: false, rank: { official: null, qg_reference_order: null, group: QS.exploreGroup(a) } };
  assert.equal(H.listOf(row), null, 'in no list chip count');
  assert.equal(H.listOf({ ...row, scope: 'UNIVERSE', rank: { ...row.rank, qg_reference_order: 1 } }), 'QG_REFERENCE');
});
