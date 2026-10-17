"""Research PIT filing adapter (owner supplement 2026-10-17 items 3, 7). Synthetic data only: no SEC download, no price.

Each test names the bug it catches. Expected values are written by hand (dates, growth ratios), never produced by the
function under test. Plan cases: S1 future filing, S2 same-day filing, S3 amendment, S4 missing filed (BACKTEST_RESEARCH_PLAN §10).
"""
import ast
from datetime import date, datetime, timedelta
import itertools
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pytest

from investment_system.qgv import v2_factors as vf
from investment_system.research import pit_filings as pf
from investment_system.validation import forward_ledger

ET = ZoneInfo('America/New_York')
SRC = Path(__file__).resolve().parents[1] / 'src' / 'investment_system'
REV = ('us-gaap', 'Revenues', 'USD')


def at(y, m, d, hh=16, mm=0):
    """A New York instant; the default is the 16:00 close (BT-11 A decision time)."""
    return datetime(y, m, d, hh, mm, tzinfo=ET)


def row(val, end, filed, accn, *, start=None, form='10-K', frame=None):
    out = {'end': end, 'val': val, 'accn': accn, 'fy': int(end[:4]), 'fp': 'FY', 'form': form, 'filed': filed}
    if start is not None:
        out['start'] = start
    if frame is not None:
        out['frame'] = frame
    return out


def annual(year, val, filed, accn, **kw):
    return row(val, f'{year}-12-31', filed, accn, start=f'{year}-01-01', **kw)


def payload(*entries, cik=1):
    facts = {}
    for (taxonomy, concept, unit), rows in entries:
        node = facts.setdefault(taxonomy, {}).setdefault(concept, {'label': concept, 'units': {}})
        node['units'].setdefault(unit, []).extend(rows)
    return {'cik': cik, 'entityName': 'SYNTHETIC CO', 'facts': facts}


def values(view):
    """{(concept, start, end): value} of the latest public value per period."""
    return {(key[1], key[3], key[4]): fact.value for key, fact in pf.resolve_as_of(view.facts).values.items()}


FY = lambda year: ('Revenues', f'{year}-01-01', f'{year}-12-31')  # noqa: E731


# ---------------- trading calendar ----------------
def test_calendar_rules_reproduce_the_published_nyse_table():
    # Catches: wrong observance rules (Saturday -> Friday, Sunday -> Monday, New Year's Day on a Saturday not observed in
    # 2028, Juneteenth, Good Friday). 2026-2028 is the exchange-published table already used by the forward ledger.
    for year in (2026, 2027, 2028):
        assert pf.rule_holidays(year) == {d for d in forward_ledger.NYSE_HOLIDAYS if d.year == year}


@pytest.mark.parametrize('day,session', [
    ('2016-02-15', False),  # Washington's Birthday: the February rebalance moves to Tuesday
    ('2016-02-16', True),
    ('2016-03-25', False),  # Good Friday
    ('2012-10-29', False), ('2012-10-30', False),  # Hurricane Sandy
    ('2018-12-05', False), ('2025-01-09', False),  # national days of mourning
    ('2021-06-18', True),   # Juneteenth not yet an NYSE holiday
    ('2022-06-20', False),  # first observed Juneteenth (Sunday -> Monday)
    ('2010-12-24', False),  # Christmas on Saturday -> Friday closed
    ('2010-12-31', True), ('2021-12-31', True),  # New Year's Day on Saturday: the Friday before stays open
    ('2017-01-02', False),  # New Year's Day on Sunday -> Monday closed
    ('2015-07-03', False),  # Independence Day on Saturday -> Friday closed
    ('2016-02-13', False),  # Saturday
])
def test_historical_sessions(day, session):
    # Catches: a weekday-only calendar for pre-2026 dates (forward_ledger lists 2026-2028 only).
    assert pf.is_session(date.fromisoformat(day)) is session


