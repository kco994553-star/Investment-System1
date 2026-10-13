"""Signal playbook v1 (docs/playbook/PLAYBOOK_V1.md, v0 · UNCALIBRATED): pure judgement engine.

`evaluate` turns one symbol's facts into the primary code, secondary chips, merged checks, choices with their
enable state and the reasons any choice is disabled (§1–§2, §5, §6). `transition` resolves a chosen verdict into the
next step (§4, plus the §3 criteria §4 does not list). `criteria` applies the ordered §3 standards for the codes whose
standards are mechanical once the user/AI facts are known. `classify_types_v0` applies the §6-2 rules.

Every number comes from qgv/playbook_v1.json. Unknown facts (None) never count as zero or as good: a condition that
cannot be checked does not fire, is listed under `unknown`, and expansion/entry choices that depend on it are disabled.
Mirrors web_assets/playbook-engine.js; tests/fixtures/playbook_reference_v1.json holds the shared vectors.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name('playbook_v1.json')
SCHEMA = 'playbook-judgement/1'
TRADE_ACTIONS = ('INCREASE', 'REDUCE', 'EXIT', 'ENTER')
PROFILE_TYPES = ('growth', 'value', 'dividend', 'quality', 'cyclical', 'defensive')
LEADERBOARD_SIGNALS = ('NEAR_TRIGGER', 'REASSESS')


def load_config(path=CONFIG_PATH):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def num(cfg, key):
    """A §12 default or a body constant; fractions are stored as [numerator, denominator]."""
    entry = cfg['defaults'].get(key) or cfg['rule_constants'][key]
    v = entry['value']
    if entry['unit'] == 'fraction':
        return v[0] / v[1]
    return v


def _known(*values):
    return all(v is not None for v in values)


def _profile(cfg, type_id):
    for p in cfg['type_profiles']:
        if p['type'] == type_id:
            return p
    raise KeyError(type_id)


def type_context(cfg, memberships, basis='v1'):
    """§6-3: member types (membership >= type_config minimum), primary type, and the thresholds each rule uses.
    basis 'v2' swaps in §14-1 percentile R2 thresholds and the §14-2 industry V percentile standard."""
    memberships = memberships or {}
    floor = cfg['type_membership']['min_membership']
    known = {t: memberships.get(t) for t in PROFILE_TYPES if memberships.get(t) is not None}
    members = [t for t in PROFILE_TYPES if t in known and known[t] >= floor]
    tie = cfg['type_tie_order']['order']
    if members:
        best = max(known[t] for t in members)
        primary = next(t for t in tie if t in members and known[t] == best)
        ordered = [t for t in tie if t in members]
    else:
        primary, ordered = 'default', ['default']
    profiles = [_profile(cfg, t) for t in ordered]
    p = _profile(cfg, primary)
    leader = memberships.get('leader')
    v2 = cfg['v2_adjustments']
    r2_rows = {r['type']: {k: v for k, v in r.items() if k != 'type'} for r in v2['r2']} if basis == 'v2' else {q['type']: q['r2'] for q in profiles}
    v_pct = {r['type']: r['v_pct'] for r in v2['v_pct_standard']}
    return {
        'primary': primary,
        'members': ordered,
        'unknown': not known,
        'leader': None if leader is None else leader >= floor,
        'thresholds': {
            'basis': basis,
            'r2': [{'type': t, **r2_rows[t]} for t in ordered],
            'v_reduce': p['v_points'],
            'v_expand': max(q['v_points'] for q in profiles),
            'safety_margin_pct': max(q['safety_margin_pct'] for q in profiles) if basis == 'v1' else None,
            'v_industry_pct': max(v_pct[t] for t in ordered) if basis == 'v2' else None,
            'recheck_days': p['recheck_days'],
            'split_count': p['split_count'],
        },
    }


def _drops(s, suffix=""):
    q = s.get('q_prev' + suffix) - s.get('q_now') if _known(s.get('q_prev' + suffix), s.get('q_now')) else None
    g = s.get('g_prev' + suffix) - s.get('g_now') if _known(s.get('g_prev' + suffix), s.get('g_now')) else None
    qg = None
    if _known(s.get('q_prev' + suffix), s.get('q_now'), s.get('g_prev' + suffix), s.get('g_now')):
        qg = (s['q_prev' + suffix] + s['g_prev' + suffix]) / 2 - (s['q_now'] + s['g_now']) / 2
    return {'q': q, 'g': g, 'qg': qg}


def _r2(cfg, tc, s, drops):
    """Any member type's R2 condition fires R2 (§6-3); 'Q·G 유지' = none fires and all were checkable."""
    hits, missing = [], []
    older = _drops(s, '2')
    for cond in tc['thresholds']['r2']:
        for metric in ('qg', 'q', 'g'):
            if metric in cond:
                d = drops[metric]
                if d is None:
                    missing.append(metric + '_change')
                elif d >= cond[metric]:
                    hits.append({'type': cond['type'], 'metric': metric, 'drop': d, 'threshold': cond[metric], 'comparison': 'PREVIOUS_QUARTER'})
                older_drop = older[metric]
                lim = cond[metric] * cfg['quarter_comparison']['two_quarters_multiplier']
                if older_drop is not None and older_drop >= lim:
                    hits.append({'type': cond['type'], 'metric': metric, 'drop': older_drop, 'threshold': lim, 'comparison': 'TWO_QUARTERS'})
        if cond.get('dividend_cut'):
            cut = s.get('dividend_cut')
            if cut is None:
                missing.append('dividend_cut')
            elif cut:
                hits.append({'type': cond['type'], 'metric': 'dividend_cut', 'drop': None, 'threshold': None})
    missing = sorted(set(missing))
    maintained = False if hits else (None if missing else True)
    if 'quality' in tc['members']:
        qc = cfg['quarter_comparison']
        maintained = False if hits else (None if not _known(drops['q'], drops['g']) else drops['q'] < qc['quality_maintained_q_lt'] and drops['g'] < qc['quality_maintained_g_lt'])
    return hits, missing, maintained


