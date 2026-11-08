"""Classification adapter, keeping the established QGV engine/config/gate intact."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import timedelta

from ..sector_qgv import day, digest
from ..sector_qgv_registry import MAPPING
from investment_system.qgv.qgv_v2 import finite, percentile, GATE_PERCENTILE

GATE_COMPARISON = 'CC-GATE-20261107-C1'


def _context(snapshot, view):
    if view.get('schema_version') != 'common-classification-view/1':
        raise ValueError('PROJECTION_VIEW_VERSION_INVALID')
    for key in ('valuation_date','universe_id','universe_version'):
        if snapshot[key] != view[key]: raise ValueError('PROJECTION_CONTEXT_MISMATCH:'+key)
    if (len(snapshot['members']) != len(set(snapshot['members'])) or
        set(snapshot['members']) != set(view['members']) or len(view['members']) != len(set(view['members'])) or
        len(view['rows']) != len(view['members']) or {r['company_id'] for r in view['rows']} != set(view['members'])):
        raise ValueError('PROJECTION_CONTEXT_MISMATCH:members')
    return {r['company_id']:r for r in view['rows']}


def project_qgv(snapshot, view):
    """Raw observations, financial cutoff, representative evidence and gate are immutable.

    Common knowledge_as_of records the review time separately from the financial
    as_of. An evaluation-only mapping becomes a one-day engine interval solely
    for this replay; it does not assert an effective historical start date.
    """
    by_code = _context(snapshot,view)
    result=deepcopy(snapshot)
    result['input_version']='common-classification-qgv/1'
    result['snapshot_id']=snapshot['snapshot_id']+':common:'+view['classification_hash'][:16]
    result['classification_context']={key:view[key] for key in (
        'schema_version','classification_hash','dictionary_version','mapping_version','knowledge_as_of')}
    for row in result['rows']:
        c=by_code[row['company_id']]
        if c.get('issuer_id') is not None and c['issuer_id'] != row.get('issuer_id'):
            raise ValueError('PROJECTION_ISSUER_MISMATCH')
        row['sector_id']=c['sector']['id'] if c['sector']['status']=='CONFIRMED' else None
        row['accounting_template']=c['accounting']['id'] if c['accounting']['status']=='CONFIRMED' else None
        # A reviewed company exception must not become an unreviewed SIC again
        # when this projection is reused as the next classification input.
        row['classification_record_id']=c['record_id']
        row['classification_component_reasons']={k:deepcopy(c[k]['reasons']) for k in ('sector','accounting','industry')}
        row['reasons']=deepcopy(c['sector']['reasons'] if row['sector_id'] is None else
                               c['accounting']['reasons'] if row['accounting_template'] is None else [])
        row['mapping']=None
        if row['sector_id'] and row['accounting_template']:
            a=c['applicability']
            start,end=(a['valid_from'],a.get('valid_to')) if a['kind']=='INTERVAL' else (
                view['valuation_date'],(day(view['valuation_date'])+timedelta(days=1)).isoformat())
            row['mapping']={'version':MAPPING,'valid_from':start,'valid_to':end,
                'effective_date_basis':a['kind'],'evidence_refs':sorted(set(c['sector']['evidence_refs']+c['accounting']['evidence_refs'])),
                'common_record_id':c['record_id'],'common_classification_hash':view['classification_hash'],
                'common_dictionary_version':view['dictionary_version'],'common_mapping_version':view['mapping_version'],
                'knowledge_as_of':view['knowledge_as_of'],'classification_rule_version':c['rule_version']}
    return result


def gate_comparison(snapshot, view):
    """Pre-registered alternative, NOT an input to aggregate() or official output.

    Existing official source Q (calc 23.1) -> common (sector, accounting) peer
    percentile. Minimum 20 unique scoring issuers, no fallback, threshold <=30.
    No sector-model Q score, prices, weight changes or sector-return model here.
    """
    by_code=_context(snapshot,view)
    rows={r['company_id']:r for r in snapshot['rows']}
    issuers=defaultdict(list)
    for key,row in rows.items():
        if row.get('issuer_id'): issuers[row['issuer_id']].append(key)
    representatives=set()
    for codes in issuers.values():
        candidates=codes if len(codes)==1 else [k for k in codes if rows[k].get('scoring_representative') is True and rows[k].get('representative_evidence')]
        if len(candidates)==1: representatives.add(candidates[0])
    values={}; groups={}; pools=defaultdict(list); reasons={}; baseline_known={}
    for key in snapshot['members']:
        row=rows.get(key,{}); c=by_code[key]; gate=row.get('gate') or {}
        group=(c['sector']['id'],c['accounting']['id']); groups[key]=group
        reason=None
        baseline_known[key]=(gate.get('calc_version')=='qgv2-calc/2026-10-23.1' and gate.get('as_of')==snapshot['valuation_date']
               and bool(gate.get('provenance')) and finite(gate.get('q_industry_percentile')) and 0<=gate['q_industry_percentile']<=100)
        valid=baseline_known[key] and finite(gate.get('source_q_score')) and 0<=gate['source_q_score']<=100
        if not valid: reason='OFFICIAL_Q_INPUT_UNVERIFIED'
        elif c['sector']['status']!='CONFIRMED' or c['accounting']['status']!='CONFIRMED': reason='CLASSIFICATION_UNCONFIRMED'
        elif key not in representatives: reason='ISSUER_REPRESENTATIVE_UNRESOLVED'
        if reason is None:
            values[key]=gate['source_q_score']; pools[group].append(values[key])
        reasons[key]=reason
    out=[]
    for key in sorted(snapshot['members']):
        gate=rows.get(key,{}).get('gate') or {}; group=groups[key]; pool=pools[group]
        reason=reasons[key]
        if reason is None and len(pool)<20: reason='PEER_SAMPLE_SMALL'
        score=percentile(values[key],pool) if reason is None else None
        old=gate.get('q_industry_percentile') if baseline_known[key] else None
        status=lambda value:'UNKNOWN' if value is None else 'VALUE_EXCLUDED' if value<=GATE_PERCENTILE else 'PASS'
        out.append({'company_id':key,'group':list(group),'source_q_score':values.get(key),
                    'baseline_percentile':old,'baseline_status':status(old),
                    'candidate_percentile':score,'candidate_status':status(score),
                    'valid_n':len(pool),'reason':reason})
    return {'schema_version':'common-classification-gate-comparison/1','comparison_id':GATE_COMPARISON,
            'adoption_state':'DIAGNOSTIC_ONLY_NOT_APPLIED','source_q_version':'qgv2-calc/2026-10-23.1',
            'peer_basis':['common_sector','accounting_template'],'minimum_valid_n':20,'fallback':None,
            'cutoff':GATE_PERCENTILE,'classification_hash':view['classification_hash'],
            'denominator':len(snapshot['members']),'rows':out,
            'transitions':dict(Counter(r['baseline_status']+'->'+r['candidate_status'] for r in out)),
            'reasons':dict(Counter(r['reason'] for r in out if r['reason'])),
            'performance':None,'performance_reason':'NOT_MEASURED_NOT_ADOPTED'}