def test_calendar_fails_closed_outside_its_range_and_on_holidays():
    with pytest.raises(pf.CalendarNotConfigured):
        pf.is_session(date(2008, 12, 31))
    with pytest.raises(pf.CalendarNotConfigured):
        pf.next_session(date(2028, 12, 29))
    with pytest.raises(ValueError):
        pf.signal_decision_time(date(2016, 2, 15))
    assert pf.signal_decision_time(date(2016, 2, 16)) == at(2016, 2, 16)


# ---------------- public time of one filing ----------------
def test_filed_date_only_is_public_from_the_next_session_open():
    # Catches: same-day use of a date-only filing; ignoring holidays; UTC midnight (sec_vintage) instead of the next open.
    assert pf.public_time('2016-02-11').at == at(2016, 2, 12, 9, 30)   # Thursday -> Friday open
    assert pf.public_time('2016-02-12').at == at(2016, 2, 16, 9, 30)   # Friday -> Tuesday (Monday holiday)
    assert pf.public_time('20160213').at == at(2016, 2, 16, 9, 30)     # FSDS spelling, Saturday
    assert pf.public_time('2016-02-12').basis == pf.FILED_DATE_NEXT_SESSION


def test_acceptance_time_is_used_when_consistent_and_read_conservatively():
    # Catches: trusting an ambiguous 'Z' label by default (could advance a fact by 4-5 hours); misreading FSDS naive times.
    t = pf.public_time('20160216', '2016-02-16 07:05:00.0')   # FSDS: New York wall clock, pre-market
    assert (t.at, t.basis) == (at(2016, 2, 16, 7, 5), pf.ACCEPTED_TIME)
    assert pf.public_time('2016-02-16', '2016-02-16T19:00:00.000Z').at == at(2016, 2, 16, 19, 0)
    assert pf.public_time('2016-02-16', '2016-02-16T19:00:00.000Z', reading='as_labeled').at == at(2016, 2, 16, 14, 0)
    # Friday after 17:30 -> filing date Tuesday (Monday holiday): still consistent, public Friday evening.
    t = pf.public_time('2016-02-16', '2016-02-12 18:10:00')
    assert (t.at, t.basis) == (at(2016, 2, 12, 18, 10), pf.ACCEPTED_TIME)


def test_inconsistent_or_invalid_acceptance_falls_back_conservatively():
    # Catches: a mismatched acceptance time (wrong accession join) advancing a fact before its filing date allows.
    t = pf.public_time('2016-02-16', '2015-06-01 10:00:00')
    assert t.at == at(2016, 2, 17, 9, 30) and pf.ACCEPTED_FILED_INCONSISTENT in t.notes
    t = pf.public_time('2016-02-16', '2016-03-01 10:00:00')   # later than the date rule: the later instant
    assert t.at == at(2016, 3, 1, 10, 0) and pf.ACCEPTED_FILED_INCONSISTENT in t.notes
    t = pf.public_time('2016-02-16', 'yesterday')
    assert t.at == at(2016, 2, 17, 9, 30) and pf.ACCEPTED_INVALID in t.notes


def test_missing_or_invalid_filing_date_is_never_replaced():
    # Catches: sec_vintage-style fallback to the period end, or using an acceptance time without a filing date.
    assert (pf.public_time(None).at, pf.public_time(None).reason) == (None, pf.MISSING_FILED)
    assert pf.public_time('', '2016-02-16 07:00:00').at is None
    assert pf.public_time('2016-02-30').reason == pf.INVALID_FILED
    with pytest.raises(ValueError):
        pf.pit_filter_companyfacts(payload(), datetime(2016, 2, 16, 16, 0))   # naive decision time


# ---------------- companyfacts filter ----------------
def test_s1_future_filing_is_blocked():
    # Catches: cutoff direction errors; using today's companyfacts (latest values) for a past decision.
    p = payload((REV, [annual(2014, 110.0, '2015-02-25', 'K14'), annual(2015, 121.0, '2016-02-19', 'K15')]))
    view = pf.pit_filter_companyfacts(p, at(2016, 2, 16))   # S = 2016-02-16, FY2015 10-K filed S + 3 days
    assert values(view) == {FY(2014): 110.0}
    assert (view.accounting.kept, view.accounting.not_yet_public) == (1, 1)


