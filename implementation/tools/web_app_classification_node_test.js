'use strict';
// 공통 분류 (DC-48, owner 2026-11-07): web_app/classification.js (IS2.classification) on Codex common-classification/1 output.
//  - Input: tests/fixtures/common_classification_main/main_fixture.json — Codex's own functions on Codex's own cases (pytest
//    checks it byte for byte), SHA-256 pinned; Codex's handoff files keep the manifest SHA-256 (contract 00bccc2c…, fixtures
//    526cbf85…, dictionary 9ae49c5f…).
//  - Every record case reads with Codex's statuses and gives one of the distinct state words; the Codex error case has no view.
//  - Tampered hash / version / record id refused or kept aside as 분류 버전 불일치; parts of another run never join.
//  - groupRows: the confirmed board group's FULL rows (every member, also those not keyed for the board), never an intersection;
//    issuer_id from the record, signal_day / security_id never made up; null with a code when anything is unknown.
//  - Small samples kept apart (tech N < 10, sector QGV N < 20, empty group, membership unknown).
//  - The same company / date reads the same classification_record_id and classification_hash in detail (view), QGV (qgv links),
//    technical and macro.
//  - source() NONE, no request; hash context token round trip.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const C = require('../src/investment_system/product/web_app/classification.js');
const T = require('../src/investment_system/product/web_app/tech-screen.js');
const X = require('./web_app_classification_fixture.js');

let n = 0;
const ok = async (name, fn) => { await fn(); n++; console.log('PASS ' + name); };
const M = X.main(), CODEX = X.codexFixtures();
const clone = (v) => JSON.parse(JSON.stringify(v));
const valid = (p) => { const r = C.validate(p); assert.equal(r.ok, true, JSON.stringify(r)); return r.value; };
const IT = 'INFORMATION_TECHNOLOGY';
const itBoard = (tech) => tech.groups.find((g) => g.sector_id === IT).board;
// Universe rows as qgv.js rowRecord makes them (id = code = company_id for a Universe504 row; issuer_id / signal_day / security_id null).
const uni = (ids, extra = []) => [...ids, ...extra].map((id, i) => ({ id, code: id, ticker: 'SYNTHETIC:TICKER:' + i, issuer_id: null, signal_day: null, security_id: null }));

