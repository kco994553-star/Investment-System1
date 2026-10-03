"""Read-only boundary to Producer Infrastructure v1. This module defines no snapshot schema.

QGV results are PROVISIONAL_RESEARCH. Infrastructure rejects that status for LIVE and FROZEN_SNAPSHOT,
and Web schema-1 has no research state (P01 is not approved). Track C has not promoted this ranking.
The published leaderboard section is therefore NOT_AVAILABLE.

The registry placeholder reason on PR #9 is LEADERBOARD_NO_UPSTREAM_QGV. That placeholder is not edited
here. This producer does have upstream QGV research records, so the published reason is
LEADERBOARD_RESEARCH_ONLY_NO_EXPORT rather than the stale placeholder.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ..contracts.models import LeaderboardRow, LeaderboardSnapshot
from ..versions import IMPLEMENTATION_KIND
from .canonical import sha256_hex
from .exporter import manifest_name, snapshots_name
from .qgv_input import parse_ts
from .rank import PUBLICATION

INFRA_PIN = {
    "branch": "feature/producer-infrastructure-v1",
    "commit": "6fe9eee5668388fa4a200904520a0b5a46c90b6f",
    "code_commit": "bcfdcd2487f643feddda7a0fa2cace085ffc28a3",
    "src_unchanged_since": "5fa7ce0647b6af91d767c54ecaaa3e31d1ab63e4",
    "pr": 9,
}
EXPECTED_INFRA_API = {
    "investment_system.producers.contract": (
        "CONTRACT", "SCHEMA_VERSION", "RESEARCH_STATUSES", "PUBLISHED_STATES",
        "make_snapshot", "not_available", "validate_snapshot", "file_resolver",
    ),
    "investment_system.producers.adapters": ("leaderboard_section", "WEB_READS", "SECTION_COMPATIBILITY"),
    "investment_system.producers.errors": ("ResearchStatusError",),
    "investment_system.producers.registry": ("DEFAULT_UNAVAILABLE", "default_registry", "ProduceRequest"),
    "investment_system.producers.serialization": ("canonical_sha256", "sha256_hex"),
}
SECTION = "leaderboard"
PRODUCER_ID = "leaderboard.real_research_producer"
REASON_CODE = PUBLICATION["reason_code"]
REASON = (
    "Leaderboard는 QGV PROVISIONAL_RESEARCH 스냅샷에 기존 엔진을 적용한 연구 결과입니다. "
    "Web 연구 상태(P01)와 Track C 검증 전에는 공개하지 않습니다."
)
CANDIDATE_STATE = "FROZEN_SNAPSHOT"
BLOCKERS = (
    "P01_RESEARCH_DATA_STATE_NOT_APPROVED",
    "TRACK_C_VALIDATION_NOT_COMPLETE",
    "WITHIN_TIE_ORDER_POLICY_BLOCKED",
)


def load_infra() -> SimpleNamespace | None:
    mods = {}
    for name in EXPECTED_INFRA_API:
        try:
            mods[name.rsplit(".", 1)[1]] = importlib.import_module(name)
        except ImportError:
            return None
    return SimpleNamespace(**mods)


def missing_api(infra: SimpleNamespace) -> list[str]:
    return [
        f"{mod}.{attr}"
        for mod, attrs in EXPECTED_INFRA_API.items()
        for attr in attrs
        if not hasattr(getattr(infra, mod.rsplit(".", 1)[1]), attr)
    ]


def export_decision(manifest: dict) -> dict:
    sem = manifest["semantic"]
    blockers = list(BLOCKERS)
    if sem.get("within_tie_order_approval") != "POLICY_BLOCKED":
        blockers = [b for b in blockers if b != "WITHIN_TIE_ORDER_POLICY_BLOCKED"]
    return {
        "section": SECTION,
        "data_state": "NOT_AVAILABLE",
        "candidate_state": CANDIDATE_STATE,
        "reason_code": REASON_CODE,
        "blockers": blockers,
        "methodology_status": sem["research_state"]["status"],
        "registry_placeholder_reason_code": "LEADERBOARD_NO_UPSTREAM_QGV",
        "registry_placeholder_note": "PR #9 placeholder. Not used: upstream QGV research records exist. Registry is not modified here.",
    }


def file_inputs(root: Path | str, out_dir: Path | str, as_of: str) -> list[dict]:
    root, out = Path(root).resolve(), Path(out_dir).resolve()
    inputs = []
    for name in (snapshots_name(as_of), manifest_name(as_of)):
        p = out / name
        body = p.read_bytes()
        inputs.append({"artifact_id": "file:" + p.relative_to(root).as_posix(), "sha256": sha256_hex(body), "bytes": len(body)})
    return inputs


def engine_snapshot_from_export(records: list[dict], manifest: dict) -> LeaderboardSnapshot:
    """Deserialize the engine snapshot already stored. Does not sort or rescore."""
    op = manifest["operational"]
    ranked = [r for r in records if r["semantic"]["eligibility"]["state"] == "RANKED"]
    ranked.sort(key=lambda r: r["semantic"]["ranking"]["engine_rank"])
    rows = []
    for r in ranked:
        sem = r["semantic"]
        rows.append(LeaderboardRow(
            rank=sem["ranking"]["engine_rank"],
            company_id=sem["company_id"],
            ticker=sem["ticker"],
            qgv_snapshot_id=r["operational"]["qgv_snapshot_id"],
            Q_score=sem["scores"]["Q_score"],
            G_score=sem["scores"]["G_score"],
            V_score=sem["scores"]["V_score"],
            total_score=sem["scores"]["total_score"],
            freshness=sem["ranking"]["freshness"],
        ))
    return LeaderboardSnapshot(
        leaderboard_snapshot_id=op["leaderboard_snapshot_id"],
        universe_id=manifest["semantic"]["universe"]["universe_id"],
        generated_at=parse_ts(op["generated_at"], "generated_at"),
        rows=tuple(rows),
        implementation_kind=IMPLEMENTATION_KIND,
        recomputed_qgv=False,
    )


def build_infra_snapshots(
    infra: SimpleNamespace,
    records: list[dict],
    manifest: dict,
    *,
    root: Path | str,
    out_dir: Path | str,
    generated_at: str,
    requested_as_of: str | None = None,
) -> dict[str, Any]:
    sem = manifest["semantic"]
    snap = engine_snapshot_from_export(records, manifest)
    scope_kind, data, synthetic = infra.adapters.leaderboard_section(snap)
    methodology = {
        "id": "QGV_LEADERBOARD",
        "version": f"{sem['methodology']['qgv_analysis_contract']}/{sem['methodology']['sort_key_id']}",
        "status": sem["research_state"]["status"],
    }
    candidate = infra.contract.make_snapshot(
        producer_id=PRODUCER_ID,
        producer_version=str(manifest["operational"].get("code_commit")),
        section=SECTION,
        data_state=CANDIDATE_STATE,
        as_of=sem["as_of"],
        requested_as_of=requested_as_of or sem["as_of"],
        generated_at=generated_at,
        methodology=methodology,
        synthetic=synthetic,
        provenance={
            "source": "leaderboard_producer.exporter",
            "inputs": file_inputs(root, out_dir, sem["as_of"]),
            "universe_id": sem["universe"]["universe_id"],
            "manifest_semantic_sha256": manifest["semantic_sha256"],
            "ranking_fingerprint": sem["ranking_fingerprint"],
        },
        validation={
            "status": "PASS",
            "checks": [
                "qgv_semantic_sha256", "universe_members_sha256", "existing_leaderboard_engine",
                "no_score_fill", "publication_not_available",
            ],
            "ranked_count": sem["ranked_count"],
            "pass_means": sem["pass_means"],
        },
        data=data,
        scope_kind=scope_kind,
    )
    candidate_error = None
    try:
        infra.contract.validate_snapshot(candidate)
    except ValueError as e:
        candidate_error = {"type": type(e).__name__, "code": getattr(e, "code", None), "message": str(e)}
    decision = export_decision(manifest)
    published = infra.contract.validate_snapshot(infra.contract.not_available(
        SECTION, PRODUCER_ID, str(manifest["operational"].get("code_commit")), generated_at, REASON, REASON_CODE,
        requested_as_of=requested_as_of or sem["as_of"],
        methodology={
            "id": "QGV_LEADERBOARD",
            "version": methodology["version"],
            "status": "NOT_AVAILABLE",
            "blocker": "; ".join(decision["blockers"]),
        },
    ))
    return {"candidate": candidate, "candidate_error": candidate_error, "published": published, "decision": decision,
            "engine_called": False}
