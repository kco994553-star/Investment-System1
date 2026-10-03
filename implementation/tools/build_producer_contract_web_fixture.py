"""Build a withheld producer-contract fixture with the existing static Web.

This tool is validation only. Its literal records are test vectors, never real
investment data or grants. Record bytes are kept outside the served Web folder.
No engine, source-data provider, calibration, or Holdout is called.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investment_system.product.web_mvp import SECTIONS, build  # noqa: E402
from investment_system.producers.assembler import assemble_bundle  # noqa: E402
from investment_system.producers.contract import not_available  # noqa: E402
from investment_system.producers.registry import (  # noqa: E402
    FrozenUniverseProducer, ProduceRequest, default_registry,
)
from investment_system.producers.serialization import canonical_bytes, sha256_hex  # noqa: E402
from investment_system.publication.envelope import attach_publication_envelope  # noqa: E402

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
AS_OF = "2026-10-02T20:00:00Z"
QGV_HASH = "a1" * 32
BOARD_HASH = "b2" * 32
TECH_HASH = "c3" * 32
FORBIDDEN = ("9876.54321", "8765.43219", "7654.32198", "RESEARCH_REGIME_TEST_ONLY")


def fixture_records():
    """Literal contract-shape fixtures; these hashes are fixed test identities."""
    macro_shell = not_available(
        "macro", "test.macro.withheld", "TEST_VECTOR_V1", NOW.isoformat(),
        "TEST ONLY: Macro research withheld", "POLICY_BLOCKED", NOW.isoformat(),
        {"id": "MACRO_CONFIRMED_ENGINE", "version": "TEST_VECTOR_V1", "status": "PROVISIONAL"},
    )
    records = [
        {"record_kind": "QGV_COMPANY_RESULT", "record_version": 1, "semantic_sha256": QGV_HASH,
         "semantic": {"status": "PASS", "status_reasons": ["PERSISTED_ONLY"], "synthetic": False,
                      "qgv": {"Q_score": 9876.54321},
                      "research_state": {"status": "PROVISIONAL_RESEARCH", "track_c_validated": False}}},
        {"record_kind": "LEADERBOARD_COMPANY_RESULT", "record_version": 1, "semantic_sha256": BOARD_HASH,
         "semantic": {"status": "PASS", "status_reasons": [], "synthetic": False,
                      "scores": {"total_score": 8765.43219},
                      "ranking": {"engine_rank": 7654.32198, "within_tie_order_approval": "POLICY_BLOCKED"},
                      "research_state": {"status": "PROVISIONAL_RESEARCH", "track_c_validated": False},
                      "publication": {"data_state": "NOT_AVAILABLE", "official": False, "live": False}}},
        {"publication": "POLICY_BLOCKED",
         "publication_reasons": ["SERIES_MAPPING_PROVISIONAL", "EXPOSURE_NOT_APPROVED",
                                 "WEB_INDICATORS_NOT_RESHAPED", "NO_APPROVED_LIVE_EXPIRY"],
         "producer_snapshot": macro_shell,
         "research_snapshot": {"regime": "RESEARCH_REGIME_TEST_ONLY"}},
        {"contract": "TECHNICAL_RESEARCH_RECORD", "schema_version": 1, "semantic_hash": TECH_HASH,
         "methodology": {"m1": "APPROVED", "m2": "APPROVED", "m3": "NOT_APPROVED"},
         "features": {"r_20": {"status": "AVAILABLE", "value": 7654.32198}},
         "regime": {"status": "AVAILABLE", "value": "RESEARCH_REGIME_TEST_ONLY"},
         "web_publication": {"status": "BLOCKED", "reason_code": "P01_DECISION_REQUIRED"}, "synthetic": False},
    ]
    return records


def fixture_bundle():
    request = ProduceRequest(NOW, NOW)
    snapshots = default_registry().run(request)
    for name in ("qgv", "technical", "macro", "leaderboard"):
        snapshot = not_available(
            name, f"test.{name}.withheld", "TEST_VECTOR_V1", NOW.isoformat(),
            "TEST ONLY: Research publication is withheld.", "RESEARCH_DISPLAY_GRANT_NONE", NOW.isoformat(),
            {"id": f"TEST_{name.upper()}", "version": "TEST_VECTOR_V1", "status": "PROVISIONAL_RESEARCH"},
        )
        # These are persisted producer metadata, distinct from section availability.
        # They are copied by the assembler; none becomes section data or authority.
        snapshot["as_of"] = AS_OF
        snapshot["validation"] = {"status": "PASS", "checks": ["TEST_VECTOR_SHAPE_ONLY"]}
        snapshots[name] = snapshot
    bundle = assemble_bundle(FrozenUniverseProducer().companies(), snapshots, NOW)
    return bundle


def build_fixture(out, evidence):
    out, evidence = Path(out).resolve(), Path(evidence).resolve()
    if out == evidence or out in evidence.parents:
        raise ValueError("evidence must be outside the served Web folder")
    evidence.mkdir(parents=True, exist_ok=True)
    records, bundle = fixture_records(), fixture_bundle()
    original_records = canonical_bytes(records)
    original_bundle = deepcopy(bundle)
    attached = attach_publication_envelope(bundle, records)
    assert canonical_bytes(records) == original_records
    for name in ("universe", *SECTIONS):
        assert attached[name] == original_bundle[name]
    assert attached["companies"] == original_bundle["companies"]
    envelope = attached["publication_envelope"]
    assert envelope["grants"] == {"research_display": "NONE", "frozen": "NONE", "live": "NONE"}
    assert envelope["display_research_active"] is False
    assert {d["publication_mode"] for d in envelope["decisions"]} == {"NOT_AVAILABLE"}
    assert {d["data_completeness"] for d in envelope["decisions"]} == {"PARTIAL", "BLOCKED"}
    assert any("PRODUCER_VALIDATION_IS_NOT_A_GRANT" in d["not_authority"] for d in envelope["decisions"])
    for name in SECTIONS:
        assert attached[name]["state"] == "NOT_AVAILABLE" and attached[name]["data"] is None
    for name in ("qgv", "technical", "macro", "leaderboard"):
        meta = attached[name]["producer"]
        assert meta["as_of"] == AS_OF
        assert meta["freshness"] == "NOT_APPLICABLE"
        assert meta["methodology"]["version"] == "TEST_VECTOR_V1"
        assert meta["validation"]["status"] == "PASS"
    serialized = canonical_bytes(attached)
    assert not any(token.encode() in serialized for token in FORBIDDEN)
    (evidence / "records.test-vector.json").write_bytes(original_records)
    build(out, attached)
    # The build must preserve every original value and only add separate search metadata.
    emitted = json.loads((out / "data.json").read_text(encoding="utf-8"))
    assert emitted == json.loads(serialized)
    manifest = {
        "kind": "WITHHELD_PRODUCER_CONTRACT_WEB_FIXTURE_V1",
        "scope": "TEST VECTORS ONLY; NOT_REAL_DATA_VERIFIED; NO_DISPLAY_GRANT",
        "evaluation_clock": NOW.isoformat(), "producer_as_of": AS_OF,
        "records_sha256": sha256_hex(original_records),
        "bundle_canonical_sha256": sha256_hex(serialized),
        "data_json_sha256": sha256_hex((out / "data.json").read_bytes()),
        "entities_json_sha256": sha256_hex((out / "entities.json").read_bytes()),
        "withheld_tokens": list(FORBIDDEN),
        "schema1_sections_unchanged": True, "records_unchanged": True,
        "research_display": "NONE", "frozen_grant": "NONE", "live_grant": "NONE",
        "Actions": "NOT_RUN", "engine_execution": "NOT_RUN",
    }
    (evidence / "fixture-manifest.json").write_bytes(canonical_bytes(manifest))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    print(json.dumps(build_fixture(args.out, args.evidence), indent=2))


if __name__ == "__main__":
    main()
