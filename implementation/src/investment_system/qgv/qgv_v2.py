"""QGV v2 PROVISIONAL device scoring reference: V v2 factors, axes, composite, presets, value-trap gate. RAM only.

Source: docs/qgv_scoring_standard/QGV_V2_CANDIDATE.md (default weights exactly, no tuning, no Holdout) and
docs/qgv_scoring_standard/QGV_V2_V_DEVICE.md (device V definitions, percentile rules, composite).
Python reference for web_assets/qgv-v2.js (vectors: tests/fixtures/qgv_v2_vectors_v1.json). Prices, market caps,
EV and V scores are arguments/results in memory only: nothing here is stored, logged, published or sent.
Missing is None (NOT_AVAILABLE), never 0. Float sums are plain left-to-right loops (no math.fsum / builtin sum)
so that the JS port adds in the same order.
"""
from __future__ import annotations

import math
import re

from .dcf import reverse_dcf, two_stage_dcf

VERSION = 'qgv-v2'
STATUS = 'PROVISIONAL'
PILLARS = ('Q', 'G', 'V')
WEIGHTS = {
    'Q': {'q_profitability': 25, 'q_moat_proxy': 20, 'q_earnings_quality': 20, 'q_financial_safety': 20, 'q_capital_allocation': 15},
    'G': {'g_revenue_growth': 25, 'g_per_share_growth': 25, 'g_growth_efficiency': 20, 'g_consistency': 15, 'g_recent_acceleration': 15},
    'V': {'v_earnings_yield': 25, 'v_fcf_yield': 25, 'v_vs_industry': 20, 'v_vs_own_history': 15, 'v_expectation_check': 15},
}
FACTORS = tuple(f for a in PILLARS for f in WEIGHTS[a])
QG_FACTORS = tuple(f for a in ('Q', 'G') for f in WEIGHTS[a])
# §5 presets (axis weights Q/G/V). The value-trap gate (§4) is a separate toggle, default ON for every preset.
PRESETS = {
    'balanced': {'name': '균형', 'name_en': 'Balanced', 'weights': {'Q': 34, 'G': 33, 'V': 33}},
    'quality': {'name': '우량 중심', 'name_en': 'Quality first', 'weights': {'Q': 50, 'G': 25, 'V': 25}},
    'growth': {'name': '성장 친화', 'name_en': 'Growth friendly', 'weights': {'Q': 30, 'G': 50, 'V': 20}},
    'value': {'name': '가치(관문 켬)', 'name_en': 'Value (gate on)', 'weights': {'Q': 25, 'G': 20, 'V': 55}},
}
DEFAULT_PRESET = 'balanced'
GATE_DEFAULT = True
GATE_PERCENTILE = 30          # Q at or below this within-industry percentile -> V excluded ('가치 함정 주의')
MIN_PEERS = 8                 # industry group smaller than this -> whole priced universe (same rule as the Q·G side)
MIN_UNIVERSE = 8              # a cross-section smaller than this is NOT_AVAILABLE
MIN_AXIS_WEIGHT = 0.5         # §2: an axis (or the total) needs >= 50% of its weight available
MIN_HISTORY = 3               # own-history factor needs >= 3 past yields (month-end price of each fiscal period-end month)
PROFILES = ('GENERAL', 'FINANCIAL')
_DAY = re.compile(r'\d{4}-\d{2}-\d{2}')


def finite(v):
    try:
        return type(v) in (int, float) and math.isfinite(v)
    except OverflowError:
        return False


def positive(v):
    return finite(v) and v > 0


def percentile(value, population):
    """Mid-rank percentile 0..100 of value inside population (which contains value). n < 2 -> None."""
    n = len(population)
    if n < 2:
        return None
    less = 0
    equal = 0
    for y in population:
        if y < value:
            less += 1
        elif y == value:
            equal += 1
    return 100.0 * (less + 0.5 * (equal - 1)) / (n - 1)


