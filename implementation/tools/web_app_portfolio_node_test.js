'use strict';
// New frontend · feature 6 포트폴리오, public layer P2-6 (menu 5 · route #/portfolio; web_app/screen-portfolio.js skeleton +
// web_app/screen-portfolio-live.js, the part after the first paint), and the tier check that qgv.js model() now projects.
//  - qgv.model(page).sets.N15.tier_check is the price-free projection of QgvScores.officialModel's tier check (rule
//    TIERS_RC_20261014, applied_to_selection false, status, core / general counts, per row id · ticker · rank · tier · weight_pct
//    · group, the summed weight and the §16 check of those weights); N10 / N20 have none; frozen; no price, quote, close or cap
//    key; the weights are the owner's 8 / 6 and the core rows are exactly the core count.
//  - The live file's pure parts on the real fixture model: candidateRows (the N15 rows in rank order joined with their tier row;
//    a row without one shows NA, never 0), tierText (every status in Korean with its code), tierLine, setLine (shortfall never
//    filled or re-weighted, its causes), causeText, modelPlan (PAGE for a page that is not READY with the page's reason,
//    NO_MODEL with OFFICIAL_NOT_PUBLISHED / OFFICIAL_INPUTS_DIFFER, MODEL).
//  - The tier constants equal QgvScores.TIERS_RC; the skeleton keeps the menu's section ids 5-1 … 5-4 and carries the notice
//    MODEL_NOT_CONFIRMED before its slots; the live file names no file, requests, stores and copies nothing, has no price
//    button, no order wording, no TARGET v0, and loads without touching the layer (it only puts IS2.portfolioLive).
// Synthetic data only (tools/qgv_v2_fixture.js, tests/fixtures/qgv_official_vectors_v1.json).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const R = require('./web_app_reuse');
const F = require('./qgv_v2_fixture.js');

const QGV2 = 'sec-qgv2.json';
const fresh = (n) => { delete require.cache[require.resolve(R.newPath(n))]; return R.requireNew(n); };
const L = fresh('screen-portfolio-live.js');
const CATALOG = JSON.parse(execFileSync('python3', ['-c', 'import json;from investment_system.product.device_actual_catalog import public_actual_catalog as c;print(json.dumps(c()))'],
  { env: { ...process.env, PYTHONPATH: path.join(R.ROOT, 'implementation/src') }, encoding: 'utf8' }));
const CODES = { schema: 'universe-codes/1', codes: JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/universe/universe_codes_v1.json'), 'utf8')) };
const OV = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/tests/fixtures/qgv_official_vectors_v1.json'), 'utf8')), PUB = JSON.parse(OV.base_text);
const matched = () => ({ ...F.strictPayload(), as_of: PUB.inputs[0].as_of });
const PRICE_KEYS = new Set(['quotes', 'quote_meta', 'month_closes', 'detail', 'reference_range', 'price', 'prices', 'market_cap', 'marketcap', 'ev', 'enterprise_value', 'ebit_yield', 'fcf_yield', 'implied_growth', 'currency_price']);
// One page environment (as web_app_qgv_node_test.js): a browser-like window, the old modules, the P1 data layer and qgv.js.
function env({ files = {} } = {}) {
  const table = { [QGV2]: { json: matched() }, 'actual-catalog.json': { json: CATALOG }, 'universe-codes.json': { json: CODES }, 'qgv-official.json': { body: OV.base_text }, ...files };
  const win = R.nodeWindow({ files: (name) => table[name] });
  const mods = R.loadOld(win), action = fresh('action.js').create({ win }), data = fresh('data.js').create({ win, action }), qgv = fresh('qgv.js').create({ win, data, action, prices: null });
  return { win, mods, data, qgv };
}
function keysDeep(v, out = new Set()) { if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) { if (!Array.isArray(v)) out.add(k); keysDeep(x, out); } return out; }
let shared = null;
async function official() {
  if (shared) return shared;
  const E = env(), pg = await E.qgv.page(), QS = E.mods.QgvScores, result = QS.officialPage(E.win, { publication: (await E.data.official()).payload, v2Inputs: E.data.get(QGV2) });
  const raw = QS.officialModel({ identities: result.identities, v2Inputs: E.data.get(QGV2), quotes: result.quotes, official: result.official, computed: result.computed });
  shared = { E, pg, QS, raw, m: E.qgv.model(pg) };
  return shared;
}

