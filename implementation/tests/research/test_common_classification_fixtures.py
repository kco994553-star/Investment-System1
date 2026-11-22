"""Published handoff cases: consumers can run the same expected outcomes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from investment_system.research.common_classification._core import digest
from investment_system.research.common_classification.catalog import current_taxonomy, dictionary
from investment_system.research.common_classification.records import append_review, from_sector_snapshot, resolve

FIXTURE=json.loads((Path(__file__).parents[2]/'docs/research/common_classification/fixtures.json').read_text())


@pytest.mark.parametrize('name',FIXTURE['record_cases'])
def test_shared_record_case(name):
    case=FIXTURE['record_cases'][name]; want=case['expected']
    if want.get('error'):
        with pytest.raises(ValueError,match=want['error']):
            resolve(case['store'],valuation_date=case['valuation_date'],knowledge_as_of=case['knowledge_as_of'])
        return
    result=resolve(case['store'],valuation_date=case['valuation_date'],knowledge_as_of=case['knowledge_as_of'])
    assert len(result['rows'])==want['member_count']
    row=result['rows'][0]
    assert row['sector']['status']==want['sector_status']
    assert row['industry']['status']==want['industry_status']
    if want['reason']: assert want['reason'] in row['sector']['reasons']
    if 'sector_id' in want: assert row['sector']['id']==want['sector_id']

def test_legacy_dictionary_hashes_preserved_current_taxonomy_uses_stable_ids_and_scopes():
    assert digest(dictionary('common-industry-dictionary/1'))=='fa764a4d520cd2817ff8c8e3f55f4de6ad0b767f739d311f4c1b5665564bb44e'
    assert digest(dictionary('common-industry-dictionary/2'))=='2ad03d247c30ce335612b69e70d69bab26959273b1e893cc8f71c8991634d861'
    current=current_taxonomy();by={r['id']:r for r in current['sectors']}
    assert current['name']=='투자시스템 공통 10섹터'
    assert set(by)==set(dictionary()['sectors'])
    assert by['TELECOMMUNICATIONS']['name']=='통신서비스'
    assert all(r['definition'] and r['includes'] and r['excludes'] and r['evidence_refs'] for r in by.values())
    assert current['classification_effect']=='NONE_DISPLAY_DEFINITION_ONLY'


def test_manifest_pins_original_fixtures_contract_and_dictionary():
    directory = Path(__file__).parents[2] / 'docs/research/common_classification'
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    assert {entry['path'] for entry in manifest['files']} == {'CONTRACT.md', 'fixtures.json', 'dictionary.json'}
    for entry in manifest['files']:
        data = (directory / entry['path']).read_bytes()
        assert len(data) == entry['size']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
    assert json.loads((directory / 'dictionary.json').read_bytes()) == dictionary()


def test_policy_registration_does_not_assign_unreviewed_company_inputs():
    path = Path(__file__).parents[1] / 'fixtures/common_classification/boundary-policy-v2.json'
    pack = json.loads(path.read_bytes())
    for case in pack['cases']:
        snapshot = case['snapshot']
        store = from_sector_snapshot(snapshot, case['evidence'], source_sha256=digest(snapshot),
                                     recorded_at='2026-11-08T12:00:00Z', data_kind='SYNTHETIC',
                                     dictionary_version=pack['dictionary_version'])
        view = resolve(store, valuation_date=snapshot['valuation_date'], knowledge_as_of='2026-11-08T12:00:00Z')
        assert view['mapping_version'] == pack['mapping_version']
        assert view['rows'][0]['sector']['status'] == 'UNKNOWN'
        assert view['rows'][0]['accounting']['status'] == 'UNKNOWN'

        # The source fixture separates the initial SIC evidence from a reviewed assignment.
        # Exercise the record boundary with the fixture's pre-reviewed outcome as input.
        imported = deepcopy(store)
        record = imported['records'][0]
        record.update(record_id='review:' + case['case_id'], recorded_at='2026-11-09T12:00:00Z')
        for component, field in [('sector', 'sector_id'), ('accounting', 'accounting_template')]:
            value = case['expected'][field]
            if value is not None:
                record[component] = dict(id=value, status='CONFIRMED', reasons=[],
                                         evidence_refs=record['source_refs'][:])
        combined = append_review(store, imported, company_ids=snapshot['members'])
        current = resolve(combined, valuation_date=view['valuation_date'], knowledge_as_of=record['recorded_at'])
        assert current['rows'][0]['sector']['id'] == case['expected']['sector_id']
        assert current['rows'][0]['accounting']['id'] == case['expected']['accounting_template']
        previous = resolve(combined, valuation_date=view['valuation_date'], knowledge_as_of=view['knowledge_as_of'])
        assert previous['classification_hash'] == view['classification_hash']
