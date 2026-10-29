'use strict';
// The shared company search (web_app/search-part-live.js, DC-23, owner 2026-10-27) over the real public inputs: the fixed 504
// codes (universe/universe_codes_v1.json, the source of universe-codes.json) and the reviewed names table
// (web_assets/company-names-ko.json), in a vm with a stub IS2.data.
//  - Universe504 only: 504 entries; a TARGET company outside the Universe (hanmi, tokyo_electron) and Korean names are not found;
//    Korean text gives nothing (the box shows a fixed hint).
//  - Keys and order: ticker (case, '.', '-' ignored; a full code too) before the English name (prefix, then a word prefix, then a
//    part); ties by ticker. An id is the TARGET company_id linked to the code, else the code.
//  - exact(): one exact ticker / code, else one exact English name, else null.
//  - Listing-ended codes are found and say so (WBD). The index is built once per page; a missing names file is built again.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const R = require('./web_app_reuse');

const ES = R.requireOld('entity-search.js');
const CODES = JSON.parse(fs.readFileSync(path.join(R.ROOT, 'implementation/src/investment_system/universe/universe_codes_v1.json'), 'utf8'));
const NAMES = JSON.parse(fs.readFileSync(R.oldPath('company-names-ko.json'), 'utf8'));

function load({ codes = CODES, names = NAMES } = {}) {
  const calls = { universe: 0, names: 0 };
  const IS2 = { h: () => null, data: { universe: async () => { calls.universe++; return codes; }, static: async (n) => { assert.equal(n, 'company-names-ko.json'); calls.names++; return names ? ES.nameIndex(names) : null; } } };
  vm.runInNewContext(fs.readFileSync(R.newPath('search-part-live.js'), 'utf8'), { window: { IS2 }, Object }, { filename: 'search-part-live.js' });
  return { P: IS2.searchPart, calls };
}
// Arrays made in the vm have its own prototype: copy them into this realm before deepEqual.
const codes = (hits) => Array.from(hits, (e) => e.code);
const all = (hits) => Array.from(hits);

test('search part: loading the file touches nothing and hands index, attach and the listing-ended table', () => {
  const { P, calls } = load();
  assert.deepEqual(Object.keys(P), ['index', 'attach', 'LISTING_ENDED']);
  assert.deepEqual(calls, { universe: 0, names: 0 }, 'no read at load');
  assert.deepEqual(JSON.parse(JSON.stringify(P.LISTING_ENDED)), { 'NASDAQ:WBD': { effective: '2026-10-06' } });
});

test('search part: Universe504 only, ticker and English name, never Korean names or TARGET-only companies', async () => {
  const { P } = load(), idx = await P.index();
  assert.equal(idx.size, 504); assert.deepEqual([...idx.missing], []);
  const nv = idx.search('nv');
  assert.deepEqual(codes(nv).slice(0, 2), ['NASDAQ:NVDA', 'NYSE:NVR'], 'ticker prefix first, ties by ticker');
  assert.equal(nv[0].id, 'nvda', 'a code linked to a TARGET company opens that company');
  assert.equal(idx.title(nv[0]), 'NVDA · NVIDIA CORP');
  assert.deepEqual(codes(idx.search('NVDA')), ['NASDAQ:NVDA']);
  assert.deepEqual(codes(idx.search('nasdaq:nvda')), ['NASDAQ:NVDA'], 'a full code');
  assert.deepEqual(codes(idx.search('brk-b')).slice(0, 1), ['NYSE:BRK.B'], "'.' and '-' are the same in a ticker");
  assert.equal(idx.title(idx.search('brk.b')[0]), 'BRK.B · BERKSHIRE HATHAWAY INC Class B');
  const micro = codes(idx.search('micro'));
  for (const c of ['NASDAQ:MSFT', 'NASDAQ:AMD', 'NASDAQ:MU', 'NASDAQ:MCHP']) assert.ok(micro.includes(c), 'micro finds ' + c);
  assert.ok(micro.indexOf('NASDAQ:MSFT') < micro.indexOf('NASDAQ:AMD'), 'a name prefix before a word prefix');
  assert.deepEqual(codes(idx.search('qualcomm')), ['NASDAQ:QCOM']);
  assert.equal(idx.search('qualcomm')[0].id, 'qcom');
  for (const q of ['퀄컴', '엔비디아', 'hanmi', '한미반도체', 'tokyo electron', 'TEL']) assert.ok(!codes(idx.search(q)).some((c) => !c.includes(':')), q);
  assert.deepEqual(all(idx.search('퀄컴')), [], 'Korean text finds nothing (the box shows the hint)');
  assert.deepEqual(all(idx.search('hanmi')), [], 'a TARGET company outside Universe504 is not found');
  assert.deepEqual(all(idx.search('zzzzqqq')), []);
  assert.deepEqual(all(idx.search('  ')), []);
  for (const e of idx.search('a')) { assert.match(e.code, /^(NYSE|NASDAQ|BATS):/); assert.equal(Object.keys(e).filter((k) => /price|cap|score|rank/i.test(k)).length, 0); }
});

test('search part: exact match and listing-ended codes', async () => {
  const { P } = load(), idx = await P.index();
  assert.equal(idx.exact('nvda').code, 'NASDAQ:NVDA'); assert.equal(idx.exact('NYSE:FIX').id, 'NYSE:FIX');
  assert.equal(idx.exact('goog').code, 'NASDAQ:GOOG'); assert.equal(idx.exact('googl').id, 'googl');
  assert.equal(idx.exact('comfort systems usa inc').code, 'NYSE:FIX', 'one exact English name');
  assert.equal(idx.exact('alphabet inc'), null, 'two share classes: no single exact match');
  assert.equal(idx.exact('nv'), null); assert.equal(idx.exact('퀄컴'), null);
  const wbd = idx.search('wbd')[0];
  assert.equal(wbd.code, 'NASDAQ:WBD'); assert.deepEqual(JSON.parse(JSON.stringify(wbd.ended)), { effective: '2026-10-06' });
  assert.equal(idx.search('warner')[0].code, 'NASDAQ:WBD', 'found by its English name too');
  assert.equal(idx.search('nvda')[0].ended, null);
  assert.equal(idx.get('nvda').code, 'NASDAQ:NVDA'); assert.equal(idx.get('NASDAQ:NVDA').id, 'nvda'); assert.equal(idx.get('hanmi'), null);
});

test('search part: one build per page; a missing file is read again on the next index()', async () => {
  const ok = load();
  await ok.P.index(); await ok.P.index();
  assert.deepEqual(ok.calls, { universe: 1, names: 1 }, 'built once');
  const noNames = load({ names: null }), a = await noNames.P.index();
  assert.deepEqual([...a.missing], ['영문 회사명 표']); assert.equal(a.title(a.search('nvda')[0]), 'NVDA', 'ticker only without names');
  await noNames.P.index();
  assert.equal(noNames.calls.universe, 2, 'built again after a missing file');
  const noCodes = load({ codes: null }), b = await noCodes.P.index();
  assert.deepEqual([...b.missing], ['Universe504 목록']); assert.equal(b.size, 0); assert.deepEqual(all(b.search('nvda')), []);
});
