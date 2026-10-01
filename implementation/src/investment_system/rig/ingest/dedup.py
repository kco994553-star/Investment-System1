"""Exact duplicates versus same-event repeats.

Exact means the same raw bytes and the same normalized mapping. A provider
story id (``source_asserted_group_id``) may mark repeated coverage of one
event without comparing text. Semantic similarity is refused: there is no
approved threshold to apply.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import IngestError
from .normalize import NormalizedNewsItem


@dataclass(frozen=True)
class Rejection:
    code: str
    message: str
    source: str | None
    source_item_id: str | None


def assign_semantic_group(*_args: object, **_kwargs: object) -> None:
    """Always refused. Do not add a threshold parameter."""
    raise IngestError(
        "POLICY_BLOCKED",
        "semantic similarity has no approved threshold in RIG_NEWS_ARCH_v0.1 or the Global/Korea news contract",
    )


def dedup(items: tuple[NormalizedNewsItem, ...]) -> tuple[tuple[NormalizedNewsItem, ...], tuple[NormalizedNewsItem, ...], tuple[Rejection, ...]]:
    by_hash: dict[str, NormalizedNewsItem] = {}
    by_identity: dict[str, NormalizedNewsItem] = {}
    accepted: list[NormalizedNewsItem] = []
    duplicates: list[NormalizedNewsItem] = []
    rejected: list[Rejection] = []
    for item in items:
        previous_identity = by_identity.get(item.source_identity)
        previous_hash = by_hash.get(item.raw_hash)
        if previous_identity is not None and (
            previous_identity.raw_hash != item.raw_hash or previous_identity.mapping_sha256 != item.mapping_sha256
        ):
            rejected.append(Rejection(
                "CONFLICT",
                f"source item {item.source_identity} changed raw hash or mapping",
                item.source,
                item.source_item_id,
            ))
            continue
        if previous_hash is not None and previous_hash.content_sha256 != item.content_sha256:
            rejected.append(Rejection(
                "CONFLICT",
                f"raw hash {item.raw_hash} is already mapped to {previous_hash.normalized_id}",
                item.source,
                item.source_item_id,
            ))
            continue
        if previous_identity is not None or previous_hash is not None:
            canonical = previous_identity or previous_hash
            assert canonical is not None
            duplicates.append(NormalizedNewsItem(**{
                **item.__dict__,
                "duplicate_of": canonical.normalized_id,
                "duplicate_group_id": canonical.duplicate_group_id,
                "coverage": "EXACT_DUPLICATE",
            }))
            continue
        kept = NormalizedNewsItem(**{
            **item.__dict__,
            "duplicate_of": None,
            "duplicate_group_id": item.normalized_id,
            "coverage": "STANDALONE",
        })
        by_hash[item.raw_hash] = kept
        by_identity[item.source_identity] = kept
        accepted.append(kept)
    counts: dict[str, int] = {}
    for item in accepted:
        if item.source_asserted_group_id:
            counts[item.source_asserted_group_id] = counts.get(item.source_asserted_group_id, 0) + 1
    accepted = [
        NormalizedNewsItem(**{**item.__dict__, "coverage": "SOURCE_ASSERTED_REPEAT"})
        if item.source_asserted_group_id and counts.get(item.source_asserted_group_id, 0) > 1
        else item
        for item in accepted
    ]
    return tuple(accepted), tuple(duplicates), tuple(rejected)
