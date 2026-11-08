"""New dated classification boundaries, using public synthetic evidence only."""
from copy import deepcopy

import pytest

from investment_system.research.common_classification.catalog import dictionary, industry_for_sic
from investment_system.research.common_classification.records import resolve, validate, from_sector_snapshot


def component(value=None, reason='NOT_REVIEWED'):
    return {'id': value, 'status': 'CONFIRMED' if value else 'UNKNOWN',
            'reasons': [] if value else [reason], 'evidence_refs': ['src'] if value else []}


def store():
    return {'schema_version': 'common-classification/1', 'dictionary_version': dictionary()['version'],
            'mapping_version': 'common-classification-map/1', 'data_kind': 'SYNTHETIC',
            'universe_id': 'SYNTHETIC', 'universe_version': '1', 'members': ['COMPANY:A'],
            'sources': [{'source_id': 'src', 'published_at': None, 'published_date': '2026-11-01',
                         'acquired_at': '2026-11-02T12:00:00Z', 'sha256': 'a'*64,
                         'url': 'https://example.invalid/synthetic', 'locator': 'synthetic evidence'}],
            'records': [{'record_id': 'record-1', 'company_id': 'COMPANY:A', 'issuer_id': 'ISSUER:A',
                         'recorded_at': '2026-11-03T12:00:00Z', 'supersedes': None,
                         'applicability': {'kind': 'EVALUATION_ONLY', 'evaluation_date': '2026-11-04',
                                           'valid_from': None, 'valid_to': None},
                         'sector': component('INFORMATION_TECHNOLOGY'), 'industry': component(),
                         'accounting': component('GENERAL'), 'source_sic': {'system':'SEC_SIC', 'code':'7372'},
                         'tags': {}, 'source_refs': ['src'], 'legacy_mapping': None,
                         'rule_version': 'synthetic/1', 'basis': 'RESEARCH_CORRESPONDENCE'}]}


def view(s, day='2026-11-04', at='2026-11-04T23:00:00Z'):
    return resolve(s, valuation_date=day, knowledge_as_of=at)


def test_explicit_dictionary_reuses_seven_subgroup_ids_and_ten_sectors():
    d = dictionary()
    assert len(d['sectors']) == 10 and len(d['industries']) == 7
    assert {i['parent_sector'] for i in d['industries']} <= set(d['sectors'])
    assert industry_for_sic('7372', 'INFORMATION_TECHNOLOGY')['id'] == 'software'
    assert industry_for_sic('7372', 'HEALTH_CARE')['status'] == 'CONFLICT'
    assert industry_for_sic('6798', None)['id'] is None


def test_sector_only_does_not_need_subindustry_and_preserves_unknown_members():
    s = store(); s['members'].append('COMPANY:MISSING')
    result = view(s)
    assert result['coverage']['member_codes'] == 2
    assert result['coverage']['sector_confirmed'] == 1
    assert result['coverage']['industry_confirmed'] == 0
    assert result['rows'][0]['sector']['id'] == 'INFORMATION_TECHNOLOGY'
    assert result['rows'][1]['sector']['reasons'] == ['CLASSIFICATION_RECORD_MISSING']


def test_evaluation_only_is_not_an_invented_historical_interval():
    s = store()
    assert view(s, '2026-11-03')['coverage']['sector_confirmed'] == 0
    assert view(s, '2026-11-05', '2026-11-06T00:00:00Z')['coverage']['sector_confirmed'] == 0
    assert s['records'][0]['applicability']['valid_from'] is None


def test_late_correction_preserves_old_decision_at_old_knowledge_cutoff():
    s = store(); new = deepcopy(s['records'][0])
    new.update(record_id='record-2', supersedes='record-1', recorded_at='2026-11-06T00:00:00Z')
    new['sector'] = component('HEALTH_CARE'); s['records'].append(new)
    assert view(s)['rows'][0]['record_id'] == 'record-1'
    assert view(s, at='2026-11-07T00:00:00Z')['rows'][0]['record_id'] == 'record-2'
    assert len(s['records']) == 2


def test_date_only_publication_is_not_midnight_or_acquisition_time():
    s = store(); s['sources'][0]['published_date'] = '2026-11-04'
    result = view(s)
    assert result['rows'][0]['sector']['status'] == 'UNKNOWN'
    assert 'SOURCE_DATE_PRECISION_INSUFFICIENT' in result['rows'][0]['sector']['reasons']
    assert s['sources'][0]['published_at'] is None
    assert view(s, at='2026-11-05T00:00:00Z')['coverage']['sector_confirmed'] == 1


