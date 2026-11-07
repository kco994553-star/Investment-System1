'use strict';
// 4.5 정책·지정학 reader (web_app/policy-impact.js, owner 2026-11-07) against Codex's policy-impact-view/1 output (#509 e0bb68dd):
// the shared synthetic view and state cases (SHA-256 pinned as handed over on #437) and the Main variants made by Codex's own
// build (tools/policy_impact_main_variants.py). The reader must take the engine's current revision, order, REVIEW_REQUIRED and
// review_due as delivered and never compute them; refusal cases name the code of the first fault.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const P = require('../src/investment_system/product/web_app/policy-impact.js');
const X = require('./web_app_policy_impact_fixture.js');

let n = 0;
const ok = (name, fn) => { fn(); n++; console.log('PASS ' + name); };
const accept = (v) => { const r = P.validate(v); assert.equal(r.ok, true, JSON.stringify(r)); return P.view(r.value); };
const refused = (fn, code, pathPart = null, base) => { const r = P.validate(X.edit(fn, base)); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); if (pathPart) assert.ok(r.path.includes(pathPart), r.path); };
const VAR = X.variants();
const AT = String.fromCharCode(64); // a credentials-in-URL case, built at run time (no address-like text in the file)

ok('Codex files: the four pinned SHA-256 of #437; the contract names the same envelope, record keys and enums as the reader', () => {
  for (const [name, [file, want]] of Object.entries(X.FILES)) assert.equal(X.sha(file), want, name);
  const c = X.contract();
  assert.equal(c.view_schema, P.VIEW_SCHEMA); assert.equal(c.schema_version, P.SCHEMA);
  for (const [k, list] of Object.entries(c.enums)) { const mine = P.ENUMS[k === 'kind' ? 'kind' : k]; assert.deepEqual([...mine].sort(), [...list].sort(), k); }
  assert.deepEqual(c.effects, { score_effect: 'NONE', gate_effect: 'NONE' }); assert.equal(c.historical_pit_eligible, false);
});
ok('synthetic-view.json and every expected view of synthetic-states.json are accepted whole; counts and current revisions as delivered', () => {
  const v = accept(X.codexView());
  assert.deepEqual(v.order.map((p) => p.policy_id + '@' + p.current.revision_id), ['p0@1', 'p1@1', 'p2@1']);
  assert.equal(v.data_kind, 'SYNTHETIC'); assert.equal(v.historical, false); assert.equal(v.freshness.review_due, false);
  for (const s of X.states()) {
    const w = accept(s.expected), b = s.expected.bundle;
    assert.equal(w.order.length, Object.keys(s.expected.current_policy_revisions).length, s.name);
    assert.equal([...w.policies.values()].reduce((a, p) => a + p.exposures.length, 0), b.exposures.length, s.name);
    assert.equal(w.sources.size, b.sources.length, s.name);
  }
  const names = X.states().map((s) => s.name); assert.deepEqual(names, ['EMPTY', 'FUTURE_SOURCE', 'UNVERIFIED_SOURCE', 'MISSING_RATIO']);
  const empty = accept(X.states()[0].expected); assert.equal(empty.order.length, 0); assert.equal(empty.freshness.review_due, null);
  const future = accept(X.states()[1].expected); assert.deepEqual(future.order.map((p) => p.policy_id), ['p1', 'p2'], 'the future source and what depends on it are absent: not filtered here');
});
ok('no revision is chosen here: the current revision is the one current_policy_revisions names, even against change times', () => {
  const v = accept(VAR.REVISED);
  const p0 = v.policies.get('p0'); assert.equal(p0.current.revision_id, '2'); assert.deepEqual(p0.older.map((r) => r.revision_id), ['1']);
  assert.deepEqual(v.order.map((p) => p.policy_id), ['unit-exception', 'p0', 'p1', 'p2'], 'the engine order');
  // the same file naming revision 1: the reader follows the file (its rows on revision 1 are REVIEW_REQUIRED, allowed anywhere)
  const w = accept(X.edit((x) => { x.current_policy_revisions.p0 = '1'; }, VAR.REVISED));
  assert.equal(w.policies.get('p0').current.revision_id, '1'); assert.deepEqual(w.policies.get('p0').older.map((r) => r.revision_id), ['2']);
  assert.equal(P.get(v, 'p0', '1').shown.revision_id, '1'); assert.equal(P.get(v, 'p0', '9'), null); assert.equal(P.get(v, 'nope'), null);
  assert.deepEqual(v.policies.get('p0').children, ['unit-exception']); assert.equal(v.policies.get('unit-exception').parent, 'p0');
  assert.equal(P.status(v, v.policies.get('unit-exception').current).text, '유예');
});
ok('review states as delivered: REVIEW_REQUIRED stays apart from the current judgment; a REVIEWED row on an older revision is refused', () => {
  const v = accept(VAR.REVISED), p0 = v.policies.get('p0');
  assert.deepEqual(p0.hypotheses.map((x) => x.review_status), ['REVIEW_REQUIRED']); assert.deepEqual(p0.exposures.map((x) => x.review_status), ['REVIEW_REQUIRED']);
  const s = P.forCompany(v, 'synthetic-company-0'); assert.equal(s.old, 1); assert.equal(s.documented + s.confirm, 0);
  // the engine may mark a row on the current revision REVIEW_REQUIRED too; the reader never turns it back
  const w = accept(X.edit((x) => { x.bundle.hypotheses[1].review_status = 'REVIEW_REQUIRED'; }, VAR.REVISED));
  assert.equal(w.policies.get('p1').hypotheses[0].review_status, 'REVIEW_REQUIRED');
  refused((x) => { x.bundle.hypotheses[0].review_status = 'REVIEWED'; }, 'STALE_NOT_FLAGGED', 'hypotheses[0]', VAR.REVISED);
  refused((x) => { x.bundle.exposures[0].review_status = 'REVIEWED'; }, 'STALE_NOT_FLAGGED', 'exposures[0]', VAR.REVISED);
});
ok('historical cases: 역사 사례 · 현재 상태 미확인 for all three; tariff and export control readable with no exposure; FINAL_AWARD is not a disbursement', () => {
  const v = accept(VAR.HISTORICAL);
  assert.equal(v.historical, true);
  for (const p of v.order) assert.equal(P.status(v, p.current).text, '역사 사례 · 현재 상태 미확인', p.policy_id);
  assert.deepEqual(v.order.map((p) => [p.current.policy_type, p.exposures.length, p.hypotheses.length]), [['TARIFF', 0, 0], ['EXPORT_CONTROL', 0, 0], ['INDUSTRIAL_SUBSIDY', 1, 1]]);
  const sub = v.order[2].current; assert.equal(sub.subsidy_stage, 'FINAL_AWARD');
  assert.ok(P.text(P.STAGE_TEXT, 'FINAL_AWARD').includes('실제 지급 아님')); assert.ok(!P.text(P.STAGE_TEXT, 'FINAL_AWARD').includes('지급 확인'));
  const e = v.order[2].exposures[0]; assert.equal(e.ratio, null); assert.deepEqual(e.reason_codes, ['RATIO_NOT_APPLICABLE', 'CURRENT_DISBURSEMENT_UNCONFIRMED']);
  assert.equal(v.freshness.review_due, null, 'no next review date: null, not false');
  assert.equal(P.forCompany(v, 'synthetic-company-0'), null, 'no link is "no policy known", the screen says 연결 근거 미확인');
  // without the bundle reason an UNKNOWN status is just 현재 상태 미확인 (never 영향 없음 / 시행 중)
  const w = accept(X.edit((x) => { x.bundle.reason_codes = []; }, VAR.HISTORICAL)); assert.equal(P.status(w, w.order[0].current).text, '현재 상태 미확인');
});
ok('list, facets and the company summary read present values only; filters keep the engine order; 0 results stay 0', () => {
  const v = accept(X.codexView());
  assert.deepEqual(P.facets(v).type, ['EXPORT_CONTROL', 'INDUSTRIAL_SUBSIDY', 'TARIFF']); assert.deepEqual(P.facets(v).company, ['synthetic-company-0', 'synthetic-company-1', 'synthetic-company-2']);
  assert.deepEqual(P.list(v, { type: 'TARIFF' }).map((p) => p.policy_id), ['p0']);
  assert.deepEqual(P.list(v, { company: 'synthetic-company-1' }).map((p) => p.policy_id), ['p1']);
  assert.deepEqual(P.list(v, { type: 'TARIFF', company: 'synthetic-company-1' }), []);
  const s = P.forCompany(v, 'synthetic-company-0');
  assert.deepEqual(s, { policies: [{ policy_id: 'p0', title: '합성 TARIFF', type: 'TARIFF' }], documented: 0, confirm: 1, old: 0, last_reviewed_at: '2026-11-07T00:00:00Z' }, 'documented region revenue with applicability UNCONFIRMED is 확인 필요');
});
ok('sources by (source_id, revision); review records with method; news references (5.2 → 4.5) from the NEWS variant only', () => {
  const v = accept(VAR.NEWS);
  const p0 = v.policies.get('p0'); const step = p0.hypotheses[0].steps[0].evidence_refs[0];
  const s = P.source(v, step); assert.equal(s.kind, 'NEWS_REFERENCE'); assert.equal(s.verification_status, 'SOURCE_UNVERIFIED');
  assert.equal(s.published.precision, 'UNKNOWN', 'first seen is never publication'); assert.equal(s.first_seen_at, '2026-11-06T12:00:00Z');
  assert.deepEqual([...P.newsLinks(v)], [['https://wire.example.org/nvda-revenue', ['p0']]]);
  assert.deepEqual([...P.newsLinks(accept(X.codexView()))], [], 'the public synthetic view has no news reference');
  const rs = P.reviewsOf(v, 'policies', 'p0', '1'); assert.equal(rs.length, 1); assert.equal(rs[0].method, 'AI_INDEPENDENT_SOURCE_CHECK');
  assert.ok(P.text(P.METHOD_TEXT, 'AI_INDEPENDENT_SOURCE_CHECK').includes('사람 검토 아님'));
});
ok('titles, availability and related articles: an id-only title says so; unknown availability is not public; a news reference is not evidence', () => {
  const v = accept(X.codexView()), p = v.order[0].current;
  assert.deepEqual(P.titleState(p), { state: 'TITLE', text: null });
  assert.equal(P.titleState({ ...p, title: p.policy_id }).state, 'ID_ONLY');
  assert.ok(P.titleState({ ...p, title: p.policy_id }).text.includes('공식 정책 제목·한국어 설명 제목 미제공'));
  assert.equal(P.availability('PUBLIC_REFERENCE').known, true); assert.equal(P.availability('UNAVAILABLE').known, true);
  const u = P.availability('MAYBE'); assert.equal(u.known, false); assert.ok(u.text.includes('확인 안 된 이용 상태'));
  assert.ok(P.text(P.KIND_TEXT, 'NEWS_REFERENCE').includes('정책 검증 근거 아님'));
  assert.ok(!/title|similar|levenshtein|includes\(\s*s\.title/i.test(String(P.newsLinks)), 'news links come from the file, never from title matching');
});
ok('links: reserved test domains (RFC 2606 / 6761) are never links; real https without credentials is; a synthetic file with a real link is refused', () => {
  for (const u of ['https://example.invalid/s0', 'https://wire.example.org/a', 'https://news.example.com/b', 'https://x.test/c', 'https://localhost/d', 'http://www.federalregister.gov/x', 'javascript:alert(1)', 'https://u:p' + AT + 'www.nist.gov/'])
    assert.equal(P.linkable(u), false, u);
  for (const u of ['https://www.federalregister.gov/documents/2024/09/18/2024-21217/x', 'https://www.nist.gov/news-events/news/2024/12/x']) assert.equal(P.linkable(u), true, u);
  refused((x) => { x.bundle.sources[0].url = 'https://www.federalregister.gov/d/1'; }, 'SYNTHETIC_REAL_LINK', 'sources[0].url');
  refused((x) => { x.bundle.sources[0].url = 'http://example.invalid/s0'; }, 'UNSAFE_URL');
  refused((x) => { x.bundle.sources[0].url = 'https://a:b' + AT + 'example.invalid/s0'; }, 'UNSAFE_URL');
});
ok('refusals: the whole file at its first fault, with Codex contract codes where Codex has them', () => {
  const C = [
    [(x) => { x.schema_version = 'policy-impact-view/2'; }, 'VIEW_VERSION'], [(x) => { x.extra = 1; }, 'KEY_UNKNOWN'], [(x) => { delete x.as_of; }, 'KEY_MISSING'],
    [(x) => { x.historical_pit_eligible = true; }, 'PIT_UNPROVEN'], [(x) => { x.bundle.historical_pit_eligible = true; }, 'PIT_UNPROVEN'],
    [(x) => { x.as_of = '2026-11-07T09:00:00+09:00'; }, 'UTC_REQUIRED'], [(x) => { x.query_timezone = '../etc'; }, 'TIMEZONE'],
    [(x) => { x.bundle.schema_version = 'policy-impact/2'; }, 'VERSION'], [(x) => { x.bundle.score_effect = 'RANK'; }, 'FORBIDDEN_EFFECT'], [(x) => { x.bundle.gate_effect = 'GATE'; }, 'FORBIDDEN_EFFECT'],
    [(x) => { x.bundle.private_note = 'x'; }, 'KEY_UNKNOWN'], [(x) => { x.bundle.policies[0].notes = []; }, 'KEY_UNKNOWN'], [(x) => { x.bundle.scope.coverage_kind = 'FULL_MARKET'; }, 'COVERAGE'],
    [(x) => { x.bundle.reason_codes = [{ secret: 1 }]; }, 'TEXT'], [(x) => { x.bundle.policies[0].target_regions = [{ x: 1 }]; }, 'TEXT'],
    [(x) => { delete x.current_policy_revisions.p1; }, 'CURRENT_REF'], [(x) => { x.current_policy_revisions.p1 = '7'; }, 'CURRENT_REF'], [(x) => { x.current_policy_revisions.ghost = '1'; }, 'CURRENT_REF'],
    [(x) => { x.bundle.policies[0].review_status = 'UNREVIEWED'; }, 'UNREVIEWED_PUBLIC'], [(x) => { x.bundle.exposures[0].evidence_status = 'CANDIDATE'; }, 'CANDIDATE_PUBLIC'],
    [(x) => { x.bundle.hypotheses[0].review_status = 'UNREVIEWED'; }, 'UNREVIEWED_PUBLIC'],
    [(x) => { x.bundle.policies[0].lifecycle_status = 'ACTIVE'; }, 'ENUM'], [(x) => { x.bundle.policies[0].data_kind = 'REAL_REVIEWED'; }, 'MIXED_KIND'],
    [(x) => { x.bundle.policies.push(JSON.parse(JSON.stringify(x.bundle.policies[0]))); }, 'DUPLICATE_REVISION'],
    [(x) => { x.bundle.policies[0].evidence_refs[0].source_id = 'ghost'; }, 'SOURCE_REF'], [(x) => { x.bundle.policies[0].evidence_refs = []; }, 'EMPTY'],
    [(x) => { x.bundle.policies[0].supersedes_revision_id = '0'; }, 'REVISION_REF'], [(x) => { x.bundle.policies[0].parent_policy_id = 'ghost'; }, 'PARENT_REF'],
    [(x) => { x.bundle.policies[0].identity_basis.issuer = 'OTHER'; }, 'UNSTABLE_POLICY_ID'], [(x) => { x.bundle.policies[2].subsidy_stage = null; }, 'SUBSIDY_STAGE'],
    [(x) => { x.bundle.policies[0].subsidy_stage = 'FINAL_AWARD'; }, 'SUBSIDY_STAGE'],
    [(x) => { x.bundle.policies[0].published = { value: '2026-11-01', precision: 'DATE', timezone: 'UTC' }; }, 'DATE_TIMEZONE'],
    [(x) => { x.bundle.policies[0].effective_to = { value: '2026-12-01', precision: 'UNKNOWN', timezone: null }; }, 'PRECISION'],
    [(x) => { x.bundle.policies[0].published = { value: '2026-02-30', precision: 'DATE', timezone: null }; }, 'DATE'],
    [(x) => { x.bundle.policies[0].recorded_at = '2026-11-07 00:00:00'; }, 'TIME'],
    [(x) => { x.bundle.sources[0].content_sha256 = 'ab'; }, 'SOURCE_HASH'], [(x) => { x.bundle.sources[0].acquired_at = '2026-11-08T00:00:00Z'; }, 'SOURCE_TIME_ORDER'],
    [(x) => { x.bundle.exposures[0].reason_codes = []; }, 'NULL_REASON'],
    [(x) => { x.bundle.exposures[0].ratio = { value: 1.5, unit: 'fraction', denominator_description: 'd', period: x.bundle.exposures[0].period, scope: 's' }; }, 'RATIO'],
    [(x) => { x.bundle.exposures[0].ratio = { value: 0.2, unit: 'percent', denominator_description: 'd', period: x.bundle.exposures[0].period, scope: 's' }; }, 'RATIO'],
    [(x) => { x.bundle.exposures[0].ratio = { value: 0.2, unit: 'fraction', denominator_description: 'd', period: { start: null, end: null }, scope: 's' }; }, 'RATIO_SCOPE'],
    [(x) => { x.bundle.exposures[0].policy_revision_id = '9'; }, 'POLICY_REF'],
    [(x) => { x.bundle.hypotheses[0].exposure_refs[0].exposure_id = 'e1'; }, 'EXPOSURE_REF'], [(x) => { x.bundle.hypotheses[0].counter_conditions = []; }, 'EMPTY'],
    [(x) => { x.bundle.hypotheses[0].steps[0].epistemic_status = 'SUPPORTED_FACT'; }, 'EMPTY'], [(x) => { x.bundle.hypotheses[0].watch_items[0].kind = 'PRICE'; }, 'ENUM'],
    [(x) => { x.bundle.review_records[0].reviewer = x.bundle.review_records[0].author; }, 'INDEPENDENT_REVIEW'],
    [(x) => { x.bundle.review_records[0].method = 'SELF_CHECK'; }, 'ENUM'], [(x) => { x.bundle.review_records[0].id = 'ghost'; }, 'REVIEW_REF'],
    [(x) => { x.bundle.refresh.result = 'UPDATED'; }, 'MANUAL_NOT_AUTO'],
    [(x) => { Object.assign(x.bundle.refresh, { mode: 'AUTOMATED', result: 'INCOMPLETE' }); }, 'INCOMPLETE_RANGE'],
    [(x) => { x.bundle.freshness.review_due = 'no'; }, 'BOOLEAN'],
  ];
  for (const [fn, code] of C) refused(fn, code);
  assert.equal(P.validate('{}').ok, false); assert.equal(P.validate(null).ok, false); assert.equal(P.validate(X.codexView().bundle).code, 'KEY_MISSING', 'a bare bundle is not the envelope');
});
ok('an identity mutation inside one policy id is refused (issuer / type / jurisdiction kept across revisions)', () => {
  refused((x) => { const p = x.bundle.policies.find((r) => r.policy_id === 'p0' && r.revision_id === '1'); p.jurisdiction = 'US_STATE'; }, 'POLICY_IDENTITY_MUTATION', null, VAR.REVISED);
});
ok('the reader is pure and decides nothing: no request, storage, clock, sort by time, score or rank in its source', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app', 'policy-impact.js'), 'utf8');
  for (const bad of [/\bfetch\(/, /localStorage|sessionStorage|indexedDB/, /Date\.now\(|new Date\(\)/, /XMLHttpRequest/, /\.sort\(\s*\(\s*a\s*,\s*b\s*\)\s*=>[^)]*(change_recorded_at|reviewed_at|recorded_at)/, /\bscore\s*[+*]=|\brank\s*=(?!=)/])
    assert.ok(!bad.test(src), String(bad));
  const screen = fs.readFileSync(path.join(__dirname, '..', 'src', 'investment_system', 'product', 'web_app', 'screen-policy-impact-live.js'), 'utf8');
  for (const bad of [/\bfetch\(/, /localStorage|sessionStorage/, /new Date\(\)|Date\.now\(/, /supersedes_revision_id\s*[!=]==/, /policy_revision_id\s*[!=]==\s*\w+\.current/]) assert.ok(!bad.test(screen), 'screen: ' + bad);
  const v = accept(X.codexView()); assert.ok(Object.isFrozen(P.validate(X.codexView()).value.bundle.policies[0]));
  assert.equal(v.order[0].current.lifecycle_status, 'ADOPTED', 'effective_from 2026-11-02 before as_of does not make it EFFECTIVE');
});
console.log('ok ' + n + ' checks');
