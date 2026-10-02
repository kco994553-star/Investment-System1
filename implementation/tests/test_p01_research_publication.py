"""P01 phase 1. Grants stay empty. Schema-1 stays schema-1. No engine is called."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system.product.web_mvp import SECTIONS, STATES, validate_bundle
from investment_system.producers.assembler import assemble_bundle
from investment_system.producers.contract import make_snapshot, not_available, validate_snapshot
from investment_system.producers.errors import ResearchStatusError
from investment_system.producers.registry import FrozenUniverseProducer, ProduceRequest
from investment_system.publication.authorization import (
    ACTIVE_AUTHORIZATIONS,
    summarize_grants,
    validate_authorization,
)
from investment_system.publication.envelope import attach_publication_envelope
from investment_system.publication.errors import AuthorizationError, ExtractionError, PromotionForbidden
from investment_system.publication.extractors import extract
from investment_system.publication.facts import make_fact
from investment_system.publication.predicate import decide, reject_promotion

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "investment_system"
NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
QGV_HASH = "ab" * 32
LB_HASH = "cd" * 32
TECH_HASH = "ef" * 32
FINGERPRINTS = {
    "leaderboard": "112b245b4f9963787ab7b2780f287e99515f05c231bfc127f656a57736e9b4c1",
    "macro": "7bbfad69ac46b5886fb30f32b871ce68983adbc089d7ea21ae3b6317d108732f",
    "n_qgv": 19,
    "portfolio_official_book": "53d930a7e3d2009347ac36f84e8a3b7504e6e5e9b0a4fe62fa5d1fb1be5a4a68",
    "qgv": "a17144803746000dc11efa630797fccbf76d2985e58ca7ae55797e7842d7ce3e",
    "technical": "82165414a2c86c5c489b7c071c44b967c344dd654238af445714bb0fe14097c7",
}


def _fact(**over):
    base = dict(
        subject_sha256=QGV_HASH,
        persisted_fingerprint=QGV_HASH,
        methodology_lifecycle="PROVISIONAL_RESEARCH",
        producer_validation="PASS",
        track_c_validation="NOT_RUN",
        track_c_claim_ignored=False,
        data_completeness="PARTIAL",
        research_record_exists=True,
        research_bytes_withheld=False,
        synthetic=False,
        stale_or_expired=False,
        policy_blockers=(),
        component_labels=(),
        within_tie_order=None,
    )
    base.update(over)
    return make_fact(**base)


def _grant(kind, subject, **over):
    body = {
        "contract": "PUBLICATION_AUTHORIZATION",
        "schema_version": 1,
        "grant_kind": kind,
        "authorization_id": "auth-test",
        "subject_sha256": subject,
        "issued_at": "2026-10-02T00:00:00+00:00",
        "explicit_event": True,
    }
    body.update(over)
    return body


def _qgv():
    return {
        "record_kind": "QGV_COMPANY_RESULT",
        "record_version": 1,
        "semantic_sha256": QGV_HASH,
        "semantic": {
            "status": "PASS",
            "status_reasons": ["PERSISTED_ONLY"],
            "synthetic": False,
            "qgv": {"Q_score": 81.25, "G_score": 72.5, "V_score": 63.5, "total": 77.125},
            "research_state": {
                "status": "PROVISIONAL_RESEARCH",
                "official_selection": False,
                "track_c_validated": False,
            },
        },
    }


def _leaderboard():
    return {
        "record_kind": "LEADERBOARD_COMPANY_RESULT",
        "record_version": 1,
        "semantic_sha256": LB_HASH,
        "semantic": {
            "status": "PASS",
            "status_reasons": [],
            "synthetic": False,
            "scores": {"total_score": 12.5},
            "ranking": {"engine_rank": 4, "within_tie_order_approval": "POLICY_BLOCKED"},
            "research_state": {"status": "PROVISIONAL_RESEARCH", "track_c_validated": True},
            "publication": {"data_state": "NOT_AVAILABLE", "official": False, "live": False},
        },
    }


def _macro():
    shell = not_available(
        "macro",
        "macro.real.v1",
        "v0.1.1",
        "2026-10-02T00:00:00+00:00",
        "withheld",
        "POLICY_BLOCKED",
        "2026-10-02T00:00:00+00:00",
        {"id": "MACRO_CONFIRMED_ENGINE", "version": "v0.1.1", "status": "PROVISIONAL"},
    )
    return {
        "publication": "POLICY_BLOCKED",
        "publication_reasons": [
            "SERIES_MAPPING_PROVISIONAL",
            "EXPOSURE_NOT_APPROVED",
            "WEB_INDICATORS_NOT_RESHAPED",
            "NO_APPROVED_LIVE_EXPIRY",
        ],
        "producer_snapshot": shell,
        "research_snapshot": {"regime": "EXPANSION", "environment": {"indicators": {"growth": 0.041}}},
    }


def _technical():
    return {
        "contract": "TECHNICAL_RESEARCH_RECORD",
        "schema_version": 1,
        "semantic_hash": TECH_HASH,
        "methodology": {"m1": "APPROVED", "m2": "APPROVED", "m3": "NOT_APPROVED", "m4": "APPROVED"},
        "features": {"r_20": {"status": "AVAILABLE", "value": 0.123456}},
        "regime": {"status": "AVAILABLE", "value": "UP"},
        "zone": {"status": "AVAILABLE", "value": "TREND"},
        "web_publication": {"status": "BLOCKED", "reason_code": "P01_DECISION_REQUIRED"},
        "synthetic": False,
    }


def _bundle():
    from investment_system.producers.registry import default_registry
    return assemble_bundle(
        FrozenUniverseProducer().companies(),
        default_registry().run(ProduceRequest(NOW, NOW)),
        NOW,
    )


def test_schema1_states_and_active_grants_stay_closed():
    assert STATES == {"LIVE", "FROZEN_SNAPSHOT", "DEMO", "NOT_AVAILABLE"}
    assert "RESEARCH" not in STATES
    assert ACTIVE_AUTHORIZATIONS == ()
    assert summarize_grants() == {"research_display": "NONE", "frozen": "NONE", "live": "NONE"}


def test_producer_pass_is_not_a_grant_and_modes_match_without_a_name():
    left = decide(_fact())
    right = decide(_fact(methodology_lifecycle="PROVISIONAL"))
    assert left["publication_mode"] == "NOT_AVAILABLE"
    assert right["publication_mode"] == "NOT_AVAILABLE"
    assert left["schema1_data_state"] == "NOT_AVAILABLE"
    assert left["official"] is False and left["live"] is False and left["track_c_validated"] is False
    assert "PRODUCER_VALIDATION_IS_NOT_A_GRANT" in left["not_authority"]
    assert "RESEARCH_DISPLAY_GRANT_NONE" in left["reasons"]
    assert left["grants"]["research_display"] == "NONE"


def test_explicit_research_grant_stays_out_of_schema1_and_blocked_bytes_stay_hidden():
    allowed = decide(_fact(), (_grant("RESEARCH_DISPLAY", QGV_HASH),))
    assert allowed["publication_mode"] == "DISPLAY_RESEARCH"
    assert allowed["schema1_data_state"] == "NOT_AVAILABLE"
    assert allowed["reasons"] == ("DISCLOSURE_PARTIAL",)
    assert allowed["official"] is False
    blocked = decide(_fact(data_completeness="BLOCKED", within_tie_order="POLICY_BLOCKED"), (_grant("RESEARCH_DISPLAY", QGV_HASH),))
    assert blocked["publication_mode"] == "NOT_AVAILABLE"
    assert "BLOCKED_NOT_A_SCORE" in blocked["reasons"]
    withheld = decide(_fact(research_bytes_withheld=True), (_grant("RESEARCH_DISPLAY", QGV_HASH),))
    assert withheld["publication_mode"] == "NOT_AVAILABLE"
    assert "RESEARCH_BYTES_WITHHELD" in withheld["reasons"]
    stale = decide(_fact(stale_or_expired=True), (_grant("RESEARCH_DISPLAY", QGV_HASH),))
    assert stale["publication_mode"] == "NOT_AVAILABLE"
    assert "STALE_DOES_NOT_FALL_BACK_TO_DISPLAY_RESEARCH" in stale["reasons"]
    synthetic = decide(_fact(synthetic=True), (_grant("RESEARCH_DISPLAY", QGV_HASH),))
    assert "SYNTHETIC_IS_NOT_RESEARCH_DISPLAY" in synthetic["reasons"]


def test_one_grant_does_not_satisfy_another_and_promotion_is_refused():
    frozen_only = decide(_fact(), (_grant("FROZEN", QGV_HASH),))
    assert frozen_only["publication_mode"] == "NOT_AVAILABLE"
    assert frozen_only["grants"] == {"research_display": "NONE", "frozen": "PRESENT", "live": "NONE"}
    assert "FROZEN_GRANT_DOES_NOT_SATISFY_RESEARCH_DISPLAY" in frozen_only["not_authority"]
    assert frozen_only["schema1_data_state"] == "NOT_AVAILABLE"
    live_only = decide(_fact(), (_grant("LIVE", QGV_HASH),))
    assert live_only["schema1_data_state"] == "NOT_AVAILABLE"
    assert "LIVE_GRANT_DOES_NOT_SATISFY_RESEARCH_DISPLAY" in live_only["not_authority"]
    for requested in ("LIVE", "FROZEN_SNAPSHOT", "OFFICIAL", "VALIDATED", "RESEARCH"):
        with pytest.raises(PromotionForbidden, match="PROMOTION_FORBIDDEN"):
            reject_promotion(requested)


def test_component_label_and_forged_track_c_are_not_authority():
    labeled = decide(_fact(component_labels=("m1:APPROVED", "m2:APPROVED"), track_c_claim_ignored=True))
    assert labeled["track_c_validated"] is False
    assert "COMPONENT_LABEL_IS_NOT_TRACK_C" in labeled["not_authority"]
    assert "TRACK_C_CLAIM_IGNORED" in labeled["not_authority"]
    with pytest.raises(ExtractionError, match="cannot record Track C"):
        _fact(track_c_validation="PASS")


def test_authorization_record_is_explicit_and_closed():
    validate_authorization(_grant("RESEARCH_DISPLAY", QGV_HASH))
    forged = _grant("RESEARCH_DISPLAY", QGV_HASH)
    forged["explicit_event"] = False
    with pytest.raises(AuthorizationError, match="explicit"):
        validate_authorization(forged)
    extra = _grant("LIVE", QGV_HASH)
    extra["derived_from_producer_pass"] = True
    with pytest.raises(AuthorizationError, match="keys"):
        validate_authorization(extra)
    wrong_subject = decide(_fact(), (_grant("RESEARCH_DISPLAY", "12" * 32),))
    assert wrong_subject["publication_mode"] == "NOT_AVAILABLE"
    assert "RESEARCH_DISPLAY_GRANT_NONE" in wrong_subject["reasons"]


def test_extractors_copy_hashes_and_drop_scores():
    qgv = _qgv()
    before = json.dumps(qgv, sort_keys=True)
    fact = extract(qgv)
    assert json.dumps(qgv, sort_keys=True) == before
    assert fact["persisted_fingerprint"] == QGV_HASH
    assert fact["data_completeness"] == "PARTIAL"
    dumped = json.dumps(fact)
    for token in ("81.25", "72.5", "63.5", "77.125", "Q_score"):
        assert token not in dumped
    qgv["semantic"]["qgv"]["total"] = 1
    assert extract(qgv)["persisted_fingerprint"] == QGV_HASH
    board = _leaderboard()
    board_fact = extract(board)
    assert board_fact["within_tie_order"] == "POLICY_BLOCKED"
    assert board_fact["data_completeness"] == "BLOCKED"
    assert board_fact["track_c_claim_ignored"] is True
    assert "12.5" not in json.dumps(board_fact)
    macro = _macro()
    macro_fact = extract(macro)
    assert macro_fact["research_bytes_withheld"] is True
    assert "EXPANSION" not in json.dumps(macro_fact)
    assert "0.041" not in json.dumps(macro_fact)
    macro["research_snapshot"]["regime"] = "NEUTRAL"
    assert extract(macro)["persisted_fingerprint"] == macro_fact["persisted_fingerprint"]
    technical = _technical()
    technical_fact = extract(technical)
    assert technical_fact["research_bytes_withheld"] is True
    assert technical_fact["component_labels"] == ("m1:APPROVED", "m2:APPROVED", "m3:NOT_APPROVED", "m4:APPROVED")
    assert "0.123456" not in json.dumps(technical_fact)
    assert "UP" not in json.dumps(technical_fact)
    technical["features"]["r_20"]["value"] = 9
    assert extract(technical)["persisted_fingerprint"] == TECH_HASH


def test_same_fact_axes_decide_the_same_way():
    first = decide(extract(_qgv()))
    second = decide(_fact(policy_blockers=("PERSISTED_ONLY",)))
    assert first["publication_mode"] == second["publication_mode"] == "NOT_AVAILABLE"
    assert first["schema1_data_state"] == second["schema1_data_state"]
    with pytest.raises(ExtractionError, match="matched 0"):
        extract({"record_kind": "SOMETHING_ELSE"})


def test_production_envelope_keeps_sections_and_does_not_activate_display():
    bundle = _bundle()
    bare = attach_publication_envelope(bundle)
    attached = attach_publication_envelope(bundle, (_qgv(), _leaderboard(), _macro(), _technical()))
    assert attached["schema_version"] == 1
    assert attached["publication_envelope"]["display_research_active"] is False
    assert attached["publication_envelope"]["research_display_grant"] == "NONE"
    assert attached["publication_envelope"]["frozen_grant"] == "NONE"
    assert attached["publication_envelope"]["live_grant"] == "NONE"
    assert attached["publication_envelope"]["schema1_research_state_added"] is False
    assert [row["publication_mode"] for row in attached["publication_envelope"]["decisions"]] == ["NOT_AVAILABLE"] * 4
    for name in ("universe", *SECTIONS):
        assert attached[name]["state"] == bundle[name]["state"]
        assert attached[name].get("data") == bundle[name].get("data")
        assert "publication_envelope" not in attached[name]
        if name != "universe":
            assert attached[name]["state"] == "NOT_AVAILABLE"
            assert attached[name]["data"] is None
    validate_bundle(attached)
    assert bare["publication_envelope"]["decisions"] == []
    again = attach_publication_envelope(bundle, (_technical(), _qgv(), _macro(), _leaderboard()))
    assert again["publication_envelope"]["decisions"] == attached["publication_envelope"]["decisions"]


def test_research_lifecycle_is_still_rejected_as_live():
    cid = FrozenUniverseProducer().companies()[0]["company_id"]
    snapshot = make_snapshot(
        producer_id="test.qgv",
        producer_version="v1",
        section="qgv",
        data_state="LIVE",
        as_of="2026-10-01T00:00:00+00:00",
        requested_as_of="2026-10-01T00:00:00+00:00",
        generated_at="2026-10-01T01:00:00+00:00",
        expires_at="2026-10-02T00:00:00+00:00",
        methodology={"id": "TEST", "version": "1", "status": "PROVISIONAL_RESEARCH"},
        synthetic=False,
        provenance={"source": "fixture", "inputs": [{"artifact_id": "raw:x", "sha256": "0" * 64}]},
        validation={"status": "PASS", "checks": []},
        scope_kind="ENTITY_MAP",
        data={cid: {"note": "not-a-score"}},
    )
    with pytest.raises(ResearchStatusError):
        validate_snapshot(snapshot)


def test_publication_package_does_not_import_engines_or_name_them_in_the_predicate():
    banned = (
        "AnalysisPipeline",
        "LeaderboardEngine",
        "MacroEngine",
        "TechnicalEngine",
        "real_model_v1",
        "run_official_book",
        "evaluate_stamped",
        "Holdout",
    )
    package = SRC / "publication"
    tree = ast.parse("\n".join(path.read_text() for path in package.glob("*.py")))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    text = "\n".join(sorted(imported))
    for token in banned:
        assert token not in text
    predicate = (package / "predicate.py").read_text().lower()
    for token in ("qgv", "leaderboard", "macro", "technical"):
        assert token not in predicate


def test_engine_fingerprints_match_the_pre_change_pin():
    script = ROOT / "tools" / "producer_engine_fingerprint.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(ROOT / "src")],
        check=True,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    observed = json.loads(completed.stdout)
    assert observed == FINGERPRINTS


def test_protected_engine_bytes_are_unchanged():
    paths = [
        "qgv/pipeline.py",
        "qgv/leaderboard.py",
        "qgv/book.py",
        "technical/engine.py",
        "macro/engine.py",
        "product/web_mvp.py",
        "producers/assembler.py",
    ]
    digest = hashlib.sha256()
    for rel in paths:
        digest.update(rel.encode())
        digest.update((SRC / rel).read_bytes())
    assert digest.hexdigest() == "1d6c56e4bcf356758ecec8c0524bf2a345eb99acd568278e0366599f3dd2f259"
