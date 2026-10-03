"""Boundary into frozen RIG P0 records.

Builds ``SourceRef`` and ``Evidence`` only. A ``NewsEvent`` is constructed
only when the caller supplies both an ``EconomicEventKind`` and a claim
statement. Kind is never inferred from the title or the body.
``issuer_id`` is never inferred from a ticker or a company_id.
The default ``SourceKind`` remains ``NEWS``. Primary disclosure passes
``PRIMARY_DISCLOSURE`` explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model import Claim, ClaimPolarity, EconomicEventKind, Evidence, NewsEvent, SourceKind, SourceRef, stable_id
from .errors import IngestError
from .normalize import NormalizedNewsItem


@dataclass(frozen=True)
class RigNewsInput:
    normalized_id: str
    source: SourceRef
    evidence: Evidence
    company_ids: tuple[str, ...]
    issuer_ids: tuple[str, ...]


def issuer_ids_for(item: NormalizedNewsItem, mapping: dict[str, str] | None) -> tuple[str, ...]:
    """Explicit company_id -> issuer_id map. Missing keys stay unmapped."""
    if not mapping:
        return ()
    found = []
    for company_id in item.canonical_entity_ids:
        issuer_id = mapping.get(company_id)
        if isinstance(issuer_id, str) and issuer_id.strip():
            found.append(issuer_id.strip())
    return tuple(found)


def to_rig_input(
    item: NormalizedNewsItem,
    *,
    issuer_ids: tuple[str, ...] = (),
    kind: SourceKind = SourceKind.NEWS,
) -> RigNewsInput:
    if item.coverage == "EXACT_DUPLICATE":
        raise IngestError("CONFLICT", "exact duplicates are not a second RIG input")
    if not isinstance(kind, SourceKind):
        raise IngestError("MALFORMED", "source kind must be a SourceKind")
    if kind not in {SourceKind.NEWS, SourceKind.PRIMARY_DISCLOSURE}:
        raise IngestError("POLICY_BLOCKED", "ingestion only emits NEWS or PRIMARY_DISCLOSURE")
    source = SourceRef(
        source_id=item.source_identity,
        kind=kind,
        publisher=item.source,
        published_at=item.published_at,
        raw_artifact_id=f"newsraw:{item.raw_hash}",
    )
    evidence = Evidence(
        evidence_id=stable_id("evd", item.normalized_id),
        source_id=source.source_id,
        locator=item.canonical_url,
        available_at=item.available_at,
    )
    return RigNewsInput(item.normalized_id, source, evidence, item.canonical_entity_ids, issuer_ids)


def promote_news_event(
    item: NormalizedNewsItem,
    *,
    kind: EconomicEventKind | None,
    statement: str | None,
    polarity: ClaimPolarity | None,
    issuer_ids: tuple[str, ...] = (),
) -> tuple[RigNewsInput, Claim, NewsEvent]:
    """Explicit promotion only. Refuses to invent kind, polarity, or occurred_on."""
    if not isinstance(kind, EconomicEventKind) or not isinstance(statement, str) or not statement.strip():
        raise IngestError("EXPLICIT_ONLY", "NewsEvent kind and claim statement must be supplied; they are not inferred")
    if not isinstance(polarity, ClaimPolarity):
        raise IngestError("EXPLICIT_ONLY", "claim polarity must be supplied; it is not inferred")
    boundary = to_rig_input(item, issuer_ids=issuer_ids)
    claim = Claim(
        claim_id=stable_id("clm", item.normalized_id),
        evidence_ids=(boundary.evidence.evidence_id,),
        statement=statement.strip(),
        polarity=polarity,
        available_at=item.available_at,
    )
    event = NewsEvent(
        event_id=stable_id("evt", item.normalized_id),
        kind=kind,
        claim_ids=(claim.claim_id,),
        available_at=item.available_at,
        occurred_on=None,
    )
    return boundary, claim, event