def test_s2_same_day_filing_is_not_used_before_the_next_session():
    # Catches: passing cutoff = S to the inclusive operating rule `filed <= cutoff`.
    p = payload((REV, [annual(2014, 110.0, '2015-02-25', 'K14'), annual(2015, 121.0, '2016-02-16', 'K15')]))
    assert FY(2015) not in values(pf.pit_filter_companyfacts(p, at(2016, 2, 16)))          # filed on S: not at S close
    assert FY(2015) not in values(pf.pit_filter_companyfacts(p, at(2016, 2, 17, 9, 29)))   # nor before the next open
    assert values(pf.pit_filter_companyfacts(p, at(2016, 2, 17, 9, 30)))[FY(2015)] == 121.0
    holiday = payload((REV, [annual(2015, 121.0, '2016-02-15', 'K15')]))                   # filed S - 1 day (a holiday)
    assert values(pf.pit_filter_companyfacts(holiday, at(2016, 2, 16)))[FY(2015)] == 121.0


def test_s3_amendment_is_hidden_until_its_own_public_time_and_the_original_stays_visible():
    # Catches: a later 10-K/A value used before it was filed; dropping the original once an amendment exists anywhere.
    p = payload((REV, [annual(2015, 121.0, '2016-02-10', 'ORIG'),
                       annual(2015, 118.0, '2016-03-01', 'AMND', form='10-K/A', frame='CY2015')]))
    early = pf.pit_filter_companyfacts(p, at(2016, 2, 22))
    assert values(early)[FY(2015)] == 121.0
    assert [r['accn'] for r in early.payload['facts']['us-gaap']['Revenues']['units']['USD']] == ['ORIG']
    assert values(pf.pit_filter_companyfacts(p, at(2016, 3, 2)))[FY(2015)] == 118.0
    assert values(pf.pit_filter_companyfacts(p, at(2016, 2, 22)))[FY(2015)] == 121.0   # recomputed later: unchanged
    # Filing date only: the amendment is not public on its own filing day; with a pre-market acceptance time it is.
    assert values(pf.pit_filter_companyfacts(p, at(2016, 3, 1, 12, 0)))[FY(2015)] == 121.0
    accepted = pf.pit_filter_companyfacts(p, at(2016, 3, 1, 12, 0), acceptance={'AMND': '2016-03-01 08:00:00'})
    assert values(accepted)[FY(2015)] == 118.0


def test_restated_comparative_in_a_later_10k_does_not_leak_backward_and_frame_is_dropped():
    # Catches: choosing the `frame`-tagged row (SEC tags the LATEST filing of a period) or the latest filing regardless of
    # its filing date, which moves a restatement into the past.
    p = payload((REV, [annual(2014, 110.0, '2015-02-25', 'K14', frame='CY2014'),
                       annual(2015, 121.0, '2016-02-25', 'K15', frame='CY2015'),
                       annual(2014, 99.0, '2016-02-25', 'K15', frame='CY2014')]))
    before = pf.pit_filter_companyfacts(p, at(2016, 2, 25))
    after = pf.pit_filter_companyfacts(p, at(2016, 2, 26))
    assert values(before) == {FY(2014): 110.0}
    assert values(after) == {FY(2014): 99.0, FY(2015): 121.0}
    assert pf.resolve_as_of(after.facts).counts == {pf.SUPERSEDED: 1}
    for view in (before, after):
        assert all('frame' not in r for r in view.payload['facts']['us-gaap']['Revenues']['units']['USD'])
    assert (before.accounting.notes[pf.FRAME_TAG_REMOVED], after.accounting.notes[pf.FRAME_TAG_REMOVED]) == (1, 3)


def test_s4_missing_filed_is_dropped_and_counted_never_replaced_by_the_period_end():
    # Catches: providers/sec_vintage.py-style `filed or end` fallback, which makes a fact public at its period end.
    p = payload((REV, [annual(2014, 110.0, '2015-02-25', 'K14'), annual(2015, 121.0, None, 'K15')]))
    view = pf.pit_filter_companyfacts(p, at(2025, 12, 31))   # ten years after the period end
    assert values(view) == {FY(2014): 110.0}
    assert view.accounting.dropped == {pf.MISSING_FILED: 1} and view.accounting.balanced()


