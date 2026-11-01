"""6th-session SEC cutoff in front of qgv.v2_factors.compute. Synthetic companyfacts only (no SEC download)."""
import copy
from datetime import date

import pytest

from investment_system.qgv import v2_factors
from investment_system.research.exp_deciles import pit

S = date(2018, 2, 16)     # first-bundle signal day; filing cutoff 2018-02-08


def annual(year, val, filed, accn, form='10-K', frame=None):
    row = {'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': val, 'accn': accn, 'fy': year, 'fp': 'FY',
           'form': form, 'filed': filed}
    if frame is not None:
        row['frame'] = frame
    return row


def company(fy2017_filed='2018-02-08', extra=()):
    """10-Ks for FY2014..FY2017, each with two comparative years, revenue +10%/yr."""
    rows = []
    for fy, filed in ((2015, '2016-02-25'), (2016, '2017-02-24'), (2017, fy2017_filed)):
        for year in (fy, fy - 1, fy - 2):
            rows.append(annual(year, 100.0 * 1.1 ** (year - 2013), filed, f'K{fy}', frame=f'CY{year}'))
    rows.extend(extra)
    return {'cik': 1, 'entityName': 'SYNTHETIC CO',
            'facts': {'us-gaap': {'Revenues': {'label': 'Revenues', 'units': {'USD': rows}}}}}


def sic_record(sic='3674'):
    return {'sic': sic, 'source': 'AS_FILED', 'reason': None, 'accn': 'K2017', 'filed': '2017-02-24',
            'usable_from': '2017-03-06'}


def test_signal_context_records_s_t_and_both_cutoffs():
    ctx = pit.signal_context(S)
    assert ctx == {'signal_day': '2018-02-16', 'execution_day': '2018-02-20', 'filing_cutoff': '2018-02-08',
                   'compute_cutoff': '2018-02-08', 'rule': pit.RULE}
    assert pit.signal_context(S, '2018-02-20') == ctx
    with pytest.raises(ValueError, match='EXECUTION_DAY_NOT_NEXT_SESSION'):
        pit.signal_context(S, '2018-02-21')


def test_filter_keeps_the_cutoff_day_rejects_the_next_and_counts_reasons():
    facts = company(extra=[annual(2017, 1.0, '2018-02-09', 'LATE'), {'end': '2012-12-31', 'val': 5.0},
                           annual(2012, 2.0, '2018/01/01', 'BADDATE'), annual(2012, 'x', '2017-01-01', 'TEXT'), 'junk'])
    original = copy.deepcopy(facts)
    view = pit.filter_companyfacts(facts, S)
    kept = view.payload['facts']['us-gaap']['Revenues']['units']['USD']
    assert {r['accn'] for r in kept} == {'K2015', 'K2016', 'K2017'}
    assert all('frame' not in r for r in kept)
    assert view.rejected == {'NOT_USABLE_AT_SIGNAL_DAY': 1, 'MISSING_FILED': 1, 'INVALID_FILED': 1,
                             'NON_NUMERIC_VALUE': 1, 'INVALID_ROW': 1}
    assert facts == original                                             # input untouched
    assert view.compute_cutoff == date(2018, 2, 8)
    assert view.filings[-1] == {'accn': 'K2017', 'filed': '2018-02-08', 'usable_from': '2018-02-16'}
    assert view.filings[0] == {'accn': 'K2015', 'filed': '2016-02-25', 'usable_from': '2016-03-04'}


def test_compute_receives_exactly_the_6th_session_cutoff(monkeypatch):
    calls, real = [], v2_factors.compute

    def spy(companyfacts, *, sic, cutoff, diagnostics=None):
        calls.append((companyfacts, sic, cutoff))
        return real(companyfacts, sic=sic, cutoff=cutoff, diagnostics=diagnostics)

    monkeypatch.setattr(v2_factors, 'compute', spy)
    pit.compute_row(company(), sic_record=sic_record(), signal_day=S, security_id='SEC-1')
    payload, sic, cutoff = calls[-1]
    assert (sic, cutoff) == ('3674', date(2018, 2, 8))
    assert all(r['filed'] <= '2018-02-08' for r in payload['facts']['us-gaap']['Revenues']['units']['USD'])


def test_filing_on_the_cutoff_day_counts_and_one_day_later_does_not():
    on_time = pit.compute_row(company('2018-02-08'), sic_record=sic_record(), signal_day=S, security_id='SEC-1')
    late = pit.compute_row(company('2018-02-09'), sic_record=sic_record(), signal_day=S, security_id='SEC-1')
    assert (on_time['state'], on_time['fiscal_year_end']) == ('LIVE', '2017-12-31')
    assert (late['state'], late['fiscal_year_end']) == ('LIVE', '2016-12-31')
    assert on_time['pit']['latest_filing_used'] == {'accn': 'K2017', 'filed': '2018-02-08', 'usable_from': '2018-02-16'}
    assert late['pit']['latest_filing_used'] == {'accn': 'K2016', 'filed': '2017-02-24', 'usable_from': '2017-03-06'}
    assert on_time['pit']['signal_day'] == '2018-02-16' and on_time['pit']['execution_day'] == '2018-02-20'
    assert late['pit']['rejected'] == {'NOT_USABLE_AT_SIGNAL_DAY': 3}
    # Equals the operating compute at the same calendar cutoff (no other change to the facts).
    operating = v2_factors.compute(company('2018-02-08'), sic='3674', cutoff=date(2018, 2, 8))
    assert (on_time['profile'], on_time['fiscal_year_end'], on_time['currency'], on_time['metrics']) == operating[:4]


