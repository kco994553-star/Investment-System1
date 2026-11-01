"""U-A / U-B membership, class-sum issuer cap, representative choice and counts. Synthetic records; hand arithmetic."""
import copy
from decimal import Decimal as D

import pytest

from investment_system.research.exp_deciles import universe as uv


def rec(sid, cik, *, shares='100000000', price='3', **kw):
    out = {'security_id': sid, 'cik': cik, 'listed': True, 'security_type': 'COMMON',
           'shares_outstanding': None if shares is None else D(shares), 'price': None if price is None else D(price)}
    out.update(kw)
    return out


def cap_record(sid, cik, usd):
    """One listed class whose cap is exactly `usd` (shares 1,000,000 x price usd/1e6)."""
    return rec(sid, cik, shares='1000000', price=str(D(usd) / D(1000000)))


def test_class_sum_cap_uses_own_prices_and_representative_price_for_same_rights_unlisted_class():
    records = [rec('A', '10', shares='100000000', price='2.00', median_dollar_volume=D('900'), security_type='COMMON_CLASS'),
               rec('C', '10', shares='50000000', price='1.90', median_dollar_volume=D('500'), security_type='COMMON_CLASS'),
               rec('B', '10', shares='10000000', price=None, listed=False, same_economic_rights=True,
                   security_type='COMMON_CLASS'),
               rec('P', '10', shares='999999999', price='25', security_type='PREFERRED')]
    out = uv.build_universes(records)
    issuer = out['issuers']['0000000010']
    # 100,000,000 x 2.00 + 50,000,000 x 1.90 + 10,000,000 x 2.00 (B at A's price) = 315,000,000; preferred not counted
    assert issuer['market_cap_usd'] == D('315000000.0000')
    assert isinstance(issuer['market_cap_usd'], D)
    assert issuer['representative'] == 'A' and issuer['representative_source'] == 'HIGHEST_MEDIAN_DOLLAR_VOLUME'
    assert [(c['security_id'], c['price_basis']) for c in issuer['classes']] == [
        ('A', 'OWN_PRICE'), ('B', 'REPRESENTATIVE_PRICE'), ('C', 'OWN_PRICE')]
    assert out['U_A']['members'] == ('0000000010',) and out['U_A']['member_securities'] == ('A',)
    assert out['securities']['B'] == {'security_id': 'B', 'cik': '0000000010', 'status': 'EXCLUDED',
                                      'reasons': ['NOT_LISTED'], 'price_label': None}
    assert out['securities']['P']['reasons'] == ['NOT_COMMON_STOCK']


@pytest.mark.parametrize('rights, reason', [(None, 'UNLISTED_CLASS_RIGHTS_UNKNOWN'), (False, 'UNLISTED_CLASS_RIGHTS_DIFFER')])
def test_unlisted_class_without_confirmed_same_rights_makes_the_cap_na(rights, reason):
    records = [rec('A', '10', shares='900000000', price='50'),
               rec('B', '10', shares='1000', listed=False, same_economic_rights=rights)]
    out = uv.build_universes(records)
    issuer = out['issuers']['0000000010']
    assert issuer['market_cap_usd'] is None and issuer['market_cap_reasons'] == [reason]
    assert issuer['U_A'] == {'status': 'UNKNOWN', 'reasons': [reason], 'basis': None}
    assert issuer['U_B'] == {'status': 'UNKNOWN', 'reasons': [reason]}
    assert out['U_A']['counts']['unknown'] == 1 and out['U_A']['counts']['excluded'] == 0


def test_representative_supplied_flag_first_then_rule_then_lowest_id_unconfirmed():
    flag = uv.build_universes([rec('A', '1', median_dollar_volume=D('9')), rec('B', '1', representative=True,
                                                                               median_dollar_volume=D('1'))])
    assert flag['issuers']['0000000001']['representative'] == 'B'
    assert flag['issuers']['0000000001']['representative_source'] == 'SUPPLIED_FLAG'
    tie = uv.build_universes([rec('B', '1', median_dollar_volume=D('5')), rec('A', '1', median_dollar_volume=D('5'))])
    assert tie['issuers']['0000000001']['representative'] == 'A'
    assert tie['issuers']['0000000001']['representative_flags'] == []
    partial = uv.build_universes([rec('B', '1', median_dollar_volume=D('9')), rec('C', '1')])
    issuer = partial['issuers']['0000000001']
    assert (issuer['representative'], issuer['representative_source']) == ('B', 'LOWEST_SECURITY_ID')
    assert issuer['representative_flags'] == ['REPRESENTATIVE_UNCONFIRMED']
    conflict = uv.build_universes([rec('A', '1', representative=True, median_dollar_volume=D('1')),
                                   rec('B', '1', representative=True, median_dollar_volume=D('2'))])
    issuer = conflict['issuers']['0000000001']
    assert issuer['representative'] == 'B' and issuer['representative_flags'] == ['REPRESENTATIVE_FLAG_CONFLICT']
    only = uv.build_universes([rec('Z', '1'), rec('P', '1', security_type='PREFERRED', representative=True)])
    issuer = only['issuers']['0000000001']
    assert (issuer['representative'], issuer['representative_source']) == ('Z', 'ONLY_LISTED_COMMON_CLASS')
    assert issuer['representative_flags'] == ['REPRESENTATIVE_FLAG_NOT_LISTED_COMMON']