def band(cfg, target):
    """§13-4: Band = max(1%p, target × 20%)."""
    return max(num(cfg, 'band_min_pp'), target * num(cfg, 'band_target_ratio'))


def _special(cfg, tc, s, macro, u3_ok_2_5):
    """§6-4 rules (§14-4 gate replaces the value-trap rule on v2) and §13-5 macro effects.
    Returns (disabled [(target, reason)], warnings, extra questions, unknown)."""
    disabled, warnings, questions, unknown = [], [], [], []
    rules = {r['id']: r for r in cfg['special_rules']}
    members = tc['members']
    v2 = tc['thresholds']['basis'] == 'v2'
    if 'cyclical' in members:
        pos = s.get('operating_margin_5y_position')
        lim = rules['cyclical_peak_earnings']['condition']['value']
        if pos is None:
            unknown.append({'rule': 'cyclical_peak_earnings', 'missing': ['operating_margin_5y_position']})
            disabled += [(e, 'SPECIAL_RULE_UNVERIFIABLE') for e in rules['cyclical_peak_earnings']['effect']['disable']]
        elif pos >= lim:
            disabled += [(e, 'CYCLICAL_PEAK_EARNINGS') for e in rules['cyclical_peak_earnings']['effect']['disable']]
    if v2:
        gate = cfg['v2_adjustments']['value_trap_gate']
        flag = s.get('value_trap_gate')
        if flag is None:
            unknown.append({'rule': 'value_trap_gate', 'missing': ['value_trap_gate']})
            disabled += [(e, 'SPECIAL_RULE_UNVERIFIABLE') for e in gate['disable']]
        elif flag:
            warnings.append(gate['warning'])
            disabled += [(e, gate['warning']) for e in gate['disable']]
    elif 'value' in members:
        streak = s.get('q_decline_streak_quarters')
        lim = rules['value_trap']['condition']['value']
        if streak is None:
            unknown.append({'rule': 'value_trap', 'missing': ['q_decline_streak_quarters']})
            disabled += [(e, 'SPECIAL_RULE_UNVERIFIABLE') for e in rules['value_trap']['effect']['disable']]
        elif streak >= lim:
            disabled += [(e, 'VALUE_TRAP') for e in rules['value_trap']['effect']['disable']]
    if tc['leader']:
        rank = s.get('sector_marketcap_rank')
        if rank is None:
            unknown.append({'rule': 'leader_rank', 'missing': ['sector_marketcap_rank']})
        elif rank > rules['leader_rank']['condition']['value']:
            questions.append(rules['leader_rank']['effect']['add_question'])
    theme = s.get('theme_weight_pct')
    limit = num(cfg, rules['theme_concentration']['condition']['value_ref'])
    if theme is None:
        unknown.append({'rule': 'theme_concentration', 'missing': ['theme_weight_pct']})
        disabled.append(('W2_ENTER', 'SPECIAL_RULE_UNVERIFIABLE'))
    elif theme > limit:
        warnings.append('THEME_CONCENTRATION')
        disabled += [(e, 'THEME_CONCENTRATION') for e in rules['theme_concentration']['effect']['disable']]
    if s.get('sector') in cfg['financial_exception']['sectors']:
        disabled += [(e, cfg['financial_exception']['reason']) for e in cfg['financial_exception']['disable']]
    effects = cfg['macro']['effects']
    if macro is None:
        unknown.append({'rule': 'macro_state', 'missing': ['macro_state']})
    elif macro == 'WARNING' and 'cyclical' in members:
        disabled += [(e, 'MACRO_WARNING_CYCLICAL') for e in effects['WARNING']['disable_cyclical']]
    elif macro == 'CRISIS':
        for e in effects['CRISIS']['disable']:
            if e == 'W2_ENTER' and u3_ok_2_5:
                continue  # 위기 중 편입: U3 조건 2~5 + W2 체크리스트를 모두 통과할 때만 (체크리스트는 criteria W2)
            disabled.append((e, 'MACRO_CRISIS'))
    return disabled, warnings, questions, unknown


