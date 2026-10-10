"""Pure fixed request descriptors and parsers of caller-supplied primary bodies.

No HTTP, credentials, environment access, storage, or model invocation occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from xml.etree import ElementTree

from ..macro.primary_contract import (
    BEA_TABLES, BLS_SERIES_IDS, ENDPOINTS, SOURCE_IDS, SOURCE_REGISTRY, TREASURY_SOURCE,
    MacroObservation, ParseResult, ReleaseMetadata, RequestPlan, SourceReceipt,
    aware, make_result, nonempty, observation_id, release_error, valid_hash,
)


def _year(year: object) -> bool:
    return type(year) is int and 1 <= year <= 9999


def _bls_ids(ids: object) -> bool:
    return (type(ids) is tuple and bool(ids) and all(type(s) is str and s in BLS_SERIES_IDS for s in ids)
            and len(ids) == len(set(ids)))


def _plan(provider: str, *, parameters=(), body=None, valid=True) -> RequestPlan:
    return RequestPlan(provider, "POST" if provider == "BLS" else "GET", ENDPOINTS[provider],
                       tuple(parameters) if valid else (), body if valid else None,
                       "BEA_USERID" if provider == "BEA" else None,
                       "PLANNED" if valid else "NOT_AVAILABLE", () if valid else ("INVALID_REQUEST",))


def build_bls_plan(series_ids: tuple[str, ...], start_year: int, end_year: int) -> RequestPlan:
    if not (_bls_ids(series_ids) and _year(start_year) and _year(end_year)
            and 0 <= end_year - start_year < 10):
        return _plan("BLS", valid=False)
    body = json.dumps({"seriesid": list(series_ids), "startyear": str(start_year), "endyear": str(end_year)},
                      separators=(",", ":")).encode()
    return _plan("BLS", body=body)


def build_bea_plan(table_name: str, years: tuple[int, ...]) -> RequestPlan:
    if not (type(table_name) is str and table_name in BEA_TABLES and type(years) is tuple
            and bool(years) and all(_year(y) for y in years) and tuple(sorted(set(years))) == years):
        return _plan("BEA", valid=False)
    return _plan("BEA", parameters=(("method", "GetData"), ("DataSetName", "NIPA"),
                 ("TableName", table_name), ("Frequency", "Q"), ("Year", ",".join(map(str, years))),
                 ("ResultFormat", "JSON")))


def build_treasury_plan(year: int) -> RequestPlan:
    if not _year(year):
        return _plan("TREASURY", valid=False)
    return _plan("TREASURY", parameters=(("data", "daily_treasury_yield_curve"),
                                        ("field_tdr_date_value", str(year))))


def _receipt_error(body: object, receipt: object, provider: str) -> str | None:
    if not isinstance(receipt, SourceReceipt) or type(body) is not bytes:
        return "INVALID_RECEIPT"
    if (receipt.provider != provider or receipt.source_url != ENDPOINTS[provider]
            or not valid_hash(receipt.response_sha256) or type(receipt.synthetic) is not bool
            or receipt.rights_status not in ("CLEARED_SCOPE", "UNCONFIRMED")
            or hashlib.sha256(body).hexdigest() != receipt.response_sha256):
        return "INVALID_RECEIPT"
    if not aware(receipt.acquired_at):
        return "INVALID_TIMESTAMP"
    if receipt.rights_status != "CLEARED_SCOPE":
        return "RIGHTS_UNCONFIRMED"
    return None


def _failed(reason: str, expected, receipt=None) -> ParseResult:
    synthetic = receipt.synthetic if isinstance(receipt, SourceReceipt) and type(receipt.synthetic) is bool else True
    return make_result(reasons=(reason,), expected=expected, synthetic=synthetic)


def _json_body(body: bytes):
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        return None
    return result if type(result) is dict else None


@dataclass(frozen=True)
class _Row:
    period: str
    raw_value: object = field(repr=False)
    unit: str
    multiplier: int | None = None
    metric: str | None = None
    series_code: str | None = None
    notes: tuple[str, ...] = field(default=(), repr=False)


_NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?", re.ASCII)
_BEA_NUMBER = re.compile(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", re.ASCII)


def _number(raw: object, provider: str) -> tuple[Decimal | None, str | None]:
    if provider in ("BEA", "TREASURY") and (raw is None or (type(raw) is str and raw in ("", "N/A", "NA", "(NA)", "--", "---", "...", "(D)"))):
        return None, "MISSING_SOURCE"
    pattern = _BEA_NUMBER if provider == "BEA" else _NUMBER
    if type(raw) is not str or pattern.fullmatch(raw) is None:
        return None, "INVALID_VALUE"
    try:
        value = Decimal(raw.replace(",", "") if provider == "BEA" else raw)
    except InvalidOperation:
        return None, "INVALID_VALUE"
    return (value, None) if value.is_finite() else (None, "INVALID_VALUE")


def _finish(rows_by_source, errors, expected, receipt: SourceReceipt, release, warnings=()) -> ParseResult:
    """Validate each source independently, retaining the other valid sources."""
    observations, reasons = [], list(warnings)
    supplied_release = ReleaseMetadata() if release is None else release
    for source in expected:
        if source in errors:
            reasons.append(errors[source])
            continue
        definition = SOURCE_REGISTRY[source]
        rows = rows_by_source.get(source, ())
        parsed, invalid = [], False
        for row in rows:
            value, error = _number(row.raw_value, definition.provider)
            if error:
                reasons.append(error)
                if error != "MISSING_SOURCE":
                    invalid = True
                continue
            parsed.append((row, value))
        if invalid:
            continue
        unique, conflict = {}, False
        for row, value in parsed:
            # Compare meaningful parsed fields, not lexical number formatting.
            semantic = (value, row.unit, row.multiplier, row.metric, row.series_code, row.notes)
            previous = unique.get(row.period)
            if previous is not None and previous[2] != semantic:
                conflict = True
                break
            if previous is None or str(value) < str(previous[1]):
                unique[row.period] = (row, value, semantic)
        if conflict:
            reasons.append("CONFLICTING_DUPLICATE")
            continue
        if not unique:
            reasons.append("MISSING_SOURCE")
            continue
        error = release_error(supplied_release, receipt.acquired_at)
        if error:
            reasons.append(error)
            continue
        for period in sorted(unique):
            row, value, _ = unique[period]
            observations.append(MacroObservation(
                observation_id(source, period, value, row.unit, definition.seasonal_adjustment,
                               receipt.response_sha256, receipt.acquired_at), source, definition.axis,
                period, definition.frequency, row.unit, definition.seasonal_adjustment, value,
                row.multiplier, row.metric, row.series_code, row.notes, receipt.response_sha256,
                receipt.acquired_at, receipt.acquired_at, receipt.acquired_at, supplied_release,
                "OBSERVED_CAPTURE_UPPER_BOUND", "OBSERVED_CAPTURE", receipt.synthetic, definition.quality_flags,
            ))
    return make_result(observations, reasons, expected, synthetic=receipt.synthetic)


def _bls_notes(footnotes):
    if type(footnotes) is not list:
        return None
    notes = []
    for note in footnotes:
        if type(note) is not dict or any(type(note[k]) is not str for k in ("code", "text") if k in note):
            return None
        if note.get("code"):
            notes.append("code:" + note["code"])
        if note.get("text"):
            notes.append("text:" + note["text"])
    return tuple(notes)


def parse_bls(body: bytes, receipt: SourceReceipt, *, expected_series_ids: tuple[str, ...],
              release: ReleaseMetadata | None = None) -> ParseResult:
    if not _bls_ids(expected_series_ids):
        return _failed("INVALID_REQUEST", (), receipt)
    expected = tuple(s for s in SOURCE_IDS if s in tuple("BLS:" + raw for raw in expected_series_ids))
    error = _receipt_error(body, receipt, "BLS")
    if error:
        return _failed(error, expected, receipt)
    obj = _json_body(body)
    if obj is None:
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    if obj.get("status") != "REQUEST_SUCCEEDED":
        return _failed("PROVIDER_ERROR", expected, receipt)
    results = obj.get("Results")
    if type(results) is not dict or type(results.get("series")) is not list:
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    rows, errors, warnings = {}, {}, []
    for series in results["series"]:
        if (type(series) is not dict or type(series.get("seriesID")) is not str
                or series["seriesID"] not in expected_series_ids):
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        source = "BLS:" + series["seriesID"]
        if type(series.get("data")) is not list:
            errors[source] = "SCHEMA_MISMATCH"
            continue
        for row in series["data"]:
            if type(row) is not dict:
                errors[source] = "SCHEMA_MISMATCH"
                continue
            year, period = row.get("year"), row.get("period")
            notes = _bls_notes(row.get("footnotes", []))
            if (type(year) is not str or re.fullmatch(r"[0-9]{4}", year) is None or not _year(int(year))
                    or type(period) is not str or re.fullmatch(r"M(?:0[1-9]|1[0-3])", period) is None or notes is None):
                errors[source] = "SCHEMA_MISMATCH"
                continue
            if period == "M13":
                warnings.append("ANNUAL_AVERAGE_EXCLUDED")
                continue
            rows.setdefault(source, []).append(_Row(year + "-" + period[1:], row.get("value"),
                                                   SOURCE_REGISTRY[source].unit, notes=notes))
    return _finish(rows, errors, expected, receipt, release, warnings)


def _bea_notes(raw):
    if type(raw) is not list:
        return None
    notes = []
    for item in raw:
        if type(item) is not dict or not nonempty(item.get("NoteText")):
            return None
        ref = item.get("NoteRef", "")
        if type(ref) is not str:
            return None
        notes.append((ref + ":" if ref else "") + item["NoteText"])
    return tuple(notes)


def _multiplier(value):
    if type(value) is int:
        return value
    if type(value) is str and re.fullmatch(r"-?[0-9]{1,4}", value):
        return int(value)
    return None


def parse_bea_nipa(body: bytes, receipt: SourceReceipt, *, expected_table: str,
                   release: ReleaseMetadata | None = None) -> ParseResult:
    if type(expected_table) is not str or expected_table not in BEA_TABLES:
        return _failed("INVALID_REQUEST", (), receipt)
    source = f"BEA:NIPA:{expected_table}:1:Q"
    expected = (source,)
    error = _receipt_error(body, receipt, "BEA")
    if error:
        return _failed(error, expected, receipt)
    obj = _json_body(body)
    if obj is None or type(obj.get("BEAAPI")) is not dict:
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    api = obj["BEAAPI"]
    results = api.get("Results")
    if "Error" in api or (type(results) is dict and "Error" in results):
        return _failed("PROVIDER_ERROR", expected, receipt)
    if type(results) is not dict or type(results.get("Data")) is not list:
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    notes = _bea_notes(results.get("Notes", []))
    if notes is None:
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    rows = []
    for row in results["Data"]:
        if type(row) is not dict or row.get("TableName") != expected_table:
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        line = row.get("LineNumber")
        if not ((type(line) is str and re.fullmatch(r"[0-9]+", line)) or type(line) is int):
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        if str(line) != "1":
            continue
        period = row.get("TimePeriod")
        mult = _multiplier(row.get("UNIT_MULT"))
        if (type(period) is not str or re.fullmatch(r"[0-9]{4}Q[1-4]", period) is None or not _year(int(period[:4]))
                or any(not nonempty(row.get(k)) for k in ("SeriesCode", "LineDescription", "Metric_Name", "CL_UNIT"))
                or mult is None):
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        row_notes = _bea_notes(row.get("Notes", []))
        if row_notes is None:
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        rows.append(_Row(period, row.get("DataValue"), row["CL_UNIT"], mult, row["Metric_Name"], row["SeriesCode"],
                         ("LineDescription:" + row["LineDescription"],) + notes + row_notes))
    # BEAAPI.Request can echo credentials; no part of it is copied to the result.
    return _finish({source: rows}, {}, expected, receipt, release)


_ATOM = "{http://www.w3.org/2005/Atom}"
_DATA = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
_META = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"


def _treasury_date(raw):
    if type(raw) is not str or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?", raw) is None:
        return None
    try:
        if "T" in raw:
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError:
        return None


def parse_treasury_yields(body: bytes, receipt: SourceReceipt, *, release: ReleaseMetadata | None = None) -> ParseResult:
    expected = (TREASURY_SOURCE,)
    error = _receipt_error(body, receipt, "TREASURY")
    if error:
        return _failed(error, expected, receipt)
    # Removing NULs also catches UTF-16/32 declarations before XML parsing.
    probe = body.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        return _failed("UNSAFE_XML", expected, receipt)
    try:
        root = ElementTree.fromstring(body)
    except (ElementTree.ParseError, ValueError, LookupError):
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    if root.tag != _ATOM + "feed":
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    if any(child.tag.rsplit("}", 1)[-1] == "entry" and child.tag != _ATOM + "entry" for child in root):
        return _failed("SCHEMA_MISMATCH", expected, receipt)
    rows = []
    for entry in root.findall(_ATOM + "entry"):
        properties = entry.findall(_ATOM + "content/" + _META + "properties")
        if len(properties) != 1:
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        props = properties[0]
        if any(e.tag.rsplit("}",1)[-1] in ("NEW_DATE", "BC_10YEAR") and e.tag not in (_DATA+"NEW_DATE", _DATA+"BC_10YEAR") for e in props):
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        dates = props.findall(_DATA + "NEW_DATE")
        rates = props.findall(_DATA + "BC_10YEAR")
        if len(dates) != 1 or len(rates) > 1:
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        period = _treasury_date(dates[0].text)
        if period is None:
            return _failed("SCHEMA_MISMATCH", expected, receipt)
        if not rates:
            # A field in a different namespace is a schema error, not a null.
            if any(e.tag.rsplit("}", 1)[-1] == "BC_10YEAR" for e in props):
                return _failed("SCHEMA_MISMATCH", expected, receipt)
            value = None
        else:
            if any(key.rsplit("}",1)[-1] == "null" and key != _META+"null" for key in rates[0].attrib):
                return _failed("SCHEMA_MISMATCH", expected, receipt)
            null = rates[0].get(_META + "null")
            if null not in (None, "true", "false"):
                return _failed("SCHEMA_MISMATCH", expected, receipt)
            value = None if null == "true" else rates[0].text
        rows.append(_Row(period, value, "percent"))
    return _finish({TREASURY_SOURCE: rows}, {}, expected, receipt, release)
