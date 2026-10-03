"""Export a Technical section as PRODUCER_SNAPSHOT v1 NOT_AVAILABLE.

This matches producers.contract.not_available on feature/producer-infrastructure-v1
(PR #9 @ 6fe9eee) for the technical section. It does not define a second snapshot
schema, does not import TechnicalEngine, and does not rescore.
Canonical does not contain the producers package, so this is the compatibility
adapter. Publication of LIVE, DEMO, or FROZEN_SNAPSHOT technical data is refused.
"""

from __future__ import annotations

from datetime import datetime

from .errors import PublicationError, SyntheticLiveError, TechnicalProducerError
from .producer import BLOCKER, PRODUCER_ID, PRODUCER_VERSION, PUBLISHED_REASON, REASON_CODE

PRODUCER_SNAPSHOT = "PRODUCER_SNAPSHOT"
SCHEMA_VERSION = 1


def _aware_iso(value: datetime, label: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TechnicalProducerError(f"{label} must be a timezone-aware datetime")
    return value.isoformat()


def export_producer_snapshot(
    *,
    requested_as_of: datetime,
    generated_at: datetime,
    data_state: str = "NOT_AVAILABLE",
) -> dict:
    """Web section envelope. data is always null. Engine is not called."""
    if data_state == "LIVE":
        raise SyntheticLiveError("placeholder Technical output cannot be published as LIVE")
    if data_state != "NOT_AVAILABLE":
        raise PublicationError(f"{data_state} is not publishable while the Technical model is POLICY_BLOCKED")
    return {
        "contract": PRODUCER_SNAPSHOT,
        "schema_version": SCHEMA_VERSION,
        "producer_id": PRODUCER_ID,
        "producer_version": PRODUCER_VERSION,
        "section": "technical",
        "data_state": "NOT_AVAILABLE",
        "requested_as_of": _aware_iso(requested_as_of, "requested_as_of"),
        "as_of": None,
        "generated_at": _aware_iso(generated_at, "generated_at"),
        "expires_at": None,
        "usable_until": None,
        "methodology": {
            "id": "NONE",
            "version": "NONE",
            "status": "NOT_AVAILABLE",
            "blocker": BLOCKER,
        },
        "synthetic": False,
        "provenance": {"source": None, "inputs": []},
        "validation": {"status": "NOT_RUN", "checks": []},
        "scope": {"kind": "DOCUMENT", "entity_ids": None},
        "data": None,
        "data_sha256": None,
        "reason": PUBLISHED_REASON,
        "reason_code": REASON_CODE,
    }
