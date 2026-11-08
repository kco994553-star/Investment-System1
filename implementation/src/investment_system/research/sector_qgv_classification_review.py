"""Additive, explicit held-source reviews. No inferred business or new collection.

The caller supplies reviewed claims, never an automatic word-to-sector classifier.
Each claim is bound to exact document bytes, XBRL context and an existing issuer.
"""
from copy import deepcopy
import hashlib
import re
import xml.etree.ElementTree as ET

from .sector_qgv import digest, day, timestamp
from .sector_qgv_held import checked_bytes
from .sector_qgv_registry import SECTORS, TEMPLATES
from .sector_qgv_classification import classify, SIC_RULES
from .common_classification.catalog import PARENTS

VERSION='held-sec-book-correspondence/0.3.0'
# Named activities only. SEC SIC remains the source code, not an official book sector.
ACTIVITIES={
 '1520':('CONSUMER_DISCRETIONARY','GENERAL','General Bldg Contractors - Residential Bldgs'),
 '3420':('INDUSTRIALS','GENERAL','Cutlery, Handtools & General Hardware'),
 '3430':('INDUSTRIALS','GENERAL','Heating Equip, Except Elec & Warm Air; & Plumbing Fixtures'),
 '3663':('INFORMATION_TECHNOLOGY','GENERAL','Radio & Tv Broadcasting & Communications Equipment'),
 '3669':('INFORMATION_TECHNOLOGY','GENERAL','Communications Equipment, NEC'),
 '4922':('ENERGY','GENERAL','Natural Gas Transmission'),
 '6199':('FINANCIALS',None,'Finance Services'),
 '6200':('FINANCIALS',None,'Security & Commodity Brokers, Dealers, Exchanges & Services'),
 '6282':('FINANCIALS',None,'Investment Advice'),
 '6411':('FINANCIALS',None,'Insurance Agents, Brokers & Service'),
}


def _sources(review, row, snapshot, evidence):
    if (review.get('issuer_id')!=row['issuer_id'] or review.get('company_id')!=row['company_id'] or
        review.get('valuation_date')!=snapshot['valuation_date'] or
        review.get('submissions_sha256')!=evidence['source_sha256']):
        raise ValueError('BUSINESS_REVIEW_CONTEXT_MISMATCH')
    docs=[]; roots=[]
    for d in review['documents']:
        if (not re.fullmatch('[0-9a-f]{64}',d.get('archive_sha256','')) or not d.get('member') or
            not d.get('source_url') or timestamp(d['acquired_at'])>timestamp(snapshot['as_of'])):
            raise ValueError('BUSINESS_REVIEW_DOCUMENT_UNAVAILABLE')
        # XML is a retained SEC instance; DTD/entity processing is outside the contract.
        body=checked_bytes(d)
        if b'<!DOCTYPE' in body or b'<!ENTITY' in body:raise ValueError('BUSINESS_REVIEW_XML_UNSUPPORTED')
        roots.append(ET.fromstring(body))
        docs.append({'source_id':'filing:'+d['sha256'], 'sha256':d['sha256'],
            'url':d['source_url'],'locator':d['member'],'archive_sha256':d['archive_sha256'],
            'published_at':None,'published_date':None,'publication_reason':'ORIGINAL_RELEASE_TIME_NOT_RETAINED',
            'acquired_at':d['acquired_at'],'availability_basis':'OBSERVED_BY_ACQUISITION_NOT_FIRST_PUBLICATION'})
    refs=[]
    for c in review['citations']:
        idx=c['document']
        if type(idx) is not int or not 0<=idx<len(roots):raise ValueError('BUSINESS_REVIEW_CITATION_INVALID')
        root=roots[idx]
        matches=[x for x in root.iter() if x.tag==c['tag'] and x.get('contextRef')==c['context_id']]
        if len(matches)!=1 or hashlib.sha256((matches[0].text or '').encode()).hexdigest()!=c['text_sha256']:
            raise ValueError('BUSINESS_REVIEW_TEXT_MISMATCH')
        contexts=[x for x in root if x.tag.rsplit('}',1)[-1]=='context' and x.get('id')==c['context_id']]
        if len(contexts)!=1:raise ValueError('BUSINESS_REVIEW_CONTEXT_INVALID')
        values={x.tag.rsplit('}',1)[-1]:x.text for x in contexts[0].iter()}
        if (values.get('identifier')!=row['issuer_id'] or values.get('startDate')!=c['period_start'] or
            values.get('endDate')!=c['period_end'] or not c['period_start'] or not c['period_end'] or
            day(c['period_start'])>day(c['period_end']) or day(c['period_end'])>day(snapshot['valuation_date'])):
            raise ValueError('BUSINESS_REVIEW_PERIOD_OR_ISSUER_INVALID')
        refs.append(docs[idx]['locator']+'#'+c['tag']+'@'+c['context_id']+'#sha256='+docs[idx]['sha256'])
    return docs,refs


