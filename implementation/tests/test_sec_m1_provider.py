"""Strict SEC M1 input processing, using synthetic JSON and no network."""

import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from investment_system.providers.sec_m1 import build_input


UTC = timezone.utc
ACQUIRED = datetime(2025, 2, 3, 12, tzinfo=UTC)
CIK = "0001045810"
ACCESSION = "0001045810-25-000001"


def fact(**changes):
    row = {
        "start": "2024-01-01", "end": "2024-12-31", "val": 100,
        "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": ACCESSION,
    }
    return {**row, **changes}


def payloads(rows=None, filings=None):
    facts = {"cik": int(CIK), "facts": {"us-gaap": {"Revenues": {"units": {"USD": rows if rows is not None else [fact()]}}}}}
    filings = filings if filings is not None else [{
        "accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01",
        "acceptanceDateTime": "2025-02-01T21:00:00Z", "reportDate": "2024-12-31",
    }]
    keys = set().union(*(f.keys() for f in filings)) if filings else set()
    submissions = {"cik": CIK, "filings": {"recent": {k: [f.get(k) for f in filings] for k in keys}}}
    return facts, submissions


def run(rows=None, filings=None, *, as_of=ACQUIRED, acquired_at=ACQUIRED, company_id="nvda", **kwargs):
    facts, submissions = payloads(rows, filings)
    return build_input(company_id, facts, submissions, acquired_at, as_of, **kwargs)


def test_acquisition_microsecond_boundary_prevents_backdating_latest_payload():
    before = run(as_of=ACQUIRED - timedelta(microseconds=1))
    assert before["status"] == "NOT_AVAILABLE"
    assert before["raw_fundamentals"] is None
    assert before["selected_input_facts"] == []
    at = run()
    assert at["status"] == "READY"
    assert at["raw_fundamentals"]["revenue"] == 100
    assert at["availability"]["available_at"] == ACQUIRED.isoformat()


def test_conservative_observation_is_not_source_first_publication():
    result = run()
    assert result["contract"] == "SEC_M1_INPUT" and result["version"] == 1
    assert result["cik"] == CIK
    assert result["availability"] == {
        "available_at": ACQUIRED.isoformat(), "basis": "OBSERVED_PUBLIC_API_UPPER_BOUND",
        "precision": "CONSERVATIVE", "published_at": None, "historical_first_publication": False,
    }
    stamp = result["raw_fundamentals"]["stamp"]
    assert stamp["published_at"] is None
    assert stamp["available_at"] == stamp["observed_at"] == ACQUIRED.isoformat()
    assert stamp["estimated"] is True
    assert stamp["estimation_method"] == "OBSERVED_PUBLIC_API_UPPER_BOUND"
    assert result["raw_fundamentals"]["source_kind"] == "OBSERVED_RAW_INPUT"
    json.dumps(result, allow_nan=False)


def test_acceptance_after_acquisition_stays_excluded_on_later_replay():
    accepted = ACQUIRED + timedelta(hours=2)
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01",
                "acceptanceDateTime": accepted.isoformat()}]
    assert run(filings=filings)["status"] == "NOT_AVAILABLE"
    result = run(filings=filings, as_of=accepted)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["filings"][0]["accepted_at"] == accepted.isoformat()
    assert result["availability"]["published_at"] is None
    assert "ACCEPTANCE_AFTER_ACQUISITION" in str(result["excluded"])


def test_late_acceptance_metadata_does_not_backdate_observed_public_bound():
    accepted = ACQUIRED - timedelta(hours=2)
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01",
                "acceptanceDateTime": accepted.isoformat()}]
    assert run(filings=filings, as_of=accepted)["status"] == "NOT_AVAILABLE"
    result = run(filings=filings)
    assert result["status"] == "READY"
    assert result["filings"][0]["accepted_at"] == accepted.isoformat()
    assert result["availability"]["available_at"] == ACQUIRED.isoformat()


def test_conflicting_values_for_same_filing_and_economic_fact_are_excluded():
    result = run([fact(), fact(val=90)])
    assert result["status"] == "NOT_AVAILABLE"
    assert "AMBIGUOUS_FACT_VALUES" in str(result["excluded"])