def axis_score(scores, axis):
    """Renormalized weighted mean over available factor scores; < 50% of axis weight -> NOT_AVAILABLE."""
    weights = WEIGHTS[axis]
    total = 0
    used = 0
    acc = 0.0
    available = 0
    missing = []
    for f, w in weights.items():
        total += w
        s = scores.get(f)
        if s is None:
            missing.append(f)
            continue
        available += 1
        used += w
        acc += w * s
    share = used / total
    out = {'score': None, 'state': 'NOT_AVAILABLE', 'weight_available': share, 'factors_available': available,
           'factors_total': len(weights), 'missing': missing}
    if used == 0 or share < MIN_AXIS_WEIGHT:
        out['reason'] = 'AXIS_WEIGHT_INSUFFICIENT'
        return out
    out.update(score=acc / used, state='READY' if not missing else 'PARTIAL', reason=None)
    return out


def type_axis_weights(memberships, type_config):
    """GSQ-017 mixing (type_config/1): memberships {type_id: 0..1|None} -> parent Q/G/V weights. None -> fallback."""
    fallback = {p: float(type_config['fallback']['weights'][p]) for p in PILLARS}
    mix = type_config['mixing']
    types = type_config['types']
    if not isinstance(memberships, dict):
        return fallback, 'TYPE_UNCONFIRMED', []

    def m(tid):
        v = memberships.get(tid)
        return v if finite(v) and 0 <= v <= 1 else None
    order = {t['id']: i for i, t in enumerate(types)}
    recognized = [t for t in types if t['affects_qgv'] and m(t['id']) is not None and m(t['id']) >= mix['minimum_membership']]
    recognized.sort(key=lambda t: (-m(t['id']), order[t['id']]))
    dropped = set()
    for a, b in mix['exclusive_pairs']:
        present = [t for t in recognized if t['id'] in (a, b) and t['id'] not in dropped]
        if len(present) == 2:
            dropped.add(present[1]['id'])
    selected = [t for t in recognized if t['id'] not in dropped][:mix['maximum_types']]
    if not selected:
        none = all(m(t['id']) is None for t in types if t['affects_qgv'])
        weights, reason = dict(fallback), 'TYPE_UNCONFIRMED' if none else 'NO_RECOGNIZED_TYPE'
    else:
        mass = 0.0
        for t in selected:
            mass += m(t['id'])
        weights = {}
        for p in PILLARS:
            acc = 0.0
            for t in selected:
                acc += t['weights'][p] * m(t['id'])
            weights[p] = acc / mass
        reason = None
    clamped = {p: min(mix['pillar_max'], max(mix['pillar_min'], weights[p])) for p in PILLARS}
    total = 0.0
    for p in PILLARS:
        total += clamped[p]
    return {p: 100.0 * clamped[p] / total for p in PILLARS}, reason, [t['id'] for t in selected]


# TYPE-SCOPE (owner instruction 2026-10-17): approved type rules evaluated on the device from published price-free metrics.
PRICEFREE_TYPE_METRICS = ('revenue_cagr_3y',)


def pricefree_memberships(metrics, type_config):
    """The same approved type rule for every scored row (TARGET or not), from that row's own published metrics.

    Only a `ramp` rule on a PRICEFREE_TYPE_METRICS metric is evaluated (type_config/1: growth, revenue_cagr_3y 0.10 -> 0.20),
    with exactly company_types._membership's ramp. Unresolved rules, price-dependent rules (dividend_yield,
    sector_marketcap_rank) and other metrics stay None (NOT_AVAILABLE), never 0. JS: QgvV2.pricefreeMemberships."""
    out = {}
    for t in type_config['types']:
        if not t['affects_qgv']:
            continue
        rule, value = t['rule'], None
        if isinstance(rule, dict) and rule.get('kind') == 'ramp' and rule.get('metric') in PRICEFREE_TYPE_METRICS \
                and isinstance(metrics, dict) and finite(metrics.get(rule['metric'])):
            value = min(1.0, max(0.0, (metrics[rule['metric']] - rule['lower']) / (rule['upper'] - rule['lower'])))
        out[t['id']] = value
    return out


