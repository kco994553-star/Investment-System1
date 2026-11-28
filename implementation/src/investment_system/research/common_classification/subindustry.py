"""Offline research taxonomy. No scoring or collection dependencies."""
import json
from collections import Counter
from pathlib import Path

VERSION = "common-subindustry/3"

# Names on the preserved 2026-11-22 research projection, not issuer identifiers.
STUDY_LABELS = {
    "consumer_products": ["자동차·개인 이동제품", "주택·생활 내구재·의류"],
    "consumer_distribution": ["선택소비 유통·서비스"],
    "dining_leisure": ["외식·숙박·여가"],
    "media_content": ["미디어·콘텐츠"],
    "staple_manufacturing": ["생활·개인용품", "식품·음료·담배 제조"],
    "staple_supply": ["필수소비 유통"],
    "fuel_chain": ["자원 탐사·생산", "생산 지원·수송", "정제·연료 가공"],
    "bank_credit": ["은행·대출"],
    "risk_insurance": ["보험·보험 중개"],
    "financial_transactions": ["자본시장·투자 서비스"],
    "property_income": ["부동산 투자·운영"],
    "care_delivery": ["의료 제공·보험·의약 유통"],
    "clinical_equipment": ["의료기기·진단장비"],
    "therapeutics": ["의약품·바이오"],
    "production_equipment": ["산업 기계·부품"],
    "freight_mobility": ["운송·물류"],
    "business_operations": ["건설·사업 지원"],
    "transport_equipment": ["항공우주·방산·운송장비"],
    "it_hardware": ["컴퓨팅·통신 하드웨어"],
    "chips_components": ["반도체·전자부품"],
    "software_information": ["소프트웨어·정보 서비스"],
    "chemical_inputs": ["화학·산업 원료"],
    "physical_materials": ["목재·제지·포장", "금속·광물·건설 소재"],
    "network_access": ["통신서비스"],
    "utility_supply": ["가스 공급·가스 중심 복합", "전력·전력 중심 복합", "수도·환경 공급망"],
}


def load_dictionary():
    return json.loads(Path(__file__).with_name("subindustries_v3.json").read_bytes())


def distribution(rows, groups):
    by_issuer = {}
    for row in rows:
        group = row.get("industry_id")
        if group:
            prior = by_issuer.setdefault(row["issuer_id"], group)
            if group != prior:
                raise ValueError("ISSUER_INDUSTRY_CONFLICT")
    counts = Counter(by_issuer.values())
    if set(counts) - set(groups):
        raise ValueError("UNKNOWN_DICTIONARY_ID")
    sizes = {group: counts[group] for group in groups}
    return {"issuers_per_industry": sizes, "under_10": sum(n < 10 for n in sizes.values()),
            "10_to_19": sum(10 <= n < 20 for n in sizes.values()),
            "20_plus": sum(n >= 20 for n in sizes.values())}
