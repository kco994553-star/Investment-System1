"""SEC EDGAR 8-K Atom adapter. Primary disclosure only.

Not a general or journalistic news provider. Parses caller-supplied Atom
bytes. Does not copy exhibit bodies or the SEC summary HTML into the public
record. Does not infer language, issuer identity, sentiment, or event kind.

``SEC_USER_AGENT`` / ``INVESTMENT_SYSTEM_SEC_UA`` is required only for the
network fetch. It is not hard-coded.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from xml.etree import ElementTree

from ..model import SourceKind
from .contract import LANGUAGE_NOT_PROVIDED, canonical_sha256, canonicalize_url, sha256_hex
from .errors import IngestError
from .normalize import NormalizedNewsItem
from .pipeline import ingest
from .producer import unavailable_news_snapshot
from .raw import _LANGUAGE
from .rig_input import to_rig_input

ADAPTER_ID = "SEC_PRIMARY_DISCLOSURE"
ADAPTER_VERSION = "v1"
SOURCE = "sec.edgar.atom"
ATOM = "http://www.w3.org/2005/Atom"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_FORMS = frozenset({"8-K", "8-K/A"})
_ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ITEM = re.compile(r"Item\s+(\d{1,2}\.\d{2})\s*:\s*(.+)")
_CIK_TITLE = re.compile(r"\((\d{1,10})\)\s*\((?:Filer|Issuer|Subject|Reporting)\)\s*$")
_CIK_URL = re.compile(r"/Archives/edgar/data/(\d+)/", re.IGNORECASE)
_ACC_URL = re.compile(r"/(\d{10}-\d{2}-\d{6})-index\.htm(?:l)?$", re.IGNORECASE)


@dataclass(frozen=True)
class DisclosureBatch:
    snapshot: dict
    raw_by_hash: dict[str, bytes]
    feed_bytes: bytes


class ExplicitIdentityMap:
    """company_id ↔ CIK ↔ issuer_id. Equality only. Not a name or ticker index."""

    def __init__(self) -> None:
        self._companies: dict[str, set[str]] = {}
        self._issuers: dict[str, str] = {}

    def add(self, cik: str, company_id: str, issuer_id: str | None = None) -> None:
        key = _cik10(cik)
        if not isinstance(company_id, str) or not company_id.strip():
            raise IngestError("MALFORMED", "company_id is required")
        cid = company_id.strip()
        self._companies.setdefault(key, set()).add(cid)
        if issuer_id is None:
            return
        if not isinstance(issuer_id, str) or not issuer_id.strip():
            raise IngestError("MALFORMED", "issuer_id must be a non-empty string when set")
        previous = self._issuers.get(cid)
        if previous is not None and previous != issuer_id.strip():
            raise IngestError("CONFLICT", "company_id already has a different issuer_id")
        self._issuers[cid] = issuer_id.strip()

    def resolve(self, cik: str) -> tuple[str, str | None, str | None]:
        owners = self._companies.get(_cik10(cik), set())
        if not owners:
            return "UNKNOWN", None, None
        if len(owners) > 1:
            return "AMBIGUOUS", None, None
        company_id = next(iter(owners))
        return "RESOLVED", company_id, self._issuers.get(company_id)


def identity_from_registry(document: dict) -> ExplicitIdentityMap:
    """Read explicit CIK and company_id pairs. Does not index names or tickers."""
    if not isinstance(document, dict):
        raise IngestError("MALFORMED", "entity registry must be an object")
    if document.get("kind") != "ENTITY_SEARCH_METADATA_REGISTRY" or document.get("schema_version") != 1:
        raise IngestError("MALFORMED", "entity registry is not schema v1")
    records = document.get("records")
    if not isinstance(records, dict):
        raise IngestError("MALFORMED", "entity registry has no records")
    mapping = ExplicitIdentityMap()
    for key, record in records.items():
        if not isinstance(record, dict) or record.get("company_id") != key:
            raise IngestError("MALFORMED", "entity registry company_id does not match its key")
        cik = record.get("cik")
        if not isinstance(cik, str) or not cik.strip():
            continue
        issuer = record.get("issuer_id")
        if issuer is not None and not isinstance(issuer, str):
            raise IngestError("MALFORMED", "issuer_id must be a string when present")
        mapping.add(cik, key, issuer.strip() if isinstance(issuer, str) and issuer.strip() else None)
    return mapping


def sec_user_agent(explicit: str | None = None) -> str:
    """Approved configuration only. Does not invent a contact string."""
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise IngestError("SEC_USER_AGENT_REQUIRED", "SEC fair-access User-Agent is empty")
        return explicit.strip()
    for name in ("SEC_USER_AGENT", "INVESTMENT_SYSTEM_SEC_UA"):
        value = os.environ.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise IngestError(
        "SEC_USER_AGENT_REQUIRED",
        "set SEC_USER_AGENT or INVESTMENT_SYSTEM_SEC_UA; this module does not hard-code a contact",
    )


def fetch_sec_atom(url: str, *, user_agent: str | None = None, timeout: float = 12.0) -> bytes:
    """Network boundary. Parsing supplied bytes does not call this."""
    agent = sec_user_agent(user_agent)
    if not isinstance(url, str) or not (
        url.startswith("https://www.sec.gov/") or url.startswith("https://data.sec.gov/")
    ):
        raise IngestError("MALFORMED", "SEC fetch is limited to www.sec.gov and data.sec.gov")
    from urllib.request import Request, urlopen

    request = Request(url, headers={"User-Agent": agent, "Accept": "application/atom+xml, application/xml"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def general_news_snapshot(*, generated_at: datetime, requested_as_of: datetime) -> dict:
    """General and journalistic news stay unavailable. An 8-K feed is not that provider."""
    return unavailable_news_snapshot(generated_at=generated_at, requested_as_of=requested_as_of)


def publish_web_disclosure(snapshot: dict, *, data_state: str = "LIVE") -> dict:
    """P01 and the freshness contract are not decided. Never assigns LIVE."""
    del snapshot, data_state
    raise IngestError(
        "WEB_PUBLICATION_BLOCKED",
        "primary disclosure web publication stays blocked until P01 and a freshness contract",
    )


def build_primary_disclosure_snapshot(
    payload: bytes,
    *,
    now: datetime,
    fetched_at: datetime,
    generated_at: datetime,
    identity: ExplicitIdentityMap | None = None,
    synthetic: bool = False,
) -> DisclosureBatch:
    """Atom bytes → NewsRawItem → PR #13 validation → exact CIK map → exact dedup."""
    _aware(now, "now")
    fetched_at = _aware(fetched_at, "fetched_at")
    generated_at = _aware(generated_at, "generated_at")
    if not isinstance(payload, bytes) or not payload:
        raise IngestError("MALFORMED", "SEC Atom payload must be raw bytes")
    if not isinstance(synthetic, bool):
        raise IngestError("MALFORMED", "synthetic must be a boolean")
    elements, slices = _parse_feed(payload)
    mapping = identity or ExplicitIdentityMap()
    records = []
    specs = []
    rejected = []
    for element, raw in zip(elements, slices):
        try:
            spec = _entry(element, raw, fetched_at=fetched_at, synthetic=synthetic)
        except IngestError as exc:
            found = re.search(br"accession-number=(\d{10}-\d{2}-\d{6})", raw)
            rejected.append({
                "code": exc.code,
                "accession": found.group(1).decode("ascii") if found else None,
                "message": exc.code,
            })
            continue
        records.append(spec["record"])
        specs.append(spec)
    # Empty alias index on purpose: titles and names are not identity evidence.
    result = ingest(records, now=now, aliases=None)
    for item in result.rejected:
        rejected.append({
            "code": item.code,
            "accession": item.source_item_id,
            "message": item.code,
        })
    by_accession = {spec["accession"]: spec for spec in specs}
    items = []
    rig_inputs = []
    for normalized in result.accepted:
        spec = by_accession[normalized.source_item_id]
        status, company_id, issuer_id = mapping.resolve(spec["cik"]) if spec["cik"] else ("UNKNOWN", None, None)
        if status == "AMBIGUOUS":
            rejected.append({"code": "AMBIGUOUS", "accession": spec["accession"], "message": "AMBIGUOUS"})
            continue
        issuer_ids = (issuer_id,) if issuer_id else ()
        linked = normalized
        if company_id:
            linked = NormalizedNewsItem(**{**normalized.__dict__, "canonical_entity_ids": (company_id,)})
        boundary = to_rig_input(linked, issuer_ids=issuer_ids, kind=SourceKind.PRIMARY_DISCLOSURE)
        if boundary.source.kind is not SourceKind.PRIMARY_DISCLOSURE:
            raise IngestError("POLICY_BLOCKED", "8-K input must stay PRIMARY_DISCLOSURE")
        rig_inputs.append(boundary)
        items.append(_public_item(spec, normalized, status, company_id, issuer_id))
    items.sort(key=lambda row: (row["sec_timestamp"]["value"], row["accession"]))
    snapshot = {
        "contract": "PRIMARY_DISCLOSURE_SNAPSHOT",
        "schema_version": 1,
        "methodology": {
            "id": ADAPTER_ID,
            "version": ADAPTER_VERSION,
            "source_layer": "PRIMARY_DISCLOSURE",
            "general_news": "NOT_AVAILABLE",
            "journalistic_news": "NOT_AVAILABLE",
            "sec_timestamp": "atom updated is feed dissemination, not acceptanceDateTime and not a publication time",
            "filed_on": "date-only when present; a date is not given a clock time",
            "acceptance_at": "NOT_PROVIDED",
            "language": "provider tag or LANGUAGE_NOT_PROVIDED; display locale is not a source language",
            "identity": "explicit CIK map only",
            "dedup": "EXACT_DUPLICATE and SOURCE_ASSERTED_REPEAT only; no similarity threshold",
            "sentiment": "NOT_DEFINED",
            "consensus": "NOT_AVAILABLE",
            "news_event": "NOT_CREATED",
        },
        "data_state": "NOT_PUBLISHED",
        "web_publication": {"status": "BLOCKED", "reason_code": "P01_FRESHNESS_REQUIRED"},
        "as_of": max((row["sec_timestamp"]["value"] for row in items), default=None),
        "generated_at": generated_at.isoformat(),
        "synthetic": synthetic or any(row["synthetic"] for row in items),
        "items": items,
        "rejected": rejected,
        "exact_duplicate_count": len(result.exact_duplicates),
        "provenance": {
            "source": SOURCE,
            "feed_sha256": sha256_hex(payload),
            "feed_bytes": len(payload),
            "fetcher": f"{ADAPTER_ID}/{ADAPTER_VERSION}",
        },
        "rig": {
            "source_kind": "PRIMARY_DISCLOSURE",
            "input_count": len(rig_inputs),
            "news_event_created": False,
        },
        "flags": {
            "GENERAL_NEWS_PROVIDER_READY": "NO",
            "RIG_REAL_PRODUCER_READY": "NO",
            "CONSENSUS_PRODUCER_READY": "NO",
        },
    }
    _refuse_leaks(snapshot)
    snapshot["semantic_hash"] = canonical_sha256(
        {key: value for key, value in snapshot.items() if key not in {"generated_at", "semantic_hash", "record_id"}}
    )
    snapshot["record_id"] = "pds_" + snapshot["semantic_hash"][:16]
    return DisclosureBatch(snapshot, dict(result.raw_by_hash), payload)