def test_row_accounting_counts_every_reason_and_balances():
    # Catches: silently lost rows (input != kept + not yet public + dropped) and unreported reasons.
    rows = [annual(2013, 100.0, '2014-02-25', 'K13'),
            annual(2014, 110.0, '2015-02-25', 'K14', frame='CY2014'),
            annual(2015, 121.0, '2016-02-25', 'K15'),                 # not yet public
            annual(2012, 90.0, None, 'K12'),                          # MISSING_FILED
            annual(2011, 80.0, '2012/02/24', 'K11'),                  # INVALID_FILED
            annual(2010, 70.0, '2011-02-24', None),                   # MISSING_ACCN
            {'val': 5.0, 'accn': 'X1', 'filed': '2011-02-24'},        # MISSING_PERIOD_END
            annual(2010, None, '2011-02-24', 'K10'),                  # NON_NUMERIC_VALUE
            annual(2010, True, '2011-02-24', 'K10'),                  # NON_NUMERIC_VALUE (a bool is not an amount)
            'not a row']                                              # INVALID_ROW
    a = pf.pit_filter_companyfacts(payload((REV, rows)), at(2016, 2, 16)).accounting
    assert (a.input_rows, a.kept, a.not_yet_public) == (10, 2, 1)
    assert a.dropped == {pf.MISSING_FILED: 1, pf.INVALID_FILED: 1, pf.MISSING_ACCN: 1, pf.MISSING_PERIOD_END: 1,
                         pf.NON_NUMERIC_VALUE: 2, pf.INVALID_ROW: 1}
    assert a.notes == {pf.FILED_DATE_NEXT_SESSION: 2, pf.FRAME_TAG_REMOVED: 1}
    assert a.balanced()


def test_duplicate_facts_resolve_deterministically_whatever_the_input_order():
    # Catches: input-order dependence; averaging or picking either of two different values filed at the same time.
    rows = [annual(2013, 100.0, '2014-02-25', 'K13'),
            annual(2013, 100.0, '2015-02-25', 'K14b'),   # the same value repeated by two filings of one day
            annual(2013, 100.0, '2015-02-25', 'K14a'),
            annual(2014, 110.0, '2015-02-25', 'K14a'),
            annual(2014, 111.0, '2015-02-25', 'K14b'),   # same day, different value -> the period is dropped
            annual(2012, 90.0, '2013-02-25', 'K12')]
    seen = set()
    for perm in itertools.permutations(rows):
        view = pf.pit_filter_companyfacts(payload((REV, [dict(r) for r in perm])), at(2016, 2, 16))
        res = pf.resolve_as_of(view.facts)
        seen.add((repr(view.payload), tuple(sorted((k, f.accn, f.value) for k, f in res.values.items())),
                  tuple(res.counts.items())))
    assert len(seen) == 1
    (_, resolved, counts), = seen
    assert [(k[3], accn, v) for k, accn, v in resolved] == [('2012-01-01', 'K12', 90.0), ('2013-01-01', 'K14a', 100.0)]
    assert dict(counts) == {pf.AMBIGUOUS_SAME_TIME: 1, pf.SAME_TIME_DUPLICATE: 1, pf.SUPERSEDED: 1}


