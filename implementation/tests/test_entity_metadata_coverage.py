"""Entity search metadata: CIK-bound, provenance-carrying, never an investment input."""
from copy import deepcopy
import json

import pytest

from investment_system.product import entity_metadata as em
from investment_system.product.entity_catalog import NAV_ENTITIES, entity_catalog
from investment_system.product.web_mvp import build, demo_bundle, repository_bundle

U, SHA, PRIOR = em.frozen_universe()
CIK = {m['company_id']: m['cik'] for m in U['members']}
RESERVED = [e['canonical_label'] for e in NAV_ENTITIES] + ['CPI', '반도체']


def sources():
    """Small source extract in the committed format (values mirror public SEC/Wikidata records)."""
    return {
        'sec_submissions': {'records': {
            CIK['nvda']: {'name': 'NVIDIA CORP', 'tickers': ['NVDA'], 'formerNames': []},
            CIK['meta']: {'name': 'Meta Platforms, Inc.', 'tickers': ['META'], 'formerNames': [
                {'name': 'FACEBOOK INC', 'from': '2012-02-01T00:00:00.000Z', 'to': '2021-10-28T00:00:00.000Z'}]},
            CIK['googl']: {'name': 'Alphabet Inc.', 'tickers': ['GOOGL', 'GOOG'], 'formerNames': []},
        }},
        'sec_company_tickers': {'rows': [{'cik': CIK['meta'], 'ticker': 'META', 'title': 'Meta Platforms, Inc.'}]},
        'wikidata': {'rows': [
            {'item': 'Q182477', 'cik': CIK['nvda'], 'en_label': 'Nvidia', 'ko_label': '엔비디아',
             'en_aliases': ['NVIDIA Corporation', 'MS', 'Semiconductor'], 'ko_aliases': ['Nvidia'], 'tickers': []},
            {'item': 'Q380', 'cik': CIK['meta'], 'en_label': 'Meta Platforms', 'ko_label': '메타 플랫폼스',
             'en_aliases': ['Facebook, Inc.', 'Shared Label', 'Owned by someone@example since 2001 ' * 3], 'ko_aliases': ['페이스북'],
             'tickers': [{'exchange': 'Q82059', 'symbol': 'FB', 'end': '2022-06-09T00:00:00Z'},
                         {'exchange': 'Q151139', 'symbol': 'FB2A', 'end': '2022-06-09T00:00:00Z'}]},
            {'item': 'Q95', 'cik': CIK['googl'], 'en_label': 'Google', 'ko_label': None,
             'en_aliases': ['Shared Label'], 'ko_aliases': [], 'tickers': []},
        ]},
        'kis_master': {'rows': [
            {'exchange': 'NAS', 'symbol': 'GOOG', 'ko_name': '알파벳 C', 'en_name': 'ALPHABET INC CL C', 'security_type': '2'},
            {'exchange': 'NAS', 'symbol': 'META', 'ko_name': '엉뚱한 이름', 'en_name': 'OTHER LISTING CORP', 'security_type': '2'},
        ]},
    }


def registry():
    return em.build_registry(U, sources(), SHA, PRIOR, RESERVED)


def index(cat):
    out = {}
    for e in cat['entities']:
        labels = [e.get('ticker'), e['canonical_label'], *e.get('localized_names', {}).values(),
                  *(a for v in e.get('aliases', {}).values() for a in v), *e.get('historical_names', []),
                  *e.get('historical_tickers', [])]
        for label in labels:
            if label:
                out.setdefault(em.normalize(label), set()).add(e['entity_type'] + ':' + e['canonical_id'])
    return out


def test_builder_is_deterministic_and_keyed_by_existing_ids():
    a, b = registry(), registry()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert set(a['records']) == {m['company_id'] for m in U['members']}
    assert all(a['records'][c]['cik'] == CIK[c] for c in a['records'])
    assert a['universe_sha256'] == SHA and a['role'] == 'SEARCH_PRESENTATION_ONLY'


def test_every_kept_value_has_provenance():
    for rec in registry()['records'].values():
        vals = [*rec['common_names'].values(), *(v for vs in rec['aliases'].values() for v in vs),
                *rec['historical_names'], *rec['historical_tickers']] + ([rec['official_name']] if rec['official_name'] else [])
        assert all(v['source'] and v['value'] for v in vals)


def test_ticker_english_korean_alias_historical_resolve_to_same_canonical_entity():
    cat = entity_catalog(repository_bundle(), metadata=registry())
    idx = index(cat)
    for label in ['META', 'Meta Platforms, Inc.', 'Meta Platforms', '메타 플랫폼스', '페이스북', 'FACEBOOK INC', 'FB']:
        assert idx[em.normalize(label)] == {'COMPANY:meta'}, label
    for label in ['NVDA', 'NVIDIA Corporation', 'Nvidia', '엔비디아']:
        assert idx[em.normalize(label)] == {'COMPANY:nvda'}, label
    assert idx[em.normalize('GOOG')] == {'COMPANY:googl'}
    assert em.normalize('알파벳 C') not in idx        # curated googl ko-KR list is kept exactly (fill-only)
    meta = next(e for e in cat['entities'] if e['canonical_id'] == 'meta')
    assert meta['historical_names'] == ['FACEBOOK INC'] and meta['historical_tickers'] == ['FB']
    assert meta['localized_names'] == {'en-US': 'Meta Platforms', 'ko-KR': '메타 플랫폼스'}
    assert 'und' not in meta['localized_names']


