"""Supplied synthetic 13F XML only: reported quantities never imply trades."""
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone
import hashlib
from importlib import import_module
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import pytest


NS = "http://www.sec.gov/edgar/document/thirteenf/informationtable"
MANAGER = "0000000123"
AS_OF = datetime(2026, 10, 10, tzinfo=timezone.utc)


def _api():
    return import_module("investment_system.providers.sec_13f")


def _metadata(**updates):
    values = dict(manager_cik=MANAGER, accession="0000000123-26-000001",
                  quarter_end=date(2026, 6, 30), filing_date=date(2026, 8, 1),
                  acquired_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
                  value_basis="USD_DOLLARS", report_type="HOLDINGS",
                  confidential_omitted=False, entry_total=1, complete=True,
                  lineage_resolved=True, cover_binding_confirmed=True)
    values.update(updates)
    return _api().FilingMetadata(**values)


def _row(*, cusip="123456789", title="COM", quantity="100", value="2000",
         quantity_type="SH", put_call=None, discretion="SOLE", other=None,
         figi=None, issuer="Synthetic Issuer", sole="100", shared="0", none="0"):
    fields = [f"<nameOfIssuer>{escape(issuer)}</nameOfIssuer>",
              f"<titleOfClass>{escape(title)}</titleOfClass>", f"<cusip>{cusip}</cusip>"]
    if figi is not None:
        fields.append(f"<figi>{figi}</figi>")
    fields.extend([f"<value>{value}</value>",
                   f"<shrsOrPrnAmt><sshPrnamt>{quantity}</sshPrnamt>"
                   f"<sshPrnamtType>{quantity_type}</sshPrnamtType></shrsOrPrnAmt>"])
    if put_call is not None:
        fields.append(f"<putCall>{put_call}</putCall>")
    fields.append(f"<investmentDiscretion>{discretion}</investmentDiscretion>")
    if other is not None:
        fields.append(f"<otherManager>{other}</otherManager>")
    fields.append(f"<votingAuthority><Sole>{sole}</Sole><Shared>{shared}</Shared>"
                  f"<None>{none}</None></votingAuthority>")
    return "<infoTable>" + "".join(fields) + "</infoTable>"


def _xml(*rows, namespace=NS):
    return (f'<informationTable xmlns="{namespace}">' + "".join(rows)
            + "</informationTable>").encode()


def _parse(*rows, metadata=None, selected=(MANAGER,), as_of=AS_OF):
    return _api().parse_information_table(
        _xml(*rows), metadata or _metadata(entry_total=len(rows)),
        selected_manager_ciks=selected, as_of=as_of)


def _pair(previous_rows, current_rows, previous_updates=None, current_updates=None):
    old = dict(quarter_end=date(2026, 3, 31), filing_date=date(2026, 5, 1),
               acquired_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
               accession="0000000123-26-000002", entry_total=len(previous_rows))
    old.update(previous_updates or {})
    new = dict(entry_total=len(current_rows))
    new.update(current_updates or {})
    return (_parse(*previous_rows, metadata=_metadata(**old)),
            _parse(*current_rows, metadata=_metadata(**new)))


def _compare(previous_rows, current_rows, **kwargs):
    return _api().compare_quarters(*_pair(previous_rows, current_rows, **kwargs))


def test_parse_preserves_schema_integers_raw_rows_and_provenance():
    payload = _xml(_row(quantity="00100", value="0002000", figi="BBG000000001"))
    result = _api().parse_information_table(payload, _metadata(),
                                           selected_manager_ciks=(MANAGER,), as_of=AS_OF)
    assert result.status == "AVAILABLE" and result.comparison_eligible
    assert result.role == "REPORTED_QUANTITY_ONLY"
    assert result.payload_sha256 == hashlib.sha256(payload).hexdigest()
    row = result.raw_rows[0]
    assert (row.quantity, row.value, row.value_basis) == (100, 2000, "USD_DOLLARS")
    assert row.raw_fields["sshPrnamt"] == "00100"
    assert row.raw_fields["value"] == "0002000"
    assert row.figi == "BBG000000001"
    assert result.holdings[0].raw_rows == result.raw_rows