/* ---------------------------------------------------------------- qgv.js model(): the tier check projection */
test('qgv.model: N15 carries the price-free tier check of QgvScores.officialModel (rule, selection unchanged, rows, weights, §16 check); N10 / N20 none', async () => {
  const { pg, raw, m } = await official(), t = raw.sets.N15.tier_check, p = m.sets.N15.tier_check;
  assert.equal(pg.state, 'READY'); assert.ok(t && p, 'the fixture gives an N15 tier check');
  assert.deepEqual([p.rule, p.applied_to_selection, p.status, p.core, p.general], [t.rule, false, t.status, t.core, t.general]);
  assert.equal(p.rule, 'TIERS_RC_20261014');
  assert.deepEqual(p.rows.map((r) => [r.id, r.ticker, r.rank, r.tier, r.weight_pct, r.group]), t.rows.map((r) => [r.company_id, r.ticker, r.rank, r.tier, r.weight_pct, r.group]), 'one row per tier row, same order');
  assert.deepEqual(p.rows.map((r) => r.id), m.sets.N15.selected.map((e) => e.id), 'the tier rows are the N15 selection (selection unchanged)');
  assert.equal(p.sum_pct, t.limits.sum_pct);
  assert.deepEqual(JSON.parse(JSON.stringify(p.limits)), JSON.parse(JSON.stringify({ single: t.limits.single, group: { limit: t.limits.group.limit, status: t.limits.group.status, top_pct: t.limits.group.top_pct,
    groups: t.limits.group.groups, unknown: t.limits.group.unknown }, min_holdings: t.limits.min_holdings })), 'the §16 check of the tier weights');
  for (const r of p.rows) assert.equal(r.weight_pct, r.tier === 'CORE' ? 8 : 6, r.ticker + ': core 8% / general 6%');
  assert.equal(p.rows.filter((r) => r.tier === 'CORE').length, p.core);
  assert.ok(p.rows.some((r) => r.tier === 'CORE') && p.rows.some((r) => r.tier === 'GENERAL'), 'the fixture has both tiers');
  assert.equal(p.sum_pct, p.rows.reduce((a, r) => a + r.weight_pct, 0));
  assert.deepEqual([m.sets.N10.tier_check, m.sets.N20.tier_check], [null, null], 'the tier rule is a 15-name rule');
  assert.ok(Object.isFrozen(p) && Object.isFrozen(p.rows[0]) && Object.isFrozen(p.limits.group.groups), 'frozen');
  const bad = [...keysDeep(p)].filter((k) => /price|quote|close/i.test(k) || k.split('_').includes('cap') || PRICE_KEYS.has(k));
  assert.deepEqual(bad, [], 'no price, quote, close or cap key');
});

test('tier constants equal QgvScores.TIERS_RC (owner decision 2026-10-14: core 5 x 8% + general 10 x 6%)', async () => {
  const { QS } = await official(), T = QS.TIERS_RC;
  assert.deepEqual([L.TIER_RULE.n, L.TIER_RULE.core_n, L.TIER_RULE.core_pct, L.TIER_RULE.general_pct], [T.n, T.core_n, T.core_pct, T.general_pct]);
  assert.equal(L.TIER_RULE.core_n * L.TIER_RULE.core_pct + L.TIER_RULE.general_n * L.TIER_RULE.general_pct, 100);
  assert.equal(L.TIER_RULE.core_n + L.TIER_RULE.general_n, T.n);
});

