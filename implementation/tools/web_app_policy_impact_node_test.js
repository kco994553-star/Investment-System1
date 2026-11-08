'use strict';
// 4.5 정책·지정학 reader (web_app/policy-impact.js, owner 2026-11-07) against Codex's policy-impact-view/1 and /2 output (#509 c2ae92a0):
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
// Test helper: each fixture is read on the delivery path it was built for (Codex public build -> PUBLIC; the retained v1 files
// and private builds -> PRIVATE_DEV). The screen never derives the path from the version: the file name it read decides.
const pathOf = (v) => (v && v.schema_version === P.PUBLIC_VIEW ? 'PUBLIC' : 'PRIVATE_DEV');
const V = (v, delivery = pathOf(v)) => P.validate(v, { delivery });
const accept = (v) => { const r = V(v); assert.equal(r.ok, true, JSON.stringify(r)); return P.view(r.value); };
const refused = (fn, code, pathPart = null, base) => { const r = V(X.edit(fn, base)); assert.equal(r.ok, false, code); assert.equal(r.code, code, JSON.stringify(r)); if (pathPart) assert.ok(r.path.includes(pathPart), r.path); };
const VAR = X.variants();
const AT = String.fromCharCode(64); // a credentials-in-URL case, built at run time (no address-like text in the file)

