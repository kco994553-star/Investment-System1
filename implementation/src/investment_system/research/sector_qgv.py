"""Offline sector model adapter: common percentile, explicit variants, no data fetching.

The operating calc23.1 constants, formulas, publication, type weights and missing
policy are not modified. Inputs are evidence-bearing observations, not public totals.
"""
from __future__ import annotations
from fractions import Fraction
import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from investment_system.qgv.qgv_v2 import percentile, finite, GATE_PERCENTILE
from .sector_qgv_registry import (CATALOG, SECTORS, TEMPLATES, FINANCIAL, MODEL,
                                  ENGINE, NORMALIZATION, MAPPING, canonical)

VALID = {'VALID','VALID_ZERO','VALID_NEGATIVE'}
MIN_SAMPLE = 20


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def timestamp(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('TIMEZONE_REQUIRED')
    return t


def day(value):
    if not isinstance(value,str) or len(value)!=10: raise ValueError('INVALID_DATE')
    return date.fromisoformat(value)


def default_config():
    return dict(schema_version='sector-qgv-config/1',config_id='default',base_preset_id=MODEL,
                scoped_overrides={},display_preferences={},owner_scope='RESEARCH',
                normalization_policy=NORMALIZATION,missing_policy='strict/1',
                gate_policy='official-q-percentile-required/1',sector_mapping_version=MAPPING)


def _roles(items):
    roles={}
    for variant,weight in items:
        role=CATALOG[variant]['role']
        if role in roles: raise ValueError('ROLE_MUST_HAVE_EXPLICIT_INNER_WEIGHTS')
        roles[role]={'weight':weight*100,'factors':{variant:10000}}
    return roles


V_DEFAULTS={
 'CONSUMER_DISCRETIONARY':[('ep_ttm_diluted',35),('cfo_mcap',40),('fcf_mcap',25)],
 'CONSUMER_STAPLES':[('ep_ttm_diluted',35),('cfo_mcap',35),('dividend_yield_ttm',30)],
 'ENERGY':[('ep_ttm_diluted',40),('cfo_mcap',30),('ebitda_ev',30)],
 'FINANCIALS':[('ep_ttm_diluted',60),('common_bp',40)],
 'HEALTH_CARE':[('ep_ttm_diluted',40),('cfo_mcap',40),('sales_mcap',20)],
 'INDUSTRIALS':[('ep_ttm_diluted',35),('cfo_mcap',35),('ebitda_ev',30)],
 'INFORMATION_TECHNOLOGY':[('ep_ttm_diluted',30),('cfo_mcap',40),('sales_ev',30)],
 'MATERIALS':[('ep_ttm_diluted',40),('cfo_mcap',30),('ebitda_ev',30)],
 'TELECOMMUNICATIONS':[('ep_ttm_diluted',40),('cfo_mcap',40),('ebitda_ev',20)],
 'UTILITIES':[('ep_ttm_diluted',30),('cfo_mcap',40),('ebitda_ev',30)],
}


def _base(sector,template):
    if sector not in SECTORS or template not in TEMPLATES: raise ValueError('MAPPING_UNRESOLVED')
    q=_roles([('operating_margin_ttm',40),('accruals_assets_ttm',30),('debt_assets',30)])
    g=_roles([('revenue_cagr_3y',60),('roa_improvement_3y',40)])
    v=_roles(V_DEFAULTS[sector])
    if template in FINANCIAL:
        q={'profitability':{'weight':7000,'factors':{'roa_ttm':5000,'roe_common_ttm':5000}},
           'financial_capacity':{'weight':3000,'factors':{'common_equity_assets':10000}}}
        g=_roles([('common_bps_cagr_3y',60),('roa_improvement_3y',40)])
        v=_roles(V_DEFAULTS['FINANCIALS'])
    elif template=='ASSET_MANAGER':
        v=_roles(V_DEFAULTS['FINANCIALS'])
    elif template=='EQUITY_REIT':
        q=_roles([('cfo_assets_ttm',40),('interest_coverage_ttm',30),('debt_assets',30)])
        g=_roles([('revenue_cagr_3y',60),('cfo_assets_improvement_3y',40)])
        v=_roles([('nareit_ffo_mcap',50),('cfo_mcap',30),('dividend_yield_ttm',20)])
    return dict(preset_id=MODEL,version='0.1.0',state='draft',validation_state='initial',
                sector_id=sector,accounting_template=template,sector_mapping_version=MAPPING,
                axis_weights=dict(zip(('Q','G','V'),[x*100 for x in SECTORS[sector]])),axes={'Q':q,'G':g,'V':v})


def preset(config,sector,template):
    return copy.deepcopy(config.get('scoped_overrides',{}).get(sector+'|'+template,_base(sector,template)))


def _weights(weights):
    if not isinstance(weights,dict) or not weights or any(type(v)!=int or not 0<=v<=10000 for v in weights.values()) or sum(weights.values())!=10000:
        raise ValueError('WEIGHTS_MUST_SUM_10000')


def validate_config(config):
    for key,value in [('schema_version','sector-qgv-config/1'),('base_preset_id',MODEL),
                       ('normalization_policy',NORMALIZATION),('missing_policy','strict/1'),
                       ('gate_policy','official-q-percentile-required/1'),('sector_mapping_version',MAPPING)]:
        if config.get(key)!=value: raise ValueError('CONFIG_VERSION_MISMATCH:'+key)
    if config.get('owner_scope') not in ('RESEARCH','PRIVATE','PUBLIC'): raise ValueError('OWNER_SCOPE_INVALID')
    for scope,p in config.get('scoped_overrides',{}).items():
        sector,template=scope.split('|')
        if sector not in SECTORS or template not in TEMPLATES: raise ValueError('MAPPING_UNRESOLVED')
        if p.get('sector_id')!=sector or p.get('accounting_template')!=template or p.get('preset_id')!=MODEL or p.get('version')!='0.1.0' or p.get('sector_mapping_version')!=MAPPING:
            raise ValueError('PRESET_SCOPE_OR_VERSION_MISMATCH')
        _validate_preset(p)
    return {'valid':True,'config_hash':config_hash(config)}


def _validate_preset(p):
    if set(p['axis_weights'])!={'Q','G','V'} or set(p['axes'])!={'Q','G','V'}: raise ValueError('AXES_INVALID')
    _weights(p['axis_weights']);seen=set()
    for axis,roles in p['axes'].items():
        _weights({k:v['weight'] for k,v in roles.items()})
        for role,r in roles.items():
            _weights(r['factors'])
            for v in r['factors']:
                key=canonical(v);f=CATALOG[key]
                if key in seen: raise ValueError('DUPLICATE_VARIANT_ALIAS')
                seen.add(key)
                if f['axis']!=axis or f['role']!=role: raise ValueError('FACTOR_ROLE_MISMATCH')
                if f['calculator_status']!='IMPLEMENTED' and r['factors'][v]*r['weight']*p['axis_weights'][axis]>0:
                    raise ValueError('CALCULATOR_PENDING:'+key)


def config_hash(config):
    # Presentation/identity/scope do not change numerical settings; authorization is Main's job.
    semantic={k:v for k,v in config.items() if k not in ('display_preferences','config_id','owner_scope','canonical_config_hash')}
    return digest(semantic)


def effective_weights(p):
    out={}
    for axis,roles in p['axes'].items():
        for r in roles.values():
            for variant,w in r['factors'].items():
                out[canonical(variant)]=float(Fraction(p['axis_weights'][axis]*r['weight']*w, sum(p['axis_weights'].values())*sum(x['weight'] for x in roles.values())*sum(r['factors'].values()))) if p.get('weight_policy')=='positive-integer-ratios/1' else p['axis_weights'][axis]*r['weight']*w/(sum(p['axis_weights'].values())*1e8)
    return out


def _result(variant,ctx,status,value=None,components=None):
    f=CATALOG[variant];components=components or []
    ends=[x.get('period_end') for x in components if x.get('period_kind')!='PRICE' and x.get('period_end')]
    def latest(k):
        values=[x[k] for x in components if x.get(k)]
        try:return max(values,key=timestamp) if values else None
        except (ValueError,TypeError,AttributeError):return None
    result = dict(variant_id=variant,formula_version=f['formula_version'],value=value,status=status,unit=f['unit'],
        fiscal_period={'kind':f['period'],'end':max(ends) if ends else None},
        price_asof=ctx['valuation_date'] if f['axis']=='V' else None,issuer_id=ctx.get('issuer_id'),
        security_id=ctx.get('security_id'),source_available_at=latest('available_at'),retrieved_at=latest('retrieved_at'),
        currency=components[0].get('currency') if components else None,scope='CONSOLIDATED',
        corporate_action_basis=next((x.get('corporate_action_basis') for x in components if x.get('corporate_action_basis')),None),
        provenance=sorted({p for x in components for p in x.get('provenance',[])}),
        validation_basis='VERIFIED_COMPONENTS',raw_components_available=bool(components),display_multiple=None)
    if variant == 'eps_diluted_cagr_3y' and ctx.get('historical_share_basis'):
        result['historical_share_basis'] = copy.deepcopy(ctx['historical_share_basis'])
        result['historical_components_hash'] = digest({s['field']:x for s,x in zip(f['inputs'],components)}) if len(components)==len(f['inputs']) else None
        result['historical_period_start'] = min((x.get('period_start') or x['period_end'] for x in components),default=None)
        result['price_join_eligible'] = False
    return result


def _history_basis_valid(proof, *, issuer_id, component_hash, start, end, as_of):
    """Reviewed historical class/attribution proof, not a listed security ID."""
    try:
        return (proof['schema_version']=='historical-common-share-basis/1' and proof['status']=='VERIFIED'
            and bool(issuer_id) and proof['issuer_id']==issuer_id
            and proof['attribution']=='COMMON_DILUTED' and bool(proof['class_basis'])
            and bool(proof['adjustment_basis']) and bool(proof['provenance'])
            and bool(component_hash) and proof['normalized_components_hash']==component_hash
            and day(proof['valid_from'])<=day(start)<=day(end)<=day(proof['valid_to'])
            and timestamp(proof['source_available_at'])<=timestamp(as_of)
            and timestamp(proof['retrieved_at'])<=timestamp(as_of))
    except (KeyError,TypeError,ValueError,AttributeError):
        return False


def _history_observation_valid(obs, row, snapshot):
    return _history_basis_valid(obs.get('historical_share_basis'),issuer_id=row.get('issuer_id'),
        component_hash=obs.get('historical_components_hash'),start=obs.get('historical_period_start'),
        end=obs.get('fiscal_period',{}).get('end'),as_of=snapshot['as_of'])


def calculate_factor(variant,inputs,ctx):
    variant=canonical(variant);f=CATALOG[variant]
    specs=f['inputs'];parts=[inputs.get(s['field']) for s in specs]
    def fail(status):
        result=_result(variant,ctx,status,components=[x for x in parts if isinstance(x,dict)])
        result['raw_components_available']=bool(parts) and all(isinstance(x,dict) and x.get('value') is not None for x in parts)
        return result
    if f['calculator_status']!='IMPLEMENTED': return fail('CALCULATOR_PENDING')
    raw_only=(ctx.get('accounting_template') is None and
              ctx.get('raw_only_accounting_unconfirmed') is True and f['axis'] in ('Q','G'))
    if ctx.get('accounting_template') not in f['scope'] and not raw_only: return fail('NOT_APPLICABLE')
    if any(not isinstance(x,dict) or x.get('value') is None for x in parts): return fail('MISSING_INPUT')
    try:
        historical = variant=='eps_diluted_cagr_3y' and _history_basis_valid(ctx.get('historical_share_basis'),
            issuer_id=ctx.get('issuer_id'), component_hash=digest({s['field']:x for s,x in zip(specs,parts)}),
            start=min(x.get('period_start') or x['period_end'] for x in parts),
            end=max(x['period_end'] for x in parts),as_of=ctx['as_of'])
        cutoff=timestamp(ctx['as_of']);valuation=day(ctx['valuation_date'])
        if valuation>cutoff.astimezone(timezone.utc).date():return fail('VALUATION_AFTER_AS_OF')
        for s,x in zip(specs,parts):
            if x.get('status') and x['status'] not in VALID: return fail(x['status'])
            if not finite(x['value']): return fail('DOMAIN_INVALID')
            if not x.get('provenance') or not x.get('available_at') or not x.get('retrieved_at'): return fail('EVIDENCE_MISSING')
            available=timestamp(x['available_at'])
            if available>cutoff or available.astimezone(timezone.utc).date()>valuation or timestamp(x['retrieved_at'])>cutoff: return fail('NOT_YET_AVAILABLE')
            if x.get('period_kind')!=s['period']: return fail('PERIOD_MISMATCH')
            end=day(x['period_end'])
            if end>valuation and s['period'] not in ('FY1','NTM','FORECAST'): return fail('PERIOD_MISMATCH')
            if s['period']=='PRICE' and end!=valuation: return fail('PERIOD_MISMATCH')
            if s['period']=='TTM':
                if not x.get('period_start') or not 350<=(end-day(x['period_start'])).days<=380: return fail('PERIOD_MISMATCH')
            if x.get('issuer_id')!=ctx.get('issuer_id') or not ctx.get('issuer_id'): return fail('SCOPE_MISMATCH')
            expected=s['unit'].replace('currency',x.get('currency') or 'UNKNOWN')
            if x.get('unit')!=expected: return fail('UNIT_MISMATCH')
            if not x.get('scope') or x['scope']!='CONSOLIDATED': return fail('SCOPE_MISMATCH')
            if s['unit'] in ('currency/share','shares') or (f['axis']=='V' and s['unit']=='decimal'):
                if not historical and (not ctx.get('security_id') or x.get('security_id')!=ctx['security_id'] or not x.get('share_basis') or not x.get('corporate_action_basis')):
                    return fail('HISTORICAL_SHARE_BASIS_UNCONFIRMED' if variant=='eps_diluted_cagr_3y' and not ctx.get('security_id') else 'SCOPE_MISMATCH')
            if variant=='shareholder_yield' and x.get('evaluation_date')!=ctx['valuation_date']:return fail('PERIOD_MISMATCH')
            if s['field'] in ('issuer_mcap','enterprise_value') and (not x.get('capital_scope_evidence') or not x.get('corporate_action_basis')):
                return fail('SCOPE_MISMATCH')
            if s['field']=='issuer_mcap' and x.get('definition_id')!='ALL_CORRESPONDING_COMMON_CLASSES': return fail('SCOPE_MISMATCH')
            if s['field']=='enterprise_value' and x.get('definition_id')!='EQUITY_DEBT_PREFERRED_NCI_LESS_CASH': return fail('SCOPE_MISMATCH')
        currencies={x.get('currency') for s,x in zip(specs,parts) if 'currency' in s['unit']}
        if None in currencies or len(currencies)>1: return fail('CURRENCY_MISMATCH')
        per=[x for s,x in zip(specs,parts) if s['unit'] in ('currency/share','shares') or (f['axis']=='V' and s['unit']=='decimal')]
        if len({x.get('share_basis') for x in per})>1 or len({x.get('corporate_action_basis') for x in per})>1: return fail('SCOPE_MISMATCH')
        flows=[x for s,x in zip(specs,parts) if s['period']=='TTM']
        if len({x['period_end'] for x in flows})>1: return fail('PERIOD_MISMATCH')
        instant=[(s,x) for s,x in zip(specs,parts) if s['period']=='INSTANT']
        if f['period']=='LATEST_QUARTER' and len({x['period_end'] for s,x in instant})>1: return fail('PERIOD_MISMATCH')
        if any(s['field'].endswith('_begin') for s in specs):
            end=day(next(x['period_end'] for s,x in zip(specs,parts) if s['field'].endswith('_end')))
            begin=day(next(x['period_end'] for s,x in zip(specs,parts) if s['field'].endswith('_begin')))
            if not 350<=(end-begin).days<=380 or any(day(x['period_end'])!=end for x in flows): return fail('PERIOD_MISMATCH')
        ys={s['period']:day(x['period_end']) for s,x in zip(specs,parts)}
        if 'FY' in ys:
            for period,end in ys.items():
                if period.startswith('FY_MINUS_'):
                    years=int(period.rsplit('_',1)[1])
                    if abs((ys['FY']-end).days-365.25*years)>20: return fail('PERIOD_MISMATCH')
        if variant=='net_share_reduction' and not 350<=(day(parts[0]['period_end'])-day(parts[1]['period_end'])).days<=380: return fail('PERIOD_MISMATCH')
        values=[x['value'] for x in parts];op=f['formula']
        if op in ('ratio','difference_ratio','sum_ratio','ratio_average','difference_average','one_minus_ratio'):
            if op=='ratio':num,den=values
            elif op=='sum_ratio': num,den=sum(values[:-1]),values[-1]
            elif op=='difference_ratio': num,den=values[0]-values[1],values[2]
            elif op=='ratio_average':num,den=values[0],sum(values[1:])/2
            elif op=='difference_average':num,den=values[0]-values[1],sum(values[2:])/2
            else:num,den=values
            if den<=0: return fail('DOMAIN_INVALID')
            if variant=='roe_common_ttm' and any(v<=0 for v in values[1:]): return fail('DOMAIN_INVALID')
            if variant in ('fcf_mcap','fcf_ev') and values[1]<0: return fail('DOMAIN_INVALID')
            if variant=='net_share_reduction' and values[0]<=0:return fail('DOMAIN_INVALID')
            if variant=='dividend_yield_ttm' and values[0]<0:return fail('DOMAIN_INVALID')
            value=1-num/den if op=='one_minus_ratio' else num/den
        elif op.startswith('cagr'):
            if values[0]<=0 or values[-1]<=0:return fail('DOMAIN_INVALID')
            value=(values[0]/values[-1])**(1/int(op[-1]))-1
        elif op=='growth1':
            if values[-1]<=0:return fail('DOMAIN_INVALID')
            value=values[0]/values[-1]-1
        elif op=='difference': value=values[0]-values[1]
        elif op=='sum': value=sum(values)
        elif op=='peg':
            if any(v<=0 for v in values): return fail('DOMAIN_INVALID')
            value=values[1]/values[0]/(values[2]*100)
        elif op=='positive_growth_share':value=sum(a>b for a,b in zip(values,values[1:]))/(len(values)-1)
        else:return fail('CALCULATOR_PENDING')
        if not finite(value):return fail('DOMAIN_INVALID')
        out=_result(variant,ctx,'VALID_NEGATIVE' if value<0 else 'VALID_ZERO' if value==0 else 'VALID',value,parts)
        if f['axis']=='V' and op in ('ratio','difference_ratio','sum_ratio') and value>0:out['display_multiple']=1/value
        return out
    except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError):
        return fail('INPUT_INVALID')


