/* Pattern engine (TECHNICAL_PATTERN_CHART_V1_DESIGN §8-§9): engine bars, split segments, swing pivots.
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
  return Object.freeze({ROLE, STRUCTURE_LABELS, canonicalJson, checkRules, param, runMode, engineBars, segments, prepare, judgement, objectId, pivots, structure, runPivots});
});