def composite_weights(preset_weights, type_weights, fallback):
    """Type weights applied on top of the preset: w_p ∝ preset_p × type_p / fallback_p (balanced preset -> type weights)."""
    raw = {p: preset_weights[p] * type_weights[p] / fallback[p] for p in PILLARS}
    total = 0.0
    for p in PILLARS:
        total += raw[p]
    return {p: 100.0 * raw[p] / total for p in PILLARS}


def month_close(month_closes, period_end):
    """Month-end close (device Prices tab, {YYYY-MM: close}) of the fiscal period-end month; None otherwise."""
    if not isinstance(month_closes, dict) or not isinstance(period_end, str) or not _DAY.fullmatch(period_end):
        return None
    v = month_closes.get(period_end[:7])
    return v if positive(v) else None


def normalized_ebit(v, years):
    """PLAYBOOK_V1 §13-2 (v0 · UNCALIBRATED): latest revenue × mean operating margin of the last `years` fiscal years.
    None unless revenue and `years` margins are all present (never filled)."""
    if not isinstance(v, dict) or not finite(v.get('revenue')):
        return None
    hist = [h for h in (v.get('operating_margin_history') or []) if isinstance(h, dict) and finite(h.get('value'))]
    hist.sort(key=lambda h: str(h.get('period_end')))
    if len(hist) < years:
        return None
    acc = 0.0
    for h in hist[-years:]:
        acc += h['value']
    return v['revenue'] * (acc / years)


def _metrics(company, quote, parameters, cyclical_years=None):
    """Per-company raw V metrics (RAM): yields, own-history score, expectation gap. Reasons when not available."""
    v = company.get('v_inputs') if isinstance(company, dict) else None
    out = {'ebit_yield': None, 'fcf_yield': None, 'own_history': None, 'gap': None,
           'implied_growth': None, 'realized_growth': None, 'reasons': {},
           'earnings_basis': 'NORMALIZED' if cyclical_years else 'REPORTED'}
    r = out['reasons']

    def fail(reason, keys=('ebit_yield', 'fcf_yield', 'own_history', 'gap')):
        for k in keys:
            r.setdefault(k, reason)
        return out
    if company.get('profile') == 'FINANCIAL':
        return fail('FINANCIAL_PROFILE_V_NOT_DEFINED')
    if not isinstance(v, dict):
        return fail('V_INPUTS_NOT_AVAILABLE')
    price = quote.get('price') if isinstance(quote, dict) else None
    if not positive(price):
        return fail('NO_DEVICE_PRICE')
    if v.get('currency') is None or quote.get('currency') != v.get('currency'):
        return fail('CURRENCY_BASIS_UNCONFIRMED')
    shares = v.get('diluted_shares')
    if not positive(shares):
        return fail('SHARES_NOT_AVAILABLE')
    ebit, fcf = v.get('ebit'), v.get('fcf')
    debt, cash = v.get('total_debt'), v.get('cash')
    # Own history: price-per-share basis, needs no EV.
    hist = v.get('ebit_per_share_history')
    closes = quote.get('month_closes')
    if cyclical_years:
        r['own_history'] = 'NORMALIZED_HISTORY_NOT_AVAILABLE'
    elif not finite(ebit):
        r['own_history'] = 'EBIT_NOT_AVAILABLE'
    elif not isinstance(closes, dict) or not closes:
        r['own_history'] = 'PRICE_HISTORY_NOT_AVAILABLE'
    else:
        past = []
        for h in hist if isinstance(hist, list) else []:
            if not isinstance(h, dict) or not finite(h.get('value')):
                continue
            c = month_close(closes, h.get('period_end'))
            if c is not None:
                past.append(h['value'] / c)
        if len(past) < MIN_HISTORY:
            r['own_history'] = 'HISTORY_TOO_SHORT'
        else:
            current = ebit / shares / price
            out['own_history'] = percentile(current, past + [current])
    # Expectation check: reverse DCF on FCF per share vs realized revenue growth.
    realized = v.get('revenue_cagr_3y')
    out['realized_growth'] = realized if finite(realized) else None
    if not finite(fcf):
        r['gap'] = 'FCF_NOT_AVAILABLE'
    else:
        rev = reverse_dcf(cashflow_per_share=fcf / shares, price=price, parameters=parameters,
                          cashflow_currency=v.get('currency'), price_currency=quote.get('currency'))
        if rev.state == 'NOT_AVAILABLE':
            r['gap'] = rev.reason_codes[0]
        else:
            out['implied_growth'] = rev.implied_growth
            if not finite(realized):
                r['gap'] = 'REALIZED_GROWTH_NOT_AVAILABLE'
            else:
                out['gap'] = rev.implied_growth - realized
    if not finite(debt) or not finite(cash) or debt < 0 or cash < 0:
        return fail('DEBT_CASH_NOT_AVAILABLE', ('ebit_yield', 'fcf_yield'))
    ev = price * shares + debt - cash
    if not ev > 0:
        return fail('EV_NON_POSITIVE', ('ebit_yield', 'fcf_yield'))
    if cyclical_years:
        # Cyclical type: EBIT-based yield on normalized earnings ('정상화 이익 기준'); no 5-year margins -> NA.
        norm = normalized_ebit(v, cyclical_years)
        if norm is None:
            r['ebit_yield'] = 'NORMALIZED_EARNINGS_NOT_AVAILABLE'
        else:
            out['ebit_yield'] = norm / ev
    elif finite(ebit):
        out['ebit_yield'] = ebit / ev
    else:
        r['ebit_yield'] = 'EBIT_NOT_AVAILABLE'
    if finite(fcf):
        out['fcf_yield'] = fcf / ev
    else:
        r['fcf_yield'] = 'FCF_NOT_AVAILABLE'
    return out