def _validated_observation(row,variant,snapshot):
    f=CATALOG[variant];obs=row.get('observations',{}).get(variant)
    if not obs:return None,'MISSING_INPUT',False,False
    raw=obs.get('raw_components_available') is True
    external=obs.get('validation_basis')=='VERIFIED_DEFINITION' and not raw
    if f['calculator_status']!='IMPLEMENTED':return None,'CALCULATOR_PENDING',raw,external
    # Unknown mapping does not erase an independently calculated raw observation.
    # It still prevents scoring and adoption below.
    if row.get('accounting_template') is not None and row['accounting_template'] not in f['scope']:return None,'NOT_APPLICABLE',raw,external
    if obs.get('status') not in VALID:return None,obs.get('status') or 'MISSING_INPUT',raw,external
    try:
        if obs.get('variant_id')!=variant or obs.get('formula_version')!=f['formula_version'] or obs.get('unit')!=f['unit']:raise ValueError('OBSERVATION_VERSION_MISMATCH')
        if not finite(obs.get('value')):raise ValueError('DOMAIN_INVALID')
        if obs.get('validation_basis') not in ('VERIFIED_COMPONENTS','VERIFIED_DEFINITION') or not obs.get('provenance'):raise ValueError('EVIDENCE_MISSING')
        if not row.get('issuer_id') or obs.get('issuer_id')!=row['issuer_id']:raise ValueError('SCOPE_MISMATCH')
        if obs.get('scope')!='CONSOLIDATED' or not obs.get('currency'):raise ValueError('SCOPE_MISMATCH')
        available=timestamp(obs['source_available_at'])
        if available>timestamp(snapshot['as_of']) or available.astimezone(timezone.utc).date()>day(snapshot['valuation_date']) or timestamp(obs['retrieved_at'])>timestamp(snapshot['as_of']):raise ValueError('NOT_YET_AVAILABLE')
        period=obs['fiscal_period']
        if period['kind']!=f['period']:raise ValueError('PERIOD_MISMATCH')
        if day(period['end'])>day(snapshot['valuation_date']) and f['period'] not in ('FY1','NTM'):raise ValueError('PERIOD_MISMATCH')
        if f['axis']=='V':
            if obs.get('price_asof')!=snapshot['valuation_date']:raise ValueError('PERIOD_MISMATCH')
            if not row.get('security_id') or obs.get('security_id')!=row['security_id'] or not obs.get('corporate_action_basis'):raise ValueError('SCOPE_MISMATCH')
        if variant=='eps_diluted_cagr_3y' and obs.get('historical_share_basis') is not None:
            if not _history_observation_valid(obs,row,snapshot):raise ValueError('HISTORICAL_SHARE_BASIS_UNCONFIRMED')
        value=obs['value'];return value,'VALID_NEGATIVE' if value<0 else 'VALID_ZERO' if value==0 else 'VALID',raw,external
    except (ValueError,KeyError,TypeError) as exc:
        reason=str(exc) if isinstance(exc,ValueError) else 'EVIDENCE_MISSING'
        return None,reason,raw,external


