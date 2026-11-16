"""Only the new producer/consumer fixture boundary, not repeated core tests."""
import hashlib, importlib.util, json
from pathlib import Path
from investment_system.research.company_ownership import json_bytes, digest

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/research/company_ownership/consumer-synthetic.json'


def cases():return {x['case_id']:x for x in json.loads(DATA.read_bytes())['cases']}


def test_new_shared_examples_are_generated_by_existing_producer():
    path=ROOT/'tools/generate_ownership_consumer_examples.py'
    spec=importlib.util.spec_from_file_location('ownership_examples',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert json_bytes(module.generate())==DATA.read_bytes()
    x=json.loads(DATA.read_bytes());assert hashlib.sha256((DATA.parent/'synthetic.json').read_bytes()).hexdigest()==x['original_fixture_sha256']
    assert {c['expected_view']['collection_state'] for c in x['cases']}=={'NOT_COLLECTED','FILTER_EMPTY','VERIFIED_ZERO_IN_SCOPE','NOT_FOUND_IN_REVIEWED_SCOPE','PARTIAL_REVIEW','REVIEWED_SCOPE'}
    for c in x['cases']:assert digest(c['expected_view'])==c['expected_view_sha256']


def test_new_cases_have_hand_checked_direction_capacity_and_unknown_chain():
    cs=cases();incoming=cs['incoming_holder']['expected_view']
    assert all(r['relative_direction']=='INCOMING' and r['direction']=='SOURCE_TO_TARGET' and r['source_entity_id']=='SYN-A' and r['target_entity_id']=='SYN-B' for r in incoming['relationships'])
    original=json.loads((DATA.parent/'synthetic.json').read_bytes())['cases'][0]['expected_view']
    assert {r['relationship_id'] for r in incoming['relationships']}=={r['relationship_id'] for r in original['relationships']}
    indirect=cs['indirect_ownership']['expected_view'];assert indirect['relationships'][0]['directness']=='INDIRECT' and indirect['confirmed_paths']==[]
    managed=cs['13f_investment_discretion']['expected_view']['relationships']
    assert len(managed)==1 and managed[0]['type']=='OWNERSHIP' and managed[0]['capacity']=='INVESTMENT_DISCRETION'
    assert managed[0]['observations'][0]['metric']=='MANAGED_HOLDINGS'
    zero=cs['verified_zero_in_scope']['expected_view'];assert zero['relationships']==[] and zero['collection']['zero_observed_on']=='2025-12-31'
    assert zero['collection_state']=='VERIFIED_ZERO_IN_SCOPE' and zero['relationship_denominator'] is None
    not_reviewed=cs['incoming_centre_not_reviewed']['expected_view']
    assert not_reviewed['collection_state']=='NOT_COLLECTED' and len(not_reviewed['relationships'])==2


def test_failure_receipts_do_not_rewrite_saved_view_or_success_clock():
    cs=cases()
    for name in ('failed','partial','parse_failed'):
        c=cs['refresh_'+name];r=c['refresh'];view=c['expected_view']
        assert r['attempt']['outcome']==name.upper() and r['attempt']['attempted_at']=='2026-01-06T12:00:00Z'
        assert r['retained_view_sha256']==digest(view)
        assert view['generated_at']==r['unchanged_generated_at']=='2026-01-05T12:00:00Z'
        assert view['collection']['last_success_at']==r['unchanged_last_success_at']=='2026-01-04T10:00:00Z'
        assert view['collection']['last_failure'] is None
