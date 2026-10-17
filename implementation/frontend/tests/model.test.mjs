// Node unit tests for the frontend view model, driven by the same cockpit engines the page loads (UMD modules from
// web_assets) and the cockpit's synthetic fixtures. Run: node --test implementation/frontend/tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import * as M from '../src/model.js';
import * as F from '../src/format.js';
import { makeView, dataBase } from '../src/data.js';

const require = createRequire(import.meta.url);
const W = new URL('../../src/investment_system/product/web_assets/', import.meta.url).pathname;
const T = new URL('../../tools/', import.meta.url).pathname;
const g = globalThis;
for (const [file, name] of [['profile-defaults.js', 'ProfileDefaults'], ['type-config-defaults.js', 'TypeConfigDefaults'], ['engine-preview.js', 'EnginePreview'],
  ['dcf-parameters-defaults.js', 'DcfParametersDefaults'], ['playbook-config-defaults.js', 'PlaybookConfigDefaults'], ['playbook-engine.js', 'PlaybookEngine'],
  ['qgv-v2.js', 'QgvV2'], ['scoring-default.js', 'ScoringDefault'], ['qgv2-inputs.js', 'Qgv2Inputs'], ['qgv-scores.js', 'QgvScores'], ['sec-qgv2.js', 'SecQgv2'],
  ['macro-lights.js', 'MacroLights'], ['public-screens.js', 'PublicScreens'], ['watchlist.js', 'DeviceWatchlist']]) g[name] = require(W + file);
const QF = require(T + 'qgv_v2_fixture.js');
const FX = require('../tools/fixture_public_dir.js');

function setup() {
  const inputs = g.Qgv2Inputs.fromInputs(g.SecQgv2.toInputs(QF.strictPayload(), { now: new Date().toISOString() }));
  const targets = [{ company_id: 'nvda', ticker: 'NVDA', name: 'NVIDIA' }, { company_id: 'msft', ticker: 'MSFT', name: 'Microsoft' }, { company_id: 'stry', ticker: 'SYK', name: 'Stryker' }];
  const identities = M.identitiesFor(inputs, targets);
  const S = g.QgvScores.compute({ identities, publicScreens: { [g.Qgv2Inputs.FILE]: inputs }, quotes: {} });
  return { inputs, identities, S, list: M.rows(S, identities, { QS: g.QgvScores, inputs }) };
}

test('one row per company: a TARGET ticker replaces its Universe code (no duplicate ranking point)', () => {
  const { identities, inputs } = setup();
  const universe = Object.keys(inputs.records).filter((c) => !c.startsWith('TARGET:')).length;
  assert.equal(identities.length, universe + 3 - 3, 'NVDA, MSFT and SYK Universe codes are replaced by their TARGET rows');
  assert.equal(identities.filter((i) => i.ticker === 'NVDA').length, 1);
  assert.equal(identities.filter((i) => i.ticker === 'SYK').length, 1, 'SYK (company id stry) is matched by ticker');
  assert.ok(identities.find((i) => i.company_id === 'nvda').target);
});

test('scores are QgvScores results as they are: no price, so V is null and never 0; ranks are unique', () => {
  const { list, S } = setup();
  const nvda = list.find((r) => r.key === 'nvda');
  assert.equal(nvda.total, S.rows.nvda.primary.total);
  assert.equal(nvda.q, S.rows.nvda.primary.q);
  assert.equal(nvda.v, null);
  assert.ok(list.every((r) => r.v === null), 'V needs prices');
  assert.ok(list.every((r) => r.total === null || F.isNum(r.total)));
  const ranks = list.map((r) => r.rank).filter((x) => x !== null);
  assert.equal(new Set(ranks).size, ranks.length, 'no duplicate ranks');
  assert.ok(!nvda.flags.includes('V 없음'), 'V flag is not repeated on every row');
});

test('NOT_AVAILABLE rows carry the engine reason (never a v1 fallback) and no numbers', () => {
  const { list } = setup();
  const na = list.find((r) => r.state === 'NOT_AVAILABLE');
  assert.ok(na);
  assert.match(na.reason, /^QGV v2 산출 불가/);
  assert.equal(na.q, null);
  assert.equal(na.total, null);
});

