"""RESEARCH_INVALIDATION_EVENT_V1.

Append-only evidence events and one supersedes-chain resolver.
Does not issue a grant, read freshness, revoke a grant, or import a producer engine.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..producers.serialization import canonical_sha256

CONTRACT = "RESEARCH_INVALIDATION_EVENT_V1"
SCHEMA_VERSION = 1
STATES = ("CLEAR", "SUSPENDED", "INVALIDATED")
RESOLUTIONS = ("UNSTATED", "CLEAR", "SUSPENDED", "INVALIDATED", "AMBIGUOUS", "INVALID_CHAIN")
_REASONS = {
    "CLEAR": frozenset({"EXPLICIT_CLEAR"}),
    "SUSPENDED": frozenset({"HOLD_PENDING_REVIEW"}),
    "INVALIDATED": frozenset({
        "EVIDENCE_SUPERSEDED",
        "LINEAGE_NO_LONGER_CURRENT",
        "INTEGRITY_FAILURE",
    }),
}
_KEYS = frozenset({
    "contract",
    "schema_version",
    "target_sha256",
    "state",
    "reason_code",
    "effective_at",
    "available_at",
    "supersedes",
    "authority_ref",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class InvalidationContractError(ValueError):
    code = "INVALIDATION_CONTRACT"

    def __init__(self, message: str):
        super().__init__(f"{self.code}: {message}")


def event_id(event: dict) -> str:
    """Id is the canonical sha256 of the body. The id is not a field of the body."""
    return canonical_sha256(validate_event(event))


def validate_event(event: object) -> dict:
    """Return a copy of one event body. Does not rewrite timestamp text."""
    if not isinstance(event, dict) or set(event) != _KEYS:
        raise InvalidationContractError("event keys are not the v1 set")
    if event.get("contract") != CONTRACT or event.get("schema_version") != SCHEMA_VERSION:
        raise InvalidationContractError("event contract is not RESEARCH_INVALIDATION_EVENT_V1")
    state = event.get("state")
    reason = event.get("reason_code")
    if state not in _REASONS or reason not in _REASONS[state]:
        raise InvalidationContractError("state and reason_code are not an admitted pair")
    target = event.get("target_sha256")
    if not isinstance(target, str) or not _HEX64.match(target):
        raise InvalidationContractError("target_sha256 must be 64 lowercase hex")
    supersedes = event.get("supersedes")
    if supersedes is not None and (not isinstance(supersedes, str) or not _HEX64.match(supersedes)):
        raise InvalidationContractError("supersedes must be null or 64 lowercase hex")
    if not isinstance(event.get("authority_ref"), str) or not event["authority_ref"].strip():
        raise InvalidationContractError("authority_ref is required")
    _aware(event.get("effective_at"), "effective_at")
    _aware(event.get("available_at"), "available_at")
    return {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "target_sha256": target,
        "state": state,
        "reason_code": reason,
        "effective_at": event["effective_at"],
        "available_at": event["available_at"],
        "supersedes": supersedes,
        "authority_ref": event["authority_ref"],
    }


def admit(existing: tuple | list, event: dict) -> tuple:
    """Append one event. Reject a duplicate, a missing or cross-target predecessor,
    a self-supersedes, and any successor of INVALIDATED. Does not sort."""
    body = validate_event(event)
    ident = canonical_sha256(body)
    rows = tuple(validate_event(item) for item in existing)
    known = {canonical_sha256(item): item for item in rows}
    if len(known) != len(rows) or ident in known:
        raise InvalidationContractError("duplicate invalidation event")
    predecessor = body["supersedes"]
    if predecessor is not None:
        if predecessor == ident:
            raise InvalidationContractError("event supersedes itself")
        if predecessor not in known:
            raise InvalidationContractError("missing predecessor")
        prior = known[predecessor]
        if prior["target_sha256"] != body["target_sha256"]:
            raise InvalidationContractError("cross-target supersedes")
        if prior["state"] == "INVALIDATED":
            raise InvalidationContractError("INVALIDATED is terminal")
    return rows + (body,)


def resolve_target(events: tuple | list, target_sha256: str, decision_time: datetime) -> dict:
    """Resolve one target at decision_time. Timestamp order never selects the head."""
    if not isinstance(target_sha256, str) or not _HEX64.match(target_sha256):
        raise InvalidationContractError("target_sha256 must be 64 lowercase hex")
    clock = _require_clock(decision_time)
    visible = _visible(events, clock)
    indexed, defect = _index(visible)
    if defect is not None:
        return _chain(defect)
    return _resolve_indexed(indexed, target_sha256)


def _visible(events: tuple | list, clock: datetime) -> list[dict]:
    rows = []
    for item in events:
        body = validate_event(item)
        if _aware(body["available_at"], "available_at") <= clock:
            rows.append(body)
    return rows


def _index(rows: list[dict]) -> tuple[dict, str | None]:
    indexed = {}
    for body in rows:
        ident = canonical_sha256(body)
        if ident in indexed:
            return {}, "duplicate_event"
        indexed[ident] = body
    return indexed, None


def _resolve_indexed(indexed: dict, target: str) -> dict:
    group = {ident: body for ident, body in indexed.items() if body["target_sha256"] == target}
    if not group:
        return {"resolution": "UNSTATED", "event_id": None, "defect": None}
    children = {ident: [] for ident in group}
    for ident, body in group.items():
        predecessor = body["supersedes"]
        if predecessor is None:
            continue
        if predecessor == ident or predecessor not in indexed:
            return _chain("missing_predecessor" if predecessor != ident else "cycle")
        if indexed[predecessor]["target_sha256"] != target:
            return _chain("cross_target")
        children[predecessor].append(ident)
    if _cycle(children):
        return _chain("cycle")
    if any(len(item) > 1 for item in children.values()):
        return _chain("branching")
    tips = [ident for ident in group if not children[ident]]
    if len(tips) != 1:
        return _chain("multiple_heads")
    path = []
    seen = set()
    cursor = tips[0]
    while cursor is not None:
        if cursor in seen or cursor not in group:
            return _chain("cycle")
        seen.add(cursor)
        path.append(cursor)
        cursor = group[cursor]["supersedes"]
    if len(seen) != len(group):
        return _chain("multiple_heads")
    chain = list(reversed(path))
    if any(group[ident]["state"] == "INVALIDATED" for ident in chain[:-1]):
        return _chain("invalidated_successor")
    instants = [_aware(group[ident]["effective_at"], "effective_at") for ident in chain]
    if len(set(instants)) != len(instants):
        return {"resolution": "AMBIGUOUS", "event_id": None, "defect": "equal_effective_at"}
    head = tips[0]
    return {"resolution": group[head]["state"], "event_id": head, "defect": None}


def _cycle(children: dict) -> bool:
    color = {ident: 0 for ident in children}

    def walk(ident: str) -> bool:
        color[ident] = 1
        for child in children[ident]:
            if color[child] == 1 or (color[child] == 0 and walk(child)):
                return True
        color[ident] = 2
        return False

    return any(walk(ident) for ident in children if color[ident] == 0)


def _chain(defect: str) -> dict:
    return {"resolution": "INVALID_CHAIN", "event_id": None, "defect": defect}


def _aware(text: object, where: str) -> datetime:
    if not isinstance(text, str) or not text.strip():
        raise InvalidationContractError(f"{where} is required")
    raw = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidationContractError(f"{where} is not an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidationContractError(f"{where} must be timezone-aware")
    return parsed


def _require_clock(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidationContractError("decision_time must be timezone-aware")
    return value
