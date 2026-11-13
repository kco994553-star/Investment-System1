'use strict';
// Company relationship reader (web_app/ownership-view.js) against Codex #531's synthetic company-ownership-view/1 cases
// (docs/research/company_ownership/synthetic.json, sha 4946549b…): every producer view reads, the five lists stay apart, the
// states stay apart, nothing is inferred; counterexamples are consumer edits of those views (marked test-made). Synthetic only.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const O = require('../src/investment_system/product/web_app/ownership-view.js');
const FILE = path.join(__dirname, '..', 'docs', 'research', 'company_ownership', 'synthetic.json');
const RAW = fs.readFileSync(FILE);
const X = JSON.parse(RAW.toString('utf8'));
const cases = Object.fromEntries(X.cases.map((c) => [c.case_id, c]));
const copy = (id) => JSON.parse(JSON.stringify(cases[id].expected_view));
const list = (v, key) => v.lists.find((l) => l.key === key).rows;

test('Codex\'s pinned synthetic file: every producer view reads for its own centre; producer errors carry no view', () => {
  assert.equal(crypto.createHash('sha256').update(RAW).digest('hex'), '4946549bd1ff63793a12c04c9d0229e6bbefae14289b27d7947b1594b633e46d');
  let views = 0;
  for (const c of X.cases) {
    if (!c.expected_view) { assert.ok(c.expected_error, c.case_id); continue; }
    const r = O.validate(c.expected_view, { entityId: c.query.entity_id });
    assert.equal(r.ok, true, c.case_id + ' ' + JSON.stringify(r)); views++;
    assert.equal(O.validate(c.expected_view, { entityId: 'SYN-B' }).code, 'CENTRE_MISMATCH', c.case_id);
  }
  assert.equal(views, 15);
});

test('five lists apart: parent / subsidiary / holdings / holders / 13F; percentages never make a parent', () => {
  const v = O.view(O.validate(copy('direct_ownership_and_parent')).value);
  assert.deepEqual(v.lists.map((l) => [l.key, l.rows.length]), [['parents', 0], ['subsidiaries', 1], ['holdings', 1], ['holders', 0], ['discretion', 0]]);
  const hold = list(v, 'holdings')[0];
  assert.equal(hold.share.length, 1); assert.match(hold.share[0].text, /^지분율 약 60%$/); assert.match(hold.share[0].basis, /해당 주식 종류 발행주식 기준 · Class A · 2025-12-31 기준/);
  assert.equal(list(v, 'subsidiaries')[0].percentNote, '지분율 미공개 · 관계는 문서에 명시됨');
  const cv = O.view(O.validate(copy('class_voting_independent')).value), h = list(cv, 'holdings')[0];
  assert.equal(h.share.length + h.voting.length >= 1, true);
  for (const r of cv.lists.flatMap((l) => l.rows)) for (const o of [...r.share, ...r.voting]) assert.match(o.text, /^(지분율|의결권) /, 'share and voting on separate lines');
  const minority = O.view(O.validate(copy('minority_no_control')).value);
  assert.equal(list(minority, 'subsidiaries').length + list(minority, 'parents').length, 0, 'a minority holding is not a parent');
  const zero = list(O.view(O.validate(copy('observed_zero')).value), 'holdings')[0];
  assert.equal(zero.share[0].zero, '0% 관측(보유 아님 · 종료 추정 아님)');
});

test('states apart: none collected / partial n / not found in scope / filter empty / conflict / review / unresolved', () => {
  const state = (id) => O.view(O.validate(copy(id)).value).state;
  assert.deepEqual(state('not_collected'), ['관계 자료 없음 · 수집 전 · 관계가 없다는 뜻이 아님']);
  assert.deepEqual(state('direct_ownership_and_parent'), ['확인된 2개 · 전체 목록 미확인']);
  assert.deepEqual(state('not_found_in_reviewed_scope'), ['검토한 범위에서 찾지 못함 · 관계 없음 확인이 아님']);
  assert.deepEqual(state('filter_empty'), ['고른 종류에 해당 없음 · 다른 종류의 관계는 있음']);
  assert.deepEqual(state('same_basis_conflict'), ['확인된 2개 · 전체 목록 미확인', '자료 충돌 1건 · 값을 고르지 않음']);
  assert.deepEqual(state('open_interval_review_required'), ['확인된 2개 · 전체 목록 미확인', '재검토 필요 2건']);
  const u = O.view(O.validate(copy('unresolved_unlisted_name')).value);
  assert.equal(u.unresolved.length, 1); assert.equal(u.unresolved[0].word, '목록에 없는 대상 · 기업 페이지 없음');
  assert.equal(u.lists.every((l) => l.rows.length === 0), true, 'an unresolved name is not an entity row');
  assert.equal(u.denominator, '전체 관계 수 미상 · 커버리지 계산 안 함');
});

