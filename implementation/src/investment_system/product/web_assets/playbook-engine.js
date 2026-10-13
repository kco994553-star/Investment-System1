/* Signal playbook v1 (docs/playbook/PLAYBOOK_V1.md, v0 · UNCALIBRATED): pure judgement engine. No network, no storage.
   Python reference: investment_system/qgv/playbook.py (vectors: tests/fixtures/playbook_reference_v1.json).
   Every number comes from the config (PlaybookConfigDefaults = qgv/playbook_v1.json). Unknown facts (null) never count
   as zero or as good: the condition does not fire, is listed under `unknown`, and dependent expansion/entry is disabled. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PlaybookEngine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCHEMA = 'playbook-judgement/1';
  const TRADE_ACTIONS = ['INCREASE', 'REDUCE', 'EXIT', 'ENTER'];
  const PROFILE_TYPES = ['growth', 'value', 'dividend', 'quality', 'cyclical', 'defensive'];
  const LEADERBOARD_SIGNALS = ['NEAR_TRIGGER', 'REASSESS'];
  const known = (...values) => values.every(v => v !== null && v !== undefined);
  const val = (o, k) => (o && o[k] !== undefined ? o[k] : null);
  const uniqSorted = list => [...new Set(list)].sort();

  function num(cfg, key) {
    const entry = cfg.defaults[key] || cfg.rule_constants[key];
    if (!entry) throw new Error('PLAYBOOK_KEY ' + key);
    return entry.unit === 'fraction' ? entry.value[0] / entry.value[1] : entry.value;
  }
  function profile(cfg, type) {
    const p = cfg.type_profiles.find(x => x.type === type);
    if (!p) throw new Error('PLAYBOOK_TYPE ' + type);
    return p;
  }
  function typeContext(cfg, memberships, basis) {
    basis = basis || 'v1';
    const m = memberships || {}, floor = cfg.type_membership.min_membership, tie = cfg.type_tie_order.order;
    const knownTypes = PROFILE_TYPES.filter(t => known(val(m, t)));
    const members = knownTypes.filter(t => m[t] >= floor);
    let primary = 'default', ordered = ['default'];
    if (members.length) {
      const best = Math.max(...members.map(t => m[t]));
      primary = tie.find(t => members.includes(t) && m[t] === best);
      ordered = tie.filter(t => members.includes(t));
    }
    const profiles = ordered.map(t => profile(cfg, t)), p = profile(cfg, primary), leader = val(m, 'leader');
    const v2 = cfg.v2_adjustments, r2Rows = {}, vPct = {};
    if (basis === 'v2') v2.r2.forEach(r => { const o = Object.assign({}, r); delete o.type; r2Rows[r.type] = o; });
    else profiles.forEach(q => { r2Rows[q.type] = q.r2; });
    v2.v_pct_standard.forEach(r => { vPct[r.type] = r.v_pct; });
    return {
      primary, members: ordered, unknown: knownTypes.length === 0, leader: leader === null ? null : leader >= floor,
      thresholds: {
        basis,
        r2: ordered.map(t => Object.assign({type: t}, r2Rows[t])),
        v_reduce: p.v_points,
        v_expand: Math.max(...profiles.map(q => q.v_points)),
        safety_margin_pct: basis === 'v1' ? Math.max(...profiles.map(q => q.safety_margin_pct)) : null,
        v_industry_pct: basis === 'v2' ? Math.max(...ordered.map(t => vPct[t])) : null,
        recheck_days: p.recheck_days,
        split_count: p.split_count,
      },
    };
  }
  function drops(s) {
    const qp = val(s, 'q_prev'), qn = val(s, 'q_now'), gp = val(s, 'g_prev'), gn = val(s, 'g_now');
    return {q: known(qp, qn) ? qp - qn : null, g: known(gp, gn) ? gp - gn : null,
      qg: known(qp, qn, gp, gn) ? (qp + gp) / 2 - (qn + gn) / 2 : null};
  }
  function r2Check(tc, s, d) {
    const hits = [], missing = [];
    for (const cond of tc.thresholds.r2) {
      for (const metric of ['qg', 'q', 'g']) {
        if (!(metric in cond)) continue;
        if (d[metric] === null) missing.push(metric + '_change');
        else if (d[metric] >= cond[metric]) hits.push({type: cond.type, metric, drop: d[metric], threshold: cond[metric]});
      }
      if (cond.dividend_cut) {
        const cut = val(s, 'dividend_cut');
        if (cut === null) missing.push('dividend_cut');
        else if (cut) hits.push({type: cond.type, metric: 'dividend_cut', drop: null, threshold: null});
      }
    }
    const miss = uniqSorted(missing);
    return {hits, missing: miss, maintained: hits.length ? false : (miss.length ? null : true)};
  }
  function band(cfg, target) { return Math.max(num(cfg, 'band_min_pp'), target * num(cfg, 'band_target_ratio')); }
  function special(cfg, tc, s, macro, u3ok25) {
    const disabled = [], warnings = [], questions = [], unknown = [];
    const rules = Object.fromEntries(cfg.special_rules.map(r => [r.id, r]));
    const add = (list, reason) => list.forEach(e => disabled.push([e, reason]));
    if (tc.members.includes('cyclical')) {
      const pos = val(s, 'operating_margin_5y_position'), r = rules.cyclical_peak_earnings;
      if (pos === null) { unknown.push({rule: 'cyclical_peak_earnings', missing: ['operating_margin_5y_position']}); add(r.effect.disable, 'SPECIAL_RULE_UNVERIFIABLE'); }
      else if (pos >= r.condition.value) add(r.effect.disable, 'CYCLICAL_PEAK_EARNINGS');
    }
    if (tc.thresholds.basis === 'v2') {
      const gate = cfg.v2_adjustments.value_trap_gate, flag = val(s, 'value_trap_gate');
      if (flag === null) { unknown.push({rule: 'value_trap_gate', missing: ['value_trap_gate']}); add(gate.disable, 'SPECIAL_RULE_UNVERIFIABLE'); }
      else if (flag) { warnings.push(gate.warning); add(gate.disable, gate.warning); }
    } else if (tc.members.includes('value')) {
      const streak = val(s, 'q_decline_streak_quarters'), r = rules.value_trap;
      if (streak === null) { unknown.push({rule: 'value_trap', missing: ['q_decline_streak_quarters']}); add(r.effect.disable, 'SPECIAL_RULE_UNVERIFIABLE'); }
      else if (streak >= r.condition.value) add(r.effect.disable, 'VALUE_TRAP');
    }
    if (tc.leader) {
      const rank = val(s, 'sector_marketcap_rank');
      if (rank === null) unknown.push({rule: 'leader_rank', missing: ['sector_marketcap_rank']});
      else if (rank > rules.leader_rank.condition.value) questions.push(rules.leader_rank.effect.add_question);
    }
    const theme = val(s, 'theme_weight_pct'), limit = num(cfg, rules.theme_concentration.condition.value_ref);
    if (theme === null) { unknown.push({rule: 'theme_concentration', missing: ['theme_weight_pct']}); disabled.push(['W2_ENTER', 'SPECIAL_RULE_UNVERIFIABLE']); }
    else if (theme > limit) { warnings.push('THEME_CONCENTRATION'); add(rules.theme_concentration.effect.disable, 'THEME_CONCENTRATION'); }
    if (cfg.financial_exception.sectors.includes(val(s, 'sector'))) add(cfg.financial_exception.disable, cfg.financial_exception.reason);
    const effects = cfg.macro.effects;
    if (macro === null) unknown.push({rule: 'macro_state', missing: ['macro_state']});
    else if (macro === 'WARNING' && tc.members.includes('cyclical')) add(effects.WARNING.disable_cyclical, 'MACRO_WARNING_CYCLICAL');
    else if (macro === 'CRISIS') effects.CRISIS.disable.forEach(e => { if (!(e === 'W2_ENTER' && u3ok25)) disabled.push([e, 'MACRO_CRISIS']); });
    return {disabled, warnings, questions, unknown};
  }
  function u3Conditions(cfg, tc, s, firedR3, r3Known, vDelta, macro) {
    const c = Object.fromEntries(cfg.macro.u3.conditions.map(x => [x.id, x])), out = {};
    out.macro_state = macro === null ? null : (macro === 'WARNING' || macro === 'CRISIS');
    const ratio = val(s, 'market_explained_ratio_60');
    if (firedR3 || (ratio !== null && ratio < c.market_led.explained_min)) out.market_led = false;
    else if (ratio === null || !r3Known) out.market_led = null;
    else out.market_led = true;
    const q = val(s, 'q_industry_pct');
    out.quality = q === null ? null : q >= c.quality.q_industry_pct_min;
    const nd = val(s, 'net_debt_to_ebitda'), ic = val(s, 'interest_coverage'), fs = c.financial_safety;
    if ((nd !== null && nd >= fs.net_debt_to_ebitda_lt) || (ic !== null && ic <= fs.interest_coverage_gt)) out.financial_safety = false;
    else out.financial_safety = nd === null || ic === null ? null : true;
    out.cheaper = vDelta === null ? null : vDelta >= tc.thresholds.v_expand;
    return out;
  }
  const all3 = values => (values.includes(false) ? false : values.includes(null) ? null : true);

  function activeCodes(cfg, mode, targetVersion) {
    const scope = cfg.implementation_scope;
    if (mode === 'ALL') return cfg.codes.map(c => c.code);
    const active = new Set(scope.core_v0.concat(targetVersion === 'v1' ? scope.target_v1_only : []));
    return cfg.codes.map(c => c.code).filter(c => active.has(c));
  }
  function evaluate(cfg, s, mode) {
    mode = mode || 'CORE_V0';
    const levels = cfg.levels.map(l => l.id), codeCfg = Object.fromEntries(cfg.codes.map(c => [c.code, c]));
    const basis = val(s, 'basis') || 'v1';
    const tc = typeContext(cfg, val(s, 'memberships'), basis), th = tc.thresholds;
    const held = !!val(s, 'held'), conv = val(s, 'conviction') || {}, convActive = !!conv.active, macro = val(s, 'macro_state');
    const d = drops(s), r2 = r2Check(tc, s, d);
    const vNow = val(s, 'v_now'), vPrev = val(s, 'v_prev20'), vDelta = known(vNow, vPrev) ? vNow - vPrev : null;
    const actual = val(s, 'actual_pct'), target = val(s, 'target_pct');
    const fired = new Map(), e4 = [];
    let unknown = [];
    const fire = (code, reasons) => fired.set(code, reasons);
    const miss = (code, fields) => unknown.push({code, missing: uniqSorted(fields)});
    const r2Reasons = hits => uniqSorted(hits.map(h => (h.metric === 'dividend_cut' ? 'DIVIDEND_CUT' : 'QG_DECLINE')));

    const data = val(s, 'data') || {};
    const x1 = [['price_missing', 'PRICE_MISSING'], ['fx_missing', 'FX_MISSING'], ['snapshot_missing', 'SNAPSHOT_MISSING']].filter(([k]) => data[k]).map(([, r]) => r);
    if (x1.length) fire('X1', x1);
    if (val(s, 'coverage') === 'BLOCKED') fire('X2', ['COVERAGE_BLOCKED']);
    if (val(s, 'user_excluded')) fire('X3', ['USER_EXCLUDED']);
    if (held && (val(s, 'invalidation_triggered') || (convActive && conv.invalidated))) fire('R1', ['CONVICTION_INVALIDATED']);
    const ex = val(s, 'excess_20'), mean = val(s, 'excess_mean_252'), sd = val(s, 'excess_sd_252');
    const r3Cond = known(ex, mean, sd) ? ex < mean - num(cfg, 'r3_sigma') * sd : null; // also U3 condition 2 (R3 미발동)
    if (held) {
      if (r2.hits.length) {
        const cut = r2.hits.filter(h => h.metric === 'dividend_cut'), own = val(s, 'own_value_worsened');
        if (basis === 'v1' || cut.length || own === true) fire('R2', r2Reasons(basis === 'v1' || own === true ? r2.hits : cut));
        else if (own === false) e4.push('QG_RELATIVE_DECLINE');
        else { miss('R2', ['own_value_worsened']); e4.push('QG_RELATIVE_DECLINE_UNVERIFIED'); }
      } else if (r2.missing.length) miss('R2', r2.missing);
      if (r3Cond === true) fire('R3', ['RECHECK_ABNORMAL_DROP']);
      else if (r3Cond === null) miss('R3', ['excess_20', 'excess_mean_252', 'excess_sd_252'].filter(k => val(s, k) === null));
    }
    if (val(s, 'coverage_prev') === 'READY' && val(s, 'coverage') === 'PARTIAL') fire('R4', ['COVERAGE_DEGRADED']);
    if (val(s, 'user_hold')) fire('R5', ['USER_HOLD']);
    if (held) {
      if (r2.maintained === true && vDelta !== null) {
        if (-vDelta >= th.v_reduce) fire('T1', ['V_DETERIORATED']);
        if (vDelta >= th.v_expand) fire('U1', ['V_IMPROVED']);
      } else if (r2.maintained !== false) {
        const fields = (r2.maintained === null ? r2.missing : []).concat(vDelta !== null ? [] : ['v_change_20']);
        miss('T1', fields); miss('U1', fields);
      }
    }
    if (target !== null) {
      if (actual === null) { miss('T2', ['actual_pct']); miss('U2', ['actual_pct']); }
      else {
        const b = band(cfg, target);
        if (actual > target + b) {
          if (vDelta === null) miss('T2', ['v_change_20']);
          else if (Math.abs(vDelta) < th.v_reduce) fire('T2', ['OVERWEIGHT_GAP']);
        }
        if (actual < target - b) fire('U2', ['UNDERWEIGHT_GAP']);
      }
    }
    const u3 = u3Conditions(cfg, tc, s, r3Cond === true, r3Cond !== null, vDelta, macro);
    if (held) {
      const ok = all3(Object.values(u3));
      if (ok === true) fire('U3', ['MACRO_DISCOUNT']);
      else if (ok === null) miss('U3', Object.entries(u3).filter(([, v]) => v === null).map(([k]) => k));
    }
    if (held && convActive) {
      const total = val(s, 'conviction_total_pct');
      if (total === null) miss('T3', ['conviction_total_pct']);
      else if (total > num(cfg, 'conviction_cap_pct')) fire('T3', ['CONVICTION_CAP_EXCEEDED']);
    }
    const days = val(s, 'earnings_days_until');
    if ((days !== null && days >= 0 && days <= num(cfg, 'e1_days_before')) || val(s, 'earnings_pending_reflection')) fire('E1', ['EARNINGS_WINDOW']);
    if (val(s, 'type_changed')) fire('E2', ['TYPE_CHANGED']);
    if (val(s, 'coverage') === 'PARTIAL' || val(s, 'qg_source_missing')) fire('E3', ['COVERAGE_PARTIAL']);
    if (LEADERBOARD_SIGNALS.includes(val(s, 'leaderboard_signal'))) e4.unshift('REASSESS_SIGNAL');
    const exits = val(s, 'thirteenf_full_exit_managers');
    if (held && exits !== null && exits >= num(cfg, 'thirteenf_full_exit_managers')) e4.push('THIRTEENF_FULL_EXIT');
    if (val(s, 'structural_news')) e4.push('STRUCTURAL_NEWS');
    if (e4.length) fire('E4', e4);
    if (val(s, 'followup_due')) fire('E5', ['FOLLOWUP_DUE']);
    if (held && convActive && ((conv.months_held || 0) >= num(cfg, 'conviction_review_months') || (conv.risk_review_count || 0) >= num(cfg, 'conviction_review_risk_count'))) fire('H2', ['CONVICTION_ANNUAL']);
    if (!held) {
      if (val(s, 'watched')) fire('W1', ['WATCH']);
      const rank = val(s, 'leaderboard_rank');
      if (known(rank, vDelta)) { if (rank <= num(cfg, 'w2_rank_max') && vDelta >= num(cfg, 'w2_v_improve_points')) fire('W2', ['ENTRY_CANDIDATE']); }
      else miss('W2', [['leaderboard_rank', rank], ['v_change_20', vDelta]].filter(([, v]) => v === null).map(([k]) => k));
    }
    const active = new Set(activeCodes(cfg, mode, val(s, 'target_version')));
    const candidateSignals = [...fired.keys()].filter(c => !active.has(c)).sort((a, b) => codeCfg[a].priority - codeCfg[b].priority).map(c => ({code: c, reasons: fired.get(c)}));
    for (const c of [...fired.keys()]) if (!active.has(c)) fired.delete(c);
    unknown = unknown.filter(u => active.has(u.code));
    if (held && val(s, 'quarterly_check_due') && (fired.size === 0 || (val(s, 'qg_source_missing') && val(s, 'post_earnings_check_due')))) fire('H1', ['QUARTERLY_CHECK']);

    const key = c => [levels.indexOf(codeCfg[c].level), codeCfg[c].priority];
    const ordered = [...fired.keys()].sort((a, b) => { const ka = key(a), kb = key(b); return ka[0] - kb[0] || ka[1] - kb[1]; });
    const outCodes = ordered.map(c => ({code: c, level: codeCfg[c].level, reasons: fired.get(c)}));
    const primary = outCodes.length ? outCodes[0] : null;

    let disabled = [];
    const lvl = c => codeCfg[c].level;
    if (ordered.some(c => lvl(c) === 'BLOCK')) TRADE_ACTIONS.forEach(a => disabled.push([a, 'BLOCKED']));
    if (ordered.some(c => lvl(c) === 'RISK_RECHECK' || lvl(c) === 'REDUCE_REVIEW')) disabled.push(['INCREASE', 'DOWN_DISABLES_UP']);
    if (fired.has('E1') && !(lvl(ordered[0]) === 'BLOCK' || ordered[0] === 'R1')) TRADE_ACTIONS.forEach(a => disabled.push([a, 'E1_HOLDS_TRADES']));
    if (fired.has('E3')) disabled.push(['INCREASE', 'E3_DISABLES_EXPANSION']);
    if (basis === 'v1') {
      const margin = val(s, 'safety_margin_pct');
      if (margin === null) disabled.push(['U1_INCREASE', 'CORE_UNVERIFIABLE'], ['W2_ENTER', 'CORE_UNVERIFIABLE']);
      else if (margin < th.safety_margin_pct) disabled.push(['U1_INCREASE', 'SAFETY_MARGIN_BELOW_TYPE'], ['W2_ENTER', 'SAFETY_MARGIN_BELOW_TYPE']);
    } else {
      const vp = val(s, 'v_industry_pct'), exp = val(s, 'expectation_check_passed');
      if (vp !== null && vp < th.v_industry_pct) disabled.push(['U1_INCREASE', 'V_PERCENTILE_BELOW_TYPE'], ['W2_ENTER', 'V_PERCENTILE_BELOW_TYPE']);
      if (exp === false) disabled.push(['U1_INCREASE', 'EXPECTATION_CHECK_FAILED'], ['W2_ENTER', 'EXPECTATION_CHECK_FAILED']);
      if (vp === null || exp === null) disabled.push(['U1_INCREASE', 'CORE_UNVERIFIABLE'], ['W2_ENTER', 'CORE_UNVERIFIABLE']);
    }
    const u3ok25 = all3(Object.entries(u3).filter(([k]) => k !== 'macro_state').map(([, v]) => v)) === true;
    const sp = special(cfg, tc, s, macro, u3ok25);
    disabled = disabled.concat(sp.disabled);

    const keep = cfg.conviction_choice;
    const choicesFor = code => {
      const base = codeCfg[code].choices.slice();
      if (mode === 'ALL' && convActive && !conv.invalidated && !fired.has('R1') && keep.applies_to.includes(code)) base.push({id: keep.id, label: keep.label, action: keep.action, source: keep.source});
      return base.map(ch => {
        const scoped = code + '_' + ch.action;
        const reasons = uniqSorted(disabled.filter(([t]) => t === ch.action || t === scoped).map(([, r]) => r));
        return {id: ch.id, label: ch.label, action: ch.action, enabled: reasons.length === 0, disabled_reasons: reasons};
      });
    };
    const checks = [];
    for (const c of ordered) for (const item of codeCfg[c].checks) checks.push({code: c, text: item.text, sources: item.sources});
    for (const q of sp.questions) if (fired.has(q.code)) checks.push({code: q.code, text: q.text, sources: ['AI']});
    const pairs = [...new Set(disabled.map(([t, r]) => t + '\u0000' + r))].sort((a, b) => {
      const [ta, ra] = a.split('\u0000'), [tb, rb] = b.split('\u0000');
      return ta < tb ? -1 : ta > tb ? 1 : ra < rb ? -1 : ra > rb ? 1 : 0;
    });
    return {
      schema: SCHEMA, config_version: cfg.config_version, calibration: cfg.calibration, basis, mode, symbol: val(s, 'symbol'),
      primary, secondary: outCodes.slice(1),
      type: {primary: tc.primary, members: tc.members, unknown: tc.unknown, leader: tc.leader, thresholds: tc.thresholds},
      band_pp: target === null ? null : band(cfg, target),
      qg: {q_drop: d.q, g_drop: d.g, qg_drop: d.qg, maintained: r2.maintained, r2_hits: r2.hits},
      v_change_20: vDelta,
      macro: {state: macro, split_multiplier: macro === 'WARNING' ? num(cfg, 'macro_warning_split_multiplier') : 1, u3_conditions: u3},
      checks,
      choices: primary ? choicesFor(primary.code) : [],
      choices_by_code: Object.fromEntries(ordered.map(c => [c, choicesFor(c)])),
      disabled: pairs.map(p => { const [t, reason] = p.split('\u0000'); return {target: t, reason}; }),
      candidate_signals: candidateSignals,
      warnings: uniqSorted(sp.warnings),
      unknown: unknown.concat(sp.unknown.map(u => ({rule: u.rule, missing: u.missing}))),
    };
  }

  function transition(cfg, from, choice, ctx) {
    const c = ctx || {}, tc = typeContext(cfg, c.memberships || null, c.basis || 'v1'), macro = c.macro_state === undefined ? null : c.macro_state;
    const row = cfg.transitions.find(r => r.from === from && r.choice === choice);
    if (!row) return {from, choice, state: 'NO_TRANSITION'};
    const action = {};
    for (const [k, v] of Object.entries(row.action)) {
      if (k.endsWith('_ref')) action[k.slice(0, -4)] = v === 'TYPE_SPLITS' ? tc.thresholds.split_count * (macro === 'WARNING' ? num(cfg, 'macro_warning_split_multiplier') : 1) : num(cfg, v);
      else action[k] = v;
    }
    if ('cyclical_delta_pp' in action && !tc.members.includes('cyclical')) delete action.cyclical_delta_pp;
    if (choice === 'W2_PROCEED' && macro === 'CRISIS') action.fraction = num(cfg, 'w2_crisis_initial_fraction');
    let followup = null;
    if (row.followup) {
      const f = row.followup;
      if (f.kind === 'DAYS') followup = {kind: 'DAYS', days: num(cfg, f.days_ref)};
      else if (f.kind === 'TYPE_RECHECK') followup = {kind: 'DAYS', days: tc.thresholds.recheck_days};
      else followup = {kind: f.kind};
    }
    let next = row.next;
    if (row.next_if_v_improved && c.v_improved) next = row.next_if_v_improved;
    const tgt = cfg.target_change;
    const target = tgt.changes_target_kinds.includes(action.kind) || 'cyclical_delta_pp' in action
      ? {store_as: tgt.store_as, apply: tgt.immediate_on_approval.includes(choice) ? 'IMMEDIATE_ON_APPROVAL' : tgt.apply_on, freed_weight: tgt.freed_weight}
      : null;
    return {from, choice, state: 'OK', action, next, followup, source: row.source, type: tc.primary, target};
  }

  function e4Level(cfg, drawdown, maxDrawdown3y, historyYears, userThreshold) {
    const r = cfg.reassess_thresholds;
    if (userThreshold !== null && userThreshold !== undefined) {
      if (drawdown === null || drawdown === undefined) return {level: null, basis: 'USER', ratio: null};
      return {level: drawdown >= userThreshold ? 'REASSESS' : null, basis: 'USER', ratio: null};
    }
    if (historyYears === null || historyYears === undefined || historyYears < r.history_years_min || drawdown === null || drawdown === undefined || !maxDrawdown3y) return {level: r.insufficient, basis: 'SYSTEM', ratio: null};
    const ratio = drawdown / maxDrawdown3y;
    let level = null;
    for (const lv of r.levels) if (ratio >= lv.ratio_min) level = lv.id;
    return {level, basis: 'SYSTEM', ratio};
  }

  function criteria(cfg, code, facts, ctx) {
    const c = ctx || {}, tc = typeContext(cfg, c.memberships || null, c.basis || 'v1'), f = facts || {};
    const need = (...keys) => keys.filter(k => val(f, k) === null);
    const res = (choice, missing) => ({choice, missing: missing || []});
    if (code === 'R2') {
      const status = val(f, 'thesis_status');
      if (status === null) return res(null, ['thesis_status']);
      if (status.filter(x => x === 'BROKEN').length * 2 > status.length) return res('R2_THESIS_BROKEN');
      let missing = need('guidance_mid_lowered', 'peers_differ');
      if (missing.length) return res(null, missing);
      if (f.guidance_mid_lowered && f.peers_differ) return res('R2_COMPANY_GUIDANCE');
      missing = need('peers_same_direction');
      if (missing.length) return res(null, missing);
      if (f.peers_same_direction >= num(cfg, 'r2_peer_same_direction_min')) return res('R2_SECTOR_CYCLE');
      const metric = f.drop_metric || 'qg', limits = tc.thresholds.r2.filter(x => metric in x).map(x => x[metric]);
      missing = need('drop_excluding_one_offs').concat(limits.length ? [] : ['drop_metric']);
      if (missing.length) return res(null, missing);
      if (f.drop_excluding_one_offs < Math.min(...limits) * num(cfg, 'r2_one_off_ratio')) return res('R2_ONE_OFF');
      return res('R2_NONE');
    }
    if (code === 'T1') {
      if (tc.thresholds.basis === 'v2') {
        const rule = cfg.v2_adjustments.t1_reduce, missing = need('v_industry_pct', 'expectation_check_passed');
        if (missing.length) return res(null, missing);
        return res(f.v_industry_pct < rule.v_pct_below && f.expectation_check_passed === false ? 'T1_REDUCE' : 'T1_MAINTAIN');
      }
      const missing = need('safety_margin_pct', 'implied_growth', 'actual_growth_3y');
      if (missing.length) return res(null, missing);
      return res(f.safety_margin_pct < 0 && f.implied_growth > f.actual_growth_3y ? 'T1_REDUCE' : 'T1_MAINTAIN');
    }
    if (code === 'T2') {
      const missing = need('excess_pp');
      if (missing.length) return res(null, missing);
      return res(f.excess_pp <= num(cfg, 't2_deposit_limit_pp') ? 'T2_DEPOSIT' : 'T2_TRIM');
    }
    if (code === 'H1') {
      const status = val(f, 'thesis_status');
      if (status === null) return res(null, ['thesis_status']);
      if (status.filter(x => x === 'BROKEN').length >= 1) return res('H1_BROKEN');
      if (status.filter(x => x === 'WEAKENED').length >= 2) return res('H1_WEAKENED');
      return res('H1_MAINTAIN');
    }
    if (code === 'R5') {
      const missing = need('condition_met', 'extensions_used');
      if (missing.length) return res(null, missing);
      if (f.condition_met) return res('R5_RELEASE');
      return res(f.extensions_used < num(cfg, 'r5_max_extensions') ? 'R5_EXTEND' : 'R5_DECIDE');
    }
    if (code === 'W2') {
      const items = val(f, 'checks');
      if (items === null || items.length !== 5 || items.some(x => x === null || x === undefined)) return res(null, ['checks']);
      return res(items.every(Boolean) ? 'W2_PROCEED' : 'W2_OBSERVE');
    }
    return {choice: null, missing: [], state: 'NOT_MECHANICAL'};
  }

  function compare(op, value, limit) {
    switch (op) {
      case '>=': return value >= limit;
      case '>': return value > limit;
      case '<': return value < limit;
      case '<=': return value <= limit;
      case '==': return value === limit;
      case 'in': return limit.includes(value);
      default: throw new Error('PLAYBOOK_OP ' + op);
    }
  }
  function classifyTypesV0(cfg, metrics) {
    const out = {};
    for (const rule of cfg.type_rules_v0) {
      if (rule.combine === 'TYPE_CONFIG_V1') { out[rule.type] = {member: null, missing: [], state: 'TYPE_CONFIG_V1'}; continue; }
      const results = [], missing = [];
      for (const cond of rule.conditions) {
        const v = val(metrics, cond.metric);
        if (v === null) { missing.push(cond.metric); results.push(null); }
        else results.push(compare(cond.op, v, cond.value));
      }
      const member = rule.combine === 'ALL'
        ? (results.includes(false) ? false : results.includes(null) ? null : true)
        : (results.includes(true) ? true : results.includes(null) ? null : false);
      out[rule.type] = {member, missing};
    }
    return out;
  }
  function portfolioLimits(cfg, rows, cashPct) {
    const lim = cfg.portfolio_limits, groups = {}, violations = [], unknown = [], sums = {};
    lim.combined_groups.forEach(g => g.sectors.forEach(sec => { groups[sec] = g.id; }));
    for (const r of rows) {
      if (r.pct > lim.single_max_pct) violations.push({rule: 'SINGLE_MAX', symbol: r.symbol, pct: r.pct, limit: lim.single_max_pct});
      if (r.sector === null || r.sector === undefined) { unknown.push(r.symbol); continue; }
      const g = groups[r.sector] || r.sector;
      sums[g] = (sums[g] || 0) + r.pct;
    }
    for (const g of Object.keys(sums).sort()) if (sums[g] > lim.sector_group_max_pct) violations.push({rule: 'SECTOR_GROUP_MAX', group: g, pct: sums[g], limit: lim.sector_group_max_pct});
    const held = rows.filter(r => r.pct > 0);
    if (held.length < lim.min_holdings) violations.push({rule: 'MIN_HOLDINGS', count: held.length, limit: lim.min_holdings});
    const total = rows.reduce((a, r) => a + r.pct, 0) + (cashPct || 0);
    if (Math.abs(total - cfg.target_v1.sum_pct) > 1e-9) violations.push({rule: 'SUM_NOT_100', pct: total, limit: cfg.target_v1.sum_pct});
    return {ok: violations.length ? false : (unknown.length ? null : true), violations, unknown_sector: unknown, group_pct: sums};
  }
  function sectorFor(cfg, symbol, etf) {
    const a = cfg.assignments.find(x => x.symbol === symbol);
    if (a) return {sector: a.sector, source: a.source};
    if (etf) {
      const rows = cfg.sector_checks.filter(r => r.etfs.includes(etf)).map(r => r.id);
      if (rows.length === 1) return {sector: rows[0], source: 'ETF_UNIQUE'};
      if (rows.length) return {sector: null, source: 'ETF_AMBIGUOUS', candidates: rows};
    }
    return {sector: null, source: 'NOT_AVAILABLE'};
  }

  return Object.freeze({SCHEMA, num, band, activeCodes, typeContext, evaluate, portfolioLimits, transition, criteria, e4Level, classifyTypesV0, sectorFor});
});
