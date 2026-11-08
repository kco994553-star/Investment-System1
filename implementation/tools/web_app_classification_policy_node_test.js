'use strict';
// 공통 분류 /2 경계 정책판 (owner 2026-11-08 「새 분류 버전 대기를 종료하고 최신 인계본을 연결하라」 2·5항):
// web_app/classification.js on Codex #520 41f2a25b output for its six synthetic boundary cases.
//  - Input: tests/fixtures/common_classification_main/policy_v2_fixture.json — Codex's own functions on Codex's own
//    boundary-policy-v2.json (pytest checks it byte for byte), SHA-256 pinned here. Main writes no view and no expected value.
//  - Each case reads whole (/2 view + /2 dictionary + macro of the same record), and recordFor gives Codex's expected sector and
//    accounting model; an unconfirmed accounting model stays 미확인 (never GENERAL), an unconfirmed sector stays unclassified.
//  - The old /1 bundle (main_fixture.json) still reads; a /2 view with the /1 dictionary, a /1 view with the /2 dictionary, a /2 view
//    with map/1, an unknown version, a dropped policy, a hash changed in the macro part are refused or kept aside.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const C = require('../src/investment_system/product/web_app/classification.js');
const X = require('./web_app_classification_fixture.js');
const { ROOT } = require('./web_app_reuse');

const POLICY_PATH = path.join(ROOT, 'implementation/tests/fixtures/common_classification_main/policy_v2_fixture.json');
const POLICY_SHA256 = 'b66d8f2a7f82f790e23ae0dbbf01d960f41bd5db558df1625f40d9e6d1837864';
let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const clone = (v) => JSON.parse(JSON.stringify(v));
const P = JSON.parse(fs.readFileSync(POLICY_PATH, 'utf8'));
const bundleOf = (c) => ({ view: c.view, macro: c.macro, dictionary: P.dictionary });
const refused = (b, code) => { const r = C.validate(b); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); };

ok('the /2 fixture is the pinned Codex output (six cases)', () => {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(POLICY_PATH)).digest('hex'), POLICY_SHA256);
  assert.deepEqual(P.cases.map((c) => c.case_id), ['reit-sector-only', 'managed-care-sector-only', 'broadcast-primary', 'newspaper-primary', 'real-estate-not-reit', 'mixed-cable-needs-business']);
  assert.deepEqual(C.VERSION_PAIRS, { 'common-industry-dictionary/1': 'common-classification-map/1', 'common-industry-dictionary/2': 'common-classification-map/2' });
});

ok('each /2 case reads whole; recordFor gives Codex expected sector and accounting; policy named; no GENERAL fill', () => {
  for (const c of P.cases) { const id = c.case_id;
    const r = C.validate(bundleOf(c)); assert.equal(r.ok, true, id + ' ' + JSON.stringify(r));
    assert.deepEqual(r.value.mismatch, {}, id + ': the macro part reads the same record');
    const row = c.view.rows[0], rec = C.recordFor(row.company_id, null, r.value);
    assert.equal(rec.dictionary_version, 'common-industry-dictionary/2', id); assert.equal(rec.mapping_version, 'common-classification-map/2', id);
    assert.deepEqual(rec.boundary_policy, { version: P.dictionary.policy.version, approved_date: P.dictionary.policy.approved_date }, id);
    const sector = c.expected.sector_id, acc = c.expected.accounting_template;
    assert.equal(rec.sector && rec.sector.id, sector, id + ': sector');
    assert.equal(rec.sector.status, sector === null ? rec.sector.status : 'CONFIRMED', id);
    if (sector === null) assert.notEqual(rec.sector.status, 'CONFIRMED', id + ': an unconfirmed sector is never shown as confirmed');
    assert.equal(rec.accounting && rec.accounting.id, acc, id + ': accounting model');
    if (acc === null) { assert.notEqual(rec.accounting_state, 'CONFIRMED', id); assert.equal(rec.peer_complete, false, id); }
    else assert.equal(rec.peer_complete, sector !== null, id);
    assert.equal(rec.source_sic.code, row.source_sic.code, id + ': the source SIC line stays the source value');
  }
});

ok('the old /1 bundle still reads (no policy on /1)', () => {
  const v = C.validate(X.bundle()); assert.equal(v.ok, true, JSON.stringify(v));
  assert.equal(v.value.view.dictionary_version, 'common-industry-dictionary/1');
  const id = v.value.view.rows[0].company_id;
  assert.equal(C.recordFor(id, null, v.value).boundary_policy, null);
});

ok('mixed pairs, unknown versions, a dropped policy and a changed hash are refused or kept aside', () => {
  const c = P.cases.find((x) => x.case_id === 'reit-sector-only'), M = X.main();
  refused({ ...bundleOf(c), dictionary: M.dictionary }, 'CLASSIFICATION_VERSION_MISMATCH');             // /2 view, /1 dictionary
  refused({ ...X.bundle(M), dictionary: P.dictionary }, 'CLASSIFICATION_VERSION_MISMATCH');            // /1 view, /2 dictionary
  let b = clone(bundleOf(c)); b.view.mapping_version = 'common-classification-map/1'; assert.equal(C.validate(b).ok, false, '/2 + map/1');
  b = clone(bundleOf(c)); b.view.dictionary_version = 'common-industry-dictionary/3'; b.view.mapping_version = 'common-classification-map/3'; assert.equal(C.validate(b).ok, false, 'unknown /3');
  b = clone(bundleOf(c)); delete b.view.boundary_policy; assert.equal(C.validate(b).ok, false, '/2 without policy');
  b = clone(bundleOf(c)); delete b.dictionary.policy; assert.equal(C.validate(b).ok, false, '/2 dictionary without policy');
  b = clone(bundleOf(c)); b.dictionary.policy.version = 'common-sector-boundaries/2026-11-09.1'; refused(b, 'CLASSIFICATION_POLICY_MISMATCH');
  b = clone(bundleOf(c)); b.dictionary.policy.book_direct_claim = true; assert.equal(C.validate(b).ok, false, 'a book claim');
  b = clone(bundleOf(c)); b.macro.classification_hash = 'f'.repeat(64); const r = C.validate(b);
  assert.equal(r.ok, true); assert.ok(r.value.mismatch.macro, 'a macro part of another hash is kept aside, never joined'); assert.equal(r.value.macro, null);
});

console.log(JSON.stringify({ passed: true, checks: n }));