@pytest.mark.parametrize('change,reason', [
    ('future_source', 'SOURCE_NOT_AVAILABLE'), ('future_record', 'RECORD_NOT_AVAILABLE'),
    ('duplicate', 'AMBIGUOUS_CLASSIFICATION'), ('unknown_interval', 'EFFECTIVE_START_UNKNOWN')])
def test_unusable_evidence_keeps_member_with_reason(change, reason):
    s = store()
    if change == 'future_source': s['sources'][0]['acquired_at'] = '2026-11-05T00:00:00Z'
    elif change == 'future_record': s['records'][0]['recorded_at'] = '2026-11-05T00:00:00Z'
    elif change == 'duplicate':
        dup = deepcopy(s['records'][0]); dup['record_id'] = 'unrelated'; s['records'].append(dup)
    else: s['records'][0]['applicability'] = {'kind':'INTERVAL','evaluation_date':None,'valid_from':None,'valid_to':None}
    assert reason in view(s)['rows'][0]['sector']['reasons']


def test_tags_order_and_revision_identity_do_not_change_numeric_classification_hash():
    s = store(); original = view(s)
    s['records'][0]['tags'] = {'lynch':['FAST_GROWER'], 'policy':['SYNTHETIC'], 'business_exposure':['A','B']}
    result = view(s)
    assert result['classification_hash'] == original['classification_hash']
    assert result['display_hash'] != original['display_hash']
    assert len(result['rows']) == 1


def test_invalid_parent_and_revision_reference_fail_before_resolution():
    s = store(); s['records'][0]['industry'] = component('medical_devices')
    with pytest.raises(ValueError, match='INDUSTRY_PARENT_CONFLICT'): validate(s)
    s = store(); s['records'][0]['supersedes'] = 'absent'
    with pytest.raises(ValueError, match='REVISION_REFERENCE_INVALID'): validate(s)


def test_deterministic_order_duplicate_issuer_and_independent_accounting_conflict():
    s=store(); second=deepcopy(s['records'][0])
    second.update(company_id='COMPANY:B',record_id='record-B')
    second['accounting']=component('BANK')
    s['members'].append('COMPANY:B'); s['records'].append(second)
    a=view(s)
    assert a['coverage']['member_codes']==2 and a['coverage']['unique_issuers']==1
    assert a['coverage']['sector_confirmed']==2 and a['coverage']['accounting_confirmed']==0
    s['records'].reverse(); s['members'].reverse()
    assert view(s)==a


def test_source_metadata_changes_invalidate_cache_without_fabricating_release_time():
    s=store(); a=view(s)
    s['sources'][0]['locator']='corrected locator'
    assert view(s)['classification_hash']!=a['classification_hash']
    s['sources'][0]['published_at']='2026-11-01'
    with pytest.raises(ValueError,match='SOURCE_PUBLICATION_PRECISION_INVALID'): validate(s)


def test_unavailable_future_history_changes_archive_hash_not_old_calculation_identity():
    s=store();a=view(s)
    future=deepcopy(s['sources'][0]);future.update(source_id='future',sha256='b'*64,acquired_at='2026-11-10T00:00:00Z')
    s['sources'].append(future)
    r=deepcopy(s['records'][0]);r.update(record_id='future-revision',supersedes='record-1',source_refs=['future'],recorded_at='2026-11-10T00:00:00Z')
    s['records'].append(r);b=view(s)
    assert a['rows']==b['rows'] and a['sources']==b['sources']
    assert a['classification_hash']==b['classification_hash']
    assert a['history_hash']!=b['history_hash']


@pytest.mark.parametrize('field,value',[('issuer_id','OTHER'),('sic','1234'),('source_sha256','b'*64)])
def test_retained_evidence_cannot_be_substituted_between_issuers_or_concepts(field,value):
    from investment_system.research.sector_qgv_registry import MAPPING
    snapshot={'mapping_version':MAPPING,'members':['A'],'universe_id':'S','universe_version':'1','valuation_date':'2026-11-04',
        'classification_rule_version':'synthetic/1','rows':[{'company_id':'A','issuer_id':'I','mapping':None,
        'official_classification':{'system':'SEC_SIC','code':'7372','source_sha256':'a'*64,'source_url':'https://example.invalid',
        'observed_at':'2026-11-03T00:00:00Z'}}]}
    evidence={'issuer_id':'I','sic':'7372','source_sha256':'a'*64};evidence[field]=value
    with pytest.raises(ValueError,match='RETAINED_EVIDENCE_MISMATCH'):
        from_sector_snapshot(snapshot,{'A':evidence},source_sha256='c'*64,recorded_at='2026-11-07T00:00:00Z',data_kind='SYNTHETIC')