def _public_item(spec: dict, item: NormalizedNewsItem, status: str, company_id: str | None, issuer_id: str | None) -> dict:
    company_filter = "RESOLVED" if status == "RESOLVED" and issuer_id else "NOT_AVAILABLE"
    return {
        "source": SOURCE,
        "source_layer": "PRIMARY_DISCLOSURE",
        "accession": spec["accession"],
        "form_type": spec["form_type"],
        "title": spec["title"],
        "item_labels": spec["item_labels"],
        "sec_timestamp": {
            "role": "FEED_DISSEMINATION",
            "element": "updated",
            "value": spec["disseminated_at"].isoformat(),
        },
        "filed_on": spec["filed_on"],
        "filed_on_status": "DATE_ONLY" if spec["filed_on"] else "NOT_PROVIDED",
        "acceptance_at": None,
        "acceptance_status": "NOT_PROVIDED",
        "canonical_url": spec["canonical_url"],
        "cik": spec["cik"],
        "company_id": company_id,
        "issuer_id": issuer_id,
        "company_filter": company_filter,
        "identity_status": status,
        "source_language": item.source_language,
        "display_locale_applied": False,
        "raw_hash": item.raw_hash,
        "normalized_id": item.normalized_id,
        "duplicate_group_id": item.duplicate_group_id,
        "coverage": item.coverage,
        "source_asserted_group_id": item.source_asserted_group_id,
        "synthetic": item.synthetic,
    }