test('consumer-made states (not in the producer set): holders, indirect, 13F, refresh failed, verified zero', () => {
  const v = copy('direct_ownership_and_parent'), own = v.relationships.find((r) => r.type === 'OWNERSHIP');
  // Holders: the same fact read from the investee's side (SYN-B): one relationship_id, INCOMING.
  const b = JSON.parse(JSON.stringify(v));
  b.entity_context = { entity_id: 'SYN-B', node_id: 'issuer:SYN-B' };
  b.relationships = b.relationships.filter((r) => r.relationship_id === own.relationship_id).map((r) => ({ ...r, relative_direction: 'INCOMING' }));
  b.counts = { ...b.counts, filtered_relationships: 1, relationships: 1 };
  const rb = O.validate(b, { entityId: 'SYN-B' }); assert.equal(rb.ok, true, JSON.stringify(rb));
  assert.equal(list(O.view(rb.value), 'holders')[0].relationship_id, own.relationship_id);
  assert.deepEqual(O.sameFact(O.validate(v).value, rb.value), [{ relationship_id: own.relationship_id, consistent: true }], 'both sides read the same id');
  // Indirect and 13F discretion.
  const i = copy('direct_ownership_and_parent'); i.relationships.find((r) => r.type === 'OWNERSHIP').directness = 'INDIRECT';
  assert.equal(list(O.view(O.validate(i).value), 'holdings')[0].directness, '간접');
  const f = copy('direct_ownership_and_parent'), fr = f.relationships.find((r) => r.type === 'OWNERSHIP');
  fr.capacity = 'INVESTMENT_DISCRETION'; fr.assertions.forEach((a) => { a.capacity = 'INVESTMENT_DISCRETION'; });
  const fv = O.view(O.validate(f).value);
  assert.equal(list(fv, 'discretion').length, 1); assert.equal(list(fv, 'holdings').length, 0, '13F is never own equity');
  // Refresh failed (previous good data shown) and a confirmed none in the reviewed scope.
  const r = copy('direct_ownership_and_parent'); r.collection = { ...r.collection, last_failure: { code: 'FETCH_FAILED', at: '2026-01-06T12:00:00Z' } };
  assert.match(O.view(O.validate(r).value).state[1], /^마지막 갱신 실패 · 이전에 성공한 자료를 보임/);
  const z = copy('not_found_in_reviewed_scope'); z.collection_state = 'VERIFIED_ZERO_IN_SCOPE';
  assert.deepEqual(O.view(O.validate(z).value).state, ['검토한 범위에서 관계 없음 확인 · 그 범위 밖은 모름']);
});