def test_amendment_counts_only_from_its_own_usable_date():
    amendment = annual(2016, 999.0, '2018-02-09', 'K2016A', form='10-K/A')
    row = pit.compute_row(company('2017-03-01', extra=[amendment]), sic_record=sic_record(), signal_day=S)
    assert row['fiscal_year_end'] == '2017-12-31'
    assert pit.filter_companyfacts(company('2017-03-01', extra=[amendment]), S).rejected == {'NOT_USABLE_AT_SIGNAL_DAY': 1}
    later = pit.compute_row(company('2017-03-01', extra=[amendment]), sic_record=sic_record(), signal_day='2018-02-20')
    assert later['pit']['latest_filing_used']['accn'] == 'K2016A'
    assert later['metrics']['revenue_ttm_growth'] != row['metrics']['revenue_ttm_growth']


def test_good_friday_filing_is_used_on_its_sixth_session():
    s = date(2018, 4, 9)
    row = pit.compute_row(company('2018-03-30'), sic_record=sic_record(), signal_day=s)
    assert row['fiscal_year_end'] == '2017-12-31'
    assert row['pit']['compute_cutoff'] == '2018-04-01' and row['pit']['filing_cutoff'] == '2018-03-29'
    assert row['pit']['latest_filing_used'] == {'accn': 'K2017', 'filed': '2018-03-30', 'usable_from': '2018-04-09'}
    late = pit.compute_row(company('2018-04-02'), sic_record=sic_record(), signal_day=s)
    assert late['fiscal_year_end'] == '2016-12-31'


def test_as_filed_sic_uses_only_filings_usable_at_s():
    rows = [{'cik': '1', 'accn': 'A1', 'filed': '2017-02-24', 'sic': '3674'},
            {'cik': '1', 'accn': 'A2', 'filed': '2018-02-08', 'sic': '3571'},
            {'cik': '1', 'accn': 'A3', 'filed': '2018-02-09', 'sic': '6021'},
            {'cik': '2', 'accn': 'B1', 'filed': '2017-01-05', 'sic': '2834'}]
    got = pit.as_filed_sic(rows, S, cik='0000000001')
    assert got == {'sic': '3571', 'source': 'AS_FILED', 'reason': None, 'accn': 'A2', 'filed': '2018-02-08',
                   'usable_from': '2018-02-16'}
    conflict = rows + [{'cik': '1', 'accn': 'A2', 'filed': '2018-02-08', 'sic': '2834'}]
    assert pit.as_filed_sic(conflict, S, cik=1)['accn'] == 'A1'          # conflicting accession has no SIC
    none = pit.as_filed_sic(rows, date(2017, 2, 24), cik=1)
    assert (none['sic'], none['reason']) == (None, 'SIC_AS_FILED_NOT_AVAILABLE')


def test_missing_inputs_give_reasoned_not_available_rows_and_a_bare_sic_is_refused():
    with pytest.raises(TypeError, match='AS_FILED_SIC_RECORD_REQUIRED'):
        pit.compute_row(company(), sic_record='3674', signal_day=S)
    no_sic = pit.compute_row(company(), sic_record=pit.as_filed_sic([], S, cik=1), signal_day=S)
    assert (no_sic['state'], no_sic['reason_codes'], no_sic['profile']) == ('NOT_AVAILABLE', ['SIC_AS_FILED_NOT_AVAILABLE'], None)
    assert all(v is None for v in no_sic['metrics'].values())
    no_facts = pit.compute_row(None, sic_record=sic_record(), signal_day=S, cik='1')
    assert no_facts['reason_codes'] == ['COMPANYFACTS_NOT_AVAILABLE'] and no_facts['cik'] == '0000000001'
    old = pit.compute_row(company(), sic_record=sic_record(), signal_day=date(2016, 2, 24))
    assert (old['state'], old['reason_codes']) == ('NOT_AVAILABLE', ['NO_PUBLIC_ANNUAL_FACTS'])
    with pytest.raises(ValueError, match='COMPANYFACTS_CIK_MISMATCH'):
        pit.compute_row(company(), sic_record=sic_record(), signal_day=S, cik='2')


def test_build_rows_keys_by_security_and_joins_as_filed_sic():
    filings = [{'cik': '1', 'accn': 'K2017', 'filed': '2018-02-08', 'sic': '3674'}]
    rows = pit.build_rows({'0000000001': company()}, filings, [{'cik': '1', 'security_id': 'SEC-1'},
                                                                {'cik': '7', 'security_id': 'SEC-7'}], S)
    assert rows['SEC-1']['state'] == 'LIVE' and rows['SEC-1']['sic'] == '3674'
    assert rows['SEC-1']['pit']['sic']['accn'] == 'K2017'
    assert rows['SEC-1']['calc_version'] == v2_factors.CALC_VERSION
    assert rows['SEC-7']['reason_codes'] == ['SIC_AS_FILED_NOT_AVAILABLE']
    with pytest.raises(ValueError, match='DUPLICATE_SECURITY_ID'):
        pit.build_rows({}, [], [{'cik': '1', 'security_id': 'X'}, {'cik': '2', 'security_id': 'X'}], S)