def _mapped(row,s):
    try:
        m=row['mapping'];d=day(s['valuation_date'])
        return (row['sector_id'] in SECTORS and row['accounting_template'] in TEMPLATES and
                m['version']==s['mapping_version'] and bool(m['evidence_refs']) and
                day(m['valid_from'])<=d and (m.get('valid_to') is None or d<day(m['valid_to'])))
    except (ValueError,KeyError,TypeError):return False


def _axis_score(p,scores,axis):
    total=0.0;missing=[]
    if axis in p.get('pending_axes',[]):return None,[v for r in p['axes'][axis].values() for v in r['factors']]
    for r in p['axes'][axis].values():
        if not r['weight']:continue
        for v,w in r['factors'].items():
            if not w:continue
            key=canonical(v);value=scores[key]['score']
            if value is None:missing.append(key)
            else:total+=float(Fraction(r['weight']*w, sum(x['weight'] for x in p['axes'][axis].values())*sum(r['factors'].values())))*value if p.get('weight_policy')=='positive-integer-ratios/1' else r['weight']*w*value/1e8
    return (None if missing else total),missing


def aggregate(p,scores,gate,valuation_date):
    axes={};missing={}
    for axis in ('Q','G','V'):axes[axis],missing[axis]=_axis_score(p,scores,axis)
    active=[a for a,w in p['axis_weights'].items() if w]
    pre=None if any(axes[a] is None for a in active) else sum(axes[a]*p['axis_weights'][a]/sum(p['axis_weights'].values()) for a in active)
    gate_status='UNKNOWN';post={a:w/sum(p['axis_weights'].values()) for a,w in p['axis_weights'].items()};total=None
    if isinstance(gate,dict) and gate.get('calc_version')=='qgv2-calc/2026-10-23.1' and gate.get('as_of')==valuation_date and gate.get('provenance') and finite(gate.get('q_industry_percentile')) and 0<=gate['q_industry_percentile']<=100:
        gate_status='VALUE_EXCLUDED' if gate['q_industry_percentile']<=GATE_PERCENTILE else 'PASS'
        if gate_status=='VALUE_EXCLUDED':
            post['V']=0.0;remaining=sum(post.values())
            post={a:w/remaining if remaining else 0.0 for a,w in post.items()}
        if pre is not None and sum(post.values())>0:total=sum(axes[a]*w for a,w in post.items() if w)
    nominal=effective_weights(p)
    effective={canonical(v):post[a]*float(Fraction(r['weight']*w,sum(x['weight'] for x in rs.values())*sum(r['factors'].values()))) if p.get('weight_policy')=='positive-integer-ratios/1' else post[a]*r['weight']*w/1e8 for a,rs in p['axes'].items() for r in rs.values() for v,w in r['factors'].items()}
    return dict(axes=axes,missing_factors=missing,pre_gate_total=pre,total=total,gate_status=gate_status,
                nominal_effective_weights=nominal,post_gate_effective_weights=effective,
                nominal_axis_weights=p['axis_weights'],post_gate_axis_weights=post)


