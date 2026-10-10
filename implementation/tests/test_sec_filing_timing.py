"""Synthetic SEC submissions: observed filing timing is not an earnings date."""

import copy
import json
from datetime import datetime, timezone

import pytest

from investment_system.providers.sec_filing_timing import build_filing_timing_pattern


ACQUIRED = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
LABEL = "제출 패턴 기반 예상 시기 · 확정 실적 발표일 아님"


def _row(n=1, *, form="10-Q", filed="2025-05-09", reported="2025-03-31", accepted=None):
    return {"form": form, "filingDate": filed, "reportDate": reported,
            "accessionNumber": f"0000999999-25-{n:06d}", "acceptanceDateTime": accepted}


def _payload(*rows):
    return {"cik": 1045810, "filings": {"recent": {
        key: [row[key] for row in rows] for key in _row()
    }}}


def _build(payload, *, company="nvda", acquired=ACQUIRED, as_of=ACQUIRED):
    return build_filing_timing_pattern(company, payload, acquired, as_of)


def test_observed_window_has_no_projected_or_confirmed_date():
    result = _build(_payload(
        _row(1, filed="2023-05-08", reported="2023-03-31"),
        _row(2, filed="2024-05-07", reported="2024-03-31"),
        _row(3)))
    assert result["status"] == "READY"
    assert result["role"] == "ESTIMATED_PATTERN_NOT_CONFIRMED"
    assert result["label"] == LABEL
    assert result["confirmed_earnings_date"] is None
    assert result["estimated_exact_date"] is None
    assert result["groups"][0]["observed_filing_windows"] == [
        {"month": 5, "day_min": 7, "day_max": 9, "count": 3}]
    assert result["groups"][0]["observation_count"] == 3


def test_cross_month_window_is_not_one_continuous_forecast():
    result = _build(_payload(
        _row(1, form="10-K", filed="2024-02-29", reported="2023-12-31"),
        _row(2, form="10-K", filed="2025-03-01", reported="2024-12-31")))
    assert result["groups"][0]["observed_filing_windows"] == [
        {"month": 2, "day_min": 29, "day_max": 29, "count": 1},
        {"month": 3, "day_min": 1, "day_max": 1, "count": 1}]


def test_different_report_month_days_are_not_assigned_to_a_fiscal_quarter():
    result = _build(_payload(_row(1), _row(2, reported="2024-03-30", filed="2024-05-09")))
    assert [group["report_month_day"] for group in result["groups"]] == ["03-30", "03-31"]
    assert all("fiscal_quarter" not in group for group in result["groups"])


def test_annual_and_quarterly_forms_have_separate_groups():
    result = _build(_payload(_row(1), _row(2, form="10-K")))
    assert [group["form"] for group in result["groups"]] == ["10-K", "10-Q"]


def test_amendments_and_other_forms_do_not_move_observed_window():
    result = _build(_payload(_row(1), _row(2, form="10-Q/A", filed="2025-06-12"),
                             _row(3, form="8-K"), _row(4, form="6-K")))
    assert result["status"] == "READY"
    assert result["groups"][0]["observation_count"] == 1
    assert result["groups"][0]["observed_filing_windows"][0]["day_max"] == 9


def test_asml_20f_is_not_promoted_to_10k():
    payload = _payload(_row(form="20-F"))
    payload["cik"] = 937966
    result = _build(payload, company="asml")
    assert result["status"] == "NOT_AVAILABLE"
    assert result["groups"] == []


def test_empty_recent_is_not_a_complete_calendar():
    result = _build(_payload())
    assert result["status"] == "NOT_AVAILABLE"
    assert result["coverage"] == "SUPPLIED_RECENT_ONLY"


def test_dashed_and_compact_accessions_deduplicate_without_input_order_effect():
    dashed, compact = _row(), _row()
    compact['accessionNumber'] = compact['accessionNumber'].replace('-', '')
    first, second = _build(_payload(dashed, compact)), _build(_payload(compact, dashed))
    assert first == second
    assert first['status'] == 'READY'
    assert first['groups'][0]['observation_count'] == 1


def test_missing_required_array_rejects_entire_payload():
    payload = _payload(_row())
    del payload["filings"]["recent"]["reportDate"]
    assert _build(payload)["status"] == "NOT_AVAILABLE"


def test_parallel_length_mismatch_does_not_silently_zip():
    payload = _payload(_row(1), _row(2))
    payload["filings"]["recent"]["filingDate"].pop()
    result = _build(payload)
    assert result["status"] == "NOT_AVAILABLE"
    assert "MISALIGNED_RECENT_ARRAYS" in result["reason_codes"]


def test_string_is_not_a_recent_array():
    payload = _payload(_row())
    payload["filings"]["recent"]["form"] = "10-Q"
    assert _build(payload)["status"] == "NOT_AVAILABLE"


def test_optional_acceptance_array_must_align_when_present():
    payload = _payload(_row())
    payload["filings"]["recent"]["acceptanceDateTime"] = []
    assert _build(payload)["status"] == "NOT_AVAILABLE"


