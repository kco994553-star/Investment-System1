#!/usr/bin/env python3
"""Synthetic Python reference for the M3 public-shares path (JS parity vectors).

Replays `public_listing_seed` -> `parse_universe_values` -> `prepare_public_shares`
-> `prepare_universe_price` -> `compare_universe_market_cap` -> top-N with the
fixed N/10% contract. Test-only; never a public or live-data serializer.
`--write` regenerates tests/fixtures/m3_public_shares_reference_v1.json.
"""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/m3_public_shares_reference_v1.json'


def _h(text):
    return sha256(text.encode()).hexdigest()


def replay(case):
    from investment_system.universe.private_subset import (
        QualityConfig, SelectionConfig, UniverseReceipt, compare_universe_market_cap, parse_universe_values,
        prepare_public_shares, prepare_universe_price, public_listing_seed, select_verified_universe_top_n,
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
    checks, shares_out = [], {}
    for row in parsed.rows:
        if row.listing is None or row.code not in records:
            continue
        shares, basis = prepare_public_shares(row.listing, records[row.code], at)
        shares_out[row.code] = {
            'state': shares.state, 'shares': shares.shares,
            'measurement_date': shares.measurement_date.isoformat() if shares.measurement_date else None,
            'accn': shares.accn, 'concept': shares.concept, 'basis_sha256': shares.basis_sha256,
            'facts_sha256': shares.facts_sha256, 'submissions_sha256': shares.submissions_sha256,
            'reason_codes': list(shares.reason_codes),
            'basis': None if basis is None else {'basis_status': basis.basis_status, 'share_class_basis': basis.share_class_basis,
                                                 'source_sha256': basis.source_sha256, 'source_evidence_ref': basis.source_evidence_ref},
        }
        checks.append(compare_universe_market_cap(row, shares, prepare_universe_price(row, basis, as_of=at), QualityConfig(.10, True)))
    selection = select_verified_universe_top_n(tuple(checks), SelectionConfig(data['n'], True), parsed=parsed)
    project_seed = lambda s: None if s is None else {
        'listing_id': s.listing_id, 'company_id': s.company_id, 'issuer_id': s.issuer_id, 'security_id': s.security_id,
        'symbol': s.symbol, 'mic': s.mic, 'currency': s.currency, 'provider_symbol': s.provider_symbol, 'cik': s.cik,
        'valid_from': s.valid_from.isoformat(), 'valid_to': None, 'identity_evidence_ref': s.identity_evidence_ref,
        'identity_sha256': s.identity_sha256, 'synthetic': s.synthetic}
    return {
        'seeds': {code: project_seed(seed) for code, seed in seeds.items()},
        'shares': shares_out,
        'rows': [{'row_index': c.row_index, 'state': c.state, 'quality': c.quality, 'quality_label': c.quality_label,
                  'reason_codes': list(c.reason_codes), 'effective_cap': c.effective_cap,
                  'relative_difference': c.relative_difference} for c in checks],
        'selection': {'state': selection.state, 'selection_status': selection.selection_status, 'requested_n': selection.requested_n,
                      'selected_n': selection.selected_n, 'verified_count': selection.verified_count,
                      'missing_count': selection.missing_count, 'selected_listing_ids': list(selection.selected_listing_ids),
                      'reason_codes': list(selection.reason_codes)},
    }


def record(cik='0000000001', symbol='DEMO', venue='XNAS', *, shares=1000, basis='SINGLE_CLASS_CONFIRMED', state='LIVE',
           reasons=None, acquired='2030-02-10T09:00:00Z', members=None, member=None, identity=True, company=None):
    accn = cik + '-30-000001'
    if reasons is None:
        reasons = [] if basis == 'SINGLE_CLASS_CONFIRMED' else ['SHARE_CLASS_BASIS'] if basis == 'SHARE_CLASS_BASIS' else ['MULTI_CLASS_AMBIGUOUS']
        if state == 'STALE':
            reasons = reasons + ['STALE_INPUT']
    members = members if members is not None else (['CommonClassAMember', 'CommonClassBMember'] if basis == 'SHARE_CLASS_BASIS' else [])
    filed = shares is not None
    return {'cik': cik, 'listing_id': f'{venue}:{symbol}:{cik}' if identity else None,
            'company_id': (company or 'sec_' + cik) if identity else None, 'shares': shares,
            'measurement_date': '2030-01-10' if filed else None, 'accn': accn if filed else None, 'form': '10-Q' if filed else None,
            'filed': '2030-01-15' if filed else None, 'acquired_at': acquired if identity else None,
            'concept': 'dei:EntityCommonStockSharesOutstanding' if filed else None, 'share_class_basis': basis,
            'basis_evidence': {'cover_accn': accn if filed and basis != 'BASIS_UNCONFIRMED' else None,
                               'class_count': len(members) if filed else None, 'class_members': members,
                               'listing_class_member': member if member is not None else (members[0] if basis == 'SHARE_CLASS_BASIS' else None)},
            'source_sha256': {'companyfacts': _h('facts-' + cik), 'submissions': _h('submissions-' + cik),
                              'cover': _h('cover-' + cik) if filed else None},
            'state': state, 'reason_codes': reasons if filed else ['SHARES_NOT_AVAILABLE']}


AT = '2030-02-10T12:00:00Z'
HEADER = ['code', 'marketcap', 'price']


def cases():
    one = lambda rec, row, code='NASDAQ:DEMO', n=1: {'records': {code: rec}, 'values': [HEADER, row], 'as_of': AT, 'n': n}
    out = [
        ('single_within_tolerance', one(record(), ['NASDAQ:DEMO', 10500, 10])),
        ('single_inclusive_ten_percent_mismatch', one(record(), ['NASDAQ:DEMO', 11000, 10])),
        ('single_google_missing_keeps_r', one(record(), ['NASDAQ:DEMO', '', 10])),
        ('single_price_missing', one(record(), ['NASDAQ:DEMO', 10000, ''])),
        ('share_class_basis_shown_not_corrected', one(record(basis='SHARE_CLASS_BASIS'), ['NASDAQ:DEMO', 10000, 10])),
        ('basis_unconfirmed_not_verified', one(record(basis='BASIS_UNCONFIRMED'), ['NASDAQ:DEMO', 10000, 10])),
        ('stale_row_not_verified', one(record(state='STALE', acquired='2030-01-20T00:00:00Z'), ['NASDAQ:DEMO', 10000, 10])),
        ('missing_shares_stay_null', one(record(shares=None, basis='BASIS_UNCONFIRMED', state='NOT_AVAILABLE'), ['NASDAQ:DEMO', 10000, 10])),
        ('identity_unresolved', one(record(identity=False, shares=None, basis='BASIS_UNCONFIRMED', state='NOT_AVAILABLE'), ['NASDAQ:DEMO', 10000, 10])),
        ('acquired_after_as_of', one(record(acquired='2030-02-10T13:00:00Z'), ['NASDAQ:DEMO', 10000, 10])),
        ('dot_class_alias_listing', one(record(cik='0000000002', symbol='BRK-B', venue='XNYS'), ['NYSE:BRK.B', 10000, 10], code='NYSE:BRK.B')),
        ('venue_prefix_mismatch', one(record(), ['NYSE:DEMO', 10000, 10], code='NYSE:DEMO')),
        ('target_company_id_kept', one(record(cik='0001045810', symbol='NVDA', company='nvda'), ['NASDAQ:NVDA', 10000, 10], code='NASDAQ:NVDA')),
    ]
    records = {f'NASDAQ:S{i}': record(cik=str(i + 10).zfill(10), symbol=f'S{i}', shares=1000 + i) for i in range(4)}
    records['NASDAQ:S3'] = record(cik='0000000013', symbol='S3', basis='SHARE_CLASS_BASIS', shares=5000)
    values = [HEADER] + [[f'NASDAQ:S{i}', (1000 + i) * 10, 10] for i in range(4)] + [['NASDAQ:UNKNOWN', 1, 1]]
    out.append(('top_n_partial_with_unconfirmed_rows', {'records': records, 'values': values, 'as_of': AT, 'n': 2}))
    return [{'id': name, 'synthetic': True, 'input': data} for name, data in out]


def build():
    vectors = cases()
    for case in vectors:
        case['expected'] = replay(case)
    return {'synthetic': True, 'role': 'REFERENCE_TEST_ONLY', 'contract': 'M3_PUBLIC_SHARES_V1', 'cases': vectors}


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
