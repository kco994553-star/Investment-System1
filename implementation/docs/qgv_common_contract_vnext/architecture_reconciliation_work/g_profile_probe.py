"""Read-only synthetic characterization. Run with the pinned owner src on PYTHONPATH.

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<owner>/implementation/src python g_profile_probe.py --owner-root <owner> --out <scratch>/g_profile_checks.json
No runtime policy or legacy semantic change is performed.
"""
from dataclasses import fields, replace
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from investment_system.contracts.models import DataStamp, FactorObservation
from investment_system.contracts.raw import RawFundamentals
from investment_system.contracts.enums import QualityState
from investment_system.contracts.strategy import custom_profile
from investment_system.qgv.raw_map import map_raw
from investment_system.qgv.pipeline import AnalysisPipeline
from investment_system.qgv.g_horizon import GHorizonConfig
from investment_system.qgv.quarterly_series import quarterly_points_from_facts
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import Q_WEIGHTS, G_WEIGHTS, V_FACTORS
from investment_system.personal.weights import OfficialRegistry, NodeDefinition, NodeType, Maturity, PersonalStrategyVersion, WeightOverride, StrategyStatus, effective_tree
from investment_system.personal.versioning import ResultNamespace, content_hash

PIN = "4fb08a05728d83519b72a2bd995669f0cb06003a"
FILES = [
    "qgv/raw_map.py", "qgv/g_horizon.py", "qgv/pipeline.py", "qgv/quarterly_series.py",
    "qgv/scoring.py", "qgv/analysis.py", "qgv/factors.py", "contracts/raw.py",
    "contracts/models.py", "contracts/strategy.py", "providers/sec_companyfacts.py",
    "providers/sec_vintage.py", "personal/weights.py", "personal/versioning.py",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.owner_root.resolve()
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        raise SystemExit("Owner HEAD differs from exact audit pin; re-audit instead of silently rebasing")
    now = datetime(2026, 10, 5, 4, 0, tzinfo=timezone.utc)
    stamp = DataStamp("synthetic-g-audit", "synthetic", "fixture", "local-only", now, now, now, synthetic=True)
    raw = RawFundamentals("SYNTHETIC-G-AUDIT", stamp, revenue=120, revenue_prev=100, eps=3, eps_prev=2, fcf=20, shares=1, ebit=20, net_income=15, invested_capital=100, wacc=.08, cash=50, total_debt=20, market_share=.2, competitive_advantage_rubric=70, management_quality_rubric=70, growth_durability_rubric=70, industry_revenue_growth=.1, source_kind="SYNTHETIC")
    checks = []

    def check(name, actual, expected):
        ok = actual == expected
        checks.append({"case": name, "actual": actual, "expected": expected, "pass": ok})
        if not ok:
            raise AssertionError((name, actual, expected))

    pipe = AnalysisPipeline()
    a = pipe.analyze_raw(raw, g_horizon=GHorizonConfig("3Y"), available_quarters=20)
    b = pipe.analyze_raw(raw, g_horizon=GHorizonConfig("5Y"), available_quarters=20)
    check("G horizon 3Y->5Y changes metadata, not score", (a.G_score == b.G_score, a.g_horizon["requested"], b.g_horizon["requested"]), (True, "3Y", "5Y"))
    obs = map_raw(raw)
    check("Forecast-label proxy equals current revenue YoY factor", obs["next_3_5y_growth"].score_0_100, obs["revenue_growth"].score_0_100)
    fall = replace(raw, eps=None, eps_prev=None, revenue_prev=100, fcf=20)
    key = "eps_fcf_per_share_growth"
    check("Missing EPS fallback uses current FCF/prior revenue", map_raw(fall)[key].score_0_100, 0.0)
    check("Fallback ignores current shares", map_raw(replace(fall, shares=100))[key].score_0_100, map_raw(fall)[key].score_0_100)
    shape = {f.name for f in fields(RawFundamentals)}
    check("RawFundamentals has no prior FCF or prior shares", ("fcf_prev" in shape, "shares_prev" in shape), (False, False))
    check("Loss narrows -2->-1 produces minimum score", map_raw(replace(raw, eps=-1, eps_prev=-2))[key].score_0_100, 0.0)
    check("Loss deepens -1->-2 produces maximum score", map_raw(replace(raw, eps=-2, eps_prev=-1))[key].score_0_100, 100.0)
    check("Zero prior EPS routes to fallback", map_raw(replace(fall, eps=1, eps_prev=0))[key].score_0_100, 0.0)
    check("Financial profile uses identical G fallback", map_raw(replace(fall, profile_kind="FINANCIAL"))[key].score_0_100, 0.0)
    missing = map_raw(replace(fall, fcf=None))[key]
    check("No EPS/no FCF is missing, not zero", (missing.quality.value, missing.score_0_100), ("MISSING_DATA", None))
    payload = {"facts": {"us-gaap": {"FreeCashFlow": {"units": {"USD": [{"val": 100.0, "start": "2026-01-01", "end": "2026-03-31", "filed": "2026-04-20T10:00:00+00:00", "form": "10-Q", "fy": 2026, "fp": "Q1", "accn": "synthetic"}]}}}}}
    check("Quarterly dollar FCF populates fcf_per_share", quarterly_points_from_facts(payload, now)[0].fcf_per_share, 100.0)
    check("Future-filing quarterly FCF excluded", len(quarterly_points_from_facts(payload, datetime(2026, 4, 19, tzinfo=timezone.utc))), 0)
    ids = set(Q_WEIGHTS) | set(G_WEIGHTS) | set(V_FACTORS)

    def factors(v):
        return {fid: FactorObservation(fid, v if fid in V_FACTORS else 70, v if fid in V_FACTORS else 70, QualityState.SYNTHETIC, "synthetic", "local-only") for fid in ids}

    s0 = AnalysisEngine().analyze("synthetic-composite", now, factors(0), synthetic=True)
    s1 = AnalysisEngine().analyze("synthetic-composite", now, factors(100), synthetic=True)
    check("V score change does not enter current composite", (s0.V_score, s1.V_score, s0.total_score, s1.total_score), (0.0, 100.0, 70.0, 70.0))
    check("Current type-adjusted equals literal total", s1.type_adjusted_score_100, s1.total_score)
    registry = OfficialRegistry("synthetic-registry", (NodeDefinition("root", None, "QGV", NodeType.GROUP, Maturity.VALIDATED, "root"), NodeDefinition("q", "root", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "Q", .5), NodeDefinition("g", "root", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "G", .5), NodeDefinition("qa", "q", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "qa", .5), NodeDefinition("qb", "q", "QGV", NodeType.WEIGHT, Maturity.VALIDATED, "qb", .5)))
    rhash = content_hash(registry)
    ver = PersonalStrategyVersion("synthetic-version", "synthetic-strategy", "synthetic-registry", ResultNamespace.SANDBOX, (WeightOverride("q", 0), WeightOverride("g", 1)), StrategyStatus.SANDBOX, now)
    tree = effective_tree(registry, ver)
    check("Zero parent preserves local mix, yields zero global contribution", (tree["qa"].local_weight, tree["qb"].local_weight, tree["qa"].global_weight, tree["qb"].global_weight), (.5, .5, 0.0, 0.0))
    check("Custom override keeps registry hash unchanged", content_hash(registry), rhash)

    def rejected(fn):
        try:
            fn()
        except ValueError:
            return True
        return False

    check("Official namespace rejects override", rejected(lambda: effective_tree(registry, replace(ver, namespace=ResultNamespace.OFFICIAL))), True)
    check("Method identity not a Custom parameter", rejected(lambda: custom_profile({"method_identity": "new"})), True)
    check("Frozen Q weights not a Custom parameter", rejected(lambda: custom_profile({"q_weights": {"new": 1}})), True)
    check("WeightOverride shape is numeric-only", tuple(f.name for f in fields(WeightOverride)), ("node_id", "local_weight"))
    paths = ["implementation/src/investment_system/" + p for p in FILES] + ["implementation/docs/qgv_common_contract_vnext/CONTRACT.md", "implementation/docs/qgv_common_contract_vnext/missing_data_gate/implementation_contract/CONTRACT.md"]
    result = {"status": "CURRENT_BEHAVIOR_CHARACTERIZATION_PASS", "input_head": head, "synthetic_only": True, "production_semantics_changed": False, "new_policy_acceptance": False, "check_count": len(checks), "pass_count": sum(c["pass"] for c in checks), "checks": checks, "pinned_source_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}, "not_executed": ["new runtime implementation", "full regression", "real PIT/OOS", "Actions", "Holdout", "migration", "scheduler hops"]}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"out": str(args.out), "checks": len(checks), "passed": sum(c["pass"] for c in checks), "sha256": hashlib.sha256(args.out.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
