"""Price-free listing projection, independent pins and read-only old-sheet review."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from investment_system.research.sector_qgv import digest
from investment_system.research.population_public_listing import build_listing, sheet_difference, retain_listing
from investment_system.universe import universe_codes


DAY = '2026-11-13'
CUTOFF = DAY + 'T22:00:00Z'


def metadata(kind='SYNTHETIC_CURRENT'):
    return dict(source_kind=kind, data_kind='SYNTHETIC', population_id='SYNTHETIC:CURRENT',
        population_version='1', basis_date=DAY, apply_at='2026-11-16T14:30:00Z',
        mapping_day=DAY, input_cutoff=CUTOFF,
        null_reasons={})


def link(code, issuer='SYNTHETIC:ISSUER:1', security='SYNTHETIC:SECURITY:1'):
    return dict(company_id=code, issuer_id=issuer, issuer_status='VERIFIED',
        issuer_refs=['SYNTHETIC:ISSUER:PROOF'], security_id=security,
        identifier_type='SYNTHETIC_FIXED_SECURITY_ID', security_status='VERIFIED',
        security_refs=['SYNTHETIC:CLASS:PROOF'], share_class_id='SYNTHETIC:CLASS:1',
        representative_status='VERIFIED', representative_refs=['SYNTHETIC:REP:PROOF'],
        google_symbol=code, google_status='VERIFIED', google_refs=['SYNTHETIC:GOOGLE:PROOF'],
        record_id='SYNTHETIC:MAPPING:' + code, valid_from='2026-01-01', valid_to=None,
        available_at=CUTOFF)


def example(codes=('NYSE:SYN0', 'NYSE:SYN1'), links=None, meta=None):
    source=dict(schema='universe-codes/1', codes=list(codes))
    body=json.dumps(source, sort_keys=True).encode()
    links=[] if links is None else links
    return build_listing(body, metadata=meta or metadata(), links=links,
        expected_source_sha256=hashlib.sha256(body).hexdigest(), expected_links_hash=digest(links))


def test_current_official_keeps_legacy_payload_and_unknown_metadata_truthful():
    source=universe_codes.public_payload(); before=deepcopy(source)
    body=json.dumps(source).encode()
    meta=metadata('CURRENT_OFFICIAL');meta.update(data_kind='PUBLIC_CODE_LIST',population_id='Universe504',
        population_version=None,basis_date=None,apply_at=None,mapping_day=None,input_cutoff=None,
        null_reasons={k:'LEGACY_SOURCE_NOT_RECORDED' for k in
                      ('population_version','basis_date','apply_at','mapping_day','input_cutoff')})
    out=build_listing(body,metadata=meta,links=[],expected_source_sha256=hashlib.sha256(body).hexdigest(),expected_links_hash=digest([]))
    assert source == before and set(source) == {'schema','codes'}
    assert out['official_current'] is True and out['use_for_new_sheet'] is True
    assert out['code_rows'] == 504
    assert out['issuers'] is None and out['known_issuers'] == 0
    assert out['population_version'] is None and out['basis_date'] is None
    assert out['codes'] == source['codes']
    assert all(r['google_symbol'] is None for r in out['members'])
    assert out['members_hash'] == digest(sorted(source['codes']))


def test_two_code_rows_of_one_issuer_and_unknown_maps_are_preserved():
    codes=('NYSE:SYN0','NYSE:SYN1')
    a=link(codes[0]);b=link(codes[1],security='SYNTHETIC:SECURITY:2')
    b['representative_status']='UNCONFIRMED';b['google_status']='UNCONFIRMED'
    result=example(codes,[a,b])
    assert result['code_rows'] == 2 and result['issuers'] == 1
    assert len(result['members']) == 2
    assert result['members'][0]['representative_security_id'] == a['security_id']
    assert result['members'][1]['representative_security_id'] is None
    assert result['members'][1]['google_symbol'] is None
    assert result['members'][1]['requested_google_symbol'] == codes[1]
    assert result['official_current'] is False  # A synthetic current-list example is not an actual official list.


def test_existing_top500_result_is_only_a_candidate_and_never_leaks_cap_inputs():
    root=Path(__file__).parents[2]
    source=json.loads((root/'tests/fixtures/qgv555-preview/top500-result.json').read_bytes())
    links=[link('NYSE:SYN'+str(i),r['issuer_id'],r['representative_security_id']) for i,r in enumerate(source['members'])]
    meta=metadata('TOP500_RESEARCH_CANDIDATE');meta.update(population_id=source['population_id'],
        population_version=source['population_version'],basis_date=source['evaluation_day'],apply_at=source['apply_at'],
        mapping_day=source['evaluation_day'],input_cutoff=source['input_cutoff'])
    for row in links: row['available_at']=source['input_cutoff']
    body=json.dumps(source).encode()
    result=build_listing(body,metadata=meta,links=links,expected_source_sha256=hashlib.sha256(body).hexdigest(),expected_links_hash=digest(links))
    assert result['status']=='CANDIDATE' and result['official_current'] is False
    assert result['use_for_new_sheet'] is False
    assert result['issuers']==3 and result['code_rows']==3
    assert result['source_result_hash']==source['result_hash']
    assert result['members_hash']!=source['members_hash']
    text=json.dumps(result)
    for field in ('market_cap_usd','price','shares','selection_evidence','ranked','retained_confirmed'):
        assert '"'+field+'"' not in text
    assert result['public_publication_authorized'] is False
    assert result['visibility']=='AUTHENTICATED_RESEARCH'
    future=deepcopy(meta);future['mapping_day']='2026-11-05'
    with pytest.raises(ValueError,match='TOP500_LIST_SOURCE_CONTEXT'):
        build_listing(body,metadata=future,links=links,expected_source_sha256=hashlib.sha256(body).hexdigest(),expected_links_hash=digest(links))


@pytest.mark.parametrize('defect', ['source_hash','links_hash','duplicate','outside','current_wrong_id'])
def test_integrity_and_roster_conflicts_fail_closed(defect):
    source=dict(schema='universe-codes/1',codes=['NYSE:SYN0'])
    body=json.dumps(source).encode();rows=[link('NYSE:SYN0')];meta=metadata()
    sh=hashlib.sha256(body).hexdigest();mh=digest(rows)
    if defect=='source_hash':sh='0'*64
    if defect=='links_hash':mh='0'*64
    if defect=='duplicate':rows.append(deepcopy(rows[0]));mh=digest(rows)
    if defect=='outside':rows[0]['company_id']='NYSE:SYN9';mh=digest(rows)
    if defect=='current_wrong_id':meta['source_kind']='CURRENT_OFFICIAL'
    with pytest.raises(ValueError):
        build_listing(body,metadata=meta,links=rows,expected_source_sha256=sh,expected_links_hash=mh)


@pytest.mark.parametrize('defect', ['expired','future','internal_seed','issuer_as_security'])
def test_mapping_claims_need_the_right_date_and_security_basis(defect):
    row=link('NYSE:SYN0')
    if defect=='expired':row['valid_to']=DAY
    if defect=='future':row['available_at']='2026-11-14T01:00:00Z'
    if defect=='internal_seed':row['identifier_type']='INTERNAL_LISTING_SEED'
    if defect=='issuer_as_security':row['security_id']=row['issuer_id']
    result=example(('NYSE:SYN0',),[row])
    member=result['members'][0]
    assert member['security_id'] is None and member['google_symbol'] is None
    assert member['mapping_reasons']


def test_old_sheet_diff_is_a_read_only_review_not_automatic_migration():
    listing=example();before=deepcopy(listing)
    rows=['NYSE:SYN0','NYSE:SYN9'];old=dict(population_id=listing['population_id'],population_version='old',members_hash=digest(sorted(rows)))
    result=sheet_difference(listing,rows,saved_identity=old,expected_listing_hash=listing['list_hash'])
    assert result['state']=='REVIEW_REQUIRED'
    assert 'POPULATION_VERSION_MISMATCH' in result['reasons']
    assert result['added_codes']==['NYSE:SYN1'] and result['removed_codes']==['NYSE:SYN9']
    assert result['action']=='USER_SELECTED_UPDATE_ONLY'
    assert result['writes']==0 and result['touches_trades_or_quotes'] is False
    assert listing==before and rows==['NYSE:SYN0','NYSE:SYN9']
    plain=sheet_difference(listing,listing['codes'],saved_identity=None,expected_listing_hash=listing['list_hash'])
    assert plain['state']=='UNVERSIONED_LIST_MATCH'
    assert 'SHEET_POPULATION_IDENTITY_UNRECORDED' in plain['reasons']


def test_retain_previous_preserves_source_dates_and_inner_listing_hash():
    listing=example();before=deepcopy(listing)
    retained=retain_listing(listing,expected_previous_hash=listing['list_hash'],failure='SOURCE_READ_FAILED')
    assert retained['status']=='RETAINED_PREVIOUS'
    assert retained['listing']==before
    assert retained['listing']['list_hash']==listing['list_hash']
    assert retained['failure']=='SOURCE_READ_FAILED'
    assert listing==before
    with pytest.raises(ValueError):retain_listing(listing,expected_previous_hash='0'*64,failure='SOURCE_READ_FAILED')


@pytest.mark.parametrize('extra', [{'market_cap_usd':123}, {'basis_date':{'private_note':'not a reason code'}}])
def test_public_unknown_reasons_cannot_carry_arbitrary_input(extra):
    meta=metadata();meta['null_reasons']=extra
    with pytest.raises(ValueError):example(meta=meta)


def test_matching_null_versions_never_become_a_verified_current_version():
    meta=metadata();meta['population_version']=None
    meta['null_reasons']={'population_version':'LEGACY_SOURCE_NOT_RECORDED'}
    listing=example(meta=meta)
    saved=dict(population_id=listing['population_id'],population_version=None,members_hash=listing['members_hash'])
    result=sheet_difference(listing,listing['codes'],saved_identity=saved,expected_listing_hash=listing['list_hash'])
    assert result['state']=='UNVERSIONED_LIST_MATCH'
    assert 'CURRENT_POPULATION_VERSION_UNRECORDED' in result['reasons']


def test_retain_rejects_a_candidate_presented_as_a_previous_confirmed_list():
    listing=example();listing['status']='CANDIDATE'
    listing['list_hash']=digest({k:v for k,v in listing.items() if k!='list_hash'})
    with pytest.raises(ValueError):retain_listing(listing,expected_previous_hash=listing['list_hash'],failure='SOURCE_READ_FAILED')


def test_paths_or_query_strings_do_not_become_public_mapping_identifiers():
    row=link('NYSE:SYN0');row['record_id']='/private/notes?secret=value'
    out=example(('NYSE:SYN0',),[row])
    assert out['members'][0]['mapping_record_id'] is None
    assert 'secret=value' not in json.dumps(out)
    row=link('NYSE:SYN0');row['google_symbol']='NYSE:SYN0?private=value'
    out=example(('NYSE:SYN0',),[row])
    assert out['members'][0]['google_symbol'] is None


@pytest.mark.parametrize('conflict', ['representative','google_symbol'])
def test_contradictory_verified_links_are_not_resolved_by_picking_a_row(conflict):
    a=link('NYSE:SYN0');b=link('NYSE:SYN1',security='SYNTHETIC:SECURITY:2')
    if conflict=='google_symbol':
        b['representative_status']='UNCONFIRMED'
        b['google_symbol']=a['google_symbol']
    with pytest.raises(ValueError):example(links=[a,b])


def test_bad_metadata_time_returns_a_fixed_reason_not_input_text():
    meta=metadata();meta['input_cutoff']='not-a-time-private-note'
    with pytest.raises(ValueError,match='PUBLIC_LIST_TIME') as e:example(meta=meta)
    assert 'private-note' not in str(e.value)


def test_generated_main_cases_match_schema_and_frozen_bytes():
    import importlib.util
    import jsonschema
    root=Path(__file__).parents[2]
    spec=importlib.util.spec_from_file_location('population_examples',root/'tools/generate_population_listing_examples.py')
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    expected=tool.examples();folder=root/'tests/fixtures/population-listing'
    body=(folder/'examples.json').read_bytes()
    assert json.loads(body)==expected
    manifest=json.loads((folder/'manifest.json').read_bytes())
    assert manifest['data_kind']=='SYNTHETIC'
    assert manifest['files']==[dict(path='examples.json',bytes=len(body),sha256=hashlib.sha256(body).hexdigest())]
    schema=json.loads((root/'docs/research/sector_qgv/population-public-list-contract.json').read_bytes())
    for case in expected['cases']:
        result=case['result']
        ref='retained_response' if case['case']=='failed_refresh' else 'sheet_review' if case['case'] in ('old_sheet','matching_unversioned_sheet') else 'listing'
        jsonschema.validate(result,{**schema,'$ref':'#/$defs/'+ref})
    assert expected['cases'][0]['result']['code_rows']==3
    assert expected['cases'][0]['result']['issuers']==2
    assert expected['cases'][0]['result']['verified_google_mappings']==2
    assert expected['cases'][1]['result']['added_codes']==['NYSE:SYN1','NYSE:SYN2']
    assert expected['cases'][1]['result']['removed_codes']==['NYSE:SYN9']
    assert expected['cases'][-1]['result']['status']=='CANDIDATE'
