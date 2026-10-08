"""User-owned immutable TARGET v0 source; identity evidence remains unresolved.

The source-subset parser and validators below are test utilities only. They do not
create a production reader, security ID, source admission or investment formula.
"""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

import pytest

IMPL = Path(__file__).resolve().parents[1]
TARGET = IMPL / 'docs/portfolio_target_owner/TARGET_v0.yaml'
SECURITY_MAP = IMPL / 'docs/security_map19_owner/TARGET_v0_SECURITY_MAP.json'
TARGET_SHA256 = 'a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b'
USER_CLOCK = '2026-10-08T20:37:00+09:00'
MEMBERS = {
    'semi_equipment': ['ASML Holding', 'Lam Research', 'KLA Corporation', 'Tokyo Electron', '한미반도체'],
    'ai_semi': ['NVIDIA', 'Advanced Micro Devices', 'Broadcom', 'Qualcomm', 'Intel'],
    'big_tech': ['Microsoft', 'Alphabet', 'Amazon'],
    'other_industrial': ['RTX Corporation', 'Stryker', 'Eaton', 'Hubbell', 'GE Vernova', 'Rockwell Automation'],
}
USER_CHOICES = {
    'Tokyo Electron': ('8035', 'USER_DECIDED: TSE (Tokyo, 8035)'),
    '한미반도체': ('042700', 'USER_DECIDED: KRX (042700)'),
    'Alphabet': ('GOOGL', 'USER_DECIDED: Class A (GOOGL)'),
}
_SCALAR = r'(?:"(?:[^"\\]|\\.)*"|[^,{}]+?)'
_FLOW = re.compile(
    r'      - \{ label:\s*(' + _SCALAR + r'),\s*ticker_hint:\s*(' + _SCALAR
    + r'),\s*listing:\s*(' + _SCALAR + r'),\s*weight_units:\s*(' + _SCALAR + r')\s*\}'
)


def _scalar(value):
    value = value.strip()
    assert value, 'source scalar must be present'
    if value.startswith('"'):
        decoded = json.loads(value)
        assert type(decoded) is str, 'quoted source scalar must be a string'
        return decoded
    if value in ('true', 'false'):
        return value == 'true'
    if re.fullmatch(r'-?\d+', value):
        return int(value)
    assert not any(c in value for c in '{}[]"\t#:'), 'unsupported source scalar shape'
    assert value[0] not in '!&*', 'unsupported YAML tag or alias'
    return value


def _parse_source(text):
    """Only the explicit block/flow shape in the pinned user file is accepted."""
    document, section, theme = {}, None, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        # The sole inline comment is on the unquoted total_units integer.
        if line.startswith('total_units:'):
            line = line.partition('#')[0].rstrip()
        if not line.startswith(' '):
            match = re.fullmatch(r'([a-z_]+):(?: (.*))?', line)
            assert match, 'unsupported root source shape'
            key, value = match.groups()
            assert key not in document, 'duplicate root key'
            if value is None:
                assert key in ('owner', 'provenance', 'themes'), 'unsupported source block'
                document[key] = [] if key == 'themes' else {}
                section = key
            else:
                document[key] = _scalar(value)
                section = None
        elif section in ('owner', 'provenance'):
            match = re.fullmatch(r'  ([a-z_]+): (.+)', line)
            assert match, 'unsupported metadata source shape'
            key, value = match.groups()
            assert key not in document[section], 'duplicate metadata key'
            document[section][key] = _scalar(value)
        elif section == 'themes' and line.startswith('  - theme_id: '):
            theme = {'theme_id': _scalar(line[len('  - theme_id: '):])}
            document['themes'].append(theme)
        elif section == 'themes' and line.startswith('    '):
            flow = _FLOW.fullmatch(line)
            if flow:
                assert theme is not None and 'holdings' in theme, 'holding outside holdings block'
                theme['holdings'].append(dict(zip(('label', 'ticker_hint', 'listing', 'weight_units'),
                                                  map(_scalar, flow.groups()))))
            else:
                match = re.fullmatch(r'    ([a-z_]+):(?: (.+))?', line)
                assert match and theme is not None, 'unsupported theme source shape'
                key, value = match.groups()
                assert key not in theme, 'duplicate theme field'
                if value is None:
                    assert key == 'holdings', 'unsupported theme block'
                    theme[key] = []
                else:
                    theme[key] = _scalar(value)
        else:
            raise AssertionError('unsupported source indentation or shape')
    assert set(document) == {'schema', 'version', 'status', 'owner', 'provenance', 'effective_at',
                             'available_at', 'unit', 'total_units', 'cash_units', 'themes'}, 'source root fields'
    assert set(document['owner']) == {'role', 'note'}, 'source owner fields'
    assert set(document['provenance']) == {'derived_from', 'adopted_by', 'adopted_at', 'adoption_note'}, 'source provenance fields'
    for item in document['themes']:
        assert set(item) == {'theme_id', 'label', 'target_units', 'holdings'}, 'source theme fields'
    return document