/* ---------------------------------------------------------------- the live file's pure parts */
test('candidateRows: the N15 selection in rank order with tier and target weight; a row without its tier row is NA, never 0', async () => {
  const { m } = await official(), rows = L.candidateRows(m, (id) => (id === null ? '미정' : 'G:' + id));
  assert.deepEqual(rows.map((r) => r.id), m.sets.N15.selected.map((e) => e.id));
  const ranks = rows.map((r) => r.rank); assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b), 'rank order');
  for (const r of rows) {
    const t = m.sets.N15.tier_check.rows.find((x) => x.id === r.id);
    assert.deepEqual([r.tier, r.weight_pct, r.tierText, r.weightText], [t.tier, t.weight_pct, t.tier === 'CORE' ? '핵심' : '일반', t.weight_pct + '%'], r.ticker);
    assert.equal(r.groupText, r.group === null ? '미정' : 'G:' + r.group);
  }
  const cut = { ...m, sets: { ...m.sets, N15: { ...m.sets.N15, tier_check: { ...m.sets.N15.tier_check, rows: m.sets.N15.tier_check.rows.slice(1) } } } };
  const first = L.candidateRows(cut)[0];
  assert.deepEqual([first.tier, first.weight_pct, first.tierText, first.weightText], [null, null, 'NA', 'NA'], 'no tier row: NA, never 0');
  assert.deepEqual(L.candidateRows(null), []); assert.deepEqual(L.candidateRows({ primary: 'N15', sets: {} }), []);
});

test('tierText / tierLine / setLine / causeText: Korean words with the code, selection unchanged, shortfall never filled', async () => {
  for (const [code, words] of Object.entries(L.TIER_STATUS)) assert.equal(L.tierText(code), words + ' (' + code + ')');
  assert.deepEqual(Object.keys(L.TIER_STATUS).sort(), ['CORE_SHORT', 'FAIL', 'INCOMPLETE', 'PASS', 'UNVERIFIED']);
  assert.equal(L.tierText('NEW_STATE'), '상태 미확인 (NEW_STATE)'); assert.equal(L.tierText(null), '상태 미확인 (NA)');
  const { m } = await official(), t = m.sets.N15.tier_check, line = L.tierLine(t);
  assert.ok(line.startsWith('등급 비중 검사 · ' + L.tierText(t.status)), line);
  assert.match(line, new RegExp('핵심 ' + t.core + ' · 일반 ' + t.general + ' · 비중 합계 ' + t.sum_pct.toFixed(2).replace('.', '\\.') + '%'));
  assert.ok(line.endsWith('선정은 바꾸지 않음'));
  if (t.limits.group.unknown.count) assert.match(line, new RegExp('업종 묶음 미정 ' + t.limits.group.unknown.count + '종목'));
  assert.equal(L.tierLine(null), '등급 비중 검사 없음 (N15가 아님)');
  const set = m.sets.N15, s = L.setLine(set, (id) => id);
  assert.ok(s.startsWith('N15 ' + set.selected.length + '/15 · 동일 비중이면 각 6.67% · '), s);
  if (!set.complete) { assert.match(s, /부족 비중 \d+\.\d\d% · 채우지 않음 · 비중 재조정 없음/); assert.match(s, /원인: 대체 후보 부족/); }
  assert.equal(L.causeText({ code: 'SECTOR_GROUP_MAX_40', count: 2, groups: ['a', 'b'] }, (id) => id.toUpperCase()), 'A/B 40% 한도로 2종목 초과');
  assert.equal(L.causeText({ code: 'MIN_HOLDINGS', count: 7, limit: 10 }), '최소 10종목 미달');
  assert.equal(L.causeText({ code: 'SOMETHING_NEW' }), null);
  assert.equal(L.setLine(null), null);
});