def test_no_duplicate_entities_and_existing_precedence_kept():
    base = entity_catalog(repository_bundle(), metadata=False)
    cat = entity_catalog(repository_bundle(), metadata=registry())
    keys = [(e['entity_type'], e['canonical_id']) for e in cat['entities']]
    assert len(keys) == len(set(keys)) == len(base['entities'])
    assert [k for k in keys] == [(e['entity_type'], e['canonical_id']) for e in base['entities']]
    nvda = next(e for e in cat['entities'] if e['canonical_id'] == 'nvda')
    assert nvda['canonical_label'] == 'NVIDIA Corporation'          # curated identity label kept
    assert nvda['localized_names'] == {'en-US': 'NVIDIA', 'ko-KR': '엔비디아'}
    assert nvda['aliases']['ko-KR'] == ['엔비디아'] and nvda['aliases']['en-US'] == ['NVIDIA']
    b = repository_bundle()
    b['companies'] = [dict(c, historical_names=['Producer name']) if c['company_id'] == 'meta' else c for c in b['companies']]
    meta = next(e for e in entity_catalog(b, metadata=registry())['entities'] if e['canonical_id'] == 'meta')
    assert meta['historical_names'] == ['Producer name'] and meta['historical_tickers'] == ['FB']


def test_false_positive_protection():
    reg = registry()
    rej = {(r['company_id'], r['value'], r['reason']) for r in reg['rejections']}
    assert ('nvda', 'MS', 'OTHER_ENTITY_TICKER') in rej               # Morgan Stanley's ticker
    assert ('nvda', 'Semiconductor', 'RESERVED_NAVIGATION_LABEL') in rej
    assert ('nvda', 'Nvidia', 'NO_HANGUL') in rej                     # Latin text is not a ko-KR name
    assert ('meta', '엉뚱한 이름', 'LISTING_NAME_MISMATCH') in rej     # listing name cross-check
    assert any(c == 'meta' and r == 'IMPLAUSIBLE_LABEL' for c, v, r in rej)  # vandalised community alias
    assert {('meta', 'Shared Label'), ('googl', 'Shared Label')} <= {(c, v) for c, v, r in rej if r == 'AMBIGUOUS_ACROSS_ENTITIES'}
    meta = reg['records']['meta']
    assert [t['value'] for t in meta['historical_tickers']] == ['FB']  # non-US venue qualifier ignored
    idx = index(entity_catalog(repository_bundle(), metadata=reg))
    assert idx[em.normalize('MS')] == {'COMPANY:ms'}
    assert 'shared label' not in idx


def test_ambiguous_wikidata_cik_is_rejected_not_guessed():
    s = sources()
    s['wikidata']['rows'].append({'item': 'Q999', 'cik': CIK['nvda'], 'en_label': 'Other', 'ko_label': '다른',
                                  'en_aliases': [], 'ko_aliases': [], 'tickers': []})
    reg = em.build_registry(U, s, SHA, PRIOR, RESERVED)
    assert reg['records']['nvda']['common_names'] == {}
    assert any(r['reason'] == 'AMBIGUOUS_CIK_ITEMS' for r in reg['rejections'])


def test_registry_is_bound_to_universe_identity_and_cik():
    reg = registry()
    b = repository_bundle()
    wrong = deepcopy(reg)
    wrong['records']['meta']['cik'] = '0000000001'
    meta = next(e for e in entity_catalog(b, metadata=wrong)['entities'] if e['canonical_id'] == 'meta')
    assert 'metadata_provenance' not in meta and meta['historical_names'] == []
    other = deepcopy(reg)
    other['universe_id'] = 'uni_other'
    assert entity_catalog(b, metadata=other) == entity_catalog(b, metadata=False)


def test_metadata_never_changes_producer_payload(tmp_path):
    b = demo_bundle(repository_bundle())
    before = deepcopy(b)
    build(tmp_path / 'with', bundle=b)
    assert b == before
    assert json.loads((tmp_path / 'with' / 'data.json').read_text()) == before


def test_malformed_source_fails_closed():
    with pytest.raises(KeyError):
        em.build_registry(U, {'wikidata': {'rows': [{'cik': CIK['nvda']}]}}, SHA)


def test_committed_registry_rebuilds_byte_identically_from_committed_sources():
    path = em.METADATA_DIR / em.REGISTRY_NAME
    if not path.exists():
        pytest.skip('registry not ingested yet')
    from investment_system.product.entity_catalog import NAV_ENTITIES as NAV
    reserved = [x for e in NAV for x in [e['canonical_label'], *e.get('localized_names', {}).values(),
                *(v for vs in e.get('aliases', {}).values() for v in vs)]]
    reg = em.build_registry(U, em.load_sources(), SHA, PRIOR, reserved)
    text = json.dumps(reg, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    assert text == path.read_text(encoding='utf-8')
    cov = em.coverage(entity_catalog(repository_bundle()), U)
    assert cov['n_company_entities'] == 500 and cov['ticker'] == 500 and not cov['missing_entities']
