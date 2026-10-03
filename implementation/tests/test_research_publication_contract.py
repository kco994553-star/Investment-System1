"""One research-publication predicate for QGV, Macro, Leaderboard, and Technical.

Does not add a schema-1 state, a ranking rule, or a QGV-only exception.
Counterexamples are the paths that would bypass Track C or emit LIVE/OFFICIAL.
"""

from __future__ import annotations

import ast
import inspect

import pytest

from investment_system.leaderboard_producer.rank import PUBLICATION
from investment_system.leaderboard_producer.research_publication import (
    HYPOTHETICAL_RESEARCH_STATE,
    OFFICIAL_LABEL,
    PROBE,
    PUBLISHED_STATES,
    SCHEMA1_STATES,
    PublicationProbeError,
    current_publication,
    forbidden_producer_pass_becomes_live,
    forbidden_research_label_becomes_official,
    forbidden_track_c_copied_from_producer_pass,
    hypothetical_research_label,
    qgv_only_exception_would_publish,
    real_cases,
    request_publication,
    track_c_attestation_accepted,
)

CASES = real_cases()
PINS = {
    "qgv": "5eec129ef81641f0bc11f5adbb43d0b2122ee24b",
    "macro": "61d3352d5d68c7830e924f17613598ca79fcec6f",
    "leaderboard": "1f6b2d2f020843b13222b66a3f9bce82cded5bef",
    "technical": "ce587040e7beb31b66a423eab6ca89767f2a2cf8",
}


def _assert_closed(decision: dict) -> None:
    assert decision["probe"] == PROBE
    assert decision["data_state"] not in PUBLISHED_STATES
    assert decision["data_state"] != OFFICIAL_LABEL
    assert decision["official"] is False
    assert decision["live"] is False
    assert decision["track_c_validated"] is False
    assert decision["producer_validation_is_track_c"] is False
    assert "TRACK_C_VALIDATION_NOT_COMPLETE" in decision["reasons"]


def test_schema1_has_no_research_state():
    assert HYPOTHETICAL_RESEARCH_STATE not in SCHEMA1_STATES
    assert PUBLICATION["data_state"] == "NOT_AVAILABLE"
    assert PUBLICATION["official"] is False and PUBLICATION["live"] is False


def test_four_real_cases_share_one_not_available_decision():
    decisions = {name: current_publication(case) for name, case in CASES.items()}
    assert set(decisions) == {"qgv", "macro", "leaderboard", "technical"}
    for name, decision in decisions.items():
        _assert_closed(decision)
        assert decision["data_state"] == "NOT_AVAILABLE"
        assert decision["research_state_added"] is False
        assert decision["p01"] == "NOT_APPROVED"
        assert decision["data_completeness"] == CASES[name]["data_completeness"]
        assert CASES[name]["pin"] == PINS[name]
    assert decisions["leaderboard"]["within_tie_order"] == "POLICY_BLOCKED"
    assert decisions["qgv"]["producer_validation"] == "PASS"
    assert decisions["technical"]["producer_validation"] == "NOT_RUN"


def test_producer_name_is_not_an_input():
    source = inspect.getsource(current_publication) + inspect.getsource(hypothetical_research_label)
    tree = ast.parse(source)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "producer_id" not in names
    for name, case in CASES.items():
        renamed = dict(case)
        renamed["producer_id"] = "qgv" if name != "qgv" else "not-qgv"
        assert current_publication(renamed) == current_publication(case)


def test_qgv_token_is_not_the_only_blocked_lifecycle():
    assert CASES["qgv"]["methodology_lifecycle"] == "PROVISIONAL_RESEARCH"
    assert CASES["macro"]["methodology_lifecycle"] == "PROVISIONAL"
    assert CASES["technical"]["methodology_lifecycle"] is None
    assert "m1:APPROVED" in CASES["technical"]["component_labels"]
    assert qgv_only_exception_would_publish(CASES["macro"], "LIVE") is True
    assert qgv_only_exception_would_publish(CASES["macro"], "FROZEN_SNAPSHOT") is True
    assert qgv_only_exception_would_publish(CASES["technical"], "LIVE") is True
    assert qgv_only_exception_would_publish(CASES["qgv"], "LIVE") is False
    with pytest.raises(PublicationProbeError, match="RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE"):
        request_publication(CASES["macro"], "FROZEN_SNAPSHOT")
    with pytest.raises(PublicationProbeError, match="RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE"):
        request_publication(CASES["qgv"], "LIVE")
    with pytest.raises(PublicationProbeError, match="RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE"):
        request_publication(CASES["technical"], "LIVE")


def test_producer_validation_pass_is_not_data_state_or_track_c():
    for name in ("qgv", "leaderboard", "macro"):
        case = CASES[name]
        assert case["producer_validation"] == "PASS"
        decision = current_publication(case)
        assert decision["data_state"] == "NOT_AVAILABLE"
        assert decision["track_c_validated"] is False
        assert forbidden_producer_pass_becomes_live(case) == "LIVE"
        assert forbidden_track_c_copied_from_producer_pass(case) is True
        with pytest.raises(PublicationProbeError, match="TRACK_C_REQUIRED|RESEARCH_LIFECYCLE"):
            request_publication(case, "LIVE")


