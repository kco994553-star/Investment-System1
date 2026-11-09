'use strict';
// 공통 사전 + 산업 → 매크로 근거 (owner 2026-11-09 queue item 5; Codex #525 731e4682). Synthetic only.
//  - web_app/common-taxonomy.js is Codex's current_taxonomy() as is: equal to Codex's public fixture taxonomy.json (pinned SHA-256);
//    TELECOMMUNICATIONS = 통신서비스; the screens' sector names come from it (classification.sectorName, sector-qgv SECTOR_TEXT); a
//    record's own dictionary (/1 says 통신) and its hash are not changed by a name.
//  - web_app/industry-macro.js reads Codex's company-industry-macro-query/1 outputs (tests/fixtures/industry_macro_main/outputs.json:
//    Codex's own query on Codex's synthetic inputs and each case of cases.json): every produced output is accepted with the counts
//    Codex's cases expect; the refused case stays a producer refusal; words keep UNKNOWN apart from a link and a link apart from a regime;
//    the reader refuses a changed contract.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const R = require('./web_app_reuse');
const T = R.requireNew('common-taxonomy.js');
const M = R.requireNew('industry-macro.js');
const C = R.requireNew('classification.js');
const S = R.requireNew('sector-qgv.js');
const FIX = path.join(__dirname, '..', 'tests', 'fixtures');
const OUT = JSON.parse(fs.readFileSync(path.join(FIX, 'industry_macro_main', 'outputs.json'), 'utf8'));
const VIEW = JSON.parse(fs.readFileSync(path.join(FIX, 'macro_industry_evidence', 'view.json'), 'utf8'));
const clone = (v) => JSON.parse(JSON.stringify(v));
const out = (id) => clone(OUT.cases.find((c) => c.id === id).output);

