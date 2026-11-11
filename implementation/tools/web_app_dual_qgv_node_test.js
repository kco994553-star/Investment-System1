'use strict';
// 두 모형 연구 결과 reader (web_app/dual-qgv.js) against Codex #529 46f73a07's synthetic delivery (docs/research/sector_qgv/
// dual-synthetic, pinned in its manifest.json), wrapped as one qgv-dual-delivery/1 scope (web_app_dual_fixture.js). Synthetic only.
//  - accepted only when each file's own bytes match the delivery manifest and the evaluation population is the delivered result
//    (operating504: the evaluation input; held1057: the reference source input); refused otherwise;
//  - U1 / U2 / S1 kept apart: no common scale, no stitched rank, a null total has no total rank; selectable while V / total are null;
//  - nothing recalculated: the stage counts must be the rows as delivered; no raw value in a detail; RAM holds checked deliveries only.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const DQ = require('../src/investment_system/product/web_app/dual-qgv.js');
const F = require('./web_app_dual_fixture.js');
const sha256 = async (b) => crypto.createHash('sha256').update(b).digest('hex');
const part = (d, f) => { const bytes = new Uint8Array(d.files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
const parts = (d) => ({ manifest: part(d, 'manifest.json'), summary: part(d, 'summary.json'), index: part(d, 'index.json') });
const check = (d, scope = d.manifest.scope, anchor = F.anchor()) => DQ.checkDelivery(parts(d), { scope, anchor, sha256 });

test('Codex\'s pinned synthetic bytes are accepted for the result they evaluated, in either scope', async () => {
  assert.equal(F.pinned(), true, 'Codex manifest pins');
  for (const scope of ['operating504', 'held1057']) {
    const r = await check(F.delivery(scope));
    assert.equal(r.ok, true, JSON.stringify(r)); assert.equal(r.value.scope, scope); assert.deepEqual(r.value.models, ['U1', 'U2', 'S1']);
    assert.equal(r.value.rows.length, 3); assert.equal(r.value.data_kind, 'SYNTHETIC'); assert.ok(Object.isFrozen(r.value.summary));
  }
});

test('anchor: another population, day or input is refused; the input side follows the scope; no anchor is refused', async () => {
  const d = F.delivery('operating504'), h = F.delivery('held1057');
  assert.equal((await check(d, 'operating504', F.anchor({ operating: { members_hash: 'a'.repeat(64) } }))).code, 'DUAL_POPULATION_MISMATCH');
  assert.equal((await check(d, 'operating504', F.anchor({ operating: { denominator: 4 } }))).code, 'DUAL_POPULATION_MISMATCH');
  assert.equal((await check(d, 'operating504', F.anchor({ operating: { population_id: 'OTHER' } }))).code, 'DUAL_POPULATION_MISMATCH');
  assert.equal((await check(d, 'operating504', F.anchor({ operating: { valuation_date: '2026-11-04' } }))).code, 'DUAL_DATE_MISMATCH');
  assert.equal((await check(d, 'operating504', F.anchor({ operating: { input_hash: 'b'.repeat(64) } }))).code, 'DUAL_INPUT_MISMATCH');
  // held1057 is tied by its reference source input, not by the evaluation projection's own hash
  const ev = F.parse('summary.json').boards.U1.evaluation_population;
  assert.equal((await check(h, 'held1057', F.anchor({ held_financial_subsample: { input_hash: ev.input_hash } }))).code, 'DUAL_INPUT_MISMATCH');
  assert.equal((await check(d, 'operating504', null)).code, 'ANCHOR_REQUIRED');
  assert.equal((await check(d, 'operating504', { scopes: [] })).code, 'ANCHOR_REQUIRED');
  assert.equal((await DQ.checkDelivery(parts(d), { scope: 'market', anchor: F.anchor(), sha256 })).code, 'SCOPE_UNKNOWN');
});

test('bytes and manifest: each file must be the manifest\'s bytes; the manifest names its scope', async () => {
  const d = F.delivery('operating504'), p = parts(d);
  p.summary = { bytes: new Uint8Array([...p.summary.bytes, 10]), body: p.summary.body };
  assert.equal((await DQ.checkDelivery(p, { scope: 'operating504', anchor: F.anchor(), sha256 })).code, 'BYTES_MISMATCH');
  const q = parts(d); q.index = { body: q.index.body };
  assert.equal((await DQ.checkDelivery(q, { scope: 'operating504', anchor: F.anchor(), sha256 })).code, 'BYTES_REQUIRED');
  assert.equal((await check(d, 'held1057')).code, 'SCOPE_MISMATCH');
  const m = parts(d); m.manifest.body = { ...m.manifest.body, files: m.manifest.body.files.filter((f) => f.path !== 'index.json') };
  assert.equal((await DQ.checkDelivery(m, { scope: 'operating504', anchor: F.anchor(), sha256 })).code, 'FILES_INVALID');
  const n = parts(d); n.manifest.body = { ...n.manifest.body, files: [...n.manifest.body.files, { path: '../coverage.json', size: 1, sha256: 'c'.repeat(64) }] };
  assert.equal((await DQ.checkDelivery(n, { scope: 'operating504', anchor: F.anchor(), sha256 })).code, 'FILES_INVALID');
});

test('refusals: claims, identities, counts, ranks and scopes as written', async () => {
  const B = (f) => (x) => { for (const k of ['U1', 'U2', 'S1']) f(x['summary.json'].boards[k], k, x); };
  const cases = [
    ['SCHEMA', (x) => { x['summary.json'].schema_version = 'qgv-dual-delivery/2'; }],
    ['VISIBILITY', (x) => { x['summary.json'].visibility = 'PUBLIC'; }],
    ['BOARDS_INVALID', (x) => { x['summary.json'].boards.U3 = x['summary.json'].boards.U1; }],
    ['KEY_UNKNOWN', (x) => { x['summary.json'].boards.U1.extra = 1; }],
    ['MODEL_MISMATCH', (x) => { x['summary.json'].boards.U2.model_id = 'unified-roa-core/0.1.0'; }],
    ['ADOPTION_CLAIMED', (x) => { x['summary.json'].boards.S1.operating_adoption = 'ADOPTED'; }],
    ['PERFORMANCE_CLAIMED', (x) => { x['summary.json'].boards.U1.performance_state = 'MEASURED'; }],
    ['BINDINGS_MISMATCH', (x) => { x['summary.json'].boards.U1.bindings.model_hash = 'd'.repeat(64); }],
    ['BINDINGS_MISMATCH', (x) => { x['summary.json'].boards.U1.bindings.reference = { ...x['summary.json'].boards.U1.bindings.reference, code_rows: 99 }; }],
    ['REFERENCE_SCOPE', (x) => { x['summary.json'].boards.U1.reference_population.scope = 'LISTED_MARKET'; }],
    ['REFERENCE_DATE_MISMATCH', (x) => { x['summary.json'].boards.U1.reference_population.valuation_date = '2026-11-01'; }],
    ['EVALUATION_MISMATCH', B((b, k) => { if (k === 'S1') { b.evaluation_population.snapshot_id = 'other'; b.bindings.evaluation.snapshot_id = 'other'; } })],
    ['DENOMINATOR_MISMATCH', (x) => { x['summary.json'].boards.U1.coverage.denominator.code_rows = 4; }],
    ['COUNT_ARITHMETIC', (x) => { x['summary.json'].boards.U1.coverage.gap95.total = { code_rows: 1, issuers: 1 }; }],
    ['COUNT_RANGE', (x) => { x['summary.json'].boards.U1.coverage.stages.Q.issuers = 4; }],
    ['MARKET_NOT_NULL', (x) => { x['summary.json'].boards.U1.coverage.whole_market_denominator = 8004; }],
    ['CAUSES_NOT_OVERLAPPING', (x) => { x['summary.json'].boards.U1.coverage.causes_overlap = false; }],
    ['STAGE_COUNT_MISMATCH', (x) => { x['index.json'].rows[0].boards.U1.axes.Q = null; }],
    ['RANK_WITHOUT_TOTAL', (x) => { x['index.json'].rows[0].boards.U2.total = null; }],
    ['RANK_RANGE', (x) => { x['index.json'].rows[0].boards.U1.rank = 4; }],
    ['RANKING_SCOPE', (x) => { x['index.json'].rows[0].boards.S1.ranking_scope = 'COMMON'; }],
    ['RANKING_SCOPE', (x) => { x['index.json'].rows[0].boards.U1.ranking_scope = 'SECTOR|X|GENERAL'; }],
    ['GATE_UNKNOWN_WITH_TOTAL', (x) => { x['index.json'].rows[0].boards.U1.gate_status = 'UNKNOWN'; }],
    ['ROWS_INVALID', (x) => { x['index.json'].rows[1].company_id = x['index.json'].rows[0].company_id; }],
    ['ROWS_INVALID', (x) => { x['index.json'].rows.pop(); }],
    ['DETAIL_NOT_IN_MANIFEST', (x) => { x['index.json'].rows[0].detail_file = 'detail-001.json'; }],
    ['INDEX_POPULATION_MISMATCH', (x) => { x['index.json'].evaluation_population = { ...x['index.json'].evaluation_population, code_rows: 4 }; }],
  ];
  for (const [code, f] of cases) { const r = await check(F.delivery('operating504', f)); assert.equal(r.code, code, code + ' ' + JSON.stringify(r)); }
});

test('detail: the file\'s rows as the index heads them; no raw value; factor ranks only with a score', async () => {
  const d = F.delivery('operating504'), r = await check(d), v = r.value;
  const ok = await DQ.checkDetail(part(d, 'detail-000.json'), 'detail-000.json', v, sha256);
  assert.equal(ok.ok, true, JSON.stringify(ok)); assert.equal(ok.value.size, 3);
  const mut = async (f) => { const x = F.parse('detail-000.json'); f(x); const bytes = Buffer.from(JSON.stringify(x));
    const e = { ...v.entries, 'detail-000.json': { path: 'detail-000.json', size: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') } };
    return (await DQ.checkDetail({ bytes: new Uint8Array(bytes), body: x }, 'detail-000.json', { ...v, entries: e }, sha256)).code; };
  const f0 = (x) => x.rows[0].boards.S1.factors.operating_margin_ttm;
  assert.equal(await mut((x) => { f0(x).raw_value = 0.1; }), 'RAW_VALUE_PRESENT');
  assert.equal(await mut((x) => { x.rows[0].boards.U1.axes.Q = 1; }), 'DETAIL_MISMATCH');
  assert.equal(await mut((x) => { f0(x).kind = 'ADDITIONAL'; }), 'FACTOR_KIND');
  assert.equal(await mut((x) => { f0(x).score = null; }), 'RANK_WITHOUT_SCORE');
  assert.equal(await mut((x) => { f0(x).decile = 3; }), 'DECILE_INVALID');
  assert.equal(await mut((x) => { x.rows.reverse(); }), 'DETAIL_ROWS_MISMATCH');
  assert.equal(await mut((x) => { x.rows[0].boards.U1.issuer_id = 'other'; }), 'DETAIL_IDENTITY');
  // the delivery's own manifest entry for this file: changed bytes are refused
  const b = part(d, 'detail-000.json'); assert.equal((await DQ.checkDetail({ bytes: new Uint8Array([...b.bytes, 32]), body: b.body }, 'detail-000.json', v, sha256)).code, 'BYTES_MISMATCH');
  assert.equal((await DQ.checkDetail(b, 'detail-001.json', v, sha256)).code, 'NOT_IN_MANIFEST');
});

test('words: each model on its own, ranks only in their scope, null is 미산출 and has no rank, 0 stays 0, no difference', async () => {
  const d = F.delivery('operating504'), v = (await check(d)).value, sn = (id) => (id === 'INFORMATION_TECHNOLOGY' ? '정보기술' : id);
  const u1 = DQ.boardView(v, 'U1');
  assert.equal(u1.head, '통합 연구 U1 · Q ROA · G ROA 개선 · V 이익·장부 · 연구 후보 · 운영 채택 안 됨 · 성과 미측정');
  assert.deepEqual(u1.states.map((s) => s[0]), ['보관 결과 조회', '입력 연결', '최종 총점', '화면 재계산', '저장·재현']);
  assert.equal(v.input_check, 'EVALUATION_INPUT_MATCHED'); assert.match(u1.states[1][1], /^평가 입력 = 지금 받은 결과의 입력/);
  const hv = (await check(F.delivery('held1057'))).value;
  assert.equal(hv.input_check, 'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED', 'a reference input match is not a verified evaluation input');
  assert.match(DQ.boardView(hv, 'U1').states[1][1], /평가 입력 연결 미확인/);
  assert.match(u1.states[3][1], /^연결 안 됨 · 보관 결과만 보임$/);
  assert.match(u1.states[4][1], /^생산자 저장본\(설정·코드·두 입력 결합\)으로만 · 다른 입력이면 거부/);
  assert.equal(u1.stages.find((s) => s.key === 'total').text, '코드 행 3 / 3 · 발행사 3 / 3');
  assert.match(u1.target, /^95% 목표 · 발행사 3 \/ 3 · 코드 행 3 \/ 3 · 세 축 동시 부족 발행사 0 · 최종 총점 부족 발행사 0$/);
  assert.match(u1.market, /전체시장 분모·커버리지 미측정/);
  const rows = DQ.rowsView(v, 'S1', { sectorName: sn });
  assert.deepEqual(rows.map((r) => r.rank), ['3 / 3 (정보기술 · GENERAL)', '2 / 3 (정보기술 · GENERAL)', '1 / 3 (정보기술 · GENERAL)'], 'the producer\'s rank in its scope, rows in delivered order');
  assert.equal(DQ.rowsView(v, 'U1')[0].Q, '0.0', '0 stays 0');
  const n = (await check(F.delivery('operating504', (x) => { const r = x['index.json'].rows[0].boards.U1; r.total = null; r.rank = null; r.axes.V = null;
    const c = x['summary.json'].boards.U1.coverage; c.stages.V = { code_rows: 2, issuers: 2 }; c.stages.joint = { code_rows: 2, issuers: 2 }; c.stages.total = { code_rows: 2, issuers: 2 };
    c.gap95.joint = { code_rows: 1, issuers: 1 }; c.gap95.total = { code_rows: 1, issuers: 1 }; }))).value;
  assert.ok(n, 'a delivery with a null total and its counts is still accepted (selectable while incomplete)');
  const z = DQ.rowsView(n, 'U1')[0]; assert.equal(z.total, '미산출'); assert.equal(z.V, '미산출'); assert.equal(z.rank, '총점 없음 · 순위 없음');
  const det = (await DQ.checkDetail(part(d, 'detail-000.json'), 'detail-000.json', v, sha256)).value;
  const c = DQ.compareView(det.get(v.rows[0].company_id), v, { sectorName: sn });
  assert.equal(c.note, '모형마다 핵심 요소·참조집단·순위 범위가 다름 · 점수 차이를 계산하지 않음');
  assert.deepEqual(c.boards.map((b) => b.key), ['U1', 'U2', 'S1']);
  assert.equal(c.boards[2].core.length, 5); assert.match(c.boards[2].core[0], /^operating_margin_ttm · 점수 0\.0 · 요소 순위 3 \/ 3 · 십분위 없음\(10개 미만\) · 참조 N 20$/);
  assert.ok(c.boards.every((b) => !/차이|평균|합계/.test(b.axes)), 'no difference, average or sum');
  assert.ok(DQ.RULES.some((r) => /총점이 없으면 총점 순위도 없음/.test(r)) && !DQ.RULES.join('').includes('TARGET'));
});

test('RAM: only a checked delivery of that scope; a drop tells the screens', async () => {
  const ram = DQ.ramStore(), v = (await check(F.delivery('operating504'))).value; let told = 0; const un = ram.subscribe(() => { told++; });
  assert.throws(() => ram.set('operating504', { scope: 'operating504', models: ['U1'], rows: [] }), /DUAL_UNCHECKED/);
  assert.throws(() => ram.set('held1057', v), /DUAL_UNCHECKED/, 'another scope\'s delivery');
  ram.set('operating504', v); assert.equal(ram.get('operating504').delivery, v); assert.equal(told, 1);
  ram.drop(); assert.equal(ram.get('operating504'), null); assert.equal(told, 2); ram.drop(); assert.equal(told, 2, 'an empty drop says nothing'); un();
});
