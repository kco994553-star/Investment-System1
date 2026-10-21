/* Technical chart workbench (P1-8, P1-9 subset). Display only: no orders, no signals, no scores.
   Real prices arrive only at run time from PrivateHistory (private Worker, RAM only) through update().
   The built-in preview uses generated synthetic bars and is always labelled as such.
   Weekly bars come only from ChartBars (chart-bars.js, lane B1); this file never aggregates bars.
   Patterns come only from PatternEngine with pattern-rules/1 (pattern-engine.js); official runs go to PatternHistory
   (RAM, append only). This file never detects pivots, zones, boxes or double bottoms/tops and never computes ATR.
   User-written notes (3.3, chart-annotation/1) and scenarios (3.1.3, chart-scenario/1) are a separate layer: they are
   stored only through a swappable user store (default: this browser), never touch PatternHistory or any record of results,
   and are always labelled "사용자 작성".
   Display settings hold toggles only (no prices). User-written objects hold the user's own time/price coordinates on this
   device only (DRAW-STORE option (a), labelled "이 기기에만 저장"). Nothing here changes official detection.
   Owner storage policy 2026-10-20 item 6: only these user-drawn anchor coordinates may be kept in this browser; no supplier
   quote or price series is ever stored or exported here. User objects can be exported to / imported from a file on this device
   (strict fields, merged without duplicates) and ride in the opt-in device backup section. A failed save (quota reached or
   storage blocked) never removes what is already stored; the screen says so and points to the export. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ChartWorkbench = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SETTINGS_KEY = 'investment.web.v1.chart-display-settings';
  const SETTINGS_SCHEMA = 'chart-display-settings/1';
  const INDICATOR_GROUPS = Object.freeze({
    SMA: Object.freeze([['SMA_5', 'price', 0], ['SMA_20', 'price', 1], ['SMA_60', 'price', 2], ['SMA_120', 'price', 3], ['SMA_240', 'price', 4]]),
    EMA: Object.freeze([['EMA_20', 'price', 5]]),
    BOLL: Object.freeze([['BOLL_UPPER_20_2', 'price', 4], ['BOLL_MIDDLE_20', 'price', 4], ['BOLL_LOWER_20_2', 'price', 4]]),
    RSI: Object.freeze([['RSI_14', 'rsi', 0]]),
    MACD: Object.freeze([['MACD_12_26', 'macd', 0], ['MACD_SIGNAL_9', 'macd', 1], ['MACD_HISTOGRAM_12_26_9', 'macd', 0, 'histogram']]),
    ATR: Object.freeze([['ATR_14', 'atr', 2]])
  });
  const DEFAULT_SETTINGS = Object.freeze({schema: SETTINGS_SCHEMA, mode: 'long', renderer: 'lwc', indicators: Object.freeze({SMA: true, EMA: false, BOLL: false, RSI: false, MACD: false, ATR: false}),
    patterns: Object.freeze({ZONES: true, BOX: true, DOUBLE: true})});
  const SYNTHETIC_LABEL = Object.freeze(['합성 자료 · 미리보기 · 실데이터 검증 아님', 'Synthetic data · Preview · Not validated on real data']);
  const NOTICE_TEXT = 'TradingView Lightweight Charts™ Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/';
  const active = new Set();

  /* ---------- settings (display toggles only) ---------- */

  function readSettings(storage) {
    let parsed = null;
    try { const raw = storage && storage.getItem(SETTINGS_KEY); parsed = raw ? JSON.parse(raw) : null; } catch (_) { parsed = null; }
    const out = {schema: SETTINGS_SCHEMA, mode: DEFAULT_SETTINGS.mode, renderer: DEFAULT_SETTINGS.renderer, indicators: {...DEFAULT_SETTINGS.indicators}, patterns: {...DEFAULT_SETTINGS.patterns}};
    if (parsed && parsed.schema === SETTINGS_SCHEMA) {
      if (['long', 'swing'].includes(parsed.mode)) out.mode = parsed.mode;
      if (['lwc', 'svg'].includes(parsed.renderer)) out.renderer = parsed.renderer;
      for (const group of ['indicators', 'patterns']) if (parsed[group] && typeof parsed[group] === 'object') for (const key of Object.keys(out[group])) if (typeof parsed[group][key] === 'boolean') out[group][key] = parsed[group][key];
    }
    return out;
  }
  function writeSettings(storage, settings) {
    try { storage.setItem(SETTINGS_KEY, JSON.stringify({schema: SETTINGS_SCHEMA, mode: settings.mode, renderer: settings.renderer, indicators: settings.indicators, patterns: settings.patterns || DEFAULT_SETTINGS.patterns})); return true; } catch (_) { return false; }
  }

  /* ---------- bars: daily view and the ChartBars weekly boundary ---------- */

  function sessionDate(timestamp, timezone) {
    const parts = new Intl.DateTimeFormat('en-CA', {timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(timestamp * 1000)), get = type => parts.find(x => x.type === type).value;
    return get('year') + '-' + get('month') + '-' + get('day');
  }
  // Same session-date rule as PrivateTrades.markers: provider session label, else the exchange-local date.
  function dailyView(raw, timezone) {
    return raw.map(bar => ({time: typeof bar.session_date === 'string' ? bar.session_date : sessionDate(bar.timestamp, timezone || 'UTC'),
      open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume, status: bar.session_status}));
  }

  /* Weekly boundary: lane B1 chart-bars.js (ChartBars, schema chart-bars/1, rule W1).
       ChartBars.normalize(private-history/1) -> daily series; ChartBars.weekly(series, actions) -> weekly series
       whose bars carry week_start, first_session, last_session, open..volume (null when missing) and state.
     This is the only place that reads ChartBars output. No aggregation happens in this file.
     Split events are not delivered yet (P1-W), so actions stay null (NOT_PROVIDED). */
  function historyOf(data) {
    return {schema: 'private-history/1', interval: '1d', basis: 'RAW_CLOSE', delay_status: 'UNKNOWN', symbol: data.symbol || '', provider: data.provider || '',
      currency: data.currency || '', timezone: data.timezone || 'UTC', read_at: data.readAt || '', bars: data.bars};
  }
  function weeklyView(view, data) {
    const api = view.ChartBars;
    if (!api || typeof api.normalize !== 'function' || typeof api.weekly !== 'function') return {code: 'WEEKLY_BARS_MODULE_PENDING', bars: null};
    let result;
    try { result = api.weekly(api.normalize(historyOf(data)), null); } catch (_) { return {code: 'WEEKLY_BARS_FAILED', bars: null}; }
    const list = result && Array.isArray(result.bars) ? result.bars : null;
    if (!list || !list.length) return {code: 'WEEKLY_BARS_FAILED', bars: null};
    return {code: 'READY', bars: list.map(w => ({time: w.week_start, start: w.first_session, end: w.last_session, open: w.open, high: w.high, low: w.low, close: w.close, volume: w.volume, status: w.state === 'COMPLETE' ? 'COMPLETE' : 'PROVISIONAL'}))};
  }
  // Price-basis continuity of the shown window from ChartBars (display reason codes only).
  function continuityCodes(view, bars) {
    const api = view.ChartBars;
    if (!api || typeof api.continuity !== 'function' || !bars.length) return ['PRICE_BASIS_CONTINUITY_UNCONFIRMED'];
    try { const r = api.continuity(null, bars[0].start, bars[bars.length - 1].end); return r && Array.isArray(r.reason_codes) && r.reason_codes.length ? r.reason_codes : ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']; }
    catch (_) { return ['PRICE_BASIS_CONTINUITY_UNCONFIRMED']; }
  }

  /* ---------- patterns: engine input and result reading (no detection here) ---------- */

  const SYNTHETIC_PATTERN_LABEL = Object.freeze(['합성 자료 · 기능 확인용 · 실데이터 검증 아님', 'Synthetic data · Function check · Not validated on real data']);
  const PATTERN_NAMES = Object.freeze({BOX_BREAKOUT_UP: ['박스 상향 돌파', 'Box breakout'], BOX_BREAKDOWN: ['박스 하향 이탈', 'Box breakdown'], DOUBLE_BOTTOM: ['이중 바닥', 'Double bottom'],
    DOUBLE_TOP: ['이중 천장', 'Double top'], SUPPORT_RESISTANCE_ZONE: ['지지·저항 구간', 'Support/resistance zone']});
  const STATE_NAMES = Object.freeze({FORMED: ['형성 완료 · 확인 대기', 'Formed · awaiting confirmation'], CONFIRMED: ['확인', 'Confirmed'], FAILED: ['확인 후 실패', 'Failed after confirmation'],
    INVALIDATED: ['무효화', 'Invalidated'], EXPIRED: ['만료', 'Expired'], NOT_JUDGEABLE: ['판정 불가', 'Not judgeable'], ACTIVE: ['유효 구간', 'Active zone'], BROKEN: ['구간 이탈', 'Zone broken'], SUPERSEDED: ['대체됨', 'Superseded']});
  const PATTERN_GROUP = Object.freeze({BOX_BREAKOUT_UP: 'BOX', BOX_BREAKDOWN: 'BOX', DOUBLE_BOTTOM: 'DOUBLE', DOUBLE_TOP: 'DOUBLE', SUPPORT_RESISTANCE_ZONE: 'ZONES'});
  // User-settings exploration grid: the sensitivity sets that pattern-rules/1 lists per parameter (design §8.8).
  // Values outside these sets are not offered. DB_SEP_MAX follows BOX_MAX_BARS (§8.8).
  const EXPLORE_GRID = Object.freeze([
    ['PIVOT_K', {D: [2, 3, 5], W: [1, 2, 3]}, ['피벗 좌우 봉 수', 'Pivot bars each side']],
    ['SWING_MIN_ATR', [0.5, 1, 1.5, 2], ['스윙 최소 진폭 (ATR 배)', 'Swing minimum (×ATR)']],
    ['ZONE_LOOKBACK', {D: [120, 250, 500], W: [52, 104, 208]}, ['구간 조회 창 (봉)', 'Zone lookback (bars)']],
    ['ZONE_TOL_ATR', [0.25, 0.5, 0.75, 1], ['구간 허용오차 (ATR 배)', 'Zone tolerance (×ATR)']],
    ['ZONE_MIN_TOUCHES', [2, 3], ['구간 최소 접촉', 'Zone minimum touches']],
    ['BREAK_BUFFER_ATR', [0, 0.25, 0.5], ['돌파 여유 (ATR 배)', 'Break buffer (×ATR)']],
    ['BOX_MIN_BARS', {D: [10, 15, 20], W: [4, 6, 8]}, ['박스 최소 길이 (봉)', 'Box minimum length (bars)']],
    ['BOX_MAX_BARS', {D: [60, 120, 250], W: [26, 52, 104]}, ['박스 최대 길이 (봉) · 이중 최대 간격도 같음', 'Box maximum length (bars) · also double max separation']],
    ['BOX_HEIGHT_ATR.min', [1.5, 2, 3], ['박스 높이 최소 (ATR 배)', 'Box height minimum (×ATR)']],
    ['BOX_HEIGHT_ATR.max', [8, 10, 15], ['박스 높이 최대 (ATR 배)', 'Box height maximum (×ATR)']],
    ['FAIL_WINDOW', {D: [3, 5, 10], W: [1, 2, 3]}, ['실패 창 (봉)', 'Failure window (bars)']],
    ['DB_TOL_ATR', [0.5, 0.75, 1, 1.5], ['이중 높이 차 허용 (ATR 배)', 'Double height tolerance (×ATR)']],
    ['DB_SEP_MIN', {D: [5, 10, 20], W: [3, 4, 6]}, ['이중 최소 간격 (봉)', 'Double minimum separation (bars)']],
    ['DB_DEPTH_ATR', [1.5, 2, 3], ['이중 깊이 (ATR 배)', 'Double depth (×ATR)']],
    ['VOL_AVG_N', {D: [10, 20, 50], W: [5, 10, 20]}, ['거래량 평균 봉 수 (참고)', 'Volume average bars (note)']],
    ['VOL_MULT', [1, 1.5, 2], ['거래량 배수 (참고)', 'Volume multiple (note)']]
  ]);
  const tfKey = timeframe => (timeframe === 'weekly' ? 'W' : 'D');
  function paramValue(params, name, tf) {
    const [head, sub] = name.split('.'), value = params[head];
    if (sub) return value[sub];
    return value && typeof value === 'object' ? value[tf] : value;
  }
  function gridOptions(spec, tf) { return Array.isArray(spec) ? spec : spec[tf]; }
  // Changed parameters -> a full pattern-rules/1 params object (the shipped defaults are never modified).
  function applyChanges(params, changes, tf) {
    const out = JSON.parse(JSON.stringify(params)), diff = [];
    for (const [name, spec] of EXPLORE_GRID) {
      if (!Object.prototype.hasOwnProperty.call(changes, name)) continue;
      const value = changes[name];
      if (!gridOptions(spec, tf).includes(value)) throw new Error('PATTERN_SETTING_OUT_OF_GRID');
      const before = paramValue(params, name, tf);
      if (value === before) continue;
      const [head, sub] = name.split('.');
      if (sub) out[head][sub] = value; else if (out[head] && typeof out[head] === 'object') out[head][tf] = value; else out[head] = value;
      if (name === 'BOX_MAX_BARS') out.DB_SEP_MAX[tf] = value;
      diff.push({name, timeframe: sub || !(params[head] && typeof params[head] === 'object') ? null : tf, from: before, to: value});
    }
    return {params: out, diff};
  }
  // Synthetic bars are generated without splits; their corporate-action record says so explicitly (function check only).
  function syntheticActions(series) {
    const bars = series.bars;
    return {status: 'AVAILABLE', covered_from: bars[0].first_session || bars[0].session_date, covered_to: bars[bars.length - 1].last_session || bars[bars.length - 1].session_date, events: []};
  }
  // Minimum bars per item (design §7.6) for the rules in use.
  function minBars(params, tf) {
    const k = paramValue(params, 'PIVOT_K', tf);
    return [['ATR14', 15], ['PIVOT', 2 * k + 1], ['ZONE', 15], ['BOX', 15 + paramValue(params, 'BOX_MIN_BARS', tf) + k], ['DOUBLE', 15 + paramValue(params, 'DB_SEP_MIN', tf) + 2 * k], ['VOLUME_NOTE', paramValue(params, 'VOL_AVG_N', tf)]];
  }
  // Display view of one engine result: signals and zones (pivots are inputs, not shown as objects).
  function patternObjects(result) {
    const groups = new Map();
    for (const tr of result.transitions) {
      if (tr.object_kind === 'PIVOT') continue;
      if (!groups.has(tr.object_id)) groups.set(tr.object_id, []);
      groups.get(tr.object_id).push(tr);
    }
    return [...groups.values()].map(list => {
      const first = list[0], last = list[list.length - 1], confirm = list.find(t => t.event === 'CONFIRMED') || null;
      const judgeable = first.event !== 'NOT_JUDGEABLE' && !!first.judgement && first.judgement.state === 'CONFIRMED';
      const ended = ['FAILED', 'INVALIDATED', 'EXPIRED', 'NOT_JUDGEABLE', 'BROKEN', 'SUPERSEDED'].includes(last.state) || last.event === 'OBSERVATION_ENDED';
      return {id: first.object_id, kind: first.object_kind, pattern: first.pattern, state: last.state, event: last.event, knownAt: last.known_at, knownIndex: last.known_index,
        startIndex: first.anchor_index, anchorAt: first.anchor_at, formedAt: first.known_at, formedIndex: first.known_index, detail: first.detail || {}, confirm, ended,
        observationEnded: list.some(t => t.event === 'OBSERVATION_ENDED'), judgeable, reasons: (last.judgement && last.judgement.reason_codes) || [],
        ruleVersion: first.rule_version, paramsSha: first.params_sha256};
    });
  }
  async function hashParams(view, canonical) {
    if (!view.crypto || !view.crypto.subtle || typeof view.TextEncoder !== 'function') throw new Error('USER_SETTINGS_HASH_UNAVAILABLE');
    const digest = await view.crypto.subtle.digest('SHA-256', new view.TextEncoder().encode(canonical));
    return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /* ---------- user-written objects: notes (3.3) and scenarios (3.1.3) ---------- */

  const USER_KEY = 'investment.web.v1.chart-user-objects', USER_SCHEMA = 'chart-user-objects/1', USER_LIMIT = 500, TEXT_LIMIT = 500, USER_IMPORT_MAX_BYTES = 16 * 1024 * 1024;
  const USER_LABEL = Object.freeze(['사용자 작성', 'User-written']);
  const DIRECTIONS = Object.freeze({UP: ['상승', 'Up', '↑'], SIDEWAYS: ['횡보', 'Sideways', '→'], DOWN: ['하락', 'Down', '↓']});
  const NOTE_KINDS = Object.freeze({LINE: ['선', 'Line'], RANGE: ['구간', 'Range'], MEMO: ['메모', 'Memo']});
  const isDate = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v + 'T00:00:00Z'));
  const isPrice = v => typeof v === 'number' && Number.isFinite(v) && v > 0;
  const isText = v => typeof v === 'string' && v.length <= TEXT_LIMIT;
  const isId = v => typeof v === 'string' && /^u-[a-z0-9]{6,32}$/.test(v);
  // Exact field sets: a user object carries the user's own anchors and words only. Anything else (a price series, quote fields,
  // OHLC, volume, a supplier name...) makes the object invalid, so it can be neither imported nor restored.
  const NOTE_FIELDS = ['schema', 'id', 'kind', 'symbol', 'interval', 'price_basis', 'author', 'points', 'text', 'created_at', 'updated_at'];
  const SCENARIO_FIELDS = ['schema', 'id', 'symbol', 'interval', 'price_basis', 'author', 'text', 'anchor_time', 'created_at', 'updated_at', 'horizon', 'direction', 'levels', 'condition', 'invalidation', 'invalidation_price'];
  const onlyFields = (o, keys) => !!o && typeof o === 'object' && !Array.isArray(o) && Object.keys(o).every(k => keys.includes(k));
  // Anchors (chart-annotation/1): listing symbol, interval D/W, price basis, time/price points.
  function validUserObject(o) {
    if (!o || typeof o !== 'object' || Array.isArray(o) || !onlyFields(o, o.schema === 'chart-scenario/1' ? SCENARIO_FIELDS : NOTE_FIELDS) || !isId(o.id) || typeof o.symbol !== 'string' || !/^[A-Z0-9.\-]{1,16}$/.test(o.symbol) || !['D', 'W'].includes(o.interval) || o.price_basis !== 'RAW_CLOSE' || o.author !== 'USER'
      || !isText(o.text || '') || !isDate(String(o.created_at || '').slice(0, 10)) || !isDate(String(o.updated_at || '').slice(0, 10))) return false;
    if (o.schema === 'chart-annotation/1') {
      if (!NOTE_KINDS[o.kind] || !Array.isArray(o.points) || o.points.length !== (o.kind === 'MEMO' ? 1 : 2) || !o.points.every(pt => onlyFields(pt, ['time', 'price']) && isDate(pt.time) && isPrice(pt.price))) return false;
      return true;
    }
    if (o.schema === 'chart-scenario/1') {
      return !!DIRECTIONS[o.direction] && ['long', 'swing'].includes(o.horizon) && Array.isArray(o.levels) && o.levels.length >= 1 && o.levels.length <= 3
        && o.levels.every(l => onlyFields(l, ['label', 'price']) && isPrice(l.price) && isText(l.label || '') && (l.label || '').length <= 40) && isText(o.condition || '') && isText(o.invalidation || '')
        && (o.invalidation_price === null || isPrice(o.invalidation_price)) && isDate(o.anchor_time);
    }
    return false;
  }
  // Storage adapter (DRAW-STORE option (a): this browser only). Another adapter with the same three methods
  // (load / save / clear) can replace it later, e.g. option (b); nothing here talks to the network.
  // Nothing is dropped silently: every valid stored object is loaded (USER_LIMIT only limits adding new ones), stored entries
  // this version cannot read are written back unchanged on the next save, and a stored value that cannot be read at all (broken
  // JSON, unknown schema) is never overwritten — save() refuses until the user clears it. save() returns false when nothing was
  // written (quota reached, storage blocked); the stored value is then exactly what it was before.
  function createDeviceUserStore(storage) {
    let kept = [], locked = false;
    return Object.freeze({
      kind: 'THIS_BROWSER',
      load() {
        let raw = null; kept = []; locked = false;
        try { raw = storage ? storage.getItem(USER_KEY) : null; } catch (_) { locked = true; return {code: 'STORAGE_UNAVAILABLE', items: [], unreadable: 0}; }
        if (raw === null) return {code: 'EMPTY', items: [], unreadable: 0};
        let parsed = null; try { parsed = JSON.parse(raw); } catch (_) { locked = true; return {code: 'STORE_INVALID', items: [], unreadable: 0}; }
        if (!parsed || parsed.schema !== USER_SCHEMA || !Array.isArray(parsed.items)) { locked = true; return {code: 'STORE_INVALID', items: [], unreadable: 0}; }
        const items = parsed.items.filter(validUserObject);
        kept = parsed.items.filter(o => !validUserObject(o));
        return {code: kept.length ? 'PARTLY_INVALID' : 'LOADED', items, unreadable: kept.length};
      },
      save(items) {
        if (locked || !storage) return false;
        try { if (items.length + kept.length) storage.setItem(USER_KEY, JSON.stringify({schema: USER_SCHEMA, items: [...items, ...kept]})); else storage.removeItem(USER_KEY); return true; } catch (_) { return false; }
      },
      clear() { try { storage.removeItem(USER_KEY); kept = []; locked = false; return true; } catch (_) { return false; } }
    });
  }
  // Export file / backup section: {schema, items[, exported_at]}. Every item must pass validUserObject (exact fields); duplicates
  // inside the file collapse to one. Throws USER_IMPORT_INVALID otherwise; nothing is written by parsing.
  function parseUserExport(payload) {
    const bad = () => { throw new Error('USER_IMPORT_INVALID'); };
    if (!onlyFields(payload, ['schema', 'exported_at', 'items']) || payload.schema !== USER_SCHEMA || !Array.isArray(payload.items)
      || (payload.exported_at !== undefined && !(typeof payload.exported_at === 'string' && payload.exported_at.length <= 40))) bad();
    const seen = new Set(), items = [];
    for (const o of payload.items) { if (!validUserObject(o)) bad(); if (seen.has(o.id)) continue; seen.add(o.id); items.push(JSON.parse(JSON.stringify(o))); }
    return items;
  }
  // Merge without duplicates: an incoming object whose id is already present, or whose content (all but id/created/updated)
  // matches one already present, is skipped; existing objects are never replaced or removed.
  function mergeUserItems(existing, incoming) {
    const body = o => { const {id, created_at, updated_at, ...rest} = o; return JSON.stringify(rest, Object.keys(rest).sort()); };
    const ids = new Set(existing.map(o => o.id)), bodies = new Set(existing.map(body)), items = [...existing];
    let added = 0, skipped = 0;
    for (const o of incoming) { const b = body(o); if (ids.has(o.id) || bodies.has(b)) { skipped++; continue; } ids.add(o.id); bodies.add(b); items.push(o); added++; }
    return {items, added, skipped};
  }
  function newId(view) {
    const bytes = new Uint8Array(8);
    if (view.crypto && view.crypto.getRandomValues) view.crypto.getRandomValues(bytes); else for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
    return 'u-' + [...bytes].map(b => b.toString(36)).join('').slice(0, 16).padEnd(6, '0');
  }
  const roundPrice = v => Number(v.toPrecision(6));

  /* ---------- synthetic preview (generated, deterministic, never market data) ---------- */

  function syntheticHistory() {
    let seed = 20261020;
    const random = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
    const round = x => Math.round(x * 100) / 100, bars = [];
    let day = Date.UTC(2025, 0, 6), close = 100;
    while (bars.length < 320) {
      const weekday = new Date(day).getUTCDay();
      if (weekday >= 1 && weekday <= 5) {
        const open = close * (1 + (random() - 0.5) * 0.02);
        close = open * (1 + (random() - 0.5) * 0.035 + 0.004 * Math.sin(bars.length / 23));
        const high = Math.max(open, close) * (1 + random() * 0.012), low = Math.min(open, close) * (1 - random() * 0.012);
        bars.push({timestamp: day / 1000 + 52200, session_date: new Date(day).toISOString().slice(0, 10), open: round(open), high: round(high), low: round(low), close: round(close), adjusted_close: null, volume: Math.round(800000 + random() * 900000), session_status: 'COMPLETE'});
        const last = bars.at(-1); last.high = Math.max(last.high, last.open, last.close); last.low = Math.min(last.low, last.open, last.close);
      }
      day += 86400000;
    }
    bars[60].volume = null;
    Object.assign(bars[120], {open: null, high: null, low: null, close: null});
    bars.at(-1).session_status = 'IN_PROGRESS';
    return Object.freeze({symbol: 'SYNTH', provider: 'SYNTHETIC', timezone: 'UTC', currency: '', readAt: '', bars});
  }

  /* ---------- helpers ---------- */

  function words(state, ko, en) { return state.locale === 'en-US' ? en : ko; }
  function node(doc, tag, attrs = {}, text) {
    const el = doc.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) if (value !== undefined && value !== null) el.setAttribute(key, String(value));
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function fmt(state, value) { return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString(state.locale || 'ko-KR', {maximumSignificantDigits: 6}) : '—'; }
  function fmtVolume(state, value) { return typeof value === 'number' && Number.isFinite(value) ? Math.round(value).toLocaleString(state.locale || 'ko-KR') : words(state, '결측', 'missing'); }
  function signed(state, value, digits) { return (value > 0 ? '+' : '') + value.toLocaleString(state.locale || 'ko-KR', {maximumFractionDigits: digits}); }
  function statusWord(state, bar) { return bar.complete ? words(state, '확정', 'complete') : words(state, '잠정', 'provisional'); }

  function lines(state) {
    if (state.timeframe !== 'daily' || !state.data || !state.data.indicators || !Array.isArray(state.data.indicators.indicators)) return [];
    const byId = new Map(state.data.indicators.indicators.map(item => [item.indicator_id, item.values])), out = [];
    for (const [group, specs] of Object.entries(INDICATOR_GROUPS)) {
      if (!state.settings.indicators[group]) continue;
      for (const [id, pane, tone, type] of specs) if (byId.has(id)) out.push({id, pane, tone, type: type || 'line', values: byId.get(id)});
    }
    return out;
  }

  /* ---------- painting ---------- */

  function setAttr(state, name, value) { state.root.setAttribute(name, String(value)); }

  function paintRange(state) {
    const span = state.renderer && state.bars.length ? state.renderer.getVisibleRange() : null;
    const from = span ? state.bars[span.from].time : '', to = span ? state.bars[span.to].time : '';
    setAttr(state, 'data-visible-from', from); setAttr(state, 'data-visible-to', to);
    const frame = state.timeframe === 'weekly' ? words(state, '주봉', 'weekly') : words(state, '일봉', 'daily');
    state.chartBox.setAttribute('aria-label', [state.symbol || words(state, '자료 없음', 'No data'), frame, from && to ? words(state, '보이는 기간 ', 'visible ') + from + ' ~ ' + to : '', words(state, '선택 패턴 없음', 'no pattern selected')].filter(Boolean).join(' · '));
  }

  function readoutText(state, index) {
    const bar = state.bars[index];
    if (!bar) return '';
    const ohlc = bar.ohlc ? words(state, '시가 ', 'O ') + fmt(state, bar.open) + ' · ' + words(state, '고가 ', 'H ') + fmt(state, bar.high) + ' · ' + words(state, '저가 ', 'L ') + fmt(state, bar.low) + ' · ' + words(state, '종가 ', 'C ') + fmt(state, bar.close) : words(state, 'OHLC 결측', 'OHLC missing');
    const span = bar.start !== bar.end ? ' (' + bar.start + ' ~ ' + bar.end + ')' : '';
    return bar.time + span + ' · ' + ohlc + ' · ' + words(state, '거래량 ', 'Vol ') + fmtVolume(state, bar.volume) + ' · ' + statusWord(state, bar);
  }

  function paintReadout(state, index, source) {
    state.cursor = typeof index === 'number' ? index : null;
    const text = state.cursor === null ? words(state, '차트 위를 가리키거나 길게 누르면 봉 값이 여기에 고정 표시됩니다.', 'Point at the chart or long-press to pin bar values here.') : readoutText(state, state.cursor);
    state.readout.textContent = text;
    state.readout.dataset.tracking = source === 'touch' ? 'touch' : source === 'keyboard' ? 'keyboard' : source === 'pointer' ? 'pointer' : 'off';
    if (state.cursor !== null) state.readout.dataset.index = String(state.cursor); else delete state.readout.dataset.index;
    if (source === 'keyboard' && state.cursor !== null) state.live.textContent = text;
  }

  function paintMeasure(state) {
    const m = state.measure;
    setAttr(state, 'data-measure-state', !state.measuring ? 'off' : m ? 'done' : state.measureStart ? 'first-point' : 'armed');
    if (!state.measuring) { state.measureOut.textContent = words(state, '측정 꺼짐 · 측정은 두 점 사이 값만 보여 줍니다(신호 아님).', 'Measure off · Shows values between two points only (not a signal).'); return; }
    if (!m) { state.measureOut.textContent = state.measureStart ? words(state, '첫 점 ', 'First point ') + state.bars[state.measureStart.index].time + ' · ' + fmt(state, state.measureStart.price) + words(state, ' · 두 번째 점을 고르세요', ' · pick the second point') : words(state, '측정 켜짐 · 차트에서 두 점을 누르세요(키보드: M).', 'Measure on · Tap two points on the chart (keyboard: M).'); return; }
    state.measureOut.textContent = words(state, '측정 · ', 'Measure · ') + m.from.time + ' ' + fmt(state, m.from.price) + ' → ' + m.to.time + ' ' + fmt(state, m.to.price)
      + ' · ' + words(state, '가격 차 ', 'diff ') + signed(state, Number(m.diff.toPrecision(6)), 6) + ' · ' + signed(state, m.percent, 2) + '% · ' + m.bars + words(state, '봉', ' bars') + ' · ' + m.days + words(state, '일', ' days')
      + ' · ' + words(state, '측정 표시만 · 신호 아님', 'measurement only · not a signal');
  }

  function paintJudgement(state) {
    // Never a signal: without confirmed price-basis continuity the window is not judged (design §7.3, Q3).
    const reasons = state.source === 'device' ? continuityCodes(state.view, state.daily) : [];
    const code = !state.data ? 'NO_DATA' : state.source === 'synthetic' ? 'SYNTHETIC_PREVIEW' : reasons.includes('CORPORATE_ACTION_IN_WINDOW') ? 'CORPORATE_ACTION_IN_WINDOW' : 'PRICE_BASIS_CONTINUITY_UNCONFIRMED';
    state.judgement.dataset.code = code;
    state.judgement.dataset.reasons = reasons.join(' ');
    state.judgement.replaceChildren(node(state.doc, 'span', {class: 'badge NOT_AVAILABLE'}, words(state, '판정 불가', 'Not judged')), state.doc.createTextNode(' ' + (reasons.length ? reasons.join(' · ') : code) + ' · ' + (
      code === 'NO_DATA' ? words(state, '차트 자료가 없습니다.', 'No chart data.')
        : code === 'SYNTHETIC_PREVIEW' ? words(state, '합성 자료는 판정하지 않습니다.', 'Synthetic data is never judged.')
          : words(state, '가격 기준 연속성(분할 이벤트, P1-W)을 확인하지 못해 패턴을 판정하지 않습니다. 패턴 엔진 연결 전입니다.', 'Price-basis continuity (split events, P1-W) is unconfirmed, so no pattern is judged. The pattern engine is not connected.'))));
  }

  function paintSource(state) {
    const doc = state.doc;
    setAttr(state, 'data-source', state.source);
    state.sourceLine.replaceChildren();
    if (state.source === 'synthetic') state.sourceLine.append(node(doc, 'strong', {'data-synthetic-label': ''}, words(state, ...SYNTHETIC_LABEL)), doc.createTextNode(' · ' + words(state, '생성한 봉 · 시장 가격 아님', 'generated bars · not market prices')));
    else if (state.source === 'device') state.sourceLine.append(doc.createTextNode(words(state, '이 기기 RAM · 비공개 일봉 · 저장 안 함 · ', 'This device RAM · private daily bars · not saved · ') + [state.data.provider, state.data.symbol, state.data.readAt ? 'read_at ' + state.data.readAt : ''].filter(Boolean).join(' · ')));
    else state.sourceLine.textContent = words(state, '자료 없음 · 위의 가격 차트에서 "가격 불러오기"를 누르거나 합성 미리보기를 고르세요.', 'No data · Press “Load prices” in the price chart above, or pick the synthetic preview.');
  }

  function paintButtons(state) {
    for (const button of state.root.querySelectorAll('[data-cw-mode]')) button.setAttribute('aria-pressed', String(button.dataset.cwMode === state.settings.mode));
    for (const button of state.root.querySelectorAll('[data-cw-timeframe]')) button.setAttribute('aria-pressed', String(button.dataset.cwTimeframe === state.timeframe));
    for (const button of state.root.querySelectorAll('[data-cw-renderer]')) button.setAttribute('aria-pressed', String(button.dataset.cwRenderer === state.settings.renderer));
    const weekly = state.root.querySelector('[data-cw-timeframe="weekly"]');
    weekly.disabled = state.weeklyCode !== 'READY';
    state.weeklyStatus.dataset.code = state.weeklyCode;
    state.weeklyStatus.textContent = state.weeklyCode === 'READY' ? '' : words(state, '주봉 · ', 'Weekly · ') + state.weeklyCode + (state.weeklyCode === 'WEEKLY_BARS_MODULE_PENDING' ? words(state, ' · 주봉 모듈(chart-bars.js) 연결 전', ' · weekly module (chart-bars.js) not connected') : '');
    const caps = state.renderer ? state.renderer.capabilities : {measure: false, zoom: false};
    state.measureButton.disabled = !caps.measure || !state.bars.length;
    state.measureButton.setAttribute('aria-pressed', String(state.measuring));
    for (const button of state.root.querySelectorAll('[data-cw-zoom]')) button.disabled = !caps.zoom || !state.bars.length;
    state.limits.hidden = !(state.renderer && state.renderer.kind === 'svg');
    state.indicatorNote.textContent = state.timeframe === 'weekly' ? words(state, '주봉에서는 보조 지표를 그리지 않습니다(TA-G3 결정 대기).', 'No indicators on weekly bars (TA-G3 decision pending).') : state.renderer && state.renderer.kind === 'svg' ? words(state, 'SVG 대체 경로는 가격 위 선(SMA·EMA·볼린저)만 그립니다.', 'The SVG fallback draws price-pane lines only (SMA, EMA, Bollinger).') : '';
  }

  function paintMode(state) {
    const doc = state.doc, panel = state.modePanel;
    panel.replaceChildren();
    panel.dataset.mode = state.settings.mode;
    if (state.settings.mode === 'long') {
      panel.append(node(doc, 'h3', {}, words(state, '장기 보유 모드', 'Long-term mode')),
        node(doc, 'p', {}, words(state, '주봉 구조를 먼저 봅니다. QGV와 나란히 볼 뿐이며, 이 차트는 QGV·TARGET·플레이북을 바꾸지 않고 입력으로도 쓰이지 않습니다.', 'Weekly structure first. Shown beside QGV only; this chart never changes QGV, TARGET or the playbook and is not an input to them.')),
        node(doc, 'a', {href: state.qgvHref || '#leaderboard', 'data-cw-qgv-link': ''}, words(state, 'QGV 나란히 보기 →', 'View QGV alongside →')));
    } else {
      panel.append(node(doc, 'h3', {}, words(state, '스윙 모드', 'Swing mode')),
        node(doc, 'p', {'data-cw-swing-slot': ''}, words(state, '시나리오 그리기 자리 · 2단계(P2-2·P2-3)에서 연결합니다 · 주문 아님 · 가정 계산 · 지금은 아무것도 그리지 않습니다.', 'Scenario drawing slot · connected in phase 2 (P2-2, P2-3) · not an order · assumption only · nothing is drawn yet.')));
    }
  }

  function paintAll(state) { paintSource(state); paintJudgement(state); paintButtons(state); paintMode(state); paintMeasure(state); paintRange(state); setAttr(state, 'data-timeframe', state.timeframe); setAttr(state, 'data-renderer', state.renderer ? state.renderer.kind : 'none'); setAttr(state, 'data-mode', state.settings.mode); }

  /* ---------- pattern panel (3.1 / 3.2) ---------- */

  const nameOf = (state, pattern) => words(state, ...(PATTERN_NAMES[pattern] || [pattern, pattern]));
  const stateOf = (state, code) => words(state, ...(STATE_NAMES[code] || [code, code]));
  function engineReady(view) { return !!(view.ChartBars && view.PatternEngine && view.PatternHistory && view.PatternConfigDefaults); }

  // Engine input for the current data: ChartBars series per timeframe and the corporate-action record.
  function patternInputs(state) {
    const view = state.view;
    state.engine = {code: 'NO_DATA', series: {}, actions: null};
    if (!state.data) return;
    if (!engineReady(view)) { state.engine.code = 'PATTERN_ENGINE_UNAVAILABLE'; return; }
    try {
      const daily = view.ChartBars.normalize(historyOf(state.data));
      const actions = state.source === 'synthetic' ? syntheticActions(daily) : null;
      state.engine = {code: 'READY', actions, series: {D: daily, W: view.ChartBars.weekly(daily, actions)}};
    } catch (_) { state.engine = {code: 'PATTERN_INPUT_INVALID', series: {}, actions: null}; }
  }

  // Official run (shipped defaults -> PatternHistory, append only) and the optional user-settings run (never recorded).
  function runPatterns(state) {
    const view = state.view, tf = tfKey(state.timeframe), p = state.patterns;
    p.official = null; p.user = null; p.objects = {official: [], user: []}; p.counts = null;
    if (state.engine.code !== 'READY' || !state.engine.series[tf]) return;
    const series = state.engine.series[tf], computedAt = new Date().toISOString();
    try {
      const official = view.PatternEngine.run(series, view.PatternConfigDefaults, state.engine.actions);
      if (official.run_mode !== 'OFFICIAL') throw new Error('PATTERN_RUN_MODE');
      const book = state.source === 'synthetic' ? p.books.synthetic : p.books.device;
      p.counts = book.append(official, computedAt);
      p.records = book.historyFor(official).records().length;
      p.official = {result: official, computedAt};
      p.objects.official = patternObjects(official);
      if (p.userRules) {
        const user = view.PatternEngine.run(series, p.userRules.rules, state.engine.actions);
        if (user.run_mode !== 'USER_SETTINGS') throw new Error('PATTERN_RUN_MODE');
        p.user = {result: user, computedAt, diff: p.userRules.diff, paramsSha: p.userRules.rules.params_sha256};
        p.objects.user = patternObjects(user);
      }
      p.code = 'READY';
    } catch (error) { p.code = error && /^[A-Z_]+$/.test(error.message) ? error.message : 'PATTERN_ENGINE_FAILED'; }
  }

  function viewObjects(state) {
    const p = state.patterns, list = p.view === 'user' ? p.objects.user : p.objects.official;
    return list.filter(o => o.judgeable && state.settings.patterns[PATTERN_GROUP[o.pattern]] !== false);
  }
  function endIndex(state, o) { return o.ended && typeof o.knownIndex === 'number' ? o.knownIndex : state.bars.length - 1; }
  function defaultShown(objects) {
    const zones = objects.filter(o => o.kind === 'ZONE' && o.state === 'ACTIVE');
    const signals = objects.filter(o => o.kind === 'SIGNAL').sort((a, b) => b.formedIndex - a.formedIndex).slice(0, 3);
    return zones.concat(signals);
  }

  function overlaysFor(state, o, source, emphasis) {
    const bars = state.bars, at = i => (bars[i] ? bars[i].time : null), end = at(endIndex(state, o)), start = at(o.startIndex), d = o.detail, out = [];
    const line = (suffix, tone, from, price) => { if (from && end && from < end && typeof price === 'number') out.push({id: o.id + suffix, kind: 'line', source, tone, emphasis, from, to: end, price}); };
    if (o.kind === 'ZONE') { line('|low', 'zone', start, d.low); line('|high', 'zone', start, d.high); }
    else if (PATTERN_GROUP[o.pattern] === 'BOX') { line('|upper', 'box', start, d.upper); line('|lower', 'box', start, d.lower); line('|inv', 'invalidation', at(o.formedIndex), d.invalidation_level); }
    else if (PATTERN_GROUP[o.pattern] === 'DOUBLE') {
      const bottom = o.pattern === 'DOUBLE_BOTTOM', position = bottom ? 'belowBar' : 'aboveBar';
      line('|neck', 'double', start, d.neckline); line('|inv', 'invalidation', at(o.formedIndex), d.invalidation_level);
      if (start) out.push({id: o.id + '|p1', kind: 'marker', source, tone: 'double', emphasis, time: start, label: 'P1', position});
      if (d.p2_at) out.push({id: o.id + '|p2', kind: 'marker', source, tone: 'double', emphasis, time: d.p2_at, label: 'P2', position});
    }
    if (emphasis === 'selected' && o.confirm && at(o.confirm.known_index)) out.push({id: o.id + '|confirm', kind: 'marker', source, tone: PATTERN_GROUP[o.pattern] === 'BOX' ? 'box' : 'double', emphasis, time: at(o.confirm.known_index), label: words(state, '확인', 'Conf.'), position: 'aboveBar'});
    return out;
  }

  function drawPatterns(state) {
    const p = state.patterns, renderer = state.renderer;
    let drawn = 0;
    if (renderer && renderer.capabilities.overlays && state.bars.length) {
      const objects = viewObjects(state), source = p.view === 'user' ? 'USER_SETTINGS' : 'AUTO', selected = objects.find(o => o.id === p.selected) || null, overlays = [];
      if (selected) {
        overlays.push(...overlaysFor(state, selected, source, 'selected'));
        if (p.showAll) for (const o of objects) if (o !== selected) overlays.push(...overlaysFor(state, o, source, 'dim'));
      } else for (const o of p.showAll ? objects : defaultShown(objects)) overlays.push(...overlaysFor(state, o, source, 'normal'));
      const user = userOverlays(state), R = state.view.ChartRenderer;
      drawn = R.normalizeOverlays(overlays, state.bars).length;
      renderer.setOverlays(overlays.concat(user));
      setAttr(state, 'data-user-drawn', R.normalizeOverlays(user, state.bars).length);
    } else { if (renderer) renderer.setOverlays([]); setAttr(state, 'data-user-drawn', 0); }
    setAttr(state, 'data-pattern-drawn', drawn);
  }

  function fmtLevel(state, value) { return typeof value === 'number' ? fmt(state, value) : '—'; }
  function cardRows(state, o, tfLabel) {
    const d = o.detail, w = (ko, en) => words(state, ko, en), rows = [], above = ['BOX_BREAKOUT_UP', 'DOUBLE_BOTTOM'].includes(o.pattern);
    rows.push([w('상태', 'State'), stateOf(state, o.state) + ' (' + o.state + ')' + (o.observationEnded ? w(' · 관찰 창 종료', ' · observation window ended') : '') + ' · known_at ' + o.knownAt]);
    if (o.kind === 'ZONE') {
      rows.push([w('구간', 'Zone'), fmtLevel(state, d.low) + ' ~ ' + fmtLevel(state, d.high) + ' · ' + w('접촉 ', 'touches ') + d.touches + ' · ' + (d.role || '')]);
      rows.push([w('탐지 근거', 'Evidence'), w('기준 피벗 ', 'pivots ') + (d.anchors || []).join(', ') + ' · ATR ' + fmtLevel(state, d.atr) + ' (' + d.atr_at + ')']);
      rows.push([w('이탈 기준', 'Break rule'), w('완결 종가가 구간 밖으로 돌파 여유(ATR 배) 이상', 'Complete close beyond the zone by the break buffer (×ATR)')]);
    } else {
      const dates = PATTERN_GROUP[o.pattern] === 'BOX' ? (d.anchors || []).join(', ') : (d.p1_at + ', ' + d.p2_at + ' · ' + w('간격 ', 'separation ') + d.separation_bars + w('봉', ' bars'));
      const levels = PATTERN_GROUP[o.pattern] === 'BOX' ? w('상단 ', 'upper ') + fmtLevel(state, d.upper) + ' · ' + w('하단 ', 'lower ') + fmtLevel(state, d.lower) : 'P1 ' + fmtLevel(state, d.p1) + ' · P2 ' + fmtLevel(state, d.p2) + ' · ' + w('넥라인 ', 'neckline ') + fmtLevel(state, d.neckline);
      rows.push([w('기준 가격', 'Reference prices'), levels + ' · ' + w('확인 기준 ', 'confirm level ') + fmtLevel(state, d.confirm_level)]);
      rows.push([w('탐지 근거', 'Evidence'), w('기준 날짜 ', 'anchors ') + dates + ' · ' + w('고정 ATR ', 'fixed ATR ') + fmtLevel(state, d.atr) + ' (' + d.atr_at + ')'
        + (o.confirm ? ' · ' + w('거래량 ', 'volume ') + (o.confirm.detail.volume ? o.confirm.detail.volume.state : 'NOT_AVAILABLE') + (o.confirm.detail.gap ? w(' · 갭 돌파', ' · gap') : '') : '')]);
      if (o.state === 'FORMED') rows.push([w('남은 조건', 'Remaining condition'), w('완결 종가 ', 'Complete close ') + (above ? '> ' : '< ') + fmtLevel(state, d.confirm_level)]);
      rows.push([w('무효화', 'Invalidation'), w('확인 전 완결 종가 ', 'Before confirmation, complete close ') + (above ? '< ' : '> ') + fmtLevel(state, d.invalidation_level)]);
    }
    rows.push([w('일봉·주봉', 'Daily/weekly'), 'NOT_AVAILABLE · ALIGNMENT_NOT_COMPUTED · ' + tfLabel]);
    rows.push([w('자료 품질', 'Data quality'), (o.judgeable ? w('가격 기준 연속성 확인', 'price-basis continuity confirmed') : 'NOT_JUDGEABLE') + (o.reasons.length ? ' · ' + o.reasons.join(' · ') : '')]);
    rows.push([w('투자 유용성', 'Investment usefulness'), w('미검증 · 형태가 맞아도 오른다는 뜻이 아님', 'Unverified · a matching shape does not mean the price will rise')]);
    rows.push([w('규칙', 'Rules'), o.ruleVersion + ' · ' + String(o.paramsSha).slice(0, 8)]);
    return rows;
  }

  function paintCards(state) {
    const doc = state.doc, p = state.patterns, list = state.patternCards, tfLabel = state.timeframe === 'weekly' ? words(state, '주봉', 'weekly') : words(state, '일봉', 'daily');
    list.replaceChildren();
    const objects = viewObjects(state).sort((a, b) => (a.kind === b.kind ? b.formedIndex - a.formedIndex : a.kind === 'SIGNAL' ? -1 : 1));
    const shown = p.expanded ? objects : objects.slice(0, 6);
    // A selected pattern always has its card listed, even when the list is collapsed.
    if (p.selected && !shown.some(o => o.id === p.selected)) { const picked = objects.find(o => o.id === p.selected); if (picked) shown.push(picked); }
    const label = p.view === 'user' ? words(state, '사용자 설정 탐색 · 공식 이력 아님', 'User-settings exploration · not official history') : words(state, '연구 기본값 · 투자 유용성 미검증', 'Research default · investment usefulness unverified');
    for (const o of shown) {
      const item = node(doc, 'li'), button = node(doc, 'button', {type: 'button', class: 'cw-pattern-card', 'data-pattern-card': o.id, 'data-pattern-state': o.state, 'data-pattern-kind': p.view === 'user' ? 'USER_SETTINGS' : 'OFFICIAL', 'aria-pressed': String(o.id === p.selected)});
      const rows = cardRows(state, o, tfLabel);
      button.append(node(doc, 'span', {class: 'cw-card-title'}, nameOf(state, o.pattern) + ' · ' + tfLabel), node(doc, 'span', {class: 'badge', 'data-pattern-label': ''}, label),
        node(doc, 'span', {class: 'cw-card-state', 'data-pattern-card-state': ''}, rows[0][1]));
      // Full card fields (design §11.1) sit next to the select button, so the button stays one control.
      const more = node(doc, 'details', {class: 'cw-card-detail'}), dl = node(doc, 'dl', {'data-pattern-card-fields': ''});
      for (const [term, value] of rows.slice(1)) dl.append(node(doc, 'dt', {}, term), node(doc, 'dd', {}, value));
      more.append(node(doc, 'summary', {}, words(state, '근거·기준 가격·무효화', 'Evidence, levels, invalidation')), dl);
      item.append(button, more); list.append(item);
    }
    state.patternMore.hidden = objects.length <= 6;
    state.patternMore.textContent = p.expanded ? words(state, '최근 6개만 보기', 'Show the latest 6') : words(state, '모두 보기 (', 'Show all (') + objects.length + ')';
    setAttr(state, 'data-pattern-cards', shown.length);
  }

  function paintSuitability(state) {
    const doc = state.doc, dl = state.patternSuitability, p = state.patterns, w = (ko, en) => words(state, ko, en), tf = tfKey(state.timeframe);
    dl.replaceChildren();
    const series = state.engine.series[tf], row = (key, term, value, code) => dl.append(node(doc, 'dt', {}, term), node(doc, 'dd', {'data-suitability': key, 'data-code': code}, value));
    if (!series) { row('ENGINE', w('패턴 엔진', 'Pattern engine'), state.engine.code, state.engine.code); return; }
    const complete = series.bars.filter(b => b.state === 'COMPLETE').length, params = (p.view === 'user' && p.userRules ? p.userRules.rules : state.view.PatternConfigDefaults).params;
    const short = minBars(params, tf).filter(([, need]) => complete < need);
    row('BARS', w('완결 봉 수', 'Complete bars'), complete + ' · ' + minBars(params, tf).map(([k, need]) => k + ' ' + need).join(' · ') + (short.length ? ' · INSUFFICIENT_BARS ' + short.map(x => x[0]).join(',') : ' · OK'), short.length ? 'INSUFFICIENT_BARS' : 'OK');
    const actions = state.view.ChartBars.corporateActions(state.engine.actions);
    row('ACTIONS', w('기업행사 (분할 이벤트)', 'Corporate actions (splits)'), state.source === 'synthetic' ? w('합성 자료 · 생성 조건상 분할 없음 (기능 확인용)', 'Synthetic data · generated without splits (function check)') : actions.status + w(' · 분할 이벤트 미제공 (Worker P1-W 전)', ' · split events not provided (before Worker P1-W)'), actions.status);
    const first = series.bars[0], last = series.bars[series.bars.length - 1], cont = state.view.ChartBars.continuity(state.engine.actions, first.first_session || first.session_date, last.last_session || last.session_date);
    row('CONTINUITY', w('가격 기준 연속성', 'Price-basis continuity'), cont.state + (cont.reason_codes.length ? ' · ' + cont.reason_codes.join(' · ') : ''), cont.state);
    const quality = series.quality && Array.isArray(series.quality.codes) ? series.quality.codes : [];
    row('QUALITY', w('자료 품질 코드', 'Data quality codes'), quality.length ? quality.join(' · ') : '—', quality.length ? 'CODES' : 'NONE');
  }

  function paintPatterns(state) {
    const p = state.patterns, w = (ko, en) => words(state, ko, en), doc = state.doc;
    const objects = p.view === 'user' ? p.objects.user : p.objects.official, judgeable = objects.filter(o => o.judgeable).length, withheld = objects.length - judgeable;
    setAttr(state, 'data-pattern-view', p.view);
    for (const b of state.root.querySelectorAll('[data-pattern-view-button]')) { b.setAttribute('aria-pressed', String(b.dataset.patternViewButton === p.view)); if (b.dataset.patternViewButton === 'user') b.disabled = !p.user; }
    state.patternShowAll.setAttribute('aria-pressed', String(p.showAll));
    state.patternSource.replaceChildren();
    if (state.source === 'synthetic') state.patternSource.append(node(doc, 'strong', {'data-pattern-synthetic-label': ''}, words(state, ...SYNTHETIC_PATTERN_LABEL)));
    const status = !state.data ? 'NO_DATA' : state.engine.code !== 'READY' ? state.engine.code : p.code !== 'READY' ? p.code : judgeable ? 'SHOWN' : 'NOT_JUDGEABLE';
    state.patternStatus.dataset.code = status;
    const reasons = [...new Set(objects.filter(o => !o.judgeable).flatMap(o => o.reasons))];
    state.patternStatus.replaceChildren();
    if (status === 'NOT_JUDGEABLE') state.patternStatus.append(node(doc, 'span', {class: 'badge NOT_AVAILABLE'}, w('판정 불가', 'Not judgeable')), doc.createTextNode(' ' + (reasons.length ? reasons.join(' · ') : 'PRICE_BASIS_CONTINUITY_UNCONFIRMED') + ' · ' + w('패턴 상태를 신호로 보이지 않습니다. 판정 불가 객체 ', 'No pattern state is shown as a signal. Withheld objects ') + withheld));
    else if (status === 'SHOWN') state.patternStatus.textContent = w('표시 ', 'Shown ') + judgeable + w('개 · 구조 설명 ', ' · structure ') + ((p.view === 'user' ? p.user : p.official).result.structure.label_ko || 'NOT_AVAILABLE') + w(' (국면 판정 아님)', ' (not a regime call)');
    else state.patternStatus.textContent = status;
    state.patternStatus.dataset.reasons = reasons.join(' ');
    const run = p.view === 'user' ? p.user : p.official;
    state.patternRun.textContent = !run ? '' : (p.view === 'user'
      ? w('사용자 설정 탐색 · 공식 이력에 쓰지 않음 · 바꾼 값 ', 'User-settings exploration · never written to the official history · changed ') + (p.user.diff.map(x => x.name + (x.timeframe ? ' ' + x.timeframe : '') + ' ' + x.from + '→' + x.to).join(', ') || '—') + ' · params ' + p.user.paramsSha.slice(0, 8)
      : w('공식 탐지 · ', 'Official detection · ') + run.result.label_ko + ' · ' + run.result.rule_version + ' · params ' + run.result.params_sha256.slice(0, 8)) + ' · ' + w('계산 ', 'computed ') + run.computedAt;
    state.patternRun.dataset.runMode = run ? run.result.run_mode : '';
    const counts = p.counts || {added: 0, duplicates: 0, withheld: 0};
    state.patternHistory.dataset.records = String(p.records || 0); state.patternHistory.dataset.added = String(counts.added); state.patternHistory.dataset.notJudgeable = String(counts.withheld); // not data-withheld: that attribute marks research sections withheld from publication
    state.patternHistory.textContent = w('공식 이력 (RAM · 추가만 · ', 'Official history (RAM · append only · ') + (state.source === 'synthetic' ? w('합성 자료 전용 장부', 'synthetic-only book') : w('기기 자료 장부', 'device-data book')) + '): '
      + w('기록 ', 'records ') + (p.records || 0) + w(' · 이번 추가 ', ' · added now ') + counts.added + w(' · 중복 ', ' · duplicates ') + counts.duplicates + w(' · 판정 불가 보류 ', ' · withheld (not judgeable) ') + counts.withheld;
    state.patternHistory.hidden = !p.official;
    state.patternOverlayNote.textContent = state.renderer && state.renderer.kind === 'svg' ? w('SVG 대체 경로에서는 패턴을 그리지 않습니다 · 카드만 봅니다.', 'The SVG fallback draws no patterns · cards only.') : '';
    paintSuitability(state); paintCards(state); drawPatterns(state);
  }

  function selectPattern(state, id, {zoom = true} = {}) {
    const p = state.patterns, objects = viewObjects(state), o = objects.find(x => x.id === id) || null;
    p.selected = o && p.selected !== o.id ? o.id : null;
    setAttr(state, 'data-pattern-selected', p.selected || '');
    if (o && p.selected && zoom && state.renderer) {
      const from = o.startIndex, to = o.confirm ? o.confirm.known_index : endIndex(state, o), pad = Math.max(2, Math.round((to - from) * 0.2));
      state.renderer.setVisibleRange({from: Math.max(0, from - pad), to: Math.min(state.bars.length - 1, to + pad)});
    }
    paintCards(state); drawPatterns(state);
    if (o) state.live.textContent = p.selected ? words(state, '선택: ', 'Selected: ') + nameOf(state, o.pattern) + ' · ' + stateOf(state, o.state) : words(state, '선택 해제', 'Selection cleared');
  }

  async function runUserSettings(state) {
    const p = state.patterns, view = state.view, tf = tfKey(state.timeframe), changes = {};
    for (const select of state.root.querySelectorAll('[data-pattern-param]')) changes[select.dataset.patternParam] = Number(select.value);
    try {
      const {params, diff} = applyChanges(view.PatternConfigDefaults.params, changes, tf);
      if (!diff.length) { p.userRules = null; p.view = 'official'; state.exploreStatus.dataset.code = 'SAME_AS_DEFAULTS'; state.exploreStatus.textContent = words(state, '기본값과 같음 · 공식 탐지를 봅니다.', 'Same as defaults · showing official detection.'); runPatterns(state); paintPatterns(state); return; }
      const sha = await hashParams(view, view.PatternEngine.canonicalJson(params));
      if (state.disposed) return;
      const D = view.PatternConfigDefaults;
      p.userRules = {rules: {schema: D.schema, rule_version: D.rule_version, status: D.status, label_ko: '사용자 설정 탐색 · 공식 이력 아님', label_en: 'User-settings exploration · not official history', params, params_sha256: sha}, diff};
      p.view = 'user'; p.selected = null;
      runPatterns(state);
      state.exploreStatus.dataset.code = p.user ? 'USER_RUN' : p.code;
      state.exploreStatus.textContent = p.user ? words(state, '사용자 설정 탐색을 실행했습니다 · 공식 이력은 그대로입니다.', 'User-settings exploration ran · the official history is unchanged.') : p.code;
    } catch (error) { state.exploreStatus.dataset.code = error && /^[A-Z_]+$/.test(error.message) ? error.message : 'PATTERN_ENGINE_FAILED'; state.exploreStatus.textContent = state.exploreStatus.dataset.code; }
    paintPatterns(state);
  }

  function resetUserSettings(state) {
    const p = state.patterns;
    p.userRules = null; p.user = null; p.objects.user = []; p.view = 'official'; p.selected = null;
    buildExploreControls(state); runPatterns(state); paintPatterns(state);
    state.exploreStatus.dataset.code = 'DEFAULTS'; state.exploreStatus.textContent = words(state, '기본값으로 돌아왔습니다.', 'Back to defaults.');
  }

  function buildExploreControls(state) {
    const doc = state.doc, tf = tfKey(state.timeframe), grid = state.exploreGrid, view = state.view;
    grid.replaceChildren();
    if (!view.PatternConfigDefaults) return;
    const current = state.patterns.userRules ? state.patterns.userRules.rules.params : view.PatternConfigDefaults.params;
    for (const [name, spec, label] of EXPLORE_GRID) {
      const wrap = node(doc, 'label', {class: 'cw-param'}), select = node(doc, 'select', {'data-pattern-param': name});
      const def = paramValue(view.PatternConfigDefaults.params, name, tf), value = paramValue(current, name, tf);
      for (const option of gridOptions(spec, tf)) { const o = node(doc, 'option', {value: String(option)}, String(option) + (option === def ? words(state, ' (기본)', ' (default)') : '')); if (option === value) o.selected = true; select.append(o); }
      wrap.append(doc.createTextNode(words(state, ...label) + ' '), select);
      grid.append(wrap);
    }
  }

  function buildPatternPanel(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en), section = node(doc, 'section', {class: 'cw-patterns', 'data-pattern-panel': '', 'aria-labelledby': state.id + '-patterns'});
    section.append(node(doc, 'h3', {id: state.id + '-patterns'}, w('패턴 · 연구 기본값 · 투자 유용성 미검증', 'Patterns · Research default · investment usefulness unverified')));
    state.patternSource = node(doc, 'p', {class: 'small', 'data-pattern-source': ''});
    const views = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': w('결과 종류', 'Result kind')});
    views.append(node(doc, 'button', {type: 'button', 'data-pattern-view-button': 'official', 'aria-pressed': 'true'}, w('공식 탐지', 'Official detection')),
      node(doc, 'button', {type: 'button', 'data-pattern-view-button': 'user', 'aria-pressed': 'false', disabled: ''}, w('사용자 설정 탐색', 'User-settings exploration')),
      node(doc, 'button', {type: 'button', 'data-pattern-view-button': 'scenario', 'aria-pressed': 'false'}, w('사용자 시나리오 · 사용자 작성 절로', 'User scenarios · go to user-written')));
    state.patternShowAll = node(doc, 'button', {type: 'button', 'data-pattern-show-all': '', 'aria-pressed': 'false'}, w('모든 패턴 보기', 'Show all patterns'));
    views.append(state.patternShowAll);
    state.patternStatus = node(doc, 'p', {class: 'cw-judgement', 'data-pattern-status': ''});
    state.patternRun = node(doc, 'p', {class: 'small', 'data-pattern-run': ''});
    state.patternHistory = node(doc, 'p', {class: 'small', 'data-pattern-history': '', hidden: ''});
    state.patternOverlayNote = node(doc, 'p', {class: 'small', 'data-pattern-overlay-note': ''});
    const suit = node(doc, 'details', {class: 'cw-suitability', 'data-pattern-suitability-box': ''});
    suit.append(node(doc, 'summary', {}, w('자료 적합성 (최소 봉 수 · 기업행사 · 가격 기준 연속성)', 'Data suitability (minimum bars · corporate actions · price-basis continuity)')));
    state.patternSuitability = node(doc, 'dl', {'data-pattern-suitability': ''});
    suit.append(state.patternSuitability);
    state.patternCards = node(doc, 'ul', {class: 'cw-pattern-cards', 'data-pattern-cards': ''});
    state.patternMore = node(doc, 'button', {type: 'button', 'data-pattern-more': '', hidden: ''});
    section.append(state.patternSource, views, state.patternStatus, state.patternRun, state.patternHistory, state.patternOverlayNote, suit, state.patternCards, state.patternMore,
      node(doc, 'p', {class: 'small'}, w('카드를 누르면 차트가 그 패턴 범위로 확대됩니다. 차트에 초점이 있을 때 Enter는 십자선 위치의 패턴 카드를 고릅니다. 판정·신호·매매 지시가 아닙니다.', 'Choosing a card zooms the chart to that pattern. With the chart focused, Enter picks the card at the crosshair. Not a judgement, signal or trading instruction.')));
    return section;
  }

  /* ---------- user layer: drawing, editing, storage ---------- */

  const userWord = state => words(state, ...USER_LABEL);
  function userHere(state) {
    const tf = tfKey(state.timeframe);
    return state.user.items.filter(o => o.symbol === state.symbol && o.interval === tf);
  }
  const saveFailedText = state => words(state, '저장 실패 · 이 브라우저 저장 공간이 가득 찼거나 쓸 수 없습니다. 이미 저장된 노트·시나리오는 그대로 두었고, 방금 바꾼 내용은 이 화면에만 있습니다(새로 고치면 사라짐). 「이 기기 파일로 내보내기」로 파일에 보관한 뒤 필요 없는 항목을 지우세요.',
    'Save failed · this browser’s storage is full or not writable. Notes and scenarios already stored were kept; the latest change exists on this screen only (lost on reload). Use “Export to a file on this device” to keep a file, then delete items you no longer need.');
  function userPersist(state) {
    const ok = state.userStore.save(state.user.items);
    state.user.unsaved = !ok;
    state.userStatus.dataset.code = ok ? 'SAVED' : 'SAVE_FAILED';
    state.userStatus.textContent = ok ? words(state, '이 기기에만 저장함 · ', 'Saved on this device only · ') + state.user.items.length + words(state, '개', ' items') : saveFailedText(state);
    if (!ok) state.live.textContent = state.userStatus.textContent;
    return ok;
  }
  function userOverlays(state) {
    if (!state.user.visible || !state.bars.length) return [];
    const bars = state.bars, last = bars[bars.length - 1].time, out = [], times = new Set(bars.map(b => b.time));
    for (const o of userHere(state)) {
      const emphasis = o.id === state.user.editing ? 'selected' : 'normal';
      if (o.schema === 'chart-annotation/1') {
        const [a, b] = o.points.length === 2 ? [...o.points].sort((x, y) => (x.time < y.time ? -1 : 1)) : o.points;
        if (o.kind === 'LINE') out.push({id: o.id, kind: 'segment', source: 'USER', tone: 'user', emphasis, from: a.time, to: b.time, fromPrice: a.price, toPrice: b.price});
        else if (o.kind === 'RANGE') for (const [suffix, price] of [['|low', Math.min(a.price, b.price)], ['|high', Math.max(a.price, b.price)]]) out.push({id: o.id + suffix, kind: 'line', source: 'USER', tone: 'user', emphasis, from: a.time, to: b.time, price});
        if (times.has(a.time)) out.push({id: o.id + '|label', kind: 'marker', source: 'USER', tone: 'user', emphasis, time: a.time, label: (o.kind === 'MEMO' ? (o.text || words(state, ...NOTE_KINDS.MEMO)) : words(state, ...NOTE_KINDS[o.kind])).slice(0, 10), position: 'aboveBar'});
      } else {
        const from = times.has(o.anchor_time) && o.anchor_time < last ? o.anchor_time : bars[Math.max(0, bars.length - 30)].time, dir = DIRECTIONS[o.direction];
        o.levels.forEach((l, n) => out.push({id: o.id + '|l' + n, kind: 'line', source: 'USER', tone: 'user', emphasis, from, to: last, price: l.price}));
        if (o.invalidation_price) out.push({id: o.id + '|inv', kind: 'line', source: 'USER', tone: 'invalidation', emphasis, from, to: last, price: o.invalidation_price});
        out.push({id: o.id + '|label', kind: 'marker', source: 'USER', tone: 'user', emphasis, time: last, label: dir[2] + ' ' + words(state, dir[0], dir[1]), position: o.direction === 'DOWN' ? 'belowBar' : 'aboveBar'});
      }
    }
    return out;
  }

  function startTool(state, tool) {
    state.user.tool = state.user.tool === tool ? null : tool; state.user.points = [];
    if (state.user.tool && state.measuring) { state.measuring = false; state.measure = null; state.measureStart = null; if (state.renderer) state.renderer.setMeasure(null); paintMeasure(state); paintButtons(state); }
    paintUserTools(state);
  }
  function paintUserTools(state) {
    for (const b of state.root.querySelectorAll('[data-user-tool]')) { b.setAttribute('aria-pressed', String(b.dataset.userTool === state.user.tool)); b.disabled = !state.bars.length || !(state.renderer && state.renderer.capabilities.overlays); }
    const need = state.user.tool === 'MEMO' ? 1 : 2;
    setAttr(state, 'data-user-tool', state.user.tool || 'off');
    state.userToolStatus.textContent = !state.user.tool ? words(state, '그리기 꺼짐 · 선·구간은 두 점, 메모는 한 점을 차트에서 누릅니다 (키보드: 차트 초점에서 N).', 'Drawing off · lines and ranges take two points, memos one point (keyboard: N with the chart focused).')
      : words(state, NOTE_KINDS[state.user.tool][0] + ' · 점 ' + (state.user.points.length + 1) + '/' + need + '을 고르세요', NOTE_KINDS[state.user.tool][1] + ' · pick point ' + (state.user.points.length + 1) + ' of ' + need);
  }
  function addUserPoint(state, hit) {
    const bar = state.bars[hit.index];
    if (!bar || !state.user.tool || !state.symbol) return;
    state.user.points.push({time: bar.time, price: roundPrice(hit.price)});
    const need = state.user.tool === 'MEMO' ? 1 : 2;
    if (state.user.points.length < need) { paintUserTools(state); return; }
    const now = new Date().toISOString(), item = {schema: 'chart-annotation/1', id: newId(state.view), kind: state.user.tool, symbol: state.symbol, interval: tfKey(state.timeframe), price_basis: 'RAW_CLOSE', author: 'USER',
      points: state.user.points, text: '', created_at: now, updated_at: now};
    if (state.user.items.length >= USER_LIMIT || !validUserObject(item)) { state.userStatus.dataset.code = 'USER_OBJECT_REFUSED'; state.userStatus.textContent = 'USER_OBJECT_REFUSED'; state.user.points = []; paintUserTools(state); return; }
    state.user.items.push(item); state.user.editing = item.id; state.user.tool = null; state.user.points = [];
    userPersist(state); paintUser(state); drawPatterns(state); paintUserTools(state);
    state.live.textContent = words(state, '사용자 작성 ' + NOTE_KINDS[item.kind][0] + ' 추가 · 이 기기에만 저장', 'User-written ' + NOTE_KINDS[item.kind][1] + ' added · saved on this device only');
    const field = state.userNotes.querySelector('[data-user-item="' + item.id + '"] [data-user-field="text"]');
    if (field) field.focus();
  }

  function field(doc, label, input) { const wrap = doc.createElement('label'); wrap.className = 'cw-field'; wrap.append(doc.createTextNode(label + ' '), input); return wrap; }
  function input(doc, attrs, value) { const el = doc.createElement('input'); for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v); el.value = value === null || value === undefined ? '' : String(value); return el; }
  function noteTitle(state, o) {
    const pts = o.points.map(pt => pt.time + ' ' + fmt(state, pt.price)).join(' → ');
    return words(state, ...NOTE_KINDS[o.kind]) + ' · ' + pts + ' · ' + (o.interval === 'W' ? words(state, '주봉', 'weekly') : words(state, '일봉', 'daily'));
  }
  function scenarioTitle(state, o) {
    const dir = DIRECTIONS[o.direction];
    return dir[2] + ' ' + words(state, dir[0], dir[1]) + ' · ' + (o.horizon === 'long' ? words(state, '장기', 'long-term') : words(state, '스윙', 'swing')) + ' · ' + o.levels.map(l => (l.label ? l.label + ' ' : '') + fmt(state, l.price)).join(' · ');
  }
  function userItem(state, o) {
    const doc = state.doc, li = node(doc, 'li', {'data-user-item': o.id, 'data-user-schema': o.schema}), drawn = new Set(state.bars.map(b => b.time));
    const times = o.schema === 'chart-annotation/1' ? o.points.map(pt => pt.time) : [];
    li.append(node(doc, 'span', {class: 'badge', 'data-user-label': ''}, userWord(state)), doc.createTextNode(' ' + (o.schema === 'chart-annotation/1' ? noteTitle(state, o) : scenarioTitle(state, o))));
    if (times.some(t => !drawn.has(t))) li.append(node(doc, 'span', {class: 'small'}, words(state, ' · 지금 봉 범위 밖', ' · outside the current bars')));
    if (o.text && o.schema === 'chart-annotation/1') li.append(node(doc, 'p', {class: 'small cw-user-text'}, o.text));
    if (o.schema === 'chart-scenario/1') li.append(node(doc, 'p', {class: 'small cw-user-text'}, words(state, '조건: ', 'Condition: ') + (o.condition || '—') + ' · ' + words(state, '무효화: ', 'Invalidation: ') + (o.invalidation || '—') + (o.invalidation_price ? ' (' + fmt(state, o.invalidation_price) + ')' : '')));
    const edit = node(doc, 'details', {class: 'cw-user-edit', 'data-user-edit': o.id});
    if (o.id === state.user.editing) edit.open = true;
    edit.append(node(doc, 'summary', {}, words(state, '고치기 · 지우기', 'Edit · delete')));
    const form = node(doc, 'div', {class: 'cw-user-form'});
    if (o.schema === 'chart-annotation/1') {
      form.append(field(doc, words(state, '메모', 'Text'), input(doc, {type: 'text', maxlength: String(TEXT_LIMIT), 'data-user-field': 'text'}, o.text)));
      o.points.forEach((pt, n) => form.append(field(doc, words(state, '날짜 ', 'Date ') + (n + 1), input(doc, {type: 'text', inputmode: 'numeric', 'data-user-field': 'time' + n, pattern: '\\d{4}-\\d{2}-\\d{2}'}, pt.time)),
        field(doc, words(state, '가격 ', 'Price ') + (n + 1), input(doc, {type: 'number', step: 'any', min: '0', 'data-user-field': 'price' + n}, pt.price))));
    } else form.append(...scenarioFields(state, o));
    form.append(node(doc, 'button', {type: 'button', 'data-user-save': o.id}, words(state, '저장', 'Save')), node(doc, 'button', {type: 'button', 'data-user-delete': o.id}, words(state, '지우기', 'Delete')));
    edit.append(form); li.append(edit);
    return li;
  }
  function scenarioFields(state, o) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en), out = [];
    const horizon = node(doc, 'select', {'data-user-field': 'horizon'});
    for (const [v, ko, en] of [['long', '장기', 'Long-term'], ['swing', '스윙', 'Swing']]) { const opt = node(doc, 'option', {value: v}, w(ko, en)); if ((o ? o.horizon : (state.settings.mode === 'swing' ? 'swing' : 'long')) === v) opt.selected = true; horizon.append(opt); }
    const direction = node(doc, 'select', {'data-user-field': 'direction'});
    for (const [v, d] of Object.entries(DIRECTIONS)) { const opt = node(doc, 'option', {value: v}, d[2] + ' ' + w(d[0], d[1])); if (o && o.direction === v) opt.selected = true; direction.append(opt); }
    out.push(field(doc, w('보기', 'View'), horizon), field(doc, w('경로', 'Path'), direction));
    for (let n = 0; n < 3; n++) {
      const level = o && o.levels[n];
      out.push(field(doc, w('핵심 가격 이름 ', 'Key level name ') + (n + 1), input(doc, {type: 'text', maxlength: '40', 'data-user-field': 'levelLabel' + n}, level ? level.label : '')),
        field(doc, w('핵심 가격 ', 'Key level ') + (n + 1), input(doc, {type: 'number', step: 'any', min: '0', 'data-user-field': 'level' + n}, level ? level.price : '')));
    }
    out.push(field(doc, w('조건', 'Condition'), input(doc, {type: 'text', maxlength: String(TEXT_LIMIT), 'data-user-field': 'condition'}, o ? o.condition : '')),
      field(doc, w('무효화 조건', 'Invalidation condition'), input(doc, {type: 'text', maxlength: String(TEXT_LIMIT), 'data-user-field': 'invalidation'}, o ? o.invalidation : '')),
      field(doc, w('무효화 가격 (선택)', 'Invalidation price (optional)'), input(doc, {type: 'number', step: 'any', min: '0', 'data-user-field': 'invalidationPrice'}, o && o.invalidation_price ? o.invalidation_price : '')));
    return out;
  }
  function readScenario(state, box, base) {
    const get = name => { const el = box.querySelector('[data-user-field="' + name + '"]'); return el ? el.value.trim() : ''; }, levels = [];
    for (let n = 0; n < 3; n++) { const price = Number(get('level' + n)); if (get('level' + n) !== '' && isPrice(price)) levels.push({label: get('levelLabel' + n), price}); }
    const inv = get('invalidationPrice'), now = new Date().toISOString();
    return {...base, schema: 'chart-scenario/1', horizon: get('horizon'), direction: get('direction'), levels, condition: get('condition'), invalidation: get('invalidation'),
      invalidation_price: inv === '' ? null : Number(inv), updated_at: now};
  }
  function saveUserItem(state, id) {
    const at = state.user.items.findIndex(o => o.id === id), box = state.root.querySelector('[data-user-edit="' + id + '"]');
    if (at < 0 || !box) return;
    const old = state.user.items[at], get = name => { const el = box.querySelector('[data-user-field="' + name + '"]'); return el ? el.value.trim() : ''; };
    const next = old.schema === 'chart-annotation/1'
      ? {...old, text: get('text'), points: old.points.map((pt, n) => ({time: get('time' + n), price: Number(get('price' + n))})), updated_at: new Date().toISOString()}
      : readScenario(state, box, old);
    if (!validUserObject(next)) { state.userStatus.dataset.code = 'USER_OBJECT_INVALID'; state.userStatus.textContent = words(state, '입력을 확인하세요 (날짜 YYYY-MM-DD, 가격 0보다 큼)', 'Check the input (date YYYY-MM-DD, price above 0)'); return; }
    state.user.items[at] = next; state.user.editing = id;
    userPersist(state); paintUser(state); drawPatterns(state);
  }
  function deleteUserItem(state, id) {
    state.user.items = state.user.items.filter(o => o.id !== id); if (state.user.editing === id) state.user.editing = null;
    userPersist(state); paintUser(state); drawPatterns(state);
    state.live.textContent = words(state, '사용자 작성 객체를 지웠습니다', 'User-written object deleted');
  }
  function addScenario(state) {
    if (!state.symbol || !state.bars.length) return;
    const now = new Date().toISOString(), item = readScenario(state, state.scenarioForm, {id: newId(state.view), symbol: state.symbol, interval: tfKey(state.timeframe), price_basis: 'RAW_CLOSE', author: 'USER', text: '',
      anchor_time: state.bars[state.bars.length - 1].time, created_at: now});
    if (state.user.items.length >= USER_LIMIT || !validUserObject(item)) { state.userStatus.dataset.code = 'USER_OBJECT_INVALID'; state.userStatus.textContent = words(state, '핵심 가격을 하나 이상 넣으세요 (0보다 큼)', 'Enter at least one key level above 0'); return; }
    state.user.items.push(item); state.user.editing = null;
    for (const el of state.scenarioForm.querySelectorAll('input')) el.value = '';
    state.scenarioDetails.open = false;
    userPersist(state); paintUser(state); drawPatterns(state);
  }
  function exportUser(state) {
    const view = state.view, blob = new view.Blob([JSON.stringify({schema: USER_SCHEMA, exported_at: new Date().toISOString(), items: state.user.items}, null, 2)], {type: 'application/json'});
    const url = view.URL.createObjectURL(blob), a = state.doc.createElement('a');
    a.href = url; a.download = 'chart-user-objects.json'; state.doc.body.append(a); a.click(); a.remove();
    view.setTimeout(() => view.URL.revokeObjectURL(url), 1000);
  }
  async function importUser(state, input) {
    const file = input.files && input.files[0]; if (!file) return;
    const refuse = (code, text) => { input.value = ''; state.userStatus.dataset.code = code; state.userStatus.textContent = text; state.live.textContent = text; };
    let incoming;
    try { if (file.size > USER_IMPORT_MAX_BYTES) throw new Error('USER_IMPORT_TOO_LARGE'); incoming = parseUserExport(JSON.parse(await file.text())); }
    catch (_) { refuse('IMPORT_REFUSED', words(state, '가져오지 않음 · 노트·시나리오 파일 형식이 아니거나 허용되지 않은 항목(가격 시계열·시세 필드 등)이 있습니다. 기존 항목은 그대로입니다.', 'Not imported · not a notes/scenarios file, or it has fields that are not allowed (price series, quote fields, …). Existing items are unchanged.')); return; }
    if (state.disposed) return;
    const before = state.user.items, merged = mergeUserItems(before, incoming);
    if (!merged.added) { refuse('IMPORTED', words(state, '새로 합칠 항목 없음 · 이미 있던 ' + merged.skipped + '개는 건너뜀', 'Nothing new to merge · skipped ' + merged.skipped + ' already present')); return; }
    if (!state.userStore.save(merged.items)) { refuse('SAVE_FAILED', saveFailedText(state)); return; }
    state.user.items = merged.items; state.user.unsaved = false; input.value = '';
    paintUser(state); drawPatterns(state);
    state.userStatus.dataset.code = 'IMPORTED';
    state.userStatus.textContent = words(state, '가져와 합침 · ' + merged.added + '개 추가 · 이미 있던 ' + merged.skipped + '개는 건너뜀 · 이 기기에만 저장', 'Imported and merged · ' + merged.added + ' added · ' + merged.skipped + ' already present skipped · this device only');
    state.live.textContent = state.userStatus.textContent;
  }
  function clearUser(state, scope) {
    const here = new Set(userHere(state).map(o => o.id));
    state.user.items = scope === 'here' ? state.user.items.filter(o => !here.has(o.id)) : [];
    state.user.editing = null;
    const ok = scope === 'here' ? userPersist(state) : state.userStore.clear();
    if (ok && !state.user.items.length) { state.user.unsaved = false; state.userStatus.dataset.code = 'CLEARED'; state.userStatus.textContent = words(state, '이 기기 저장을 비웠습니다', 'Cleared on this device'); }
    else if (!ok && scope !== 'here') { state.userStatus.dataset.code = 'SAVE_FAILED'; state.userStatus.textContent = saveFailedText(state); }
    paintUser(state); drawPatterns(state);
  }

  function paintUser(state) {
    const doc = state.doc, here = userHere(state), notes = here.filter(o => o.schema === 'chart-annotation/1'), scenarios = here.filter(o => o.schema === 'chart-scenario/1');
    state.userNotes.replaceChildren(...notes.map(o => userItem(state, o)));
    state.userScenarios.replaceChildren();
    for (const dir of Object.keys(DIRECTIONS)) for (const o of scenarios.filter(x => x.direction === dir)) state.userScenarios.append(userItem(state, o));
    if (!notes.length) state.userNotes.append(node(doc, 'li', {class: 'small'}, words(state, '이 종목·봉 주기에 노트가 없습니다.', 'No notes for this symbol and interval.')));
    if (!scenarios.length) state.userScenarios.append(node(doc, 'li', {class: 'small'}, words(state, '이 종목·봉 주기에 시나리오가 없습니다.', 'No scenarios for this symbol and interval.')));
    setAttr(state, 'data-user-count', here.length); setAttr(state, 'data-user-total', state.user.items.length);
    state.userAnchor.textContent = state.symbol ? words(state, '좌표 기준: ', 'Anchors: ') + state.symbol + ' · ' + (state.timeframe === 'weekly' ? words(state, '주봉', 'weekly') : words(state, '일봉', 'daily')) + ' · RAW_CLOSE · ' + words(state, '날짜/가격', 'date/price') : words(state, '자료를 불러오면 노트·시나리오를 쓸 수 있습니다.', 'Load data to write notes and scenarios.');
    state.scenarioSave.disabled = !state.bars.length;
    state.swingSlot.hidden = state.settings.mode !== 'swing';
    paintUserTools(state);
  }

  function buildUserPanel(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en), section = node(doc, 'section', {class: 'cw-user', 'data-user-panel': '', 'aria-labelledby': state.id + '-user'});
    section.append(node(doc, 'h3', {id: state.id + '-user'}, w('사용자 작성 · 시나리오(3.1.3) · 차트 노트(3.3)', 'User-written · scenarios (3.1.3) · chart notes (3.3)')),
      node(doc, 'p', {class: 'small', 'data-user-boundary': ''}, w('사용자 작성 객체는 공식 탐지 이력과 성과 기록에 쓰지 않고, 공식 탐지를 바꾸지 않습니다. 이 브라우저에 저장 · 내보내기·가져오기·백업 가능 · 서버·Google 시트·계정으로 보내지 않습니다. 주문 아님.', 'User-written objects are never written to the official detection history or any results record and never change official detection. Saved in this browser · export, import and backup available · never sent to a server, Google Sheet or account. Not an order.')));
    state.userAnchor = node(doc, 'p', {class: 'small', 'data-user-anchor': ''});
    const tools = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': w('그리기', 'Draw')});
    for (const [kind, names] of Object.entries(NOTE_KINDS)) tools.append(node(doc, 'button', {type: 'button', 'data-user-tool': kind, 'aria-pressed': 'false'}, w(names[0], names[1])));
    const visible = node(doc, 'label', {class: 'cw-toggle'}), box = node(doc, 'input', {type: 'checkbox', 'data-user-visible': ''});
    box.checked = true; visible.append(box, doc.createTextNode(' ' + w('차트에 사용자 작성 보이기', 'Show user-written objects on the chart')));
    state.userToolStatus = node(doc, 'p', {class: 'small', role: 'status', 'data-user-tool-status': ''});
    state.userNotes = node(doc, 'ul', {class: 'cw-user-list', 'data-user-notes': ''});
    const scenarioBox = node(doc, 'fieldset', {class: 'cw-scenario', 'data-user-scenario-form': ''});
    scenarioBox.append(node(doc, 'legend', {}, w('시나리오 쓰기 (상승·횡보·하락 · 핵심 가격 · 조건 · 무효화)', 'Write a scenario (up / sideways / down · key levels · condition · invalidation)')), ...scenarioFields(state, null));
    state.scenarioSave = node(doc, 'button', {type: 'button', 'data-user-scenario-save': ''}, w('시나리오 저장', 'Save scenario'));
    state.swingSlot = node(doc, 'p', {class: 'small', 'data-user-swing-slot': '', hidden: ''}, w('스윙 가정 계산(손익비·수량, 설계 §12.2) 자리 · 이 단계 범위 밖 · 주문 아님 · 가정 계산', 'Swing assumption calculator (reward/risk, size; design §12.2) slot · out of scope here · not an order · assumption only'));
    scenarioBox.append(state.scenarioSave, state.swingSlot);
    state.scenarioForm = scenarioBox;
    state.userScenarios = node(doc, 'ul', {class: 'cw-user-list', 'data-user-scenarios': ''});
    state.userStatus = node(doc, 'p', {class: 'small', role: 'status', 'data-user-status': ''});
    const footer = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': w('이 기기 저장', 'Device storage')});
    footer.append(node(doc, 'button', {type: 'button', 'data-user-clear': 'here'}, w('이 종목·봉 주기 지우기', 'Clear this symbol and interval')), node(doc, 'button', {type: 'button', 'data-user-clear': 'all'}, w('모두 지우기', 'Clear all')),
      node(doc, 'button', {type: 'button', 'data-user-export': ''}, w('이 기기 파일로 내보내기', 'Export to a file on this device')));
    const importLabel = node(doc, 'label', {class: 'cw-field cw-user-import'});
    importLabel.append(doc.createTextNode(w('파일에서 가져오기 (합치기)', 'Import from a file (merge)') + ' '), node(doc, 'input', {type: 'file', accept: 'application/json,.json', 'data-user-import': ''}));
    footer.append(importLabel);
    state.scenarioDetails = node(doc, 'details', {class: 'cw-scenario-new', 'data-user-scenario-new': ''});
    state.scenarioDetails.append(node(doc, 'summary', {}, w('새 시나리오 쓰기', 'Write a new scenario')), scenarioBox);
    section.append(state.userAnchor, tools, visible, state.userToolStatus, node(doc, 'h4', {}, w('차트 노트', 'Chart notes')), state.userNotes, node(doc, 'h4', {}, w('시나리오', 'Scenarios')), state.scenarioDetails, state.userScenarios, footer, state.userStatus);
    return section;
  }

  /* ---------- rendering ---------- */

  function computeBars(state) {
    state.weeklyCode = 'WEEKLY_BARS_MODULE_PENDING';
    state.daily = []; state.weekly = null;
    patternInputs(state);
    if (!state.data) return;
    const R = state.view.ChartRenderer;
    state.daily = R.normalizeBars(dailyView(state.data.bars, state.data.timezone));
    const weekly = weeklyView(state.view, state.data);
    state.weeklyCode = weekly.code;
    if (weekly.bars) { try { state.weekly = R.normalizeBars(weekly.bars); } catch (_) { state.weekly = null; state.weeklyCode = 'WEEKLY_BARS_FAILED'; } }
  }

  async function createRenderer(state, want) {
    const R = state.view.ChartRenderer, callbacks = {
      locale: state.locale, provisionalLabel: words(state, '잠정', 'Prov.'),
      onCrosshair: hit => {
        if (state.disposed) return;
        // While the keyboard drives the cursor, crosshair events from a resting mouse (LWC re-hit-tests it
        // after every scroll or zoom) must not move the readout away from the keyboard bar.
        const keyboard = state.lastInput === 'keyboard' && state.keyboardCursor !== null;
        if (!hit) { paintReadout(state, state.keyboardCursor, state.keyboardCursor !== null ? 'keyboard' : null); return; }
        if (keyboard && hit.index !== state.keyboardCursor) return;
        paintReadout(state, hit.index, state.touching ? 'touch' : hit.index === state.keyboardCursor ? 'keyboard' : 'pointer');
      },
      onRange: () => { if (!state.disposed) paintRange(state); }
    };
    state.rendererCode = 'READY';
    try { return await R.create(state.chartBox, want, callbacks); }
    catch (error) {
      if (state.disposed) throw error;
      state.rendererCode = error && error.message === 'RENDERER_UNAVAILABLE' ? 'RENDERER_UNAVAILABLE' : 'RENDERER_FAILED';
      return R.create(state.chartBox, 'svg', callbacks);
    }
  }

  // One renderer at a time on the chart box: creations are serialised so a late one never wipes a newer one.
  async function ensureRenderer(state) {
    for (;;) {
      if (state.pending) { try { await state.pending; } catch (_) { /* handled by the creator */ } continue; }
      if (state.disposed) return null;
      const want = state.settings.renderer === 'svg' ? 'svg' : 'lwc';
      if (state.renderer && (state.renderer.kind === want || state.rendererCode !== 'READY')) return state.renderer;
      if (state.renderer) { state.renderer.destroy(); state.renderer = null; }
      state.pending = createRenderer(state, want);
      let renderer = null;
      try { renderer = await state.pending; } catch (_) { renderer = null; } finally { state.pending = null; }
      if (!renderer) return null;
      if (state.disposed) { renderer.destroy(); return null; }
      state.renderer = renderer;
      state.rendererStatus.dataset.code = state.rendererCode;
      state.rendererStatus.textContent = state.rendererCode === 'READY' ? '' : words(state, '렌더러 · ', 'Renderer · ') + state.rendererCode + words(state, ' · SVG 대체 경로로 표시', ' · shown with the SVG fallback');
      return renderer;
    }
  }

  async function render(state, {keepRange = null} = {}) {
    const generation = ++state.renderGeneration;
    if (!state.data && !state.renderer) { state.bars = []; setAttr(state, 'data-bar-count', 0); setAttr(state, 'data-provisional-count', 0); state.patterns.key = null; runPatterns(state); paintReadout(state, null, null); paintAll(state); paintUser(state); paintPatterns(state); return; }
    const renderer = await ensureRenderer(state);
    if (!renderer || state.disposed || generation !== state.renderGeneration) return;
    state.bars = state.timeframe === 'weekly' && state.weekly ? state.weekly : state.daily;
    if (state.timeframe === 'weekly' && !state.weekly) { state.timeframe = 'daily'; state.bars = state.daily; }
    state.measure = null; state.measureStart = null; state.keyboardCursor = null; renderer.setMeasure(null);
    state.chartBox.style.height = '';
    if (!state.bars.length) { renderer.setData({bars: [], lines: []}); state.chartBox.dataset.panes = '0'; }
    else {
      try {
        const panes = renderer.setData({bars: state.bars, lines: lines(state)});
        state.chartBox.dataset.panes = String(panes);
        state.chartBox.style.height = renderer.kind === 'lwc' ? (300 + Math.max(0, panes - 2) * 90) + 'px' : 'auto';
      } catch (error) { state.rendererStatus.dataset.code = 'RENDER_INPUT_INVALID'; state.rendererStatus.textContent = 'RENDER_INPUT_INVALID'; state.bars = []; }
      if (keepRange) renderer.setVisibleRange(keepRange);
      else if (state.bars.length) renderer.setVisibleRange({from: Math.max(0, state.bars.length - (state.timeframe === 'weekly' ? 104 : 120)), to: state.bars.length - 1});
    }
    setAttr(state, 'data-bar-count', state.bars.length);
    setAttr(state, 'data-provisional-count', state.bars.filter(bar => !bar.complete).length);
    const patternKey = [state.data ? state.data.bars : null, state.source, state.timeframe, state.patterns.userRules ? state.patterns.userRules.rules.params_sha256 : ''];
    if (!state.patterns.key || patternKey.some((v, i) => v !== state.patterns.key[i])) {
      if (state.patterns.key && state.patterns.key[2] !== state.timeframe) buildExploreControls(state);
      state.patterns.key = patternKey; state.patterns.selected = null; setAttr(state, 'data-pattern-selected', '');
      runPatterns(state);
      if (state.patterns.view === 'user' && !state.patterns.user) state.patterns.view = 'official';
    }
    paintReadout(state, null, null);
    paintAll(state);
    paintUser(state);
    paintPatterns(state);
  }

  function addMeasurePoint(state, hit) {
    if (!hit || !state.bars[hit.index]) return;
    if (!state.measureStart || state.measure) { state.measure = null; state.measureStart = hit; state.renderer.setMeasure(null); }
    else { state.measure = state.view.ChartRenderer.measure(state.bars, state.measureStart, hit); state.renderer.setMeasure(state.measure); }
    paintMeasure(state);
    if (state.measure) state.live.textContent = state.measureOut.textContent;
  }

  function moveCursor(state, index) {
    if (!state.bars.length) return;
    const next = Math.max(0, Math.min(state.bars.length - 1, index));
    state.keyboardCursor = next;
    const span = state.renderer.getVisibleRange();
    if (span && (next < span.from || next > span.to)) state.renderer.scroll(next < span.from ? next - span.from : next - span.to);
    state.renderer.showCrosshair(next);
    paintReadout(state, next, 'keyboard');
  }

  function onKey(state, event) {
    if (!state.renderer || !state.renderer.capabilities.keyboard || !state.bars.length) return;
    const current = state.keyboardCursor !== null ? state.keyboardCursor : state.cursor !== null ? state.cursor : (state.renderer.getVisibleRange() || {to: state.bars.length - 1}).to;
    const step = event.shiftKey ? 10 : 1;
    let handled = true;
    switch (event.key) {
      case 'ArrowLeft': moveCursor(state, current - (state.keyboardCursor === null ? 0 : step)); break;
      case 'ArrowRight': moveCursor(state, current + (state.keyboardCursor === null ? 0 : step)); break;
      case 'Home': state.renderer.setVisibleRange({from: 0, to: Math.min(state.bars.length - 1, 59)}); moveCursor(state, 0); break;
      case 'End': state.renderer.setVisibleRange({from: Math.max(0, state.bars.length - 60), to: state.bars.length - 1}); moveCursor(state, state.bars.length - 1); break;
      case '+': case '=': state.renderer.zoom(0.7); break;
      case '-': case '_': state.renderer.zoom(1.4); break;
      case 'Escape': state.keyboardCursor = null; state.renderer.clearCrosshair(); paintReadout(state, null, null); state.live.textContent = words(state, '십자선 지움', 'Crosshair cleared'); break;
      case 'Enter': {
        // Picks the most recent shown pattern whose span holds the keyboard bar (design §11.3).
        const at = state.keyboardCursor, hit = at === null ? null : viewObjects(state).filter(o => o.startIndex <= at && at <= endIndex(state, o)).sort((a, b) => b.formedIndex - a.formedIndex)[0];
        if (!hit) { handled = false; break; }
        if (state.patterns.selected !== hit.id) selectPattern(state, hit.id, {zoom: false});
        const card = state.patternCards.querySelector('[data-pattern-card="' + (state.view.CSS && state.view.CSS.escape ? state.view.CSS.escape(hit.id) : hit.id) + '"]');
        if (card) card.scrollIntoView({block: 'nearest'});
        break;
      }
      case 'n': case 'N':
        if (state.user.tool && state.keyboardCursor !== null && state.bars[state.keyboardCursor].ohlc) addUserPoint(state, {index: state.keyboardCursor, price: state.bars[state.keyboardCursor].close});
        else handled = false;
        break;
      case 'm': case 'M':
        if (state.measuring && state.keyboardCursor !== null && state.bars[state.keyboardCursor].ohlc) addMeasurePoint(state, {index: state.keyboardCursor, price: state.bars[state.keyboardCursor].close});
        else handled = false;
        break;
      default: handled = false;
    }
    if (handled) event.preventDefault();
  }

  /* ---------- public API ---------- */

  function setData(state, data, source) {
    state.data = data; state.source = data ? source : 'none'; state.symbol = data ? data.symbol : '';
    state.measuring = false; computeBars(state);
    if (state.settings.mode === 'long' && state.weeklyCode === 'READY') state.timeframe = 'weekly'; else if (state.timeframe === 'weekly' && state.weeklyCode !== 'READY') state.timeframe = 'daily';
    return render(state);
  }

  function preview(state) {
    const data = syntheticHistory();
    return setData(state, {...data, indicators: state.view.ResearchIndicators ? state.view.ResearchIndicators.calculate(data.bars) : null}, 'synthetic');
  }

  function update(state, payload) {
    if (state.disposed) return Promise.resolve();
    if (!payload) { if (state.source === 'device') { state.patterns.books.device.clear(); return setData(state, null, 'none'); } return Promise.resolve(); }
    if (!Array.isArray(payload.bars) || !payload.bars.length) return Promise.resolve();
    if (state.source === 'device' && state.data && state.data.symbol === payload.symbol && state.data.readAt === payload.readAt && state.data.bars === payload.bars) {
      state.data = {...state.data, indicators: payload.indicators};
      return state.timeframe === 'daily' ? render(state, {keepRange: state.renderer ? state.renderer.getVisibleRange() : null}) : Promise.resolve();
    }
    return setData(state, {symbol: payload.symbol || '', provider: payload.provider || '', timezone: payload.timezone || 'UTC', currency: payload.currency || '', readAt: payload.readAt || '', bars: payload.bars, indicators: payload.indicators || null}, 'device');
  }

  function dispose(state) {
    if (state.disposed) return;
    state.disposed = true;
    if (state.renderer) state.renderer.destroy();
    state.renderer = null; state.data = null; state.daily = []; state.weekly = null; state.bars = [];
    state.patterns.books.device.clear(); state.patterns.books.synthetic.clear(); state.patterns.official = null; state.patterns.user = null; state.patterns.objects = {official: [], user: []};
    state.engine = {code: 'NO_DATA', series: {}, actions: null};
    if (state.observer) state.observer.disconnect();
    state.view.removeEventListener('pagehide', state.pagehide);
    active.delete(state);
  }

  function build(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en);
    const root = node(doc, 'section', {class: 'card chart-workbench', 'data-chart-workbench': '', 'data-source': 'none', 'data-renderer': 'none', 'data-timeframe': 'daily', 'data-mode': state.settings.mode, 'data-bar-count': '0', 'data-provisional-count': '0', 'data-visible-from': '', 'data-visible-to': '', 'data-measure-state': 'off', 'aria-labelledby': state.id + '-title'});
    root.append(node(doc, 'h2', {id: state.id + '-title'}, w('기술 차트 · 미리보기', 'Technical chart · Preview')),
      node(doc, 'p', {class: 'small', 'data-cw-boundary': ''}, w('TradingView 위젯 아님 · 이 기기에서 그림 · 가격은 RAM에만 · 매매 기능 없음 · 판정·신호 없음', 'Not a TradingView widget · Drawn on this device · Prices stay in RAM · No trading features · No judgement or signal')));
    const toolbar = node(doc, 'div', {class: 'cw-toolbar', role: 'toolbar', 'aria-label': w('차트 도구', 'Chart tools')});
    const group = (label, items, attr) => { const g = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': label}); for (const [value, text] of items) g.append(node(doc, 'button', {type: 'button', [attr]: value, 'aria-pressed': 'false'}, text)); return g; };
    toolbar.append(group(w('모드', 'Mode'), [['long', w('장기', 'Long-term')], ['swing', w('스윙', 'Swing')]], 'data-cw-mode'),
      group(w('봉 주기', 'Interval'), [['daily', w('일봉', 'Daily')], ['weekly', w('주봉', 'Weekly')]], 'data-cw-timeframe'),
      group(w('그리기 방식', 'Renderer'), [['lwc', 'Lightweight Charts'], ['svg', w('SVG 대체', 'SVG fallback')]], 'data-cw-renderer'));
    const tools = node(doc, 'div', {class: 'cw-group', role: 'group', 'aria-label': w('보기', 'View')});
    state.measureButton = node(doc, 'button', {type: 'button', 'data-cw-measure': '', 'aria-pressed': 'false'}, w('측정', 'Measure'));
    tools.append(state.measureButton, node(doc, 'button', {type: 'button', 'data-cw-zoom': 'in', 'aria-label': w('확대', 'Zoom in')}, '+'), node(doc, 'button', {type: 'button', 'data-cw-zoom': 'out', 'aria-label': w('축소', 'Zoom out')}, '−'), node(doc, 'button', {type: 'button', 'data-cw-zoom': 'fit'}, w('전체', 'Fit')),
      node(doc, 'button', {type: 'button', 'data-cw-synthetic': ''}, w('합성 미리보기', 'Synthetic preview')));
    toolbar.append(tools);
    state.sourceLine = node(doc, 'p', {class: 'cw-source', 'data-cw-source': ''});
    state.judgement = node(doc, 'p', {class: 'cw-judgement', 'data-cw-judgement': ''});
    state.weeklyStatus = node(doc, 'p', {class: 'small', 'data-cw-weekly-status': ''});
    state.rendererStatus = node(doc, 'p', {class: 'small', 'data-cw-renderer-status': ''});
    state.readout = node(doc, 'div', {class: 'cw-readout', 'data-cw-readout': '', 'data-tracking': 'off'});
    state.chartBox = node(doc, 'div', {class: 'cw-chart', 'data-cw-chart': '', 'data-panes': '0', tabindex: '0', role: 'group', 'aria-describedby': state.id + '-help'});
    state.limits = node(doc, 'p', {class: 'cw-limits', 'data-cw-limits': '', hidden: ''}, w('SVG 대체 경로 · 기능 제한: 확대·이동·십자선·측정·거래량·보조 지표 창·키보드 이동이 없습니다. 아래 일별 가격 표를 함께 보세요.', 'SVG fallback · Limits: no zoom, pan, crosshair, measure, volume, indicator panes or keyboard movement. Use the daily price table as well.'));
    state.measureOut = node(doc, 'p', {class: 'cw-measure', 'data-cw-measure-out': ''});
    state.indicatorNote = node(doc, 'p', {class: 'small', 'data-cw-indicator-note': ''});
    const help = node(doc, 'p', {class: 'small', id: state.id + '-help'}, w('키보드(차트에 초점): ←/→ 한 봉 · Shift+←/→ 열 봉 · +/− 확대·축소 · Home/End 처음·끝 · Esc 십자선 지우기 · 측정 켜짐에서 M 점 찍기. 폰: 끌어서 이동, 두 손가락 확대, 길게 눌러 값 추적.', 'Keyboard (chart focused): ←/→ one bar · Shift+←/→ ten bars · +/− zoom · Home/End first/last · Esc clear crosshair · M marks a point while measuring. Phone: drag to pan, pinch to zoom, long-press to track values.'));
    state.live = node(doc, 'div', {class: 'sr-only', 'aria-live': 'polite', 'data-cw-live': ''});
    state.modePanel = node(doc, 'div', {class: 'cw-mode-panel', 'data-cw-mode-panel': ''});
    root.append(toolbar, state.sourceLine, state.judgement, state.weeklyStatus, state.rendererStatus, state.readout, state.chartBox, state.limits, state.measureOut, state.indicatorNote, help, state.live, state.modePanel, buildPatternPanel(state), buildUserPanel(state), buildSettings(state), buildNotice(state));
    return root;
  }

  function buildSettings(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en);
    const details = node(doc, 'details', {class: 'cw-settings', 'data-cw-settings': ''});
    details.append(node(doc, 'summary', {}, w('지표·패턴 표시 설정 · 이 기기 저장', 'Indicator and pattern display settings · saved on this device')));
    const fieldset = node(doc, 'fieldset', {}), legend = node(doc, 'legend', {}, w('연구용 지표 (RESEARCH_DISPLAY_ONLY · 일봉)', 'Research indicators (RESEARCH_DISPLAY_ONLY · daily)'));
    fieldset.append(legend);
    const labels = {SMA: 'SMA 5·20·60·120', EMA: 'EMA 20', BOLL: w('볼린저 20/2', 'Bollinger 20/2'), RSI: 'RSI 14', MACD: 'MACD 12/26/9', ATR: 'ATR 14'};
    for (const key of Object.keys(INDICATOR_GROUPS)) {
      const label = node(doc, 'label', {class: 'cw-toggle'}), box = node(doc, 'input', {type: 'checkbox', 'data-cw-indicator': key});
      box.checked = state.settings.indicators[key];
      label.append(box, doc.createTextNode(' ' + labels[key]));
      fieldset.append(label);
    }
    const patterns = node(doc, 'fieldset', {'data-cw-pattern-display': ''});
    patterns.append(node(doc, 'legend', {}, w('패턴 표시 (화면만 · 탐지에 영향 없음)', 'Pattern display (screen only · no effect on detection)')));
    for (const [key, text] of [['ZONES', w('지지·저항 구간', 'Support/resistance zones')], ['BOX', w('박스 돌파·이탈', 'Box breakout/breakdown')], ['DOUBLE', w('이중 바닥·천장', 'Double bottom/top')]]) {
      const label = node(doc, 'label', {class: 'cw-toggle'}), box = node(doc, 'input', {type: 'checkbox', 'data-cw-pattern': key});
      box.checked = state.settings.patterns[key] !== false;
      label.append(box, doc.createTextNode(' ' + text));
      patterns.append(label);
    }
    const explore = node(doc, 'fieldset', {'data-pattern-explore': ''});
    explore.append(node(doc, 'legend', {}, w('사용자 설정 탐색 (pattern-rules/1 민감도 범위 · 지금 봉 주기 값)', 'User-settings exploration (pattern-rules/1 sensitivity sets · current interval)')));
    state.exploreGrid = node(doc, 'div', {class: 'cw-param-grid'});
    state.exploreStatus = node(doc, 'p', {class: 'small', role: 'status', 'data-pattern-explore-status': ''});
    explore.append(state.exploreGrid, node(doc, 'button', {type: 'button', 'data-pattern-explore-run': ''}, w('이 설정으로 탐색', 'Explore with these settings')), node(doc, 'button', {type: 'button', 'data-pattern-explore-reset': ''}, w('기본값으로', 'Back to defaults')),
      node(doc, 'p', {class: 'small'}, w('탐색 결과는 "사용자 설정 탐색"으로 따로 보이며 공식 탐지 이력에 쓰지 않습니다. 바꾼 값과 params 해시를 결과와 함께 적습니다. 탐색 설정은 저장하지 않습니다.', 'Exploration results appear separately as “user-settings exploration” and are never written to the official history. Changed values and the params hash are shown with the result. Exploration settings are not saved.')),
      state.exploreStatus);
    details.append(fieldset, patterns, explore, node(doc, 'p', {class: 'small'}, w('표시 설정은 이 기기 화면에만 적용됩니다. 공식 탐지·규칙 버전·QGV·TARGET에 영향을 주지 않으며, 가격은 저장하지 않습니다.', 'Display settings apply to this screen only. They never affect official detection, rule versions, QGV or TARGET, and no prices are saved.')),
      state.settingsStatus = node(doc, 'p', {class: 'small', role: 'status', 'data-cw-settings-status': ''}));
    return details;
  }

  function buildNotice(state) {
    const doc = state.doc, w = (ko, en) => words(state, ko, en), p = node(doc, 'p', {class: 'small cw-notice', 'data-cw-notice': ''});
    const link = (href, text, extra = {}) => node(doc, 'a', {href, ...extra}, text);
    p.append(doc.createTextNode(w('차트 그리기: TradingView Lightweight Charts™ 5.2.1 (Apache-2.0, 이 사이트에 포함한 파일 · 로고 끔). ', 'Chart drawing: TradingView Lightweight Charts™ 5.2.1 (Apache-2.0, file hosted on this site · logo off). ')),
      node(doc, 'span', {'data-cw-notice-text': ''}, NOTICE_TEXT), doc.createTextNode(' · '),
      link('https://www.tradingview.com/', 'TradingView', {rel: 'noopener noreferrer', target: '_blank', 'data-cw-attribution-link': ''}), doc.createTextNode(' · '),
      link('lightweight-charts-5.2.1.LICENSE.txt', 'LICENSE'), doc.createTextNode(' · '), link('lightweight-charts-5.2.1.NOTICE.txt', 'NOTICE'), doc.createTextNode(' · '),
      link('third-party-notices.txt', w('제3자 고지', 'Third-party notices')));
    return p;
  }

  function wire(state) {
    const root = state.root;
    root.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button || !root.contains(button) || button.disabled) return;
      if (button.dataset.cwMode) {
        state.settings.mode = button.dataset.cwMode; persist(state);
        if (state.settings.mode === 'long' && state.weeklyCode === 'READY' && state.timeframe !== 'weekly') switchTimeframe(state, 'weekly'); else paintAll(state);
      } else if (button.dataset.cwTimeframe) switchTimeframe(state, button.dataset.cwTimeframe);
      else if (button.dataset.cwRenderer) { state.settings.renderer = button.dataset.cwRenderer; persist(state); void render(state); }
      else if (button.hasAttribute('data-cw-measure')) { state.user.tool = null; state.user.points = []; paintUserTools(state); state.measuring = !state.measuring; state.measure = null; state.measureStart = null; if (state.renderer) state.renderer.setMeasure(null); paintButtons(state); paintMeasure(state); }
      else if (button.dataset.cwZoom && state.renderer) { if (button.dataset.cwZoom === 'fit') state.renderer.fit(); else state.renderer.zoom(button.dataset.cwZoom === 'in' ? 0.7 : 1.4); }
      else if (button.hasAttribute('data-cw-synthetic')) void preview(state);
      else if (button.dataset.patternViewButton === 'scenario') { state.scenarioDetails.open = true; state.scenarioForm.scrollIntoView({block: 'nearest'}); const first = state.scenarioForm.querySelector('select'); if (first) first.focus(); }
      else if (button.dataset.patternViewButton) { if (['official', 'user'].includes(button.dataset.patternViewButton)) { state.patterns.view = button.dataset.patternViewButton; state.patterns.selected = null; setAttr(state, 'data-pattern-selected', ''); paintPatterns(state); } }
      else if (button.hasAttribute('data-pattern-show-all')) { state.patterns.showAll = !state.patterns.showAll; paintPatterns(state); }
      else if (button.dataset.patternCard) selectPattern(state, button.dataset.patternCard);
      else if (button.hasAttribute('data-pattern-more')) { state.patterns.expanded = !state.patterns.expanded; paintCards(state); }
      else if (button.hasAttribute('data-pattern-explore-run')) void runUserSettings(state);
      else if (button.hasAttribute('data-pattern-explore-reset')) resetUserSettings(state);
      else if (button.dataset.userTool) startTool(state, button.dataset.userTool);
      else if (button.dataset.userSave) saveUserItem(state, button.dataset.userSave);
      else if (button.dataset.userDelete) deleteUserItem(state, button.dataset.userDelete);
      else if (button.hasAttribute('data-user-scenario-save')) addScenario(state);
      else if (button.dataset.userClear) clearUser(state, button.dataset.userClear);
      else if (button.hasAttribute('data-user-export')) exportUser(state);
    });
    root.addEventListener('change', event => {
      const box = event.target;
      if (box.hasAttribute && box.hasAttribute('data-user-visible')) { state.user.visible = box.checked; drawPatterns(state); return; }
      if (box.hasAttribute && box.hasAttribute('data-user-import')) { void importUser(state, box); return; }
      if (box.dataset && box.dataset.cwPattern) { state.settings.patterns[box.dataset.cwPattern] = box.checked; persist(state); state.patterns.selected = null; paintPatterns(state); return; }
      if (box.dataset && box.dataset.cwIndicator) { state.settings.indicators[box.dataset.cwIndicator] = box.checked; persist(state); if (state.bars.length) void render(state, {keepRange: state.renderer ? state.renderer.getVisibleRange() : null}); }
    });
    state.chartBox.addEventListener('keydown', event => { state.lastInput = 'keyboard'; onKey(state, event); });
    for (const type of ['pointermove', 'wheel']) state.chartBox.addEventListener(type, () => { state.lastInput = 'pointer'; }, {passive: true});
    // A tap or click (little movement, short press) marks a measure point while measuring.
    state.chartBox.addEventListener('pointerdown', event => { state.lastInput = 'pointer'; if (event.pointerType === 'touch') state.touching = true; state.press = {x: event.clientX, y: event.clientY, at: event.timeStamp}; });
    state.chartBox.addEventListener('pointerup', event => {
      const press = state.press; state.press = null;
      if (event.pointerType === 'touch') { state.touching = false; if (state.readout.dataset.tracking === 'touch') state.readout.dataset.tracking = 'touch-held'; }
      if ((!state.measuring && !state.user.tool) || !press || !state.renderer || Math.hypot(event.clientX - press.x, event.clientY - press.y) > 6 || event.timeStamp - press.at > 500) return;
      const hit = state.renderer.pointAt(event.clientX, event.clientY);
      if (hit && state.user.tool) addUserPoint(state, hit); else if (hit) addMeasurePoint(state, hit);
    });
    state.chartBox.addEventListener('pointercancel', event => { state.press = null; if (event.pointerType === 'touch') state.touching = false; });
  }

  function persist(state) {
    const ok = writeSettings(state.storage, state.settings);
    state.settingsStatus.dataset.code = ok ? 'SAVED' : 'STORAGE_UNAVAILABLE';
    state.settingsStatus.textContent = ok ? words(state, '이 기기에 저장함(표시 설정만)', 'Saved on this device (display settings only)') : 'STORAGE_UNAVAILABLE';
  }

  function switchTimeframe(state, next) {
    if (next === state.timeframe || (next === 'weekly' && !state.weekly)) { paintAll(state); return; }
    const source = state.bars, span = state.renderer ? state.renderer.getVisibleRange() : null, target = next === 'weekly' ? state.weekly : state.daily;
    const keep = span && source.length ? state.view.ChartRenderer.mapRange(source, target, span) : null;
    state.timeframe = next;
    void render(state, {keepRange: keep});
  }

  let counter = 0;
  function mount(host, options = {}) {
    const doc = host.ownerDocument, view = doc.defaultView;
    let storage = null; try { storage = options.storage || view.localStorage; } catch (_) { storage = null; }
    const userStore = options.userStore || createDeviceUserStore(storage), loaded = userStore.load();
    const state = {doc, view, host, storage, userStore, user: {items: loaded.items, code: loaded.code, tool: null, points: [], editing: null, visible: true}, locale: options.locale, qgvHref: options.qgvHref || null, id: 'cw' + (++counter), settings: readSettings(storage), data: null, source: 'none', symbol: '',
      daily: [], weekly: null, bars: [], timeframe: 'daily', weeklyCode: 'WEEKLY_BARS_MODULE_PENDING', renderer: null, rendererCode: 'READY', pending: null, renderGeneration: 0,
      cursor: null, keyboardCursor: null, lastInput: null, press: null, measuring: false, measureStart: null, measure: null, touching: false, disposed: false,
      engine: {code: 'NO_DATA', series: {}, actions: null},
      patterns: {view: 'official', code: 'NO_DATA', official: null, user: null, userRules: null, objects: {official: [], user: []}, counts: null, records: 0, selected: null, showAll: false, expanded: false, key: null,
        books: view.PatternHistory ? {device: view.PatternHistory.createBook(), synthetic: view.PatternHistory.createBook()} : {device: {clear() {}}, synthetic: {clear() {}}}}};
    state.root = build(state);
    host.replaceChildren(state.root);
    wire(state);
    buildExploreControls(state);
    state.userStatus.dataset.code = loaded.code;
    state.userStatus.textContent = words(state, '이 기기에만 저장 · ', 'Saved on this device only · ') + loaded.items.length + words(state, '개', ' items') + (loaded.code === 'LOADED' || loaded.code === 'EMPTY' ? '' : ' · ' + loaded.code)
      + (loaded.unreadable ? words(state, ' · 읽지 못한 항목 ' + loaded.unreadable + '개는 지우지 않고 그대로 둡니다', ' · ' + loaded.unreadable + ' unreadable items are kept as they are') : '')
      + (loaded.code === 'STORE_INVALID' ? words(state, ' · 저장된 값을 읽을 수 없어 덮어쓰지 않습니다(모두 지우기 전까지 저장하지 않음)', ' · the stored value cannot be read, so it is not overwritten (no saving until Clear all)') : '');
    active.add(state);
    state.pagehide = () => dispose(state);
    view.addEventListener('pagehide', state.pagehide);
    if (view.MutationObserver) { state.observer = new view.MutationObserver(() => { if (!host.isConnected || !state.root.isConnected) dispose(state); }); state.observer.observe(doc.documentElement, {childList: true, subtree: true}); }
    paintAll(state); paintReadout(state, null, null);
    void render(state);
    return Object.freeze({update: payload => update(state, payload), clear: () => setData(state, null, 'none'), dispose: () => dispose(state), preview: () => preview(state)});
  }

  function disposeAll() { for (const state of [...active]) dispose(state); }

  return Object.freeze({SETTINGS_KEY, SETTINGS_SCHEMA, SYNTHETIC_LABEL, SYNTHETIC_PATTERN_LABEL, EXPLORE_GRID, readSettings, writeSettings, dailyView, weeklyView, continuityCodes, syntheticHistory,
    syntheticActions, applyChanges, minBars, patternObjects, USER_KEY, USER_SCHEMA, USER_LIMIT, validUserObject, createDeviceUserStore, parseUserExport, mergeUserItems, mount, disposeAll});
});
