"""Versioned 555 research orchestration using the existing percentile/axis kernels.

No data fetching, price reconstruction, official-policy mutation or UI arithmetic.
Raw metric definitions belong to v2_factors or the explicit sector catalog.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone, date
from fractions import Fraction
from functools import lru_cache
import math
import re

from ..qgv.qgv_v2 import WEIGHTS, axis_score, GATE_PERCENTILE
from ..qgv.v2_scoring import SUBMETRICS, _Pool, percentile, MIN_PEERS
from .sector_qgv import digest, timestamp
from .sector_qgv_registry import SECTORS, TEMPLATES, ALIASES as SECTOR_ALIASES

IDS={'U1-555':'unified-555/0.1.0','S1-555':'sector-555/0.1.0'}
OWNER_IDS={'U1-555':'unified-555/0.2.0','S1-555':'sector-555/0.2.0'}
TWO_STAGE_IDS={'U1-555':'unified-555/0.3.0','S1-555':'sector-555/0.3.0'}
OFFICIAL_REUSE_IDS={'U1-555':'unified-555/0.4.0','S1-555':'sector-555/0.4.0'}
FINANCIAL_TEMP_IDS={'U1-555':'unified-555-financial-temporary/0.5.0','S1-555':'sector-555-financial-temporary/0.5.0'}
REGISTERED_IDS={'0.1.0':IDS,'0.2.0':OWNER_IDS,'0.3.0':TWO_STAGE_IDS,'0.4.0':OFFICIAL_REUSE_IDS,'0.5.0':FINANCIAL_TEMP_IDS}
TWO_STAGE_POLICY='cross-filing-consistency-full-period/2'
OFFICIAL_REUSE_POLICY='official-kernel-share-reuse/1'
FINANCIAL_TEMP_POLICY='official-financial-role-bridge/1'
FINANCIAL_PEER_MODELS={'BANK','INSURANCE','BROKER','ASSET_MANAGER','MORTGAGE_REIT'}
OWNER_POLICIES=dict(classification_policy='official-profile-sic-provisional/1',
    accounting_policy='reit-general-financial-reference-only/1',
    historical_share_policy='cross-filing-annual-duplicates/1',
    growth_efficiency_policy='incremental-roic-then-roa-improvement/1',
    valuation_share_policy='central-weighted-average-diluted/1',
    target_policy='joint-eligible95-all15-reference/1')
V_SPECS={'v_earnings_yield':(('ebit_yield',1),),'v_fcf_yield':(('fcf_yield',1),),
    'v_vs_industry':(('ebit_yield',1),),'v_vs_own_history':(('own_history',1),),
    'v_expectation_check':(('gap',-1),)}
SPECS={**SUBMETRICS['GENERAL'],**V_SPECS}
ALIASES={'EV_EBIT_TTM':'ebit_yield','EV_FCF_TTM':'fcf_yield'}
ALIASES.update({alias:'sector::'+v for alias,v in SECTOR_ALIASES.items() if alias not in ALIASES})
ALIASES.update({'sector::'+alias:'sector::'+v for alias,v in SECTOR_ALIASES.items()})
SHARE_METRICS={'eps_cagr_3y','fcf_per_share_cagr_3y','dilution_3y'}
SHARE_DENOMINATOR='WEIGHTED_AVERAGE_DILUTED_SHARES'
FORMULAS={
 'roic':('NOPAT / mean(FY opening, closing invested capital)','FY','return_level','v2_factors._Company.roic'),
 'gross_profit_to_assets':('FY gross profit / FY closing assets','FY','gross_profit','v2_factors._metrics_general'),
 'moat_proxy':('mean(return) * max(0, 1-std/mean); mean<=0: mean; >=3 of 5 FY','FY_5Y_MIN3','return_level','v2_factors._moat'),
 'accruals_to_assets':('(FY NI - FY CFO) / mean(opening,closing assets)','FY','cash_conversion','v2_factors._metrics_general'),
 'fcf_to_net_income':('(FY CFO - cash CAPEX) / FY NI; NI>0','FY','cash_conversion','v2_factors._metrics_general'),
 'net_debt_to_ebitda':('(interest-bearing debt - cash) / (FY EBIT + DA); denominator>0','FY','debt_capacity','v2_factors._metrics_general'),
 'interest_coverage':('FY EBIT / FY interest; interest>0','FY','interest_capacity','v2_factors._metrics_general'),
 'dilution_3y':('(split-consistent diluted weighted shares FY/FY-3)^(1/3)-1','FY_3Y','share_basis','v2_factors._growth_common'),
 'incremental_roic_5y':('(NOPAT FY-NOPAT FY-5)/(IC FY-IC FY-5); delta IC>0','FY_5Y','incremental_return','v2_factors._incremental'),
 'incremental_roic_3y':('(NOPAT FY-NOPAT FY-3)/(IC FY-IC FY-3); delta IC>0','FY_3Y','incremental_return','v2_factors._incremental'),
 'revenue_cagr_3y':('(revenue FY/revenue FY-3)^(1/3)-1; positive endpoints','FY_3Y','revenue_growth','v2_factors._growth_common'),
 'eps_cagr_3y':('(verified diluted EPS FY/FY-3)^(1/3)-1; positive endpoints','FY_3Y','earnings_growth','v2_factors._growth_common'),
 'fcf_per_share_cagr_3y':('(verified FCF/share FY/FY-3)^(1/3)-1; positive endpoints','FY_3Y','cash_growth','v2_factors._metrics_general'),
 'revenue_positive_growth_share':('positive annual revenue changes / available changes; >=3 of 5','FY_5Y_MIN3','revenue_growth','v2_factors._growth_common'),
 'revenue_growth_volatility':('population std annual revenue changes; >=3 of 5','FY_5Y_MIN3','revenue_growth','v2_factors._growth_common'),
 'revenue_acceleration':('TTM revenue YoY growth - FY3 revenue CAGR','TTM_AND_FY3','revenue_growth','v2_factors._growth_common'),
 'ebit_yield':('validated TTM EBIT / positive EV','TTM','enterprise_earnings','sector_qgv.calculate_factor'),
 'fcf_yield':('(TTM CFO - positive cash CAPEX) / positive EV','TTM','enterprise_cash','sector_qgv.calculate_factor'),
 'own_history':('current EBIT/share/price percentile in eligible own historical values','HISTORY_MIN3','enterprise_earnings','qgv_v2.percentile'),
 'gap':('reverse DCF implied growth - realized FY3 revenue CAGR','DCF_AND_FY3','revenue_growth','qgv_v2.reverse_dcf'),
}


@lru_cache(maxsize=1)
def catalog():
    out={}
    for role,spec in SPECS.items():
        for metric,direction in spec:
            formula,period,family,source=FORMULAS[metric]
            if metric not in out:
                out[metric]=dict(canonical_id=metric,variant=f'{metric}/555-v0',display_name=metric,
                    aliases=[a for a,m in ALIASES.items() if m==metric],formula=formula,period=period,
                    unit='percentile' if metric=='own_history' else 'decimal',direction=direction,
                    axis=role[0].upper(),roles=[],accounting_scope=['GENERAL'],input_family=family,
                    formula_source=source,required_inputs=formula,source='EXISTING_CODE_DEFINITION',
                    implementation_status='EXISTING_KERNEL',availability='PER_INPUT',validation='REQUIRES_EVIDENCE',
                    default=True,recommendation='OWNER_555_BASELINE_NOT_PERFORMANCE_OPTIMUM')
            out[metric]['roles'].append(role)
    # Explicit namespace: FY legacy and TTM sector variants are never aliases.
    from .sector_qgv_registry import CATALOG
    for key,v in CATALOG.items():
        if v['calculator_status']!='IMPLEMENTED':continue
        out['sector::'+key]=dict(canonical_id='sector::'+key,variant=key+'/sector-1',display_name=v['display_name'],
            aliases=[a for a,m in ALIASES.items() if m=='sector::'+key],formula=v.get('formula',v.get('formula_id')),period=v.get('period'),unit=v.get('unit'),
            direction=1 if v['direction']=='HIGHER' else -1,axis=v['axis'],roles=[],
            accounting_scope=v['scope'],input_family=v.get('overlap_group',v['role']),
            formula_source='sector_qgv.calculate_factor',required_inputs=v['inputs'],source='SECTOR_CATALOG',
            implementation_status='EXISTING_KERNEL',availability='PER_INPUT',validation='REQUIRES_EVIDENCE',
            default=False,recommendation='SUITABLE_OPTION_NOT_DEFAULT')
    for key in ('ebit_yield','fcf_yield','own_history','gap'):
        out['central::'+key]=dict(out[key],canonical_id='central::'+key,
            variant=key+'/central-wad-reported-1',aliases=[],
            formula=out[key]['formula']+'; EV uses price × weighted-average diluted shares + debt − cash',
            formula_source='qgv_v2._metrics; qgv2_inputs._v_inputs',
            period='CENTRAL_SELECTED_REPORTED_FLOW_PERIOD',
            valuation_share_basis='WEIGHTED_AVERAGE_DILUTED',default=False,
            recommendation='OWNER_RESEARCH_20261114_NOT_ACTUAL_CLASS_MARKET_CAP')
    for key in SHARE_METRICS:
        out[key].update(denominator_definition=SHARE_DENOMINATOR,
            share_basis_validation='METRIC_SPECIFIC_FULL_USED_PERIOD',
            actual_issuance_interpretation=False,
            numerator_definition=('REPORTED_DILUTED_EPS_WITH_ATTRIBUTABLE_DILUTED_NUMERATOR_EVIDENCE'
                if key=='eps_cagr_3y' else 'FY_CFO_MINUS_CASH_CAPEX'
                if key=='fcf_per_share_cagr_3y' else 'WEIGHTED_AVERAGE_DILUTED_SHARE_COUNT_CHANGE'))
    from .qgv_555_financial_temporary import financial_catalog
    out.update(financial_catalog())
    return out


def configuration(candidate, *, version='0.1.0'):
    if candidate not in IDS:raise ValueError('UNKNOWN_MODEL')
    if version not in REGISTERED_IDS:raise ValueError('UNKNOWN_MODEL_VERSION')
    out=dict(schema_version='qgv-555-config/1',model_id=REGISTERED_IDS[version][candidate],candidate=candidate,
        version=version,axis_weights=dict(Q=34,G=33,V=33),sector_axis_overrides={},
        roles={r:dict(axis=a,weight=w,metrics={m:1 for m,d in SPECS[r]}) for a,rs in WEIGHTS.items() for r,w in rs.items()},
        minimum=MIN_PEERS,missing_policy='available-role-weight-50/1',
        submetric_missing_policy='available-submetric-weight-renormalize/1',
        reference_policy='legacy-general-industry-fallback8/1' if candidate=='U1-555' else 'sector-accounting-no-fallback8/1',
        gate_policy='official-q-percentile-required/1',duplicate_policy='DISCLOSE_ONLY',
        classification_dictionary_version='common-industry-dictionary/2',type_multiplier=False,
        additional_factor_weight=0,official=False)
    if version!='0.1.0':
        out.update(OWNER_POLICIES)
        if version=='0.3.0':out['historical_share_policy']=TWO_STAGE_POLICY
        if version in ('0.4.0','0.5.0'):out.update(historical_share_policy=OFFICIAL_REUSE_POLICY,
            share_evidence_scope='ALL_OFFICIAL_REUSE')
        if version=='0.5.0':
            from .qgv_555_financial_temporary import financial_role_recipes,VERSION
            out.update(financial_temporary_policy=FINANCIAL_TEMP_POLICY,
                financial_role_mapping_version=VERSION,financial_roles=financial_role_recipes())
        for role in V_SPECS:out['roles'][role]['metrics']={'central::'+k:v for k,v in out['roles'][role]['metrics'].items()}
    return out


def validate_configuration(c):
    if c.get('candidate') not in IDS:raise ValueError('MODEL_ID')
    base=configuration(c['candidate'],version=c.get('version'))
    if c.get('model_id')!=base['model_id']:raise ValueError('MODEL_ID')
    if c['version'] in ('0.4.0','0.5.0'):
        if c.get('share_evidence_scope') not in ('ALL_OFFICIAL_REUSE','EVIDENCE_ONLY'):raise ValueError('SHARE_EVIDENCE_SCOPE')
    elif c.get('share_evidence_scope') is not None:raise ValueError('SHARE_EVIDENCE_SCOPE')
    for key in ('financial_temporary_policy','financial_role_mapping_version'):
        if c.get(key)!=base.get(key):raise ValueError('POLICY_CHANGE_REQUIRES_SEPARATE_VERSION:'+key)
    if c['version']=='0.5.0':
        from .qgv_555_financial_temporary import validate_role_recipes
        validate_role_recipes(c.get('financial_roles',{}))
    if c.get('financial_roles')!=base.get('financial_roles'):raise ValueError('FINANCIAL_ROLE_MAPPING_VERSION')
    for k in OWNER_POLICIES:
        if c.get(k)!=base.get(k):raise ValueError('POLICY_CHANGE_REQUIRES_SEPARATE_VERSION:'+k)
    for k in ('schema_version','version','minimum','missing_policy','submetric_missing_policy',
              'reference_policy','gate_policy','duplicate_policy','type_multiplier','additional_factor_weight','classification_dictionary_version'):
        if c.get(k)!=base[k]:raise ValueError('POLICY_CHANGE_REQUIRES_SEPARATE_VERSION:'+k)
    def valid_weights(ws):
        return all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in ws) and sum(ws)>0
    if set(c['axis_weights'])!=set('QGV') or not valid_weights(c['axis_weights'].values()):raise ValueError('AXIS_WEIGHTS')
    for sector,weights in c.get('sector_axis_overrides',{}).items():
        if sector not in SECTORS or set(weights)!=set('QGV') or not valid_weights(weights.values()):raise ValueError('SECTOR_AXIS_WEIGHTS')
    if set(c['roles'])!=set(SPECS):raise ValueError('ROLE_IDS')
    cats=catalog()
    for a in 'QGV':
        if not valid_weights([r['weight'] for r in c['roles'].values() if r['axis']==a]):raise ValueError('ROLE_WEIGHTS')
    for role,r in c['roles'].items():
        if r['axis']!=role[0].upper():raise ValueError('ROLE_AXIS')
        ids=[ALIASES.get(m,m) for m in r['metrics']]
        if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_CANONICAL_METRIC')
        equivalent={'sector::ebit_ev':'ebit_yield','sector::fcf_ev':'fcf_yield'}
        if len({equivalent.get(m,m) for m in ids})!=len(ids):raise ValueError('DUPLICATE_SAME_FORMULA_METRIC')
        if not valid_weights(r['metrics'].values()):raise ValueError('METRIC_WEIGHTS')
        if any(m not in cats or cats[m]['axis']!=r['axis'] for m in ids):raise ValueError('UNSUPPORTED_METRIC_VARIANT')
    overrides=c.get('scoped_role_overrides',{})
    if overrides and c['candidate']!='S1-555':raise ValueError('UNIFIED_SCOPE_OVERRIDE')
    for scope,roles in overrides.items():
        if scope.count('|')!=1 or scope.split('|')[0] not in SECTORS or scope.split('|')[1] not in TEMPLATES:raise ValueError('SETTING_SCOPE')
        if not set(roles)<=set(SPECS):raise ValueError('ROLE_IDS')
        local=deepcopy(c);local['scoped_role_overrides']={};local['roles'].update(roles);validate_configuration(local)
    return c


def identity(s):
    ids=[r['company_id'] for r in s['rows']]
    if len(ids)!=len(set(ids)) or set(ids)!=set(s['members']):raise ValueError('POPULATION_MEMBERS')
    return dict(population_id=s['population_id'],population_version=s['population_version'],
        unit='CODE_ROW',code_rows=len(ids),issuers=len({r['issuer_id'] for r in s['rows'] if r.get('issuer_id')}),
        evaluation_day=s['evaluation_day'],input_cutoff=s['input_cutoff'],input_hash=digest(s),
        members_hash=digest(sorted(ids)),classification_version=s['classification_version'],
        classification_context=deepcopy(s.get('classification_context')),
        source_anchors=deepcopy(s.get('source_anchors',[])))


def official_reuse_assumptions_valid(proof):
    """Shared producer/direct-CLI invariant; labels cannot turn assumptions into evidence."""
    basis=proof.get('adoption_basis');requires=proof.get('requires_assumption')
    evidence=proof.get('evidence_only_eligible');assumptions=proof.get('allowed_assumptions')
    return (type(requires) is bool and type(evidence) is bool and isinstance(assumptions,list)
        and all(isinstance(x,str) and bool(x) for x in assumptions)
        and bool(assumptions)==requires
        and not (evidence and (requires or basis not in ('EVIDENCE_LINKED','FILING_SPLIT_ADJUSTED')))
        and not (basis=='OFFICIAL_ASSUMPTION_INHERITED' and not requires))


def _financial_enabled(c,r):
    return (c.get('financial_temporary_policy')==FINANCIAL_TEMP_POLICY and
        r.get('financial_calculation_profile')=='FINANCIAL' and
        r.get('financial_temporary_policy')==FINANCIAL_TEMP_POLICY and
        (r.get('owner_source_context') or {}).get('profile')=='FINANCIAL' and
        bool(r.get('financial_temporary_source_refs')))


def _row_support(c,r):
    if _financial_enabled(c,r):
        if c['candidate']=='U1-555':return True,None
        if r.get('sector_id') not in SECTORS:return False,'SECTOR_CLASSIFICATION_UNCONFIRMED'
        if r.get('accounting_template') not in FINANCIAL_PEER_MODELS:return False,'FINANCIAL_PEER_MODEL_UNCONFIRMED'
        return True,None
    ok=r.get('accounting_template')=='GENERAL' and (c['candidate']=='U1-555' or r.get('sector_id') in SECTORS)
    reason='SECTOR_CLASSIFICATION_UNCONFIRMED' if c['version']!='0.1.0' and r.get('accounting_template')=='GENERAL' else 'ACCOUNTING_RECIPE_PREPARING'
    return ok,None if ok else reason


def financial_peer_context(c,r,snapshot):
    """S1 peers require the retained point-in-time classification, not a label."""
    if not _financial_enabled(c,r) or c['candidate']!='S1-555':return r
    m=r.get('classification_mapping') or {};ctx=snapshot.get('classification_context') or {}
    hashes={x.get('classification_hash') for x in (ctx.get('source_contexts') or [ctx])}
    try:
        valid=(r.get('classification_status')=='VERIFIED' and bool(r.get('classification_record_id')) and
            m.get('common_record_id')==r['classification_record_id'] and bool(m.get('evidence_refs')) and
            m.get('common_dictionary_version')==c['classification_dictionary_version'] and
            m.get('common_classification_hash') in hashes and bool(m.get('common_mapping_version')) and
            date.fromisoformat(m['valid_from'])<=date.fromisoformat(snapshot['evaluation_day']) and
            (m.get('valid_to') is None or date.fromisoformat(snapshot['evaluation_day'])<date.fromisoformat(m['valid_to'])) and
            timestamp(m['knowledge_as_of'])<=timestamp(snapshot['input_cutoff']))
    except (KeyError,TypeError,ValueError,AttributeError):valid=False
    if valid:return r
    out=deepcopy(r);out['reported_peer_accounting_template']=r.get('accounting_template')
    out['accounting_template']=None
    return out


def _usable(r,metric,s,*,share_policy=None,share_evidence_scope=None,financial_policy=None):
    proof=(r.get('metric_evidence') or {}).get(metric)
    x=r.get('metrics',{}).get(metric)
    if metric.startswith('financial::'):
        if (financial_policy!=FINANCIAL_TEMP_POLICY or
            not _financial_enabled(dict(financial_temporary_policy=financial_policy),r)):
            return None,'FINANCIAL_TEMPORARY_NOT_ENABLED'
        spec=catalog()[metric]
        context=r.get('owner_source_context') or {}
        if (not proof or proof.get('status')!='TEMPORARY_OFFICIAL_FINANCIAL_RAW' or
            proof.get('financial_temporary_policy')!=FINANCIAL_TEMP_POLICY or
            proof.get('source_formula_version')!='qgv2-calc/2026-10-23.1' or
            proof.get('source_metric')!=spec['source_metric'] or proof.get('variant')!=spec['variant'] or
            not proof.get('source_refs') or proof.get('source_record_hash')!=context.get('record_hash') or
            proof.get('source_body_sha256')!=context.get('companyfacts_sha256') or
            any(not isinstance(context.get(k),str) or not re.fullmatch('[0-9a-f]{64}',context[k])
                for k in ('record_hash','companyfacts_sha256'))):
            return None,'FINANCIAL_RAW_SOURCE_UNVERIFIED'
        try:
            acquired=timestamp(context['acquired_at']);reviewed=timestamp(proof['reviewed_at'])
            available=timestamp(proof['available_at']);cutoff=timestamp(s['input_cutoff'])
            clock_ok=(timestamp(proof['source_available_at'])==acquired==timestamp(proof['retrieved_at']) and
                acquired<=reviewed<=available<=cutoff and
                (not proof.get('source_review_created_at') or acquired<=timestamp(proof['source_review_created_at'])<=reviewed))
        except (KeyError,TypeError,ValueError,AttributeError):clock_ok=False
        if not clock_ok:return None,'FINANCIAL_RAW_CLOCK_UNVERIFIED'
        if spec['historical_share_evidence_required']:
            basis=proof.get('adoption_basis')
            if basis in ('ADDITIONAL_VERIFICATION_REQUIRED','EXPLICIT_CONFLICT_EXCLUDED'):return None,basis
            if proof.get('raw_reusable') is not True:
                return None,proof.get('reason') or 'FORMULA_DOMAIN_OR_OTHER_INPUT_UNAVAILABLE'
            if (proof.get('official_share_reuse_version')!='held-555-official-share-reuse/1' or
                proof.get('historical_share_basis')!='OFFICIAL_PATH_REUSED' or
                proof.get('strict_verified') is not False or not official_reuse_assumptions_valid(proof)):
                return None,'FINANCIAL_SHARE_BASIS_UNVERIFIED'
            if basis not in ('EVIDENCE_LINKED','FILING_SPLIT_ADJUSTED','OFFICIAL_ASSUMPTION_INHERITED'):
                return None,'FINANCIAL_SHARE_BASIS_UNVERIFIED'
            if share_evidence_scope=='EVIDENCE_ONLY' and (proof['requires_assumption'] or not proof['evidence_only_eligible']):
                return None,'OFFICIAL_ASSUMPTION_NOT_IN_EVIDENCE_ONLY'
            from .qgv_555_official_share import FORMULAS as RF
            variant=RF.get(spec['source_metric'],'OFFICIAL_EQUITY_OVER_WEIGHTED_DILUTED_SHARES_CAGR_3Y')
            if proof.get('formula_variant')!=variant or proof.get('denominator_definition')!=SHARE_DENOMINATOR:
                return None,'FINANCIAL_SHARE_FORMULA_MISMATCH'
        return (x,'VALID') if proof.get('raw_reusable') is True and type(x) in (int,float) and math.isfinite(x) else (None,'RAW_MISSING')
    official_share=metric in SHARE_METRICS and share_policy==OFFICIAL_REUSE_POLICY
    if official_share:
        from .qgv_555_official_share import FORMULAS as REUSE_FORMULAS
        if not proof or proof.get('official_share_reuse_version')!='held-555-official-share-reuse/1':
            return None,'OFFICIAL_SHARE_REUSE_EVIDENCE_MISSING'
        basis=proof.get('adoption_basis')
        if basis in ('ADDITIONAL_VERIFICATION_REQUIRED','EXPLICIT_CONFLICT_EXCLUDED'):return None,basis
        if (basis not in ('EVIDENCE_LINKED','FILING_SPLIT_ADJUSTED','OFFICIAL_ASSUMPTION_INHERITED') or
            proof.get('strict_verified') is not False or not official_reuse_assumptions_valid(proof)):
            return None,'OFFICIAL_SHARE_REUSE_EVIDENCE_MISSING'
        if share_evidence_scope=='EVIDENCE_ONLY' and (
            proof['requires_assumption'] or not proof['evidence_only_eligible']):
            return None,'OFFICIAL_ASSUMPTION_NOT_IN_EVIDENCE_ONLY'
        if proof.get('denominator_definition')!=SHARE_DENOMINATOR:return None,'SHARE_DENOMINATOR_DEFINITION_MISMATCH'
        if proof.get('formula_variant')!=REUSE_FORMULAS[metric]:return None,'OFFICIAL_SHARE_FORMULA_MISMATCH'
    if type(x) not in (int,float) or not math.isfinite(x):return None,'RAW_MISSING'
    if metric in SHARE_METRICS and share_policy==TWO_STAGE_POLICY and (not proof or
        proof.get('share_eligibility_stage')!='FINAL_ELIGIBLE' or
        proof.get('two_stage_review_version')!='held-555-share-eligibility/2'):
        return None,'SHARE_PERIOD_ELIGIBILITY_UNVERIFIED'
    if metric in SHARE_METRICS and share_policy==TWO_STAGE_POLICY and proof.get('denominator_definition')!=SHARE_DENOMINATOR:
        return None,'SHARE_DENOMINATOR_DEFINITION_MISMATCH'
    if not proof or proof.get('status')!=('RESEARCH_USABLE' if official_share else 'VERIFIED') or not proof.get('source_refs') or proof.get('variant')!=catalog()[metric]['variant']:
        return None,'DEFINITION_OR_SOURCE_UNVERIFIED'
    if timestamp(proof['available_at'])>timestamp(s['input_cutoff']):return None,'NOT_AVAILABLE_AT_CUTOFF'
    if metric in SHARE_METRICS and proof.get('historical_share_basis')!=('OFFICIAL_PATH_REUSED' if official_share else 'VERIFIED'):return None,'HISTORICAL_SHARE_BASIS_UNVERIFIED'
    if r.get('accounting_template') not in catalog()[metric]['accounting_scope']:return None,'ACCOUNTING_NOT_APPLICABLE'
    if metric in ('ebit_yield','fcf_yield','own_history','gap') or metric.startswith('central::'):
        if proof.get('valuation_day')!=s['evaluation_day'] or proof.get('security_and_actions')!='VERIFIED':return None,'VALUATION_SECURITY_BASIS_UNVERIFIED'
        if metric.startswith('central::') and proof.get('share_basis')!='WEIGHTED_AVERAGE_DILUTED':return None,'VALUATION_SHARE_BASIS_UNVERIFIED'
    return x,'VALID'


def calculation_row(c, row):
    """Owner-approved research view; preserve the original classification record."""
    if c['version']=='0.1.0':return row
    out=deepcopy(row)
    if 'calculation_accounting_template' in row:
        context=row.get('owner_source_context') or {}
        activating=(row['calculation_accounting_template']=='GENERAL' and row.get('accounting_template')!='GENERAL')
        if activating and (not context or not (row.get('temporary_classification') or {}).get('source_refs')):
            raise ValueError('TEMPORARY_CLASSIFICATION_EVIDENCE')
        if (row.get('calculation_sector_id')!=row.get('sector_id') and row.get('calculation_sector_id') is not None
            and not row.get('calculation_sector_evidence')):
            raise ValueError('TEMPORARY_SECTOR_EVIDENCE')
        out['accounting_template']=row['calculation_accounting_template']
        out['sector_id']=row.get('calculation_sector_id')
        out['industry_group']=row.get('calculation_industry_group')
    if _financial_enabled(c,row):
        peer=row.get('financial_peer_template')
        if peer is not None and (peer not in FINANCIAL_PEER_MODELS or peer!=row.get('accounting_template')):
            raise ValueError('FINANCIAL_PEER_MODEL_EVIDENCE')
        out['accounting_template']=peer
    return out


def _gate(r,s):
    g=r.get('gate') or {}
    p=g.get('percentile')
    if (type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=100 or
        g.get('evaluation_day')!=s['evaluation_day'] or not g.get('source_refs') or
        g.get('calc_version')!='qgv2-calc/2026-10-23.1'):
        return 'UNKNOWN'
    return 'VALUE_EXCLUDED' if p<=GATE_PERCENTILE else 'PASS'


def _bindings(c,e,ref):
    from pathlib import Path
    import hashlib
    files=[Path(__file__),Path(__file__).parent.parent/'qgv/v2_scoring.py',Path(__file__).parent.parent/'qgv/qgv_v2.py']
    if c.get('financial_temporary_policy')==FINANCIAL_TEMP_POLICY:
        files.append(Path(__file__).parent/'qgv_555_financial_temporary.py')
    return dict(configuration_hash=digest(c),evaluation=identity(e),reference=identity(ref),
        code_hash=digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))


def run(c,e,ref,*,calculated_at=None):
    validate_configuration(c)
    for s in (e,ref):
        if s.get('schema_version')!='qgv-555-input/1':raise ValueError('INPUT_SCHEMA')
        identity(s);date.fromisoformat(s['evaluation_day']);timestamp(s['input_cutoff'])
    for k in ('evaluation_day','input_cutoff','classification_version'):
        if e[k]!=ref[k]:raise ValueError('INPUT_CONTEXT:'+k)
    for s in (e,ref):
        ctx=s.get('classification_context') or {};contexts=ctx.get('source_contexts') or [ctx]
        if not contexts or any(x.get('dictionary_version')!=c['classification_dictionary_version'] or not x.get('mapping_version') or not x.get('classification_hash') for x in contexts):
            raise ValueError('CLASSIFICATION_CONTEXT_REQUIRED')
    cats=catalog();points={};ref_rows={}
    for original in sorted(ref['rows'],key=lambda x:x['company_id']):
        r=financial_peer_context(c,calculation_row(c,original),ref)
        if not r.get('issuer_id') or (r.get('accounting_template')!='GENERAL' and not _financial_enabled(c,r)):continue
        if r['issuer_id'] in points:
            if r.get('metrics')!=ref_rows[r['issuer_id']].get('metrics'):raise ValueError('ISSUER_POINT_CONFLICT')
            continue
        points[r['issuer_id']]={m:_usable(r,m,ref,share_policy=c.get('historical_share_policy'),share_evidence_scope=c.get('share_evidence_scope'),financial_policy=c.get('financial_temporary_policy'))[0] for m in cats};ref_rows[r['issuer_id']]=r
    pools={('all',):_Pool(points)}
    for keyfun in (lambda r:('industry',r.get('industry_group')),lambda r:('sector',r.get('sector_id'),r.get('accounting_template'))):
        groups=defaultdict(dict)
        for issuer,r in ref_rows.items():groups[keyfun(r)][issuer]=points[issuer]
        pools.update({k:_Pool(v) for k,v in groups.items()})
    out=[]
    for original in sorted(e['rows'],key=lambda x:x['company_id']):
        r=financial_peer_context(c,calculation_row(c,original),e)
        role_config=deepcopy(c['roles'])
        financial=_financial_enabled(c,r)
        if financial:role_config=deepcopy(c['financial_roles'])
        elif c['candidate']=='S1-555':role_config.update(c.get('scoped_role_overrides',{}).get(str(r.get('sector_id'))+'|'+str(r.get('accounting_template')),{}))
        supported,unsupported_reason=_row_support(c,r)
        raw={m:_usable(r,m,e,share_policy=c.get('historical_share_policy'),share_evidence_scope=c.get('share_evidence_scope'),financial_policy=c.get('financial_temporary_policy')) for m in cats};roles={};metric_scores={}
        for role,spec in role_config.items():
            vals=[];items=[]
            for name,mw in spec['metrics'].items():
                m=ALIASES.get(name,name);requested_metric=m;value,reason=raw[m];score=None;n=0;basis=None
                if (c['version']!='0.1.0' and role=='g_growth_efficiency' and
                    m=='incremental_roic_3y' and value is None and
                    'sector::roa_improvement_3y' not in {ALIASES.get(k,k) for k in spec['metrics']}):
                    m='sector::roa_improvement_3y';value,reason=raw[m]
                if supported and value is not None and mw>0:
                    if m in ('own_history','central::own_history'):
                        if 0<=value<=100:score=value;basis='OWN_HISTORY'
                    else:
                        if c['candidate']=='S1-555':keys=[('sector',r.get('sector_id'),r.get('accounting_template'))]
                        elif spec['axis']=='Q' or role=='v_vs_industry':keys=[('industry',r.get('industry_group')),('all',)]
                        else:keys=[('all',)]
                        for key in keys:
                            p=pools.get(key,_Pool({}));less,equal,n=p.rank(m,cats[m]['direction'],value,r['issuer_id'])
                            basis='|'.join(str(x) for x in key)
                            if n>=c['minimum']:
                                score=percentile(less,equal,n);break
                        if score is None:reason='PEER_SAMPLE_SMALL'
                elif not supported:reason=unsupported_reason
                elif mw==0:reason='DISABLED_IN_SETTING'
                items.append(dict(metric=m,raw=value,raw_status=raw[m][1],score=score,reason=None if score is not None else reason,
                                  reference_n=n,reference_scope=basis,weight=mw))
                if c['version']!='0.1.0':
                    items[-1].update(requested_metric=requested_metric,
                        selection_reason='PRIMARY_RAW_UNAVAILABLE_ROA_FALLBACK' if m!=requested_metric else 'PRIMARY',
                        primary_raw_status=raw[requested_metric][1],
                        display_flags=['SUBSTITUTE_METRIC'] if m!=requested_metric and score is not None else [])
                    if m!=requested_metric:items[-1]['substitute_for']=requested_metric
                    if financial:
                        proof=(r.get('metric_evidence') or {}).get(m) or {}
                        items[-1]['financial_raw_evidence']=dict(source_metric=cats[m].get('source_metric'),
                            formula=cats[m]['formula'],period=cats[m]['period'],attribution=cats[m].get('attribution'),
                            source_refs=deepcopy(proof.get('source_refs',[])),
                            source_available_at=proof.get('source_available_at'),retrieved_at=proof.get('retrieved_at'),
                            reviewed_at=proof.get('reviewed_at'),common_attribution_confirmed=False,
                            temporary_status='TEMPORARY_OFFICIAL_FINANCIAL')
                    if c['version']=='0.3.0' and m in SHARE_METRICS:
                        proof=(r.get('metric_evidence') or {}).get(m) or {}
                        items[-1]['share_validation']=dict(
                            final_eligibility=proof.get('share_eligibility_stage','UNCONFIRMED'),
                            review_version=proof.get('two_stage_review_version'),
                            denominator_definition=proof.get('denominator_definition'),
                            stages=deepcopy(proof.get('validation_stages')),
                            diagnostic_raw=(r.get('metrics',{}).get(m) if
                                type(r.get('metrics',{}).get(m)) in (int,float) and
                                math.isfinite(r['metrics'][m]) else None),
                            source_refs=deepcopy(proof.get('source_refs',[])),
                            reviewed_at=proof.get('reviewed_at'),retrieved_at=proof.get('retrieved_at'))
                    if c['version'] in ('0.4.0','0.5.0') and (m in SHARE_METRICS or m.startswith('financial::') and cats[m].get('historical_share_evidence_required')):
                        proof=(r.get('metric_evidence') or {}).get(m) or {}
                        items[-1]['share_validation']=dict(
                            review_version=proof.get('official_share_reuse_version'),
                            adoption_basis=proof.get('adoption_basis'),strict_verified=False,
                            requires_assumption=proof.get('requires_assumption'),
                            allowed_assumptions=deepcopy(proof.get('allowed_assumptions',[])),
                            evidence_only_eligible=proof.get('evidence_only_eligible'),
                            denominator_definition=proof.get('denominator_definition'),
                            formula_variant=proof.get('formula_variant'),formula_source=proof.get('formula_source'),
                            periods=deepcopy(proof.get('periods',[])),
                            additional_verification_required=proof.get('additional_verification_required',True),
                            additional_verification=deepcopy(proof.get('additional_verification',[])),
                            diagnostic_raw=r.get('metrics',{}).get(m),source_reason=proof.get('reason'),
                            source_refs=deepcopy(proof.get('source_refs',[])),
                            reviewed_at=proof.get('reviewed_at'),retrieved_at=proof.get('retrieved_at'),
                            coverage_scope=c['share_evidence_scope'],
                            verifies_valuation_security=False)
                if score is not None:vals.append((score,mw))
                metric_scores[role+'|'+m]=items[-1]
            score=sum(x*w for x,w in vals)/sum(w for _,w in vals) if vals else None
            roles[role]=dict(score=score,metrics=items,selected=spec['weight']>0,
                             partial=len(vals)<sum(w>0 for w in spec['metrics'].values()) or bool(financial and not spec['metrics']))
            if financial:roles[role].update(temporary_status=spec['temporary_status'],
                definition_status=spec['definition_status'],null_reason=spec['null_reason'])
        weights=c['axis_weights'] if c['candidate']=='U1-555' else c.get('sector_axis_overrides',{}).get(r.get('sector_id'),dict(zip('QGV',SECTORS.get(r.get('sector_id'),(34,33,33)))))
        scores={k:v['score'] for k,v in roles.items()}
        axes={a:axis_score(scores,a,{role:spec['weight'] for role,spec in role_config.items() if spec['axis']==a}) for a in 'QGV'}
        gate=_gate(r,e);valid=[a for a in 'QGV' if axes[a]['score'] is not None]
        included=[a for a in valid if not (a=='V' and gate=='VALUE_EXCLUDED')]
        enough=sum(weights[a] for a in valid)>=sum(weights.values())*.5
        total=sum(weights[a]*axes[a]['score'] for a in included)/sum(weights[a] for a in included) if included and enough and gate!='UNKNOWN' else None
        lineage=[];families=defaultdict(lambda:dict(nominal=0.,effective=0.))
        for role,spec in role_config.items():
            a=spec['axis'];role_total=sum(v['weight'] for v in role_config.values() if v['axis']==a)
            role_used=sum(v['weight'] for k,v in role_config.items() if v['axis']==a and scores[k] is not None)
            metrics=roles[role]['metrics'];metric_total=sum(x['weight'] for x in metrics)
            metric_used=sum(x['weight'] for x in metrics if x['score'] is not None)
            for item in metrics:
                nom=Fraction(str(weights[a]))/Fraction(str(sum(weights.values())))*Fraction(str(spec['weight']))/Fraction(str(role_total))*Fraction(str(item['weight']))/Fraction(str(metric_total))
                eff=0.
                if total is not None and a in included and scores[role] is not None and item['score'] is not None and metric_used:
                    eff=weights[a]/sum(weights[x] for x in included)*spec['weight']/role_used*item['weight']/metric_used
                family=cats[item['metric']]['input_family']
                lineage.append(dict(axis=a,role=role,metric=item['metric'],input_family=family,nominal=float(nom),nominal_ratio=[nom.numerator,nom.denominator],effective=eff))
                families[family]['nominal']+=float(nom);families[family]['effective']+=eff
        reported_weights=weights
        if c['candidate']=='S1-555' and r.get('sector_id') not in SECTORS:
            lineage=[];families={};reported_weights=None
        out.append(dict(company_id=r['company_id'],issuer_id=r['issuer_id'],security_id=r.get('security_id'),
            sector_id=r.get('sector_id'),accounting_template=r.get('accounting_template'),roles=roles,axes=axes,
            active_roles={a:sum(v['weight']>0 for v in role_config.values() if v['axis']==a) for a in 'QGV'},
            fifteen_roles_complete=all(roles[k]['score'] is not None and role_config[k]['weight']>0 for k in SPECS),
            gate_status=gate,gate_scope='OFFICIAL_INPUT_DECISION_INDEPENDENT_OF_MODEL_APPLICABILITY',
            nominal_axis_weights=reported_weights,total=total,partial_total=total is not None and len(valid)<3,
            ranking_scope='COMMON' if c['candidate']=='U1-555' else 'SECTOR|'+str(r.get('sector_id'))+'|'+str(r.get('accounting_template')),
            status='READY' if supported else unsupported_reason,lineage=lineage,
            input_family_contributions=dict(families)))
        if c['version']!='0.1.0':
            temp=original.get('temporary_classification') or {}
            flags=[]
            if (temp.get('status')=='TEMPORARY_OFFICIAL_PROFILE' or
                original.get('accounting_template') is None and original.get('owner_source_context')):
                flags.append('CLASSIFICATION_PROVISIONAL')
            if temp.get('status')=='TEMPORARY_REIT_GENERAL':flags.append('REIT_PROVISIONAL')
            if original.get('financial_reference'):flags.append('TEMPORARY_OFFICIAL_PROXY')
            if any('SUBSTITUTE_METRIC' in m.get('display_flags',[]) for v in roles.values() for m in v['metrics']):
                flags.append('SUBSTITUTE_METRIC')
            out[-1].update(original_accounting_template=original.get('accounting_template'),
                original_sector_id=original.get('sector_id'),
                calculation_accounting_template=r.get('accounting_template'),
                temporary_classification=deepcopy(original.get('temporary_classification')),
                financial_reference=deepcopy(original.get('financial_reference')),
                growth_efficiency_calculation=[dict(metric=x['metric'],requested_metric=x['requested_metric'],
                    selection_reason=x['selection_reason'],score_status=x['reason'])
                    for x in roles['g_growth_efficiency']['metrics']],
                valuation_share_basis='WEIGHTED_AVERAGE_DILUTED_NOT_ACTUAL_CLASS_SHARES')
            out[-1].update(display_flags=flags,display_label=temp.get('label'),
                source_model=(original.get('financial_reference') or {}).get('model_id'))
            if financial:
                from .qgv_555_financial_temporary import contribution_metadata,STATUS
                flags=[f for f in flags if f!='TEMPORARY_OFFICIAL_PROXY']+[STATUS]
                out[-1].update(display_flags=flags,financial_calculation_profile='FINANCIAL',
                    display_label='금융 임시(공식 FINANCIAL 원지표)',
                    source_reference_display_label=temp.get('label'),
                    peer_accounting_template=r.get('accounting_template'),temporary_model_status=STATUS,
                    financial_reference_only=False,financial_definition_complete=False,
                    defined_roles={a:sum(bool(v['metrics']) for v in role_config.values() if v['axis']==a) for a in 'QGV'},
                    financial_temporary_contributions=(contribution_metadata(roles,axis_weights=weights,
                        included_axes=included,total_available=total is not None) if reported_weights is not None else None))
    # Do not invent a new decile rule: the reusable stored order adapter below
    # uses the existing dual rule verbatim via its function (including tie splits).
    _rank(out)
    b=_bindings(c,e,ref)
    result=dict(schema_version='qgv-555-result/1',model_id=c['model_id'],configuration=deepcopy(c),
        evaluation=b['evaluation'],reference=b['reference'],bindings=b,rows=out,
        calculated_at=calculated_at or datetime.now(timezone.utc).isoformat(),
        duplicate_control=dict(applied='DISCLOSE_ONLY',A='PENDING_FIXED_SHARED_BUDGET',B='SEPARATE_USER_CONFIGURATION'),
        performance='NOT_MEASURED',official=False,whole_market_denominator=None)
    def count(predicate):return len({r['issuer_id'] for r in out if r.get('issuer_id') and predicate(r)})
    result['coverage']=dict(denominator=b['evaluation']['issuers'],target=math.ceil(.95*b['evaluation']['issuers']),
        axes={a:count(lambda r:r['axes'][a]['score'] is not None) for a in 'QGV'},
        roles={k:count(lambda r:r['roles'][k]['score'] is not None) for k in SPECS},
        all15=count(lambda r:r['fifteen_roles_complete']),joint=count(lambda r:all(r['axes'][a]['score'] is not None for a in 'QGV')),
        gate_known=count(lambda r:r['gate_status']!='UNKNOWN'),gate_pass=count(lambda r:r['gate_status']=='PASS'),
        total=count(lambda r:r['total'] is not None),eligible_total=count(lambda r:r['total'] is not None and not r['partial_total']))
    if c['version'] in ('0.4.0','0.5.0'):result['coverage'].update(share_evidence_scope=c['share_evidence_scope'],
        strict_share_verification=False,official_raw_reused_not_official_score=True)
    if c['version']=='0.5.0':result['coverage'].update(
        financial_temporary_issuers=count(lambda r:r.get('temporary_model_status')=='TEMPORARY_OFFICIAL_FINANCIAL'),
        financial_temporary_code_rows=sum(r.get('temporary_model_status')=='TEMPORARY_OFFICIAL_FINANCIAL' for r in out),
        financial_temporary_axes={a:count(lambda r:r.get('temporary_model_status')=='TEMPORARY_OFFICIAL_FINANCIAL' and r['axes'][a]['score'] is not None) for a in 'QGV'},
        financial_dedicated_definition_complete=False)
    result['coverage']['role_stages']={role:dict(
        raw_any=count(lambda r:any(x['raw'] is not None for x in r['roles'][role]['metrics'])),
        raw_all=count(lambda r:bool(r['roles'][role]['metrics']) and all(x['raw'] is not None for x in r['roles'][role]['metrics'])),
        score=count(lambda r:r['roles'][role]['score'] is not None)) for role in SPECS}
    if c['version']!='0.1.0':
        result['coverage'].update(axis_target=math.ceil(.9*b['evaluation']['issuers']),
            target_criteria='ALL_THREE_AXES_EACH_ROLE_WEIGHT_AT_LEAST_50_AND_ELIGIBLE_TOTAL',
            all15_reference_only=True,
            growth_efficiency_choices={m:len({r['issuer_id'] for r in out
                if r['roles']['g_growth_efficiency']['metrics'][0]['metric']==m})
                for m in {r['roles']['g_growth_efficiency']['metrics'][0]['metric'] for r in out}},
            growth_efficiency_scored={m:len({r['issuer_id'] for r in out
                if r['roles']['g_growth_efficiency']['metrics'][0]['metric']==m
                and r['roles']['g_growth_efficiency']['metrics'][0]['score'] is not None})
                for m in {r['roles']['g_growth_efficiency']['metrics'][0]['metric'] for r in out}})
    result['result_hash']=digest(result)
    return result


def _rank(rows):
    from .dual_qgv import _rank_factors
    from .sector_qgv import rank_result_rows
    from .sector_qgv_registry import CATALOG
    # Adapter maps each role into a temporary existing factor slot, calls the
    # established rank/decile kernel, then copies metadata back. No formulas copied.
    slot=next(iter(CATALOG))
    for role in SPECS:
        bridge=[dict(company_id=r['company_id'],ranking_scope=r['ranking_scope'],
            factors={v:dict(score=r['roles'][role]['score'] if v==slot else None) for v in CATALOG}) for r in rows]
        _rank_factors(bridge)
        for r,x in zip(rows,bridge):r['roles'][role].update({k:x['factors'][slot][k] for k in ('rank','rank_n','decile','decile_status')})
    groups=defaultdict(list)
    for r in rows:groups[r['ranking_scope']].append(r);r.update(rank=None,rank_n=0)
    for group in groups.values():
        ranked=rank_result_rows([r for r in group if r['total'] is not None and not r['partial_total']])
        for i,r in enumerate(ranked):
            next(x for x in group if x['company_id']==r['company_id']).update(rank=i+1,rank_n=len(ranked))


def validate_binding(result,*,expected_evaluation,expected_reference):
    if result['evaluation']!=expected_evaluation:raise ValueError('EVALUATION_ANCHOR_MISMATCH')
    if result['reference']!=expected_reference:raise ValueError('REFERENCE_ANCHOR_MISMATCH')
    if result['result_hash']!=digest({k:v for k,v in result.items() if k!='result_hash'}):raise ValueError('RESULT_HASH')
    return True


def replay(saved,e,ref):
    if identity(e)!=saved['evaluation'] or identity(ref)!=saved['reference']:raise ValueError('SAVED_INPUT_MISMATCH')
    if _bindings(saved['configuration'],e,ref)['code_hash']!=saved['bindings']['code_hash']:raise ValueError('SAVED_ENGINE_VERSION_REQUIRED')
    return run(saved['configuration'],e,ref,calculated_at=saved['calculated_at'])


def fixture(n=21):
    rows=[];cats=catalog();ts='2026-11-04T22:00:00Z'
    for i in range(n):
        rows.append(dict(company_id=f'SYN:{i:03}',issuer_id=f'synthetic-issuer-{i:03}',security_id=f'synthetic-security-{i:03}',
            sector_id='INFORMATION_TECHNOLOGY',accounting_template='GENERAL',industry_group='synthetic-industry',
            metrics={m:(50 if m=='own_history' else i+1) for m in cats},
            metric_evidence={m:dict(status='VERIFIED',variant=v['variant'],source_refs=['SYNTHETIC_ONLY'],available_at=ts,
                historical_share_basis='VERIFIED',valuation_day='2026-11-04',security_and_actions='VERIFIED',
                share_eligibility_stage='FINAL_ELIGIBLE',two_stage_review_version='held-555-share-eligibility/2',
                denominator_definition=SHARE_DENOMINATOR if m in SHARE_METRICS else None,
                validation_stages=dict(stage1_status='CROSS_FILING_CONSISTENT',stage2_status='FINAL_ELIGIBLE',
                    corporate_action_status='DOCUMENTED_COMMON_BASIS',adjustment_applied=False) if m in SHARE_METRICS else None,
                share_basis='WEIGHTED_AVERAGE_DILUTED' if m.startswith('central::') else None) for m,v in cats.items()},
            gate=dict(percentile=80,calc_version='qgv2-calc/2026-10-23.1',evaluation_day='2026-11-04',source_refs=['SYNTHETIC_OFFICIAL_GATE'])))
    e=dict(schema_version='qgv-555-input/1',population_id='synthetic-evaluation',population_version='1',
        evaluation_day='2026-11-04',input_cutoff=ts,classification_version='synthetic-adapter-map/1',
        classification_context=dict(dictionary_version='common-industry-dictionary/2',mapping_version='common-classification-map/2',classification_hash='a'*64),
        members=[r['company_id'] for r in rows],rows=rows,source_anchors=['SYNTHETIC'])
    ref=deepcopy(e);ref['population_id']='synthetic-reference'
    return e,ref


def accounting_recipes(*, version='0.1.0'):
    """Do not activate five names as five defined financial formulas."""
    out=[]
    known={'q_profitability':['roa_ttm','roe_common_ttm'],
           'q_financial_safety':['common_equity_assets'],
           'g_revenue_growth':['revenue_cagr_3y'],
           'g_per_share_growth':['common_bps_cagr_3y','eps_diluted_cagr_3y'],
           'v_earnings_yield':['ep_ttm_diluted'],'v_vs_industry':['common_bp']}
    for t in TEMPLATES:
        out.append(dict(accounting_template=t,state='DEFINED_GENERAL' if t=='GENERAL' else 'PREPARING',
            roles={role:dict(weight=WEIGHTS[role[0].upper()][role],
                variants=[m for m,d in SPECS[role]] if t=='GENERAL' else known.get(role,[]),
                state='DEFINED' if t=='GENERAL' else 'PARTIAL_DEFINITION' if role in known else 'DEFINITION_REQUIRED',
                limitation=None if t=='GENERAL' else 'Independent attribution, period, peer and five-role recipe review required; no GENERAL fallback') for role in SPECS}))
    if version in ('0.2.0','0.3.0','0.4.0','0.5.0'):
        cfg=configuration('S1-555',version=version)
        for item in out:
            if item['accounting_template']=='EQUITY_REIT':
                item.update(state='TEMPORARY_GENERAL',label='REIT 임시(일반기업 식)',
                    calculation_accounting_template='GENERAL',permanent_ffo_affo_recipe='PREPARING')
                for role,node in item['roles'].items():
                    node.update(variants=list(cfg['roles'][role]['metrics']),state='TEMPORARY_GENERAL',
                        limitation='Owner-approved interim GENERAL calculation; not a completed FFO/AFFO recipe')
            elif item['accounting_template']=='GENERAL':
                for role,node in item['roles'].items():node['variants']=list(cfg['roles'][role]['metrics'])
            else:item['financial_reference_policy']='ORIGINAL_OFFICIAL_MODEL_ONLY_NOT_555'
    elif version!='0.1.0':raise ValueError('UNKNOWN_MODEL_VERSION')
    return out