def test_missing_acceptance_uses_acquisition_bound():
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"}]
    result = run(filings=filings)
    assert result["status"] == "READY"
    assert result["filings"][0]["accepted_at"] is None


@pytest.mark.parametrize("acceptance", ["not-a-time", "2025-02-01", "2025-02-01T12:00:00", 42])
def test_malformed_or_naive_acceptance_is_excluded(acceptance):
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01",
                "acceptanceDateTime": acceptance}]
    result = run(filings=filings)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert result["excluded"]


@pytest.mark.parametrize("missing", ["filed", "end", "accn", "form"])
def test_fact_missing_identity_or_dates_never_falls_back_to_period_end(missing):
    row = fact()
    del row[missing]
    result = run([row])
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert result["revision_candidates"][0]["source_row"] == row


@pytest.mark.parametrize("changes", [
    {"filed": "2025-02-02"}, {"form": "10-K/A"}, {"accn": "0001045810-25-000999"},
])
def test_fact_must_match_submissions_accession_form_and_filing_date(changes):
    assert run([fact(**changes)])["status"] == "NOT_AVAILABLE"


@pytest.mark.parametrize("source", ["facts", "submissions"])
def test_payload_cik_mismatch_fails_closed(source):
    facts, submissions = payloads()
    (facts if source == "facts" else submissions)["cik"] = "0000789019"
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert "CIK_MISMATCH" in str(result["excluded"])


@pytest.mark.parametrize("arg", ["acquired_at", "as_of"])
def test_naive_call_times_are_rejected(arg):
    with pytest.raises(ValueError, match="timezone"):
        run(**{arg: ACQUIRED.replace(tzinfo=None)})


@pytest.mark.parametrize("company_id", ["hanmi", "tokyo_electron", "not-a-target"])
def test_target_scope_is_existing_us17_only(company_id):
    with pytest.raises(ValueError, match="US17"):
        run(company_id=company_id)


def test_unsupported_form_filter_is_rejected():
    with pytest.raises(ValueError, match="form_filter"):
        run(form_filter="8-K")


@pytest.mark.parametrize("changes", [
    {"start": "2024-10-01"}, {"start": "not-a-date"}, {"end": "not-a-date"},
    {"start": "2025-01-01"}, {"val": "not-a-number"}, {"val": float("inf")},
])
def test_invalid_duration_or_value_cannot_reappear_via_old_converter_fallback(changes):
    result = run([fact(**changes)])
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert result["selected_input_facts"] == []
    json.dumps(result, allow_nan=False)


def test_quarter_filter_removes_year_to_date_duration():
    accession = "0001045810-25-000002"
    filings = [{"accessionNumber": accession, "form": "10-Q", "filingDate": "2025-02-01"}]
    quarter = fact(accn=accession, form="10-Q", start="2024-10-01", fp="Q4", val=30)
    ytd = fact(accn=accession, form="10-Q", fp="Q4", val=100)
    result = run([ytd, quarter], filings=filings, form_filter="10-Q")
    assert result["status"] == "READY"
    assert result["raw_fundamentals"]["revenue"] == 30
    assert len(result["selected_input_facts"]) == 1


def test_economic_period_dedup_does_not_treat_changed_fy_as_previous_period():
    newer = "0001045810-25-000002"
    rows = [fact(), fact(accn=newer, filed="2025-02-02", fy=2025, val=90)]
    filings = [
        {"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"},
        {"accessionNumber": newer, "form": "10-K", "filingDate": "2025-02-02"},
    ]
    result = run(rows, filings)
    assert result["raw_fundamentals"]["revenue"] == 90
    assert result["raw_fundamentals"]["revenue_prev"] is None
    assert len(result["selected_input_facts"]) == 1
    assert len(result["revision_candidates"]) == 2
    assert all(c["parent_accession"] is None and not c["formal_amendment"] for c in result["revision_candidates"])


