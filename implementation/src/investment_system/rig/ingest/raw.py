"""Raw news item. The provider payload bytes are preserved unchanged.

Normalized fields are a separate mapping. They never replace ``raw_bytes``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from .contract import LANGUAGE_NOT_PROVIDED, canonicalize_url, sha256_hex
from .errors import IngestError

_LANGUAGE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_ALLOWED = frozenset({
    "source",
    "source_item_id",
    "canonical_url",
    "title",
    "body",
    "published_at",
    "available_at",
    "fetched_at",
    "source_language",
    "raw_bytes",
    "mentions",
    "source_asserted_group_id",
    "synthetic",
    "http_status",
    "notes",
    "fetcher",
    "display_locale",
})


@dataclass(frozen=True)
class NewsRawItem:
    source: str
    source_item_id: str
    submitted_url: str
    canonical_url: str
    title: str
    body: str
    published_at: datetime
    available_at: datetime
    fetched_at: datetime
    source_language: str
    raw_bytes: bytes
    raw_hash: str
    mentions: tuple[str, ...]
    source_asserted_group_id: str | None
    synthetic: bool
    http_status: int | None
    notes: str
    fetcher: str


def _aware(record: dict, name: str) -> datetime:
    value = record.get(name)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IngestError("MALFORMED", f"{name} must be a timezone-aware datetime")
    return value


def _text(record: dict, name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise IngestError("MALFORMED", f"{name} is required")
    return value.strip()


def parse_record(record: object, *, now: datetime) -> NewsRawItem:
    """Validate one supplied item against ``now``. ``now`` is the caller's clock."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise IngestError("MALFORMED", "now must be a timezone-aware datetime")
    if not isinstance(record, dict):
        raise IngestError("MALFORMED", "news item must be an object")
    unknown = sorted(set(record) - _ALLOWED)
    if unknown:
        raise IngestError("MALFORMED", f"unknown field {unknown[0]}")
    if "display_locale" in record:
        raise IngestError(
            "DISPLAY_LOCALE_IS_NOT_SOURCE_LANGUAGE",
            "display_locale is a presentation preference and cannot be stored on a news item",
        )
    source = _text(record, "source")
    source_item_id = _text(record, "source_item_id")
    submitted = record.get("canonical_url")
    if not isinstance(submitted, str):
        raise IngestError("MALFORMED", "canonical_url is required")
    try:
        canonical = canonicalize_url(submitted)
    except ValueError as exc:
        raise IngestError("MALFORMED", str(exc)) from exc
    title = record.get("title")
    body = record.get("body")
    if not isinstance(title, str) or not " ".join(title.split()):
        raise IngestError("MALFORMED", "title is required")
    if not isinstance(body, str):
        raise IngestError("MALFORMED", "body must be a string")
    language = record.get("source_language")
    if language == LANGUAGE_NOT_PROVIDED:
        pass
    elif not isinstance(language, str) or _LANGUAGE.fullmatch(language) is None:
        raise IngestError(
            "MALFORMED",
            "source_language must be a BCP 47-like language tag, or LANGUAGE_NOT_PROVIDED when the provider omitted it",
        )
    published = _aware(record, "published_at")
    available = _aware(record, "available_at")
    fetched = _aware(record, "fetched_at")
    if not (published <= available <= fetched):
        raise IngestError("TIME_ORDER", "require published_at <= available_at <= fetched_at")
    if published > now or available > now or fetched > now:
        raise IngestError("FUTURE", "news timestamps must not be later than the evaluation clock")
    raw = record.get("raw_bytes")
    if not isinstance(raw, bytes):
        raise IngestError("MALFORMED", "raw_bytes must be the original payload bytes")
    mentions = record.get("mentions", ())
    if not isinstance(mentions, (list, tuple)) or not all(isinstance(m, str) and m.strip() for m in mentions):
        raise IngestError("MALFORMED", "mentions must be a list of non-empty strings")
    group = record.get("source_asserted_group_id")
    if group is not None and (not isinstance(group, str) or not group.strip()):
        raise IngestError("MALFORMED", "source_asserted_group_id must be a non-empty string when set")
    synthetic = record.get("synthetic", False)
    if not isinstance(synthetic, bool):
        raise IngestError("MALFORMED", "synthetic must be a boolean")
    http_status = record.get("http_status")
    if http_status is not None and (not isinstance(http_status, int) or isinstance(http_status, bool) or not 100 <= http_status <= 599):
        raise IngestError("MALFORMED", "http_status must be an integer 100-599")
    notes = record.get("notes", "")
    if not isinstance(notes, str):
        raise IngestError("MALFORMED", "notes must be a string")
    fetcher = record.get("fetcher", "RIG_NEWS_INGEST/1+supplied")
    if not isinstance(fetcher, str) or not fetcher.strip():
        raise IngestError("MALFORMED", "fetcher must be a non-empty string")
    return NewsRawItem(
        source=source,
        source_item_id=source_item_id,
        submitted_url=submitted.strip(),
        canonical_url=canonical,
        title=" ".join(title.split()),
        body=body,
        published_at=published,
        available_at=available,
        fetched_at=fetched,
        source_language=language,
        raw_bytes=raw,
        raw_hash=sha256_hex(raw),
        mentions=tuple(m.strip() for m in mentions),
        source_asserted_group_id=None if group is None else group.strip(),
        synthetic=synthetic,
        http_status=http_status,
        notes=notes,
        fetcher=fetcher.strip(),
    )