def test_default_selection_is_not_available_without_default_investors():
    result = _api().parse_information_table(_xml(_row()), _metadata(), as_of=AS_OF)
    assert result.status == "NOT_AVAILABLE"
    assert result.reasons == ("MANAGER_NOT_SELECTED",) and not result.raw_rows


def test_selection_identifies_manager_and_normalizes_cik_not_issuer():
    assert _parse(_row(), selected=("123",)).status == "AVAILABLE"
    excluded = _parse(_row(), selected=("456",))
    assert excluded.status == "NOT_AVAILABLE" and not excluded.holdings
    for bad in ("123", (True,), ("１２３",), ("0",)):
        assert _parse(_row(), selected=bad).status == "NOT_AVAILABLE"


def test_invalid_cover_identity_and_quarter_metadata_fail_closed():
    for updates in (dict(manager_cik="bad"), dict(accession="bad"),
                    dict(quarter_end=date(2026, 6, 29)),
                    dict(quarter_end=datetime(2026, 6, 30)),
                    dict(filing_date=date(2026, 6, 29)), dict(report_type="OTHER"),
                    dict(amendment_type="UNKNOWN"), dict(complete=1)):
        result = _parse(_row(), metadata=_metadata(**updates))
        assert result.status == "NOT_AVAILABLE" and not result.holdings


def test_capture_and_as_of_require_aware_timestamps_and_available_filing():
    cases = [(_metadata(acquired_at=datetime(2026, 8, 2)), AS_OF),
             (_metadata(), datetime(2026, 10, 10)),
             (_metadata(acquired_at=AS_OF + timedelta(seconds=1)), AS_OF),
             (_metadata(acquired_at=datetime(2026, 7, 31, tzinfo=timezone.utc)), AS_OF),
             (_metadata(), datetime(2026, 7, 31, tzinfo=timezone.utc))]
    for metadata, cutoff in cases:
        result = _parse(_row(), metadata=metadata, as_of=cutoff)
        assert result.status == "NOT_AVAILABLE" and not result.raw_rows


def test_source_digest_is_checked_against_the_supplied_payload():
    payload = _xml(_row())
    digest = hashlib.sha256(payload).hexdigest()
    assert _parse(_row(), metadata=_metadata(source_response_sha256=digest)).status == "AVAILABLE"
    for bad in ("0" * 64, "invalid", 42):
        result = _parse(_row(), metadata=_metadata(source_response_sha256=bad))
        assert result.status == "NOT_AVAILABLE" and not result.holdings


def test_value_basis_is_explicit_and_never_inferred_from_quarter():
    for basis in ("USD_DOLLARS", "USD_THOUSANDS"):
        result = _parse(_row(value="123"), metadata=_metadata(value_basis=basis))
        assert result.raw_rows[0].value == 123 and result.holdings[0].value_basis == basis
    for missing in (None, "USD", "AUTOMATIC"):
        assert _parse(_row(), metadata=_metadata(value_basis=missing)).status == "NOT_AVAILABLE"
    assert _api().FilingMetadata().value_basis is None


def test_schema_requires_exact_namespace_root_and_children():
    payloads = [_xml(_row(), namespace=""), _xml(_row(), namespace="urn:other"),
                _xml(_row()).replace(b"informationTable", b"wrongRoot"),
                _xml(_row()).replace(b"<cusip>", b'<cusip xmlns="urn:other">')]
    for payload in payloads:
        result = _api().parse_information_table(payload, _metadata(),
                                               selected_manager_ciks=(MANAGER,), as_of=AS_OF)
        assert result.status == "NOT_AVAILABLE" and not result.raw_rows
    hint = _xml(_row()).replace(
        b"<informationTable ",
        b'<informationTable xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        b'xsi:schemaLocation="http://www.sec.gov/edgar/document/thirteenf/informationtable '
        b'https://example.invalid/never-fetch.xsd" ')
    result = _api().parse_information_table(hint, _metadata(),
                                           selected_manager_ciks=(MANAGER,), as_of=AS_OF)
    assert result.status == "AVAILABLE"


