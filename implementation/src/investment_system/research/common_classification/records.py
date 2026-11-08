"""Dated, versioned classifications. Import/review time is not source release time."""
from copy import deepcopy
from collections import Counter
from datetime import timezone
import re

from ..sector_qgv import digest, day, timestamp
from ..sector_qgv_registry import SECTORS, TEMPLATES, MAPPING
from .catalog import (dictionary, industry_for_sic, VERSION, MAPPING_VERSION, PARENTS,
                      POLICY_DICTIONARY_VERSION, POLICY_MAPPING_VERSION, BOUNDARY_POLICY_VERSION, BOUNDARY_SOURCE)

SCHEMA = 'common-classification/1'


def unknown(reason):
    return {'id':None, 'status':'UNKNOWN', 'reasons':[reason], 'evidence_refs':[]}


def confirmed(value, refs):
    return {'id':value, 'status':'CONFIRMED', 'reasons':[], 'evidence_refs':list(refs)}


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _time(value):
    if value is not None:
        if not isinstance(value, str): raise ValueError('INVALID_TIME')
        if len(value) == 10: day(value)
        else: timestamp(value)


def _available(value, cutoff):
    if value is None: return None
    if len(value) == 10:
        d, end = day(value), timestamp(cutoff).astimezone(timezone.utc).date()
        return True if d < end else False if d > end else None
    return timestamp(value) <= timestamp(cutoff)


def _component(value, allowed):
    if not isinstance(value, dict) or value.get('status') not in ('CONFIRMED','UNKNOWN','CONFLICT'):
        raise ValueError('COMPONENT_STATUS_INVALID')
    if not isinstance(value.get('reasons'), list) or not isinstance(value.get('evidence_refs'), list):
        raise ValueError('COMPONENT_EVIDENCE_INVALID')
    if any(not _text(x) for x in value['reasons']+value['evidence_refs']):
        raise ValueError('COMPONENT_EVIDENCE_INVALID')
    if value['status'] == 'CONFIRMED':
        if value.get('id') not in allowed or not value['evidence_refs'] or value['reasons']:
            raise ValueError('CONFIRMED_COMPONENT_INVALID')
    elif value.get('id') is not None or not value['reasons']:
        raise ValueError('UNKNOWN_COMPONENT_REQUIRES_NULL_AND_REASON')