def test_data_completeness_is_not_the_publication_state():
    assert CASES["technical"]["data_completeness"] == "FEATURE_OR_SCENARIO_NOT_AVAILABLE"
    assert CASES["leaderboard"]["data_completeness"] != current_publication(CASES["leaderboard"])["data_state"]
    filled = dict(CASES["leaderboard"])
    filled["data_completeness"] = "READY"
    assert current_publication(filled)["data_state"] == "NOT_AVAILABLE"
    assert current_publication(filled)["track_c_validated"] is False


def test_research_label_if_enabled_does_not_promote_or_bypass_track_c():
    for case in CASES.values():
        with pytest.raises(PublicationProbeError, match="P01_NOT_APPROVED"):
            hypothetical_research_label(case, enabled=False)
    qgv = hypothetical_research_label(CASES["qgv"], enabled=True)
    board = hypothetical_research_label(CASES["leaderboard"], enabled=True)
    for decision in (qgv, board):
        _assert_closed(decision)
        assert decision["data_state"] == HYPOTHETICAL_RESEARCH_STATE
        assert decision["research_state_added"] is True
        assert decision["producer_validation"] == "PASS"
    assert board["within_tie_order"] == "POLICY_BLOCKED"
    macro = hypothetical_research_label(CASES["macro"], enabled=True)
    technical = hypothetical_research_label(CASES["technical"], enabled=True)
    for decision in (macro, technical):
        _assert_closed(decision)
        assert decision["data_state"] == "NOT_AVAILABLE"
        assert "RESEARCH_LABEL_WITHHELD" in decision["reasons"]


def test_forged_track_c_flag_and_research_label_cannot_become_live_or_official():
    forged = dict(CASES["qgv"])
    forged["track_c_validation"] = "PASS"
    forged["track_c_attestation"] = {"issuer": "track_c", "id": "self-issued", "track_c_validated": True}
    assert track_c_attestation_accepted(forged["track_c_attestation"]) is False
    decision = current_publication(forged)
    _assert_closed(decision)
    labeled = hypothetical_research_label(forged, enabled=True)
    _assert_closed(labeled)
    assert labeled["data_state"] == HYPOTHETICAL_RESEARCH_STATE
    with pytest.raises(PublicationProbeError, match="OFFICIAL_PROMOTION_FORBIDDEN"):
        request_publication(forged, "OFFICIAL", research_state_enabled=True)
    with pytest.raises(PublicationProbeError, match="RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE"):
        request_publication(forged, "LIVE", research_state_enabled=True)
    stripped = dict(forged)
    stripped["methodology_lifecycle"] = "VALIDATED"
    stripped["research_record_exists"] = False
    stripped["policy_blockers"] = ()
    with pytest.raises(PublicationProbeError, match="TRACK_C_REQUIRED"):
        request_publication(stripped, "LIVE", research_state_enabled=True)
    with pytest.raises(PublicationProbeError, match="COMPONENT_LABEL_IS_NOT_TRACK_C"):
        request_publication(
            {
                **stripped,
                "component_labels": CASES["technical"]["component_labels"],
                "track_c_attestation": None,
                "track_c_validation": "NOT_RUN",
            },
            "FROZEN_SNAPSHOT",
        )
    with pytest.raises(PublicationProbeError, match="OFFICIAL_PROMOTION_FORBIDDEN"):
        request_publication(CASES["technical"], "LIVE_OFFICIAL", research_state_enabled=True)
    assert forbidden_research_label_becomes_official(CASES["technical"]) == OFFICIAL_LABEL
    assert forbidden_research_label_becomes_official(CASES["leaderboard"]) == OFFICIAL_LABEL


def test_synthetic_cannot_use_research_or_live():
    synthetic = dict(CASES["qgv"])
    synthetic["synthetic"] = True
    with pytest.raises(PublicationProbeError, match="SYNTHETIC_IS_NOT_RESEARCH"):
        hypothetical_research_label(synthetic, enabled=True)
    demo = request_publication(synthetic, "DEMO")
    assert demo["data_state"] == "DEMO"
    assert demo["official"] is False and demo["live"] is False and demo["track_c_validated"] is False
    with pytest.raises(PublicationProbeError, match="RESEARCH_LIFECYCLE_NOT_PUBLISHED_STATE"):
        request_publication(synthetic, "LIVE")


def test_leaderboard_publication_constant_unchanged_by_probe():
    assert PUBLICATION == {
        "data_state": "NOT_AVAILABLE",
        "reason_code": "LEADERBOARD_RESEARCH_ONLY_NO_EXPORT",
        "official": False,
        "live": False,
    }
    decision = current_publication(CASES["leaderboard"])
    assert decision["within_tie_order"] == "POLICY_BLOCKED"
    assert "WITHIN_TIE_ORDER_POLICY_BLOCKED" in CASES["leaderboard"]["policy_blockers"]