def test_duplicate_fields_unknown_fields_and_nested_scalar_fail_whole_capture():
    variants = [_row().replace("<value>2000</value>", "<value>2000</value><value>2000</value>"),
                _row().replace("</infoTable>", "<unknown>1</unknown></infoTable>"),
                _row().replace("<cusip>123456789</cusip>", "<cusip><x>123456789</x></cusip>"),
                _row().replace("<None>0</None>", "<None>0</None><None>0</None>"),
                _row().replace("<Sole>100</Sole><Shared>0</Shared>",
                               "<Shared>0</Shared><Sole>100</Sole>")]
    for row in variants:
        result = _parse(_row(cusip="987654321"), row)
        assert result.status == "NOT_AVAILABLE" and not result.raw_rows and not result.holdings


def test_missing_required_fields_and_empty_issuer_class_fail_whole_capture():
    for row in (_row().replace("<investmentDiscretion>SOLE</investmentDiscretion>", ""),
                _row().replace("<None>0</None>", ""), _row(issuer=""), _row(title=""),
                _row(issuer="x" * 151), _row(title="x" * 151), _row(issuer="日本語")):
        assert _parse(row).status == "NOT_AVAILABLE"


def test_numeric_fields_require_ascii_unsigned_integer_up_to_sixteen_digits():
    for value in ("-1", "+1", "1.5", "1e3", "NaN", "١٢", "10000000000000000", "", "\u00a01\u00a0"):
        for field in ("quantity", "value", "sole", "shared", "none"):
            result = _parse(_row(**{field: value}))
            assert result.status == "NOT_AVAILABLE" and not result.holdings
    result = _parse(_row(quantity="9999999999999999", value="0", sole="0"))
    assert result.raw_rows[0].quantity == 9999999999999999


def test_cusip_figi_and_enumerations_follow_schema_without_ticker_aliases():
    for kwargs in (dict(cusip="123"), dict(cusip="１２３４５６７８９"),
                   dict(cusip="12345*789"), dict(figi="BBG1"),
                   dict(figi="ＢＢＧ000000001"), dict(quantity_type="shares"),
                   dict(put_call="PUT"), dict(discretion="SHARED")):
        assert _parse(_row(**kwargs)).status == "NOT_AVAILABLE"
    for kwargs in (dict(quantity_type="PRN"), dict(put_call="Put"),
                   dict(put_call="Call"), dict(discretion="DFND"), dict(discretion="OTR")):
        assert _parse(_row(**kwargs)).raw_rows


def test_xml_dtd_entity_nul_and_malformed_content_are_rejected():
    normal = _xml(_row())
    dtd = b'<!DOCTYPE informationTable [<!ENTITY x "Synthetic">]>' + normal
    payloads = [dtd, dtd.decode().encode("utf-16"),
                normal.replace(b"Synthetic Issuer", b"&x;"), b"<broken", normal + b"\x00"]
    for payload in payloads:
        result = _api().parse_information_table(payload, _metadata(),
                                               selected_manager_ciks=(MANAGER,), as_of=AS_OF)
        assert result.status == "NOT_AVAILABLE" and not result.raw_rows


def test_payload_size_and_bytes_type_are_bounded():
    for payload in ("not bytes", None, b"x" * (_api().MAX_PAYLOAD_BYTES + 1)):
        result = _api().parse_information_table(payload, _metadata(),
                                               selected_manager_ciks=(MANAGER,), as_of=AS_OF)
        assert result.status == "NOT_AVAILABLE" and not result.holdings


def test_invalid_row_never_leaves_valid_rows_for_false_exit_comparison():
    previous = _parse(_row())
    current = _parse(_row(cusip="987654321"), _row(quantity="bad"))
    assert current.status == "NOT_AVAILABLE" and current.raw_rows == ()
    compared = _api().compare_quarters(previous, current)
    assert compared.status == "NOT_AVAILABLE" and compared.changes == ()


def test_partial_valid_capture_preserves_rows_but_cannot_compare():
    previous, current = _pair([_row()], [_row(cusip="987654321")],
                              current_updates=dict(complete=False))
    assert current.status == "PARTIAL" and current.raw_rows and current.holdings
    result = _api().compare_quarters(previous, current)
    assert result.status == "NOT_AVAILABLE" and result.changes == ()


def test_cover_binding_and_lineage_defaults_preserve_parse_but_gate_comparison():
    for flag in ("cover_binding_confirmed", "lineage_resolved"):
        result = _parse(_row(), metadata=_metadata(**{flag: False}))
        assert result.status == "PARTIAL" and not result.comparison_eligible and result.raw_rows
    defaults = _api().FilingMetadata()
    assert not defaults.complete and not defaults.lineage_resolved and not defaults.cover_binding_confirmed


