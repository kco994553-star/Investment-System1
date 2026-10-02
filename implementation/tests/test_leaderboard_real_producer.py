"""Leaderboard REAL producer. Existing engine only. No new ranking formula."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from investment_system.contracts.models import QGVSnapshot
from investment_system.leaderboard_producer.canonical import canonical_sha256
from investment_system.leaderboard_producer.errors import LeaderboardProducerError
from investment_system.leaderboard_producer.exporter import export_batch, load_export
from investment_system.leaderboard_producer.qgv_input import (
    FROZEN_AS_OF,
    members_identity,
    methodology_weights_sha256,
    validate_qgv_record,
)
from investment_system.leaderboard_producer.rank import build_leaderboard
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.leaderboard import LeaderboardEngine
from tests.helpers import complete_obs

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2024-12-31T00:00:00+00:00"
WHEN = datetime(2024, 12, 31, tzinfo=timezone.utc)
GEN = datetime(2026, 10, 1, tzinfo=timezone.utc)
PINNED_SHA = {
    "src/investment_system/qgv/leaderboard.py": "f3246131c2219a6f3ea869aa7c88d6cefb30e735992dbcb3b5fc095ff3565248",
    "src/investment_system/qgv/scoring.py": "1aa4802a65175210be802c7d1d08e17e8af5cfa40a9b6faaa014447354d9e629",
    "src/investment_system/qgv/factors.py": "0df21503c383e3ff79a91bf143c003a8e131718918eb1fe57abecea7e6781a6e",
    "src/investment_system/qgv/analysis.py": "bfd4e1310dde9f908f60a8a2030cb9928f4267f73180c3eb5b12bc7947e3de88",
    "src/investment_system/technical/engine.py": "f7268f52b3134fff8173bcb633552f1b567419aa68afa9977dd98f9846563bdf",
    "src/investment_system/macro/engine.py": "c593a2ef3b1be06960dde46ccc34db9f1858d1357336614ccf15bbb57ccec80b",
    "src/investment_system/qgv/portfolio.py": "ecb44165cb163d2e975e94c39c343a18ed3e2d43538431394065b4523246da49",
    "src/investment_system/personal/portfolio.py": "5b68de0501a7db435d3b21448dc805709b40f250babd7fee1bb264dfa96909d7",
    "src/investment_system/validation/vertical_slice.py": "4ab06fce30064ccf0a54f2c8e6dd39b4b97fdb996511958fac24d25d031a98dc",
}


def _research():
    return {
        "status": "PROVISIONAL_RESEARCH",
        "rule_id": "PROVISIONAL_QG_PRESENT_EQUAL_WEIGHT",
        "v_policy_status": "PROVISIONAL_INITIAL_PRIOR",
        "official_selection": False,
        "official_pass": False,
        "full_pit_pass": False,
        "calibrated": False,
        "track_c_validated": False,
    }


def _snap(company_id: str, score: float, *, synthetic: bool = True) -> QGVSnapshot:
    return AnalysisEngine().analyze(company_id, WHEN, complete_obs(score), synthetic=synthetic)


def _record(snap: QGVSnapshot, *, ticker: str, cross_rank: int = 9, synthetic: bool | None = None) -> dict:
    from investment_system.leaderboard_producer.canonical import to_jsonable
    q = to_jsonable(snap)
    q.pop("qgv_snapshot_id")
    syn = snap.synthetic if synthetic is None else synthetic
    semantic = {
        "company_id": snap.company_id,
        "ticker": ticker,
        "cik": "0000000001",
        "as_of": AS_OF,
        "status": "PASS",
        "status_reasons": [],
        "universe": {"universe_id": "uni_test", "universe_kind": "US_MCAP_TOP500_OFFICIAL", "policy_status": "OFFICIAL"},
        "methodology": {
            "qgv_system_version": snap.qgv_system_version,
            "qgv_standard_version": snap.qgv_standard_version,
            "qgv_analysis_contract": snap.qgv_analysis_contract,
            "implementation_line": snap.implementation_line,
            "weights_sha256": methodology_weights_sha256(),
        },
        "research_state": _research(),
        "synthetic": syn,
        "pit": {
            "fundamentals_available_at": "2024-11-01T00:00:00+00:00",
            "price_observed_at": "2024-12-30T00:00:00+00:00",
            "prior_year_price_observed_at": None,
            "fundamentals_synthetic": syn,
            "known_limitations": ["SEC_COMPANYFACTS_VALUE_MAY_BE_RESTATED"],
        },
        "lineage": {"inputs": [{
            "artifact_id": f"raw:companyfacts:{snap.company_id}",
            "sha256": "a" * 64,
            "source_kind": "SYNTHETIC" if syn else "LIVE_FETCH",
        }]},
        "qgv": q,
        "cross_section": {"rank": cross_rank, "eligible": True, "selected_provisional": True, "n_cross_section": 2},
    }
    rec = {
        "record_kind": "QGV_COMPANY_RESULT",
        "record_version": 1,
        "semantic": semantic,
        "semantic_sha256": canonical_sha256(semantic),
        "operational": {"qgv_snapshot_id": snap.qgv_snapshot_id, "generated_at": GEN.isoformat(), "code_commit": "TEST", "run_id": "t"},
    }
    return validate_qgv_record(rec, require_real=not syn)


def _official(pairs):
    members = []
    for i, (cid, ticker) in enumerate(pairs, start=1):
        members.append({
            "company_id": cid, "ticker": ticker, "cik": "0000000001", "rank": i, "rank_is_lower_bound": False,
        })
    return {"as_of": "2024-12-31", "universe_id": "uni_test", "members": members}


def _manifest(records, official):
    ident = members_identity(official)
    rows = [{
        "company_id": r["semantic"]["company_id"],
        "status": r["semantic"]["status"],
        "status_reasons": r["semantic"]["status_reasons"],
        "semantic_sha256": r["semantic_sha256"],
    } for r in sorted(records, key=lambda r: r["semantic"]["company_id"])]
    sem = {
        "as_of": AS_OF,
        "scope": "FULL_UNIVERSE",
        "expected_count": len(rows),
        "persisted_count": len(rows),
        "records": rows,
        "records_sha256": canonical_sha256(rows),
        "universe": {
            "universe_id": "uni_test",
            "universe_kind": "US_MCAP_TOP500_OFFICIAL",
            "policy_status": "OFFICIAL",
            "membership_basis": "DERIVED_AT_AS_OF",
            "n_members": len(ident),
            "members_sha256": canonical_sha256(ident),
        },
        "methodology": {
            "qgv_system_version": records[0]["semantic"]["methodology"]["qgv_system_version"],
            "qgv_standard_version": records[0]["semantic"]["methodology"]["qgv_standard_version"],
            "qgv_analysis_contract": records[0]["semantic"]["methodology"]["qgv_analysis_contract"],
            "implementation_line": records[0]["semantic"]["methodology"]["implementation_line"],
            "weights_sha256": methodology_weights_sha256(),
        },
        "research_state": _research(),
        "data_lineage": {"inputs_sha256": "b" * 64},
    }
    return {
        "manifest_kind": "QGV_PRODUCER_BATCH_MANIFEST",
        "manifest_version": 1,
        "semantic": sem,
        "semantic_sha256": canonical_sha256(sem),
        "operational": {},
    }


def _run(scores):
    """scores: list of (company_id, ticker, score, cross_rank)."""
    snaps = [( _snap(cid, score), ticker, cross) for cid, ticker, score, cross in scores]
    records = [_record(s, ticker=t, cross_rank=c) for s, t, c in snaps]
    records.sort(key=lambda r: r["semantic"]["company_id"])
    official = _official([(cid, t) for cid, t, _, _ in scores])
    manifest = _manifest(records, official)
    produced, man = build_leaderboard(
        records, manifest, official, "c" * 64, generated_at=GEN, code_commit="TEST", run_id="run-1", require_real=False,
    )
    return produced, man


def test_cross_track_sources_are_unchanged():
    for rel, expect in PINNED_SHA.items():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert digest == expect, rel


def test_engine_ranks_by_existing_total_not_cross_section_or_market_cap():
    produced, man = _run([
        ("zeta", "ZETA", 10.0, 1),
        ("alpha", "ALPH", 90.0, 99),
    ])
    ranked = {r["semantic"]["company_id"]: r for r in produced}
    assert ranked["alpha"]["semantic"]["ranking"]["engine_rank"] == 1
    assert ranked["zeta"]["semantic"]["ranking"]["engine_rank"] == 2
    assert ranked["zeta"]["semantic"]["ranking"]["qgv_cross_section_rank"] == 1
    assert ranked["zeta"]["semantic"]["ranking"]["qgv_cross_section_rank_used"] is False
    assert ranked["alpha"]["semantic"]["display"]["market_cap_rank_used_in_ranking"] is False
    assert ranked["alpha"]["semantic"]["scores"]["total_score"] == ranked["alpha"]["semantic"]["scores"]["total_score"]
    assert man["semantic"]["publication"]["data_state"] == "NOT_AVAILABLE"
    assert man["semantic"]["publication"]["official"] is False
    assert man["semantic"]["research_state"]["track_c_validated"] is False
    assert "BUY_SIGNAL" in man["semantic"]["not_implied"]


def test_market_cap_rank_does_not_change_engine_rank():
    produced, _ = _run([("aaa", "AAA", 50.0, 1), ("bbb", "BBB", 40.0, 2)])
    official = _official([("aaa", "AAA"), ("bbb", "BBB")])
    official["members"][0]["rank"], official["members"][1]["rank"] = 2, 1
    records = []
    # rebuild inputs the same way and only swap display ranks
    snaps = {"aaa": _snap("aaa", 50.0), "bbb": _snap("bbb", 40.0)}
    # New snapshot ids would change operational ids only. Use the same scores via a fresh run's records
    # by calling build again with swapped ranks.
    base_records = [
        _record(snaps["aaa"], ticker="AAA"),
        _record(snaps["bbb"], ticker="BBB"),
    ]
    base_records.sort(key=lambda r: r["semantic"]["company_id"])
    man_in = _manifest(base_records, official)
    produced2, _ = build_leaderboard(
        base_records, man_in, official, "c" * 64, generated_at=GEN, code_commit="TEST", run_id="run-2", require_real=False,
    )
    r1 = {r["semantic"]["company_id"]: r["semantic"]["ranking"]["engine_rank"] for r in produced}
    r2 = {r["semantic"]["company_id"]: r["semantic"]["ranking"]["engine_rank"] for r in produced2}
    assert r1 == r2 == {"aaa": 1, "bbb": 2}
    d1 = {r["semantic"]["company_id"]: r["semantic"]["display"]["market_cap_rank"] for r in produced}
    d2 = {r["semantic"]["company_id"]: r["semantic"]["display"]["market_cap_rank"] for r in produced2}
    assert d1["aaa"] == 1 and d2["aaa"] == 2
    assert d1 != d2


def test_tie_is_policy_blocked_and_not_a_ticker_rule():
    produced, man = _run([("bbb", "BBB", 40.0, 1), ("aaa", "AAA", 40.0, 2)])
    rows = sorted(
        (r for r in produced if r["semantic"]["eligibility"]["state"] == "RANKED"),
        key=lambda r: r["semantic"]["ranking"]["engine_rank"],
    )
    assert rows[0]["semantic"]["company_id"] == "aaa"  # stable sort of company_id input, not an approved policy
    assert rows[0]["semantic"]["ranking"]["rank_band_start"] == rows[1]["semantic"]["ranking"]["rank_band_start"] == 1
    assert rows[0]["semantic"]["ranking"]["tie_size"] == 2
    assert rows[0]["semantic"]["ranking"]["within_tie_order_approval"] == "POLICY_BLOCKED"
    assert rows[0]["semantic"]["ranking"]["input_order_is_tie_break_policy"] is False
    assert man["semantic"]["tie_group_count"] == 1
    assert man["semantic"]["tied_company_count"] == 2
    assert man["semantic"]["within_tie_order_approval"] == "POLICY_BLOCKED"


def test_missing_total_is_not_filled_with_zero():
    snap = _snap("nullco", 10.0)
    rec = _record(snap, ticker="NULL")
    rec["semantic"]["qgv"]["total_score"] = None
    rec["semantic"]["qgv"]["Q_score"] = None
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    other = _record(_snap("keep", 80.0), ticker="KEEP")
    records = sorted([rec, other], key=lambda r: r["semantic"]["company_id"])
    official = _official([("nullco", "NULL"), ("keep", "KEEP")])
    produced, man = build_leaderboard(
        records, _manifest(records, official), official, "d" * 64,
        generated_at=GEN, code_commit="TEST", run_id="run-3", require_real=False,
    )
    null = next(r for r in produced if r["semantic"]["company_id"] == "nullco")
    assert null["semantic"]["scores"]["total_score"] is None
    assert null["semantic"]["scores"]["Q_score"] is None
    assert null["semantic"]["scores"]["missing_filled"] is False
    assert null["semantic"]["eligibility"]["state"] == "RANKED"
    assert null["semantic"]["ranking"]["engine_rank"] == 2
    assert man["semantic"]["null_total_score_count"] == 1
    assert man["semantic"]["eligible_count"] == 2
    assert man["semantic"]["ranked_count"] == 2


def test_zero_q_is_preserved_not_rewritten():
    snap = _snap("zeroq", 25.0)
    rec = _record(snap, ticker="ZERO")
    rec["semantic"]["qgv"]["Q_score"] = 0.0
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    records = [rec]
    official = _official([("zeroq", "ZERO")])
    produced, _ = build_leaderboard(
        records, _manifest(records, official), official, "e" * 64,
        generated_at=GEN, code_commit="TEST", run_id="run-4", require_real=False,
    )
    assert produced[0]["semantic"]["scores"]["Q_score"] == 0.0


def test_partial_and_blocked_are_not_dropped():
    good = _record(_snap("good", 70.0), ticker="GOOD")
    blocked = _record(_snap("blocked", 10.0), ticker="BLK")
    blocked["semantic"]["qgv"]["coverage_state"] = "BLOCKED"
    blocked["semantic"]["qgv"]["total_score"] = None
    blocked["semantic"]["qgv"]["Q_score"] = None
    blocked["semantic_sha256"] = canonical_sha256(blocked["semantic"])
    good["semantic"]["qgv"]["coverage_state"] = "PARTIAL"
    good["semantic_sha256"] = canonical_sha256(good["semantic"])
    records = sorted([good, blocked], key=lambda r: r["semantic"]["company_id"])
    official = _official([("good", "GOOD"), ("blocked", "BLK")])
    produced, man = build_leaderboard(
        records, _manifest(records, official), official, "f" * 64,
        generated_at=GEN, code_commit="TEST", run_id="run-5", require_real=False,
    )
    states = {r["semantic"]["company_id"]: r["semantic"]["eligibility"]["coverage_state"] for r in produced}
    assert states == {"good": "PARTIAL", "blocked": "BLOCKED"}
    assert man["semantic"]["coverage_counts"]["PARTIAL"] == 1
    assert man["semantic"]["coverage_counts"]["BLOCKED"] == 1
    assert man["semantic"]["not_ranked_count"] == 0


def test_upstream_not_run_is_explicit_and_not_scored():
    ranked = _record(_snap("ranked", 55.0), ticker="RAN")
    missing = _record(_snap("missing", 10.0), ticker="MIS")
    missing["semantic"]["status"] = "NOT_RUN"
    missing["semantic"]["status_reasons"] = ["NO_FUNDAMENTALS_AT_AS_OF"]
    missing["semantic"]["qgv"] = None
    missing["semantic_sha256"] = canonical_sha256(missing["semantic"])
    records = sorted([ranked, missing], key=lambda r: r["semantic"]["company_id"])
    official = _official([("ranked", "RAN"), ("missing", "MIS")])
    produced, man = build_leaderboard(
        records, _manifest(records, official), official, "1" * 64,
        generated_at=GEN, code_commit="TEST", run_id="run-6", require_real=False,
    )
    miss = next(r for r in produced if r["semantic"]["company_id"] == "missing")
    assert miss["semantic"]["eligibility"]["state"] == "NOT_RANKED"
    assert miss["semantic"]["scores"] is None
    assert miss["semantic"]["status"] == "PASS"
    assert "UPSTREAM_QGV_NOT_RUN" in miss["semantic"]["status_reasons"]
    assert man["semantic"]["expected_count"] == 2
    assert man["semantic"]["ranked_count"] == 1
    assert man["semantic"]["not_ranked_count"] == 1
    assert man["semantic"]["upstream_not_run_count"] == 1
    assert [r["semantic"]["company_id"] for r in produced] == ["missing", "ranked"]


def test_silent_exclusion_and_identity_and_hash_failures():
    one = _record(_snap("only", 10.0), ticker="ONLY")
    official = _official([("only", "ONLY"), ("gone", "GONE")])
    with pytest.raises(LeaderboardProducerError) as ei:
        build_leaderboard([one], _manifest([one], official), official, "2" * 64,
                          generated_at=GEN, code_commit="TEST", run_id="x", require_real=False)
    assert ei.value.code == "PARTIAL_BATCH_HIDDEN"
    bad = _record(_snap("only", 10.0), ticker="NOPE")
    official1 = _official([("only", "ONLY")])
    with pytest.raises(LeaderboardProducerError) as et:
        build_leaderboard([bad], _manifest([bad], official1), official1, "2" * 64,
                          generated_at=GEN, code_commit="TEST", run_id="x", require_real=False)
    assert et.value.code == "IDENTITY"
    tampered = _record(_snap("only", 10.0), ticker="ONLY")
    tampered["semantic"]["qgv"]["total_score"] = 1.0
    with pytest.raises(LeaderboardProducerError) as eh:
        validate_qgv_record(tampered, require_real=False)
    assert eh.value.code == "SEMANTIC_HASH"


def test_pit_provenance_synthetic_and_promotion_fail_closed():
    rec = _record(_snap("only", 10.0), ticker="ONLY")
    rec["semantic"]["pit"]["fundamentals_available_at"] = "2025-01-02T00:00:00+00:00"
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    with pytest.raises(LeaderboardProducerError) as ep:
        validate_qgv_record(rec, require_real=False)
    assert ep.value.code == "PIT_VIOLATION"
    rec = _record(_snap("only", 10.0), ticker="ONLY")
    rec["semantic"]["lineage"]["inputs"] = []
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    with pytest.raises(LeaderboardProducerError) as eprov:
        validate_qgv_record(rec, require_real=False)
    assert eprov.value.code == "MISSING_PROVENANCE"
    rec = _record(_snap("only", 10.0), ticker="ONLY")
    with pytest.raises(LeaderboardProducerError) as es:
        validate_qgv_record(rec, require_real=True)
    assert es.value.code == "SYNTHETIC_STATE"
    rec = _record(_snap("only", 10.0), ticker="ONLY")
    rec["semantic"]["research_state"]["status"] = "OFFICIAL"
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    with pytest.raises(LeaderboardProducerError) as eo:
        validate_qgv_record(rec, require_real=False)
    assert eo.value.code == "PROMOTION_FORBIDDEN"


def test_future_as_of_is_policy_blocked():
    rec = _record(_snap("only", 10.0), ticker="ONLY")
    official = _official([("only", "ONLY")])
    man = _manifest([rec], official)
    man["semantic"]["as_of"] = "2025-03-31T00:00:00+00:00"
    rec["semantic"]["as_of"] = man["semantic"]["as_of"]
    rec["semantic"]["qgv"]["as_of"] = man["semantic"]["as_of"]
    rec["semantic_sha256"] = canonical_sha256(rec["semantic"])
    man["semantic"]["records"][0]["semantic_sha256"] = rec["semantic_sha256"]
    man["semantic"]["records_sha256"] = canonical_sha256(man["semantic"]["records"])
    man["semantic_sha256"] = canonical_sha256(man["semantic"])
    assert "2025-03-31" not in FROZEN_AS_OF
    with pytest.raises(LeaderboardProducerError) as e:
        build_leaderboard([rec], man, official, "3" * 64, generated_at=GEN, code_commit="TEST", run_id="x", require_real=False)
    assert e.value.code == "POLICY_BLOCKED"


def test_replay_is_deterministic_and_exporter_does_not_rank(tmp_path):
    spec = [("aaa", "AAA", 30.0, 2), ("bbb", "BBB", 70.0, 1)]
    produced, man = _run(spec)
    produced2, man2 = _run(spec)
    assert [r["semantic_sha256"] for r in produced] == [r["semantic_sha256"] for r in produced2]
    assert man["semantic_sha256"] == man2["semantic_sha256"]
    assert man["semantic"]["ranking_fingerprint"] == man2["semantic"]["ranking_fingerprint"]
    assert produced[0]["operational"]["qgv_snapshot_id"] != produced2[0]["operational"]["qgv_snapshot_id"]
    def _boom(*_a, **_k):
        raise AssertionError("exporter recalculated ranking")
    original = LeaderboardEngine.build
    LeaderboardEngine.build = _boom
    try:
        written = export_batch(produced, man, tmp_path)
        loaded, loaded_man = load_export(tmp_path, AS_OF)
    finally:
        LeaderboardEngine.build = original
    assert [r["semantic_sha256"] for r in loaded] == [r["semantic_sha256"] for r in produced]
    assert loaded_man["semantic_sha256"] == man["semantic_sha256"]
    assert written["operational"]["files"]


def test_score_change_changes_fingerprint_without_rescore():
    _, a = _run([("aaa", "AAA", 30.0, 1), ("bbb", "BBB", 70.0, 2)])
    _, b = _run([("aaa", "AAA", 35.0, 1), ("bbb", "BBB", 70.0, 2)])
    assert a["semantic"]["ranking_fingerprint"] != b["semantic"]["ranking_fingerprint"]


def test_search_ranking_is_not_an_input():
    src = (ROOT / "src/investment_system/leaderboard_producer/rank.py").read_text()
    assert "entity-search" not in src
    assert "def engine_sort_key" in src
    body = src.split("def engine_sort_key", 1)[1].split("def ", 1)[0]
    assert "market_cap" not in body
    assert "consensus" not in body
    assert "portfolio" not in body.lower()


def test_universe_and_qgv_hash_are_preserved():
    produced, man = _run([("aaa", "AAA", 30.0, 1)])
    assert produced[0]["semantic"]["universe"]["members_sha256"] == man["semantic"]["universe"]["members_sha256"]
    assert produced[0]["semantic"]["source"]["qgv_semantic_sha256"]
    assert produced[0]["semantic"]["lineage"]["official_snapshot_sha256"] == "c" * 64
    assert produced[0]["semantic"]["display"]["daily_move"] is None
    assert produced[0]["semantic"]["display"]["consensus"] is None
    assert produced[0]["semantic"]["display"]["scenario"] is None
    assert produced[0]["semantic"]["display"]["reevaluation_trigger"] is None


def test_committed_real_evidence_if_present():
    out = ROOT / "reports" / "leaderboard_producer" / "full"
    if not (out / "leaderboard_batch_manifest_2024-12-31.json").is_file():
        return
    for day in FROZEN_AS_OF:
        records, man = load_export(out, day)
        sem = man["semantic"]
        assert sem["expected_count"] == 500
        assert sem["ranked_count"] == 500
        assert sem["not_ranked_count"] == 0
        assert sem["publication"]["data_state"] == "NOT_AVAILABLE"
        assert sem["publication"]["official"] is False
        assert sem["research_state"]["status"] == "PROVISIONAL_RESEARCH"
        assert sem["research_state"]["track_c_validated"] is False
        assert sem["within_tie_order_approval"] == "POLICY_BLOCKED"
        assert sem["tie_group_count"] == 1
        assert sem["qgv_cross_section_rank_used"] is False
        assert sem["methodology"]["ranking_formula_changed"] is False
        assert all(r["semantic"]["scores"]["missing_filled"] is False for r in records)
        assert all(r["semantic"]["display"]["consensus"] is None for r in records)
        assert any(r["semantic"]["eligibility"]["coverage_state"] == "BLOCKED" for r in records)
        assert any(r["semantic"]["eligibility"]["coverage_state"] == "PARTIAL" for r in records)
        assert not any(r["semantic"]["eligibility"]["coverage_state"] == "READY" for r in records)


def test_real_replay_matches_committed_evidence_when_qgv_export_present():
    exports = os.environ.get("LEADERBOARD_QGV_EXPORTS")
    out = ROOT / "reports" / "leaderboard_producer" / "full"
    if not exports or not (out / "leaderboard_batch_manifest_2024-12-31.json").is_file():
        return
    from investment_system.leaderboard_producer.qgv_input import load_official_snapshot, load_qgv_export
    official_dir = ROOT / "reports" / "gate_evidence"
    for day in FROZEN_AS_OF:
        records, manifest = load_qgv_export(exports, day)
        official, official_sha = load_official_snapshot(official_dir / f"official_snapshot_{day}.json")
        produced, built = build_leaderboard(
            records, manifest, official, official_sha, generated_at=GEN, code_commit="REPLAY", run_id="replay", require_real=True,
        )
        committed, committed_man = load_export(out, day)
        assert built["semantic_sha256"] == committed_man["semantic_sha256"]
        assert [r["semantic_sha256"] for r in produced] == [r["semantic_sha256"] for r in committed]
        for src, row in zip(sorted(records, key=lambda r: r["semantic"]["company_id"]), produced):
            if src["semantic"]["status"] != "PASS":
                continue
            assert row["semantic"]["scores"]["Q_score"] == src["semantic"]["qgv"]["Q_score"]
            assert row["semantic"]["scores"]["G_score"] == src["semantic"]["qgv"]["G_score"]
            assert row["semantic"]["scores"]["V_score"] == src["semantic"]["qgv"]["V_score"]
            assert row["semantic"]["scores"]["total_score"] == src["semantic"]["qgv"]["total_score"]
            assert row["semantic"]["source"]["qgv_semantic_sha256"] == src["semantic_sha256"]
