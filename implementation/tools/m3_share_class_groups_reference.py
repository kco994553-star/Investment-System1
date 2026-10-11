#!/usr/bin/env python3
"""Synthetic Python reference for M3 share_class_groups/v0 (JS parity vectors).

Replays the public-shares M3 path (tools/m3_public_shares_reference.py) and adds
`prepare_share_class_groups` -> `select_verified_universe_top_n(groups=...)`:
economically identical listed classes of one CIK are summed (class cover shares x
class Sheet price) and ranked once; any missing class/price/LIVE share keeps the
whole company unranked with a reason. Synthetic values only (real CIKs are the
config keys, never data). Test-only; never a public or live-data serializer.
`--write` regenerates tests/fixtures/m3_share_class_groups_reference_v0.json.
"""
from datetime import datetime
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/m3_share_class_groups_reference_v0.json'


def _base():
    spec = importlib.util.spec_from_file_location('_m3_public_shares_reference', Path(__file__).with_name('m3_public_shares_reference.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def replay(case, config):
    from investment_system.universe.private_subset import (
        QualityConfig, SelectionConfig, UniverseReceipt, compare_universe_market_cap, parse_universe_values,
        prepare_public_shares, prepare_share_class_groups, prepare_universe_price, public_listing_seed, select_verified_universe_top_n,
    )
    if case.get('synthetic') is not True:
        raise ValueError('SYNTHETIC_ONLY')
    data = case['input']
    records, values = data['records'], data['values']
    at = datetime.fromisoformat(data['as_of'].replace('Z', '+00:00'))
    seeds = {code: public_listing_seed(code, record, synthetic=True) for code, record in records.items()}
    digest = sha256(json.dumps(values, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()
    receipt = UniverseReceipt('GOOGLEFINANCE_PRIVATE_UNIVERSE', at, digest, 'synthetic-vector', 1, True)
    parsed = parse_universe_values(values, receipt, identity_lookup={c: s for c, s in seeds.items() if s is not None})
    quality = QualityConfig(.10, True)
    checks = []
    for row in parsed.rows:
        if row.listing is None or row.code not in records:
            continue
        shares, basis = prepare_public_shares(row.listing, records[row.code], at)
        checks.append(compare_universe_market_cap(row, shares, prepare_universe_price(row, basis, as_of=at), quality))
    groups = prepare_share_class_groups(parsed, records, at, quality, config)
    selection = select_verified_universe_top_n(tuple(checks), SelectionConfig(data['n'], True), parsed=parsed, groups=groups)
    return {
        'groups': [{'group_id': g.group_id, 'config_version': g.config_version, 'cik': g.cik, 'row_index': g.row_index,
                    'member_codes': list(g.member_codes), 'member_row_indexes': list(g.member_row_indexes),
                    'member_symbols': list(g.member_symbols), 'member_shares': list(g.member_shares),
                    'cover_class_count': g.cover_class_count, 'state': g.state, 'effective_cap': g.effective_cap,
                    'relative_difference': g.relative_difference, 'quality': g.quality, 'quality_label': g.quality_label,
                    'reason_codes': list(g.reason_codes)} for g in groups],
        'selection': {'state': selection.state, 'selection_status': selection.selection_status, 'requested_n': selection.requested_n,
                      'selected_n': selection.selected_n, 'verified_count': selection.verified_count,
                      'missing_count': selection.missing_count, 'selected_listing_ids': list(selection.selected_listing_ids),
                      'selected_caps': [c.effective_cap for c in selection.selected],
                      'missing': [[index, list(codes)] for index, codes in selection.missing],
                      'reason_codes': list(selection.reason_codes)},
    }


AT = '2030-02-10T12:00:00Z'
HEADER = ['code', 'marketcap', 'price']
ABC = ['CommonClassAMember', 'CommonClassBMember', 'CommonClassCMember']
AB = ['CommonClassAMember', 'CommonClassBMember']


def cases():
    record = _base().record
    googl = lambda **k: record(**{'cik': '0001652044', 'symbol': 'GOOGL', 'basis': 'SHARE_CLASS_BASIS', 'shares': 5800,
                                  'members': ABC, 'member': 'CommonClassAMember', **k})
    goog = lambda **k: record(**{'cik': '0001652044', 'symbol': 'GOOG', 'basis': 'SHARE_CLASS_BASIS', 'shares': 5400,
                                 'members': ABC, 'member': 'CommonClassCMember', **k})
    pair = lambda cik, a, b, sa, sb: {f'NASDAQ:{a}': record(cik=cik, symbol=a, basis='SHARE_CLASS_BASIS', shares=sa, members=AB, member=AB[0]),
                                      f'NASDAQ:{b}': record(cik=cik, symbol=b, basis='SHARE_CLASS_BASIS', shares=sb, members=AB, member=AB[1])}
    demo = {'NASDAQ:DEMO': record()}
    # Alphabet: 5800*150 + 5400*151 = 1685400 company R; DEMO single class 1000*10.
    alpha_rows = [['NASDAQ:GOOGL', 1690000, 150], ['NASDAQ:GOOG', 1690000, 151], ['NASDAQ:DEMO', 10000, 10]]

    def case(records, rows, n=2):
        return {'records': records, 'values': [HEADER] + rows, 'as_of': AT, 'n': n}
    out = [
        ('alphabet_two_classes_summed_ranked_once', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(), **demo}, alpha_rows)),
        ('fox_and_news_corp_summed', case({**pair('0001754301', 'FOXA', 'FOX', 300, 200), **pair('0001564708', 'NWSA', 'NWS', 400, 190)},
                                          [['NASDAQ:FOXA', 15000, 30], ['NASDAQ:FOX', 15000, 28], ['NASDAQ:NWSA', '', 25], ['NASDAQ:NWS', 9000, 26]])),
        ('group_google_mismatch_still_ranked_with_label', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(), **demo},
                                                              [['NASDAQ:GOOGL', 1000000, 150], ['NASDAQ:GOOG', 1000000, 151], ['NASDAQ:DEMO', 10000, 10]])),
        ('member_price_missing_company_not_ranked', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(), **demo},
                                                        [['NASDAQ:GOOGL', 1690000, 150], ['NASDAQ:GOOG', 1690000, ''], ['NASDAQ:DEMO', 10000, 10]])),
        ('member_stale_company_not_ranked', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(state='STALE', acquired='2030-01-20T00:00:00Z'), **demo}, alpha_rows)),
        ('member_basis_unconfirmed_company_not_ranked', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(basis='BASIS_UNCONFIRMED'), **demo}, alpha_rows)),
        ('member_shares_missing_company_not_ranked', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(shares=None, basis='BASIS_UNCONFIRMED', state='NOT_AVAILABLE', members=[], member=None), **demo}, alpha_rows)),
        ('member_row_absent_no_partial_sum', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(), **demo}, [['NASDAQ:GOOGL', 1690000, 150], ['NASDAQ:DEMO', 10000, 10]])),
        ('cover_class_count_differs_from_config', case({'NASDAQ:GOOGL': googl(members=AB), 'NASDAQ:GOOG': goog(members=AB, member='CommonClassBMember'), **demo}, alpha_rows)),
        ('same_class_member_twice_mismatch', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(member='CommonClassAMember'), **demo}, alpha_rows)),
        ('single_class_member_contradicts_group', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(basis='SINGLE_CLASS_CONFIRMED', members=['CommonClassCMember']), **demo}, alpha_rows)),
        ('different_filing_dates_mismatch', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': {**goog(), 'measurement_date': '2030-01-09'}, **demo}, alpha_rows)),
        ('unconfigured_share_class_stays_excluded', case({'NYSE:BRK.B': record(cik='0001067983', symbol='BRK-B', venue='XNYS', basis='SHARE_CLASS_BASIS'), **demo},
                                                         [['NYSE:BRK.B', 10000, 10], ['NASDAQ:DEMO', 10000, 10]], n=1)),
        ('other_listing_of_group_issuer_is_duplicate', case({'NASDAQ:GOOGL': googl(), 'NASDAQ:GOOG': goog(),
                                                             'NASDAQ:GOOGX': record(cik='0001652044', symbol='GOOGX'), **demo},
                                                            alpha_rows + [['NASDAQ:GOOGX', 10000, 10]])),
    ]
    return [{'id': name, 'synthetic': True, 'input': data} for name, data in out]


def build():
    from investment_system.universe.share_class_groups import SHARE_CLASS_GROUPS_V0, validate_share_class_groups
    config = validate_share_class_groups(json.loads(json.dumps(SHARE_CLASS_GROUPS_V0)))
    vectors = cases()
    for case in vectors:
        case['expected'] = replay(case, config)
    return {'synthetic': True, 'role': 'REFERENCE_TEST_ONLY', 'contract': 'M3_SHARE_CLASS_GROUPS_V0', 'config': config, 'cases': vectors}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    body = json.dumps(build(), indent=1, sort_keys=True, allow_nan=False) + '\n'
    if args.write:
        FIXTURE.write_text(body)
    else:
        print(body)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
