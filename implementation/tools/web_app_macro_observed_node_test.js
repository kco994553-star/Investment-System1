'use strict';
// 매크로 관측 자료 (feature 4.1.3; owner 2026-11-05): web_app/macro-observed.js against Codex's macro-current-query/1 (#477 efc8715f).
//  - The SYNTHETIC files made by Codex's own tool (tests/fixtures/macro_current_query_v1_synthetic.json, sha256 pinned) are read
//    unchanged: 14 series, the file's counts, the query times and ages.
//  - Words per series: AVAILABLE / STALE / NOT_AVAILABLE with reason; 기준 기간 · data_asof · frequency · unit · seasonal
//    adjustment; RAW_DIAGNOSTIC = 진단값 관측 (not an adopted regime judgment), NOT_COMPUTED = 미산출 with its reason;
//    원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE on every row (never an acquisition time); first acquisition recorded or only an
//    upper bound; held + 수정 버전; FAILED_AFTER_SUCCESS keeps the last success; NEVER_SUCCEEDED.
//  - No observed value reaches a view (the current query file is private and not approved for a public screen).
//  - The whole file is refused at its first fault (wrong schema, a value with NOT_COMPUTED, a filled original release, a
//    transition flag, an official-judgement scope, a held series with a value, counts, ages, update status, unknown keys).
//  - source() is NONE with no payload.
const assert = require('node:assert/strict');
const M = require('../src/investment_system/product/web_app/macro-observed.js');
const X = require('./web_app_macro_observed_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const C = X.cases(), V = Object.fromEntries(Object.entries(C).map(([k, p]) => [k, M.validate(p)]));
const view = (k) => M.view(V[k].value, { dataKind: 'SYNTHETIC' });
const row = (k, id) => view(k).series.find((s) => s.id === id);
const all = (s) => Object.values(s.lines).join(' | ');

ok('fixture: pinned bytes, SYNTHETIC header, made by Codex #477 tool; every case read unchanged and deep-frozen', () => {
  assert.equal(X.sha(), X.SHA256);
  const b = X.bundle();
  assert.equal(b.data_kind, 'SYNTHETIC'); assert.match(b._synthetic, /SYNTHETIC/); assert.match(b.source_ref, /efc8715f/);
  for (const k of ['main', 'late', 'never']) assert.equal(V[k].ok, true, k + ' ' + JSON.stringify(V[k]));
  assert.ok(Object.isFrozen(V.main.value.series[X.IDS.curve].source));
  assert.deepEqual(Object.keys(V.main.value.series), M.SERIES.map((s) => s[0]));
  assert.equal(V.main.value.schema_version, 'macro-current-query/1');
});

ok('head: 합성 개발 검증, schema, query / cache times and age, cache reuse with 0 requests, the file counts', () => {
  const v = view('main');
  assert.match(v.status, /^합성 개발 검증 · 실자료 아님 · macro-current-query\/1 · 근거 계약 macro-observed-evidence\/1/);
  assert.deepEqual(v.query.map((q) => q[0]), ['조회 시각', '계산 캐시 기준', '보관본 생성', '갱신', '시점 범위']);
  assert.equal(v.query[0][1], '2026-01-04 00:00 UTC');
  assert.equal(v.query[1][1], '2026-01-03 12:00 UTC · 12시간 전');
  assert.equal(v.query[3][1], '계산 캐시 재사용 · 원천을 새로 받지 않음 · 외부 요청 0건');
  assert.equal(v.counts, '14계열 · 조회 가능 6 (신선 5 · stale 1) · 값 유지 6 · 미산출 8 · 원발표 입증 0 · 원기관 버전 입증 0 · 과거 시점 검증 가능 0');
  assert.match(M.view(V.main.value).status, /^자료 종류 표시 없음/, 'no kind given: said, never assumed real');
});

ok('per series: period / data_asof, frequency, unit, seasonal adjustment; RAW_DIAGNOSTIC = 진단값 관측, NOT_COMPUTED = 미산출', () => {
  const c = row('main', X.IDS.curve), g = row('main', X.IDS.gdp), d = row('main', X.IDS.temp);
  assert.equal(c.lines.period, '기준 기간 2025-11 · data_asof 2025-11'); assert.equal(c.lines.meta, '월 · 단위 %p · 계절조정 해당 없음');
  assert.equal(g.lines.meta, '분기 · 단위 % · 계절조정 연율'); assert.equal(g.lines.period, '기준 기간 2025Q3 · data_asof 2025Q3');
  assert.equal(c.lines.kind, '진단값 관측 · 채택된 국면 판단 아님 · 값 미표시');
  assert.equal(d.resultKind, 'NOT_COMPUTED'); assert.equal(d.lines.kind, '미산출 · 수집 전'); assert.equal(d.lines.period, '기준 기간 없음');
  assert.equal(row('main', X.IDS.census).lines.kind, '미산출 · API 키 미설정');
  assert.equal(row('main', X.IDS.dol).lines.state, '자료 없음 · 약관 원문 미확인 · 공개 보류');
  assert.match(row('main', X.IDS.dol).lines.terms, /약관 미확인 · 공개 보류/);
  assert.equal(row('main', X.IDS.fomc).lines.state, '조회 가능 · stale 판정 없음 (사건 계열)');
});

ok('원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE on every row; acquisition recorded, or an upper bound only (never as a release time)', () => {
  for (const k of ['main', 'late', 'never']) for (const s of view(k).series) {
    assert.ok(s.lines.evidence.startsWith('원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE · '), k + ' ' + s.id);
    assert.match(s.lines.vintage, /^원기관 자료 버전 미확인 · NOT_PROVEN_IN_ARCHIVE · 과거 시점\(PIT\) 검증 불가/);
  }
  assert.match(row('main', X.IDS.curve).lines.evidence, /첫 취득 2026-01-02 12:00 UTC \(기록된 수신\) · 선택 버전 취득 2026-01-03 12:00 UTC/);
  assert.match(row('main', X.IDS.ip).lines.evidence, /첫 취득 시각 기록 없음 · 늦어도 2026-01-03 12:00 UTC \(보관본 생성 상한\) · 선택 버전 취득 시각 기록 없음 · 늦어도 2026-01-03 12:00 UTC \(보수 상한\)/);
  assert.match(row('main', X.IDS.temp).lines.evidence, /취득 기록 없음$/);
});

ok('held + revised: the curve keeps a revised version (값 유지 예 · 수정 버전 예); no transition event in a current query', () => {
  const c = row('main', X.IDS.curve);
  assert.equal(c.version, 'REVISION'); assert.equal(c.held, true);
  assert.equal(c.lines.flags, '값 유지 예 · 수정 버전 예 · 이번 조회의 수정 아니오 · 새 관측 아니오 · 새로 조회 가능 아니오');
  assert.match(c.lines.evidence, /버전 수정 버전 · 기간 첫 근거 최초 보관 기준값/);
  assert.match(row('main', X.IDS.ip).lines.evidence, /버전 보관 중 첫 기록/);
});

ok('STALE: old period kept as 진단값 with stale words; 200 days later five series are stale', () => {
  const h = row('main', X.IDS.hours);
  assert.equal(h.state, 'STALE'); assert.equal(h.lines.state, 'stale · 기준 기간 지연 (값 유지 · 진단용)');
  assert.equal(h.lines.period, '기준 기간 2025-04 · data_asof 2025-04'); assert.equal(h.resultKind, 'RAW_DIAGNOSTIC');
  const late = view('late');
  assert.equal(late.series.filter((s) => s.state === 'STALE').length, 5);
  assert.match(late.counts, /조회 가능 6 \(신선 1 · stale 5\)/);
  assert.match(late.query[1][1], /· 200일 전$/);
});

ok('update status: FAILED_AFTER_SUCCESS keeps the last success and says the failure; LAST_SUCCESS_RETAINED; NEVER_SUCCEEDED', () => {
  const l = row('main', X.IDS.labor);
  assert.equal(l.update, 'FAILED_AFTER_SUCCESS'); assert.equal(l.resultKind, 'RAW_DIAGNOSTIC'); assert.equal(l.state, 'AVAILABLE');
  assert.equal(l.lines.update, '마지막 성공 수집 2026-01-02 12:00 UTC (1일 12시간 전) · 최근 수집 실패 · 마지막 성공값 유지 · 실패 사유 출처 응답 없음');
  assert.equal(row('main', X.IDS.curve).lines.update, '마지막 성공 수집 2026-01-03 12:00 UTC (12시간 전) · 마지막 성공 유지');
  const never = view('never');
  assert.ok(never.series.every((s) => s.update === 'NEVER_SUCCEEDED' && s.resultKind === 'NOT_COMPUTED' && s.lines.update === '마지막 성공 수집 없음 · 성공한 수집 없음'));
  assert.match(never.counts, /^14계열 · 조회 가능 0 \(신선 0 · stale 0\) · 값 유지 0 · 미산출 14/);
});

ok('no observed value in any view (sentinel digits absent); values exist in the validated file only', () => {
  for (const k of ['main', 'late', 'never']) {
    const text = JSON.stringify(view(k));
    assert.doesNotMatch(text, X.SENTINEL, k);
    for (const s of Object.values(C[k].series)) if (s.value !== null) assert.ok(!text.includes(String(s.value)), k + ' ' + s.source_id);
  }
  assert.match(JSON.stringify(C.main), X.SENTINEL, 'the fixture itself carries the sentinels');
  assert.match(M.TEXT.VALUES, /값 미표시 · 현재 조회 파일은 비공개 생성/);
});

ok('refused whole at the first fault, nothing repaired', () => {
  const S = X.IDS;
  const cases = [
    ['SCHEMA_VERSION', 'main', (p) => { p.schema_version = 'macro-observed-timeline/1'; }],
    ['EVIDENCE_CONTRACT', 'main', (p) => { p.evidence_contract_version = 'macro-observed-evidence/2'; }],
    ['VALUE_WITH_NOT_COMPUTED', 'main', (p) => { p.series[S.temp].value = 1.5; }],
    ['VALUE_MISSING', 'main', (p) => { p.series[S.curve].value = null; }],
    ['NUMBER_NOT_FINITE', 'main', (p) => { p.series[S.curve].value = '0.15'; }],
    ['PUBLICATION_HELD_VALUE', 'main', (p) => { Object.assign(p.series[S.dol], { value: 1, result_kind: 'RAW_DIAGNOSTIC' }); }],
    ['OFFICIAL_RELEASE_UNPROVEN', 'main', (p) => { p.series[S.curve].official_release_at = p.series[S.curve].first_acquired_at; }],
    ['SOURCE_VERSION_UNPROVEN', 'main', (p) => { p.series[S.curve].source_version_status = 'PROVEN'; }],
    ['FLAG_INVALID', 'main', (p) => { p.series[S.curve].revised = true; }],
    ['HELD_MISMATCH', 'main', (p) => { p.series[S.curve].held = false; }],
    ['STATE_MISMATCH', 'main', (p) => { p.series[S.hours].state = 'AVAILABLE'; }],
    ['STALE_MISMATCH', 'main', (p) => { p.series[S.curve].stale = null; }],
    ['SCOPE_INVALID', 'main', (p) => { p.scope.official_judgement = true; }],
    ['MODEL_APPLIED', 'main', (p) => { p.series[S.gdp].model_status = 'APPLIED'; }],
    ['PIT_ELIGIBLE', 'main', (p) => { p.series[S.gdp].historical_pit_eligible = true; }],
    ['UPDATE_STATUS_MISMATCH', 'main', (p) => { p.series[S.labor].update_status = 'LAST_SUCCESS_RETAINED'; }],
    ['UPDATE_STATUS_MISMATCH', 'never', (p) => { p.series[S.temp].update_status = 'FAILED_AFTER_SUCCESS'; }],
    ['AGE_MISMATCH', 'main', (p) => { p.seconds_since_cache_asof = 0; }],
    ['AGE_MISMATCH', 'main', (p) => { p.series[S.curve].seconds_since_success = 1; }],
    ['ACQUISITION_MISMATCH', 'main', (p) => { p.series[S.ip].first_acquired_at = p.series[S.ip].first_acquired_by; }],
    ['COUNT_MISMATCH', 'main', (p) => { p.counts.stale = 0; }],
    ['SERIES_SET', 'main', (p) => { delete p.series[S.dol]; }],
    ['KEY_UNKNOWN', 'main', (p) => { p.series[S.curve].adopted_regime = 'x'; }],
    ['KEY_MISSING', 'main', (p) => { delete p.counts; }],
    ['EXTERNAL_REQUESTS', 'main', (p) => { p.new_external_requests = 1; }],
    ['TIME_ORDER', 'main', (p) => { p.query_at = '2026-01-01T00:00:00Z'; }],
    ['PERIOD_INVALID', 'main', (p) => { p.series[S.curve].observation_period = '2025-13'; p.series[S.curve].data_asof = '2025-13'; }],
    ['REASON_MISSING', 'main', (p) => { p.series[S.temp].reason = null; }],
  ];
  for (const [code, k, fn] of cases) {
    const r = M.validate(X.mutate(k, fn));
    assert.equal(r.ok, false, code); assert.equal(r.code, code, code + ' got ' + r.code + ' at ' + r.path); assert.equal(r.value, undefined);
  }
  for (const bad of [null, [], 'x', 1]) assert.equal(M.validate(bad).ok, false);
});

ok('age and reason words', () => {
  assert.deepEqual([0, 59, 60, 3600, 5400, 86400, 129600].map(M.ageText), ['0초', '59초', '1분', '1시간', '1시간 30분', '1일', '1일 12시간']);
  assert.equal(M.reasonText('NOPE'), '사유 코드 미등록 · NOPE');
});

(async () => {
  const s = await M.source();
  assert.deepEqual([s.state, s.payload, s.code], ['NONE', null, 'MACRO_CURRENT_NOT_CONNECTED']); n++; console.log('PASS source() is NONE: no payload, no request');
  console.log(JSON.stringify({ passed: true, checks: n }));
})().catch((e) => { console.error(e); process.exitCode = 1; });
