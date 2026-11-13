'use strict';
// QGV 3/3/3 (owner 2026-11-13 「3/3/3 인계 수령 정정 및 #535 연결 재개」; Codex #534 f79e9776, #437 6849630620 / 6849892120 /
// 6850109806 / 6850174335): the dual reader (web_app/dual-qgv.js) against Codex's pinned contract, boundary deliveries and full-bin
// examples (docs/research/sector_qgv/qgv333-examples, manifest.json). Checks:
//  - the registration is the contract: model ids, version, adapter, qgv-dual-config/2, each configuration hash = SHA-256 of the
//    contract's canonical candidate config, the unified nine factors, and the factor evidence table as the contract states it;
//  - one generation per delivery, in its own slot: old and new candidates never mixed, a 3/3/3 delivery never read as U1 / U2 / S1;
//  - another configuration, version or adapter refused (Codex's rejected_config_versions, and an integer weight given as true / 1.0);
//  - the boundary cases as Codex expects them (UNKNOWN gate: total null with nine scores; core missing: G null), Q / G and factors
//    shown without a total, no total rank without a total, PREPARING never with a total;
//  - the exact rational weights checked as written (reduced, axes sum to 1, a third of the axis per core factor, 1/9 for unified);
//  - the applicability-only upper bound's arithmetic as written; the full-bin path for the 3/3/3 boards.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const DQ = require('../src/investment_system/product/web_app/dual-qgv.js');
const DF = require('./web_app_dual_fixture.js');
const QX = path.join(DF.D, '..', 'qgv333-examples');
const sha256 = async (b) => crypto.createHash('sha256').update(b).digest('hex');
const canon = (v) => Array.isArray(v) ? '[' + v.map(canon).join(',') + ']' : v && typeof v === 'object' ? '{' + Object.keys(v).sort().map((k) => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}' : JSON.stringify(v);
const hash = (v) => crypto.createHash('sha256').update(canon(v)).digest('hex');
const CONTRACT = JSON.parse(fs.readFileSync(path.join(QX, 'qgv-333-contract.json'), 'utf8'));
const EXPECTED = JSON.parse(fs.readFileSync(path.join(QX, 'boundary-delivery', 'expected.json'), 'utf8'));
const P = (files, f) => { const bytes = new Uint8Array(files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
const anchorOf = (d) => { const e = P(d.files, 'summary.json').body.boards['U2-333'].evaluation_population;
  return { scopes: [{ scope: 'operating', valuation_date: e.valuation_date, population_id: e.id, population_version: e.version, members_hash: e.members_hash, denominator: e.code_rows, input_hash: e.input_hash, config_hash: null }] }; };
const check = (d, slot = 'operating504@333') => DQ.checkDelivery({ manifest: P(d.files, 'manifest.json'), summary: P(d.files, 'summary.json'), index: P(d.files, 'index.json') }, { scope: slot, anchor: anchorOf(d), sha256 });
const Q = ['U2-333', 'U1-333', 'S1-333'];

test('Codex\'s pinned examples; the registration is the contract (ids, version, adapter, config/2, configuration hashes, nine factors, evidence)', async () => {
  const m = JSON.parse(fs.readFileSync(path.join(QX, 'manifest.json'), 'utf8'));
  for (const f of m.files) { const b = fs.readFileSync(path.join(QX, f.path)); assert.equal(b.length, f.size, f.path); assert.equal(await sha256(b), f.sha256, f.path); }
  for (const k of Q) {
    const M = DQ.MODELS[k], c = CONTRACT.candidates[k];
    assert.deepEqual([M.model_id, M.version, M.adapter, M.config, M.gen, M.kind], [c.model_id, c.version, c.execution_version, c.schema_version, 'Q333', c.kind]);
    assert.equal(M.configuration_hash, hash(c), k + ': the registered configuration is the contract\'s exact candidate config');
    if (c.kind === 'COMMON') {
      const ax = c.uniform_preset.axes, f = ['Q', 'G', 'V'].flatMap((a) => Object.values(ax[a]).flatMap((r) => Object.keys(r.factors)));
      assert.deepEqual(M.factors, f, k + ': the nine core factors'); assert.deepEqual(c.uniform_preset.axis_weights, { Q: 1, G: 1, V: 1 });
    } else assert.equal(M.factors, null, 'S1-333: its factors are per sector × accounting model (each row\'s own selected variants)');
  }
  assert.deepEqual(Object.keys(DQ.EVIDENCE_333).sort(), Object.keys(CONTRACT.factors).sort());
  for (const [v, f] of Object.entries(CONTRACT.factors)) {
    const e = DQ.EVIDENCE_333[v];
    assert.deepEqual([e.axis, e.role, e.name, e.formula, e.period, e.direction, e.status], [f.axis, f.role, f.display_name, f.formula, f.period, f.direction, f.calculator_status], v);
  }
  assert.equal(CONTRACT.additional_core_weight, 0); assert.equal(CONTRACT.unavailable_is_zero, false); assert.equal(CONTRACT.deciles, 'stored-evaluation-deciles/1');
  for (const k of ['U1', 'U2', 'S1']) assert.equal(DQ.MODELS[k].gen, 'REDUCED');
  // Codex #534 EPS history (6851482941): its own input gap, never shown as waiting for a price only.
  assert.equal(DQ.word('HISTORICAL_SHARE_BASIS_UNCONFIRMED'), '역사 보통주 귀속 근거 미확인(가격 대기 아님)');
});

test('boundary deliveries: accepted in the 3/3/3 slot as Codex expects; refused in the reduced slot; the reduced delivery refused in the 3/3/3 slot', async () => {
  for (const [id, cases] of Object.entries(EXPECTED.cases)) {
    const d = DF.q333(null, id), r = await check(d);
    assert.equal(r.ok, true, id + ' ' + JSON.stringify(r)); assert.deepEqual(r.value.models, Q); assert.equal(r.value.slot, 'operating504@333'); assert.equal(r.value.scope, 'operating504'); assert.equal(r.value.gen, 'Q333');
    const x = await DQ.checkDetail(P(d.files, 'detail-000.json'), 'detail-000.json', r.value, sha256);
    assert.equal(x.ok, true, id + ' detail ' + JSON.stringify(x));
    for (const [k, e] of Object.entries(cases)) {
      const b = x.value.get(e.company_id).boards[k];
      assert.deepEqual([b.axes, b.total, b.gate_status, b.missing_factors], [e.axes, e.total, e.gate_status, e.missing_factors], id + ' ' + k);
      const v = DQ.compareView(x.value.get(e.company_id), r.value, {}).boards.find((y) => y.key === k);
      assert.equal(v.rank, '총점 없음 · 순위 없음', 'no total, no total rank'); assert.match(v.axes, /^Q 66\.7 · G (미산출|0\.0) · V 0\.0 · 총점 미산출$/, 'Q / G / V shown without a total');
      assert.equal(v.core.length, 9); assert.equal(v.evidence.length, 9);
    }
    assert.equal((await check(d, 'operating504')).code, 'MODEL_GENERATION_SLOT', id + ': never read into the reduced slot');
  }
  const old = DF.delivery('operating504');
  const r = await DQ.checkDelivery({ manifest: P(old.files, 'manifest.json'), summary: P(old.files, 'summary.json'), index: P(old.files, 'index.json') }, { scope: 'operating504@333', anchor: DF.anchor(), sha256 });
  assert.equal(r.code, 'MODEL_GENERATION_SLOT', 'U1 / U2 / S1 are not 3/3/3 boards');
  const u = await check(DF.q333(null, 'unknown-gate')), x = await DQ.checkDetail(P(DF.q333(null, 'unknown-gate').files, 'detail-000.json'), 'detail-000.json', u.value, sha256);
  const b = x.value.get('company-000').boards['U2-333'];
  assert.equal(b.selected_variants.filter((v) => b.factors[v].score !== null).length, 9, 'UNKNOWN gate: nine core scores'); assert.equal(b.total, null, 'and still no total');
});

test('one generation per bundle; another configuration, version or adapter refused (rejected_config_versions, true / 1.0 for integer 1)', async () => {
  const oldU1 = DF.parse('summary.json').boards.U1;
  assert.equal((await check(DF.q333(null, 'core-missing', (x) => { x['summary.json'].boards.U1 = oldU1; }))).code, 'MODEL_GENERATION_MIXED');
  for (const rej of EXPECTED.rejected_config_versions) {
    const c = JSON.parse(JSON.stringify(CONTRACT.candidates[rej.candidate])); assert.equal(hash(c), rej.base_configuration_hash); Object.assign(c, rej.mutation);
    const r = await check(DF.q333(null, 'core-missing', (x) => { const b = x['summary.json'].boards[rej.candidate]; b.configuration_hash = hash(c); b.bindings.model_hash = hash(c); }));
    assert.equal(r.code, 'CONFIG_VERSION_MISMATCH', rej.candidate + ' ' + rej.expected_error);
  }
  for (const bad of [true, 1.0000001]) {
    const c = JSON.parse(JSON.stringify(CONTRACT.candidates['U2-333'])); c.uniform_preset.axis_weights.Q = bad;
    assert.notEqual(hash(c), DQ.MODELS['U2-333'].configuration_hash);
    const r = await check(DF.q333(null, 'core-missing', (x) => { const b = x['summary.json'].boards['U2-333']; b.configuration_hash = hash(c); b.bindings.model_hash = hash(c); }));
    assert.equal(r.code, 'CONFIG_VERSION_MISMATCH', String(bad));
  }
  const cases = [['MODEL_VERSION_UNKNOWN', (b) => { b.adapter_version = 'dual-qgv-research/0.1.0'; b.bindings.adapter_version = 'dual-qgv-research/0.1.0'; }],
    ['MODEL_VERSION_UNKNOWN', (b) => { b.model_version = '999.0.0'; }], ['MODEL_MISMATCH', (b) => { b.model_id = 'unified-roa-core/0.1.0'; }]];
  for (const [code, f] of cases) assert.equal((await check(DF.q333(null, 'core-missing', (x) => f(x['summary.json'].boards['U1-333'])))).code, code);
  assert.equal((await check(DF.q333(null, 'core-missing', (x) => { delete x['summary.json'].boards['S1-333'].coverage.stages.gate_known; }))).code, 'KEY_MISSING');
  assert.equal((await check(DF.q333(null, 'core-missing', (x) => { x['summary.json'].boards['S1-333'].coverage.stages.gate_known.issuers = 2; }))).code, 'STAGE_COUNT_MISMATCH');
  assert.equal((await check(DF.q333(null, 'core-missing', (x) => { x['summary.json'].boards['U2-333'].coverage.applicability_only_upper_bound.can_reach95_under_known_scope = false; }))).code, 'UPPER_BOUND_INVALID');
  assert.equal((await check(DF.q333(null, 'core-missing', (x) => { x['summary.json'].boards['U2-333'].coverage.applicability_only_upper_bound.assumptions = 'FORECAST'; }))).code, 'UPPER_BOUND_INVALID');
  assert.equal((await check(DF.q333(null, 'unknown-gate', (x) => { for (const r of x['index.json'].rows) if (r.boards['U2-333'].gate_status === 'UNKNOWN') { r.boards['U2-333'].total = 50; } }))).code, 'GATE_UNKNOWN_WITH_TOTAL');
});

test('detail: exact rational weights as written, recipe state, PREPARING without a total; refusals keep the delivery', async () => {
  const run = async (edit) => { const d = DF.q333(null, 'core-missing', (x) => edit(x['detail-000.json'].rows[0].boards)), r = await check(d);
    assert.equal(r.ok, true); return DQ.checkDetail(P(d.files, 'detail-000.json'), 'detail-000.json', r.value, sha256); };
  const F = (b) => b.weight_fractions;
  const cases = [
    ['FRACTION_INVALID', (B) => { F(B['U2-333']).nominal_factors.roa_ttm = { numerator: 2, denominator: 18 }; }],
    ['FRACTION_INVALID', (B) => { F(B['U2-333']).nominal_axes.Q = { numerator: 1, denominator: 0 }; }],
    ['FRACTION_INVALID', (B) => { F(B['U2-333']).nominal_axes.Q = { numerator: 0.5, denominator: 1.5 }; }],
    ['WEIGHT_SUM', (B) => { F(B['S1-333']).post_gate_axes.V = { numerator: 1, denominator: 2 }; }],
    ['WEIGHT_NOT_THIRD', (B) => { F(B['S1-333']).nominal_factors.operating_margin_ttm = { numerator: 1, denominator: 9 }; }],
    ['WEIGHT_NOT_REGISTERED', (B) => { const w = F(B['U1-333']); w.nominal_axes = { Q: { numerator: 1, denominator: 2 }, G: { numerator: 1, denominator: 4 }, V: { numerator: 1, denominator: 4 } };
      for (const v of B['U1-333'].selected_variants) w.nominal_factors[v] = { numerator: 1, denominator: { Q: 6, G: 12, V: 12 }[DQ.EVIDENCE_333[v].axis] }; }],
    ['CORE_NOT_REGISTERED', (B) => { const b = B['U2-333'], i = b.selected_variants.indexOf('eps_diluted_cagr_3y'); b.selected_variants[i] = 'revenue_growth_consistency_3y';
      b.factors.revenue_growth_consistency_3y = { ...b.factors.revenue_growth_consistency_3y, kind: 'CORE' }; b.factors.eps_diluted_cagr_3y.kind = 'ADDITIONAL';
      for (const s of ['nominal_factors', 'post_gate_factors']) { F(b)[s].revenue_growth_consistency_3y = F(b)[s].eps_diluted_cagr_3y; delete F(b)[s].eps_diluted_cagr_3y; } }],
    ['KEY_MISSING', (B) => { delete F(B['S1-333']).post_gate_factors.cfo_mcap; }],
    ['WEIGHT_FRACTIONS_MISSING', (B) => { delete B['U2-333'].weight_fractions; }],
    ['RECIPE_STATE', (B) => { B['S1-333'].recipe_state = 'READY'; }],
    ['KEY_MISSING', (B) => { delete B['S1-333'].recipe_state; }],
    ['PREPARING_WITH_TOTAL', (B) => { B['S1-333'].recipe_state = 'PREPARING'; B['S1-333'].total = 40; }],
    ['RAW_VALUE_PRESENT', (B) => { B['U2-333'].factors.roa_ttm.raw_value = 0; }],
  ];
  for (const [code, edit] of cases) { const x = await run(edit); assert.equal(x.ok, false, code); assert.equal(x.code, code, code + ' ' + x.path); }
  const ok = await run(() => {}); assert.equal(ok.ok, true);
  const s1 = DQ.compareView(ok.value.get('company-000'), (await check(DF.q333(null, 'core-missing'))).value, {}).boards.find((b) => b.key === 'S1-333');
  assert.equal(s1.weights, '축 비중(관문 전) Q 3/10 · G 1/4 · V 9/20 · 관문 뒤 Q 3/10 · G 1/4 · V 9/20 · 축 안 세 요소는 각 1/3', 'the producer\'s fractions, never a re-derived share');
  assert.match(s1.core[0], / · 총점 비중 1\/10$/); assert.equal(s1.missing, 'Q 결손 없음 · G 결손 eps_diluted_cagr_3y · V 결손 없음');
  assert.equal(s1.evidence[0], 'operating_margin_ttm · 영업이익률 · Q 축 profitability · 산식 ratio · 최근 4분기(TTM) · 높을수록 좋음');
});

test('views and RAM: the 3/3/3 stages, configuration and upper bound words; one slot per generation; the full-bin path for 3/3/3 boards', async () => {
  const d = DF.q333(null, 'core-missing'), r = await check(d), v = DQ.boardView(r.value, 'U2-333');
  assert.deepEqual(v.stages.map((s) => s.key), ['core_inputs', 'core_raw', 'core_scores', 'Q', 'G', 'V', 'joint', 'total', 'nine_core_scores', 'gate_known']);
  assert.match(v.config, /^설정 qgv-dual-config\/2 · 모형 unified-333-eps\/0\.1\.0 · 적용 dual-qgv-research\/0\.2\.0 · 등록된 정확한 설정과 일치/);
  assert.match(v.upper, /^적용 범위만 본 상한\(.*예측 아님\) 발행사 3 \/ 3 · 모든 행이 적용 부적합인 발행사 0 · 95% 목표 발행사 3 · 이 가정에서도 도달 가능$/);
  assert.equal(DQ.boardView((await DQ.checkDelivery({ manifest: P(DF.delivery('operating504').files, 'manifest.json'), summary: P(DF.delivery('operating504').files, 'summary.json'), index: P(DF.delivery('operating504').files, 'index.json') }, { scope: 'operating504', anchor: DF.anchor(), sha256 })).value, 'U1').upper, null);
  const ram = DQ.ramStore();
  assert.throws(() => ram.set('operating504', r.value), /DUAL_UNCHECKED/, 'a 3/3/3 delivery only in its own slot');
  ram.set('operating504@333', r.value); assert.equal(ram.get('operating504'), null); assert.equal(ram.get('operating504@333').delivery, r.value);
  // Codex's full-bin examples for the 3/3/3 boards (bins/ + bin-routing/): every group complete and routed.
  const f = (p) => { const bytes = new Uint8Array(fs.readFileSync(path.join(QX, p))); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const scopes = {}; for (const g of f('bins/distribution-000.json').body.parts) for (const row of g.rows) (scopes[row.company_id] ||= {})[g.group_id.split('|')[0]] = g.group_id.split('|').slice(1, -1).join('|');
  const D = await DQ.checkDistributionSynthetic({ manifest: f('bins/distribution-manifest.json'), index: f('bins/distribution-index.json') }, sha256, { scopes });
  assert.equal(D.ok, true, JSON.stringify(D)); assert.deepEqual([...new Set(D.value.groups.map((g) => g.board))], Q); assert.equal(D.value.display_policy, 'stored-evaluation-deciles/1');
  const part = await DQ.checkDistributionPart(f('bins/distribution-000.json'), 'distribution-000.json', D.value, sha256); assert.equal(part.ok, true, JSON.stringify(part));
  const bins = await DQ.checkBins({ manifest: f('bin-routing/bin-manifest.json'), index: f('bin-routing/bin-index.json') }, D.value, sha256); assert.equal(bins.ok, true, JSON.stringify(bins));
  const bp = await DQ.checkBinsPart(f('bin-routing/bins-000.json'), 'bins-000.json', bins.value, sha256); assert.equal(bp.ok, true, JSON.stringify(bp));
  let n = 0; for (const g of D.value.groups) { const G = DQ.distributionGroup(D.value, g.group_id, new Map([['distribution-000.json', part.value]]));
    assert.equal(G.ok, true, g.group_id); assert.equal((await DQ.binsMatchGroup(bp.value.get(g.group_id), G.value, sha256)).ok, true, g.group_id); n++; }
  assert.ok(n > 0);
});

// The 3/3/3 EPS input connection follow-up (owner 2026-11-13 「3/3/3 화면 연결 우선」 §1, §3; Codex #534 bfadb012): a progress record
// checked against Main's index (test-made counts here, the producer's shape); the stages kept apart; HISTORICAL_SHARE_BASIS_UNCONFIRMED
// never 「가격만 대기」; the numeric endpoint candidates never an adopted or eligible count; the input version shown and never mixed;
// the screen's results named by which side of the comparison they are; a result delivery is never read through it.
test('EPS stages: checked against the index; five stages, separate lines, times and input version; which side the screen is', async () => {
  const op = DF.q333(null, 'core-missing'), he = DF.q333('held1057');
  const parts = (e) => ({ index: P(e.files, 'eps-index.json'), diagnostic: P(e.files, 'diagnostic-summary.json'), comparison: P(e.files, 'run-comparison.json'), continuation: P(e.files, 'continuation-inputs.json') });
  const run = (edit) => DQ.checkEps(parts(DF.eps({ operating504: op, held1057: he }, edit)), sha256);
  const r = await run(); assert.equal(r.ok, true, JSON.stringify(r));
  const d = (await check(op)).value, v = DQ.epsView(r.value, 'operating504', d);
  assert.equal(v.onScreen, 'BEFORE'); assert.match(v.screen, /이전 입력 버전/);
  assert.deepEqual(v.stages.map((x) => x[0]), ['4개년 숫자 연결', '역사 보통주 기준 검토', '적격 원지표 채택', '요소 점수(희석 EPS 3년 성장)', 'G축 · 총점']);
  assert.match(v.stages[0][1], /^3 \/ 3 발행사\(구성값 하나라도 3\) · 숫자를 이은 것일 뿐 채택·점수 아님$/);
  assert.match(v.stages[1][1], /역사 보통주 귀속 근거 미확인」 3 발행사 · 가격 대기 아님 · .*0으로 채우지 않음/);
  assert.ok(!/가격만 대기/.test(JSON.stringify(v)), 'never 「가격만 대기」');
  assert.match(v.stages[2][1], /^0 \/ 3 발행사 · 수치 진단 후보 2 발행사 · 미채택 · 적격 EPS·채택 수가 아님$/);
  assert.match(v.stages[4][1], /산출 건수이지 점수가 아님/);
  assert.deepEqual(v.separate.map((x) => x[0]), ['공식 관문 판정 불가(U2-333)', '회계모형 미확정(U2-333)', 'Q 결손']);
  assert.match(v.version, /평가 입력 .+… → aaaaaaaaaaaa… · 참조 입력 .+… → bbbbbbbbbbbb… · 같은 평가일이라도 입력 버전이 다르면 다른 결과 · 섞지 않음$/);
  assert.deepEqual(v.times.map((x) => x[0]), ['평가일', '입력 마감(재무 스냅숏)', '분류 지식 시점', '역사 주식 기준 검토 시각', '새 원천 취득', '계산']);
  assert.match(v.times[5][1], /계산 시각 칸 없음\(전달 안 됨\)$/); assert.match(v.delivery, /결과 묶음.*전달 전/);
  assert.match(v.bounds, /^조건부 상한\(실제 회복 아님.*\) U2 2 \/ 3 · 회계 부적합 0 · EPS 비양수 1 · 합집합 1\(교집합 0\)/);
  assert.equal(DQ.epsView(r.value, 'operating504', null).onScreen, 'NOT_LOADED');
  const other = (await check(DF.q333(null, 'unknown-gate'))).value;
  assert.equal(DQ.epsView(r.value, 'operating504', other).onScreen, 'OTHER', 'other results are not this comparison\'s; never read together');
  const cases = [
    ['EPS_RESULT_DELIVERY', (x) => { x.index = { result_delivery: { manifest_sha256: 'e'.repeat(64) } }; }],
    ['EPS_BOUNDS', (x) => { x.diag.operating.structural_bounds.combined_upper = 3; }],
    ['EPS_DIAGNOSTIC', (x) => { x.diag.held.adopted_raw = 4; }],
    ['EPS_DATE_MISMATCH', (x) => { x.diag.held.as_of = '2026-11-03T00:00:00Z'; }],
    ['CONFIG_VERSION_MISMATCH', (x) => { x.comparison.operating504['S1-333'].after_bindings.model_hash = 'f'.repeat(64); }],
    ['EPS_COMPARISON', (x) => { delete x.comparison.held1057['U1-333']; }],
    ['EPS_INPUTS', (x) => { x.inputs.schema_version = 'qgv-333-eps-continuation/2'; }],
  ];
  for (const [code, edit] of cases) assert.equal((await run(edit)).code, code, code);
  const p = parts(DF.eps({ operating504: op, held1057: he })); p.comparison = { bytes: new Uint8Array([...p.comparison.bytes, 10]), body: p.comparison.body };
  assert.equal((await DQ.checkEps(p, sha256)).code, 'BYTES_MISMATCH', 'each file is the index\'s bytes');
});

// The 3/3/3 Q input recovery (owner 2026-11-13 §1 Q 결손·공식 관문 결손 별도 줄, §3 시각; Codex #534 4352c8ec): the next input
// version after the EPS step, checked against Main's index; primary Q causes, gate states and official input linkage each add up to
// the issuers and are shown apart (overlaps never added; linkage never a PASS count); the clocks kept apart (calculation time absent
// stays absent); the three input versions chained by hash; the screen's results named by version; a result delivery never read through it.
test('Q input recovery: separate Q-missing / gate / linkage lines, clocks, version chain and which version the screen is', async () => {
  const op = DF.q333(null, 'core-missing'), he = DF.q333('held1057'), E = DF.eps({ operating504: op, held1057: he });
  const eparts = { index: P(E.files, 'eps-index.json'), diagnostic: P(E.files, 'diagnostic-summary.json'), comparison: P(E.files, 'run-comparison.json'), continuation: P(E.files, 'continuation-inputs.json') };
  const ev = (await DQ.checkEps(eparts, sha256)).value;
  const parts = (q) => ({ index: P(q.files, 'q-index.json'), diagnostic: P(q.files, 'diagnostic-summary.json'), comparison: P(q.files, 'comparison.json') });
  const run = (edit) => DQ.checkQinput(parts(DF.qinput(E, edit)), sha256);
  const r = await run(); assert.equal(r.ok, true, JSON.stringify(r));
  const d = (await check(op)).value, v = DQ.qinputView(r.value, 'operating504', ev, d);
  assert.equal(v.onScreen, 'ORIGINAL'); assert.match(v.screen, /원래 입력 버전.*함께 읽지 않음/);
  assert.equal(v.chain, 'CHAINED'); assert.match(v.chainText, /원래 3\/3\/3 → EPS 연결 → Q 입력 복구/);
  assert.equal(DQ.qinputView(r.value, 'operating504', null, d).onScreen, 'OTHER', 'without the EPS step the original cannot be named');
  assert.equal(DQ.qinputView(r.value, 'operating504', null, d).chain, 'NOT_CHECKED');
  assert.equal(DQ.qinputView(r.value, 'operating504', ev, null).onScreen, 'NOT_LOADED');
  assert.deepEqual(v.times.map((x) => x[0]), ['평가일', '원래 입력 마감(재무)', '새 입력 마감(검토 반영)', '근거 검토 시각', '원천 취득', '생산자 검증 시각', '계산 시각']);
  assert.match(v.times[5][1], /계산 시각 아님$/); assert.match(v.times[6][1], /^전달 안 됨 · 실행 코드 444444444444로만 고정$/);
  assert.match(v.kind, /RETROSPECTIVE_REVIEW.*historical PIT\) 아님/);
  assert.deepEqual(v.qPrimary, [['Q 산출 가능', '2 / 3 발행사'], ['분류·회계모형 미확정', '1 / 3 발행사']]); assert.match(v.qPrimaryNote, /겹치지 않음 · 합계 3 = 3 발행사/);
  assert.match(v.qOverlapNote, /더하지 않음/); assert.equal(v.qOverlap.length, 2);
  assert.deepEqual(v.gate.map((x) => x[0]), ['공식 관문 판정 가능(통과 수 아님)', '판정 불가 · 공식 백분위는 연결됐으나 산식 미확정']);
  assert.deepEqual(v.link, [['공식 Q 백분위 입력 연결', '3 / 3 발행사']]); assert.match(v.linkNote, /판정 가능 수·통과 수가 아님/);
  assert.match(v.stages[0][1], /^Q 산출 1 → 2\(\+1 · 잃음 0 · 기존 점수 바뀜 1\)/); assert.match(v.relative, /재무 개선이 아님/);
  assert.match(v.delivery, /결과 묶음.*전달 전.*점수·순위·분위를 보이지 않음/);
  assert.ok(!/가격만 대기/.test(JSON.stringify(v)));
  // a different EPS step: the chain is broken and said so
  const E2 = DF.eps({ operating504: op, held1057: he }, (x) => { for (const k of ['U2-333', 'U1-333', 'S1-333']) x.comparison.operating504[k].after_result_hash = '9'.repeat(64); });
  const ev2 = (await DQ.checkEps({ index: P(E2.files, 'eps-index.json'), diagnostic: P(E2.files, 'diagnostic-summary.json'), comparison: P(E2.files, 'run-comparison.json'), continuation: P(E2.files, 'continuation-inputs.json') }, sha256)).value;
  assert.equal(DQ.qinputView(r.value, 'operating504', ev2, d).chain, 'BROKEN');
  const cases = [
    ['Q_RESULT_DELIVERY', (x) => { x.index = { result_delivery: { manifest_sha256: 'e'.repeat(64) } }; }],
    ['Q_RESULT_KIND', (x) => { x.index = { historical_system_pit_complete: true }; }],
    ['Q_CLOCKS', (x) => { x.index = { clocks: { valuation_date: '2026-02-02', original_input_cutoff: '', input_cutoff: 'x', reviewed_at: 'x', producer_verified_at: 'x', calculated_at: null } }; }],
    ['Q_SUM', (x) => { x.diag.held1057.gate_diagnostic.DECISION_KNOWN_NOT_NECESSARILY_PASS = 3; }],
    ['Q_SUM', (x) => { x.diag.operating504.official_input_linkage = { PERCENTILE_LINKED: 2 }; }],
    ['Q_COUNT_DISAGREE', (x) => { x.comparison.held1057['U1-333'].stages.Q.after = 1; }],
    ['Q_DATE_MISMATCH', (x) => { x.comparison.operating504['U2-333'].after_bindings.evaluation.as_of = '2026-02-03T00:00:00Z'; }],
    ['CONFIG_VERSION_MISMATCH', (x) => { x.comparison.operating504['S1-333'].after_bindings.model_hash = 'f'.repeat(64); }],
    ['Q_COMPARISON', (x) => { delete x.comparison.held1057['S1-333']; }],
    ['Q_DIAGNOSTIC', (x) => { x.diag.operating504.whole_market_denominator = 501; }],
  ];
  for (const [code, edit] of cases) assert.equal((await run(edit)).code, code, code);
  const p = parts(DF.qinput(E)); p.diagnostic = { bytes: new Uint8Array([...p.diagnostic.bytes, 10]), body: p.diagnostic.body };
  assert.equal((await DQ.checkQinput(p, sha256)).code, 'BYTES_MISMATCH', 'each file is the index\'s bytes');
});
