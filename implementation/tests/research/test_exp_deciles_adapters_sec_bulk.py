"""adapters/sec_bulk.py: PIT companyfacts, as-filed SIC (FSDS sub.txt), single-class cover shares, Form 25 / 15 evidence.
Invented files in tmp_path only (exp_deciles_adapter_fixtures); no SEC request."""
from decimal import Decimal
import gzip

import pytest

import exp_deciles_adapter_fixtures as fx
from investment_system.research.exp_deciles import pit, universe
from investment_system.research.exp_deciles.adapters import sec_bulk
from investment_system.research.exp_deciles.adapters.common import SUPPLIED, UNKNOWN, AdapterError

ALL = [fx.CIK[k] for k in 'ABCDEFG']


@pytest.fixture()
def files(tmp_path):
    return fx.write_all(tmp_path / 'src')


def _load(files, ciks=ALL):
    return sec_bulk.load_companyfacts(files['companyfacts_zip'], ciks)


def test_pit_companyfacts_keeps_only_rows_usable_at_s_and_drops_frame(files):
    raw, problems = _load(files)
    payloads, items = sec_bulk.pit_companyfacts(raw, problems, fx.S)
    a = payloads[fx.cik10('A')]
    filed = {row['filed'] for unit in a['facts']['us-gaap']['Revenues']['units'].values() for row in unit}
    assert filed == {'2018-02-01'}                       # the 10-Q filed 2018-04-30 is not in the bundle
    cover = a['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares']
    assert all('frame' not in row for row in cover) and {r['filed'] for r in cover} == {'2017-11-01', '2018-02-01'}
    assert items[fx.cik10('A')]['status'] == SUPPLIED and items[fx.cik10('A')]['compute_cutoff'] == '2018-02-08'
    assert items[fx.cik10('A')]['rejected'] == {'NOT_USABLE_AT_SIGNAL_DAY': 2}
    # the engine's own filter over the adapter's payload is the identity (same rule, nothing after the cutoff)
    assert pit.filter_companyfacts(a, fx.S).payload == a
    # C's only filing is one day after the cutoff; E is not in the archive
    assert fx.cik10('C') not in payloads and items[fx.cik10('C')]['reasons'] == ['COMPANYFACTS_NO_ROWS_USABLE_AT_S']
    assert items[fx.cik10('E')] == {'status': UNKNOWN, 'reasons': ['COMPANYFACTS_NOT_IN_ARCHIVE']}


def test_companyfacts_archive_missing_or_cik_mismatch_is_unknown(tmp_path):
    raw, problems = sec_bulk.load_companyfacts(None, [fx.CIK['A']])
    assert raw == {} and problems[fx.cik10('A')]['reasons'] == ['COMPANYFACTS_ARCHIVE_NOT_SUPPLIED']
    path = fx.write_companyfacts_zip(tmp_path, mismatch=True)
    raw, problems = sec_bulk.load_companyfacts(path, [fx.CIK['A']])
    assert raw == {} and problems[fx.cik10('A')]['reasons'] == ['COMPANYFACTS_CIK_MISMATCH']
    with pytest.raises(AdapterError, match='CIK_INVALID'):
        sec_bulk.load_companyfacts(path, ['ABC'])


def test_as_filed_sic_rows_from_fsds_sub_txt(files):
    rows, items, counts = sec_bulk.as_filed_sic(files['fsds'], ALL, fx.S)
    assert rows == [{'cik': fx.cik10('A'), 'accn': fx.accn('A', '18', '000001'), 'filed': '2018-02-01', 'sic': '3571'},
                    {'cik': fx.cik10('C'), 'accn': fx.accn('C', '17', '000001'), 'filed': '2017-11-01', 'sic': '7372'}]
    assert items[fx.cik10('A')]['sic'] == '3571' and items[fx.cik10('A')]['usable_from'] == '2018-02-09'
    assert items[fx.cik10('E')] == {'status': UNKNOWN, 'reasons': ['SIC_AS_FILED_NOT_IN_FSDS']}
    assert counts['candidate_rows_not_usable_at_s'] == 1 and counts['candidate_rows_sic_missing'] == 1
    # the engine picks the same SIC from these rows
    assert pit.as_filed_sic(rows, fx.S, fx.CIK['A'])['sic'] == '3571'
    _, items, _ = sec_bulk.as_filed_sic([], ALL, fx.S)
    assert {i['reasons'][0] for i in items.values()} == {'FSDS_NOT_SUPPLIED'}


def test_cover_shares_single_class_fields_for_the_engine(files):
    raw, problems = _load(files)
    shares = sec_bulk.cover_shares(raw, problems, ALL, fx.S, securities_per_cik={fx.cik10('A'): 1},
                                   ticker_counts=sec_bulk.submissions_ticker_counts(files['submissions_zip'], ALL))
    a = shares[fx.cik10('A')]
    assert a['status'] == SUPPLIED and a['shares_outstanding'] == Decimal(50000000)
    assert (a['shares_filed'], a['shares_period_end']) == ('2018-02-01', '2018-01-20')   # the 10-K, not the later 10-Q
    assert a['share_price_basis'] == 'UNCONFIRMED' and a['basis_reason'] == 'SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK'
    assert a['single_class_basis'] == 'NO_MULTI_CLASS_EVIDENCE' and a['flags'] == []
    # the engine reads these F2 fields: usable at S, but the basis keeps the issuer UNKNOWN (never excluded)
    rec = {'security_id': 'X', 'cik': fx.CIK['A'], 'listed': True, 'security_type': 'COMMON', 'price': Decimal('10'),
           **{k: a[k] for k in ('shares_outstanding', 'shares_filed', 'shares_period_end', 'share_price_basis')}}
    out = universe.build_universes([rec], signal_day=fx.S)
    unit = out['issuers'][fx.cik10('A')]
    assert unit['U_A']['status'] == 'UNKNOWN' and 'SHARE_PRICE_BASIS_UNCONFIRMED' in unit['market_cap_reasons']