def _u3(cfg, tc, s, fired_r3, r3_known, v_delta, macro):
    """§13-5 U3 conditions 1–5 → {'id': True/False/None}."""
    c = {x['id']: x for x in cfg['macro']['u3']['conditions']}
    out = {'macro_state': None if macro is None else macro in ('WARNING', 'CRISIS')}
    ratio = s.get('market_explained_ratio_60')
    if fired_r3 or (ratio is not None and ratio < c['market_led']['explained_min']):
        out['market_led'] = False
    elif ratio is None or not r3_known:
        out['market_led'] = None
    else:
        out['market_led'] = True
    q = s.get('q_industry_pct')
    out['quality'] = None if q is None else q >= c['quality']['q_industry_pct_min']
    nd, ic = s.get('net_debt_to_ebitda'), s.get('interest_coverage')
    fs = c['financial_safety']
    if nd is not None and nd >= fs['net_debt_to_ebitda_lt'] or ic is not None and ic <= fs['interest_coverage_gt']:
        out['financial_safety'] = False
    else:
        out['financial_safety'] = None if nd is None or ic is None else True
    out['cheaper'] = None if v_delta is None else v_delta >= tc['thresholds']['v_expand']
    return out


def _all(values):
    values = list(values)
    return False if False in values else (None if None in values else True)


def active_codes(cfg, mode='CORE_V0', target_version=None):
    """§0-1: core v0 codes (+T2/U2 once TARGET v1 is adopted); mode 'ALL' also runs the stored candidates."""
    scope = cfg['implementation_scope']
    if mode == 'ALL':
        return [c['code'] for c in cfg['codes']]
    active = set(scope['core_v0']) | (set(scope['target_v1_only']) if target_version == 'v1' else set())
    return [c['code'] for c in cfg['codes'] if c['code'] in active]