def validate(store):
    versions={VERSION:MAPPING_VERSION,POLICY_DICTIONARY_VERSION:POLICY_MAPPING_VERSION}
    if (store.get('schema_version') != SCHEMA or store.get('dictionary_version') not in versions or
        store.get('mapping_version') != versions[store['dictionary_version']] or store.get('data_kind') not in ('SYNTHETIC','RETAINED_INPUT')):
        raise ValueError('CLASSIFICATION_VERSION_INVALID')
    dictionary(store['dictionary_version'])  # Detect drift in referenced source definitions.
    if store['dictionary_version']==POLICY_DICTIONARY_VERSION:
        p=store.get('boundary_policy',{})
        if (p.get('version')!=BOUNDARY_POLICY_VERSION or p.get('approved_date')!='2026-11-08' or
            p.get('source')!=BOUNDARY_SOURCE or not p.get('recorded_at') or
            timestamp(p['recorded_at']).date()<day(p['approved_date'])):
            raise ValueError('CLASSIFICATION_POLICY_INVALID')
    members = store['members']
    if not isinstance(members, list) or any(not _text(x) for x in members) or len(set(members)) != len(members):
        raise ValueError('CLASSIFICATION_MEMBERS_INVALID')
    sources = {}
    for source in store['sources']:
        key = source.get('source_id')
        if (not _text(key) or key in sources or not _text(source.get('url')) or
            not _text(source.get('locator')) or not re.fullmatch('[0-9a-f]{64}', source.get('sha256',''))):
            raise ValueError('CLASSIFICATION_SOURCE_INVALID')
        for field in ('published_at','published_date','acquired_at'): _time(source.get(field))
        if (source.get('published_at') and len(source['published_at'])==10 or
            source.get('published_date') and len(source['published_date'])!=10):
            raise ValueError('SOURCE_PUBLICATION_PRECISION_INVALID')
        if source.get('published_at') and source.get('published_date') and source['published_at'][:10] != source['published_date']:
            raise ValueError('SOURCE_PUBLICATION_DATE_CONFLICT')
        sources[key] = source
    records = {}
    for r in store['records']:
        key = r.get('record_id')
        if not _text(key) or key in records or r.get('company_id') not in members or not _text(r.get('issuer_id')):
            raise ValueError('CLASSIFICATION_RECORD_ID_INVALID')
        _time(r.get('recorded_at'))
        if not _text(r.get('rule_version')) or r.get('basis') not in ('RESEARCH_CORRESPONDENCE','OFFICIAL_CLASSIFICATION'):
            raise ValueError('CLASSIFICATION_RULE_REQUIRED')
        if not isinstance(r.get('source_refs'), list) or any(x not in sources for x in r['source_refs']):
            raise ValueError('CLASSIFICATION_SOURCE_REFERENCE_INVALID')
        a = r['applicability']
        if a['kind'] == 'EVALUATION_ONLY':
            day(a['evaluation_date'])
            if a.get('valid_from') is not None or a.get('valid_to') is not None:
                raise ValueError('EVALUATION_ONLY_IS_NOT_EFFECTIVE_INTERVAL')
        elif a['kind'] == 'INTERVAL':
            for f in ('valid_from','valid_to'):
                if a.get(f) is not None: day(a[f])
            if a.get('valid_from') and a.get('valid_to') and a['valid_from'] >= a['valid_to']:
                raise ValueError('CLASSIFICATION_INTERVAL_INVALID')
        else: raise ValueError('CLASSIFICATION_APPLICABILITY_INVALID')
        for field, allowed in (('sector',SECTORS),('industry',PARENTS),('accounting',TEMPLATES)):
            _component(r[field], allowed)
        if r['industry']['status'] == 'CONFIRMED' and (r['sector']['status'] != 'CONFIRMED' or PARENTS[r['industry']['id']] != r['sector']['id']):
            raise ValueError('INDUSTRY_PARENT_CONFLICT')
        if any(r[f]['status'] == 'CONFIRMED' for f in ('sector','industry','accounting')) and not r['source_refs']:
            raise ValueError('CONFIRMED_SOURCE_MISSING')
        if not isinstance(r.get('tags'), dict): raise ValueError('CLASSIFICATION_TAGS_INVALID')
        records[key] = r
    for r in records.values():
        seen = {r['record_id']}; previous = r.get('supersedes')
        while previous:
            if previous not in records or previous in seen or records[previous]['company_id'] != r['company_id']:
                raise ValueError('REVISION_REFERENCE_INVALID')
            seen.add(previous); previous = records[previous].get('supersedes')
    return store


def _eligibility(r, sources, valuation_date, knowledge_as_of):
    a = r['applicability']
    if a['kind'] == 'EVALUATION_ONLY':
        if a['evaluation_date'] != valuation_date: return 'EVALUATION_ONLY_DATE_MISMATCH'
    else:
        if a.get('valid_from') is None: return 'EFFECTIVE_START_UNKNOWN'
        if not a['valid_from'] <= valuation_date or a.get('valid_to') and valuation_date >= a['valid_to']:
            return 'OUTSIDE_CLASSIFICATION_INTERVAL'
    available = _available(r.get('recorded_at'), knowledge_as_of)
    if available is not True: return 'RECORD_NOT_AVAILABLE' if available is False else 'REVIEW_TIME_UNKNOWN'
    for key in r['source_refs']:
        s = sources[key]
        acquired = _available(s.get('acquired_at'), knowledge_as_of)
        if acquired is not True: return 'SOURCE_NOT_AVAILABLE' if acquired is False else 'SOURCE_ACQUISITION_UNKNOWN'
        publication = s.get('published_at') or s.get('published_date')
        if publication:
            known = _available(publication, knowledge_as_of)
            if known is not True: return 'SOURCE_NOT_AVAILABLE' if known is False else 'SOURCE_DATE_PRECISION_INSUFFICIENT'
    return None