def _entry(element: ElementTree.Element, raw: bytes, *, fetched_at: datetime, synthetic: bool) -> dict:
    title = " ".join((element.findtext(f"{{{ATOM}}}title") or "").split())
    if not title:
        raise IngestError("MALFORMED", "SEC entry title is required")
    form_type = _form_type(element, title)
    accession = _accession(element, raw)
    href = _href(element)
    canonical = _sec_url(href)
    cik = _ciks_agree(title, href)
    disseminated = _dissemination(element.findtext(f"{{{ATOM}}}updated") or "")
    summary = _summary_text(element)
    filed_on = _filed_on(summary)
    if accession_in_summary(summary) not in {None, accession}:
        raise IngestError("ACCESSION_MISMATCH", "summary accession does not match the Atom id")
    language = _language(element)
    if disseminated > fetched_at:
        raise IngestError("TIME_ORDER", "feed dissemination is later than fetched_at")
    record = {
        "source": SOURCE,
        "source_item_id": accession,
        "canonical_url": canonical,
        "title": title,
        "body": "",
        "published_at": disseminated,
        "available_at": disseminated,
        "fetched_at": fetched_at,
        "source_language": language,
        "raw_bytes": raw,
        "mentions": [],
        "synthetic": synthetic,
        "fetcher": f"{ADAPTER_ID}/{ADAPTER_VERSION}",
    }
    return {
        "record": record,
        "accession": accession,
        "form_type": form_type,
        "title": title,
        "item_labels": _item_labels(summary),
        "disseminated_at": disseminated,
        "filed_on": filed_on,
        "canonical_url": canonical,
        "cik": cik,
    }


