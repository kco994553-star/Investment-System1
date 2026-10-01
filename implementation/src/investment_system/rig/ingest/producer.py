"""Emit a PRODUCER_SNAPSHOT v1 news section without importing the unmerged package.

The dict matches the audited Producer Infrastructure contract
(``PRODUCER_INFRA_AUDITED_SHA``). No TTL is invented: LIVE requires the
caller to pass ``expires_at``. With no provider and no batch, the only
unattended output is NOT_AVAILABLE / NEWS_NO_SOURCE.

Consensus is not a section of that contract and is not emitted.
"""

from __future__ import annotations

from datetime import datetime

from .contract import METHODOLOGY_ID, METHODOLOGY_VERSION, SEMANTIC_GROUPING, canonical_sha256
from .errors import IngestError
from .normalize import NormalizedNewsItem
from .pipeline import IngestResult
from .rig_input import issuer_ids_for

_STATES = frozenset({"LIVE", "FROZEN_SNAPSHOT", "DEMO", "NOT_AVAILABLE"})
_PUBLISHED = frozenset({"LIVE", "FROZEN_SNAPSHOT", "DEMO"})
_FORBIDDEN = frozenset({"sentiment", "impact_score", "consensus", "display_locale", "summary"})


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IngestError("MALFORMED", f"{name} must be a timezone-aware datetime")
    return value


def _snapshot(
    *,
    data_state: str,
    generated_at: datetime,
    requested_as_of: datetime,
    as_of: datetime | None,
    expires_at: datetime | None,
    data: list | None,
    inputs: list[dict],
    source: str | None,
    reason: str | None,
    reason_code: str | None,
    synthetic: bool,
    checks: list[str],
    validation_status: str,
) -> dict:
    return {
        "contract": "PRODUCER_SNAPSHOT",
        "schema_version": 1,
        "producer_id": "rig.news_ingest",
        "producer_version": METHODOLOGY_VERSION,
        "section": "news",
        "data_state": data_state,
        "requested_as_of": requested_as_of.isoformat(),
        "as_of": None if as_of is None else as_of.isoformat(),
        "generated_at": generated_at.isoformat(),
        "expires_at": None if expires_at is None else expires_at.isoformat(),
        "usable_until": None,
        "methodology": {
            "id": METHODOLOGY_ID if data is not None else "NONE",
            "version": METHODOLOGY_VERSION if data is not None else "NONE",
            "status": "INFORMATION_ONLY" if data is not None else "NOT_AVAILABLE",
        },
        "synthetic": synthetic,
        "provenance": {"source": source, "inputs": inputs},
        "validation": {"status": validation_status, "checks": checks},
        "scope": {"kind": "DOCUMENT", "entity_ids": None},
        "data": data,
        "data_sha256": None if data is None else canonical_sha256(data),
        "reason": reason,
        "reason_code": reason_code,
    }


def unavailable_news_snapshot(
    *,
    generated_at: datetime,
    requested_as_of: datetime,
    reason_code: str = "NEWS_NO_SOURCE",
    reason: str = "No news provider is activated. Ingestion does not fetch.",
) -> dict:
    """Unattended news output. This is not a real news producer."""
    generated_at = _aware(generated_at, "generated_at")
    requested_as_of = _aware(requested_as_of, "requested_as_of")
    if reason_code not in {"NEWS_NO_SOURCE", "NO_ITEMS_AT_AS_OF", "NO_PUBLISHABLE_ITEMS"}:
        raise IngestError("MALFORMED", "unknown news absence reason")
    if not reason.strip():
        raise IngestError("MALFORMED", "reason is required")
    return _snapshot(
        data_state="NOT_AVAILABLE",
        generated_at=generated_at,
        requested_as_of=requested_as_of,
        as_of=None,
        expires_at=None,
        data=None,
        inputs=[],
        source=None,
        reason=reason,
        reason_code=reason_code,
        synthetic=False,
        checks=["provider_activated:false", f"semantic_grouping:{SEMANTIC_GROUPING}", "consensus:NOT_AVAILABLE"],
        validation_status="NOT_RUN",
    )


