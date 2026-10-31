'use strict';
// New frontend · feature 5 뉴스·공시·관계망 (web_app/screen-news-live.js, the part after the first paint; screen-news.js is its
// skeleton): the pure parts ported from the old readers equal the old functions on synthetic lists (tools/web_app_news_fixture.js).
//  - Display tables = news-signals.js CLASSES / CHANNELS / TIERS / FILTER_DEFAULT, sec-disclosures.js CLASSES, dart-disclosures.js
//    CLASSES.
//  - timeline = NewsSignals.timeline (with DartDisclosures as its dartApi) and dartRows = DartDisclosures.timeline, for full,
//    partial (one or two files missing: an IR release whose 8-K is absent stands alone) and empty lists, every company range.
//  - rowCategory / rowOccurrence / rowTier / filterRows = the old functions over every channel × class × new-repeat × order and
//    several interest / held sets; categories / categoryLabel = news-signals.js mount's cats / catLabel (frozen copy below).
//  - counts = the numbers NewsSignals.occurrenceSummary writes (read from its DOM through a small fake document).
//  - refreshStatus / refreshText = the old functions for an updated run, the GDELT 429 run, a schema 1 copy, a copy written
//    without a collection and the offline NOT_AVAILABLE file, per company range; refreshBadge = mount's badge rule.
//  - secClassLabel = SecDisclosures.classLabel, dartClassLabel = DartDisclosures.classLabel, secItemsText = renderRow's items line,
//    isStale = the mounts' STALE rule; the evidence words (filingDedup, newsDedup, newsLatest, occurrenceLabel), treeFacts
//    (ia-screens.js newsExamples rule), labelOf, scopeIds and cleanFilters against their stated rules.
// The file loads under node without a window (module.exports); nothing here touches the network or a device store.
const test = require('node:test');
const assert = require('node:assert/strict');
const R = require('./web_app_reuse');
const X = require('./web_app_news_fixture.js');

const M = require(R.newPath('screen-news-live.js'));
const NS = R.requireOld('news-signals.js'), SD = R.requireOld('sec-disclosures.js'), DD = R.requireOld('dart-disclosures.js');
const SETS = {
  full: { sec: X.sec(), news: X.news(), dart: X.dart() },
  failedRun: { sec: X.sec(), news: X.news(X.NOW, { scenario: 'GDELT_429' }), dart: X.dart() },
  without: { sec: X.sec(), news: X.news(X.NOW, { without: ['nvda', 'amd'] }), dart: X.dart() },
  noSec: { sec: null, news: X.news(), dart: X.dart() },
  noNews: { sec: X.sec(), news: null, dart: X.dart() },
  newsOnly: { sec: null, news: X.news(), dart: null },
  none: { sec: null, news: null, dart: null },
  empty: X.empty(),
};
const RANGES = [null, [], ['msft'], ['nvda', 'amd'], ['hanmi'], ['tokyo_electron', 'stry'], ['googl', 'msft', 'hanmi'], ['NYSE:FIX']];
const NEWS_COPIES = { updated: X.news(), failedRun: X.news(X.NOW, { scenario: 'GDELT_429' }), v1: X.newsV1(), noRun: X.newsNoRun(), empty: X.empty().news };

test('display tables are the old readers\' words', () => {
  assert.deepEqual(M.NEWS_CLASS, NS.CLASSES);
  assert.deepEqual(M.SEC_CLASS, SD.CLASSES);
  assert.deepEqual(M.DART_CLASS, DD.CLASSES);
  assert.deepEqual(M.CHANNEL, { DISCLOSURE: NS.CHANNELS.DISCLOSURE[0], NEWS: NS.CHANNELS.NEWS[0] });
  assert.deepEqual(M.TIERS, Object.fromEntries(Object.entries(NS.TIERS).map(([k, v]) => [k, v[0]])));
  assert.deepEqual(M.FILTER_DEFAULT, NS.FILTER_DEFAULT);
  assert.deepEqual(M.FILES, { sec: SD.FILENAME, news: NS.FILENAME, dart: DD.FILENAME });
  assert.equal(M.LIMIT, 30, 'the old mounts\' newest-30 window');
});