def _parse_feed(payload: bytes) -> tuple[list[ElementTree.Element], list[bytes]]:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise IngestError("MALFORMED", "SEC Atom payload is not XML") from exc
    elements = [
        child for child in list(root) if child.tag == f"{{{ATOM}}}entry" or child.tag == "entry"
    ]
    slices = _entry_slices(payload)
    if len(elements) != len(slices):
        raise IngestError("MALFORMED", "raw entry bytes do not match the parsed entries")
    return elements, slices


def _entry_slices(payload: bytes) -> list[bytes]:
    slices = []
    start = 0
    while True:
        opened = payload.find(b"<entry", start)
        if opened < 0:
            return slices
        marker = opened + len(b"<entry")
        if marker < len(payload) and payload[marker:marker + 1] not in {b">", b" ", b"\n", b"\r", b"\t", b"/"}:
            start = marker
            continue
        closed = payload.find(b"</entry>", opened)
        if closed < 0:
            raise IngestError("MALFORMED", "unclosed atom entry")
        closed += len(b"</entry>")
        slices.append(payload[opened:closed])
        start = closed


def _form_type(element: ElementTree.Element, title: str) -> str:
    terms = []
    for category in list(element):
        if category.tag not in {f"{{{ATOM}}}category", "category"}:
            continue
        label = (category.attrib.get("label") or "").casefold()
        if label == "form type" and category.attrib.get("term"):
            terms.append(category.attrib["term"].strip())
    head = title.split(" - ", 1)[0].strip()
    titled = head if head in _FORMS else None
    if len(set(terms)) > 1:
        raise IngestError("FORM_MISMATCH", "SEC entry has more than one form type")
    stated = terms[0] if terms else None
    if stated and titled and stated != titled:
        raise IngestError("FORM_MISMATCH", "SEC category form does not match the title form")
    form = stated or titled
    if form not in _FORMS:
        raise IngestError("OUT_OF_SCOPE", "only 8-K and 8-K/A are in this adapter")
    return form


def _accession(element: ElementTree.Element, raw: bytes) -> str:
    entry_id = (element.findtext(f"{{{ATOM}}}id") or element.findtext("id") or "").strip()
    match = re.search(r"accession-number=(\d{10}-\d{2}-\d{6})", entry_id)
    href = _href(element)
    url_match = _ACC_URL.search(href)
    found = []
    if match:
        found.append(match.group(1))
    if url_match:
        found.append(url_match.group(1))
    if not found:
        raise IngestError("MALFORMED", "SEC accession is missing")
    if len(set(found)) != 1:
        raise IngestError("ACCESSION_MISMATCH", "Atom id and index URL name different accessions")
    accession = found[0]
    if not _ACCESSION.fullmatch(accession):
        raise IngestError("MALFORMED", "SEC accession is not in dashed form")
    if accession.encode("ascii") not in raw and accession.replace("-", "").encode("ascii") not in raw:
        raise IngestError("MALFORMED", "accession is not in the raw entry bytes")
    return accession


