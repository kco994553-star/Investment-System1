"""Compatibility boundary to Producer Infrastructure v1 (read-only dependency, not merged into this branch).

This module defines no snapshot schema. It:
1. lazily imports the Infrastructure's own `investment_system.producers` package;
2. rebuilds the engine's `QGVSnapshot` objects from persisted records;
3. hands them to `producers.adapters.qgv_section`;
4. builds snapshots with `producers.contract.make_snapshot` / `not_available` and validates them with `validate_snapshot`.

While the Infrastructure is not merged, `load_infra()` returns None and only the export decision is available.

Export decision (fail-closed): QGV results are `PROVISIONAL_RESEARCH`. The Infrastructure rejects that
methodology status for LIVE and FROZEN_SNAPSHOT (`ResearchStatusError`), and Web schema-1 has no research state
(P01 is not approved). The published QGV section is therefore `NOT_AVAILABLE`, with the Infrastructure's own reason
code `QGV_RESEARCH_ONLY_NO_EXPORT`. The full candidate snapshot is still built and validated so the rejection is
proven, not assumed.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .exporter import manifest_name, snapshots_name
from .record import qgv_snapshot_from_record, sha256_hex

INFRA_PIN = {"branch": "feature/producer-infrastructure-v1", "commit": "5fa7ce0647b6af91d767c54ecaaa3e31d1ab63e4",
             "code_commit": "bcfdcd2487f643feddda7a0fa2cace085ffc28a3"}
# The Infrastructure API this boundary consumes. A compatibility check fails if any name is absent.
EXPECTED_INFRA_API = {
    "investment_system.producers.contract": ("CONTRACT", "SCHEMA_VERSION", "RESEARCH_STATUSES", "PUBLISHED_STATES",
                                             "make_snapshot", "not_available", "validate_snapshot", "file_resolver"),
    "investment_system.producers.adapters": ("qgv_section", "WEB_READS", "SECTION_COMPATIBILITY"),
    "investment_system.producers.errors": ("ResearchStatusError",),
    "investment_system.producers.registry": ("DEFAULT_UNAVAILABLE", "default_registry", "ProduceRequest"),
    "investment_system.producers.serialization": ("canonical_sha256", "sha256_hex"),
}
SECTION = "qgv"
PRODUCER_ID = "qgv.real_research_producer"
REASON_CODE = "QGV_RESEARCH_ONLY_NO_EXPORT"  # producers/registry.DEFAULT_UNAVAILABLE['qgv'][0]
REASON = "QGV 결과는 연구용(PROVISIONAL_RESEARCH)이며 Web 연구 상태(P01)와 Track C 검증 전에는 공개하지 않습니다."
CANDIDATE_STATE = "FROZEN_SNAPSHOT"  # the state the data would take: point-in-time, historical as_of
BLOCKERS = ("P01_RESEARCH_DATA_STATE_NOT_APPROVED", "TRACK_C_VALIDATION_NOT_COMPLETE")


def load_infra() -> SimpleNamespace | None:
    """The Infrastructure modules, or None when the dependency is not on this branch."""
    mods = {}
    for name in EXPECTED_INFRA_API:
        try:
            mods[name.rsplit(".", 1)[1]] = importlib.import_module(name)
        except ImportError:
            return None
    return SimpleNamespace(**mods)


def missing_api(infra: SimpleNamespace) -> list[str]:
    return [f"{mod}.{attr}" for mod, attrs in EXPECTED_INFRA_API.items()
            for attr in attrs if not hasattr(getattr(infra, mod.rsplit(".", 1)[1]), attr)]


def export_decision(manifest: dict) -> dict:
    sem = manifest["semantic"]
    blockers = list(BLOCKERS)
    if not sem["complete"]:
        blockers.append(f"PARTIAL_BATCH:{sem['counts']}")
    return {"section": SECTION, "data_state": "NOT_AVAILABLE", "candidate_state": CANDIDATE_STATE,
            "reason_code": REASON_CODE, "blockers": blockers, "methodology_status": sem["research_state"]["status"],
            "unblock_when": ["P01 approved with a research data state that Web schema-1 can show",
                             "Track C C7-C10 complete and an Official QGV promotion decided by its owner"]}


def file_inputs(root: Path | str, out_dir: Path | str, as_of: str) -> list[dict]:
    root, out = Path(root).resolve(), Path(out_dir).resolve()
    inputs = []
    for name in (snapshots_name(as_of), manifest_name(as_of)):
        p = out / name
        body = p.read_bytes()
        inputs.append({"artifact_id": "file:" + p.relative_to(root).as_posix(), "sha256": sha256_hex(body), "bytes": len(body)})
    return inputs


def build_infra_snapshots(infra: SimpleNamespace, records: list[dict], manifest: dict, *, root: Path | str,
                          out_dir: Path | str, generated_at: str, requested_as_of: str | None = None) -> dict[str, Any]:
    """Build (a) the research candidate and (b) the publishable NOT_AVAILABLE snapshot with the Infrastructure's code."""
    sem = manifest["semantic"]
    snaps = [qgv_snapshot_from_record(r) for r in records if r["semantic"]["status"] == "PASS"]
    scope_kind, data, synthetic = infra.adapters.qgv_section(snaps)
    methodology = {"id": "QGV", "version": f"{sem['methodology']['qgv_analysis_contract']}/{sem['methodology']['qgv_standard_version']}",
                   "status": sem["research_state"]["status"], "weights_sha256": sem["methodology"]["weights_sha256"],
                   "cross_section_rule_id": sem["methodology"]["cross_section_rule_id"]}
    fails = sum(1 for r in records if r["semantic"]["status"] == "FAIL")
    candidate = infra.contract.make_snapshot(
        producer_id=PRODUCER_ID, producer_version=str(manifest["operational"].get("code_commit")), section=SECTION,
        data_state=CANDIDATE_STATE, as_of=sem["as_of"], requested_as_of=requested_as_of or sem["as_of"],
        generated_at=generated_at, methodology=methodology, synthetic=synthetic,
        provenance={"source": "qgv_producer.exporter", "inputs": file_inputs(root, out_dir, sem["as_of"]),
                    "universe_id": sem["universe"]["universe_id"], "manifest_semantic_sha256": manifest["semantic_sha256"],
                    "raw_inputs_sha256": sem["data_lineage"]["inputs_sha256"]},
        validation={"status": "PASS" if fails == 0 else "FAIL",
                    "checks": ["record_semantic_sha256", "pit_available_at_le_as_of", "raw_lineage_sha256",
                               "synthetic_state", "research_state_not_promoted", "manifest_counts"],
                    "counts": sem["counts"], "complete": sem["complete"]},
        data=data, scope_kind=scope_kind)
    candidate_error = None
    try:
        infra.contract.validate_snapshot(candidate)
    except ValueError as e:  # all Infrastructure errors subclass ValueError
        candidate_error = {"type": type(e).__name__, "code": getattr(e, "code", None), "message": str(e)}
    decision = export_decision(manifest)
    published = infra.contract.validate_snapshot(infra.contract.not_available(
        SECTION, PRODUCER_ID, str(manifest["operational"].get("code_commit")), generated_at, REASON, REASON_CODE,
        requested_as_of=requested_as_of or sem["as_of"],
        methodology={"id": "QGV", "version": methodology["version"], "status": "NOT_AVAILABLE",
                     "blocker": "; ".join(decision["blockers"])}))
    return {"candidate": candidate, "candidate_error": candidate_error, "published": published, "decision": decision}
