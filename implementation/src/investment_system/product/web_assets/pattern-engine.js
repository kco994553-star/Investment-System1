/* Pattern engine (TECHNICAL_PATTERN_CHART_V1_DESIGN §8-§9): engine bars, split segments, swing pivots, support/resistance
   zones, box breakout/breakdown, double bottom/top and the common state machine (FORMED/CONFIRMED/FAILED/INVALIDATED/EXPIRED).
   Pure functions: no network, storage, DOM, QGV or clock reads. Python reference: investment_system/technical/patterns.py
   (vectors: tests/fixtures/pattern_engine_reference_v1.json). ATR14 comes from ResearchIndicators (chart-indicators.js);
   bars come from ChartBars (chart-bars.js). Parameters are pattern-rules/1 research defaults, never validated investment
   rules; nothing here is a probability, win rate, percentage or score. Each transition carries known_at: the session date of
   the complete bar at which it becomes knowable (a pivot at bar i is known at bar i + k). Only the shipped
   PatternConfigDefaults object counts as the official rule set; any other rules object is a user-settings run. */
(function (root, factory) {
  const node = typeof module === 'object' && module.exports;
  const api = factory(node ? require('./chart-indicators.js') : root.ResearchIndicators, node ? require('./chart-bars.js') : root.ChartBars,
    node ? require('./pattern-config-defaults.js') : root.PatternConfigDefaults);
  if (node) module.exports = api; else root.PatternEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (ResearchIndicators, ChartBars, Defaults) {
  'use strict';
  const ROLE = 'RESEARCH_DEFAULT';
  const STRUCTURE_LABELS = Object.freeze({HH_HL: '고점·저점 상승', LH_LL: '고점·저점 하락', MIXED: '혼재'});
  function fail(code) { throw new Error(code); }
  function canonicalJson(value) {
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
    if (typeof value === 'number') { if (!Number.isFinite(value)) fail('PATTERN_RULES_INVALID'); return JSON.stringify(value); }
    if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
    if (typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonicalJson(value[k])).join(',') + '}';
    fail('PATTERN_RULES_INVALID');
  }
  function checkRules(rules) {
    if (!rules || typeof rules !== 'object' || rules.schema !== 'pattern-rules/1' || rules.status !== ROLE || !rules.params || typeof rules.params !== 'object'
      || typeof rules.params_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(rules.params_sha256)) fail('PATTERN_RULES_INVALID');
    return rules;
  }
  function param(rules, name, timeframe) {
    const value = rules.params[name];
    if (value === undefined) fail('PATTERN_RULES_INVALID');
    return value && typeof value === 'object' && Object.prototype.hasOwnProperty.call(value, timeframe) ? value[timeframe] : value;
  }
  // The run mode is OFFICIAL only for the shipped frozen defaults; anything else never enters the official history (§8.7, §11.4).
  function runMode(rules) { return rules === Defaults ? 'OFFICIAL' : 'USER_SETTINGS'; }

  function engineBars(series) {
    const src = series.bars, timeframe = series.timeframe;
    let last = -1;
    src.forEach((b, i) => { if (b.state === 'COMPLETE') last = i; });
    const out = src.slice(0, last + 1).map((b, i) => {
      const ok = b.state === 'COMPLETE' && b.ohlc === 'PRESENT', daily = timeframe === 'D';
      return {i, date: daily ? b.session_date : b.week_start, first_session: daily ? b.session_date : b.first_session, last_session: daily ? b.session_date : b.last_session,
        known_at: daily ? (b.state === 'COMPLETE' ? b.session_date : null) : b.known_at, timestamp: b.timestamp, ok,
        open: ok ? b.open : null, high: ok ? b.high : null, low: ok ? b.low : null, close: ok ? b.close : null,
        volume: ok && b.volume_state === 'REPORTED' ? b.volume : null};
    });
    let following = null;
    for (let i = out.length - 1; i >= 0; i--) { if (out[i].known_at === null) out[i].known_at = following; following = out[i].known_at; }
    return out;
  }
  function segments(bars, actions) {
    actions = actionsOf(actions);
    const cuts = [];
    for (const d of actions.status === 'AVAILABLE' ? actions.splits : []) {
      const at = bars.find(b => b.last_session >= d);
      if (at && at.i > 0 && !cuts.includes(at.i)) cuts.push(at.i);
    }
    cuts.sort((a, b) => a - b);
    const starts = [0, ...cuts], ends = [...cuts.map(c => c - 1), bars.length - 1], out = [];
    starts.forEach((s, n) => { if (s <= ends[n]) out.push([s, ends[n]]); });
    return out;
  }
  function actionsOf(value) {
    return value && typeof value === 'object' && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, 'splits') && Object.prototype.hasOwnProperty.call(value, 'status') ? value : ChartBars.corporateActions(value);
  }
  function atr14(bars) {
    if (!bars.length) return [];
    const r = ResearchIndicators.calculate(bars.map(b => ({timestamp: b.timestamp, session_status: 'COMPLETE', open: b.open, high: b.high, low: b.low, close: b.close, adjusted_close: null})));
    if (r.state === 'NOT_AVAILABLE') return bars.map(() => null);
    return [...r.indicators.find(x => x.indicator_id === 'ATR_14').values];
  }
  function prepare(series, rules, actions) {
    checkRules(rules);
    if (!series || series.schema !== ChartBars.SCHEMA || !['D', 'W'].includes(series.timeframe)) fail('CHART_BARS_INPUT_INVALID');
    const bars = engineBars(series), normalized = actionsOf(actions), segs = bars.length ? segments(bars, normalized) : [], atr = bars.map(() => null);
    for (const [s, e] of segs) atr14(bars.slice(s, e + 1)).forEach((v, n) => { atr[s + n] = v; });
    return {symbol: series.symbol, timeframe: series.timeframe, rule_version: rules.rule_version, params_sha256: rules.params_sha256, run_mode: runMode(rules),
      rules, bars, atr, segments: segs, actions: normalized};
  }
  function judgement(ctx, start, end) { return ChartBars.continuity(ctx.actions, ctx.bars[start].first_session, ctx.bars[end].last_session); }
  function objectId(ctx, kind, ...anchors) { return [kind, ctx.symbol, ctx.timeframe, ctx.rule_version, ...anchors].join('|'); }

  function candidate(bars, i, k, key, sign) {
    const here = bars[i][key];
    for (let j = i - k; j < i; j++) if (!(sign * (here - bars[j][key]) > 0)) return false;
    for (let j = i + 1; j <= i + k; j++) if (!(sign * (here - bars[j][key]) >= 0)) return false;
    return true;
  }
  function pivotTransition(ctx, i, kind, price, atrValue, t, k) {
    const bars = ctx.bars;
    return {object_id: objectId(ctx, 'PIVOT', kind, bars[i].date), object_kind: 'PIVOT', event: 'PIVOT_CONFIRMED', timeframe: ctx.timeframe, rule_version: ctx.rule_version,
      params_sha256: ctx.params_sha256, anchor_index: i, anchor_at: bars[i].date, known_index: t, known_at: bars[t].known_at,
      detail: {pivot: kind, price, atr: atrValue}, judgement: judgement(ctx, i - k, t)};
  }
  function pivots(ctx) {
    const tf = ctx.timeframe, k = param(ctx.rules, 'PIVOT_K', tf), swing = param(ctx.rules, 'SWING_MIN_ATR'), bars = ctx.bars, atr = ctx.atr;
    const transitions = [], skipped = {MISSING_BARS_IN_WINDOW: 0, ATR_UNAVAILABLE: 0}, confirmedAll = [];
    for (const [s, e] of ctx.segments) {
      const confirmed = [];
      for (let t = s; t <= e; t++) {
        const i = t - k;
        if (i - k < s) continue;
        if (!bars.slice(i - k, t + 1).every(b => b.ok)) { skipped.MISSING_BARS_IN_WINDOW++; continue; }
        let kinds = [['HIGH', 'high', 1], ['LOW', 'low', -1]].filter(([, key, sign]) => candidate(bars, i, k, key, sign)).map(([kind]) => kind);
        if (!kinds.length) continue;
        if (atr[t] === null) { skipped.ATR_UNAVAILABLE++; continue; }
        if (kinds.length === 2 && confirmed.length && confirmed[confirmed.length - 1].pivot === 'HIGH') kinds = ['LOW', 'HIGH'];
        for (const kind of kinds) {
          const price = bars[i][kind === 'HIGH' ? 'high' : 'low'], last = confirmed.length ? confirmed[confirmed.length - 1] : null;
          let event = null;
          if (last === null) event = 'PIVOT_CONFIRMED';
          else if (last.pivot !== kind) { const amplitude = kind === 'HIGH' ? price - last.price : last.price - price; if (amplitude >= swing * atr[t]) event = 'PIVOT_CONFIRMED'; }
          else if (kind === 'HIGH' ? price > last.price : price < last.price) {
            event = 'PIVOT_CONFIRMED'; confirmed.pop();
            transitions.push({...pivotTransition(ctx, last.anchor_index, kind, last.price, last.atr, t, k), event: 'SUPERSEDED', superseded_by: objectId(ctx, 'PIVOT', kind, bars[i].date)});
          }
          if (event) {
            const record = pivotTransition(ctx, i, kind, price, atr[t], t, k);
            transitions.push(record);
            confirmed.push({pivot: kind, anchor_index: i, price, atr: atr[t], object_id: record.object_id, anchor_at: bars[i].date, known_index: t, known_at: bars[t].known_at});
          }
        }
      }
      confirmedAll.push(...confirmed);
    }
    return {transitions, confirmed: confirmedAll, skipped};
  }
  function structure(confirmed) {
    const highs = confirmed.filter(p => p.pivot === 'HIGH').map(p => p.price).slice(-2), lows = confirmed.filter(p => p.pivot === 'LOW').map(p => p.price).slice(-2);
    if (highs.length < 2 || lows.length < 2) return {state: 'NOT_AVAILABLE', reason_code: 'INSUFFICIENT_PIVOTS', label_ko: null};
    const state = highs[1] > highs[0] && lows[1] > lows[0] ? 'HH_HL' : highs[1] < highs[0] && lows[1] < lows[0] ? 'LH_LL' : 'MIXED';
    return {state, reason_code: null, label_ko: STRUCTURE_LABELS[state]};
  }
  function runPivots(series, rules, actions) {
    const ctx = prepare(series, rules, actions), result = pivots(ctx);
    return {role: ROLE, label_ko: rules.label_ko, rule_version: ctx.rule_version, params_sha256: ctx.params_sha256, run_mode: ctx.run_mode, timeframe: ctx.timeframe,
      segments: ctx.segments, transitions: result.transitions, skipped: result.skipped, structure: structure(result.confirmed)};
  }

  // ------------------------------------------------------------ signals, zones and the common state machine (P1-3..P1-5)
  // Per bar t of a segment, in this fixed order: A. live objects take bar t (signals: expiry, missing bar, confirmation,
  // invalidation, failure, observation end; zones: expiry, break; first bar of a later segment: every live object becomes
  // NOT_JUDGEABLE / CORPORATE_ACTION_IN_WINDOW), B. pivots known at t, C. zone re-clustering when a pivot changed,
  // D. new signals formed at t (box when none is live, double bottom/top for a new pivot). A new signal is first checked on
  // the next bar. Thresholds use the formation-bar ATR and never move.
  const PREVIEW_NOTE_KO = '잠정 봉 기준 조건 충족 · 확정 아님';
  const hit = (rule, close) => (rule[0] === 'ABOVE' ? close > rule[1] : close < rule[1]);
  const failed = (rule, close) => (rule[0] === 'IN_RANGE' ? rule[1] <= close && close <= rule[2] : hit(rule, close));
  function avg(values) { let total = 0; for (const v of values) total = total + v; return total / values.length; }
  function volumeNote(ctx, segStart, t) {
    const n = param(ctx.rules, 'VOL_AVG_N', ctx.timeframe), mult = param(ctx.rules, 'VOL_MULT'), bars = ctx.bars;
    if (bars[t].volume === null) return {state: 'NOT_AVAILABLE', reason_code: 'VOLUME_MISSING'};
    if (t - n < segStart) return {state: 'NOT_AVAILABLE', reason_code: 'INSUFFICIENT_BARS'};
    const previous = bars.slice(t - n, t).map(b => b.volume);
    if (previous.some(v => v === null)) return {state: 'NOT_AVAILABLE', reason_code: 'VOLUME_MISSING'};
    return {state: bars[t].volume >= mult * avg(previous) ? 'WITH_VOLUME' : 'WITHOUT_VOLUME', reason_code: null};
  }
  function makeRun(ctx) {
    const r = {ctx, out: [], seen: new Set(), failWindow: param(ctx.rules, 'FAIL_WINDOW', ctx.timeframe)};
    r.emit = (obj, event, t, state, detail) => {
      const bars = ctx.bars;
      r.out.push({object_id: obj.object_id, object_kind: obj.object_kind, pattern: obj.pattern, event, state, timeframe: ctx.timeframe, rule_version: ctx.rule_version,
        params_sha256: ctx.params_sha256, anchor_index: obj.start, anchor_at: bars[obj.start].date, known_index: t, known_at: bars[t].known_at, detail, judgement: judgement(ctx, obj.start, t)});
    };
    r.end = (obj, event, t, state, detail) => { obj.state = state; r.emit(obj, event, t, state, detail); };
    r.signal = (pattern, oid, start, t, confirm, invalidation, fail, expireAfter, atrValue, detail) => {
      const obj = {object_id: oid, object_kind: 'SIGNAL', pattern, start, state: 'FORMED', confirm, invalidation, fail, expire_after: expireAfter, confirmed_index: null};
      r.seen.add(oid);
      r.emit(obj, 'FORMED', t, 'FORMED', {...detail, confirm_level: confirm[1], invalidation_level: invalidation[1], atr: atrValue, atr_at: ctx.bars[t].date, expire_after_index: expireAfter});
      return obj;
    };
    r.step = (obj, t, segStart) => {
      const bar = ctx.bars[t];
      if (obj.state === 'FORMED') {
        if (t > obj.expire_after) return r.end(obj, 'EXPIRED', t, 'EXPIRED', {});
        if (!bar.ok) return r.end(obj, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {reason_codes: ['MISSING_BARS_IN_WINDOW']});
        if (hit(obj.confirm, bar.close)) { obj.state = 'CONFIRMED'; obj.confirmed_index = t; return r.emit(obj, 'CONFIRMED', t, 'CONFIRMED', {gap: hit(obj.confirm, bar.open), volume: volumeNote(ctx, segStart, t)}); }
        if (hit(obj.invalidation, bar.close)) return r.end(obj, 'INVALIDATED', t, 'INVALIDATED', {});
      } else if (obj.state === 'CONFIRMED') {
        if (!bar.ok) return r.end(obj, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {reason_codes: ['MISSING_BARS_IN_WINDOW']});
        if (failed(obj.fail, bar.close)) return r.end(obj, 'FAILED', t, 'FAILED', {});
        if (t - obj.confirmed_index >= r.failWindow) { obj.ended = true; return r.emit(obj, 'OBSERVATION_ENDED', t, 'CONFIRMED', {}); }
      }
      return undefined;
    };
    r.live = obj => (obj.object_kind === 'ZONE' ? obj.state === 'ACTIVE' : obj.state === 'FORMED' || (obj.state === 'CONFIRMED' && !obj.ended));
    return r;
  }
  function clusters(items, tol) {
    const groups = []; let current = [];
    for (const item of items) { if (current.length && item.price - current[current.length - 1].price > tol) { groups.push(current); current = []; } current.push(item); }
    if (current.length) groups.push(current);
    const out = [];
    while (groups.length) {
      const g = groups.shift();
      if (g.length > 1 && g[g.length - 1].price - g[0].price > 2 * tol) {
        const gaps = g.slice(0, -1).map((x, n) => g[n + 1].price - x.price), cut = gaps.indexOf(Math.max(...gaps)) + 1;
        groups.unshift(g.slice(0, cut), g.slice(cut));
      } else out.push(g);
    }
    return out;
  }
  const dateList = (ctx, anchors) => anchors.map(a => ctx.bars[a].date);
  function recluster(r, ctx, zones, confirmed, t, s, p, tolAtr) {
    const tol = tolAtr * ctx.atr[t], lookback = p('ZONE_LOOKBACK');
    const members = confirmed.filter(c => c.anchor_index >= Math.max(s, t - lookback + 1)).sort((a, b) => a.price - b.price || a.anchor_index - b.anchor_index);
    const fresh = [];
    for (const g of clusters(members, tol)) {
      if (g.length < p('ZONE_MIN_TOUCHES')) continue;
      const anchors = g.map(c => c.anchor_index).sort((a, b) => a - b), kinds = new Set(g.map(c => c.pivot));
      fresh.push([objectId(ctx, 'ZONE', dateList(ctx, anchors).join(',')), g, anchors, kinds.size > 1 ? 'MIXED' : kinds.has('HIGH') ? 'RESISTANCE' : 'SUPPORT']);
    }
    const ids = new Set(fresh.map(f => f[0]));
    for (const z of zones) if (z.state === 'ACTIVE' && !ids.has(z.object_id)) r.end(z, 'SUPERSEDED', t, 'SUPERSEDED', {});
    for (const [oid, g, anchors, role] of fresh) {
      if (r.seen.has(oid)) continue;
      r.seen.add(oid);
      const z = {object_id: oid, object_kind: 'ZONE', pattern: 'SUPPORT_RESISTANCE_ZONE', start: anchors[0], state: 'ACTIVE', low: g[0].price, high: g[g.length - 1].price, atr: ctx.atr[t], formed_index: t, last_touch: anchors[anchors.length - 1]};
      const close = ctx.bars[t].close;
      z.side = close > z.high ? 'ABOVE' : close < z.low ? 'BELOW' : 'INSIDE';
      zones.push(z);
      r.emit(z, 'ACTIVE', t, 'ACTIVE', {low: z.low, high: z.high, touches: g.length, role, close_side: z.side, role_mixed: role === 'MIXED', atr: z.atr, atr_at: ctx.bars[t].date, anchors: dateList(ctx, anchors)});
    }
  }
  function naCandidate(r, pattern, oid, start, t) {
    if (r.seen.has(oid)) return;
    r.seen.add(oid);
    r.emit({object_id: oid, object_kind: 'SIGNAL', pattern, start}, 'NOT_JUDGEABLE', t, 'NOT_JUDGEABLE', {reason_codes: ['MISSING_BARS_IN_WINDOW']});
  }
  function formBox(r, ctx, confirmed, t, s, p, bufferAtr, tolAtr) {
    const bars = ctx.bars, atr = ctx.atr[t], tol = tolAtr * atr, loLen = p('BOX_MIN_BARS'), hiLen = p('BOX_MAX_BARS'), hMin = p('BOX_HEIGHT_ATR').min, hMax = p('BOX_HEIGHT_ATR').max;
    const pool = confirmed.filter(c => c.anchor_index >= Math.max(s, t - hiLen + 1));
    for (const start of [...new Set(pool.map(c => c.anchor_index))].sort((a, b) => a - b)) {
      const length = t - start + 1;
      if (!(loLen <= length && length <= hiLen)) continue;
      const inside = pool.filter(c => c.anchor_index >= start), highs = inside.filter(c => c.pivot === 'HIGH'), lows = inside.filter(c => c.pivot === 'LOW');
      if (!highs.length || !lows.length) continue;
      const upperPrice = Math.max(...highs.map(c => c.price)), lowerPrice = Math.min(...lows.map(c => c.price));
      const upper = highs.filter(c => c.price >= upperPrice - tol), lower = lows.filter(c => c.price <= lowerPrice + tol);
      if (upper.length < 2 || lower.length < 2 || !upper.concat(lower).some(c => c.anchor_index === start)) continue;
      const window = bars.slice(start, t + 1);
      if (window.some(b => b.ok && !(lowerPrice <= b.close && b.close <= upperPrice))) continue;
      const height = upperPrice - lowerPrice;
      if (!(hMin * atr <= height && height <= hMax * atr)) continue;
      const anchorDates = dateList(ctx, upper.concat(lower).map(c => c.anchor_index).sort((a, b) => a - b)), anchors = anchorDates.join(','), boxId = objectId(ctx, 'BOX', anchors);
      if (!window.every(b => b.ok)) { naCandidate(r, 'BOX', boxId, start, t); continue; }
      if (r.seen.has(boxId)) continue;
      r.seen.add(boxId);
      const buf = bufferAtr * atr, expire = start + hiLen - 1;
      const detail = {box_id: boxId, upper: upperPrice, lower: lowerPrice, upper_touches: upper.length, lower_touches: lower.length, anchors: anchorDates};
      return [r.signal('BOX_BREAKOUT_UP', objectId(ctx, 'BOX_BREAKOUT_UP', anchors), start, t, ['ABOVE', upperPrice + buf], ['BELOW', lowerPrice - buf], ['IN_RANGE', lowerPrice, upperPrice], expire, atr, detail),
        r.signal('BOX_BREAKDOWN', objectId(ctx, 'BOX_BREAKDOWN', anchors), start, t, ['BELOW', lowerPrice - buf], ['ABOVE', upperPrice + buf], ['IN_RANGE', lowerPrice, upperPrice], expire, atr, detail)];
    }
    return null;
  }
  function formDouble(r, ctx, confirmed, p2, t, s, p, bufferAtr) {
    const bars = ctx.bars, atr = ctx.atr[t], bottom = p2.pivot === 'LOW', pattern = bottom ? 'DOUBLE_BOTTOM' : 'DOUBLE_TOP';
    const sepMin = p('DB_SEP_MIN'), sepMax = p('DB_SEP_MAX'), buf = bufferAtr * atr, a2 = p2.anchor_index;
    const candidates = confirmed.filter(c => c.pivot === p2.pivot && c.anchor_index < a2).sort((a, b) => b.anchor_index - a.anchor_index);
    for (const p1 of candidates) {
      const a1 = p1.anchor_index, sep = a2 - a1;
      if (sep < sepMin) continue;
      if (sep > sepMax) break;
      if (Math.abs(p2.price - p1.price) > p('DB_TOL_ATR') * atr) continue;
      const between = confirmed.filter(c => c.pivot !== p2.pivot && a1 < c.anchor_index && c.anchor_index < a2).map(c => c.price);
      if (!between.length) continue;
      const neck = bottom ? Math.max(...between) : Math.min(...between), edge = bottom ? Math.min(p1.price, p2.price) : Math.max(p1.price, p2.price);
      const depth = bottom ? neck - Math.max(p1.price, p2.price) : Math.min(p1.price, p2.price) - neck;
      if (depth < p('DB_DEPTH_ATR') * atr) continue;
      if (bars.slice(a1, a2 + 1).some(b => b.ok && (bottom ? b.close < edge : b.close > edge))) continue;
      const level = bottom ? neck + buf : neck - buf;
      if (bars.slice(a2 + 1, t + 1).some(b => b.ok && (bottom ? b.close > level : b.close < level))) continue;
      const oid = objectId(ctx, pattern, bars[a1].date, bars[a2].date);
      if (!bars.slice(a1, t + 1).every(b => b.ok)) { naCandidate(r, pattern, oid, a1, t); return null; }
      if (r.seen.has(oid)) return null;
      const detail = {p1: p1.price, p2: p2.price, neckline: neck, p1_at: bars[a1].date, p2_at: bars[a2].date, separation_bars: sep};
      return bottom ? r.signal(pattern, oid, a1, t, ['ABOVE', level], ['BELOW', edge - buf], ['BELOW', neck], t + sep, atr, detail)
        : r.signal(pattern, oid, a1, t, ['BELOW', level], ['ABOVE', edge + buf], ['ABOVE', neck], t + sep, atr, detail);
    }
    return null;
  }
  function run(series, rules, actions) {
    const ctx = prepare(series, rules, actions), piv = pivots(ctx), byBar = new Map();
    for (const tr of piv.transitions) { if (!byBar.has(tr.known_index)) byBar.set(tr.known_index, []); byBar.get(tr.known_index).push(tr); }
    const r = makeRun(ctx), tf = ctx.timeframe, bars = ctx.bars, atr = ctx.atr, p = name => param(rules, name, tf);
    const bufferAtr = p('BREAK_BUFFER_ATR'), tolAtr = p('ZONE_TOL_ATR'), skipped = {...piv.skipped};
    let priorLive = [];
    ctx.segments.forEach(([s, e], n) => {
      const signals = [], zones = []; let confirmed = [], liveBox = null;
      if (n > 0) for (const obj of priorLive) r.end(obj, 'NOT_JUDGEABLE', s, 'NOT_JUDGEABLE', {reason_codes: ['CORPORATE_ACTION_IN_WINDOW']});
      for (let t = s; t <= e; t++) {
        const bar = bars[t];
        for (const obj of signals) if (r.live(obj)) r.step(obj, t, s);
        for (const z of zones) {
          if (z.state !== 'ACTIVE' || z.formed_index >= t) continue;
          if (t - z.last_touch + 1 > p('ZONE_LOOKBACK')) r.end(z, 'EXPIRED', t, 'EXPIRED', {});
          else if (bar.ok && z.side !== 'ABOVE' && bar.close > z.high + bufferAtr * z.atr) r.end(z, 'BROKEN', t, 'BROKEN', {direction: 'UP'});
          else if (bar.ok && z.side !== 'BELOW' && bar.close < z.low - bufferAtr * z.atr) r.end(z, 'BROKEN', t, 'BROKEN', {direction: 'DOWN'});
        }
        if (liveBox && !liveBox.some(o => r.live(o))) liveBox = null;
        const events = byBar.get(t) || [], newPivots = [];
        for (const tr of events) {
          r.out.push(tr);
          if (tr.event === 'SUPERSEDED') confirmed = confirmed.filter(c => c.object_id !== tr.object_id);
          else { const item = {object_id: tr.object_id, pivot: tr.detail.pivot, anchor_index: tr.anchor_index, price: tr.detail.price, anchor_at: tr.anchor_at}; confirmed.push(item); newPivots.push(item); }
        }
        if (events.length && atr[t] !== null) recluster(r, ctx, zones, confirmed, t, s, p, tolAtr);
        if (atr[t] === null) continue;
        if (!liveBox) { liveBox = formBox(r, ctx, confirmed, t, s, p, bufferAtr, tolAtr); if (liveBox) signals.push(...liveBox); }
        for (const item of newPivots) { const obj = formDouble(r, ctx, confirmed, item, t, s, p, bufferAtr); if (obj) signals.push(obj); }
      }
      priorLive = signals.concat(zones).filter(o => r.live(o));
    });
    const objects = new Map();
    for (const tr of r.out) objects.set(tr.object_id, {object_id: tr.object_id, object_kind: tr.object_kind, pattern: tr.pattern === undefined ? null : tr.pattern,
      state: tr.object_kind !== 'PIVOT' ? tr.state : tr.event === 'PIVOT_CONFIRMED' ? 'CONFIRMED' : 'SUPERSEDED', last_event: tr.event, last_known_at: tr.known_at, judgement: tr.judgement});
    return {role: ROLE, label_ko: rules.label_ko, rule_version: ctx.rule_version, params_sha256: ctx.params_sha256, run_mode: ctx.run_mode, symbol: ctx.symbol, timeframe: tf,
      segments: ctx.segments, transitions: r.out, skipped, structure: structure(piv.confirmed), objects: [...objects.keys()].sort().map(k => objects.get(k))};
  }
  function preview(series, result) {
    const last = series.bars.length ? series.bars[series.bars.length - 1] : null;
    if (!last || last.state !== 'PROVISIONAL' || last.ohlc !== 'PRESENT') return [];
    const formed = new Map();
    for (const tr of result.transitions) if (tr.object_kind === 'SIGNAL' && tr.event === 'FORMED') formed.set(tr.object_id, tr.detail);
    const out = [];
    for (const obj of result.objects) {
      if (obj.object_kind !== 'SIGNAL' || obj.state !== 'FORMED' || !formed.has(obj.object_id)) continue;
      const d = formed.get(obj.object_id), above = ['BOX_BREAKOUT_UP', 'DOUBLE_BOTTOM'].includes(obj.pattern);
      if (above ? last.close > d.confirm_level : last.close < d.confirm_level) out.push({object_id: obj.object_id, note_ko: PREVIEW_NOTE_KO, provisional_at: last.session_date || last.week_start});
    }
    return out;
  }
  return Object.freeze({ROLE, STRUCTURE_LABELS, PREVIEW_NOTE_KO, canonicalJson, checkRules, param, runMode, engineBars, segments, prepare, judgement, objectId, pivots, structure, runPivots, run, preview});
});