def _href(element: ElementTree.Element) -> str:
    for child in list(element):
        if child.tag in {f"{{{ATOM}}}link", "link"} and child.attrib.get("href"):
            return child.attrib["href"].strip()
    raise IngestError("MALFORMED", "SEC index link is required")


def _sec_url(href: str) -> str:
    if href.startswith("/"):
        href = "https://www.sec.gov" + href
    try:
        canonical = canonicalize_url(href)
    except ValueError as exc:
        raise IngestError("MALFORMED", "SEC index link is not an absolute http(s) URL") from exc
    host = canonical.split("/", 3)[2]
    if host not in {"www.sec.gov", "sec.gov"}:
        raise IngestError("MALFORMED", "canonical filing link must be on sec.gov")
    return canonical


def _ciks_agree(title: str, href: str) -> str | None:
    titled = _CIK_TITLE.search(title)
    located = _CIK_URL.search(href)
    found = []
    if titled:
        found.append(_cik10(titled.group(1)))
    if located:
        found.append(_cik10(located.group(1)))
    if not found:
        return None
    if len(set(found)) != 1:
        raise IngestError("CIK_MISMATCH", "title CIK and index URL CIK disagree")
    return found[0]


def _cik10(value: str) -> str:
    if not isinstance(value, str) or not value.strip().isdigit() or not 1 <= len(value.strip()) <= 10:
        raise IngestError("MALFORMED", "CIK must be 1 to 10 digits")
    return value.strip().zfill(10)


def _dissemination(text: str) -> datetime:
    raw = text.strip()
    if _DATE.fullmatch(raw):
        raise IngestError("DATE_ONLY_NOT_A_CLOCK", "date-only updated is not a feed dissemination timestamp")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise IngestError("MALFORMED", "updated is not an ISO timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise IngestError("MALFORMED", "updated must be timezone-aware")
    return value


def _summary_text(element: ElementTree.Element) -> str:
    summary = element.find(f"{{{ATOM}}}summary")
    if summary is None:
        summary = element.find("summary")
    text = "".join(summary.itertext()) if summary is not None else ""
    return re.sub(r"<[^>]+>", " ", text)


def _filed_on(summary: str) -> str | None:
    match = re.search(r"Filed:\s*(\S+)", summary)
    if not match:
        return None
    token = match.group(1).strip()
    if not _DATE.fullmatch(token):
        return None
    date.fromisoformat(token)
    return token


def accession_in_summary(summary: str) -> str | None:
    match = re.search(r"AccNo:\s*(\d{10}-\d{2}-\d{6})", summary)
    return match.group(1) if match else None


def _item_labels(summary: str) -> list[dict[str, str]]:
    labels = []
    seen: dict[str, str] = {}
    for code, label in _ITEM.findall(summary):
        text = " ".join(label.split())
        if not text:
            continue
        previous = seen.get(code)
        if previous is not None and previous != text:
            raise IngestError("MALFORMED", "the same SEC item code has two labels")
        if previous is None:
            seen[code] = text
            labels.append({"code": code, "label": text})
    return labels


def _language(element: ElementTree.Element) -> str:
    raw = element.attrib.get(XML_LANG) or element.attrib.get("lang")
    if raw is None or not raw.strip():
        return LANGUAGE_NOT_PROVIDED
    if _LANGUAGE.fullmatch(raw) is None:
        raise IngestError("MALFORMED", "xml:lang is not a BCP 47-like tag and is not inferred")
    return raw


def _refuse_leaks(snapshot: dict) -> None:
    import json

    text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    for token in ("<b>", "AccNo", "EXHIBIT BODY"):
        if token in text or token.casefold() in text.casefold():
            raise IngestError("POLICY_BLOCKED", "exhibit text or SEC summary markup must not be copied")


def _aware(value: datetime, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IngestError("MALFORMED", f"{label} must be a timezone-aware datetime")
    return value