def test_report_type_and_confidential_unknown_or_omitted_gate_comparison():
    for updates in (dict(report_type="NOTICE"), dict(report_type="COMBINATION"),
                    dict(confidential_omitted=None), dict(confidential_omitted=True)):
        result = _parse(_row(), metadata=_metadata(**updates))
        assert result.status == "PARTIAL" and not result.comparison_eligible
    assert _api().FilingMetadata().confidential_omitted is None


def test_entry_count_is_raw_row_count_not_aggregated_count():
    result = _parse(_row(), _row(), metadata=_metadata(entry_total=2))
    assert result.status == "AVAILABLE" and len(result.holdings) == 1
    for count in (None, 1, 3):
        partial = _parse(_row(), _row(), metadata=_metadata(entry_total=count))
        assert partial.status == "PARTIAL" and not partial.comparison_eligible
    for count in (-1, True, "2"):
        assert _parse(_row(), metadata=_metadata(entry_total=count)).status == "NOT_AVAILABLE"


def test_optional_value_total_uses_untransformed_value_basis():
    assert _parse(_row(), metadata=_metadata(value_total=2000)).status == "AVAILABLE"
    mismatch = _parse(_row(), metadata=_metadata(value_total=2000000, value_basis="USD_THOUSANDS"))
    assert mismatch.status == "PARTIAL" and mismatch.raw_rows[0].value == 2000
    assert _parse(_row(), metadata=_metadata(value_total=True)).status == "NOT_AVAILABLE"


def test_restatement_requires_complete_resolved_canonical_quarter_lineage():
    result = _parse(_row(), metadata=_metadata(amendment_type="RESTATEMENT"))
    assert result.status == "AVAILABLE"
    for flag in ("complete", "lineage_resolved"):
        partial = _parse(_row(), metadata=_metadata(amendment_type="RESTATEMENT", **{flag: False}))
        assert partial.status == "PARTIAL" and not partial.comparison_eligible


def test_new_holdings_amendment_is_additional_and_never_standalone_complete():
    result = _parse(_row(), metadata=_metadata(amendment_type="NEW_HOLDINGS"))
    assert result.status == "PARTIAL" and "ADDITIONAL_HOLDINGS_AMENDMENT" in result.reasons
    assert not result.comparison_eligible


def test_unresolved_other_manager_references_preserve_rows_but_gate_comparison():
    result = _parse(_row(other="1"), _row(other="2"))
    assert result.status == "PARTIAL" and not result.comparison_eligible
    assert result.raw_rows[0].other_manager_refs == ("1",)
    assert result.raw_rows[0].other_manager_ciks is None
    assert len(result.raw_rows) == 2 and len(result.holdings) == 2


def test_other_manager_cover_map_resolves_actual_ciks_and_copies_input():
    cover_map = {"1": "456", "2": "789"}
    metadata = _metadata(other_manager_ciks=cover_map)
    cover_map["1"] = "999"
    result = _parse(_row(other="1,2"), metadata=metadata)
    assert result.status == "AVAILABLE"
    assert result.raw_rows[0].other_manager_ciks == ("0000000456", "0000000789")
    with pytest.raises(TypeError):
        metadata.other_manager_ciks["1"] = "111"
    for other in ("0", "1000", "1," * 50 + "1"):
        assert _parse(_row(other=other), metadata=metadata).status == "NOT_AVAILABLE"
    assert _parse(_row(other="0"), metadata=_metadata(other_manager_ciks={"0": "456"})).status == "NOT_AVAILABLE"


def test_duplicates_aggregate_only_identical_full_security_basis():
    result = _parse(_row(quantity="100"), _row(quantity="200", value="3000"))
    assert len(result.holdings) == 1 and len(result.raw_rows) == 2
    holding = result.holdings[0]
    assert (holding.quantity, holding.value, len(holding.raw_rows)) == (300, 5000, 2)
    collapsed = _parse(_row(title="COMMON  SHARES"), _row(title="COMMON\tSHARES"))
    assert len(collapsed.holdings) == 1 and collapsed.holdings[0].quantity == 200


