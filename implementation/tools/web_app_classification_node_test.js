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
//  - Accounting model apart from the sector (Codex #516 4cf2e037); evidence refs read whole (MAX.ref); the owner's private delivery
//    (connectPrivate / disconnectPrivate / subscribe, owner 2026-11-08).
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

  // The group roster is Codex technical-filter-membership/1 (GROUP_JOIN.md, #516 5b0ec88a): a view needs its universe context and
  // each member's applicability on the evaluation date. Codex's technical-case views carry neither, so they make no roster.
  const GJ = X.universe().group_join, gjBundle = (view = GJ.view) => valid({ view, technical: GJ.technical, dictionary: M.dictionary });
  const gjUni = (extra = []) => uni(GJ.codes, extra);
  await ok('groupRows: the roster\'s FULL rows (each once, issuer connected from the record with provenance, keys untouched), never an intersection', () => {
    const b = gjBundle(), board = GJ.board, universe = gjUni(['NYSE:OTHER1', 'NYSE:OTHER2']), before = clone(universe);
    const got = C.groupRowsWhy(board, universe, b);
    assert.equal(got.code, null); assert.deepEqual(got.rows.map((r) => r.code), GJ.codes, 'every member, only members');
    for (const r of got.rows) { const m = GJ.group_manifest.members.find((x) => x.company_id === r.code);
      assert.equal(r.issuer_id, m.issuer_id); assert.equal(r.issuer_connection.basis, 'VERIFIED_CLASSIFICATION_RECORD'); assert.equal(r.issuer_connection.previous_issuer_id, null);
      assert.equal(r.issuer_connection.classification_record_id, m.classification_record_id); assert.equal(r.issuer_connection.signal_day, b.view.valuation_date);
      assert.equal(Object.hasOwn(r, 'classification_record_id'), false, 'record id never written onto the row'); assert.equal(r.signal_day, null); assert.equal(r.security_id, null); }
    assert.deepEqual(universe, before, 'universe rows unchanged');
    const gi = C.groupInput(board, universe, b);
    assert.equal(gi.mode, 'V2'); assert.equal(gi.code, null); assert.deepEqual(gi.rows.map((r) => r.code), GJ.codes); assert.ok(gi.rows.every((r, i) => r === universe[i]), 'the original row objects, not copies');
    assert.deepEqual(clone(gi.manifest), GJ.group_manifest, 'roster = Codex build_group_manifest'); assert.deepEqual(clone(gi.context), GJ.group_context, 'context = the pinned request context');
    const nineKeyed = universe.map((r, i) => (i < 2 ? { ...r, signal_day: board.signal_day, security_id: 'SYNTHETIC:SECURITY:' + i } : r));
    assert.equal(C.groupInput(board, nineKeyed, b).rows.length, 3, 'rows keyed for the board do not shrink the group');
    assert.equal(C.groupInput({ ...board, group_id: 'SYNTHETIC:LEADERBOARD' }, universe, b).mode, 'NONE', 'another board: the /1 path');
  });
  await ok('counterexamples (Codex #516 consumer probe of Main 23dd5dc5): row hash / row record id / other-day record refused, never overwritten or filled', () => {
    const b = gjBundle(), board = GJ.board, u = gjUni();
    const hash = u.map((r, i) => (i ? r : { ...r, classification_hash: 'b'.repeat(64) })), rec = u.map((r, i) => (i ? r : { ...r, classification_record_id: 'SYNTHETIC:WRONG' }));
    assert.equal(C.groupRowsWhy(board, hash, b).code, 'ROW_CLASSIFICATION_MISMATCH');
    assert.equal(C.groupRowsWhy(board, rec, b).code, 'ROW_CLASSIFICATION_MISMATCH'); assert.equal(rec[0].classification_record_id, 'SYNTHETIC:WRONG', 'not overwritten');
    const off = gjBundle(GJ.view_not_applicable_on_day), gi = C.groupInput(board, u, off);
    assert.equal(gi.manifest.membership_status, 'UNKNOWN'); assert.deepEqual([...gi.manifest.reasons], ['CLASSIFICATION_APPLICABILITY_UNCONFIRMED']);
    assert.equal(C.groupRowsWhy(board, u, off).code, 'GROUP_MEMBERSHIP_UNCONFIRMED', 'no issuer from another day\'s record');
    assert.equal(C.groupRowsWhy(board, u.map((r, i) => (i ? r : { ...r, issuer_id: 'SYNTHETIC:WRONG' })), b).code, 'ISSUER_MISMATCH', 'a conflicting issuer is not replaced');
  });

  await ok('groupRows null (with its code) whenever the group is not known', () => {
    const b = gjBundle(), board = GJ.board, universe = gjUni();
    const why = (bd, u, bb = b) => C.groupRowsWhy(bd, u, bb).code;
    assert.equal(why(board, universe.slice(1)), 'MEMBER_NOT_MAPPED', 'a member without its row');
    assert.equal(why(board, [...universe, universe[0]]), 'MEMBER_NOT_MAPPED', 'a member with two rows');
    assert.equal(why({ ...board, group_id: 'SYNTHETIC:LEADERBOARD' }, universe), 'BOARD_GROUP_NOT_COMMON');
    assert.equal(why({ ...board, group_id: 'COMMON:ENERGY:SPLIT_ADJUSTED' }, universe), 'BOARD_GROUP_NOT_IN_PROJECTION');
    assert.equal(why({ ...board, signal_day: '2017-01-09' }, universe), 'BOARD_DATE_MISMATCH');
    assert.equal(why({ ...board, membership_source: 'common-classification:' + 'b'.repeat(64) }, universe), 'CLASSIFICATION_VERSION_MISMATCH');
    assert.equal(why(board, universe, null), 'CLASSIFICATION_NOT_CONNECTED');
    assert.equal(C.groupRows(board, universe), null, 'no loaded source today: null');
    const tc = valid(X.technicalCase('normal'));
    assert.equal(why(itBoard(tc.technical), uni(tc.view.rows.map((r) => r.company_id)), tc), 'GROUP_UNIVERSE_CONTEXT_REQUIRED', 'Codex technical-case views carry no universe context: no roster');
    const view = valid({ view: M.technical_cases.normal.view });
    assert.equal(why(itBoard(M.technical_cases.normal.technical), universe, view), 'TECHNICAL_PROJECTION_NOT_CONNECTED');
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

  await ok('2.2.7: a sector QGV preview is matched to records only through qgv links naming that preview on the same date', () => {
    const b = valid(X.bundle()), p = M.bundle.qgv_preview, r = C.previewCheck(p, b);
    assert.equal(r.state, 'OK'); assert.equal(r.rows.size, p.result_rows.length); assert.equal(r.missing, 0);
    for (const row of p.result_rows) assert.equal(r.rows.get(row.company_id).record_id, b.view.rows.find((x) => x.company_id === row.company_id).record_id);
    for (const k of ['preview_id', 'input_hash', 'config_hash', 'cache_key', 'engine_version']) {
      const x = C.previewCheck({ ...p, [k]: k === 'engine_version' ? 'sector-qgv-engine/9' : 'c'.repeat(64) }, b);
      assert.equal(x.state, 'PREVIEW_NOT_LINKED', k); assert.deepEqual([...x.differs], [k]); assert.equal(x.rows, null, 'no row matched');
    }
    assert.equal(C.previewCheck({ ...p, valuation_date: '2026-11-01' }, b).state, 'DATE_MISMATCH');
    assert.equal(C.previewCheck(p, valid(X.uBundle())).state, 'PREVIEW_NOT_LINKED', 'another run\'s links');
    assert.equal(C.previewCheck(p, valid({ ...X.bundle(), qgv_links: null })).state, 'LINKS_NONE');
    const t = clone(X.bundle()); t.qgv_links.rows[0].classification_record_id = 'record:other';
    assert.equal(C.previewCheck(p, valid(t)).state, 'VERSION_MISMATCH');
    const extra = { ...p, result_rows: [...p.result_rows, { company_id: 'company-999', status: 'MAPPING_UNRESOLVED', rank: null }] }, e = C.previewCheck(extra, b);
    assert.equal(e.state, 'OK'); assert.equal(e.missing, 1); assert.equal(e.rows.get('company-999').reason, 'CLASSIFICATION_LINK_MISSING');
    assert.equal(C.previewCheck(p, null).state, C.state().state === 'OK' ? 'OK' : 'NONE');
    assert.equal(new Set(Object.values(C.PREVIEW_STATE)).size, Object.keys(C.PREVIEW_STATE).length, 'each state its own words');
  });

  await ok('source() answers NONE; load() reads it once and makes no request; the file has no request code', async () => {
    const s = await C.source(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null);
    const st = await C.load(); assert.equal(st.state, 'NONE'); assert.equal(C.state().state, 'NONE'); assert.equal(C.value(), null);
    assert.equal(C.recordFor('NYSE:MMM').words, '분류 자료 없음');
    const src = fs.readFileSync(path.join(__dirname, '../src/investment_system/product/web_app/classification.js'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    assert.doesNotMatch(src, /\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|sendBeacon/);
  });
  // Codex #516 4cf2e037 HELD_REVIEW.md: sector and accounting model are independent states; evidence refs are opaque locators.
  await ok('accounting model kept apart: confirmed sector + unknown accounting is never a complete QGV peer group; accounting alone is told', () => {
    const b = clone(X.bundle()), rows = b.view.rows, conf = rows.find((r) => r.sector.status === 'CONFIRMED' && r.accounting.status === 'CONFIRMED');
    assert.ok(conf, 'the fixture has a fully confirmed row');
    const both = C.recordFor(conf.company_id, null, valid(clone(X.bundle())));
    assert.equal(both.accounting_state, 'CONFIRMED'); assert.equal(both.peer_complete, true); assert.equal(both.accounting_words, null);
    conf.accounting = { id: null, status: 'UNKNOWN', reasons: ['ACCOUNTING_TEMPLATE_UNCONFIRMED'], evidence_refs: [] };
    const v = valid(b), r = C.recordFor(conf.company_id, null, v);
    assert.equal(r.sector.status, 'CONFIRMED'); assert.equal(r.accounting_state, 'UNKNOWN'); assert.equal(r.peer_complete, false);
    assert.equal(r.accounting_words, '회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님');
    assert.equal(r.state, both.state, 'the sector state words do not change: the accounting line says the rest');
    const b2 = clone(X.bundle()), row2 = b2.view.rows.find((x) => x.company_id === conf.company_id), acc = clone(row2.accounting);
    row2.sector = { id: null, status: 'UNKNOWN', reasons: ['SECTOR_UNCONFIRMED'], evidence_refs: [] }; row2.industry = { id: null, status: 'UNKNOWN', reasons: ['SECTOR_UNCONFIRMED'], evidence_refs: [] }; row2.accounting = acc;
    const r2 = C.recordFor(conf.company_id, null, valid(b2));
    assert.equal(r2.accounting_state, 'CONFIRMED'); assert.equal(r2.peer_complete, false); assert.equal(r2.accounting_words, '회계모형만 확인 · 섹터 미확인');
  });
  await ok('evidence refs: a 330-character locator (the held review) is read whole; one past MAX.ref is refused; words keep 300', () => {
    const b = clone(X.bundle()), row = b.view.rows.find((r) => r.sector.status === 'CONFIRMED');
    row.sector.evidence_refs = ['synthetic:source:' + 'a'.repeat(313)]; assert.equal(row.sector.evidence_refs[0].length, 330);
    assert.equal(C.validate(b).ok, true);
    row.sector.evidence_refs = ['x'.repeat(4097)]; const r = C.validate(b); assert.equal(r.ok, false); assert.equal(r.code, 'TOO_LARGE');
    const w = clone(X.bundle()), sic = w.view.rows.find((r) => r.source_sic && typeof r.source_sic.system === 'string');
    assert.ok(sic, 'the fixture has a source SIC'); sic.source_sic.system = 'S'.repeat(301);
    assert.equal(C.validate(w).code, 'TOO_LARGE', 'a shown word keeps the 300 bound');
  });
  await ok('private delivery: connectPrivate checks the bundle whole, makes it the RAM source (PRIVATE), disconnectPrivate drops it', async () => {
    const seen = []; const un = C.subscribe(() => seen.push(C.state().state));
    const bad = clone(X.bundle()); bad.view.schema_version = 'x';
    const r0 = C.connectPrivate(bad); assert.equal(r0.ok, false); assert.equal((await C.source()).state, 'NONE'); assert.equal(seen.length, 0, 'a refused bundle changes nothing');
    const r1 = C.connectPrivate(clone(X.bundle())); assert.equal(r1.ok, true); assert.equal(seen.length, 1);
    const s = await C.source(); assert.equal(s.state, 'OK'); assert.equal(s.delivery, 'PRIVATE'); assert.equal(s.text, '비공개 보관본 · 인증 경로 · 게시본 아님');
    const st = await C.load(); assert.equal(st.state, 'OK'); assert.equal(st.delivery, 'PRIVATE'); assert.equal(C.state().delivery, 'PRIVATE');
    const any = C.value().view.rows[0]; assert.equal(C.recordFor(any.company_id).delivery, 'PRIVATE');
    C.disconnectPrivate(); assert.equal(seen.length, 2); assert.equal(C.state().state, 'NOT_LOADED', 'a dropped delivery is not the loaded state');
    assert.equal((await C.load()).state, 'NONE'); assert.equal(C.value(), null); assert.equal(C.recordFor(any.company_id).words, '분류 자료 없음');
    C.disconnectPrivate(); assert.equal(seen.length, 2, 'nothing to drop: no notice'); un();
  });
  console.log(JSON.stringify({ passed: true, checks: n }));
})().catch((e) => { console.error('FAIL ' + (e && e.stack || e)); process.exitCode = 1; });
