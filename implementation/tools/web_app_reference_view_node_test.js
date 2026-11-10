'use strict';
// 참조집단 확대 연구 reader (web_app/reference-view.js) against Codex #528 2ca567b2's synthetic view
// (docs/research/sector_qgv/reference-synthetic/view.json, pinned in its manifest.json). Synthetic only.
//  - accepted only for the delivered result it evaluated (population id / version / members hash / denominator, day, input
//    and config hash); refused for any other;
//  - two populations apart (evaluation code rows / issuers vs reference issuers); reference-only issuers never rows; a null total
//    has a null rank; per-group reference N = its reference issuers and stays whatever the screen shows;
//  - words: 참조집단 확대 is its own comparison type (not 원값 보완, 핵심 요소 축소 or 비중 변경); not adopted, no performance,
//    no whole market; null is 미산출.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const RV = require('../src/investment_system/product/web_app/reference-view.js');
const D = path.join(__dirname, '..', 'docs', 'research', 'sector_qgv', 'reference-synthetic');
const RAW = fs.readFileSync(path.join(D, 'view.json'));
const clone = (v) => JSON.parse(JSON.stringify(v));
const base = () => JSON.parse(RAW.toString('utf8'));
const anchorFor = (x, over = {}) => { const e = x.evaluation_population;
  return { scopes: [{ scope: 'operating', valuation_date: e.valuation_date, population_id: e.id, population_version: e.version, members_hash: e.members_hash,
    denominator: e.code_rows, input_hash: e.input_hash, config_hash: x.bindings.config_hash, ...over }] }; };

test('the synthetic view is Codex\'s pinned bytes and is accepted for the result it evaluated', () => {
  const m = JSON.parse(fs.readFileSync(path.join(D, 'manifest.json'), 'utf8')).files.find((f) => f.path === 'view.json');
  assert.equal(crypto.createHash('sha256').update(RAW).digest('hex'), m.sha256, 'Codex manifest pin');
  const x = base(), r = RV.validate(x, anchorFor(x));
  assert.equal(r.ok, true, JSON.stringify(r)); assert.equal(r.value.scope, 'operating');
  // from a checked bundle's coverage context
  const e = x.evaluation_population, bundle = { coverage: { scopes: { operating: { context: { valuation_date: e.valuation_date,
    population: { id: e.id, version: e.version, members_hash: e.members_hash, denominator: e.code_rows }, result_identity: { input_hash: e.input_hash, config_hash: x.bindings.config_hash } } } } } };
  assert.equal(RV.validate(x, RV.anchorOf(bundle)).ok, true);
});

test('anchor: another population, members, denominator, input, day or config is refused; no anchor is refused', () => {
  const x = base();
  for (const [k, v] of [['population_id', 'OTHER'], ['population_version', '2'], ['members_hash', 'a'.repeat(64)], ['denominator', 4], ['input_hash', 'b'.repeat(64)]])
    assert.equal(RV.validate(x, anchorFor(x, { [k]: v })).code, 'REFERENCE_RESULT_MISMATCH', k);
  assert.equal(RV.validate(x, anchorFor(x, { valuation_date: '2026-11-03' })).code, 'REFERENCE_DATE_MISMATCH');
  assert.equal(RV.validate(x, anchorFor(x, { config_hash: 'c'.repeat(64) })).code, 'REFERENCE_CONFIG_MISMATCH');
  assert.equal(RV.validate(x, null).code, 'ANCHOR_REQUIRED');
});