test('refused: claims the contract forbids, or a view that is not about this centre', () => {
  const bad = (id, edit, code) => { const v = copy(id); edit(v); assert.equal(O.validate(v).code, code, code); };
  bad('direct_ownership_and_parent', (v) => { v.relationship_denominator = 10; }, 'COVERAGE_CLAIMED');
  bad('direct_ownership_and_parent', (v) => { v.historical_system_pit = true; }, 'PIT_CLAIMED');
  bad('direct_ownership_and_parent', (v) => { v.collection_state = 'COMPLETE'; }, 'COLLECTION_STATE');
  bad('direct_ownership_and_parent', (v) => { v.relationships[0].relative_direction = 'INCOMING'; }, 'RELATIVE_DIRECTION');
  bad('explicit_path_duplicate_cycle', (v) => { const r = v.relationships.find((x) => x.relative_direction === 'INCOMING'); r.target_entity_id = 'SYN-C'; r.assertions.forEach((a) => { a.target_entity_id = 'SYN-C'; }); }, 'ENTITY');
  bad('direct_ownership_and_parent', (v) => { v.relationships[1].relationship_id = v.relationships[0].relationship_id; }, 'RELATIONSHIP_ID');
  bad('explicit_path_duplicate_cycle', (v) => { v.confirmed_paths[0].economic_ownership_percent = '48'; }, 'LOOK_THROUGH');
  bad('direct_ownership_and_parent', (v) => { v.counts.filtered_relationships = 3; }, 'COUNTS');
  bad('not_collected', (v) => { v.relationships = copy('minority_no_control').relationships; v.counts.filtered_relationships = 1; v.counts.relationships = 1; v.entities = copy('minority_no_control').entities; v.counts.legal_entities = 2; }, 'COLLECTION_STATE');
  bad('direct_ownership_and_parent', (v) => { v.relationships.find((r) => r.type === 'OWNERSHIP').observations[0].value = '101'; }, 'DECIMAL');
  bad('direct_ownership_and_parent', (v) => { v.relationships.find((r) => r.type === 'OWNERSHIP').observations[0].value = 60; }, 'DECIMAL');
  bad('direct_ownership_and_parent', (v) => { v.relationships.find((r) => r.type === 'PARENT_SUBSIDIARY').positive_ownership = true; }, 'CONTROL_FROM_PERCENT');
  bad('direct_ownership_and_parent', (v) => { const r = v.relationships.find((x) => x.type === 'PARENT_SUBSIDIARY'); r.capacity = 'INVESTMENT_DISCRETION'; }, '13F_CAPACITY');
  bad('unresolved_unlisted_name', (v) => { v.mentions[0].mention_id = 'SYN-A'; }, 'MENTION');
  bad('direct_ownership_and_parent', (v) => { v.relationships[0].observations[0] = { ...v.relationships[0].observations[0], raw_value: 0.6 }; }, 'KEY_UNEXPECTED');
});

test('RAM: only checked views; found by the centre\'s code row; a drop tells the screens', () => {
  const v = O.validate(copy('direct_ownership_and_parent')).value;
  assert.throws(() => O.ram.put(copy('direct_ownership_and_parent')), /OWNERSHIP_VIEW_NOT_CHECKED/);
  let told = 0; const off = O.ram.subscribe(() => { told++; });
  O.ram.put(v); assert.equal(O.ram.forCompany('SYN:A'), v); assert.equal(O.ram.forCompany('SYN:B'), null, 'SYN:B is not the centre of this view');
  O.ram.clear(); assert.equal(O.ram.forCompany('SYN:A'), null); assert.equal(told, 2); off();
});

// Codex #531 b53b0ec0: twelve producer-made consumer cases (consumer-synthetic.json, sha 213d8ce0…), each with its expected view and
// byte hash, and three separate refresh-attempt receipts bound to their retained view.
const CX = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'research', 'company_ownership', 'consumer-synthetic.json'), 'utf8'));
const cx = Object.fromEntries(CX.cases.map((c) => [c.case_id, c]));
const sha256 = async (b) => crypto.createHash('sha256').update(b).digest('hex');
const canon = (x) => Array.isArray(x) ? '[' + x.map(canon).join(',') + ']' : x !== null && typeof x === 'object' ? '{' + Object.keys(x).sort().map((k) => JSON.stringify(k) + ':' + canon(x[k])).join(',') + '}' : JSON.stringify(x);

test('Codex\'s twelve consumer cases: pinned; every view reads for its centre with the producer\'s byte hash; lists as expected', () => {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, '..', 'docs', 'research', 'company_ownership', 'consumer-synthetic.json'))).digest('hex'), '213d8ce0f40ea02e42df945cabfe10e391193ccf45c06b0bb893a4be17774f1a');
  assert.equal(CX.cases.length, 12);
  for (const c of CX.cases) {
    const r = O.validate(c.expected_view, { entityId: c.query.entity_id }); assert.equal(r.ok, true, c.case_id + ' ' + JSON.stringify(r));
    assert.equal(crypto.createHash('sha256').update(canon(c.expected_view) + '\n').digest('hex'), c.expected_view_sha256, c.case_id + ': the producer\'s view bytes');
  }
  const counts = (id) => Object.fromEntries(O.view(O.validate(cx[id].expected_view).value).lists.map((l) => [l.key, l.rows.length]));
  assert.deepEqual([counts('incoming_holder').holders, counts('incoming_holder').parents], [1, 1], 'read from the investee side');
  assert.equal(counts('indirect_ownership').holdings, 1); assert.equal(counts('13f_investment_discretion').discretion, 1);
  assert.equal(counts('13f_investment_discretion').holdings + counts('13f_investment_discretion').subsidiaries, 0, '13F is never own equity or control');
  const ind = O.view(O.validate(cx.indirect_ownership.expected_view).value).lists.find((l) => l.key === 'holdings').rows[0];
  assert.equal(ind.directness, '간접');
});

