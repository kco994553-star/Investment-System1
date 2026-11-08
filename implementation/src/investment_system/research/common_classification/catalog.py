"""A thin parent dictionary over existing IDs, never another SIC classifier."""
from investment_system.qgv.sic_industry import load_sic_config, classify_sic
from ..sector_qgv_registry import SECTORS, MAPPING

VERSION = 'common-industry-dictionary/1'
MAPPING_VERSION = 'common-classification-map/1'
POLICY_DICTIONARY_VERSION = 'common-industry-dictionary/2'
POLICY_MAPPING_VERSION = 'common-classification-map/2'
BOUNDARY_POLICY_VERSION = 'common-sector-boundaries/2026-11-08.1'
BOUNDARY_SOURCE = 'owner:2026-11-08:common-classification-boundaries'
# Reuse the seven explicit adopted subgroup definitions; broad source groups
# such as manufacturing_industrial_tech have no one-to-one sector parent.
PARENTS = {
    'beverages': 'CONSUMER_STAPLES', 'computers': 'INFORMATION_TECHNOLOGY',
    'semiconductors': 'INFORMATION_TECHNOLOGY', 'medical_devices': 'HEALTH_CARE',
    'food_retail': 'CONSUMER_STAPLES', 'software': 'INFORMATION_TECHNOLOGY',
    'health_services': 'HEALTH_CARE',
}
LABELS = ('경기소비재','필수소비재','에너지','금융','헬스케어','산업재','정보기술','소재','통신','유틸리티')


def dictionary(version=VERSION):
    if version not in (VERSION,POLICY_DICTIONARY_VERSION):raise ValueError('CLASSIFICATION_DICTIONARY_VERSION_INVALID')
    source = load_sic_config()
    by_id = {row['id']: row for row in source['subgroups']}
    if set(PARENTS) != set(by_id) or not set(PARENTS.values()) <= set(SECTORS):
        raise ValueError('INDUSTRY_DICTIONARY_SOURCE_CHANGED')
    result={'schema_version':'common-classification-dictionary/1', 'version':version,
            'sector_version':MAPPING, 'sectors':dict(zip(SECTORS, LABELS)),
            'industries':[{'id':key, 'name':by_id[key]['name'], 'parent_sector':parent,
                          'source_dictionary':source['config_version'], 'source_id':key,
                          'source_parent':by_id[key]['group'], 'status':'RESEARCH_CORRESPONDENCE'}
                         for key,parent in sorted(PARENTS.items())],
            'exceptions':{'REIT':'UPPER_SECTOR_AND_ACCOUNTING_NOT_RESOLVED',
                          'COMMUNICATION_SERVICES':'NOT_AN_ALIAS_OF_TELECOMMUNICATIONS',
                          'MULTI_BUSINESS':'PRIMARY_ACTIVITY_EVIDENCE_REQUIRED'},
            'etf_reference_version':'sector_etf_map/v1',
            'source_classification_version':source['config_version']}
    if version==POLICY_DICTIONARY_VERSION:
        result['exceptions']={
            'REIT':'FINANCIALS_UPPER_SECTOR_ACCOUNTING_INDEPENDENT_NOT_ALL_REAL_ESTATE',
            'COMMUNICATION_SERVICES':'NOT_AN_ALIAS_OF_TELECOMMUNICATIONS',
            'TELECOM_MEDIA':'NETWORK_SERVICES_TELECOM_MEDIA_ENTERTAINMENT_DISCRETIONARY_PRIMARY_ACTIVITY_REQUIRED',
            'MANAGED_CARE':'HEALTH_CARE_UPPER_SECTOR_ACCOUNTING_INDEPENDENT',
            'MULTI_BUSINESS':'PRIMARY_ACTIVITY_EVIDENCE_REQUIRED'}
        result['policy']={'version':BOUNDARY_POLICY_VERSION,'approved_date':'2026-11-08',
                          'source':BOUNDARY_SOURCE,'book_direct_claim':False,'automatic_company_assignment':False}
    return result


def industry_for_sic(sic, sector_id):
    source = classify_sic(sic)
    subgroup = source['subgroup']
    if not sector_id or not subgroup:
        return {'id':None, 'status':'UNKNOWN', 'reasons':['SUBINDUSTRY_NOT_CONFIRMED'], 'evidence_refs':[]}
    if PARENTS.get(subgroup) != sector_id:
        return {'id':None, 'status':'CONFLICT', 'reasons':['SOURCE_INDUSTRY_PARENT_CONFLICT'], 'evidence_refs':[]}
    return {'id':subgroup, 'status':'CONFIRMED', 'reasons':[],
            'evidence_refs':['sic_industry_groups/v0:subgroup:'+subgroup,
                             VERSION+':parent:'+subgroup],
            'basis':'RESEARCH_CORRESPONDENCE_NOT_OFFICIAL_INDUSTRY'}