(async () => {
  await ok('pins: Main fixture and Codex handoff files unchanged', () => {
    assert.equal(X.mainSha(), X.MAIN_SHA256);
    for (const [name, want] of Object.entries(X.HANDOFF_SHA256)) assert.equal(X.handoffSha(name), want, name);
    assert.deepEqual(M.codex_handoff.sha256, X.HANDOFF_SHA256);
    assert.equal(Object.keys(M.record_cases).length, 13); assert.equal(Object.keys(M.technical_cases).length, 9);
  });

  const WANT = { normal: 'CONFIRMED', multiple_business_tags: 'SECTOR_ONLY', sector_only: 'SECTOR_ONLY', unclassified: 'NO_DATA', change_before_known: 'SECTOR_ONLY',
    change_after_known: 'SECTOR_ONLY', future_source: 'NO_DATA', reit_exception: 'UNRESOLVED', modern_communication_exception: 'UNRESOLVED',
    book_telecommunications: 'SECTOR_ONLY', outside_interval: 'NOT_APPLICABLE_ON_DATE', conflicting_primary_sector: 'CONFLICT' };
  await ok('every record case: Codex statuses read as they are, one state per case, Codex error case has no view', () => {
    for (const [name, c] of Object.entries(M.record_cases)) {
      const want = CODEX.record_cases[name].expected;
      if (want.error) { assert.equal(c.view, null, name); assert.equal(c.error, want.error); continue; }
      const b = valid(X.recordCase(name)), row = c.view.rows[0], rec = C.recordFor(row.company_id, null, b);
      assert.equal(rec.state, WANT[name], name); assert.equal(rec.sector.status, want.sector_status, name); assert.equal(rec.industry.status, want.industry_status, name);
      assert.equal(rec.record_id, row.record_id); assert.equal(rec.classification_hash, c.view.classification_hash); assert.equal(rec.security_id, null, 'a record has no security id');
      if (want.reason) assert.ok(rec.sector.reasons.includes(want.reason), name);
      assert.ok(!/(^|\s)0(\s|$)|기타/.test(rec.words), 'unknown never 0 or 기타: ' + rec.words);
    }
    assert.equal(C.recordFor('COMPANY:A', null, valid(X.recordCase('change_before_known'))).sector.id, IT);
    assert.equal(C.recordFor('COMPANY:A', null, valid(X.recordCase('change_after_known'))).sector.id, 'HEALTH_CARE', 'later correction known later');
    const reit = C.recordFor('COMPANY:A', null, valid(X.recordCase('reit_exception')));
    assert.equal(reit.words, '섹터 대응 미확인 · 근거 부족 (REIT_UPPER_SECTOR_UNRESOLVED)', 'UNRESOLVED code as is');
    assert.equal(C.recordFor('COMPANY:A', null, valid(X.recordCase('outside_interval'))).words, '평가일 2026-11-04에 적용되는 분류 없음');
    const conflict = valid(X.recordCase('conflicting_primary_sector'));
    for (const id of ['COMPANY:A', 'COMPANY:B']) { const r = C.recordFor(id, null, conflict); assert.equal(r.words, '분류 충돌 · 근거 불일치'); assert.equal(r.sector.id, null); }
    assert.equal(C.recordFor('COMPANY:A', null, valid(X.recordCase('normal'))).industry.id, 'software');
  });

  await ok('other evaluation date: Codex EVALUATION_ONLY on another day and a request for another day both say 적용되는 분류 없음', () => {
    const v = M.variants.normal_other_date, b = valid({ view: v.view, macro: v.macro, dictionary: M.dictionary });
    const r = C.recordFor('COMPANY:A', null, b);
    assert.equal(r.state, 'NOT_APPLICABLE_ON_DATE'); assert.equal(r.words, '평가일 2026-11-05에 적용되는 분류 없음'); assert.equal(r.reason, 'EVALUATION_ONLY_DATE_MISMATCH');
    const asked = C.recordFor('COMPANY:A', '2026-11-03', valid(X.recordCase('normal')));
    assert.equal(asked.state, 'NOT_APPLICABLE_ON_DATE'); assert.equal(asked.words, '평가일 2026-11-03에 적용되는 분류 없음'); assert.equal(asked.sector, null);
    assert.equal(C.recordFor('COMPANY:Z', null, valid(X.recordCase('normal'))).words, '분류 자료 없음');
  });

  await ok('states and their words are all distinct (no single merged "순위 없음" state)', () => {
    const words = new Map();
    for (const name of Object.keys(WANT)) { const r = C.recordFor('COMPANY:A', null, valid(X.recordCase(name))); words.set(r.state, words.get(r.state) || new Set()); words.get(r.state).add(r.words.replace(/\(.*\)|\d{4}-\d{2}-\d{2}/g, '#')); }
    words.set('VERSION_MISMATCH', new Set([C.WORDS.VERSION_MISMATCH]));
    assert.deepEqual([...words.keys()].sort(), ['CONFIRMED', 'CONFLICT', 'NOT_APPLICABLE_ON_DATE', 'NO_DATA', 'SECTOR_ONLY', 'UNRESOLVED', 'VERSION_MISMATCH']);
    for (const v of words.values()) assert.equal(v.size, 1);
    const all = [...words.values()].map((v) => [...v][0]); assert.equal(new Set(all).size, all.length, all.join(' | '));
    const s = [C.sample('TECH', { n_valid: 9 }), C.sample('SECTOR_QGV', { n_valid: 19 }), C.sample('TECH', { n_valid: 0 }), C.sample('TECH', { n_valid: null, membership_status: 'UNKNOWN' }), C.sample('TECH', { n_valid: 10 })];
    assert.deepEqual(s.map((x) => x.state), ['SAMPLE_SMALL', 'SAMPLE_SMALL', 'EMPTY_GROUP', 'GROUP_UNCONFIRMED', 'OK']);
    assert.equal(new Set(s.map((x) => x.words)).size, 5, 'tech small, sector QGV small, empty, unconfirmed, ok: each its own words');
    assert.deepEqual([s[0].rank, s[0].median, s[0].decile], [true, true, false], 'tech N<10: rank and median kept, no decile');
    assert.deepEqual([s[1].score, s[1].rank], [false, false], 'sector QGV N<20: no factor score');
    assert.deepEqual([s[3].rank, s[3].median], [false, false], 'membership unknown: no rank, no median');
    assert.ok(s[0].words.includes('유효 N 9 < 10') && s[1].words.includes('유효 N 19 < 20'));
  });

  await ok('every technical case: Codex boards read by IS2.techScreen; N / k / membership as Codex expected', () => {
    for (const [name, c] of Object.entries(M.technical_cases)) {
      const want = CODEX.technical_cases[name].expected;
      if (want.error) { assert.equal(c.technical, null); assert.equal(c.error, want.error); continue; }
      const b = valid(X.technicalCase(name)); assert.deepEqual(b.mismatch, {}, name);
      const g = b.technical.groups.find((x) => x.sector_id === IT), m = g.board.metrics.momentum_3m;
      assert.equal(g.membership_status, want.membership_status, name); assert.equal(m.n_valid, want.n_valid, name); assert.equal(m.k, want.k, name);
      assert.equal(T.validate(g.board).ok, true);
      const st = C.sample('TECH', { n_valid: m.n_valid, membership_status: g.membership_status });
      assert.equal(st.state, { normal: 'OK', missing_security: 'GROUP_UNCONFIRMED', empty_group: 'EMPTY_GROUP' }[name] || 'SAMPLE_SMALL', name);
    }
  });

  await ok('groupRows: the confirmed group\'s FULL rows from the record (all members, issuer from the record, no made-up key), never an intersection', () => {
    const b = valid(X.technicalCase('normal')), board = itBoard(b.technical), members = b.view.rows.map((r) => r.company_id);
    const universe = uni(members, ['NYSE:OTHER1', 'NYSE:OTHER2']);
    const got = C.groupRowsWhy(board, universe, b);
    assert.equal(got.code, null); assert.deepEqual(got.rows.map((r) => r.code), members, 'every member, only members');
    for (const r of got.rows) { const v = b.view.rows.find((x) => x.company_id === r.code); assert.equal(r.issuer_id, v.issuer_id); assert.equal(r.classification_record_id, v.record_id);
      assert.equal(r.signal_day, null); assert.equal(r.security_id, null); assert.notEqual(r.issuer_id, r.id); }
    // Only 9 of the 10 members carry a board key (the rows "already on the board"): the group is still all 10, so the join is
    // refused instead of joining the 9.
    const links = M.technical_cases.normal.security_links, keyed = universe.map((r, i) => (i < 9 ? { ...r, signal_day: board.signal_day, security_id: 'SYNTHETIC:SECURITY:' + i, ticker: 'SYNTHETIC:TICKER:' + i } : r));
    const g9 = C.groupRowsWhy(board, keyed, b).rows; assert.equal(g9.length, 10);
    assert.equal(T.joinRows(board, g9, { links, data_kind: 'SYNTHETIC' }).code, 'INVALID_SESSION_DATE');
    assert.equal(T.joinRows(board, g9.slice(0, 9), { links, data_kind: 'SYNTHETIC' }).ok, true, 'the 9-row intersection would have joined (hiding the missing member)');
    const all = universe.map((r, i) => (i < 10 ? { ...r, signal_day: board.signal_day, security_id: 'SYNTHETIC:SECURITY:' + i, ticker: 'SYNTHETIC:TICKER:' + i } : r));
    const j = T.joinRows(board, C.groupRowsWhy(board, all, b).rows, { links, data_kind: 'SYNTHETIC' });
    assert.equal(j.ok, true, JSON.stringify(j)); assert.equal(j.keys.size, 10);
    // Out-of-group rows keep their place: groupRows never returns them and never reorders the universe.
    assert.deepEqual(all.slice(10).map((r) => r.code), ['NYSE:OTHER1', 'NYSE:OTHER2']);
  });

  await ok('groupRows null (with its code) whenever the group is not known', () => {
    const b = valid(X.technicalCase('normal')), board = itBoard(b.technical), universe = uni(b.view.rows.map((r) => r.company_id));
    const why = (bd, u, bb = b) => C.groupRowsWhy(bd, u, bb).code;
    assert.equal(why(board, universe.slice(1)), 'MEMBER_NOT_MAPPED', 'a member without its row');
    assert.equal(why(board, [...universe, universe[0]]), 'MEMBER_NOT_MAPPED', 'a member with two rows');
    assert.equal(why(board, universe.map((r, i) => (i ? r : { ...r, issuer_id: 'ISSUER:OTHER' }))), 'ISSUER_MISMATCH');
    assert.equal(why({ ...board, group_id: 'SYNTHETIC:LEADERBOARD' }, universe), 'BOARD_GROUP_NOT_COMMON');
    assert.equal(why({ ...board, group_id: 'COMMON:ENERGY:SPLIT_ADJUSTED' }, universe), 'BOARD_GROUP_NOT_IN_PROJECTION');
    assert.equal(why({ ...board, signal_day: '2017-01-09' }, universe), 'BOARD_DATE_MISMATCH');
    assert.equal(why({ ...board, membership_source: 'common-classification:' + 'b'.repeat(64) }, universe), 'CLASSIFICATION_VERSION_MISMATCH');
    assert.equal(why(board, universe, null), C.state().state === 'OK' ? null : 'CLASSIFICATION_NOT_CONNECTED');
    assert.equal(C.groupRows(board, universe), null, 'no loaded source today: null');
    const miss = valid(X.technicalCase('missing_security'));
    assert.equal(why(itBoard(miss.technical), uni(miss.view.rows.map((r) => r.company_id)), miss), 'GROUP_MEMBERSHIP_UNCONFIRMED');
    const empty = valid(X.technicalCase('empty_group')), eg = C.groupRowsWhy(itBoard(empty.technical), [], empty);
    assert.equal(eg.code, null); assert.deepEqual(eg.rows, [], 'a confirmed empty group is known and empty, not unknown');
    const view = valid({ view: M.technical_cases.normal.view });
    assert.equal(why(board, universe, view), 'TECHNICAL_PROJECTION_NOT_CONNECTED');
  });

  await ok('version mismatch: a part of another run or a tampered record is kept aside and refuses joins (분류 버전 불일치)', () => {
    const other = valid({ ...X.bundle(), technical: M.technical_cases.normal.technical });
    assert.equal(other.mismatch.technical, 'CLASSIFICATION_HASH_MISMATCH'); assert.equal(other.technical, null);
    assert.equal(C.groupRowsWhy(itBoard(M.technical_cases.normal.technical), [], other).code, 'CLASSIFICATION_VERSION_MISMATCH');
    const pr = C.partRecord('technical', 'company-000', other); assert.equal(pr.state, 'VERSION_MISMATCH'); assert.equal(pr.words, '분류 버전 불일치');
    assert.equal(C.partRecord('macro', 'company-000', other).state, 'OK', 'the other parts still read the same record');
    const rec = clone(X.bundle()); rec.technical.rows[3].classification_record_id = 'record:other';
    assert.equal(valid(rec).mismatch.technical, 'RECORD_ID_MISMATCH');
    const iss = clone(X.bundle()); iss.qgv_links.rows[0].issuer_id = 'issuer-x'; assert.equal(valid(iss).mismatch.qgv_links, 'ISSUER_ID_MISMATCH');
    const day = clone(X.bundle()); day.macro.valuation_date = '2026-11-03'; assert.equal(valid(day).mismatch.macro, 'VALUATION_DATE_MISMATCH');
    const mem = clone(X.bundle()); mem.macro.rows.pop(); assert.equal(valid(mem).mismatch.macro, 'MEMBERS_MISMATCH');
  });

  await ok('validators refuse tampered hash / version / shape at the first fault', () => {
    const refused = (p, code) => { const r = C.validate(p); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); };
    const t1 = clone(X.bundle()); t1.view.dictionary_version = 'common-industry-dictionary/2'; refused(t1, 'CLASSIFICATION_VERSION_INVALID');
    const t2 = clone(X.bundle()); t2.view.mapping_version = 'x'; refused(t2, 'CLASSIFICATION_VERSION_INVALID');
    const t3 = clone(X.bundle()); t3.view.classification_hash = 'A'.repeat(64); refused(t3, 'HASH_INVALID');
    const t4 = clone(X.technicalCase('normal')); t4.technical.classification_hash = 'b'.repeat(64); refused(t4, 'MEMBERSHIP_SOURCE_MISMATCH');
    const t5 = clone(X.bundle()); t5.view.schema_version = 'common-classification-view/2'; refused(t5, 'SCHEMA_VERSION');
    const t6 = clone(X.bundle()); t6.view.rows[0].sector = { id: null, status: 'UNKNOWN', reasons: [], evidence_refs: [] }; refused(t6, 'UNKNOWN_COMPONENT_REQUIRES_NULL_AND_REASON');
    const t7 = clone(X.bundle()); t7.view.rows[0].sector.id = 'COMMUNICATION_SERVICES'; refused(t7, 'ID_UNKNOWN');
    const t8 = clone(X.bundle()); t8.macro.benchmark_is_common_sector = true; refused(t8, 'SCOPE_CLAIM_NOT_SUPPORTED');
    const t9 = clone(X.bundle()); t9.macro.sector_returns = {}; refused(t9, 'ESTIMATE_NOT_SUPPORTED');
    const t10 = clone(X.technicalCase('normal')); t10.technical.groups[0].board.group_id = 'COMMON:ENERGY:RAW'; refused(t10, 'BOARD_GROUP_ID_MISMATCH');
    const t11 = clone(X.technicalCase('normal')); t11.technical.rows[0].security_ids = [t11.technical.rows[0].issuer_id]; refused(t11, 'ISSUER_OR_TICKER_IS_NOT_SECURITY_ID');
    const t12 = clone(X.technicalCase('normal')); t12.technical.extra = 1; refused(t12, 'KEY_UNKNOWN');
    const t13 = clone(X.bundle()); t13.view.rows.pop(); refused(t13, 'COMMON_VIEW_MEMBERSHIP_MISMATCH');
    const t14 = clone(X.bundle()); t14.qgv_links.preview_identity.input_hash = 'x'; refused(t14, 'HASH_INVALID');
    const t15 = clone(X.technicalCase('normal')); t15.technical.groups.find((g) => g.sector_id === IT).board.metrics.momentum_3m.k = 3; refused(t15, 'BOARD_K_MISMATCH');
    refused({ technical: M.technical_cases.normal.technical }, 'KEY_MISSING');
    assert.equal(C.validateView(M.technical_cases.version_mismatch.view).code, 'CLASSIFICATION_VERSION_INVALID', 'Codex version_mismatch view');
  });

  await ok('same company / date: detail (view), QGV (qgv links), technical and macro read the same record id and hash', () => {
    const b = valid(X.bundle());
    assert.deepEqual(b.mismatch, {});
    for (const row of b.view.rows) {
      const rec = C.recordFor(row.company_id, b.view.valuation_date, b);
      for (const part of ['qgv_links', 'technical', 'macro']) {
        const p = C.partRecord(part, row.company_id, b);
        assert.equal(p.state, 'OK'); assert.ok(C.sameRecord(rec, p), part + ' ' + row.company_id);
        assert.equal(p.classification_record_id, row.record_id); assert.equal(p.classification_hash, b.view.classification_hash);
      }
    }
    const a = C.recordFor('company-000', null, b), z = C.recordFor('company-001', null, b);
    assert.equal(C.sameRecord(a, z), false, 'another company'); assert.equal(C.sameRecord(a, { ...a, classification_hash: 'c'.repeat(64) }), false, 'another hash');
    assert.equal(C.sameRecord(a, { ...a, dictionary_version: 'x' }), false, 'another version'); assert.equal(C.sameRecord(a, { ...a, valuation_date: '2026-11-03' }), false, 'another date');
    // Today's Codex state in this run: no verified security id, every technical group with members unknown, no rank.
    const groups = b.technical.groups.filter((g) => g.counts.company_members > 0);
    assert.ok(groups.length > 0 && groups.every((g) => g.membership_status === 'UNKNOWN'));
    assert.equal(b.qgv_links.preview_identity.engine_version, 'sector-qgv-engine/0.1.0');
  });

  await ok('macro: common industry, SIC group and ETF reference kept apart; no own sector return or probability', () => {
    const b = valid(X.technicalCase('normal')), r = b.macro.rows[0];
    assert.equal(b.macro.benchmark_is_common_sector, false); assert.equal(b.macro.source_industry_is_common_sector, false);
    assert.equal(r.benchmark.version, 'sector_etf_map/v1'); assert.equal(r.source_industry.version, 'sic_industry_groups/v0');
    assert.equal(r.statistic_mapping.status, 'UNKNOWN'); assert.equal(r.probabilities, null); assert.equal(r.sector_returns, null);
  });

  await ok('filter options / matches: from the records only; UNCLASSIFIED is its own choice; never adds a sector', () => {
    const b = valid(X.recordCase('normal')), o = C.options(b);
    assert.deepEqual(o.sectors, [{ id: IT, n: 1 }]); assert.deepEqual(o.industries, [{ sector: IT, id: 'software', n: 1 }]);
    const rec = C.recordFor('COMPANY:A', null, b), un = C.recordFor('COMPANY:A', null, valid(X.recordCase('unclassified')));
    assert.ok(C.matches(rec, { sector: IT }) && C.matches(rec, { sector: IT, industry: 'software' }) && !C.matches(rec, { sector: IT, industry: 'computers' }));
    assert.ok(!C.matches(un, { sector: IT }) && C.matches(un, { sector: 'UNCLASSIFIED' }) && !C.matches(rec, { sector: 'UNCLASSIFIED' }));
    const so = C.recordFor('COMPANY:A', null, valid(X.recordCase('sector_only')));
    assert.ok(C.matches(so, { sector: IT, industry: 'UNCLASSIFIED' }) && !C.matches(so, { sector: IT, industry: 'software' }));
    assert.equal(C.sectorName(IT, M.dictionary), '정보기술'); assert.equal(C.industryName('software', M.dictionary), '소프트웨어');
  });

  await ok('hash context: token carries sector / industry / date / hash; another version or date is told apart', () => {
    const b = valid(X.bundle()), t = C.context({ sector: IT, industry: null }, b);
    assert.equal(t, 'cc:' + IT + ':-:2026-11-02:' + b.view.classification_hash.slice(0, 12));
    assert.deepEqual({ ...C.parseContext(t) }, { sector: IT, industry: null, valuation_date: '2026-11-02', hash12: b.view.classification_hash.slice(0, 12) });
    assert.equal(C.contextState(t, b), 'OK');
    assert.equal(C.contextState(t.replace(/:[0-9a-f]{12}$/, ':' + '0'.repeat(12)), b), 'VERSION_MISMATCH');
    assert.equal(C.contextState(t.replace('2026-11-02', '2026-11-01'), b), 'DATE_MISMATCH');
    assert.equal(C.parseContext('cc:x'), null); assert.equal(C.context({ sector: 'COMMUNICATION_SERVICES' }, b), null);
  });

  await ok('source() answers NONE; load() reads it once and makes no request; the file has no request code', async () => {
    const s = await C.source(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null);
    const st = await C.load(); assert.equal(st.state, 'NONE'); assert.equal(C.state().state, 'NONE'); assert.equal(C.value(), null);
    assert.equal(C.recordFor('NYSE:MMM').words, '분류 자료 없음');
    const src = fs.readFileSync(path.join(__dirname, '../src/investment_system/product/web_app/classification.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    assert.doesNotMatch(src, /\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|sendBeacon/);
  });
  console.log(JSON.stringify({ passed: true, checks: n }));
})().catch((e) => { console.error('FAIL ' + (e && e.stack || e)); process.exitCode = 1; });
