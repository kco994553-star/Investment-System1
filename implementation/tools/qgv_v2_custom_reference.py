#!/usr/bin/env python3
"""Synthetic Python reference vectors for QGV v2 PERSONAL_PREVIEW two-level weights (qgv_v2.score_universe(weights=...)).

Usage: qgv_v2_custom_reference.py --write   (regenerates tests/fixtures/qgv_v2_custom_vectors_v1.json)
       qgv_v2_custom_reference.py --check   (exit 1 when the committed fixture differs from a fresh run)
Synthetic codes, prices and fundamentals only (SYN tickers, the qgv_v2_reference.py universe plus a raw-metric universe scored
by v2_scoring.score_rows); never a public or live-data serializer. The official vectors (qgv_v2_vectors_v1.json) are unchanged.
"""
import copy
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/qgv_v2_custom_vectors_v1.json'


def scored_universe():
    """A raw-metric universe (60 GENERAL in 3 SIC groups + 10 FINANCIAL + one TARGET row) scored by v2_scoring.score_rows,
    turned into qgv_v2 companies whose `factors` and `qg_axes` are exactly the published shape (E2 input)."""
    import qgv_v2_reference as base
    from investment_system.qgv import v2_scoring as vs
    rnd = random.Random(20261018)
    metrics_of = {p: sorted({mname for specs in vs.SUBMETRICS[p].values() for mname, _ in specs}) for p in ('GENERAL', 'FINANCIAL')}
    universe = {}
    for n in range(70):
        profile = 'FINANCIAL' if n >= 60 else 'GENERAL'
        group = None if profile == 'FINANCIAL' else ('syn_group_a', 'syn_group_b', 'syn_group_c')[n % 3] if n % 11 else 'syn_group_tiny'
        metrics = {}
        for mname in metrics_of[profile]:
            metrics[mname] = None if rnd.random() < 0.12 else round(rnd.uniform(-1.0, 1.0), 3)
        if n in (5, 17):  # Q axis below 50% of its weight
            for mname in ('roic', 'gross_profit_to_assets', 'moat_proxy', 'accruals_to_assets', 'fcf_to_net_income'):
                metrics[mname] = None
        universe[f'NYSE:SYNS{n:02d}'] = {'cik': 9000 + n, 'state': 'LIVE', 'profile': profile, 'industry_group': group, 'metrics': metrics}
    target = {'synt': dict(copy.deepcopy(universe['NYSE:SYNS03']), state='LIVE')}
    target['synt']['metrics']['roic'] = 0.9
    scores, _ = vs.score_rows(universe, target)
    companies = {}
    for (role, key), sc in sorted(scores.items()):
        src = universe[key] if role == 'universe' else target[key]
        n = int(key[-2:]) if role == 'universe' else 3
        company = base._company(n + 1, src['industry_group'], profile=src['profile'])
        company.update(cik=src['cik'], factors=sc['factors'], qg_axes={a: {'score': sc['axes'][a]['score']} for a in ('Q', 'G')})
        if role == 'target':
            company['in_cross_section'] = False
        companies[('TARGET:' + key) if role == 'target' else key] = company
    return companies


def trees():
    from investment_system.qgv import qgv_v2 as m
    official = m.official_weights('balanced')
    q_changed = copy.deepcopy(official)
    q_changed['inner']['Q']['q_profitability'] = 40
    zero = copy.deepcopy(official)
    zero['inner']['Q']['q_moat_proxy'] = 0
    zero['inner']['G']['g_recent_acceleration'] = 0
    v_custom = copy.deepcopy(official)
    v_custom['inner']['V'] = {'v_earnings_yield': 10, 'v_fcf_yield': 10, 'v_vs_industry': 30, 'v_vs_own_history': 0, 'v_expectation_check': 50}
    no_v = copy.deepcopy(official)
    no_v['axis'] = {'Q': 60, 'G': 40, 'V': 0}
    halves = copy.deepcopy(official)
    halves['axis'] = {'Q': 12.5, 'G': 37.5, 'V': 50}
    halves['inner']['G'] = {'g_revenue_growth': 0.5, 'g_per_share_growth': 0.25, 'g_growth_efficiency': 0.125, 'g_consistency': 0.0625, 'g_recent_acceleration': 0.0625}
    return {'official-balanced': official, 'q-profitability-40': q_changed, 'zero-excluded': zero, 'v-inner-custom': v_custom,
            'axis-no-v': no_v, 'fractional': halves}


