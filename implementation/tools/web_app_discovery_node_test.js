'use strict';
// 의외의 기업 (owner 2026-11-06; features 2.1.8 list · 2.4.6 mark): web_app/discovery.js against Codex's discovery-company/v1
// (#503 998414635aa4f1899748b1b76fc7ebf3ddc9d12f) and its public synthetic file, byte-identical and read unchanged.
//  - Each of Codex's six cases passes as delivered and gives exactly its expected list / mark / first-selection / publication
//    behaviour; the bundle as a whole is one company in six states, so as a list it is refused (DUPLICATE_COMPANY).
//  - The join is qgv_ref.company_id through the existing company list (never a ticker); CANDIDATE / IN_REVIEW / SUSPENDED /
//    REMOVED are never entries; a display that disagrees with the state, a shown claim that is not the record's own, a missing
//    evidence id, open gates under SELECTED or publication_approved true refuse the whole input.
//  - Sort recent / name / QGV (no official rank = its own group, never 0); filters and facets only from present values.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const D = require('../src/investment_system/product/web_app/discovery.js');
const X = require('./web_app_discovery_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const ROWS = Array.from({ length: 8 }, (_, i) => Object.freeze({ code: 'NYSE:ZZT' + i, id: 'ZZT' + i, ticker: 'ZZT' + i, name_en: 'Test ' + i, name_ko: null, status: 'ACTIVE', withdrawn_on: null, official: true }));
const BY = new Map(ROWS.flatMap((r) => [[r.id, r], [r.code, r]]));
const get = (k) => BY.get(k) || null;
const LIST = X.linked(ROWS), V0 = D.validate(LIST);

ok('Codex synthetic file: byte-identical to #503 and every case read unchanged', () => {
  assert.equal(X.codexSha(), X.CODEX_SHA256);
  const C = X.codex(); assert.equal(C.synthetic_only, true); assert.equal(C.cases.length, 6);
  for (const c of C.cases) { const r = D.validate(c.record); assert.equal(r.ok, true, c.case_id + ' ' + JSON.stringify(r)); assert.equal(r.value.data_kind, 'SYNTHETIC'); }
  assert.deepEqual(D.validate(C), { ok: false, code: 'DUPLICATE_COMPANY', path: '$[1].qgv_ref.company_id' }, 'one company in six states is not a list');
});
ok('each case gives Codex expected behaviour: list, mark, first selection, publication, direct link', () => {
  for (const c of X.codex().cases) {
    const r = JSON.parse(JSON.stringify(c.record)); r.qgv_ref.company_id = ROWS[0].id;
    const v = D.view(D.validate(r).value, { get }), e = D.markFor(v, ROWS[0]), x = c.expected;
    assert.equal(v.entries.length === 1, x.list_eligible, c.case_id + ' list');
    assert.equal(e ? e.record.display.mark : null, x.mark, c.case_id + ' mark');
    assert.equal(c.record.first_selected_at === null, x.first_selected_null, c.case_id);
    assert.equal(c.record.publication_approved, x.publication_approved);
    if (x.list_eligible) assert.ok(e.record.display.risks.some((f) => f.value === x.risk_visible), 'risk visible');
    assert.equal(c.record.awareness.market_attention === null, x.unknown_market_attention);
  }
});
ok('listed states only; hidden states counted; synthetic kind kept', () => {
  assert.equal(V0.ok, true, JSON.stringify(V0)); assert.equal(V0.value.data_kind, 'SYNTHETIC');
  const v = D.view(V0.value, { get });
  assert.deepEqual(v.entries.map((e) => [e.company.id, e.status]), [['ZZT2', 'SELECTED'], ['ZZT3', 'REVIEW_REQUIRED'], ['ZZT6', 'SELECTED']]);
  assert.deepEqual({ ...v.hidden }, { CANDIDATE: 1, IN_REVIEW: 1, SUSPENDED: 1, REMOVED: 1 });
  for (const i of [0, 1, 4, 5]) assert.equal(D.markFor(v, ROWS[i]), null, 'no mark for ' + LIST[i].state);
  const e2 = D.markFor(v, ROWS[2]); assert.equal(e2.record, LIST.length && v.entries[0].record, 'list and mark: the same record object');
  assert.equal(D.markFor(v, { code: 'NYSE:ZZT2', id: 'NYSE:ZZT2' }).company.id, 'ZZT2', 'found by code too');
  assert.deepEqual([v.entries[0].partial, v.entries[1].partial, v.entries[2].partial], [false, false, true]);
  assert.deepEqual([v.entries[0].review, v.entries[1].review], [false, true]);
});
ok('identity: qgv_ref.company_id must name an existing company; listing ended dropped', () => {
  const v = D.view(V0.value, { get: (k) => (k === 'ZZT2' ? null : get(k)) });
  assert.equal(v.dropped.IDENTITY_UNRESOLVED, 1); assert.equal(v.entries.length, 2);
  const w = D.view(V0.value, { get: (k) => (k === 'ZZT6' ? { ...get(k), status: 'WITHDRAWN' } : get(k)) });
  assert.equal(w.dropped.LISTING_ENDED, 1);
});
ok('sort recent / name / QGV (no-rank group, never 0); filters and facets from present values; 0 keeps the conditions', () => {
  const es = D.view(V0.value, { get }).entries, title = (e) => e.company.name_en, ids = (l) => l.map((e) => e.company.id);
  assert.deepEqual(ids(D.sort(es, 'recent', { title })), ['ZZT2', 'ZZT3', 'ZZT6']);
  assert.deepEqual(ids(D.sort(es, 'name', { title: (e) => ({ ZZT2: '다', ZZT3: '가', ZZT6: '나' })[e.company.id] })), ['ZZT3', 'ZZT6', 'ZZT2']);
  const q = { ZZT2: { rank: 40 }, ZZT3: { rank: null }, ZZT6: { rank: 7 } };
  const s = D.sort(es, 'qgv', { title, qgv: (e) => q[e.company.id] });
  assert.deepEqual(ids(s), ['ZZT6', 'ZZT2', 'ZZT3']); assert.deepEqual(s.map((e) => D.qgvGroup(q[e.company.id])), ['RANKED', 'RANKED', 'NO_RANK']);
  const fc = D.facets(es, {});
  assert.deepEqual(fc.type.map((x) => x.slice()), [['FAST_GROWER', '고성장', 1], ['NONE', '유형 미분류', 1], ['CYCLICAL', '경기순환', 1]]);
  assert.deepEqual(fc.strength.map((x) => [x[0], x[2]]), [['반복 구매', 2], ['NONE', 1]]);
  assert.deepEqual(ids(D.filter(es, { strength: '반복 구매' })), ['ZZT2', 'ZZT6']);
  const f = { type: 'FAST_GROWER', strength: 'NONE' }; assert.equal(D.filter(es, f).length, 0); assert.deepEqual(f, { type: 'FAST_GROWER', strength: 'NONE' });
});
ok('sections: discovery reason, types, strengths, regions, signals, risks with their states; awareness unmeasured', () => {
  const r = D.view(V0.value, { get }).entries[0].record, st = D.sectionState(r);
  assert.deepEqual(D.SECTIONS.map(st), ['CONFIRMED', 'CONFIRMED', 'CONFIRMED', 'CONFIRMED', 'CONFIRMED', 'CONFIRMED']);
  assert.equal(D.topicLabel('types', 'FAST_GROWER'), '고성장'); assert.equal(D.topicLabel('signals', 'BUYBACK_EXECUTED'), '자사주 매입 실행'); assert.equal(D.topicLabel('regions', 'REVENUE'), '매출 지역');
  assert.equal(D.awarenessOf(r, 'market_attention'), null);
  const r3 = D.view(V0.value, { get }).entries[2].record; assert.equal(D.sectionState(r3)('strengths'), 'UNCONFIRMED');
  assert.equal(D.sectionState(X.caseOf('SELECTED'))('types'), 'NONE');
});
ok('refusals: the whole input at its first fault', () => {
  const sel = () => X.caseOf('SELECTED');
  const cases = [
    ['SCHEMA_VERSION', (r) => { r.schema_version = 'discovery-company/v2'; }],
    ['KEY_UNKNOWN', (r) => { r.score = 1; }], ['KEY_MISSING', (r) => { delete r.display.unknowns; }],
    ['DISPLAY_STATE_MISMATCH', (r) => { r.display.mark = null; }], ['DISPLAY_STATE_MISMATCH', (r) => { r.state = 'SUSPENDED'; r.state_reason = r.display.state_reason; }],
    ['DISPLAY_STATE_MISMATCH', (r) => { r.display.state_reason = '다른 사유'; }],
    ['DISPLAY_REF', (r) => { r.display.business[0].claim = '다른 주장'; }],
    ['EVIDENCE_REF', (r) => { r.judgments[0].evidence_ids = ['nope']; }],
    ['GATES_OPEN', (r) => { r.blocked_gates = ['CURRENTNESS']; }], ['GATES_OPEN', (r) => { r.material_refutations = ['x']; }],
    ['PUBLICATION_APPROVED', (r) => { r.publication_approved = true; }],
    ['FIRST_SELECTED_MISSING', (r) => { r.first_selected_at = null; }],
    ['TOPIC_INVALID', (r) => { X.enrich(r, { type: 'LYNCH_TYPE_7', strength: 'x' }); }],
    ['BANNED_LABEL', (r) => { r.judgments[0].claim = '린치 유형 고성장'; r.display.selection_summary[0].claim = '린치 유형 고성장'; }],
    ['URL_INVALID', (r) => { r.evidence[0].source_url = 'javascript:alert(1)'; }], ['SHA_INVALID', (r) => { r.evidence[0].sha256 = 'abc'; }],
    ['TIME_INVALID', (r) => { r.as_of = '2026-11-06'; }], ['STATE_INVALID', (r) => { r.state = 'PUBLISHED'; }],
    ['JUDGMENT_REF', (r) => { r.awareness.market_attention = 'nope'; }],
  ];
  for (const [code, fn] of cases) { const r = sel(); fn(r); const q = D.validate(r); assert.equal(q.ok, false, code); assert.equal(q.code, code, code + ' got ' + q.code + ' ' + q.path); }
  assert.equal(D.validate(null).ok, false); assert.equal(D.validate({ cases: [] }).code, 'BUNDLE_INVALID');
});
ok('source(): NONE today (no public file, no request)', async () => { const s = await D.source(); assert.equal(s.state, 'NONE'); assert.equal(s.payload, null); });
ok('screen words: panel order and no 린치 유형 / 8장 특성 on any web_app screen file', () => {
  assert.deepEqual(D.SECTIONS.map((s) => D.SECTION_TEXT[s]), ['이 기업을 발견한 이유', '기업 유형', '눈여겨볼 사업 강점', '사업지역과 성장 여력', '추가로 주목할 신호', '함께 확인할 위험']);
  const dir = path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app');
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.js'))) {
    fs.readFileSync(path.join(dir, f), 'utf8').split('\n').forEach((l, i) => { if (/린치\s*유형|8장\s*특성/.test(l)) assert.ok(f === 'discovery.js' && /const BANNED=/.test(l), f + ':' + (i + 1)); });
  }
});
console.log('ok ' + n + ' checks');
