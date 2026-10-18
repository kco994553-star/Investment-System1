'use strict';
// PriceTime (D10): read time and the price's own time stay apart; staleness only from a confirmed price time or date.
// Synthetic records only (no price values are needed or read).
const test = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const PT = require(path.join(__dirname, '../src/investment_system/product/web_assets/price-time.js'));
const DM = require(path.join(__dirname, '../src/investment_system/product/web_assets/device-market.js'));
// The existing device-market quote rule (DeviceMarket.staleness) is passed in; PriceTime has no threshold of its own.
const NOW = Date.parse('2026-10-18T10:00:00Z'), READ = '2026-10-18T09:30:00.000Z', RULE = {now: NOW, staleness: DM.staleness};

test('GOOGLEFINANCE UNKNOWN: as_of equals the read time but is never a price time', () => {
  const d = PT.describe({as_of: READ, available_at: READ, source: 'GOOGLEFINANCE', time_status: 'UNKNOWN'}, RULE);
  assert.equal(d.status, 'UNCONFIRMED'); assert.equal(d.price_time, null); assert.equal(d.price_date, null);
  assert.equal(d.read_at, READ); assert.equal(d.stale, null); assert.equal(d.freshness, 'UNDETERMINED');
  assert.equal(d.price_label_ko, '가격 기준 시각 미확인'); assert.equal(d.read_label_ko, '읽은 시각 2026-10-18 09:30 UTC · 2026-10-18 18:30 KST');
  assert.equal(d.label_ko, '가격 기준 시각 미확인 · 읽은 시각 2026-10-18 09:30 UTC · 2026-10-18 18:30 KST · 신선도 판정 불가');
  assert.ok(!d.label_ko.includes('STALE')); assert.equal(PT.describe({as_of: READ, available_at: READ, source: 'GOOGLEFINANCE', time_status: 'FX_UNKNOWN'}, RULE).status, 'UNCONFIRMED');
});
test('Universe tab price (GOOGLEFINANCE_CURRENT, trade_time null) and priceBasis (price_time null) are UNCONFIRMED; read = acquired/observed', () => {
  const sub = PT.describe({price_kind: 'GOOGLEFINANCE_CURRENT', trade_time: null, exact_eod: false, as_of: READ, observed_at: READ, available_at: READ}, RULE);
  assert.equal(sub.status, 'UNCONFIRMED'); assert.equal(sub.read_at, READ);
  const basis = PT.describe({source: 'GOOGLEFINANCE_PRIVATE_UNIVERSE', read_id: 'job_x', acquired_at: READ, currency: 'USD', price_time: null}, RULE);
  assert.equal(basis.status, 'UNCONFIRMED'); assert.equal(basis.read_at, READ); assert.equal(basis.stale, null);
});
test('Worker close (SESSION_CLOSE) is DATE_ONLY; an old session date read just now is STALE', () => {
  const fresh = PT.describe({as_of: '2026-10-16T00:00:00Z', available_at: READ, source: 'WORKER_CLOSE', time_status: 'SESSION_CLOSE'}, RULE);
  assert.equal(fresh.status, 'DATE_ONLY'); assert.equal(fresh.price_date, '2026-10-16'); assert.equal(fresh.stale, false); assert.equal(fresh.freshness, 'CURRENT');
  assert.equal(fresh.label_ko, '가격 기준일 2026-10-16 (거래일) · 읽은 시각 2026-10-18 09:30 UTC · 2026-10-18 18:30 KST');
  const old = PT.describe({as_of: '2026-09-01T00:00:00Z', available_at: READ, source: 'WORKER_CLOSE', time_status: 'SESSION_CLOSE'}, RULE);
  assert.equal(old.stale, true); assert.equal(old.freshness, 'STALE'); assert.ok(old.label_ko.endsWith('STALE · 오래된 가격'));
});
test('KNOWN / MANUAL price time is CONFIRMED; staleness follows it, not the read time', () => {
  const known = PT.describe({as_of: '2026-10-17T20:00:00Z', available_at: READ, source: 'GOOGLEFINANCE', time_status: 'KNOWN'}, RULE);
  assert.equal(known.status, 'CONFIRMED'); assert.equal(known.price_time, '2026-10-17T20:00:00Z'); assert.equal(known.stale, false);
  assert.equal(known.price_label_ko, '가격 기준 시각 2026-10-17 20:00 UTC · 2026-10-18 05:00 KST');
  const manual = PT.describe({as_of: '2026-10-01T00:00:00Z', available_at: READ, source: 'MANUAL'}, RULE);
  assert.equal(manual.status, 'CONFIRMED'); assert.equal(manual.stale, true);
});
test('without an existing rule for the source, even a confirmed time stays 판정 불가 (no invented threshold)', () => {
  for (const options of [{now: NOW}, {now: NOW, staleness: () => { throw new Error('x'); }}, {now: NOW, staleness: () => 'OTHER'}]) {
    const d = PT.describe({as_of: '2020-01-01T00:00:00Z', available_at: READ, source: 'MANUAL'}, options);
    assert.equal(d.status, 'CONFIRMED'); assert.equal(d.stale, null); assert.equal(d.freshness, 'UNDETERMINED'); assert.ok(d.label_ko.endsWith('신선도 판정 불가'));
  }
});
test('Prices_D row: date is the price date, fetched_at the read time', () => {
  const d = PT.describe({symbol: 'SYN', date: '2026-10-15', source: 'GOOGLEFINANCE', fetched_at: READ}, RULE);
  assert.equal(d.status, 'DATE_ONLY'); assert.equal(d.price_date, '2026-10-15'); assert.equal(d.read_at, READ);
});
test('missing or malformed input never invents a time', () => {
  for (const q of [null, undefined, {}, {as_of: 'yesterday'}, {time_status: 'KNOWN', as_of: 'x'}, {time_status: 'OTHER', as_of: READ}]) {
    const d = PT.describe(q, RULE); assert.equal(d.status, 'UNCONFIRMED'); assert.equal(d.stale, null);
  }
  assert.equal(PT.describe({}, RULE).read_label_ko, '읽은 시각 —');
});
test('English labels and escaped HTML without inline style', () => {
  const d = PT.describe({as_of: READ, available_at: READ, source: 'GOOGLEFINANCE', time_status: 'UNKNOWN'}, RULE);
  assert.equal(d.price_label_en, 'Price time unconfirmed'); assert.ok(d.label_en.includes('Freshness undetermined'));
  const html = PT.html(d, {locale: 'ko-KR'});
  assert.ok(html.includes('data-price-time-status="UNCONFIRMED"')); assert.ok(html.includes('data-price-freshness="UNDETERMINED"'));
  assert.ok(html.includes('<span data-price-own-time>가격 기준 시각 미확인</span>')); assert.ok(!/style=/.test(html));
});
test('summarize spans confirmed times only; unconfirmed rows are counted, never dated by their read', () => {
  const s = PT.summarize([
    {as_of: READ, available_at: READ, source: 'GOOGLEFINANCE', time_status: 'UNKNOWN'},
    {as_of: '2026-09-01T00:00:00Z', available_at: READ, source: 'WORKER_CLOSE', time_status: 'SESSION_CLOSE'},
    {as_of: '2026-10-17T20:00:00Z', available_at: '2026-10-17T21:00:00Z', source: 'GOOGLEFINANCE', time_status: 'KNOWN'}], RULE);
  assert.deepEqual({...s}, {rows: 3, confirmed: 2, unconfirmed: 1, stale: 1, from: '2026-09-01', to: '2026-10-17T20:00:00Z', read_from: '2026-10-17T21:00:00Z', read_to: READ});
});
