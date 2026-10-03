"""Eligibility facts copied from a persisted record. Not a new score."""

from __future__ import annotations

import re

from .errors import ExtractionError

FACT_KEYS = (
    "subject_sha256",
    "persisted_fingerprint",
    "methodology_lifecycle",
    "producer_validation",
    "track_c_validation",
    "track_c_claim_ignored",
    "data_completeness",
    "research_record_exists",
    "research_bytes_withheld",
    "synthetic",
    "stale_or_expired",
    "policy_blockers",
    "component_labels",
    "within_tie_order",
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_VALIDATION = frozenset({"PASS", "FAIL", "NOT_RUN"})
_COMPLETENESS = frozenset({"READY", "PARTIAL", "BLOCKED"})


def make_fact(**fields: object) -> dict:
    if set(fields) != set(FACT_KEYS):
        raise ExtractionError("eligibility fact keys are not the v1 set")
    subject = fields["subject_sha256"]
    fingerprint = fields["persisted_fingerprint"]
    if not isinstance(subject, str) or not _HEX64.match(subject):
        raise ExtractionError("subject_sha256 must be a persisted 64 lowercase hex")
    if fingerprint != subject:
        raise ExtractionError("persisted fingerprint must be the same stored hash, not a new one")
    lifecycle = fields["methodology_lifecycle"]
    if lifecycle is not None and not isinstance(lifecycle, str):
        raise ExtractionError("methodology_lifecycle must be a string or null")
    if fields["producer_validation"] not in _VALIDATION:
        raise ExtractionError("producer_validation must be PASS, FAIL, or NOT_RUN")
    if fields["track_c_validation"] != "NOT_RUN":
        raise ExtractionError("this layer cannot record Track C as PASS or FAIL")
    if not isinstance(fields["track_c_claim_ignored"], bool):
        raise ExtractionError("track_c_claim_ignored must be a boolean")
    if fields["data_completeness"] not in _COMPLETENESS:
        raise ExtractionError("data_completeness must be READY, PARTIAL, or BLOCKED")
    for flag in ("research_record_exists", "research_bytes_withheld", "synthetic", "stale_or_expired"):
        if not isinstance(fields[flag], bool):
            raise ExtractionError(f"{flag} must be a boolean")
    blockers = fields["policy_blockers"]
    labels = fields["component_labels"]
    if not isinstance(blockers, tuple) or not all(isinstance(item, str) for item in blockers):
        raise ExtractionError("policy_blockers must be a tuple of strings")
    if not isinstance(labels, tuple) or not all(isinstance(item, str) for item in labels):
        raise ExtractionError("component_labels must be a tuple of strings")
    tie = fields["within_tie_order"]
    if tie is not None and not isinstance(tie, str):
        raise ExtractionError("within_tie_order must be a string or null")
    return {key: fields[key] for key in FACT_KEYS}
