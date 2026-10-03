"""RIG news ingestion contract constants (``RIG_NEWS_INGEST`` v1).

This package normalizes a supplied news payload into a RIG input. It does not
fetch, score, translate, or classify economic-event kind. ``display_locale`` is
never an input to identity, hashing, language, or grouping.

Semantic near-duplicate grouping is POLICY_BLOCKED: ``RIG_NEWS_ARCH_v0.1`` and
the Global/Korea source contract name same-event grouping but publish no
similarity threshold. No numeric threshold is defined here.
"""

from __future__ import annotations

import hashlib
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

CONTRACT = "RIG_NEWS_INGEST"
SCHEMA_VERSION = 1
METHODOLOGY_ID = "RIG_NEWS_INGEST"
METHODOLOGY_VERSION = "1"
ENTITY_MATCH_ID = "ENTITY_MATCH_V1"
SEMANTIC_GROUPING = "POLICY_BLOCKED"
# Audited read-only dependencies. Not merged and not vendored.
ENTITY_METADATA_AUDITED_SHA = "a013f1c1758642f90a65fe11df69fc234c143a48"
PRODUCER_INFRA_AUDITED_SHA = "6fe9eee5668388fa4a200904520a0b5a46c90b6f"

# Fields a normalized item is required to preserve. Raw body stays on the raw
# record; only its hash crosses the boundary.
PRESERVED = (
    "source",
    "source_item_id",
    "canonical_url",
    "title",
    "published_at",
    "available_at",
    "fetched_at",
    "source_language",
    "raw_hash",
    "provenance",
    "canonical_entity_ids",
    "duplicate_group_id",
    "methodology",
)


def canonical_bytes(value: object) -> bytes:
    """Same canonical JSON as PRODUCER_SNAPSHOT serialization: sorted keys, UTF-8, no NaN."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: object) -> str:
    return sha256_hex(canonical_bytes(value))


def canonicalize_url(url: str) -> str:
    """Deterministic source identity for an absolute http(s) URL.

    Drops the fragment and sorts the query. Does not strip tracking parameters:
    no approved denylist exists, and stripping would change identity.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("canonical_url is required")
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("canonical_url must be an absolute http(s) URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("canonical_url must not carry credentials")
    try:
        host = parts.hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("canonical_url host is not valid") from exc
    port = parts.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = parts.path or "/"
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))