test('scope state and evidence state apart: REVIEWED_SCOPE read; a not-reviewed centre keeps the incoming relationships others confirm', () => {
  const rs = O.view(O.validate(cx.reviewed_scope.expected_view).value);
  assert.equal(rs.scopeState, '검토한 범위는 검토 완료 · 그 범위 밖은 모름 · 전체 관계 완결 아님');
  const nc = O.view(O.validate(cx.incoming_centre_not_reviewed.expected_view).value);
  assert.equal(nc.scopeState, '이 기업 자체 검토 전 · 관계가 없다는 뜻이 아님');
  assert.match(nc.evidenceState, /^다른 기업 근거로 확인된 관계 2개\(이 기업을 향한 관계\)$/);
  assert.ok(nc.lists.flatMap((l) => l.rows).every((r) => r.relative === 'INCOMING'));
  assert.deepEqual(O.view(O.validate(cx.not_collected.expected_view).value).state, ['관계 자료 없음 · 수집 전 · 관계가 없다는 뜻이 아님'], 'not collected and nothing delivered');
  assert.equal(O.view(O.validate(cx.verified_zero_in_scope.expected_view).value).scopeState, '검토한 범위에서 관계 없음 확인 · 그 범위 밖은 모름');
  // Still refused: a not-reviewed centre stating its own (outgoing) relationship.
  const out = JSON.parse(JSON.stringify(cx.incoming_centre_not_reviewed.expected_view)); out.relationships[0].relative_direction = 'OUTGOING';
  assert.ok(['COLLECTION_STATE', 'RELATIVE_DIRECTION'].includes(O.validate(out).code));
});

test('refresh receipts: bound to the retained view bytes and times; shown beside the view; the view itself unchanged', async () => {
  for (const [id, word] of [['refresh_failed', '실패'], ['refresh_partial', '일부만 성공'], ['refresh_parse_failed', '해석 실패']]) {
    const c = cx[id], v = O.validate(c.expected_view).value, r = await O.checkReceipt(c.refresh, v, sha256);
    assert.equal(r.ok, true, id + ' ' + JSON.stringify(r));
    const w = O.view(v, { receipt: r.value });
    assert.equal(w.refresh, '마지막 갱신 시도 ' + word + ' · 시도 ' + c.refresh.attempt.attempted_at + ' · 이전에 성공한 자료를 보임(성공 ' + c.refresh.unchanged_last_success_at + ' · 생성 ' + c.refresh.unchanged_generated_at + ')');
    assert.equal(v.collection.last_failure, null, 'the producer\'s view keeps last_failure null'); assert.equal(v.generated_at, c.refresh.unchanged_generated_at);
    assert.equal(O.view(v).refresh, null, 'no receipt, no refresh line (not a success either)');
  }
  const c = cx.refresh_failed, v = O.validate(c.expected_view).value, other = O.validate(cx.reviewed_scope.expected_view).value;
  assert.equal((await O.checkReceipt(c.refresh, other, sha256)).code, 'RECEIPT_VIEW_MISMATCH', 'a receipt for another view');
  assert.equal((await O.checkReceipt({ ...c.refresh, unchanged_generated_at: '2026-01-06T00:00:00Z' }, v, sha256)).code, 'RECEIPT_VIEW_MISMATCH', 'a changed time');
  assert.equal((await O.checkReceipt({ ...c.refresh, attempt: { ...c.refresh.attempt, outcome: 'TIMEOUT' } }, v, sha256)).code, 'RECEIPT_OUTCOME');
  assert.equal((await O.checkReceipt({ ...c.refresh, attempt: { ...c.refresh.attempt, attempted_at: '2026-01-01T00:00:00Z' } }, v, sha256)).code, 'RECEIPT_TIME');
  assert.throws(() => O.ram.put(v, { ...c.refresh }), /OWNERSHIP_RECEIPT_NOT_CHECKED/);
  const r = (await O.checkReceipt(c.refresh, v, sha256)).value; O.ram.put(v, r); assert.equal(O.ram.receiptFor(v), r); O.ram.clear();
});