def test_cover_shares_unknown_paths_never_zero(files):
    raw, problems = _load(files)
    shares = sec_bulk.cover_shares(raw, problems, ALL, fx.S, securities_per_cik={fx.cik10('B'): 2},
                                   ticker_counts=sec_bulk.submissions_ticker_counts(files['submissions_zip'], ALL))
    expected = {'B': 'MULTI_CLASS_SECURITIES_AT_S', 'C': 'COVER_SHARES_NOT_USABLE_AT_S',
                'D': 'COVER_SHARES_AMBIGUOUS_IN_FILING', 'E': 'COMPANYFACTS_NOT_IN_ARCHIVE',
                'F': 'COVER_SHARES_NOT_IN_COMPANYFACTS', 'G': 'MULTI_TICKER_IN_SUBMISSIONS'}
    for key, reason in expected.items():
        item = shares[fx.cik10(key)]
        assert item['status'] == UNKNOWN and item['reasons'][0] == reason, key
        assert item['shares_outstanding'] is None and item['shares_filed'] is None and item['shares_period_end'] is None


def test_multi_class_wins_over_a_non_dimensional_count(files):
    """B has a plain cover count in companyfacts, but two classes in the map: the count is not used for either class."""
    raw, problems = _load(files)
    shares = sec_bulk.cover_shares(raw, problems, [fx.CIK['B']], fx.S, securities_per_cik={fx.cik10('B'): 2})
    item = shares[fx.cik10('B')]
    assert item['reasons'] == ['MULTI_CLASS_SECURITIES_AT_S'] and item['shares_outstanding'] is None
    assert item['flags'] == ['SUBMISSIONS_TICKER_CHECK_NOT_RUN']
    single = sec_bulk.cover_shares(raw, problems, [fx.CIK['B']], fx.S, securities_per_cik={fx.cik10('B'): 1})
    assert single[fx.cik10('B')]['status'] == SUPPLIED and single[fx.cik10('B')]['flags'] == [
        'SUBMISSIONS_TICKER_CHECK_NOT_RUN']


def test_form_25_without_effective_date_and_rows_after_the_cutoff(files):
    records, rows, counts = sec_bulk.terminations(files['form_idx'], [fx.CIK['H'], fx.CIK['A']], fx.S)
    assert records == [{'cik': fx.cik10('H'), 'filed': '2018-01-10',
                        'evidence': f"SEC full-index form.idx Form 25-NSE accession {fx.accn('H', '18', '000002')}"}]
    assert 'effective_date' not in records[0]
    assert rows[0]['reasons'] == ['EFFECTIVE_DATE_NOT_IN_INDEX_ROW', 'TERMINATION_CLASS_NOT_IN_INDEX_ROW']
    assert counts['candidate_rows_not_usable_at_s'] == 1          # the 15-12B filed 2018-02-14
    assert counts['amendments_not_used'] == 1 and counts['without_effective_date'] == 1
    # the engine keeps such a unit an UNKNOWN candidate (not effective), never a termination
    out = universe.build_universes([], signal_day=fx.S, previous_u_a=[fx.CIK['H']], terminations=records)
    assert out['issuers'][fx.cik10('H')]['U_A']['status'] == 'UNKNOWN'
    assert out['terminations'][0]['status'] == 'TERMINATION_EFFECTIVE_DATE_MISSING'


def test_effective_date_only_from_a_confirmed_caller_value(files, tmp_path):
    accn = fx.accn('H', '18', '000002')
    records, rows, counts = sec_bulk.terminations(files['form_idx'], [fx.CIK['H']], fx.S,
                                                  effective_dates={accn: '2018-01-22'})
    assert records[0]['effective_date'] == '2018-01-22' and rows[0]['reasons'][0] == 'EFFECTIVE_DATE_CONFIRMED_BY_CALLER'
    out = universe.build_universes([], signal_day=fx.S, previous_u_a=[fx.CIK['H']], terminations=records)
    assert out['terminations'][0]['status'] == 'TERMINATION_EVIDENCED'
    with pytest.raises(AdapterError, match='EFFECTIVE_DATE_BEFORE_FILING'):
        sec_bulk.terminations(files['form_idx'], [fx.CIK['H']], fx.S, effective_dates={accn: '2018-01-01'})
    # a plain (not gzip) form.idx reads the same
    plain = fx.write_form_idx(tmp_path, gz=False)
    assert sec_bulk.terminations([plain], [fx.CIK['H']], fx.S)[0] == sec_bulk.terminations(
        files['form_idx'], [fx.CIK['H']], fx.S)[0]


def test_form_idx_without_header_is_refused(tmp_path):
    path = tmp_path / 'bad.idx.gz'
    path.write_bytes(gzip.compress(b'25  X  1  2018-01-01  edgar/data/1/0000000001-18-000001.txt\n'))
    with pytest.raises(AdapterError, match='FORM_IDX_HEADER_MISSING'):
        sec_bulk.terminations([path], [1], fx.S)


def test_deterministic(files):
    one = sec_bulk.as_filed_sic(files['fsds'], ALL, fx.S), sec_bulk.terminations(files['form_idx'], ALL, fx.S)
    two = sec_bulk.as_filed_sic(files['fsds'], list(reversed(ALL)), fx.S), sec_bulk.terminations(
        files['form_idx'], list(reversed(ALL)), fx.S)
    assert one == two