def _input_identity(s):
    # Display/name/Lynch changes cannot alter calculations, ordering or cache identity.
    fields=('company_id','issuer_id','security_id','sector_id','accounting_template','mapping','observations','gate','scoring_representative','representative_evidence')
    rows=sorted([{k:r[k] for k in fields if k in r} for r in s['rows']],key=lambda r:r['company_id'])
    return digest(dict(rows=rows,members=sorted(s['members']),**{k:s[k] for k in ('snapshot_id','input_version','universe_id','universe_version','mapping_version','as_of','valuation_date')}))


def scoring_representatives(records):
    """One evidenced scoring row per issuer; this is not a security master."""
    issuer_rows=defaultdict(list)
    for key,row in records.items():
        if row.get('issuer_id'):issuer_rows[row['issuer_id']].append(key)
    peers=set()
    for keys in issuer_rows.values():
        if len(keys)==1:peers.add(keys[0])
        else:
            reps=[key for key in keys if records[key].get('scoring_representative') is True and records[key].get('representative_evidence')]
            if len(reps)==1:peers.add(reps[0])
    return peers,issuer_rows


def rank_result_rows(rows):
    """Existing unrounded total ordering, applied to the evaluation set only."""
    for row in rows:row['rank']=None
    valid=sorted((r for r in rows if r['total'] is not None),key=lambda r:(-r['total'],r['company_id']))
    for n,r in enumerate(valid,1):r['rank']=n
    return valid


