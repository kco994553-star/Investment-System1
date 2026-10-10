"""Offline request descriptors and supplied-body parsers. No transport or storage."""
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import xml.etree.ElementTree as ET

from ..macro.primary_contract import (
    BLS_SERIES, ENDPOINTS, TREASURY_ID, SourceReceipt, ReleaseMetadata,
    MacroObservation, ParseResult, RequestPlan, aware, observation_id,
)


def _year(year):
    return type(year) is int and 1900 <= year <= 9999


def _plan(provider, valid, parameters=(), body=None):
    return RequestPlan(provider, "POST" if provider == "BLS" else "GET", ENDPOINTS[provider],
                       parameters if valid else (), body if valid else None,
                       "BEA_USERID" if provider == "BEA" else None,
                       "PLANNED" if valid else "NOT_AVAILABLE", () if valid else ("INVALID_REQUEST",))


def _bls_ids(ids):
    return isinstance(ids, tuple) and 0 < len(ids) <= 25 and all(isinstance(s,str) and s in BLS_SERIES for s in ids) and len(set(ids)) == len(ids)


def build_bls_plan(series_ids: tuple[str, ...], start_year: int, end_year: int) -> RequestPlan:
    valid = _bls_ids(series_ids) and _year(start_year) and _year(end_year) and 0 <= end_year-start_year < 10
    body = json.dumps(dict(seriesid=series_ids, startyear=str(start_year), endyear=str(end_year)), sort_keys=True).encode() if valid else None
    return _plan("BLS", valid, body=body)


def build_bea_plan(table_name: str, years: tuple[int, ...]) -> RequestPlan:
    valid = table_name in ("T10106", "T10101") and isinstance(years, tuple) and bool(years) and all(_year(y) for y in years) and list(years) == sorted(set(years))
    params = (("method", "GetData"), ("DataSetName", "NIPA"), ("TableName", table_name), ("Frequency", "Q"), ("Year", ",".join(map(str,years))), ("ResultFormat", "JSON")) if valid else ()
    return _plan("BEA", valid, params)


def build_treasury_plan(year: int) -> RequestPlan:
    return _plan("TREASURY", _year(year), (("data", "daily_treasury_yield_curve"), ("field_tdr_date_value", str(year))))


def _result(observations=(), reasons=(), expected=(), synthetic=True):
    present = {o.source_id for o in observations}
    missing = tuple(s for s in expected if s not in present)
    return ParseResult("INPUT_RESEARCH" if observations else "NOT_AVAILABLE", tuple(observations),
                       tuple(dict.fromkeys(reasons)), missing, synthetic)


def _receipt_reason(body, receipt, provider):
    if not isinstance(body, bytes) or not isinstance(receipt, SourceReceipt):
        return "INVALID_RECEIPT"
    if receipt.provider != provider or receipt.source_url != ENDPOINTS[provider] or type(receipt.synthetic) is not bool or receipt.response_sha256 != hashlib.sha256(body).hexdigest():
        return "INVALID_RECEIPT"
    if not aware(receipt.acquired_at):
        return "INVALID_TIMESTAMP"
    if receipt.rights_status != "CLEARED_SCOPE":
        return "RIGHTS_UNCONFIRMED"
    return None


def _release_reason(release, at):
    if release is None:
        return None
    if not isinstance(release, ReleaseMetadata):
        return "RELEASE_EVIDENCE_UNCONFIRMED"
    if release.release_at is not None and not aware(release.release_at):
        return "INVALID_TIMESTAMP"
    if release.release_at is not None and release.release_at > at:
        return "INVALID_TIME_ORDER"
    if release.release_at is None or release.evidence_kind != "PUBLISHED_ARTIFACT" or not isinstance(release.release_evidence_ref,str) or not release.release_evidence_ref.strip() or release.estimate_kind not in ("INITIAL", "ADVANCE", "SECOND", "THIRD", "REVISED", "UNKNOWN"):
        return "RELEASE_EVIDENCE_UNCONFIRMED"
    return None