def test_u_a_first_build_uses_entry_and_boundaries_are_inclusive():
    out = uv.build_universes([cap_record('A', '1', 250000000), cap_record('B', '2', 249999999),
                              cap_record('C', '3', 260000000)])
    assert out['first_build'] is True
    assert out['U_A']['members'] == ('0000000001', '0000000003')
    assert out['issuers']['0000000002']['U_A'] == {'status': 'EXCLUDED', 'reasons': ['BELOW_U_A_ENTRY_THRESHOLD'],
                                                   'basis': 'FIRST_BUILD_ENTRY'}
    assert out['U_A']['transitions'] == {'entered': (), 'stayed': (), 'left': ()}


def test_u_a_hysteresis_enter_stay_leave_and_unknown_is_not_a_member():
    previous = ['1', '3', '5', '6']
    records = [cap_record('X', '1', 210000000),        # member, >= 200m: stays
               cap_record('Y', '2', 240000000),        # not member, < 250m: stays out
               cap_record('Z', '3', 190000000),        # member, < 200m: leaves
               cap_record('W', '4', 260000000),        # not member, >= 250m: enters
               rec('P', '6', price=None),              # member, price missing: unknown, leaves (not excluded)
               cap_record('S', '7', 200000000)]        # not member, exactly 200m: no entry
    out = uv.build_universes(records, previous_u_a=previous)
    assert out['U_A']['members'] == ('0000000001', '0000000004')
    issuers = out['issuers']
    assert issuers['0000000001']['U_A'] == {'status': 'ELIGIBLE', 'reasons': [], 'basis': 'STAY'}
    assert issuers['0000000002']['U_A']['reasons'] == ['BELOW_U_A_ENTRY_THRESHOLD']
    assert issuers['0000000003']['U_A'] == {'status': 'EXCLUDED', 'reasons': ['BELOW_U_A_STAY_THRESHOLD'], 'basis': 'STAY'}
    assert issuers['0000000004']['U_A']['basis'] == 'ENTRY'
    assert issuers['0000000006']['U_A'] == {'status': 'UNKNOWN', 'reasons': ['PRICE_MISSING'], 'basis': None}
    assert issuers['0000000007']['U_A']['reasons'] == ['BELOW_U_A_ENTRY_THRESHOLD']
    assert out['U_A']['transitions'] == {
        'entered': ('0000000004',), 'stayed': ('0000000001',),
        'left': ({'cik': '0000000003', 'reasons': ['BELOW_U_A_STAY_THRESHOLD']},
                 {'cik': '0000000005', 'reasons': ['NOT_IN_RECORDS_AT_S']},
                 {'cik': '0000000006', 'reasons': ['PRICE_MISSING']})}
    counts = out['U_A']['counts']
    assert counts == {'candidate': 6, 'eligible': 2, 'excluded': 3, 'unknown': 1,
                      'excluded_by_reason': {'BELOW_U_A_ENTRY_THRESHOLD': 2, 'BELOW_U_A_STAY_THRESHOLD': 1},
                      'unknown_by_reason': {'PRICE_MISSING': 1}}
    # Next year: the unknown issuer is no longer a previous member and needs the entry threshold.
    nxt = uv.build_universes([cap_record('P', '6', 220000000)], previous_u_a=out['U_A']['members'])
    assert nxt['issuers']['0000000006']['U_A']['reasons'] == ['BELOW_U_A_ENTRY_THRESHOLD']


def test_u_b_threshold_without_hysteresis_and_subset_of_u_a():
    records = [cap_record('A', '1', D('10000000000')), cap_record('B', '2', D('9999999999.99')),
               cap_record('C', '3', D('25000000000'))]
    out = uv.build_universes(records, previous_u_a=['2'])
    assert out['U_B']['members'] == ('0000000001', '0000000003')
    assert out['issuers']['0000000002']['U_B'] == {'status': 'EXCLUDED', 'reasons': ['BELOW_U_B_THRESHOLD']}
    assert set(out['U_B']['members']) <= set(out['U_A']['members'])
    assert out['U_B']['member_securities'] == ('A', 'C')
    assert 'transitions' not in out['U_B']


