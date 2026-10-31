'use strict';
// Synthetic public lists for the new frontend's 4. 뉴스 screen tests (web_app_news_node_test.js, web_app_news_browser_test.js).
// Not real filings or news: made-up accessions, titles and example links that only have to pass the old readers' own
// validation (SecDisclosures.validate, NewsSignals.validate, DartDisclosures.validate). Nothing here is a price or a body text.
//  - sec(now) / news(now, {scenario, without}): tools/sec_disclosures_fixture.js and tools/news_signals_fixture.js relative to
//    NOW (the browser test's fixed clock): SEC 8-K rows for nvda (8-K + 8-K/A), amd, msft, googl; GDELT items with one repeat
//    group (nvda), googl, amd, hanmi; two msft IR releases, one repeating the msft 8-K EX-99.1. scenario 'GDELT_429' is the
//    observed failed-refresh shape (every item carried from the previous run).
//  - newsV1(now): the same items as a schema 1 copy (no per-company result, no refresh); newsNoRun(now): schema 2 written without
//    a collection (refresh null).
//  - dart(): the synthetic live DART vector (tests/fixtures/dart_public_vectors_v1.json, written by the Python tests).
//  - empty(): the offline build's NOT_AVAILABLE files (tools/fixtures/empty_public_screens.json), served explicitly.
const fs = require('node:fs');
const path = require('node:path');
const SEC = require('./sec_disclosures_fixture.js');
const NEWS = require('./news_signals_fixture.js');
const NS = require('../src/investment_system/product/web_assets/news-signals.js');
const { EMPTY } = require('./empty_public_screens.js');

const NOW = Date.parse('2026-10-14T03:00:00.000Z');
const sec = (now = NOW) => SEC.payload(now);
const news = (now = NOW, { scenario = 'UPDATED', without = [] } = {}) => NEWS.payload(now, SEC.payload(now), { scenario, without });
const dart = () => JSON.parse(fs.readFileSync(path.join(__dirname, '../tests/fixtures/dart_public_vectors_v1.json'), 'utf8')).cases.find((c) => c.name === 'live').payload;
const base = (p) => (p.state === 'LIVE' ? [] : p.state === 'STALE' ? ['STALE_INPUT'] : ['NO_ELIGIBLE_INPUT']);
function newsV1(now = NOW) {
  const p = structuredClone(news(now));
  p.schema_version = 1; delete p.refresh; p.reason_codes = base(p);
  for (const s of Object.values(p.sources)) for (const e of Object.values(s)) { delete e.last_result; delete e.last_result_code; }
  return NS.validate(p);
}
function newsNoRun(now = NOW) {
  const p = structuredClone(news(now));
  p.refresh = null; p.reason_codes = base(p);
  for (const s of Object.values(p.sources)) for (const e of Object.values(s)) { e.last_result = null; e.last_result_code = null; }
  return NS.validate(p);
}
const empty = () => ({ sec: structuredClone(EMPTY['sec-disclosures.json']), news: structuredClone(EMPTY['news-signals.json']), dart: structuredClone(EMPTY['dart-disclosures.json']) });
module.exports = Object.freeze({ NOW, sec, news, dart, newsV1, newsNoRun, empty });