def resolve(store, *, valuation_date, knowledge_as_of):
    validate(store); day(valuation_date); timestamp(knowledge_as_of)
    if store.get('boundary_policy') and timestamp(knowledge_as_of)<timestamp(store['boundary_policy']['recorded_at']):
        raise ValueError('POLICY_NOT_AVAILABLE')
    if day(valuation_date) > timestamp(knowledge_as_of).astimezone(timezone.utc).date(): raise ValueError('VALUATION_AFTER_KNOWLEDGE')
    sources = {s['source_id']:s for s in store['sources']}; rows = []
    for member in sorted(store['members']):
        candidates = sorted((r for r in store['records'] if r['company_id'] == member), key=lambda r:r['record_id'])
        eligible = [r for r in candidates if _eligibility(r,sources,valuation_date,knowledge_as_of) is None]
        superseded = set()
        by_id = {r['record_id']:r for r in candidates}
        for r in eligible:
            prior = r.get('supersedes')
            while prior:
                superseded.add(prior); prior = by_id[prior].get('supersedes')
        active = [r for r in eligible if r['record_id'] not in superseded]
        if len(active) == 1: row = deepcopy(active[0])
        else:
            reason = ('AMBIGUOUS_CLASSIFICATION' if len(active)>1 else
                      _eligibility(candidates[-1],sources,valuation_date,knowledge_as_of) if candidates else 'CLASSIFICATION_RECORD_MISSING')
            issuers = {r['issuer_id'] for r in candidates}
            row = {'company_id':member,'issuer_id':next(iter(issuers)) if len(issuers)==1 else None,
                   'record_id':None,'source_sic':None,'tags':{},'source_refs':[],
                   **{f:unknown(reason) for f in ('sector','industry','accounting')}}
        rows.append(row)
    # Two class codes of one issuer may not silently assert two primary sectors.
    by_issuer = {}
    for r in rows:
        if r['issuer_id']: by_issuer.setdefault(r['issuer_id'], []).append(r)
    for group in by_issuer.values():
        sectors = {r['sector']['id'] for r in group if r['sector']['status']=='CONFIRMED'}
        if len(sectors)>1:
            for r in group:
                r['sector']=unknown('ISSUER_PRIMARY_SECTOR_CONFLICT'); r['sector']['status']='CONFLICT'
                r['industry']=unknown('ISSUER_PRIMARY_SECTOR_CONFLICT')
        templates = {r['accounting']['id'] for r in group if r['accounting']['status']=='CONFIRMED'}
        if len(templates)>1:
            for r in group:
                r['accounting']=unknown('ISSUER_ACCOUNTING_CONFLICT'); r['accounting']['status']='CONFLICT'
    identity_fields = ('company_id','issuer_id','record_id','sector','industry','accounting','source_sic','source_refs','applicability','rule_version','recorded_at')
    selected_sources={ref for r in rows for ref in r['source_refs']}
    resolved_sources=[deepcopy(sources[key]) for key in sorted(selected_sources)]
    identity = {'rows':[{k:r[k] for k in identity_fields if k in r} for r in rows],
                'members':sorted(store['members']),'universe_id':store['universe_id'],
                'universe_version':store['universe_version'],'dictionary_version':store['dictionary_version'],
                'mapping_version':store['mapping_version'],'valuation_date':valuation_date,
                'knowledge_as_of':knowledge_as_of,'dictionary_hash':digest(dictionary(store['dictionary_version'])),
                'sources':resolved_sources}
    if store.get('boundary_policy'):identity['boundary_policy']=deepcopy(store['boundary_policy'])
    history={**store,'members':sorted(store['members']),
             'sources':sorted(store['sources'],key=lambda s:s['source_id']),
             'records':sorted(store['records'],key=lambda r:r['record_id'])}
    coverage = {'member_codes':len(rows),'unique_issuers':len(by_issuer),
                **{f+'_confirmed':sum(r[f]['status']=='CONFIRMED' for r in rows) for f in ('sector','industry','accounting')},
                'source_sic_available':sum(bool(r.get('source_sic')) for r in rows)}
    coverage['sector_confirmed_issuers']=len({r['issuer_id'] for r in rows if r['sector']['status']=='CONFIRMED'})
    return {'schema_version':'common-classification-view/1', 'data_kind':store['data_kind'],
            'valuation_date':valuation_date,'knowledge_as_of':knowledge_as_of,
            'universe_id':store['universe_id'],'universe_version':store['universe_version'],
            'dictionary_version':store['dictionary_version'],'mapping_version':store['mapping_version'],'members':sorted(store['members']),
            'rows':rows, 'sources':resolved_sources, 'classification_hash':digest(identity),
            'history_hash':digest(history),
            'dictionary_hash':digest(dictionary(store['dictionary_version'])),
            'display_hash':digest({'identity':identity,'rows':rows}), 'coverage':coverage,
            'review_scope':'RETAINED_EVALUATION_REVIEW_NOT_HISTORICAL_PIT_CERTIFICATION',
            'unresolved_reasons':dict(Counter(x for r in rows for x in r['sector']['reasons']))}