def test_amendment_receipts_preserve_original_without_inventing_parent():
    amended = "0001045810-25-000002"
    amendment_time = ACQUIRED + timedelta(days=1)
    original_filing = {"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"}
    original_facts, original_submissions = payloads()
    original_copy = copy.deepcopy(original_facts)
    original = build_input("nvda", original_facts, original_submissions, ACQUIRED, ACQUIRED)
    rows = [fact(), fact(accn=amended, filed="2025-02-04", form="10-K/A", val=90)]
    filings = [original_filing, {"accessionNumber": amended, "form": "10-K/A", "filingDate": "2025-02-04",
                               "acceptanceDateTime": amendment_time.isoformat()}]
    before = run(rows, filings, acquired_at=amendment_time, as_of=amendment_time - timedelta(microseconds=1))
    after = run(rows, filings, acquired_at=amendment_time, as_of=amendment_time)
    assert before["status"] == "NOT_AVAILABLE"
    assert original["raw_fundamentals"]["revenue"] == 100
    assert after["raw_fundamentals"]["revenue"] == 90
    assert after["selected_input_facts"][0]["formal_amendment"] is True
    assert after["selected_input_facts"][0]["parent_accession"] is None
    retained_original = next(c for c in after["revision_candidates"] if c["accn"] == ACCESSION.replace("-", ""))
    assert retained_original["source_row"]["val"] == 100
    assert original_facts == original_copy


def test_input_order_does_not_change_period_winner():
    rows = [fact(), fact(val=90, accn="0001045810-25-000002", filed="2025-02-02")]
    filings = [{"accessionNumber": r["accn"], "form": r["form"], "filingDate": r["filed"]} for r in rows]
    assert run(rows, filings) == run(list(reversed(rows)), list(reversed(filings)))


def test_missing_or_unsupported_inputs_stay_not_available():
    empty = build_input("nvda", {}, {}, ACQUIRED, ACQUIRED)
    assert empty["status"] == "NOT_AVAILABLE" and empty["raw_fundamentals"] is None
    facts, submissions = payloads()
    facts["facts"] = {"custom": {"OtherMetric": {"units": {"USD": [fact()]}}}}
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "NOT_AVAILABLE" and result["raw_fundamentals"] is None


@pytest.mark.parametrize("filings", [[], "invalid", 42])
def test_malformed_submissions_container_is_not_available(filings):
    facts, submissions = payloads()
    submissions["filings"] = filings
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None


def test_unhashable_source_fiscal_year_fails_closed_before_legacy_converter():
    result = run([fact(fy=[2024])])
    assert result["status"] == "NOT_AVAILABLE"
    assert "INVALID_FISCAL_YEAR" in str(result["excluded"])


def test_timezone_offsets_are_normalized_without_changing_observation_bound():
    offset = timezone(timedelta(hours=-5))
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01",
                "acceptanceDateTime": "2025-02-01T16:00:00-05:00"}]
    result = run(filings=filings, acquired_at=ACQUIRED.astimezone(offset), as_of=ACQUIRED.astimezone(offset))
    assert result["acquired_at"] == result["as_of"] == ACQUIRED.isoformat()
    assert result["filings"][0]["accepted_at"] == "2025-02-01T21:00:00+00:00"


