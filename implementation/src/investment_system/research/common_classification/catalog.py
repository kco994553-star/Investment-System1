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

# Current system definitions live in this catalog, not in screen-specific maps.
# Archived dictionary/1 and /2 serializations above remain byte-compatible for
# existing classification/result hashes; this descriptor does not reclassify.
DEFINITION_VERSION = 'investment-system-common-10-sector/1'
DEFINITION_SOURCE = 'owner:2026-11-08:common-taxonomy-and-coverage'
SECTOR_DEFINITIONS = {
    'CONSUMER_DISCRETIONARY': ('경기소비재', '선택적 소비 관련 제품·서비스의 주 사업', ['선택적 소비재·서비스', '근거가 확인된 미디어·오락'], ['필수소비', '주 사업 미확인 플랫폼·복합사업']),
    'CONSUMER_STAPLES': ('필수소비재', '반복적인 생활 필수 소비 제품·서비스의 주 사업', ['식품·음료', '필수 생활용품·식품 소매'], ['선택적 소비 사업', '통계기관 식품 코드 전체의 자동 대응']),
    'ENERGY': ('에너지', '에너지 자원의 생산·정제·관련 서비스 주 사업', ['석유·가스 생산·정제', '사업 근거가 있는 에너지 서비스'], ['전력·가스 공급 유틸리티의 자동 포함']),
    'FINANCIALS': ('금융', '금융 서비스와 승인된 REIT 상위 배치', ['은행·보험·금융 서비스', 'REIT: 별도 회계모형'], ['모든 부동산 기업의 REIT 간주', '관리의료의 금융 자동 배치']),
    'HEALTH_CARE': ('헬스케어', '의료 제품·서비스와 확인된 건강보험·관리의료', ['의약·의료기기·의료서비스', '주 사업 확인된 건강보험·관리의료'], ['복합기업의 근거 없는 일괄 배치', '회계모형 GENERAL 자동 부여']),
    'INDUSTRIALS': ('산업재', '기업·산업 활동용 자본재와 산업 서비스의 주 사업', ['자본재·산업 서비스', '근거 확인된 운송·건설 관련 사업'], ['제조업 통계 전체의 자동 대응', '에너지·소재·IT 제조의 무차별 포함']),
    'INFORMATION_TECHNOLOGY': ('정보기술', '정보 처리 기술 제품·소프트웨어·관련 서비스의 주 사업', ['컴퓨터·반도체·소프트웨어', '근거 확인된 정보기술 서비스'], ['광고·플랫폼이라는 명칭만의 자동 포함', '통신망 서비스']),
    'MATERIALS': ('소재', '원재료·기초 소재 공급의 주 사업', ['화학·금속·종이 등 근거 확인 소재 사업'], ['상품 용도와 주 사업이 미확인인 복합 제조업']),
    'TELECOMMUNICATIONS': ('통신서비스', '실제 통신망과 유무선 통신서비스의 주 사업', ['통신망·유선·무선 통신서비스'], ['미디어·오락의 자동 포함', '현대 Communication Services·XLC 범위 복사']),
    'UTILITIES': ('유틸리티', '전력·가스·수도 등 공급 유틸리티의 주 사업', ['전력·가스·수도 공급 유틸리티'], ['에너지 자원 생산·정제의 자동 포함']),
}


def current_taxonomy():
    """Current display/definition contract; stable IDs and old records unchanged."""
    if set(SECTOR_DEFINITIONS) != set(SECTORS):
        raise ValueError('SECTOR_DEFINITION_ID_MISMATCH')
    old = dictionary(POLICY_DICTIONARY_VERSION)
    return {'schema_version': 'common-classification-definition/1', 'version': DEFINITION_VERSION,
        'name': '투자시스템 공통 10섹터', 'basis': 'BOOK_BASED_SYSTEM_CLASSIFICATION_NOT_GICS_SIC_OR_ETF',
        'classification_effect': 'NONE_DISPLAY_DEFINITION_ONLY',
        'record_dictionary_versions': [VERSION, POLICY_DICTIONARY_VERSION],
        'sectors': [{'id': key, 'name': SECTOR_DEFINITIONS[key][0], 'definition': SECTOR_DEFINITIONS[key][1],
                     'includes': list(SECTOR_DEFINITIONS[key][2]), 'excludes': list(SECTOR_DEFINITIONS[key][3]),
                     'version': DEFINITION_VERSION, 'evidence_refs': [DEFINITION_SOURCE, BOUNDARY_SOURCE],
                     'book_direct_claim': False, 'automatic_company_assignment': False} for key in SECTORS],
        'industries': old['industries'], 'boundary_policy': old['policy'],
        'separate_dimensions': ['common_sector', 'common_industry', 'source_sic', 'accounting_model', 'tags', 'etf_benchmark']}
