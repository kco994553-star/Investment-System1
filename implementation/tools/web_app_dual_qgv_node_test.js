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
  assert.equal(c.boards[2].core.length, 5); assert.match(c.boards[2].core[0], /^operating_margin_ttm · 점수 0\.0 · 분위 없음\(평가 유효 10개 미만\) · 요소 순위 3 \/ 평가 유효 3 · 참조 N 20 · 비교집단 정보기술 · GENERAL · 평가일 \d{4}-\d{2}-\d{2}$/);
  assert.match(c.boards[0].core[0], / · 비교집단 평가 집단 전체 · /, 'U1 factors are ranked in the integrated group');
  // A board without a total still shows each scored factor's band in its own group (test-made row: total null, decile 7).
  const t = JSON.parse(JSON.stringify(det.get(v.rows[0].company_id))), tb = t.boards.S1, tv = tb.selected_variants[0];
  tb.total = null; tb.rank = null; Object.assign(tb.factors[tv], { score: 61.5, rank: 40, rank_n: 130, decile: 7, decile_status: 'VALID' });
  const tc = DQ.compareView(t, v, { sectorName: sn }).boards[2];
  assert.equal(tc.rank, '총점 없음 · 순위 없음');
  assert.match(tc.core[0], /^operating_margin_ttm · 점수 61\.5 · 상위 30–40%\(분위 7\) · 요소 순위 40 \/ 평가 유효 130 · /);
  assert.ok(c.bandRule.some((x) => /^분위 숫자 10 = 상위 0–10% · 1 = 상위 90–100%/.test(x)) && c.bandRule.some((x) => /섹터 분위를 합친 통합 분위 없음/.test(x)));
  assert.ok(c.boards.every((b) => !/차이|평균|합계/.test(b.axes)), 'no difference, average or sum');
  assert.ok(DQ.RULES.some((r) => /총점이 없으면 총점 순위도 없음/.test(r)) && !DQ.RULES.join('').includes('TARGET'));
});

