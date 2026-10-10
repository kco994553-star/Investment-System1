"""Synthetic-only screen boundary and unchanged existing regime thresholds."""
from datetime import datetime, timezone, timedelta
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import math
import hashlib

import pytest

from investment_system.macro.government_screen import (
    build_government_macro_screen, evaluate_synthetic_macro_inputs,
)
from investment_system.macro.primary_contract import SourceReceipt
from investment_system.providers.macro_primary import parse_bls, parse_bea_nipa, parse_treasury_yields

NOW = datetime(2026, 1, 8, 17, tzinfo=timezone.utc)


def all_results():
    def receipt(provider, url, body):
        return SourceReceipt(provider, url, hashlib.sha256(body).hexdigest(), NOW, True, "CLEARED_SCOPE")
    ids = ("CUSR0000SA0", "CUUR0000SA0", "CES0000000001", "LNS14000000")
    body = json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": [
        {"seriesID": s, "data": [{"year": "2025", "period": "M11", "value": "123.45", "footnotes": []}]} for s in ids]}}).encode()
    results = [parse_bls(body, receipt("BLS", "https://api.bls.gov/publicAPI/v1/timeseries/data/", body), expected_series_ids=ids)]
    for table in ("T10106", "T10101"):
        body = json.dumps({"BEAAPI": {"Request": {"RequestParam": [{"ParameterName": "USERID", "ParameterValue": "SYNTHETIC_PRIVATE_SENTINEL"}]}, "Results": {"Data": [
            {"TableName": table, "LineNumber": "1", "TimePeriod": "2025Q3", "SeriesCode": "SYNTHETIC_GDP", "LineDescription": "Synthetic GDP", "Metric_Name": "Dollars" if table == "T10106" else "Percent change", "CL_UNIT": "Billions" if table == "T10106" else "Percent", "UNIT_MULT": "9" if table == "T10106" else "0", "DataValue": "123.4"}]}}}).encode()
        results.append(parse_bea_nipa(body, receipt("BEA", "https://apps.bea.gov/api/data", body), expected_table=table))
    body = b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><entry><content><m:properties><d:NEW_DATE>2026-01-07T00:00:00</d:NEW_DATE><d:BC_10YEAR>2.75</d:BC_10YEAR></m:properties></content></entry></feed>'
    results.append(parse_treasury_yields(body, receipt("TREASURY", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml", body)))
    return tuple(results)


@pytest.mark.parametrize("growth,inflation,state,regime", [
    (0.04, 0.02, "NORMAL", "EXPANSION"),
    (-0.01, 0.06, "WARNING", "STAGFLATION_RISK"),
    (0.1, 0.09, "EMERGENCY", "INFLATION_SHOCK"),
    (0.03, 0.03, "NORMAL", "NEUTRAL"),
    (-0.01, 0.05, "NORMAL", "NEUTRAL"),
    (0, 0.08, "NORMAL", "NEUTRAL"),
])
def test_existing_engine_thresholds(growth, inflation, state, regime):
    inputs = {"growth": growth, "inflation": inflation}
    before = deepcopy(inputs)
    result = evaluate_synthetic_macro_inputs(inputs, NOW)
    assert result["state"] == "SYNTHETIC_CHECK"
    assert (result["macro_state"], result["regime"]) == (state, regime)
    assert result["macro_version"] == "v0.1.1"
    assert result["synthetic"] is True
    assert result["model_status"] == "NOT_APPLIED"
    assert inputs == before


@pytest.mark.parametrize("inputs", [
    {}, {"growth": 0.02}, {"inflation": 0.02},
    {"growth": True, "inflation": 0.02},
    {"growth": "0.02", "inflation": 0.02},
    {"growth": None, "inflation": 0.02},
    {"growth": math.nan, "inflation": 0.02},
    {"growth": math.inf, "inflation": 0.02},
    {"growth": 10**1000, "inflation": 0.02},
    {"growth": 0.02, "inflation": 0.02, "price": 5},
    None, [],
])
def test_missing_invalid_or_extra_input_never_becomes_normal(inputs):
    result = evaluate_synthetic_macro_inputs(inputs, NOW)
    assert result["state"] == "NOT_AVAILABLE"
    assert result["regime"] is result["macro_state"] is None


def test_naive_cutoff_is_unavailable():
    result = evaluate_synthetic_macro_inputs({"growth": 0, "inflation": 0}, NOW.replace(tzinfo=None))
    assert result["state"] == "NOT_AVAILABLE"
    assert "INVALID_TIMESTAMP" in result["reason_codes"]


def test_empty_grid_has_48_null_cells_without_default_regime():
    result = build_government_macro_screen((), NOW)
    assert len(result["cells"]) == 48
    assert all(c["value"] is None for c in result["cells"])
    assert result["regime"]["state"] == "NOT_AVAILABLE"
    assert result["regime"]["macro_state"] is None
    assert result["model_status"] == "NOT_APPLIED"
    json.dumps(result, allow_nan=False)


def test_primary_raw_data_is_json_safe_and_not_engine_fractions():
    results = all_results()
    result = build_government_macro_screen(results, NOW)
    levels = [c for c in result["cells"] if c["dimension"] == "Level"]
    assert sum(c["state"] == "RAW_EVIDENCE" for c in levels) == 4
    assert len(result["observations"]) == 7
    assert all(isinstance(o["value"], str) for o in result["observations"])
    assert result["regime"]["reason_codes"] == ["UNAPPROVED_ENGINE_INPUT_MAPPING"]
    text = json.dumps(result, allow_nan=False)
    assert "SYNTHETIC_PRIVATE_SENTINEL" not in text
    assert "source_notes" not in text and "source_url" not in text
    assert result["pit_status"] == "OBSERVED_BOUND_ONLY"
    assert all(o["availability_basis"] == "OBSERVED_CAPTURE_UPPER_BOUND" for o in result["observations"])


def test_future_capture_is_not_presented_as_known():
    result = build_government_macro_screen(all_results(), NOW - timedelta(seconds=1))
    assert result["observations"] == []
    assert result["regime"]["state"] == "NOT_AVAILABLE"
    assert "AVAILABLE_AFTER_AS_OF" in result["reason_codes"]


def test_invalid_primary_input_does_not_escape_as_json():
    result = build_government_macro_screen((object(),), NOW)
    assert result["observations"] == []
    assert result["state"] == "NOT_AVAILABLE"


def test_each_call_produces_independent_containers():
    first = build_government_macro_screen((), NOW)
    first["cells"][0]["reason_codes"].append("LOCAL_EDIT")
    assert "LOCAL_EDIT" not in build_government_macro_screen((), NOW)["cells"][0]["reason_codes"]


def remaining_results(*, synthetic=True, acquired_at=NOW):
    from investment_system.providers.macro_remaining import (
        RemainingSeriesBinding, GovernmentReceipt, parse_fed_sdmx, parse_treasury_mts,
    )
    results = []
    for release, axis, filters, seasonal in (
        ("H41", "Liquidity", {"CATEGORY": "SYNTHETIC", "SUBCATEGORY": "SYNTHETIC", "COMPONENT": "SYNTHETIC", "DISTRIBUTION": "SYNTHETIC", "SERIESTYPE": "L", "CURRENCY": "USD"}, "NOT_APPLICABLE"),
        ("H8", "Credit", {"SA": "SA", "BG": "SYNTHETIC", "H8_UNITS": "LEVEL", "CATEGORY": "SYNTHETIC", "ITEM": "SYNTHETIC", "CURRENCY": "USD"}, "SA"),
        ("H10", "FX", {"FX": "SYNTHETIC", "CURRENCY": "USD"}, "NOT_APPLICABLE"),
    ):
        provider = "FED_" + release
        attrs = {"SERIES_NAME": "SYNTHETIC_SERIES", "FREQ": "19", "UNIT": "Currency", "UNIT_MULT": "1000000", **filters}
        rendered = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        body = (f'<c:DataSet xmlns:c="http://www.federalreserve.gov/structure/compact/common" xmlns:f="http://www.federalreserve.gov/structure/compact/{release}_{release}" id="SYNTHETIC_DATASET"><f:Series {rendered}><c:Obs TIME_PERIOD="2026-01-07" OBS_VALUE="12.50"/></f:Series></c:DataSet>').encode()
        binding = RemainingSeriesBinding(axis, provider, "Currency", "W", seasonal,
            "SYNTHETIC_EXPLICIT_BASIS", "OBS_VALUE", "TIME_PERIOD", source_id="SYNTHETIC_SERIES",
            field_filters=tuple(filters.items()), source_frequency="19", unit_multiplier=Decimal("1000000"), dataset_id="SYNTHETIC_DATASET")
        receipt = GovernmentReceipt(provider, f"https://www.federalreserve.gov/datadownload/Output.aspx?rel={release}&filetype=sdmx&type=package", hashlib.sha256(body).hexdigest(), acquired_at, synthetic, "CLEARED_SCOPE")
        results.append(parse_fed_sdmx(body, receipt, binding))
    body = json.dumps({"data": [{"line_code": "SYNTHETIC", "reporting_period": "2025-12", "amount": "-12.50", "record_date": "2026-01-07"}], "meta": {"total-pages": 1, "total-count": 1, "count": 1}}).encode()
    binding = RemainingSeriesBinding("Fiscal", "TREASURY_MTS", "Millions of USD", "M", "NSA", "SYNTHETIC_MONTHLY_FLOW", "amount", "reporting_period", field_filters=(("line_code", "SYNTHETIC"),), table_path="mts_table_1")
    receipt = GovernmentReceipt("TREASURY_MTS", "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1", hashlib.sha256(body).hexdigest(), acquired_at, synthetic, "CLEARED_SCOPE")
    results.append(parse_treasury_mts(body, receipt, binding))
    return tuple(results)


def test_all_eight_axis_raw_levels_remain_unscored_and_json_safe():
    result = build_government_macro_screen(all_results(), NOW, remaining_results())
    levels = [c for c in result["cells"] if c["dimension"] == "Level"]
    assert all(c["state"] == "RAW_EVIDENCE" for c in levels)
    assert all(c["value"] is None for c in result["cells"])
    assert result["regime"]["state"] == "NOT_AVAILABLE"
    fed = [o for o in result["observations"] if o["provider"].startswith("FED_")]
    assert all(o["unit_multiplier"] == "1000000" and o["value"] == "12.50" for o in fed)
    assert next(o for o in result["observations"] if o["axis"] == "Fiscal")["value"] == "-12.50"
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("mixed_side", ["primary", "remaining", "across"])
def test_mixed_input_package_is_fully_blocked(mixed_side):
    primary, remaining = all_results(), remaining_results()
    if mixed_side == "primary":
        second = replace(primary[0], synthetic=False, observations=tuple(replace(o, synthetic=False) for o in primary[0].observations))
        primary = primary + (second,)
    elif mixed_side == "remaining":
        remaining += remaining_results(synthetic=False)
    else:
        remaining = remaining_results(synthetic=False)
    result = build_government_macro_screen(primary, NOW, remaining)
    assert result["observations"] == []
    assert result["state"] == "NOT_AVAILABLE"
    assert "MIXED_SYNTHETIC_INPUT" in result["reason_codes"]
    assert all(c["state"] == "NOT_AVAILABLE" and not c["evidence_ids"] for c in result["cells"])


def test_remaining_future_capture_does_not_fill_the_four_other_levels():
    result = build_government_macro_screen(all_results(), NOW, remaining_results(acquired_at=NOW + timedelta(seconds=1)))
    assert sum(c["state"] == "RAW_EVIDENCE" for c in result["cells"]) == 4
    assert "AVAILABLE_AFTER_AS_OF" in result["reason_codes"]