test('timeline = NewsSignals.timeline (DartDisclosures as dartApi); dartRows = DartDisclosures.timeline', () => {
  let rows = 0, orphan = 0, folded = 0, related = 0;
  for (const [name, set] of Object.entries(SETS)) for (const ids of RANGES) {
    const got = M.timeline(set, { companyIds: ids }), want = NS.timeline(set, { companyIds: ids, dartApi: DD });
    assert.deepEqual(got, want, name + ' ' + JSON.stringify(ids));
    rows += got.length; orphan += got.filter((r) => r.orphan).length; folded += got.filter((r) => r.repeats && r.repeats.length).length; related += got.filter((r) => r.related && r.related.length).length;
    assert.deepEqual(M.dartRows(set.dart, ids), DD.timeline(set.dart, { companyIds: ids }), name + ' dart ' + JSON.stringify(ids));
  }
  assert.ok(rows > 100 && orphan > 0 && folded > 0 && related > 0, 'the cases reach every row kind (orphan IR release, folded repeats, IR under its 8-K)');
  const all = M.timeline(SETS.full);
  assert.deepEqual(all.map((r) => r.channel + ':' + r.source).slice(0, 4), ['NEWS:GDELT', 'DISCLOSURE:SEC', 'NEWS:GDELT', 'NEWS:GDELT'], 'newest first, both channels in one list (the nvda event at its first report)');
  assert.equal(all.length, SETS.full.sec.events.length + SETS.full.dart.events.length + 5, 'the nvda repeat folds and the msft IR release sits under its 8-K');
});

test('rowCategory / rowOccurrence / rowTier / filterRows = the old functions over every filter', () => {
  const CTX = [{}, { held: [], interests: [] }, { held: [], interests: ['msft', 'nvda'] }, { held: ['amd'], interests: ['hanmi', 'amd'] }];
  let combos = 0, nonEmpty = 0;
  for (const [name, set] of Object.entries(SETS)) for (const ids of [null, ['msft'], ['nvda', 'amd', 'hanmi']]) {
    const all = M.timeline(set, { companyIds: ids }), rows = all.slice(0, M.LIMIT);
    for (const r of all) {
      assert.equal(M.rowCategory(r), NS.rowCategory(r)); assert.equal(M.rowOccurrence(r), NS.rowOccurrence(r));
      for (const c of CTX) assert.equal(M.rowTier(r, c), NS.rowTier(r, c));
    }
    for (const channel of ['ALL', 'DISCLOSURE', 'NEWS']) for (const category of ['ALL', ...M.categories(all), 'SEC:NONE']) for (const occurrence of ['ALL', 'NEW', 'REPEAT'])
      for (const order of ['TIME', 'IMPORTANCE']) for (const c of CTX) {
        const f = { channel, category, occurrence, order }, got = M.filterRows(rows, f, c);
        assert.deepEqual(got, NS.filterRows(rows, f, c), name + ' ' + JSON.stringify(f));
        combos++; if (got.length) nonEmpty++;
      }
    assert.deepEqual(M.filterRows(rows), NS.filterRows(rows), 'default filter');
  }
  assert.ok(combos > 1000 && nonEmpty > 300, 'many filter combinations, most of them showing rows (' + nonEmpty + '/' + combos + ')');
  // IMPORTANCE puts the interest rows first and keeps time order inside a tier.
  const rows = M.timeline(SETS.full).slice(0, M.LIMIT), imp = M.filterRows(rows, { ...M.FILTER_DEFAULT, order: 'IMPORTANCE' }, { held: [], interests: ['msft'] });
  const firstOther = imp.findIndex((r) => r.company_id !== 'msft');
  assert.ok(firstOther > 0 && imp.slice(firstOther).every((r) => r.company_id !== 'msft'), 'interest tier first');
});

