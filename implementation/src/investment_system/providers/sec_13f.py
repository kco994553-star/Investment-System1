"""Parse supplied SEC 13F information tables and compare reported quantities.

Cover/header binding, completeness and canonical amendment lineage are explicit
caller attestations. This module does not fetch or verify a separate cover file,
resolve issuers/tickers, infer trades, transform units, or publish holdings.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import re
from types import MappingProxyType
from xml.etree import ElementTree as ET


NAMESPACE = "http://www.sec.gov/edgar/document/thirteenf/informationtable"
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
ROLE = "REPORTED_QUANTITY_ONLY"
EXIT_LABEL = "공개 보고에서 소멸/수량0, 실제 전량매도 확정 아님"
_QENDS = {(3, 31), (6, 30), (9, 30), (12, 31)}
_INTEGER = re.compile(r"[0-9]{1,16}")
_REFERENCE = re.compile(r"[0-9]{1,3}")
_CUSIP = re.compile(r"[A-Za-z0-9]{9}")
_FIGI = re.compile(r"[A-Za-z0-9]{12}")
_HASH = re.compile(r"[0-9a-f]{64}")
_ISSUER = re.compile(r"[A-Za-z0-9\s!\\#$(),.:;`=@'\-{}|/&]+", re.ASCII)
_SCHEMA_LOCATION = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
_ROW_ORDER = ("nameOfIssuer", "titleOfClass", "cusip", "figi", "value", "shrsOrPrnAmt",
              "putCall", "investmentDiscretion", "otherManager", "votingAuthority")


@dataclass(frozen=True)
class FilingMetadata:
    """Supplied cover metadata; no value basis or manager roster is inferred."""

    manager_cik: str | None = field(default=None, repr=False)
    accession: str | None = field(default=None, repr=False)
    quarter_end: date | None = field(default=None, repr=False)
    filing_date: date | None = field(default=None, repr=False)
    acquired_at: datetime | None = field(default=None, repr=False)
    value_basis: str | None = field(default=None, repr=False)
    report_type: str | None = field(default=None, repr=False)
    amendment_type: str | None = field(default=None, repr=False)
    confidential_omitted: bool | None = field(default=None, repr=False)
    entry_total: int | None = field(default=None, repr=False)
    value_total: int | None = field(default=None, repr=False)
    complete: bool = field(default=False, repr=False)
    lineage_resolved: bool = field(default=False, repr=False)
    cover_binding_confirmed: bool = field(default=False, repr=False)
    other_manager_ciks: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}), repr=False)
    source_response_sha256: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if isinstance(self.other_manager_ciks, Mapping):
            object.__setattr__(self, "other_manager_ciks", MappingProxyType(dict(self.other_manager_ciks)))


@dataclass(frozen=True, repr=False)
class SecurityKey:
    cusip: str
    title_of_class: str
    quantity_type: str
    put_call: str | None
    investment_discretion: str
    other_manager_ciks: tuple[str, ...] | None


@dataclass(frozen=True, repr=False)
class RawHolding:
    issuer_name: str
    title_of_class: str
    cusip: str
    figi: str | None
    quantity: int
    quantity_type: str
    value: int
    value_basis: str
    put_call: str | None
    investment_discretion: str
    other_manager_refs: tuple[str, ...]
    other_manager_ciks: tuple[str, ...] | None
    voting_authority: tuple[int, int, int]
    raw_fields: Mapping[str, str]

    def __post_init__(self):
        object.__setattr__(self, "raw_fields", MappingProxyType(dict(self.raw_fields)))


@dataclass(frozen=True, repr=False)
class ReportedHolding:
    key: SecurityKey
    quantity: int
    value: int
    value_basis: str
    raw_rows: tuple[RawHolding, ...]


@dataclass(frozen=True)
class ParseResult:
    status: str
    reasons: tuple[str, ...] = ()
    role: str = field(default=ROLE, init=False)
    payload_sha256: str | None = None
    comparison_eligible: bool = False
    raw_rows: tuple[RawHolding, ...] = field(default=(), repr=False)
    holdings: tuple[ReportedHolding, ...] = field(default=(), repr=False)
    metadata: FilingMetadata | None = field(default=None, repr=False)
    as_of: datetime | None = field(default=None, repr=False)


@dataclass(frozen=True, repr=False)
class QuantityChange:
    key: SecurityKey
    kind: str
    previous_quantity: int
    current_quantity: int
    delta_quantity: int
    label: str
    role: str = field(default=ROLE, init=False)


@dataclass(frozen=True)
class ComparisonResult:
    status: str
    reasons: tuple[str, ...] = ()
    role: str = field(default=ROLE, init=False)
    changes: tuple[QuantityChange, ...] = field(default=(), repr=False)


def _cik(value: object) -> str | None:
    if type(value) is str and re.fullmatch(r"[0-9]{1,10}", value) and int(value) > 0:
        return value.zfill(10)
    return None


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _reference(value: object) -> bool:
    return type(value) is str and _REFERENCE.fullmatch(value) is not None and int(value) >= 1


def _metadata_error(metadata: object, as_of: object) -> str | None:
    if not isinstance(metadata, FilingMetadata):
        return "INVALID_METADATA"
    if not _aware(as_of) or not _aware(metadata.acquired_at):
        return "INVALID_TIMESTAMP"
    if (_cik(metadata.manager_cik) is None or type(metadata.accession) is not str
            or re.fullmatch(r"[0-9]{10}-[0-9]{2}-[0-9]{6}", metadata.accession) is None
            or type(metadata.quarter_end) is not date or type(metadata.filing_date) is not date
            or (metadata.quarter_end.month, metadata.quarter_end.day) not in _QENDS
            or metadata.filing_date < metadata.quarter_end
            or metadata.value_basis not in ("USD_DOLLARS", "USD_THOUSANDS")
            or metadata.report_type not in ("HOLDINGS", "NOTICE", "COMBINATION")
            or metadata.amendment_type not in (None, "RESTATEMENT", "NEW_HOLDINGS")
            or any(type(flag) is not bool for flag in
                   (metadata.complete, metadata.lineage_resolved, metadata.cover_binding_confirmed))
            or (metadata.confidential_omitted is not None and type(metadata.confidential_omitted) is not bool)
            or (metadata.entry_total is not None and not _nonnegative_int(metadata.entry_total))
            or (metadata.value_total is not None and not _nonnegative_int(metadata.value_total))
            or not isinstance(metadata.other_manager_ciks, Mapping)):
        return "INVALID_METADATA"
    for reference, manager in metadata.other_manager_ciks.items():
        if not _reference(reference) or _cik(manager) is None:
            return "INVALID_METADATA"
    if (metadata.source_response_sha256 is not None
            and (type(metadata.source_response_sha256) is not str
                 or _HASH.fullmatch(metadata.source_response_sha256) is None)):
        return "INVALID_SOURCE_DIGEST"
    acquired = metadata.acquired_at.astimezone(timezone.utc)
    cutoff = as_of.astimezone(timezone.utc)
    if acquired > cutoff or metadata.filing_date > cutoff.date():
        return "NOT_AVAILABLE_AS_OF"
    if acquired.date() < metadata.filing_date:
        return "INVALID_TIMESTAMP"
    return None


def _unavailable(reason: str, *, digest=None) -> ParseResult:
    return ParseResult("NOT_AVAILABLE", (reason,), payload_sha256=digest)


class _InvalidXML(ValueError):
    pass


def _xml_strip(raw: str) -> str:
    return raw.strip(" \t\r\n")


def _fields(element, required: tuple[str, ...], optional: tuple[str, ...] = (), *, order=None):
    if element.attrib or _xml_strip(element.text or ""):
        raise _InvalidXML
    fields = {}
    expected_order, previous_position = order or required + optional, -1
    for child in element:
        if not isinstance(child.tag, str) or not child.tag.startswith("{" + NAMESPACE + "}"):
            raise _InvalidXML
        name = child.tag[len(NAMESPACE) + 2:]
        if name not in required + optional or name in fields or _xml_strip(child.tail or ""):
            raise _InvalidXML
        position = expected_order.index(name)
        if position <= previous_position:
            raise _InvalidXML
        previous_position = position
        fields[name] = child
    if any(name not in fields for name in required):
        raise _InvalidXML
    return fields


def _text(element) -> str:
    if element.attrib or len(element):
        raise _InvalidXML
    return element.text or ""


def _integer(raw: str) -> int:
    if _INTEGER.fullmatch(_xml_strip(raw)) is None:
        raise _InvalidXML
    return int(_xml_strip(raw))


def _parse_row(element, metadata: FilingMetadata) -> RawHolding:
    parts = _fields(element, ("nameOfIssuer", "titleOfClass", "cusip", "value", "shrsOrPrnAmt",
                              "investmentDiscretion", "votingAuthority"),
                    ("figi", "putCall", "otherManager"), order=_ROW_ORDER)
    shares = _fields(parts.pop("shrsOrPrnAmt"), ("sshPrnamt", "sshPrnamtType"))
    votes = _fields(parts.pop("votingAuthority"), ("Sole", "Shared", "None"))
    raw = {name: _text(element) for name, element in (parts | shares | votes).items()}
    clean = {name: _xml_strip(text) for name, text in raw.items()}
    clean["titleOfClass"] = re.sub(r"[ \t\r\n]+", " ", clean["titleOfClass"])
    if (not clean["nameOfIssuer"] or not clean["titleOfClass"]
            or len(raw["nameOfIssuer"]) > 150 or _ISSUER.fullmatch(raw["nameOfIssuer"]) is None
            or len(clean["titleOfClass"]) > 150
            or _CUSIP.fullmatch(clean["cusip"]) is None
            or ("figi" in clean and _FIGI.fullmatch(clean["figi"]) is None)
            or clean["sshPrnamtType"] not in ("SH", "PRN")
            or clean.get("putCall") not in (None, "Put", "Call")
            or clean["investmentDiscretion"] not in ("SOLE", "DFND", "OTR")):
        raise _InvalidXML
    references = ()
    actual_managers: tuple[str, ...] | None = ()
    if "otherManager" in clean:
        references = tuple(_xml_strip(part) for part in clean["otherManager"].split(","))
        if len(raw["otherManager"]) > 100 or not references or any(not _reference(part) for part in references):
            raise _InvalidXML
        actual = [_cik(metadata.other_manager_ciks.get(reference)) for reference in references]
        actual_managers = tuple(sorted(set(actual))) if all(actual) else None
    return RawHolding(clean["nameOfIssuer"], clean["titleOfClass"], clean["cusip"], clean.get("figi"),
                      _integer(raw["sshPrnamt"]), clean["sshPrnamtType"], _integer(raw["value"]),
                      metadata.value_basis, clean.get("putCall"), clean["investmentDiscretion"],
                      references, actual_managers,
                      tuple(_integer(raw[name]) for name in ("Sole", "Shared", "None")), raw)


def _key(row: RawHolding) -> SecurityKey:
    return SecurityKey(row.cusip, row.title_of_class, row.quantity_type, row.put_call,
                       row.investment_discretion, row.other_manager_ciks)


def _key_order(key: SecurityKey):
    return (key.cusip, key.title_of_class, key.quantity_type, key.put_call or "",
            key.investment_discretion, key.other_manager_ciks or ())


def _aggregate(rows: tuple[RawHolding, ...]) -> tuple[ReportedHolding, ...]:
    grouped, unresolved = {}, []
    for row in rows:
        key = _key(row)
        if row.other_manager_ciks is None:
            unresolved.append(ReportedHolding(key, row.quantity, row.value, row.value_basis, (row,)))
        else:
            grouped.setdefault(key, []).append(row)
    holdings = [ReportedHolding(key, sum(row.quantity for row in group),
                                sum(row.value for row in group), group[0].value_basis, tuple(group))
                for key, group in grouped.items()]
    return tuple(sorted(holdings + unresolved, key=lambda holding: _key_order(holding.key)))


def _comparison_reasons(metadata: FilingMetadata, rows: tuple[RawHolding, ...]) -> tuple[str, ...]:
    reasons = []
    if not metadata.cover_binding_confirmed:
        reasons.append("COVER_BINDING_UNCONFIRMED")
    if not metadata.complete:
        reasons.append("INCOMPLETE_CAPTURE")
    if not metadata.lineage_resolved:
        reasons.append("UNRESOLVED_QUARTER_LINEAGE")
    if metadata.report_type != "HOLDINGS":
        reasons.append("NON_HOLDINGS_REPORT")
    if metadata.confidential_omitted is not False:
        reasons.append("CONFIDENTIAL_OMISSIONS_UNRESOLVED")
    if metadata.amendment_type == "NEW_HOLDINGS":
        reasons.append("ADDITIONAL_HOLDINGS_AMENDMENT")
    if metadata.entry_total is None:
        reasons.append("ENTRY_TOTAL_UNCONFIRMED")
    elif metadata.entry_total != len(rows):
        reasons.append("ENTRY_TOTAL_MISMATCH")
    if metadata.value_total is not None and metadata.value_total != sum(row.value for row in rows):
        reasons.append("VALUE_TOTAL_MISMATCH")
    if any(row.other_manager_ciks is None for row in rows):
        reasons.append("OTHER_MANAGER_ATTRIBUTION_UNRESOLVED")
    return tuple(reasons)


def parse_information_table(payload: bytes, metadata: FilingMetadata, *,
                            selected_manager_ciks: tuple[str, ...] = (), as_of: datetime) -> ParseResult:
    """No selection returns NA; valid partial tables retain private rows.

    One invalid row invalidates the whole capture, preventing skipped rows from
    becoming apparent exits. A supplied value total is in the explicit value basis.
    """
    error = _metadata_error(metadata, as_of)
    if error:
        return _unavailable(error)
    if type(selected_manager_ciks) not in (tuple, list):
        return _unavailable("INVALID_MANAGER_SELECTION")
    selected = tuple(_cik(manager) for manager in selected_manager_ciks)
    if any(manager is None for manager in selected):
        return _unavailable("INVALID_MANAGER_SELECTION")
    if _cik(metadata.manager_cik) not in selected:
        return _unavailable("MANAGER_NOT_SELECTED")
    if type(payload) is not bytes:
        return _unavailable("INVALID_PAYLOAD")
    if len(payload) > MAX_PAYLOAD_BYTES:
        return _unavailable("PAYLOAD_TOO_LARGE")
    digest = hashlib.sha256(payload).hexdigest()
    if metadata.source_response_sha256 is not None and metadata.source_response_sha256 != digest:
        return _unavailable("SOURCE_DIGEST_MISMATCH", digest=digest)
    upper = payload.replace(b"\x00", b"").upper()
    if b"\x00" in payload or b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return _unavailable("DISALLOWED_XML", digest=digest)
    try:
        root = ET.fromstring(payload)
        # A schemaLocation is only an ignored hint; no schema/resource is fetched.
        if (root.tag != "{" + NAMESPACE + "}informationTable"
                or set(root.attrib) - {_SCHEMA_LOCATION} or _xml_strip(root.text or "")):
            raise _InvalidXML
        rows = []
        for child in root:
            if child.tag != "{" + NAMESPACE + "}infoTable" or _xml_strip(child.tail or ""):
                raise _InvalidXML
            rows.append(_parse_row(child, metadata))
        if not rows:
            raise _InvalidXML
    except (ET.ParseError, _InvalidXML, ValueError, RecursionError):
        return _unavailable("INVALID_INFORMATION_TABLE", digest=digest)
    raw_rows = tuple(rows)
    reasons = _comparison_reasons(metadata, raw_rows)
    return ParseResult("PARTIAL" if reasons else "AVAILABLE", reasons, payload_sha256=digest,
                       comparison_eligible=not reasons, raw_rows=raw_rows, holdings=_aggregate(raw_rows),
                       metadata=metadata, as_of=as_of)


def _quarter_index(quarter: date) -> int:
    return quarter.year * 4 + quarter.month // 3 - 1


def _eligible_capture(result: ParseResult) -> bool:
    """Recheck caller-constructed/replaced records without an authenticity claim."""
    if (result.status != "AVAILABLE" or result.comparison_eligible is not True
            or _metadata_error(result.metadata, result.as_of) is not None
            or type(result.payload_sha256) is not str or _HASH.fullmatch(result.payload_sha256) is None
            or type(result.raw_rows) is not tuple or not result.raw_rows
            or type(result.holdings) is not tuple or not result.holdings
            or any(type(row) is not RawHolding for row in result.raw_rows)
            or any(type(holding) is not ReportedHolding or type(holding.key) is not SecurityKey
                   or type(holding.raw_rows) is not tuple for holding in result.holdings)):
        return False
    if any(not _nonnegative_int(row.quantity) or not _nonnegative_int(row.value)
           or row.value_basis != result.metadata.value_basis
           or type(row.other_manager_refs) is not tuple
           or type(row.other_manager_ciks) is not tuple for row in result.raw_rows):
        return False
    try:
        return (not _comparison_reasons(result.metadata, result.raw_rows)
                and result.holdings == _aggregate(result.raw_rows))
    except (TypeError, ValueError, AttributeError):
        return False


def compare_quarters(previous: ParseResult, current: ParseResult) -> ComparisonResult:
    """Compare consecutive eligible quarters for the same verified manager/cutoff.

    EXIT includes de minimis omission uncertainty (Form 13F Instruction 9).
    Values, splits and actual transaction dates do not enter this calculation.
    """
    if not isinstance(previous, ParseResult) or not isinstance(current, ParseResult):
        return ComparisonResult("NOT_AVAILABLE", ("INVALID_CAPTURE",))
    if not _eligible_capture(previous) or not _eligible_capture(current):
        return ComparisonResult("NOT_AVAILABLE", ("INELIGIBLE_CAPTURE",))
    if _cik(previous.metadata.manager_cik) != _cik(current.metadata.manager_cik):
        return ComparisonResult("NOT_AVAILABLE", ("MANAGER_MISMATCH",))
    if previous.as_of.astimezone(timezone.utc) != current.as_of.astimezone(timezone.utc):
        return ComparisonResult("NOT_AVAILABLE", ("AS_OF_MISMATCH",))
    if _quarter_index(current.metadata.quarter_end) - _quarter_index(previous.metadata.quarter_end) != 1:
        return ComparisonResult("NOT_AVAILABLE", ("NONCONSECUTIVE_QUARTERS",))
    old = {holding.key: holding.quantity for holding in previous.holdings}
    new = {holding.key: holding.quantity for holding in current.holdings}
    old_basis, new_basis = {}, {}
    for key in old:
        old_basis.setdefault(key.cusip, set()).add(key)
    for key in new:
        new_basis.setdefault(key.cusip, set()).add(key)
    if any(old_basis[cusip] != new_basis[cusip] for cusip in old_basis.keys() & new_basis.keys()):
        return ComparisonResult("NOT_AVAILABLE", ("INCOMPATIBLE_SECURITY_BASIS",))
    labels = {"NEW": "공개 보고 수량 신규", "ADD": "공개 보고 수량 증가",
              "REDUCE": "공개 보고 수량 감소", "EXIT": EXIT_LABEL}
    changes = []
    for key in sorted(old.keys() | new.keys(), key=_key_order):
        before, after = old.get(key, 0), new.get(key, 0)
        if before == after:
            continue
        kind = "NEW" if before == 0 else "EXIT" if after == 0 else "ADD" if after > before else "REDUCE"
        changes.append(QuantityChange(key, kind, before, after, after - before, labels[kind]))
    return ComparisonResult("AVAILABLE", changes=tuple(changes))