def evaluate(cfg, s, mode='CORE_V0'):
    """One symbol's facts → judgement. Input keys: docs/playbook/PLAYBOOK_ENGINE_V1.md.
    Codes outside the active set (§0-1 candidates, T2/U2 before TARGET v1) are not judged; they are listed under
    `candidate_signals` so real cases can be counted for the 2027-02 review."""
    levels = [lv['id'] for lv in cfg['levels']]
    code_cfg = {c['code']: c for c in cfg['codes']}
    basis = s.get('basis') or 'v1'
    tc = type_context(cfg, s.get('memberships'), basis)
    th = tc['thresholds']
    held = bool(s.get('held'))
    conv = s.get('conviction') or {}
    conv_active = bool(conv.get('active'))
    macro = None if s.get('macro_available_count') == 0 else s.get('macro_state')
    drops = _drops(s)
    r2_hits, r2_missing, maintained = _r2(cfg, tc, s, drops)
    v_delta = s['v_now'] - s['v_prev20'] if _known(s.get('v_now'), s.get('v_prev20')) else None
    actual, target = s.get('actual_pct'), s.get('target_pct')
    fired, unknown, e4 = {}, [], []

    def fire(code, reasons):
        fired[code] = reasons

    def miss(code, fields):
        unknown.append({'code': code, 'missing': sorted(set(fields))})

    data = s.get('data') or {}
    x1 = [r for k, r in (('price_missing', 'PRICE_MISSING'), ('fx_missing', 'FX_MISSING'), ('snapshot_missing', 'SNAPSHOT_MISSING')) if data.get(k)]
    if x1:
        fire('X1', x1)
    if s.get('coverage') == 'BLOCKED':
        fire('X2', ['COVERAGE_BLOCKED'])
    if s.get('user_excluded'):
        fire('X3', ['USER_EXCLUDED'])
    if held and (s.get('invalidation_triggered') or (conv_active and conv.get('invalidated'))):
        fire('R1', ['CONVICTION_INVALIDATED'])  # §0-1: 무효화 조건 발생 시 R1은 모든 보유 종목에 적용
    ex, mean, sd = s.get('excess_20'), s.get('excess_mean_252'), s.get('excess_sd_252')
    r3_cond = (ex < mean - num(cfg, 'r3_sigma') * sd) if _known(ex, mean, sd) else None  # also U3 condition 2 (R3 미발동)
    if held:
        if r2_hits:
            cut = [h for h in r2_hits if h['metric'] == 'dividend_cut']
            own = s.get('own_value_worsened')
            if basis == 'v1' or cut or own is True:
                fire('R2', sorted({'DIVIDEND_CUT' if h['metric'] == 'dividend_cut' else 'QG_DECLINE' for h in (r2_hits if basis == 'v1' or own is True else cut)}))
            elif own is False:
                e4.append('QG_RELATIVE_DECLINE')  # §14-1: 남들이 좋아져서 상대적으로 밀린 것
            else:
                miss('R2', ['own_value_worsened'])
                e4.append('QG_RELATIVE_DECLINE_UNVERIFIED')
        elif r2_missing:
            miss('R2', r2_missing)
        if r3_cond is True:
            fire('R3', ['RECHECK_ABNORMAL_DROP'])
        elif r3_cond is None:
            miss('R3', [k for k in ('excess_20', 'excess_mean_252', 'excess_sd_252') if s.get(k) is None])
    if s.get('coverage_prev') == 'READY' and s.get('coverage') == 'PARTIAL':
        fire('R4', ['COVERAGE_DEGRADED'])
    if s.get('user_hold'):
        fire('R5', ['USER_HOLD'])
    if held:
        if maintained is True and v_delta is not None:
            if -v_delta >= th['v_reduce']:
                fire('T1', ['V_DETERIORATED'])
            if v_delta >= th['v_expand']:
                fire('U1', ['V_IMPROVED'])
        elif maintained is not False:
            fields = (r2_missing if maintained is None else []) + ([] if v_delta is not None else ['v_change_20'])
            miss('T1', fields)
            miss('U1', fields)
    if target is not None:
        if actual is None:
            miss('T2', ['actual_pct'])
            miss('U2', ['actual_pct'])
        else:
            b = band(cfg, target)
            if actual > target + b:
                if v_delta is None:
                    miss('T2', ['v_change_20'])
                elif abs(v_delta) < th['v_reduce']:
                    fire('T2', ['OVERWEIGHT_GAP'])
            if actual < target - b:
                fire('U2', ['UNDERWEIGHT_GAP'])
    u3 = _u3(cfg, tc, s, r3_cond is True, r3_cond is not None, v_delta, macro)
    if held:
        ok = _all(u3.values())
        if ok:
            fire('U3', ['MACRO_DISCOUNT'])
        elif ok is None:
            miss('U3', [k for k, v in u3.items() if v is None])
    if held and conv_active:
        total = s.get('conviction_total_pct')
        if total is None:
            miss('T3', ['conviction_total_pct'])
        elif total > num(cfg, 'conviction_cap_pct'):
            fire('T3', ['CONVICTION_CAP_EXCEEDED'])
    days = s.get('earnings_days_until')
    if (days is not None and 0 <= days <= num(cfg, 'e1_days_before')) or s.get('earnings_pending_reflection'):
        fire('E1', ['EARNINGS_WINDOW'])
    if s.get('type_changed'):
        fire('E2', ['TYPE_CHANGED'])
    if s.get('coverage') == 'PARTIAL' or s.get('qg_source_missing'):
        fire('E3', ['COVERAGE_PARTIAL'])
    if s.get('leaderboard_signal') in LEADERBOARD_SIGNALS:
        e4.insert(0, 'REASSESS_SIGNAL')
    exits = s.get('thirteenf_full_exit_managers')
    if held and exits is not None and exits >= num(cfg, 'thirteenf_full_exit_managers'):
        e4.append('THIRTEENF_FULL_EXIT')
    if s.get('structural_news'):
        e4.append('STRUCTURAL_NEWS')
    if e4:
        fire('E4', e4)
    if s.get('followup_due'):
        fire('E5', ['FOLLOWUP_DUE'])
    if held and conv_active and ((conv.get('months_held') or 0) >= num(cfg, 'conviction_review_months')
                                 or (conv.get('risk_review_count') or 0) >= num(cfg, 'conviction_review_risk_count')):
        fire('H2', ['CONVICTION_ANNUAL'])
    if not held:
        if s.get('watched'):
            fire('W1', ['WATCH'])
        rank = s.get('leaderboard_rank')
        if _known(rank, v_delta):
            if rank <= num(cfg, 'w2_rank_max') and v_delta >= num(cfg, 'w2_v_improve_points'):
                fire('W2', ['ENTRY_CANDIDATE'])
        else:
            miss('W2', [k for k, v in (('leaderboard_rank', rank), ('v_change_20', v_delta)) if v is None])
    active = set(active_codes(cfg, mode, s.get('target_version')))
    candidate_signals = [{'code': c, 'reasons': fired[c]} for c in sorted(fired, key=lambda c: code_cfg[c]['priority']) if c not in active]
    fired = {c: r for c, r in fired.items() if c in active}
    unknown = [u for u in unknown if u['code'] in active]
    if held and s.get('quarterly_check_due') and (not fired or (s.get('qg_source_missing') and s.get('post_earnings_check_due'))):
        fire('H1', ['QUARTERLY_CHECK'])  # §13-7: Q·G 없는 종목은 실적 발표 후 H1 필수

    ordered = sorted(fired, key=lambda c: (levels.index(code_cfg[c]['level']), code_cfg[c]['priority']))
    out_codes = [{'code': c, 'level': code_cfg[c]['level'], 'reasons': fired[c]} for c in ordered]
    primary = out_codes[0] if out_codes else None

    # §2-3, §5, §6-4, §13-5, §14 restrictions → per choice disabled reasons.
    disabled = []
    lvl = {c: code_cfg[c]['level'] for c in ordered}
    if any(lvl[c] == 'BLOCK' for c in ordered):
        disabled += [(a, 'BLOCKED') for a in TRADE_ACTIONS]
    if any(lvl[c] in ('RISK_RECHECK', 'REDUCE_REVIEW') for c in ordered):
        disabled.append(('INCREASE', 'DOWN_DISABLES_UP'))
    if 'E1' in fired and not (lvl[ordered[0]] == 'BLOCK' or ordered[0] == 'R1'):
        disabled += [(a, 'E1_HOLDS_TRADES') for a in TRADE_ACTIONS]
    if 'E3' in fired:
        disabled.append(('INCREASE', 'E3_DISABLES_EXPANSION'))
    if basis == 'v1':
        margin = s.get('safety_margin_pct')
        if margin is None:
            disabled += [('U1_INCREASE', 'CORE_UNVERIFIABLE'), ('W2_ENTER', 'CORE_UNVERIFIABLE')]
        elif margin < th['safety_margin_pct']:
            disabled += [('U1_INCREASE', 'SAFETY_MARGIN_BELOW_TYPE'), ('W2_ENTER', 'SAFETY_MARGIN_BELOW_TYPE')]
    else:
        vp, exp = s.get('v_industry_pct'), s.get('expectation_check_passed')
        if vp is not None and vp < th['v_industry_pct']:
            disabled += [('U1_INCREASE', 'V_PERCENTILE_BELOW_TYPE'), ('W2_ENTER', 'V_PERCENTILE_BELOW_TYPE')]
        if exp is False:
            disabled += [('U1_INCREASE', 'EXPECTATION_CHECK_FAILED'), ('W2_ENTER', 'EXPECTATION_CHECK_FAILED')]
        if vp is None or exp is None:
            disabled += [('U1_INCREASE', 'CORE_UNVERIFIABLE'), ('W2_ENTER', 'CORE_UNVERIFIABLE')]
    u3_ok_2_5 = _all(v for k, v in u3.items() if k != 'macro_state') is True
    sp_disabled, warnings, questions, sp_unknown = _special(cfg, tc, s, macro, u3_ok_2_5)
    disabled += sp_disabled

    keep = cfg['conviction_choice']

    def choices_for(code):
        base = list(code_cfg[code]['choices'])
        if mode == 'ALL' and conv_active and not conv.get('invalidated') and 'R1' not in fired and code in keep['applies_to']:
            base.append({k: keep[k] for k in ('id', 'label', 'action', 'source')})
        out = []
        for ch in base:
            scoped = code + '_' + ch['action']
            reasons = sorted({r for target_id, r in disabled if target_id in (ch['action'], scoped)})
            out.append({'id': ch['id'], 'label': ch['label'], 'action': ch['action'], 'enabled': not reasons, 'disabled_reasons': reasons})
        return out

    checks = []
    for c in ordered:
        for item in code_cfg[c]['checks']:
            checks.append({'code': c, 'text': item['text'], 'sources': item['sources']})
    for q in questions:
        if q['code'] in fired:
            checks.append({'code': q['code'], 'text': q['text'], 'sources': ['AI']})
    multiplier = num(cfg, 'macro_warning_split_multiplier') if macro == 'WARNING' else 1

    return {
        'schema': SCHEMA,
        'config_version': cfg['config_version'],
        'calibration': cfg['calibration'],
        'basis': basis,
        'mode': mode,
        'symbol': s.get('symbol'),
        'primary': primary,
        'secondary': out_codes[1:],
        'type': {k: tc[k] for k in ('primary', 'members', 'unknown', 'leader', 'thresholds')},
        'band_pp': None if target is None else band(cfg, target),
        'qg': {'q_drop': drops['q'], 'g_drop': drops['g'], 'qg_drop': drops['qg'], 'maintained': maintained, 'r2_hits': r2_hits},
        'v_change_20': v_delta,
        'macro': {'state': macro, 'label': cfg['macro']['unavailable_label'] if macro is None else macro, 'split_multiplier': multiplier, 'u3_conditions': u3},
        'checks': checks,
        'choices': choices_for(primary['code']) if primary else [],
        'choices_by_code': {c: choices_for(c) for c in ordered},
        'disabled': [{'target': t, 'reason': r} for t, r in sorted(set(disabled))],
        'candidate_signals': candidate_signals,
        'warnings': sorted(set(warnings)),
        'unknown': unknown + [{'rule': u['rule'], 'missing': u['missing']} for u in sp_unknown],
    }


