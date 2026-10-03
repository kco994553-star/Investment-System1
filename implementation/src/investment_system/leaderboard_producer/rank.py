"""Apply the existing LeaderboardEngine. Do not reimplement the sort to 'improve' it.

The engine key, copied here only so tie groups can be labeled, is::

    (total_score is not None, total_score or -1, Q_score or -1)  # reverse=True

`or -1` is the engine's sentinel (a 0.0 Q score sorts as -1). Stored scores are never rewritten.
There is no approved tie-break. Input order is the QGV export order (company_id ascending) so the
engine's stable sort is replayable. Distinct engine ranks inside a tie are POLICY_BLOCKED, not a new rule.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping
from uuid import uuid4

from ..contracts.models import QGVSnapshot
from ..qgv.leaderboard import LeaderboardEngine
from ..versions import IMPLEMENTATION_KIND
from .canonical import canonical_sha256, to_jsonable
from .errors import LeaderboardProducerError
from .qgv_input import (
    QGV_PIN,
    members_identity,
    qgv_snapshot_from_record,
    validate_qgv_manifest,
    validate_qgv_record,
)

RECORD_KIND = "LEADERBOARD_COMPANY_RESULT"
RECORD_VERSION = 1
MANIFEST_KIND = "LEADERBOARD_PRODUCER_BATCH_MANIFEST"
MANIFEST_VERSION = 1
SORT_KEY_ID = "EXISTING_TOTAL_PRESENT_THEN_TOTAL_OR_SENTINEL_THEN_Q_OR_SENTINEL"
INPUT_ORDER = "QGV_RECORD_COMPANY_ID_ASCENDING"
PASS_MEANS = "VALID_PERSISTENCE_IDENTITY_LINEAGE_AND_EXISTING_RANKING_CONTRACT_ONLY"
NOT_IMPLIED = (
    "ATTRACTIVE",
    "QGV_FULLY_SCORED",
    "STRATEGY_VALIDATED",
    "STATISTICAL_SKILL",
    "OFFICIAL_RECOMMENDATION",
    "BUY_SIGNAL",
)
PUBLICATION = {
    "data_state": "NOT_AVAILABLE",
    "reason_code": "LEADERBOARD_RESEARCH_ONLY_NO_EXPORT",
    "official": False,
    "live": False,
}
WEB_FIELD_STATUS = {
    "rows[].rank": "AVAILABLE",
    "rows[].company_id": "AVAILABLE",
    "rows[].ticker": "AVAILABLE",
    "rows[].total_score": "AVAILABLE",
    "rows[].market_cap_rank": "DERIVABLE_WITHOUT_SEMANTIC_CHANGE",
    "rows[].daily_move": "DATA_BLOCKED",
    "rows[].consensus": "NOT_AVAILABLE",
    "rows[].scenario": "DATA_BLOCKED",
    "rows[].reevaluation_trigger": "NOT_AVAILABLE",
}
ELIGIBILITY_RULE = "NO_SEPARATE_RULE_ENGINE_RANKS_EVERY_PASS_SNAPSHOT"


def engine_sort_key(snapshot: QGVSnapshot) -> tuple:
    """Must stay identical to LeaderboardEngine.build. Not a new formula."""
    return (snapshot.total_score is not None, snapshot.total_score or -1, snapshot.Q_score or -1)


def _lineage_inputs(sem: Mapping) -> list[dict]:
    out = []
    for i in sem["lineage"]["inputs"]:
        out.append({
            "artifact_id": i["artifact_id"],
            "sha256": i["sha256"],
            **({"bytes": i["bytes"]} if "bytes" in i else {}),
        })
    return out


def _research(sem: Mapping) -> dict:
    rs = dict(sem["research_state"])
    # Preserve verbatim keys. Do not add OFFICIAL.
    return rs


def _display(member: Mapping | None) -> dict:
    rank = None if member is None else member.get("rank")
    lower = None if member is None else member.get("rank_is_lower_bound")
    return {
        "market_cap_rank": rank,
        "market_cap_rank_is_lower_bound": lower,
        "market_cap_rank_source": "official_snapshot.members.rank" if rank is not None else "NOT_AVAILABLE",
        "market_cap_rank_used_in_ranking": False,
        "daily_move": None,
        "consensus": None,
        "scenario": None,
        "reevaluation_trigger": None,
    }


def _not_ranked_semantic(
    rec: Mapping,
    *,
    universe: Mapping,
    methodology: Mapping,
    manifest_sha: str,
    official_sha: str,
    reason: str,
) -> dict:
    sem = rec["semantic"]
    return {
        "as_of": sem["as_of"],
        "company_id": sem["company_id"],
        "ticker": sem["ticker"],
        "status": "PASS",
        "status_reasons": [reason],
        "pass_means": PASS_MEANS,
        "not_implied": list(NOT_IMPLIED),
        "eligibility": {
            "state": "NOT_RANKED",
            "rule_id": ELIGIBILITY_RULE,
            "partial_blocked_filter": "NOT_DEFINED_NOT_INVENTED",
            "upstream_qgv_status": sem["status"],
            "upstream_status_reasons": list(sem["status_reasons"]),
            "coverage_state": None if not isinstance(sem.get("qgv"), dict) else sem["qgv"].get("coverage_state"),
        },
        "ranking": None,
        "scores": None,
        "source": {
            "qgv_record_kind": rec["record_kind"],
            "qgv_record_version": rec["record_version"],
            "qgv_semantic_sha256": rec["semantic_sha256"],
        },
        "display": {"market_cap_rank": None, "market_cap_rank_used_in_ranking": False,
                    "daily_move": None, "consensus": None, "scenario": None, "reevaluation_trigger": None},
        "universe": universe,
        "methodology": methodology,
        "research_state": _research(sem),
        "pit": sem.get("pit"),
        "lineage": {
            "inputs": _lineage_inputs(sem) if sem.get("lineage", {}).get("inputs") else [],
            "qgv_manifest_semantic_sha256": manifest_sha,
            "official_snapshot_sha256": official_sha,
        },
        "publication": dict(PUBLICATION),
    }


def build_leaderboard(
    qgv_records: list[dict],
    qgv_manifest: dict,
    official: Mapping,
    official_sha256: str,
    *,
    generated_at: datetime,
    code_commit: str,
    run_id: str | None = None,
    require_real: bool = True,
) -> tuple[list[dict], dict]:
    """Return (company records, manifest). Does not write files and does not rescore."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise LeaderboardProducerError("PIT_EVIDENCE_MISSING", "generated_at must be timezone-aware")
    for rec in qgv_records:
        validate_qgv_record(rec, require_real=require_real)
    validate_qgv_manifest(qgv_manifest, qgv_records)
    sem = qgv_manifest["semantic"]
    if sem.get("research_state", {}).get("status") != "PROVISIONAL_RESEARCH":
        raise LeaderboardProducerError("PROMOTION_FORBIDDEN", "QGV batch research status is not PROVISIONAL_RESEARCH")
    if sem.get("research_state", {}).get("track_c_validated") is not False:
        raise LeaderboardProducerError("PROMOTION_FORBIDDEN", "QGV batch must not claim Track C validation")
    as_of = parse_as_of(sem["as_of"])
    if as_of > generated_at:
        raise LeaderboardProducerError("PIT_VIOLATION", "as_of is later than generated_at")
    ident = members_identity(official)
    members_sha = canonical_sha256(ident)
    if members_sha != sem["universe"]["members_sha256"]:
        raise LeaderboardProducerError("UNIVERSE_HASH", "official snapshot members hash differs from the QGV manifest")
    if official.get("universe_id") != sem["universe"]["universe_id"]:
        raise LeaderboardProducerError("UNIVERSE_HASH", "official snapshot universe_id differs from the QGV manifest")
    if str(official.get("as_of", ""))[:10] != sem["as_of"][:10]:
        raise LeaderboardProducerError("UNIVERSE", "official snapshot as_of date differs from the QGV batch")
    if len(ident) != sem["universe"]["n_members"] or len(ident) != sem["expected_count"]:
        raise LeaderboardProducerError("PARTIAL_BATCH_HIDDEN", "official member count differs from the QGV expected count")
    by_id = {m["company_id"]: m for m in official["members"]}
    if len(by_id) != len(official["members"]):
        raise LeaderboardProducerError("IDENTITY", "duplicate company_id in the official snapshot")
    qgv_ids = [r["semantic"]["company_id"] for r in qgv_records]
    if set(qgv_ids) != set(by_id):
        missing = sorted(set(by_id) - set(qgv_ids))
        extra = sorted(set(qgv_ids) - set(by_id))
        raise LeaderboardProducerError("PARTIAL_BATCH_HIDDEN", f"universe/QGV member mismatch missing={missing[:5]} extra={extra[:5]}")
    for rec in qgv_records:
        member = by_id[rec["semantic"]["company_id"]]
        if member["ticker"] != rec["semantic"]["ticker"]:
            raise LeaderboardProducerError(
                "IDENTITY", f"{rec['semantic']['company_id']}: ticker {rec['semantic']['ticker']!r} != universe {member['ticker']!r}"
            )

    universe = {
        "universe_id": sem["universe"]["universe_id"],
        "universe_kind": sem["universe"]["universe_kind"],
        "policy_status": sem["universe"]["policy_status"],
        "membership_basis": sem["universe"]["membership_basis"],
        "members_sha256": members_sha,
        "n_members": len(ident),
    }
    method_src = sem["methodology"]
    methodology = {
        "leaderboard_spec": "QGV Leaderboard Specification v1.0",
        "leaderboard_engine": "investment_system.qgv.leaderboard.LeaderboardEngine.build",
        "sort_key_id": SORT_KEY_ID,
        "input_order": INPUT_ORDER,
        "input_order_is_tie_break_policy": False,
        "ranking_formula_changed": False,
        "qgv_system_version": method_src.get("qgv_system_version"),
        "qgv_standard_version": method_src.get("qgv_standard_version"),
        "qgv_analysis_contract": method_src.get("qgv_analysis_contract"),
        "implementation_line": method_src.get("implementation_line"),
        "implementation_kind": IMPLEMENTATION_KIND,
        "weights_sha256": method_src.get("weights_sha256"),
        "recomputed_qgv": False,
    }
    manifest_sha = qgv_manifest["semantic_sha256"]
    rankable = [r for r in qgv_records if r["semantic"]["status"] == "PASS"]
    withheld = [r for r in qgv_records if r["semantic"]["status"] != "PASS"]
    # Declared input order. This is not an approved tie-break; see CONTRACT.md.
    rankable = sorted(rankable, key=lambda r: r["semantic"]["company_id"])
    snapshots = [qgv_snapshot_from_record(r) for r in rankable]
    tickers = {r["semantic"]["company_id"]: r["semantic"]["ticker"] for r in rankable}
    before = [(s.company_id, s.Q_score, s.G_score, s.V_score, s.total_score, s.coverage_state) for s in snapshots]
    lb = LeaderboardEngine().build(universe["universe_id"], generated_at, snapshots, tickers=tickers)
    after = [(s.company_id, s.Q_score, s.G_score, s.V_score, s.total_score, s.coverage_state) for s in snapshots]
    if after != before:
        raise LeaderboardProducerError("SCORE_MUTATION", "LeaderboardEngine mutated QGV scores")
    if lb.recomputed_qgv:
        raise LeaderboardProducerError("SCORE_MUTATION", "engine reported recomputed_qgv")
    expected_order = [s.company_id for s in sorted(snapshots, key=engine_sort_key, reverse=True)]
    got_order = [row.company_id for row in lb.rows]
    if got_order != expected_order:
        raise LeaderboardProducerError("RANKING", "engine order does not match its own sort key; refusing to relabel ranks")
    if len(lb.rows) != len(rankable):
        raise LeaderboardProducerError("PARTIAL_BATCH_HIDDEN", "engine dropped or added a company")

    by_snap = {s.company_id: s for s in snapshots}
    by_rec = {r["semantic"]["company_id"]: r for r in rankable}
    bands: list[list[Any]] = []
    for row in lb.rows:
        key = engine_sort_key(by_snap[row.company_id])
        if not bands or bands[-1][0] != key:
            bands.append([key, []])
        bands[-1][1].append(row)
    rank_meta = {}
    for group in bands:
        rows = group[1]
        start = rows[0].rank
        approval = "NOT_APPLICABLE" if len(rows) == 1 else "POLICY_BLOCKED"
        for row in rows:
            rank_meta[row.company_id] = (start, len(rows), approval)

    produced = []
    for row in lb.rows:
        rec = by_rec[row.company_id]
        snap = by_snap[row.company_id]
        q = rec["semantic"]["qgv"]
        if (row.Q_score, row.G_score, row.V_score, row.total_score) != (
            snap.Q_score, snap.G_score, snap.V_score, snap.total_score
        ):
            raise LeaderboardProducerError("SCORE_MUTATION", f"{row.company_id}: engine row scores differ from the snapshot")
        if row.qgv_snapshot_id != rec["operational"]["qgv_snapshot_id"]:
            raise LeaderboardProducerError("IDENTITY", f"{row.company_id}: qgv_snapshot_id was not preserved")
        if row.ticker != rec["semantic"]["ticker"]:
            raise LeaderboardProducerError("IDENTITY", f"{row.company_id}: ticker was not preserved")
        band_start, tie_size, approval = rank_meta[row.company_id]
        cross = rec["semantic"].get("cross_section") or {}
        semantic = {
            "as_of": rec["semantic"]["as_of"],
            "company_id": row.company_id,
            "ticker": row.ticker,
            "status": "PASS",
            "status_reasons": [],
            "pass_means": PASS_MEANS,
            "not_implied": list(NOT_IMPLIED),
            "eligibility": {
                "state": "RANKED",
                "rule_id": ELIGIBILITY_RULE,
                "partial_blocked_filter": "NOT_DEFINED_NOT_INVENTED",
                "upstream_qgv_status": "PASS",
                "upstream_status_reasons": list(rec["semantic"]["status_reasons"]),
                "coverage_state": q.get("coverage_state"),
            },
            "ranking": {
                "engine": methodology["leaderboard_engine"],
                "engine_rank": row.rank,
                "sort_key_id": SORT_KEY_ID,
                "rank_band_start": band_start,
                "tie_size": tie_size,
                "within_tie_order_approval": approval,
                "input_order": INPUT_ORDER,
                "input_order_is_tie_break_policy": False,
                "recomputed_qgv": False,
                "qgv_cross_section_rank_used": False,
                "qgv_cross_section_rank": cross.get("rank"),
                "qgv_cross_section_eligible": cross.get("eligible"),
                "freshness": row.freshness,
            },
            "scores": {
                "Q_score": q.get("Q_score"),
                "G_score": q.get("G_score"),
                "V_score": q.get("V_score"),
                "total_score": q.get("total_score"),
                "missing_filled": False,
            },
            "source": {
                "qgv_record_kind": rec["record_kind"],
                "qgv_record_version": rec["record_version"],
                "qgv_semantic_sha256": rec["semantic_sha256"],
            },
            "display": _display(by_id[row.company_id]),
            "universe": universe,
            "methodology": methodology,
            "research_state": _research(rec["semantic"]),
            "pit": {
                "fundamentals_available_at": rec["semantic"]["pit"].get("fundamentals_available_at"),
                "price_observed_at": rec["semantic"]["pit"].get("price_observed_at"),
                "prior_year_price_observed_at": rec["semantic"]["pit"].get("prior_year_price_observed_at"),
                "known_limitations": list(rec["semantic"]["pit"].get("known_limitations") or []),
            },
            "lineage": {
                "inputs": _lineage_inputs(rec["semantic"]),
                "qgv_manifest_semantic_sha256": manifest_sha,
                "official_snapshot_sha256": official_sha256,
                "qgv_pin": dict(QGV_PIN),
            },
            "publication": dict(PUBLICATION),
        }
        produced.append(_finish(semantic, {
            "generated_at": generated_at.isoformat(),
            "code_commit": code_commit,
            "run_id": run_id or f"lb_{uuid4().hex[:12]}",
            "leaderboard_snapshot_id": lb.leaderboard_snapshot_id,
            "qgv_snapshot_id": row.qgv_snapshot_id,
        }))

    for rec in withheld:
        reason = "UPSTREAM_QGV_" + rec["semantic"]["status"]
        semantic = _not_ranked_semantic(
            rec, universe=universe, methodology=methodology, manifest_sha=manifest_sha,
            official_sha=official_sha256, reason=reason,
        )
        produced.append(_finish(semantic, {
            "generated_at": generated_at.isoformat(),
            "code_commit": code_commit,
            "run_id": produced[0]["operational"]["run_id"] if produced else (run_id or f"lb_{uuid4().hex[:12]}"),
            "leaderboard_snapshot_id": lb.leaderboard_snapshot_id,
            "qgv_snapshot_id": None,
        }))
    produced.sort(key=lambda r: r["semantic"]["company_id"])
    if [r["semantic"]["company_id"] for r in produced] != sorted(by_id):
        raise LeaderboardProducerError("PARTIAL_BATCH_HIDDEN", "a universe member has no leaderboard record")

    ranked = [r for r in produced if r["semantic"]["eligibility"]["state"] == "RANKED"]
    ranked_by_rank = sorted(ranked, key=lambda r: r["semantic"]["ranking"]["engine_rank"])
    fingerprint_rows = [
        {
            "company_id": r["semantic"]["company_id"],
            "engine_rank": r["semantic"]["ranking"]["engine_rank"],
            "rank_band_start": r["semantic"]["ranking"]["rank_band_start"],
            "tie_size": r["semantic"]["ranking"]["tie_size"],
            "within_tie_order_approval": r["semantic"]["ranking"]["within_tie_order_approval"],
            "Q_score": r["semantic"]["scores"]["Q_score"],
            "G_score": r["semantic"]["scores"]["G_score"],
            "V_score": r["semantic"]["scores"]["V_score"],
            "total_score": r["semantic"]["scores"]["total_score"],
            "coverage_state": r["semantic"]["eligibility"]["coverage_state"],
            "qgv_semantic_sha256": r["semantic"]["source"]["qgv_semantic_sha256"],
        }
        for r in ranked_by_rank
    ]
    coverage: dict[str, int] = {}
    for r in ranked:
        c = r["semantic"]["eligibility"]["coverage_state"] or "NONE"
        coverage[c] = coverage.get(c, 0) + 1
    tie_groups = {}
    for r in ranked:
        if r["semantic"]["ranking"]["tie_size"] > 1:
            tie_groups.setdefault(r["semantic"]["ranking"]["rank_band_start"], 0)
            tie_groups[r["semantic"]["ranking"]["rank_band_start"]] += 1
    cross_eligible = sum(1 for r in ranked if r["semantic"]["ranking"]["qgv_cross_section_eligible"] is True)
    null_totals = sum(1 for r in ranked if r["semantic"]["scores"]["total_score"] is None)
    manifest_sem = {
        "as_of": sem["as_of"],
        "universe": universe,
        "expected_count": len(ident),
        "eligible_count": len(rankable),
        "eligibility_rule": ELIGIBILITY_RULE,
        "partial_blocked_policy": "NOT_DEFINED_FOLLOWED_EXISTING_ENGINE_INCLUDE",
        "ranked_count": len(ranked),
        "not_ranked_count": len(withheld),
        "upstream_fail_count": sum(1 for r in withheld if r["semantic"]["status"] == "FAIL"),
        "upstream_not_run_count": sum(1 for r in withheld if r["semantic"]["status"] == "NOT_RUN"),
        "coverage_counts": dict(sorted(coverage.items())),
        "null_total_score_count": null_totals,
        "qgv_cross_section_eligible_count": cross_eligible,
        "qgv_cross_section_rank_used": False,
        "tie_group_count": len(tie_groups),
        "tied_company_count": sum(tie_groups.values()),
        "within_tie_order_approval": "POLICY_BLOCKED" if tie_groups else "NOT_APPLICABLE",
        "ranking_fingerprint": canonical_sha256(fingerprint_rows),
        "input_snapshot_hashes": {
            "qgv_manifest_semantic_sha256": manifest_sha,
            "qgv_records_sha256": sem["records_sha256"],
            "official_snapshot_sha256": official_sha256,
            "qgv_inputs_sha256": sem.get("data_lineage", {}).get("inputs_sha256"),
        },
        "methodology": methodology,
        "research_state": dict(sem["research_state"]),
        "lineage_hash": canonical_sha256({
            "qgv_manifest_semantic_sha256": manifest_sha,
            "official_snapshot_sha256": official_sha256,
            "members_sha256": members_sha,
            "ranking_fingerprint_input": fingerprint_rows,
        }),
        "web_field_status": dict(WEB_FIELD_STATUS),
        "publication": dict(PUBLICATION),
        "pass_means": PASS_MEANS,
        "not_implied": list(NOT_IMPLIED),
        "records": [
            {
                "company_id": r["semantic"]["company_id"],
                "status": r["semantic"]["status"],
                "eligibility": r["semantic"]["eligibility"]["state"],
                "engine_rank": None if r["semantic"]["ranking"] is None else r["semantic"]["ranking"]["engine_rank"],
                "semantic_sha256": r["semantic_sha256"],
            }
            for r in produced
        ],
        "qgv_pin": dict(QGV_PIN),
    }
    manifest_sem["records_sha256"] = canonical_sha256(manifest_sem["records"])
    # lineage_hash was computed before records_sha256 existed; keep it as the input fingerprint only.
    manifest = {
        "manifest_kind": MANIFEST_KIND,
        "manifest_version": MANIFEST_VERSION,
        "semantic": to_jsonable(manifest_sem),
        "semantic_sha256": canonical_sha256(manifest_sem),
        "operational": {
            "generated_at": generated_at.isoformat(),
            "code_commit": code_commit,
            "run_id": produced[0]["operational"]["run_id"] if produced else run_id,
            "leaderboard_snapshot_id": lb.leaderboard_snapshot_id,
        },
    }
    return produced, manifest


def parse_as_of(value: str) -> datetime:
    from .qgv_input import parse_ts
    return parse_ts(value, "as_of")


def _finish(semantic: dict, operational: dict) -> dict:
    sem = to_jsonable(semantic)
    return {
        "record_kind": RECORD_KIND,
        "record_version": RECORD_VERSION,
        "semantic": sem,
        "semantic_sha256": canonical_sha256(sem),
        "operational": to_jsonable(operational),
    }
