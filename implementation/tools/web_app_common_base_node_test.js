'use strict';
// New frontend common base (2026-10-31; docs/frontend_v2/COMMON_BASE_20261031.md): the three contracts later lanes call.
//  - IS2.companies (web_app/companies.js) over the real public inputs (universe/universe_codes_v1.json, the source of
//    universe-codes.json, and web_assets/company-names-ko.json) and the real listing-ended table of search-part-live.js: rows
//    {code, id, ticker, name_en, name_ko, status, withdrawn_on, official} deep-frozen, get / find / exact / korean, WITHDRAWN (WBD
//    shown as delisted), scope(), one read of each file per page, a failed part read again, fail-closed without the table; the
//    home's search and company index have no other code path to the files.
//  - IS2.lab (web_app/lab.js): validate() accepts the fixture's valid payloads (deep-frozen copy, input untouched) and refuses
//    each invalid variant with its code and path (tools/lab_backtest_fixture.js, synthetic values only), tolerance edges; the
//    owner's status texts exactly; nullText; source() answers NONE + PRIVATE_NOT_READY without any request or data read.
//  - IS2.privateArea (web_app/private.js): NOT_READY and its texts; no network, storage or sign-in.
//  - Loading each file touches nothing on IS2 but its own namespace; loader.js lists them after the layer with facades.
//  - parts.notReady: the shared 준비 중 line.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const R = require('./web_app_reuse');
const F = require('./lab_backtest_fixture.js');