def invalid_trees():
    from investment_system.qgv import qgv_v2 as m
    good = m.official_weights('balanced')
    out = []

    def bad(name, mutate):
        t = copy.deepcopy(good)
        mutate(t)
        out.append({'id': name, 'weights': t})
    bad('axis-sum-zero', lambda t: t.update(axis={'Q': 0, 'G': 0, 'V': 0}))
    bad('inner-sum-zero', lambda t: t['inner'].update(G=dict.fromkeys(m.WEIGHTS['G'], 0)))
    bad('negative', lambda t: t['inner']['Q'].update(q_profitability=-1))
    bad('above-100', lambda t: t['axis'].update(Q=101))
    bad('unknown-factor', lambda t: t['inner']['Q'].update(q_unknown=10))
    bad('missing-factor', lambda t: t['inner']['V'].pop('v_fcf_yield'))
    bad('factor-on-wrong-axis', lambda t: (t['inner']['Q'].pop('q_moat_proxy'), t['inner']['Q'].update(g_consistency=20)))
    bad('string-weight', lambda t: t['axis'].update(G='33'))
    bad('null-weight', lambda t: t['inner']['V'].update(v_vs_industry=None))
    bad('boolean-weight', lambda t: t['axis'].update(V=True))
    bad('missing-axis', lambda t: t['axis'].pop('V'))
    bad('extra-key', lambda t: t.update(gate=True))
    out.append({'id': 'not-an-object', 'weights': [1, 2, 3]})
    return out  # NaN/Infinity are not JSON: the Python and node tests add them directly.


def cases():
    import qgv_v2_reference as base
    from investment_system.qgv import qgv_v2 as m
    from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
    from investment_system.qgv.type_config import load_official_type_config
    cfg = load_official_type_config().to_dict()
    params = load_default_dcf_parameters()
    u = base.universe()
    pub = base.published(u)
    full = base.market(u, skip=('NYSE:SYNN1',))
    scored = scored_universe()
    scored_market = base.market(scored)
    t = trees()
    spec = [
        ('published-q-profitability-40', pub, full, 'q-profitability-40', None, True, False),
        ('published-zero-excluded', pub, full, 'zero-excluded', None, True, False),
        ('published-v-inner-custom', pub, full, 'v-inner-custom', None, True, False),
        ('recomputed-axis-no-v-types-off', u, full, 'axis-no-v', None, False, False),
        ('published-fractional-gate-off', pub, full, 'fractional', False, True, False),
        ('scored-official-forced-recompute', scored, scored_market, 'official-balanced', None, True, True),
        ('scored-q-profitability-40', scored, scored_market, 'q-profitability-40', None, True, False),
    ]
    out = []
    for cid, comps, mk, tree, gate, types_on, recompute in spec:
        result = m.score_universe(copy.deepcopy(comps), copy.deepcopy(mk), type_config=cfg, parameters=params, gate=gate,
                                  weights=copy.deepcopy(t[tree]), type_weights=types_on, recompute_published=recompute)
        # The score_rows universe is stored once (top-level `scored_universe`); its cases name it instead of repeating it.
        out.append({'id': cid, 'input': {'companies': 'scored_universe' if comps is scored else comps, 'synthetic_market': mk, 'weights': t[tree], 'gate': gate,
                                         'type_weights': types_on, 'recompute_published': recompute}, 'expected': result})
    return out


def payload():
    from investment_system.qgv import qgv_v2 as m
    t = trees()
    ids = [{'weights': t[k], 'type_weights': on, 'expected': m.weights_id(m.validate_weights(t[k]), on)} for k in sorted(t) for on in (True, False)]
    axis = []
    for k in ('zero-excluded', 'v-inner-custom', 'fractional'):
        tree = t[k]
        for a, scores in (('Q', {'q_profitability': 80, 'q_moat_proxy': None, 'q_earnings_quality': 40, 'q_financial_safety': None, 'q_capital_allocation': 0}),
                          ('G', {'g_revenue_growth': None, 'g_per_share_growth': 70, 'g_growth_efficiency': 50, 'g_consistency': None, 'g_recent_acceleration': 30}),
                          ('V', {'v_earnings_yield': 10, 'v_fcf_yield': None, 'v_vs_industry': None, 'v_vs_own_history': 90, 'v_expectation_check': None})):
            axis.append({'axis': a, 'scores': scores, 'weights': tree['inner'][a], 'expected': m.axis_score(scores, a, tree['inner'][a])})
    return {'schema_version': 1, 'kind': 'QGV_V2_CUSTOM_WEIGHT_VECTORS', 'synthetic': True, 'version': m.VERSION, 'status': m.STATUS,
            'namespace': m.PERSONAL_NAMESPACE, 'weights_schema': m.WEIGHTS_SCHEMA, 'scored_universe': scored_universe(),
            'units': {'weights_id': ids, 'axis': axis, 'invalid': invalid_trees()}, 'cases': cases()}


def main(argv):
    text = json.dumps(payload(), ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    if '--write' in argv:
        FIXTURE.write_text(text, encoding='utf-8')
        print('WROTE ' + str(FIXTURE.name))
        return 0
    if '--check' in argv:
        same = FIXTURE.exists() and FIXTURE.read_text(encoding='utf-8') == text
        print('FIXTURE_' + ('OK' if same else 'STALE'))
        return 0 if same else 1
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
