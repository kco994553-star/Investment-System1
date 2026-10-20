/* Official pattern detection history (TECHNICAL_PATTERN_CHART_V1_DESIGN §8.4-§8.7, P1-6). RAM only: no network, no
   storage, no DOM; a page reload or session change starts empty (durable storage is phase 2, owner decision Q2).
   Python reference: investment_system/technical/pattern_history.py. Append only: a record is never changed or removed.
   One history per (symbol, timeframe, rule_version, params_sha256): another version is refused, never mixed. Only OFFICIAL
   PatternEngine runs are accepted; user settings and user drawings never touch it (§11.4). An object enters only when its
   first transition was judgeable (price-basis continuity CONFIRMED); its later transitions follow it. Data revisions add
   DATA_REVISION records and leave earlier records as they were. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PatternHistory = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'pattern-history/1', REVISION_NOTE_KO = '자료 수정 후 재계산 결과 다름';
  const CONTENT = ['object_id', 'object_kind', 'pattern', 'event', 'state', 'timeframe', 'rule_version', 'params_sha256', 'anchor_index', 'anchor_at', 'known_index', 'known_at', 'detail', 'judgement', 'superseded_by'];
  const KEY = ['symbol', 'timeframe', 'rule_version', 'params_sha256'];
  function fail(code) { throw new Error(code); }
  function canon(v) {
    if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
    if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}';
    return JSON.stringify(v);
  }
  const clone = v => JSON.parse(JSON.stringify(v));
  function deepFreeze(v) { if (v && typeof v === 'object') { Object.values(v).forEach(deepFreeze); Object.freeze(v); } return v; }
  function content(tr) { const out = {}; for (const k of CONTENT) if (Object.prototype.hasOwnProperty.call(tr, k)) out[k] = tr[k]; return out; }
  const recordKey = (oid, event, knownAt) => oid + '|' + event + '|' + String(knownAt);
  const eligible = first => first.event !== 'NOT_JUDGEABLE' && first.judgement && first.judgement.state === 'CONFIRMED';
  function create(symbol, timeframe, ruleVersion, paramsSha256) {
    const key = {symbol, timeframe, rule_version: ruleVersion, params_sha256: paramsSha256}, records = [], keys = new Map(), decided = new Map();
    function check(result) {
      if (!result || result.run_mode !== 'OFFICIAL') fail('HISTORY_USER_SETTINGS_REFUSED');
      if (KEY.some(k => result[k] !== key[k])) fail('HISTORY_VERSION_MIXED');
    }
    function push(record, computedAt) {
      const item = deepFreeze({...clone(record), seq: records.length + 1, computed_at: computedAt});
      records.push(item); keys.set(recordKey(item.object_id, item.event, item.known_at), item);
    }
    // A recorded object whose recomputed past (known_at <= latest recorded date) differs from its records is diverged: nothing of
    // it is added (conflicts; data revisions go through recordRevision). A new object starting on or before that date is late (§13.1).
    function append(result, computedAt) {
      check(result);
      const counts = {added: 0, duplicates: 0, withheld: 0, conflicts: 0, late: 0}, days = records.filter(x => x.event !== 'DATA_REVISION').map(x => x.known_at);
      const latest = days.length ? days.reduce((a, b) => (b > a ? b : a)) : null, recorded = new Map(), runs = new Map();
      for (const x of records) if (x.event !== 'DATA_REVISION') { if (!recorded.has(x.object_id)) recorded.set(x.object_id, []); recorded.get(x.object_id).push(canon(content(x))); }
      for (const tr of result.transitions) if (latest !== null && tr.known_at <= latest) { if (!runs.has(tr.object_id)) runs.set(tr.object_id, []); runs.get(tr.object_id).push(canon(content(tr))); }
      const diverged = new Set([...recorded].filter(([oid, seq]) => canon(runs.get(oid) || []) !== canon(seq)).map(([oid]) => oid)), late = new Set();
      for (const tr of result.transitions) {
        if (!decided.has(tr.object_id)) decided.set(tr.object_id, eligible(tr));
        if (!decided.get(tr.object_id)) counts.withheld++;
        else if (diverged.has(tr.object_id)) counts.conflicts++;
        else if (keys.has(recordKey(tr.object_id, tr.event, tr.known_at))) counts.duplicates++;
        else if (late.has(tr.object_id) || (!recorded.has(tr.object_id) && latest !== null && tr.known_at <= latest)) { late.add(tr.object_id); counts.late++; }
        else { push(content(tr), computedAt); if (!recorded.has(tr.object_id)) recorded.set(tr.object_id, []); counts.added++; }
      }
      return counts;
    }
    function recordRevision(official, revised, revisedDates, knownAt, computedAt) {
      check(official); check(revised);
      const byObject = result => { const out = new Map(); for (const tr of result.transitions) { if (!out.has(tr.object_id)) out.set(tr.object_id, []); out.get(tr.object_id).push(canon(content(tr))); } return out; };
      const a = byObject(official), b = byObject(revised), affected = [];
      for (const oid of [...new Set(records.map(x => x.object_id))].sort()) {
        if (canon(a.get(oid) || null) === canon(b.get(oid) || null)) continue;
        affected.push(oid);
        if (keys.has(recordKey(oid, 'DATA_REVISION', knownAt))) continue;
        const first = records.find(x => x.object_id === oid);
        push({object_id: oid, object_kind: first.object_kind, pattern: first.pattern === undefined ? null : first.pattern, event: 'DATA_REVISION', state: null, timeframe: key.timeframe,
          rule_version: key.rule_version, params_sha256: key.params_sha256, anchor_index: first.anchor_index, anchor_at: first.anchor_at, known_index: null, known_at: knownAt,
          detail: {revised_dates: [...revisedDates].sort(), note_ko: REVISION_NOTE_KO, recomputed: b.has(oid) ? 'DIFFERENT' : 'ABSENT'}, judgement: null}, computedAt);
      }
      return {affected};
    }
    return Object.freeze({key: Object.freeze({...key}), append, recordRevision, records: () => records.slice()});
  }
  function createBook() {
    const items = new Map();
    const historyFor = result => { const k = KEY.map(x => result[x]).join('\u0000'); if (!items.has(k)) items.set(k, create(...KEY.map(x => result[x]))); return items.get(k); };
    return Object.freeze({
      historyFor,
      append(result, computedAt) { if (!result || result.run_mode !== 'OFFICIAL') fail('HISTORY_USER_SETTINGS_REFUSED'); return historyFor(result).append(result, computedAt); },
      keys: () => [...items.values()].map(h => KEY.map(x => h.key[x])).sort((x, y) => (x.join('\u0000') < y.join('\u0000') ? -1 : 1)),
      clear() { items.clear(); }
    });
  }
  return Object.freeze({SCHEMA, REVISION_NOTE_KO, create, createBook});
});
