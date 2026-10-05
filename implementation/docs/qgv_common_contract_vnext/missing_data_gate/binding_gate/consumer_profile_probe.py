#!/usr/bin/env python3
"""Read-only legacy consumer/profile characterization. No production mutation.

Run with the owner implementation/src on PYTHONPATH and --out in scratch. The
publication family runs in a subprocess with the pinned integration source on
PYTHONPATH so module imports cannot silently mix two source trees. Synthetic
registry nodes and the local-only grant fixture are never activated or stored.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile


INTEGRATION_PIN = "523e702a806a718d163cfbf62aa3fc29d8c3ef3c"


def check(checks: list[str], condition: bool, description: str) -> None:
    assert condition, description
    checks.append(description)


def publication_probe() -> dict:
    from investment_system.publication.authorization import ACTIVE_AUTHORIZATIONS
    from investment_system.publication.errors import PromotionForbidden
    from investment_system.publication.facts import make_fact
    from investment_system.publication.predicate import decide, reject_promotion

    checks: list[str] = []
    fact = make_fact(
        subject_sha256="a" * 64,
        persisted_fingerprint="a" * 64,
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
    # These manufactured facts are not real company evidence. synthetic=False
    # characterizes the predicate's partial-disclosure branch, not authenticity.
    grant = {
        "contract": "PUBLICATION_AUTHORIZATION",
        "schema_version": 1,
        "grant_kind": "RESEARCH_DISPLAY",
        "authorization_id": "SYNTHETIC_CONSUMER_REVIEW_ONLY",
        "subject_sha256": "a" * 64,
        "issued_at": "2026-10-05T12:05:31+09:00",
        "explicit_event": True,
    }
    without = decide(fact)
    with_fixture = decide(fact, (grant,))
    blocked = decide({**fact, "data_completeness": "BLOCKED"}, (grant,))
    check(checks, ACTIVE_AUTHORIZATIONS == (), "production active grants remain empty")
    check(checks, without["publication_mode"] == "NOT_AVAILABLE", "partial without grant stays NOT_AVAILABLE")
    check(checks, with_fixture["publication_mode"] == "DISPLAY_RESEARCH", "partial with local fixture grant allows DISPLAY_RESEARCH")
    check(checks, with_fixture["reasons"] == ("DISCLOSURE_PARTIAL",), "fixture-granted partial disclosure reason preserved")
    check(checks, blocked["publication_mode"] == "NOT_AVAILABLE", "BLOCKED with fixture grant stays NOT_AVAILABLE")
    check(checks, "BLOCKED_NOT_A_SCORE" in blocked["reasons"], "BLOCKED reason remains explicit")
    rejected = []
    for requested in ("LIVE", "OFFICIAL"):
        try:
            reject_promotion(requested)
        except PromotionForbidden as exc:
            rejected.append(str(exc))
            check(checks, True, f"{requested} promotion rejected")
        else:
            raise AssertionError(f"{requested} promotion accepted")
    return {
        "checks": checks,
        "case": {
            "case_id": "CP-PUBLICATION-INDEPENDENT",
            "fixture": "Manufactured eligibility facts and local-only grant; not real company evidence or authorization",
            "actual": {
                "active_authorizations": [],
                "partial_without_grant": without,
                "partial_with_fixture_grant": with_fixture,
                "blocked_with_fixture_grant": blocked,
                "rejected_promotions": rejected,
            },
        },
    }


def owner_probe(repo: Path) -> tuple[list[str], list[dict]]:
    from investment_system.contracts.enums import ProfileKind, QualityState
    from investment_system.contracts.models import FactorObservation
    from investment_system.contracts.strategy import custom_profile
    from investment_system.personal.quality import DataQuality, is_actionable
    from investment_system.personal.versioning import ResultNamespace, content_hash
    from investment_system.personal.weights import (
        Maturity, NodeDefinition, NodeType, OfficialRegistry,
        PersonalStrategyVersion, StrategyStatus, WeightOverride, WeightTreeError,
        effective_tree,
    )
    from investment_system.qgv.analysis import AnalysisEngine
    from investment_system.qgv.leaderboard import LeaderboardEngine
    from investment_system.validation.vertical_slice import rank_cross_section

    checks: list[str] = []
    golden_path = repo / "implementation/docs/qgv_common_contract_vnext/golden_cases.json"
    golden = json.loads(golden_path.read_text())

    def analyze(case_id: str, company_id: str):
        case = next(c for c in golden["cases"] if c["case_id"] == case_id)
        observations = {
            v["factor_id"]: FactorObservation(**{**v, "quality": QualityState(v["quality"])})
            for v in case["observations"]
        }
        return AnalysisEngine().analyze(
            company_id, datetime.fromisoformat(case["as_of"]), observations,
            profile_kind=ProfileKind(case["profile_kind"]),
            confidence=case["confidence"], synthetic=True,
        )

    complete = analyze("all_70", "complete-fixture")
    partial = analyze("competitive_advantage__MISSING_DATA__numeric", "partial-fixture")
    board = LeaderboardEngine().build(
        "SYNTHETIC_CONSUMER_AUDIT", complete.as_of, [complete, partial],
        tickers={complete.company_id: "COMPLETE", partial.company_id: "PARTIAL"},
    )
    rank = next(row.rank for row in board.rows if row.company_id == partial.company_id)
    check(checks, partial.total_score == 63.0, "partial total equals 63")
    check(checks, partial.coverage_state.value == "PARTIAL", "partial coverage equals PARTIAL")
    check(checks, len(board.rows) == 2, "legacy board includes both supplied snapshots")
    check(checks, rank == 2, "partial snapshot receives legacy rank 2")
    selection = rank_cross_section({partial.company_id: {
        "Q": partial.Q_score, "G": partial.G_score, "V": partial.V_score,
    }})
    check(checks, selection[0]["eligible"] is True, "provisional Portfolio selector accepts Q/G-present partial")
    check(checks, is_actionable(DataQuality.PARTIAL) is True, "Personal actionable helper accepts PARTIAL")

    registry = OfficialRegistry("SYNTHETIC_REGISTRY", (
        NodeDefinition("root", None, "QGV", NodeType.GROUP, Maturity.PRODUCTION, "Root"),
        NodeDefinition("a", "root", "QGV", NodeType.WEIGHT, Maturity.PRODUCTION, "A", 0.5),
        NodeDefinition("b", "root", "QGV", NodeType.WEIGHT, Maturity.PRODUCTION, "B", 0.5),
    ))
    before = content_hash(registry)
    version = PersonalStrategyVersion(
        "fixture-version", "fixture", "SYNTHETIC_REGISTRY",
        ResultNamespace.CUSTOM_ACTIVE,
        (WeightOverride("a", 0.0), WeightOverride("b", 1.0)),
        StrategyStatus.DRAFT, complete.as_of,
    )
    tree = effective_tree(registry, version)
    check(checks, tree["a"].global_weight == 0.0, "Custom zero has zero global contribution weight")
    check(checks, content_hash(registry) == before, "Official registry content hash unchanged after Custom resolution")
    errors = []
    try:
        effective_tree(registry, dataclasses.replace(version, namespace=ResultNamespace.OFFICIAL))
    except WeightTreeError as exc:
        errors.append(str(exc))
        check(checks, True, "Official override rejected")
    else:
        raise AssertionError("Official override accepted")
    changes = (
        ({"method_identity": "changed"}, "StrategyProfile method identity key rejected"),
        ({"q_weights": {}}, "StrategyProfile frozen Q weights key rejected"),
    )
    for change, description in changes:
        try:
            custom_profile(change)
        except ValueError as exc:
            errors.append(str(exc))
            check(checks, True, description)
        else:
            raise AssertionError(description)
    fields = [f.name for f in dataclasses.fields(WeightOverride)]
    check(checks, fields == ["node_id", "local_weight"], "WeightOverride fields exactly numeric node_id/local_weight")
    return checks, [
        {"case_id": "CP-PARTIAL-LEADERBOARD", "fixture_ref": "golden_cases.json:competitive_advantage__MISSING_DATA__numeric", "actual": {"Q": partial.Q_score, "G": partial.G_score, "total": partial.total_score, "coverage": partial.coverage_state.value, "rank": rank, "board_rows": len(board.rows)}},
        {"case_id": "CP-PARTIAL-PORTFOLIO-SELECTION", "actual": selection[0]},
        {"case_id": "CP-PERSONAL-PARTIAL", "actual": {"is_actionable_PARTIAL": True}},
        {"case_id": "CP-WEIGHT-ISOLATION", "actual": {"registry_hash_before": before, "registry_hash_after": content_hash(registry), "custom_zero_global_weight": tree["a"].global_weight, "rejected_changes": errors, "override_fields": fields}},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Scratch JSON evidence path")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--integration-root", type=Path)
    parser.add_argument("--publication-only", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.publication_only:
        evidence = publication_probe()
    else:
        repo = args.repo_root or next(p for p in Path(__file__).resolve().parents if (p / "implementation/src/investment_system").is_dir())
        integration = args.integration_root or repo.parent / "qgv-integration-2026-10-05"
        observed = subprocess.check_output(["git", "-C", str(integration), "rev-parse", "HEAD"], text=True).strip()
        if observed != INTEGRATION_PIN:
            raise AssertionError(f"Integration source drift: {observed} != {INTEGRATION_PIN}")
        checks, cases = owner_probe(repo)
        with tempfile.TemporaryDirectory(prefix="qgv-consumer-probe-") as scratch:
            publication_out = Path(scratch) / "publication.json"
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(integration / "implementation/src") + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--publication-only", "--out", str(publication_out)], cwd=integration, env=env, check=True, capture_output=True, text=True)
            publication = json.loads(publication_out.read_text())
        checks.extend(publication["checks"])
        cases.append(publication["case"])
        assert len(checks) == 20 and len(cases) == 5
        evidence = {
            "status": "READ_ONLY_CURRENT_BOUNDARY_CHARACTERIZATION_PASS",
            "production_runtime_vnext": "NOT_IMPLEMENTED",
            "new_consumer_policy_acceptance": "NOT_RUN",
            "integration_source_head": observed,
            "counterexample_families": cases,
            "checks": {"passed": len(checks), "failed": 0, "asserted_conditions": checks},
            "holdout": "UNCONSUMED",
            "runtime_enabled": False,
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "checks": len(evidence["checks"]) if args.publication_only else evidence["checks"]["passed"], "families": 1 if args.publication_only else len(evidence["counterexample_families"])}))


if __name__ == "__main__":
    main()