def test_share_and_split_facts_pass_through_unchanged_and_obey_their_own_public_time():
    # Catches: the adapter rescaling share counts (a second split adjustment on top of SEC's restated counts) or exposing a
    # split ratio before the filing that reports it. Per-share split handling itself stays the v2 SPLIT rule (not here).
    shares = ('us-gaap', 'WeightedAverageNumberOfDilutedSharesOutstanding', 'shares')
    ratio = ('us-gaap', 'StockholdersEquityNoteStockSplitConversionRatio1', 'pure')
    cover = ('dei', 'EntityCommonStockSharesOutstanding', 'shares')
    p = payload((shares, [annual(2015, 10.0, '2016-02-25', 'K15'), annual(2015, 20.0, '2017-02-24', 'K16'),
                          annual(2016, 20.0, '2017-02-24', 'K16')]),
                (ratio, [row(2.0, '2016-06-30', '2017-02-24', 'K16')]),
                (cover, [row(10.2, '2016-02-01', '2016-02-25', 'K15')]))
    before = pf.pit_filter_companyfacts(p, at(2016, 12, 30))
    after = pf.pit_filter_companyfacts(p, at(2017, 2, 27))   # K16 filed Friday 2017-02-24 -> public Monday open
    name = lambda key: key[1]  # noqa: E731
    assert values(before) == {(name(shares), '2015-01-01', '2015-12-31'): 10.0, (name(cover), None, '2016-02-01'): 10.2}
    assert values(after) == {(name(shares), '2015-01-01', '2015-12-31'): 20.0, (name(shares), '2016-01-01', '2016-12-31'): 20.0,
                             (name(ratio), None, '2016-06-30'): 2.0, (name(cover), None, '2016-02-01'): 10.2}
    for taxonomy, concept, unit in (shares, ratio, cover):
        for kept in after.payload['facts'][taxonomy][concept]['units'][unit]:
            assert kept in p['facts'][taxonomy][concept]['units'][unit]   # identical row: no value touched


# ---------------- as-filed SIC (FSDS sub) ----------------
SUB = [  # synthetic FSDS `sub` rows
    {'adsh': '0000000001-15-000001', 'cik': 1, 'sic': '3674', 'form': '10-K', 'filed': '20150225',
     'accepted': '2015-02-25 16:05:00.0', 'prevrpt': 1},
    {'adsh': '0000000001-16-000001', 'cik': 1, 'sic': '6022', 'form': '10-K', 'filed': '20160225',
     'accepted': '2016-02-25 16:05:00.0', 'prevrpt': 0},
    {'adsh': '0000000001-16-000002', 'cik': '0000000001', 'sic': '', 'form': '10-Q', 'filed': '20160505',
     'accepted': '2016-05-05 08:00:00.0', 'prevrpt': 0},
    {'adsh': '0000000002-16-000001', 'cik': 2, 'sic': '0000', 'form': '10-K', 'filed': '20160301',
     'accepted': '2016-03-01 09:00:00.0', 'prevrpt': 0},
]
SUB_GENERAL = [{'adsh': '0000000001-12-000001', 'cik': 1, 'sic': '3674', 'form': '10-K', 'filed': '20120224',
                'accepted': '2012-02-24 10:00:00.0', 'prevrpt': 0}]


def test_as_filed_sic_is_point_in_time_and_never_the_current_sic():
    # Catches: a later SIC change (here GENERAL -> FINANCIAL) leaking backward; hiding an original because FSDS later marks
    # it `prevrpt`; filling a missing SIC from somewhere else.
    s, counts = pf.as_filed_sic(SUB, 1, at(2016, 2, 25))   # that day's 16:05 acceptance is not public at the 16:00 close
    assert (s.sic, s.adsh, s.reason) == ('3674', '0000000001-15-000001', None)
    assert counts == {'ROWS': 3, pf.NOT_YET_PUBLIC: 2}
    s, counts = pf.as_filed_sic(SUB, '0000000001', at(2016, 6, 1))
    assert (s.sic, s.adsh) == ('6022', '0000000001-16-000001') and counts[pf.SIC_MISSING_ON_FILING] == 1
    s, counts = pf.as_filed_sic(SUB, 2, at(2016, 6, 1))
    assert (s.sic, s.reason) == (None, pf.NO_PUBLIC_FILING_WITH_SIC) and counts[pf.SIC_MISSING_ON_FILING] == 1
    assert pf.as_filed_sic(SUB, 3, at(2016, 6, 1))[0].reason == pf.NO_FSDS_FILING
    assert pf.as_filed_sic(SUB, 1, at(2015, 1, 2))[0] == pf.SicAsOf(None, None, None, pf.NO_PUBLIC_FILING_WITH_SIC)