test('modelPlan: a page that is not READY keeps its reason; no publication / another input file is NO_MODEL with its code; else MODEL', async () => {
  const { pg, m } = await official();
  assert.deepEqual({ ...L.modelPlan(pg, m) }, { kind: 'MODEL', code: null });
  const none = env({ files: { 'qgv-official.json': null } }), p0 = await none.qgv.page();
  assert.equal(p0.state, 'READY'); assert.equal(none.qgv.model(p0), null);
  assert.deepEqual({ ...L.modelPlan(p0, null) }, { kind: 'NO_MODEL', code: p0.price_basis.reason });
  assert.match(p0.price_basis.reason, /^OFFICIAL_/);
  const other = env({ files: { [QGV2]: { json: { ...F.strictPayload(), as_of: '2026-10-12T22:30:00Z' } } } }), p1 = await other.qgv.page();
  assert.deepEqual({ ...L.modelPlan(p1, other.qgv.model(p1)) }, { kind: 'NO_MODEL', code: 'OFFICIAL_INPUTS_DIFFER' });
  const empty = env({ files: { [QGV2]: null, 'qgv-official.json': null } }), p2 = await empty.qgv.page();
  assert.equal(p2.state, 'NO_DATA'); assert.deepEqual({ ...L.modelPlan(p2, null) }, { kind: 'PAGE', code: p2.reason });
  assert.ok(empty.qgv.reasonText(p2.reason) && !/0/.test(empty.qgv.reasonText(p2.reason)), 'the page reason is words, not a zero');
  assert.deepEqual({ ...L.modelPlan(null, null) }, { kind: 'PAGE', code: 'PAGE_NOT_READY' });
});

/* ---------------------------------------------------------------- skeleton and file rules */
test('screen-portfolio.js keeps the menu sections 5-1 … 5-4 and draws the notice MODEL_NOT_CONFIRMED before its slots', () => {
  const sk = fs.readFileSync(R.newPath('screen-portfolio.js'), 'utf8'), menus = fs.readFileSync(R.newPath('screen-menus.js'), 'utf8');
  const ids = (t) => [...t.matchAll(/\['(5-\d)'/g)].map((x) => x[1]);
  assert.deepEqual(ids(sk), ['5-1', '5-2', '5-3', '5-4']); assert.deepEqual(ids(sk), ids(menus), 'the same section ids as screen-menus.js');
  assert.match(sk, /portfolioNotice:'MODEL_NOT_CONFIRMED'/);
  assert.match(sk, /id==='5-1'\?notice\(\):null,slots\[id\]=/, 'the notice comes before the 5-1 slot (above any candidate row)');
  assert.match(sk, /매매 지시도 아닙니다/); assert.match(sk, /TARGET v1은 아직 /);
  assert.match(sk, /I\.portfolioLive/);
});

test('screen-portfolio-live.js names no file, requests / stores / copies nothing, has no price button, order wording or TARGET v0; loads without touching the layer', () => {
  const text = fs.readFileSync(R.newPath('screen-portfolio-live.js'), 'utf8'), code = text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[\s;,(){}])\/\/.*$/gm, '$1');
  assert.deepEqual(code.match(/[a-z0-9-]+\.json/g), null, 'no file named (the page comes from IS2.qgv)');
  assert.doesNotMatch(code, /fetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|clipboard|workers\.dev|\/kis\/|\/private\//, 'no request, storage, copy or private address');
  assert.doesNotMatch(code, /I\.prices|IS2\.prices|readUniverse|periodReturns|loadTabs|\.quote\(|I\.store|I\.engines|forEngines/, 'no price, device store or engine call (TARGET store and builder untouched)');
  assert.doesNotMatch(code, /주문|매수|매도|buy|sell/i, 'no order / buy / sell wording');
  assert.doesNotMatch(code, /TARGET v0|v0\b|19종목|actual-catalog/, 'no TARGET v0 (catalog 19)');
  assert.doesNotMatch(code, /(\?\?|\|\|)\s*0(?!\d)/, 'NA is never filled with 0');
  assert.doesNotMatch(code, /로그인됨|signed in/i, 'never pretends a signed-in state');
  assert.equal((code.match(/privatePanel\(/g) || []).length, 1, 'exactly one private panel');
  const touched = [], IS2 = new Proxy({ h() {}, href() {}, parts: {} }, { get(t, k) { if (!['h', 'href', 'parts', 'append', 'portfolioLive'].includes(k)) touched.push(k); return t[k]; }, set(t, k, v) { t[k] = v; return true; } });
  vm.runInNewContext(text, { window: { IS2 }, Object }, { filename: 'screen-portfolio-live.js' });
  assert.deepEqual(touched, [], 'nothing of the layer is read while the file loads');
  assert.deepEqual(Object.keys(IS2.portfolioLive), ['screen']);
});