test('categories / categoryLabel = news-signals.js mount cats / catLabel (frozen copy of lines 216-217)', () => {
  const catOrder = (k) => (k === 'RESULTS' ? '0' : k.startsWith('NEWS:') ? '1' + k : k.startsWith('SEC:') ? '2' + k : '3' + k);
  const oldCats = (all) => [...new Set(all.map(NS.rowCategory))].sort((a, b) => (catOrder(a) < catOrder(b) ? -1 : 1));
  const oldLabel = (key) => { if (key === 'RESULTS') return '실적'; const [src, c] = key.split(':'), table = src === 'NEWS' ? NS.CLASSES : src === 'SEC' ? SD.CLASSES : DD.CLASSES, pair = table && table[c]; return (pair ? pair[0] : c) + ' · ' + (src === 'NEWS' ? '뉴스' : src); };
  for (const [name, set] of Object.entries(SETS)) {
    const all = M.timeline(set);
    assert.deepEqual(M.categories(all), oldCats(all), name);
    for (const k of M.categories(all)) assert.equal(M.categoryLabel(k), oldLabel(k), k);
  }
  assert.deepEqual(M.categories(M.timeline(SETS.full)), ['RESULTS', 'NEWS:LEGAL', 'NEWS:OTHER', 'NEWS:PRODUCT', 'SEC:MATERIAL_AGREEMENT', 'SEC:OFFICERS_DIRECTORS', 'SEC:OTHER', 'DART:EXCHANGE', 'DART:FAIR_DISCLOSURE', 'DART:MAJOR_EVENT', 'DART:OTHER', 'DART:PERIODIC']);
});

test('counts = the numbers NewsSignals.occurrenceSummary writes', () => {
  // A small fake document: occurrenceSummary only creates elements, sets text / class / attributes and appends.
  const el = () => ({ children: [], attrs: {}, textContent: '', className: '', setAttribute(k, v) { this.attrs[k] = v; }, append(...c) { this.children.push(...c); } });
  const doc = { createElement: el, createDocumentFragment: el };
  const oldCounts = (rows) => { const frag = NS.occurrenceSummary(doc, rows, M.LIMIT, false), dl = frag.children[0], out = {};
    for (const n of dl.children) if (n.attrs['data-occurrence-count']) out[n.attrs['data-occurrence-count']] = Number(n.textContent); return out; };
  for (const [name, set] of Object.entries(SETS)) for (const ids of RANGES) {
    const rows = M.timeline(set, { companyIds: ids }).slice(0, M.LIMIT);
    assert.deepEqual(M.counts(rows), oldCounts(rows), name + ' ' + JSON.stringify(ids));
  }
  assert.deepEqual(M.counts(M.timeline(SETS.full).slice(0, M.LIMIT)), { NEW: 17, REPEAT: 2, FOLDED: 2 });
  assert.deepEqual(M.counts(M.timeline(SETS.newsOnly)), { NEW: 5, REPEAT: 1, FOLDED: 1 }, 'the orphan IR release counts as a repeat');
});

test('refreshStatus / refreshText = the old functions; refreshBadge = mount\'s badge rule', () => {
  const oldBadge = (rows) => { const recorded = rows.filter((x) => x.kind === 'RECORDED'); if (!recorded.length) return null;
    return recorded.every((x) => ['UPDATED', 'NO_NEW_ITEMS'].includes(x.result)) ? 'OK' : recorded.some((x) => ['UPDATED', 'NO_NEW_ITEMS'].includes(x.result) || x.result === 'PARTIAL_FAILED') ? 'PARTIAL_FAILED' : 'FAILED'; };
  const kinds = new Set(), results = new Set();
  for (const [name, n] of Object.entries(NEWS_COPIES)) for (const ids of RANGES) {
    const got = M.refreshStatus(n, { companyIds: ids }), want = NS.refreshStatus(n, { companyIds: ids });
    assert.deepEqual(got, want, name + ' ' + JSON.stringify(ids));
    for (const r of got) { kinds.add(r.kind); if (r.result) results.add(r.result); assert.equal(M.refreshText(r), NS.refreshText(r, false), name + ' ' + r.source + ' ' + JSON.stringify(ids)); }
    assert.equal(M.refreshBadge(got), oldBadge(want));
  }
  assert.deepEqual([...kinds].sort(), ['NO_FEED', 'NO_RUN', 'RECORDED', 'UNRECORDED']);
  assert.deepEqual([...results].sort(), ['FAILED', 'NOT_RUN', 'NO_NEW_ITEMS', 'PARTIAL_FAILED', 'UPDATED']);
  assert.deepEqual(M.refreshStatus(null), []);
  const failedRun = M.refreshStatus(NEWS_COPIES.failedRun);
  assert.equal(M.refreshBadge(failedRun), 'PARTIAL_FAILED');
  assert.match(M.refreshText(failedRun[0]), /^GDELT · 이전 자료 유지 · 마지막 성공 2026-10-13 16:30 UTC · 최근 갱신 실패\(GDELT HTTP_429, 2026-10-14 02:30 UTC\)$/);
  assert.equal(M.refreshText(M.refreshStatus(NEWS_COPIES.updated, { companyIds: ['hanmi'] })[1]), '회사 IR · 보는 기업에 확인된 공식 피드 없음');
});