def _business(review,row,snapshot,evidence):
    docs,refs=_sources(review,row,snapshot,evidence)
    claims=review['claims']
    if set(claims)-{'sector','accounting','industry'}:raise ValueError('BUSINESS_REVIEW_COMPONENT_INVALID')
    identity=deepcopy(review)
    for d in identity['documents']:d.pop('path',None)
    mapping={};fields={'sector':'sector_id','accounting':'accounting_template','industry':'reviewed_industry_id'}
    for field,claim in claims.items():
        allowed=SECTORS if field=='sector' else TEMPLATES if field=='accounting' else PARENTS
        ids=claim.get('citations')
        if (claim.get('id') not in allowed or not claim.get('rationale') or not ids or
            any(type(i) is not int or not 0<=i<len(refs) for i in ids)):
            raise ValueError('BUSINESS_REVIEW_CLAIM_UNSUPPORTED')
        if field=='accounting':
            expected='FINANCIAL' if claim['id'] in ('BANK','INSURANCE','BROKER','ASSET_MANAGER') else 'GENERAL'
            if row.get('source_profile')!=expected:raise ValueError('BUSINESS_REVIEW_ACCOUNTING_PROFILE_CONFLICT')
        row[fields[field]]=claim['id']
        mapping[field]={'classification_rule_version':VERSION,'rule_id':VERSION+':business:'+digest(identity)[:16],
            'reason':claim['rationale'],'evidence_refs':[refs[i] for i in ids]}
    if row.get('reviewed_industry_id') and PARENTS[row['reviewed_industry_id']]!=row.get('sector_id'):
        raise ValueError('BUSINESS_REVIEW_INDUSTRY_PARENT_CONFLICT')
    row.setdefault('component_mappings',{}).update(mapping)
    row['review_sources']=docs
    if not row.get('sector_id'):
        row['reasons']=[review.get('sector_unresolved_reason') or (row.get('reasons') or ['SECTOR_UNCONFIRMED'])[0]]
    elif row.get('accounting_template'):row['reasons']=[]
    else:row['reasons']=['ACCOUNTING_TEMPLATE_UNCONFIRMED']


def extend_review(snapshot,evidence_by_code,business_reviews):
    result=deepcopy(snapshot);changes=[]
    reviews={x['company_id']:x for x in business_reviews}
    if len(reviews)!=len(business_reviews) or not set(reviews)<=set(snapshot['members']):
        raise ValueError('BUSINESS_REVIEW_MEMBERS_INVALID')
    for row in result['rows']:
        if row.get('mapping'):
            if row['company_id'] in reviews:raise ValueError('EXISTING_CLASSIFICATION_REPLACEMENT_NOT_SUPPORTED')
            continue
        old=deepcopy(row);sic=row.get('source_sic');e=evidence_by_code.get(row['company_id'])
        rule=None;activity=ACTIVITIES.get(sic)
        if activity and e and ' '.join(e.get('sic_description','').split()).casefold()==' '.join(activity[2].split()).casefold():
            rule={'sector_id':activity[0],'accounting_template':activity[1],'rule_id':VERSION+':'+sic,
                  'reason':'Reviewed named SEC primary activity: '+activity[2]+'. No segment mix or accounting model inferred.'}
        elif old.get('reasons')==['ACCOUNTING_PROFILE_CONFLICT']:
            rule=SIC_RULES.get(sic)
        linked=classify(e,as_of=snapshot['as_of'],expected_issuer=row['issuer_id'],expected_sic=sic,
                        source_profile=row.get('source_profile'),reviewed_rules={sic:rule} if rule else {},
                        rule_version=VERSION,independent_components=True)
        source_valid=linked['official_classification'] is not None and linked['reasons']!=['SIC_SOURCE_CONFLICT']
        if rule:row.update(linked)
        review=reviews.get(row['company_id'])
        if review:
            if not source_valid:raise ValueError('BUSINESS_REVIEW_SUBMISSIONS_INVALID')
            row['official_classification']=linked['official_classification']
            _business(review,row,snapshot,e)
        if row!=old:
            changes.append({'company_id':row['company_id'],'issuer_id':row['issuer_id'],
                'before_sector':old.get('sector_id'),'after_sector':row.get('sector_id'),
                'before_accounting':old.get('accounting_template'),'after_accounting':row.get('accounting_template'),
                'before_reasons':old.get('reasons'),'after_reasons':row.get('reasons'),
                'component_mappings':row.get('component_mappings',{})})
    result.update(classification_rule_version=VERSION,input_version='held-sec-sector-classified/3',
                  snapshot_id=snapshot['snapshot_id']+'-review-'+digest(changes)[:12])
    return result,{'schema_version':'sector-classification-review/1','classification_rule_version':VERSION,
        'changes':changes,'original_denominator':len(snapshot['members']),
        'new_sector':sum(x['before_sector'] is None and x['after_sector'] is not None for x in changes),
        'new_accounting':sum(x['before_accounting'] is None and x['after_accounting'] is not None for x in changes),
        'raw_observations_recomputed':0,'gate_inputs_recomputed':0}