const ES = R.requireOld('entity-search.js');
const CODES = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/universe/universe_codes_v1.json'), 'utf8'));
const NAMES = JSON.parse(fs.readFileSync(R.oldPath('company-names-ko.json'), 'utf8'));
const fresh = (n) => { delete require.cache[require.resolve(R.newPath(n))]; return R.requireNew(n); };
const C = fresh('companies.js'), L = fresh('lab.js'), P = fresh('private.js');
// The listing-ended table as the page has it: search-part-live.js run on a stub IS2.
const ENDED = (() => { const IS2 = { h: () => null }; vm.runInNewContext(fs.readFileSync(R.newPath('search-part-live.js'), 'utf8'), { window: { IS2 }, Object }, { filename: 'search-part-live.js' }); return IS2.searchPart.LISTING_ENDED; })();
const plain = (v) => JSON.parse(JSON.stringify(v));
const code = (text) => text.replace(/\/\*[\s\S]*?\*\//g, (c) => c.replace(/[^\n]/g, ' ')).split('\n').map((l) => l.replace(/(^|[\s;,(){}])\/\/.*$/, '$1')).join('\n');
function deepFrozen(v, at = '$') { if (v && typeof v === 'object') { assert.ok(Object.isFrozen(v), at + ' frozen'); for (const [k, x] of Object.entries(v)) deepFrozen(x, at + '.' + k); } }

function companies({ codes = CODES, names = NAMES, ended = ENDED, fail = false } = {}) {
  const calls = { universe: 0, static: [] };
  const data = {
    universe: async () => { calls.universe++; if (fail) throw new Error('LOADER_FAILED data.js'); return codes; },
    static: async (n) => { calls.static.push(n); if (fail) throw new Error('LOADER_FAILED data.js'); return n === 'company-names-ko.json' && names ? ES.nameIndex(names) : null; },
  };
  return { C: C.create({ data, ended }), calls };
}

/* ---------------------------------------------------------------- IS2.companies */
test('companies: Universe504 rows from the two static files, deep-frozen, in the code list order', async () => {
  const { C: c, calls } = companies();
  assert.deepEqual([...c.list()], [], 'nothing before ready()'); assert.ok(Object.isFrozen(c.list()));
  assert.equal(c.get('NYSE:FIX'), null); assert.deepEqual([...c.find('nv')], []); assert.equal(c.exact('nvda'), null);
  assert.deepEqual(calls, { universe: 0, static: [] }, 'no read before ready()');
  const r = await c.ready();
  assert.deepEqual(plain(r), { state: 'OK', size: 504, missing: [] }); deepFrozen(r);
  const rows = c.list();
  assert.equal(rows.length, 504); deepFrozen(rows);
  assert.deepEqual(rows.map((x) => x.code), CODES, 'the code list order');
  for (const x of rows) {
    assert.deepEqual(Object.keys(x), ['code', 'id', 'ticker', 'name_en', 'name_ko', 'status', 'withdrawn_on', 'official']);
    assert.match(x.code, /^(NYSE|NASDAQ|BATS):/); assert.equal(x.ticker, x.code.slice(x.code.indexOf(':') + 1)); assert.equal(x.official, true);
    assert.ok(['ACTIVE', 'WITHDRAWN'].includes(x.status));
    const rec = ES.nameIndex(NAMES).get(x.code), cls = rec && rec.class_label;
    assert.equal(x.name_en, rec && rec.en_name ? rec.en_name + (cls ? ' Class ' + cls : '') : null, x.code + ' name_en');
    assert.equal(x.name_ko, rec && rec.ko_name ? rec.ko_name + (cls ? ' ' + cls : '') : null, x.code + ' name_ko (null without a reviewed Korean name)');
  }
  assert.ok(rows.some((x) => x.name_ko === null) && rows.some((x) => x.name_ko !== null), 'both kinds of rows exist');
  assert.deepEqual(plain(c.get('NYSE:FIX')), { code: 'NYSE:FIX', id: 'NYSE:FIX', ticker: 'FIX', name_en: 'COMFORT SYSTEMS USA INC', name_ko: c.get('NYSE:FIX').name_ko, status: 'ACTIVE', withdrawn_on: null, official: true });
  assert.equal(c.get('nvda').code, 'NASDAQ:NVDA', 'a linked TARGET company_id finds its code'); assert.equal(c.get('NASDAQ:NVDA').id, 'nvda');
  assert.equal(c.get('hanmi'), null, 'a TARGET company outside Universe504 is not a row'); assert.equal(c.get(7), null); assert.equal(c.get(undefined), null);
  assert.equal(c.get('NYSE:BRK.B').name_en, 'BERKSHIRE HATHAWAY INC Class B', 'the share-class letter');
  for (const x of rows) assert.deepEqual(Object.keys(x).filter((k) => /price|cap|score|rank|weight/i.test(k)), []);
  assert.deepEqual(calls, { universe: 1, static: ['company-names-ko.json'] }, 'each file once; no other file');
  await c.ready(); assert.deepEqual(calls, { universe: 1, static: ['company-names-ko.json'] }, 'built once per page');
});

test('companies: find / exact / korean follow the shared search rules (DC-23)', async () => {
  const { C: c } = companies(); await c.ready();
  const codes = (rows) => rows.map((x) => x.code);
  assert.deepEqual(codes(c.find('nv')).slice(0, 2), ['NASDAQ:NVDA', 'NYSE:NVR'], 'ticker prefix first, ties by ticker');
  assert.deepEqual(codes(c.find('nv', 1)), ['NASDAQ:NVDA'], 'limit');
  assert.ok(c.find('a').length > 8, 'no limit: every match'); assert.ok(Object.isFrozen(c.find('a')));
  for (const bad of [0, -1, 1.5, '3', null]) assert.throws(() => c.find('a', bad), /LIMIT_INVALID/, String(bad));
  assert.deepEqual(codes(c.find('nasdaq:nvda')), ['NASDAQ:NVDA']); assert.deepEqual(codes(c.find('brk-b')).slice(0, 1), ['NYSE:BRK.B']);
  assert.deepEqual(codes(c.find('qualcomm')), ['NASDAQ:QCOM']);
  for (const q of ['퀄컴', '엔비디아', 'hanmi', '', '  ', null, undefined]) assert.deepEqual([...c.find(q)], [], String(q));
  assert.equal(c.korean('퀄컴'), true); assert.equal(c.korean('nv'), false); assert.equal(c.korean(undefined), false);
  assert.equal(c.exact('comfort systems usa inc').code, 'NYSE:FIX'); assert.equal(c.exact('alphabet inc'), null); assert.equal(c.exact('nv'), null);
  assert.equal(c.exact('googl').id, 'googl'); assert.equal(c.exact('퀄컴'), null);
});

test('companies: a listing-ended code is WITHDRAWN (WBD shown as delisted), still listed and found; scope()', async () => {
  const { C: c } = companies(); await c.ready();
  assert.deepEqual(plain(ENDED), { 'NASDAQ:WBD': { effective: '2026-10-06' } }, 'the table of search-part-live.js (kept equal to the server table)');
  const wbd = c.get('NASDAQ:WBD');
  assert.deepEqual([wbd.status, wbd.withdrawn_on, wbd.official], ['WITHDRAWN', '2026-10-06', true]);
  assert.equal(c.find('wbd')[0], wbd, 'found'); assert.equal(c.find('warner')[0], wbd, 'found by its English name'); assert.equal(c.exact('wbd'), wbd);
  assert.deepEqual(c.list().filter((x) => x.status === 'WITHDRAWN').map((x) => x.code), Object.keys(ENDED));
  assert.ok(c.list().filter((x) => x.status === 'ACTIVE').every((x) => x.withdrawn_on === null));
  assert.deepEqual(plain(c.scope()), { id: 'UNIVERSE504', label: 'Universe504', as_of: null }); assert.ok(Object.isFrozen(c.scope()));
  assert.equal(c.scope(), C.SCOPE);
});

test('companies: a missing part is read again; no table or no layer fails closed; ready() never rejects', async () => {
  const noNames = companies({ names: null }), a = await noNames.C.ready();
  assert.deepEqual(plain(a), { state: 'PARTIAL', size: 504, missing: ['영문 회사명 표'] });
  assert.equal(noNames.C.get('NASDAQ:NVDA').name_en, null); assert.equal(noNames.C.find('nvda')[0].code, 'NASDAQ:NVDA', 'tickers still work');
  await noNames.C.ready(); assert.equal(noNames.calls.universe, 2, 'read again after a missing part');
  const noCodes = companies({ codes: null }), b = await noCodes.C.ready();
  assert.deepEqual(plain(b), { state: 'FAILED', size: 0, missing: ['Universe504 목록'] }); assert.deepEqual([...noCodes.C.find('nvda')], []);
  for (const ended of [() => undefined, null, 'x', { 'NASDAQ:WBD': { effective: 'soon' } }, { WBD: { effective: '2026-10-06' } }]) {
    const n = companies({ ended }), x = await n.C.ready();
    assert.deepEqual(plain(x), { state: 'FAILED', size: 0, missing: ['상장 종료 표'] }, 'without the listing-ended table nothing is shown as active: ' + JSON.stringify(ended));
    assert.deepEqual(n.calls, { universe: 0, static: [] });
  }
  const late = companies({ ended: () => ENDED }); assert.equal((await late.C.ready()).state, 'OK', 'the table is taken when ready() runs');
  const broken = companies({ fail: true }), y = await broken.C.ready();
  assert.deepEqual(plain(y), { state: 'FAILED', size: 0, missing: ['Universe504 목록', '영문 회사명 표'] });
});

test('one code path: the home search and the company index read companies only through IS2.companies', () => {
  const part = code(fs.readFileSync(R.newPath('search-part-live.js'), 'utf8')), live = code(fs.readFileSync(R.newPath('screen-search-live.js'), 'utf8'));
  assert.doesNotMatch(part, /\.universe\(|company-names-ko|\.static\(|I\.data\b/, 'search-part-live.js reads no file itself');
  assert.match(part, /I\.companies/);
  assert.doesNotMatch(live, /\.universe\(|LISTING_ENDED/, 'screen-search-live.js takes codes, links and WITHDRAWN from IS2.companies');
  assert.match(live, /C\.ready\(\)/); assert.match(live, /I\.companies\.get\(/);
  const comp = code(fs.readFileSync(R.newPath('companies.js'), 'utf8'));
  assert.doesNotMatch(comp, /fetch\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|document\.cookie/);
});

/* ---------------------------------------------------------------- IS2.lab: validate */
test('lab validate: the fixture payload is accepted as a deep-frozen copy; the argument is untouched', () => {
  const p = F.payload(), r = L.validate(p);
  assert.equal(r.ok, true); assert.ok(Object.isFrozen(r)); deepFrozen(r.value);
  assert.deepEqual(plain(r.value), plain(p)); assert.notEqual(r.value, p); assert.equal(Object.isFrozen(p), false, 'the input is not frozen');
  assert.equal(r.value.runs.length, 2); assert.equal(r.value.runs[0].metrics.sharpe, null);
  for (const [name, make] of F.valid) { const v = L.validate(make()); assert.equal(v.ok, true, name + ': ' + JSON.stringify(v)); deepFrozen(v.value); }
  // Fixture metrics are computed from the curve (synthetic values): the checks hold by construction.
  const run0 = p.runs[0], last = run0.equity_curve.at(-1);
  assert.ok(Math.abs(run0.metrics.total_return - (last.strategy / 100 - 1)) <= 1e-4);
  assert.ok(run0.metrics.max_drawdown < F.drawdown(run0.equity_curve), 'the pilot has a daily drawdown deeper than the monthly one');
  assert.equal(run0.period.end, '2025-06-20'); assert.equal(last.date, '2025-06', 'a partial last month');
  for (const r0 of p.runs) assert.ok(r0.description.includes('시험용 합성 값'), 'marked synthetic');
});

test('lab validate: each invalid variant is refused, whole, with its code and path', () => {
  const seen = new Set();
  for (const [name, codeWanted, at, make] of F.invalid) {
    const r = L.validate(make());
    assert.deepEqual({ ...r }, { ok: false, code: codeWanted, path: at }, name); assert.ok(Object.isFrozen(r)); assert.equal('value' in r, false, name + ': nothing of the file is kept');
    seen.add(codeWanted);
  }
  const RULES = ['NOT_OBJECT', 'SCHEMA_VERSION', 'KEY_MISSING', 'KEY_UNKNOWN', 'TYPE', 'TOO_LARGE', 'ID_INVALID', 'ENUM', 'DATE_INVALID', 'PERIOD_ORDER', 'GENERATED_AT_ZONE',
    'SOURCE_COMMIT', 'RUN_ID_DUPLICATE', 'NUMBER_NOT_FINITE', 'NULL_REASON_MISSING', 'NULL_REASON_KEY', 'NULL_REASON_UNUSED', 'MAX_DRAWDOWN_RANGE', 'VOLATILITY_RANGE',
    'COST_NEGATIVE', 'EXCESS_CAGR_MISMATCH', 'TOTAL_RETURN_MISMATCH', 'CAGR_MISMATCH', 'BENCHMARK_CAGR_MISMATCH', 'MAX_DRAWDOWN_MISMATCH', 'CURVE_START', 'CURVE_END',
    'CURVE_ORDER', 'CURVE_DUPLICATE', 'CURVE_TOO_SHORT', 'CURVE_VALUE'];
  assert.deepEqual([...seen].sort(), [...RULES].sort(), 'one variant (at least) per rule');
});

test('lab validate: tolerances, non-JSON values, __proto__ and depth', () => {
  const ok = (fn) => { const p = F.payload(); fn(p.runs[0]); return L.validate(p); };
  const m = (r) => r.metrics;
  assert.equal(ok((r) => { m(r).excess_cagr += 5e-7; }).ok, true, 'excess_cagr within 1e-6');
  assert.equal(ok((r) => { m(r).total_return += 5e-5; m(r).cagr = m(r).cagr; }).ok, true, 'total_return within 1e-4');
  assert.equal(ok((r) => { m(r).cagr += 0.0015; m(r).excess_cagr = m(r).cagr - m(r).benchmark_cagr; }).ok, true, 'cagr within 0.002');
  assert.equal(ok((r) => { m(r).cagr += 0.0025; m(r).excess_cagr = m(r).cagr - m(r).benchmark_cagr; }).code, 'CAGR_MISMATCH');
  assert.equal(ok((r) => { m(r).benchmark_cagr -= 0.0019; m(r).excess_cagr = m(r).cagr - m(r).benchmark_cagr; }).ok, true, 'benchmark_cagr within 0.002');
  const mdd = (r) => F.drawdown(r.equity_curve);
  assert.equal(ok((r) => { m(r).max_drawdown = mdd(r) + 5e-5; }).ok, true, 'max_drawdown milder by less than 1e-4');
  assert.equal(ok((r) => { m(r).max_drawdown = mdd(r) + 2e-4; }).code, 'MAX_DRAWDOWN_MISMATCH');
  assert.equal(ok((r) => { m(r).max_drawdown = -1; }).ok, true, '-1 is the floor');
  for (const v of [new Date(0), new Map(), () => 1, undefined, Symbol('x'), 10n]) assert.equal(ok((r) => { r.name = v; }).code, 'TYPE', String(typeof v));
  assert.deepEqual({ ...L.validate(JSON.parse(JSON.stringify(F.payload()).replace('{"schema_version"', '{"__proto__":{"x":1},"schema_version"'))) }, { ok: false, code: 'KEY_UNKNOWN', path: '$.__proto__' });
  let deep = 1; for (let i = 0; i < 20; i++) deep = { d: deep };
  const p = F.payload(); p.extra = deep; assert.equal(L.validate(p).code, 'TOO_DEEP');
  assert.equal(L.validate(F.payload()).ok, true, 'validate keeps no state between calls');
});

/* ---------------------------------------------------------------- IS2.lab: status, nullText, source */
test('lab status: the owner\'s texts exactly', () => {
  const [pilot, synthetic] = F.payload().runs;
  assert.equal(L.status(undefined), '연구 결과가 아직 없습니다'); assert.equal(L.status(null), '연구 결과가 아직 없습니다');
  assert.equal(L.status(pilot), '실데이터 파일럿 · 미검증');
  assert.equal(L.status(synthetic), '합성 데이터 · 시험용');
  assert.equal(L.status(F.mixedRun()), '실데이터와 합성 데이터 혼합 · 파일럿 · 미검증');
  assert.equal(L.status(F.pitFalseRun()), '실데이터 파일럿 · 미검증 · 모집단 시점 정합성 미확인');
  const v = (o) => ({ ...pilot, ...o });
  assert.equal(L.status(v({ run_type: 'FORMAL' })), '실데이터 정식 실행 · 미검증');
  assert.equal(L.status(v({ validation_status: 'PIT_VERIFIED' })), '실데이터 파일럿 · 입력 시점 검증됨');
  assert.equal(L.status(v({ validation_status: 'REVIEWED', run_type: 'FORMAL' })), '실데이터 정식 실행 · 검토 완료');
  assert.equal(L.status(v({ data_status: 'MIXED', validation_status: 'REVIEWED', universe: { ...pilot.universe, point_in_time: false } })), '실데이터와 합성 데이터 혼합 · 파일럿 · 검토 완료 · 모집단 시점 정합성 미확인');
  assert.equal(L.status({ ...synthetic, universe: { ...synthetic.universe, point_in_time: false } }), '합성 데이터 · 시험용', 'universe timing is not a synthetic run\'s question');
  // An unverified run never reads as verified.
  for (const r of [pilot, F.mixedRun(), F.pitFalseRun()]) assert.doesNotMatch(L.status(r), /검증됨|검토 완료/);
  for (const bad of [{}, { ...pilot, data_status: 'X' }, 'run', 3]) assert.throws(() => L.status(bad), /LAB_RUN_INVALID/);
  assert.equal(L.nullText(pilot, 'sharpe'), '– · 무위험 수익률 기준 미정 (시험용)');
  assert.equal(L.nullText(pilot, 'cagr'), null);
  assert.throws(() => L.nullText(pilot, 'alpha'), /LAB_METRIC_UNKNOWN/);
  assert.equal(L.TEXT.EMPTY, '연구 결과가 아직 없습니다'); assert.equal(L.TEXT.PRIVATE_LOGIN_REQUIRED, '비공개 연구 결과 · 로그인 필요'); deepFrozen(L.TEXT);
});

test('lab source(): NONE with PRIVATE_NOT_READY, no request, no data read, no public lab file', async () => {
  const touched = [], data = new Proxy({}, { get(t, k) { touched.push(String(k)); return () => { throw new Error('no data read'); }; } });
  const win = R.nodeWindow(), IS2 = { data };
  // As the page installs them: private.js, then lab.js, on one IS2 of a browser-like window.
  for (const n of ['private.js', 'lab.js']) vm.runInNewContext(fs.readFileSync(R.newPath(n), 'utf8'), { IS2, Object, fetch: win.fetch, window: win }, { filename: n });
  const r = await IS2.lab.source();
  assert.deepEqual({ ...r }, { state: 'NONE', code: 'LAB_NO_PUBLIC_RESULT', payload: null, private: 'PRIVATE_NOT_READY', text: '연구 결과가 아직 없습니다', private_text: '비공개 기능 준비 중' });
  assert.ok(Object.isFrozen(r)); assert.deepEqual(win.requests, [], 'no request'); assert.deepEqual(touched, [], 'IS2.data is never touched');
  const later = L.create({ privateArea: { state: () => 'LOGIN_REQUIRED', text: () => '로그인 필요' } }), x = await later.source();
  assert.deepEqual([x.state, x.private, x.private_text], ['NONE', 'PRIVATE_LOGIN_REQUIRED', '비공개 연구 결과 · 로그인 필요'], 'a later private path, not signed in');
  assert.equal((await L.create({}).source()).private, 'PRIVATE_NOT_READY', 'without the private area: not ready');
  const lab = code(fs.readFileSync(R.newPath('lab.js'), 'utf8'));
  assert.doesNotMatch(lab, /fetch\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|document\.cookie|strictFetch|\.static\(/, 'lab.js requests and stores nothing');
  const FILES = fresh('data.js').FILES;
  assert.deepEqual(FILES.filter((n) => /lab|backtest/i.test(n)), [], 'no public Lab file in IS2.data.FILES');
});

/* ---------------------------------------------------------------- IS2.privateArea */
test('privateArea: NOT_READY today; the Korean lines; no network, storage or sign-in', () => {
  const a = P.create();
  assert.equal(a.state(), 'NOT_READY');
  assert.equal(a.text(), '비공개 기능 준비 중'); assert.equal(a.text('NOT_READY'), '비공개 기능 준비 중'); assert.equal(a.text('NOT_READY', 'lab'), '비공개 기능 준비 중');
  assert.equal(a.text('LOGIN_REQUIRED'), '로그인 필요'); assert.equal(a.text('LOGIN_REQUIRED', 'lab'), '비공개 연구 결과 · 로그인 필요');
  assert.equal(a.text('SIGNED_IN'), '비공개 영역 연결됨');
  for (const s of P.STATES) for (const area of [undefined, 'lab']) assert.doesNotMatch(a.text(s, area), /로그인됨/);
  assert.throws(() => a.text('LOGGED_IN'), /PRIVATE_STATE_UNKNOWN/); assert.throws(() => a.text('NOT_READY', 'kis'), /PRIVATE_AREA_UNKNOWN/);
  assert.deepEqual([...a.STATES], ['NOT_READY', 'LOGIN_REQUIRED', 'SIGNED_IN']); assert.ok(Object.isFrozen(a) && Object.isFrozen(a.STATES));
  const src = code(fs.readFileSync(R.newPath('private.js'), 'utf8'));
  assert.doesNotMatch(src, /fetch\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|cookie|google|accounts\./i);
});

test('privateArea panels: one set of states and words for every screen (public + private two layers)', () => {
  const a = P.create();
  assert.deepEqual([...a.PANEL_STATES], ['NOT_READY', 'LOGIN_REQUIRED', 'LOADING', 'ERROR', 'EMPTY', 'READY']);
  assert.equal(a.panelState(), 'NOT_READY');
  assert.equal(a.panelText('NOT_READY'), '비공개 기능 준비 중'); assert.equal(a.panelText('LOGIN_REQUIRED'), '로그인 필요');
  assert.equal(a.panelText('LOGIN_REQUIRED', { area: 'lab' }), '비공개 연구 결과 · 로그인 필요');
  assert.equal(a.panelText('LOADING'), '비공개 자료 불러오는 중'); assert.equal(a.panelText('EMPTY'), '비공개 자료가 아직 없습니다'); assert.equal(a.panelText('READY'), '');
  assert.equal(a.panelText('ERROR'), '비공개 자료를 불러오지 못했습니다');
  assert.equal(a.panelText('ERROR', { code: 'ACCESS_REQUIRED' }), '비공개 자료를 불러오지 못했습니다 · ACCESS_REQUIRED');
  assert.throws(() => a.panelText('ERROR', { code: 'see https://x' }), /PRIVATE_CODE_INVALID/);
  assert.throws(() => a.panelText('SIGNED_IN'), /PRIVATE_PANEL_STATE_UNKNOWN/); assert.throws(() => a.panelText('EMPTY', { area: 'kis' }), /PRIVATE_AREA_UNKNOWN/);
  for (const s of a.PANEL_STATES) assert.doesNotMatch(a.panelText(s), /로그인됨|\d/);
});

/* ---------------------------------------------------------------- loading and the loader */
test('loading companies.js, private.js and lab.js puts only their own namespace on IS2 and reads nothing', () => {
  for (const [n, ns] of [['companies.js', 'companies'], ['private.js', 'privateArea'], ['lab.js', 'lab']]) {
    const seen = [], IS2 = new Proxy({}, { get(t, k) { seen.push('get ' + String(k)); return t[k]; }, set(t, k, v) { seen.push('set ' + String(k)); t[k] = v; return true; } });
    vm.runInNewContext(fs.readFileSync(R.newPath(n), 'utf8'), { IS2, Object }, { filename: n });
    assert.deepEqual(seen, ['set ' + ns], n);
  }
});

test('loader: the common base loads after the layer and before the screens, with facades', () => {
  const Lo = fresh('loader.js'), order = [...Lo.LOAD_ORDER], at = (n) => order.indexOf(n);
  assert.deepEqual(order.slice(at('engines.js'), at('search-part-live.js') + 1), ['engines.js', 'companies.js', 'private.js', 'lab.js', 'search-part-live.js']);
  assert.deepEqual({ companies: Lo.NAMESPACES.companies, privateArea: Lo.NAMESPACES.privateArea, lab: Lo.NAMESPACES.lab }, { companies: 'companies.js', privateArea: 'private.js', lab: 'lab.js' });
  assert.deepEqual(Object.keys(Lo.API.companies).sort(), Object.keys(C.create({})).sort());
  assert.deepEqual(Object.keys(Lo.API.lab).sort(), Object.keys(L.create({})).sort());
  assert.deepEqual(Object.keys(Lo.API.privateArea).sort(), Object.keys(P.create()).sort());
  assert.deepEqual(R.loadOrder(), order, 'the build and the helper read the same list');
});

test('parts.notReady: the shared 준비 중 line, with what is missing, no number of its own', () => {
  const made = [], h = (tag, attrs, ...kids) => { const el = { tag, attrs, kids: kids.flat().filter((k) => k !== null && k !== undefined && k !== '') }; made.push(el); return el; };
  const IS2 = { h, href: () => '#/', register: () => {}, icon: () => null };
  vm.runInNewContext(fs.readFileSync(R.newPath('parts.js'), 'utf8'), { window: IS2.window = { IS2 }, Object, Array, setTimeout, AbortController }, { filename: 'parts.js' });
  const text = (el) => el.kids.map((k) => (typeof k === 'string' ? k : text(k))).join('');
  const a = IS2.parts.notReady('비공개 기능 준비 중');
  assert.deepEqual([a.tag, a.attrs.class, Object.keys(a.attrs.dataset)], ['p', 'pending not-ready', ['notReady']]); assert.equal(text(a), '비공개 기능 준비 중');
  const b = IS2.parts.notReady('공식 국면 미산출 · 준비 중', ['국면 모델', '과거 국면 기록']);
  assert.equal(text(b), '공식 국면 미산출 · 준비 중 · 없는 것: 국면 모델 · 과거 국면 기록');
  assert.equal(text(IS2.parts.notReady('준비 중', [])), '준비 중');
});
