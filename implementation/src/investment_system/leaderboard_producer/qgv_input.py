"""Read-only consumer of QGV_COMPANY_RESULT v1.

Does not import qgv_producer (that package is an unmerged branch) and does not rescore.
Identity is the persisted semantic hash plus a byte-identical QGVSnapshot rebuild.
"""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..contracts.enums import CalibrationLifecycle, CoverageState, ProfileKind, QualityState
from ..contracts.models import QGVSnapshot, VCandidate
from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_CANDIDATES, V_INITIAL_PRIOR
from .canonical import canonical_sha256, to_jsonable
from .errors import LeaderboardProducerError

QGV_RECORD_KIND = "QGV_COMPANY_RESULT"
QGV_RECORD_VERSION = 1
QGV_MANIFEST_KIND = "QGV_PRODUCER_BATCH_MANIFEST"
QGV_MANIFEST_VERSION = 1
QGV_PIN = {
    "branch": "ccr-db5d5960-qen9yi",
    "pr": 10,
    "commit": "5eec129ef81641f0bc11f5adbb43d0b2122ee24b",
    "role": "read-only persisted QGV evidence; not merged into this branch",
}
RESEARCH_STATUS = "PROVISIONAL_RESEARCH"
PROMOTED = frozenset({
    "OFFICIAL", "VALIDATED", "PROMOTED", "LIVE_OFFICIAL", "LIVE", "STANDARD", "CALIBRATED",
    "VALIDATION_SELECTED", "OOS_TESTED", "PIT_TESTED",
})
OUTCOME_KEYS = frozenset({
    "realized_return", "px1", "horizon_as_of", "outcomes", "outcome_metrics",
    "equal_weight_realized", "realized",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
# Frozen Official as-of dates that already have QGV producer evidence. No other Universe is created.
FROZEN_AS_OF = ("2024-06-30", "2024-09-30", "2024-12-31")


def methodology_config() -> dict:
    """Read the frozen weights. Not a new standard."""
    return {
        "Q_WEIGHTS": dict(Q_WEIGHTS),
        "G_WEIGHTS": dict(G_WEIGHTS),
        "V_INITIAL_PRIOR": dict(V_INITIAL_PRIOR),
        "V_CANDIDATES": {
            k: {"weights": dict(v["weights"]), "lifecycle": v["lifecycle"]} for k, v in V_CANDIDATES.items()
        },
    }


def methodology_weights_sha256() -> str:
    return canonical_sha256(methodology_config())


def parse_ts(value: Any, where: str) -> datetime:
    if not isinstance(value, str):
        raise LeaderboardProducerError("PIT_EVIDENCE_MISSING", f"{where} must be an ISO timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise LeaderboardProducerError("PIT_EVIDENCE_MISSING", f"{where} unparsable: {value!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise LeaderboardProducerError("PIT_EVIDENCE_MISSING", f"{where} must be timezone-aware")
    return dt


def _walk_keys(v: Any) -> Iterable[str]:
    if isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from _walk_keys(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk_keys(x)


def snapshot_semantic(snapshot: QGVSnapshot) -> dict:
    d = to_jsonable(snapshot)
    d.pop("qgv_snapshot_id")
    return d


def qgv_snapshot_from_record(rec: Mapping) -> QGVSnapshot:
    """Rebuild the persisted snapshot. Rejects a shape that is not the current QGVSnapshot."""
    q = dict(rec["semantic"]["qgv"])
    q["qgv_snapshot_id"] = rec["operational"]["qgv_snapshot_id"]
    q["analyzed_at"] = datetime.fromisoformat(q["analyzed_at"])
    q["as_of"] = datetime.fromisoformat(q["as_of"])
    q["profile_kind"] = ProfileKind(q["profile_kind"])
    q["V_policy_status"] = CalibrationLifecycle(q["V_policy_status"])
    q["coverage_state"] = CoverageState(q["coverage_state"])
    q["quality_states"] = tuple(QualityState(x) for x in q["quality_states"])
    q["key_drivers"] = tuple(q["key_drivers"])
    q["data_stamp_refs"] = tuple(q["data_stamp_refs"])
    q["v_candidates"] = tuple(
        VCandidate(
            candidate_id=v["candidate_id"],
            lifecycle=CalibrationLifecycle(v["lifecycle"]),
            weights=dict(v["weights"]),
            v_score=v["v_score"],
            blocked_reason=v["blocked_reason"],
        )
        for v in q["v_candidates"]
    )
    fields = {f.name for f in dataclasses.fields(QGVSnapshot)}
    if set(q) != fields:
        raise LeaderboardProducerError("SCHEMA", f"snapshot fields differ from QGVSnapshot: {sorted(set(q) ^ fields)}")
    snap = QGVSnapshot(**q)
    if snapshot_semantic(snap) != rec["semantic"]["qgv"]:
        raise LeaderboardProducerError("SCHEMA", "reconstructed snapshot is not identical to the persisted one")
    return snap


def _check_research(rs: Any) -> None:
    if not isinstance(rs, dict):
        raise LeaderboardProducerError("RESEARCH_STATE", "research_state required")
    if rs.get("status") != RESEARCH_STATUS:
        raise LeaderboardProducerError(
            "PROMOTION_FORBIDDEN", f"research_state.status must stay {RESEARCH_STATUS}, got {rs.get('status')!r}"
        )
    if str(rs.get("v_policy_status")) in PROMOTED:
        raise LeaderboardProducerError("PROMOTION_FORBIDDEN", f"V policy {rs.get('v_policy_status')!r} is not promotable here")
    for k in ("official_selection", "official_pass", "full_pit_pass", "calibrated", "track_c_validated"):
        if rs.get(k) is not False:
            raise LeaderboardProducerError("PROMOTION_FORBIDDEN", f"research_state.{k} must be false")


def validate_qgv_record(rec: Any, *, require_real: bool = True) -> dict:
    if not isinstance(rec, dict) or rec.get("record_kind") != QGV_RECORD_KIND:
        raise LeaderboardProducerError("SCHEMA", f"record_kind must be {QGV_RECORD_KIND}")
    if rec.get("record_version") != QGV_RECORD_VERSION:
        raise LeaderboardProducerError("SCHEMA", f"unsupported record_version {rec.get('record_version')!r}")
    if rec.get("semantic_sha256") != canonical_sha256(rec.get("semantic")):
        raise LeaderboardProducerError("SEMANTIC_HASH", "QGV semantic_sha256 does not match semantic content")
    sem = rec["semantic"]
    for k in (
        "company_id", "ticker", "as_of", "status", "status_reasons", "universe", "methodology",
        "research_state", "synthetic", "pit", "lineage", "qgv", "cross_section",
    ):
        if k not in sem:
            raise LeaderboardProducerError("SCHEMA", f"semantic.{k} absent")
    if sem["status"] not in ("PASS", "FAIL", "NOT_RUN"):
        raise LeaderboardProducerError("SCHEMA", f"status {sem['status']!r} is not PASS/FAIL/NOT_RUN")
    parse_ts(sem["as_of"], "as_of")
    _check_research(sem["research_state"])
    leaked = OUTCOME_KEYS.intersection(_walk_keys(sem))
    if leaked:
        raise LeaderboardProducerError("OUTCOME_LEAK", f"post-as_of keys present: {sorted(leaked)}")
    if not isinstance(sem["synthetic"], bool):
        raise LeaderboardProducerError("SYNTHETIC_STATE", "synthetic must be boolean")
    if sem["status"] != "PASS":
        if not sem["status_reasons"]:
            raise LeaderboardProducerError("SCHEMA", f"{sem['status']} requires status_reasons")
        return rec
    q = sem["qgv"]
    if not isinstance(q, dict):
        raise LeaderboardProducerError("SCHEMA", "PASS requires the engine QGVSnapshot")
    if q.get("company_id") != sem["company_id"]:
        raise LeaderboardProducerError("IDENTITY", "snapshot company_id differs from the record")
    if parse_ts(q.get("as_of"), "qgv.as_of") != parse_ts(sem["as_of"], "as_of"):
        raise LeaderboardProducerError("IDENTITY", "snapshot as_of differs from record as_of")
    m = sem["methodology"]
    for k in ("qgv_system_version", "qgv_standard_version", "qgv_analysis_contract", "implementation_line"):
        if m.get(k) != q.get(k):
            raise LeaderboardProducerError("METHODOLOGY", f"methodology.{k} differs from the snapshot")
    if m.get("weights_sha256") != methodology_weights_sha256():
        raise LeaderboardProducerError(
            "METHODOLOGY", "record weights_sha256 does not match qgv/factors.py; refusing to rank under a different methodology"
        )
    op = rec.get("operational")
    if not isinstance(op, dict) or not op.get("qgv_snapshot_id"):
        raise LeaderboardProducerError("IDENTITY", "operational.qgv_snapshot_id required")
    # Rebuild before PIT/provenance so a shape error is not mislabeled.
    snap = qgv_snapshot_from_record(rec)
    marked = (
        snap.synthetic is True
        or snap.coverage_state == CoverageState.SYNTHETIC
        or QualityState.SYNTHETIC in snap.quality_states
        or sem["pit"].get("fundamentals_synthetic") is True
        or any(str(i.get("source_kind", "")).upper().startswith("SYNTHETIC") for i in (sem["lineage"].get("inputs") or []))
    )
    if marked != sem["synthetic"]:
        raise LeaderboardProducerError("SYNTHETIC_STATE", "synthetic flag disagrees with the snapshot or inputs")
    if require_real and sem["synthetic"]:
        raise LeaderboardProducerError("SYNTHETIC_STATE", "the real leaderboard producer does not rank synthetic QGV")
    as_of = parse_ts(sem["as_of"], "as_of")
    pit = sem["pit"]
    avail = parse_ts(pit.get("fundamentals_available_at"), "pit.fundamentals_available_at")
    if avail > as_of:
        raise LeaderboardProducerError("PIT_VIOLATION", f"fundamentals available_at {avail.isoformat()} > as_of")
    for k in ("price_observed_at", "prior_year_price_observed_at"):
        if pit.get(k) is not None and parse_ts(pit[k], f"pit.{k}") > as_of:
            raise LeaderboardProducerError("PIT_VIOLATION", f"{k} {pit[k]} > as_of")
    inputs = sem["lineage"].get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise LeaderboardProducerError("MISSING_PROVENANCE", "no hashed raw input")
    seen = set()
    for i in inputs:
        aid = i.get("artifact_id") if isinstance(i, dict) else None
        if not isinstance(aid, str) or not aid.startswith("raw:"):
            raise LeaderboardProducerError("MISSING_PROVENANCE", f"input artifact_id {aid!r} is not a raw store id")
        if aid in seen:
            raise LeaderboardProducerError("MISSING_PROVENANCE", f"duplicate input {aid}")
        seen.add(aid)
        if not isinstance(i.get("sha256"), str) or not _HEX64.match(i["sha256"]):
            raise LeaderboardProducerError("SOURCE_HASH", f"invalid sha256 for {aid}")
    if not any(a.startswith("raw:companyfacts:") for a in seen):
        raise LeaderboardProducerError("MISSING_PROVENANCE", "fundamentals source (companyfacts) not in lineage")
    if require_real:
        limits = pit.get("known_limitations") or []
        if "SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED" not in limits:
            raise LeaderboardProducerError("PIT_EVIDENCE_MISSING", "known PIT limitation was dropped")
    return rec


def validate_qgv_manifest(manifest: Any, records: list[dict]) -> dict:
    if not isinstance(manifest, dict) or manifest.get("manifest_kind") != QGV_MANIFEST_KIND:
        raise LeaderboardProducerError("SCHEMA", f"manifest must be {QGV_MANIFEST_KIND}")
    if manifest.get("manifest_version") != QGV_MANIFEST_VERSION:
        raise LeaderboardProducerError("SCHEMA", "unsupported QGV manifest version")
    sem = manifest.get("semantic")
    if not isinstance(sem, dict) or manifest.get("semantic_sha256") != canonical_sha256(sem):
        raise LeaderboardProducerError("SEMANTIC_HASH", "QGV manifest semantic_sha256 does not match")
    if sem.get("scope") != "FULL_UNIVERSE":
        raise LeaderboardProducerError("SAMPLE_NOT_A_UNIVERSE", "a SAMPLE QGV batch is not a Leaderboard Universe")
    day = str(sem.get("as_of", ""))[:10]
    if day not in FROZEN_AS_OF:
        raise LeaderboardProducerError(
            "POLICY_BLOCKED",
            f"as_of {sem.get('as_of')!r} is outside the Frozen QGV dates {FROZEN_AS_OF}; no new Universe is created (P02)",
        )
    rows = [
        {
            "company_id": r["semantic"]["company_id"],
            "status": r["semantic"]["status"],
            "status_reasons": r["semantic"]["status_reasons"],
            "semantic_sha256": r["semantic_sha256"],
        }
        for r in records
    ]
    if rows != sem.get("records") or canonical_sha256(rows) != sem.get("records_sha256"):
        raise LeaderboardProducerError("MANIFEST_MISMATCH", "QGV manifest rows differ from the loaded records")
    if len(records) != sem.get("expected_count") or len(records) != sem.get("persisted_count"):
        raise LeaderboardProducerError("PARTIAL_BATCH_HIDDEN", "QGV persisted count differs from expected count")
    ids = [r["semantic"]["company_id"] for r in records]
    if ids != sorted(set(ids)):
        raise LeaderboardProducerError("IDENTITY", "QGV records must be unique and sorted by company_id")
    for r in records:
        if r["semantic"]["as_of"] != sem["as_of"]:
            raise LeaderboardProducerError("IDENTITY", f"{r['semantic']['company_id']}: as_of differs from the QGV manifest")
        if r["semantic"]["universe"]["universe_id"] != sem["universe"]["universe_id"]:
            raise LeaderboardProducerError("IDENTITY", f"{r['semantic']['company_id']}: universe differs from the QGV manifest")
    return manifest


def load_qgv_export(directory: Path | str, as_of_day: str) -> tuple[list[dict], dict]:
    directory = Path(directory)
    day = as_of_day[:10]
    manifest_path = directory / f"qgv_batch_manifest_{day}.json"
    snaps_path = directory / f"qgv_company_snapshots_{day}.jsonl"
    if not manifest_path.is_file() or not snaps_path.is_file():
        raise LeaderboardProducerError("DATA_BLOCKED", f"QGV export for {day} is not at {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in snaps_path.read_text(encoding="utf-8").splitlines() if line]
    for rec in records:
        validate_qgv_record(rec)
    validate_qgv_manifest(manifest, records)
    return records, manifest


def members_identity(official: Mapping) -> list[dict]:
    members = official.get("members")
    if not isinstance(members, list) or not members:
        raise LeaderboardProducerError("UNIVERSE", "official snapshot has no members")
    out = []
    for m in members:
        if not isinstance(m, dict) or not m.get("company_id") or not m.get("ticker"):
            raise LeaderboardProducerError("UNIVERSE", "official member missing company_id or ticker")
        out.append({"company_id": m["company_id"], "ticker": m["ticker"], "cik": m.get("cik")})
    return out


def load_official_snapshot(path: Path | str) -> tuple[dict, str]:
    path = Path(path)
    if not path.is_file():
        raise LeaderboardProducerError("UNIVERSE", f"official snapshot missing: {path}")
    raw = path.read_bytes()
    from .canonical import sha256_hex
    return json.loads(raw.decode("utf-8")), sha256_hex(raw)
