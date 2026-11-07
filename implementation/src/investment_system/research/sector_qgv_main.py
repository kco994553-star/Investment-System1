"""Main editor transport -> existing sector engine; display copies, never rescores.

This is an offline request/response bridge. Auth, browser reader and server route
belong to Main. No HTTP service, publication or front-end calculator is added.
"""
from __future__ import annotations
import copy
from .sector_qgv import (default_config,preset,validate_config,preview_qgv,
                        compare_previews,save_user_config,config_hash,list_factors)
from .sector_qgv_registry import CATALOG,MODEL,SECTORS,TEMPLATES

BRIDGE='sector-qgv-main-bridge/1'
MAIN_TEMP_IDS={
 'Q01_OPERATING_MARGIN':'operating_margin_ttm','Q_ROA':'roa_ttm','Q_ROE_COMMON':'roe_common_ttm',
 'Q_ROIC':'roic_explicit','Q_CFO_TO_AVG_ASSETS':'cfo_assets_ttm','Q05_ACCRUALS':'accruals_assets_ttm',
 'Q06_DEBT_TO_ASSETS':'debt_assets','Q14_COMMON_EQUITY_TO_ASSETS':'common_equity_assets',
 'Q_INTEREST_COVERAGE':'interest_coverage_ttm','G02_SALES_CAGR3':'revenue_cagr_3y',
 'G_EPS_CAGR3':'eps_diluted_cagr_3y','G13_COMMON_BPS_CAGR3':'common_bps_cagr_3y',
 'G06_ROA_CHANGE3':'roa_improvement_3y','G14_CFO_AVG_ASSETS_CHANGE3':'cfo_assets_improvement_3y',
 'V_EARNINGS_YIELD':'ep_ttm_diluted','V_PEG_FWD':'peg_forecast','V_FFO_TO_MCAP':'nareit_ffo_mcap',
 'V_CFO_YIELD':'cfo_mcap','V06_FCF_TO_MCAP':'fcf_mcap','V_DIVIDEND_YIELD_TTM':'dividend_yield_ttm',
 'V_EBITDA_TO_EV':'ebitda_ev','V_EBIT_TO_EV':'ebit_ev','V_SALES_TO_MCAP':'sales_mcap',
 'V_SALES_TO_EV':'sales_ev','V_BOOK_YIELD':'common_bp','V_TBV_YIELD':'tangible_common_bp',
 'V_SHAREHOLDER_YIELD':'shareholder_yield'}
ROLE_IDS={'accrual_quality':'accounting_quality','financial_strength':'financial_capacity',
          'capital':'financial_capacity','coverage':'interest_capacity','other':'other_value'}


def variant_id(value):
    if value=='V_FWD_EARNINGS_YIELD':raise ValueError('MAIN_FORWARD_PERIOD_AMBIGUOUS')
    result=MAIN_TEMP_IDS.get(value,value)
    if result not in CATALOG:raise ValueError('MAIN_FACTOR_UNKNOWN')
    return result


def editor_tree(p):
    return {'axis_weights':copy.deepcopy(p['axis_weights']),
        'roles':{a:[{'role':role,'weight_bp':r['weight'],
                    'factors':[{'factor_id':v,'weight_bp':w} for v,w in r['factors'].items()]}
                   for role,r in roles.items()] for a,roles in p['axes'].items()}}


def editor_config(config):
    validate_config(config)
    return {'schema':'sector-qgv-user-config/1','preset_set':'sector-qgv-default',
            'version':'0.1.0','overrides':{k:editor_tree(p) for k,p in config['scoped_overrides'].items()}}


def canonical_config(config):
    if config.get('schema_version')=='sector-qgv-config/1':
        validate_config(config);return copy.deepcopy(config)
    if (set(config)!={'schema','preset_set','version','overrides'} or
        config['schema']!='sector-qgv-user-config/1' or config['preset_set']!='sector-qgv-default' or
        config['version']!='0.1.0' or not isinstance(config['overrides'],dict)):
        raise ValueError('MAIN_CONFIG_VERSION_MISMATCH')
    result=default_config()
    for ctx,tree in config['overrides'].items():
        if len(ctx.split('|'))!=2:raise ValueError('MAIN_CONTEXT_INVALID')
        sector,template=ctx.split('|');p=preset(result,sector,template)
        if set(tree)!={'axis_weights','roles'} or set(tree['roles'])!={'Q','G','V'}:raise ValueError('MAIN_TREE_INVALID')
        p['axis_weights']=copy.deepcopy(tree['axis_weights']);p['axes']={}
        for axis,roles in tree['roles'].items():
            converted={}
            for r in roles:
                if set(r)!={'role','weight_bp','factors'}:raise ValueError('MAIN_ROLE_INVALID')
                role=ROLE_IDS.get(r['role'],r['role'])
                if role in converted:raise ValueError('MAIN_ROLE_DUPLICATE')
                fs={}
                for f in r['factors']:
                    if set(f)!={'factor_id','weight_bp'}:raise ValueError('MAIN_FACTOR_INVALID')
                    v=variant_id(f['factor_id'])
                    if v in fs:raise ValueError('MAIN_FACTOR_DUPLICATE')
                    if CATALOG[v]['role']!=role or CATALOG[v]['axis']!=axis:raise ValueError('MAIN_ROLE_REBASE_REQUIRED')
                    fs[v]=f['weight_bp']
                converted[role]={'weight':r['weight_bp'],'factors':fs}
            p['axes'][axis]=converted
        result['scoped_overrides'][ctx]=p
    validate_config(result);return result