def transition(cfg, frm, choice, ctx=None):
    """§4 (+§3, §13-3, §13-5) row for (code, choice) with every reference resolved for the symbol's context."""
    ctx = ctx or {}
    tc = type_context(cfg, ctx.get('memberships'), ctx.get('basis') or 'v1')
    macro = ctx.get('macro_state')
    row = next((r for r in cfg['transitions'] if r['from'] == frm and r['choice'] == choice), None)
    if row is None:
        return {'from': frm, 'choice': choice, 'state': 'NO_TRANSITION'}
    action = {}
    for k, v in row['action'].items():
        if k.endswith('_ref'):
            name = k[:-4]
            if v == 'TYPE_SPLITS':
                action[name] = tc['thresholds']['split_count'] * (num(cfg, 'macro_warning_split_multiplier') if macro == 'WARNING' else 1)
            else:
                action[name] = num(cfg, v)
        else:
            action[k] = v
    if 'cyclical_delta_pp' in action and 'cyclical' not in tc['members']:
        del action['cyclical_delta_pp']
    if choice == 'W2_PROCEED' and macro == 'CRISIS':
        action['fraction'] = num(cfg, 'w2_crisis_initial_fraction')
    followup = None
    if row['followup']:
        f = row['followup']
        if f['kind'] == 'DAYS':
            followup = {'kind': 'DAYS', 'days': num(cfg, f['days_ref'])}
        elif f['kind'] == 'TYPE_RECHECK':
            followup = {'kind': 'DAYS', 'days': tc['thresholds']['recheck_days']}
        else:
            followup = {'kind': f['kind']}
    nxt = row['next']
    if row.get('next_if_v_improved') and ctx.get('v_improved'):
        nxt = row['next_if_v_improved']
    tgt = cfg['target_change']
    target = None
    if action['kind'] in tgt['changes_target_kinds'] or 'cyclical_delta_pp' in action:
        target = {'store_as': tgt['store_as'],
                  'apply': 'IMMEDIATE_ON_APPROVAL' if choice in tgt['immediate_on_approval'] else tgt['apply_on'],
                  'freed_weight': tgt['freed_weight']}
    return {'from': frm, 'choice': choice, 'state': 'OK', 'action': action, 'next': nxt, 'followup': followup,
            'source': row['source'], 'type': tc['primary'], 'target': target}


