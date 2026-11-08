"""Annual S/T, filing cutoff and the frozen schedule_v1.json. Expected dates are written by hand (settings doc section 2)."""
from datetime import date, timedelta
import json

import pytest

from investment_system.research import pit_filings
from investment_system.research.exp_deciles import schedule, settings

EXPECTED = [  # year, third Monday, S, T, filing cutoff F(S)
    (2017, '2017-02-20', '2017-02-17', '2017-02-21', '2017-02-09'),
    (2018, '2018-02-19', '2018-02-16', '2018-02-20', '2018-02-08'),
    (2019, '2019-02-18', '2019-02-15', '2019-02-19', '2019-02-07'),
    (2020, '2020-02-17', '2020-02-14', '2020-02-18', '2020-02-06'),
    (2021, '2021-02-15', '2021-02-12', '2021-02-16', '2021-02-04'),
    (2022, '2022-02-21', '2022-02-18', '2022-02-22', '2022-02-10'),
    (2023, '2023-02-20', '2023-02-17', '2023-02-21', '2023-02-09'),
    (2024, '2024-02-19', '2024-02-16', '2024-02-20', '2024-02-08'),
    (2025, '2025-02-17', '2025-02-14', '2025-02-18', '2025-02-06'),
    (2026, '2026-02-16', '2026-02-13', '2026-02-17', '2026-02-05'),
]


def test_frozen_file_equals_the_hand_written_table_and_verifies():
    rows = schedule.load_frozen()['rows']
    assert [tuple(r[k] for k in schedule.ROW_KEYS) for r in rows] == EXPECTED
    result = schedule.verify_frozen()
    assert result['ok'] is True and result['mismatches'] == []
    assert len(result['sha256']) == 64


def test_frozen_file_bytes_are_the_generator_output():
    assert schedule.FROZEN_FILE.read_text(encoding='ascii') == schedule.dumps(schedule.frozen_payload())


def test_recomputed_schedule_matches_and_t_is_tuesday_after_presidents_day():
    assert [tuple(r.values()) for r in schedule.build_schedule()] == EXPECTED
    for _, monday, s, t, _ in EXPECTED:
        assert not pit_filings.is_session(date.fromisoformat(monday))       # Presidents' Day is a holiday
        assert date.fromisoformat(t).weekday() == 1
        assert schedule.execution_day_for(s) == date.fromisoformat(t)


def test_tampered_frozen_copy_fails_verification(tmp_path):
    payload = schedule.load_frozen()
    payload['rows'][1]['filing_cutoff'] = '2018-02-09'
    copy = tmp_path / 'schedule_v1.json'
    copy.write_text(json.dumps(payload), encoding='ascii')
    result = schedule.verify_frozen(copy)
    assert result['ok'] is False
    assert {'year': 2018, 'field': 'filing_cutoff', 'frozen': '2018-02-09', 'computed': '2018-02-08'} in result['mismatches']
    assert {'year': 2018, 'reason': 'FILING_CUTOFF_NOT_6TH_SESSION_BEFORE_S'} in result['mismatches']


def test_437_example_filed_2018_02_05_is_usable_from_2018_02_13():
    # 2/6, 2/7, 2/8, 2/9, 2/12 pass in full; usable on the next session.
    assert schedule.usable_from(date(2018, 2, 5)) == date(2018, 2, 13)
    assert schedule.is_usable('2018-02-05', '2018-02-13') is True
    assert schedule.is_usable('2018-02-05', '2018-02-12') is False


def test_cutoff_edges_for_the_first_bundle_signal_day():
    s = date(2018, 2, 16)
    assert schedule.filing_cutoff(s) == date(2018, 2, 8)
    assert schedule.compute_cutoff(s) == date(2018, 2, 8)
    assert schedule.usable_from(date(2018, 2, 8)) == s                     # last usable filing date
    assert schedule.usable_from(date(2018, 2, 9)) == date(2018, 2, 20)     # one day later misses S (T, not S)
    assert schedule.is_usable(date(2018, 2, 8), s) and not schedule.is_usable(date(2018, 2, 9), s)


def test_non_session_filing_date_between_the_6th_and_5th_session_is_usable():
    # Good Friday 2018-03-30: NYSE closed, an SEC filing date is possible. Sessions after it: 4/2, 4/3, 4/4, 4/5, 4/6, 4/9.
    s = date(2018, 4, 9)
    assert schedule.filing_cutoff(s) == date(2018, 3, 29)                  # last SESSION date that is usable
    assert schedule.compute_cutoff(s) == date(2018, 4, 1)                  # last CALENDAR date that is usable
    assert schedule.usable_from(date(2018, 3, 30)) == s
    assert schedule.is_usable(date(2018, 3, 30), s) and schedule.is_usable(date(2018, 4, 1), s)
    assert not schedule.is_usable(date(2018, 4, 2), s)


def test_compute_cutoff_is_exactly_the_usable_rule_for_every_calendar_filing_date():
    s = date(2016, 1, 4)
    while s <= date(2027, 12, 31):
        if pit_filings.is_session(s) and s.day in (1, 2, 3, 4, 5, 8, 15, 28) or s in (date(2018, 4, 9), date(2025, 1, 15)):
            cutoff, session_cutoff = schedule.compute_cutoff(s), schedule.filing_cutoff(s)
            for back in range(0, 20):
                f = s - timedelta(days=back)
                usable = schedule.usable_from(f) <= s
                assert usable == (f <= cutoff), (s, f)
                if pit_filings.is_session(f):
                    assert usable == (f <= session_cutoff), (s, f)
        s += timedelta(days=1)


def test_frozen_years_have_equal_session_and_calendar_cutoffs():
    for _, _, s, _, f in EXPECTED:
        assert schedule.compute_cutoff(s).isoformat() == f == schedule.filing_cutoff(s).isoformat()


def test_signal_day_must_be_a_session_and_calendar_fails_closed():
    with pytest.raises(ValueError, match='SIGNAL_DAY_NOT_A_SESSION'):
        schedule.filing_cutoff(date(2018, 2, 19))
    with pytest.raises(pit_filings.CalendarNotConfigured):
        schedule.usable_from(date(2028, 12, 22))
    with pytest.raises(pit_filings.CalendarNotConfigured):
        schedule.annual_dates(2008)
    with pytest.raises(TypeError):
        schedule.usable_from(20180205)


def test_frozen_row_lookup():
    assert schedule.frozen_row(year=2018)['S'] == '2018-02-16'
    assert schedule.frozen_row('2025-02-14')['T'] == '2025-02-18'
    with pytest.raises(ValueError, match='NOT_A_FROZEN_SIGNAL_DAY'):
        schedule.frozen_row('2016-02-12')
    assert settings.SCHEDULE_YEARS[0] == 2017                               # no S before IEX HIST (2016-12-12)
