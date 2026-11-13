"""Fixed 3/3/3 configurations and diagnostics; uses the existing dual/sector engines."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from .sector_qgv_registry import CATALOG, SECTORS, TEMPLATES, FINANCIAL, MAPPING
from .sector_qgv import default_config, V_DEFAULTS, digest

VERSION='dual-qgv-research/0.2.0'
POLICY='positive-integer-ratios/1'
IDS={'U2-333':'unified-333-eps/0.1.0','U1-333':'unified-333-persistence/0.1.0','S1-333':'sector-333/0.1.0'}
GENERAL_Q=['operating_margin_ttm','accruals_assets_ttm','debt_assets']
COMMON_Q=['roa_ttm','accruals_assets_ttm','debt_assets']
GENERAL_G=['revenue_cagr_3y','roa_improvement_3y','eps_diluted_cagr_3y']
COMMON_V=['ep_ttm_diluted','common_bp','cfo_mcap']
FINANCIAL_V=['ep_ttm_diluted','common_bp','dividend_yield_ttm']


def roles(variants):
    out={}
    for v in variants:
        role=CATALOG[v]['role']
        r=out.setdefault(role,{'weight':0,'factors':{}})
        r['factors'][v]=1;r['weight']+=1
    return out


def recipe(sector,template):
    q,g,v=GENERAL_Q,GENERAL_G,[x[0] for x in V_DEFAULTS[sector]]
    pending=[]
    if template in FINANCIAL:
        q=['roa_ttm','roe_common_ttm','common_equity_assets']
        g=['common_bps_cagr_3y','roa_improvement_3y','eps_diluted_cagr_3y']
        v=FINANCIAL_V
    elif template=='ASSET_MANAGER':v=FINANCIAL_V
    elif template=='EQUITY_REIT':
        q=['cfo_assets_ttm','interest_coverage_ttm','debt_assets']
        g=['revenue_cagr_3y','cfo_assets_improvement_3y','ffo_per_share_growth']
        v=['nareit_ffo_mcap','cfo_mcap','dividend_yield_ttm']
    elif sector=='FINANCIALS':
        # This is a proposal slot, not an inferred financial accounting model.
        v=FINANCIAL_V;pending=['V']
    return dict(preset_id=IDS['S1-333'],version='0.1.0',sector_id=sector,
        accounting_template=template,sector_mapping_version=MAPPING,
        weight_policy=POLICY,axis_weights=dict(zip('QGV',SECTORS[sector])),
        axes={a:roles(vs) for a,vs in zip('QGV',(q,g,v))},pending_axes=pending,
        recipe_state='PREPARING' if pending or any(CATALOG[x]['calculator_status']!='IMPLEMENTED' for x in q+g+v) else 'DEFINED_RESEARCH')


def candidate_configs():
    base=dict(schema_version='qgv-dual-config/2',version='0.1.0',minimum=20,
        missing_policy='strict/1',gate_policy='official-q-percentile-required/1',
        research_knowledge_cutoff='2026-11-13T09:38:00Z',execution_version=VERSION,
        study_id='QGV-333-20261113-01',additional_policy='CATALOG_ZERO_CORE_WEIGHT',core_policy='FIXED_333')
    out={}
    for key in ('U2-333','U1-333'):
        g=GENERAL_G if key=='U2-333' else ['revenue_cagr_3y','roa_improvement_3y','revenue_growth_consistency_3y']
        p=dict(preset_id=IDS[key],version='0.1.0',sector_id=None,accounting_template=None,
            sector_mapping_version=MAPPING,weight_policy=POLICY,axis_weights=dict.fromkeys('QGV',1),
            axes={a:roles(vs) for a,vs in zip('QGV',(COMMON_Q,g,COMMON_V))},pending_axes=[],recipe_state='DEFINED_RESEARCH')
        out[key]=dict(base,model_id=IDS[key],kind='COMMON',uniform_preset=p)
    out['S1-333']=dict(base,model_id=IDS['S1-333'],kind='SECTOR',sector_config=default_config(),
        scoped_presets={s+'|'+t:recipe(s,t) for s in SECTORS for t in TEMPLATES})
    return deepcopy(out)


def validate_candidate(config):
    expected=next((v for v in candidate_configs().values() if v['model_id']==config.get('model_id')),None)
    # Python considers True == 1 == 1.0; fixed integer-ratio JSON does not.
    try:matches=expected is not None and digest(config)==digest(expected)
    except (TypeError,ValueError):matches=False
    if not matches:raise ValueError('QGV333_FIXED_CONFIG_MISMATCH')
    for p in ([config['uniform_preset']] if config['kind']=='COMMON' else config['scoped_presets'].values()):
        seen=set()
        for a,rs in p['axes'].items():
            variants=[v for r in rs.values() for v in r['factors']]
            if len(variants)!=3:raise ValueError('QGV333_COUNT')
            for role,r in rs.items():
                if r['weight']!=len(r['factors']) or any(w!=1 for w in r['factors'].values()):raise ValueError('QGV333_WEIGHT')
                for v in r['factors']:
                    if v in seen or CATALOG[v]['axis']!=a or CATALOG[v]['role']!=role:raise ValueError('QGV333_VARIANT')
                    seen.add(v)


def fractions(p,post):
    """Exact rational weights beside display floats, never rounded basis-point weights."""
    def pair(v):return {'numerator':v.numerator,'denominator':v.denominator}
    axes={a:Fraction(w,sum(p['axis_weights'].values())) for a,w in p['axis_weights'].items()}
    if post.get('V')==0 and p['axis_weights']['V']:
        remaining=sum(axes[a] for a in 'QG');effective={a:axes[a]/remaining if a!='V' else Fraction(0) for a in axes}
    else:effective=axes
    out={'nominal_axes':{a:pair(w) for a,w in axes.items()},'post_gate_axes':{a:pair(w) for a,w in effective.items()},'nominal_factors':{},'post_gate_factors':{}}
    for a,rs in p['axes'].items():
        for r in rs.values():
            for v,w in r['factors'].items():
                inner=Fraction(r['weight']*w,sum(x['weight'] for x in rs.values())*sum(r['factors'].values()))
                out['nominal_factors'][v]=pair(axes[a]*inner);out['post_gate_factors'][v]=pair(effective[a]*inner)
    return out


def extend_coverage(result):
    rows=result['rows'];cov=result['coverage']
    def count(sub):return {'code_rows':len(sub),'issuers':len({r['issuer_id'] for r in sub if r.get('issuer_id')})}
    cov['stages']['nine_core_scores']=count([r for r in rows if len(r['selected_variants'])==9 and all(r['factors'][v]['score'] is not None for v in r['selected_variants'])])
    cov['stages']['gate_known']=count([r for r in rows if r['gate_status'] in ('PASS','VALUE_EXCLUDED')])
    for v,f in cov['selected_factors'].items():
        selected=[r for r in rows if v in r['selected_variants']]
        f['inputs']=count([r for r in selected if r['factors'][v]['raw_components_available'] or r['factors'][v]['verified_external_available']])
        f['raw_failures']={k:count([r for r in selected if r['factors'][v]['raw_status']==k and r['factors'][v]['raw_value'] is None]) for k in sorted({r['factors'][v]['raw_status'] for r in selected if r['factors'][v]['raw_value'] is None})}
        f['score_failures']={k:count([r for r in selected if r['factors'][v]['score_status']==k and r['factors'][v]['score'] is None]) for k in sorted({r['factors'][v]['score_status'] for r in selected if r['factors'][v]['score'] is None})}
    incompatible=[r for r in rows if any(r['factors'][v]['raw_status']=='NOT_APPLICABLE' for v in r['selected_variants'])]
    by_issuer=defaultdict(list)
    bad_ids={r['company_id'] for r in incompatible}
    for r in rows:
        if r.get('issuer_id'):by_issuer[r['issuer_id']].append(r)
    blocked_issuers={i for i,rs in by_issuer.items() if all(r['company_id'] in bad_ids for r in rs)}
    # Optimistic bound: all other inputs/classification/gates/peers assumed solved.
    cov['applicability_only_upper_bound']={'known_incompatible':count(incompatible),'issuers_all_rows_incompatible':len(blocked_issuers),
        'optimistic_issuers':cov['denominator']['issuers']-len(blocked_issuers),
        'assumptions':'ALL_OTHER_INPUTS_CLASSIFICATION_PEERS_AND_GATE_RESOLVED;NOT_FORECAST',
        'can_reach95_under_known_scope':cov['denominator']['issuers']-len(blocked_issuers)>=cov['target95']['issuers']}
    return cov


def configuration_contract():
    cs=candidate_configs();used=sorted({v for c in cs.values() for p in ([c['uniform_preset']] if c['kind']=='COMMON' else c['scoped_presets'].values()) for rs in p['axes'].values() for r in rs.values() for v in r['factors']})
    return dict(schema_version='qgv-333-contract/1',candidates=cs,factors={v:deepcopy(CATALOG[v]) for v in used},
        normalization='EXISTING_COMMON_OR_SECTOR_MIDRANK',deciles='stored-evaluation-deciles/1',
        unavailable_is_zero=False,additional_core_weight=0,formula_evidence='QGV_333_EVIDENCE.md',
        financial_V_third='RESEARCH_EXTENSION_DEFINED_DIVIDEND_YIELD;NOT_PRIOR_OPERATING_DEFAULT',
        original_models_replaced=False,performance='NOT_MEASURED',deployment='NOT_STARTED')