// The authenticated delivery (owner 2026-11-13): Main's index (company-ownership-delivery/1, stage_private_ownership_view.py) names each
// staged view's and receipt's size and SHA-256; a view is taken only with exactly those bytes, for that centre, company ids and dataset.
test('authenticated delivery: index → view bytes → receipt; damaged, missing, unlisted or another centre\'s files refused', async () => {
  const enc = (x) => new Uint8Array(Buffer.from(canon(x) + '\n')), file = (x, bytes) => ({ bytes: bytes || enc(x), body: x });
  const shaHex = (b) => crypto.createHash('sha256').update(b).digest('hex');
  const a = cx.refresh_failed, b = cx.incoming_holder, av = enc(a.expected_view), bv = enc(b.expected_view), rb = new Uint8Array(Buffer.from(JSON.stringify(a.refresh, null, 2) + '\n'));
  const entry = (c, v, r) => ({ entity_id: c.expected_view.entity_context.entity_id, company_ids: c.expected_view.entities.find((e) => e.entity_id === c.expected_view.entity_context.entity_id).company_ids,
    dataset_hash: c.expected_view.dataset_hash, view: { size: v.length, sha256: shaHex(v) }, receipt: r ? { size: r.length, sha256: shaHex(r) } : null });
  const idx = { schema_version: 'company-ownership-delivery/1', data_kind: 'SYNTHETIC', sources: [{ handoff_path: 'handoffs/x', handoff_manifest_sha256: 'a'.repeat(64) }], new_external_requests: 0,
    views: [entry(a, av, rb), entry(b, bv, null)] };
  const I = O.checkDeliveryIndex({ body: idx }); assert.equal(I.ok, true, JSON.stringify(I));
  assert.equal(shaHex(av), a.expected_view_sha256, 'the producer\'s view bytes');
  const ea = O.entryFor(I.value, 'SYN:A2'), eb = O.entryFor(I.value, 'SYN:B');
  assert.equal(ea.entity_id, 'SYN-A'); assert.equal(eb.entity_id, 'SYN-B'); assert.equal(O.entryFor(I.value, 'NYSE:MMM'), null, 'a company the index does not list');
  const ok = await O.checkDelivered(I.value, ea, file(a.expected_view, av), file(a.refresh, rb), sha256);
  assert.equal(ok.ok, true, JSON.stringify(ok)); assert.equal(ok.value.receiptRefused, null); assert.equal(ok.value.dataKind, 'SYNTHETIC');
  assert.match(O.view(ok.value.view, { receipt: ok.value.receipt }).refresh, /^마지막 갱신 시도 실패 · 시도 /, 'the refresh failure beside the retained view');
  assert.equal(ok.value.view.generated_at, a.refresh.unchanged_generated_at, 'the view\'s own time unchanged');
  const nb = await O.checkDelivered(I.value, eb, file(b.expected_view, bv), null, sha256); assert.equal(nb.ok, true); assert.equal(nb.value.receipt, null);
  const dmg = av.slice(); dmg[20] ^= 1;
  assert.equal((await O.checkDelivered(I.value, ea, file(a.expected_view, dmg), file(a.refresh, rb), sha256)).code, 'FILE_MISMATCH', 'damaged view bytes');
  assert.equal((await O.checkDelivered(I.value, ea, null, file(a.refresh, rb), sha256)).code, 'VIEW_MISSING');
  assert.equal((await O.checkDelivered(I.value, ea, file(a.expected_view, av), null, sha256)).code, 'RECEIPT_MISSING', 'a listed receipt missing');
  assert.equal((await O.checkDelivered(I.value, eb, file(b.expected_view, bv), file(a.refresh, rb), sha256)).code, 'RECEIPT_UNLISTED');
  const rd = rb.slice(); rd[5] ^= 1; assert.equal((await O.checkDelivered(I.value, ea, file(a.expected_view, av), file(a.refresh, rd), sha256)).code, 'FILE_MISMATCH', 'damaged receipt bytes');
  assert.equal((await O.checkDelivered(I.value, ea, file(b.expected_view, bv), file(a.refresh, rb), sha256)).code, 'FILE_MISMATCH', 'another view\'s file under this entity');
  // An index entry whose bytes match but whose company ids / dataset are not the view's.
  const alt = { ...idx, views: [{ ...entry(a, av, rb), company_ids: ['SYN:A'] }] }, I2 = O.checkDeliveryIndex({ body: alt }).value;
  assert.equal((await O.checkDelivered(I2, I2.views[0], file(a.expected_view, av), file(a.refresh, rb), sha256)).code, 'INDEX_COMPANY_MISMATCH');
  const alt2 = { ...idx, views: [{ ...entry(a, av, rb), dataset_hash: 'f'.repeat(64) }] }, I3 = O.checkDeliveryIndex({ body: alt2 }).value;
  assert.equal((await O.checkDelivered(I3, I3.views[0], file(a.expected_view, av), file(a.refresh, rb), sha256)).code, 'INDEX_DATASET_MISMATCH');
  // A receipt that is listed and intact but not bound to this view's times: the view is kept, without a refresh line, and says why.
  const badR = { ...a.refresh, attempt: { ...a.refresh.attempt, attempted_at: '2000-01-01T00:00:00Z' } }, br = new Uint8Array(Buffer.from(JSON.stringify(badR)));
  const alt3 = { ...idx, views: [entry(a, av, br)] }, I4 = O.checkDeliveryIndex({ body: alt3 }).value;
  const kept = await O.checkDelivered(I4, I4.views[0], file(a.expected_view, av), file(badR, br), sha256);
  assert.equal(kept.ok, true); assert.equal(kept.value.receipt, null); assert.equal(kept.value.receiptRefused, 'RECEIPT_TIME');
  // Index refusals.
  const bad = (edit) => { const x = JSON.parse(JSON.stringify(idx)); edit(x); return O.checkDeliveryIndex({ body: x }).code; };
  assert.equal(bad((x) => { x.schema_version = 'company-ownership-delivery/2'; }), 'SCHEMA');
  assert.equal(bad((x) => { x.data_kind = 'PUBLIC'; }), 'DATA_KIND');
  assert.equal(bad((x) => { x.new_external_requests = 1; }), 'NOT_PROJECTION');
  assert.equal(bad((x) => { x.views[1].entity_id = 'SYN-A'; }), 'INDEX_DUPLICATE', 'two views for one centre');
  assert.equal(bad((x) => { x.views[1].company_ids = ['SYN:A']; }), 'INDEX_DUPLICATE', 'one company in two views');
  assert.equal(bad((x) => { x.views[0].view.sha256 = 'XYZ'; }), 'TYPE');
  assert.equal(bad((x) => { x.views[0].note = 1; }), 'KEY_UNEXPECTED');
  assert.equal(bad((x) => { x.views = []; }), 'TYPE');
  assert.equal((await O.checkDelivered(idx, ea, file(a.expected_view, av), null, sha256)).code, 'INDEX_NOT_CHECKED', 'an index the reader did not check');
});