def from_sector_snapshot(snapshot, evidence_by_code, *, source_sha256, recorded_at, data_kind, dictionary_version=VERSION):
    """Import retained classifications without reclassifying financials or inventing dates."""
    timestamp(recorded_at)
    if snapshot['mapping_version'] != MAPPING: raise ValueError('RETAINED_MAPPING_VERSION_INVALID')
    sources = {}; records = []
    for r in snapshot['rows']:
        code = r['company_id']; e = evidence_by_code.get(code, {})
        official = deepcopy(r.get('official_classification')); m = r.get('mapping')
        if e:
            expected={'issuer_id':r['issuer_id'],'sic':(official or {}).get('code'),
                      'source_sha256':(official or {}).get('source_sha256')}
            for key,value in expected.items():
                if key in e:
                    actual=e[key]
                    if key=='sic' and value is not None and actual is not None:
                        actual,value=str(actual).zfill(4),str(value).zfill(4)
                    if actual!=value: raise ValueError('RETAINED_EVIDENCE_MISMATCH:'+key)
        source_hash = e.get('source_sha256') or (official or {}).get('source_sha256')
        refs = []
        if source_hash:
            key = 'source:'+source_hash; refs=[key]
            candidate = {'source_id':key,'sha256':source_hash,
                         'url':e.get('source_url') or official['source_url'],
                         'locator':e.get('member') or 'retained official_classification',
                         'archive_sha256':e.get('archive_sha256'),
                         'published_at':None,'published_date':None,
                         'publication_reason':'ORIGINAL_RELEASE_TIME_NOT_RETAINED',
                         'acquired_at':e.get('acquired_at') or (official or {}).get('observed_at'),
                         'availability_basis':'OBSERVED_BY_ACQUISITION_NOT_FIRST_PUBLICATION'}
            if key in sources and sources[key] != candidate: raise ValueError('SOURCE_METADATA_CONFLICT')
            sources[key]=candidate
        components=r.get('component_mappings',{})
        sm=components.get('sector') or m; am=components.get('accounting') or m
        for source in r.get('review_sources',[]):
            key=source['source_id']
            if key in sources and sources[key]!=source:raise ValueError('SOURCE_METADATA_CONFLICT')
            sources[key]=deepcopy(source);refs.append(key)
        sector = confirmed(r['sector_id'],sm['evidence_refs']) if sm else unknown((r.get('reasons') or ['SECTOR_UNCONFIRMED'])[0])
        accounting = confirmed(r['accounting_template'],am['evidence_refs']) if am else unknown('ACCOUNTING_TEMPLATE_UNCONFIRMED')
        sic = official.get('code') if official and official.get('system')=='SEC_SIC' else None
        industry = industry_for_sic(sic, sector['id'])
        if components.get('industry'):
            industry=confirmed(r['reviewed_industry_id'],components['industry']['evidence_refs'])
        records.append({'record_id':'retained:'+digest({'company_id':code,'snapshot':source_sha256})[:32],
                        'company_id':code,'issuer_id':r['issuer_id'], 'recorded_at':recorded_at,
                        'recorded_at_basis':'CURRENT_IMPORT_REVIEW_NOT_ORIGINAL_DECISION_TIME',
                        'original_reviewed_at':None,'supersedes':None,
                        'applicability':{'kind':'EVALUATION_ONLY','evaluation_date':snapshot['valuation_date'],
                                         'valid_from':None,'valid_to':None},
                        'sector':sector,'industry':industry,'accounting':accounting,
                        'source_sic':official,'source_refs':refs,'tags':{},
                        'rule_version':(sm or am or {}).get('classification_rule_version',snapshot['classification_rule_version']),
                        'basis':'RESEARCH_CORRESPONDENCE','legacy_mapping':deepcopy(m),
                        'retained_snapshot_sha256':source_sha256})
    result={'schema_version':SCHEMA,'dictionary_version':VERSION,'mapping_version':MAPPING_VERSION,
            'data_kind':data_kind,'members':list(snapshot['members']),
            'universe_id':snapshot['universe_id'],'universe_version':snapshot['universe_version'],
            'sources':[sources[k] for k in sorted(sources)],'records':records}
    if dictionary_version==POLICY_DICTIONARY_VERSION:return upgrade_policy_store(result,recorded_at=recorded_at)
    if dictionary_version!=VERSION:raise ValueError('CLASSIFICATION_DICTIONARY_VERSION_INVALID')
    return validate(result)