def e4_level(cfg, drawdown, max_drawdown_3y, history_years, user_threshold=None):
    """§13-6: drawdown from peak vs the symbol's 3-year maximum drawdown (both as positive fractions).
    A user threshold (positive fraction) wins and maps straight to REASSESS when reached."""
    r = cfg['reassess_thresholds']
    if user_threshold is not None:
        if drawdown is None:
            return {'level': None, 'basis': 'USER', 'ratio': None}
        return {'level': 'REASSESS' if drawdown >= user_threshold else None, 'basis': 'USER', 'ratio': None}
    if history_years is None or history_years < r['history_years_min'] or drawdown is None or not max_drawdown_3y:
        return {'level': r['insufficient'], 'basis': 'SYSTEM', 'ratio': None}
    ratio = drawdown / max_drawdown_3y
    level = None
    for lv in r['levels']:
        if ratio >= lv['ratio_min']:
            level = lv['id']
    return {'level': level, 'basis': 'SYSTEM', 'ratio': ratio}


def criteria(cfg, code, facts, ctx=None):
    """Ordered §3 standards → the choice id they point to, or None with the missing facts."""
    ctx = ctx or {}
    tc = type_context(cfg, ctx.get('memberships'), ctx.get('basis') or 'v1')
    f = facts or {}

    def need(*keys):
        return [k for k in keys if f.get(k) is None]

    if code == 'R2':
        # "위에서부터 먼저 해당하는 것": a criterion that cannot be checked stops the walk (a later one may not win).
        status = f.get('thesis_status')
        if status is None:
            return {'choice': None, 'missing': ['thesis_status']}
        if sum(1 for x in status if x == 'BROKEN') * 2 > len(status):
            return {'choice': 'R2_THESIS_BROKEN', 'missing': []}
        missing = need('guidance_mid_lowered', 'peers_differ')
        if missing:
            return {'choice': None, 'missing': missing}
        if f['guidance_mid_lowered'] and f['peers_differ']:
            return {'choice': 'R2_COMPANY_GUIDANCE', 'missing': []}
        missing = need('peers_same_direction')
        if missing:
            return {'choice': None, 'missing': missing}
        if f['peers_same_direction'] >= num(cfg, 'r2_peer_same_direction_min'):
            return {'choice': 'R2_SECTOR_CYCLE', 'missing': []}
        metric = f.get('drop_metric') or 'qg'
        limits = [c[metric] for c in tc['thresholds']['r2'] if metric in c]
        missing = need('drop_excluding_one_offs') + ([] if limits else ['drop_metric'])
        if missing:
            return {'choice': None, 'missing': missing}
        if f['drop_excluding_one_offs'] < min(limits) * num(cfg, 'r2_one_off_ratio'):
            return {'choice': 'R2_ONE_OFF', 'missing': []}
        return {'choice': 'R2_NONE', 'missing': []}
    if code == 'T1':
        if tc['thresholds']['basis'] == 'v2':  # §14-2: 업종 내 V 백분위 < 30 이고 기대 점검 실패
            rule = cfg['v2_adjustments']['t1_reduce']
            missing = need('v_industry_pct', 'expectation_check_passed')
            if missing:
                return {'choice': None, 'missing': missing}
            reduce = f['v_industry_pct'] < rule['v_pct_below'] and f['expectation_check_passed'] is False
            return {'choice': 'T1_REDUCE' if reduce else 'T1_MAINTAIN', 'missing': []}
        missing = need('safety_margin_pct', 'implied_growth', 'actual_growth_3y')
        if missing:
            return {'choice': None, 'missing': missing}
        if f['safety_margin_pct'] < 0 and f['implied_growth'] > f['actual_growth_3y']:
            return {'choice': 'T1_REDUCE', 'missing': []}
        return {'choice': 'T1_MAINTAIN', 'missing': []}
    if code == 'T2':
        missing = need('excess_pp')
        if missing:
            return {'choice': None, 'missing': missing}
        return {'choice': 'T2_DEPOSIT' if f['excess_pp'] <= num(cfg, 't2_deposit_limit_pp') else 'T2_TRIM', 'missing': []}
    if code == 'H1':
        status = f.get('thesis_status')
        if status is None:
            return {'choice': None, 'missing': ['thesis_status']}
        if status.count('BROKEN') >= 1:
            return {'choice': 'H1_BROKEN', 'missing': []}
        if status.count('WEAKENED') >= 2:
            return {'choice': 'H1_WEAKENED', 'missing': []}
        return {'choice': 'H1_MAINTAIN', 'missing': []}
    if code == 'R5':
        missing = need('condition_met', 'extensions_used')
        if missing:
            return {'choice': None, 'missing': missing}
        if f['condition_met']:
            return {'choice': 'R5_RELEASE', 'missing': []}
        return {'choice': 'R5_EXTEND' if f['extensions_used'] < num(cfg, 'r5_max_extensions') else 'R5_DECIDE', 'missing': []}
    if code == 'W2':
        items = f.get('checks')
        if items is None or len(items) != 5 or any(x is None for x in items):
            return {'choice': None, 'missing': ['checks']}
        return {'choice': 'W2_PROCEED' if all(items) else 'W2_OBSERVE', 'missing': []}
    return {'choice': None, 'missing': [], 'state': 'NOT_MECHANICAL'}


