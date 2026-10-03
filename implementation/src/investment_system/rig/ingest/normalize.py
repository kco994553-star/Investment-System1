"""Deterministic normalization. Same raw mapping -> same id and public JSON.

The raw body is not copied onto the normalized record. ``body_sha256`` is the
bridge. ``display_locale`` is not a parameter and not a field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..model import stable_id
from .contract import (
    CONTRACT,
    ENTITY_MATCH_ID,
    METHODOLOGY_ID,
    METHODOLOGY_VERSION,
    SCHEMA_VERSION,
    SEMANTIC_GROUPING,
    canonical_bytes,
    sha256_hex,
)
from .raw import NewsRawItem


@dataclass(frozen=True)
class EntityHit:
    mention: str
    status: str  # RESOLVED | UNKNOWN | AMBIGUOUS
    company_id: str | None
    matched_field: str | None


@dataclass(frozen=True)
class NormalizedNewsItem:
    """Normalized news representation. Not ``rig.model.NewsEvent``.

    ``rig.model.NewsEvent`` is a real-world economic event and stays frozen.
    Promoting this item into that type requires an explicit kind and claim.
    """

    normalized_id: str
    source: str
    source_item_id: str
    source_identity: str
    canonical_url: str
    submitted_url: str
    title: str
    published_at: datetime
    available_at: datetime
    fetched_at: datetime
    source_language: str
    raw_hash: str
    raw_bytes: int
    body_sha256: str
    content_sha256: str
    mapping_sha256: str
    mentions: tuple[str, ...]
    source_asserted_group_id: str | None
    synthetic: bool
    http_status: int | None
    notes: str
    fetcher: str
    entity_hits: tuple[EntityHit, ...] = ()
    canonical_entity_ids: tuple[str, ...] = ()
    duplicate_of: str | None = None
    duplicate_group_id: str = ""
    coverage: str = "STANDALONE"
    semantic_grouping: str = SEMANTIC_GROUPING

    @property
    def methodology(self) -> dict[str, str]:
        return {"id": METHODOLOGY_ID, "version": METHODOLOGY_VERSION}


def _content_material(raw: NewsRawItem, body_sha256: str) -> dict:
    return {
        "available_at": raw.available_at.isoformat(),
        "body_sha256": body_sha256,
        "canonical_url": raw.canonical_url,
        "mentions": list(raw.mentions),
        "published_at": raw.published_at.isoformat(),
        "source_asserted_group_id": raw.source_asserted_group_id,
        "source_language": raw.source_language,
        "synthetic": raw.synthetic,
        "title": raw.title,
    }


def _mapping_material(raw: NewsRawItem, content: dict) -> dict:
    return {**content, "source": raw.source, "source_item_id": raw.source_item_id}


def normalize(raw: NewsRawItem) -> NormalizedNewsItem:
    body_sha256 = sha256_hex(raw.body.encode("utf-8"))
    content = _content_material(raw, body_sha256)
    mapping = _mapping_material(raw, content)
    item_id = stable_id(
        "nwi",
        METHODOLOGY_VERSION,
        raw.source,
        raw.source_item_id,
        raw.canonical_url,
        raw.raw_hash,
    )
    return NormalizedNewsItem(
        normalized_id=item_id,
        source=raw.source,
        source_item_id=raw.source_item_id,
        source_identity=f"{raw.source}:{raw.source_item_id}",
        canonical_url=raw.canonical_url,
        submitted_url=raw.submitted_url,
        title=raw.title,
        published_at=raw.published_at,
        available_at=raw.available_at,
        fetched_at=raw.fetched_at,
        source_language=raw.source_language,
        raw_hash=raw.raw_hash,
        raw_bytes=len(raw.raw_bytes),
        body_sha256=body_sha256,
        content_sha256=sha256_hex(canonical_bytes(content)),
        mapping_sha256=sha256_hex(canonical_bytes(mapping)),
        mentions=raw.mentions,
        source_asserted_group_id=raw.source_asserted_group_id,
        synthetic=raw.synthetic,
        http_status=raw.http_status,
        notes=raw.notes,
        fetcher=raw.fetcher,
        duplicate_group_id=item_id,
    )


def to_public_dict(item: NormalizedNewsItem) -> dict:
    """Normalized JSON. Contains no raw body and no display locale."""
    return {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "methodology": item.methodology,
        "entity_match": ENTITY_MATCH_ID,
        "semantic_grouping": item.semantic_grouping,
        "normalized_id": item.normalized_id,
        "source": item.source,
        "source_item_id": item.source_item_id,
        "source_identity": item.source_identity,
        "canonical_url": item.canonical_url,
        "submitted_url": item.submitted_url,
        "title": item.title,
        "published_at": item.published_at.isoformat(),
        "available_at": item.available_at.isoformat(),
        "fetched_at": item.fetched_at.isoformat(),
        "source_language": item.source_language,
        "raw_hash": item.raw_hash,
        "raw_bytes": item.raw_bytes,
        "body_sha256": item.body_sha256,
        "content_sha256": item.content_sha256,
        "mapping_sha256": item.mapping_sha256,
        "provenance": {
            "source": item.source,
            "source_item_id": item.source_item_id,
            "canonical_url": item.canonical_url,
            "submitted_url": item.submitted_url,
            "raw_hash": item.raw_hash,
            "raw_bytes": item.raw_bytes,
            "fetched_at": item.fetched_at.isoformat(),
            "fetcher": item.fetcher,
            "http_status": item.http_status,
            "notes": item.notes,
        },
        "mentions": list(item.mentions),
        "entity_hits": [
            {
                "mention": h.mention,
                "status": h.status,
                "company_id": h.company_id,
                "matched_field": h.matched_field,
            }
            for h in item.entity_hits
        ],
        "canonical_entity_ids": list(item.canonical_entity_ids),
        "duplicate_of": item.duplicate_of,
        "duplicate_group_id": item.duplicate_group_id,
        "source_asserted_group_id": item.source_asserted_group_id,
        "coverage": item.coverage,
    }
