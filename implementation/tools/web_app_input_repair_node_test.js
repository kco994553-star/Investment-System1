'use strict';
// 입력 연결 수정 전후 비교 reader (web_app/input-repair.js) against Codex #527 sector_qgv_held_repair.comparison outputs
// (tests/fixtures/input_repair_comparison/outputs.json: Codex's preview_qgv with the default configuration and Codex's comparison on
// Codex's synthetic input; see tools/input_repair_comparison_fixture.py). Synthetic only.
//  - every produced output is accepted for the result it names (after_input_hash, date, denominator) and refused for any other;
//  - the refused case (a setting change) stays the producer's refusal: the screen never receives a comparison for a setting change;
//  - words: 입력 연결 수정, never 요소·비중 or 분류 변경; a common-valid change is a relative score shift, not 실적 개선; performance and
//    the whole market stay 미측정; a structural small group stays a shortfall; null is 미산출, 0 is 0;
//  - arithmetic, keys and the same-input case are checked as written.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../src/investment_system/product/web_app/input-repair.js');
const OUT = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'tests', 'fixtures', 'input_repair_comparison', 'outputs.json'), 'utf8'));
const clone = (v) => JSON.parse(JSON.stringify(v));
const out = (id) => clone(OUT.cases.find((c) => c.id === id).output);
const anchorFor = (x, over = {}) => ({ scopes: [{ scope: 'operating', valuation_date: x.valuation_date, input_hash: x.after_input_hash, denominator: x.denominator, ...over }] });

test('Codex\'s outputs are accepted for the result they name; the setting change stays the producer\'s refusal', () => {
  assert.equal(OUT.cases.length, 5);
  for (const c of OUT.cases) {
    if (c.error) { assert.equal(c.id, 'config_changed'); assert.equal(c.error, 'REPAIR_CONFIG_CHANGED'); continue; }
    const r = R.validate(clone(c.output), anchorFor(c.output));
    assert.equal(r.ok, true, c.id + ' ' + JSON.stringify(r)); assert.equal(r.value.scope, 'operating');
  }
});

test('anchor: another result, date or denominator, or no anchor at all, is refused', () => {
  const x = out('peer_minimum');
  assert.equal(R.validate(x, anchorFor(x, { input_hash: 'a'.repeat(64) })).code, 'COMPARISON_RESULT_MISMATCH');
  assert.equal(R.validate(x, anchorFor(x, { input_hash: x.before_input_hash })).code, 'COMPARISON_RESULT_MISMATCH', 'the before result is not the delivered one');
  assert.equal(R.validate(x, anchorFor(x, { denominator: x.denominator + 1 })).code, 'COMPARISON_RESULT_MISMATCH');
  assert.equal(R.validate(x, anchorFor(x, { valuation_date: '2026-11-05' })).code, 'COMPARISON_DATE_MISMATCH');
  assert.equal(R.validate(x, null).code, 'ANCHOR_REQUIRED'); assert.equal(R.validate(x, { scopes: [] }).code, 'ANCHOR_REQUIRED');
  // From a checked held issuer bundle: each coverage scope's own context.
  const bundle = { coverage: { scopes: { operating: { context: { valuation_date: x.valuation_date, population: { denominator: x.denominator }, result_identity: { input_hash: x.after_input_hash } } },
    catalog: { context: { valuation_date: x.valuation_date, population: { denominator: 8004 }, result_identity: { input_hash: 'b'.repeat(64) } } } } } };
  assert.deepEqual(R.anchorOf(bundle).scopes.map((s) => s.scope), ['operating', 'catalog']);
  assert.equal(R.validate(x, R.anchorOf(bundle)).value.scope, 'operating');
});

