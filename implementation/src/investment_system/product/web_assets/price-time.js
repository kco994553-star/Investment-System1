/* PriceTime: the one shared formatter for a price's two times (FRONTEND_DATA_CONTRACT §1-8, defect D10).
   A price has a READ time (when this device read it from a sheet, the Worker or a manual entry) and its OWN time (the trade
   date/time of the price). They are shown apart and never substituted for each other:
   - CONFIRMED   the price carries its own trade time (time_status KNOWN, or a MANUAL/API as_of the user supplied).
   - DATE_ONLY   only the trade date is known (Worker daily close: time_status SESSION_CLOSE; price tab Prices_D `date`).
   - UNCONFIRMED no price time at all (GOOGLEFINANCE with time_status UNKNOWN/FX_UNKNOWN, the Universe tab
                 GOOGLEFINANCE_CURRENT with trade_time null, PrivateSubsetView.priceBasis() with price_time null).
                 Shown exactly '가격 기준 시각 미확인'; freshness is '판정 불가', never current.
   Staleness is judged ONLY from a confirmed price time or date (7 days, the DeviceMarket rule); the read time never decides it.
   Reads only fields the existing records already carry (time_status, as_of, available_at, trade_time, price_time, acquired_at,
   observed_at, date, fetched_at). No price value is read, stored, sent or logged here. No DOM, no network. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PriceTime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const STALE_AFTER_MS = 7 * 24 * 60 * 60 * 1000, KST_MS = 9 * 60 * 60 * 1000;
  const UNCONFIRMED_KO = '가격 기준 시각 미확인', UNCONFIRMED_EN = 'Price time unconfirmed';
  const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/, DAY = /^\d{4}-\d{2}-\d{2}$/;
  const UNKNOWN = new Set(['UNKNOWN', 'FX_UNKNOWN']);
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  function instant(value) {
    if (typeof value !== 'string' || !ISO.test(value)) return null;
    const t = Date.parse(value); return Number.isFinite(t) ? t : null;
  }
  function day(value) {
    if (typeof value !== 'string' || !DAY.test(value)) return null;
    const t = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === value ? value : null;
  }
  /* '2026-10-18 09:31 UTC · 2026-10-18 18:31 KST' (KST = UTC+9, no DST); null when not a timestamp. */
  function clock(value) {
    const t = typeof value === 'number' ? value : instant(value);
    if (t === null || !Number.isFinite(t)) return null;
    const f = ms => new Date(ms).toISOString().slice(0, 16).replace('T', ' ');
    return f(t) + ' UTC · ' + f(t + KST_MS) + ' KST';
  }
  function firstTime(q, keys) { for (const k of keys) if (has(q, k) && instant(q[k]) !== null) return q[k]; return null; }
  /* {price_time, price_date} of one record from its existing fields; both null = UNCONFIRMED. */
  function own(q) {
    const none = {price_time: null, price_date: null};
    if (typeof q.time_status === 'string') {
      if (UNKNOWN.has(q.time_status)) return none;
      if (q.time_status === 'SESSION_CLOSE') return {price_time: null, price_date: day(String(q.as_of || '').slice(0, 10))};
      if (q.time_status === 'KNOWN') return instant(q.as_of) !== null ? {price_time: q.as_of, price_date: null} : none;
      return none;
    }
    if (q.price_kind === 'GOOGLEFINANCE_CURRENT') return none;
    if (has(q, 'price_time') || has(q, 'trade_time')) {
      const v = has(q, 'price_time') ? q.price_time : q.trade_time;
      if (instant(v) !== null) return {price_time: v, price_date: null};
      if (day(v) !== null) return {price_time: null, price_date: v};
      return {price_time: null, price_date: day(q.price_date) || null};
    }
    if (has(q, 'price_date') || (has(q, 'date') && has(q, 'fetched_at'))) return {price_time: null, price_date: day(has(q, 'price_date') ? q.price_date : q.date)};
    // A record without time_status (MANUAL/API device quote): as_of is the price time the user supplied (DeviceMarket 'KNOWN').
    if (instant(q.as_of) !== null) return {price_time: q.as_of, price_date: null};
    if (day(q.as_of) !== null) return {price_time: null, price_date: q.as_of};
    return none;
  }
  /* describe(quote, {now, staleAfterMs}) -> {read_at, price_time|null, price_date|null, status, freshness, stale, labels}.
     stale is true/false only for CONFIRMED/DATE_ONLY; null (판정 불가) for UNCONFIRMED. */
  function describe(quote, options = {}) {
    const q = quote !== null && typeof quote === 'object' ? quote : {};
    const read_at = firstTime(q, ['read_at', 'available_at', 'acquired_at', 'fetched_at', 'observed_at']);
    const {price_time, price_date} = own(q);
    const status = price_time !== null ? 'CONFIRMED' : price_date !== null ? 'DATE_ONLY' : 'UNCONFIRMED';
    const now = typeof options.now === 'number' ? options.now : options.now !== undefined && instant(options.now) !== null ? instant(options.now) : Date.now();
    const limit = Number.isFinite(options.staleAfterMs) && options.staleAfterMs > 0 ? options.staleAfterMs : STALE_AFTER_MS;
    const basis = status === 'CONFIRMED' ? instant(price_time) : status === 'DATE_ONLY' ? Date.parse(price_date + 'T00:00:00Z') : null;
    const stale = basis === null ? null : now - basis >= limit;
    const freshness = stale === null ? 'UNDETERMINED' : stale ? 'STALE' : 'CURRENT';
    const readKo = '읽은 시각 ' + (clock(read_at) || '—'), readEn = 'Read at ' + (clock(read_at) || '—');
    const priceKo = status === 'CONFIRMED' ? '가격 기준 시각 ' + clock(price_time) : status === 'DATE_ONLY' ? '가격 기준일 ' + price_date + ' (거래일)' : UNCONFIRMED_KO;
    const priceEn = status === 'CONFIRMED' ? 'Price time ' + clock(price_time) : status === 'DATE_ONLY' ? 'Price date ' + price_date + ' (trading day)' : UNCONFIRMED_EN;
    const freshKo = freshness === 'STALE' ? 'STALE · 오래된 가격' : freshness === 'UNDETERMINED' ? '신선도 판정 불가' : '';
    const freshEn = freshness === 'STALE' ? 'STALE · old price' : freshness === 'UNDETERMINED' ? 'Freshness undetermined' : '';
    const join = parts => parts.filter(Boolean).join(' · ');
    return Object.freeze({read_at, price_time, price_date, status, freshness, stale,
      stale_after_days: limit / (24 * 60 * 60 * 1000),
      price_label_ko: priceKo, price_label_en: priceEn, read_label_ko: readKo, read_label_en: readEn,
      freshness_label_ko: freshKo, freshness_label_en: freshEn,
      label_ko: join([priceKo, readKo, freshKo]), label_en: join([priceEn, readEn, freshEn])});
  }
  function label(desc, locale) { return locale === 'en-US' ? desc.label_en : desc.label_ko; }
  const esc = v => String(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  /* Escaped inline HTML (no style attribute, CSP). data-price-time-status / data-price-freshness for screens and tests. */
  function html(desc, {locale = 'ko-KR'} = {}) {
    const en = locale === 'en-US';
    const fresh = en ? desc.freshness_label_en : desc.freshness_label_ko;
    return '<span class="price-time" data-price-time-status="' + desc.status + '" data-price-freshness="' + desc.freshness + '">'
      + '<span data-price-own-time>' + esc(en ? desc.price_label_en : desc.price_label_ko) + '</span> · '
      + '<span data-price-read-at>' + esc(en ? desc.read_label_en : desc.read_label_ko) + '</span>'
      + (fresh ? ' · <span data-price-stale="' + desc.freshness + '">' + esc(fresh) + '</span>' : '') + '</span>';
  }
  /* summarize(quotes, {now}) -> {rows, confirmed, unconfirmed, stale, from, to, read_from, read_to}: from/to span the confirmed
     price times/dates (as in QgvScores.vCoverage price_time), read_from/read_to the read times. Old prices are never hidden
     behind a newer read time. */
  const ms = v => v.length === 10 ? Date.parse(v + 'T00:00:00Z') : Date.parse(v);
  function summarize(list, options = {}) {
    const out = {rows: 0, confirmed: 0, unconfirmed: 0, stale: 0, from: null, to: null, read_from: null, read_to: null};
    for (const quote of Array.isArray(list) ? list : []) {
      const d = quote && typeof quote.status === 'string' && has(quote, 'freshness') ? quote : describe(quote, options), own = d.price_time || d.price_date;
      out.rows++;
      if (d.status === 'UNCONFIRMED') out.unconfirmed++; else out.confirmed++;
      if (d.stale === true) out.stale++;
      if (own) { if (out.from === null || ms(own) < ms(out.from)) out.from = own; if (out.to === null || ms(own) > ms(out.to)) out.to = own; }
      if (d.read_at) { if (out.read_from === null || ms(d.read_at) < ms(out.read_from)) out.read_from = d.read_at; if (out.read_to === null || ms(d.read_at) > ms(out.read_to)) out.read_to = d.read_at; }
    }
    return Object.freeze(out);
  }
  return Object.freeze({STALE_AFTER_MS, UNCONFIRMED_KO, UNCONFIRMED_EN, describe, label, html, summarize, clock});
});
