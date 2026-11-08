"""Held SEC classification evidence -> dated research correspondence and Q gate.

SEC SIC is the official source classification. Book-sector/accounting assignments
below are Codex research correspondences for one evaluation, not official GICS,
legal business-history intervals or security/representative-listing identification.
No extraction of fresh data, price calculation or re-derivation of retained ratios.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
import tarfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from .sector_qgv import digest, timestamp, day
from .sector_qgv_registry import MAPPING
from .sector_qgv_held import checked_bytes
from investment_system.qgv import qgv_v2 as official

RULE_VERSION='held-sec-book-correspondence/0.1.0'
CALC_VERSION='qgv2-calc/2026-10-23.1'
# Exact-code whitelist. Mixed business categories are intentionally absent.
# These assignments express the named SIC activity's economic role in the book's
# ten-sector taxonomy; they do not repurpose the operational SIC -> ETF table.
SIC_RULES={}
def _assign(sector,codes,template='GENERAL',rationale=''):
    for code in codes.split():
        if code in SIC_RULES:raise ValueError('DUPLICATE_SIC_RULE')
        SIC_RULES[code]={'sector_id':sector,'accounting_template':template,
                         'reason':rationale,'rule_id':RULE_VERSION+':'+code}

_assign('INFORMATION_TECHNOLOGY','3570 3571 3572 3575 3576 3577 3661 3670 3672 3674 3678 3679 7370 7371 7372 7373 7374',
        rationale='Named computing, software, semiconductor or electronic-component activity; book information technology correspondence.')
_assign('HEALTH_CARE','2833 2834 2835 2836 3841 3842 3843 3844 3845 3851 5047 5122 8000 8011 8050 8060 8062 8071 8082 8090',
        rationale='Named medicines, medical devices or healthcare delivery activity; not insurance/managed-care by assumption.')
_assign('UTILITIES','4911 4923 4924 4931 4932 4939 4941',
        rationale='Named electric/gas/water distribution utility; pipelines and waste businesses are not inferred to be utilities.')
_assign('ENERGY','1220 1221 1222 1231 1311 1381 1382 1389 2911 2990',
        rationale='Named coal/oil/gas extraction, field services or petroleum refining activity.')
_assign('MATERIALS','1000 1011 1021 1040 1041 1090 1229 1400 2400 2421 2600 2611 2621 2631 2650 2670 2810 2819 2820 2821 2860 2870 2873 2890 3241 3270 3310 3312 3330 3334 3350 3411',
        rationale='Named mining, basic materials, industrial chemicals, paper or basic-metal production.')
_assign('CONSUMER_STAPLES','2000 2011 2013 2015 2020 2024 2030 2040 2050 2052 2060 2080 2082 2086 2090 2100 2111 2840 2844 5140 5141 5411',
        rationale='Named food, beverage, tobacco, household/personal consumables or food-distribution activity.')
_assign('CONSUMER_DISCRETIONARY','1531 2300 2320 2330 2340 2390 2510 2511 2512 2517 2520 2531 2590 3021 3140 3630 3651 3711 3714 3751 3942 3944 3949 3960 5000 5200 5211 5500 5531 5600 5621 5651 5661 5700 5712 5731 5734 5812 5940 5944 5945 5947 7011 7030 7510 7812 7841 7900 7948 7990 7997',
        rationale='Named discretionary household products, specialty retail, automotive, lodging, restaurant or leisure activity; general mixed retail is held.')
_assign('INDUSTRIALS','1500 1520 1600 1623 1700 1731 3510 3523 3530 3531 3532 3533 3537 3540 3541 3550 3560 3561 3562 3564 3567 3569 3580 3585 3590 3612 3613 3620 3621 3640 3644 3671 3690 3713 3720 3721 3724 3728 3730 3743 3760 3812 3823 3990 4011 4100 4210 4213 4220 4400 4412 4512 4513 4522 4581 4700 4731 4950 4953 5080 5084 7340 7361 7363 8711',
        rationale='Named capital goods, engineering/construction, industrial transport or support activity; broad business-service/scientific categories are held.')
_assign('TELECOMMUNICATIONS','4812 4813',
        rationale='Named wireless/wireline telephone communication; media/platform/cable are not automatically book telecom.')
_assign('FINANCIALS','6021 6022 6029 6035 6036',template='BANK',rationale='Named commercial/savings bank activity; capital-intensive bank accounting template.')
_assign('FINANCIALS','6311 6321 6331 6351 6361 6399',template='INSURANCE',rationale='Named insurance carrier activity; not insurance agents, brokers or managed healthcare.')
_assign('FINANCIALS','6211',template='BROKER',rationale='Named security broker/dealer activity; not all miscellaneous finance or investment advice.')

UNRESOLVED={
 '6798':'REIT_ACCOUNTING_AND_BOOK_SECTOR_UNRESOLVED',
 '6282':'FEE_BUSINESS_NOT_ESTABLISHED',
 '6200':'FINANCIAL_BUSINESS_MODEL_UNRESOLVED',
 '6199':'FINANCIAL_BUSINESS_MODEL_UNRESOLVED',
 '6411':'FEE_BUSINESS_NOT_ESTABLISHED',
 '6324':'MANAGED_CARE_BOOK_SECTOR_UNRESOLVED',
 '4832':'BOOK_TELECOM_MEDIA_BOUNDARY_UNRESOLVED',
 '4833':'BOOK_TELECOM_MEDIA_BOUNDARY_UNRESOLVED',
 '4841':'BOOK_TELECOM_MEDIA_BOUNDARY_UNRESOLVED',
 '4899':'BOOK_TELECOM_MEDIA_BOUNDARY_UNRESOLVED',
 '7389':'SIC_BUSINESS_MIX_UNRESOLVED',
 '3559':'SEMICONDUCTOR_EQUIPMENT_OR_INDUSTRIAL_UNRESOLVED',
 '3826':'INSTRUMENT_END_MARKET_UNRESOLVED',
 '3827':'INSTRUMENT_END_MARKET_UNRESOLVED',
 '3829':'INSTRUMENT_END_MARKET_UNRESOLVED',
 '8731':'RESEARCH_END_MARKET_UNRESOLVED',
 '5311':'MIXED_RETAIL_BOOK_SECTOR_UNRESOLVED',
 '5331':'MIXED_RETAIL_BOOK_SECTOR_UNRESOLVED',
 '5961':'MIXED_RETAIL_BOOK_SECTOR_UNRESOLVED',
}
# Broad wholesale SIC 5000 cannot establish discretionary end markets.
for _mixed in ('5000','1520','3550','3690','7374','7510','7812','7841'):
    SIC_RULES.pop(_mixed,None)
SIC_RULES['3671']={'sector_id':'INFORMATION_TECHNOLOGY','accounting_template':'GENERAL',
                   'reason':'Named electronic-tube/component production.', 'rule_id':RULE_VERSION+':3671'}


def classify(evidence,*,as_of,expected_issuer,expected_sic,source_profile,reviewed_rules=None,rule_version=RULE_VERSION,independent_components=False):
    out={'sector_id':None,'accounting_template':None,'mapping':None,
         'official_classification':None,'reasons':[]}
    def fail(reason):out['reasons']=[reason];return out
    if not isinstance(evidence,dict):return fail('CLASSIFICATION_SOURCE_NOT_CONNECTED')
    if evidence.get('issuer_id')!=expected_issuer or not expected_issuer:return fail('ISSUER_MISMATCH')
    if evidence.get('source_kind')!='SEC_SUBMISSIONS' or not all(isinstance(evidence.get(k),str) and re.fullmatch('[0-9a-f]{64}',evidence[k]) for k in ('source_sha256','archive_sha256')):
        return fail('SOURCE_EVIDENCE_INCOMPLETE')
    if not evidence.get('member') or not evidence.get('sic_description') or not evidence.get('source_url'):return fail('SOURCE_EVIDENCE_INCOMPLETE')
    try:
        if timestamp(evidence['acquired_at'])>timestamp(as_of):return fail('SOURCE_NOT_AVAILABLE_AT_EVALUATION')
        evaluation=timestamp(as_of).astimezone(timezone.utc).date()
    except (KeyError,ValueError,TypeError):return fail('SOURCE_TIME_UNCONFIRMED')
    sic=evidence.get('sic')
    out['official_classification']={'system':'SEC_SIC','code':sic,'description':evidence['sic_description'],
        'observed_at':evidence['acquired_at'],'source_sha256':evidence['source_sha256'],'source_url':evidence['source_url']}
    if sic!=expected_sic:return fail('SIC_SOURCE_CONFLICT')
    rule=(SIC_RULES if reviewed_rules is None else reviewed_rules).get(sic)
    if rule is None:return fail(UNRESOLVED.get(sic,'EXACT_SIC_CORRESPONDENCE_NOT_REVIEWED'))
    financial=rule['accounting_template'] in ('BANK','INSURANCE','BROKER')
    accounting_ok=rule['accounting_template'] is not None and source_profile==('FINANCIAL' if financial else 'GENERAL')
    if not accounting_ok and not independent_components:return fail('ACCOUNTING_PROFILE_CONFLICT')
    out.update(sector_id=rule['sector_id'],accounting_template=rule['accounting_template'] if accounting_ok else None)
    ref=evidence['member']+'#sha256='+evidence['source_sha256']
    mapping={'version':MAPPING,'classification_rule_version':rule_version,
        'kind':'RESEARCH_CORRESPONDENCE','valid_from':evaluation.isoformat(),
        'valid_to':(evaluation+timedelta(days=1)).isoformat(),
        'effective_date_basis':'SINGLE_EVALUATION_APPLICATION_NOT_SOURCE_CHANGE_DATE',
        'source_observed_at':evidence['acquired_at'],'rule_id':rule['rule_id'],
        'reason':rule['reason'],'evidence_refs':[ref,evidence['source_url']],
        'official_system':'SEC_SIC','official_code':sic,'source_archive_sha256':evidence['archive_sha256']}
    if accounting_ok:out['mapping']=mapping
    if independent_components:
        out['component_mappings']={'sector':copy.deepcopy(mapping)}
        if accounting_ok:out['component_mappings']['accounting']=copy.deepcopy(mapping)
        else:out['reasons']=['ACCOUNTING_TEMPLATE_UNCONFIRMED' if rule['accounting_template'] is None else 'ACCOUNTING_PROFILE_CONFLICT']
    return out


def load_held_classification(sec,archive_specs):
    """Only hash-pinned submissions in the existing archive inventory; no backup search."""
    wanted={r.get('source_sha256',{}).get('submissions') for r in sec['records'].values()}
    by_hash={}
    for spec in archive_specs:
        checked_bytes(spec)
        with tarfile.open(spec['path']) as archive:
            tag=spec['release'];manifest=json.load(archive.extractfile(tag+'/manifest.json'))
            for comp in manifest['companies']:
                expected=comp.get('sha256',{}).get('submissions.json')
                if not expected or expected not in wanted:continue
                member=tag+'/'+comp['cik']+'/submissions.json';body=archive.extractfile(member).read()
                if hashlib.sha256(body).hexdigest()!=expected:raise ValueError('CLASSIFICATION_MEMBER_HASH_MISMATCH')
                payload=json.loads(body);cik=str(payload.get('cik','')).zfill(10)
                if cik!=comp['cik']:raise ValueError('CLASSIFICATION_MEMBER_ISSUER_MISMATCH')
                candidate={'issuer_id':cik,'sic':str(payload.get('sic','')).zfill(4),
                    'sic_description':payload.get('sicDescription'),'source_sha256':expected,
                    'archive_sha256':spec['sha256'],'member':member,'acquired_at':comp['acquired_at'],
                    'source_url':'https://data.sec.gov/submissions/CIK'+cik+'.json',
                    'source_kind':'SEC_SUBMISSIONS','fiscal_year_end':payload.get('fiscalYearEnd')}
                # Identical verified bytes can occur in multiple retained releases.
                # Earliest observed availability is evidence, not archive list order.
                def order(e):return (timestamp(e['acquired_at']),e['archive_sha256'],e['member'])
                if expected not in by_hash or order(candidate)<order(by_hash[expected]):
                    by_hash[expected]=candidate
    result={}
    for code,row in sec['records'].items():
        evidence=by_hash.get(row.get('source_sha256',{}).get('submissions'))
        if evidence:
            if evidence['issuer_id']!=row.get('cik'):raise ValueError('CLASSIFICATION_ROW_ISSUER_MISMATCH')
            result[code]=evidence
    return result


def official_q_gate(companies,*,as_of,source_sha256,calc_version):
    """Replay only the existing official Q percentile, independent of prices/new Q.

    Uses the operating engine's published-axis interpretation, official industry
    groups, representative pool, issuer dedupe and >=8/fallback policy unchanged.
    This is formula replay, never labelled an official publication on this date.
    """
    if calc_version!=CALC_VERSION:raise ValueError('OFFICIAL_GATE_VERSION_MISMATCH')
    timestamp(as_of)
    if not re.fullmatch('[0-9a-f]{64}',source_sha256):raise ValueError('OFFICIAL_GATE_SOURCE_HASH_INVALID')
    ids=sorted(companies);values={}
    for key,c in companies.items():
        scores={f:c.get('factors',{}).get(f) for f in official.QG_FACTORS}
        pub=c.get('qg_axes')
        # Do not reconstruct unavailable published axes or substitute new sector Q.
        values[key]=official._published_axis('Q',scores,pub.get('Q'))['score'] if isinstance(pub,dict) else None
    groups={k:c.get('industry_group') for k,c in companies.items()}
    issuers={k:c.get('cik') for k,c in companies.items()}
    pool=[k for k in ids if companies[k].get('in_cross_section',True) is not False]
    percentiles=official._cross(values,groups,ids,pool,industry=True,issuers=issuers)
    result={}
    for key in ids:
        value,reason,basis,n=percentiles.get(key,(None,'OFFICIAL_Q_UNAVAILABLE',None,0))
        result[key]={'q_industry_percentile':value,'calc_version':calc_version,'as_of':as_of[:10],
            'source_as_of':as_of,'derivation':'OFFICIAL_Q_ONLY_REPLAY',
            'publication_status':'RESEARCH_REPLAY_NOT_OFFICIAL_PUBLICATION','reason':reason,
            'peer_basis':basis,'peer_count':n,'source_q_score':values[key],
            'official_gate_min_peers':official.MIN_PEERS,
            'provenance':['sec-qgv2.json#sha256='+source_sha256,'qgv.qgv_v2._published_axis+_cross']}
    return result


def link_classification(snapshot,evidence_by_code,*,gates=None,representatives=None):
    result=copy.deepcopy(snapshot);gates=gates or {};representatives=representatives or {}
    audit={'denominator':len(snapshot['members']),'raw_observations_recomputed':0,'source_classification_confirmed':0,
           'mapped':0,'unresolved':0,'reasons':{},'sector_template_counts':{},'gate_valid':0,'gate_unavailable':0,
           'classification_rule_version':RULE_VERSION}
    for row in result['rows']:
        mapping=classify(evidence_by_code.get(row['company_id']),as_of=snapshot['as_of'],
            expected_issuer=row.get('issuer_id'),expected_sic=row.get('source_sic'),source_profile=row.get('source_profile'))
        row.update(mapping)
        if mapping['official_classification']:audit['source_classification_confirmed']+=1
        if mapping['mapping']:
            audit['mapped']+=1;key=mapping['sector_id']+'|'+mapping['accounting_template']
            audit['sector_template_counts'][key]=audit['sector_template_counts'].get(key,0)+1
        else:
            audit['unresolved']+=1
            for reason in mapping['reasons']:audit['reasons'][reason]=audit['reasons'].get(reason,0)+1
        gate=gates.get(row['company_id'])
        if gate and (gate['as_of']!=snapshot['valuation_date'] or gate['source_as_of']!=snapshot['as_of']):raise ValueError('GATE_SNAPSHOT_MISMATCH')
        row['gate']=gate
        audit['gate_valid' if gate and gate['q_industry_percentile'] is not None else 'gate_unavailable']+=1
        rep=representatives.get(row['company_id'])
        if rep is not None:
            row['scoring_representative']=rep['in_cross_section']
            row['representative_evidence']=rep['provenance']
            row['representative_scope']='OFFICIAL_Q_ISSUER_SCORING_ONLY_NOT_SECURITY_OR_MARKET_CAP'
    if len(result['rows'])!=len(snapshot['members']):raise ValueError('MEMBERSHIP_ROWS_INCOMPLETE')
    result['snapshot_id']=snapshot['snapshot_id']+'-classified-'+digest({k:v['mapping'] for k,v in ((r['company_id'],r) for r in result['rows'])})[:12]
    result['input_version']='held-sec-sector-classified/1'
    result['classification_rule_version']=RULE_VERSION
    audit['raw_observations_unchanged']=all(a['observations']==b['observations'] for a,b in zip(snapshot['rows'],result['rows']))
    if not audit['raw_observations_unchanged']:raise ValueError('RAW_OBSERVATION_CHANGED')
    return result,audit


def connect_held_classification(snapshot,sec,archives,source_sha256):
    """Retained raw matrix + its exact financial source -> classified preview input."""
    from investment_system.qgv.qgv_official import prepare
    if (snapshot['as_of']!=sec['as_of'] or set(snapshot['members'])!=set(sec['records']) or
        snapshot['snapshot_id']!='held-sec-'+source_sha256[:16] or sec.get('calc_version')!=CALC_VERSION):
        raise ValueError('CLASSIFICATION_SNAPSHOT_MISMATCH')
    evidence=load_held_classification(sec,archives)
    ctx=prepare(sec,timestamp(sec['as_of']))
    gates=official_q_gate(ctx['companies'],as_of=sec['as_of'],source_sha256=source_sha256,calc_version=sec['calc_version'])
    representatives={k:{'in_cross_section':c.get('in_cross_section',True) is not False,
        'provenance':['sec-qgv2.json#sha256='+source_sha256,'qgv.qgv_official.prepare/in_cross_section']}
        for k,c in ctx['companies'].items() if k in sec['records']}
    result,audit=link_classification(snapshot,evidence,gates=gates,representatives=representatives)
    audit['official_gate_context']={'calc_version':CALC_VERSION,'source_as_of':sec['as_of'],
        'source_sha256':source_sha256,'context_rows':len(ctx['companies']),
        'representative_pool':sum(c.get('in_cross_section',True) is not False for c in ctx['companies'].values()),
        'derivation':'OFFICIAL_Q_ONLY_REPLAY','price_inputs_used':0,
        'publication_status':'RESEARCH_REPLAY_NOT_OFFICIAL_PUBLICATION',
        'replayed_at':datetime.now(timezone.utc).isoformat()}
    return result,audit


# Additive review only. Original 0.1.0 behavior remains reproducible.
ADDENDUM_VERSION = 'held-sec-book-correspondence/0.2.0'
ADDENDUM_ACTIVITIES = {
    '2033': ('CONSUMER_STAPLES', 'Canned, Fruits, Veg, Preserves, Jams & Jellies'),
    '2070': ('CONSUMER_STAPLES', 'Fats & Oils'),
    '2842': ('CONSUMER_STAPLES', 'Specialty Cleaning, Polishing and Sanitation Preparations'),
    '2851': ('MATERIALS', 'Paints, Varnishes, Lacquers, Enamels & Allied Prods'),
    '3100': ('CONSUMER_DISCRETIONARY', 'Leather & Leather Products'),
    '3480': ('INDUSTRIALS', 'Ordnance & Accessories, (No Vehicles/Guided Missiles)'),
    '3490': ('INDUSTRIALS', 'Miscellaneous Fabricated Metal Products'),
    '3822': ('INDUSTRIALS', 'Auto Controls For Regulating Residential & Comml Environments'),
    '4991': ('UTILITIES', 'Cogeneration Services & Small Power Producers'),
    '5013': ('CONSUMER_DISCRETIONARY', 'Wholesale-Motor Vehicle Supplies & New Parts'),
    '5070': ('INDUSTRIALS', 'Wholesale-Hardware & Plumbing & Heating Equipment & Supplies'),
    '5810': ('CONSUMER_DISCRETIONARY', 'Retail-Eating & Drinking Places'),
    '7359': ('INDUSTRIALS', 'Services-Equipment Rental & Leasing, NEC'),
}


def extend_held_classification(snapshot, evidence_by_code, *, rule_version=ADDENDUM_VERSION, business_reviews=None):
    """Connect reviewed exact SEC activities, retaining all prior rows and gates.

    The SEC-assigned primary activity is business evidence at the source's level;
    it does not establish segment weights, official GICS or security identity.
    Mixed/REIT/end-market/accounting conflicts remain unresolved. No old mapping,
    raw observation, financial input or official Q gate is recomputed/replaced.
    """
    if rule_version in ('held-sec-book-correspondence/0.3.0','held-sec-book-correspondence/0.4.0','held-sec-book-correspondence/0.5.0'):
        from .sector_qgv_classification_review import extend_review
        return extend_review(snapshot,evidence_by_code,business_reviews or [],version=rule_version)
    if rule_version != ADDENDUM_VERSION or business_reviews:
        raise ValueError('CLASSIFICATION_REVIEW_VERSION_INVALID')
    result = copy.deepcopy(snapshot); changes = []
    for row in result['rows']:
        if row.get('mapping') or row.get('reasons') != ['EXACT_SIC_CORRESPONDENCE_NOT_REVIEWED']:
            continue
        sic = row.get('source_sic'); activity = ADDENDUM_ACTIVITIES.get(sic)
        evidence = evidence_by_code.get(row['company_id'])
        if not activity or not evidence:
            continue
        sector, expected_description = activity
        if ' '.join(evidence.get('sic_description','').split()).casefold() != expected_description.casefold():
            continue
        rule = {sic: {'sector_id': sector, 'accounting_template': 'GENERAL',
                      'rule_id': ADDENDUM_VERSION+':'+sic,
                      'reason': 'Research book-sector correspondence for SEC primary activity: '+expected_description+'. Segment mix and official GICS not inferred.'}}
        linked = classify(evidence, as_of=snapshot['as_of'],expected_issuer=row.get('issuer_id'),
                          expected_sic=sic,source_profile=row.get('source_profile'),
                          reviewed_rules=rule,rule_version=ADDENDUM_VERSION)
        if not linked['mapping']:
            continue
        changes.append({'company_id': row['company_id'],'source_sic': sic,'source_description':expected_description,
                        'before_reasons':row['reasons'],'after_sector':sector,'after_template':'GENERAL',
                        'mapping':linked['mapping']})
        row.update(linked)
    result['classification_rule_version'] = ADDENDUM_VERSION
    result['snapshot_id'] = snapshot['snapshot_id']+'-addendum-'+digest(changes)[:12]
    result['input_version'] = 'held-sec-sector-classified/2'
    return result, {'schema_version':'sector-classification-addendum/1','changes':changes,
                    'original_denominator':len(snapshot['members']),'newly_mapped':len(changes),
                    'raw_observations_recomputed':0,'gate_inputs_recomputed':0,
                    'classification_rule_version':ADDENDUM_VERSION}