def _target():
    assert TARGET.is_file(), 'adopted user TARGET source file must exist'
    return _parse_source(TARGET.read_text(encoding='utf-8'))


def _mapping():
    assert SECURITY_MAP.is_file(), 'unresolved TARGET security map must exist'
    return json.loads(SECURITY_MAP.read_text(encoding='utf-8'))


def _integer(value):
    assert type(value) is int, 'weight/count/index must be a strict integer, never bool'


def _validate_target(document):
    assert document['schema'] == 'PORTFOLIO_TARGET/0.1' and document['version'] == 'v0'
    assert document['status'] == 'ADOPTED' and document['unit'] == 'weight_units'
    assert document['owner']['role'] == document['provenance']['adopted_by'] == 'USER', 'user owner'
    for clock in (document['effective_at'], document['available_at'], document['provenance']['adopted_at']):
        assert clock == USER_CLOCK and datetime.fromisoformat(clock).tzinfo is not None, 'user clock'
    _integer(document['total_units'])
    _integer(document['cash_units'])
    assert document['total_units'] == 10000 and document['cash_units'] == 0, 'whole target/cash units'
    seen_themes, seen_holdings = set(), set()
    for theme in document['themes']:
        assert theme['theme_id'] not in seen_themes, 'duplicate theme membership'
        seen_themes.add(theme['theme_id'])
        _integer(theme['target_units'])
        for holding in theme['holdings']:
            assert holding['label'] not in seen_holdings, 'duplicate holding membership'
            seen_holdings.add(holding['label'])
            _integer(holding['weight_units'])
            assert type(holding['ticker_hint']) is str, 'ticker hint must remain a string, not identity'
            if holding['label'] in USER_CHOICES:
                assert (holding['ticker_hint'], holding['listing']) == USER_CHOICES[holding['label']], 'user listing choice'
            else:
                assert holding['listing'] == 'UNRESOLVED_BY_AGENT', 'unresolved listing remains unresolved'
        assert theme['target_units'] == sum(h['weight_units'] for h in theme['holdings']), 'theme units sum'
    assert seen_themes == set(MEMBERS) and len(seen_holdings) == 19, 'exact theme/holding roster'
    assert sum(t['target_units'] for t in document['themes']) + document['cash_units'] == document['total_units'], 'whole units sum'
    for theme in document['themes']:
        assert [h['label'] for h in theme['holdings']] == MEMBERS[theme['theme_id']], 'user theme membership'


