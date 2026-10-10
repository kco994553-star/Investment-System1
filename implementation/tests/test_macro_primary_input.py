"""Synthetic primary-agency contracts; no captured provider data."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import builtins
import logging
import socket

import pytest

from investment_system.macro.primary_contract import (
    AXES, DIMENSIONS, BLS_SERIES, SourceReceipt, ReleaseMetadata,
)
from investment_system.providers.macro_primary import (
    build_bls_plan, build_bea_plan, build_treasury_plan,
    parse_bls, parse_bea_nipa, parse_treasury_yields,
)
from investment_system.macro.primary_input import select_observed_vintages, build_evidence_grid

AT = datetime(2030, 1, 5, 12, tzinfo=timezone.utc)
URLS = {"BLS": "https://api.bls.gov/publicAPI/v1/timeseries/data/",
        "BEA": "https://apps.bea.gov/api/data",
        "TREASURY": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"}


def receipt(body, provider="BLS", at=AT):
    return SourceReceipt(provider, URLS[provider], hashlib.sha256(body).hexdigest(), at, True, "CLEARED_SCOPE")


def bls_payload(ids=tuple(BLS_SERIES), value="123.4", rows=None):
    data = rows if rows is not None else [{"year": "2029", "period": "M12", "value": value,
                                           "footnotes": [{"code": "P", "text": "synthetic provisional"}]}]
    return json.dumps({"status": "REQUEST_SUCCEEDED", "Results": {"series": [
        {"seriesID": sid, "data": data} for sid in ids]}}).encode()


def bls(body=None, **kwargs):
    body = bls_payload() if body is None else body
    return parse_bls(body, receipt(body), expected_series_ids=tuple(BLS_SERIES), **kwargs)


def bea_payload(table="T10106", **changes):
    row = {"TableName": table, "LineNumber": "1", "TimePeriod": "2029Q4",
           "SeriesCode": "SYNTHETIC-GDP", "LineDescription": "Real gross domestic product",
           "Metric_Name": "Chained Dollars", "CL_UNIT": "Billions of Chained Dollars",
           "UNIT_MULT": "9", "DataValue": "1,234.5"}
    row.update(changes)
    return json.dumps({"BEAAPI": {"Request": {"UserID": "private-echo-sentinel"},
                    "Results": {"Data": [row], "Notes": [{"NoteText": "synthetic base year"}]}}}).encode()


def bea(body=None, table="T10106"):
    body = bea_payload(table) if body is None else body
    return parse_bea_nipa(body, receipt(body, "BEA"), expected_table=table)


def treasury_payload(value="1.25", attr="", namespace="http://schemas.microsoft.com/ado/2007/08/dataservices"):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:x="{namespace}" '
            'xmlns:z="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">'
            '<entry><content><z:properties><x:NEW_DATE>2029-12-31T00:00:00</x:NEW_DATE>'
            f'<x:BC_10YEAR {attr}>{value}</x:BC_10YEAR></z:properties></content></entry></feed>').encode()


def treasury(body=None):
    body = treasury_payload() if body is None else body
    return parse_treasury_yields(body, receipt(body, "TREASURY"))


def test_fixed_request_plans_have_exact_official_hosts_and_parameters():
    b = build_bls_plan(tuple(BLS_SERIES), 2028, 2029)
    assert b.endpoint == URLS["BLS"] and b.method == "POST"
    assert json.loads(b.body) == {"seriesid": list(BLS_SERIES), "startyear": "2028", "endyear": "2029"}
    e = build_bea_plan("T10106", (2028, 2029))
    assert dict(e.public_parameters) == {"method": "GetData", "DataSetName": "NIPA", "TableName": "T10106", "Frequency": "Q", "Year": "2028,2029", "ResultFormat": "JSON"}
    t = build_treasury_plan(2029)
    assert t.endpoint == URLS["TREASURY"] and dict(t.public_parameters) == {"data": "daily_treasury_yield_curve", "field_tdr_date_value": "2029"}
    assert build_bea_plan("ALL", (2029,)).state == "NOT_AVAILABLE"


def test_bls_plan_enforces_v1_allowlist_and_span():
    assert build_bls_plan(tuple(BLS_SERIES), 2020, 2029).state == "PLANNED"
    for ids, start, end in [((), 2029, 2029), (("DGS10",), 2029, 2029), (("CUSR0000SA0",)*2, 2029, 2029), (tuple(BLS_SERIES), 2019, 2029), (tuple(BLS_SERIES), True, 2029), (tuple(BLS_SERIES), 2030, 2029)]:
        p = build_bls_plan(ids, start, end)
        assert p.state == "NOT_AVAILABLE" and p.body is None and p.reason_codes == ("INVALID_REQUEST",)


def test_bea_plan_has_credential_slot_without_secret_or_network():
    p = build_bea_plan("T10101", (2029,))
    assert p.credential_slot == "BEA_USERID" and p.body is None
    assert "UserID" not in dict(p.public_parameters)
    for years in [(2029, 2029), (2030, 2029), (), ("ALL",), (True,)]:
        assert build_bea_plan("T10106", years).reason_codes == ("INVALID_REQUEST",)
    assert build_treasury_plan(True).state == "NOT_AVAILABLE"


def test_receipt_hash_provider_rights_and_time_are_required():
    body = bls_payload()
    r = receipt(body)
    for changed, reason in [(replace(r, response_sha256="0"*64), "INVALID_RECEIPT"), (replace(r, provider="BEA"), "INVALID_RECEIPT"), (replace(r, source_url=URLS["BLS"]+"?key=sentinel"), "INVALID_RECEIPT"), (replace(r, acquired_at=AT.replace(tzinfo=None)), "INVALID_TIMESTAMP"), (replace(r, rights_status="UNCONFIRMED"), "RIGHTS_UNCONFIRMED")]:
        p = parse_bls(body, changed, expected_series_ids=tuple(BLS_SERIES))
        assert p.observations == () and p.reason_codes == (reason,)


def test_cpi_seasonal_and_nonseasonal_are_not_interchangeable():
    obs = {o.source_id: o for o in bls().observations}
    assert obs["BLS:CUSR0000SA0"].seasonal_adjustment == "SA"
    assert obs["BLS:CUUR0000SA0"].seasonal_adjustment == "NSA"
    assert obs["BLS:CUSR0000SA0"].unit == "index 1982-84=100"
    p = bls(bls_payload(("CUSR0000SA0",)))
    assert "BLS:CUUR0000SA0" in p.missing_source_ids


def test_labor_payroll_and_unemployment_keep_distinct_units():
    obs = {o.source_id: o for o in bls().observations}
    assert obs["BLS:CES0000000001"].unit == "thousands"
    assert obs["BLS:LNS14000000"].unit == "percent"


def test_bls_status_missing_series_and_annual_average():
    bad = json.dumps({"status": "REQUEST_FAILED"}).encode()
    assert bls(bad).reason_codes == ("PROVIDER_ERROR",)
    p = bls(bls_payload(rows=[{"year": "2029", "period": "M13", "value": "100"}]))
    assert not p.observations and "ANNUAL_AVERAGE_EXCLUDED" in p.reason_codes
    assert set(p.missing_source_ids) == {"BLS:"+s for s in BLS_SERIES}


def test_bls_invalid_values_duplicates_and_footnotes():
    for value in [None, "", "NaN", "Infinity", True, "1,2"]:
        assert bls(bls_payload(value=value)).state == "NOT_AVAILABLE"
    row = {"year": "2029", "period": "M12", "value": "100"}
    assert len(bls(bls_payload(rows=[row, row])).observations) == 4
    p = bls(bls_payload(rows=[row, {**row, "value": "101"}]))
    assert p.reason_codes == ("CONFLICTING_DUPLICATE",) and not p.observations
    assert bls().observations[0].source_notes == ("P:synthetic provisional",)


def test_bea_nipa_selects_line_one_and_keeps_unit_metadata():
    o = bea().observations[0]
    assert o.source_id == "BEA:NIPA:T10106:1:Q" and o.value == Decimal("1234.5")
    assert (o.unit, o.unit_multiplier, o.metric_name, o.source_series_code) == ("Billions of Chained Dollars", 9, "Chained Dollars", "SYNTHETIC-GDP")
    assert "synthetic base year" in o.source_notes and "Real gross domestic product" in o.source_notes
    assert bea(bea_payload(LineNumber="2")).state == "NOT_AVAILABLE"
    assert bea(table="T10101").observations[0].source_id == "BEA:NIPA:T10101:1:Q"


def test_bea_format_missing_error_and_request_echo():
    for changes in [{"DataValue": "1,2"}, {"DataValue": "--"}, {"TimePeriod": "2029Q5"}, {"TableName": "T10101"}, {"Metric_Name": ""}, {"UNIT_MULT": True}]:
        assert bea(bea_payload(**changes)).state == "NOT_AVAILABLE"
    assert bea(json.dumps({"BEAAPI": {"Results": {"Error": {"APIErrorDescription": "private-echo-sentinel"}}}}).encode()).reason_codes == ("PROVIDER_ERROR",)
    assert "private-echo-sentinel" not in repr(bea())


def test_treasury_namespace_null_zero_and_schema():
    for value in ["0", "-0.25"]:
        assert treasury(treasury_payload(value)).observations[0].value == Decimal(value)
    for body in [treasury_payload("", 'z:null="true"'), treasury_payload("N/A"), treasury_payload(namespace="wrong")]:
        assert treasury(body).state == "NOT_AVAILABLE"
    assert treasury().observations[0].unit == "percent"


def test_xml_dtd_and_external_entities_are_rejected():
    for prefix in [b'<!DOCTYPE feed SYSTEM "file:///private-sentinel">', b'<!ENTITY x SYSTEM "https://private-sentinel">']:
        p = treasury(prefix+treasury_payload())
        assert p.reason_codes == ("UNSAFE_XML",) and "private-sentinel" not in repr(p)


def test_capture_time_is_not_observation_or_release_time():
    for p in [bls(), bea(), treasury()]:
        for o in p.observations:
            assert o.available_at == o.vintage_at == o.ingested_at == AT
            assert o.release.release_at is None and o.release.estimate_kind == "UNKNOWN"
            assert o.availability_basis == "OBSERVED_CAPTURE_UPPER_BOUND"


def test_release_metadata_requires_evidence_and_time_order():
    valid = ReleaseMetadata(AT-timedelta(days=1), "synthetic-artifact", "PUBLISHED_ARTIFACT", "REVISED", None)
    assert bls(release=valid).observations[0].available_at == AT
    for r, reason in [(replace(valid, evidence_kind="SCHEDULE"), "RELEASE_EVIDENCE_UNCONFIRMED"), (replace(valid, release_evidence_ref=None), "RELEASE_EVIDENCE_UNCONFIRMED"), (replace(valid, release_at=AT.replace(tzinfo=None)), "INVALID_TIMESTAMP"), (replace(valid, release_at=AT+timedelta(days=1)), "INVALID_TIME_ORDER")]:
        assert bls(release=r).reason_codes == (reason,)


def test_cutoff_does_not_use_future_or_revised_capture():
    b1, b2 = bls_payload(value="100"), bls_payload(value="101")
    p1 = parse_bls(b1, receipt(b1), expected_series_ids=tuple(BLS_SERIES))
    p2 = parse_bls(b2, receipt(b2, at=AT+timedelta(days=1)), expected_series_ids=tuple(BLS_SERIES))
    assert {o.value for o in select_observed_vintages(p1.observations+p2.observations, AT).observations} == {Decimal("100")}
    assert {o.value for o in select_observed_vintages(p1.observations+p2.observations, AT+timedelta(days=1)).observations} == {Decimal("101")}
    assert not select_observed_vintages(p1.observations, AT-timedelta(seconds=1)).observations
    same_capture = parse_bls(b2, receipt(b2), expected_series_ids=tuple(BLS_SERIES))
    assert "CONFLICTING_VINTAGE" in select_observed_vintages(p1.observations+same_capture.observations, AT).reason_codes


def test_strict_historical_is_blocked_without_release_vintage_proof():
    p = select_observed_vintages(bls().observations, AT, strict_historical=True)
    assert p.state == "NOT_AVAILABLE" and p.reason_codes == ("HISTORICAL_VINTAGE_NOT_PROVEN",)


def test_grid_has_exact_48_keys_and_four_deferred_axes():
    g = build_evidence_grid((bls(), bea(), treasury()), AT)
    assert len(g.cells) == 48 and {(c.axis, c.dimension) for c in g.cells} == {(a,d) for a in AXES for d in DIMENSIONS}
    assert sum(c.state == "RAW_EVIDENCE" for c in g.cells) == 4
    assert sum(c.reason_codes == ("DEFERRED_GSQ011",) for c in g.cells) == 24
    p = bls()
    assert len(build_evidence_grid((p,p), AT).observations) == 4
    collision = replace(p, observations=(replace(p.observations[0], source_id="BLS:LNS14000000"),))
    assert build_evidence_grid((p,collision), AT).reason_codes == ("OBSERVATION_ID_COLLISION",)


def test_grid_missing_input_remains_missing_and_never_scores():
    p = bls(bls_payload(("CUSR0000SA0",)))
    g = build_evidence_grid((p,), AT)
    assert all(c.value is None for c in g.cells)
    assert all(c.state == "NOT_AVAILABLE" for c in g.cells if c.dimension == "Level")
    assert next(c for c in g.cells if c.axis == "Growth" and c.dimension == "Surprise").reason_codes == ("EXPECTATIONS_NOT_CONFIGURED",)
    future = build_evidence_grid((bls(),), AT-timedelta(seconds=1))
    assert future.state == "NOT_AVAILABLE" and "AVAILABLE_AFTER_AS_OF" in future.reason_codes


def test_partial_input_research_does_not_claim_model_or_pit_ready():
    g = build_evidence_grid((bls(bls_payload(("CUSR0000SA0",))),), AT)
    assert (g.state,g.model_status,g.pit_status) == ("INPUT_RESEARCH","NOT_APPLIED","OBSERVED_BOUND_ONLY")
    p = bls()
    mixed = replace(p, synthetic=False, observations=tuple(replace(o, synthetic=False) for o in p.observations))
    assert build_evidence_grid((p,mixed), AT).reason_codes == ("MIXED_SYNTHETIC_INPUT",)


def test_parsers_and_grid_have_no_io_mutation_or_diagnostic_leaks(monkeypatch, capsys):
    body = bls_payload(); before = deepcopy(body); r = receipt(body)
    def forbidden(*args, **kwargs):
        pytest.fail("I/O at pure boundary")
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden); m.setattr(socket, "create_connection", forbidden)
        m.setattr(socket.socket, "connect", forbidden); m.setattr(logging.Logger, "_log", forbidden)
        p = parse_bls(body,r,expected_series_ids=tuple(BLS_SERIES))
        g = build_evidence_grid((p,), AT)
    assert g.state == "INPUT_RESEARCH" and before == body
    assert capsys.readouterr() == ("", "")