test('words: input connection repair, not a setting or classification change; a relative shift is not performance', () => {
  const pm = out('peer_minimum'), v = R.view(pm, 'operating');
  assert.match(v.head, /^입력 연결 수정 전후 비교 \(INPUT_CONNECTION_REPAIR\) · 평가일 \d{4}-\d{2}-\d{2} · 분모 20 · 운영504 코드 행$/);
  assert.match(v.not, /요소·비중 변경 아님 · 분류 변경 아님 · 설정 변경 아님/); assert.match(v.limits, /성과 미측정 · 전체시장 분모 미측정/);
  assert.equal(v.axes.find((a) => a.key === 'Q').text, 'Q · 전 0 → 후 20 · 새로 산출 +20 · 산출 사라짐 0 · 기존 값 바뀜 0 / 20');
  assert.equal(v.axes.find((a) => a.key === 'joint').text.split(' · ')[0], 'Q·G·V 세 축 동시');
  assert.equal(v.shift, null, 'no common-valid value changed here');
  assert.ok(v.rows.length > 0 && v.rows.every((r) => /· Q 미산출→/.test(r.text)), 'null before is 미산출, never 0');
  // peer_shift: the pool stays above the minimum, new raw inputs enter → existing scores move (a relative shift)
  const ps = R.view(out('peer_shift'), 'operating');
  assert.equal(ps.axes.find((a) => a.key === 'Q').text, 'Q · 전 21 → 후 24 · 새로 산출 +3 · 산출 사라짐 0 · 기존 값 바뀜 20 / 24');
  assert.match(ps.shift, /상대점수가 달라진 것 · 기업 실적 개선·전략 성과 아님$/);
  assert.ok(ps.factors.some((f) => /^operating_margin_ttm · 원지표 · 기본 선택 행 · 전 21 → 후 24 · 새로 산출 \+3/.test(f.text)));
  // small_group: a sector group below the minimum stays a structural shortfall, named by the current taxonomy
  const sg = R.view(out('small_group'), 'operating', { sectorName: (id) => (id === 'ENERGY' ? '에너지' : id) });
  assert.ok(sg.shortfall.length > 0 && sg.shortfall.every((t) => /구성원 \d+ · 원지표 \d+ · 점수 대표 \d+ · 최소 20$/.test(t)));
  assert.ok(sg.shortfall.some((t) => t.startsWith('에너지 · GENERAL · ')));
  assert.match(sg.shortfallWord, /입력 연결로 풀리지 않음/);
  // no_change: the same input, nothing moved
  const nc = R.view(out('no_change'), 'operating');
  assert.equal(nc.same, '전후 입력이 같음 · 바뀐 것 없음'); assert.equal(nc.rows.length, 0); assert.equal(nc.factors.length, 0);
});

test('refusals: keys, treatment, arithmetic, ranges, rows, groups, market, performance, same input', () => {
  const cases = [
    ['SCHEMA', (x) => { x.schema_version = 'sector-qgv-input-repair-comparison/2'; }],
    ['TREATMENT', (x) => { x.treatment = 'FACTOR_WEIGHT_CHANGE'; }],
    ['KEYS', (x) => { x.extra = 1; }], ['KEYS', (x) => { delete x.groups; }],
    ['COUNT_ARITHMETIC', (x) => { x.axes.Q.after = 19; }],
    ['COUNT_RANGE', (x) => { x.axes.G.before = x.denominator + 1; x.axes.G.after = x.denominator + 1; }],
    ['COUNT_ARITHMETIC', (x) => { x.axes.Q.changed_common = x.axes.Q.before - x.axes.Q.lost + 1; }],
    ['FACTOR_KEY', (x) => { x.factors['Bad Key'] = { before: 0, after: 0, gained: 0, lost: 0, changed_common: 0 }; }],
    // a selected-row count above the all-row count (within the denominator)
    ['COUNT_ARITHMETIC', (x) => { const k = Object.keys(x.factors).find((y) => y.endsWith(':selected') && x.factors[y.replace(':selected', ':all')].before < x.denominator);
      const c = x.factors[k]; c.before = x.factors[k.replace(':selected', ':all')].before + 1; c.gained = Math.min(c.gained, x.denominator - c.before); c.lost = 0; c.changed_common = 0; c.after = c.before + c.gained; }],
    ['ROWS_INVALID', (x) => { x.rows[1].company_id = x.rows[0].company_id; }], ['TYPE', (x) => { x.rows.push(clone(x.rows[0])); }],
    ['ROWS_INVALID', (x) => { x.rows[0].factors = []; }],
    ['GROUPS_INVALID', (x) => { x.groups[0].structural_shortfall = !x.groups[0].structural_shortfall; }],
    ['GROUPS_INVALID', (x) => { x.groups[0].raw_valid = x.groups[0].members + 1; }],
    ['MARKET_NOT_NULL', (x) => { x.whole_market_denominator = 0; }],
    ['PERFORMANCE_CLAIMED', (x) => { x.performance = 'IMPROVED'; }],
    ['NO_CHANGE_INCONSISTENT', (x) => { x.before_input_hash = x.after_input_hash; }],
    ['HASH', (x) => { x.after_input_hash = 'XYZ'; }],
  ];
  for (const [code, f] of cases) { const x = out('peer_minimum'); f(x); assert.equal(R.validate(x, anchorFor(x)).code, code, code); }
});
