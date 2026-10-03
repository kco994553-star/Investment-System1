"""Common research-publication probe. Not a publisher and not a ranking change.

P01 is not approved, so schema-1 gains no RESEARCH data state here. The probe
only answers two questions, with one predicate and no producer-name switch:

1. Do the four real candidates (QGV PR #10, Macro PR #12, Leaderboard PR #14,
   Technical PR #15) already share one publication decision?
2. If a RESEARCH data state were added later, can that label bypass Track C
   or become LIVE / OFFICIAL by itself?

Axes that must stay separate (collapsing any two is a promotion bug):

- data_state: what a Web bundle may render (schema-1 only, today).
- producer_validation: mechanical PASS / FAIL / NOT_RUN (persistence, PIT,
  lineage). This is not Track C and not an Official label.
- methodology_lifecycle: domain status copied verbatim. Every research-class
  token blocks LIVE and FROZEN_SNAPSHOT. PROVISIONAL_RESEARCH is not special.
- track_c_validation: external. This module cannot mint or accept it.
- data_completeness: READY / PARTIAL / BLOCKED, a missing feature, or a
  scenario that is NOT_AVAILABLE. Not a Web state and not filled here.
- policy facts: withheld bytes, within-tie POLICY_BLOCKED, and similar.
  They are inputs. They are not new eligibility, tie-break, ranking,
  consensus, scenario, or reassessment rules.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

PROBE = "RESEARCH_PUBLICATION_PROBE"
PROBE_VERSION = 1
P01 = "NOT_APPROVED"
SCHEMA1_STATES = frozenset({"LIVE", "FROZEN_SNAPSHOT", "DEMO", "NOT_AVAILABLE"})
PUBLISHED_STATES = frozenset({"LIVE", "FROZEN_SNAPSHOT"})
# Same set Producer Infrastructure already uses (contract.RESEARCH_STATUSES).
# Copied as an observation. PR #9 is not edited. Not a QGV-only list.
RESEARCH_LIFECYCLE = frozenset({
    "PROVISIONAL_RESEARCH",
    "IDEA",
    "RESEARCH",
    "PROVISIONAL",
    "PROVISIONAL_INITIAL_PRIOR",
})
HYPOTHETICAL_RESEARCH_STATE = "RESEARCH"  # not in SCHEMA1_STATES; tests only
OFFICIAL_LABEL = "OFFICIAL"


class PublicationProbeError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _closed(**fields: Any) -> dict:
    decision = {
        "probe": PROBE,
        "data_state": "NOT_AVAILABLE",
        "official": False,
        "live": False,
        "track_c_validated": False,
        "producer_validation_is_track_c": False,
        "research_state_added": False,
        "p01": P01,
    }
    decision.update(fields)
    if decision["data_state"] in PUBLISHED_STATES or decision["data_state"] == OFFICIAL_LABEL:
        raise PublicationProbeError("PROMOTION_FORBIDDEN", "probe must not emit LIVE, FROZEN_SNAPSHOT, or OFFICIAL")
    if decision["official"] or decision["live"] or decision["track_c_validated"]:
        raise PublicationProbeError("PROMOTION_FORBIDDEN", "probe must not set official, live, or track_c_validated")
    if decision["data_state"] == HYPOTHETICAL_RESEARCH_STATE and not decision["research_state_added"]:
        raise PublicationProbeError("P01_NOT_APPROVED", "RESEARCH data state is not in schema-1")
    return decision


def track_c_attestation_accepted(_attestation: Mapping | None) -> bool:
    """Always false. A producer validation PASS is not an attestation, and this probe cannot check one."""
    return False


def current_publication(case: Mapping) -> dict:
    """Approved contract today. One function for every producer. Always NOT_AVAILABLE.

    `producer_id` is not read. Renaming a case must not change the decision.
    `data_completeness` is not read. Coverage and missing features stay on their own axis.
    """
    reasons = ["P01_RESEARCH_DATA_STATE_NOT_APPROVED"]
    if case["methodology_lifecycle"] in RESEARCH_LIFECYCLE or case.get("research_record_exists"):
        reasons.append("METHODOLOGY_LIFECYCLE_NOT_PUBLISHABLE")
    if case.get("track_c_validation") != "PASS" or not track_c_attestation_accepted(case.get("track_c_attestation")):
        reasons.append("TRACK_C_VALIDATION_NOT_COMPLETE")
    if case.get("producer_validation") != "PASS":
        reasons.append("PRODUCER_VALIDATION_NOT_PASS")
    if case.get("policy_blockers"):
        reasons.append("POLICY_BLOCKED")
    if case.get("research_bytes_withheld"):
        reasons.append("RESEARCH_BYTES_WITHHELD")
    if case.get("synthetic"):
        reasons.append("SYNTHETIC_NOT_LIVE")
    return _closed(
        data_state="NOT_AVAILABLE",
        reasons=tuple(reasons),
        producer_validation=case.get("producer_validation"),
        methodology_lifecycle=case.get("methodology_lifecycle"),
        data_completeness=case.get("data_completeness"),
        within_tie_order=case.get("within_tie_order"),
    )


def hypothetical_research_label(case: Mapping, *, enabled: bool) -> dict:
    """What a later P01 option B would still be forbidden from doing.

    `enabled=True` is a test switch. It does not add RESEARCH to schema-1 and
    it does not publish. The label, when allowed, is not LIVE and not OFFICIAL,
    and it leaves Track C false. Withheld bytes stay NOT_AVAILABLE even if the
    caller asks for the label — that uses a fact on the case, not the producer name.
    """
    if not enabled:
        raise PublicationProbeError("P01_NOT_APPROVED", "RESEARCH data state is not approved")
    if case.get("synthetic"):
        raise PublicationProbeError("SYNTHETIC_IS_NOT_RESEARCH", "synthetic output cannot use a research label")
    if case["methodology_lifecycle"] not in RESEARCH_LIFECYCLE and not case.get("research_record_exists"):
        raise PublicationProbeError("NOT_A_RESEARCH_RECORD", "research label requires a research lifecycle or record")
    base = current_publication(case)
    if case.get("research_bytes_withheld"):
        return _closed(**{**base, "reasons": base["reasons"] + ("RESEARCH_LABEL_WITHHELD",)})
    return _closed(
        **{
            **base,
            "data_state": HYPOTHETICAL_RESEARCH_STATE,
            "research_state_added": True,
            "reasons": tuple(r for r in base["reasons"] if r != "P01_RESEARCH_DATA_STATE_NOT_APPROVED"),
        }
    )


def request_publication(case: Mapping, requested: str, *, research_state_enabled: bool = False) -> dict:
    """Fail closed on every promotion request. There is no success path to LIVE or OFFICIAL."""
    if requested in {OFFICIAL_LABEL, "LIVE_OFFICIAL", "VALIDATED"}:
        raise PublicationProbeError("OFFICIAL_PROMOTION_FORBIDDEN", f"{requested} is not granted by a data state")
    if requested in PUBLISHED_STATES:
        lifecycle = case.get("methodology_lifecycle")
        if lifecycle in RESEARCH_LIFECYCLE or case.get("research_record_exists"):
            raise PublicationProbeError(
                "RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE",
                f"{lifecycle!r} cannot be published as {requested}",
            )
        if case.get("component_labels"):
            raise PublicationProbeError(
                "COMPONENT_LABEL_IS_NOT_TRACK_C",
                "feature or phase labels such as m1/m2 APPROVED are not Track C and not LIVE",
            )
        if not track_c_attestation_accepted(case.get("track_c_attestation")):
            raise PublicationProbeError("TRACK_C_REQUIRED", "Track C attestation is not accepted by this probe")
        raise PublicationProbeError("PROMOTION_NOT_OWNED_HERE", "this probe does not emit a published state")
    if requested == HYPOTHETICAL_RESEARCH_STATE:
        return hypothetical_research_label(case, enabled=research_state_enabled)
    if requested == "DEMO":
        if not case.get("synthetic"):
            raise PublicationProbeError("DEMO_REQUIRES_SYNTHETIC", "real research bytes are not DEMO")
        return _closed(data_state="DEMO", reasons=("SYNTHETIC_DEMO_ONLY",), producer_validation=case.get("producer_validation"))
    if requested == "NOT_AVAILABLE":
        return current_publication(case)
    raise PublicationProbeError("UNSUPPORTED_STATE", f"{requested!r} is not a schema-1 state")


def qgv_only_exception_would_publish(case: Mapping, requested: str) -> bool:
    """Counterexample detector. A gate that blocks only PROVISIONAL_RESEARCH is not the common contract.

    Macro's lifecycle is PROVISIONAL. That gate would let a LIVE/FROZEN request through
    the lifecycle check. The common contract must report that as non-compliant.
    """
    if requested not in PUBLISHED_STATES:
        return False
    token = case.get("methodology_lifecycle")
    blocked_by_qgv_token_only = token == "PROVISIONAL_RESEARCH"
    still_research = token in RESEARCH_LIFECYCLE or bool(case.get("research_record_exists"))
    return still_research and not blocked_by_qgv_token_only


def forbidden_producer_pass_becomes_live(case: Mapping) -> str:
    """The promotion bug. Returned so tests can show the safe gate rejects it."""
    if case.get("producer_validation") == "PASS":
        return "LIVE"
    return "NOT_AVAILABLE"


def forbidden_research_label_becomes_official(case: Mapping) -> str:
    if case["methodology_lifecycle"] in RESEARCH_LIFECYCLE or case.get("research_record_exists"):
        return OFFICIAL_LABEL
    return "NOT_AVAILABLE"


def forbidden_track_c_copied_from_producer_pass(case: Mapping) -> bool:
    return case.get("producer_validation") == "PASS"


def real_cases() -> Mapping[str, Mapping]:
    """Facts observed on the pinned HEADs. Not a replay and not a new score.

    Pins are the branch tips verified 2026-10-02. They are read-only.
    """
    qgv = {
        "pr": 10,
        "pin": "5eec129ef81641f0bc11f5adbb43d0b2122ee24b",
        "methodology_lifecycle": "PROVISIONAL_RESEARCH",
        "producer_validation": "PASS",
        "track_c_validation": "NOT_RUN",
        "track_c_attestation": None,
        "data_completeness": "PARTIAL_OR_BLOCKED_READY_0",
        "research_record_exists": True,
        "research_bytes_withheld": False,
        "synthetic": False,
        "policy_blockers": ("P01_RESEARCH_DATA_STATE_NOT_APPROVED", "TRACK_C_VALIDATION_NOT_COMPLETE"),
        "within_tie_order": None,
        "pass_means": "PERSISTENCE_PIT_LINEAGE_RESEARCH_STATE_NOT_FULLY_SCORED",
    }
    macro = {
        "pr": 12,
        "pin": "61d3352d5d68c7830e924f17613598ca79fcec6f",
        "methodology_lifecycle": "PROVISIONAL",
        "producer_validation": "PASS",
        "track_c_validation": "NOT_RUN",
        "track_c_attestation": None,
        "data_completeness": "RESEARCH_SNAPSHOT_NOT_WEB_PAYLOAD",
        "research_record_exists": True,
        "research_bytes_withheld": True,
        "synthetic": False,
        "policy_blockers": (
            "SERIES_MAPPING_PROVISIONAL",
            "EXPOSURE_NOT_APPROVED",
            "WEB_INDICATORS_NOT_RESHAPED",
            "NO_APPROVED_LIVE_EXPIRY",
        ),
        "within_tie_order": None,
        "pass_means": "PIT_VINTAGE_AND_UNCHANGED_ENGINE_NOT_WEB_LIVE",
    }
    leaderboard = {
        "pr": 14,
        "pin": "1f6b2d2f020843b13222b66a3f9bce82cded5bef",
        "methodology_lifecycle": "PROVISIONAL_RESEARCH",
        "producer_validation": "PASS",
        "track_c_validation": "NOT_RUN",
        "track_c_attestation": None,
        "data_completeness": "READY_0_PARTIAL_AND_BLOCKED_PRESERVED",
        "research_record_exists": True,
        "research_bytes_withheld": False,
        "synthetic": False,
        "policy_blockers": (
            "P01_RESEARCH_DATA_STATE_NOT_APPROVED",
            "TRACK_C_VALIDATION_NOT_COMPLETE",
            "WITHIN_TIE_ORDER_POLICY_BLOCKED",
        ),
        "within_tie_order": "POLICY_BLOCKED",
        "pass_means": "PERSISTENCE_IDENTITY_LINEAGE_EXISTING_RANKING_CONTRACT_ONLY",
    }
    technical = {
        "pr": 15,
        "pin": "ce587040e7beb31b66a423eab6ca89767f2a2cf8",
        "methodology_lifecycle": None,
        "producer_validation": "NOT_RUN",
        "track_c_validation": "NOT_RUN",
        "track_c_attestation": None,
        "data_completeness": "FEATURE_OR_SCENARIO_NOT_AVAILABLE",
        "research_record_exists": True,
        "research_bytes_withheld": True,
        "synthetic": False,
        "component_labels": ("m1:APPROVED", "m2:APPROVED", "m3:NOT_APPROVED"),
        "policy_blockers": ("P01_DECISION_REQUIRED", "M3_NOT_APPROVED", "SESSION_CONTINUITY_UNVERIFIED"),
        "within_tie_order": None,
        "pass_means": "M1_M2_RESEARCH_RECORD_ONLY_REAL_RESEARCH_PRODUCER_READY_NO",
        "real_research_producer_ready": False,
    }
    return MappingProxyType({
        "qgv": MappingProxyType(qgv),
        "macro": MappingProxyType(macro),
        "leaderboard": MappingProxyType(leaderboard),
        "technical": MappingProxyType(technical),
    })