// Codex #437 6848164775 counterexamples (raw 77f9d153 handoffs/main-final-acceptance-20261113/receipt-boundaries.js), ported: a
// receipt names its retained dataset (= the view's dataset_hash), is bound to the one view it was checked against (RAM and display),
// and its attempt is an instant with a time and an explicit zone.
test('receipt boundaries: dataset hash, binding to its own view (RAM and display), instant with time and zone', async () => {
  const c = cx.refresh_failed, v = O.validate(c.expected_view).value, other = O.validate(cx.reviewed_scope.expected_view).value;
  const normal = await O.checkReceipt(c.refresh, v, sha256); assert.equal(normal.ok, true); assert.equal(c.refresh.retained_dataset_sha256, v.dataset_hash);
  assert.equal((await O.checkReceipt({ ...c.refresh, retained_dataset_sha256: '0'.repeat(64) }, v, sha256)).code, 'RECEIPT_DATASET_MISMATCH');
  assert.throws(() => O.ram.put(other, normal.value), /OWNERSHIP_RECEIPT_NOT_BOUND/, 'a receipt checked for one view is not kept with another');
  assert.equal(O.view(other, { receipt: normal.value }).refresh, null, 'nor shown beside another view');
  assert.match(O.view(v, { receipt: normal.value }).refresh, /^마지막 갱신 시도 실패/, 'shown beside its own view');
  for (const at of ['2026-01-06', '2026-01-06T12:00:00', '2026-01-06 12:00:00Z', '2026-01-06T12Z'])
    assert.equal((await O.checkReceipt({ ...c.refresh, attempt: { ...c.refresh.attempt, attempted_at: at } }, v, sha256)).code, 'RECEIPT_TIME', at);
  for (const at of ['2026-01-06T12:00:00Z', '2026-01-06T12:00:00.5+09:00', '2026-01-06T12:00Z'])
    assert.equal((await O.checkReceipt({ ...c.refresh, attempt: { ...c.refresh.attempt, attempted_at: at } }, v, sha256)).ok, true, at);
  O.ram.put(v, normal.value); assert.equal(O.ram.receiptFor(v), normal.value); O.ram.clear();
});