test('labels, items line, STALE and evidence words', () => {
  const events = [...SETS.full.sec.events, { ...SETS.full.sec.events[0], classification: 'OTHER', items: ['9.01', '3.02'] }, { ...SETS.full.sec.events[0], classification: 'OTHER', items: ['9.01'] }];
  for (const e of events) assert.equal(M.secClassLabel(e, SD.ITEMS), SD.classLabel(e.classification, false, e.items));
  const oldItems = (e) => e.items.map((c) => { const [en, k] = SD.ITEMS[c]; return c + ' ' + k + ' (' + en + ')'; }).join(' / ') || (['6-K', '6-K/A'].includes(e.form) ? '분기 실적 6-K · 공시 첨부 제목 확인' : '항목 미제공');
  for (const e of [...events, { ...events[0], items: [], form: '6-K' }, { ...events[0], items: [] }]) assert.equal(M.secItemsText(e, SD.ITEMS), oldItems(e));
  for (const c of Object.keys(DD.CLASSES)) assert.equal(M.dartClassLabel(c), DD.classLabel(c, false));
  for (const [c, [k, en]] of Object.entries(NS.CLASSES)) assert.equal(M.newsClassLabel(c), k + ' (' + en + ')');
  // STALE: as_of + stale_after_seconds passed, never for a NOT_AVAILABLE file (the old mounts' rule).
  const oldStale = (p, now) => p.state !== 'NOT_AVAILABLE' && now - Date.parse(p.as_of) > p.stale_after_seconds * 1000;
  for (const p of [SETS.full.sec, SETS.full.news, SETS.full.dart, ...Object.values(SETS.empty)]) for (const now of [X.NOW, X.NOW + 2 * 86400000, X.NOW + 3 * 86400000])
    assert.equal(M.isStale(p, now), oldStale(p, now));
  assert.equal(M.isStale(SETS.full.dart, X.NOW), true, 'the DART vector (as of 2026-10-11) is overdue at the test clock');
  assert.equal(M.isStale(SETS.full.sec, X.NOW), false); assert.equal(M.isStale(null, X.NOW), false);
  // Evidence words (sec / dart evidence(), news-signals.js newsEvidence / latest).
  const amended = SETS.full.sec.events.find((e) => e.occurrence === 'REPEAT');
  assert.equal(M.filingDedup(SETS.full.sec.events[0], SETS.full.sec.events[0].accession), '새 공시 · 묶음 시작');
  assert.equal(M.filingDedup(amended, amended.accession), '정정·반복 · 원 공시 묶음 ' + amended.group_id);
  assert.equal(M.filingDedup({ ...amended, group_id: amended.company_id + ':' + amended.accession }, amended.accession), '정정·반복 · 원 공시를 하나로 특정하지 못해 단독 표시');
  const rows = M.timeline(SETS.newsOnly), orphan = rows.find((r) => r.orphan), group = rows.find((r) => r.repeats.length), single = rows.find((r) => r.channel === 'NEWS' && !r.orphan && !r.repeats.length);
  assert.match(M.newsDedup(orphan), /^8-K 관련 IR 보도자료 · 그 8-K\(\d{10}-\d{2}-\d{6}\)가 목록에 없어 단독 표시$/);
  assert.equal(M.newsDedup(group), '같은 사건 묶음 · 첫 보도 + 반복 1건 (72시간 안 제목 유사)');
  assert.equal(M.newsDedup(single), '새 소식 · 반복 보도 없음');
  assert.equal(M.newsDedup({ item: { ...single.item, occurrence: 'REPEAT' }, repeats: [], orphan: false }), '반복 보도 · 첫 보도는 목록 범위 밖');
  assert.deepEqual([orphan, group, single, M.timeline(SETS.full).find((r) => r.source === 'SEC'), { channel: 'DISCLOSURE', source: 'SEC', event: amended }].map(M.occurrenceLabel), ['8-K 관련 · 반복', '새 소식', '새 소식', '새 공시', '정정·반복']);
  assert.equal(M.newsLatest(SETS.full.news, single.item), '새 뉴스 반영 · 2026-10-14 02:30 UTC');
  const f429 = SETS.failedRun.news, gd = f429.items.find((i) => i.source === 'GDELT' && i.company_id === 'amd'), gn = f429.items.find((i) => i.source === 'GDELT' && i.company_id === 'nvda');
  assert.equal(M.newsLatest(f429, gd), '조회 실패 HTTP_429 · 2026-10-14 02:30 UTC · 이 행은 이전 수집분');
  assert.equal(M.newsLatest(f429, gn), '요청 안 함 HTTP_429 · 2026-10-14 02:30 UTC · 이 행은 이전 수집분');
  assert.equal(M.newsLatest(NEWS_COPIES.v1, single.item), '결과 미기록'); assert.equal(M.newsLatest(NEWS_COPIES.noRun, single.item), '결과 미기록'); assert.equal(M.newsLatest(null, single.item), '결과 미기록');
});