# ---------------- price-free Q·G raw metrics through v2_factors, no universe ----------------
def r(year):
    return 100.0 * 1.1 ** (year - 2009)


K_FILED = {2011: '2012-02-24', 2012: '2013-02-25', 2013: '2014-02-25', 2014: '2015-02-25', 2015: '2016-02-25'}


def company_rows():
    """Each 10-K reports its year and two comparative years at +10%/yr. The FY2015 10-K restates FY2013 and FY2014 to
    90% and carries the `frame` tags, as SEC tags the latest filing."""
    rows = []
    for fy, filed in K_FILED.items():
        for year in (fy, fy - 1, fy - 2):
            restated = fy == 2015 and year < 2015
            rows.append(annual(year, r(year) * (0.9 if restated else 1.0), filed, f'K{fy}', frame=f'CY{year}' if fy == 2015 else None))
    return rows


def company(extra=(), *more):
    return payload((REV, company_rows() + list(extra)), *more)


def test_q_g_raw_metrics_run_on_pit_facts_without_a_universe(monkeypatch):
    # Catches: v2_factors receiving non-public rows or a later cutoff; the restated FY2014 entering a 2016-02-16 score;
    # any percentile or selection appearing without a historical universe.
    calls, real = [], vf.compute

    def spy(companyfacts, *, sic, cutoff, diagnostics=None):
        calls.append((companyfacts, sic, cutoff))
        return real(companyfacts, sic=sic, cutoff=cutoff, diagnostics=diagnostics)

    monkeypatch.setattr(pf.v2_factors, 'compute', spy)
    sic = lambda when: pf.as_filed_sic(SUB_GENERAL, 1, when)[0]  # noqa: E731
    a = pf.qg_raw_metrics_as_of(company(), at(2016, 2, 16), sic_as_of=sic(at(2016, 2, 16)))
    assert (a['status'], a['profile'], a['fiscal_year_end']) == ('OK', 'GENERAL', '2014-12-31')
    assert math.isclose(a['metrics']['revenue_cagr_3y'], 0.1, rel_tol=1e-5)      # originals: (r(2014) / r(2011)) ** (1/3) - 1
    assert math.isclose(a['metrics']['revenue_ttm_growth'], 0.1, rel_tol=1e-5)
    assert (a['universe'], a['percentile'], a['sic']['source']) == (None, None, 'FSDS_SUB_AS_FILED')
    seen, sic_seen, cutoff_seen = calls[-1]
    assert (sic_seen, cutoff_seen) == ('3674', date(2016, 2, 16))
    assert all(x['filed'] <= '2016-02-15' and 'frame' not in x for x in seen['facts']['us-gaap']['Revenues']['units']['USD'])
    same_day = pf.qg_raw_metrics_as_of(company(), at(2016, 2, 25), sic_as_of=sic(at(2016, 2, 25)))
    assert same_day['fiscal_year_end'] == '2014-12-31'                             # FY2015 10-K filed that day
    b = pf.qg_raw_metrics_as_of(company(), at(2016, 2, 26), sic_as_of=sic(at(2016, 2, 26)))
    assert b['fiscal_year_end'] == '2015-12-31'
    assert math.isclose(b['metrics']['revenue_cagr_3y'], 0.1, rel_tol=1e-5)       # r(2015) / r(2012): FY2012 not restated
    assert math.isclose(b['metrics']['revenue_ttm_growth'], 1.1 / 0.9 - 1, rel_tol=1e-5)   # against the restated FY2014
    cross = pf.cross_section_as_of([a, b], at(2016, 2, 26))
    assert (cross['status'], cross['reason_codes']) == ('NOT_AVAILABLE', [pf.NEEDS_HISTORICAL_UNIVERSE])
    assert (cross['scores'], cross['selection']) == (None, None)