def preview_qgv(config,snapshot,request_id):
    return _preview_core(config,snapshot,request_id)


def _preview_core(config,snapshot,request_id,*,execution=None):
    """Shared kernel; dual research caller validates its explicit execution policy."""
    validate_config(config);s=snapshot
    if s.get('schema_version')!='sector-qgv-input/1' or s.get('mapping_version')!=MAPPING:raise ValueError('INPUT_VERSION_MISMATCH')
    if day(s['valuation_date'])>timestamp(s['as_of']).astimezone(timezone.utc).date():raise ValueError('VALUATION_AFTER_AS_OF')
    if len(set(s['members']))!=len(s['members']):raise ValueError('DUPLICATE_MEMBER')
    rows={}
    for row in s['rows']:
        key=row['company_id']
        if key in rows:raise ValueError('DUPLICATE_COMPANY_ID')
        if key not in s['members']:raise ValueError('ROW_OUTSIDE_UNIVERSE')
        rows[key]=row
    records={key:rows.get(key,{'company_id':key}) for key in sorted(s['members'])}
    matrix={};presets={};pools=defaultdict(list)
    peers,issuer_rows=scoring_representatives(records)
    for key,row in records.items():
        mapped=_mapped(row,s)
        if mapped:
            presets[key]=(copy.deepcopy(execution['uniform_preset']) if execution and execution['kind']=='COMMON' else
                          copy.deepcopy(execution['scoped_presets'][row['sector_id']+'|'+row['accounting_template']]) if execution and execution.get('scoped_presets') else
                          preset(config,row['sector_id'],row['accounting_template']))
        # Availability covers registered variants, even when mapping prevents scoring.
        matrix[key]={v:_validated_observation(row,v,s) for v in CATALOG}
        if execution and execution.get('core_policy')=='FIXED_333':
            for v,(value,status,raw,external) in matrix[key].items():
                if CATALOG[v]['calculator_status']!='IMPLEMENTED':
                    matrix[key][v]=(None,'CALCULATOR_PENDING',raw,external)
                elif row.get('accounting_template') in TEMPLATES and row['accounting_template'] not in CATALOG[v]['scope']:
                    matrix[key][v]=(None,'NOT_APPLICABLE',raw,external)
                elif value is not None and any(i['unit']=='currency/share' for i in CATALOG[v]['inputs']):
                    obs=row['observations'][v]
                    history_ok=v=='eps_diluted_cagr_3y' and _history_observation_valid(obs,row,s)
                    if not history_ok and (not row.get('security_id') or obs.get('security_id')!=row['security_id'] or not obs.get('corporate_action_basis')):
                        matrix[key][v]=(None,'SCOPE_MISMATCH',raw,external)
        if not mapped:continue
        group=() if execution and execution['kind']=='COMMON' else (row['sector_id'],row['accounting_template'])
        for v,(value,status,_,_) in matrix[key].items():
            if value is not None and key in peers:pools[group+(v,)].append(value)
    out=[]
    for key,row in records.items():
        p=presets.get(key);fs={}
        for v,(value,status,raw,external) in matrix[key].items():
            group=() if execution and execution['kind']=='COMMON' else (row.get('sector_id'),row.get('accounting_template'))
            pool=pools.get(group+(v,),[])
            reason=status
            score=None
            if value is not None:
                if not p:reason='MAPPING_UNRESOLVED'
                elif key not in peers:reason='ISSUER_REPRESENTATIVE_UNRESOLVED'
                elif len(pool)<MIN_SAMPLE:reason='PEER_SAMPLE_SMALL'
                else:
                    score=percentile(value,pool)
                    if CATALOG[v]['direction']=='LOWER':score=100-score
                    reason='VALID'
            fs[v]=dict(raw_value=value,raw_status=status,score=score,score_status=reason,valid_n=len(pool),
                       raw_components_available=raw,verified_external_available=external)
        result=dict(company_id=key,issuer_id=row.get('issuer_id'),security_id=row.get('security_id'),
                    sector_id=row.get('sector_id'),accounting_template=row.get('accounting_template'),
                    factors=fs,rank=None,status='MAPPING_UNRESOLVED')
        if p:
            result.update(aggregate(p,fs,row.get('gate'),s['valuation_date']))
            result['status']='VALID' if result['total'] is not None else 'GATE_UNKNOWN' if result['gate_status']=='UNKNOWN' else 'STRICT_INCOMPLETE'
            result['selected_variants']=[v for v,w in effective_weights(p).items() if w>0]
            if result['pre_gate_total'] is not None and sum(result['post_gate_axis_weights'].values())==0:result['status']='NO_WEIGHT_AFTER_GATE'
        else:result.update(axes=dict.fromkeys(('Q','G','V')),total=None,pre_gate_total=None,gate_status='UNKNOWN')
        out.append(result)
    valid=rank_result_rows(out)
    n=len(records);cov={'denominator':{'kind':'ORIGINAL_MEMBER_ROWS','count':n,'unique_issuers':len(issuer_rows),
                                    'security_id_present':sum(bool(r.get('security_id')) for r in records.values())},'factors':{}}
    for v in CATALOG:
        factor_rows=[r['factors'][v] for r in out]
        cov['factors'][v]=dict(raw_inputs=sum(x['raw_components_available'] for x in factor_rows),
            verified_external=sum(x['verified_external_available'] for x in factor_rows),
            raw_valid=sum(x['raw_value'] is not None for x in factor_rows),score_valid=sum(x['score'] is not None for x in factor_rows),
            denominator=n,raw_failures=dict(Counter(x['raw_status'] for x in factor_rows if x['raw_value'] is None)),
            score_failures=dict(Counter(x['score_status'] for x in factor_rows if x['score'] is None)))
        selected=[r for r in out if v in r.get('selected_variants',[])]
        cov['factors'][v]['selected_coverage']={'denominator':len(selected),
            'raw_valid':sum(r['factors'][v]['raw_value'] is not None for r in selected),
            'score_valid':sum(r['factors'][v]['score'] is not None for r in selected)}
    cov['axes']={a:{'valid':sum(r['axes'][a] is not None for r in out),'denominator':n} for a in ('Q','G','V')}
    cov['all_axes']={'valid':sum(all(v is not None for v in r['axes'].values()) for r in out),'denominator':n}
    cov['total']={'valid':len(valid),'denominator':n}
    cov['row_failures']=dict(Counter(r['status'] for r in out if r['total'] is None))
    cfg=config_hash(config);inp=_input_identity(s)
    versions=dict(model_version=MODEL,engine_version=ENGINE,normalization_version=NORMALIZATION,mapping_version=MAPPING,
                  input_version=s['input_version'],snapshot_id=s['snapshot_id'],universe_id=s['universe_id'],universe_version=s['universe_version'])
    cache=digest(dict(config_hash=cfg,input_hash=inp,**versions))
    return dict(schema_version='sector-qgv-preview/1',preview_id=digest({'cache':cache,'request_id':request_id}),
                request_id=request_id,config_hash=cfg,input_hash=inp,cache_key=cache,**versions,
                as_of=s['as_of'],valuation_date=s['valuation_date'],state='draft',validation_state='initial',
                deployment_state='NOT_DEPLOYED',performance_state='NOT_MEASURED',result_rows=out,coverage=cov,validation_errors=[])