def _validate_mapping(mapping, document):
    source = mapping['user_target_source']
    assert source['sha256'] == TARGET_SHA256 and source['bytes'] == 4463, 'map source hash/bytes'
    assert source['repository_path'] == 'implementation/docs/portfolio_target_owner/TARGET_v0.yaml', 'map source path'
    assert source['version'] == 'v0' and source['content_modified'] is False, 'map source version'
    assert source['effective_at'] == source['available_at'] == source['provenance']['adopted_at'] == USER_CLOCK, 'map user clock'
    assert source['owner']['role'] == source['provenance']['adopted_by'] == 'USER', 'map user owner'
    counts = mapping['counts']
    for value in counts.values():
        _integer(value)
    assert counts['roster'] == 19 and counts['resolved'] == 0 and counts['unresolved'] == 19, 'mapping unresolved counts'
    assert counts['existing_approved_security_ids_found'] == counts['new_ids_generated'] == 0, 'no admitted or generated IDs'
    assert mapping['source_admission'] is False, 'map source admission forbidden'
    rows = mapping['rows']
    assert len(rows) == 19, 'mapping row count'
    index = 0
    for i, theme in enumerate(document['themes']):
        for j, holding in enumerate(theme['holdings']):
            row = rows[index]
            _integer(row['row_index'])
            assert row['row_index'] == index and row['user_source_pointer'] == f'/themes/{i}/holdings/{j}', 'mapping source pointer'
            assert row['theme_id'] == theme['theme_id'] and row['theme_label'] == theme['label'], 'mapping theme membership'
            assert row['owner_listing_input'] == holding, 'mapping source holding/listing input'
            assert row['user_instrument_selection_supplied'] is (holding['label'] in USER_CHOICES), 'existing user listing selection'
            assert row['status'] == 'UNRESOLVED' and row['source_admission'] is False, 'unresolved row admission'
            for field in ('existing_approved_security_id', 'security_id', 'issuer_id', 'listing_id', 'reviewed_company_link'):
                assert row[field] is None, 'unresolved identity must remain null'
            assert row['user_choices_reopened'] is False, 'user choices must not be reopened'
            assert row['legacy_company_reference']['source_pin'] == 'legacy_company_registry', 'company namespace is reference evidence'
            assert row['legacy_company_reference']['json_scope'] == 'OFFICIAL_PORTFOLIO_V11 authored-company reference; not an admitted SecurityRecord'
            assert row['existing_chart_observation']['source_pin'] == 'chart_existing_fact_readiness', 'existing partial evidence retained'
            assert row['precise_blocked_fact'] and row['missing_common_admission_evidence'], 'unresolved reason/evidence retained'
            index += 1


def test_target_v0_user_bytes_are_immutable():
    assert TARGET.is_file(), 'adopted user TARGET source file must exist'
    raw = TARGET.read_bytes()
    assert len(raw) == 4463 and hashlib.sha256(raw).hexdigest() == TARGET_SHA256


def test_target_v0_owner_and_clocks_are_literal_user_inputs():
    document = _target()
    _validate_target(document)
    assert document['provenance']['derived_from'] == 'QGV Portfolio Specification v1.1 §2 (2026-09-14, 사용자 작성)'
    assert datetime.fromisoformat(document['available_at']) > datetime.fromisoformat('2026-09-14T00:00:00+09:00')


def test_target_v0_theme_totals_and_unique_roster():
    document = _target()
    _validate_target(document)
    assert {t['theme_id']: t['target_units'] for t in document['themes']} == {
        'semi_equipment': 3000, 'ai_semi': 2500, 'big_tech': 2000, 'other_industrial': 2500}


def test_target_v0_quoted_listing_and_leading_zero_hints_survive_parsing():
    holdings = {h['label']: h for t in _target()['themes'] for h in t['holdings']}
    for label, choice in USER_CHOICES.items():
        assert (holdings[label]['ticker_hint'], holdings[label]['listing']) == choice
    assert type(holdings['한미반도체']['ticker_hint']) is str and holdings['한미반도체']['ticker_hint'].startswith('0')
    with pytest.raises(AssertionError, match='unsupported'):
        _parse_source(TARGET.read_text() + '\nunknown_block:\n  value: 1\n')
    invalid_flow = TARGET.read_text().replace('"USER_DECIDED: Class A (GOOGL)"', 'USER_DECIDED: Class A (GOOGL)')
    with pytest.raises(AssertionError, match='unsupported'):
        _parse_source(invalid_flow)


def test_target_v0_security_mapping_keeps_all_19_unresolved():
    _validate_mapping(_mapping(), _target())


def test_target_v0_rejects_changed_theme_sum():
    document = _target()
    document['themes'][0]['holdings'][0]['weight_units'] += 1
    with pytest.raises(AssertionError, match='theme units sum'):
        _validate_target(document)


