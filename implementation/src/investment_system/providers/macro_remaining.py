"""Pure supplied-body parsers for four unadopted government evidence families.

No requests, environment/credential access, storage, scoring, scaling or FX
conversion. Fed support is limited to the schema-backed standalone common
DataSet; the full-feed SDMX envelope has not been verified. Explicit selectors
are caller evidence, never a default series or approval for model input.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from types import MappingProxyType
from typing import Literal
from urllib.parse import parse_qsl, urlsplit
from xml.etree import ElementTree

from ..macro.primary_contract import aware, nonempty, utc, valid_hash

MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
PROVIDER_AXES = MappingProxyType({"FED_H41": "Liquidity", "FED_H8": "Credit", "FED_H10": "FX", "TREASURY_MTS": "Fiscal"})
REASON_CODES = (
    "UNADOPTED_INPUT_SELECTION", "INVALID_REQUEST", "INVALID_RESULT", "INVALID_RECEIPT",
    "INVALID_TIMESTAMP", "INVALID_TIME_ORDER", "RIGHTS_UNCONFIRMED", "PAYLOAD_TOO_LARGE",
    "UNSAFE_XML", "SCHEMA_MISMATCH", "INCOMPLETE_PAYLOAD", "INVALID_VALUE", "MISSING_VALUE",
    "CONFLICTING_DUPLICATE", "CONFLICTING_VINTAGE", "OBSERVATION_ID_COLLISION",
    "MIXED_SYNTHETIC_INPUT", "AVAILABLE_AFTER_AS_OF", "MISSING_SOURCE",
)
_FED_COMMON = "http://www.federalreserve.gov/structure/compact/common"
_FED_RELEASES = MappingProxyType({"FED_H41": "H41", "FED_H8": "H8", "FED_H10": "H10"})
_BASIS_FIELDS = MappingProxyType({
    "FED_H41": ("CATEGORY", "SUBCATEGORY", "COMPONENT", "DISTRIBUTION", "SERIESTYPE"),
    "FED_H8": ("SA", "BG", "H8_UNITS", "CATEGORY", "ITEM"),
    "FED_H10": ("FX",),
})
_FREQUENCIES = MappingProxyType({"8": "D", "9": "D", **{str(n): "W" for n in range(16, 23)}, "129": "M", "162": "Q", "203": "A"})
_FIELD = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,127}", re.ASCII)
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?", re.ASCII)
_MISSING = ("", "null", "NA", "N/A", "ND", "--", "---", "...", ".")


@dataclass(frozen=True)
class RemainingSeriesBinding:
    axis: str
    provider: str
    unit: str = field(repr=False)
    frequency: str
    seasonal_adjustment: str
    basis: str
    observation_field: str
    period_field: str
    source_id: str | None = None
    field_filters: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    table_path: str | None = None
    source_frequency: str | None = None
    unit_multiplier: Decimal | None = None
    dataset_id: str | None = None


@dataclass(frozen=True)
class GovernmentReceipt:
    provider: str
    source_url: str = field(repr=False)
    response_sha256: str
    acquired_at: datetime
    synthetic: bool
    rights_status: Literal["CLEARED_SCOPE", "UNCONFIRMED"]


@dataclass(frozen=True)
class RemainingObservation:
    observation_id: str
    source_id: str
    axis: str
    provider: str
    observation_period: str
    value: Decimal = field(repr=False)
    unit: str = field(repr=False)
    frequency: str
    seasonal_adjustment: str
    basis: str
    source_frequency: str | None
    unit_multiplier: Decimal | None
    available_at: datetime
    vintage_at: datetime
    ingested_at: datetime
    source_response_sha256: str
    synthetic: bool
    source_url: str = field(repr=False)
    rights_status: str
    binding: RemainingSeriesBinding = field(repr=False)
    source_metadata: tuple[tuple[str, str], ...] = field(repr=False)
    availability_basis: Literal["OBSERVED_CAPTURE_UPPER_BOUND"] = "OBSERVED_CAPTURE_UPPER_BOUND"
    vintage_kind: Literal["OBSERVED_CAPTURE"] = "OBSERVED_CAPTURE"


@dataclass(frozen=True)
class RemainingParseResult:
    state: Literal["RAW_EVIDENCE", "NOT_AVAILABLE"]
    observations: tuple[RemainingObservation, ...] = field(repr=False)
    reason_codes: tuple[str, ...]
    synthetic: bool


def _result(observations=(), reasons=(), *, synthetic=True):
    observations = tuple(observations)
    return RemainingParseResult("RAW_EVIDENCE" if observations else "NOT_AVAILABLE", observations,
                                tuple(r for r in REASON_CODES if r in reasons), synthetic)


def _failed(reason, receipt=None):
    synthetic = receipt.synthetic if isinstance(receipt, GovernmentReceipt) and type(receipt.synthetic) is bool else True
    return _result(reasons=(reason,), synthetic=synthetic)


def _pairs(value):
    return (type(value) is tuple and all(type(p) is tuple and len(p) == 2 and
            type(p[0]) is str and _FIELD.fullmatch(p[0]) is not None and nonempty(p[1]) for p in value)
            and len({p[0] for p in value}) == len(value))


def _binding_valid(binding, provider=None):
    if not isinstance(binding, RemainingSeriesBinding):
        return False
    if (type(binding.provider) is not str or binding.provider not in PROVIDER_AXES
            or (provider is not None and binding.provider != provider)
            or binding.axis != PROVIDER_AXES[binding.provider]
            or any(not nonempty(getattr(binding, name)) for name in
                   ("unit", "frequency", "seasonal_adjustment", "basis", "observation_field", "period_field"))
            or binding.frequency not in ("D", "W", "M", "Q", "A")
            or _FIELD.fullmatch(binding.observation_field) is None or _FIELD.fullmatch(binding.period_field) is None
            or (binding.source_id is not None and not nonempty(binding.source_id))
            or not _pairs(binding.field_filters)):
        return False
    if binding.provider == "TREASURY_MTS":
        return (nonempty(binding.table_path) and re.fullmatch(r"mts_table_[1-9][0-9]*", binding.table_path) is not None
                and bool(binding.field_filters) and binding.period_field != "record_date"
                and binding.observation_field != "record_date" and binding.source_frequency is None
                and binding.unit_multiplier is None and binding.dataset_id is None)
    filters = dict(binding.field_filters)
    return (binding.table_path is None and nonempty(binding.dataset_id)
            and binding.observation_field == "OBS_VALUE" and binding.period_field == "TIME_PERIOD"
            and (nonempty(binding.source_id) or bool(binding.field_filters))
            and all(key in filters for key in _BASIS_FIELDS[binding.provider])
            and type(binding.source_frequency) is str and _FREQUENCIES.get(binding.source_frequency) == binding.frequency
            and type(binding.unit_multiplier) is Decimal and binding.unit_multiplier.is_finite() and binding.unit_multiplier > 0
            and (binding.seasonal_adjustment in ("SA", "NSA") if binding.provider == "FED_H8"
                 else binding.seasonal_adjustment == "NOT_APPLICABLE"))


def _source_url_valid(source_url, binding):
    if type(source_url) is not str or len(source_url) > 8192 or any(ord(c) < 32 for c in source_url):
        return False
    try:
        url = urlsplit(source_url)
        if url.scheme != "https" or url.fragment or url.username is not None or url.password is not None:
            return False
        query = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True, max_num_fields=24)
    except (ValueError, UnicodeError):
        return False
    if len({k for k, _ in query}) != len(query):
        return False
    params = dict(query)
    if binding.provider == "TREASURY_MTS":
        return (url.netloc == "api.fiscaldata.treasury.gov" and url.path ==
                "/services/api/fiscal_service/v1/accounting/mts/" + binding.table_path
                and all(k in ("fields", "filter", "sort", "format", "page[number]", "page[size]") for k in params)
                and params.get("format", "json") == "json")
    return (url.netloc == "www.federalreserve.gov" and url.path == "/datadownload/Output.aspx"
            and all(k in ("rel", "series", "lastobs", "from", "to", "filetype", "label", "layout", "type") for k in params)
            and params.get("rel") == _FED_RELEASES[binding.provider] and params.get("filetype") == "sdmx"
            and params.get("type", "package") == "package")


def _receipt_error(payload, receipt, binding):
    if (type(payload) is not bytes or not isinstance(receipt, GovernmentReceipt)
            or receipt.provider != binding.provider or not valid_hash(receipt.response_sha256)
            or type(receipt.synthetic) is not bool or not _source_url_valid(receipt.source_url, binding)
            or receipt.rights_status not in ("CLEARED_SCOPE", "UNCONFIRMED")
            or hashlib.sha256(payload).hexdigest() != receipt.response_sha256):
        return "INVALID_RECEIPT"
    if not aware(receipt.acquired_at):
        return "INVALID_TIMESTAMP"
    if receipt.rights_status != "CLEARED_SCOPE":
        return "RIGHTS_UNCONFIRMED"
    if len(payload) > MAX_PAYLOAD_BYTES:
        return "PAYLOAD_TOO_LARGE"
    return None


def _period_valid(period, frequency):
    if type(period) is not str:
        return False
    try:
        if frequency in ("D", "W") and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", period):
            date.fromisoformat(period)
            return True
        if frequency == "M" and re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", period):
            date.fromisoformat(period + "-01")
            return True
        if frequency == "Q" and re.fullmatch(r"[0-9]{4}-?Q[1-4]", period):
            return int(period[:4]) > 0
        if frequency == "A" and re.fullmatch(r"[0-9]{4}", period):
            return int(period) > 0
    except ValueError:
        pass
    return False


def _number(raw):
    if raw is None or (type(raw) is str and raw in _MISSING):
        return None, "MISSING_VALUE"
    if type(raw) is not str or _NUMBER.fullmatch(raw) is None:
        return None, "INVALID_VALUE"
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None, "INVALID_VALUE"
    return (value, None) if value.is_finite() else (None, "INVALID_VALUE")


def _binding_view(binding):
    return {"axis": binding.axis, "provider": binding.provider, "unit": binding.unit,
            "frequency": binding.frequency, "seasonal_adjustment": binding.seasonal_adjustment,
            "basis": binding.basis, "observation_field": binding.observation_field,
            "period_field": binding.period_field, "source_id": binding.source_id,
            "field_filters": sorted(binding.field_filters), "table_path": binding.table_path,
            "dataset_id": binding.dataset_id,
            "source_frequency": binding.source_frequency,
            "unit_multiplier": str(binding.unit_multiplier) if binding.unit_multiplier is not None else None}


def _source_id(binding, metadata):
    if binding.provider != "TREASURY_MTS":
        return binding.provider + ":" + dict(metadata)["SERIES_NAME"]
    selector = json.dumps(_binding_view(binding), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return binding.provider + ":" + binding.table_path + ":" + hashlib.sha256(selector).hexdigest()


def _observation_id(obs):
    body = {"source_id": obs.source_id, "period": obs.observation_period, "value": str(obs.value),
            "binding": _binding_view(obs.binding), "metadata": obs.source_metadata,
            "response_sha256": obs.source_response_sha256, "captured": utc(obs.ingested_at).isoformat(),
            "source_url": obs.source_url, "synthetic": obs.synthetic}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _observation(period, value, metadata, receipt, binding):
    obs = RemainingObservation("", _source_id(binding, metadata), binding.axis, binding.provider, period, value,
                               binding.unit, binding.frequency, binding.seasonal_adjustment, binding.basis,
                               binding.source_frequency, binding.unit_multiplier, receipt.acquired_at,
                               receipt.acquired_at, receipt.acquired_at, receipt.response_sha256, receipt.synthetic,
                               receipt.source_url, receipt.rights_status, binding, metadata)
    return replace(obs, observation_id=_observation_id(obs))


def _finish(rows, receipt, binding):
    unique = {}
    for period, raw, metadata in rows:
        if not _period_valid(period, binding.frequency):
            return _failed("SCHEMA_MISMATCH", receipt)
        value, error = _number(raw)
        if error:
            return _failed(error, receipt)
        previous = unique.get(period)
        if previous is not None and (previous[0] != value or previous[1] != metadata):
            return _failed("CONFLICTING_DUPLICATE", receipt)
        if previous is None or str(value) < str(previous[0]):
            unique[period] = (value, metadata)
    if not unique:
        return _failed("MISSING_SOURCE", receipt)
    return _result((_observation(period, *unique[period], receipt, binding) for period in sorted(unique)), synthetic=receipt.synthetic)


def _fed_metadata_valid(metadata, binding):
    values = dict(metadata)
    if (any(not nonempty(values.get(key)) for key in ("SERIES_NAME", "FREQ", "UNIT", "UNIT_MULT") + _BASIS_FIELDS[binding.provider])
            or values.get("DATASET_ID") != binding.dataset_id
            or values["FREQ"] != binding.source_frequency or values["UNIT"] != binding.unit
            or any(values.get(key) != value for key, value in binding.field_filters)
            or (binding.source_id is not None and values["SERIES_NAME"] != binding.source_id)):
        return False
    multiplier, error = _number(values["UNIT_MULT"])
    if error or multiplier != binding.unit_multiplier:
        return False
    if binding.provider == "FED_H8" and values.get("SA") != binding.seasonal_adjustment:
        return False
    if "CURRENCY" in values and "CURRENCY" not in dict(binding.field_filters):
        return False
    return True


def parse_fed_sdmx(payload: bytes, receipt: GovernmentReceipt, binding: RemainingSeriesBinding) -> RemainingParseResult:
    if not _binding_valid(binding) or binding.provider not in _FED_RELEASES:
        return _failed("UNADOPTED_INPUT_SELECTION", receipt)
    error = _receipt_error(payload, receipt, binding)
    if error:
        return _failed(error, receipt)
    probe = payload.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        return _failed("UNSAFE_XML", receipt)
    try:
        root = ElementTree.fromstring(payload)
    except (ElementTree.ParseError, ValueError, LookupError, RecursionError):
        return _failed("SCHEMA_MISMATCH", receipt)
    common = "{" + _FED_COMMON + "}"
    release = _FED_RELEASES[binding.provider]
    series_tag = "{http://www.federalreserve.gov/structure/compact/" + release + "_" + release + "}Series"
    if root.tag != common + "DataSet" or root.get("id") != binding.dataset_id:
        return _failed("SCHEMA_MISMATCH", receipt)
    rows = []
    for series in root:
        if series.tag != series_tag or any("}" in key for key in series.attrib):
            return _failed("SCHEMA_MISMATCH", receipt)
        attrs = dict(series.attrib)
        if binding.source_id is not None and attrs.get("SERIES_NAME") != binding.source_id:
            continue
        if any(attrs.get(key) != value for key, value in binding.field_filters):
            continue
        if "DATASET_ID" in attrs:
            return _failed("SCHEMA_MISMATCH", receipt)
        metadata = tuple(sorted({**attrs, "DATASET_ID": root.get("id")}.items()))
        if not _fed_metadata_valid(metadata, binding):
            return _failed("SCHEMA_MISMATCH", receipt)
        for obs in series:
            if (obs.tag != common + "Obs" or list(obs)
                    or any(key not in ("TIME_PERIOD", "OBS_VALUE", "OBS_STATUS") for key in obs.attrib)):
                return _failed("SCHEMA_MISMATCH", receipt)
            obs_metadata = metadata
            if "OBS_STATUS" in obs.attrib:
                if "OBS_STATUS" in attrs or not nonempty(obs.get("OBS_STATUS")):
                    return _failed("SCHEMA_MISMATCH", receipt)
                obs_metadata = tuple(sorted(metadata + (("OBS_STATUS", obs.get("OBS_STATUS")),)))
            rows.append((obs.get("TIME_PERIOD"), obs.get("OBS_VALUE"), obs_metadata))
    return _finish(rows, receipt, binding)


def _unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("nonfinite JSON")


def parse_treasury_mts(payload: bytes, receipt: GovernmentReceipt, binding: RemainingSeriesBinding) -> RemainingParseResult:
    if not _binding_valid(binding, "TREASURY_MTS"):
        return _failed("UNADOPTED_INPUT_SELECTION", receipt)
    error = _receipt_error(payload, receipt, binding)
    if error:
        return _failed(error, receipt)
    try:
        obj = json.loads(payload, object_pairs_hook=_unique_json, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        return _failed("SCHEMA_MISMATCH", receipt)
    if type(obj) is not dict or type(obj.get("data")) is not list or type(obj.get("meta")) is not dict:
        return _failed("SCHEMA_MISMATCH", receipt)
    meta = obj["meta"]
    if "total-pages" not in meta or "total_pages" in meta:
        return _failed("INCOMPLETE_PAYLOAD", receipt)
    pages = meta["total-pages"]
    if type(pages) is str and re.fullmatch(r"[0-9]{1,9}", pages):
        pages = int(pages)
    if type(pages) is not int or pages < 1:
        return _failed("SCHEMA_MISMATCH", receipt)
    if pages > 1:
        return _failed("INCOMPLETE_PAYLOAD", receipt)
    for key in ("count", "total-count"):
        if key in meta:
            count = meta[key]
            if type(count) is str and re.fullmatch(r"[0-9]{1,9}", count):
                count = int(count)
            if type(count) is not int or count < 0:
                return _failed("SCHEMA_MISMATCH", receipt)
            if count != len(obj["data"]):
                return _failed("INCOMPLETE_PAYLOAD", receipt)
    if "links" in obj:
        if type(obj["links"]) is not dict:
            return _failed("SCHEMA_MISMATCH", receipt)
        if obj["links"].get("next") is not None:
            return _failed("INCOMPLETE_PAYLOAD", receipt)
    for key in ("labels", "dataTypes", "dataFormats"):
        if key in meta and type(meta[key]) is not dict:
            return _failed("SCHEMA_MISMATCH", receipt)
    rows = []
    for row in obj["data"]:
        if type(row) is not dict:
            return _failed("SCHEMA_MISMATCH", receipt)
        if any(row.get(key) != value for key, value in binding.field_filters):
            continue
        metadata = dict(binding.field_filters)
        if "record_date" in row:
            if not nonempty(row["record_date"]):
                return _failed("SCHEMA_MISMATCH", receipt)
            metadata["record_date"] = row["record_date"]
        for key, output in (("labels", "label"), ("dataTypes", "data_type"), ("dataFormats", "data_format")):
            value = meta.get(key, {}).get(binding.observation_field)
            if value is not None:
                if not nonempty(value):
                    return _failed("SCHEMA_MISMATCH", receipt)
                metadata[output] = value
        rows.append((row.get(binding.period_field), row.get(binding.observation_field), tuple(sorted(metadata.items()))))
    return _finish(rows, receipt, binding)


def _observation_error(obs):
    if not isinstance(obs, RemainingObservation):
        return "INVALID_RECEIPT"
    if not _binding_valid(obs.binding):
        return "UNADOPTED_INPUT_SELECTION"
    binding = obs.binding
    if any(type(getattr(obs, key)) is not str for key in
           ("provider", "source_id", "axis", "unit", "frequency", "seasonal_adjustment", "basis",
            "observation_period", "source_url", "rights_status", "source_response_sha256", "observation_id")):
        return "INVALID_RECEIPT"
    if (obs.provider != binding.provider or not _source_url_valid(obs.source_url, binding)
            or not valid_hash(obs.source_response_sha256) or not valid_hash(obs.observation_id)
            or type(obs.synthetic) is not bool or obs.rights_status not in ("CLEARED_SCOPE", "UNCONFIRMED")):
        return "INVALID_RECEIPT"
    if obs.rights_status != "CLEARED_SCOPE":
        return "RIGHTS_UNCONFIRMED"
    if not all(aware(t) for t in (obs.available_at, obs.vintage_at, obs.ingested_at)):
        return "INVALID_TIMESTAMP"
    if not utc(obs.available_at) == utc(obs.vintage_at) == utc(obs.ingested_at):
        return "INVALID_TIME_ORDER"
    if (binding.provider == "TREASURY_MTS" and obs.unit_multiplier is not None) or (
            binding.provider != "TREASURY_MTS" and (type(obs.unit_multiplier) is not Decimal or not obs.unit_multiplier.is_finite())):
        return "SCHEMA_MISMATCH"
    if (any(getattr(obs, key) != getattr(binding, key) for key in
            ("axis", "unit", "frequency", "seasonal_adjustment", "basis", "source_frequency", "unit_multiplier"))
            or not _period_valid(obs.observation_period, obs.frequency) or not _pairs(obs.source_metadata)
            or obs.availability_basis != "OBSERVED_CAPTURE_UPPER_BOUND" or obs.vintage_kind != "OBSERVED_CAPTURE"):
        return "SCHEMA_MISMATCH"
    if type(obs.value) is not Decimal or not obs.value.is_finite():
        return "INVALID_VALUE"
    metadata = dict(obs.source_metadata)
    if binding.provider == "TREASURY_MTS":
        if any(metadata.get(key) != value for key, value in binding.field_filters):
            return "SCHEMA_MISMATCH"
    elif not _fed_metadata_valid(obs.source_metadata, binding):
        return "SCHEMA_MISMATCH"
    if obs.source_id != _source_id(binding, obs.source_metadata) or obs.observation_id != _observation_id(obs):
        return "INVALID_RECEIPT"
    return None


def _result_valid(result):
    return (isinstance(result, RemainingParseResult) and type(result.state) is str
            and result.state in ("RAW_EVIDENCE", "NOT_AVAILABLE") and type(result.observations) is tuple
            and (result.state == "RAW_EVIDENCE") == bool(result.observations) and type(result.synthetic) is bool
            and type(result.reason_codes) is tuple and all(type(r) is str and r in REASON_CODES for r in result.reason_codes))


def _collision_view(obs):
    # Compare strings only: malformed Decimal scalars (including signaling NaN)
    # cannot raise during the pre-validation collision check.
    times = tuple((key, utc(getattr(obs, key)).isoformat() if aware(getattr(obs, key)) else repr(getattr(obs, key)))
                  for key in ("available_at", "vintage_at", "ingested_at"))
    binding = json.dumps(_binding_view(obs.binding), sort_keys=True) if _binding_valid(obs.binding) else repr(obs.binding)
    scalars = tuple(repr(getattr(obs, key)) for key in (
        "value", "source_metadata", "provider", "axis", "source_id", "unit", "frequency",
        "seasonal_adjustment", "basis", "unit_multiplier", "source_frequency", "source_response_sha256",
        "synthetic", "source_url", "rights_status", "observation_period", "availability_basis", "vintage_kind"))
    return times, binding, scalars


def _capture_content(obs):
    return (obs.value, obs.unit, obs.frequency, obs.seasonal_adjustment, obs.basis, obs.source_frequency,
            obs.unit_multiplier, obs.source_metadata, json.dumps(_binding_view(obs.binding), sort_keys=True), obs.provider, obs.axis)


def select_remaining_observed(results: tuple[RemainingParseResult, ...], as_of: datetime) -> RemainingParseResult:
    """Select known captures only; this never proves pre-capture vintage history."""
    if not aware(as_of):
        return _result(reasons=("INVALID_TIMESTAMP",))
    if type(results) is not tuple:
        return _result(reasons=("INVALID_REQUEST",))
    if not all(_result_valid(result) for result in results):
        return _result(reasons=("INVALID_RESULT",))
    flags = {result.synthetic for result in results}
    if len(flags) > 1:
        return _result(reasons=("MIXED_SYNTHETIC_INPUT",))
    synthetic = next(iter(flags)) if flags else True
    observations = tuple(obs for result in results for obs in result.observations)
    if any(isinstance(obs, RemainingObservation) and type(obs.synthetic) is bool and obs.synthetic != synthetic for obs in observations):
        return _result(reasons=("MIXED_SYNTHETIC_INPUT",), synthetic=synthetic)
    seen = {}
    for obs in observations:
        if isinstance(obs, RemainingObservation) and valid_hash(obs.observation_id):
            view = _collision_view(obs)
            if obs.observation_id in seen and seen[obs.observation_id] != view:
                return _result(reasons=("OBSERVATION_ID_COLLISION",), synthetic=synthetic)
            seen[obs.observation_id] = view
    reasons = [reason for result in results for reason in result.reason_codes]
    valid, blocked = [], set()
    for obs in observations:
        error = _observation_error(obs)
        if error:
            reasons.append(error)
            if not isinstance(obs, RemainingObservation) or type(obs.source_id) is not str:
                return _result(reasons=(error,), synthetic=synthetic)
            blocked.add(obs.source_id)
        else:
            valid.append(obs)
    captures = {}
    for obs in valid:
        if utc(obs.available_at) > utc(as_of):
            reasons.append("AVAILABLE_AFTER_AS_OF")
            continue
        key = (obs.source_id, obs.observation_period, utc(obs.available_at))
        previous = captures.get(key)
        if previous is not None and _capture_content(previous) != _capture_content(obs):
            blocked.add(obs.source_id)
            reasons.append("CONFLICTING_VINTAGE")
        elif previous is None or obs.observation_id < previous.observation_id:
            captures[key] = obs
    selected = {}
    for obs in captures.values():
        if obs.source_id in blocked:
            continue
        key = (obs.source_id, obs.observation_period)
        if key not in selected or utc(obs.available_at) > utc(selected[key].available_at):
            selected[key] = obs
    output = sorted(selected.values(), key=lambda obs: (tuple(PROVIDER_AXES).index(obs.provider), obs.source_id, obs.observation_period))
    return _result(output, reasons, synthetic=synthetic)
