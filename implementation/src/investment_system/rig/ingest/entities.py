"""Exact company_id resolution. No similarity score and no threshold.

Labels are matched by ``ENTITY_MATCH_V1``: NFKC, casefold, punctuation to
space, collapsed whitespace. Tickers also drop spaces. A mention that hits
more than one company_id is AMBIGUOUS and resolves to nobody.

The PR #7 registry is a read-only JSON shape. This module does not import
``product.entity_metadata`` and does not copy the registry into the branch.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .errors import IngestError
from .normalize import EntityHit, NormalizedNewsItem


def name_key(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in folded)
    return " ".join(cleaned.split())


def ticker_key(text: str) -> str:
    return name_key(text).replace(" ", "")


@dataclass
class AliasIndex:
    """Injected label index. Identity is the caller's company_id, never invented here."""

    source: str = "injected"
    universe_id: str | None = None
    universe_sha256: str | None = None
    _tickers: dict[str, set[str]] = field(default_factory=dict)
    _names: dict[str, set[str]] = field(default_factory=dict)

    def add(self, company_id: str, *, tickers: tuple[str, ...] = (), names: tuple[str, ...] = ()) -> None:
        if not isinstance(company_id, str) or not company_id.strip():
            raise IngestError("MALFORMED", "company_id is required")
        cid = company_id.strip()
        for ticker in tickers:
            if isinstance(ticker, str) and ticker.strip():
                self._tickers.setdefault(ticker_key(ticker), set()).add(cid)
        for name in names:
            if isinstance(name, str) and name.strip():
                self._names.setdefault(name_key(name), set()).add(cid)

    def resolve(self, mention: str) -> EntityHit:
        if not isinstance(mention, str) or not mention.strip():
            raise IngestError("MALFORMED", "mention is required")
        owners = set(self._tickers.get(ticker_key(mention), ())) | set(self._names.get(name_key(mention), ()))
        if not owners:
            return EntityHit(mention.strip(), "UNKNOWN", None, None)
        if len(owners) > 1:
            return EntityHit(mention.strip(), "AMBIGUOUS", None, None)
        company_id = next(iter(owners))
        field_name = "ticker" if company_id in self._tickers.get(ticker_key(mention), ()) else "name"
        return EntityHit(mention.strip(), "RESOLVED", company_id, field_name)


def annotate(item: NormalizedNewsItem, index: AliasIndex) -> NormalizedNewsItem:
    hits = tuple(index.resolve(mention) for mention in item.mentions)
    company_ids = tuple(sorted({hit.company_id for hit in hits if hit.status == "RESOLVED" and hit.company_id}))
    return NormalizedNewsItem(
        **{**item.__dict__, "entity_hits": hits, "canonical_entity_ids": company_ids}
    )


def _values(node: object) -> list[str]:
    """Collect registry ``value`` fields. Bare strings are names only at the leaves of ``value``."""
    found: list[str] = []
    if isinstance(node, dict):
        value = node.get("value")
        if isinstance(value, str):
            found.append(value)
        for key, child in node.items():
            if key != "value" and isinstance(child, (dict, list)):
                found.extend(_values(child))
    elif isinstance(node, list):
        for child in node:
            found.extend(_values(child))
    return found


def index_from_registry(document: dict) -> AliasIndex:
    """Read a PR #7 ``ENTITY_SEARCH_METADATA_REGISTRY`` document. Does not fetch or merge entities."""
    if not isinstance(document, dict):
        raise IngestError("MALFORMED", "entity registry must be an object")
    if document.get("kind") != "ENTITY_SEARCH_METADATA_REGISTRY" or document.get("schema_version") != 1:
        raise IngestError("MALFORMED", "entity registry is not schema v1")
    if document.get("role") != "SEARCH_PRESENTATION_ONLY":
        raise IngestError("MALFORMED", "entity registry role is not search/presentation metadata")
    records = document.get("records")
    if not isinstance(records, dict) or not records:
        raise IngestError("MALFORMED", "entity registry has no records")
    index = AliasIndex(
        source="entity_metadata_registry_v1",
        universe_id=document.get("universe_id") if isinstance(document.get("universe_id"), str) else None,
        universe_sha256=document.get("universe_sha256") if isinstance(document.get("universe_sha256"), str) else None,
    )
    for key, record in records.items():
        if not isinstance(record, dict) or record.get("company_id") != key:
            raise IngestError("MALFORMED", "entity registry company_id does not match its key")
        names = _values(record.get("official_name"))
        names += _values(record.get("common_names"))
        names += _values(record.get("aliases"))
        names += _values(record.get("historical_names"))
        ticker = record.get("ticker")
        tickers = [ticker] if isinstance(ticker, str) else []
        tickers += _values(record.get("historical_tickers"))
        index.add(key, tickers=tuple(tickers), names=tuple(names))
    return index
