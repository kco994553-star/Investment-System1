"""NewsRawItem -> provenance -> entity resolution -> exact dedup -> normalized item.

``display_locale`` is accepted so a caller cannot hide it inside the item,
then ignored. It does not change ids, hashes, source language, or grouping.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .dedup import Rejection, dedup
from .entities import AliasIndex, annotate
from .errors import IngestError
from .normalize import NormalizedNewsItem, normalize
from .raw import parse_record


@dataclass(frozen=True)
class IngestResult:
    accepted: tuple[NormalizedNewsItem, ...]
    exact_duplicates: tuple[NormalizedNewsItem, ...]
    rejected: tuple[Rejection, ...]
    raw_by_hash: dict[str, bytes]
    display_locale_applied: bool = False


def _identity(record: object, name: str) -> str | None:
    if isinstance(record, dict):
        value = record.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def ingest(
    records: object,
    *,
    now: datetime,
    aliases: AliasIndex | None = None,
    display_locale: str | None = None,
) -> IngestResult:
    if display_locale is not None and not isinstance(display_locale, str):
        raise IngestError("MALFORMED", "display_locale must be a string when passed")
    del display_locale  # presentation only; intentionally unused
    if not isinstance(records, (list, tuple)):
        raise IngestError("MALFORMED", "records must be a list")
    index = aliases or AliasIndex()
    parsed = []
    rejected: list[Rejection] = []
    raw_by_hash: dict[str, bytes] = {}
    for record in records:
        try:
            raw = parse_record(record, now=now)
        except IngestError as exc:
            rejected.append(Rejection(exc.code, str(exc), _identity(record, "source"), _identity(record, "source_item_id")))
            continue
        raw_by_hash.setdefault(raw.raw_hash, raw.raw_bytes)
        parsed.append(raw)
    normalized = tuple(annotate(normalize(raw), index) for raw in parsed)
    accepted, duplicates, conflicts = dedup(normalized)
    return IngestResult(accepted, duplicates, tuple(rejected) + conflicts, raw_by_hash, False)
