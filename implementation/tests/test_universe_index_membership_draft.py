"""DRAFT contract tests for the index-following Universe rule (B-1, docs/daily_data_pipeline/UNIVERSE_INDEX_FOLLOWING_20261023.md).

The module `investment_system.universe.index_membership` does not exist yet; these tests are skipped until it does.
Synthetic codes, CIKs and dates only (no real index data, no prices).

Expected API (design §5-2/5-3):
- validate_membership(payload) -> list of reason codes ([] = usable)
- membership_at(payload, day) -> (codes: list[str], universe_version: str)
- code_aliases(payload, day) -> {old_code: new_code} for CODE_CHANGE events effective on or before `day`
- carry_rows(kept_records, codes, aliases) -> {code: row} (kept row moved to the new code when the CIK is the same)
- universe_changes(payload, day) -> public price-free change list (no values)
"""
from datetime import date
import copy

import pytest

im = pytest.importorskip('investment_system.universe.index_membership')

A, B, C, D, X = 'NYSE:AAA', 'NASDAQ:BBB', 'NYSE:CCC', 'NYSE:DDD', 'NASDAQ:XXX'
CIK = {A: '0000000001', B: '0000000002', C: '0000000003', D: '0000000004', X: '0000000009'}
SRC = 'https://press.spglobal.com/2099-01-01-synthetic'


def payload():
    return {
        'schema': 'universe-membership/1',
        'index': 'S&P 500',
        'base': {'universe_version': 'universe/2099-01-01.0', 'codes': [A, B, C, X], 'approved': '2099-01-01',
                 'commit': 'synthetic'},
        'exceptions': [{'code': X, 'cik': CIK[X], 'decision_ref': 'SYN-1', 'reason': 'TARGET'}],
        'events': [
            {'id': 'e1', 'action': 'DELETE', 'code': C, 'cik': CIK[C], 'announced': '2099-02-01', 'effective': '2099-02-10',
             'reason': 'QUARTERLY_REBALANCE', 'source': SRC},
            {'id': 'e2', 'action': 'ADD', 'code': D, 'cik': CIK[D], 'announced': '2099-02-01', 'effective': '2099-02-10',
             'reason': 'QUARTERLY_REBALANCE', 'source': SRC},
            {'id': 'e3', 'action': 'CODE_CHANGE', 'code': 'NYSE:BBX', 'old_code': B, 'cik': CIK[B],
             'announced': '2099-02-20', 'effective': '2099-03-01', 'reason': 'LISTING_TRANSFER_TICKER_CHANGE', 'source': SRC},
        ],
    }


def test_valid_payload_has_no_reasons():
    assert im.validate_membership(payload()) == []


def test_before_any_effective_date_is_the_base():
    codes, version = im.membership_at(payload(), date(2099, 2, 9))
    assert codes == [A, B, C, X]
    assert version == 'universe/2099-01-01.0'


def test_change_applies_on_the_effective_session_not_the_announcement():
    p = payload()
    assert C in im.membership_at(p, date(2099, 2, 1))[0]          # announced only
    codes, version = im.membership_at(p, date(2099, 2, 10))       # "prior to the open" on the effective date
    assert C not in codes and D in codes
    assert version == 'universe/2099-02-10.1'


def test_code_change_keeps_the_cik_and_bumps_the_version():
    codes, version = im.membership_at(payload(), date(2099, 3, 1))
    assert B not in codes and 'NYSE:BBX' in codes
    assert version == 'universe/2099-03-01.1'
    assert im.code_aliases(payload(), date(2099, 3, 1)) == {B: 'NYSE:BBX'}
    assert im.code_aliases(payload(), date(2099, 2, 28)) == {}


def test_code_change_with_another_cik_is_rejected():
    p = payload()
    p['events'][2]['cik'] = '0000000077'
    assert 'CODE_CHANGE_CIK_MISMATCH' in im.validate_membership(p)


def test_delete_of_an_absent_code_and_double_add_are_rejected():
    p = payload()
    p['events'].append(dict(p['events'][0], id='e4'))
    assert 'DELETE_ABSENT_CODE' in im.validate_membership(p)
    p = payload()
    p['events'].append(dict(p['events'][1], id='e5'))
    assert 'ADD_PRESENT_CODE' in im.validate_membership(p)


def test_event_requires_an_official_source_and_dates_in_order():
    p = payload()
    p['events'][0]['source'] = 'https://example.com/etf-holdings.xlsx'
    assert 'SOURCE_NOT_OFFICIAL' in im.validate_membership(p)
    p = payload()
    p['events'][0]['announced'] = '2099-02-11'
    assert 'ANNOUNCED_AFTER_EFFECTIVE' in im.validate_membership(p)


def test_events_are_append_only_and_ids_unique():
    p = payload()
    p['events'].append(dict(p['events'][0]))
    assert 'EVENT_ID_DUPLICATE' in im.validate_membership(p)


def test_exception_must_carry_an_owner_decision():
    p = payload()
    p['exceptions'][0]['decision_ref'] = ''
    assert 'EXCEPTION_WITHOUT_DECISION' in im.validate_membership(p)
    p = payload()
    p['exceptions'][0]['code'] = 'NYSE:ZZZ'   # an exception names a code of the base snapshot
    assert 'EXCEPTION_NOT_IN_BASE' in im.validate_membership(p)


def test_carry_rows_moves_a_kept_row_to_the_new_code_without_changing_values():
    kept = {B: {'cik': CIK[B], 'acquired_at': '2099-02-25T00:00:00Z', 'metrics': {'roic': 0.1}}}
    codes, _ = im.membership_at(payload(), date(2099, 3, 1))
    rows = im.carry_rows(kept, codes, im.code_aliases(payload(), date(2099, 3, 1)))
    assert rows['NYSE:BBX'] == kept[B] and B not in rows
    assert rows['NYSE:BBX'] is not kept[B]


def test_carry_rows_never_moves_a_row_of_another_cik():
    kept = {B: {'cik': '0000000077', 'acquired_at': '2099-02-25T00:00:00Z', 'metrics': {}}}
    codes, _ = im.membership_at(payload(), date(2099, 3, 1))
    rows = im.carry_rows(kept, codes, {B: 'NYSE:BBX'})
    assert 'NYSE:BBX' not in rows


def test_deleted_code_leaves_rows_but_stays_in_the_public_change_list():
    codes, _ = im.membership_at(payload(), date(2099, 2, 10))
    kept = {C: {'cik': CIK[C], 'acquired_at': '2099-02-01T00:00:00Z', 'metrics': {'roic': 0.2}}}
    assert C not in im.carry_rows(kept, codes, {})
    changes = im.universe_changes(payload(), date(2099, 3, 1))
    row = next(x for x in changes if x['code'] == C)
    assert row == {'id': 'e1', 'action': 'DELETE', 'code': C, 'cik': CIK[C], 'effective': '2099-02-10',
                   'reason': 'QUARTERLY_REBALANCE', 'source': SRC}
    assert all('metrics' not in x and 'value' not in x for x in changes)


def test_membership_is_pure():
    p = payload()
    before = copy.deepcopy(p)
    im.membership_at(p, date(2099, 3, 1))
    im.universe_changes(p, date(2099, 3, 1))
    assert p == before