def test_missing_inputs_are_unknown_never_excluded_and_counts_balance():
    records = [cap_record('OK', '1', 300000000),
               cap_record('SMALL', '2', 1000000),
               rec('PREF', '3', security_type='PREFERRED'),                       # issuer with no common stock
               rec('UNL', '4', listed=False),                                     # common, not listed
               rec('LQ', '5', listed=None),                                        # listing unknown
               rec('TQ', '6', security_type=None),                                 # type unknown
               rec('NOCIK', None),                                                 # listed common, CIK unknown
               rec('BADCIK', 'abc'),                                               # CIK not a number
               rec('NOCIKPREF', None, security_type='WARRANT'),                    # definitively not common
               rec('SH', '7', shares=None),                                        # shares missing
               rec('PZ', '8', price='0'),                                          # unusable price
               rec('MIXA', '9', shares='1000000000', price='5'), rec('MIXB', '9', security_type=None, listed=False)]
    out = uv.build_universes(records)
    sec = out['security_counts']
    assert sec['candidate'] == 13 and sec['listed_common'] + sec['excluded'] + sec['unknown'] == 13
    assert sec['excluded_by_reason'] == {'NOT_COMMON_STOCK': 2, 'NOT_LISTED': 2}
    assert sec['unknown_by_reason'] == {'CIK_INVALID': 1, 'CIK_UNKNOWN': 1, 'LISTING_STATUS_UNKNOWN': 1,
                                        'SECURITY_TYPE_UNKNOWN': 1}
    ua = out['U_A']['counts']
    assert ua['candidate'] == ua['eligible'] + ua['excluded'] + ua['unknown'] == 11   # 9 CIKs + 2 CIK-less units
    assert ua['eligible'] == 1
    assert ua['excluded_by_reason'] == {'BELOW_U_A_ENTRY_THRESHOLD': 1, 'NO_LISTED_COMMON_STOCK': 2}
    assert ua['unknown_by_reason'] == {'CIK_INVALID': 1, 'CIK_UNKNOWN': 1, 'LISTING_STATUS_UNKNOWN': 1,
                                       'PRICE_INVALID': 1, 'SECURITY_TYPE_UNKNOWN': 2,
                                       'SHARES_OUTSTANDING_MISSING': 1}
    assert out['issuers']['SECURITY:NOCIK']['U_A'] == {'status': 'UNKNOWN', 'reasons': ['CIK_UNKNOWN'], 'basis': None}
    assert 'SECURITY:NOCIKPREF' not in out['issuers']
    ub = out['U_B']['counts']
    assert (ub['candidate'], ub['eligible'], ub['unknown']) == (11, 0, 7)
    assert ub['excluded_by_reason'] == {'BELOW_U_B_THRESHOLD': 2, 'NO_LISTED_COMMON_STOCK': 2}


def test_inputs_validated_decimal_only_and_duplicates_checked():
    with pytest.raises(TypeError, match='PRICE_DECIMAL_REQUIRED'):
        uv.build_universes([rec('A', '1', price=None) | {'price': 12.5}])
    with pytest.raises(ValueError, match='PERMANENT_SECURITY_ID_REQUIRED'):
        uv.build_universes([rec('', '1')])
    with pytest.raises(ValueError, match='CONFLICTING_SECURITY_RECORDS'):
        uv.build_universes([rec('A', '1'), rec('A', '1', price='4')])
    with pytest.raises(TypeError, match='LISTED_MUST_BE_TRUE_FALSE_OR_NONE'):
        uv.build_universes([rec('A', '1', listed=1)])
    same = uv.build_universes([rec('A', '1'), rec('A', '1')])
    assert same['security_counts']['candidate'] == 1
    text = uv.build_universes([rec('A', '1', shares=None) | {'shares_outstanding': '100000000', 'price': '3'}])
    assert text['issuers']['0000000001']['market_cap_usd'] == D('300000000')


def test_pure_order_independent_and_price_label_carried():
    records = [rec('B', '2', price='4', price_label='PROXY_LAST_TRADE'), rec('A', '1'), cap_record('C', '3', 1)]
    original = copy.deepcopy(records)
    a = uv.build_universes(records, signal_day='2018-02-16')
    b = uv.build_universes(list(reversed(records)), signal_day='2018-02-16')
    assert a == b and records == original
    assert a['issuers']['0000000002']['price_label'] == 'PROXY_LAST_TRADE'
    assert a['issuers']['0000000002']['classes'][0]['price_label'] == 'PROXY_LAST_TRADE'
    assert a['signal_day'] == '2018-02-16'