def _reference_range(company, parameters):
    """Price-free DCF '참고 범위' (not a factor): FCF/share at h = growth-rule lower and upper bounds."""
    v = company.get('v_inputs') if isinstance(company, dict) else None
    na = lambda reason: {'state': 'NOT_AVAILABLE', 'reason': reason, 'low': None, 'high': None}
    if company.get('profile') == 'FINANCIAL':
        return na('FINANCIAL_PROFILE_V_NOT_DEFINED')
    if not isinstance(v, dict) or not finite(v.get('fcf')) or not positive(v.get('diluted_shares')):
        return na('FCF_NOT_AVAILABLE')
    rule = parameters.get('explicit_growth_rule') if isinstance(parameters, dict) else None
    if not isinstance(rule, dict):
        return na('EXPLICIT_GROWTH_UNDECIDED')
    cf = v['fcf'] / v['diluted_shares']
    if not cf > 0:
        return na('NON_POSITIVE_CASHFLOW')
    ends = []
    for g in (rule['lower'], rule['upper']):
        x = two_stage_dcf(cashflow_per_share=cf, growth_rate=g, parameters=parameters, cashflow_currency=v.get('currency'))
        if x.state == 'NOT_AVAILABLE':
            return na(x.reason_codes[0])
        ends.append(x.value_per_share)
    return {'state': 'PROVISIONAL', 'reason': None, 'low': ends[0], 'high': ends[1]}


def _cross(values, groups, ids, pooled, *, industry, issuers=None):
    """Percentile per id over the pooled ids (cross-section: one point per issuer) whose value is not None.
    industry=True: within group (>= MIN_PEERS) else universe. A non-pooled id (TARGET-only row, second listing of
    the same issuer) is ranked against the pool plus its own point."""
    population = [i for i in pooled if values[i] is not None]
    issuers = issuers or {}
    out = {}
    for i in ids:
        if values[i] is None:
            continue
        issuer = issuers.get(i)
        pop = [j for j in population if j == i or not issuer or issuers.get(j) != issuer]
        if len(pop) + (0 if i in pop else 1) < MIN_UNIVERSE:
            out[i] = (None, 'CROSS_SECTION_TOO_SMALL', None, len(pop) + (0 if i in pop else 1))
            continue
        basis, peers = 'UNIVERSE', pop
        if industry:
            g = groups.get(i)
            members = [j for j in pop if g is not None and groups.get(j) == g]
            if g is not None and len(members) + (0 if i in members else 1) >= MIN_PEERS:
                basis, peers = 'INDUSTRY', members
            else:
                basis = 'UNIVERSE_FALLBACK'
        vals = [values[j] for j in peers] + ([] if i in peers else [values[i]])
        out[i] = (percentile(values[i], vals), None, basis, len(vals))
    return out