def _number(value, *, comma=False):
    if not isinstance(value, str):
        return None
    pattern = r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?" if comma else r"[+-]?\d+(?:\.\d+)?"
    if not re.fullmatch(pattern, value):
        return None
    try:
        number = Decimal(value.replace(",", ""))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def _observation(receipt, source, axis, period, frequency, unit, sa, value,
                 release, notes=(), multiplier=None, metric=None, series=None):
    return MacroObservation(observation_id(source, period, value, unit, sa, receipt.response_sha256, receipt.acquired_at),
                            source, axis, period, frequency, unit, sa, value, multiplier, metric, series, notes,
                            receipt.response_sha256, receipt.acquired_at, receipt.acquired_at, receipt.acquired_at,
                            release or ReleaseMetadata(), "OBSERVED_CAPTURE_UPPER_BOUND", "OBSERVED_CAPTURE", receipt.synthetic,
                            ("CURRENT_HISTORY_MAY_BE_REVISED", "FIRST_PUBLICATION_NOT_PROVEN"))


def _finish(observations, reasons, expected, receipt, release):
    grouped = {}
    conflicts = set()
    for o in observations:
        key = (o.source_id, o.observation_period)
        if key in grouped and grouped[key] != o:
            conflicts.add(o.source_id)
        grouped[key] = o
    if conflicts:
        reasons.append("CONFLICTING_DUPLICATE")
    good = tuple(o for _,o in sorted(grouped.items()) if o.source_id not in conflicts)
    reason = _release_reason(release, receipt.acquired_at)
    if reason:
        return _result(reasons=(reason,), expected=expected, synthetic=receipt.synthetic)
    missing = set(expected)-{o.source_id for o in good}
    if missing and not reasons:
        reasons.append("MISSING_SOURCE")
    return _result(good, reasons, expected, receipt.synthetic)


def parse_bls(body: bytes, receipt: SourceReceipt, *, expected_series_ids: tuple[str, ...], release: ReleaseMetadata | None = None) -> ParseResult:
    if not _bls_ids(expected_series_ids):
        return _result(reasons=("INVALID_REQUEST",))
    expected = tuple("BLS:"+s for s in expected_series_ids)
    reason = _receipt_reason(body, receipt, "BLS")
    if reason:
        return _result(reasons=(reason,), expected=expected)
    try:
        root = json.loads(body)
        if root.get("status") != "REQUEST_SUCCEEDED":
            return _result(reasons=("PROVIDER_ERROR",), expected=expected, synthetic=receipt.synthetic)
        series = root["Results"]["series"]
        if not isinstance(series,list):
            raise ValueError
        observations, reasons, invalid = [], [], set()
        for item in series:
            sid = item["seriesID"]
            if sid not in expected_series_ids or not isinstance(item["data"],list):
                raise ValueError
            source = "BLS:"+sid
            for row in item["data"]:
                year, period = row.get("year"), row.get("period")
                if not isinstance(year,str) or not re.fullmatch(r"[1-9]\d{3}",year) or not isinstance(period,str) or not re.fullmatch(r"M(?:0[1-9]|1[0-3])",period):
                    invalid.add(source); reasons.append("SCHEMA_MISMATCH"); continue
                if period == "M13":
                    reasons.append("ANNUAL_AVERAGE_EXCLUDED"); continue
                value = _number(row.get("value"))
                if value is None:
                    invalid.add(source); reasons.append("INVALID_VALUE"); continue
                footnotes = row.get("footnotes", [])
                if not isinstance(footnotes,list) or any(not isinstance(f,dict) or any(not isinstance(v,str) for v in f.values()) for f in footnotes):
                    invalid.add(source); reasons.append("SCHEMA_MISMATCH"); continue
                notes = tuple(f.get("code", "")+":"+f.get("text", "") for f in footnotes if f)
                axis, unit, sa = BLS_SERIES[sid]
                observations.append(_observation(receipt,source,axis,year+"-"+period[1:],"M",unit,sa,value,release,notes))
        observations = [o for o in observations if o.source_id not in invalid]
        return _finish(observations,reasons,expected,receipt,release)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        return _result(reasons=("SCHEMA_MISMATCH",), expected=expected, synthetic=receipt.synthetic)