test('operating504 reference input: anchored only by a matching independent anchor; a mismatching anchor refuses; none = not compared', async () => {
  const d = F.delivery('operating504'), anc = (edit) => { const bytes = new Uint8Array(F.referenceAnchor(edit)); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const run = (a) => DQ.checkDelivery({ ...parts(d), ...(a ? { reference_anchor: a } : {}) }, { scope: 'operating504', anchor: F.anchor(), sha256 });
  assert.equal((await run()).value.input_check, 'EVALUATION_INPUT_MATCHED', 'no anchor: the reference side is not compared');
  assert.match(DQ.INPUT_WORD.EVALUATION_INPUT_MATCHED, /참조 입력은 독립 기준과 대조 안 됨$/);
  const ok = await run(anc()); assert.equal(ok.ok, true, JSON.stringify(ok)); assert.equal(ok.value.input_check, 'EVALUATION_INPUT_MATCHED_REFERENCE_ANCHORED');
  assert.match(DQ.INPUT_WORD.EVALUATION_INPUT_MATCHED_REFERENCE_ANCHORED, /참조 입력 = 생산자 독립 기준/);
  assert.equal((await run(anc((x) => { x.expected_reference.input_hash = 'f'.repeat(64); }))).code, 'REFERENCE_ANCHOR_MISMATCH', 'another reference input');
  assert.equal((await run(anc((x) => { x.expected_reference.members_hash = 'f'.repeat(64); }))).code, 'REFERENCE_ANCHOR_MISMATCH', 'another reference membership');
  assert.equal((await run(anc((x) => { x.expected_reference.code_rows += 1; x.candidate_rows += 1; }))).code, 'REFERENCE_ANCHOR_MISMATCH');
  assert.equal((await run(anc((x) => { x.matches_all_dual_boards = false; }))).code, 'REFERENCE_ANCHOR_INVALID');
  assert.equal((await run(anc((x) => { x.new_score_calculations = 1; }))).code, 'REFERENCE_ANCHOR_INVALID');
  assert.equal((await run(anc((x) => { x.scope = 'held1057'; }))).code, 'SCOPE_MISMATCH');
  assert.equal((await run(anc((x) => { x.extra = 1; }))).code, 'KEY_UNKNOWN');
  // The delivery whose reference binding was changed consistently (Codex binding case) is now refused when an anchor is staged.
  const moved = F.delivery('operating504', (docs) => { for (const b of Object.values(docs['summary.json'].boards)) { b.bindings.reference.input_hash = 'e'.repeat(64); b.reference_population.input_hash = 'e'.repeat(64); b.reference_population.candidate_population.input_hash = 'e'.repeat(64); } });
  const r = await DQ.checkDelivery({ ...parts(moved), reference_anchor: anc() }, { scope: 'operating504', anchor: F.anchor(), sha256 });
  assert.equal(r.code, 'REFERENCE_ANCHOR_MISMATCH', JSON.stringify(r));
  const h = F.delivery('held1057');
  assert.equal((await DQ.checkDelivery({ ...parts(h), reference_anchor: anc((x) => { x.scope = 'held1057'; }) }, { scope: 'held1057', anchor: F.anchor(), sha256 })).code, 'REFERENCE_ANCHOR_NOT_APPLICABLE');
});

test('held1057 evaluation input: attested only by a matching projection proof; a mismatching proof refuses; none = unverified', async () => {
  const h = F.delivery('held1057'), lin = (edit) => { const bytes = new Uint8Array(F.lineage(edit)); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const go = (l, d = h, scope = 'held1057') => DQ.checkDelivery({ ...parts(d), lineage: l }, { scope, anchor: F.anchor(), sha256 });
  assert.equal((await go(undefined)).value.input_check, 'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED');
  const ok = await go(lin()); assert.equal(ok.ok, true, JSON.stringify(ok)); assert.equal(ok.value.input_check, 'EVALUATION_INPUT_PROJECTION_ATTESTED');
  assert.match(DQ.boardView(ok.value, 'U1').states[1][1], /생산자 투영 증명과 대조됨/);
  for (const [code, edit] of [
    ['LINEAGE_SCHEMA', (x) => { x.schema_version = 'other/1'; }],
    ['LINEAGE_MISMATCH', (x) => { x.evaluation = { ...x.evaluation, members_hash: 'e'.repeat(64) }; }],
    ['LINEAGE_MISMATCH', (x) => { x.reference_source = { ...x.reference_source, input_hash: 'e'.repeat(64) }; }],
    ['LINEAGE_INVALID', (x) => { x.selected_issuer_count = 2; }],
    ['LINEAGE_INVALID', (x) => { x.row_values_or_classification_changed = true; }],
    ['LINEAGE_INVALID', (x) => { x.changed_top_level_fields.push('classification'); }],
    ['LINEAGE_INVALID', (x) => { x.whole_market_denominator = 8004; }],
    ['LINEAGE_INVALID', (x) => { x.new_score_calculations = 1; }]]) assert.equal((await go(lin(edit))).code, code, code);
  assert.equal((await go(lin(), F.delivery('operating504'), 'operating504')).code, 'LINEAGE_NOT_APPLICABLE', 'operating504 needs no proof and takes none');
});

test('preset fields: present on every row with a preset, absent exactly on MAPPING_UNRESOLVED; never optional', async () => {
  const d = F.delivery('operating504'), v = (await check(d)).value;
  const mut = async (f) => { const x = F.parse('detail-000.json'); f(x); const bytes = Buffer.from(JSON.stringify(x));
    const e = { ...v.entries, 'detail-000.json': { path: 'detail-000.json', size: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') } };
    return (await DQ.checkDetail({ bytes: new Uint8Array(bytes), body: x }, 'detail-000.json', { ...v, entries: e }, sha256)).code; };
  assert.equal(await mut((x) => { delete x.rows[0].boards.U1.nominal_axis_weights; }), 'PRESET_FIELD_MISSING');
  assert.equal(await mut((x) => { delete x.rows[1].boards.S1.missing_factors; }), 'PRESET_FIELD_MISSING');
});

test('Codex binding cases (dual-delivery-binding-cases.json): expectations from the pinned inputs, never from the delivery', async () => {
  const C = JSON.parse(require('node:fs').readFileSync(require('node:path').join(F.D, '..', 'dual-delivery-binding-cases.json'), 'utf8'));
  const patch = (c) => (x) => { for (const p of c.patches) { const doc = x[p[0] + '.json']; let o = doc; for (const k of p.slice(1, -2)) o = o[k]; o[p[p.length - 2]] = p[p.length - 1]; } };
  const proof = () => { const bytes = new Uint8Array(F.lineage((x) => { x.evaluation = C.expected_evaluation; x.reference_source = C.expected_reference; }));
    return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const run = (scope, c, l) => { const d = F.delivery(scope, c.patches.length ? patch(c) : undefined); return DQ.checkDelivery({ ...parts(d), ...(l ? { lineage: l } : {}) }, { scope, anchor: F.anchor(), sha256 }); };
  const got = {};
  for (const c of C.cases) got[c.id] = { op: await run('operating504', c), held: await run('held1057', c, proof()), bare: await run('held1057', c) };
  assert.equal(got.normal.op.ok, true); assert.equal(got.normal.held.value.input_check, 'EVALUATION_INPUT_PROJECTION_ATTESTED', 'held: both bindings by the trusted proof');
  assert.equal(got.evaluation_hash_mismatch.op.code, 'DUAL_INPUT_MISMATCH', 'operating504: the staged result anchors the evaluation input');
  assert.equal(got.evaluation_hash_mismatch.held.code, 'LINEAGE_MISMATCH', 'held1057: the trusted proof refuses the changed evaluation input');
  assert.equal(got.evaluation_hash_mismatch.bare.value.input_check, 'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED', 'no proof: unverified, never attested');
  assert.equal(got.reference_hash_mismatch.held.code, 'DUAL_INPUT_MISMATCH');
  // operating504 has no independent reference anchor in the staged bundle: not refused on that side, and the screen says so.
  assert.equal(got.reference_hash_mismatch.op.value.input_check, 'EVALUATION_INPUT_MATCHED');
  assert.match(DQ.INPUT_WORD.EVALUATION_INPUT_MATCHED, /참조 입력은 독립 기준과 대조 안 됨/);
});

test('factor leaders: Codex\'s synthetic companion reads for its own delivery only; stored ranks as delivered, nothing re-sorted', async () => {
  const lp = (L, f) => { const bytes = new Uint8Array(L.files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const open = async (d, L) => { const v = (await check(d)).value; return DQ.checkLeaders({ manifest: lp(L, 'factor-leaders-manifest.json'), index: lp(L, 'factor-leaders.json') }, v, sha256); };
  const d = F.delivery('operating504'), L = F.leaders(d), r = await open(d, L);
  assert.equal(r.ok, true, JSON.stringify(r)); assert.equal(r.value.groups.length, 153);
  assert.deepEqual([...new Set(r.value.groups.map((g) => g.board))], ['S1', 'U1', 'U2']);
  const s = await DQ.checkLeaderShard(lp(L, 'factor-leaders-000.json'), 'factor-leaders-000.json', r.value, sha256);
  assert.equal(s.ok, true, JSON.stringify(s)); assert.equal(s.value.size, 153);
  const g = [...s.value.values()].find((x) => x.leaders.length > 1), v = DQ.leaderView(g);
  assert.deepEqual(v.rows.map((x) => x.rank), g.leaders.map((x, i) => (i + 1) + ' / ' + g.evaluation_valid_n), 'the stored order');
  assert.match(v.d10, /^평가 유효 \d+개 < 10 · 분위 계산 안 함$/); assert.deepEqual(v.bands, [], 'no bands below N 10'); assert.match(v.counts, /참조 유효 \d+\(순위 분모 아님\)/);
  assert.equal(DQ.leaderView([...s.value.values()].find((x) => x.evaluation_valid_n === 0)).d10, '유효 점수 없음 · 순위 없음');
  // Not this delivery: another delivery's manifest, another board identity, not a projection.
  const h = F.delivery('held1057');
  assert.equal((await open(h, L)).code, 'SCOPE_MISMATCH', 'operating504 leaders on held1057');
  assert.equal((await open(F.delivery('operating504', () => {}), L)).code, 'LEADERS_SOURCE_MISMATCH', 'the same content under another delivery manifest');
  assert.equal((await open(h, F.leaders(h))).ok, true, 'a companion re-pointed at held1057 reads there');
  assert.equal((await open(d, F.leaders(d, (x) => { x['factor-leaders.json'].boards.U1.result_hash = 'a'.repeat(64); }))).code, 'LEADERS_BOARD_MISMATCH');
  assert.equal((await open(d, F.leaders(d, (x) => { x['factor-leaders.json'].rank_recalculated = true; }))).code, 'NOT_PROJECTION');
  assert.equal((await open(d, F.leaders(d, (x) => { x['factor-leaders.json'].whole_market_denominator = 8004; }))).code, 'NOT_PROJECTION');
  assert.equal((await open(d, F.leaders(d, (x) => { x['factor-leaders.json'].groups[0].evaluation_valid_n = 4; }))).code, 'TYPE', 'N above the evaluation code rows');
  assert.equal((await open(d, F.leaders(d, (x) => { x['factor-leaders.json'].groups[1].group_id = x['factor-leaders.json'].groups[0].group_id; }))).code, 'GROUPS_INVALID');
  // A shard: each group as indexed, the stored prefix 1..min(N, top_n), the decile state from N, no raw value.
  const shard = async (edit) => { const E = F.leaders(d, edit), o = await open(d, E); assert.equal(o.ok, true, JSON.stringify(o));
    return (await DQ.checkLeaderShard(lp(E, 'factor-leaders-000.json'), 'factor-leaders-000.json', o.value, sha256)).code; };
  const first = (x) => x['factor-leaders-000.json'].groups.find((z) => z.leaders.length > 1);
  assert.equal(await shard((x) => { const z = first(x); z.leaders = z.leaders.slice(1); }), 'LEADER_PREFIX', 'a missing rank 1');
  assert.equal(await shard((x) => { const z = first(x); [z.leaders[0], z.leaders[1]] = [z.leaders[1], z.leaders[0]]; }), 'LEADER_PREFIX', 'a re-sorted list');
  assert.equal(await shard((x) => { first(x).leaders[0].raw_value = 0.1; }), 'RAW_VALUE_PRESENT');
  assert.equal(await shard((x) => { first(x).decile_status = 'VALID'; }), 'DECILE_STATUS', 'N < 10 is never VALID');
  assert.equal(await shard((x) => { first(x).leaders[0].decile = 10; }), 'DECILE_STATUS', 'no decile below N 10');
  assert.equal(await shard((x) => { first(x).reference_valid_n += 1; }), 'GROUP_CONTEXT');
  assert.equal(await shard((x) => { x['factor-leaders-000.json'].groups.pop(); }), 'GROUPS_MISMATCH');
  assert.equal((await DQ.checkLeaders({}, { scope: 'operating504' }, sha256)).code, 'DELIVERY_NOT_CHECKED');
  // The D10 line compares the stored D10 boundary with the list length (display only; checked against the real files locally).
  // Test-made group (display only): N 250, ten stored boundaries of 25 ranks each, a top-20 preview.
  const valid = { board: 'S1', ranking_scope: 'SECTOR|X|GENERAL', variant_id: 'v', evaluation_valid_n: 250, evaluation_rows_in_scope: 260, reference_valid_n: 900, top_n: 20, decile_status: 'VALID',
    decile_boundaries: Array.from({ length: 10 }, (_, j) => ({ decile: 10 - j, count: 25, first_rank: 25 * j + 1, last_rank: 25 * j + 25, first_score: 100 - 10 * j, last_score: 91 - 10 * j })),
    leaders: Array.from({ length: 20 }, (_, i) => ({ company_id: 'c' + i, rank: i + 1, rank_n: 250, score: 99 - i, decile: 10, kind: 'CORE' })) };
  const vv = DQ.leaderView(valid);
  assert.equal(vv.d10, '저장된 상위 0–10% 구간 25개(순위 1–25) · 이 목록 20개 · 이 구간 일부만(상위 20개 표시 한도)');
  assert.match(vv.preview, /^상위 20개 미리보기 · 10분위 전체 조회가 아님/);
  assert.deepEqual(vv.bands.map((b) => b.band), ['상위 0–10%', '상위 10–20%', '상위 20–30%', '상위 30–40%', '상위 40–50%', '상위 50–60%', '상위 60–70%', '상위 70–80%', '상위 80–90%', '상위 90–100%']);
  assert.deepEqual([vv.bands[0].ranks, vv.bands[0].scores, vv.bands[0].members], ['순위 1–25 / 250', '요소 점수 100.0–91.0', '구성 기업 25개 중 이 미리보기에 20개 · 전체 구성 목록은 분할 전달 대기']);
  assert.deepEqual([vv.bands[9].decile, vv.bands[9].ranks, vv.bands[9].shown, vv.bands[9].complete], [1, '순위 226–250 / 250', 0, false]);
  assert.equal(vv.rows[0].decile, '상위 0–10%'); assert.equal(vv.rows[0].d, 10);
  assert.equal(DQ.BAND[1], '상위 90–100%'); assert.equal(DQ.bandText({ decile: null, decile_status: 'SAMPLE_LT_10' }), '분위 없음(평가 유효 10개 미만)');
});

test('selection contract: Codex\'s synthetic chain checks; it pins these leaders; top N and the stored D10 stay apart', async () => {
  const lp = (X, f) => { const bytes = new Uint8Array(X.files[f]); return { bytes, body: JSON.parse(Buffer.from(bytes).toString('utf8')) }; };
  const d = F.delivery('operating504'), v = (await check(d)).value, L = F.leaders(d);
  const lv = (await DQ.checkLeaders({ manifest: lp(L, 'factor-leaders-manifest.json'), index: lp(L, 'factor-leaders.json') }, v, sha256)).value;
  const sel = (S, leaders = lv) => DQ.checkSelection({ manifest: lp(S, 'factor-leaders-selection-manifest.json'), body: lp(S, 'factor-leaders-selection.json') }, leaders, sha256);
  const r = await sel(F.selection(L)); assert.equal(r.ok, true, JSON.stringify(r)); assert.equal(r.value.groups.size, 153);
  const shard = (await DQ.checkLeaderShard(lp(L, 'factor-leaders-000.json'), 'factor-leaders-000.json', lv, sha256)).value;
  for (const g of shard.values()) assert.equal(DQ.selectionMatchesShard(r.value.groups.get(g.group_id), g), true, g.group_id);
  const g = [...shard.values()].find((x) => x.leaders.length > 1);
  assert.match(DQ.leaderView(g, { selection: r.value.groups.get(g.group_id) }).sel, /^생산자 선택 계약과 대조됨/);
  assert.match(DQ.leaderView(g).sel, /^생산자 선택 계약 없음/);
  // Not these leaders, not a projection, a group that is not the leaders', a top-10 % that breaks the contract rule.
  const h = F.delivery('held1057'), hv = (await check(h)).value, HL = F.leaders(h);
  const hlv = (await DQ.checkLeaders({ manifest: lp(HL, 'factor-leaders-manifest.json'), index: lp(HL, 'factor-leaders.json') }, hv, sha256)).value;
  assert.equal((await sel(F.selection(L), hlv)).code, 'SCOPE_MISMATCH');
  assert.equal((await sel(F.selection(HL), hlv)).ok, true, 're-pointed at held1057 leaders');
  assert.equal((await sel(F.selection(L, (x) => { x.rank_recalculated = true; }))).code, 'NOT_PROJECTION');
  assert.equal((await sel(F.selection(L, (x) => { x.groups.pop(); }))).code, 'GROUPS_MISMATCH');
  assert.equal((await sel(F.selection(L, (x) => { x.groups[0].evaluation_valid_n += 1; }))).code, 'GROUP_CONTEXT');
  assert.equal((await sel(F.selection(L, (x) => { x.groups[0].top_10_percent.status = 'VALID'; }))).code, 'DECILE_STATUS');
  assert.equal((await sel(F.selection(L, (x) => { x.groups[0].top_10_percent.complete_in_top_n = true; }))).code, 'TOP_DECILE_BOUNDARY');
  assert.equal((await sel(F.selection(L, (x) => { x.source_delivery_manifest_sha256 = 'a'.repeat(64); }))).code, 'SELECTION_SOURCE_MISMATCH');
  // A selection entry that disagrees with the loaded shard is shown as a disagreement, never as the list.
  const e = JSON.parse(JSON.stringify(r.value.groups.get(g.group_id))); e.top_n.returned_n += 1;
  assert.equal(DQ.selectionMatchesShard(e, g), false); assert.equal(DQ.leaderView(g, { selection: e }).selectionOk, false);
});

test('RAM: only a checked delivery of that scope; a drop tells the screens', async () => {
  const ram = DQ.ramStore(), v = (await check(F.delivery('operating504'))).value; let told = 0; const un = ram.subscribe(() => { told++; });
  assert.throws(() => ram.set('operating504', { scope: 'operating504', models: ['U1'], rows: [] }), /DUAL_UNCHECKED/);
  assert.throws(() => ram.set('held1057', v), /DUAL_UNCHECKED/, 'another scope\'s delivery');
  ram.set('operating504', v); assert.equal(ram.get('operating504').delivery, v); assert.equal(told, 1);
  ram.drop(); assert.equal(ram.get('operating504'), null); assert.equal(told, 2); ram.drop(); assert.equal(told, 2, 'an empty drop says nothing'); un();
});

// The research engine route (owner 2026-11-11 §3): requests name model and candidate; an answer is used only for that very request.
test('engine answers: the same request, model and candidate; board of that candidate; no rank without a total; saved records', async () => {
  const E = require('./web_app_sector_qgv_engine.js'), eng = E.start({ env: {} });
  try {
    const U1 = 'unified-roa-core/0.1.0', S1 = 'sector-reduced-core/0.1.0';
    assert.throws(() => DQ.engineRequest('preview', 'unknown/0.1.0'), /MODEL_ID_UNKNOWN/);
    assert.throws(() => DQ.engineRequest('comparisons', U1), /DUAL_OP_UNKNOWN/);
    const q = DQ.engineRequest('preview', U1, { input_id: 'DUAL_BOTH_VALID' });
    assert.equal(q.model, 'INTEGRATED'); assert.equal(q.model_id, U1); assert.match(q.request_id, /^DUAL-preview-U1-\d+$/);
    const a = await eng.call(q), ok = DQ.checkAnswer(q, a);
    assert.equal(ok.ok, true, JSON.stringify(ok.code));
    // The pinned synthetic result was made at #529's code. Its configuration and both input identities are bound unchanged and every
    // row's axes, total, rank and status are the pinned ones; the code binding is the current code's, and the result hash moves exactly
    // with it (#534 changed dual_qgv.py for config/2: an exact old replay is at its original execution commit, Codex QGV_333.md).
    const pin = F.parse('summary.json').boards.U1, bd = ok.value.board;
    for (const k of ['model_hash', 'evaluation', 'reference', 'engine_version', 'adapter_version']) assert.deepEqual(bd.bindings[k], pin.bindings[k], 'bindings.' + k);
    assert.equal(bd.result_hash === pin.result_hash, bd.bindings.code_hash === pin.bindings.code_hash, 'the result hash moves exactly with the code binding');
    const pinRows = new Map(F.parse('index.json').rows.map((r) => [r.company_id, r.boards.U1]));
    assert.equal(bd.rows.length, pinRows.size);
    for (const r of bd.rows) for (const k of ['axes', 'total', 'rank', 'rank_n', 'ranking_scope', 'status', 'gate_status']) assert.deepEqual(r[k], pinRows.get(r.company_id)[k], r.company_id + '.' + k);
    // the answer to another request, or under another model, is never used
    assert.equal(DQ.checkAnswer({ ...q, request_id: 'DUAL-preview-U1-0' }, a).code, 'ENGINE_ANSWER_OTHER_REQUEST');
    assert.equal(DQ.checkAnswer({ ...q, model_id: 'unified-sales-core/0.1.0' }, a).code, 'MODEL_RESPONSE_MISMATCH');
    const forged = JSON.parse(JSON.stringify(a)); forged.board.model_id = S1;
    assert.equal(DQ.checkAnswer(q, forged).code, 'MODEL_RESPONSE_MISMATCH');
    const ranked = JSON.parse(JSON.stringify(a)); ranked.board.rows[0].total = null;
    assert.equal(DQ.checkAnswer(q, ranked).code, 'RANK_WITHOUT_TOTAL');
    // Q/G only: shown, no total, no rank
    const g = DQ.engineRequest('preview', S1, { input_id: 'DUAL_QG_ONLY' }), ga = DQ.checkAnswer(g, await eng.call(g));
    assert.equal(ga.ok, true); const rows = DQ.boardRowsView(ga.value.board);
    assert.ok(rows.every((r) => r.Q !== '미산출' && r.total === '미산출' && r.rank === '총점 없음 · 순위 없음'));
    // save → a valid qgv-dual-saved/1 for that candidate; replay of it is the same result
    const s = DQ.engineRequest('save', U1, { result_hash: ok.value.board.result_hash }), sa = DQ.checkAnswer(s, await eng.call(s));
    assert.equal(sa.ok, true); assert.equal(DQ.validateSaved(sa.value.saved).ok, true);
    const r = DQ.engineRequest('replay', U1, { saved: sa.value.saved }), ra = DQ.checkAnswer(r, await eng.call(r));
    assert.equal(ra.ok, true); assert.equal(ra.value.kind, 'EXACT_REPLAY');
    // an engine refusal stays the engine's code
    const u = DQ.engineRequest('replay', U1, { saved: { schema_version: 'sector-qgv-saved/1' } });
    assert.equal(DQ.checkAnswer(u, await eng.call(u)).code, 'SAVED_SCHEMA_MISMATCH');
    assert.equal(DQ.validateSaved({ schema_version: 'sector-qgv-saved/1' }).code, 'KEY_MISSING');
  } finally { eng.close(); }
});
