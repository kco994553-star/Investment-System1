"""Persist a built leaderboard. Does not call LeaderboardEngine and does not rescore."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .canonical import canonical_bytes, canonical_sha256, sha256_hex
from .errors import LeaderboardProducerError
from .rank import MANIFEST_KIND, MANIFEST_VERSION, RECORD_KIND, RECORD_VERSION


def _date(as_of: str) -> str:
    return as_of[:10]


def snapshots_name(as_of: str) -> str:
    return f"leaderboard_company_snapshots_{_date(as_of)}.jsonl"


def manifest_name(as_of: str) -> str:
    return f"leaderboard_batch_manifest_{_date(as_of)}.json"


def validate_record(rec: Any) -> dict:
    if not isinstance(rec, dict) or rec.get("record_kind") != RECORD_KIND or rec.get("record_version") != RECORD_VERSION:
        raise LeaderboardProducerError("SCHEMA", f"record must be {RECORD_KIND} v{RECORD_VERSION}")
    if rec.get("semantic_sha256") != canonical_sha256(rec.get("semantic")):
        raise LeaderboardProducerError("SEMANTIC_HASH", "leaderboard semantic_sha256 does not match")
    sem = rec["semantic"]
    if sem.get("pass_means") != "VALID_PERSISTENCE_IDENTITY_LINEAGE_AND_EXISTING_RANKING_CONTRACT_ONLY":
        raise LeaderboardProducerError("SCHEMA", "PASS semantics marker missing")
    if sem.get("publication", {}).get("data_state") != "NOT_AVAILABLE" or sem["publication"].get("official") is not False:
        raise LeaderboardProducerError("PROMOTION_FORBIDDEN", "leaderboard record must stay NOT_AVAILABLE and not Official")
    if sem.get("methodology", {}).get("ranking_formula_changed") is not False:
        raise LeaderboardProducerError("RANKING", "ranking formula must stay unchanged")
    if sem.get("methodology", {}).get("recomputed_qgv") is not False:
        raise LeaderboardProducerError("SCORE_MUTATION", "recomputed_qgv must stay false")
    elig = sem.get("eligibility") or {}
    if elig.get("state") == "RANKED":
        scores = sem.get("scores") or {}
        if scores.get("missing_filled") is not False:
            raise LeaderboardProducerError("SCORE_MUTATION", "missing scores must not be filled")
        ranking = sem.get("ranking") or {}
        if ranking.get("qgv_cross_section_rank_used") is not False:
            raise LeaderboardProducerError("RANKING", "QGV cross-section rank must not be used as the leaderboard rank")
        if ranking.get("input_order_is_tie_break_policy") is not False:
            raise LeaderboardProducerError("POLICY_BLOCKED", "input order was promoted to a tie-break policy")
        if sem.get("display", {}).get("market_cap_rank_used_in_ranking") is not False:
            raise LeaderboardProducerError("RANKING", "market-cap rank must not be a ranking input")
        for k in ("daily_move", "consensus", "scenario", "reevaluation_trigger"):
            if sem.get("display", {}).get(k) is not None:
                raise LeaderboardProducerError("SCHEMA", f"display.{k} must stay NOT_AVAILABLE")
    return rec


def validate_manifest(manifest: Any, records: list[dict]) -> dict:
    if not isinstance(manifest, dict) or manifest.get("manifest_kind") != MANIFEST_KIND \
            or manifest.get("manifest_version") != MANIFEST_VERSION:
        raise LeaderboardProducerError("SCHEMA", f"manifest must be {MANIFEST_KIND} v{MANIFEST_VERSION}")
    sem = manifest["semantic"]
    if manifest.get("semantic_sha256") != canonical_sha256(sem):
        raise LeaderboardProducerError("SEMANTIC_HASH", "manifest semantic_sha256 does not match")
    if sem.get("publication", {}).get("data_state") != "NOT_AVAILABLE":
        raise LeaderboardProducerError("PROMOTION_FORBIDDEN", "batch publication must stay NOT_AVAILABLE")
    rows = [
        {
            "company_id": r["semantic"]["company_id"],
            "status": r["semantic"]["status"],
            "eligibility": r["semantic"]["eligibility"]["state"],
            "engine_rank": None if r["semantic"]["ranking"] is None else r["semantic"]["ranking"]["engine_rank"],
            "semantic_sha256": r["semantic_sha256"],
        }
        for r in records
    ]
    if rows != sem["records"] or canonical_sha256(rows) != sem["records_sha256"]:
        raise LeaderboardProducerError("MANIFEST_MISMATCH", "manifest rows differ from the records")
    ids = [r["company_id"] for r in rows]
    if ids != sorted(set(ids)):
        raise LeaderboardProducerError("IDENTITY", "records must be unique and sorted by company_id")
    ranked = [r for r in rows if r["eligibility"] == "RANKED"]
    ranks = [r["engine_rank"] for r in ranked]
    if sorted(ranks) != list(range(1, len(ranked) + 1)):
        raise LeaderboardProducerError("RANKING", "engine ranks are not a permutation of 1..n")
    if len(records) != sem["expected_count"]:
        raise LeaderboardProducerError(
            "PARTIAL_BATCH_HIDDEN", f"expected {sem['expected_count']} company records, have {len(records)}"
        )
    if sem["ranked_count"] + sem["not_ranked_count"] != sem["expected_count"]:
        raise LeaderboardProducerError("MANIFEST_MISMATCH", "ranked + not_ranked != expected")
    if sem["eligible_count"] != sem["ranked_count"]:
        raise LeaderboardProducerError("MANIFEST_MISMATCH", "eligible_count must equal ranked_count (no silent filter)")
    if sem["ranked_count"] != len(ranked):
        raise LeaderboardProducerError("MANIFEST_MISMATCH", "ranked_count disagrees with records")
    return manifest


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def serialize_records(records: list[dict]) -> bytes:
    return b"".join(canonical_bytes(r) + b"\n" for r in records)


def export_batch(records: list[dict], manifest: dict, out_dir: Path | str) -> dict:
    """Validate and write. Ranking is not recomputed here."""
    for r in records:
        validate_record(r)
    validate_manifest(manifest, records)
    out = Path(out_dir)
    body = serialize_records(records)
    as_of = manifest["semantic"]["as_of"]
    written = dict(manifest)
    written["operational"] = {
        **manifest["operational"],
        "files": {snapshots_name(as_of): {"sha256": sha256_hex(body), "bytes": len(body)}},
    }
    _atomic_write(out / snapshots_name(as_of), body)
    text = json.dumps(written, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    _atomic_write(out / manifest_name(as_of), text.encode("utf-8"))
    return written


def load_export(out_dir: Path | str, as_of: str) -> tuple[list[dict], dict]:
    out = Path(out_dir)
    manifest = json.loads((out / manifest_name(as_of)).read_text(encoding="utf-8"))
    body = (out / snapshots_name(as_of)).read_bytes()
    f = (manifest.get("operational") or {}).get("files", {}).get(snapshots_name(as_of))
    if not f or f.get("sha256") != sha256_hex(body):
        raise LeaderboardProducerError("SOURCE_HASH", "snapshot file sha256 does not match the manifest")
    records = [json.loads(line) for line in body.decode("utf-8").splitlines() if line]
    for r in records:
        validate_record(r)
    validate_manifest(manifest, records)
    return records, manifest