def test_q_g_metrics_refuse_a_bare_sic_and_stay_not_available_without_an_as_filed_sic():
    # Catches: a current SIC (submissions JSON) passed as a plain string; a missing SIC defaulting to the GENERAL profile.
    with pytest.raises(TypeError):
        pf.qg_raw_metrics_as_of(company(), at(2016, 3, 1), sic_as_of='3674')
    missing = pf.as_filed_sic(SUB, 3, at(2016, 3, 1))[0]
    out = pf.qg_raw_metrics_as_of(company(), at(2016, 3, 1), sic_as_of=missing)
    assert (out['status'], out['profile'], out['metrics']) == ('NOT_AVAILABLE', None, None)
    assert out['reason_codes'] == ['SIC_AS_FILED_NO_FSDS_FILING']


@pytest.mark.parametrize('signal', ['2015-02-25', '2015-02-26', '2016-02-16', '2016-02-25', '2016-02-26', '2016-03-01'])
def test_date_only_view_equals_the_operating_cutoff_of_the_previous_calendar_day(signal):
    # BT-11 A: decision at the close of S with filing dates only == operating v2 with cutoff S - 1 day (plan S28-style
    # equivalence for the PIT step). Catches: an off-by-one day in either direction; the adapter dropping or altering rows.
    day = date.fromisoformat(signal)
    when = pf.signal_decision_time(day)
    ours = pf.qg_raw_metrics_as_of(company(), when, sic_as_of=pf.as_filed_sic(SUB_GENERAL, 1, when)[0])
    operating = vf.compute(company(), sic='3674', cutoff=day - timedelta(days=1))
    assert (ours['profile'], ours['fiscal_year_end'], ours['currency'], ours['metrics']) == operating[:4]


def test_rows_filed_later_never_change_a_past_view():
    # Prefix invariance: amendments, restatements with frame tags, a same-day filing, a new year and another currency, all
    # filed at or after S, must not change anything at the close of S. Catches any leak path (frame, latest-filing choice,
    # currency or FY0 chosen from later rows).
    decision = at(2016, 2, 16)
    later = [annual(year, r(year) * 0.5, '2016-02-17', 'K15A', form='10-K/A', frame=f'CY{year}') for year in range(2009, 2016)]
    later += [annual(2015, 77.0, '2016-02-16', 'K15S'), annual(2016, 999.0, '2017-02-24', 'K16')]
    grown = company(later, (('us-gaap', 'Revenues', 'EUR'), [annual(2015, 50.0, '2016-02-18', 'K15E')]))
    base_view, grown_view = pf.pit_filter_companyfacts(company(), decision), pf.pit_filter_companyfacts(grown, decision)
    assert (grown_view.payload, grown_view.facts) == (base_view.payload, base_view.facts)
    sic = pf.as_filed_sic(SUB_GENERAL, 1, decision)[0]
    base, grown_out = (pf.qg_raw_metrics_as_of(p, decision, sic_as_of=sic) for p in (company(), grown))
    assert (grown_out['fiscal_year_end'], grown_out['metrics']) == (base['fiscal_year_end'], base['metrics'])


# ---------------- research / operations boundary ----------------
def test_research_module_imports_only_the_reused_read_only_pieces():
    # Catches: the research adapter reaching into operating selection (v2_scoring, qgv_v2, sec_universe_*, pipelines),
    # prices, files or the network.
    tree = ast.parse((SRC / 'research' / 'pit_filings.py').read_text(encoding='utf-8'))
    stdlib = {'__future__', 'collections', 'dataclasses', 'datetime', 'math', 're', 'zoneinfo'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert {alias.name for alias in node.names} <= stdlib
        elif isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            if node.level == 0:
                assert node.module in stdlib
            else:
                assert (node.level, node.module, frozenset(names)) in {(2, 'qgv', frozenset({'v2_factors'})),
                                                                     (2, 'validation', frozenset({'forward_ledger'}))}


def test_no_operating_module_imports_the_research_package():
    # Catches: operating code starting to depend on research code (the research path must stay separable).
    pattern = re.compile(r'^\s*(?:from|import)\s+(?:investment_system)?\.*research(?:[.\s]|$)', re.M)
    offenders = [str(path.relative_to(SRC)) for path in SRC.rglob('*.py')
                 if path.relative_to(SRC).parts[0] != 'research' and pattern.search(path.read_text(encoding='utf-8'))]
    assert offenders == []