test('treeFacts (ia-screens.js newsExamples: count, as_of, newest), labelOf, scopeIds, cleanFilters', () => {
  const byDesc = (rows, k) => [...rows].sort((a, b) => (String(b[k]) < String(a[k]) ? -1 : String(b[k]) > String(a[k]) ? 1 : 0))[0] || null;
  for (const [name, set] of Object.entries(SETS)) {
    const t = M.treeFacts(set);
    assert.deepEqual(t.sec, set.sec ? { count: set.sec.events.length, as_of: set.sec.as_of, latest: byDesc(set.sec.events, 'accepted_at') } : null, name);
    assert.deepEqual(t.news, set.news ? { count: set.news.items.length, as_of: set.news.as_of, latest: byDesc(set.news.items, 'published_at') } : null, name);
    assert.deepEqual(t.dart, set.dart ? { count: set.dart.events.length, as_of: set.dart.as_of, latest: set.dart.events[0] || null } : null, name + ' (DART newest first by filing date)');
  }
  assert.deepEqual([M.treeFacts(SETS.empty).sec.count, M.treeFacts(SETS.empty).sec.latest], [0, null], 'an empty file counts 0 and has no example');
  const C = { get: (id) => (id === 'nvda' || id === 'NASDAQ:NVDA' ? { ticker: 'NVDA' } : id === 'stry' ? { ticker: 'SYK' } : null) };
  assert.deepEqual(['nvda', 'stry', 'hanmi', 'tokyo_electron', 'amd'].map((id) => M.labelOf(id, C)), ['NVDA', 'SYK', '042700', '8035', 'AMD']);
  assert.equal(M.labelOf('amd', { get() { throw Error('x'); } }), 'AMD', 'a company list that cannot answer falls back to the id');
  assert.equal(M.labelOf('msft', null), 'MSFT');
  assert.equal(M.scopeIds('ALL', { center: 'nvda', interests: ['msft'] }), null);
  assert.deepEqual(M.scopeIds('CENTER', { center: 'nvda' }), ['nvda']);
  assert.equal(M.scopeIds('CENTER', { center: null }), null, 'no centre: every company');
  assert.deepEqual(M.scopeIds('INTEREST', { interests: ['msft', 'nvda'] }), ['msft', 'nvda']);
  assert.deepEqual(M.scopeIds('INTEREST', {}), [], 'no interests: none (the screen says so)');
  assert.deepEqual(M.cleanFilters({ channel: 'NEWS', category: 'SEC:OTHER', occurrence: 'X', order: 'IMPORTANCE', extra: 1 }, ['SEC:OTHER']), { channel: 'NEWS', category: 'SEC:OTHER', occurrence: 'ALL', order: 'IMPORTANCE' });
  assert.deepEqual(M.cleanFilters({ category: 'SEC:OTHER' }, []), M.FILTER_DEFAULT, 'a class the list no longer has falls back to ALL');
  assert.deepEqual(M.cleanFilters(null), M.FILTER_DEFAULT);
});

test('the module exports pure parts and install only (no window, no layer at load)', () => {
  assert.equal(typeof M.install, 'function');
  for (const [k, v] of Object.entries(M)) if (typeof v === 'object') assert.ok(Object.isFrozen(v), k + ' is frozen');
});