def test_us17_foreign_filer_keeps_20f_and_reporting_currency():
    facts, submissions = payloads([fact(form="20-F")], [{
        "accessionNumber": ACCESSION, "form": "20-F", "filingDate": "2025-02-01",
    }])
    facts["cik"] = submissions["cik"] = "0000937966"
    facts["facts"] = {"ifrs-full": {"Revenue": {"units": {"EUR": [fact(form="20-F")]}}}}
    result = build_input("asml", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "READY"
    assert result["raw_fundamentals"]["reporting_currency"] == "EUR"


def test_conflicting_submission_identity_excludes_the_accession():
    filings = [
        {"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"},
        {"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-02"},
    ]
    result = run(filings=filings)
    assert result["status"] == "NOT_AVAILABLE"
    assert "AMBIGUOUS_FILING" in str(result["excluded"])


@pytest.mark.parametrize("source", ["facts", "submissions"])
def test_both_payloads_need_cik_to_attribute_the_issuer(source):
    facts, submissions = payloads()
    del (facts if source == "facts" else submissions)["cik"]
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert "MISSING_CIK" in str(result["excluded"])


@pytest.mark.parametrize("acceptances", [
    (None, None), ("2025-02-01T19:00:00Z", None),
    ("2025-02-01T19:00:00Z", "2025-02-01T19:00:00Z"),
])
def test_same_day_revision_order_requires_distinct_known_acceptance_times(acceptances):
    newer = "0001045810-25-000002"
    rows = [fact(), fact(accn=newer, val=90)]
    filings = [{"accessionNumber": r["accn"], "form": "10-K", "filingDate": r["filed"],
                "acceptanceDateTime": acceptance} for r, acceptance in zip(rows, acceptances)]
    result = run(rows, filings)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["selected_input_facts"] == []
    assert "AMBIGUOUS_REVISION_ORDER" in str(result["excluded"])


def test_distinct_acceptance_times_order_same_day_revisions_without_parent_claim():
    newer = "0001045810-25-000002"
    rows = [fact(), fact(accn=newer, val=90)]
    filings = [{"accessionNumber": r["accn"], "form": "10-K", "filingDate": r["filed"],
                "acceptanceDateTime": accepted} for r, accepted in zip(rows, [
                    "2025-02-01T18:00:00Z", "2025-02-01T19:00:00Z"])]
    result = run(rows, filings)
    assert result["status"] == "READY"
    assert result["raw_fundamentals"]["revenue"] == 90
    assert result["selected_input_facts"][0]["parent_accession"] is None


def test_ambiguous_latest_day_does_not_silently_fallback_to_older_period_revision():
    rows = [fact(), fact(accn="0001045810-25-000002", filed="2025-02-02", val=90),
            fact(accn="0001045810-25-000003", filed="2025-02-02", val=80)]
    filings = [{"accessionNumber": r["accn"], "form": "10-K", "filingDate": r["filed"]} for r in rows]
    result = run(rows, filings)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["selected_input_facts"] == []
    assert len(result["revision_candidates"]) == 3


def test_quarter_request_does_not_treat_annual_foreign_report_as_10q():
    facts, submissions = payloads([fact(form="20-F")], [{
        "accessionNumber": ACCESSION, "form": "20-F", "filingDate": "2025-02-01",
    }])
    facts["cik"] = submissions["cik"] = "0000937966"
    result = build_input("asml", facts, submissions, ACQUIRED, ACQUIRED, form_filter="10-Q")
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert "UNSUPPORTED_FORM" in str(result["excluded"])


@pytest.mark.parametrize("taxonomy,concept,unit", [
    ("us-gaap", "Revenues", "USD"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
    ("ifrs-full", "Revenue", "EUR"),
    ("us-gaap", "NetIncomeLoss", "USD"), ("ifrs-full", "ProfitLoss", "EUR"),
    ("us-gaap", "OperatingIncomeLoss", "USD"), ("us-gaap", "FreeCashFlow", "USD"),
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD"),
    ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "USD"),
    ("us-gaap", "EarningsPerShareDiluted", "USD/shares"),
    ("us-gaap", "EarningsPerShareBasic", "USD/shares"),
])
def test_supported_duration_fact_requires_start_before_old_converter(taxonomy, concept, unit):
    row = fact()
    del row["start"]
    facts, submissions = payloads()
    facts["facts"] = {taxonomy: {concept: {"units": {unit: [row]}}}}
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert result["selected_input_facts"] == []
    assert "MISSING_DURATION_START" in str(result["excluded"])
    assert result["revision_candidates"][0]["source_row"] == row


@pytest.mark.parametrize("concept,unit,raw_field", [
    ("CashAndCashEquivalentsAtCarryingValue", "USD", "cash"),
    ("LongTermDebt", "USD", "total_debt"), ("LongTermDebtNoncurrent", "USD", "total_debt"),
    ("StockholdersEquity", "USD", "equity"),
    ("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "USD", "equity"),
    ("CommonStockSharesOutstanding", "shares", "shares"),
])
def test_instant_fact_does_not_require_duration_start(concept, unit, raw_field):
    row = fact()
    del row["start"]
    facts, submissions = payloads()
    facts["facts"] = {"us-gaap": {concept: {"units": {unit: [row]}}}}
    result = build_input("nvda", facts, submissions, ACQUIRED, ACQUIRED)
    assert result["status"] == "READY"
    assert result["raw_fundamentals"][raw_field] == 100
    assert result["selected_input_facts"][0]["start"] == ""


@pytest.mark.parametrize("form,form_filter", [
    ("10-Q-NONSENSE", "10-Q"), ("10-Q/A/FOO", "10-Q"), ("6-K/A", "10-Q"),
    ("10-K-NONSENSE", "10-K"), ("40-F/A", "10-K"),
])
def test_m1_requires_exact_form_allowlist_in_index_and_facts(form, form_filter):
    row = fact(form=form)
    if form_filter == "10-Q":
        row["start"] = "2024-10-01"
    filings = [{"accessionNumber": ACCESSION, "form": form, "filingDate": "2025-02-01"}]
    result = run([row], filings, form_filter=form_filter)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["raw_fundamentals"] is None
    assert result["selected_input_facts"] == []
    assert result["form_filter"] == form_filter
    assert "UNSUPPORTED_FORM" in str(result["excluded"])


@pytest.mark.parametrize("form,form_filter", [
    ("10-K", "10-K"), ("10-K/A", "10-K"), ("20-F", "10-K"),
    ("20-F/A", "10-K"), ("40-F", "10-K"),
    ("10-Q", "10-Q"), ("10-Q/A", "10-Q"), ("6-K", "10-Q"),
])
def test_exact_supported_forms_remain_available(form, form_filter):
    row = fact(form=form)
    if form_filter == "10-Q":
        row["start"] = "2024-10-01"
    filings = [{"accessionNumber": ACCESSION, "form": form, "filingDate": "2025-02-01"}]
    result = run([row], filings, form_filter=form_filter)
    assert result["status"] == "READY"
    assert result["raw_fundamentals"]["revenue"] == 100


def test_conflicting_latest_revision_blocks_older_value_fallback():
    newer = "0001045810-25-000002"
    rows = [fact(), fact(accn=newer, filed="2025-02-02", val=90),
            fact(accn=newer, filed="2025-02-02", val=80)]
    filings = [{"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"},
               {"accessionNumber": newer, "form": "10-K", "filingDate": "2025-02-02"}]
    result = run(rows, filings)
    assert result["status"] == "NOT_AVAILABLE"
    assert result["selected_input_facts"] == []
    assert len(result["revision_candidates"]) == 3
    assert "AMBIGUOUS_FACT_VALUES" in str(result["excluded"])


def test_strictly_later_filing_day_can_resolve_observed_value_conflict():
    newer, resolved = "0001045810-25-000002", "0001045810-25-000003"
    rows = [fact(), fact(accn=newer, filed="2025-02-02", val=90),
            fact(accn=newer, filed="2025-02-02", val=80),
            fact(accn=resolved, filed="2025-02-03", val=70)]
    filings = [{"accessionNumber": r["accn"], "form": "10-K", "filingDate": r["filed"]} for r in rows]
    result = run(rows, filings)
    assert result["status"] == "READY"
    assert result["raw_fundamentals"]["revenue"] == 70
    assert len(result["selected_input_facts"]) == 1
    assert len(result["revision_candidates"]) == 4


@pytest.mark.parametrize("resolved_acceptance,status", [(None, "NOT_AVAILABLE"), ("2025-02-02T19:00:00Z", "READY")])
def test_same_day_revision_needs_proven_later_order_to_resolve_conflict(resolved_acceptance, status):
    newer, resolved = "0001045810-25-000002", "0001045810-25-000003"
    rows = [fact(), fact(accn=newer, filed="2025-02-02", val=90),
            fact(accn=newer, filed="2025-02-02", val=80),
            fact(accn=resolved, filed="2025-02-02", val=70)]
    filings = [
        {"accessionNumber": ACCESSION, "form": "10-K", "filingDate": "2025-02-01"},
        {"accessionNumber": newer, "form": "10-K", "filingDate": "2025-02-02",
         "acceptanceDateTime": "2025-02-02T18:00:00Z"},
        {"accessionNumber": resolved, "form": "10-K", "filingDate": "2025-02-02",
         "acceptanceDateTime": resolved_acceptance},
    ]
    result = run(rows, filings)
    assert result["status"] == status
    assert len(result["revision_candidates"]) == 4
    if status == "READY":
        assert result["raw_fundamentals"]["revenue"] == 70
    else:
        assert result["selected_input_facts"] == []