def _published_axis(axis, scores, published):
    """Q/G axis from the published sec-qgv2 score (the Q·G side's peer rules) with this side's coverage fields."""
    out = axis_score(scores, axis)
    score = published.get('score') if isinstance(published, dict) else None
    if finite(score) and 0 <= score <= 100:
        out.update(score=score, state='READY' if not out['missing'] else 'PARTIAL', reason=None)
    else:
        out.update(score=None, state='NOT_AVAILABLE', reason='AXIS_NOT_PUBLISHED')
    return out


def score_universe(companies, quotes, *, type_config, parameters, preset=DEFAULT_PRESET, gate=None):
    """Score every company. companies: {code: {industry_group, profile, factors, v_inputs, memberships,
    qg_axes?: published {Q:{score}, G:{score}}, in_cross_section?: False for TARGET-only/duplicate-issuer rows}};
    quotes: {code: {price, currency, month_closes?: {YYYY-MM: close}}} (device RAM). Returns {code: result}. Pure, deterministic."""
    if preset not in PRESETS:
        raise ValueError('PRESET_INVALID')
    gate_on = GATE_DEFAULT if gate is None else bool(gate)
    ids = sorted(companies)
    groups = {i: companies[i].get('industry_group') for i in ids}
    fallback = {p: float(type_config['fallback']['weights'][p]) for p in PILLARS}
    quotes = quotes if isinstance(quotes, dict) else {}
    # Q/G factor scores come from the public SEC file (already 0..100 or None).
    qg = {}
    for i in ids:
        f = companies[i].get('factors') if isinstance(companies[i].get('factors'), dict) else {}
        qg[i] = {k: (f.get(k) if finite(f.get(k)) and 0 <= f.get(k) <= 100 else None) for k in QG_FACTORS}
    def axis_of(i, a):
        pub = companies[i].get('qg_axes')
        return _published_axis(a, qg[i], pub.get(a)) if isinstance(pub, dict) else axis_score(qg[i], a)
    q_axis = {i: axis_of(i, 'Q') for i in ids}
    g_axis = {i: axis_of(i, 'G') for i in ids}
    pooled = [i for i in ids if companies[i].get('in_cross_section', True) is not False]
    issuers = {i: companies[i].get('cik') for i in ids}
    q_pct = _cross({i: q_axis[i]['score'] for i in ids}, groups, ids, pooled, industry=True, issuers=issuers)
    cyclical_type = type_config['value_basis']['cyclical_type']
    years = type_config['value_basis']['normalized_years']
    typed = {i: type_axis_weights(companies[i].get('memberships'), type_config) for i in ids}
    metrics = {i: _metrics(companies[i], quotes.get(i), parameters, years if companies[i].get('cyclical_basis') is True or cyclical_type in typed[i][2] else None) for i in ids}
    ey = _cross({i: metrics[i]['ebit_yield'] for i in ids}, groups, ids, pooled, industry=False, issuers=issuers)
    fy = _cross({i: metrics[i]['fcf_yield'] for i in ids}, groups, ids, pooled, industry=False, issuers=issuers)
    ind = _cross({i: metrics[i]['ebit_yield'] for i in ids}, groups, ids, pooled, industry=True, issuers=issuers)
    exp = _cross({i: (None if metrics[i]['gap'] is None else -metrics[i]['gap']) for i in ids}, groups, ids, pooled, industry=False, issuers=issuers)
    preset_weights = PRESETS[preset]['weights']
    results = {}
    for i in ids:
        c, m = companies[i], metrics[i]
        factors = {}
        for k in QG_FACTORS:
            s = qg[i][k]
            factors[k] = {'score': s, 'state': 'NOT_AVAILABLE' if s is None else 'PUBLIC', 'reason': 'SEC_FACTOR_NOT_AVAILABLE' if s is None else None, 'basis': None}
        for k, cross, key in (('v_earnings_yield', ey, 'ebit_yield'), ('v_fcf_yield', fy, 'fcf_yield'),
                              ('v_vs_industry', ind, 'ebit_yield'), ('v_expectation_check', exp, 'gap')):
            if i in cross and cross[i][0] is not None:
                factors[k] = {'score': cross[i][0], 'state': 'CALCULATED', 'reason': None, 'basis': cross[i][2]}
            else:
                factors[k] = {'score': None, 'state': 'NOT_AVAILABLE', 'reason': cross[i][1] if i in cross else m['reasons'].get(key), 'basis': None}
        oh = m['own_history']
        factors['v_vs_own_history'] = ({'score': oh, 'state': 'CALCULATED', 'reason': None, 'basis': 'OWN_HISTORY'} if oh is not None else
                                       {'score': None, 'state': 'NOT_AVAILABLE', 'reason': m['reasons'].get('own_history'), 'basis': None})
        v_axis = axis_score({k: factors[k]['score'] for k in WEIGHTS['V']}, 'V')
        axes = {'Q': q_axis[i], 'G': g_axis[i], 'V': v_axis}
        tw, type_reason, selected = typed[i]
        weights = composite_weights(preset_weights, tw, fallback)
        flags = []
        qp = q_pct.get(i)
        q_percentile, q_basis = (qp[0], qp[2]) if qp else (None, None)
        trap = gate_on and q_percentile is not None and q_percentile <= GATE_PERCENTILE
        if trap:
            flags.append('VALUE_TRAP_CAUTION')
        if gate_on and q_percentile is None:
            flags.append('GATE_NOT_EVALUATED')
        if axes['V']['score'] is None:
            flags.append('V_NOT_AVAILABLE')
        data = 0.0
        for p in PILLARS:
            if axes[p]['score'] is not None:
                data += weights[p]
        included = [p for p in PILLARS if axes[p]['score'] is not None and not (p == 'V' and trap)]
        total = None
        total_reason = None
        if data / 100.0 < MIN_AXIS_WEIGHT or not included:
            total_reason = 'AXIS_WEIGHT_INSUFFICIENT'
        else:
            acc = 0.0
            used = 0.0
            for p in included:
                acc += weights[p] * axes[p]['score']
                used += weights[p]
            total = acc / used
        available = 0
        for k in FACTORS:
            if factors[k]['score'] is not None:
                available += 1
        results[i] = {
            'version': VERSION, 'status': STATUS,
            'profile': {'preset': preset, 'gate': gate_on, 'id': VERSION + '/' + preset + '/gate-' + ('on' if gate_on else 'off')},
            'axes': axes, 'factors': factors, 'factors_available': available, 'factors_total': len(FACTORS),
            'q_industry_percentile': q_percentile, 'q_industry_basis': q_basis,
            'type_weights': tw, 'type_reason': type_reason, 'selected_types': selected, 'weights': weights,
            'v_excluded': 'VALUE_TRAP_GATE' if trap else None, 'value_trap_gate': bool(trap), 'total': total, 'total_reason': total_reason, 'flags': flags,
            'detail': {'earnings_basis': m['earnings_basis'], 'ebit_yield': m['ebit_yield'], 'fcf_yield': m['fcf_yield'], 'implied_growth': m['implied_growth'],
                       'realized_growth': m['realized_growth'], 'expectation_gap': m['gap'],
                       'industry_basis': factors['v_vs_industry']['basis'], 'industry_peers': ind[i][3] if i in ind else None},
            'reference_range': _reference_range(c, parameters),
        }
    return results