def save_user_config(config,preview,*,request_id,expected_preview_id):
    validate_config(config)
    if preview.get('schema_version')!='sector-qgv-preview/1' or preview.get('validation_errors') or preview.get('config_hash')!=config_hash(config) or preview.get('request_id')!=request_id or preview.get('preview_id')!=expected_preview_id or preview.get('engine_version')!=ENGINE or preview.get('model_version')!=MODEL:
        raise ValueError('PREVIEW_CONFIG_OR_REQUEST_MISMATCH')
    return dict(config=copy.deepcopy(config),canonical_config_hash=config_hash(config),preview_id=preview['preview_id'],
                snapshot_id=preview['snapshot_id'],universe_id=preview['universe_id'],universe_version=preview['universe_version'])


def list_factors(config,sector,template):
    defaults=effective_weights(_base(sector,template));selected=effective_weights(preset(config,sector,template));out=[]
    for v,f in CATALOG.items():
        out.append(dict(copy.deepcopy(f),is_default=defaults.get(v,0)>0,selected=selected.get(v,0)>0,
                        accounting_applicability=template in f['scope'],validation_state='initial',
                        recommendation={'recommended':defaults.get(v,0)>0,'evidence_level':'OWNER_INITIAL_DESIGN',
                        'reason':'Owner §5 initial accounting/sector allocation; performance unverified.' if defaults.get(v,0)>0 else None,
                        'source_refs':f['evidence_refs'],'reviewed_at':'2026-11-06','version':MODEL}))
    return out