def test_absent_acceptance_does_not_invent_midnight_publication():
    payload = _payload(_row())
    del payload["filings"]["recent"]["acceptanceDateTime"]
    result = _build(payload)
    assert result["status"] == "READY"
    assert result["observations"][0]["accepted_at"] is None
    assert result["availability"]["published_at"] is None
    assert result["availability"]["available_at"] == ACQUIRED.isoformat()
    assert result["availability"]["historical_first_publication"] is False


def test_cik_identity_is_required():
    payload = _payload(_row())
    payload["cik"] = 789019
    assert _build(payload)["reason_codes"] == ["CIK_MISMATCH"]


def test_missing_cik_cannot_use_company_id_as_a_replacement():
    payload = _payload(_row())
    del payload["cik"]
    assert _build(payload)["status"] == "NOT_AVAILABLE"


def test_unicode_cik_digits_are_not_accepted():
    payload = _payload(_row())
    payload["cik"] = "１０４５８１０"
    assert _build(payload)["status"] == "NOT_AVAILABLE"


def test_unknown_company_cannot_expand_the_approved_target():
    with pytest.raises(ValueError):
        _build(_payload(_row()), company="unapproved")


def test_naive_cutoff_and_capture_are_rejected():
    with pytest.raises(ValueError):
        _build(_payload(_row()), as_of=ACQUIRED.replace(tzinfo=None))
    with pytest.raises(ValueError):
        _build(_payload(_row()), acquired=ACQUIRED.replace(tzinfo=None))


def test_capture_after_cutoff_is_not_backfilled_from_old_filing_dates():
    result = _build(_payload(_row()), as_of=datetime(2025, 12, 31, tzinfo=timezone.utc))
    assert result["status"] == "NOT_AVAILABLE"
    assert result["reason_codes"] == ["NOT_AVAILABLE_AT_AS_OF"]
    assert result["groups"] == []


def test_bad_or_naive_acceptance_is_not_accepted_as_an_exact_time():
    result = _build(_payload(_row(1, accepted="bad"),
                             _row(2, accepted="2025-05-09T16:00:00")))
    assert result["status"] == "NOT_AVAILABLE"
    assert all(row["reason"] == "INVALID_ACCEPTANCE_TIME" for row in result["excluded"])


def test_acceptance_after_acquisition_is_inconsistent():
    result = _build(_payload(_row(accepted="2026-01-01T12:00:01Z")))
    assert result["status"] == "NOT_AVAILABLE"
    assert result["excluded"][0]["reason"] == "ACCEPTANCE_AFTER_ACQUISITION"


def test_acceptance_utc_date_can_differ_from_filing_date():
    result = _build(_payload(_row(accepted="2025-05-10T00:30:00Z")))
    assert result["status"] == "READY"
    assert result["observations"][0]["accepted_at"] == "2025-05-10T00:30:00+00:00"


def test_future_filing_or_report_after_filing_is_excluded():
    result = _build(_payload(_row(1, filed="2026-01-02"),
                             _row(2, reported="2025-05-10")))
    assert result["status"] == "NOT_AVAILABLE"
    assert {row["reason"] for row in result["excluded"]} == {
        "FILING_AFTER_ACQUISITION", "REPORT_AFTER_FILING"}


def test_invalid_calendar_dates_are_not_accepted():
    result = _build(_payload(_row(1, filed="2025-02-30"),
                             _row(2, reported="2025-3-31")))
    assert result["status"] == "NOT_AVAILABLE"
    assert {row["reason"] for row in result["excluded"]} == {
        "INVALID_FILING_DATE", "INVALID_REPORT_DATE"}


def test_identical_accession_deduplication_counts_one_observation():
    row = _row()
    result = _build(_payload(row, copy.deepcopy(row)))
    assert result["status"] == "READY"
    assert result["groups"][0]["observation_count"] == 1


def test_conflicting_accession_does_not_choose_a_winner():
    result = _build(_payload(_row(1), _row(1, filed="2025-05-10")))
    assert result["status"] == "NOT_AVAILABLE"
    assert result["groups"] == []
    assert "CONFLICTING_ACCESSION" in result["reason_codes"]


def test_multiple_originals_for_same_report_do_not_choose_latest():
    result = _build(_payload(_row(1), _row(2, filed="2025-05-10")))
    assert result["status"] == "NOT_AVAILABLE"
    assert result["groups"] == []
    assert "AMBIGUOUS_ORIGINAL_FILINGS" in result["reason_codes"]


def test_all_supplied_recent_is_order_invariant_json_safe_and_input_immutable():
    rows = [_row(1, filed="2020-05-08", reported="2020-03-31"), _row(2)]
    payload = _payload(*rows)
    before = copy.deepcopy(payload)
    first = _build(payload)
    second = _build(_payload(*reversed(rows)))
    assert first["groups"] == second["groups"]
    assert first["observations"] == second["observations"]
    assert first["groups"][0]["observation_count"] == 2
    assert first["coverage"] == "SUPPLIED_RECENT_ONLY"
    assert payload == before
    assert json.loads(json.dumps(first, allow_nan=False))["label"] == LABEL


def test_valid_observations_survive_invalid_row_with_partial_status():
    result = _build(_payload(_row(1), _row(2, filed="not-a-day", reported="2024-03-31")))
    assert result["status"] == "PARTIAL"
    assert result["groups"][0]["observation_count"] == 1
    assert result["excluded"][0]["reason"] == "INVALID_FILING_DATE"