test('words: two populations apart, reference N fixed, its own comparison type, not adopted; null is 미산출', () => {
  const x = base(), w = RV.view(x, 'operating', { sectorName: (id) => (id === 'INFORMATION_TECHNOLOGY' ? '정보기술' : id) });
  assert.equal(w.type, '참조집단 확대'); assert.notEqual(w.type, RV.TYPE.INPUT_REPAIR);
  assert.deepEqual(Object.values(RV.TYPE), ['참조집단 확대', '원값 보완(입력 연결 수정)', '핵심 요소 축소', '비중 변경']);
  assert.match(w.head, /^참조집단 확대 연구 \(PRIVATE_RESEARCH · 운영 채택 안 됨\) · SYN-REF-01 v1 · 평가일 2026-11-02$/);
  assert.match(w.not, /참조 전용 기업은 순위·분모에 들어가지 않음/); assert.match(w.limits, /성과 미측정 · 전체시장 분모 미측정 · 공식 QGV·TARGET에 반영되지 않음/);
  assert.match(w.evaluation, /^평가 모집단 SYN-EVAL · 코드 행 3 · 고유 발행사 3 · /);
  assert.match(w.reference, /^참조집단 SYN-REF v1 · 발행사 20 \(외부 추가 17\) · 요소 입력이 적격인 연구 참조 · 상장·증권·투자 적격 확인 아님/);
  assert.equal(w.axes.find((a) => a.key === 'Q').text, 'Q · 코드 행 전 0 → 후 3 (새로 +3 · 사라짐 0 · 기존 값 바뀜 0) · 고유 발행사 0 → 3 (새로 +3)');
  assert.equal(w.axes.find((a) => a.key === 'total').text, '최종 총점 · 코드 행 전 0 → 후 0 (새로 +0 · 사라짐 0 · 기존 값 바뀜 0) · 고유 발행사 0 → 0 (새로 +0)', '0 stays 0');
  assert.equal(w.newAny, 'Q·G·V 중 한 축이라도 새로 생긴 고유 발행사 3 / 3', 'Q and G gains 3 each, union 3');
  assert.ok(w.groups.length > 0 && w.groups.every((g) => /참조 N [\d/]+ → 20 \(외부 추가 \d+\) · 최소 20$/.test(g.text)));
  assert.ok(w.rows.every((r) => / · 총점 미산출→미산출 · 순위 미산출→미산출$/.test(r.text)), 'missing V: total and rank stay 미산출');
  assert.match(w.nFixed, /화면 필터로 바뀌지 않음/);
  assert.ok(!JSON.stringify(w).includes('company-019'), 'no reference member list in the words');
});

test('refusals: claims, identities, counts, rows and groups as written', () => {
  const cases = [
    ['SCHEMA', (x) => { x.schema_version = 'sector-qgv-reference-view/2'; }],
    ['VISIBILITY', (x) => { x.visibility = 'PUBLIC'; }],
    ['ADOPTION_CLAIMED', (x) => { x.operating_adoption = 'ADOPTED'; }],
    ['RANK_SCOPE', (x) => { x.rank_scope = 'WHOLE_MARKET'; }],
    ['PERFORMANCE_CLAIMED', (x) => { x.performance = { return: 0.1 }; }],
    ['MARKET_NOT_NULL', (x) => { x.whole_market_denominator = 8004; }],
    ['KEYS', (x) => { x.extra = 1; }],
    ['REFERENCE_DATE_MISMATCH', (x) => { x.reference_population.valuation_date = '2026-11-01'; }],
    ['BINDINGS_MISMATCH', (x) => { x.bindings.evaluation = { ...x.bindings.evaluation, code_rows: 4 }; }],
    ['DENOMINATOR_MISMATCH', (x) => { x.comparison.denominator_code_rows = 4; }],
    ['COUNT_ARITHMETIC', (x) => { x.comparison.axes.Q.lost_rows = 1; }],
    ['COUNT_RANGE', (x) => { x.comparison.axes.G.after_issuers = 4; }],
    ['ROWS_INVALID', (x) => { x.comparison.rows[1].company_id = x.comparison.rows[0].company_id; }],
    ['ROWS_INVALID', (x) => { x.comparison.rows.pop(); }],
    ['RANK_WITHOUT_TOTAL', (x) => { x.comparison.rows[0].after_rank = 1; }],
    ['GROUPS_INVALID', (x) => { x.groups[0].after_valid_n += 1; }],
    ['GROUPS_INVALID', (x) => { x.groups[0].reference_issuers.push(x.groups[0].reference_issuers[0]); }],
    ['POPULATION_INVALID', (x) => { x.evaluation_population.members_hash = 'x'; x.bindings.evaluation.members_hash = 'x'; }],
  ];
  for (const [code, f] of cases) { const x = base(); f(x); assert.equal(RV.validate(x, anchorFor(base())).code, code, code); }
  // a refused view leaves nothing half-read: validate is pure
  const x = base(), y = clone(x); RV.validate(x, anchorFor(x)); assert.deepEqual(x, y);
});
