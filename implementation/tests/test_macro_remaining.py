"""Author-created synthetic payloads only; no network, credentials or observations."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib
import importlib.util
import json

import pytest

NOW = datetime(2032, 3, 18, 20, tzinfo=timezone.utc)
MODULE = "investment_system.providers.macro_remaining"
FED_URL = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=sdmx"
MTS_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_1"
MESSAGE = "http://www.SDMX.org/resources/SDMXML/schemas/v1_0/message"
FED = "http://www.federalreserve.gov/structure/compact/H41_H41"
COMMON = "http://www.federalreserve.gov/structure/compact/common"


def api():
    assert importlib.util.find_spec(MODULE) is not None, "remaining parser module is missing"
    return importlib.import_module(MODULE)


def binding(a, provider="TREASURY_MTS", **changes):
    fed = provider != "TREASURY_MTS"
    defaults = dict(axis={"FED_H41": "Liquidity", "FED_H8": "Credit", "FED_H10": "FX", "TREASURY_MTS": "Fiscal"}[provider],
                    provider=provider, unit="Currency" if fed else "Millions of USD", frequency="W" if fed else "M",
                    seasonal_adjustment="NOT_APPLICABLE" if fed else "NSA", basis="SYNTHETIC_EXPLICIT_BASIS", observation_field="OBS_VALUE" if fed else "amount",
                    period_field="TIME_PERIOD" if fed else "reporting_period", source_id="SYNTHETIC_SERIES" if fed else None,
                    field_filters=(("CATEGORY", "SYNTHETIC"), ("SUBCATEGORY", "SYNTHETIC"), ("COMPONENT", "SYNTHETIC"), ("DISTRIBUTION", "SYNTHETIC"), ("SERIESTYPE", "L"), ("CURRENCY", "USD")) if fed else (("line_code", "SYNTHETIC_TOTAL"),),
                    table_path=None if fed else "mts_table_1", source_frequency="19" if fed else None, unit_multiplier=Decimal("1000000") if fed else None,
                    dataset_id="SYNTHETIC_DATASET" if fed else None)
    defaults.update(changes)
    return a.RemainingSeriesBinding(**defaults)


def receipt(a, body, provider="TREASURY_MTS", **changes):
    url = MTS_URL if provider == "TREASURY_MTS" else FED_URL.replace("H41", {"FED_H41": "H41", "FED_H8": "H8", "FED_H10": "H10"}[provider])
    defaults = dict(provider=provider, source_url=url, response_sha256=hashlib.sha256(body).hexdigest(), acquired_at=NOW,
                    synthetic=True, rights_status="CLEARED_SCOPE")
    defaults.update(changes)
    return a.GovernmentReceipt(**defaults)


def mts_payload(rows=None, pages=1):
    return {"data": rows if rows is not None else [{"line_code": "SYNTHETIC_TOTAL", "reporting_period": "2032-02", "record_date": "2032-03-10", "amount": "12.50"}],
            "meta": {"total-pages": pages, "labels": {"amount": "Synthetic amount"}, "dataTypes": {"amount": "CURRENCY"}, "dataFormats": {"amount": "Currency"}}}


def mts(a, obj=None, **changes):
    body = json.dumps(mts_payload() if obj is None else obj).encode()
    b = changes.pop("binding", binding(a))
    return a.parse_treasury_mts(body, receipt(a, body, **changes), b)


def fed_body(value="12.50", period="2032-03-17", extra="", root_ns=MESSAGE, data_ns=FED):
    common_ns = COMMON if root_ns == MESSAGE else root_ns
    return (f'<c:DataSet xmlns:f="{data_ns}" xmlns:c="{common_ns}" id="SYNTHETIC_DATASET">'
            '<f:Series SERIES_NAME="SYNTHETIC_SERIES" FREQ="19" UNIT="Currency" UNIT_MULT="1000000" CURRENCY="USD" CATEGORY="SYNTHETIC" SUBCATEGORY="SYNTHETIC" COMPONENT="SYNTHETIC" DISTRIBUTION="SYNTHETIC" SERIESTYPE="L">'
            f'<c:Obs TIME_PERIOD="{period}" OBS_VALUE="{value}" OBS_STATUS="P"/>{extra}</f:Series></c:DataSet>').encode()


def fed(a, body=None, provider="FED_H41", **changes):
    body = fed_body() if body is None else body
    b = changes.pop("binding", binding(a, provider))
    return a.parse_fed_sdmx(body, receipt(a, body, provider, **changes), b)


def unavailable(result, reason):
    assert result.state == "NOT_AVAILABLE"
    assert result.observations == ()
    assert reason in result.reason_codes


def test_missing_module_contract_is_explicit():
    a = api()
    assert all(hasattr(a, name) for name in ("RemainingSeriesBinding", "GovernmentReceipt", "RemainingObservation", "RemainingParseResult", "parse_fed_sdmx", "parse_treasury_mts", "select_remaining_observed"))


def test_treasury_exact_selector_parses_decimal_without_transforming_unit():
    a = api()
    result = mts(a)
    assert result.state == "RAW_EVIDENCE" and result.reason_codes == ()
    obs, = result.observations
    assert obs.value == Decimal("12.50") and str(obs.value) == "12.50"
    assert obs.observation_period == "2032-02" and obs.unit == "Millions of USD"
    assert obs.axis == "Fiscal" and obs.provider == "TREASURY_MTS"
    assert obs.available_at == obs.vintage_at == obs.ingested_at == NOW
    assert obs.availability_basis == "OBSERVED_CAPTURE_UPPER_BOUND"
    assert obs.vintage_kind == "OBSERVED_CAPTURE"


def test_fed_exact_series_parses_official_compact_fields_and_metadata():
    a = api()
    result = fed(a)
    obs, = result.observations
    assert result.state == "RAW_EVIDENCE" and obs.value == Decimal("12.50")
    assert obs.observation_period == "2032-03-17" and obs.frequency == "W"
    assert ("UNIT_MULT", "1000000") in obs.source_metadata
    assert obs.unit_multiplier == Decimal("1000000")
    assert ("CURRENCY", "USD") in obs.source_metadata
    assert ("OBS_STATUS", "P") in obs.source_metadata
    for provider, filters, attributes, seasonal in (
            ("FED_H8", (("SA", "NSA"), ("BG", "SYNTHETIC"), ("H8_UNITS", "LEVEL"), ("CATEGORY", "SYNTHETIC"), ("ITEM", "SYNTHETIC"), ("CURRENCY", "USD")),
             b' SA="NSA" BG="SYNTHETIC" H8_UNITS="LEVEL" ITEM="SYNTHETIC"', "NSA"),
            ("FED_H10", (("FX", "SYNTHETIC_PAIR"), ("CURRENCY", "USD")), b' FX="SYNTHETIC_PAIR"', "NOT_APPLICABLE")):
        release = provider.removeprefix("FED_")
        body = fed_body().replace(b'H41_H41', (release + "_" + release).encode()).replace(b' SERIESTYPE="L"', attributes)
        selected = binding(a, provider, field_filters=filters, seasonal_adjustment=seasonal)
        parsed = fed(a, body, provider, binding=selected)
        assert parsed.state == "RAW_EVIDENCE" and parsed.observations[0].provider == provider


def test_fed_filters_require_exact_matching_series_metadata():
    a = api()
    selected = binding(a, "FED_H41", source_id=None)
    selected = replace(selected, field_filters=selected.field_filters + (("SERIES_NAME", "SYNTHETIC_SERIES"),))
    assert fed(a, binding=selected).state == "RAW_EVIDENCE"
    unavailable(fed(a, binding=replace(selected, field_filters=tuple((key, "EUR" if key == "CURRENCY" else value) for key, value in selected.field_filters))), "MISSING_SOURCE")


def test_contract_dataclasses_are_immutable_and_sensitive_fields_are_hidden():
    a = api()
    body = json.dumps(mts_payload()).encode()
    r = receipt(a, body)
    result = mts(a)
    with pytest.raises(FrozenInstanceError):
        r.synthetic = False
    with pytest.raises(FrozenInstanceError):
        result.observations[0].value = Decimal(0)
    assert MTS_URL not in repr(r) and "12.50" not in repr(result)
    assert MTS_URL not in repr(result.observations[0])


def test_unbound_inputs_are_never_adopted():
    a = api()
    body = json.dumps(mts_payload()).encode()
    unavailable(a.parse_treasury_mts(body, receipt(a, body), None), "UNADOPTED_INPUT_SELECTION")
    unavailable(mts(a, binding=binding(a, field_filters=(), source_id=None)), "UNADOPTED_INPUT_SELECTION")


def test_binding_axis_provider_mismatch_is_unadopted():
    a = api()
    unavailable(mts(a, binding=binding(a, axis="Credit")), "UNADOPTED_INPUT_SELECTION")


def test_binding_requires_every_semantic_field():
    a = api()
    for name in ("unit", "frequency", "seasonal_adjustment", "basis", "observation_field", "period_field"):
        unavailable(mts(a, binding=binding(a, **{name: ""})), "UNADOPTED_INPUT_SELECTION")


def test_binding_duplicate_or_mutable_filters_are_rejected():
    a = api()
    for filters in ([('line_code', 'SYNTHETIC_TOTAL')], (("line_code", "x"), ("line_code", "y"))):
        unavailable(mts(a, binding=binding(a, field_filters=filters)), "UNADOPTED_INPUT_SELECTION")


def test_treasury_table_and_period_basis_must_be_explicit():
    a = api()
    unavailable(mts(a, binding=binding(a, table_path=None)), "UNADOPTED_INPUT_SELECTION")
    unavailable(mts(a, binding=binding(a, period_field="record_date")), "UNADOPTED_INPUT_SELECTION")


def test_receipt_hash_and_provider_are_validated():
    a = api()
    unavailable(mts(a, response_sha256="0" * 64), "INVALID_RECEIPT")
    body = json.dumps(mts_payload()).encode()
    unavailable(a.parse_treasury_mts(body, receipt(a, body, provider="FED_H41"), binding(a)), "INVALID_RECEIPT")


def test_receipt_requires_aware_capture_and_cleared_scope():
    a = api()
    unavailable(mts(a, acquired_at=NOW.replace(tzinfo=None)), "INVALID_TIMESTAMP")
    unavailable(mts(a, rights_status="UNCONFIRMED"), "RIGHTS_UNCONFIRMED")


def test_treasury_source_family_rejects_host_path_query_and_credentials_lookalikes():
    a = api()
    urls = [MTS_URL.replace("api.fiscaldata.treasury.gov", "api.fiscaldata.treasury.gov.example.org"),
            MTS_URL.replace("https://", "http://"), MTS_URL + "/extra", MTS_URL + "?api_key=SYNTHETIC_SECRET",
            MTS_URL.replace("mts_table_1", "mts_table_10"), MTS_URL + "#ignored",
            MTS_URL.replace("https://", "https://user:password@"), "https://api.stlouisfed.org/fred/series"]
    for url in urls:
        unavailable(mts(a, source_url=url), "INVALID_RECEIPT")


def test_fed_source_family_requires_release_and_sdmx_and_rejects_keys():
    a = api()
    for url in (FED_URL.replace("H41", "H8"), FED_URL.replace("sdmx", "csv"), FED_URL + "&key=SYNTHETIC_SECRET",
                FED_URL.replace("Output.aspx", "Output.aspx/extra"), FED_URL.replace("www.federalreserve.gov", "federalreserve.gov.evil.org")):
        unavailable(fed(a, source_url=url), "INVALID_RECEIPT")


def test_payload_type_and_size_fail_closed():
    a = api()
    unavailable(a.parse_treasury_mts("{}", None, binding(a)), "INVALID_RECEIPT")
    body = b" " * (a.MAX_PAYLOAD_BYTES + 1)
    unavailable(a.parse_treasury_mts(body, receipt(a, body), binding(a)), "PAYLOAD_TOO_LARGE")


def test_treasury_publication_date_is_metadata_only():
    a = api()
    obs, = mts(a).observations
    assert obs.observation_period == "2032-02"
    assert ("record_date", "2032-03-10") in obs.source_metadata
    assert obs.available_at == NOW


def test_treasury_only_selected_line_is_read_and_never_summed():
    a = api()
    rows = mts_payload()["data"] + [{"line_code": "SYNTHETIC_SUBTOTAL", "reporting_period": "2032-02", "amount": "500"}]
    result = mts(a, mts_payload(rows))
    assert len(result.observations) == 1 and result.observations[0].value == Decimal("12.50")


def test_treasury_selector_missing_field_is_not_a_default_total():
    a = api()
    unavailable(mts(a, binding=binding(a, field_filters=(("unknown_line", "total"),))), "MISSING_SOURCE")


def test_treasury_missing_values_are_unavailable_never_zero():
    a = api()
    for value in (None, "", "null", "NA", "N/A", "--", "..."):
        row = dict(mts_payload()["data"][0], amount=value)
        unavailable(mts(a, mts_payload([row])), "MISSING_VALUE")


def test_treasury_rejects_invalid_nonfinite_and_boolean_values():
    a = api()
    for value in ("NaN", "Infinity", "-Infinity", "1,000", True, 12.5, "private-sentinel"):
        row = dict(mts_payload()["data"][0], amount=value)
        result = mts(a, mts_payload([row]))
        unavailable(result, "INVALID_VALUE")
        assert "private-sentinel" not in repr(result)


def test_treasury_duplicate_json_fields_and_nonfinite_json_are_rejected():
    a = api()
    for body in (b'{"data": [], "data": [], "meta": {"total_pages": 1}}', b'{"data": [], "meta": {"total_pages": NaN}}'):
        unavailable(a.parse_treasury_mts(body, receipt(a, body), binding(a)), "SCHEMA_MISMATCH")


def test_treasury_declared_multiple_pages_are_incomplete():
    a = api()
    unavailable(mts(a, mts_payload(pages=2)), "INCOMPLETE_PAYLOAD")
    for changed in ({"meta": {"total-pages": 1, "total-count": 2}}, {"meta": {"total-pages": 1, "count": 2}},
                    {"links": {"next": "SYNTHETIC_NEXT_PAGE"}}, {"meta": {"total_pages": 1}}):
        obj = mts_payload()
        obj.update(changed)
        unavailable(mts(a, obj), "INCOMPLETE_PAYLOAD")


def test_treasury_malformed_meta_or_rows_are_rejected():
    a = api()
    for obj in ({"data": [], "meta": []}, {"data": {}, "meta": {"total-pages": 1}},
                {"data": [None], "meta": {"total-pages": 1}}, {"data": [], "meta": {"total-pages": "private"}}):
        unavailable(mts(a, obj), "SCHEMA_MISMATCH")


def test_treasury_period_is_explicit_and_frequency_validated():
    a = api()
    for period in ("2032-13", "0000-02", "2032-02-01", None):
        row = dict(mts_payload()["data"][0], reporting_period=period)
        unavailable(mts(a, mts_payload([row])), "SCHEMA_MISMATCH")


def test_treasury_equal_duplicates_are_deduplicated_but_conflicts_block():
    a = api()
    row = mts_payload()["data"][0]
    assert len(mts(a, mts_payload([row, dict(row, amount="12.500")])).observations) == 1
    unavailable(mts(a, mts_payload([row, dict(row, amount="13")])), "CONFLICTING_DUPLICATE")


def test_fed_namespace_root_and_shadow_fields_are_validated():
    a = api()
    for body in (fed_body(root_ns="urn:wrong"), fed_body(data_ns="urn:wrong"),
                 fed_body().replace(b'<c:Obs ', b'<bad:Obs xmlns:bad="urn:wrong" '),
                 fed_body().replace(b'id="SYNTHETIC_DATASET"', b'id="OTHER_DATASET"'),
                 b'<m:CompactData xmlns:m="' + MESSAGE.encode() + b'">' + fed_body() + b'</m:CompactData>'):
        unavailable(fed(a, body), "SCHEMA_MISMATCH")
    unavailable(fed(a, binding=binding(a, "FED_H41", dataset_id=None)), "UNADOPTED_INPUT_SELECTION")


def test_fed_dtd_and_entities_are_blocked_even_utf16():
    a = api()
    for body in (b'<!DOCTYPE x [<!ENTITY secret "private">]>' + fed_body(),
                 ('<!DOCTYPE x [<!ENTITY secret "private">]>' + fed_body().decode()).encode("utf-16")):
        unavailable(fed(a, body), "UNSAFE_XML")


def test_fed_semantic_metadata_mismatch_is_unavailable():
    a = api()
    for field, value in (("UNIT", "Percent"), ("FREQ", "20"), ("UNIT_MULT", "1000")):
        original = {"UNIT": "Currency", "FREQ": "19", "UNIT_MULT": "1000000"}[field]
        unavailable(fed(a, fed_body().replace(f'{field}="{original}"'.encode(), f'{field}="{value}"'.encode())), "SCHEMA_MISMATCH")
    unavailable(fed(a, binding=binding(a, "FED_H41", field_filters=tuple((k, v) for k, v in binding(a, "FED_H41").field_filters if k != "CURRENCY"))), "SCHEMA_MISMATCH")


def test_fed_missing_observation_and_series_are_not_zero():
    a = api()
    unavailable(fed(a, fed_body("ND")), "MISSING_VALUE")
    unavailable(fed(a, binding=binding(a, "FED_H41", source_id="OTHER_SERIES")), "MISSING_SOURCE")


def test_fed_conflicting_duplicate_obs_blocks_series():
    a = api()
    extra = '<c:Obs TIME_PERIOD="2032-03-17" OBS_VALUE="13"/>'
    unavailable(fed(a, fed_body(extra=extra)), "CONFLICTING_DUPLICATE")
    extra = '<c:Obs TIME_PERIOD="2032-03-17" OBS_VALUE="12.50" OBS_STATUS="R"/>'
    unavailable(fed(a, fed_body(extra=extra)), "CONFLICTING_DUPLICATE")


def test_selection_combines_axes_and_is_deterministic():
    a = api()
    first, second = mts(a), fed(a)
    forward = a.select_remaining_observed((first, second), NOW)
    backward = a.select_remaining_observed((second, first), NOW)
    assert forward == backward and forward.state == "RAW_EVIDENCE"
    assert len(forward.observations) == 2
    selected = binding(a, "FED_H41")
    reordered = fed(a, binding=replace(selected, field_filters=tuple(reversed(selected.field_filters))))
    identical = a.select_remaining_observed((second, reordered), NOW)
    assert identical.observations == second.observations and "CONFLICTING_VINTAGE" not in identical.reason_codes


def test_selection_uses_latest_eligible_capture_and_retains_future_reason():
    a = api()
    older = mts(a, acquired_at=NOW - timedelta(days=1))
    current = mts(a)
    future = mts(a, acquired_at=NOW + timedelta(days=1))
    result = a.select_remaining_observed((older, current, future), NOW)
    assert result.observations == current.observations
    assert "AVAILABLE_AFTER_AS_OF" in result.reason_codes


def test_selection_conflicting_same_capture_blocks_source():
    a = api()
    conflicting = mts_payload([dict(mts_payload()["data"][0], amount="13")])
    unavailable(a.select_remaining_observed((mts(a), mts(a, conflicting)), NOW), "CONFLICTING_VINTAGE")


def test_selection_future_conflict_cannot_remove_known_capture():
    a = api()
    known = mts(a)
    future = NOW + timedelta(days=1)
    revised = mts_payload([dict(mts_payload()["data"][0], amount="13")])
    result = a.select_remaining_observed((known, mts(a, acquired_at=future), mts(a, revised, acquired_at=future)), NOW)
    assert result.observations == known.observations
    assert "CONFLICTING_VINTAGE" not in result.reason_codes


def test_selection_rejects_mixed_synthetic_including_empty_results():
    a = api()
    real = mts(a, synthetic=False)
    empty = a.RemainingParseResult("NOT_AVAILABLE", (), ("MISSING_SOURCE",), True)
    unavailable(a.select_remaining_observed((real, empty), NOW), "MIXED_SYNTHETIC_INPUT")


def test_selection_revalidates_receipt_url_rights_and_bound_metadata():
    a = api()
    result = mts(a)
    original, = result.observations
    for changes, reason in (({"source_url": "https://fred.stlouisfed.org/series/x"}, "INVALID_RECEIPT"),
                            ({"rights_status": "UNCONFIRMED"}, "RIGHTS_UNCONFIRMED"),
                            ({"unit": "unknown"}, "SCHEMA_MISMATCH"),
                            ({"binding": None}, "UNADOPTED_INPUT_SELECTION")):
        altered = replace(result, observations=(replace(original, **changes),))
        unavailable(a.select_remaining_observed((altered,), NOW), reason)


def test_selection_validates_time_order_period_and_finite_decimal():
    a = api()
    result = mts(a)
    original, = result.observations
    for changes, reason in (({"vintage_at": NOW - timedelta(seconds=1)}, "INVALID_TIME_ORDER"),
                            ({"available_at": NOW.replace(tzinfo=None)}, "INVALID_TIMESTAMP"),
                            ({"observation_period": "2032-13"}, "SCHEMA_MISMATCH"),
                            ({"value": Decimal("sNaN")}, "INVALID_VALUE")):
        altered = replace(result, observations=(replace(original, **changes),))
        unavailable(a.select_remaining_observed((altered,), NOW), reason)


def test_selection_rejects_invalid_result_shapes_without_raw_reason_echo():
    a = api()
    for result in (None, a.RemainingParseResult("RAW_EVIDENCE", (), (), True),
                   a.RemainingParseResult("NOT_AVAILABLE", (), ("private-sentinel",), True)):
        selected = a.select_remaining_observed((result,), NOW)
        unavailable(selected, "INVALID_RESULT")
        assert "private-sentinel" not in repr(selected)


def test_selection_rejects_identity_collision_and_invalid_cutoff():
    a = api()
    result = mts(a)
    obs, = result.observations
    collision = replace(result, observations=(replace(obs, value=Decimal("99")),))
    unavailable(a.select_remaining_observed((result, collision), NOW), "OBSERVATION_ID_COLLISION")
    unavailable(a.select_remaining_observed((result,), NOW.replace(tzinfo=None)), "INVALID_TIMESTAMP")
    unavailable(a.select_remaining_observed([result], NOW), "INVALID_REQUEST")
    for field in ("source_id", "axis", "unit", "provider"):
        first = replace(result, observations=(replace(obs, **{field: Decimal("sNaN")}),))
        second = replace(result, observations=(replace(obs, **{field: Decimal("1")}),))
        unavailable(a.select_remaining_observed((first, second), NOW), "OBSERVATION_ID_COLLISION")


def test_fiscal_distinct_value_columns_have_distinct_source_identities():
    a = api()
    row = dict(mts_payload()["data"][0], outlays="20")
    first = mts(a, mts_payload([row]))
    second = mts(a, mts_payload([row]), binding=binding(a, observation_field="outlays"))
    assert first.observations[0].source_id != second.observations[0].source_id
    result = a.select_remaining_observed((first, second), NOW)
    assert len(result.observations) == 2 and "CONFLICTING_VINTAGE" not in result.reason_codes
