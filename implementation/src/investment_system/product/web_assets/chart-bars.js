/* Chart bar model (TECHNICAL_PATTERN_CHART_V1_DESIGN §7, P1-1 + client half of P1-W). Pure RAM functions:
   no network, no storage, no DOM, no price repair. Python reference: investment_system/technical/chart_bars.py
   (vectors: tests/fixtures/chart_bars_reference_v1.json). Input is a private-history/1 response already checked by
   PrivateHistory.validateHistory. Missing values stay null with a reason code (never 0, never interpolated); a
   reported volume of 0 is a real zero. Weekly bars follow rule W1. Without split events every window is
   PRICE_BASIS_CONTINUITY_UNCONFIRMED; a window crossing a split is CORPORATE_ACTION_IN_WINDOW. Prices are never re-adjusted. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ChartBars = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'chart-bars/1', SOURCE_SCHEMA = 'private-history/1';
  const FALLBACK_PROVIDERS = ['Tiingo EOD', 'KRX OPEN API'], STATUSES = ['COMPLETE', 'IN_PROGRESS', 'UNKNOWN'];
  const OHLC = ['open', 'high', 'low', 'close'], COMPARED = ['open', 'high', 'low', 'close', 'volume'];
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const get = (o, k) => (own(o, k) && o[k] !== undefined ? o[k] : null);
  function fail(code) { throw new Error(code); }
  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const t = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(t) && new Date(t).toISOString().slice(0, 10) === value ? value : null;
  }
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const sorted = list => [...list].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const uniqSorted = list => sorted([...new Set(list)]);
  function sessionDate(timestamp, timeZone) {
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(timestamp * 1000));
    const part = type => parts.find(x => x.type === type).value;
    return part('year') + '-' + part('month') + '-' + part('day');
  }
  function quality(bars, headerCodes) {
    const counts = {};
    for (const code of headerCodes) counts[code] = (counts[code] || 0) + 1;
    for (const bar of bars) for (const code of bar.codes) counts[code] = (counts[code] || 0) + 1;
    const codes = sorted(Object.keys(counts)), ordered = {};
    for (const code of codes) ordered[code] = counts[code];
    return {codes, counts: ordered};
  }
  function headerCodes(series) {
    const codes = [];
    if (series.delay_status === 'UNKNOWN') codes.push('DELAY_UNKNOWN');
    if (FALLBACK_PROVIDERS.includes(series.provider)) codes.push('PROVIDER_FALLBACK');
    return codes;
  }
  function finish(bars) {
    let lastComplete = -1;
    bars.forEach((b, i) => { if (b.session_status === 'COMPLETE') lastComplete = i; });
    bars.forEach((bar, i) => {
      bar.index = i;
      const codes = bar.codes.filter(c => c !== 'NON_COMPLETE_IN_HISTORY');
      if (bar.state === 'PROVISIONAL' && i < lastComplete) codes.push('NON_COMPLETE_IN_HISTORY');
      bar.codes = uniqSorted(codes);
    });
    return bars;
  }
  function normalize(history) {
    if (!history || typeof history !== 'object' || Array.isArray(history) || history.schema !== SOURCE_SCHEMA || history.interval !== '1d'
      || history.basis !== 'RAW_CLOSE' || !Array.isArray(history.bars) || typeof history.timezone !== 'string' || typeof history.symbol !== 'string') fail('CHART_BARS_INPUT_INVALID');
    try { new Intl.DateTimeFormat('en-CA', {timeZone: history.timezone}); } catch (_) { fail('CHART_BARS_INPUT_INVALID'); }
    const bars = []; let previous = 0;
    for (const raw of history.bars) {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw) || !Number.isSafeInteger(raw.timestamp) || raw.timestamp <= previous || !STATUSES.includes(raw.session_status)) fail('CHART_BARS_INPUT_INVALID');
      previous = raw.timestamp;
      for (const key of ['open', 'high', 'low', 'close', 'adjusted_close', 'volume']) {
        const value = get(raw, key);
        if (value !== null && (!finite(value) || (key === 'volume' ? value < 0 : value <= 0))) fail('CHART_BARS_INPUT_INVALID');
      }
      let sd = get(raw, 'session_date');
      if (sd !== null && !day(sd)) fail('CHART_BARS_INPUT_INVALID');
      sd = sd || sessionDate(raw.timestamp, history.timezone);
      const codes = [], complete = raw.session_status === 'COMPLETE';
      if (!complete) codes.push('PROVISIONAL_SESSION');
      const o = get(raw, 'open'), h = get(raw, 'high'), l = get(raw, 'low'), c = get(raw, 'close'), v = get(raw, 'volume');
      let present = [o, h, l, c].every(x => x !== null);
      if (!present) codes.push('OHLC_MISSING');
      else if (!(l <= h && l <= o && o <= h && l <= c && c <= h)) { present = false; codes.push('OHLC_INCONSISTENT'); }
      if (v === null) codes.push('VOLUME_MISSING');
      bars.push({index: 0, session_date: sd, timestamp: raw.timestamp, open: o, high: h, low: l, close: c, adjusted_close: get(raw, 'adjusted_close'), volume: v,
        session_status: raw.session_status, state: complete ? 'COMPLETE' : 'PROVISIONAL', ohlc: present ? 'PRESENT' : 'MISSING', volume_state: v === null ? 'MISSING' : 'REPORTED', codes});
    }
    const seen = new Map();
    for (const bar of bars) seen.set(bar.session_date, (seen.get(bar.session_date) || 0) + 1);
    for (const bar of bars) if (seen.get(bar.session_date) > 1) { bar.ohlc = 'MISSING'; bar.volume_state = 'MISSING'; bar.codes.push('DUPLICATE_SESSION_DATE'); }
    for (let i = 1; i < bars.length; i++) if (bars[i - 1].session_date > bars[i].session_date) fail('CHART_BARS_INPUT_INVALID');
    const series = {schema: SCHEMA, source_schema: SOURCE_SCHEMA, timeframe: 'D', symbol: history.symbol, provider: get(history, 'provider'), exchange: get(history, 'exchange'),
      currency: get(history, 'currency'), timezone: history.timezone, read_at: get(history, 'read_at'), delay_status: get(history, 'delay_status'), interval: '1d', basis: 'RAW_CLOSE', bars: finish(bars)};
    series.quality = quality(series.bars, headerCodes(series));
    return series;
  }
  function weekday(d) { return (new Date(d + 'T00:00:00Z').getUTCDay() + 6) % 7; } // Monday 0 ... Sunday 6
  function weekStart(d) { return new Date(Date.parse(d + 'T00:00:00Z') - weekday(d) * 86400000).toISOString().slice(0, 10); }
  function corporateActions(value) {
    if (value === null || value === undefined) return {status: 'NOT_PROVIDED', splits: []};
    if (typeof value !== 'object' || Array.isArray(value) || !['NOT_PROVIDED', 'LOOKUP_FAILED', 'AVAILABLE'].includes(value.status)) return {status: 'INVALID', splits: []};
    if (value.status !== 'AVAILABLE') return {status: value.status, splits: []};
    const start = day(value.covered_from), end = day(value.covered_to), events = value.events;
    if (!start || !end || start > end || !Array.isArray(events)) return {status: 'INVALID', splits: []};
    const splits = [];
    for (const event of events) {
      if (!event || typeof event !== 'object' || Array.isArray(event) || !['SPLIT', 'DIVIDEND'].includes(event.kind) || !day(event.effective_date)) return {status: 'INVALID', splits: []};
      if (event.kind === 'SPLIT') splits.push(event.effective_date);
    }
    return {status: 'AVAILABLE', covered_from: start, covered_to: end, splits: uniqSorted(splits)};
  }
  function actionsOf(value) { return value && typeof value === 'object' && !Array.isArray(value) && own(value, 'splits') && own(value, 'status') ? value : corporateActions(value); }
  function continuity(actions, start, end) {
    actions = actionsOf(actions);
    if (actions.status !== 'AVAILABLE') {
      const sub = {NOT_PROVIDED: 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED', LOOKUP_FAILED: 'CORPORATE_ACTION_LOOKUP_FAILED'}[actions.status] || 'CORPORATE_ACTION_EVENTS_INVALID';
      return {state: 'NOT_JUDGEABLE', reason_codes: ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', sub]};
    }
    if (start < actions.covered_from || end > actions.covered_to) return {state: 'NOT_JUDGEABLE', reason_codes: ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_COVERAGE_GAP']};
    if (actions.splits.some(d => start < d && d <= end)) return {state: 'NOT_JUDGEABLE', reason_codes: ['CORPORATE_ACTION_IN_WINDOW']};
    return {state: 'CONFIRMED', reason_codes: []};
  }
  function weekly(series, actions) {
    if (!series || series.schema !== SCHEMA || series.timeframe !== 'D') fail('CHART_BARS_INPUT_INVALID');
    const splits = actionsOf(actions).splits, groups = new Map();
    for (const bar of series.bars) { const key = weekStart(bar.session_date); if (!groups.has(key)) groups.set(key, []); groups.get(key).push(bar); }
    const keys = sorted(groups.keys()), out = [];
    keys.forEach((key, n) => {
      const days = groups.get(key), codes = [];
      let later = null;
      for (const k of keys.slice(n + 1)) { later = groups.get(k).find(b => b.state === 'COMPLETE') || null; if (later) break; }
      const weekend = days.some(b => weekday(b.session_date) >= 5), friday = days.find(b => weekday(b.session_date) === 4) || null;
      let state, knownAt;
      if (days.some(b => b.state !== 'COMPLETE')) { state = 'PROVISIONAL'; knownAt = null; codes.push('PROVISIONAL_DAILY_IN_WEEK'); }
      else if (friday && !weekend) { state = 'COMPLETE'; knownAt = friday.session_date; }
      else if (later) { state = 'COMPLETE'; knownAt = later.session_date; }
      else { state = 'PROVISIONAL'; knownAt = null; codes.push('WEEK_NOT_CLOSED'); }
      if (weekend) codes.push('WEEKEND_SESSION');
      const first = days[0].session_date, last = days[days.length - 1].session_date, straddles = splits.some(d => first < d && d <= last);
      const allOhlc = days.every(b => b.ohlc === 'PRESENT'), allVolume = days.every(b => b.volume_state === 'REPORTED');
      const ohlcOk = allOhlc && !weekend && !straddles, volumeOk = allVolume && !straddles;
      if (!allOhlc) codes.push('OHLC_MISSING_IN_WEEK');
      if (!allVolume) codes.push('VOLUME_MISSING_IN_WEEK');
      if (straddles) codes.push('CORPORATE_ACTION_IN_BAR');
      out.push({index: n, week_start: key, first_session: first, last_session: last, session_count: days.length, timestamp: days[days.length - 1].timestamp,
        open: ohlcOk ? days[0].open : null, high: ohlcOk ? Math.max(...days.map(b => b.high)) : null, low: ohlcOk ? Math.min(...days.map(b => b.low)) : null,
        close: ohlcOk ? days[days.length - 1].close : null, volume: volumeOk ? days.reduce((a, b) => a + b.volume, 0) : null,
        state, known_at: knownAt, ohlc: ohlcOk ? 'PRESENT' : 'MISSING', volume_state: volumeOk ? 'REPORTED' : 'MISSING', codes: uniqSorted(codes)});
    });
    const result = {};
    for (const [k, v] of Object.entries(series)) if (!['bars', 'quality', 'timeframe'].includes(k)) result[k] = v;
    result.timeframe = 'W'; result.bars = out; result.quality = quality(out, headerCodes(series));
    return result;
  }
  // prefer 'INCOMING' builds the separate revised-data view (§8.6); the official history keeps the default view.
  function merge(previous, incoming, prefer = 'PREVIOUS') {
    if (!['PREVIOUS', 'INCOMING'].includes(prefer)) fail('CHART_BARS_INPUT_INVALID');
    for (const s of [previous, incoming]) if (!s || s.schema !== SCHEMA || s.timeframe !== 'D') fail('CHART_BARS_INPUT_INVALID');
    if (previous.symbol !== incoming.symbol || previous.timezone !== incoming.timezone) fail('CHART_BARS_MERGE_MISMATCH');
    const held = new Map(previous.bars.map(b => [b.session_date, b])), revised = [];
    for (const bar of incoming.bars) {
      const old = held.get(bar.session_date);
      if (!old || old.state !== 'COMPLETE') { held.set(bar.session_date, {...bar, codes: bar.codes.filter(c => c !== 'PRICE_REVISED')}); continue; }
      if (bar.state !== 'COMPLETE' || COMPARED.some(k => old[k] !== bar[k])) { revised.push(bar.session_date); const kept = prefer === 'INCOMING' ? bar : old; held.set(bar.session_date, {...kept, codes: uniqSorted([...kept.codes, 'PRICE_REVISED'])}); }
    }
    const bars = sorted(held.keys()).map(d => ({...held.get(d), codes: [...held.get(d).codes]}));
    const merged = {};
    for (const [k, v] of Object.entries(previous)) if (!['bars', 'quality'].includes(k)) merged[k] = v;
    merged.read_at = incoming.read_at; merged.bars = finish(bars);
    merged.quality = quality(merged.bars, headerCodes(merged).concat(previous.provider !== incoming.provider ? ['PROVIDER_MIXED'] : []));
    return {series: merged, revised: sorted(revised)};
  }
  function sessionSetMismatch(series, storeDates) {
    const days = uniqSorted(series.bars.filter(b => b.state === 'COMPLETE').map(b => b.session_date)), store = uniqSorted(storeDates.filter(d => day(d)));
    const none = {state: 'NOT_AVAILABLE', reason_codes: ['NO_OVERLAP'], missing_in_bars: 0, missing_in_store: 0};
    if (!days.length || !store.length) return none;
    const lo = days[0] > store[0] ? days[0] : store[0], hi = days[days.length - 1] < store[store.length - 1] ? days[days.length - 1] : store[store.length - 1];
    if (lo > hi) return none;
    const a = new Set(days.filter(d => lo <= d && d <= hi)), b = new Set(store.filter(d => lo <= d && d <= hi));
    const missingInBars = [...b].filter(d => !a.has(d)).length, missingInStore = [...a].filter(d => !b.has(d)).length, mismatch = Boolean(missingInBars || missingInStore);
    return {state: mismatch ? 'MISMATCH' : 'MATCH', reason_codes: mismatch ? ['SESSION_SET_MISMATCH'] : [], missing_in_bars: missingInBars, missing_in_store: missingInStore};
  }
  return Object.freeze({SCHEMA, normalize, weekly, merge, corporateActions, continuity, sessionSetMismatch, sessionDate});
});
