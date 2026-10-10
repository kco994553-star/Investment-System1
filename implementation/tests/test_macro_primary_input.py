"""Author-created synthetic fixtures; no provider data or IO."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import builtins
import hashlib
import importlib
import importlib.util
import json
import logging
import socket
from types import SimpleNamespace
import pytest

NOW = datetime(2026, 1, 8, 17, tzinfo=timezone.utc)
BLS = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BEA = "https://apps.bea.gov/api/data"
TREASURY = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
BLS_IDS = ("CUSR0000SA0", "CUUR0000SA0", "CES0000000001", "LNS14000000")
ALL_IDS = tuple("BLS:" + s for s in BLS_IDS) + ("BEA:NIPA:T10106:1:Q", "BEA:NIPA:T10101:1:Q", "TREASURY:daily_treasury_yield_curve:BC_10YEAR")
AXES = ("Growth", "Inflation", "Liquidity", "Monetary Policy", "Credit", "Labor", "Fiscal", "FX")
DIMS = ("Level", "Direction", "Momentum", "Surprise", "Stress", "Confidence")
SENTINEL = "SYNTHETIC_PRIVATE_SENTINEL"


def api():
    names = ("investment_system.macro.primary_contract", "investment_system.providers.macro_primary", "investment_system.macro.primary_input")
    assert all(importlib.util.find_spec(name) is not None for name in names), "primary input modules are missing"
    merged = {}
    for name in names:
        merged.update(vars(importlib.import_module(name)))
    return SimpleNamespace(**merged)


def encoded(obj):
    return json.dumps(obj).encode()


def receipt(a, provider, body, **changes):
    r = a.SourceReceipt(provider=provider, source_url={"BLS": BLS, "BEA": BEA, "TREASURY": TREASURY}[provider], response_sha256=hashlib.sha256(body).hexdigest(), acquired_at=NOW, synthetic=True, rights_status="CLEARED_SCOPE")
    return replace(r, **changes)


def bls_payload(ids=BLS_IDS, value="123.45"):
    return {"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": s, "data": [{"year": "2025", "period": "M11", "value": value, "footnotes": [{"code": "P", "text": "Synthetic provisional observation"}]}]} for s in ids]}}


def bls(a, payload=None, ids=BLS_IDS, **changes):
    body = encoded(bls_payload(ids) if payload is None else payload)
    return a.parse_bls(body, receipt(a, "BLS", body, **changes), expected_series_ids=ids)


def bea_payload(table="T10106", value="1,234.5"):
    return {"BEAAPI": {"Request": {"RequestParam": [{"ParameterName": "USERID", "ParameterValue": SENTINEL}]}, "Results": {"Data": [{"TableName": table, "LineNumber": "1", "TimePeriod": "2025Q3", "SeriesCode": "SYNTHETIC_GDP", "LineDescription": "Synthetic real gross domestic product", "Metric_Name": "Chained dollars" if table == "T10106" else "Percent change", "CL_UNIT": "Billions of chained 2019 dollars" if table == "T10106" else "Percent", "UNIT_MULT": "9" if table == "T10106" else "0", "DataValue": value}], "Notes": [{"NoteRef": "1", "NoteText": "Synthetic note"}], "UTCProductionTime": "1900-01-01T00:00:00Z"}}}


def bea(a, payload=None, table="T10106", **changes):
    body = encoded(bea_payload(table) if payload is None else payload)
    return a.parse_bea_nipa(body, receipt(a, "BEA", body, **changes), expected_table=table)


def treasury_body(value="2.75", prefix="d", date="2026-01-07T00:00:00", null=False):
    attr = ' m:null="true"' if null else ""
    return (f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:{prefix}="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><entry><content><m:properties><{prefix}:NEW_DATE>{date}</{prefix}:NEW_DATE><{prefix}:BC_10YEAR{attr}>{value}</{prefix}:BC_10YEAR></m:properties></content></entry></feed>').encode()


def treasury(a, body=None, **changes):
    body = treasury_body() if body is None else body
    return a.parse_treasury_yields(body, receipt(a, "TREASURY", body, **changes))


def all_results(a):
    return (bls(a), bea(a), bea(a, table="T10101"), treasury(a))


def unavailable(result, reason):
    assert result.state == "NOT_AVAILABLE" and not result.observations
    assert reason in result.reason_codes


def test_fixed_request_plans_have_exact_official_hosts_and_parameters():
    a = api(); p = a.build_bls_plan(BLS_IDS, 2020, 2025)
    assert (p.provider, p.method, p.endpoint, p.state) == ("BLS", "POST", BLS, "PLANNED")
    assert json.loads(p.body) == {"seriesid": list(BLS_IDS), "startyear": "2020", "endyear": "2025"}
    for table in ("T10106", "T10101"):
        p = a.build_bea_plan(table, (2024, 2025))
        assert (p.method, p.endpoint) == ("GET", BEA)
        assert dict(p.public_parameters) == {"method": "GetData", "DataSetName": "NIPA", "TableName": table, "Frequency": "Q", "Year": "2024,2025", "ResultFormat": "JSON"}
    p = a.build_treasury_plan(2025)
    assert (p.method, p.endpoint, dict(p.public_parameters)) == ("GET", TREASURY, {"data": "daily_treasury_yield_curve", "field_tdr_date_value": "2025"})
    for table in ("ALL", "X", "T10106,T10101", "TableID=1", "https://example.invalid", "FRED", None, []):
        p = a.build_bea_plan(table, (2025,))
        assert (p.state, p.reason_codes, p.body) == ("NOT_AVAILABLE", ("INVALID_REQUEST",), None)


def test_bls_plan_enforces_v1_allowlist_and_span():
    a = api()
    assert a.build_bls_plan(BLS_IDS, 2016, 2025).state == "PLANNED"
    for args in [(BLS_IDS, 2015, 2025), (BLS_IDS, 2025, 2024), (BLS_IDS, True, 2025), (BLS_IDS, 2024.0, 2025), (BLS_IDS, 0, 2025), (("DGS10",), 2024, 2025), ((BLS_IDS[0], BLS_IDS[0]), 2024, 2025), ((), 2024, 2025), (([],), 2024, 2025)]:
        p = a.build_bls_plan(*args)
        assert (p.state, p.reason_codes, p.body) == ("NOT_AVAILABLE", ("INVALID_REQUEST",), None)
    for years in ((), (2025, 2024), (2025, 2025), (True,), (2025.0,), ("ALL",), None):
        assert a.build_bea_plan("T10106", years).reason_codes == ("INVALID_REQUEST",)
    for year in (True, None, "ALL", 2025.0, 0, 10000):
        assert a.build_treasury_plan(year).reason_codes == ("INVALID_REQUEST",)


def test_bea_plan_has_credential_slot_without_secret_or_network(monkeypatch):
    a = api()
    def forbidden(*args, **kwargs):
        pytest.fail("request planning performed IO")
    monkeypatch.setattr(socket, "socket", forbidden); monkeypatch.setattr(builtins, "open", forbidden)
    p = a.build_bea_plan("T10106", (2025,))
    assert p.state == "PLANNED" and p.credential_slot == "BEA_USERID" and p.body is None
    assert "UserID" not in dict(p.public_parameters) and SENTINEL not in repr(p)
    with pytest.raises(FrozenInstanceError):
        p.state = "NOT_AVAILABLE"


def test_receipt_hash_provider_rights_and_time_are_required():
    a = api(); body = encoded(bls_payload()); original = receipt(a, "BLS", body)
    for changes, reason in [({"response_sha256": "0" * 64}, "INVALID_RECEIPT"), ({"provider": "BEA"}, "INVALID_RECEIPT"), ({"source_url": BLS + "?private=" + SENTINEL}, "INVALID_RECEIPT"), ({"acquired_at": NOW.replace(tzinfo=None)}, "INVALID_TIMESTAMP"), ({"acquired_at": None}, "INVALID_TIMESTAMP"), ({"rights_status": "UNCONFIRMED"}, "RIGHTS_UNCONFIRMED"), ({"synthetic": 1}, "INVALID_RECEIPT"), ({"rights_status": []}, "INVALID_RECEIPT")]:
        unavailable(a.parse_bls(body, replace(original, **changes), expected_series_ids=BLS_IDS), reason)
    for parser, kwargs in ((a.parse_bls, {"expected_series_ids": BLS_IDS}), (a.parse_bea_nipa, {"expected_table": "T10106"}), (a.parse_treasury_yields, {})):
        unavailable(parser(body, None, **kwargs), "INVALID_RECEIPT")
        unavailable(parser(None, original, **kwargs), "INVALID_RECEIPT")
    unavailable(bls(a, acquired_at=datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1)))), "INVALID_TIMESTAMP")


def test_cpi_seasonal_and_nonseasonal_are_not_interchangeable():
    a = api(); first, second = bls(a, ids=BLS_IDS[:2]).observations
    assert (first.source_id, first.seasonal_adjustment, first.unit) == (ALL_IDS[0], "SA", "index 1982-84=100")
    assert (second.source_id, second.seasonal_adjustment, second.unit) == (ALL_IDS[1], "NSA", "index 1982-84=100")
    assert first.observation_id != second.observation_id
    result = bls(a, payload=bls_payload(BLS_IDS[:1]), ids=BLS_IDS[:2])
    assert result.missing_source_ids == (ALL_IDS[1],)
    level = next(c for c in a.build_evidence_grid((result,), NOW).cells if (c.axis, c.dimension) == ("Inflation", "Level"))
    assert level.state == "NOT_AVAILABLE" and "MISSING_SOURCE" in level.reason_codes


def test_labor_payroll_and_unemployment_keep_distinct_units():
    a = api(); obs = bls(a, ids=BLS_IDS[2:]).observations
    assert [(o.source_id, o.axis, o.unit) for o in obs] == [(ALL_IDS[2], "Labor", "thousands"), (ALL_IDS[3], "Labor", "percent")]
    assert all(o.seasonal_adjustment == "SA" and o.value == Decimal("123.45") for o in obs)
    cell = next(c for c in a.build_evidence_grid((bls(a, ids=BLS_IDS[2:]),), NOW).cells if (c.axis, c.dimension) == ("Labor", "Level"))
    assert cell.state == "RAW_EVIDENCE" and len(cell.evidence_ids) == 2 and cell.value is None


def test_bls_status_missing_series_and_annual_average():
    a = api(); p = bls_payload(BLS_IDS[:1])
    assert bls(a, p).missing_source_ids == ALL_IDS[1:4]
    p["status"] = "REQUEST_FAILED"; unavailable(bls(a, p), "PROVIDER_ERROR")
    p = bls_payload(); p["Results"]["series"][0]["data"].append({"year": "2025", "period": "M13", "value": "99", "footnotes": []})
    result = bls(a, p)
    assert len(result.observations) == 4 and "ANNUAL_AVERAGE_EXCLUDED" in result.reason_codes
    assert {o.observation_period for o in result.observations} == {"2025-11"}
    for period in ("M00", "M14", "Q01", None, 1):
        p = bls_payload(); p["Results"]["series"][0]["data"][0]["period"] = period
        r = bls(a, p)
        assert r.missing_source_ids == (ALL_IDS[0],) and "SCHEMA_MISMATCH" in r.reason_codes


def test_bls_invalid_values_duplicates_and_footnotes():
    a = api()
    for value in (None, "", "NaN", "Infinity", "1e2", "1,234", True, 123.45, float("nan")):
        p = bls_payload(); p["Results"]["series"][0]["data"][0]["value"] = value; r = bls(a, p)
        assert r.state == "INPUT_RESEARCH" and len(r.observations) == 3
        assert r.missing_source_ids == (ALL_IDS[0],) and "INVALID_VALUE" in r.reason_codes
    p = bls_payload(); row = deepcopy(p["Results"]["series"][0]["data"][0]); p["Results"]["series"][0]["data"].append(deepcopy(row))
    r = bls(a, p); assert len(r.observations) == 4
    assert any("Synthetic provisional" in note for note in r.observations[0].source_notes)
    assert r.observations[0].release.estimate_kind == "UNKNOWN"
    p["Results"]["series"][0]["data"][1]["value"] = "125"; r = bls(a, p)
    assert len(r.observations) == 3 and "CONFLICTING_DUPLICATE" in r.reason_codes
    p = bls_payload(); p["Results"]["series"][0]["data"].append(deepcopy(row)); p["Results"]["series"][0]["data"][1]["footnotes"] = []
    assert "CONFLICTING_DUPLICATE" in bls(a, p).reason_codes


def test_bea_nipa_selects_line_one_and_keeps_unit_metadata():
    a = api()
    for table, mult in (("T10106", 9), ("T10101", 0)):
        p = bea_payload(table); row = p["BEAAPI"]["Results"]["Data"][0]; other = deepcopy(row); other["LineNumber"] = "2"; other["DataValue"] = "999"
        p["BEAAPI"]["Results"]["Data"].append(other); r = bea(a, p, table)
        assert len(r.observations) == 1; o = r.observations[0]
        assert (o.source_id, o.value, o.frequency, o.observation_period, o.unit_multiplier) == (f"BEA:NIPA:{table}:1:Q", Decimal("1234.5"), "Q", "2025Q3", mult)
        assert (o.source_series_code, o.metric_name, o.unit) == ("SYNTHETIC_GDP", row["Metric_Name"], row["CL_UNIT"])
        assert any("Synthetic note" in n for n in o.source_notes) and any("Synthetic real gross" in n for n in o.source_notes)
        p["BEAAPI"]["Results"]["Data"] = [other]; unavailable(bea(a, p, table), "MISSING_SOURCE")


def test_bea_format_missing_error_and_request_echo():
    a = api()
    for value in ("1,2", "12,34.5", "NaN", "Infinity", True, 1.25, None, "(NA)", "--", "1e3"):
        r = bea(a, bea_payload(value=value)); assert r.state == "NOT_AVAILABLE" and not r.observations and SENTINEL not in repr(r)
    for value, expected in (("-1,234.50", Decimal("-1234.50")), ("0", Decimal(0))):
        assert bea(a, bea_payload(value=value)).observations[0].value == expected
    p = bea_payload(); p["BEAAPI"]["Results"]["Error"] = {"APIErrorDescription": SENTINEL}; unavailable(bea(a, p), "PROVIDER_ERROR")
    for field, value in (("TableName", "T10101"), ("TimePeriod", "2025Q5"), ("SeriesCode", ""), ("CL_UNIT", None), ("UNIT_MULT", True), ("Metric_Name", [])):
        p = bea_payload(); p["BEAAPI"]["Results"]["Data"][0][field] = value; unavailable(bea(a, p), "SCHEMA_MISMATCH")
    assert SENTINEL not in repr(bea(a))


def test_treasury_namespace_null_zero_and_schema():
    a = api()
    for value in ("0", "-0.25", "2.75"):
        r = treasury(a, treasury_body(value, prefix="anything")); assert r.observations[0].value == Decimal(value) and r.observations[0].unit == "percent"
    for body in (treasury_body(null=True), treasury_body("N/A"), treasury_body().replace(b'<d:BC_10YEAR>2.75</d:BC_10YEAR>', b'')):
        unavailable(treasury(a, body), "MISSING_SOURCE")
    for body in (treasury_body(date="2026-02-30T00:00:00"), treasury_body().replace(b'2007/08/dataservices"', b'2007/08/wrong"'), b"<feed/>"):
        unavailable(treasury(a, body), "SCHEMA_MISMATCH")
    for value in ("NaN", "Infinity", "true", "1e2"):
        unavailable(treasury(a, treasury_body(value)), "INVALID_VALUE")
    wrong_entry = treasury_body().replace(b'<entry>', b'<entry xmlns="urn:wrong">')
    unavailable(treasury(a, wrong_entry), "SCHEMA_MISMATCH")
    entry = wrong_entry.split(b'<entry', 1)[1].split(b'</entry>', 1)[0]
    mixed = treasury_body().replace(b'</feed>', b'<entry' + entry + b'</entry></feed>')
    unavailable(treasury(a, mixed), "SCHEMA_MISMATCH")
    extension = treasury_body().replace(b'</feed>', b'<extra xmlns="urn:extension">ignored</extra></feed>')
    assert treasury(a, extension).observations[0].value == Decimal("2.75")


def test_xml_dtd_and_external_entities_are_rejected(monkeypatch):
    a = api(); bodies = [b'<!DOCTYPE feed [<!ENTITY x SYSTEM "file:///SYNTHETIC_PRIVATE_SENTINEL">]>' + treasury_body(), b'<!ENTITY x "SYNTHETIC_PRIVATE_SENTINEL">' + treasury_body()]
    bodies.append(('<?xml version="1.0" encoding="UTF-16"?>' + bodies[0].decode()).encode("utf-16"))
    def forbidden(*args, **kwargs):
        pytest.fail("unsafe XML performed IO")
    monkeypatch.setattr(builtins, "open", forbidden); monkeypatch.setattr(socket, "socket", forbidden)
    for body in bodies:
        r = treasury(a, body); unavailable(r, "UNSAFE_XML"); assert SENTINEL not in repr(r)


def test_capture_time_is_not_observation_or_release_time():
    a = api()
    for r in all_results(a):
        for o in r.observations:
            assert o.available_at == o.vintage_at == o.ingested_at == NOW
            assert o.release.release_at is None and o.release.estimate_kind == "UNKNOWN"
            assert o.availability_basis == "OBSERVED_CAPTURE_UPPER_BOUND" and o.vintage_kind == "OBSERVED_CAPTURE"
            assert o.quality_flags and type(o.value) is Decimal and str(o.value) not in repr(o)
            with pytest.raises(FrozenInstanceError):
                o.value = Decimal(0)
    first = bls(a).observations[0]
    assert len(first.observation_id) == 64 and first.observation_id == bls(a).observations[0].observation_id
    assert first.observation_id != bls(a, acquired_at=NOW + timedelta(seconds=1)).observations[0].observation_id


def test_release_metadata_requires_evidence_and_time_order():
    a = api(); body = encoded(bls_payload())
    good = a.ReleaseMetadata(release_at=NOW - timedelta(days=1), release_evidence_ref="synthetic:release-1", evidence_kind="PUBLISHED_ARTIFACT", estimate_kind="INITIAL", revision_parent=None)
    r = a.parse_bls(body, receipt(a, "BLS", body), expected_series_ids=BLS_IDS, release=good)
    assert r.observations[0].release == good and r.observations[0].available_at == NOW
    for changes, reason in [({"release_evidence_ref": None}, "RELEASE_EVIDENCE_UNCONFIRMED"), ({"evidence_kind": "SCHEDULE"}, "RELEASE_EVIDENCE_UNCONFIRMED"), ({"release_at": NOW.replace(tzinfo=None)}, "INVALID_TIMESTAMP"), ({"release_at": NOW + timedelta(seconds=1)}, "INVALID_TIME_ORDER")]:
        unavailable(a.parse_bls(body, receipt(a, "BLS", body), expected_series_ids=BLS_IDS, release=replace(good, **changes)), reason)
    unavailable(a.parse_bls(body, receipt(a, "BLS", body), expected_series_ids=BLS_IDS, release={}), "RELEASE_EVIDENCE_UNCONFIRMED")


def test_cutoff_does_not_use_future_or_revised_capture():
    a = api(); old = bls(a, ids=BLS_IDS[:1]).observations
    new = bls(a, bls_payload(BLS_IDS[:1], "150"), ids=BLS_IDS[:1], acquired_at=NOW + timedelta(days=2)).observations
    assert a.select_observed_vintages(new + old, NOW + timedelta(days=1)).observations == old
    assert a.select_observed_vintages(old + new, NOW + timedelta(days=2)).observations == new
    unavailable(a.select_observed_vintages(old, NOW - timedelta(seconds=1)), "AVAILABLE_AFTER_AS_OF")
    conflict = bls(a, bls_payload(BLS_IDS[:1], "150"), ids=BLS_IDS[:1]).observations
    unavailable(a.select_observed_vintages(old + conflict, NOW), "CONFLICTING_VINTAGE")
    unavailable(a.select_observed_vintages(old, NOW.replace(tzinfo=None)), "INVALID_TIMESTAMP")
    for changes, reason in [({"value": True}, "INVALID_VALUE"), ({"value": Decimal("NaN")}, "INVALID_VALUE"), ({"available_at": NOW + timedelta(seconds=1)}, "INVALID_TIME_ORDER"), ({"axis": "Credit"}, "SCHEMA_MISMATCH"), ({"observation_period": "bad"}, "SCHEMA_MISMATCH"), ({"synthetic": 1}, "INVALID_RECEIPT")]:
        unavailable(a.select_observed_vintages((replace(old[0], **changes),), NOW), reason)
    unavailable(a.select_observed_vintages((None,), NOW), "INVALID_RECEIPT")
    for value in (Decimal("sNaN"), Decimal("NaN"), True, 1.0):
        corrupt = replace(old[0], value=value)
        r = a.select_observed_vintages((old[0], corrupt), NOW)
        assert r.state == "NOT_AVAILABLE" and not r.observations
    corrupt = replace(old[0], synthetic=Decimal("sNaN"))
    assert a.select_observed_vintages((old[0], corrupt), NOW).state == "NOT_AVAILABLE"


def test_strict_historical_is_blocked_without_release_vintage_proof():
    a = api()
    for observations in ((), bls(a).observations, bea(a).observations):
        unavailable(a.select_observed_vintages(observations, NOW, strict_historical=True), "HISTORICAL_VINTAGE_NOT_PROVEN")


def test_grid_has_exact_48_keys_and_four_deferred_axes():
    a = api(); grid = a.build_evidence_grid(all_results(a), NOW)
    assert [(c.axis, c.dimension) for c in grid.cells] == [(axis, dim) for axis in AXES for dim in DIMS]
    assert grid.contract == "MACRO_PRIMARY_INPUT/1" and len(grid.observations) == 7 and grid.missing_source_ids == ()
    assert sum(c.state == "RAW_EVIDENCE" for c in grid.cells) == 4
    for c in grid.cells:
        if c.axis in ("Liquidity", "Credit", "Fiscal", "FX"):
            assert c.state == "NOT_AVAILABLE" and c.reason_codes == ("DEFERRED_GSQ011",)
    first = bls(a); collision = replace(first.observations[1], observation_id=first.observations[0].observation_id)
    unavailable(a.build_evidence_grid((replace(first, observations=(first.observations[0], collision)),), NOW), "OBSERVATION_ID_COLLISION")
    unavailable(a.build_evidence_grid((first, bea(a, synthetic=False)), NOW), "MIXED_SYNTHETIC_INPUT")
    unavailable(a.build_evidence_grid((None,), NOW), "INVALID_RECEIPT")
    contradictory = replace(first, missing_source_ids=ALL_IDS[:2], reason_codes=("RIGHTS_UNCONFIRMED",))
    grid = a.build_evidence_grid((contradictory,), NOW)
    unavailable(grid, "INVALID_RECEIPT")
    assert all(c.state == "NOT_AVAILABLE" for c in grid.cells)


def test_grid_missing_input_remains_missing_and_never_scores(monkeypatch):
    a = api()
    from investment_system.macro.engine import MacroEngine
    def forbidden(*args, **kwargs):
        pytest.fail("evidence grid invoked the macro engine")
    monkeypatch.setattr(MacroEngine, "evaluate", forbidden)
    grid = a.build_evidence_grid((bls(a, ids=BLS_IDS[:1]), bea(a, table="T10101")), NOW)
    assert set(grid.missing_source_ids) == set(ALL_IDS) - {ALL_IDS[0], ALL_IDS[5]}
    for c in grid.cells:
        assert c.state == "NOT_AVAILABLE" and c.value is None and c.evidence_ids == ()
        if c.axis in ("Growth", "Inflation", "Labor", "Monetary Policy"):
            expected = {"Level": "MISSING_SOURCE", "Surprise": "EXPECTATIONS_NOT_CONFIGURED", "Confidence": "NO_APPROVED_CONFIDENCE_RULE"}.get(c.dimension, "NO_APPROVED_STATE_RULE")
            assert expected in c.reason_codes
    grid = a.build_evidence_grid((treasury(a, acquired_at=NOW + timedelta(days=1)),), NOW)
    unavailable(grid, "AVAILABLE_AFTER_AS_OF")
    assert "AVAILABLE_AFTER_AS_OF" in next(c for c in grid.cells if (c.axis, c.dimension) == ("Monetary Policy", "Level")).reason_codes


def test_partial_input_research_does_not_claim_model_or_pit_ready():
    a = api(); grid = a.build_evidence_grid((bls(a, ids=BLS_IDS[:1]),), NOW)
    assert (grid.state, grid.model_status, grid.pit_status) == ("INPUT_RESEARCH", "NOT_APPLIED", "OBSERVED_BOUND_ONLY")
    assert all(word not in vars(grid) for word in ("live", "official", "calibrated", "score", "weights"))
    empty = a.build_evidence_grid((), NOW)
    assert (empty.state, empty.pit_status) == ("NOT_AVAILABLE", "NOT_VERIFIED")
    assert len(empty.cells) == 48 and set(empty.missing_source_ids) == set(ALL_IDS)


def test_parsers_and_grid_have_no_io_mutation_or_diagnostic_leaks(monkeypatch, capsys):
    a = api(); payload = bls_payload(); before = deepcopy(payload)
    bodies = (encoded(payload), encoded(bea_payload()), treasury_body())
    receipts = tuple(receipt(a, p, b) for p, b in zip(("BLS", "BEA", "TREASURY"), bodies))
    def forbidden(*args, **kwargs):
        pytest.fail("pure input boundary performed IO")
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden); m.setattr(socket, "socket", forbidden); m.setattr(logging.Logger, "_log", forbidden)
        results = (a.parse_bls(bodies[0], receipts[0], expected_series_ids=BLS_IDS), a.parse_bea_nipa(bodies[1], receipts[1], expected_table="T10106"), a.parse_treasury_yields(bodies[2], receipts[2]))
        grid = a.build_evidence_grid(results, NOW)
    assert payload == before and grid.state == "INPUT_RESEARCH" and SENTINEL not in repr(results) + repr(grid)
    assert capsys.readouterr() == ("", "")