def display_projection(preview,model,labels=None):
    """Copy engine totals/ranks/axes exactly. No browser aggregate/rank fallback."""
    rows=[];labels=labels or {}
    for r in preview['result_rows']:
        why={}
        for axis,value in r['axes'].items():
            missing=r.get('missing_factors',{}).get(axis,[])
            why[axis]=None if value is not None else r['factors'][missing[0]]['score_status'] if missing else r['status']
        rows.append({'company_id':r['company_id'],'universe_code':None,
            'sector_id':r['sector_id'],'template_id':r['accounting_template'],
            **r['axes'],'total':r['total'],'rank':r['rank'],
            'sector_rank':None,'sector_rank_reason':'NOT_PROVIDED_BY_ENGINE',
            'reason':None if r['status']=='VALID' else r['status'],
            'why':why,'excluded':[a for a,w in r.get('nominal_axis_weights',{}).items() if w==0],
            'lynch_tags':copy.deepcopy(labels.get(r['company_id'],[])),
            'gate_status':r['gate_status'],'missing_factors':r.get('missing_factors',{}),
            'context':r['sector_id']+'|'+r['accounting_template'] if r['sector_id'] and r['accounting_template'] else None})
    return {'model':model,'key':preview['cache_key'],'denominator':preview['coverage']['denominator']['count'],
        'computed':preview['coverage']['total']['valid'],
        'axes':{a:c['valid'] for a,c in preview['coverage']['axes'].items()},
        'reasons':copy.deepcopy(preview['coverage']['row_failures']),'rows':rows,
        'preview_id':preview['preview_id'],'request_id':preview['request_id']}


def run_preview_request(snapshot,request):
    if request.get('schema_version')!='sector-qgv-main-request/1':raise ValueError('MAIN_REQUEST_VERSION_MISMATCH')
    rid=request['request_id']
    if not isinstance(rid,str) or not rid:raise ValueError('MAIN_REQUEST_ID_REQUIRED')
    before_config=canonical_config(request['before_config']);after_config=canonical_config(request['after_config'])
    before=preview_qgv(before_config,snapshot,rid+':before')
    after=preview_qgv(after_config,snapshot,rid)
    diff=compare_previews(before,after,'MAIN_PREVIEW')
    labels={r['company_id']:r.get('lynch_tags',[]) for r in snapshot['rows']}
    b=display_projection(before,'BEFORE',labels);a=display_projection(after,'AFTER',labels)
    old={r['company_id']:r for r in b['rows']};common={r['company_id']:r for r in diff['rows']}
    display_diff={'common':diff['common_valid'],'gained':diff['gained'],'lost':diff['lost'],'rows':[]}
    for row in a['rows']:
        key=row['company_id'];c=common.get(key,{})
        display_diff['rows'].append({'company_id':key,'universe_code':None,'sector_id':row['sector_id'],
            'template_id':row['template_id'],'before':old[key],'after':row,
            'common_before':c.get('before_common_rank'),'common_after':c.get('after_common_rank')})
    return {'schema_version':'sector-qgv-main-response/1','bridge_version':BRIDGE,'request_id':rid,
        'before_config':before_config,'after_config':after_config,
        'before':before,'after':after,'diff':diff,
        'display':{'before':b,'after':a,'diff':display_diff},
        'saved_config':save_user_config(after_config,after,request_id=rid,expected_preview_id=after['preview_id'])}


def editor_contract():
    # Templates are options, not evidence that any real issuer belongs to them.
    c=default_config()
    return {'schema_version':'sector-qgv-editor-contract/1','bridge_version':BRIDGE,
        'model_version':MODEL,'default_config':editor_config(c),'canonical_policies':c,
        'catalog':list_factors(c,'INFORMATION_TECHNOLOGY','GENERAL'),
        'default_context':'INFORMATION_TECHNOLOGY|GENERAL',
        'contexts':{s+'|'+t:editor_tree(preset(c,s,t)) for s in SECTORS for t in TEMPLATES},
        'temporary_id_map':MAIN_TEMP_IDS,'temporary_role_map':ROLE_IDS,
        'ambiguous_ids':{'V_FWD_EARNINGS_YIELD':['ep_fy1','ep_ntm']},
        'selection_key':'variant_id','display_score_unit':'0_to_100',
        'raw_unit_source':'catalog.unit','local_scoring_allowed':False,
        'mapping_warning':'Context options never establish company classification or REIT book sector.'}