def parse_bea_nipa(body: bytes, receipt: SourceReceipt, *, expected_table: str, release: ReleaseMetadata | None = None) -> ParseResult:
    if expected_table not in ("T10106", "T10101"):
        return _result(reasons=("INVALID_REQUEST",))
    source = f"BEA:NIPA:{expected_table}:1:Q"
    reason = _receipt_reason(body,receipt,"BEA")
    if reason:
        return _result(reasons=(reason,),expected=(source,))
    try:
        root = json.loads(body)["BEAAPI"]
        results = root["Results"]
        if "Error" in results or "Error" in root:
            return _result(reasons=("PROVIDER_ERROR",),expected=(source,),synthetic=receipt.synthetic)
        data, notes = results["Data"], results.get("Notes", [])
        if not isinstance(data,list) or not isinstance(notes,list) or any(not isinstance(n,dict) or not isinstance(n.get("NoteText"),str) for n in notes):
            raise ValueError
        observations, reasons = [], []
        for row in data:
            if row.get("TableName") != expected_table:
                raise ValueError
            if row.get("LineNumber") != "1":
                continue
            period = row["TimePeriod"]
            if not isinstance(period,str) or not re.fullmatch(r"[1-9]\d{3}Q[1-4]",period):
                raise ValueError
            for key in ("SeriesCode", "LineDescription", "Metric_Name", "CL_UNIT"):
                if not isinstance(row.get(key),str) or not row[key].strip():
                    raise ValueError
            mult = row["UNIT_MULT"]
            if not isinstance(mult,str) or not re.fullmatch(r"[+-]?\d+",mult):
                raise ValueError
            value = _number(row.get("DataValue"),comma=True)
            if value is None:
                reasons.append("INVALID_VALUE"); continue
            observations.append(_observation(receipt,source,"Growth",period,"Q",row["CL_UNIT"],"PROVIDER_DEFINED",value,release,
                                            (row["LineDescription"],)+tuple(n["NoteText"] for n in notes),int(mult),row["Metric_Name"],row["SeriesCode"]))
        if reasons:
            observations = []
        return _finish(observations,reasons,(source,),receipt,release)
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        return _result(reasons=("SCHEMA_MISMATCH",),expected=(source,),synthetic=receipt.synthetic)


def parse_treasury_yields(body: bytes, receipt: SourceReceipt, *, release: ReleaseMetadata | None = None) -> ParseResult:
    reason = _receipt_reason(body,receipt,"TREASURY")
    if reason:
        return _result(reasons=(reason,),expected=(TREASURY_ID,))
    # Reject markup before XML parsing, including UTF-16/32 encoded declarations.
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", body.replace(b"\x00", b""), re.IGNORECASE):
        return _result(reasons=("UNSAFE_XML",),expected=(TREASURY_ID,),synthetic=receipt.synthetic)
    atom = "{http://www.w3.org/2005/Atom}"
    data = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
    meta = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"
    try:
        root = ET.fromstring(body)
        if root.tag != atom+"feed":
            raise ValueError
        observations, reasons = [], []
        for entry in root.findall(atom+"entry"):
            props = entry.find(atom+"content/"+meta+"properties")
            if props is None:
                raise ValueError
            dt, yield_node = props.find(data+"NEW_DATE"), props.find(data+"BC_10YEAR")
            if dt is None or not dt.text or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00",dt.text):
                raise ValueError
            period = date.fromisoformat(dt.text[:10]).isoformat()
            if yield_node is None or yield_node.get(meta+"null") == "true" or yield_node.text in (None,"N/A"):
                reasons.append("MISSING_SOURCE"); continue
            value = _number(yield_node.text)
            if value is None:
                reasons.append("INVALID_VALUE"); continue
            observations.append(_observation(receipt,TREASURY_ID,"Monetary Policy",period,"D","percent","NOT_APPLICABLE",value,release))
        if "INVALID_VALUE" in reasons:
            observations = []
        return _finish(observations,reasons,(TREASURY_ID,),receipt,release)
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        return _result(reasons=("SCHEMA_MISMATCH",),expected=(TREASURY_ID,),synthetic=receipt.synthetic)