test('one dictionary: the embedded current taxonomy is Codex\'s, names come from it, records keep their own dictionary', () => {
  const raw = fs.readFileSync(path.join(FIX, 'macro_industry_evidence', 'taxonomy.json'));
  assert.equal(crypto.createHash('sha256').update(raw).digest('hex'), '0804c7c54ebc34064129de45a08fafcb782286a22869aa99cfbd2cf889cf712d', 'Codex fixture pinned (#437 6721800433)');
  assert.deepEqual(JSON.parse(JSON.stringify(T.DATA)), JSON.parse(raw.toString('utf8')));
  assert.equal(T.NAME, '투자시스템 공통 10섹터'); assert.equal(T.VERSION, 'investment-system-common-10-sector/1');
  assert.equal(T.sectorName('TELECOMMUNICATIONS'), '통신서비스');
  assert.equal(T.DATA.sectors.length, 10); assert.equal(T.DATA.classification_effect, 'NONE_DISPLAY_DEFINITION_ONLY');
  assert.ok(Object.isFrozen(T.DATA) && Object.isFrozen(T.DATA.sectors[0]));
  assert.equal(T.sectorName('NOT_A_SECTOR'), 'NOT_A_SECTOR', 'an unknown id is shown as the id');
  // the screens read it
  const dict1 = { sectors: { TELECOMMUNICATIONS: '통신' }, industries: [] }, before = JSON.stringify(dict1);
  assert.equal(C.sectorName('TELECOMMUNICATIONS', dict1), '통신서비스', 'display name from the current definition');
  assert.equal(JSON.stringify(dict1), before, 'the record\'s dictionary object is not changed');
  assert.equal(C.sectorName('OTHER_ID', { sectors: { OTHER_ID: 'x' } }), 'x', 'fallback to the bundle dictionary for an id the definition does not know');
  assert.deepEqual({ ...S.SECTOR_TEXT }, Object.fromEntries(T.DATA.sectors.map((x) => [x.id, x.name])), 'sector QGV names = the definition');
  assert.equal(S.SECTOR_TEXT.TELECOMMUNICATIONS, '통신서비스');
  const src = fs.readFileSync(R.newPath('sector-qgv.js'), 'utf8');
  assert.doesNotMatch(src.replace(/\/\*[\s\S]*?\*\//g, ''), /TELECOMMUNICATIONS:'통신'/, 'no separate name table left in sector-qgv.js');
});

test('Codex\'s produced outputs are accepted with the counts its cases expect; the refused case stays refused', () => {
  assert.equal(OUT.cases.length, 8);
  for (const c of OUT.cases) {
    if (c.error) { assert.equal(c.codex_expected.error, c.error, c.id); continue; }
    const r = M.validate(clone(c.output), { view: VIEW });
    assert.equal(r.ok, true, c.id + ' ' + JSON.stringify(r));
    const e = c.codex_expected || {};
    if ('linked_companies' in e) assert.equal(c.output.counts.linked_companies, e.linked_companies, c.id);
    if ('unique_series' in e) assert.equal(c.output.counts.unique_series, e.unique_series, c.id);
    if ('value' in e) assert.equal((c.output.observations['SYN:SERIES'] || { value: null }).value, e.value, c.id);
    if ('query_usable_companies' in e) assert.equal(c.output.companies.filter((x) => x.query_usable_series_ids.length).length, e.query_usable_companies, c.id);
  }
  assert.equal(OUT.cases.find((c) => c.id === 'wrong_source_version').error, 'SOURCE_SERIES_DEFINITION_MISMATCH');
});

test('words: a link is not a regime; UNKNOWN keeps its reason and the macro query; 0 stays 0; a hidden value is 미산출', () => {
  const base = out('base'), s = M.summaryView(base), c0 = M.companyView(base, 'SYNTHETIC:COMPANY:0');
  assert.equal(s.head, '기업 행 2 · 산업 연결 2 · 활성 대응 1 · 계열 1');
  assert.match(s.not, /국면 판정 아님/); assert.match(s.keeps, /기존 매크로 현재 조회는 그대로/);
  assert.equal(c0.industry, '정보기술 · 반도체'); assert.match(c0.mappings[0], /복수 산업 대응\(비중 없음 · 나누거나 합치지 않음\)/);
  assert.match(c0.series[0], /^SYN:SERIES · 0 hours · 기간 2016-12/);
  const fv = M.companyView(out('future_value'), 'SYNTHETIC:COMPANY:0');
  assert.match(fv.series[0], /SYN:SERIES · 미산출 · 관측값이 평가 시점 뒤에 나옴/); assert.match(fv.head, /현재 조회 가능 0개/);
  const p = M.companyView(out('partial'), 'SYNTHETIC:COMPANY:1');
  assert.equal(p.status, 'UNKNOWN'); assert.match(p.head, /^산업 대응 미확인 · 근거가 확인된 산업 대응 없음$/);
  const ef = M.summaryView(out('evidence_future'));
  assert.equal(ef.head, '기업 행 2 · 산업 연결 0 · 활성 대응 0 · 계열 0'); assert.match(ef.inactive[0], /근거가 평가 시점 뒤에 확보됨/);
  assert.match(M.summaryView(out('date_precision')).inactive[0], /근거 확보 시각 미확인/);
  const u = M.summaryView(out('unknown'));
  assert.match(u.unknownMappings, /^미확인 대응 1건 · 공식 산업 정의 문서 미보유$/);
  assert.equal(M.companyView(base, 'NOT_THERE'), null);
});

test('refusals: fixed nulls, PIT, taxonomy, context, companies, series, counts, observations, mappings', () => {
  const cases = [
    ['NOT_NULL', (q) => { q.aggregate_value = 0; }], ['NOT_NULL', (q) => { q.probabilities = {}; }], ['NOT_NULL', (q) => { q.allocation_weights = [1]; }],
    ['PIT_CLAIMED', (q) => { q.historical_pit_certified = true; }], ['OFFICIAL_CHANGED', (q) => { q.official_results_changed = true; }],
    ['TAXONOMY_VERSION_MISMATCH', (q) => { q.taxonomy.version = 'investment-system-common-10-sector/2'; }],
    ['TAXONOMY_MISMATCH', (q) => { q.taxonomy.sectors.find((x) => x.id === 'TELECOMMUNICATIONS').name = '통신'; }],
    ['CLASSIFICATION_CONTEXT_MISMATCH', (q) => { q.classification_context.classification_hash = 'f'.repeat(64); }],
    ['COMPANY_INVALID', (q) => { q.companies.push(clone(q.companies[0])); }],
    ['UNKNOWN_REASON_REQUIRED', (q) => { q.companies[0].mapping_status = 'UNKNOWN'; }],
    ['MAPPING_REF_UNKNOWN', (q) => { q.companies[0].mapping_refs[0].revision_id = '9'; }],
    ['SERIES_UNKNOWN', (q) => { q.companies[0].related_series_ids = ['OTHER']; q.companies[0].query_usable_series_ids = []; }],
    ['SERIES_NOT_USABLE', (q) => { q.observations['SYN:SERIES'].query_usable = false; }],
    ['OBSERVATION_VALUE_WITH_REASON', (q) => { q.observations['SYN:SERIES'].query_reasons = ['OBSERVATION_NOT_AVAILABLE']; }],
    ['COUNTS_MISMATCH', (q) => { q.counts.linked_companies = 1; }],
    ['MAPPING_INVALID', (q) => { q.mappings[0].allocation_weights = [0.5, 0.5]; }],
    ['UNKNOWN_MAPPING_REASON_REQUIRED', (q) => { q.mappings[0].relation = 'UNKNOWN'; q.mappings[0].status = 'UNKNOWN'; q.mappings[0].unknown_reasons = []; }],
    ['MAPPING_EVIDENCE_MISSING', (q) => { q.evidence = []; }],
    ['SCHEMA', (q) => { q.schema_version = 'company-industry-macro-query/2'; }],
  ];
  for (const [code, f] of cases) { const q = out('base'); f(q); assert.equal(M.validate(q, { view: VIEW }).code, code, code); }
  assert.equal(M.validate(out('base')).ok, true, 'without a view the context is not compared (the screen always passes one)');
});