def test_same_cusip_classes_options_units_discretion_attribution_are_never_merged():
    rows = [_row(), _row(title="CLASS B"), _row(quantity_type="PRN"),
            _row(put_call="Put"), _row(put_call="Call"), _row(discretion="DFND"),
            _row(other="1"), _row(other="2")]
    result = _parse(*rows, metadata=_metadata(entry_total=len(rows),
                                             other_manager_ciks={"1": "456", "2": "789"}))
    assert result.status == "AVAILABLE" and len(result.holdings) == len(rows)


def test_referenced_aliases_for_same_actual_manager_can_aggregate():
    result = _parse(_row(other="1"), _row(other="2"),
                    metadata=_metadata(entry_total=2, other_manager_ciks={"1": "456", "2": "456"}))
    assert result.status == "AVAILABLE" and len(result.holdings) == 1
    assert result.holdings[0].quantity == 200


def test_new_and_add_changes_are_reported_quantity_only():
    result = _compare([_row()], [_row(quantity="150"), _row(cusip="987654321", quantity="70")])
    assert result.status == "AVAILABLE" and result.role == "REPORTED_QUANTITY_ONLY"
    by_kind = {change.kind: change for change in result.changes}
    assert set(by_kind) == {"ADD", "NEW"}
    assert (by_kind["ADD"].previous_quantity, by_kind["ADD"].current_quantity,
            by_kind["ADD"].delta_quantity) == (100, 150, 50)
    assert (by_kind["NEW"].previous_quantity, by_kind["NEW"].current_quantity) == (0, 70)


def test_reduce_change_reports_quantity_and_negative_delta():
    result = _compare([_row()], [_row(quantity="75")])
    assert result.status == "AVAILABLE"
    change, = result.changes
    assert (change.kind, change.previous_quantity, change.current_quantity, change.delta_quantity) == (
        "REDUCE", 100, 75, -25)


def test_absent_reported_holding_is_exit_with_mandatory_non_sale_label():
    result = _compare([_row(), _row(cusip="987654321")], [_row(cusip="987654321")])
    change, = result.changes
    assert change.kind == "EXIT" and change.current_quantity == 0
    assert change.label == "공개 보고에서 소멸/수량0, 실제 전량매도 확정 아님"


def test_explicit_zero_is_exit_but_prior_zero_to_positive_is_new():
    exited = _compare([_row()], [_row(quantity="0", sole="0")])
    assert exited.changes[0].kind == "EXIT" and exited.changes[0].delta_quantity == -100
    entered = _compare([_row(quantity="0", sole="0")], [_row()])
    assert entered.changes[0].kind == "NEW"


def test_unchanged_and_value_only_changes_do_not_emit_add_or_any_change():
    for current in (_row(), _row(value="3000")):
        result = _compare([_row()], [current])
        assert result.status == "AVAILABLE" and result.changes == ()


def test_consecutive_calendar_quarters_include_year_boundary():
    result = _compare([_row()], [_row(quantity="110")],
                      previous_updates=dict(quarter_end=date(2025, 12, 31),
                                            filing_date=date(2026, 2, 1),
                                            acquired_at=datetime(2026, 2, 2, tzinfo=timezone.utc)),
                      current_updates=dict(quarter_end=date(2026, 3, 31),
                                           filing_date=date(2026, 5, 1),
                                           acquired_at=datetime(2026, 5, 2, tzinfo=timezone.utc)))
    assert result.status == "AVAILABLE" and result.changes[0].kind == "ADD"


def test_gap_same_quarter_and_reversed_quarters_never_emit_false_changes():
    previous, current = _pair([_row()], [_row(cusip="987654321")])
    assert _api().compare_quarters(current, previous).status == "NOT_AVAILABLE"
    for quarter in (date(2026, 3, 31), date(2026, 9, 30)):
        updates = dict(quarter_end=quarter)
        if quarter.month == 9:
            updates.update(filing_date=date(2026, 10, 1),
                           acquired_at=datetime(2026, 10, 2, tzinfo=timezone.utc))
        result = _compare([_row()], [_row(cusip="987654321")], current_updates=updates)
        assert result.status == "NOT_AVAILABLE" and result.changes == ()