def test_target_v0_rejects_changed_whole_sum():
    document = _target()
    document['themes'][0]['holdings'][0]['weight_units'] += 1
    document['themes'][0]['target_units'] += 1
    with pytest.raises(AssertionError, match='whole units sum'):
        _validate_target(document)


def test_target_v0_rejects_noninteger_and_boolean_weights():
    for bad in (True, False, 10000.0, '10000'):
        for scope in ('total', 'cash', 'theme', 'holding'):
            document = _target()
            if scope == 'total': document['total_units'] = bad
            elif scope == 'cash': document['cash_units'] = bad
            elif scope == 'theme': document['themes'][0]['target_units'] = bad
            else: document['themes'][0]['holdings'][0]['weight_units'] = bad
            with pytest.raises(AssertionError, match='strict integer'):
                _validate_target(document)


def test_target_v0_rejects_duplicate_and_reassigned_membership():
    document = _target()
    document['themes'][1]['theme_id'] = document['themes'][0]['theme_id']
    with pytest.raises(AssertionError, match='duplicate theme'):
        _validate_target(document)
    document = _target()
    document['themes'][1]['holdings'][0]['label'] = document['themes'][0]['holdings'][0]['label']
    with pytest.raises(AssertionError, match='duplicate holding'):
        _validate_target(document)
    document = _target()
    a, b = document['themes'][0]['holdings'][0], document['themes'][1]['holdings'][0]
    for key in ('label', 'ticker_hint', 'listing'):
        a[key], b[key] = b[key], a[key]
    with pytest.raises(AssertionError, match='user theme membership'):
        _validate_target(document)  # both integer sums still agree: membership alone changed


def test_target_v0_rejects_rewritten_user_listing_choices():
    for label in USER_CHOICES:
        document = _target()
        holding = next(h for t in document['themes'] for h in t['holdings'] if h['label'] == label)
        holding['listing'] = 'UNRESOLVED_BY_AGENT'
        with pytest.raises(AssertionError, match='user listing choice'):
            _validate_target(document)


def test_target_v0_rejects_owner_changes_and_backdated_clocks():
    for key in ('effective_at', 'available_at'):
        document = _target()
        document[key] = '2026-09-14T00:00:00+09:00'
        with pytest.raises(AssertionError, match='user clock'):
            _validate_target(document)
    document = _target()
    document['owner']['role'] = 'AGENT'
    with pytest.raises(AssertionError, match='user owner'):
        _validate_target(document)


def test_target_v0_rejects_fabricated_identity_and_admission():
    for field in ('existing_approved_security_id', 'security_id', 'issuer_id', 'listing_id', 'reviewed_company_link'):
        mapping = _mapping()
        mapping['rows'][0][field] = 'FABRICATED_ID'
        with pytest.raises(AssertionError, match='identity must remain null'):
            _validate_mapping(mapping, _target())
    for field in ('source_admission', 'user_choices_reopened'):
        mapping = _mapping()
        mapping['rows'][0][field] = True
        with pytest.raises(AssertionError):
            _validate_mapping(mapping, _target())


def test_target_v0_rejects_map_source_and_roster_divergence():
    original = _mapping()
    variants = []
    changed = deepcopy(original); changed['user_target_source']['sha256'] = '0' * 64; variants.append(changed)
    changed = deepcopy(original); changed['user_target_source']['available_at'] = '2026-09-14T00:00:00+09:00'; variants.append(changed)
    changed = deepcopy(original); changed['rows'].pop(); variants.append(changed)
    changed = deepcopy(original); changed['counts']['resolved'] = True; variants.append(changed)
    changed = deepcopy(original); changed['rows'][0]['user_source_pointer'] = '/themes/0/holdings/1'; variants.append(changed)
    changed = deepcopy(original); changed['rows'][0]['theme_id'] = 'ai_semi'; variants.append(changed)
    changed = deepcopy(original); changed['rows'][3]['owner_listing_input']['listing'] = 'UNRESOLVED_BY_AGENT'; variants.append(changed)
    for changed in variants:
        with pytest.raises(AssertionError):
            _validate_mapping(changed, _target())