ok('Codex files: the seven pinned SHA-256 of #437; the contract names the same envelopes, record keys and enums as the reader', () => {
  for (const [name, [file, want]] of Object.entries(X.FILES)) assert.equal(X.sha(file), want, name);
  const c = X.contract();
  assert.equal(c.view_schema, P.VIEW_SCHEMA); assert.equal(c.view_schema, P.PUBLIC_VIEW); assert.equal(c.private_view_schema, P.PRIVATE_VIEW); assert.equal(c.schema_version, P.SCHEMA);
  assert.equal(c.navigation_sidecar, P.NAV_SCHEMA); assert.deepEqual(Object.keys(c.watch_availability).sort(), [...P.ENUMS.availability].sort());
  assert.deepEqual([...c.watch_publication_permissions.allowed].sort(), [...P.ENUMS.publication_permission].sort());
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
ok('titles, availability, related articles and delivery paths: an id-only title says so; UNKNOWN is not public; a news reference is not evidence; the path fixes the version', () => {
  const v = accept(X.codexView()), p = v.order[0].current;
  assert.deepEqual(P.titleState(p), { state: 'TITLE', text: null });
  assert.equal(P.availability('UNKNOWN').known, false); assert.ok(P.availability('UNKNOWN').text.includes('공개 허가 아님'));
  assert.ok(P.availability('PUBLIC_REFERENCE').text.includes('공개 허가와 별개'));
  assert.equal(P.titleState({ ...p, title: p.policy_id }).state, 'ID_ONLY');
  assert.ok(P.titleState({ ...p, title: p.policy_id }).text.includes('공식 정책 제목·한국어 설명 제목 미제공'));
  assert.equal(P.availability('PUBLIC_REFERENCE').known, true); assert.equal(P.availability('UNAVAILABLE').known, true);
  const u = P.availability('MAYBE'); assert.equal(u.known, false); assert.ok(u.text.includes('확인 안 된 이용 상태'));
  // the contract's three values only (Codex contract.py WATCH_AVAILABILITY): another value refuses the file
  refused((x) => { x.bundle.hypotheses[0].watch_items[0].availability = 'MAYBE'; }, 'ENUM', 'availability');
  assert.equal(V(X.edit((x) => { x.bundle.hypotheses[0].watch_items[0].availability = 'UNKNOWN'; })).ok, true, 'a private (v1) view keeps UNKNOWN');
  // public view/2: a watch item is there only as PUBLIC_REFERENCE with an explicit permission (build-side); never UNKNOWN / UNAVAILABLE
  const v2 = X.publicV2(); assert.equal(V(v2).ok, true); assert.equal(accept(v2).public, true); assert.equal(accept(X.codexView()).public, false);
  assert.ok(v2.bundle.hypotheses.every((h) => h.watch_items.length === 0), 'no permission given: no public watch item');
  const leak = X.edit((x) => { x.bundle.hypotheses[0].watch_items = [{ kind: 'POLICY_UPDATE', reference_id: 'p0', rationale: 'r', availability: 'UNKNOWN' }]; }, v2);
  assert.equal(V(leak).code, 'WATCH_NOT_PUBLIC');
  // delivery paths: the path fixes the version; neither version is read as the other, and the path must be named
  assert.equal(P.validate(v2, { delivery: 'PRIVATE_DEV' }).code, 'VIEW_DELIVERY_MISMATCH', 'a public view/2 is not taken as private output');
  assert.equal(P.validate(X.codexView(), { delivery: 'PUBLIC' }).code, 'VIEW_DELIVERY_MISMATCH', 'a retained / private view/1 is never read on the public path');
  assert.equal(P.validate(v2).code, 'DELIVERY_REQUIRED'); assert.equal(P.validate(v2, { delivery: 'v2' }).code, 'DELIVERY_REQUIRED');
  for (const d of ['PUBLIC', 'PRIVATE_DEV']) assert.equal(P.validate(X.edit((x) => { x.schema_version = 'policy-impact-view/3'; }, v2), { delivery: d }).code, 'VIEW_VERSION', 'an unknown version is refused on ' + d);
  assert.deepEqual(Object.keys(P.DELIVERY), ['PUBLIC', 'PRIVATE_DEV']); assert.equal(P.DELIVERY.PUBLIC.file, P.FILE);
  refused((x) => { x.schema_version = 'policy-impact-view/3'; }, 'VIEW_VERSION');
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
    [(x) => { x.schema_version = 'policy-impact-view/0'; }, 'VIEW_VERSION'], [(x) => { x.extra = 1; }, 'KEY_UNKNOWN'], [(x) => { delete x.as_of; }, 'KEY_MISSING'],
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
  assert.equal(V('{}').ok, false); assert.equal(V(null).ok, false); assert.equal(V(X.codexView().bundle).code, 'KEY_MISSING', 'a bare bundle is not the envelope');
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
  const v = accept(X.codexView()); assert.ok(Object.isFrozen(V(X.codexView()).value.bundle.policies[0]));
  assert.equal(v.order[0].current.lifecycle_status, 'ADOPTED', 'effective_from 2026-11-02 before as_of does not make it EFFECTIVE');
});
(async () => {
  const job = X.navJob(), navv = X.navView();
  let r = await P.validateNavigation(navv, job.view); assert.equal(r.ok, true, JSON.stringify(r));
  const ix = P.navIndex(r.value), pol = job.view.bundle.policies[0];
  const t = P.titleState(pol, ix); assert.equal(t.state, 'OFFICIAL'); assert.equal(t.official, navv.titles[0].official_title); assert.equal(t.ko, navv.titles[0].explanation_title_ko);
  assert.ok(t.koText.includes('공식 제목 아님')); assert.equal(P.titleOf(pol, ix), navv.titles[0].official_title); assert.equal(P.titleOf(pol, null), pol.title, 'no sidecar: the file title, untouched');
  assert.equal(ix.count, 1); assert.deepEqual([...ix.news.keys()], [navv.news_links[0].news_ref.link]);
  // the Main NAV variant (Codex projection, the screen's news link) is bound to its view as well
  const NAV = VAR.NAV; r = await P.validateNavigation(NAV.navigation, NAV.view); assert.equal(r.ok, true, JSON.stringify(r));
  // bound to the exact view: another view, a changed view, a changed hash -> refused whole
  const bad = async (nav, view, code) => { const q = await P.validateNavigation(nav, view); assert.equal(q.ok, false, code); assert.equal(q.code, code, JSON.stringify(q)); };
  await bad(navv, X.publicV2(), 'TITLE_SOURCE');
  const changed = JSON.parse(JSON.stringify(job.view)); changed.bundle.policies[0].scope_description += '.'; await bad(navv, changed, 'BASE_VIEW_HASH');
  const e = (fn) => { const c = JSON.parse(JSON.stringify(navv)); fn(c); return c; };
  await bad(e((c) => { c.base_view_hash = '0'.repeat(64); }), job.view, 'BASE_VIEW_HASH');
  await bad(e((c) => { c.titles[0].explanation_origin = 'OFFICIAL'; }), job.view, 'EXPLANATION_ORIGIN');
  await bad(e((c) => { c.titles[0].source_sha256 = 'a'.repeat(64); }), job.view, 'TITLE_SOURCE');
  await bad(e((c) => { c.titles[0].publication_permission = 'PRIVATE_ONLY'; }), job.view, 'NAV_NOT_PUBLIC');
  await bad(e((c) => { c.news_links[0].relation = 'POLICY_EVIDENCE'; }), job.view, 'NOT_POLICY_EVIDENCE');
  await bad(e((c) => { c.news_links[0].evidence_effect = 'SUPPORTS'; }), job.view, 'NOT_POLICY_EVIDENCE');
  await bad(e((c) => { c.news_links[0].news_ref.link = 'https://www.reuters.com/x'; }), job.view, 'SYNTHETIC_REAL_LINK');
  await bad(e((c) => { c.automatic_publication = true; }), job.view, 'NAV_AUTO_PUBLICATION');
  await bad(e((c) => { c.data_kind = 'REAL_REVIEWED'; }), job.view, 'MIXED_KIND');
  await bad(e((c) => { c.extra = 1; }), job.view, 'KEY_UNKNOWN');
  assert.throws(() => P.canon({ a: 1 }), (x) => x.code === 'NAV_HASH_NUMBER', 'a number is not reproduced: the sidecar is refused, never joined to a guess');
  // the same text as Python json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':')): {"a":{},"b":[true,null,"é\"\n"]}
  assert.equal(P.canon({ b: [true, null, 'é"\n'], a: {} }), '{"a":{},"b":[true,null,"é\\"\\n"]}');
  n++; console.log('PASS navigation sidecar: bound to the exact view by base_view_hash (JS digest = Codex digest), official / Korean titles apart, reviewed news links only, every fault refuses it whole');
  // ---- navigation/2 (Codex #512 37cef584): bound to the SHA-256 of the exact delivered view bytes; /1 kept explicitly
  const u8 = (b) => new Uint8Array(b), dec = async (b) => { const d = await P.decodeView(u8(b)); assert.equal(d.ok, true, JSON.stringify(d)); return d.value; };
  const cases = X.nav2Cases(); assert.deepEqual(cases.map((c) => c.ratio), [0, 1, 0.125, 1e-7, 0, 1]);
  for (const c of cases) {
    const rec = await dec(c.viewBytes);
    assert.equal(rec.sha256, c.viewSha256, c.name + ': the hash is over the delivered bytes'); assert.equal(rec.byteLength, c.viewBytes.length);
    const v = P.validate(rec.json, { delivery: 'PUBLIC' }); assert.equal(v.ok, true, c.name + ' ' + JSON.stringify(v));
    assert.equal(typeof rec.json.bundle.exposures[0].ratio.value, 'number', c.name + ': the number stays a number');
    const q = await P.validateNavigation(c.navigation, rec); assert.equal(q.ok, true, c.name + ' ' + JSON.stringify(q));
    const ix = P.navIndex(q.value); assert.equal(q.value.titles.length, c.expected.titles); assert.equal(ix.count, c.expected.news_links);
    assert.equal(P.titleState(rec.json.bundle.policies[0], ix).state, 'OFFICIAL');
    // /2 needs the byte record: the parsed object alone is refused (no re-serialized hash), whatever its content
    await bad(c.navigation, rec.json, 'NAV_VIEW_BYTES_REQUIRED');
    // the same view re-serialized or re-indented is other bytes: refused, never re-hashed to fit
    for (const other of [JSON.stringify(rec.json), JSON.stringify(rec.json, null, 1) + '\n', c.viewBytes.toString('utf8').replace(/\n$/, '')]) {
      const r2 = await dec(Buffer.from(other, 'utf8')); assert.notEqual(r2.sha256, c.viewSha256); await bad(c.navigation, r2, 'BASE_VIEW_HASH'); }
    const n2 = (fn) => { const x = JSON.parse(JSON.stringify(c.navigation)); fn(x); return x; };
    await bad(n2((x) => { x.hash_algorithm = 'SHA256_CANONICAL_JSON'; }), rec, 'NAV_HASH_ALGORITHM');
    await bad(n2((x) => { delete x.hash_algorithm; }), rec, 'KEY_MISSING');
    await bad(n2((x) => { x.schema_version = 'policy-impact-navigation/3'; }), rec, 'NAV_VERSION');
    await bad(n2((x) => { x.titles[0].publication_permission = 'PRIVATE_ONLY'; }), rec, 'NAV_NOT_PUBLIC');
    await bad(n2((x) => { x.news_links[0].evidence_effect = 'SUPPORTS'; }), rec, 'NOT_POLICY_EVIDENCE');
    // the legacy /1 rule on the same numeric view: NAV_HASH_NUMBER, as before (never a guessed hash)
    const legacy = n2((x) => { x.schema_version = 'policy-impact-navigation/1'; delete x.hash_algorithm; });
    const l = await P.validateNavigation(legacy, rec); assert.equal(l.code, c.expected.legacy_reader, c.name);
  }
  // the decoder refuses what Codex's reader refuses, before any check
  const code = async (bytes) => (await P.decodeView(bytes)).code, T = (s2) => new TextEncoder().encode(s2);
  const base = cases[0].viewBytes.toString('utf8');
  assert.equal(await code(T(base.replace('"schema_version": "policy-impact-view/2",', '"schema_version": "policy-impact-view/2", "schema_version": "policy-impact-view/2",'))), 'VIEW_DUPLICATE_KEY');
  assert.equal(await code(T(base.replace(/"value": 0\b/, '"value": 1e400'))), 'VIEW_NUMBER');
  assert.equal(await code(T('\ufeff' + base)), 'VIEW_BOM');
  assert.equal(await code(u8([...cases[0].viewBytes.subarray(0, 20), 0xff, ...cases[0].viewBytes.subarray(20)])), 'VIEW_UTF8');
  assert.equal(await code(T(base.slice(0, -10))), 'VIEW_JSON'); assert.equal(await code(T('[]')), 'VIEW_JSON'); assert.equal(await code(base), 'VIEW_BYTES_REQUIRED');
  // a /1 sidecar still binds to its view (record or plain object), unchanged
  const r1 = await P.validateNavigation(navv, await dec(Buffer.from(JSON.stringify(job.view)))); assert.equal(r1.ok, true, JSON.stringify(r1));
  n++; console.log('PASS navigation/2: Codex 6 pairs (0, 1, 0.125, 1e-7, 0.0, 1.0) bound to the delivered bytes, 1 title + 1 news link each; re-serialized / re-indented / unbound / wrong algorithm / version 3 / permission refused; /1 kept (NAV_HASH_NUMBER on numbers); duplicate key, non-finite number, BOM, bad UTF-8 refused');
  console.log('ok ' + n + ' checks');
})().catch((e) => { console.error(e); process.exitCode = 1; });