test('leaderboard view: filter, search and sort keep missing values last in both directions', () => {
  const { list } = setup();
  const byTotal = M.view(list, { sort: 'total' });
  const firstMissing = byTotal.findIndex((r) => r.total === null);
  assert.ok(firstMissing > 0);
  assert.ok(byTotal.slice(firstMissing).every((r) => r.total === null));
  for (let i = 1; i < firstMissing; i++) assert.ok(byTotal[i - 1].total >= byTotal[i].total);
  const asc = M.view(list, { sort: 'q', dir: 1 });
  const qMissing = asc.findIndex((r) => r.q === null);
  assert.ok(asc.slice(qMissing).every((r) => r.q === null));
  assert.deepEqual(M.view(list, { scope: 'target' }).map((r) => r.key).sort(), ['msft', 'nvda', 'stry']);
  assert.deepEqual(M.view(list, { query: 'nvd' }).map((r) => r.ticker), ['NVDA']);
  assert.ok(M.view(list, { onlyScored: true }).every((r) => r.state === 'READY' || r.state === 'PARTIAL'));
});

test('coverage counts the published Universe only (TARGET rows excluded)', () => {
  const { inputs } = setup();
  const c = M.coverage(inputs);
  assert.equal(c.codes, 504);
  assert.ok(c.q > 0 && c.g > 0 && c.both <= Math.min(c.q, c.g));
  assert.equal(c.calcVersion, inputs.calc_version);
  assert.ok(c.missing + c.mismatch <= c.codes);
  assert.deepEqual(M.coverage(null).codes, 0);
});

test('factor rows: 15 v2 factors with weights; V factors say a price is needed', () => {
  const { S } = setup();
  const rows = M.factorRows(S.rows.nvda.primary, g.QgvV2.WEIGHTS);
  assert.equal(rows.length, 15);
  assert.deepEqual([...new Set(rows.map((r) => r.axis))], ['Q', 'G', 'V']);
  for (const r of rows.filter((x) => x.axis === 'V')) { assert.equal(r.score, null); assert.match(r.reason, /가격 필요/); assert.equal(r.code, 'NO_DEVICE_PRICE'); }
  assert.ok(rows.every((r) => !/^[A-Z_]+$/.test(r.label)), 'labels are words');
  assert.equal(M.reasonText('SOMETHING_NEW'), '자료 부족');
});

test('macro: merged public lights only; market and credit wait for device prices', () => {
  const now = new Date();
  const m = M.macro(g.MacroLights, { 'macro-screen.json': FX.macroScreen(now) });
  assert.equal(m.available_count, 3);
  assert.equal(m.lit_count, 1);
  assert.equal(m.lights.market.reason, 'DEVICE_NOT_LOADED');
  assert.equal(M.macro(g.MacroLights, {}), null);
});

test('TARGET weights come from the catalog (TARGET v0), not from holdings', () => {
  const catalog = { total_units: 10000, themes: [{ theme_id: 'ai_semi', label: 'AI·반도체', target_units: 2500 }], instruments: [{ ticker: 'NVDA', label: 'NVIDIA', theme_id: 'ai_semi', target_units: 800, currency: 'USD' }] };
  assert.equal(M.targetInfo(catalog).NVDA.weight, 0.08);
  assert.equal(M.themeTargets(catalog)[0].members[0].weight, 0.08);
  assert.deepEqual(M.targetInfo(null), {});
});

test('formatting: missing is null (rendered as —), links are http(s) only, ids are not names', () => {
  assert.equal(F.score(null), null);
  assert.equal(F.score(0), '0.0', 'a real 0 stays 0');
  assert.equal(F.pct(0.08), '8.0%');
  assert.equal(F.shortTime('not a date'), null);
  assert.equal(F.safeUrl('javascript:alert(1)'), null);
  assert.equal(F.safeUrl('https://www.sec.gov/x'), 'https://www.sec.gov/x');
  assert.equal(F.esc('<b>"x"</b>'), '&lt;b&gt;&quot;x&quot;&lt;/b&gt;');
  assert.equal(F.idName('tokyo_electron'), 'Tokyo Electron');
  assert.equal(F.ago(new Date(Date.now() - 2 * 3600e3).toISOString()), '2시간 전');
});

test('data view shim resolves bare file names against a same-origin relative base only', async () => {
  const seen = [];
  const view = makeView('../', { fetch: (u) => { seen.push(u); return Promise.resolve({ ok: false }); }, AbortController });
  await view.fetch('sec-qgv2.json');
  assert.deepEqual(seen, ['../sec-qgv2.json']);
  const doc = (content) => ({ querySelector: () => ({ getAttribute: () => content }) });
  assert.equal(dataBase(doc('../')), '../');
  assert.equal(dataBase(doc('https://evil.example/')), '../', 'no cross-origin base');
});