def _card(item: NormalizedNewsItem, issuer_ids: tuple[str, ...]) -> dict:
    card = {
        "event_id": item.normalized_id,
        "headline": item.title,
        "issuer_ids": list(issuer_ids),
        "company_ids": list(item.canonical_entity_ids),
        "available_at": item.available_at.isoformat(),
        "published_at": item.published_at.isoformat(),
        "fetched_at": item.fetched_at.isoformat(),
        "status": "NEW",
        "source": item.source,
        "source_item_id": item.source_item_id,
        "canonical_url": item.canonical_url,
        "source_language": item.source_language,
        "raw_hash": item.raw_hash,
        "duplicate_group_id": item.duplicate_group_id,
        "source_asserted_group_id": item.source_asserted_group_id,
        "coverage": item.coverage,
        "methodology": item.methodology,
    }
    leaked = _FORBIDDEN.intersection(card)
    if leaked:
        raise IngestError("POLICY_BLOCKED", f"news card must not carry {sorted(leaked)[0]}")
    return card


def build_news_snapshot(
    result: IngestResult,
    *,
    now: datetime,
    requested_as_of: datetime,
    data_state: str,
    expires_at: datetime | None = None,
    issuer_by_company: dict[str, str] | None = None,
) -> dict:
    """Reviewed batch -> snapshot. Empty publishable set stays NOT_AVAILABLE."""
    now = _aware(now, "now")
    requested_as_of = _aware(requested_as_of, "requested_as_of")
    if data_state not in _STATES or data_state == "NOT_AVAILABLE":
        raise IngestError("DATA_STATE", "batch data_state must be LIVE, FROZEN_SNAPSHOT, or DEMO")
    included = tuple(item for item in result.accepted if item.available_at <= requested_as_of)
    if not included:
        code = "NO_ITEMS_AT_AS_OF" if result.accepted else "NO_PUBLISHABLE_ITEMS" if result.rejected else "NEWS_NO_SOURCE"
        reason = {
            "NO_ITEMS_AT_AS_OF": "No normalized news was available at requested_as_of.",
            "NO_PUBLISHABLE_ITEMS": "Every supplied news item was rejected.",
            "NEWS_NO_SOURCE": "No news provider is activated. Ingestion does not fetch.",
        }[code]
        return unavailable_news_snapshot(
            generated_at=now, requested_as_of=requested_as_of, reason_code=code, reason=reason,
        )
    as_of = max(item.available_at for item in included)
    if as_of > now:
        raise IngestError("FUTURE", "snapshot as_of is later than the evaluation clock")
    synthetic = any(item.synthetic for item in included)
    if synthetic and data_state != "DEMO":
        raise IngestError("DATA_STATE", "synthetic news may only be published as DEMO")
    if data_state == "DEMO" and not synthetic:
        raise IngestError("DATA_STATE", "DEMO is only for items explicitly marked synthetic")
    if data_state == "LIVE":
        expires_at = _aware(expires_at, "expires_at") if expires_at is not None else None
        if expires_at is None:
            raise IngestError("EXPIRES_AT_REQUIRED", "LIVE news requires a caller-supplied expires_at; no TTL is defined")
        if expires_at <= as_of:
            raise IngestError("TIME_ORDER", "expires_at must be later than as_of")
    elif expires_at is not None:
        raise IngestError("DATA_STATE", "expires_at is only meaningful for LIVE")
    cards = [
        _card(item, issuer_ids_for(item, issuer_by_company))
        for item in sorted(included, key=lambda item: (item.available_at, item.normalized_id))
    ]
    inputs = [
        {"artifact_id": f"newsraw:{item.raw_hash}", "sha256": item.raw_hash, "bytes": item.raw_bytes}
        for item in sorted(included, key=lambda item: item.raw_hash)
    ]
    # One input per raw hash. Included items are canonical, so hashes are unique
    # unless two different mappings share a hash, which dedup already rejects.
    if len({i["artifact_id"] for i in inputs}) != len(inputs):
        raise IngestError("CONFLICT", "duplicate raw artifact in one snapshot")
    source = "rig.news_ingest:" + ",".join(sorted({item.source for item in included}))
    checks = [
        "time_order:published_at<=available_at<=fetched_at",
        "future:rejected",
        f"exact_duplicates:{len(result.exact_duplicates)}",
        "entity_match:ENTITY_MATCH_V1",
        f"semantic_grouping:{SEMANTIC_GROUPING}",
        "sentiment:not_defined",
        "consensus:NOT_AVAILABLE",
        "display_locale:not_applied",
    ]
    return _snapshot(
        data_state=data_state,
        generated_at=now,
        requested_as_of=requested_as_of,
        as_of=as_of,
        expires_at=expires_at,
        data=cards,
        inputs=inputs,
        source=source,
        reason=None,
        reason_code=None,
        synthetic=synthetic,
        checks=checks,
        validation_status="PASS",
    )