def _compare(op, value, limit):
    if op == '>=':
        return value >= limit
    if op == '>':
        return value > limit
    if op == '<':
        return value < limit
    if op == '<=':
        return value <= limit
    if op == '==':
        return value == limit
    if op == 'in':
        return value in limit
    raise ValueError(op)


def classify_types_v0(cfg, metrics):
    """§6-2 rules → {type: {'member': True/False/None, 'missing': [...]}} (None = 확인 불가)."""
    metrics = dict(metrics or {})
    if metrics.get('sic') is not None:
        metrics['sector_group_candidate'] = sic_candidate(cfg, metrics['sic'])
    out = {}
    for rule in cfg['type_rules_v0']:
        if rule['combine'] == 'TYPE_CONFIG_V1':
            out[rule['type']] = {'member': None, 'missing': [], 'state': 'TYPE_CONFIG_V1'}
            continue
        results, missing = [], []
        for cond in rule['conditions']:
            v = (metrics or {}).get(cond['metric'])
            if v is None:
                missing.append(cond['metric'])
                results.append(None)
            else:
                results.append(_compare(cond['op'], v, cond['value']))
        if rule['combine'] == 'ALL':
            member = False if False in results else (None if None in results else True)
        else:
            member = True if True in results else (None if None in results else False)
        out[rule['type']] = {'member': member, 'missing': missing}
    return out