def test_different_verified_manager_and_different_as_of_captures_cannot_compare():
    previous, current = _pair([_row()], [_row(quantity="110")])
    other = _parse(_row(quantity="110"), selected=("456",), metadata=_metadata(manager_cik="456"))
    assert _api().compare_quarters(previous, other).status == "NOT_AVAILABLE"
    older_cutoff = _parse(_row(quantity="110"), as_of=AS_OF - timedelta(days=1))
    assert _api().compare_quarters(previous, older_cutoff).status == "NOT_AVAILABLE"
    assert _api().compare_quarters(None, current).status == "NOT_AVAILABLE"
    fold_zone = ZoneInfo("America/New_York")
    first = datetime(2026, 11, 1, 1, 30, tzinfo=fold_zone, fold=0)
    second = datetime(2026, 11, 1, 1, 30, tzinfo=fold_zone, fold=1)
    assert first == second and first.astimezone(timezone.utc) != second.astimezone(timezone.utc)
    previous_fold = _parse(_row(), metadata=previous.metadata, as_of=first)
    current_fold = _parse(_row(quantity="110"), as_of=second)
    assert _api().compare_quarters(previous_fold, current_fold).reasons == ("AS_OF_MISMATCH",)
    malformed = [
        _api().ParseResult("AVAILABLE", comparison_eligible=True,
                           metadata=_api().FilingMetadata(), as_of=AS_OF),
        replace(current, raw_rows=()), replace(current, holdings=()),
        replace(current, raw_rows=(object(),)), replace(current, holdings=(object(),)),
        replace(current, metadata=replace(current.metadata, complete=False)),
        replace(current, metadata=replace(current.metadata, entry_total=2)),
        replace(current, holdings=(replace(current.holdings[0], quantity=999),)),
        replace(current, raw_rows=(replace(current.raw_rows[0], quantity="bad"),)),
    ]
    for capture in malformed:
        comparison = _api().compare_quarters(previous, capture)
        assert comparison.status == "NOT_AVAILABLE" and comparison.changes == ()


def test_same_cusip_incompatible_security_basis_is_not_aliased_to_new_exit():
    for kwargs in (dict(title="CLASS B"), dict(quantity_type="PRN"), dict(put_call="Put"),
                   dict(discretion="DFND"), dict(other="1")):
        result = _compare([_row()], [_row(**kwargs)],
                          current_updates=dict(other_manager_ciks={"1": "456"}))
        assert result.status == "NOT_AVAILABLE" and result.changes == ()
        assert result.reasons == ("INCOMPATIBLE_SECURITY_BASIS",)


def test_results_rows_keys_changes_are_frozen_and_private_in_repr():
    previous, current = _pair([_row()], [_row(quantity="110")])
    result = _api().compare_quarters(previous, current)
    objects = [_metadata(), current, current.raw_rows[0], current.holdings[0],
               current.holdings[0].key, result, result.changes[0]]
    for obj in objects:
        assert "Synthetic Issuer" not in repr(obj) and "123456789" not in repr(obj)
        assert MANAGER not in repr(obj)
    for obj, attribute in ((current, "status"), (current.raw_rows[0], "quantity"),
                           (current.holdings[0], "quantity"), (current.holdings[0].key, "cusip"),
                           (result.changes[0], "kind")):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, attribute, "mutated")
    with pytest.raises(TypeError):
        current.raw_rows[0].raw_fields["value"] = "private"
    for obj in (current, result, result.changes[0]):
        with pytest.raises(ValueError):
            replace(obj, role="ACTUAL_TRADE")


def test_reasons_are_fixed_and_do_not_echo_invalid_inputs_or_private_metadata():
    sentinel = "PRIVATE_SENTINEL_EMAIL@example.invalid"
    result = _parse(_row(issuer=sentinel, quantity=sentinel))
    assert result.status == "NOT_AVAILABLE"
    assert all(sentinel not in reason for reason in result.reasons)
    assert sentinel not in repr(result) and result.raw_rows == ()


def test_comparison_has_no_value_basis_price_split_or_trade_inference():
    result = _compare([_row()], [_row(quantity="200", value="999")],
                      current_updates=dict(value_basis="USD_THOUSANDS"))
    assert result.status == "AVAILABLE"
    change, = result.changes
    assert (change.kind, change.delta_quantity) == ("ADD", 100)
    assert not hasattr(change, "price") and not hasattr(change, "actual_trade")
    assert "매수" not in change.label and "매도" not in change.label