def upgrade_policy_store(store, *, recorded_at):
    """Version the correspondence policy without changing any company record."""
    validate(store);timestamp(recorded_at)
    out=deepcopy(store)
    if out['dictionary_version']==POLICY_DICTIONARY_VERSION:return out
    out.update(dictionary_version=POLICY_DICTIONARY_VERSION,mapping_version=POLICY_MAPPING_VERSION,
               boundary_policy={'version':BOUNDARY_POLICY_VERSION,'source':BOUNDARY_SOURCE,
                                'approved_date':'2026-11-08','recorded_at':recorded_at,
                                'recorded_at_basis':'RESEARCH_APPLICATION_NOT_ORIGINAL_COMPANY_CLASSIFICATION_DATE'})
    return validate(out)


def append_review(store, imported, *, company_ids):
    """Append reviewed rows and provenance; no previous decision/source is overwritten."""
    validate(store);validate(imported)
    for field in ('members','universe_id','universe_version','data_kind','dictionary_version','mapping_version'):
        if store[field]!=imported[field]:raise ValueError('REVIEW_STORE_CONTEXT_MISMATCH:'+field)
    ids=set(company_ids)
    if len(ids)!=len(company_ids) or not ids<=set(store['members']):raise ValueError('REVIEW_MEMBERS_INVALID')
    out=deepcopy(store);sources={s['source_id']:s for s in out['sources']}
    new_sources={s['source_id']:s for s in imported['sources']}
    for candidate in imported['records']:
        if candidate['company_id'] not in ids:continue
        r=deepcopy(candidate)
        old=[x for x in store['records'] if x['company_id']==r['company_id'] and x['applicability']==r['applicability']]
        superseded={x['supersedes'] for x in old if x.get('supersedes')}
        heads=[x for x in old if x['record_id'] not in superseded]
        if len(heads)!=1 or heads[0]['issuer_id']!=r['issuer_id']:raise ValueError('REVIEW_PREDECESSOR_UNCONFIRMED')
        if timestamp(r['recorded_at'])<=timestamp(heads[0]['recorded_at']):raise ValueError('REVIEW_TIME_NOT_LATER')
        r['supersedes']=heads[0]['record_id'];r['tags']=deepcopy(heads[0]['tags'])
        refs=[]
        for key in r['source_refs']:
            source=deepcopy(new_sources[key])
            if key in sources and sources[key]!=source:
                key=key+':metadata:'+digest(source)[:16];source['source_id']=key
            if key not in sources:out['sources'].append(source);sources[key]=source
            elif sources[key]!=source:raise ValueError('REVIEW_SOURCE_ID_CONFLICT')
            refs.append(key)
        r['source_refs']=refs;out['records'].append(r)
    if sum(x['company_id'] in ids for x in imported['records'])!=len(ids):raise ValueError('REVIEW_ROWS_INCOMPLETE')
    return validate(out)