def comparison_configs():
    axis=default_config()
    for sector in SECTORS:
        for template in TEMPLATES:
            p=preset(axis,sector,template);p['axis_weights']={'Q':3400,'G':3300,'V':3300}
            axis['scoped_overrides'][sector+'|'+template]=p
    factor=default_config();p=preset(factor,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['V']['other_value']['factors']={'ebitda_ev':10000};factor['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    inner=default_config();p=preset(inner,'INFORMATION_TECHNOLOGY','GENERAL')
    p['axes']['V']['earnings']['weight']=3500;p['axes']['V']['cash']['weight']=3500
    inner['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL']=p
    return {'SQGV-20261106-C1':axis,'SQGV-20261106-C2':factor,'SQGV-20261106-C3':inner}


def compare_previews(before,after,comparison_id):
    for key in ('snapshot_id','input_hash','universe_id','universe_version','engine_version','normalization_version','mapping_version','valuation_date'):
        if before[key]!=after[key]:raise ValueError('COMPARISON_CONTEXT_MISMATCH:'+key)
    a={r['company_id']:r for r in before['result_rows']};b={r['company_id']:r for r in after['result_rows']}
    if set(a)!=set(b):raise ValueError('COMPARISON_UNIVERSE_MISMATCH')
    va={k for k,r in a.items() if r['total'] is not None};vb={k for k,r in b.items() if r['total'] is not None};common=va&vb
    ranks=[]
    for records in (a,b):ranks.append({k:n for n,k in enumerate(sorted(common,key=lambda k:(-records[k]['total'],k)),1)})
    return dict(comparison_id=comparison_id,common_valid=len(common),gained=sorted(vb-va),lost=sorted(va-vb),
                before_coverage=before['coverage']['total'],after_coverage=after['coverage']['total'],
                performance=None,performance_reason='PIT_EXECUTION_COST_INPUT_NOT_CONNECTED',
                rows=[dict(company_id=k,before=a[k]['total'],after=b[k]['total'],delta=b[k]['total']-a[k]['total'],
                           before_common_rank=ranks[0][k],after_common_rank=ranks[1][k],
                           before_rank=a[k]['rank'],after_rank=b[k]['rank']) for k in sorted(common)])
