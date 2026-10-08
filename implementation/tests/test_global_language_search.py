"""Presentation regression over real producer snapshots, not new investment logic."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from investment_system.product.entity_catalog import entity_catalog
from investment_system.product.web_mvp import build, repository_bundle, demo_bundle, envelope
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.technical.engine import TechnicalEngine
from investment_system.macro.engine import MacroEngine
from investment_system.qgv.portfolio import PortfolioEngine
from tests.helpers import AS_OF, complete_obs


def test_canonical_catalog_reuses_identity_and_does_not_mutate():
    b = demo_bundle(repository_bundle())
    before = deepcopy(b)
    cat = entity_catalog(b)
    assert b == before
    companies = [e for e in cat['entities'] if e['entity_type'] == 'COMPANY']
    assert {e['canonical_id'] for e in companies} == {c['company_id'] for c in b['companies']}
    nvda = next(e for e in companies if e['canonical_id'] == 'nvda')
    assert nvda['canonical_label'] == 'NVIDIA Corporation'
    assert nvda['aliases']['ko-KR'] == ['엔비디아']
    assert not any(e['entity_type'] == 'INVESTOR' for e in cat['entities'])


def test_registered_investor_and_historical_metadata_only():
    b = repository_bundle()
    b['search_entities'] = [{'entity_type': 'INVESTOR', 'canonical_id': 'test-investor',
        'canonical_label': 'Registered Test Investor', 'aliases': {'ko-KR': ['테스트 투자자']},
        'source': 'test registration; no profile'}]
    b['companies'][0]['historical_names'] = ['Historic registered name']
    assert any(e['canonical_id'] == 'test-investor' for e in entity_catalog(b)['entities'])
    assert entity_catalog(b)['entities'][0]['historical_names'] == ['Historic registered name']
    b['search_entities'][0]['source'] = ''
    with pytest.raises(ValueError):
        entity_catalog(b)


def test_reject_duplicate_entities_and_invalid_aliases():
    b = repository_bundle()
    b['search_entities'] = [{'entity_type':'MACRO','canonical_id':'CPIAUCSL',
        'canonical_label':'Duplicate','source':'test'}]
    with pytest.raises(ValueError):
        entity_catalog(b)
    b.pop('search_entities')
    b['companies'][0]['aliases'] = {'ko-KR': 'invalid'}
    with pytest.raises(ValueError):
        entity_catalog(b)


def test_build_preserves_numerical_snapshots_and_source_original(tmp_path):
    qgv = AnalysisEngine().analyze('nvda', AS_OF, complete_obs(), synthetic=True).to_dict()
    technical = TechnicalEngine().evaluate('nvda', AS_OF, [0.01, 0.02, -0.01]).to_dict()
    macro = MacroEngine().evaluate(AS_OF, {'growth':0.04,'inflation':0.02}).to_dict()
    portfolio = PortfolioEngine().official_v11(AS_OF).to_dict()
    b = demo_bundle(repository_bundle())
    for key, value in [('qgv',{'nvda':qgv}),('technical',{'nvda':technical}),
                       ('macro',macro),('portfolio',portfolio)]:
        b[key] = envelope(value, 'DEMO', AS_OF.isoformat(), 'test producer / synthetic')
    b['news'] = envelope([{'headline':'Original article', 'source_language':'en',
        'source_original': {'ticker':'NVDA','cik':'0001045810','cusip':'67066G104',
        'accession':'0001045810-24-000264','source_url':'https://www.sec.gov/Archives/',
        'provenance':{'stamp':'original'},'raw_source_data':'raw SEC filing'}}],
        'DEMO', AS_OF.isoformat(), 'test producer')
    before = deepcopy(b)
    build(tmp_path, bundle=b)
    assert b == before
    assert json.loads((tmp_path/'data.json').read_text()) == before
    assert (tmp_path/'locale.js').exists() and (tmp_path/'entity-search.js').exists()
    assert json.loads((tmp_path/'entities.json').read_text()) == entity_catalog(b)
    # Locale has no path into any engine; browser test changes it against these payload shapes.
    assert 'display_locale' not in json.dumps(before)


def test_default_build_company_identity_still_exact_500(tmp_path):
    b = repository_bundle()
    build(tmp_path, bundle=b)
    cat = json.loads((tmp_path/'entities.json').read_text())
    assert len([e for e in cat['entities'] if e['entity_type'] == 'COMPANY']) == 500
    assert json.loads((tmp_path/'data.json').read_text())['universe'] == b['universe']