def portfolio_limits(cfg, rows, cash_pct=None):
    """§16 limits for a TARGET draft: rows [{'symbol', 'pct', 'sector'}]. ok is None when a sector is unknown."""
    lim = cfg['portfolio_limits']
    groups = {sec: g['id'] for g in lim['combined_groups'] for sec in g['sectors']}
    violations, unknown, sums = [], [], {}
    for r in rows:
        if r['pct'] > lim['single_max_pct']:
            violations.append({'rule': 'SINGLE_MAX', 'symbol': r['symbol'], 'pct': r['pct'], 'limit': lim['single_max_pct']})
        if r.get('sector') is None:
            unknown.append(r['symbol'])
            continue
        g = groups.get(r['sector'], r['sector'])
        sums[g] = sums.get(g, 0) + r['pct']
    for g in sorted(sums):
        if sums[g] > lim['sector_group_max_pct']:
            violations.append({'rule': 'SECTOR_GROUP_MAX', 'group': g, 'pct': sums[g], 'limit': lim['sector_group_max_pct']})
    held = [r for r in rows if r['pct'] > 0]
    if len(held) < lim['min_holdings']:
        violations.append({'rule': 'MIN_HOLDINGS', 'count': len(held), 'limit': lim['min_holdings']})
    total = sum(r['pct'] for r in rows) + (cash_pct or 0)
    if abs(total - cfg['target_v1']['sum_pct']) > 1e-9:
        violations.append({'rule': 'SUM_NOT_100', 'pct': total, 'limit': cfg['target_v1']['sum_pct']})
    ok = False if violations else (None if unknown else True)
    return {'ok': ok, 'violations': violations, 'unknown_sector': unknown, 'group_pct': sums}


def _sic(sic):
    if isinstance(sic, bool):
        return None
    if isinstance(sic, int) and 0 <= sic <= 9999:
        return sic
    if isinstance(sic, str) and re.fullmatch(r"[0-9]{1,4}", sic):
        return int(sic)
    return None


def sic_candidate(cfg, sic):
    sic = _sic(sic)
    if sic is None:
        return None
    for label, ranges in cfg['sic_candidates'].items():
        if any(lo <= sic <= hi for lo, hi in ranges):
            return label
    return 'NONE'


def sector_for(cfg, symbol, etf=None, sic=None):
    """§7: the 19 symbols use the §7-2 table; others map by ETF only when exactly one §7-1 row uses it."""
    for a in cfg['assignments']:
        if a['symbol'] == symbol:
            return {'sector': a['sector'], 'source': a['source']}
    sic = _sic(sic)
    if sic is not None:
        for row in cfg['sic_subgroups']:
            if any(lo <= sic <= hi for lo, hi in row['ranges']):
                return {'sector': row['sector'], 'source': 'SIC_SUBGROUP'}
    if etf in ('XLK', 'XLI'):
        return {'sector': 'technology_hardware' if etf == 'XLK' else 'general_industrial', 'source': 'ETF_FALLBACK'}
    if etf:
        rows = [r['id'] for r in cfg['sector_checks'] if etf in r['etfs']]
        if len(rows) == 1:
            return {'sector': rows[0], 'source': 'ETF_UNIQUE'}
        if rows:
            return {'sector': None, 'source': 'ETF_AMBIGUOUS', 'candidates': rows}
    return {'sector': None, 'source': 'NOT_AVAILABLE'}
